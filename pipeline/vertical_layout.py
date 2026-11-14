#!/usr/bin/env python3
"""pipeline/vertical_layout.py — deterministic per-shot vertical layout class (DEC-2, DEC-5, M5).

PBX 2026-11-11: the 9:16 is a speaker-centred reframe by default; 2-3 people get stacked bands; the
wide safe frame (letterbox) only for a shared screen or when the speaker cannot be identified, and then
flagged in the EDL and the Telegram caption. Detection MEASURES (SCRFD faces, face_scrfd.py); these
fixed rules DECIDE. Layouts are per SHOT: a clip is sampled every SAMPLE_S and split where the class of
the picture changes (Natalie Brunell's Nov 10 clip = chart graphic -> talking head -> Capitol B-roll).

Per sample (face area = bbox area / frame area):
  screen   largest face < SCREEN_FACE_FRAC (1.0 %) or no face: a shared screen / chart / B-roll with at
           most a small face-cam (DataDash face-cam 0.4 %; Yahoo Finance standing host 1.6 %; Natalie
           Brunell 7.7-13 %: SCRFD measurements 2026-11-11)
  single   exactly one face >= PROMINENT_FRAC (1.0 %)
  stack2 / stack3   two / three faces >= 1.0 %, the smallest >= MIN_BAND_RATIO of the largest
  uncertain  anything else (4+ faces, one dominant face plus small ones of unclear role)
Shots: runs of equal sample class; runs shorter than MIN_SHOT_S are merged into the longer neighbour.
Rendering per shot class: single -> fixed speaker-centred 9:16 crop at the shot's median face centre
(no animated panning, Law 18a); stack2/3 -> equal bands left-to-right; screen/uncertain -> safe frame
(letterbox), always reported in the plan as flagged.
"""
import json
import os
import subprocess

import numpy as np

SAMPLE_S = 0.5
SCREEN_FACE_FRAC = 0.010
PROMINENT_FRAC = 0.010
MIN_BAND_RATIO = 0.35
MIN_SHOT_S = 1.0
SAFE_FRAME = ("screen", "uncertain")
# RULING 93 (orchestrator 2026-11-13 '23:59'): the 9:16 single crop must not cut a lower third mid-word where a crop
# inside the face-safe range keeps every element wholly in or wholly out. Law 20: constants, never tuned to pass.
# Measured on the published 0c68b589 CNBC clip (DoD 23:51): the band holds the tag, the logo and the banner words.
LT_BAND = (0.70, 0.985)        # the lower-third band, fractions of the frame height
LT_CANNY = (80, 200)           # edge thresholds
LT_CLOSE = (13, 5)             # horizontal closing: letters into a word, not words into a line
LT_TEXT_H = (14, 90)           # an element's height in pixels (text, not a rule or a bar)
LT_MIN_W, LT_MIN_AREA = 10, 60
FACE_MARGIN_FRAC = 0.10        # the face box stays >= 10 % of the crop width from either crop edge


def lower_third_spans(frame):
    """Ruling 93: the x spans [x0, x1] of word-sized, text-like elements in the frame's lower-third band (Canny edges
    closed horizontally into word-sized boxes)."""
    import cv2
    h = frame.shape[0]
    y0, y1 = int(LT_BAND[0] * h), int(LT_BAND[1] * h)
    edges = cv2.Canny(cv2.cvtColor(frame[y0:y1], cv2.COLOR_BGR2GRAY), *LT_CANNY)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, LT_CLOSE))
    n, _, st, _ = cv2.connectedComponentsWithStats(closed, 8)
    return sorted({(int(st[i][0]), int(st[i][0] + st[i][2])) for i in range(1, n)
                   if LT_TEXT_H[0] <= st[i][3] <= LT_TEXT_H[1] and st[i][2] >= LT_MIN_W and st[i][4] >= LT_MIN_AREA})


def single_crop(faces, spans, w, h):
    """Ruling 93: the 9:16 single crop's x for a shot (crop width h * 9 / 16, full height). Today's crop is centred on
    the median face (render_vertical._shot_vf). When a crop edge falls inside a lower-third element (spans) and some x
    inside the face-safe range (every sampled face box inside the crop, FACE_MARGIN_FRAC of the crop width from either
    edge) has no edge inside any element, the nearest such x; else today's x, reported as cut. -> (x, record)."""
    cw = int(h * 9 / 16)
    if not faces:                                  # batch 74 c1 consensus: no face sample, no face-safe range: no x
        return None, {"rule": "ruling 93", "x": None, "cut": False, "spans": len(spans), "why": "no face samples"}
    cx = int(np.median([f[1] for f in faces]))
    base = max(0, min(w - cw, cx - cw // 2))

    def cuts(x):
        return [[a, b] for a, b in spans if a < x < b or a < x + cw < b]
    if not cuts(base):
        return base, {"rule": "ruling 93", "x": base, "moved_px": 0, "cut": False, "spans": len(spans)}
    sides = [(f[0] * w * h) ** 0.5 for f in faces]
    left = min(f[1] - s / 2 for f, s in zip(faces, sides))
    right = max(f[1] + s / 2 for f, s in zip(faces, sides))
    m = FACE_MARGIN_FRAC * cw
    lo, hi = max(0, int(np.ceil(right + m - cw))), min(w - cw, int(np.floor(left - m)))
    clear = [x for x in range(lo, hi + 1) if not cuts(x)]
    if clear:
        x = min(clear, key=lambda v: (abs(v - base), v))
        return x, {"rule": "ruling 93", "x": x, "moved_px": x - base, "cut": False, "spans": len(spans),
                   "face_safe_x": [lo, hi]}
    return base, {"rule": "ruling 93", "x": base, "moved_px": 0, "cut": True, "spans": len(spans),
                  "face_safe_x": [lo, hi], "cut_spans": cuts(base)[:8]}
G4_LAYOUT = {"single": "single", "stack2": "2face", "stack3": "3face", "screen": "screenshare",
             "uncertain": "single"}


def _probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,nb_frames,r_frame_rate:format=duration", "-of", "json", path],
                       capture_output=True, text=True, check=True, timeout=30)
    j = json.loads(r.stdout)
    s = j["streams"][0]
    num, den = (int(x) for x in s["r_frame_rate"].split("/"))
    return int(s["width"]), int(s["height"]), num / den, float(j["format"]["duration"])


def sample_label(faces, w, h):
    """Class of one sampled frame from its SCRFD faces [(x0, y0, x1, y1, score)]."""
    fr = [((x1 - x0) * (y1 - y0) / float(w * h), (x0 + x1) / 2.0, (y0 + y1) / 2.0) for x0, y0, x1, y1, _ in faces]
    fr.sort(key=lambda f: -f[0])
    if not fr or fr[0][0] < SCREEN_FACE_FRAC:
        return "screen", fr
    prom = [f for f in fr if f[0] >= PROMINENT_FRAC]
    if len(prom) == 1:
        return "single", fr
    if len(prom) in (2, 3) and prom[-1][0] >= MIN_BAND_RATIO * prom[0][0]:
        return f"stack{len(prom)}", fr
    return "uncertain", fr


def _runs(labels):
    runs, i = [], 0
    while i < len(labels):
        j = i
        while j < len(labels) and labels[j] == labels[i]:
            j += 1
        runs.append([labels[i], i, j])
        i = j
    return runs


CUT_PEAK_RATIO = 3.0   # a frame difference >= 3x the window median is a picture cut


def _cut_frame(clip_path, mid, half, n_frames):
    """First frame of the new shot near `mid`: the largest consecutive-frame difference (64x36 grey)
    within +-half frames when it is a clear peak, else `mid` (sample-accurate)."""
    import cv2
    a, b = max(1, mid - half), min(n_frames - 1, mid + half)
    cap = cv2.VideoCapture(clip_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, a - 1)
    prev, diffs = None, []
    for f in range(a - 1, b + 1):
        ok, fr = cap.read()
        if not ok:
            break
        g = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (64, 36)).astype(np.float32)
        if prev is not None:
            diffs.append((float(np.mean(np.abs(g - prev))), f))
        prev = g
    cap.release()
    if len(diffs) < 3:
        return mid
    vals = np.array([d for d, _ in diffs])
    k = int(np.argmax(vals))
    return diffs[k][1] if vals[k] >= CUT_PEAK_RATIO * max(np.median(vals), 1e-3) else mid


def classify(clip_path, detect=None):
    """Per-shot plan for a prepared clip: {"shots": [{"start", "end", "class", "faces", ...}], ...}.
    Times are clip-relative seconds, shot edges on frame boundaries."""
    import cv2
    if detect is None:
        from face_scrfd import detect
    w, h, fps, dur = _probe(clip_path)
    cap = cv2.VideoCapture(clip_path)
    n_frames = int(round(dur * fps))
    times = np.arange(SAMPLE_S / 2, dur, SAMPLE_S)
    samples = []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(n_frames - 1, int(t * fps)))
        ok, frame = cap.read()
        label, fr = sample_label(detect(frame), w, h) if ok else ("uncertain", [])
        if not ok:      # never silent (cross-LLM UF-1): counted in the plan, printed in the run log
            print(f"  WARNING vertical_layout: frame unreadable in {os.path.basename(clip_path)} at {t:.2f} s -> uncertain")
        samples.append({"t": round(float(t), 3), "class": label, "read_ok": bool(ok),
                        "faces": [[round(a, 4), round(x), round(y)] for a, x, y in fr[:4]],
                        "lt": [list(s) for s in lower_third_spans(frame)] if ok else []})   # ruling 93
    cap.release()
    if not samples:
        raise RuntimeError(f"no frames sampled from {clip_path}")
    labels = [s["class"] for s in samples]
    runs = _runs(labels)
    min_n = max(1, int(round(MIN_SHOT_S / SAMPLE_S)))
    changed = True
    while changed and len(runs) > 1:                      # absorb short runs into the longer neighbour
        changed = False
        for k, (lab, a, b) in enumerate(runs):
            if b - a < min_n:
                left = runs[k - 1] if k > 0 else None
                right = runs[k + 1] if k + 1 < len(runs) else None
                tgt = max([r for r in (left, right) if r], key=lambda r: r[2] - r[1])
                for i in range(a, b):
                    labels[i] = tgt[0]
                runs = _runs(labels)
                changed = True
                break
    edges = {}
    for _, a, _b in runs[1:]:                             # refine each internal edge to the cut frame
        mid = int(round((times[a - 1] + times[a]) / 2 * fps))
        edges[a] = _cut_frame(clip_path, mid, int(round(SAMPLE_S * fps)), n_frames)
    shots = []
    for lab, a, b in runs:
        start = 0.0 if a == 0 else round(edges[a] / fps, 4)
        end = round(dur, 4) if b == len(times) else round(edges[b] / fps, 4)
        faces = [s["faces"] for s in samples[a:b] if s["class"] == lab]
        shot = {"start": start, "end": end, "class": lab, "flagged": lab in SAFE_FRAME,
                "g4_layout": G4_LAYOUT[lab], "n_samples": b - a}
        if lab == "single":
            shot["face_cx"] = int(np.median([f[0][1] for f in faces]))
            shot["face_cy"] = int(np.median([f[0][2] for f in faces]))
            spans = sorted({tuple(x) for s in samples[a:b] for x in s.get("lt") or []})   # ruling 93: one static
            shot["crop_x"], shot["lower_third"] = single_crop([f[0] for f in faces], spans, w, h)  # crop, every sample
        elif lab in ("stack2", "stack3"):
            n = int(lab[-1])
            per = [sorted(f[:n], key=lambda c: c[1]) for f in faces]    # each sample's n faces, left to right
            shot["band_cx"] = [int(x) for x in np.median([[c[1] for c in p] for p in per], axis=0)]
            shot["band_cy"] = [int(y) for y in np.median([[c[2] for c in p] for p in per], axis=0)]
        shots.append(shot)
    return {"clip": os.path.basename(clip_path), "width": w, "height": h, "fps": fps, "duration": round(dur, 4),
            "rules": {"SAMPLE_S": SAMPLE_S, "SCREEN_FACE_FRAC": SCREEN_FACE_FRAC, "PROMINENT_FRAC": PROMINENT_FRAC,
                      "MIN_BAND_RATIO": MIN_BAND_RATIO, "MIN_SHOT_S": MIN_SHOT_S},
            "shots": shots, "samples": samples, "unreadable_samples": sum(1 for s in samples if not s["read_ok"]),
            "flagged": any(s["flagged"] for s in shots)}


# ── G4s LAYOUT TRUTH (DEC-2): a label must match the picture; safe frame only where labelled ──

SAFE_FRAME_BAND = (656, 1264)   # render_vertical.LETTERBOX_VF: the 16:9 frame scaled to 1080x608, centred
SAFE_FRAME_MIN_CORR = 0.90      # band vs the prepared frame, 64x36 grey, measured 2026-11-11: letterbox
                                # 0.998-1.000 (Nov 10 9:16, 18 frames); v2f speaker crops <= 0.448 (24 frames)


def _frame(path, t):
    import cv2
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
    ok, f = cap.read()
    cap.release()
    return f if ok else None


def _thumb(bgr):
    import cv2
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return cv2.resize(g, (64, 36), interpolation=cv2.INTER_AREA).astype(np.float64)


def is_safe_frame(vert_bgr, src_bgr):
    """True when a 1080x1920 frame is the safe frame: its centre band reproduces the WHOLE 16:9 source
    frame of the same instant (normalised correlation >= SAFE_FRAME_MIN_CORR). A speaker crop or
    stacked bands show part of the picture, never all of it; a plain or soft background cannot pass."""
    if vert_bgr.shape[:2] != (1920, 1080):
        return False, {"band_corr": None, "shape": list(vert_bgr.shape[:2])}
    a, b = _thumb(vert_bgr[SAFE_FRAME_BAND[0]:SAFE_FRAME_BAND[1]]), _thumb(src_bgr)
    a, b = a - a.mean(), b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    r = float((a * b).sum() / d) if d > 0 else 0.0
    return r >= SAFE_FRAME_MIN_CORR, {"band_corr": round(r, 3)}


def gate_g4s(plans, prepared, vert_final=None, vert_segments=None, detect=None):
    """plans {clip_id: plan}, prepared {clip_id: prepared clip path}. Each shot's label must equal the
    majority class re-measured on that shot's own frames (never the label itself); in the 9:16 final the
    shot must be a safe frame iff it is labelled screen/uncertain. Returns (ok, table)."""
    if detect is None:
        from face_scrfd import detect
    import cv2
    seg_start = {s["label"]: s["start"] for s in (vert_segments or [])}
    table, ok_all = [], True
    for cid, plan in plans.items():
        for k, shot in enumerate(plan["shots"]):
            times = [shot["start"] + (shot["end"] - shot["start"]) * (i + 0.5) / 5 for i in range(5)]
            meas = []
            for t in times:
                f = _frame(prepared[cid], t)
                meas.append(sample_label(detect(f), f.shape[1], f.shape[0])[0] if f is not None else "uncertain")
            majority = max(set(meas), key=meas.count)
            row = {"segment": cid, "shot": k, "label": shot["class"], "measured": meas, "label_ok": majority == shot["class"]}
            if vert_final and cid in seg_start:
                tm = (shot["start"] + shot["end"]) / 2
                vf, sf = _frame(vert_final, seg_start[cid] + tm), _frame(prepared[cid], tm)
                safe, m = is_safe_frame(vf, sf) if vf is not None and sf is not None else (None, {})
                row.update(vertical_safe_frame=safe, **m,
                           vertical_ok=safe is not None and safe == (shot["class"] in SAFE_FRAME))
            row["pass"] = row["label_ok"] and row.get("vertical_ok", True)
            ok_all &= row["pass"]
            table.append(row)
    return ok_all, table


def layout_note(edl):
    """Caption lines for the Telegram drop (DEC-2/DEC-5): every safe-frame shot named with its layout,
    never silent; a segment without a measured layout is reported too. '' when every shot is reframed."""
    lines = []
    for label, seg in [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl.get("clips", [])]:
        vl = seg.get("vertical_layout")
        if not vl:
            lines.append(f"9:16 {label} ({seg.get('channel')}): layout NOT MEASURED")
            continue
        spans = [f"layout={sh['class']}" + (" (speaker unidentified)" if sh["class"] == "uncertain" else "")
                 + f" {sh['start']:.2f}-{sh['end']:.2f} s" for sh in vl["shots"] if sh["flagged"]]
        if spans:
            lines.append(f"9:16 SAFE FRAME {label} ({seg.get('channel')}): " + "; ".join(spans))
    return "\n".join(lines)


def per_shot_manifest(segments, plans):
    """Manifest with each clip split into its shots (type talking_head, G4 layout per shot) so the
    UNCHANGED gate_g4 applies the right face rule to every shot. Shot times are measured on the
    prepared clip, lead-in pad included, so they map onto the timeline by the segment start alone."""
    out = []
    for s in segments:
        plan = plans.get(s["label"]) if s.get("type") == "talking_head" else None
        if not plan:
            out.append(s)
            continue
        for k, sh in enumerate(plan["shots"]):
            out.append({"label": f"{s['label']}#{k}", "type": "talking_head", "layout": sh["g4_layout"],
                        "source_faces": int(sh["class"][-1]) if sh["class"].startswith("stack") else 1,
                        "start": round(s["start"] + sh["start"], 3), "end": round(s["start"] + sh["end"], 3)})
    return out
