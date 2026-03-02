# CLAUDE CODE PROMPT — PULSE CHECK V4: DUAL-HOST + REAL CLIPS + FULL EXTRAS

## CRITICAL CONTEXT

This task was attempted by a previous Claude Code session and **nothing was built**. The session read files for 13 minutes then committed only runtime logs. The existing video_pipeline_v3 files are UNCHANGED from their V3 state. This time you MUST produce actual code. Do not just explore — BUILD.

## CURRENT STATE

```bash
# Run these FIRST:
ls -la ~/protocol_pulse/video_pipeline_v3/*.py
wc -l ~/protocol_pulse/video_pipeline_v3/*.py
cat ~/protocol_pulse/video_pipeline_v3/config.yaml
head -30 ~/protocol_pulse/video_pipeline_v3/tts_engine.py
head -30 ~/protocol_pulse/video_pipeline_v3/script_writer.py
head -30 ~/protocol_pulse/video_pipeline_v3/assembler.py
head -30 ~/protocol_pulse/video_pipeline_v3/daily_producer.py
```

Existing V3 files:
- `assembler.py` — FFmpeg with xfade transitions
- `clip_fetcher.py` — Pexels stock footage (REPLACING THIS)
- `daily_producer.py` — Orchestrator with --test
- `tts_engine.py` — ElevenLabs Jessica voice, chunking
- `script_writer.py` — Claude API script generation (single narrator)
- `shorts_cutter.py` — Vertical shorts generation
- `relay.py` — Replit/Ultron relay helper
- `config.yaml` — Channel list, API config

## WHAT TO BUILD (5 NEW FILES + 3 MODIFIED FILES)

### NEW FILE 1: `dual_host_tts.py` — Two-Voice Dialogue Engine

```bash
# First, check available ElevenLabs voices:
curl -s "https://api.elevenlabs.io/v1/voices" \
  -H "xi-api-key: $(grep ELEVENLABS ~/protocol_pulse/.env 2>/dev/null | cut -d= -f2 || python3 -c 'from video_pipeline_v3.relay import get_key; print(get_key(\"ELEVENLABS_API_KEY\"))')" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
for v in d['voices'][:30]:
    g = v.get('labels',{}).get('gender','?')
    a = v.get('labels',{}).get('accent','?')
    print(f\"{v['voice_id']} | {v['name']} | {g} | {a}\")
"
```

Build a TTS engine that generates dialogue between two hosts:

```python
"""
dual_host_tts.py — Generate two-voice dialogue audio for Pulse Check V4

Usage:
    from dual_host_tts import generate_dialogue_audio
    
    dialogue = [
        {"host": 1, "text": "So Saylor just dropped another banger..."},
        {"host": 2, "text": "Dude, I saw that. Let's roll the clip."},
        {"host": "CLIP", "duration": 30},  # silence placeholder for clip
        {"host": 2, "text": "Ok here's what blows my mind about this..."},
        {"host": 1, "text": "Right, and if you think about it..."},
    ]
    
    result = generate_dialogue_audio(dialogue, output_dir="output/")
    # Returns: {
    #   "audio_path": "output/dialogue.wav",
    #   "timing_markers": [
    #     {"host": 1, "start_ms": 0, "end_ms": 2500, "text": "So Saylor..."},
    #     {"host": 2, "start_ms": 2800, "end_ms": 5200, "text": "Dude..."},
    #     {"host": "CLIP", "start_ms": 5500, "end_ms": 35500},
    #     ...
    #   ],
    #   "total_duration_ms": 45000
    # }
"""

# Host 1: Jessica (already configured) — cgSgspJ2msm6clMCkdW9
# Host 2: Pick a good male voice from the list above
# Gap between speakers: 300ms silence
# CLIP segments: insert silence of specified duration
# Concatenate all segments with pydub or ffmpeg
# Return timing markers so assembler knows when to show what
```

### NEW FILE 2: `visual_fetcher.py` — Real Visuals (Replaces Pexels)

```python
"""
visual_fetcher.py — Fetch REAL visuals instead of stock footage

Priority order:
1. YouTube clips — yt-dlp specific timestamp ranges
2. Article screenshots — playwright captures of PP articles
3. Tweet/Nostr screenshots — styled cards or real captures
4. Data charts — matplotlib BTC/mempool/hashrate charts
5. Pexels B-roll — LAST RESORT, transitions only (2-3s max)
"""

import subprocess
import os

def download_youtube_clip(video_id, start_sec, end_sec, output_path):
    """Download a specific segment of a YouTube video using yt-dlp."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    # yt-dlp with --download-sections for timestamp range
    cmd = [
        "yt-dlp",
        "--download-sections", f"*{start_sec}-{end_sec}",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", output_path,
        "--no-playlist",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return os.path.exists(output_path)

def screenshot_article(url, output_path):
    """Screenshot a web article using playwright."""
    # Use playwright to capture article headline + hero image area
    # Crop to 1920x1080 or aspect-appropriate
    # Apply dark vignette overlay for cinematic look
    pass

def screenshot_tweet(tweet_text, author, handle, output_path):
    """Generate a styled tweet card image."""
    # Use PIL/Pillow to render a dark-themed tweet card
    # Include: profile pic placeholder, author name, @handle, tweet text
    # Platform-colored accent (blue for X, purple for Nostr)
    pass

def generate_chart(chart_type, data, output_path):
    """Generate BTC/mempool/hashrate charts with matplotlib."""
    # chart_type: "price_7d", "mempool_fees", "hashrate_30d", "difficulty"
    # Dark background (#0a0a0f), green/red line, key price levels
    # Semi-transparent PNG overlay (1920x1080)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    pass

def fetch_pexels_broll(query, output_path, duration=3):
    """Last resort — short Pexels B-roll for transitions only."""
    # Existing pexels logic from clip_fetcher.py but limited to 3s clips
    pass
```

### NEW FILE 3: `thumbnail_gen.py` — Auto Episode Thumbnails

```python
"""
thumbnail_gen.py — Generate 1280x720 thumbnails for every episode

Layout:
- Left 60%: Main headline text (large, bold, white on dark gradient)
- Right 40%: Featured creator's channel avatar or article screenshot
- Bottom bar: "PULSE CHECK" branding + date + BTC price
- Color accent: red (#cc0000) urgency bar on left edge
"""

from PIL import Image, ImageDraw, ImageFont
import os

def generate_thumbnail(title, subtitle, date, btc_price, 
                       featured_image_path=None, output_path="thumbnail.jpg"):
    """
    Generate a professional 1280x720 thumbnail.
    
    Args:
        title: Main headline (e.g., "SAYLOR: $10M BITCOIN")
        subtitle: Secondary text (e.g., "+ Lyn Alden calls dollar crisis")
        date: Episode date string
        btc_price: Current BTC price string
        featured_image_path: Optional path to creator image/screenshot
        output_path: Where to save the thumbnail
    """
    WIDTH, HEIGHT = 1280, 720
    
    # Create dark gradient background
    img = Image.new('RGB', (WIDTH, HEIGHT), '#0a0a0f')
    draw = ImageDraw.Draw(img)
    
    # Red accent bar on left edge
    draw.rectangle([(0, 0), (6, HEIGHT)], fill='#cc0000')
    
    # Try to load a bold font, fall back to default
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
        sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        brand_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()
        brand_font = ImageFont.load_default()
    
    # Title text (left side, vertically centered)
    # Word-wrap title to fit in left 60%
    max_width = int(WIDTH * 0.55)
    # ... implement text wrapping and drawing
    
    # Featured image (right side)
    if featured_image_path and os.path.exists(featured_image_path):
        feat = Image.open(featured_image_path).resize((400, 400))
        img.paste(feat, (WIDTH - 440, 100))
    
    # Bottom branding bar
    draw.rectangle([(0, HEIGHT-60), (WIDTH, HEIGHT)], fill='#111116')
    draw.text((20, HEIGHT-48), f"PULSE CHECK  |  {date}  |  BTC {btc_price}", 
              fill='#888888', font=brand_font)
    
    img.save(output_path, 'JPEG', quality=95)
    return output_path
```

### NEW FILE 4: `chapters.py` — YouTube Chapter Markers

```python
"""
chapters.py — Generate YouTube chapter markers from script segments

Outputs:
1. chapters.txt — YouTube description format
2. FFmpeg chapter metadata (embedded in MP4)
"""

def generate_chapters_txt(segments, output_path="chapters.txt"):
    """Generate YouTube-format chapter markers."""
    lines = []
    for seg in segments:
        time_str = format_time(seg['start_seconds'])
        lines.append(f"{time_str} {seg['title']}")
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    return output_path

def generate_ffmpeg_metadata(segments, output_path="chapters_meta.txt"):
    """Generate FFmpeg chapter metadata file for embedding in MP4."""
    lines = [";FFMETADATA1"]
    for seg in segments:
        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={seg['start_seconds'] * 1000}")
        lines.append(f"END={seg['end_seconds'] * 1000}")
        lines.append(f"title={seg['title']}")
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    return output_path

def format_time(seconds):
    """Convert seconds to MM:SS or H:MM:SS format."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
```

### NEW FILE 5: `podcast_feed.py` — RSS Audio Podcast Feed

```python
"""
podcast_feed.py — Generate iTunes-compatible RSS podcast feed

After each episode:
1. Extract audio-only: ffmpeg -i episode.mp4 -vn -c:a libmp3lame -q:a 2 episode.mp3
2. Update RSS feed XML
3. Serve from static directory
"""

def extract_audio(video_path, audio_path):
    """Extract audio track from video as MP3."""
    import subprocess
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-c:a", "libmp3lame", "-q:a", "2",
        "-y", audio_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return audio_path

def update_feed(episode_data, feed_path="podcast_feed/feed.xml"):
    """Add new episode to RSS feed XML."""
    # iTunes-compatible RSS feed
    # Fields: title, pubDate, enclosure (MP3 URL), duration, description
    # Use feedgen library if available, otherwise raw XML
    pass

def generate_full_feed(episodes, feed_path="podcast_feed/feed.xml"):
    """Generate complete RSS feed from episode list."""
    pass
```

### MODIFY: `script_writer.py` — Dual-Host Conversation Script

Update the Claude API prompt to generate a two-host conversation instead of single narrator:

```python
SCRIPT_PROMPT = """You are writing a script for "Pulse Check" — a daily Bitcoin highlight reel with two hosts having a casual conversation.

HOST 1 (JESSICA): The anchor. Warm, knowledgeable, keeps the flow.
HOST 2 (ANALYST): The co-host. Enthusiastic, adds sharp context, occasionally pushes back.

STYLE: Casual Joe Rogan banter. Two friends obsessed with Bitcoin talking about the day's best content. They interrupt each other, get excited, laugh. NOT a news broadcast.

EXAMPLE:
Host 1: "So Michael Saylor just dropped another absolute banger on his channel—"
Host 2: "Dude, I saw that. The man is literally unstoppable."
Host 1: "Let's roll the clip and then break it down..."
[CLIP PLAYS]
Host 2: "Ok so here's what's wild about what he just said..."

Given today's top clips and data:
{clips_data}

BTC: {btc_price} ({btc_change})  |  F&G: {fng}

Generate JSON:
{{
  "title": "Pulse Check — {date}",
  "segments": [
    {{
      "type": "clip_react",
      "source_channel": "channel name",
      "source_video_id": "youtube_id",
      "clip_start": 145,
      "clip_end": 175,
      "dialogue": [
        {{"host": 1, "text": "..."}},
        {{"host": 2, "text": "..."}},
        {{"host": "CLIP", "duration": 30}},
        {{"host": 2, "text": "..."}},
        {{"host": 1, "text": "..."}}
      ],
      "overlay_text": "SAYLOR: BTC $10M TARGET"
    }}
  ],
  "cold_open": {{"host": 1, "text": "Three clips you need to see today..."}},
  "outro": {{"host": 1, "text": "That's your Pulse Check. Stay sovereign."}},
  "chapters": [
    {{"time": "0:00", "title": "Intro"}},
    {{"time": "0:15", "title": "Saylor's $10M Target"}}
  ],
  "thumbnail": {{
    "headline": "SAYLOR: $10M BITCOIN",
    "subtext": "+ Lyn Alden on dollar crisis"
  }}
}}"""
```

### MODIFY: `assembler.py` — Composite Real Clips + Dialogue

Update to handle:
- Dialogue sections: show host name labels + waveform overlay during conversation
- Clip sections: show actual YouTube clip full-screen with source attribution overlay
- Transitions: smooth crossfade between clips and commentary
- Lower-third ticker: "PROTOCOL PULSE | PULSE CHECK | BTC $XX,XXX"
- Embed chapter metadata in final MP4

### MODIFY: `daily_producer.py` — Updated Orchestration

New flow:
```
1. GATHER — yt-dlp check all channels for new videos (last 24h)
2. TRANSCRIBE — Whisper on GPU (existing transcriber)
3. SELECT — Claude picks top 3 clips from transcripts
4. DOWNLOAD — yt-dlp download specific clip segments (visual_fetcher.py)
5. SCREENSHOTS — Capture article/tweet screenshots (visual_fetcher.py)
6. SCRIPT — Claude generates dual-host conversation (script_writer.py)
7. TTS — Generate two-voice dialogue audio (dual_host_tts.py)
8. ASSEMBLE — Composite everything (assembler.py)
9. SHORTS — Generate 3 vertical shorts (shorts_cutter.py)
10. THUMBNAIL — Generate 1280x720 (thumbnail_gen.py)
11. CHAPTERS — Generate chapter markers (chapters.py)
12. PODCAST — Extract audio + update RSS (podcast_feed.py)
13. OUTPUT — Everything to output/YYYY-MM-DD/
```

## DEPENDENCIES

```bash
# Check and install:
which yt-dlp || pip install yt-dlp --break-system-packages
which playwright || pip install playwright --break-system-packages && playwright install chromium
python3 -c "from PIL import Image; print('Pillow OK')" || pip install Pillow --break-system-packages
python3 -c "from feedgen.feed import FeedGenerator; print('feedgen OK')" || pip install feedgen --break-system-packages
```

## TEST RUN

```bash
cd ~/protocol_pulse/video_pipeline_v3
python3 daily_producer.py --test
```

Test mode should:
- Use 1-2 clips only
- Generate ~60-90s episode
- Produce ALL output files

Expected output:
```
output/test_YYYYMMDD_HHMMSS/
├── pulse_check_YYYYMMDD.mp4    (dual-host audio, real clips)
├── short_1.mp4
├── short_2.mp4
├── short_3.mp4
├── thumbnail.jpg               (1280x720)
├── chapters.txt                (YouTube format)
├── pulse_check_audio.mp3       (podcast audio)
├── script.json
└── clips/                      (downloaded YouTube segments)
```

## VERIFICATION

Run these BEFORE committing:
```bash
# 1. Count new/modified files
ls -la ~/protocol_pulse/video_pipeline_v3/*.py | wc -l
# Should be 12+ (9 existing + 5 new, some existing modified)

# 2. Check new files exist
ls ~/protocol_pulse/video_pipeline_v3/dual_host_tts.py
ls ~/protocol_pulse/video_pipeline_v3/visual_fetcher.py
ls ~/protocol_pulse/video_pipeline_v3/thumbnail_gen.py
ls ~/protocol_pulse/video_pipeline_v3/chapters.py
ls ~/protocol_pulse/video_pipeline_v3/podcast_feed.py

# 3. Import test
cd ~/protocol_pulse
python3 -c "from video_pipeline_v3.dual_host_tts import generate_dialogue_audio; print('OK')"
python3 -c "from video_pipeline_v3.thumbnail_gen import generate_thumbnail; print('OK')"
python3 -c "from video_pipeline_v3.chapters import generate_chapters_txt; print('OK')"

# 4. Run test (this is the real verification)
cd ~/protocol_pulse/video_pipeline_v3 && python3 daily_producer.py --test
```

## SUCCESS CRITERIA

Before committing, ALL of these must be true:
- [ ] 5 new .py files created in video_pipeline_v3/
- [ ] script_writer.py updated with dual-host prompt
- [ ] assembler.py handles clip + dialogue compositing
- [ ] daily_producer.py orchestrates the full new pipeline
- [ ] --test produces at least: MP4 + thumbnail + chapters.txt
- [ ] Audio has TWO distinct voices (verify by listening or checking TTS calls)

## RULES
- Work on `main` branch
- All new files in `~/protocol_pulse/video_pipeline_v3/`
- Two ElevenLabs voices — verify both work
- yt-dlp clips cached in `downloads/yt_cache/`
- matplotlib: `Agg` backend (no GUI)
- playwright: headless only
- git add + commit + push when done
- DO NOT just read files and quit. BUILD CODE.
