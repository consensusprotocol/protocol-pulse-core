# Protocol Pulse — Newsletter Engine (B1 Gospel)
# LAW 1: Resend API only (RESEND_API_KEY in .env)
# LAW 2: One newsletter per day maximum
# LAW 3: Dark cyberpunk HTML email (inline styles, Gmail/Outlook safe)
# LAW 4: CAN-SPAM compliant unsubscribe
#
# Cron: 0 12 * * * python3 -c 'from core.services.newsletter import NewsletterEngine; NewsletterEngine().send()'
# (12 UTC = 08:00 ET)

import os
import json
import uuid
import re
import logging
from datetime import datetime, timedelta, date

import resend

from app import db
import models

SITE_URL = os.environ.get('SITE_URL', 'https://protocolpulse.io')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
FROM_EMAIL = 'pulse@protocolpulse.io'
ADMIN_SECRET = os.environ.get('ADMIN_SECRET', '')


class NewsletterEngine:
    """B1 Gospel newsletter engine — Resend API, one per day, CAN-SPAM."""

    def __init__(self):
        resend.api_key = RESEND_API_KEY

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def already_sent_today(self) -> bool:
        """Check newsletter_sends for today's date (LAW 2)."""
        today_start = datetime.combine(date.today(), datetime.min.time())
        sent = models.NewsletterSend.query.filter(
            models.NewsletterSend.sent_at >= today_start
        ).first()
        return sent is not None

    def get_top_articles(self, n=5) -> list:
        """Top articles by published_at in the last 24 hours."""
        cutoff = datetime.utcnow() - timedelta(hours=24)
        articles = models.Article.query.filter(
            models.Article.published == True,
            models.Article.created_at >= cutoff
        ).order_by(models.Article.created_at.desc()).limit(n).all()
        return articles

    def get_oracle_signal(self) -> str:
        """Read today's signal from narrative_context.json."""
        paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'video_pipeline_v3', 'data', 'intelligence', 'narrative_context.json'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'intelligence', 'narrative_context.json'),
        ]
        for p in paths:
            try:
                with open(p, 'r') as f:
                    ctx = json.load(f)
                return ctx.get('episode_narrative', ctx.get('dominant_narrative', 'No signal available'))
            except (FileNotFoundError, json.JSONDecodeError):
                continue
        return 'Network signal unavailable'

    def _get_btc_price(self) -> str:
        """Fetch BTC price via price_service or fallback."""
        try:
            from services.price_service import price_service
            data = price_service.get_price()
            if data and data.get('usd'):
                return f"${data['usd']:,.0f}"
        except Exception:
            pass
        try:
            import requests as req
            r = req.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', timeout=5)
            p = r.json().get('bitcoin', {}).get('usd', 0)
            return f"${p:,.0f}"
        except Exception:
            return '$--,---'

    @staticmethod
    def _clean_summary(content, max_length=200):
        if not content:
            return ''
        clean = re.sub(r'<[^>]+>', '', content)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if len(clean) > max_length:
            clean = clean[:max_length].rsplit(' ', 1)[0] + '...'
        return clean

    # ------------------------------------------------------------------
    # Email builders
    # ------------------------------------------------------------------

    def build_html(self, articles, btc_price, signal, unsubscribe_token='TOKEN') -> str:
        """Build dark cyberpunk HTML email (inline styles, no CSS classes)."""
        today_str = datetime.utcnow().strftime('%B %d, %Y')

        # Top story
        top = articles[0] if articles else None
        top_title = top.title if top else 'No top story'
        top_url = f"{SITE_URL}/articles/{top.id}" if top else SITE_URL
        top_summary = self._clean_summary(top.content if top else '', 200)

        # Briefing articles (2-5)
        briefing = articles[1:5] if len(articles) > 1 else []

        briefing_rows = ''
        for a in briefing:
            cat = a.category or 'Bitcoin'
            briefing_rows += f'''
            <tr>
                <td style="padding: 10px 0; border-bottom: 1px solid #1a1a1a;">
                    <a href="{SITE_URL}/articles/{a.id}" style="color: #f4f5f8; text-decoration: none; font-size: 15px; font-weight: 600;">{a.title}</a>
                    <span style="display: inline-block; background: #1a1a1a; color: #FF0000; font-size: 10px; padding: 2px 8px; border-radius: 3px; margin-left: 8px; letter-spacing: 0.05em; text-transform: uppercase;">{cat}</span>
                    <div style="color: #888; font-size: 13px; margin-top: 4px;">{self._clean_summary(a.content, 100)}</div>
                </td>
            </tr>'''

        npub = os.environ.get('NOSTR_NPUB', '')
        npub_line = f'<p style="color:#555; font-size:11px; margin-top:8px;">npub: {npub}</p>' if npub else ''

        html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0; padding:0; background-color:#0a0a0a; font-family: Arial, Helvetica, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0a0a;">
<tr><td align="center" style="padding: 20px 0;">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#0a0a0a; max-width:600px; width:100%;">

    <!-- HEADER -->
    <tr><td style="background: linear-gradient(135deg, #0a0a0a 0%, #1a0000 100%); padding: 30px 24px; text-align: center; border-bottom: 2px solid #FF0000;">
        <h1 style="margin:0; color:#FF0000; font-size:28px; letter-spacing:0.15em; font-weight:800;">PROTOCOL PULSE</h1>
        <p style="margin:8px 0 0; color:#888; font-size:13px; letter-spacing:0.1em;">{today_str}</p>
        <p style="margin:6px 0 0; color:#F8C15C; font-size:18px; font-weight:700;">BTC: {btc_price}</p>
    </td></tr>

    <!-- TOP STORY -->
    <tr><td style="padding: 28px 24px 20px;">
        <p style="margin:0 0 10px; color:#FF0000; font-size:11px; letter-spacing:0.15em; text-transform:uppercase; font-weight:700;">TOP STORY</p>
        <a href="{top_url}" style="color:#f4f5f8; text-decoration:none; font-size:20px; font-weight:700; line-height:1.3;">{top_title}</a>
        <p style="color:#aaa; font-size:14px; line-height:1.5; margin:12px 0 0;">{top_summary}</p>
    </td></tr>

    <!-- BRIEFING -->
    <tr><td style="padding: 0 24px 20px;">
        <p style="margin:0 0 12px; color:#FF0000; font-size:11px; letter-spacing:0.15em; text-transform:uppercase; font-weight:700;">BRIEFING</p>
        <table width="100%" cellpadding="0" cellspacing="0">
            {briefing_rows}
        </table>
    </td></tr>

    <!-- NETWORK SIGNAL -->
    <tr><td style="padding: 20px 24px; background-color:#0f0f0f; border-left: 3px solid #F8C15C;">
        <p style="margin:0 0 8px; color:#F8C15C; font-size:11px; letter-spacing:0.15em; text-transform:uppercase; font-weight:700;">NETWORK SIGNAL</p>
        <p style="color:#ccc; font-size:14px; line-height:1.5; margin:0;">{signal}</p>
    </td></tr>

    <!-- CTA -->
    <tr><td align="center" style="padding: 30px 24px;">
        <a href="{SITE_URL}" style="display:inline-block; background:#FF0000; color:#fff; text-decoration:none; padding:14px 36px; font-size:14px; font-weight:700; letter-spacing:0.1em; border-radius:4px;">READ FULL BRIEFING &rarr;</a>
    </td></tr>

    <!-- FOOTER -->
    <tr><td style="padding: 20px 24px; border-top: 1px solid #1a1a1a; text-align:center;">
        <p style="color:#555; font-size:11px; margin:0;">You received this because you subscribed to Protocol Pulse.</p>
        <p style="margin:8px 0 0;"><a href="{SITE_URL}/unsubscribe?token={unsubscribe_token}" style="color:#FF0000; font-size:11px; text-decoration:underline;">Unsubscribe</a></p>
        {npub_line}
    </td></tr>

</table>
</td></tr></table>
</body>
</html>'''
        return html

    def build_text(self, articles, btc_price, signal) -> str:
        """Plain-text version of the newsletter."""
        today_str = datetime.utcnow().strftime('%B %d, %Y')
        lines = [
            f"PROTOCOL PULSE — {today_str}",
            f"BTC: {btc_price}",
            "",
            "═══ TOP STORY ═══",
        ]
        if articles:
            top = articles[0]
            lines.append(f"{top.title}")
            lines.append(f"{SITE_URL}/articles/{top.id}")
            lines.append(self._clean_summary(top.content, 200))
            lines.append("")

        lines.append("═══ BRIEFING ═══")
        for a in articles[1:5]:
            lines.append(f"• {a.title} [{a.category or 'Bitcoin'}]")
            lines.append(f"  {SITE_URL}/articles/{a.id}")
        lines.append("")
        lines.append("═══ NETWORK SIGNAL ═══")
        lines.append(signal)
        lines.append("")
        lines.append(f"Read full briefing: {SITE_URL}")
        lines.append("")
        lines.append(f"Unsubscribe: {SITE_URL}/unsubscribe?token=TOKEN")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Main send
    # ------------------------------------------------------------------

    def send(self) -> dict:
        """Assemble and send today's newsletter via Resend (LAW 1)."""
        if not RESEND_API_KEY:
            return {'success': False, 'error': 'RESEND_API_KEY not configured'}

        if self.already_sent_today():
            return {'success': False, 'error': 'Newsletter already sent today (LAW 2)'}

        articles = self.get_top_articles(5)
        if not articles:
            return {'success': False, 'error': 'No articles from last 24h'}

        btc_price = self._get_btc_price()
        signal = self.get_oracle_signal()
        today_str = datetime.utcnow().strftime('%b %d, %Y')
        subject = f"Protocol Pulse \u2014 {today_str} | BTC: {btc_price}"

        # Get active subscribers
        subscribers = models.NewsletterSubscriber.query.filter_by(subscribed=True).all()
        if not subscribers:
            return {'success': False, 'error': 'No active subscribers'}

        sent_count = 0
        errors = []
        first_message_id = None

        for sub in subscribers:
            html = self.build_html(articles, btc_price, signal, unsubscribe_token=sub.unsubscribe_token)
            text = self.build_text(articles, btc_price, signal)

            try:
                result = resend.Emails.send({
                    'from': f'Protocol Pulse <{FROM_EMAIL}>',
                    'to': [sub.email],
                    'subject': subject,
                    'html': html,
                    'text': text,
                })
                msg_id = result.get('id', '') if isinstance(result, dict) else str(result)
                if not first_message_id:
                    first_message_id = msg_id
                sent_count += 1
            except Exception as e:
                errors.append(f"{sub.email}: {e}")
                logging.error(f"Resend error for {sub.email}: {e}")

        # Record the send
        article_ids = json.dumps([a.id for a in articles])
        send_record = models.NewsletterSend(
            subject=subject,
            resend_message_id=first_message_id or '',
            recipient_count=sent_count,
            sent_at=datetime.utcnow(),
            article_ids=article_ids,
        )
        db.session.add(send_record)
        db.session.commit()

        logging.info(f"Newsletter sent to {sent_count}/{len(subscribers)} subscribers")

        return {
            'success': True,
            'sent_count': sent_count,
            'total_subscribers': len(subscribers),
            'errors': errors,
            'subject': subject,
        }


# ------------------------------------------------------------------
# Legacy compatibility — keep newsletter_service for existing routes
# ------------------------------------------------------------------

class NewsletterService:
    """Thin wrapper for backward compat with existing subscribe routes."""

    def __init__(self):
        self.enabled = bool(RESEND_API_KEY)

    def subscribe_user(self, email: str, name: str = None) -> bool:
        """Add to newsletter_subscribers table + User table."""
        try:
            # Newsletter subscribers table (CAN-SPAM with token)
            existing = models.NewsletterSubscriber.query.filter_by(email=email).first()
            if existing:
                if not existing.subscribed:
                    existing.subscribed = True
                    existing.unsubscribed_at = None
                    db.session.commit()
                    logging.info(f"Re-subscribed: {email}")
                    return True
                return True  # already subscribed
            sub = models.NewsletterSubscriber(
                email=email,
                unsubscribe_token=str(uuid.uuid4()),
                subscribed=True,
                source='api',
            )
            db.session.add(sub)

            # Also update User table if exists
            user = models.User.query.filter_by(email=email).first()
            if user:
                user.newsletter_subscribed = True
            else:
                user = models.User(
                    username=name or email.split('@')[0],
                    email=email,
                    newsletter_subscribed=True,
                )
                db.session.add(user)

            db.session.commit()
            logging.info(f"Subscribed: {email}")
            return True
        except Exception as e:
            db.session.rollback()
            logging.error(f"Subscribe error: {e}")
            return False


newsletter_service = NewsletterService()


# ------------------------------------------------------------------
# GHL Webhook Integration (preserved from original)
# ------------------------------------------------------------------

GHL_WEBHOOK_URL = os.environ.get('GHL_WEBHOOK_URL', '')


def send_daily_brief_to_ghl(ghl_webhook_url=None):
    """Send articles to GHL webhook for automated newsletter distribution."""
    import requests as req

    webhook_url = ghl_webhook_url or GHL_WEBHOOK_URL
    if not webhook_url:
        return {'status': 'skipped', 'reason': 'No webhook URL configured'}

    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        today_articles = models.Article.query.filter(
            models.Article.published == True,
            models.Article.created_at >= cutoff
        ).order_by(models.Article.created_at.desc()).limit(5).all()

        if not today_articles:
            return {'status': 'skipped', 'reason': 'No articles to send'}

        def clean(content, ml=200):
            if not content:
                return ''
            c = re.sub(r'<[^>]+>', '', content)
            c = re.sub(r'\s+', ' ', c).strip()
            return c[:ml].rsplit(' ', 1)[0] + '...' if len(c) > ml else c

        payload = {
            'email_subject': f"Protocol Pulse: The {datetime.utcnow().strftime('%B %d')} Brief",
            'send_date': datetime.utcnow().isoformat(),
            'article_count': len(today_articles),
            'articles': [
                {
                    'title': a.title,
                    'summary': clean(a.content, 200),
                    'category': a.category or 'Bitcoin',
                    'url': f"{SITE_URL}/articles/{a.id}",
                    'published_at': a.created_at.isoformat(),
                }
                for a in today_articles[:3]
            ],
            'headline': today_articles[0].title,
            'headline_url': f"{SITE_URL}/articles/{today_articles[0].id}",
            'site_url': SITE_URL,
            'unsubscribe_url': f"{SITE_URL}/unsubscribe",
        }

        resp = req.post(webhook_url, json=payload, headers={'Content-Type': 'application/json'}, timeout=30)

        if resp.status_code == 200:
            return {'status': 'success', 'articles_sent': len(today_articles), 'response_code': 200}
        return {'status': 'error', 'response_code': resp.status_code, 'error': resp.text}
    except Exception as e:
        logging.error(f"GHL error: {e}")
        return {'status': 'error', 'error': str(e)}
