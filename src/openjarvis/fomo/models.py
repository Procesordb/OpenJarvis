# Created by the AGI PROCESOR project in 2026.

"""Domain models for the AGI PROCESOR market-risk radar.

The models in this module are deliberately exchange-agnostic.  They describe
market observations supplied by a caller; they never fetch data, authenticate
to a trading account, or place a transaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

DecimalLike = Decimal | int | float | str


def as_decimal(value: DecimalLike, *, field_name: str) -> Decimal:
    """Convert a JSON-friendly numeric value to a finite ``Decimal``.

    Floats are converted through their string representation so callers do not
    accidentally import the binary floating-point approximation.
    """

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric, not boolean")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid decimal number") from exc
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class ContractRiskFlags:
    """Optional facts reported by an authorised contract-analysis source.

    ``None`` means that a fact was not checked.  It is intentionally distinct
    from ``False``, which means the source checked the condition and did not
    find it.
    """

    honeypot_detected: bool | None = None
    mint_authority_enabled: bool | None = None
    freeze_authority_enabled: bool | None = None
    transfer_restrictions: bool | None = None
    owner_can_change_fees: bool | None = None
    contract_unverified: bool | None = None
    source_data_stale: bool | None = None

    def checked_count(self) -> int:
        """Return the number of flags that were actually checked."""

        return sum(value is not None for value in self.as_dict().values())

    def as_dict(self) -> dict[str, bool | None]:
        """Return stable, serialisable flag names and values."""

        return {
            "honeypot_detected": self.honeypot_detected,
            "mint_authority_enabled": self.mint_authority_enabled,
            "freeze_authority_enabled": self.freeze_authority_enabled,
            "transfer_restrictions": self.transfer_restrictions,
            "owner_can_change_fees": self.owner_can_change_fees,
            "contract_unverified": self.contract_unverified,
            "source_data_stale": self.source_data_stale,
        }


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """A point-in-time market observation used for risk scoring."""

    symbol: str
    price_usd: DecimalLike
    market_cap_usd: DecimalLike
    liquidity_usd: DecimalLike
    volume_24h_usd: DecimalLike
    price_change_24h_pct: DecimalLike
    token_age_hours: DecimalLike
    top_holders_pct: DecimalLike
    chain: str = "unknown"
    contract_risks: ContractRiskFlags = field(default_factory=ContractRiskFlags)
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    source: str = "caller-supplied"

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not symbol or len(symbol) > 32:
            raise ValueError("symbol must contain between 1 and 32 characters")
        object.__setattr__(self, "symbol", symbol)

        chain = self.chain.strip().lower()
        if not chain:
            raise ValueError("chain must not be empty")
        object.__setattr__(self, "chain", chain)

        source = self.source.strip()
        if not source:
            raise ValueError("source must not be empty")
        object.__setattr__(self, "source", source)

        numeric_fields = (
            "price_usd",
            "market_cap_usd",
            "liquidity_usd",
            "volume_24h_usd",
            "price_change_24h_pct",
            "token_age_hours",
            "top_holders_pct",
        )
        for name in numeric_fields:
            value = as_decimal(getattr(self, name), field_name=name)
            object.__setattr__(self, name, value)

        if self.price_usd <= 0:
            raise ValueError("price_usd must be greater than zero")
        for name in (
            "market_cap_usd",
            "liquidity_usd",
            "volume_24h_usd",
            "token_age_hours",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if not Decimal("0") <= self.top_holders_pct <= Decimal("100"):
            raise ValueError("top_holders_pct must be between 0 and 100")
        if not isinstance(self.observed_at, datetime):
            raise ValueError("observed_at must be a datetime")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must include timezone information")
        if not isinstance(self.contract_risks, ContractRiskFlags):
            raise ValueError("contract_risks must be ContractRiskFlags")

    @property
    def volume_to_liquidity_ratio(self) -> Decimal | None:
        """Return 24-hour volume divided by liquidity, if defined."""

        if self.liquidity_usd == 0:
            return None
        return self.volume_24h_usd / self.liquidity_usd

    def as_dict(self) -> dict[str, Any]:
        """Return a lossless JSON-ready representation."""

        return {
            "symbol": self.symbol,
            "chain": self.chain,
            "price_usd": str(self.price_usd),
            "market_cap_usd": str(self.market_cap_usd),
            "liquidity_usd": str(self.liquidity_usd),
            "volume_24h_usd": str(self.volume_24h_usd),
            "price_change_24h_pct": str(self.price_change_24h_pct),
            "token_age_hours": str(self.token_age_hours),
            "top_holders_pct": str(self.top_holders_pct),
            "contract_risks": self.contract_risks.as_dict(),
            "observed_at": self.observed_at.isoformat(),
            "source": self.source,
        }


class RiskLevel(str, Enum):
    """Risk bands used by the deterministic scorer."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RadarDisposition(str, Enum):
    """Non-transactional radar labels; never a buy or sell instruction."""

    WATCH = "watch"
    CAUTION = "caution"
    AVOID = "avoid"


@dataclass(frozen=True, slots=True)
class RiskFlag:
    """One explainable component of a risk score."""

    code: str
    title: str
    detail: str
    points: int


@dataclass(frozen=True, slots=True)
class RiskScenario:
    """A plausible downside scenario and a corresponding safety control."""

    name: str
    trigger: str
    impact: str
    control: str


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Explainable result returned by :class:`FomoRiskScorer`."""

    symbol: str
    score: int
    level: RiskLevel
    disposition: RadarDisposition
    flags: tuple[RiskFlag, ...]
    scenarios: tuple[RiskScenario, ...]
    summary: str
    disclaimer: str


__all__ = [
    "ContractRiskFlags",
    "DecimalLike",
    "MarketSnapshot",
    "RadarDisposition",
    "RiskAssessment",
    "RiskFlag",
    "RiskLevel",
    "RiskScenario",
    "as_decimal",
]
