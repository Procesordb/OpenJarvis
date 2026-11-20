<!-- Created by the AGI PROCESOR project in 2026. -->

# AGI PROCESOR FOMO Radar

AGI PROCESOR FOMO Radar is an independent, local-first market-risk and paper
trading MVP built on OpenJarvis. It turns caller-supplied market observations
into a deterministic, explainable risk score. It does not fetch data from
Fomo, log in to Fomo, hold funds, sign transactions, or execute trades.

!!! warning "Educational analysis only"

    The score is a heuristic, not a price prediction, recommendation, or
    promise of profit. Source data can be incomplete, stale, or wrong. A user
    remains responsible for every decision.

## Product boundary

The MVP supports:

- caller-supplied or separately authorised market data;
- risk scores from 0 to 100 with a breakdown of every contributing flag;
- downside scenarios and possible risk controls;
- `watch`, `caution`, and `avoid` radar labels;
- a local, persistent paper-trading ledger;
- a validated public affiliate link with a visible disclosure.

The MVP intentionally does **not** support:

- Fomo credentials, cookies, session tokens, private keys, or seed phrases;
- Fomo scraping or browser automation;
- wallet access, deposits, withdrawals, order routing, or automated trading;
- hidden affiliate redirects or guaranteed-return claims.

The current machine-readable boundary is available at:

```text
GET /v1/fomo/capabilities
```

## Start the local app

```bash
uv sync --extra dev --extra server
cd frontend
npm install
npm run build
cd ..
uv run jarvis gui
```

Open `/fomo-radar` in the app. The first UI version uses clearly labelled demo
data. The API below is functional and accepts custom snapshots.

## Assess a market snapshot

```bash
curl -X POST http://127.0.0.1:8000/v1/fomo/risk-assessments \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EXAMPLE",
    "chain": "base",
    "price_usd": "0.0125",
    "market_cap_usd": "5000000",
    "liquidity_usd": "175000",
    "volume_24h_usd": "620000",
    "price_change_24h_pct": "34.2",
    "token_age_hours": "96",
    "top_holders_pct": "48",
    "source": "authorised-provider-or-user-input",
    "contract_risks": {
      "contract_unverified": false,
      "mint_authority_enabled": true
    }
  }'
```

Numeric strings are accepted to preserve decimal precision. `null` contract
flags mean "not checked" and are deliberately different from `false`.

The response includes the submitted snapshot, the total score, risk level,
radar disposition, explainable flags, scenarios, disclaimer, and
`execution_capability: "none"`.

## Paper trading

Read the simulated portfolio:

```text
GET /v1/fomo/paper/portfolio
```

Record a simulated fill:

```bash
curl -X POST http://127.0.0.1:8000/v1/fomo/paper/trades \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EXAMPLE",
    "side": "buy",
    "quantity": "100",
    "price_usd": "0.0125",
    "fee_bps": "45",
    "note": "paper test only",
    "confirm_paper_trade": true
  }'
```

`confirm_paper_trade: true` is mandatory. This endpoint only updates local
simulation accounting. It contains no code capable of creating a real order.
The ledger uses decimal arithmetic, records fees and cost basis, calculates
realised and unrealised P&L, and persists with an atomic file replacement.

Default storage is:

```text
~/.openjarvis/agi-procesor/paper-ledger.json
```

## Affiliate disclosure

Public affiliate metadata is available at:

```text
GET /v1/fomo/affiliate?language=pl
```

The default link is `https://fomo.family/r/AGIPROCESOR`. The validator accepts
only an HTTPS `fomo.family/r/<code>` URL, without credentials, query parameters,
or fragments.

The product displays this disclosure:

> Materiał reklamowy / link afiliacyjny. AGI PROCESOR może otrzymać część
> opłat transakcyjnych, jeśli zarejestrujesz się przez ten link. Nie jest to
> obietnica zysku ani indywidualna rekomendacja inwestycyjna.

The link can be overridden with the public, non-secret environment variable
`AGI_PROCESOR_FOMO_REFERRAL_URL`. Do not put account credentials in any AGI
PROCESOR environment variable.

## Local configuration

The optional settings below affect only the paper simulator and public link:

| Variable | Default | Meaning |
|---|---:|---|
| `AGI_PROCESOR_FOMO_REFERRAL_URL` | `https://fomo.family/r/AGIPROCESOR` | Validated public referral link |
| `AGI_PROCESOR_PAPER_LEDGER_PATH` | config directory | Local JSON simulation ledger |
| `AGI_PROCESOR_PAPER_INITIAL_CASH_USD` | `10000` | Initial simulated cash |
| `AGI_PROCESOR_PAPER_FEE_BPS` | `45` | Default simulated fee in basis points |

Before publishing a branded integration or adding a data source, obtain written
authorisation for the intended Fomo brand use and integration method. Only an
officially authorised interface should ever replace the current link-only
mode.
