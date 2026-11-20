# Created by the AGI PROCESOR project in 2026.

"""Tests for the local-only paper trading ledger."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

import pytest

from openjarvis.fomo import (
    PaperTradingError,
    PaperTradingLedger,
    TradeSide,
)


def test_buy_and_partial_sell_account_for_both_fees() -> None:
    ledger = PaperTradingLedger(initial_cash_usd="1000", default_fee_bps="100")

    buy = ledger.execute("agi", TradeSide.BUY, "10", "10")
    after_buy = ledger.portfolio({"AGI": "12"})

    assert buy.fee_usd == Decimal("1")
    assert buy.cash_delta_usd == Decimal("-101")
    assert ledger.cash_usd == Decimal("899")
    assert after_buy.positions[0].average_entry_price_usd == Decimal("10.1")
    assert after_buy.positions[0].unrealized_pnl_usd == Decimal("19")
    assert after_buy.total_pnl_usd == Decimal("19")

    sell = ledger.execute("AGI", "sell", "4", "15")
    portfolio = ledger.portfolio({"AGI": "12"})

    assert sell.fee_usd == Decimal("0.6")
    assert sell.realized_pnl_usd == Decimal("19.0")
    assert portfolio.cash_usd == Decimal("958.4")
    assert portfolio.positions[0].quantity == Decimal("6")
    assert portfolio.positions[0].cost_basis_usd == Decimal("60.6")
    assert portfolio.unrealized_pnl_usd == Decimal("11.4")
    assert portfolio.total_pnl_usd == Decimal("30.4")


def test_rejects_overspending_and_overselling() -> None:
    ledger = PaperTradingLedger(initial_cash_usd="100")

    with pytest.raises(PaperTradingError, match="insufficient simulated cash"):
        ledger.execute("AGI", "buy", "11", "10")
    assert ledger.cash_usd == Decimal("100")
    assert ledger.trades == ()

    ledger.execute("AGI", "buy", "1", "10", fee_bps="0")
    with pytest.raises(PaperTradingError, match="position"):
        ledger.execute("AGI", "sell", "2", "10", fee_bps="0")
    assert len(ledger.trades) == 1


@pytest.mark.parametrize(
    ("quantity", "price", "fee"),
    [
        ("0", "1", "0"),
        ("1", "0", "0"),
        ("1", "1", "-1"),
        ("1", "1", "10001"),
    ],
)
def test_rejects_invalid_trade_values(quantity: str, price: str, fee: str) -> None:
    ledger = PaperTradingLedger()
    with pytest.raises((PaperTradingError, ValueError)):
        ledger.execute("AGI", "buy", quantity, price, fee_bps=fee)


def test_estimated_mark_is_explicit() -> None:
    ledger = PaperTradingLedger(initial_cash_usd="100", default_fee_bps="0")
    ledger.execute("AGI", "buy", "2", "10")

    portfolio = ledger.portfolio()

    assert portfolio.positions[0].price_is_estimated is True
    assert portfolio.unrealized_pnl_usd == 0
    assert portfolio.total_pnl_usd == 0


def test_ledger_persists_and_reloads_without_credentials(tmp_path) -> None:
    path = tmp_path / "paper-ledger.json"
    ledger = PaperTradingLedger(
        initial_cash_usd="1000",
        storage_path=path,
        default_fee_bps="25",
    )
    ledger.execute("AGI", "buy", "10", "5", note="paper test")

    restored = PaperTradingLedger(initial_cash_usd="1", storage_path=path)
    restored_portfolio = restored.portfolio({"AGI": "6"})
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)

    assert restored.cash_usd == Decimal("949.875")
    assert restored_portfolio.positions[0].quantity == Decimal("10")
    assert restored.trades[0].note == "paper test"
    assert payload["metadata"] == {
        "contains_credentials": False,
        "mode": "paper-only",
    }
    assert "private_key" not in raw
    assert "session_token" not in raw


def test_invalid_ledger_file_fails_closed(tmp_path) -> None:
    path = tmp_path / "paper-ledger.json"
    path.write_text("not json", encoding="utf-8")

    with pytest.raises(PaperTradingError, match="invalid or unreadable"):
        PaperTradingLedger(storage_path=path)


def test_naive_execution_timestamp_is_rejected() -> None:
    ledger = PaperTradingLedger()
    with pytest.raises(PaperTradingError, match="timezone"):
        ledger.execute(
            "AGI",
            "buy",
            "1",
            "1",
            executed_at=datetime(2026, 11, 20),
        )
