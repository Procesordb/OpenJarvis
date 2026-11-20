# Created by the AGI PROCESOR project in 2026.

"""Opt-in alert delivery adapters configured exclusively through environment."""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Mapping
from urllib.parse import urlparse

import httpx

from openjarvis.alerts.models import AlertChannel, AlertEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DispatchResult:
    channel: AlertChannel
    success: bool
    detail: str
    attempted_at: datetime

    def as_dict(self) -> dict[str, object]:
        return {
            "channel": self.channel.value,
            "success": self.success,
            "detail": self.detail,
            "attempted_at": self.attempted_at.isoformat(),
        }


def render_alert(event: AlertEvent) -> str:
    """Render all disclosures required for every delivery channel."""

    flag_text = ", ".join(event.risk_flags) if event.risk_flags else "none reported"
    return "\n".join(
        (
            f"AGI PROCESOR ALERT — {event.state.value.upper()}",
            f"Asset: {event.symbol}",
            f"Human review context: {event.review_action.value}",
            f"Source: {event.source}",
            f"Observed timestamp: {event.observed_at.isoformat()}",
            f"Risk: {event.risk_score}/100 ({event.risk_level})",
            f"Observed price: ${event.price_usd}",
            f"Condition: {event.condition}",
            f"Invalidation condition: {event.invalidation_condition}",
            f"Risk flags: {flag_text}",
            "Execution capability: none; no transaction was or can be placed.",
            f"Disclaimer: {event.disclaimer}",
        )
    )


def render_sms(event: AlertEvent, *, max_chars: int = 300) -> str:
    """Render a cost-bounded SMS while retaining every required disclosure."""

    if max_chars < 220:
        raise ValueError("SMS character budget must be at least 220")
    budgets = {"source": 18, "condition": 30, "invalidation": 30}

    def build() -> str:
        return "\n".join(
            (
                f"AGI {event.state.value.upper()} {event.symbol}",
                f"Src:{_clip(event.source, budgets['source'])}",
                f"At:{event.observed_at.isoformat(timespec='seconds')}",
                f"Risk:{event.risk_score}/100 {event.risk_level}",
                f"Cond:{_clip(event.condition, budgets['condition'])}",
                (
                    "Invalid:"
                    f"{_clip(event.invalidation_condition, budgets['invalidation'])}"
                ),
                "No execution.",
                (
                    "Disclaimer: educational only; no advice, profit promise, "
                    "or buy/sell instruction. Verify data."
                ),
            )
        )

    message = build()
    for field_name in ("condition", "invalidation", "source"):
        while len(message) > max_chars and budgets[field_name] > 8:
            budgets[field_name] -= 1
            message = build()
    if len(message) > max_chars:
        raise ValueError("SMS character budget is too small for required disclosures")
    return message


class AlertDispatcher:
    """Deliver already-approved events; it does not decide when to send."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._env = os.environ if environ is None else environ

    def capabilities(self) -> dict[str, dict[str, object]]:
        """Return booleans and reasons only, never destinations or secrets."""

        result: dict[str, dict[str, object]] = {}
        for channel in AlertChannel:
            try:
                self._validate_channel(channel)
            except ValueError as exc:
                result[channel.value] = {
                    "configured": False,
                    "reason": str(exc),
                }
            else:
                result[channel.value] = {"configured": True}
        return result

    def send(self, channel: AlertChannel, event: AlertEvent) -> DispatchResult:
        """Send to one channel, returning a sanitised delivery result."""

        attempted_at = datetime.now(timezone.utc)
        try:
            self._validate_channel(channel)
            message = render_alert(event)
            if channel is AlertChannel.EMAIL:
                self._send_smtp(
                    recipient=self._required("AGI_PROCESOR_ALERTS_EMAIL_TO"),
                    subject=f"AGI PROCESOR {event.state.value.upper()}: {event.symbol}",
                    message=message,
                )
            elif channel is AlertChannel.TELEGRAM:
                self._send_telegram(message)
            elif channel is AlertChannel.NTFY:
                self._send_ntfy(event, message)
            else:
                self._send_sms(
                    event,
                    render_sms(event, max_chars=self._sms_max_chars()),
                )
        except ValueError as exc:
            return DispatchResult(channel, False, str(exc), attempted_at)
        except Exception as exc:  # noqa: BLE001 - sanitise all provider failures
            logger.warning(
                "Alert delivery failed for channel=%s error_type=%s",
                channel.value,
                type(exc).__name__,
            )
            return DispatchResult(
                channel,
                False,
                f"Delivery failed ({type(exc).__name__}); inspect operator logs",
                attempted_at,
            )
        return DispatchResult(channel, True, "Delivered", attempted_at)

    def _validate_channel(self, channel: AlertChannel) -> None:
        if channel is AlertChannel.EMAIL:
            self._validate_smtp()
            self._required("AGI_PROCESOR_ALERTS_EMAIL_TO")
        elif channel is AlertChannel.TELEGRAM:
            self._required("AGI_PROCESOR_ALERTS_TELEGRAM_BOT_TOKEN")
            self._required("AGI_PROCESOR_ALERTS_TELEGRAM_CHAT_ID")
        elif channel is AlertChannel.NTFY:
            self._https_url("AGI_PROCESOR_ALERTS_NTFY_URL")
        else:
            self._sms_max_chars()
            mode = self._env.get("AGI_PROCESOR_ALERTS_SMS_MODE", "").strip().lower()
            if mode == "email_gateway":
                self._validate_smtp()
                self._required("AGI_PROCESOR_ALERTS_SMS_EMAIL_TO")
            elif mode == "http":
                parsed = self._https_url("AGI_PROCESOR_ALERTS_SMS_HTTP_URL")
                self._required("AGI_PROCESOR_ALERTS_SMS_HTTP_TOKEN")
                self._required("AGI_PROCESOR_ALERTS_SMS_TO")
                allowed = {
                    item.strip().lower()
                    for item in self._env.get(
                        "AGI_PROCESOR_ALERTS_SMS_ALLOWED_HOSTS", ""
                    ).split(",")
                    if item.strip()
                }
                if not parsed.hostname or parsed.hostname.lower() not in allowed:
                    raise ValueError("SMS HTTP host is not explicitly allowlisted")
            else:
                raise ValueError("SMS mode is not configured")

    def _validate_smtp(self) -> None:
        self._required("AGI_PROCESOR_ALERTS_SMTP_HOST")
        self._required("AGI_PROCESOR_ALERTS_SMTP_FROM")
        use_ssl = _truthy(self._env.get("AGI_PROCESOR_ALERTS_SMTP_USE_SSL", "true"))
        starttls = _truthy(self._env.get("AGI_PROCESOR_ALERTS_SMTP_STARTTLS", "true"))
        if not use_ssl and not starttls:
            raise ValueError("SMTP requires TLS (SSL or STARTTLS)")
        username = self._env.get("AGI_PROCESOR_ALERTS_SMTP_USERNAME", "").strip()
        password = self._env.get("AGI_PROCESOR_ALERTS_SMTP_PASSWORD", "").strip()
        if bool(username) != bool(password):
            raise ValueError("SMTP username and password must be configured together")

    def _send_smtp(self, *, recipient: str, subject: str, message: str) -> None:
        host = self._required("AGI_PROCESOR_ALERTS_SMTP_HOST")
        use_ssl = _truthy(self._env.get("AGI_PROCESOR_ALERTS_SMTP_USE_SSL", "true"))
        starttls = _truthy(self._env.get("AGI_PROCESOR_ALERTS_SMTP_STARTTLS", "true"))
        default_port = 465 if use_ssl else 587
        port = int(self._env.get("AGI_PROCESOR_ALERTS_SMTP_PORT", str(default_port)))
        email = EmailMessage()
        email["From"] = self._required("AGI_PROCESOR_ALERTS_SMTP_FROM")
        email["To"] = recipient
        email["Subject"] = subject
        email.set_content(message)

        context = ssl.create_default_context()
        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        kwargs = {"context": context} if use_ssl else {}
        with smtp_class(host, port, timeout=15, **kwargs) as client:
            if starttls and not use_ssl:
                client.starttls(context=context)
            username = self._env.get("AGI_PROCESOR_ALERTS_SMTP_USERNAME", "").strip()
            if username:
                client.login(
                    username,
                    self._required("AGI_PROCESOR_ALERTS_SMTP_PASSWORD"),
                )
            client.send_message(email)

    def _send_telegram(self, message: str) -> None:
        token = self._required("AGI_PROCESOR_ALERTS_TELEGRAM_BOT_TOKEN")
        chat_id = self._required("AGI_PROCESOR_ALERTS_TELEGRAM_CHAT_ID")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._post_json(url, {"chat_id": chat_id, "text": message[:4096]})

    def _send_ntfy(self, event: AlertEvent, message: str) -> None:
        url = self._https_url("AGI_PROCESOR_ALERTS_NTFY_URL").geturl()
        headers = {
            "Title": f"AGI PROCESOR {event.state.value.upper()}: {event.symbol}",
            "Priority": "high" if event.state.value == "avoid" else "default",
        }
        token = self._env.get("AGI_PROCESOR_ALERTS_NTFY_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            response = client.post(
                url, content=message.encode("utf-8"), headers=headers
            )
            if not 200 <= response.status_code < 300:
                raise RuntimeError(f"ntfy returned HTTP {response.status_code}")

    def _send_sms(self, event: AlertEvent, message: str) -> None:
        mode = self._env.get("AGI_PROCESOR_ALERTS_SMS_MODE", "").strip().lower()
        if mode == "email_gateway":
            self._send_smtp(
                recipient=self._required("AGI_PROCESOR_ALERTS_SMS_EMAIL_TO"),
                subject=f"{event.state.value.upper()} {event.symbol}",
                message=message,
            )
            return
        url = self._https_url("AGI_PROCESOR_ALERTS_SMS_HTTP_URL").geturl()
        self._post_json(
            url,
            {
                "to": self._required("AGI_PROCESOR_ALERTS_SMS_TO"),
                "message": message,
            },
            token=self._required("AGI_PROCESOR_ALERTS_SMS_HTTP_TOKEN"),
        )

    def _post_json(
        self,
        url: str,
        payload: dict[str, str],
        *,
        token: str | None = None,
    ) -> None:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            response = client.post(url, json=payload, headers=headers)
            if not 200 <= response.status_code < 300:
                raise RuntimeError(f"provider returned HTTP {response.status_code}")

    def _required(self, name: str) -> str:
        value = self._env.get(name, "").strip()
        if not value:
            label = name.removeprefix("AGI_PROCESOR_ALERTS_").lower()
            raise ValueError(f"{label} is not configured")
        return value

    def _sms_max_chars(self) -> int:
        raw = self._env.get("AGI_PROCESOR_ALERTS_SMS_MAX_CHARS", "300").strip()
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError("sms_max_chars must be an integer") from exc
        if not 300 <= value <= 1000:
            raise ValueError("sms_max_chars must be between 300 and 1000")
        if value > 300 and not _truthy(
            self._env.get("AGI_PROCESOR_ALERTS_SMS_ALLOW_MULTIPART", "false")
        ):
            raise ValueError(
                "SMS budgets above 300 require explicit sms_allow_multipart=true"
            )
        return value

    def _https_url(self, name: str):
        value = self._required(name)
        parsed = urlparse(value)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            label = name.removeprefix("AGI_PROCESOR_ALERTS_").lower()
            raise ValueError(f"{label} must be an HTTPS URL")
        if parsed.username or parsed.password:
            raise ValueError("Credentials must not be embedded in provider URLs")
        return parsed


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _clip(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    if limit <= 3:
        return compact[:limit]
    return compact[: limit - 3] + "..."


__all__ = ["AlertDispatcher", "DispatchResult", "render_alert", "render_sms"]
