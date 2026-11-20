# Created by the AGI PROCESOR project in 2026.

"""Explicitly confirmed HTTP API for non-transactional market-risk alerts."""

from __future__ import annotations

import os
import threading
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from openjarvis.alerts import (
    AlertChannel,
    AlertRule,
    AlertService,
    AlertServiceError,
    AlertStore,
    AlertStoreError,
    render_alert,
)
from openjarvis.core.paths import get_config_dir
from openjarvis.fomo import ContractRiskFlags, MarketSnapshot, RiskAssessment

router = APIRouter(prefix="/v1/alerts", tags=["agi-procesor-alerts"])
_service_init_lock = threading.Lock()


class ContractRiskFlagsRequest(BaseModel):
    honeypot_detected: bool | None = None
    mint_authority_enabled: bool | None = None
    freeze_authority_enabled: bool | None = None
    transfer_restrictions: bool | None = None
    owner_can_change_fees: bool | None = None
    contract_unverified: bool | None = None
    source_data_stale: bool | None = None


class MarketSnapshotRequest(BaseModel):
    """Caller-supplied observation; this API never fetches or scrapes it."""

    symbol: str = Field(
        min_length=1,
        max_length=32,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$",
    )
    price_usd: Decimal = Field(gt=0)
    market_cap_usd: Decimal = Field(ge=0)
    liquidity_usd: Decimal = Field(ge=0)
    volume_24h_usd: Decimal = Field(ge=0)
    price_change_24h_pct: Decimal
    token_age_hours: Decimal = Field(ge=0)
    top_holders_pct: Decimal = Field(ge=0, le=100)
    chain: str = Field(default="unknown", min_length=1, max_length=64)
    contract_risks: ContractRiskFlagsRequest = Field(
        default_factory=ContractRiskFlagsRequest
    )
    observed_at: datetime | None = None
    source: str = Field(default="caller-supplied", min_length=1, max_length=256)


class RuleCreateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    symbol: str = Field(
        min_length=1,
        max_length=32,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$",
    )
    channels: list[Literal["email", "telegram", "ntfy", "sms"]] = Field(
        min_length=1,
        max_length=4,
    )
    enabled: bool = True
    watch_max_risk_score: int = Field(default=24, ge=0, le=100)
    avoid_min_risk_score: int = Field(default=75, ge=0, le=100)
    entry_price_at_or_below: Decimal | None = Field(default=None, gt=0)
    exit_price_at_or_below: Decimal | None = Field(default=None, gt=0)
    exit_price_at_or_above: Decimal | None = Field(default=None, gt=0)
    cooldown_minutes: int = Field(default=60, ge=15, le=43_200)
    activation_condition: str = Field(min_length=10, max_length=500)
    invalidation_condition: str = Field(min_length=10, max_length=500)
    confirm_rule_creation: Literal[True]


class RuleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    symbol: str | None = Field(
        default=None,
        min_length=1,
        max_length=32,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$",
    )
    channels: list[Literal["email", "telegram", "ntfy", "sms"]] | None = Field(
        default=None,
        min_length=1,
        max_length=4,
    )
    enabled: bool | None = None
    watch_max_risk_score: int | None = Field(default=None, ge=0, le=100)
    avoid_min_risk_score: int | None = Field(default=None, ge=0, le=100)
    entry_price_at_or_below: Decimal | None = Field(default=None, gt=0)
    exit_price_at_or_below: Decimal | None = Field(default=None, gt=0)
    exit_price_at_or_above: Decimal | None = Field(default=None, gt=0)
    cooldown_minutes: int | None = Field(default=None, ge=15, le=43_200)
    activation_condition: str | None = Field(
        default=None,
        min_length=10,
        max_length=500,
    )
    invalidation_condition: str | None = Field(
        default=None,
        min_length=10,
        max_length=500,
    )
    confirm_rule_update: Literal[True]


class RuleDeleteRequest(BaseModel):
    confirm_rule_deletion: Literal[True]


class EvaluationRequest(BaseModel):
    rule_id: str = Field(min_length=1, max_length=128)
    snapshot: MarketSnapshotRequest
    confirm_queue: Literal[True]


class DryRunRequest(BaseModel):
    rule_id: str = Field(min_length=1, max_length=128)
    snapshot: MarketSnapshotRequest


class SendRequest(BaseModel):
    confirm_send: Literal[True]


class DispatchPendingRequest(BaseModel):
    operator_scheduled: Literal[True]
    limit: int = Field(default=25, ge=1, le=100)


def _get_service(request: Request) -> AlertService:
    existing = getattr(request.app.state, "_agi_alert_service", None)
    if existing is not None:
        return existing
    with _service_init_lock:
        existing = getattr(request.app.state, "_agi_alert_service", None)
        if existing is not None:
            return existing
        default_path = get_config_dir() / "agi-procesor" / "alerts.json"
        path = Path(
            os.environ.get("AGI_PROCESOR_ALERTS_STORE_PATH", str(default_path))
        ).expanduser()
        service = AlertService(AlertStore(path))
        request.app.state._agi_alert_service = service
        return service


@router.get("/capabilities")
async def alert_capabilities(request: Request) -> dict[str, object]:
    service = _get_service(request)
    channel_capabilities = service.dispatcher.capabilities()
    return {
        "product": "AGI PROCESOR Alerts",
        "market_data_mode": "caller-supplied or separately authorised",
        "supported_states": ["watch", "caution", "avoid"],
        "supported_channels": [channel.value for channel in AlertChannel],
        "configured_channels": [
            name
            for name, status in channel_capabilities.items()
            if status["configured"] is True
        ],
        "channels": channel_capabilities,
        "persistence": "atomic-local-json",
        "dispatch_scheduler_enabled": _truthy(
            os.environ.get("AGI_PROCESOR_ALERTS_SCHEDULER_ENABLED", "false")
        ),
        "dispatch_scheduler_mode": "external-operator-triggered",
        "automatic_evaluation": False,
        "snapshot_freshness": {
            "required": True,
            "max_age_seconds": service.max_snapshot_age_seconds,
            "max_future_skew_seconds": service.max_future_skew_seconds,
        },
        "delivery_policy": {
            "atomic_claim": True,
            "lease_seconds": service.delivery_lease_seconds,
            "max_attempts_per_channel": service.max_attempts_per_channel,
            "retry_backoff_seconds": service.retry_backoff_seconds,
            "already_successful_channels_are_skipped": True,
            "crash_delivery_semantics": "at-least-once after lease expiry",
        },
        "sms_policy": {
            "default_max_chars": 300,
            "multipart_requires_explicit_opt_in": True,
        },
        "explicit_send_confirmation": True,
        "automated_trading": False,
        "wallet_access": False,
        "account_access": False,
        "human_decision_required": True,
        "execution_capability": "none",
    }


@router.get("/rules")
async def list_rules(request: Request) -> dict[str, object]:
    service = _get_service(request)
    return {
        "rules": [_rule_payload(service, rule) for rule in service.store.list_rules()]
    }


@router.post("/rules", status_code=201)
async def create_rule(body: RuleCreateRequest, request: Request) -> dict[str, object]:
    service = _get_service(request)
    symbol = body.symbol.strip().upper()
    try:
        rule = AlertRule.create(
            name=(body.name or f"{symbol} risk watch"),
            symbol=symbol,
            channels=tuple(AlertChannel(item) for item in body.channels),
            enabled=body.enabled,
            watch_max_risk_score=body.watch_max_risk_score,
            avoid_min_risk_score=body.avoid_min_risk_score,
            entry_price_at_or_below=body.entry_price_at_or_below,
            exit_price_at_or_below=body.exit_price_at_or_below,
            exit_price_at_or_above=body.exit_price_at_or_above,
            cooldown_seconds=body.cooldown_minutes * 60,
            activation_condition=body.activation_condition,
            invalidation_condition=body.invalidation_condition,
        )
        service.store.upsert_rule(rule)
    except (ValueError, AlertStoreError) as exc:
        raise _http_error(exc) from exc
    return {"rule": _rule_payload(service, rule)}


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    body: RuleUpdateRequest,
    request: Request,
) -> dict[str, object]:
    service = _get_service(request)
    existing = service.store.get_rule(rule_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Alert rule was not found")
    changes = body.model_dump(
        exclude_unset=True,
        exclude={"confirm_rule_update"},
    )
    nullable_thresholds = {
        "entry_price_at_or_below",
        "exit_price_at_or_below",
        "exit_price_at_or_above",
    }
    changes = {
        key: value
        for key, value in changes.items()
        if value is not None or key in nullable_thresholds
    }
    if "channels" in changes:
        changes["channels"] = tuple(AlertChannel(item) for item in changes["channels"])
    if "cooldown_minutes" in changes:
        changes["cooldown_seconds"] = changes.pop("cooldown_minutes") * 60
    if "symbol" in changes:
        changes["symbol"] = changes["symbol"].strip().upper()
    changes["updated_at"] = datetime.now(timezone.utc)
    try:
        updated = replace(existing, **changes)
        service.store.upsert_rule(updated)
    except (TypeError, ValueError, AlertStoreError) as exc:
        raise _http_error(exc) from exc
    return {"rule": _rule_payload(service, updated)}


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    body: RuleDeleteRequest,
    request: Request,
) -> dict[str, object]:
    try:
        removed = _get_service(request).store.delete_rule(rule_id)
    except AlertStoreError as exc:
        raise _http_error(exc) from exc
    if not removed:
        raise HTTPException(status_code=404, detail="Alert rule was not found")
    return {"deleted": True, "rule_id": rule_id}


@router.post("/dry-run")
async def dry_run(body: DryRunRequest, request: Request) -> dict[str, object]:
    """Evaluate without queueing, persistence, or delivery."""

    return _evaluate(body.rule_id, body.snapshot, _get_service(request), persist=False)


@router.post("/test-render")
async def test_render(body: DryRunRequest, request: Request) -> dict[str, object]:
    """Render a complete example without queueing or delivery."""

    result = _evaluate(
        body.rule_id,
        body.snapshot,
        _get_service(request),
        persist=False,
    )
    event = result["event"]
    assert isinstance(event, dict)
    from openjarvis.alerts import AlertEvent

    return {
        "dry_run": True,
        "message": render_alert(AlertEvent.from_dict(event)),
        "event": event,
    }


@router.post("/evaluate")
async def evaluate_and_queue(
    body: EvaluationRequest,
    request: Request,
) -> dict[str, object]:
    """Evaluate and persist to the queue after explicit confirmation."""

    return _evaluate(body.rule_id, body.snapshot, _get_service(request), persist=True)


@router.get("/history")
async def alert_history(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, object]:
    service = _get_service(request)
    history = [
        _event_payload(service, event)
        for event in service.store.list_events(limit=limit)
    ]
    return {"history": history, "count": len(history)}


@router.get("/events")
async def alert_events(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, object]:
    service = _get_service(request)
    events = [
        _event_payload(service, event)
        for event in service.store.list_events(limit=limit)
    ]
    return {"events": events, "count": len(events)}


@router.get("/events/{event_id}/render")
async def render_stored_event(event_id: str, request: Request) -> dict[str, object]:
    try:
        message = _get_service(request).render_event(event_id)
    except AlertServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"event_id": event_id, "message": message, "delivery_performed": False}


@router.post("/events/{event_id}/send")
async def send_stored_event(
    event_id: str,
    body: SendRequest,
    request: Request,
) -> dict[str, object]:
    service = _get_service(request)
    try:
        event, outcomes = await run_in_threadpool(
            service.send_event,
            event_id,
            confirm_send=body.confirm_send,
        )
    except AlertServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "event": _event_payload(service, event),
        "deliveries": [item.as_dict() for item in outcomes],
        "transaction_executed": False,
    }


@router.post("/dispatch-pending")
async def dispatch_pending(
    body: DispatchPendingRequest,
    request: Request,
) -> dict[str, object]:
    if not _truthy(os.environ.get("AGI_PROCESOR_ALERTS_SCHEDULER_ENABLED", "false")):
        raise HTTPException(status_code=409, detail="Operator scheduler is disabled")
    service = _get_service(request)
    try:
        outcomes = await run_in_threadpool(
            service.dispatch_pending,
            operator_scheduled=body.operator_scheduled,
            limit=body.limit,
        )
    except AlertServiceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "processed": len(outcomes),
        "results": list(outcomes),
        "transaction_executed": False,
    }


def _evaluate(
    rule_id: str,
    body: MarketSnapshotRequest,
    service: AlertService,
    *,
    persist: bool,
) -> dict[str, object]:
    rule = service.store.get_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Alert rule was not found")
    try:
        snapshot = _snapshot(body)
        result = service.evaluate(rule, snapshot, persist=persist)
    except (ValueError, AlertStoreError) as exc:
        raise _http_error(exc) from exc
    return {
        "dry_run": not persist,
        "queued": result.event.queue_status.value == "queued",
        "snapshot": snapshot.as_dict(),
        "assessment": _assessment_payload(result.assessment),
        "event": result.event.as_dict(),
        "transaction_executed": False,
    }


def _snapshot(body: MarketSnapshotRequest) -> MarketSnapshot:
    values = body.model_dump()
    risk_values = values.pop("contract_risks")
    if values["observed_at"] is None:
        values.pop("observed_at")
    return MarketSnapshot(
        **values,
        contract_risks=ContractRiskFlags(**risk_values),
    )


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
        "summary": assessment.summary,
        "disclaimer": assessment.disclaimer,
        "execution_capability": "none",
    }


def _rule_payload(service: AlertService, rule: AlertRule) -> dict[str, object]:
    payload = rule.as_dict()
    latest = next(
        (
            event
            for event in service.store.list_events(limit=1000)
            if event.rule_id == rule.rule_id
        ),
        None,
    )
    payload["last_disposition"] = None if latest is None else latest.state.value.upper()
    payload["last_evaluated_at"] = (
        None if latest is None else latest.evaluated_at.isoformat()
    )
    payload["condition_text_machine_evaluated"] = False
    payload["machine_evaluated_fields"] = [
        "symbol",
        "watch_max_risk_score",
        "avoid_min_risk_score",
        "entry_price_at_or_below",
        "exit_price_at_or_below",
        "exit_price_at_or_above",
    ]
    return payload


def _event_payload(service: AlertService, event) -> dict[str, object]:
    payload = event.as_dict()
    payload["disposition"] = event.state.value
    payload["deliveries"] = list(service.store.delivery_history(event.event_id))
    return payload


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AlertStoreError):
        return HTTPException(status_code=500, detail="Alert persistence failed safely")
    return HTTPException(status_code=422, detail=str(exc))


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


__all__ = ["router"]
