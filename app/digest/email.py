"""Email delivery via Resend for weekly digests."""

import os

import resend


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
    confirm_url = f"{base}/digest/confirm?token={token}"

    resend.Emails.send(
        {
            "from": "crumb.blog <notes@crumb.blog>",
            "to": [email],
            "subject": "Confirm your subscription",
            "html": f"""\
<div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
  <p style="font-size: 16px; line-height: 1.6; color: #1a1a1a;">
    Someone (hopefully you) asked to receive weekly summaries
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
        }
    )


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
    unsub_url = f"{base}/digest/unsubscribe?token={unsubscribe_token}"

    resend.Emails.send(
        {
            "from": "crumb.blog <notes@crumb.blog>",
            "to": [email],
            "subject": f"Weekly summary: {digest_title}",
            "html": f"""\
<div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
  <p style="font-size: 16px; line-height: 1.6; color: #1a1a1a;">
    {digest_html}
  </p>
  <p style="margin: 24px 0;">
    <a href="{base}" style="font-size: 14px; color: #1a1a1a; text-decoration: underline;">
      See the full feed →
    </a>
  </p>
  <p style="font-size: 12px; color: #999;">
    You subscribed to weekly summaries from crumb.blog.<br />
    <a href="{unsub_url}" style="color: #999;">Unsubscribe</a>
  </p>
</div>""",
        }
    )
