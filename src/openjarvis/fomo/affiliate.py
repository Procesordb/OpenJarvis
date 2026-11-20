# Created by the AGI PROCESOR project in 2026.

"""Link-only affiliate configuration for AGI PROCESOR.

No account credential, session token, wallet key, or automated Fomo access is
accepted by this module.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

DEFAULT_REFERRAL_URL = "https://fomo.family/r/AGIPROCESOR"
AFFILIATE_DISCLOSURE_PL = (
    "Materiał reklamowy / link afiliacyjny. AGI PROCESOR może otrzymać część "
    "opłat transakcyjnych, jeśli zarejestrujesz się przez ten link. Nie jest to "
    "obietnica zysku ani indywidualna rekomendacja inwestycyjna."
)
AFFILIATE_DISCLOSURE_EN = (
    "Advertising / affiliate link. AGI PROCESOR may receive a share of trading "
    "fees if you register through this link. This is not a promise of profit or "
    "personal investment advice."
)
_REFERRAL_PATH = re.compile(r"^/r/([A-Za-z0-9_-]{1,64})$")


@dataclass(frozen=True, slots=True)
class AffiliateConfig:
    """Validated public referral-link metadata."""

    referral_url: str = DEFAULT_REFERRAL_URL
    disclosure_pl: str = AFFILIATE_DISCLOSURE_PL
    disclosure_en: str = AFFILIATE_DISCLOSURE_EN
    integration_mode: str = "link-only"

    def __post_init__(self) -> None:
        parsed = urlparse(self.referral_url)
        if parsed.scheme != "https" or parsed.hostname != "fomo.family":
            raise ValueError(
                "referral_url must be an HTTPS link on fomo.family",
            )
        if parsed.username or parsed.password or parsed.port:
            raise ValueError("referral_url must not contain credentials or a port")
        if parsed.query or parsed.fragment or parsed.params:
            raise ValueError(
                "referral_url must not contain query parameters or fragments",
            )
        if _REFERRAL_PATH.fullmatch(parsed.path) is None:
            raise ValueError("referral_url must use the /r/<code> format")
        if not self.disclosure_pl.strip() or not self.disclosure_en.strip():
            raise ValueError("affiliate disclosures must not be empty")
        if self.integration_mode != "link-only":
            raise ValueError("only link-only affiliate integration is supported")

    @property
    def referral_code(self) -> str:
        """Return the public referral code from the validated URL."""

        match = _REFERRAL_PATH.fullmatch(urlparse(self.referral_url).path)
        assert match is not None
        return match.group(1)

    def public_metadata(self, *, language: str = "pl") -> dict[str, object]:
        """Return safe UI metadata with no secret or account fields."""

        disclosure = (
            self.disclosure_en
            if language.lower().startswith("en")
            else self.disclosure_pl
        )
        return {
            "referral_url": self.referral_url,
            "referral_code": self.referral_code,
            "disclosure": disclosure,
            "integration_mode": self.integration_mode,
            "automated_trading": False,
            "account_access": False,
            "contains_credentials": False,
        }

    @classmethod
    def from_env(cls) -> "AffiliateConfig":
        """Read the optional public link override from a non-secret env var."""

        return cls(
            referral_url=os.environ.get(
                "AGI_PROCESOR_FOMO_REFERRAL_URL",
                DEFAULT_REFERRAL_URL,
            ),
        )


__all__ = [
    "AFFILIATE_DISCLOSURE_EN",
    "AFFILIATE_DISCLOSURE_PL",
    "AffiliateConfig",
    "DEFAULT_REFERRAL_URL",
]
