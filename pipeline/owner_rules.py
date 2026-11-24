#!/usr/bin/env python3
"""pipeline/owner_rules.py -- RULING 162 (orchestrator 07:45 ET Nov 24, from PBX's review of pin afd8977d at 07:37),
both sides, ONE file: the builder loads it read-only (it seals VERSION and this file's sha256 on its rows) and the
render calls it at validate. It imports one pipeline module, canon (a decoder file: the same bytes in both trees by
the decoder lockstep, and the one normaliser of every comparison: test_canon's TestSites), nothing else.

(1) A CLIP NEVER ENDS WHILE THE SPEAKER IS STILL MID-SENTENCE, or mid-thought: out_edge() asks whether a clip's last
    sentence finishes the speaker's thought, given what the speaker says next. The reason for the rule (must-fail):
    afd8977d's opener (0shaXx_n870) "Stocks had fallen seven days in a row, Bitcoin was on its way to 55K, and everybody
    had the same story." -- the source goes on "The AI bubble had finally popped, and a full market crash was coming
    Monday morning." Both recognisers put a full stop after 'story' and a 490 ms pause follows, so the sentence law
    reads a sentence end there; the thought runs on past it.
(2) OUR LINES ADD VALUE, NEVER A LIST OF THE CHANNELS: line_faults() names what makes one of our voiceover lines (the
    intro, a bridge, the closing line) a listing: a credited channel's name, or one of LISTING_PHRASES. The sign-off
    (the outro tag's credits, law L-a) is not one of these lines."""
import json
import os
import re
import urllib.request

VERSION = "owner_rules 4 (ruling 162 + items 2, 7, 2026-11-24)"

OUT_EDGE_PROMPT = """You check where a short video clip ENDS. The clip is cut from a longer recording of one speaker. It
must never stop while the speaker's thought is unfinished: a viewer must never feel the speaker was cut off in the
middle of saying something.

WHAT THE SPEAKER SAID JUST BEFORE THE CLIP (context only):
<before>{before}</before>

THE CLIP (judge its LAST sentence):
<clip>{clip}</clip>

WHAT THE SPEAKER SAYS RIGHT AFTER THE CLIP, sentence by sentence (a transcript: its full stops can be wrong):
{after}

QUESTION: does the clip's last sentence FINISH the speaker's thought as it stands?
Answer "no" only when a viewer hearing the clip alone would feel the speaker was cut off: the clip's last words set up
something that a following sentence delivers (for example "and the reason is simple." followed by the reason; "here
is what nobody tells you." followed by it; "there were three warning signs." followed by them), a following sentence
is really the rest of the same sentence, or the clip stops on an unfinished clause.
Answer "yes" when the last sentence is complete in itself, even when the speaker goes on to explain it, give an
example, interpret it or start a new point on the same topic.
If "no": "finishes_at" is the number in brackets of the FIRST following sentence at whose end the thought is finished,
or null when none of the listed sentences finishes it.
Reply with JSON only: {{"complete": "yes|no", "finishes_at": <number or null>, "why": "<one short sentence>"}}"""

LISTING_PHRASES = ("in the words of", "in their words", "in their own words", "in their own clips",
                   "as these clips show", "three takes on")

SENTENCE_END = re.compile(r"[.?!][\"')\]”’]*$")


def sentences(words, n, forward=True):
    """Up to n sentences of a decoder's words ([{"word": ...}] or strings), split after each word that ends in . ? or !
    (quotes and brackets after it allowed). forward: the first n of `words`; else the LAST n. A stretch with no full
    stop at its end is still a sentence: the recording ends there."""
    out, cur = [], []
    for w in words or []:
        t = str(w.get("word") if isinstance(w, dict) else w).strip()
        if not t:
            continue
        cur.append(t)
        if SENTENCE_END.search(t):
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out[:n] if forward else out[-n:] if n else []


def _first_json(text, key):
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", text or ""):
        try:
            obj, _ = dec.raw_decode(text, m.start())
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and key in obj:
            return obj
    return None


def _unmeasured(why, backend=None):
    return {"complete": None, "finishes_at": None, "why": why, "backend": backend, "measured": False,
            "version": VERSION}


def answer_key(prompt, coords):
    """The out-edge answer's cache key (orchestrator 09:45 ET Nov 24): this file's VERSION, the exact prompt (the clip's
    words, the words before and after it: the transcript) and the caller's cut coordinates. A changed cut, transcript
    or prompt version is another key: the old answer is void."""
    import hashlib
    return hashlib.sha256(json.dumps({"version": VERSION, "prompt": prompt, "coords": coords}, sort_keys=True,
                                     default=str).encode()).hexdigest()


def out_edge(router, clip_text, before_text, next_sentences, seed=7, role="out_edge", max_tokens=2000,
             no_answer=(Exception,), cache_dir=None, coords=None, frozen=False, **call_kw):
    """RULING 162 (1): does the clip's last sentence finish the speaker's thought? router.call(role, prompt,
    max_tokens=, seed=, **call_kw) -> a reply with .text and .backend (the builder's providers.Router, or the render's
    HeimdallText). -> {"complete": True / False / None, "finishes_at": the 0-based index into next_sentences of the
    sentence that finishes the thought, or None, "why", "backend", "measured", "version"}.
    measured False (an exception of the `no_answer` kinds, a reply that is not the JSON asked for): the edge is
    UNVERIFIED (ruling 160 (2a)): never a pass, never a refusal; the caller says which check could not be answered.
    An exception of any other kind propagates (the builder's spend stop, a kill).
    cache_dir (orchestrator 09:45 ET Nov 24): a measured answer is stored under answer_key(prompt, coords) and served
    again for the same key ("cached": True); frozen=True (the replay) serves stored answers only and never asks: a key
    with no stored answer is measured False, open work, never a pass."""
    after = [str(s).strip() for s in next_sentences or [] if str(s).strip()]
    prompt = OUT_EDGE_PROMPT.format(
        before=" ".join(str(before_text or "").split()) or "(the clip starts the recording)",
        clip=" ".join(str(clip_text or "").split()),
        after="\n".join(f"[{i}] {s}" for i, s in enumerate(after)) or "(none: the recording ends with the clip)")
    key = answer_key(prompt, coords)
    path = os.path.join(cache_dir, key[:2], f"{key}.json") if cache_dir else None
    if path and os.path.exists(path):
        try:
            with open(path) as f:
                stored = json.load(f)
            if stored.get("key") == key and stored.get("measured") is True:
                return dict(stored, cached=True)
        except (OSError, ValueError, AttributeError):
            pass                                                     # unreadable: asked again (or open work)
    if frozen:
        return dict(_unmeasured("no frozen answer for this edge: open work"), key=key)
    try:
        rep = router.call(role, prompt, max_tokens=max_tokens, seed=seed, **call_kw)
    except no_answer as e:
        return dict(_unmeasured(f"no answer: {type(e).__name__}: {str(e)[:300]}"), key=key)
    backend = getattr(rep, "backend", None)
    obj = _first_json(getattr(rep, "text", "") or "", "complete") or {}
    a = str(obj.get("complete", "")).strip().lower()
    if a not in ("yes", "no"):
        return dict(_unmeasured(f"unreadable reply: {str(getattr(rep, 'text', ''))[:300]!r}", backend), key=key)
    fin = obj.get("finishes_at")
    if isinstance(fin, str) and fin.strip().isdigit():
        fin = int(fin.strip())
    elif isinstance(fin, float) and fin.is_integer():           # batch 127 c1 (glm F1): 2.0 is sentence 2
        fin = int(fin)
    if a == "yes" or isinstance(fin, bool) or not isinstance(fin, int) or not 0 <= fin < len(after):
        fin = None
    out = {"complete": a == "yes", "finishes_at": fin, "why": " ".join(str(obj.get("why") or "").split())[:300],
           "backend": backend, "measured": True, "version": VERSION, "key": key}
    if path:                                                         # a measured answer only (no answer = open work)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".tmp", "w") as f:
            json.dump(dict(out, coords=coords), f, default=str)
        os.replace(path + ".tmp", path)
    return out


# ITEM 7 (orchestrator 09:20 / 09:35 ET Nov 24, "NO SILENT MEANING SWAP"): a differing pair whose two sides sit on one
# meaning axis with different values changes what was said ('approved' / 'rejected', 'million' / 'billion'). ONE list,
# both sides: the builder's attest.critical and the render's G18 and lock pre-check call meaning_pair.
MEANING_PAIRS = (
    ("trade", ("buy", "buys", "buying", "bought", "buyer", "buyers"),
              ("sell", "sells", "selling", "sold", "seller", "sellers")),
    ("direction", ("up", "higher", "rise", "rises", "rising", "rose", "risen", "gain", "gains", "gained", "rally",
                   "rallies", "rallied", "surge", "surges", "surged", "climb", "climbs", "climbed", "jump", "jumps",
                   "jumped", "increase", "increases", "increased", "above", "inflow", "inflows", "pump", "pumped"),
                  ("down", "lower", "fall", "falls", "falling", "fell", "fallen", "loss", "losses", "lost", "drop",
                   "drops", "dropped", "plunge", "plunges", "plunged", "decline", "declines", "declined", "decrease",
                   "decreases", "decreased", "below", "outflow", "outflows", "dump", "dumped", "crash", "crashed")),
    ("sentiment", ("bull", "bulls", "bullish"), ("bear", "bears", "bearish")),
    ("position", ("long", "longs"), ("short", "shorts")),
    ("quantity", ("more", "most", "many"), ("less", "least", "fewer", "few")),
    ("approval", ("approve", "approves", "approved", "approval", "approving", "accept", "accepts", "accepted", "allow",
                  "allows", "allowed", "pass", "passes", "passed", "win", "wins", "won", "yes"),
                 ("reject", "rejects", "rejected", "rejection", "rejecting", "deny", "denies", "denied", "denial",
                  "block", "blocks", "blocked", "fail", "fails", "failed", "lose", "loses", "lost", "no")),
    ("factor", ("double", "doubles", "doubled", "doubling", "triple", "tripled"), ("half", "halve", "halves", "halved",
                                                                                      "halving")),
)
SIZE_WORDS = {"hundred": 2, "hundreds": 2, "thousand": 3, "thousands": 3, "million": 6, "millions": 6, "billion": 9,
              "billions": 9, "trillion": 12, "trillions": 12}


def _meaning(tokens):
    """{(axis, value)} of the words among `tokens` (canon tokens) that sit on a meaning axis."""
    out = set()
    for t in tokens:
        for axis, plus, minus in MEANING_PAIRS:
            if t in plus:
                out.add((axis, "+"))
            if t in minus:
                out.add((axis, "-"))
        if t in SIZE_WORDS:
            out.add(("size", SIZE_WORDS[t]))
    return out


def _scale(tok):
    """(significant digits, power of ten) of a canon number token ('10000000' -> ((1,), 7); '1500000' -> ((1, 5), 5)),
    or None (not a number, or zero)."""
    from decimal import Decimal, InvalidOperation
    try:
        d = Decimal(str(tok))
    except (InvalidOperation, ValueError):
        return None
    if not d.is_finite() or d == 0:
        return None
    t = d.normalize().as_tuple()
    return t.digits, len(t.digits) + t.exponent


def _scale_word(tok):
    """The scale word a canon number reads with: 0 under a thousand, 1 thousand, 2 million, 3 billion, 4 trillion or
    more; None for a token that is not a number."""
    v = _scale(tok)
    if v is None:
        return None
    return min(4, max(0, (v[1] - 1) // 3))


def size_pair(xs, ys):
    """ITEM 7's sizes on NUMBERS (orchestrator 10:50 ET Nov 24: "thousand/million/billion/trillion in general"; canon
    folds 'ten million' / 'ten billion' to 10000000 / 10000000000, so the size words are gone): two numbers whose scale
    words differ, one of them a thousand or more ('ten million' / 'ten billion', '12 billion' / '15 trillion',
    15,000,500 / 15,500: million against thousand), or with the SAME significant digits at least 100 times apart
    ('two million' / 'two hundred million'). 20 against 2 and 15,500 against 55,000 are not: ordinary number pairs.
    One definition: the builder's selection calls this function too."""
    a = [(_scale(t), _scale_word(t)) for t in xs if _scale(t)]
    b = [(_scale(t), _scale_word(t)) for t in ys if _scale(t)]
    return any((wa != wb and max(wa, wb) >= 1) or (va[0] == vb[0] and abs(va[1] - vb[1]) >= 2)
               for va, wa in a for vb, wb in b)


def meaning_pair(x, y):
    """ITEM 7: True when the two sides of a differing pair (x, y: lists of words; read as canon tokens) put a word on
    the same meaning axis with a DIFFERENT value: buy / sell, up / down, approved / rejected, million / billion, doubled
    / halved and the rest of MEANING_PAIRS and SIZE_WORDS, or two numbers of one size apart (size_pair). A word form of
    the same word ('bottom' / 'bottomed') or a word on one side only is not one. Such a pair is material: it holds,
    and is never adopted silently."""
    import canon
    tx = canon.canon_tokens(" ".join(str(t) for t in x or []))
    ty = canon.canon_tokens(" ".join(str(t) for t in y or []))
    xs, ys = _meaning(tx), _meaning(ty)
    return any(a == b and v != w for a, v in xs for b, w in ys) or size_pair(tx, ty)


def _stands_in(line, sub):
    """sub (canon tokens) stands in line (canon tokens) in order and side by side; its LAST word may differ by a
    possessive or plural ending (canon.word_form, ruling 142 (2): "brunell's" is 'Brunell')."""
    import canon
    n = len(sub)
    for i in range(len(line) - n + 1):
        w = line[i:i + n]
        if w == sub or (n and w[:-1] == sub[:-1] and canon.word_form([w[-1]], [sub[-1]])):
            return True
    return False


ABBREVIATION = re.compile(r"^(?:[A-Za-z]\.){2,}$|^(?:mr|mrs|ms|dr|vs|etc|inc|jr|sr|st|no)\.$", re.I)


def sentence_count(text):
    """ITEM 2: the sentences of one line of ours: a word ending in . ? or ! (closing quotes or brackets after it) ends
    one when another word follows it and that word opens with a capital or a digit; an abbreviation ('U.S.', 'Dr.')
    ends none."""
    ws = str(text or "").split()
    ends = sum(1 for i, w in enumerate(ws[:-1]) if SENTENCE_END.search(w) and not ABBREVIATION.match(w.strip("\"')]"))
               and (ws[i + 1][:1].isupper() or ws[i + 1][:1].isdigit()))
    return ends + 1 if ws else 0


def line_faults(text, names, clip_texts=None):
    """RULING 162 (2): what makes `text`, one line of ours, a listing: "names '<name>'" for each of `names` (the
    credited channels' display names and aliases) whose canon tokens stand in the line's (canon.canon_tokens: case,
    punctuation and number words folded) in order and side by side, a possessive or plural ending on the last word
    allowed, and "says '<phrase>'" for each LISTING_PHRASES phrase in it. [] when nothing makes it one. A one-word
    channel name that is also a plain word ('Strike', 'Unchained') is matched as that word: such a line is held.
    ITEM 2 (orchestrator 09:20 ET Nov 24), checked before any model: "more than one sentence" (sentence_count), and,
    when clip_texts (the clips' own words) are given, "says '<n>', which no clip says" for each number the line WRITES
    WITH DIGITS ('$55,000', '20%') that no clip's canon tokens carry; a number word ('one', 'first') is not a digit."""
    import canon
    line = canon.canon_tokens(str(text or ""))
    faults = []
    for n in names or []:
        toks = canon.canon_tokens(str(n or ""))
        if toks and _stands_in(line, toks) and f"names '{n}'" not in faults:
            faults.append(f"names '{n}'")
    for p in LISTING_PHRASES:
        if _stands_in(line, canon.canon_tokens(p)):
            faults.append(f"says '{p}'")
    if sentence_count(text) > 1:
        faults.append("more than one sentence")
    if clip_texts is not None:                       # numbers the line WRITES with digits only (the builder, 11:0x
        said = {t for c in clip_texts for t in canon.canon_tokens(str(c or ""))}   # ET: canon folds 'one', 'first',
        ws = str(text or "").split()                                               # 'three' to digits: never theirs);
        for t, f, l in canon.canon_spans(ws):        # the whole line read by canon ('3.5 billion' is 3500000000),
            if any(ch.isdigit() for ch in t) and any(ch.isdigit() for w in ws[f:l + 1] for ch in w) \
                    and t not in said and f"says '{t}', which no clip says" not in faults:   # a token counted only
                faults.append(f"says '{t}', which no clip says")                         # when its words had a digit
    return faults


DIGIT_FAULT = "which no clip says"


def line_rules(text, names, clip_texts=None):
    """ITEM 2's categories, decided HERE once for both sides (orchestrator 11:20 ET Nov 24: a side that mapped every
    fault to LISTING read 'The floor held. Watch Monday.' as a listing): "LISTING" only for a credited channel's name or
    a listing phrase; "ONE_SENTENCE" for more than one sentence; "DIGIT" for a number no clip says. -> the codes found,
    in that order; [] for a clean line."""
    f = line_faults(text, names, clip_texts=clip_texts)
    codes = []
    if any(x.startswith("names '") or (x.startswith("says '") and not x.endswith(DIGIT_FAULT)) for x in f):
        codes.append("LISTING")
    if "more than one sentence" in f:
        codes.append("ONE_SENTENCE")
    if any(x.endswith(DIGIT_FAULT) for x in f):
        codes.append("DIGIT")
    return codes


class HeimdallText:
    """The render's router for out_edge: ONE Heimdall gateway model, temperature 0 (free). The key is read by NAME
    from the repo .env and never printed. .call() raises on any route error (out_edge: measured False)."""
    BASE = "https://api-staging.heimdallm.com/api/v1"

    def __init__(self, model="qwen/qwen3.8-27b", timeout=300):
        self.model, self.timeout = model, timeout

    def _key(self):
        env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        with open(env) as f:
            for line in f:
                if "=" in line and line.split("=", 1)[0].strip() == "HEIMDALL_API_KEY":   # the exact NAME (c2, glm F2)
                    return line.split("=", 1)[1].strip().strip('"\'')
        raise RuntimeError("HEIMDALL_API_KEY not found in the repo .env")

    def call(self, role, prompt, max_tokens=2000, seed=7, **_kw):
        body = {"model": self.model, "temperature": 0, "seed": seed, "max_tokens": max_tokens,
                "reasoning": {"effort": "low"}, "messages": [{"role": "user", "content": prompt}]}
        req = urllib.request.Request(f"{self.BASE}/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {self._key()}",
                                              "Content-Type": "application/json"})
        raw = json.loads(urllib.request.urlopen(req, timeout=self.timeout).read())
        first = (raw.get("choices") or [{}])[0] if isinstance(raw, dict) else {}       # batch 127 c1 (glm F2):
        msg = first.get("message") if isinstance(first, dict) else None               # a malformed body reads as
        text = msg.get("content") if isinstance(msg, dict) else ""                    # no text (no answer)
        text = text if isinstance(text, str) else ""

        class Reply:
            pass
        rep = Reply()
        rep.text, rep.backend = text, f"heimdall:{self.model}"
        return rep
