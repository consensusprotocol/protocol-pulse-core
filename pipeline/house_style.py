#!/usr/bin/env python3
"""pipeline/house_style.py — ORCHESTRATOR RULING 6 (22:40 ET Nov 12): the HOUSE STYLE of the text a viewer reads or
hears. That is the TITLE, the CAPTION and the TAKEAWAY (the one VO line); a BRIDGE / INTRO gets the rules shared by every
surface.

PBX's standing copy rules: lowercase, no hashtags, no em-dashes, no emoji clutter, no AI-sounding phrasing, no hedging.

A deterministic lint, no model:
- lint(slot, text) -> [violation];
- lint_lines(lines) lints a package's lines;
- PROMPT_RULES tells the writer the same rules, built from the same constants so the two never drift.

Each violation is {"slot", "rule": "STYLE", "detail": "<rule id>: <the offending words>"}, one per rule id.

It is a gate on the writer's text BESIDE the VO-fidelity and context gates (L-q / L-t), never instead of them.

Decisions the ruling leaves open:
- the caption's "short" is CAPTION_MAX_WORDS (24);
- a period after a one-letter abbreviation ("u.s.") ends no sentence;
- money words match as STEMS on purpose ("investigation" trips invest\\w*);
- "May" the month trips the hedge "may";
- a title's first-word contraction ("It's", "That's") is not a possessive.
"""
import re

STYLE_SLOTS = ("title", "caption", "takeaway", "bridge", "intro")   # "bridge_1" etc. and "intro" use the bridge rules

# every surface
HEDGES = ("may", "might", "could be", "perhaps", "possibly", "arguably")
AI_PHRASES = ("it's worth noting", "it is worth noting", "delve", "delves", "delving", "tapestry", "testament to",
              "in today's world", "ever-evolving", "game-changer", "navigate the")
EM_DASHES = ("—", "–", " -- ")                         # em-dash, en-dash, the typed double hyphen
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U0001F1E6-\U0001F1FF☀-➿⭐⭕️]")
HASHTAG_RE = re.compile(r"#\w")

# caption
CAPTION_MAX_SENTENCES = 2
CAPTION_MAX_WORDS = 24             # the builder's reading of "one or two SHORT sentences"
SELF_REFERENCE = ("this medley", "this video", "this clip", "these clips", "builds toward", "this montage")
MONEY_PATTERNS = (r"opportunit\w*", r"invest\w*", r"profit\w*", r"get\s+rich", r"to\s+the\s+moon", r"buy\s+the\s+dip",
                  r"financial\s+advice")   # stems on purpose: "opportunity"/"invest"-style words in any form

# title
TITLE_MAX_WORDS = 8
CONTRACTIONS = ("it's", "that's", "what's", "here's", "there's", "who's", "let's", "he's", "she's", "where's", "how's",
                "why's")          # a first word that ends in 's but is not a possessive

# takeaway
TAKEAWAY_MAX_WORDS = 20
TAKEAWAY_OPENERS = ("what stands out", "it's worth noting", "ultimately", "in the end")
WHICH_MAKES_RE = re.compile(r"\bwhich\s+makes\b", re.I)
STYLE_REFERENCE = ("No ruler. Just rules nobody gets to bend. That's the idea, and it's the part most people still miss "
                   "when they look at Bitcoin.")   # the line PBX appreciated (24 words; the 20-word cap is for new lines)

RULE_IDS = ("hashtag", "em-dash", "emoji", "hedge", "ai-phrasing",
            "caption-lowercase", "caption-sentences", "caption-words", "self-reference", "money-word",
            "title-words", "title-possessive",
            "takeaway-words", "takeaway-opener", "which-makes")


def _norm(text):
    """Curly apostrophes read as straight ones, so "it’s worth noting" is caught as "it's worth noting"."""
    return (text or "").replace("’", "'").replace("‘", "'")


def _phrase_re(phrase):
    """A word-bounded, case-insensitive pattern for a phrase; any run of spaces between its words."""
    return re.compile(r"\b" + r"\s+".join(re.escape(w) for w in phrase.split()) + r"\b", re.I)


_HEDGE_RES = [(h, _phrase_re(h)) for h in HEDGES]
_AI_RES = [(p, _phrase_re(p)) for p in AI_PHRASES]
_SELF_RES = [(p, _phrase_re(p)) for p in SELF_REFERENCE]
_MONEY_RES = [(p, re.compile(r"\b" + p + r"\b", re.I)) for p in MONEY_PATTERNS]
_OPENER_RES = [(o, re.compile(r"^\W*" + r"\s+".join(re.escape(w) for w in o.split()) + r"\b", re.I))
               for o in TAKEAWAY_OPENERS]
_END_RE = re.compile(r"[.!?]['\")\]]*$")
_ABBREV_RE = re.compile(r"(\w\.)+['\")\]]*")


def words(text):
    return len((text or "").split())


def sentence_count(text):
    """Sentences = tokens that end a sentence ('.', '!', '?', then closing quotes or brackets), not counting a
    one-letter abbreviation ("u.s.", "e.g."); a last sentence without final punctuation still counts."""
    toks = (text or "").split()
    n = sum(1 for t in toks if _END_RE.search(t) and not _ABBREV_RE.fullmatch(t))
    if toks and not _END_RE.search(toks[-1]):
        n += 1
    return max(n, 1) if toks else 0


def _found(res, text):
    return [name for name, rx in res if rx.search(text)]


def lint(slot, text):
    """The house style of one line -> [{"slot", "rule": "STYLE", "detail": "<rule id>: <the offending words>"}], one
    violation per broken rule. slot: "title", "caption", "takeaway", "intro" or "bridge*" (the bridge rules)."""
    kind = "bridge" if slot == "intro" or slot.startswith("bridge") else slot
    if kind not in ("title", "caption", "takeaway", "bridge"):
        raise ValueError(f"house_style.lint: unknown slot {slot!r}")
    t = _norm(text)
    out = []

    def v(rule, why):
        out.append({"slot": slot, "rule": "STYLE", "detail": f"{rule}: {why}"})

    # every surface
    tags = re.findall(r"#\w+", t)
    if tags:
        v("hashtag", ", ".join(repr(x) for x in tags))
    dashes = [d for d in EM_DASHES if d in t]
    if dashes:
        v("em-dash", ", ".join(repr(d.strip() or d) for d in dashes) + " (use a period or a comma)")
    emo = EMOJI_RE.findall(t)
    if emo:
        v("emoji", ", ".join(repr(e) for e in emo))
    hedges = _found(_HEDGE_RES, t)
    if hedges:
        v("hedge", ", ".join(repr(h) for h in hedges) + " (say it plainly or not at all)")
    ai = _found(_AI_RES, t)
    if ai:
        v("ai-phrasing", ", ".join(repr(p) for p in ai))

    if kind == "caption":
        if t != t.lower():
            upper = [w for w in t.split() if w != w.lower()]
            v("caption-lowercase", "capitals in " + ", ".join(repr(w) for w in upper[:5]) + " (all lowercase, names too)")
        n = sentence_count(t)
        if n > CAPTION_MAX_SENTENCES:
            v("caption-sentences", f"{n} sentences (at most {CAPTION_MAX_SENTENCES})")
        if words(t) > CAPTION_MAX_WORDS:
            v("caption-words", f"{words(t)} words (at most {CAPTION_MAX_WORDS})")
        selfref = _found(_SELF_RES, t)
        if selfref:
            v("self-reference", ", ".join(repr(p) for p in selfref) + " (never talk about the video itself)")
        money = [m.group(0) for _, rx in _MONEY_RES for m in [rx.search(t)] if m]
        if money:
            v("money-word", ", ".join(repr(m) for m in money))
    elif kind == "title":
        if words(t) > TITLE_MAX_WORDS:
            v("title-words", f"{words(t)} words (at most {TITLE_MAX_WORDS})")
        first = t.split()[0] if t.split() else ""
        tok = re.sub(r"^\W+|[^\w']+$", "", first).lower()
        if re.fullmatch(r"[\w-]+'s|[\w-]+s'", tok) and tok not in CONTRACTIONS:
            v("title-possessive", f"opens with the possessive {first!r} (say the thing: 'The market no government owns')")
    elif kind == "takeaway":
        if words(t) > TAKEAWAY_MAX_WORDS:
            v("takeaway-words", f"{words(t)} words (at most {TAKEAWAY_MAX_WORDS})")
        opener = _found(_OPENER_RES, t)
        if opener:
            v("takeaway-opener", f"opens with {opener[0]!r} (make the point; no throat-clearing)")
        if WHICH_MAKES_RE.search(t):
            v("which-makes", "a 'which makes ...' clause (end the sentence; say the point in the next one)")
    return out


def lint_lines(lines):
    """The house style of a package's lines ([{"slot", "text", ...}]): every title, caption, takeaway, intro and
    bridge* line, each violation under the line's own slot; other slots are not text a viewer gets."""
    out = []
    for ln in lines or []:
        slot = ln.get("slot") or ""
        if slot in STYLE_SLOTS or slot.startswith("bridge"):
            out += lint(slot, ln.get("text") or "")
    return out


PROMPT_RULES = (
    "HOUSE STYLE (PBX's standing copy rules; a line that breaks one is rejected):\n"
    f"- Everywhere: no hashtags; no em-dash or en-dash (use a period or a comma); no emoji; no hedging words "
    f"({', '.join(HEDGES)}); no AI-sounding phrasing ({', '.join(AI_PHRASES)}).\n"
    f"- CAPTION: all lowercase, names too; one or two short sentences, at most {CAPTION_MAX_WORDS} words in all; never "
    f"talk about the video itself ({', '.join(SELF_REFERENCE)}); no money words (opportunity, invest, profit, get "
    f"rich, to the moon, buy the dip, financial advice).\n"
    f"- TITLE: at most {TITLE_MAX_WORDS} words, plain; never open with a possessive (not \"Bitcoin's overlooked value "
    f"comes from ...\" but \"The market no government owns\").\n"
    f"- TAKEAWAY: at most {TAKEAWAY_MAX_WORDS} words in short declarative sentences: a point, not a summary; never "
    f"open with " + ", ".join(f'"{o}"' for o in TAKEAWAY_OPENERS) + "; no \"which makes ...\" clause.\n"
    f"- PBX MAX's voice, for its rhythm, never its words: \"{STYLE_REFERENCE}\"")
