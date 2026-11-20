# Created by the AGI PROCESOR project in 2026.

"""Tests for deterministic FOMO Radar scoring."""

from __future__ import annotations

from openjarvis.fomo import (
    ContractRiskFlags,
    FomoRiskScorer,
    MarketSnapshot,
    RadarDisposition,
    RiskLevel,
    assess_market,
)


def _snapshot(**overrides: object) -> MarketSnapshot:
    values: dict[str, object] = {
        "symbol": "SAFE",
        "price_usd": "10",
        "market_cap_usd": "1000000000",
        "liquidity_usd": "5000000",
        "volume_24h_usd": "5000000",
        "price_change_24h_pct": "2",
        "token_age_hours": "20000",
        "top_holders_pct": "20",
        "contract_risks": ContractRiskFlags(
            honeypot_detected=False,
            mint_authority_enabled=False,
            freeze_authority_enabled=False,
            transfer_restrictions=False,
            owner_can_change_fees=False,
            contract_unverified=False,
            source_data_stale=False,
        ),
    }
    values.update(overrides)
    return MarketSnapshot(**values)  # type: ignore[arg-type]


def test_low_risk_snapshot_has_zero_score() -> None:
    assessment = assess_market(_snapshot())

    assert assessment.score == 0
    assert assessment.level is RiskLevel.LOW
    assert assessment.disposition is RadarDisposition.WATCH
    assert assessment.flags == ()
    assert "not investment advice" in assessment.disclaimer


def test_critical_risk_is_capped_and_fully_explained() -> None:
    snapshot = _snapshot(
        symbol="RISK",
        market_cap_usd="50000",
        liquidity_usd="5000",
        volume_24h_usd="100000",
        price_change_24h_pct="150",
        token_age_hours="12",
        top_holders_pct="90",
        contract_risks=ContractRiskFlags(
            honeypot_detected=True,
            transfer_restrictions=True,
        ),
    )

    assessment = FomoRiskScorer().assess(snapshot)
    codes = {flag.code for flag in assessment.flags}
    scenarios = {scenario.name for scenario in assessment.scenarios}

    assert assessment.score == 100
    assert assessment.level is RiskLevel.CRITICAL
    assert assessment.disposition is RadarDisposition.AVOID
    assert "contract_honeypot" in codes
    assert "liquidity_critical" in codes
    assert "Extreme 24-hour price move" in {flag.title for flag in assessment.flags}
    assert "Liquidity exit" in scenarios
    assert "Concentrated-holder sell-off" in scenarios
    assert "Contract-control event" in scenarios
    assert "Momentum reversal" in scenarios
    assert "Unproven market" in scenarios


def test_unknown_contract_checks_are_visible_and_scored() -> None:
    assessment = assess_market(_snapshot(contract_risks=ContractRiskFlags()))

    assert assessment.score == 8
    assert assessment.flags[0].code == "contract_not_checked"
    assert "unknown does not mean safe" in assessment.flags[0].detail
    assert {scenario.name for scenario in assessment.scenarios} == {
        "Data-quality gap",
    }


def test_same_snapshot_always_produces_same_assessment() -> None:
    snapshot = _snapshot(
        liquidity_usd="40000",
        market_cap_usd="400000",
        price_change_24h_pct="30",
    )
    scorer = FomoRiskScorer()

    assert scorer.assess(snapshot) == scorer.assess(snapshot)


def test_medium_risk_is_watch_not_transaction_instruction() -> None:
    assessment = assess_market(
        _snapshot(
            liquidity_usd="40000",
            market_cap_usd="400000",
            volume_24h_usd="40000",
        ),
    )

    assert assessment.score == 32
    assert assessment.level is RiskLevel.MEDIUM
    assert assessment.disposition is RadarDisposition.WATCH
