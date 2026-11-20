# Created by the AGI PROCESOR project in 2026.

"""Safe HTTP surface for the AGI PROCESOR market-risk MVP.

The router accepts caller-supplied market observations, returns a transparent
risk assessment, and records simulated paper trades.  It deliberately exposes
no account login, wallet, order-routing, scraping, or live-trading capability.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from openjarvis.core.paths import get_config_dir
from openjarvis.fomo import (
    AffiliateConfig,
    ContractRiskFlags,
    MarketSnapshot,
    PaperPortfolio,
    PaperTradingError,
    PaperTradingLedger,
    RiskAssessment,
    TradeSide,
    assess_market,
)

router = APIRouter(prefix="/v1/fomo", tags=["agi-procesor-fomo-radar"])
_ledger_init_lock = threading.Lock()


class ContractRiskFlagsRequest(BaseModel):
    """Optional findings from an authorised contract-analysis source."""

    honeypot_detected: bool | None = None
    mint_authority_enabled: bool | None = None
    freeze_authority_enabled: bool | None = None
    transfer_restrictions: bool | None = None
    owner_can_change_fees: bool | None = None
    contract_unverified: bool | None = None
    source_data_stale: bool | None = None


class MarketSnapshotRequest(BaseModel):
    """One user- or provider-supplied observation; no fetching happens here."""

    symbol: str = Field(min_length=1, max_length=32)
    price_usd: Decimal = Field(gt=0)
    market_cap_usd: Decimal = Field(ge=0)
    liquidity_usd: Decimal = Field(ge=0)
    volume_24h_usd: Decimal = Field(ge=0)
    price_change_24h_pct: Decimal
    token_age_hours: Decimal = Field(ge=0)
    top_holders_pct: Decimal = Field(ge=0, le=100)
    chain: str = Field(default="unknown", min_length=1, max_length=64)
    contract_risks: ContractRiskFlagsRequest = Field(
        default_factory=ContractRiskFlagsRequest,
    )
    observed_at: datetime | None = None
    source: str = Field(default="caller-supplied", min_length=1, max_length=256)


class PaperTradeRequest(BaseModel):
    """Explicitly confirmed simulated fill; never a real order."""

    symbol: str = Field(min_length=1, max_length=32)
    side: Literal["buy", "sell"]
    quantity: Decimal = Field(gt=0)
    price_usd: Decimal = Field(gt=0)
    fee_bps: Decimal | None = Field(default=None, ge=0, le=10_000)
    note: str = Field(default="", max_length=500)
    confirm_paper_trade: Literal[True]


class PortfolioRequest(BaseModel):
    """Optional mark prices for a read-only paper-portfolio valuation."""

    marks: dict[str, Decimal] = Field(default_factory=dict)


def _get_ledger(request: Request) -> PaperTradingLedger:
    existing = getattr(request.app.state, "_agi_fomo_ledger", None)
    if existing is not None:
        return existing

    with _ledger_init_lock:
        existing = getattr(request.app.state, "_agi_fomo_ledger", None)
        if existing is not None:
            return existing

        default_path = get_config_dir() / "agi-procesor" / "paper-ledger.json"
        storage_path = Path(
            os.environ.get(
                "AGI_PROCESOR_PAPER_LEDGER_PATH",
                str(default_path),
            ),
        ).expanduser()
        ledger = PaperTradingLedger(
            initial_cash_usd=os.environ.get(
                "AGI_PROCESOR_PAPER_INITIAL_CASH_USD",
                "10000",
            ),
            storage_path=storage_path,
            default_fee_bps=os.environ.get(
                "AGI_PROCESOR_PAPER_FEE_BPS",
                "45",
            ),
        )
        request.app.state._agi_fomo_ledger = ledger
        return ledger


def _assessment_payload(assessment: RiskAssessment) -> dict[str, object]:
    return {
        "symbol": assessment.symbol,
        "score": assessment.score,
        "level": assessment.level.value,
        "disposition": assessment.disposition.value,
        "flags": [
            {
                "code": flag.code,
                "title": flag.title,
                "detail": flag.detail,
                "points": flag.points,
            }
            for flag in assessment.flags
        ],
        "scenarios": [
            {
                "name": scenario.name,
                "trigger": scenario.trigger,
                "impact": scenario.impact,
                "control": scenario.control,
            }
            for scenario in assessment.scenarios
        ],
        "summary": assessment.summary,
        "disclaimer": assessment.disclaimer,
        "execution_capability": "none",
    }


def _portfolio_payload(portfolio: PaperPortfolio) -> dict[str, object]:
    return {
        "mode": "paper-only",
        "initial_cash_usd": str(portfolio.initial_cash_usd),
        "cash_usd": str(portfolio.cash_usd),
        "market_value_usd": str(portfolio.market_value_usd),
        "equity_usd": str(portfolio.equity_usd),
        "realized_pnl_usd": str(portfolio.realized_pnl_usd),
        "unrealized_pnl_usd": str(portfolio.unrealized_pnl_usd),
        "total_pnl_usd": str(portfolio.total_pnl_usd),
        "positions": [
            {
                "symbol": position.symbol,
                "quantity": str(position.quantity),
                "average_entry_price_usd": str(
                    position.average_entry_price_usd,
                ),
                "cost_basis_usd": str(position.cost_basis_usd),
                "mark_price_usd": str(position.mark_price_usd),
                "market_value_usd": str(position.market_value_usd),
                "unrealized_pnl_usd": str(position.unrealized_pnl_usd),
                "price_is_estimated": position.price_is_estimated,
            }
            for position in portfolio.positions
        ],
    }


@router.get("/capabilities")
async def fomo_capabilities() -> dict[str, object]:
    """Describe hard product boundaries for clients and audits."""

    return {
        "product": "AGI PROCESOR FOMO Radar",
        "relationship_to_fomo": "independent affiliate; no endorsement implied",
        "market_data_mode": "caller-supplied or separately authorised",
        "account_access": False,
        "scraping": False,
        "wallet_access": False,
        "automated_trading": False,
        "paper_trading": True,
        "human_decision_required": True,
    }


@router.get("/affiliate")
async def affiliate_metadata(language: str = "pl") -> dict[str, object]:
    """Return validated public link metadata and the required disclosure."""

    try:
        return AffiliateConfig.from_env().public_metadata(language=language)
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail="Invalid public affiliate-link configuration",
        ) from exc


@router.post("/risk-assessments")
async def create_risk_assessment(
    body: MarketSnapshotRequest,
) -> dict[str, object]:
    """Score one supplied snapshot without performing any network request."""

    values = body.model_dump()
    flag_values = values.pop("contract_risks")
    if values["observed_at"] is None:
        values.pop("observed_at")
    try:
        snapshot = MarketSnapshot(
            **values,
            contract_risks=ContractRiskFlags(**flag_values),
        )
        assessment = assess_market(snapshot)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "snapshot": snapshot.as_dict(),
        "assessment": _assessment_payload(assessment),
    }


@router.get("/paper/trades")
async def list_paper_trades(request: Request) -> dict[str, object]:
    ledger = _get_ledger(request)
    return {
        "mode": "paper-only",
        "trades": [trade.as_dict() for trade in ledger.trades],
    }


@router.get("/paper/portfolio")
async def get_paper_portfolio(request: Request) -> dict[str, object]:
    return _portfolio_payload(_get_ledger(request).portfolio())


@router.post("/paper/portfolio")
async def value_paper_portfolio(
    body: PortfolioRequest,
    request: Request,
) -> dict[str, object]:
    try:
        return _portfolio_payload(_get_ledger(request).portfolio(body.marks))
    except PaperTradingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/paper/trades")
async def create_paper_trade(
    body: PaperTradeRequest,
    request: Request,
) -> dict[str, object]:
    ledger = _get_ledger(request)
    try:
        trade = ledger.execute(
            body.symbol,
            TradeSide(body.side),
            body.quantity,
            body.price_usd,
            fee_bps=body.fee_bps,
            note=body.note,
        )
    except PaperTradingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "mode": "paper-only",
        "trade": trade.as_dict(),
        "portfolio": _portfolio_payload(ledger.portfolio()),
    }


__all__ = ["router"]
