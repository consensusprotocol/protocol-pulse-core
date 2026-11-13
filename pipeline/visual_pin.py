"""pipeline/visual_pin.py: RULING 70 (orchestrator 15:29 Nov 13), the pin-stage VISUAL check.

"One contact sheet per clip, the three questions including lower_third; xAI first, Heimdall image models as failover;
fail closed. A finding on third_person or on_screen_text does not reject the clip by itself: it is sealed as a FLAG
that I and PBX see with the pin (text of the finding + the sheet), and a clip with a third_person finding may not be
the HOOK unless the claim in the words is confirmed as reported fact by step A's context. lower_third feeds ruling 69
as one more piece of evidence, never alone. Report the measured cost on the first build."

Per clip (a moment's [start, end]):
- fetch(): the span's video at <= 480p, yt-dlp download sections on CPU (as transcript_truth.audio_window fetches its
  audio).
- sheet(): at most TILES stills (the cut-in frame, one every EVERY_S seconds, the last frame), each labelled with its
  time in the source, in ONE JPEG contact sheet (ffmpeg on CPU, PIL to tile). No GPU.
- ONE verdict (role visual_check: xai_vision:grok-4.7, then the Heimdall image models), JSON, checked in code
  (check()). A reply out of contract, or no answer, is retried once with a new seed, then the clip is NOT measured:
  it cannot be sealed (law L-m).
- flags(): a third_person finding (a person other than the speaker shown as a still, photo or graphic while the words
  make a negative claim) and every on-screen text that asserts more than the words. They are sealed, never a reject.
- hook_block(): why the clip may not be the HOOK, or None. Step A passes only a clip whose view is "own_sincere" (the
  speaker's own assertion: context_integrity.a_failures), so no step-A verdict confirms a claim as REPORTED fact; a
  third_person finding therefore blocks the hook (fail closed) until step A is asked that.
Verdicts are cached per moment and span (cache=), like step A's: a clip is paid for once across builds."""
import base64
import hashlib
import json
import os
import subprocess
import threading

VERSION = "visual-1"
ROLE = "visual_check"
TILES, EVERY_S, TILE_W = 8, 2.0, 480
HOW = ("still", "photo", "graphic", "none")
FORMAT = "bv*[height<=480][ext=mp4]/bv*[height<=480]/b[height<=480]"
CACHE_LOCK = threading.Lock()
TEXTS_MAX, TEXT_CHARS = 12, 200          # audit 1541 C2: a verbose reply never bloats the sealed pin

PROMPT = """You check what a VIEWER SEES in one clip of another channel's video, before it is cut into ours.
The image is a contact sheet of {n} frames of the clip, left to right and top to bottom, each labelled with its time in
the source video (seconds). The clip's words, as spoken:
"{text}"

Answer three questions from the frames only:
1. third_person: is a person who is NOT the one speaking shown as a STILL, a PHOTO or a GRAPHIC (not live video of a
   person taking part in the show) while the clip's words make a NEGATIVE claim (a mistake, an accusation, a scandal,
   a crime, a failure)? Report any NAME the screen shows as TEXT with that person. Never name anyone from a face: only
   text on the screen names a person.
2. on_screen_text: every headline graphic, chyron, banner or title card the SOURCE shows (not subtitles of the spoken
   words, not the channel's logo), copied exactly, each with whether it ASSERTS something the clip's words do not.
3. lower_third: the on-screen name strap (lower third) of the person speaking, copied exactly, or null.

Return ONLY this JSON object:
{{"third_person": {{"shown": true or false, "how": "still|photo|graphic|none", "words_negative": true or false,
  "name_on_screen": "<the on-screen text naming them> or null", "finding": "<one sentence>"}},
 "on_screen_text": [{{"text": "...", "asserts_beyond_words": true or false, "why": "..."}}],
 "lower_third": {{"name": "<the name on the strap> or null", "text": "<the strap's full text> or null"}}}}"""


def load_cache(path):
    try:
        with open(path) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(path, cache):
    if not path:
        return
    with CACHE_LOCK:
        with open(path + ".tmp", "w") as f:
            json.dump(cache, f, indent=1, sort_keys=True)
        os.replace(path + ".tmp", path)


def key(m):
    """The cache key: the moment and span, VERSION, and a digest of everything else the verdict reads (the clip's
    words, the prompt, the sheet's parameters; audit 1541 C1). A hit is used only on the same sheet bytes."""
    inputs = json.dumps([PROMPT, TILES, EVERY_S, TILE_W, FORMAT, str(m.get("text") or "")])
    return (f"{m['moment_id']}:{float(m['start']):.3f}-{float(m['end']):.3f}:{VERSION}:"
            f"{hashlib.sha256(inputs.encode()).hexdigest()[:16]}")


def _sha_of(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def times(dur, every=EVERY_S, tiles=TILES):
    """The stills' offsets in the clip: the cut-in frame, one every `every` seconds, the last frame; at most `tiles`,
    the first and the last always kept."""
    last = max(0.0, dur - 0.05)
    ts = [0.0]
    t = every
    while t < last - 0.25:
        ts.append(round(t, 2))
        t += every
    if last > 0:
        ts.append(round(last, 2))
    if len(ts) > tiles:                                  # too many for one sheet: evenly spaced, both ends kept
        ts = [round(last * i / (tiles - 1), 2) for i in range(tiles)]
    return ts


def fetch(video_id, start, end, work_dir):
    """The span's video at <= 480p (yt-dlp download sections, CPU) -> the file's path."""
    d = os.path.join(work_dir, "visual")
    os.makedirs(d, exist_ok=True)
    stem = f"{video_id}_{int(start * 1000)}_{int(end * 1000)}"
    have = [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[0] == stem and not f.endswith(".jpg")]
    if not have:
        subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", FORMAT, "--download-sections",
                        f"*{start:.2f}-{end:.2f}", "--force-keyframes-at-cuts", "-o", os.path.join(d, stem + ".%(ext)s"),
                        f"https://www.youtube.com/watch?v={video_id}"], check=True, timeout=300, capture_output=True)
        have = [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[0] == stem and not f.endswith(".jpg")]
    if not have:
        raise OSError(f"no video fetched for {stem}")
    return os.path.join(d, have[0])


def sheet(video, start, end, work_dir):
    """ONE contact sheet of the clip -> (its path, sha256, the stills' source times)."""
    from PIL import Image, ImageDraw
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                       capture_output=True, text=True, check=True, timeout=30)
    dur = min(float(r.stdout.strip()), end - start)
    offs = times(dur)
    d = os.path.join(work_dir, "visual")
    tiles = []
    for i, t in enumerate(offs):
        out = os.path.join(d, f"_still_{os.getpid()}_{threading.get_ident()}_{i}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf",
                        f"scale={TILE_W}:-2", "-q:v", "3", out], check=True, timeout=60)
        with Image.open(out) as im:
            tiles.append(im.convert("RGB").copy())
        os.remove(out)
    cols = min(4, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    w, h = tiles[0].size
    canvas = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    for i, (im, t) in enumerate(zip(tiles, offs)):
        x, y = (i % cols) * w, (i // cols) * h
        canvas.paste(im.resize((w, h)), (x, y))
        label = f"{start + t:.2f} s"
        draw.rectangle([x, y, x + 9 * len(label), y + 16], fill=(0, 0, 0))
        draw.text((x + 3, y + 2), label, fill=(255, 255, 255))
    tmp = os.path.join(d, f"_sheet_{os.getpid()}_{threading.get_ident()}.jpg")
    canvas.save(tmp, "JPEG", quality=85)
    with open(tmp, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    path = os.path.join(d, f"visual_{sha[:16]}.jpg")
    os.replace(tmp, path)
    return path, sha, [round(start + t, 2) for t in offs]


def _json(text):
    t = str(text or "")
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < a:
        raise ValueError("no JSON object in the reply")
    return json.loads(t[a:b + 1])


def _opt_str(x):
    return x.strip() if isinstance(x, str) and x.strip() and x.strip().lower() not in ("null", "none") else None


def check(v):
    """The verdict, in contract or ValueError -> {"third_person", "on_screen_text", "lower_third"}."""
    if not isinstance(v, dict) or set(v) != {"third_person", "on_screen_text", "lower_third"}:
        raise ValueError("keys must be exactly third_person, on_screen_text, lower_third")
    tp, ost, lt = v["third_person"], v["on_screen_text"], v["lower_third"]
    if not isinstance(tp, dict) or type(tp.get("shown")) is not bool or tp.get("how") not in HOW or \
            type(tp.get("words_negative")) is not bool or not isinstance(tp.get("finding"), str):
        raise ValueError("third_person out of contract")
    if not isinstance(ost, list) or any(not isinstance(x, dict) or not isinstance(x.get("text"), str) or
                                        type(x.get("asserts_beyond_words")) is not bool for x in ost):
        raise ValueError("on_screen_text out of contract")
    if not isinstance(lt, dict):
        raise ValueError("lower_third out of contract")
    texts = [x for x in ost if x["text"].strip()]
    keep = sorted(texts, key=lambda x: not x["asserts_beyond_words"])[:TEXTS_MAX]   # the asserting ones first
    return {"third_person": {"shown": tp["shown"], "how": tp["how"], "words_negative": tp["words_negative"],
                             "name_on_screen": _opt_str(tp.get("name_on_screen")),
                             "finding": tp["finding"].strip()[:TEXT_CHARS]},
            "on_screen_text": [{"text": x["text"].strip()[:TEXT_CHARS], "asserts_beyond_words": x["asserts_beyond_words"],
                                "why": str(x.get("why") or "").strip()[:TEXT_CHARS]} for x in keep],
            **({"on_screen_text_truncated": len(texts) - len(keep)} if len(texts) > len(keep) else {}),
            "lower_third": {"name": _opt_str(lt.get("name")), "text": _opt_str(lt.get("text"))}}


def flags(v):
    """RULING 70: the findings sealed as FLAGS (never a reject by themselves)."""
    out = []
    tp = v["third_person"]
    if tp["shown"] and tp["how"] in ("still", "photo", "graphic") and tp["words_negative"]:
        out.append({"kind": "third_person", "text": tp["finding"], "name_on_screen": tp["name_on_screen"]})
    out += [{"kind": "on_screen_text", "text": x["text"], "why": x["why"]} for x in v["on_screen_text"]
            if x["asserts_beyond_words"]]
    return out


def hook_block(rec):
    """Why this clip may not be the HOOK (ruling 70), or None."""
    if not (rec or {}).get("measured"):
        return "its visual check is not measured (law L-m)"
    tp = next((f for f in rec.get("flags") or [] if f["kind"] == "third_person"), None)
    if tp is not None:                           # audit 1541 C2: what the sheet showed, not only that it blocked
        return ("ruling 70: a third person is shown as a still while the words make a negative claim, and step A's "
                "context does not confirm the claim as reported fact (step A passes only the speaker's own view): "
                f"{tp['text'][:TEXT_CHARS]}" + (f" (on screen: {tp['name_on_screen']})" if tp.get("name_on_screen")
                                                else ""))
    return None


def sealed(rec):
    """The part of a visual record a pin seals (package_pin.SEALED_LATER "visual"): the findings, the flags, the sheet's
    name, sha256 and times (the sheet itself is copied beside the pin), the back-end. Never a scratch path or a cost."""
    out = {k: rec[k] for k in ("version", "measured", "flags", "third_person", "on_screen_text", "lower_third",
                               "backend", "replayed", "why") if k in rec}
    if isinstance(rec.get("sheet"), dict):
        out["sheet"] = {k: rec["sheet"][k] for k in ("name", "sha256", "times") if k in rec["sheet"]}
    return out


def visual_for(router, m, work_dir, cache, seed=7, log=print):
    """The clip's visual record (cached per moment and span). Not measured on any failure: never a pass (law L-m).
    -> {"version", "measured", "flags", "third_person", "on_screen_text", "lower_third", "sheet" {"name", "sha256",
    "times", "path"}, "backend", "replayed", "usd", "cached"} or {"measured": False, "why"}."""
    import providers as P
    k = key(m)
    hit = cache.get(k) if cache is not None and (cache.get(k) or {}).get("measured") else None
    if hit is not None:                              # the judged sheet, still on disk with the judged bytes
        p = os.path.join(work_dir, "visual", (hit.get("sheet") or {}).get("name") or "-")
        if _sha_of(p) == (hit.get("sheet") or {}).get("sha256"):
            return dict(hit, cached=True, usd=0.0, sheet=dict(hit["sheet"], path=p))
    try:
        video = fetch(m["video_id"], float(m["start"]), float(m["end"]), work_dir)
        path, sha, ts = sheet(video, float(m["start"]), float(m["end"]), work_dir)
        if hit is not None and sha == hit["sheet"]["sha256"]:        # rebuilt, the same bytes: the same verdict
            return dict(hit, cached=True, usd=0.0, sheet=dict(hit["sheet"], path=path))
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
    except Exception as e:                       # noqa: BLE001  no sheet: not measured (law L-m), never a crash
        return {"version": VERSION, "measured": False, "why": f"no contact sheet: {type(e).__name__}: {str(e)[:160]}"}
    prompt = {"text": PROMPT.format(n=len(ts), text=str(m.get("text") or "").replace('"', "'")), "images": [b64]}
    why = None
    for sd in (seed, seed + 1):
        r = None
        try:
            r = router.call(ROLE, prompt, 1500, sd)
            v = check(_json(r.text))
            rec = {"version": VERSION, "measured": True, **v, "flags": flags(v),
                   "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path},
                   "backend": r.backend, "replayed": bool(getattr(r, "replayed", False)),
                   "usd": 0.0 if getattr(r, "cached", False) else float(getattr(r, "usd", 0.0) or 0.0),
                   "usage": getattr(r, "usage", None), "cached": bool(getattr(r, "cached", False))}
            if cache is not None and not rec["replayed"]:
                cache[k] = {x: y for x, y in rec.items() if x not in ("cached", "usd")}
            return rec
        except Exception as e:                   # noqa: BLE001  fail closed; each try's reason is kept (C2)
            if r is not None and not isinstance(e, (P.ProviderError, P.SpendLimit)) and hasattr(router, "reject"):
                router.reject(r)
            kind = "no back-end answered" if isinstance(e, (P.ProviderError, P.SpendLimit)) else "out of contract"
            why = (f"{why}; then " if why else "") + f"seed {sd}: {kind}: {type(e).__name__}: {str(e)[:200]}"
    return {"version": VERSION, "measured": False, "why": f"no verdict in contract after two tries: {why}",
            "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path}}
