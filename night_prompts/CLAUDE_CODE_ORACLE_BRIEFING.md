# CLAUDE CODE PROMPT — ORACLE BRIEFING: AVATAR STAGE CONTENT ENGINE

## MISSION

Build an automated content pipeline that generates daily "Oracle Briefing" videos for the Protocol Pulse Avatar Stage (`/stage`). These are short (60-90 second), punchy intelligence briefs delivered by the Proto_P Oracle avatar with lip-synced animation, data overlays, and editorial opinion.

This is the SECOND video format alongside Pulse Check. Where Pulse Check is a dual-host highlight reel reacting to YouTube clips, the Oracle Briefing is a single authoritative voice — the Protocol Pulse AI — delivering its daily take.

## THE FORMAT

```
[0:00] GLITCH INTRO — 2s animated Protocol Pulse logo with glitch effect
[0:02] AVATAR APPEARS — Proto_P fades in with telemetry data overlay
[0:05] HOOK — "Here's what the network is telling us today."

[0:08] SEGMENT 1: THE NUMBER — One key metric with context
  "Bitcoin just crossed $97,000 — but the real signal is in the mempool. 
   Fee pressure is at its highest since November..."
  [Data overlay: BTC price chart, mempool visualization]

[0:25] SEGMENT 2: THE SIGNAL — Most important development
  "Michael Saylor's Strategy just filed for another $2 billion convertible 
   note offering. This is the fourth this quarter..."
  [Article screenshot overlay]

[0:45] SEGMENT 3: THE TAKE — Protocol Pulse editorial opinion
  "Here's what nobody's talking about: the hash rate just hit a new 
   all-time high while difficulty adjusts upward. Miners aren't 
   capitulating — they're doubling down..."
  [Hashrate chart overlay]

[1:05] SIGN-OFF
  "That's your Oracle Briefing. The signal is clear. Stay sovereign."
  [Proto_P fades out, Protocol Pulse logo]
```

## EXISTING INFRASTRUCTURE

### Avatar Server (RUNNING on Ultron)
- Location: `/home/ultron/protocol_pulse/oracle/avatar_server.py`
- Port: 8200 (via avatar.protocolpulse.io Cloudflare tunnel)
- Avatar image: `Proto_P_Avatar_512.png`
- Lip-sync: Wav2Lip-GAN (batch_size=48, 134fps on 4090)
- Voice: Jessica (ElevenLabs ID: cgSgspJ2msm6clMCkdW9)
- **Known issue:** Model reloads from disk every request (~13s overhead). FIX THIS by keeping the model in GPU memory.

### Avatar API
```bash
# Test current avatar endpoint
curl -s https://avatar.protocolpulse.io/health
# Generate speech: POST /generate with {text, voice_id}
```

### Protocol Pulse APIs (for data)
- `/api/articles/latest` — latest published articles
- `/api/media/sentiment` — fear & greed + sentiment data
- CoinGecko — BTC price + 24h change
- mempool.space — fees, mempool size, hashrate, block height, difficulty

## NEW FILES TO CREATE

Location: `~/protocol_pulse/oracle_briefing/`

### 1. `briefing_writer.py` — Script Generator

Uses Claude API to generate the Oracle Briefing script.

```python
BRIEFING_PROMPT = """You are the Protocol Pulse Oracle — an AI intelligence system that monitors the Bitcoin network 24/7. You speak with authority, precision, and occasionally dry wit. You are NOT a news anchor. You are a sovereign intelligence asset delivering classified-level signal.

VOICE: Authoritative but not robotic. Think: a brilliant analyst briefing a room of insiders. Short sentences. Punchy. Occasional rhetorical questions. Never filler words.

BAD: "Today we're going to take a look at some interesting developments in the Bitcoin space."
GOOD: "The network just told us something. Most people missed it."

BAD: "Bitcoin's price has increased by 3.2% over the last 24 hours."  
GOOD: "Ninety-seven thousand. That's where we are. But the price isn't the signal today — the mempool is."

Given the following data, write an Oracle Briefing script:

BTC Price: {btc_price} ({btc_change_24h})
Mempool: {mempool_size} MB, {fee_rate} sat/vB median
Hashrate: {hashrate} EH/s
Block Height: {block_height}
Fear & Greed: {fng_value} ({fng_label})
Difficulty Adjustment: {difficulty_change}

Top articles from last 24h:
{articles}

Top YouTube clips from last 24h (transcripts):
{clip_summaries}

Generate a JSON script:
{{
  "title": "Oracle Briefing — {date}",
  "hook": "One sentence hook that makes people stop scrolling",
  "segments": [
    {{
      "label": "THE NUMBER",
      "narration": "45 words max. One key metric with context.",
      "overlay": "price_chart" | "mempool_viz" | "hashrate_chart" | "article_screenshot" | "tweet_screenshot",
      "overlay_data": {{...}}
    }},
    {{
      "label": "THE SIGNAL",  
      "narration": "50 words max. Most important development.",
      "overlay": "...",
      "overlay_data": {{...}}
    }},
    {{
      "label": "THE TAKE",
      "narration": "50 words max. Editorial opinion. What nobody else is saying.",
      "overlay": "...",
      "overlay_data": {{...}}
    }}
  ],
  "signoff": "That's your Oracle Briefing. [custom closing based on today's vibe]",
  "thumbnail": {{
    "headline": "5 words max for thumbnail text",
    "metric": "$97,000" 
  }}
}}
"""
```

### 2. `briefing_producer.py` — Orchestrator

Full pipeline:

```
1. DATA GATHER
   - Fetch BTC price, mempool, hashrate, FNG from live APIs
   - Fetch latest PP articles from /api/articles/latest
   - Optionally: pull clip summaries from Pulse Check pipeline if available

2. SCRIPT GENERATION
   - Feed data to Claude API
   - Parse JSON response
   - Validate segment count and word limits

3. TTS GENERATION  
   - Concatenate all narration text with 0.5s pauses between segments
   - Send to ElevenLabs Jessica voice
   - Save as briefing_audio.wav

4. AVATAR GENERATION
   - Send audio to avatar server at localhost:8200
   - Receive lip-synced video of Proto_P
   - CRITICAL: Fix the model reload issue FIRST (see below)

5. OVERLAY COMPOSITING
   - Layer data overlays on top of/beside the avatar video
   - Layout: Avatar on left (40%), data overlay on right (60%)
   - Or: Avatar full-screen with semi-transparent data overlay
   - Use FFmpeg for compositing

6. INTRO/OUTRO
   - Prepend 2s glitch intro (pre-rendered, store in assets/)
   - Append 3s outro with logo
   - Create intro/outro once, reuse daily

7. THUMBNAIL
   - Generate 1280×720 thumbnail with Pillow
   - Proto_P avatar face + headline text + BTC price
   - Dark cinematic style with red accent

8. OUTPUT
   output/oracle_YYYYMMDD/
   ├── oracle_briefing_20260302.mp4   (1080p, 60-90s)
   ├── oracle_short.mp4               (vertical 1080×1920 for social)
   ├── thumbnail.jpg                  (1280×720)
   ├── script.json
   └── timing_report.txt
```

### 3. `overlay_engine.py` — Data Visualization Overlays

Generates visual overlays for each segment type:

**price_chart:**
- Pull 7-day BTC price from CoinGecko
- Render with matplotlib: dark background, green/red line, key price levels
- Semi-transparent PNG overlay (1920×1080)
- Animated reveal: line draws left-to-right over 3 seconds

**mempool_viz:**
- Pull mempool data from mempool.space API
- Render fee rate histogram or block weight visualization
- Color-coded: green (low fees) → red (congested)

**hashrate_chart:**
- Pull hashrate data from mempool.space
- Bar chart of recent difficulty epochs
- Highlight current vs previous

**article_screenshot:**
- Use playwright to screenshot a Protocol Pulse article URL
- Crop to headline + first paragraph
- Apply dark border + Protocol Pulse watermark

**tweet_screenshot:**
- Render a styled card with tweet text + author info
- Platform-colored accent (X=blue border)
- No need to screenshot real tweet — generate a styled version

### 4. `avatar_optimizer.py` — Fix Model Reload Issue

The avatar server currently reloads the Wav2Lip model from disk on every request (13s overhead). Fix this:

```python
# In avatar_server.py, the model should load ONCE at startup:
# 
# CURRENT (broken):
# def generate():
#     model = load_model('wav2lip.pth')  # 13s every time!
#     ...
#
# FIXED:
# MODEL = None
# def get_model():
#     global MODEL
#     if MODEL is None:
#         MODEL = load_model('wav2lip.pth')
#     return MODEL
#
# def generate():
#     model = get_model()  # instant after first call
#     ...

# Check current avatar_server.py for the pattern:
cat ~/protocol_pulse/oracle/avatar_server.py | grep -n "load_model\|Wav2Lip\|checkpoint\|torch.load"
```

After fixing, restart avatar server:
```bash
tmux send-keys -t avatar C-c
sleep 2
tmux send-keys -t avatar 'cd ~/protocol_pulse/oracle && python3 avatar_server.py' Enter
```

Verify: two requests back-to-back should show first request ~13s, second request <2s.

## STAGE PAGE INTEGRATION

After the Oracle Briefing pipeline works, the `/stage` page should:
- Auto-display the latest Oracle Briefing video
- Show an archive of past briefings
- Embed the video player with the thumbnail
- This is a FUTURE task — for now, just get the pipeline producing videos

## SCHEDULING

Oracle Briefing runs daily at 7:00 AM EST (before markets open).
Add to crontab or systemd timer:
```bash
# crontab -e
0 7 * * * cd /home/ultron/protocol_pulse/oracle_briefing && python3 briefing_producer.py >> /home/ultron/protocol_pulse/logs/oracle_briefing.log 2>&1
```

## DEPENDENCIES

```bash
# Check existing
which ffmpeg ffprobe playwright

# Install missing
pip install matplotlib Pillow feedgen playwright
playwright install chromium

# Verify ElevenLabs key
python3 -c "from video_pipeline_v3.relay import get_key; k=get_key('ELEVENLABS_API_KEY'); print(f'Key: {k[:8]}...' if k else 'MISSING')"

# Verify avatar server
curl -s https://avatar.protocolpulse.io/health
```

## TEST RUN

```bash
cd ~/protocol_pulse/oracle_briefing
python3 briefing_producer.py --test
```

Test mode:
- Use cached/sample data (don't fetch all APIs)
- Generate shorter briefing (~45s)
- Skip avatar generation if server is down (use static image fallback)
- Output to `output/test_oracle_YYYYMMDD_HHMMSS/`

## VERIFICATION

1. **Audio** — Jessica voice, clear, authoritative, no gTTS
2. **Avatar** — Lip-synced Proto_P, blinks, subtle head movement
3. **Overlays** — Data visualizations render correctly, not garbled
4. **Duration** — 60-90 seconds (not too long)
5. **Thumbnail** — Professional 1280×720 with headline + avatar
6. **Model fix** — Second avatar generation < 3s (not 13s)

## EXECUTION ORDER

1. **FIRST:** Fix avatar model reload issue in `avatar_server.py`
2. **SECOND:** Build `overlay_engine.py` (data visualizations)
3. **THIRD:** Build `briefing_writer.py` (Claude script generation)
4. **FOURTH:** Build `briefing_producer.py` (orchestrator)
5. **FIFTH:** Build thumbnail generation
6. **LAST:** Test end-to-end with `--test`

## RULES

- Work on `main` branch
- `claude --dangerously-skip-permissions` in tmux (interactive only, no `-p`)
- Avatar server fix is CRITICAL — do it first, verify timing improvement
- All API keys accessed via relay.py get_key() or environment variables
- matplotlib: use `Agg` backend (no GUI): `import matplotlib; matplotlib.use('Agg')`
- Playwright: use headless mode only
- Git commit + push when done
- Report: avatar timing before/after fix, overlay samples, file list, timing breakdown
