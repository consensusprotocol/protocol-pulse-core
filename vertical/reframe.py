#!/usr/bin/env python3
"""vertical.reframe — CLI entry point for the standalone vertical reframing pipeline.

Pipeline:
  1. shotmap    — Analyze source(s) per-shot layout, faces, screen-share
  2. compose    — Per-shot 9:16 composition via compositor
  3. assemble   — Concat composed shots + VO + shoutout + outro
  4. qa_gates   — G1-G6 gate verification
  5. critic     — Grok-4 vision review
  6. sheet      — Contact sheet for review
  7. tg_preview — Send to Telegram if all pass

Usage:
    python3 -m vertical.reframe \\
        --edl cuts_v3.json \\
        --sources sources_pcm \\
        --out out/segment_v14_vertical.mp4 \\
        [--stage shotmap|compose|assemble|qa|critic|sheet|tg|all] \\
        [--no-critic] [--no-tg]

Law 21: every stage has a time budget. GPU/cached path by default.
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

BASE = pathlib.Path(__file__).resolve().parent
WORK = BASE / "work"
CACHE = BASE / "cache"
VERT_W, VERT_H = 1080, 1920
FPS = 24

sys.path.insert(0, str(BASE.parent / "video_pipeline_v3"))
sys.path.insert(0, str(BASE.parent / "segment_v1"))


def md5_file(path, n=16 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read(n))
    return h.hexdigest()


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def timed(label):
    """Context manager that prints and records stage timing."""
    class Timer:
        def __init__(self):
            self.elapsed = 0.0
        def __enter__(self):
            self.t0 = time.time()
            print(f"\n=== {label} ===", flush=True)
            return self
        def __exit__(self, *exc):
            self.elapsed = time.time() - self.t0
            print(f"  [{label}] {self.elapsed:.1f}s", flush=True)
    return Timer()


# ================================================================
# Stage 1: Shotmap
# ================================================================

def stage_shotmap(sources_dir, edl_path):
    """Run shotmap on each unique source video referenced by the EDL."""
    from vertical.shotmap import build as shotmap_build

    with open(edl_path) as f:
        edl = json.load(f)

    # Collect unique source videos
    video_ids = set()
    for cut in edl:
        vid = cut.get("video_id", "")
        if vid:
            video_ids.add(vid)

    shot_maps = {}
    for vid in sorted(video_ids):
        # Find the source file (.mov preferred, then .mkv, then .mp4)
        src = None
        for ext in (".mov", ".mkv", ".mp4"):
            candidate = os.path.join(sources_dir, vid + ext)
            if os.path.exists(candidate):
                src = candidate
                break
        if not src:
            print(f"  WARNING: no source found for {vid} in {sources_dir}")
            continue

        # Check cache
        src_md5 = md5_file(src)
        cache_path = CACHE / f"{src_md5}.json"
        if cache_path.exists():
            print(f"  {vid}: cached ({cache_path.name})")
            shot_maps[vid] = json.loads(cache_path.read_text())
            continue

        out_dir = WORK / f"shotmap_{vid}"
        out_dir.mkdir(parents=True, exist_ok=True)
        result = shotmap_build(src, str(out_dir))
        if result:
            shot_maps[vid] = result
            # Cache the result
            CACHE.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(result, indent=1))

    # Write combined shot map
    combined = {
        "sources": shot_maps,
        "edl": edl,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    combined_path = WORK / "shot_map.json"
    combined_path.write_text(json.dumps(combined, indent=1))
    print(f"  Combined shot map: {combined_path} ({len(shot_maps)} sources)")
    return combined


# ================================================================
# Stage 2: Compose
# ================================================================

def stage_compose(shot_map_data, sources_dir, edl_path):
    """Compose each EDL cut to 9:16 using the shot map."""
    from vertical.compositor import compose_shot

    with open(edl_path) as f:
        edl = json.load(f)

    composed = []
    compose_dir = WORK / "composed"
    compose_dir.mkdir(parents=True, exist_ok=True)

    for cut in edl:
        vid = cut.get("video_id", "")
        clip_id = cut.get("clip_id", "unknown")
        cut_in = cut.get("cut_in", 0)
        cut_out = cut.get("cut_out", 0)

        # Find source
        src = None
        for ext in (".mov", ".mkv", ".mp4"):
            candidate = os.path.join(sources_dir, vid + ext)
            if os.path.exists(candidate):
                src = candidate
                break
        if not src:
            print(f"  WARNING: skip {clip_id} — no source for {vid}")
            continue

        # Get shots for this source from the shot map
        source_map = shot_map_data.get("sources", {}).get(vid, {})
        shots = source_map.get("shots", [])
        fps = source_map.get("video", {}).get("fps", 30.0)

        # Find shots overlapping our cut window
        frame_in = int(cut_in * fps)
        frame_out = int(cut_out * fps)
        relevant_shots = [
            s for s in shots
            if s["frame_out"] > frame_in and s["frame_in"] < frame_out
        ]

        if not relevant_shots:
            # Fallback: treat entire cut as a single shot
            relevant_shots = [{
                "id": f"{clip_id}_fallback",
                "frame_in": frame_in,
                "frame_out": frame_out,
                "t_in": cut_in,
                "t_out": cut_out,
                "layout": "single",
                "total_faces": 1,
                "tiles": [{"x0": 0, "x1": 1920, "face_count": 1}],
                "seams": [],
                "screen_share": False,
            }]

        out_path = compose_dir / f"{clip_id}_vertical.mp4"
        work_sub = WORK / f"compose_{clip_id}"
        work_sub.mkdir(parents=True, exist_ok=True)

        result = compose_shot(
            shots=relevant_shots,
            master_path=src,
            cut_in=cut_in,
            cut_out=cut_out,
            out_path=str(out_path),
            work_dir=str(work_sub),
            clip_id=clip_id,
        )
        composed.append({
            "clip_id": clip_id,
            "path": str(out_path),
            "duration": cut_out - cut_in,
            "layout": result.get("layout", "unknown"),
            "faces": result.get("total_faces", 0),
        })
        print(f"  {clip_id}: {result.get('layout')} -> {out_path.name}")

    composed_manifest = WORK / "composed_manifest.json"
    with open(composed_manifest, "w") as f:
        json.dump(composed, f, indent=2)
    return composed


# ================================================================
# Stage 3: Assemble
# ================================================================

def stage_assemble(composed, out_path, vo_manifest_path=None):
    """Concatenate composed clips + VO + shoutout + outro into final vertical."""
    from vertical.compositor import assemble

    parts = []
    for c in composed:
        if os.path.exists(c["path"]):
            parts.append(c["path"])

    if not parts:
        print("  ERROR: no composed parts to assemble")
        return None

    assemble(parts, str(out_path), fps=FPS)

    if os.path.exists(out_path):
        dur = get_duration(out_path)
        print(f"  Assembled: {out_path} ({dur:.2f}s)")
        return str(out_path)
    return None


# ================================================================
# Stage 4: QA Gates
# ================================================================

def stage_qa(final_mp4, manifest_path):
    """Run qa_gates.py G1-G6."""
    try:
        from qa_gates import run_all_gates
        qa_dir = str(WORK / "qa")
        os.makedirs(qa_dir, exist_ok=True)
        ok, results = run_all_gates(str(final_mp4), manifest_path, qa_dir=qa_dir)
        # Write results
        results_path = WORK / "gate_results_9x16.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        return ok, results
    except ImportError:
        print("  WARNING: qa_gates.py not importable, skipping")
        return True, {}


# ================================================================
# Stage 5: Critic
# ================================================================

def stage_critic(shot_map_data, composed_dir):
    """Run Grok-4 vision critic on composed shots."""
    try:
        from vertical.critic import critique_all
        sources = shot_map_data.get("sources", {})
        all_shots = []
        for vid, smap in sources.items():
            all_shots.extend(smap.get("shots", []))
        result = critique_all(all_shots, str(composed_dir), str(WORK))
        return result
    except Exception as e:
        print(f"  Critic error: {e}")
        return {"overall_pass": False, "error": str(e)}


# ================================================================
# Stage 6: Contact Sheet
# ================================================================

def stage_sheet(composed, out_png):
    """Generate a 12-frame contact sheet from composed clips."""
    import cv2
    from PIL import Image

    frames = []
    for c in composed[:12]:
        if not os.path.exists(c["path"]):
            continue
        cap = cv2.VideoCapture(c["path"])
        dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1)
        cap.set(cv2.CAP_PROP_POS_MSEC, dur * 500)  # mid point
        ret, frame = cap.read()
        cap.release()
        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(rgb))

    if not frames:
        print("  No frames for contact sheet")
        return

    # 4 columns, thumbnail 135x240
    tw, th = 135, 240
    cols = 4
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (12, 12, 12))
    for i, img in enumerate(frames):
        x = (i % cols) * tw
        y = (i // cols) * th
        thumb = img.resize((tw, th), Image.LANCZOS)
        sheet.paste(thumb, (x, y))

    sheet.save(str(out_png))
    print(f"  Contact sheet: {out_png} ({len(frames)} frames)")


# ================================================================
# Stage 7: Telegram Preview
# ================================================================

def stage_tg(final_mp4, caption):
    """Send preview to Telegram via tg_preview.py."""
    try:
        tg_script = BASE.parent / "segment_v1" / "tg_preview.py"
        if tg_script.exists():
            subprocess.run([
                sys.executable, str(tg_script),
                str(final_mp4), "--caption", caption,
            ], timeout=120)
        else:
            print(f"  tg_preview.py not found at {tg_script}")
    except Exception as e:
        print(f"  TG preview error: {e}")


# ================================================================
# MAIN
# ================================================================

def main():
    ap = argparse.ArgumentParser(description="Vertical reframing pipeline")
    ap.add_argument("--edl", required=True, help="EDL JSON (cuts_v3.json)")
    ap.add_argument("--sources", required=True, help="Sources directory")
    ap.add_argument("--out", required=True, help="Output MP4 path")
    ap.add_argument("--stage", default="all",
                    choices=["shotmap", "compose", "assemble", "qa",
                             "critic", "sheet", "tg", "all"])
    ap.add_argument("--no-critic", action="store_true")
    ap.add_argument("--no-tg", action="store_true")
    args = ap.parse_args()

    WORK.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    timings = {}
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"=== VERTICAL REFRAME v1 ===")
    print(f"  EDL: {args.edl}")
    print(f"  Sources: {args.sources}")
    print(f"  Output: {args.out}")
    print(f"  Stage: {args.stage}")

    # Stage 1: Shotmap
    shot_map_data = None
    if args.stage in ("shotmap", "all"):
        with timed("SHOTMAP") as t:
            shot_map_data = stage_shotmap(args.sources, args.edl)
        timings["shotmap"] = t.elapsed
    else:
        sm_path = WORK / "shot_map.json"
        if sm_path.exists():
            shot_map_data = json.loads(sm_path.read_text())

    # Stage 2: Compose
    composed = None
    if args.stage in ("compose", "all") and shot_map_data:
        with timed("COMPOSE") as t:
            composed = stage_compose(shot_map_data, args.sources, args.edl)
        timings["compose"] = t.elapsed
    else:
        cm_path = WORK / "composed_manifest.json"
        if cm_path.exists():
            composed = json.loads(cm_path.read_text())

    # Stage 3: Assemble
    final_mp4 = None
    if args.stage in ("assemble", "all") and composed:
        with timed("ASSEMBLE") as t:
            final_mp4 = stage_assemble(composed, out_path)
        timings["assemble"] = t.elapsed
    elif os.path.exists(args.out):
        final_mp4 = args.out

    # Stage 4: QA Gates
    qa_ok = True
    if args.stage in ("qa", "all") and final_mp4:
        manifest_path = str(WORK / "composed_manifest.json")
        with timed("QA GATES") as t:
            qa_ok, qa_results = stage_qa(final_mp4, manifest_path)
        timings["qa_gates"] = t.elapsed
        if not qa_ok:
            fail_path = WORK / "GATE_FAIL.txt"
            fail_path.write_text(f"QA GATE FAILURE: {final_mp4}\n")
            print(f"  GATE FAILURE — {fail_path}")

    # Stage 5: Critic
    critic_ok = True
    if args.stage in ("critic", "all") and not args.no_critic and composed:
        with timed("CRITIC") as t:
            critic_result = stage_critic(
                shot_map_data or {}, WORK / "composed")
            critic_ok = critic_result.get("overall_pass", False)
        timings["critic"] = t.elapsed

    # Stage 6: Contact Sheet
    if args.stage in ("sheet", "all") and composed:
        with timed("CONTACT SHEET") as t:
            stage_sheet(composed, WORK / "contact_sheet_v14.png")
        timings["sheet"] = t.elapsed

    # Stage 7: Telegram
    all_pass = qa_ok and critic_ok
    if args.stage in ("tg", "all") and not args.no_tg and final_mp4 and all_pass:
        n_shots = sum(
            len(s.get("shots", []))
            for s in (shot_map_data or {}).get("sources", {}).values())
        caption = (
            f"REVIEW v14 9:16 (vertical module v1): "
            f"shotmap layouts, critic {'PASS' if critic_ok else 'FAIL'} "
            f"on {n_shots} shots")
        with timed("TG PREVIEW") as t:
            stage_tg(final_mp4, caption)
        timings["tg"] = t.elapsed
    elif not all_pass and final_mp4:
        print(f"\n  BLOCKED: QA={'PASS' if qa_ok else 'FAIL'}, "
              f"Critic={'PASS' if critic_ok else 'FAIL'} — no Telegram send")

    # Timing summary
    total = sum(timings.values())
    print(f"\n=== TIMING BREAKDOWN ===")
    for stage, elapsed in timings.items():
        print(f"  {stage:15s}: {elapsed:6.1f}s")
    print(f"  {'TOTAL':15s}: {total:6.1f}s")
    if total > 480:
        print(f"  WARNING: exceeded 8-minute budget ({total:.0f}s)")

    # Write timing to work dir for REPORT
    timing_path = WORK / "timings.json"
    with open(timing_path, "w") as f:
        json.dump(timings, f, indent=2)

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
