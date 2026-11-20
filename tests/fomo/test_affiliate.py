# Created by the AGI PROCESOR project in 2026.

"""Tests for safe public affiliate-link metadata."""

from __future__ import annotations

import pytest

from openjarvis.fomo import AffiliateConfig


def test_default_affiliate_metadata_is_link_only_and_disclosed() -> None:
    config = AffiliateConfig()
    metadata = config.public_metadata(language="pl")

    assert config.referral_code == "AGIPROCESOR"
    assert metadata["referral_url"] == "https://fomo.family/r/AGIPROCESOR"
    assert metadata["integration_mode"] == "link-only"
    assert metadata["automated_trading"] is False
    assert metadata["account_access"] is False
    assert metadata["contains_credentials"] is False
    assert "link afiliacyjny" in metadata["disclosure"]


def test_english_disclosure_is_available() -> None:
    disclosure = AffiliateConfig().public_metadata(language="en-US")["disclosure"]
    assert "affiliate link" in disclosure
    assert "not a promise of profit" in disclosure


@pytest.mark.parametrize(
    "url",
    [
        "http://fomo.family/r/AGIPROCESOR",
        "https://evil.example/r/AGIPROCESOR",
        "https://user:pass@fomo.family/r/AGIPROCESOR",
        "https://fomo.family/r/AGIPROCESOR?token=secret",
        "https://fomo.family/profile/AGIPROCESOR",
    ],
)
def test_rejects_unsafe_or_non_referral_urls(url: str) -> None:
    with pytest.raises(ValueError):
        AffiliateConfig(referral_url=url)


def test_public_link_can_be_overridden_from_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "AGI_PROCESOR_FOMO_REFERRAL_URL",
        "https://fomo.family/r/ANOTHER_CODE",
    )
    config = AffiliateConfig.from_env()
    assert config.referral_code == "ANOTHER_CODE"


def test_only_link_only_integration_is_permitted() -> None:
    with pytest.raises(ValueError, match="link-only"):
        AffiliateConfig(integration_mode="account-api")
