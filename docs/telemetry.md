# Telemetry

AGI PROCESOR can send **optional usage analytics** to a PostHog service that
the owner of an installation configures, to see where the product breaks and
which features people actually use. None is configured by default. This page
documents exactly what is and isn't collected, where the data goes, and how
to enable or disable it.

## TL;DR

- **No destination by default.** AGI PROCESOR ships without an analytics
  endpoint, so the installer and `agi init` ask nothing and send nothing until
  `[analytics] host` and `key` (or `AGI_PROCESOR_ANALYTICS_HOST` and
  `AGI_PROCESOR_ANALYTICS_KEY`) are set.
- **Off until you choose to share.** In an interactive Bash installation or
  `agi init`, the dedicated prompt says: **Press Enter or Y to consent,
  or N to decline**. Enter at that prompt enables sharing; EOF, cancellation,
  or an unattended run does not.
- **Installation ID** — one random UUID links install and usage events.
  A random identifier is not a guarantee of legal anonymity.
- **No chat content, ever.** Only counts, timings, and feature names.
- **Destination** — the configured PostHog endpoint; see below.
- **Documented retention policy: 365 days.** Enforcement is configured on
  the receiving service, rather than in the client.

## Choosing whether to share

The Bash installer asks before its first analytics beacon. The answer is
saved as `[analytics] enabled` in `config.toml`, so the backend and frontend
use the same choice. Installer reruns save the latest answer even when
completed installation steps are skipped. No IP-based country lookup is used;
the same prompt applies everywhere.

For unattended installs, consent explicitly with `--analytics` or decline with
`--no-analytics`:

```bash
curl -fsSL https://procesordb.github.io/OpenJarvis/install.sh | bash -s -- --analytics
# Or: ... | bash -s -- --no-analytics
agi init --analytics
# Or: agi init --no-analytics
```

To change your choice later:

```bash
agi config set analytics.enabled false
# To enable: agi config set analytics.enabled true
```

Restart the server and reload the frontend after changing the setting.
An existing, explicitly configured `enabled = true` remains enabled until
changed. Configurations without an analytics setting now default to off.
Local performance telemetry and Savings Leaderboard participation remain
separate settings.

In the browser and desktop apps, the **Share your savings** dialog
offers explicit buttons without a checkbox. Displaying or closing the dialog
does not enable analytics. Confirm with **Enable analytics only** or
**Enable analytics & join leaderboard**, or use **Continue without sharing**
to turn analytics off. A saved UI choice takes effect immediately in both
the frontend and the running backend.

Joining the leaderboard requires a display name and contact email submitted
with savings to the configured Supabase leaderboard. Analytics preferences
send only the on/off choice to the local server; names and emails are not
attached to PostHog usage events by this form.
Use **Join leaderboard only** to join with analytics off; submitting the
name/email form with Enter also uses that option. Stopping leaderboard
updates and disabling usage analytics are separate actions. Stopping updates
does not delete previously submitted entries from Supabase.

## What we collect

### Lifecycle events

| Event | Source | Why we send it |
|---|---|---|
| `install_started` | `install.sh` | Top of install funnel |
| `install_stage_completed` | `install.sh` | Per-stage timing — where do people drop off? |
| `install_completed` | `install.sh` | Did the install succeed? |
| `install_failed` | `install.sh` | Which stage failed, and on what OS |
| `app_opened` | Backend + frontend | DAU / WAU / MAU |
| `setup_completed` | Frontend | First-run wizard finished |
| `first_chat_sent` | Backend | First-ever message — activation |
| `uninstall_started` | `uninstall.sh` (if user runs it) | Churn signal |

### Usage events

| Event | Why we send it |
|---|---|
| `chat_session_ended` | Aggregated per-session: turn count, tokens, latency, tool count |
| `tool_first_used` | Which built-in tools are actually adopted |
| `model_changed` | How often users switch models |
| `feature_used` | Which features get traffic, which don't |
| `connector_auth_completed` | Which connectors people set up |
| `error_shown_to_user` | User-visible error class (not stack trace) |
| `feedback_submitted` | Was a rating given? Was a comment included? |
| `settings_changed` | Which settings get toggled |
| `usage_daily_summary` | Once-per-day aggregated counts |

The canonical, authoritative list with every property name and its
type validator lives in
[`src/agi_procesor/analytics/events.py`](../src/agi_procesor/analytics/events.py).
That file is the only place new events can be added — PR review is
the gate.

## Backend safeguards

Backend events use a property allowlist and value-level redaction:

- **Chat content** — prompts, model outputs, system messages, tool args.
- **File paths** — anything matching `~/`, `$HOME`, `/Users/<name>`, `/home/<name>`, `file://`.
- **Emails** matching the redaction patterns.
- **IP addresses** (IPv4 + IPv6) in property values. IP geolocation is
  disabled in the backend SDK; the receiving infrastructure can still
  observe connection IPs.
- **MAC addresses** matching the redaction patterns. Event properties do
  not include hardware serials or drive UUIDs.
- **Stack traces** — only error class enums.
- **API keys, OAuth tokens, JWTs, bearer tokens, password assignments** —
  matched and dropped at value level.
- **Hostnames** that look personal (e.g. `alice-macbook.local`).
- **Lists, dicts, sets** — composite values are never sent so PII can't
  smuggle through inside containers.

Two independent filters run before backend event properties are sent:

1. [`src/agi_procesor/analytics/redaction.py`](../src/agi_procesor/analytics/redaction.py) — value-level pattern matching (20+ regexes for PII).
2. [`src/agi_procesor/analytics/events.py`](../src/agi_procesor/analytics/events.py) — structural allowlist (event name + property name + type validator).

Any failure at either layer → the event or property is silently
dropped. Tests covering the patterns: [`tests/analytics/test_redaction.py`](../tests/analytics/test_redaction.py).

The frontend sends directly through `posthog-js`. Its wrapper restricts event
names but does not use these backend property filters. The SDK can add browser
and page metadata, including the current URL. Autocapture, pageviews, and session
recording are disabled. Installer beacons use fixed fields assembled separately.

## Where the data goes

- AGI PROCESOR has no default endpoint. Events go only to the PostHog service
  set in `[analytics] host` and `key`, or in `AGI_PROCESOR_ANALYTICS_HOST` and
  `AGI_PROCESOR_ANALYTICS_KEY` (which the Bash installer reads too). A
  configured endpoint alone does not establish its hosting provider or server
  logging settings.
- **Never** sold, shared with advertisers, or used for anything other
  than improving AGI PROCESOR.

## Retention

- The documented retention policy is **365 days**. The receiving service
  must be configured to enforce it; client code does not delete remote events.
- Replacing the local installation ID changes the identifier used for future
  events. It does not delete previously collected events.

## How identity works

A single UUID v4 is generated when sharing is first enabled and stored at
`~/.agi-procesor/anon_id`. The install script, backend, and frontend all
read the same file so events across the lifecycle can be linked to the
same installation.

Delete the file (`rm ~/.agi-procesor/anon_id`) and a fresh UUID will be
generated next time analytics are enabled. Events associated with the
previous UUID remain on the receiving service until deleted there.

## For researchers and contributors

- **Adding an event**: edit `src/agi_procesor/analytics/events.py`,
  declare the spec, then update this page. PR review enforces both.
- **Adding a PII pattern**: edit `src/agi_procesor/analytics/redaction.py`
  and add a test case in `tests/analytics/test_redaction.py`.
- **Inspecting what your install sends**: run with
  `AGI_PROCESOR_LOG_LEVEL=DEBUG` and grep for `Analytics`. You'll see
  every event name and (redacted) property dict before it ships.

## Related

- Local telemetry (FLOPs, energy, latency stored in
  `~/.agi-procesor/telemetry.db`) is a **separate** subsystem documented
  in [`src/agi_procesor/telemetry/`](../src/agi_procesor/telemetry/). It
  never leaves the machine and is controlled by `[telemetry]` (not
  `[analytics]`) in `config.toml`.
- The leaderboard / contest opt-in (`OptInModal.tsx`) is a separate,
  voluntary feature that publicly shares your energy and savings on
  the AGI PROCESOR leaderboard. It is **not** the same as analytics and
  requires explicit opt-in with a display name and email.
