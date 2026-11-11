#!/usr/bin/env python3
"""DEC-12a: G9's re-encode spread, MEASURED. The locked outro (config.conform_outro, both formats) goes through
the final-encode path 5 times: render16 / render_vertical's concat pass (h264_nvenc p4 constqp QP 18) and the
watermark pass (same settings, no overlay over the outro region); the final's later steps copy the video.
Identical input encodes identically (NVENC constqp is deterministic), so the five runs differ only where the
outro sits in the GOP: 0 / 50 / 100 / 150 / 200 frames of black before it; and (the final's real context) the
outro after each of five REAL credits cards; plus the real finals of that outro (v2f, the Nov 11 recut, its
preview). spread = max - min over all of them, rounded up to 0.01, at most 0.05 (DEC-12a).
Each result is measured exactly as qa_gates.gate_g9 does (mean grey of 3 frames in the last 1.0 s), on
encodes tagged bt709 / tv like every final (the conformed outro is untagged: decoded alone it reads BT.601).
Writes spread.json next to this script. Usage: python3 measure_g9_spread.py"""
import json
import math
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np

REPO = os.path.expanduser("~/protocol_pulse")
sys.path.insert(0, os.path.join(REPO, "pipeline"))
from config import conform_outro, NVENC_QP_FINAL, FPS  # noqa: E402

PHASES = (0, 50, 100, 150, 200)
HERE = os.path.dirname(os.path.abspath(__file__))


def nvenc(args, out):
    # tagged like every final (bt709, limited range: inherited from its first segment); the conformed outro
    # itself is untagged, and G9 decodes the FINAL, so the measurement decodes the same YUV the same way
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp",
                    "-qp", str(NVENC_QP_FINAL), "-pix_fmt", "yuv420p", "-r", str(FPS), "-colorspace", "bt709",
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-an", out], check=True)


def g9_luma(path, force_bt709=False):
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                               capture_output=True, text=True).stdout)
    vals = []
    for i in range(3):
        t = max(0, dur - 1.0) + (i + 0.5) / 3
        f = tempfile.mktemp(suffix=".png")
        vf = ["-vf", "setparams=colorspace=bt709"] if force_bt709 else []
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.4f}", "-i", path, *vf, "-frames:v", "1", f], check=True)
        vals.append(float(cv2.imread(f, cv2.IMREAD_GRAYSCALE).mean()))
        os.unlink(f)
    return float(np.mean(vals)), vals


CARDS = ("references/v2f_2026-11-06/run/qa", "runs/pinned_20261111_172202/qa", "runs/pinned_20261111_172202_replay_cut1329/qa",
         "runs/pinned_20261111_123750/qa", "tests/fixtures/pulse_20261110/video")


def cards(fmt, tmp):
    """In a final the outro follows a credits card, so its frames are predicted from that card: the second
    measurement puts five REAL cards before it (their different lengths also vary the GOP phase)."""
    rows = []
    outro = conform_outro(fmt)
    for i, d in enumerate(CARDS):
        card = os.path.join(REPO, d, f"shoutout_{fmt}.mp4")
        concat, final = os.path.join(tmp, f"{fmt}_card{i}_concat.mp4"), os.path.join(tmp, f"{fmt}_card{i}_final.mp4")
        nvenc(["-i", card, "-i", outro, "-filter_complex",
               "[0:v]setsar=1[a];[1:v]setsar=1[b];[a][b]concat=n=2:v=1:a=0,setpts=PTS-STARTPTS"], concat)
        nvenc(["-i", concat], final)
        m, vals = g9_luma(final)
        rows.append({"card": d, "luma": round(m, 4), "frames": [round(v, 4) for v in vals]})
        print(fmt, "card", d, round(m, 4))
    return rows


FINALS = {  # real outputs of the final-encode path ending on the same locked outro, decoded as bt709 (as tagged)
    "16x9": ("references/v2f_2026-11-06/run/out/segment.mp4", "runs/pinned_20261111_172202/out/segment.mp4",
             "runs/pinned_20261111_172202_replay_cut1329_replay_preview/out/segment.mp4"),
    "9x16": ("references/v2f_2026-11-06/run/out/segment_vertical.mp4",
             "runs/pinned_20261111_172202/out/segment_vertical.mp4",          # untagged (pre-36e769d0): decoded bt709
             "runs/pinned_20261111_172202_replay_cut1329_replay_preview/out/segment_vertical.mp4")}


def finals(fmt):
    rows = []
    for d in FINALS[fmt]:
        p = os.path.join(REPO, d)
        if not os.path.exists(p):                       # never a silent skip: a missing final would shrink
            raise SystemExit(f"STOP: real final missing: {d}")   # the measured spread
        m, vals = g9_luma(p, force_bt709=True)
        rows.append({"final": d, "luma": round(m, 4), "frames": [round(v, 4) for v in vals]})
        print(fmt, "final", d, round(m, 4))
    return rows


def main():
    res = {}
    tmp = tempfile.mkdtemp(prefix="g9spread_")
    for fmt, (w, h) in (("16x9", (1920, 1080)), ("9x16", (1080, 1920))):
        outro = conform_outro(fmt)
        rows = []
        for k in PHASES:
            concat = os.path.join(tmp, f"{fmt}_{k}_concat.mp4")
            final = os.path.join(tmp, f"{fmt}_{k}_final.mp4")
            if k:
                nvenc(["-f", "lavfi", "-i", f"color=black:s={w}x{h}:r={FPS}:d={k / FPS}", "-i", outro,
                       "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0,setpts=PTS-STARTPTS"], concat)
            else:
                nvenc(["-i", outro, "-vf", "setpts=PTS-STARTPTS"], concat)
            nvenc(["-i", concat], final)                       # the watermark pass re-encode
            m, vals = g9_luma(final)
            rows.append({"phase_frames": k, "luma": round(m, 4), "frames": [round(v, 4) for v in vals]})
            print(fmt, k, round(m, 4))
        lum = [r["luma"] for r in rows]
        crow = cards(fmt, tmp)
        clum = [r["luma"] for r in crow]
        frow = finals(fmt)
        flum = [r["luma"] for r in frow]
        allv = lum + clum + flum
        spread = round(max(allv) - min(allv), 4)
        res[fmt] = {"outro": outro, "gop_phase_runs": rows, "gop_phase_spread": round(max(lum) - min(lum), 4),
                    "card_runs": crow, "card_spread": round(max(clum) - min(clum), 4),
                    "real_finals": frow, "spread": spread,
                    "spread_rounded": min(0.05, math.ceil(spread * 100 - 1e-9) / 100)}
    with open(os.path.join(HERE, "spread.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: v["spread"] for k, v in res.items()}))


if __name__ == "__main__":
    main()
