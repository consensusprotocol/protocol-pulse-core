# CLAUDE CODE PROMPT — X SPACES LIVE SCRAPER: REAL-TIME SENTIMENT ENGINE

## IMPORTANT: SEPARATE PROJECT DIRECTORY

This is a STANDALONE service. It does NOT live in the Protocol Pulse Flask app or media_reforge.

```bash
mkdir -p ~/protocol_pulse/spaces_scraper
cd ~/protocol_pulse/spaces_scraper
```

Work ONLY in this directory. No git branch needed — this directory is new and won't conflict with anything.

## WHAT WE'RE BUILDING

A service that:
1. Monitors target X/Twitter accounts for live Spaces
2. Joins the Space programmatically and captures the audio stream
3. Transcribes audio in real-time using Whisper on the local RTX 4090
4. Extracts sentiment/topics from the transcript using Claude or Gemini
5. Exposes results via a local API that the Protocol Pulse media page can consume

This gives Protocol Pulse a COMPETITIVE EDGE — real-time intelligence from live Bitcoin Spaces that no other aggregator has.

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────┐
│                  SPACES SCRAPER                      │
│                                                      │
│  ┌──────────┐   ┌──────────┐   ┌─────────────────┐ │
│  │ Space     │──▶│ Audio    │──▶│ Whisper         │ │
│  │ Detector  │   │ Capture  │   │ Transcriber     │ │
│  │           │   │ (HLS)    │   │ (RTX 4090)      │ │
│  └──────────┘   └──────────┘   └────────┬────────┘ │
│       │                                  │          │
│       │              ┌───────────────────▼────────┐ │
│       │              │ Sentiment Analyzer          │ │
│       │              │ (Claude/Gemini API)         │ │
│       │              └───────────────────┬────────┘ │
│       │                                  │          │
│  ┌────▼──────────────────────────────────▼────────┐ │
│  │              REST API (port 8210)               │ │
│  │  GET /spaces/active  — current live spaces      │ │
│  │  GET /spaces/feed    — latest transcripts       │ │
│  │  GET /spaces/sentiment — rolling sentiment      │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## PHASE 1: SPACE DETECTOR

### Option A: X API v2 (if we have API access)

Check for X API credentials:
```bash
grep -r "X_BEARER\|TWITTER_BEARER\|X_API\|TWITTER_API" ~/protocol_pulse/.env ~/protocol_pulse/config*.py 2>/dev/null
env | grep -i "twitter\|x_api\|x_bearer" 2>/dev/null
```

If bearer token exists, use the Spaces search endpoint:
```
GET https://api.twitter.com/2/spaces/search?query=bitcoin&state=live
Authorization: Bearer {token}
```

This returns live Spaces matching "bitcoin" with title, host, participant count.

### Option B: Playwright Scraper (if no API access)

Use Playwright (headless Chromium) to:
1. Navigate to `https://x.com/{username}` for each target account
2. Check for the purple "LIVE" badge on their profile
3. If live, click into the Space and intercept the HLS stream URL from network requests

```python
from playwright.async_api import async_playwright

TARGET_ACCOUNTS = [
    "sabordebitcoin", "BitcoinMagazine", "thebitcoinlayer", 
    "WhatBitcoinDid", "DocumentingBTC", "MartyBent",
    "PeterMcCormack", "gladstein", "daboradebitcoin",
    "FossGregfoss", "maxkeiser", "stabordebitcoin"
]

async def check_for_live_spaces():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for account in TARGET_ACCOUNTS:
            page = await browser.new_page()
            await page.goto(f"https://x.com/{account}")
            # Look for Space indicators in the DOM
            # Check for HLS stream URLs in network requests
```

**Install Playwright:**
```bash
pip install playwright
playwright install chromium
```

### Option C: Guest Token + Direct API (No Auth Required)

X's guest authentication flow can be used to access some endpoints:
```python
import requests

# Get guest token
r = requests.post("https://api.twitter.com/1.1/guest/activate.json",
    headers={"Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=..."})
guest_token = r.json()["guest_token"]

# Search for live audio spaces
r = requests.get("https://twitter.com/i/api/graphql/...",
    headers={
        "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=...",
        "X-Guest-Token": guest_token
    })
```

Try all three options in order. Use whichever works.

## PHASE 2: AUDIO CAPTURE (HLS Stream Interception)

X Spaces audio is streamed via HLS (HTTP Live Streaming). The stream URL looks like:
```
https://prod-fastly-{region}.video.pscp.tv/Transcoding/v1/hls/{stream_id}/non_transcode/us-east-1/periscope-replay-direct-prod-us-east-1-public/audio-only/...
```

To capture:
1. Use Playwright to join the Space
2. Intercept network requests matching `*.m3u8` or `*pscp.tv*` or `*video.periscope.tv*`
3. Parse the HLS playlist
4. Download audio segments as they appear (each is ~2-6 seconds)
5. Pipe segments to Whisper in near-real-time

```python
class AudioCapture:
    def __init__(self, space_url):
        self.segments = asyncio.Queue()
        
    async def intercept_hls(self, page):
        """Capture HLS stream URL from network requests"""
        async def handle_request(route, request):
            if 'pscp.tv' in request.url and '.m3u8' in request.url:
                self.hls_url = request.url
                print(f"Captured HLS: {self.hls_url}")
            await route.continue_()
        
        await page.route("**/*pscp.tv*", handle_request)
    
    async def pull_segments(self):
        """Continuously pull new audio segments from HLS playlist"""
        while self.running:
            # Parse m3u8 playlist for new .aac segments
            # Download each new segment
            # Add to queue for transcription
            await asyncio.sleep(2)
```

Alternative: Use `ffmpeg` to capture the HLS stream directly:
```bash
ffmpeg -i "{hls_url}" -c:a pcm_s16le -ar 16000 -ac 1 -f wav pipe:1
```

This outputs raw audio that can be piped directly to Whisper.

## PHASE 3: REAL-TIME WHISPER TRANSCRIPTION

Use `faster-whisper` on the RTX 4090 for GPU-accelerated transcription:

```bash
pip install faster-whisper
```

```python
from faster_whisper import WhisperModel

class RealtimeTranscriber:
    def __init__(self):
        # Load model once, keep in GPU memory
        self.model = WhisperModel("large-v3", device="cuda", compute_type="float16")
        self.transcript_buffer = []
        
    def transcribe_segment(self, audio_segment_path):
        """Transcribe a single audio segment (~5s chunk)"""
        segments, info = self.model.transcribe(
            audio_segment_path,
            beam_size=5,
            language="en",
            vad_filter=True,  # Skip silence
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        text = " ".join([s.text for s in segments])
        self.transcript_buffer.append({
            "text": text,
            "timestamp": time.time(),
            "confidence": info.language_probability
        })
        return text
    
    def get_rolling_transcript(self, last_n_minutes=5):
        """Get transcript from last N minutes"""
        cutoff = time.time() - (last_n_minutes * 60)
        recent = [t for t in self.transcript_buffer if t["timestamp"] > cutoff]
        return " ".join([t["text"] for t in recent])
```

**Performance target:** Whisper large-v3 on RTX 4090 should transcribe 5s of audio in <1s. This means real-time transcription with a ~5s delay.

## PHASE 4: SENTIMENT EXTRACTION

Every 30 seconds, analyze the rolling transcript:

```python
class SentimentAnalyzer:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")  # Use Gemini (free) for this
        
    async def analyze(self, transcript_chunk):
        """Extract sentiment and topics from transcript"""
        prompt = f"""Analyze this Bitcoin Spaces transcript for sentiment and key topics.
        
Transcript (last 2 minutes):
{transcript_chunk}

Respond in JSON only:
{{
  "sentiment_score": 0-100 (0=extreme fear, 100=extreme greed),
  "sentiment_label": "EXTREME FEAR|FEAR|NEUTRAL|GREED|EXTREME GREED",
  "key_topics": ["topic1", "topic2"],
  "notable_quotes": ["quote1"],
  "market_signals": ["signal1"],
  "confidence": 0.0-1.0
}}"""
        
        # Use Gemini 2.5 Flash (free tier, fast)
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            params={"key": self.api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        return parse_json_response(response)
```

## PHASE 5: REST API

Expose results on port 8210 (Flask or FastAPI):

```python
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Spaces Scraper API")

@app.get("/spaces/active")
async def active_spaces():
    """List currently monitored live spaces"""
    return {
        "spaces": [
            {
                "id": "1234567890",
                "host": "@sabordebitcoin",
                "title": "Bitcoin Weekly Roundup",
                "participants": 342,
                "started_at": "2026-03-02T03:00:00Z",
                "duration_minutes": 45,
                "is_recording": True
            }
        ]
    }

@app.get("/spaces/feed")
async def transcript_feed():
    """Latest transcript chunks with sentiment"""
    return {
        "chunks": [
            {
                "text": "I think we're seeing a clear accumulation pattern...",
                "speaker": "unknown",  # Speaker diarization is hard, optional
                "timestamp": "2026-03-02T03:45:00Z",
                "sentiment": 72
            }
        ]
    }

@app.get("/spaces/sentiment")
async def rolling_sentiment():
    """Rolling sentiment from all active spaces"""
    return {
        "overall_score": 68,
        "label": "GREED",
        "active_spaces_count": 2,
        "sample_window_minutes": 10,
        "topics": ["accumulation", "ETF inflows", "hashrate ATH"],
        "updated_at": "2026-03-02T03:46:00Z"
    }
```

## FILE STRUCTURE

```
~/protocol_pulse/spaces_scraper/
├── main.py              — Entry point, starts detector + API server
├── detector.py          — Finds live Bitcoin Spaces (API or Playwright)
├── capture.py           — HLS audio stream capture
├── transcriber.py       — Whisper real-time transcription
├── analyzer.py          — Gemini sentiment extraction
├── api_server.py        — FastAPI REST endpoints (port 8210)
├── config.py            — API keys, target accounts, relay config
├── requirements.txt     — Dependencies
└── README.md            — Architecture and usage docs
```

## DEPENDENCIES

```
faster-whisper>=0.10.0
playwright>=1.40.0
fastapi>=0.100.0
uvicorn>=0.23.0
requests>=2.31.0
aiohttp>=3.9.0
m3u8>=3.6.0
```

Install:
```bash
cd ~/protocol_pulse/spaces_scraper
pip install -r requirements.txt
playwright install chromium
```

## CLOUDFLARE TUNNEL

The API should be accessible externally. Set up a Cloudflare tunnel:
```bash
# Check if cloudflared is available
which cloudflared
# If the avatar server uses a tunnel, follow the same pattern
cat /etc/systemd/system/cloudflare-avatar.service 2>/dev/null
```

Target URL: `spaces.protocolpulse.io` → localhost:8210

## TESTING

### Test 1: Detector
```bash
python3 detector.py --test
# Should output: list of currently live Bitcoin Spaces (or "none found")
```

### Test 2: Transcriber
```bash
python3 transcriber.py --test
# Should: load Whisper model, transcribe a 10s test audio, print result + timing
# Expected: <1s transcription time for 10s audio on RTX 4090
```

### Test 3: Full Pipeline (if a Space is live)
```bash
python3 main.py --test
# Should: detect Space, capture 60s of audio, transcribe, analyze sentiment, print report
```

### Test 4: API Server
```bash
python3 main.py &
sleep 5
curl -s http://localhost:8210/spaces/active | python3 -m json.tool
curl -s http://localhost:8210/spaces/sentiment | python3 -m json.tool
```

## RULES

- This is a STANDALONE service. Do NOT modify any files outside ~/protocol_pulse/spaces_scraper/
- Do NOT import from or depend on the Protocol Pulse Flask app
- Use Gemini (free) for sentiment analysis, not Claude (save API budget for articles)
- Whisper model stays loaded in GPU memory — do NOT reload on each segment
- Handle X blocking gracefully — rotate user agents, add delays, respect rate limits
- If Playwright approach fails (X blocks headless browsers), document what happened and try guest token approach
- Log everything to spaces_scraper.log
- `claude --dangerously-skip-permissions` in tmux (interactive only, no `-p` flag)
- When done: git add spaces_scraper/ && git commit && git push from main branch (no conflicts — new directory)
- Report: what approach worked for detection, Whisper performance stats, API endpoints live

## LEGAL NOTE

This scrapes publicly accessible audio streams. It's in a gray area with X's ToS.
- Do NOT store or redistribute raw audio — only transcripts and sentiment
- Do NOT impersonate users or create fake accounts
- Add rate limiting and respectful delays between checks
- Include a prominent disclaimer in README.md about intended use for research/analysis only
