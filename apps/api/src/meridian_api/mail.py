"""Send one email when an alert first crosses, then wait until it clears."""

from __future__ import annotations

import logging
import re
import smtplib
from collections import defaultdict
from decimal import Decimal
from email.message import EmailMessage

from meridian_config.settings import get_settings
from meridian_db.models import Alert, User, UserPreference
from meridian_db.session import session_scope
from sqlalchemy import select

from meridian_api.gateway import active_book
from meridian_api.portfolio_view import evaluate_alerts

LOGGER = logging.getLogger("meridian.alerts")
_ADDRESS = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_LOCAL = (".local", ".invalid", ".test", ".example")


def deliverable(address: str) -> bool:
    cleaned = address.strip()
    if not _ADDRESS.match(cleaned):
        return False
    host = cleaned.rsplit("@", 1)[1].lower()
    return not host.endswith(_LOCAL)


def smtp_ready() -> bool:
    settings = get_settings()
    return bool(settings.smtp_host.strip() and settings.smtp_from.strip())


def recipient(user: User | None, preference: UserPreference | None) -> str:
    chosen = "" if preference is None else preference.notify_email or ""
    if deliverable(chosen):
        return chosen.strip()
    account = "" if user is None else user.email
    if deliverable(account):
        return account.strip()
    return ""


def describe_alert(alert: Alert, quote) -> tuple[str, str]:
    ticker = alert.ticker or "Symbol"
    price = f"${quote.price.quantize(Decimal('0.01'))}"
    session = quote.as_of.isoformat()
    params = alert.params or {}
    rule = _rule(alert.alert_type, params)
    subject = f"Meridian alert: {ticker} {rule}"
    body = (
        f"{ticker} last closed at {price} on {session}.\n"
        f"The alert that matched is {rule}.\n\n"
        "The price is the last Nasdaq regular session, not a live quote. "
        "This note is not a recommendation to buy or sell."
    )
    return subject, body


def send_mail(address: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not smtp_ready() or not deliverable(address):
        return False
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = address.strip()
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as client:
            if settings.smtp_tls:
                client.starttls()
            if settings.smtp_user.strip():
                client.login(settings.smtp_user, settings.smtp_password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException):
        LOGGER.exception("alert email failed")
        return False
    return True


def sweep() -> None:
    settings = get_settings()
    with session_scope(settings.database_url) as db:
        alerts = list(db.scalars(select(Alert).where(Alert.enabled.is_(True))))
        if not alerts:
            return
        user_ids = {alert.user_id for alert in alerts}
        users = {user.id: user for user in db.scalars(select(User).where(User.id.in_(user_ids)))}
        preferences = {
            row.user_id: row for row in db.scalars(select(UserPreference).where(UserPreference.user_id.in_(user_ids)))
        }
        grouped: dict = defaultdict(list)
        for alert in alerts:
            grouped[alert.user_id].append(alert)
        book = active_book()
        ready = smtp_ready()
        for user_id, rows in grouped.items():
            address = recipient(users.get(user_id), preferences.get(user_id)) if ready else ""
            evaluate_alerts(rows, book, _notify(address) if address else None)


def _notify(address: str):
    def notify(alert: Alert, quote) -> bool:
        subject, body = describe_alert(alert, quote)
        return send_mail(address, subject, body)

    return notify


def _rule(kind: str, params: dict) -> str:
    direction = params.get("direction", "above")
    if kind == "percent":
        basis = _amount(params.get("basis"))
        target = _amount(params.get("target"))
        return f"{params.get('percent')}% {direction} ${basis} (${target})"
    if kind == "price":
        return f"price {direction} ${_amount(params.get('price'))}"
    if kind == "rsi":
        return f"RSI {direction} {params.get('level')}"
    return f"relative volume at or above {params.get('relativeVolume')}"


def _amount(value: object) -> str:
    text = str(value or "0").replace("$", "").replace(",", "")
    return f"{Decimal(text).quantize(Decimal('0.01'))}"
