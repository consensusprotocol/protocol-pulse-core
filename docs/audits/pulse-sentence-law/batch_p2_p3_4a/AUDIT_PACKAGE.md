# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-11 05:45 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
The automated Protocol Pulse "Pulse Check" medley (pipeline/run_fresh.py) cuts hooks and clips from
partner YouTube videos, renders 16:9 and 9:16, and runs QA gates. PBX watched the 2026-11-10 cut and
found editorial errors every gate had passed: the opening word sounded clipped (D1), clips started or
ended mid-sentence (D2/D3), credit avatars were warped (D4), the vertical was letterboxed (D5) and
channel changes were abrupt (D6). This work makes the gates catch what a human caught, proves it on
yesterday's files (tests/fixtures/pulse_20261110, pipeline/test_pulse_20261110_mustfail.py), fixes the
causes, then requires three clean fresh videos in a row with no code edits between them.

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS
- SENTENCE LAW: a clip's first word is the first word of a sentence and its last word the last word of
  a sentence. Boundary = transcript punctuation AND an acoustic pause >= 80 ms between the two words
  (pipeline/sentence_law.py states every constant). An unpunctuated transcript stretch has NO boundary
  (fail closed). Punctuation is added at transcription time only from a second, prompted ASR decode of
  the same audio, onto aligned verbatim words; the words never change (pipeline/punctuation.py). No
  language model decides a boundary (the per-gap adjudicator called 19/19 gaps sentence ends; removed).
- SELECTION LOCK: the words a clip must contain are fixed at selection time (selection_lock in edl.json,
  sha256-sealed). No later stage may recompute expected first/last words from a moved cut.
- SNAP LIMIT: a cut may move only inside the silence between the chosen sentence and its neighbour; it
  may never add or drop a word. No legal boundary in that gap = the window is rejected.
- ONSET/TAIL: every rendered segment keeps >= 80 ms of genuine sub-speech audio before its first onset
  and after its last offset; codec zero/padding is not room tone; a source that starts speaking at its
  file head without lead-in needs a declared room-tone lead-in pad. Edge words keep >= 85 % of their
  duration in the render.
- CREDITS: round avatars of the channels actually used; the avatar is the channel's real square avatar,
  never a video thumbnail, never a generated placeholder; G12/G15 unchanged.
- LAW 20 / M2: gate thresholds are constants; a failed gate is a hard stop; never change what a check
  accepts to make a render pass; never reclassify a failing gate as a false positive.
- M12 FAIL CLOSED: missing data, model failure or an exception rejects; it never produces a pass.
- LAW 22: the frozen v2f reference (references/v2f_2026-11-06) must keep re-rendering byte-identically.
- Smallest diff; no new renderer, compositor or selector (M1); GPU0 only; no publishing.



---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (2187 lines)
```
   1 | diff --git a/pipeline/face_scrfd.py b/pipeline/face_scrfd.py
   2 | new file mode 100644
   3 | index 00000000..a5184ed4
   4 | --- /dev/null
   5 | +++ b/pipeline/face_scrfd.py
   6 | @@ -0,0 +1,76 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/face_scrfd.py — SCRFD-10G face detector (insightface buffalo_l det_10g.onnx) via
   9 | +onnxruntime (CPU). Used to MEASURE faces for the vertical layout class (DEC-2/DEC-5): the
  10 | +BlazeFace short-range model misses medium/small faces (Yahoo Finance's standing host, 2026-11-11) and
  11 | +the Haar cascade over-counts (2-4 'faces' on a single talking head). Detection measures; the layout
  12 | +rules in vertical_layout.py decide, deterministically."""
  13 | +import os
  14 | +
  15 | +import cv2
  16 | +import numpy as np
  17 | +
  18 | +MODEL = os.path.expanduser("~/.insightface/models/buffalo_l/det_10g.onnx")
  19 | +MODEL_SHA256 = "5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91"   # pinned 2026-11-11
  20 | +INPUT = 640
  21 | +SCORE_MIN = 0.5
  22 | +NMS_IOU = 0.4
  23 | +_SESSION = None
  24 | +
  25 | +
  26 | +def _session():
  27 | +    global _SESSION
  28 | +    if _SESSION is None:
  29 | +        import hashlib
  30 | +        import onnxruntime as ort
  31 | +        # the layout classes are only reproducible with this exact model: fail closed on any other
  32 | +        if not os.path.exists(MODEL):
  33 | +            raise FileNotFoundError(f"STOP: SCRFD model missing: {MODEL}")
  34 | +        with open(MODEL, "rb") as f:
  35 | +            digest = hashlib.sha256(f.read()).hexdigest()
  36 | +        if digest != MODEL_SHA256:
  37 | +            raise RuntimeError(f"STOP: SCRFD model sha256 {digest[:12]}... is not the pinned {MODEL_SHA256[:12]}...")
  38 | +        # CPU on purpose: this host's onnxruntime CUDA provider lacks cuDNN 8, and ~12 frames per clip
  39 | +        # need no GPU (GPU1 must never be touched; GPU0 stays free for whisper/NVENC)
  40 | +        _SESSION = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
  41 | +    return _SESSION
  42 | +
  43 | +
  44 | +def _nms(boxes, scores):
  45 | +    order, keep = scores.argsort()[::-1], []
  46 | +    while order.size:
  47 | +        i = order[0]
  48 | +        keep.append(i)
  49 | +        xx1, yy1 = np.maximum(boxes[i, 0], boxes[order[1:], 0]), np.maximum(boxes[i, 1], boxes[order[1:], 1])
  50 | +        xx2, yy2 = np.minimum(boxes[i, 2], boxes[order[1:], 2]), np.minimum(boxes[i, 3], boxes[order[1:], 3])
  51 | +        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
  52 | +        area = lambda b: (b[..., 2] - b[..., 0]) * (b[..., 3] - b[..., 1])
  53 | +        iou = inter / (area(boxes[i]) + area(boxes[order[1:]]) - inter + 1e-9)
  54 | +        order = order[1:][iou <= NMS_IOU]
  55 | +    return keep
  56 | +
  57 | +
  58 | +def detect(bgr):
  59 | +    """Faces in a BGR frame as [(x0, y0, x1, y1, score)] in frame pixels, largest first."""
  60 | +    h, w = bgr.shape[:2]
  61 | +    scale = INPUT / max(h, w)
  62 | +    nh, nw = int(round(h * scale)), int(round(w * scale))
  63 | +    canvas = np.zeros((INPUT, INPUT, 3), np.uint8)
  64 | +    canvas[:nh, :nw] = cv2.resize(bgr, (nw, nh))
  65 | +    blob = cv2.dnn.blobFromImage(canvas, 1.0 / 128, (INPUT, INPUT), (127.5, 127.5, 127.5), swapRB=True)
  66 | +    sess = _session()
  67 | +    outs = sess.run(None, {sess.get_inputs()[0].name: blob})
  68 | +    boxes, scores = [], []
  69 | +    for idx, stride in enumerate((8, 16, 32)):
  70 | +        sc, bb = outs[idx].reshape(-1), outs[idx + 3].reshape(-1, 4) * stride
  71 | +        g = INPUT // stride
  72 | +        centers = (np.stack(np.mgrid[:g, :g][::-1], axis=-1).reshape(-1, 2) * stride).astype(np.float32)
  73 | +        centers = np.repeat(centers, 2, axis=0)                     # two anchors per location
  74 | +        keep = sc >= SCORE_MIN
  75 | +        c, d = centers[keep], bb[keep]
  76 | +        boxes.append(np.stack([c[:, 0] - d[:, 0], c[:, 1] - d[:, 1], c[:, 0] + d[:, 2], c[:, 1] + d[:, 3]], 1))
  77 | +        scores.append(sc[keep])
  78 | +    boxes, scores = np.concatenate(boxes) / scale, np.concatenate(scores)
  79 | +    if not len(scores):
  80 | +        return []
  81 | +    out = [(*boxes[i].tolist(), float(scores[i])) for i in _nms(boxes, scores)]
  82 | +    return sorted(out, key=lambda f: -(f[2] - f[0]) * (f[3] - f[1]))
  83 | diff --git a/pipeline/render16.py b/pipeline/render16.py
  84 | index e001edf3..1561a39f 100644
  85 | --- a/pipeline/render16.py
  86 | +++ b/pipeline/render16.py
  87 | @@ -363,15 +363,17 @@ def render_16x9(segment_dir, qa_version=None, output_name="segment.mp4",
  88 |  
  89 |      concat_raw = os.path.join(qa_dir, "concat_raw.mp4")
  90 |      concat_partial = concat_raw.replace(".mp4", ".partial.mp4")
  91 | -    subprocess.run([
  92 | -        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
  93 | -        "-vf", "setpts=PTS-STARTPTS",
  94 | -        "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
  95 | -        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_FINAL),
  96 | -        "-pix_fmt", "yuv420p",
  97 | -        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
  98 | -        "-movflags", "+faststart", concat_partial,
  99 | -    ], capture_output=True, timeout=600, check=True)
 100 | +    timeline = _transition_concat(segment_dir, segments, concat_partial, WIDTH, HEIGHT, qa_dir)
 101 | +    if timeline is None:                     # no TRANSITIONS.json: the frozen hard-cut concat (v2f)
 102 | +        subprocess.run([
 103 | +            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
 104 | +            "-vf", "setpts=PTS-STARTPTS",
 105 | +            "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
 106 | +            "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_FINAL),
 107 | +            "-pix_fmt", "yuv420p",
 108 | +            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 109 | +            "-movflags", "+faststart", concat_partial,
 110 | +        ], capture_output=True, timeout=600, check=True)
 111 |      os.replace(concat_partial, concat_raw)
 112 |      concat_dur = get_duration(concat_raw)
 113 |      print(f"  Concat: {concat_dur:.2f}s")
 114 | @@ -387,6 +389,8 @@ def render_16x9(segment_dir, qa_version=None, output_name="segment.mp4",
 115 |              shoutout_start = cumulative
 116 |              break
 117 |          cumulative += dur
 118 | +    if timeline is not None:
 119 | +        shoutout_start = next(e["start"] for e in timeline if e["label"] == "shoutout")
 120 |  
 121 |      print(f"  Watermark: 0 -> {shoutout_start:.2f}s")
 122 |  
 123 | @@ -496,12 +500,15 @@ def render_16x9(segment_dir, qa_version=None, output_name="segment.mp4",
 124 |  
 125 |      cumul = 0.0
 126 |      manifest_segments = []
 127 | -    for label, path, seg_type in segments:
 128 | -        dur = get_duration(path)
 129 | +    tl = {e["label"]: e for e in timeline} if timeline is not None else {}
 130 | +    for label, path, seg_type in (segments if timeline is None else
 131 | +                                  [(e["label"], None, e["type"]) for e in timeline]):
 132 | +        dur = get_duration(path) if timeline is None else tl[label]["end"] - tl[label]["start"]
 133 | +        start = cumul if timeline is None else tl[label]["start"]
 134 |          seg_entry = {
 135 |              "label": label,
 136 | -            "start": round(cumul, 3),
 137 | -            "end": round(cumul + dur, 3),
 138 | +            "start": round(start, 3),
 139 | +            "end": round(start + dur, 3),
 140 |              "type": seg_type,
 141 |          }
 142 |  
 143 | @@ -547,6 +554,21 @@ def render_16x9(segment_dir, qa_version=None, output_name="segment.mp4",
 144 |      return final_path, manifest_path, vo_assembled_tracks
 145 |  
 146 |  
 147 | +def _transition_concat(segment_dir, segments, out_path, w, h, qa_dir):
 148 | +    """Phase 3 / DEC-4: when the run declares TRANSITIONS.json, concatenate with transitions between
 149 | +    segments of different channels (pipeline/transitions.py) and return the timeline; else None."""
 150 | +    tr_path = os.path.join(segment_dir, "TRANSITIONS.json")
 151 | +    if not os.path.exists(tr_path):
 152 | +        return None
 153 | +    import transitions as TR
 154 | +    with open(tr_path) as f:
 155 | +        tr = json.load(f)
 156 | +    junctions = TR.plan(segments, tr["channels"], {k: tuple(v) for k, v in tr["lead_tail"].items()},
 157 | +                        tr["style"])
 158 | +    print(f"  Transitions ({tr['style']}): {[(j['after'], j['frames'], j['kind']) for j in junctions]}")
 159 | +    return TR.concat(segments, junctions, out_path, NVENC_QP_FINAL, w, h, qa_dir)
 160 | +
 161 | +
 162 |  # ── Helpers for finding pre-rendered clip files ──
 163 |  
 164 |  def _find_clip_file(qa_dir, clip_id, cuts=None, sources_dir=None):
 165 | diff --git a/pipeline/render_vertical.py b/pipeline/render_vertical.py
 166 | index 57e9408d..19fa58eb 100644
 167 | --- a/pipeline/render_vertical.py
 168 | +++ b/pipeline/render_vertical.py
 169 | @@ -352,6 +352,60 @@ def reframe_letterbox(seg_path, output_path, seg_label, layout_cfg=None):
 170 |      return False, "letterbox"
 171 |  
 172 |  
 173 | +# ==============================================================
 174 | +# AUTO (DEC-2/DEC-5, 2026-11-11): per-shot plan from vertical_layout.classify
 175 | +# ==============================================================
 176 | +
 177 | +LETTERBOX_VF = ("split[main][bg];[bg]scale=-2:2400:flags=lanczos,crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
 178 | +                "boxblur=20:5,colorlevels=rimax=0.65:gimax=0.65:bimax=0.65[bgout];"
 179 | +                f"[main]scale={VERT_W}:-2:flags=lanczos[mainout];[bgout][mainout]overlay=(W-w)/2:(H-h)/2")
 180 | +
 181 | +
 182 | +def _shot_vf(shot, src_w, src_h):
 183 | +    """Filter for one shot of a 1920x1080 prepared clip -> 1080x1920 (approved filters reused)."""
 184 | +    cls = shot["class"]
 185 | +    if cls == "single":                                   # v2f fixed speaker-centred crop (Law 18a)
 186 | +        x = max(0, min(src_w - CROP_W, int(shot["face_cx"]) - CROP_W // 2))
 187 | +        return f"crop={CROP_W}:{CROP_H}:{x}:0,scale={VERT_W}:{VERT_H}:flags=lanczos"
 188 | +    if cls in ("stack2", "stack3"):                       # equal bands, left to right (Law 18b equal mode)
 189 | +        n = int(cls[-1])
 190 | +        bh = VERT_H // n
 191 | +        cw = src_w // n
 192 | +        ch = int(round(cw * bh / VERT_W))
 193 | +        parts = [f"split={n}" + "".join(f"[b{i}]" for i in range(n)) + ";"]
 194 | +        for i, (cx, cy) in enumerate(zip(shot["band_cx"], shot["band_cy"])):   # each face at 40 % of its band
 195 | +            x = max(0, min(src_w - cw, int(cx) - cw // 2))
 196 | +            y = max(0, min(src_h - ch, int(cy) - int(ch * 0.4)))
 197 | +            parts.append(f"[b{i}]crop={cw}:{ch}:{x}:{y},scale={VERT_W}:{bh}:flags=lanczos[s{i}];")
 198 | +        return "".join(parts) + "".join(f"[s{i}]" for i in range(n)) + f"vstack=inputs={n},pad={VERT_W}:{VERT_H}"
 199 | +    return LETTERBOX_VF                                   # screen / uncertain: safe frame (flagged)
 200 | +
 201 | +
 202 | +def reframe_auto(seg_path, output_path, seg_label, plan):
 203 | +    """Per-shot 9:16 from the PREPARED clip (lead-in pad and fades identical to 16:9). Video only is
 204 | +    re-composed; the clip's audio is copied unchanged. Returns (ok, layout_summary)."""
 205 | +    fps = plan["fps"]
 206 | +    graph, labels = [], []
 207 | +    for k, shot in enumerate(plan["shots"]):
 208 | +        a, b = int(round(shot["start"] * fps)), int(round(shot["end"] * fps))
 209 | +        graph.append(f"[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS,"
 210 | +                     f"{_shot_vf(shot, plan['width'], plan['height'])},setsar=1:1[v{k}]")
 211 | +        labels.append(f"[v{k}]")
 212 | +    graph.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[vout]")
 213 | +    r = subprocess.run([
 214 | +        "ffmpeg", "-y", "-i", seg_path, "-filter_complex", ";".join(graph),
 215 | +        "-map", "[vout]", "-map", "0:a", "-r", str(FPS),
 216 | +        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_INTERMEDIATE),
 217 | +        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", output_path,
 218 | +    ], capture_output=True, timeout=600)
 219 | +    if r.returncode != 0:
 220 | +        print(f"      ffmpeg error: {r.stderr.decode()[-400:]}")
 221 | +        return False, "auto"
 222 | +    summary = "+".join(f"{s['class']}[{s['start']:.2f}-{s['end']:.2f}]" for s in plan["shots"])
 223 | +    print(f"    Reframe auto {seg_label}: {summary}")
 224 | +    return True, f"auto:{summary}"
 225 | +
 226 | +
 227 |  # ==============================================================
 228 |  # VO VISUAL (native 9:16) — face-crop BG from preceding clip
 229 |  # ==============================================================
 230 | @@ -710,6 +764,10 @@ def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4"
 231 |                      ok, crop_rect = reframe_grid(trimmed, vert_path, clip_id, override)
 232 |                  else:
 233 |                      ok, crop_rect = reframe_single(trimmed, vert_path, clip_id, override)
 234 | +            elif layout == "auto":
 235 | +                # DEC-2/DEC-5: per-shot plan measured on the prepared clip (vertical_layout.classify)
 236 | +                src_clip = _find_clip_file(qa_dir, clip_id, cuts, paths["sources_dir"])
 237 | +                ok, crop_rect = reframe_auto(src_clip, vert_path, clip_id, override["plan"])
 238 |              elif layout == "letterbox":
 239 |                  # M21: Full 16:9 letterbox for unapproved channels
 240 |                  src_clip = _find_clip_file(qa_dir, clip_id, cuts, paths["sources_dir"])
 241 | @@ -718,12 +776,11 @@ def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4"
 242 |                  src_clip = _find_clip_file(qa_dir, clip_id, cuts, paths["sources_dir"])
 243 |                  ok, crop_rect = reframe_fixed_crop(src_clip, vert_path, clip_id)
 244 |  
 245 | -        if ok:
 246 | -            reframed[clip_id] = vert_path
 247 | -            crop_rects[clip_id] = crop_rect
 248 | -        else:
 249 | -            print(f"  WARNING: reframe failed for {clip_id}, using original")
 250 | -            reframed[clip_id] = src_clip
 251 | +        if not ok:
 252 | +            # M12 fail closed (2026-11-11): never drop a 16:9 clip into the 9:16 timeline
 253 | +            raise RuntimeError(f"STOP: vertical reframe failed for {clip_id} (layout {crop_rect})")
 254 | +        reframed[clip_id] = vert_path
 255 | +        crop_rects[clip_id] = crop_rect
 256 |  
 257 |      print(f"\n  Reframed: {list(reframed.keys())}")
 258 |  
 259 | @@ -852,17 +909,20 @@ def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4"
 260 |              f.write(f"file '{path}'\n")
 261 |  
 262 |      concat_raw = os.path.join(qa_dir, "concat_raw_vert.mp4")
 263 | -    r = subprocess.run([
 264 | -        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
 265 | -        "-vf", "setpts=PTS-STARTPTS",
 266 | -        "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
 267 | -        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_FINAL),
 268 | -        "-pix_fmt", "yuv420p",
 269 | -        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 270 | -        "-movflags", "+faststart", concat_raw,
 271 | -    ], capture_output=True, timeout=600)
 272 | -    if r.returncode != 0:
 273 | -        print(f"  ffmpeg stderr: {r.stderr.decode()[-500:]}")
 274 | +    from render16 import _transition_concat
 275 | +    timeline = _transition_concat(segment_dir, segments, concat_raw, VERT_W, VERT_H, qa_dir)
 276 | +    if timeline is None:                     # no TRANSITIONS.json: the frozen hard-cut concat (v2f)
 277 | +        r = subprocess.run([
 278 | +            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist,
 279 | +            "-vf", "setpts=PTS-STARTPTS",
 280 | +            "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
 281 | +            "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(NVENC_QP_FINAL),
 282 | +            "-pix_fmt", "yuv420p",
 283 | +            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 284 | +            "-movflags", "+faststart", concat_raw,
 285 | +        ], capture_output=True, timeout=600)
 286 | +        if r.returncode != 0:
 287 | +            print(f"  ffmpeg stderr: {r.stderr.decode()[-500:]}")
 288 |      concat_dur = get_duration(concat_raw)
 289 |      print(f"  Concat: {concat_dur:.2f}s")
 290 |  
 291 | @@ -877,6 +937,8 @@ def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4"
 292 |              shoutout_start = cumulative
 293 |              break
 294 |          cumulative += dur
 295 | +    if timeline is not None:
 296 | +        shoutout_start = next(e["start"] for e in timeline if e["label"] == "shoutout")
 297 |  
 298 |      print(f"  Watermark: 0 -> {shoutout_start:.2f}s")
 299 |  
 300 | @@ -986,12 +1048,15 @@ def render_9x16(segment_dir, qa_version=None, output_name="segment_vertical.mp4"
 301 |  
 302 |      cumul = 0.0
 303 |      manifest_segments = []
 304 | -    for label, path, seg_type in segments:
 305 | -        dur = get_duration(path)
 306 | +    tl = {e["label"]: e for e in timeline} if timeline is not None else {}
 307 | +    for label, path, seg_type in (segments if timeline is None else
 308 | +                                  [(e["label"], None, e["type"]) for e in timeline]):
 309 | +        dur = get_duration(path) if timeline is None else tl[label]["end"] - tl[label]["start"]
 310 | +        start = cumul if timeline is None else tl[label]["start"]
 311 |          seg_entry = {
 312 |              "label": label,
 313 | -            "start": round(cumul, 3),
 314 | -            "end": round(cumul + dur, 3),
 315 | +            "start": round(start, 3),
 316 | +            "end": round(start + dur, 3),
 317 |              "type": seg_type,
 318 |          }
 319 |  
 320 | diff --git a/pipeline/run_fresh.py b/pipeline/run_fresh.py
 321 | index 5265476b..9018ec19 100644
 322 | --- a/pipeline/run_fresh.py
 323 | +++ b/pipeline/run_fresh.py
 324 | @@ -351,12 +351,11 @@ def stage_validate(run):
 325 |          if rec is None:
 326 |              layout_errors.append((label, channel, "unknown channel"))
 327 |              continue
 328 | -        expected = "crop" if rec.get("layout_status") == "approved" else "letterbox"
 329 | -        if mode != expected:
 330 | -            layout_errors.append((label, channel, f"expected {expected}, got {mode!r}"))
 331 | +        if mode != "auto":                    # DEC-5: per-shot plan measured after prepare
 332 | +            layout_errors.append((label, channel, f"expected auto, got {mode!r}"))
 333 |      run.prov["layout_compat"] = {"segments": [(l, s.get("channel")) for l, s in segs],
 334 |                                   "vertical_overrides": ov,
 335 | -                                 "policy": "approved=crop; pending=letterbox"}
 336 | +                                 "policy": "DEC-5: auto (per-shot plan after prepare)"}
 337 |      if layout_errors:
 338 |          raise Hold(f"layout compatibility: {layout_errors}")
 339 |      for l, s in segs:
 340 | @@ -495,6 +494,60 @@ def stage_prepare(run, cuts):
 341 |          raise Hold(f"clip-preparation contract / edge-word check failed for {fails}")
 342 |  
 343 |  
 344 | +# ── transitions (Phase 3, DEC-4) ──
 345 | +
 346 | +TRANSITION_STYLE = "crossfade"   # DEC-4 production default: 6-frame dissolve + audio crossfade
 347 | +
 348 | +
 349 | +def write_transitions(run, style):
 350 | +    """TRANSITIONS.json for both renderers: style, each clip's measured genuine lead-in / tail (the
 351 | +    only time a transition may overlap) and channel (transitions only between different channels)."""
 352 | +    with open(os.path.join(run.dir, "cuts_final.json")) as f:
 353 | +        cuts = json.load(f)
 354 | +    with open(os.path.join(run.dir, "edl.json")) as f:
 355 | +        edl = json.load(f)
 356 | +    segs = {"hook": edl["hook"], **{f"clip_{c['index']:02d}": c for c in edl.get("clips", [])}}
 357 | +    lead_tail = {}
 358 | +    for c in cuts:
 359 | +        ht = L.head_tail(L.SourceAudio(os.path.join(run.dir, "qa", f"final_{c['clip_id']}.mp4")))
 360 | +        lead_tail[c["clip_id"]] = [ht["lead_ms"] / 1000.0, ht["tail_ms"] / 1000.0]
 361 | +    rec = {"style": style, "lead_tail": lead_tail,
 362 | +           "channels": {cid: seg.get("channel") for cid, seg in segs.items()}}
 363 | +    jdump(os.path.join(run.dir, "TRANSITIONS.json"), rec)
 364 | +    run.prov["transitions"] = rec
 365 | +
 366 | +
 367 | +# ── stage 8b: vertical layout (DEC-2 / DEC-5) ──
 368 | +
 369 | +def stage_layout(run, cuts):
 370 | +    """Measure every prepared clip per shot (vertical_layout.classify: SCRFD faces, fixed rules) and
 371 | +    record the plan: vertical_overrides.json (renderer input), VERTICAL_LAYOUT.json (all samples) and
 372 | +    edl.json segment 'vertical_layout' (shot classes, flagged safe frames) for gates and the caption."""
 373 | +    import vertical_layout as V
 374 | +    qa = os.path.join(run.dir, "qa")
 375 | +    with open(os.path.join(run.dir, "vertical_overrides.json")) as f:
 376 | +        ov = json.load(f)
 377 | +    with open(os.path.join(run.dir, "edl.json")) as f:
 378 | +        edl = json.load(f)
 379 | +    segs = {"hook": edl["hook"], **{f"clip_{c['index']:02d}": c for c in edl.get("clips", [])}}
 380 | +    plans = {}
 381 | +    for c in cuts:
 382 | +        cid = c["clip_id"]
 383 | +        plan = V.classify(os.path.join(qa, f"final_{cid}.mp4"))
 384 | +        plans[cid] = plan
 385 | +        ov[cid] = {"layout": "auto", "plan": {k: v for k, v in plan.items() if k != "samples"}}
 386 | +        segs[cid]["vertical_layout"] = {"shots": [{k: sh[k] for k in ("start", "end", "class", "flagged")}
 387 | +                                                  for sh in plan["shots"]], "flagged": plan["flagged"]}
 388 | +        print(f"  {cid}: " + " | ".join(f"{sh['class']} {sh['start']:.2f}-{sh['end']:.2f}"
 389 | +                                        + (" (SAFE FRAME, flagged)" if sh["flagged"] else "")
 390 | +                                        for sh in plan["shots"]))
 391 | +    jdump(os.path.join(run.dir, "vertical_overrides.json"), ov)
 392 | +    jdump(os.path.join(run.dir, "VERTICAL_LAYOUT.json"), plans)
 393 | +    jdump(os.path.join(run.dir, "edl.json"), edl)
 394 | +    run.prov["vertical_layout"] = {cid: [(sh["class"], sh["start"], sh["end"]) for sh in p["shots"]]
 395 | +                                   for cid, p in plans.items()}
 396 | +
 397 | +
 398 |  # ── stage 9: render ──
 399 |  
 400 |  FALLBACK_RE = re.compile(r"reframe failed for (\S+), using original")
 401 | @@ -508,6 +561,7 @@ def stage_render(run):
 402 |      from config import resolve_paths
 403 |  
 404 |      paths = resolve_paths(run.dir)
 405 | +    write_transitions(run, TRANSITION_STYLE)
 406 |      build_shoutout(run.dir, None, "16x9")
 407 |      build_shoutout(run.dir, None, "9x16")
 408 |      preflight_check(run.dir)
 409 | @@ -551,6 +605,23 @@ def stage_render(run):
 410 |          "outro conform failed" in log9.lower()
 411 |      fb["fallback_occurred"] = bool(fb["log_hits"] or fb["structural"])
 412 |      run.prov["vertical_fallback_check"] = fb
 413 | +
 414 | +    # G4 input (DEC-2/DEC-5): each talking-head entry carries its clip-level layout. A clip with any
 415 | +    # screen/uncertain shot gets G4's existing 'screenshare' rule here; the per-shot G4 in stage_gates
 416 | +    # applies the face rules to every talking-head shot, and G4s checks every label against the picture.
 417 | +    with open(os.path.join(run.dir, "VERTICAL_LAYOUT.json")) as f:
 418 | +        plans = json.load(f)
 419 | +    for man in (man16, man9):
 420 | +        with open(man) as f:
 421 | +            m = json.load(f)
 422 | +        for sg in m["segments"]:
 423 | +            plan = plans.get(sg["label"]) if sg.get("type") == "talking_head" else None
 424 | +            if plan:
 425 | +                classes = {sh["class"] for sh in plan["shots"]}
 426 | +                cls = classes.pop() if len(classes) == 1 else "mixed"
 427 | +                sg["layout"] = {"single": "single", "stack2": "2face", "stack3": "3face"}.get(cls, "screenshare")
 428 | +                sg["source_faces"] = int(cls[-1]) if cls.startswith("stack") else 1
 429 | +        jdump(man, m)
 430 |      return final16, man16, final9, man9
 431 |  
 432 |  
 433 | @@ -686,6 +757,23 @@ def stage_gates(run, final16, man16, final9, man9):
 434 |                            "last_segment": last.get("label"), "conform_fallback": fallback}
 435 |          rows[fmt].update(tail_rows(res["G9_tail"]["pass"], fallback))
 436 |  
 437 | +    # G4 per shot + G4s layout truth (DEC-2 / DEC-5)
 438 | +    import vertical_layout as V
 439 | +    with open(os.path.join(run.dir, "VERTICAL_LAYOUT.json")) as f:
 440 | +        plans = json.load(f)
 441 | +    prepared = {cid: os.path.join(qa, f"final_{cid}.mp4") for cid in plans}
 442 | +    g4_shots, g4s = {}, {}
 443 | +    for fmt, final, man, sgs in (("16x9", final16, man16, segs16), ("9x16", final9, man9, segs9)):
 444 | +        g4dir = os.path.join(qa, f"g4_shots_{fmt}")
 445 | +        os.makedirs(g4dir, exist_ok=True)
 446 | +        with open(man) as f:
 447 | +            shout = json.load(f).get("shoutout_start", 0)
 448 | +        ok, g4_shots[fmt] = qa_gates.gate_g4(final, V.per_shot_manifest(sgs, plans), fmt, shout, g4dir)
 449 | +        rows[fmt]["G4_faces_per_shot"] = _status(ok)
 450 | +        ok, g4s[fmt] = V.gate_g4s(plans, prepared, vert_final=final9 if fmt == "9x16" else None,
 451 | +                                  vert_segments=segs9 if fmt == "9x16" else None)
 452 | +        rows[fmt]["G4s_layout_truth"] = _status(ok)
 453 | +
 454 |      # G16 SENTENCE_BOUNDARY: re-run on the final cut state (format-independent; same row in both)
 455 |      g16_ok, g16 = L.gate_g16(run.dir)
 456 |      for fmt in ("16x9", "9x16"):
 457 | @@ -699,6 +787,26 @@ def stage_gates(run, final16, man16, final9, man9):
 458 |      rows["16x9"]["G17_onset_tail"] = _status(g17a_ok and g17b16_ok)
 459 |      rows["9x16"]["G17_onset_tail"] = _status(g17a_ok and g17b9_ok)
 460 |  
 461 | +    # G18 WORD-FOR-WORD (mission 4a): every clip's first/last words are its locked sentences' and its
 462 | +    # words are exactly those of the source span it was cut from (both finals; whisper on GPU0)
 463 | +    import word_diff as WD
 464 | +    with open(os.path.join(run.dir, "edl.json")) as f:
 465 | +        edl_now = json.load(f)
 466 | +    locks = {"hook": edl_now["hook"].get("selection_lock"),
 467 | +             **{f"clip_{c['index']:02d}": c.get("selection_lock") for c in edl_now.get("clips", [])}}
 468 | +    g18_clips = {c["clip_id"]: {"lock_text": (locks.get(c["clip_id"]) or {}).get("text", ""),
 469 | +                                "source": os.path.join(run.dir, "sources", f"{c['video_id']}.mp4"),
 470 | +                                "cut_in": c["cut_in"], "cut_out": c["cut_out"]} for c in cuts}
 471 | +    missing = [cid for cid, c in g18_clips.items() if not c["lock_text"]]
 472 | +    tr = WD.Transcriber()
 473 | +    g18 = {}
 474 | +    for fmt, final, sgs in (("16x9", final16, segs16), ("9x16", final9, segs9)):
 475 | +        ok, g18[fmt] = WD.gate_g18(final, sgs, g18_clips, transcriber=tr)
 476 | +        rows[fmt]["G18_word_for_word"] = _status(ok and not missing)
 477 | +    del tr
 478 | +    if missing:
 479 | +        g18["missing_selection_lock"] = missing
 480 | +
 481 |      fb = run.prov["vertical_fallback_check"]
 482 |      rows["9x16"]["vertical_silent_fallback"] = "FAIL (fallback occurred)" if fb["fallback_occurred"] \
 483 |          else "PASS (no fallback)"
 484 | @@ -706,7 +814,8 @@ def stage_gates(run, final16, man16, final9, man9):
 485 |      gates_out = {"rows": rows, "flags": flags, "limitations": limits,
 486 |                   "G11": g11, "G14_16x9": g14_16, "G14_9x16": g14_9, "G14c": g14c,
 487 |                   "G15_16x9": g15_16, "G15_9x16": g15_9, "G8": g8_report, "G9": g9_report, "G16": g16,
 488 | -                 "G17": {"prepared": g17a, "16x9": g17b16, "9x16": g17b9},
 489 | +                 "G17": {"prepared": g17a, "16x9": g17b16, "9x16": g17b9}, "G18": g18,
 490 | +                 "G4_per_shot": g4_shots, "G4s": g4s,
 491 |                   "run_gates_overall": {"16x9": ok16, "9x16": ok9}}
 492 |      jdump(os.path.join(run.dir, "GATE_REPORT.json"), gates_out)
 493 |      run.prov["gates"] = {"rows": rows, "flags": flags, "limitations": limits}
 494 | @@ -893,9 +1002,13 @@ def main():
 495 |          run.stage("sentence_law", lambda: stage_sentence_law(run))
 496 |          run.stage("voice", lambda: stage_voice(run))
 497 |          run.stage("prepare", lambda: stage_prepare(run, cuts))
 498 | +        run.stage("layout", lambda: stage_layout(run, cuts))
 499 |          final16, man16, final9, man9 = run.stage("render", lambda: stage_render(run))
 500 |          rows, flags, limits = run.stage("gates", lambda: stage_gates(run, final16, man16,
 501 |                                                                        final9, man9))
 502 | +        # mission 4a / DEC-8: the automated verification pack (words, joins, credits) for the drop
 503 | +        import verify_pack
 504 | +        run.stage("verify", lambda: verify_pack.build(run.dir))
 505 |          v16, bad16 = verdict_for(rows["16x9"])
 506 |          v9, bad9 = verdict_for(rows["9x16"])
 507 |          run.prov["verdicts"] = {"16x9": v16, "9x16": v9}
 508 | diff --git a/pipeline/select_passages.py b/pipeline/select_passages.py
 509 | index df63a787..e1dcb327 100644
 510 | --- a/pipeline/select_passages.py
 511 | +++ b/pipeline/select_passages.py
 512 | @@ -129,27 +129,16 @@ def _generate_vo_script(keyword, hook_text, clips, channels):
 513 |  
 514 |  
 515 |  def build_vertical_overrides(hook_seg, clip_segs, registry=None):
 516 | -    """vertical_overrides.json content — default letterbox for all (M21).
 517 | -    Channels with approved hand tables use those ('crop'); others get letterbox.
 518 | -    Shared by AUTO (select_and_build_edl) and PINNED (pinned.build_edl)."""
 519 | -    if registry is None:
 520 | -        registry = []
 521 | -        channels_path = os.path.join(PIPELINE_DIR, "channels.json")
 522 | -        if os.path.exists(channels_path):
 523 | -            with open(channels_path) as f:
 524 | -                registry = json.load(f)
 525 | -    approved_channels = set()
 526 | -    for ch in registry:
 527 | -        if ch.get("layout_status") == "approved":
 528 | -            approved_channels.add(ch.get("display_name", ""))
 529 | -
 530 | +    """vertical_overrides.json content. DEC-5 (orchestrator, delegated by PBX, 2026-11-11): every
 531 | +    segment, approved or pending channel, gets layout 'auto' - the approved speaker-centred reframe,
 532 | +    stacked bands for 2-3 people, the safe frame only for a shared screen or an unidentifiable speaker
 533 | +    (flagged). The per-shot plan is measured on the prepared clip in run_fresh's 'layout' stage
 534 | +    (vertical_layout.py). M21's letterbox-by-registry-status default is retired. `registry` is kept
 535 | +    for call compatibility. Shared by AUTO (select_and_build_edl) and PINNED (pinned.build_edl)."""
 536 |      overrides = {}
 537 |      for seg in [hook_seg] + clip_segs:
 538 |          label = "hook" if seg is hook_seg else f"clip_{seg['index']:02d}"
 539 | -        if seg["channel"] in approved_channels:
 540 | -            overrides[label] = {"layout": "crop"}  # Use approved layout
 541 | -        else:
 542 | -            overrides[label] = {"layout": "letterbox"}  # M21
 543 | +        overrides[label] = {"layout": "auto"}
 544 |      return overrides
 545 |  
 546 |  
 547 | diff --git a/pipeline/telegram.py b/pipeline/telegram.py
 548 | index 93e755b6..22d85afd 100644
 549 | --- a/pipeline/telegram.py
 550 | +++ b/pipeline/telegram.py
 551 | @@ -115,3 +115,109 @@ def _send_via_requests(final_16, final_9, segment_dir):
 552 |              print(f"  Telegram {label}: message_id={data['result']['message_id']}")
 553 |          else:
 554 |              raise RuntimeError(f"STOP: Telegram send failed ({label}): {data}")
 555 | +
 556 | +
 557 | +# ==============================================================
 558 | +# run_fresh drops (mission 4a / DEC-8, 2026-11-11): both aspects, the verdict in the caption
 559 | +# ==============================================================
 560 | +
 561 | +HOLD_OK = "HOLD FOR APPROVAL - all gates passed, no waivers"
 562 | +REVIEW = "REVIEW ONLY"
 563 | +CAPTION_MAX = 1024                       # Telegram caption limit
 564 | +DIMS = {"16x9": (1920, 1080), "9x16": (1080, 1920)}
 565 | +
 566 | +
 567 | +def gate_status(run_dir):
 568 | +    """(all_pass, failing) from GATE_REPORT.json: every row of both formats must read PASS. Placeholder rows
 569 | +    '<gate>(run_gates)' point to the real row (G11 parity in 9x16) and are not results themselves."""
 570 | +    with open(os.path.join(run_dir, "GATE_REPORT.json")) as f:
 571 | +        rows = json.load(f)["rows"]
 572 | +    failing = [f"{k} ({fmt}): {v[:60]}" for fmt in ("16x9", "9x16") for k, v in rows.get(fmt, {}).items()
 573 | +               if not k.endswith("(run_gates)") and not str(v).startswith("PASS")]
 574 | +    if not rows.get("16x9") or not rows.get("9x16"):
 575 | +        failing.append("gate rows missing for a format")
 576 | +    return not failing, failing
 577 | +
 578 | +
 579 | +def build_caption(run_dir, fmt, option=None):
 580 | +    """Verdict line first: HOLD FOR APPROVAL only when every gate passed with no waiver AND the
 581 | +    automated verification pack is complete; otherwise REVIEW ONLY with the failing list."""
 582 | +    import vertical_layout
 583 | +    ok, failing = gate_status(run_dir)
 584 | +    vpath = os.path.join(run_dir, "VERIFY", "VERIFICATION.json")
 585 | +    pack_ok = os.path.exists(vpath) and json.load(open(vpath)).get("complete") is True
 586 | +    if not pack_ok:
 587 | +        failing.append("verification pack missing or incomplete")
 588 | +    with open(os.path.join(run_dir, "edl.json")) as f:
 589 | +        edl = json.load(f)
 590 | +    head = HOLD_OK if (ok and pack_ok) else f"{REVIEW} - {len(failing)} failing"
 591 | +    if option:
 592 | +        head = f"OPTION {option} (transition choice, not a release candidate) | {head}"
 593 | +    lines = [head, f"{os.path.basename(os.path.normpath(run_dir))} | {fmt} {DIMS[fmt][0]}x{DIMS[fmt][1]}",
 594 | +             f"Story: {edl.get('topic', '')}",
 595 | +             "Clips: " + ", ".join([edl["hook"].get("channel", "?")] + [c.get("channel", "?") for c in edl.get("clips", [])])]
 596 | +    note = vertical_layout.layout_note(edl) if fmt == "9x16" else ""
 597 | +    if note:
 598 | +        lines.append(note)
 599 | +    if failing:
 600 | +        lines.append("Failing: " + "; ".join(failing))
 601 | +    cap = "\n".join(lines)
 602 | +    return cap if len(cap) <= CAPTION_MAX else cap[:CAPTION_MAX - 20] + " ...(see GATE_REPORT)"
 603 | +
 604 | +
 605 | +def _dims(path):
 606 | +    import subprocess
 607 | +    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
 608 | +                        "stream=width,height:format=duration", "-of", "json", path],
 609 | +                       capture_output=True, text=True, check=True, timeout=30)
 610 | +    j = json.loads(r.stdout)
 611 | +    return int(j["streams"][0]["width"]), int(j["streams"][0]["height"]), float(j["format"]["duration"])
 612 | +
 613 | +
 614 | +def deliver_run(run_dir, option=None, send=None, sheets=True):
 615 | +    """Send a run_fresh run's two finals to the approval chat (never publishing), each with its caption,
 616 | +    plus (sheets=True) the verification pack's contact sheets; transition options send the two finals only.
 617 | +    send(kind, path, fields) -> message_id (tests inject it).
 618 | +    Writes TELEGRAM_DELIVERY.json. Raises on a missing/misdimensioned final (fail closed)."""
 619 | +    import hashlib
 620 | +    send = send or _send_bot_api
 621 | +    finals = {"16x9": os.path.join(run_dir, "out", "segment.mp4"),
 622 | +              "9x16": os.path.join(run_dir, "out", "segment_vertical.mp4")}
 623 | +    record = {"option": option, "messages": []}
 624 | +    for fmt, path in finals.items():
 625 | +        if not os.path.exists(path):
 626 | +            raise FileNotFoundError(f"STOP: final output missing: {path}")
 627 | +        w, h, dur = _dims(path)
 628 | +        if (w, h) != DIMS[fmt]:
 629 | +            raise RuntimeError(f"STOP: {fmt} final is {w}x{h}, expected {DIMS[fmt][0]}x{DIMS[fmt][1]}")
 630 | +        cap = build_caption(run_dir, fmt, option)
 631 | +        mid = send("video", path, {"caption": cap, "width": w, "height": h, "duration": int(round(dur)),
 632 | +                                   "supports_streaming": "true"})
 633 | +        record["messages"].append({"format": fmt, "message_id": mid, "caption": cap,
 634 | +                                   "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()})
 635 | +    for sheet in (("joins_16x9.jpg", "joins_9x16.jpg", "credits_16x9.jpg", "credits_9x16.jpg") if sheets else ()):
 636 | +        p = os.path.join(run_dir, "VERIFY", sheet)
 637 | +        if os.path.exists(p):
 638 | +            mid = send("photo", p, {"caption": f"verification pack: {sheet[:-4]}"})
 639 | +            record["messages"].append({"sheet": sheet, "message_id": mid})
 640 | +    with open(os.path.join(run_dir, f"TELEGRAM_DELIVERY{'_' + option if option else ''}.json"), "w") as f:
 641 | +        json.dump(record, f, indent=2)
 642 | +    return record
 643 | +
 644 | +
 645 | +def _send_bot_api(kind, path, fields):
 646 | +    """One sendVideo / sendPhoto to the approval chat (M16 path; credentials never printed)."""
 647 | +    import requests
 648 | +    sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
 649 | +    from relay import get_key
 650 | +    tok, chat = get_key("TELEGRAM_BOT_TOKEN"), get_key("TELEGRAM_CHAT_ID")
 651 | +    if not tok or not chat:
 652 | +        raise RuntimeError("STOP: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
 653 | +    method, field = ("sendVideo", "video") if kind == "video" else ("sendPhoto", "photo")
 654 | +    with open(path, "rb") as fh:
 655 | +        resp = requests.post(f"https://api.telegram.org/bot{tok}/{method}", data={"chat_id": chat, **fields},
 656 | +                             files={field: fh}, timeout=600)
 657 | +    data = resp.json()
 658 | +    if not data.get("ok"):
 659 | +        raise RuntimeError(f"STOP: Telegram {method} failed: {data.get('description')}")
 660 | +    return data["result"]["message_id"]
 661 | diff --git a/pipeline/test_telegram_delivery.py b/pipeline/test_telegram_delivery.py
 662 | new file mode 100644
 663 | index 00000000..17fb245e
 664 | --- /dev/null
 665 | +++ b/pipeline/test_telegram_delivery.py
 666 | @@ -0,0 +1,121 @@
 667 | +#!/usr/bin/env python3
 668 | +"""Mission 4a / DEC-8 delivery contract: 'HOLD FOR APPROVAL - all gates passed, no waivers' only when every
 669 | +gate row of both formats is PASS and the automated verification pack is complete; otherwise 'REVIEW ONLY'
 670 | +with the failing list. Both aspects, real dimensions; safe frames named in the 9:16 caption. No network:
 671 | +the sender is injected. Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_telegram_delivery.py"""
 672 | +import json
 673 | +import os
 674 | +import shutil
 675 | +import subprocess
 676 | +import sys
 677 | +import tempfile
 678 | +import unittest
 679 | +
 680 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
 681 | +sys.path.insert(0, PIPELINE)
 682 | +
 683 | +import telegram as TG  # noqa: E402
 684 | +
 685 | +ROWS = {"16x9": {"G1_voice": "PASS", "G11_parity(run_gates)": "NOT RUN BY run_gates (no horiz) — see G11 below",
 686 | +                 "G16_sentence_boundary": "PASS", "G18_word_for_word": "PASS"},
 687 | +        "9x16": {"G1_voice": "PASS", "G11_parity(run_gates)": "NOT RUN BY run_gates (no horiz) — see G11 below",
 688 | +                 "G11_parity": "PASS", "G4s_layout_truth": "PASS", "G18_word_for_word": "PASS"}}
 689 | +
 690 | +
 691 | +class TestDelivery(unittest.TestCase):
 692 | +    @classmethod
 693 | +    def setUpClass(cls):
 694 | +        cls.media = tempfile.mkdtemp(prefix="tgm_")
 695 | +        for name, (w, h) in (("segment.mp4", (1920, 1080)), ("segment_vertical.mp4", (1080, 1920)),
 696 | +                             ("wrong.mp4", (1280, 720))):
 697 | +            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r=24:d=1",
 698 | +                            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
 699 | +                            os.path.join(cls.media, name)], check=True)
 700 | +
 701 | +    @classmethod
 702 | +    def tearDownClass(cls):
 703 | +        shutil.rmtree(cls.media, ignore_errors=True)
 704 | +
 705 | +    def run_dir(self, rows=ROWS, pack_complete=True, flagged=False):
 706 | +        rd = tempfile.mkdtemp(prefix="tgr_")
 707 | +        self.addCleanup(shutil.rmtree, rd, True)
 708 | +        os.makedirs(os.path.join(rd, "out"))
 709 | +        os.makedirs(os.path.join(rd, "VERIFY"))
 710 | +        for name in ("segment.mp4", "segment_vertical.mp4"):
 711 | +            shutil.copy(os.path.join(self.media, name), os.path.join(rd, "out", name))
 712 | +        json.dump({"rows": rows}, open(os.path.join(rd, "GATE_REPORT.json"), "w"))
 713 | +        json.dump({"complete": pack_complete}, open(os.path.join(rd, "VERIFY", "VERIFICATION.json"), "w"))
 714 | +        shot = {"start": 0.0, "end": 9.4, "class": "screen" if flagged else "single", "flagged": flagged}
 715 | +        json.dump({"topic": "Bitcoin price dip",
 716 | +                   "hook": {"channel": "Yahoo Finance", "vertical_layout": {"shots": [shot], "flagged": flagged}},
 717 | +                   "clips": [{"index": 1, "channel": "Natalie Brunell",
 718 | +                              "vertical_layout": {"shots": [dict(shot, **{"class": "single", "flagged": False})],
 719 | +                                                  "flagged": False}}]},
 720 | +                  open(os.path.join(rd, "edl.json"), "w"))
 721 | +        return rd
 722 | +
 723 | +    def deliver(self, rd, option=None):
 724 | +        sent = []
 725 | +        rec = TG.deliver_run(rd, option=option, send=lambda kind, path, fields: sent.append(
 726 | +            (kind, os.path.basename(path), fields)) or len(sent))
 727 | +        return rec, sent
 728 | +
 729 | +    def test_all_pass_with_complete_pack_is_hold_for_approval_in_both_aspects(self):
 730 | +        rd = self.run_dir()
 731 | +        rec, sent = self.deliver(rd)
 732 | +        vids = [s for s in sent if s[0] == "video"]
 733 | +        self.assertEqual([(s[1], s[2]["width"], s[2]["height"]) for s in vids],
 734 | +                         [("segment.mp4", 1920, 1080), ("segment_vertical.mp4", 1080, 1920)])
 735 | +        for s in vids:
 736 | +            self.assertTrue(s[2]["caption"].startswith(TG.HOLD_OK), s[2]["caption"])
 737 | +            self.assertNotIn("Failing", s[2]["caption"])
 738 | +        written = json.load(open(os.path.join(rd, "TELEGRAM_DELIVERY.json")))
 739 | +        self.assertEqual([m["format"] for m in written["messages"] if "format" in m], ["16x9", "9x16"])
 740 | +
 741 | +    def test_any_failing_row_is_review_only_with_the_list(self):
 742 | +        rows = json.loads(json.dumps(ROWS))
 743 | +        rows["9x16"]["G4s_layout_truth"] = "FAIL"
 744 | +        _, sent = self.deliver(self.run_dir(rows))
 745 | +        cap = sent[0][2]["caption"]
 746 | +        self.assertTrue(cap.startswith("REVIEW ONLY - 1 failing"), cap)
 747 | +        self.assertIn("G4s_layout_truth (9x16): FAIL", cap)
 748 | +
 749 | +    def test_a_waiver_is_not_a_pass(self):
 750 | +        rows = json.loads(json.dumps(ROWS))
 751 | +        rows["16x9"]["G8_sharpness"] = "FLAG/LIMITED (absolute floor vs soft source)"
 752 | +        _, sent = self.deliver(self.run_dir(rows))
 753 | +        self.assertTrue(sent[0][2]["caption"].startswith("REVIEW ONLY"), sent[0][2]["caption"])
 754 | +
 755 | +    def test_incomplete_verification_pack_is_review_only(self):
 756 | +        _, sent = self.deliver(self.run_dir(pack_complete=False))
 757 | +        self.assertIn("verification pack missing or incomplete", sent[0][2]["caption"])
 758 | +        self.assertTrue(sent[0][2]["caption"].startswith("REVIEW ONLY"))
 759 | +
 760 | +    def test_safe_frame_is_named_in_the_vertical_caption(self):
 761 | +        _, sent = self.deliver(self.run_dir(flagged=True))
 762 | +        vert = [s for s in sent if s[1] == "segment_vertical.mp4"][0][2]["caption"]
 763 | +        self.assertIn("9:16 SAFE FRAME hook (Yahoo Finance): layout=screen 0.00-9.40 s", vert)
 764 | +
 765 | +    def test_option_label_comes_first(self):
 766 | +        _, sent = self.deliver(self.run_dir(), option="B")
 767 | +        self.assertTrue(sent[0][2]["caption"].startswith("OPTION B (transition choice"), sent[0][2]["caption"])
 768 | +
 769 | +    def test_sheets_are_sent_with_the_main_drop_only(self):
 770 | +        rd = self.run_dir()
 771 | +        for name in ("joins_16x9.jpg", "credits_9x16.jpg"):
 772 | +            open(os.path.join(rd, "VERIFY", name), "wb").write(b"\xff\xd8\xff\xd9")
 773 | +        _, sent = self.deliver(rd)
 774 | +        self.assertEqual([s[1] for s in sent if s[0] == "photo"], ["joins_16x9.jpg", "credits_9x16.jpg"])
 775 | +        sent2 = []
 776 | +        TG.deliver_run(rd, option="A", sheets=False, send=lambda k, p, f: sent2.append(k) or 1)
 777 | +        self.assertEqual(sent2, ["video", "video"])
 778 | +
 779 | +    def test_wrong_dimensions_stop(self):
 780 | +        rd = self.run_dir()
 781 | +        shutil.copy(os.path.join(self.media, "wrong.mp4"), os.path.join(rd, "out", "segment.mp4"))
 782 | +        with self.assertRaises(RuntimeError):
 783 | +            self.deliver(rd)
 784 | +
 785 | +
 786 | +if __name__ == "__main__":
 787 | +    unittest.main()
 788 | diff --git a/pipeline/test_transitions.py b/pipeline/test_transitions.py
 789 | new file mode 100644
 790 | index 00000000..a7a5c527
 791 | --- /dev/null
 792 | +++ b/pipeline/test_transitions.py
 793 | @@ -0,0 +1,194 @@
 794 | +#!/usr/bin/env python3
 795 | +"""Phase 3 / DEC-4 (2026-11-11): transitions only between DIFFERENT channels, never at the open, never
 796 | +over speech (bounded by the measured tail of A and lead-in of B), picture and sound frame-locked, sound
 797 | +design below speech. Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_transitions.py"""
 798 | +import json
 799 | +import os
 800 | +import shutil
 801 | +import subprocess
 802 | +import sys
 803 | +import tempfile
 804 | +import unittest
 805 | +
 806 | +import numpy as np
 807 | +
 808 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
 809 | +sys.path.insert(0, PIPELINE)
 810 | +
 811 | +import transitions as TR  # noqa: E402
 812 | +
 813 | +SEGS = [("hook", "h.mp4", "talking_head"), ("clip_01", "c1.mp4", "talking_head"),
 814 | +        ("clip_02", "c2.mp4", "talking_head"), ("shoutout", "s.mp4", "shoutout"), ("outro", "o.mp4", "outro")]
 815 | +CH = {"hook": "DataDash", "clip_01": "Natalie Brunell", "clip_02": "Yahoo Finance"}
 816 | +LT = {"hook": (0.30, 0.40), "clip_01": (0.35, 0.50), "clip_02": (0.30, 0.45)}   # (lead_s, tail_s)
 817 | +
 818 | +
 819 | +class TestPlan(unittest.TestCase):
 820 | +    def test_dissolves_only_between_different_channels_and_talking_heads(self):
 821 | +        j = TR.plan(SEGS, CH, LT, "crossfade")
 822 | +        self.assertEqual([(x["after"], x["frames"], x["kind"]) for x in j], [(0, 6, "dissolve"), (1, 6, "dissolve")])
 823 | +        same = dict(CH, clip_01="DataDash")
 824 | +        self.assertEqual([x["after"] for x in TR.plan(SEGS, same, LT, "crossfade")], [1])
 825 | +        self.assertTrue(all(x["after"] < 2 for x in j))          # never into credits / outro
 826 | +
 827 | +    def test_never_over_speech(self):
 828 | +        # clip_01 has only 0.10 s of genuine lead-in: the dissolve shrinks to 2 frames (0.083 s)
 829 | +        lt = dict(LT, clip_01=(0.10, 0.50))
 830 | +        j = TR.plan(SEGS, CH, lt, "crossfade")
 831 | +        self.assertEqual(j[0]["frames"], 2)
 832 | +        self.assertLessEqual(j[0]["frames"] / TR.FPS, min(LT["hook"][1], 0.10))
 833 | +        # under 2 frames of non-speech: a hard cut, never a transition over a word
 834 | +        lt = dict(LT, clip_01=(0.05, 0.50))
 835 | +        self.assertEqual([x["after"] for x in TR.plan(SEGS, CH, lt, "crossfade")], [1])
 836 | +
 837 | +    def test_A_splits_the_dip_across_the_cut(self):
 838 | +        lt = dict(LT, clip_01=(0.10, 0.50))                     # each side fades at most its own silence
 839 | +        j = TR.plan(SEGS, CH, lt, "A")[0]
 840 | +        self.assertEqual((j["kind"], j["frames"]), ("dip", 4))
 841 | +        self.assertLessEqual(j["frames"] / 2 / TR.FPS, 0.10)
 842 | +
 843 | +    def test_C_is_a_short_insert(self):
 844 | +        j = TR.plan(SEGS, CH, LT, "C")
 845 | +        self.assertEqual([(x["after"], x["kind"]) for x in j], [(0, "insert"), (1, "insert")])
 846 | +        self.assertLess(TR.WIPE_FRAMES / TR.FPS, 0.35)
 847 | +
 848 | +    def test_unknown_style_refused(self):
 849 | +        with self.assertRaises(ValueError):
 850 | +            TR.plan(SEGS, CH, LT, "D")
 851 | +
 852 | +
 853 | +class TestSoundDesign(unittest.TestCase):
 854 | +    def test_thumps_peak_at_the_declared_level_with_micro_fades(self):
 855 | +        tmp = tempfile.mkdtemp(prefix="thump_")
 856 | +        self.addCleanup(shutil.rmtree, tmp, True)
 857 | +        for name, x in (("t.wav", TR.thump()), ("dt.wav", TR.double_thump())):
 858 | +            p = os.path.join(tmp, name)
 859 | +            TR.write_wav(p, x, TR.THUMP_PEAK_DBFS)
 860 | +            import wave
 861 | +            with wave.open(p) as f:
 862 | +                a = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float64) / 32767
 863 | +            self.assertAlmostEqual(20 * np.log10(np.max(np.abs(a))), TR.THUMP_PEAK_DBFS, delta=0.1)
 864 | +            self.assertLess(abs(a[0]), 1e-3)
 865 | +            self.assertLess(abs(a[-1]), 1e-3)
 866 | +
 867 | +    def test_wipe_is_a_red_line_sweeping_on_black(self):
 868 | +        # measured 2026-11-11 at the render sizes: 94.5 % (16:9) / 95.7 % (9:16) black, median pixel 0
 869 | +        for w, h in ((1920, 1080), (1080, 1920)):
 870 | +            frames = [np.asarray(f).astype(int) for f in TR.wipe_frames(w, h)]
 871 | +            self.assertEqual(len(frames), TR.WIPE_FRAMES)
 872 | +            last = frames[-1]
 873 | +            self.assertEqual(int(np.median(last.max(axis=2))), 0)                 # on black
 874 | +            self.assertGreater((last.max(axis=2) < 40).mean(), 0.90)
 875 | +            red = [((f[..., 0] > 150) & (f[..., 1] < 90)).mean() for f in frames]
 876 | +            self.assertGreater(red[-1], 0.003)                                    # the red ECG line
 877 | +            self.assertTrue(all(a < b for a, b in zip(red, red[1:])), red)        # sweeping in
 878 | +
 879 | +
 880 | +RAMP = "nullsrc=s=320x180:r=24:d={dur},format=gray,geq=lum='16+3*N'"   # luma identifies every frame
 881 | +
 882 | +
 883 | +def _seg(path, colour, freq, dur, speech):
 884 | +    """Synthetic segment: a solid colour (or RAMP), a tone only inside `speech` (start, end), silence else."""
 885 | +    video = RAMP.format(dur=dur) if colour == "ramp" else f"color=c={colour}:s=320x180:r=24:d={dur}"
 886 | +    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", video,
 887 | +                    "-f", "lavfi", "-i", f"sine=f={freq}:r=48000:d={dur}",
 888 | +                    "-filter_complex", f"[1:a]volume='between(t,{speech[0]},{speech[1]})':eval=frame,"
 889 | +                                       "aformat=channel_layouts=stereo[a]",
 890 | +                    "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
 891 | +                    "-c:a", "aac", "-b:a", "192k", "-shortest", path], check=True)
 892 | +    return path
 893 | +
 894 | +
 895 | +def _lumas(path):
 896 | +    import cv2
 897 | +    cap, out = cv2.VideoCapture(path), []
 898 | +    while True:
 899 | +        ok, f = cap.read()
 900 | +        if not ok:
 901 | +            return np.array(out)
 902 | +        out.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).mean())
 903 | +
 904 | +
 905 | +def _onset(path, t0, t1):
 906 | +    """First 10 ms window in [t0, t1] whose RMS rises above -40 dBFS (the tone's start)."""
 907 | +    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", path, "-f", "f32le",
 908 | +                        "-ac", "1", "-ar", "48000", "-"], capture_output=True, check=True)
 909 | +    a = np.frombuffer(r.stdout, np.float32)
 910 | +    for k in range(0, len(a) - 480, 480):
 911 | +        if 20 * np.log10(np.sqrt(np.mean(a[k:k + 480] ** 2)) + 1e-12) > -40:
 912 | +            return t0 + k / 48000
 913 | +    return None
 914 | +
 915 | +
 916 | +def _probe(path):
 917 | +    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-show_entries",
 918 | +                        "stream=codec_type,nb_read_packets,duration", "-of", "json", path],
 919 | +                       capture_output=True, text=True, check=True)
 920 | +    return {s["codec_type"]: s for s in json.loads(r.stdout)["streams"]}
 921 | +
 922 | +
 923 | +@unittest.skipUnless(os.environ.get("CUDA_VISIBLE_DEVICES") == "0", "NVENC concat needs GPU0")
 924 | +class TestConcat(unittest.TestCase):
 925 | +    """Three 3 s segments, channels A, B, B: one dissolve (A->B), one hard cut (B->B)."""
 926 | +
 927 | +    def setUp(self):
 928 | +        self.tmp = tempfile.mkdtemp(prefix="trc_")
 929 | +        self.addCleanup(shutil.rmtree, self.tmp, True)
 930 | +        self.segs = [("hook", _seg(os.path.join(self.tmp, "a.mp4"), "red", 440, 3, (0.4, 2.6)), "talking_head"),
 931 | +                     ("clip_01", _seg(os.path.join(self.tmp, "b.mp4"), "ramp", 660, 3, (0.4, 2.6)), "talking_head"),
 932 | +                     ("clip_02", _seg(os.path.join(self.tmp, "c.mp4"), "green", 880, 3, (0.4, 2.6)), "talking_head")]
 933 | +        self.ch = {"hook": "A", "clip_01": "B", "clip_02": "B"}
 934 | +        self.lt = {k: (0.4, 0.4) for k in self.ch}
 935 | +
 936 | +    def run_style(self, style):
 937 | +        out = os.path.join(self.tmp, f"{style}.mp4")
 938 | +        j = TR.plan(self.segs, self.ch, self.lt, style)
 939 | +        tl = TR.concat(self.segs, j, out, 23, 320, 180, self.tmp)
 940 | +        return out, j, tl
 941 | +
 942 | +    def test_dissolve_overlaps_only_silence_and_stays_frame_locked(self):
 943 | +        out, j, tl = self.run_style("crossfade")
 944 | +        self.assertEqual([(x["after"], x["frames"]) for x in j], [(0, 6)])
 945 | +        dd = 6 / 24
 946 | +        self.assertAlmostEqual(tl[1]["start"], tl[0]["end"] - dd, places=3)   # overlap = the dissolve
 947 | +        self.assertAlmostEqual(tl[2]["start"], tl[1]["end"], places=3)        # same channel: hard cut
 948 | +        p = _probe(out)
 949 | +        n_frames = int(p["video"]["nb_read_packets"])
 950 | +        self.assertEqual(n_frames, 3 * 72 - 6)
 951 | +        self.assertAlmostEqual(float(p["audio"]["duration"]), n_frames / 24, delta=0.03)   # A/V locked
 952 | +        # the overlap region holds no tone from either side (both are in their silences)
 953 | +        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{tl[1]['start']:.3f}", "-t", f"{dd:.3f}", "-i", out,
 954 | +                            "-f", "f32le", "-ac", "1", "-ar", "48000", "-"], capture_output=True, check=True)
 955 | +        a = np.frombuffer(r.stdout, np.float32)
 956 | +        self.assertLess(20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-12), -50)
 957 | +
 958 | +    def test_dissolved_clip_picture_and_sound_start_together(self):
 959 | +        # B = a luma ramp (frame k is identifiable): after the dissolve, output frame (start*24 + k) must be
 960 | +        # B's frame k, and B's tone (0.4 s into B) must start 0.4 s after the same start. ffmpeg 4.4.2's
 961 | +        # xfade with offset = start put every B frame one frame late (41.7 ms behind its sound).
 962 | +        out, j, tl = self.run_style("crossfade")
 963 | +        b, x = _lumas(self.segs[1][1]), _lumas(out)
 964 | +        s0 = int(round(tl[1]["start"] * 24))
 965 | +        k = np.arange(6, 72)
 966 | +        self.assertLess(float(np.max(np.abs(x[s0 + k] - b[k]))), 1.5, (x[s0 + 4:s0 + 10], b[4:10]))
 967 | +        onset = _onset(out, tl[1]["start"] + 0.2, tl[1]["start"] + 0.6)
 968 | +        self.assertAlmostEqual(onset - tl[1]["start"], 0.4, delta=0.012)
 969 | +
 970 | +    def test_C_inserts_one_wipe_between_channels_only(self):
 971 | +        out, j, tl = self.run_style("C")
 972 | +        self.assertEqual([e["label"] for e in tl], ["hook", "transition_C", "clip_01", "clip_02"])
 973 | +        self.assertEqual(tl[0]["start"], 0.0)                                 # nothing at the open
 974 | +        p = _probe(out)
 975 | +        self.assertEqual(int(p["video"]["nb_read_packets"]), 3 * 72 + TR.WIPE_FRAMES)
 976 | +
 977 | +
 978 | +class TestFrozenPath(unittest.TestCase):
 979 | +    def test_no_transitions_file_keeps_the_frozen_concat(self):
 980 | +        import render16
 981 | +        tmp = tempfile.mkdtemp(prefix="trf_")
 982 | +        self.addCleanup(shutil.rmtree, tmp, True)
 983 | +        self.assertIsNone(render16._transition_concat(tmp, SEGS, os.path.join(tmp, "x.mp4"), 1920, 1080, tmp))
 984 | +
 985 | +
 986 | +if __name__ == "__main__":
 987 | +    unittest.main()
 988 | diff --git a/pipeline/test_vertical_layout.py b/pipeline/test_vertical_layout.py
 989 | new file mode 100644
 990 | index 00000000..89e7f213
 991 | --- /dev/null
 992 | +++ b/pipeline/test_vertical_layout.py
 993 | @@ -0,0 +1,193 @@
 994 | +#!/usr/bin/env python3
 995 | +"""DEC-2 / DEC-5 (orchestrator, delegated by PBX, 2026-11-11): the 9:16 is a speaker-centred reframe by
 996 | +default; 2-3 people get stacked bands; the safe frame only for a shared screen ('screen') or an
 997 | +unidentifiable speaker, flagged. Layouts are per SHOT. Fixture: the Nov 10 prepared clips at 360p
 998 | +(face-area rules are fractions of the frame, so they are scale-invariant).
 999 | +Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_vertical_layout.py"""
1000 | +import copy
1001 | +import os
1002 | +import shutil
1003 | +import subprocess
1004 | +import sys
1005 | +import tempfile
1006 | +import unittest
1007 | +
1008 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
1009 | +REPO = os.path.dirname(PIPELINE)
1010 | +sys.path.insert(0, PIPELINE)
1011 | +FIX = os.path.join(REPO, "tests", "fixtures", "pulse_20261110", "video")
1012 | +CLIP = {c: os.path.join(FIX, f"prepared_{c}_360p.mp4") for c in ("hook", "clip_01", "clip_02")}
1013 | +
1014 | +
1015 | +def V():
1016 | +    import vertical_layout
1017 | +    return vertical_layout
1018 | +
1019 | +
1020 | +class TestClassifier(unittest.TestCase):
1021 | +    @classmethod
1022 | +    def setUpClass(cls):
1023 | +        cls.plans = {c: V().classify(p) for c, p in CLIP.items()}
1024 | +
1025 | +    def classes(self, c):
1026 | +        return [s["class"] for s in self.plans[c]["shots"]]
1027 | +
1028 | +    def test_chart_with_face_cam_is_screen(self):           # DataDash hook (face-cam 0.4 % of frame)
1029 | +        self.assertEqual(self.classes("hook"), ["screen"])
1030 | +        self.assertTrue(self.plans["hook"]["flagged"])
1031 | +
1032 | +    def test_standing_host_is_single(self):                  # Yahoo Finance (face 1.6 % of frame)
1033 | +        self.assertEqual(self.classes("clip_02"), ["single"])
1034 | +        self.assertFalse(self.plans["clip_02"]["flagged"])
1035 | +
1036 | +    def test_cutaways_are_their_own_shots(self):             # Natalie: chart | talking head | Capitol
1037 | +        self.assertEqual(self.classes("clip_01"), ["screen", "single", "screen"])
1038 | +        sh = self.plans["clip_01"]["shots"]
1039 | +        self.assertAlmostEqual(sh[1]["start"], 105 / 24, places=3)    # the cut frame, not a sample time
1040 | +        self.assertAlmostEqual(sh[2]["start"], 393 / 24, places=3)
1041 | +
1042 | +
1043 | +class TestLayoutTruth(unittest.TestCase):
1044 | +    """G4s: a label must match the re-measured picture (never the label itself)."""
1045 | +
1046 | +    @classmethod
1047 | +    def setUpClass(cls):
1048 | +        cls.plans = {c: V().classify(p) for c, p in CLIP.items()}
1049 | +
1050 | +    def test_correct_labels_pass(self):
1051 | +        ok, table = V().gate_g4s(self.plans, CLIP)
1052 | +        self.assertTrue(ok, [r for r in table if not r["pass"]])
1053 | +
1054 | +    def test_talking_head_mislabelled_as_screen_fails(self):           # DEC-2 must-fail
1055 | +        bad = copy.deepcopy(self.plans)
1056 | +        for sh in bad["clip_02"]["shots"]:
1057 | +            sh["class"] = "screen"
1058 | +        ok, table = V().gate_g4s(bad, CLIP)
1059 | +        self.assertFalse(ok)
1060 | +        self.assertFalse(next(r for r in table if r["segment"] == "clip_02")["label_ok"])
1061 | +
1062 | +    def test_screen_mislabelled_as_single_fails(self):
1063 | +        bad = copy.deepcopy(self.plans)
1064 | +        bad["hook"]["shots"][0].update({"class": "single", "face_cx": 320})
1065 | +        ok, table = V().gate_g4s(bad, CLIP)
1066 | +        self.assertFalse(next(r for r in table if r["segment"] == "hook")["label_ok"])
1067 | +
1068 | +
1069 | +class TestStackGeometry(unittest.TestCase):
1070 | +    """Stacked bands: every face lies inside its own band, at 40 % of the band height unless the frame
1071 | +    edge clamps it (band positions are measured per face, never a fixed height)."""
1072 | +
1073 | +    def crops(self, vf):
1074 | +        import re
1075 | +        return [tuple(int(v) for v in m) for m in re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", vf)]
1076 | +
1077 | +    def test_each_face_inside_its_band(self):
1078 | +        import render_vertical as RV
1079 | +        for cls, cxs, cys in (("stack2", [500, 1400], [380, 520]), ("stack3", [300, 960, 1650], [300, 650, 120])):
1080 | +            crops = self.crops(RV._shot_vf({"class": cls, "band_cx": cxs, "band_cy": cys}, 1920, 1080))
1081 | +            self.assertEqual(len(crops), int(cls[-1]))
1082 | +            for (w, h, x, y), cx, cy in zip(crops, cxs, cys):
1083 | +                self.assertTrue(x <= cx <= x + w and y <= cy <= y + h, (cls, (w, h, x, y), cx, cy))
1084 | +                if 0 < y and y + h < 1080:
1085 | +                    self.assertAlmostEqual((cy - y) / h, 0.4, delta=0.01)
1086 | +
1087 | +
1088 | +class TestCaptionNote(unittest.TestCase):
1089 | +    """DEC-2/DEC-5: a safe frame is flagged in the caption with its layout, never silent."""
1090 | +
1091 | +    def edl(self, hook_shots, clip_shots):
1092 | +        mk = lambda shots: {"shots": shots, "flagged": any(s["flagged"] for s in shots)}
1093 | +        return {"hook": {"channel": "DataDash", "vertical_layout": mk(hook_shots)},
1094 | +                "clips": [{"index": 1, "channel": "Natalie Brunell", "vertical_layout": mk(clip_shots)}]}
1095 | +
1096 | +    def shot(self, cls, a, b):
1097 | +        return {"start": a, "end": b, "class": cls, "flagged": cls in ("screen", "uncertain")}
1098 | +
1099 | +    def test_every_safe_frame_shot_is_named_with_its_layout(self):
1100 | +        note = V().layout_note(self.edl([self.shot("screen", 0, 9.4)],
1101 | +                                        [self.shot("screen", 0, 4.375), self.shot("single", 4.375, 16.375),
1102 | +                                         self.shot("uncertain", 16.375, 17.2)]))
1103 | +        self.assertIn("9:16 SAFE FRAME hook (DataDash): layout=screen 0.00-9.40 s", note)
1104 | +        self.assertIn("clip_01 (Natalie Brunell): layout=screen 0.00-4.38 s; "
1105 | +                      "layout=uncertain (speaker unidentified) 16.38-17.20 s", note)
1106 | +        self.assertNotIn("single", note)
1107 | +
1108 | +    def test_all_reframed_is_silent_and_unmeasured_is_reported(self):
1109 | +        self.assertEqual(V().layout_note(self.edl([self.shot("single", 0, 9)], [self.shot("stack2", 0, 15)])), "")
1110 | +        e = self.edl([self.shot("single", 0, 9)], [])
1111 | +        del e["clips"][0]["vertical_layout"]
1112 | +        self.assertIn("clip_01 (Natalie Brunell): layout NOT MEASURED", V().layout_note(e))
1113 | +
1114 | +
1115 | +class TestSafeFrameTruth(unittest.TestCase):
1116 | +    """G4s on the 9:16 picture (CPU encode). D5 must-fail: Yahoo Finance's standing host (single) shown
1117 | +    as the letterbox safe frame, as the Nov 10 9:16 did; must-pass: the same shot as a speaker crop."""
1118 | +
1119 | +    @classmethod
1120 | +    def setUpClass(cls):
1121 | +        cls.tmp = tempfile.mkdtemp(prefix="g4s_")
1122 | +        cls.src = os.path.join(cls.tmp, "clip_02.mp4")
1123 | +        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", CLIP["clip_02"], "-t", "4", "-vf", "scale=1920:1080",
1124 | +                        "-r", "24", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-an", cls.src],
1125 | +                       check=True)
1126 | +        cls.plan = V().classify(cls.src)
1127 | +
1128 | +    @classmethod
1129 | +    def tearDownClass(cls):
1130 | +        shutil.rmtree(cls.tmp, ignore_errors=True)
1131 | +
1132 | +    def render(self, vf, name):
1133 | +        out = os.path.join(self.tmp, name)
1134 | +        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.src, "-vf", vf, "-c:v", "libx264", "-crf", "20",
1135 | +                        "-preset", "veryfast", "-pix_fmt", "yuv420p", out], check=True)
1136 | +        return out
1137 | +
1138 | +    def g4s(self, vert):
1139 | +        return V().gate_g4s({"clip_02": self.plan}, {"clip_02": self.src}, vert_final=vert,
1140 | +                            vert_segments=[{"label": "clip_02", "start": 0.0}])
1141 | +
1142 | +    def test_talking_head_shown_as_safe_frame_fails(self):        # D5 must-fail
1143 | +        import render_vertical as RV
1144 | +        self.assertEqual([s["class"] for s in self.plan["shots"]], ["single"])
1145 | +        ok, table = self.g4s(self.render(RV.LETTERBOX_VF, "letterbox.mp4"))
1146 | +        self.assertFalse(ok, table)
1147 | +        self.assertTrue(table[0]["vertical_safe_frame"], table)
1148 | +
1149 | +    def test_talking_head_cropped_passes(self):
1150 | +        import render_vertical as RV
1151 | +        ok, table = self.g4s(self.render(RV._shot_vf(self.plan["shots"][0], 1920, 1080), "crop.mp4"))
1152 | +        self.assertTrue(ok, table)
1153 | +        self.assertFalse(table[0]["vertical_safe_frame"], table)
1154 | +
1155 | +
1156 | +@unittest.skipUnless(os.environ.get("CUDA_VISIBLE_DEVICES") == "0", "NVENC render needs GPU0")
1157 | +class TestReframeAuto(unittest.TestCase):
1158 | +    """End to end on a 1080p copy of Natalie's clip: 1080x1920, same duration, the chart and Capitol
1159 | +    shots are safe frames, the talking-head shot is a crop (no blurred bands)."""
1160 | +
1161 | +    def test_per_shot_render(self):
1162 | +        import cv2
1163 | +        import render_vertical as RV
1164 | +        tmp = tempfile.mkdtemp(prefix="reframe_")
1165 | +        try:
1166 | +            src = os.path.join(tmp, "clip_01.mp4")
1167 | +            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", CLIP["clip_01"], "-f", "lavfi", "-i",
1168 | +                            "anullsrc=r=48000:cl=stereo", "-shortest", "-vf", "scale=1920:1080", "-r", "24",
1169 | +                            "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-c:a", "aac", src], check=True)
1170 | +            plan = V().classify(src)
1171 | +            out = os.path.join(tmp, "vert.mp4")
1172 | +            ok, summary = RV.reframe_auto(src, out, "clip_01", plan)
1173 | +            self.assertTrue(ok, summary)
1174 | +            w, h, fps, dur = V()._probe(out)
1175 | +            self.assertEqual((w, h), (1080, 1920))
1176 | +            self.assertAlmostEqual(dur, plan["duration"], delta=1 / 24 + 0.03)
1177 | +            for sh in plan["shots"]:
1178 | +                tm = (sh["start"] + sh["end"]) / 2
1179 | +                safe, m = V().is_safe_frame(V()._frame(out, tm), V()._frame(src, tm))
1180 | +                self.assertEqual(safe, sh["class"] in V().SAFE_FRAME, (sh, m))
1181 | +        finally:
1182 | +            shutil.rmtree(tmp, ignore_errors=True)
1183 | +
1184 | +
1185 | +if __name__ == "__main__":
1186 | +    unittest.main()
1187 | diff --git a/pipeline/test_word_diff.py b/pipeline/test_word_diff.py
1188 | new file mode 100644
1189 | index 00000000..dac2eac2
1190 | --- /dev/null
1191 | +++ b/pipeline/test_word_diff.py
1192 | @@ -0,0 +1,106 @@
1193 | +#!/usr/bin/env python3
1194 | +"""G18 WORD-FOR-WORD (mission 4a): the final says exactly the locked sentences. Must-fail: yesterday's
1195 | +final (PBX review of pinned_20261110_150345): clip_01 starts on a clipped "above 81,000" and runs into
1196 | +"All right, you've probably seen people celebrating" (D2/D3a); clip_02 starts on "days of course" (D3b).
1197 | +Run (GPU parts): cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_word_diff.py"""
1198 | +import json
1199 | +import os
1200 | +import shutil
1201 | +import sys
1202 | +import tempfile
1203 | +import unittest
1204 | +
1205 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
1206 | +REPO = os.path.dirname(PIPELINE)
1207 | +sys.path.insert(0, PIPELINE)
1208 | +FIX = os.path.join(REPO, "tests", "fixtures", "pulse_20261110")
1209 | +
1210 | +import word_diff as W  # noqa: E402
1211 | +
1212 | +
1213 | +class TestCanonical(unittest.TestCase):
1214 | +    """Two whisper passes over the SAME audio render numbers and disfluent repeats differently (measured on
1215 | +    the Nov 10 fixture); both sides are canonicalised alike, real word changes still count."""
1216 | +
1217 | +    def test_asr_renderings_of_the_same_words_are_equal(self):
1218 | +        for a, b in (("It went from above $81 ,000 after the election.", "it went from above 81,000 after the election"),
1219 | +                     ("U .S. Bitcoin ETFs had about $1 .3 billion", "US Bitcoin ETFs had about one point three billion dollars"),
1220 | +                     ("around $74 000, around the 50 weekly MA", "around seventy four thousand dollars around the fifty weekly MA"),
1221 | +                     ("241 House winners and 50 senators", "two hundred forty one house winners and fifty senators"),
1222 | +                     ("up still 25 % off the lows", "up still twenty five percent off the lows"),
1223 | +                     ("days. Of course, of course, Bitcoin dropped", "days of course bitcoin dropped")):
1224 | +            self.assertEqual(W.diff(a, b), [], (a, b))
1225 | +
1226 | +    def test_missing_added_and_changed_words_count(self):
1227 | +        d = W.diff("It went from above $81,000 after the election. That was the week.",
1228 | +                   "81,000 after the election. That was the week. All right, you've probably seen")
1229 | +        self.assertIn(("delete", "it went from above", ""), d)
1230 | +        self.assertIn(("insert", "", "all right you've probably seen"), d)
1231 | +        self.assertEqual(W.diff("the market fell", "the market rose"), [("replace", "fell", "rose")])
1232 | +        self.assertEqual(W.diff("bitcoin fell", "bitcoin fell fell sharply"), [("insert", "", "sharply")])
1233 | +
1234 | +    def test_edges_compare_the_first_and_last_two_words(self):
1235 | +        self.assertEqual(W.edges("But I don't check it. Many times.", "but i don't check it many times"), [])
1236 | +        self.assertEqual(W.edges("It went from above $81,000. Just last week.",
1237 | +                                 "above 81,000. Just last week. All right, people celebrating"),
1238 | +                         [("start", "it went", "above 81000"), ("end", "last week", "people celebrating")])
1239 | +
1240 | +
1241 | +def _clips():
1242 | +    """Yesterday's three clips: the editor's sentences locked on today's transcripts (as the G16 fixture),
1243 | +    and the source span each was cut from."""
1244 | +    import sentence_law as L
1245 | +    tmp = tempfile.mkdtemp(prefix="g18_")
1246 | +    try:
1247 | +        shutil.copytree(os.path.join(FIX, "run", "transcripts"), os.path.join(tmp, "t"))
1248 | +        for f in os.listdir(os.path.join(FIX, "selection", "transcripts_punctuated")):
1249 | +            shutil.copy(os.path.join(FIX, "selection", "transcripts_punctuated", f), os.path.join(tmp, "t"))
1250 | +        edl = json.load(open(os.path.join(FIX, "run", "edl.json")))
1251 | +        sel = {p["video_id"]: p for p in json.load(open(os.path.join(FIX, "selection", "B3_chosen.json")))["chosen"]}
1252 | +        cuts = {c["clip_id"]: c for c in json.load(open(os.path.join(FIX, "run", "cuts_final.json")))}
1253 | +        out = {}
1254 | +        for label, seg in [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl["clips"]]:
1255 | +            words = json.load(open(os.path.join(tmp, "t", f"{seg['video_id']}.json")))["words"]
1256 | +            i0, i1, _ = L.anchor(words, sel[seg["video_id"]]["text"])
1257 | +            out[label] = {"lock_text": " ".join(w["word"] for w in words[i0:i1 + 1]),
1258 | +                          "source": os.path.join(FIX, "audio", f"src_{seg['video_id']}.flac"),
1259 | +                          "cut_in": cuts[label]["cut_in"], "cut_out": cuts[label]["cut_out"]}
1260 | +        return out
1261 | +    finally:
1262 | +        shutil.rmtree(tmp, ignore_errors=True)
1263 | +
1264 | +
1265 | +@unittest.skipUnless(os.path.exists("/dev/nvidia0"), "whisper large-v3 needs a GPU")
1266 | +class TestYesterdaysFinal(unittest.TestCase):
1267 | +    @classmethod
1268 | +    def setUpClass(cls):
1269 | +        segs = json.load(open(os.path.join(FIX, "run", "concat_manifest_16x9.json")))["segments"]
1270 | +        cls.ok, rows = W.gate_g18(os.path.join(FIX, "audio", "out_16x9.flac"), segs, _clips())
1271 | +        cls.rows = {r["segment"]: r for r in rows}
1272 | +
1273 | +    def test_gate_fails(self):
1274 | +        self.assertFalse(self.ok, self.rows)
1275 | +
1276 | +    def test_clip01_clipped_start_and_run_on_fail(self):            # D3a + D2
1277 | +        r = self.rows["clip_01"]
1278 | +        self.assertFalse(r["pass"], r)
1279 | +        self.assertEqual([e[0] for e in r["edges"]], ["start", "end"], r)
1280 | +        self.assertIn("celebrating", r["edges"][1][2], r)
1281 | +        self.assertIn(("insert", "", "above"), r["identity"], r)    # the clipped fragment is in the final only
1282 | +
1283 | +    def test_clip02_start_inside_days_fails(self):                  # D3b
1284 | +        r = self.rows["clip_02"]
1285 | +        self.assertFalse(r["pass"], r)
1286 | +        self.assertEqual(r["edges"][0][:2], ("start", "of course"), r)
1287 | +        self.assertTrue(r["edges"][0][2].startswith("days"), r)
1288 | +
1289 | +    def test_hook_words_are_intact(self):
1290 | +        # D1 (the hook's onset) is acoustic and caught by G16/G17; its words are all there. The lock's own
1291 | +        # ASR rendering of the fast "73,400, 500" differs from the final's: reported, not gated.
1292 | +        r = self.rows["hook"]
1293 | +        self.assertTrue(r["pass"], r)
1294 | +        self.assertTrue(r["lock_diff_reported"], r)
1295 | +
1296 | +
1297 | +if __name__ == "__main__":
1298 | +    unittest.main()
1299 | diff --git a/pipeline/transition_options.py b/pipeline/transition_options.py
1300 | new file mode 100644
1301 | index 00000000..b04f688c
1302 | --- /dev/null
1303 | +++ b/pipeline/transition_options.py
1304 | @@ -0,0 +1,53 @@
1305 | +#!/usr/bin/env python3
1306 | +"""pipeline/transition_options.py — the labelled transition options on one finished cut (Phase 3, DEC-4).
1307 | +
1308 | +The production run renders the DEC-4 default (6-frame cross-dissolve + matching audio crossfade). For PBX's
1309 | +choice, the SAME cut (same cuts, same prepared clips, same layout plan) is rendered again per option in a
1310 | +copy of the run dir, and every option is gated and packed like a production render:
1311 | +  A  clean cut; 6-frame audio dip-crossfade across the cut
1312 | +  B  6-frame cross-dissolve + matching audio crossfade + a soft synthesized pulse thump
1313 | +  C  brand ECG line sweep, 8 frames on black, double thump (no logo, no text, nothing at the open)
1314 | +Usage: CUDA_VISIBLE_DEVICES=0 python3 transition_options.py RUN_DIR [A B C]
1315 | +Delivery is separate: telegram.deliver_run(<copy>, option="A") (labelled, never a release candidate).
1316 | +"""
1317 | +import json
1318 | +import os
1319 | +import shutil
1320 | +import sys
1321 | +
1322 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
1323 | +sys.path.insert(0, PIPELINE)
1324 | +
1325 | +
1326 | +def render_option(run_dir, style):
1327 | +    import run_fresh as rf
1328 | +    import verify_pack
1329 | +    dst = f"{run_dir.rstrip('/')}_option{style}"
1330 | +    if os.path.exists(dst):
1331 | +        raise SystemExit(f"STOP: {dst} exists")
1332 | +    shutil.copytree(run_dir, dst, ignore=shutil.ignore_patterns("TELEGRAM_DELIVERY*.json", "VERIFY"))
1333 | +    for p in ("out/segment.mp4", "out/segment_vertical.mp4", "GATE_REPORT.json"):
1334 | +        if os.path.exists(os.path.join(dst, p)):
1335 | +            os.remove(os.path.join(dst, p))
1336 | +    run = rf.Run(dst)
1337 | +    with open(os.path.join(dst, "status.json")) as f:
1338 | +        run.mode = json.load(f).get("mode", "auto")
1339 | +    pin = os.path.join(dst, "PINNED_DECISION.json")
1340 | +    if run.mode == "pinned" and os.path.exists(pin):        # same limiter as the original render
1341 | +        with open(pin) as f:
1342 | +            run.machine_cuts = bool(json.load(f).get("pin", {}).get("machine_cuts", False))
1343 | +    with open(os.path.join(dst, "cuts_final.json")) as f:
1344 | +        cuts = json.load(f)
1345 | +    rf.TRANSITION_STYLE = style                     # the option, on the same cut
1346 | +    final16, man16, final9, man9 = rf.stage_render(run)
1347 | +    rows, flags, limits = rf.stage_gates(run, final16, man16, final9, man9)
1348 | +    verify_pack.build(dst)
1349 | +    run.save()
1350 | +    print(f"option {style}: {dst} | " + ", ".join(f"{fmt}: {rf.verdict_for(rows[fmt])[0]}" for fmt in rows))
1351 | +    return dst, cuts
1352 | +
1353 | +
1354 | +if __name__ == "__main__":
1355 | +    rd = os.path.abspath(sys.argv[1])
1356 | +    for st in (sys.argv[2:] or ["A", "B", "C"]):
1357 | +        render_option(rd, st)
1358 | diff --git a/pipeline/transitions.py b/pipeline/transitions.py
1359 | new file mode 100644
1360 | index 00000000..088b4622
1361 | --- /dev/null
1362 | +++ b/pipeline/transitions.py
1363 | @@ -0,0 +1,250 @@
1364 | +#!/usr/bin/env python3
1365 | +"""pipeline/transitions.py — transitions between segments from DIFFERENT channels only (Phase 3, DEC-4).
1366 | +
1367 | +Styles (run-level, TRANSITIONS.json written by run_fresh before rendering; no file = hard cuts, the
1368 | +frozen v2f path, Law 22):
1369 | +  crossfade  DEC-4 production default: 6-frame cross-dissolve + matching audio crossfade (= B without
1370 | +             the thump).
1371 | +  A          clean cut; 6-frame audio dip-crossfade centred on the cut (A fades over its last 3 frames,
1372 | +             B rises over its first 3) - no picture effect, no overlap, picture and sound frame-locked.
1373 | +  B          6-frame cross-dissolve + matching audio crossfade + a soft low pulse thump (sub sine + short
1374 | +             click) at the dissolve's centre.
1375 | +  C          brand pulse wipe: an 8-frame insert (0.333 s) on black in which the brand ECG line
1376 | +             (brand/2026-11/pp_pulse_glossy.svg path) sweeps left to right, with a heartbeat double thump.
1377 | +Overlaps (crossfade/B) and fades (A) only ever cover non-speech: each junction is bounded by the
1378 | +measured genuine tail of A and lead-in of B (sentence_law.head_tail on the prepared clips); a junction
1379 | +that cannot hold >= 2 frames of non-speech stays a hard cut. Sound design peaks at THUMP_PEAK_DBFS
1380 | +(-24 dBFS before the music bed and loudnorm, Law 13 range) and sits only where nobody speaks.
1381 | +Nothing is ever added at the open of the video (the first junction is after the hook).
1382 | +"""
1383 | +import json
1384 | +import math
1385 | +import os
1386 | +import subprocess
1387 | +import wave
1388 | +
1389 | +import numpy as np
1390 | +
1391 | +FPS = 24
1392 | +SR = 48000
1393 | +DISSOLVE_FRAMES = 6
1394 | +WIPE_FRAMES = 8
1395 | +MIN_FRAMES = 2
1396 | +THUMP_PEAK_DBFS = -24.0
1397 | +STYLES = ("crossfade", "A", "B", "C")
1398 | +PULSE_PATH = ("M38 278 L84 278 C109 278 115 220 136 220 C158 220 164 330 180 330 C196 330 242 98 252 98 "
1399 | +              "C262 98 306 384 316 384 C329 384 342 220 364 220 C385 220 391 278 416 278 L462 278")
1400 | +
1401 | +
1402 | +def plan(segments, channels, lead_tail, style):
1403 | +    """Junction list [{"after": i, "frames": n, "kind": ...}] for the concat of `segments` (manifest
1404 | +    order: (label, path, type)). channels {label: channel}; lead_tail {label: (lead_s, tail_s)}."""
1405 | +    if style not in STYLES:
1406 | +        raise ValueError(f"unknown transition style {style!r}")
1407 | +    out = []
1408 | +    for i in range(len(segments) - 1):
1409 | +        (la, _, ta), (lb, _, tb) = segments[i], segments[i + 1]
1410 | +        if ta != "talking_head" or tb != "talking_head" or channels.get(la) == channels.get(lb):
1411 | +            continue                                            # only between different channels
1412 | +        want = WIPE_FRAMES if style == "C" else DISSOLVE_FRAMES
1413 | +        if style == "C":
1414 | +            out.append({"after": i, "frames": want, "kind": "insert", "style": style})
1415 | +            continue
1416 | +        tail_a, lead_b = lead_tail[la][1], lead_tail[lb][0]
1417 | +        half = style == "A"                                     # A: each side fades over half
1418 | +        room = min(tail_a, lead_b) * (2 if half else 1)
1419 | +        n = min(want, int(math.floor(room * FPS + 1e-9)))
1420 | +        if n >= MIN_FRAMES:
1421 | +            out.append({"after": i, "frames": n, "kind": "dip" if half else "dissolve", "style": style,
1422 | +                        "bounded_by_ms": [int(tail_a * 1000), int(lead_b * 1000)]})
1423 | +    return out
1424 | +
1425 | +
1426 | +# ── sound design (generated in code; no stock packs) ──
1427 | +
1428 | +def thump(sub_hz=52.0, dur=0.32, click_ms=4.0):
1429 | +    t = np.arange(int(dur * SR)) / SR
1430 | +    body = np.sin(2 * np.pi * sub_hz * t) * np.exp(-t / 0.075) * (1 - np.exp(-t / 0.004))
1431 | +    k = int(click_ms / 1000 * SR)
1432 | +    click = np.zeros_like(t)
1433 | +    click[:k] = np.random.default_rng(11).normal(0, 1, k) * np.hanning(2 * k)[k:] * 0.35
1434 | +    x = body + np.convolve(click, np.ones(24) / 24, mode="same")
1435 | +    return x / np.max(np.abs(x))
1436 | +
1437 | +
1438 | +def double_thump():
1439 | +    a, b = thump(), thump(sub_hz=46.0) * 0.6
1440 | +    gap = int(0.17 * SR)
1441 | +    out = np.zeros(gap + len(b))
1442 | +    out[:len(a)] += a
1443 | +    out[gap:gap + len(b)] += b
1444 | +    return out / np.max(np.abs(out))
1445 | +
1446 | +
1447 | +def write_wav(path, mono, peak_dbfs):
1448 | +    x = mono * (10 ** (peak_dbfs / 20))
1449 | +    k = int(0.005 * SR)                                         # Law 13: 5 ms micro-fades at both ends
1450 | +    x[:k] *= np.linspace(0, 1, k)
1451 | +    x[-k:] *= np.linspace(1, 0, k)
1452 | +    st = np.stack([x, x], 1)
1453 | +    with wave.open(path, "wb") as f:
1454 | +        f.setnchannels(2)
1455 | +        f.setsampwidth(2)
1456 | +        f.setframerate(SR)
1457 | +        f.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())
1458 | +
1459 | +
1460 | +# ── C: brand pulse wipe insert ──
1461 | +
1462 | +def _bezier_points(path=PULSE_PATH, steps=24):
1463 | +    import re
1464 | +    toks = re.findall(r"[MLC]|-?\d+(?:\.\d+)?", path)
1465 | +    pts, cur, i = [], None, 0
1466 | +    while i < len(toks):
1467 | +        cmd = toks[i]
1468 | +        if cmd in ("M", "L"):
1469 | +            cur = (float(toks[i + 1]), float(toks[i + 2]))
1470 | +            pts.append(cur)
1471 | +            i += 3
1472 | +        elif cmd == "C":
1473 | +            p1, p2, p3 = [(float(toks[i + 1 + 2 * k]), float(toks[i + 2 + 2 * k])) for k in range(3)]
1474 | +            for s in range(1, steps + 1):
1475 | +                u = s / steps
1476 | +                pts.append(tuple((1 - u) ** 3 * cur[d] + 3 * (1 - u) ** 2 * u * p1[d] + 3 * (1 - u) * u ** 2 * p2[d]
1477 | +                                 + u ** 3 * p3[d] for d in range(2)))
1478 | +            cur = p3
1479 | +            i += 7
1480 | +        else:
1481 | +            raise ValueError(f"unsupported path command {cmd}")
1482 | +    return pts
1483 | +
1484 | +
1485 | +def wipe_frames(w, h, n=WIPE_FRAMES):
1486 | +    """n RGB frames on black: the brand ECG line (thin neon: dark under-stroke, red glow, hot core)
1487 | +    drawn left to right across the frame's middle, fully drawn on the last frame."""
1488 | +    from PIL import Image, ImageDraw, ImageFilter
1489 | +    pts = _bezier_points()
1490 | +    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
1491 | +    sx = w / (max(xs) - min(xs))
1492 | +    sy = sx * 0.55 if w > h else sx * 0.9
1493 | +    cy = h / 2
1494 | +    line = [((x - min(xs)) * sx, cy + (y - 278) * sy) for x, y in pts]
1495 | +    scale = max(1.0, w / 1920)
1496 | +    frames = []
1497 | +    for k in range(n):
1498 | +        upto = (k + 1) / n * w
1499 | +        vis = [p for p in line if p[0] <= upto]
1500 | +        if len(vis) < 2:
1501 | +            vis = line[:2]
1502 | +        glow = Image.new("RGB", (w, h), (0, 0, 0))
1503 | +        ImageDraw.Draw(glow).line(vis, fill=(225, 6, 0), width=int(16 * scale), joint="curve")
1504 | +        glow = glow.filter(ImageFilter.GaussianBlur(10 * scale))
1505 | +        img = Image.new("RGB", (w, h), (0, 0, 0))
1506 | +        d = ImageDraw.Draw(img)
1507 | +        d.line(vis, fill=(26, 0, 0), width=int(12 * scale), joint="curve")
1508 | +        img = Image.fromarray(np.maximum(np.asarray(img), np.asarray(glow)))
1509 | +        d = ImageDraw.Draw(img)
1510 | +        d.line(vis, fill=(255, 42, 26), width=int(5 * scale), joint="curve")
1511 | +        d.line(vis, fill=(255, 210, 204), width=max(1, int(1.5 * scale)), joint="curve")
1512 | +        frames.append(img)
1513 | +    return frames
1514 | +
1515 | +
1516 | +def render_wipe(path, w, h, qp):
1517 | +    import tempfile
1518 | +    tmp = tempfile.mkdtemp(prefix="wipe_")
1519 | +    for k, f in enumerate(wipe_frames(w, h)):
1520 | +        f.save(os.path.join(tmp, f"f{k:02d}.png"))
1521 | +    wav = os.path.join(tmp, "dt.wav")
1522 | +    dur = WIPE_FRAMES / FPS
1523 | +    x = double_thump()
1524 | +    pad = np.zeros(int(dur * SR))
1525 | +    pad[:min(len(pad), len(x))] = x[:len(pad)]
1526 | +    write_wav(wav, pad, THUMP_PEAK_DBFS)
1527 | +    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%02d.png"),
1528 | +                    "-i", wav, "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(qp),
1529 | +                    "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
1530 | +                    "-t", f"{dur:.4f}", "-movflags", "+faststart", path], check=True, capture_output=True, timeout=120)
1531 | +    return path
1532 | +
1533 | +
1534 | +# ── concat with transitions ──
1535 | +
1536 | +def _frames(path):
1537 | +    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
1538 | +                        "stream=nb_read_packets", "-of", "csv=p=0", path], capture_output=True, text=True,
1539 | +                       check=True, timeout=60)
1540 | +    return int(r.stdout.strip().split(",")[0])
1541 | +
1542 | +
1543 | +def concat(segments, junctions, out_path, qp, w, h, work_dir):
1544 | +    """Concatenate (label, path, type) segments with the planned junctions. Every input is normalised
1545 | +    to its exact video frame count (audio padded/trimmed to it) so picture and sound stay locked.
1546 | +    Returns the timeline [{"label","type","start","end"}] (overlapping entries at dissolves)."""
1547 | +    style_c = [j for j in junctions if j["kind"] == "insert"]
1548 | +    segs = list(segments)
1549 | +    if style_c:
1550 | +        wipe = render_wipe(os.path.join(work_dir, "transition_wipe_C.mp4"), w, h, qp)
1551 | +        for j in sorted(style_c, key=lambda j: -j["after"]):
1552 | +            segs.insert(j["after"] + 1, ("transition_C", wipe, "transition"))
1553 | +        junctions = [j for j in junctions if j["kind"] != "insert"]
1554 | +    jmap = {segs.index(segments[j["after"]]): j for j in junctions}
1555 | +    frames = [_frames(p) for _, p, _ in segs]
1556 | +    graph, tl = [], []
1557 | +    for i, (_, p, _) in enumerate(segs):
1558 | +        d = frames[i] / FPS
1559 | +        graph.append(f"[{i}:v]setpts=PTS-STARTPTS,fps={FPS},trim=end_frame={frames[i]},setsar=1[v{i}]")
1560 | +        graph.append(f"[{i}:a]asetpts=PTS-STARTPTS,aresample=async=1,apad,atrim=end={d:.6f},"
1561 | +                     f"aformat=sample_fmts=fltp:sample_rates={SR}:channel_layouts=stereo[a{i}]")
1562 | +    vcur, acur, t = "v0", "a0", frames[0] / FPS
1563 | +    tl.append({"label": segs[0][0], "type": segs[0][2], "start": 0.0, "end": round(t, 4)})
1564 | +    thumps = []
1565 | +    for i in range(1, len(segs)):
1566 | +        j = jmap.get(i - 1)
1567 | +        di = frames[i] / FPS
1568 | +        if j and j["kind"] == "dissolve":
1569 | +            dd = j["frames"] / FPS
1570 | +            # ffmpeg 4.4.2 xfade keeps A through the frame at round(offset*fps) and starts B on the NEXT
1571 | +            # frame: offset=t-dd put B's frame k at t-dd+(k+1)/fps, one frame (41.7 ms) behind B's own
1572 | +            # audio for the whole clip (measured 2026-11-11, test_transitions TestConcat). One frame
1573 | +            # earlier lands B's first frame exactly at t-dd, where acrossfade starts B's audio.
1574 | +            graph.append(f"[{vcur}][v{i}]xfade=transition=fade:duration={dd:.6f}:"
1575 | +                         f"offset={t - dd - 1 / FPS:.6f}[vx{i}]")
1576 | +            graph.append(f"[{acur}][a{i}]acrossfade=d={dd:.6f}:c1=tri:c2=tri[ax{i}]")
1577 | +            start = t - dd
1578 | +            if j["style"] == "B":
1579 | +                thumps.append(start + dd / 2)
1580 | +        else:
1581 | +            if j and j["kind"] == "dip":
1582 | +                dd = j["frames"] / FPS / 2
1583 | +                graph.append(f"[{acur}]afade=t=out:st={t - dd:.6f}:d={dd:.6f}[ad{i}]")
1584 | +                graph.append(f"[a{i}]afade=t=in:st=0:d={dd:.6f}[ai{i}]")
1585 | +                acur, ain = f"ad{i}", f"ai{i}"
1586 | +            else:
1587 | +                ain = f"a{i}"
1588 | +            graph.append(f"[{vcur}][{acur}][v{i}][{ain}]concat=n=2:v=1:a=1[vx{i}][ax{i}]")
1589 | +            start = t
1590 | +        vcur, acur, t = f"vx{i}", f"ax{i}", start + di
1591 | +        tl.append({"label": segs[i][0], "type": segs[i][2], "start": round(start, 4), "end": round(t, 4)})
1592 | +    inputs = []
1593 | +    for _, p, _ in segs:
1594 | +        inputs += ["-i", p]
1595 | +    if thumps:
1596 | +        x = np.zeros(int((t + 1) * SR))
1597 | +        th = thump()
1598 | +        for c in thumps:
1599 | +            k = int((c - 0.02) * SR)
1600 | +            x[k:k + len(th)] += th[:len(x) - k]
1601 | +        tw = os.path.join(work_dir, "transition_thumps_B.wav")
1602 | +        write_wav(tw, x / max(1e-9, np.max(np.abs(x))), THUMP_PEAK_DBFS)
1603 | +        inputs += ["-i", tw]
1604 | +        graph.append(f"[{acur}][{len(segs)}:a]amix=inputs=2:duration=first:normalize=0[amx]")
1605 | +        acur = "amx"
1606 | +    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph),
1607 | +                    "-map", f"[{vcur}]", "-map", f"[{acur}]", "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp",
1608 | +                    "-qp", str(qp), "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
1609 | +                    "-ar", "48000", "-ac", "2", "-movflags", "+faststart", out_path],
1610 | +                   check=True, capture_output=True, timeout=1200)
1611 | +    with open(os.path.join(work_dir, "transitions_timeline.json"), "w") as f:
1612 | +        json.dump({"junctions": junctions + style_c, "timeline": tl, "thumps_s": thumps}, f, indent=2)
1613 | +    return tl
1614 | diff --git a/pipeline/verify_pack.py b/pipeline/verify_pack.py
1615 | new file mode 100644
1616 | index 00000000..1d1d6a04
1617 | --- /dev/null
1618 | +++ b/pipeline/verify_pack.py
1619 | @@ -0,0 +1,79 @@
1620 | +#!/usr/bin/env python3
1621 | +"""pipeline/verify_pack.py — the automated verification pack (mission 4a; DEC-8 'no hand step').
1622 | +
1623 | +What a reviewer checks by eye, produced for every run before any delivery and attached to the drop:
1624 | +  1. words   G18 word-for-word rows from GATE_REPORT.json (edges + identity per clip, both finals)
1625 | +  2. joins   frames at every segment boundary of both finals (last frame before, first after, and the
1626 | +             middle of a dissolve), one labelled contact sheet per format
1627 | +  3. credits the credits card: three frames per format and the measured G12/G15 rows
1628 | +VERIFY/VERIFICATION.json records every artefact; `complete` is True only when all of them exist.
1629 | +"""
1630 | +import json
1631 | +import os
1632 | +import subprocess
1633 | +
1634 | +FPS = 24
1635 | +
1636 | +
1637 | +def _frame(video, t, out):
1638 | +    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1",
1639 | +                    "-q:v", "3", out], check=True, timeout=60)
1640 | +    return out if os.path.exists(out) else None
1641 | +
1642 | +
1643 | +def _sheet(items, out, tile_w):
1644 | +    """items: [(label, path)] -> one labelled grid image (3 per row)."""
1645 | +    from PIL import Image, ImageDraw
1646 | +    ims = [(lab, Image.open(p).convert("RGB")) for lab, p in items if p]
1647 | +    if not ims:
1648 | +        return None
1649 | +    th = int(round(ims[0][1].height * tile_w / ims[0][1].width))
1650 | +    cols = 3
1651 | +    rows = (len(ims) + cols - 1) // cols
1652 | +    sheet = Image.new("RGB", (cols * tile_w, rows * (th + 28)), (0, 0, 0))
1653 | +    d = ImageDraw.Draw(sheet)
1654 | +    for k, (lab, im) in enumerate(ims):
1655 | +        x, y = (k % cols) * tile_w, (k // cols) * (th + 28)
1656 | +        sheet.paste(im.resize((tile_w, th)), (x, y + 28))
1657 | +        d.text((x + 6, y + 6), lab, fill=(255, 255, 255))
1658 | +    sheet.save(out, quality=88)
1659 | +    return out
1660 | +
1661 | +
1662 | +def build(run_dir):
1663 | +    vdir = os.path.join(run_dir, "VERIFY")
1664 | +    os.makedirs(vdir, exist_ok=True)
1665 | +    with open(os.path.join(run_dir, "GATE_REPORT.json")) as f:
1666 | +        rep = json.load(f)
1667 | +    pack = {"words": rep.get("G18"), "joins": {}, "credits": {"G12": {}, "G15": {}}}
1668 | +    for fmt, final, tile in (("16x9", "segment.mp4", 480), ("9x16", "segment_vertical.mp4", 270)):
1669 | +        final = os.path.join(run_dir, "out", final)
1670 | +        with open(os.path.join(run_dir, "qa", f"concat_manifest_{fmt}.json")) as f:
1671 | +            segs = json.load(f)["segments"]
1672 | +        items = []
1673 | +        for a, b in zip(segs, segs[1:]):
1674 | +            tag = f"{a['label']}->{b['label']}"
1675 | +            overlap = a["end"] - b["start"]
1676 | +            pts = [("last", b["start"] - 1.0 / FPS if overlap <= 1e-3 else a["end"] - 1.0 / FPS),
1677 | +                   ("first", (b["start"] if overlap <= 1e-3 else a["end"]) + 0.5 / FPS)]
1678 | +            if overlap > 1e-3:
1679 | +                pts.insert(1, ("mid-dissolve", b["start"] + overlap / 2))
1680 | +            for name, t in pts:
1681 | +                items.append((f"{fmt} {tag} {name} {t:.2f}s",
1682 | +                              _frame(final, t, os.path.join(vdir, f"join_{fmt}_{tag}_{name}.jpg"))))
1683 | +        pack["joins"][fmt] = {"frames": [p for _, p in items], "sheet": _sheet(
1684 | +            items, os.path.join(vdir, f"joins_{fmt}.jpg"), tile)}
1685 | +        sh = next((s for s in segs if s["label"] == "shoutout"), None)
1686 | +        if sh:
1687 | +            c_items = [(f"{fmt} credits {t:.2f}s", _frame(final, t, os.path.join(vdir, f"credits_{fmt}_{k}.jpg")))
1688 | +                       for k, t in enumerate((sh["start"] + 1.0, (sh["start"] + sh["end"]) / 2, sh["end"] - 0.5))]
1689 | +            pack["credits"][fmt] = {"frames": [p for _, p in c_items],
1690 | +                                    "sheet": _sheet(c_items, os.path.join(vdir, f"credits_{fmt}.jpg"), tile)}
1691 | +        pack["credits"]["G12"][fmt] = rep.get("rows", {}).get(fmt, {}).get("G12_credits")
1692 | +        pack["credits"]["G15"][fmt] = rep.get(f"G15_{fmt}")
1693 | +    files = [pack["joins"][f]["sheet"] for f in ("16x9", "9x16")] + \
1694 | +            [pack["credits"].get(f, {}).get("sheet") for f in ("16x9", "9x16")]
1695 | +    pack["complete"] = bool(pack["words"]) and all(p and os.path.exists(p) for p in files)
1696 | +    with open(os.path.join(vdir, "VERIFICATION.json"), "w") as f:
1697 | +        json.dump(pack, f, indent=2, default=str)
1698 | +    return pack
1699 | diff --git a/pipeline/vertical_layout.py b/pipeline/vertical_layout.py
1700 | new file mode 100644
1701 | index 00000000..aeb39d2a
1702 | --- /dev/null
1703 | +++ b/pipeline/vertical_layout.py
1704 | @@ -0,0 +1,257 @@
1705 | +#!/usr/bin/env python3
1706 | +"""pipeline/vertical_layout.py — deterministic per-shot vertical layout class (DEC-2, DEC-5, M5).
1707 | +
1708 | +PBX 2026-11-11: the 9:16 is a speaker-centred reframe by default; 2-3 people get stacked bands; the
1709 | +wide safe frame (letterbox) only for a shared screen or when the speaker cannot be identified, and then
1710 | +flagged in the EDL and the Telegram caption. Detection MEASURES (SCRFD faces, face_scrfd.py); these
1711 | +fixed rules DECIDE. Layouts are per SHOT: a clip is sampled every SAMPLE_S and split where the class of
1712 | +the picture changes (Natalie Brunell's Nov 10 clip = chart graphic -> talking head -> Capitol B-roll).
1713 | +
1714 | +Per sample (face area = bbox area / frame area):
1715 | +  screen   largest face < SCREEN_FACE_FRAC (1.0 %) or no face: a shared screen / chart / B-roll with at
1716 | +           most a small face-cam (DataDash face-cam 0.4 %; Yahoo Finance standing host 1.6 %; Natalie
1717 | +           Brunell 7.7-13 %: SCRFD measurements 2026-11-11)
1718 | +  single   exactly one face >= PROMINENT_FRAC (1.0 %)
1719 | +  stack2 / stack3   two / three faces >= 1.0 %, the smallest >= MIN_BAND_RATIO of the largest
1720 | +  uncertain  anything else (4+ faces, one dominant face plus small ones of unclear role)
1721 | +Shots: runs of equal sample class; runs shorter than MIN_SHOT_S are merged into the longer neighbour.
1722 | +Rendering per shot class: single -> fixed speaker-centred 9:16 crop at the shot's median face centre
1723 | +(no animated panning, Law 18a); stack2/3 -> equal bands left-to-right; screen/uncertain -> safe frame
1724 | +(letterbox), always reported in the plan as flagged.
1725 | +"""
1726 | +import json
1727 | +import os
1728 | +import subprocess
1729 | +
1730 | +import numpy as np
1731 | +
1732 | +SAMPLE_S = 0.5
1733 | +SCREEN_FACE_FRAC = 0.010
1734 | +PROMINENT_FRAC = 0.010
1735 | +MIN_BAND_RATIO = 0.35
1736 | +MIN_SHOT_S = 1.0
1737 | +SAFE_FRAME = ("screen", "uncertain")
1738 | +G4_LAYOUT = {"single": "single", "stack2": "2face", "stack3": "3face", "screen": "screenshare",
1739 | +             "uncertain": "single"}
1740 | +
1741 | +
1742 | +def _probe(path):
1743 | +    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
1744 | +                        "stream=width,height,nb_frames,r_frame_rate:format=duration", "-of", "json", path],
1745 | +                       capture_output=True, text=True, check=True, timeout=30)
1746 | +    j = json.loads(r.stdout)
1747 | +    s = j["streams"][0]
1748 | +    num, den = (int(x) for x in s["r_frame_rate"].split("/"))
1749 | +    return int(s["width"]), int(s["height"]), num / den, float(j["format"]["duration"])
1750 | +
1751 | +
1752 | +def sample_label(faces, w, h):
1753 | +    """Class of one sampled frame from its SCRFD faces [(x0, y0, x1, y1, score)]."""
1754 | +    fr = [((x1 - x0) * (y1 - y0) / float(w * h), (x0 + x1) / 2.0, (y0 + y1) / 2.0) for x0, y0, x1, y1, _ in faces]
1755 | +    fr.sort(key=lambda f: -f[0])
1756 | +    if not fr or fr[0][0] < SCREEN_FACE_FRAC:
1757 | +        return "screen", fr
1758 | +    prom = [f for f in fr if f[0] >= PROMINENT_FRAC]
1759 | +    if len(prom) == 1:
1760 | +        return "single", fr
1761 | +    if len(prom) in (2, 3) and prom[-1][0] >= MIN_BAND_RATIO * prom[0][0]:
1762 | +        return f"stack{len(prom)}", fr
1763 | +    return "uncertain", fr
1764 | +
1765 | +
1766 | +def _runs(labels):
1767 | +    runs, i = [], 0
1768 | +    while i < len(labels):
1769 | +        j = i
1770 | +        while j < len(labels) and labels[j] == labels[i]:
1771 | +            j += 1
1772 | +        runs.append([labels[i], i, j])
1773 | +        i = j
1774 | +    return runs
1775 | +
1776 | +
1777 | +CUT_PEAK_RATIO = 3.0   # a frame difference >= 3x the window median is a picture cut
1778 | +
1779 | +
1780 | +def _cut_frame(clip_path, mid, half, n_frames):
1781 | +    """First frame of the new shot near `mid`: the largest consecutive-frame difference (64x36 grey)
1782 | +    within +-half frames when it is a clear peak, else `mid` (sample-accurate)."""
1783 | +    import cv2
1784 | +    a, b = max(1, mid - half), min(n_frames - 1, mid + half)
1785 | +    cap = cv2.VideoCapture(clip_path)
1786 | +    cap.set(cv2.CAP_PROP_POS_FRAMES, a - 1)
1787 | +    prev, diffs = None, []
1788 | +    for f in range(a - 1, b + 1):
1789 | +        ok, fr = cap.read()
1790 | +        if not ok:
1791 | +            break
1792 | +        g = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (64, 36)).astype(np.float32)
1793 | +        if prev is not None:
1794 | +            diffs.append((float(np.mean(np.abs(g - prev))), f))
1795 | +        prev = g
1796 | +    cap.release()
1797 | +    if len(diffs) < 3:
1798 | +        return mid
1799 | +    vals = np.array([d for d, _ in diffs])
1800 | +    k = int(np.argmax(vals))
1801 | +    return diffs[k][1] if vals[k] >= CUT_PEAK_RATIO * max(np.median(vals), 1e-3) else mid
1802 | +
1803 | +
1804 | +def classify(clip_path, detect=None):
1805 | +    """Per-shot plan for a prepared clip: {"shots": [{"start", "end", "class", "faces", ...}], ...}.
1806 | +    Times are clip-relative seconds, shot edges on frame boundaries."""
1807 | +    import cv2
1808 | +    if detect is None:
1809 | +        from face_scrfd import detect
1810 | +    w, h, fps, dur = _probe(clip_path)
1811 | +    cap = cv2.VideoCapture(clip_path)
1812 | +    n_frames = int(round(dur * fps))
1813 | +    times = np.arange(SAMPLE_S / 2, dur, SAMPLE_S)
1814 | +    samples = []
1815 | +    for t in times:
1816 | +        cap.set(cv2.CAP_PROP_POS_FRAMES, min(n_frames - 1, int(t * fps)))
1817 | +        ok, frame = cap.read()
1818 | +        label, fr = sample_label(detect(frame), w, h) if ok else ("uncertain", [])
1819 | +        samples.append({"t": round(float(t), 3), "class": label, "faces": [[round(a, 4), round(x), round(y)] for a, x, y in fr[:4]]})
1820 | +    cap.release()
1821 | +    if not samples:
1822 | +        raise RuntimeError(f"no frames sampled from {clip_path}")
1823 | +    labels = [s["class"] for s in samples]
1824 | +    runs = _runs(labels)
1825 | +    min_n = max(1, int(round(MIN_SHOT_S / SAMPLE_S)))
1826 | +    changed = True
1827 | +    while changed and len(runs) > 1:                      # absorb short runs into the longer neighbour
1828 | +        changed = False
1829 | +        for k, (lab, a, b) in enumerate(runs):
1830 | +            if b - a < min_n:
1831 | +                left = runs[k - 1] if k > 0 else None
1832 | +                right = runs[k + 1] if k + 1 < len(runs) else None
1833 | +                tgt = max([r for r in (left, right) if r], key=lambda r: r[2] - r[1])
1834 | +                for i in range(a, b):
1835 | +                    labels[i] = tgt[0]
1836 | +                runs = _runs(labels)
1837 | +                changed = True
1838 | +                break
1839 | +    edges = {}
1840 | +    for _, a, _b in runs[1:]:                             # refine each internal edge to the cut frame
1841 | +        mid = int(round((times[a - 1] + times[a]) / 2 * fps))
1842 | +        edges[a] = _cut_frame(clip_path, mid, int(round(SAMPLE_S * fps)), n_frames)
1843 | +    shots = []
1844 | +    for lab, a, b in runs:
1845 | +        start = 0.0 if a == 0 else round(edges[a] / fps, 4)
1846 | +        end = round(dur, 4) if b == len(times) else round(edges[b] / fps, 4)
1847 | +        faces = [s["faces"] for s in samples[a:b] if s["class"] == lab]
1848 | +        shot = {"start": start, "end": end, "class": lab, "flagged": lab in SAFE_FRAME,
1849 | +                "g4_layout": G4_LAYOUT[lab], "n_samples": b - a}
1850 | +        if lab == "single":
1851 | +            shot["face_cx"] = int(np.median([f[0][1] for f in faces]))
1852 | +            shot["face_cy"] = int(np.median([f[0][2] for f in faces]))
1853 | +        elif lab in ("stack2", "stack3"):
1854 | +            n = int(lab[-1])
1855 | +            per = [sorted(f[:n], key=lambda c: c[1]) for f in faces]    # each sample's n faces, left to right
1856 | +            shot["band_cx"] = [int(x) for x in np.median([[c[1] for c in p] for p in per], axis=0)]
1857 | +            shot["band_cy"] = [int(y) for y in np.median([[c[2] for c in p] for p in per], axis=0)]
1858 | +        shots.append(shot)
1859 | +    return {"clip": os.path.basename(clip_path), "width": w, "height": h, "fps": fps, "duration": round(dur, 4),
1860 | +            "rules": {"SAMPLE_S": SAMPLE_S, "SCREEN_FACE_FRAC": SCREEN_FACE_FRAC, "PROMINENT_FRAC": PROMINENT_FRAC,
1861 | +                      "MIN_BAND_RATIO": MIN_BAND_RATIO, "MIN_SHOT_S": MIN_SHOT_S},
1862 | +            "shots": shots, "samples": samples,
1863 | +            "flagged": any(s["flagged"] for s in shots)}
1864 | +
1865 | +
1866 | +# ── G4s LAYOUT TRUTH (DEC-2): a label must match the picture; safe frame only where labelled ──
1867 | +
1868 | +SAFE_FRAME_BAND = (656, 1264)   # render_vertical.LETTERBOX_VF: the 16:9 frame scaled to 1080x608, centred
1869 | +SAFE_FRAME_MIN_CORR = 0.90      # band vs the prepared frame, 64x36 grey, measured 2026-11-11: letterbox
1870 | +                                # 0.998-1.000 (Nov 10 9:16, 18 frames); v2f speaker crops <= 0.448 (24 frames)
1871 | +
1872 | +
1873 | +def _frame(path, t):
1874 | +    import cv2
1875 | +    cap = cv2.VideoCapture(path)
1876 | +    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
1877 | +    ok, f = cap.read()
1878 | +    cap.release()
1879 | +    return f if ok else None
1880 | +
1881 | +
1882 | +def _thumb(bgr):
1883 | +    import cv2
1884 | +    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
1885 | +    return cv2.resize(g, (64, 36), interpolation=cv2.INTER_AREA).astype(np.float64)
1886 | +
1887 | +
1888 | +def is_safe_frame(vert_bgr, src_bgr):
1889 | +    """True when a 1080x1920 frame is the safe frame: its centre band reproduces the WHOLE 16:9 source
1890 | +    frame of the same instant (normalised correlation >= SAFE_FRAME_MIN_CORR). A speaker crop or
1891 | +    stacked bands show part of the picture, never all of it; a plain or soft background cannot pass."""
1892 | +    if vert_bgr.shape[:2] != (1920, 1080):
1893 | +        return False, {"band_corr": None, "shape": list(vert_bgr.shape[:2])}
1894 | +    a, b = _thumb(vert_bgr[SAFE_FRAME_BAND[0]:SAFE_FRAME_BAND[1]]), _thumb(src_bgr)
1895 | +    a, b = a - a.mean(), b - b.mean()
1896 | +    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
1897 | +    r = float((a * b).sum() / d) if d > 0 else 0.0
1898 | +    return r >= SAFE_FRAME_MIN_CORR, {"band_corr": round(r, 3)}
1899 | +
1900 | +
1901 | +def gate_g4s(plans, prepared, vert_final=None, vert_segments=None, detect=None):
1902 | +    """plans {clip_id: plan}, prepared {clip_id: prepared clip path}. Each shot's label must equal the
1903 | +    majority class re-measured on that shot's own frames (never the label itself); in the 9:16 final the
1904 | +    shot must be a safe frame iff it is labelled screen/uncertain. Returns (ok, table)."""
1905 | +    if detect is None:
1906 | +        from face_scrfd import detect
1907 | +    import cv2
1908 | +    seg_start = {s["label"]: s["start"] for s in (vert_segments or [])}
1909 | +    table, ok_all = [], True
1910 | +    for cid, plan in plans.items():
1911 | +        for k, shot in enumerate(plan["shots"]):
1912 | +            times = [shot["start"] + (shot["end"] - shot["start"]) * (i + 0.5) / 5 for i in range(5)]
1913 | +            meas = []
1914 | +            for t in times:
1915 | +                f = _frame(prepared[cid], t)
1916 | +                meas.append(sample_label(detect(f), f.shape[1], f.shape[0])[0] if f is not None else "uncertain")
1917 | +            majority = max(set(meas), key=meas.count)
1918 | +            row = {"segment": cid, "shot": k, "label": shot["class"], "measured": meas, "label_ok": majority == shot["class"]}
1919 | +            if vert_final and cid in seg_start:
1920 | +                tm = (shot["start"] + shot["end"]) / 2
1921 | +                vf, sf = _frame(vert_final, seg_start[cid] + tm), _frame(prepared[cid], tm)
1922 | +                safe, m = is_safe_frame(vf, sf) if vf is not None and sf is not None else (None, {})
1923 | +                row.update(vertical_safe_frame=safe, **m,
1924 | +                           vertical_ok=safe is not None and safe == (shot["class"] in SAFE_FRAME))
1925 | +            row["pass"] = row["label_ok"] and row.get("vertical_ok", True)
1926 | +            ok_all &= row["pass"]
1927 | +            table.append(row)
1928 | +    return ok_all, table
1929 | +
1930 | +
1931 | +def layout_note(edl):
1932 | +    """Caption lines for the Telegram drop (DEC-2/DEC-5): every safe-frame shot named with its layout,
1933 | +    never silent; a segment without a measured layout is reported too. '' when every shot is reframed."""
1934 | +    lines = []
1935 | +    for label, seg in [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl.get("clips", [])]:
1936 | +        vl = seg.get("vertical_layout")
1937 | +        if not vl:
1938 | +            lines.append(f"9:16 {label} ({seg.get('channel')}): layout NOT MEASURED")
1939 | +            continue
1940 | +        spans = [f"layout={sh['class']}" + (" (speaker unidentified)" if sh["class"] == "uncertain" else "")
1941 | +                 + f" {sh['start']:.2f}-{sh['end']:.2f} s" for sh in vl["shots"] if sh["flagged"]]
1942 | +        if spans:
1943 | +            lines.append(f"9:16 SAFE FRAME {label} ({seg.get('channel')}): " + "; ".join(spans))
1944 | +    return "\n".join(lines)
1945 | +
1946 | +
1947 | +def per_shot_manifest(segments, plans):
1948 | +    """Manifest with each clip split into its shots (type talking_head, G4 layout per shot) so the
1949 | +    UNCHANGED gate_g4 applies the right face rule to every shot. Shot times are measured on the
1950 | +    prepared clip, lead-in pad included, so they map onto the timeline by the segment start alone."""
1951 | +    out = []
1952 | +    for s in segments:
1953 | +        plan = plans.get(s["label"]) if s.get("type") == "talking_head" else None
1954 | +        if not plan:
1955 | +            out.append(s)
1956 | +            continue
1957 | +        for k, sh in enumerate(plan["shots"]):
1958 | +            out.append({"label": f"{s['label']}#{k}", "type": "talking_head", "layout": sh["g4_layout"],
1959 | +                        "source_faces": int(sh["class"][-1]) if sh["class"].startswith("stack") else 1,
1960 | +                        "start": round(s["start"] + sh["start"], 3), "end": round(s["start"] + sh["end"], 3)})
1961 | +    return out
1962 | diff --git a/pipeline/word_diff.py b/pipeline/word_diff.py
1963 | new file mode 100644
1964 | index 00000000..c37d367b
1965 | --- /dev/null
1966 | +++ b/pipeline/word_diff.py
1967 | @@ -0,0 +1,144 @@
1968 | +#!/usr/bin/env python3
1969 | +"""pipeline/word_diff.py — G18 WORD-FOR-WORD (PBX 2026-11-11, mission 4a).
1970 | +
1971 | +Every clip in the final is transcribed (faster-whisper large-v3, en, beam 5, word timestamps, no VAD, NO
1972 | +prompt: a prompt would bias the ASR towards the expected words and hide a clipped edge) and must say:
1973 | +  (a) EDGES: its first and last two words are the first and last two words of its selection lock
1974 | +      (a clipped start, a lost ending or a run-on into the next sentence fails here: D1-D3);
1975 | +  (b) IDENTITY: exactly the words of the source span it was cut from [cut_in, cut_out], transcribed
1976 | +      the same way in isolation (a transition, concat or render that eats, repeats or adds a word fails).
1977 | +The middle of a clip cannot differ from its lock except by ASR rendering (the cut only places its two
1978 | +edges), so the full diff against the lock is REPORTED for the human, not gated: two whisper passes over the
1979 | +same audio render numbers ('$74,000' / '74 000' / 'seventy four thousand dollars') and disfluent repeats
1980 | +('of course of course' / 'of course') differently (measured on the Nov 10 fixture, 2026-11-11).
1981 | +Both sides are canonicalised alike: case, punctuation, number fragments ('88 ,000'), spelled numbers,
1982 | +currency/percent words after a number, immediate repeats of 1-3 words.
1983 | +"""
1984 | +import difflib
1985 | +import os
1986 | +import re
1987 | +import subprocess
1988 | +import tempfile
1989 | +
1990 | +ASR = {"model": "large-v3", "language": "en", "beam_size": 5, "word_timestamps": True, "vad_filter": False}
1991 | +EDGE_WORDS = 2
1992 | +
1993 | +_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
1994 | +                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
1995 | +_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
1996 | +_SCALES = {"hundred": 100, "thousand": 1000}   # whisper writes '74,000' but keeps '1.3 billion' as words
1997 | +_AFTER_NUMBER = {"dollars", "dollar", "percent", "per", "cent"}
1998 | +
1999 | +
2000 | +def _spelled_numbers(tokens):
2001 | +    out, i = [], 0
2002 | +    while i < len(tokens):
2003 | +        if tokens[i] in _UNITS or tokens[i] in _TENS:
2004 | +            total, cur, j = 0, 0, i
2005 | +            while j < len(tokens) and (tokens[j] in _UNITS or tokens[j] in _TENS or tokens[j] in _SCALES
2006 | +                                       or (tokens[j] == "and" and j + 1 < len(tokens) and tokens[j + 1] in _UNITS)):
2007 | +                t = tokens[j]
2008 | +                if t in _UNITS:
2009 | +                    cur += _UNITS[t]
2010 | +                elif t in _TENS:
2011 | +                    cur += _TENS[t]
2012 | +                elif t == "hundred":
2013 | +                    cur *= 100
2014 | +                elif t in _SCALES:
2015 | +                    total += max(cur, 1) * _SCALES[t]
2016 | +                    cur = 0
2017 | +                j += 1
2018 | +            out.append(str(total + cur))
2019 | +            i = j
2020 | +        else:
2021 | +            out.append(tokens[i])
2022 | +            i += 1
2023 | +    return out
2024 | +
2025 | +
2026 | +def norm(text):
2027 | +    t = (text or "").lower().replace("’", "'")
2028 | +    t = re.sub(r"(\d)\s+([.,]\d)", r"\1\2", t)            # '88 ,000' -> '88,000', '1 .3' -> '1.3'
2029 | +    t = re.sub(r"(\d)\s+(?=\d{3}\b)", r"\1", t)             # '74 000' -> '74000'
2030 | +    t = re.sub(r"\$\s+(\d)", r"$\1", t)
2031 | +    t = re.sub(r"\b(\w)\s+\.(?=\w)", r"\1.", t)              # 'u .s.' -> 'u.s.'
2032 | +    t = re.sub(r"\b([a-z])\.(?=[a-z]\b)", r"\1", t)            # 'u.s.' -> 'us.' (single-letter abbreviations)
2033 | +    t = re.sub(r"(?<=\d)[,](?=\d{3}\b)", "", t)             # '74,000' -> '74000'
2034 | +    t = re.sub(r"[^\w\s']", " ", t)                         # punctuation, '$', '%' (both sides alike)
2035 | +    t = re.sub(r"(?<!\w)'|'(?!\w)", "", t)                  # quote marks, not apostrophes
2036 | +    tokens = _spelled_numbers(t.split())
2037 | +    tokens = [w for k, w in enumerate(tokens)                # 'one point three' -> '1 3', like '1.3' -> '1 3'
2038 | +              if not (w == "point" and 0 < k < len(tokens) - 1 and tokens[k - 1].isdigit() and tokens[k + 1].isdigit())]
2039 | +    tokens = [w for k, w in enumerate(tokens) if not (w in _AFTER_NUMBER and k and (
2040 | +        tokens[k - 1].isdigit() or tokens[k - 1] in ("million", "billion", "trillion")))]
2041 | +    return _collapse_repeats(tokens)
2042 | +
2043 | +
2044 | +def _collapse_repeats(tokens):
2045 | +    out = []
2046 | +    for w in tokens:
2047 | +        out.append(w)
2048 | +        for n in (3, 2, 1):
2049 | +            if len(out) >= 2 * n and out[-n:] == out[-2 * n:-n]:
2050 | +                del out[-n:]
2051 | +                break
2052 | +    return out
2053 | +
2054 | +
2055 | +def diff(expected, heard):
2056 | +    """Word-level differences [(op, expected_words, heard_words)] after canonicalisation; [] if equal."""
2057 | +    e, h = norm(expected), norm(heard)
2058 | +    out = []
2059 | +    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, e, h, autojunk=False).get_opcodes():
2060 | +        if op != "equal":
2061 | +            out.append((op, " ".join(e[a0:a1]), " ".join(h[b0:b1])))
2062 | +    return out
2063 | +
2064 | +
2065 | +def edges(lock_text, heard, n=EDGE_WORDS):
2066 | +    """[] when the heard text starts and ends with the lock's first/last n canonical words."""
2067 | +    e, h = norm(lock_text), norm(heard)
2068 | +    out = []
2069 | +    if h[:n] != e[:n]:
2070 | +        out.append(("start", " ".join(e[:n]), " ".join(h[:n])))
2071 | +    if h[-n:] != e[-n:]:
2072 | +        out.append(("end", " ".join(e[-n:]), " ".join(h[-n:])))
2073 | +    return out
2074 | +
2075 | +
2076 | +class Transcriber:
2077 | +    def __init__(self):
2078 | +        from faster_whisper import WhisperModel
2079 | +        self.model = WhisperModel(ASR["model"], device="cuda", compute_type="float16")
2080 | +
2081 | +    def span(self, media, t0, t1):
2082 | +        with tempfile.TemporaryDirectory(prefix="g18_") as tmp:
2083 | +            wav = os.path.join(tmp, "span.wav")
2084 | +            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", media,
2085 | +                            "-vn", "-ac", "1", "-ar", "16000", wav], check=True, timeout=120)
2086 | +            segs, _ = self.model.transcribe(wav, language=ASR["language"], beam_size=ASR["beam_size"],
2087 | +                                            word_timestamps=ASR["word_timestamps"], vad_filter=ASR["vad_filter"])
2088 | +            return " ".join(w.word.strip() for s in segs for w in (s.words or []))
2089 | +
2090 | +
2091 | +def gate_g18(final_path, segments, clips, transcriber=None):
2092 | +    """segments: the final's manifest entries. clips: {label: {"lock_text", "source", "cut_in", "cut_out"}}.
2093 | +    Returns (ok, rows); each row carries the gated edge + identity diffs and the reported lock diff."""
2094 | +    tr = transcriber or Transcriber()
2095 | +    by_label = {s["label"]: s for s in segments}
2096 | +    rows, ok_all = [], True
2097 | +    for label, c in clips.items():
2098 | +        seg = by_label.get(label)
2099 | +        if seg is None:
2100 | +            rows.append({"segment": label, "pass": False, "error": "segment missing from the manifest"})
2101 | +            ok_all = False
2102 | +            continue
2103 | +        heard = tr.span(final_path, seg["start"], seg["end"])
2104 | +        src = tr.span(c["source"], c["cut_in"], c["cut_out"])
2105 | +        row = {"segment": label, "heard": heard, "source_span_heard": src, "lock_text": c["lock_text"],
2106 | +               "edges": edges(c["lock_text"], heard), "identity": diff(src, heard),
2107 | +               "lock_diff_reported": diff(c["lock_text"], heard)}
2108 | +        row["pass"] = not row["edges"] and not row["identity"]
2109 | +        ok_all &= row["pass"]
2110 | +        rows.append(row)
2111 | +    return ok_all, rows
2112 | diff --git a/scripts/pulse_check_run.sh b/scripts/pulse_check_run.sh
2113 | new file mode 100755
2114 | index 00000000..9584528d
2115 | --- /dev/null
2116 | +++ b/scripts/pulse_check_run.sh
2117 | @@ -0,0 +1,69 @@
2118 | +#!/usr/bin/env bash
2119 | +# scripts/pulse_check_run.sh — ONE command for a Pulse Check run (DEC-8 d, 2026-11-11). NOT installed in cron.
2120 | +#
2121 | +#   scripts/pulse_check_run.sh                    # AUTO: the engine's own top Bitcoin story (run_fresh.py)
2122 | +#   scripts/pulse_check_run.sh --pinned PIN.json  # PINNED (e.g. the corrected Nov 10 recut)
2123 | +#   options: --no-telegram   render + gates + verification pack only
2124 | +#            --foreground    run in this shell (default: a detached tmux session, see below)
2125 | +#
2126 | +# - one run at a time: flock on /tmp/pulse_check_run.lock (a second invocation exits 75 at once)
2127 | +# - tmux-safe: unless already inside a pipeline_* session (or --foreground), relaunches itself in a NEW
2128 | +#   detached session pipeline_pulse_check_<UTC stamp>; scripts/tmux_cleanup.sh (cron) keeps 'pipeline'
2129 | +#   sessions, so a long render is never reaped as idle. No other session is touched.
2130 | +# - GPU0 only (CUDA_VISIBLE_DEVICES=0); nothing is published: drops go to the Telegram approval chat
2131 | +#   only (pipeline/telegram.deliver_run): "HOLD FOR APPROVAL - all gates passed, no waivers" or
2132 | +#   "REVIEW ONLY" with the failing list.
2133 | +# - log: logs/pulse_check/run_<stamp>.log (git HEAD, run dir, exit code, delivery message ids)
2134 | +# Exit: run_fresh's code (0 = every gate passed, 3 = HOLD), 75 = locked, 64 = usage.
2135 | +set -uo pipefail
2136 | +REPO="$(cd "$(dirname "$0")/.." && pwd)"
2137 | +SELF="$REPO/scripts/pulse_check_run.sh"
2138 | +STAMP="$(date -u +%Y%m%d_%H%M%S)"
2139 | +
2140 | +FOREGROUND=0
2141 | +TELEGRAM=1
2142 | +ARGS=()
2143 | +ORIG=("$@")
2144 | +while [ $# -gt 0 ]; do
2145 | +  case "$1" in
2146 | +    --pinned) [ $# -ge 2 ] || { echo "usage: --pinned PIN.json" >&2; exit 64; }
2147 | +              ARGS+=(--pinned "$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"); shift 2 ;;
2148 | +    --no-telegram) TELEGRAM=0; shift ;;
2149 | +    --foreground) FOREGROUND=1; shift ;;
2150 | +    *) echo "unknown argument: $1" >&2; exit 64 ;;
2151 | +  esac
2152 | +done
2153 | +
2154 | +CUR_SESSION=""
2155 | +[ -n "${TMUX:-}" ] && CUR_SESSION="$(tmux display-message -p '#S' 2>/dev/null || true)"
2156 | +if [ "$FOREGROUND" = 0 ] && [[ "$CUR_SESSION" != pipeline_* ]]; then
2157 | +  NAME="pipeline_pulse_check_$STAMP"
2158 | +  tmux new-session -d -s "$NAME" "bash '$SELF' --foreground ${ORIG[*]}"
2159 | +  echo "started in tmux session $NAME (attach: tmux attach -t $NAME); log: $REPO/logs/pulse_check/"
2160 | +  exit 0
2161 | +fi
2162 | +
2163 | +LOG_DIR="$REPO/logs/pulse_check"
2164 | +mkdir -p "$LOG_DIR"
2165 | +LOG="$LOG_DIR/run_$STAMP.log"
2166 | +exec 9>/tmp/pulse_check_run.lock
2167 | +if ! flock -n 9; then
2168 | +  echo "pulse_check_run: another run holds /tmp/pulse_check_run.lock" | tee -a "$LOG" >&2
2169 | +  exit 75
2170 | +fi
2171 | +
2172 | +export CUDA_VISIBLE_DEVICES=0
2173 | +cd "$REPO/pipeline" || exit 1
2174 | +echo "=== pulse_check_run $STAMP | HEAD $(git -C "$REPO" rev-parse HEAD) | args: ${ARGS[*]:-auto} ===" | tee -a "$LOG"
2175 | +python3 run_fresh.py "${ARGS[@]}" 2>&1 | tee -a "$LOG"
2176 | +RC=${PIPESTATUS[0]}
2177 | +RUN_DIR="$(grep -m1 -oP '(?<==== FRESH-TOPIC RUN ).*(?= ===)' "$LOG" || true)"
2178 | +echo "run_fresh exit $RC | run dir ${RUN_DIR:-none}" | tee -a "$LOG"
2179 | +
2180 | +if [ "$TELEGRAM" = 1 ] && [ -n "$RUN_DIR" ] && [ -f "$RUN_DIR/out/segment.mp4" ] && [ -f "$RUN_DIR/out/segment_vertical.mp4" ]; then
2181 | +  python3 -c "import sys, telegram; r = telegram.deliver_run(sys.argv[1]); print('delivered:', [m.get('message_id') for m in r['messages']])" \
2182 | +    "$RUN_DIR" 2>&1 | tee -a "$LOG"
2183 | +elif [ "$TELEGRAM" = 1 ]; then
2184 | +  echo "no finals rendered: nothing delivered (the run's REPORT.md and status.json are the ledger)" | tee -a "$LOG"
2185 | +fi
2186 | +exit "$RC"
2187 | 
```

---

## YOUR REVIEW TASK: PULSE CHECK SENTENCE LAW / ONSET / CREDITS (Python pipeline, no UI, no DB)

The only file is the exact staged diff of ONE commit. Review that diff, nothing else.
Only state what you can verify from the diff shown. If uncertain, say so. Do not guess. Cite diff lines.

### Q1: CORRECTNESS
Does each changed function do what its docstring and the laws above say? Off-by-one in time/index
handling, wrong units (seconds vs ms), wrong comparisons, silent exceptions, state that leaks between
clips. Can any path produce a PASS (or a cut, a lock, a window) when data is missing or a model failed?

### Q2: LAW COMPLIANCE
For each law above: COMPLIANT / VIOLATION / PARTIAL with the diff line. In particular: can a cut move
outside the locked sentence's silence, can expected words be recomputed after selection, can a gate
threshold have been loosened, can the v2f reference path behave differently?

### Q3: TESTS
Do the tests prove the claim (must-fail fixtures FAIL for the right reason; controls PASS for the right
reason)? Any assertion that could pass vacuously?

### Q4: VERDICT
List every defect as: SEVERITY | diff line | issue | fix. End with READY or NOT READY.

