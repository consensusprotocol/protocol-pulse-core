#!/usr/bin/env python3
"""Stage 3a-b: Extract clips with handles, find true speech onset/offset, seam QA.
Law 14 compliant: transcript timestamps are NOT cut points."""
import json
import os
import subprocess
import numpy as np
import wave
import struct
import math

BASE = "/home/ultron/protocol_pulse/segment_v1"
EDL_FILE = os.path.join(BASE, "edl.json")
SOURCES_DIR = os.path.join(BASE, "sources")
QA_DIR = os.path.join(BASE, "qa")
os.makedirs(QA_DIR, exist_ok=True)

with open(EDL_FILE) as f:
    edl = json.load(f)


def extract_audio_segment(source_mp4, start_s, end_s, output_wav):
    """Extract audio segment as 16kHz mono PCM WAV."""
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(max(0, start_s)), "-to", str(end_s),
        "-i", source_mp4, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        output_wav,
    ], capture_output=True, timeout=30)


def read_wav_samples(wav_path):
    """Read WAV file and return numpy array of samples."""
    try:
        with wave.open(wav_path, 'rb') as wf:
            n_frames = wf.getnframes()
            if n_frames == 0:
                return np.array([], dtype=np.float32), 0
            raw = wf.readframes(n_frames)
            sr = wf.getframerate()
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            return samples, sr
    except Exception as e:
        print(f"  WAV read error: {e}")
        return np.array([], dtype=np.float32), 0


def compute_rms_envelope(samples, sr, window_ms=10):
    """Compute RMS over window_ms windows."""
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
    """Convert linear to dB, clamp to -80."""
    if val <= 0:
        return -80.0
    return max(20 * math.log10(val), -80.0)


def find_speech_onset(samples, sr, word_start_s, handle_start_s):
    """Find true speech onset: RMS > noise_floor + 12dB, walking back from word_start.
    Returns offset in seconds from start of the audio segment."""
    rms, win_samples = compute_rms_envelope(samples, sr, window_ms=10)
    if len(rms) == 0:
        return 0.0

    # Noise floor: median RMS of first 100ms
    noise_windows = max(1, int(0.1 * sr / win_samples))
    noise_floor = np.median(rms[:noise_windows]) if noise_windows <= len(rms) else np.median(rms)
    noise_db = db(noise_floor)
    threshold_db = noise_db + 12

    # Word start position in windows
    word_offset_s = word_start_s - handle_start_s
    word_win = int(word_offset_s * sr / win_samples)
    word_win = min(word_win, len(rms) - 1)

    # Walk backwards from word_start up to 400ms
    max_walk_wins = int(0.4 * sr / win_samples)
    onset_win = word_win
    for i in range(word_win, max(word_win - max_walk_wins, 0), -1):
        if db(rms[i]) < threshold_db:
            onset_win = i + 1
            break
    else:
        onset_win = max(word_win - max_walk_wins, 0)

    onset_s = onset_win * win_samples / sr
    return onset_s


def find_speech_offset(samples, sr, word_end_s, handle_start_s):
    """Find speech offset: last RMS > threshold after last word + 120ms room tone."""
    rms, win_samples = compute_rms_envelope(samples, sr, window_ms=10)
    if len(rms) == 0:
        return len(samples) / sr

    # Noise floor from last 100ms
    noise_windows = max(1, int(0.1 * sr / win_samples))
    noise_floor = np.median(rms[-noise_windows:]) if noise_windows <= len(rms) else np.median(rms)
    noise_db = db(noise_floor)
    threshold_db = noise_db + 12

    # Word end position
    word_offset_s = word_end_s - handle_start_s
    word_win = int(word_offset_s * sr / win_samples)
    word_win = min(word_win, len(rms) - 1)

    # Walk forward up to 600ms
    max_walk_wins = int(0.6 * sr / win_samples)
    offset_win = word_win
    for i in range(word_win, min(word_win + max_walk_wins, len(rms))):
        if db(rms[i]) >= threshold_db:
            offset_win = i
        else:
            break

    # Add 120ms room tone
    room_tone_wins = int(0.12 * sr / win_samples)
    offset_win = min(offset_win + room_tone_wins, len(rms) - 1)

    offset_s = offset_win * win_samples / sr
    return offset_s


def process_clip(clip_info, clip_id):
    """Process one clip: extract with handles, find onset/offset, return cut info."""
    vid = clip_info["video_id"]
    src = os.path.join(SOURCES_DIR, f"{vid}.mp4")
    if not os.path.exists(src):
        return None

    word_start = clip_info["word_start"]
    word_end = clip_info["word_end"]

    # 500ms handle before, 700ms after
    handle_start = max(0, word_start - 0.5)
    handle_end = word_end + 0.7

    # Extract audio for analysis
    wav_path = os.path.join(QA_DIR, f"{clip_id}_analysis.wav")
    extract_audio_segment(src, handle_start, handle_end, wav_path)
    samples, sr = read_wav_samples(wav_path)
    if len(samples) == 0:
        print(f"  WARNING: Empty audio for {clip_id}")
        return None

    # Find true onset and offset
    onset_s = find_speech_onset(samples, sr, word_start, handle_start)
    offset_s = find_speech_offset(samples, sr, word_end, handle_start)

    # Convert back to absolute source time
    cut_in = handle_start + onset_s
    cut_out = handle_start + offset_s

    # Ensure we don't cut inside a word
    if cut_in > word_start:
        cut_in = max(word_start - 0.05, handle_start)
    if cut_out < word_end:
        cut_out = word_end + 0.12

    return {
        "clip_id": clip_id,
        "video_id": vid,
        "word_start": word_start,
        "word_end": word_end,
        "handle_start": round(handle_start, 3),
        "handle_end": round(handle_end, 3),
        "onset_delta": round(onset_s - (word_start - handle_start), 3),
        "offset_delta": round(offset_s - (word_end - handle_start), 3),
        "cut_in": round(cut_in, 3),
        "cut_out": round(cut_out, 3),
        "cut_duration": round(cut_out - cut_in, 3),
    }


def seam_qa(cuts_list):
    """For each clip boundary, write 1.5s audio excerpt and check quality."""
    seams = []
    for i in range(len(cuts_list) - 1):
        cur = cuts_list[i]
        nxt = cuts_list[i + 1]
        if not cur or not nxt:
            continue

        seam_id = f"seam_{i+1:02d}"

        # Extract last 0.75s of current clip
        cur_src = os.path.join(SOURCES_DIR, f"{cur['video_id']}.mp4")
        cur_end_wav = os.path.join(QA_DIR, f"{seam_id}_a.wav")
        extract_audio_segment(cur_src, cur["cut_out"] - 0.75, cur["cut_out"], cur_end_wav)

        # Extract first 0.75s of next clip
        nxt_src = os.path.join(SOURCES_DIR, f"{nxt['video_id']}.mp4")
        nxt_start_wav = os.path.join(QA_DIR, f"{seam_id}_b.wav")
        extract_audio_segment(nxt_src, nxt["cut_in"], nxt["cut_in"] + 0.75, nxt_start_wav)

        # Concatenate for the seam excerpt
        seam_wav = os.path.join(QA_DIR, f"{seam_id}.wav")
        subprocess.run([
            "ffmpeg", "-y",
            "-i", cur_end_wav, "-i", nxt_start_wav,
            "-filter_complex", "[0][1]concat=n=2:v=0:a=1",
            "-c:a", "pcm_s16le", "-ar", "16000", seam_wav,
        ], capture_output=True, timeout=15)

        # Analyze: peak in first/last 50ms
        samples_a, sr_a = read_wav_samples(cur_end_wav)
        samples_b, sr_b = read_wav_samples(nxt_start_wav)

        result = {"seam_id": seam_id, "between": [cur["clip_id"], nxt["clip_id"]]}

        if len(samples_a) > 0:
            last_50ms = samples_a[-int(sr_a * 0.05):] if len(samples_a) > int(sr_a * 0.05) else samples_a
            result["peak_end_50ms_db"] = round(db(np.max(np.abs(last_50ms))), 1)
        if len(samples_b) > 0:
            first_50ms = samples_b[:int(sr_b * 0.05)] if len(samples_b) > int(sr_b * 0.05) else samples_b
            result["peak_start_50ms_db"] = round(db(np.max(np.abs(first_50ms))), 1)

        # Check for hard step (>6dB jump between adjacent 10ms windows at boundary)
        if len(samples_a) > 0 and len(samples_b) > 0:
            rms_a, _ = compute_rms_envelope(samples_a, sr_a, 10)
            rms_b, _ = compute_rms_envelope(samples_b, sr_b, 10)
            if len(rms_a) > 0 and len(rms_b) > 0:
                jump_db = abs(db(rms_a[-1]) - db(rms_b[0]))
                result["boundary_jump_db"] = round(jump_db, 1)
                result["pass"] = jump_db <= 6.0
            else:
                result["pass"] = True
                result["note"] = "Could not compute boundary jump"
        else:
            result["pass"] = False
            result["note"] = "Missing audio"

        result["seam_wav"] = seam_wav
        seams.append(result)

    return seams


# === MAIN ===
if __name__ == "__main__":
    print("=== STAGE 3a: EXTRACT AND CUT CLIPS ===\n")

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
                  f"onset_delta={cut['onset_delta']:+.3f}s offset_delta={cut['offset_delta']:+.3f}s")
            all_cuts.append(cut)
        else:
            print("FAILED")

    # Write cuts.json
    with open(os.path.join(BASE, "cuts.json"), "w") as f:
        json.dump(all_cuts, f, indent=2)
    print(f"\nCuts written: {len(all_cuts)} clips")

    total = sum(c["cut_duration"] for c in all_cuts)
    print(f"Total cut duration: {total:.1f}s")

    # Stage 3b: Seam QA
    print("\n=== STAGE 3b: SEAM QA ===\n")
    seams = seam_qa(all_cuts)

    pass_count = sum(1 for s in seams if s.get("pass"))
    fail_count = len(seams) - pass_count
    print(f"\nSeam results: {pass_count} PASS, {fail_count} FAIL out of {len(seams)}")

    for s in seams:
        status = "PASS" if s.get("pass") else "FAIL"
        jump = s.get("boundary_jump_db", "?")
        print(f"  {s['seam_id']}: {status} (jump={jump}dB) between {s['between']}")

    # Handle FAIL seams: widen handle and re-measure up to 3 iterations
    for attempt in range(3):
        fails = [s for s in seams if not s.get("pass")]
        if not fails:
            break
        print(f"\n  Retry attempt {attempt+1} for {len(fails)} failed seams...")
        for s in fails:
            # Find the clips involved
            clip_ids = s["between"]
            for cut in all_cuts:
                if cut["clip_id"] in clip_ids:
                    # Widen handles by 200ms
                    cut["cut_in"] = max(0, cut["cut_in"] - 0.2)
                    cut["cut_out"] = cut["cut_out"] + 0.2
                    cut["cut_duration"] = round(cut["cut_out"] - cut["cut_in"], 3)
        seams = seam_qa(all_cuts)
        pass_count = sum(1 for s in seams if s.get("pass"))
        print(f"  After retry: {pass_count} PASS out of {len(seams)}")

    # Write final seams.json
    with open(os.path.join(BASE, "seams.json"), "w") as f:
        json.dump(seams, f, indent=2)

    # Update cuts.json with final values
    with open(os.path.join(BASE, "cuts.json"), "w") as f:
        json.dump(all_cuts, f, indent=2)

    print(f"\nSeams written to {BASE}/seams.json")
    print(f"Final cuts written to {BASE}/cuts.json")
