#!/usr/bin/env python3
"""pipeline/loudness.py: ruling 29 (orchestrator 2026-11-13 '01:55'): "G5 -15.2 LUFS against -14 +- 1: a render
defect. The final mix must be measured and corrected to target before the gates (two-pass loudness on the final, then
re-measure). The gate stays."

correct_finals(final16, final9) runs after both renders, before the gates:
1. pass 1: ffmpeg loudnorm measures the 16:9 final (input_i, input_tp, input_lra, input_thresh, target_offset);
2. within TOL_LU of the target: nothing is rewritten;
3. otherwise pass 2: loudnorm with the measured values and linear=true (a plain gain when the true-peak ceiling allows
   it; ffmpeg reports "dynamic" when it does not, and that is recorded) on the 16:9 audio only. The video stream is
   copied;
4. the 9:16 final gets EXACTLY that corrected audio stream, muxed over its own copied video. Law 23: the vertical
   carries the horizontal's mixed audio, identical by construction;
5. both are re-measured. They replace the finals only when both re-measure within TOL_LU of the target. Otherwise the
   rendered finals stay as they are and the reason is recorded: the gate decides on those.
Returns the record for PROVENANCE ("loudness")."""
import hashlib
import json
import os
import re
import subprocess

TARGET_I, TARGET_TP, TARGET_LRA = -14.0, -2.0, 11.0     # G5: ebur128 I = -14 +- 1, TP <= -2.0
TOL_LU = 0.5                                            # tighter than the gate's +- 1: corrected near the target
CODEC_TP_MARGIN = 0.5      # pass 2 aims 0.5 dB under the gate's ceiling: measured 2026-11-13 on pin #1's final, a
                           # linear +1.21 dB predicted -2.08 dBTP and re-measured -1.64 after the AAC encode


def measure(path):
    """loudnorm's pass-1 measurement of `path` (ffmpeg's own JSON). Raises RuntimeError when it cannot be read."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=600)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr)
    if r.returncode != 0 or not m:
        raise RuntimeError(f"loudness not measurable for {path}: {r.stderr.strip()[-200:]}")
    d = json.loads(m.group(0))
    return {k: (d[k] if k == "normalization_type" else float(d[k])) for k in d}


def _correct16(src, dst, m):
    af = (f"loudnorm=I={TARGET_I}:TP={TARGET_TP - CODEC_TP_MARGIN}:LRA={TARGET_LRA}:measured_I={m['input_i']}:"
          f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}:linear=true:print_format=json")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", src, "-map", "0:v:0", "-map", "0:a:0",
                        "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                        "-movflags", "+faststart", dst], capture_output=True, text=True, timeout=900)
    m2 = re.search(r"\{[^{}]*\"normalization_type\"[^{}]*\}", r.stderr)
    if r.returncode != 0 or not os.path.exists(dst):
        raise RuntimeError(f"pass 2 failed: {r.stderr.strip()[-200:]}")
    return json.loads(m2.group(0)).get("normalization_type") if m2 else None


def audio_md5(path):
    """md5 over the audio stream's packets (ffmpeg framemd5, stream copy): equal = the same audio bytes."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-c", "copy", "-f", "framemd5", "-"],
                       capture_output=True, text=True, timeout=300)
    lines = [l.split(",")[-1].strip() for l in r.stdout.splitlines() if l and not l.startswith("#")]
    if r.returncode != 0 or not lines:
        raise RuntimeError(f"audio not readable in {path}")
    return hashlib.md5("\n".join(lines).encode()).hexdigest()


def _mux9(video9, audio_from16, dst):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-i", video9, "-i", audio_from16,
                        "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-movflags", "+faststart", dst],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not os.path.exists(dst):
        raise RuntimeError(f"9:16 mux failed: {r.stderr.strip()[-200:]}")


def correct_finals(final16, final9):
    rec = {"target_i": TARGET_I, "target_tp": TARGET_TP, "tol_lu": TOL_LU}
    before = measure(final16)
    rec["before_16x9"] = before
    if abs(before["input_i"] - TARGET_I) <= TOL_LU and before["input_tp"] <= TARGET_TP:
        rec["action"] = "none: within tolerance"
        return rec
    t16, t9 = final16 + ".loud.mp4", final9 + ".loud.mp4"
    try:
        rec["normalization_type"] = _correct16(final16, t16, before)
        _mux9(final9, t16, t9)
        a16, a9 = measure(t16), measure(t9)
        rec["after_16x9"], rec["after_9x16"] = a16, a9
        bad = [f"{n} {a['input_i']} LUFS / {a['input_tp']} dBTP" for n, a in (("16x9", a16), ("9x16", a9))
               if abs(a["input_i"] - TARGET_I) > TOL_LU or a["input_tp"] > TARGET_TP]
        if bad:
            rec["action"] = f"kept the rendered finals: the corrected files re-measure off target ({'; '.join(bad)})"
            return rec
        if audio_md5(t16) != audio_md5(t9):                # Law 23 (audit batch 53 C2): one audio, byte for byte
            rec["action"] = "kept the rendered finals: the 9:16 audio is not the 16:9's corrected audio"
            return rec
        _replace_pair((t16, final16), (t9, final9))
        rec["action"] = "corrected"
        return rec
    except (RuntimeError, OSError) as e:
        rec["action"] = f"kept the rendered finals: {type(e).__name__}: {e}"
        return rec
    finally:
        for t in (t16, t9):
            if os.path.exists(t):
                os.unlink(t)


def _replace_pair(*moves):
    """Both finals replaced, or neither: the originals are kept as hard links until both moves succeed, and are put
    back if either fails (audit batch 53 C2, qwen)."""
    keep = []
    try:
        for _, dst in moves:
            os.link(dst, dst + ".orig")
            keep.append(dst)
        for src, dst in moves:
            os.replace(src, dst)
    except OSError:
        for dst in keep:
            os.replace(dst + ".orig", dst)
        raise
    finally:
        for _, dst in moves:
            if os.path.exists(dst + ".orig"):
                os.unlink(dst + ".orig")
