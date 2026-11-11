#!/usr/bin/env python3
"""pipeline/visual_check.py — contact sheet of the FINISHED video + the fixed visual checklist.

Orchestrator note 06:20 ET (PBX, from a session that cut a clean six-video medley: "make a sheet of the
finished video and read it before calling it done"). For every run and both formats:
  sheet      one still every SHEET_EVERY_S, one still BOUNDARY_FRAMES frames either side of every segment
             boundary (outside any dissolve), the credits card at full resolution, and (9:16) each talking
             head's first clean frame at full resolution; every still timestamped. Saved under qa/.
  checklist  six fixed questions answered FROM THE SHEET (not from measurements). In a supervised session
             a human/agent reads the sheet; unattended, the sheet goes to a Heimdall vision route that must
             answer JSON; any "no" (or no answer) is a HOLD. A check added on top of the gates, never a
             replacement for one.
"""
import base64
import json
import os
import re
import subprocess

FPS = 24
SHEET_EVERY_S = 2.0
BOUNDARY_FRAMES = 3
VISION_MODELS = ("qwen/qwen3.8-27b", "nvidia/nemotron-3.5-super-vl")   # Heimdall gateway, image input
                                           # (listed 2026-11-11); a "no" from EITHER holds
VISION_BASE = "https://api-staging.heimdallm.com/api/v1"

CHECKLIST = [
    ("credits_round_and_match", "On the credits card (full-resolution panel) every channel avatar is the channel's "
                                "own round PROFILE picture: not a video thumbnail (no headline text or title words "
                                "inside the circle), not squashed or stretched, and the names under the circles are "
                                "the channels whose clips appear in the video."),
    ("vertical_speaker_centred", "On a 9:16 sheet: every talking-head segment shows its speaker centred in the "
                                 "frame, or the segment is a shared screen / chart (layout=screen). On a 16:9 sheet: n/a."),
    ("no_letterbox_on_talking_heads", "Look at the full-resolution first-frame panels and the stills of every "
                                      "talking-head segment (a person speaking to camera). Answer 'no' if ANY of them "
                                      "shows the person inside a smaller horizontal picture band in the middle of the "
                                      "tall frame with blurred or black areas above and below it (letterbox). Answer "
                                      "'yes' only if every talking head fills the frame from top to bottom. On a 16:9 "
                                      "sheet: n/a."),
    ("no_bad_boundary_frames", "No frozen, black or duplicated frame at any segment boundary (the stills labelled "
                               "-3f / +3f)."),
    ("watermark_present", "The channel watermark / logo is visible on the content stills before the credits."),
    ("no_next_shot_before_transition", "In the '-3f' still before every boundary nothing from the NEXT shot is "
                                       "already visible."),
]


def _probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True, timeout=30)
    return float(r.stdout.strip())


def _grab(video, t, out, width=None):
    vf = ["-vf", f"scale={width}:-2"] if width else []
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1",
                        *vf, "-q:v", "2", out], check=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return out if os.path.exists(out) else None


def contact_sheet(final, segments, fmt, out_path, work_dir):
    """Build the timestamped sheet; returns {"path", "stills", "full_res"}. segments: the final's manifest."""
    from PIL import Image, ImageDraw
    os.makedirs(work_dir, exist_ok=True)
    dur = _probe_duration(final)
    vertical = fmt == "9x16"
    tw = 180 if vertical else 320
    cols = 10 if vertical else 6

    def seg_at(t):
        hits = [s["label"] for s in segments if s["start"] <= t < s["end"]]
        return "/".join(hits) or "-"
    items = []                                                  # (label, path)
    t = 0.0
    while t < dur - 0.05:
        items.append((f"{t:5.1f}s {seg_at(t)}", _grab(final, t, os.path.join(work_dir, f"g_{t:06.2f}.jpg"), tw)))
        t += SHEET_EVERY_S
    for a, b in zip(segments, segments[1:]):
        before = b["start"] - BOUNDARY_FRAMES / FPS            # A, before any dissolve
        after = a["end"] + BOUNDARY_FRAMES / FPS               # B, after any dissolve
        for tag, tt in (("-3f", before), ("+3f", after)):
            items.append((f"{a['label']}|{b['label']} {tag} {tt:.2f}s",
                          _grab(final, tt, os.path.join(work_dir, f"b_{a['label']}_{b['label']}_{tag}.jpg"), tw)))
    full = []
    sh = next((s for s in segments if s["label"] == "shoutout"), None)
    if sh:
        tm = (sh["start"] + sh["end"]) / 2
        full.append((f"credits card {tm:.2f}s (full resolution)", _grab(final, tm, os.path.join(work_dir, "full_credits.jpg"))))
    if vertical:
        for i, s in enumerate(segments):
            if s.get("type") != "talking_head":
                continue
            prev = segments[i - 1] if i else None
            t0 = max(s["start"], prev["end"] if prev and prev["end"] > s["start"] else s["start"]) + 1.0 / FPS
            full.append((f"{s['label']} first clean frame {t0:.2f}s (full resolution)",
                         _grab(final, t0, os.path.join(work_dir, f"full_{s['label']}.jpg"))))
    ims = [(lab, Image.open(p).convert("RGB")) for lab, p in items if p]
    fulls = [(lab, Image.open(p).convert("RGB")) for lab, p in full if p]
    th = ims[0][1].height if ims else 0
    rows = (len(ims) + cols - 1) // cols
    lab_h = 22
    grid_w = cols * tw
    full_w = sum(im.width for _, im in fulls) + 10 * max(0, len(fulls) - 1)
    full_h = (max(im.height for _, im in fulls) + lab_h) if fulls else 0
    W = max(grid_w, full_w)
    H = 40 + rows * (th + lab_h) + 20 + full_h
    sheet = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    d.text((8, 10), f"{os.path.basename(os.path.dirname(os.path.dirname(final)))} {fmt} contact sheet: "
                    f"{SHEET_EVERY_S:.0f} s stills, +-{BOUNDARY_FRAMES} frames at every boundary, full-res panels below",
           fill=(255, 255, 255))
    for k, (lab, im) in enumerate(ims):
        x, y = (k % cols) * tw, 40 + (k // cols) * (th + lab_h)
        d.text((x + 3, y + 4), lab, fill=(255, 220, 0))
        sheet.paste(im, (x, y + lab_h))
    x, y = 0, 40 + rows * (th + lab_h) + 20
    for lab, im in fulls:
        d.text((x + 4, y + 4), lab, fill=(255, 220, 0))
        sheet.paste(im, (x, y + lab_h))
        x += im.width + 10
    sheet.save(out_path, quality=90)
    return {"path": out_path, "stills": len(ims), "full_res": [lab for lab, _ in fulls], "size": [W, H]}


PROMPT = """You are checking a finished news video from its CONTACT SHEET (stills of the final video, each labelled
with its time; boundary stills labelled -3f / +3f; full-resolution panels at the bottom). Judge ONLY what you
can SEE on the sheet. Format of this sheet: {fmt}. {layout_note}
Answer every question with "yes", "no" or (only where the question allows it) "n/a", and a short reason:
{questions}
Reply with JSON only: {{"answers": {{"<key>": {{"answer": "yes|no|n/a", "why": "..."}}, ...}}}} using exactly the keys
{keys}."""


def _key():
    env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        with open(env) as f:
            return next(l.split("=", 1)[1].strip().strip('"\'') for l in f if l.startswith("HEIMDALL_API_KEY"))
    except (OSError, StopIteration):
        raise RuntimeError("vision route not configured: HEIMDALL_API_KEY not found in the repo .env") from None


def _first_json(content, key):
    """The first JSON object in a reply that carries `key` (prose or more braces around it are ignored)."""
    dec, s = json.JSONDecoder(), content or ""
    for m in re.finditer(r"\{", s):
        try:
            obj, _ = dec.raw_decode(s, m.start())
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and key in obj:
            return obj
    return None


def _parse(content):
    """The checklist answers of a reply; None when there are none."""
    return (_first_json(content, "answers") or {}).get("answers")


def _request(image_path, text, model):
    """One Heimdall vision request: a JPEG and a question."""
    import urllib.request
    img = base64.b64encode(open(image_path, "rb").read()).decode()
    body = {"model": model, "temperature": 0, "max_tokens": 16000, "reasoning": {"effort": "low"},
            "messages": [{"role": "user", "content": [{"type": "text", "text": text},
                                                      {"type": "image_url",
                                                       "image_url": {"url": f"data:image/jpeg;base64,{img}"}}]}]}
    return urllib.request.Request(f"{VISION_BASE}/chat/completions", data=json.dumps(body).encode(),
                                  headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"})


def _call(req, timeout):
    """(content, raw) of one vision call; raises on a route error (callers retry, then HOLD)."""
    import urllib.request
    raw = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return (raw.get("choices") or [{}])[0].get("message", {}).get("content") or "", raw


def ask_vision(sheet_path, fmt, layout_note="", model=VISION_MODELS[0], timeout=600, attempts=2):
    """The checklist answered by ONE Heimdall vision model from the sheet image: (answers, raw). An
    unparseable reply or a route error is retried, then answers = {} (every line missing = HOLD, never a crash)."""
    qs = "\n".join(f"- {k}: {q}" for k, q in CHECKLIST)
    text = PROMPT.format(fmt=fmt, layout_note=layout_note or "", questions=qs, keys=[k for k, _ in CHECKLIST])
    req = _request(sheet_path, text, model)
    tries = []
    for _ in range(attempts):
        try:
            content, raw = _call(req, timeout)
        except Exception as e:                      # network / HTTP / bad body: retried, then no answer = HOLD
            tries.append({"error": f"{type(e).__name__}: {e}"[:500]})
            continue
        tries.append({"finish_reason": (raw.get("choices") or [{}])[0].get("finish_reason"), "content": content[:4000]})
        answers = _parse(content)
        if isinstance(answers, dict):
            return answers, {"model": model, "content": content[:4000], "usage": raw.get("usage")}
    return {}, {"model": model, "unparseable": tries}


def ask_panel(sheet_path, fmt, layout_note=""):
    """Every VISION_MODEL answers; a line passes only if no model says no (fail closed)."""
    per = {m: ask_vision(sheet_path, fmt, layout_note, model=m) for m in VISION_MODELS}
    oks = {m: verdict(a, fmt) for m, (a, _) in per.items()}
    return all(ok for ok, _ in oks.values()), {m: {"rows": rows, "raw": per[m][1]} for m, (ok, rows) in oks.items()}


def verdict(answers, fmt):
    """PASS only when every checklist line is answered "yes" (or "n/a" where allowed). Missing = no."""
    rows = {}
    for k, _ in CHECKLIST:
        val = answers.get(k) if isinstance(answers.get(k), dict) else {}   # a malformed line is a missing one
        a = str(val.get("answer", "")).strip().lower()
        allowed_na = k in ("vertical_speaker_centred", "no_letterbox_on_talking_heads") and fmt == "16x9"
        rows[k] = {"answer": a or "missing", "why": val.get("why", ""),
                   "ok": a == "yes" or (a == "n/a" and allowed_na)}
    return all(r["ok"] for r in rows.values()), rows


# ── letterbox, ONE frame per shot (06:50 ET: asked about the whole sheet, both models missed yesterday's
#    letterboxed talking heads; asked about one frame, both answered right; E-FAIL-022) ──

LETTERBOX_PROMPT = """This is ONE frame of a vertical (9:16) news video. Look at how the picture is laid out from top to
bottom. Question: is the SHARP picture only a horizontal band across the middle of the frame, with a BLURRED (or
black) enlarged copy of the image filling the areas above and below that band? (This is called a letterbox.)
Reply with JSON only: {"letterboxed": "yes|no", "why": "..."}"""


def shot_frames(final, segments, layout, work_dir):
    """One full-resolution frame from the middle of every shot of every 9:16 talking-head segment, with the
    shot's class from VERTICAL_LAYOUT.json (shot times are relative to the segment's prepared clip, whose first
    frame is the segment's start in the final); a frame inside a dissolve is moved out of it. A segment without
    a measured layout is one shot of class 'unknown' (asked like a talking head)."""
    os.makedirs(work_dir, exist_ok=True)
    layout, out = layout or {}, []
    for i, s in enumerate(segments):
        if s.get("type") != "talking_head":
            continue
        lo = max(s["start"], segments[i - 1]["end"] if i else s["start"]) + 1.0 / FPS
        hi = min(s["end"], segments[i + 1]["start"] if i + 1 < len(segments) else s["end"]) - 1.0 / FPS
        shots = (layout.get(s["label"]) or {}).get("shots") or \
            [{"start": 0.0, "end": s["end"] - s["start"], "class": "unknown"}]
        for k, sh in enumerate(shots):
            t = min(max(s["start"] + (sh["start"] + sh["end"]) / 2, lo), hi) if lo <= hi else \
                (s["start"] + s["end"]) / 2                     # (a segment shorter than two frames)
            out.append({"label": s["label"], "shot": k, "t": round(t, 3), "class": sh.get("class", "unknown"),
                        "path": _grab(final, t, os.path.join(work_dir, f"shot_{s['label']}_{k}.jpg"))})
    return out


def ask_letterbox(path, model, timeout=600, attempts=2, trail=None):
    """'yes' / 'no' from one model about one frame, or None (no clear answer after the retries). Every attempt
    (error, or the reply's answer and reason) is appended to `trail` when given (it lands in GATE_REPORT)."""
    trail = [] if trail is None else trail
    req = _request(path, LETTERBOX_PROMPT, model)
    for _ in range(attempts):
        try:
            content, _raw = _call(req, timeout)
        except Exception as e:                      # route error: retried, then no answer
            trail.append({"error": f"{type(e).__name__}: {e}"[:300]})
            continue
        obj = _first_json(content, "letterboxed") or {}
        a = str(obj.get("letterboxed", "")).strip().lower()
        trail.append({"answer": a or "unparseable", "why": str(obj.get("why", content))[:300]})
        if a in ("yes", "no"):
            return a
    return None


def letterbox_check(frames):
    """Every non-screen shot asked of every VISION_MODEL. Letterboxed 'yes', no answer, a missing frame or an
    error from ANY model fails the line (fail closed). A screen shot is letterboxed by design (DEC-2) and is
    not asked."""
    rows, ok = [], True
    for f in frames:
        if f["class"] == "screen":
            rows.append({**f, "asked": False, "ok": True, "why": "layout=screen: letterbox by design (DEC-2)"})
            continue
        ans, trails, err = {}, {}, None
        for m in VISION_MODELS:
            trails[m] = []
            try:
                ans[m] = ask_letterbox(f["path"], m, trail=trails[m]) if f["path"] else None
            except Exception as e:                  # e.g. the route is not configured
                ans[m], err = None, f"{type(e).__name__}: {e}"
        good = bool(ans) and all(a == "no" for a in ans.values())     # no model asked = no answer = FAIL
        ok = ok and good
        rows.append({**f, "asked": True, "answers": ans, "trail": trails, "ok": good, **({"error": err} if err else {})})
    return ok, rows
