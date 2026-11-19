"""AGI PROCESOR defaults: nothing leaves the machine unless the owner configures it."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest

from agi_procesor.cli import _analytics_consent, _version_check
from agi_procesor.core.config import AnalyticsConfig

ROOT = Path(__file__).resolve().parents[2]


def test_analytics_has_no_default_destination(monkeypatch):
    monkeypatch.delenv("AGI_PROCESOR_ANALYTICS_HOST", raising=False)
    monkeypatch.delenv("AGI_PROCESOR_ANALYTICS_KEY", raising=False)
    cfg = AnalyticsConfig()
    assert cfg.host == ""
    assert cfg.key == ""
    assert cfg.enabled is False


def test_no_consent_question_without_destination(monkeypatch, capsys):
    monkeypatch.delenv("AGI_PROCESOR_ANALYTICS_HOST", raising=False)
    monkeypatch.delenv("AGI_PROCESOR_ANALYTICS_KEY", raising=False)

    class _Tty(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr(
        _analytics_consent.click, "get_text_stream", lambda name: _Tty("y\n")
    )
    assert _analytics_consent.ask_analytics_consent() is False
    assert "PostHog" not in capsys.readouterr().err


def test_version_check_is_off_without_release_feed(monkeypatch):
    monkeypatch.setattr(_version_check, "_PYPI_API", "")
    assert _version_check._check_disabled() is True


def test_desktop_app_has_no_upstream_updater():
    conf_path = ROOT / "frontend/src-tauri/tauri.conf.json"
    conf = json.loads(conf_path.read_text(encoding="utf-8"))
    assert conf["productName"] == "AGI-PROCESOR"
    assert conf["identifier"] == "com.agiprocesor.desktop"
    updater = conf["plugins"]["updater"]
    assert updater["active"] is False
    assert updater["endpoints"] == []


def test_leaderboard_has_no_default_service():
    src = (ROOT / "frontend/src/lib/supabase.ts").read_text(encoding="utf-8")
    assert "supabase.co" not in src
    assert "SUPABASE_URL.length > 0 && SUPABASE_ANON_KEY.length > 0" in src


def test_package_and_cli_names():
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'(?m)^name = "agi-procesor"$', py)
    assert re.search(r'(?m)^agi = "agi_procesor\.cli:main"$', py)


# The GitHub repository keeps its current name for now and the credits name the
# upstream project; everything else has to say AGI PROCESOR.
_ALLOWED = re.compile(
    r"(?i:built on \[?OpenJarvis\]?)"
    r"|upstream OpenJarvis"
    r"|github\.com/open-jarvis/OpenJarvis"
    r"|openjarvis\.stanford\.edu"
    r"|saadfalcon2026openjarvis\w*"
    r"|title=\{OpenJarvis: Personal AI, On Personal Devices\}"
    r"|Procesordb/OpenJarvis"
    r"|procesordb\.github\.io/OpenJarvis"
    r"|youdotcom-integration/open-jarvis-openjarvis"
)
_KEEP = {
    "LICENSE",
    "NOTICE",
    "CHANGELOG.md",
    "README.md",
    "tests/branding/test_agi_procesor_defaults.py",
}
_KEEP_DIRS = ("scripts/rebrand/",)
_SKIP_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "target",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}
_TOPS = ["src", "frontend/src", "rust", "configs", "deploy", "scripts", "docs", "tests"]


def _lines(top):
    base = ROOT / top
    if not base.exists():
        pytest.skip(top + " is not in this checkout")
    for p in base.rglob("*"):
        if not p.is_file() or _SKIP_PARTS & set(p.parts):
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel in _KEEP or rel.startswith(_KEEP_DIRS):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            yield f"{rel}:{n}: {line.strip()[:120]}", line


@pytest.mark.parametrize("top", _TOPS + [".github"])
def test_no_old_project_name(top):
    old = "jar" + "vis"
    hits = [
        where for where, line in _lines(top) if old in _ALLOWED.sub("", line).lower()
    ]
    assert not hits, "old project name left in:\n" + "\n".join(hits[:40])


# The upstream project's own analytics endpoint and key and its leaderboard
# database, split so that this file does not contain them either.
_UPSTREAM_SERVICES = (
    "34.231.106" + ".201",
    "phc_" + "ysKu72",
    "mtbtgpwzr" + "bostweaanpr",
)


@pytest.mark.parametrize("top", _TOPS + [".github"])
def test_no_upstream_service_endpoints(top):
    hits = [
        where
        for where, line in _lines(top)
        if any(s in line for s in _UPSTREAM_SERVICES)
    ]
    assert not hits, "upstream service left in:\n" + "\n".join(hits[:40])


_PROMOTION = re.compile(r"(?i)giveaway|win a mac mini|chance to win")


@pytest.mark.parametrize("top", ["src", "frontend/src", "docs"])
def test_no_upstream_giveaway(top):
    hits = [where for where, line in _lines(top) if _PROMOTION.search(line)]
    assert not hits, "upstream promotion left in:\n" + "\n".join(hits[:40])


def test_installer_has_no_default_analytics_destination():
    src = (ROOT / "scripts/install/install.sh").read_text(encoding="utf-8")
    assert 'ANALYTICS_HOST="${AGI_PROCESOR_ANALYTICS_HOST:-}"' in src
    assert 'ANALYTICS_KEY="${AGI_PROCESOR_ANALYTICS_KEY:-}"' in src


def test_init_offers_the_agi_preset():
    from click.testing import CliRunner

    from agi_procesor.cli import cli

    result = CliRunner().invoke(cli, ["init", "--help"])
    assert result.exit_code == 0
    assert "inteligencja-agi" in result.output
