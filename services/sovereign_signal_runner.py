#!/usr/bin/env python3
"""
The Sovereign Signal — Daily Newsletter Runner
Runs daily at 9am ET. Pulls live intel, runs 4-pass pipeline,
sends via Resend to all active newsletter subscribers.
"""
import os, sys, logging
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / 'core'))
sys.path.insert(0, str(BASE))

logging.basicConfig(
    level=logging.INFO,
    format="[sovereign_signal] %(asctime)s %(message)s",
    handlers=[
        logging.FileHandler(BASE / 'logs' / 'sovereign_signal.log'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger('sovereign_signal')

def _load_env():
    env = BASE / '.env'
    if env.exists():
        for line in env.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())
_load_env()

def _get_subscribers():
    from app import app
    from models import NewsletterSubscriber
    with app.app_context():
        subs = NewsletterSubscriber.query.filter_by(subscribed=True).all()
        return [s.email for s in subs if s.email and '@' in s.email and 'test' not in s.email.lower() and 'diagnostic' not in s.email.lower()]

def _get_intel_breakdowns():
    """Pull today's top articles as intel breakdowns for the digest pipeline."""
    try:
        from app import app
        from models import Article
        with app.app_context():
            arts = Article.query.filter(
                Article.published == True
            ).order_by(Article.created_at.desc()).limit(20).all()
            return [{
                'title': a.title,
                'summary': (a.summary or '')[:300],
                'category': a.category or 'Bitcoin',
                'url': a.source_url or '',
                'source': a.source_type or 'rss',
                'created_at': str(a.created_at),
            } for a in arts]
    except Exception as e:
        logger.error("Failed to fetch articles: %s", e)
        return []

def _build_html(content, subject):
    """Wrap Sovereign Signal content in clean email HTML."""
    # Convert markdown-ish formatting to HTML
    import re
    html_content = content
    # Bold **text**
    html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
    # Headers
    html_content = re.sub(r'^## (.+)$', r'<h2 style="color:#cc0000;font-family:Georgia,serif;margin:1.5rem 0 0.5rem;">\1</h2>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^# (.+)$', r'<h1 style="color:#fff;font-family:Georgia,serif;">\1</h1>', html_content, flags=re.MULTILINE)
    # Newlines to paragraphs
    paragraphs = html_content.split('\n\n')
    html_paras = ''.join(f'<p style="margin:0 0 1rem;line-height:1.7;">{p.strip()}</p>' for p in paragraphs if p.strip())

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="background:#0a0a0a;color:#e0e0e0;font-family:'Georgia',serif;max-width:640px;margin:0 auto;padding:0;">
  <div style="background:#0a0a0a;padding:2rem 2rem 1rem;">
    <div style="border-bottom:2px solid #cc0000;padding-bottom:1rem;margin-bottom:1.5rem;">
      <span style="font-family:'Courier New',monospace;font-size:.7rem;letter-spacing:.2em;text-transform:uppercase;color:#cc0000;">Protocol Pulse</span>
      <h1 style="font-size:1.6rem;font-weight:700;color:#fff;margin:.5rem 0 0;font-family:Georgia,serif;">The Sovereign Signal</h1>
    </div>
    <div style="font-size:.95rem;line-height:1.75;">{html_paras}</div>
    <div style="margin-top:2rem;padding-top:1rem;border-top:1px solid #222;font-family:'Courier New',monospace;font-size:.65rem;color:#555;text-align:center;">
      Protocol Pulse &middot; <a href="https://protocolpulse.io" style="color:#cc0000;">protocolpulse.io</a>
      &middot; <a href="https://protocolpulse.io/unsubscribe" style="color:#555;">unsubscribe</a>
    </div>
  </div>
</body>
</html>"""

def run():
    logger.info("=== Sovereign Signal daily run ===")

    # 1. Get subscribers (excluding test addresses)
    try:
        emails = _get_subscribers()
    except Exception as e:
        logger.error("Could not load subscribers: %s", e)
        # Fallback: direct DB query
        import sqlite3
        conn = sqlite3.connect(str(BASE / 'instance' / 'protocol_pulse.db'))
        rows = conn.execute("SELECT email FROM newsletter_subscribers WHERE subscribed=1").fetchall()
        emails = [r[0] for r in rows if r[0] and '@' in r[0] and 'test' not in r[0] and 'diagnostic' not in r[0]]
        conn.close()

    logger.info("Recipients: %d", len(emails))
    if not emails:
        logger.warning("No real subscribers yet — skipping send (will still generate draft)")

    # 2. Get intel
    breakdowns = _get_intel_breakdowns()
    logger.info("Intel items: %d", len(breakdowns))

    # 3. Run 4-pass Sovereign Signal pipeline
    try:
        from services.newsletter_digest import NewsletterDigestService
        svc = NewsletterDigestService()
        result = svc.generate_weekly_digest(breakdowns)
        if result.get('error'):
            logger.error("Digest pipeline error: %s", result['error'])
            return False
        content = result.get('final', result.get('tightened', ''))
        subject = result.get('subject', 'The Sovereign Signal — Protocol Pulse Intelligence Brief')
        logger.info("Digest generated: %d chars, subject: %s", len(content), subject)
    except Exception as e:
        logger.error("Digest pipeline failed: %s", e)
        # Fallback: use newsletter_engine's simpler generate
        try:
            from services.newsletter_engine import NewsletterEngine
            eng = NewsletterEngine()
            articles = _get_intel_breakdowns()
            summary = eng.generate_ai_summary([{'title': a['title'], 'summary': a['summary'], 'category': a['category']} for a in articles])
            content = summary
            subject = eng.generate_subject(eng.get_btc_price())
        except Exception as e2:
            logger.error("Fallback engine also failed: %s", e2)
            return False

    # 4. Send (or log draft if no real subscribers)
    html = _build_html(content, subject)

    if emails:
        try:
            from services.newsletter_engine import NewsletterEngine
            eng = NewsletterEngine()
            result = eng.send_newsletter(emails, subject=subject, html=html)
            logger.info("Send result: %s", result)
            if result.get('success'):
                logger.info("SENT to %d/%d recipients", result['sent'], result['total'])
                return True
            else:
                logger.error("Send failed: %s", result.get('error'))
                return False
        except Exception as e:
            logger.error("Send exception: %s", e)
            return False
    else:
        # Save draft for preview
        draft_path = BASE / 'data' / 'newsletter_drafts'
        draft_path.mkdir(exist_ok=True)
        from datetime import datetime
        fname = draft_path / f"sovereign_signal_{datetime.now().strftime('%Y%m%d')}.html"
        fname.write_text(html)
        logger.info("No real subscribers - draft saved to %s", fname)
        return True

if __name__ == '__main__':
    run()
