#!/usr/bin/env python3
"""pipeline/clip_contract.py — prepared-clip contract (generalization D).

Enforced on every qa/final_<clip>.mp4 BEFORE shout-out and renders:
  1920x1080, square pixels, 24 fps constant (r_frame_rate == avg_frame_rate == 24/1),
  48 kHz stereo audio, container/video/audio durations within one frame (1/24 s) of
  the cut duration, and the expected 20 ms fade-in / 30 ms fade-out present in the
  audio envelope (edge level well below the level just inside the fade, or a
  genuinely silent edge, which is recorded as such).
"""
import json
import subprocess

import numpy as np

WIDTH, HEIGHT, FPS, SR, CHANNELS = 1920, 1080, 24, 48000, 2
FRAME_S = 1.0 / FPS
FADE_EDGE_MS = 5          # measured edge window
FADE_DROP_DB = 9.0        # edge must be >= this far below the inside reference
SILENT_EDGE_DBFS = -60.0  # an already-silent edge cannot show a fade; recorded
MAX_PAD_MS = 50           # max exact-zero codec padding skipped at each end


def _probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                        "-of", "json", path], capture_output=True, text=True,
                       check=True, timeout=30)
    return json.loads(r.stdout)


def _db(x):
    return 20 * np.log10(np.sqrt(np.mean(x.astype(np.float64) ** 2)) + 1e-9)


def fade_levels(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR),
                        "-f", "f32le", "-"], capture_output=True, check=True, timeout=120)
    x = np.frombuffer(r.stdout, np.float32)
    ms = SR // 1000
    # AAC priming/padding can leave exact digital zeros at either end; those are
    # codec artefacts, not a fade. Skip up to MAX_PAD_MS of them before measuring.
    nz = np.flatnonzero(np.abs(x) > 1e-7)
    if len(nz) == 0:
        return -180.0, -180.0, -180.0, -180.0, 0, 0
    lead = min(int(nz[0]), MAX_PAD_MS * ms)
    trail = min(len(x) - 1 - int(nz[-1]), MAX_PAD_MS * ms)
    x = x[lead:len(x) - trail]
    e = FADE_EDGE_MS * ms
    head_edge, head_ref = _db(x[:e]), _db(x[25 * ms:45 * ms])
    tail_edge, tail_ref = _db(x[-e:]), _db(x[-55 * ms:-35 * ms])
    return head_edge, head_ref, tail_edge, tail_ref, lead / ms, trail / ms


def _fade_ok(edge, ref):
    if edge <= SILENT_EDGE_DBFS:
        return True, "silent-edge"
    return edge <= ref - FADE_DROP_DB, "faded" if edge <= ref - FADE_DROP_DB else "NOT faded"


def check_clip(path, expected_duration):
    """Returns (ok, details)."""
    p = _probe(path)
    v = [s for s in p["streams"] if s["codec_type"] == "video"]
    a = [s for s in p["streams"] if s["codec_type"] == "audio"]
    errors = []
    d = {"file": path, "expected_duration": round(expected_duration, 3)}
    if len(v) != 1 or len(a) != 1:
        return False, {**d, "errors": [f"streams video={len(v)} audio={len(a)}"]}
    v, a = v[0], a[0]
    d.update(width=v["width"], height=v["height"], r_frame_rate=v["r_frame_rate"],
             avg_frame_rate=v["avg_frame_rate"], sar=v.get("sample_aspect_ratio", "1:1"),
             sample_rate=int(a["sample_rate"]), channels=int(a["channels"]))
    if (v["width"], v["height"]) != (WIDTH, HEIGHT):
        errors.append(f"resolution {v['width']}x{v['height']}")
    if d["sar"] not in ("1:1", "0:1"):
        errors.append(f"sar {d['sar']}")
    if v["r_frame_rate"] != f"{FPS}/1" or v["avg_frame_rate"] != f"{FPS}/1":
        errors.append(f"fps r={v['r_frame_rate']} avg={v['avg_frame_rate']}")
    if d["sample_rate"] != SR or d["channels"] != CHANNELS:
        errors.append(f"audio {d['sample_rate']}Hz/{d['channels']}ch")
    durs = {"container": float(p["format"]["duration"]),
            "video": float(v.get("duration", 0)), "audio": float(a.get("duration", 0))}
    d["durations"] = {k: round(x, 4) for k, x in durs.items()}
    for k, x in durs.items():
        if abs(x - expected_duration) > FRAME_S + 1e-6:
            errors.append(f"{k} duration {x:.4f} vs cut {expected_duration:.4f} "
                          f"(>|{FRAME_S * 1000:.1f} ms|)")
    he, hr, te, tr, lead_ms, trail_ms = fade_levels(path)
    hin_ok, hin = _fade_ok(he, hr)
    tout_ok, tout = _fade_ok(te, tr)
    d["fade_in"] = {"edge_db": round(he, 1), "ref_db": round(hr, 1), "result": hin,
                    "codec_zero_pad_ms": round(lead_ms, 1)}
    d["fade_out"] = {"edge_db": round(te, 1), "ref_db": round(tr, 1), "result": tout,
                     "codec_zero_pad_ms": round(trail_ms, 1)}
    if not hin_ok:
        errors.append(f"fade-in missing (edge {he:.1f} dB vs ref {hr:.1f} dB)")
    if not tout_ok:
        errors.append(f"fade-out missing (edge {te:.1f} dB vs ref {tr:.1f} dB)")
    d["errors"] = errors
    return not errors, d
