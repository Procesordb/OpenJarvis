# Created by the AGI PROCESOR project in 2026.

"""Local-only paper trading ledger.

This module simulates accounting; it has no exchange client, signing code,
wallet access, or transaction execution capability.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from openjarvis.fomo.models import DecimalLike, as_decimal


class PaperTradingError(ValueError):
    """Raised when a simulated trade or ledger file is invalid."""


class TradeSide(str, Enum):
    """Supported simulated trade directions."""

    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True, slots=True)
class PaperTrade:
    """Immutable record of a simulated fill."""

    trade_id: str
    symbol: str
    side: TradeSide
    quantity: Decimal
    price_usd: Decimal
    gross_value_usd: Decimal
    fee_usd: Decimal
    cash_delta_usd: Decimal
    realized_pnl_usd: Decimal
    executed_at: datetime
    note: str = ""

    def as_dict(self) -> dict[str, str]:
        """Return a lossless JSON-ready record."""

        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": str(self.quantity),
            "price_usd": str(self.price_usd),
            "gross_value_usd": str(self.gross_value_usd),
            "fee_usd": str(self.fee_usd),
            "cash_delta_usd": str(self.cash_delta_usd),
            "realized_pnl_usd": str(self.realized_pnl_usd),
            "executed_at": self.executed_at.isoformat(),
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class PaperPosition:
    """Read-only mark-to-market view of a simulated position."""

    symbol: str
    quantity: Decimal
    average_entry_price_usd: Decimal
    cost_basis_usd: Decimal
    mark_price_usd: Decimal
    market_value_usd: Decimal
    unrealized_pnl_usd: Decimal
    price_is_estimated: bool


@dataclass(frozen=True, slots=True)
class PaperPortfolio:
    """Read-only portfolio summary."""

    initial_cash_usd: Decimal
    cash_usd: Decimal
    market_value_usd: Decimal
    equity_usd: Decimal
    realized_pnl_usd: Decimal
    unrealized_pnl_usd: Decimal
    total_pnl_usd: Decimal
    positions: tuple[PaperPosition, ...]


@dataclass(slots=True)
class _OpenPosition:
    quantity: Decimal
    cost_basis_usd: Decimal


class PaperTradingLedger:
    """Thread-safe, optionally persistent simulated USD portfolio.

    Persistence uses a versioned local JSON file and an atomic replace.  The
    file contains simulated accounting data only; credentials and wallet data
    are neither accepted nor stored.
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        initial_cash_usd: DecimalLike = Decimal("10000"),
        *,
        storage_path: str | Path | None = None,
        default_fee_bps: DecimalLike = Decimal("45"),
    ) -> None:
        initial_cash = as_decimal(
            initial_cash_usd,
            field_name="initial_cash_usd",
        )
        fee_bps = as_decimal(default_fee_bps, field_name="default_fee_bps")
        if initial_cash < 0:
            raise PaperTradingError("initial_cash_usd must be non-negative")
        self._validate_fee_bps(fee_bps)

        self._lock = threading.RLock()
        self._storage_path = Path(storage_path) if storage_path is not None else None
        self._initial_cash_usd = initial_cash
        self._cash_usd = initial_cash
        self._default_fee_bps = fee_bps
        self._realized_pnl_usd = Decimal("0")
        self._positions: dict[str, _OpenPosition] = {}
        self._trades: list[PaperTrade] = []

        if self._storage_path is not None and self._storage_path.exists():
            self._load()

    @property
    def trades(self) -> tuple[PaperTrade, ...]:
        """Return an immutable view of the simulated trade history."""

        with self._lock:
            return tuple(self._trades)

    @property
    def cash_usd(self) -> Decimal:
        """Return currently available simulated cash."""

        with self._lock:
            return self._cash_usd

    def execute(
        self,
        symbol: str,
        side: TradeSide | str,
        quantity: DecimalLike,
        price_usd: DecimalLike,
        *,
        fee_bps: DecimalLike | None = None,
        executed_at: datetime | None = None,
        note: str = "",
    ) -> PaperTrade:
        """Record one simulated fill and persist it atomically.

        This method never contacts a broker, wallet, exchange, or Fomo.
        """

        normalized_symbol = self._normalize_symbol(symbol)
        normalized_side = self._normalize_side(side)
        normalized_quantity = as_decimal(quantity, field_name="quantity")
        normalized_price = as_decimal(price_usd, field_name="price_usd")
        normalized_fee_bps = (
            self._default_fee_bps
            if fee_bps is None
            else as_decimal(fee_bps, field_name="fee_bps")
        )
        if normalized_quantity <= 0:
            raise PaperTradingError("quantity must be greater than zero")
        if normalized_price <= 0:
            raise PaperTradingError("price_usd must be greater than zero")
        self._validate_fee_bps(normalized_fee_bps)

        timestamp = executed_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise PaperTradingError("executed_at must include timezone information")
        clean_note = note.strip()
        if len(clean_note) > 500:
            raise PaperTradingError("note must not exceed 500 characters")

        with self._lock:
            old_cash = self._cash_usd
            old_realized = self._realized_pnl_usd
            old_positions = {
                key: _OpenPosition(value.quantity, value.cost_basis_usd)
                for key, value in self._positions.items()
            }
            old_trades = list(self._trades)
            try:
                trade = self._apply_trade(
                    normalized_symbol,
                    normalized_side,
                    normalized_quantity,
                    normalized_price,
                    normalized_fee_bps,
                    timestamp,
                    clean_note,
                )
                self._trades.append(trade)
                self._persist()
            except Exception:
                self._cash_usd = old_cash
                self._realized_pnl_usd = old_realized
                self._positions = old_positions
                self._trades = old_trades
                raise
            return trade

    def portfolio(
        self,
        marks: Mapping[str, DecimalLike] | None = None,
    ) -> PaperPortfolio:
        """Return a mark-to-market view without changing ledger state.

        If a mark is missing, the average entry price is used and the position
        is labelled as estimated.  This avoids silently inventing profit or
        loss while still allowing a portfolio view without live market data.
        """

        normalized_marks = {
            self._normalize_symbol(symbol): as_decimal(
                price,
                field_name=f"mark[{symbol}]",
            )
            for symbol, price in (marks or {}).items()
        }
        if any(price <= 0 for price in normalized_marks.values()):
            raise PaperTradingError("all mark prices must be greater than zero")

        with self._lock:
            positions: list[PaperPosition] = []
            market_value = Decimal("0")
            unrealized = Decimal("0")
            for symbol in sorted(self._positions):
                position = self._positions[symbol]
                average = position.cost_basis_usd / position.quantity
                estimated = symbol not in normalized_marks
                mark = normalized_marks.get(symbol, average)
                value = position.quantity * mark
                position_unrealized = value - position.cost_basis_usd
                market_value += value
                unrealized += position_unrealized
                positions.append(
                    PaperPosition(
                        symbol=symbol,
                        quantity=position.quantity,
                        average_entry_price_usd=average,
                        cost_basis_usd=position.cost_basis_usd,
                        mark_price_usd=mark,
                        market_value_usd=value,
                        unrealized_pnl_usd=position_unrealized,
                        price_is_estimated=estimated,
                    ),
                )
            equity = self._cash_usd + market_value
            return PaperPortfolio(
                initial_cash_usd=self._initial_cash_usd,
                cash_usd=self._cash_usd,
                market_value_usd=market_value,
                equity_usd=equity,
                realized_pnl_usd=self._realized_pnl_usd,
                unrealized_pnl_usd=unrealized,
                total_pnl_usd=equity - self._initial_cash_usd,
                positions=tuple(positions),
            )

    def _apply_trade(
        self,
        symbol: str,
        side: TradeSide,
        quantity: Decimal,
        price: Decimal,
        fee_bps: Decimal,
        timestamp: datetime,
        note: str,
    ) -> PaperTrade:
        gross = quantity * price
        fee = gross * fee_bps / Decimal("10000")
        realized = Decimal("0")

        if side is TradeSide.BUY:
            total_cost = gross + fee
            if total_cost > self._cash_usd:
                raise PaperTradingError(
                    "insufficient simulated cash for purchase plus fee",
                )
            position = self._positions.get(symbol)
            if position is None:
                self._positions[symbol] = _OpenPosition(quantity, total_cost)
            else:
                position.quantity += quantity
                position.cost_basis_usd += total_cost
            cash_delta = -total_cost
        else:
            position = self._positions.get(symbol)
            if position is None or quantity > position.quantity:
                raise PaperTradingError("insufficient simulated position to sell")
            removed_cost = position.cost_basis_usd * quantity / position.quantity
            net_proceeds = gross - fee
            realized = net_proceeds - removed_cost
            position.quantity -= quantity
            position.cost_basis_usd -= removed_cost
            if position.quantity == 0:
                del self._positions[symbol]
            cash_delta = net_proceeds
            self._realized_pnl_usd += realized

        self._cash_usd += cash_delta
        return PaperTrade(
            trade_id=uuid.uuid4().hex,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price_usd=price,
            gross_value_usd=gross,
            fee_usd=fee,
            cash_delta_usd=cash_delta,
            realized_pnl_usd=realized,
            executed_at=timestamp,
            note=note,
        )

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        if not isinstance(symbol, str):
            raise PaperTradingError("symbol must be a string")
        normalized = symbol.strip().upper()
        if not normalized or len(normalized) > 32:
            raise PaperTradingError(
                "symbol must contain between 1 and 32 characters",
            )
        return normalized

    @staticmethod
    def _normalize_side(side: TradeSide | str) -> TradeSide:
        if isinstance(side, TradeSide):
            return side
        try:
            return TradeSide(str(side).strip().lower())
        except ValueError as exc:
            raise PaperTradingError("side must be 'buy' or 'sell'") from exc

    @staticmethod
    def _validate_fee_bps(fee_bps: Decimal) -> None:
        if not Decimal("0") <= fee_bps <= Decimal("10000"):
            raise PaperTradingError("fee_bps must be between 0 and 10000")

    def _state_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "initial_cash_usd": str(self._initial_cash_usd),
            "cash_usd": str(self._cash_usd),
            "default_fee_bps": str(self._default_fee_bps),
            "realized_pnl_usd": str(self._realized_pnl_usd),
            "positions": {
                symbol: {
                    "quantity": str(position.quantity),
                    "cost_basis_usd": str(position.cost_basis_usd),
                }
                for symbol, position in sorted(self._positions.items())
            },
            "trades": [trade.as_dict() for trade in self._trades],
            "metadata": {
                "mode": "paper-only",
                "contains_credentials": False,
            },
        }

    def _persist(self) -> None:
        if self._storage_path is None:
            return
        path = self._storage_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(
                    self._state_payload(),
                    handle,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _load(self) -> None:
        assert self._storage_path is not None
        try:
            with self._storage_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if data.get("schema_version") != self.SCHEMA_VERSION:
                raise PaperTradingError("unsupported paper ledger schema version")

            self._initial_cash_usd = as_decimal(
                data["initial_cash_usd"],
                field_name="initial_cash_usd",
            )
            self._cash_usd = as_decimal(data["cash_usd"], field_name="cash_usd")
            self._default_fee_bps = as_decimal(
                data["default_fee_bps"],
                field_name="default_fee_bps",
            )
            self._validate_fee_bps(self._default_fee_bps)
            self._realized_pnl_usd = as_decimal(
                data["realized_pnl_usd"],
                field_name="realized_pnl_usd",
            )
            self._positions = {
                self._normalize_symbol(symbol): _OpenPosition(
                    as_decimal(position["quantity"], field_name="quantity"),
                    as_decimal(
                        position["cost_basis_usd"],
                        field_name="cost_basis_usd",
                    ),
                )
                for symbol, position in data["positions"].items()
            }
            self._trades = [self._trade_from_dict(item) for item in data["trades"]]
        except PaperTradingError:
            raise
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PaperTradingError("invalid or unreadable paper ledger file") from exc

        if self._initial_cash_usd < 0 or self._cash_usd < 0:
            raise PaperTradingError("paper ledger contains invalid cash values")
        for position in self._positions.values():
            if position.quantity <= 0 or position.cost_basis_usd < 0:
                raise PaperTradingError("paper ledger contains an invalid position")

    @staticmethod
    def _trade_from_dict(data: Mapping[str, str]) -> PaperTrade:
        timestamp = datetime.fromisoformat(data["executed_at"])
        if timestamp.tzinfo is None:
            raise PaperTradingError("stored trade timestamp must include timezone")
        trade = PaperTrade(
            trade_id=data["trade_id"],
            symbol=PaperTradingLedger._normalize_symbol(data["symbol"]),
            side=PaperTradingLedger._normalize_side(data["side"]),
            quantity=as_decimal(data["quantity"], field_name="quantity"),
            price_usd=as_decimal(data["price_usd"], field_name="price_usd"),
            gross_value_usd=as_decimal(
                data["gross_value_usd"],
                field_name="gross_value_usd",
            ),
            fee_usd=as_decimal(data["fee_usd"], field_name="fee_usd"),
            cash_delta_usd=as_decimal(
                data["cash_delta_usd"],
                field_name="cash_delta_usd",
            ),
            realized_pnl_usd=as_decimal(
                data["realized_pnl_usd"],
                field_name="realized_pnl_usd",
            ),
            executed_at=timestamp,
            note=data.get("note", ""),
        )
        if trade.quantity <= 0 or trade.price_usd <= 0:
            raise PaperTradingError("stored trade contains invalid quantity or price")
        if trade.fee_usd < 0:
            raise PaperTradingError("stored trade contains a negative fee")
        return trade


__all__ = [
    "PaperPortfolio",
    "PaperPosition",
    "PaperTrade",
    "PaperTradingError",
    "PaperTradingLedger",
    "TradeSide",
]
