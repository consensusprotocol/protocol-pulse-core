#!/usr/bin/env python3
"""Master orchestrator for Pulse Check video pipeline — V5 real content."""
import os, sys, json, argparse, time, shutil
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from channel_scanner import scan_all_channels
from clip_selector import select_clips
from clip_extractor import extract_all as extract_clips
from script_writer import generate_from_clips, generate_script
from tts_engine import generate_all_audio
from clip_fetcher import fetch_all_clips
from assembler import assemble_episode, verify_video
from shorts_cutter import generate_shorts


def _load_cached_transcripts() -> list:
    """Load videos from cached transcript files (skip scan + transcription)."""
    transcript_dir = os.path.join(BASE, "transcripts")
    videos = []
    if not os.path.isdir(transcript_dir):
        return videos
    for fname in os.listdir(transcript_dir):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(transcript_dir, fname)) as f:
                data = json.load(f)
            vid = fname.replace(".json", "")
            videos.append({
                "video_id": vid,
                "title": data.get("title", vid),
                "channel": data.get("channel", "Unknown"),
                "duration": data.get("duration", 0),
                "upload_date": "",
                "url": f"https://www.youtube.com/watch?v={vid}",
                "transcript_text": data.get("text", ""),
                "timestamped_text": data.get("timestamped_text", ""),
            })
        except Exception:
            continue
    return videos


def run_pipeline(output_path: str, style: str = "default", cached_only: bool = False) -> bool:
    """Run the complete V5 video pipeline with real content."""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(BASE, "output", f"run_{run_id}")
    os.makedirs(run_dir, exist_ok=True)

    print("\n" + "=" * 70)
    print(f"  PULSE CHECK V5 PIPELINE — Run {run_id}")
    print(f"  Style: {style}")
    print(f"  Output: {output_path}")
    if cached_only:
        print(f"  Mode: CACHED TRANSCRIPTS ONLY (skip scan)")
    print("=" * 70)

    # ─── BTC Price (fetch early, used everywhere) ───
    btc_price = "N/A"
    try:
        import urllib.request as _ur
        with _ur.urlopen("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5) as r:
            btc_price = f"${json.loads(r.read())['bitcoin']['usd']:,.0f}"
    except Exception:
        try:
            with _ur.urlopen("https://mempool.space/api/v1/prices", timeout=5) as r:
                btc_price = f"${json.loads(r.read()).get('USD', 0):,.0f}"
        except Exception:
            pass
    print(f"  BTC Price: {btc_price}")

    # ─── Step 1: Scan channels + transcribe ───
    if cached_only:
        print("\n[STEP 1/7] LOADING CACHED TRANSCRIPTS...")
        t0 = time.time()
        videos = _load_cached_transcripts()
    else:
        print("\n[STEP 1/7] SCANNING BITCOIN YOUTUBE CHANNELS...")
        t0 = time.time()
        videos = scan_all_channels()
    print(f"  Videos scanned: {len(videos)}")
    print(f"  With transcripts: {sum(1 for v in videos if v.get('transcript_text'))}")
    print(f"  Time: {time.time()-t0:.1f}s")

    if not videos or not any(v.get('transcript_text') for v in videos):
        print("  [WARN] No transcripts — falling back to legacy script")
        script = generate_script(style=style)
        selections = {}
        extracted_clips = {}
    else:
        # ─── Step 2: Select best clips ───
        print("\n[STEP 2/6] SELECTING BEST CLIPS (Claude EP)...")
        t0 = time.time()
        selections = select_clips(videos)
        clips = selections.get("clips", [])
        print(f"  Clips selected: {len(clips)}")
        for i, c in enumerate(clips, 1):
            print(f"    {i}. {c.get('channel','?')} — {c.get('video_title', c.get('title','?'))[:60]}")
        print(f"  Time: {time.time()-t0:.1f}s")

        if not clips:
            print("  [WARN] No clips selected — falling back")
            script = generate_script(style=style)
            extracted_clips = {}
        else:
            # ─── Step 2b: Extract clip segments from YouTube ───
            print("\n[STEP 2b/7] EXTRACTING CLIP SEGMENTS (yt-dlp + ffmpeg)...")
            t0 = time.time()
            yt_clip_dir = os.path.join(run_dir, "yt_clips")
            extracted_clips = extract_clips(selections, yt_clip_dir)
            print(f"  Clips extracted: {len(extracted_clips)}")
            for rank, ci in sorted(extracted_clips.items()):
                print(f"    #{rank}: {ci.get('channel','?')} — {ci.get('duration',0):.1f}s")
            print(f"  Time: {time.time()-t0:.1f}s")

            # ─── Step 3: Generate script from clips ───
            print("\n[STEP 3/7] WRITING HOST DIALOGUE...")
            t0 = time.time()
            script = generate_from_clips(selections, btc_price=btc_price)
            seg_count = len(script.get("segments", []))
            word_count = sum(len(s.get("text", "").split()) for s in script.get("segments", []))
            print(f"  Segments: {seg_count}")
            print(f"  Words: {word_count}")
            print(f"  Title: {script.get('episode_title', '?')}")
            print(f"  Time: {time.time()-t0:.1f}s")

    # Save script
    with open(os.path.join(run_dir, "script.json"), "w") as f:
        json.dump(script, f, indent=2)

    # ─── Step 4: TTS ───
    print("\n[STEP 4/7] GENERATING TTS AUDIO (ElevenLabs)...")
    t0 = time.time()
    audio_dir = os.path.join(run_dir, "audio")
    audio_paths = generate_all_audio(script, audio_dir)
    seg_count = sum(1 for s in audio_paths.get("segments", []) if s and os.path.exists(s))
    print(f"  Audio segments: {seg_count}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # ─── Step 5: Fetch B-roll ───
    print("\n[STEP 5/7] FETCHING B-ROLL CLIPS...")
    t0 = time.time()
    clip_dir = os.path.join(run_dir, "clips")
    clip_data = fetch_all_clips(script, clip_dir)
    # Merge any yt_clips from fetcher (legacy path) into extracted_clips
    for rk, ci in clip_data.get("yt_clips", {}).items():
        try: rank = int(rk)
        except: rank = len(extracted_clips) + 1
        if rank not in extracted_clips:
            if isinstance(ci, list): ci = ci[0] if ci and isinstance(ci[0], dict) else {"path": ""}
            if isinstance(ci, dict): extracted_clips[rank] = ci
    print(f"  YouTube clips (total): {len(extracted_clips)}")
    print(f"  Pexels B-roll: {len(clip_data.get('broll', []))}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # ─── Step 5b: X Spaces Segment Injection ───
    try:
        from utils.spaces_pipeline import get_latest_spaces_segment
        spaces_seg = get_latest_spaces_segment(max_age_hours=6)
        if spaces_seg:
            segments = script.get("segments", [])
            # Insert before last segment (wrap/outro)
            if segments:
                segments.insert(-1, spaces_seg)
            else:
                segments.append(spaces_seg)
            script["segments"] = segments
            print(f"  X Spaces segment injected: {spaces_seg['space_title']}")
        else:
            print("  No fresh X Spaces content — skipping injection")
    except Exception as e:
        print(f"  X Spaces injection skipped: {e}")

    # ─── Step 6: Assemble ───
    print("\n[STEP 6/7] ASSEMBLING VIDEO (Black Diamond)...")
    t0 = time.time()
    broll_clips = clip_data.get("broll", [])
    result = assemble_episode(script, audio_paths, extracted_clips, output_path,
                              btc_price=btc_price, broll_clips=broll_clips)
    print(f"  Time: {time.time()-t0:.1f}s")

    if not result:
        print("\n  [FAIL] Assembly failed!")
        return False

    # ─── Step 7: Verify ───
    print("\n[STEP 7/7] VERIFYING OUTPUT...")
    passed = verify_video(output_path)

    # ─── Step 8: Grok QC (MANDATORY — never skip) ────────────────────────
    if passed and os.path.exists(output_path):
        print("\n[STEP 8/8] GROK-4 VISION FORENSIC QC...")
        import subprocess as _sp
        import re as _re
        xai_key = os.environ.get("XAI_API_KEY", "")
        if xai_key:
            qc_script = os.path.join(os.path.dirname(BASE), "utils", "grok_qc_v2.py")
            if os.path.exists(qc_script):
                t0 = time.time()
                qc_result = _sp.run(
                    ["python3", qc_script, "--video", output_path, "--interval", "5", "--batch-size", "20"],
                    capture_output=True, text=True, timeout=900,
                    env={**os.environ, "XAI_API_KEY": xai_key}
                )
                elapsed = time.time() - t0
                report_path = None
                for line in qc_result.stdout.split("\n"):
                    if "MASTER_QC_REPORT.md" in line:
                        candidate = line.strip().split()[-1]
                        if os.path.exists(candidate):
                            report_path = candidate
                grade = "?"
                if report_path and os.path.exists(report_path):
                    rtext = open(report_path).read()
                    m = _re.search(r"GRADE:\s*([A-F][+-]?)", rtext)
                    if m:
                        grade = m.group(1)
                print(f"  QC complete in {elapsed:.0f}s — Grade: {grade}")
                if report_path:
                    print(f"  Report: {report_path}")
                grade_map = {"A": "✅ PUBLISH READY", "B": "✅ PUBLISH READY",
                             "C": "⚠️  MINOR ISSUES", "D": "❌ DO NOT PUBLISH",
                             "F": "❌ DO NOT PUBLISH"}
                status = grade_map.get(grade[0] if grade else "?", "⚠️  CHECK REPORT")
                print(f"  STATUS: {status}")
            else:
                print(f"  WARN: grok_qc_v2.py not found at {qc_script}")
        else:
            print("  WARN: XAI_API_KEY not set — Grok QC skipped")
    # ─────────────────────────────────────────────────────────────────────

    # ─── Generate Shorts ───
    work_dir = os.path.join(os.path.dirname(output_path), "work")
    shorts_dir = os.path.join(BASE, "output", "shorts")
    print("\n[BONUS] GENERATING VERTICAL SHORTS...")
    shorts = generate_shorts(script, shorts_dir)
    print(f"  Shorts generated: {len(shorts)}")

    # Summary
    print("\n" + "=" * 70)
    if passed:
        print(f"  SUCCESS: {output_path}")
        try:
            import subprocess
            r = subprocess.run(
                f"ffprobe -v error -show_entries format=duration,size -of csv=p=0 '{output_path}'",
                shell=True, capture_output=True, text=True
            )
            parts = r.stdout.strip().split(",")
            dur = float(parts[0]) if parts else 0
            sz = int(parts[1]) if len(parts) > 1 else 0
            print(f"  Duration: {dur:.1f}s | Size: {sz/1024/1024:.1f}MB")
        except:
            pass
    else:
        print(f"  WARNING: Verification had failures, but video may still be usable")
    print("=" * 70)

    return passed


def main():
    parser = argparse.ArgumentParser(description="Pulse Check Video Pipeline")
    parser.add_argument("--output", "-o", default=None, help="Output MP4 path")
    parser.add_argument("--style", "-s", default="default", choices=["default", "breaking"],
                        help="Script style")
    parser.add_argument("--date", default="today", help="Date for content (unused in V1)")
    parser.add_argument("--cached-only", action="store_true",
                        help="Use cached transcripts only (skip channel scan + Whisper)")
    args = parser.parse_args()

    if args.output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = os.path.join(BASE, "output", f"pulse_check_{ts}.mp4")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    success = run_pipeline(args.output, args.style, cached_only=args.cached_only)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
