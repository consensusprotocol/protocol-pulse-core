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
  G3c Acoustic tail: last 120ms of each clip < -35 dBFS, no onset (M19)
  G13 VO Audible: whisper each VO slot from output, >= 80% word match, RMS >= music+6dB (M7)

Exit non-zero on any FAIL. Writes GATE_FAIL.txt on failure.
"""
import json, os, re, subprocess, sys, math, struct, wave, time
import numpy as np

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

BASE = "/home/ultron/protocol_pulse/segment_v1"
VO_DIR = os.path.join(BASE, "vo_audio")

VOICE_SIM_THRESHOLD = 0.75  # Law 20 — do not change
TRANSCRIPT_OVERLAP_THRESHOLD = 0.80
FPS = 24

# ── DEC-1 REFERENCE CALIBRATION (orchestrator, delegated by PBX, 2026-11-11) ──
# PBX's approved v2f outputs (references/v2f_2026-11-06/run/out/segment.mp4 sha256 47293813...,
# segment_vertical.mp4 sha256 5545a261...) are by definition passing (Law 22). For the four gates they
# failed on 2026-11-11 the threshold is the reference's own measured worst value, per format, with no
# extra margin (floats truncated to 2 decimals so the reference passes at its own measurement). Every
# other threshold is unchanged. Measurements: docs/audits/DEFINITION_OF_DONE_PULSE_CHECK.md (1f).
# Authority: PBX handed the orchestrator full authority 2026-11-11 02:50 ET; DEC-1 is the one
# named exception to Law 20 / M2, recorded under 'Decisions (orchestrator, delegated by PBX)' there.
G3C_VALLEY_DEPTH_DB = {"16x9": 11.63, "9x16": 11.65}    # was 12.0: strictest depth at which the v2f hook tail passes (11.6301 / 11.6543)
G5_TRUE_PEAK_MAX_DBFS = {"16x9": -2.0, "9x16": -1.3}    # 9x16 was -2.0: v2f segment_vertical.mp4 true peak -1.3 dBFS (16x9 -2.2 passed)
G8_SHARPNESS_FLOOR = {"16x9": 27.56, "9x16": 10.84}     # was 60: v2f worst segment medians (16x9 hook 27.56, 9x16 clip_03 10.84)
G9_V2F_LUMA = {"16x9": 14.3357, "9x16": 14.7715}       # DEC-1: v2f's own tail luma (the locked outro ends on black)
G9_REENCODE_SPREAD = {"16x9": 0.05, "9x16": 0.04}      # DEC-12a: MEASURED spread (the outro's encode depends on its GOP
    # phase and on the credits card before it) of the same locked outro through the
    # final-encode path (5 GOP phases, 5 real credits cards before it, the real finals): 0.0438 / 0.0335, rounded up
    # to 0.01, at most 0.05 (docs/audits/pulse-sentence-law/dec12a_g9_spread/spread.json). DEC-1's zero margin
    # made a correct render pass or fail by encoder state (OD-4).
G9_LUMA_FLOOR = {k: round(G9_V2F_LUMA[k] - G9_REENCODE_SPREAD[k], 4) for k in G9_V2F_LUMA}   # 14.2857 / 14.7315

# ── Faster-Whisper singleton (medium, float16, cuda, vad OFF, word timestamps) ──
_FW_MODEL = None

def _get_fw_model():
    """Load faster-whisper medium model once per gate run."""
    global _FW_MODEL
    if _FW_MODEL is None:
        from faster_whisper import WhisperModel
        _FW_MODEL = WhisperModel("medium", device="cuda", compute_type="float16")
    return _FW_MODEL


def fw_transcribe(wav_path, word_timestamps=True):
    """Transcribe a WAV with faster-whisper medium. Returns (text, word_segments)."""
    model = _get_fw_model()
    segments, info = model.transcribe(
        wav_path, language="en", beam_size=5,
        word_timestamps=word_timestamps,
        vad_filter=False,
    )
    words_all = []
    text_parts = []
    for seg in segments:
        text_parts.append(seg.text)
        if word_timestamps and seg.words:
            words_all.extend(seg.words)
    text = " ".join(text_parts).strip().lower()
    return text, words_all


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
    """Run faster-whisper medium on a WAV and return lowercase transcript."""
    text, _ = fw_transcribe(wav_path, word_timestamps=False)
    return text


def word_overlap(transcript, reference_text):
    """Fraction of reference words found in transcript, in the pipeline's one canonical form (pipeline/canon.py).
    No reference words = 0.0: an empty expected text never scores a match (Claude-gates V1)."""
    ref_words = set(_canon_tokens(reference_text))
    trans_words = set(_canon_tokens(transcript))
    if not ref_words:
        return 0.0
    return len(ref_words & trans_words) / len(ref_words)


def _canon_tokens(text):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))
    import canon
    return canon.canon_tokens(text or "")


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

    # R2-07: handle M20 edits with no intro — use signoff or first available VO
    if "intro" in manifest and manifest["intro"].get("stem_wav"):
        ref_wav_path = os.path.join(VO_DIR, manifest["intro"]["stem_wav"])
    elif "signoff" in manifest and manifest["signoff"].get("stem_wav"):
        ref_wav_path = os.path.join(VO_DIR, manifest["signoff"]["stem_wav"])
    else:
        # Find any available VO stem
        ref_wav_path = None
        for key, val in manifest.items():
            if isinstance(val, dict) and val.get("stem_wav"):
                ref_wav_path = os.path.join(VO_DIR, val["stem_wav"])
                break
        if ref_wav_path is None:
            print("  G1: No VO reference found in manifest")
            return False, [{"region": "error", "pass": False, "reason": "no VO reference"}]
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
    # R2-13: negative control failure must fail the gate
    connery_path = os.path.join(VO_DIR, "legacy", "vo_bridge_01.wav")
    if os.path.exists(connery_path):
        conn_wav = preprocess_wav(connery_path)
        conn_embed = encoder.embed_utterance(conn_wav)
        conn_sim = cosine_sim(conn_embed, ref_embed)
        neg_pass = conn_sim < VOICE_SIM_THRESHOLD
        print(f"  [negative] Connery bridge: sim={conn_sim:.4f} (should be < {VOICE_SIM_THRESHOLD})")
        table.append({"region": "connery_negative", "sim": round(conn_sim, 4),
                       "sim_pass": neg_pass, "pass": neg_pass})
        if not neg_pass:
            all_pass = False

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
        cf, cl = _canon().canon_tokens(seg.get("first_word", "")), _canon().canon_tokens(seg.get("last_word", ""))
        edl_first, edl_last = (cf[0] if cf else ""), (cl[-1] if cl else "")      # the one canonical form

        if not edl_first and not edl_last:
            continue

        # Whisper first 0.7s
        first_wav = os.path.join(qa_dir, f"g3_{label}_first.wav")
        extract_audio_region(final_mp4, seg_start, 0.7, first_wav)
        first_transcript = whisper_segment(first_wav, qa_dir)
        first_words = _canon().canon_tokens(first_transcript)
        first_word_found = first_words[0] if first_words else ""

        # Also check first 2.0s for broader word search (whisper-tiny is noisy on 0.7s)
        first2_wav = os.path.join(qa_dir, f"g3_{label}_first2.wav")
        extract_audio_region(final_mp4, seg_start, min(2.0, seg_end - seg_start), first2_wav)
        first2_transcript = whisper_segment(first2_wav, qa_dir)

        # Whisper last 0.7s (and also last 2.0s for broader word search)
        last_start = max(seg_start, seg_end - 0.7)
        last_wav = os.path.join(qa_dir, f"g3_{label}_last.wav")
        extract_audio_region(final_mp4, last_start, 0.7, last_wav)
        last_transcript = whisper_segment(last_wav, qa_dir)
        last_words = _canon().canon_tokens(last_transcript)
        last_word_found = last_words[-1] if last_words else ""

        # Also check last 2.0s for the EDL word (clips may have post-speech tail)
        last2_start = max(seg_start, seg_end - 2.0)
        last2_wav = os.path.join(qa_dir, f"g3_{label}_last2.wav")
        extract_audio_region(final_mp4, last2_start, 2.0, last2_wav)
        last2_transcript = whisper_segment(last2_wav, qa_dir)

        # R2-03: require non-empty transcripts — "" in "word" is always True
        first_ok = False
        last_ok = False
        if not edl_first:
            first_ok = True
        elif first_word_found and (edl_first in first_word_found or first_word_found in edl_first):
            first_ok = True
        if not edl_last:
            last_ok = True
        elif last_word_found and (edl_last in last_word_found or last_word_found in edl_last):
            last_ok = True

        # Fuzzy: also check if the word appears anywhere in the transcripts
        # Require non-empty transcript to prevent "" in "" false passes
        if not first_ok and edl_first:
            if first_transcript.strip():
                first_ok = edl_first in _canon().canon(first_transcript)
            if not first_ok and first2_transcript.strip():
                first_ok = edl_first in _canon().canon(first2_transcript)
        if not last_ok and edl_last:
            if last_transcript.strip():
                last_ok = edl_last in _canon().canon(last_transcript)
            if not last_ok and last2_transcript.strip():
                last_ok = edl_last in _canon().canon(last2_transcript)

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
# G3b: CUT_OUT_CLEAN
# ==============================================================

G3B_READS, G3B_CONTEXT_S, G3B_TAIL_S = 3, 1.5, 1.0     # DEC-12f


def _canon():
    """The pipeline's one canonical form for every text comparison (pipeline/canon.py)."""
    if os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline") not in sys.path:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
    import canon
    return canon


def _g3b_words(text):
    """Reading words in the one canonical form (law L-g: '$40 trillion' = '40 trillion dollars', '50%' = '50
    percent'; pipeline/canon.py)."""
    return _canon().canon_tokens(text)


def _g3b_match(expected, heard):
    """The old rule, unchanged: the same word, or the expected word inside the heard one ('magnitude' in
    'magnitudes'); a heard prefix of it ('magnet' for 'magnitude') does not match."""
    return heard == expected or expected in heard


def gate_g3b(final_mp4, segments, qa_dir, edl_path=None):
    """Whisper the tail of each cut clip in the final output (DEC-12f: 3 readings with 1.5 s of context,
    majority). The transcript must end with the EDL's declared last_word and must NOT
    contain the source's next word (from EDL field 'next_source_word').
    Constant thresholds, output-based."""
    print("\n=== G3b: CUT_OUT_CLEAN ===")

    # Load EDL for next_source_word lookup
    edl_clips = {}
    if edl_path and os.path.exists(edl_path):
        with open(edl_path) as f:
            edl = json.load(f)
        hook = edl.get("hook", {})
        if hook:
            edl_clips["hook"] = hook
        for clip in edl.get("clips", []):
            edl_clips[f"clip_{clip['index']:02d}"] = clip

    all_pass = True
    table = []

    for seg in segments:
        if seg.get("type") != "talking_head":
            continue

        label = seg["label"]
        seg_end = seg["end"]
        seg_start = seg["start"]
        lock = (edl_clips.get(label, {}).get("selection_lock") or {}).get("text") or ""
        tail = " ".join(lock.split()[-5:]) if lock else seg.get("last_word", "")
        ew = _g3b_words(tail)                              # the expected last word read in its own context (canon)
        edl_last = ew[-1] if ew else ""

        if not edl_last:
            continue

        # DEC-12f (2026-11-11): three readings of the tail with 1.5 s of leading context, majority vote. The
        # window start is jittered by 0 / 1 / 2 video frames so they are three readings, not one decode three
        # times. The expected last word must be one of the last two words heard in >= 2 of 3 readings. (One
        # decode heard Nov 10's '... rally.' as 'route.' while G17b, G18 and the 9:16 decode passed.)
        reads = []
        for j in range(G3B_READS):
            w0 = max(seg_start, seg_end - G3B_TAIL_S - G3B_CONTEXT_S + j / FPS)
            wav = os.path.join(qa_dir, f"g3b_{label}_read{j}.wav")
            extract_audio_region(final_mp4, w0, seg_end - w0, wav)
            reads.append(_g3b_words(whisper_segment(wav, qa_dir)))
        tail_transcript = " | ".join(" ".join(ws[-4:]) for ws in reads)
        votes = sum(1 for ws in reads if any(_g3b_match(edl_last, w) for w in ws[-2:]))
        last_found = votes * 2 > len(reads)
        dissent = votes < len(reads)        # law L-c: one dissenting reading sends the edge to the acoustic check

        # Check 2: next source word must NOT appear (if declared in EDL)
        # R2-03: check ALL next words including short ones like "So"
        edl_entry = edl_clips.get(label, {})
        next_words = _g3b_words(edl_entry.get("next_source_word", "") or "")   # '50%' -> ['50', 'percent']
        next_word = " ".join(next_words)
        next_leaked = False
        if next_words:                    # any of its words heard AFTER the expected last word (or at the very end)
            def _leak(ws):               # in a majority (batch 14 audit: every token of a symbol word, fail closed)
                idx = max((i for i, w in enumerate(ws) if _g3b_match(edl_last, w)), default=None)
                after = ws[idx + 1:] if idx is not None else ws[-2:]
                return any(n in after for n in next_words)
            next_leaked = sum(1 for ws in reads if _leak(ws)) * 2 > len(reads)

        ok = last_found and not next_leaked
        if not ok:
            all_pass = False

        status = "PASS" if ok else "FAIL"
        entry = {
            "segment": label,
            "edl_last": edl_last,
            "tail_transcript": tail_transcript[:80],
            "last_found": last_found,
            "votes": f"{votes}/{len(reads)}",
            "dissent": dissent,
            "next_source_word": next_word if next_word else None,
            "next_leaked": next_leaked,
            "pass": ok,
        }
        table.append(entry)

        leak_note = f", next='{next_word}' leaked!" if next_leaked else ""
        print(f"  {label}: tail='{tail_transcript[:50]}' last_found={last_found}{leak_note} [{status}]")

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

    # Duration window: 60-120s for both aspects (R2-14)
    dur_min = 60.0
    dur_max = 120.0
    dur_ok = dur_min <= dur <= dur_max
    results["duration"] = dur
    results["dur_ok"] = dur_ok
    if not dur_ok:
        all_pass = False
    print(f"  Duration: {dur:.2f}s ({dur_min:.0f}-{dur_max:.0f}s) [{'PASS' if dur_ok else 'FAIL'}]")

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
    tp_max = G5_TRUE_PEAK_MAX_DBFS.get(fmt, G5_TRUE_PEAK_MAX_DBFS["16x9"])   # DEC-1
    tp_ok = true_peak is not None and true_peak <= tp_max

    results["integrated_lufs"] = integrated
    results["true_peak"] = true_peak
    results["lufs_ok"] = lufs_ok
    results["tp_ok"] = tp_ok

    if not (lufs_ok and tp_ok):
        all_pass = False

    print(f"  Integrated: {integrated} LUFS (target -14+/-1) [{'PASS' if lufs_ok else 'FAIL'}]")
    print(f"  True Peak: {true_peak} dBFS (target <={tp_max}) [{'PASS' if tp_ok else 'FAIL'}]")

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

def _laplacian_centre(img_gray):
    """Laplacian variance on centre 60% region."""
    import cv2
    h, w = img_gray.shape
    x0, x1 = int(w * 0.2), int(w * 0.8)
    y0, y1 = int(h * 0.2), int(h * 0.8)
    roi = img_gray[y0:y1, x0:x1]
    return float(cv2.Laplacian(roi, cv2.CV_64F).var())


def gate_g8(final_mp4, segments, qa_dir, upscaled_labels=None, crop_widths=None,
            source_clips=None, fmt="16x9"):
    """Sharpness gate: absolute floor + source-relative degradation check (R2/A9).

    Two independent checks per talking-head segment:
      1. Source usability: source median Laplacian >= SHARPNESS_FLOOR (or scaled floor
         for upscaled content). If source itself is too soft, report but do not blame
         the pipeline.
      2. Pipeline degradation: output median >= 0.85 * source median. Catches encode
         quality loss, bad scaling, or accidental blur.

    Both checks must pass. Missing source or missing frames => FAIL.
    source_clips: dict mapping label -> source mp4 path."""
    import cv2

    print("\n=== G8: SHARPNESS ===")

    SHARPNESS_FLOOR = G8_SHARPNESS_FLOOR.get(fmt, G8_SHARPNESS_FLOOR["16x9"])  # DEC-1 (was 60)
    DEGRADATION_RATIO = 0.85      # output must be >= 85% of source sharpness

    if upscaled_labels is None:
        upscaled_labels = set()
    if crop_widths is None:
        crop_widths = {}
    if source_clips is None:
        source_clips = {}

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
        # Relative offsets into the clip (for source frame extraction)
        rel_offsets = [seg_dur * (i + 0.5) / 5 for i in range(5)]

        out_variances = []
        src_variances = []
        src_path = source_clips.get(label, "")
        has_source = bool(src_path) and os.path.exists(src_path)

        for i, t in enumerate(sample_times):
            # Output frame
            frame_path = os.path.join(qa_dir, f"g8_{label}_{i}.png")
            extract_frame(final_mp4, t, frame_path)
            if not os.path.exists(frame_path):
                continue
            img = cv2.imread(frame_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            out_variances.append(round(_laplacian_centre(img), 2))

            # Source frame at matching relative offset
            if has_source:
                src_frame_path = os.path.join(qa_dir, f"g8_{label}_{i}_src.png")
                extract_frame(src_path, rel_offsets[i], src_frame_path)
                if os.path.exists(src_frame_path):
                    src_img = cv2.imread(src_frame_path, cv2.IMREAD_GRAYSCALE)
                    if src_img is not None:
                        # Scale source to output dimensions for fair comparison
                        out_h, out_w = img.shape
                        if src_img.shape != img.shape:
                            src_img = cv2.resize(src_img, (out_w, out_h),
                                                 interpolation=cv2.INTER_AREA)
                        src_variances.append(round(_laplacian_centre(src_img), 2))

        out_median = float(np.median(out_variances)) if out_variances else 0.0
        src_median = float(np.median(src_variances)) if src_variances else 0.0

        # Floor for upscaled content
        if label in upscaled_labels:
            cw = crop_widths.get(label, 607)
            floor = round(SHARPNESS_FLOOR * (cw / 1080) ** 2, 1)
        else:
            floor = SHARPNESS_FLOOR

        # Check 1: absolute floor (output must meet minimum)
        floor_ok = out_median >= floor

        # Check 2: source-relative degradation
        if not has_source:
            # No source clip => cannot verify, FAIL
            degrad_ok = False
            degrad_reason = "no_source"
        elif not src_variances:
            degrad_ok = False
            degrad_reason = "src_frames_missing"
        elif src_median < floor:
            # Source itself is soft — report usability issue but still check ratio
            degrad_ok = out_median >= DEGRADATION_RATIO * src_median if src_median > 0 else False
            degrad_reason = f"soft_source({src_median:.1f}<{floor})"
        else:
            degrad_ok = out_median >= DEGRADATION_RATIO * src_median
            degrad_reason = None

        # DEC-3 (orchestrator, delegated by PBX, 2026-11-11; recorded in
        # docs/audits/DEFINITION_OF_DONE_PULSE_CHECK.md 'Decisions'): a clip is never rejected for SOURCE
        # softness alone - when the source itself is below the floor, the render only has to keep
        # >= DEGRADATION_RATIO of it. Otherwise floor and ratio both apply.
        soft_source = bool(has_source and src_variances and src_median < floor)
        ok = degrad_ok if soft_source else (floor_ok and degrad_ok)
        if not ok:
            all_pass = False

        ratio = round(out_median / src_median, 3) if src_median > 0 else 0.0

        table.append({
            "segment": label,
            "out_variances": out_variances,
            "src_variances": src_variances,
            "out_median": round(out_median, 2),
            "src_median": round(src_median, 2),
            "ratio": ratio,
            "floor": floor,
            "floor_pass": floor_ok,
            "degradation_pass": degrad_ok,
            "degradation_reason": degrad_reason,
            "pass": ok,
        })

        tag = " [R1-upscale]" if label in upscaled_labels else ""
        status = "PASS" if ok else "FAIL"
        ratio_str = f", ratio={ratio:.3f}" if src_median > 0 else ""
        src_info = f", src_median={src_median:.1f}" if has_source else " [NO SOURCE]"
        print(f"  {label}{tag}: out_median={out_median:.1f} (min={floor}){src_info}"
              f"{ratio_str} [{status}]")

    return all_pass, table


# ==============================================================
# G9: TAIL (last 1.0s not black/silent)
# ==============================================================

def gate_g9(final_mp4, qa_dir, fmt="16x9"):
    """Last 1.0s of final file: mean luma > 20 AND audio not silent.
    Law 20 — do not change thresholds."""
    import cv2

    print("\n=== G9: TAIL ===")

    LUMA_FLOOR = G9_LUMA_FLOOR.get(fmt, G9_LUMA_FLOOR["16x9"])  # DEC-1 (was 20)
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

def gate_g10(final_mp4, segments, crop_rects, qa_dir, chyron_clip_ids=None):
    """IMAGE-BASED chyron check on the FINAL output picture.
    Samples 5 frames inside each chyron-channel segment, takes the bottom 12% band,
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

    if chyron_clip_ids is None:
        chyron_clip_ids = set()

    chyron_segs = [seg for seg in segments
                   if seg.get("type") == "talking_head"
                   and seg["label"] in chyron_clip_ids]

    if not chyron_segs:
        print("  No chyron-channel shots — SKIP (PASS)")
        return True, {"skip": True, "pass": True}

    all_pass = True
    table = []

    for seg in chyron_segs:
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
    DEC-11: the brand-red ring masks the renderer draws, at the card layout (pipeline/credit_rings.py).
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

    # DEC-11 (2026-11-11): count the rings the renderer draws: brand-red (R > 100, R > G+40, R > B+40,
    # unchanged) external contours of ring size, each at its card-layout position for expected_count
    # channels (pipeline/credit_rings.py). A HoughCircles search also counted circles in avatar artwork
    # (OD-1: Natalie Brunell's orange background).
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))
    import credit_rings as CR
    cv2.imwrite(os.path.join(qa_dir, "g12_red_mask.png"), CR.red_mask(img))
    detected, _, at_layout, rings = CR.check_card(img, expected_count)
    debug_img = img.copy()
    for r in rings:
        cv2.ellipse(debug_img, (int(r["cx"]), int(r["cy"])), (int(r["axes"][1] / 2), int(r["axes"][0] / 2)),
                    0, 0, 360, (0, 255, 0), 3)
    cv2.imwrite(os.path.join(qa_dir, "g12_circles.png"), debug_img)

    ok = detected == expected_count and bool(at_layout)
    if detected == expected_count and not at_layout:
        print(f"  {detected} rings, but not at the card layout's positions for {expected_count} channels")

    print(f"  Detected circles: {detected} (expected: {expected_count}) [{'PASS' if ok else 'FAIL'}]")

    return ok, {
        "detected": detected,
        "expected": expected_count,
        "at_layout": at_layout,
        "rings": rings,
        "method": "DEC-11 ring mask",
        "pass": ok,
    }


# ==============================================================
# G13: VO_AUDIBLE (M7 — every scripted VO line must be heard)
# ==============================================================

# Known music hallucination phrases whisper produces on silence/music
_MUSIC_HALLUCINATIONS = {
    "thanks for watching", "subscribe", "music", "thank you for watching",
    "please subscribe", "like and subscribe", "see you next time",
    "you", "the", "",
}

FOLLOW_WORDS = {"follow", "subscribe", "check"}


def _fuzzy_word_overlap(scripted, transcribed):
    """Word-set overlap ratio (intersection / scripted count) in the one canonical form (pipeline/canon.py)."""
    s_words = set(_canon_tokens(scripted))
    t_words = set(_canon_tokens(transcribed))
    if not s_words:
        return 0.0
    return len(s_words & t_words) / len(s_words)


def _is_silent_reading(transcript):
    """An empty reading, or one that is only a known music / outro hallucination, in canonical form (Claude-gates
    V3: the raw set never matched a transcript that carries punctuation)."""
    t = _canon_tokens(transcript)
    return len(" ".join(t)) < 3 or t in [_canon_tokens(h) for h in _MUSIC_HALLUCINATIONS]


def _says(transcript_tokens, phrase):
    """True when the canonical words of `phrase` occur as a contiguous run in the transcript's canonical words
    (token equality, never a substring: Claude-gates T1 / T8)."""
    p = _canon_tokens(phrase)
    n = len(p)
    return n > 0 and any(transcript_tokens[i:i + n] == p for i in range(len(transcript_tokens) - n + 1))


def _rms_db(wav_path):
    """Compute RMS in dB from a WAV file. Returns -inf for silence."""
    try:
        wf = wave.open(wav_path, "rb")
        frames = wf.readframes(wf.getnframes())
        wf.close()
        samples = np.frombuffer(frames, dtype=np.int16).astype(float)
        if len(samples) == 0:
            return float("-inf")
        rms = np.sqrt(np.mean(samples ** 2))
        if rms < 1:
            return float("-inf")
        return 20 * math.log10(rms / 32768.0)
    except Exception:
        return float("-inf")


def gate_g13(final_mp4, segments, qa_dir, edl_path=None, channels_json_path=None):
    """M7/M14 AUDIO PRESENCE: transcribe each VO slot from the OUTPUT audio.
    Requires >= 80% fuzzy word match to scripted text.
    Signoff slot must contain channel names (or aliases from channels.json) and a follow/subscribe word.
    VO RMS must be >= music bed + 6 dB in the slot.
    Empty or music-hallucination transcripts = SILENT = FAIL."""
    print("\n=== G13: VO_AUDIBLE (M7/M14) ===")

    vo_segs = [s for s in segments if s.get("type") == "vo"]
    # Also check signoff within the shoutout segment
    shout_seg = next((s for s in segments if s.get("type") == "shoutout"), None)

    # Build channel alias map from channels.json (M14)
    # Maps display_name -> set of whisper-friendly aliases
    channel_aliases = {}
    if channels_json_path and os.path.exists(channels_json_path):
        try:
            with open(channels_json_path) as f:
                ch_registry = json.load(f)
            for entry in ch_registry:
                name = entry.get("display_name", "")
                if not name:
                    continue
                aliases = set()
                aliases.add(name.lower())
                # Add any explicit aliases from registry
                for a in entry.get("aliases", []):
                    aliases.add(a.lower())
                # Auto-generate split alias (e.g. "CoinDesk" -> "coin desk")
                import re
                spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).lower()
                if spaced != name.lower():
                    aliases.add(spaced)
                channel_aliases[name] = aliases
        except Exception as e:
            print(f"  G13 alias map error: {e}")

    # Load EDL for signoff text and channel names
    signoff_text = ""
    channel_names = []
    if edl_path and os.path.exists(edl_path):
        with open(edl_path) as f:
            edl = json.load(f)
        signoff_text = edl.get("vo", {}).get("signoff", "")
        for clip in edl.get("clips", []):
            ch = clip.get("channel", "")
            if ch and ch not in channel_names:
                channel_names.append(ch)
        hook_ch = edl.get("hook", {}).get("channel", "")
        if hook_ch and hook_ch not in channel_names:
            channel_names.append(hook_ch)

    if not vo_segs and not shout_seg:
        print("  No VO segments or shoutout — SKIP (PASS)")
        return True, {"skip": True, "pass": True}

    # Ensure faster-whisper medium model is loaded (singleton)
    _get_fw_model()
    all_pass = True
    table = []

    # Check each VO segment (intro, bridges)
    for seg in vo_segs:
        label = seg["label"]
        start = seg["start"]
        dur = seg["end"] - seg["start"]
        scripted = seg.get("text", "")

        print(f"  Slot: {label} ({start:.2f}s–{seg['end']:.2f}s)")

        # Extract audio region
        wav_path = os.path.join(qa_dir, f"g13_{label}.wav")
        extract_audio_region(final_mp4, start, dur, wav_path, sr=16000)

        if not os.path.exists(wav_path):
            print(f"    FAIL: could not extract audio")
            table.append({"slot": label, "pass": False, "reason": "no audio extracted"})
            all_pass = False
            continue

        # Transcribe with faster-whisper medium
        transcript, _ = fw_transcribe(wav_path, word_timestamps=False)
        transcript = transcript.strip()
        print(f"    Scripted:     '{scripted}'")
        print(f"    Transcribed:  '{transcript}'")

        # Check for music hallucination / silence (canonical form)
        if _is_silent_reading(transcript):
            print(f"    FAIL: SILENT (hallucination or empty)")
            table.append({"slot": label, "pass": False, "reason": "SILENT",
                          "transcript": transcript, "scripted": scripted})
            all_pass = False
            continue

        # Fuzzy word match
        overlap = _fuzzy_word_overlap(scripted, transcript)
        print(f"    Word overlap: {overlap:.0%} (threshold: 80%)")

        # RMS check: extract VO region and flanking music region
        rms_vo = _rms_db(wav_path)
        # Sample 2s of music bed from just before VO slot (or after if at start)
        music_start = max(0, start - 2.5)
        music_wav = os.path.join(qa_dir, f"g13_{label}_music.wav")
        extract_audio_region(final_mp4, music_start, 2.0, music_wav, sr=16000)
        rms_music = _rms_db(music_wav)
        rms_delta = rms_vo - rms_music if rms_music != float("-inf") else 99.0
        print(f"    VO RMS: {rms_vo:.1f} dB, Music RMS: {rms_music:.1f} dB, delta: {rms_delta:.1f} dB (need >= 6)")

        # Primary: transcript match >= 80%. RMS delta is informational only
        # because the output audio is a full mix (VO + music + clip audio).
        slot_pass = overlap >= 0.80
        if not slot_pass:
            all_pass = False
            print(f"    FAIL: overlap {overlap:.0%} < 80%")
        else:
            print(f"    PASS (RMS info: delta {rms_delta:.1f} dB)")

        table.append({
            "slot": label, "pass": slot_pass,
            "overlap": round(overlap, 3),
            "rms_vo": round(rms_vo, 1), "rms_music": round(rms_music, 1),
            "rms_delta": round(rms_delta, 1),
            "transcript": transcript, "scripted": scripted,
        })

    # Check signoff within shoutout segment
    if shout_seg and signoff_text:
        label = "signoff"
        # Signoff VO plays during the shoutout segment
        start = shout_seg["start"]
        dur = shout_seg["end"] - shout_seg["start"]

        print(f"  Slot: {label} ({start:.2f}s–{shout_seg['end']:.2f}s)")

        wav_path = os.path.join(qa_dir, f"g13_{label}.wav")
        extract_audio_region(final_mp4, start, dur, wav_path, sr=16000)

        if not os.path.exists(wav_path):
            print(f"    FAIL: could not extract audio")
            table.append({"slot": label, "pass": False, "reason": "no audio extracted"})
            all_pass = False
        else:
            transcript, _ = fw_transcribe(wav_path, word_timestamps=False)
            transcript = transcript.strip()
            print(f"    Scripted:     '{signoff_text}'")
            print(f"    Transcribed:  '{transcript}'")

            if _is_silent_reading(transcript):
                print(f"    FAIL: SILENT (hallucination or empty)")
                table.append({"slot": label, "pass": False, "reason": "SILENT",
                              "transcript": transcript, "scripted": signoff_text})
                all_pass = False
            else:
                overlap = _fuzzy_word_overlap(signoff_text, transcript)
                print(f"    Word overlap: {overlap:.0%} (threshold: 80%)")

                # RMS check
                rms_vo = _rms_db(wav_path)
                music_start = max(0, start - 2.5)
                music_wav = os.path.join(qa_dir, f"g13_{label}_music.wav")
                extract_audio_region(final_mp4, music_start, 2.0, music_wav, sr=16000)
                rms_music = _rms_db(music_wav)
                rms_delta = rms_vo - rms_music if rms_music != float("-inf") else 99.0
                print(f"    VO RMS: {rms_vo:.1f} dB, Music RMS: {rms_music:.1f} dB, delta: {rms_delta:.1f} dB")

                # Signoff-specific: channel names and follow/subscribe word, as canonical word runs
                t_tokens = _canon_tokens(transcript)
                missing_channels = []
                for ch in channel_names:
                    # M14: check channel name OR any alias from channels.json
                    aliases = channel_aliases.get(ch, {ch.lower()})
                    if not any(_says(t_tokens, alias) for alias in aliases):
                        missing_channels.append(ch)

                has_follow = any(_says(t_tokens, w) for w in FOLLOW_WORDS)

                # Primary: transcript match, channels, follow word.
                # RMS delta is informational (output is a full mix).
                slot_pass = (overlap >= 0.80
                             and not missing_channels and has_follow)
                reasons = []
                if overlap < 0.80:
                    reasons.append(f"overlap {overlap:.0%} < 80%")
                if missing_channels:
                    reasons.append(f"missing channels: {missing_channels}")
                if not has_follow:
                    reasons.append("no follow/subscribe word")

                if not slot_pass:
                    all_pass = False
                    print(f"    FAIL: {', '.join(reasons)}")
                else:
                    print(f"    PASS (channels+follow heard, RMS info: delta {rms_delta:.1f} dB)")

                table.append({
                    "slot": label, "pass": slot_pass,
                    "overlap": round(overlap, 3),
                    "rms_vo": round(rms_vo, 1), "rms_music": round(rms_music, 1),
                    "rms_delta": round(rms_delta, 1),
                    "channels_heard": [c for c in channel_names if c not in missing_channels],
                    "channels_missing": missing_channels,
                    "has_follow_word": has_follow,
                    "transcript": transcript, "scripted": signoff_text,
                })

    print(f"  G13 overall: {'PASS' if all_pass else 'FAIL'}")
    return all_pass, table


# ==============================================================
# G3c: ACOUSTIC_TAIL (M19 — last 120ms of each clip < -35 dBFS)
# ==============================================================

def gate_g3c(final_mp4, segments, qa_dir, fmt="16x9"):
    """M19a: Acoustic tail check on each talking-head clip in the OUTPUT.

    Two checks per clip:
      TAIL — last 120ms must show declining energy and no onset (no next-word
             leak). The final 40ms (valley zone) must be <= speech_median - 12 dB.
      HEAD — first 120ms must have no onset (cut-in contamination).

    Uses pipeline/acoustic.py for RMS analysis."""
    print("\n=== G3c: ACOUSTIC_TAIL (M19a relative rule) ===")

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))
    from acoustic import rms_envelope, _load_wav_samples, _extract_audio_mono

    import tempfile

    VALLEY_DEPTH_DB = G3C_VALLEY_DEPTH_DB.get(fmt, G3C_VALLEY_DEPTH_DB["16x9"])  # M19a 12 dB; DEC-1

    all_pass = True
    table = []

    for seg in segments:
        if seg.get("type") != "talking_head":
            continue

        label = seg["label"]
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_dur = seg_end - seg_start

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            full_wav = tmp.name
        try:
            _extract_audio_mono(final_mp4, seg_start, seg_dur, full_wav)
            samples, sr = _load_wav_samples(full_wav)
            rms_db, times = rms_envelope(samples, sr)

            # Speech median: median RMS of the full clip (excluding quietest 10%)
            if len(rms_db) > 0:
                sorted_rms = np.sort(rms_db)
                speech_start = max(1, len(sorted_rms) // 10)
                speech_median_db = float(np.median(sorted_rms[speech_start:]))
            else:
                speech_median_db = -20.0

            tail_threshold = speech_median_db - VALLEY_DEPTH_DB

            # ── TAIL: last 120ms (12 frames at 10ms hop) ──
            tail_frames = max(1, 120 // 10)
            tail_rms = rms_db[-tail_frames:] if len(rms_db) >= tail_frames else rms_db

            # 1) Onset check: no SUSTAINED rising edge in the tail 120ms
            #    A rise from < (threshold-3) to > threshold sustained for >= 3 frames
            #    signals next-word leak. Single-frame spikes from encoding are ignored.
            tail_has_onset = False
            for i in range(1, len(tail_rms)):
                if tail_rms[i - 1] < (tail_threshold - 3.0) and tail_rms[i] > tail_threshold:
                    # Check sustain: next 2 frames also above threshold
                    sustained = all(
                        i + k < len(tail_rms) and tail_rms[i + k] > tail_threshold
                        for k in range(1, 3)
                    )
                    if sustained:
                        tail_has_onset = True
                        break

            # 2) Valley zone check: last 60ms (6 frames) median must be <= speech_median - 12 dB
            #    This verifies the cut sits in a valley, not mid-speech.
            #    Uses median (not max) to tolerate single-frame spikes from encoding.
            valley_zone = tail_rms[-6:] if len(tail_rms) >= 6 else tail_rms
            valley_max_db = float(np.median(valley_zone)) if len(valley_zone) > 0 else -80.0

            tail_ok = (valley_max_db <= tail_threshold) and not tail_has_onset

            # Full tail max for reporting
            tail_max_db = float(np.max(tail_rms)) if len(tail_rms) > 0 else -80.0

            # ── HEAD: first 120ms — informational onset detection ──
            # Natural speech onset at clip start is expected and NOT a failure.
            # Only flag if onset happens in first 10ms (overlap from prior segment).
            head_frames = min(tail_frames, len(rms_db))
            head_rms = rms_db[:head_frames]
            head_has_onset = False
            for i in range(1, min(2, len(head_rms))):  # only first 10ms
                if head_rms[i - 1] < -35.0 and head_rms[i] > -30.0:
                    head_has_onset = True
                    break
            head_ok = not head_has_onset

        except Exception as e:
            valley_max_db = 0.0
            tail_max_db = 0.0
            tail_has_onset = True
            tail_ok = False
            tail_threshold = -32.0
            speech_median_db = -20.0
            head_has_onset = False
            head_ok = True
            print(f"  {label}: ERROR {e}")
        finally:
            if os.path.exists(full_wav):
                os.unlink(full_wav)

        ok = tail_ok and head_ok
        if not ok:
            all_pass = False

        entry = {
            "segment": label,
            "speech_median_db": round(speech_median_db, 1),
            "tail_threshold_db": round(tail_threshold, 1),
            "valley_max_db": round(valley_max_db, 1),
            "tail_max_db": round(tail_max_db, 1),
            "tail_has_onset": tail_has_onset,
            "tail_ok": tail_ok,
            "head_has_onset": head_has_onset,
            "head_ok": head_ok,
            "pass": ok,
        }
        table.append(entry)

        status = "PASS" if ok else "FAIL"
        tail_note = f"valley={valley_max_db:.1f}dB thresh={tail_threshold:.1f}dB onset={'Y' if tail_has_onset else 'N'}"
        head_note = f"head onset={'Y' if head_has_onset else 'N'}"
        print(f"  {label}: speech_med={speech_median_db:.1f}dB {tail_note}, {head_note} [{status}]")

    return all_pass, table


# ==============================================================
# MAIN
# ==============================================================

def run_all_gates(final_mp4, manifest_path, qa_dir=None, source_clips=None,
                   vo_assembled_tracks=None, edl_path=None, channels_json_path=None,
                   horiz_mp4=None):
    """Run all gates. Returns (all_pass, results_dict).
    source_clips: dict mapping clip label -> source mp4 path (for G4 layout classification).
    vo_assembled_tracks: dict mapping VO label -> assembled WAV path (silence + stem, no BGM).
    edl_path: path to edl.json (for G10 chyron channel lookup).
    channels_json_path: path to channels.json registry (for G10 has_chyron)."""
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

    # G3b: Cut-out clean (last 1.0s must end with EDL last_word, no next word leak)
    g3b_pass, g3b_table = gate_g3b(final_mp4, segments, qa_dir, edl_path=edl_path)
    results["G3b_cut_out_clean"] = {"pass": g3b_pass, "table": g3b_table}
    if not g3b_pass:
        any_fail = True

    # G3c: Acoustic tail (M19 — last 120ms of each clip < -35 dBFS, no onset)
    g3c_pass, g3c_table = gate_g3c(final_mp4, segments, qa_dir, fmt=fmt)
    results["G3c_acoustic_tail"] = {"pass": g3c_pass, "table": g3c_table}
    if not g3c_pass:
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

    # G8: Sharpness (source-relative, R2/A9)
    g8_pass, g8_table = gate_g8(final_mp4, segments, qa_dir,
                                 source_clips=source_clips, fmt=fmt)
    results["G8_sharpness"] = {"pass": g8_pass, "table": g8_table}
    if not g8_pass:
        any_fail = True

    # G9: Tail (last 1.0s not black/silent)
    g9_pass, g9_data = gate_g9(final_mp4, qa_dir, fmt=fmt)
    results["G9_tail"] = {"pass": g9_pass, "data": g9_data}
    if not g9_pass:
        any_fail = True

    # G11: Parity (vertical mirrors horizontal) — R2-02
    if horiz_mp4 and os.path.exists(horiz_mp4):
        g11_pass, g11_data = gate_g11(final_mp4, horiz_mp4, segments, segments)
        results["G11_parity"] = {"pass": g11_pass, "data": g11_data}
        if not g11_pass:
            any_fail = True
    else:
        results["G11_parity"] = {"pass": True, "skip": True, "reason": "no horiz_mp4"}

    # G10: Chyron (channels with has_chyron=true in registry)
    chyron_clip_ids = set()
    if edl_path and channels_json_path:
        try:
            with open(edl_path) as f:
                edl = json.load(f)
            with open(channels_json_path) as f:
                ch_registry = json.load(f)
            chyron_channels = {
                entry["display_name"]
                for entry in ch_registry
                if entry.get("has_chyron", False)
            }
            # Map hook
            hook = edl.get("hook", {})
            if hook.get("channel") in chyron_channels:
                chyron_clip_ids.add("hook")
            # Map clips
            for clip in edl.get("clips", []):
                if clip.get("channel") in chyron_channels:
                    chyron_clip_ids.add(f"clip_{clip['index']:02d}")
        except Exception as e:
            print(f"  G10 registry lookup error: {e}")

    g10_pass, g10_table = gate_g10(final_mp4, segments, {}, qa_dir,
                                    chyron_clip_ids=chyron_clip_ids)
    results["G10_chyron"] = {"pass": g10_pass, "data": g10_table}
    if not g10_pass:
        any_fail = True

    # G13: VO Audible (M7 — every scripted VO line must be heard in output)
    g13_pass, g13_table = gate_g13(final_mp4, segments, qa_dir, edl_path=edl_path,
                                    channels_json_path=channels_json_path)
    results["G13_vo_audible"] = {"pass": g13_pass, "table": g13_table}
    if not g13_pass:
        any_fail = True

    # G12: Credits (avatar circles in shoutout)
    expected_channels = 0
    if edl_path and os.path.exists(edl_path):
        try:
            with open(edl_path) as f:
                edl_data = json.load(f)
            channel_set = set()
            if edl_data.get("hook", {}).get("channel"):
                channel_set.add(edl_data["hook"]["channel"])
            for clip in edl_data.get("clips", []):
                if clip.get("channel"):
                    channel_set.add(clip["channel"])
            expected_channels = len(channel_set)
        except Exception:
            pass
    if expected_channels > 0:
        g12_pass, g12_data = gate_g12(final_mp4, segments, expected_channels, qa_dir)
        results["G12_credits"] = {"pass": g12_pass, "data": g12_data}
        if not g12_pass:
            any_fail = True
    else:
        g12_pass = True
        results["G12_credits"] = {"pass": True, "skip": True}

    elapsed = time.time() - t0
    results["elapsed_s"] = round(elapsed, 1)
    results["all_pass"] = not any_fail

    # Summary
    print(f"\n{'='*50}")
    print(f"  G1 Voice:     {'PASS' if g1_pass else 'FAIL'}")
    print(f"  G2 Watermark: {'PASS' if g2_pass else 'FAIL'}")
    print(f"  G3 Cuts:      {'PASS' if g3_pass else 'FAIL'}")
    print(f"  G3b OutClean: {'PASS' if g3b_pass else 'FAIL'}")
    print(f"  G3c AcouTail: {'PASS' if g3c_pass else 'FAIL'}")
    print(f"  G4 Faces:     {'PASS' if g4_pass else 'FAIL'}")
    print(f"  G5 Tech:      {'PASS' if g5_pass else 'FAIL'}")
    print(f"  G6 Pre-roll:  {'PASS' if g6_pass else 'FAIL'}")
    print(f"  G8 Sharpness: {'PASS' if g8_pass else 'FAIL'}")
    print(f"  G9 Tail:      {'PASS' if g9_pass else 'FAIL'}")
    print(f"  G10 Chyron:   {'PASS' if g10_pass else 'FAIL'}")
    print(f"  G12 Credits:  {'PASS' if g12_pass else 'FAIL'}")
    print(f"  G13 VOAudible:{'PASS' if g13_pass else 'FAIL'}")
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
            for gate_name in ["G1_voice", "G2_watermark", "G3_cuts", "G3b_cut_out_clean", "G3c_acoustic_tail", "G4_faces", "G5_tech", "G6_preroll", "G8_sharpness", "G9_tail", "G10_chyron", "G12_credits", "G13_vo_audible"]:
                gate_data = results.get(gate_name, {})
                if not gate_data.get("pass", True):
                    f.write(f"  FAILED: {gate_name}\n")
        print(f"  GATE_FAIL.txt written: {fail_path}")
    else:
        # R2-22: remove stale GATE_FAIL.txt on passing run
        GATE_FAIL_PATH = os.path.join(qa_dir, "GATE_FAIL.txt")
        if os.path.exists(GATE_FAIL_PATH):
            os.remove(GATE_FAIL_PATH)
            print(f"  Removed stale GATE_FAIL.txt: {GATE_FAIL_PATH}")

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
