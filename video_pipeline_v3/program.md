# PROTOCOL PULSE — AUTORESEARCH PROGRAM v3
# Based on cross-LLM audit consensus (GPT-4o + Grok + Gemini, Aug 10 2026)
# This is the DEFINITIVE fix list. No more band-aids.

## NORTH STAR
FFmpeg should COMPOSITE and ENCODE visual content. It should NEVER GENERATE it.
Python constructs manifests and commands. FFmpeg executes them. GPU stays in the loop.
No frame-by-frame PIL rendering. No per-pixel math. No MoviePy in production.

---

## PHASE 1: RENDER ARCHITECTURE (P0 — do first, everything else depends on this)

### 1A: Kill geq — replace with pre-rendered background loops
READ: video_pipeline_v3/render_narrator.py, render_social.py, render_data.py
FIND: every call to _build_black_diamond_bg or any function using geq filter
REPLACE WITH:
```python
# Use pre-rendered loop instead of geq
bg_args = ["-stream_loop", "-1", "-i", BG_LOOP_PATH, "-t", str(duration)]
```
Where BG_LOOP_PATH = "assets/backgrounds/bg_loop.mp4"
If bg_loop.mp4 doesn't exist, generate a simple one ONCE:
```bash
ffmpeg -y -f lavfi -i "color=c=0x0A0A0A:s=1920x1080:d=10:r=30" \
  -vf "drawbox=x=0:y=0:w=1920:h=1080:c=0x141414@0.3:t=fill" \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p \
  assets/backgrounds/bg_loop.mp4
```
VERIFY: grep -rn "geq" video_pipeline_v3/*.py returns ZERO results
SUCCESS: render_narrator no longer times out on background generation

### 1B: Kill MoviePy from production path
READ: every .py file that imports moviepy
REPLACE: all MoviePy compositing with ffmpeg subprocess calls
RULE: MoviePy may only be used for duration queries (clip.duration), never for rendering
VERIFY: no moviepy TextClip, CompositeVideoClip, or write_videofile in render path

### 1C: Wire full NVENC pipeline
IN: video_pipeline_v3/assembler_common.py
ADD to run_ffmpeg and run_ffmpeg_filtergraph:
```
For decode: -hwaccel cuda -hwaccel_output_format cuda
For encode: -c:v h264_nvenc -preset p5 -tune hq -rc vbr -cq 19 -b:v 0
```
NOTE: On this ffmpeg build, -rc takes integers not strings. Test with:
  ffmpeg -h encoder=h264_nvenc | grep rc
Use overlay_cuda where possible, but DON'T force it — CPU overlay is fine for
pre-rendered PNG assets. Mixed CPU/GPU graph is acceptable.
VERIFY: ffmpeg command logs show h264_nvenc, not libx264

### 1D: Intermediate files on RAM disk
All temporary files (tts clips, card PNGs, segment videos) go to /dev/shm/pp_render/
instead of disk. Create at start, clean at end.
```python
import os, shutil
TMPDIR = "/dev/shm/pp_render"
os.makedirs(TMPDIR, exist_ok=True)
# ... use TMPDIR for all intermediates ...
# cleanup:
shutil.rmtree(TMPDIR, ignore_errors=True)
```

---

## PHASE 2: SOCIAL CARDS (P1)

### 2A: HTML template + Playwright screenshot
CREATE: video_pipeline_v3/social_card_renderer.py
BUILD: an HTML/CSS template that looks like a premium branded tweet card:
- Dark background (#0A0A0A)
- Red left border accent (#CC0000)
- Handle in red, tweet text in white
- Platform icon (X/Nostr) top-right
- Engagement stats bottom-right
- Dynamic height based on text length
- Brand watermark subtle bottom

RENDER: Use persistent Playwright browser context:
```python
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(viewport={"width": 1200, "height": 800})
    page = await context.new_page()
    await page.set_content(html_template.format(**post_data))
    await page.locator(".card").screenshot(path=output_png)
```

OUTPUT: PNG files, one per social post
THEN: FFmpeg overlays the PNGs onto the video as simple image assets
NO: text rendering inside ffmpeg filtergraphs

### 2B: Actual tweet screenshots (preferred path)
For X posts: use Playwright to capture the actual tweet URL
For Nostr: use HTML template (no reliable web view)
CACHE: by post ID — never re-screenshot the same post
FALLBACK: if live screenshot fails, use the HTML template

---

## PHASE 3: TTS VOICE QUALITY (P1)

### 3A: Wire Chatterbox V3 properly
READ: video_pipeline_v3/tts_engine.py
The tts_chatterbox function was never properly defined. Fix it:
```python
def tts_chatterbox(text, output_path):
    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device="cuda:1")
    wav = model.generate(text, audio_prompt_path=PBX_REFERENCE_AUDIO)
    torchaudio.save(output_path + ".wav", wav, model.sr)
    # Convert to AAC
    subprocess.run(["ffmpeg", "-y", "-i", output_path + ".wav",
                     "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                     output_path], capture_output=True, timeout=30)
    return os.path.exists(output_path) and os.path.getsize(output_path) > 500
```
REFERENCE AUDIO: /home/ultron/protocol_pulse/data/audio/line_001_pbx.m4a
TEST: generate 5 sample lines, listen, verify no robotic cadence

### 3B: TTS bakeoff harness (if time allows)
Install: Qwen3-TTS, MOSS-TTS 1.5, CosyVoice 3, update F5-TTS to 1.1.22
Create: 50 test lines covering Bitcoin jargon, numbers, names, emotion
Generate: all lines with all engines
Score: speaker identity, naturalness, prosody, pronunciation, stability
Pick winner for production

### 3C: Pronunciation JSON file
MOVE: all pronunciation replacements from inline regex to a JSON file:
```json
{
  "fiat": "fee-aht",
  "Szabo": "Say-bo",
  "Saylor": "Say-lor",
  "satoshis": "satoshees",
  "Antonopoulos": "Ahn-toh-NOP-oh-lus"
}
```
LOAD: at TTS engine startup
APPLY: before every TTS call

### 3D: Sentence-level pacing
Split text into sentences. Generate TTS for each sentence separately.
Insert 0.2-0.4s silence between sentences (natural breathing rhythm).
Concatenate with ffmpeg.

---

## PHASE 4: CLIP SENTENCE BOUNDARIES (P1)

### 4A: WhisperX word-level alignment
Install whisperx if not present: pip install whisperx
Use word-level timestamps instead of segment-level
Cut ONLY at sentence-ending punctuation (. ! ?) followed by a pause

### 4B: Semantic exit scoring
After WhisperX identifies candidate cut points, use local Qwen to score each:
```
Rate this as a clip exit point (0-100):
"...and that's why the hash rate matters for security."
vs
"...and that's why the hash rate—"
```
Pick the highest-scoring exit within the duration window.

### 4C: Never use silence as the primary cutter
Silence generates CANDIDATES. Semantic scoring picks the WINNER.
300-800ms padding after the last word of the selected sentence.
1.5s audio fadeout.

---

## PHASE 5: PRODUCTION QC GATE (P2)

### 5A: Automated output verification
After EVERY render, before declaring success:
```python
def verify_output(path):
    checks = {
        "exists": os.path.exists(path),
        "size_mb": os.path.getsize(path) / 1024 / 1024,
        "duration": ffprobe_duration(path),
        "resolution": ffprobe_resolution(path),  # must be 1920x1080
        "has_audio": ffprobe_has_audio(path),
        "bitrate_mbps": ffprobe_bitrate(path) / 1_000_000,
    }
    checks["pass"] = (
        checks["exists"] and
        checks["size_mb"] > 50 and
        checks["duration"] > 180 and
        checks["resolution"] == "1920x1080" and
        checks["has_audio"] and
        checks["bitrate_mbps"] > 3
    )
    return checks
```
Log all checks. Only declare success if ALL pass.

### 5B: Script metadata stripping verification
After script generation, verify NO metadata tags remain:
```python
BANNED_PATTERNS = ["(NARRATION)", "(WARM)", "(COLD OPEN)", "(SETUP)",
                   "(REACT)", "(AUTHORITY)", "(CLEAR)", "(WHISPER)",
                   "Cold Open:", "Narration:", "Warm:", "Setup:"]
for pattern in BANNED_PATTERNS:
    assert pattern not in script_text, f"Metadata leak: {pattern}"
```

---

## PHASE 6: LLM COST MANAGEMENT (P2)

### 6A: Install LiteLLM as gateway
```bash
pip install litellm
```
Deploy config at ~/protocol_pulse/litellm_config.yaml
Route: local Qwen for scoring/classification, Gemini for mid-tier, Anthropic for premium
Budget: $5/day soft, $10/day hard
Log: every request with model, tokens, cost

### 6B: Token cost logger
Every LLM call in the pipeline should log:
```python
logger.info(f"[LLM] model={model} tokens_in={in} tokens_out={out} cost=${cost:.4f}")
```

---

## EXPERIMENT LOOP
1. Pick highest-priority incomplete phase
2. Read ALL relevant files before making changes
3. Make ONE change
4. Test: run a segment render (not full pipeline) to verify
5. If pass: commit with "PASS: [phase] [description]"
6. If fail: revert, try different approach
7. After all phases: run full test render
8. Verify output with Phase 5 QC gate
9. Only declare done when QC gate passes

## CONSTRAINTS
- One file change per commit
- python3 -m py_compile after every edit
- Never change assembler.py and clip_extractor.py in same commit
- TTS uses cuda:1, render uses cuda:0
- All intermediate files to /dev/shm/pp_render/
- Test renders: python3 daily_producer.py --test --no-resume --skip-scan

## GATE RENDER RULE
A gate render only counts if launched AFTER the last commit touching the
render path. If commits land mid-render, kill and relaunch immediately.
Never let a stale render burn wall-clock — the whole point of a gate is
to prove the code you just committed produces a valid file.

Enforcement checklist before declaring a gate PASS:
  1. `git log -1 --format=%H` at gate-render kickoff
  2. `git log --since="<render_start_ts>" -- video_pipeline_v3/ services/` empty
  3. If any commit lands mid-render → SIGTERM the running producer,
     `rm -rf /dev/shm/pp_render/*`, `rm /tmp/daily_producer_gpu*.lock`,
     relaunch.
  4. Only after a clean start-to-finish run on the current HEAD is the
     Phase 5 QC gate authoritative.
