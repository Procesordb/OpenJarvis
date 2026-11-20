# Modified by the AGI PROCESOR project in 2026; see AGI_PROCESSOR_CHANGES.md.

"""Smoke tests for `jarvis self-update`.

Focus on the surface that's easy to corrupt (output formatting, exit
codes, --check short-circuit). We don't actually run pip/uv from a
unit test; the subprocess call is mocked.
"""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from openjarvis.cli import self_update_cmd
from openjarvis.cli._install_detect import InstallInfo
from openjarvis.cli.self_update_cmd import self_update


def _mock_info(kind: str = "pypi") -> InstallInfo:
    return InstallInfo(
        kind=kind,
        upgrade_command={
            "pypi": "pip install --upgrade openjarvis",
            "uv-tool": "uv tool upgrade openjarvis",
            "editable-git": "jarvis self-update",
            "unknown": "pip install --upgrade openjarvis",
        }[kind],
        repo_root=Path("/tmp/repo with spaces") if kind == "editable-git" else None,
    )


@pytest.fixture
def legacy_updates(monkeypatch):
    """Exercise retained upstream code without enabling it in production."""
    monkeypatch.setattr(self_update_cmd, "_UPSTREAM_SELF_UPDATE_ENABLED", True)


def test_branded_fork_blocks_upstream_update_before_detection_or_subprocess():
    with (
        patch("openjarvis.cli.self_update_cmd.detect_install") as detect,
        patch("openjarvis.cli.self_update_cmd.subprocess.run") as run,
    ):
        result = CliRunner().invoke(self_update, ["--yes"])

    assert result.exit_code != 0
    assert "Automatic self-update is disabled" in result.output
    assert "AGI PROCESOR" in result.output
    detect.assert_not_called()
    run.assert_not_called()


def test_check_flag_prints_command_and_exits_clean(legacy_updates):
    with patch(
        "openjarvis.cli.self_update_cmd.detect_install",
        return_value=_mock_info("pypi"),
    ):
        runner = CliRunner()
        result = runner.invoke(self_update, ["--check"])
    assert result.exit_code == 0
    assert "pip install --upgrade openjarvis" in result.output
    assert "Install method: pypi" in result.output


@pytest.mark.parametrize("kind", ["pypi", "editable-git"])
def test_check_does_not_invoke_subprocess(kind, legacy_updates):
    with (
        patch(
            "openjarvis.cli.self_update_cmd.detect_install",
            return_value=_mock_info(kind),
        ),
        patch("openjarvis.cli.self_update_cmd.subprocess.run") as mock_run,
    ):
        CliRunner().invoke(self_update, ["--check"])
    mock_run.assert_not_called()


def test_yes_skips_confirmation_and_runs(legacy_updates):
    mock_proc = MagicMock(returncode=0)
    with (
        patch(
            "openjarvis.cli.self_update_cmd.detect_install",
            return_value=_mock_info("pypi"),
        ),
        patch(
            "openjarvis.cli.self_update_cmd.subprocess.run",
            return_value=mock_proc,
        ) as mock_run,
    ):
        result = CliRunner().invoke(self_update, ["-y"])
    assert result.exit_code == 0
    mock_run.assert_called_once()
    # PyPI path uses shlex.split (no shell=True)
    args, kwargs = mock_run.call_args
    assert kwargs.get("shell") is not True
    assert args[0] == ["pip", "install", "--upgrade", "openjarvis"]


@pytest.mark.parametrize("shallow", ["true", "false"])
def test_editable_git_repairs_history_and_rebuilds_active_venv(
    monkeypatch, shallow, legacy_updates
):
    """Recover tags before rebuilding even when Git has no new commits."""
    mock_proc = CompletedProcess([], 0, stdout=shallow + "\n", stderr="")
    monkeypatch.setattr("openjarvis.cli.self_update_cmd.sys.prefix", "/managed venv")
    monkeypatch.setattr(
        "openjarvis.cli.self_update_cmd.sys.executable", "/managed venv/bin/python"
    )
    with (
        patch(
            "openjarvis.cli.self_update_cmd.detect_install",
            return_value=_mock_info("editable-git"),
        ),
        patch(
            "openjarvis.cli.self_update_cmd.subprocess.run",
            return_value=mock_proc,
        ) as mock_run,
    ):
        result = CliRunner().invoke(self_update, ["-y"])
    assert result.exit_code == 0, result.output
    commands = [call.args[0] for call in mock_run.call_args_list]
    assert commands[0] == ["git", "rev-parse", "--is-shallow-repository"]
    assert commands[1] == ["git", "fetch", "--tags"] + (
        ["--unshallow"] if shallow == "true" else []
    )
    assert commands[2] == ["git", "pull", "--ff-only"]
    assert commands[3] == [
        "uv",
        "sync",
        "--python",
        "/managed venv/bin/python",
        "--inexact",
        "--reinstall-package",
        "openjarvis",
    ]
    for call in mock_run.call_args_list:
        assert call.kwargs.get("shell") is not True
        assert call.kwargs["cwd"] == _mock_info("editable-git").repo_root
    assert mock_run.call_args.kwargs["env"]["UV_PROJECT_ENVIRONMENT"] == "/managed venv"


def test_editable_global_install_rebuilds_running_interpreter(
    monkeypatch, legacy_updates
):
    mock_proc = CompletedProcess([], 0, stdout="false\n", stderr="")
    monkeypatch.setattr("openjarvis.cli.self_update_cmd.sys.prefix", "/global python")
    monkeypatch.setattr(
        "openjarvis.cli.self_update_cmd.sys.base_prefix", "/global python"
    )
    monkeypatch.setattr(
        "openjarvis.cli.self_update_cmd.sys.executable", "/global python/python"
    )
    with (
        patch(
            "openjarvis.cli.self_update_cmd.detect_install",
            return_value=_mock_info("editable-git"),
        ),
        patch(
            "openjarvis.cli.self_update_cmd.subprocess.run",
            return_value=mock_proc,
        ) as mock_run,
    ):
        result = CliRunner().invoke(self_update, ["-y"])

    assert result.exit_code == 0
    assert mock_run.call_args.args[0] == [
        "uv",
        "pip",
        "install",
        "--python",
        "/global python/python",
        "--reinstall-package",
        "openjarvis",
        "-e",
        ".",
    ]


@pytest.mark.parametrize("failed_step", [0, 1, 2, 3])
def test_editable_upgrade_stops_on_failure(monkeypatch, failed_step, legacy_updates):
    monkeypatch.setattr("openjarvis.cli.self_update_cmd.sys.prefix", "/managed venv")
    responses = [CompletedProcess([], 0, stdout="true\n", stderr="")] * failed_step
    responses.append(CompletedProcess([], 7, stdout="", stderr="failed"))
    with (
        patch(
            "openjarvis.cli.self_update_cmd.detect_install",
            return_value=_mock_info("editable-git"),
        ),
        patch(
            "openjarvis.cli.self_update_cmd.subprocess.run", side_effect=responses
        ) as run,
    ):
        result = CliRunner().invoke(self_update, ["-y"])
    assert result.exit_code == 7
    assert run.call_count == failed_step + 1
    assert "Upgrade complete" not in result.output


def test_failed_upgrade_propagates_exit_code(legacy_updates):
    mock_proc = MagicMock(returncode=3)
    with (
        patch(
            "openjarvis.cli.self_update_cmd.detect_install",
            return_value=_mock_info("pypi"),
        ),
        patch(
            "openjarvis.cli.self_update_cmd.subprocess.run",
            return_value=mock_proc,
        ),
    ):
        result = CliRunner().invoke(self_update, ["-y"])
    assert result.exit_code == 3


def test_unknown_install_kind_warns_but_proceeds(legacy_updates):
    mock_proc = MagicMock(returncode=0)
    with (
        patch(
            "openjarvis.cli.self_update_cmd.detect_install",
            return_value=_mock_info("unknown"),
        ),
        patch(
            "openjarvis.cli.self_update_cmd.subprocess.run",
            return_value=mock_proc,
        ),
    ):
        result = CliRunner().invoke(self_update, ["-y"])
    assert result.exit_code == 0
    assert "Could not determine install method" in result.output


def test_decline_confirmation_exits_nonzero(legacy_updates):
    with (
        patch(
            "openjarvis.cli.self_update_cmd.detect_install",
            return_value=_mock_info("pypi"),
        ),
        patch("openjarvis.cli.self_update_cmd.subprocess.run") as mock_run,
    ):
        result = CliRunner().invoke(self_update, input="n\n")
    assert result.exit_code == 1
    assert "Aborted" in result.output
    mock_run.assert_not_called()
