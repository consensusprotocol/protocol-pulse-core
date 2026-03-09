# PROTOCOL PULSE - COMPLETE CODEBASE FOR VERIFICATION

## ⚠️ CURRENT STATUS (October 10, 2025)

**AUTOMATION STATUS: NOT WORKING**
- Last articles generated: October 7, 2025 (3 days ago)
- Automation process: NOT RUNNING
- Web server: RUNNING
- Database: OPERATIONAL
- All AI APIs: CONNECTED

**THE PROBLEM:** The automation loop keeps crashing and doesn't stay running to generate articles automatically.

---

## 📁 FILE: `app.py` - Flask Application Factory

```python
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "protocol-pulse-secret-key-2025")

# Get port from environment for deployment
port = int(os.environ.get("PORT", 5000))

# Configure the database
database_url = os.environ.get("DATABASE_URL", "sqlite:///protocol_pulse.db")
if database_url.startswith("sqlite:"):
    database_url += "?charset=utf8mb4"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Import routes after app creation
import routes
```

---

## 📁 FILE: `main.py` - Application Entry Point

```python
from app import app  # noqa: F401
```

---

## 📁 FILE: `models.py` - Database Models

```python
from app import db
from datetime import datetime
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    newsletter_subscribed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    author = db.Column(db.String(100), default="Protocol Pulse AI")
    category = db.Column(db.String(50), default="Web3")
    tags = db.Column(db.String(500))  # Comma-separated tags
    source_url = db.Column(db.String(500))
    source_type = db.Column(db.String(50))  # reddit, ai_generated, manual
    featured = db.Column(db.Boolean, default=False)
    published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    seo_title = db.Column(db.String(200))
    seo_description = db.Column(db.String(300))
    substack_url = db.Column(db.String(500))  # URL of published Substack post
    header_image_url = db.Column(db.String(500))  # Header image for the article
    screenshot_url = db.Column(db.String(500))  # Screenshot for social media posts
    video_url = db.Column(db.String(500))  # YouTube embed URL for video content

class Podcast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    host = db.Column(db.String(100))
    episode_number = db.Column(db.Integer)
    duration = db.Column(db.String(20))  # Format: "1h 23m"
    audio_url = db.Column(db.String(500))
    cover_image_url = db.Column(db.String(500))
    published_date = db.Column(db.DateTime, default=datetime.utcnow)
    featured = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50), default="Web3")
    rss_source = db.Column(db.String(100))  # Source RSS feed name

class ContentPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Advertisement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    image_url = db.Column(db.String(300), nullable=False)
    target_url = db.Column(db.String(300), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

---

## 📁 FILE: `generate_article_now.py` - Single Article Generator (WORKING)

```python
#!/usr/bin/env python3
"""
Simple script to generate a single article immediately
Can be run from cron or manually
"""
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Article
from services.content_generator import ContentGenerator
import random
import logging

logging.basicConfig(level=logging.INFO)

# Breaking news topics
TOPICS = [
    "Bitcoin mining difficulty reaches new all-time high as hash rate surges",
    "Major institutional investors allocate billions to Bitcoin treasury reserves", 
    "Lightning Network payment volume breaks monthly records",
    "DeFi protocols implement revolutionary new yield farming mechanisms",
    "Central banks accelerate CBDC development in response to Bitcoin adoption",
    "Major corporations announce Bitcoin payment integration plans",
    "Renewable energy Bitcoin mining initiatives expand globally",
    "DeFi total value locked reaches new milestone despite market volatility",
    "Bitcoin ETF inflows surge as retail and institutional demand grows",
    "Layer 2 scaling solutions see unprecedented adoption rates"
]

def generate_article():
    """Generate a single breaking news article"""
    with app.app_context():
        try:
            generator = ContentGenerator()
            topic = random.choice(TOPICS)
            
            logging.info(f"🔥 Generating article: {topic}")
            
            article_data = generator.generate_article(
                topic=topic,
                content_type='breaking_news',
                source_type='ai_generated'
            )
            
            if article_data:
                article = Article()
                article.title = article_data['title']
                article.content = article_data['content']
                article.summary = ""
                article.category = article_data.get('category', 'Bitcoin')
                article.tags = article_data.get('tags', 'bitcoin,breaking,news')
                article.author = "Al Ingle"
                article.seo_title = article_data.get('seo_title', article_data['title'])
                article.seo_description = article_data.get('seo_description', article_data['title'][:150])
                article.published = True
                article.featured = True
                db.session.add(article)
                db.session.commit()
                
                logging.info(f"✅ Article created: {article.title}")
                
                # Auto-publish to Substack
                try:
                    from services.substack_service import SubstackService
                    substack_service = SubstackService()
                    newsletter_content = substack_service.format_content_for_newsletter(article.content, 'bitcoin')
                    substack_url = substack_service.publish_to_substack(article.title, newsletter_content, article.header_image_url)
                    
                    if substack_url:
                        article.substack_url = substack_url
                        db.session.commit()
                        logging.info(f"🚀 Published to Substack: {substack_url}")
                except Exception as e:
                    logging.error(f"❌ Substack error: {e}")
                
                return True
            else:
                logging.error("❌ No article data generated")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = generate_article()
    sys.exit(0 if success else 1)
```

---

## 📁 FILE: `auto_generate_loop.py` - Continuous Article Generation (CRASHES)

```python
#!/usr/bin/env python3
"""
Continuous article generation loop - runs every 15 minutes
THIS VERSION KEEPS CRASHING
"""
import time
import subprocess
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def run_generation():
    """Run the article generation script"""
    try:
        result = subprocess.run(
            ['python3', 'generate_article_now.py'],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            logging.info("✅ Article generated successfully")
        else:
            logging.error(f"❌ Generation failed: {result.stderr[:200]}")
    except Exception as e:
        logging.error(f"❌ Error running generation: {e}")

if __name__ == '__main__':
    logging.info("🚀 Starting automated article generation (every 15 minutes)")
    
    # Generate first article immediately
    logging.info("📰 Generating initial article...")
    run_generation()
    
    # Loop forever, generating every 15 minutes
    while True:
        try:
            logging.info(f"⏰ Waiting 15 minutes until {datetime.now().strftime('%H:%M:%S')}")
            time.sleep(900)  # 15 minutes = 900 seconds
            
            logging.info("📰 Generating new article...")
            run_generation()
            
        except KeyboardInterrupt:
            logging.info("⏹️  Automation stopped")
            break
        except Exception as e:
            logging.error(f"❌ Loop error: {e}")
            time.sleep(60)  # Wait 1 minute before retry
```

---

## 📁 FILE: `services/scheduler.py` - Automation Functions

```python
import schedule
import time
import random
from datetime import datetime, timedelta
from app import app, db
from models import Article
from services.content_generator import ContentGenerator
import logging

generator = ContentGenerator()

# Diverse breaking news topics for automated generation
BREAKING_TOPICS = [
    "Bitcoin mining difficulty reaches new all-time high as hash rate surges",
    "Major institutional investors allocate billions to Bitcoin treasury reserves", 
    "Lightning Network payment volume breaks monthly records",
    "DeFi protocols implement revolutionary new yield farming mechanisms",
    "Central banks accelerate CBDC development in response to Bitcoin adoption",
    "Major corporations announce Bitcoin payment integration plans",
    "Renewable energy Bitcoin mining initiatives expand globally",
    "DeFi total value locked reaches new milestone despite market volatility",
    "Bitcoin ETF inflows surge as retail and institutional demand grows",
    "Layer 2 scaling solutions see unprecedented adoption rates",
    "Bitcoin reaches new adoption milestone in emerging markets",
    "DeFi lending protocols revolutionize traditional banking models"
]

def generate_scheduled_article():
    """Generate fresh breaking news articles automatically"""
    with app.app_context():
        try:
            # Select random topic for variety
            topic = random.choice(BREAKING_TOPICS)
            
            # Generate the article with breaking news focus
            article_data = generator.generate_article(
                topic=topic,
                content_type='breaking_news',
                source_type='ai_generated'
            )
            
            if article_data:
                article = Article()
                article.title = article_data['title']
                article.content = article_data['content']
                article.summary = ""  # TL;DR embedded in content
                article.category = article_data.get('category', 'Bitcoin')
                article.tags = article_data.get('tags', 'bitcoin,breaking,news')
                article.author = "Al Ingle"
                article.seo_title = article_data.get('seo_title', article_data['title'])
                article.seo_description = article_data.get('seo_description', article_data['title'][:150])
                article.header_image_url = article_data.get('header_image_url')
                article.published = True  # Auto-publish breaking news
                article.featured = True   # Mark as featured for homepage visibility
                db.session.add(article)
                db.session.commit()
                
                logging.info(f"✅ Auto-generated breaking news: {article.title}")
                
                # Immediately publish to Substack (hands-off workflow)
                try:
                    from services.substack_service import SubstackService
                    substack_service = SubstackService()
                    
                    # Format content for newsletter
                    newsletter_content = substack_service.format_content_for_newsletter(
                        article.content, 'bitcoin'
                    )
                    
                    # Publish to Substack
                    substack_url = substack_service.publish_to_substack(
                        article.title,
                        newsletter_content,
                        article.header_image_url
                    )
                    
                    if substack_url:
                        # Update article with Substack URL
                        article.substack_url = substack_url
                        db.session.commit()
                        logging.info(f"🚀 Auto-published to Substack: {substack_url}")
                    else:
                        logging.warning(f"⚠️ Failed to auto-publish '{article.title}' to Substack")
                        
                except Exception as e:
                    logging.error(f"❌ Auto-publish to Substack failed: {e}")
                
                # Archive older articles to keep homepage fresh
                archive_old_articles()
                
            else:
                logging.error("❌ Failed to generate scheduled article content")
                
        except Exception as e:
            logging.error(f"❌ Error in scheduled article generation: {str(e)}")

def archive_old_articles():
    """Archive articles older than 7 days to keep homepage fresh"""
    with app.app_context():
        try:
            # Find articles older than 7 days that are still featured
            archive_date = datetime.utcnow() - timedelta(days=7)
            old_featured = Article.query.filter(
                Article.featured == True,
                Article.created_at < archive_date
            ).all()
            
            archived_count = 0
            for article in old_featured:
                article.featured = False  # Remove from featured to archive
                archived_count += 1
            
            if archived_count > 0:
                db.session.commit()
                logging.info(f"📁 Archived {archived_count} older featured articles")
                
        except Exception as e:
            logging.error(f"❌ Error archiving articles: {str(e)}")

def maintain_featured_count():
    """Ensure we always have 3-6 featured articles on homepage"""
    with app.app_context():
        try:
            featured_count = Article.query.filter_by(published=True, featured=True).count()
            
            # If we have too few featured articles, promote recent ones
            if featured_count < 3:
                recent_articles = Article.query.filter_by(
                    published=True, 
                    featured=False
                ).order_by(Article.created_at.desc()).limit(3 - featured_count).all()
                
                for article in recent_articles:
                    article.featured = True
                
                if recent_articles:
                    db.session.commit()
                    logging.info(f"📈 Promoted {len(recent_articles)} articles to featured")
                    
        except Exception as e:
            logging.error(f"❌ Error maintaining featured count: {str(e)}")

def run_social_monitoring():
    """Run automated social media monitoring"""
    with app.app_context():
        try:
            from services.reddit_service import RedditService
            from services.x_service import XService
            from services.youtube_service import YouTubeService
            from services.ai_service import AIService
            
            reddit = RedditService()
            x_service = XService()
            youtube = YouTubeService()
            ai = AIService()
            trends = []
            
            # Monitor X handles for new posts
            x_handles = ['CaitlinLong_', 'lopp', 'adam3us', 'woonomic', 'bitschmidty', 'LawrenceLepard', 'maxkeiser', 'jackmallers', 'TheBTCTherapist']
            for handle in x_handles:
                tweets = x_service.get_feedback(handle)
                for tweet in tweets:
                    from routes_social import take_screenshot, extract_screenshot_text
                    screenshot = take_screenshot(f"https://x.com/{handle}/status/{tweet['id']}")
                    screenshot_text = extract_screenshot_text(screenshot)
                    trends.append({
                        'type': 'x', 
                        'title': tweet['text'], 
                        'content': tweet['text'], 
                        'screenshot': screenshot, 
                        'screenshot_text': screenshot_text, 
                        'topic': tweet['topic'], 
                        'nuance': tweet['nuance'],
                        'source_url': f"https://x.com/{handle}/status/{tweet['id']}"
                    })
            
            # Monitor YouTube channels for new videos
            videos = youtube.get_recent_videos()
            for video in videos:
                from routes_social import take_screenshot, extract_screenshot_text
                screenshot = take_screenshot(f"https://www.youtube.com/watch?v={video['id']}")
                screenshot_text = extract_screenshot_text(screenshot)
                trends.append({
                    'type': 'youtube', 
                    'title': video['title'], 
                    'content': video['transcript'], 
                    'screenshot': screenshot, 
                    'screenshot_text': screenshot_text, 
                    'video_url': f"https://www.youtube.com/embed/{video['id']}", 
                    'topic': video['topic'], 
                    'nuance': video['nuance'],
                    'source_url': f"https://www.youtube.com/watch?v={video['id']}"
                })
            
            # Generate articles with auto-approval and immediate Substack publishing
            published_count = 0
            for trend in trends:
                prompt = f"Write a speculative article on '{trend['title']}': Discuss implications with a sharp, provocative, investigative tone, acknowledging potential inaccuracy but exploring Web3/Bitcoin impact. Incorporate screenshot context: {trend['screenshot_text']}."
                article_data = ai.generate_content_openai(prompt, system_prompt="You are an investigative journalist for Protocol Pulse, crafting bold, nuanced Web3 pieces.")
                
                # Create hyperlinked content that opens in new window
                content_with_link = f'<p><a href="{trend["source_url"]}" target="_blank" rel="noopener">🔗 View Original Post</a></p>\n{article_data}'
                
                article = Article()
                article.title = trend['title']
                article.content = content_with_link
                article.screenshot_url = trend['screenshot']
                article.video_url = trend.get('video_url')
                article.source_type = trend['type']
                article.source_url = trend['source_url']
                article.published = True  # Auto-approved
                article.category = 'Web3'
                article.author = "Al Ingle"
                article.featured = False  # Social content not auto-featured
                db.session.add(article)
                db.session.commit()
                
                # Auto-publish to Substack
                try:
                    from services.substack_service import SubstackService
                    substack_service = SubstackService()
                    newsletter_content = substack_service.format_content_for_newsletter(article.content, 'article')
                    substack_url = substack_service.publish_to_substack(article.title, newsletter_content, article.screenshot_url)
                    
                    if substack_url:
                        article.substack_url = substack_url
                        db.session.commit()
                        published_count += 1
                        logging.info(f"🚀 Auto-published social trend '{article.title}' to Substack: {substack_url}")
                except Exception as e:
                    logging.error(f"❌ Substack publishing failed for '{article.title}': {e}")
            
            logging.info(f"📱 Social monitoring completed: {len(trends)} trends found, {published_count} published to Substack")
            
        except Exception as e:
            logging.error(f"❌ Social monitoring error: {str(e)}")

# Schedule automated content generation
schedule.every(15).minutes.do(generate_scheduled_article)  # Generate breaking news every 15 minutes for testing
schedule.every(2).hours.do(run_social_monitoring)        # Monitor X/YouTube every 2 hours
schedule.every(6).hours.do(maintain_featured_count)     # Maintain homepage freshness
schedule.every(1).days.do(archive_old_articles)        # Daily archiving

def run_scheduler():
    """Main scheduler loop for automated content generation"""
    logging.info("🚀 Protocol Pulse Content Scheduler Started")
    logging.info("📰 Breaking news generation: Every 15 minutes")
    logging.info("📱 Social monitoring (X/YouTube): Every 2 hours")
    logging.info("📁 Article archiving: Daily")
    logging.info("🔄 Homepage maintenance: Every 6 hours")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logging.info("⏹️  Scheduler stopped by user")
            break
        except Exception as e:
            logging.error(f"❌ Scheduler error: {str(e)}")
            time.sleep(300)  # Wait 5 minutes before retrying

if __name__ == '__main__':
    run_scheduler()
```

---

## 🔧 HOW TO RUN AUTOMATION

### Option 1: Manual One-Time Generation (WORKS)
```bash
python3 generate_article_now.py
```

### Option 2: Continuous Loop (KEEPS CRASHING - DOES NOT WORK)
```bash
python3 auto_generate_loop.py
```

### Option 3: Full Scheduler (KEEPS CRASHING - DOES NOT WORK)
```bash
python3 automation_runner.py
```

---

## ❌ KNOWN ISSUES

1. **Automation crashes and doesn't stay running**
2. **Substack auto-publishing now requires CAPTCHA verification**  
3. **No persistent process management - automation dies when terminal closes**
4. **No error recovery - crashes permanently instead of restarting**

---

## ✅ WHAT WORKS

- ✅ Web server running on port 5000
- ✅ All AI APIs connected (Grok, Gemini, OpenAI, ElevenLabs, HeyGen)
- ✅ Database operational with PostgreSQL
- ✅ Manual article generation works perfectly
- ✅ World-class mobile CSS optimizations implemented
- ✅ Article formatting with professional typography

---

## 💡 SOLUTION NEEDED

The automation needs a proper **process manager** or **cron job** to:
1. Run `generate_article_now.py` every 15 minutes reliably
2. Restart automatically if it crashes
3. Run in background persistently
4. Log all activities

**Suggested implementations:**
- systemd service
- supervisord
- PM2 for Python
- Simple cron job running `generate_article_now.py` every 15 minutes

---

END OF COMPLETE CODEBASE
