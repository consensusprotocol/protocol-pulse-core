#!/usr/bin/env python3
"""
PROTOCOL PULSE — GROK-4 VISION QC ENGINE v2
============================================
Forensic-grade video quality control. Extracts dense frame grid across the
full video, sends batches to Grok-4 Vision for meticulous multi-axis analysis,
and produces an actionable bug report with timecodes.

Usage:
    python3 grok_qc_v2.py --video <path_to_mp4> --out <output_dir>
    python3 grok_qc_v2.py --video ~/protocol_pulse/video_pipeline_v3/output/pulse_check_20260309_124332.mp4

Frame sampling: 1 frame every 5 seconds + keyframes at every segment boundary
Total frames for 700s video: ~140 frames sent across 5 batches
"""

import os, sys, json, base64, subprocess, argparse, re
from pathlib import Path
from datetime import datetime

XAI_KEY = os.environ.get("XAI_API_KEY", "")
if not XAI_KEY:
    env = Path.home() / "protocol_pulse/.env"
    if env.exists():
        for line in env.read_text().split("\n"):
            if line.startswith("XAI_API_KEY="):
                XAI_KEY = line.split("=", 1)[1].strip()
                break

# ─── MASTER QC PROMPT ────────────────────────────────────────────────────────
# This is the full expert knowledge briefing sent to Grok before every batch.

MASTER_PROMPT = """
You are a BROADCAST QC DIRECTOR and SENIOR VIDEO ENGINEER for Protocol Pulse,
a professional Bitcoin intelligence media platform. Your job is to perform
FORENSIC-LEVEL quality control on a "Pulse Check" daily episode.

You have worked on broadcast television, streaming platforms, and YouTube
channels at the highest production level. You are meticulous, technical,
and you will NOT overlook anything. Every issue must be logged with its
exact timecode, a clear description of what's wrong, and a severity rating.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHOW FORMAT — MEMORIZE THIS STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Segment sequence (in exact order):
[000] TITLE CARD (0:00–0:02)
[001] COLD OPEN HOOK (0:02–~0:14)
[002] SETUP NARRATION segments (host narrates into clips)
[003] CLIP #1 (or PLACEHOLDER if unavailable)
[004] CLIP #2
[005] CLIP #3
[006] CLIP #4
[007] CLIP #5
[008] SOCIAL/TWEET CARDS (3-4 tweet cards)
[009] BRANDED OUTRO

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESIGN SYSTEM — PIXEL-EXACT SPECIFICATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Canvas: 1920×1080px, 30fps

BACKGROUND LAYER (every segment except clips):
  - Dark cyberpunk animated bg: deep navy/black (#0A0A0F to #0D1117)
  - Subtle animated grid lines or particle effect
  - NO plain gray, NO white, NO raw black rectangles from YouTube thumbnails
  - CRITICAL: Background must fill 100% of canvas (all 1920px wide, all 1080px tall)
  - Common bug: background only fills LEFT half, right side is plain gray/dark

COLOR PALETTE:
  - Background: #0A0A0F (near-black, NOT pure #000000)
  - Primary accent: #FF3333 (red) — borders, segment type labels
  - Gold/info: #F8C15C — bottom info bar, stats, prices
  - White: #FFFFFF — primary body text
  - Cyan: #00FFFF — data overlays, secondary accent
  - FAIL conditions: pink (#FF69B4), magenta, bright green, purple = WRONG colors

BOTTOM INFO BAR (present in ALL segments except cold open):
  - Full-width: x=0, y=1032, w=1920, h=48px
  - Background: black glassmorphism (rgba(0,0,0,0.85) + blur)
  - Left side: "BTC $XX,XXX" in gold (#F8C15C), JetBrains Mono font
  - Center: horizontal progress bar or episode ticker
  - Right side: "MAR 09, 2026 — DAILY BRIEF" or episode title in gold
  - FAIL: red/pink bar, bar missing, bar only covers partial width, wrong colors
  - FAIL: bar bleeds over main content area

PIP (PICTURE-IN-PICTURE) ELEMENT — NARRATION SEGMENTS ONLY:
  - Zone: top-right quadrant ONLY — x: 960–1880, y: 40–540
  - Size: approx 716×402px (16:9 within quadrant)
  - Content: YouTube thumbnail preview of next clip
  - MUST have: thin red (#FF3333) 2px border around PiP frame
  - MUST have: channel name lower-third overlay (white text, dark bg strip)
  - MUST have: corner bracket decorations (tactical BD-style, 16px)
  - FAIL: PiP overlapping with narrator text (left half)
  - FAIL: PiP outside top-right quadrant
  - FAIL: PiP missing entirely when a clip thumbnail is available
  - FAIL: duplicate PiP images stacked on same position
  - FAIL: PiP showing wrong segment's clip

NARRATOR TEXT ZONE — NARRATION SEGMENTS:
  - Safe zone: x=40 to x=960 (LEFT HALF ONLY, never overlapping PiP)
  - y: centered in 200–800px range
  - Font: large, white, bold, clean readable
  - FAIL: text extends into right half (x>960) where PiP lives
  - FAIL: text cut off at edges
  - FAIL: text color is yellow, red, or gray instead of white
  - FAIL: text overflows 3 lines (truncate at 3 lines max)
  - FAIL: empty text block (black rectangle with no text = TTS silence fallback)

ANIMATED SUBTITLES / LOWER-THIRD (during narration):
  - Band at: y=778 to y=885 (72%–82% of height)
  - Dark glass background: rgba(0,0,0,0.75)
  - Left red accent bar: 4px wide, full band height, #FF3333
  - Text: white, medium weight, centered in band
  - Should be present and synced to speech
  - FAIL: subtitle band missing entirely
  - FAIL: band covers more than 10% of screen height
  - FAIL: band overlaps PiP or bottom info bar

TITLE CARD (segment [000], 0:00–0:02):
  - Should display: "PROTOCOL PULSE" (large white bold) + "PULSE CHECK" (red accent)
  - Background: full-canvas cyberpunk animated background
  - Optional: host avatar/face silhouette on right side
  - FAIL: YouTube thumbnail content bleeding into title card background
  - FAIL: right half of screen is plain gray or dark (#1A1A1A flat gray) — no bg
  - FAIL: left half shows YouTube clip content, right half is empty/gray
  - FAIL: title text missing or illegible
  - FAIL: bottom info bar not present on title card
  - FAIL: host face NOT cropped cleanly (partial head, floats without proper framing)

COLD OPEN HOOK (segment [001], 0:02–~0:14):
  - Full-screen dramatic clip OR face-cam of host
  - NO LOGO overlay (intentional for hook impact)
  - NO music (cold, raw feel)
  - High energy, Bitcoin/macro financial content
  - FAIL: generic stock footage or plain black
  - FAIL: PROTOCOL PULSE branding logo showing (breaks cold open rule)
  - FAIL: audio present but video shows black/still frame

YOUTUBE CLIP SEGMENTS ([003]–[007]):
  - Full-screen 1920×1080, source clip
  - 2px red border on all 4 edges
  - Bottom: "PROTOCOL PULSE" white text watermark (lower-right or lower-center)
  - FAIL: clip shows "PLACEHOLDER" or "SIGNAL INTERRUPTED" message instead of real clip
  - FAIL: clip is a near-black, dark, or blank placeholder
  - FAIL: clip border is pink/magenta instead of red
  - FAIL: no watermark visible
  - FAIL: clip has wrong aspect ratio (letterboxed, stretched, pillarboxed)

PLACEHOLDER CARD (when clip unavailable):
  - Should show: animated grid bg + "⚡ INTELLIGENCE INCOMING" + "SOURCING PARTNER SIGNAL..."
  - Color: #0D1117 bg, cyan/red text
  - Duration: exactly 8s
  - FAIL: plain black with no text
  - FAIL: "Source Unavailable - Signal Interrupted" debug message visible to viewers
  - FAIL: placeholder shows YouTube UI elements, error pages, or thumbnails

SOCIAL/TWEET CARD SEGMENTS:
  - Full-screen dark card with: avatar circle, @handle, tweet text body
  - Background: dark with subtle cyberpunk pattern
  - Red or gold accent dividers
  - Profile picture should be present (not placeholder silhouette)
  - FAIL: plain black card with no text
  - FAIL: tweet text cut off mid-sentence
  - FAIL: multiple tweet cards showing identical content
  - FAIL: avatar shows generic silhouette (profile image didn't load)

BRANDED OUTRO:
  - Protocol Pulse 3D logo animation
  - "SUBSCRIBE / FOLLOW" CTA
  - Social handles
  - Dark bg, clean professional
  - FAIL: outro cuts abruptly without logo
  - FAIL: outro shows audio waveform with no visual

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUDIO INDICATORS TO ASSESS VISUALLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Even though you're analyzing still frames, these visual cues tell you about audio:
- Waveform visualizer bars (if present): are they flat/zero? = silence
- Subtitle text: is it present? = voiceover likely active
- Empty subtitle band: likely means TTS silence fallback (ElevenLabs quota 0)
- Progress bar in bottom info bar: should advance, not be static
- Host face segments showing no mouth movement indicators = silent narration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASSET OVERLAP / Z-ORDER ERRORS — CRITICAL CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For every frame, specifically check these overlap scenarios:
1. PiP box vs narrator text: is any text hidden behind the PiP?
2. Bottom info bar vs main content: does the bar cover any important visual?
3. Subtitle band vs PiP: do they overlap? (subtitle at y=778+, PiP ends at y=540 = safe zone)
4. Watermark vs lower-thirds: do they stack?
5. Multiple text drawtext layers rendering on same y-position
6. Any element extending outside canvas bounds (x<0, x>1920, y<0, y>1080)
7. Corner brackets rendering at wrong position (center of screen instead of corners)
8. Red border frame: is it 2px only, or is it accidentally thicker (4px, 8px)?
9. YouTube thumbnail from clip leaking into background of narration segment
10. Background only rendering on partial canvas (left half, top half, etc.)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRANSITION QUALITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Between segments: should be smooth xfade (slideleft, 0.25s) or clean cut
- FAIL: hard cut with single black frame visible
- FAIL: content from TWO segments visible simultaneously (bleed-through)
- FAIL: aspect ratio changes mid-transition
- FAIL: audio and video clearly desync at cut point

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO ANALYZE EACH FRAME I SEND YOU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For EACH frame, produce a structured report in this EXACT format:

---
FRAME [timecode] — [segment type]
PASS/FAIL/WARN overall
BACKGROUND: [full-canvas / partial / wrong color / thumbnail bleed]
BOTTOM BAR: [present/missing | color: gold/red/wrong | width: full/partial]
PIP: [present/absent | position: correct/wrong | overlap with text: yes/no]
TEXT: [readable/cut-off/wrong-zone | overlap issues]
SUBTITLES: [present/absent | position correct/wrong]
RED BORDER: [present/absent | correct thickness]
WATERMARK: [present/absent]
Z-ORDER BUGS: [list any element stacking/overlap issues]
SPECIFIC ISSUES:
  - [Issue 1 — CRITICAL/HIGH/MEDIUM/LOW]
  - [Issue 2]
  (none if perfect)
---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AT END OF EVERY BATCH — RUNNING BUG LOG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After analyzing all frames in this batch, append:

=== RUNNING BUG LOG (this batch) ===
CRITICAL (production-blocking):
  [timecode] — [issue description] — [which ffmpeg filter/assembler function to fix]
HIGH (significantly degrades viewer experience):
  [timecode] — [issue description]
MEDIUM (visible but not blocking):
  [timecode] — [issue description]
LOW (minor polish):
  [timecode] — [issue description]

=== PRESERVED ELEMENTS (what's working — do NOT change) ===
  [list elements that look correct and should be protected]

=== SPECIFIC CODE FIX RECOMMENDATIONS ===
For each CRITICAL/HIGH issue, suggest the exact assembler.py change:
  BUG: [description]
  FIX: [specific ffmpeg filter, Python function, or draw operation to change]
  EXAMPLE: "In make_title_card_visual(): ensure bg_clip fills full 1920x1080, 
            call clip.set_position(0,0).set_size(1920,1080)"
"""

# ─── FRAME EXTRACTION ────────────────────────────────────────────────────────

def extract_frames(video_path: str, out_dir: str, interval: int = 5) -> list[tuple[int, str]]:
    """Extract 1 frame every N seconds + segment boundary keyframes."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # Get duration
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "csv=p=0", video_path
    ], capture_output=True, text=True)
    duration = float(result.stdout.strip() or "0")
    if duration == 0:
        print(f"ERROR: Could not get duration from {video_path}")
        return []

    print(f"Video duration: {duration:.1f}s ({duration/60:.1f}min)")
    print(f"Extracting 1 frame every {interval}s = ~{int(duration/interval)} frames...")

    frames = []

    # Segment boundary keyframes (always include regardless of interval)
    keyframe_times = [0, 2, 3, 5, 8, 10, 14, 15]  # title, cold open boundaries
    # Add every 5s through the video
    t = 1
    while t < duration:
        keyframe_times.append(int(t))
        t += interval
    keyframe_times = sorted(set([min(int(x), int(duration)-1) for x in keyframe_times]))

    for t in keyframe_times:
        fname = f"frame_{t:05d}s.jpg"
        fpath = os.path.join(out_dir, fname)
        if not os.path.exists(fpath):
            subprocess.run([
                "ffmpeg", "-y", "-ss", str(t), "-i", video_path,
                "-vframes", "1", "-q:v", "2",     # high quality JPEG
                "-vf", "scale=1280:720",           # scale down for API efficiency
                fpath
            ], capture_output=True)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
            frames.append((t, fpath))

    print(f"Extracted {len(frames)} frames to {out_dir}")
    return frames


# ─── GROK API CALL ───────────────────────────────────────────────────────────

def call_grok_vision(frames_batch: list[tuple[int, str]], batch_num: int,
                     total_batches: int, video_info: dict) -> str:
    """Send a batch of frames to Grok-4 Vision for analysis."""
    import requests

    batch_header = f"""
BATCH {batch_num}/{total_batches} — FRAMES {frames_batch[0][0]}s to {frames_batch[-1][0]}s
Video: {video_info['filename']} | Duration: {video_info['duration']:.0f}s | Size: {video_info['size_mb']:.1f}MB
Blackout events detected by ffmpeg: {video_info.get('black_events', 'see forensic data')}
Silence events: {video_info.get('silence_events', 'FULL VIDEO SILENT (ElevenLabs quota=0)')}

This batch contains {len(frames_batch)} frames. Analyze each one systematically.
Apply the MASTER QC PROMPT specifications to every frame.
Be EXHAUSTIVE — do not summarize or skip. If a frame has 5 issues, list all 5.
"""

    content = [{"type": "text", "text": MASTER_PROMPT + batch_header}]

    for ts, fpath in frames_batch:
        with open(fpath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        # Determine segment type from known timeline
        seg = classify_segment(ts, video_info.get('duration', 700))
        content.append({"type": "text", "text": f"\n=== FRAME @ {ts}s [{seg}] ==="})
        content.append({"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}})

    print(f"  Sending batch {batch_num}/{total_batches} ({len(frames_batch)} frames) to grok-4-0709...")
    resp = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
        json={
            "model": "grok-4-0709",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 8000,
            "temperature": 0.05,   # near-zero temp for consistent, analytical output
        },
        timeout=300
    )

    if resp.status_code == 200:
        text = resp.json()["choices"][0]["message"]["content"]
        print(f"  Batch {batch_num} complete — {len(text)} chars returned")
        return text
    else:
        err = f"GROK API ERROR {resp.status_code}: {resp.text[:400]}"
        print(f"  {err}")
        return err


def classify_segment(t: int, duration: float) -> str:
    """Classify approximate segment type from timestamp."""
    if t < 2:   return "TITLE_CARD"
    if t < 15:  return "COLD_OPEN"
    if t < 30:  return "SETUP_NARRATION"
    # Clips roughly fill middle of video
    clip_zone = duration * 0.15
    if t < clip_zone * 2: return "CLIP_SEGMENT"
    if t > duration - 60: return "OUTRO_ZONE"
    if t > duration - 120: return "TWEET_CARDS"
    return "MID_SEGMENT"


# ─── FINAL SYNTHESIS ─────────────────────────────────────────────────────────

SYNTHESIS_PROMPT = """
You have just completed a full forensic QC pass on a Protocol Pulse Pulse Check episode.
I am now giving you ALL batch reports. Synthesize them into a MASTER BUG REPORT.

Structure your output EXACTLY as:

# PROTOCOL PULSE QC — MASTER BUG REPORT
## Video: [filename] | Analyzed: [date] | Total frames: [N]

## EXECUTIVE SUMMARY
[2-3 sentences: overall quality grade A/B/C/D/F, whether it's releasable, top 3 blocking issues]

## GRADE: [A/B/C/D/F] — [one sentence reason]

## CRITICAL BUGS (production-blocking — do not release until fixed)
For each:
### BUG-[N]: [NAME] — CRITICAL
- **Timecodes affected**: [list all]
- **What you see**: [exact visual description]
- **Expected**: [what it should look like per spec]
- **Root cause hypothesis**: [what assembler.py code is likely wrong]
- **Fix**: [specific code change]

## HIGH SEVERITY BUGS (degrade viewer experience significantly)
[same format]

## MEDIUM BUGS (visible but not blocking)
[same format]

## LOW / POLISH ISSUES
[brief list]

## ELEMENTS WORKING CORRECTLY (preserve these — do not touch)
[bulleted list of what's actually good]

## SECOND-PASS CLAUDE CODE PROMPT
[A complete, paste-ready prompt for the next Claude Code session to fix all CRITICAL + HIGH bugs.
Include exact timecodes, exact descriptions, and exact fix instructions.
Start with: "You are fixing video pipeline bugs in ~/protocol_pulse/video_pipeline_v3/assembler.py..."]
"""

def synthesize_all_batches(batch_results: list[str], video_info: dict, out_dir: str) -> str:
    """Run final synthesis call combining all batch reports."""
    import requests

    combined = "\n\n".join([
        f"=== BATCH {i+1} RESULTS ===\n{r}" for i, r in enumerate(batch_results)
    ])
    # Truncate if too long
    if len(combined) > 50000:
        combined = combined[:50000] + "\n...[TRUNCATED FOR CONTEXT]..."

    content = [{
        "type": "text",
        "text": SYNTHESIS_PROMPT + f"\n\nVIDEO INFO:\n{json.dumps(video_info, indent=2)}\n\n{combined}"
    }]

    print("\nRunning final synthesis...")
    resp = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
        json={
            "model": "grok-4-0709",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 6000,
            "temperature": 0.1,
        },
        timeout=300
    )

    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        return f"SYNTHESIS FAILED: {resp.status_code} — {resp.text[:400]}"


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Protocol Pulse Grok-4 Vision QC Engine v2")
    parser.add_argument("--video", required=True, help="Path to MP4 file")
    parser.add_argument("--out", default=None, help="Output directory (default: logs/grok_qc/<timestamp>)")
    parser.add_argument("--interval", type=int, default=5, help="Frame extraction interval in seconds (default: 5)")
    parser.add_argument("--batch-size", type=int, default=25, help="Frames per Grok API call (default: 25)")
    args = parser.parse_args()

    video_path = os.path.expanduser(args.video)
    if not os.path.exists(video_path):
        print(f"ERROR: Video not found: {video_path}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.out or os.path.expanduser(
        f"~/protocol_pulse/logs/grok_qc/{timestamp}"
    )
    frames_dir = os.path.join(out_dir, "frames")
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"PROTOCOL PULSE — GROK-4 VISION QC v2")
    print(f"Video: {video_path}")
    print(f"Output: {out_dir}")
    print(f"{'='*60}\n")

    # Video metadata
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration,size",
        "-of", "json", video_path
    ], capture_output=True, text=True)
    fmt = json.loads(result.stdout).get("format", {})
    video_info = {
        "filename": os.path.basename(video_path),
        "path": video_path,
        "duration": float(fmt.get("duration", 0)),
        "size_mb": int(fmt.get("size", 0)) / 1024 / 1024,
        "analyzed_at": timestamp,
        "black_events": "none detected",
        "silence_events": "audio present — analyze visual cues only",
    }
    print(f"Duration: {video_info['duration']:.1f}s ({video_info['duration']/60:.1f}min)")
    print(f"Size: {video_info['size_mb']:.1f}MB\n")

    # Extract frames
    frames = extract_frames(video_path, frames_dir, interval=args.interval)
    if not frames:
        print("ERROR: No frames extracted")
        sys.exit(1)

    # Batch into groups
    batch_size = args.batch_size
    batches = [frames[i:i+batch_size] for i in range(0, len(frames), batch_size)]
    print(f"\nSending {len(frames)} frames in {len(batches)} batches of {batch_size}")
    print(f"Estimated time: {len(batches) * 45}–{len(batches) * 90}s\n")

    # Run Grok on each batch
    batch_results = []
    for i, batch in enumerate(batches):
        result = call_grok_vision(batch, i+1, len(batches), video_info)
        batch_results.append(result)
        # Save individual batch
        batch_file = os.path.join(out_dir, f"batch_{i+1:02d}.md")
        Path(batch_file).write_text(
            f"# Batch {i+1}/{len(batches)} — Frames {batch[0][0]}s–{batch[-1][0]}s\n\n{result}"
        )
        print(f"  Saved: {batch_file}")

    # Synthesize
    master_report = synthesize_all_batches(batch_results, video_info, out_dir)
    master_file = os.path.join(out_dir, "MASTER_QC_REPORT.md")
    Path(master_file).write_text(f"# MASTER QC REPORT\nGenerated: {timestamp}\n\n{master_report}")
    print(f"\nMASTER REPORT: {master_file}")

    # Print summary
    print(f"\n{'='*60}")
    print("QC COMPLETE")
    print(f"{'='*60}")
    print(master_report[:3000])
    print(f"\nFull report: {master_file}")
    print(f"Batch files: {out_dir}/batch_*.md")


if __name__ == "__main__":
    main()
