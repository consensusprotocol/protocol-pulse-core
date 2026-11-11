#!/usr/bin/env python3
"""pipeline/pulse_transitions.py — transitions between segments from DIFFERENT channels only (Phase 3, DEC-4).

Styles (run-level, TRANSITIONS.json written by run_fresh before rendering; no file = hard cuts, the
frozen v2f path, Law 22):
  crossfade  DEC-4 production default: 6-frame cross-dissolve + matching audio crossfade (= B without
             the thump).
  A          clean cut; 6-frame audio dip-crossfade centred on the cut (A fades over its last 3 frames,
             B rises over its first 3) - no picture effect, no overlap, picture and sound frame-locked.
  B          6-frame cross-dissolve + matching audio crossfade + a soft low pulse thump (sub sine + short
             click) at the dissolve's centre.
  C          brand pulse wipe: an 8-frame insert (0.333 s) on black in which the brand ECG line
             (brand/2026-11/pp_pulse_glossy.svg path) sweeps left to right, with a heartbeat double thump.
Overlaps (crossfade/B) and fades (A) only ever cover non-speech: each junction is bounded by the
measured genuine tail of A and lead-in of B (sentence_law.head_tail on the prepared clips); a junction
that cannot hold >= 2 frames of non-speech stays a hard cut. Sound design peaks at THUMP_PEAK_DBFS
(-24 dBFS before the music bed and loudnorm, Law 13 range) and sits only where nobody speaks.
Nothing is ever added at the open of the video (the first junction is after the hook).
"""
import json
import math
import os
import subprocess
import wave

import numpy as np

FPS = 24
SR = 48000
DISSOLVE_FRAMES = 6
WIPE_FRAMES = 8
MIN_FRAMES = 2
THUMP_PEAK_DBFS = -24.0
STYLES = ("crossfade", "A", "B", "C")
PULSE_PATH = ("M38 278 L84 278 C109 278 115 220 136 220 C158 220 164 330 180 330 C196 330 242 98 252 98 "
              "C262 98 306 384 316 384 C329 384 342 220 364 220 C385 220 391 278 416 278 L462 278")


def plan(segments, channels, lead_tail, style):
    """Junction list [{"after": i, "frames": n, "kind": ...}] for the concat of `segments` (manifest
    order: (label, path, type)). channels {label: channel}; lead_tail {label: (lead_s, tail_s)}."""
    if style not in STYLES:
        raise ValueError(f"unknown transition style {style!r}")
    out = []
    for i in range(len(segments) - 1):
        (la, _, ta), (lb, _, tb) = segments[i], segments[i + 1]
        if ta != "talking_head" or tb != "talking_head" or channels.get(la) == channels.get(lb):
            continue                                            # only between different channels
        want = WIPE_FRAMES if style == "C" else DISSOLVE_FRAMES
        if style == "C":
            out.append({"after": i, "frames": want, "kind": "insert", "style": style})
            continue
        tail_a, lead_b = lead_tail[la][1], lead_tail[lb][0]
        half = style == "A"                                     # A: each side fades over half
        room = min(tail_a, lead_b) * (2 if half else 1)
        n = min(want, int(math.floor(room * FPS + 1e-9)))
        if n >= MIN_FRAMES:
            out.append({"after": i, "frames": n, "kind": "dip" if half else "dissolve", "style": style,
                        "bounded_by_ms": [int(tail_a * 1000), int(lead_b * 1000)]})
    return out


# ── sound design (generated in code; no stock packs) ──

def thump(sub_hz=52.0, dur=0.32, click_ms=4.0):
    t = np.arange(int(dur * SR)) / SR
    body = np.sin(2 * np.pi * sub_hz * t) * np.exp(-t / 0.075) * (1 - np.exp(-t / 0.004))
    k = int(click_ms / 1000 * SR)
    click = np.zeros_like(t)
    click[:k] = np.random.default_rng(11).normal(0, 1, k) * np.hanning(2 * k)[k:] * 0.35
    x = body + np.convolve(click, np.ones(24) / 24, mode="same")
    return x / np.max(np.abs(x))


def double_thump():
    a, b = thump(), thump(sub_hz=46.0) * 0.6
    gap = int(0.17 * SR)
    out = np.zeros(gap + len(b))
    out[:len(a)] += a
    out[gap:gap + len(b)] += b
    return out / np.max(np.abs(out))


def write_wav(path, mono, peak_dbfs):
    x = mono * (10 ** (peak_dbfs / 20))
    k = int(0.005 * SR)                                         # Law 13: 5 ms micro-fades at both ends
    x[:k] *= np.linspace(0, 1, k)
    x[-k:] *= np.linspace(1, 0, k)
    st = np.stack([x, x], 1)
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())


# ── C: brand pulse wipe insert ──

def _bezier_points(path=PULSE_PATH, steps=24):
    import re
    toks = re.findall(r"[MLC]|-?\d+(?:\.\d+)?", path)
    pts, cur, i = [], None, 0
    while i < len(toks):
        cmd = toks[i]
        if cmd in ("M", "L"):
            cur = (float(toks[i + 1]), float(toks[i + 2]))
            pts.append(cur)
            i += 3
        elif cmd == "C":
            p1, p2, p3 = [(float(toks[i + 1 + 2 * k]), float(toks[i + 2 + 2 * k])) for k in range(3)]
            for s in range(1, steps + 1):
                u = s / steps
                pts.append(tuple((1 - u) ** 3 * cur[d] + 3 * (1 - u) ** 2 * u * p1[d] + 3 * (1 - u) * u ** 2 * p2[d]
                                 + u ** 3 * p3[d] for d in range(2)))
            cur = p3
            i += 7
        else:
            raise ValueError(f"unsupported path command {cmd}")
    return pts


def wipe_frames(w, h, n=WIPE_FRAMES):
    """n RGB frames on black: the brand ECG line (thin neon: dark under-stroke, red glow, hot core)
    drawn left to right across the frame's middle, fully drawn on the last frame."""
    from PIL import Image, ImageDraw, ImageFilter
    pts = _bezier_points()
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    sx = w / (max(xs) - min(xs))
    sy = sx * 0.55 if w > h else sx * 0.9
    cy = h / 2
    line = [((x - min(xs)) * sx, cy + (y - 278) * sy) for x, y in pts]
    scale = max(1.0, w / 1920)
    frames = []
    for k in range(n):
        upto = (k + 1) / n * w
        vis = [p for p in line if p[0] <= upto]
        if len(vis) < 2:
            vis = line[:2]
        glow = Image.new("RGB", (w, h), (0, 0, 0))
        ImageDraw.Draw(glow).line(vis, fill=(225, 6, 0), width=int(16 * scale), joint="curve")
        glow = glow.filter(ImageFilter.GaussianBlur(10 * scale))
        img = Image.new("RGB", (w, h), (0, 0, 0))
        d = ImageDraw.Draw(img)
        d.line(vis, fill=(26, 0, 0), width=int(12 * scale), joint="curve")
        img = Image.fromarray(np.maximum(np.asarray(img), np.asarray(glow)))
        d = ImageDraw.Draw(img)
        d.line(vis, fill=(255, 42, 26), width=int(5 * scale), joint="curve")
        d.line(vis, fill=(255, 210, 204), width=max(1, int(1.5 * scale)), joint="curve")
        frames.append(img)
    return frames


def render_wipe(path, w, h, qp):
    import tempfile
    tmp = tempfile.mkdtemp(prefix="wipe_")
    for k, f in enumerate(wipe_frames(w, h)):
        f.save(os.path.join(tmp, f"f{k:02d}.png"))
    wav = os.path.join(tmp, "dt.wav")
    dur = WIPE_FRAMES / FPS
    x = double_thump()
    pad = np.zeros(int(dur * SR))
    pad[:min(len(pad), len(x))] = x[:len(pad)]
    write_wav(wav, pad, THUMP_PEAK_DBFS)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%02d.png"),
                    "-i", wav, "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(qp),
                    "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-t", f"{dur:.4f}", "-movflags", "+faststart", path], check=True, capture_output=True, timeout=120)
    return path


# ── concat with transitions ──

def _frames(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_packets", "-of", "csv=p=0", path], capture_output=True, text=True,
                       check=True, timeout=60)
    return int(r.stdout.strip().split(",")[0])


def concat(segments, junctions, out_path, qp, w, h, work_dir):
    """Concatenate (label, path, type) segments with the planned junctions. Every input is normalised
    to its exact video frame count (audio padded/trimmed to it) so picture and sound stay locked.
    Returns the timeline [{"label","type","start","end"}] (overlapping entries at dissolves)."""
    style_c = [j for j in junctions if j["kind"] == "insert"]
    segs = list(segments)
    if style_c:
        wipe = render_wipe(os.path.join(work_dir, "transition_wipe_C.mp4"), w, h, qp)
        for j in sorted(style_c, key=lambda j: -j["after"]):
            segs.insert(j["after"] + 1, ("transition_C", wipe, "transition"))
        junctions = [j for j in junctions if j["kind"] != "insert"]
    jmap = {segs.index(segments[j["after"]]): j for j in junctions}
    frames = [_frames(p) for _, p, _ in segs]
    graph, tl = [], []
    for i, (_, p, _) in enumerate(segs):
        d = frames[i] / FPS
        graph.append(f"[{i}:v]setpts=PTS-STARTPTS,fps={FPS},trim=end_frame={frames[i]},setsar=1[v{i}]")
        graph.append(f"[{i}:a]asetpts=PTS-STARTPTS,aresample=async=1,apad,atrim=end={d:.6f},"
                     f"aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo[a{i}]")
    vcur, acur, t = "v0", "a0", frames[0] / FPS
    tl.append({"label": segs[0][0], "type": segs[0][2], "start": 0.0, "end": round(t, 4)})
    thumps = []
    for i in range(1, len(segs)):
        j = jmap.get(i - 1)
        di = frames[i] / FPS
        if j and j["kind"] == "dissolve":
            dd = j["frames"] / FPS
            # ffmpeg 4.4.2 xfade keeps A through the frame at round(offset*fps) and starts B on the NEXT
            # frame: offset=t-dd put B's frame k at t-dd+(k+1)/fps, one frame (41.7 ms) behind B's own
            # audio for the whole clip (measured 2026-11-11, test_transitions TestConcat). One frame
            # earlier lands B's first frame exactly at t-dd, where acrossfade starts B's audio.
            graph.append(f"[{vcur}][v{i}]xfade=transition=fade:duration={dd:.6f}:"
                         f"offset={t - dd - 1 / FPS:.6f}[vx{i}]")
            graph.append(f"[{acur}][a{i}]acrossfade=d={dd:.6f}:c1=tri:c2=tri[ax{i}]")
            start = t - dd
            if j["style"] == "B":
                thumps.append(start + dd / 2)
        else:
            if j and j["kind"] == "dip":
                dd = j["frames"] / FPS / 2
                graph.append(f"[{acur}]afade=t=out:st={t - dd:.6f}:d={dd:.6f}[ad{i}]")
                graph.append(f"[a{i}]afade=t=in:st=0:d={dd:.6f}[ai{i}]")
                acur, ain = f"ad{i}", f"ai{i}"
            else:
                ain = f"a{i}"
            graph.append(f"[{vcur}][{acur}][v{i}][{ain}]concat=n=2:v=1:a=1[vx{i}][ax{i}]")
            start = t
        vcur, acur, t = f"vx{i}", f"ax{i}", start + di
        tl.append({"label": segs[i][0], "type": segs[i][2], "start": round(start, 4), "end": round(t, 4)})
    inputs = []
    for _, p, _ in segs:
        inputs += ["-i", p]
    if thumps:
        x = np.zeros(int((t + 1) * SR))
        th = thump()
        for c in thumps:
            k = int((c - 0.02) * SR)
            x[k:k + len(th)] += th[:len(x) - k]
        tw = os.path.join(work_dir, "transition_thumps_B.wav")
        write_wav(tw, x / max(1e-9, np.max(np.abs(x))), THUMP_PEAK_DBFS)
        inputs += ["-i", tw]
        graph.append(f"[{acur}][{len(segs)}:a]amix=inputs=2:duration=first:normalize=0[amx]")
        acur = "amx"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph),
                    "-map", f"[{vcur}]", "-map", f"[{acur}]", "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp",
                    "-qp", str(qp), "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-ac", "2", "-movflags", "+faststart", out_path],
                   check=True, capture_output=True, timeout=1200)
    with open(os.path.join(work_dir, "transitions_timeline.json"), "w") as f:
        json.dump({"junctions": junctions + style_c, "timeline": tl, "thumps_s": thumps}, f, indent=2)
    return tl
