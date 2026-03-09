# PROTOCOL PULSE - COMPLETE WORKING CODE (December 19, 2025)

## ✅ STATUS: AUTOMATION IS NOW WORKING!

**Latest Test Results:**
- ✅ Article #17 generated: "Lightning Network payment volume breaks monthly records..."
- ✅ Automation run #3: SUCCESS (took 19 seconds)
- ✅ Using Gemini API (GEMINI_API_KEY working)
- ✅ Grok model updated from grok-2-1212 → grok-3

---

## 🚨 WHAT WAS FIXED

1. **Grok model deprecated** - Updated from `grok-2-1212` to `grok-3`
2. **Missing API keys** - OpenAI and Anthropic keys were NOT set, so added Gemini as primary
3. **Content generator updated** - Now uses Gemini first, with fallbacks
4. **Webhook endpoint added** - `/api/trigger-automation` for scheduled calls

---

## 🚀 HOW TO ENABLE AUTOMATIC ARTICLE GENERATION

### Step 1: Set Up Scheduled Deployment in Replit

1. Open your Replit project
2. Click the **magnifying glass** (search) or go to **All Tools**
3. Type **"Publishing"** and select it
4. Click **"Scheduled"** option
5. Click **"Set up your published app"**
6. Configure:
   - **Run Command:** `python3 scheduled_job.py`
   - **Schedule:** Type "Every 15 minutes" or use cron: `*/15 * * * *`
7. Click **Deploy**

**That's it!** Articles will now generate automatically every 15 minutes.

---

## 📁 KEY FILES (COMPLETE CODE)

### 1. `scheduled_job.py` - Scheduled Deployment Entry Point

```python
#!/usr/bin/env python3
"""
Scheduled Job for Replit Scheduled Deployments
Run Command: python3 scheduled_job.py
Schedule: Every 15 minutes (or */15 * * * *)
"""
import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print(f"[{datetime.utcnow().isoformat()}] Starting scheduled article generation...")
    
    try:
        from app import app
        from services.automation import generate_article_with_tracking
        
        with app.app_context():
            result = generate_article_with_tracking()
            
            print(json.dumps({
                'timestamp': datetime.utcnow().isoformat(),
                'result': result
            }, indent=2))
            
            if result.get('success'):
                print(f"SUCCESS: Generated article #{result.get('article_id')}: {result.get('title')}")
                return 0
            elif result.get('skipped'):
                print("SKIPPED: Another process is running")
                return 0
            else:
                print(f"FAILED: {result.get('error')}")
                return 1
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
```

---

### 2. `services/automation.py` - Core Automation Logic

```python
"""
Automation helper with database-backed execution tracking and locking
Ensures idempotent execution and prevents duplicate runs
"""
import logging
from datetime import datetime, timedelta
from app import app, db
from models import Article
from services.content_generator import ContentGenerator
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

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

def acquire_lock(task_name='article_generation', ttl_minutes=10):
    """Acquire execution lock to prevent duplicate runs"""
    from models import AutomationRun
    
    cutoff = datetime.utcnow() - timedelta(minutes=ttl_minutes)
    active_run = AutomationRun.query.filter(
        AutomationRun.task_name == task_name,
        AutomationRun.started_at >= cutoff,
        AutomationRun.finished_at == None
    ).first()
    
    if active_run:
        logging.warning(f"⏳ Lock held by run {active_run.id}")
        return None
    
    run = AutomationRun(
        task_name=task_name,
        started_at=datetime.utcnow(),
        status='running'
    )
    db.session.add(run)
    db.session.commit()
    logging.info(f"🔒 Lock acquired: {run.id}")
    return run

def release_lock(run, status='success', error=None):
    """Release execution lock and update status"""
    run.finished_at = datetime.utcnow()
    run.status = status
    if error:
        run.error = str(error)[:500]
    db.session.commit()
    logging.info(f"🔓 Lock released: {run.id} ({status})")

def generate_article_with_tracking():
    """Core generation routine with structured logging and error handling"""
    with app.app_context():
        run = acquire_lock()
        if not run:
            logging.info("⏭️  Skipping: Another process is running")
            return {'skipped': True}
        
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
                
                # Try Substack (non-blocking)
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
                    logging.error(f"❌ Substack error (non-fatal): {e}")
                
                release_lock(run, 'success')
                return {'success': True, 'article_id': article.id, 'title': article.title}
            else:
                logging.error("❌ No article data generated")
                release_lock(run, 'failed', 'No article data generated')
                return {'success': False, 'error': 'No article data'}
                
        except Exception as e:
            logging.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            release_lock(run, 'failed', e)
            return {'success': False, 'error': str(e)}

def get_last_run_status():
    """Get the status of the last automation run for health checks"""
    from models import AutomationRun
    
    last_run = AutomationRun.query.order_by(AutomationRun.started_at.desc()).first()
    
    if not last_run:
        return {'status': 'never_run'}
    
    return {
        'last_run': last_run.started_at.isoformat() if last_run.started_at else None,
        'status': last_run.status,
        'finished': last_run.finished_at.isoformat() if last_run.finished_at else None,
        'error': last_run.error
    }
```

---

### 3. `services/grok_service.py` - Updated Grok Model

```python
# Line 20 - Updated model
self.model = "grok-3"  # Was grok-2-1212 (deprecated)
```

---

### 4. `services/content_generator.py` - Uses Gemini Now

```python
# Line 9 - Added import
from services.gemini_service import gemini_service

# Line 15 - Added to __init__
self.gemini_service = gemini_service

# Lines 157-181 - Updated content generation
# Generate the main content using Gemini (primary) with fallbacks
content = None

# Try Gemini first (we have API key)
try:
    content = self.gemini_service.generate_content(formatted_prompt, system_prompt)
except Exception as e:
    logging.warning(f"Gemini generation failed: {e}")

# Fallback to OpenAI if available
if not content:
    try:
        content = self.ai_service.generate_content_openai(formatted_prompt, system_prompt)
    except Exception as e:
        logging.warning(f"OpenAI generation failed: {e}")

# Fallback to Anthropic if available
if not content:
    try:
        content = self.ai_service.generate_content_anthropic(formatted_prompt, system_prompt)
    except Exception as e:
        logging.warning(f"Anthropic generation failed: {e}")

if not content:
    raise Exception("Failed to generate content with any AI service")
```

---

### 5. `services/gemini_service.py` - Added generate_content Method

```python
def generate_content(self, prompt, system_prompt=None):
    """Generate general content using Gemini - primary method for content generation"""
    try:
        config = types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=3000
        )
        
        if system_prompt:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
                max_output_tokens=3000
            )
        
        response = self.client.models.generate_content(
            model=self.text_model,
            contents=prompt,
            config=config
        )
        
        return response.text or None
        
    except Exception as e:
        logging.error(f"Gemini content generation error: {e}")
        return None
```

---

### 6. `models.py` - Added AutomationRun Model

```python
class AutomationRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # running, success, failed, skipped
    error = db.Column(db.String(500))  # Error message if failed
```

---

### 7. `routes.py` - Added Trigger and Health Endpoints

```python
@app.route('/api/trigger-automation', methods=['POST', 'GET'])
def trigger_automation():
    """Webhook endpoint to trigger article generation from Scheduled Deployment"""
    from services.automation import generate_article_with_tracking
    
    result = generate_article_with_tracking()
    
    if result.get('success'):
        return jsonify({
            'status': 'success',
            'message': f"Article generated: {result.get('title')}",
            'article_id': result.get('article_id')
        }), 200
    elif result.get('skipped'):
        return jsonify({
            'status': 'skipped',
            'message': 'Another process is running'
        }), 200
    else:
        return jsonify({
            'status': 'failed',
            'message': result.get('error', 'Unknown error')
        }), 500

@app.route('/health/automation')
def automation_health():
    """Health check endpoint for automation monitoring"""
    from services.automation import get_last_run_status
    from datetime import datetime, timedelta
    
    status = get_last_run_status()
    
    if status.get('status') == 'never_run':
        return jsonify({
            'status': 'warning',
            'message': 'Automation has never run',
            'details': status
        }), 200
    
    if status.get('last_run'):
        last_run_time = datetime.fromisoformat(status['last_run'])
        if datetime.utcnow() - last_run_time > timedelta(minutes=20):
            return jsonify({
                'status': 'stale',
                'message': 'Automation is stale (last run >20 minutes ago)',
                'details': status
            }), 200
    
    if status.get('status') == 'failed':
        return jsonify({
            'status': 'failed',
            'message': 'Last automation run failed',
            'details': status
        }), 200
    
    return jsonify({
        'status': 'healthy',
        'message': 'Automation is running normally',
        'details': status
    }), 200
```

---

## 📊 TEST COMMANDS

### Manual Trigger (Instant Test)
```bash
curl http://localhost:5000/api/trigger-automation
```

### Health Check
```bash
curl http://localhost:5000/health/automation
```

### View Recent Articles
```sql
SELECT id, title, created_at FROM article ORDER BY created_at DESC LIMIT 5;
```

### View Automation Runs
```sql
SELECT * FROM automation_run ORDER BY started_at DESC LIMIT 5;
```

---

## ✅ CURRENT STATUS

| Component | Status |
|-----------|--------|
| Web Server | ✅ Running (port 5000) |
| Gemini API | ✅ Working (primary AI provider) |
| Grok API | ✅ Updated to grok-3 |
| Database | ✅ Operational |
| Automation Trigger | ✅ `/api/trigger-automation` working |
| Health Check | ✅ `/health/automation` working |
| Article #17 | ✅ Just generated successfully! |

---

## 🎯 NEXT STEP

**Go to Publishing > Scheduled in Replit and set up the scheduled deployment:**

1. Run Command: `python3 scheduled_job.py`
2. Schedule: "Every 15 minutes"
3. Deploy

**Articles will then auto-generate every 15 minutes without any manual intervention!**

---

END OF COMPLETE WORKING CODE
