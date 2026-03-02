# CLAUDE CODE PROMPT — PULSE CHECK V4: HIGHLIGHT REEL + DUAL-HOST COMMENTARY

## MISSION

Transform the Pulse Check from a generic news recap with stock footage into a **highlight reel of the best Bitcoin content from the last 24 hours** with casual, Joe Rogan-style dual-host commentary reacting to the clips. Think NotebookLM's podcast feature but for Bitcoin video content.

## WHAT EXISTS (V3 — already working)

Location: `~/protocol_pulse/video_pipeline_v3/`
- `daily_producer.py` — orchestrates full pipeline with --test flag
- `tts_engine.py` — ElevenLabs Jessica voice, chunking, retry
- `clip_fetcher.py` — Pexels stock footage (WE ARE REPLACING THIS)
- `assembler.py` — FFmpeg with xfade transitions
- `script_writer.py` — Claude API script generation
- `transcriber.py` — Whisper transcription
- Branch: now merged to main, commit 743e17f

V3 produces: 1920×1080 main video + 3 vertical shorts with Jessica narration over Pexels stock footage.

## WHAT'S WRONG WITH V3

1. **Generic stock footage** — cheap-looking Pexels clips of "finance" and "technology"
2. **Single narrator** — feels like a corporate training video
3. **News recap only** — reads headlines instead of reacting to actual content
4. **No real clips** — doesn't show the actual YouTube content being discussed
5. **No article visuals** — mentions articles but never shows them

## THE NEW FORMAT: PULSE CHECK V4

### Structure of each episode (~3-5 minutes):

```
[0:00] COLD OPEN — 5-second highlight montage with Protocol Pulse branding
[0:05] INTRO — "Welcome to Pulse Check, your daily Bitcoin highlight reel"

[0:15] SEGMENT 1 — React to YouTube clip #1
  - Show 15-30s of the actual YouTube clip (fair use commentary)
  - Cut to dual-host commentary reacting to it (30-45s)
  - Article screenshot overlay if referencing a PP article

[1:30] SEGMENT 2 — React to YouTube clip #2
  - Same format

[2:45] SEGMENT 3 — React to YouTube clip or major news
  - Can be a tweet/Nostr note screenshot if no good clip

[3:45] WRAP — Quick takes on BTC price + sentiment
[4:00] OUTRO — "Stay sovereign. That's your Pulse Check."
```

### Dual-Host Voices

**Host 1 (Jessica):** The anchor. Introduces segments, asks questions, keeps flow.
- ElevenLabs voice ID: `cgSgspJ2msm6clMCkdW9` (already configured)

**Host 2 (Co-host):** The analyst. Reacts, adds context, occasionally pushes back.
- Pick a male ElevenLabs voice. Check what's available:
```bash
curl -s "https://api.elevenlabs.io/v1/voices" -H "xi-api-key: $(python3 -c 'from relay import get_key; print(get_key(\"ELEVENLABS_API_KEY\"))')" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for v in d['voices'][:30]:
    print(f\"{v['voice_id']} | {v['name']} | {v.get('labels',{}).get('gender','?')} | {v.get('labels',{}).get('accent','?')}\")
"
```
- Pick a natural-sounding male voice with American accent
- If none available, use `pNInz6obpgDQGcFmaJgB` (Adam — default male)

**Conversation style: Casual Joe Rogan banter**
- Host 1: "So Michael Saylor just dropped another absolute banger on his channel—"
- Host 2: "Dude, I saw that. The man is literally unstoppable. What was it, like his fifth video this week?"
- Host 1: "Let's roll the clip and then break it down..."
- [clip plays]
- Host 2: "Ok so here's what's wild about what he just said..."

The script writer prompt must generate this conversational back-and-forth, NOT formal news anchor style.

### Visual Layer (REPLACING PEXELS)

**Priority order for visuals (use the FIRST that applies):**

1. **Actual YouTube clips** — Download the segment being discussed
   - Use `yt-dlp` to grab the specific timestamp range
   - `yt-dlp --download-sections "*START-END" -f "bestvideo[height<=1080]+bestaudio" URL`
   - Overlay "Source: @ChannelName" attribution in bottom-right

2. **Article screenshots** — For Protocol Pulse articles or external articles
   - Use `playwright` or `cutycapt` to screenshot the article
   - Crop to the headline + hero image area
   - Apply Ken Burns slow zoom + dark vignette overlay
   - `playwright screenshot --full-page URL`

3. **Tweet/post screenshots** — For X or Nostr content
   - Screenshot the tweet using playwright
   - Or generate a styled card with the quote text + profile pic
   - Apply same Ken Burns treatment

4. **Data overlays** — For price/market segments
   - Pull BTC chart image from TradingView or generate with matplotlib
   - Overlay current price, 24h change, key levels

5. **Pexels B-roll** — LAST RESORT ONLY for transitions between segments
   - 2-3 second transitional clips max
   - Only for moments where no specific visual exists

### YouTube Channel Monitoring

The video pipeline already monitors these channels (from `clip_fetcher.py` / `transcriber.py`):
```bash
# Check what channels are configured
cat ~/protocol_pulse/video_pipeline_v3/config.yaml | grep -A 50 channel
# Also check if there's a channels list elsewhere
find ~/protocol_pulse/video_pipeline_v3/ -name "*.py" -exec grep -l "youtube\|channel" {} \;
```

Target channels for highlight clips:
- Michael Saylor, Robert Breedlove, Natalie Brunell
- Bitcoin Magazine, Simply Bitcoin, Swan Bitcoin
- Preston Pysh, Peter McCormack, Lyn Alden
- Pomp (Anthony Pompliano), Marty Bent
- The Bitcoin Layer, What Bitcoin Did

For each channel:
1. Check for videos published in last 24 hours
2. Download and Whisper-transcribe them
3. Extract the most insightful/provocative 30-60 second segments
4. Feed transcripts to Claude to pick the top 3 clips for the episode

### Script Generation (Claude API)

Rewrite `script_writer.py` to generate a dual-host conversation:

```python
SCRIPT_PROMPT = """You are writing a script for "Pulse Check" — a daily Bitcoin highlight reel with two hosts.

HOST 1 (JESSICA): The anchor. Warm, knowledgeable, keeps the flow. Think Bloomberg anchor meets podcast host.
HOST 2 (ANALYST): The co-host. Enthusiastic, adds context, pushes back sometimes. Think Joe Rogan's curiosity meets a sharp trader.

STYLE: Casual banter. They're two friends who are obsessed with Bitcoin talking about the day's best content. NOT a news broadcast. NOT formal. They interrupt each other, laugh, get excited.

Here are today's top clips and articles:
{clips_data}

Current BTC price: {btc_price}
24h change: {btc_change}
Fear & Greed: {fng}

Generate a script with this EXACT JSON structure:
{
  "title": "Pulse Check — {date}",
  "segments": [
    {
      "type": "clip_react",
      "source_channel": "Michael Saylor",
      "source_video_id": "abc123",
      "clip_start": 145,
      "clip_end": 175,
      "clip_context": "Brief description of what happens in the clip",
      "dialogue": [
        {"host": 1, "text": "So Saylor just posted this incredible breakdown..."},
        {"host": 2, "text": "Roll the clip, let's hear it."},
        {"host": "CLIP", "text": "[CLIP PLAYS — 30 seconds]"},
        {"host": 2, "text": "Ok so here's what blows my mind about this..."},
        {"host": 1, "text": "Right, and if you think about it..."}
      ],
      "overlay_text": "SAYLOR: BTC $10M TARGET",
      "duration_target": 75
    }
  ],
  "cold_open": {"host": 1, "text": "Three clips you need to see today..."},
  "outro": {"host": 1, "text": "That's your Pulse Check. Stay sovereign."},
  "chapters": [
    {"time": "0:00", "title": "Intro"},
    {"time": "0:15", "title": "Saylor's $10M Bitcoin Target"},
    {"time": "1:30", "title": "Lyn Alden on the Dollar Crisis"}
  ],
  "thumbnail": {
    "headline": "SAYLOR: $10M BITCOIN",
    "subtext": "+ Lyn Alden calls dollar crisis",
    "style": "urgent"
  }
}
"""
```

### TTS Engine Updates

Update `tts_engine.py`:
- Add `generate_dialogue_audio(dialogue_list, output_dir)` function
- For each dialogue turn:
  - host=1 → Jessica voice
  - host=2 → Co-host voice (the male voice you selected)
  - host="CLIP" → skip (clip audio plays here)
- Concatenate all audio turns with 0.3s silence gaps between speakers
- Add subtle audio processing: slight compression, normalize loudness
- Return timing markers so the assembler knows when each turn starts/ends

### Assembler Updates

Update `assembler.py`:
- During dialogue sections: show a stylized "studio" overlay
  - Dark background with subtle animated waveform
  - Host name labels that highlight when speaking ("JESSICA" / "ANALYST")
  - Or: show relevant article screenshot / chart behind the dialogue
- During clip sections: show the actual YouTube clip full-screen with attribution
- Transitions: smooth crossfade between clips and commentary
- Lower-third persistent ticker: "PROTOCOL PULSE | PULSE CHECK | BTC $XX,XXX"

### NEW: Auto-Thumbnail Generation

Create `thumbnail_gen.py`:
- Generate a 1280×720 thumbnail for every episode
- Layout:
  - Left: Main headline text (large, bold, white on dark)
  - Right: Screenshot or face of the featured creator
  - Bottom: "PULSE CHECK" branding + date
  - Color accent: red (#cc0000) urgency bar
- Use PIL/Pillow for image generation
- Input: thumbnail data from script JSON
- Output: `output/YYYY-MM-DD/thumbnail.jpg`

### NEW: YouTube Chapter Markers

Create `chapters.py`:
- Read chapter data from script JSON
- Output two formats:
  1. `chapters.txt` — YouTube description format:
     ```
     0:00 Intro
     0:15 Saylor's $10M Bitcoin Target  
     1:30 Lyn Alden on the Dollar Crisis
     ```
  2. FFmpeg chapter metadata embedded in the MP4

### NEW: Newsletter Embed

Create `newsletter_embed.py`:
- After episode is produced, generate an HTML email snippet
- Includes: thumbnail image, title, brief description, "Watch Now" button linking to YouTube
- Calls the Resend API to send to subscriber list
- Check for Resend config:
```bash
grep -r "RESEND\|SENDGRID\|newsletter" ~/protocol_pulse/.env ~/protocol_pulse/config*.py 2>/dev/null
```

### NEW: RSS Audio Podcast Feed

Create `podcast_feed.py`:
- Extract audio-only track from the episode: `ffmpeg -i episode.mp4 -vn -c:a libmp3lame -q:a 2 episode.mp3`
- Generate/update an RSS XML feed at `~/protocol_pulse/podcast_feed/feed.xml`
- Feed format: standard iTunes podcast RSS
- Each entry: title, date, duration, MP3 enclosure URL
- The MP3 files get served from a static directory on Replit

## UPDATED DAILY PRODUCER

`daily_producer.py` orchestration flow:

```
1. GATHER — Check all monitored YouTube channels for new videos (yt-dlp)
2. TRANSCRIBE — Whisper transcribe new videos on RTX 4090
3. SELECT — Claude picks top 3 clips from transcripts
4. DOWNLOAD — yt-dlp download the specific clip segments
5. SCREENSHOT — Playwright captures article/tweet screenshots
6. SCRIPT — Claude generates dual-host conversation script
7. TTS — ElevenLabs generates Host 1 + Host 2 audio
8. ASSEMBLE — FFmpeg composites clips + commentary + overlays
9. SHORTS — Generate 3 vertical shorts from best segments
10. THUMBNAIL — Generate 1280×720 thumbnail
11. CHAPTERS — Generate YouTube chapter file
12. PODCAST — Extract audio, update RSS feed
13. NEWSLETTER — Generate email embed (optional, triggered separately)
14. OUTPUT — Everything to output/YYYY-MM-DD/
```

## DEPENDENCIES

```bash
# Check what's already installed
which yt-dlp playwright ffmpeg ffprobe

# Install missing
pip install yt-dlp playwright Pillow feedgen
playwright install chromium
```

## TEST RUN

```bash
python3 daily_producer.py --test
```

Test mode:
- Only process 1-2 clips (not all channels)
- Generate shorter episode (~90s)
- Skip newsletter send
- Output to `output/test_YYYYMMDD_HHMMSS/`

Expected output:
```
output/test_20260302_XXXXXX/
├── pulse_check_20260302.mp4      (1080p, ~90s, dual-host)
├── short_1.mp4                   (1080×1920 vertical)
├── short_2.mp4
├── short_3.mp4
├── thumbnail.jpg                 (1280×720)
├── chapters.txt                  (YouTube chapter markers)
├── pulse_check_audio.mp3         (podcast audio)
├── script.json                   (full dialogue script)
├── timing_report.txt
└── clips/                        (downloaded YouTube segments)
```

## VERIFICATION

1. Play main video — should hear TWO distinct voices having a conversation
2. Visuals — should see actual YouTube clips, NOT stock footage
3. Thumbnail — should be a professional 1280×720 image
4. Chapters — should have timestamped segments
5. Audio MP3 — should play independently as podcast
6. Script JSON — should have `dialogue` arrays with host turns

## RULES

- Work on `main` branch
- `claude --dangerously-skip-permissions` in tmux (interactive only, no `-p`)
- yt-dlp downloads go in `downloads/yt_cache/` — cache aggressively
- Whisper model stays loaded in GPU memory between transcriptions
- Fair use: clips must be under 60 seconds each, with commentary
- Always attribute sources with on-screen overlay
- Two ElevenLabs voices — verify both work before full pipeline run
- Git commit + push when done
- Report: voice IDs used, clip sources, timing breakdown, file list
