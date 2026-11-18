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
- RULING 93 (23:58 ET Nov 13): question 4 (burned_in): every ticker, crawl, lower third or channel bug burned into
  the source, and how the 9:16 version treats it. layout_block(): a ticker or crawl, or a lower third or bug that is
  not wholly in the 16:9, that the 9:16 edge would cut mid-word, or that covers the speaker, makes the clip NOT
  eligible in any role (per clip, never by channel name); one that sits whole in the 16:9 and wholly in or out of the
  9:16 is eligible and sealed as a "burned_in" FLAG for the orchestrator.
- RULING 93 AMENDED (orchestrator 21:10 ET Nov 14), visual-3: the source's own BURNED CAPTIONS of the spoken words are
  asked for explicitly (question 4's kind "caption", with the frame times each shows in), on a sheet of one frame a
  second (TILES 36, the 35 s ceiling). Visual-2 asked to leave "subtitles of the spoken words" out, twice, and missed
  Blockware's. A caption never makes a clip ineligible: one the 9:16 crop cuts mid-word makes it 16:9-ONLY (formats():
  "formats": ["16x9"], sealed in the visual record), and each caption is flagged ("burned_caption").
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

VERSION = "visual-3"                     # RULING 93 AMENDED (21:10 ET Nov 14): the source's burned captions asked for
ROLE = "visual_check"                    #   explicitly, one frame a second (visual-2: ruling 93, 23:58 ET Nov 13)
TILES, EVERY_S, TILE_W, COLS = 40, 1.0, 320, 6   # 21:10 Nov 14: "at least one frame a second across the span" (the
#   35 s ceiling takes 36; 40 leaves room); 6 x 320 px across keeps the sheet 1920 px wide (visual-2 sampled 8 at 480 px:
#   one every 3.27 s on Blockware's 22.94 s, and its question excluded the captions it showed)
HOW = ("still", "photo", "graphic", "none")
BURNED = ("ticker", "crawl", "lower_third", "bug", "caption")   # ruling 93: question 4's kinds; "caption" (ruling 93
CAPTION = "caption"                                    # amended): the source's own burned subtitles of the words
RENDER_16X9_ONLY = True       # the integrator's format-aware release LANDED (c396c3c8, its message 21:55 ET Nov 14: run_fresh,
#   release_auth and the review drop read moments_package["formats"], exactly ["16x9"] or ["16x9", "9x16"]): a 16:9-only
#   clip is eligible and sealed with formats ["16x9"]. Until then it was HELD here (layout_block, with this False).
RUNNING = ("ticker", "crawl")                          # ruling 93: "a ticker or crawl = not eligible"
IN_9X16 = ("whole", "out", "cut")
FORMAT = "bv*[height<=480][ext=mp4]/bv*[height<=480]/b[height<=480]"
CACHE_LOCK = threading.Lock()
TEXTS_MAX, TEXT_CHARS = 12, 200          # audit 1541 C2: a verbose reply never bloats the sealed pin

PROMPT = """You check what a VIEWER SEES in one clip of another channel's video, before it is cut into ours.
The image is a contact sheet of {n} frames of the clip, left to right and top to bottom, each labelled with its time in
the source video (seconds). The clip's words, as spoken:
"{text}"

Answer four questions from the frames only:
1. third_person: is a person who is NOT the one speaking shown as a STILL, a PHOTO or a GRAPHIC (not live video of a
   person taking part in the show) while the clip's words make a NEGATIVE claim (a mistake, an accusation, a scandal,
   a crime, a failure)? Report any NAME the screen shows as TEXT with that person. Never name anyone from a face: only
   text on the screen names a person.
2. on_screen_text: every headline graphic, chyron, banner or title card the SOURCE shows (not its captions of the
   spoken words, which are question 4's; not the channel's logo), copied exactly, each with whether it ASSERTS
   something the clip's words do not.
3. lower_third: the on-screen name strap (lower third) of the person speaking, copied exactly, or null.
4. burned_in: every piece of text or graphic burned into the SOURCE picture: a ticker or a crawl (text that runs or
   scrolls across the frame), a lower third (a name or headline strap), a channel bug (a logo or watermark), AND THE
   SOURCE'S OWN BURNED-IN CAPTIONS OR SUBTITLES of the spoken words (kind "caption": styled words that show what is
   being said, often large and animated, word by word or phrase by phrase). Look at EVERY frame: list each distinct
   caption text you can read as its own item, copied exactly, with "at": the frame times (seconds) it shows in.
   For each item say whether it sits WHOLLY inside the frame, and how the
   VERTICAL 9:16 version would treat it. The 9:16 version shows, for ONE speaker, a full-height strip about one third
   of the frame's width, centred on the speaker's face; for two or three people, a band around each face, stacked; for
   a shared screen (a chart, a slide, b-roll), the whole frame. "in_9x16" is "whole" (wholly inside the 9:16 picture),
   "out" (wholly outside it) or "cut" (the 9:16 edge would cut through it mid-word). FOR A CAPTION the strip may slide
   left or right, but only so far that the speaker's WHOLE face stays inside it with a margin (a tenth of the frame's
   width from either edge): "whole" if ONE such position shows the caption whole, "cut" if every such position cuts it
   mid-word, "out" if it lies outside every such position. "covers_speaker": does it cover the speaking person's face
   or mouth? An empty list means you read NO text at all burned into any frame.

Return ONLY this JSON object:
{{"third_person": {{"shown": true or false, "how": "still|photo|graphic|none", "words_negative": true or false,
  "name_on_screen": "<the on-screen text naming them> or null", "finding": "<one sentence>"}},
 "on_screen_text": [{{"text": "...", "asserts_beyond_words": true or false, "why": "..."}}],
 "lower_third": {{"name": "<the name on the strap> or null", "text": "<the strap's full text> or null"}},
 "burned_in": [{{"kind": "ticker|crawl|lower_third|bug|caption", "text": "<its text, copied>",
   "whole_in_16x9": true or false, "in_9x16": "whole|out|cut", "covers_speaker": true or false,
   "at": [<the frame times it shows in, seconds>]}}]}}"""


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
    inputs = json.dumps([PROMPT, TILES, EVERY_S, TILE_W, COLS, FORMAT, str(m.get("text") or "")])
    return (f"{m['moment_id']}:{float(m['start']):.3f}-{float(m['end']):.3f}:{VERSION}:"
            f"{hashlib.sha256(inputs.encode()).hexdigest()[:16]}")


def _sha_of(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def times(dur, every=EVERY_S, tiles=TILES):
    """The stills' offsets in the clip: the cut-in frame, one every `every` seconds, the last frame (so no gap is ever
    longer than `every`); at most `tiles`, the first and the last always kept."""
    last = max(0.0, dur - 0.05)
    ts = [0.0]
    t = every
    while t < last - 0.01:
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
    import transcript_truth as TT
    cut = os.path.join(d, stem + ".cut.mp4")                    # RULING 142 (3): a post_live span cut before, whole
    whole_cut = lambda: os.path.exists(cut) and TT.media_seconds(cut) >= TT.MIN_SECTION_SHARE * (end - start)
    if not have and whole_cut():                                # (audit 20261117_1556 C1 qwen: never a partial one)
        return cut
    if not have:
        subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", FORMAT, "--download-sections",
                        f"*{start:.2f}-{end:.2f}", "--force-keyframes-at-cuts", "-o", os.path.join(d, stem + ".%(ext)s"),
                        f"https://www.youtube.com/watch?v={video_id}"], check=True, timeout=300, capture_output=True)
        have = [f for f in sorted(os.listdir(d)) if os.path.splitext(f)[0] == stem and not f.endswith(".jpg")]
    path = os.path.join(d, have[0]) if have else None
    if path is not None and TT.media_seconds(path) >= TT.MIN_SECTION_SHARE * (end - start):
        return path
    #   RULING 142 (3): a post_live stream's empty (or absent) section: the whole
    if not whole_cut():                                                # stream once (<= 480p), the span cut here
        whole = TT.whole_stream(video_id, FORMAT, d, "video")
        tmp = os.path.join(d, stem + ".cut.tmp.mp4")                  # renamed into place only whole
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-i", whole, "-t",
                        f"{end - start:.3f}", "-an", "-vf", "scale=-2:'min(480,ih)'", "-c:v", "libx264", "-preset",
                        "veryfast", "-crf", "28", tmp],
                       check=True, timeout=300)
        if TT.media_seconds(tmp) < TT.MIN_SECTION_SHARE * (end - start):
            os.remove(tmp)
            raise OSError(f"no video in the section or the whole stream for {stem}")
        os.replace(tmp, cut)
    return cut


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
    cols = min(COLS, len(tiles))
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
    """The verdict, in contract or ValueError -> {"third_person", "on_screen_text", "lower_third", "burned_in"}."""
    if not isinstance(v, dict) or set(v) != {"third_person", "on_screen_text", "lower_third", "burned_in"}:
        raise ValueError("keys must be exactly third_person, on_screen_text, lower_third, burned_in")
    tp, ost, lt, bi = v["third_person"], v["on_screen_text"], v["lower_third"], v["burned_in"]
    if not isinstance(bi, list) or any(
            not isinstance(x, dict) or x.get("kind") not in BURNED or not isinstance(x.get("text"), (str, type(None)))
            or type(x.get("whole_in_16x9")) is not bool or x.get("in_9x16") not in IN_9X16 or
            type(x.get("covers_speaker")) is not bool or
            (x["kind"] == CAPTION and not (x.get("text") or "").strip()) or
            not isinstance(x.get("at", []), list) or
            any(type(a) not in (int, float) for a in x.get("at") or []) for x in bi):   # a wordless bug may carry
        raise ValueError("burned_in out of contract (ruling 93)")                          # no text; a caption must
    items = [{"kind": x["kind"], "text": (x.get("text") or "").strip()[:TEXT_CHARS],
              "whole_in_16x9": x["whole_in_16x9"], "in_9x16": x["in_9x16"], "covers_speaker": x["covers_speaker"],
              **({"at": sorted({round(float(a), 2) for a in x["at"]})[:TILES]} if x.get("at") else {})}
             for x in bi]
    items = sorted(items, key=lambda x: (burned_block(x) is None,              # the blocking ones first, then a
                                         not (x["kind"] == CAPTION and x["in_9x16"] == "cut")))   # cut caption (audit
    #   2131 C1, glm: the 16:9-only decision must survive TEXTS_MAX), so a cut never hides
    #   one (audit 0003 C1, glm: a ticker listed 13th would otherwise pass)
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
            "lower_third": {"name": _opt_str(lt.get("name")), "text": _opt_str(lt.get("text"))},
            "burned_in": items[:TEXTS_MAX],
            **({"burned_in_truncated": len(items) - TEXTS_MAX} if len(items) > TEXTS_MAX else {})}


def flags(v):
    """RULING 70: the findings sealed as FLAGS (never a reject by themselves)."""
    out = []
    tp = v["third_person"]
    if tp["shown"] and tp["how"] in ("still", "photo", "graphic") and tp["words_negative"]:
        out.append({"kind": "third_person", "text": tp["finding"], "name_on_screen": tp["name_on_screen"]})
    out += [{"kind": "on_screen_text", "text": x["text"], "why": x["why"]} for x in v["on_screen_text"]
            if x["asserts_beyond_words"]]
    out += [{"kind": "burned_in", "text": x["text"], "item": x["kind"], "in_9x16": x["in_9x16"]}   # ruling 93: an
            for x in v.get("burned_in") or [] if not burned_block(x) and x["kind"] != CAPTION]   # eligible lower
    out += [{"kind": "burned_caption", "text": x["text"], "in_9x16": x["in_9x16"],              # third or bug, and
             **({"at": x["at"]} if x.get("at") else {})}                                          # (ruling 93 amended)
            for x in v.get("burned_in") or [] if x["kind"] == CAPTION]                            # each burned caption,
    return out                                                                   # flagged for the orchestrator


def formats(rec):
    """RULING 93 AMENDED (orchestrator 21:10 ET Nov 14): "source-burned captions that the 9:16 crop cuts mid-word make the
    clip 16:9-ONLY (sealed as formats: ['16x9'], the integrator renders and delivers that format alone) unless a crop
    exists that shows them whole; they do not make the clip ineligible." -> ["16x9"] when any burned caption of a
    measured record is "cut" in the 9:16, else None (both formats, as before)."""
    if not (rec or {}).get("measured"):
        return None
    cut = [x for x in rec.get("burned_in") or [] if x.get("kind") == CAPTION and x.get("in_9x16") == "cut"]
    return ["16x9"] if cut else None


def burned_block(x):
    """RULING 93 on one burned-in item -> why it makes the clip NOT eligible, or None (eligible, flagged): a ticker or
    a crawl; a lower third or bug that is not wholly inside the 16:9, that the 9:16 edge would cut through mid-word, or
    that covers the speaker."""
    if x["kind"] == CAPTION:                     # ruling 93 amended: a burned caption never makes a clip ineligible;
        return None                              # cut by the 9:16 it makes it 16:9-only (formats())
    if x["kind"] in RUNNING:
        return f"a {x['kind']} ({x['text'][:80]!r}): not eligible"
    if not x["whole_in_16x9"]:
        return f"a {x['kind']} not wholly inside the 16:9 ({x['text'][:80]!r})"
    if x["in_9x16"] == "cut":
        return f"a {x['kind']} the 9:16 crop would cut through mid-word ({x['text'][:80]!r})"
    if x["covers_speaker"]:
        return f"a {x['kind']} that covers the speaker ({x['text'][:80]!r})"
    return None


def layout_block(rec):
    """RULING 93 (23:58 ET Nov 13): why the clip may not be on screen in ANY role, or None. Not measured, or a record
    without question 4 (an earlier version), is never a pass (law L-m); otherwise burned_block() on every item."""
    if not (rec or {}).get("measured"):
        return "its visual check is not measured (law L-m)"
    if not isinstance(rec.get("burned_in"), list):
        return "ruling 93: the burned-in text question was not asked (an earlier visual record)"
    if rec.get("version") != VERSION:            # 21:10 Nov 14: visual-2 never asked for the source's captions
        return f"its visual record is {rec.get('version')!r}, which never asked for the source's burned captions"
    why = [w for w in (burned_block(x) for x in rec["burned_in"]) if w]
    if formats(rec) and not RENDER_16X9_ONLY:    # ruling 93 amended: 16:9-only, which the render cannot pass yet
        why.append("16:9-only (a burned caption the 9:16 crop cuts mid-word, ruling 93 amended), and the integrator's "
                   "render cannot pass a 16:9-only pin until its format-aware release lands: held")
    return (f"ruling 93 ({len(why)} item(s)): " + "; ".join(why))[:600] if why else None   # (audit 0003 C2)


def crop_only(rec):
    """RULING 123 (2) (orchestrator 14:05 ET Nov 16): the reason a measured record's ONLY refusal is ruling 93's 9:16 crop
    (a lower third or bug wholly inside the 16:9, not over the speaker, that the 9:16 crop would cut through mid-word),
    or None. Such a clip shows whole in 16:9: as a HOOK, when no hook passes for both formats, it may open a package
    sealed formats ['16x9'] (package.build). A ticker or crawl, a part outside the 16:9, a speaker covered, a third
    person (ruling 70) or an unmeasured or older record: None."""
    if not ((rec or {}).get("measured") is True and rec.get("version") == VERSION and
            isinstance(rec.get("burned_in"), list)) or hook_block(rec) is not None or \
            not RENDER_16X9_ONLY:                # the exception makes a 16:9-only pin: only when the render can pass one
        return None
    why = [burned_block(x) for x in rec["burned_in"]]
    cut = [x for x, w in zip(rec["burned_in"], why) if w]
    if not cut or any(x["kind"] in RUNNING or x["kind"] == CAPTION or not x["whole_in_16x9"] or x["in_9x16"] != "cut"
                      or x["covers_speaker"] for x in cut):
        return None
    return "; ".join(w for w in why if w)


def graphics_only(rec):
    """RULING 146 (1) (orchestrator 07:55 ET Nov 18): the kinds of the source's OWN on-screen graphics (ticker, crawl,
    lower third, bug) when they are a measured, current record's ONLY refusal (ruling 93's burned_block), else None.
    They are refused only because OUR 9:16 crop cuts them; a package sealed 16:9 only shows them whole, so there they
    are SOFT. A third person (ruling 70), an unmeasured or older record, or a render that cannot pass a 16:9-only pin:
    None."""
    if not ((rec or {}).get("measured") is True and rec.get("version") == VERSION and
            isinstance(rec.get("burned_in"), list)) or hook_block(rec) is not None or not RENDER_16X9_ONLY:
        return None
    return sorted({x["kind"] for x in rec["burned_in"] if burned_block(x)}) or None


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
                               "burned_in", "burned_in_truncated", "formats", "backend", "replayed", "why") if k in rec}
    if isinstance(rec.get("sheet"), dict):
        out["sheet"] = {k: rec["sheet"][k] for k in ("name", "sha256", "times") if k in rec["sheet"]}
    return out


def cost(r):
    """A reply's cost as RULING 70 reports it: {"usd": the vendor-reported figure where the reply carries one (xAI
    cost_in_usd_ticks, Heimdall usage.cost: Reply.usage["usd_reported"]), "usd_basis": "reported"}; else the price-table
    estimate (Reply.usd, an upper bound) with "usd_basis": "estimate"; a reply served from its recording costs nothing
    ("cached")."""
    if getattr(r, "cached", False):
        return {"usd": 0.0, "usd_basis": "cached"}
    rep = (getattr(r, "usage", None) or {}).get("usd_reported")
    if isinstance(rep, (int, float)) and not isinstance(rep, bool):
        return {"usd": round(float(rep), 6), "usd_basis": "reported"}
    return {"usd": round(float(getattr(r, "usd", 0.0) or 0.0), 6), "usd_basis": "estimate"}


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
            return dict(hit, cached=True, usd=0.0, usd_basis="cached", sheet=dict(hit["sheet"], path=p))
    try:
        video = fetch(m["video_id"], float(m["start"]), float(m["end"]), work_dir)
        path, sha, ts = sheet(video, float(m["start"]), float(m["end"]), work_dir)
        if hit is not None and sha == hit["sheet"]["sha256"]:        # rebuilt, the same bytes: the same verdict
            return dict(hit, cached=True, usd=0.0, usd_basis="cached", sheet=dict(hit["sheet"], path=path))
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
                   **({"formats": formats(dict(v, measured=True))} if formats(dict(v, measured=True)) else {}),
                   "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path},
                   "backend": r.backend, "replayed": bool(getattr(r, "replayed", False)),
                   **cost(r),
                   "usage": getattr(r, "usage", None), "cached": bool(getattr(r, "cached", False))}
            if cache is not None and not rec["replayed"]:
                cache[k] = {x: y for x, y in rec.items() if x not in ("cached", "usd", "usd_basis")}
            return rec
        except Exception as e:                   # noqa: BLE001  fail closed; each try's reason is kept (C2)
            if r is not None and not isinstance(e, (P.ProviderError, P.SpendLimit)) and hasattr(router, "reject"):
                router.reject(r)
            kind = "no back-end answered" if isinstance(e, (P.ProviderError, P.SpendLimit)) else "out of contract"
            why = (f"{why}; then " if why else "") + f"seed {sd}: {kind}: {type(e).__name__}: {str(e)[:200]}"
    return {"version": VERSION, "measured": False, "why": f"no verdict in contract after two tries: {why}",
            "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path}}
