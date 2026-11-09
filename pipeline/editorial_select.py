#!/usr/bin/env python3
"""pipeline/editorial_select.py — transcript-first story selection for run_fresh.

LAW: titles/metadata are discovery hints; transcripts establish story identity.

Three independent scores, applied in this order:
  1. STORY IMPORTANCE      current / significant / Bitcoin-relevant
                           (local LLM ratings; the story-engine score is recorded and flagged
                           when its GPT-4o legs are unavailable — never treated as equivalent)
  2. CROSS-SOURCE COVERAGE independent channels whose transcripts are adjudicated SAME_EVENT,
                           each with verbatim-verified evidence chunk ids
  3. CLIP QUALITY          strongest complete statements inside the confirmed story cluster

Editorial universe = every enabled registry channel with a channel_id (layout approval is NOT
a filter here). Layout approval gates only which passages may become rendered clips.

Candidate stories = ranked story-engine items (all of them) + emergent transcript clusters
(bottom-up: what Bitcoin media is discussing). Every reasonable candidate is evaluated; HOLD only
when none is producible. Output: TOPIC_SELECTION.json, passages.json (the frozen select stage's
input contract, full-video seconds), sources.json.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)
sys.path.insert(0, PIPELINE_DIR)

import transcript_store as ts  # noqa: E402

STORIES_PATH = os.path.join(REPO, "data", "intelligence", "candidate_stories.json")
CHANNELS_PATH = os.path.join(PIPELINE_DIR, "channels.json")

UNIVERSE_HOURS = 72
TOPUP_MAX_WHISPER_HOURS = 8.0      # in-run acquisition for uploads the background ingest missed
MAX_CANDIDATES = 24
BTC_RELEVANCE_MIN = 3
RETRIEVAL_MIN_SIM = 0.55
MAX_ADJUDICATE_PER_STORY = 14
MIN_COVERAGE_CHANNELS = 2
MIN_LAYOUT_CHANNELS = 2            # R5: clips from >= 2 distinct channels
HOOK_MIN_S, HOOK_MAX_S = 8.0, 12.0
CLIP_MIN_S, CLIP_MAX_S = 13.0, 25.0
HOOK_MIN_SCORE, CLIP_MIN_SCORE = 4.0, 3.5
N_CLIPS = 3                        # v2f format: hook + 3 clips
MAX_VERIFIED_QUOTES_PER_VIDEO = 2  # D2 (PBX 2026-11-09): up to two verified windows per source video
DEDUPE_SIM = 0.88
V2F_VIDEO_IDS = {"RBFN4CB60To", "Pxrak-iMT0g", "QCgW8RlTu5Q"}


class NoProducibleStory(Exception):
    pass


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _recency(age_h):
    if age_h is None:
        return 0.4
    return 1.0 if age_h <= 24 else 0.7 if age_h <= 48 else 0.4 if age_h <= 72 else 0.1


def _parse_ts(s):
    """ISO-8601 timestamp -> aware UTC datetime, or None."""
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _story_published(generated_at, freshness_minutes):
    """D1: article publish time = story-engine generation time - freshness. None when either is
    missing; a missing freshness is never read as 'just published'."""
    g = _parse_ts(generated_at)
    if g is None or freshness_minutes is None:
        return None
    return (g - timedelta(minutes=float(freshness_minutes))).isoformat()


def layout_eligible(channel):
    """Any registered channel with an id is clip-eligible. Presentation safety is
    enforced later: approved channels crop; pending channels letterbox.
    """
    return bool(channel.get("channel_id"))


def story_engine_status(stories, path=STORIES_PATH):
    st = stories.get("stories", [])
    degraded = bool(st) and all(s.get("independent_corroboration", 1) == 1 and
                                s.get("unexpectedness") == 2 and s.get("tension") == 2
                                for s in st)
    return {"path": path, "generated_at": stories.get("generated_at"),
            "sha256": ts.sha256_file(path),
            "llm_legs": ("UNAVAILABLE — GPT-4o clustering/soft scoring returned defaults for every "
                         "story (OpenAI 429; xAI key absent); engine rank = recency + source quality "
                         "+ magnitude regex only") if degraded else "present"}


# ── passages (clip quality inputs) ──

# Quote-anchored windows (PBX 2026-11-06 18:03): code picks the cut, the model only scores it.
#   anchor   = the verified evidence quote, aligned to word timestamps
#   window   = exactly the sentence(s) holding the quote; never expanded or padded
#   boundary = a start must be a sentence boundary (else rejected, never trimmed or guessed)
#   dedupe   = overlapping windows of the same kind in one video collapse to the first kept
ANCHOR_MIN_RATIO = 0.85            # token-level match of quote vs aligned word span
ANCHOR_PAD_S = 30.0                # search the supporting chunks' span +/- this
CONTINUATION_OPENERS = {"and", "but", "or", "so", "because", "cause", "which", "also", "plus", "then",
                        "though", "although", "whereas", "nor", "yet"}
_TERMINAL = (".", "!", "?")


def _tok(w):
    return [t for t in re.split(r"[^a-z0-9]+", (w or "").lower().replace("’", "'").replace("'", "")) if t]


def _word_sentences(words):
    """Sentences as word-index ranges, split after terminal punctuation (same rule as
    transcript_store.sentences_from_words)."""
    out, s0 = [], 0
    for i, w in enumerate(words):
        if w["word"].rstrip().endswith(_TERMINAL):
            out.append((s0, i))
            s0 = i + 1
    if s0 < len(words):
        out.append((s0, len(words) - 1))
    return out


def align_quote(quote, words, t0, t1):
    """Locate a verified quote in word timestamps within [t0, t1]. Returns
    {"w0", "w1", "start", "end", "ratio"} or None. Never fabricates a location."""
    from difflib import SequenceMatcher
    qt = [t for w in (quote or "").split() for t in _tok(w)]
    toks = [(t, i) for i, w in enumerate(words) if t0 <= w["start"] <= t1 for t in _tok(w["word"])]
    if len(qt) < 5 or not toks:
        return None
    seq = [t for t, _ in toks]
    blk = max(SequenceMatcher(None, qt, seq, autojunk=False).get_matching_blocks(), key=lambda b: b.size)
    if blk.size < 3:
        return None
    base, best = blk.b - blk.a, None
    for s in range(max(0, base - 3), min(len(seq), base + 4)):
        for n in range(max(1, len(qt) - 3), len(qt) + 4):
            if s + n > len(seq):
                break
            r = SequenceMatcher(None, qt, seq[s:s + n], autojunk=False).ratio()
            if best is None or r > best[0] + 1e-9:
                best = (r, s, s + n - 1)
    r, s, e = best
    if r < ANCHOR_MIN_RATIO:
        return None
    w0, w1 = toks[s][1], toks[e][1]
    return {"w0": w0, "w1": w1, "start": words[w0]["start"], "end": words[w1]["end"], "ratio": round(r, 3)}


def start_is_boundary(words, sents, si):
    """A window start is a boundary only if the previous sentence ended with terminal punctuation,
    the first word opens a sentence (capital or digit) and is not a continuation conjunction."""
    w0 = sents[si][0]
    if si > 0 and not words[w0 - 1]["word"].rstrip().endswith(_TERMINAL):
        return False, "previous word has no terminal punctuation"
    first = re.sub(r"^[\"'(\[“‘$]+", "", words[w0]["word"].strip())
    if not first or not (first[0].isupper() or first[0].isdigit()):
        return False, f"starts lower-case ({words[w0]['word'].strip()!r})"
    t = _tok(first)
    if t and t[0] in CONTINUATION_OPENERS:
        return False, f"starts with continuation {first!r}"
    return True, "ok"


def anchored_window(words, sents, anchor, lo, hi):
    """PBX 2026-11-06 18:52: the window is EXACTLY the sentence(s) that hold the verified quote.
    No expansion into any sentence that does not contain the quote, no padding. Invalid if the
    duration is outside [lo, hi], the start is not a boundary, or it does not end on '.' or '!'.
    Returns (window, None) or (None, reason); the span is always reported for audit."""
    sa = next(i for i, (a, b) in enumerate(sents) if a <= anchor["w0"] <= b)
    se = next(i for i, (a, b) in enumerate(sents) if a <= anchor["w1"] <= b)
    st, en = words[sents[sa][0]]["start"], words[sents[se][1]]["end"]
    d = round(en - st, 2)
    span = {"start": st, "end": en, "duration": d,
            "first_sentence": " ".join(w["word"].strip() for w in words[sents[sa][0]:sents[sa][1] + 1]),
            "last_sentence": " ".join(w["word"].strip() for w in words[sents[se][0]:sents[se][1] + 1]),
            "n_sentences": se - sa + 1}
    ok, why = start_is_boundary(words, sents, sa)
    if not ok:
        return None, f"start rejected: {why}", span
    if d < lo:
        return None, f"quote sentence(s) {d} s < minimum {lo} s (no padding)", span
    if d > hi:
        return None, f"quote sentence(s) {d} s > maximum {hi} s", span
    if not words[sents[se][1]]["word"].rstrip().endswith((".", "!")):
        return None, "does not end on '.' or '!'", span
    text = " ".join(w["word"].strip() for w in words[sents[sa][0]:sents[se][1] + 1])
    return {**span, "text": text, "anchor_start": anchor["start"], "anchor_end": anchor["end"]}, None, span


def expanded_window(words, sents, anchor, lo, hi, on_event):
    """PBX 2026-11-06 23:45 (clips): verified adjacent expansion.
    Start on the verified quote sentence(s). While shorter than `lo`, consider the immediately next,
    then the immediately previous sentence; include one only if `on_event(text)` (the same event
    checker, run independently on that sentence) returns True. A sentence that fails closes ITS
    direction (expansion never jumps past it); the other direction is still offered to the checker
    (PBX 2026-11-07 00:25). Expansion stops when both directions are closed. A sentence that would
    push the window past `hi` also closes that direction.
    D4 (PBX 2026-11-09 01:34): `on_event` is adjacent_admissible() in production; a sentence that
    starts more than 8 s from the anchor boundary it extends, or a third sentence in one direction,
    closes that direction without a checker call.
    Accept only if lo <= duration <= hi, the start is a boundary and it ends on '.' or '!'.
    Returns (window, None, span) or (None, reason, span); span records every check for audit."""
    sa = next(i for i, (a, b) in enumerate(sents) if a <= anchor["w0"] <= b)
    se = next(i for i, (a, b) in enumerate(sents) if a <= anchor["w1"] <= b)

    def stext(i):
        return " ".join(w["word"].strip() for w in words[sents[i][0]:sents[i][1] + 1])

    def dur(a, b):
        return words[sents[b][1]]["end"] - words[sents[a][0]]["start"]

    a, b, checks, stops = sa, se, [], []
    admitted = {"next": 0, "prev": 0}
    open_dirs = ["next", "prev"]
    while dur(a, b) < lo and open_dirs:
        progressed = False
        for d in list(open_dirs):
            if dur(a, b) >= lo:
                break
            i = b + 1 if d == "next" else a - 1
            if i < 0 or i >= len(sents):
                open_dirs.remove(d)
                continue
            na, nb = (a, i) if d == "next" else (i, b)
            if dur(na, nb) > hi:
                open_dirs.remove(d)
                checks.append({"direction": d, "sentence": stext(i), "on_event": None,
                               "detail": f"would exceed {hi} s; direction closed"})
                continue
            # D4a (PBX 2026-11-09 ~02:05): content-free interjections are transparent — included in
            # the window but skipped for the (a) check, not counted toward the two-sentence cap, and
            # they do not close the direction.  The 8 s bound (b) still applies to them.
            txt_i = stext(i)
            lw_i = _lc_words(txt_i)
            if lw_i and set(lw_i) <= INTERJECTIONS:
                closed = _adjacent_gate(words, sents, sa, se, i, d, admitted)  # (b) 8 s still applies
                if closed:
                    open_dirs.remove(d)
                    checks.append({"direction": d, "sentence": txt_i, "on_event": None, "detail": closed})
                    continue
                checks.append({"direction": d, "sentence": txt_i, "on_event": None,
                               "detail": "interjection: transparent (D4a); not counted toward cap"})
                a, b, progressed = na, nb, True
                # admitted[d] NOT incremented (transparent to cap)
                continue
            closed = _adjacent_gate(words, sents, sa, se, i, d, admitted)      # D4 (b) + cap
            if closed:
                open_dirs.remove(d)
                checks.append({"direction": d, "sentence": txt_i, "on_event": None, "detail": closed})
                continue
            ok, detail = on_event(txt_i)
            checks.append({"direction": d, "sentence": txt_i, "on_event": bool(ok), "detail": detail})
            if not ok:
                open_dirs.remove(d)
                stops.append(f"{d} sentence not verified on-event ({detail})")
                continue
            a, b, progressed = na, nb, True
            admitted[d] += 1
        if not progressed:
            break
    st, en = words[sents[a][0]]["start"], words[sents[b][1]]["end"]
    d = round(en - st, 2)
    span = {"start": st, "end": en, "duration": d, "first_sentence": stext(a), "last_sentence": stext(b),
            "n_sentences": b - a + 1, "quote_sentences": [sa, se], "added_sentences": (sa - a) + (b - se),
            "expansion": checks}
    if d > hi:
        return None, f"quote sentence(s) {d} s > maximum {hi} s", span
    if d < lo:
        return None, (f"{d} s < minimum {lo} s after verified expansion"
                      + (f"; expansion stopped: {'; '.join(stops)}" if stops
                         else "; no further verified adjacent sentence fits")), span
    ok, why = start_is_boundary(words, sents, a)
    if not ok:
        return None, f"start rejected: {why}", span
    if not words[sents[b][1]]["word"].rstrip().endswith((".", "!")):
        return None, "does not end on '.' or '!'", span
    text = " ".join(w["word"].strip() for w in words[sents[a][0]:sents[b][1] + 1])
    return {**span, "text": text, "anchor_start": anchor["start"], "anchor_end": anchor["end"]}, None, span


def sentence_on_event(llm, q, text, cache=None):
    """The same event checker used for evidence (story_semantics.verify_support), run independently
    on one adjacent sentence. On-event only if SUPPORTS and free of injection markers."""
    import story_semantics as sm
    if cache is not None and text in cache:
        return cache[text]
    if sm.injection_markers(text):
        res = (False, "injection markers")
    else:
        try:
            s = sm.verify_support(llm, q, text)
            res = (s.get("support") == "SUPPORTS", f"{s.get('support')}: {s.get('reason', '')}"[:200])
        except (sm.LLMParseError, KeyError, TypeError, AttributeError) as e:
            res = (False, f"checker inconclusive: {type(e).__name__}: {e}")
    if cache is not None:
        cache[text] = res
    return res


# D4 (PBX 2026-11-09 01:34): what may join a window next to the verified anchor sentence.
ADJ_MAX_START_S = 8.0            # (b) an admitted sentence starts within 8 s of the anchor boundary it extends
ADJ_MAX_PER_DIRECTION = 2        # at most two admitted adjacent sentences per direction
BACKREF_WORDS = {"this", "that", "these", "those", "it", "its", "they", "them", "their"}   # deictic / pronoun
BACKREF_PHRASES = ("what just happened", "what happened", "the hack", "the breach")        # definite reference
# PBX ruling 2026-11-09 ~02:05: a sentence made ONLY of these interjections skips (a); (b), (c), cap still apply
INTERJECTIONS = {"oh", "ah", "wow", "yeah", "yes", "right", "okay", "mhm", "hmm", "huh", "wait", "sure",
                 "exactly", "true"}
_NOT_ENTITY = {"I", "The", "This", "That", "These", "Those", "It", "And", "But", "So", "We", "You", "They",
               "He", "She", "A", "An", "In", "On", "Of", "To", "Yeah", "Oh", "Okay", "Well", "Now", "Look"}


def _lc_words(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower().replace("’", "'"))


def _numbers(text):
    t = re.sub(r"(\d)\s+([.,])\s*(\d)", r"\1\2\3", text or "")      # whisper writes '6 .3' and '80 ,000'
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", t)}


def _anchor_entities(anchor, q):
    names = set()
    for e in q.get("entities") or []:
        if isinstance(e, dict):
            names |= {n for n in [e.get("name", "")] + list(e.get("aliases") or [])
                      if isinstance(n, str) and len(n.strip()) >= 2}
    found = {n for n in names if re.search(r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9])", anchor, re.I)}
    toks = re.findall(r"[A-Za-z][A-Za-z0-9]*", anchor)
    return found | {t for i, t in enumerate(toks) if i > 0 and t[0].isupper() and t not in _NOT_ENTITY}


def backward_reference(text, anchor, q):
    """D4 (a), deterministic: the sentence refers back to the verified event (deictic / pronoun /
    definite reference) or shares a named entity or number with the anchor. Returns what was found
    (for the audit record) or None."""
    lw = _lc_words(text)
    low = " ".join(lw)
    found = sorted(BACKREF_WORDS & set(lw))
    found += [p for p in BACKREF_PHRASES if re.search(r"\b" + re.escape(p) + r"\b", low)]
    event_nouns = {w for w in _lc_words(f"{q.get('action') or ''} {q.get('affected_object') or ''}") if len(w) >= 4}
    found += [f"the {w}" for w in sorted(event_nouns) if f"the {w}" not in found and re.search(rf"\bthe {w}\b", low)]
    found += [f"entity {e}" for e in sorted(_anchor_entities(anchor, q))
              if re.search(r"(?<![A-Za-z0-9])" + re.escape(e) + r"(?![A-Za-z0-9])", text or "", re.I)]
    found += [f"number {n}" for n in sorted(_numbers(anchor) & _numbers(text))]
    return ", ".join(found) or None


def adjacent_admissible(llm, q, anchor, text, cache=None):
    """D4: an adjacent sentence joins a window only if (a) backward_reference() finds a reference to
    the verified event or a shared entity/number (a sentence made only of INTERJECTIONS is exempt
    from (a), PBX ruling 2026-11-09) AND (c) an independent verifier answers
    story_semantics.REACTION_QUESTION with SAME_EVENT_REACTION_OR_CONSEQUENCE. NEW_SUBJECT and
    OTHER_EVENT are hard rejects. (b) (start within 8 s) and the per-direction cap are enforced by
    the window builders. Returns (admitted, detail)."""
    import story_semantics as sm
    if cache is not None and (anchor, text) in cache:
        return cache[(anchor, text)]
    if sm.injection_markers(text):
        res = (False, "injection markers")
    else:
        ref = backward_reference(text, anchor, q)
        lw = _lc_words(text)
        if not ref and lw and set(lw) <= INTERJECTIONS:
            ref = "interjection only (exempt from (a), PBX ruling 2026-11-09)"
        if not ref:
            res = (False, "no backward reference, shared entity or shared number with the anchor")
        else:
            try:
                r = sm.verify_reaction(llm, q, anchor, text)
                res = (r["label"] == sm.REACTION_OK, f"{r['label']} [{ref}]: {r.get('reason', '')}"[:240])
            except (sm.LLMParseError, KeyError, TypeError, AttributeError) as e:
                res = (False, f"checker inconclusive: {type(e).__name__}: {e}")
    if cache is not None:
        cache[(anchor, text)] = res
    return res


def _adjacent_gate(words, sents, sa, se, i, d, admitted):
    """D4 (b) + cap for candidate sentence i in direction d; returns a closing reason or None."""
    if admitted[d] >= ADJ_MAX_PER_DIRECTION:
        return f"cap: {ADJ_MAX_PER_DIRECTION} sentences already admitted {d}; direction closed"
    gap = (words[sents[i][0]]["start"] - words[sents[se][1]]["end"] if d == "next"
           else words[sents[sa][0]]["start"] - words[sents[i][0]]["start"])
    if gap > ADJ_MAX_START_S:
        return f"starts {gap:.2f} s from the anchor boundary (> {ADJ_MAX_START_S} s); direction closed"
    return None


def _anchor_text(words, sents, w0, w1):
    """Text of the verified anchor sentence(s) holding words w0..w1."""
    sa = next(i for i, (a, b) in enumerate(sents) if a <= w0 <= b)
    se = next(i for i, (a, b) in enumerate(sents) if a <= w1 <= b)
    return " ".join(w["word"].strip() for w in words[sents[sa][0]:sents[se][1] + 1])


def second_verified_quote(llm, q, v, today=""):
    """D2 (PBX 2026-11-09): a second window from the same source video needs its own verified quote.
    The same adjudication (story_semantics.adjudicate) runs independently on the video's other
    retrieved excerpts; the excerpt holding the first quote is left out, so the second quote comes
    from a different passage. It counts only under the first quote's rule: CURRENT_EVENT, verbatim
    quote from a non-flagged excerpt, valid chunk id, independent SUPPORTS.
    Returns (verdict, None) or (None, reason)."""
    import story_semantics as sm
    first = v.get("evidence_quote") or ""
    rest = [x for x in (v.get("excerpts") or []) if not sm.quote_in(first, [x.get("text", "")])]
    if not rest:
        return None, "no other retrieved excerpt"
    try:
        r = sm.adjudicate(llm, q, {"title": v.get("title", ""), "channel": v.get("channel", ""),
                                   "published_at": v.get("published_at", "-")}, rest, today=today)
    except (sm.LLMParseError, KeyError, TypeError, AttributeError, ValueError) as e:
        return None, f"second adjudication inconclusive: {type(e).__name__}: {e}"
    if not r.get("counted_as_same_event"):
        return None, (f"second quote not verified (verdict {r.get('verdict')}, support {r.get('support')}, "
                      f"quote_verified {r.get('quote_verified')})")
    return r, None


def repair_window(words, sents, win, fault, lo, hi, on_event):
    """D3 (PBX 2026-11-09): a window rated below its floor ONLY for a boundary fault is repaired once
    with the verified adjacent expansion in that direction (starts_mid_thought -> previous sentence,
    ends_mid_thought -> next sentence). Every added sentence must pass the same event checker on its
    own; a failing sentence closes the direction, which ends the repair; never past `hi`. At least
    one sentence is added, more only while that edge is still not a boundary. The repaired window
    must pass the same window rules. Returns (window, None, span) or (None, reason, span)."""
    a = next((i for i, (x, _) in enumerate(sents) if words[x]["start"] == win["start"]), None)
    b = next((i for i, (_, y) in enumerate(sents) if words[y]["end"] == win["end"]), None)
    span = {"fault": fault, "from": [win["start"], win["end"]], "expansion": []}
    if a is None or b is None:
        return None, "window is not on sentence boundaries", span
    d = "prev" if fault == "starts_mid_thought" else "next"
    sa, se = (win.get("quote_sentences") or [a, b])[:2]      # the verified anchor sentence(s)
    admitted = {"prev": sa - a, "next": b - se}              # D4 cap counts what the window already has

    def stext(i):
        return " ".join(w["word"].strip() for w in words[sents[i][0]:sents[i][1] + 1])

    def edge_ok(a, b):
        return start_is_boundary(words, sents, a)[0] if d == "prev" else \
            words[sents[b][1]]["word"].rstrip().endswith((".", "!"))

    added = 0
    while added == 0 or not edge_ok(a, b):
        i = a - 1 if d == "prev" else b + 1
        if i < 0 or i >= len(sents):
            return None, f"boundary repair: no {d} sentence", span
        na, nb = (i, b) if d == "prev" else (a, i)
        if words[sents[nb][1]]["end"] - words[sents[na][0]]["start"] > hi:
            span["expansion"].append({"direction": d, "sentence": stext(i), "on_event": None,
                                      "detail": f"would exceed {hi} s; direction closed"})
            return None, f"boundary repair: {d} sentence would exceed {hi} s", span
        # D4a: interjections are transparent in repair too
        txt_i = stext(i)
        lw_i = _lc_words(txt_i)
        if lw_i and set(lw_i) <= INTERJECTIONS:
            closed = _adjacent_gate(words, sents, sa, se, i, d, admitted)  # (b) still applies
            if closed:
                span["expansion"].append({"direction": d, "sentence": txt_i, "on_event": None, "detail": closed})
                return None, f"boundary repair: {closed}", span
            span["expansion"].append({"direction": d, "sentence": txt_i, "on_event": None,
                                      "detail": "interjection: transparent (D4a); not counted toward cap"})
            a, b = na, nb
            continue
        closed = _adjacent_gate(words, sents, sa, se, i, d, admitted)          # D4 (b) + cap
        if closed:
            span["expansion"].append({"direction": d, "sentence": txt_i, "on_event": None, "detail": closed})
            return None, f"boundary repair: {closed}", span
        ok, detail = on_event(txt_i)
        span["expansion"].append({"direction": d, "sentence": txt_i, "on_event": bool(ok), "detail": detail})
        if not ok:
            return None, f"boundary repair: {d} sentence not verified on-event ({detail})", span
        a, b, added = na, nb, added + 1
        admitted[d] += 1
    st, en = words[sents[a][0]]["start"], words[sents[b][1]]["end"]
    dd = round(en - st, 2)
    span.update(start=st, end=en, duration=dd, added_sentences=added)
    if not lo <= dd <= hi:
        return None, f"repaired window {dd} s outside {lo}-{hi} s", span
    ok, why = start_is_boundary(words, sents, a)
    if not ok:
        return None, f"repaired start rejected: {why}", span
    if not words[sents[b][1]]["word"].rstrip().endswith((".", "!")):
        return None, "repaired window does not end on '.' or '!'", span
    return {"start": st, "end": en, "duration": dd, "first_sentence": stext(a), "last_sentence": stext(b),
            "n_sentences": b - a + 1, "text": " ".join(w["word"].strip() for w in words[sents[a][0]:sents[b][1] + 1]),
            "anchor_start": win.get("anchor_start"), "anchor_end": win.get("anchor_end")}, None, span


def _form_score(text):
    from rank import _score_passage
    return _score_passage(text, [])


# ── main ──

class Checkpoint:
    """E4: atomic TOPIC_SELECTION.json checkpoints throughout evaluation."""

    def __init__(self, run_dir, rec):
        self.run_dir, self.rec, self.n = run_dir, rec, 0

    def __call__(self, phase, **progress):
        self.n += 1
        self.rec["progress"] = {"phase": phase, "checkpoint": self.n, "at": ts.now_iso(), **progress}
        _write(self.run_dir, "TOPIC_SELECTION.json", self.rec)


def _infra_error(msg):
    m = (msg or "").lower()
    return any(k in m for k in ("out of memory", "cuda", "cublas", "cudnn", "gpu0 release not proven"))


def select_story(run_dir, log=print, embedder=None, llm=None, universe_fn=None,
                 stories_path=STORIES_PATH, topup=True, now=None):
    rec = {"law": "titles/metadata are discovery hints; transcripts establish story identity",
           "started": ts.now_iso()}
    ck = Checkpoint(run_dir, rec)
    try:
        return _select_story(run_dir, rec, ck, log, embedder, llm, universe_fn, stories_path, topup, now)
    except NoProducibleStory:
        raise
    except Exception as e:
        import traceback
        rec["crashed"] = {"error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()}
        ck("crashed")
        raise


def _select_story(run_dir, rec, ck, log, embedder, llm, universe_fn, stories_path, topup, now):
    import story_semantics as sm
    from transcript_ingest import universe as ingest_universe
    t0 = time.time()
    now = now or datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    with open(CHANNELS_PATH) as f:
        registry = json.load(f)
    by_cid = {c["channel_id"]: c for c in registry if c.get("channel_id")}
    rec.update({"universe_hours": UNIVERSE_HOURS, "today": today,
                "editorial_channels": sorted(c["display_name"] for c in by_cid.values() if c.get("enabled", True)),
                "layout_eligible_channels": sorted(c["display_name"] for c in by_cid.values()
                                                   if layout_eligible(c)),
                "params": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float))}})
    ck("start")

    # 1. universe + transcripts (cache first; top-up only what background ingest has not covered)
    vids = (universe_fn or ingest_universe)(UNIVERSE_HOURS)
    vids = [v for v in vids if v["video_id"] not in V2F_VIDEO_IDS]
    budget, used, uni = TOPUP_MAX_WHISPER_HOURS * 3600, 0.0, []
    for v in sorted(vids, key=lambda v: (0 if layout_eligible(v["channel"]) else 1, v["age_h"])):
        r = ts.canonical_transcript(v["video_id"])
        status = "cached" if r else None
        if r is None and topup:
            try:
                r, status = ts.acquire(v["video_id"], rss=v["rss"], channel=v["channel"], allow_whisper=False)
                if r is None and status == "pending_whisper":
                    dur = ts.ensure_meta(v["video_id"])["duration"] or 0
                    if used + dur <= budget:
                        r, status = ts.acquire(v["video_id"], rss=v["rss"], channel=v["channel"],
                                               allow_whisper=True, try_captions=False)
                        used += dur
                    else:
                        status = "deferred_budget"
            except Exception as e:
                status = f"error:{type(e).__name__}"
        uni.append({"video_id": v["video_id"], "canonical_url": ts.canonical_url(v["video_id"]),
                    "channel": v["channel"]["display_name"], "channel_id": v["channel"]["channel_id"],
                    "title": v["rss"]["title"], "published_at": v["rss"]["published"], "age_h": v["age_h"],
                    "layout_eligible": layout_eligible(v["channel"]),
                    "transcript_status": status or "missing",
                    "transcript_method": r and r["transcript_method"], "transcript_model": r and r["transcript_model"],
                    "transcript_sha256": r and r["transcript_sha256"], "_rec": r})
    rec["universe"] = [{k: v for k, v in u.items() if k != "_rec"} for u in uni]
    rec["universe_summary"] = {"videos": len(uni), "with_transcript": sum(1 for u in uni if u["_rec"]),
                               "channels": len({u["channel_id"] for u in uni}),
                               "topup_whisper_audio_h": round(used / 3600, 2)}
    log(f"  universe: {rec['universe_summary']}")
    ts.release_whisper()
    ck("universe")

    # 2. attributed chunks + embeddings
    E = embedder or sm.Embedder()
    chunks, vecs = [], []
    for u in uni:
        if not u["_rec"]:
            continue
        cs = ts.chunks(u["_rec"])
        _, vv = E.chunk_vectors(u["_rec"], cs)
        for c in cs:
            c["age_h"], c["layout_eligible"] = u["age_h"], u["layout_eligible"]
        chunks += cs
        vecs.append(vv)
    vecs = np.vstack(vecs) if vecs else np.zeros((0, 768), np.float32)
    by_chunk = {c["chunk_id"]: c for c in chunks}
    rec["embedding_model"] = E.model_id
    rec["n_chunks"] = len(chunks)
    log(f"  chunks: {len(chunks)} from {rec['universe_summary']['with_transcript']} transcripts")

    L = llm or sm.LocalLLM().start()
    rec["llm"] = {"model": L.model, "host": L.host, "serve_env": getattr(L, "serve_env", None),
                  "attempts_per_call": sm.LLM_ATTEMPTS}
    ck("embedded")

    # 3. candidates: story engine (all) + emergent clusters with current-development evidence
    with open(stories_path) as f:
        stories = json.load(f)
    rec["story_engine"] = story_engine_status(stories, stories_path)
    cands = []
    rec["candidates"] = cands
    for s in stories.get("stories", []):
        cands.append({"origin": "story_engine", "engine_rank": s.get("rank"),
                      "engine_score": s.get("overall_score"), "headline": s.get("headline"),
                      "summary": s.get("summary"), "source_domain": s.get("source_domain"),
                      "age_h": (s.get("freshness_minutes") or 0) / 60,
                      "source_published": _story_published(stories.get("generated_at"),
                                                           s.get("freshness_minutes"))})
    emergent = []
    rec["emergent_clusters"] = emergent
    for gi, g in enumerate(sm.emergent_clusters(chunks, vecs)):
        lab = sm.label_cluster(L, chunks, vecs, g, today)
        ages = [chunks[i]["age_h"] for i in g["chunk_idx"]]
        entry = {"channels": g["channels"], "n_chunks": len(g["chunk_idx"]), "label": lab}
        if not lab.get("current_ok"):
            entry["rejected"] = ("no verified current-development evidence"
                                 if lab.get("is_specific_event") else
                                 lab.get("error") or "not a specific current event")
        else:
            cdq = lab.get("current_development_chunk_id")
            entry["current_development_evidence"] = {
                "chunk_id": cdq, "quote": lab.get("current_development_quote"),
                "channel": by_chunk.get(cdq, {}).get("channel_name"),
                "canonical_url": by_chunk.get(cdq, {}).get("canonical_url")}
            cands.append({"origin": "transcript_cluster", "headline": lab["headline"],
                          "summary": lab.get("summary", ""), "source_domain": "transcript cluster",
                          "cluster_channels": g["channels"], "cluster_chunk_ids": lab.get("excerpt_chunk_ids"),
                          "current_development_evidence": entry["current_development_evidence"],
                          "age_h": min(ages) if ages else None,
                          # D1: upload time of the video holding the verified current-development quote
                          "source_published": by_chunk.get(cdq, {}).get("published_at")})
        emergent.append(entry)
        ck("emergent", cluster=gi)
    log(f"  candidates: {len(cands)} ({sum(c['origin'] == 'transcript_cluster' for c in cands)} emergent, "
        f"{sum(1 for e in emergent if e.get('rejected'))} emergent clusters rejected)")

    # 4. STORY IMPORTANCE (+ E1 currentness gate)
    for ci, c in enumerate(cands[:MAX_CANDIDATES + len(emergent)]):
        try:
            q = sm.derive_story_query(L, c, today)
        except sm.LLMParseError as e:
            c["importance_gate"] = ["inconclusive: story-query derivation failed (LLM output unparseable)"]
            c["llm_error"] = {"error": str(e), "llm_attempts": e.attempts}
            ck("derive", candidate=ci, of=len(cands))
            continue
        c["query"] = q
        imp = {"llm_importance": q.get("importance"), "llm_bitcoin_relevance": q.get("bitcoin_relevance"),
               "is_specific_event": q.get("is_specific_event"), "model_event_date": q.get("event_date"),
               "model_event_recency": q.get("event_recency"), "recency": _recency(c.get("age_h")),
               "engine_score": c.get("engine_score"),
               "engine_score_note": rec["story_engine"]["llm_legs"] if c["origin"] == "story_engine" else None}
        try:
            imp["importance_score"] = round(0.45 * float(q.get("importance", 0)) / 5 +
                                            0.35 * float(q.get("bitcoin_relevance", 0)) / 5 +
                                            0.20 * imp["recency"], 3)
        except Exception:
            imp["importance_score"] = 0.0
        c["importance"] = imp
        gate = []
        if (q.get("bitcoin_relevance") or 0) < BTC_RELEVANCE_MIN:
            gate.append(f"bitcoin_relevance {q.get('bitcoin_relevance')} < {BTC_RELEVANCE_MIN}")
        if not q.get("is_specific_event", True):
            gate.append("not a specific event")
        # D1: publish metadata dates the event; the model date is a tiebreaker only without it
        g = sm.grounded_event_date(q, _parse_ts(c.get("source_published")), now, UNIVERSE_HOURS)
        c["event_date_grounding"] = g
        if g["model_date_discarded"]:
            log(f"  D1/E9 model date discarded ({g['model_date']['status']}): {c['headline'][:70]}")
        if g["stale"]:
            gate.append(g["stale_reason"])
        c["importance_gate"] = gate
        ck("derive", candidate=ci, of=len(cands))
    live = [c for c in cands if "query" in c and not c["importance_gate"]]
    if live:
        ev = E.encode([c["query"].get("underlying_event", c["headline"]) for c in live])
        for i, c in enumerate(live):
            for j in range(i):
                if not live[j].get("merged_into") and float(ev[i] @ ev[j]) >= DEDUPE_SIM:
                    keep, drop = (live[j], c) if live[j]["importance"]["importance_score"] >= \
                        c["importance"]["importance_score"] else (c, live[j])
                    drop["merged_into"] = keep["headline"]
    order = sorted([c for c in live if not c.get("merged_into")],
                   key=lambda c: -c["importance"]["importance_score"])
    rec["evaluation_order"] = [c["headline"] for c in order]
    ck("importance")

    # 5. CROSS-SOURCE COVERAGE (all candidates first)
    for oi, c in enumerate(order):
        q = c["query"]
        qv = E.encode(sm.query_texts(q), query=True)
        sims = (vecs @ qv.T).max(axis=1) if len(chunks) else np.zeros(0)
        pats = sm.alias_patterns(q)
        per_vid = {}
        for i, ch in enumerate(chunks):
            hits = sum(1 for p in pats if p.search(ch["text"]))
            if sims[i] >= RETRIEVAL_MIN_SIM or hits >= 2:
                per_vid.setdefault(ch["video_id"], []).append((float(sims[i]) + 0.03 * min(hits, 3), i))
        ranked_v = sorted(per_vid.items(), key=lambda kv: -max(s for s, _ in kv[1]))
        picked, seen_ch = [], set()
        for vid, lst in ranked_v:                       # channel diversity first
            ch0 = chunks[lst[0][1]]["channel_id"]
            if ch0 not in seen_ch:
                picked.append((vid, lst))
                seen_ch.add(ch0)
        for vid, lst in ranked_v:
            if len(picked) >= MAX_ADJUDICATE_PER_STORY:
                break
            if (vid, lst) not in picked:
                picked.append((vid, lst))
        picked = picked[:MAX_ADJUDICATE_PER_STORY]
        verdicts = []
        c["coverage"] = {"videos_evaluated": 0, "verdicts": verdicts, "status": "in_progress"}
        for vi, (vid, lst) in enumerate(picked):
            idx = [i for _, i in sorted(lst, reverse=True)[:4]]
            ex = [chunks[i] for i in sorted(idx, key=lambda i: chunks[i]["start"])]
            u = next(x for x in uni if x["video_id"] == vid)
            v = sm.adjudicate(L, q, {"title": u["title"], "channel": u["channel"],
                                     "published_at": u["published_at"]}, ex, today=today)
            v.update(video_id=vid, canonical_url=u["canonical_url"], channel=u["channel"],
                     channel_id=u["channel_id"], title=u["title"], published_at=u["published_at"],
                     layout_eligible=u["layout_eligible"], transcript_sha256=u["transcript_sha256"],
                     transcript_method=u["transcript_method"],
                     excerpts=[{"chunk_id": x["chunk_id"], "start": x["start"], "end": x["end"],
                                "text": x["text"]} for x in ex],
                     retrieval_score=round(max(s for s, _ in lst), 3))
            verdicts.append(v)
            c["coverage"]["videos_evaluated"] = len(verdicts)
            ck("adjudicate", candidate=oi, of=len(order), video=vi, of_videos=len(picked))
        same = [v for v in verdicts if v["counted_as_same_event"]]
        cov_ch = sorted({v["channel_id"] for v in same})
        lay_ch = sorted({v["channel_id"] for v in same if v["layout_eligible"]})
        c["coverage"].update(status="done", same_event_videos=len(same), independent_channels=len(cov_ch),
                             inconclusive=sum(1 for v in verdicts if v["verdict"] == "INCONCLUSIVE"),
                             channels=[by_cid.get(x, {}).get("display_name", x) for x in cov_ch],
                             layout_eligible_channels=[by_cid[x]["display_name"] for x in lay_ch])
        cur = sm.transcript_currentness(verdicts)            # E1/E9: transcripts decide currentness
        c["currentness"] = cur
        if c.get("event_date_grounding", {}).get("model_date_discarded"):
            c.setdefault("flags", []).append("model date discarded as hallucinated (D1/E9)")
        log(f"  [{c['importance']['importance_score']:.2f}] {c['headline'][:70]} -> coverage "
            f"{len(cov_ch)} ch ({len(lay_ch)} layout-eligible), currentness {cur['status']}")
        if cur["status"] != "CURRENT":
            c["decision"] = f"inconclusive: currentness {cur['reason']}"
        elif len(cov_ch) < MIN_COVERAGE_CHANNELS:
            c["decision"] = f"rejected: coverage {len(cov_ch)} < {MIN_COVERAGE_CHANNELS} independent channels"
        elif len(lay_ch) < MIN_LAYOUT_CHANNELS:
            c["decision"] = (f"rejected: only {len(lay_ch)} layout-eligible channel(s) with evidence "
                             f"(clips need >= {MIN_LAYOUT_CHANNELS}); editorial coverage {len(cov_ch)}")
        else:
            c["decision"] = "coverage_qualified"
        ck("coverage", candidate=oi, of=len(order))

    # 6. E5: one GPU0 swap -> word-level transcripts for every coverage-qualified candidate
    qualified = [c for c in order if c.get("decision") == "coverage_qualified"]
    need = {}
    for c in qualified:
        for v in c["coverage"]["verdicts"]:
            if v["counted_as_same_event"] and v["layout_eligible"]:
                need[v["video_id"]] = v["channel_id"]
    words, arb = {}, {"videos": sorted(need)}
    rec["gpu_arbitration"] = arb
    todo = [vid for vid in need if (ts.canonical_transcript(vid) or {}).get("transcript_method") != "whisper_words"]
    for vid in need:
        if vid not in todo:
            words[vid] = (ts.canonical_transcript(vid), "cached")
    if todo:
        try:
            arb["release"] = sm.release_gpu0_for_whisper(L, log=log)
        except RuntimeError as e:
            arb["release_error"] = str(e)
            for vid in todo:
                words[vid] = (None, f"infra: {e}")
        else:
            for vid in todo:
                r, st = ts.acquire(vid, channel=by_cid[need[vid]], allow_whisper=True, prefer_words=True)
                err = ts.LAST_ERROR.get(vid, "")
                if r is None or r.get("transcript_method") != "whisper_words":
                    words[vid] = (None, f"infra: {err}" if _infra_error(err) else f"failed: {st} {err}")
                else:
                    words[vid] = (r, st)
                ck("word_transcripts", video=vid)
            ts.release_whisper()
            arb["after_whisper"] = sm.gpu0_memory()
    arb["results"] = {vid: st for vid, (r, st) in words.items()}
    ck("word_transcripts_done")

    # 7. CLIP QUALITY
    for oi, c in enumerate(qualified):
        cq = _clip_quality(c, [v for v in c["coverage"]["verdicts"] if v["counted_as_same_event"]],
                           E, L, by_cid, words, log, today=today)
        c["clip_quality"] = cq
        c["decision"] = "producible" if cq["producible"] else (
            ("INFRA_HOLD: " if cq.get("infra") else "rejected: ") + cq["reason"])
        ck("clip_quality", candidate=oi, of=len(qualified))

    producible = [c for c in order if c.get("decision") == "producible"]
    infra = [c for c in order if str(c.get("decision", "")).startswith("INFRA_HOLD")]
    L.stop()
    if embedder is None:
        E.close()
    rec["seconds"] = round(time.time() - t0)
    if not producible:
        rec["decision"] = ("HOLD (infrastructure): no producible candidate and "
                           f"{len(infra)} candidate(s) blocked by GPU/transcription infrastructure"
                           if infra else "HOLD: no candidate is producible (see candidates[].decision)")
        ck("done")
        raise NoProducibleStory(rec["decision"])
    win = max(producible, key=lambda c: (c["importance"]["importance_score"],
                                         c["coverage"]["independent_channels"],
                                         c["clip_quality"]["mean_chosen_score"]))
    rec["selected"] = {"headline": win["headline"], "origin": win["origin"],
                       "short_label": win["query"].get("short_label"),
                       "underlying_event": win["query"].get("underlying_event"),
                       "currentness": win["currentness"],
                       "event_date_grounding": win.get("event_date_grounding"),
                       "flags": win.get("flags", []),
                       "importance": win["importance"],
                       "coverage": {k: v for k, v in win["coverage"].items() if k != "verdicts"},
                       "clip_quality": {k: v for k, v in win["clip_quality"].items() if k != "candidates"},
                       "why": ("highest story importance among producible candidates; ties broken by "
                               "coverage then clip quality"),
                       "other_producible": [c["headline"] for c in producible if c is not win],
                       "infra_held": [c["headline"] for c in infra]}
    rec["decision"] = "SELECTED"
    chosen = win["clip_quality"]["chosen"]
    _write(run_dir, "passages.json", {"story": win["query"], "passages": win["clip_quality"]["candidates"],
                                      "chosen": chosen,
                                      "channels": sorted({p["channel"] for p in chosen})})
    srcs, seen = [], set()
    for p in chosen:
        if p["video_id"] in seen:
            continue
        seen.add(p["video_id"])
        srcs.append({"video_id": p["video_id"], "channel": p["channel"], "title": p["title"],
                     "url": ts.canonical_url(p["video_id"]), "published": p["published_at"],
                     "handle": p.get("handle", ""), "tier": p.get("tier", 9),
                     "transcript_sha256": p["transcript_sha256"]})
    _write(run_dir, "sources.json", srcs)
    ck("done")
    return win["query"].get("short_label") or win["headline"], rec


def _clip_quality(c, same, E, L, by_cid, words, log, today=""):
    import story_semantics as sm
    q = c["query"]
    qv = E.encode([q.get("underlying_event", c["headline"])], query=True)[0]
    cands, infra, missing, anchors = [], [], [], []
    on_event_cache = {}
    for v in same:
        if not v["layout_eligible"]:
            continue                      # editorial evidence only; never a clip
        ch = by_cid[v["channel_id"]]
        r, st = words.get(v["video_id"], (None, "not prepared"))
        if r is None:
            (infra if str(st).startswith("infra") else missing).append((v["video_id"], st))
            continue
        ws = r.get("words") or []
        if not ws:
            anchors.append({"video_id": v["video_id"], "channel": ch["display_name"], "quote": v["evidence_quote"],
                            "result": "no word timestamps in record"})
            missing.append((v["video_id"], "no word timestamps"))
            continue
        sents = _word_sentences(ws)
        v2, why2 = second_verified_quote(L, q, v, today)          # D2: up to two verified quotes per video
        for qi, ev in enumerate([v] + ([v2] if v2 else []), 1):
            a_rec = {"video_id": v["video_id"], "channel": ch["display_name"], "quote": ev["evidence_quote"],
                     "quote_index": qi}
            if qi == 1:
                a_rec["second_quote"] = "verified" if v2 else why2
            anchors.append(a_rec)
            spans = [ts.parse_chunk_id(x)[1:] for x in ev["supporting_chunk_ids"]]
            anc = align_quote(ev["evidence_quote"], ws, max(0, min(a for a, _ in spans) - ANCHOR_PAD_S),
                              max(b for _, b in spans) + ANCHOR_PAD_S)
            if anc is None:
                a_rec["result"] = "verified quote not found in word timestamps (no window)"
                continue
            a_rec.update(anchor_start=anc["start"], anchor_end=anc["end"], match_ratio=anc["ratio"], windows={})
            anchor_text = _anchor_text(ws, sents, anc["w0"], anc["w1"])
            for lo, hi, kind in ((HOOK_MIN_S, HOOK_MAX_S, "hook"), (CLIP_MIN_S, CLIP_MAX_S, "clip")):
                # verified adjacent expansion for hooks (8-12 s) and clips (13-25 s) alike
                # (PBX 2026-11-07 03:01: hooks use the same rule and checker as clips);
                # D4: an adjacent sentence must be a reaction to / consequence of the verified event
                w, why, span = expanded_window(ws, sents, anc, lo, hi,
                                               lambda t: adjacent_admissible(L, c["query"], anchor_text, t, on_event_cache))
                a_rec.setdefault("spans", {})[kind] = {**span, "valid": w is not None, "why": why}
                if w is None:
                    a_rec["windows"][kind] = f"none: {why}"
                    continue
                dup = next((p for p in cands if p["video_id"] == v["video_id"] and p["kind"] == kind and
                            not (w["end"] <= p["start"] or w["start"] >= p["end"])), None)
                if dup:
                    a_rec["windows"][kind] = f"deduped: overlaps {dup['source_chunk_id']}"
                    continue
                a_rec["windows"][kind] = f"{w['start']:.2f}-{w['end']:.2f} ({w['duration']} s)"
                cands.append({**w, "kind": kind, "video_id": v["video_id"], "channel": ch["display_name"],
                              "channel_id": ch["channel_id"], "handle": ch.get("yt_handle", ""),
                              "tier": ch.get("tier", 9), "title": v["title"], "published_at": v["published_at"],
                              "canonical_url": v["canonical_url"], "transcript_sha256": r["transcript_sha256"],
                              "transcript_method": r["transcript_method"],
                              "anchor_quote": ev["evidence_quote"], "quote_index": qi,
                              "source_chunk_id": ts.chunk_id(v["video_id"], w["start"], w["end"])})
    base = {"infra_failures": infra, "other_failures": missing, "anchors": anchors,
            "window_rule": "hooks and clips: quote sentence(s) + verified adjacent expansion, next then previous, a failed sentence closes its direction; boundary start; overlap-deduped; code picks the cut; "
                           "D2: up to 2 independently verified quotes per video, never overlapping; "
                           "D3: a window below its floor only for a boundary fault is repaired once in that direction and re-rated"}
    if infra and len({p["channel"] for p in cands}) < MIN_LAYOUT_CHANNELS:
        return {**base, "producible": False, "infra": True, "candidates": cands, "chosen": [],
                "mean_chosen_score": 0,
                "reason": f"word-level transcription blocked by infrastructure for {[v for v, _ in infra]}"}
    if not cands:
        return {**base, "producible": False, "reason": "no quote-anchored boundary window in layout-eligible evidence",
                "candidates": [], "chosen": [], "mean_chosen_score": 0}
    pv = E.encode([p["text"] for p in cands])
    for p, vv in zip(cands, pv):
        p["relevance"] = round(float(vv @ qv), 3)
        p["form"] = _form_score(p["text"])
    pre = sorted(cands, key=lambda p: -(p["relevance"] + p["form"] / 100))
    shortlist, per = [], {}
    for p in pre:
        k = (p["video_id"], p["kind"])
        if per.get(k, 0) < 4:
            shortlist.append(p)
            per[k] = per.get(k, 0) + 1
        if len(shortlist) >= 24:
            break
    for i, p in enumerate(shortlist):
        p["pid"] = f"p{i}"
    rating_errors = []
    for b in range(0, len(shortlist), 8):
        ratings, err = sm.rate_passages(L, q, shortlist[b:b + 8])
        if err:
            rating_errors.append(err)
        for p in shortlist[b:b + 8]:
            p["clip_score"], p["clip_reason"], p["clip_fault"] = ratings.get(p["pid"], (0.0, "unrated", "unspecified"))
    # D3 (PBX 2026-11-09): below its floor ONLY for a boundary fault -> one verified repair in that
    # direction, then re-rated once. Floors unchanged; off_topic / other / unspecified never repaired.
    repairs, fixed = [], []
    for p in list(shortlist):
        floor, lo, hi = ((HOOK_MIN_SCORE, HOOK_MIN_S, HOOK_MAX_S) if p["kind"] == "hook"
                         else (CLIP_MIN_SCORE, CLIP_MIN_S, CLIP_MAX_S))
        if p["clip_score"] >= floor or p["clip_fault"] not in sm.BOUNDARY_FAULTS:
            continue
        ws = words[p["video_id"]][0]["words"]
        sents_p = _word_sentences(ws)
        qs = p.get("quote_sentences") or [None, None]
        anchor_text = (" ".join(w["word"].strip() for w in ws[sents_p[qs[0]][0]:sents_p[qs[1]][1] + 1])
                       if None not in qs else p.get("anchor_quote", ""))
        w, why, span = repair_window(ws, sents_p, p, p["clip_fault"], lo, hi,
                                     lambda t: adjacent_admissible(L, q, anchor_text, t, on_event_cache))
        rep = {"pid": p["pid"], "kind": p["kind"], "channel": p["channel"], "fault": p["clip_fault"],
               "score_before": p["clip_score"], "reason_before": p["clip_reason"], "span": span,
               "result": why or "repaired; re-rated"}
        repairs.append(rep)
        if w:
            fixed.append(({**p, **w, "pid": p["pid"] + "r",
                           "repaired_from": {"pid": p["pid"], "start": p["start"], "end": p["end"],
                                             "score": p["clip_score"], "fault": p["clip_fault"]},
                           "source_chunk_id": ts.chunk_id(p["video_id"], w["start"], w["end"])}, rep))
    if fixed:
        fv = E.encode([x["text"] for x, _ in fixed])
        for (x, _), vv in zip(fixed, fv):
            x["relevance"], x["form"] = round(float(vv @ qv), 3), _form_score(x["text"])
        ratings, err = sm.rate_passages(L, q, [x for x, _ in fixed])
        if err:
            rating_errors.append(err)
        for x, rep in fixed:
            x["clip_score"], x["clip_reason"], x["clip_fault"] = ratings.get(x["pid"], (0.0, "unrated", "unspecified"))
            rep.update(score_after=x["clip_score"], reason_after=x["clip_reason"], fault_after=x["clip_fault"])
            shortlist.append(x)
    base["rating_errors"] = rating_errors
    base["boundary_repairs"] = repairs
    hooks = sorted([p for p in shortlist if p["kind"] == "hook" and p["clip_score"] >= HOOK_MIN_SCORE],
                   key=lambda p: (-p["clip_score"], -p["relevance"]))
    clips = sorted([p for p in shortlist if p["kind"] == "clip" and p["clip_score"] >= CLIP_MIN_SCORE],
                   key=lambda p: (-p["clip_score"], -p["relevance"]))
    if not hooks:
        return {**base, "producible": False, "candidates": shortlist, "chosen": [], "mean_chosen_score": 0,
                "reason": (f"no hook passage scored >= {HOOK_MIN_SCORE}" +
                           (" (clip ratings inconclusive: LLM output unparseable)" if rating_errors else ""))}
    def assemble(hook):
        chosen = [hook]
        for p in clips:
            if len(chosen) >= 1 + N_CLIPS:
                break
            if any(x["video_id"] == p["video_id"] and not (p["end"] <= x["start"] or p["start"] >= x["end"])
                   for x in chosen) or sum(1 for x in chosen[1:] if x["channel"] == p["channel"]) >= 2 \
                    or sum(1 for x in chosen if x["video_id"] == p["video_id"]) >= MAX_VERIFIED_QUOTES_PER_VIDEO:
                continue                                  # overlap (R2) / per-channel cap / D2 per-video cap
            chosen.append(p)
        return chosen

    # hooks in score order; the first whose non-overlapping set is producible wins (a hook must not
    # consume the only qualifying clip of a channel). Falls back to the top hook for the record.
    chosen = None
    for h in hooks:
        trial = assemble(h)
        if len(trial) >= 3 and len({p["channel"] for p in trial}) >= MIN_LAYOUT_CHANNELS:
            chosen = trial
            break
    chosen = chosen or assemble(hooks[0])
    chans = {p["channel"] for p in chosen}
    if len(chosen) < 3 or len(chans) < MIN_LAYOUT_CHANNELS:
        return {**base, "producible": False, "candidates": shortlist, "chosen": [], "mean_chosen_score": 0,
                "infra": bool(infra),
                "reason": f"clip quality: {len(chosen) - 1} usable clips across {len(chans)} channel(s)" +
                          (f"; infrastructure-blocked videos {[v for v, _ in infra]}" if infra else "")}
    out = []
    for p in chosen:   # select_passages input contract (full-video seconds)
        out.append({"video_id": p["video_id"], "channel": p["channel"], "handle": p["handle"],
                    "title": p["title"], "tier": p["tier"], "start": round(p["start"], 2),
                    "end": round(p["end"], 2), "text": p["text"], "duration": p["duration"],
                    "score": round(p["clip_score"] * 20 + p["relevance"], 2),
                    "clip_score": p["clip_score"], "relevance": p["relevance"],
                    "published_at": p["published_at"], "canonical_url": p["canonical_url"],
                    "transcript_sha256": p["transcript_sha256"], "source_chunk_id": p["source_chunk_id"]})
    return {**base, "producible": True, "reason": "ok", "candidates": shortlist, "chosen": out,
            "mean_chosen_score": round(sum(p["clip_score"] for p in chosen) / len(chosen), 2),
            "channels": sorted(chans)}


def _write(run_dir, name, obj):
    p = os.path.join(run_dir, name)
    with open(p + ".tmp", "w") as f:
        json.dump(obj, f, indent=1, default=str, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(p + ".tmp", p)
