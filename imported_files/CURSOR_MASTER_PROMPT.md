# PROTOCOL PULSE COMMAND CENTER
## FINAL Master Cursor Prompt

**Copy this ENTIRE prompt into Cursor Composer (Cmd+I) to deploy the complete system.**

---

```
I am deploying the Protocol Pulse Command Center. Execute the following systems in order:

## SYSTEM 1: X ENGAGEMENT SENTRY

### 1.1 Database Models (add to models.py)
Create these SQLAlchemy models:

```python
class XInboxTweet(db.Model):
    """Incoming tweets from monitored accounts"""
    id = db.Column(db.Integer, primary_key=True)
    tweet_id = db.Column(db.String(64), unique=True, nullable=False)
    author_handle = db.Column(db.String(50), nullable=False)
    author_name = db.Column(db.String(100))
    tweet_text = db.Column(db.Text, nullable=False)
    tweet_url = db.Column(db.String(500))
    tweet_created_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='new')  # new, drafted, approved, posted, rejected, skipped
    tier = db.Column(db.String(30))
    style = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class XReplyDraft(db.Model):
    """Generated reply drafts"""
    id = db.Column(db.Integer, primary_key=True)
    inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
    draft_text = db.Column(db.String(300), nullable=False)
    confidence = db.Column(db.Float)
    reasoning = db.Column(db.Text)
    style_used = db.Column(db.String(30))
    risk_flags = db.Column(db.Text)  # JSON array
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    inbox = db.relationship('XInboxTweet', backref='drafts')

class XReplyPost(db.Model):
    """Posted replies log"""
    id = db.Column(db.Integer, primary_key=True)
    inbox_id = db.Column(db.Integer, db.ForeignKey('x_inbox_tweet.id'), nullable=False)
    draft_id = db.Column(db.Integer, db.ForeignKey('x_reply_draft.id'))
    reply_tweet_id = db.Column(db.String(64))
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)
    response_payload = db.Column(db.Text)  # JSON
```

### 1.2 X Client Service (services/x_client.py)
Create a service with:
- `fetch_latest_tweets(handles, since_id_map)` - Uses Tweepy to get recent tweets
- `post_reply(in_reply_to_tweet_id, text)` - Posts reply with rate limiting
- OAuth1 user context for posting
- 429 backoff handling
- Maintains `since_id` per handle in database

### 1.3 Reply Generator Service (services/x_reply_writer.py)
Create a service that:
- Takes tweet + author + tier + style as input
- Uses the MATTY ICE prompt from config/final_response_prompt.py
- Calls Claude API (claude-sonnet-4-20250514)
- Returns JSON: {response, confidence, reasoning, style_used, skip, reason}
- Enforces all forbidden phrases and length limits
- Integrates current sentiment state if available

### 1.4 Scheduled Jobs (jobs/)
Create these scheduled jobs:

**x_listener.py** (runs every 5 minutes):
- Parse monitored handles from config
- Fetch new tweets for each handle
- Insert to XInboxTweet if new (dedupe by tweet_id)
- Skip retweets and replies
- Set status = 'new'

**x_draft_generator.py** (runs every 5 minutes):
- Query XInboxTweet where status='new' limit 10
- For each, call reply generator
- If skip=true, set status='skipped'
- If confidence >= 0.70, create XReplyDraft, set status='drafted'
- If confidence < 0.70, set status='skipped'

### 1.5 Admin Routes (routes/x_admin_routes.py)
Create these endpoints:

- GET `/admin/x-replies` - List all drafted tweets pending approval
- GET `/admin/x-replies/stats` - Service statistics
- POST `/admin/x-replies/<inbox_id>/approve` - Approve and post the draft
- POST `/admin/x-replies/<inbox_id>/reject` - Reject with optional reason
- POST `/admin/x-replies/<inbox_id>/edit` - Edit draft text before approving
- POST `/admin/x-replies/test-generate` - Test generation for a handle without posting
- POST `/admin/x-replies/run-cycle` - Manually trigger listener + generator

All routes require admin authentication.

### 1.6 Admin Dashboard Template (templates/admin/x_replies.html)
Build a sovereign-styled dashboard:
- List pending drafts with original tweet, author, generated response
- Show confidence score with color coding (green >0.85, yellow 0.70-0.85)
- Approve / Edit / Reject buttons
- Stats sidebar: responses today, queue size, last cycle time
- Real-time refresh every 30 seconds

## SYSTEM 2: MINING RISK ORACLE

### 2.1 Location Data (config/mining_locations.json)
Use the provided mining_locations.json with 18 global locations including:
- US (Texas, Wyoming, Georgia)
- Canada (Alberta, Quebec)
- Paraguay, El Salvador, Argentina
- Iceland, Norway, Finland
- UAE, Oman
- Russia, Kazakhstan
- Ethiopia, Bhutan, Malaysia

Each location has scores for all factors in political/economic/operational categories.

### 2.2 Risk Oracle Service (services/mining_risk_oracle.py)
Create a service with:
- `calculate_category_score(scores, category)` - Weighted average
- `calculate_overall_score(scores)` - Combined score (political 30%, economic 35%, operational 35%)
- `get_location_risk(location_id)` - Full risk assessment
- `get_all_locations()` - All locations with scores
- `compare_locations(location_ids)` - Side-by-side comparison
- `get_rankings(sort_by)` - Sorted by overall/political/economic/electricity/hashrate
- `generate_report(location_id)` - Full report with recommendations
- `check_for_alerts()` - Detect significant risk changes

### 2.3 API Routes (routes/mining_routes.py)
Create these endpoints:
- GET `/api/mining/regions` - Search/list regions
- GET `/api/mining/risk/<location_id>` - Full risk assessment
- GET `/api/mining/rankings?sort_by=overall` - Ranked list
- POST `/api/mining/compare` - Compare multiple locations
- GET `/api/mining/report/<location_id>` - Detailed report
- GET `/api/mining/map-data` - Simplified data for map

### 2.4 Dashboard Page (templates/mining_risk.html)
Build a world-class dashboard:
- Mapbox GL JS globe with color-coded markers (green=low risk, red=high)
- Click marker to select location
- Sidebar: location dropdown, overall score dial, category breakdown bars
- Real-time metrics grid: electricity rate, hashrate share, facilities, policy status
- Factor list sorted by lowest score (biggest risks first)
- Recommendations section
- Compare mode: select 2-3 locations side by side
- Sovereign red/black/white aesthetic matching Protocol Pulse

## INTEGRATION REQUIREMENTS

### Environment Variables (add to Replit Secrets):
```
X_BEARER_TOKEN=
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=
ANTHROPIC_API_KEY=
MAPBOX_TOKEN=
ADMIN_KEY=
```

### Dependencies (pip install):
```
tweepy
anthropic
requests
apscheduler
```

### Scheduler Setup (in main.py or app.py):
```python
from apscheduler.schedulers.background import BackgroundScheduler
from jobs.x_listener import run_listener
from jobs.x_draft_generator import run_draft_generator

scheduler = BackgroundScheduler()
scheduler.add_job(run_listener, 'interval', minutes=5)
scheduler.add_job(run_draft_generator, 'interval', minutes=5)
scheduler.start()
```

### Register Routes:
```python
from routes.x_admin_routes import register_x_admin_routes
from routes.mining_routes import register_mining_routes

register_x_admin_routes(app)
register_mining_routes(app)
```

## CRITICAL CONSTRAINTS

1. **NO AUTO-POSTING** - All replies require human approval initially
2. **Rate limits enforced** - Max 6/hour, 25/day
3. **Confidence gate** - Only queue drafts with confidence >= 0.70
4. **Blacklist active** - Skip tweets with promotional keywords
5. **Delay randomization** - 90-420 second delay before posting (when approved)
6. **Budget tracking** - Log all API calls for cost monitoring

## GO-LIVE CHECKLIST

After implementation:
1. Run database migrations
2. Verify all env vars are set
3. Test `/admin/x-replies/test-generate` with handle "saylor"
4. Verify mining risk map loads at `/mining-risk`
5. Check scheduler is running (logs show cycles)
6. Approve first draft manually to test posting
7. Monitor for 24 hours before considering auto-post

Files to create:
- models.py (add models)
- services/x_client.py
- services/x_reply_writer.py
- services/mining_risk_oracle.py
- jobs/x_listener.py
- jobs/x_draft_generator.py
- routes/x_admin_routes.py
- routes/mining_routes.py
- templates/admin/x_replies.html
- templates/mining_risk.html
- config/command_center_config.json
- config/mining_locations.json
- config/final_response_prompt.py
```

---

## WHAT THIS BUILDS

| System | Feature | Status |
|--------|---------|--------|
| X Sentry | Tweet monitoring | ✅ Every 5 min |
| X Sentry | AI response generation | ✅ Claude-powered |
| X Sentry | Confidence scoring | ✅ 0.70+ to queue |
| X Sentry | Approval workflow | ✅ Human required |
| X Sentry | Rate limiting | ✅ 6/hr, 25/day |
| Mining Oracle | 18 global locations | ✅ Full database |
| Mining Oracle | Weighted risk scoring | ✅ 30/35/35 split |
| Mining Oracle | Interactive map | ✅ Mapbox GL |
| Mining Oracle | Comparison tool | ✅ Side-by-side |
| Mining Oracle | Risk alerts | ✅ Auto-detect |

## BUDGET SUMMARY

| Component | Monthly Cost |
|-----------|-------------|
| X API Basic | $100 |
| Claude API | ~$5 |
| Mapbox Free | $0 |
| Other APIs | ~$20 |
| **Total** | **~$125/month** |

Well under your $500 limit.
