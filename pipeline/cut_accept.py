#!/usr/bin/env python3
"""pipeline/cut_accept.py — fresh-topic cut acceptance (generalization C).

No cut is accepted merely because the cutter found an energy valley.

Checks per cut (all must pass; any failure = HOLD before render, no auto-widen):
  verified   cut.py must have produced verified=true (its fallback is never accepted)
  OUT pause  cut_out must sit in a genuine pause: a quiet run (>= QUIET dB below the
             clip's speech median) at least MIN_PAUSE wide, with at least MIN_GAP of
             that pause still ahead of the cut. The cut may sit at most OUT_DECAY_TOL
             before the pause starts, and only if the audio between the cut and the
             pause never re-rises to speech level (it is the last word's decay).
             -> rejects intra-word closures/dips (9.13 'thinks', 249.37 'magnitude'),
                cuts that touch the next word (249.63 one-time exception, 636.78),
                and cuts placed after a following word (1012.13 'It's').
  IN speech  cut_in must not sit inside continuous speech: the 100 ms before it must
             contain at least one frame >= LOUD dB below the speech median
             (skipped at file start). -> rejects 997.25 'themselves'.
  Edge words (on the PREPARED clip, Law 14c): whisper of the first/last EDGE_S seconds
             must yield the EDL first_word / last_word as the first / last word.

Acoustic thresholds are calibrated on the v2f reference (see test_fresh.py fixtures).
"""
import json
import os
import re
import subprocess

import numpy as np

SR = 16000
HOP_S = 0.010
QUIET_BELOW_MEDIAN_DB = 25.0
LOUD_BELOW_MEDIAN_DB = 12.0
MIN_PAUSE_S = 0.080
MIN_GAP_AFTER_OUT_S = 0.060
OUT_DECAY_TOL_S = 0.030
IN_LOOKBACK_S = 0.100
EDGE_S = 3.0
EPS = 1e-6


def envelope(src, t0, t1):
    """10 ms RMS envelope (dBFS) of mono 16 kHz audio in [t0, t1] of src."""
    t0 = max(0.0, t0)
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", src, "-t", f"{t1 - t0:.3f}",
         "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True, timeout=120)
    x = np.frombuffer(r.stdout, np.float32)
    h = int(SR * HOP_S)
    n = len(x) // h
    if n == 0:
        raise RuntimeError(f"no audio decoded from {src} [{t0:.3f},{t1:.3f}]")
    rms = np.sqrt(np.mean(x[:n * h].reshape(n, h) ** 2, axis=1)) + 1e-9
    return t0 + np.arange(n) * HOP_S, 20 * np.log10(rms)


def speech_median_db(t, db, cut_in, cut_out):
    inside = (t >= cut_in) & (t < cut_out)
    seg = db[inside]
    if len(seg) < 10:
        raise RuntimeError("clip too short for speech median")
    return float(np.median(seg[seg > np.percentile(seg, 30)]))


def _quiet_runs(t, quiet_mask):
    """Contiguous quiet runs as (start_t, end_t); end_t = first non-quiet frame time
    (or window end)."""
    runs = []
    i, n = 0, len(quiet_mask)
    while i < n:
        if quiet_mask[i]:
            j = i
            while j < n and quiet_mask[j]:
                j += 1
            end_t = t[j] if j < n else t[-1] + HOP_S
            runs.append((float(t[i]), float(end_t)))
            i = j
        else:
            i += 1
    return runs


def check_cut_out(t, db, cut_out, med):
    quiet = med - QUIET_BELOW_MEDIAN_DB
    loud = med - LOUD_BELOW_MEDIAN_DB
    runs = [r for r in _quiet_runs(t, db < quiet) if r[1] - r[0] >= MIN_PAUSE_S - EPS]
    for start, end in runs:
        if start - OUT_DECAY_TOL_S - EPS <= cut_out <= end - MIN_GAP_AFTER_OUT_S + EPS:
            if cut_out < start:
                between = db[(t >= cut_out - EPS) & (t < start - EPS)]
                if len(between) and between.max() >= loud:
                    continue
            return True, {"pause_start": round(start, 3), "pause_end": round(end, 3),
                          "gap_after_ms": round((end - cut_out) * 1000),
                          "quiet_db": round(quiet, 1)}
    near = [r for r in runs if r[1] > cut_out - 0.5 and r[0] < cut_out + 0.5]
    return False, {"reason": "cut_out not inside a genuine pause with >=60 ms ahead",
                   "quiet_db": round(quiet, 1),
                   "nearby_pauses": [(round(a, 3), round(b, 3)) for a, b in near]}


def check_cut_in(t, db, cut_in, med):
    loud = med - LOUD_BELOW_MEDIAN_DB
    if cut_in < IN_LOOKBACK_S:
        return True, {"note": "cut_in at file start"}
    win = db[(t >= cut_in - IN_LOOKBACK_S - EPS) & (t < cut_in - EPS)]
    if len(win) == 0:
        return False, {"reason": "no audio before cut_in"}
    ok = bool(win.min() < loud)
    d = {"lookback_min_db": round(float(win.min()), 1), "loud_db": round(loud, 1)}
    if not ok:
        d["reason"] = "cut_in inside continuous speech (no boundary dip in prior 100 ms)"
    return ok, d


def check_cut_acoustics(source_path, cut_in, cut_out):
    """Returns (ok, details) for the OUT pause and IN speech checks on the source."""
    t, db = envelope(source_path, cut_in - 1.0, cut_out + 1.0)
    med = speech_median_db(t, db, cut_in, cut_out)
    out_ok, out_d = check_cut_out(t, db, cut_out, med)
    in_ok, in_d = check_cut_in(t, db, cut_in, med)
    return out_ok and in_ok, {"speech_median_db": round(med, 1),
                              "out": {"pass": out_ok, **out_d},
                              "in": {"pass": in_ok, **in_d}}


# ── Law 14c edge-word check on the prepared clip ──

def norm_word(w):
    """A word in the pipeline's one canonical form (pipeline/canon.py), spaces removed."""
    import canon
    return "".join(canon.canon_tokens(w))


def words_match(heard, expected):
    a, b = norm_word(heard), norm_word(expected)
    if not a or not b:
        return False
    if a == b:
        return True
    # whisper sometimes splits/truncates differently ("pris" vs "prison"):
    # accept a prefix relation only when both are >= 3 chars.
    return len(a) >= 3 and len(b) >= 3 and (a.startswith(b) or b.startswith(a))


def spoken_tokens(words):
    """Whisper's words in the one canonical form, spoken order (pipeline/canon.py): '$40 trillion.' ->
    40000000000000 dollars ; '5%' -> 5 percent."""
    import canon
    return canon.canon_tokens(" ".join(words))


def _model():
    """The process's one large-v3 (L-r: gpu0.whisper loads it through swap_to; any later swap deletes it)."""
    import gpu0
    return gpu0.whisper("large-v3")


def _whisper_words(wav_path):
    segs, _ = _model().transcribe(wav_path, language="en", beam_size=5,
                                  word_timestamps=True, vad_filter=False,
                                  condition_on_previous_text=False)
    out = []
    for s in segs:
        for w in (s.words or []):
            out.append({"word": w.word.strip(), "start": round(w.start, 3),
                        "end": round(w.end, 3)})
    return out


def check_edge_words(clip_mp4, first_word, last_word, work_dir, label):
    """Whisper the first and last EDGE_S seconds of the prepared clip."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", clip_mp4], capture_output=True, text=True,
                       check=True, timeout=30)
    dur = float(r.stdout.strip())
    edge = min(EDGE_S, dur)
    head = os.path.join(work_dir, f"edge_{label}_head.wav")
    tail = os.path.join(work_dir, f"edge_{label}_tail.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip_mp4, "-t", f"{edge:.3f}",
                    "-ac", "1", "-ar", "16000", head], check=True, timeout=60)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, dur - edge):.3f}",
                    "-i", clip_mp4, "-ac", "1", "-ar", "16000", tail], check=True, timeout=60)
    hw, tw = _whisper_words(head), _whisper_words(tail)
    hs = spoken_tokens([w["word"] for w in hw])
    ts = spoken_tokens([w["word"] for w in tw])
    heard_first = hs[0] if hs else ""
    heard_last = ts[-1] if ts else ""
    first_ok = words_match(heard_first, first_word)
    last_ok = words_match(heard_last, last_word)
    return first_ok and last_ok, {
        "expected_first": first_word, "heard_first": heard_first, "first_pass": first_ok,
        "expected_last": last_word, "heard_last": heard_last, "last_pass": last_ok,
        "head_words": [w["word"] for w in hw[:6]],
        "tail_words": [w["word"] for w in tw[-6:]],
    }
