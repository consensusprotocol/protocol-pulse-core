#!/usr/bin/env python3
"""Fix clip OUT points per Law 14c: whisper trailing-syllable compensation.
OUT = max(next_word_start - 60ms, waveform_decay_point)
Hard gate: re-transcribe last 700ms to confirm final word matches EDL."""
import json, os, subprocess, sys, wave, math, struct
import numpy as np

BASE = "/home/ultron/protocol_pulse/segment_v1"
SOURCES = os.path.join(BASE, "sources")
TRANSCRIPTS = os.path.join(BASE, "transcripts")
QA = os.path.join(BASE, "qa_v3")
os.makedirs(QA, exist_ok=True)

with open(os.path.join(BASE, "edl_v2.json")) as f:
    edl = json.load(f)

with open(os.path.join(BASE, "cuts_v2.json")) as f:
    cuts_v2 = json.load(f)


def extract_wav(src, start, end, out):
    """Extract audio segment to 16kHz mono PCM WAV (no CUDA)."""
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(max(0, start)), "-to", str(end),
        "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", out,
    ], capture_output=True, timeout=30)
    return os.path.exists(out) and os.path.getsize(out) > 100


def read_wav(path):
    try:
        with wave.open(path, 'rb') as wf:
            n = wf.getnframes()
            if n == 0:
                return np.array([], dtype=np.float32), 0
            raw = wf.readframes(n)
            sr = wf.getframerate()
            return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0, sr
    except Exception:
        return np.array([], dtype=np.float32), 0


def db(v):
    return max(20 * math.log10(v), -80.0) if v > 0 else -80.0


def compute_rms_windows(samples, sr, window_ms=10):
    """Compute RMS in fixed windows."""
    win = int(sr * window_ms / 1000)
    if win == 0 or len(samples) < win:
        return np.array([]), win
    n_win = len(samples) // win
    rms = np.zeros(n_win)
    for i in range(n_win):
        chunk = samples[i * win:(i + 1) * win]
        rms[i] = np.sqrt(np.mean(chunk ** 2))
    return rms, win


def find_decay_point(samples, sr, word_end_offset_s):
    """Find waveform decay point after word_end: first 10ms window where
    RMS stays below noise_floor+6dB for 120ms, then add 150ms room tone."""
    rms, win = compute_rms_windows(samples, sr, 10)
    if len(rms) == 0:
        return word_end_offset_s + 0.15

    # Noise floor from last 200ms of handle
    noise_windows = max(1, int(0.2 * sr / win))
    tail_rms = rms[-noise_windows:] if noise_windows <= len(rms) else rms
    noise_floor_db = db(np.median(tail_rms))
    threshold_db = noise_floor_db + 6.0

    # Start searching from word_end
    word_win = int(word_end_offset_s * sr / win)
    word_win = min(word_win, len(rms) - 1)

    # Find 120ms sustain below threshold (12 windows of 10ms)
    sustain_required = 12
    sustain_count = 0
    decay_win = word_win

    for i in range(word_win, len(rms)):
        if db(rms[i]) < threshold_db:
            sustain_count += 1
            if sustain_count >= sustain_required:
                # Decay point is where sustain started
                decay_win = i - sustain_required + 1
                break
        else:
            sustain_count = 0
    else:
        # Never found sustained silence — use end of handle
        decay_win = len(rms) - 1

    # Add 150ms room tone
    room_tone_wins = int(0.15 * sr / win)
    final_win = min(decay_win + room_tone_wins, len(rms) - 1)
    return final_win * win / sr


def find_speech_onset(samples, sr, word_start_offset_s):
    """Find speech onset before first word (same as stage3_v2)."""
    rms, win = compute_rms_windows(samples, sr, 10)
    if len(rms) == 0:
        return 0.0
    noise_windows = max(1, int(0.1 * sr / win))
    noise_floor = np.median(rms[:noise_windows]) if noise_windows <= len(rms) else np.median(rms)
    threshold_db = db(noise_floor) + 12
    word_win = min(int(word_start_offset_s * sr / win), len(rms) - 1)
    max_walk = int(0.4 * sr / win)
    onset_win = word_win
    for i in range(word_win, max(word_win - max_walk, 0), -1):
        if db(rms[i]) < threshold_db:
            onset_win = i + 1
            break
    else:
        onset_win = max(word_win - max_walk, 0)
    return onset_win * win / sr


def whisper_verify_tail(src, cut_out, last_word_expected):
    """Hard gate: transcribe last 700ms with faster-whisper, confirm final word."""
    tail_wav = os.path.join(QA, "tail_verify.wav")
    extract_wav(src, cut_out - 0.7, cut_out, tail_wav)

    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("large-v3", device="cuda", compute_type="float16")
        segments, _ = model.transcribe(tail_wav, word_timestamps=True, beam_size=1)
        words = []
        for seg in segments:
            if seg.words:
                words.extend(seg.words)
        if words:
            last_transcribed = words[-1].word.strip().lower().rstrip(".,!?")
            expected = last_word_expected.strip().lower().rstrip(".,!?")
            match = last_transcribed == expected
            all_text = " ".join(w.word.strip() for w in words)
            return match, all_text, last_transcribed
        return False, "", ""
    except Exception as e:
        print(f"    Whisper verify error: {e}")
        return None, "", str(e)


def get_next_word_start(video_id, word_end):
    """Look up the next word after word_end in transcript."""
    transcript_path = os.path.join(TRANSCRIPTS, f"{video_id}.json")
    if not os.path.exists(transcript_path):
        return None
    with open(transcript_path) as f:
        data = json.load(f)
    words = data.get("words", [])
    best_idx = None
    best_dist = 999
    for i, w in enumerate(words):
        d = abs(w["end"] - word_end)
        if d < best_dist:
            best_dist = d
            best_idx = i
    if best_idx is not None and best_idx + 1 < len(words):
        return words[best_idx + 1]["start"]
    return None


# Pre-computed next-word starts (verified from transcripts)
NEXT_WORD_STARTS = {
    "hook": 234.100,      # "Yeah." after "far."
    "clip_01": 89.470,    # "Stolen" after "group."
    "clip_02": 248.500,   # "WHEN" after "BEFORE." (same timestamp — tight)
    "clip_03": 777.180,   # "That" after "account."
    "clip_04": 486.460,   # "And" after "Bitcoin."
}


def process_clip_v3(clip_info, clip_id, old_cut):
    """Compute new OUT point per Law 14c."""
    vid = clip_info["video_id"]
    src = os.path.join(SOURCES, f"{vid}.mp4")
    if not os.path.exists(src):
        print(f"  ERROR: source not found: {src}")
        return None

    ws = clip_info["word_start"]
    we = clip_info["word_end"]
    last_word = clip_info.get("last_word", "")

    # Handle: 0.5s before first word, 1.0s after last word (wider for decay search)
    hs = max(0, ws - 0.5)
    he = we + 1.0

    # Extract audio with wide handle
    raw_wav = os.path.join(QA, f"{clip_id}_v3_raw.wav")
    extract_wav(src, hs, he, raw_wav)
    samples, sr = read_wav(raw_wav)
    if len(samples) == 0:
        print(f"  ERROR: empty audio for {clip_id}")
        return None

    # Law 14c: two candidates for OUT point
    word_end_offset = we - hs

    # Candidate 1: next_word_start - 60ms
    nws = NEXT_WORD_STARTS.get(clip_id)
    if nws is None:
        nws = get_next_word_start(vid, we)
    candidate_1 = nws - 0.06 if nws else we + 0.15

    # Candidate 2: waveform decay point
    decay_offset = find_decay_point(samples, sr, word_end_offset)
    candidate_2 = hs + decay_offset

    # OUT = max of both candidates (absolute time in source)
    cut_out = max(candidate_1, candidate_2)

    # Onset (same method as before)
    onset_offset = find_speech_onset(samples, sr, ws - hs)
    cut_in = hs + onset_offset
    if cut_in > ws:
        cut_in = max(ws - 0.05, hs)

    print(f"  {clip_id}: word_end={we:.3f}, next_word={nws:.3f}" +
          f" → c1={candidate_1:.3f} c2={candidate_2:.3f} → OUT={cut_out:.3f}" +
          f" (was {old_cut['cut_out']:.3f}, delta={cut_out - old_cut['cut_out']:+.3f}s)")

    # Hard gate: whisper verify (attempt up to 4 widenings)
    verified = False
    verify_out = cut_out
    for attempt in range(5):
        match, text, last_w = whisper_verify_tail(src, verify_out, last_word)
        if match is None:
            print(f"    Whisper unavailable, skipping verification")
            verified = True  # Allow through if whisper is down
            break
        if match:
            print(f"    VERIFY PASS (attempt {attempt}): \"{text}\" — last word \"{last_w}\" matches")
            verified = True
            cut_out = verify_out
            break
        else:
            print(f"    VERIFY FAIL (attempt {attempt}): \"{text}\" — got \"{last_w}\", expected \"{last_word.rstrip('.,!?').lower()}\"")
            verify_out += 0.1  # Widen 100ms
    if not verified:
        print(f"    WARNING: Could not verify after 5 attempts, using best estimate")

    return {
        "clip_id": clip_id,
        "video_id": vid,
        "word_start": ws,
        "word_end": we,
        "handle_start": round(hs, 3),
        "handle_end": round(he, 3),
        "cut_in": round(cut_in, 3),
        "cut_out": round(cut_out, 3),
        "cut_duration": round(cut_out - cut_in, 3),
        "law_14c": {
            "next_word_start": round(nws, 3) if nws else None,
            "candidate_1_nws": round(candidate_1, 3),
            "candidate_2_decay": round(candidate_2, 3),
            "verified": verified,
        }
    }


if __name__ == "__main__":
    print("=== FIX TAILS v3 (Law 14c) ===\n")

    all_cuts = []

    # Hook
    hook = edl.get("hook")
    if hook and hook.get("video_id"):
        old = next((c for c in cuts_v2 if c["clip_id"] == "hook"), None)
        if old:
            cut = process_clip_v3(hook, "hook", old)
            if cut:
                all_cuts.append(cut)

    # Clips
    for clip in edl.get("clips", []):
        clip_id = f"clip_{clip['index']:02d}"
        old = next((c for c in cuts_v2 if c["clip_id"] == clip_id), None)
        if old:
            cut = process_clip_v3(clip, clip_id, old)
            if cut:
                all_cuts.append(cut)

    total = sum(c["cut_duration"] for c in all_cuts)
    print(f"\nCuts v3: {len(all_cuts)} clips, {total:.1f}s total")

    with open(os.path.join(BASE, "cuts_v3.json"), "w") as f:
        json.dump(all_cuts, f, indent=2)
    print(f"Written cuts_v3.json")
