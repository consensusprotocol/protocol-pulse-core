# X PIPELINE, NOSTR QUALITY FILTER, X SPACES — STRATEGY + ASSET PROMPTS

## WHAT EXISTS (already built, needs activation)

### Tweet Monitor — `services/video_engine/sources/tweet_monitor.py`
- Uses Twitter API v2 Bearer Token
- Monitors: Saylor, Lyn Alden, Jeff Booth, Natalie Brunell (from `config/twitter_engagement.json`)
- Caches results 30min, fetches 24h window
- **BLOCKER:** `TWITTER_BEARER_TOKEN` env var not set in `.env`
- **Fix:** PBX needs to add `TWITTER_BEARER_TOKEN=xxxxx` to `~/protocol_pulse/.env`
  Get it from: https://developer.twitter.com/en/portal/dashboard → your app → Keys & Tokens

### X Spaces Scraper — `~/protocol_pulse/spaces_scraper/`
- Full pipeline: SpaceDetector → AudioCapture → RealtimeTranscriber → SentimentAnalyzer → FastAPI (port 8210)
- **NOT running** — needs to be started and added to cron/supervisor
- Monitors: ODELL, MartyBent, PrestonPysh, BitcoinMagazine, TheBitcoinConf, SimplyBitcoinTV

### Nostr Signal Service — `services/nostr_signal_service.py`
- Exists, built, has DB at `data/nostr_signal.db`
- Quality filtering is weak — random posts slipping through

---

## PART 1: X TWEET PIPELINE — WIRE IT NOW

### Step 1: PBX provides TWITTER_BEARER_TOKEN
Add to `~/protocol_pulse/.env`:
```
TWITTER_BEARER_TOKEN=your_bearer_token_here
```
Get from: https://developer.twitter.com/en/portal → your app → Bearer Token

### Step 2: Expand monitored accounts
Update `config/twitter_engagement.json` monitored_accounts to add Protocol Pulse's full target list:
```json
"saylor", "LynAldenContact", "JeffBooth", "natbrunell",
"BitcoinMagazine", "ODELL", "MartyBent", "PrestonPysh",
"WPO_Bitcoin", "SimplyBitcoinTV", "TheBitcoinConf",
"breedlove22", "gladstein", "niccarter", "dergigi",
"DocumentingBTC", "coryklippsten", "bitcoinmagazine",
"jamesvonmoltke" (PBX can customize this list)
```

### Step 3: Scoring algorithm — how to rank tweets for the video
```python
def score_tweet(tweet: dict) -> float:
    """Score a tweet for inclusion in Pulse Check social segment."""
    likes = tweet.get("public_metrics", {}).get("like_count", 0)
    retweets = tweet.get("public_metrics", {}).get("retweet_count", 0)
    replies = tweet.get("public_metrics", {}).get("reply_count", 0)
    quotes = tweet.get("public_metrics", {}).get("quote_count", 0)
    
    # Engagement score
    engagement = likes + (retweets * 3) + (replies * 2) + (quotes * 2)
    
    # Tier multiplier (tier 1 accounts get 2x boost)
    tier = tweet.get("_tier", 2)
    tier_mult = 2.0 if tier == 1 else 1.0
    
    # Recency boost (last 6h = 1.5x, 6-12h = 1.2x, 12-24h = 1.0x)
    age_hours = tweet.get("_age_hours", 24)
    recency = 1.5 if age_hours < 6 else (1.2 if age_hours < 12 else 1.0)
    
    # Content signal boost (price/macro/policy beats = 1.3x)
    text = tweet.get("text", "").lower()
    signal_keywords = ["bitcoin", "btc", "sats", "lightning", "etf", "fed", 
                       "inflation", "cbdc", "sovereignty", "mining", "halving"]
    signal_boost = 1.3 if any(k in text for k in signal_keywords) else 1.0
    
    return engagement * tier_mult * recency * signal_boost
```

### Step 4: Check schedule — 3x daily
Run tweet fetch at: 8AM, 1PM, 6PM EST (matches Oracle Briefing schedule)
Add to crontab:
```
0 13,18,23 * * * cd ~/protocol_pulse && python3 -c "from services.video_engine.sources.tweet_monitor import TweetMonitor; TweetMonitor([]).fetch_notable_tweets()" >> logs/tweet_monitor.log 2>&1
```

### Step 5: Wire to video pipeline
In `daily_producer.py`, before calling `write_script()`:
```python
from services.video_engine.sources.tweet_monitor import TweetMonitor
tweets = TweetMonitor(accounts=[...]).fetch_notable_tweets()
top_tweets = sorted(tweets, key=score_tweet, reverse=True)[:5]
social_posts = "\n".join([f"@{t['author_id']}: {t['text'][:140]}" for t in top_tweets])
# Pass to write_script(... social_posts=social_posts)
```

---

## PART 2: NOSTR QUALITY FILTER

### Problem: Random low-quality posts slipping through

### Fix — Tiered quality scoring for Nostr:
```python
def score_nostr_post(event: dict, trusted_pubkeys: list) -> float:
    """Score a Nostr event for Pulse Check inclusion."""
    
    # Zap count (lightning tips = highest quality signal on Nostr)
    zaps = event.get("zap_count", 0)
    zap_score = zaps * 5  # zaps are gold
    
    # Reactions/reposts
    reactions = event.get("reaction_count", 0)
    reposts = event.get("repost_count", 0)
    engagement = reactions + (reposts * 3)
    
    # Trusted author boost (well-known Bitcoin Nostr accounts)
    pubkey = event.get("pubkey", "")
    trusted_boost = 3.0 if pubkey in trusted_pubkeys else 1.0
    
    # Minimum quality gates (hard filter)
    if zaps == 0 and reactions < 5:
        return 0  # too low signal, exclude
    if len(event.get("content", "")) < 50:
        return 0  # too short, not substantive
    
    return (zap_score + engagement) * trusted_boost
```

**Trusted Nostr pubkeys to seed** (get from `nostr.band` or `primal.net` for known Bitcoiners):
- Odell, Marty Bent, Lyn Alden, Jeff Booth, Matt Odell, Giacomo (nvk), Calle (cashu dev), fiatjaf

Add `trusted_pubkeys` list to `config/nostr_signal_config.json` and load in `nostr_signal_service.py`.

---

## PART 3: X SPACES — ACTIVATE THE SCRAPER

### What the scraper does (already built):
- `detector.py` — polls Twitter API for live Spaces from monitored accounts
- `capture.py` — records audio via yt-dlp
- `transcriber.py` — real-time Whisper transcription
- `analyzer.py` — sentiment + key moment extraction
- `api_server.py` — FastAPI on port 8210 serving results

### How to activate:
```bash
# Start in tmux
tmux new-session -d -s spaces_scraper
tmux send-keys -t spaces_scraper 'cd ~/protocol_pulse/spaces_scraper && python3 main.py' Enter
```

Add to supervisor or cron to keep alive. Logs to `spaces_scraper/spaces_scraper.log`.

### Wire to video pipeline:
The spaces scraper API at `http://localhost:8210` serves:
- `GET /highlights` — top 5 key moments from recent Spaces (text + timestamp + speaker)
- `GET /clips` — audio clip files of those moments

In `daily_producer.py`, check for recent Space clips:
```python
import urllib.request
try:
    r = urllib.request.urlopen("http://localhost:8210/highlights", timeout=5)
    spaces_data = json.loads(r.read())
    # Add to social_posts or as dedicated spaces_segment in script
except:
    spaces_data = []
```

---

## PART 4: ASSET DESIGN PROMPTS FOR GRAPHIC DESIGNER / SORA / DALL-E

### Asset 1: Audio Waveform Visualizer Background (for narrator segments)
**Prompt for designer:**
"Design a 1920x1080 dark background for a Bitcoin intelligence show called Protocol Pulse. 
Style: 2026 premium YouTube — think Bloomberg Terminal meets cyberpunk. 
Elements: Deep space near-black navy base (#050510). Subtle hexagonal grid overlay at 8% opacity. 
Thin horizontal electric blue (#00D4FF) accent line at vertical center. 
Left side: vertical gradient bar in electric blue to purple (#7B2FFF). 
Bottom strip: 120px dark bar for ticker text (#0A0A1A).
Top right area: 200x60px reserved for watermark.
Center: 1800x200px transparent zone for audio waveform overlay.
NO text. NO logos. Just the background canvas."

### Asset 2: X Spaces Segment Overlay Card
"Design a lower-third overlay card for a video segment called 'X Spaces Eavesdrop'.
1920x200px, positioned at bottom of 1080p frame.
Left side: X (Twitter) logo in white on dark background, 80x80px.
Center text area: 'X SPACES EAVESDROP' in bold white, subtitle: '@[handle] is speaking'
Right: audio waveform bars (placeholder visual, 5 bars animated style)
Color scheme: Black base (#000000), X logo area, white text, electric blue accents.
Semi-transparent: 85% opacity so video shows through."

### Asset 3: Social Segment Title Card  
"Design a full-width title card for a segment called 'WHAT THE BITCOIN INTERNET IS SAYING'
1920x180px banner, positioned at top third of frame.
Font: Bold, modern, slightly condensed. White text on deep dark semi-transparent bg.
Left accent: thin vertical electric orange bar (#FF6B00)
Subtle Bitcoin ₿ symbol watermark at 5% opacity in background
This is for a daily Bitcoin intelligence video — premium, not meme-y."

### Asset 4: Platform Logo Pills
"Design a set of small platform identifier pills for video overlays.
Each: 280x56px, rounded rectangle, 80% opacity dark bg
- X/Twitter version: X logo + 'TWITTER/X' text
- Nostr version: Nostr purple logo (#7B2FFF) + 'NOSTR' text  
- YouTube version: YouTube red + 'YOUTUBE' text
These appear in top-right corner during social segments to ID the source platform."

---

## SUMMARY — WHAT PBX NEEDS TO DO

1. **Add to `~/protocol_pulse/.env`:** `TWITTER_BEARER_TOKEN=your_bearer_token`
   Get from: https://developer.twitter.com/en/portal
   (Free Basic tier = 10,000 reads/month — enough for our use)

2. **Confirm Nostr trusted pubkeys** — share list of Bitcoiners you follow on Nostr
   and we'll hard-code them as quality signal sources

3. **Custom assets** — use the prompts above with your designer or DALL-E/Midjourney
   for the waveform background, X Spaces overlay, social title card, platform pills

4. **X Spaces auto-start** — once Twitter bearer is configured, Claude Code can
   activate the spaces_scraper tmux session and wire it to the pipeline

Everything else (scoring, API wiring, pipeline integration) Claude Code executes autonomously
once the bearer token is in place.
