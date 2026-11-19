"""External anonymous usage analytics.

Sends anonymized events to the PostHog service configured for this
installation (none by default) to measure setup success, retention,
feature usage, and churn — without ever collecting chat content,
prompts, file paths, emails, IPs, or hardware identifiers.

Distinct from :mod:`agi_procesor.telemetry`, which stores local FLOPs and
energy metrics in a SQLite DB and never leaves the machine.

Disable: set ``[analytics] enabled = false`` in ``~/.agi-procesor/config.toml``.
"""

from agi_procesor.analytics.aggregator import SessionAggregator
from agi_procesor.analytics.bridge import EventBridge
from agi_procesor.analytics.client import AnalyticsClient
from agi_procesor.analytics.identity import (
    get_or_create_anon_id,
    is_analytics_enabled,
    reset_anon_id,
)
from agi_procesor.analytics.redaction import hash_id, redact

__all__ = [
    "AnalyticsClient",
    "EventBridge",
    "SessionAggregator",
    "get_or_create_anon_id",
    "is_analytics_enabled",
    "reset_anon_id",
    "redact",
    "hash_id",
]
