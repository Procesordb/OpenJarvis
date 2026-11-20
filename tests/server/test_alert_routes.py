# Created by the AGI PROCESOR project in 2026.

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openjarvis.alerts import AlertChannel, AlertService, AlertStore, DispatchResult
from openjarvis.server.alert_routes import router
from openjarvis.server.api_routes import include_all_routes


class _SuccessfulDispatcher:
    def capabilities(self):
        return {channel.value: {"configured": True} for channel in AlertChannel}

    def send(self, channel, event):
        return DispatchResult(
            channel=channel,
            success=True,
            detail="Delivered by test adapter",
            attempted_at=datetime.now(timezone.utc),
        )


def _client(tmp_path) -> TestClient:
    app = FastAPI()
    app.state._agi_alert_service = AlertService(
        AlertStore(tmp_path / "alerts.json"),
        dispatcher=_SuccessfulDispatcher(),
    )
    app.include_router(router)
    return TestClient(app)


def _rule_payload(**overrides):
    payload = {
        "symbol": "SAFE",
        "channels": ["email", "telegram"],
        "cooldown_minutes": 15,
        "activation_condition": (
            "Generated risk and price thresholds match the review plan."
        ),
        "invalidation_condition": (
            "A newer authorised snapshot changes risk or invalidates source facts."
        ),
        "confirm_rule_creation": True,
    }
    payload.update(overrides)
    return payload


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
        "source": "authorised API test feed",
        "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_global_api_router_wires_alert_capabilities():
    app = FastAPI()
    include_all_routes(app)

    paths = {route.path for route in app.routes}

    assert "/v1/alerts/capabilities" in paths


def test_capabilities_disclose_boundaries_and_channel_state(tmp_path, monkeypatch):
    monkeypatch.delenv("AGI_PROCESOR_ALERTS_SCHEDULER_ENABLED", raising=False)

    response = _client(tmp_path).get("/v1/alerts/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["supported_states"] == ["watch", "caution", "avoid"]
    assert body["automated_trading"] is False
    assert body["execution_capability"] == "none"
    assert body["dispatch_scheduler_enabled"] is False
    assert body["dispatch_scheduler_mode"] == "external-operator-triggered"
    assert body["automatic_evaluation"] is False
    assert body["snapshot_freshness"]["required"] is True
    assert body["delivery_policy"]["atomic_claim"] is True
    assert body["delivery_policy"]["max_attempts_per_channel"] == 3
    assert body["sms_policy"]["default_max_chars"] == 300
    assert set(body["configured_channels"]) == {
        "email",
        "telegram",
        "ntfy",
        "sms",
    }


def test_rule_creation_requires_confirmation_and_safe_minimums(tmp_path):
    client = _client(tmp_path)
    missing_confirmation = _rule_payload()
    missing_confirmation.pop("confirm_rule_creation")

    assert client.post("/v1/alerts/rules", json=missing_confirmation).status_code == 422
    assert (
        client.post(
            "/v1/alerts/rules",
            json=_rule_payload(activation_condition="short"),
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/v1/alerts/rules",
            json=_rule_payload(cooldown_minutes=14),
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/v1/alerts/rules",
            json=_rule_payload(symbol="BAD\nSYMBOL"),
        ).status_code
        == 422
    )

    created = client.post("/v1/alerts/rules", json=_rule_payload())

    assert created.status_code == 201
    rule = created.json()["rule"]
    assert rule["watch_max_risk_score"] == 24
    assert rule["avoid_min_risk_score"] == 75
    assert rule["cooldown_seconds"] == 900
    assert rule["execution_capability"] == "none"
    assert rule["condition_text_machine_evaluated"] is False
    assert "watch_max_risk_score" in rule["machine_evaluated_fields"]


def test_dry_run_queue_dedupe_render_and_explicit_send_flow(tmp_path):
    client = _client(tmp_path)
    rule_id = client.post("/v1/alerts/rules", json=_rule_payload()).json()["rule"][
        "rule_id"
    ]
    evaluation = {"rule_id": rule_id, "snapshot": _snapshot()}

    dry_run = client.post("/v1/alerts/dry-run", json=evaluation)
    assert dry_run.status_code == 200
    assert dry_run.json()["dry_run"] is True
    assert client.get("/v1/alerts/history").json()["count"] == 0
    assert client.post("/v1/alerts/evaluate", json=evaluation).status_code == 422

    queued = client.post(
        "/v1/alerts/evaluate",
        json={**evaluation, "confirm_queue": True},
    )
    assert queued.status_code == 200
    event = queued.json()["event"]
    assert event["state"] == "watch"
    assert event["queue_status"] == "queued"
    assert event["execution_capability"] == "none"

    duplicate = client.post(
        "/v1/alerts/evaluate",
        json={**evaluation, "confirm_queue": True},
    )
    assert duplicate.json()["event"]["queue_status"] == "cooldown_suppressed"
    rule_view = client.get("/v1/alerts/rules").json()["rules"][0]
    assert rule_view["last_disposition"] == "WATCH"
    assert rule_view["last_evaluated_at"] is not None

    rendered = client.get(f"/v1/alerts/events/{event['event_id']}/render")
    assert rendered.status_code == 200
    message = rendered.json()["message"]
    assert "Source: authorised API test feed" in message
    assert "Invalidation condition:" in message
    assert "Disclaimer:" in message

    assert (
        client.post(f"/v1/alerts/events/{event['event_id']}/send", json={}).status_code
        == 422
    )
    sent = client.post(
        f"/v1/alerts/events/{event['event_id']}/send",
        json={"confirm_send": True},
    )
    assert sent.status_code == 200
    assert sent.json()["event"]["queue_status"] == "sent"
    assert sent.json()["transaction_executed"] is False
    assert len(sent.json()["deliveries"]) == 2

    history = client.get("/v1/alerts/history").json()["history"]
    assert history[0]["disposition"] in {"watch", "caution", "avoid"}
    assert history[0]["source"] == "authorised API test feed"


def test_rule_update_and_delete_each_require_explicit_confirmation(tmp_path):
    client = _client(tmp_path)
    rule_id = client.post("/v1/alerts/rules", json=_rule_payload()).json()["rule"][
        "rule_id"
    ]
    update = {
        "activation_condition": "Updated review condition remains human controlled.",
        "invalidation_condition": (
            "Updated invalidation requires a newer verified snapshot."
        ),
    }

    assert client.put(f"/v1/alerts/rules/{rule_id}", json=update).status_code == 422
    updated = client.put(
        f"/v1/alerts/rules/{rule_id}",
        json={**update, "confirm_rule_update": True, "cooldown_minutes": 30},
    )
    assert updated.status_code == 200
    assert updated.json()["rule"]["cooldown_minutes"] == 30

    partial = client.put(
        f"/v1/alerts/rules/{rule_id}",
        json={"enabled": False, "confirm_rule_update": True},
    )
    assert partial.status_code == 200
    assert partial.json()["rule"]["enabled"] is False

    with_price = client.put(
        f"/v1/alerts/rules/{rule_id}",
        json={"entry_price_at_or_below": "1.00", "confirm_rule_update": True},
    )
    assert with_price.json()["rule"]["entry_price_at_or_below"] == "1.00"
    cleared = client.put(
        f"/v1/alerts/rules/{rule_id}",
        json={"entry_price_at_or_below": None, "confirm_rule_update": True},
    )
    assert cleared.status_code == 200
    assert cleared.json()["rule"]["entry_price_at_or_below"] is None

    assert (
        client.request("DELETE", f"/v1/alerts/rules/{rule_id}", json={}).status_code
        == 422
    )
    deleted = client.request(
        "DELETE",
        f"/v1/alerts/rules/{rule_id}",
        json={"confirm_rule_deletion": True},
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
