"""RULING 67 (orchestrator 14:02 Nov 13): ATTESTED-TEXT RE-SEAL.

When the render's decode and the second recogniser AGREE on a span and the pin's text differs, the pin is re-sealed
with the attested text (law L-v: the words as spoken). The verdicts already paid for carry over, recorded as carried
with the exact diff, ONLY when every differing token is a function word or an immediate repetition of the speaker's
own words. If any differing token is a number, a name, a negation or a content word, the clip's step A (both vendors)
and the stand-alone verdict are re-judged on the attested text before the seal (not done here: such a diff is
refused). The takeaway, title and caption are re-gated only if they quote the changed words (refused here too).

The diff is the render's own (pipeline/pinned.adjudicate_lock): canon.canon_tokens of the run's decode against the
approved text, difflib.SequenceMatcher(autojunk=False) opcodes. canon.py here is byte-identical to the render's, and
critical() is the render's _lv2_critical with its lists. CPU only, no model call. Imports nothing from package.py
(package_pin, which the integrator's check imports, must never pull it in).

RULING 84 (orchestrator 20:41 Nov 13) has its own class, class_84, for the render's lock pre-check only (the
second recogniser against the lock): fillers, and ONE function word. carry_class (ruling 67's re-seal) is unchanged."""
import re
from difflib import SequenceMatcher

import canon

# pipeline/pinned.py (the render), LV2_NEGATIONS / LV2_ORDINALS / _lv2_critical, copied verbatim in behaviour
LV2_NEGATIONS = frozenset({"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "cannot", "can't",
                           "won't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "shouldn't",
                           "wouldn't", "couldn't", "hasn't", "haven't", "hadn't"})
LV2_ORDINALS = frozenset({"first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
                          "eleventh", "twelfth", "twentieth", "hundredth", "thousandth", "millionth", "billionth",
                          "half", "quarter", "double", "triple", "dozen"})
# English closed-class words: articles, demonstratives, pronouns, prepositions, conjunctions, auxiliaries and their
# contractions, wh-words. NO negation, number or ordinal is in it (those are law L-v 2's critical tokens).
FUNCTION_WORDS = frozenset("""
a an the this that these those that's this's there there's here here's
i you he she it we they me him her us them my your his its our their mine yours hers ours theirs
myself yourself himself herself itself ourselves themselves one's
i'm you're he's she's it's we're they're i've you've we've they've i'll you'll he'll she'll it'll we'll they'll
i'd you'd he'd she'd we'd they'd
in on at to of for from with by about into onto upon over under up down out off through as like than via per
and or but so because if then when while though although whether
is are was were be been being am do does did have has had will would can could shall should may might must
what which who whom whose why how where
""".split())


# RULING 84 (a): the fillers the second recogniser hears and Whisper drops, exactly the ruling's list (canon tokens)
FILLERS = frozenset(("um", "uh", "er", "ah", "mm", "hmm"))


def critical(tok, texts):
    """Law L-v 2 as the render tests it (pinned._lv2_critical): a number, a negation, or a name (in either text, a
    capitalised word that does not open a sentence; 'I' excepted). A doubtful token is critical."""
    if re.search(r"\d", tok) or tok in LV2_NEGATIONS or tok.endswith("n't") or tok in LV2_ORDINALS:
        return True
    for t in texts:
        for m in re.finditer(r"[A-Za-z][A-Za-z'’-]*", t or ""):
            w = m.group(0)
            if w.lower() == tok and w[0].isupper() and w != "I":
                before = t[:m.start()].rstrip()
                if before and before[-1] not in ".!?":
                    return True
    return False


def diff(run_text, pin_text):
    """The render's ruling-17 diff -> (run tokens, pin tokens, the non-equal opcodes (tag, a, b, c, d))."""
    r, p = canon.canon_tokens(run_text), canon.canon_tokens(pin_text)
    return r, p, [o for o in SequenceMatcher(None, r, p, autojunk=False).get_opcodes() if o[0] != "equal"]


def carry_class(r, p, op, texts):
    """RULING 67: the class of one difference -> "immediate repetition", "function word", or None (re-judge).
    Each side's tokens (the run's r[a:b], the pin's p[c:d]; one may be empty) must be an immediate repetition on that
    side (they repeat the tokens right before or right after them there: the speaker's own words said twice) or all
    function words. That holds for a delete, an insert, and a replace alike, so the class never depends on how the
    matcher aligns a repetition (audit 1400 C2). No critical token (L-v 2) is ever carried over."""
    _tag, a, b, c, d = op
    if any(critical(t, texts) for t in r[a:b] + p[c:d]):
        return None

    def repeats(x, lo, hi):
        n = hi - lo
        return n > 0 and (x[max(lo - n, 0):lo] == x[lo:hi] or x[hi:hi + n] == x[lo:hi])
    sides = ((r, a, b), (p, c, d))
    if not all(repeats(x, lo, hi) or all(t in FUNCTION_WORDS for t in x[lo:hi]) for x, lo, hi in sides):
        return None
    return "immediate repetition" if any(repeats(*s) for s in sides) else "function word"


def class_84(spoken, approved):
    """RULING 84 (orchestrator 20:41 Nov 13): the render's lock pre-check class, as the integrator's pre-check applies
    it (its message of 20:4x Nov 13), on this side's comparison: the spoken text (the second recogniser's reading)
    against the approved text. -> [{"spoken", "approved", "class"}], one per difference; a class None holds.
    1. A filler (FILLERS) inside a difference is dropped from the SPOKEN side only: class "filler". A filler on the
       approved side alone is not in the class.
    2. The fillers dropped, the texts are compared again. A number, a negation or a name on either side holds.
    3. One token against one token, both function words: "one function word". At most ONE per span; another holds.
    4. Any other substitution (both sides non-empty) holds, a 2-for-2 or 1-for-2 of function words included.
    5. An insert or a drop: ruling 67's class (carry_class), unchanged, on the filler-free spoken text."""
    texts = (spoken, approved)
    r, p, ops = diff(spoken, approved)
    drop = {i for _tag, a, b, _c, _d in ops for i in range(a, b) if r[i] in FILLERS}
    out = [{"spoken": r[i], "approved": "", "class": "filler"} for i in sorted(drop)]
    r2 = [t for i, t in enumerate(r) if i not in drop]
    one = 0
    for op in SequenceMatcher(None, r2, p, autojunk=False).get_opcodes():
        tag, a, b, c, d = op
        if tag == "equal":
            continue
        rs, ps = r2[a:b], p[c:d]
        if any(critical(t, texts) for t in rs + ps):
            k = None
        elif rs and ps:
            k = "one function word" if (len(rs) == len(ps) == 1 and rs[0] in FUNCTION_WORDS and
                                        ps[0] in FUNCTION_WORDS and one == 0) else None
            one += k is not None
        else:
            k = carry_class(r2, p, op, texts)
        out.append({"spoken": " ".join(rs), "approved": " ".join(ps), "class": k})
    return out


def reads(x, s, lo, hi):
    """The second recogniser's tokens s read x's tokens lo..hi-1 AT this position (pinned.adjudicate_lock's reads):
    they and one neighbour on each side are aligned and consecutive in s; at x's start / end nothing may precede /
    follow them in s."""
    xmap = {a + k: b + k for op, a, a2, b, _ in SequenceMatcher(None, x, s, autojunk=False).get_opcodes()
            if op == "equal" for k in range(a2 - a)}
    idx = list(range(max(lo - 1, 0), min(hi + 1, len(x))))
    if not idx or not all(i in xmap for i in idx) or not all(xmap[j] == xmap[i] + 1 for i, j in zip(idx, idx[1:])):
        return False
    return (lo > 0 or xmap[idx[0]] == 0) and (hi < len(x) or xmap[idx[-1]] == len(s) - 1)


def attested_text(pin_text, run_words):
    """The minimal edit of the approved text to the run's decode: the approved surface words wherever the tokens are
    equal, the run's own decoded words at each difference. run_words: the run's decoded words of the locked span, in
    order. Raises ValueError when a difference does not fall on whole words (fail closed). The result's canonical
    tokens equal the run decode's exactly (checked)."""
    pw = pin_text.split()
    rw = [str(w).strip() for w in run_words if str(w).strip()]
    pt = [canon.canon_tokens(w) for w in pw]
    rt = [canon.canon_tokens(w) for w in rw]
    p, r = [t for x in pt for t in x], [t for x in rt for t in x]
    if p != canon.canon_tokens(pin_text) or r != canon.canon_tokens(" ".join(rw)):
        raise ValueError("the per-word canonical tokens do not add up to the text's (fail closed)")

    def word_at(tok_lens):                              # token index -> (word index, first token of that word)
        out, k = {}, 0
        for i, n in enumerate(tok_lens):
            for j in range(n):
                out[k + j] = (i, j == 0)
            k += n
        return out, k
    pmap, pn = word_at([len(x) for x in pt])
    rmap, rn = word_at([len(x) for x in rt])

    def words(wmap, n, lo, hi, side):                  # the whole words covering tokens lo..hi-1
        if lo == hi:                                    # an insertion point must fall between two words
            if lo < n and not wmap[lo][1]:
                raise ValueError(f"a difference splits a word on the {side} side (fail closed)")
            return []
        if not wmap[lo][1] or (hi < n and not wmap[hi][1]):
            raise ValueError(f"a difference splits a word on the {side} side (fail closed)")
        return sorted({wmap[t][0] for t in range(lo, hi)})
    out = []
    for tag, c, d, a, b in SequenceMatcher(None, p, r, autojunk=False).get_opcodes():   # pin -> run
        if tag == "equal":
            out += [pw[i] for i in words(pmap, pn, c, d, "approved")]
        else:
            words(pmap, pn, c, d, "approved")
            out += [rw[i] for i in words(rmap, rn, a, b, "run")]
    text = " ".join(out)
    if canon.canon_tokens(text) != r:
        raise ValueError("the attested text's tokens are not the run decode's (fail closed)")
    return text


def quotes(lines, r, p, ops):
    """The lines (takeaway, title, caption, ...) that quote the changed words: a line holding, consecutively, the
    approved tokens of a difference with one neighbour on each side, or the run's. -> [line text]."""
    def has(text, w):
        t, n = canon.canon_tokens(text), len(w)
        return n > 0 and any(t[i:i + n] == w for i in range(len(t) - n + 1))
    hit = []
    for line in lines:
        for _, a, b, c, d in ops:
            if has(line, p[max(c - 1, 0):d + 1]) or has(line, r[max(a - 1, 0):b + 1]):
                hit.append(line)
                break
    return hit
