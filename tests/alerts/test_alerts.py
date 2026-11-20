# Created by the AGI PROCESOR project in 2026.

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest

from openjarvis.alerts import (
    AlertChannel,
    AlertDispatcher,
    AlertRule,
    AlertService,
    AlertServiceError,
    AlertStore,
    AlertStoreError,
    DispatchResult,
    QueueStatus,
    ReviewAction,
    render_alert,
    render_sms,
)
from openjarvis.fomo import ContractRiskFlags, MarketSnapshot


def _rule(**overrides) -> AlertRule:
    values = {
        "name": "SAFE risk watch",
        "symbol": "SAFE",
        "channels": (AlertChannel.EMAIL,),
        "cooldown_seconds": 900,
        "activation_condition": "Review only when generated thresholds match.",
        "invalidation_condition": "Invalidate when newer verified data changes risk.",
    }
    values.update(overrides)
    return AlertRule.create(**values)


def _snapshot(**overrides) -> MarketSnapshot:
    values = {
        "symbol": "SAFE",
        "price_usd": "1.25",
        "market_cap_usd": "50000000",
        "liquidity_usd": "5000000",
        "volume_24h_usd": "250000",
        "price_change_24h_pct": "3.5",
        "token_age_hours": "9000",
        "top_holders_pct": "18",
        "chain": "base",
        "source": "authorised unit-test feed",
        "observed_at": datetime.now(timezone.utc).replace(microsecond=0),
    }
    values.update(overrides)
    return MarketSnapshot(**values)


def test_rule_evaluation_has_explicit_watch_caution_and_avoid_states(tmp_path):
    service = AlertService(AlertStore(tmp_path / "alerts.json"))
    rule = _rule()

    watch = service.evaluate(rule, _snapshot(), persist=False).event
    caution = service.evaluate(
        rule,
        _snapshot(
            liquidity_usd="100000",
            price_change_24h_pct="30",
            top_holders_pct="50",
        ),
        persist=False,
    ).event
    avoid = service.evaluate(
        rule,
        _snapshot(
            contract_risks=ContractRiskFlags(honeypot_detected=True),
        ),
        persist=False,
    ).event

    assert watch.state.value == "watch"
    assert watch.review_action is ReviewAction.ENTRY_REVIEW
    assert caution.state.value == "caution"
    assert caution.review_action is ReviewAction.MONITOR
    assert avoid.state.value == "avoid"
    assert avoid.review_action is ReviewAction.EXIT_REVIEW
    assert "instruction to buy or sell" in avoid.disclaimer


def test_rule_cannot_weaken_underlying_avoid_disposition(tmp_path):
    service = AlertService(AlertStore(tmp_path / "alerts.json"))
    event = service.evaluate(
        _rule(avoid_min_risk_score=90),
        _snapshot(
            liquidity_usd="5000",
            volume_24h_usd="0",
            token_age_hours="2",
            top_holders_pct="70",
        ),
        persist=False,
    ).event

    assert event.risk_score < 90
    assert event.state.value == "avoid"
    assert "underlying risk scorer" in event.condition


def test_render_discloses_source_time_risk_invalidation_and_no_execution(tmp_path):
    result = AlertService(AlertStore(tmp_path / "alerts.json")).evaluate(
        _rule(),
        _snapshot(),
        persist=False,
    )

    message = render_alert(result.event)

    assert "Source: authorised unit-test feed" in message
    assert f"Observed timestamp: {result.event.observed_at.isoformat()}" in message
    assert "Risk:" in message
    assert "Invalidation condition:" in message
    assert "Disclaimer:" in message
    assert "Execution capability: none" in message


def test_atomic_store_persists_and_suppresses_duplicate_inside_cooldown(tmp_path):
    path = tmp_path / "nested" / "alerts.json"
    store = AlertStore(path)
    rule = store.upsert_rule(_rule())
    event = AlertService(store).evaluate(rule, _snapshot(), persist=False).event
    now = datetime(2026, 1, 2, 1, tzinfo=timezone.utc)

    first = store.enqueue(event, cooldown_seconds=900, now=now)
    duplicate = store.enqueue(
        AlertService(store).evaluate(rule, _snapshot(), persist=False).event,
        cooldown_seconds=900,
        now=now + timedelta(minutes=5),
    )

    assert first.queue_status is QueueStatus.QUEUED
    assert duplicate.queue_status is QueueStatus.COOLDOWN_SUPPRESSED
    reloaded = AlertStore(path)
    assert reloaded.get_rule(rule.rule_id) == rule
    assert len(reloaded.list_events()) == 2
    assert not list(path.parent.glob("*.tmp"))


def test_corrupt_store_fails_closed_without_overwrite(tmp_path):
    path = tmp_path / "alerts.json"
    path.write_text("not-json", encoding="utf-8")
    original = path.read_bytes()

    with pytest.raises(AlertStoreError):
        AlertStore(path).upsert_rule(_rule())

    assert path.read_bytes() == original


def test_actual_delivery_requires_confirmation(tmp_path):
    store = AlertStore(tmp_path / "alerts.json")
    rule = store.upsert_rule(_rule(enabled=True))
    service = AlertService(store)
    event = service.evaluate(rule, _snapshot(), persist=True).event

    with pytest.raises(AlertServiceError, match="confirm_send"):
        service.send_event(event.event_id, confirm_send=False)


def test_channel_capabilities_do_not_disclose_destinations_or_secrets():
    dispatcher = AlertDispatcher(
        {
            "AGI_PROCESOR_ALERTS_SMTP_HOST": "smtp.example.test",
            "AGI_PROCESOR_ALERTS_SMTP_FROM": "sender@example.test",
            "AGI_PROCESOR_ALERTS_SMTP_USE_SSL": "false",
            "AGI_PROCESOR_ALERTS_SMTP_STARTTLS": "true",
            "AGI_PROCESOR_ALERTS_EMAIL_TO": "owner@example.test",
            "AGI_PROCESOR_ALERTS_TELEGRAM_BOT_TOKEN": "very-secret-token",
            "AGI_PROCESOR_ALERTS_TELEGRAM_CHAT_ID": "123456",
            "AGI_PROCESOR_ALERTS_NTFY_URL": "https://ntfy.example.test/topic",
            "AGI_PROCESOR_ALERTS_NTFY_TOKEN": "ntfy-secret",
            "AGI_PROCESOR_ALERTS_SMS_MODE": "http",
            "AGI_PROCESOR_ALERTS_SMS_HTTP_URL": ("https://sms.example.test/messages"),
            "AGI_PROCESOR_ALERTS_SMS_HTTP_TOKEN": "sms-secret",
            "AGI_PROCESOR_ALERTS_SMS_TO": "+48123456789",
            "AGI_PROCESOR_ALERTS_SMS_ALLOWED_HOSTS": "sms.example.test",
        }
    )

    capabilities = dispatcher.capabilities()
    rendered = repr(capabilities)

    assert all(value["configured"] is True for value in capabilities.values())
    assert "very-secret-token" not in rendered
    assert "+48123456789" not in rendered


def test_http_sms_requires_explicit_host_allowlist():
    dispatcher = AlertDispatcher(
        {
            "AGI_PROCESOR_ALERTS_SMS_MODE": "http",
            "AGI_PROCESOR_ALERTS_SMS_HTTP_URL": "https://sms.example.test/send",
            "AGI_PROCESOR_ALERTS_SMS_HTTP_TOKEN": "secret",
            "AGI_PROCESOR_ALERTS_SMS_TO": "+48123456789",
            "AGI_PROCESOR_ALERTS_SMS_ALLOWED_HOSTS": "different.example.test",
        }
    )

    capability = dispatcher.capabilities()["sms"]

    assert capability["configured"] is False
    assert "allowlisted" in capability["reason"]


def test_provider_error_log_is_sanitised(tmp_path, monkeypatch, caplog):
    secret = "telegram-secret-token"
    dispatcher = AlertDispatcher(
        {
            "AGI_PROCESOR_ALERTS_TELEGRAM_BOT_TOKEN": secret,
            "AGI_PROCESOR_ALERTS_TELEGRAM_CHAT_ID": "123",
        }
    )
    event = (
        AlertService(AlertStore(tmp_path / "alerts.json"))
        .evaluate(
            _rule(channels=(AlertChannel.TELEGRAM,)),
            _snapshot(),
            persist=False,
        )
        .event
    )

    def fail(message):
        raise RuntimeError(f"provider URL contained {secret}")

    monkeypatch.setattr(dispatcher, "_send_telegram", fail)
    result = dispatcher.send(AlertChannel.TELEGRAM, event)

    assert result.success is False
    assert "RuntimeError" in result.detail
    assert "RuntimeError" in caplog.text
    assert secret not in result.detail
    assert secret not in caplog.text


def test_snapshot_freshness_rejects_stale_and_future_data(tmp_path):
    now = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
    service = AlertService(
        AlertStore(tmp_path / "alerts.json"),
        max_snapshot_age_seconds=60,
        max_future_skew_seconds=10,
        clock=lambda: now,
    )

    with pytest.raises(ValueError, match="stale"):
        service.evaluate(
            _rule(),
            _snapshot(observed_at=now - timedelta(seconds=61)),
            persist=False,
        )
    with pytest.raises(ValueError, match="future"):
        service.evaluate(
            _rule(),
            _snapshot(observed_at=now + timedelta(seconds=11)),
            persist=False,
        )
    assert service.evaluate(_rule(), _snapshot(observed_at=now), persist=False)


def test_sms_renderer_is_cost_bounded_and_keeps_required_disclosures(tmp_path):
    event = (
        AlertService(AlertStore(tmp_path / "alerts.json"))
        .evaluate(
            _rule(),
            _snapshot(),
            persist=False,
        )
        .event
    )

    message = render_sms(event)

    assert len(message) <= 300
    assert "Src:" in message
    assert "At:" in message
    assert "Risk:" in message
    assert "Cond:" in message
    assert "Invalid:" in message
    assert "Disclaimer:" in message
    assert "No execution." in message


def test_parallel_send_uses_one_atomic_delivery_claim(tmp_path):
    class BlockingDispatcher:
        def __init__(self):
            self.started = threading.Event()
            self.release = threading.Event()
            self.calls = 0

        def send(self, channel, event):
            self.calls += 1
            self.started.set()
            assert self.release.wait(timeout=5)
            return DispatchResult(
                channel,
                True,
                "Delivered",
                datetime.now(timezone.utc),
            )

    dispatcher = BlockingDispatcher()
    store = AlertStore(tmp_path / "alerts.json")
    rule = store.upsert_rule(_rule())
    service = AlertService(store, dispatcher=dispatcher)
    event = service.evaluate(rule, _snapshot(), persist=True).event
    worker_errors: list[Exception] = []

    def worker() -> None:
        try:
            service.send_event(event.event_id, confirm_send=True)
        except Exception as exc:  # pragma: no cover - asserted below
            worker_errors.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    assert dispatcher.started.wait(timeout=5)
    with pytest.raises(AlertServiceError, match="active send lease"):
        service.send_event(event.event_id, confirm_send=True)
    dispatcher.release.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert not worker_errors
    assert dispatcher.calls == 1
    assert store.get_event(event.event_id).queue_status is QueueStatus.SENT


def test_retry_backoff_and_attempt_limit_do_not_repeat_provider_calls(tmp_path):
    class FailingDispatcher:
        def __init__(self):
            self.calls = 0

        def send(self, channel, event):
            self.calls += 1
            return DispatchResult(channel, False, "failed", clock[0])

    clock = [datetime(2026, 11, 20, 12, tzinfo=timezone.utc)]
    dispatcher = FailingDispatcher()
    store = AlertStore(tmp_path / "alerts.json")
    rule = store.upsert_rule(_rule())
    service = AlertService(
        store,
        dispatcher=dispatcher,
        max_attempts_per_channel=2,
        retry_backoff_seconds=60,
        clock=lambda: clock[0],
    )
    event = service.evaluate(
        rule,
        _snapshot(observed_at=clock[0]),
        persist=True,
    ).event

    first = service.send_event(event.event_id, confirm_send=True)
    immediate = service.send_event(event.event_id, confirm_send=True)
    clock[0] += timedelta(seconds=61)
    second = service.send_event(event.event_id, confirm_send=True)
    exhausted = service.send_event(event.event_id, confirm_send=True)

    assert first[0].queue_status is QueueStatus.FAILED
    assert "backoff" in immediate[1][0].detail.lower()
    assert second[0].queue_status is QueueStatus.FAILED
    assert "limit" in exhausted[1][0].detail.lower()
    assert dispatcher.calls == 2


def test_failed_delivery_does_not_start_success_cooldown(tmp_path):
    class FailingDispatcher:
        def send(self, channel, event):
            return DispatchResult(
                channel,
                False,
                "failed",
                datetime.now(timezone.utc),
            )

    store = AlertStore(tmp_path / "alerts.json")
    rule = store.upsert_rule(_rule())
    service = AlertService(
        store,
        dispatcher=FailingDispatcher(),
        max_attempts_per_channel=1,
        retry_backoff_seconds=0,
    )
    first = service.evaluate(rule, _snapshot(), persist=True).event
    service.send_event(first.event_id, confirm_send=True)

    next_event = service.evaluate(rule, _snapshot(), persist=True).event

    assert next_event.queue_status is QueueStatus.QUEUED
