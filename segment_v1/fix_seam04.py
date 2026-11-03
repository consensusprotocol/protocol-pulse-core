#!/usr/bin/env python3
"""Fix seam_04 (clip_03->clip_04): widen clip_04 head handle, re-find onset, re-measure."""
import json, os, subprocess, numpy as np, wave, math

BASE = "/home/ultron/protocol_pulse/segment_v1"
SOURCES = os.path.join(BASE, "sources")
QA = os.path.join(BASE, "qa_v2")


def extract_wav(src_mp4, start, end, out_wav):
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(max(0, start)), "-to", str(end),
        "-i", src_mp4, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", out_wav,
    ], capture_output=True, timeout=30)


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


def db(val):
    if val <= 0:
        return -80.0
    return max(20 * math.log10(val), -80.0)


def rms_envelope(samples, sr, window_ms=10):
    win = int(sr * window_ms / 1000)
    if win == 0 or len(samples) < win:
        return np.array([]), 0
    n_win = len(samples) // win
    rms = np.zeros(n_win)
    for i in range(n_win):
        chunk = samples[i * win:(i + 1) * win]
        rms[i] = np.sqrt(np.mean(chunk ** 2))
    return rms, win


def find_onset(samples, sr, word_start_s, handle_start_s):
    rms, win = rms_envelope(samples, sr, 10)
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


def measure_seam_db(src_a, cut_out_a, src_b, cut_in_b):
    """Measure boundary jump between two clips using 200ms on each side."""
    wav_a = os.path.join(QA, "seam04_fix_a.wav")
    wav_b = os.path.join(QA, "seam04_fix_b.wav")
    extract_wav(src_a, cut_out_a - 0.2, cut_out_a, wav_a)
    extract_wav(src_b, cut_in_b, cut_in_b + 0.2, wav_b)
    sa, sra = read_wav(wav_a)
    sb, srb = read_wav(wav_b)
    if len(sa) == 0 or len(sb) == 0:
        return None
    rms_a = np.sqrt(np.mean(sa ** 2))
    rms_b = np.sqrt(np.mean(sb ** 2))
    return abs(db(rms_a) - db(rms_b))


# Load cuts
with open(os.path.join(BASE, "cuts_v2.json")) as f:
    cuts = json.load(f)

clip_03 = next(c for c in cuts if c["clip_id"] == "clip_03")
clip_04 = next(c for c in cuts if c["clip_id"] == "clip_04")

src_03 = os.path.join(SOURCES, f"{clip_03['video_id']}.mp4")
src_04 = os.path.join(SOURCES, f"{clip_04['video_id']}.mp4")

print(f"=== FIXING SEAM 04: clip_03 -> clip_04 ===\n")
print(f"  clip_03: {clip_03['video_id']} cut_out={clip_03['cut_out']}")
print(f"  clip_04: {clip_04['video_id']} cut_in={clip_04['cut_in']} word_start={clip_04['word_start']}")

initial = measure_seam_db(src_03, clip_03["cut_out"], src_04, clip_04["cut_in"])
print(f"\n  Initial measurement: {initial:.1f}dB" if initial else "\n  Initial measurement: FAILED")

# Strategy 1: Widen clip_04 head handle by 150ms steps (3 attempts)
print("\n--- Strategy 1: Widen clip_04 head handle ---")
best_jump = initial
best_cut_in = clip_04["cut_in"]
orig_handle = clip_04["handle_start"]

for attempt in range(1, 4):
    new_handle = max(0, orig_handle - 0.15 * attempt)
    # Re-extract and find onset
    wav_test = os.path.join(QA, f"seam04_s1_try{attempt}.wav")
    extract_wav(src_04, new_handle, clip_04["handle_end"], wav_test)
    samples, sr = read_wav(wav_test)
    if len(samples) == 0:
        print(f"  Try {attempt}: handle={new_handle:.3f} — audio extraction failed")
        continue
    onset_s = find_onset(samples, sr, clip_04["word_start"], new_handle)
    new_cut_in = new_handle + onset_s
    if new_cut_in > clip_04["word_start"]:
        new_cut_in = max(clip_04["word_start"] - 0.05, new_handle)

    jump = measure_seam_db(src_03, clip_03["cut_out"], src_04, new_cut_in)
    status = "PASS" if jump and jump <= 12.0 else "FAIL"
    print(f"  Try {attempt}: handle={new_handle:.3f} onset={onset_s:.3f}s cut_in={new_cut_in:.3f} -> {jump:.1f}dB {status}" if jump else f"  Try {attempt}: FAILED")
    if jump and jump < best_jump:
        best_jump = jump
        best_cut_in = new_cut_in

if best_jump <= 12.0:
    print(f"\n  FIXED via Strategy 1: cut_in={best_cut_in:.3f} jump={best_jump:.1f}dB PASS")
    clip_04["cut_in"] = round(best_cut_in, 3)
    clip_04["cut_duration"] = round(clip_04["cut_out"] - clip_04["cut_in"], 3)
else:
    # Strategy 2: Trim clip_03 tail to last-word offset + 150ms room tone
    print(f"\n--- Strategy 2: Trim clip_03 tail ---")
    new_cut_out_03 = clip_03["word_end"] + 0.15
    jump2 = measure_seam_db(src_03, new_cut_out_03, src_04, best_cut_in)
    status2 = "PASS" if jump2 and jump2 <= 12.0 else "FAIL"
    print(f"  clip_03 cut_out: {clip_03['cut_out']:.3f} -> {new_cut_out_03:.3f}, jump={jump2:.1f}dB {status2}" if jump2 else "  Measurement failed")

    if jump2 and jump2 <= 12.0:
        print(f"\n  FIXED via Strategy 2: clip_03 cut_out={new_cut_out_03:.3f} + clip_04 cut_in={best_cut_in:.3f} jump={jump2:.1f}dB PASS")
        clip_03["cut_out"] = round(new_cut_out_03, 3)
        clip_03["cut_duration"] = round(clip_03["cut_out"] - clip_03["cut_in"], 3)
        clip_04["cut_in"] = round(best_cut_in, 3)
        clip_04["cut_duration"] = round(clip_04["cut_out"] - clip_04["cut_in"], 3)
    else:
        # Strategy 2b: try combining both trims with wider clip_04 handle
        print(f"\n--- Strategy 2b: Combined trim ---")
        for attempt in range(1, 4):
            new_handle_04 = max(0, orig_handle - 0.15 * attempt)
            wav_test = os.path.join(QA, f"seam04_s2b_try{attempt}.wav")
            extract_wav(src_04, new_handle_04, clip_04["handle_end"], wav_test)
            samples, sr = read_wav(wav_test)
            if len(samples) == 0:
                continue
            onset_s = find_onset(samples, sr, clip_04["word_start"], new_handle_04)
            new_cut_in_04 = new_handle_04 + onset_s
            if new_cut_in_04 > clip_04["word_start"]:
                new_cut_in_04 = max(clip_04["word_start"] - 0.05, new_handle_04)
            jump2b = measure_seam_db(src_03, new_cut_out_03, src_04, new_cut_in_04)
            status2b = "PASS" if jump2b and jump2b <= 12.0 else "FAIL"
            print(f"  Try {attempt}: clip_03_out={new_cut_out_03:.3f} clip_04_in={new_cut_in_04:.3f} -> {jump2b:.1f}dB {status2b}" if jump2b else f"  Try {attempt}: FAILED")
            if jump2b and jump2b <= 12.0:
                clip_03["cut_out"] = round(new_cut_out_03, 3)
                clip_03["cut_duration"] = round(clip_03["cut_out"] - clip_03["cut_in"], 3)
                clip_04["cut_in"] = round(new_cut_in_04, 3)
                clip_04["cut_duration"] = round(clip_04["cut_out"] - clip_04["cut_in"], 3)
                print(f"\n  FIXED via Strategy 2b attempt {attempt}")
                break
        else:
            # Ship it flagged
            print(f"\n  FLAGGED: seam_04 could not be fixed below 12dB.")
            print(f"  Best numbers: clip_03 cut_out={clip_03['cut_out']:.3f}, clip_04 cut_in={best_cut_in:.3f}, jump={best_jump:.1f}dB")
            print(f"  Note: VO bridge sits at this seam — will be masked in final render.")
            clip_04["cut_in"] = round(best_cut_in, 3)
            clip_04["cut_duration"] = round(clip_04["cut_out"] - clip_04["cut_in"], 3)

# Update cuts file
for i, c in enumerate(cuts):
    if c["clip_id"] == "clip_03":
        cuts[i] = clip_03
    elif c["clip_id"] == "clip_04":
        cuts[i] = clip_04

with open(os.path.join(BASE, "cuts_v2.json"), "w") as f:
    json.dump(cuts, f, indent=2)

total = sum(c["cut_duration"] for c in cuts)
print(f"\nUpdated cuts_v2.json — total cut duration: {total:.1f}s")
