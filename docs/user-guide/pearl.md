# Pearl CLI Integration

AGI PROCESOR includes a thin `agi pearl` wrapper for Pearl's native command
line tools. It does not replace Pearl's node or wallet; it makes the common
commands discoverable from the same CLI users use for mining.

## Binary Discovery

`agi pearl` looks for `pearld`, `oyster`, and `prlctl` on `PATH`, then under
`$PEARL_HOME/bin`.

```bash
export PEARL_HOME=/path/to/pearl
agi pearl doctor
```

## Native Pass-Through

Use pass-through commands when you need the full Pearl surface:

```bash
agi pearl node -- --help
agi pearl wallet -- --help
agi pearl ctl -- --help
```

These map directly to:

| AGI PROCESOR command | Pearl binary |
|---|---|
| `agi pearl node` | `pearld` |
| `agi pearl wallet` | `oyster` |
| `agi pearl ctl` | `prlctl` |

The command format is always `agi pearl <command>`. Pearl-native arguments
go after that command. Use `--` before Pearl arguments when the arguments begin
with dashes and you want to make the pass-through boundary explicit.

## Wallet Address Helper

If Oyster is already running, generate a mining address through wallet RPC:

```bash
agi pearl address \
  -u rpcuser \
  -P rpcpass \
  -s localhost:44207
```

The helper uses `prlctl --wallet` and defaults to `--notls`, which matches the
local validation flow. Use `--tls --skipverify` if your Oyster RPC endpoint is
serving TLS with a local certificate.

## Boundary

`agi mine` is the AGI PROCESOR mining lifecycle. `agi pearl` is an escape
hatch to Pearl's native node, wallet, and RPC tools. For advanced node or
wallet administration, Pearl's own help output is the source of truth.
