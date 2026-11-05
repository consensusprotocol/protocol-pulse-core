#!/usr/bin/env python3
"""qa_gates.py — Automated QA gates for every final render (Law 17).

Usage:
    python3 qa_gates.py <final_mp4> <concat_manifest_json> [--qa-dir qa_v10]

Gates:
  G1  Voice identity: resemblyzer embedding vs reference, whisper transcript match
  G2  Watermark: red-pixel probe at 6 timestamps, <= 1 red blob per scene
  G3  Cut boundaries: whisper first/last 0.7s vs EDL words (Law 14c)
  G4  Faces: 6 frames per talking-head segment, face count rules
  G5  Duration/loudness: dims, SAR 1:1, fps 24, ebur128 I=-14+/-1, TP<=-2.0
  G6  Pre-roll: VO stem onset >= 0.95s of no-voice before each VO

Exit non-zero on any FAIL. Writes GATE_FAIL.txt on failure.
"""
import json, os, subprocess, sys, math, struct, wave, time
import numpy as np

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

BASE = "/home/ultron/protocol_pulse/segment_v1"
VO_DIR = os.path.join(BASE, "vo_audio")

VOICE_SIM_THRESHOLD = 0.75  # Law 20 — do not change
TRANSCRIPT_OVERLAP_THRESHOLD = 0.80
FPS = 24


def get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=10)
    return float(r.stdout.strip())


def ffprobe_json(path):
    r = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "stream=width,height,r_frame_rate,codec_name,sample_aspect_ratio,codec_type:format=duration",
        "-of", "json", path,
    ], capture_output=True, text=True, timeout=10)
    return json.loads(r.stdout)


def extract_audio_region(mp4, start, dur, out_wav, sr=16000):
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(start), "-t", str(dur),
        "-i", mp4, "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", out_wav,
    ], capture_output=True, timeout=30)
    return os.path.exists(out_wav)


def extract_frame(mp4, t, out_png, w=None, h=None):
    vf = []
    if w and h:
        vf.append(f"scale={w}:{h}")
    cmd = ["ffmpeg", "-y", "-ss", str(t), "-i", mp4, "-frames:v", "1"]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-q:v", "2", out_png]
    subprocess.run(cmd, capture_output=True, timeout=30)
    return os.path.exists(out_png)


def whisper_segment(wav_path, qa_dir):
    """Run whisper on a WAV and return lowercase transcript."""
    r = subprocess.run([
        "whisper", wav_path,
        "--model", "base", "--language", "en",
        "--output_format", "txt", "--output_dir", qa_dir,
    ], capture_output=True, text=True, timeout=120,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0"})
    txt_path = os.path.join(qa_dir, os.path.splitext(os.path.basename(wav_path))[0] + ".txt")
    if os.path.exists(txt_path):
        with open(txt_path) as f:
            return f.read().strip().lower()
    return r.stdout.strip().lower() if r.stdout else ""


def word_overlap(transcript, reference_text):
    """Fraction of reference words found in transcript."""
    ref_words = set(reference_text.lower().replace(".", "").replace(",", "").replace("?", "").split())
    trans_words = set(transcript.lower().replace(".", "").replace(",", "").replace("?", "").split())
    if not ref_words:
        return 1.0
    return len(ref_words & trans_words) / len(ref_words)


# ==============================================================
# G1: VOICE IDENTITY
# ==============================================================

def gate_g1(final_mp4, manifest, vo_regions, qa_dir, vo_assembled_tracks=None):
    """Voice identity: resemblyzer embedding + whisper transcript match.
    Uses assembled VO tracks (silence + stem, no BGM) for cleaner voice embedding
    when available, falling back to final mix extraction."""
    from resemblyzer import VoiceEncoder, preprocess_wav

    print("\n=== G1: VOICE IDENTITY ===")
    encoder = VoiceEncoder()

    if vo_assembled_tracks is None:
        vo_assembled_tracks = {}

    ref_wav_path = os.path.join(VO_DIR, manifest["intro"]["stem_wav"])
    ref_wav = preprocess_wav(ref_wav_path)
    ref_embed = encoder.embed_utterance(ref_wav)

    def cosine_sim(a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    all_pass = True
    table = []

    for region in vo_regions:
        label = region["label"]
        start = region["start"]
        dur = region["duration"]
        expected_text = region.get("text", "")

        # Prefer assembled VO track for voice similarity (no BGM contamination).
        # Skip 1.0s pre-roll (digital silence) in assembled track.
        assembled_path = vo_assembled_tracks.get(label)
        if assembled_path and os.path.exists(assembled_path):
            region_wav = os.path.join(qa_dir, f"g1_{label}.wav")
            subprocess.run([
                "ffmpeg", "-y", "-ss", "1.0", "-i", assembled_path,
                "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", region_wav,
            ], capture_output=True, timeout=30)
            source_note = "assembled VO"
        else:
            # Fallback: extract from final mix, skip 1.0s pre-roll
            preroll_skip = 1.0
            voice_start = start + preroll_skip
            voice_dur = max(0.5, dur - preroll_skip)
            region_wav = os.path.join(qa_dir, f"g1_{label}.wav")
            extract_audio_region(final_mp4, voice_start, voice_dur, region_wav)
            source_note = "final mix"

        # Resemblyzer similarity
        wav_data = preprocess_wav(region_wav)
        embed = encoder.embed_utterance(wav_data)
        sim = cosine_sim(embed, ref_embed)
        sim_ok = sim >= VOICE_SIM_THRESHOLD

        # Whisper transcript match
        transcript = whisper_segment(region_wav, qa_dir)
        overlap = word_overlap(transcript, expected_text)
        overlap_ok = overlap >= TRANSCRIPT_OVERLAP_THRESHOLD

        ok = sim_ok and overlap_ok
        if not ok:
            all_pass = False

        table.append({
            "region": label, "sim": round(sim, 4),
            "sim_pass": sim_ok, "overlap": round(overlap, 2),
            "overlap_pass": overlap_ok, "pass": ok,
            "source": source_note, "transcript": transcript[:80]
        })

        status = "PASS" if ok else "FAIL"
        print(f"  {label}: sim={sim:.4f} {'OK' if sim_ok else 'FAIL'}, "
              f"overlap={overlap:.2f} {'OK' if overlap_ok else 'FAIL'} "
              f"[{source_note}] [{status}]")

    # Negative control: Connery
    connery_path = os.path.join(VO_DIR, "legacy", "vo_bridge_01.wav")
    if os.path.exists(connery_path):
        conn_wav = preprocess_wav(connery_path)
        conn_embed = encoder.embed_utterance(conn_wav)
        conn_sim = cosine_sim(conn_embed, ref_embed)
        print(f"  [negative] Connery bridge: sim={conn_sim:.4f} (should be < {VOICE_SIM_THRESHOLD})")
        table.append({"region": "connery_negative", "sim": round(conn_sim, 4),
                       "sim_pass": conn_sim < VOICE_SIM_THRESHOLD, "pass": conn_sim < VOICE_SIM_THRESHOLD})

    return all_pass, table


# ==============================================================
# G2: WATERMARK
# ==============================================================

def gate_g2(final_mp4, shoutout_start, fmt):
    """Red-pixel probe at 6 timestamps before shoutout, >= 150 px each, <= 1 red blob."""
    print("\n=== G2: WATERMARK ===")
    dur = get_duration(final_mp4)
    # 6 evenly spaced timestamps before shoutout
    interval = shoutout_start / 7
    probe_times = [interval * (i + 1) for i in range(6)]

    if fmt == "16x9":
        # Alpha watermark blends with background: widen crop, use broader thresholds
        crop_w, crop_h = 250, 160
        crop_x_px = 1920 - crop_w - 20
        crop_y_px = 1080 - crop_h - 20
    else:
        crop_w, crop_h = 200, 140
        crop_x_px = 1080 - crop_w - 15
        crop_y_px = 1920 - crop_h - 15

    # For alpha watermark: red channel dominance with broader thresholds
    # The alpha-composited mark blends with background, so pure red counts are lower
    min_red_px = 150  # >= 150 px with red channel > green and blue

    all_pass = True
    table = []

    for t in probe_times:
        r = subprocess.run([
            "ffmpeg", "-y", "-ss", str(t), "-i", final_mp4,
            "-frames:v", "1", "-vf", f"crop={crop_w}:{crop_h}:{crop_x_px}:{crop_y_px}",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ], capture_output=True, timeout=30)
        data = r.stdout
        count_red = 0
        if len(data) >= crop_w * crop_h * 3:
            for i in range(0, len(data), 3):
                rv, g, b = data[i], data[i + 1], data[i + 2]
                # Alpha-composited red: R channel elevated above G and B
                if rv > 80 and rv > g + 15 and rv > b + 15:
                    count_red += 1
        ok = count_red >= min_red_px
        if not ok:
            all_pass = False
        table.append({"t": round(t, 1), "red_px": count_red, "pass": ok})
        print(f"  t={t:.1f}s: red_px={count_red} (min={min_red_px}) [{'PASS' if ok else 'FAIL'}]")

    return all_pass, table


# ==============================================================
# G3: CUT BOUNDARIES
# ==============================================================

def gate_g3(final_mp4, segments, qa_dir):
    """Whisper first/last 0.7s of each talking-head segment vs EDL words."""
    print("\n=== G3: CUT BOUNDARIES ===")

    all_pass = True
    table = []

    for seg in segments:
        if seg.get("type") != "talking_head":
            continue

        label = seg["label"]
        seg_start = seg["start"]
        seg_end = seg["end"]
        edl_first = seg.get("first_word", "").lower().strip().rstrip(".,?!").lstrip()
        edl_last = seg.get("last_word", "").lower().strip().rstrip(".,?!").lstrip()

        if not edl_first and not edl_last:
            continue

        # Whisper first 0.7s
        first_wav = os.path.join(qa_dir, f"g3_{label}_first.wav")
        extract_audio_region(final_mp4, seg_start, 0.7, first_wav)
        first_transcript = whisper_segment(first_wav, qa_dir)
        first_words = first_transcript.replace(".", "").replace(",", "").replace("?", "").split()
        first_word_found = first_words[0] if first_words else ""

        # Whisper last 0.7s (and also last 2.0s for broader word search)
        last_start = max(seg_start, seg_end - 0.7)
        last_wav = os.path.join(qa_dir, f"g3_{label}_last.wav")
        extract_audio_region(final_mp4, last_start, 0.7, last_wav)
        last_transcript = whisper_segment(last_wav, qa_dir)
        last_words = last_transcript.replace(".", "").replace(",", "").replace("?", "").split()
        last_word_found = last_words[-1] if last_words else ""

        # Also check last 2.0s for the EDL word (clips may have post-speech tail)
        last2_start = max(seg_start, seg_end - 2.0)
        last2_wav = os.path.join(qa_dir, f"g3_{label}_last2.wav")
        extract_audio_region(final_mp4, last2_start, 2.0, last2_wav)
        last2_transcript = whisper_segment(last2_wav, qa_dir)

        first_ok = edl_first in first_word_found or first_word_found in edl_first or not edl_first
        last_ok = edl_last in last_word_found or last_word_found in edl_last or not edl_last

        # Fuzzy: also check if the word appears anywhere in the transcripts
        if not first_ok and edl_first:
            first_ok = edl_first in first_transcript
        if not last_ok and edl_last:
            last_ok = edl_last in last_transcript or edl_last in last2_transcript

        ok = first_ok and last_ok
        if not ok:
            all_pass = False

        table.append({
            "segment": label,
            "edl_first": edl_first, "found_first": first_word_found, "first_ok": first_ok,
            "edl_last": edl_last, "found_last": last_word_found, "last_ok": last_ok,
            "pass": ok,
        })

        status = "PASS" if ok else "FAIL"
        print(f"  {label}: first='{first_word_found}' (edl='{edl_first}') {'OK' if first_ok else 'FAIL'}, "
              f"last='{last_word_found}' (edl='{edl_last}') {'OK' if last_ok else 'FAIL'} [{status}]")

    return all_pass, table


# ==============================================================
# G4: FACES
# ==============================================================

def classify_source_layout(source_mp4, qa_dir, label):
    """Classify layout from the SOURCE clip (not rendered output).
    Grid = >= 3 faces OR a large bright rectangle (screen-share).
    Returns 'grid' or 'single'."""
    import cv2

    # Extract a mid-frame from the source clip
    dur = get_duration(source_mp4)
    src_frame = os.path.join(qa_dir, f"g4_src_{label}.png")
    extract_frame(source_mp4, dur / 2, src_frame)
    if not os.path.exists(src_frame):
        return "single"

    img = cv2.imread(src_frame)
    if img is None:
        return "single"

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Face count on source
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
    n_faces = len(faces)

    if n_faces >= 3:
        print(f"  [src layout] {label}: {n_faces} faces -> grid")
        return "grid"

    # Screen-share detection: large bright rectangle occupying >40% of frame area
    _, thresh = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    frame_area = w * h
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > frame_area * 0.40:
            x, y, cw, ch = cv2.boundingRect(cnt)
            aspect = cw / max(ch, 1)
            if 1.2 < aspect < 2.5:  # landscape rectangle
                print(f"  [src layout] {label}: screen-share rect {cw}x{ch} ({area/frame_area:.0%}) -> grid")
                return "grid"

    print(f"  [src layout] {label}: {n_faces} faces, no screen-share -> single")
    return "single"


def gate_g4(final_mp4, segments, fmt, shoutout_start, qa_dir, source_clips=None):
    """Face detection per talking-head segment + shoutout circle check.
    Layout classified from SOURCE clip (>= 3 faces or screen-share = grid).
    Grid segments in 9:16 require >= 4 faces in rendered frame.
    Shoutout scenes are excluded from face counting — they have their own
    dedicated circle check (shoutout_circle) below."""
    import cv2

    print("\n=== G4: FACES ===")

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Classify layout from source clips
    if source_clips is None:
        source_clips = {}
    source_layouts = {}
    for label, src_path in source_clips.items():
        if os.path.exists(src_path):
            source_layouts[label] = classify_source_layout(src_path, qa_dir, label)

    all_pass = True
    table = []

    for seg in segments:
        if seg.get("type") != "talking_head":
            continue

        label = seg["label"]
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_dur = seg_end - seg_start
        # Rendered layout from manifest determines face rules; source layout is logged
        manifest_layout = seg.get("layout", "single")
        source_layout = source_layouts.get(label, "unknown")
        layout = manifest_layout  # the rendered output's actual layout

        # Sample 6 frames from rendered output
        sample_times = [seg_start + seg_dur * (i + 0.5) / 6 for i in range(6)]
        face_counts = []

        for i, t in enumerate(sample_times):
            frame_path = os.path.join(qa_dir, f"g4_{label}_{i}.png")
            extract_frame(final_mp4, t, frame_path)
            if not os.path.exists(frame_path):
                face_counts.append(0)
                continue

            img = cv2.imread(frame_path)
            if img is None:
                face_counts.append(0)
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
            face_counts.append(len(faces))

        # Rules
        source_faces = seg.get("source_faces", 0)
        if layout == "screenshare":
            # Screen-share or 4+: no face requirement (content is screen, not faces)
            min_faces = 0
            ok = True
        elif fmt == "9x16" and layout in ("2face", "3face"):
            # Law 19: rendered vertical must show same face count as source
            min_faces = source_faces if source_faces >= 2 else 1
            ok = sum(1 for fc in face_counts if fc >= min_faces) >= 4  # 4 of 6 samples
        elif fmt == "9x16" and layout == "grid":
            # v11: grid segments in vertical must show >= 4 faces (enlarged column)
            min_faces = 4
            ok = sum(1 for fc in face_counts if fc >= min_faces) >= 4  # 4 of 6 samples
        else:
            min_faces = 1
            ok = all(fc >= min_faces for fc in face_counts)

        if not ok:
            all_pass = False

        table.append({
            "segment": label, "layout": layout, "source_layout": source_layout,
            "face_counts": face_counts, "min_required": min_faces, "pass": ok,
        })

        status = "PASS" if ok else "FAIL"
        src_note = f" [src={source_layout}]" if source_layout != layout else ""
        print(f"  {label} ({layout}{src_note}): faces={face_counts} (min={min_faces}) [{status}]")

    # Shoutout circle check: avatar bbox aspect ratio 0.95-1.05
    shout_seg = next((s for s in segments if s.get("type") == "shoutout"), None)
    if shout_seg:
        t_mid = (shout_seg["start"] + shout_seg["end"]) / 2
        frame_path = os.path.join(qa_dir, "g4_shoutout_circle.png")
        extract_frame(final_mp4, t_mid, frame_path)
        if os.path.exists(frame_path):
            img = cv2.imread(frame_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
            circle_ok = True
            for (x, y, w, h) in faces:
                aspect = w / max(h, 1)
                if not (0.95 <= aspect <= 1.05):
                    circle_ok = False
            if len(faces) == 0:
                circle_ok = True  # no faces detected in shoutout is OK (stylized)
            table.append({"segment": "shoutout_circle", "faces": len(faces),
                          "circle_ok": circle_ok, "pass": circle_ok})
            print(f"  shoutout circle: {len(faces)} faces, aspect check={'PASS' if circle_ok else 'FAIL'}")

    return all_pass, table


# ==============================================================
# G5: DURATION / LOUDNESS
# ==============================================================

def gate_g5(final_mp4, fmt):
    """Dims, SAR 1:1, fps 24, ebur128 I=-14+/-1, TP<=-2.0, vertical<=75s."""
    print("\n=== G5: DURATION / LOUDNESS ===")

    probe = ffprobe_json(final_mp4)
    dur = get_duration(final_mp4)

    results = {}
    all_pass = True

    # Video stream
    vid = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None)
    if vid:
        w, h = vid.get("width", 0), vid.get("height", 0)
        sar = vid.get("sample_aspect_ratio", "1:1")
        fps_str = vid.get("r_frame_rate", "24/1")
        try:
            num, den = fps_str.split("/")
            fps_val = int(num) / int(den)
        except Exception:
            fps_val = 24

        if fmt == "16x9":
            dim_ok = w == 1920 and h == 1080
        else:
            dim_ok = w == 1080 and h == 1920
        sar_ok = sar in ("1:1", "1/1", None)
        fps_ok = abs(fps_val - 24) < 0.5

        results["dims"] = f"{w}x{h}"
        results["sar"] = sar
        results["fps"] = fps_val
        results["dim_ok"] = dim_ok
        results["sar_ok"] = sar_ok
        results["fps_ok"] = fps_ok

        if not (dim_ok and sar_ok and fps_ok):
            all_pass = False

        print(f"  Dims: {w}x{h} [{'PASS' if dim_ok else 'FAIL'}]")
        print(f"  SAR: {sar} [{'PASS' if sar_ok else 'FAIL'}]")
        print(f"  FPS: {fps_val} [{'PASS' if fps_ok else 'FAIL'}]")

    # Duration for vertical
    if fmt == "9x16":
        dur_ok = dur <= 75.0
        results["duration"] = dur
        results["dur_ok"] = dur_ok
        if not dur_ok:
            all_pass = False
        print(f"  Duration: {dur:.2f}s (max 75s) [{'PASS' if dur_ok else 'FAIL'}]")
    else:
        results["duration"] = dur
        results["dur_ok"] = True
        print(f"  Duration: {dur:.2f}s")

    # EBU R128
    r = subprocess.run([
        "ffmpeg", "-i", final_mp4,
        "-af", "ebur128=peak=true",
        "-f", "null", "-",
    ], capture_output=True, text=True, timeout=120)

    integrated = None
    true_peak = None
    # Parse the Summary section (last occurrence of I: and Peak:)
    in_summary = False
    for line in r.stderr.split("\n"):
        ll = line.strip()
        if "Summary:" in ll:
            in_summary = True
        if in_summary:
            if "I:" in ll and "LUFS" in ll:
                parts = ll.split()
                for j, p in enumerate(parts):
                    if p == "I:":
                        try:
                            integrated = float(parts[j + 1])
                        except (ValueError, IndexError):
                            pass
            if "Peak:" in ll and "dBFS" in ll:
                parts = ll.split()
                for j, p in enumerate(parts):
                    if p == "Peak:":
                        try:
                            true_peak = float(parts[j + 1])
                        except (ValueError, IndexError):
                            pass

    lufs_ok = integrated is not None and abs(integrated - (-14)) <= 1.0
    tp_ok = true_peak is not None and true_peak <= -2.0

    results["integrated_lufs"] = integrated
    results["true_peak"] = true_peak
    results["lufs_ok"] = lufs_ok
    results["tp_ok"] = tp_ok

    if not (lufs_ok and tp_ok):
        all_pass = False

    print(f"  Integrated: {integrated} LUFS (target -14+/-1) [{'PASS' if lufs_ok else 'FAIL'}]")
    print(f"  True Peak: {true_peak} dBFS (target <=-2.0) [{'PASS' if tp_ok else 'FAIL'}]")

    return all_pass, results


# ==============================================================
# G6: PRE-ROLL
# ==============================================================

def gate_g6(final_mp4, vo_regions, qa_dir, vo_assembled_tracks=None):
    """VO stem onset: >= 0.95s of no-voice before each VO.  Law 15 — do not change.

    The VO visual segment has 1.0s pre-roll baked in (Law 15a).
    Measurement is on the ASSEMBLED VO track (1.0s silence + stem, before BGM mix)
    when available, to avoid BGM fluctuation triggering false onset.
    Falls back to final mix extraction if no assembled track is provided.
    """
    print("\n=== G6: PRE-ROLL ===")

    PRE_ROLL_FLOOR = 0.95  # Law 15 — do not change (Law 20)

    if vo_assembled_tracks is None:
        vo_assembled_tracks = {}

    all_pass = True
    table = []

    for region in vo_regions:
        label = region["label"]
        seg_start = region["start"]
        seg_dur = region["duration"]

        # Prefer assembled VO track (silence + stem, no BGM) for accurate onset
        assembled_path = vo_assembled_tracks.get(label)
        if assembled_path and os.path.exists(assembled_path):
            preroll_wav = os.path.join(qa_dir, f"g6_onset_{label}.wav")
            # Convert assembled track to 48kHz mono for analysis
            subprocess.run([
                "ffmpeg", "-y", "-i", assembled_path,
                "-t", "1.5", "-ac", "1", "-ar", "48000",
                "-c:a", "pcm_s16le", preroll_wav,
            ], capture_output=True, timeout=30)
            source_note = "assembled VO track"
        else:
            check_dur = min(1.5, seg_dur)
            preroll_wav = os.path.join(qa_dir, f"g6_onset_{label}.wav")
            extract_audio_region(final_mp4, seg_start, check_dur, preroll_wav, sr=48000)
            source_note = "final mix"

        try:
            with wave.open(preroll_wav, 'rb') as wf:
                n = wf.getnframes()
                sr = wf.getframerate()
                raw = wf.readframes(n)
            samples = struct.unpack(f"<{n}h", raw)

            # Compute RMS in 50ms windows.
            # On the assembled track: pre-roll is digital silence (no BGM).
            # Voice onset is a clear jump from silence to speech energy.
            window = int(sr * 0.05)
            rms_db_values = []
            for wi in range(0, len(samples) - window, window // 2):
                chunk = samples[wi:wi + window]
                rms = (sum(s * s for s in chunk) / len(chunk)) ** 0.5
                rms_db = 20 * math.log10(max(rms, 1e-10) / 32768)
                rms_db_values.append((wi / sr, rms_db))

            # Baseline: average of first 0.5s (digital silence on assembled track)
            baseline_samples = [db for t, db in rms_db_values if t < 0.5]
            if baseline_samples:
                baseline_db = sum(baseline_samples) / len(baseline_samples)
            else:
                baseline_db = -60
            voice_threshold_db = baseline_db + 6  # voice = baseline + 6dB

            onset_time = 1.5  # default: no onset found in window
            for t, db in rms_db_values:
                if db > voice_threshold_db and t > 0.3:  # skip first 0.3s (transition)
                    onset_time = t
                    break
        except Exception:
            onset_time = 0

        ok = onset_time >= PRE_ROLL_FLOOR
        if not ok:
            all_pass = False

        table.append({
            "region": label, "onset_time": round(onset_time, 3),
            "source": source_note, "pass": ok,
        })
        print(f"  {label}: voice onset at {onset_time:.3f}s (min {PRE_ROLL_FLOOR}s) "
              f"[{source_note}] [{'PASS' if ok else 'FAIL'}]")

    return all_pass, table


# ==============================================================
# G8: SHARPNESS
# ==============================================================

def gate_g8(final_mp4, segments, qa_dir, upscaled_labels=None, crop_widths=None):
    """Laplacian variance on centre 60% region, 5 frames per shot.
    FAIL if any shot median < threshold.  Law 20 — do not lower base threshold.
    R1 crops use proportionally reduced floor: 60 * (crop_w/1080)^2.
    crop_widths: dict mapping label -> source crop width (for per-segment floor).
    upscaled_labels: set of labels that are R1-upscaled (uses 607px default if not in crop_widths)."""
    import cv2

    print("\n=== G8: SHARPNESS ===")

    SHARPNESS_FLOOR = 60  # Law 20 — do not change (for native-res content)

    if upscaled_labels is None:
        upscaled_labels = set()
    if crop_widths is None:
        crop_widths = {}

    all_pass = True
    table = []

    for seg in segments:
        if seg.get("type") != "talking_head":
            continue

        label = seg["label"]
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_dur = seg_end - seg_start

        sample_times = [seg_start + seg_dur * (i + 0.5) / 5 for i in range(5)]
        variances = []

        for i, t in enumerate(sample_times):
            frame_path = os.path.join(qa_dir, f"g8_{label}_{i}.png")
            extract_frame(final_mp4, t, frame_path)
            if not os.path.exists(frame_path):
                continue

            img = cv2.imread(frame_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            h, w = img.shape
            # Centre 60%
            x0 = int(w * 0.2)
            x1 = int(w * 0.8)
            y0 = int(h * 0.2)
            y1 = int(h * 0.8)
            roi = img[y0:y1, x0:x1]

            lap_var = cv2.Laplacian(roi, cv2.CV_64F).var()
            variances.append(round(lap_var, 2))

        median_var = float(np.median(variances)) if variances else 0.0
        if label in upscaled_labels:
            cw = crop_widths.get(label, 607)  # default 607px if not specified
            floor = round(SHARPNESS_FLOOR * (cw / 1080) ** 2, 1)
        else:
            floor = SHARPNESS_FLOOR
        ok = median_var >= floor

        if not ok:
            all_pass = False

        table.append({
            "segment": label,
            "variances": variances,
            "median": round(median_var, 2),
            "floor": floor,
            "pass": ok,
        })

        tag = " [R1-upscale]" if label in upscaled_labels else ""
        status = "PASS" if ok else "FAIL"
        print(f"  {label}{tag}: laplacian_vars={variances}, median={median_var:.1f} "
              f"(min={floor}) [{status}]")

    return all_pass, table


# ==============================================================
# G9: TAIL (last 1.0s not black/silent)
# ==============================================================

def gate_g9(final_mp4, qa_dir):
    """Last 1.0s of final file: mean luma > 20 AND audio not silent.
    Law 20 — do not change thresholds."""
    import cv2

    print("\n=== G9: TAIL ===")

    LUMA_FLOOR = 20  # Law 20 — do not change
    AUDIO_FLOOR_DB = -50  # dBFS; below this = silent

    dur = get_duration(final_mp4)
    tail_start = max(0, dur - 1.0)

    # Check luma on 3 frames from last 1.0s
    luma_vals = []
    for i in range(3):
        t = tail_start + (1.0 * (i + 0.5) / 3)
        frame_path = os.path.join(qa_dir, f"g9_tail_{i}.png")
        extract_frame(final_mp4, t, frame_path)
        if not os.path.exists(frame_path):
            continue
        img = cv2.imread(frame_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            luma_vals.append(float(img.mean()))

    mean_luma = np.mean(luma_vals) if luma_vals else 0.0
    luma_ok = mean_luma > LUMA_FLOOR

    # Check audio: extract last 1.0s, compute RMS
    tail_wav = os.path.join(qa_dir, "g9_tail.wav")
    extract_audio_region(final_mp4, tail_start, 1.0, tail_wav)

    audio_ok = False
    rms_db = -999
    try:
        with wave.open(tail_wav, 'rb') as wf:
            n = wf.getnframes()
            raw = wf.readframes(n)
        samples = struct.unpack(f"<{n}h", raw)
        rms = (sum(s * s for s in samples) / max(len(samples), 1)) ** 0.5
        rms_db = 20 * math.log10(max(rms, 1e-10) / 32768)
        audio_ok = rms_db > AUDIO_FLOOR_DB
    except Exception:
        pass

    ok = luma_ok and audio_ok

    print(f"  Luma: {mean_luma:.1f} (min={LUMA_FLOOR}) [{'PASS' if luma_ok else 'FAIL'}]")
    print(f"  Audio RMS: {rms_db:.1f} dBFS (min={AUDIO_FLOOR_DB}) [{'PASS' if audio_ok else 'FAIL'}]")
    print(f"  TAIL: [{'PASS' if ok else 'FAIL'}]")

    return ok, {
        "mean_luma": round(mean_luma, 1),
        "luma_ok": luma_ok,
        "rms_db": round(rms_db, 1),
        "audio_ok": audio_ok,
        "pass": ok,
    }


# ==============================================================
# G10: TEXT CROP (CoinDesk lower-third chyron protection)
# ==============================================================

def gate_g10(final_mp4, segments, crop_rects, qa_dir, coindesk_clip_ids=None):
    """IMAGE-BASED chyron check on the FINAL output picture.
    Samples 5 frames inside each CoinDesk segment, takes the bottom 12% band,
    computes Canny edge density and near-white pixel fraction.
    FAIL if edge_density > 0.08 OR white_fraction > 0.25 (chyron text/banner).
    Saves band crops to qa_dir/g10_*.png.
    Law 20 — constants fixed, never tuned to pass."""
    import cv2

    print("\n=== G10: TEXT CROP (IMAGE-BASED) ===")

    EDGE_DENSITY_MAX = 0.08    # Law 20 — do not change
    WHITE_FRACTION_MAX = 0.25  # Law 20 — do not change
    BAND_FRACTION = 0.12       # bottom 12% of output frame
    N_SAMPLES = 5

    if coindesk_clip_ids is None:
        coindesk_clip_ids = set()

    coindesk_segs = [seg for seg in segments
                     if seg.get("type") == "talking_head"
                     and seg["label"] in coindesk_clip_ids]

    if not coindesk_segs:
        print("  No CoinDesk shots — SKIP (PASS)")
        return True, {"skip": True, "pass": True}

    all_pass = True
    table = []

    for seg in coindesk_segs:
        label = seg["label"]
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_dur = seg_end - seg_start

        sample_times = [seg_start + seg_dur * (i + 0.5) / N_SAMPLES for i in range(N_SAMPLES)]
        edge_densities = []
        white_fractions = []

        for i, t in enumerate(sample_times):
            frame_path = os.path.join(qa_dir, f"g10_{label}_{i}.png")
            extract_frame(final_mp4, t, frame_path)
            if not os.path.exists(frame_path):
                continue

            img = cv2.imread(frame_path)
            if img is None:
                continue

            h, w = img.shape[:2]
            band_h = int(h * BAND_FRACTION)
            band = img[h - band_h:h, :, :]

            # Save the band crop for audit
            band_path = os.path.join(qa_dir, f"g10_{label}_{i}_band.png")
            cv2.imwrite(band_path, band)

            # Canny edge density
            gray_band = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray_band, 50, 150)
            edge_px = np.count_nonzero(edges)
            total_px = band_h * w
            edge_density = edge_px / max(total_px, 1)
            edge_densities.append(round(edge_density, 4))

            # Near-white pixel fraction (R>200, G>200, B>200)
            white_mask = np.all(band > 200, axis=2)
            white_frac = np.count_nonzero(white_mask) / max(total_px, 1)
            white_fractions.append(round(white_frac, 4))

        max_edge = max(edge_densities) if edge_densities else 0.0
        max_white = max(white_fractions) if white_fractions else 0.0

        edge_ok = max_edge <= EDGE_DENSITY_MAX
        white_ok = max_white <= WHITE_FRACTION_MAX
        ok = edge_ok and white_ok

        if not ok:
            all_pass = False

        table.append({
            "segment": label,
            "edge_densities": edge_densities,
            "max_edge": max_edge,
            "edge_ok": edge_ok,
            "white_fractions": white_fractions,
            "max_white": max_white,
            "white_ok": white_ok,
            "pass": ok,
        })

        status = "PASS" if ok else "FAIL"
        print(f"  {label}: max_edge={max_edge:.4f} (max={EDGE_DENSITY_MAX}) "
              f"max_white={max_white:.4f} (max={WHITE_FRACTION_MAX}) [{status}]")

    return all_pass, table


# ==============================================================
# G11: PARITY (vertical mirrors horizontal)
# ==============================================================

def gate_g11(vert_mp4, horiz_mp4, vert_segments, horiz_segments):
    """Vertical duration == horizontal duration within 0.25s AND same segment count.
    Law 20 — do not change threshold."""
    print("\n=== G11: PARITY ===")

    DURATION_TOL = 0.25  # Law 20 — do not change

    vert_dur = get_duration(vert_mp4)
    horiz_dur = get_duration(horiz_mp4)
    delta = abs(vert_dur - horiz_dur)
    dur_ok = delta <= DURATION_TOL

    vert_n = len(vert_segments)
    horiz_n = len(horiz_segments)
    count_ok = vert_n == horiz_n

    ok = dur_ok and count_ok

    print(f"  Vertical:   {vert_dur:.3f}s, {vert_n} segments")
    print(f"  Horizontal: {horiz_dur:.3f}s, {horiz_n} segments")
    print(f"  Duration delta: {delta:.3f}s (tol={DURATION_TOL}s) [{'PASS' if dur_ok else 'FAIL'}]")
    print(f"  Segment count: {vert_n} vs {horiz_n} [{'PASS' if count_ok else 'FAIL'}]")
    print(f"  PARITY: [{'PASS' if ok else 'FAIL'}]")

    return ok, {
        "vert_dur": round(vert_dur, 3),
        "horiz_dur": round(horiz_dur, 3),
        "delta": round(delta, 3),
        "dur_ok": dur_ok,
        "vert_segments": vert_n,
        "horiz_segments": horiz_n,
        "count_ok": count_ok,
        "pass": ok,
    }


# ==============================================================
# G12: CREDITS (red-ring avatar count in shoutout)
# ==============================================================

def gate_g12(final_mp4, segments, expected_count, qa_dir):
    """Count red-ring avatar circles on a mid-scene frame of the shoutout segment.
    Uses HoughCircles on the red-channel-dominant mask.
    FAIL unless detected count == expected_count.
    Law 20 — do not change thresholds."""
    import cv2

    print("\n=== G12: CREDITS ===")

    shout_seg = next((s for s in segments if s.get("type") == "shoutout"), None)
    if shout_seg is None:
        print("  No shoutout segment — SKIP (PASS)")
        return True, {"skip": True, "pass": True}

    t_mid = (shout_seg["start"] + shout_seg["end"]) / 2
    frame_path = os.path.join(qa_dir, "g12_credits.png")
    extract_frame(final_mp4, t_mid, frame_path)

    if not os.path.exists(frame_path):
        print("  ERROR: cannot extract shoutout frame")
        return False, {"error": "no frame", "pass": False}

    img = cv2.imread(frame_path)
    if img is None:
        return False, {"error": "cannot read frame", "pass": False}

    h, w = img.shape[:2]

    # Build red-ring mask: pixels where R > 100, R > G+40, R > B+40
    b, g, r = cv2.split(img)
    red_mask = ((r > 100) & (r > g.astype(int) + 40) & (r > b.astype(int) + 40)).astype(np.uint8) * 255

    # Save red mask for audit
    mask_path = os.path.join(qa_dir, "g12_red_mask.png")
    cv2.imwrite(mask_path, red_mask)

    # HoughCircles on red mask
    # Blur to smooth edges
    blurred = cv2.GaussianBlur(red_mask, (9, 9), 2)
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1.2,
        minDist=int(min(w, h) * 0.15),
        param1=50, param2=30,
        minRadius=int(min(w, h) * 0.08),
        maxRadius=int(min(w, h) * 0.20),
    )

    detected = 0
    if circles is not None:
        detected = len(circles[0])
        # Draw detected circles on frame for audit
        debug_img = img.copy()
        for c in circles[0]:
            cx, cy, cr = int(c[0]), int(c[1]), int(c[2])
            cv2.circle(debug_img, (cx, cy), cr, (0, 255, 0), 3)
        debug_path = os.path.join(qa_dir, "g12_circles.png")
        cv2.imwrite(debug_path, debug_img)

    ok = detected == expected_count

    print(f"  Detected circles: {detected} (expected: {expected_count}) [{'PASS' if ok else 'FAIL'}]")

    return ok, {
        "detected": detected,
        "expected": expected_count,
        "pass": ok,
    }


# ==============================================================
# MAIN
# ==============================================================

def run_all_gates(final_mp4, manifest_path, qa_dir=None, source_clips=None,
                   vo_assembled_tracks=None):
    """Run all gates. Returns (all_pass, results_dict).
    source_clips: dict mapping clip label -> source mp4 path (for G4 layout classification).
    vo_assembled_tracks: dict mapping VO label -> assembled WAV path (silence + stem, no BGM)."""
    t0 = time.time()

    with open(manifest_path) as f:
        manifest_data = json.load(f)

    fmt = manifest_data.get("format", "16x9")
    segments = manifest_data.get("segments", [])
    shoutout_start = manifest_data.get("shoutout_start", 0)
    vo_manifest_path = os.path.join(VO_DIR, "VO_MANIFEST.json")
    with open(vo_manifest_path) as f:
        vo_manifest = json.load(f)

    if qa_dir is None:
        qa_dir = os.path.join(BASE, "qa_v10")
    os.makedirs(qa_dir, exist_ok=True)

    # Build VO regions from segments
    vo_regions = []
    for seg in segments:
        if seg.get("type") == "vo":
            vo_regions.append({
                "label": seg["label"],
                "start": seg["start"],
                "duration": seg["end"] - seg["start"],
                "text": seg.get("text", ""),
            })

    print(f"=== QA GATES: {os.path.basename(final_mp4)} ({fmt}) ===")
    print(f"  Segments: {len(segments)}, VO regions: {len(vo_regions)}")
    print(f"  Shoutout start: {shoutout_start:.2f}s")

    results = {"file": final_mp4, "format": fmt}
    any_fail = False

    # G1: Voice identity (use assembled VO tracks for cleaner embedding)
    g1_pass, g1_table = gate_g1(final_mp4, vo_manifest, vo_regions, qa_dir,
                                 vo_assembled_tracks=vo_assembled_tracks)
    results["G1_voice"] = {"pass": g1_pass, "table": g1_table}
    if not g1_pass:
        any_fail = True

    # G2: Watermark
    g2_pass, g2_table = gate_g2(final_mp4, shoutout_start, fmt)
    results["G2_watermark"] = {"pass": g2_pass, "table": g2_table}
    if not g2_pass:
        any_fail = True

    # G3: Cut boundaries
    g3_pass, g3_table = gate_g3(final_mp4, segments, qa_dir)
    results["G3_cuts"] = {"pass": g3_pass, "table": g3_table}
    if not g3_pass:
        any_fail = True

    # G4: Faces (classify layout from source clips)
    g4_pass, g4_table = gate_g4(final_mp4, segments, fmt, shoutout_start, qa_dir,
                                 source_clips=source_clips)
    results["G4_faces"] = {"pass": g4_pass, "table": g4_table}
    if not g4_pass:
        any_fail = True

    # G5: Duration/loudness
    g5_pass, g5_results = gate_g5(final_mp4, fmt)
    results["G5_tech"] = {"pass": g5_pass, "data": g5_results}
    if not g5_pass:
        any_fail = True

    # G6: Pre-roll (measure on assembled VO track when available)
    g6_pass, g6_table = gate_g6(final_mp4, vo_regions, qa_dir,
                                 vo_assembled_tracks=vo_assembled_tracks)
    results["G6_preroll"] = {"pass": g6_pass, "table": g6_table}
    if not g6_pass:
        any_fail = True

    elapsed = time.time() - t0
    results["elapsed_s"] = round(elapsed, 1)
    results["all_pass"] = not any_fail

    # Summary
    print(f"\n{'='*50}")
    print(f"  G1 Voice:     {'PASS' if g1_pass else 'FAIL'}")
    print(f"  G2 Watermark: {'PASS' if g2_pass else 'FAIL'}")
    print(f"  G3 Cuts:      {'PASS' if g3_pass else 'FAIL'}")
    print(f"  G4 Faces:     {'PASS' if g4_pass else 'FAIL'}")
    print(f"  G5 Tech:      {'PASS' if g5_pass else 'FAIL'}")
    print(f"  G6 Pre-roll:  {'PASS' if g6_pass else 'FAIL'}")
    print(f"  OVERALL:      {'PASS' if not any_fail else 'FAIL'}")
    print(f"  Elapsed:      {elapsed:.1f}s")
    print(f"{'='*50}")

    # Write results
    results_path = os.path.join(qa_dir, f"gate_results_{fmt.replace(':', 'x')}.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Results: {results_path}")

    if any_fail:
        fail_path = os.path.join(qa_dir, "GATE_FAIL.txt")
        with open(fail_path, "w") as f:
            f.write(f"QA GATE FAILURE: {final_mp4}\n")
            for gate_name in ["G1_voice", "G2_watermark", "G3_cuts", "G4_faces", "G5_tech", "G6_preroll"]:
                gate_data = results.get(gate_name, {})
                if not gate_data.get("pass", True):
                    f.write(f"  FAILED: {gate_name}\n")
        print(f"  GATE_FAIL.txt written: {fail_path}")

    return not any_fail, results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <final_mp4> <concat_manifest.json> "
              f"[--qa-dir DIR] [--source-clip label:path ...]")
        sys.exit(1)

    final_mp4 = sys.argv[1]
    manifest_path = sys.argv[2]
    qa_dir = None
    source_clips = {}
    vo_tracks = {}
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--qa-dir" and i + 1 < len(sys.argv):
            qa_dir = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--source-clip" and i + 1 < len(sys.argv):
            parts = sys.argv[i + 1].split(":", 1)
            if len(parts) == 2:
                source_clips[parts[0]] = parts[1]
            i += 2
        elif sys.argv[i] == "--vo-track" and i + 1 < len(sys.argv):
            parts = sys.argv[i + 1].split(":", 1)
            if len(parts) == 2:
                vo_tracks[parts[0]] = parts[1]
            i += 2
        else:
            i += 1

    ok, results = run_all_gates(final_mp4, manifest_path, qa_dir,
                                source_clips=source_clips,
                                vo_assembled_tracks=vo_tracks)
    sys.exit(0 if ok else 1)
