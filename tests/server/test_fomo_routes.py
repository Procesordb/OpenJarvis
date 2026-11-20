# Created by the AGI PROCESOR project in 2026.

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openjarvis.fomo import PaperTradingLedger
from openjarvis.server.fomo_routes import router


def _client() -> TestClient:
    app = FastAPI()
    app.state._agi_fomo_ledger = PaperTradingLedger(
        initial_cash_usd="1000",
        default_fee_bps="45",
    )
    app.include_router(router)
    return TestClient(app)


def _snapshot(**overrides):
    payload = {
        "symbol": "SAFE",
        "price_usd": "1.25",
        "market_cap_usd": "50000000",
        "liquidity_usd": "5000000",
        "volume_24h_usd": "250000",
        "price_change_24h_pct": "3.5",
        "token_age_hours": "9000",
        "top_holders_pct": "18",
        "chain": "base",
        "source": "unit-test fixture",
    }
    payload.update(overrides)
    return payload


def test_capabilities_make_non_trading_boundary_explicit():
    response = _client().get("/v1/fomo/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["automated_trading"] is False
    assert body["wallet_access"] is False
    assert body["scraping"] is False
    assert body["paper_trading"] is True


def test_risk_assessment_is_explainable_and_non_executing():
    response = _client().post(
        "/v1/fomo/risk-assessments",
        json=_snapshot(
            liquidity_usd="5000",
            token_age_hours="2",
            top_holders_pct="92",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assessment"]["score"] > 0
    assert body["assessment"]["level"] in {"medium", "high", "critical"}
    assert body["assessment"]["flags"]
    assert body["assessment"]["execution_capability"] == "none"
    assert "not investment advice" in body["assessment"]["disclaimer"]


def test_risk_request_rejects_impossible_holder_concentration():
    response = _client().post(
        "/v1/fomo/risk-assessments",
        json=_snapshot(top_holders_pct="101"),
    )

    assert response.status_code == 422


def test_affiliate_metadata_contains_disclosure_and_no_credentials():
    response = _client().get("/v1/fomo/affiliate?language=pl")

    assert response.status_code == 200
    body = response.json()
    assert body["referral_url"] == "https://fomo.family/r/AGIPROCESOR"
    assert body["integration_mode"] == "link-only"
    assert body["contains_credentials"] is False
    assert "link afiliacyjny" in body["disclosure"]


def test_paper_trade_requires_explicit_simulation_confirmation():
    response = _client().post(
        "/v1/fomo/paper/trades",
        json={
            "symbol": "TEST",
            "side": "buy",
            "quantity": "10",
            "price_usd": "2",
        },
    )

    assert response.status_code == 422


def test_paper_trade_updates_only_the_simulated_portfolio():
    client = _client()
    response = client.post(
        "/v1/fomo/paper/trades",
        json={
            "symbol": "TEST",
            "side": "buy",
            "quantity": "10",
            "price_usd": "2",
            "confirm_paper_trade": True,
            "note": "simulation test",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "paper-only"
    assert body["trade"]["side"] == "buy"
    assert body["portfolio"]["positions"][0]["symbol"] == "TEST"

    history = client.get("/v1/fomo/paper/trades").json()
    assert history["mode"] == "paper-only"
    assert len(history["trades"]) == 1
