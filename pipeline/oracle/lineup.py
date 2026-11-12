#!/usr/bin/env python3
"""pipeline/oracle/lineup.py — the written product rules, the strict reply schemas and the deterministic checks.

A line-up = one hook + 2-3 clips, each segment a list of consecutive sentence ids (export rows) from one video.
  RULES          the product rules as written for both models (order pp-backtest: >= 2 partner channels on the
                 same development, current, a hook that stands alone, whole stand-alone sentences, enough for
                 60-70 s, no altcoin content) plus the format the selector builds (hook 8-12 s, clips 12-20 s,
                 1-3 sentences, ends on a statement, <= 2 segments per video, <= 2 clips per channel)
  parse_oracle   the oracle's reply, strictly: a malformed, empty or partial reply, or any sentence id that is not
                 a row of the day's export, is ORACLE_FAILED (OracleFailed), never NONE (law L-l, L-m)
  parse_judge    the judge's verdict, strictly: LEGAL only with every rule checked true and nothing failed; an
                 inconsistent reply is JUDGE_FAILED (JudgeFailed), never a pass
  check          the deterministic half of the rules: the ids form the segments the rules allow, the durations,
                 the channel count, the per-video / per-channel limits, the runtime floor and the altcoin word screen
                 (fail closed: a line-up the screen catches is illegal whatever the models said)
  VARIANTS       the rule sets measured (orchestrator note 2026-11-12 01:55): same_dev_hard (the order's rules, the
                 8-12 s / 12-20 s windows hard), same_dev (the same with the windows as targets, law L-o) and moments
                 (PBX's 01:48 rule: moments from >= 2 channels need not be one development; a voiceover may stitch
                 them if it never misattributes); the last two ask for as many sentence-disjoint line-ups as exist.
                 Every line-up's window misses are recorded, so legality with the windows hard is known for all.
"""
import json
import re

import canon  # noqa: E402  (flat, as the pipeline imports it: pipeline/oracle/__init__.py puts pipeline/ on sys.path)

HOOK_S = (8.0, 12.0)                   # = editorial_select.HOOK_MIN_S, HOOK_MAX_S
CLIP_S = (12.0, 20.0)                  # = editorial_select.CLIP_MIN_S, CLIP_MAX_S (PBX mission 1d)
MAX_SENTENCES = 3                      # = editorial_select.MAX_WINDOW_SENTENCES
CLIPS = (2, 3)                         # hook + >= 2 clips (SELECT success, red-team D); v2f format: 3 clips
MIN_CHANNELS = 2                       # = MIN_COVERAGE_CHANNELS / MIN_LAYOUT_CHANNELS
import editorial_select as _es  # noqa: E402  (one source for the limits the selector enforces; LAW 20)
if (HOOK_S, CLIP_S, MAX_SENTENCES, MIN_CHANNELS) != ((_es.HOOK_MIN_S, _es.HOOK_MAX_S), (_es.CLIP_MIN_S, _es.CLIP_MAX_S),
                                                     _es.MAX_WINDOW_SENTENCES, _es.MIN_COVERAGE_CHANNELS):
    raise ImportError("pipeline/oracle/lineup.py: the selector's hook / clip windows, sentence or channel limits changed; "
                      "the oracle's rules (and the prompts pinned by sha) must change with them, never silently")
PER_VIDEO = 2                          # = editorial_select.MAX_VERIFIED_QUOTES_PER_VIDEO
CLIPS_PER_CHANNEL = 2                  # editorial_select assemble(): a third clip of one channel is skipped
CARD_AND_OUTRO_S = 13.5                # credits card ~9 s + locked outro 4.46 s (DoD DEC-10e G5 note)
MIN_RUNTIME_S = 60.0                   # G5 floor; the format's target is 60-70 s
MIN_CONTENT_S = MIN_RUNTIME_S - CARD_AND_OUTRO_S
MAX_LINEUPS = 3
ALTCOINS = {"ethereum", "eth", "ether", "solana", "xrp", "cardano", "dogecoin", "doge", "shiba", "bnb", "avax",
            "polkadot", "litecoin", "ltc", "chainlink", "matic", "monero", "xmr", "trx", "toncoin", "hyperliquid",
            "pepe", "altcoin", "altcoins", "memecoin", "memecoins", "shitcoin", "shitcoins"}
ID = re.compile(r"[A-Za-z0-9_-]{6,20}:\d{1,5}")

_HEAD = "PRODUCT RULES (Pulse Check: a 60-70 second Bitcoin news video made only of partner channels' own words)"
_HEAD_MOMENTS = "PRODUCT RULES (Pulse Check: a 60-70 second Bitcoin video made only of partner channels' own words)"
_R1_DEV = """1. ONE DEVELOPMENT, AT LEAST TWO CHANNELS. The whole line-up is about one specific Bitcoin news development, and
   at least two different channels state that same development. The same topic is not enough: "the Bitcoin price"
   or "ETF flows" is a topic; "Bitcoin fell below $74,000 over the weekend" or "US spot Bitcoin ETFs saw $1.3
   billion of outflows last week" is a development. Every segment states the development itself or a direct
   consequence of / reaction to it. Every channel in the statements is a partner channel."""
_R1_MOMENTS = """1. MOMENTS FROM AT LEAST TWO CHANNELS, NEVER MISATTRIBUTED. The line-up is the best stand-alone, engagement-worthy
   moments about Bitcoin from at least two different partner channels. The segments need NOT be about one
   development: a short voiceover may link different moments, so their order must allow a truthful one-sentence
   bridge between them. Never misattribute: no segment may be placed so that it sounds like a reply to, a
   confirmation of, or the source of another channel's claim unless it is one, and no claim may be heard as another
   channel's. Every channel in the statements is a partner channel."""
_R2_DEV = """2. CURRENT. The development happened or materially changed in the 72 hours before the video is made, and the
   segments present it as current news, not as background, history or a recap of something older."""
_R2_MOMENTS = """2. CURRENT. Every segment speaks about something current: news, data or a view about the 72 hours before the
   video is made, not history, evergreen education or a recap of something older."""
_R3 = """3. A HOOK THAT STANDS ALONE. The first segment (the hook) is heard first, with nothing before it. On its own it
   must make clear that the subject is Bitcoin and what happened: it may not open on a word that points to
   something unheard (a pronoun such as "it", "this", "that", "they"; a connective such as "and", "but", "so";
   a reply such as "yeah", "right")."""
_R4_DEV = f"""4. WHOLE STAND-ALONE SENTENCES. Every segment is 1-{MAX_SENTENCES} whole consecutive sentences of one video, from the
   start of its first sentence to the end of its last, and it ends on a statement (a full stop or an exclamation
   mark, never a question). Each clip makes sense heard right after the segments before it; nothing in it
   depends on words that are not in the line-up."""
_R4_MOMENTS = f"""4. WHOLE STAND-ALONE SENTENCES WORTH HEARING. Every segment is 1-{MAX_SENTENCES} whole consecutive sentences of one video,
   from the start of its first sentence to the end of its last, and it ends on a statement (a full stop or an
   exclamation mark, never a question). Every segment makes complete sense on its own (nothing in it depends on
   words that are not in the line-up) and is worth hearing: a specific claim, number, insight or strong view, never
   filler, an ad read, small talk, a question or channel housekeeping."""
_R5_HARD = f"""5. ENOUGH FOR 60-70 SECONDS. One hook of {HOOK_S[0]:g}-{HOOK_S[1]:g} seconds, then {CLIPS[0]} or {CLIPS[1]} clips of {CLIP_S[0]:g}-{CLIP_S[1]:g} seconds each;
   hook plus clips total at least {MIN_CONTENT_S:g} seconds (the credits card and outro add about {CARD_AND_OUTRO_S:g} seconds)."""
_R5_TARGET = f"""5. ENOUGH FOR 60-70 SECONDS. One hook, then {CLIPS[0]} or {CLIPS[1]} clips; hook plus clips total at least {MIN_CONTENT_S:g} seconds (the
   credits card and outro add about {CARD_AND_OUTRO_S:g} seconds; aim for 60-70 seconds in all). Duration TARGETS, not limits: a
   hook of about {HOOK_S[0]:g}-{HOOK_S[1]:g} seconds and clips of about {CLIP_S[0]:g}-{CLIP_S[1]:g} seconds; a segment may go outside its target when
   the moment needs it."""
_R6 = """6. NO ALTCOIN CONTENT. No segment names or discusses any cryptocurrency other than Bitcoin (Ethereum/ETH,
   Solana, XRP, Dogecoin, BNB, Cardano, memecoins, "altcoins", ...), not even in passing or as a comparison."""
_FORMAT = (f"FORMAT LIMITS. At most {PER_VIDEO} segments from one video, never sharing a sentence; at most "
           f"{CLIPS_PER_CHANNEL} clips from one channel.")


def _rules(head, *parts):
    return "\n".join((head,) + parts + (_FORMAT,))


RULES = _rules(_HEAD, _R1_DEV, _R2_DEV, _R3, _R4_DEV, _R5_HARD, _R6)
RULES_SAME_TARGETS = _rules(_HEAD, _R1_DEV, _R2_DEV, _R3, _R4_DEV, _R5_TARGET, _R6)
RULES_MOMENTS = _rules(_HEAD_MOMENTS, _R1_MOMENTS, _R2_MOMENTS, _R3, _R4_MOMENTS, _R5_TARGET, _R6)

ORACLE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["verdict", "none_reason", "lineups"],
    "properties": {
        "verdict": {"type": "string", "enum": ["LINEUPS", "NONE"]},
        "none_reason": {"type": "string"},
        "lineups": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["development", "current_because", "hook", "clips"],
            "properties": {
                "development": {"type": "string"},
                "current_because": {"type": "string"},
                "hook": {"type": "array", "items": {"type": "string"}},
                "clips": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}}}}}}

JUDGE_CHECKS = ("one_development_two_channels", "current", "hook_stands_alone", "whole_standalone_sentences",
                "enough_for_60_70_s", "no_altcoin_content", "format_limits")
MOMENT_CHECKS = ("two_channels_never_misattributed",) + JUDGE_CHECKS[1:]


def judge_schema(checks=JUDGE_CHECKS):
    return {"type": "object", "additionalProperties": False,
            "required": ["development", "checks", "failed", "verdict", "reason"],
            "properties": {
                "development": {"type": "string"},
                "checks": {"type": "object", "additionalProperties": False, "required": list(checks),
                           "properties": {k: {"type": "boolean"} for k in checks}},
                "failed": {"type": "array", "items": {"type": "string", "enum": list(checks)}},
                "verdict": {"type": "string", "enum": ["LEGAL", "ILLEGAL"]},
                "reason": {"type": "string"}}}


JUDGE_SCHEMA = judge_schema()
VARIANTS = {
    "same_dev_hard": {"rules": RULES, "checks": JUDGE_CHECKS, "windows_hard": True, "max_lineups": MAX_LINEUPS,
                      "distinct": False, "subdir": "",
                      "label": "same development; 8-12 s / 12-20 s windows hard; up to 3 line-ups asked"},
    "same_dev_hard_max": {"rules": RULES, "checks": JUDGE_CHECKS, "windows_hard": True, "max_lineups": 8,
                          "distinct": True, "subdir": "same_dev_hard_max", "judge_as": "same_dev_hard",
                          "label": "same development; windows hard; as many sentence-disjoint line-ups as exist"},
    "same_dev": {"rules": RULES_SAME_TARGETS, "checks": JUDGE_CHECKS, "windows_hard": False, "max_lineups": 8,
                 "distinct": True, "subdir": "same_dev",
                 "label": "same development; windows as targets (L-o); as many sentence-disjoint line-ups as exist"},
    "moments": {"rules": RULES_MOMENTS, "checks": MOMENT_CHECKS, "windows_hard": False, "max_lineups": 8,
                "distinct": True, "subdir": "moments",
                "label": "moments first (PBX 01:48); windows as targets (L-o); as many sentence-disjoint line-ups"},
}


class OracleFailed(ValueError):
    """The oracle's reply is not a whole, valid answer: recorded as ORACLE_FAILED, never as NONE."""


class JudgeFailed(ValueError):
    """The judge's reply is not a whole, consistent verdict: recorded as JUDGE_FAILED, never as a pass."""


def _json_object(text, err):
    if not isinstance(text, str) or not text.strip():
        raise err("empty reply")
    try:
        obj = json.loads(text)
    except ValueError as e:
        raise err(f"not JSON: {e}")
    if not isinstance(obj, dict):
        raise err("reply is not a JSON object")
    return obj


def _exact_keys(obj, keys, where, err):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        got = sorted(obj) if isinstance(obj, dict) else type(obj).__name__
        raise err(f"{where}: keys {got} != {sorted(keys)}")


def _ids(v, where, rows_by_id):
    if not isinstance(v, list) or not v or not all(isinstance(x, str) for x in v):
        raise OracleFailed(f"{where}: must be a non-empty list of sentence ids")
    for x in v:
        if not ID.fullmatch(x):
            raise OracleFailed(f"{where}: malformed sentence id {x!r}")
        if x not in rows_by_id:
            raise OracleFailed(f"{where}: sentence id {x!r} is not in the day's statements")
    return list(v)


def parse_oracle(text, rows_by_id, max_lineups=MAX_LINEUPS):
    """{'verdict': 'LINEUPS'|'NONE', 'none_reason', 'lineups': [{'development', 'current_because', 'hook', 'clips'}]}
    or OracleFailed. Every id must be a row of the day's export; NONE needs its reason and no line-up."""
    o = _json_object(text, OracleFailed)
    _exact_keys(o, ORACLE_SCHEMA["required"], "reply", OracleFailed)
    if o["verdict"] not in ("LINEUPS", "NONE"):
        raise OracleFailed(f"verdict {o['verdict']!r}")
    if not isinstance(o["none_reason"], str) or not isinstance(o["lineups"], list):
        raise OracleFailed("none_reason must be a string and lineups a list")
    if o["verdict"] == "NONE":
        if o["lineups"] or not o["none_reason"].strip():
            raise OracleFailed("NONE needs a reason and no line-up")
        return {"verdict": "NONE", "none_reason": o["none_reason"].strip(), "lineups": []}
    if not 1 <= len(o["lineups"]) <= max_lineups:
        raise OracleFailed(f"LINEUPS needs 1-{max_lineups} line-ups, got {len(o['lineups'])}")
    out = []
    for k, lu in enumerate(o["lineups"], 1):
        _exact_keys(lu, ORACLE_SCHEMA["properties"]["lineups"]["items"]["required"], f"line-up {k}", OracleFailed)
        for f in ("development", "current_because"):
            if not isinstance(lu[f], str) or not lu[f].strip():
                raise OracleFailed(f"line-up {k}: {f} must be a non-empty string")
        if not isinstance(lu["clips"], list) or not lu["clips"]:
            raise OracleFailed(f"line-up {k}: clips must be a non-empty list of segments")
        out.append({"development": lu["development"].strip(), "current_because": lu["current_because"].strip(),
                    "hook": _ids(lu["hook"], f"line-up {k} hook", rows_by_id),
                    "clips": [_ids(c, f"line-up {k} clip {j}", rows_by_id) for j, c in enumerate(lu["clips"], 1)]})
    return {"verdict": "LINEUPS", "none_reason": o["none_reason"].strip(), "lineups": out}


def parse_judge(text, checks=JUDGE_CHECKS):
    """{'development', 'checks', 'failed', 'verdict', 'reason'} or JudgeFailed. LEGAL only when every check is
    exactly true and nothing failed; ILLEGAL only when the failed list names exactly the false checks."""
    o = _json_object(text, JudgeFailed)
    _exact_keys(o, JUDGE_SCHEMA["required"], "reply", JudgeFailed)
    _exact_keys(o["checks"], checks, "checks", JudgeFailed)
    if not all(type(v) is bool for v in o["checks"].values()):
        raise JudgeFailed("every check must be true or false")
    if not isinstance(o["failed"], list) or not all(isinstance(x, str) and x in checks for x in o["failed"]):
        raise JudgeFailed("failed must list check names")
    if o["verdict"] not in ("LEGAL", "ILLEGAL"):
        raise JudgeFailed(f"verdict {o['verdict']!r}")
    for f in ("development", "reason"):
        if not isinstance(o[f], str) or not o[f].strip():
            raise JudgeFailed(f"{f} must be a non-empty string")
    false = {k for k, v in o["checks"].items() if v is False}
    if set(o["failed"]) != false or len(o["failed"]) != len(false):
        raise JudgeFailed(f"failed {sorted(o['failed'])} does not match the false checks {sorted(false)}")
    if (o["verdict"] == "LEGAL") != (not false):
        raise JudgeFailed(f"verdict {o['verdict']} contradicts the checks (false: {sorted(false)})")
    return {"development": o["development"].strip(), "checks": dict(o["checks"]), "failed": sorted(false),
            "verdict": o["verdict"], "reason": o["reason"].strip()}


def altcoin_terms(text):
    """Altcoin words a sentence names (canonical tokens; the channel name 'Altcoin Daily' is not content)."""
    toks = canon.canon_tokens(text)
    return sorted({t for i, t in enumerate(toks) if t in ALTCOINS
                   and not (t == "altcoin" and i + 1 < len(toks) and toks[i + 1] == "daily")})


def segments(lineup):
    return [("hook", lineup["hook"])] + [(f"clip_{j:02d}", c) for j, c in enumerate(lineup["clips"], 1)]


def check(lineup, rows_by_id, windows_hard=True):
    """[violation, ...] of the deterministic rules for one parsed line-up (empty = structurally legal), plus a
    summary {'segments': [...], 'content_s', 'runtime_s', 'channels', 'window_misses'}. A segment outside its
    8-12 s / 12-20 s window is always listed in window_misses; it is a violation only when windows_hard (law L-o
    made the windows targets: both readings are reported)."""
    bad, segs, seen, per_video, clips_per_channel, misses = [], [], {}, {}, {}, []
    if not CLIPS[0] <= len(lineup["clips"]) <= CLIPS[1]:
        bad.append(f"{len(lineup['clips'])} clips (needs {CLIPS[0]}-{CLIPS[1]})")
    for label, ids in segments(lineup):
        rows = [rows_by_id[i] for i in ids]
        kind = "hook" if label == "hook" else "clip"
        lo, hi = HOOK_S if kind == "hook" else CLIP_S
        dur = round(rows[-1]["end_s"] - rows[0]["start_s"], 2)
        segs.append({"segment": label, "ids": ids, "video_id": rows[0]["video_id"], "channel": rows[0]["channel"],
                     "channel_id": rows[0]["channel_id"], "duration_s": dur,
                     "layout_eligible": all(r["layout_eligible"] for r in rows),
                     "timing": sorted({r["timing"] for r in rows})})
        if len(ids) > MAX_SENTENCES:
            bad.append(f"{label}: {len(ids)} sentences > {MAX_SENTENCES}")
        if len({r["video_id"] for r in rows}) > 1:
            bad.append(f"{label}: sentences from more than one video")
        elif any(b["sentence_index"] != a["sentence_index"] + 1 for a, b in zip(rows, rows[1:])):
            bad.append(f"{label}: sentences are not consecutive ({', '.join(ids)})")
        if not rows[-1]["ends_statement"]:
            bad.append(f"{label}: does not end on a statement ({rows[-1]['text'][-40:]!r})")
        cut = [r["id"] for r in rows if not r.get("complete")]
        if cut:                      # ended by a speaker change or the transcript end, not by its own punctuation
            bad.append(f"{label}: not a whole sentence ({', '.join(cut)}: no terminal punctuation)")
        if not lo <= dur <= hi:
            misses.append(f"{label}: {dur} s outside {lo:g}-{hi:g} s")
            if windows_hard:
                bad.append(misses[-1])
        for i in ids:
            if i in seen:
                bad.append(f"{label}: sentence {i} already used by {seen[i]}")
            seen[i] = label
        per_video[rows[0]["video_id"]] = per_video.get(rows[0]["video_id"], 0) + 1
        if kind == "clip":
            clips_per_channel[rows[0]["channel_id"]] = clips_per_channel.get(rows[0]["channel_id"], 0) + 1
        for r in rows:
            alt = altcoin_terms(r["text"])
            if alt:
                bad.append(f"{label}: altcoin content in {r['id']} ({', '.join(alt)})")
    bad += [f"{n} segments from video {v} > {PER_VIDEO}" for v, n in per_video.items() if n > PER_VIDEO]
    bad += [f"{n} clips from one channel ({c}) > {CLIPS_PER_CHANNEL}" for c, n in clips_per_channel.items()
            if n > CLIPS_PER_CHANNEL]
    channels = sorted({s["channel"] for s in segs})
    if len({s["channel_id"] for s in segs}) < MIN_CHANNELS:
        bad.append(f"{len(channels)} channel(s) < {MIN_CHANNELS}")
    content = round(sum(s["duration_s"] for s in segs), 2)
    if content < MIN_CONTENT_S:
        bad.append(f"content {content} s < {MIN_CONTENT_S:g} s (runtime {content + CARD_AND_OUTRO_S:.1f} s < {MIN_RUNTIME_S:g} s)")
    return bad, {"segments": segs, "content_s": content, "runtime_s": round(content + CARD_AND_OUTRO_S, 1),
                 "channels": channels, "window_misses": misses}


def disjoint_max(lineups):
    """Indices of the largest set of line-ups that pairwise share no sentence (exhaustive; a day has <= 8)."""
    ids = [{i for _, seg in segments(lu) for i in seg} for lu in lineups]
    best = []
    for mask in range(1, 1 << len(lineups)):
        pick = [k for k in range(len(lineups)) if mask >> k & 1]
        if len(pick) > len(best) and all(not (ids[a] & ids[b]) for a in pick for b in pick if a < b):
            best = pick
    return best


def layout_survives(summary):
    """Does the line-up still satisfy the structure with only layout-eligible segments (the selector's
    layout_eligible: a has_chyron channel never supplies a clip)? (ok, why)."""
    segs = summary["segments"]
    if all(s["layout_eligible"] for s in segs):
        return True, "every segment's channel is layout-eligible"
    keep = [s for s in segs if s["layout_eligible"]]
    hook_ok = keep and keep[0]["segment"] == "hook"
    n_clips = sum(1 for s in keep if s["segment"] != "hook")
    content = sum(s["duration_s"] for s in keep)
    dead = [s["channel"] for s in segs if not s["layout_eligible"]]
    ok = bool(hook_ok) and n_clips >= CLIPS[0] and len({s["channel_id"] for s in keep}) >= MIN_CHANNELS \
        and content >= MIN_CONTENT_S
    return ok, (f"without {', '.join(sorted(set(dead)))} (not layout-eligible): "
                + ("still a legal structure" if ok else
                   f"hook {'kept' if hook_ok else 'lost'}, {n_clips} clip(s), {len({s['channel_id'] for s in keep})} "
                   f"channel(s), {content:.1f} s"))
