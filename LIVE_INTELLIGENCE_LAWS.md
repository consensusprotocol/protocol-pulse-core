# PROTOCOL PULSE — LIVE INTELLIGENCE LAWS
# Real-Time Stream Intelligence System — YouTube Live + X Spaces
# Status: GOSPEL. Load into every session touching live monitoring code.
# Created: 2026-03-05

---

## THE PRINCIPLE

Live streams and X Spaces are the purest form of real-time, unfiltered sentiment.
When a Bitcoin influencer goes live, they speak without editing, without revision.
That raw signal — captured, transcribed, and classified within seconds — gives
Protocol Pulse a 6-12 hour lead over every other media outlet.

This is the moat. Nobody else has this.

---

## SECTION 1: YOUTUBE LIVE STREAM DETECTION + CAPTURE

### Detection:
- Poll every 5 minutes via cron: `*/5 * * * *`
- Use yt-dlp `--flat-playlist --match-filter is_live` against channel /streams URL
- Only scan Tier 1 + Tier 2 channels from channels.yaml (priority <= 2)
- When a partner channel goes live, log: `LIVE DETECTED: {channel} — {title}`

### Capture:
- Use `yt-dlp --live-from-start -f bestaudio` for audio stream capture
- Audio captured as .m4a (AAC container, matching PIPELINE_LAWS audio spec)
- Capture runs as a background subprocess; monitor process health every 30 seconds
- If the stream ends, the capture process terminates naturally
- If capture fails, retry once after 60 seconds, then log failure and move on

### Processing:
- Stream audio to Whisper in 30-second chunks (do NOT wait for stream to end)
- Use ffmpeg to extract 30-second segments: `-ss {offset} -t 30 -ar 16000 -ac 1`
- Whisper model: `base` for real-time speed on GPU (large-v3 too slow for live)
- Each chunk transcribed immediately upon extraction
- Classify each chunk's topics and sentiment (keyword-based for speed, no API cost)
- Update `data/intelligence/live_signals.json` after each chunk

### Stream Lifecycle:
```
Channel goes live
  -> Detect (5 min poll)
  -> Start audio capture (background process)
  -> Every 30 seconds: extract chunk -> Whisper -> classify -> update signals
  -> Stream ends: finalize, compute overall sentiment, archive transcript
  -> Alert Terminal subscribers via API (WebSocket push for Commander+)
  -> Post X commentary if sentiment spike detected
  -> Video pipeline references live_signals.json in next episode
```

---

## SECTION 2: X SPACES DETECTION + CAPTURE

### Detection:
- Monitor partner accounts for active X Spaces
- Use twspace-dl or yt-dlp for X Spaces audio capture
- Guest token GraphQL detection (primary) with Playwright fallback
- Guest token refreshes ~13min; X public bearer hardcoded in detector
- Poll every 5 minutes, same cron cycle as YouTube Live

### Capture:
- Same 30-second chunk processing pipeline as YouTube Live
- X Spaces are the purest form of real-time unfiltered sentiment
- Multiple speakers in Spaces: transcribe all, attribute by audio fingerprint if possible
- If attribution fails, label as "Space participant" (still valuable for sentiment)

### Integration:
- X Spaces data flows into the same `live_signals.json` as YouTube Live
- Space entries tagged with `source: "x_spaces"` vs `source: "youtube_live"`
- Terminal API serves both sources through the same `/live` endpoint

---

## SECTION 3: DATA FLOW

```
Channel goes live -> Detect (5 min poll) -> Capture audio ->
Whisper chunk (30s) -> Classify (keywords, no API cost) -> live_signals.json ->
Terminal API (WebSocket push) -> X post (commentary on spikes) ->
Video pipeline (next episode references it)
```

### live_signals.json Schema:
```json
{
  "live_streams": [
    {
      "video_id": "abc123",
      "title": "Bitcoin price reaction LIVE",
      "channel": "Simply Bitcoin",
      "source": "youtube_live",
      "url": "https://www.youtube.com/watch?v=abc123",
      "started_at": "2026-03-05T19:00:00Z",
      "last_updated": "2026-03-05T19:45:00Z",
      "topics": ["price", "ETF"],
      "current_sentiment": 72,
      "sentiment_history": [
        {"time": "2026-03-05T19:00:30Z", "score": 65},
        {"time": "2026-03-05T19:01:00Z", "score": 72}
      ],
      "transcript_chunks": ["First 200 chars of each chunk..."],
      "status": "live"
    }
  ],
  "updated_at": "2026-03-05T19:45:00Z",
  "monitoring": true,
  "channels_watched": 42
}
```

---

## SECTION 4: TECHNICAL ARCHITECTURE

### Files:
- `utils/live_monitor.py` — Main daemon (detection + orchestration)
- `utils/live_capture.py` — Audio stream capture (future: dedicated module)
- `utils/live_transcriber.py` — Whisper chunked processing (future: dedicated module)
- `utils/live_classifier.py` — Topic + sentiment classification (future: dedicated module)
- `data/intelligence/live_signals.json` — Real-time output file

### V1 Architecture (current build):
All four functions (detect, capture, transcribe, classify) live in
`utils/live_monitor.py` as a single daemon. When complexity warrants it,
split into dedicated modules (V2).

### Cron:
```
*/5 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/live_monitor.py >> logs/live_monitor.log 2>&1
```

### Dependencies:
- yt-dlp (already installed)
- ffmpeg (already installed)
- whisper (already installed, GPU-accelerated on 4090)
- PyYAML (already installed)

---

## SECTION 5: COST MANAGEMENT

- Whisper runs FREE on the 4090 GPU (no API cost for transcription)
- Keyword-based classification: $0 (no API calls for V1)
- Claude API classification (V2, optional): ~$0.01 per 30-second chunk
- A typical 2-hour live stream = 240 chunks = ~$2.40 in Claude API (V2 only)
- V1 uses keyword classification only — total cost: $0
- Only capture from Tier 1 + Tier 2 channels (not all 76)
- Bandwidth: ~128kbps audio * 2 hours = ~115 MB per stream (negligible)

---

## SECTION 6: INTEGRATION WITH EXISTING SYSTEMS

### Terminal API:
- `GET /api/v2/terminal/live` — Current live streams + real-time topics
- Commander+ tier only (free tier gets "N streams active" count only)
- Response includes: channel, title, topics, current_sentiment, duration, url

### Video Pipeline:
- `daily_producer.py` checks `live_signals.json` for hot topics
- If a live stream captured a breaking topic, it gets priority in clip selection
- Live stream transcripts can be referenced in narrator script

### X Posting:
- Auto-commentary when live sentiment spikes (>80 or <20)
- Template: "{channel} is live discussing {topic}. Sentiment: {bullish/bearish}. Key quote: '{quote}'"
- Human review required for first 50 auto-posts (then fully autonomous)

---

## SECTION 7: ALERT THRESHOLDS

### Sentiment Spike Alert:
- Threshold: sentiment score > 80 (very bullish) or < 20 (very bearish)
- Requires at least 3 consecutive chunks trending in same direction
- Alert Terminal subscribers via WebSocket
- Post to X if the spike persists for 5+ minutes

### Multi-Stream Convergence:
- If 2+ channels go live within 30 minutes on the same topic: BREAKING
- This indicates a major event is unfolding
- Terminal gets priority alert
- X post: "BREAKING: {N} channels live on {topic}. Something is happening."

### Topic Velocity Boost:
- Live stream topics get a 1.5x velocity multiplier in daily_signals.json
- Rationale: a channel going LIVE on a topic signals higher urgency than a pre-recorded upload

---

## SECTION 8: STALENESS RULES

- Live streams expire from live_signals.json after 24 hours
- Streams marked `status: "ended"` after 6 hours with no new chunks
- Expired streams archived to `data/intelligence/live_archive/` (monthly rotation)
- The `/live` endpoint only returns streams with `status: "live"` or `status: "ended"` (last 6 hours)

---

## SECTION 9: LOOP DETECTION

### Purpose:
Filter out 24/7 ambient streams, price tickers, lofi radio, and other looped
content that pollutes live intelligence with noise. These streams appear "live"
but carry zero signal value.

### Scoring System:
Each stream is evaluated with red flags (discard indicators) and green flags (real content indicators).

**Red Flags (+1 each if true):**
- Duration > 8 hours (YouTube) or > 6 hours (X Spaces)
- Title contains loop keywords: "24/7", "live price", "live chart", "radio", "ambient", "lofi", "non-stop", "continuous", "price ticker"
- Transcript repetition: split into 50-word blocks with 25-word overlap; if unique blocks / total blocks < 50%, it's looped
- Consecutive live days >= 2 (stream has been "live" for multiple calendar days)
- Viewer count variance < 5% coefficient of variation across 3+ samples (bot/ambient pattern)

**Green Flags (+1 each if true):**
- Title contains real content keywords: "discussion", "debate", "interview", "ama", "recap", "reaction", "breaking", "analysis", "panel", "live with"
- Duration between 30 minutes and 5 hours (typical real stream length)

**Decision:** Discard if `red_flags >= 2 AND green_flags == 0`

### Integration:
- `utils/live_monitor.py`: `is_looped_stream()` called before adding to live_signals.json (8h threshold)
- `utils/spaces_monitor.py`: `is_looped_stream()` called before adding to live_signals.json (6h threshold)
- Discarded streams logged: `[LOOP_DETECT] Discarding: {title}`

---

*This document defines the real-time stream intelligence system.
Pair with: PIPELINE_LAWS.md, CONTENT_INTELLIGENCE_LAWS.md, PULSE_TERMINAL_LAWS.md*
