#!/usr/bin/env python3
"""pipeline/package.py — STEP 2 PACKAGE + STEP 3 OPTIMISE (law L-q, '01:55'; laws L-s..L-x; orchestrator 03:40, 05:25,
05:30): ANGLE FIRST. The moments need not share a development: under moments-first there is no same-event test.

usable()      moments a package may use: on screen eligible (word timing, law L-e), no hard-exclusion risk (L-u), not
              overlapping a moment delivered in the previous 24 h (novelty by video and time, L-p), channel not opted
              out, <= 20 s (L-u), a time-sensitive moment only from a source <= TIME_SENSITIVE_H old (L-v 3), no
              measured speaker change (L-v 1)
prescreen()   step A of law L-s on each usable moment's own context, ONCE per moment (package-independent), stored on
              the moment (`store`: a JSON ledger keyed by moment and the step-A prompt); never recomputed
ANGLES        role angle_write: up to MAX_ANGLES one-sentence angles, each backed by 3-8 cleared moments from >= 3
              channels (one clip per channel, L-u)
lineup_for()  code: hook + 2-3 clips for one angle, every segment from a different channel, at most one price prediction
              (L-u), a clip under SHORT_CLIP_S only as the punchline, and the length the runtime (60-70 s, L-o) AND the
              factory's EDL rule R4 (VO <= 25 % of runtime, one bridge per channel transition) both allow
write_v3()    role angle_write: the PBX MAX VO in the renderer's order (hook -> intro -> clip 1 -> bridge -> ...), in
              one of two styles (05:25 item 3): "host" (tease / hedge-matched hand-off of a VERIFIED speaker / the
              host's own takeaway after a clip) or "quote" (show + topic, at most four exact words quoted); NEVER a
              restatement of a clip's claim; word budgets from R4 and the runtime
GATES (hard, every one, recorded in a sealed inventory, package_pin.REQUIRED_GATES):
              cheap first (no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4;
              then concurrently: the classifying fidelity verdict (A / B / C / D, 05:25 items 1-2) and context
              integrity B0 / B / C (L-s; step A precomputed); exclusion (L-u) and the second recognition pass (L-v 2)
              start in the background as soon as a line-up is fixed; then COHERENCE (blind, >= 4).
              Every verdict avoids the vendors and model families of every reply whose text it judges (L-x).
              A rejected line goes back to the writer with the exact violations; a clip that fails exclusion or L-v 2
              is dropped and the angle re-lined; at most WRITES writes per angle and MAX_ANGLES angles; the first
              package with coherence >= COHERENCE_MIN wins (05:30).
OUTPUT pp.package/1: segments (moment ids, verbatim text, times), VO, title, caption, the gate inventory, the model per
              artefact, seconds and dollars.
"""
import hashlib
import itertools
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import context_integrity as CI
import eligibility as E
import vo_fidelity as VF

SEG_MAX_S = 20.0                   # L-u: at most 20 s per source video
RUNTIME_S = E.RUNTIME_S            # L-o: 60-70 s, the one hard length rule
WPS = 2.6                          # PBX MAX VO words per second: an ASSUMPTION until the render measures it
SIGNOFF_WORDS = 18                 # the preview's sign-off ("Clips today from A, B, and C. Go follow them ...")
FIXED_S = round(E.TAIL_S - SIGNOFF_WORDS / WPS, 2)   # credits card + outro + transitions without VO (~7.4 s)
VO_S = (6.0, 22.0)                 # the VO's seconds (intro + bridges), the slack that lands the runtime
R4_WPS, R4_PREROLL_S, R4_SHARE = 2.5, 1.0, 0.25      # edl_rules.rule_r4's own estimate (the factory's rule)
TIME_SENSITIVE_H = 24.0            # L-v 3: 'today' / 'just' / a price level only from a source this fresh
PRESCREEN_N = 24                   # moments whose own context is screened (step A) before any writing
PRESCREEN_BATCH = 8                # excerpts per step-A call
PRICE_PREDICTIONS_MAX = 1          # L-u: at most one per video
SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is the angle's punchline (the last clip)
MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
WRITES = 2
COHERENCE_MIN = 4                  # the blind coherence verdict: every rating >= 4 and a through-line, else next angle
BUDGET_S, BUDGET_USD = 360.0, 1.50  # orchestrator 05:25 item 5: per package
VO_DEPENDENT = ("NOT_ENTAILED", "POLARITY", "STRONGER", "FALSE_RELATION")   # context failures the VO's framing causes
VO_FIX = {"NOT_ENTAILED": "the viewer would take this clip to assert more than its speaker said in context: do not "
                          "frame or restate it",
          "POLARITY": "the framing flips what the speaker meant: do not characterise the speaker's view",
          "STRONGER": "the framing makes the speaker sound more certain than in context: do not restate or reinforce "
                      "the clip; keep any attribution's verb as hedged as the clip",
          "FALSE_RELATION": "the voice-over makes these speakers look like they respond to or agree WITH each other: "
                            "never relate one speaker to another"}


def usable(moments, ctx, delivered=(), optout=frozenset()):
    """delivered: moment ids, or {"video_id", "start", "end"} of moments delivered in the previous 24 h; a moment that
    overlaps a delivered one in the same video is not novel (audit p2 U2: an id changes when a record is re-punctuated)."""
    ids = {d for d in delivered if isinstance(d, str)}
    spans = [d for d in delivered if isinstance(d, dict)]
    out, why = [], {}
    for m in moments:
        mid = m["moment_id"]
        overlap = any(d.get("video_id") == m["video_id"] and float(d["start"]) < float(m["end"]) and
                      float(m["start"]) < float(d["end"]) for d in spans)
        if not m.get("on_screen_ok"):
            why[mid] = "not eligible on screen: " + "; ".join(
                f"{r}: {', '.join(v['reasons'])}" for r, v in (m.get("eligibility") or {}).items() if not v["ok"])
        elif m.get("excluded"):
            why[mid] = f"hard exclusion (L-u): {m['excluded']}"
        elif mid in ids or overlap:
            why[mid] = "delivered in the previous 24 h (or overlaps a delivered moment)"
        elif m["channel_id"] in optout:
            why[mid] = "channel opted out"
        elif m.get("duration_s") is None or m["duration_s"] > SEG_MAX_S:
            why[mid] = f"{m.get('duration_s')} s: over the {SEG_MAX_S} s per source video (L-u) or unmeasured"
        elif time_sensitive(m) and (E.age_hours(m["published_at"], ctx.now) is None or
                                    E.age_hours(m["published_at"], ctx.now) > TIME_SENSITIVE_H):
            why[mid] = f"time-sensitive words from a source older than {TIME_SENSITIVE_H} h (L-v 3)"
        elif (m.get("speaker") or {}).get("turn_change_inside") is True:
            why[mid] = "a speaker change inside (L-v 1)"
        else:
            out.append(m)                              # an unmeasured speaker is a CANDIDATE; L-v 2 decides (M11)
    return out, why


def time_sensitive(m):
    """L-v 3, MEASURED (audit C2 K6): the miner's flag, OR a recency word / a current-kind price in the clip's own
    words."""
    t = m.get("text") or ""
    return "time_sensitive" in m.get("risk", []) or bool(VF.time_words(t)) or \
        any(kind == "current" for _, kind in VF.price_mentions(t))


def runtime(segs, vo_s):
    """segments' word spans + every spoken VO second (intro, bridges AND the sign-off) + FIXED_S (audit p2 M4)."""
    return round(sum(m["duration_s"] for m in segs) + vo_s + FIXED_S, 2)


R4_MOMENTS_SHARE = 0.40            # orchestrator 06:00 ruling 4: moments-first VO up to 40 % of the runtime; a VO line
                                   # after the hook, after every clip and after the last clip; 60-70 s stays hard


def r4_max_vo_words(content_s, n_vo):
    """The most VO words (intro + bridges) the moments-first R4 allows: edl_rules' own estimate (words / 2.5 + 1 s per
    VO line) <= 40 % of the runtime estimate (content + VO and the standard sign-off at WPS + FIXED_S)."""
    num = R4_MOMENTS_SHARE * (content_s + SIGNOFF_WORDS / WPS + FIXED_S) - R4_PREROLL_S * n_vo
    return max(0, int(num / (1 / R4_WPS - R4_MOMENTS_SHARE / WPS)))


def min_vo_words(content_s):
    """The fewest VO words (intro + bridges) that land 60 s: content + VO + the standard sign-off + FIXED_S >= 60."""
    return max(0, int(WPS * (RUNTIME_S[0] - content_s - SIGNOFF_WORDS / WPS - FIXED_S) + 0.999))


def content_range(n_clips=2):
    """Seconds the segments may fill so that some VO lands the runtime in 60-70 s AND fits R4 (one VO line for the
    intro + one bridge per clip but the last)."""
    n_vo = 1 + (n_clips - 1)
    lo = next(c / 10 for c in range(200, 700) if min_vo_words(c / 10) <= r4_max_vo_words(c / 10, n_vo))
    return lo, RUNTIME_S[1] - FIXED_S - SIGNOFF_WORDS / WPS - VO_S[0]


def r4(pk):
    """R4 for a moments-first package, as the orchestrator ordered it at 06:00 (ruling 4; the integrator brings
    edl_rules.rule_r4 to it): VO (intro + bridges, edl_rules' estimate 2.5 w/s + 1 s per line) <= 40 % of the runtime
    estimate; the word caps of config.py; at most one VO line after each clip (the last clip included).
    -> (ok, reason). The share over clips + VO (today's edl_rules denominator) is reported beside it."""
    from config import BRIDGE_WORD_CAP, INTRO_WORD_CAP
    n_clips = len(pk["segments"]) - 1
    words = [len((pk["vo"]["intro"] or "").split())] + [len(b.split()) for b in pk["vo"]["bridges"]]
    n_lines = (1 if pk["vo"]["intro"] else 0) + len(pk["vo"]["bridges"])
    vo_s = sum(words) / R4_WPS + R4_PREROLL_S * n_lines
    share = vo_s / pk["runtime_s_estimate"]
    share_old = vo_s / (sum(sg["duration_s"] for sg in pk["segments"]) + vo_s)
    after = list(pk["vo"]["bridges_after_clip"])
    fails = []
    if words[0] > INTRO_WORD_CAP:
        fails.append(f"intro {words[0]} words (max {INTRO_WORD_CAP})")
    fails += [f"bridge {i + 1} {w} words (max {BRIDGE_WORD_CAP})" for i, w in enumerate(words[1:]) if w > BRIDGE_WORD_CAP]
    if len(set(after)) != len(after) or any(type(a) is not int or not 1 <= a <= n_clips for a in after):
        fails.append(f"bridges after clips {after}: one per clip, 1..{n_clips}")
    if share > R4_MOMENTS_SHARE:
        fails.append(f"VO={share:.1%} of the runtime (max {R4_MOMENTS_SHARE:.0%})")
    note = f"VO {vo_s:.1f} s = {share:.1%} of the {pk['runtime_s_estimate']} s runtime ({share_old:.1%} of clips + VO)"
    return (not fails), ("R4 (moments-first, 06:00) FAIL: " + "; ".join(fails) if fails else
                         "R4 (moments-first, 06:00) PASS") + f" | {note}"


def budgets(content_s, n_bridges=1):
    """Word budgets (intro, each bridge, (min, max) total) that land 60-70 s and fit R4; 40 % to the intro."""
    hi = min(r4_max_vo_words(content_s, 1 + n_bridges), int(VO_S[1] * WPS))
    lo = min(min_vo_words(content_s), hi)
    return max(6, int(hi * 0.4)), max(4, int(hi * 0.6 / max(1, n_bridges))), (lo, hi)


def _name(m, ctx):
    return (ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"]


def signoff(segs, ctx):
    """L-a: the spoken sign-off names exactly the credit set, hook first (code, never the model)."""
    names = list(dict.fromkeys(_name(m, ctx) for m in segs))
    who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + f", and {names[-1]}"
    return f"Clips today from {who}. Go follow them for more. Links are below."


def plain_vo(segs, ctx):
    """L-w 2: the plain factual fallback VO ("Next, <show> on <topic>."): it claims nothing beyond who speaks. Ranked
    last (orchestrator 03:40); the title names whole channels only (U11)."""
    intro = {"text": f"Here's {_name(segs[0], ctx)} on Bitcoin.", "cites": []}
    bridges = [{"text": f"Next, {_name(m, ctx)} on Bitcoin.", "cites": []} for m in segs[2:]]
    chans = list(dict.fromkeys(_name(m, ctx) for m in segs))
    title = "Bitcoin: " + ", ".join(chans[:-1]) + f" and {chans[-1]}"
    while len(title) > 70 and len(chans) > 1:
        chans = chans[:-1]
        title = "Bitcoin: " + ", ".join(chans) + " and others"
    caption = f"Clips from {', '.join(dict.fromkeys(_name(m, ctx) for m in segs))}. Links to every source below."
    return intro, bridges, {"text": title[:70], "cites": []}, {"text": caption, "cites": []}


def assemble(order, by_id, fields, ctx, vo_kind):
    segs = [by_id[i] for i in order]
    lines = [dict(fields["intro"], slot="intro")] + \
        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"].startswith(("intro", "bridge")))
    pk = {"schema": "pp.package/1", "type": fields.get("type", "moments"), "angle": fields.get("angle", ""),
          "vo_kind": vo_kind, "style": fields.get("style"),
          "segments": [{"label": "hook" if i == 0 else f"clip_{i:02d}", "moment_id": m["moment_id"],
                        "video_id": m["video_id"], "channel_id": m["channel_id"], "channel": _name(m, ctx),
                        "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
                        "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
                        "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
                        "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s"}
                       for i, m in enumerate(segs)],
          "vo": {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
                 "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1)),     # the renderer's after_clip
                 "signoff": signoff(segs, ctx)},
          "title": fields["title"]["text"], "caption": fields["caption"]["text"],
          "hook_first_words": " ".join(segs[0]["text"].split()[:8]),
          "lines": lines}
    so_words = len(pk["vo"]["signoff"].split())
    pk["runtime_s_estimate"] = runtime(segs, (vo_words + so_words) / WPS)
    pk["runtime_note"] = (f"segments {sum(m['duration_s'] for m in segs):.2f} s (word timing) + VO {vo_words} words + "
                          f"sign-off {so_words} words at {WPS} w/s (assumed) + fixed {FIXED_S} s (credits card, outro, "
                          f"transitions); the render measures the final")
    return pk


# ── step A once per moment (orchestrator 05:25 item 5) ──

STEP_A_VERSION = hashlib.sha256(CI.STEP_A.encode()).hexdigest()[:12]


def _load_store(store):
    if not store or not os.path.exists(store):
        return {}
    with open(store) as f:
        return json.load(f)


def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRESCREEN_N, batch=PRESCREEN_BATCH,
              store=None, log=print):
    """Step A (context only, package-independent by law L-s) on the best n usable moments, distinct channels first:
    ({moment_id: A item}, {moment_id: [failing rules]}, {vendor}, {family}). Each moment is screened ONCE: a stored item
    (same moment, same step-A prompt, a back-end off the writers' vendor and family) is reused, never recomputed.
    writer_vendor / writer_family: of the writers, so step A never runs on them."""
    import providers as P
    seen, order = set(), []
    ranked = sorted(ms, key=lambda m: (-m["rank_score"], m["moment_id"]))
    for m in ranked:
        if m["channel_id"] not in seen:
            order.append(m)
            seen.add(m["channel_id"])
    order = (order + [m for m in ranked if m not in order])[:n]
    db = _load_store(store)
    wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
    a_by, fails, vendors, families, todo = {}, {}, set(), set(), []
    for m in order:
        rec = db.get(f"{m['moment_id']}:{STEP_A_VERSION}")
        b = router.backends.get((rec or {}).get("backend"))
        if rec and b is not None and b.vendor not in wv and b.family not in wf:
            a_by[m["moment_id"]] = rec
            fails[m["moment_id"]] = CI.a_failures(rec)
            vendors.add(b.vendor)
            families.add(b.family)
        else:
            todo.append(m)
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        contexts = {}
        for m in chunk:
            text, win = CI._window_text(sources[m["video_id"]], m["sentences"][0], m["sentences"][1], *m["words"])
            contexts[m["moment_id"]] = {"text": text, "title": sources[m["video_id"]].title or "",
                                        "channel": _name(m, ctx), "window": win,
                                        "published": str(m.get("published_at") or "")[:16],
                                        "show_date": ctx.now.strftime("%Y-%m-%d")}
        try:
            got, backend = CI.step_a(router, contexts, writer_vendor, seed=7 + i, writer_family=writer_family)
        except Exception as e:                           # unreadable: these moments are not cleared (law L-m)
            for m in chunk:
                fails[m["moment_id"]] = [f"STEP_A_UNAVAILABLE: {type(e).__name__}"]
            continue
        b = router.backends.get(backend)
        vendors.add(b.vendor if b else backend)
        families.add(b.family if b else backend)
        for mid, a in got.items():
            a_by[mid] = a
            fails[mid] = CI.a_failures(a)
            db[f"{mid}:{STEP_A_VERSION}"] = a
    if store and todo:
        os.makedirs(os.path.dirname(os.path.abspath(store)), exist_ok=True)
        with open(store + ".tmp", "w") as f:
            json.dump(db, f, indent=1)
        os.replace(store + ".tmp", store)
    return a_by, fails, vendors, families


ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words, with a
voice-over that makes a point. Below are clips (verbatim quotes, each with its channel and length) that passed our
checks. The channels were not in one conversation and never answer each other.

{note}
{clips}

Find up to {k} ANGLES, best first. An angle is ONE sentence a viewer could repeat: a point that several of these clips
GENUINELY support together (each clip adds a different reason, fact or voice to the same point). Do not make a point
the clips do not state. Do not build an angle on a price level or move as if it were today's news unless a clip says
it is today's.
The video uses ONE clip per channel: a hook and 2-3 clips, from 3-4 DIFFERENT channels, together {lo:.0f}-{hi:.0f}
seconds of clips. Give as many good angles as the clips allow (aim for {k}); for each angle give: "angle" (the
sentence); "moments": the ids of 5 to 8 clips that support it (more choice survives a clip that later fails a check),
from at least 3 different channels, with enough seconds among them; "hook": one of those ids whose FIRST WORDS grab
attention AND set up the angle; "support": for each of those ids, a few words on what it adds (an internal note).
Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "id", "id"], "hook": "id",
"support": {{"id": "..."}}}}]}}"""

STYLES = {
    "host": "HOST STYLE: you have a point of view. A bridge may (a) tease the next clip with a question or a topic, never "
            "saying what its speaker thinks; (b) hand off with an attribution ONLY for a clip whose speaker is marked "
            "VERIFIED, with the clip's own hedge (\"Stephan Livera thinks so.\"); (c) land your own takeaway AFTER a "
            "clip, as your opinion, never as what the speaker said.",
    "quote": "QUOTE-LED STYLE: introduce each clip by its show and its topic in a few words; you may quote AT MOST FOUR "
             "exact words of that clip in quotation marks; the point is carried by the sequence of clips and the ONE "
             "title."}

WRITE_V3 = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
THE ANGLE (the point this video makes): "{angle}"
The clips, in play order (verbatim; the channels were not in one conversation and never answer each other):

{note}
{lineup}

The video plays: the HOOK clip, then your INTRO, then clip 1, then {slots}, then a sign-off that credits every channel
(written by code).
Write:
- "intro": heard right AFTER the hook: your own take that sets up the angle.
- "bridges": exactly {n_bridges} line(s), one after each clip but the last.
- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters.
- LENGTH: intro + bridges together {lo}-{hi} words; the intro at most {intro_words}, each bridge at most {bridge_words}.
Every line gives "cites": the ids of the clips it relies on (none for your own commentary).
{style}
RULES (a line that breaks one is rejected):
- NEVER restate a clip's claim before or after it, and never repeat its words: the clip says it, in its own words.
- Your OWN commentary (an opinion, framing, a question, a tease, a takeaway) is welcome, but it must contain no number,
  price, date, named person or company, must not say or imply what any speaker thinks, and must not relate speakers.
- Say what a speaker says or thinks ONLY for a clip marked VERIFIED, by that name, with the clip's own hedge: "thinks"
  for "I think", "feels" for "I feel like", "says" only for a flat statement. For any other clip credit the SHOW only
  ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says".
- Never say or imply that channels agree, answer, rebut or react to each other.
- No price level; no advice to buy, sell or use leverage; no quotes except a clip's exact words; no "destroys",
  "slams", "exposes", "admits", "confirms", "caught".
{extra}Return ONLY this JSON object: {{"intro": {{"text": "...", "cites": []}}, "bridges": [{{"text": "...", "cites": ["id"]}}],
"title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}}}}"""

COHERENCE_PROMPT = """You watch a 60-second video. Here is everything it says and shows, in order (each clip is a
different person's own words).

{package}

1) State the video's through-line in ONE sentence, or "none" if it has none.
2) For each clip, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
3) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
   1 = no point, or a point the clips do not support).
Return ONLY this JSON object: {{"through_line": "...", "clips": {{"<label>": 1}}, "vo_point": 1}}"""


def current_levels(sources, ctx, hours=24.0):
    """The Bitcoin price levels this universe states as CURRENT (audit p2 C10): from sentences that name Bitcoin, in a
    clause with a present-tense word before the price and no future, conditional or history word in the sentence
    (vo_fidelity.current_level_values), from sources <= `hours` old (L-v 3)."""
    out = set()
    for src in sources:
        age = E.age_hours(src.published_at, ctx.now)
        if age is None or age > hours:
            continue
        for a, b in src.sentences:
            t = E.spoken(src.tokens[a:b + 1])
            if E.names_bitcoin(t):
                out |= set(VF.current_level_values(t))
    return sorted(out)


def check_angles(obj, by_id, k=MAX_ANGLES):
    if not isinstance(obj, dict) or set(obj) != {"angles"} or not isinstance(obj["angles"], list) or \
            not 1 <= len(obj["angles"]) <= k:
        raise ValueError(f"exactly {{'angles': [1-{k} items]}}")
    out = []
    for i, a in enumerate(obj["angles"]):
        if not isinstance(a, dict) or set(a) != {"angle", "moments", "hook", "support"}:
            raise ValueError(f"angle {i + 1}: keys must be exactly angle, moments, hook, support")
        ms = a["moments"]
        if not isinstance(a["angle"], str) or not a["angle"].strip() or not isinstance(ms, list) or \
                not all(isinstance(m, str) for m in ms):
            raise ValueError(f"angle {i + 1}: a sentence and a list of offered ids")
        unknown = [m for m in ms if m not in by_id]
        if unknown:
            raise ValueError(f"angle {i + 1}: ids not offered {unknown[:3]} (never dropped silently)")
        if not 3 <= len(ms) <= 8 or len(set(ms)) != len(ms):
            raise ValueError(f"angle {i + 1}: 3-8 distinct offered ids")
        if len({by_id[m]["channel_id"] for m in ms}) < 3 or a["hook"] not in ms:
            raise ValueError(f"angle {i + 1}: >= 3 channels (one clip per channel, L-u), and the hook one of its moments")
        if not isinstance(a["support"], dict) or set(a["support"]) != set(ms):
            raise ValueError(f"angle {i + 1}: 'support' needs exactly its moment ids")
        out.append(a)
    return out


def lineup_for(angle, by_id, dropped=frozenset()):
    """Hook + 2-3 clips for one angle: the proposer's hook (else the angle's best hook-eligible moment by its first
    2 s), clips from the angle's other moments, every segment from a different channel (L-u), at most
    PRICE_PREDICTIONS_MAX price predictions (L-u), a clip under SHORT_CLIP_S only as the last (the punchline), the
    length the runtime AND R4 allow. Best by the proposer's order. None if impossible."""
    ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
    hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok")]
    hooks.sort(key=lambda m: (m["moment_id"] != angle["hook"], -m["scores"]["hook_first_2s"]))
    for h in hooks:
        pool = [m for m in ms if m is not h and (m.get("eligibility") or {}).get("clip", {}).get("ok")
                and m["channel_id"] != h["channel_id"]]
        best = None
        for n in (3, 2):
            lo, hi = content_range(n)
            for combo in itertools.combinations(pool, n):
                if len({m["channel_id"] for m in combo}) != n:
                    continue
                if sum("price_prediction" in m.get("risk", []) for m in (h, *combo)) > PRICE_PREDICTIONS_MAX:
                    continue
                order = sorted(combo, key=lambda m: angle["moments"].index(m["moment_id"]))
                if [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]:
                    continue
                dur = h["duration_s"] + sum(m["duration_s"] for m in order)
                if not lo <= dur <= hi:
                    continue
                key = (n, -sum(angle["moments"].index(m["moment_id"]) for m in order))
                if best is None or key > best[0]:
                    best = (key, [h] + order)
            if best:
                return best[1]
    return None


STOP = frozenset("a an the and or but so of to in on at for from with by as is are was were be been it its it's this that "
                 "these those there here i you he she we they me him her us them my your his our their not no do does "
                 "did just like kind sort very really some any all".split())


def duplicates(pk):
    """A clip must add something (orchestrator 03:40; audit p2 C16): no VO line (intro, every bridge), no title and no
    caption repeats ANY clip's words: a run of >= 5 canonical tokens with >= 3 content words, or >= 60 % of a short
    clip's (<= 15 content words) CONTENT words."""
    out = []
    lines = [(x["slot"], x["text"]) for x in pk["lines"]]
    for seg in pk["segments"]:
        ct = VF.ctoks(seg["text"])
        content = [t for t in ct if t not in STOP]
        for slot, text in lines:
            lt = VF.ctoks(text)
            run5 = any(VF._run_in(ct[j:j + 5], lt) and sum(t not in STOP for t in ct[j:j + 5]) >= 3
                       for j in range(max(0, len(ct) - 4)))
            lset = {t for t in lt if t not in STOP}
            share = len([t for t in content if t in lset]) / max(1, len(content))
            if run5 or (len(content) <= 15 and share >= 0.6):
                out.append({"slot": slot, "rule": "DUPLICATE", "detail": f"repeats the words of {seg['label']}"})
    return out


NO_LINE = re.compile(r"^\W*(none|no\b|n/?a\b|unclear|nothing|there is no)", re.I)


def coherence(router, pk, writer_vendor, seed=7, writer_family=None):
    """The blind QUALITY verdict (never the vendor / family of the text it judges): through-line + ratings. ->
    (ok, verdict). A through-line that reads 'None.', 'no through-line', 'n/a' or is under 4 words is none (M7)."""
    import providers as P
    r = None
    try:
        r = router.call("coherence_verdict", COHERENCE_PROMPT.format(package=CI.package_view(pk)), 1200, seed,
                        avoid_vendor=writer_vendor, avoid_family=writer_family)
        v = json.loads(r.text.strip())
        labels = [sg["label"] for sg in pk["segments"]]
        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labels) or \
                any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
            raise ValueError("coherence verdict out of contract")
    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
        if r is not None and isinstance(e, (ValueError, TypeError)):
            router.reject(r)
        return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False}
    tl = v["through_line"] if isinstance(v["through_line"], str) else ""
    ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
        min(list(v["clips"].values()) + [v["vo_point"]]) >= COHERENCE_MIN
    return ok, dict(v, backend=r.backend, measured=True, replayed=bool(getattr(r, "replayed", False)))


def _lineup_block(segs, ctx, a_by):
    from story_semantics import quote_data
    out = []
    for i, m in enumerate(segs):
        ver = (a_by.get(m["moment_id"]) or {}).get("speaker_verified")
        who = f"speaker VERIFIED: {_name(m, ctx)}" if ver else "speaker NOT verified (credit the show only)"
        out.append(f'{"HOOK" if i == 0 else f"CLIP {i}"} id={m["moment_id"]} | show: {_name(m, ctx)} | {who} | '
                   f'{m["duration_s"]:.1f} s | "{quote_data(m["text"], 700)}"')
    return "\n".join(out)


def write_v3(router, angle, segs, ctx, a_by, style="host", extra="", seed=7, avoid_vendor=None):
    from select_by_id import UNTRUSTED
    from story_semantics import quote_data
    content = sum(m["duration_s"] for m in segs)
    nb = len(segs) - 2
    iw, bw, (lo, hi) = budgets(content, nb)
    slots = ", then ".join(f"your bridge, then clip {i + 2}" for i in range(nb)) or "nothing"
    angle_text = " ".join(quote_data(angle["angle"], 300).replace('"', "'").split())     # M9: escaped, one line
    prompt = WRITE_V3.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
                             lineup=_lineup_block(segs, ctx, a_by), slots=slots, n_bridges=nb, lo=lo, hi=hi,
                             intro_words=min(iw, 30), bridge_words=min(bw, 20), style=STYLES[style],
                             extra=(extra + "\n") if extra else "")
    r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor)
    try:
        obj = json.loads(r.text.strip())
        ids = [m["moment_id"] for m in segs]
        keys = {"intro", "bridges", "title", "caption"}
        if not isinstance(obj, dict) or set(obj) != keys:
            raise ValueError(f"keys must be exactly {sorted(keys)}")
        if not isinstance(obj["bridges"], list) or len(obj["bridges"]) != nb:
            raise ValueError(f"'bridges' must hold {nb} lines")
        for slot, ln in [("intro", obj["intro"]), ("title", obj["title"]), ("caption", obj["caption"])] + \
                [(f"bridge_{i + 1}", b) for i, b in enumerate(obj["bridges"])]:
            if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
                    not ln["text"].strip() or not isinstance(ln["cites"], list) or \
                    any(not isinstance(c, str) or c not in ids for c in ln["cites"]):
                raise ValueError(f"{slot}: needs text and cites from the line-up's ids")
        if len(obj["title"]["text"]) > 70 or len(obj["caption"]["text"]) > 220:
            raise ValueError("title <= 70 characters, caption <= 220")
    except (ValueError, TypeError):
        router.reject(r)
        raise
    return r, dict(obj, type="moments", angle=angle["angle"], style=style)


def fidelity_segments(pk, a_by):
    """The fidelity gate's view of the segments: the show always; the speaker only when step A VERIFIED the channel's
    host with quoted evidence (law L-v 1); otherwise not verified."""
    out = {}
    for sg in pk["segments"]:
        ver = (a_by.get(sg["moment_id"]) or {}).get("speaker_verified")
        out[sg["moment_id"]] = {"show": sg["channel"], "speaker": sg["channel"] if ver else None,
                                "names": [sg["channel"]] if ver else [], "video_id": sg["video_id"], "text": sg["text"]}
    return out


def cheap_checks(pk, a_by, levels, now):
    """The gates that cost nothing, run before any paid verdict: VO fidelity's deterministic rules, DUPLICATE,
    runtime, R4. -> (violations, det, dup, rt_ok, r4_res)."""
    segs_v = fidelity_segments(pk, a_by)
    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
    det = VF.check_deterministic(segs_v, lines, man, levels)
    dup = duplicates(pk)
    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
    r4_res = r4(pk)
    v = det["violations"] + dup + ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail":
                                                      f"{pk['runtime_s_estimate']} s outside 60-70 s: change the VO's "
                                                      f"length"}]) + \
        ([] if r4_res[0] else [{"slot": "-", "rule": "R4", "detail": r4_res[1]}])
    return v, det, dup, rt_ok, r4_res


def paid_gates(router, pk, sources, a_by, levels, now, writers_v, writers_f, pool):
    """The classifying fidelity verdict and context integrity (B0, B, C; step A precomputed), concurrently."""
    segs_v = fidelity_segments(pk, a_by)
    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
    a_use = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
    f_fid = pool.submit(VF.check, router, segs_v, lines, writers_v, 7, man, levels, writers_f)
    f_ctx = pool.submit(CI.check_contexts, router, pk, CI.contexts_from_sources(pk, sources, now), writers_v, 7, a_use,
                        writers_f, True)
    return f_fid.result(), f_ctx.result()


def exclusion_for(router, m, sources, cache):
    if m["moment_id"] not in cache:
        import moments as M
        src = sources[m["video_id"]]
        a, b = CI.window(src, m["sentences"][0], m["sentences"][1])
        w0, w1 = m["words"]
        cache[m["moment_id"]] = M.exclusion_verdict(
            router, m["text"], E.spoken(src.tokens[src.sentences[a][0]:w0]),
            E.spoken(src.tokens[w1 + 1:src.sentences[b][1] + 1]), avoid_model=(m.get("mined") or {}).get("by"))
    return cache[m["moment_id"]]


def truth_for(router, m, work_dir, cache):
    if m["moment_id"] not in cache:
        import transcript_truth as TT
        try:
            cache[m["moment_id"]] = TT.verify_segment(router, m["video_id"], float(m["start"]), float(m["end"]),
                                                      m["text"], work_dir)
        except Exception as e:                         # not measured: never a pass (law L-m)
            cache[m["moment_id"]] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
    return cache[m["moment_id"]]


def _writers(router):
    """The vendor and family of the angle_write chain's first back-end not down (verdicts avoid them; a live failover
    adds the next writer's)."""
    for name in router.chain("angle_write"):
        b = router.backends.get(name)
        if b is not None and name not in router.down:
            return {b.vendor}, {b.family}
    return set(), set()


def _redo(violations):
    return ("Your previous script was REJECTED. Exactly these lines failed, with the reason; rewrite ONLY them:\n" +
            "\n".join(f"- {v['slot']}: {v['rule']}: {v['detail']}" for v in violations)[:1800])


def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
          writes=WRITES, work_dir=None, store=None, styles=("host", "quote"), spend=None):
    """Angle first, inside the orchestrator's budgets (05:25 item 5, 05:30): at most max_angles angles x `writes`
    writes, stopped at the first package that passes every hard gate with coherence >= COHERENCE_MIN. work_dir: where
    law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger. spend: a
    callable returning the ledger's USD (dollars per package). -> {"package", "packages", "tried", "angles", ...}."""
    t0 = time.time()
    usd0 = spend() if spend else None
    ms, why = usable(moments, ctx, delivered, optout)
    wv, wf = _writers(router)
    a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
    levels = current_levels(sources.values(), ctx)
    out = {"packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
           "prescreen": {"screened": len(fails), "cleared": len(cleared),
                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "package": None}
    log(f"  {len(ms)} usable, {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
    if len({m["channel_id"] for m in cleared.values()}) < 3:
        out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
        return out
    if not work_dir:
        out["why_none"] = "no work_dir: law L-v 2's second pass cannot run, so no package can pass (fail closed)"
        return out
    from select_by_id import UNTRUSTED
    from story_semantics import quote_data
    clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s | "{quote_data(m["text"], 600)}"'
                      for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
    lo, hi = content_range(2)[0], content_range(3)[1]
    angles, angle_reply = None, None
    for seed in (7, 8):                               # one re-ask on an out-of-contract reply (never served again)
        r = None
        try:
            r = router.call("angle_write", ANGLE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"),
                                                               clips=clips, k=max_angles, lo=lo, hi=hi), 3000, seed)
            angles, angle_reply = check_angles(json.loads(r.text.strip()), cleared, max_angles), r
            break
        except Exception as e:
            if r is not None:
                router.reject(r)
            out["why_none"] = f"no readable angles: {type(e).__name__}: {str(e)[:200]}"
    if not angles:
        return out
    out.pop("why_none", None)
    out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
    writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
    log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)")
    exc, tru = {}, {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for ai, angle in enumerate(angles):
            dropped, w_used = set(), 0
            while w_used < writes and not out["packages"]:
                segs = lineup_for(angle, cleared, frozenset(dropped))
                rec = {"angle": ai + 1, "text": angle["angle"],
                       "lineup": [m["moment_id"] for m in segs] if segs else None, "attempts": []}
                out["tried"].append(rec)
                if segs is None:
                    rec["why"] = "no line-up: fewer than a hook + 2 clips from distinct channels in the length rules"
                    break
                bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
                                       pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
                extra, relined = "", False
                while w_used < writes:
                    style = styles[min(w_used, len(styles) - 1)]
                    w_used += 1
                    try:
                        wr, fields = write_v3(router, angle, segs, ctx, a_by, style, extra, seed=7 + w_used + 10 * ai)
                    except Exception as e:
                        rec["attempts"].append({"style": style, "writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
                        continue
                    writers_v.add(wr.vendor)
                    writers_f.add(wr.family)
                    stale = [m for m in segs if (lambda b: b is None or b.vendor in writers_v or b.family in writers_f)(
                        router.backends.get((a_by.get(m["moment_id"]) or {}).get("backend")))]
                    if stale:                                  # audit C2 K5: never judged by the writer's vendor
                        got_a, _, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f, store=None)
                        for mid, a_ in got_a.items():
                            a_by[mid] = a_
                        if any(CI.a_failures(a_by.get(m["moment_id"], {})) for m in stale):
                            rec["why"] = "step A, re-screened off the writer's vendor, fails a clip: re-lined"
                            dropped |= {m["moment_id"] for m in stale if CI.a_failures(a_by.get(m["moment_id"], {}))}
                            relined = True
                            break
                    pk = assemble([m["moment_id"] for m in segs], cleared, fields, ctx,
                                  f"written ({style}), attempt {w_used}")
                    cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
                    att = {"style": style, "writer": wr.backend, "runtime": pk["runtime_s_estimate"],
                           "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]]}
                    rec["attempts"].append(att)
                    log(f"  angle {ai + 1} write {w_used} ({style}, {wr.backend}): " +
                        ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
                        + f" ({time.time() - t0:.0f} s)")
                    if cheap:
                        att["violations"] = cheap
                        extra = _redo(cheap)
                        continue
                    fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
                    framing = [v for v in cx["violations"] if v["rule"] in VO_DEPENDENT]
                    att["violations"] = fid["violations"] + cx["violations"]
                    att["verdict_classes"] = (fid.get("verdict") or {}).get("classes")
                    log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'}, context {'PASS' if cx['ok'] else 'FAIL'} "
                        f"({time.time() - t0:.0f} s)")
                    if not fid["ok"] or not cx["ok"]:
                        if fid["ok"] and not framing:
                            rec["why"] = "context integrity failed on something the VO cannot fix"
                            w_used = writes
                            break
                        extra = _redo(fid["violations"] + [{"slot": v["segment"], "rule": v["rule"],
                                                            "detail": VO_FIX.get(v["rule"], v["detail"])}
                                                           for v in framing])
                        continue
                    got = {mid: (f[0].result(), f[1].result()) for mid, f in bg.items()}
                    lost = {mid for mid, (e, t) in got.items() if e.get("verdict") != "keep" or not t.get("ok")}
                    att["exclusion"] = {mid: e for mid, (e, _) in got.items()}
                    att["second_pass"] = {mid: t for mid, (_, t) in got.items()}
                    if lost:
                        dropped |= lost
                        rec["why"] = f"exclusion / L-v 2 dropped {sorted(lost)}: re-lined"
                        relined = True
                        break
                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)
                    att["coherence"] = coh
                    log(f"    coherence {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo {coh.get('vo_point')} "
                        f"({time.time() - t0:.0f} s)")
                    a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
                    pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
                                            {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
                                            ok_c, coh)
                    if not ok_c:
                        rec["why"] = "coherence below 4 or no through-line: next angle"
                        w_used = writes
                        break
                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend,
                                    "fidelity_verdict": fid.get("backend"), "context": cx.get("backends"),
                                    "coherence": coh.get("backend")}
                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh}
                    pk["seconds"] = round(time.time() - t0, 1)
                    pk["usd"] = round(spend() - usd0, 4) if spend else None
                    out["packages"].append(pk)
                    rec["result"] = "PACKAGE"
                    break
                if out["packages"] or not relined:
                    break
            if out["packages"]:
                break
            if time.time() - t0 > BUDGET_S * 2 or (spend and spend() - usd0 > BUDGET_USD * 2):
                out["why_none"] = "twice the per-package time / spend budget is used: stopped"
                break
    out["package"] = out["packages"][0] if out["packages"] else None
    out["seconds"] = round(time.time() - t0, 1)
    out["usd"] = round(spend() - usd0, 4) if spend else None
    return out


def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
    """The sealed GATE INVENTORY (audit p2 C1; package_pin.REQUIRED_GATES): one row per hard gate, each
    {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m)."""
    row = lambda ok, by, replayed=False, n=1, measured=True: {
        "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
        "replayed": replayed if isinstance(replayed, bool) else None, "n": n}     # None (unstated) refuses the pin

    def rep(values):                                 # tri-state over several replies (audit C2 K4)
        values = list(values)
        return None if any(not isinstance(x, bool) for x in values) else any(values)
    det = fid["deterministic"]
    viol = {v["rule"] for v in ctx_.get("violations") or []}
    a_rows = list((a_by or {}).values())
    return {
        "vo_fidelity_deterministic": row(det["ok"], "code (vo_fidelity.check_deterministic)"),
        "vo_fidelity_verdict": row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"), fid.get("replayed"),
                                   measured=bool(fid.get("measured"))),
        "duplicate": row(not dup, "code (package.duplicates)"),
        "price_now": row(not any(v["rule"] == "PRICE_NOW" for v in det["violations"]),
                         "code (vo_fidelity.price_now)", measured=bool(det.get("price_now_measured"))),
        "runtime": row(rt_ok, f"code (estimate at {WPS} w/s)"),
        "r4": row(bool(r4_res[0]), "package.r4 (moments-first R4, orchestrator 06:00)"),
        "context_a": row(bool(a_rows) and not any(CI.a_failures(a) for a in a_rows),
                         sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
                         n=len(a_rows)),
        "context_b": row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
                         measured=bool(ctx_.get("measured"))),
        "context_c": row(ctx_.get("ok") is True and not (viol & {"NOT_ENTAILED", "POLARITY", "STRONGER"}),
                         (ctx_.get("backends") or {}).get("C"), ctx_.get("replayed"), measured=bool(ctx_.get("measured"))),
        "exclusion": row(all(e.get("verdict") == "keep" for e in exc.values()),
                         sorted({str(e.get("backend")) for e in exc.values()}),
                         rep(e.get("replayed") for e in exc.values()), n=len(exc),
                         measured=all(e.get("measured") for e in exc.values())),
        "second_pass": row(all(t.get("ok") for t in truth.values()), sorted({str(t.get("model")) for t in truth.values()}),
                           rep(t.get("replayed") for t in truth.values()), n=len(truth),
                           measured=all("error" not in t for t in truth.values())),
        "cuttable": row(all((t.get("edges") or {}).get("cuttable") is True for t in truth.values()),
                        "transcript_truth.edges: the independent recogniser's sentence boundary at every IN and OUT "
                        "(orchestrator 06:45 ruling C / 7)", rep(t.get("replayed") for t in truth.values()), n=len(truth),
                        measured=all("edges" in t for t in truth.values())),
        "coherence": row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
    }
