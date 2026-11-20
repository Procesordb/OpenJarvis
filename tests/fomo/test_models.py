# Created by the AGI PROCESOR project in 2026.

"""Tests for FOMO Radar domain models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from openjarvis.fomo import ContractRiskFlags, MarketSnapshot


def test_market_snapshot_normalizes_losslessly() -> None:
    snapshot = MarketSnapshot(
        symbol="  agi ",
        chain=" Solana ",
        price_usd=0.125,
        market_cap_usd="1000000",
        liquidity_usd="250000",
        volume_24h_usd=500000,
        price_change_24h_pct="-12.5",
        token_age_hours=240,
        top_holders_pct="39.5",
        contract_risks=ContractRiskFlags(contract_unverified=False),
        source="authorised-market-feed",
    )

    assert snapshot.symbol == "AGI"
    assert snapshot.chain == "solana"
    assert snapshot.price_usd == Decimal("0.125")
    assert snapshot.volume_to_liquidity_ratio == Decimal("2")
    payload = snapshot.as_dict()
    assert payload["price_usd"] == "0.125"
    assert payload["contract_risks"]["contract_unverified"] is False
    assert payload["observed_at"].endswith("+00:00")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("price_usd", "0"),
        ("market_cap_usd", "-1"),
        ("liquidity_usd", "-1"),
        ("volume_24h_usd", "-1"),
        ("token_age_hours", "-1"),
        ("top_holders_pct", "101"),
    ],
)
def test_market_snapshot_rejects_invalid_values(field: str, value: str) -> None:
    values: dict[str, object] = {
        "symbol": "TEST",
        "price_usd": "1",
        "market_cap_usd": "1000000",
        "liquidity_usd": "100000",
        "volume_24h_usd": "50000",
        "price_change_24h_pct": "1",
        "token_age_hours": "100",
        "top_holders_pct": "20",
    }
    values[field] = value

    with pytest.raises(ValueError):
        MarketSnapshot(**values)  # type: ignore[arg-type]


def test_market_snapshot_rejects_non_finite_and_boolean_numbers() -> None:
    base = {
        "symbol": "TEST",
        "market_cap_usd": "1000000",
        "liquidity_usd": "100000",
        "volume_24h_usd": "50000",
        "price_change_24h_pct": "1",
        "token_age_hours": "100",
        "top_holders_pct": "20",
    }
    with pytest.raises(ValueError, match="finite"):
        MarketSnapshot(price_usd="NaN", **base)
    with pytest.raises(ValueError, match="boolean"):
        MarketSnapshot(price_usd=True, **base)


def test_snapshot_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone"):
        MarketSnapshot(
            symbol="TEST",
            price_usd="1",
            market_cap_usd="1000000",
            liquidity_usd="100000",
            volume_24h_usd="50000",
            price_change_24h_pct="1",
            token_age_hours="100",
            top_holders_pct="20",
            observed_at=datetime(2026, 11, 20),
        )


def test_zero_liquidity_has_no_ratio() -> None:
    snapshot = MarketSnapshot(
        symbol="TEST",
        price_usd="1",
        market_cap_usd="1000000",
        liquidity_usd="0",
        volume_24h_usd="50000",
        price_change_24h_pct="1",
        token_age_hours="100",
        top_holders_pct="20",
    )
    assert snapshot.volume_to_liquidity_ratio is None


def test_contract_checked_count_distinguishes_false_from_unknown() -> None:
    flags = ContractRiskFlags(
        honeypot_detected=False,
        mint_authority_enabled=True,
    )
    assert flags.checked_count() == 2
