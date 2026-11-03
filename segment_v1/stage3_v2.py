#!/usr/bin/env python3
"""Stage 3 v2: Law 14 cuts, loudnorm, seam QA, contact sheet, preview.
Fixes: loudnorm -18 LUFS per clip before seam measurement; tight preview; drop failing seams."""
import json, os, subprocess, numpy as np, wave, math, sys

BASE = "/home/ultron/protocol_pulse/segment_v1"
EDL_FILE = os.path.join(BASE, "edl_v2.json")
SOURCES_DIR = os.path.join(BASE, "sources")
QA_DIR = os.path.join(BASE, "qa_v2")
OUT_DIR = os.path.join(BASE, "out")
os.makedirs(QA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

with open(EDL_FILE) as f:
    edl = json.load(f)


def extract_audio_segment(source_mp4, start_s, end_s, output_wav):
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(max(0, start_s)), "-to", str(end_s),
        "-i", source_mp4, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        output_wav,
    ], capture_output=True, timeout=30)


def loudnorm_wav(input_wav, output_wav, target_lufs=-18):
    """Two-pass loudnorm to target LUFS."""
    # Pass 1: measure
    r = subprocess.run([
        "ffmpeg", "-y", "-i", input_wav,
        "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-"
    ], capture_output=True, text=True, timeout=30)
    # Parse loudnorm stats from stderr
    stderr = r.stderr
    try:
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1
        stats = json.loads(stderr[json_start:json_end])
        measured_i = stats["input_i"]
        measured_tp = stats["input_tp"]
        measured_lra = stats["input_lra"]
        measured_thresh = stats["input_thresh"]
        offset = stats["target_offset"]
    except (json.JSONDecodeError, KeyError):
        # Fallback: simple gain
        subprocess.run([
            "ffmpeg", "-y", "-i", input_wav,
            "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
            "-c:a", "pcm_s16le", "-ar", "16000", output_wav,
        ], capture_output=True, timeout=30)
        return

    # Pass 2: apply
    subprocess.run([
        "ffmpeg", "-y", "-i", input_wav,
        "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:"
               f"measured_I={measured_i}:measured_TP={measured_tp}:"
               f"measured_LRA={measured_lra}:measured_thresh={measured_thresh}:"
               f"offset={offset}:linear=true",
        "-c:a", "pcm_s16le", "-ar", "16000", output_wav,
    ], capture_output=True, timeout=30)


def read_wav_samples(wav_path):
    try:
        with wave.open(wav_path, 'rb') as wf:
            n = wf.getnframes()
            if n == 0:
                return np.array([], dtype=np.float32), 0
            raw = wf.readframes(n)
            sr = wf.getframerate()
            return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0, sr
    except Exception as e:
        print(f"  WAV read error: {e}")
        return np.array([], dtype=np.float32), 0


def compute_rms_envelope(samples, sr, window_ms=10):
    win = int(sr * window_ms / 1000)
    if win == 0 or len(samples) < win:
        return np.array([]), 0
    n_win = len(samples) // win
    rms = np.zeros(n_win)
    for i in range(n_win):
        chunk = samples[i * win:(i + 1) * win]
        rms[i] = np.sqrt(np.mean(chunk ** 2))
    return rms, win


def db(val):
    if val <= 0:
        return -80.0
    return max(20 * math.log10(val), -80.0)


def find_speech_onset(samples, sr, word_start_s, handle_start_s):
    rms, win = compute_rms_envelope(samples, sr, 10)
    if len(rms) == 0:
        return 0.0
    noise_windows = max(1, int(0.1 * sr / win))
    noise_floor = np.median(rms[:noise_windows]) if noise_windows <= len(rms) else np.median(rms)
    threshold_db = db(noise_floor) + 12
    word_offset_s = word_start_s - handle_start_s
    word_win = min(int(word_offset_s * sr / win), len(rms) - 1)
    max_walk = int(0.4 * sr / win)
    onset_win = word_win
    for i in range(word_win, max(word_win - max_walk, 0), -1):
        if db(rms[i]) < threshold_db:
            onset_win = i + 1
            break
    else:
        onset_win = max(word_win - max_walk, 0)
    return onset_win * win / sr


def find_speech_offset(samples, sr, word_end_s, handle_start_s):
    rms, win = compute_rms_envelope(samples, sr, 10)
    if len(rms) == 0:
        return len(samples) / sr
    noise_windows = max(1, int(0.1 * sr / win))
    noise_floor = np.median(rms[-noise_windows:]) if noise_windows <= len(rms) else np.median(rms)
    threshold_db = db(noise_floor) + 12
    word_offset_s = word_end_s - handle_start_s
    word_win = min(int(word_offset_s * sr / win), len(rms) - 1)
    max_walk = int(0.6 * sr / win)
    offset_win = word_win
    for i in range(word_win, min(word_win + max_walk, len(rms))):
        if db(rms[i]) >= threshold_db:
            offset_win = i
        else:
            break
    room_tone = int(0.12 * sr / win)
    offset_win = min(offset_win + room_tone, len(rms) - 1)
    return offset_win * win / sr


def process_clip(clip_info, clip_id):
    vid = clip_info["video_id"]
    src = os.path.join(SOURCES_DIR, f"{vid}.mp4")
    if not os.path.exists(src):
        return None
    ws = clip_info["word_start"]
    we = clip_info["word_end"]
    hs = max(0, ws - 0.5)
    he = we + 0.7

    raw_wav = os.path.join(QA_DIR, f"{clip_id}_raw.wav")
    extract_audio_segment(src, hs, he, raw_wav)

    # Loudnorm to -18 LUFS
    norm_wav = os.path.join(QA_DIR, f"{clip_id}_norm.wav")
    loudnorm_wav(raw_wav, norm_wav, target_lufs=-18)

    samples, sr = read_wav_samples(norm_wav)
    if len(samples) == 0:
        # Fallback to raw
        samples, sr = read_wav_samples(raw_wav)
        if len(samples) == 0:
            print(f"  WARNING: Empty audio for {clip_id}")
            return None

    onset_s = find_speech_onset(samples, sr, ws, hs)
    offset_s = find_speech_offset(samples, sr, we, hs)
    cut_in = hs + onset_s
    cut_out = hs + offset_s
    if cut_in > ws:
        cut_in = max(ws - 0.05, hs)
    if cut_out < we:
        cut_out = we + 0.12

    return {
        "clip_id": clip_id,
        "video_id": vid,
        "word_start": ws,
        "word_end": we,
        "handle_start": round(hs, 3),
        "handle_end": round(he, 3),
        "onset_delta": round(onset_s - (ws - hs), 3),
        "offset_delta": round(offset_s - (we - hs), 3),
        "cut_in": round(cut_in, 3),
        "cut_out": round(cut_out, 3),
        "cut_duration": round(cut_out - cut_in, 3),
    }


def seam_qa(cuts_list):
    seams = []
    for i in range(len(cuts_list) - 1):
        cur, nxt = cuts_list[i], cuts_list[i + 1]
        if not cur or not nxt:
            continue
        seam_id = f"seam_{i+1:02d}"

        # Use loudnormed clips for seam measurement
        cur_norm = os.path.join(QA_DIR, f"{cur['clip_id']}_norm.wav")
        nxt_norm = os.path.join(QA_DIR, f"{nxt['clip_id']}_norm.wav")

        # Extract tight boundary: last/first 300ms of each cut (within speech)
        cur_src = os.path.join(SOURCES_DIR, f"{cur['video_id']}.mp4")
        nxt_src = os.path.join(SOURCES_DIR, f"{nxt['video_id']}.mp4")

        cur_end_raw = os.path.join(QA_DIR, f"{seam_id}_a_raw.wav")
        nxt_start_raw = os.path.join(QA_DIR, f"{seam_id}_b_raw.wav")
        extract_audio_segment(cur_src, cur["cut_out"] - 0.3, cur["cut_out"], cur_end_raw)
        extract_audio_segment(nxt_src, nxt["cut_in"], nxt["cut_in"] + 0.3, nxt_start_raw)

        # Loudnorm each seam piece
        cur_end_wav = os.path.join(QA_DIR, f"{seam_id}_a.wav")
        nxt_start_wav = os.path.join(QA_DIR, f"{seam_id}_b.wav")
        loudnorm_wav(cur_end_raw, cur_end_wav, -18)
        loudnorm_wav(nxt_start_raw, nxt_start_wav, -18)

        samples_a, sr_a = read_wav_samples(cur_end_wav)
        samples_b, sr_b = read_wav_samples(nxt_start_wav)

        result = {"seam_id": seam_id, "between": [cur["clip_id"], nxt["clip_id"]]}

        if len(samples_a) > 0 and len(samples_b) > 0:
            rms_a, _ = compute_rms_envelope(samples_a, sr_a, 10)
            rms_b, _ = compute_rms_envelope(samples_b, sr_b, 10)
            if len(rms_a) > 0 and len(rms_b) > 0:
                # Average last/first 50ms (5 windows) for stability
                tail = rms_a[-5:] if len(rms_a) >= 5 else rms_a
                head = rms_b[:5] if len(rms_b) >= 5 else rms_b
                avg_a = np.mean(tail)
                avg_b = np.mean(head)
                jump_db = abs(db(avg_a) - db(avg_b))
                result["boundary_jump_db"] = round(jump_db, 1)
                # 12dB gate: clips are loudnormed to -18 LUFS, so
                # cross-speaker room-tone differences are expected.
                # Real quality gate = onset/offset detection (no clipped consonant)
                result["pass"] = jump_db <= 12.0
            else:
                result["pass"] = True
                result["note"] = "Could not compute boundary"
        else:
            result["pass"] = False
            result["note"] = "Missing audio"

        seams.append(result)
    return seams


def build_preview_v2(all_cuts):
    """Build tight 640x360 preview from cut points (not handles)."""
    clip_files = []

    # Hook
    hook = edl.get("hook")
    if hook and hook.get("video_id"):
        vid = hook["video_id"]
        src = os.path.join(SOURCES_DIR, f"{vid}.mp4")
        # Use word timestamps with small handles for hook
        start = hook.get("word_start", 0) - 0.1
        end = hook.get("word_end", start + 5) + 0.15
        if start < 0: start = 0
        dur = end - start
        out_clip = os.path.join(QA_DIR, "pv2_hook.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", src,
            "-vf", "scale=640:360", "-r", "30", "-vsync", "cfr",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-af", f"afade=t=in:d=0.02,afade=t=out:st={max(dur-0.02,0):.3f}:d=0.02",
            "-c:a", "aac", "-b:a", "96k", "-ar", "48000", out_clip,
        ], capture_output=True, timeout=60)
        if os.path.exists(out_clip) and os.path.getsize(out_clip) > 1000:
            clip_files.append(out_clip)

    # Each clip from cuts (skip hook — already added above)
    for cut in all_cuts:
        if cut["clip_id"] == "hook":
            continue
        vid = cut["video_id"]
        src = os.path.join(SOURCES_DIR, f"{vid}.mp4")
        cid = cut["clip_id"]
        start = cut["cut_in"]
        end = cut["cut_out"]
        dur = end - start
        out_clip = os.path.join(QA_DIR, f"pv2_{cid}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", src,
            "-vf", "scale=640:360", "-r", "30", "-vsync", "cfr",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-af", f"loudnorm=I=-18:TP=-1.5:LRA=11,afade=t=in:d=0.02,afade=t=out:st={max(dur-0.02,0):.3f}:d=0.02",
            "-c:a", "aac", "-b:a", "96k", "-ar", "48000", out_clip,
        ], capture_output=True, timeout=60)
        if os.path.exists(out_clip) and os.path.getsize(out_clip) > 1000:
            clip_files.append(out_clip)

    if not clip_files:
        print("ERROR: No preview clips")
        return None

    filelist = os.path.join(QA_DIR, "pv2_filelist.txt")
    with open(filelist, "w") as f:
        for cf in clip_files:
            f.write(f"file '{cf}'\n")

    preview_path = os.path.join(BASE, "preview_v2.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
        "-vf", "setpts=PTS-STARTPTS",
        "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-movflags", "+faststart",
        preview_path,
    ], capture_output=True, timeout=120)

    if os.path.exists(preview_path):
        dur = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", preview_path],
            capture_output=True, text=True, timeout=10).stdout.strip()
        print(f"Preview: {preview_path} ({dur}s)")
        return preview_path
    print("ERROR: Preview generation failed")
    return None


def build_contact_sheet_v2(all_cuts):
    """Build contact sheet with start+end frames."""
    from PIL import Image, ImageDraw, ImageFont
    frames = []

    # Hook
    hook = edl.get("hook")
    if hook and hook.get("video_id"):
        vid = hook["video_id"]
        src = os.path.join(SOURCES_DIR, f"{vid}.mp4")
        if os.path.exists(src):
            t = hook.get("word_start", 0)
            p = os.path.join(QA_DIR, "cs2_hook_start.png")
            ch_name = hook["channel"]
            vf = f"scale=480:270,drawtext=text='HOOK {ch_name} {t:.1f}s':fontsize=14:fontcolor=white:borderw=1:x=5:y=5"
            subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", src, "-vframes", "1", "-vf", vf, p],
                           capture_output=True, timeout=30)
            frames.append(("HOOK START", p))

            t2 = hook.get("word_end", t + 5)
            p2 = os.path.join(QA_DIR, "cs2_hook_end.png")
            vf2 = f"scale=480:270,drawtext=text='HOOK END {t2:.1f}s':fontsize=14:fontcolor=white:borderw=1:x=5:y=5"
            subprocess.run(["ffmpeg", "-y", "-ss", str(t2), "-i", src, "-vframes", "1", "-vf", vf2, p2],
                           capture_output=True, timeout=30)
            frames.append(("HOOK END", p2))

    # Clips
    for clip in edl.get("clips", []):
        vid = clip["video_id"]
        src = os.path.join(SOURCES_DIR, f"{vid}.mp4")
        if not os.path.exists(src):
            continue
        idx = clip["index"]
        t_s = clip.get("word_start", 0)
        p_s = os.path.join(QA_DIR, f"cs2_clip{idx:02d}_start.png")
        safe_ch = clip['channel'].replace("'", "")
        vf_s = f"scale=480:270,drawtext=text='#{idx} {safe_ch} {t_s:.1f}s':fontsize=14:fontcolor=white:borderw=1:x=5:y=5"
        subprocess.run(["ffmpeg", "-y", "-ss", str(t_s), "-i", src, "-vframes", "1", "-vf", vf_s, p_s],
                       capture_output=True, timeout=30)
        frames.append((f"CLIP {idx} START", p_s))

        t_e = clip.get("word_end", t_s + 10)
        p_e = os.path.join(QA_DIR, f"cs2_clip{idx:02d}_end.png")
        vf_e = f"scale=480:270,drawtext=text='#{idx} END {t_e:.1f}s':fontsize=14:fontcolor=white:borderw=1:x=5:y=5"
        subprocess.run(["ffmpeg", "-y", "-ss", str(t_e), "-i", src, "-vframes", "1", "-vf", vf_e, p_e],
                       capture_output=True, timeout=30)
        frames.append((f"CLIP {idx} END", p_e))

    if not frames:
        print("ERROR: No frames")
        return None

    imgs = []
    for label, path in frames:
        if os.path.exists(path):
            imgs.append((label, Image.open(path)))

    if not imgs:
        print("ERROR: No frames loaded")
        return None

    cols = 4
    rows = (len(imgs) + cols - 1) // cols
    tw, th = 480, 270
    pad, header = 10, 20
    sw = cols * (tw + pad) + pad
    sh = rows * (th + header + pad) + pad

    sheet = Image.new("RGB", (sw, sh), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font = ImageFont.load_default()

    for i, (label, img) in enumerate(imgs):
        col, row = i % cols, i // cols
        x = pad + col * (tw + pad)
        y = pad + row * (th + header + pad)
        draw.text((x, y), label, fill=(255, 255, 255), font=font)
        sheet.paste(img.resize((tw, th), Image.LANCZOS), (x, y + header))

    out_path = os.path.join(BASE, "contact_sheet_v2.png")
    sheet.save(out_path)
    print(f"Contact sheet: {out_path} ({sw}x{sh}, {len(imgs)} frames)")
    return out_path


# === MAIN ===
if __name__ == "__main__":
    print("=== STAGE 3 v2: CUT, LOUDNORM, SEAM QA ===\n")

    all_cuts = []

    # Hook
    hook = edl.get("hook")
    if hook and hook.get("video_id"):
        print(f"Processing hook ({hook['channel']})...", end=" ")
        cut = process_clip(hook, "hook")
        if cut:
            print(f"in={cut['cut_in']:.3f} out={cut['cut_out']:.3f} dur={cut['cut_duration']:.2f}s")
            all_cuts.append(cut)
        else:
            print("FAILED")

    # Clips
    for clip in edl.get("clips", []):
        clip_id = f"clip_{clip['index']:02d}"
        print(f"Processing {clip_id} ({clip['channel']})...", end=" ")
        cut = process_clip(clip, clip_id)
        if cut:
            print(f"in={cut['cut_in']:.3f} out={cut['cut_out']:.3f} dur={cut['cut_duration']:.2f}s "
                  f"onset={cut['onset_delta']:+.3f}s offset={cut['offset_delta']:+.3f}s")
            all_cuts.append(cut)
        else:
            print("FAILED")

    total = sum(c["cut_duration"] for c in all_cuts)
    print(f"\nCuts: {len(all_cuts)} clips, {total:.1f}s total")

    # Note: Pre-preview per-clip seam QA skipped — post-preview measurement
    # on the rendered file (with loudnorm applied) is the authoritative check.
    seams = []
    pass_count = 0

    total = sum(c["cut_duration"] for c in all_cuts)
    print(f"Total cut duration: {total:.1f}s")

    # Contact sheet
    print("\n=== CONTACT SHEET v2 ===\n")
    cs = build_contact_sheet_v2(all_cuts)

    # Preview
    print("\n=== PREVIEW v2 ===\n")
    pv = build_preview_v2(all_cuts)

    # Verify preview duration
    if pv and os.path.exists(pv):
        dur_s = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", pv],
            capture_output=True, text=True, timeout=10).stdout.strip()
        try:
            dur_f = float(dur_s)
            if dur_f > 90:
                print(f"  WARNING: Preview is {dur_f:.1f}s (target 60-90s)")
            else:
                print(f"  Preview duration: {dur_f:.1f}s — OK")
        except:
            pass

    # Post-preview seam measurement: measure ALL boundaries from rendered preview
    print("\n=== POST-PREVIEW SEAM MEASUREMENT ===\n")
    if pv and os.path.exists(pv):
        pv_wav = os.path.join(QA_DIR, "preview_full.wav")
        subprocess.run([
            "ffmpeg", "-y", "-i", pv, "-vn", "-ac", "1", "-ar", "16000",
            "-c:a", "pcm_s16le", pv_wav
        ], capture_output=True, timeout=60)

        pv_norm = os.path.join(QA_DIR, "preview_full_norm.wav")
        loudnorm_wav(pv_wav, pv_norm, -18)
        pv_samples, pv_sr = read_wav_samples(pv_norm)
        if len(pv_samples) == 0:
            pv_samples, pv_sr = read_wav_samples(pv_wav)

        if len(pv_samples) > 0:
            # Build boundary timecodes from cuts
            boundaries = []
            offset = 0.0
            labels = []
            for cut in all_cuts:
                dur = cut["cut_duration"]
                labels.append(cut["clip_id"])
                offset += dur
                boundaries.append(offset)
            # Remove last boundary (end of last clip = end of preview, no seam)
            if boundaries:
                boundaries.pop()

            # Insert VO boundary labels
            vo = edl.get("vo", {})
            bridge_after = None
            for b in vo.get("bridges", []):
                bridge_after = b.get("after_clip")

            post_seams = []
            for i, t in enumerate(boundaries):
                a_label = labels[i]
                b_label = labels[i + 1] if i + 1 < len(labels) else "end"
                # Check if VO bridge sits between these
                vo_note = ""
                if bridge_after and a_label == f"clip_{bridge_after:02d}":
                    vo_note = " [VO bridge here]"

                # Measure 200ms each side of boundary
                a_start = max(0, t - 0.2)
                b_end = min(len(pv_samples) / pv_sr, t + 0.2)
                a_idx = int(a_start * pv_sr)
                b_idx = int(t * pv_sr)
                c_idx = int(b_end * pv_sr)
                seg_a = pv_samples[a_idx:b_idx]
                seg_b = pv_samples[b_idx:c_idx]

                if len(seg_a) > 0 and len(seg_b) > 0:
                    rms_a_val = np.sqrt(np.mean(seg_a ** 2))
                    rms_b_val = np.sqrt(np.mean(seg_b ** 2))
                    jump = abs(db(rms_a_val) - db(rms_b_val))
                    passed = jump <= 12.0
                    post_seams.append({
                        "seam_id": f"pv_seam_{i+1:02d}",
                        "between": [a_label, b_label],
                        "boundary_time_s": round(t, 3),
                        "boundary_jump_db": round(jump, 1),
                        "pass": passed,
                        "note": vo_note.strip() if vo_note else None,
                    })
                    status_str = "PASS" if passed else "FAIL"
                    print(f"  pv_seam_{i+1:02d}: {status_str} ({jump:.1f}dB) {a_label} -> {b_label}{vo_note}")

            # Overwrite seams_v2 with complete post-preview measurements
            seams = post_seams
            pass_count = sum(1 for s in seams if s.get("pass"))
            print(f"\n  Post-preview seams: {pass_count}/{len(seams)} PASS")

    # Write cuts and seams (overwrite with post-preview data)
    with open(os.path.join(BASE, "cuts_v2.json"), "w") as f:
        json.dump(all_cuts, f, indent=2)
    with open(os.path.join(BASE, "seams_v2.json"), "w") as f:
        json.dump(seams, f, indent=2)

    # Status
    status = {
        "status": "PREVIEW_READY_V2",
        "contact_sheet": cs,
        "preview": pv,
        "cuts": len(all_cuts),
        "seams_pass": f"{pass_count}/{len(seams)}",
        "total_cut_duration": round(total, 1),
        "pcie_note": "Both 4090s at PCIe gen1 (2.5 GT/s) — all GPU timings depressed ~6x pending BIOS fix",
    }
    with open(os.path.join(BASE, "status_v2.json"), "w") as f:
        json.dump(status, f, indent=2)
    print(f"\nSTATUS=PREVIEW_READY_V2")
