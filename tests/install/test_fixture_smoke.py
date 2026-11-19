"""Smoke test that the tmp_agi_procesor_home fixture works."""

from __future__ import annotations

from pathlib import Path

from agi_procesor.core import config as config_mod


def test_fixture_redirects_default_config_dir(tmp_agi_procesor_home: Path) -> None:
    assert config_mod.DEFAULT_CONFIG_DIR == tmp_agi_procesor_home
    assert tmp_agi_procesor_home.exists()
    assert (tmp_agi_procesor_home / ".state").exists()
    assert (tmp_agi_procesor_home / ".state" / "models").exists()


def test_fixture_redirects_config_path(tmp_agi_procesor_home: Path) -> None:
    assert config_mod.DEFAULT_CONFIG_PATH == tmp_agi_procesor_home / "config.toml"
