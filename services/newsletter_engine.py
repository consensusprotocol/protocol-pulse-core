"""
PROTOCOL PULSE NEWSLETTER ENGINE
=================================
World-class automated newsletter with:
- Beautiful dark/red design
- AI-powered content curation
- Multi-LLM quality control
- Automated daily delivery
- Self-custody focused messaging

Exceeds expectations. Every time.
"""

import os
import logging
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class NewsletterEngine:
    def __init__(self):
        self.resend_key = os.environ.get("RESEND_API_KEY")
        self.from_email = os.environ.get("NEWSLETTER_FROM_EMAIL", "Protocol Pulse <newsletter@protocolpulse.io>")
        self.site_url = os.environ.get("SITE_URL", "https://protocolpulse.io")
        
        if self.resend_key:
            logger.info("Newsletter Engine initialized with Resend")
        else:
            logger.warning("RESEND_API_KEY not set - newsletter disabled")
    
    def get_todays_articles(self, limit: int = 5) -> List[Dict]:
        """Get today's best articles with aggressive topic diversity."""
        try:
            from app import app
            from models import Article
            
            with app.app_context():
                cutoff = datetime.utcnow() - timedelta(hours=24)
                all_recent = Article.query.filter(
                    Article.published == True,
                    Article.created_at >= cutoff
                ).order_by(Article.created_at.desc()).all()
                
                if not all_recent:
                    return []
                
                # Separate by type
                opinion = [a for a in all_recent if a.category in ("opinion", "sentiment")]
                news = [a for a in all_recent if a.category not in ("opinion", "sentiment")]
                
                selected = []
                used_themes = set()
                
                # Theme detection — group by dominant topic keyword
                def get_theme(title):
                    t = title.lower()
                    themes = {
                        "mining": ["mining", "miner", "hashrate", "hash rate", "difficulty"],
                        "price": ["price", "rally", "crash", "correction", "plunge", "below", "above"],
                        "whale": ["whale", "wallet", "moved", "transfer", "genesis", "satoshi"],
                        "etf": ["etf", "blackrock", "fidelity", "grayscale", "spot"],
                        "regulation": ["regulation", "sec", "congress", "law", "ban", "bill"],
                        "macro": ["fed", "inflation", "rate", "treasury", "dollar", "tariff"],
                        "adoption": ["adopt", "country", "nation", "legal tender", "reserve"],
                        "lightning": ["lightning", "layer 2", "l2", "payment"],
                        "security": ["hack", "exploit", "vulnerability", "attack"],
                    }
                    for theme, keywords in themes.items():
                        if any(kw in t for kw in keywords):
                            return theme
                    return "general"
                
                # 1. Lead with opinion/intel briefing
                for a in opinion[:1]:
                    theme = get_theme(a.title)
                    selected.append(a)
                    used_themes.add(theme)
                
                # 2. Fill with DIVERSE news — max 1 article per theme
                for a in news:
                    if len(selected) >= limit:
                        break
                    theme = get_theme(a.title)
                    if theme not in used_themes:
                        selected.append(a)
                        used_themes.add(theme)
                
                # 3. If still short, allow second article from popular themes
                if len(selected) < limit:
                    for a in news:
                        if len(selected) >= limit:
                            break
                        if a not in selected:
                            selected.append(a)
                
                return [{
                    "id": a.id,
                    "title": a.title,
                    "summary": a.summary or "",
                    "url": f"{self.site_url}/articles/{a.id}",
                    "image": a.header_image_url or "",
                    "category": a.category or "Bitcoin"
                } for a in selected]
                
        except Exception as e:
            logger.error(f"Error getting articles: {e}")
            return []

    def generate_ai_summary(self, articles: List[Dict]) -> str:
        """Generate a razor-sharp morning briefing. No AI slop."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            titles_block = "\n".join(f"- [{a.get('category','news')}] {a['title']}" for a in articles[:7])
            summaries_block = "\n".join(f"  {a.get('summary', '')[:150]}" for a in articles[:3])
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """You write the morning note for a Bitcoin intelligence publication. 3 sentences max. Under 50 words total.

WRITE LIKE: A Bloomberg terminal alert that a human edited for wit.
NOT LIKE: A ChatGPT summary of news articles.

SENTENCE 1: What happened. Lead with the most specific, surprising fact. A number, a name, a move. Not a vague "markets are volatile."
SENTENCE 2: Why it matters or what it means. One sharp implication.
SENTENCE 3 (optional): What to watch. Only if there's something specific.

INSTANT REJECTION — if your draft contains ANY of these, rewrite:
- "plummeted" / "soared" / "surged" / "tumbled" 
- "stark reality" / "reality check" / "wake-up call"
- "landscape" / "amidst" / "amid" / "in the wake of"
- "presenting" / "highlighting" / "underscoring" / "signaling"
- "market conditions evolve" / "remains to be seen" / "time will tell"
- "broader volatility" / "significant fluctuation" / "notable shift"
- Any sentence that could apply to any week (if you could swap the date and it still works, it's too vague)
- Any sentence telling the reader what to think or feel

GOOD EXAMPLE:
"A Satoshi-era wallet moved 11,300 BTC overnight — $750M hitting exchanges for the first time since 2012. Bitcoin dropped below $65K on the liquidation cascade. Difficulty adjusts Thursday."

BAD EXAMPLE:
"Bitcoin has plummeted below $65,000 as market chaos strikes, reflecting broader volatility and presenting a stark reality check for the network."

The good example has: specific number, specific dollar amount, specific date context, specific upcoming event.
The bad example has: generic verbs, vague references, no specifics, AI filler."""},
                    {"role": "user", "content": f"Today's articles and summaries:\n{titles_block}\n\nKey details:\n{summaries_block}\n\nWrite the morning note. 3 sentences max. Be specific."}
                ],
                max_tokens=120,
                temperature=0.7
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Rejection check — if AI slop leaked through, use a hard fallback
            slop_words = ["plummeted", "soared", "tumbled", "landscape", "amidst", 
                         "stark reality", "reality check", "broader volatility",
                         "significant fluctuation", "remains to be seen", "time will tell",
                         "presenting a", "highlighting the", "underscoring"]
            
            for slop in slop_words:
                if slop.lower() in summary.lower():
                    logger.warning(f"Summary contained slop word '{slop}', requesting rewrite")
                    # One retry with even stricter instruction
                    retry = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "Rewrite this in 2 sentences. Use only specific facts. No adjectives. No commentary. Bloomberg wire style."},
                            {"role": "user", "content": f"Rewrite without AI language:\n{summary}"}
                        ],
                        max_tokens=80,
                        temperature=0.5
                    )
                    summary = retry.choices[0].message.content.strip()
                    break
            
            return summary
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return ""

    def get_btc_price(self) -> Dict:
        """Get BTC price with fallback sources."""
        import requests
        
        # Try CoinGecko first
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true", timeout=10)
            if r.status_code == 200:
                data = r.json().get("bitcoin", {})
                return {"price": data.get("usd", 0), "change": data.get("usd_24h_change", 0)}
        except:
            pass
        
        # Fallback: CoinCap
        try:
            r = requests.get("https://api.coincap.io/v2/assets/bitcoin", timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", {})
                return {"price": float(data.get("priceUsd", 0)), "change": float(data.get("changePercent24Hr", 0))}
        except:
            pass
        
        # Fallback: use last known from our price service
        try:
            from services.price_service import get_latest_prices
            prices = get_latest_prices()
            if prices and prices.get("btc"):
                return {"price": prices["btc"], "change": 0}
        except:
            pass
        
        return {"price": 0, "change": 0}

    def generate_html(self, articles: List[Dict], summary: str, btc_data: Dict) -> str:
        """Generate beautiful HTML newsletter"""
        
        date_str = datetime.utcnow().strftime("%B %d, %Y")
        
        # Price formatting
        price = f"${btc_data['price']:,.0f}" if btc_data['price'] else "—"
        change = btc_data['change']
        change_color = "#22c55e" if change >= 0 else "#ef4444"
        change_str = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
        
        # Build article cards
        articles_html = ""
        for i, article in enumerate(articles[:5]):
            is_opinion = article.get('category', '').lower() in ('opinion', 'sentiment')
            border_style = "border-left: 3px solid #dc2626; padding-left: 16px;" if is_opinion else ""
            category_label = "EDITORIAL" if is_opinion else article.get('category', 'Bitcoin').upper()
            category_color = "#f59e0b" if is_opinion else "#dc2626"
            
            articles_html += f"""
            <tr>
                <td style="padding: 24px 0; border-bottom: 1px solid #2a2a2a;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td style="vertical-align: top; {border_style}">
                                <a href="{article['url']}" style="color: #ffffff; text-decoration: none;">
                                    <span style="color: {category_color}; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;">{category_label}</span>
                                    <h3 style="margin: 8px 0 12px; font-size: 18px; font-weight: 600; line-height: 1.4; color: #ffffff;">
                                        {article['title']}
                                    </h3>
                                </a>
                                <p style="margin: 0; color: #9ca3af; font-size: 14px; line-height: 1.6;">
                                    {article['summary'][:180]}{'...' if len(article['summary']) > 180 else ''}
                                </p>
                                <a href="{article['url']}" style="display: inline-block; margin-top: 12px; color: #dc2626; font-size: 13px; text-decoration: none; font-weight: 500;">
                                    Read full analysis &rarr;
                                </a>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            """

        
        html = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Protocol Pulse Daily Brief</title>
</head>
<body style="margin: 0; padding: 0; background-color: #000000; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    
    <!-- Wrapper -->
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #000000;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                
                <!-- Main Container -->
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #0a0a0a; border-radius: 16px; overflow: hidden; border: 1px solid #1a1a1a;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="padding: 40px 40px 30px; background: linear-gradient(180deg, #1a0a0a 0%, #0a0a0a 100%); border-bottom: 1px solid #2a2a2a;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td>
                                        <h1 style="margin: 0; font-size: 28px; font-weight: 700; letter-spacing: 3px; color: #dc2626;">
                                            PROTOCOL PULSE
                                        </h1>
                                        <p style="margin: 8px 0 0; font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px;">
                                            Daily Intelligence Brief • {date_str}
                                        </p>
                                    </td>
                                    <td align="right" style="vertical-align: top;">
                                        <table cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="background: #111111; border-radius: 8px; padding: 12px 16px; border: 1px solid #2a2a2a;">
                                                    <span style="font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px;">BTC</span><br>
                                                    <span style="font-size: 18px; font-weight: 600; color: #ffffff;">{price}</span>
                                                    <span style="font-size: 12px; color: {change_color}; margin-left: 6px;">{change_str}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Executive Summary -->
                    <tr>
                        <td style="padding: 30px 40px; background: linear-gradient(135deg, #0f0505 0%, #0a0a0a 100%); border-bottom: 1px solid #2a2a2a;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="padding-left: 16px; border-left: 3px solid #dc2626;">
                                        <span style="font-size: 11px; color: #dc2626; text-transform: uppercase; letter-spacing: 2px; font-weight: 600;">Executive Summary</span>
                                        <p style="margin: 12px 0 0; font-size: 16px; line-height: 1.7; color: #e5e7eb;">
                                            {summary}
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Articles -->
                    <tr>
                        <td style="padding: 30px 40px;">
                            <h2 style="margin: 0 0 20px; font-size: 14px; color: #dc2626; text-transform: uppercase; letter-spacing: 2px; font-weight: 600;">
                                Today's Intelligence
                            </h2>
                            <table width="100%" cellpadding="0" cellspacing="0">
                                {articles_html}
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Tagline -->
                    <tr>
                        <td style="padding: 30px 40px; background: #0f0f0f; border-top: 1px solid #2a2a2a;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center">
                                        <p style="margin: 0; font-size: 13px; color: #6b7280; letter-spacing: 0.5px;">
                                            The signal. Every morning. No noise.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 30px 40px; background: #050505; border-top: 1px solid #1a1a1a;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center">
                                        <p style="margin: 0 0 16px; font-size: 12px; color: #4b5563;">
                                            <a href="{self.site_url}" style="color: #dc2626; text-decoration: none;">Website</a>
                                            &nbsp;&nbsp;•&nbsp;&nbsp;
                                            <a href="https://twitter.com/protocolpulse" style="color: #dc2626; text-decoration: none;">Twitter</a>
                                            &nbsp;&nbsp;•&nbsp;&nbsp;
                                            <a href="{self.site_url}/articles" style="color: #dc2626; text-decoration: none;">Archives</a>
                                        </p>
                                        <p style="margin: 0; font-size: 11px; color: #374151;">
                                            You received this because you subscribed to Protocol Pulse.<br>
                                            <a href="{self.site_url}/unsubscribe" style="color: #6b7280;">Unsubscribe</a>
                                        </p>
                                        <p style="margin: 16px 0 0; font-size: 10px; color: #1f2937;">
                                            © 2026 Protocol Pulse • Bitcoin Intelligence
                                        </p>
                                    </td>
                                </tr>
                            </table>
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

    def send_newsletter(self, to_emails: List[str], subject: str = None, html: str = None) -> Dict:
        """Send newsletter via Resend"""
        if not self.resend_key:
            return {"success": False, "error": "Resend not configured"}
        
        if not to_emails:
            return {"success": False, "error": "No recipients"}
        
        # Generate content if not provided
        if not html:
            articles = self.get_todays_articles()
            if not articles:
                return {"success": False, "error": "No articles to send"}
            
            summary = self.generate_ai_summary(articles)
            btc_data = self.get_btc_price()
            html = self.generate_html(articles, summary, btc_data)
        
        if not subject:
            subject = f"Protocol Pulse • {datetime.utcnow().strftime('%B %d')} Intelligence Brief"
        
        # Send via Resend
        try:
            sent = 0
            errors = []
            
            # Send in batches of 50
            for i in range(0, len(to_emails), 50):
                batch = to_emails[i:i+50]
                
                response = requests.post(
                    "https://api.resend.com/emails/batch",
                    headers={
                        "Authorization": f"Bearer {self.resend_key}",
                        "Content-Type": "application/json"
                    },
                    json=[{
                        "from": self.from_email,
                        "to": email,
                        "subject": subject,
                        "html": html
                    } for email in batch],
                    timeout=30
                )
                
                if response.status_code == 200:
                    sent += len(batch)
                else:
                    errors.append(f"Batch {i}: {response.text}")
            
            return {
                "success": sent > 0,
                "sent": sent,
                "total": len(to_emails),
                "errors": errors if errors else None
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_subscribers(self) -> List[str]:
        """Get subscriber emails from database"""
        try:
            from app import app
            from models import User
            
            with app.app_context():
                # Get users with newsletter_subscribed = True
                users = User.query.filter_by(newsletter_subscribed=True).all()
                return [u.email for u in users if u.email]
        except:
            return []
    
    def run_daily_newsletter(self) -> Dict:
        """Main entry point for daily newsletter"""
        logger.info("Running daily newsletter...")
        
        # Check if already sent today
        sent_file = "data/newsletter_sent.json"
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        try:
            import os
            os.makedirs("data", exist_ok=True)
            
            if os.path.exists(sent_file):
                with open(sent_file, 'r') as f:
                    data = json.load(f)
                if data.get("last_sent") == today:
                    logger.info("Newsletter already sent today")
                    return {"success": False, "error": "Already sent today"}
        except:
            pass
        
        # Get subscribers
        subscribers = self.get_subscribers()
        
        if not subscribers:
            logger.warning("No subscribers found")
            return {"success": False, "error": "No subscribers"}
        
        # Send
        result = self.send_newsletter(subscribers)
        
        # Mark as sent
        if result.get("success"):
            with open(sent_file, 'w') as f:
                json.dump({"last_sent": today, "sent": result.get("sent", 0)}, f)
        
        logger.info(f"Newsletter result: {result}")
        return result
    
    def send_test(self, email: str) -> Dict:
        """Send test newsletter to single email"""
        articles = self.get_todays_articles()
        
        if not articles:
            # Use dummy data for test
            articles = [{
                "id": 1,
                "title": "Bitcoin Self-Custody Reaches Record Adoption",
                "summary": "More individuals than ever are taking control of their own Bitcoin. Hardware wallet sales surge as sovereignty becomes the priority for serious Bitcoiners.",
                "url": f"{self.site_url}/articles/1",
                "category": "Sovereignty"
            }, {
                "id": 2,
                "title": "Lightning Network Capacity Hits All-Time High",
                "summary": "The peer-to-peer payment layer continues to grow as more nodes come online and channel capacity expands globally.",
                "url": f"{self.site_url}/articles/2",
                "category": "Technology"
            }]
        
        summary = self.generate_ai_summary(articles)
        btc_data = self.get_btc_price()
        html = self.generate_html(articles, summary, btc_data)
        
        return self.send_newsletter([email], html=html)


# Singleton
newsletter_engine = NewsletterEngine()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "test" and len(sys.argv) > 2:
            email = sys.argv[2]
            result = newsletter_engine.send_test(email)
            print(json.dumps(result, indent=2))
        
        elif cmd == "run":
            result = newsletter_engine.run_daily_newsletter()
            print(json.dumps(result, indent=2))
        
        elif cmd == "preview":
            articles = newsletter_engine.get_todays_articles()
            summary = newsletter_engine.generate_ai_summary(articles)
            btc = newsletter_engine.get_btc_price()
            html = newsletter_engine.generate_html(articles, summary, btc)
            
            # Save preview
            with open("newsletter_preview.html", "w") as f:
                f.write(html)
            print("✅ Preview saved to newsletter_preview.html")
        
        else:
            print("Usage: python newsletter_engine.py [test <email> | run | preview]")
    else:
        print("Usage: python newsletter_engine.py [test <email> | run | preview]")
