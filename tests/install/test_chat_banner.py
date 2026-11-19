"""Tests for the chat startup banner."""

from __future__ import annotations

from pathlib import Path

from agi_procesor.cli import _bg_state
from agi_procesor.cli._chat_banner import render_startup_banner


def test_banner_empty_when_all_ready(
    tmp_agi_procesor_home: Path, write_model_marker
) -> None:
    (tmp_agi_procesor_home / ".state" / "extension-built").write_text("")
    write_model_marker("qwen3.5:9b", "ready")
    s = _bg_state.get_status()
    banner = render_startup_banner(s)
    assert banner == ""


def test_banner_shows_rust_building(tmp_agi_procesor_home: Path) -> None:
    """Pending rust ext (no marker file) is shown as 'building'."""
    s = _bg_state.get_status()  # all pending
    banner = render_startup_banner(s)
    assert "Rust extension" in banner
    assert "building" in banner.lower()


def test_banner_shows_model_downloading(
    tmp_agi_procesor_home: Path, write_model_marker
) -> None:
    (tmp_agi_procesor_home / ".state" / "extension-built").write_text("")
    write_model_marker("qwen3.5:9b", "downloading")
    s = _bg_state.get_status()
    banner = render_startup_banner(s)
    assert "qwen3.5:9b" in banner
    assert "downloading" in banner.lower()


def test_banner_shows_failed_in_dim_warning(tmp_agi_procesor_home: Path) -> None:
    (tmp_agi_procesor_home / ".state" / "extension-failed").write_text("error tail")
    s = _bg_state.get_status()
    banner = render_startup_banner(s)
    assert "failed" in banner.lower()
    assert "doctor" in banner.lower()
