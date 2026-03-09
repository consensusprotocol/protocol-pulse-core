# SESSION 3: ALL-IN PLAYBOOK — PROTOCOL PULSE STRATEGIC BUILD
# ================================================================
# Autonomous build session on Ultron (4x RTX 4090) + Replit Relay
# Build ALL deliverables. Do not stop until every page is live and verified.
# ================================================================

## INFRASTRUCTURE

REPLIT RELAY:
TOKEN=581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552
URL=https://protocolpulse.replit.app/api/admin/exec
Run Replit commands: curl -s -X POST "$URL" -H "Content-Type: application/json" -d "{\"token\":\"$TOKEN\",\"cmd\":\"CMD\"}"
Keep relay scripts under 1.5KB. DB table is `articles` (not article). Podcast table is `podcast`.

ULTRON RELAY:
TOKEN=57eadb9f3e6503ecf381b9046f90f7c21dd98e1d9c17bc8d83061649b081edcf
URL=https://relay.protocolpulse.io/exec
Run Ultron commands: curl -s -X POST "$URL" -H "Content-Type: application/json" -d "{\"token\":\"$TOKEN\",\"cmd\":\"CMD\"}"

API keys on Replit env: ANTHROPIC_API_KEY ELEVENLABS_API_KEY PEXELS_API_KEY XAI_API_KEY
Ultron has: XAI_API_KEY in env, FFmpeg, Python3, 4x RTX 4090 GPUs, faster-whisper, yt-dlp.

GIT: Repo is consensusprotocol/protocol-pulse-core on GitHub. After ALL changes, git add, commit, push from Replit.

RIGOR: Before claiming done: 1) Build it 2) Test it with curl 3) Verify response is 200 4) Check rendered HTML has correct content 5) Only then move on.

---

## EXISTING SITE ARCHITECTURE (DO NOT BREAK)

**Framework:** Flask (Python 3.11) on Replit, templates extend `base.html`
**CSS:** Bootstrap 5.3 + custom CSS files in static/css/ (pulse.css, style.css, coindesk-style.css, stealth-alpha.css)
**Fonts:** Inter (body), JetBrains Mono (mono), Instrument Serif (display on dossier)
**JS:** Bootstrap JS, custom per-page JS in script blocks
**Design Language:** Dark theme (#000000 bg, #0a0a0a surfaces), red accent (#dc2626 / #CC0000), white text with opacity variants, subtle grid patterns, glass morphism panels. Reference `/dossier` page for premium design standard.
**Routes:** Defined in routes.py (8000+ lines), imported by app.py. Blueprints: onboarding_bp, oracle_bp, dashboard_bp.
**Models:** In models.py. Key existing models: Article, Podcast, Sponsor, Advertisement, User, PremiumAsk, ClipJob, ContentPerformance, EngagementEvent
**Existing Sponsor model fields:** name, company, email, website_url, logo_url, tier, status, impressions, clicks, ctr, budget_sats, spent_sats, cpm_sats, target_categories, target_personas, ad_copy, cta_text, cta_url, start_date, end_date
**Existing routes of note:** /premium, /dossier, /oracle, /articles, /podcasts, /charts, /stage, /pulse-forecast, /nostr-signal, /api/analytics/sponsor-metrics

ALL new pages must:
- Extend base.html: {% extends "base.html" %}
- Use {% block title %}, {% block extra_css %}, {% block content %}, {% block extra_js %}
- Match the dark theme design language (black bg, red accents, JetBrains Mono for data)
- Be mobile responsive
- Have proper meta descriptions for SEO

---

## THE VISION

We just analyzed the All-In Podcast transcript and extracted 8 strategic initiatives. This session builds the infrastructure for ALL of them. Think of Protocol Pulse as the "ESPN SportsCenter for Bitcoin" — we need the production value, editorial authority, and monetization infrastructure to match.

---

## BUILD 1: SPONSORS & MEDIA KIT PAGE (/sponsors)
**Priority: HIGHEST — This is how we make money**

Create a world-class media kit / sponsor landing page. This is what prospects see when the Sponsor Radar agent sends them our way.

### Route (add to routes.py):
```python
@app.route('/sponsors')
@app.route('/advertise')
@app.route('/media-kit')
def sponsors_page():
    return render_template('sponsors.html')
```

### Template: templates/sponsors.html
Design it like a premium SaaS pricing page meets a media kit. Sections:

**1. Hero Section:**
- Headline: "Reach the Bitcoin-First Audience"
- Subhead: "Protocol Pulse delivers daily intelligence to thousands of Bitcoiners who build, invest, and influence. Your brand. Their attention."
- CTA: "Download Media Kit" (link to a placeholder PDF) + "Contact Us" (mailto:sponsors@protocolpulse.io)

**2. Audience Stats Panel (animated counters):**
- Daily Articles: "50+"
- Monthly Pageviews: "Coming Soon" (honest — we're early stage, but frame as "growing fast")
- Newsletter Subscribers: "Growing"
- Podcast Downloads: "CypherPunk'd"  
- Audience Demo: "Builders, investors, operators. 85% male, 25-55, high-income, Bitcoin-first."
- Frame as: "Early sponsor = founding partner pricing. Lock in now."

**3. Sponsorship Tiers (card grid, 4 tiers):**

| Tier | Name | Price | Includes |
|------|------|-------|----------|
| 1 | **Pulse Presenting** | Custom | Pre-roll on Pulse Check videos, artponsors@protocolpulse.io
- Or link to Calendly/contact page

**7. Conference Sponsorship Upsell:**
- "Sponsor Our Events" section
- BitcoinDay Naples — [date TBD]
- BTC in DC at the Kennedy Center — [date TBD]
- "Event sponsors get stage time, booth, VIP access, content features"

### Design Notes:
- Use the dossier page as design reference for premium feel
- Animated gradient border on the top tier card
- Subtle particle/grid animation in hero
- Stats should use JetBrains Mono font
- Mobile: stack tier cards vertically
- Add subtle testimonial placeholder: "What our partners say" (empty sad: "Every AI announcement. Every market reaction. Every Bitcoin signal."
- Tagline: "Markets have shifted from asking WHEN cash flows get disrupted to IF they survive at all."

**2. Framework Explainer (the Chamath "When vs If" model):**
- Visual: Two-column or timeline showing the shift
- LEFT: "THE OLD WORLD: When will disruption happen?" — PE multiples steady, SaaS predictable, ARR is king
- RIGHT: "THE NEW WORLD: Will these cash flows survive at all?" — Massive de-risking, PEs compressing, WACCs exploding
- Pull the exact framework from Chamath: When → If transition, PE compression, revenue multiple collapse, WACC expansion
- Quote attribution: "The market is no longer debating when. It's debating if." — adapted from All-In analysis

**3. Disruption Events Timeline (hardcoded for V1, API-driven later):**
Each event card shows:
- Date
- AI Company + Announcement
- Affected Sector / Companies
- Market Impact (% drops)
- Bitcoin Signal (how this connects to the BTC thesis)

**Seed data (from transcript + our knowledge):**

Event 1: Feb 3, 2025 — Anthropic announces Claude legal plugin
- Affected: Thomson Reuters (-10%), LexisNexis (-10%), LegalZoom (-10%)
- Signal: "Traeeds trustless settlement → Bitcoin + Lightning

**5. "Jevons Paradox" Sidebar:**
- Explain: "When you lower the cost of something supply-constrained, demand explodes"
- Software engineering example from Aaron Levie
- Fortune 500 IT spend is only 5% — should be 50%
- Elon: "Companies are cybernetic organisms, part software, part human"

**6. Submit a Disruption Event:**
- Simple form: Date, AI Company, Announcement, Affected Companies, Source URL
- Stores to a new DB table or just emails to admin
- "Help us track the revolution"

### Design:
- Timeline layout with alternating left/right cat" → /sponsors
- CTA: "Get Notified" → email signup

**3. Why Sponsor Our Events:**
- "Direct access to high-net-worth Bitcoin-first audience"
- "Stage time for keynotes and panels"
- "Content creation: podcast interviews, video features, article coverage"
- "VIP networking with industry leaders"

**4. Past Events Gallery:**
- Placeholder section for photos/recap content
- "Content from our events reaches [X] people across all platforms"

### Design:
- Full-width hero with subtle venue photography (use Pexels for stock)
- Event cards: large, cinematic, with location/date overlay
- Sponsor CTA prominently placed

---

## BUILD 4: EDITORIAL FRAMEWORK INTEGRATION
**Priority: HIGH — Differentiates our content editorially**

### 4A. Article Tags Enhancement
Add two new article categories/tags to the system:

Via Replit relay, run SQL:
```sql
-- Check if category column exists, if not it's in the content
-- We'll add editorial framework tags via article generation
```

Modify the article generation system to include the "When vs If" framework:
- Create file: `editorial_framework.py` in the project root

```python
"""
Editorial Framework: The When vs If Lens
Every major story gets a

Style: Think Chamath Palihapitiya meets a war correspondent. Data-driven. Provocative. 
Never generic. Always connect back to Bitcoin or monetary policy.

Based on these stories: {stories}

Return a single editorial drop that would make someone stop scrolling.
"""
```

Push this file to Replit via relay.

### 4B. Recursive Thumbnail Intelligence System
Create file: `thumbnail_agent.py`

This agent:
1. Weekly searches YouTube creator optimization forums/articles
2. Extracts best practices for thumbnails and titles
3. Appends findings to THUMBNAIL_SKILLS.md
4. The article image generator references this file

```python
"""
Thumbnail & Title Recursive Intelligence Agent
Runs weekly. Searches for latest CTR optimization research.
Builds a compounding skills file.
"""
import os, json, datetime, requests

SKILLS_FILE = os.path.join(os.path.dirname(__file__), "THUMBNAIL_SKILLS.md")
XAI_KEY = os.environ.get("XAI_API_KEY", "")

def update_skills():
    """Search for latest thumbnail/title optimization research via Grok."""
    if not XAI_KEY:
        print("[thumbnail_agent] No XAI key, skipping")
        return
    
    prompt = """Search your knowledge for the latest YouTube thumbnail and title optimization 
    strategies from 2025-2026. Include:
    1. Heat map research (where do eyes land first?)
    2. Color psychology for CTR
    3. Text overlay best practices (font size, word count, contrast)
    4. Face/emotion impact on CTR
    5. Title formula patterns that drive clicks
    6. A/B testing insights from major creators
    7. Mr. Beast team techniques
    8. Algorithm-friendly practices
    
    Format as actionable rules with specific numbers where possible.
    Return as markdown with ## headers for each category."""
    
    r = requests.post("https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
        json={"model": "grok-3-latest", "messages": [{"role": "user", "content": prompt}]},
        timeout=60)
    
    if r.status_code == 200:
        content = r.json()["choices"][0]["message"]["content"]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Append to skills file
        with open(SKILLS_FILE, "a") as f:
            f.write(f"\n\n---\n## Updated: {timestamp}\n\n{content}\n")
        
        print(f"[thumbnail_agent] Skills updated: {l-3x CTR boost)
2. 3-4 words MAX on thumbnail text
3. High contrast: bright text on dark bg or vice versa
4. Red + Yellow + White = highest click colors
5. Thumbnail must be readable at 120x90px (mobile feed size)
6. Title: 50-60 chars max, front-load the hook
7. Numbers in titles increase CTR by 36%
8. "How/Why/What" outperform declarative titles
9. Curiosity gap: imply value without revealing it
10. Heat maps show eyes go: face → text → logo (design in that order)

### Bitcoin-Specific Rules
1. BTC price in thumbnail when it's dramatic (ATH, crash, round number)
2. Orange (#F7931A) for Bi_API_KEY", "")
RADAR_OUTPUT = os.path.join(os.path.dirname(__file__), "SPONSOR_RADAR_REPORT.md")

# Top podcasts to monitor for sponsors
TARGET_PODCASTS = [
    "All-In Podcast",
    "What Bitcoin Did",
    "Bitcoin Magazine Podcast",
    "The Pomp Podcast",
    "Bankless",
    "Unchained",
    "The Bitcoin Standard Podcast",
    "TFTC - Tales from the Crypt",
    "Stephan Livera Podcast",
    "Bitcoin Audible",
    "The Investor's Podcast - We Study Billionaires",
    "Coin Stories with Natalie Brunell",
    "Simply Bitcoin",
    "Swan Signal",
    "Preston Pysh - The Investor's Podcast",
   te URL

Focus on sponsors in these categories relevant to our Bitcoin audience:
{json.dumps(RELEVANT_CATEGORIES, indent=2)}

Return as a JSON array of sponsor objects.
"""
    
    r = requests.post("https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
        json={"model": "grok-3-latest", "messages": [{"role": "user", "content": prompt}]},
        timeout=90)
    
    if r.status_code == 200:
        content = r.json()["choices"][0]["message"]["content"]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        report = f"""# Sponsor Radar Report
## Generated: {timestamp}
## Protocol Pulse Advertising Intelligence

### Methodology
Scanned {len(TARGET_PODCASTS)} podcasts for active sponsors.
Filtered for relevance to Bitcoin-first audience.

### Findings

{content}

### Action Items
1. Cross-reference against existing Sponsor table in DB
2. Generate personalized outreach for top 10 prospects
3. Highlight sponsors leaving other shows (opportunity signal)
4. Track which sponsors appear across multiple shows (big spenders)

---
*Generated by Sponsor Radar Agent*
"""
        with open(RADAR_OUTPUT, "w") as f:
            f.write(report)
        print(f"[sponsor_radar] Report generated: {len(content)} chars")
    else:
        print(f"[sponsor_radar] Grok error: {r.status_code}")

if __name__ == "__main__":
    scan_sponsors()
```

---

## BUILD 5: RECURSIVE IMPROVEMENT RULE (THE META-SYSTEM)
**Priority: HIGH — This is what makes everything compound**

Create file: `RECURSIVE_IMPROVEMENT_RULE.md` in project root:

```markdown
# THE RECURSIVE IMPROVEMENT RULE
## Protocol Pulse Operating System

> Every automated system in Protocol Pulse has a skills file that gets uSOCIAL_SKILLS.md | (TODO) social_agent.py | Weekly |
| SEO | (TODO) SEO_SKILLS.md | (TODO) seo_agent.py | Weekly |

### The Rule
1. Every agent has a "soul file" (its core instructions) and a "skills file" (learned best practices)
2. Skills files are append-only logs — new learnings stack on top
3. Every Saturday, agents search for the latest research in their domain
4. Findings get added to skills files automatically
5. The next time the system runs, it uses the updated skills
6. This creates recursive, compounding improvement

### Cron Schedule
```
# Thumbnail skills update - every Saturdaeplit
CONTENT=$(cat sponsors.html | base64 -w0)
curl -s -X POST "$REPLIT_URL" -H "Content-Type: application/json" \
  -d "{\"token\":\"$TOKEN\",\"cmd\":\"echo $CONTENT | base64 -d > templates/sponsors.html\"}"
```

For files >1.5KB, split into chunks or use Python to write them:
```bash
curl -s -X POST "$URL" -H "Content-Type: application/json" \
  -d "{\"token\":\"$TOKEN\",\"cmd\":\"python3 -c \\\"import base64; open('templates/sponsors.html','wb').write(base64.b64decode('BASE64_CONTENT'))\\\"\"}"
```

### Files to push to Replit:
1. `templates/sponsors.html` — Sponsors/media kit page
2. `templates/disruption_tracker.html` — AI Disruption Tracker
3. `templates/events.html` — Events hub
4. `editorial_framework.py` — Editorial When vs If framework
5. `thumbnail_agent.py` — Thumbnail recursive agent
6. `THUMBNAIL_SKILLS.md` — Initial thumbnail skills
7. `sponsor_radar.py` — Sponsor radar agent
8. `SPONSOR_RADAR_REPORT.md` — (generated on first run)
9. `RECURSIVE_IMPROVEMENT_RULE.md` — Operating system doc

### Routes to add to routes.py (append near the end, before the last route):
```python
# === ALL-IN PLAYBOOK ROUTES (Session 3) ===

@app.route('/sponsors')
@app.route('/advertise')
@app.route('/media-kit')
def sponsors_page():
    """Media kit and sponsorship landing page."""
    return render_template('sponsors.html')

@app.route('/disruption-tracker')
@app.route('/ai-tracker')
@app.route('/kill-list')
def disruption_tracker():
    """AI Disruption Tracker — the Claude Kill List."""
    return render_template('disruption_tracker.html')

@app.route('/events')
def events_page():
    """Events hub — BitcoinDay + BTC in DC."""
    return render_template('events.html')
```

Use sed or Python to append these routes. Be careful not to break existing roudev/null || echo 'check app logs'\"}"
```

### Visual verification for each page:
```bash
# Check sponsors page has key content
curl -s "https://protocolpulse.replit.app/sponsors" | grep -c "Pulse Presenting"
# Should return 1+

# Check disruption tracker has key content  
curl -s "https://protocolpulse.replit.app/disruption-tracker" | grep -c "When vs If"
# Should return 1+

# Check events page has key content
curl -s "https://protocolpulse.replit.app/events" | grep -c "BitcoinDay"
# Should return 1+
```

---

## BUILD 8: GIT COMMIT & PUSH

After ALL pages are live and verified:
```bash
cd ~/emplate now. Build it complete. Then disruption tracker. Then events. Then agents. Then verify. Then push.
