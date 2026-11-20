# Created by the AGI PROCESOR project in 2026.

"""Non-transactional alert domain models.

Rules are evaluated only against snapshots supplied by an authorised caller.
The resulting states describe observed risk; they are not orders, forecasts,
or promises of profit.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from openjarvis.fomo import MarketSnapshot, RadarDisposition, RiskAssessment
from openjarvis.fomo.models import DecimalLike, as_decimal

ALERT_DISCLAIMER = (
    "Educational market-risk alert only. It is not investment advice, a "
    "promise of profit, or an instruction to buy or sell. Source data may be "
    "wrong, delayed, or incomplete. Verify it independently and make your own "
    "decision. AGI PROCESOR cannot execute transactions."
)
_SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")


class AlertChannel(str, Enum):
    EMAIL = "email"
    TELEGRAM = "telegram"
    NTFY = "ntfy"
    SMS = "sms"


class ReviewAction(str, Enum):
    """Human review context; deliberately not a trading instruction."""

    ENTRY_REVIEW = "entry_review"
    MONITOR = "monitor"
    EXIT_REVIEW = "exit_review"


class QueueStatus(str, Enum):
    OBSERVED = "observed"
    QUEUED = "queued"
    SENDING = "sending"
    COOLDOWN_SUPPRESSED = "cooldown_suppressed"
    SENT = "sent"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AlertRule:
    """Explicit thresholds for one asset and one or more delivery channels."""

    rule_id: str
    name: str
    symbol: str
    channels: tuple[AlertChannel, ...]
    enabled: bool = True
    watch_max_risk_score: int = 24
    avoid_min_risk_score: int = 75
    entry_price_at_or_below: Decimal | None = None
    exit_price_at_or_below: Decimal | None = None
    exit_price_at_or_above: Decimal | None = None
    cooldown_seconds: int = 3600
    activation_condition: str = ""
    invalidation_condition: str = ""
    created_at: datetime = datetime.min.replace(tzinfo=timezone.utc)
    updated_at: datetime = datetime.min.replace(tzinfo=timezone.utc)

    def __post_init__(self) -> None:
        rule_id = self.rule_id.strip()
        if not rule_id or len(rule_id) > 128:
            raise ValueError("rule_id must contain between 1 and 128 characters")
        object.__setattr__(self, "rule_id", rule_id)

        name = self.name.strip()
        if not name or len(name) > 120:
            raise ValueError("name must contain between 1 and 120 characters")
        object.__setattr__(self, "name", name)

        symbol = self.symbol.strip().upper()
        if _SYMBOL_PATTERN.fullmatch(symbol) is None:
            raise ValueError(
                "symbol must start with an alphanumeric character and contain "
                "only letters, digits, dot, underscore, or hyphen"
            )
        object.__setattr__(self, "symbol", symbol)

        channels = tuple(dict.fromkeys(AlertChannel(item) for item in self.channels))
        if not channels:
            raise ValueError("at least one alert channel is required")
        object.__setattr__(self, "channels", channels)

        if not 0 <= self.watch_max_risk_score <= 100:
            raise ValueError("watch_max_risk_score must be between 0 and 100")
        if not 0 <= self.avoid_min_risk_score <= 100:
            raise ValueError("avoid_min_risk_score must be between 0 and 100")
        if self.watch_max_risk_score >= self.avoid_min_risk_score:
            raise ValueError(
                "watch_max_risk_score must be lower than avoid_min_risk_score"
            )
        if not 60 <= self.cooldown_seconds <= 2_592_000:
            raise ValueError("cooldown_seconds must be between 60 and 2592000")

        for field_name in (
            "entry_price_at_or_below",
            "exit_price_at_or_below",
            "exit_price_at_or_above",
        ):
            raw = getattr(self, field_name)
            if raw is None:
                continue
            value = as_decimal(raw, field_name=field_name)
            if value <= 0:
                raise ValueError(f"{field_name} must be greater than zero")
            object.__setattr__(self, field_name, value)

        for field_name in ("activation_condition", "invalidation_condition"):
            value = getattr(self, field_name).strip()
            if len(value) > 500:
                raise ValueError(f"{field_name} must be at most 500 characters")
            if _has_control_characters(value):
                raise ValueError(f"{field_name} must not contain control characters")
            object.__setattr__(self, field_name, value)

        for field_name in ("created_at", "updated_at"):
            value = getattr(self, field_name)
            if value.tzinfo is None:
                raise ValueError(f"{field_name} must include timezone information")

    @classmethod
    def create(
        cls,
        *,
        name: str,
        symbol: str,
        channels: tuple[AlertChannel, ...],
        **values: Any,
    ) -> AlertRule:
        now = datetime.now(timezone.utc)
        return cls(
            rule_id=uuid.uuid4().hex,
            name=name,
            symbol=symbol,
            channels=channels,
            created_at=now,
            updated_at=now,
            **values,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "symbol": self.symbol,
            "channels": [channel.value for channel in self.channels],
            "enabled": self.enabled,
            "watch_max_risk_score": self.watch_max_risk_score,
            "avoid_min_risk_score": self.avoid_min_risk_score,
            "entry_price_at_or_below": _decimal_text(self.entry_price_at_or_below),
            "exit_price_at_or_below": _decimal_text(self.exit_price_at_or_below),
            "exit_price_at_or_above": _decimal_text(self.exit_price_at_or_above),
            "cooldown_seconds": self.cooldown_seconds,
            "cooldown_minutes": self.cooldown_seconds // 60,
            "activation_condition": self.activation_condition,
            "invalidation_condition": self.invalidation_condition,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "execution_capability": "none",
        }

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> AlertRule:
        return cls(
            rule_id=str(values["rule_id"]),
            name=str(values["name"]),
            symbol=str(values["symbol"]),
            channels=tuple(AlertChannel(item) for item in values["channels"]),
            enabled=bool(values.get("enabled", True)),
            watch_max_risk_score=int(values.get("watch_max_risk_score", 24)),
            avoid_min_risk_score=int(values.get("avoid_min_risk_score", 75)),
            entry_price_at_or_below=_optional_decimal(
                values.get("entry_price_at_or_below")
            ),
            exit_price_at_or_below=_optional_decimal(
                values.get("exit_price_at_or_below")
            ),
            exit_price_at_or_above=_optional_decimal(
                values.get("exit_price_at_or_above")
            ),
            cooldown_seconds=int(values.get("cooldown_seconds", 3600)),
            activation_condition=str(values.get("activation_condition", "")),
            invalidation_condition=str(values.get("invalidation_condition", "")),
            created_at=datetime.fromisoformat(str(values["created_at"])),
            updated_at=datetime.fromisoformat(str(values["updated_at"])),
        )


@dataclass(frozen=True, slots=True)
class AlertEvent:
    """One explainable evaluation, optionally queued for human notification."""

    event_id: str
    rule_id: str
    symbol: str
    state: RadarDisposition
    review_action: ReviewAction
    queue_status: QueueStatus
    source: str
    observed_at: datetime
    evaluated_at: datetime
    price_usd: Decimal
    risk_score: int
    risk_level: str
    risk_flags: tuple[str, ...]
    condition: str
    invalidation_condition: str
    channels: tuple[AlertChannel, ...]
    fingerprint: str
    disclaimer: str = ALERT_DISCLAIMER

    def __post_init__(self) -> None:
        if _SYMBOL_PATTERN.fullmatch(self.symbol) is None:
            raise ValueError("event symbol contains unsupported characters")
        source = self.source.strip()
        if not source or len(source) > 256 or _has_control_characters(source):
            raise ValueError("event source must be 1-256 characters without controls")
        object.__setattr__(self, "source", source)
        if not 0 <= self.risk_score <= 100:
            raise ValueError("risk_score must be between 0 and 100")
        if self.price_usd <= 0:
            raise ValueError("price_usd must be greater than zero")
        for field_name in ("observed_at", "evaluated_at"):
            if getattr(self, field_name).tzinfo is None:
                raise ValueError(f"{field_name} must include timezone information")

    def with_status(self, status: QueueStatus) -> AlertEvent:
        return replace(self, queue_status=status)

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "rule_id": self.rule_id,
            "symbol": self.symbol,
            "state": self.state.value,
            "review_action": self.review_action.value,
            "queue_status": self.queue_status.value,
            "source": self.source,
            "observed_at": self.observed_at.isoformat(),
            "evaluated_at": self.evaluated_at.isoformat(),
            "price_usd": str(self.price_usd),
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risk_flags": list(self.risk_flags),
            "condition": self.condition,
            "invalidation_condition": self.invalidation_condition,
            "channels": [channel.value for channel in self.channels],
            "fingerprint": self.fingerprint,
            "disclaimer": self.disclaimer,
            "execution_capability": "none",
        }

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> AlertEvent:
        return cls(
            event_id=str(values["event_id"]),
            rule_id=str(values["rule_id"]),
            symbol=str(values["symbol"]),
            state=RadarDisposition(values["state"]),
            review_action=ReviewAction(values["review_action"]),
            queue_status=QueueStatus(values["queue_status"]),
            source=str(values["source"]),
            observed_at=datetime.fromisoformat(str(values["observed_at"])),
            evaluated_at=datetime.fromisoformat(str(values["evaluated_at"])),
            price_usd=as_decimal(values["price_usd"], field_name="price_usd"),
            risk_score=int(values["risk_score"]),
            risk_level=str(values["risk_level"]),
            risk_flags=tuple(str(item) for item in values.get("risk_flags", [])),
            condition=str(values["condition"]),
            invalidation_condition=str(values["invalidation_condition"]),
            channels=tuple(AlertChannel(item) for item in values["channels"]),
            fingerprint=str(values["fingerprint"]),
            disclaimer=str(values.get("disclaimer", ALERT_DISCLAIMER)),
        )


def evaluate_alert_rule(
    rule: AlertRule,
    snapshot: MarketSnapshot,
    assessment: RiskAssessment,
) -> AlertEvent:
    """Evaluate one rule without persistence, I/O, or transaction execution."""

    if snapshot.symbol != rule.symbol:
        raise ValueError(
            f"snapshot symbol {snapshot.symbol} does not match "
            f"rule symbol {rule.symbol}"
        )
    state, action, condition, invalidation = _classify(rule, snapshot, assessment)
    flag_codes = tuple(sorted(flag.code for flag in assessment.flags))
    stable_input = "|".join(
        (
            rule.rule_id,
            rule.updated_at.isoformat(),
            state.value,
            action.value,
            ",".join(flag_codes),
        )
    )
    fingerprint = hashlib.sha256(stable_input.encode("utf-8")).hexdigest()
    return AlertEvent(
        event_id=uuid.uuid4().hex,
        rule_id=rule.rule_id,
        symbol=snapshot.symbol,
        state=state,
        review_action=action,
        queue_status=QueueStatus.OBSERVED,
        source=snapshot.source,
        observed_at=snapshot.observed_at,
        evaluated_at=datetime.now(timezone.utc),
        price_usd=snapshot.price_usd,
        risk_score=assessment.score,
        risk_level=assessment.level.value,
        risk_flags=flag_codes,
        condition=condition,
        invalidation_condition=invalidation,
        channels=rule.channels,
        fingerprint=fingerprint,
    )


def _classify(
    rule: AlertRule,
    snapshot: MarketSnapshot,
    assessment: RiskAssessment,
) -> tuple[RadarDisposition, ReviewAction, str, str]:
    price = snapshot.price_usd
    exit_causes: list[str] = []
    if assessment.score >= rule.avoid_min_risk_score:
        exit_causes.append(
            f"risk {assessment.score}/100 reached avoid threshold "
            f"{rule.avoid_min_risk_score}"
        )
    if (
        assessment.disposition is RadarDisposition.AVOID
        and assessment.score < rule.avoid_min_risk_score
    ):
        exit_causes.append("the underlying risk scorer disposition is AVOID")
    if rule.exit_price_at_or_below is not None and price <= rule.exit_price_at_or_below:
        exit_causes.append(
            f"price ${price} is at or below ${rule.exit_price_at_or_below}"
        )
    if rule.exit_price_at_or_above is not None and price >= rule.exit_price_at_or_above:
        exit_causes.append(
            f"price ${price} is at or above ${rule.exit_price_at_or_above}"
        )
    if exit_causes:
        return (
            RadarDisposition.AVOID,
            ReviewAction.EXIT_REVIEW,
            _operator_context(
                "Exit-risk review triggered: " + "; ".join(exit_causes) + ".",
                rule.activation_condition,
            ),
            rule.invalidation_condition
            or (
                "Invalid only after a newer authorised snapshot no longer meets "
                "any exit-risk threshold and independent checks confirm the change."
            ),
        )

    entry_price_ok = (
        rule.entry_price_at_or_below is None or price <= rule.entry_price_at_or_below
    )
    if assessment.score <= rule.watch_max_risk_score and entry_price_ok:
        price_text = (
            "no entry price ceiling configured"
            if rule.entry_price_at_or_below is None
            else f"price ${price} is at or below ${rule.entry_price_at_or_below}"
        )
        return (
            RadarDisposition.WATCH,
            ReviewAction.ENTRY_REVIEW,
            _operator_context(
                (
                    "Entry-research review triggered: "
                    f"risk {assessment.score}/100 is at or below watch threshold "
                    f"{rule.watch_max_risk_score}; {price_text}."
                ),
                rule.activation_condition,
            ),
            rule.invalidation_condition
            or (
                "Invalid if a newer authorised snapshot raises risk above "
                f"{rule.watch_max_risk_score}, breaches an exit threshold, or "
                "material source facts cannot be independently verified."
            ),
        )

    parts = [
        f"risk {assessment.score}/100 lies between configured WATCH and AVOID bands"
    ]
    if not entry_price_ok:
        parts.append(
            f"price ${price} is above entry review ceiling "
            f"${rule.entry_price_at_or_below}"
        )
    return (
        RadarDisposition.CAUTION,
        ReviewAction.MONITOR,
        _operator_context(
            "Caution monitoring state: " + "; ".join(parts) + ".",
            rule.activation_condition,
        ),
        rule.invalidation_condition
        or "Re-evaluate when a newer authorised snapshot changes risk or price bands.",
    )


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _operator_context(generated: str, context: str) -> str:
    if not context:
        return generated
    return f"{generated} Operator note (not machine-evaluated): {context}"


def _has_control_characters(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _optional_decimal(value: DecimalLike | None) -> Decimal | None:
    if value is None:
        return None
    return as_decimal(value, field_name="threshold")


__all__ = [
    "ALERT_DISCLAIMER",
    "AlertChannel",
    "AlertEvent",
    "AlertRule",
    "QueueStatus",
    "ReviewAction",
    "evaluate_alert_rule",
]
