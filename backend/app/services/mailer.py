"""Email (22 Oct 2026): sign-up codes, password reset links, invites and approval notices.

Any SMTP provider works (Gmail with an app password, Brevo, Resend, SendGrid, Amazon SES…): set
NOWBUILDER_SMTP_HOST / PORT / USER / PASSWORD / SECURITY and NOWBUILDER_MAIL_FROM. In development with no
SMTP host, nothing is sent: emails are kept in memory and shown at /dev/outbox, so the whole flow can
be tried on a laptop. Codes and links never appear in logs.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from html import escape

from ..config import get_settings

log = logging.getLogger("nowbuilder.mail")
_OUTBOX: deque[dict] = deque(maxlen=50)
_lock = threading.Lock()


class MailError(Exception):
    """Shown to the user: the email couldn't be sent."""


@dataclass
class Mail:
    to: str
    subject: str
    text: str
    html: str
    kind: str = "notice"
    at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def outbox() -> list[dict]:
    with _lock:
        return list(reversed(_OUTBOX))


def clear_outbox() -> None:
    with _lock:
        _OUTBOX.clear()


def send(mail: Mail) -> None:
    """Send now; raises MailError when the mail server refuses or can't be reached."""
    s = get_settings()
    if s.dev_outbox:
        with _lock:
            _OUTBOX.append(asdict(mail))
        log.info("Dev outbox: %s email to %s (open /dev/outbox to read it)", mail.kind, mail.to)
        return
    if not s.smtp_host.strip():
        raise MailError("nowBuilder can't send email yet: the server has no mail settings (NOWBUILDER_SMTP_HOST). Ask the nowBuilder team.")
    msg = EmailMessage()
    name, addr = parseaddr(s.mail_from)
    login = s.smtp_user.strip()
    msg["From"] = formataddr((name or "nowBuilder", addr or login))
    msg["To"] = mail.to
    msg["Subject"] = mail.subject
    msg.set_content(mail.text)
    msg.add_alternative(mail.html, subtype="html")
    # The envelope sender is the account we sign in with (Gmail and most providers refuse others);
    # the From header keeps NOWBUILDER_MAIL_FROM's display name.
    envelope = login if "@" in login else (addr or login)
    try:
        mode = s.smtp_security.strip().lower()
        if mode == "ssl":
            server = smtplib.SMTP_SSL(s.smtp_host.strip(), s.smtp_port, timeout=15, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(s.smtp_host.strip(), s.smtp_port, timeout=15)
            if mode == "starttls":
                server.starttls(context=ssl.create_default_context())
        with server:
            if login:
                server.login(login, s.smtp_password.replace(" ", "") if "gmail" in s.smtp_host else s.smtp_password)
            server.send_message(msg, from_addr=envelope)
    except (smtplib.SMTPException, OSError) as e:
        log.warning("Couldn't send %s email to %s: %s", mail.kind, mail.to, explain(e))
        raise MailError("nowBuilder couldn't send the email right now. Try again in a minute.") from e


def explain(e: Exception) -> str:
    """The mail server's own answer plus what to check, for the backend log (never the password)."""
    s = get_settings()
    code = getattr(e, "smtp_code", None)
    raw = getattr(e, "smtp_error", b"")
    reply = (raw.decode(errors="replace") if isinstance(raw, bytes) else str(raw)).replace("\n", " ").strip()
    said = f"{type(e).__name__} {code or ''} {reply}".strip()
    if not s.smtp_user.strip():
        return f"{said}. NOWBUILDER_SMTP_USER is empty, so nowBuilder didn't sign in to {s.smtp_host}. Set it to the full email address."
    if "smtpclientauthentication is disabled" in reply.lower() or "5.7.139" in reply:
        return (f"{said}. Microsoft 365: your organisation (or this mailbox) doesn't allow apps to send mail with a password "
                "(Authenticated SMTP is off). Only its IT admin can change that. Use another mail account (for example Gmail with an "
                "App password) or a sending service such as Brevo.")
    if isinstance(e, smtplib.SMTPAuthenticationError) or code in (534, 535):
        if "gmail" in s.smtp_host.lower():
            return f"{said}. Gmail didn't accept NOWBUILDER_SMTP_USER / NOWBUILDER_SMTP_PASSWORD. Use a 16-letter App password (2-Step Verification on) for that same Gmail account, not your normal password."
        return f"{said}. The mail server didn't accept NOWBUILDER_SMTP_USER / NOWBUILDER_SMTP_PASSWORD. Check them with your mail provider."
    if isinstance(e, smtplib.SMTPSenderRefused):
        return f"{said}. The server refused the sender. Use your sign-in address in NOWBUILDER_MAIL_FROM (for Gmail: nowBuilder <{s.smtp_user.strip()}>), or verify that sender with your provider."
    if isinstance(e, smtplib.SMTPRecipientsRefused):
        return f"{said}. The server refused the recipient address."
    if code == 550 or "quota" in reply.lower() or "limit" in reply.lower():
        return f"{said}. Probably the provider's daily sending limit; it resets within 24 hours."
    if isinstance(e, (OSError, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected)):
        return f"{type(e).__name__}: {e}. Check NOWBUILDER_SMTP_HOST ({s.smtp_host}), NOWBUILDER_SMTP_PORT ({s.smtp_port}) and NOWBUILDER_SMTP_SECURITY ({s.smtp_security})."
    return said


def send_later(mail: Mail) -> None:
    """Best effort, in the background: for notices that must never slow down or block the action."""
    def run() -> None:
        try:
            send(mail)
        except MailError:
            pass
    threading.Thread(target=run, daemon=True).start()


# ---------- templates ----------

def _page(title: str, body_html: str) -> str:
    return (
        '<!doctype html><html><body style="margin:0;background:#f3f6fb;font-family:Segoe UI,Arial,sans-serif;color:#15233b">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:32px 12px"><tr><td align="center">'
        '<table role="presentation" width="520" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border:1px solid #dfe5ef;border-radius:14px">'
        '<tr><td style="padding:28px 32px 8px;font-size:18px;font-weight:600;color:#1d5fd6">nowBuilder</td></tr>'
        f'<tr><td style="padding:8px 32px 28px;font-size:15px;line-height:1.55">'
        f'<h1 style="font-size:20px;margin:0 0 14px">{escape(title)}</h1>{body_html}</td></tr>'
        '</table><p style="font-size:12px;color:#7a869c;margin:16px 0 0">You got this email because of an action in nowBuilder. '
        'If it wasn\'t you, you can ignore it.</p></td></tr></table></body></html>'
    )


def _button(url: str, label: str) -> str:
    return (f'<p style="margin:22px 0"><a href="{escape(url)}" style="background:#1d5fd6;color:#ffffff;text-decoration:none;'
            f'padding:12px 20px;border-radius:9px;font-weight:600;display:inline-block">{escape(label)}</a></p>'
            f'<p style="font-size:13px;color:#4a5872">Or open this link: <br><span style="word-break:break-all">{escape(url)}</span></p>')


def verification_code(to: str, first_name: str, code: str, minutes: int) -> Mail:
    return Mail(
        to=to, kind="verify", subject=f"{code} is your nowBuilder code",
        text=f"Hi {first_name},\n\nYour nowBuilder code is {code}. Type it on the sign-up page to confirm your email.\n"
             f"It works for {minutes} minutes.\n\nIf you didn't create a nowBuilder account, ignore this email.",
        html=_page("Confirm your email",
                   f"<p>Hi {escape(first_name)},</p><p>Type this code in nowBuilder to confirm your email:</p>"
                   f'<p style="font-size:30px;font-weight:700;letter-spacing:8px;margin:18px 0;font-family:Consolas,monospace">{code}</p>'
                   f"<p style=\"color:#4a5872\">It works for {minutes} minutes. If you didn't create a nowBuilder account, ignore this email.</p>"),
    )


def password_reset(to: str, first_name: str, url: str, minutes: int) -> Mail:
    return Mail(
        to=to, kind="reset", subject="Reset your nowBuilder password",
        text=f"Hi {first_name},\n\nOpen this link to choose a new nowBuilder password:\n{url}\n\nIt works once, for {minutes} minutes. "
             "If you didn't ask for this, ignore this email: your password stays the same.",
        html=_page("Reset your password",
                   f"<p>Hi {escape(first_name)},</p><p>Someone (hopefully you) asked to reset your nowBuilder password.</p>"
                   + _button(url, "Choose a new password")
                   + f"<p style=\"color:#4a5872\">The link works once, for {minutes} minutes. If you didn't ask for this, ignore this email: your password stays the same.</p>"),
    )


def invite(to: str, inviter: str, workspace: str, role: str, url: str, days: int) -> Mail:
    return Mail(
        to=to, kind="invite", subject=f"{inviter} invited you to {workspace} on nowBuilder",
        text=f"{inviter} invited you to work in {workspace} on nowBuilder as {role}.\n\nJoin here: {url}\n\nThe invite works for {days} days.",
        html=_page(f"Join {workspace} on nowBuilder",
                   f"<p><strong>{escape(inviter)}</strong> invited you to work in <strong>{escape(workspace)}</strong> as <strong>{escape(role)}</strong>.</p>"
                   "<p>nowBuilder plans, builds, checks and deploys ServiceNow changes from plain-language requirements.</p>"
                   + _button(url, f"Join {workspace}") + f"<p style=\"color:#4a5872\">The invite works for {days} days.</p>"),
    )


def signup_waiting(to: str, person: str, email: str, workspace: str, url: str) -> Mail:
    return Mail(
        to=to, kind="approval-needed", subject=f"{person} is waiting for approval on nowBuilder",
        text=f"{person} ({email}) signed up and confirmed their email. {workspace} is waiting for your approval.\n\nReview it: {url}",
        html=_page("A new workspace is waiting",
                   f"<p><strong>{escape(person)}</strong> ({escape(email)}) signed up and confirmed their email.</p>"
                   f"<p><strong>{escape(workspace)}</strong> is waiting for your approval.</p>" + _button(url, "Review on Platform")),
    )


def approved(to: str, first_name: str, workspace: str, instances: int, members: int, url: str) -> Mail:
    o, m = f"{instances} ServiceNow instance{'s' if instances != 1 else ''}", f"{members} member{'s' if members != 1 else ''}"
    return Mail(
        to=to, kind="approved", subject=f"{workspace} is approved: you can start using nowBuilder",
        text=f"Hi {first_name},\n\n{workspace} is approved. You can connect up to {o} and have up to {m}.\n\nOpen nowBuilder: {url}",
        html=_page("You're approved",
                   f"<p>Hi {escape(first_name)},</p><p><strong>{escape(workspace)}</strong> is approved. "
                   f"You can connect up to {instances} ServiceNow instance{'s' if instances != 1 else ''} and have up to {members} member{'s' if members != 1 else ''}.</p>"
                   "<p>Start by connecting your ServiceNow instance and adding your AI provider.</p>" + _button(url, "Open nowBuilder")),
    )
