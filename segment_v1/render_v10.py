#!/usr/bin/env python3
"""Render segment_v10.mp4 (16:9, 1920x1080, 24fps).

Changes from v9:
  1. Alpha watermark (pp_mark_wave_alpha.png) at 60% opacity, no black box
  2. VO bridge uses correct PBX stem from VO_MANIFEST.json (v9 reused v8 which had Connery)
  3. VO visuals: R5 style — freeze last frame, gaussian blur sigma 6,
     slow 1.0x->1.08x zoom, waveform bottom 22%, 1.0s pre-roll
  4. Produces concat_manifest.json for qa_gates.py
"""
import json, os, subprocess, sys, time, math, struct, wave, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scene_shoutout import render_shoutout, save_qa_frames

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

BASE = "/home/ultron/protocol_pulse/segment_v1"
QA = os.path.join(BASE, "qa_v10")
QA_V3 = os.path.join(BASE, "qa_v3")
QA_V7 = os.path.join(BASE, "qa_v7")
OUT = os.path.join(BASE, "out")
VO_DIR = os.path.join(BASE, "vo_audio")
BGM = "/home/ultron/protocol_pulse/video_pipeline_v3/assets/music/confident_02.mp3"
PP_MARK = os.path.join(BASE, "brand", "2026-11", "pp_mark_wave_alpha.png")

os.makedirs(QA, exist_ok=True)

sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
from relay import get_key

FPS = 24
PRE_ROLL = 1.0
WIDTH = 1920
HEIGHT = 1080
ACCENT_COLOR = (247, 147, 26)


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def ease_in_out(t):
    return 0.5 * (1 - math.cos(math.pi * t))


def render_vo_visual_v10(vo_wav, preceding_src, preceding_cut_out, output_mp4):
    """R5 VO visual: freeze last frame, blur sigma 6, 1.0x->1.08x zoom, waveform bottom 22%, pre-roll."""
    print(f"  Rendering R5 VO visual: {os.path.basename(output_mp4)}")

    vo_dur = get_duration(vo_wav)
    total_dur = PRE_ROLL + vo_dur
    total_frames = int(total_dur * FPS)
    preroll_frames = int(PRE_ROLL * FPS)

    print(f"    VO: {vo_dur:.2f}s + {PRE_ROLL}s pre-roll = {total_dur:.2f}s ({total_frames} frames)")

    # Extract last frame of preceding clip
    bg_png = os.path.join(QA, f"vo_bg_{os.path.basename(output_mp4).replace('.mp4', '.png')}")
    frame_ts = preceding_cut_out - 0.1
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(frame_ts), "-i", preceding_src,
        "-vframes", "1", "-vf", f"scale={WIDTH}:{HEIGHT}", "-q:v", "2", bg_png,
    ], capture_output=True, timeout=30)

    bg_img = Image.open(bg_png).convert("RGB")
    # Apply gaussian blur sigma 6
    bg_blurred = bg_img.filter(ImageFilter.GaussianBlur(radius=6))

    # Load VO audio RMS for waveform
    vo_frames = total_frames - preroll_frames
    try:
        with wave.open(vo_wav, 'rb') as wf:
            n = wf.getnframes()
            raw = wf.readframes(n)
        if wf.getsampwidth() == 2:
            samples = struct.unpack(f"<{n * wf.getnchannels()}h", raw)
        else:
            samples = [0] * n
        nc = wf.getnchannels()
        if nc > 1:
            samples = [samples[i] for i in range(0, len(samples), nc)]
        spf = max(1, len(samples) // max(vo_frames, 1))
        rms_vo = []
        for fi in range(vo_frames):
            start = fi * spf
            end = min(start + spf, len(samples))
            chunk = samples[start:end]
            rms_val = (sum(s * s for s in chunk) / max(len(chunk), 1)) ** 0.5 if chunk else 0
            rms_vo.append(min(1.0, rms_val / 12000))
    except Exception:
        rms_vo = [0.1] * vo_frames

    rms_values = [0.0] * preroll_frames + rms_vo

    # Render frames
    frames_dir = os.path.join(QA, f"vo_frames_{os.path.basename(output_mp4).replace('.mp4', '')}")
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

    # Waveform params — bottom 22%
    num_bars = 28
    bar_area_w = int(WIDTH * 0.65)
    bar_max_h = int(HEIGHT * 0.08)
    bar_y_center = int(HEIGHT * 0.89)
    bar_w = bar_area_w // num_bars - 2
    bar_x_start = (WIDTH - bar_area_w) // 2
    band_top = bar_y_center - bar_max_h - 10
    band_bottom = bar_y_center + bar_max_h + 10

    scale_start, scale_end = 1.00, 1.08

    for fi in range(total_frames):
        t = fi / max(total_frames - 1, 1)
        ease_t = ease_in_out(t)

        scale = scale_start + (scale_end - scale_start) * ease_t
        sw = int(WIDTH * scale)
        sh = int(HEIGHT * scale)
        scaled = bg_blurred.resize((sw, sh), Image.LANCZOS)
        left = (sw - WIDTH) // 2
        top = (sh - HEIGHT) // 2
        frame = scaled.crop((left, top, left + WIDTH, top + HEIGHT))

        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle([0, band_top, WIDTH, band_bottom], fill=(0, 0, 0, 204))

        for i in range(num_bars):
            idx = fi - num_bars // 2 + i
            val = rms_values[idx] if 0 <= idx < len(rms_values) else 0
            bar_h = max(2, int(val * bar_max_h))
            x = bar_x_start + i * (bar_w + 2)
            intensity = min(1.0, val * 2.5)
            alpha = int(153 * max(0.3, intensity))
            color = ACCENT_COLOR + (alpha,)
            draw.rectangle([x, bar_y_center - bar_h, x + bar_w, bar_y_center], fill=color)
            draw.rectangle([x, bar_y_center, x + bar_w, bar_y_center + bar_h], fill=color)

        composited = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")
        composited.save(os.path.join(frames_dir, f"frame_{fi:05d}.png"), "PNG")

    # Audio: silence + VO
    silence_wav = os.path.join(QA, "vo_16_silence.wav")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(PRE_ROLL), "-c:a", "pcm_s16le", silence_wav,
    ], capture_output=True, timeout=10)

    combined_wav = os.path.join(QA, f"vo_16_audio_{os.path.basename(output_mp4).replace('.mp4', '.wav')}")
    audio_list = os.path.join(QA, "vo_16_audio_list.txt")
    with open(audio_list, "w") as f:
        f.write(f"file '{silence_wav}'\n")
        f.write(f"file '{os.path.abspath(vo_wav)}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list,
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", combined_wav,
    ], capture_output=True, timeout=30)

    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-i", combined_wav,
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=120)

    if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
        dur = get_duration(output_mp4)
        print(f"    Output: {dur:.2f}s")
        shutil.rmtree(frames_dir)
        return True
    print("    ERROR: VO render failed")
    return False


def apply_watermark_alpha(input_mp4, output_mp4, mark_path, mark_px, margin,
                          opacity, fade_in_dur, shoutout_start):
    """Overlay alpha watermark on final concat. No black box — alpha PNG."""
    overlay_expr = (
        f"[1:v]scale={mark_px}:-1,format=rgba,"
        f"colorchannelmixer=aa={opacity},"
        f"fade=t=in:d={fade_in_dur}:alpha=1[wm];"
        f"[0:v][wm]overlay=W-w-{margin}:H-h-{margin}:"
        f"enable='between(t,0,{shoutout_start:.3f})':"
        f"shortest=1[vout]"
    )

    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", input_mp4,
        "-loop", "1", "-i", mark_path,
        "-filter_complex", overlay_expr,
        "-map", "[vout]", "-map", "0:a",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "copy",
        "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=600)

    if r.returncode != 0:
        print(f"    ffmpeg watermark stderr: {r.stderr.decode()[-500:]}")

    return os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 10000


if __name__ == "__main__":
    t0 = time.time()
    print("=== SEGMENT V10: 16:9 ===\n")

    with open(os.path.join(BASE, "edl_v2.json")) as f:
        edl = json.load(f)
    with open(os.path.join(BASE, "cuts_v3.json")) as f:
        cuts = json.load(f)
    with open(os.path.join(VO_DIR, "VO_MANIFEST.json")) as f:
        vo_manifest = json.load(f)

    # ========== STEP 1: Verify voice ==========
    print("=== STEP 1: VERIFY VOICE ===")
    voice_id = get_key("ELEVENLABS_VOICE_ID_PP")
    if not voice_id:
        print("FATAL: ELEVENLABS_VOICE_ID_PP not in .env")
        sys.exit(1)
    voice_id = voice_id.strip()
    print(f"  voice_id: {voice_id}")
    assert voice_id == "43nxoDRMpcLls4afQ9MK", f"Wrong voice_id: {voice_id}"

    # ========== STEP 2: Render VO visuals (R5) from correct PBX stems ==========
    print("\n=== STEP 2: RENDER VO VISUALS (R5 — blur + zoom + waveform) ===")

    # VO intro: after hook
    hook_cut = next((c for c in cuts if c["clip_id"] == "hook"), None)
    hook_src = os.path.join(BASE, "sources", f"{hook_cut['video_id']}.mp4")
    vo_intro_wav = os.path.join(VO_DIR, vo_manifest["intro"]["stem_wav"])
    vo_intro_mp4 = os.path.join(QA, "v10_vo_intro.mp4")
    render_vo_visual_v10(vo_intro_wav, hook_src, hook_cut["cut_out"], vo_intro_mp4)

    # VO bridge: after clip_03 — using CORRECT PBX stem from manifest
    clip03_cut = next((c for c in cuts if c["clip_id"] == "clip_03"), None)
    clip03_src = os.path.join(BASE, "sources", f"{clip03_cut['video_id']}.mp4")
    vo_bridge_wav = os.path.join(VO_DIR, vo_manifest["bridge_01"]["stem_wav"])
    vo_bridge_mp4 = os.path.join(QA, "v10_vo_bridge.mp4")
    render_vo_visual_v10(vo_bridge_wav, clip03_src, clip03_cut["cut_out"], vo_bridge_mp4)

    # ========== STEP 3: Build segment list ==========
    print("\n=== STEP 3: SEGMENT LIST ===")

    shoutout_path = os.path.join(QA_V7, "shoutout_16x9.mp4")
    assert os.path.exists(shoutout_path), f"Missing: {shoutout_path}"

    segments = [
        ("hook",          os.path.join(QA_V3, "final_hook.mp4"),       "talking_head"),
        ("vo_intro",      vo_intro_mp4,                                 "vo"),
        ("clip_01",       os.path.join(QA_V3, "final_clip_01.mp4"),    "talking_head"),
        ("clip_02",       os.path.join(QA_V3, "final_clip_02_v5.mp4"), "talking_head"),
        ("clip_03",       os.path.join(QA_V3, "final_clip_03.mp4"),    "talking_head"),
        ("vo_bridge",     vo_bridge_mp4,                                "vo"),
        ("clip_04",       os.path.join(QA_V3, "final_clip_04.mp4"),    "talking_head"),
        ("shoutout",      shoutout_path,                                "shoutout"),
        ("outro",         os.path.join(QA_V3, "final_outro.mp4"),      "outro"),
    ]

    for label, path, _ in segments:
        assert os.path.exists(path), f"MISSING: {path}"
        dur = get_duration(path)
        print(f"  {label}: {dur:.2f}s  ({path})")

    total_seg_dur = sum(get_duration(p) for _, p, _ in segments)
    print(f"\n  Total: {total_seg_dur:.1f}s")

    # ========== STEP 4: Concat ==========
    print("\n=== STEP 4: CONCAT ===")

    filelist = os.path.join(QA, "v10_filelist.txt")
    with open(filelist, "w") as f:
        for label, path, _ in segments:
            f.write(f"file '{path}'\n")

    concat_raw = os.path.join(QA, "v10_concat_raw.mp4")
    r = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
        "-vf", "setpts=PTS-STARTPTS",
        "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", concat_raw,
    ], capture_output=True, timeout=600)
    if r.returncode != 0:
        print(f"  ffmpeg stderr: {r.stderr.decode()[-500:]}")
    concat_dur = get_duration(concat_raw)
    print(f"  Concat: {concat_dur:.2f}s")

    # ========== STEP 5: Watermark (alpha) ==========
    print("\n=== STEP 5: ALPHA WATERMARK ===")

    cumulative = 0
    shoutout_start = 0
    for label, path, _ in segments:
        dur = get_duration(path)
        if label == "shoutout":
            shoutout_start = cumulative
            break
        cumulative += dur

    print(f"  Watermark: 0 → {shoutout_start:.2f}s")
    print(f"  Mark: {PP_MARK}")
    print(f"  96px, lower-right 40px margin, 60% opacity, 0.4s fade-in")

    concat_wm = os.path.join(QA, "v10_concat_wm.mp4")
    ok = apply_watermark_alpha(concat_raw, concat_wm, PP_MARK,
                               mark_px=96, margin=40, opacity=0.6,
                               fade_in_dur=0.4, shoutout_start=shoutout_start)
    if not ok:
        print("FATAL: Watermark overlay failed")
        sys.exit(1)
    print(f"  Watermarked: {get_duration(concat_wm):.2f}s")

    # ========== STEP 6: BGM mix ==========
    print("\n=== STEP 6: BGM MIX ===")

    bgm_path = os.path.join(QA, "v10_bgm.mp4")
    wm_dur = get_duration(concat_wm)
    bgm_fade_out_start = wm_dur - 1.5

    subprocess.run([
        "ffmpeg", "-y",
        "-i", concat_wm,
        "-stream_loop", "-1", "-i", BGM,
        "-filter_complex",
        f"[1:a]volume=-26dB,afade=t=in:d=1.0,afade=t=out:st={bgm_fade_out_start:.1f}:d=1.5[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", bgm_path,
    ], capture_output=True, timeout=300)
    print(f"  BGM mix: {get_duration(bgm_path):.2f}s")

    # ========== STEP 7: Loudnorm 2-pass + alimiter ==========
    print("\n=== STEP 7: LOUDNORM + ALIMITER ===")

    r = subprocess.run([
        "ffmpeg", "-y", "-i", bgm_path,
        "-af", "loudnorm=I=-14:TP=-2.0:LRA=11:print_format=json",
        "-f", "null", "-",
    ], capture_output=True, text=True, timeout=300)

    mi = None
    try:
        stderr = r.stderr
        js = stderr[stderr.rfind("{"):stderr.rfind("}") + 1]
        stats = json.loads(js)
        mi = stats["input_i"]
        mtp = stats["input_tp"]
        mlra = stats["input_lra"]
        mt = stats["input_thresh"]
        off = stats["target_offset"]
        print(f"  Measured: I={mi} TP={mtp} LRA={mlra}")
    except Exception as e:
        print(f"  WARNING: loudnorm parse error: {e}")

    normed_wav = os.path.join(QA, "v10_normed.wav")
    if mi:
        subprocess.run([
            "ffmpeg", "-y", "-i", bgm_path,
            "-af", f"loudnorm=I=-14:TP=-2.0:LRA=11:"
                   f"measured_I={mi}:measured_TP={mtp}:"
                   f"measured_LRA={mlra}:measured_thresh={mt}:"
                   f"offset={off}:linear=true",
            "-ar", "48000", "-ac", "2", normed_wav,
        ], capture_output=True, timeout=300)
    else:
        subprocess.run([
            "ffmpeg", "-y", "-i", bgm_path,
            "-af", "loudnorm=I=-14:TP=-2.0:LRA=11",
            "-ar", "48000", "-ac", "2", normed_wav,
        ], capture_output=True, timeout=300)

    final_path = os.path.join(OUT, "segment_v10.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", bgm_path,
        "-i", normed_wav,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
        "-af", "alimiter=limit=0.707946:level=false",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", final_path,
    ], capture_output=True, timeout=300)

    if not os.path.exists(final_path) or os.path.getsize(final_path) < 10000:
        print("FATAL: V10 render failed")
        sys.exit(1)

    # ========== STEP 8: Build concat manifest for qa_gates ==========
    print("\n=== STEP 8: CONCAT MANIFEST ===")

    # Get EDL words for each clip
    edl_map = {}
    for c in cuts:
        edl_map[c["clip_id"]] = c
    for clip_edl in edl.get("clips", []):
        idx = clip_edl["index"]
        cid = f"clip_{idx:02d}"
        if cid not in edl_map:
            continue
        edl_map[cid]["first_word_edl"] = clip_edl.get("first_word", "")
        edl_map[cid]["last_word_edl"] = clip_edl.get("last_word", "")
    # Hook words from EDL
    hook_edl = edl.get("hook", {})
    if "hook" in edl_map:
        edl_map["hook"]["first_word_edl"] = hook_edl.get("first_word", "")
        edl_map["hook"]["last_word_edl"] = hook_edl.get("last_word", "")

    cumul = 0.0
    manifest_segments = []
    for label, path, seg_type in segments:
        dur = get_duration(path)
        seg_entry = {
            "label": label,
            "start": round(cumul, 3),
            "end": round(cumul + dur, 3),
            "type": seg_type,
        }

        if seg_type == "talking_head":
            clip_id = label
            if clip_id in edl_map:
                seg_entry["first_word"] = edl_map[clip_id].get("first_word_edl", "")
                seg_entry["last_word"] = edl_map[clip_id].get("last_word_edl", "")
        elif seg_type == "vo":
            role_key = "intro" if "intro" in label else "bridge_01"
            if "signoff" in label:
                role_key = "signoff"
            seg_entry["text"] = vo_manifest.get(role_key, {}).get("text", "")

        manifest_segments.append(seg_entry)
        cumul += dur

    manifest_data = {
        "format": "16x9",
        "segments": manifest_segments,
        "shoutout_start": shoutout_start,
    }
    manifest_path = os.path.join(QA, "concat_manifest_16x9.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"  Manifest: {manifest_path}")

    # Contact sheet (12 frames, 4x3)
    print("\n=== CONTACT SHEET ===")
    contact_path = os.path.join(QA, "v10_16x9_contact.jpg")
    dur = get_duration(final_path)
    cframes_dir = os.path.join(QA, "v10_contact_16")
    os.makedirs(cframes_dir, exist_ok=True)
    for i in range(12):
        ts = dur * (i + 0.5) / 12
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(ts), "-i", final_path,
            "-vframes", "1", "-q:v", "2",
            os.path.join(cframes_dir, f"frame_{i:02d}.jpg"),
        ], capture_output=True, timeout=30)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", os.path.join(cframes_dir, "frame_%02d.jpg"),
        "-vf", "tile=4x3:padding=4:color=black",
        "-q:v", "3", contact_path,
    ], capture_output=True, timeout=30)
    print(f"  Saved: {contact_path}")

    v10_dur = get_duration(final_path)
    v10_size = os.path.getsize(final_path)
    r = subprocess.run(["md5sum", final_path], capture_output=True, text=True, timeout=30)
    md5 = r.stdout.strip()

    elapsed = time.time() - t0
    print(f"\n=== SEGMENT V10 (16:9) COMPLETE ===")
    print(f"  File: {final_path}")
    print(f"  Duration: {v10_dur:.3f}s")
    print(f"  Size: {v10_size:,} bytes ({v10_size / 1024 / 1024:.1f} MB)")
    print(f"  Render time: {elapsed:.0f}s ({elapsed / 60:.1f}min)")
    print(f"  md5sum: {md5}")
