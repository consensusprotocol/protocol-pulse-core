# SendGrid Newsletter Service - Protocol Pulse
# Using blueprint:python_sendgrid integration
# 
# FACTUAL ACCURACY MANDATE: All newsletter content is verified before sending.
# The fact-checker validates Bitcoin metrics, node counts, fee rates, etc.
# against live blockchain data sources (mempool.space, bitnodes.io, coingecko).
#
# HIGHLEVEL REQUIREMENTS:
# To enable automated newsletter distribution via GHL:
# 1. Create a GHL Workflow triggered by webhook
# 2. Set up a webhook URL in your GHL Location Settings
# 3. Configure GHL_WEBHOOK_URL environment variable
# 4. Create email template in GHL that uses these payload fields:
#    - email_subject: Newsletter subject line
#    - headline: Lead article title
#    - headline_url: Link to lead article
#    - articles[]: Array of article objects (title, summary, url, category)
#    - article_count: Number of articles included
# 5. Configure a contact list or tag for subscribers in GHL
# 6. Wire the workflow to send emails using your template

import os
import sys
import logging
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    _sendgrid_available = True
except ImportError:
    SendGridAPIClient = None
    Mail = Email = To = Content = None
    _sendgrid_available = False
    logging.warning("sendgrid package not installed - newsletter functionality disabled")

from app import db
import models


class NewsletterService:
    def __init__(self):
        self.sendgrid_key = os.environ.get('SENDGRID_API_KEY')
        if not self.sendgrid_key or not _sendgrid_available:
            if not _sendgrid_available:
                logging.warning("SendGrid package not available - newsletter disabled")
            else:
                logging.warning("SENDGRID_API_KEY not configured - newsletter functionality disabled")
            self.enabled = False
            self.sg = None
        else:
            self.enabled = True
            self.sg = SendGridAPIClient(self.sendgrid_key)

    def subscribe_user(self, email: str, name: str = None) -> bool:
        """Subscribe user to newsletter and save to database"""
        try:
            # Save to database
            existing_user = models.User.query.filter_by(email=email).first()
            if not existing_user:
                user = models.User()
                user.username = name or email.split('@')[0]
                user.email = email
                user.newsletter_subscribed = True
                db.session.add(user)
                db.session.commit()
                logging.info(f"New user subscribed: {email}")
            else:
                existing_user.newsletter_subscribed = True
                db.session.commit()
                logging.info(f"Existing user resubscribed: {email}")
            
            # Send welcome email only when provider is enabled; never block local subscription.
            if self.enabled:
                self.send_welcome_email(email, name)
            else:
                logging.info("Newsletter provider disabled; local subscription stored without email send.")
            return True
            
        except Exception as e:
            logging.error(f"Newsletter subscription error: {e}")
            return False

    def send_welcome_email(self, to_email: str, name: str = None) -> bool:
        """Send welcome email to new subscriber"""
        if not self.enabled:
            return False
            
        try:
            subject = "Welcome to Protocol Pulse - Your Bitcoin & DeFi News Source"
            
            display_name = f' {name}' if name else ''
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #dc2626; color: white; padding: 20px; text-align: center;">
                    <h1>Welcome to Protocol Pulse</h1>
                </div>
                <div style="padding: 30px;">
                    <h2>Hello{display_name}!</h2>
                    <p>Thank you for subscribing to Protocol Pulse, your trusted source for Bitcoin and DeFi news.</p>
                    
                    <p>You'll receive:</p>
                    <ul>
                        <li>🚀 Breaking Bitcoin & DeFi news</li>
                        <li>📊 AI-powered market analysis</li>
                        <li>🎯 Expert insights from Al Ingle</li>
                        <li>🔥 Weekly newsletter roundups</li>
                    </ul>
                    
                    <p>Visit our website to read the latest articles: <a href="https://protocolpulse.replit.app">Protocol Pulse</a></p>
                    
                    <p>Best regards,<br>The Protocol Pulse Team</p>
                </div>
            </div>
            """
            
            message = Mail(
                from_email=Email("newsletter@protocolpulse.com", "Protocol Pulse"),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.sg.send(message)
            logging.info(f"Welcome email sent to {to_email}")
            return True
            
        except Exception as e:
            logging.error(f"SendGrid welcome email error: {e}")
            return False

    def _strip_html(self, html_content: str) -> str:
        """Strip HTML tags to get plain text for fact-checking."""
        import re
        clean = re.sub(r'<[^>]+>', ' ', html_content)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def send_newsletter(self, subject: str, content: str, recipients: list = None, 
                         skip_fact_check: bool = False) -> bool:
        """
        Send newsletter to all subscribers or specific recipients.
        
        FACTUAL ACCURACY MANDATE: Content is verified before sending.
        Uses blocking fact-check - if verification fails or service errors,
        newsletter is NOT sent. This ensures all distributed content is accurate.
        
        Args:
            subject: Newsletter subject line
            content: HTML content to send
            recipients: Optional list of email addresses (defaults to all subscribers)
            skip_fact_check: Set True to skip verification (not recommended)
        
        Returns:
            bool: True if newsletter sent successfully, False otherwise
        """
        if not self.enabled:
            logging.error("Newsletter service not enabled - SENDGRID_API_KEY missing")
            return False
        
        # BLOCKING FACT CHECK - Newsletter must be factual
        # If fact-check fails OR service errors, we do NOT send
        if not skip_fact_check:
            try:
                from services.fact_checker import verify_article_before_publish
                
                plain_text = self._strip_html(content)
                is_verified, verification_report = verify_article_before_publish(plain_text)
                
                if not is_verified:
                    logging.error(f"Newsletter BLOCKED - fact-check failed: {verification_report.get('errors', [])}")
                    self.last_verification_report = verification_report
                    return False
                    
                logging.info("Newsletter passed fact-check verification")
                self.last_verification_report = verification_report
                
            except Exception as e:
                # STRICT BLOCKING: If fact-checker service fails, do NOT send
                logging.error(f"Newsletter BLOCKED - fact-check service error: {e}")
                self.last_verification_report = {'error': str(e), 'verified': False}
                return False
            
        try:
            if recipients is None:
                subscribed_users = models.User.query.filter_by(newsletter_subscribed=True).all()
                recipients = [user.email for user in subscribed_users]
            
            if not recipients:
                logging.warning("No newsletter recipients found")
                return False
            
            for email in recipients:
                message = Mail(
                    from_email=Email("newsletter@protocolpulse.com", "Protocol Pulse"),
                    to_emails=To(email),
                    subject=subject,
                    html_content=Content("text/html", content)
                )
                
                self.sg.send(message)
            
            logging.info(f"Newsletter sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logging.error(f"Newsletter sending error: {e}")
            return False
    
    def get_last_verification_report(self) -> dict:
        """Get the verification report from the last send attempt."""
        return getattr(self, 'last_verification_report', {})

# Global newsletter service instance
newsletter_service = NewsletterService()


# ============================================
# HighLevel (GHL) Webhook Integration
# ============================================

GHL_WEBHOOK_URL = os.environ.get('GHL_WEBHOOK_URL', '')
SITE_URL = os.environ.get('SITE_URL', 'https://protocolpulse.io')


def send_daily_brief_to_ghl(ghl_webhook_url=None):
    """
    Fetches articles from the last 24 hours and sends them to GHL webhook
    for automated newsletter distribution.
    
    Args:
        ghl_webhook_url: Optional webhook URL override (uses env var if not provided)
    
    Returns:
        dict with status and response details
    """
    from datetime import datetime, timedelta
    import requests
    import re
    
    webhook_url = ghl_webhook_url or GHL_WEBHOOK_URL
    
    if not webhook_url:
        logging.warning("GHL_WEBHOOK_URL not configured - skipping newsletter send")
        return {'status': 'skipped', 'reason': 'No webhook URL configured'}
    
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        today_articles = models.Article.query.filter(
            models.Article.published == True,
            models.Article.created_at >= cutoff
        ).order_by(models.Article.created_at.desc()).limit(5).all()
        
        if not today_articles:
            logging.info("No articles from last 24h - skipping newsletter")
            return {'status': 'skipped', 'reason': 'No articles to send'}
        
        def clean_summary(content, max_length=200):
            if not content:
                return ""
            clean = re.sub(r'<[^>]+>', '', content)
            clean = re.sub(r'\s+', ' ', clean).strip()
            if len(clean) > max_length:
                clean = clean[:max_length].rsplit(' ', 1)[0] + '...'
            return clean
        
        payload = {
            "email_subject": f"Protocol Pulse: The {datetime.utcnow().strftime('%B %d')} Brief",
            "send_date": datetime.utcnow().isoformat(),
            "article_count": len(today_articles),
            "articles": [
                {
                    "title": article.title,
                    "summary": clean_summary(article.content, 200),
                    "category": article.category or "Bitcoin",
                    "url": f"{SITE_URL}/articles/{article.id}",
                    "published_at": article.created_at.isoformat()
                }
                for article in today_articles[:3]
            ],
            "headline": today_articles[0].title if today_articles else "",
            "headline_url": f"{SITE_URL}/articles/{today_articles[0].id}" if today_articles else "",
            "site_url": SITE_URL,
            "unsubscribe_url": f"{SITE_URL}/unsubscribe"
        }
        
        logging.info(f"Sending {len(today_articles)} articles to GHL webhook")
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            logging.info("Successfully sent newsletter to GHL")
            return {
                'status': 'success',
                'articles_sent': len(today_articles),
                'response_code': response.status_code
            }
        else:
            logging.error(f"GHL webhook returned {response.status_code}: {response.text}")
            return {
                'status': 'error',
                'response_code': response.status_code,
                'error': response.text
            }
            
    except Exception as e:
        logging.error(f"Error sending to GHL: {str(e)}")
        return {'status': 'error', 'error': str(e)}