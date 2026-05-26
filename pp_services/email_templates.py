"""
F5 EMAIL TEMPLATES — Protocol Pulse
====================================
Dark-themed (#0a0a0a) email templates for double opt-in newsletter flow.
All templates use inline CSS for email client compatibility.
"""

SITE_URL_DEFAULT = "https://protocolpulse.io"


def _wrapper(inner_html: str) -> str:
    """Wrap inner content in the standard dark email shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
</head>
<body style="margin:0;padding:0;background:#080808;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#080808;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px;width:100%;background:#0d0d0d;
                      border:1px solid #1e1e1e;border-radius:8px;overflow:hidden;">
{inner_html}
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _header() -> str:
    return """
          <tr>
            <td style="padding:32px;background:linear-gradient(135deg,#0d0d0d 0%,#130000 100%);
                       border-bottom:2px solid #dc2626;text-align:center;">
              <p style="margin:0 0 6px;font-size:24px;font-weight:800;
                         letter-spacing:4px;color:#dc2626;font-family:monospace;">
                PROTOCOL PULSE
              </p>
              <p style="margin:0;font-size:12px;color:#555;
                         text-transform:uppercase;letter-spacing:2px;">
                Bitcoin Intelligence
              </p>
            </td>
          </tr>"""


def _footer(unsubscribe_url: str, site_url: str) -> str:
    return f"""
          <tr>
            <td style="padding:20px 32px;border-top:1px solid #1a1a1a;
                       background:#0a0a0a;text-align:center;">
              <p style="margin:0 0 8px;font-size:12px;color:#444;">
                <a href="{unsubscribe_url}"
                   style="color:#dc2626;text-decoration:none;">Unsubscribe</a>
                &nbsp;&bull;&nbsp;
                <a href="{site_url}" style="color:#555;text-decoration:none;">
                  protocolpulse.io
                </a>
              </p>
              <p style="margin:8px 0 0;font-size:11px;color:#333;">
                Protocol Pulse by Consensus Protocol LLC, Naples FL
              </p>
            </td>
          </tr>"""


def confirmation_email(confirm_url: str, email: str, site_url: str = SITE_URL_DEFAULT) -> dict:
    """
    Double opt-in confirmation email.
    Returns {subject, html}.
    """
    inner = _header() + f"""
          <tr>
            <td style="padding:40px 32px;">
              <h1 style="margin:0 0 8px;font-size:28px;font-weight:800;color:#F8C15C;
                         letter-spacing:1px;text-align:center;">
                SIGNAL RECEIVED
              </h1>
              <p style="margin:0 0 24px;font-size:13px;color:#555;text-align:center;
                         text-transform:uppercase;letter-spacing:2px;">
                Confirm your subscription
              </p>
              <p style="margin:0 0 20px;font-size:15px;color:#b0b0b0;line-height:1.7;">
                You requested to join the <strong style="color:#fff;">Protocol Pulse</strong>
                daily Bitcoin intelligence briefing. Every morning you'll receive:
              </p>

              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#111;border:1px solid #1e1e1e;
                            border-radius:6px;margin-bottom:28px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0 0 8px;font-size:14px;color:#d0d0d0;">
                      &#9654;&nbsp; Top stories from 80+ sources, distilled to 5 minutes
                    </p>
                    <p style="margin:0 0 8px;font-size:14px;color:#d0d0d0;">
                      &#9654;&nbsp; Oracle Signal score and market intelligence
                    </p>
                    <p style="margin:0;font-size:14px;color:#d0d0d0;">
                      &#9654;&nbsp; Network stats, hashrate, and on-chain data
                    </p>
                  </td>
                </tr>
              </table>

              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                <tr>
                  <td align="center">
                    <a href="{confirm_url}"
                       style="display:inline-block;padding:16px 40px;
                              background:#F8C15C;color:#000;font-size:15px;
                              font-weight:800;text-decoration:none;
                              border-radius:6px;letter-spacing:1px;
                              font-family:monospace;">
                      CONFIRM SUBSCRIPTION
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin:0;font-size:12px;color:#555;text-align:center;line-height:1.6;">
                If you didn't request this, you can safely ignore this email.
                <br>This link expires in 48 hours.
              </p>
            </td>
          </tr>

          <tr>
            <td style="padding:16px 32px;border-top:1px solid #1a1a1a;
                       background:#0a0a0a;text-align:center;">
              <p style="margin:0;font-size:11px;color:#333;">
                Protocol Pulse by Consensus Protocol LLC, Naples FL
              </p>
            </td>
          </tr>"""

    return {
        "subject": "Confirm your Protocol Pulse Intel feed",
        "html": _wrapper(inner),
    }


def welcome_email(unsubscribe_url: str, site_url: str = SITE_URL_DEFAULT) -> dict:
    """
    Welcome email sent immediately on signup.
    PBX voice — direct, cypherpunk, no filler.
    Returns {subject, html}.
    """
    inner = _header() + f"""
          <tr>
            <td style="padding:40px 32px;">
              <h1 style="margin:0 0 8px;font-size:28px;font-weight:800;color:#F8C15C;
                         letter-spacing:1px;text-align:center;">
                YOU'RE IN.
              </h1>
              <p style="margin:0 0 28px;font-size:13px;color:#555;text-align:center;
                         text-transform:uppercase;letter-spacing:2px;">
                The signal is locked
              </p>

              <p style="margin:0 0 16px;font-size:15px;color:#b0b0b0;line-height:1.8;">
                Most people wake up to noise. You just opted into signal.
              </p>
              <p style="margin:0 0 24px;font-size:15px;color:#b0b0b0;line-height:1.8;">
                Every morning at <strong style="color:#F8C15C;">6:45 AM ET</strong>,
                Protocol Pulse lands in your inbox. No opinions. No filler.
                Just the intelligence that moves markets &mdash; distilled to five minutes.
              </p>

              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#111;border:1px solid #1e1e1e;
                            border-radius:6px;margin-bottom:28px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0 0 12px;font-size:11px;text-transform:uppercase;
                               letter-spacing:2px;color:#dc2626;font-weight:700;">
                      WHAT HITS YOUR INBOX
                    </p>
                    <p style="margin:0 0 10px;font-size:14px;color:#d0d0d0;line-height:1.6;">
                      &#9654;&nbsp; <strong style="color:#fff;">Daily Intelligence Brief</strong>
                      &mdash; top stories from 80+ sources, verified against on-chain data
                    </p>
                    <p style="margin:0 0 10px;font-size:14px;color:#d0d0d0;line-height:1.6;">
                      &#9654;&nbsp; <strong style="color:#fff;">Oracle Signal Score</strong>
                      &mdash; our proprietary sentiment + velocity reading on Bitcoin
                    </p>
                    <p style="margin:0 0 10px;font-size:14px;color:#d0d0d0;line-height:1.6;">
                      &#9654;&nbsp; <strong style="color:#fff;">Network Pulse</strong>
                      &mdash; hashrate, difficulty, mempool pressure, whale movements
                    </p>
                    <p style="margin:0;font-size:14px;color:#d0d0d0;line-height:1.6;">
                      &#9654;&nbsp; <strong style="color:#fff;">Macro Context</strong>
                      &mdash; the geopolitical signals most analysts sleep through
                    </p>
                  </td>
                </tr>
              </table>

              <p style="margin:0 0 28px;font-size:14px;color:#888;line-height:1.7;
                         border-left:3px solid #dc2626;padding-left:16px;">
                This is the free tier. It's already better than 90% of what's out there.
                But if you want the real edge &mdash; live terminal, sovereign API keys,
                on-chain alerts before they hit Twitter &mdash; Commander access is where
                operators live.
              </p>

              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
                <tr>
                  <td align="center">
                    <a href="{site_url}/terminal"
                       style="display:inline-block;padding:16px 40px;
                              background:#dc2626;color:#fff;font-size:15px;
                              font-weight:800;text-decoration:none;
                              border-radius:6px;letter-spacing:1px;
                              font-family:monospace;">
                      UNLOCK COMMANDER ACCESS &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin:0;font-size:13px;color:#555;text-align:center;
                         font-family:monospace;">
                6:45 AM ET. Every day. No exceptions.<br>
                Stay sovereign.
              </p>
            </td>
          </tr>
""" + _footer(unsubscribe_url, site_url)

    return {
        "subject": "Welcome to Protocol Pulse",
        "html": _wrapper(inner),
    }


def digest_email(articles_list: list, unsubscribe_url: str,
                 site_url: str = SITE_URL_DEFAULT) -> dict:
    """
    Daily digest email with article cards.
    articles_list: [{title, summary, cover_image_url, url}, ...]
    Returns {subject, html}.
    """
    top_headline = articles_list[0]["title"] if articles_list else "Today's Intel"

    articles_html = ""
    for art in articles_list:
        img_html = ""
        cover = art.get("cover_image_url", "")
        if cover:
            img_html = f"""
                    <img src="{cover}" alt="" width="560" height="200"
                         style="display:block;width:100%;max-height:200px;
                                object-fit:cover;border-radius:4px;margin-bottom:12px;">"""

        summary = art.get("summary", "")[:250]
        url = art.get("url", site_url)
        articles_html += f"""
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="margin-bottom:20px;border-bottom:1px solid #1e1e1e;padding-bottom:20px;">
                <tr>
                  <td>{img_html}
                    <a href="{url}"
                       style="color:#fff;font-size:17px;font-weight:700;
                              text-decoration:none;line-height:1.35;display:block;
                              margin-bottom:8px;">
                      {art.get('title', 'Untitled')}
                    </a>
                    <p style="margin:0 0 10px;color:#888;font-size:14px;line-height:1.6;">
                      {summary}
                    </p>
                    <a href="{url}"
                       style="color:#dc2626;font-size:13px;font-weight:600;
                              text-decoration:none;letter-spacing:0.5px;">
                      READ MORE &rarr;
                    </a>
                  </td>
                </tr>
              </table>"""

    inner = _header() + f"""
          <tr>
            <td style="padding:28px 32px 8px;">
              {articles_html}
            </td>
          </tr>

          <tr>
            <td style="padding:4px 32px 28px;text-align:center;">
              <a href="{site_url}"
                 style="display:inline-block;padding:13px 32px;
                        background:#dc2626;color:#fff;font-size:14px;
                        font-weight:700;text-decoration:none;
                        border-radius:6px;letter-spacing:0.5px;">
                Read Full Briefing at protocolpulse.io &rarr;
              </a>
            </td>
          </tr>
""" + _footer(unsubscribe_url, site_url)

    return {
        "subject": f"Protocol Pulse Intel: {top_headline}",
        "html": _wrapper(inner),
    }
