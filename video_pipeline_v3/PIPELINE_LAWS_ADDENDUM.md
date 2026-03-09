
---

## SECTION 15: AD READ FILTER — PERMANENT LAW
### Clip segments containing ad reads are INVALID. They must never enter the assembly.

This is not a one-time fix. It is a permanent enforcement layer in `clip_extractor.py`.
Every clip transcript segment must pass this filter before it is eligible for selection.

```python
AD_READ_PATTERNS = [
    "brought to you by",
    "this episode is sponsored",
    "thanks to our sponsor",
    "today's sponsor",
    "use code ",
    "promo code",
    "discount code",
    "go to ",
    ".com/",
    "check out ",
    "head over to",
    "sign up at",
    "visit ",
    "affiliate",
    "limited time offer",
    "use my link",
    "click the link in",
    "swipe up",
    "free trial",
    "get 20% off",
    "get 10% off",
]

def contains_ad_read(transcript_segment: str) -> bool:
    """
    Return True if this transcript segment contains ad read content.
    Called on EVERY clip candidate before selection. If True, REJECT the clip.
    This runs in clip_extractor.py AND clip_selector.py as a double gate.
    """
    lower = transcript_segment.lower()
    for pattern in AD_READ_PATTERNS:
        if pattern in lower:
            log(f"🚫 AD READ DETECTED — pattern '{pattern}' found. Clip REJECTED.")
            return True
    return False
```

**LAW: `contains_ad_read()` is called at TWO points:**
1. In `clip_selector.py` — before a timestamp range is even selected (LLM prompt + post-selection validation)
2. In `clip_extractor.py` — before the extracted clip file is returned to the assembler

**LAW: If ad read content is detected, the clip is REJECTED entirely. Do not trim around it. Reject and find the next eligible segment.**

**LAW: Add to `SELECTION_PROMPT` in `clip_selector.py`:**
```
CRITICAL — AD READ REJECTION: NEVER select a timestamp range that contains an ad 
read, sponsorship segment, or promotional mention. Patterns that DISQUALIFY a segment:
"brought to you by", "use code", "go to [domain].com", "promo code", "check out",
"today's sponsor", "free trial", discount offers, affiliate URLs.
If the best moments in a video are interrupted by ad reads, select from a different 
video. Publishing ad content from other shows is a serious brand violation.
```

---

## SECTION 16: BRAND COLORS — IMMUTABLE PALETTE
### Protocol Pulse brand colors are RED, BLACK, WHITE. No exceptions, ever.

```python
# PROTOCOL PULSE BRAND PALETTE — use these constants everywhere
BRAND = {
    "primary_red":   "0xCC0000",     # Main accent, waveform, borders, highlights
    "dark_red":      "0x880000",     # Secondary, host 2 label, subtle accents
    "bright_red":    "0xFF4444",     # Waveform mirror, energy moments
    "bg_black":      "0x0A0000",     # Base background (near-black with red undertone)
    "bg_dark":       "0x100000",     # Slightly lighter background panels
    "card_bg":       "0x1A0000",     # Tweet cards, info panel backgrounds
    "text_white":    "0xFFFFFF",     # All body text
    "text_gold":     "0xFFD700",     # Ticker text only
    "host1_label":   "0xCC0000",     # Primary host label background
    "host2_label":   "0x880000",     # Secondary host label background
    "thumb_border":  "0xCC0000",     # Thumbnail PIP border
}

# BANNED COLORS — never use these in any visual element:
# 0x00D4FF — cyan (was old waveform color)
# 0x7B2FFF — purple
# 0x3388FF — blue (was old host 2 color)
# 0x0A0520 — blue-tinted background
# 0x050510 — blue-tinted base
```

**LAW: Before committing any assembler.py change, run:**
```bash
grep -n "00D4FF\|7B2FFF\|3388FF\|0A0520\|050510" assembler.py
```
**If any results appear: fix them before committing. Zero banned colors allowed.**

**LAW: The waveform visualizer uses `BRAND["primary_red"]` and `BRAND["bright_red"]`.
Never blue, never cyan, never purple.**

**LAW: The bottom-third waveform design — compact, contained, bottom of frame.
NOT full-screen. A sleek visualizer strip, not a wallpaper.**

---

## SECTION 17: NARRATION IS THE TIMELINE — OUTRO TIMING AUTHORITY
### Nothing starts the outro until narration audio is 100% complete. No exceptions.

This enforces Rule 3.5 from Section 3. The outro timing bug (outro playing at 3:28 while
narrator continues to 3:41) is a Rule 3.5 violation and must never happen again.

```python
def get_narration_end_timestamp(dialogue_parts: list) -> float:
    """
    Calculate the EXACT timestamp when the last narration word ends.
    The outro may not begin until AFTER this timestamp.
    """
    total = 0.0
    for part in dialogue_parts:
        duration = get_duration(part["video_path"])
        total += duration
    return total  # This is the narration_end_timestamp

def assemble_episode(dialogue_parts, outro_path, work_dir, **kwargs):
    """
    RULE: Outro is appended ONLY after ALL dialogue parts including wrap.
    The concat list must have all dialogue parts listed BEFORE outro.
    """
    parts = []
    
    # Step 1: Render ALL dialogue parts (includes cold open, clips, narrator 
    # segments, wrap). Every part goes into `parts` list.
    for entry in dialogue_parts:
        rendered = render_segment(entry, work_dir)
        if not validate_video_file(rendered):
            raise RuntimeError(f"Invalid segment: {entry}")
        parts.append(rendered)
    
    # Step 2: ONLY after ALL dialogue is in parts list, add outro
    narration_end = sum(get_duration(p) for p in parts)
    log(f"Narration ends at {narration_end:.1f}s — outro starts here")
    
    if outro_path and os.path.exists(outro_path):
        parts.append(outro_path)
    
    # Step 3: Concat in order — narration always finishes before outro plays
    return concat_parts(parts, work_dir)
```

**LAW: The `parts` list is built sequentially. Outro is always the LAST item appended.**
**LAW: Never start outro while narration audio is still in the timeline.**
**LAW: If outro video is a different duration than expected, pad or trim it — never let it interrupt narration.**

---

## SECTION 18: AUDIO SYNC — ROOT CAUSE DIAGNOSIS REQUIRED
### AV sync must be diagnosed at the source, not patched at the output.

The recurring audio sync issue has two completely different root causes with different fixes.
**Diagnose which one it is before writing any code.**

### Diagnosis Protocol:
```bash
# Step 1: Check a raw downloaded clip BEFORE any processing
ffprobe -v quiet -print_format json -show_streams raw_clip.mp4 | python3 -c "
import json,sys
data=json.load(sys.stdin)
for s in data['streams']:
    print(s['codec_type'], 'start_time:', s.get('start_time','N/A'), 
          'start_pts:', s.get('start_pts','N/A'))
"
# If video start_time != audio start_time on the RAW clip: ROOT CAUSE = download/source
# Fix: PTS regeneration during clip extraction

# Step 2: Check the assembled output
ffprobe -v quiet -print_format json -show_streams final_output.mp4 | python3 -c "
import json,sys
data=json.load(sys.stdin)
for s in data['streams']:
    print(s['codec_type'], 'start_time:', s.get('start_time','N/A'))
"
# If raw clips are in sync but output is not: ROOT CAUSE = assembler concat
# Fix: Normalize all segments before concat, use -async 1 in final encode
```

### Fix A: Source out of sync (clips arrive pre-drifted)
```python
# In clip_extractor.py — apply to EVERY clip immediately after download
def fix_clip_sync(input_path: str, output_path: str) -> bool:
    return run_ffmpeg([
        "-fflags", "+genpts+igndts",
        "-i", input_path,
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-r", "30", "-vsync", "cfr",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=fps=30",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-af", "aresample=async=1:min_hard_comp=0.100000:first_pts=0",
        "-avoid_negative_ts", "make_zero",
        "-movflags", "+faststart",
        output_path,
    ], "fix_clip_sync", 180)
```

### Fix B: Assembler introducing drift (concat is misaligning streams)
```python
# In assembler.py — normalize EVERY segment before adding to concat list
def normalize_for_concat(input_path: str, output_path: str) -> bool:
    """Ensure consistent timebase and stream layout before concat."""
    return run_ffmpeg([
        "-i", input_path,
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-r", "30", "-vsync", "cfr",
        "-pix_fmt", "yuv420p",
        "-video_track_timescale", "90000",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-af", "aresample=async=1",
        output_path,
    ], "normalize_concat", 120)
```

**LAW: Run the diagnosis protocol FIRST. Report which root cause is identified.**
**LAW: Apply the correct fix — don't apply both blindly.**
**LAW: After fix, log AV offset for every clip:**
```python
def measure_av_offset(clip_path: str) -> float:
    """Returns offset in seconds. 0 = perfect. Positive = audio ahead of video."""
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", clip_path],
        capture_output=True, text=True
    ).stdout)
    streams = probe.get("streams", [])
    v_start = next((float(s.get("start_time", 0)) for s in streams if s["codec_type"] == "video"), 0)
    a_start = next((float(s.get("start_time", 0)) for s in streams if s["codec_type"] == "audio"), 0)
    offset = a_start - v_start
    log(f"AV offset for {os.path.basename(clip_path)}: {offset:+.3f}s")
    if abs(offset) > 0.1:
        log(f"⚠️ AV SYNC WARNING: offset {offset:+.3f}s exceeds 0.1s threshold")
    return offset
```
**LAW: Any clip with AV offset > 0.1s after fix must be flagged in the log.**
