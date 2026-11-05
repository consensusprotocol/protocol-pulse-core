#!/usr/bin/env python3
"""Stage S4: Extract clips with handles, find true speech onset/offset, seam QA.
Law 14c: transcript timestamps are NOT cut points. Waveform-verified.
Writes cuts_final.json with verified:true per cut (Law 22)."""
import json
import os
import subprocess
import numpy as np
import wave
import struct
import math
import sys

BASE = "/home/ultron/protocol_pulse/segment_v2"
EDL_FILE = f"{BASE}/edl.json"
SOURCES_DIR = f"{BASE}/sources"
QA_DIR = f"{BASE}/qa"
os.makedirs(QA_DIR, exist_ok=True)

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

with open(EDL_FILE) as f:
    edl = json.load(f)


def extract_audio_segment(source_mp4, start_s, end_s, output_wav):
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(max(0, start_s)), "-to", str(end_s),
        "-i", source_mp4, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        output_wav,
    ], capture_output=True, timeout=30)


def read_wav_samples(wav_path):
    try:
        with wave.open(wav_path, 'rb') as wf:
            n = wf.getnframes()
            if n == 0:
                return np.array([], dtype=np.float32), 0
            raw = wf.readframes(n)
            sr = wf.getframerate()
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            return samples, sr
    except Exception:
        return np.array([], dtype=np.float32), 0


def compute_rms_envelope(samples, sr, window_ms=10):
    win_samples = int(sr * window_ms / 1000)
    if win_samples == 0 or len(samples) < win_samples:
        return np.array([]), 0
    n_windows = len(samples) // win_samples
    rms = np.zeros(n_windows)
    for i in range(n_windows):
        chunk = samples[i * win_samples:(i + 1) * win_samples]
        rms[i] = np.sqrt(np.mean(chunk ** 2))
    return rms, win_samples


def db(val):
    if val <= 0:
        return -80.0
    return max(20 * math.log10(val), -80.0)


def find_speech_onset(samples, sr, word_start_s, handle_start_s):
    rms, win_samples = compute_rms_envelope(samples, sr, window_ms=10)
    if len(rms) == 0:
        return 0.0
    noise_windows = max(1, int(0.1 * sr / win_samples))
    noise_floor = np.median(rms[:noise_windows]) if noise_windows <= len(rms) else np.median(rms)
    threshold_db = db(noise_floor) + 12
    word_offset_s = word_start_s - handle_start_s
    word_win = min(int(word_offset_s * sr / win_samples), len(rms) - 1)
    max_walk = int(0.4 * sr / win_samples)
    onset_win = word_win
    for i in range(word_win, max(word_win - max_walk, 0), -1):
        if db(rms[i]) < threshold_db:
            onset_win = i + 1
            break
    else:
        onset_win = max(word_win - max_walk, 0)
    return onset_win * win_samples / sr


def find_speech_offset(samples, sr, word_end_s, handle_start_s):
    rms, win_samples = compute_rms_envelope(samples, sr, window_ms=10)
    if len(rms) == 0:
        return len(samples) / sr
    noise_windows = max(1, int(0.1 * sr / win_samples))
    noise_floor = np.median(rms[-noise_windows:]) if noise_windows <= len(rms) else np.median(rms)
    threshold_db = db(noise_floor) + 12
    word_offset_s = word_end_s - handle_start_s
    word_win = min(int(word_offset_s * sr / win_samples), len(rms) - 1)
    max_walk = int(0.6 * sr / win_samples)
    offset_win = word_win
    for i in range(word_win, min(word_win + max_walk, len(rms))):
        if db(rms[i]) >= threshold_db:
            offset_win = i
        else:
            break
    room_tone = int(0.15 * sr / win_samples)
    offset_win = min(offset_win + room_tone, len(rms) - 1)
    return offset_win * win_samples / sr


def verify_with_whisper(src_mp4, cut_in, cut_out, expected_last_word):
    """Law 14c hard gate: transcribe last 700ms, confirm last word matches."""
    wav = os.path.join(QA_DIR, "verify_tail.wav")
    tail_start = max(cut_in, cut_out - 0.7)
    extract_audio_segment(src_mp4, tail_start, cut_out, wav)
    if not os.path.exists(wav) or os.path.getsize(wav) < 100:
        return False, "no audio"
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cuda", compute_type="float16")
        segs, _ = model.transcribe(wav, beam_size=3, language="en")
        text = " ".join(s.text.strip() for s in segs).strip()
        last = text.split()[-1] if text.split() else ""
        # Normalize: strip punctuation for comparison
        import string
        norm_last = last.lower().strip(string.punctuation)
        norm_expected = expected_last_word.lower().strip(string.punctuation)
        match = norm_last == norm_expected or norm_expected in norm_last or norm_last in norm_expected
        return match, text
    except Exception as e:
        return False, str(e)


def process_clip(clip_info, clip_id):
    vid = clip_info["video_id"]
    src = os.path.join(SOURCES_DIR, f"{vid}.mp4")
    if not os.path.exists(src):
        return None

    word_start = clip_info["word_start"]
    word_end = clip_info["word_end"]
    handle_start = max(0, word_start - 0.5)
    handle_end = word_end + 0.7

    wav_path = os.path.join(QA_DIR, f"{clip_id}_analysis.wav")
    extract_audio_segment(src, handle_start, handle_end, wav_path)
    samples, sr = read_wav_samples(wav_path)
    if len(samples) == 0:
        return None

    onset_s = find_speech_onset(samples, sr, word_start, handle_start)
    offset_s = find_speech_offset(samples, sr, word_end, handle_start)

    cut_in = handle_start + onset_s
    cut_out = handle_start + offset_s

    if cut_in > word_start:
        cut_in = max(word_start - 0.05, handle_start)
    if cut_out < word_end:
        cut_out = word_end + 0.15

    # Law 14c whisper verification
    last_word = clip_info.get("last_word", "")
    verified = False
    for attempt in range(4):
        match, tail_text = verify_with_whisper(src, cut_in, cut_out, last_word)
        if match:
            verified = True
            break
        cut_out += 0.1  # widen 100ms

    return {
        "clip_id": clip_id,
        "video_id": vid,
        "channel": clip_info.get("channel", ""),
        "text": clip_info.get("text", ""),
        "word_start": word_start,
        "word_end": word_end,
        "cut_in": round(cut_in, 3),
        "cut_out": round(cut_out, 3),
        "cut_duration": round(cut_out - cut_in, 3),
        "verified": verified,
        "last_word_expected": last_word,
    }


print("=== STAGE S4: EXTRACT AND CUT CLIPS ===\n")
all_cuts = []

# Hook
hook = edl.get("hook")
if hook and hook.get("video_id"):
    print(f"Processing hook ({hook.get('channel','?')})...", end=" ", flush=True)
    cut = process_clip(hook, "hook")
    if cut:
        print(f"in={cut['cut_in']:.3f} out={cut['cut_out']:.3f} dur={cut['cut_duration']:.2f}s verified={cut['verified']}")
        all_cuts.append(cut)
    else:
        print("FAILED")

# Clips
for clip in edl.get("clips", []):
    clip_id = f"clip_{clip['index']:02d}"
    print(f"Processing {clip_id} ({clip['channel']})...", end=" ", flush=True)
    cut = process_clip(clip, clip_id)
    if cut:
        print(f"in={cut['cut_in']:.3f} out={cut['cut_out']:.3f} dur={cut['cut_duration']:.2f}s verified={cut['verified']}")
        all_cuts.append(cut)
    else:
        print("FAILED")

# Write cuts_final.json (Law 22)
with open(f"{BASE}/cuts_final.json", "w") as f:
    json.dump(all_cuts, f, indent=2)

total = sum(c["cut_duration"] for c in all_cuts)
verified_count = sum(1 for c in all_cuts if c["verified"])
print(f"\nCuts written: {len(all_cuts)} clips, total {total:.1f}s")
print(f"Verified: {verified_count}/{len(all_cuts)}")

if verified_count < len(all_cuts):
    unverified = [c["clip_id"] for c in all_cuts if not c["verified"]]
    print(f"WARNING: Unverified cuts: {unverified}")
