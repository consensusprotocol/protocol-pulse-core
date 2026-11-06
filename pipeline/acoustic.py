#!/usr/bin/env python3
"""pipeline/acoustic.py — Acoustic cut-point analysis (M19).

RMS envelope at 10 ms hop on source audio. Detects speech offset/onset
to set precise cut_out/cut_in points independent of whisper timestamps.

Usage:
    from pipeline.acoustic import compute_acoustic_cut_out, compute_acoustic_cut_in

Key rules (M19):
  - cut_out = min(offset + 0.30, onset - 0.06)
  - onset - offset < 0.12 s → unsafe boundary (R9 fails)
  - 30 ms fade-out at every cut-out, 20 ms fade-in at every cut-in
"""
import os
import struct
import subprocess
import wave

import numpy as np


# ── Constants ──
HOP_MS = 10        # RMS envelope hop size in milliseconds
ONSET_THRESH_DB = -30.0   # absolute dBFS threshold for onset detection
BED_ONSET_DB = 15.0       # dB above bed for relative onset detection
FADE_OUT_MS = 30   # fade-out at cut-out
FADE_IN_MS = 20    # fade-in at cut-in
MIN_GAP_S = 0.12   # minimum gap between offset and onset for safe boundary


def _extract_audio_mono(mp4_path, start_s, duration_s, out_wav, sr=16000):
    """Extract mono audio from video at given position."""
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(start_s), "-t", str(duration_s),
        "-i", mp4_path, "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", out_wav,
    ], capture_output=True, timeout=30, check=True)
    return out_wav


def _load_wav_samples(wav_path):
    """Load mono WAV and return (samples_float, sample_rate)."""
    with wave.open(wav_path, 'rb') as wf:
        sr = wf.getframerate()
        n = wf.getnframes()
        nc = wf.getnchannels()
        raw = wf.readframes(n)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    if nc > 1:
        samples = samples[::nc]
    # Normalize to [-1, 1]
    samples = samples / 32768.0
    return samples, sr


def rms_envelope(samples, sr, hop_ms=HOP_MS):
    """Compute RMS envelope at `hop_ms` hop. Returns (rms_db, times)."""
    hop = int(sr * hop_ms / 1000)
    n_frames = len(samples) // hop
    rms_db = np.full(n_frames, -80.0)
    times = np.arange(n_frames) * hop_ms / 1000.0

    for i in range(n_frames):
        start = i * hop
        end = min(start + hop, len(samples))
        chunk = samples[start:end]
        rms = np.sqrt(np.mean(chunk ** 2)) if len(chunk) > 0 else 1e-10
        rms_db[i] = 20 * np.log10(max(rms, 1e-10))

    return rms_db, times


def find_speech_offset(rms_db, times, last_word_end_approx):
    """Find the acoustic offset (silence start) after the last word.
    Looks for the point where RMS drops below -30 dBFS after the word end."""
    # Start searching from the approximate word end
    start_idx = np.searchsorted(times, last_word_end_approx - 0.05)
    end_idx = min(len(rms_db), np.searchsorted(times, last_word_end_approx + 0.5))

    # Find where signal drops below threshold
    for i in range(start_idx, end_idx):
        if rms_db[i] < ONSET_THRESH_DB:
            return times[i]

    # If no clear drop, use word_end + small offset
    return last_word_end_approx + 0.05


def find_speech_onset(rms_db, times, search_start, bed_rms_db=None):
    """Find the next speech onset after search_start.
    Returns onset time or None if no onset found in window."""
    start_idx = np.searchsorted(times, search_start)
    end_idx = min(len(rms_db), np.searchsorted(times, search_start + 1.0))

    # Compute threshold: absolute or relative to bed
    abs_thresh = 10 ** (ONSET_THRESH_DB / 20)
    if bed_rms_db is not None:
        rel_thresh_db = bed_rms_db + BED_ONSET_DB
    else:
        rel_thresh_db = ONSET_THRESH_DB

    for i in range(start_idx, end_idx):
        if rms_db[i] > max(ONSET_THRESH_DB, rel_thresh_db):
            return times[i]

    return None  # No onset in window


def compute_acoustic_cut_out(source_mp4, whisper_word_end, window_s=1.5):
    """Compute the acoustic cut-out point for a clip from source video.

    Args:
        source_mp4: path to source video
        whisper_word_end: whisper-reported end time of last word
        window_s: audio window to analyze around the word end

    Returns:
        dict with:
            cut_out: float — the acoustic cut-out timestamp in source
            offset: float — speech offset time
            onset: float or None — next speech onset time
            gap: float — gap between offset and onset (inf if no onset)
            safe: bool — whether the boundary is safe (gap >= 0.12s)
            bed_db: float — estimated bed noise level
    """
    import tempfile
    # Extract audio window around the word end
    extract_start = max(0, whisper_word_end - 0.5)
    extract_dur = window_s + 0.5
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = tmp.name

    try:
        _extract_audio_mono(source_mp4, extract_start, extract_dur, tmp_wav)
        samples, sr = _load_wav_samples(tmp_wav)
        rms_db, times = rms_envelope(samples, sr)

        # Adjust times to source-absolute
        times = times + extract_start

        # Estimate bed noise from the quietest 20% of the window
        sorted_rms = np.sort(rms_db)
        bed_db = float(np.median(sorted_rms[:max(1, len(sorted_rms) // 5)]))

        # Find offset (silence after last word)
        offset = find_speech_offset(rms_db, times, whisper_word_end)

        # Find onset (next speech start)
        onset = find_speech_onset(rms_db, times, offset, bed_db)

        # Compute gap
        if onset is not None:
            gap = onset - offset
        else:
            gap = float('inf')

        safe = gap >= MIN_GAP_S

        # Compute cut_out per M19
        if onset is not None:
            cut_out = min(offset + 0.30, onset - 0.06)
        else:
            cut_out = offset + 0.30

        return {
            "cut_out": round(cut_out, 3),
            "offset": round(offset, 3),
            "onset": round(onset, 3) if onset is not None else None,
            "gap": round(gap, 3) if gap != float('inf') else float('inf'),
            "safe": safe,
            "bed_db": round(bed_db, 1),
        }
    finally:
        if os.path.exists(tmp_wav):
            os.unlink(tmp_wav)


def measure_output_tail(output_mp4, clip_end_time, duration_ms=120):
    """Gate G3c: measure the last `duration_ms` ms of a clip in the output.

    Returns:
        dict with:
            rms_db: float — RMS of the tail region in dBFS
            max_db: float — peak dBFS in the tail
            has_onset: bool — whether an onset is detected
            pass_absolute: bool — tail < -35 dBFS
    """
    import tempfile
    tail_start = clip_end_time - duration_ms / 1000.0
    tail_dur = duration_ms / 1000.0

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = tmp.name

    try:
        _extract_audio_mono(output_mp4, tail_start, tail_dur, tmp_wav)
        samples, sr = _load_wav_samples(tmp_wav)
        rms_db_arr, times = rms_envelope(samples, sr)

        if len(rms_db_arr) == 0:
            return {"rms_db": -80.0, "max_db": -80.0, "has_onset": False, "pass_absolute": True}

        avg_rms_db = float(np.mean(rms_db_arr))
        max_db = float(np.max(rms_db_arr))

        # Check for onset: any frame > -30 dBFS after a frame < -35 dBFS
        has_onset = False
        for i in range(1, len(rms_db_arr)):
            if rms_db_arr[i - 1] < -35.0 and rms_db_arr[i] > -30.0:
                has_onset = True
                break

        return {
            "rms_db": round(avg_rms_db, 1),
            "max_db": round(max_db, 1),
            "has_onset": has_onset,
            "pass_absolute": max_db < -35.0,
        }
    finally:
        if os.path.exists(tmp_wav):
            os.unlink(tmp_wav)


def apply_fades(input_mp4, output_mp4, cut_in_fade_ms=FADE_IN_MS, cut_out_fade_ms=FADE_OUT_MS):
    """Apply fade-in and fade-out to a clip's audio."""
    fade_in_s = cut_in_fade_ms / 1000.0
    fade_out_s = cut_out_fade_ms / 1000.0

    # Get duration for fade-out position
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", input_mp4],
        capture_output=True, text=True, timeout=10, check=True,
    )
    dur = float(r.stdout.strip())
    fade_out_start = max(0, dur - fade_out_s)

    partial = output_mp4 + ".partial"
    subprocess.run([
        "ffmpeg", "-y", "-i", input_mp4,
        "-af", f"afade=t=in:d={fade_in_s},afade=t=out:st={fade_out_start}:d={fade_out_s}",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", partial,
    ], capture_output=True, timeout=120, check=True)
    os.replace(partial, output_mp4)
