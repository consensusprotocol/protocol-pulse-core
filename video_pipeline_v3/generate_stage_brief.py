#!/usr/bin/env python3
"""
generate_stage_brief.py — Oracle Stage Timed Briefing Generator

After a Grade A video render, condenses the full episode script into a
90-second spoken monologue, renders it through the Oracle avatar (Wav2Lip),
and saves the result to data/stage_briefs/.

Usage:
    python3 generate_stage_brief.py --test          # Use latest render output
    python3 generate_stage_brief.py /path/to/output # Explicit output dir

Called automatically by daily_producer.py after quality gate passes.
"""

import argparse
import base64
import glob
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger("stage_brief")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

BASE = os.path.dirname(os.path.abspath(__file__))
BRIEFS_DIR = os.path.join(BASE, "data", "stage_briefs")
AVATAR_BASE = os.environ.get("AVATAR_BASE_URL", "http://localhost:8200")

# Claude Haiku for condensation
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

CONDENSE_SYSTEM = (
    "You are Oracle, a Bitcoin intelligence reporter. Write a punchy 90-second "
    "spoken brief (max 200 words). Cover: the top story, 2-3 key signals, one "
    "strong closing line. PBX voice: direct, confident, no fluff. No 'Hello' "
    "or 'Welcome'. Start with the strongest insight."
)


def _find_latest_output():
    """Find the most recent render output directory."""
    output_base = os.path.join(BASE, "output")
    # Look for date directories (YYYY-MM-DD)
    dirs = sorted(glob.glob(os.path.join(output_base, "2*")), reverse=True)
    for d in dirs:
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "script.json")):
            return d
    # Fallback: test directories
    test_dirs = sorted(glob.glob(os.path.join(output_base, "test_*")), reverse=True)
    for d in test_dirs:
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "script.json")):
            return d
    return None


def _load_script(output_dir):
    """Load script.json from output directory."""
    path = os.path.join(output_dir, "script.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"script.json not found in {output_dir}")
    with open(path) as f:
        return json.load(f)


def _load_selections(output_dir):
    """Load selections.json from output directory."""
    path = os.path.join(output_dir, "selections.json")
    if not os.path.exists(path):
        logger.warning("selections.json not found, proceeding without clip data")
        return {"clips": []}
    with open(path) as f:
        return json.load(f)


def _extract_dialogue_text(script):
    """Extract all host dialogue lines from script."""
    lines = []
    if script.get("cold_open"):
        lines.append(script["cold_open"])
    for seg in script.get("dialogue", []):
        if seg.get("host") == "CLIP":
            continue
        text = seg.get("text", "").strip()
        if text:
            lines.append(text)
    return "\n\n".join(lines)


def _format_clip_list(selections):
    """Format clip selections into a readable list."""
    clips = selections.get("clips", [])
    if not clips:
        return "No clips available."
    parts = []
    for c in clips:
        parts.append(
            f"- {c.get('channel', 'Unknown')}: \"{c.get('quote', '')[:120]}\""
        )
    return "\n".join(parts)


def _condense_script(dialogue_text, clip_list, episode_title):
    """Use Claude Haiku to condense the full script into a 90-second monologue."""
    if not ANTHROPIC_API_KEY:
        # Try loading from .env
        env_path = os.path.join(os.path.dirname(BASE), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.strip().split("=", 1)[1].strip("'\"")
                        os.environ["ANTHROPIC_API_KEY"] = key
                        break

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    user_prompt = (
        f"Episode: {episode_title}\n\n"
        f"Full dialogue:\n{dialogue_text}\n\n"
        f"Clips featured:\n{clip_list}\n\n"
        "Condense this into a punchy 90-second spoken brief (max 200 words)."
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 400,
            "system": CONDENSE_SYSTEM,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["content"][0]["text"].strip()
    word_count = len(text.split())
    logger.info(f"Condensed brief: {word_count} words")
    if word_count > 250:
        logger.warning(f"Brief is {word_count} words (target: 200 max)")
    return text


def _split_into_chunks(text, max_sentences=3):
    """Split text into chunks of ~max_sentences sentences for the 30s avatar limit."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current = []
    for s in sentences:
        current.append(s)
        if len(current) >= max_sentences:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def _generate_tts(text):
    """Generate TTS audio via avatar server /oracle/voice endpoint.
    Retries up to 3 times with 10s delay. Timeout 300s.
    """
    for attempt in range(1, 4):
        try:
            logger.info(f"[TTS] Attempt {attempt}/3 for {len(text)} chars")
            resp = requests.post(
                f"{AVATAR_BASE}/oracle/voice",
                json={"text": text},
                timeout=300,
            )
            resp.raise_for_status()
            logger.info(f"[TTS] OK: {len(resp.content)} bytes (attempt {attempt})")
            return resp.content
        except Exception as e:
            logger.warning(f"[TTS] Attempt {attempt}/3 failed: {e}")
            if attempt < 3:
                import time as _time
                _time.sleep(10)
    raise RuntimeError("TTS failed after 3 attempts")


def _render_avatar_chunk(audio_bytes):
    """Render a single <=30s chunk through Wav2Lip via avatar server.
    Retries up to 3 times with 10s delay. Timeout 300s.
    """
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    is_wav = audio_bytes[:4] == b"RIFF"
    content_type = "audio/wav" if is_wav else "audio/mpeg"
    for attempt in range(1, 4):
        try:
            logger.info(f"[RENDER] Avatar chunk attempt {attempt}/3 ({len(audio_bytes)} bytes)")
            resp = requests.post(
                f"{AVATAR_BASE}/generate",
                json={
                    "audio_base64": audio_b64,
                    "content_type": content_type,
                    "enable_blinks": True,
                    "enable_head_movement": True,
                    "fps": 30.0,
                },
                timeout=300,
            )
            resp.raise_for_status()
            duration = float(resp.headers.get("X-Duration", 0))
            logger.info(f"[RENDER] OK: {len(resp.content)} bytes, {duration:.1f}s (attempt {attempt})")
            return resp.content, duration
        except Exception as e:
            logger.warning(f"[RENDER] Attempt {attempt}/3 failed: {e}")
            if attempt < 3:
                import time as _time
                _time.sleep(10)
    raise RuntimeError("Avatar render failed after 3 attempts")


def _render_avatar_video(brief_text):
    """
    Render full brief as avatar video, chunking text to stay under 30s limit.
    Each chunk: TTS -> Wav2Lip -> MP4 part. Then concatenate with FFmpeg.
    """
    import subprocess
    import tempfile

    chunks = _split_into_chunks(brief_text, max_sentences=3)
    logger.info(f"Split brief into {len(chunks)} chunks")

    if len(chunks) == 1:
        # Single chunk — direct render
        audio = _generate_tts(chunks[0])
        video_bytes, duration = _render_avatar_chunk(audio)
        return video_bytes, duration

    # Multi-chunk — render each, concatenate
    tmpdir = tempfile.mkdtemp(prefix="stage_brief_")
    part_paths = []
    total_duration = 0.0

    try:
        for i, chunk in enumerate(chunks):
            logger.info(f"  Chunk {i+1}/{len(chunks)}: {len(chunk.split())} words")
            audio = _generate_tts(chunk)
            video_bytes, dur = _render_avatar_chunk(audio)
            total_duration += dur

            part_path = os.path.join(tmpdir, f"part_{i:03d}.mp4")
            with open(part_path, "wb") as f:
                f.write(video_bytes)
            part_paths.append(part_path)

        # Build concat list
        concat_list = os.path.join(tmpdir, "concat.txt")
        with open(concat_list, "w") as f:
            for p in part_paths:
                f.write(f"file '{p}'\n")

        # Concatenate with FFmpeg
        output_path = os.path.join(tmpdir, "final.mp4")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-pix_fmt", "yuv420p", "-r", "30", "-vsync", "cfr",
            "-vf", "setpts=PTS-STARTPTS",
            "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
            "-movflags", "+faststart",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"FFmpeg concat failed: {result.stderr.decode()[-500:]}")
            raise RuntimeError("FFmpeg concat failed")

        with open(output_path, "rb") as f:
            final_bytes = f.read()

        return final_bytes, total_duration

    finally:
        # Cleanup temp files
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def _post_brief_triggers():
    """Post-brief triggers: refresh transcript cache, Nostr signal, clear RAG stale flag."""
    # 1. Refresh Nostr signal cache
    try:
        signal_script = os.path.join(BASE, "fetch_signal_cache.py")
        if os.path.exists(signal_script):
            import subprocess
            subprocess.Popen(
                [sys.executable, signal_script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                cwd=BASE,
            )
            logger.info("Post-brief: Nostr signal refresh triggered")
    except Exception as e:
        logger.warning(f"Post-brief Nostr refresh failed: {e}")

    # 2. Clear RAG stale-content flag so next Oracle session gets fresh articles
    try:
        rag_flag = os.path.join(os.path.dirname(BASE), "data", "rag_stale.flag")
        if os.path.exists(rag_flag):
            os.remove(rag_flag)
            logger.info("Post-brief: RAG stale flag cleared")
    except Exception as e:
        logger.warning(f"Post-brief RAG flag clear failed: {e}")

    # 3. Touch transcript cache marker to signal freshness
    try:
        tx_marker = os.path.join(BASE, "data", "channel_archive", ".last_brief_refresh")
        with open(tx_marker, "w") as f:
            f.write(datetime.now(timezone.utc).isoformat())
        logger.info("Post-brief: transcript cache marker updated")
    except Exception as e:
        logger.warning(f"Post-brief transcript marker failed: {e}")


def generate_brief(output_dir):
    """
    Main entry point. Generates a stage brief from a render output directory.

    Args:
        output_dir: Path to output directory containing script.json + selections.json

    Returns:
        Path to generated MP4, or None on failure.
    """
    try:
        logger.info(f"Generating stage brief from: {output_dir}")
        t0 = time.time()

        # 1. Load source data
        script = _load_script(output_dir)
        selections = _load_selections(output_dir)

        episode_title = script.get("episode_title", "Pulse Check")
        dialogue_text = _extract_dialogue_text(script)
        clip_list = _format_clip_list(selections)

        if not dialogue_text:
            logger.error("No dialogue text found in script.json")
            return None

        # 2. Condense via Claude
        logger.info("Condensing script via Claude Haiku...")
        brief_text = _condense_script(dialogue_text, clip_list, episode_title)

        # 3+4. Generate TTS + render avatar video (chunked for 30s limit)
        logger.info("Rendering avatar video (chunked TTS + Wav2Lip)...")
        video_bytes, duration = _render_avatar_video(brief_text)
        logger.info(f"Avatar video: {len(video_bytes)} bytes, {duration:.1f}s")

        # 5. Save outputs
        os.makedirs(BRIEFS_DIR, exist_ok=True)
        now = datetime.now(timezone.utc)
        ts_str = now.strftime("%Y%m%d_%H%M")
        date_str = now.strftime("%Y-%m-%d")

        mp4_filename = f"brief_{ts_str}.mp4"
        mp4_path = os.path.join(BRIEFS_DIR, mp4_filename)

        with open(mp4_path, "wb") as f:
            f.write(video_bytes)

        file_size_mb = os.path.getsize(mp4_path) / (1024 * 1024)
        if file_size_mb > 150:
            logger.error(f"Brief MP4 too large: {file_size_mb:.1f}MB (max 150MB)")
            os.remove(mp4_path)
            return None

        logger.info(f"Saved: {mp4_path} ({file_size_mb:.1f}MB)")

        # 6. Write metadata JSON
        meta = {
            "title": episode_title,
            "generated_at": now.isoformat(),
            "duration": round(duration, 1),
            "mp4_path": mp4_filename,
            "mp4_url": f"/data/stage_briefs/{mp4_filename}",
            "video_url": f"/data/stage_briefs/{mp4_filename}",
            "episode_date": date_str,
            "script_summary": brief_text[:500],
            "word_count": len(brief_text.split()),
            "source_dir": os.path.basename(output_dir),
        }
        meta_path = os.path.join(BRIEFS_DIR, f"brief_{ts_str}.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        # 7. Update latest.json
        latest_path = os.path.join(BRIEFS_DIR, "latest.json")
        with open(latest_path, "w") as f:
            json.dump(meta, f, indent=2)

        # 8. Post-brief triggers: refresh transcripts, Nostr, RAG freshness
        _post_brief_triggers()

        elapsed = round(time.time() - t0, 1)
        logger.info(f"Stage brief complete in {elapsed}s: {mp4_filename}")
        return mp4_path

    except Exception as e:
        logger.error(f"Stage brief generation failed: {e}", exc_info=True)
        return None


def main():
    parser = argparse.ArgumentParser(description="Generate Oracle Stage brief")
    parser.add_argument("output_dir", nargs="?", help="Path to render output directory")
    parser.add_argument("--test", action="store_true", help="Use latest render output")
    args = parser.parse_args()

    if args.test or not args.output_dir:
        output_dir = _find_latest_output()
        if not output_dir:
            print("ERROR: No render output found in output/")
            sys.exit(1)
        print(f"Using latest output: {output_dir}")
    else:
        output_dir = args.output_dir

    if not os.path.isdir(output_dir):
        print(f"ERROR: Not a directory: {output_dir}")
        sys.exit(1)

    result = generate_brief(output_dir)
    if result:
        print(f"\nSUCCESS: {result}")
        sys.exit(0)
    else:
        print("\nFAILED: Brief generation failed (check logs)")
        sys.exit(1)


if __name__ == "__main__":
    main()
