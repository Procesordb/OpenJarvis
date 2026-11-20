<!-- Created by the AGI PROCESOR project in 2026. -->

# AGI PROCESOR Alerts

AGI PROCESOR Alerts turns a caller-supplied or separately authorised market
snapshot into an explainable risk notification. It does **not** log in to
Fomo, scrape Fomo, access a wallet, fetch market data, or place a transaction.
The existing deterministic FOMO risk scorer supplies the risk score.

## What the three states mean

- `WATCH` means the configured low-risk and optional entry-price research
  thresholds were observed. It is a prompt for human research, not a buy
  instruction.
- `CAUTION` means neither the `WATCH` nor `AVOID` band was met. A human should
  monitor and re-evaluate with newer authorised data.
- `AVOID` means the configured high-risk or exit-price review threshold was
  observed. It is a prompt to review exposure, not an automatic sell order.

`activation_condition` and `invalidation_condition` are operator-authored
notes shown in the UI and messages. They are **not executable expressions**.
Machine evaluation uses only the fields returned in
`machine_evaluated_fields`: symbol, risk-score thresholds, and optional price
thresholds. Every generated event also contains a backend-generated condition
and an invalidation condition.

## Safe API flow

1. Create a rule with `POST /v1/alerts/rules`. The request must include
   `confirm_rule_creation: true`, both condition texts (at least 10
   characters), at least one channel, and a cooldown of at least 15 minutes.
2. Preview with `POST /v1/alerts/dry-run` or
   `POST /v1/alerts/test-render`. Neither endpoint persists or sends anything.
3. Supply a new authorised snapshot to `POST /v1/alerts/evaluate` with
   `confirm_queue: true`. The API evaluates and records it; it still sends
   nothing.
4. Send one queued event with `POST /v1/alerts/events/{event_id}/send` and
   `confirm_send: true`.
5. An external operator scheduler may call `POST /v1/alerts/dispatch-pending`
   only when `AGI_PROCESOR_ALERTS_SCHEDULER_ENABLED=true`, and must include
   `operator_scheduled: true`.

There is no internal market poller or hidden scheduler. For continuous
operation, an authorised external process must supply fresh snapshots and
explicitly choose whether to queue them. `GET /v1/alerts/capabilities` reports
`automatic_evaluation: false` and describes the dispatch gate honestly.

Rule updates require `confirm_rule_update: true`; deletion requires
`confirm_rule_deletion: true`. Repeated equivalent events are suppressed for
the rule's cooldown period. A stable fingerprint uses the rule, state, review
context, and risk flag codes rather than volatile price text.

Snapshots fail closed when `observed_at` is older than
`AGI_PROCESOR_ALERTS_MAX_SNAPSHOT_AGE_SECONDS` (900 seconds by default) or is
further in the future than `AGI_PROCESOR_ALERTS_MAX_FUTURE_SKEW_SECONDS` (60
seconds by default). This prevents an old or incorrectly dated observation
from looking like a current alert.

## Delivery configuration

All destinations and credentials come from environment variables or the VPS
secret mechanism. They are never accepted in rule requests and are never
returned by the capabilities endpoint.

| Channel | Required variables |
| --- | --- |
| Email | `AGI_PROCESOR_ALERTS_SMTP_HOST`, `..._SMTP_FROM`, `..._EMAIL_TO`; optional port, username/password, SSL and STARTTLS flags |
| Telegram | `AGI_PROCESOR_ALERTS_TELEGRAM_BOT_TOKEN`, `..._TELEGRAM_CHAT_ID` |
| ntfy | `AGI_PROCESOR_ALERTS_NTFY_URL`; optional `..._NTFY_TOKEN` |
| SMS via email gateway | `AGI_PROCESOR_ALERTS_SMS_MODE=email_gateway`, SMTP settings, `..._SMS_EMAIL_TO` |
| SMS via HTTP | `AGI_PROCESOR_ALERTS_SMS_MODE=http`, `..._SMS_HTTP_URL`, `..._SMS_HTTP_TOKEN`, `..._SMS_TO`, and `..._SMS_ALLOWED_HOSTS` |

SMTP must use SSL or STARTTLS. ntfy and HTTP SMS URLs must use HTTPS. An HTTP
SMS host must appear in the explicit allowlist, which prevents rule input from
turning the server into an arbitrary request proxy. Provider errors are
sanitised so a token embedded in a Telegram URL cannot leak through the API.

Telegram and self-hosted ntfy can avoid per-message software fees, but no
universal free SMS service exists. Carrier email-to-SMS support and HTTP SMS
pricing depend on the operator's provider.

SMS text is compacted to at most 300 characters by default while retaining
source, timestamp, risk, condition, invalidation, no-execution language, and a
disclaimer. A larger `AGI_PROCESOR_ALERTS_SMS_MAX_CHARS` value is rejected
unless `AGI_PROCESOR_ALERTS_SMS_ALLOW_MULTIPART=true` explicitly accepts the
potential extra provider cost.

Actual delivery uses an atomic lease
(`AGI_PROCESOR_ALERTS_DELIVERY_LEASE_SECONDS`, default 120) so concurrent
`/send` calls cannot both dispatch an event. Failed channels use bounded
attempts (`AGI_PROCESOR_ALERTS_MAX_ATTEMPTS_PER_CHANNEL`, default 3) and
backoff (`AGI_PROCESOR_ALERTS_RETRY_BACKOFF_SECONDS`, default 60); a channel
that already succeeded is never resent during retry. A worker crash after a
provider accepts a message but before local acknowledgement is inherently an
at-least-once boundary: after the lease expires, an operator retry can produce
a duplicate. The capabilities endpoint states this explicitly.

## Message and storage guarantees

Every rendered notification includes:

- state and human review context;
- source and observed timestamp;
- risk score, level, and risk flags;
- the condition and invalidation condition;
- an explicit statement that execution capability is `none`;
- the educational-risk disclaimer.

The default store is
`<OpenJarvis config dir>/agi-procesor/alerts.json`. Override it with
`AGI_PROCESOR_ALERTS_STORE_PATH`. Writes use a same-directory temporary file,
flush and `fsync`, then atomic replacement. A file lock protects cooperating
processes. Corrupt or unsupported state fails closed and is not overwritten.

The store contains rules, event history, cooldown fingerprints, and sanitised
delivery results. It does not contain provider tokens or account passwords.
