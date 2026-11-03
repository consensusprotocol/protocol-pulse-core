#!/usr/bin/env python3
"""Stage 3c: Build contact sheet and low-res preview.
Contact sheet: start+end frame from every clip + hook, labelled.
Preview: 640x360, straight cuts, 20ms audio fades at seams."""
import json
import os
import subprocess
import sys

BASE = "/home/ultron/protocol_pulse/segment_v1"
EDL_FILE = os.path.join(BASE, "edl.json")
CUTS_FILE = os.path.join(BASE, "cuts.json")
SOURCES_DIR = os.path.join(BASE, "sources")
QA_DIR = os.path.join(BASE, "qa")
OUT_DIR = os.path.join(BASE, "out")
os.makedirs(QA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

with open(EDL_FILE) as f:
    edl = json.load(f)

# Load cuts if available
cuts = {}
if os.path.exists(CUTS_FILE):
    with open(CUTS_FILE) as f:
        cuts = json.load(f)


def extract_frame(source_mp4, time_s, output_png, label=""):
    """Extract a single frame at time_s, scale to 480x270, burn label."""
    vf = f"scale=480:270"
    if label:
        safe = label.replace("'", "\\'").replace(":", "\\:")
        vf += f",drawtext=text='{safe}':fontsize=14:fontcolor=white:borderw=1:x=5:y=5"
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(time_s), "-i", source_mp4,
        "-vframes", "1", "-vf", vf, output_png,
    ], capture_output=True, timeout=30)


def build_contact_sheet():
    """Build contact_sheet_v1.png with start+end frames from all clips."""
    from PIL import Image, ImageDraw, ImageFont

    frames = []  # (label, png_path)

    # Hook
    hook = edl.get("hook")
    if hook and hook.get("video_id"):
        vid = hook["video_id"]
        src = os.path.join(SOURCES_DIR, f"{vid}.mp4")
        if os.path.exists(src):
            t = hook.get("word_start", 0)
            p = os.path.join(QA_DIR, "cs_hook_start.png")
            label = f"HOOK {hook['channel']} {t:.1f}s \"{hook['first_word']}\""
            extract_frame(src, t, p, label)
            frames.append(("HOOK START", p))

            t2 = hook.get("word_end", t + 5)
            p2 = os.path.join(QA_DIR, "cs_hook_end.png")
            label2 = f"HOOK END {t2:.1f}s \"{hook['last_word']}\""
            extract_frame(src, t2, p2, label2)
            frames.append(("HOOK END", p2))

    # Each clip
    for clip in edl.get("clips", []):
        vid = clip["video_id"]
        src = os.path.join(SOURCES_DIR, f"{vid}.mp4")
        if not os.path.exists(src):
            continue
        idx = clip["index"]

        t_start = clip.get("word_start", 0)
        p_start = os.path.join(QA_DIR, f"cs_clip{idx:02d}_start.png")
        label_s = f"#{idx} {clip['channel']} {t_start:.1f}s \"{clip['first_word']}\""
        extract_frame(src, t_start, p_start, label_s)
        frames.append((f"CLIP {idx} START", p_start))

        t_end = clip.get("word_end", t_start + 10)
        p_end = os.path.join(QA_DIR, f"cs_clip{idx:02d}_end.png")
        label_e = f"#{idx} END {t_end:.1f}s \"{clip['last_word']}\""
        extract_frame(src, t_end, p_end, label_e)
        frames.append((f"CLIP {idx} END", p_end))

    # Compose into a grid
    if not frames:
        print("ERROR: No frames extracted")
        return

    # Load all frames
    imgs = []
    for label, path in frames:
        if os.path.exists(path):
            imgs.append((label, Image.open(path)))
        else:
            print(f"  WARNING: missing frame {path}")

    if not imgs:
        print("ERROR: No frames loaded")
        return

    # Grid: 4 columns
    cols = 4
    rows = (len(imgs) + cols - 1) // cols
    thumb_w, thumb_h = 480, 270
    pad = 10
    header = 20

    sheet_w = cols * (thumb_w + pad) + pad
    sheet_h = rows * (thumb_h + header + pad) + pad

    sheet = Image.new("RGB", (sheet_w, sheet_h), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font = ImageFont.load_default()

    for i, (label, img) in enumerate(imgs):
        col = i % cols
        row = i // cols
        x = pad + col * (thumb_w + pad)
        y = pad + row * (thumb_h + header + pad)
        draw.text((x, y), label, fill=(255, 255, 255), font=font)
        img_resized = img.resize((thumb_w, thumb_h), Image.LANCZOS)
        sheet.paste(img_resized, (x, y + header))

    out_path = os.path.join(BASE, "contact_sheet_v1.png")
    sheet.save(out_path)
    print(f"Contact sheet: {out_path} ({sheet_w}x{sheet_h}, {len(imgs)} frames)")
    return out_path


def build_preview():
    """Build 640x360 preview with straight cuts and 20ms audio fades."""
    # First extract each clip segment from source
    clip_files = []

    # Hook
    hook = edl.get("hook")
    if hook and hook.get("video_id"):
        vid = hook["video_id"]
        src = os.path.join(SOURCES_DIR, f"{vid}.mp4")
        cut_key = f"hook_{vid}"
        # Use cuts.json if available, else use word timestamps with handles
        start = hook.get("word_start", 0) - 0.5
        end = hook.get("word_end", start + 5) + 0.7
        if start < 0:
            start = 0
        out_clip = os.path.join(QA_DIR, "preview_hook.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", src,
            "-vf", "scale=640:360", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-af", "afade=t=in:d=0.02,afade=t=out:st=" + str(end - start - 0.02) + ":d=0.02",
            "-c:a", "aac", "-b:a", "96k", "-ar", "48000",
            out_clip,
        ], capture_output=True, timeout=60)
        if os.path.exists(out_clip) and os.path.getsize(out_clip) > 1000:
            clip_files.append(out_clip)

    # VO intro placeholder (silence for now — actual VO WAV placed later)
    # Skip in preview for now

    # Each clip
    for clip in edl.get("clips", []):
        vid = clip["video_id"]
        src = os.path.join(SOURCES_DIR, f"{vid}.mp4")
        idx = clip["index"]
        start = clip.get("word_start", 0) - 0.5
        end = clip.get("word_end", start + 10) + 0.7
        if start < 0:
            start = 0
        dur = end - start
        out_clip = os.path.join(QA_DIR, f"preview_clip{idx:02d}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", src,
            "-vf", "scale=640:360", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-af", f"afade=t=in:d=0.02,afade=t=out:st={max(dur-0.02, 0):.3f}:d=0.02",
            "-c:a", "aac", "-b:a", "96k", "-ar", "48000",
            out_clip,
        ], capture_output=True, timeout=60)
        if os.path.exists(out_clip) and os.path.getsize(out_clip) > 1000:
            clip_files.append(out_clip)

    if not clip_files:
        print("ERROR: No preview clips extracted")
        return

    # Concat with ffmpeg
    filelist = os.path.join(QA_DIR, "preview_filelist.txt")
    with open(filelist, "w") as f:
        for cf in clip_files:
            f.write(f"file '{cf}'\n")

    preview_path = os.path.join(BASE, "preview_v1.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
        "-vf", "setpts=PTS-STARTPTS",
        "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000",
        "-movflags", "+faststart",
        preview_path,
    ], capture_output=True, timeout=120)

    if os.path.exists(preview_path):
        dur = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", preview_path],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        print(f"Preview: {preview_path} ({dur}s)")
    else:
        print("ERROR: Preview generation failed")

    return preview_path


if __name__ == "__main__":
    print("=== STAGE 3c: CONTACT SHEET AND PREVIEW ===")
    cs = build_contact_sheet()
    print()
    pv = build_preview()

    # Write status
    status = {
        "status": "PREVIEW_READY",
        "contact_sheet": cs,
        "preview": pv,
    }
    with open(os.path.join(BASE, "status.json"), "w") as f:
        json.dump(status, f, indent=2)
    print(f"\nSTATUS=PREVIEW_READY written to status.json")
    print(f"Contact sheet: {cs}")
    print(f"Preview: {pv}")
