#!/usr/bin/env python3
"""Stage 4: Full 1920x1080 24fps render with all layers.
Timeline: hook → VO intro (Ken Burns) → clip_01-03 → VO bridge (Ken Burns) → clip_04 → outro
Layers: V1 clips, V2 lower-thirds (5s each), V3 waveform (VO only), A1-3 mixed, BGM at -22dB
Encode: h264_nvenc p4, AAC 192k 48kHz. Final loudnorm -14 LUFS."""
import json, os, subprocess, sys, time

BASE = "/home/ultron/protocol_pulse/segment_v1"
SOURCES = os.path.join(BASE, "sources")
QA = os.path.join(BASE, "qa_v3")
OUT = os.path.join(BASE, "out")
LT_DIR = os.path.join(BASE, "lower_thirds")
VO_DIR = os.path.join(BASE, "vo_audio")
os.makedirs(OUT, exist_ok=True)
os.makedirs(QA, exist_ok=True)

OUTRO = "/home/ultron/protocol_pulse/video_pipeline_v3/assets/outro_branded.mp4"
BGM = "/home/ultron/protocol_pulse/video_pipeline_v3/assets/music/confident_02.mp3"

FPS = 24
WIDTH = 1920
HEIGHT = 1080
LT_DURATION = 5.0  # Lower third overlay duration (seconds)

with open(os.path.join(BASE, "cuts_v3.json")) as f:
    cuts = json.load(f)
with open(os.path.join(BASE, "edl_v2.json")) as f:
    edl = json.load(f)

bridge_after = None
for b in edl.get("vo", {}).get("bridges", []):
    bridge_after = b.get("after_clip")


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def render_clip_1080(cut, lt_png, out_path):
    """Render a single clip at 1920x1080 24fps with lower-third overlay for first 5s."""
    src = os.path.join(SOURCES, f"{cut['video_id']}.mp4")
    dur = cut["cut_out"] - cut["cut_in"]
    fade_out = max(dur - 0.02, 0)

    # Build video filter: scale + lower-third overlay (fade in/out)
    vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2"

    if lt_png and os.path.exists(lt_png):
        # Lower-third: fade in 0.3s, hold, fade out 0.5s at 4.5s
        lt_fade_out_start = min(LT_DURATION - 0.5, dur - 0.5)
        lt_end = min(LT_DURATION, dur)
        # Use overlay with enable and alpha
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(cut["cut_in"]), "-to", str(cut["cut_out"]), "-i", src,
            "-i", lt_png,
            "-filter_complex",
            f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2[bg];"
            f"[1:v]format=rgba,fade=t=in:st=0:d=0.3:alpha=1,"
            f"fade=t=out:st={lt_fade_out_start:.3f}:d=0.5:alpha=1[lt];"
            f"[bg][lt]overlay=0:0:enable='between(t,0,{lt_end:.1f})'",
            "-r", str(FPS), "-vsync", "cfr",
            "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
            "-pix_fmt", "yuv420p",
            "-af", f"loudnorm=I=-18:TP=-1.5:LRA=11,afade=t=in:d=0.02,afade=t=out:st={fade_out:.3f}:d=0.02",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            out_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(cut["cut_in"]), "-to", str(cut["cut_out"]), "-i", src,
            "-vf", vf,
            "-r", str(FPS), "-vsync", "cfr",
            "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
            "-pix_fmt", "yuv420p",
            "-af", f"loudnorm=I=-18:TP=-1.5:LRA=11,afade=t=in:d=0.02,afade=t=out:st={fade_out:.3f}:d=0.02",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            out_path,
        ]

    subprocess.run(cmd, capture_output=True, timeout=180)
    return os.path.exists(out_path) and os.path.getsize(out_path) > 1000


def render_vo_1080(vo_visual_mp4, out_path):
    """Scale VO visual to 1920x1080 24fps (already rendered at this res by render_vo_visual.py)."""
    subprocess.run([
        "ffmpeg", "-y", "-i", vo_visual_mp4,
        "-vf", f"scale={WIDTH}:{HEIGHT}", "-r", str(FPS), "-vsync", "cfr",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        out_path,
    ], capture_output=True, timeout=60)
    return os.path.exists(out_path) and os.path.getsize(out_path) > 500


def render_outro(out_path):
    """Scale outro to 1920x1080 24fps."""
    subprocess.run([
        "ffmpeg", "-y", "-i", OUTRO,
        "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
               f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2",
        "-r", str(FPS), "-vsync", "cfr",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        out_path,
    ], capture_output=True, timeout=60)
    return os.path.exists(out_path) and os.path.getsize(out_path) > 500


if __name__ == "__main__":
    t0 = time.time()
    print("=== STAGE 4: FULL 1080p RENDER ===\n")

    # First, render VO visuals at full resolution
    print("Rendering VO visuals at 1080p...")
    sys.path.insert(0, BASE)
    from render_vo_visual import render_vo_segment
    VO_INTRO_WAV = os.path.join(VO_DIR, "vo_intro.wav")
    VO_BRIDGE_WAV = os.path.join(VO_DIR, "vo_bridge_01.wav")

    hook_cut = next((c for c in cuts if c["clip_id"] == "hook"), None)
    vo_intro_1080 = os.path.join(QA, "vo_intro_1080.mp4")
    if hook_cut:
        hook_src = os.path.join(SOURCES, f"{hook_cut['video_id']}.mp4")
        render_vo_segment(VO_INTRO_WAV, hook_src, hook_cut["cut_out"],
                          vo_intro_1080, width=1920, height=1080, preview=False)
    print()

    bridge_cut = next((c for c in cuts if c["clip_id"] == f"clip_{bridge_after:02d}"), None) if bridge_after else None
    vo_bridge_1080 = os.path.join(QA, "vo_bridge_1080.mp4")
    if bridge_cut:
        bridge_src = os.path.join(SOURCES, f"{bridge_cut['video_id']}.mp4")
        render_vo_segment(VO_BRIDGE_WAV, bridge_src, bridge_cut["cut_out"],
                          vo_bridge_1080, width=1920, height=1080, preview=False)
    print()

    # Render each segment
    segments = []

    # Hook
    if hook_cut:
        lt = os.path.join(LT_DIR, "lt_hook.png")
        p = os.path.join(QA, "final_hook.mp4")
        print(f"Rendering hook...", end=" ", flush=True)
        if render_clip_1080(hook_cut, lt, p):
            segments.append(("hook", p))
            print(f"OK ({get_duration(p):.2f}s)")

    # VO intro
    if os.path.exists(vo_intro_1080):
        p = os.path.join(QA, "final_vo_intro.mp4")
        print(f"Normalizing VO intro...", end=" ", flush=True)
        if render_vo_1080(vo_intro_1080, p):
            segments.append(("vo_intro", p))
            print(f"OK ({get_duration(p):.2f}s)")

    # Clips + VO bridge
    for cut in cuts:
        if cut["clip_id"] == "hook":
            continue
        clip_id = cut["clip_id"]
        lt = os.path.join(LT_DIR, f"lt_{clip_id}.png")
        p = os.path.join(QA, f"final_{clip_id}.mp4")
        print(f"Rendering {clip_id}...", end=" ", flush=True)
        if render_clip_1080(cut, lt, p):
            segments.append((clip_id, p))
            print(f"OK ({get_duration(p):.2f}s)")

        # VO bridge
        clip_num = int(clip_id.split("_")[1])
        if bridge_after and clip_num == bridge_after and os.path.exists(vo_bridge_1080):
            bp = os.path.join(QA, "final_vo_bridge.mp4")
            print(f"Normalizing VO bridge...", end=" ", flush=True)
            if render_vo_1080(vo_bridge_1080, bp):
                segments.append(("vo_bridge", bp))
                print(f"OK ({get_duration(bp):.2f}s)")

    # Outro
    print(f"Rendering outro...", end=" ", flush=True)
    op = os.path.join(QA, "final_outro.mp4")
    if render_outro(op):
        segments.append(("outro", op))
        print(f"OK ({get_duration(op):.2f}s)")

    if len(segments) < 3:
        print(f"\nERROR: Only {len(segments)} segments rendered")
        sys.exit(1)

    order = " -> ".join(s[0] for s in segments)
    total_dur = sum(get_duration(p) for _, p in segments)
    print(f"\n  Order: {order}")
    print(f"  Total segment duration: {total_dur:.1f}s")

    # Concat all segments
    print("\n=== CONCAT ===")
    filelist = os.path.join(QA, "final_filelist.txt")
    with open(filelist, "w") as f:
        for label, path in segments:
            f.write(f"file '{path}'\n")

    concat_path = os.path.join(QA, "concat_raw.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
        "-vf", "setpts=PTS-STARTPTS",
        "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", concat_path,
    ], capture_output=True, timeout=600)
    print(f"  Concat: {concat_path} ({get_duration(concat_path):.2f}s)")

    # Mix BGM at -22dB under the full mix
    print("\n=== BGM MIX ===")
    bgm_mix_path = os.path.join(QA, "with_bgm.mp4")
    concat_dur = get_duration(concat_path)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", concat_path,
        "-stream_loop", "-1", "-i", BGM,
        "-filter_complex",
        f"[1:a]volume=-22dB,afade=t=in:d=1.0,afade=t=out:st={concat_dur - 2.0:.1f}:d=2.0[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", bgm_mix_path,
    ], capture_output=True, timeout=300)
    print(f"  BGM mix: {bgm_mix_path} ({get_duration(bgm_mix_path):.2f}s)")

    # Final loudnorm pass: -14 LUFS, TP <= -2.0dBTP
    print("\n=== FINAL LOUDNORM ===")
    # Pass 1: measure
    r = subprocess.run([
        "ffmpeg", "-y", "-i", bgm_mix_path,
        "-af", "loudnorm=I=-14:TP=-2.0:LRA=11:print_format=json",
        "-f", "null", "-",
    ], capture_output=True, text=True, timeout=300)
    stderr = r.stderr
    try:
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1
        stats = json.loads(stderr[json_start:json_end])
        mi = stats["input_i"]
        mtp = stats["input_tp"]
        mlra = stats["input_lra"]
        mt = stats["input_thresh"]
        off = stats["target_offset"]
        print(f"  Measured: I={mi} TP={mtp} LRA={mlra}")
    except Exception:
        mi = mtp = mlra = mt = off = None

    final_path = os.path.join(OUT, "segment_v3.mp4")
    if mi is not None:
        subprocess.run([
            "ffmpeg", "-y", "-i", bgm_mix_path,
            "-c:v", "copy",
            "-af", f"loudnorm=I=-14:TP=-2.0:LRA=11:"
                   f"measured_I={mi}:measured_TP={mtp}:"
                   f"measured_LRA={mlra}:measured_thresh={mt}:"
                   f"offset={off}:linear=true",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", final_path,
        ], capture_output=True, timeout=300)
    else:
        # Single-pass fallback
        subprocess.run([
            "ffmpeg", "-y", "-i", bgm_mix_path,
            "-c:v", "copy",
            "-af", "loudnorm=I=-14:TP=-2.0:LRA=11",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", final_path,
        ], capture_output=True, timeout=300)

    elapsed = time.time() - t0
    if os.path.exists(final_path):
        dur = get_duration(final_path)
        sz = os.path.getsize(final_path)
        print(f"\n=== FINAL OUTPUT ===")
        print(f"  File: {final_path}")
        print(f"  Duration: {dur:.2f}s")
        print(f"  Size: {sz:,} bytes ({sz/1024/1024:.1f} MB)")
        print(f"  Render time: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    else:
        print(f"\nERROR: Final render failed after {elapsed:.0f}s")
        sys.exit(1)
