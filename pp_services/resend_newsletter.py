"""
Resend Newsletter Service - Protocol Pulse
==========================================
Modern email service with simple API.

Setup:
1. Create account at resend.com
2. Get API key from dashboard
3. Add RESEND_API_KEY to Replit Secrets
4. Verify your domain (or use onboarding@resend.dev for testing)
"""

import os
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ResendNewsletterService:
    def __init__(self):
        self.api_key = os.environ.get('RESEND_API_KEY')
        self.from_email = os.environ.get('NEWSLETTER_FROM_EMAIL', 'Protocol Pulse <newsletter@protocolpulse.com>')
        self.base_url = "https://api.resend.com"
        
        if not self.api_key:
            logger.warning("RESEND_API_KEY not configured - newsletter disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Resend newsletter service initialized")
    
    @staticmethod
    def _ai_summary_block(digest_summary):
        """Build AI summary HTML block (separate method to avoid nested f-string)."""
        if not digest_summary:
            return ''
        return (
            '<!-- AI Summary -->'
            '<tr>'
            '<td style="padding: 30px; background: linear-gradient(135deg, #1a0505 0%, #111 100%); border-bottom: 1px solid #333;">'
            '<h2 style="color: #fff; font-size: 16px; margin: 0 0 15px; text-transform: uppercase; letter-spacing: 1px;">'
            '&#129302; AI Intelligence Summary'
            '</h2>'
            '<p style="color: #ccc; font-size: 15px; line-height: 1.7; margin: 0;">'
            f'{digest_summary}'
            '</p>'
            '</td>'
            '</tr>'
        )

    def send_email(self, to: str, subject: str, html: str, text: str = None) -> Dict:
        """Send a single email"""
        if not self.enabled:
            return {"success": False, "error": "Resend not configured"}
        
        try:
            response = requests.post(
                f"{self.base_url}/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": self.from_email,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text or subject
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Email sent: {data.get('id')}")
                return {"success": True, "id": data.get("id")}
            else:
                logger.error(f"Resend error: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return {"success": False, "error": str(e)}
    
    def send_batch(self, emails: List[Dict]) -> Dict:
        """
        Send batch emails (up to 100 at once)
        emails: [{"to": "email@example.com", "subject": "...", "html": "..."}]
        """
        if not self.enabled:
            return {"success": False, "error": "Resend not configured"}
        
        try:
            # Resend batch endpoint
            batch_data = []
            for email in emails[:100]:  # Max 100 per batch
                batch_data.append({
                    "from": self.from_email,
                    "to": [email["to"]],
                    "subject": email["subject"],
                    "html": email["html"]
                })
            
            response = requests.post(
                f"{self.base_url}/emails/batch",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=batch_data,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Batch sent: {len(data.get('data', []))} emails")
                return {"success": True, "sent": len(batch_data), "data": data}
            else:
                logger.error(f"Batch error: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Batch send failed: {e}")
            return {"success": False, "error": str(e)}
    
    def send_newsletter(self, subject: str, html_content: str, subscriber_list: List[str] = None) -> Dict:
        """
        Send newsletter to all subscribers or a specific list
        """
        if not self.enabled:
            return {"success": False, "error": "Resend not configured"}
        
        # Get subscribers from database if not provided
        if not subscriber_list:
            try:
                from app import app
                from models import User
                
                with app.app_context():
                    subscribers = User.query.filter_by(newsletter_subscribed=True).all()
                    subscriber_list = [u.email for u in subscribers if u.email]
                    logger.info(f"Found {len(subscriber_list)} subscribers")
            except Exception as e:
                logger.error(f"Error fetching subscribers: {e}")
                return {"success": False, "error": str(e)}
        
        if not subscriber_list:
            return {"success": False, "error": "No subscribers found"}
        
        # Send in batches of 100
        total_sent = 0
        errors = []
        
        for i in range(0, len(subscriber_list), 100):
            batch = subscriber_list[i:i+100]
            emails = [{"to": email, "subject": subject, "html": html_content} for email in batch]
            
            result = self.send_batch(emails)
            if result.get("success"):
                total_sent += result.get("sent", 0)
            else:
                errors.append(result.get("error"))
        
        return {
            "success": total_sent > 0,
            "total_sent": total_sent,
            "total_subscribers": len(subscriber_list),
            "errors": errors if errors else None
        }
    
    def generate_newsletter_html(self, articles: List[Dict], digest_summary: str = None) -> str:
        """Generate beautiful HTML newsletter from articles"""
        
        today = datetime.utcnow().strftime("%B %d, %Y")
        
        # Build articles HTML
        articles_html = ""
        for i, article in enumerate(articles[:10]):  # Max 10 articles
            articles_html += f'''
            <tr>
                <td style="padding: 20px 0; border-bottom: 1px solid #333;">
                    <a href="{article.get('url', '#')}" style="color: #dc2626; font-size: 18px; font-weight: 600; text-decoration: none;">
                        {article.get('title', 'Untitled')}
                    </a>
                    <p style="color: #999; font-size: 14px; margin: 10px 0 0; line-height: 1.5;">
                        {article.get('summary', '')[:200]}...
                    </p>
                </td>
            </tr>
            '''
        
        html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #0a0a0a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #111; border: 1px solid #dc2626; border-radius: 12px;">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 30px; text-align: center; border-bottom: 1px solid #333;">
                            <h1 style="margin: 0; color: #dc2626; font-size: 28px; letter-spacing: 2px;">
                                PROTOCOL PULSE
                            </h1>
                            <p style="margin: 10px 0 0; color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">
                                Bitcoin Intelligence Brief • {today}
                            </p>
                        </td>
                    </tr>
                    
                    {self._ai_summary_block(digest_summary)}
                    
                    <!-- Articles -->
                    <tr>
                        <td style="padding: 30px;">
                            <h2 style="color: #fff; font-size: 16px; margin: 0 0 20px; text-transform: uppercase; letter-spacing: 1px;">
                                📰 Today's Intel
                            </h2>
                            <table width="100%" cellpadding="0" cellspacing="0">
                                {articles_html}
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 30px; text-align: center; border-top: 1px solid #333; background: #0a0a0a;">
                            <p style="color: #666; font-size: 12px; margin: 0;">
                                You're receiving this because you subscribed to Protocol Pulse.<br>
                                <a href="{{{{unsubscribe_url}}}}" style="color: #dc2626;">Unsubscribe</a>
                            </p>
                            <p style="color: #444; font-size: 11px; margin: 15px 0 0;">
                                © 2026 Protocol Pulse • Bitcoin Intelligence
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
'''
        return html


# Singleton
resend_newsletter = ResendNewsletterService()


def send_daily_newsletter():
    """Automated daily newsletter sender"""
    from app import app
    from models import Article
    from pp_services.newsletter_digest import newsletter_digest_service
    
    with app.app_context():
        # Get today's published articles
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        articles = Article.query.filter(
            Article.published == True,
            Article.created_at >= cutoff
        ).order_by(Article.created_at.desc()).limit(10).all()
        
        if not articles:
            logger.info("No articles to send in newsletter")
            return {"success": False, "error": "No articles"}
        
        # Format articles for newsletter
        article_list = []
        for a in articles:
            article_list.append({
                "title": a.title,
                "summary": a.summary or "",
                "url": f"https://protocolpulse.io/article/{a.id}"
            })
        
        # Generate AI digest summary
        try:
            digest = newsletter_digest_service.generate_digest(
                [{"title": a.title, "content": a.content[:500]} for a in articles]
            )
            summary = digest.get("summary", "")
        except:
            summary = None
        
        # Generate HTML
        html = resend_newsletter.generate_newsletter_html(article_list, summary)
        
        # Send
        subject = f"⚡ Protocol Pulse Daily Brief - {datetime.utcnow().strftime('%B %d')}"
        result = resend_newsletter.send_newsletter(subject, html)
        
        logger.info(f"Newsletter sent: {result}")
        return result


if __name__ == "__main__":
    # Test
    print("Testing Resend Newsletter Service...")
    
    if resend_newsletter.enabled:
        test_html = resend_newsletter.generate_newsletter_html([
            {"title": "Test Article 1", "summary": "This is a test summary", "url": "#"},
            {"title": "Test Article 2", "summary": "Another test summary", "url": "#"}
        ], "This is an AI-generated summary of today's Bitcoin news.")
        
        print("HTML generated successfully!")
        print(f"Length: {len(test_html)} chars")
    else:
        print("Resend not configured - add RESEND_API_KEY to secrets")
