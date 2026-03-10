#!/usr/bin/env python3
"""
gemini_video_qc.py — Gemini 2.5 Pro video quality control for Protocol Pulse

Usage:
    python3 utils/gemini_video_qc.py <path/to/video.mp4>

Output:
    ~/protocol_pulse/logs/gemini_qc/TIMESTAMP/GEMINI_QC_REPORT.json
    ~/protocol_pulse/logs/gemini_qc/TIMESTAMP/GEMINI_QC_REPORT.md (human-readable)
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

# ── Configuration ───────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-pro"
LOGS_DIR = Path("~/protocol_pulse/logs/gemini_qc").expanduser()

QC_PROMPT = """You are a professional video quality control analyst reviewing a Bitcoin intelligence briefing show called "Protocol Pulse / Pulse Check."

Watch the ENTIRE video with AUDIO before scoring. Pay attention to what you actually see and hear.

Score each dimension 0–10 (10 = perfect):

1. **voices** (0–10): Are there clearly two distinct human narrator voices (Eryn and Mark)? Is dialogue audible and intelligible throughout? Score 0 if only silence/music, 5 if one voice, 10 if two distinct voices with good audio.

2. **pip** (0–10): During narration segments, is there a Picture-in-Picture video playing in the top-right quadrant (NOT a static thumbnail)? Score 0 if absent/static image, 10 if actual video clip is playing.

3. **cold_open** (0–10): Does the cold open (first 3–5 seconds) show a clean cinematic background (#0A0A0F dark) with just date text? Score 0 if thumbnail/face overlaps text, 5 if partially clean, 10 if completely clean.

4. **background** (0–10): Is the cyberpunk background (#0A0A0F with subtle red grid) consistently applied? No pure black screens, no random colors.

5. **debug_text** (0–10): Are there zero debug labels, placeholder cards ("INTELLIGENCE INCOMING", "CLIP #N LOADING"), or engineering text visible in the final video? Score 0 if placeholders present, 10 if completely clean.

6. **audio_quality** (0–10): Is audio balanced, not clipping, not muffled? Is background music present but not overwhelming voices?

7. **pacing** (0–10): Does the video have appropriate pacing? Good transitions, not rushed or dragging?

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{
  "scores": {
    "voices": <int>,
    "pip": <int>,
    "cold_open": <int>,
    "background": <int>,
    "debug_text": <int>,
    "audio_quality": <int>,
    "pacing": <int>
  },
  "overall_grade": "<A|B|C|D|F>",
  "grade_rationale": "<1 sentence>",
  "top_3_fixes": [
    "<fix 1 — specific and actionable>",
    "<fix 2 — specific and actionable>",
    "<fix 3 — specific and actionable>"
  ],
  "claude_code_prompt": "<detailed prompt for Claude Code to fix the top issues — reference specific function names and file paths in ~/protocol_pulse/video_pipeline_v3/assembler.py or other files>"
}

Grade rubric:
- A: All scores ≥ 8, no critical failures
- B: Average ≥ 7, at most one score < 6
- C: Average ≥ 5, voices score ≥ 6
- D: Average ≥ 4 OR voices score 3–5
- F: voices = 0 OR average < 4 OR multiple critical failures"""


def upload_video(client: genai.Client, video_path: str):
    """Upload video to Gemini File API and wait for processing."""
    print(f"[qc] Uploading {video_path} to Gemini File API...")
    file_size = os.path.getsize(video_path)
    print(f"[qc] File size: {file_size / 1024 / 1024:.1f} MB")

    with open(video_path, "rb") as f:
        video_file = client.files.upload(
            file=f,
            config=types.UploadFileConfig(mime_type="video/mp4")
        )

    print(f"[qc] Upload complete: {video_file.name} — waiting for processing...")

    # Poll until ACTIVE
    max_wait = 300  # 5 minutes
    waited = 0
    while video_file.state.name == "PROCESSING":
        if waited >= max_wait:
            raise TimeoutError(f"Gemini file processing timed out after {max_wait}s")
        time.sleep(5)
        waited += 5
        video_file = client.files.get(name=video_file.name)
        print(f"[qc] Processing... ({waited}s)")

    if video_file.state.name == "FAILED":
        raise RuntimeError(f"Gemini file processing failed: {video_file.state}")

    print(f"[qc] File ready: {video_file.uri}")
    return video_file


def run_ffprobe_checks(video_path: str) -> dict:
    """Run ffmpeg blackdetect, silencedetect, and ebur128 checks."""
    import subprocess

    results = {}

    # Black frame detection
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-vf", "blackdetect=d=0.5:pix_th=0.10",
             "-an", "-f", "null", "-"],
            capture_output=True, text=True, timeout=60
        )
        black_lines = [l for l in r.stderr.split("\n") if "black_start" in l]
        results["black_frames"] = len(black_lines)
        results["black_segments"] = black_lines[:5]
    except Exception as e:
        results["black_frames_error"] = str(e)

    # Silence detection
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-af", "silencedetect=n=-50dB:d=2",
             "-vn", "-f", "null", "-"],
            capture_output=True, text=True, timeout=60
        )
        silence_lines = [l for l in r.stderr.split("\n") if "silence_start" in l or "silence_end" in l]
        results["silence_segments"] = len([l for l in silence_lines if "silence_start" in l])
        results["silence_details"] = silence_lines[:10]
    except Exception as e:
        results["silence_error"] = str(e)

    # LUFS measurement
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", video_path, "-af", "ebur128=peak=true",
             "-vn", "-f", "null", "-"],
            capture_output=True, text=True, timeout=120
        )
        lufs_line = ""
        lra_line = ""
        for line in r.stderr.split("\n"):
            if "I:" in line and "LUFS" in line:
                lufs_line = line.strip()
            if "LRA:" in line and "LU" in line:
                lra_line = line.strip()
        if lufs_line:
            results["lufs_line"] = lufs_line
        if lra_line:
            results["lra_line"] = lra_line
    except Exception as e:
        results["lufs_error"] = str(e)

    return results


def main():
    parser = argparse.ArgumentParser(description="Gemini 2.5 Pro video QC for Protocol Pulse")
    parser.add_argument("video", help="Path to MP4 file to analyze")
    parser.add_argument("--no-upload", action="store_true", help="Skip upload (for testing ffprobe only)")
    args = parser.parse_args()

    video_path = os.path.expanduser(args.video)
    if not os.path.exists(video_path):
        print(f"[qc] ERROR: Video not found: {video_path}")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[qc] ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = LOGS_DIR / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[qc] Output dir: {out_dir}")

    # Run ffprobe checks first (fast, local)
    print("[qc] Running ffprobe checks (blackdetect, silencedetect, ebur128)...")
    ffprobe = run_ffprobe_checks(video_path)
    print(f"[qc] Black segments: {ffprobe.get('black_frames', '?')}")
    print(f"[qc] Silence segments: {ffprobe.get('silence_segments', '?')}")
    if "lufs_line" in ffprobe:
        print(f"[qc] LUFS: {ffprobe['lufs_line']}")

    # Upload to Gemini and get QC
    qc_result = {}
    raw_text = ""
    if not args.no_upload:
        try:
            video_file = upload_video(client, video_path)

            print(f"[qc] Sending to {GEMINI_MODEL} for analysis...")
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Part.from_uri(file_uri=video_file.uri, mime_type="video/mp4"),
                    QC_PROMPT,
                ],
                config=types.GenerateContentConfig(
                    temperature=1.0,  # required for thinking models
                    max_output_tokens=8192,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=5000,  # reserve tokens for reasoning
                    ),
                )
            )

            # Gemini 2.5 Pro (thinking model) may return None for response.text
            # Extract from candidates directly
            raw_text = None
            if response.text:
                raw_text = response.text.strip()
            elif response.candidates:
                for cand in response.candidates:
                    if cand.content and cand.content.parts:
                        for part in cand.content.parts:
                            # Skip thought parts, grab final text
                            if hasattr(part, "text") and part.text:
                                raw_text = part.text.strip()
                                # Keep last non-empty text part (final answer)
            if not raw_text:
                raise ValueError(f"Empty response from Gemini. candidates={response.candidates}")
            print(f"[qc] Raw response length: {len(raw_text)} chars")

            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                lines = raw_text.split("\n")
                raw_text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

            # Sanitize: remove non-ASCII/garbage chars that thinking models sometimes inject
            import re
            raw_text = re.sub(r'[^\x00-\x7F]+', '', raw_text)

            qc_result = json.loads(raw_text)
            print(f"[qc] Grade: {qc_result.get('overall_grade', '?')}")
            print(f"[qc] Rationale: {qc_result.get('grade_rationale', '')}")

            # Clean up Gemini file
            client.files.delete(name=video_file.name)
            print(f"[qc] Deleted Gemini file: {video_file.name}")

        except json.JSONDecodeError as e:
            print(f"[qc] ERROR parsing Gemini JSON: {e}")
            print(f"[qc] Raw text: {raw_text[:500]}")
            qc_result = {"error": "json_parse_failed", "raw": raw_text}
        except Exception as e:
            print(f"[qc] ERROR: {type(e).__name__}: {e}")
            qc_result = {"error": str(e)}
    else:
        print("[qc] --no-upload: skipping Gemini analysis")
        qc_result = {
            "scores": {"voices": 0, "pip": 0, "cold_open": 5, "background": 5,
                       "debug_text": 0, "audio_quality": 5, "pacing": 5},
            "overall_grade": "F",
            "grade_rationale": "Test mode — no upload",
            "top_3_fixes": ["Test fix 1", "Test fix 2", "Test fix 3"],
            "claude_code_prompt": "Test mode"
        }

    # Merge ffprobe results
    qc_result["ffprobe"] = ffprobe
    qc_result["video_path"] = video_path
    qc_result["timestamp"] = timestamp
    qc_result["model"] = GEMINI_MODEL

    # Save JSON report
    json_path = out_dir / "GEMINI_QC_REPORT.json"
    with open(json_path, "w") as f:
        json.dump(qc_result, f, indent=2)
    print(f"[qc] JSON report: {json_path}")

    # Generate markdown report
    grade = qc_result.get("overall_grade", "?")
    scores = qc_result.get("scores", {})
    top3 = qc_result.get("top_3_fixes", [])
    claude_prompt = qc_result.get("claude_code_prompt", "")

    avg = sum(scores.values()) / len(scores) if scores else 0

    md = f"""# GEMINI QC REPORT
Generated: {timestamp}
Video: {video_path}
Model: {GEMINI_MODEL}

## GRADE: {grade}
{qc_result.get('grade_rationale', '')}

## SCORES
| Dimension | Score |
|-----------|-------|
"""
    for dim, score in scores.items():
        bar = "█" * score + "░" * (10 - score)
        md += f"| {dim:<15} | {score:>2}/10  {bar} |\n"

    md += f"\n**Average: {avg:.1f}/10**\n"

    md += "\n## TOP 3 FIXES\n"
    for i, fix in enumerate(top3, 1):
        md += f"{i}. {fix}\n"

    md += f"""
## CLAUDE CODE PROMPT
```
{claude_prompt}
```

## FFPROBE CHECKS
- Black segments detected: {ffprobe.get('black_frames', 'N/A')}
- Silence segments detected: {ffprobe.get('silence_segments', 'N/A')}
- LUFS: {ffprobe.get('lufs_line', 'N/A')}
"""

    if ffprobe.get("black_segments"):
        md += "\n### Black Segments\n"
        for seg in ffprobe["black_segments"]:
            md += f"- {seg}\n"

    if ffprobe.get("silence_details"):
        md += "\n### Silence Details\n"
        for seg in ffprobe["silence_details"][:6]:
            md += f"- {seg}\n"

    md_path = out_dir / "GEMINI_QC_REPORT.md"
    with open(md_path, "w") as f:
        f.write(md)
    print(f"[qc] MD report: {md_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"GEMINI QC GRADE: {grade}")
    print(f"Average score: {avg:.1f}/10")
    print(f"{'='*60}")
    for dim, score in scores.items():
        status = "✓" if score >= 7 else "✗"
        print(f"  {status} {dim}: {score}/10")
    print(f"{'='*60}")
    print("Top fixes:")
    for i, fix in enumerate(top3, 1):
        print(f"  {i}. {fix}")
    print(f"{'='*60}\n")

    return 0 if grade in ("A", "B") else 1


if __name__ == "__main__":
    sys.exit(main())
