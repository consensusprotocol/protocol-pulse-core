#!/usr/bin/env python3
"""Gemini QC — dimension-scored video quality control for Pulse Check episodes.

Returns numeric scores (1-10) per dimension:
  pip, cold_open, background, voices, audio_quality, debug_text

Usage:
    from video_pipeline_v3.gemini_qc import run_gemini_qc
    result = run_gemini_qc("path/to/video.mp4")
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Resolve Gemini API key
def _get_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key
    for envf in [Path.home() / "protocol_pulse/.env",
                 Path(__file__).resolve().parent / ".env"]:
        if envf.exists():
            for line in envf.read_text().split("\n"):
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("'\"")
    return ""


QC_PROMPT = """You are a broadcast QC engineer scoring a Protocol Pulse "Pulse Check" episode.

SHOW DESIGN (score against THIS, not generic expectations):
- Canvas: 1920×1080, 30fps, dark cyberpunk aesthetic
- Background: deep dark (#0A0A0F) with red grid overlay + vignette — this is CORRECT, not a bug
- Top bar: "PROTOCOL PULSE LIVE" branding pill — this is CORRECT branding
- Bottom info bar: "PULSE CHECK" left, scrolling gold ticker right with BTC price
- Narration segments: large white text left half, PiP preview top-right showing next clip
- Clip segments: full-screen YouTube clips with bottom ticker + "PROTOCOL PULSE" watermark
- Social cards: tweet content on dark background
- Waveform visualizer in narration segments is intentional design
- "COMING UP NEXT" label on PiP is functional, NOT debug text

SCORING DIMENSIONS (1-10 each):

1. **pip** — Picture-in-Picture quality in narration segments. Score 10 if PiP shows real thumbnails in correct position (top-right), has red border, channel name. Score 8 if PiP present but some missing thumbnails. Score 5 if PiP rarely present. Score 1 if no PiP at all.

2. **cold_open** — First 15 seconds quality. Score 10 if title card + cold open are clean with branding, BTC price, date. Score 8 if present but minor issues. Score 5 if partially broken. Score 1 if black/missing.

3. **background** — Background consistency across narration segments. Score 10 if dark cyberpunk with grid consistently present. Score 8 if mostly consistent. Score 5 if inconsistent. Score 1 if plain black or broken.

4. **voices** — Are there voice segments? Look for subtitle text, waveform activity. Score 10 if narration text visible in multiple segments (indicating TTS audio). Score 5 if sparse. Score 1 if no narration text at all.

5. **audio_quality** — Visual indicators of audio quality. Score 10 if: narration text is present in setup segments (indicating TTS voiceover), waveform visualizers show activity in narration segments, clip segments show people speaking on camera, and bottom ticker is scrolling. Score 8 if most of these are present. Note: data segments and social cards may NOT have waveforms — this is normal. Only narration/setup segments need waveforms. Score 5 only if MOST segments lack any audio indicators.

6. **debug_text** — Absence of debug overlays. Score 10 if NO debug text like "ORACLE NARRATION ACTIVE", "Story Arc Locked", "RECON-ID", "NARRATIVE SETUP //", "Muted Preview", "Broadcast Signature System", "Motion Active", "Narration Layer". Score 5 if some debug text. Score 1 if pervasive debug overlays.

Return ONLY valid JSON (no markdown fences):
{
  "pip": <1-10>,
  "cold_open": <1-10>,
  "background": <1-10>,
  "voices": <1-10>,
  "audio_quality": <1-10>,
  "debug_text": <1-10>,
  "overall_grade": "<A/B/C/D/F>",
  "issues": ["<issue 1>", "<issue 2>"],
  "strengths": ["<strength 1>", "<strength 2>"]
}
"""


def _extract_frames(video_path: str, interval: int = 15) -> list[tuple[int, str]]:
    """Extract frames at regular intervals."""
    tmpdir = tempfile.mkdtemp(prefix="gemini_qc_")
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip() or "0")
    if duration == 0:
        return []

    times = [1, 3, 8, 10, 15]  # key early frames
    t = 20
    while t < duration - 5:
        times.append(int(t))
        t += interval
    times.append(int(duration) - 5)  # near end
    times = sorted(set(times))

    frames = []
    for t in times:
        if t >= duration:
            continue
        fpath = os.path.join(tmpdir, f"frame_{t:05d}.jpg")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(t), "-i", video_path,
            "-vframes", "1", "-q:v", "3", "-vf", "scale=960:540",
            fpath
        ], capture_output=True)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 500:
            frames.append((t, fpath))

    return frames


def run_gemini_qc(video_path: str) -> dict:
    """Run Gemini QC and return dimension scores."""
    import requests

    key = _get_gemini_key()
    if not key:
        return {"error": "GEMINI_API_KEY not found"}

    video_path = os.path.expanduser(video_path)
    if not os.path.exists(video_path):
        return {"error": f"Video not found: {video_path}"}

    print(f"[gemini_qc] Extracting frames from {os.path.basename(video_path)}...")
    frames = _extract_frames(video_path, interval=20)
    if not frames:
        return {"error": "No frames extracted"}
    print(f"[gemini_qc] Extracted {len(frames)} frames")

    # Build vision API request with inline images
    content = [{"type": "text", "text": QC_PROMPT}]
    for t, fpath in frames:
        with open(fpath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append({"type": "text", "text": f"\n--- Frame at {t}s ---"})
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}})

    # Try Gemini first, fallback to Grok Vision
    text = None

    if key:
        print(f"[gemini_qc] Trying Gemini with {len(frames)} frames...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
        parts = [{"text": QC_PROMPT}]
        for t, fpath in frames:
            with open(fpath, "rb") as f:
                b64data = base64.b64encode(f.read()).decode()
            parts.append({"text": f"\n--- Frame at {t}s ---"})
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64data}})
        resp = requests.post(url, json={
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000}
        }, timeout=120)
        if resp.status_code == 200:
            try:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except (KeyError, IndexError):
                pass
        if text is None:
            print(f"[gemini_qc] Gemini failed ({resp.status_code}), falling back to Grok Vision")

    if text is None:
        # Fallback to Grok Vision
        xai_key = os.environ.get("XAI_API_KEY", "")
        if not xai_key:
            for envf in [Path.home() / "protocol_pulse/.env",
                         Path(__file__).resolve().parent / ".env"]:
                if envf.exists():
                    for line in envf.read_text().split("\n"):
                        if line.startswith("XAI_API_KEY="):
                            xai_key = line.split("=", 1)[1].strip().strip("'\"")
                            break
        if not xai_key:
            return {"error": "No API key available (Gemini blocked, XAI not found)"}

        print(f"[gemini_qc] Sending {len(frames)} frames to Grok Vision...")
        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
            json={
                "model": "grok-4-0709",
                "messages": [{"role": "user", "content": content}],
                "max_tokens": 2000,
                "temperature": 0.1,
            },
            timeout=180,
        )
        if resp.status_code != 200:
            return {"error": f"Grok API error {resp.status_code}: {resp.text[:300]}"}
        text = resp.json()["choices"][0]["message"]["content"].strip()

    try:
        # Strip markdown fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        result = json.loads(text)

        # Add computed fields
        scores = [result.get(k, 0) for k in ["pip", "cold_open", "background", "voices", "audio_quality", "debug_text"]]
        result["avg_score"] = round(sum(scores) / len(scores), 1)
        result["video"] = os.path.basename(video_path)

        print(f"[gemini_qc] Grade: {result.get('overall_grade', '?')}")
        for dim in ["pip", "cold_open", "background", "voices", "audio_quality", "debug_text"]:
            print(f"  {dim}: {result.get(dim, '?')}/10")
        print(f"  avg: {result['avg_score']}/10")

        return result

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        return {"error": f"Failed to parse Gemini response: {e}", "raw": text[:500] if 'text' in dir() else ""}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 gemini_qc.py <video_path>")
        sys.exit(1)
    result = run_gemini_qc(sys.argv[1])
    print(json.dumps(result, indent=2))
