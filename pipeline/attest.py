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
second recogniser against the lock): fillers, and ONE function word. carry_class (ruling 67's re-seal) is unchanged.

RULING 131 (orchestrator 08:25 ET Nov 17) has its own re-check, class_131: (A) per differing pair of the render's lock,
two of the three readings (the approved text, the run's decode, the second recogniser) decide it and the sealed text
takes that reading, at least 3 tokens from both cut edges; never a number, a name or a negation; all three different
holds. (B) a currency symbol is formatting (canon.dollars_after_number, G18's one tolerance). It re-runs the render's own
steps on the three readings the lock records and never trusts the record's own classes.

RULING 135 (orchestrator 10:50 ET Nov 17), THE COMPARISON CANON: "differences of spelling are not differences of
speech". A differing pair whose two sides are the same words by canon.same_words (case, punctuation and apostrophes
ignored; segmentation ignored, names too; the closed list of spoken reductions; non-lexical tokens, fillers and a stray
single consonant, left out; a digit or a different single letter still differs) is no difference: dropped right after
the currency pairs in class_131 (as the render's lock drops it before the critical check and the vote) and before any
class in class_84 (as ruling 72's comparison drops it). The sealed text keeps the approved words there."""
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
    """Law L-v 2 / ruling 143 (1)'s MATERIAL word as the render tests it (pinned._lv2_critical): a number, a negation,
    a name (in either text, a capitalised word that does not open a sentence; 'I' excepted) or a ticker (in either
    text, a word of two or more capitals, wherever it stands: 'IBIT'; the integrator's batch 113). A doubtful token is
    critical."""
    if re.search(r"\d", tok) or tok in LV2_NEGATIONS or tok.endswith("n't") or tok in LV2_ORDINALS:
        return True
    for t in texts:
        for m in re.finditer(r"[A-Za-z][A-Za-z'’-]*", t or ""):
            w = m.group(0)
            if w.lower() == tok and w[0].isupper() and w != "I":
                before = t[:m.start()].rstrip()
                if (before and before[-1] not in ".!?") or (len(w) >= 2 and w.isupper()):
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


def class_84(spoken, approved, approved_tokens=None):
    """RULING 84 (orchestrator 20:41 Nov 13): the render's lock pre-check class, as the integrator's pre-check applies
    it (its message of 20:4x Nov 13), on this side's comparison: the spoken text (the second recogniser's reading)
    against the approved text. -> [{"spoken", "approved", "class"}], one per difference; a class None holds.
    1. A filler (FILLERS) inside a difference is dropped from the SPOKEN side only: class "filler". A filler on the
       approved side alone is not in the class.
    2. The fillers dropped, the texts are compared again. A number, a negation or a name on either side holds.
    3. One token against one token, both function words: "one function word". At most ONE per span; another holds.
    4. Any other substitution (both sides non-empty) holds, a 2-for-2 or 1-for-2 of function words included.
    5. An insert or a drop: ruling 67's class (carry_class), unchanged, on the filler-free spoken text.
    approved_tokens (RULING 148 (3)): the approved side's canon tokens as they are (class_131's merged reading), never
    tokenised again from a joined string: canon reads digits, a space and three digits as one number ('24 7 365' ->
    ['24', '7365']), so a re-read join can differ from its own tokens (build 149: Yahoo Finance f0a51c45 held on '7 365'
    against '7365', which the render's lock adopts). approved stays the text the critical-word test reads."""
    texts = (spoken, approved)
    if approved_tokens is None:
        r, p, ops = diff(spoken, approved)
    else:
        r, p = canon.canon_tokens(spoken), list(approved_tokens)
        ops = [o for o in SequenceMatcher(None, r, p, autojunk=False).get_opcodes() if o[0] != "equal"]
    drop = {i for _tag, a, b, _c, _d in ops for i in range(a, b) if r[i] in FILLERS}
    out = [{"spoken": r[i], "approved": "", "class": "filler"} for i in sorted(drop)]
    r2 = [t for i, t in enumerate(r) if i not in drop]
    one = 0
    for op in SequenceMatcher(None, r2, p, autojunk=False).get_opcodes():
        tag, a, b, c, d = op
        if tag == "equal":
            continue
        rs, ps = r2[a:b], p[c:d]
        if canon.same_words(rs, ps, stray="x"):          # RULING 135: spelling only; a lone consonant is a stray
            #   sound only on the spoken side (the second recogniser's reading, as ruling 72's comparison passes it)
            out.append({"spoken": " ".join(rs), "approved": " ".join(ps), "class": "spelling only (ruling 135)"})
            continue
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


# RULING 131 (orchestrator 08:25 ET Nov 17): the render's lock records a two-of-three adjudication under this rule (the
# integrator's message of 08:2x Nov 17: lock["adjudication"]["rule"] "ruling 131 (A) (orchestrator 2026-11-17
# '08:25')"); a pair takes the run's reading only at EDGE_131 tokens or more from both edges of the run's decode
RULE_131 = "ruling 131 (A)"
EDGE_131 = 3                                    # pinned.MAJORITY_EDGE


def currency_pair(r, p, op):
    """RULING 131 (B), the render's own test (pinned.adjudicate_lock): every token on the pair's non-empty side(s) is a
    'dollars' right after a number token (canon.dollars_after_number: '$2 billion' is a spoken '2 billion'); an empty
    side is vacuously so (audit 20261117_0843 C1, qwen P2)."""
    _tag, a, b, c, d = op
    return all(canon.dollars_after_number(r, i) for i in range(a, b)) and \
        all(canon.dollars_after_number(p, j) for j in range(c, d))


def edge_distance(r, p, op):
    """RULING 131 (A), as the render's lock measures it (the integrator's message of 08:4x Nov 17): min(a, len(r) - b)
    in the run decode's canon tokens r. A pair with an empty side ("delete" or "insert") inside a repetition may slide,
    since both texts stay the same ("that's why that's why": difflib may put the extra copy on either): shift -n while
    n <= the equal run before it and seq[x - n] == seq[y - n], +n while n <= the equal run after it and
    seq[x + n - 1] == seq[y + n - 1] (seq, x, y = r, a, b for a delete; p, c, d for an insert); its distance is the
    largest over the shifts (0 included). A replace never slides."""
    tag, a, b, c, d = op
    shifts = [0]
    full = SequenceMatcher(None, r, p, autojunk=False).get_opcodes()
    if tag in ("delete", "insert") and tuple(op) in full:
        k = full.index(tuple(op))
        seq, x, y = (r, a, b) if tag == "delete" else (p, c, d)
        left = full[k - 1][2] - full[k - 1][1] if k > 0 and full[k - 1][0] == "equal" else 0
        right = full[k + 1][2] - full[k + 1][1] if k + 1 < len(full) and full[k + 1][0] == "equal" else 0
        n = 1
        while n <= left and seq[x - n] == seq[y - n]:
            shifts.append(-n)
            n += 1
        n = 1
        while n <= right and seq[x + n - 1] == seq[y + n - 1]:
            shifts.append(n)
            n += 1
    return max(min(a + n, len(r) - (b + n)) for n in shifts)


def spill_trimmed(lock_tokens, s):
    """RULING 72's reading of a span, as the integrator's pre-check takes it (its lock_precheck.reading + _spill, the
    integrator's message of 08:5x Nov 17): the second recogniser's canon tokens s (its words whose midpoint lies in the
    lock's window +- 0.3 s) with the neighbours' spill trimmed: every token before the lock's first aligned token goes
    (fillers included), unless those tokens repeat the ones right after them (the speaker's own edge repeat, 'When,
    when', is kept); the end alike. -> the trimmed tokens."""
    ops = SequenceMatcher(None, lock_tokens, s, autojunk=False).get_opcodes()
    lo, hi = 0, len(s)
    if ops and ops[0][0] == "insert" and ops[0][1] == 0:
        d = ops[0][4]
        lo = next((d - n for n in range(d, 0, -1) if s[d - n:d] == s[d:d + n]), d)
    if ops and ops[-1][0] == "insert" and ops[-1][1] == len(lock_tokens):
        c = ops[-1][3]
        hi = next((c + n for n in range(len(s) - c, 0, -1) if s[c:c + n] == s[c - n:c]), c)
    return s[lo:max(lo, hi)]


def class_131(spoken, approved, adj):
    """RULING 131 (A) and (B) (orchestrator 08:25 ET Nov 17): this side's own re-check of an adoption, from the render's
    lock record (the pre-check entry's "adjudication": the FIRST lock's "run_decode", "approved", "second_recogniser",
    "pairs"), never from the record's own classes. spoken: the entry's spoken text; approved: the segment's approved
    text. Each step is the render's own (pinned.adjudicate_lock), re-run on the recorded readings:
    1. The ruling-17 diff (diff: canon tokens of the run's decode against the approved text). (B) first: a currency
       pair (currency_pair) is no difference and keeps the approved words.
    2. A number, a name or a negation in any other pair holds (law L-v 2: the render holds before any vote).
    3. Per pair (reads: the render's test of the second recogniser's reading there): it reads the approved words ->
       the approved; else it reads the run's AND edge_distance >= EDGE_131 tokens -> the run's; else (all three
       differ, or the run's too near an edge) the pair holds.
    4. The record's pairs must be exactly these (currency pairs aside), in order: the same words (canon tokens), the
       same reading taken, the same edge distance.
    5. The spoken text's canon tokens are the merged reading (the approved tokens, each run-taken pair as the run's)
       or, with ruling 72's adoptions on top, exactly the second recogniser's own reading of the span (spill_trimmed:
       the pre-check's as_spoken text); every difference from the merged reading must be in ruling 84's class
       (class_84, as today's adopt_spoken), or it holds.
    -> [{"spoken", "approved", "class", "took", "edge_distance"} (+ "why" when it holds)], one per pair in the diff's
    order, then ruling 72's differences on the merged text (took "ruling 72"), then one per failed whole-record test;
    a class None holds."""
    def held(why, **kw):
        return dict({"spoken": "", "approved": "", "took": None, "edge_distance": None}, **kw, **{"class": None},
                    why=why)
    adj = adj if isinstance(adj, dict) else {}
    run_t, pin_t, sec_t = adj.get("run_decode"), adj.get("approved"), adj.get("second_recogniser")
    if not all(isinstance(t, str) for t in (run_t, pin_t, sec_t, spoken, approved)) or \
            canon.canon_tokens(pin_t) != canon.canon_tokens(approved):
        return [held("the lock record does not hold the three readings of this segment's approved text")]
    texts = (run_t, pin_t)
    r, p, ops = diff(run_t, pin_t)
    s = canon.canon_tokens(sec_t)
    out, took_run = [], set()
    for op in ops:
        _tag, a, b, c, d = op
        row = {"spoken": " ".join(r[a:b]), "approved": " ".join(p[c:d])}
        if currency_pair(r, p, op):
            out.append(dict(row, took="currency", edge_distance=None, **{"class": "currency format (ruling 131 (B))"}))
            continue
        if canon.same_words(r[a:b], p[c:d]):            # RULING 135: dropped before the critical check and the vote
            #   (no stray side: in the lock a lone letter is a token, and the vote of three readings decides it)
            out.append(dict(row, took="spelling", edge_distance=None, **{"class": "spelling only (ruling 135)"}))
            continue
        row["edge_distance"] = edge_distance(r, p, op)
        if any(critical(t, texts) for t in r[a:b] + p[c:d]) and not canon.word_form(r[a:b], p[c:d]):   # RULING 142
            #   (2): a possessive or plural ending ('bitcoin' / "bitcoin's") goes to the vote, as the render's lock
            out.append(dict(row, took=None, **{"class": None}, why="a number, a name or a negation (law L-v 2)"))
        elif reads(p, s, c, d):
            out.append(dict(row, took="approved", **{"class": "two of three readings: the approved words"}))
        elif reads(r, s, a, b) and row["edge_distance"] >= EDGE_131:
            out.append(dict(row, took="run", **{"class": "two of three readings: as spoken"}))
            took_run.add((a, c))
        else:
            out.append(dict(row, took=None, **{"class": None}, why=(
                f"the run's reading within {EDGE_131} tokens of a cut edge" if reads(r, s, a, b) else
                "all three readings differ")))
    merged = []
    for tag, a, b, c, d in SequenceMatcher(None, r, p, autojunk=False).get_opcodes():
        merged += r[a:b] if (tag != "equal" and (a, c) in took_run) else p[c:d]
    rec = adj.get("pairs")
    theirs = [(x.get("run"), x.get("approved"), x.get("took"), x.get("edge_distance")) for x in rec] \
        if isinstance(rec, list) and all(isinstance(x, dict) for x in rec) else None
    mine = [(x["spoken"], x["approved"], x["took"], x["edge_distance"]) for x in out
            if x["took"] not in ("currency", "spelling")]           # the record keeps both apart from its pairs
    if theirs != mine:
        out.append(held(f"the lock record's pairs are not this side's: {theirs} against {mine}"[:400]))
    sp = canon.canon_tokens(spoken)
    if sp != merged and sp != spill_trimmed(merged, s):  # ruling 72 adopts only the second recogniser's own reading
        out.append(held("the spoken text is neither the merged reading nor the second recogniser's own reading of the "
                        "span (ruling 72 adopts only its reading)"))
    for x in class_84(spoken, " ".join(merged), merged):   # ruling 72 on top of the merged reading, as today; RULING
        #   148 (3): compared as its tokens, never re-read from the join ('24 7 365' would read ['24', '7365'])
        out.append(dict(x, took="ruling 72", edge_distance=None, **(
            {"why": "the spoken text differs from the merged reading outside ruling 84's class"} if x["class"] is None
            else {})))
    return out


RULE_143 = "ruling 143"
AUDIO_SHARE_MIN = 0.85     # RULING 143 (4), pinned.AUDIO_SHARE_MIN: two audio readings sharing less are the wrong audio
AUDIO_APART_MIN = 3        # ... and only when more than this many of the run decode's words are missing (pinned's)


def audio_share(x, y):
    """RULING 143 (4) as pinned.audio_share: the share of the run decode's tokens x the second reading y heard, in
    order (matched / len(x)); y's extra words (repeats, false starts, the window's spill) never lower it."""
    x, y = list(x or []), list(y or [])
    if not x or not y:
        return 0.0
    return sum(m.size for m in SequenceMatcher(None, x, y, autojunk=False).get_matching_blocks()) / len(x)


def wrong_audio(x, y):
    """RULING 143 (4) as pinned.wrong_audio: the share when under AUDIO_SHARE_MIN AND more than AUDIO_APART_MIN of the
    run decode's tokens are missing (HARD), else None (the same audio)."""
    share = audio_share(x, y)
    apart = len(list(x or [])) - round(share * len(list(x or [])))
    return share if share < AUDIO_SHARE_MIN and apart > AUDIO_APART_MIN else None


def material_pair(x, y, texts):
    """RULING 143 (1) as pinned.material_pair: a differing pair is MATERIAL when either side holds a number, a negation,
    a name, a ticker or an amount (critical); a word-form pair (ruling 142 (2)) is not. ITEM 7 (orchestrator 09:20 /
    09:35 ET Nov 24): a MEANING pair (owner_rules.meaning_pair: buy / sell, up / down, approved / rejected, million /
    billion, doubled / halved ...) is material too; class_143 and lock_precheck.decide HOLD it (meaning_swaps)."""
    return (not canon.word_form(x, y) and any(critical(t, texts) for t in list(x) + list(y))) or \
        bool(meaning_swaps(" ".join(x), " ".join(y)) != [])


def meaning_swaps(spoken, approved):
    """ITEM 7, "NO SILENT MEANING SWAP": the differing pairs of two readings (canon tokens, the ruling-17 diff) that
    put a word on ONE meaning axis with a DIFFERENT value, by the integrator's one list (owner_rules.meaning_pair,
    loaded from its file and sha as out_edge loads it) -> [[spoken words, approved words], ...] ([] when none). None
    when the rules cannot be loaded or have no meaning_pair: the caller holds (fail closed). Such a pair is never
    adopted, whatever the two ears say: transcript 'approved', both ears 'rejected' holds the clip. A SIZE pair written
    as digits after canon (size_pair: 'ten million' / 'ten billion') is one too (10:50 ET Nov 24)."""
    try:
        import out_edge as OE
        mp = OE.rules()[0].meaning_pair
    except Exception:                                  # noqa: BLE001  no rules file, or no meaning_pair in it
        return None
    s, a = canon.canon_tokens(spoken or ""), canon.canon_tokens(approved or "")
    return [[" ".join(s[i:j]), " ".join(a[k:l])] for tag, i, j, k, l in
            SequenceMatcher(None, s, a, autojunk=False).get_opcodes()
            if tag != "equal" and (mp(s[i:j], a[k:l]) or size_pair(s[i:j], a[k:l]))]


SCALES = ((10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (10 ** 3, "thousand"))


def size_of(tok):
    """ITEM 7 (orchestrator 10:50 ET Nov 24): the scale word a number is said with, read off its canon token (canon
    writes 'ten million' as '10000000', '$10B' as '10000000000'): 'trillion', 'billion', 'million', 'thousand', or ''
    under a thousand. None when the token is not a number."""
    if not re.fullmatch(r"\d+(?:\.\d+)?", tok or ""):
        return None
    v = float(tok)
    return next((w for n, w in SCALES if v >= n), "")


def size_pair(x, y):
    """ITEM 7 (10:50 ET Nov 24): a SIZE pair written as digits after canon: the two sides of a differing pair (canon
    tokens) each carry a number, said with different scale words ('ten million' / 'ten billion'; thousand / million
    / billion / trillion in general). It holds the clip like buy / sell, even when both ears agree. Numbers of one
    scale ('55,000' / '56,000') are not one: ruling 143 settles those."""
    xs = {z for z in map(size_of, x) if z is not None}
    ys = {z for z in map(size_of, y) if z is not None}
    return bool(xs and ys and xs != ys)


def class_143(spoken, approved, adj):
    """RULING 143 (orchestrator 2026-11-17 '15:55'; landed by ruling 153, 20:03 ET Nov 23): this side's own re-check of
    the render lock's settlement, from its record (the pre-check entry's "adjudication": "run_decode", "approved",
    "second_recogniser", "pairs"), never from the record's own classes. Each step is pinned.adjudicate_lock's, re-run on
    the recorded readings:
    1. The ruling-17 diff (canon tokens of the run decode against the approved text); a currency pair (ruling 131 (B))
       and a spelling-only pair (ruling 135) are no difference.
    2. HARD (4): the run decode and the second recogniser (its fillers dropped, ruling 135 (d)) sharing under
       AUDIO_SHARE_MIN of the run's words, more than AUDIO_APART_MIN apart: the wrong audio.
    3. Per pair (reads: the render's test of the second reading there): a MATERIAL pair (material_pair) takes the run
       decode's reading only when the second recogniser reads it too (the two audio readings agree: the transcript is
       corrected), else it holds; a NON-MATERIAL pair never holds: the approved reading where the second recogniser
       reads it, else the run decode's.
    4. The record's pairs must be exactly these, in order (the same words, materiality and reading taken); the render's
       fallback (the settled words cannot be written into the approved text: the run decode's text, every pair
       'run') is accepted only with every pair settled and the spoken text the run decode's.
    5. The spoken text's canon tokens are the settled reading (the approved tokens, each run-taken pair as the run's).
    -> [{"spoken", "approved", "material", "class", "took", "edge_distance"} (+ "why" when it holds)]; a class None
    holds."""
    def held(why, **kw):
        return dict({"spoken": "", "approved": "", "took": None, "edge_distance": None, "material": None}, **kw,
                    **{"class": None}, why=why)
    adj = adj if isinstance(adj, dict) else {}
    run_t, pin_t, sec_t = adj.get("run_decode"), adj.get("approved"), adj.get("second_recogniser")
    if not all(isinstance(t, str) for t in (run_t, pin_t, sec_t, spoken, approved)) or \
            canon.canon_tokens(pin_t) != canon.canon_tokens(approved):
        return [held("the lock record does not hold the three readings of this segment's approved text")]
    texts = (run_t, pin_t, sec_t)
    r, p, ops = diff(run_t, pin_t)
    s = [x for x in canon.canon_tokens(sec_t) if not canon.nonlexical(x)]
    share = wrong_audio(r, s)
    if share is not None:
        return [held(f"the run decode and the second recogniser share {share:.0%} of their words: the wrong audio "
                     f"(ruling 143 (4))")]
    out, took_run = [], set()
    for op in ops:
        _tag, a, b, c, d = op
        row = {"spoken": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "edge_distance": None}
        if currency_pair(r, p, op):
            out.append(dict(row, took="currency", material=None, **{"class": "currency format (ruling 131 (B))"}))
            continue
        if canon.same_words(r[a:b], p[c:d]):
            out.append(dict(row, took="spelling", material=None, **{"class": "spelling only (ruling 135)"}))
            continue
        material = material_pair(r[a:b], p[c:d], texts)
        pin_ok, run_ok = reads(p, s, c, d), reads(r, s, a, b)
        if meaning_swaps(" ".join(r[a:b]), " ".join(p[c:d])) != []:   # ITEM 7: a meaning swap (or no rules) holds,
            out.append(dict(row, took=None, material=True, **{"class": None},   # even when both ears agree
                            why="item 7: a meaning swap is never adopted silently (owner_rules.meaning_pair)"))
        elif material and run_ok:
            out.append(dict(row, took="run", material=True, **{"class": "ruling 143 (3): the two audio readings "
                                                                         "agree: the transcript corrected"}))
        elif material:
            out.append(dict(row, took=None, material=True, **{"class": None},
                            why="a material word (a number, a negation, a name, a ticker or an amount) on which the "
                                "two audio readings disagree (ruling 143 (3))"))
        else:
            out.append(dict(row, took="approved" if pin_ok else "run", material=False, **{"class": (
                "ruling 143 (2): a small word, the approved reading the second recogniser reads" if pin_ok else
                "ruling 143 (2): a small word, never a hold: the run decode's reading")}))
        if out[-1]["took"] == "run":
            took_run.add((a, c))
    merged = []
    for tag, a, b, c, d in SequenceMatcher(None, r, p, autojunk=False).get_opcodes():
        merged += r[a:b] if (tag != "equal" and (a, c) in took_run) else p[c:d]
    rec = adj.get("pairs")
    theirs = [(x.get("run"), x.get("approved"), x.get("material"), x.get("took")) for x in rec] \
        if isinstance(rec, list) and all(isinstance(x, dict) for x in rec) else None
    mine = [(x["spoken"], x["approved"], x["material"], x["took"]) for x in out if x["took"] not in ("currency",
                                                                                                    "spelling")]
    sp = canon.canon_tokens(spoken)
    fallback = (theirs is not None and len(theirs) == len(mine) and all(t[3] == "run" for t in theirs) and
                [t[:3] for t in theirs] == [m[:3] for m in mine] and all(m[3] is not None for m in mine) and sp == r)
    if theirs != mine and not fallback:
        out.append(held(f"the lock record's pairs are not this side's: {theirs} against {mine}"[:400]))
    if sp != merged and not fallback:
        out.append(held("the spoken text is not the settled reading (ruling 143 seals the settled reading only)"))
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
