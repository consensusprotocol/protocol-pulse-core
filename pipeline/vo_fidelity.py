#!/usr/bin/env python3
"""pipeline/vo_fidelity.py — VO FIDELITY (law L-o 11, '01:55'; law L-t, '02:30'): the PBX MAX VO, the title and the
caption never put words in a speaker's mouth. Two layers, BOTH must pass ("vo check needs to be real 100%"):

(a) DETERMINISTIC (this module, no model): every line names the segments it relies on (cites = moment ids), and
    - NEEDS_SOURCE: a line with a fact (number, name, quote, attribution, time word) cites at least one segment;
    - ATTRIBUTION: "<X> says / argues / ...", "<X>: ...", "according to <X>" bind X to a cited segment: by its VERIFIED
      speaker, or by its show. A person-like show name with a speech verb needs the speaker verified (law L-v 1: a
      person is named only when verified; otherwise credit the show: "on X"). A pronoun or generic subject ("she
      says", "analysts say") is unbound;
    - NUMBER: every number (canon value and unit, law L-k) is in the sentences of the attribution that governs it
      (the nearest one in its sentence), else of the cited segments; a count of the package itself ("three voices")
      and "one" as a determiner are production language;
    - NAME: every capitalised token that is not an English word (/usr/share/dict/words) is in the cited sentences or
      is production metadata (a credited show, a verified speaker, the show date): no person who does not appear (L-t);
    - QUOTE: quoted words (double or single quotes) are a verbatim run of the governing segment (canonical form);
    - RELATION: words that make speakers agree, answer, rebut or echo each other only when every party is from the same
      source video (one conversation); parties are the cited segments, the credited shows named, or a plural party word;
    - FRAMING: banned framing verbs (L-t) only when the source itself uses the word;
    - IMPERATIVE: no financial imperative or advice framing (buy / sell / leverage / all in / time to buy) (L-t);
    - TIME: a recency word (today, overnight, just hit, this month, ...) only when a cited segment says it (L-v 3);
    - PRICE_NOW: a price level on ANY line is today's (within tolerance of a level the universe states as current),
      or reads as history (a history marker governs it and no present-tense word), or as a forecast (a modal or future
      word governs it) (orchestrator 03:40; L-v 3 / L-t).
(b) BLIND VERDICT (role "fidelity_verdict" through pipeline/providers.py, never the vendor or model family of the text
    it judges): given ONLY the segments' sentences, their shows and verified speakers, the production facts and the
    lines, every claim of EVERY line (a connective line too), each yes / no / uncertain with supporting words COPIED
    EXACTLY from the line's own cited segments or the production facts. The decision is code: every line covered, every
    claim "yes", every support a verbatim run (>= 3 tokens, or a whole shorter segment); anything else fails (law L-m).
"""
import json
import re

import canon

METADATA = ("PBX MAX", "Protocol Pulse", "Pulse Check", "Bitcoin", "BTC")
SPEECH_S = ("says", "said", "argues", "argued", "thinks", "thought", "believes", "believed", "warns", "warned",
            "predicts", "predicted", "claims", "claimed", "notes", "noted", "explains", "explained", "expects",
            "expected", "sees", "saw", "tells", "told", "adds", "added", "calls", "called", "reckons", "insists",
            "insisted", "suggests", "suggested", "writes", "wrote", "asks", "asked", "points out", "pointed out",
            "makes the case", "made the case")
SPEECH_BASE = ("say", "argue", "think", "believe", "warn", "predict", "claim", "note", "explain", "expect", "see",
               "tell", "add", "call", "reckon", "insist", "suggest", "write", "ask", "point out", "make the case")
ATTRIB_VERBS = SPEECH_S                                        # (kept for callers that list them)
PRONOUN_SUBJECTS = ("he", "she", "they", "his guest", "her guest", "their guest", "the guest", "the host",
                    "this guest", "this host", "the speaker", "this speaker", "the analyst", "this analyst",
                    "the author", "experts", "analysts", "critics", "many", "some", "others", "people", "everyone")
VO_SELF = ("i", "we")                                          # PBX MAX itself: its claims are the verdict's to judge
RELATION = re.compile(
    r"\b(agree[sd]?|agreeing|disagree[sd]?|disagreeing|respond(s|ed|ing)? to|repl(y|ies|ied|ying) to|"
    r"answer(s|ed|ing)? (him|her|them|that|this|the question)|rebut(s|ted|ting)?|push(es|ed|ing)? back|"
    r"counter(s|ed|ing)?|fire[sd]? back|echo(es|ed|ing)?|contradict(s|ed|ing)?|"
    r"back(s|ed|ing)? (him|her|them|that|this) up|backs? up|sides? with|takes? issue|in response|in contrast|"
    r"on the other side|on the other hand|weighs? in|shoots? down|goes further|went further|takes? it further|"
    r"(sees?|saw|puts?) it the same way|the same view|similarly|likewise|concur(s|red|ring)?|isn'?t buying it|"
    r"(has|takes|had|took) (a different|the opposite|another) (view|take)|different take|"
    r"both (say|said|agree|think|warn|see|argue|believe|expect|predict|make)|"
    r"all (three|four) (say|agree|think|warn|see|argue|believe|expect|predict)|"
    r"(are|were) on the same page|each other|one another)\b", re.I)
PARTY_WORDS = re.compile(r"\b(both|all three|all four|they all|the two|these (channels|voices|speakers)|each other|"
                         r"one another|everyone)\b", re.I)
FRAMING = {"destroy": r"destroy(s|ed|ing)?", "slam": r"slam(s|med|ming)?", "expose": r"expos(e|es|ed|ing)",
           "admit": r"admit(s|ted|ting)?", "confirm": r"confirm(s|ed|ing)?", "caught": r"caught",
           "torch": r"torch(es|ed|ing)", "blast": r"blast(s|ed|ing)?", "crush": r"crush(es|ed|ing)?",
           "debunk": r"debunk(s|ed|ing)?", "obliterate": r"obliterat(e|es|ed|ing)", "demolish": r"demolish(es|ed|ing)?",
           "wreck": r"wreck(s|ed|ing)?", "eviscerate": r"eviscerat(e|es|ed|ing)", "humiliate": r"humiliat(e|es|ed|ing)",
           "rip into": r"rip(s|ped|ping)? into", "dunk on": r"dunk(s|ed|ing)? on", "bombshell": r"bombshells?",
           "reveal": r"reveal(s|ed|ing)?"}
_TRADE = r"(buy(ing)?|sell(ing)?|short(ing)?|long|load(ing)? up|ape|go(ing)? all[- ]in|get(ting)? in|stack(ing)?|" \
         r"lever(age|aging)?( up)?|bet(ting)?)"
_NOT_A_VERB = r"(?![-‐–]|\s+(pressure|side|walls?|orders?|signals?|volume|interest|squeezes?|sellers?|buyers?|term|" \
              r"positions?|liquidations?|offs?|programs?|ratios?)\b)"
IMPERATIVE = re.compile(
    r"\byou(?:'ve|’ve| have|'d|’d| had)?\s+(?:(?:really|probably|definitely|just|absolutely|seriously)\s+)?"
    r"(?:should|need to|must|have to|ought to|got to|gotta|better)\s+(?:(?:really|probably|definitely|just|"
    r"absolutely|seriously|be)\s+)?" + _TRADE + r"\b"
    r"|\b(?:it'?s|it’s|it is|now'?s|now is|now’s)\s+(?:the\s+)?time\s+to\s+(?:buy|sell|get in|load up|stack|"
    r"go all[- ]in|back up the truck)\b"
    r"|\b(?:don'?t|don’t|do not|never)\s+(?:ever\s+)?(?:sell|buy|miss)\b"
    r"|(?:^|[.!?:]\s+|\bso\s+)(?:buy|sell|short|load up|ape in|go all[- ]in|get in now|stack sats|lever up)\b"
    + _NOT_A_VERB, re.I)
TIME_WORDS = ("today", "tonight", "yesterday", "this morning", "this afternoon", "this evening", "this week",
              "this weekend", "this month", "last night", "overnight", "right now", "currently", "at the moment",
              "as we speak", "recently", "minutes ago", "hours ago", "breaking news")
_TIME_RE = re.compile(r"\bjust\s+(?:\w+ed|hit|set|broke|fell|rose|ran|made|won|lost|got|saw|bought|sold|went|came|"
                      r"took|began|flipped|topped)\b|\bbreaking\s*:|\b(?:monday|tuesday|wednesday|thursday|friday|"
                      r"saturday|sunday)(?:'s|’s)?\b", re.I)
_NUM = re.compile(r"^-?\d+(\.\d+)?$")
HISTORY_WORDS = ("since", "back", "ago", "once", "was", "were", "had", "history", "historically", "historic",
                 "decade", "decades", "past", "previous", "last cycle", "used to", "low", "bottom")
FUTURE_WORDS = ("could", "will", "would", "might", "may", "going", "gonna", "target", "targets", "predict",
                "predicts", "predicted", "forecast", "forecasts", "expect", "expects", "expected", "projection",
                "reach", "if", "should", "call", "calls", "eventually", "someday")
PRESENT_WORDS = ("is", "are", "now", "today", "currently", "trading", "trades", "sits", "sitting", "hovering",
                 "tonight", "holds", "holding")
PRICE_PREPS = ("at", "to", "hit", "hits", "from", "above", "below", "past", "over", "under", "near", "around",
               "trading", "reached", "reaches", "crossed", "crosses", "broke", "breaks", "tops", "topped", "tested",
               "tests", "testing", "toward", "towards", "reclaimed", "reclaims", "holds", "held", "sits")
COUNT_WORDS = ("bitcoin", "bitcoins", "btc", "coins", "coin", "sats", "satoshis", "holders", "addresses", "people",
               "users", "companies", "nodes", "miners", "transactions", "blocks", "times", "percent", "years",
               "months", "days", "hours")
PRODUCTION_NOUNS = ("clips", "clip", "channels", "channel", "voices", "voice", "shows", "show", "videos", "video",
                    "takes", "views", "speakers", "segments", "sources")
_QUOTE = re.compile(r"[\"“”]([^\"“”]{2,}?)[\"“”]|(?<![\w’'])[‘']([^‘’']{2,}?)[’'](?![\w’'])")
COMMON_CAPS = frozenset("I The This That These Those It And But So We You They He She Here There Now Today Next First "
                        "Then Also Plus Meanwhile Still Yet Why What How When Where Who Which Our Your Their Its "
                        "Let Let's Clips Go Links Follow Watch Stay A An In On At For From With As If Not No Yes "
                        "One Two Three Four Five Six Seven Eight Nine Ten Here's That's It's".split())
PRODUCTION_WORDS = frozenset({"pbx", "max", "protocol", "pulse", "check", "bitcoin", "btc", "sats", "hodl", "crypto"})
_LEX = None


def lexicon():
    """Lower-case English words (the system word list) + production words. A capitalised token that is not one of
    them is a NAME candidate. Without the word list every capitalised token is a candidate (fail closed)."""
    global _LEX
    if _LEX is None:
        words = set(PRODUCTION_WORDS)
        try:
            with open("/usr/share/dict/words") as f:
                words |= {w.strip() for w in f if w.strip() and w.strip().islower()}
        except OSError:
            pass
        _LEX = frozenset(words)
    return _LEX


def ctoks(text):
    return canon.canon_tokens(text or "")


def _run_in(sub, toks):
    """sub (canonical tokens) occurs as a contiguous run in toks."""
    n = len(sub)
    return n > 0 and any(toks[i:i + n] == sub for i in range(len(toks) - n + 1))


def _fold(w):
    """A token for name matching: lower case, possessive and plural folded."""
    w = re.sub(r"(['’]s|['’])$", "", (w or "").lower().strip(".,;:!?\"“”()"))
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w


def _folds(text):
    return [_fold(w) for w in re.findall(r"[A-Za-z0-9][\w'’&.-]*", text or "") if _fold(w)]


def numbers_of(text):
    """[(value, unit or None)] in canonical form: '$73,000' -> ('73000', 'dollars'); '16%' -> ('16', 'percent')."""
    t = ctoks(text)
    out = []
    for i, w in enumerate(t):
        if _NUM.match(w):
            unit = t[i + 1] if i + 1 < len(t) and t[i + 1] in ("dollars", "percent") else None
            out.append((w, unit))
    return out


def _has_number(src_toks, value, unit):
    for i, w in enumerate(src_toks):
        if w == value and (unit is None or (i + 1 < len(src_toks) and src_toks[i + 1] == unit)):
            return True
    return False


# ── price levels (PRICE_NOW, orchestrator 03:40) ──

def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]


def _clauses(sentence):
    return [c for c in re.split(r"[;—–]|,\s|:\s", sentence) if c.strip()]


def _price_values(toks):
    """[(index, value)] of the price-like numbers of canonical tokens: a money amount of 1,000-10,000,000 dollars, or
    10,000-1,000,000 after a price word ('at', 'to', 'hit', 'trading', ...); never a count of coins or holders."""
    out = []
    for i, w in enumerate(toks):
        if not _NUM.match(w):
            continue
        v = float(w)
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        prv = toks[i - 1] if i > 0 else ""
        if nxt in COUNT_WORDS:
            continue
        if (nxt == "dollars" and 1_000 <= v <= 10_000_000) or (10_000 <= v <= 1_000_000 and prv in PRICE_PREPS):
            out.append((i, v))
    return out


def _has(words, toks):
    for w in words:
        wt = w.split()
        if _run_in(wt, toks):
            return True
    return False


def price_mentions(text):
    """[(value, kind)] for each price-like number of a line: kind "future" (a modal / future word before it in its
    clause), "history" (a history marker or a year before it in its sentence, and no present-tense word in its clause),
    else "current"."""
    out = []
    for s in _sentences(text):
        st = ctoks(s)
        for c in _clauses(s):
            ct = ctoks(c)
            for i, v in _price_values(ct):
                before = ct[:i]
                k = _run_find(ct, st)
                sent_before = st[:k + i] if k is not None else st
                year_before = any(re.fullmatch(r"(19|20)\d\d", t) for t in sent_before if t != ct[i])
                by_year_after = any(ct[j] == "by" and j + 1 < len(ct) and re.fullmatch(r"(19|20)\d\d", ct[j + 1])
                                    for j in range(i + 1, len(ct) - 1))
                if _has(FUTURE_WORDS, before) or by_year_after:
                    out.append((v, "future"))
                elif (year_before or _has(HISTORY_WORDS, sent_before)) and not _has(PRESENT_WORDS, before):
                    out.append((v, "history"))
                else:
                    out.append((v, "current"))
    return out


def _run_find(sub, toks):
    n = len(sub)
    for i in range(len(toks) - n + 1):
        if toks[i:i + n] == sub:
            return i
    return None


def price_levels(text):
    """Every price-like value a line states (any kind)."""
    return [v for v, _ in price_mentions(text)]


def current_level_values(sentence):
    """The levels one source sentence states as CURRENT: a price in a clause with a present-tense word before it and no
    future / conditional / history word anywhere in the sentence (package.current_levels)."""
    st = ctoks(sentence)
    if _has(FUTURE_WORDS, st) or _has(HISTORY_WORDS, st) or any(re.fullmatch(r"(19|20)\d\d", t) for t in st):
        return []
    out = []
    for c in _clauses(sentence):
        ct = ctoks(c)
        out += [v for i, v in _price_values(ct) if _has(PRESENT_WORDS, ct[:i]) and 10_000 <= v <= 1_000_000]
    return out


def price_now(text, current_levels, tolerance=0.05):
    """PRICE_NOW: the CURRENT-kind price values of a line that match no current level within tolerance. -> [values]."""
    cur = [float(c) for c in current_levels or ()]
    return [v for v, kind in price_mentions(text)
            if kind == "current" and not any(abs(v - c) <= tolerance * c for c in cur if c > 0)]


# ── names and attribution ──

def _segment_names(s):
    """A segment's VERIFIED speaker names (empty when the speaker is not verified)."""
    return [n for n in [s.get("speaker")] + list(s.get("names") or []) if n]


def _show(s):
    return s.get("show") or s.get("speaker") or ""


def person_like(name):
    """A show named like a person: two or more capitalised tokens, none an English word ('Natalie Brunell')."""
    ws = re.findall(r"[A-Za-z][A-Za-z'’.-]*", name or "")
    return len(ws) >= 2 and all(w[0].isupper() and _fold(w) not in lexicon() for w in ws)


def manifest_terms(segments, manifest=None):
    """Production metadata a line may state without a citation (never a claim about what anyone said): the credited
    shows and verified speaker names, the show, the date (month, weekday) and the package's own counts."""
    from datetime import date
    names = {n for s in segments.values() for n in [_show(s)] + _segment_names(s) if n}
    m = manifest or {}
    names |= set(m.get("channels") or []) | ({m["show"]} if m.get("show") else set())
    nums = {str(len(segments)), str(len({s["video_id"] for s in segments.values()})),
            str(len(set(m.get("channels") or []) or {_show(s) for s in segments.values()}))}
    if m.get("date"):
        try:
            d = date.fromisoformat(m["date"])
            names |= {d.strftime("%B"), d.strftime("%A"), d.strftime("%b")}
        except ValueError:
            pass
    return sorted(names), nums


def names_of(text, allowed=()):
    """NAME candidates of a line: capitalised tokens (or all-caps acronyms) that are not English words, production
    metadata or allowed terms, wherever they stand (a Title Case line and a sentence start included)."""
    ok = {f for a in tuple(allowed) + METADATA for f in _folds(a)}
    out = []
    for w in re.findall(r"[A-Za-z][A-Za-z'’.&-]*", text or ""):
        core = re.sub(r"(['’]s|['’])$", "", w.strip(".-"))
        if not core or not core[0].isupper():
            continue
        parts = [p for p in re.split(r"[-.&]", core) if p]
        acronym = core.isupper() and len(core) >= 2
        if not acronym and all(p.lower() in lexicon() for p in parts):
            continue
        if core in ("I", "A") or _fold(core) in ok:
            continue
        out.append(core)
    return list(dict.fromkeys(out))


_CAPRUN = r"[A-Z][\w'’.&-]*(?:\s+(?:of|and|&|de|van|von|da)\s+[A-Z][\w'’.&-]*|\s+[A-Z][\w'’.&-]*){0,5}"


def _verbs(forms):
    return "|".join(re.escape(v) for v in sorted(forms, key=len, reverse=True))


def _attributions(text):
    """[(subject, form, start)] in order: '<Subject> <speech verb>' (case-insensitive verb, capitalised subject),
    '<pronoun or generic subject> <speech verb>', '<Subject>: ...' (at a sentence start), 'according to <Subject>'."""
    out = []
    t = text or ""
    for m in re.finditer(r"(" + _CAPRUN + r")\s+(?:also\s+|now\s+|still\s+|even\s+)?(?i:" + _verbs(SPEECH_S + SPEECH_BASE)
                         + r")\b", t):
        out.append((m.group(1), "speech", m.start()))
    for m in re.finditer(r"(?i:\b(" + "|".join(re.escape(p) for p in PRONOUN_SUBJECTS) + r")\s+(?:also\s+)?(?:"
                         + _verbs(SPEECH_S + SPEECH_BASE) + r")\b)", t):
        if not any(a[2] <= m.start() < a[2] + len(a[0]) + 1 for a in out):
            out.append((m.group(1), "pronoun", m.start()))
    for m in re.finditer(r"(?:^|[.!?]\s+|\b(?:Next|Then|And|Here's|Now),?\s+)(" + _CAPRUN + r"):\s", t):
        out.append((m.group(1), "colon", m.start(1)))
    for m in re.finditer(r"(?i:according to)\s+(" + _CAPRUN + r")", t):
        out.append((m.group(1), "according", m.start()))
    out.sort(key=lambda a: a[2])
    return out


def _clean_subject(subj):
    ws = subj.split()
    while ws and ws[0].strip(",") in COMMON_CAPS:
        ws = ws[1:]
    return " ".join(ws)


def _match(subject, name):
    s, n = _folds(subject), _folds(name)
    return bool(s and n) and (_run_in(n, s) or _run_in(s, n))


def _governed(text, atts):
    """Split a line into (chunk text, attribution index or None): each attribution governs its sentence from its
    position to the next attribution; the words before a sentence's first attribution belong to it as well ('..., says
    X'); a sentence without one is governed by the cited segments (None)."""
    out, pos = [], 0
    for s in _sentences(text):
        start = (text or "").find(s, pos)
        end = start + len(s)
        pos = end
        inside = [(i, a) for i, a in enumerate(atts) if start <= a[2] < end]
        if not inside:
            out.append((s, None))
            continue
        cuts = [a[2] for _, a in inside] + [end]
        out.append((text[start:cuts[1]], inside[0][0]))
        for k in range(1, len(inside)):
            out.append((text[cuts[k]:cuts[k + 1]], inside[k][0]))
    return out


_META_FOLDS = frozenset(f for m in METADATA for f in _folds(m))
_OPINION = {"think": ("thinks", "think", "thought", "believes", "believe", "believed", "reckons", "reckon"),
            "feel": ("feels", "feel", "felt"),
            "believe": ("believes", "believe", "believed", "thinks", "think", "thought"),
            "guess": ("guesses", "guess", "suspects", "suspect", "thinks", "think", "reckons", "reckon"),
            "suspect": ("suspects", "suspect", "thinks", "think", "reckons", "reckon"),
            "reckon": ("reckons", "reckon", "thinks", "think")}
_OPINION_RE = re.compile(r"\bI\s+(?:really\s+|just\s+|do\s+|personally\s+|kind of\s+|kinda\s+|still\s+)?"
                         r"(think|feel|believe|guess|suspect|reckon)\b|\b(in my (?:opinion|view)|to me,|I'd say|"
                         r"I would say|my sense is|my view is|my take is)", re.I)


def hedge_markers(text):
    """The clip's own opinion markers ('I think', 'I feel like', 'in my opinion', ...)."""
    return [m.group(0) for m in _OPINION_RE.finditer(text or "")]


def hedge_verbs(text):
    """The attribution verbs a clip's hedges allow (orchestrator 05:25 item 2: 'thinks' for 'I think', 'feels' for 'I
    feel like', 'says' only for a flat assertion). Empty when the clip has no opinion marker."""
    need = set()
    for m in _OPINION_RE.finditer(text or ""):
        need |= set(_OPINION[m.group(1).lower()]) if m.group(1) else {"thinks", "think", "feels", "feel", "believes",
                                                                        "believe", "reckons", "reckon"}
    return need


def _speech_verb(subj0, form, text, start):
    """The speech verb right after an attribution's subject (None for the colon / 'according to' forms)."""
    if form not in ("speech", "pronoun"):
        return None
    m = re.match(r"\s+(?:also\s+|now\s+|still\s+|even\s+)?(" + _verbs(SPEECH_S + SPEECH_BASE) + r")\b",
                 (text or "")[start + len(subj0):], re.I)
    return m.group(1).lower() if m else None


def time_words(text, meta=()):
    """Recency words of a line (L-v 3); the show date's own weekday is production metadata."""
    out = [w for w in TIME_WORDS if re.search(r"\b" + re.escape(w) + r"\b", text or "", re.I)]
    for m in _TIME_RE.finditer(text or ""):
        if re.sub(r"['’]s$", "", m.group(0)).strip().title() not in set(meta):
            out.append(m.group(0))
    return out


def fact_numbers(text, meta_nums=frozenset()):
    """The numbers of a text that state a fact, [(value, unit)]: leaves out the package's own count beside a production
    noun ('three voices') and 'one' written as a word (a determiner or pronoun: 'one thing', 'one of')."""
    out, t = [], ctoks(text)
    plain = (text or "").replace(",", "")
    for i, w in enumerate(t):
        if not _NUM.match(w):
            continue
        unit = t[i + 1] if i + 1 < len(t) and t[i + 1] in ("dollars", "percent") else None
        spelled = not re.search(rf"(?<![\d.]){re.escape(w)}(?![\d])", plain)
        if unit is None and w in meta_nums and any(x in PRODUCTION_NOUNS for x in t[i + 1:i + 3]):
            continue
        if unit is None and w == "1" and spelled:
            continue
        out.append((w, unit))
    return out


def check_deterministic(segments, lines, manifest=None, current_levels=None):
    """segments: {moment_id: {"show": the credited channel, "speaker": the VERIFIED speaker's name or None, "names":
    [verified names], "video_id", "text"}} (a caller without "show" passes the speaker as both); lines: [{"slot", "text",
    "cites": [moment_id, ...]}] (VO lines, the title, the caption); manifest: {"channels", "date", "show"};
    current_levels: the universe's current price levels (None: PRICE_NOW not measured).
    -> {"ok", "violations": [{"slot", "rule", "detail"}], "price_now_measured"}."""
    v = []
    meta, meta_nums = manifest_terms(segments, manifest)
    seg_toks = {mid: ctoks(s["text"]) for mid, s in segments.items()}
    for ln in lines:
        slot, text = ln["slot"], ln.get("text") or ""
        cites = [c for c in (ln.get("cites") or []) if isinstance(c, str)]
        V = lambda rule, detail: v.append({"slot": slot, "rule": rule, "detail": detail})
        unknown = [c for c in ln.get("cites") or [] if not isinstance(c, str) or c not in segments]
        if unknown:
            V("CITE_UNKNOWN", f"cites {unknown} are not segments of this package")
        cited = [c for c in cites if c in segments]
        pool = [t for c in cited for t in seg_toks[c]]
        atts = _attributions(text)
        names = names_of(text, meta)
        quotes = [q for pair in _QUOTE.findall(text) for q in pair if q]
        times = time_words(text, meta)
        if (fact_numbers(text, meta_nums) or names or quotes or atts or times) and not cited:
            V("NEEDS_SOURCE", "a line with a number, name, quote, attribution or time word cites no segment")
        pools = []                                                   # per attribution: the governing segments
        for subj0, form, _ in atts:
            subj = _clean_subject(subj0)
            words0 = subj0.lower().split()
            if form == "pronoun" or subj.lower() in PRONOUN_SUBJECTS or (not subj and words0 and
                                                                         words0[-1] in PRONOUN_SUBJECTS + VO_SELF):
                who = (subj or (words0[-1] if words0 else "")).lower()
                if who not in VO_SELF:
                    V("ATTRIBUTION", f"'{subj0.strip()} ...': name who speaks, by the show ('on <show>') or by a "
                                     f"verified name")
                pools.append(None)
                continue
            if not subj:
                pools.append(None)
                continue
            by_speaker = [c for c in cited if any(_match(subj, n) for n in _segment_names(segments[c]))]
            by_show = [c for c in cited if c not in by_speaker and _match(subj, _show(segments[c]))]
            if by_speaker:
                pools.append(by_speaker)
            elif by_show:
                if form == "speech" and person_like(_show(segments[by_show[0]])):
                    V("ATTRIBUTION", f"'{subj}' with a speech verb names a person, but the speaker of "
                                     f"{_show(segments[by_show[0]])}'s clip is not verified (law L-v 1): credit the show "
                                     f"('on {_show(segments[by_show[0]])}')")
                pools.append(by_show)
            elif all(_fold(w) in lexicon() or _fold(w) in _META_FOLDS for w in subj.split()):
                if form in ("speech", "according"):                  # "Analysts say", "according to experts"
                    V("ATTRIBUTION", f"'{subj}' is not a speaker of this package: name who speaks, by the show "
                                     f"('on <show>') or by a verified name")
                pools.append(None)                                   # "Bitcoin: ..." is a label, not a speaker
            else:
                V("ATTRIBUTION", f"'{subj}': no cited segment is spoken by {subj} or comes from that show")
                pools.append(None)
        for (subj0, form, start), segs_ in zip(atts, pools):
            verb = _speech_verb(subj0, form, text, start)
            for c in segs_ or []:
                need = hedge_verbs(segments[c]["text"])
                if verb and need and verb not in need:
                    V("HEDGE", f"'{verb}' makes {_show(segments[c])}'s clip sound firmer than it is: the clip hedges "
                               f"('{hedge_markers(segments[c]['text'])[0]}'); use {sorted(need)[:3]}")
        for chunk, ai in _governed(text, atts):
            gov = pools[ai] if ai is not None and pools[ai] else cited
            gpool = [t for c in gov for t in seg_toks[c]]
            for val, unit in fact_numbers(chunk, meta_nums):
                if not _has_number(gpool, val, unit):
                    V("NUMBER", f"{val}{' ' + unit if unit else ''} is not in the cited sentences" +
                      (" of the attributed speaker / show" if ai is not None and pools[ai] else ""))
            for q in [q for pair in _QUOTE.findall(chunk) for q in pair if q]:
                if not any(_run_in(ctoks(q), seg_toks[c]) for c in gov):
                    V("QUOTE", f"\"{q}\" is not a verbatim run of the " +
                      ("attributed speaker's" if ai is not None and pools[ai] else "cited") + " sentences")
        pool_f = {_fold(t) for t in pool} | {_fold(t) for c in cited for t in re.findall(r"[\w'’]+", segments[c]["text"])}
        for n in names:
            if _fold(n) not in pool_f:
                V("NAME", f"'{n}' is not said in the cited sentences (and is not a credited show, a verified speaker or "
                          f"the show date)")
        parties = {segments[c]["video_id"] for c in cited}
        named = {segments[c]["video_id"] for c in segments if _show(segments[c]) and
                 re.search(r"\b" + re.escape(_show(segments[c])) + r"\b", text)}
        if PARTY_WORDS.search(text):
            named |= {s["video_id"] for s in segments.values()}
        rel = RELATION.search(text)
        if rel and len(parties | named) > 1:
            V("RELATION", f"'{rel.group(0)}' relates speakers who were not in one conversation")
        for lemma, pat in FRAMING.items():
            if re.search(r"\b" + pat + r"\b", text, re.I) and not any(
                    re.search(r"\b" + pat + r"\b", segments[c]["text"], re.I) for c in cited):
                V("FRAMING", f"'{lemma}' framing is not the source's own word (L-t)")
        if IMPERATIVE.search(text):
            V("IMPERATIVE", f"financial imperative or advice framing: '{IMPERATIVE.search(text).group(0).strip()}'")
        for w in times:
            if not any(_run_in(ctoks(w), seg_toks[c]) for c in cited):
                V("TIME", f"'{w}' is not said in the cited sentences (L-v 3: time words need the source's own)")
        if current_levels is not None:
            stale = price_now(text, current_levels)
            if stale:
                V("PRICE_NOW", f"states the level(s) {stale} as if current, but this universe's current levels are "
                               f"{sorted(set(current_levels))[:6]}; mark it as history or drop it (L-v 3 / L-t)")
    return {"ok": not v, "violations": v, "price_now_measured": current_levels is not None}


CLASSES = ("attribution", "fact", "production", "commentary")
STOPWORDS = frozenset("a an the and or but so of to in on at for from with by as is are was were be been it its it's "
                      "this that these those there here i you he she we they me him her us them my your his our their "
                      "do does did just like kind sort very really some any all no not".split())
COMMENTARY_TESTS = ("fact", "speaker_view", "imperative_or_prediction", "accusation", "sounds_like_a_speaker")
VERDICT_PROMPT = """You check a short video script for fidelity to its sources. You see ONLY the words each clip's
speaker said (the segments, each with its show and whether the speaker's identity is verified), the production facts
(true by construction), and the script's lines (voice-over, title, caption), each with the clips it cites.

SEGMENTS:
{segments}

PRODUCTION FACTS (segment label "manifest"):
{manifest}

SCRIPT LINES:
{lines}

Split every line into its claims and CLASSIFY each claim:
- "attribution": says or implies what a named speaker or show said, thinks, feels or did; who a speaker is; any
  agreement, answer or disagreement between speakers;
- "fact": a checkable statement about the world in the voice-over's own voice: a number, price, date, event, or a named
  person or company doing something;
- "production": what the video itself is: its channels, how many clips or voices, credits, "next", "links below";
- "commentary": the host's OWN opinion, framing, question, tease or takeaway, attributed to nobody.
When unsure between commentary and attribution or fact, choose attribution or fact.
EVERY sentence of every line belongs to at least one claim. Give each claim's "words": its exact words in the line.
For an attribution, fact or production claim, "supported" is "yes" only if the words you cite state it with the same
meaning and polarity and the SAME OR WEAKER certainty, adding nothing; "no" if they do not; "uncertain" if you cannot
tell. Attribution and fact claims cite ONLY the segments their line cites; production claims cite "manifest". A claim
that a NAMED PERSON said or thinks something is "yes" only if that segment's speaker is verified as that person. Copy
every supporting run EXACTLY (a continuous run of at least three words, or the whole segment if it is shorter); several
segments may support one claim together, each with its own words. Set "tests" to {{}}.
For a commentary claim, set "supported" to "n/a" and "support" to [], and answer each test "yes", "no" or "uncertain"
in "tests": "fact" (does it state a checkable fact, number, price, date or a named person or company?),
"speaker_view" (does it characterise any speaker's view, or how one speaker relates to another?),
"imperative_or_prediction" (financial advice, or a prediction?), "accusation", "sounds_like_a_speaker" (could a viewer
take it for something a speaker said: in quotation marks, or after "as X put it"?).
Return ONLY this JSON object: {{"claims": [{{"line": "<slot>", "words": "<exact words of the line>", "class":
"attribution" | "fact" | "production" | "commentary", "claim": "...", "supported": "yes" | "no" | "uncertain" | "n/a",
"support": [{{"segment": "<label>", "words": "<exact words>"}}], "tests": {{}}}}]}}"""


def manifest_text(segments, manifest=None):
    """The production facts a line may state: the credited shows, the show, the date, that source links are given."""
    m = manifest or {}
    chans = list(dict.fromkeys(list(m.get("channels") or []) + [_show(s) for s in segments.values()]))
    parts = [f"The video is about Bitcoin and contains clips from {', '.join(chans)}.", f"There are {len(segments)} clips.",
             "Links to every source are below.", "The voice-over is PBX MAX on Protocol Pulse."]
    if m.get("show"):
        parts.append(f"The show is {m['show']}.")
    if m.get("date"):
        parts.append(f"The show date is {m['date']}.")
    return " ".join(parts)


def verdict_prompt(segments, lines, manifest=None):
    from story_semantics import quote_data
    seg = "\n".join(
        f'<segment label="{mid}" show="{quote_data(_show(s), 80)}" speaker="'
        f'{quote_data(s["speaker"], 80) + " (verified)" if s.get("speaker") else "not verified"}">'
        f'{quote_data(s["text"], 900)}</segment>' for mid, s in segments.items())
    lns = "\n".join(f'<line slot="{ln["slot"]}" cites="{", ".join(str(c) for c in ln.get("cites") or []) or "none"}">'
                    f'{quote_data(ln.get("text") or "", 400)}</line>' for ln in lines)
    return VERDICT_PROMPT.format(segments=seg, lines=lns, manifest=manifest_text(segments, manifest))


def strict_features(words, segments, manifest=None, production=False):
    """What makes words NOT host commentary by rule (05:25 item 2, tests i, iii, v): a fact number, a name that is not
    production metadata, a quote, an attribution, a price, a time word, a financial imperative, a relation or framing
    word, 'as X put it'. -> [feature, ...] (empty: the words may be commentary)."""
    meta, meta_nums = manifest_terms(segments, manifest)
    out = []
    if fact_numbers(words, meta_nums):
        out.append("a number")
    if names_of(words, meta):
        out.append(f"a name ({', '.join(names_of(words, meta)[:3])})")
    if [q for pair in _QUOTE.findall(words) for q in pair if q] or re.search(r"\bas \w+(\s\w+)? (put|puts|said) it\b",
                                                                               words, re.I):
        out.append("a quotation")
    if [a for a in _attributions(words) if a[1] != "colon" or _clean_subject(a[0])]:
        out.append("an attribution")
    if production and re.search(r"\b(says?|said|thinks?|argues?|warns?|believes?|explains?|predicts?)\b", words, re.I):
        out.append("a speech verb")
    if price_mentions(words):
        out.append("a price")
    if time_words(words, meta):
        out.append("a time word")
    if IMPERATIVE.search(words):
        out.append("a financial imperative")
    if RELATION.search(words) or any(re.search(r"\b" + p + r"\b", words, re.I) for p in FRAMING.values()):
        out.append("a relation or framing word")
    return out


def check_verdict(raw, segments, lines, manifest=None):
    """The blind CLASSIFYING verdict's reply (strict; never repaired) -> {"ok", "claims", "violations", "classes"}.
    Every sentence of every line is covered by a claim whose words are the line's own. Attribution / fact: "yes" with
    supports from the line's own cited segments; production: "yes" with supports from the manifest; each support a
    verbatim run (>= 3 tokens, or a whole shorter text). Commentary: every test "no", and none of the rule features
    (strict_features) - a commentary label on words that carry one is judged as a fact with no support (strict by
    default, 05:25 item 2). Anything else fails (law L-m)."""
    obj = json.loads(raw.strip()) if isinstance(raw, str) else None
    if not isinstance(obj, dict) or set(obj) != {"claims"} or not isinstance(obj["claims"], list):
        raise ValueError("the verdict must be exactly {'claims': [...]}")
    by_slot = {ln["slot"]: ln for ln in lines}
    cites = {s: [c for c in ln.get("cites") or [] if isinstance(c, str)] for s, ln in by_slot.items()}
    texts = dict({mid: s["text"] for mid, s in segments.items()}, manifest=manifest_text(segments, manifest))
    v, cover, classes = [], {s: [] for s in by_slot}, {}
    keys = {"line", "words", "class", "claim", "supported", "support", "tests"}
    for c in obj["claims"]:
        if not isinstance(c, dict) or set(c) != keys:
            raise ValueError(f"each claim needs exactly {sorted(keys)}")
        if not isinstance(c["line"], str) or c["line"] not in by_slot or not isinstance(c["words"], str) or \
                c["class"] not in CLASSES or not isinstance(c["claim"], str) or not isinstance(c["support"], list) or \
                not isinstance(c["tests"], dict) or c["supported"] not in ("yes", "no", "uncertain", "n/a"):
            raise ValueError(f"claim on line {str(c.get('line'))[:40]!r}: a field is out of its contract")
        slot, lt, wt = c["line"], ctoks(by_slot[c["line"]]["text"]), ctoks(c["words"])
        at = _run_find(wt, lt) if wt else None
        if at is None:
            v.append({"slot": slot, "rule": "VERDICT_WORDS", "detail": f"the claim's words are not the line's own: "
                                                                       f"{c['words'][:120]!r}"})
            continue
        cover[slot].append((at, at + len(wt)))
        classes.setdefault(slot, []).append(c["class"])
        if c["class"] == "commentary":
            if c["supported"] != "n/a" or c["support"] or set(c["tests"]) != set(COMMENTARY_TESTS) or \
                    any(x not in ("yes", "no", "uncertain") for x in c["tests"].values()):
                raise ValueError("a commentary claim needs supported 'n/a', support [] and exactly the five tests")
            feats = strict_features(c["words"], segments, manifest)
            if feats:
                v.append({"slot": slot, "rule": "NOT_COMMENTARY",
                          "detail": f"'{c['words'][:100]}' is labelled commentary but carries {', '.join(feats)}: as an "
                                    f"attribution or fact it has no support"})
                continue
            failed = [t for t in COMMENTARY_TESTS if c["tests"][t] != "no"]
            if failed:
                v.append({"slot": slot, "rule": "COMMENTARY",
                          "detail": f"host commentary '{c['words'][:100]}' fails {', '.join(failed)}"})
            continue
        if c["tests"] != {} or c["supported"] == "n/a":
            raise ValueError("an attribution / fact / production claim needs supported yes|no|uncertain and tests {}")
        if c["class"] == "production":                  # bound to the manifest (audit C2 K2)
            feats = strict_features(c["words"], segments, manifest, production=True)
            if feats:
                v.append({"slot": slot, "rule": "NOT_PRODUCTION",
                          "detail": f"'{c['words'][:100]}' is labelled production but carries {', '.join(feats)}"})
                continue
        if c["supported"] != "yes":
            v.append({"slot": slot, "rule": "VERDICT_" + c["supported"].upper(), "detail": c["claim"][:200]})
            continue
        allowed = {"manifest"} if c["class"] == "production" else set(cites[slot])
        good = []
        for x in c["support"]:
            if isinstance(x, dict) and set(x) == {"segment", "words"} and isinstance(x["segment"], str) and \
                    isinstance(x["words"], str) and x["segment"] in allowed and x["segment"] in texts:
                st, xt = ctoks(texts[x["segment"]]), ctoks(x["words"])
                if _run_in(xt, st) and (len(xt) >= 3 or xt == st):
                    good.append(x)
        if not c["support"] or len(good) != len(c["support"]):
            v.append({"slot": slot, "rule": "VERDICT_UNVERIFIED",
                      "detail": f"supports are not verbatim runs (>= 3 words) of " +
                                ("the production facts" if c["class"] == "production" else "the line's own cited "
                                                                                           "segments") +
                                f": {c['claim'][:150]}"})
    for slot, ln in by_slot.items():                 # FULL coverage: every content word of every sentence (audit C2 K1)
        lt, pos = ctoks(ln.get("text") or ""), 0
        covered = {i for x, y in cover[slot] for i in range(x, y)}
        for sent in _sentences(ln.get("text") or ""):
            st = ctoks(sent)
            at = _run_find(st, lt[pos:]) if st else None
            if at is None:
                if st:
                    v.append({"slot": slot, "rule": "VERDICT_INCOMPLETE", "detail": f"sentence not located: {sent[:100]!r}"})
                continue
            a, b = pos + at, pos + at + len(st)
            pos = b
            missing = [lt[i] for i in range(a, b) if lt[i] not in STOPWORDS and i not in covered]
            if missing:
                v.append({"slot": slot, "rule": "VERDICT_INCOMPLETE",
                          "detail": f"no claim covers {missing[:6]} in {sent[:100]!r}"})
    return {"ok": not v, "claims": obj["claims"], "violations": v, "classes": classes}


def check(router, segments, lines, writer_vendor, seed=7, manifest=None, current_levels=None, writer_family=None):
    """Both layers. -> {"ok", "deterministic", "verdict", "violations", "backend", "measured", "replayed"}; the verdict
    never runs on the vendors / families of the text it judges; a verdict that cannot be had or read is a failure
    (law L-m) and leaves the layer NOT measured."""
    import providers as P
    det = check_deterministic(segments, lines, manifest, current_levels)
    out = {"deterministic": det, "verdict": None, "backend": None, "measured": False, "replayed": False, "seed": seed}
    try:                                      # the 20:33 order: an answer out of contract moves on (P.call_parsed)
        r, out["verdict"] = P.call_parsed(router, "fidelity_verdict", verdict_prompt(segments, lines, manifest),
                                          lambda t: check_verdict(t, segments, lines, manifest), 2500, seed,
                                          avoid_vendor=writer_vendor, avoid_family=writer_family)
        out["backend"], out["replayed"] = r.backend, bool(getattr(r, "replayed", False))
        out["measured"] = True
    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
        out["verdict"] = {"ok": False, "claims": [], "violations": [{"slot": "-", "rule": "VERDICT_UNAVAILABLE",
                                                                      "detail": f"{type(e).__name__}: {str(e)[:200]}"}]}
    out["violations"] = det["violations"] + out["verdict"]["violations"]
    out["ok"] = det["ok"] and out["verdict"]["ok"]
    return out


def majority(runs, lines):
    """Orchestrator ruling 07:42 (3): a verdict that flips on unchanged text is run THREE times (the seed differs, the
    text does not) and the majority decides. runs: check() results on the same segments and lines. Per line slot a
    run votes "pass" only when it was measured and its verdict holds no violation on that slot nor on the whole reply
    ("-"); a slot passes when more than half of the runs vote "pass" (an unmeasured run votes "fail", law L-m).
    -> a check()-shaped result: the seed-free deterministic layer, the first run's claims, every violation of a slot
    the majority fails (plus VERDICT_MAJORITY with the votes), "runs" (n) and "majority" = {"votes": {slot: [...]},
    "splits": [slots whose votes differ], "runs": [per run: seed, backend, measured, replayed, ok, violations]}. A
    split is recorded, never hidden (the ruling: recorded in the package and named in the caption)."""
    if not runs or len(runs) % 2 == 0:
        raise ValueError(f"majority needs an odd number of runs, got {len(runs)}")
    slots = [ln["slot"] for ln in lines]
    whole = lambda v: v.get("slot") == "-" or v.get("slot") not in slots   # an unknown slot fails every slot (C1 H1)
    votes = {}
    for s in slots:
        votes[s] = ["pass" if r.get("measured") and not any(
            v.get("slot") == s or whole(v) for v in (r.get("verdict") or {}).get("violations") or []) else "fail"
            for r in runs]
    failed = [s for s, vs in votes.items() if 2 * vs.count("pass") <= len(runs)]
    viol, seen = [], set()
    for s in failed:
        viol.append({"slot": s, "rule": "VERDICT_MAJORITY", "detail": f"votes {votes[s]} (seeds "
                                                                        f"{[r.get('seed') for r in runs]})"})
        for r in runs:
            for v in (r.get("verdict") or {}).get("violations") or []:
                k = (v.get("slot"), v.get("rule"), v.get("detail"))
                if (v.get("slot") == s or whole(v)) and k not in seen:
                    seen.add(k)
                    viol.append(v)
    n_measured = sum(bool(r.get("measured")) for r in runs)
    reps = [r.get("replayed") for r in runs]
    base = runs[0]
    verdict = {"ok": 2 * n_measured > len(runs) and not failed,
               "claims": (base.get("verdict") or {}).get("claims") or [], "violations": viol}
    out = {"deterministic": base["deterministic"], "verdict": verdict,
           "backend": " / ".join(sorted({str(r.get("backend")) for r in runs})),
           "measured": 2 * n_measured > len(runs),
           "replayed": None if any(not isinstance(x, bool) for x in reps) else any(reps), "runs": len(runs),
           "majority": {"votes": votes, "splits": [s for s, vs in votes.items() if len(set(vs)) > 1],
                        "runs": [{"seed": r.get("seed"), "backend": r.get("backend"), "measured": r.get("measured"),
                                  "replayed": r.get("replayed"), "ok": bool((r.get("verdict") or {}).get("ok")),
                                  "violations": (r.get("verdict") or {}).get("violations") or []} for r in runs]}}
    out["violations"] = base["deterministic"]["violations"] + viol
    out["ok"] = base["deterministic"]["ok"] and verdict["ok"]
    return out
