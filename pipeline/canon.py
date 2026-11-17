#!/usr/bin/env python3
"""pipeline/canon.py — ONE canonical form for every text comparison in the pipeline (orchestrator 2026-11-11 '21:10').

Two strings that a listener would hear as the same words compare equal; a different number, a dropped word or a
different name does not. canon_tokens(text) -> the canonical word list; canon(text) -> those words joined by spaces.

  entities / unicode  'S&amp;P' = 'S&P'; curly quotes, dashes, ellipsis, nbsp folded (NFKC)
  split tokens        '$81 ,000' = '$81,000'; 'U .S.' = 'U.S.'; '1 .3' = '1.3' (a Whisper word joined with spaces)
  case, punctuation   lower-case; trailing / leading punctuation dropped; a curly apostrophe is a straight one,
                      and an apostrophe stays ("it's" and "its" are different words; heads=True gives "it")
  hyphens / dashes    split words ('well-known' = 'well known')
  numbers             one value form: '74,000' = '74000' = '74k' = 'seventy four thousand' = 'seventy-four
                      thousand'; '1.66 billion' = '$1.66B' value-wise; decimals 'one point six six' = '1.66';
                      ordinals '3rd' = 'third' = 'ord3' (never the cardinal: 'one second' != 'one two')
  currency / percent  '$40 trillion' = '40 trillion dollars' (the spoken order); '5.5%' = '5.5 percent' =
                      'five point five percent'; 'dollar' = 'dollars'; currency_free() (ruling 131 (B)) also equals
                      '$2 billion' and a spoken '2 billion' where a site asks for it (G18, the sentence lock)
  signs               '-5%' = 'minus 5 percent', '+5%' = 'plus 5 percent' (GPT-cut F04: -5% != +5%); a hyphen
                      between words or a range ('2026-11', '74-75') is not a sign, nor one right after a number
                      and a space before a digit ('24 -7, 365' = '24/7/365', ruling 142 (1))
Every comparison site (quote verification, selection anchors, edge words, G3b, G18, sign-off names, ledger
statements) goes through this module; pipeline/test_canon.py fails any site that compares text another way.
"""
import html
import re
import unicodedata
from decimal import Decimal, InvalidOperation

_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
_SCALES = {"hundred": 100, "thousand": 10 ** 3, "million": 10 ** 6, "billion": 10 ** 9, "trillion": 10 ** 12}
_SUFFIX = {"k": 10 ** 3, "m": 10 ** 6, "mn": 10 ** 6, "b": 10 ** 9, "bn": 10 ** 9, "t": 10 ** 12, "tn": 10 ** 12}
# US retirement plans are NAMES: '401k' = '401(k)' (tokenised '401', 'k') is never 401000 (L-k: a different number never
# compares equal; the 2026-11-14 pre-check finding). With a '$' before it, '$401k' stays the amount $401,000.
_PLANS = ("401k", "403b", "457b")
_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
        "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
        "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
        "thirtieth": 30, "fortieth": 40, "fiftieth": 50, "sixtieth": 60, "seventieth": 70, "eightieth": 80,
        "ninetieth": 90, "hundredth": 100, "thousandth": 1000}
_FOLD = str.maketrans({"‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'", "´": "'",
                       "`": "'", "“": '"', "”": '"', "„": '"', "″": '"', "‐": "-",
                       "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-", "−": " minus ",
                       "…": "...", " ": " ", " ": " ", " ": " "})
_SPLIT = re.compile(r"\s+(?=[.,][0-9A-Za-z])")            # '$81 ,000', 'U .S.': one written word
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}\b)")
_SPACED_THOUSANDS = re.compile(r"(?<![\d.,])(\d{1,3}(?:\d{3})*)\s+(\d{3})(?!\d|[.,]\d)")   # chained: '1 000 000'   # '74 000', '74 000.'; not '74 000.5'
_NUM = re.compile(r"^(\d+(?:\.\d+)?)(k|mn|m|bn|b|tn|t)?$")
_ORDNUM = re.compile(r"^(\d+)(st|nd|rd|th)$")
_TOKEN = re.compile(r"\$|%|[a-z0-9]+(?:[.'][a-z0-9]+)*")


def _value(d):
    """A Decimal as the one canonical number string: '74000', '1.66', '5.5'."""
    d = d.normalize()
    return str(int(d)) if d == d.to_integral_value() else format(d, "f")


def fold(text):
    """The character-level part of the canonical form, as text: entities decoded, unicode folded, split tokens
    joined, thousands separators dropped, lower-case (for sites with their own word rules on top, e.g.
    stand_alone's contraction heads)."""
    t = unicodedata.normalize("NFKC", html.unescape(text or "")).translate(_FOLD)
    t = _SPLIT.sub("", t)
    while True:                                         # '74 000', '1 000 000' (to a fixpoint: claude-fable #5)
        t2 = _SPACED_THOUSANDS.sub(r"\1\2", t)
        if t2 == t:
            break
        t = t2
    t = _THOUSANDS.sub("", t)
    return t.lower()


_SIGN = re.compile(r"(?<![\w.,$%])-(?=\$?\d)")             # '-5%', '(-$40M)': a sign, not a hyphen or a range
_SIGN_SPACED = re.compile(r"(^|[^\d\s.,%]\s*)-\s+(?=\$?\d)")   # '- 5%', 'is - 5%' (cycle-2 #6); '70 - 75' is a range
_PLUS = re.compile(r"\+\s*(?=\$?\d)")                         # '+5%', '+ 5%': a plus is never a hyphen
_CUR_SIGN = re.compile(r"\$\s*([-+])\s*(?=\d)")                # '$-5', '$+5': the sign after the currency
_NUM_HYPHEN = re.compile(r"(\d\s+)-(?=\d)")    # ruling 142 (1): '24 -7' after a number and a space: never a sign


def _prepare(text):
    t = fold(text).replace("\u2212", " minus ")       # (fold maps U+2212 itself; kept for safety)
    t = _NUM_HYPHEN.sub(r"\1", t)                    # ruling 142 (1): '24 -7, 365' reads '24 7 365', as '24/7/365'
    t = _CUR_SIGN.sub(lambda m: (" minus $" if m.group(1) == "-" else " plus $"), t)
    t = _PLUS.sub(" plus ", t)
    t = _SIGN_SPACED.sub(lambda m: m.group(1) + " minus ", t)
    t = _SIGN.sub(" minus ", t)                        # GPT-cut F04 / audit #6: -5% != +5%, '- 5%' != '+ 5%'
    return _TOKEN.findall(t.replace("-", " ").replace("_", " "))


def _words_number(toks, i):
    """Parse a spoken number at toks[i] ('seventy four thousand', 'one point six six', 'a hundred').
    Returns (Decimal, next index) or None. Scales strictly DESCEND ('five thousand and six thousand' is two numbers,
    not 11000; 'one hundred and two hundred' is 100 and 200: claude-fable cycle 2 F2): a scale that cannot apply
    ends the number at the last completed scale group (the 'and' before it stays a word)."""
    total, cur, j, seen, last = Decimal(0), Decimal(0), i, False, None
    last_scale, mark = None, None                 # mark: (total, cur, j) right after the last scale word
    while j < len(toks):
        w = toks[j]
        if w in _UNITS:
            if last == "unit" or (last == "tens" and _UNITS[w] >= 10):       # 'three two', 'twenty eleven': two numbers
                break
            cur += _UNITS[w]
            last = "unit"
        elif w in _TENS:
            if last in ("unit", "tens"):                  # 'twenty twenty', 'five twenty': two numbers
                break
            cur += _TENS[w]
            last = "tens"
        elif w in _SCALES and (seen or w == "hundred"):
            if w == "hundred":
                if cur >= 100:                            # 'one hundred and two hundred': a second number
                    if mark:
                        total, cur, j = mark
                    break
                cur = (cur or 1) * 100
            else:
                if last_scale is not None and _SCALES[w] >= last_scale:   # 'five thousand and six thousand'
                    if mark:
                        total, cur, j = mark
                    break
                total, cur = total + (cur or 1) * _SCALES[w], Decimal(0)
                last_scale = _SCALES[w]
            last = "scale"
            seen, j = True, j + 1
            mark = (total, cur, j)
            continue
        elif w == "a" and j + 1 < len(toks) and toks[j + 1] in _SCALES and not seen:
            cur, last = Decimal(1), "unit"
        elif w == "and" and last == "scale" and j + 1 < len(toks) and (toks[j + 1] in _UNITS or toks[j + 1] in _TENS):
            pass                               # 'one hundred and two'; never 'one and two' (GPT audit #5)
        else:
            break
        seen, j = True, j + 1
    if not seen:
        return None
    value = total + cur
    if j + 1 < len(toks) and toks[j] == "point" and toks[j + 1] in _UNITS:      # 'one point six six'
        digits = []
        j += 1
        while j < len(toks) and toks[j] in _UNITS and _UNITS[toks[j]] < 10:
            digits.append(str(_UNITS[toks[j]]))
            j += 1
        value = Decimal(f"{int(value)}.{''.join(digits)}")
    return value, j


def _canon_seq(trips, heads=False):
    """The one state machine: (prepared token, first word, last word) -> (canonical token, first word, last word).
    A number phrase or an amount spans every word it consumed (GPT audit #4: 'seventy four thousand' -> 74000
    spans 'seventy' .. 'thousand', so a lock ending on it ends on 'thousand')."""
    toks = [t for t, _, _ in trips]
    out, i, owed = [], 0, None                     # owed: the span of a '$' that still owes 'dollars'
    while i < len(toks):
        t, own = toks[i], (trips[i][1], trips[i][2])
        if t == "$":
            if owed is not None:
                out.append(("dollars",) + owed)
            owed, i = own, i + 1
            continue
        if t == "%":
            out.append(("percent",) + own)
            i += 1
            continue
        num, s0 = None, i
        plan = t if t in _PLANS else (t + toks[i + 1] if i + 1 < len(toks) and len(toks[i + 1]) == 1
                                      and t + toks[i + 1] in _PLANS else None)     # '401', 'k': only the letter
        if plan is not None and owed is None:        # a plan's name, one token over every word it spans
            last = i if plan == t else i + 1
            out.append((plan, trips[i][1], trips[last][2]))
            i = last + 1
            continue
        m = _NUM.match(t)
        if m:
            try:
                num = Decimal(m.group(1)) * (_SUFFIX[m.group(2)] if m.group(2) else 1)
            except InvalidOperation:
                num = None
            i += 1
        elif _ORDNUM.match(t) or t in _ORD:             # an ordinal is its own token: '3rd' = 'third' = 'ord3',
            n = int(_ORDNUM.match(t).group(1)) if _ORDNUM.match(t) else _ORD[t]   # never the cardinal 3
            out.append((f"ord{n}",) + own)              # ('one second' != 'one two': claude-fable audit #5)
            if owed is not None:
                out.append(("dollars",) + owed)
                owed = None
            i += 1
            continue
        else:
            parsed = _words_number(toks, i)
            if parsed:
                num, i = parsed
                tail = _ORD.get(toks[i]) if i < len(toks) else None
                if tail is not None and num == num.to_integral_value() and (
                        (tail < 10 and num % 10 == 0 and num >= 20 and (num % 100 or num >= 100))
                        or (tail in (100, 1000) and num < 1000) or (tail < 100 and num % 100 == 0 and num >= 100)):
                    n = int(num) + tail if tail < 100 else int(num) * tail   # 'twenty first' 21, 'one hundredth' 100
                    out.append((f"ord{n}", trips[s0][1], trips[i][2]))      # (cycle 2 F4)
                    if owed is not None:
                        out.append(("dollars",) + owed)
                        owed = None
                    i += 1
                    continue
        if num is not None:
            if toks[i:i + 3] == ["and", "a", "half"]:     # 'five and a half' = 5.5 (G18's rule since 08:30)
                num, i = num + Decimal("0.5"), i + 3
            while i < len(toks) and toks[i] in _SCALES and toks[i] != "hundred":   # '1.66 billion', '40 trillion'
                num, i = num * _SCALES[toks[i]], i + 1
            span = (trips[s0][1], trips[i - 1][2])
            out.append((_value(num),) + span)
            if owed is not None and i < len(toks) and toks[i] in ("%", "percent", "pct"):
                owed = None                        # '$50%': a percentage is never a dollar amount (batch 14)
            if owed is not None:                   # the spoken 'dollars' sits after the amount's last word
                if i < len(toks) and toks[i] in ("dollar", "dollars"):
                    out.append(("dollars", trips[i][1], trips[i][2]))
                    i += 1
                else:
                    out.append(("dollars", span[1], span[1]))
                owed = None
            continue
        if owed is not None:
            out.append(("dollars",) + owed)
            owed = None
        if t in ("dollar", "dollars"):
            out.append(("dollars",) + own)
        elif t in ("percent", "pct"):
            out.append(("percent",) + own)
        elif t == "per" and i + 1 < len(toks) and toks[i + 1] == "cent":
            out.append(("percent", own[0], trips[i + 1][2]))
            i += 1
        else:
            w = (t.split("'")[0] if heads and "'" in t else t).replace(".", "")   # "it's" != "its" (M1)
            if w:
                out.append((w,) + own)
        i += 1
    if owed is not None:
        out.append(("dollars",) + owed)
    return out


def canon_tokens(text, heads=False):
    """heads=True reduces a contraction to its head ("that's" -> "that", "we've" -> "we") for sites that ask
    which word a contraction starts with (backward references, openers); the default keeps the apostrophe."""
    return [t for t, _, _ in _canon_seq([(p, 0, 0) for p in _prepare(text)], heads)]


def canon_spans(words):
    """Canonical tokens of a word list as (token, first word index, last word index) (alignment sites: quote
    anchoring and selection locks use the FIRST index of their first token and the LAST index of their last).
    A Whisper word split across two words ('$81', ',000'; '74', '000') is read as one."""
    trips, i = [], 0
    while i < len(words):
        w, j = (words[i] or ""), i + 1
        if w.strip() in ("-", "+", "\u2212") and j < len(words) and re.match(r"^\s*\$?\d", words[j] or "") and \
                (w.strip() != "-" or not i or not re.search(r"[\d.,%]\s*$", words[i - 1] or "")):
            w, j = w.strip() + (words[j] or "").strip(), j + 1        # '-' '5%' = '-5%'; '70' '-' '75' stays a range
        if i and re.match(r"^\s*-\d", w) and re.search(r"\d$", (words[i - 1] or "").rstrip()):
            w = w.replace("-", "", 1)        # ruling 142 (1), word by word as in the text: '24' '-7,' reads '24' '7'
        while j < len(words) and (re.match(r"^\s*[.,][0-9A-Za-z]", words[j] or "") or (     # '$81' ',000'
                re.fullmatch(r"\$?\d{1,3}(\d{3})*", w.strip()) and re.fullmatch(r"\d{3}[.,!?]*", (words[j] or "").strip()))):
            w, j = w + (words[j] or "").strip(), j + 1                                      # '74' '000'
        trips += [(p, i, j - 1) for p in _prepare(w)]
        i = j
    return _canon_seq(trips)


def canon_aligned(words):
    """(token, index of the source word it starts in) pairs of canon_spans (punctuation transfer and other sites
    that only need where a token begins)."""
    return [(t, f) for t, f, _ in canon_spans(words)]


_AMOUNT = re.compile(r"\d+(\.\d+)?")


def dollars_after_number(tokens, k):
    """RULING 131 (B) (orchestrator 2026-11-17 '08:25'): True when canonical token k is a 'dollars' right after a number,
    the token a currency symbol makes ('$2 billion' -> '2000000000 dollars', the spoken order)."""
    return tokens[k] == "dollars" and k > 0 and bool(_AMOUNT.fullmatch(tokens[k - 1]))


def currency_free(tokens):
    """RULING 131 (B): a currency symbol is formatting, so '$2 billion' equals a spoken '2 billion'. The canonical tokens
    with every 'dollars' right after a number dropped (both sides of a comparison alike). This is G18's one tolerance
    since mission 4a (word_diff.norm), now the one function G18 and the sentence lock both use."""
    return [w for k, w in enumerate(tokens) if not dollars_after_number(tokens, k)]


# RULING 135 (orchestrator 10:50 ET Nov 17): THE COMPARISON CANON. "Differences of spelling are not differences of
# speech." Applied to a differing pair's two sides before the pair is compared (the lock, ruling 72's comparison,
# G18); canon_tokens itself is unchanged, so spans, edges and indices are not touched.
REDUCTIONS = {      # (c) spoken reductions equal their full form: a CLOSED list, none added without a ruling
    "kinda": ("kind", "of"), "sorta": ("sort", "of"), "gonna": ("going", "to"), "wanna": ("want", "to"),
    "gotta": ("got", "to"), "lemme": ("let", "me"), "gimme": ("give", "me"), "cause": ("because",),
    "cuz": ("because",), "em": ("them",), "ya": ("you",), "yeah": ("yes",), "yep": ("yes",)}
FILLER_TOKENS = frozenset({"um", "uh", "er", "ah", "hm", "hmm", "mm", "mhm"})      # (d) non-lexical
CONSONANTS = frozenset("bcdfghjklmnpqrstvwxz")                                     # (d) a stray consonant ("a", "i": words)


def comparison_form(tokens):
    """RULING 135 (a)+(c): canon tokens with their apostrophes removed, each spoken reduction (REDUCTIONS) expanded."""
    out = []
    for t in tokens:
        t = str(t).replace("'", "")
        out += list(REDUCTIONS.get(t, (t,)))
    return out


def nonlexical(tok, stray=False):
    """RULING 135 (d): a filler (FILLER_TOKENS); with stray, also a single consonant letter. Not a word."""
    return tok in FILLER_TOKENS or (stray and len(tok) == 1 and tok in CONSONANTS)


_FORM_END = re.compile(r"(?:'s|s'|'|s)$")         # ruling 142 (2): a possessive or plural ending (the canon folds ’)


def word_form(x, y):
    """Ruling 142 (2) (orchestrator 2026-11-17 '14:32'): two readings that differ ONLY by a possessive or plural ending
    on ONE word ('bitcoin' / "bitcoin's" / 'bitcoins' / "bitcoins'"): a word-form pair, decided like any other differing
    pair by ruling 131 (A)'s two of three (the sealed text takes that reading; all three different still holds). Never
    a token with a digit ('1990s' is not '1990': a number stays law L-v 2's). The same "'s" written as a contraction is
    the same pair (the ruling's own case, Natalie Brunell feb4b72f: "Bitcoin's a responsibility" against "Bitcoin is a
    responsibility"): [t + "'s"] against [t, 'is'] or [t, 'has']."""
    x, y = list(x or []), list(y or [])
    for a, b in ((x, y), (y, x)):                             # the contraction, either way round
        if len(a) == 1 and len(b) == 2 and b[1] in ("is", "has") and a[0] == b[0] + "'s" \
                and not re.search(r"\d", a[0]):
            return True
    if len(x) != len(y) or not x:
        return False
    diff = [(a, b) for a, b in zip(x, y) if a != b]
    if len(diff) != 1 or re.search(r"\d", diff[0][0] + diff[0][1]):
        return False
    a, b = (_FORM_END.sub("", t) for t in diff[0])
    return bool(a) and a == b


def same_words(x, y, stray=()):
    """RULING 135: the two sides of a differing pair (lists of canon tokens) are the same words. Both sides in comparison
    form (a, c), fillers left out (d); equal tokens, or, when neither side holds a digit, equal letters once every space
    and hyphen is gone (b: 'itrust capital's' = 'I trust capital's' = 'iTrustCapital's', names too). A single consonant
    is a stray sound only on a side named in `stray` ("x" / "y"): the side the caller knows ONE reading alone hears
    (ruling 72's second recogniser against the lock, G18's final decode); in the lock itself a lone letter is a token
    and the vote of three readings decides it (Heimdall batch 104 c2: a letter two readings hear is a word). Still a
    difference: two different single letters, any digit difference (numbers compare token for token; the currency form
    is (B)'s), and any other change of letters (a negation, a name, a content word). "cause" is taken as the ruled
    "'cause" (canon_tokens drops the apostrophe, so the noun reads the same; two readings of one audio never trade the
    noun "cause" for "because")."""
    cx, cy = comparison_form(x), comparison_form(y)
    lx = [t for t in cx if len(t) == 1 and t in CONSONANTS]
    ly = [t for t in cy if len(t) == 1 and t in CONSONANTS]
    if lx and ly and lx != ly:
        return False
    a = [t for t in cx if not nonlexical(t, "x" in stray)]
    b = [t for t in cy if not nonlexical(t, "y" in stray)]
    if a == b:
        return True
    if any(ch.isdigit() for t in a + b for ch in t):
        return False
    return "".join(a).replace("-", "") == "".join(b).replace("-", "")


def canon(text):
    return " ".join(canon_tokens(text))


def same(a, b):
    return canon_tokens(a) == canon_tokens(b)
