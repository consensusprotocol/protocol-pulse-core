#!/usr/bin/env python3
"""Render segment_v4.mp4: identical to v3 but with PBX clone voice.
Reuses all clip segments from v3 render, only re-renders VO visuals."""
import json, os, subprocess, sys, time

BASE = "/home/ultron/protocol_pulse/segment_v1"
SOURCES = os.path.join(BASE, "sources")
QA = os.path.join(BASE, "qa_v3")
OUT = os.path.join(BASE, "out")
VO_DIR = os.path.join(BASE, "vo_audio")

BGM = "/home/ultron/protocol_pulse/video_pipeline_v3/assets/music/confident_02.mp3"
FPS = 24
WIDTH = 1920
HEIGHT = 1080

# PBX VO files
VO_INTRO_PBX = os.path.join(VO_DIR, "vo_intro_pbx_v1.wav")
VO_BRIDGE_PBX = os.path.join(VO_DIR, "vo_bridge_01_pbx_v1.wav")

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


if __name__ == "__main__":
    t0 = time.time()
    print("=== SEGMENT V4: PBX VOICE SWAP ===\n")

    # Import VO visual renderer
    sys.path.insert(0, BASE)
    from render_vo_visual import render_vo_segment

    # Render PBX VO visuals at 1080p
    hook_cut = next((c for c in cuts if c["clip_id"] == "hook"), None)
    vo_intro_pbx_1080 = os.path.join(QA, "vo_intro_pbx_1080.mp4")
    if hook_cut:
        hook_src = os.path.join(SOURCES, f"{hook_cut['video_id']}.mp4")
        print("Rendering PBX VO intro visual (1080p)...")
        render_vo_segment(VO_INTRO_PBX, hook_src, hook_cut["cut_out"],
                          vo_intro_pbx_1080, width=1920, height=1080, preview=False)

    bridge_cut = next((c for c in cuts if c["clip_id"] == f"clip_{bridge_after:02d}"), None) if bridge_after else None
    vo_bridge_pbx_1080 = os.path.join(QA, "vo_bridge_pbx_1080.mp4")
    if bridge_cut:
        bridge_src = os.path.join(SOURCES, f"{bridge_cut['video_id']}.mp4")
        print("\nRendering PBX VO bridge visual (1080p)...")
        render_vo_segment(VO_BRIDGE_PBX, bridge_src, bridge_cut["cut_out"],
                          vo_bridge_pbx_1080, width=1920, height=1080, preview=False)

    # Normalize PBX VO segments to match other segments' format
    def normalize_vo(src, dst):
        subprocess.run([
            "ffmpeg", "-y", "-i", src,
            "-vf", f"scale={WIDTH}:{HEIGHT}", "-r", str(FPS), "-vsync", "cfr",
            "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            dst,
        ], capture_output=True, timeout=60)
        return os.path.exists(dst)

    # Build segment list reusing v3 clip renders
    segments = []

    # Hook (reuse from v3)
    v3_hook = os.path.join(QA, "final_hook.mp4")
    if os.path.exists(v3_hook):
        segments.append(("hook", v3_hook))
        print(f"\n  hook: REUSE ({get_duration(v3_hook):.2f}s)")

    # VO intro (PBX)
    pbx_vo_intro = os.path.join(QA, "final_vo_intro_pbx.mp4")
    if normalize_vo(vo_intro_pbx_1080, pbx_vo_intro):
        segments.append(("vo_intro_pbx", pbx_vo_intro))
        print(f"  vo_intro_pbx: OK ({get_duration(pbx_vo_intro):.2f}s)")

    # Clips (reuse from v3) + VO bridge (PBX)
    for cut in cuts:
        if cut["clip_id"] == "hook":
            continue
        clip_id = cut["clip_id"]
        v3_clip = os.path.join(QA, f"final_{clip_id}.mp4")
        if os.path.exists(v3_clip):
            segments.append((clip_id, v3_clip))
            print(f"  {clip_id}: REUSE ({get_duration(v3_clip):.2f}s)")

        clip_num = int(clip_id.split("_")[1])
        if bridge_after and clip_num == bridge_after:
            pbx_bridge = os.path.join(QA, "final_vo_bridge_pbx.mp4")
            if normalize_vo(vo_bridge_pbx_1080, pbx_bridge):
                segments.append(("vo_bridge_pbx", pbx_bridge))
                print(f"  vo_bridge_pbx: OK ({get_duration(pbx_bridge):.2f}s)")

    # Outro (reuse from v3)
    v3_outro = os.path.join(QA, "final_outro.mp4")
    if os.path.exists(v3_outro):
        segments.append(("outro", v3_outro))
        print(f"  outro: REUSE ({get_duration(v3_outro):.2f}s)")

    order = " -> ".join(s[0] for s in segments)
    total_dur = sum(get_duration(p) for _, p in segments)
    print(f"\n  Order: {order}")
    print(f"  Total: {total_dur:.1f}s")

    # Concat
    print("\n=== CONCAT ===")
    filelist = os.path.join(QA, "v4_filelist.txt")
    with open(filelist, "w") as f:
        for label, path in segments:
            f.write(f"file '{path}'\n")

    concat_path = os.path.join(QA, "v4_concat.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
        "-vf", "setpts=PTS-STARTPTS",
        "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", concat_path,
    ], capture_output=True, timeout=600)
    print(f"  Concat: {get_duration(concat_path):.2f}s")

    # BGM mix
    print("\n=== BGM MIX ===")
    bgm_path = os.path.join(QA, "v4_bgm.mp4")
    cd = get_duration(concat_path)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", concat_path,
        "-stream_loop", "-1", "-i", BGM,
        "-filter_complex",
        f"[1:a]volume=-22dB,afade=t=in:d=1.0,afade=t=out:st={cd - 2.0:.1f}:d=2.0[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", bgm_path,
    ], capture_output=True, timeout=300)
    print(f"  BGM mix: {get_duration(bgm_path):.2f}s")

    # Final loudnorm
    print("\n=== FINAL LOUDNORM ===")
    r = subprocess.run([
        "ffmpeg", "-y", "-i", bgm_path,
        "-af", "loudnorm=I=-14:TP=-2.0:LRA=11:print_format=json",
        "-f", "null", "-",
    ], capture_output=True, text=True, timeout=300)
    try:
        stderr = r.stderr
        js = stderr[stderr.rfind("{"):stderr.rfind("}") + 1]
        stats = json.loads(js)
        mi, mtp, mlra, mt, off = stats["input_i"], stats["input_tp"], stats["input_lra"], stats["input_thresh"], stats["target_offset"]
        print(f"  Measured: I={mi} TP={mtp} LRA={mlra}")
    except Exception:
        mi = None

    final_path = os.path.join(OUT, "segment_v4.mp4")
    if mi:
        subprocess.run([
            "ffmpeg", "-y", "-i", bgm_path,
            "-c:v", "copy",
            "-af", f"loudnorm=I=-14:TP=-2.0:LRA=11:"
                   f"measured_I={mi}:measured_TP={mtp}:"
                   f"measured_LRA={mlra}:measured_thresh={mt}:"
                   f"offset={off}:linear=true",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", final_path,
        ], capture_output=True, timeout=300)
    else:
        subprocess.run([
            "ffmpeg", "-y", "-i", bgm_path,
            "-c:v", "copy",
            "-af", "loudnorm=I=-14:TP=-2.0:LRA=11",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", final_path,
        ], capture_output=True, timeout=300)

    elapsed = time.time() - t0
    if os.path.exists(final_path):
        dur = get_duration(final_path)
        sz = os.path.getsize(final_path)
        print(f"\n=== SEGMENT V4 (PBX VOICE) ===")
        print(f"  File: {final_path}")
        print(f"  Duration: {dur:.2f}s")
        print(f"  Size: {sz:,} bytes ({sz/1024/1024:.1f} MB)")
        print(f"  Render time: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    else:
        print(f"\nERROR: V4 render failed after {elapsed:.0f}s")
        sys.exit(1)
