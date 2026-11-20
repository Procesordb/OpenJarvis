# Created by the AGI PROCESOR project in 2026.

"""Safe, local-only market risk and paper-trading primitives.

The package intentionally contains no Fomo login, scraper, wallet, exchange
client, order router, or automated trading implementation.
"""

from __future__ import annotations

from openjarvis.fomo.affiliate import (
    AFFILIATE_DISCLOSURE_EN,
    AFFILIATE_DISCLOSURE_PL,
    DEFAULT_REFERRAL_URL,
    AffiliateConfig,
)
from openjarvis.fomo.models import (
    ContractRiskFlags,
    MarketSnapshot,
    RadarDisposition,
    RiskAssessment,
    RiskFlag,
    RiskLevel,
    RiskScenario,
)
from openjarvis.fomo.paper import (
    PaperPortfolio,
    PaperPosition,
    PaperTrade,
    PaperTradingError,
    PaperTradingLedger,
    TradeSide,
)
from openjarvis.fomo.risk import EDUCATIONAL_DISCLAIMER, FomoRiskScorer

RiskScorer = FomoRiskScorer


def assess_market(snapshot: MarketSnapshot) -> RiskAssessment:
    """Assess one caller-supplied snapshot with the default scorer."""

    return FomoRiskScorer().assess(snapshot)


__all__ = [
    "AFFILIATE_DISCLOSURE_EN",
    "AFFILIATE_DISCLOSURE_PL",
    "DEFAULT_REFERRAL_URL",
    "EDUCATIONAL_DISCLAIMER",
    "AffiliateConfig",
    "ContractRiskFlags",
    "FomoRiskScorer",
    "MarketSnapshot",
    "PaperPortfolio",
    "PaperPosition",
    "PaperTrade",
    "PaperTradingError",
    "PaperTradingLedger",
    "RadarDisposition",
    "RiskAssessment",
    "RiskFlag",
    "RiskLevel",
    "RiskScenario",
    "RiskScorer",
    "TradeSide",
    "assess_market",
]
