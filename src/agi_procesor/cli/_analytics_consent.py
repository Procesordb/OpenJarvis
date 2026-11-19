"""Dedicated terminal consent for optional external usage analytics."""

from __future__ import annotations

import click
import tomlkit

from agi_procesor.core.config import AnalyticsConfig


def ask_analytics_consent(host: str | None = None) -> bool:
    """Ask once per init; a deliberate Enter/Y consents, EOF/cancellation does not.

    AGI PROCESOR: without a configured analytics host and key there is nothing
    to share, so no question is asked and the answer is "no".
    """
    cfg = AnalyticsConfig()
    if not ((host or cfg.host) and cfg.key):
        return False
    stream = click.get_text_stream("stdin")
    if not stream.isatty():
        return False
    click.echo(
        "\nHelp improve AGI PROCESOR by sharing optional usage statistics.\n"
        "Data includes feature usage, timings, token counts, error categories,\n"
        "environment metadata, and a random installation ID.\n"
        "Recipient: the PostHog endpoint configured for this installation.\n"
        "Privacy details: https://procesordb.github.io/OpenJarvis/telemetry/\n"
        "You can disable sharing later: agi config set analytics.enabled false\n"
        "(then restart the server and reload the app).\n"
        "Declining does not change AGI PROCESOR functionality.",
        err=True,
    )
    click.echo(f"Analytics destination: {host or AnalyticsConfig().host}", err=True)
    while True:
        click.echo("Press Enter or Y to consent, or N to decline: ", nl=False, err=True)
        try:
            answer = stream.readline()
        except (EOFError, KeyboardInterrupt):
            click.echo(err=True)
            return False
        if not answer:
            return False
        answer = answer.strip().lower()
        if answer in ("", "y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        click.echo("Please press Enter, type Y, or type N.", err=True)


def apply_analytics_choice(content: str, choice: bool | None, *, prompt: bool) -> str:
    """Persist an explicit flag or terminal choice in generated/copied TOML."""
    if choice is None:
        if not prompt or not click.get_text_stream("stdin").isatty():
            # Defaults are off. Preserve an explicitly supplied config in
            # unattended init rather than rewriting unrelated input files.
            return content
        doc = tomlkit.parse(content)
        host = doc.get("analytics", {}).get("host", AnalyticsConfig().host)
        choice = ask_analytics_consent(str(host))
    doc = tomlkit.parse(content)
    if "analytics" not in doc:
        doc.add("analytics", tomlkit.table())
    doc["analytics"]["enabled"] = choice
    doc["analytics"]["choice_recorded"] = True
    return tomlkit.dumps(doc)
