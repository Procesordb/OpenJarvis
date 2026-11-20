# Created by the AGI PROCESOR project in 2026.

"""Application service joining risk scoring, queueing, and opt-in delivery."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from openjarvis.alerts.dispatch import AlertDispatcher, DispatchResult, render_alert
from openjarvis.alerts.models import AlertEvent, AlertRule, QueueStatus
from openjarvis.alerts.store import AlertClaimError, AlertStore, AlertStoreError
from openjarvis.fomo import FomoRiskScorer, MarketSnapshot, RiskAssessment


class AlertServiceError(RuntimeError):
    """Raised for invalid state transitions at the alert service boundary."""


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    event: AlertEvent
    assessment: RiskAssessment
    persisted: bool


class AlertService:
    """Evaluate supplied snapshots; never fetch markets or execute a trade."""

    def __init__(
        self,
        store: AlertStore,
        *,
        dispatcher: AlertDispatcher | None = None,
        scorer: FomoRiskScorer | None = None,
        max_snapshot_age_seconds: int | None = None,
        max_future_skew_seconds: int | None = None,
        delivery_lease_seconds: int | None = None,
        max_attempts_per_channel: int | None = None,
        retry_backoff_seconds: int | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.dispatcher = dispatcher or AlertDispatcher()
        self.scorer = scorer or FomoRiskScorer()
        self.max_snapshot_age_seconds = max_snapshot_age_seconds or _bounded_env_int(
            "AGI_PROCESOR_ALERTS_MAX_SNAPSHOT_AGE_SECONDS",
            default=900,
            minimum=60,
            maximum=604_800,
        )
        self.max_future_skew_seconds = (
            max_future_skew_seconds
            if max_future_skew_seconds is not None
            else _bounded_env_int(
                "AGI_PROCESOR_ALERTS_MAX_FUTURE_SKEW_SECONDS",
                default=60,
                minimum=0,
                maximum=300,
            )
        )
        self.delivery_lease_seconds = delivery_lease_seconds or _bounded_env_int(
            "AGI_PROCESOR_ALERTS_DELIVERY_LEASE_SECONDS",
            default=120,
            minimum=30,
            maximum=3600,
        )
        self.max_attempts_per_channel = max_attempts_per_channel or _bounded_env_int(
            "AGI_PROCESOR_ALERTS_MAX_ATTEMPTS_PER_CHANNEL",
            default=3,
            minimum=1,
            maximum=10,
        )
        self.retry_backoff_seconds = (
            retry_backoff_seconds
            if retry_backoff_seconds is not None
            else _bounded_env_int(
                "AGI_PROCESOR_ALERTS_RETRY_BACKOFF_SECONDS",
                default=60,
                minimum=0,
                maximum=86_400,
            )
        )
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def evaluate(
        self,
        rule: AlertRule,
        snapshot: MarketSnapshot,
        *,
        persist: bool,
    ) -> EvaluationResult:
        from openjarvis.alerts.models import evaluate_alert_rule

        self._validate_snapshot_freshness(snapshot)
        assessment = self.scorer.assess(snapshot)
        event = evaluate_alert_rule(rule, snapshot, assessment)
        if persist:
            event = (
                self.store.enqueue(
                    event,
                    cooldown_seconds=rule.cooldown_seconds,
                )
                if rule.enabled
                else self.store.record_observation(event)
            )
        return EvaluationResult(event, assessment, persist)

    def render_event(self, event_id: str) -> str:
        event = self.store.get_event(event_id)
        if event is None:
            raise AlertServiceError("Alert event was not found")
        return render_alert(event)

    def send_event(
        self,
        event_id: str,
        *,
        confirm_send: bool,
    ) -> tuple[AlertEvent, tuple[DispatchResult, ...]]:
        if confirm_send is not True:
            raise AlertServiceError("Actual delivery requires confirm_send=true")
        try:
            event, lease_id = self.store.claim_delivery(
                event_id,
                lease_seconds=self.delivery_lease_seconds,
                now=self._now(),
            )
        except KeyError as exc:
            raise AlertServiceError("Alert event was not found") from exc
        except (AlertClaimError, AlertStoreError, ValueError) as exc:
            raise AlertServiceError(str(exc)) from exc

        successful = self.store.successful_channels(event_id)
        results: list[DispatchResult] = []
        delivered_now = False
        for channel in event.channels:
            if channel in successful:
                continue
            attempts = [
                item
                for item in self.store.delivery_history(event_id)
                if item.get("channel") == channel.value
            ]
            now = self._now()
            if len(attempts) >= self.max_attempts_per_channel:
                results.append(
                    DispatchResult(
                        channel,
                        False,
                        "Retry limit reached; operator review required",
                        now,
                    )
                )
                continue
            if attempts and attempts[-1].get("success") is not True:
                last_attempt = datetime.fromisoformat(attempts[-1]["attempted_at"])
                elapsed = (now - last_attempt).total_seconds()
                if elapsed < self.retry_backoff_seconds:
                    remaining = int(self.retry_backoff_seconds - elapsed)
                    results.append(
                        DispatchResult(
                            channel,
                            False,
                            f"Retry backoff active for {remaining} more second(s)",
                            now,
                        )
                    )
                    continue
            try:
                outcome = self.dispatcher.send(channel, event)
            except Exception as exc:  # noqa: BLE001 - custom adapters are isolated
                outcome = DispatchResult(
                    channel,
                    False,
                    f"Delivery adapter failed ({type(exc).__name__})",
                    now,
                )
            self.store.record_delivery(
                event_id=event.event_id,
                channel=channel,
                success=outcome.success,
                detail=outcome.detail,
                attempted_at=outcome.attempted_at,
            )
            results.append(outcome)
            delivered_now = delivered_now or outcome.success

        successful = self.store.successful_channels(event_id)
        if successful == set(event.channels):
            status = QueueStatus.SENT
        elif successful:
            status = QueueStatus.PARTIAL
        else:
            status = QueueStatus.FAILED
        unsuccessful = set(event.channels) - successful
        retry_exhausted = bool(unsuccessful) and all(
            len(
                [
                    item
                    for item in self.store.delivery_history(event_id)
                    if item.get("channel") == channel.value
                ]
            )
            >= self.max_attempts_per_channel
            for channel in unsuccessful
        )
        try:
            updated = self.store.complete_delivery(
                event_id,
                lease_id=lease_id,
                status=status,
                delivered_any=delivered_now,
                retry_exhausted=retry_exhausted,
                now=self._now(),
            )
        except (AlertClaimError, AlertStoreError, ValueError) as exc:
            raise AlertServiceError(str(exc)) from exc
        return updated, tuple(results)

    def dispatch_pending(
        self,
        *,
        operator_scheduled: bool,
        limit: int = 25,
    ) -> tuple[dict[str, object], ...]:
        """Operator-controlled scheduler hook; no scheduler starts implicitly."""

        if operator_scheduled is not True:
            raise AlertServiceError(
                "Scheduled delivery requires operator_scheduled=true"
            )
        pending = self.store.list_events(
            limit=limit,
            statuses={
                QueueStatus.QUEUED,
                QueueStatus.SENDING,
                QueueStatus.PARTIAL,
                QueueStatus.FAILED,
            },
        )
        outcomes: list[dict[str, object]] = []
        for event in reversed(pending):
            try:
                updated, deliveries = self.send_event(
                    event.event_id,
                    confirm_send=True,
                )
            except AlertServiceError as exc:
                outcomes.append(
                    {
                        "event_id": event.event_id,
                        "queue_status": event.queue_status.value,
                        "deliveries": [],
                        "error": str(exc),
                    }
                )
                continue
            outcomes.append(
                {
                    "event_id": event.event_id,
                    "queue_status": updated.queue_status.value,
                    "deliveries": [item.as_dict() for item in deliveries],
                }
            )
        return tuple(outcomes)

    def _validate_snapshot_freshness(self, snapshot: MarketSnapshot) -> None:
        now = self._now()
        observed_at = snapshot.observed_at.astimezone(timezone.utc)
        age_seconds = (now - observed_at).total_seconds()
        if age_seconds > self.max_snapshot_age_seconds:
            raise ValueError(
                "snapshot is stale; observed_at exceeds the configured maximum age"
            )
        if age_seconds < -self.max_future_skew_seconds:
            raise ValueError(
                "snapshot observed_at is too far in the future for configured skew"
            )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise AlertServiceError("Alert service clock must include timezone")
        return value.astimezone(timezone.utc)


def _bounded_env_int(
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


__all__ = [
    "AlertService",
    "AlertServiceError",
    "EvaluationResult",
]
