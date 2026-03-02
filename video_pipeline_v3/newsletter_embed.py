#!/usr/bin/env python3
"""Newsletter embed — HTML email snippet with thumbnail + watch button.
Uses Resend API for email delivery when API key is available."""
import os, json
from datetime import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key


def generate_email_html(episode_title: str, thumbnail_url: str = "",
                        video_url: str = "", segments_summary: list = None,
                        btc_price: str = "N/A") -> str:
    """Generate HTML email snippet for newsletter embedding.

    Args:
        episode_title: Episode title
        thumbnail_url: URL to thumbnail image
        video_url: YouTube or direct video URL
        segments_summary: List of segment headlines
        btc_price: Current BTC price string

    Returns:
        HTML string for email body.
    """
    date_str = datetime.now().strftime("%B %d, %Y")
    segments_html = ""
    if segments_summary:
        items = "".join(f"<li style='margin:4px 0;color:#ccc;'>{s}</li>" for s in segments_summary)
        segments_html = f"<ul style='padding-left:20px;margin:12px 0;'>{items}</ul>"

    thumbnail_block = ""
    if thumbnail_url:
        thumbnail_block = f"""
        <a href="{video_url or '#'}" style="display:block;margin:16px 0;">
          <img src="{thumbnail_url}" alt="{episode_title}"
               style="width:100%;max-width:640px;border-radius:8px;border:1px solid #222;" />
        </a>"""

    watch_button = ""
    if video_url:
        watch_button = f"""
        <a href="{video_url}"
           style="display:inline-block;background:#CC0000;color:white;
                  padding:12px 32px;border-radius:6px;text-decoration:none;
                  font-weight:bold;font-size:16px;margin:16px 0;">
          ▶ WATCH NOW
        </a>"""

    return f"""
<div style="max-width:640px;margin:0 auto;background:#0A0A0A;border:1px solid #1a1a1a;
            border-radius:12px;overflow:hidden;font-family:Arial,sans-serif;">

  <!-- Header -->
  <div style="background:#111;padding:16px 24px;border-bottom:2px solid #CC0000;">
    <span style="color:#666;font-size:12px;letter-spacing:2px;">PROTOCOL PULSE</span>
    <h2 style="color:white;margin:4px 0 0;font-size:20px;">PULSE CHECK</h2>
    <span style="color:#888;font-size:13px;">{date_str} | BTC {btc_price}</span>
  </div>

  <!-- Thumbnail -->
  <div style="padding:0 24px;">{thumbnail_block}</div>

  <!-- Title -->
  <div style="padding:0 24px;">
    <h3 style="color:white;font-size:22px;margin:12px 0 8px;">{episode_title}</h3>
  </div>

  <!-- Segments -->
  <div style="padding:0 24px;font-size:14px;">{segments_html}</div>

  <!-- CTA -->
  <div style="padding:16px 24px;text-align:center;">{watch_button}</div>

  <!-- Footer -->
  <div style="background:#080808;padding:12px 24px;border-top:1px solid #1a1a1a;
              text-align:center;">
    <span style="color:#555;font-size:11px;">Protocol Pulse — Bitcoin Intelligence Daily — Stay Sovereign</span>
  </div>
</div>"""


def send_newsletter(html: str, subject: str, to_email: str = "",
                    from_email: str = "pulse@protocolpulse.io") -> bool:
    """Send newsletter via Resend API.

    Args:
        html: Email HTML body
        subject: Email subject line
        to_email: Recipient (or list ID)
        from_email: Sender address

    Returns:
        True if sent successfully.
    """
    if not HAS_REQUESTS:
        print("  [newsletter] requests library not available")
        return False

    api_key = get_key("RESEND_API_KEY")
    if not api_key:
        print("  [newsletter] RESEND_API_KEY not available, HTML saved only")
        return False

    if not to_email:
        print("  [newsletter] No recipient specified, HTML saved only")
        return False

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "html": html,
            },
            timeout=30,
        )
        if r.status_code in (200, 201):
            print(f"  [newsletter] Email sent to {to_email}")
            return True
        else:
            print(f"  [newsletter] Resend API error {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  [newsletter] Error: {e}")
        return False


def save_newsletter_html(html: str, output_path: str) -> str:
    """Save newsletter HTML to file."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
    print(f"  [newsletter] HTML saved: {output_path}")
    return output_path


if __name__ == "__main__":
    html = generate_email_html(
        "The Hash Rate Hammer",
        segments_summary=["Mining Difficulty Record", "Sovereign Funds Buying"],
        btc_price="$97,000",
    )
    base = os.path.dirname(os.path.abspath(__file__))
    save_newsletter_html(html, os.path.join(base, "output", "test_newsletter.html"))
