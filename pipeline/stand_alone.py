#!/usr/bin/env python3
"""pipeline/stand_alone.py — every segment must stand alone and belong to a Bitcoin story.

Orchestrator note 2026-11-11 08:30 ET (direction 2), after recut run 6 opened on "But I don't check it on an
hourly basis" (a hook whose pronoun has no referent) and closed on "And the NASDAQ fell even harder ...
concentrated in AI" (a Nasdaq/AI statement, context rather than a clip):
  OPENER  a hook (heard first, so nothing before it can give a pronoun its referent) may not open on a
          pronoun, a conjunction or a reply fragment. A clip may open on a conjunction or a reply fragment
          only if the clip scorer (story_semantics.rate_passages, the same criterion selection uses)
          affirms it stands alone: score >= CLIP_MIN_SCORE and no "starts_mid_thought" fault.
  TOPIC   every segment names the story's subject itself, or (a clip only) completes the previous segment's
          claim: after any leading conjunction its subject is a back-referring pronoun ("It went from above
          $81,000 ...") and it carries a price/market figure. For a Bitcoin story (its subject or headline
          names Bitcoin) the subject is Bitcoin/BTC: "And the NASDAQ fell 5.5 %" has a new subject, context
          not a clip (Bitcoin-only editorial line). For another subject (Nov 4's approved Binance hack) the
          subject's own words are the subject (a Bitcoin aside is not a clip of that story).
Deterministic first-token screen plus the existing scorer; no model decides a pass by itself."""
import re

CONJUNCTIONS = {"and", "but", "or", "so", "because", "cause", "which", "also", "plus", "then", "though",
                "although", "whereas", "nor", "yet"}          # = editorial_select.CONTINUATION_OPENERS
PRONOUNS = {"i", "me", "my", "it", "its", "this", "that", "these", "those", "they", "them", "their", "he", "him",
            "his", "she", "her", "we", "us", "our", "you", "your", "there"}
REPLY_FRAGMENTS = {"yeah", "yes", "yep", "no", "nope", "right", "exactly", "absolutely", "totally", "sure", "okay",
                   "ok", "oh", "well", "um", "uh", "agreed", "true", "correct", "indeed", "anyway", "anyways"}
BACKREF = {"it", "its", "this", "that", "these", "those", "they"}
# RULING 94 (b) (orchestrator 2026-11-14 '00:40'): a first- or second-person pronoun opener is NOT a cold-open fault
# ("I will bet you one Bitcoin that..." is a fine first line); only a third-person or demonstrative pronoun with no
# referent in the clip is, and the clip scorer judges exactly that (affirmed: it opens; else a fault, fail closed)
FIRST_SECOND = {"i", "me", "my", "we", "us", "our", "you", "your"}
THIRD = PRONOUNS - FIRST_SECOND
BITCOIN = re.compile(r"\b(bitcoin|btc)\b", re.I)
FIGURE = re.compile(r"\$\s?\d|\d\s?%|\bpercent\b|\b\d{1,3}(?:\s?,\s?\d{3})+\b|\b\d+(?:\s?\.\s?\d+)?\s?(?:k|thousand|million|billion)\b",
                    re.I)
CLIP_MIN_SCORE = 3.5                                           # = editorial_select.CLIP_MIN_SCORE
FILLERS = {"you", "know", "like", "i", "mean"}


def _words(text):
    """Lower-case word tokens; a contraction is reduced to its head ("we've" -> "we", "it's" -> "it")."""
    import canon                                    # the one canonical form, contraction heads (pipeline/canon.py)
    return canon.canon_tokens(text, heads=True)


def affirmed(score, fault, moments=False):
    """The clip scorer's affirmation, the ONE threshold: opener, trimmed_opener and the pin-stage scorer
    (stand_alone_scorer.py, order '09:58' item 56) all read it here. The story path: score >= CLIP_MIN_SCORE and no
    starts_mid_thought fault. A MOMENTS pin (ruling 60, '11:01': "bar 3.5, no fixed score for an opener word: the
    model judges the clip as spoken"): the score alone. Measured 2026-11-13: the model labels an opening "I mean" /
    "However" starts_mid_thought while scoring the clip 4 ("understood alone"), and every REFERENT_OUTSIDE clip it
    refuses scores <= 3, so the label added only an opener penalty."""
    if moments:
        return score is not None and score >= CLIP_MIN_SCORE
    return score is not None and score >= CLIP_MIN_SCORE and fault != "starts_mid_thought"


def clip_scorer(event, llm=None, moments=False):
    """The clip scorer stage_validate asks: rate(passages) -> {pid: (score, reason, fault)} on the GPU0 LocalLLM
    (gemma3:27b, temperature 0). The story path: story_semantics.rate_passages with {"underlying_event": event}. A
    MOMENTS pin (ruling 60): story_semantics.rate_alone, stand-alone only, no event. ONE code path for the render's
    validate and the pin-stage scorer (order '09:58' item 56). Without `llm` it starts the model and stops it after
    the call (validate's way); with one, the caller owns its life. An unparseable reply raises (never invented)."""
    def rate(passages):
        import story_semantics as sm
        own = llm is None
        m = sm.LocalLLM().start() if own else llm
        try:
            ratings, err = sm.rate_alone(m, passages) if moments else \
                sm.rate_passages(m, {"underlying_event": event}, passages)
        finally:
            if own:
                m.stop()
        if err:
            raise RuntimeError(f"clip scorer reply unparseable: {err}")
        return ratings
    return rate


def opener(kind, text, score=None, fault=None, moments=False):
    """(ok, reason) for the first word of a hook or a clip."""
    ws = _words(text)
    if not ws:
        return False, "empty segment"
    w = ws[0]
    if kind == "hook":
        for group, name in ((CONJUNCTIONS, "conjunction"), (REPLY_FRAGMENTS, "reply fragment")):
            if w in group:          # ruling 94 (a): only ruling 33's one-word trim variant opens (check_edl's trim rule)
                return False, f"hook opens on the {name} {w!r}: nothing is heard before a hook"
        if w in THIRD:              # ruling 94 (b): a referent the clip may not carry: the scorer judges it
            if score is None:
                return False, f"hook opens on the pronoun {w!r} and no clip-scorer verdict is available (fail closed)"
            if affirmed(score, fault, moments):
                return True, f"hook opens on {w!r}; the clip scorer affirms it stands alone ({score}, fault {fault})"
            return False, f"hook opens on {w!r}; the clip scorer does not affirm it stands alone ({score}, fault {fault})"
        return True, f"opens on {w!r}"
    if w in CONJUNCTIONS or w in REPLY_FRAGMENTS:
        if score is None:
            return False, f"clip opens on {w!r} and no clip-scorer verdict is available (fail closed)"
        if affirmed(score, fault, moments):
            return True, f"clip opens on {w!r}; the clip scorer affirms it stands alone ({score}, fault {fault})"
        return False, f"clip opens on {w!r}; the clip scorer does not affirm it stands alone ({score}, fault {fault})"
    return True, f"opens on {w!r}"


STOP = {"the", "and", "for", "with", "from", "into", "over", "under", "after", "about", "their", "this", "that",
        "spot", "price", "prices", "market", "markets", "shares", "stock", "stocks", "news", "week", "weekend"}


def subject_terms(affected_object="", headline=""):
    """The words a segment must use to be about the story. A Bitcoin story (its subject or headline names
    Bitcoin): Bitcoin/BTC. Otherwise the subject's own content words only (Heimdall batch 6: a Bitcoin aside
    is not a clip of a Binance-hack story): the affected object's, else the headline's. None at all: an EMPTY
    set, so no segment names the subject and the story fails closed (Heimdall batch 7)."""
    if BITCOIN.search(f"{affected_object} {headline}"):
        return {"bitcoin", "btc"}
    content = lambda t: {w for w in _words(t) if len(w) >= 4 and w not in STOP and not w.isdigit()}
    return content(affected_object) or content(headline)


def _mentions(text, subject):
    ws = set(_words(text))
    return sorted(w for w in subject if w in ws or (w.endswith("s") and w[:-1] in ws) or f"{w}s" in ws)


def topical(kind, text, prev_text=None, subject=("bitcoin", "btc")):
    """(ok, reason): the segment names the story subject, or a clip completes the previous segment's claim."""
    subject = set(subject)
    hit = _mentions(text, subject)
    if hit:
        return True, f"names the subject ({', '.join(hit)})"
    if kind == "hook":
        return False, f"the hook does not name the story subject ({', '.join(sorted(subject))})"
    ws = _words(text)
    k = 0
    while k < len(ws) and (ws[k] in CONJUNCTIONS or ws[k] in FILLERS - {"i"}):
        k += 1
    first = ws[k] if k < len(ws) else ""
    if prev_text and _mentions(prev_text, subject) and first in BACKREF and FIGURE.search(text or ""):
        return True, f"completes the previous segment's claim ({first!r} + a figure)"
    return False, (f"does not name the story subject ({', '.join(sorted(subject))}) and does not complete the "
                   f"previous segment's claim (it opens on {first!r}): context, not a clip")


def topical_screen(kind, text, prev_text, screen):
    """Ruling 34 (orchestrator 2026-11-13 '03:42'), moments packages only: a segment is about Bitcoin when the miner's
    about-Bitcoin screen (BTC_SCREEN, carried on the pin) matches its own words, or (a clip only) it completes the
    previous segment's claim exactly as topical() allows. The medley-level rule (one segment names Bitcoin) is
    check_edl's."""
    m = screen.search(text or "")
    if m:
        return True, f"about Bitcoin by the miner's screen ({m.group(0)!r})"
    if kind == "hook":
        return False, "the hook does not pass the miner's about-Bitcoin screen"
    ok, why = topical(kind, text, prev_text, ("bitcoin", "btc"))
    if ok:
        return ok, why
    return False, f"does not pass the miner's about-Bitcoin screen and does not complete the previous claim"


def trimmed_word(seg):
    """The leading word a segment's lock trims (ruling 33 part 2: selection_lock.trimmed_leading), else None."""
    t = (seg.get("selection_lock") or {}).get("trimmed_leading")
    return str(t.get("word") or "?") if isinstance(t, dict) else None


def trimmed_opener(word, score, fault, moments=False):
    """Ruling 33 part 2 (orchestrator 2026-11-13 '03:42'): a segment locked with ONE leading word trimmed passes only
    when the clip scorer affirms the TRIMMED text stands alone at the unchanged threshold, whatever its first word."""
    if score is None:
        return False, f"{word!r} trimmed and no clip-scorer verdict on the trimmed text (fail closed, ruling 33 part 2)"
    if affirmed(score, fault, moments):
        return True, f"{word!r} trimmed; the clip scorer affirms the trimmed text stands alone ({score}, fault {fault})"
    return False, f"{word!r} trimmed; the clip scorer does not affirm the trimmed text stands alone ({score}, fault {fault})"


def check_edl(edl, rate=None, subject=("bitcoin", "btc"), screen=None, moments=False):
    """Every segment of an EDL in order. rate(passages) -> {pid: (score, reason, fault)} is called only for
    clips opening on a conjunction / reply fragment (the clip scorer), for every segment whose lock trims a leading
    word (ruling 33 part 2, the hook included) and for a hook opening on a third-person or demonstrative pronoun
    (ruling 94 (b)); without it they fail closed.
    screen (ruling 34, a moments package's carried BTC_SCREEN, compiled): each segment's TOPIC test is the screen,
    and the medley must name Bitcoin (BITCOIN: bitcoin / btc) in at least one segment, the hook or a clip, in the
    speaker's own words. screen None: every segment names the subject, as before (the story path).
    moments (ruling 60, a moments pin): the scorer's verdict is read with affirmed(..., moments=True), the score alone."""
    segs = [("hook", "hook", edl["hook"])] + [(f"clip_{c['index']:02d}", "clip", c) for c in edl.get("clips", [])]
    need = [(label, s) for label, kind, s in segs if trimmed_word(s) or (kind == "clip" and _words(s.get("text"))[:1]
            and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS))
            or (kind == "hook" and _words(s.get("text"))[:1] and _words(s.get("text"))[0] in THIRD)]   # ruling 94 (b)
    scores, rate_error = {}, None
    if need and rate is not None:
        try:
            scores = rate([{"pid": label, "channel": s.get("channel", ""), "text": s["text"],
                            "duration": float(s.get("duration") or 0)} for label, s in need]) or {}
        except Exception as e:                                  # an unavailable scorer is no verdict
            rate_error = f"{type(e).__name__}: {e}"
    rows, prev = [], None
    for label, kind, s in segs:
        sc = scores.get(label)
        score, fault = (sc[0], sc[2]) if sc else (None, None)
        o_ok, o_why = opener(kind, s.get("text"), score, fault, moments)
        if o_ok and trimmed_word(s):                                   # ruling 33 part 2
            o_ok, o_why = trimmed_opener(trimmed_word(s), score, fault, moments)
        t_ok, t_why = topical_screen(kind, s.get("text"), prev, screen) if screen is not None else \
            topical(kind, s.get("text"), prev, subject)
        rows.append({"segment": label, "channel": s.get("channel"), "first_words": " ".join((s.get("text") or "").split()[:6]),
                     "opener": {"pass": o_ok, "why": o_why}, "topic": {"pass": t_ok, "why": t_why},
                     **({"scorer": {"score": sc[0], "reason": sc[1], "fault": sc[2]}} if sc else {}),
                     "pass": o_ok and t_ok})
        prev = s.get("text")
    out = {"ok": all(r["pass"] for r in rows), "rows": rows, "rate_error": rate_error, "subject": sorted(subject)}
    if screen is not None:                                   # ruling 34: the MEDLEY names Bitcoin, once at least
        named = [r["segment"] for (label, kind, s), r in zip(segs, rows) if BITCOIN.search(s.get("text") or "")]
        out["medley_names_bitcoin"] = {"pass": bool(named), "segments": named,
                                       "why": f"named by {', '.join(named)}" if named else
                                       "no segment names Bitcoin in the speaker's own words (ruling 34)"}
        out["screen"] = screen.pattern
        out["ok"] = out["ok"] and bool(named)
    return out
