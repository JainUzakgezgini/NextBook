"""Sends e-mail through an SMTP server (Gmail by default)."""
import smtplib
import ssl
import threading
from email.message import EmailMessage

from flask import current_app

# Used by the tests (MAIL_SUPPRESS_SEND=True): messages are stored here instead of sent.
outbox = []


def _send(app, msg):
    cfg = app.config
    try:
        with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=20) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            smtp.send_message(msg)
        app.logger.info("Password reset e-mail sent")
    except Exception as exc:  # never crash the page because of e-mail problems
        app.logger.error("Sending e-mail failed: %r", exc)


def send_email(to, subject, body, debug_link=None):
    """Send in the background, so every request takes the same time.

    (If only existing accounts made the page slow, an attacker could time the
    response to find out which e-mail addresses have an account.)
    """
    app = current_app._get_current_object()
    msg = EmailMessage()
    msg["From"] = f"NextBook <{app.config['MAIL_FROM']}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    if app.config.get("MAIL_SUPPRESS_SEND"):
        outbox.append(msg)
        return
    if not (app.config.get("MAIL_USERNAME") and app.config.get("MAIL_PASSWORD")):
        if app.debug and debug_link:
            # Local development without e-mail settings: show the link in the terminal instead.
            app.logger.warning("E-mail is not configured. Password reset link: %s", debug_link)
        else:
            app.logger.error("E-mail is not configured (MAIL_USERNAME / MAIL_PASSWORD missing in .env)")
        return
    threading.Thread(target=_send, args=(app, msg), daemon=True).start()
