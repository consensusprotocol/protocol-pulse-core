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
              channels (one clip per channel, L-u), listed in PLAY ORDER (L-y 3)
lineup_for()  code: the hook + 2-4 clips for one angle in the proposer's play order, every segment from a different
              channel, at most one price prediction (L-u), a clip under SHORT_CLIP_S only as the punchline, and seconds
              that let ONE takeaway land the factory's runtime estimate in 60-70 s (L-o, L-y 4)
medley()      the blind clips-ALONE verdict (L-y 3): a through-line, a rating per clip, a verdict per join
write_takeaway() role angle_write: the ONE takeaway (host commentary), ONE title, ONE caption, and the one bridge only
              at a join the clips-alone verdict flagged (L-y 2); NEVER a restatement of a clip's claim
GATES (hard, every one, recorded in a sealed inventory, package_pin.required_gates):
              the clips-alone verdict first (no writing before it passes);
              cheap (no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4, the L-y shape;
              then concurrently: the classifying fidelity verdict (A / B / C / D, 05:25 items 1-2) and context
              integrity B0 / B / C (L-s; step A precomputed); exclusion (L-u) and the second recognition pass (L-v 2)
              start in the background once the clips-alone verdict passes; then COHERENCE with the takeaway (>= 4).
              Every verdict avoids the vendors and model families of every reply whose text it judges (L-x).
              A rejected line goes back to the writer with the exact violations; a clip that fails exclusion or L-v 2
              is dropped and the angle re-lined; at most WRITES writes per line-up, LY_LINEUPS line-ups per angle and
              MAX_ANGLES angles; the first package that passes every gate wins (05:30).
OUTPUT pp.package/1: segments (moment ids, verbatim text, times), VO, title, caption, the gate inventory, the model per
              artefact, seconds and dollars.

L-y VOICEOVER IS MINIMAL (orchestrator 20:30 ET Nov 12, PBX's verdict on the reviewed video; amends L-q, L-w 1 and
R4-moments): build() makes the MEDLEY the default shape. The hook and 2-4 clips play back to back with no narration,
then ONE takeaway after the last clip (host commentary, class D, one or two sentences, <= 30 words), then the
sign-off. There is no intro after the hook and no bridge.
- SELECTION carries the weight: the angle proposer gives the moments in PLAY ORDER, each clip's opening making sense
  after the previous clip's ending in the speaker's own words (lineup_for).
- The blind coherence verdict is asked on the clips ALONE first (medley(): a through-line a viewer can state, a rating
  per clip, and per join whether a viewer can follow the jump). Only then is it asked on the takeaway (coherence()).
- A bridge is the EXCEPTION: at most ONE, only at the join the clips-alone verdict flagged, and only when the writer
  also judges a viewer cannot follow it. The package records why (ly_shape()). Two or more flagged joins mean the
  line-up is wrong: other clips are picked.
- 3-5 clips; the factory's runtime estimate stays inside 60-70 s (the measured final is accepted at 58-72 s, ruling 12).
- One clip per channel unless the supply forces otherwise, and then the package says so (supply_exception).
"""
import hashlib
import itertools
import json
import math
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import context_integrity as CI
import eligibility as E
import house_style as HS
import vo_fidelity as VF

SEG_MAX_S = 20.0                   # L-u: at most 20 s per source video
RUNTIME_S = E.RUNTIME_S            # L-o: 60-70 s, the packaging target the factory's estimate must meet (ruling 12)
VO_S = (6.0, 22.0)                 # the PBX MAX v3 VO's seconds (intro + bridges), content_range()'s slack
R4_WPS, R4_PREROLL_S, R4_SHARE = 2.5, 1.0, 0.25      # edl_rules.rule_r4's own estimate (the factory's rule)
TIME_SENSITIVE_H = 24.0            # L-v 3: 'today' / 'just' / a price level only from a source this fresh
PRESCREEN_N = 24                   # moments whose own context is screened (step A) before any writing
PRESCREEN_BATCH = 8                # excerpts per step-A call
PRICE_PREDICTIONS_MAX = 1          # L-u: at most one per video
SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is the angle's punchline (the last clip)
MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
WRITES = 2
COHERENCE_MIN = 4                  # the blind coherence verdict: every rating >= 4 and a through-line, else next angle
BUDGET_WALL_S = 900.0              # orchestrator 22:40 ruling 5 (Heimdall as the writer; was 05:25 item 5's 360 s x2):
BUDGET_USD_REPORTED = 1.50         # per package 15 min wall and $1.50 by the vendors' OWN reported cost,
BUDGET_USD_ESTIMATE = 5.00         # with the price-table estimate (it over-states ~7x) only as a hard ceiling
LINEUPS_PER_BUILD = 8              # RULING 41 (04:58 ET Nov 13): up to 8 line-ups per BUILD, over every angle. A clips-
                                   # alone failure is answered by swapping the segments rated below the bar (swap_lineup);
                                   # the bar itself is unchanged
SEARCH_USD_REPORTED = 3.00         # ruling 41: a build may spend $3 (vendor-reported) searching, reported in out["search"];
SEARCH_USD_ESTIMATE = 10.00        # ruling 5's $1.50 / 15 min is per PACKAGE delivered (its own line-up). The estimate
                                   # ceiling keeps ruling 5's ratio ($5.00 : $1.50) for calls whose vendor reports no cost
SEARCH_WALL_S = 2400.0             # the build ends cleanly before its driver's timeout (a killed build writes no record)
TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33 part 2: the ONE leading word a cut may trim
TRIM_SCORER_PENDING = True         # ruling 33 (b): the render's clip scorer (gemma3:27b on Ultron's GPU0, which the
                                   # pin stage may not use) must affirm every trimmed segment. RULING 49 (07:02 Nov 13):
                                   # YES, a trimmed clip is sealed with that verdict PENDING AT THE RENDER (stage_validate
                                   # runs before any render; a refusal there costs no GPU), stated in the sealed row and
                                   # per clip in the pin (scorer_pending: true). False: the render's check with no scorer
TRIMMED_PER_LINEUP_MAX = 1         # ruling 49 (b): at most ONE trimmed clip per line-up until the first trimmed clip has
                                   # been affirmed at validate once (the integrator says when): one refusal cannot sink a
                                   # line-up twice. package_pin.TRIMMED_PER_PIN_MAX holds the pin to the same number
SWAP_TOP = 10                      # candidates read per swapped place, best by score first, after the place's own
                                   # rules (a short clip only at the last place): audit 0510 C1, glm P1-3
NO_VOICE_AFTER = 2                 # ruling 3 (22:40): the takeaway failing its gates this many times ships no VO line
WRITER_DEADLINE_S = 300.0          # ruling 5: one writer call never waits more than 5 min; it fails over (deepseek ->
                                   # qwen -> xAI in the writer chain) and the failover is recorded
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


FINAL_TAIL_S = E.TAIL_S             # what a final adds to its word spans (credits card + sign-off, outro, cut edges, pads)


def runtime(segs, vo_lines):
    """The FACTORY's own estimate, the one its hard 60-70 s check reads (edl_rules._r4_moments, main a5ec0f17: "hook +
    clips + VO + FINAL_TAIL_S", each VO line "words / 2.5 + the 1.0 s pre-roll"): segments' word spans + every VO line
    (intro, bridges) at R4_WPS w/s + R4_PREROLL_S each + FINAL_TAIL_S (the sign-off is inside it). It replaced (07:42)
    this module's own estimate (2.6 w/s, no pre-roll, a fixed tail + the sign-off), which ran 3-4 s lower than the
    factory's on three VO lines. Neither is a measurement: the render measures the final (design section 8, open)."""
    vo = sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in vo_lines if t and t.strip())
    return round(sum(m["duration_s"] for m in segs) + vo + FINAL_TAIL_S, 2)


MOMENTS_TAKEAWAY_WORD_CAP = 30     # orchestrator 08:40 ruling 10: the VO line after the LAST clip (the takeaway) of a
                                   # moments pin; bridges BETWEEN clips keep config.BRIDGE_WORD_CAP (20)
R4_MOMENTS_SHARE = 0.45            # orchestrator 08:29 ruling 9: moments-first VO up to 45 % of the TOTAL runtime (06:00
                                   # ruling 4 said 40 %); a VO line after the hook, after every clip and after the last
                                   # clip; 60-70 s stays hard


LY_CLIPS = (2, 4)                  # L-y 4: 3 to 5 clips = the hook + 2-4 clips, back to back (the medley)
LY_TAKEAWAY_MIN_WORDS = 8          # L-y 5: one or two sentences
LY_TAKEAWAY_MAX_WORDS = HS.TAKEAWAY_MAX_WORDS   # ruling 6 (22:40): at most 20 words for a new takeaway; ruling 10's
                                   # MOMENTS_TAKEAWAY_WORD_CAP (30) stays the factory's upper bound in R4
LY_BRIDGE_WORDS = 12               # L-y 2: the one exceptional bridge, "as short as it can be" (asked of the writer;
                                   # config.BRIDGE_WORD_CAP 20 stays the hard bound, ly_shape)
LY_BRIDGE_MIN_WORDS = 3            # the shortest bridge a first write budgets for ("Next, on keys.")
LY_MAX_BRIDGES = 1                 # L-y 2: at most ONE bridge per video
LY_AIM_S = (61.5, 68.5)            # the takeaway's length aims the factory's estimate here when the clips allow it
                                   # (inside 60-70 s with margin: the voice measured 2.91 w/s vs R4's 2.5, ruling 12)
LY_LINEUPS = 2                     # line-ups tried per angle (a clips-alone failure drops its weak clips once)


def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
    """Seconds the clips may fill so that ONE takeaway of LY_TAKEAWAY_MIN_WORDS..LY_TAKEAWAY_MAX_WORDS words (and
    n_bridges bridges of bridge_words) lands the factory's estimate (runtime()) inside 60-70 s (L-y 4)."""
    extra = n_bridges * (bridge_words / R4_WPS + R4_PREROLL_S)
    lo = RUNTIME_S[0] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MAX_WORDS / R4_WPS + R4_PREROLL_S)
    hi = RUNTIME_S[1] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MIN_WORDS / R4_WPS + R4_PREROLL_S)
    return round(lo, 2), round(hi, 2)


def bridge_budget(content_s):
    """For a line-up that must carry one bridge (L-y 2), before the bridge is written: (n, (lo, hi)), the largest bridge
    limit n <= LY_BRIDGE_WORDS words such that ANY bridge of LY_BRIDGE_MIN_WORDS..n words with a takeaway of lo..hi
    words lands the factory's estimate in 60-70 s (the two budgets overlap), or None when no bridge fits these clips
    (audit 2030 C3: the writer is never handed a range that a legal bridge can push outside 60-70 s)."""
    w = lambda n: [" ".join(["word"] * n)]
    short = takeaway_budget(content_s, w(LY_BRIDGE_MIN_WORDS))
    if short is None:
        return None
    for n in range(LY_BRIDGE_WORDS, LY_BRIDGE_MIN_WORDS - 1, -1):
        long_ = takeaway_budget(content_s, w(n))
        if long_ is not None and max(short[0], long_[0]) <= min(short[1], long_[1]):
            return n, (max(short[0], long_[0]), min(short[1], long_[1]))
    return None


def takeaway_budget(content_s, other=()):
    """(lo, hi) words for the takeaway, given the clips' seconds and the other VO lines' texts (a bridge): the factory's
    estimate (runtime()) inside LY_AIM_S when the clips allow it, else inside 60-70 s; never under
    LY_TAKEAWAY_MIN_WORDS, above house style's cap (20, ruling 6) or past R4's share. None when no length lands 60-70 s."""
    other = [t for t in other if t and t.strip()]
    fixed = content_s + FINAL_TAIL_S + sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in other)
    words_at = lambda s: R4_WPS * (s - fixed - R4_PREROLL_S)     # the takeaway's words that land the estimate at s
    cap = min(LY_TAKEAWAY_MAX_WORDS,
              r4_max_vo_words(content_s, 1 + len(other)) - sum(len(t.split()) for t in other))
    for a, b in (LY_AIM_S, RUNTIME_S):
        lo, hi = max(LY_TAKEAWAY_MIN_WORDS, math.ceil(words_at(a) - 1e-9)), min(cap, math.floor(words_at(b) + 1e-9))
        if lo <= hi:
            return lo, hi
    return None


def r4_max_vo_words(content_s, n_vo):
    """The most VO words (intro + bridges) the moments-first R4 allows: edl_rules' own estimate (words / 2.5 + 1 s per
    VO line) <= R4_MOMENTS_SHARE of the runtime estimate (runtime(): content + that VO + FINAL_TAIL_S)."""
    # VO_s = w / R4_WPS + PRE * n ; runtime = content + VO_s + TAIL ; VO_s <= SHARE * runtime
    vo_max = R4_MOMENTS_SHARE * (content_s + FINAL_TAIL_S) / (1 - R4_MOMENTS_SHARE)
    return max(0, int(R4_WPS * (vo_max - R4_PREROLL_S * n_vo)))


def min_vo_words(content_s, n_vo=2):
    """The fewest VO words (intro + bridges) that land 60 s by the factory's estimate (runtime())."""
    return max(0, int(R4_WPS * (RUNTIME_S[0] - content_s - FINAL_TAIL_S - R4_PREROLL_S * n_vo) + 0.999))


def content_range(n_clips=2):
    """Seconds the segments may fill so that some VO lands the runtime in 60-70 s AND fits R4 (one VO line for the
    intro + one bridge per clip but the last)."""
    n_vo = 1 + (n_clips - 1)
    lo = next(c / 10 for c in range(200, 700) if min_vo_words(c / 10, n_vo) <= r4_max_vo_words(c / 10, n_vo))
    return lo, RUNTIME_S[1] - FINAL_TAIL_S - VO_S[0] - R4_PREROLL_S * n_vo          # runtime()'s own terms


def r4(pk):
    """R4 for a moments-first package, as the orchestrator ordered it at 06:00 (ruling 4; the integrator brings
    edl_rules.rule_r4 to it; the cap is 45 % since ruling 9, 08:29): VO (intro + bridges, edl_rules' estimate 2.5 w/s +
    1 s per line) <= R4_MOMENTS_SHARE of the runtime
    estimate; the word caps of config.py (the takeaway after the LAST clip: MOMENTS_TAKEAWAY_WORD_CAP, ruling 10);
    at most one VO line after each clip (the last clip included).
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
    for i, w in enumerate(words[1:]):          # ruling 10: the line after the LAST clip is the takeaway (cap 30)
        last = i < len(after) and after[i] == n_clips
        cap = MOMENTS_TAKEAWAY_WORD_CAP if last else BRIDGE_WORD_CAP
        if w > cap:
            fails.append(f"{'takeaway' if last else 'bridge'} {i + 1} {w} words (max {cap})")
    if len(set(after)) != len(after) or any(type(a) is not int or not 1 <= a <= n_clips for a in after):
        fails.append(f"bridges after clips {after}: one per clip, 1..{n_clips}")
    if share > R4_MOMENTS_SHARE:
        fails.append(f"VO={share:.1%} of the runtime (max {R4_MOMENTS_SHARE:.0%})")
    note = f"VO {vo_s:.1f} s = {share:.1%} of the {pk['runtime_s_estimate']} s runtime ({share_old:.1%} of clips + VO)"
    return (not fails), ("R4 (moments-first, 06:00) FAIL: " + "; ".join(fails) if fails else
                         "R4 (moments-first, 06:00) PASS") + f" | {note}"


def _name(m, ctx):
    return (ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"]


def signoff(segs, ctx):
    """L-a: the spoken sign-off names exactly the credit set, hook first (code, never the model)."""
    names = list(dict.fromkeys(_name(m, ctx) for m in segs))
    who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + f", and {names[-1]}"
    return f"Clips today from {who}. Go follow them for more. Links are below."


def utc_z(when):
    """An ISO 8601 time with its offset -> "YYYY-MM-DDTHH:MM:SSZ" (UTC), or None when it cannot be read (the pin then
    refuses it: ruling 1, 22:40, recency on the render clock needs the source's publish time)."""
    from datetime import datetime, timezone
    try:
        t = datetime.fromisoformat(str(when).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return None if t.tzinfo is None else t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def labels(n):
    """The segments' labels in play order: the hook, then clip_01 ... (the renderer's clip index = the position)."""
    return ["hook" if i == 0 else f"clip_{i:02d}" for i in range(n)]


def _package(segs, ctx, fields, vo_kind, vo, lines):
    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"] not in ("title", "caption"))
    pk = {"schema": "pp.package/1", "type": fields.get("type", "moments"), "angle": fields.get("angle", ""),
          "vo_kind": vo_kind, "style": fields.get("style"),
          "segments": [{"label": lb, "moment_id": m["moment_id"],
                        **({"source_key": m["source_key"]} if m.get("source_key") else {}),   # a window moment's
                        "video_id": m["video_id"], "channel_id": m["channel_id"], "channel": _name(m, ctx),
                        "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
                        "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
                        "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
                        "time_sensitive": bool(time_sensitive(m)),          # ruling 1 (22:40): L-v 3 on the render
                        "source_published_at": utc_z(m.get("published_at")),  # clock, both sealed in the pin
                        "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s",
                        **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"],
                            "scorer_pending": bool(TRIM_SCORER_PENDING)}   # ruling 49 (a): the clip scorer's verdict
                           if m.get("trimmed_leading") else {})}   # on the trimmed text is pending at the render
                                                                   # (strict: False, which the pin refuses)
                       for lb, m in zip(labels(len(segs)), segs)],
          "vo": dict(vo, signoff=signoff(segs, ctx)),
          "title": fields["title"]["text"], "caption": fields["caption"]["text"],
          "hook_first_words": " ".join(segs[0]["text"].split()[:8]),
          "lines": lines}
    vo_lines = [pk["vo"]["intro"]] + list(pk["vo"]["bridges"])
    pk["runtime_s_estimate"] = runtime(segs, vo_lines)
    pk["runtime_note"] = (f"segments {sum(m['duration_s'] for m in segs):.2f} s (word timing) + VO {vo_words} words at "
                          f"{R4_WPS} w/s + {R4_PREROLL_S} s pre-roll per line + tail {FINAL_TAIL_S} s (sign-off, credits, "
                          f"outro, edges): the factory's own R4 estimate; the render measures the final")
    return pk


def assemble(order, by_id, fields, ctx, vo_kind):
    """The PBX MAX v3 shape (an intro after the hook and a line after clips; the orchestrator's given packages of the
    night of Nov 11-12). L-y's medley is assemble_medley()."""
    segs = [by_id[i] for i in order]
    lines = [dict(fields["intro"], slot="intro")] + \
        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
    vo = {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
          "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1))}      # the renderer's after_clip
    return _package(segs, ctx, fields, vo_kind, vo, lines)


def assemble_medley(order, by_id, fields, ctx, vo_kind):
    """L-y: the clips back to back, ONE takeaway after the last clip (slot "takeaway", the renderer's after_clip = the
    last clip), and at most one bridge: after the hook it is the renderer's intro slot (slot "intro"), after clip k it is
    a bridge after_clip k (slot "bridge_1"). fields: takeaway, bridge (None or {"text", "cites", "why"}), bridge_after
    (None, 0 = after the hook, or k), title, caption."""
    segs = [by_id[i] for i in order]
    n_clips = len(segs) - 1
    b, k, t = fields.get("bridge"), fields.get("bridge_after"), fields.get("takeaway")
    if b is not None and (type(k) is not int or not 0 <= k < n_clips):
        raise ValueError(f"a bridge sits at a join between two clips: after 0..{n_clips - 1}, not {k!r}")
    if t is None and b is not None:
        raise ValueError("a no-voice medley carries no bridge either (ruling 3, 22:40: clips back to back)")
    mid = b is not None and k > 0
    lines = ([dict(b, slot="intro")] if b is not None and k == 0 else []) + \
        ([dict(b, slot="bridge_1")] if mid else []) + \
        ([dict(t, slot="takeaway")] if t is not None else []) + \
        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
    vo = {"intro": b["text"] if b is not None and k == 0 else None,
          "bridges": ([b["text"]] if mid else []) + ([t["text"]] if t is not None else []),
          "bridges_after_clip": ([k] if mid else []) + ([n_clips] if t is not None else [])}
    pk = _package(segs, ctx, fields, vo_kind, vo, lines)
    pk["shape"] = "medley"
    pk["btc_screen"] = {"pattern": E.BTC_SCREEN.pattern, "source": E.BTC_SCREEN_SOURCE}   # ruling 34: sealed (to_pin)
    pk["bridge"] = None if b is None else {"after": pk["segments"][k]["label"], "after_clip": k,
                                           "join": f"{pk['segments'][k]['label']} -> {pk['segments'][k + 1]['label']}",
                                           "text": b["text"], "why": b.get("why"),
                                           "confirmed_by": fields.get("bridge_confirmed_by")}
    pk["supply_exception"] = fields.get("supply_exception")
    pk["no_voice"] = fields.get("no_voice")
    return pk


# ── step A once per moment (orchestrator 05:25 item 5) ──

STEP_A_VERSION = hashlib.sha256(CI.STEP_A.encode()).hexdigest()[:12]


def _load_store(store):
    if not store or not os.path.exists(store):
        return {}
    with open(store) as f:
        return json.load(f)


def src_of(x, sources):
    """A moment's (or a package segment's) own Source: context_integrity.source_for, the one lookup rule."""
    return CI.source_for(x, sources)


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
            text, win = CI._window_text(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"])
            if text is None:        # no L-s context (a window record without its caption record, short coverage, an
                fails[m["moment_id"]] = ["CONTEXT_UNAVAILABLE: no L-s context for this moment (law L-s)"]   # unclocked
                continue            # moment): THIS moment is not cleared; it never poisons its batch's call
            contexts[m["moment_id"]] = {"text": text, "title": src_of(m, sources).title or "",
                                        "channel": _name(m, ctx), "window": win,
                                        "published": str(m.get("published_at") or "")[:16],
                                        "show_date": ctx.now.strftime("%Y-%m-%d")}
        if not contexts:
            continue
        try:
            got, backend = CI.step_a(router, contexts, writer_vendor, seed=7 + i, writer_family=writer_family)
        except Exception as e:                           # unreadable: these moments are not cleared (law L-m)
            for mid in contexts:
                fails[mid] = [f"STEP_A_UNAVAILABLE: {type(e).__name__}"]
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


def second_screen(router, cleared, a_by, sources, ctx, log=print):
    """ORDER 06:22 item 45: step A from a SECOND vendor on every cuttable clip, BEFORE the angle step. The writer is
    known only when the angle call answers (Heimdall first, Grok on its failure: angle_write), and a verdict never
    comes from the writer's vendor (L-x). The only step-A vendors are the writers' own two (context_verdict: xai, then
    heimdall), so each clip is screened again OFF its first verdict's vendor and family: whichever vendor then writes,
    a verdict off it already exists, and no line-up is built on a clip that a re-screen would fail (the 05:48 build).
    The clips are grouped by their first verdict's back-end, and the groups' step-A batches run in parallel (each
    call takes about 3 min on Heimdall). -> ({moment id: [first verdict, second verdict]} for the clips that pass
    both, {moment id: [why not]} for the rest). No second verdict, a failing one, or one from the first's vendor or
    family is never a pass (law L-m)."""
    groups = {}
    for mid, m in cleared.items():
        b = router.backends.get((a_by.get(mid) or {}).get("backend"))
        groups.setdefault((b.vendor, b.family) if b is not None else None, []).append(m)
    jobs = [(k, g[i:i + PRESCREEN_BATCH]) for k, g in groups.items() if k is not None
            for i in range(0, len(g), PRESCREEN_BATCH)]
    def one(k, chunk):                  # a chunk whose screen raises fails closed, never the build (audit 0640 C1)
        try:
            return prescreen(router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log)
        except Exception as e:
            return {}, {m["moment_id"]: [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:120]}"]
                        for m in chunk}, set(), set()
    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as ex:
        res = list(ex.map(lambda j: one(*j), jobs))          # Executor.map keeps the order of jobs: zipped below
    two, fail = {}, {}
    for (k, chunk), (got, fails, _, _) in zip(jobs, res):
        for m in chunk:
            mid, a2 = m["moment_id"], got.get(m["moment_id"])
            b2 = router.backends.get((a2 or {}).get("backend"))
            if fails.get(mid) or a2 is None:
                fail[mid] = list(fails.get(mid) or ["STEP_A_UNAVAILABLE: no second verdict (law L-m)"])
            elif b2 is None or b2.vendor == k[0] or (k[1] and b2.family == k[1]):
                fail[mid] = [f"STEP_A_SAME_VENDOR: the second verdict came from {a2.get('backend')}, not off the "
                             f"first's vendor {k[0]} and family {k[1]} (law L-m)"]
            else:
                two[mid] = [a_by[mid], a2]
    for m in groups.get(None, []):
        fail[m["moment_id"]] = [f"STEP_A_UNKNOWN_BACKEND: the first verdict's back-end "
                                f"{(a_by.get(m['moment_id']) or {}).get('backend')!r} is not in the router, so no "
                                f"second vendor can be chosen (law L-m)"]
    return two, fail


ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words. The clips
play BACK TO BACK as a medley, with NO narration between them; the host speaks ONE closing line at the end. Below are
clips (verbatim quotes, each with its channel, its length and its PLACEMENT LIMITS) that passed our checks. The
channels were not in one conversation and never answer each other.

{note}
{clips}

Find up to {k} ANGLES, best first. An angle is ONE sentence a viewer could repeat: a point that several of these clips
GENUINELY support together (each clip adds a different reason, fact or voice to the same point). Do not make a point
the clips do not state. Do not build an angle on a price level or move as if it were today's news unless a clip says
it is today's.
With no narration the ORDER carries the video: list each angle's clips in the order they should PLAY, so that every
clip's opening makes sense right after the previous clip's ending, in the speakers' own words (no clip may need an
introduction to be understood). The video plays the hook and 2-4 more clips, ONE per channel, from 3-5 DIFFERENT
channels, together {lo:.0f}-{hi:.0f} seconds of clips. PLACEMENT LIMITS: a clip marked "only the hook or the LAST
clip" is the first or the LAST id of an angle's list, never in between; a clip marked "only the LAST clip" is the LAST
id or is not in it; a clip marked "cannot open" is never the hook. Give as many good angles as the clips allow (aim for
{k}); for
each angle give: "angle" (the sentence); "moments": the ids of 4 to 8 clips IN PLAY ORDER, the hook first (more choice
survives a clip that later fails a check), from at least 3 different channels, with enough seconds among them;
"hook": the first id, whose FIRST WORDS grab attention AND set up the angle; "support": for each of those ids, a few
words on what it adds and why it follows the clip before it (an internal note).
Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "id", "id"], "hook": "id",
"support": {{"id": "..."}}}}]}}"""

HOOK_QUESTION = """THE HOOK is judged on its own job, NOT on the through-line. Rate each of its three parts 1-5 separately:
   "scroll": do its first 2-3 seconds stop a viewer from scrolling past? (5 = certainly, 1 = not at all)
   "alone": does it stand alone, so that a viewer needs nothing said before it? (5 = fully, 1 = not at all)
   "setup": does it set up what follows, so that a viewer who hears it wants the next clip? (5 = certainly, 1 = not
   at all)"""                    # ruling 52 + the 09:59 answer: ONE definition of the hook's job, in both verdicts

MEDLEY_PROMPT = """You watch a short video made ONLY of these clips, played back to back with NO narration between them.
Each clip is a person's own words from a show; the shows were not in one conversation. The first clip (label "hook")
opens the video.

{clips}

1) Played back to back with no narration, is there a through-line a viewer can state? State it in ONE sentence, or
   "none" if there is none.
2) """ + HOOK_QUESTION + """
3) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
4) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
   clip's subject or referent clear coming from the previous clip's ending? Answer true or false, and why in a few
   words.
Return ONLY this JSON object: {{"through_line": "...", "hook": {{"scroll": 1, "alone": 1, "setup": 1}},
"clips": {{{clip_keys}}}, "joins": {{{joins}}}}}"""
HOOK_PARTS = ("scroll", "alone", "setup")   # ruling 52 (08:06 Nov 13): the hook's own job, each part rated 1-5
HOOK_RULE = "the lowest of scroll / alone / setup (ruling 52): every part must reach the bar"

WRITE_LY = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
THE ANGLE (the point this video makes): "{angle}"
The clips play BACK TO BACK as a medley, with no narration between them (verbatim, in play order; the channels were not
in one conversation and never answer each other):

{note}
{lineup}

After the last clip you speak ONE closing line, the TAKEAWAY; then a sign-off credits every channel (written by code).
{bridge}Write:
- "takeaway": {lo}-{hi} words in short declarative sentences: the point the medley adds up to, as YOUR OWN
  commentary (your opinion or conclusion), a point and not a summary, never a restatement of any clip.
- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters. Both carry the angle.
Every line gives "cites": the ids of the clips it relies on (none for your own commentary).
RULES (a line that breaks one is rejected):
- NEVER restate a clip's claim, and never repeat its words: the clip says it, in its own words.
- Your OWN commentary is an opinion or a conclusion, nothing else: no checkable fact, number, price, date, named person
  or company; never what a speaker thinks or how speakers relate; no prediction of what will happen; no advice or
  instruction to the viewer (no "you should", "your job", "must"); no accusation; nothing that sounds like a quote.
- Say what a speaker says or thinks ONLY for a clip marked VERIFIED, by that name, with the clip's own hedge: "thinks"
  for "I think", "feels" for "I feel like", "says" only for a flat statement. For any other clip credit the SHOW only
  ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says" or "<name> discusses".
- Never say or imply that channels agree, answer, rebut or react to each other.
- No price level; no advice to buy, sell or use leverage; no quotes except a clip's exact words; no "destroys",
  "slams", "exposes", "admits", "confirms", "caught".
- A line that names a show, a person or Bitcoin's price cites the clips it comes from.
{style}
{extra}Return ONLY this JSON object: {{"takeaway": {{"text": "...", "cites": []}}, "bridge": {bridge_shape},
"title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}}}}"""

BRIDGE_ASK = """ONE JOIN NEEDS HELP: a blind viewer who watched these clips back to back could not follow the jump from
{a} to {b} ("{why}"). Write ONE "bridge", heard between them: as short as it can be (at most {n} words); it only makes
the next clip's subject or referent clear (its show and its topic, or a question); it never says what the next speaker
thinks. Give "why": one sentence on why a viewer could not follow the jump without it. If you judge a viewer CAN
follow this jump without narration, give "bridge": null (these clips then do not sit together, and other clips are
picked).
"""

COHERENCE_PROMPT = """You watch a 60-second video. Here is everything it says and shows, in order (each clip is a
different person's own words; the first clip, label "hook", opens the video).

{package}

1) State the video's through-line in ONE sentence, or "none" if it has none.
2) """ + HOOK_QUESTION + """
3) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
4) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
   1 = no point, or a point the clips do not support).
Return ONLY this JSON object: {{"through_line": "...", "hook": {{"scroll": 1, "alone": 1, "setup": 1}},
"clips": {{{clip_keys}}}, "vo_point": 1}}"""


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


def stand_alone_check(segs):
    """The render's STAND_ALONE (main run_fresh.stage_validate -> stand_alone.check_edl) on one line-up, at the pin stage
    (the integrator held pin d2657bbe on it, 03:00 ET Nov 13): the hook, then the clips in play order (clip_01, ...), the
    subject Bitcoin (run_fresh.stand_alone_subject for a pinned moments package labelled 'bitcoin'), and NO clip scorer.
    The render's scorer is a local model on GPU0, which this stage may not use, so a clip that opens on a conjunction or
    a reply fragment fails closed here, as check_edl does without one: never sealed for the scorer to rescue.
    check_edl's verdict reads only each segment's text, the subject and rate (channel and duration feed only the
    scorer's passages, unused with rate=None; the labels come from the order). The subject is fixed because
    package_pin.to_pin labels every moments pin 'bitcoin' (audit 0310 C1, glm P1-1 / qwen P1-1).
    RULING 34 (the render's side merged at 55315124): the topic test is the miner's about-Bitcoin screen that every
    moments pin seals (eligibility.BTC_SCREEN, moments_package.btc_screen), and the MEDLEY must name Bitcoin in at
    least one segment (out["medley_names_bitcoin"], part of out["ok"]): check_edl(..., screen=...), as the render."""
    import stand_alone as SA
    def seg(m, extra):
        lock = {} if TRIM_SCORER_PENDING or not m.get("trimmed_leading") else \
            {"selection_lock": {"trimmed_leading": {"word": m["trimmed_leading"]}}}    # the render's own marker
        return dict(extra, text=m["text"], channel=m.get("channel_name"), **lock)
    edl = {"hook": seg(segs[0], {}),
           "clips": [seg(m, {"index": i, "duration": m.get("duration_s")}) for i, m in enumerate(segs[1:], 1)]}
    r = SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"), screen=E.BTC_SCREEN)
    r["scorer_pending"] = [lb for lb, m in zip(labels(len(segs)), segs)
                           if m.get("trimmed_leading") and TRIM_SCORER_PENDING]            # ruling 33 (b), item 42
    for row in r["rows"]:              # the sealed row STATES the divergence, not only the labels (audit 0530 C2, glm)
        if row["segment"] in r["scorer_pending"]:
            row["opener"]["why"] += ("; the clip scorer's verdict on the trimmed text is PENDING AT THE RENDER (GPU0; "
                                     "ruling 33 part 2)")
    return r


def ad_read_out(ms, sources):
    """{moment id: why} for the moments the exclusion screen's DETERMINISTIC part refuses (moments.ad_read_marker: an
    ad-read marker in the moment or in the sentence right before it, the same context exclusion_for() reads). The same
    rule refuses them at the package stage; run first, the angles are never built around them. A moment with no
    Source or no context is left to the package stage, which refuses it (fail closed); so is any moment whose fields
    the lookup cannot read (a KeyError). out is a census of the moments that survived no_role_on_screen."""
    import moments as M
    out = {}
    for m in ms:
        try:
            before, _ = CI.context_around(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"])
        except (KeyError, IndexError):                 # no Source, or fields the lookup cannot read: left to the
            continue                                    # package stage (audit 0352 C2, qwen)
        why = M.ad_read_marker(m["text"], before) if before is not None else None
        if why:
            out[m["moment_id"]] = why
    return out


def trim_variant(m, sources):
    """RULING 33 PART 2 (the render merged it at 11e361cc; the orchestrator's 04:58 item 42, "use it now"). A moment
    whose first word is ONE of TRIM_WORDS, left out by the render's STAND_ALONE opener rule, may be cut one word in.
    The variant's text, start and words begin at the next word of its word record (start/end bound the KEPT words),
    and it carries trimmed_leading (the word as spoken) and untrimmed_start (the trimmed word's start). It must take a
    place under the render's STAND_ALONE as trimmed (no_role_on_screen and no_topic both None on the trimmed text).
    Then it is judged like any moment: step A on the trimmed span (ruling 33 c), L-v 2 with the trimmed word heard right
    before the clip (transcript_truth.edges), and the acoustic onset rule on the trimmed cut (ruling 33 a, build()).
    The clip scorer's verdict (ruling 33 b) is the render's, on GPU0: pending at the render (stand_alone_check). -> the
    variant, or None."""
    import canon
    try:
        src = src_of(m, sources)
        w0, w1 = m["words"]
        toks = src.tokens
        word, nxt = toks[w0].get("word") or "", toks[w0 + 1]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    tok = canon.canon_tokens(word)                 # exactly ONE canonical token, as the render's validate_schema
    if w1 <= w0 or len(tok) != 1 or tok[0] not in TRIM_WORDS:          # ("and/or" is two: the integrator, 07:19)
        return None
    if len(canon.canon_tokens(E.spoken(toks[w0 + 1:w1 + 1]))) < E.MIN_STATEMENT_TOKENS:
        return None                          # the kept words still make a statement (audit 0530 C1, glm P0-2)
    a = nxt.get("start")
    if not isinstance(a, (int, float)) or isinstance(a, bool) or not float(m["start"]) <= float(a) < float(m["end"]):
        return None
    v = dict(m, moment_id=f"{m['moment_id']}~trim", text=E.spoken(toks[w0 + 1:w1 + 1]), start=float(a),
             duration_s=round(float(m["end"]) - float(a), 2), words=[w0 + 1, w1],
             trimmed_leading=word.strip().strip(".,!?;:\"'()\u201c\u201d\u2014\u2026"),
             untrimmed_start=float(m["start"]), trimmed_from=m["moment_id"])
    if no_role_on_screen(v) or no_topic(v):
        return None
    return v


REPOST_ALIGN_MIN = 0.80          # ruling 53: the share of the shorter moment's words that are TIME-aligned
REPOST_TIME_TOL_S = 0.30         # a re-post is the same audio: its matched words keep their spacing within this


def _timed_words(m, sources):
    """[(the word's canonical form, its start s)] for a moment's own words, from its word record; None without one."""
    import canon
    try:
        toks = src_of(m, sources).tokens
        w0, w1 = m["words"]
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        return None
    out = []
    for t in toks[w0:w1 + 1]:
        key, st = " ".join(canon.canon_tokens(t.get("word") or "")), t.get("start")
        if key and isinstance(st, (int, float)) and not isinstance(st, bool):
            out.append((key, float(st)))
    return out or None


def _time_aligned(ta, tb):
    """How many words of two timed word lists match IN ORDER (difflib's matching blocks) AND keep one clock offset:
    each matched pair's start-time difference lies within REPOST_TIME_TOL_S of the median difference. Two uploads of
    one audio share the spacing of every word; two speakers saying similar words do not."""
    import difflib
    import statistics
    sm = difflib.SequenceMatcher(None, [w for w, _ in ta], [w for w, _ in tb], autojunk=False)
    pairs = [(ta[x.a + k][1], tb[x.b + k][1]) for x in sm.get_matching_blocks() for k in range(x.size)]
    if not pairs:
        return 0
    off = statistics.median(y - x for x, y in pairs)
    return sum(abs((y - x) - off) <= REPOST_TIME_TOL_S for x, y in pairs)


def reposted_once(ms, sources):
    """RULING 53 (08:06 Nov 13): the same speech re-posted by a SECOND channel is ONE moment. Two moments on different
    channels are the same speech when their texts are equal after normalisation (canon.canon_tokens, the one normal
    form), or when at least REPOST_ALIGN_MIN of the shorter one's words are TIME-ALIGNED: the same words in order, at
    one clock offset (each within REPOST_TIME_TOL_S; _time_aligned); the 80 % counts the words that HAVE timings
    (a word with no start or no canonical form cannot be aligned). ONE offset per pair: a copy spliced with words
    inserted mid-speech sits at two offsets and is not merged by timing (audit 0816 C2, glm P1-1). One offset per
    matched block instead would merge two speakers saying near-identical words (qwen's C1 example passes per block
    at 0.3 s), and a spliced copy still falls to the package's duplicate check. Without a word record with timings
    only equal text merges, so two moments are never merged on a guess. Of each such group the ORIGINAL publisher's moment is kept:
    the earliest published_at (a time with no zone is read as UTC, the pipeline's own; an unreadable one is never
    preferred; a tie goes to the lower moment id). Only it plays, so its channel is the one credited.
    -> (the moments kept, in their order, {copy's moment id: why})."""
    import collections
    from datetime import datetime, timezone
    import canon
    text = {m["moment_id"]: canon.canon_tokens(m.get("text") or "") for m in ms}
    timed = {m["moment_id"]: _timed_words(m, sources) for m in ms}

    def at(m):                                    # the earliest readable publish time first; none is never first
        try:
            t = datetime.fromisoformat(str(m.get("published_at") or "").replace("Z", "+00:00"))
        except ValueError:
            return (1, 0.0, m["moment_id"])
        t = t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        return (0, t.astimezone(timezone.utc).timestamp(), m["moment_id"])

    def same(a, b):
        if text[a["moment_id"]] and text[a["moment_id"]] == text[b["moment_id"]]:
            return "equal text after normalisation"
        ta, tb = timed[a["moment_id"]], timed[b["moment_id"]]
        if not ta or not tb:
            return None                           # no timings: only equal text merges
        short = min(len(ta), len(tb))
        shared = collections.Counter(w for w, _ in ta) & collections.Counter(w for w, _ in tb)
        if sum(shared.values()) < REPOST_ALIGN_MIN * short:     # shared words >= words in matched blocks >= the
            return None                           # time-aligned ones: below 80 % here, below 80 % there (C2, glm P2-1)
        hit = _time_aligned(ta, tb)
        return (f"{hit} of the shorter's {short} words time-aligned (the same words in order, one clock offset within "
                f"{REPOST_TIME_TOL_S:.1f} s)") if hit >= REPOST_ALIGN_MIN * short else None
    parent = {m["moment_id"]: m["moment_id"] for m in ms}

    def root_of(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    how = {}
    for i, a in enumerate(ms):
        for b in ms[i + 1:]:
            if a["channel_id"] == b["channel_id"]:
                continue                                  # the rule is about a SECOND channel
            w = same(a, b)
            if w:
                ra, rb = root_of(a["moment_id"]), root_of(b["moment_id"])
                if ra != rb:
                    parent[rb] = ra
                how[(a["moment_id"], b["moment_id"])] = how[(b["moment_id"], a["moment_id"])] = w
    groups = {}
    for m in ms:
        groups.setdefault(root_of(m["moment_id"]), []).append(m)
    kept_of = {r: min(g, key=at)["moment_id"] for r, g in groups.items()}     # each group's original, once
    by = {m["moment_id"]: m for m in ms}
    out, dup = [], {}
    for m in ms:
        mid = m["moment_id"]
        k = kept_of[root_of(mid)]
        if k == mid:
            out.append(m)
            continue
        o = by[k]
        dup[mid] = (f"the same speech as {k} ({o.get('channel_name') or o['channel_id']}, published "
                    f"{o.get('published_at')}), re-posted by a second channel "
                    f"({m.get('channel_name') or m['channel_id']}, published {m.get('published_at')}): "
                    f"{how.get((k, mid)) or 'matched through another copy'} (ruling 53: the original publisher's is "
                    f"kept and credited)")
    return out, dup


def no_topic(m):
    """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
    fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
    names Bitcoin (stand_alone.topical_screen as a clip: its most favourable place). build() leaves it out before any
    vendor call."""
    import stand_alone as SA
    ok, why = SA.topical_screen("clip", m["text"], "Bitcoin", E.BTC_SCREEN)
    return None if ok else f"the render's STAND_ALONE topic rule with the pin's screen (ruling 34): {why}"


def no_role_on_screen(m):
    """Why a moment can take NO place in a line-up under the render's STAND_ALONE opener rule with no clip scorer (it
    opens on a conjunction or a reply fragment: the clip role fails closed without the scorer, the hook role fails on
    it), else None. build() leaves such moments out before any vendor call."""
    import stand_alone as SA
    c_ok, c_why = SA.opener("clip", m["text"])          # a moment without text fails fast (audit 0310 C2, qwen)
    h_ok, h_why = SA.opener("hook", m["text"])
    return None if (c_ok or h_ok) else f"the render's STAND_ALONE with no clip scorer at the pin stage: {c_why}; {h_why}"


def lineup_ok(segs, crange=None, repeat_ok=False):
    """The rules lineup_for applies, checked on a GIVEN line-up in play order -> (ok, why): the hook can open (hook
    eligibility and the G17a measure), every clip is clip-eligible, the hook + LY_CLIPS clips, one segment per channel
    (or, repeat_ok, one channel with two clips from two videos: L-y 4), at most PRICE_PREDICTIONS_MAX price predictions,
    a clip under SHORT_CLIP_S only last, the seconds inside crange, and the render's STAND_ALONE (stand_alone_check)."""
    lo, hi = crange or medley_content_range()
    h, clips = segs[0], segs[1:]
    if not LY_CLIPS[0] <= len(clips) <= LY_CLIPS[1]:
        return False, f"{len(clips)} clips"
    if not ((h.get("eligibility") or {}).get("hook", {}).get("ok") and (h.get("hook_onset") or {}).get("pass") is True):
        return False, "the hook cannot open"
    if not all((m.get("eligibility") or {}).get("clip", {}).get("ok") for m in clips):
        return False, "a clip is not clip-eligible"
    chans = [m["channel_id"] for m in segs]
    if len(set(chans)) != len(segs) and not (repeat_ok and len(set(chans)) == len(segs) - 1 and
                                             len({m["video_id"] for m in segs}) == len(segs)):
        return False, "one segment per channel"
    if sum("price_prediction" in m.get("risk", []) for m in segs) > PRICE_PREDICTIONS_MAX:
        return False, "price predictions"
    if sum(bool(m.get("trimmed_leading")) for m in segs) > TRIMMED_PER_LINEUP_MAX:
        return False, f"more than {TRIMMED_PER_LINEUP_MAX} trimmed clip (ruling 49 b)"
    if any(m["duration_s"] < SHORT_CLIP_S for m in clips[:-1]):
        return False, "a short clip that is not last"
    dur = sum(m["duration_s"] for m in segs)
    if not lo <= dur <= hi:
        return False, f"{dur:.1f} s outside {lo}-{hi} s"
    if not stand_alone_check(segs)["ok"]:
        return False, "the render's STAND_ALONE"
    return True, "ok"


def swap_lineup(segs, weak, pool, avoid=frozenset(), crange=None):
    """RULING 41: the next line-up after a clips-alone failure. Every segment in `weak` (moment ids rated below the
    bar) is swapped AT ITS PLACE for the next candidate by score from the whole cleared pool: the hook for the next hook
    by its first 2 s (scores.hook_first_2s), a clip for the next clip by rank_score. The segments rated 4-5 stay where
    they are. The first combination (up to SWAP_TOP candidates per place, in score order) that passes lineup_ok wins,
    one clip per channel first, then L-y 4's supply exception. -> (segs, {old id: new id}) or (None, None)."""
    used = {m["moment_id"] for m in segs}
    places = [i for i, m in enumerate(segs) if m["moment_id"] in weak]
    if not places:
        return None, None
    free = [m for m in pool.values() if m["moment_id"] not in used and m["moment_id"] not in avoid]

    def cands(i):
        if i == 0:
            c = [m for m in free if (m.get("eligibility") or {}).get("hook", {}).get("ok")
                 and (m.get("hook_onset") or {}).get("pass") is True]
            c.sort(key=lambda m: (-m["scores"]["hook_first_2s"], -m["rank_score"], m["moment_id"]))
        else:
            c = [m for m in free if (m.get("eligibility") or {}).get("clip", {}).get("ok")
                 and (i == len(segs) - 1 or m["duration_s"] >= SHORT_CLIP_S)]     # the place's own rule first
            c.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
        return c[:SWAP_TOP]
    options = [cands(i) for i in places]
    for repeat_ok in (False, True):
        for combo in itertools.product(*options):
            if len({m["moment_id"] for m in combo}) != len(combo):
                continue
            new = list(segs)
            for i, m in zip(places, combo):
                new[i] = m
            if lineup_ok(new, crange, repeat_ok)[0]:
                return new, {segs[i]["moment_id"]: m["moment_id"] for i, m in zip(places, combo)}
    return None, None


def placement(m):
    """RULING 54: a clip's placement limits as the angle proposer is told them, exactly lineup_for's rules. Without hook
    eligibility and a passed hook onset (G17a) it cannot open. Under SHORT_CLIP_S it may not play mid-line-up: the
    short-clip rule binds the clips AFTER the hook only, so a short clip that can open may be the hook or the LAST clip,
    and one that cannot open only the LAST (the 08:46 build: a 7.26 s opener was the only formable hook)."""
    opens = bool((m.get("eligibility") or {}).get("hook", {}).get("ok")) and \
        (m.get("hook_onset") or {}).get("pass") is True
    if m["duration_s"] < SHORT_CLIP_S:
        return f" | under {SHORT_CLIP_S:.0f} s: " + ("only the hook or the LAST clip" if opens else "only the LAST clip")
    return "" if opens else " | cannot open (never the hook)"


def pool_fill(angle, pool, dropped=frozenset()):
    """PROPOSAL 1: an angle whose own moments form no line-up (lineup_for, one clip per channel, then L-y 4's
    exception) is completed from the WHOLE cleared pool, as ruling 41's swap fills a place: the pool's other moments
    are appended to the angle's after its own, best by rank_score, and lineup_for runs again under every unchanged
    rule. Its preference (the proposer's earliest moments first) keeps as many of the angle's own as fit, and the added
    clips play after them. The pool adds at most SWAP_TOP candidates (the best by score, as ruling 41's swap reads
    them), and a filled line-up keeps at least HALF of its segments from the angle's own moments: the pool completes
    the angle's missing places, it never replaces the angle (audit 0830 C1, glm P1-4 / P1-5). "First line-up only"
    is the CALLER's rule (build() calls it only while the angle has judged no line-up).
    -> (segs, [the added moment ids]) or (None, None)."""
    own = [mid for mid in angle["moments"] if mid in pool]
    rest = [m["moment_id"] for m in sorted(pool.values(), key=lambda m: (-m["rank_score"], m["moment_id"]))
            if m["moment_id"] not in own and m["moment_id"] not in dropped][:SWAP_TOP]
    if not rest:
        return None, None
    ext = dict(angle, moments=own + rest)
    mine = set(own)
    half = lambda segs: 2 * sum(m["moment_id"] in mine for m in segs) >= len(segs)   # the angle's own: >= half
    for repeat_ok in (False, True):
        segs = lineup_for(ext, pool, dropped, repeat_ok=repeat_ok, need_onset=True, need_stand_alone=True, accept=half)
        if segs is not None:
            return segs, [m["moment_id"] for m in segs if m["moment_id"] not in mine]
    return None, None


def supply_exception(segs, ctx):
    """L-y 4: the reason a line-up takes two clips from one channel (two videos), else None."""
    rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs) if sum(m["channel_id"] == c for m in segs) > 1]
    if not rep:
        return None
    return (f"one clip per channel cannot fill the medley's seconds from this angle's moments: "
            f"{', '.join(_name(next(m for m in segs if m['channel_id'] == c), ctx) for c in rep)}"
            f" gives two clips, from two videos (L-y 4)")


def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False,
               need_stand_alone=False, accept=None):
    """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
    medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
    angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
    predictions (L-u), a clip under SHORT_CLIP_S only as the last (the punchline), and the clips' seconds inside crange
    (default medley_content_range(): one takeaway lands the factory's estimate in 60-70 s). Best = the proposer's
    earliest moments (the lowest sum of play positions, so the default hook -> clip -> clip when it fits), then the
    seconds nearest the middle of crange. repeat_ok (L-y 4, only when one clip per channel cannot fill the runtime):
    ONE channel may give two clips, from two different videos. need_onset (build() sets it): a moment opens the
    medley only if its hook onset was measured and passed (hook_onset_for, G17a at the pin stage); the proposer's hook
    gives way to the angle's next one that did. need_stand_alone (build() sets it): every line-up must pass the render's
    STAND_ALONE (stand_alone_check). None if impossible."""
    lo, hi = crange or medley_content_range()
    pos = {m: i for i, m in enumerate(angle["moments"])}
    ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
    hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok") and
             (not need_onset or (m.get("hook_onset") or {}).get("pass") is True)]
    hooks.sort(key=lambda m: (m["moment_id"] != angle["hook"], -m["scores"]["hook_first_2s"]))
    for h in hooks:
        pool = [m for m in ms if m is not h and (m.get("eligibility") or {}).get("clip", {}).get("ok")
                and (repeat_ok or m["channel_id"] != h["channel_id"])]
        best = None
        for n in range(clips[0], clips[1] + 1):
            for combo in itertools.combinations(pool, n):
                chans = [m["channel_id"] for m in (h, *combo)]
                if len(set(chans)) != n + 1 and not (repeat_ok and len(set(chans)) == n and
                                                     len({m["video_id"] for m in (h, *combo)}) == n + 1):
                    continue
                if sum("price_prediction" in m.get("risk", []) for m in (h, *combo)) > PRICE_PREDICTIONS_MAX:
                    continue
                if sum(bool(m.get("trimmed_leading")) for m in (h, *combo)) > TRIMMED_PER_LINEUP_MAX:   # ruling 49 b
                    continue
                order = sorted(combo, key=lambda m: pos[m["moment_id"]])
                if [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]:
                    continue
                dur = h["duration_s"] + sum(m["duration_s"] for m in order)
                if not lo <= dur <= hi:
                    continue
                if accept is not None and not accept([h] + order):       # the caller's own condition (pool_fill)
                    continue
                if need_stand_alone and not stand_alone_check([h] + order)["ok"]:
                    continue
                key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
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
    (ok, verdict). A through-line that reads 'None.', 'no through-line', 'n/a' or is under 4 words is none (M7).
    Ruling 52, as the orchestrator answered at 09:59 Nov 13: the HOOK is rated on its own job here too (HOOK_QUESTION,
    the same three parts as the clips-alone verdict), and its rating is DERIVED as the lowest part (HOOK_RULE), written
    to verdict["clips"]["hook"]; the clips after the hook and vo_point are rated as before."""
    import providers as P
    r = None
    labs = [sg["label"] for sg in pk["segments"]]
    try:
        r = router.call("coherence_verdict", COHERENCE_PROMPT.format(
                            package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])),
                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
        v = json.loads(r.text.strip())
        if not isinstance(v, dict) or set(v) != {"through_line", "hook", "clips", "vo_point"} or \
                not isinstance(v["hook"], dict) or set(v["hook"]) != set(HOOK_PARTS) or \
                any(type(x) is not int or not 1 <= x <= 5 for x in v["hook"].values()) or \
                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
                any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
            raise ValueError("coherence verdict out of contract")
    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
        if r is not None and isinstance(e, (ValueError, TypeError)):
            router.reject(r)
        return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False}
    v = dict(v, clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}, hook_rule=HOOK_RULE)
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


def joins(labs):
    """The joins of a medley in play order: "<label> -> <next label>"; join k follows segment k (k = 0 is the hook)."""
    return [f"{a} -> {b}" for a, b in zip(labs, labs[1:])]


def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
    """L-y 3: the blind coherence verdict on the clips ALONE (no VO, no title), asked FIRST: "played back to back with
    no narration, is there a through-line a viewer can state?", a 1-5 rating per clip after the hook on how much it
    advances it, and per join whether a viewer can follow the jump. RULING 52: the HOOK is rated on its own job, in
    three parts the judge answers separately (HOOK_PARTS: stops a scroll in its first 2-3 s, stands alone, sets up
    what follows), and its rating is DERIVED, never free-form: the lowest part (HOOK_RULE), written to
    verdict["clips"]["hook"]; the parts stay in verdict["hook"]. Never the vendor / family of the writer. -> (ok,
    verdict): ok when the through-line is stated (>= 4 words, not 'none'), every rating (the hook's derived one
    included) is >= COHERENCE_MIN and at most LY_MAX_BRIDGES joins are not followable; verdict["flagged"] = the joins
    a viewer could not follow (a bridge may go only there, L-y 2)."""
    import providers as P
    labs = labels(len(segs))
    js = joins(labs)
    clips = "\n".join(f'CLIP label="{lb}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
                      for lb, m in zip(labs, segs))
    r = None
    try:
        r = router.call("coherence_verdict",
                        MEDLEY_PROMPT.format(clips=clips, clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:]),
                                             joins=", ".join(f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
        v = json.loads(r.text.strip())
        if not isinstance(v, dict) or set(v) != {"through_line", "hook", "clips", "joins"} or \
                not isinstance(v["hook"], dict) or set(v["hook"]) != set(HOOK_PARTS) or \
                any(type(x) is not int or not 1 <= x <= 5 for x in v["hook"].values()) or \
                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
                any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()) or \
                not isinstance(v["joins"], dict) or set(v["joins"]) != set(js) or \
                any(not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
                    or not isinstance(x["why"], str) for x in v["joins"].values()):
            raise ValueError("clips-alone verdict out of contract")
    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
        if r is not None and isinstance(e, (ValueError, TypeError)):
            router.reject(r)
        return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False, "flagged": None}
    v = dict(v, clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}, hook_rule=HOOK_RULE)
    tl = v["through_line"] if isinstance(v["through_line"], str) else ""
    flagged = [j for j in js if v["joins"][j]["followable"] is False]
    ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
        min(v["clips"].values()) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES
    return ok, dict(v, flagged=flagged, backend=r.backend, measured=True,
                    replayed=bool(getattr(r, "replayed", False)))


class NoBridgeFits(ValueError):
    """These clips leave no takeaway length (and, for a flagged join, no bridge length) that lands 60-70 s."""


def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
    """L-y: ONE takeaway (host commentary, class D), ONE title, ONE caption, and a bridge ONLY at `join` (k, why), the
    one join the clips-alone verdict flagged (L-y 2): the writer gives it with its reason, or null when it judges a
    viewer can follow the jump. The takeaway's word budget lands the factory's estimate (takeaway_budget()) with the
    other VO lines' texts `other` (a bridge already written; when a bridge is asked for and none is written yet, the
    budget and the bridge limit come from bridge_budget(): any bridge the writer may write lands). Raises NoBridgeFits,
    before any model call, when no length lands 60-70 s. -> (reply, fields) with fields["bridge_after"] = k when a
    bridge is given."""
    from select_by_id import UNTRUSTED
    from story_semantics import quote_data
    content = sum(m["duration_s"] for m in segs)
    budget, n_bridge = takeaway_budget(content, other), LY_BRIDGE_WORDS
    if join is not None and not other:                # until the bridge is written, a budget that holds for ANY bridge
        bb = bridge_budget(content)                     # of 3..n words (audit 2030 C1 glm; C2 qwen, grok; C3 glm, qwen)
        if bb is None:
            raise NoBridgeFits(f"no bridge of {LY_BRIDGE_MIN_WORDS}-{LY_BRIDGE_WORDS} words and takeaway land 60-70 s "
                               f"with {content:.1f} s of clips")
        n_bridge, budget = bb
    if budget is None:
        raise NoBridgeFits(f"no takeaway length lands 60-70 s with {content:.1f} s of clips and the lines {list(other)}")
    labs = labels(len(segs))
    ask, shape = "", "null"
    if join is not None:
        k, why = join
        ask = BRIDGE_ASK.format(a=labs[k].upper().replace("_", " "), b=labs[k + 1].upper().replace("_", " "),
                                why=" ".join(quote_data(why, 300).replace('"', "'").split()), n=n_bridge)
        shape = '{"text": "...", "cites": ["id"], "why": "..."} or null'
    angle_text = " ".join(quote_data(angle["angle"], 300).replace('"', "'").split())     # M9: escaped, one line
    prompt = WRITE_LY.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
                             lineup=_lineup_block(segs, ctx, a_by), bridge=ask, lo=budget[0], hi=budget[1],
                             extra=(extra + "\n") if extra else "", bridge_shape=shape, style=HS.PROMPT_RULES)
    r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor, deadline_s=WRITER_DEADLINE_S)
    try:
        obj = json.loads(r.text.strip())
        ids = [m["moment_id"] for m in segs]
        keys = {"takeaway", "bridge", "title", "caption"}
        if not isinstance(obj, dict) or set(obj) != keys:
            raise ValueError(f"keys must be exactly {sorted(keys)}")
        lines = [("takeaway", obj["takeaway"], {"text", "cites"}), ("title", obj["title"], {"text", "cites"}),
                 ("caption", obj["caption"], {"text", "cites"})]
        if obj["bridge"] is not None:
            if join is None:
                raise ValueError("no join needs a bridge: 'bridge' must be null (L-y 1)")
            lines.append(("bridge", obj["bridge"], {"text", "cites", "why"}))
        for slot, ln, want in lines:
            if not isinstance(ln, dict) or set(ln) != want or not isinstance(ln["text"], str) or \
                    not ln["text"].strip() or not isinstance(ln["cites"], list) or \
                    any(not isinstance(c, str) or c not in ids for c in ln["cites"]) or \
                    ("why" in want and (not isinstance(ln["why"], str) or not ln["why"].strip())):
                raise ValueError(f"{slot}: needs text and cites from the line-up's ids" +
                                 (" and a reason" if "why" in want else ""))
        if len(obj["title"]["text"]) > 70 or len(obj["caption"]["text"]) > 220:
            raise ValueError("title <= 70 characters, caption <= 220")
    except (ValueError, TypeError):
        router.reject(r)
        raise
    return r, dict(obj, bridge_after=join[0] if join is not None and obj["bridge"] is not None else None,
                   type="moments", angle=angle["angle"], style="medley", takeaway_budget=list(budget))


def question_hook(segs):
    """Ruling 37: the hook ends on a question (its text ends with '?', the render's R1 test). Such a hook is allowed; the
    clips-alone verdict must find the join after it followable, since no bridge may follow a question."""
    return bool(segs) and str(segs[0].get("text") or "").rstrip().endswith("?")


def ly_shape(pk):
    """L-y (orchestrator 20:30), checked by code on the package -> (ok, [why]): 3-5 segments; ONE takeaway, after the
    last clip; at most LY_MAX_BRIDGES bridge(s), each at a join the clips-alone verdict flagged (pk["medley"], measured)
    with its reason recorded, and every flagged join bridged (else these clips do not sit together); a bridge within
    config.BRIDGE_WORD_CAP words; one clip per channel unless pk["supply_exception"] says why not (L-y 4)."""
    from config import BRIDGE_WORD_CAP
    segs, vo = pk["segments"], pk["vo"]
    n_clips = len(segs) - 1
    fails = []
    if not LY_CLIPS[0] <= n_clips <= LY_CLIPS[1]:
        fails.append(f"{len(segs)} segments: a medley plays 3-5 (the hook + {LY_CLIPS[0]}-{LY_CLIPS[1]} clips)")
    bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
    nv = pk.get("no_voice")
    if nv is not None:                        # ruling 3 (22:40): clips back to back and the sign-off, NO VO line at all,
        if not isinstance(nv, dict) or not str(nv.get("why") or "").strip():   # only after the takeaway failed twice
            fails.append("a no-voice medley must record why (ruling 3: the takeaway failed its gates twice)")
        if bridges or after or vo.get("intro"):
            fails.append("a no-voice medley carries no VO line (ruling 3)")
    elif not bridges or len(after) != len(bridges) or after[-1] != n_clips or not (bridges[-1] or "").strip():
        fails.append("no takeaway after the last clip (L-y 1)")
    js = joins([sg["label"] for sg in segs])
    bad = [a for a in after[:-1] if type(a) is not int or not 0 < a < n_clips]
    if bad:                                    # audit 2030 C4 (glm P1 (a), grok P2): named, never only a count mismatch
        fails.append(f"after_clip {bad}: a bridge between clips sits after clip 1..{n_clips - 1} (after the hook it is "
                     f"the intro)")
    bridged = ([js[0]] if vo.get("intro") else []) + [js[a] for a in after[:-1] if type(a) is int and 0 < a < n_clips]
    texts = ([vo["intro"]] if vo.get("intro") else []) + bridges[:-1]
    if len(bridged) != len(texts) and not bad:
        fails.append(f"a line after clips {after[:-1]} that is not at a join between two clips")
    if len(texts) > LY_MAX_BRIDGES:
        fails.append(f"{len(texts)} bridges (L-y 2: at most {LY_MAX_BRIDGES})")
    med = pk.get("medley") or {}
    if med.get("measured") is not True or not isinstance(med.get("flagged"), list):
        fails.append("the clips-alone verdict was not measured (L-y 3)")
    elif question_hook(segs) and js and js[0] in med["flagged"]:
        fails.append(f"ruling 37: a hook ending on a question takes no bridge after it, so {js[0]} must be followable "
                     f"(the render's R1 reads the sealed clips-alone verdict)")
    elif sorted(bridged) != sorted(med["flagged"]):
        fails.append(f"bridges at {bridged or 'no join'}, the clips-alone verdict flagged {med['flagged'] or 'no join'}"
                     f": a bridge goes only, and always, where a viewer could not follow the jump (L-y 2)")
    rec = pk.get("bridge") or {}
    if texts and not (rec.get("why") or "").strip():
        fails.append("the bridge's reason is not recorded (L-y 2)")
    if texts and (not isinstance(rec.get("text"), str) or rec["text"].strip() != texts[0].strip()):
        fails.append("the bridge record's text is not the bridge line (the factory's R11 binds them)")
    cb = rec.get("confirmed_by")
    if texts and not ((isinstance(cb, str) and cb.strip()) or (isinstance(cb, (list, dict)) and cb)):
        fails.append("the bridge's confirmation by the clips-alone verdict is not recorded (L-y 2, R11)")
    if not texts and pk.get("bridge"):
        fails.append("a bridge record with no bridge line")
    for t in texts:
        if len(t.split()) > BRIDGE_WORD_CAP:
            fails.append(f"bridge of {len(t.split())} words (max {BRIDGE_WORD_CAP})")
    chans = [sg["channel_id"] for sg in segs]
    if len(set(chans)) != len(chans) and not (pk.get("supply_exception") or "").strip():
        fails.append("two clips from one channel without the supply exception recorded (L-y 4)")
    return not fails, fails


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
    runtime, R4, and for a medley the L-y shape. -> (violations, det, dup, rt_ok, r4_res)."""
    segs_v = fidelity_segments(pk, a_by)
    lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
    det = VF.check_deterministic(segs_v, lines, man, levels)
    dup = duplicates(pk)
    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
    r4_res = r4(pk)
    what = "the takeaway's" if pk.get("shape") == "medley" else "the VO's"
    v = det["violations"] + dup + ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail":
                                                      f"{pk['runtime_s_estimate']} s outside 60-70 s: change {what} "
                                                      f"length"}]) + \
        ([] if r4_res[0] else [{"slot": "-", "rule": "R4", "detail": r4_res[1]}])
    if pk.get("shape") == "medley":
        v += [{"slot": "-", "rule": "LY_SHAPE", "detail": why} for why in ly_shape(pk)[1]]
        v += HS.lint_lines(pk["lines"])                    # ruling 6 (22:40): PBX's copy rules, deterministic
        import package_pin                                 # ruling 1: the pin's recency facts, before any paid verdict
        v += [{"slot": "-", "rule": "RECENCY", "detail": why} for why in package_pin.recency_problems(pk["segments"])]
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


def exclusion_for(router, m, sources, cache, seed=7):
    key = m["moment_id"] if seed == 7 else (m["moment_id"], seed)
    if key not in cache:
        import moments as M
        src = src_of(m, sources)
        before, after = CI.context_around(src, m["sentences"][0], m["sentences"][1], *m["words"])
        if before is None:                                    # no context to judge in (a window record without its
            cache[key] = {"verdict": "exclude", "why": "no context: the moment's context is unavailable",   # caption
                          "risks": [], "backend": None, "measured": False, "replayed": False}            # record)
        else:
            cache[key] = M.exclusion_verdict(router, m["text"], before, after, seed=seed,
                                             avoid_model=(m.get("mined") or {}).get("by"))
    return cache[key]


MAJORITY_SEEDS = (7, 8, 9)


def once_then_majority(run, ok, seeds=MAJORITY_SEEDS):
    """Orchestrator 08:18 item 4 / 08:29: a model-judged verdict that is not PASS on its first run gets the three-run
    majority (07:42 item 3) ONCE; whole gate sets are never rerun. run(seed) -> a result; ok(result) -> True only for a
    MEASURED pass. -> (passed, results, votes): the first result alone when it passes, else all three and a pass only
    when more than half of them pass (an unmeasured run is a "fail" vote, law L-m)."""
    first = run(seeds[0])
    if ok(first):
        return True, [first], ["pass"]
    res = [first] + [run(sd) for sd in seeds[1:]]
    votes = ["pass" if ok(x) else "fail" for x in res]
    return 2 * votes.count("pass") > len(res), res, votes


def with_votes(results, votes, passed, seeds=MAJORITY_SEEDS):
    """The record a gate reads after once_then_majority: the first PASSING run when the majority passed (else the first
    run), with "majority" = {"votes", "seeds", "runs": every result} and a replayed tri-state over ALL runs (C2 K4)."""
    rep = next((x for x, v in zip(results, votes) if v == "pass"), results[0]) if passed else results[0]
    out = dict(rep)
    if len(results) > 1:
        reps = [x.get("replayed") for x in results]
        out["majority"] = {"votes": votes, "seeds": list(seeds[:len(results)]), "runs": results}
        out["replayed"] = None if any(not isinstance(x, bool) for x in reps) else any(reps)
    return out


def truth_for(router, m, work_dir, cache):
    if m["moment_id"] not in cache:
        import transcript_truth as TT
        try:
            cache[m["moment_id"]] = TT.verify_segment(router, m["video_id"], float(m["start"]), float(m["end"]),
                                                      m["text"], work_dir, trimmed=m.get("trimmed_leading"))
        except Exception as e:                         # not measured: never a pass (law L-m)
            cache[m["moment_id"]] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
    return cache[m["moment_id"]]


def hook_onset_for(m, sources, work_dir, cache):
    """G17a at the pin stage (hook_onset.measure): may this moment OPEN a medley? Its cut planned on the source audio
    (the L-v 2 window) with the render's own edge_plan, and >= 80 ms of genuine quiet before its first onset by the
    render's own head_tail. Any failure to measure is recorded and never a pass (law L-m)."""
    if m["moment_id"] not in cache:
        import hook_onset as HO
        try:
            cache[m["moment_id"]] = HO.measure(src_of(m, sources), m["words"][0], m["words"][1], m["video_id"],
                                               float(m["start"]), float(m["end"]), work_dir,
                                               trimmed=m.get("trimmed_leading"))     # ruling 33 part 2 (item 42)
        except Exception as e:
            cache[m["moment_id"]] = {"pass": False, "measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
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
    """The writer's second try: exactly the failing lines, by the keys the writer returns ("bridge" for the one bridge,
    whichever join it sits at)."""
    key = {"intro": "bridge", "bridge_1": "bridge"}
    return ("Your previous reply was REJECTED. Return the WHOLE JSON object again, every key; rewrite ONLY the lines "
            "below and keep the others exactly as they were. The failing lines, with the reason:\n" +
            "\n".join(f"- {key.get(v['slot'], v['slot'])}: {v['rule']}: {v['detail']}" for v in violations)[:1800])


def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
    """One written takeaway and the gates on ITS line (L-y 6: "one free-text line to judge per video ... measure it"):
    the deterministic fidelity rules and DUPLICATE on the takeaway slot, then the classifying verdict's violations on it.
    passed: True / False once the verdict judged it, None when other gates stopped the write before the verdict.
    context_framing: the context-integrity failures the VO's framing causes (VO_DEPENDENT; per clip, so not attributed
    to one line: recorded beside `passed`, never folded into it)."""
    line = next((x for x in pk["lines"] if x["slot"] == "takeaway"), {})
    rec = {"angle": ai + 1, "lineup": n_lineup, "write": w_used, "text": line.get("text"),
           "words": len((line.get("text") or "").split()),
           "cheap_fail": sorted({v["rule"] for v in cheap if v.get("slot") == "takeaway"}),
           "other_cheap_fail": sorted({v["rule"] for v in cheap if v.get("slot") != "takeaway"}), "verdict_fail": None,
           "passed": False if any(v.get("slot") == "takeaway" for v in cheap) else None,
           "context_framing": None if cx is None else sorted({v["rule"] for v in cx.get("violations") or []
                                                              if v.get("rule") in VO_DEPENDENT})}
    if fid is not None:
        ver = fid.get("verdict") or {}
        if fid.get("measured") and isinstance(ver.get("violations"), list):
            rec["verdict_fail"] = sorted({v["rule"] for v in ver["violations"] if v.get("slot") in ("takeaway", "-")})
            rec["passed"] = not rec["cheap_fail"] and not rec["verdict_fail"]
        else:
            rec["verdict_fail"] = ["NOT MEASURED"]
            rec["passed"] = False if rec["cheap_fail"] else None
    return rec


def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD):
    """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
    item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
    written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
    one bridge, only at the join the clips-alone verdict flagged); the first package that passes every hard gate wins.
    work_dir: where law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger.
    spend: a callable returning the ledger's USD (dollars per package).
    -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
    t0 = time.time()
    usd0 = _spent(spend)
    ms, why = usable(moments, ctx, delivered, optout)
    n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
    ms, reposted = reposted_once(ms, sources)          # ruling 53: a speech re-posted by a second channel is ONE
    no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
               for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
    trims = {m["moment_id"]: v for m in ms if m["moment_id"] in no_role for v in [trim_variant(m, sources)] if v}
    ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42)
    ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
    ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
    wv, wf = _writers(router)
    a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
    levels = current_levels(sources.values(), ctx)
    out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
           "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
           "reposted": reposted,
           "prescreen": {"screened": len(fails), "cleared": len(cleared),
                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
           "package": None}
    log(f"  {n_usable} usable, {len(reposted)} of them the same speech re-posted by a second channel (ruling 53: "
        f"the original publisher's kept), {len(no_role)} left out by the render's STAND_ALONE (an opener the clip scorer "
        f"would have to affirm, or no place under the topic rule with the pin's screen; {len(trims)} of them back as "
        f"variants with ONE leading word trimmed, ruling 33 part 2), {len(ad_read)} on an ad-read "
        f"marker (the exclusion screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
    if len({m["channel_id"] for m in cleared.values()}) < 3:
        out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
        return out
    if not work_dir:
        out["why_none"] = "no work_dir: law L-v 2's second pass cannot run, so no package can pass (fail closed)"
        return out
    from select_by_id import UNTRUSTED
    from story_semantics import quote_data
    exc, tru = {}, {}
    with ThreadPoolExecutor(max_workers=8) as pre:     # L-v 2 + CUTTABLE per moment, before the angles (L-y 3)
        futs = {mid: pre.submit(truth_for, router, m, work_dir, tru) for mid, m in cleared.items()}
        tru.update({mid: f.result() for mid, f in futs.items()})
    cut_ok = lambda t: bool(t.get("ok")) and (t.get("edges") or {}).get("cuttable") is True
    out["prescreen"]["second_pass"] = {
        mid: "PASS" if cut_ok(t) else ("NOT MEASURED: " + t["error"] if t.get("error") else
                                       "L-v 2 FAIL" if not t.get("ok") else "not cuttable at an edge (ruling C / 7)")
        for mid, t in tru.items()}
    cleared = {mid: m for mid, m in cleared.items() if cut_ok(tru.get(mid) or {})}
    out["prescreen"]["cuttable"] = len(cleared)
    log(f"  {len(cleared)} of them pass the second recognition pass and CUTTABLE ({time.time() - t0:.0f} s)")
    hk = {}
    for mid, m in cleared.items():                     # G17a at the pin stage: which moments may OPEN a medley. In
        m["hook_onset"] = hook_onset_for(m, sources, work_dir, hk)    # turn: a CPU decode of the L-v 2 window each,
                                                                      # already on disk (audit 0155 C2: grok, qwen, glm)
    out["prescreen"]["hook_onset"] = {mid: "PASS" if m["hook_onset"].get("pass") is True else
                                      ("NOT MEASURED: " if not m["hook_onset"].get("measured") else "FAIL: ") +
                                      str(m["hook_onset"].get("why")) for mid, m in cleared.items()}
    trim_cut = {mid: ("NOT MEASURED: " if not t.get("measured") else "FAIL: ") + str(t.get("why"))   # ruling 33 (a):
                for mid, m in cleared.items() if m.get("trimmed_leading")        # the trimmed cut as the render plans
                for t in [m["hook_onset"].get("trim") or {"measured": False, "why": "no trimmed-cut record"}]   # it
                if t.get("pass") is not True}                                    # opens in quiet, at ANY place. Its
    cleared = {mid: m for mid, m in cleared.items() if mid not in trim_cut}     # hook lead decides only whether it
    # may OPEN the medley (hook_onset "pass", need_onset), never whether it may play as a clip (audit 0710 C1, qwen)
    out["prescreen"]["trim_cut"] = trim_cut
    log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
        f"(G17a at the pin stage: genuine quiet before the first onset)")
    a_two, off_fail = second_screen(router, cleared, a_by, sources, ctx, log=log)        # ORDER 06:22 item 45
    out["prescreen"]["second_vendor"] = {mid: f"PASS ({a_two[mid][1].get('backend')})" if mid in a_two else
                                         "FAIL: " + "; ".join(off_fail.get(mid) or ["no second verdict"])
                                         for mid in cleared}
    cleared = {mid: m for mid, m in cleared.items() if mid in a_two}
    log(f"  {len(cleared)} of them clear step A from both vendors too (order 06:22 item 45: whichever vendor writes, "
        f"a verdict off it exists) ({time.time() - t0:.0f} s)")
    if len({m["channel_id"] for m in cleared.values()}) < 3:
        out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass, CUTTABLE and step A from both "
                           f"vendors, from fewer than 3 channels")
        return out
    clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s{placement(m)} | '
                      f'"{quote_data(m["text"], 600)}"'
                      for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
    lo, hi = medley_content_range()
    angles, angle_reply = None, None
    for seed in (7, 8):                               # one re-ask on an out-of-contract reply (never served again)
        r = None
        try:
            r = router.call("angle_write", ANGLE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"),
                                                               clips=clips, k=max_angles, lo=lo, hi=hi), 3000, seed,
                            deadline_s=WRITER_DEADLINE_S)
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
    out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
    writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}

    def off_writers(mid):
        """ORDER 06:22 item 45: the moment's passing step-A verdict from a back-end off every writer's vendor and
        family so far, else None (the re-screen after a write decides, item 44). The FIRST qualifying one in a_two's
        order (the first screen's, then the second's, then any re-screen's): any verdict off the writers satisfies
        L-x, so a later one is never preferred."""
        for a_ in a_two.get(mid, ()):
            b = router.backends.get(a_.get("backend"))
            if b is not None and b.vendor not in writers_v and b.family not in writers_f:
                return a_
        return None
    for mid in cleared:
        a_by[mid] = off_writers(mid) or a_by[mid]
    writer_avoid = {router.backends[n].vendor for n in router.chain("angle_write") if n in router.backends} - \
        {angle_reply.vendor}                   # every write stays on the angle's vendor, so a judge is always left
    log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)")
    doomed = set()                                         # moments a per-moment gate dropped: out of every angle

    def over_budget(ai):
        """The SEARCH budget (ruling 41, 04:58): a build may spend $3.00 vendor-reported searching ($10.00 estimate
        ceiling), inside SEARCH_WALL_S. Checked before every line-up and every write. -> the stop record (it ends the
        build), or None. Ruling 5's 15 min / $1.50 is per PACKAGE delivered: package_over()."""
        used_s = time.time() - t0
        est, rep = (a - b for a, b in zip(_spent(spend), usd0))
        if used_s <= SEARCH_WALL_S and rep <= SEARCH_USD_REPORTED and est <= SEARCH_USD_ESTIMATE:
            return None
        out["why_none"] = (f"stopped in angle {ai + 1} of {len(angles)}: the search spent {used_s:.0f} s of "
                           f"{SEARCH_WALL_S:.0f} s / ${rep:.2f} of ${SEARCH_USD_REPORTED:.2f} reported / ${est:.2f} of "
                           f"the ${SEARCH_USD_ESTIMATE:.2f} estimate ceiling (ruling 41, 04:58)")
        out["budget_stop"] = {"seconds": round(used_s, 1), "usd_reported": round(rep, 4), "usd_estimate": round(est, 4),
                              "angles_tried": ai + 1, "angles": len(angles)}
        return out["budget_stop"]

    def package_over(line):
        """Ruling 5 (22:40) as ruling 41 reads it: per PACKAGE delivered, 15 min wall and $1.50 reported (the $5
        estimate ceiling), counted from the moment its own line-up's clips-alone verdict is requested, that call
        included (line = (time, spend then)). Checked before every write. -> why this line-up stops (the search goes
        on), or None."""
        l_s = time.time() - line[0]
        l_est, l_rep = (a - b for a, b in zip(_spent(spend), line[1]))
        if l_s <= BUDGET_WALL_S and l_rep <= BUDGET_USD_REPORTED and l_est <= BUDGET_USD_ESTIMATE:
            return None
        return (f"this line-up's package spent {l_s:.0f} s of {BUDGET_WALL_S:.0f} s / ${l_rep:.2f} of "
                f"${BUDGET_USD_REPORTED:.2f} reported / ${l_est:.2f} of the ${BUDGET_USD_ESTIMATE:.2f} estimate (ruling 5, "
                f"per package delivered: ruling 41)")

    def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup):
        """Ruling 3 (22:40): the takeaway failed its gates twice on a line-up whose clips ALONE passed with no join a
        viewer cannot follow, so the package ships with NO VO line: clips back to back and the sign-off. It is not
        dropped. The title and caption are the latest write's and go through every gate again. The factory's estimate
        must still land 60-70 s, so when the clips are too short one more clip of the angle is added in the proposer's
        order, and the new line-up is judged on the clips alone again. -> a package, or None (rec["no_voice"] why)."""
        nv_lo, nv_hi = RUNTIME_S[0] - FINAL_TAIL_S, RUNTIME_S[1] - FINAL_TAIL_S
        pos = {m_: i for i, m_ in enumerate(angle["moments"])}
        rec["no_voice"] = note = {"tried": True}
        if med.get("measured") is not True or med.get("flagged") != []:     # audit 2240 C1 (qwen, glm): its own guard
            note["why_not"] = "the clips-alone verdict is not a measured pass with every join followable"
            return None
        order, added, nv_med = list(segs), None, med
        content = sum(m["duration_s"] for m in order)
        if content > nv_hi:
            note["why_not"] = f"{content:.1f} s of clips: over {nv_hi:.1f} s with no VO line"
            return None
        if content < nv_lo:                                  # "the packager may add a clip"
            chans = {m["channel_id"] for m in segs}
            for mid in angle["moments"]:
                m = cleared.get(mid)
                if m is None or m in segs or mid in dropped or mid in doomed or m["channel_id"] in chans or \
                        not (m.get("eligibility") or {}).get("clip", {}).get("ok"):
                    continue
                cand = [segs[0]] + sorted(segs[1:] + [m], key=lambda x: pos.get(x["moment_id"], 99))
                if len(cand) - 1 > LY_CLIPS[1] or [x for x in cand[1:-1] if x["duration_s"] < SHORT_CLIP_S] or \
                        sum("price_prediction" in x.get("risk", []) for x in cand) > PRICE_PREDICTIONS_MAX or \
                        sum(bool(x.get("trimmed_leading")) for x in cand) > TRIMMED_PER_LINEUP_MAX or \
                        not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
                    continue
                order, added = cand, mid
                break
            if added is None:
                note["why_not"] = f"{content:.1f} s of clips and no one clip of the angle lands {nv_lo:.1f}-{nv_hi:.1f} s"
                return None
            ok2, nv_med = medley(router, order, ctx, writers_v, seed=50 + n_lineup + 10 * ai, writer_family=writers_f)
            note["medley"] = nv_med
            if not ok2 or nv_med["flagged"]:
                note["why_not"] = "the line-up with the added clip fails on the clips alone (or has a join to bridge)"
                return None
        fields = {"takeaway": None, "bridge": None, "bridge_after": None, "title": last["title"],
                  "caption": last["caption"], "type": "moments", "angle": angle["angle"], "style": "medley, no voice",
                  "supply_exception": exception,
                  "no_voice": {"why": "the takeaway failed its gates in both writes; ruling 3 (22:40) ships the clips "
                                      "back to back with the sign-off only", "added_clip": added,
                               "lineup_before": [m["moment_id"] for m in segs]}}
        pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
        pk["medley"] = nv_med
        cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
        if cheap:
            note["why_not"] = f"cheap gates: {sorted({v['rule'] for v in cheap})}"
            note["violations"] = cheap
            return None
        with ThreadPoolExecutor(max_workers=8) as nv_pool:
            bg2 = {m["moment_id"]: (nv_pool.submit(exclusion_for, router, m, sources, exc),
                                    nv_pool.submit(truth_for, router, m, work_dir, tru)) for m in order}
            got = {mid: (f[0].result(), f[1].result()) for mid, f in bg2.items()}
            if any(e.get("verdict") != "keep" or not t.get("ok") or (t.get("edges") or {}).get("cuttable") is not True
                   for e, t in got.values()):
                note["why_not"] = "a clip fails exclusion, the second pass or CUTTABLE"
                return None
            fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, nv_pool)
        if not fid["ok"] or not cx["ok"]:
            note["why_not"] = "the title / caption fail VO fidelity or context integrity"
            note["violations"] = fid["violations"] + cx["violations"]
            return None
        coh = dict(nv_med, vo_point=None, note="no VO line: the clips-alone verdict is the coherence verdict (ruling 3)")
        a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
        pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab, {k: v for k, (v, _) in got.items()},
                                {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
                                shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
                                hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
                                stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]))
        import package_pin
        problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
        if problems:
            note["why_not"] = f"a required gate is not exactly PASS: {problems}"
            return None
        pk["models"] = {"angle": angle_reply.backend, "writer": "the latest write's title and caption",
                        "medley": nv_med.get("backend"), "fidelity_verdict": fid.get("backend"),
                        "context": cx.get("backends"), "coherence": nv_med.get("backend")}
        pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": nv_med}
        pk["seconds"] = round(time.time() - t0, 1)
        pk["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
        note["result"] = "PACKAGE"
        log(f"  angle {ai + 1} line-up {n_lineup}: NO-VOICE package ({len(order)} clips, "
            f"{sum(m['duration_s'] for m in order):.1f} s, added {added}) ({time.time() - t0:.0f} s)")
        return pk

    total = 0                                             # ruling 41: line-ups judged in this build, over every angle
    with ThreadPoolExecutor(max_workers=8) as pool:
        for ai, angle in enumerate(angles):
            dropped, n_lineup, swapped = set(), 0, None
            while total < lineups and not out["packages"] and not out.get("budget_stop"):
                if over_budget(ai):
                    break
                if swapped is not None:                   # ruling 41: the swapped line-up is judged next
                    segs, swapped = swapped, None
                    exception = supply_exception(segs, ctx)
                else:
                    segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
                                                 need_stand_alone=True), None
                    if segs is None:                      # L-y 4: one clip per channel unless the supply forces otherwise
                        segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True,
                                          need_stand_alone=True)
                        if segs is not None:
                            exception = supply_exception(segs, ctx)
                    filled = None
                    if segs is None and n_lineup == 0:    # PROPOSAL 1: the angle's own moments form not even its
                        segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed))   # FIRST line-up: the
                        # pool completes it. A re-line after a drop moves on to the next angle, as before
                        exception = supply_exception(segs, ctx) if segs is not None else None
                rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
                       "supply_exception": exception, "attempts": [],
                       **({"pool_filled": filled} if filled else {})}
                out["tried"].append(rec)
                if segs is None:
                    rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
                    break
                n_lineup += 1
                total += 1
                line = (time.time(), _spent(spend))         # this line-up's package budget counts from here (ruling 41)
                ok_m, med = medley(router, segs, ctx, writers_v, seed=7 + n_lineup + 10 * ai, writer_family=writers_f)
                rec["medley"], rec["medley_ok"] = med, ok_m
                log(f"  angle {ai + 1} line-up {n_lineup} ({len(segs)} clips, "
                    f"{sum(m['duration_s'] for m in segs):.1f} s): clips alone {'PASS' if ok_m else 'FAIL'} "
                    f"{med.get('clips')} flagged {med.get('flagged')} ({time.time() - t0:.0f} s)")
                labs = labels(len(segs))
                if not ok_m:                              # L-y 2 / 3: pick clips that sit together
                    by_lab = dict(zip(labs, segs))
                    weak = {by_lab[lb]["moment_id"] for lb, x in (med.get("clips") or {}).items()
                            if lb in by_lab and x < COHERENCE_MIN}      # ruling 41: the HOOK too (the next hook)
                    if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
                        weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
                    if not med.get("measured") or not weak:
                        rec["why"] = "the clips alone have no through-line a viewer can state (or it was not measured)"
                        break
                    dropped |= weak
                    swapped, swaps = swap_lineup(segs, weak, cleared, frozenset(dropped | doomed))
                    rec["why"] = (f"the clips alone fail (ratings / joins): swapped {swaps}, re-judged (ruling 41)"
                                  if swapped is not None else
                                  f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, no swap fits the "
                                  f"line-up rules: re-lined")
                    continue
                if question_hook(segs) and joins(labs)[0] in med["flagged"]:   # ruling 37: no bridge after a question
                    dropped.add(segs[1]["moment_id"])
                    rec["why"] = (f"ruling 37: the join after the question hook must be followable without a bridge, and "
                                  f"the clips alone flag {joins(labs)[0]}: re-lined")
                    continue
                join = None
                if med["flagged"]:
                    k = joins(labs).index(med["flagged"][0])
                    join = (k, med["joins"][med["flagged"][0]]["why"])
                bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
                                       pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
                extra, relined, w_used, written = "", False, 0, ()
                take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
                while w_used < writes:
                    if over_budget(ai):
                        break
                    w_over = package_over(line)
                    if w_over:
                        rec["why"] = w_over
                        break
                    w_used += 1
                    try:
                        wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup,
                                                    avoid_vendor=writer_avoid or None, other=written)
                    except NoBridgeFits as e:                  # the seconds rule it out: re-line, no write is paid
                        if join is not None:
                            dropped.add(segs[join[0] + 1]["moment_id"])
                        rec["why"] = f"{e}: re-lined"
                        relined = join is not None
                        break
                    except Exception as e:
                        rec["attempts"].append({"writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
                        continue
                    writers_v.add(wr.vendor)
                    writers_f.add(wr.family)
                    for m in segs:                             # item 45: the verdict off every writer, when one exists
                        a_by[m["moment_id"]] = off_writers(m["moment_id"]) or a_by[m["moment_id"]]
                    stale = [m for m in segs if (lambda b: b is None or b.vendor in writers_v or b.family in writers_f)(
                        router.backends.get((a_by.get(m["moment_id"]) or {}).get("backend")))]
                    if stale:                                  # audit C2 K5: never judged by the writer's vendor
                        got_a, fails_a, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f,
                                                         n=len(stale), store=None)
                        bad = {}
                        for m in stale:
                            mid = m["moment_id"]
                            if got_a.get(mid) is not None and not fails_a.get(mid):
                                a_by[mid] = got_a[mid]
                                a_two.setdefault(mid, []).append(got_a[mid])
                            else:                              # no verdict off the writers is never a pass (L-m)
                                bad[mid] = list(fails_a.get(mid) or ["STEP_A_UNAVAILABLE: no verdict off the writers "
                                                                     "(law L-m)"])
                        if bad:                                # ORDER 06:22 item 44: only these clips go, for good,
                            dropped |= set(bad)                # with their reason; the next-best cuttable clip takes
                            doomed |= set(bad)                 # each place (ruling 41's swap); the clips-alone verdict
                            out["prescreen"].setdefault("rescreen_failed", {}).update(bad)     # re-judges the line-up
                            swapped, swaps = swap_lineup(segs, set(bad), cleared, frozenset(dropped | doomed))
                            rec["why"] = (f"step A, re-screened off the writer's vendor, fails {sorted(bad)} (out for "
                                          f"good): " + (f"swapped {swaps}, re-judged (order 06:22 item 44)"
                                                        if swapped is not None else
                                                        "no swap fits the line-up rules: re-lined"))
                            relined = True
                            break
                    if join is not None and fields["bridge"] is None:
                        dropped.add(segs[join[0] + 1]["moment_id"])
                        rec["why"] = (f"the clips-alone verdict flagged {med['flagged'][0]}; the writer judged it "
                                      f"followable without a bridge: these clips do not sit together (L-y 2): re-lined")
                        relined = True
                        break
                    if fields["bridge"] is not None:
                        fields["bridge_confirmed_by"] = {"join": med["flagged"][0], "why": join[1],
                                                         "backend": med.get("backend")}
                    fields["supply_exception"] = exception
                    pk = assemble_medley([m["moment_id"] for m in segs], cleared, fields, ctx,
                                         f"medley (L-y), written, attempt {w_used}")
                    pk["medley"] = med
                    written = [fields["bridge"]["text"]] if fields.get("bridge") else ()   # a redo budgets with it
                    cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
                    att = {"writer": wr.backend, "writer_tried": [list(x) for x in getattr(wr, "tried", [])],   # ruling 5
                           "runtime": pk["runtime_s_estimate"], "bridge": pk["bridge"],
                           "takeaway_budget": fields.get("takeaway_budget"),
                           "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]]}
                    rec["attempts"].append(att)
                    take = _takeaway_record(ai, n_lineup, w_used, pk, cheap)
                    out["takeaways"].append(take)
                    last_fields = fields
                    log(f"  angle {ai + 1} line-up {n_lineup} write {w_used} ({wr.backend}, takeaway {take['words']} "
                        f"words, {pk['runtime_s_estimate']} s): " +
                        ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
                        + f" ({time.time() - t0:.0f} s)")
                    got = {mid: (f[0].result(), f[1].result()) for mid, f in bg.items()}   # the clips' own gates first
                    lost = {mid for mid, (e, t) in got.items() if e.get("verdict") != "keep" or not t.get("ok")
                            or (t.get("edges") or {}).get("cuttable") is not True}   # CUTTABLE is a required gate
                    if lost:
                        rec["lost_why"] = {mid: ("exclusion" if e.get("verdict") != "keep" else
                                                 "second pass (L-v 2)" if not t.get("ok") else
                                                 "not cuttable at an edge (ruling C / 7)")
                                           for mid, (e, t) in got.items() if mid in lost}
                        att["exclusion"] = {mid: e for mid, (e, _) in got.items()}
                        dropped |= lost
                        doomed |= lost                         # per-moment verdicts: no angle may use them again
                        rec["why"] = f"exclusion / L-v 2 / CUTTABLE dropped {rec['lost_why']}: re-lined"
                        relined = True
                        break
                    if cheap:
                        att["violations"] = cheap
                        take_failed += take["passed"] is False
                        b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
                        extra = _redo([dict(v, detail=v["detail"] + (f" (a takeaway of {b[0]}-{b[1]} words lands it)"
                                                                     if b else " (no takeaway length lands it with this "
                                                                                "bridge: shorten the bridge)" if written
                                                                     else " (no takeaway length lands it)"))
                                       if v["rule"] == "RUNTIME" else v for v in cheap])
                        continue
                    fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid, cx)
                    framing = [v for v in cx["violations"] if v["rule"] in VO_DEPENDENT]
                    att["violations"] = fid["violations"] + cx["violations"]
                    att["verdict_classes"] = (fid.get("verdict") or {}).get("classes")
                    log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'} (takeaway "
                        f"{'PASS' if take['passed'] else take['verdict_fail']}), context "
                        f"{'PASS' if cx['ok'] else 'FAIL'} ({time.time() - t0:.0f} s)")
                    take_failed += take["passed"] is False
                    if not fid["ok"] or not cx["ok"]:
                        if fid["ok"] and not framing:
                            rec["why"] = "context integrity failed on something the VO cannot fix"
                            w_used = writes
                            break
                        extra = _redo(fid["violations"] + [{"slot": v["segment"], "rule": v["rule"],
                                                            "detail": VO_FIX.get(v["rule"], v["detail"])}
                                                           for v in framing])
                        continue
                    att["exclusion"] = {mid: e for mid, (e, _) in got.items()}
                    att["second_pass"] = {mid: t for mid, (_, t) in got.items()}
                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)    # then on the takeaway
                    att["coherence"] = coh
                    log(f"    coherence with the takeaway {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo "
                        f"{coh.get('vo_point')} ({time.time() - t0:.0f} s)")
                    a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
                    pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
                                            {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
                                            style=HS.lint_lines(pk["lines"]),
                                            hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
                                            stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]))
                    if not ok_c:
                        tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
                        if coh.get("measured") and type(coh.get("vo_point")) is int and \
                                coh["vo_point"] < COHERENCE_MIN and min(coh["clips"].values()) >= COHERENCE_MIN and \
                                len(tl.split()) >= 4 and not NO_LINE.search(tl):
                            take_failed += 1                  # the takeaway's point failed its coherence gate
                            extra = _redo([{"slot": "takeaway", "rule": "COHERENCE", "detail":
                                            f"a blind viewer rated the takeaway's point {coh['vo_point']} of 5 for "
                                            f"being supported by the clips: land the point the clips make together"}])
                            continue                          # the clips hold; only the takeaway's point is weak
                        weak = {sg["moment_id"] for sg in pk["segments"][1:]
                                if (coh.get("clips") or {}).get(sg["label"], COHERENCE_MIN) < COHERENCE_MIN}
                        dropped |= weak
                        relined = bool(weak)
                        rec["why"] = ("coherence with the takeaway below 4 or no through-line: " +
                                      (f"dropped {sorted(weak)}, re-lined" if weak else "next angle"))
                        break
                    import package_pin
                    problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
                    if problems:                              # never return a package its pin would refuse (L-j)
                        rec["why"] = f"a required gate is not exactly PASS: {problems}: next angle"
                        w_used = writes
                        break
                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend, "medley": med.get("backend"),
                                    "fidelity_verdict": fid.get("backend"), "context": cx.get("backends"),
                                    "coherence": coh.get("backend")}
                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med}
                    pk["seconds"] = round(time.time() - t0, 1)
                    pk["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
                    out["packages"].append(pk)
                    rec["result"] = "PACKAGE"
                    break
                if not out["packages"] and not relined and ok_m and not med["flagged"] and \
                        take_failed >= NO_VOICE_AFTER and last_fields is not None and not out.get("budget_stop"):
                    nv = no_voice(angle, segs, med, last_fields, exception, dropped, rec, ai, n_lineup)
                    if nv is not None:
                        out["packages"].append(nv)
                        rec["result"] = "PACKAGE (no voice, ruling 3)"
                if not out["packages"] and not rec.get("why") and not rec.get("result"):
                    last = (rec.get("attempts") or [{}])[-1]
                    rules = sorted({str(v.get("rule")) for v in last.get("violations") or []})
                    rec["why"] = f"{w_used} write(s) failed their gates" + (f" ({', '.join(rules)})" if rules else "")
                if out["packages"] or not relined:
                    break
            if out["packages"] or out.get("budget_stop") or over_budget(ai):
                break
    out["package"] = out["packages"][0] if out["packages"] else None
    s_est, s_rep = (a - b for a, b in zip(_spent(spend), usd0))
    out["search"] = {"lineups": total, "limit": lineups, "usd_reported": round(s_rep, 4),
                     "usd_estimate": round(s_est, 4), "seconds": round(time.time() - t0, 1)}
    log(f"  search: {total} line-up(s) of {lineups}, ${s_rep:.2f} reported / ${s_est:.2f} estimate (ruling 41: $3.00 "
        f"reported per build)")
    if out["package"] is None and not out.get("why_none"):       # every angle ended without a package: say why
        out["why_none"] = ("no angle gave a package: " + "; ".join(
            f"angle {t.get('angle')}: {str(t.get('why') or t.get('result') or 'no reason recorded')[:250]}"
            for t in out["tried"])) if out["tried"] else "no angle gave a line-up to try"
    out["seconds"] = round(time.time() - t0, 1)
    out["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
    return out


def _spent(spend):
    """(estimate, vendor-reported) from the caller's meter. A bare number is the estimate alone; its reported figure
    is then taken to be the same (the conservative reading). No meter: (0, 0)."""
    if not spend:
        return 0.0, 0.0
    v = spend()
    return (float(v[0]), float(v[1])) if isinstance(v, (tuple, list)) else (float(v), float(v))


def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
              hook=None, stand=None):
    """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
    {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
    A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
    (shape=(ok, [why]) from ly_shape()). hook: the hook moment's hook_onset record -> the "hook_onset" row (G17a at
    the pin stage, required for a medley: package_pin.MEDLEY_GATES); None leaves it out, which refuses the pin.
    stand: stand_alone_check() of the package's segments in play order -> the "stand_alone" row (the render's
    STAND_ALONE at the pin stage, required for a medley); None leaves it out, which refuses the pin."""
    row = lambda ok, by, replayed=False, n=1, measured=True: {
        "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
        "replayed": replayed if isinstance(replayed, bool) else None, "n": n}     # None (unstated) refuses the pin

    votes_of = lambda x: {"votes": x["majority"]["votes"]} if isinstance(x, dict) and x.get("majority") else {}

    def rep(values):                                 # tri-state over several replies (audit C2 K4)
        values = list(values)
        return None if any(not isinstance(x, bool) for x in values) else any(values)
    det = fid["deterministic"]
    viol = {v["rule"] for v in ctx_.get("violations") or []}
    a_rows = list((a_by or {}).values())
    return {
        "vo_fidelity_deterministic": row(det["ok"], "code (vo_fidelity.check_deterministic)"),
        "vo_fidelity_verdict": dict(row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"),
                                        fid.get("replayed"), n=fid.get("runs", 1), measured=bool(fid.get("measured"))),
                                    **({"votes": fid["majority"]["votes"], "splits": fid["majority"]["splits"]}
                                       if fid.get("majority") else {})),          # ruling 07:42 (3): the majority
        "duplicate": row(not dup, "code (package.duplicates)"),
        "price_now": row(not any(v["rule"] == "PRICE_NOW" for v in det["violations"]),
                         "code (vo_fidelity.price_now)", measured=bool(det.get("price_now_measured"))),
        "runtime": row(rt_ok, f"code (the factory's R4 estimate: {R4_WPS} w/s + {R4_PREROLL_S} s a VO line + "
                              f"{FINAL_TAIL_S} s tail)"),
        "r4": row(bool(r4_res[0]), "package.r4 (moments-first R4, orchestrator 06:00)"),
        "context_a": row(bool(a_rows) and not any(CI.a_failures(a) for a in a_rows),
                         sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
                         n=len(a_rows)),
        "context_b": dict(row(ctx_.get("ok") is True, (ctx_.get("backends") or {}).get("B"), ctx_.get("replayed"),
                              measured=bool(ctx_.get("measured"))), **votes_of(ctx_)),
        "context_c": dict(row(ctx_.get("ok") is True and not (viol & {"NOT_ENTAILED", "POLARITY", "STRONGER"}),
                              (ctx_.get("backends") or {}).get("C"), ctx_.get("replayed"),
                              measured=bool(ctx_.get("measured"))), **votes_of(ctx_)),
        "exclusion": dict(row(all(e.get("verdict") == "keep" for e in exc.values()),
                              sorted({str(e.get("backend")) for e in exc.values()}),
                              rep(e.get("replayed") for e in exc.values()), n=len(exc),
                              measured=all(e.get("measured") for e in exc.values())),
                          **({"votes": {k: e["majority"]["votes"] for k, e in exc.items() if e.get("majority")}}
                             if any(e.get("majority") for e in exc.values()) else {})),
        "second_pass": row(all(t.get("ok") for t in truth.values()), sorted({str(t.get("model")) for t in truth.values()}),
                           rep(t.get("replayed") for t in truth.values()), n=len(truth),
                           measured=all("error" not in t for t in truth.values())),
        "cuttable": row(all((t.get("edges") or {}).get("cuttable") is True for t in truth.values()),
                        "transcript_truth.edges: the independent recogniser's sentence boundary at every IN and OUT "
                        "(orchestrator 06:45 ruling C / 7)", rep(t.get("replayed") for t in truth.values()), n=len(truth),
                        measured=all("edges" in t for t in truth.values())),
        "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
                          **votes_of(coh)),
        **({"medley": dict(row(bool(medley[0]), medley[1].get("backend"), medley[1].get("replayed"),
                               measured=bool(medley[1].get("measured"))), flagged=medley[1].get("flagged"))}
           if medley is not None else {}),
        **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]))}
           if shape is not None else {}),
        **({"house_style": dict(row(not style, "code (house_style.lint_lines, ruling 6)"),
                                why=[f"{v['slot']}: {v['detail']}" for v in style])}
           if style is not None else {}),
        **({"hook_onset": dict(row(hook.get("pass") is True, "hook_onset.measure (sentence_law.edge_plan + head_tail "
                                   "on the source audio: G17a at the pin stage)", measured=hook.get("measured") is True),
                               lead_ms=hook.get("lead_ms"), cut_in=hook.get("cut_in"), why=hook.get("why"))}
           if hook is not None else {}),
        **({"stand_alone": dict(row(stand.get("ok") is True, "stand_alone.check_edl (the render's STAND_ALONE at the pin "
                                    "stage; no clip scorer, so a conjunction or reply-fragment opener fails closed)"),
                                rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
                                      f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"),
                                scorer_pending=stand.get("scorer_pending") or [])}
           if stand is not None else {}),
    }
