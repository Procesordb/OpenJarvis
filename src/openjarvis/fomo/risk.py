# Created by the AGI PROCESOR project in 2026.

"""Deterministic and explainable token-risk scoring for AGI PROCESOR."""

from __future__ import annotations

from decimal import Decimal

from openjarvis.fomo.models import (
    MarketSnapshot,
    RadarDisposition,
    RiskAssessment,
    RiskFlag,
    RiskLevel,
    RiskScenario,
)

EDUCATIONAL_DISCLAIMER = (
    "Educational market-risk analysis only. It is not investment advice, a "
    "promise of profit, or an instruction to buy or sell. Verify source data "
    "and make your own decision."
)


class FomoRiskScorer:
    """Score a caller-supplied snapshot without making network requests.

    The score is a transparent heuristic, not a price predictor.  Higher values
    mean that more observable risk factors are present.  Every point is backed
    by a human-readable flag returned with the assessment.
    """

    def assess(self, snapshot: MarketSnapshot) -> RiskAssessment:
        """Return a deterministic assessment for ``snapshot``."""

        flags: list[RiskFlag] = []
        self._score_liquidity(snapshot, flags)
        self._score_market_size(snapshot, flags)
        self._score_turnover(snapshot, flags)
        self._score_volatility(snapshot, flags)
        self._score_age(snapshot, flags)
        self._score_concentration(snapshot, flags)
        self._score_contract(snapshot, flags)

        raw_score = sum(flag.points for flag in flags)
        score = min(100, raw_score)
        level = self._risk_level(score)
        disposition = self._disposition(level)
        scenarios = self._scenarios(flags)

        summary = (
            f"{snapshot.symbol}: {level.value} observed risk ({score}/100); "
            f"radar disposition: {disposition.value}. "
            f"{len(flags)} explainable risk factor(s) found."
        )
        return RiskAssessment(
            symbol=snapshot.symbol,
            score=score,
            level=level,
            disposition=disposition,
            flags=tuple(flags),
            scenarios=scenarios,
            summary=summary,
            disclaimer=EDUCATIONAL_DISCLAIMER,
        )

    @staticmethod
    def _add(
        flags: list[RiskFlag],
        code: str,
        title: str,
        detail: str,
        points: int,
    ) -> None:
        flags.append(
            RiskFlag(code=code, title=title, detail=detail, points=points),
        )

    def _score_liquidity(
        self,
        snapshot: MarketSnapshot,
        flags: list[RiskFlag],
    ) -> None:
        liquidity = snapshot.liquidity_usd
        if liquidity == 0:
            self._add(
                flags,
                "liquidity_none",
                "No reported liquidity",
                "The supplied source reports zero USD liquidity.",
                40,
            )
        elif liquidity < Decimal("10000"):
            self._add(
                flags,
                "liquidity_critical",
                "Extremely thin liquidity",
                f"Reported liquidity is only ${liquidity}.",
                30,
            )
        elif liquidity < Decimal("50000"):
            self._add(
                flags,
                "liquidity_low",
                "Low liquidity",
                f"Reported liquidity is ${liquidity}.",
                20,
            )
        elif liquidity < Decimal("250000"):
            self._add(
                flags,
                "liquidity_limited",
                "Limited liquidity",
                f"Reported liquidity is ${liquidity}.",
                10,
            )

    def _score_market_size(
        self,
        snapshot: MarketSnapshot,
        flags: list[RiskFlag],
    ) -> None:
        market_cap = snapshot.market_cap_usd
        if market_cap < Decimal("100000"):
            self._add(
                flags,
                "market_cap_micro",
                "Micro-cap asset",
                f"Reported market capitalisation is ${market_cap}.",
                20,
            )
        elif market_cap < Decimal("500000"):
            self._add(
                flags,
                "market_cap_very_small",
                "Very small market capitalisation",
                f"Reported market capitalisation is ${market_cap}.",
                12,
            )
        elif market_cap < Decimal("2000000"):
            self._add(
                flags,
                "market_cap_small",
                "Small market capitalisation",
                f"Reported market capitalisation is ${market_cap}.",
                5,
            )

    def _score_turnover(
        self,
        snapshot: MarketSnapshot,
        flags: list[RiskFlag],
    ) -> None:
        ratio = snapshot.volume_to_liquidity_ratio
        if ratio is None:
            return
        if ratio > Decimal("10"):
            self._add(
                flags,
                "turnover_extreme",
                "Extreme volume-to-liquidity ratio",
                f"24h volume is {ratio:.2f}x reported liquidity.",
                15,
            )
        elif ratio > Decimal("5"):
            self._add(
                flags,
                "turnover_high",
                "High volume-to-liquidity ratio",
                f"24h volume is {ratio:.2f}x reported liquidity.",
                10,
            )
        elif ratio < Decimal("0.01"):
            self._add(
                flags,
                "turnover_dormant",
                "Very low trading activity",
                f"24h volume is only {ratio:.4f}x reported liquidity.",
                8,
            )

    def _score_volatility(
        self,
        snapshot: MarketSnapshot,
        flags: list[RiskFlag],
    ) -> None:
        change = abs(snapshot.price_change_24h_pct)
        if change > Decimal("100"):
            points = 15
            code = "volatility_extreme"
            title = "Extreme 24-hour price move"
        elif change > Decimal("50"):
            points = 10
            code = "volatility_high"
            title = "High 24-hour price move"
        elif change > Decimal("25"):
            points = 5
            code = "volatility_elevated"
            title = "Elevated 24-hour price move"
        else:
            return
        self._add(
            flags,
            code,
            title,
            f"Absolute 24h price change is {change}%.",
            points,
        )

    def _score_age(
        self,
        snapshot: MarketSnapshot,
        flags: list[RiskFlag],
    ) -> None:
        age = snapshot.token_age_hours
        if age < Decimal("24"):
            self._add(
                flags,
                "age_newborn",
                "Token is less than one day old",
                f"Reported age is {age} hour(s).",
                20,
            )
        elif age < Decimal("168"):
            self._add(
                flags,
                "age_new",
                "Token is less than one week old",
                f"Reported age is {age} hour(s).",
                12,
            )
        elif age < Decimal("720"):
            self._add(
                flags,
                "age_young",
                "Token is less than one month old",
                f"Reported age is {age} hour(s).",
                5,
            )

    def _score_concentration(
        self,
        snapshot: MarketSnapshot,
        flags: list[RiskFlag],
    ) -> None:
        concentration = snapshot.top_holders_pct
        if concentration > Decimal("80"):
            points = 25
            code = "holders_dominant"
            title = "Extreme holder concentration"
        elif concentration > Decimal("60"):
            points = 15
            code = "holders_concentrated"
            title = "High holder concentration"
        elif concentration > Decimal("40"):
            points = 8
            code = "holders_elevated"
            title = "Elevated holder concentration"
        else:
            return
        self._add(
            flags,
            code,
            title,
            f"Top holders control {concentration}% of reported supply.",
            points,
        )

    def _score_contract(
        self,
        snapshot: MarketSnapshot,
        flags: list[RiskFlag],
    ) -> None:
        contract = snapshot.contract_risks
        rules = (
            (
                contract.honeypot_detected,
                "contract_honeypot",
                "Honeypot behaviour detected",
                "The supplied contract-analysis source flagged honeypot behaviour.",
                100,
            ),
            (
                contract.transfer_restrictions,
                "contract_transfer_restricted",
                "Transfer restrictions detected",
                "The contract may prevent or selectively restrict transfers.",
                30,
            ),
            (
                contract.owner_can_change_fees,
                "contract_mutable_fees",
                "Owner can change fees",
                "The contract owner may be able to change transaction fees.",
                20,
            ),
            (
                contract.freeze_authority_enabled,
                "contract_freeze_authority",
                "Freeze authority is enabled",
                "An authority may be able to freeze token accounts.",
                15,
            ),
            (
                contract.mint_authority_enabled,
                "contract_mint_authority",
                "Mint authority is enabled",
                "An authority may be able to increase token supply.",
                12,
            ),
            (
                contract.contract_unverified,
                "contract_unverified",
                "Contract source is unverified",
                "The supplied source could not verify the deployed contract source.",
                10,
            ),
            (
                contract.source_data_stale,
                "data_stale",
                "Source data is stale",
                "The supplied source marked its contract data as stale.",
                8,
            ),
        )
        for enabled, code, title, detail, points in rules:
            if enabled is True:
                self._add(flags, code, title, detail, points)

        if contract.checked_count() == 0:
            self._add(
                flags,
                "contract_not_checked",
                "Contract checks unavailable",
                "No contract-risk facts were supplied; unknown does not mean safe.",
                8,
            )

    @staticmethod
    def _risk_level(score: int) -> RiskLevel:
        if score >= 75:
            return RiskLevel.CRITICAL
        if score >= 50:
            return RiskLevel.HIGH
        if score >= 25:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @staticmethod
    def _disposition(level: RiskLevel) -> RadarDisposition:
        if level is RiskLevel.CRITICAL:
            return RadarDisposition.AVOID
        if level is RiskLevel.HIGH:
            return RadarDisposition.CAUTION
        return RadarDisposition.WATCH

    @staticmethod
    def _scenarios(flags: list[RiskFlag]) -> tuple[RiskScenario, ...]:
        codes = {flag.code for flag in flags}
        scenarios: list[RiskScenario] = []
        if any(code.startswith("liquidity_") for code in codes):
            scenarios.append(
                RiskScenario(
                    name="Liquidity exit",
                    trigger=(
                        "Liquidity is withdrawn or a larger order reaches the pool."
                    ),
                    impact=(
                        "Severe slippage or inability to exit at the displayed price."
                    ),
                    control=(
                        "Do not rely on the quote; independently verify depth "
                        "and slippage."
                    ),
                ),
            )
        if any(code.startswith("holders_") for code in codes):
            scenarios.append(
                RiskScenario(
                    name="Concentrated-holder sell-off",
                    trigger="One or more dominant holders sell or transfer supply.",
                    impact="Abrupt repricing and reduced available liquidity.",
                    control=(
                        "Verify holder identities, vesting, and recent wallet "
                        "movements."
                    ),
                ),
            )
        contract_control_codes = codes - {"contract_not_checked"}
        if any(code.startswith("contract_") for code in contract_control_codes):
            scenarios.append(
                RiskScenario(
                    name="Contract-control event",
                    trigger=(
                        "A privileged contract capability is exercised or "
                        "blocks an exit."
                    ),
                    impact=(
                        "Unexpected fees, dilution, frozen funds, or failed transfers."
                    ),
                    control=(
                        "Require an independent contract audit before taking "
                        "financial risk."
                    ),
                ),
            )
        if "contract_not_checked" in codes or "data_stale" in codes:
            scenarios.append(
                RiskScenario(
                    name="Data-quality gap",
                    trigger="Required contract checks are missing or stale.",
                    impact="The risk score may omit a material contract capability.",
                    control=(
                        "Obtain fresh results from an authorised contract-analysis "
                        "source before relying on the assessment."
                    ),
                ),
            )
        if any(code.startswith("volatility_") for code in codes):
            scenarios.append(
                RiskScenario(
                    name="Momentum reversal",
                    trigger=(
                        "A rapid price move reverses as short-term demand disappears."
                    ),
                    impact="Large loss over a short interval.",
                    control=(
                        "Treat recent performance as risk evidence, not a "
                        "return forecast."
                    ),
                ),
            )
        if any(code.startswith("age_") for code in codes):
            scenarios.append(
                RiskScenario(
                    name="Unproven market",
                    trigger=(
                        "Early liquidity, token controls, or participants "
                        "change quickly."
                    ),
                    impact="Historical metrics cease to describe current conditions.",
                    control=(
                        "Wait for more history and repeat all checks before "
                        "any decision."
                    ),
                ),
            )
        return tuple(scenarios)


__all__ = ["EDUCATIONAL_DISCLAIMER", "FomoRiskScorer"]
