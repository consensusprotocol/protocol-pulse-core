#!/usr/bin/env python3
"""pipeline/spotlight.py: RULINGS 90, 91 and 92 (the orchestrator's 22:40 and 22:52 orders, Nov 13; ruling 90 is LAW
since 22:52): the SPOTLIGHT, a second pin kind. The medley stays the flagship and is always tried first: "a spotlight
is built only when the window's search ends with no medley, or for a moment no medley used".

RULING 90, its words: "ONE moment, one speaker, one channel: 12 to 35 s of clip. No hook/clip split, no bridge, no
join. Then at most ONE closing line in the PBX MAX voice, 12 words or fewer, class D commentary that characterises what
was SAID (the two refused patterns stay refused) ... Then the sign-off and the credits card with that one channel, then
the outro. Total 28 to 50 s. ... it must rate >= 4 on the hook's own job (it opens cold) AND >= 4 as a clip standing
alone (the ALONE scorer + step A, both vendors as routed); the visual check clean; inside 12 h at the render clock;
never a delivered span; at most one spotlight per channel per day. If the strong moment is under 12 s, snap it OUTWARD
to the speaker's whole thought (ruling 32's snap; the added words judged as usual), not padded. EVERY integrity law is
unchanged: L-s, L-v, the pre-check (17 / 72 / 73 / 84), the cut rules, G16-G20, the credits."
RULING 91: "Default for a spotlight: NO PBX line ... A line is written only as a candidate and is kept only if a
separate VALUE verdict (off the writer's family) answers all of: it says something the clip does not already say; it
does not restate, summarise or cheer the clip; a viewer would miss it if it were cut; it is 12 words or fewer; plus
the usual fidelity and context gates. One write, one verdict; anything short of a clear yes means no line."
RULING 92: "A spotlight moment must come from a conversation or original reporting ... NOT from a solo host-to-camera
news recap or reaction segment, on any channel. Measured, not listed by name: the turn markers across the episode (one
speaker throughout = solo), plus the visual check's layout (one face to camera with headline graphics or b-roll =
recap)."
The pin contract, agreed with the integrator at 22:44 ET: package_pin's shape "spotlight" (SPOTLIGHT_GATES,
CLOSING_GATES, spotlight_problems, first_comment_text, the sealed closing / shape / first comment).

- pool(): free, before any verdict. package.usable with ruling 90's 35 s ceiling (the orchestrator's 22:58 note: L-u's
  20 s per source video is a medley rule), one spotlight per channel per ET day (the SPOTLIGHTS record), the snap of a
  short moment (snap()), the render's hook opener rule and its topic rule. The driver sends the pool to the clip scorer
  with the medley's own candidates at the build's start (package.build's scorer_extra), so the ALONE rating is asked
  before the spotlight needs it.
- build(): the medley's own verdicts, each cached or recorded across builds (step A, the second recognition pass and
  CUTTABLE, G17a, the hook rating, the visual sheet, the second step-A family), then the ALONE scorer, ruling 92's
  source test, the exclusion verdict and the render's lock pre-check, best moment first; then ONE write (title,
  caption, the first comment and a candidate closing line), the gates, the closing line's value verdict, and the
  package. Nothing measured is never a pass (law L-m); any failure of the closing line leaves no line (ruling 91).
"""
import base64
import hashlib
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import context_integrity as CI
import eligibility as E
import house_style as HS
import package as P
import package_pin as PP
import vo_fidelity as VF

SPOT_S = (12.0, 35.0)                  # ruling 90: 12 to 35 s of clip
RUNTIME_S = PP.SPOT_RUNTIME_S          # ruling 90: total 28 to 50 s (the render's edl_rules R4 / G5)
SNAP_TO_S = round(max(SPOT_S[0], RUNTIME_S[0] - P.FINAL_TAIL_S), 2)
#   13.7 s: the factory's tail (sign-off, credits card, outro, edges) is 14.3 s, so with no closing line (ruling 91's
#   default) a shorter clip cannot reach 28 s. A moment shorter than this is snapped; it is never padded.
HOOK_MIN = 4                           # ruling 90: >= 4 on the hook's own job (package.hook_own: scroll / alone)
ALONE_MIN = 4.0                        # ruling 90: >= 4 standing alone, by the ALONE scorer (its scale is 1-5)
CLOSING_MAX_WORDS = PP.SPOT_CLOSING_MAX_WORDS   # 12
COMMENT_MAX_LINES = 2                  # ruling 90: "one or two short casual lines"
COMMENT_MAX_WORDS = 30
MARKER_TOL_S = 1.0                     # = ledger_build.MARKER_EDGE_S: a caption marker this close to an edge is not in
LAYOUTS = ("conversation", "first_hand", "recap", "reaction", "other")
LAYOUT_OK = ("conversation", "first_hand")
CONVERSATION_TPM = 1.0                 # ruling 92's caption half (see source_test)
FINALISTS = 3                          # moments taken to exclusion, the pre-check and the write, best first
WRITES = 2                             # the title, caption and comment: one more write when a gate refuses them
SCORER_WAIT_S = 600.0                  # a moment that passes everything but has no ALONE rating yet waits this long for
SCORER_POLL_S = 30.0                   # the integrator's scorer pass (its request went out at the build's start)
HANDLES = "/home/ultron/protocol_pulse/pipeline/channels.json"   # the integrator's registry: x_handle is verified,
HANDLE_RE = re.compile(r"^@[A-Za-z0-9_]{1,15}$")                 # an empty one is none (22:44 ET)
VALUE_KEYS = ("adds", "no_restate", "missed", "short")
CLOSING_SAID = P.TAKEAWAY_SAID.replace("The takeaway may", "The closing line may").replace("the clips SAID",
                                                                                            "the clip SAID")


def et_day(now):
    """The ET calendar day of the render clock (all times ET): the 'day' of one spotlight per channel per day."""
    from zoneinfo import ZoneInfo
    return now.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")


def load_spotlit(path):
    """The spotlights already sealed: [{"channel_id", "channel", "day_et", "story_id", "package_sha256", "at"}]. No
    file: none yet. -> the list, or None when the file cannot be read (then one per channel per day is not measured,
    and no spotlight is built: law L-m)."""
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            rows = json.load(f)["spotlights"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    ok = isinstance(rows, list) and all(isinstance(r, dict) and isinstance(r.get("channel_id"), str) and
                                        r["channel_id"] and isinstance(r.get("day_et"), str) for r in rows)
    return rows if ok else None


def record_spotlit(path, row):
    """Append one sealed spotlight to the record, atomically. Raises ValueError when the record cannot be read."""
    rows = load_spotlit(path)
    if rows is None:
        raise ValueError(f"{path} cannot be read: the spotlight is not recorded")
    with open(path + ".tmp", "w") as f:
        json.dump({"spotlights": rows + [row]}, f, indent=1)
    os.replace(path + ".tmp", path)


def snap(m, sources, ctx, captions_for=None):
    """RULING 90 with ruling 32's snap: a moment shorter than SNAP_TO_S is snapped OUTWARD to the speaker's whole
    thought: whole sentences of the SAME word record, the next ones first (the speaker going on), then the ones before
    it, until it lasts SNAP_TO_S, never past SPOT_S[1] and never across a caption speaker-change marker (ruling 69's
    markers; MARKER_TOL_S from an edge does not count, as ruling 32 reads them). Never padded. Captions with no marker
    show no change; L-v 2 then measures one speaker on the audio, as for any snapped moment. The snapped span is a NEW
    moment (its own id; the miner's eligibility and price-prediction risk judged again on it) and every gate of the
    build judges it as usual. -> (moment, None) or (None, why)."""
    import ledger_build as LB
    import moments as M
    import speakers as SP
    try:
        src = P.src_of(m, sources)
        k0, k1 = m["sentences"]
        n = len(src.sentences)
        units, _ = (captions_for or SP.captions)(m["video_id"])
    except Exception as e:                             # noqa: BLE001  no record to snap in: never a guess
        return None, f"no word record or caption record to snap in ({type(e).__name__}: {str(e)[:120]})"
    marks = [u[0] for u in units or () if u[2]]

    def t(i, key):
        x = src.tokens[i].get(key)
        return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None

    def measure(a, b):
        t0, t1 = t(src.sentences[a][0], "start"), t(src.sentences[b][1], "end")
        if t0 is None or t1 is None:
            return None, "a word time is missing"
        if t1 - t0 > SPOT_S[1]:
            return None, f"it would run {t1 - t0:.2f} s, over {SPOT_S[1]:g} s"
        inside = [x for x in marks if t0 + MARKER_TOL_S < x < t1 - MARKER_TOL_S]
        if inside:
            return None, f"a caption speaker-change marker at {inside[0]:.2f} s"
        return t1 - t0, None

    a, b = k0, k1
    dur, why = measure(a, b)
    if dur is None:
        return None, f"the moment itself: {why}"
    if dur >= SNAP_TO_S:
        return m, None                                 # long enough: no snap, the moment as it is
    blocked = []
    while dur < SNAP_TO_S:
        step = None
        for na, nb, side in ((a, b + 1, "the next sentence"), (a - 1, b, "the sentence before")):
            if na < 0 or nb >= n:
                blocked.append(f"{side}: the word record ends")
                continue
            d, w = measure(na, nb)
            if d is None:
                blocked.append(f"{side}: {w}")
                continue
            step = (na, nb, d)
            break
        if step is None:
            return None, f"{dur:.2f} s and no whole sentence can be added ({'; '.join(blocked[-2:])})"
        a, b, dur = step
    sp = E.Span(src, a, b)
    w_old0, w_old1 = src.sentences[k0][0], src.sentences[k1][1]
    info = {"snapped_words": [w_old0 - sp.w0, sp.w1 - w_old1]}
    record = {"from": m["moment_id"], "sentences": [a, b], "was": [k0, k1], "seconds": [m.get("duration_s"), None],
              "added": {"before": E.spoken(src.tokens[sp.w0:w_old0]), "after": E.spoken(src.tokens[w_old1 + 1:sp.w1 + 1])},
              "rule": f"ruling 90 with ruling 32's snap: whole sentences outward to {SNAP_TO_S:g} s, no speaker marker"}
    rec = M.record(sp, {"scores": m["scores"], "names_person": m.get("names_person", False),
                        "risk": LB.snap_risk(sp.text, info, m.get("risk")), "topics": list(m.get("topics") or []),
                        "reason": m.get("reason") or ""}, ctx, M.judge(sp, ctx),
                   dict(m.get("mined") or {}, spotlight_snap_from=m["moment_id"]))
    rec["rank_score"] = M.rank_score(rec)
    if m.get("source_key"):
        rec["source_key"] = m["source_key"]
    record["seconds"][1] = rec["duration_s"]
    rec["spotlight_snap"] = record
    return rec, None


def pool(moments, sources, ctx, delivered=(), optout=frozenset(), spotlit=(), captions_for=None):
    """Stage 1, FREE (no vendor call) -> (the moments that may be a spotlight, {moment id: why not}): package.usable
    with ruling 90's 35 s ceiling (inside 12 h on the render clock, never a delivered span or the same speech, no hard
    exclusion, no speaker change inside, L-v 3), one per re-posted speech (ruling 53), one spotlight per channel per ET
    day (spotlit; None: not measured, so none), a moment under SNAP_TO_S snapped (snap(), then usable() again on the
    snapped span), the render's STAND_ALONE hook opener rule (it opens cold) and its topic rule."""
    import stand_alone as SA
    ms, why = P.usable(moments, ctx, delivered, optout, seg_max=SPOT_S[1])
    ms, reposted = P.reposted_once(ms, sources)
    why.update({k: f"ruling 53: {v}" for k, v in reposted.items()})
    if spotlit is None:
        why.update({m["moment_id"]: "ruling 90: one spotlight per channel per day is not measured (the spotlights "
                                    "record cannot be read)" for m in ms})
        return [], why
    day = et_day(ctx.now)
    taken = {r["channel_id"] for r in spotlit if r.get("day_et") == day}
    out, seen = [], set()
    for m in ms:
        mid = m["moment_id"]
        if m["channel_id"] in taken:
            why[mid] = f"ruling 90: this channel already has a spotlight on {day} (ET)"
            continue
        v = m
        if float(m["duration_s"]) < SNAP_TO_S:
            v, w = snap(m, sources, ctx, captions_for)
            if v is None:
                why[mid] = f"ruling 90: {m['duration_s']} s is under {SNAP_TO_S:g} s and the snap fails: {w}"
                continue
            ok, w2 = P.usable([v], ctx, delivered, optout, seg_max=SPOT_S[1])
            if not ok:
                why[mid] = f"ruling 90: snapped to {v['moment_id']} ({v['duration_s']} s), which is out: " \
                           f"{w2.get(v['moment_id'])}"
                continue
        if v["moment_id"] in seen:
            why[mid] = f"the same span as {v['moment_id']}, already in the pool"
            continue
        ok, w = SA.opener("hook", v.get("text") or "")
        if not ok:
            why[mid] = f"ruling 90: it cannot open cold (the render's STAND_ALONE hook rule): {w}"
            continue
        top = P.no_topic(v)
        if top:
            why[mid] = top
            continue
        seen.add(v["moment_id"])
        out.append(v)
    return out, why


def episode_turns(video_id, captions_for=None):
    """RULING 92's caption half: the speaker-change markers across the EPISODE (speakers.captions, ruling 69's reader).
    -> {"measured", "turns", "minutes", "turns_per_min", "file", "sha256"}; no marked record: {"measured": False,
    "unmarked": True} (no marker at all is unknown, not solo: pp-ingest's contract)."""
    import speakers as SP
    try:
        units, rec = (captions_for or SP.captions)(video_id)
    except Exception as e:                             # noqa: BLE001
        return {"measured": False, "why": f"{type(e).__name__}: {str(e)[:120]}"}
    if not units:
        return {"measured": False, "unmarked": True,
                "why": "no caption record with speaker-change markers: unmarked or missing (unknown, not solo)"}
    turns = sum(1 for u in units if u[2])
    minutes = (units[-1][0] - units[0][0]) / 60.0
    return {"measured": True, "turns": turns, "minutes": round(minutes, 1),
            "turns_per_min": round(turns / minutes, 2) if minutes > 0 else None,
            "file": (rec or {}).get("file"), "sha256": (rec or {}).get("sha256")}


def source_test(turns, layout):
    """RULING 92 -> (ok, why). A PASS needs a MEASURED layout of a conversation or a first-hand statement
    (LAYOUT_OK). A recap, a reaction, or a layout the judge cannot place ('other') fails on any channel; a layout that
    is not measured is never a pass (law L-m). The caption markers across the episode can only make it stricter: a
    layout read as a conversation from an episode whose captions are marked but carry fewer than CONVERSATION_TPM
    turns a minute is not measured as a conversation (Nov 13: Simply Bitcoin's solo recap L6H7538ogGs 0.48 turns a
    minute; the pool's interviews and panels 1.18-2.53). Unmarked captions are unknown, not solo: the layout decides."""
    if not (layout or {}).get("measured"):
        return False, f"the layout is not measured: {(layout or {}).get('why')}"
    lay = layout["layout"]
    if lay not in LAYOUT_OK:
        return False, f"the layout is '{lay}' ({layout.get('why')}): not a conversation or a first-hand statement"
    tpm = (turns or {}).get("turns_per_min")
    if lay == "conversation" and (turns or {}).get("measured") and (tpm is None or tpm < CONVERSATION_TPM):
        return False, (f"the frames read as a conversation but the episode's captions carry {tpm} speaker turns a "
                       f"minute (under {CONVERSATION_TPM:g})")
    return True, f"layout '{lay}'" + (f"; {turns['turns']} caption turns in {turns['minutes']} min ({tpm} a minute)"
                                      if (turns or {}).get("measured") else "; captions unmarked")


LAYOUT_PROMPT = """You see a contact sheet of {n} frames of ONE clip from a Bitcoin video, left to right and top to
bottom. The clip's words, as spoken: "{text}"
From the frames only, classify the SOURCE's format:
- "conversation": two or more people talking with each other: an interview, a podcast, a panel (in one room, or on a
  split screen or a video call);
- "first_hand": one person making their own statement to an audience: a keynote, a speech, a guest answering on a news
  network;
- "recap": one host speaking to the camera with headline graphics, a news set or b-roll: a news recap;
- "reaction": a host showing or reacting to another video, a post or a chart inside the host's own frame;
- "other": none of these, or you cannot tell.
Return ONLY this JSON object: {{"layout": "conversation" | "first_hand" | "recap" | "reaction" | "other",
"people_on_screen": <the most people visible in one frame, a number>, "why": "<one sentence>"}}"""
LAYOUT_VERSION = hashlib.sha256(LAYOUT_PROMPT.encode()).hexdigest()[:12]
LAYOUT_LOCK = threading.Lock()


def parse_layout(text):
    """The layout verdict in contract, or ValueError."""
    v = json.loads(text.strip())
    if not isinstance(v, dict) or set(v) != {"layout", "people_on_screen", "why"}:
        raise ValueError("keys must be exactly layout, people_on_screen, why")
    if v["layout"] not in LAYOUTS or type(v["people_on_screen"]) is not int or v["people_on_screen"] < 0 or \
            not isinstance(v["why"], str) or not v["why"].strip():
        raise ValueError("layout out of contract")
    return {"layout": v["layout"], "people_on_screen": v["people_on_screen"], "why": v["why"].strip()[:300]}


def _load_json(path):
    try:
        with open(path) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def layout_for(router, m, vrec, cache_path=None, seed=7):
    """RULING 92's visual half: the source's layout, judged on the clip's own contact sheet (the visual check's, ruling
    70: the same bytes it judged) with LAYOUT_PROMPT, by the visual_check role (one call, cached by the moment, the
    sheet's sha256 and the prompt's version). -> {"measured", "layout", "people_on_screen", "why", "backend",
    "replayed"} or {"measured": False, "why"}: never a pass unmeasured."""
    import providers as Pr
    from story_semantics import quote_data
    sheet = (vrec or {}).get("sheet") or {}
    path, sha = sheet.get("path"), sheet.get("sha256")
    if not (vrec or {}).get("measured") or not path or not sha:
        return {"measured": False, "why": "no judged contact sheet (the visual check is not measured)"}
    k = f"{m['moment_id']}:{sha}:{LAYOUT_VERSION}"
    hit = _load_json(cache_path).get(k) if cache_path else None
    if isinstance(hit, dict) and hit.get("measured") is True:
        return dict(hit, cached=True)
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        return {"measured": False, "why": f"the sheet cannot be read ({type(e).__name__})"}
    if hashlib.sha256(raw).hexdigest() != sha:
        return {"measured": False, "why": "the sheet on disk is not the one the visual check judged"}
    prompt = {"text": LAYOUT_PROMPT.format(n=len(sheet.get("times") or []),
                                           text=quote_data(m.get("text") or "", 700).replace('"', "'")),
              "images": [base64.b64encode(raw).decode()]}
    r = None
    try:
        r = router.call("visual_check", prompt, 600, seed)
        v = parse_layout(r.text)
    except Exception as e:                             # noqa: BLE001  no verdict: never a pass (law L-m)
        if r is not None and not isinstance(e, (Pr.ProviderError, Pr.SpendLimit)) and hasattr(router, "reject"):
            router.reject(r)
        return {"measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
    rec = dict(v, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)),
               version=LAYOUT_VERSION, sheet_sha256=sha)
    if cache_path and not rec["replayed"]:
        with LAYOUT_LOCK:
            c = _load_json(cache_path)
            c[k] = rec
            with open(cache_path + ".tmp", "w") as f:
                json.dump(c, f, indent=1)
            os.replace(cache_path + ".tmp", cache_path)
    return rec


def alone_score(m):
    """The ALONE scorer's rating of the moment's CURRENT text (package.verdict_of: the integrator's verdicts of the
    render's own scorer, rulings 56 / 60), or None when it has none yet."""
    v = P.verdict_of(m)
    return float(v["score"]) if v is not None else None


def _published_ts(m):
    """The moment's publish time as a UTC timestamp; an unreadable one sorts as the oldest."""
    from datetime import datetime, timezone
    z = P.utc_z(m.get("published_at"))
    return datetime.strptime(z, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() if z else float("-inf")


def rank_key(m):
    """Best first: the hook's own-job rating, the ALONE rating, the hook's parts, the miner's score, the newest
    source, then the id (a total order)."""
    hr = m.get("hook_rating") or {}
    return (-((P.hook_own(m) or {}).get("rating") or 0), -(alone_score(m) or 0.0),
            -sum(hr.get(k) or 0 for k in P.HOOK_PARTS), -float(m.get("rank_score") or 0.0), -_published_ts(m),
            m["moment_id"])


WRITE_SPOT = """You are PBX MAX, the host of a short Bitcoin video that SPOTLIGHTS one clip of another channel's own
words. The clip plays alone, in full; then a sign-off credits the channel (written by code).

{note}
{clip}

Write:
- "title": ONE title of at most 8 words (and at most 70 characters) that says what the clip is about.
- "caption": ONE caption (at most 220 characters).
- "comment": the first comment under the video, as PBX writes them: one or two short casual lines about THIS clip in
  plain words; not preachy; no emoji, no hashtags, no handles, no links and no credits (code adds the credits).
- "closing": a CANDIDATE closing line the host speaks right after the clip, at most {cmax} words, as your OWN
  commentary. It is kept ONLY if it says something the clip does not already say: it never restates, summarises or
  cheers the clip, and a viewer would miss it if it were cut. When you have nothing to add, give null: the clip then
  goes straight to the sign-off, which is the default. {said}
Every line gives "cites": the clip's id when it relies on the clip (none for your own commentary).
RULES (a line that breaks one is rejected):
- NEVER restate the clip's claim, and never repeat its words: the clip says it, in its own words.
- Your OWN commentary is an opinion or a conclusion, nothing else: no checkable fact, number, price, date, named person
  or company; never what the speaker thinks; no prediction of what will happen; no advice or instruction to the viewer
  (no "you should", "your job", "must"); no accusation; nothing that sounds like a quote.
- Say what the speaker says or thinks ONLY when the clip is marked VERIFIED, by that name, with the clip's own hedge:
  "thinks" for "I think", "feels" for "I feel like", "says" only for a flat statement. Otherwise credit the SHOW only
  ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says" or "<name> discusses".
- No price level; no advice to buy, sell or use leverage; no quotes except the clip's exact words; no "destroys",
  "slams", "exposes", "admits", "confirms", "caught".
- A line that names a show, a person or Bitcoin's price cites the clip.
{style}
{extra}Return ONLY this JSON object: {{"title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}},
"comment": {{"text": "...", "cites": []}}, "closing": {{"text": "...", "cites": []}} or null}}"""

VALUE_PROMPT = """You judge ONE line a host would speak right after a clip in a short video. The clip plays first,
alone and in full; then the host's line; then a sign-off credits the channel.
{note}
CLIP (on {show}): "{clip}"
LINE: "{line}"
Answer each question "yes" or "no". Anything you cannot answer with a clear yes is "no".
- "adds": does the line say something the clip does not already say?
- "no_restate": does the line avoid restating, summarising or cheering the clip?
- "missed": would a viewer miss the line if it were cut?
- "short": is the line 12 words or fewer?
Return ONLY this JSON object: {{"adds": "yes" | "no", "no_restate": "yes" | "no", "missed": "yes" | "no", "short":
"yes" | "no", "why": "<one sentence>"}}"""


def parse_write(text, mid, closing_allowed=True):
    """One write in contract -> {"title", "caption", "comment", "closing"} (closing None or a line), or ValueError."""
    obj = json.loads(text.strip())
    keys = {"title", "caption", "comment", "closing"}
    if not isinstance(obj, dict) or set(obj) != keys:
        raise ValueError(f"keys must be exactly {sorted(keys)}")
    out = {}
    for slot in ("title", "caption", "comment", "closing"):
        ln = obj[slot]
        if slot == "closing" and (ln is None or not closing_allowed):
            out[slot] = None
            continue
        if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
                not ln["text"].strip() or not isinstance(ln["cites"], list) or \
                any(not isinstance(c, str) or c != mid for c in ln["cites"]):
            raise ValueError(f"{slot}: needs text and cites from the clip's id")
        out[slot] = {"text": ln["text"].strip(), "cites": list(dict.fromkeys(ln["cites"]))}
    if len(out["title"]["text"]) > 70 or len(out["caption"]["text"]) > 220:
        raise ValueError("title <= 70 characters, caption <= 220")
    return out


def parse_value(text):
    """Ruling 91's value verdict in contract -> {"adds", "no_restate", "missed", "short", "why"}, or ValueError."""
    v = json.loads(text.strip())
    if not isinstance(v, dict) or set(v) != set(VALUE_KEYS) | {"why"}:
        raise ValueError(f"keys must be exactly {sorted(set(VALUE_KEYS) | {'why'})}")
    if any(v[k] not in ("yes", "no") for k in VALUE_KEYS) or not isinstance(v["why"], str):
        raise ValueError("each answer is 'yes' or 'no', with a reason")
    return {**{k: v[k] for k in VALUE_KEYS}, "why": v["why"].strip()[:300]}


def value_verdict(router, m, line, show, writers_v, writers_f, seed=7):
    """RULING 91: ONE value verdict on the candidate closing line, off the writer's vendor and family (the
    coherence_verdict role). ok only when all four answers are "yes" AND the line counts at most CLOSING_MAX_WORDS
    words in code; an unavailable or out-of-contract answer is no verdict, so no line (never re-asked: "one write, one
    verdict")."""
    import providers as Pr
    from select_by_id import UNTRUSTED
    from story_semantics import quote_data
    prompt = VALUE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"), show=quote_data(show, 80),
                                 clip=quote_data(m["text"], 1200).replace('"', "'"),
                                 line=quote_data(line, 200).replace('"', "'"))
    r = None
    try:
        r = router.call("coherence_verdict", prompt, 400, seed, avoid_vendor=writers_v, avoid_family=writers_f)
        v = parse_value(r.text)
    except Exception as e:                             # noqa: BLE001  no verdict: no line (ruling 91)
        if r is not None and not isinstance(e, (Pr.ProviderError, Pr.SpendLimit)) and hasattr(router, "reject"):
            router.reject(r)
        return {"measured": False, "ok": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
    words = len(line.split())
    return dict(v, measured=True, ok=all(v[k] == "yes" for k in VALUE_KEYS) and words <= CLOSING_MAX_WORDS,
                words=words, backend=r.backend, replayed=bool(getattr(r, "replayed", False)))


def style_lint(lines):
    """PBX's house style on a spotlight's lines: the title and caption rules (house_style.lint); the closing line by
    the takeaway's rules and at most CLOSING_MAX_WORDS words; the comment by the rules every surface keeps (no hashtag,
    dash, emoji, hedge or AI phrasing), at most COMMENT_MAX_LINES lines and COMMENT_MAX_WORDS words, and no handle, link
    or credit (code adds the credits)."""
    out = []
    for ln in lines:
        slot, text = ln["slot"], ln.get("text") or ""
        if slot in ("title", "caption"):
            out += HS.lint(slot, text)
        elif slot == "closing":
            out += [dict(v, slot="closing") for v in HS.lint("takeaway", text)]
            if len(text.split()) > CLOSING_MAX_WORDS:
                out.append({"slot": "closing", "rule": "STYLE",
                            "detail": f"closing-words: {len(text.split())} words (at most {CLOSING_MAX_WORDS})"})
        elif slot == "comment":
            out += [dict(v, slot="comment") for v in HS.lint("bridge", text)]   # the every-surface rules only
            n_lines = len([x for x in text.split("\n") if x.strip()])
            if n_lines > COMMENT_MAX_LINES:
                out.append({"slot": "comment", "rule": "STYLE",
                            "detail": f"comment-lines: {n_lines} lines (at most {COMMENT_MAX_LINES})"})
            if HS.words(text) > COMMENT_MAX_WORDS:
                out.append({"slot": "comment", "rule": "STYLE",
                            "detail": f"comment-words: {HS.words(text)} words (at most {COMMENT_MAX_WORDS})"})
            if re.search(r"@|https?://|www\.|\bcredits?\b", text, re.I):
                out.append({"slot": "comment", "rule": "STYLE",
                            "detail": "comment-credits: no handle, link or credit (code adds them)"})
    return out


def credits(channel, speaker, table_path=HANDLES):
    """RULING 90: the first comment's credits: the channel's X handle and the attested speaker's, ONLY from the
    verified table (the integrator's registry: x_handle, an empty one is none). The speaker has a handle only when the
    attested name is itself a registry channel (no speaker-level table exists: the integrator, 22:44 ET); a name
    without a verified handle stays UNTAGGED, and the record says so. -> {"tags", "channel", "speaker"}."""
    try:
        with open(table_path) as f:
            reg = json.load(f)
        rows = reg if isinstance(reg, list) else []
    except (OSError, ValueError):
        rows = []
    def handle_of(name):
        for r in rows:
            names = [r.get("display_name")] + list(r.get("aliases") or [])
            if isinstance(r, dict) and name in [x for x in names if isinstance(x, str)]:
                h = r.get("x_handle")
                return (h, None) if isinstance(h, str) and HANDLE_RE.match(h) else \
                    (None, "the registry has no verified X handle for it")
        return None, "not in the verified table" if rows else "the verified table cannot be read"
    h, why = handle_of(channel)
    out = {"channel": {"name": channel, "handle": h, "untagged_why": why}, "speaker": None}
    tags = [h or channel]
    sp = speaker if isinstance(speaker, dict) and speaker.get("measured") is True and \
        isinstance(speaker.get("name"), str) and speaker["name"] not in ("", "unknown") else None
    if sp is not None and sp["name"] != channel:
        hs, why_s = handle_of(sp["name"])
        out["speaker"] = {"name": sp["name"], "handle": hs, "untagged_why": why_s}
        if (hs or sp["name"]) not in tags:
            tags.append(hs or sp["name"])
    elif sp is None:
        out["speaker"] = {"name": None, "handle": None,
                          "untagged_why": "no attested speaker (the speaker record names none): the channel only"}
    out["tags"] = tags
    return out


def assemble(m, ctx, fields, closing):
    """The spotlight package (ruling 90): ONE segment (label "hook"), no intro and no bridge, the closing line or none,
    the sign-off with its one channel (package.signoff), the title, caption and comment as gated lines, the medley's
    about-Bitcoin screen (ruling 34: the render judges with it), and the factory's runtime estimate with the closing
    line counted."""
    lines = ([dict(closing, slot="closing")] if closing else []) + \
        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption"),
         dict(fields["comment"], slot="comment")]
    vo = {"intro": None, "bridges": [], "bridges_after_clip": [], "closing": closing["text"] if closing else None}
    pk = P._package([m], ctx, {"title": fields["title"], "caption": fields["caption"], "type": "moments",
                               "angle": "", "style": "spotlight"}, "spotlight (ruling 90)", vo, lines)
    pk["shape"] = "spotlight"
    pk["btc_screen"] = {"pattern": E.BTC_SCREEN.pattern, "source": E.BTC_SCREEN_SOURCE}
    pk["runtime_s_estimate"] = P.runtime([m], [vo["closing"]])
    pk["runtime_note"] = (f"the moment {m['duration_s']:.2f} s (word timing)" +
                          (f" + the closing line ({len(vo['closing'].split())} words at {P.R4_WPS} w/s + "
                           f"{P.R4_PREROLL_S} s pre-roll)" if vo["closing"] else ", no closing line") +
                          f" + tail {P.FINAL_TAIL_S} s (sign-off, credits card, outro, edges): the factory's estimate")
    return pk


def cheap(pk, a_by, levels, now):
    """The free gates of a spotlight's lines -> (violations, det, dup, rt_ok, style): VO fidelity's deterministic rules,
    DUPLICATE, the 28-50 s runtime, the house style and the recency facts the pin carries."""
    segs_v = P.fidelity_segments(pk, a_by)
    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
    det = VF.check_deterministic(segs_v, lines, man, levels)
    dup = P.duplicates(pk)
    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
    style = style_lint(pk["lines"])
    v = det["violations"] + dup + style + \
        ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail": f"{pk['runtime_s_estimate']} s outside "
                                                                     f"{RUNTIME_S[0]:g}-{RUNTIME_S[1]:g} s"}]) + \
        [{"slot": "-", "rule": "RECENCY", "detail": w} for w in PP.recency_problems(pk["segments"])]
    return v, det, dup, rt_ok, style


def _row(ok, by, replayed=False, measured=True, **extra):
    return dict({"status": "NOT RUN" if not measured else ("PASS" if ok else "FAIL"), "by": by,
                 "replayed": replayed if isinstance(replayed, bool) else None, "n": 1}, **extra)


def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre, src_rec, facts, closing=None):
    """The sealed gate inventory of a spotlight (package_pin.SPOTLIGHT_GATES, + CLOSING_GATES with a closing line):
    package.inventory's rows that apply to one clip (its "r4" and "coherence" rows judge several clips and a medley's
    VO: they are left out), then ruling 90-92's own rows. facts: {"never_delivered", "one_per_channel_day",
    "window"} as the build measured them. closing: {"value", "fidelity", "context"} when a closing line ships."""
    mid = m["moment_id"]
    rows = P.inventory(fid, dup, rt_ok, (True, "n/a"), cx, {"hook": a_off}, {mid: exc}, {mid: truth}, False,
                       {"measured": False}, style=style, hook=m.get("hook_onset"), stand=P.stand_alone_check([m]),
                       visual=[m.get("visual")])
    rows.pop("r4", None)
    rows.pop("coherence", None)
    v = m.get("visual") or {}
    rows["visual"] = _row(v.get("measured") is True and not v.get("flags"), v.get("backend"), v.get("replayed"),
                          measured=v.get("measured") is True, flags=list(v.get("flags") or []),
                          by_rule="ruling 90: the visual check clean (no flag; ruling 70's sheet)")
    own, hr = P.hook_own(m), m.get("hook_rating") or {}
    rows["hook_own"] = _row(own is not None and own["rating"] >= HOOK_MIN, hr.get("backend"),
                            bool(hr.get("replayed", False)), measured=own is not None,
                            rating=(own or {}).get("rating"), scroll=hr.get("scroll"), alone=hr.get("alone"),
                            why=hr.get("why"), min=HOOK_MIN, rule="ruling 90: >= 4 on the hook's own job (ruling 61)")
    sv = P.verdict_of(m)
    rows["stands_alone"] = _row(sv is not None and float(sv["score"]) >= ALONE_MIN,
                                f"the ALONE scorer ({(sv or {}).get('model')}, the render's stand_alone scorer as the "
                                f"integrator's pin-stage service gave it, rulings 56 / 60)", False,
                                measured=sv is not None, score=(sv or {}).get("score"), reason=(sv or {}).get("reason"),
                                text_sha256=(sv or {}).get("text_sha256"), min=ALONE_MIN)
    fams = [a.get("backend") for a in a_two or []]
    rows["step_a_two_families"] = _row(len(a_two or []) == 2 and not any(CI.a_failures(a) for a in a_two),
                                       fams, None if any(not isinstance(a.get("replayed"), bool) for a in a_two or [])
                                       else any(a.get("replayed") for a in a_two or []),
                                       measured=len(a_two or []) == 2,
                                       rule="ruling 90: step A from both families as routed (package.second_screen)")
    rows["spotlight_source"] = _row(src_rec["ok"], (src_rec.get("layout") or {}).get("backend"),
                                    bool((src_rec.get("layout") or {}).get("replayed", False)),
                                    measured=(src_rec.get("layout") or {}).get("measured") is True,
                                    why=src_rec.get("why"), turns=src_rec.get("turns"), layout=src_rec.get("layout"),
                                    rule="ruling 92: conversation, not reaction (caption turns + the layout)")
    rows["window_12h"] = _row(not PP.window_problems(pk["segments"], facts["now"]),
                              "code (package_pin.window_problems, ruling 76: <= 12 h on the render clock)",
                              why=PP.window_problems(pk["segments"], facts["now"]))
    rows["never_delivered"] = _row(facts["never_delivered"] is True,
                                   "code (package.usable: no delivered span overlapped, not the same speech, ruling 76 b)",
                                   measured=isinstance(facts["never_delivered"], bool))
    rows["one_per_channel_day"] = _row(facts["one_per_channel_day"] is True,
                                       f"code (the spotlights record: no spotlight from this channel on {facts['day']} ET)",
                                       measured=isinstance(facts["one_per_channel_day"], bool))
    covered = [s for s in (pre or {}).get("segments") or [] if isinstance(s, dict)]
    rows["precheck"] = _row((pre or {}).get("ok") is True and len(covered) == 1 and
                            covered[0].get("verdict") in ("pass", "adopt") and
                            covered[0].get("video_id") == m["video_id"],             # one verdict on THIS clip
                            "lock_precheck (the render's own lock: rulings 17 / 68 / 72 / 73 / 84)", False,
                            measured=pre is not None and not (pre or {}).get("error") and bool(covered),
                            verdicts=[s.get("verdict") for s in (pre or {}).get("segments") or []
                                      if isinstance(s, dict)])
    if closing is not None:
        val, cf, cc = closing["value"], closing["fidelity"], closing["context"]
        rows["closing_value"] = _row(val.get("ok") is True, val.get("backend"), bool(val.get("replayed", False)),
                                     measured=val.get("measured") is True,
                                     answers={k: val.get(k) for k in VALUE_KEYS}, why=val.get("why"),
                                     words=val.get("words"), rule="ruling 91: all four a clear yes")
        rows["closing_fidelity"] = _row(cf.get("ok") is True, cf.get("backend"), bool(cf.get("replayed", False)),
                                        measured=bool(cf.get("measured")),
                                        violations=[f"{x['slot']}: {x['rule']}" for x in cf.get("violations") or []])
        rows["closing_context"] = _row(cc.get("ok") is True, cc.get("backends"), cc.get("replayed"),
                                       measured=bool(cc.get("measured")),
                                       violations=[x.get("rule") for x in cc.get("violations") or []])
    return rows


STAGES = ("step A", "the second recognition pass and CUTTABLE", "opens cold (G17a, the hook rules)",
          "the hook's own job >= 4", "the visual check clean", "step A from the second family", "the ALONE scorer >= 4",
          "ruling 92's source test", "exclusion, the pre-check and the package")


def near(rec, k=3):
    """The k moments that got furthest (ruling 92's 'three nearest and their ratings'): by the last stage passed, then
    the hook's own-job rating, then the ALONE rating."""
    rows = sorted(rec.items(), key=lambda kv: (-kv[1].get("stage", 0), -(kv[1].get("hook_own") or 0),
                                               -(kv[1].get("alone") or 0), kv[0]))
    return [dict(v, moment_id=mid, passed=list(STAGES[:v.get("stage", 0)])) for mid, v in rows[:k]]


def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, work_dir=None, store=None,
          step_a_cache=None, hook_cache=None, scorer_verdicts_path=None, visual_cache=None, layout_cache=None,
          lock_check=None, spotlit=(), handles_path=HANDLES, wait_s=SCORER_WAIT_S, sleep=time.sleep,
          captions_for=None, finalists=FINALISTS, attribute=None):
    """RULINGS 90-92: the best spotlight in the pool, or none -> {"package", "pool", "moments" (each moment's furthest
    stage and why it stopped), "finalists", "near", "why_none", ...}. The stages run cheapest first, each on what the
    one before passed; every verdict is the medley's own and cached or recorded across builds: step A
    (package.prescreen), L-v 2 and CUTTABLE (truth_for), G17a (hook_onset_for), the render's hook rules and the hook's
    own-job rating (package._can_open, hook_ratings: >= HOOK_MIN), the visual check clean (visual_pin: measured, no
    flag, not blocked as a hook), step A from the second family (package.second_screen), the ALONE scorer >= ALONE_MIN
    (a moment with no rating yet waits up to wait_s for the integrator's pass, polling the verdicts file), ruling 92's
    source test; then, best first (rank_key), up to `finalists` moments: the exclusion verdict, the render's lock
    pre-check (lock_check; no verdict stops the search, as in a medley build) and package_for(). lock_check None: no
    pin (fail closed). spotlit: load_spotlit()'s list (None: not measured, no spotlight). attribute: the speaker
    attribution (default speakers.attribute_package)."""
    import lock_precheck as LP
    import visual_pin as VP
    t0 = time.time()
    out = {"shape": "spotlight", "package": None, "moments": {}, "finalists": [], "near": [], "why_none": None}
    if not work_dir:
        out["why_none"] = "no work_dir: L-v 2's second pass cannot run (fail closed)"
        return out
    ms, why = pool(moments, sources, ctx, delivered, optout, spotlit, captions_for)
    out["pool"] = {"may": len(ms), "out": why,
                   "snapped": {m["moment_id"]: m["spotlight_snap"] for m in ms if m.get("spotlight_snap")}}
    log(f"  SPOTLIGHT (rulings 90-92): {len(ms)} moment(s) may be one ({len(out['pool']['snapped'])} snapped outward "
        f"to {SNAP_TO_S:g} s), {len(why)} out before any verdict")
    if not ms:
        out["why_none"] = "no moment in the 12 h pool may be a spotlight before any verdict (stage 1)"
        return out
    rec = out["moments"]
    for m in ms:
        rec[m["moment_id"]] = {"channel": P._name(m, ctx), "video_id": m["video_id"], "seconds": m["duration_s"],
                               "text": (m.get("text") or "")[:200], "stage": 0}

    def stop(mid, why_):
        rec[mid]["out"] = why_

    def passed(mids, k):
        for mid in mids:
            rec[mid]["stage"] = max(rec[mid]["stage"], k)
    idx, srec = P.scorer_verdicts(scorer_verdicts_path, P.render_scorer_sha()) if scorer_verdicts_path else \
        ({}, {"read": False, "why": "no verdicts file given"})
    out["scorer"] = srec
    ms = [P.with_verdict(m, idx) for m in ms]
    wv, wf = P._writers(router)
    a_by, fails, _, _ = P.prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log, cache=step_a_cache)
    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
    for m in ms:
        if m["moment_id"] not in cleared:
            stop(m["moment_id"], "step A: " + ("; ".join(fails.get(m["moment_id"]) or []) or "no verdict (law L-m)"))
    passed(cleared, 1)
    tru, hk = {}, {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {mid: ex.submit(P.truth_for, router, m, work_dir, tru) for mid, m in cleared.items()}
        got = {mid: f.result() for mid, f in futs.items()}
    tru.update(got)
    cut = {}
    for mid, m in cleared.items():
        t = tru.get(mid) or {}
        if t.get("ok") and (t.get("edges") or {}).get("cuttable") is True:
            cut[mid] = m
        else:
            stop(mid, "L-v 2 / CUTTABLE: " + ("NOT MEASURED: " + str(t["error"]) if t.get("error") else
                                              "the second pass disagrees" if not t.get("ok") else
                                              "not cuttable at an edge"))
    passed(cut, 2)
    openers = {}
    for mid, m in cut.items():
        m["hook_onset"] = P.hook_onset_for(m, sources, work_dir, hk)
        m.pop("hook_rating", None)                       # a rating is this build's own (its cache's)
        m.pop("visual_hook_block", None)
        if P._can_open(m):
            openers[mid] = m
        else:
            stop(mid, f"it cannot open cold: hook eligibility, G17a ({(m['hook_onset'] or {}).get('why')}) or the "
                      f"render's hook rule")
    passed(openers, 3)
    rated, herr = P.hook_ratings(router, list(openers.values()), ctx, wv, wf, cache=hook_cache) if openers else \
        ({}, None)
    strong = {}
    for mid, m in openers.items():
        m["hook_rating"] = rated.get(mid) or {"rating": None, "why": f"not rated: {herr}"}
        own = P.hook_own(m)
        rec[mid]["hook_own"] = (own or {}).get("rating")
        if own is not None and own["rating"] >= HOOK_MIN:
            strong[mid] = m
        else:
            stop(mid, f"the hook's own job rates {(own or {}).get('rating')} (needs {HOOK_MIN}): "
                      f"{m['hook_rating'].get('why')}")
    passed(strong, 4)
    vcache = VP.load_cache(visual_cache) if visual_cache else {}
    if strong:
        with ThreadPoolExecutor(max_workers=4) as ex:
            vis = list(ex.map(lambda m_: VP.visual_for(router, m_, work_dir, vcache), list(strong.values())))
        for m, v in zip(list(strong.values()), vis):
            m["visual"] = v
        if visual_cache:
            VP.save_cache(visual_cache, vcache)
    clean = {}
    for mid, m in strong.items():
        v = m.get("visual") or {}
        if v.get("measured") is True and not v.get("flags") and not VP.hook_block(v):
            clean[mid] = m
        else:
            stop(mid, "the visual check: " + (f"not measured ({v.get('why')})" if v.get("measured") is not True else
                                              f"not clean ({[f.get('kind') for f in v.get('flags') or []]})"))
    passed(clean, 5)
    two, off_fail = P.second_screen(router, clean, a_by, sources, ctx, log=log, cache=step_a_cache) if clean else \
        ({}, {})
    both = {}
    for mid, m in clean.items():
        if mid in two:
            both[mid] = m
        else:
            stop(mid, "step A from the second family: " + "; ".join(off_fail.get(mid) or ["no verdict (law L-m)"]))
    passed(both, 6)
    waited = 0.0
    if both and scorer_verdicts_path and wait_s > 0 and \
            not any((alone_score(m) or 0.0) >= ALONE_MIN for m in both.values()) and \
            any(alone_score(m) is None for m in both.values()):
        log(f"  SPOTLIGHT: {sum(alone_score(m) is None for m in both.values())} moment(s) wait for the ALONE scorer "
            f"(the integrator's pass; up to {wait_s:.0f} s)")
        t_w = time.time()
        for _ in range(max(1, int(wait_s // SCORER_POLL_S))):      # a bounded number of polls
            sleep(SCORER_POLL_S)
            idx, srec = P.scorer_verdicts(scorer_verdicts_path, P.render_scorer_sha())
            both = {mid: P.with_verdict(m, idx) for mid, m in both.items()}
            if all(alone_score(m) is not None for m in both.values()):
                break
        waited = time.time() - t_w
        out["scorer"] = srec
    out["scorer_waited_s"] = round(waited, 1)
    fine = {}
    for mid, m in both.items():
        sc = alone_score(m)
        rec[mid]["alone"] = sc
        if sc is not None and sc >= ALONE_MIN:
            fine[mid] = m
        else:
            stop(mid, f"the ALONE scorer: {sc if sc is not None else 'no rating yet'} (needs {ALONE_MIN:g})" +
                 (f": {(P.verdict_of(m) or {}).get('reason')}" if sc is not None else
                  " (asked with the build's scorer candidates)"))
    passed(fine, 7)
    ok_src = []
    for mid, m in fine.items():
        turns = episode_turns(m["video_id"], captions_for)
        lay = layout_for(router, m, m.get("visual"), layout_cache)
        ok, w = source_test(turns, lay)
        m["spotlight_source"] = {"ok": ok, "why": w, "turns": turns, "layout": lay}
        rec[mid]["source"] = w
        if ok:
            ok_src.append(m)
        else:
            stop(mid, f"ruling 92: {w}")
    passed([m["moment_id"] for m in ok_src], 8)
    ranked = sorted(ok_src, key=rank_key)
    out["finalists"] = [m["moment_id"] for m in ranked]
    log(f"  SPOTLIGHT: {len(cleared)} cleared step A, {len(cut)} cuttable, {len(openers)} open cold, {len(strong)} "
        f"rate >= {HOOK_MIN} as an opener, {len(clean)} clean, {len(both)} two families, {len(fine)} ALONE >= "
        f"{ALONE_MIN:g}, {len(ranked)} from a conversation ({time.time() - t0:.0f} s)")
    exc_cache = {}
    for m in ranked[:finalists]:
        mid = m["moment_id"]
        exc = P.exclusion_for(router, m, sources, exc_cache)
        if exc.get("verdict") != "keep":
            stop(mid, f"the exclusion verdict: {exc.get('verdict')} ({exc.get('why')})")
            continue
        if lock_check is None:
            stop(mid, "no lock pre-check was given: never a pin (fail closed)")
            continue
        try:
            pre = lock_check([m])
        except Exception as e:                           # noqa: BLE001  no verdict, never a pass
            pre = LP.failed(e)
        if not pre.get("ok"):
            stop(mid, f"rulings 68 / 72: the render's lock: {pre.get('error') or 'the clip holds'}"[:400])
            if pre.get("error") or not pre.get("segments"):
                out["lock_stop"] = rec[mid]["out"]       # no verdict: the search stops (as a medley build)
                break
            continue
        day = et_day(ctx.now)                            # the one day pool() measured (audit 2322 C2, grok)
        facts = {"now": ctx.now, "day": day,                             # measured again right before the package:
                 "never_delivered": bool(P.usable([m], ctx, delivered, optout, seg_max=SPOT_S[1])[0]),   # no
                 "one_per_channel_day": spotlit is not None and m["channel_id"] not in    # delivered span or speech
                 {r["channel_id"] for r in spotlit or () if r.get("day_et") == day}}
        pk, why_p = package_for(router, m, ctx, sources, two[mid], tru[mid], exc, pre, facts, log=log,
                                handles_path=handles_path, attribute=attribute)
        if pk is not None:
            pk["seconds"] = round(time.time() - t0, 1)
            out["package"] = pk
            rec[mid]["out"] = "PACKAGE"
            break
        stop(mid, why_p)
    if out["package"] is None:
        out["near"] = near(rec)
        out["why_none"] = out.get("lock_stop") or ("no moment passes rulings 90-92 now" if not ranked else
                                                   f"no finalist gave a package: " +
                                                   "; ".join(f"{mid}: {rec[mid].get('out')}"
                                                             for mid in out["finalists"][:finalists]))[:600]
    return out


def package_for(router, m, ctx, sources, a_two, truth, exc, pre, facts, log=print, handles_path=HANDLES,
                attribute=None):
    """The writes, the gates and the package for ONE moment -> (package, None) or (None, why).
    - ONE write (angle_write): title, caption, comment and a candidate closing line. A title, caption or comment that
      fails a free gate gets ONE more write of those lines (P._redo); the closing line is never written again
      (ruling 91: one write, one verdict).
    - Every verdict comes off every writer's vendor and family (law L-s); step A's verdict off them must exist (L-x).
    - The lines without the closing: VO fidelity's verdict (vo_fidelity_verdict) and, when no closing ships, context
      integrity (context_b / context_c).
    - The closing line ships only when ALL hold: it passes the free gates with the package (house style, <= 12 words,
      DUPLICATE, the runtime still 28-50 s), ruling 91's value verdict is a clear yes on all four, its own fidelity
      verdict passes, and context integrity passes with it spoken after the clip. Otherwise no line (the default).
    - Then the speaker record (sealed), the credits and the first comment (code), the lock's adopted text (LP.apply),
      and the inventory, every required row exactly PASS (package_pin.gate_problems)."""
    import lock_precheck as LP
    import providers as Pr
    import speakers as SP
    from select_by_id import UNTRUSTED
    mid = m["moment_id"]
    show = P._name(m, ctx)
    levels = P.current_levels(sources.values(), ctx)
    both_verify = dict(a_two[0], speaker_verified=all((a or {}).get("speaker_verified") for a in a_two))
    clip = P._lineup_block([m], ctx, {mid: both_verify}).replace("HOOK id=", "CLIP id=", 1)   # a name only when
    #   BOTH step-A verdicts verify the speaker: the gates read the one off the writer, unknown until it answers
    replies, notes, fields, closing0, extra = [], [], None, None, ""
    for w in range(WRITES):
        r = None
        prompt = WRITE_SPOT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"), clip=clip,
                                   cmax=CLOSING_MAX_WORDS, said=CLOSING_SAID, style=HS.PROMPT_RULES,
                                   extra=(extra + "\n") if extra else "")
        try:
            r = router.call("angle_write", prompt, 1500, 7 + w, deadline_s=P.WRITER_DEADLINE_S)
            got = parse_write(r.text, mid, closing_allowed=(w == 0))
        except (Pr.ProviderError, Pr.SpendLimit) as e:
            return None, f"no writer answered ({type(e).__name__}: {str(e)[:200]})"
        except (ValueError, TypeError, KeyError) as e:
            if r is not None:
                router.reject(r)
            notes.append({"write": w + 1, "error": f"{type(e).__name__}: {str(e)[:200]}"})
            extra = f"Your previous reply was REJECTED as out of contract ({str(e)[:200]}). Return the JSON exactly."
            continue
        replies.append(r)
        if w == 0:
            closing0 = got["closing"]
        fields = {k: got[k] for k in ("title", "caption", "comment")}
        wv_, wf_ = {x.vendor for x in replies}, {x.family for x in replies}
        a_off = next((a for a in a_two for b in [router.backends.get(a.get("backend"))]
                      if b is not None and b.vendor not in wv_ and b.family not in wf_), None)
        if a_off is None:
            return None, (f"no step-A verdict off the writers {sorted(wv_)} / {sorted(wf_)} (L-x): "
                          f"{[a.get('backend') for a in a_two]}")
        pk0 = assemble(m, ctx, fields, None)
        v0 = cheap(pk0, {mid: a_off}, levels, ctx.now)[0]
        notes.append({"write": w + 1, "backend": r.backend, "fields": fields, "closing": closing0 if w == 0 else None,
                      "cheap": v0})
        if not v0:
            break
        fields, extra = None, P._redo(v0)
    if fields is None:
        return None, "the title, caption or comment failed the free gates in both writes: " + \
            "; ".join(f"{v['slot']}: {v['rule']}" for v in (notes[-1].get("cheap") or []))[:400] if notes else \
            "no write in contract"
    writers_v, writers_f = {x.vendor for x in replies}, {x.family for x in replies}
    a_lab = {"hook": a_off}
    segs_v = P.fidelity_segments(pk0, {mid: a_off})
    man = {"channels": [show], "date": ctx.now.strftime("%Y-%m-%d")}
    line = lambda pk_, slots: [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk_["lines"]
                               if x["slot"] in slots]
    spoken_after = lambda pk_: dict(pk_, vo=dict(pk_["vo"], intro=pk_["vo"]["closing"], bridges=[],
                                                 bridges_after_clip=[]))   # CI reads the line after the clip there
    closing_rec, cl_why, pk1 = None, "no candidate (the writer gave none)", None
    with ThreadPoolExecutor(max_workers=6) as ex:
        f_fid = ex.submit(VF.check, router, segs_v, line(pk0, ("title", "caption", "comment")), writers_v, 7, man,
                          levels, writers_f)
        if closing0 is not None:
            pk1 = assemble(m, ctx, fields, closing0)
            v1 = cheap(pk1, {mid: a_off}, levels, ctx.now)[0]
            if v1:
                cl_why, pk1 = "the free gates: " + "; ".join(f"{v['slot']}: {v['rule']}: {v['detail']}"
                                                             for v in v1)[:300], None
            else:
                f_val = ex.submit(value_verdict, router, m, closing0["text"], show, writers_v, writers_f)
                f_cf = ex.submit(VF.check, router, segs_v, line(pk1, ("closing",)), writers_v, 7, man, levels,
                                 writers_f)
                f_cc = ex.submit(CI.check_contexts, router, spoken_after(pk1),
                                 CI.contexts_from_sources(pk1, sources, ctx.now), writers_v, 7, a_lab, writers_f, True)
                val, cf, cc = f_val.result(), f_cf.result(), f_cc.result()
                closing_rec = {"value": val, "fidelity": cf, "context": cc}
                if not (val.get("ok") and cf.get("ok") and cf.get("measured") and cc.get("ok") and cc.get("measured")):
                    cl_why = ("ruling 91's value verdict: " + str(val.get("why")) if not val.get("ok") else
                              "its fidelity verdict: " + "; ".join(f"{x['rule']}" for x in cf.get("violations") or [])
                              if not (cf.get("ok") and cf.get("measured")) else
                              "context integrity with it: " + "; ".join(str(x.get("rule"))
                                                                         for x in cc.get("violations") or []))[:300]
                    pk1 = None
        fid = f_fid.result()
    if not (fid.get("ok") and fid.get("measured")):
        return None, "VO fidelity's verdict on the title, caption or comment: " + \
            "; ".join(f"{x['slot']}: {x['rule']}" for x in fid.get("violations") or [])[:300]
    if pk1 is not None:
        pk, cx = pk1, closing_rec["context"]
    else:
        pk = pk0
        cx = CI.check_contexts(router, pk0, CI.contexts_from_sources(pk0, sources, ctx.now), writers_v, 7, a_lab,
                               writers_f, True)
        closing_rec = None
        if not (cx.get("ok") and cx.get("measured")):
            return None, "context integrity: " + "; ".join(str(x.get("rule")) for x in cx.get("violations") or [])[:300]
    v_all, det, dup, rt_ok, style = cheap(pk, {mid: a_off}, levels, ctx.now)
    (attribute or SP.attribute_package)(router, pk, sources, log=log)      # the speaker record, sealed (item 3)
    cr = credits(show, pk["segments"][0].get("speaker"), handles_path)
    pk["comment_credits"] = cr
    pk["first_comment"] = PP.first_comment_text(fields["comment"]["text"], cr["tags"])
    src_rec = m.get("spotlight_source") or {"ok": False, "why": "not measured"}
    pk["spotlight"] = {"moment_id": mid, "snap": m.get("spotlight_snap"), "hook_own": P.hook_own(m),
                       "alone": alone_score(m), "source": {k: src_rec.get(k) for k in ("ok", "why")},
                       "closing": {"candidate": (closing0 or {}).get("text"), "kept": pk1 is not None,
                                   "why_not": None if pk1 is not None else cl_why},
                       "writes": [{k: x.get(k) for k in ("write", "backend", "error")} for x in notes]}
    pk["models"] = {"writer": [x.backend for x in replies], "fidelity_verdict": fid.get("backend"),
                    "context": cx.get("backends"), "value": ((closing_rec or {}).get("value") or {}).get("backend"),
                    "layout": (src_rec.get("layout") or {}).get("backend")}
    pk["checks"] = {"fidelity": fid, "context": cx, "closing": closing_rec}
    pk["gates"] = inventory(pk, m, dict(fid, deterministic=det), dup, rt_ok, style, cx, a_off, a_two, exc, truth,
                            pre, src_rec, facts, closing=closing_rec if pk1 is not None else None)
    #   (the deterministic row covers every line that ships, the closing line included: cheap() on the final package)
    try:
        pk = LP.apply(pk, pre)
    except Exception as e:                               # noqa: BLE001  never a crash, never a pin
        return None, f"rulings 68 / 72: {e}"[:400]
    problems = PP.gate_problems(pk["gates"], PP.required_gates(pk)) + \
        [f"{x}: the gated line differs from the one shipped" for x in PP.line_problems(pk)] + \
        PP.spotlight_problems(pk) + [f"{v['slot']}: {v['rule']}" for v in v_all]
    if problems:
        return None, f"a required gate is not exactly PASS: {problems}"[:600]
    log(f"  SPOTLIGHT PACKAGE: {mid} ({show}, {m['duration_s']} s" +
        (f", snapped from {m['spotlight_snap']['from']}" if m.get("spotlight_snap") else "") +
        f"), closing line: {pk['vo']['closing']!r}, runtime {pk['runtime_s_estimate']} s")
    return pk, None
