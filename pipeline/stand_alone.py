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
BITCOIN = re.compile(r"\b(bitcoin|btc)\b", re.I)
FIGURE = re.compile(r"\$\s?\d|\d\s?%|\bpercent\b|\b\d{1,3}(?:\s?,\s?\d{3})+\b|\b\d+(?:\s?\.\s?\d+)?\s?(?:k|thousand|million|billion)\b",
                    re.I)
CLIP_MIN_SCORE = 3.5                                           # = editorial_select.CLIP_MIN_SCORE
FILLERS = {"you", "know", "like", "i", "mean"}


def _words(text):
    """Lower-case word tokens; a contraction is reduced to its head ("we've" -> "we", "it's" -> "it")."""
    import canon                                    # the one canonical form, contraction heads (pipeline/canon.py)
    return canon.canon_tokens(text, heads=True)


def opener(kind, text, score=None, fault=None):
    """(ok, reason) for the first word of a hook or a clip."""
    ws = _words(text)
    if not ws:
        return False, "empty segment"
    w = ws[0]
    if kind == "hook":
        for group, name in ((PRONOUNS, "pronoun"), (CONJUNCTIONS, "conjunction"), (REPLY_FRAGMENTS, "reply fragment")):
            if w in group:
                return False, f"hook opens on the {name} {w!r}: nothing is heard before a hook"
        return True, f"opens on {w!r}"
    if w in CONJUNCTIONS or w in REPLY_FRAGMENTS:
        if score is None:
            return False, f"clip opens on {w!r} and no clip-scorer verdict is available (fail closed)"
        if score >= CLIP_MIN_SCORE and fault != "starts_mid_thought":
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


def check_edl(edl, rate=None, subject=("bitcoin", "btc")):
    """Every segment of an EDL in order. rate(passages) -> {pid: (score, reason, fault)} is called only for
    clips opening on a conjunction / reply fragment (the clip scorer); without it they fail closed."""
    segs = [("hook", "hook", edl["hook"])] + [(f"clip_{c['index']:02d}", "clip", c) for c in edl.get("clips", [])]
    need = [(label, s) for label, kind, s in segs if kind == "clip" and _words(s.get("text"))[:1]
            and (_words(s["text"])[0] in CONJUNCTIONS or _words(s["text"])[0] in REPLY_FRAGMENTS)]
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
        o_ok, o_why = opener(kind, s.get("text"), score, fault)
        t_ok, t_why = topical(kind, s.get("text"), prev, subject)
        rows.append({"segment": label, "channel": s.get("channel"), "first_words": " ".join((s.get("text") or "").split()[:6]),
                     "opener": {"pass": o_ok, "why": o_why}, "topic": {"pass": t_ok, "why": t_why},
                     **({"scorer": {"score": sc[0], "reason": sc[1], "fault": sc[2]}} if sc else {}),
                     "pass": o_ok and t_ok})
        prev = s.get("text")
    return {"ok": all(r["pass"] for r in rows), "rows": rows, "rate_error": rate_error, "subject": sorted(subject)}
