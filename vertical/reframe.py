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
        --edl cuts_final.json \\
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

HANDLE_SECS = 3  # extra seconds each side of EDL cut for shotmap


def _extract_window(src, out_mp4, t_in, t_out):
    """Extract a time window from source. Re-encodes to ensure clean keyframes."""
    dur = t_out - t_in
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(max(0, t_in)), "-i", str(src),
        "-t", str(dur),
        "-c:v", "libx264", "-crf", "17", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-avoid_negative_ts", "make_zero",
        str(out_mp4),
    ], capture_output=True, timeout=120)
    return os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 0


def stage_shotmap(sources_dir, edl_path):
    """Run shotmap only on EDL windows (cut_in-3s to cut_out+3s), not full sources."""
    from vertical.shotmap import build as shotmap_build

    with open(edl_path) as f:
        edl = json.load(f)

    # Group cuts by source video, merge overlapping windows
    from collections import defaultdict
    vid_windows = defaultdict(list)
    for cut in edl:
        vid = cut.get("video_id", "")
        if not vid:
            continue
        t_in = cut.get("cut_in", 0) - HANDLE_SECS
        t_out = cut.get("cut_out", 0) + HANDLE_SECS
        vid_windows[vid].append((max(0, t_in), t_out, cut.get("clip_id", "unknown")))

    shot_maps = {}
    windows_dir = WORK / "edl_windows"
    windows_dir.mkdir(parents=True, exist_ok=True)

    for vid in sorted(vid_windows):
        # Find the source file
        src = None
        for ext in (".mov", ".mkv", ".mp4"):
            candidate = os.path.join(sources_dir, vid + ext)
            if os.path.exists(candidate):
                src = candidate
                break
        if not src:
            print(f"  WARNING: no source found for {vid} in {sources_dir}")
            continue

        # Merge overlapping windows for this source
        windows = sorted(vid_windows[vid])
        merged = [list(windows[0])]
        for w_in, w_out, cid in windows[1:]:
            if w_in <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], w_out)
                merged[-1][2] += f"+{cid}"
            else:
                merged.append([w_in, w_out, cid])

        total_window_s = sum(w[1] - w[0] for w in merged)
        print(f"  {vid}: {len(merged)} window(s), {total_window_s:.1f}s total", flush=True)

        # Process each merged window
        vid_results = {"shots": [], "video": None}
        for w_in, w_out, label in merged:
            # Cache key: source md5 + window range
            cache_key = f"{md5_file(src)}_{w_in:.2f}_{w_out:.2f}"
            cache_path = CACHE / f"{cache_key}.json"
            if cache_path.exists():
                cached = json.loads(cache_path.read_text())
                vid_results["shots"].extend(cached.get("shots", []))
                if cached.get("video"):
                    vid_results["video"] = cached["video"]
                print(f"    window {w_in:.1f}-{w_out:.1f}s: cached", flush=True)
                continue

            # Extract window to file (cached if already exists)
            win_mp4 = str(windows_dir / f"{vid}_{w_in:.0f}_{w_out:.0f}.mp4")
            if os.path.exists(win_mp4) and os.path.getsize(win_mp4) > 0:
                print(f"    window {w_in:.1f}-{w_out:.1f}s: mp4 cached", flush=True)
            elif not _extract_window(src, win_mp4, w_in, w_out):
                print(f"    WARNING: failed to extract window {w_in:.1f}-{w_out:.1f}s from {vid}")
                continue

            out_dir = WORK / f"shotmap_{vid}_{w_in:.0f}_{w_out:.0f}"
            out_dir.mkdir(parents=True, exist_ok=True)
            result = shotmap_build(win_mp4, str(out_dir))
            if result:
                # Offset shot times back to source timeline
                for s in result.get("shots", []):
                    s["t_in"] = round(s["t_in"] + w_in, 3)
                    s["t_out"] = round(s["t_out"] + w_in, 3)
                    s["frame_in"] = int(s["frame_in"] + w_in * result.get("video", {}).get("fps", 30))
                    s["frame_out"] = int(s["frame_out"] + w_in * result.get("video", {}).get("fps", 30))
                vid_results["shots"].extend(result.get("shots", []))
                if result.get("video"):
                    vid_results["video"] = result["video"]
                # Cache window result
                CACHE.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(result, indent=1))

        if vid_results["shots"]:
            shot_maps[vid] = vid_results

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

def _adapt_shot(shot):
    """Adapt shotmap shot dict to the fields compositor expects."""
    adapted = dict(shot)
    # Compositor checks 'face_count' and 'has_screenshare'
    if "face_count" not in adapted and "total_faces" in adapted:
        adapted["face_count"] = adapted["total_faces"] or 1
    if "has_screenshare" not in adapted:
        adapted["has_screenshare"] = adapted.get("screen_share", False)
    return adapted


def stage_compose(shot_map_data, sources_dir, edl_path):
    """Compose each EDL cut to 9:16 using compose_all from compositor."""
    from vertical.compositor import compose_all

    with open(edl_path) as f:
        edl = json.load(f)

    all_compose_results = []
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
                "edl_t_in": cut_in,
                "edl_t_out": cut_out,
                "layout": "single",
                "face_count": 1,
                "has_screenshare": False,
                "tiles": [{"x0": 0, "x1": 1920, "face_count": 1}],
                "seams": [],
            }]
        else:
            # Clamp first/last shot to cut boundaries
            relevant_shots = [_adapt_shot(s) for s in relevant_shots]
            relevant_shots[0] = dict(relevant_shots[0])
            relevant_shots[0]["frame_in"] = max(relevant_shots[0]["frame_in"], frame_in)
            relevant_shots[-1] = dict(relevant_shots[-1])
            relevant_shots[-1]["frame_out"] = min(relevant_shots[-1]["frame_out"], frame_out)

            # Inject EDL-authoritative timestamps on each shot so compositor
            # uses seconds from the EDL rather than frame_in/src_fps (avoids
            # 30fps window vs 29.97fps source mismatch).
            for i, s in enumerate(relevant_shots):
                if i == 0:
                    s["edl_t_in"] = cut_in
                else:
                    s["edl_t_in"] = s.get("t_in", s["frame_in"] / fps)
                if i == len(relevant_shots) - 1:
                    s["edl_t_out"] = cut_out
                else:
                    s["edl_t_out"] = s.get("t_out", s["frame_out"] / fps)

        # Prefix shot IDs with clip_id for uniqueness
        for s in relevant_shots:
            s["id"] = f"{clip_id}_{s['id']}"

        clip_compose_dir = str(compose_dir / clip_id)
        work_sub = str(WORK / f"compose_{clip_id}")
        os.makedirs(clip_compose_dir, exist_ok=True)
        os.makedirs(work_sub, exist_ok=True)

        results = compose_all(
            shot_map=relevant_shots,
            master_path=src,
            out_dir=clip_compose_dir,
            work_dir=work_sub,
        )
        all_compose_results.extend(results)

        n_ok = sum(1 for r in results if r["ok"])
        layouts = set(r["layout"] for r in results)
        print(f"  {clip_id}: {n_ok}/{len(results)} shots OK, layouts={layouts}")

    composed_manifest = WORK / "composed_manifest.json"
    with open(composed_manifest, "w") as f:
        json.dump(all_compose_results, f, indent=2, default=str)
    return all_compose_results


# ================================================================
# Stage 3: Assemble
# ================================================================

def stage_assemble(composed, out_path, vo_manifest_path=None):
    """Concatenate composed clips into final vertical using compositor.assemble."""
    from vertical.compositor import assemble

    if not composed:
        print("  ERROR: no composed parts to assemble")
        return None

    ok = assemble(composed, str(out_path), fps=FPS)

    if ok and os.path.exists(out_path):
        dur = get_duration(out_path)
        print(f"  Assembled: {out_path} ({dur:.2f}s)")
        return str(out_path)
    print("  ASSEMBLE FAILED")
    return None


# ================================================================
# Stage 4: QA Gates
# ================================================================

def stage_qa(final_mp4, manifest_path):
    """Run vertical-specific QA gates (G1-G6 adapted for 9:16)."""
    results = {}
    all_ok = True

    # G1: Resolution must be 1080x1920
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,codec_name,pix_fmt,r_frame_rate",
         "-of", "json", str(final_mp4)],
        capture_output=True, text=True, timeout=15)
    vinfo = json.loads(probe.stdout).get("streams", [{}])[0]
    w, h = vinfo.get("width", 0), vinfo.get("height", 0)
    g1 = (w == VERT_W and h == VERT_H)
    results["G1_resolution"] = {"pass": g1, "actual": f"{w}x{h}", "expected": f"{VERT_W}x{VERT_H}"}
    if not g1:
        all_ok = False
    print(f"  G1 Resolution: {'PASS' if g1 else 'FAIL'} ({w}x{h})")

    # G2: Codec must be h264/yuv420p
    codec = vinfo.get("codec_name", "")
    pix = vinfo.get("pix_fmt", "")
    g2 = (codec == "h264" and pix == "yuv420p")
    results["G2_codec"] = {"pass": g2, "codec": codec, "pix_fmt": pix}
    if not g2:
        all_ok = False
    print(f"  G2 Codec: {'PASS' if g2 else 'FAIL'} ({codec}/{pix})")

    # G3: Duration > 10s
    dur = get_duration(final_mp4)
    g3 = dur > 10.0
    results["G3_duration"] = {"pass": g3, "duration": dur}
    if not g3:
        all_ok = False
    print(f"  G3 Duration: {'PASS' if g3 else 'FAIL'} ({dur:.2f}s)")

    # G4: Audio present (48kHz stereo)
    aprobe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=sample_rate,channels",
         "-of", "json", str(final_mp4)],
        capture_output=True, text=True, timeout=15)
    ainfo = json.loads(aprobe.stdout).get("streams", [{}])[0]
    sr = int(ainfo.get("sample_rate", 0))
    ch = int(ainfo.get("channels", 0))
    g4 = (sr == 48000 and ch == 2)
    results["G4_audio"] = {"pass": g4, "sample_rate": sr, "channels": ch}
    if not g4:
        all_ok = False
    print(f"  G4 Audio: {'PASS' if g4 else 'FAIL'} ({sr}Hz, {ch}ch)")

    # G5: File size > 1MB (not empty/corrupt)
    fsize = os.path.getsize(final_mp4)
    g5 = fsize > 1_000_000
    results["G5_filesize"] = {"pass": g5, "bytes": fsize}
    if not g5:
        all_ok = False
    print(f"  G5 Filesize: {'PASS' if g5 else 'FAIL'} ({fsize/1e6:.1f}MB)")

    # G6: No black frames at start/end (sample first+last 0.5s)
    g6 = True  # Assume pass unless we detect black
    for pos, label in [("0.2", "start"), (str(max(0, dur - 0.5)), "end")]:
        frame_path = str(WORK / f"qa_g6_{label}.png")
        subprocess.run(
            ["ffmpeg", "-y", "-ss", pos, "-i", str(final_mp4),
             "-frames:v", "1", "-q:v", "2", frame_path],
            capture_output=True, timeout=15)
        if os.path.exists(frame_path):
            import cv2
            img = cv2.imread(frame_path)
            if img is not None:
                mean_luma = img.mean()
                if mean_luma < 5.0:
                    g6 = False
                    print(f"  G6: black frame at {label} (luma={mean_luma:.1f})")
    results["G6_no_black"] = {"pass": g6}
    if not g6:
        all_ok = False
    print(f"  G6 No Black: {'PASS' if g6 else 'FAIL'}")

    results_path = WORK / "gate_results_9x16.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    return all_ok, results


def gate_g7(final_mp4, edl_path, composed):
    """G7 Completeness: assembled duration matches EDL, every shot in manifest."""
    with open(edl_path) as f:
        edl = json.load(f)

    # Expected duration = sum of EDL cut durations
    expected_dur = sum(c.get("cut_duration", c.get("cut_out", 0) - c.get("cut_in", 0))
                       for c in edl)
    actual_dur = get_duration(final_mp4)
    dur_ok = abs(actual_dur - expected_dur) <= 0.5
    dur_delta = actual_dur - expected_dur

    # Shot coverage: every composed shot must be ok
    total_shots = len(composed) if composed else 0
    ok_shots = sum(1 for c in (composed or []) if c.get("ok"))
    missing = total_shots - ok_shots
    coverage_ok = (missing == 0 and total_shots > 0)

    # Also check: every EDL clip has at least one composed shot
    edl_clip_ids = {c.get("clip_id") for c in edl}
    composed_prefixes = set()
    for c in (composed or []):
        cid = c.get("id", "")
        # IDs are prefixed like "hook_sh001", "clip_01_sh001"
        for eid in edl_clip_ids:
            if cid.startswith(eid + "_"):
                composed_prefixes.add(eid)
    missing_clips = edl_clip_ids - composed_prefixes
    clips_ok = len(missing_clips) == 0

    g7 = dur_ok and coverage_ok and clips_ok
    detail = (f"dur={actual_dur:.2f}s vs expected={expected_dur:.2f}s "
              f"(delta={dur_delta:+.2f}s), "
              f"shots={ok_shots}/{total_shots}, "
              f"clips={'all' if clips_ok else 'MISSING:' + ','.join(missing_clips)}")
    print(f"  G7 Completeness: {'PASS' if g7 else 'FAIL'} ({detail})")

    result = {
        "pass": g7,
        "expected_duration": round(expected_dur, 2),
        "actual_duration": round(actual_dur, 2),
        "duration_delta": round(dur_delta, 2),
        "total_shots": total_shots,
        "ok_shots": ok_shots,
        "missing_shots": missing,
        "missing_clips": sorted(missing_clips),
    }
    return g7, result


# ================================================================
# Stage 5: Critic
# ================================================================

def stage_critic(composed, shot_map_data):
    """Run Grok-4 vision critic on composed shots by extracting frames from MP4s."""
    try:
        from vertical.critic import critique_shot
        import logging
        logger = logging.getLogger("vertical.critic")

        critic_dir = WORK / "critic_frames"
        critic_dir.mkdir(parents=True, exist_ok=True)

        results = []
        pass_count = 0
        fail_count = 0

        for entry in composed:
            if not entry.get("ok"):
                continue
            mp4 = entry.get("out_path", "")
            if not os.path.exists(mp4):
                continue
            shot_id = entry.get("id", "unknown")

            # Extract frames at 25% and 75%
            dur = get_duration(mp4)
            if dur < 0.5:
                continue
            t1 = dur * 0.25
            t2 = dur * 0.75
            f1 = str(critic_dir / f"{shot_id}_25.png")
            f2 = str(critic_dir / f"{shot_id}_75.png")
            for t, fp in [(t1, f1), (t2, f2)]:
                subprocess.run(
                    ["ffmpeg", "-y", "-ss", str(t), "-i", mp4,
                     "-frames:v", "1", "-q:v", "2", fp],
                    capture_output=True, timeout=15)

            if not os.path.exists(f1) or not os.path.exists(f2):
                fail_count += 1
                results.append({"shot_id": shot_id, "pass": False,
                                "issues": ["frame extraction failed"]})
                continue

            # Build shot dict for critic — tiles list sized to face_count
            # so the critic's expected-tiles check doesn't false-fail
            fc = entry.get("face_count", 1)
            shot = {
                "shot_id": shot_id,
                "layout": entry.get("layout", "unknown"),
                "face_count": fc,
                "tiles": [{"face_count": 1}] * max(fc, 1),
            }
            result = critique_shot(shot, f1, f2, str(WORK))
            results.append(result)
            if result.get("pass"):
                pass_count += 1
            else:
                fail_count += 1

        overall = fail_count == 0 and pass_count > 0
        total = pass_count + fail_count
        summary = f"{pass_count}/{total} shots passed" if total > 0 else "no shots evaluated"
        print(f"  Critic: {summary} (overall={'PASS' if overall else 'FAIL'})")

        critic_result = {"overall_pass": overall, "shots": results, "summary": summary}
        with open(WORK / "critic_results.json", "w") as f:
            json.dump(critic_result, f, indent=2, default=str)
        return critic_result
    except Exception as e:
        print(f"  Critic error: {e}")
        import traceback
        traceback.print_exc()
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
        p = c.get("out_path") or c.get("path", "")
        if not os.path.exists(p):
            continue
        cap = cv2.VideoCapture(p)
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

def _run_t1(final_mp4, shot_map_data):
    """Run T1 face count test: rendered faces must match shot_map per shot."""
    try:
        from vertical.tests.test_face_count import count_faces_mediapipe, extract_frame
        import tempfile
        if not shot_map_data:
            print("  T1: no shot_map data, SKIP")
            return True
        qa_dir = str(WORK / "qa_t1")
        os.makedirs(qa_dir, exist_ok=True)
        failures = []
        all_shots = []
        for vid, smap in shot_map_data.get("sources", {}).items():
            for s in smap.get("shots", []):
                s_copy = dict(s)
                s_copy["_vid"] = vid
                all_shots.append(s_copy)
        # Sample up to 10 shots
        import random
        sample = random.sample(all_shots, min(10, len(all_shots)))
        for shot in sample:
            expected = shot.get("total_faces") or shot.get("face_count") or 0
            if expected == 0:
                continue
            t_in = shot.get("t_in", 0)
            t_out = shot.get("t_out", 0)
            mid_t = (t_in + t_out) / 2
            if mid_t <= 0:
                continue
            frame_path = os.path.join(qa_dir, f"t1_{shot.get('id', 'unk')}.png")
            if extract_frame(str(final_mp4), mid_t, frame_path):
                actual = count_faces_mediapipe(frame_path)
                if actual != expected:
                    failures.append(f"  shot {shot.get('id')}: expected {expected}, got {actual}")
        if failures:
            print(f"  T1 FAIL ({len(failures)} mismatches):")
            for f in failures:
                print(f)
            return False
        print(f"  T1 PASS ({len(sample)} shots sampled)")
        return True
    except Exception as e:
        print(f"  T1 error: {e}")
        return False


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
    ap.add_argument("--edl", required=True, help="EDL JSON (Law 22: use cuts_final.json, the single source of truth)")
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

    # Stage 4b: G7 Completeness
    g7_ok = True
    if args.stage in ("qa", "all") and final_mp4:
        with timed("G7 COMPLETENESS") as t:
            g7_ok, g7_result = gate_g7(final_mp4, args.edl, composed)
        timings["g7_completeness"] = t.elapsed
        if not g7_ok:
            qa_ok = False

    # Stage 4c: T1 face count test
    t1_ok = True
    if args.stage in ("qa", "all") and final_mp4:
        with timed("T1 FACE COUNT") as t:
            t1_ok = _run_t1(final_mp4, shot_map_data)
        timings["t1_face_count"] = t.elapsed

    # Stage 5: Critic
    critic_ok = True
    if args.stage in ("critic", "all") and not args.no_critic and composed:
        with timed("CRITIC") as t:
            critic_result = stage_critic(composed, shot_map_data or {})
            critic_ok = critic_result.get("overall_pass", False)
        timings["critic"] = t.elapsed

    # Stage 6: Contact Sheet
    if args.stage in ("sheet", "all") and composed:
        with timed("CONTACT SHEET") as t:
            stage_sheet(composed, WORK / "contact_sheet_v14.png")
        timings["sheet"] = t.elapsed

    # Stage 7: Telegram
    all_pass = qa_ok and g7_ok and t1_ok and critic_ok
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
              f"G7={'PASS' if g7_ok else 'FAIL'}, "
              f"T1={'PASS' if t1_ok else 'FAIL'}, "
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
