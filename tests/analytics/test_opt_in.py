"""Default-off analytics must not create an identity or initialise sending."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agi_procesor.analytics.client import AnalyticsClient
from agi_procesor.core.config import AgiConfig, AnalyticsConfig, load_config
from agi_procesor.server import analytics_routes


def test_missing_analytics_section_defaults_off(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[engine]\ndefault = "ollama"\n')
    assert load_config(path).analytics.enabled is False


def test_disabled_client_never_creates_id_or_initialises_sdk(
    tmp_path, monkeypatch
) -> None:
    init_sdk = MagicMock()
    monkeypatch.setattr(AnalyticsClient, "_init_sdk", init_sdk)
    cfg = AnalyticsConfig(anon_id_path=str(tmp_path / "anon_id"))
    client = AnalyticsClient(cfg)
    client.capture("app_opened", {"platform": "cli"})
    assert not client.enabled
    assert client.anon_id == ""
    assert not Path(cfg.anon_id_path).exists()
    init_sdk.assert_not_called()


@pytest.mark.parametrize("enabled", [False, True])
def test_identity_gates_frontend_and_id_creation(
    tmp_path, monkeypatch, enabled
) -> None:
    cfg = AgiConfig()
    cfg.analytics.enabled = enabled
    cfg.analytics.anon_id_path = str(tmp_path / "anon_id")
    monkeypatch.setattr(analytics_routes, "load_config", lambda: cfg)
    app = FastAPI()
    app.include_router(analytics_routes.router)
    response = TestClient(app).get("/v1/analytics/identity")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is enabled
    assert bool(data["key"]) is enabled
    assert bool(data["anon_id"]) is enabled
    assert Path(cfg.analytics.anon_id_path).exists() is enabled


@pytest.fixture(autouse=True)
def _configured_analytics_destination(monkeypatch):
    # AGI PROCESOR ships without an analytics destination; these tests cover the
    # consent and sharing flow once the owner of an installation configures one.
    monkeypatch.setenv("AGI_PROCESOR_ANALYTICS_HOST", "https://analytics.example.com")
    monkeypatch.setenv("AGI_PROCESOR_ANALYTICS_KEY", "phc_test_key")
