#!/usr/bin/env bats

setup() {
    TEST_TMPDIR=$(mktemp -d)
    export AGI_PROCESOR_HOME="$TEST_TMPDIR/.agi-procesor"
    mkdir -p "$AGI_PROCESOR_HOME/.state"
    mkdir -p "$AGI_PROCESOR_HOME/src/rust/crates/agi-procesor-python"
    touch "$AGI_PROCESOR_HOME/src/rust/crates/agi-procesor-python/Cargo.toml"
    export UV_STUB_LOG="$TEST_TMPDIR/uv.log"
    : > "$UV_STUB_LOG"
    export PYTHON_STUB_LOG="$TEST_TMPDIR/python.log"
    : > "$PYTHON_STUB_LOG"
    mkdir -p "$AGI_PROCESOR_HOME/.venv/bin"
    cat > "$AGI_PROCESOR_HOME/.venv/bin/python" <<'EOF'
#!/usr/bin/env bash
echo "$0 $*" >> "$PYTHON_STUB_LOG"
exit "${PYTHON_STUB_EXIT:-0}"
EOF
    chmod +x "$AGI_PROCESOR_HOME/.venv/bin/python"
    # A function takes precedence over the script's self-healed PATH, even
    # on developer machines with a real uvx in ~/.local/bin.
    export UVX_STUB="$BATS_TEST_DIRNAME/stubs/uvx"
    uvx() { "$UVX_STUB" "$@"; }
    export -f uvx
    export PATH="$BATS_TEST_DIRNAME/stubs:$PATH"
    export SCRIPT="$BATS_TEST_DIRNAME/../../../scripts/install/build-extension.sh"
}

teardown() {
    [[ -n "${TEST_TMPDIR:-}" ]] && rm -rf "$TEST_TMPDIR"
}

@test "writes extension-built marker on success" {
    UV_STUB_EXIT=0 run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [ -f "$AGI_PROCESOR_HOME/.state/extension-built" ]
}

@test "writes extension-failed marker on failure" {
    UV_STUB_EXIT=1 run bash "$SCRIPT"
    [ "$status" -ne 0 ]
    [ -f "$AGI_PROCESOR_HOME/.state/extension-failed" ]
    [ -s "$AGI_PROCESOR_HOME/.state/extension-failed" ]
}

@test "removes prior failed marker on success" {
    touch "$AGI_PROCESOR_HOME/.state/extension-failed"
    UV_STUB_EXIT=0 run bash "$SCRIPT"
    [ ! -f "$AGI_PROCESOR_HOME/.state/extension-failed" ]
    [ -f "$AGI_PROCESOR_HOME/.state/extension-built" ]
}

@test "builds and verifies the extension in the runtime venv" {
    UV_STUB_EXIT=0 run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    grep -Fx "VIRTUAL_ENV=$AGI_PROCESOR_HOME/.venv" "$UV_STUB_LOG"
    grep -Fx "maturin develop --uv -m $AGI_PROCESOR_HOME/src/rust/crates/agi-procesor-python/Cargo.toml" "$UV_STUB_LOG"
    grep -Fx "$AGI_PROCESOR_HOME/.venv/bin/python -c import agi_procesor_rust" "$PYTHON_STUB_LOG"
    [ ! -d "$AGI_PROCESOR_HOME/src/.venv" ]
}

@test "reports a failed runtime import and preserves its exit code" {
    touch "$AGI_PROCESOR_HOME/.state/extension-built"
    PYTHON_STUB_EXIT=7 run bash "$SCRIPT"
    [ "$status" -eq 7 ]
    [ ! -f "$AGI_PROCESOR_HOME/.state/extension-built" ]
    grep -q "failed in the serving venv ($AGI_PROCESOR_HOME/.venv)" "$AGI_PROCESOR_HOME/.state/extension-failed"
    grep -q 'exit=7' "$AGI_PROCESOR_HOME/.state/extension-failed"
}

@test "fails before compilation when the runtime venv is missing" {
    touch "$AGI_PROCESOR_HOME/.state/extension-built"
    rm -f "$AGI_PROCESOR_HOME/.venv/bin/python"
    run bash "$SCRIPT"
    [ "$status" -ne 0 ]
    [ ! -s "$UV_STUB_LOG" ]
    [ ! -f "$AGI_PROCESOR_HOME/.state/extension-built" ]
    grep -q "runtime venv not found" "$AGI_PROCESOR_HOME/.state/extension-failed"
}

@test "fails before compilation when the manifest is missing" {
    touch "$AGI_PROCESOR_HOME/.state/extension-built"
    rm -f "$AGI_PROCESOR_HOME/src/rust/crates/agi-procesor-python/Cargo.toml"
    run bash "$SCRIPT"
    [ "$status" -ne 0 ]
    [ ! -s "$UV_STUB_LOG" ]
    [ ! -f "$AGI_PROCESOR_HOME/.state/extension-built" ]
    grep -q "manifest not found" "$AGI_PROCESOR_HOME/.state/extension-failed"
}

@test "atomic rename — no .tmp file left behind" {
    UV_STUB_EXIT=0 run bash "$SCRIPT"
    leftover=$(find "$AGI_PROCESOR_HOME/.state" -name "*.tmp" 2>/dev/null | wc -l)
    [ "$leftover" -eq 0 ]
}
