# Created by the AGI PROCESOR project in 2026.

"""Atomic local persistence for alert rules, queue state, and deliveries."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from openjarvis.alerts.models import (
    AlertChannel,
    AlertEvent,
    AlertRule,
    QueueStatus,
)


class AlertStoreError(RuntimeError):
    """Raised when persisted alert state cannot be read or written safely."""


class AlertClaimError(AlertStoreError):
    """Raised when an event cannot be atomically claimed for delivery."""


class AlertStore:
    """A small multi-thread/process-safe JSON store with atomic replacement."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path).expanduser().resolve()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise AlertStoreError(
                f"Cannot create alert state directory at {self.path.parent}"
            ) from exc
        self._thread_lock = threading.RLock()
        self._file_lock = FileLock(str(self.path) + ".lock", timeout=10)

    def list_rules(self) -> tuple[AlertRule, ...]:
        state = self._read()
        rules = [AlertRule.from_dict(item) for item in state["rules"].values()]
        return tuple(sorted(rules, key=lambda item: item.created_at))

    def get_rule(self, rule_id: str) -> AlertRule | None:
        state = self._read()
        values = state["rules"].get(rule_id)
        return None if values is None else AlertRule.from_dict(values)

    def upsert_rule(self, rule: AlertRule) -> AlertRule:
        def mutate(state: dict[str, Any]) -> None:
            state["rules"][rule.rule_id] = rule.as_dict()

        self._mutate(mutate)
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        removed = False

        def mutate(state: dict[str, Any]) -> None:
            nonlocal removed
            removed = state["rules"].pop(rule_id, None) is not None

        self._mutate(mutate)
        return removed

    def enqueue(
        self,
        event: AlertEvent,
        *,
        cooldown_seconds: int,
        now: datetime | None = None,
    ) -> AlertEvent:
        """Persist an event, suppressing a duplicate inside its cooldown."""

        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must include timezone information")
        stored = event

        def mutate(state: dict[str, Any]) -> None:
            nonlocal stored
            previous_text = state["cooldowns"].get(event.fingerprint)
            suppressed = False
            if previous_text is not None:
                previous = datetime.fromisoformat(str(previous_text))
                suppressed = (current - previous).total_seconds() < cooldown_seconds
            pending_id = state["pending_fingerprints"].get(event.fingerprint)
            if pending_id is not None:
                pending_values = state["events"].get(pending_id)
                if pending_values is None:
                    state["pending_fingerprints"].pop(event.fingerprint, None)
                else:
                    pending_status = QueueStatus(pending_values["queue_status"])
                    if pending_status in {
                        QueueStatus.QUEUED,
                        QueueStatus.SENDING,
                        QueueStatus.PARTIAL,
                        QueueStatus.FAILED,
                    }:
                        suppressed = True
                    else:
                        state["pending_fingerprints"].pop(event.fingerprint, None)
            status = (
                QueueStatus.COOLDOWN_SUPPRESSED if suppressed else QueueStatus.QUEUED
            )
            stored = event.with_status(status)
            state["events"][stored.event_id] = stored.as_dict()
            if not suppressed:
                state["pending_fingerprints"][event.fingerprint] = event.event_id

        self._mutate(mutate)
        return stored

    def claim_delivery(
        self,
        event_id: str,
        *,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> tuple[AlertEvent, str]:
        """Atomically claim an event so concurrent senders cannot duplicate it."""

        if not 30 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 30 and 3600")
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must include timezone information")
        claimed: AlertEvent | None = None
        lease_id = uuid.uuid4().hex

        def mutate(state: dict[str, Any]) -> None:
            nonlocal claimed
            values = state["events"].get(event_id)
            if values is None:
                raise KeyError(event_id)
            event = AlertEvent.from_dict(values)
            existing_claim = state["claims"].get(event_id)
            if event.queue_status is QueueStatus.SENDING and existing_claim:
                expires_at = datetime.fromisoformat(existing_claim["expires_at"])
                if expires_at > current:
                    raise AlertClaimError(
                        "Alert event already has an active send lease"
                    )
            elif event.queue_status not in {
                QueueStatus.QUEUED,
                QueueStatus.PARTIAL,
                QueueStatus.FAILED,
                QueueStatus.SENDING,
            }:
                raise AlertClaimError(
                    f"Event in {event.queue_status.value} state is not sendable"
                )

            claimed = event.with_status(QueueStatus.SENDING)
            state["events"][event_id] = claimed.as_dict()
            state["claims"][event_id] = {
                "lease_id": lease_id,
                "claimed_at": current.isoformat(),
                "expires_at": (current + timedelta(seconds=lease_seconds)).isoformat(),
            }

        self._mutate(mutate)
        if claimed is None:  # pragma: no cover - guarded by mutation
            raise AlertStoreError("Delivery claim did not produce an event")
        return claimed, lease_id

    def complete_delivery(
        self,
        event_id: str,
        *,
        lease_id: str,
        status: QueueStatus,
        delivered_any: bool,
        retry_exhausted: bool,
        now: datetime | None = None,
    ) -> AlertEvent:
        """Finish a claim and start cooldown only after a real delivery."""

        if status not in {QueueStatus.SENT, QueueStatus.PARTIAL, QueueStatus.FAILED}:
            raise ValueError("completion status must be sent, partial, or failed")
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must include timezone information")
        completed: AlertEvent | None = None

        def mutate(state: dict[str, Any]) -> None:
            nonlocal completed
            values = state["events"].get(event_id)
            claim = state["claims"].get(event_id)
            if values is None:
                raise KeyError(event_id)
            if claim is None or claim.get("lease_id") != lease_id:
                raise AlertClaimError(
                    "Alert delivery lease is missing or no longer owned"
                )
            event = AlertEvent.from_dict(values)
            if event.queue_status is not QueueStatus.SENDING:
                raise AlertClaimError("Alert event is no longer in sending state")
            completed = event.with_status(status)
            state["events"][event_id] = completed.as_dict()
            state["claims"].pop(event_id, None)
            if delivered_any:
                state["cooldowns"][event.fingerprint] = current.isoformat()
            if status is QueueStatus.SENT or retry_exhausted:
                if state["pending_fingerprints"].get(event.fingerprint) == event_id:
                    state["pending_fingerprints"].pop(event.fingerprint, None)

        self._mutate(mutate)
        if completed is None:  # pragma: no cover - guarded by mutation
            raise AlertStoreError("Delivery completion did not produce an event")
        return completed

    def record_observation(self, event: AlertEvent) -> AlertEvent:
        """Persist a disabled-rule or otherwise non-queued observation."""

        observed = event.with_status(QueueStatus.OBSERVED)

        def mutate(state: dict[str, Any]) -> None:
            state["events"][observed.event_id] = observed.as_dict()

        self._mutate(mutate)
        return observed

    def get_event(self, event_id: str) -> AlertEvent | None:
        state = self._read()
        values = state["events"].get(event_id)
        return None if values is None else AlertEvent.from_dict(values)

    def list_events(
        self,
        *,
        limit: int = 100,
        statuses: set[QueueStatus] | None = None,
    ) -> tuple[AlertEvent, ...]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        state = self._read()
        events = [AlertEvent.from_dict(item) for item in state["events"].values()]
        if statuses is not None:
            events = [item for item in events if item.queue_status in statuses]
        events.sort(key=lambda item: item.evaluated_at, reverse=True)
        return tuple(events[:limit])

    def update_event_status(
        self,
        event_id: str,
        status: QueueStatus,
    ) -> AlertEvent:
        result: AlertEvent | None = None

        def mutate(state: dict[str, Any]) -> None:
            nonlocal result
            values = state["events"].get(event_id)
            if values is None:
                raise KeyError(event_id)
            result = AlertEvent.from_dict(values).with_status(status)
            state["events"][event_id] = result.as_dict()

        self._mutate(mutate)
        if result is None:  # pragma: no cover - guarded by the mutation above
            raise AlertStoreError("event status update did not produce a result")
        return result

    def record_delivery(
        self,
        *,
        event_id: str,
        channel: AlertChannel,
        success: bool,
        detail: str,
        attempted_at: datetime,
    ) -> None:
        if attempted_at.tzinfo is None:
            raise ValueError("attempted_at must include timezone information")

        def mutate(state: dict[str, Any]) -> None:
            if event_id not in state["events"]:
                raise KeyError(event_id)
            state["deliveries"].append(
                {
                    "event_id": event_id,
                    "channel": channel.value,
                    "success": bool(success),
                    "detail": detail[:300],
                    "attempted_at": attempted_at.isoformat(),
                }
            )

        self._mutate(mutate)

    def delivery_history(self, event_id: str) -> tuple[dict[str, Any], ...]:
        state = self._read()
        return tuple(
            dict(item)
            for item in state["deliveries"]
            if item.get("event_id") == event_id
        )

    def successful_channels(self, event_id: str) -> set[AlertChannel]:
        return {
            AlertChannel(item["channel"])
            for item in self.delivery_history(event_id)
            if item.get("success") is True
        }

    def _read(self) -> dict[str, Any]:
        try:
            with self._thread_lock, self._file_lock:
                return self._read_unlocked()
        except Timeout as exc:
            raise AlertStoreError("Timed out waiting for the alert state lock") from exc

    def _mutate(self, callback: Any) -> None:
        try:
            with self._thread_lock, self._file_lock:
                state = self._read_unlocked()
                callback(state)
                self._write_unlocked(state)
        except Timeout as exc:
            raise AlertStoreError("Timed out waiting for the alert state lock") from exc

    def _read_unlocked(self) -> dict[str, Any]:
        if not self.path.exists():
            return _empty_state()
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise AlertStoreError(
                f"Cannot read alert state at {self.path}; it was not overwritten"
            ) from exc
        if not isinstance(state, dict) or state.get("schema_version") != 1:
            raise AlertStoreError("Unsupported or invalid alert state schema")
        for key, expected_type in (
            ("rules", dict),
            ("events", dict),
            ("deliveries", list),
            ("cooldowns", dict),
        ):
            if not isinstance(state.get(key), expected_type):
                raise AlertStoreError(f"Invalid alert state field: {key}")
        state.setdefault("claims", {})
        state.setdefault("pending_fingerprints", {})
        if not isinstance(state["claims"], dict):
            raise AlertStoreError("Invalid alert state field: claims")
        if not isinstance(state["pending_fingerprints"], dict):
            raise AlertStoreError("Invalid alert state field: pending_fingerprints")
        return state

    def _write_unlocked(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
                temporary_path = Path(handle.name)
            try:
                temporary_path.chmod(0o600)
            except OSError:
                pass
            os.replace(temporary_path, self.path)
        except OSError as exc:
            raise AlertStoreError(f"Cannot persist alert state at {self.path}") from exc
        finally:
            if temporary_path is not None and temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    pass


def _empty_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "rules": {},
        "events": {},
        "deliveries": [],
        "cooldowns": {},
        "claims": {},
        "pending_fingerprints": {},
    }


__all__ = ["AlertClaimError", "AlertStore", "AlertStoreError"]
