"""Email delivery via Resend for Trail Notes."""

import os

import resend
from dotenv import load_dotenv

load_dotenv()


def _get_base_url() -> str:
    return os.getenv("BASE_URL", "https://crumb.blog")


def _ensure_api_key() -> None:
    key = os.getenv("RESEND_API_KEY", "")
    if not key:
        raise RuntimeError("RESEND_API_KEY is not set")
    resend.api_key = key


def send_confirmation_email(email: str, token: str) -> None:
    """Send double opt-in confirmation email."""
    _ensure_api_key()
    base = _get_base_url()
    confirm_url = f"{base}/trail-notes/confirm?token={token}"

    resend.Emails.send({
        "from": "Trail Notes <notes@crumb.blog>",
        "to": [email],
        "subject": "You're on the path.",
        "html": f"""\
<div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
  <p style="font-size: 16px; line-height: 1.6; color: #1a1a1a;">
    Someone (hopefully you) asked to receive Trail Notes — a weekly letter
    from <a href="{base}" style="color: #1a1a1a;">crumb.blog</a>.
  </p>
  <p style="font-size: 16px; line-height: 1.6; color: #1a1a1a;">
    To confirm, just click the link below:
  </p>
  <p style="margin: 32px 0;">
    <a href="{confirm_url}"
       style="font-size: 16px; color: #1a1a1a; text-decoration: underline;">
      Yes, I'd like to follow along →
    </a>
  </p>
  <p style="font-size: 14px; color: #666;">
    If you didn't request this, just ignore this email. No harm done.
  </p>
</div>""",
    })


def send_digest_email(
    email: str,
    unsubscribe_token: str,
    digest_title: str,
    digest_html: str,
    digest_id: int,
) -> None:
    """Send a published digest to a confirmed subscriber."""
    _ensure_api_key()
    base = _get_base_url()
    unsub_url = f"{base}/trail-notes/unsubscribe?token={unsubscribe_token}"
    web_url = f"{base}/trail-notes/{digest_id}"

    resend.Emails.send({
        "from": "Trail Notes <notes@crumb.blog>",
        "to": [email],
        "subject": f"Trail Notes: {digest_title}",
        "html": f"""\
<div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
  {digest_html}
  <hr style="border: none; border-top: 1px solid #e5e5e5; margin: 32px 0;" />
  <p style="font-size: 14px; color: #666;">
    <a href="{web_url}" style="color: #666;">Read on the web →</a>
  </p>
  <p style="font-size: 12px; color: #999;">
    You're receiving this because you subscribed to Trail Notes on crumb.blog.<br />
    <a href="{unsub_url}" style="color: #999;">Unsubscribe</a>
  </p>
</div>""",
    })
