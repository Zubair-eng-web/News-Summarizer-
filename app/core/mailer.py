import smtplib
import ssl
from email.message import EmailMessage

import httpx

from app.core.config import settings

RESEND_URL = "https://api.resend.com/emails"


def send_via_resend(msg: EmailMessage, http_post=None) -> None:
    """HTTPS (port 443) se email bhejta hai. Cloud ke free plans SMTP ports band kar dete hain."""
    html = msg.get_body(preferencelist=("html",))
    text = msg.get_body(preferencelist=("plain",))
    payload = {
        "from": str(msg["From"]),
        "to": [str(msg["To"])],
        "subject": str(msg["Subject"]),
    }
    if html is not None:
        payload["html"] = html.get_content()
    if text is not None:
        payload["text"] = text.get_content()

    post = http_post or httpx.post
    response = post(
        RESEND_URL,
        json=payload,
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Resend error {response.status_code}: {response.text[:200]}")


def deliver(build, smtp_class=None, http_post=None, receiver=None) -> None:
    """build(sender, receiver) -> EmailMessage. RESEND_API_KEY ho to HTTPS, warna Gmail SMTP."""
    receiver = receiver or settings.email_receiver

    if settings.resend_api_key and smtp_class is None:
        if not receiver:
            raise ValueError("EMAIL_RECEIVER set nahi hai")
        send_via_resend(build(settings.resend_from, receiver), http_post)
        return

    if not (settings.email_sender and settings.email_password and receiver):
        raise ValueError("EMAIL_SENDER / EMAIL_PASSWORD / EMAIL_RECEIVER .env me set nahi hain")

    msg = build(settings.email_sender, receiver)
    smtp_class = smtp_class or smtplib.SMTP_SSL
    context = ssl.create_default_context()
    with smtp_class("smtp.gmail.com", 465, context=context, timeout=30) as server:
        server.login(settings.email_sender, settings.email_password)
        server.send_message(msg)
