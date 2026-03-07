#!/usr/bin/env python3
"""Master orchestrator for Pulse Check video pipeline."""
import os, sys, json, argparse, time, shutil
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from script_writer import generate_script
from tts_engine import generate_all_audio
from clip_fetcher import fetch_all_clips
from assembler import assemble_episode, verify_video
from shorts_cutter import generate_shorts


def run_pipeline(output_path: str, style: str = "default") -> bool:
    """Run the complete video pipeline."""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(BASE, "output", f"run_{run_id}")
    os.makedirs(run_dir, exist_ok=True)

    print("\n" + "=" * 70)
    print(f"  PULSE CHECK VIDEO PIPELINE — Run {run_id}")
    print(f"  Style: {style}")
    print(f"  Output: {output_path}")
    print("=" * 70)

    # ─── Step 1: Generate Script ───
    print("\n[STEP 1/5] GENERATING SCRIPT...")
    t0 = time.time()
    script = generate_script(style=style)
    print(f"  Title: {script.get('episode_title', 'Untitled')}")
    print(f"  Segments: {len(script.get('segments', []))}")
    print(f"  Est. duration: {script.get('total_estimated_duration_seconds', 0)}s")
    print(f"  Time: {time.time()-t0:.1f}s")

    # Save script
    with open(os.path.join(run_dir, "script.json"), "w") as f:
        json.dump(script, f, indent=2)

    # ─── Step 2: Generate TTS Audio ───
    print("\n[STEP 2/5] GENERATING TTS AUDIO...")
    t0 = time.time()
    audio_dir = os.path.join(run_dir, "audio")
    audio_paths = generate_all_audio(script, audio_dir)
    print(f"  Audio files: {sum(1 for v in audio_paths.values() if isinstance(v, str) and os.path.exists(v))}")
    seg_count = sum(1 for s in audio_paths.get('segments', []) if s and os.path.exists(s))
    print(f"  Segment audio: {seg_count}/{len(script.get('segments', []))}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # ─── Step 3: Fetch/Generate Clips ───
    print("\n[STEP 3/5] FETCHING/GENERATING CLIPS...")
    t0 = time.time()
    clip_dir = os.path.join(run_dir, "clips")
    clip_data = fetch_all_clips(script, clip_dir)
    extracted_clips = {}
    for rk, ci in clip_data.get("yt_clips", {}).items():
        try: rank = int(rk)
        except: rank = len(extracted_clips) + 1
        if isinstance(ci, list): ci = ci[0] if ci and isinstance(ci[0], dict) else {"path": ""}
        if isinstance(ci, dict): extracted_clips[rank] = ci
    print(f"  YouTube clips: {len(extracted_clips)}")
    print(f"  Pexels B-roll: {len(clip_data.get('broll', []))}")
    print(f"  Time: {time.time()-t0:.1f}s")

    # ─── Step 4: Assemble Video ───
    print("\n[STEP 4/5] ASSEMBLING VIDEO...")
    t0 = time.time()
    # FIX 5: Fetch BTC price and pass to assembler
    btc_price = "N/A"
    try:
        import urllib.request
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
            btc_price = f"${data['bitcoin']['usd']:,.0f}"
    except Exception:
        try:
            url2 = "https://mempool.space/api/v1/prices"
            with urllib.request.urlopen(url2, timeout=5) as r2:
                data = json.loads(r2.read())
                btc_price = f"${data.get('USD', 0):,.0f}"
        except Exception:
            pass
    print(f"  BTC Price: {btc_price}")
    # FIX 6: Pass broll clips to assembler
    broll_clips = clip_data.get("broll", [])
    result = assemble_episode(script, audio_paths, extracted_clips, output_path,
                              btc_price=btc_price, broll_clips=broll_clips)
    print(f"  Time: {time.time()-t0:.1f}s")

    if not result:
        print("\n  [FAIL] Assembly failed!")
        return False

    # ─── Step 5: Verify ───
    print("\n[STEP 5/5] VERIFYING OUTPUT...")
    passed = verify_video(output_path)

    # ─── Generate Shorts ───
    work_dir = os.path.join(os.path.dirname(output_path), "work")
    shorts_dir = os.path.join(BASE, "output", "shorts")
    print("\n[BONUS] GENERATING VERTICAL SHORTS...")
    shorts = generate_shorts(work_dir, script, shorts_dir)
    print(f"  Shorts generated: {len(shorts)}")

    # Summary
    print("\n" + "=" * 70)
    if passed:
        print(f"  SUCCESS: {output_path}")
        dur = 0
        sz = 0
        try:
            import subprocess
            r = subprocess.run(
                f"ffprobe -v error -show_entries format=duration,size -of csv=p=0 '{output_path}'",
                shell=True, capture_output=True, text=True
            )
            parts = r.stdout.strip().split(",")
            dur = float(parts[0]) if parts else 0
            sz = int(parts[1]) if len(parts) > 1 else 0
        except:
            pass
        print(f"  Duration: {dur:.1f}s | Size: {sz/1024/1024:.1f}MB")
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
    args = parser.parse_args()

    if args.output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = os.path.join(BASE, "output", f"pulse_check_{ts}.mp4")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    success = run_pipeline(args.output, args.style)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
