#!/usr/bin/env python3
"""pipeline/acoustic.py — Acoustic cut-point analysis (M19).

RMS envelope at 10 ms hop on source audio. Detects speech offset/onset
to set precise cut_out/cut_in points independent of whisper timestamps.

Usage:
    from pipeline.acoustic import compute_acoustic_cut_out, compute_acoustic_cut_in

Key rules (M19 / M19a):
  - M19a valley rule: cut_out = centre of first qualifying RMS valley
    after whisper_word_end + 0.10. Valley must be >= 12 dB below speech
    median AND >= 40 ms wide.
  - Fallback (no valley): cut_out = min(offset + 0.30, onset - 0.06)
  - onset - offset < 0.12 s → unsafe boundary (R9 fails)
  - 30 ms fade-out at every cut-out, 20 ms fade-in at every cut-in
"""
import os
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


VALLEY_DEPTH_DB = 12.0   # M19a: valley must be >= 12 dB below speech median
VALLEY_MIN_WIDTH_MS = 60  # M19a: valley must be >= 60 ms wide (rejects stop-consonant closures)
VALLEY_WINDOW_MS = 30     # M19a: smoothing window for valley search


def _smoothed_rms(rms_db, window_frames):
    """Sliding-window mean of rms_db (in dB). Returns same-length array."""
    if window_frames < 2 or len(rms_db) < window_frames:
        return rms_db.copy()
    kernel = np.ones(window_frames) / window_frames
    # Pad to keep length
    padded = np.pad(rms_db, (window_frames // 2, window_frames - 1 - window_frames // 2), mode='edge')
    return np.convolve(padded, kernel, mode='valid')[:len(rms_db)]


ACOUSTIC_OFFSET_DB = 6.0  # acoustic offset: last frame within 6 dB of speech median


def _find_acoustic_offset(rms_db, times, whisper_word_end, speech_median_db,
                           smoothed=None, hop_ms=HOP_MS):
    """Find the acoustic offset: last time the smoothed RMS is within 6 dB of
    the speech median, searched after whisper_word_end - 0.05.

    Per addendum: this is the last frame where speech energy is still at word
    level, catching cases where whisper under-reports the word end.

    Scans from whisper_word_end - 0.05 to whisper_word_end + 0.5. Returns the
    time of the last frame in that window where smoothed RMS >= speech_median - 6 dB,
    constrained to not extend past the next inter-word valley (a qualifying
    gap >= 60ms at the 12 dB valley depth threshold).

    Returns acoustic_offset time (float).
    """
    if smoothed is None:
        window_frames = max(1, VALLEY_WINDOW_MS // hop_ms)
        smoothed = _smoothed_rms(rms_db, window_frames)

    # Find the last frame within 6 dB of speech median, but do not extend
    # past a gap where RAW rms drops below the 6 dB threshold for >= 80ms.
    # This distinguishes intra-word gaps (stop consonants, typically < 80ms
    # even at 6 dB) from inter-word valleys (typically > 80ms at 6 dB).
    search_start = whisper_word_end - 0.05
    start_idx = int(np.searchsorted(times, search_start))
    end_limit = int(min(len(smoothed), np.searchsorted(times, whisper_word_end + 0.5)))

    offset_threshold = speech_median_db - ACOUSTIC_OFFSET_DB
    gap_boundary_frames = 8  # 80ms at 10ms hop — gap boundary for offset scan

    # First: find the boundary — first gap >= 80ms at 6 dB in raw RMS
    boundary_idx = end_limit
    gap_count = 0
    for i in range(start_idx, end_limit):
        if rms_db[i] < offset_threshold:
            gap_count += 1
            if gap_count >= gap_boundary_frames:
                boundary_idx = i - gap_boundary_frames + 1
                break
        else:
            gap_count = 0

    # Then: last frame within 6 dB before that boundary
    last_above_idx = start_idx
    for i in range(start_idx, boundary_idx):
        if smoothed[i] >= offset_threshold:
            last_above_idx = i

    return float(times[min(last_above_idx, len(times) - 1)])


RESUME_MIN_MS = 100  # speech resumption threshold for intra-word gap detection


def find_valley(rms_db, times, search_start, search_end, speech_median_db, hop_ms=HOP_MS):
    """M19a: find the FIRST qualifying RMS valley in [search_start, search_end].

    A valley is a contiguous run of frames where the smoothed RMS is below
    speech_median_db - VALLEY_DEPTH_DB. The valley must be >= VALLEY_MIN_WIDTH_MS wide
    (60 ms — rejects stop-consonant closures which are typically 30-40 ms).

    Returns the FIRST qualifying valley after the search_start.

    Returns:
        dict with centre, end, depth_db, width_ms; or None if no valid valley.
    """
    window_frames = max(1, VALLEY_WINDOW_MS // hop_ms)
    smoothed = _smoothed_rms(rms_db, window_frames)

    start_idx = int(np.searchsorted(times, search_start))
    end_idx = int(min(len(smoothed), np.searchsorted(times, search_end)))

    threshold = speech_median_db - VALLEY_DEPTH_DB

    # Return FIRST qualifying valley
    i = start_idx
    while i < end_idx:
        if smoothed[i] < threshold:
            j = i
            while j < end_idx and smoothed[j] < threshold:
                j += 1
            width_ms = (j - i) * hop_ms
            if width_ms >= VALLEY_MIN_WIDTH_MS:
                valley_slice = smoothed[i:j]
                deepest_idx = i + int(np.argmin(valley_slice))
                depth_db = speech_median_db - float(smoothed[deepest_idx])
                centre_idx = (i + j) // 2
                centre_time = float(times[centre_idx]) if centre_idx < len(times) else float(times[-1])
                end_idx_v = min(j, len(times) - 1)
                end_time = float(times[end_idx_v])
                return {
                    "centre": round(centre_time, 3),
                    "end": round(end_time, 3),
                    "depth_db": round(depth_db, 1),
                    "width_ms": round(width_ms, 1),
                }
            i = j
        else:
            i += 1

    return None


ONSET_SUSTAIN_FRAMES = 5  # M19a: onset must be sustained >= 5 frames (50ms) above threshold


class UnsafeBoundaryError(RuntimeError):
    """Raised when acoustic cut-out fails safety assertions."""
    pass


def compute_acoustic_cut_out(source_mp4, whisper_word_end, window_s=1.5):
    """M19a: Compute the acoustic cut-out point using the valley rule.

    Algorithm:
      1. Acoustic offset = last time smoothed RMS is within 6 dB of speech
         median, searched after whisper_word_end - 0.05.
      2. Find next sustained speech onset after acoustic offset.
      3. Search for FIRST qualifying valley >= 60 ms in [acoustic_offset, onset].
      4. Cut at valley END, 30 ms fade.
      5. Assert: cut_out >= acoustic_offset AND (onset is None OR cut_out <= onset - 0.060).
         Raises UnsafeBoundaryError if either fails.

    Args:
        source_mp4: path to source video
        whisper_word_end: whisper-reported end time of last word
        window_s: audio window to analyze around the word end

    Returns:
        dict with cut_out, acoustic_offset, valley, onset, speech_median_db, bed_db.

    Raises:
        UnsafeBoundaryError: if no valid valley or safety assertions fail.
    """
    import tempfile
    extract_start = max(0, whisper_word_end - 2.0)
    extract_dur = window_s + 2.0
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = tmp.name

    try:
        _extract_audio_mono(source_mp4, extract_start, extract_dur, tmp_wav)
        samples, sr = _load_wav_samples(tmp_wav)
        rms_db, times = rms_envelope(samples, sr)

        # Adjust times to source-absolute
        times = times + extract_start

        # Precompute smoothed RMS for offset + valley
        window_frames = max(1, VALLEY_WINDOW_MS // HOP_MS)
        smoothed = _smoothed_rms(rms_db, window_frames)

        # Bed noise from quietest 20%
        sorted_rms = np.sort(rms_db)
        bed_db = float(np.median(sorted_rms[:max(1, len(sorted_rms) // 5)]))

        # Speech median: median RMS of last 2s before whisper_word_end
        speech_start_idx = int(np.searchsorted(times, whisper_word_end - 2.0))
        speech_end_idx = int(np.searchsorted(times, whisper_word_end))
        if speech_end_idx > speech_start_idx:
            speech_median_db = float(np.median(rms_db[speech_start_idx:speech_end_idx]))
        else:
            speech_median_db = -20.0

        # Step 1: Acoustic offset (using smoothed RMS, within 6 dB)
        acoustic_offset = _find_acoustic_offset(
            rms_db, times, whisper_word_end, speech_median_db, smoothed=smoothed)

        # Step 2: FIRST qualifying valley after acoustic offset
        valley_search_end = whisper_word_end + 1.5
        valley = find_valley(rms_db, times, acoustic_offset, valley_search_end,
                             speech_median_db)

        if valley is None:
            raise UnsafeBoundaryError(
                f"No qualifying valley found after acoustic_offset={acoustic_offset:.3f} "
                f"(whisper_word_end={whisper_word_end:.3f})")

        # Step 3: Sustained onset AFTER the valley (next word start)
        onset_thresh = max(bed_db + BED_ONSET_DB, speech_median_db - 6.0)
        onset = None
        onset_search_start = int(np.searchsorted(times, valley["end"]))
        onset_search_end = int(min(len(rms_db), np.searchsorted(times, whisper_word_end + 1.5)))
        for i in range(onset_search_start, onset_search_end):
            if rms_db[i] > onset_thresh:
                sustained = True
                for k in range(1, ONSET_SUSTAIN_FRAMES):
                    if i + k >= len(rms_db) or rms_db[i + k] < onset_thresh:
                        sustained = False
                        break
                if sustained:
                    onset = float(times[i])
                    break

        # Step 4: Cut at valley END, clamped to onset - 60ms if needed
        cut_out = valley["end"]
        if onset is not None and cut_out > onset - 0.060:
            cut_out = onset - 0.060

        # Step 5: Safety assertions — raise on failure, no fallback
        if cut_out < acoustic_offset:
            raise UnsafeBoundaryError(
                f"cut_out={cut_out:.3f} < acoustic_offset={acoustic_offset:.3f}")

        return {
            "cut_out": round(cut_out, 3),
            "safe": True,
            "acoustic_offset": round(acoustic_offset, 3),
            "valley": valley,
            "onset": round(onset, 3) if onset is not None else None,
            "speech_median_db": round(speech_median_db, 1),
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

    # R2-21: Use .mp4 extension (not .partial) so FFmpeg auto-detects muxer
    partial = output_mp4 + ".tmp.mp4"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_mp4,
            "-af", f"afade=t=in:d={fade_in_s},afade=t=out:st={fade_out_start}:d={fade_out_s}",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", partial,
        ], capture_output=True, timeout=120, check=True)
        os.replace(partial, output_mp4)
    except Exception:
        if os.path.exists(partial):
            os.unlink(partial)
        raise
