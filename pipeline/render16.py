#!/usr/bin/env python3
"""pipeline/render16.py — Parameterised 16:9 renderer.

FROZEN from segment_v1/render_v12.py. Logic unchanged.
Only difference: paths resolved from --segment dir instead of hardcoded BASE.

Usage:
    python3 -m pipeline.render16 --segment <segment_dir> [--qa-version N]
"""
import argparse
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import time
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

if os.environ.get("CUDA_VISIBLE_DEVICES") not in ("", "-1"):   # L-r: an explicit CPU request stays CPU (this line
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"                    # forced GPU0 into CPU test sessions); else GPU0 only

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)
from config import verify_vo_voice
from config import (FPS, PRE_ROLL, WIDTH, HEIGHT, ACCENT_COLOR,
                    NVENC_QP_FINAL, NVENC_QP_INTERMEDIATE,
                    resolve_paths, resolve_brand, resolve_bgm,
                    conform_outro)

# Import shoutout renderer from segment_v1 (frozen)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "segment_v1"))   # this checkout, never a fixed path (Claude-gates C4)
from scene_shoutout import render_shoutout, save_qa_frames

# Import relay for API keys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_pipeline_v3"))   # this checkout, never a fixed path (Claude-gates C4)
from relay import get_key


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def ease_in_out(t):
    return 0.5 * (1 - math.cos(math.pi * t))


def render_vo_visual(vo_wav, preceding_src, preceding_cut_out, output_mp4, label, qa_dir):
    """R5 VO visual: freeze last frame, blur sigma 6, 1.0x->1.08x zoom, waveform bottom 22%, pre-roll.
    Returns the path to the assembled VO WAV (silence + stem) for G6 measurement."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
    print(f"  Rendering R5 VO visual: {os.path.basename(output_mp4)}")

    vo_dur = get_duration(vo_wav)
    total_dur = PRE_ROLL + vo_dur
    total_frames = int(total_dur * FPS)
    preroll_frames = int(PRE_ROLL * FPS)

    print(f"    VO: {vo_dur:.2f}s + {PRE_ROLL}s pre-roll = {total_dur:.2f}s ({total_frames} frames)")

    bg_png = os.path.join(qa_dir, f"vo_bg_{label}.png")
    frame_ts = preceding_cut_out - 0.1
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(frame_ts), "-i", preceding_src,
        "-vframes", "1", "-vf", f"scale={WIDTH}:{HEIGHT}", "-q:v", "2", bg_png,
    ], capture_output=True, timeout=30)

    bg_img = Image.open(bg_png).convert("RGB")
    bg_blurred = bg_img.filter(ImageFilter.GaussianBlur(radius=6))

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

    frames_dir = os.path.join(qa_dir, f"vo_frames_{label}")
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

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
    silence_wav = os.path.join(qa_dir, f"vo_silence_{label}.wav")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(PRE_ROLL), "-c:a", "pcm_s16le", silence_wav,
    ], capture_output=True, timeout=10, check=True)

    # R2-06: Resample VO stem to 48000 Hz stereo BEFORE concat
    # ElevenLabs outputs 22050 Hz mono; concat demuxer needs matching formats
    resampled_wav = os.path.join(qa_dir, f"vo_stem_48k_{label}.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", os.path.abspath(vo_wav),
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", resampled_wav,
    ], capture_output=True, timeout=30, check=True)

    combined_wav = os.path.join(qa_dir, f"vo_assembled_{label}.wav")
    audio_list = os.path.join(qa_dir, f"vo_audio_list_{label}.txt")
    with open(audio_list, "w") as f:
        f.write(f"file '{silence_wav}'\n")
        f.write(f"file '{resampled_wav}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list,
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", combined_wav,
    ], capture_output=True, timeout=30, check=True)

    gpu0.raise_if_oom(subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-i", combined_wav,
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=120), "render16 nvenc")

    if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
        dur = get_duration(output_mp4)
        print(f"    Output: {dur:.2f}s")
        shutil.rmtree(frames_dir)
        return combined_wav
    print("    ERROR: VO render failed")
    return None


def apply_watermark_alpha(input_mp4, output_mp4, mark_path, mark_px, margin,
                          opacity, fade_in_dur, shoutout_start):
    """Overlay alpha watermark on final concat. No black box -- alpha PNG."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
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
        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_FINAL),
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "copy",
        "-movflags", "+faststart", output_mp4,
    ], capture_output=True, timeout=600)
    gpu0.raise_if_oom(r, "render16 nvenc")      # L-r: never a later "render failed"

    if r.returncode != 0:
        print(f"    ffmpeg watermark stderr: {r.stderr.decode()[-500:]}")

    return os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 10000


def render_16x9(segment_dir, qa_version=None, output_name="segment.mp4",
                alimiter_dbfs=-3.0):
    """Full 16:9 render pipeline. Returns (final_path, manifest_path, vo_assembled_tracks) or raises."""
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident
    t0 = time.time()
    print("=== RENDER 16:9 ===\n")

    paths = resolve_paths(segment_dir, qa_version)
    qa_dir = paths["qa_dir"]
    out_dir = paths["out_dir"]

    # Load data files
    with open(paths["edl_json"]) as f:
        edl = json.load(f)
    with open(paths["cuts_json"]) as f:
        cuts = json.load(f)
    with open(paths["vo_manifest"]) as f:
        vo_manifest = json.load(f)

    pp_mark = resolve_brand(segment_dir)
    bgm_track = resolve_bgm(segment_dir)

    # ========== STEP 1: Verify voice ==========
    print("=== STEP 1: VERIFY VOICE ===")
    voice_id, model_id = verify_vo_voice(vo_manifest)
    print(f"  voice_id: {voice_id}")
    print(f"  model: {model_id}")

    # ========== STEP 2: Render VO visuals (R5) ==========
    print("\n=== STEP 2: RENDER VO VISUALS ===")

    vo_assembled_tracks = {}
    sources_dir = paths["sources_dir"]

    # Find VO entries in manifest that have stem_wav
    vo_entries = []
    for key in ["intro", "bridge_01", "signoff"]:
        if key in vo_manifest and "stem_wav" in vo_manifest[key]:
            vo_entries.append((key, vo_manifest[key]))

    # Render intro VO visual
    if "intro" in vo_manifest:
        hook_cut = next((c for c in cuts if c["clip_id"] == "hook"), None)
        if hook_cut:
            hook_src = os.path.join(sources_dir, f"{hook_cut['video_id']}.mp4")
            vo_intro_wav = os.path.join(paths["vo_dir"], vo_manifest["intro"]["stem_wav"])
            vo_intro_mp4 = os.path.join(qa_dir, "vo_intro.mp4")
            assembled = render_vo_visual(
                vo_intro_wav, hook_src, hook_cut["cut_out"], vo_intro_mp4, "vo_intro", qa_dir)
            if assembled:
                vo_assembled_tracks["vo_intro"] = assembled

    # Render bridge VO visual(s)
    # Map manifest bridge keys to EDL after_clip values
    edl_bridges = edl.get("vo", {}).get("bridges", [])
    bridge_keys = sorted([k for k in vo_manifest if k.startswith("bridge_")])
    for bi, bkey in enumerate(bridge_keys):
        bridge_data = vo_manifest[bkey]
        # Use EDL after_clip to find preceding clip (the correct source for BG)
        if bi < len(edl_bridges) and "after_clip" in edl_bridges[bi]:
            after_clip_idx = edl_bridges[bi]["after_clip"]
        else:
            # Fallback: bridge_NN means after clip NN (old convention)
            after_clip_idx = int(bkey.split("_")[1])
        preceding_clip_id = f"clip_{after_clip_idx:02d}"
        last_clip_cut = next((c for c in cuts if c["clip_id"] == preceding_clip_id), None)
        if not last_clip_cut:
            last_clip_cut = next((c for c in cuts if c["clip_id"] == "hook"), cuts[0])

        clip_src = os.path.join(sources_dir, f"{last_clip_cut['video_id']}.mp4")
        vo_bridge_wav = os.path.join(paths["vo_dir"], bridge_data["stem_wav"])
        vo_bridge_mp4 = os.path.join(qa_dir, f"vo_{bkey}.mp4")
        assembled = render_vo_visual(
            vo_bridge_wav, clip_src, last_clip_cut["cut_out"], vo_bridge_mp4, f"vo_{bkey}", qa_dir)
        if assembled:
            vo_assembled_tracks[f"vo_{bkey}"] = assembled

    print(f"\n  Assembled VO tracks: {list(vo_assembled_tracks.keys())}")

    # ========== STEP 3: Build segment list ==========
    print("\n=== STEP 3: SEGMENT LIST ===")

    # Build segments from EDL structure
    segments = []

    # Hook
    segments.append(("hook", _find_clip_file(qa_dir, "hook", cuts, sources_dir), "talking_head"))

    # Intro VO (M12: required if EDL has intro text)
    vo_intro_mp4 = os.path.join(qa_dir, "vo_intro.mp4")
    if edl.get("vo", {}).get("intro"):
        if not os.path.exists(vo_intro_mp4):
            raise FileNotFoundError(f"STOP: intro VO missing: {vo_intro_mp4}")
        segments.append(("vo_intro", vo_intro_mp4, "vo"))

    # Build bridge placement map: clip_index -> bridge manifest key
    bridge_after_map = {}  # {after_clip_idx: bridge_key}
    for bi, bkey in enumerate(bridge_keys):
        if bi < len(edl_bridges) and "after_clip" in edl_bridges[bi]:
            bridge_after_map[edl_bridges[bi]["after_clip"]] = bkey
        else:
            bridge_after_map[int(bkey.split("_")[1])] = bkey

    # Clips and bridges interleaved per EDL
    clip_ids = sorted([c["clip_id"] for c in cuts if c["clip_id"].startswith("clip_")])
    for clip_id in clip_ids:
        clip_file = _find_clip_file(qa_dir, clip_id, cuts, sources_dir)
        segments.append((clip_id, clip_file, "talking_head"))

        # Check if a bridge follows this clip (per EDL after_clip)
        clip_idx = int(clip_id.split("_")[1])
        if clip_idx in bridge_after_map:
            bkey = bridge_after_map[clip_idx]
            vo_bridge_mp4 = os.path.join(qa_dir, f"vo_{bkey}.mp4")
            if not os.path.exists(vo_bridge_mp4):
                raise FileNotFoundError(f"STOP: bridge VO missing: {vo_bridge_mp4}")
            segments.append((f"vo_{bkey}", vo_bridge_mp4, "vo"))

    # Shoutout (M12: required)
    shoutout_path = _find_shoutout(qa_dir)
    segments.append(("shoutout", shoutout_path, "shoutout"))

    # Outro (M12: required)
    outro_path = _find_outro(qa_dir)
    segments.append(("outro", outro_path, "outro"))

    for label, path, _ in segments:
        assert os.path.exists(path), f"MISSING: {path}"
        dur = get_duration(path)
        print(f"  {label}: {dur:.2f}s  ({path})")

    total_seg_dur = sum(get_duration(p) for _, p, _ in segments)
    print(f"\n  Total: {total_seg_dur:.1f}s")

    # ========== STEP 4: Concat ==========
    print("\n=== STEP 4: CONCAT ===")

    filelist = os.path.join(qa_dir, "filelist.txt")
    with open(filelist, "w") as f:
        for label, path, _ in segments:
            f.write(f"file '{path}'\n")

    concat_raw = os.path.join(qa_dir, "concat_raw.mp4")
    concat_partial = concat_raw.replace(".mp4", ".partial.mp4")
    timeline = _transition_concat(segment_dir, segments, concat_partial, WIDTH, HEIGHT, qa_dir)
    if timeline is None:                     # no TRANSITIONS.json: the frozen hard-cut concat (v2f)
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
            "-vf", "setpts=PTS-STARTPTS",
            "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
            "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_FINAL),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", concat_partial,
        ], capture_output=True, timeout=600, check=True)
    os.replace(concat_partial, concat_raw)
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
    if timeline is not None:
        shoutout_start = next((e["start"] for e in timeline if e["label"] == "shoutout"), shoutout_start)

    print(f"  Watermark: 0 -> {shoutout_start:.2f}s")

    concat_wm = os.path.join(qa_dir, "concat_wm.mp4")
    ok = apply_watermark_alpha(concat_raw, concat_wm, pp_mark,
                               mark_px=96, margin=40, opacity=0.6,
                               fade_in_dur=0.4, shoutout_start=shoutout_start)
    if not ok:
        print("FATAL: Watermark overlay failed")
        sys.exit(1)
    print(f"  Watermarked: {get_duration(concat_wm):.2f}s")

    # ========== STEP 6: BGM mix ==========
    print("\n=== STEP 6: BGM MIX ===")

    bgm_path = os.path.join(qa_dir, "bgm.mp4")
    wm_dur = get_duration(concat_wm)
    bgm_fade_out_start = wm_dur - 1.5

    bgm_partial = bgm_path.replace(".mp4", ".partial.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", concat_wm,
        "-stream_loop", "-1", "-i", bgm_track,
        "-filter_complex",
        f"[1:a]volume=-26dB,afade=t=in:d=1.0,afade=t=out:st={bgm_fade_out_start:.1f}:d=1.5[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", bgm_partial,
    ], capture_output=True, timeout=300, check=True)
    os.replace(bgm_partial, bgm_path)
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

    normed_wav = os.path.join(qa_dir, "normed.wav")
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

    final_path = os.path.join(out_dir, output_name)
    final_partial = final_path.replace(".mp4", ".partial.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", bgm_path,
        "-i", normed_wav,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
        "-af", f"alimiter=limit={10 ** (alimiter_dbfs / 20):.6f}:level=false",  # {alimiter_dbfs} dBFS
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", final_partial,
    ], capture_output=True, timeout=300, check=True)
    os.replace(final_partial, final_path)

    # ========== STEP 8: Build concat manifest for qa_gates ==========
    print("\n=== STEP 8: CONCAT MANIFEST ===")

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
    hook_edl = edl.get("hook", {})
    if "hook" in edl_map:
        edl_map["hook"]["first_word_edl"] = hook_edl.get("first_word", "")
        edl_map["hook"]["last_word_edl"] = hook_edl.get("last_word", "")

    cumul = 0.0
    manifest_segments = []
    tl = {e["label"]: e for e in timeline} if timeline is not None else {}
    for label, path, seg_type in (segments if timeline is None else
                                  [(e["label"], None, e["type"]) for e in timeline]):
        dur = get_duration(path) if timeline is None else tl[label]["end"] - tl[label]["start"]
        start = cumul if timeline is None else tl[label]["start"]
        seg_entry = {
            "label": label,
            "start": round(start, 3),
            "end": round(start + dur, 3),
            "type": seg_type,
        }

        if seg_type == "talking_head":
            clip_id = label
            if clip_id in edl_map:
                seg_entry["first_word"] = edl_map[clip_id].get("first_word_edl", "")
                seg_entry["last_word"] = edl_map[clip_id].get("last_word_edl", "")
        elif seg_type == "vo":
            role_key = "intro" if "intro" in label else label.replace("vo_", "")
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
    manifest_path = os.path.join(qa_dir, "concat_manifest_16x9.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"  Manifest: {manifest_path}")

    # Save assembled VO tracks map for qa_gates
    vo_tracks_path = os.path.join(qa_dir, "vo_assembled_tracks.json")
    with open(vo_tracks_path, "w") as f:
        json.dump(vo_assembled_tracks, f, indent=2)
    print(f"  VO assembled tracks: {vo_tracks_path}")

    final_dur = get_duration(final_path)
    final_size = os.path.getsize(final_path)
    elapsed = time.time() - t0
    print(f"\n=== 16:9 COMPLETE ===")
    print(f"  File: {final_path}")
    print(f"  Duration: {final_dur:.3f}s")
    print(f"  Size: {final_size:,} bytes ({final_size / 1024 / 1024:.1f} MB)")
    print(f"  Render time: {elapsed:.0f}s ({elapsed / 60:.1f}min)")

    return final_path, manifest_path, vo_assembled_tracks


def _transition_concat(segment_dir, segments, out_path, w, h, qa_dir):
    """Phase 3 / DEC-4: when the run declares TRANSITIONS.json, concatenate with transitions between
    segments of different channels (pipeline/pulse_transitions.py) and return the timeline; else None."""
    tr_path = os.path.join(segment_dir, "TRANSITIONS.json")
    if not os.path.exists(tr_path):
        return None
    import pulse_transitions as TR      # NOT 'transitions': video_pipeline_v3/transitions.py shadows it (E-FAIL-021)
    with open(tr_path) as f:
        tr = json.load(f)
    junctions = TR.plan(segments, tr["channels"], {k: tuple(v) for k, v in tr["lead_tail"].items()},
                        tr["style"])
    print(f"  Transitions ({tr['style']}): {[(j['after'], j['frames'], j['kind']) for j in junctions]}")
    return TR.concat(segments, junctions, out_path, NVENC_QP_FINAL, w, h, qa_dir)


# ── Helpers for finding pre-rendered clip files ──

def _find_clip_file(qa_dir, clip_id, cuts=None, sources_dir=None):
    """Find the pre-rendered clip file in the CURRENT qa_dir only (M12: no cross-qa, no raw fallback)."""
    import glob as _glob
    pattern = os.path.join(qa_dir, f"final_{clip_id}*.mp4")
    best = None
    best_version = -1
    for hit in _glob.glob(pattern):
        basename = os.path.basename(hit)
        name_no_ext = basename.replace("final_", "").replace(".mp4", "")
        if not name_no_ext.startswith(clip_id):
            continue
        rest = name_no_ext[len(clip_id):]
        if rest == "":
            version = 0
        elif rest.startswith("_v") and rest[2:].isdigit():
            version = int(rest[2:])
        else:
            continue
        if version > best_version:
            best = hit
            best_version = version
    if best:
        return best
    raise FileNotFoundError(f"STOP: clip file for '{clip_id}' not found in {qa_dir}")


def _find_shoutout(qa_dir, segment_dir=None):
    """Find shoutout in CURRENT qa_dir only (M12: no cross-qa scanning)."""
    for name in ["shoutout_16x9.mp4", "shoutout.mp4"]:
        candidate = os.path.join(qa_dir, name)
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"STOP: shoutout not found in {qa_dir}")


def _find_outro(qa_dir, segment_dir=None):
    """Find 16:9 outro. Prefers PBX new outro (Amendment 1 §2), falls back to qa_dir."""
    try:
        return conform_outro("16x9")
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        import gpu0
        if gpu0.is_oom(e):           # L-r: an NVENC out-of-memory is never a fallback (E-FAIL-052)
            raise gpu0.GpuOOM(f"outro conform: CUDA/NVENC out of memory ({e})") from e
        print(f"  PBX outro conform failed ({e}), falling back to qa_dir")
    for name in ["final_outro.mp4", "outro.mp4"]:
        candidate = os.path.join(qa_dir, name)
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"STOP: outro not found in {qa_dir}")


def main():
    p = argparse.ArgumentParser(description="Parameterised 16:9 renderer (frozen from render_v12.py)")
    p.add_argument("--segment", required=True, help="Segment directory")
    p.add_argument("--qa-version", type=int, default=None, help="QA version number")
    p.add_argument("--output-name", default="segment.mp4", help="Output filename")
    args = p.parse_args()

    render_16x9(args.segment, args.qa_version, args.output_name)


if __name__ == "__main__":
    main()
