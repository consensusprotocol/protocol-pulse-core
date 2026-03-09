Read PIPELINE_LAWS.md and PRODUCTION_DESIGN_LAWS.md first.

The overnight production rebuild just completed. This is the FOLLOW-UP session addressing remaining items.

=== TASK 1: WHOOSH SFX REPLACEMENT (10 min) ===

The current glitch_whoosh.wav is harsh pink noise. Replace with a gentle, cinematic, aerial low-hum whoosh.

Generate a better whoosh using layered synthesis:
  # Layer 1: Low frequency sweep (the "hum")
  ffmpeg -f lavfi -i "sine=frequency=120:duration=1.0,afade=t=in:d=0.1,afade=t=out:st=0.6:d=0.4,lowpass=f=400,volume=0.6" -ar 44100 -ac 2 /tmp/whoosh_low.wav
  
  # Layer 2: Mid frequency air (the "aerial" quality)  
  ffmpeg -f lavfi -i "anoisesrc=d=1.0:c=brown:r=44100,afade=t=in:d=0.08,afade=t=out:st=0.5:d=0.5,bandpass=f=800:width_type=h:w=400,volume=0.3" -ar 44100 -ac 2 /tmp/whoosh_mid.wav
  
  # Layer 3: High shimmer (subtle brightness)
  ffmpeg -f lavfi -i "anoisesrc=d=1.0:c=white:r=44100,afade=t=in:d=0.05,afade=t=out:st=0.4:d=0.6,bandpass=f=4000:width_type=h:w=1000,volume=0.1" -ar 44100 -ac 2 /tmp/whoosh_high.wav
  
  # Mix all 3 layers
  ffmpeg -i /tmp/whoosh_low.wav -i /tmp/whoosh_mid.wav -i /tmp/whoosh_high.wav -filter_complex "[0][1][2]amix=inputs=3:duration=first:dropout_transition=0" -ar 44100 -ac 2 assets/sfx/glitch_whoosh.wav

Also regenerate card_swoosh.wav with the same gentle quality but shorter (0.4s):
  Similar approach but with 0.4s duration and higher frequencies.

Verify: Play both files. They should sound cinematic and pleasant, not harsh.
Commit: git add assets/sfx/ -m 'fix: gentle cinematic whoosh SFX — layered synthesis'

=== TASK 2: PULSE TERMINAL API (2 hrs) ===

Build the Commander tier API endpoints on the Flask app (Replit side).
These expose the pipeline's intelligence data as a paid API.

Create routes_api_terminal.py:

Endpoints:
  GET /api/v2/terminal/topics
    Returns: topic velocity data from latest scan
    {
      "topics": [
        {"topic": "ETF flows", "channels": 7, "sentiment": "bullish", "velocity_score": 85},
        {"topic": "mining difficulty", "channels": 4, "sentiment": "bearish", "velocity_score": 42}
      ],
      "scan_time": "2026-03-05T06:00:00Z",
      "next_scan": "2026-03-05T12:00:00Z"
    }
  
  GET /api/v2/terminal/entities
    Returns: entity mention tracking
    {
      "entities": [
        {"name": "Saylor", "mentions_24h": 14, "sentiment_shift": "+23%"},
        {"name": "BlackRock", "mentions_24h": 9, "sentiment_shift": "+5%"}
      ]
    }
  
  GET /api/v2/terminal/sentiment
    Returns: overall market sentiment
    {
      "overall": {"score": 72, "label": "bullish", "change_24h": "+7"},
      "institutional": {"score": 85, "label": "very_bullish"},
      "retail": {"score": 55, "label": "neutral"}
    }
  
  GET /api/v2/terminal/breaking
    Returns: breaking news alerts (if velocity >= 4 channels in 3 hours)
    {
      "breaking": false,
      "last_alert": null,
      "monitoring": true
    }

Authentication:
  All /api/v2/terminal/* endpoints require API key:
  Header: X-API-Key: {subscriber_api_key}
  
  Create a simple API key system:
  - config/api_keys.json: {"keys": [{"key": "test-key-123", "tier": "commander", "subscriber": "test"}]}
  - Middleware checks X-API-Key header against config
  - Free tier: /api/v2/terminal/topics returns only top 3 topics
  - Commander tier ($49/mo): full access to all endpoints
  
  For now, create a test key so PBX can verify the endpoints work.

Data source:
  These endpoints read from data files that the pipeline writes:
  - data/intelligence/daily_signals.json (written by channel scanner)
  - data/intelligence/entity_mentions.json (written by NER pass)
  - data/intelligence/sentiment.json (written by sentiment classifier)
  
  If the data files don't exist yet, return mock data with a flag:
  {"mock": true, "note": "Pipeline data not yet accumulated. Real data populates after first production scan."}

Register blueprint in app.py (same pattern as routes_api_v2).

Verify: curl /api/v2/terminal/topics with test API key returns data
Commit and push to GitHub. Then push to Replit.

=== TASK 3: NODE PULSE MONITOR (1.5 hrs) ===

Build utils/node_monitor.py per CONTENT_INTELLIGENCE_LAWS Addendum C.

Bitnodes API integration:
  import requests
  
  def get_node_snapshot():
      resp = requests.get("https://bitnodes.io/api/v1/snapshots/latest/", timeout=10)
      data = resp.json()
      return {
          "total_nodes": data.get("total_nodes", 0),
          "timestamp": data.get("timestamp", ""),
          "latest_height": data.get("latest_height", 0)
      }
  
  def compare_snapshots(current, previous):
      if not previous:
          return {"net_change": 0, "is_milestone": False}
      net = current["total_nodes"] - previous["total_nodes"]
      # Check milestones: every 5K
      milestone = (current["total_nodes"] // 5000) != (previous["total_nodes"] // 5000)
      return {"net_change": net, "is_milestone": milestone, "milestone_number": (current["total_nodes"] // 5000) * 5000 if milestone else None}

Save snapshots to data/node_snapshots/{timestamp}.json.
Auto-tweet on milestones (when X posting pipeline is active).

Verify: python3 -c "from utils.node_monitor import get_node_snapshot; print(get_node_snapshot())"
Commit: git add utils/node_monitor.py -m 'feat: Node Pulse monitor — Bitnodes API + milestone detection'

=== TASK 4: PLAYWRIGHT TWEET SCREENSHOTS (1 hr) ===

Build utils/tweet_screenshot.py:

  from playwright.sync_api import sync_playwright
  
  def capture_tweet(tweet_url: str, output_path: str) -> bool:
      with sync_playwright() as p:
          browser = p.chromium.launch(headless=True)
          page = browser.new_page(viewport={"width": 1280, "height": 1024})
          
          # Navigate to tweet
          page.goto(tweet_url, wait_until="networkidle", timeout=15000)
          
          # Wait for tweet to render
          page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
          
          # Screenshot just the tweet element
          tweet = page.query_selector('article[data-testid="tweet"]')
          if tweet:
              tweet.screenshot(path=output_path)
              browser.close()
              return True
          
          # Fallback: screenshot the visible area
          page.screenshot(path=output_path, clip={"x": 0, "y": 0, "width": 800, "height": 600})
          browser.close()
          return True

Wire into social segment: when a tweet URL is available, capture screenshot
and use it as the card visual instead of the Remotion text card.

Verify: python3 -c "from utils.tweet_screenshot import capture_tweet; capture_tweet('https://x.com/saylor/status/1886847694068080989', '/tmp/test_tweet.png')" && ls -la /tmp/test_tweet.png
Commit: git add utils/tweet_screenshot.py -m 'feat: Playwright tweet screenshot capture'

After ALL tasks: git push origin main.


=== TASK 5: CHANNEL INTELLIGENCE DAEMON (1.5 hrs) ===

Per PIPELINE_LAWS Sections 21-22. Build the background monitoring system.

Create utils/channel_daemon.py:

This runs every 15 minutes via cron. It:
1. Reads channels.yaml for the full channel list
2. For each channel, runs yt-dlp --flat-playlist to get latest video IDs
3. Compares against data/channel_archive/known_videos.json
4. For NEW videos only:
   a. Download audio (yt-dlp -f bestaudio)
   b. Transcribe with Whisper (GPU-accelerated on 4090)
   c. Save full transcript to data/channel_archive/{channel_name}/{video_id}.json
   d. Run topic classification (use Claude API or simple keyword matching)
   e. Update data/intelligence/daily_signals.json
   f. Add video_id to known_videos.json
5. Skip channels that haven't uploaded in 48+ hours (check hourly instead of every 15 min)

Create data/channel_archive/known_videos.json:
  {"videos": {}, "last_scan": "", "total_archived": 0}

Each archived video entry:
  {
    "video_id": "abc123",
    "title": "Bitcoin Mining Difficulty Hits ATH",
    "channel": "Simply Bitcoin",
    "upload_date": "2026-03-05",
    "duration": 3600,
    "transcript_text": "full transcript here...",
    "timestamped_text": [{"start": 0.0, "end": 5.2, "text": "..."}],
    "topics": ["mining", "difficulty"],
    "sentiment": "bullish",
    "archived_at": "2026-03-05T06:30:00Z"
  }

Install the cron job:
  (crontab -l 2>/dev/null; echo "*/15 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/channel_daemon.py >> logs/channel_daemon.log 2>&1") | crontab -
  mkdir -p logs

Run one manual scan to seed the archive:
  python3 utils/channel_daemon.py

Report: How many channels scanned, how many new videos found, archive size.

Also update clip_selector.py to enforce the 5-CLIP RULE:
- Production mode: EXACTLY 5 clips from 5 DIFFERENT channels
- If LLM returns fewer than 5, or duplicates a channel, re-select
- If archive has fewer than 5 channels with fresh content, expand time window
- Log: "5-CLIP RULE: Selected {n} clips from {n} unique channels: {channel_list}"

Verify: python3 -c "from utils.channel_daemon import scan_all_channels; print('daemon OK')"
Verify: crontab -l shows the */15 entry
Commit: git add utils/channel_daemon.py data/channel_archive/ clip_selector.py -m 'feat: channel intelligence daemon + 5-clip rule enforcement'
