#!/usr/bin/env python3
"""Render segment_v2 16:9 (1920x1080, 24fps).
Self-contained: extracts clips, renders VO visuals, shoutout, concat, watermark, BGM."""
import json, os, subprocess, sys, time, math, struct, wave, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

BASE = "/home/ultron/protocol_pulse/segment_v2"
QA = f"{BASE}/qa"
OUT = f"{BASE}/out"
VO_DIR = f"{BASE}/vo_audio"
SOURCES_DIR = f"{BASE}/sources"
BGM = "/home/ultron/protocol_pulse/video_pipeline_v3/assets/music/confident_02.mp3"
PP_MARK = f"{BASE}/brand/2026-11/pp_mark_wave_alpha.png"
AVATAR_DIR = "/home/ultron/protocol_pulse/segment_v1/brand/avatars"

os.makedirs(QA, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")

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


def extract_clip_mp4(src_mp4, cut_in, cut_out, output_mp4):
    """Extract a clip segment at 1920x1080x24fps."""
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(cut_in), "-to", str(cut_out),
        "-i", src_mp4,
        "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
               f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=0x0A0A0F,"
               f"setpts=PTS-STARTPTS",
        "-af", "asetpts=PTS-STARTPTS",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=120)
    return os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000


def render_vo_visual(vo_wav, preceding_src, preceding_cut_out, output_mp4, label):
    """R5: freeze last frame, blur, 1.0x->1.08x zoom, waveform, pre-roll."""
    print(f"  Rendering VO visual: {label}")
    vo_dur = get_duration(vo_wav)
    total_dur = PRE_ROLL + vo_dur
    total_frames = int(total_dur * FPS)
    preroll_frames = int(PRE_ROLL * FPS)

    bg_png = f"{QA}/vo_bg_{label}.png"
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(max(0, preceding_cut_out - 0.1)), "-i", preceding_src,
        "-vframes", "1", "-vf", f"scale={WIDTH}:{HEIGHT}", "-q:v", "2", bg_png,
    ], capture_output=True, timeout=30)

    bg_img = Image.open(bg_png).convert("RGB")
    bg_blurred = bg_img.filter(ImageFilter.GaussianBlur(radius=6))

    # Load VO audio RMS
    vo_frames = total_frames - preroll_frames
    try:
        with wave.open(vo_wav, 'rb') as wf:
            n = wf.getnframes()
            raw = wf.readframes(n)
            nc = wf.getnchannels()
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        if nc > 1:
            samples = samples[::nc]
        spf = max(1, len(samples) // max(vo_frames, 1))
        rms_vo = []
        for fi in range(vo_frames):
            s, e = fi * spf, min((fi+1) * spf, len(samples))
            chunk = samples[s:e]
            rms_val = np.sqrt(np.mean(chunk**2)) / 12000 if len(chunk) else 0
            rms_vo.append(min(1.0, rms_val))
    except Exception:
        rms_vo = [0.1] * vo_frames
    rms_values = [0.0] * preroll_frames + rms_vo

    frames_dir = f"{QA}/vo_frames_{label}"
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

    num_bars, bar_area_w, bar_max_h = 28, int(WIDTH * 0.65), int(HEIGHT * 0.08)
    bar_y_center = int(HEIGHT * 0.89)
    bar_w = bar_area_w // num_bars - 2
    bar_x_start = (WIDTH - bar_area_w) // 2
    band_top, band_bottom = bar_y_center - bar_max_h - 10, bar_y_center + bar_max_h + 10

    for fi in range(total_frames):
        t = fi / max(total_frames - 1, 1)
        scale = 1.0 + 0.08 * ease_in_out(t)
        sw, sh = int(WIDTH * scale), int(HEIGHT * scale)
        scaled = bg_blurred.resize((sw, sh), Image.LANCZOS)
        left, top = (sw - WIDTH) // 2, (sh - HEIGHT) // 2
        frame = scaled.crop((left, top, left + WIDTH, top + HEIGHT))

        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle([0, band_top, WIDTH, band_bottom], fill=(0, 0, 0, 204))

        for i in range(num_bars):
            idx = fi - num_bars // 2 + i
            val = rms_values[idx] if 0 <= idx < len(rms_values) else 0
            bar_h = max(2, int(val * bar_max_h))
            x = bar_x_start + i * (bar_w + 2)
            alpha = int(153 * max(0.3, min(1.0, val * 2.5)))
            color = ACCENT_COLOR + (alpha,)
            draw.rectangle([x, bar_y_center - bar_h, x + bar_w, bar_y_center], fill=color)
            draw.rectangle([x, bar_y_center, x + bar_w, bar_y_center + bar_h], fill=color)

        composited = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")
        composited.save(f"{frames_dir}/frame_{fi:05d}.png", "PNG")

    # Audio: silence + VO
    silence_wav = f"{QA}/vo_silence_{label}.wav"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(PRE_ROLL), "-c:a", "pcm_s16le", silence_wav,
    ], capture_output=True, timeout=10)

    combined_wav = f"{QA}/vo_assembled_{label}.wav"
    audio_list = f"{QA}/vo_list_{label}.txt"
    with open(audio_list, "w") as f:
        f.write(f"file '{silence_wav}'\nfile '{os.path.abspath(vo_wav)}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list,
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", combined_wav,
    ], capture_output=True, timeout=30)

    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS), "-i", f"{frames_dir}/frame_%05d.png",
        "-i", combined_wav,
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=120)

    ok = os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000
    if ok:
        print(f"    {get_duration(output_mp4):.2f}s")
        shutil.rmtree(frames_dir)
    return ok


def apply_watermark(input_mp4, output_mp4, shoutout_start):
    mark_px, margin, opacity, fade_dur = 120, 30, 0.5, 1.0
    filt = (
        f"[1:v]scale={mark_px}:-1,format=rgba,"
        f"colorchannelmixer=aa={opacity},"
        f"fade=t=in:d={fade_dur}:alpha=1[wm];"
        f"[0:v][wm]overlay=W-w-{margin}:H-h-{margin}:"
        f"enable='between(t,0,{shoutout_start:.3f})':"
        f"shortest=1[vout]"
    )
    r = subprocess.run([
        "ffmpeg", "-y", "-i", input_mp4, "-loop", "1", "-i", PP_MARK,
        "-filter_complex", filt, "-map", "[vout]", "-map", "0:a",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "copy",
        "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=600)
    return os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 10000


def add_bgm(input_mp4, output_mp4):
    """Mix BGM at -20dB under speech."""
    dur = get_duration(input_mp4)
    r = subprocess.run([
        "ffmpeg", "-y", "-i", input_mp4, "-stream_loop", "-1", "-i", BGM,
        "-filter_complex",
        f"[1:a]volume=0.1,afade=t=in:d=2,afade=t=out:st={dur-3}:d=3[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:weights=1 0.08[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=300)
    return os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 10000


if __name__ == "__main__":
    t0 = time.time()
    print("=== SEGMENT V2: 16:9 RENDER ===\n")

    with open(f"{BASE}/edl.json") as f:
        edl = json.load(f)
    with open(f"{BASE}/cuts_final.json") as f:
        cuts = json.load(f)
    with open(f"{VO_DIR}/VO_MANIFEST.json") as f:
        vo_manifest = json.load(f)

    # === STEP 1: Extract clips ===
    print("=== STEP 1: EXTRACT CLIPS ===")
    clip_paths = {}
    for cut in cuts:
        cid = cut["clip_id"]
        src = f"{SOURCES_DIR}/{cut['video_id']}.mp4"
        out = f"{QA}/clip_{cid}.mp4"
        print(f"  {cid}: {cut['cut_in']:.3f}-{cut['cut_out']:.3f} ({cut['cut_duration']:.1f}s)...", end=" ")
        if extract_clip_mp4(src, cut["cut_in"], cut["cut_out"], out):
            dur = get_duration(out)
            print(f"OK {dur:.2f}s")
            clip_paths[cid] = out
        else:
            print("FAIL")

    # === STEP 2: Render VO visuals ===
    print("\n=== STEP 2: VO VISUALS ===")
    vo_paths = {}
    vo_files = {m["type"]: m["wav"] for m in vo_manifest}

    # Intro VO: freeze from hook clip out
    hook_cut = next((c for c in cuts if c["clip_id"] == "hook"), None)
    if hook_cut and "intro" in vo_files:
        vo_mp4 = f"{QA}/vo_intro.mp4"
        src = f"{SOURCES_DIR}/{hook_cut['video_id']}.mp4"
        if render_vo_visual(vo_files["intro"], src, hook_cut["cut_out"], vo_mp4, "intro"):
            vo_paths["intro"] = vo_mp4

    # Bridge VOs: freeze from preceding clip
    for m in vo_manifest:
        if m["type"].startswith("bridge_"):
            after = m.get("after_clip")
            if after:
                cid = f"clip_{after:02d}"
                cut = next((c for c in cuts if c["clip_id"] == cid), None)
                if cut:
                    vo_mp4 = f"{QA}/vo_{m['type']}.mp4"
                    src = f"{SOURCES_DIR}/{cut['video_id']}.mp4"
                    if render_vo_visual(m["wav"], src, cut["cut_out"], vo_mp4, m["type"]):
                        vo_paths[m["type"]] = vo_mp4

    # Signoff VO: freeze from last clip
    last_clip_cut = cuts[-1]
    if "signoff" in vo_files:
        vo_mp4 = f"{QA}/vo_signoff.mp4"
        src = f"{SOURCES_DIR}/{last_clip_cut['video_id']}.mp4"
        if render_vo_visual(vo_files["signoff"], src, last_clip_cut["cut_out"], vo_mp4, "signoff"):
            vo_paths["signoff"] = vo_mp4

    # === STEP 3: Shoutout scene ===
    print("\n=== STEP 3: SHOUTOUT ===")
    shoutout_path = f"{QA}/shoutout_16x9.mp4"

    # Build channels list from EDL
    channels_in_edl = []
    seen_ch = set()
    for clip in edl["clips"]:
        ch = clip["channel"]
        if ch not in seen_ch:
            seen_ch.add(ch)
            handle = clip["handle"]
            # Map channel to avatar
            avatar_map = {
                "Simply Bitcoin": "simply_bitcoin.png",
                "BTC Sessions": "btc_sessions.png",
                "CoinDesk": "coindesk.png",
                "Bitcoin Magazine": "simply_bitcoin.png",  # fallback
                "The Bitcoin Layer": "simply_bitcoin.png",  # fallback
            }
            avatar = os.path.join(AVATAR_DIR, avatar_map.get(ch, "simply_bitcoin.png"))
            channels_in_edl.append({"name": ch, "handle": handle, "avatar_path": avatar})

    try:
        from scene_shoutout import render_shoutout
        signoff_wav = vo_files.get("signoff")
        render_shoutout(channels_in_edl, (WIDTH, HEIGHT), signoff_wav, shoutout_path)
        print(f"  Shoutout: {get_duration(shoutout_path):.2f}s")
    except Exception as e:
        print(f"  WARNING: Shoutout failed: {e}")
        # Create a simple black frame as fallback
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x0A0A0F:size={WIDTH}x{HEIGHT}:d=5:r={FPS}",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", "5", "-c:v", "h264_nvenc", "-c:a", "aac", "-shortest",
            "-movflags", "+faststart", shoutout_path,
        ], capture_output=True, timeout=30)

    # === STEP 4: Build segment list and concat ===
    print("\n=== STEP 4: CONCAT ===")
    segments = []

    # Build order: hook -> vo_intro -> clips interleaved with bridges -> vo_signoff -> shoutout
    if "hook" in clip_paths:
        segments.append(("hook", clip_paths["hook"]))
    if "intro" in vo_paths:
        segments.append(("vo_intro", vo_paths["intro"]))

    for i, clip in enumerate(edl["clips"]):
        cid = f"clip_{clip['index']:02d}"
        if cid in clip_paths:
            segments.append((cid, clip_paths[cid]))
        # Check for bridge after this clip
        bridge_key = f"bridge_{clip['index']}"
        if bridge_key in vo_paths:
            segments.append((f"vo_{bridge_key}", vo_paths[bridge_key]))

    if "signoff" in vo_paths:
        segments.append(("vo_signoff", vo_paths["signoff"]))
    segments.append(("shoutout", shoutout_path))

    print("  Segments:")
    for label, path in segments:
        dur = get_duration(path)
        print(f"    {label}: {dur:.2f}s")

    filelist = f"{QA}/concat_filelist.txt"
    with open(filelist, "w") as f:
        for _, path in segments:
            f.write(f"file '{path}'\n")

    concat_raw = f"{QA}/concat_raw.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
        "-vf", "setpts=PTS-STARTPTS",
        "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", concat_raw,
    ], capture_output=True, timeout=600)
    concat_dur = get_duration(concat_raw)
    print(f"  Concat: {concat_dur:.2f}s")

    # === STEP 5: Watermark ===
    print("\n=== STEP 5: WATERMARK ===")
    cumulative = 0
    shoutout_start = concat_dur - 5
    for label, path in segments:
        dur = get_duration(path)
        if label == "shoutout":
            shoutout_start = cumulative
            break
        cumulative += dur

    watermarked = f"{QA}/watermarked.mp4"
    if apply_watermark(concat_raw, watermarked, shoutout_start):
        print(f"  Watermarked: {get_duration(watermarked):.2f}s")
    else:
        print("  WARNING: Watermark failed, using raw concat")
        watermarked = concat_raw

    # === STEP 6: BGM ===
    print("\n=== STEP 6: BGM MIX ===")
    final_path = f"{OUT}/segment_v2.mp4"
    if add_bgm(watermarked, final_path):
        final_dur = get_duration(final_path)
        final_size = os.path.getsize(final_path) / 1024 / 1024
        print(f"  Final: {final_dur:.2f}s, {final_size:.1f} MB")
    else:
        print("  WARNING: BGM failed, using watermarked")
        shutil.copy(watermarked, final_path)

    # === STEP 7: Write manifest ===
    manifest = {
        "segments": [{"label": l, "path": p, "duration": get_duration(p)} for l, p in segments],
        "final": final_path,
        "duration": get_duration(final_path),
    }
    with open(f"{QA}/concat_manifest_16x9.json", "w") as f:
        json.dump(manifest, f, indent=2)

    elapsed = time.time() - t0
    print(f"\n=== DONE in {elapsed/60:.1f} min ===")
    print(f"Output: {final_path}")
