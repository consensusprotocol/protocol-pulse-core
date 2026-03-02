#!/usr/bin/env python3
"""Daily Pulse Check Producer — production orchestrator.

Usage:
  python3 daily_producer.py               # Full daily episode → output/YYYY-MM-DD/
  python3 daily_producer.py --test        # Short test run (2-3 segs) → output/test_YYYYMMDD_HHMMSS/
  python3 daily_producer.py --style breaking   # Use breaking-news script style
"""
import os, sys, json, argparse, time, shutil, subprocess
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from script_writer import generate_script
from tts_engine import generate_all_audio
from clip_fetcher import fetch_all_clips
from assembler import assemble_episode, verify_video
from shorts_cutter import generate_shorts


# ──────────────────────────────────────────────────────────────────────────────
# Intel gather (latest articles + BTC price)
# ──────────────────────────────────────────────────────────────────────────────

def gather_intel() -> list:
    """Pull recent articles from Replit DB for script context."""
    try:
        from relay import query_db
        raw = query_db(
            "SELECT title, summary, published_at FROM articles "
            "ORDER BY published_at DESC LIMIT 10"
        )
        if raw:
            return json.loads(raw)
    except Exception as e:
        print(f"  [intel] DB fetch failed ({e}), using sample script")
    return []


def get_btc_price() -> str:
    """Fetch current BTC price from mempool.space."""
    try:
        import requests
        r = requests.get("https://mempool.space/api/v1/prices", timeout=5)
        if r.status_code == 200:
            usd = r.json().get("USD", 0)
            return f"${usd:,.0f}"
    except Exception:
        pass
    return "N/A"


# ──────────────────────────────────────────────────────────────────────────────
# Test-mode script truncation
# ──────────────────────────────────────────────────────────────────────────────

def truncate_script_for_test(script: dict, max_segments: int = 3) -> dict:
    """Limit script to max_segments for faster test runs."""
    if len(script.get("segments", [])) <= max_segments:
        return script
    truncated = dict(script)
    truncated["segments"] = script["segments"][:max_segments]
    truncated["total_estimated_duration_seconds"] = sum(
        s.get("duration_seconds", 20) for s in truncated["segments"]
    ) + 30  # + cold open/outro
    return truncated


# ──────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────────────────────────────────────

def run_pipeline(test_mode: bool = False, style: str = "default") -> bool:
    """Run the complete Pulse Check video production pipeline."""
    ts = datetime.now()
    date_str = ts.strftime("%Y%m%d")
    time_str = ts.strftime("%Y%m%d_%H%M%S")

    if test_mode:
        run_dir = os.path.join(BASE, "output", f"test_{time_str}")
    else:
        run_dir = os.path.join(BASE, "output", ts.strftime("%Y-%m-%d"))

    os.makedirs(run_dir, exist_ok=True)

    final_video = os.path.join(run_dir, f"pulse_check_{date_str}.mp4")
    timing = {}
    t_pipeline_start = time.time()

    print("\n" + "=" * 70)
    print(f"  PULSE CHECK VIDEO PIPELINE — {'TEST ' if test_mode else ''}Run {time_str}")
    print(f"  Style: {style} | Output: {run_dir}")
    print("=" * 70)

    # ── Step 1: Gather Intel ────────────────────────────────────────────────
    print("\n[STEP 1/6] GATHERING INTEL...")
    t0 = time.time()
    stories = gather_intel()
    btc_price = get_btc_price()
    print(f"  Articles: {len(stories)} | BTC: {btc_price}")
    timing["intel_gather"] = round(time.time() - t0, 2)

    # ── Step 2: Generate Script ─────────────────────────────────────────────
    print("\n[STEP 2/6] GENERATING SCRIPT...")
    t0 = time.time()
    script = generate_script(stories=stories if stories else None, style=style)
    if test_mode:
        script = truncate_script_for_test(script, max_segments=3)
        print(f"  [test] Script truncated to {len(script['segments'])} segments")

    print(f"  Title: {script.get('episode_title', 'Untitled')}")
    print(f"  Segments: {len(script.get('segments', []))}")
    print(f"  Est. duration: {script.get('total_estimated_duration_seconds', 0)}s")
    timing["script_gen"] = round(time.time() - t0, 2)

    # Save script.json to run dir
    script_path = os.path.join(run_dir, "script.json")
    with open(script_path, "w") as f:
        json.dump(script, f, indent=2)

    # ── Step 3: Generate Narration (ElevenLabs Jessica) ─────────────────────
    print("\n[STEP 3/6] GENERATING NARRATION (ElevenLabs Jessica)...")
    t0 = time.time()
    audio_dir = os.path.join(run_dir, "audio")
    audio_paths = generate_all_audio(script, audio_dir)
    seg_count = sum(1 for s in audio_paths.get("segments", []) if s and os.path.exists(s))
    print(f"  Segment audio: {seg_count}/{len(script.get('segments', []))}")
    timing["tts_gen"] = round(time.time() - t0, 2)

    # Export full narration as narration.wav for reference
    if audio_paths.get("full") and os.path.exists(audio_paths["full"]):
        narration_wav = os.path.join(run_dir, "narration.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", audio_paths["full"],
             "-c:a", "pcm_s16le", "-ar", "44100", narration_wav],
            capture_output=True, text=True
        )
        if os.path.exists(narration_wav):
            dur = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", narration_wav],
                capture_output=True, text=True
            ).stdout.strip() or "0")
            print(f"  narration.wav: {dur:.1f}s exported")

    # ── Step 4: Fetch B-roll (Pexels) ───────────────────────────────────────
    print("\n[STEP 4/6] FETCHING PEXELS B-ROLL...")
    t0 = time.time()
    clip_dir = os.path.join(run_dir, "clips")
    clip_data = fetch_all_clips(script, clip_dir)
    total_clips = sum(len(s.get("clips", [])) for s in clip_data.get("segments", []))
    print(f"  Clips fetched: {total_clips} across {len(clip_data.get('segments', []))} segments")
    timing["pexels_fetch"] = round(time.time() - t0, 2)

    # ── Step 5: Assemble Video ──────────────────────────────────────────────
    print("\n[STEP 5/6] ASSEMBLING VIDEO (xfade transitions)...")
    t0 = time.time()
    result = assemble_episode(script, audio_paths, clip_data, final_video)
    timing["assembly"] = round(time.time() - t0, 2)

    if not result or not os.path.exists(final_video):
        print("\n  [FAIL] Assembly failed — aborting")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        return False

    # ── Step 6: Verify + Generate Shorts ───────────────────────────────────
    print("\n[STEP 6/6] VERIFYING + GENERATING SHORTS...")
    t0 = time.time()
    passed = verify_video(final_video)

    # Generate shorts directly in the run dir (not in a subdirectory)
    work_dir = os.path.join(run_dir, "work")
    shorts = generate_shorts(work_dir, script, run_dir)
    timing["verify_shorts"] = round(time.time() - t0, 2)

    # Rename shorts to short_1.mp4, short_2.mp4, etc.
    for i, s in enumerate(shorts):
        dest = os.path.join(run_dir, f"short_{i+1}.mp4")
        if os.path.exists(s) and s != dest:
            shutil.move(s, dest)
    print(f"  Shorts generated: {len(shorts)}")

    # ── Summary ─────────────────────────────────────────────────────────────
    timing["total"] = round(time.time() - t_pipeline_start, 2)

    # Always capture video stats for report
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", final_video],
        capture_output=True, text=True
    )
    try:
        info = json.loads(r.stdout)
        fmt = info.get("format", {})
        streams = info.get("streams", [])
        vid = next((s for s in streams if s.get("codec_type") == "video"), {})
        aud = next((s for s in streams if s.get("codec_type") == "audio"), {})
        dur = float(fmt.get("duration", 0))
        sz = int(fmt.get("size", 0)) / 1024 / 1024
        timing["video_duration"] = round(dur, 1)
        timing["video_size_mb"] = round(sz, 1)
    except Exception:
        vid, aud, dur, sz = {}, {}, 0, 0

    print("\n" + "=" * 70)
    if passed:
        print(f"  SUCCESS: {final_video}")
        print(f"  Video: {vid.get('width')}x{vid.get('height')} {vid.get('codec_name')} {dur:.1f}s")
        print(f"  Audio: {aud.get('codec_name')} {aud.get('sample_rate')}Hz")
        print(f"  Size: {sz:.1f}MB")
    else:
        print(f"  WARNING: Verification had minor failures — video is usable")

    print(f"\n  TIMING BREAKDOWN:")
    for step, secs in timing.items():
        if step not in ("video_duration", "video_size_mb"):
            print(f"    {step:20s}: {secs:.1f}s")
    print(f"\n  Output directory: {run_dir}")
    print("=" * 70)

    _write_timing_report(run_dir, timing, t_pipeline_start, success=passed)
    return passed


def _write_timing_report(run_dir: str, timing: dict, t_start: float, success: bool):
    """Write a timing_report.txt to the run directory."""
    report_path = os.path.join(run_dir, "timing_report.txt")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"PULSE CHECK VIDEO PIPELINE — Timing Report",
        f"Generated: {ts}",
        f"Status: {'SUCCESS' if success else 'FAILED'}",
        "",
        "STEP TIMINGS:",
    ]
    for step, val in timing.items():
        if step in ("video_duration", "video_size_mb"):
            continue
        lines.append(f"  {step:<22}: {val:.1f}s")
    lines += [
        "",
        "OUTPUT STATS:",
        f"  video_duration_s     : {timing.get('video_duration', 'N/A')}",
        f"  video_size_mb        : {timing.get('video_size_mb', 'N/A')}",
        f"  total_wall_time_s    : {time.time() - t_start:.1f}",
        "",
        f"Output directory: {run_dir}",
    ]
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  timing_report.txt written")


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pulse Check Daily Video Producer")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: 2-3 segments, output to test_YYYYMMDD_HHMMSS/")
    parser.add_argument("--style", "-s", default="default",
                        choices=["default", "breaking"],
                        help="Script style (default | breaking)")
    args = parser.parse_args()

    success = run_pipeline(test_mode=args.test, style=args.style)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
