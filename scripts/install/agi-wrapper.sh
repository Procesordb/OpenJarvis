#!/usr/bin/env bash
# agi-wrapper.sh — symlinked to ~/.local/bin/agi.
# Activates the managed venv and execs the real agi CLI.

AGI_PROCESOR_HOME="${AGI_PROCESOR_HOME:-$HOME/.agi-procesor}"
VENV="$AGI_PROCESOR_HOME/.venv"

if [[ ! -d "$VENV" ]]; then
    echo "agi: venv not found at $VENV" >&2
    echo "Re-run the installer: curl -fsSL https://procesordb.github.io/OpenJarvis/install.sh | bash" >&2
    exit 1
fi

exec "$VENV/bin/agi" "$@"
