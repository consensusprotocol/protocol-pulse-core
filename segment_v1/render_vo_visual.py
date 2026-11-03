#!/usr/bin/env python3
"""Render VO visual segments: Ken Burns zoom on last frame + waveform overlay.
Used for both VO intro and VO bridge segments.

Ken Burns: 1.00→1.06 scale with ease-in-out over VO duration
Waveform: 28 vertical bars, centered bottom third, #F7931A at 60% opacity
Background: 80% black band behind waveform
"""
import json, os, subprocess, sys, wave, struct, math, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE = "/home/ultron/protocol_pulse/segment_v1"
SOURCES = os.path.join(BASE, "sources")
VO_DIR = os.path.join(BASE, "vo_audio")
QA = os.path.join(BASE, "qa_v3")
os.makedirs(QA, exist_ok=True)

FPS = 24  # User spec: 24fps for final
ACCENT_COLOR = (247, 147, 26)  # #F7931A Bitcoin orange


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def extract_last_frame(src_mp4, timestamp, out_png, width=1920, height=1080):
    """Extract a frame from source at timestamp."""
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(timestamp), "-i", src_mp4,
        "-vframes", "1", "-vf", f"scale={width}:{height}",
        "-q:v", "2", out_png,
    ], capture_output=True, timeout=30)
    return os.path.exists(out_png)


def load_audio_rms(wav_path, num_frames):
    """Load WAV and compute RMS per video frame (adapted from waveform_viz.py)."""
    try:
        with wave.open(wav_path, 'rb') as wf:
            n = wf.getnframes()
            sr = wf.getframerate()
            raw = wf.readframes(n)
        if wf.getsampwidth() == 2:
            samples = struct.unpack(f"<{n * wf.getnchannels()}h", raw)
        else:
            return [0.1] * num_frames
        # Average channels if stereo
        nc = wf.getnchannels()
        if nc > 1:
            samples = [samples[i] for i in range(0, len(samples), nc)]
        samples_per_frame = max(1, len(samples) // max(num_frames, 1))
        rms_values = []
        for f in range(num_frames):
            start = f * samples_per_frame
            end = min(start + samples_per_frame, len(samples))
            chunk = samples[start:end]
            if chunk:
                rms = (sum(s * s for s in chunk) / len(chunk)) ** 0.5
                normalized = min(1.0, rms / 12000)
            else:
                normalized = 0
            rms_values.append(normalized)
        return rms_values
    except Exception as e:
        print(f"  Audio load error: {e}")
        return [0.1] * num_frames


def ease_in_out(t):
    """Smooth ease-in-out: 0→1 with acceleration/deceleration."""
    return 0.5 * (1 - math.cos(math.pi * t))


def render_vo_segment(vo_wav, preceding_clip_src, preceding_cut_out,
                      output_mp4, width=1920, height=1080, preview=False):
    """Render a VO segment with Ken Burns + waveform overlay.

    Args:
        vo_wav: path to VO audio WAV
        preceding_clip_src: source MP4 of the clip before this VO
        preceding_cut_out: timestamp of the last frame of preceding clip
        output_mp4: output path
        width/height: output resolution
        preview: if True, render at 640x360
    """
    if preview:
        width, height = 640, 360

    vo_dur = get_duration(vo_wav)
    num_frames = int(vo_dur * FPS)
    if num_frames <= 0:
        print(f"  ERROR: VO duration {vo_dur}s → 0 frames")
        return False

    print(f"  VO duration: {vo_dur:.3f}s → {num_frames} frames at {FPS}fps")

    # 1. Extract last frame of preceding clip
    bg_png = os.path.join(QA, "vo_bg_frame.png")
    # Use slightly before cut_out to get a clean frame
    frame_ts = preceding_cut_out - 0.1
    extract_last_frame(preceding_clip_src, frame_ts, bg_png, width, height)
    if not os.path.exists(bg_png):
        print(f"  ERROR: Could not extract background frame")
        return False
    bg_img = Image.open(bg_png).convert("RGB").resize((width, height), Image.LANCZOS)

    # 2. Load VO audio RMS for waveform
    rms_values = load_audio_rms(vo_wav, num_frames)

    # 3. Render frame sequence to temp directory
    frames_dir = os.path.join(QA, "vo_frames")
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

    # Ken Burns params
    scale_start = 1.00
    scale_end = 1.06

    # Waveform params
    num_bars = 28
    bar_area_w = int(width * 0.65)
    bar_max_h = int(height * 0.12)
    bar_y_center = int(height * 0.72)  # bottom third
    bar_w = bar_area_w // num_bars - 2
    bar_gap = 2
    bar_x_start = (width - bar_area_w) // 2

    # Background band for waveform
    band_top = bar_y_center - bar_max_h - 10
    band_bottom = bar_y_center + bar_max_h + 10

    print(f"  Rendering {num_frames} frames...", end="", flush=True)
    for frame_idx in range(num_frames):
        t = frame_idx / max(num_frames - 1, 1)
        ease_t = ease_in_out(t)

        # Ken Burns: scale from 1.00 to 1.06
        scale = scale_start + (scale_end - scale_start) * ease_t
        scaled_w = int(width * scale)
        scaled_h = int(height * scale)
        scaled = bg_img.resize((scaled_w, scaled_h), Image.LANCZOS)
        # Center crop back to output size
        left = (scaled_w - width) // 2
        top = (scaled_h - height) // 2
        frame = scaled.crop((left, top, left + width, top + height))

        # Draw semi-transparent black band behind waveform
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        draw_overlay.rectangle(
            [0, band_top, width, band_bottom],
            fill=(0, 0, 0, 204)  # 80% opacity black
        )

        # Draw waveform bars
        # Use a window of RMS values around current frame
        for i in range(num_bars):
            sample_idx = frame_idx - num_bars // 2 + i
            if 0 <= sample_idx < len(rms_values):
                val = rms_values[sample_idx]
            else:
                val = 0

            bar_h = int(val * bar_max_h)
            bar_h = max(bar_h, 2)  # minimum visible

            x = bar_x_start + i * (bar_w + bar_gap)

            # Color: accent color with intensity-based alpha
            intensity = min(1.0, val * 2.5)
            alpha = int(153 * max(0.3, intensity))  # 60% max opacity, 18% min
            r, g, b = ACCENT_COLOR
            color = (r, g, b, alpha)

            # Top half
            draw_overlay.rectangle(
                [x, bar_y_center - bar_h, x + bar_w, bar_y_center],
                fill=color
            )
            # Bottom mirror
            draw_overlay.rectangle(
                [x, bar_y_center, x + bar_w, bar_y_center + bar_h],
                fill=color
            )

        # Composite
        frame_rgba = frame.convert("RGBA")
        composited = Image.alpha_composite(frame_rgba, overlay)
        final = composited.convert("RGB")

        frame_path = os.path.join(frames_dir, f"frame_{frame_idx:05d}.png")
        final.save(frame_path, "PNG")

        if frame_idx % 50 == 0:
            print(".", end="", flush=True)

    print(f" done ({num_frames} frames)")

    # 4. Encode frames + audio to MP4
    # Use h264_nvenc for speed
    crf = "28" if preview else "20"
    preset = "p4" if not preview else "p1"

    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-i", vo_wav,
        "-c:v", "h264_nvenc", "-preset", preset, "-rc", "constqp", "-qp", crf,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart",
        output_mp4,
    ], capture_output=True, timeout=120)

    if os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
        dur = get_duration(output_mp4)
        print(f"  Output: {output_mp4} ({dur:.2f}s, {os.path.getsize(output_mp4):,} bytes)")
        return True
    print(f"  ERROR: encoding failed")
    return False


if __name__ == "__main__":
    print("=== RENDER VO VISUALS ===\n")

    with open(os.path.join(BASE, "cuts_v3.json")) as f:
        cuts = json.load(f)

    with open(os.path.join(BASE, "edl_v2.json")) as f:
        edl = json.load(f)

    preview = "--preview" in sys.argv

    # VO intro: after hook
    hook_cut = next((c for c in cuts if c["clip_id"] == "hook"), None)
    vo_intro_wav = os.path.join(VO_DIR, "vo_intro.wav")
    if hook_cut and os.path.exists(vo_intro_wav):
        hook_src = os.path.join(SOURCES, f"{hook_cut['video_id']}.mp4")
        out = os.path.join(QA, "vo_intro_visual.mp4")
        print("Rendering VO intro visual...")
        render_vo_segment(vo_intro_wav, hook_src, hook_cut["cut_out"], out,
                          preview=preview)

    # VO bridge: after clip_03
    bridge_after = None
    for b in edl.get("vo", {}).get("bridges", []):
        bridge_after = b.get("after_clip")

    if bridge_after:
        bridge_cut = next((c for c in cuts if c["clip_id"] == f"clip_{bridge_after:02d}"), None)
        vo_bridge_wav = os.path.join(VO_DIR, "vo_bridge_01.wav")
        if bridge_cut and os.path.exists(vo_bridge_wav):
            bridge_src = os.path.join(SOURCES, f"{bridge_cut['video_id']}.mp4")
            out = os.path.join(QA, "vo_bridge_visual.mp4")
            print("\nRendering VO bridge visual...")
            render_vo_segment(vo_bridge_wav, bridge_src, bridge_cut["cut_out"], out,
                              preview=preview)

    print("\nDone.")
