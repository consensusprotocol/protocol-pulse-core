#!/usr/bin/env python3
"""Daily Pulse Check Producer V4 — 14-step dual-host pipeline.

Usage:
  python3 daily_producer.py               # Full daily episode
  python3 daily_producer.py --test        # Short test run
  python3 daily_producer.py --style breaking
"""
import os, sys, json, argparse, time, shutil, subprocess
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from script_writer import generate_script
from tts_engine import generate_dialogue_audio
from clip_fetcher import fetch_all_clips
from assembler import assemble_episode, verify_video
from shorts_cutter import generate_shorts
from thumbnail_gen import generate_thumbnail
from chapters import generate_chapters
from podcast_feed import extract_podcast_audio, generate_rss_item
from newsletter_embed import generate_email_html, save_newsletter_html


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: GATHER — pull recent articles + BTC price
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
    return "$97,000"  # Fallback


# ──────────────────────────────────────────────────────────────────────────────
# Test-mode dialogue truncation
# ──────────────────────────────────────────────────────────────────────────────

def truncate_for_test(script: dict, max_lines: int = 8) -> dict:
    """Limit dialogue to max_lines for faster test runs."""
    dialogue = script.get("dialogue", [])
    if len(dialogue) <= max_lines:
        return script
    truncated = dict(script)
    truncated["dialogue"] = dialogue[:max_lines]
    # Keep only non-CLIP lines for duration estimate
    speech_lines = [d for d in truncated["dialogue"] if d.get("host") != "CLIP"]
    truncated["total_estimated_duration_seconds"] = len(speech_lines) * 8
    return truncated


# ──────────────────────────────────────────────────────────────────────────────
# Main V4 pipeline — 14 steps
# ──────────────────────────────────────────────────────────────────────────────

def run_pipeline(test_mode: bool = False, style: str = "default") -> bool:
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
    print(f"  PULSE CHECK V4 — DUAL HOST PIPELINE")
    print(f"  {'TEST ' if test_mode else ''}Run {time_str} | Style: {style}")
    print(f"  Output: {run_dir}")
    print("=" * 70)

    # ── Step 1: GATHER ─────────────────────────────────────────────────────
    print("\n[STEP 1/14] GATHERING INTEL...")
    t0 = time.time()
    stories = gather_intel()
    btc_price = get_btc_price()
    print(f"  Articles: {len(stories)} | BTC: {btc_price}")
    timing["1_gather"] = round(time.time() - t0, 2)

    # ── Step 2: TRANSCRIBE (placeholder — for future Spaces integration) ──
    print("\n[STEP 2/14] TRANSCRIBE (skipped — no live audio)")
    timing["2_transcribe"] = 0.0

    # ── Step 3: SELECT (story selection done in script generation) ─────────
    print("\n[STEP 3/14] SELECT (integrated with script generation)")
    timing["3_select"] = 0.0

    # ── Step 4: DOWNLOAD YouTube clips ────────────────────────────────────
    # (We need the script first to know which clips to fetch, so we
    #  generate the script first, then fetch clips)

    # ── Step 6: SCRIPT — generate dual-host dialogue ─────────────────────
    print("\n[STEP 6/14] GENERATING DUAL-HOST SCRIPT...")
    t0 = time.time()
    script = generate_script(stories=stories if stories else None,
                             style=style, btc_price=btc_price)
    if test_mode:
        script = truncate_for_test(script, max_lines=8)
        print(f"  [test] Dialogue truncated to {len(script['dialogue'])} lines")

    print(f"  Title: {script.get('episode_title', 'Untitled')}")
    print(f"  Dialogue lines: {len(script.get('dialogue', []))}")
    print(f"  Est. duration: {script.get('total_estimated_duration_seconds', 0)}s")
    timing["6_script"] = round(time.time() - t0, 2)

    # Save script.json
    script_path = os.path.join(run_dir, "script.json")
    with open(script_path, "w") as f:
        json.dump(script, f, indent=2)
    print(f"  script.json saved")

    # ── Step 4 (cont): DOWNLOAD YouTube clips based on script ────────────
    print("\n[STEP 4/14] FETCHING CLIPS (YouTube + Pexels)...")
    t0 = time.time()
    clip_dir = os.path.join(run_dir, "clips")
    clip_data = fetch_all_clips(script, clip_dir)
    yt_count = len(clip_data.get("yt_clips", {}))
    broll_count = len(clip_data.get("broll", []))
    print(f"  YouTube clips: {yt_count} | Pexels B-roll: {broll_count}")
    timing["4_download"] = round(time.time() - t0, 2)

    # ── Step 5: SCREENSHOT (placeholder for article screenshots) ──────────
    print("\n[STEP 5/14] SCREENSHOT (skipped — not needed for test)")
    timing["5_screenshot"] = 0.0

    # ── Step 7: TTS — dual-host dialogue audio ───────────────────────────
    print("\n[STEP 7/14] GENERATING DUAL-HOST AUDIO (ElevenLabs)...")
    t0 = time.time()
    audio_dir = os.path.join(run_dir, "audio")
    audio_data = generate_dialogue_audio(script["dialogue"], audio_dir)
    successful = sum(1 for l in audio_data.get("lines", [])
                     if l.get("path") and os.path.exists(l.get("path", "")))
    total_lines = len(script["dialogue"])
    print(f"  Audio lines: {successful}/{total_lines}")
    print(f"  Total duration: {audio_data.get('total_duration', 0):.1f}s")
    timing["7_tts"] = round(time.time() - t0, 2)

    # ── Step 8: ASSEMBLE — build the video ───────────────────────────────
    print("\n[STEP 8/14] ASSEMBLING VIDEO...")
    t0 = time.time()
    result = assemble_episode(script, audio_data, clip_data, final_video,
                              btc_price=btc_price)
    timing["8_assemble"] = round(time.time() - t0, 2)

    if not result or not os.path.exists(final_video):
        print("\n  [FAIL] Assembly failed — aborting")
        _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
        return False

    # ── Step 9: SHORTS — vertical cuts ───────────────────────────────────
    print("\n[STEP 9/14] GENERATING SHORTS...")
    t0 = time.time()
    work_dir = os.path.join(run_dir, "work")
    shorts = generate_shorts(work_dir, script, run_dir, max_shorts=3)
    print(f"  Shorts generated: {len(shorts)}")
    timing["9_shorts"] = round(time.time() - t0, 2)

    # ── Step 10: THUMBNAIL ───────────────────────────────────────────────
    print("\n[STEP 10/14] GENERATING THUMBNAIL...")
    t0 = time.time()
    thumb_data = script.get("thumbnail", {})
    thumb_path = os.path.join(run_dir, "thumbnail.png")
    generate_thumbnail(
        thumb_data.get("headline", script.get("episode_title", "PULSE CHECK")),
        thumb_data.get("subtext", ""),
        thumb_path,
    )
    timing["10_thumbnail"] = round(time.time() - t0, 2)

    # ── Step 11: CHAPTERS ────────────────────────────────────────────────
    print("\n[STEP 11/14] GENERATING CHAPTERS...")
    t0 = time.time()
    chapters_path = os.path.join(run_dir, "chapters.txt")
    generate_chapters(script, audio_data, chapters_path)
    timing["11_chapters"] = round(time.time() - t0, 2)

    # ── Step 12: PODCAST — extract audio MP3 ─────────────────────────────
    print("\n[STEP 12/14] EXTRACTING PODCAST AUDIO...")
    t0 = time.time()
    podcast_path = os.path.join(run_dir, "podcast.mp3")
    extract_podcast_audio(final_video, podcast_path)
    timing["12_podcast"] = round(time.time() - t0, 2)

    # ── Step 13: NEWSLETTER — generate email HTML ────────────────────────
    print("\n[STEP 13/14] GENERATING NEWSLETTER...")
    t0 = time.time()
    email_html = generate_email_html(
        script.get("episode_title", "Pulse Check"),
        segments_summary=script.get("segments_summary", []),
        btc_price=btc_price,
    )
    newsletter_path = os.path.join(run_dir, "newsletter.html")
    save_newsletter_html(email_html, newsletter_path)
    timing["13_newsletter"] = round(time.time() - t0, 2)

    # ── Step 14: OUTPUT — verify + summarize ─────────────────────────────
    print("\n[STEP 14/14] VERIFYING OUTPUT...")
    t0 = time.time()
    passed = verify_video(final_video)
    timing["14_verify"] = round(time.time() - t0, 2)

    # ── Summary ──────────────────────────────────────────────────────────
    timing["total"] = round(time.time() - t_pipeline_start, 2)

    # Video stats
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", final_video],
        capture_output=True, text=True,
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
    print(f"  PULSE CHECK V4 — {'SUCCESS' if passed else 'COMPLETE (warnings)'}")
    print(f"  Video: {vid.get('width')}x{vid.get('height')} {vid.get('codec_name')} {dur:.1f}s")
    print(f"  Audio: {aud.get('codec_name')} {aud.get('sample_rate')}Hz")
    print(f"  Size:  {sz:.1f}MB")

    # Output manifest
    outputs = {
        "video": final_video,
        "shorts": [os.path.join(run_dir, f"short_{i+1}.mp4") for i in range(len(shorts))],
        "thumbnail": thumb_path,
        "chapters": chapters_path,
        "podcast": podcast_path,
        "newsletter": newsletter_path,
        "script": script_path,
    }

    print(f"\n  OUTPUT FILES:")
    for name, path in outputs.items():
        if isinstance(path, list):
            for p in path:
                exists = "✓" if os.path.exists(p) else "✗"
                print(f"    {exists} {os.path.basename(p)}")
        else:
            exists = "✓" if os.path.exists(path) else "✗"
            print(f"    {exists} {os.path.basename(path)}")

    print(f"\n  TIMING:")
    for step, secs in timing.items():
        if step not in ("video_duration", "video_size_mb"):
            print(f"    {step:20s}: {secs:.1f}s")
    print(f"\n  Output: {run_dir}")
    print("=" * 70)

    _write_timing_report(run_dir, timing, t_pipeline_start, success=passed)

    # Save output manifest
    manifest_path = os.path.join(run_dir, "manifest.json")
    manifest = {
        "version": "v4",
        "episode_title": script.get("episode_title", ""),
        "btc_price": btc_price,
        "test_mode": test_mode,
        "timestamp": time_str,
        "outputs": {k: (v if isinstance(v, list) else [v]) for k, v in outputs.items()},
        "timing": timing,
        "success": passed,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return passed


def _write_timing_report(run_dir: str, timing: dict, t_start: float, success: bool):
    report_path = os.path.join(run_dir, "timing_report.txt")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "PULSE CHECK V4 — Timing Report",
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
    ]
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pulse Check V4 — Dual Host Video Producer")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: truncated dialogue, test output dir")
    parser.add_argument("--style", "-s", default="default",
                        choices=["default", "breaking"],
                        help="Script style (default | breaking)")
    args = parser.parse_args()
    success = run_pipeline(test_mode=args.test, style=args.style)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
