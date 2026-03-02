# CLAUDE CODE PROMPT — ORACLE BRIEFING: BUILD FROM SCRATCH

## CRITICAL CONTEXT

This task was attempted by a previous Claude Code session and **the directory doesn't even exist**. Nothing was built. This time you MUST create `~/protocol_pulse/oracle_briefing/` and all files within it. Do not just explore — BUILD.

## WHAT IS AN ORACLE BRIEFING

A 60-90 second daily intelligence video where the Proto_P Oracle avatar delivers a punchy, authoritative Bitcoin market brief. Three segments:

1. **THE NUMBER** — One key metric with context (15-20s)
2. **THE SIGNAL** — Most important development (20-25s)  
3. **THE TAKE** — Protocol Pulse editorial opinion (20-25s)

The avatar speaks over data visualizations (charts, article screenshots, stats overlays).

## EXISTING INFRASTRUCTURE

```bash
# Avatar server (running):
curl -s http://localhost:8200/health 2>/dev/null || echo "Check avatar tmux"
# Avatar generates lip-synced video from text+audio

# Protocol Pulse APIs:
curl -s https://protocolpulse.replit.app/api/articles/latest 2>/dev/null | python3 -m json.tool | head -20

# Live data APIs:
curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true" 2>/dev/null
curl -s "https://mempool.space/api/v1/fees/recommended" 2>/dev/null
curl -s "https://mempool.space/api/v1/mining/hashrate/1w" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Hashrate: {d[\"currentHashrate\"]/1e18:.1f} EH/s')" 2>/dev/null
curl -s "https://api.alternative.me/fng/" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data'][0])" 2>/dev/null
```

## FILES TO CREATE

All in `~/protocol_pulse/oracle_briefing/`:

### 1. `data_gatherer.py` (~150 lines)

Fetch all live data needed for the briefing:

```python
"""Gather live Bitcoin data for Oracle Briefing."""
import requests
import json
from datetime import datetime

def gather_all():
    """Fetch all data sources, return structured dict."""
    data = {}
    
    # BTC price + 24h change
    data['btc'] = fetch_btc_price()
    
    # Mempool: fees, unconfirmed tx count
    data['mempool'] = fetch_mempool()
    
    # Hashrate + difficulty
    data['mining'] = fetch_mining()
    
    # Fear & Greed Index
    data['fng'] = fetch_fear_greed()
    
    # Latest Protocol Pulse articles (top 5)
    data['articles'] = fetch_latest_articles()
    
    # Block height
    data['block_height'] = fetch_block_height()
    
    data['timestamp'] = datetime.now().isoformat()
    return data

def fetch_btc_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                         params={"ids": "bitcoin", "vs_currencies": "usd", 
                                 "include_24hr_change": "true"}, timeout=10)
        d = r.json()['bitcoin']
        return {"price": d['usd'], "change_24h": d.get('usd_24h_change', 0)}
    except Exception as e:
        return {"price": 0, "change_24h": 0, "error": str(e)}

# ... implement all fetch functions with error handling
# Each function should return data or {"error": "message"}
# Never crash on API failure — use fallback values
```

### 2. `briefing_writer.py` (~200 lines)

Generate the Oracle script via Claude API:

```python
"""Generate Oracle Briefing script using Claude API."""
import anthropic
import json
import os

BRIEFING_PROMPT = """You are the Protocol Pulse Oracle — an AI intelligence system monitoring the Bitcoin network 24/7. You speak with authority, precision, and dry wit. You are NOT a news anchor. You are a sovereign intelligence asset delivering classified-level signal.

VOICE RULES:
- Short sentences. Punchy. Rhetorical questions allowed.
- NEVER: "Today we're going to look at..." or "Let's discuss..."
- ALWAYS: "The network just told us something." or "Ninety-seven thousand. That's where we are."
- Sound like a brilliant analyst briefing insiders, not a YouTuber.

DATA:
BTC: ${btc_price} ({btc_change})
Mempool: {mempool_size} unconfirmed, {fee_rate} sat/vB
Hashrate: {hashrate} EH/s
Block: {block_height}
Fear & Greed: {fng_value} ({fng_label})
Difficulty: {difficulty_change}

Recent articles:
{articles}

Generate JSON:
{{
  "title": "Oracle Briefing — {date}",
  "hook": "One sentence that makes people stop scrolling",
  "segments": [
    {{
      "label": "THE NUMBER",
      "narration": "45 words MAX. One key metric with sharp context.",
      "overlay_type": "price_chart|mempool|hashrate|article|stat_card",
      "overlay_data": {{"metric": "...", "value": "..."}}
    }},
    {{
      "label": "THE SIGNAL",
      "narration": "50 words MAX. Most important development.",
      "overlay_type": "...",
      "overlay_data": {{}}
    }},
    {{
      "label": "THE TAKE",
      "narration": "50 words MAX. What nobody else is saying. Opinionated.",
      "overlay_type": "...",
      "overlay_data": {{}}
    }}
  ],
  "signoff": "That's your Oracle Briefing. [custom closing]",
  "thumbnail": {{
    "headline": "5 words max",
    "metric": "$XX,XXX"
  }}
}}
"""

def generate_script(data):
    """Generate Oracle Briefing script from gathered data."""
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY') or _get_key())
    
    prompt = BRIEFING_PROMPT.format(
        btc_price=f"${data['btc']['price']:,.0f}",
        btc_change=f"{data['btc']['change_24h']:+.1f}%",
        mempool_size=data['mempool'].get('count', '?'),
        fee_rate=data['mempool'].get('fastest_fee', '?'),
        hashrate=data['mining'].get('hashrate', '?'),
        block_height=data.get('block_height', '?'),
        fng_value=data['fng'].get('value', '?'),
        fng_label=data['fng'].get('classification', '?'),
        difficulty_change=data['mining'].get('difficulty_change', '?'),
        articles=_format_articles(data.get('articles', [])),
        date=data['timestamp'][:10]
    )
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = response.content[0].text
    # Parse JSON from response
    text = text.strip().replace('```json', '').replace('```', '').strip()
    return json.loads(text)
```

### 3. `overlay_engine.py` (~250 lines)

Generate data visualization overlays for compositing onto avatar video:

```python
"""Generate data overlays for Oracle Briefing video."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def generate_overlay(overlay_type, overlay_data, output_path):
    """Generate a 1920x1080 semi-transparent overlay image."""
    if overlay_type == "price_chart":
        return _price_chart(overlay_data, output_path)
    elif overlay_type == "mempool":
        return _mempool_viz(overlay_data, output_path)
    elif overlay_type == "hashrate":
        return _hashrate_chart(overlay_data, output_path)
    elif overlay_type == "stat_card":
        return _stat_card(overlay_data, output_path)
    elif overlay_type == "article":
        return _article_screenshot(overlay_data, output_path)
    else:
        return _stat_card(overlay_data, output_path)

def _price_chart(data, output_path):
    """7-day BTC price chart, dark theme."""
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor('#0a0a0f')
    ax.set_facecolor('#0a0a0f')
    # ... dark themed chart with green/red line
    # Save as semi-transparent PNG
    fig.savefig(output_path, transparent=True, bbox_inches='tight', pad_inches=0)
    plt.close()
    return output_path

def _stat_card(data, output_path):
    """Large metric display card."""
    img = Image.new('RGBA', (1920, 1080), (10, 10, 15, 200))
    draw = ImageDraw.Draw(img)
    # Big number in center, label above, context below
    # Use Protocol Pulse styling: dark bg, white text, red accents
    img.save(output_path)
    return output_path

# ... implement all overlay types
```

### 4. `briefing_producer.py` (~300 lines) — Main Orchestrator

```python
"""
Oracle Briefing Producer — Orchestrates the full pipeline.

Usage:
    python3 briefing_producer.py          # Production run
    python3 briefing_producer.py --test   # Test with cached data
"""

import argparse
import os
import sys
import time
import json
import subprocess
from datetime import datetime

from data_gatherer import gather_all
from briefing_writer import generate_script
from overlay_engine import generate_overlay

def produce_briefing(test=False):
    start = time.time()
    date_str = datetime.now().strftime('%Y%m%d')
    
    if test:
        output_dir = f"output/test_oracle_{date_str}_{int(time.time())}"
    else:
        output_dir = f"output/oracle_{date_str}"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[1/7] Gathering data...")
    data = gather_all()
    with open(f"{output_dir}/data.json", 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"[2/7] Generating script...")
    script = generate_script(data)
    with open(f"{output_dir}/script.json", 'w') as f:
        json.dump(script, f, indent=2)
    
    print(f"[3/7] Generating TTS audio...")
    full_narration = build_narration(script)
    audio_path = generate_tts(full_narration, f"{output_dir}/narration.wav")
    
    print(f"[4/7] Generating avatar video...")
    avatar_path = generate_avatar(audio_path, f"{output_dir}/avatar_raw.mp4")
    
    print(f"[5/7] Generating overlays...")
    overlay_paths = []
    for i, seg in enumerate(script['segments']):
        path = f"{output_dir}/overlay_{i}.png"
        generate_overlay(seg['overlay_type'], seg.get('overlay_data', {}), path)
        overlay_paths.append(path)
    
    print(f"[6/7] Compositing final video...")
    final_path = composite_video(avatar_path, overlay_paths, script, 
                                 f"{output_dir}/oracle_briefing_{date_str}.mp4")
    
    print(f"[7/7] Generating thumbnail...")
    from thumbnail_gen import generate_briefing_thumbnail
    generate_briefing_thumbnail(script, f"{output_dir}/thumbnail.jpg")
    
    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.0f}s")
    print(f"Output: {output_dir}/")
    
    # List all output files
    for f in sorted(os.listdir(output_dir)):
        size = os.path.getsize(f"{output_dir}/{f}")
        print(f"  {f} ({size:,} bytes)")

def build_narration(script):
    """Concatenate all segment narrations with pauses."""
    parts = [script.get('hook', '')]
    for seg in script['segments']:
        parts.append(seg['narration'])
    parts.append(script.get('signoff', ''))
    return ' ... '.join(parts)  # ... = pause marker

def generate_tts(text, output_path):
    """Generate TTS audio using ElevenLabs Jessica voice."""
    import requests
    api_key = os.environ.get('ELEVENLABS_API_KEY') or _get_key('ELEVENLABS_API_KEY')
    voice_id = "cgSgspJ2msm6clMCkdW9"  # Jessica
    
    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={"text": text, "model_id": "eleven_turbo_v2_5",
              "voice_settings": {"stability": 0.6, "similarity_boost": 0.85}},
        timeout=60
    )
    with open(output_path, 'wb') as f:
        f.write(resp.content)
    return output_path

def generate_avatar(audio_path, output_path):
    """Send audio to avatar server for lip-synced video."""
    import requests
    # POST audio to avatar server
    # The avatar server at localhost:8200 should accept audio and return video
    # Check the actual endpoint format:
    # curl http://localhost:8200/health
    pass

def composite_video(avatar_path, overlay_paths, script, output_path):
    """Composite avatar video with data overlays using FFmpeg."""
    # Layout: Avatar on left (40%), overlay on right (60%)
    # Or: Avatar full-screen with semi-transparent overlay
    # Add intro (2s) and outro (3s)
    # Use FFmpeg filter_complex for compositing
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    produce_briefing(test=args.test)
```

### 5. `thumbnail_gen.py` (~80 lines) — Oracle-specific thumbnails

Similar to Pulse Check but Oracle-branded:
- Proto_P avatar face on left
- Headline + metric on right
- "ORACLE BRIEFING" branding

## TEST RUN

```bash
mkdir -p ~/protocol_pulse/oracle_briefing/output
cd ~/protocol_pulse/oracle_briefing
python3 briefing_producer.py --test
```

Expected output:
```
output/test_oracle_YYYYMMDD_XXXX/
├── oracle_briefing_YYYYMMDD.mp4  (60-90s, avatar + overlays)
├── thumbnail.jpg                 (1280x720)
├── script.json
├── data.json
├── narration.wav
├── avatar_raw.mp4
├── overlay_0.png
├── overlay_1.png
├── overlay_2.png
└── timing_report.txt
```

## VERIFICATION

```bash
# Files exist:
ls ~/protocol_pulse/oracle_briefing/*.py | wc -l  # Should be 5
# Imports work:
cd ~/protocol_pulse/oracle_briefing
python3 -c "from data_gatherer import gather_all; d=gather_all(); print(f'BTC: ${d[\"btc\"][\"price\"]:,.0f}')"
python3 -c "from overlay_engine import generate_overlay; print('OK')"
# Test run produces output:
python3 briefing_producer.py --test
ls -la output/test_oracle_*/
```

## SUCCESS CRITERIA
- [ ] 5 .py files created in `~/protocol_pulse/oracle_briefing/`
- [ ] `data_gatherer.py` fetches live BTC, mempool, hashrate, FNG data
- [ ] `briefing_writer.py` generates script via Claude API
- [ ] `overlay_engine.py` generates at least stat_card overlays
- [ ] `briefing_producer.py --test` runs without crashing
- [ ] At least script.json + data.json produced in test output

## RULES
- Work on `main` branch
- Create the `oracle_briefing/` directory from scratch
- All API calls have timeout and error handling
- matplotlib: Agg backend
- Git add + commit + push when done
- DO NOT just explore and quit. CREATE ALL 5 FILES.
