"""Transactional email via Amazon SES.

Three messages: verify-your-email, reset-your-password, and a login OTP code.
All sent from the verified domain nipunacareers.com as no-reply@.

On Lambda the SES call is authorised by the execution role (which carries
ses:SendEmail on identity/nipunacareers.com); locally boto3 falls through to the
static AWS keys in .env. Either way no credentials are handled here.

**Sandbox caveat, deliberately not worked around:** while the SES account is in
the sandbox, SES only delivers to verified recipient addresses and rejects
everything else at send time. Those failures raise EmailSendError, which the
auth routes log and, for the enumeration-safe flows (OTP request, forgot
password), swallow — so a bounce never tells a caller whether an address exists.
"""

import os

from botocore.exceptions import BotoCoreError, ClientError

# Where the emailed links point. The frontend is same-origin with the API behind
# CloudFront, so this is just the public site.
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://nipunacareers.com").rstrip("/")

SENDER = os.getenv("MAIL_SENDER", "Nipuna Careers <no-reply@nipunacareers.com>")

# SES identities are per-region; the verified domain lives in the Lambda's own
# region, which is also where AWS_REGION points.
_SES_REGION = os.getenv("AWS_REGION", "ap-south-1")


class EmailSendError(Exception):
    """SES refused the message — sandbox recipient, throttle, or misconfig."""


def _client():
    # Imported lazily so importing this module (and the whole app) does not
    # construct a boto3 client at cold start for a request that sends no mail.
    import boto3

    return boto3.client("sesv2", region_name=_SES_REGION)


def _send(to: str, subject: str, html: str, text: str) -> None:
    try:
        _client().send_email(
            FromEmailAddress=SENDER,
            Destination={"ToAddresses": [to]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": text, "Charset": "UTF-8"},
                        "Html": {"Data": html, "Charset": "UTF-8"},
                    },
                }
            },
        )
    except (BotoCoreError, ClientError) as exc:
        raise EmailSendError(f"SES refused mail to {to}: {exc}") from exc


def _shell(title: str, body_html: str) -> str:
    """A minimal, client-safe HTML wrapper. Inline styles only — email clients
    strip <style> and <head>, and Solarized-dark tones would be unreadable on a
    white mail client, so this stays light and neutral."""
    return f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
            max-width:480px;margin:0 auto;padding:24px;color:#0f172a">
  <h1 style="font-size:20px;margin:0 0 16px">{title}</h1>
  {body_html}
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
  <p style="font-size:12px;color:#64748b;margin:0">
    Nipuna Careers · If you did not request this, you can ignore this email.
  </p>
</div>"""


def _button(url: str, label: str) -> str:
    return (
        f'<p style="margin:20px 0"><a href="{url}" '
        'style="background:#2563eb;color:#fff;text-decoration:none;padding:12px 20px;'
        'border-radius:8px;display:inline-block;font-weight:600">'
        f'{label}</a></p>'
        f'<p style="font-size:13px;color:#64748b;word-break:break-all">'
        f'Or paste this link into your browser:<br>{url}</p>'
    )


def send_verification_email(to: str, token: str) -> None:
    url = f"{APP_BASE_URL}/verify-email?token={token}"
    html = _shell(
        "Confirm your email",
        "<p>Welcome to Nipuna Careers. Confirm this address to activate your "
        "account.</p>" + _button(url, "Verify email"),
    )
    text = f"Confirm your email to activate your Nipuna Careers account:\n{url}\n"
    _send(to, "Verify your Nipuna Careers email", html, text)


def send_reset_email(to: str, token: str) -> None:
    url = f"{APP_BASE_URL}/reset-password?token={token}"
    html = _shell(
        "Reset your password",
        "<p>We received a request to reset your password. This link expires in "
        "one hour and can be used once.</p>" + _button(url, "Set a new password"),
    )
    text = f"Reset your Nipuna Careers password (expires in 1 hour, single use):\n{url}\n"
    _send(to, "Reset your Nipuna Careers password", html, text)


def send_login_otp(to: str, code: str) -> None:
    html = _shell(
        "Your login code",
        f'<p>Enter this code to sign in. It expires in 10 minutes.</p>'
        f'<p style="font-size:32px;font-weight:700;letter-spacing:6px;margin:16px 0">{code}</p>',
    )
    text = f"Your Nipuna Careers login code is {code}. It expires in 10 minutes.\n"
    _send(to, f"{code} is your Nipuna Careers login code", html, text)
