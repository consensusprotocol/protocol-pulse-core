#!/usr/bin/env python3
"""pipeline/eligibility.py — ONE eligibility predicate for Pulse Check selection (orchestrator 2026-11-12 00:32 ET).

    eligible(item, ctx) -> Result

is the one question every selection step asks: may this source, these whole sentences or this line-up be used, in
this role, now? Today the answer is spread over editorial_select, stand_alone, sentence_law, select_passages,
transcript_ingest, transcript_store, edl_rules and run_fresh, and those places disagree; docs/audits/
SELECT_BY_ID_DESIGN.md section 4 lists every rule with file:line and, where two places disagree, takes the stricter.
Pure: no model, no file, no network, no clock (ctx.now is handed in). A rule that cannot be measured on what it is
handed fails closed (law L-j); nothing measured is never a pass (law L-m).

item    Source   one video: registry partner, channel identity, freshness, v2f material, uploads only, layout
        Span     whole sentences k0..k1 of ONE Source, in a role: 'evidence' (a statement a story rests on),
                 'hook' or 'clip' (heard on screen)
        Lineup   a story (evidence spans and its claim) and, once chosen, the hook and 2-3 clips in play order
ctx     Context  now (aware UTC), the channel registry, the role, the story statements an on-screen span must carry,
                 the delivered-story ledger, clip-scorer verdicts (stand_alone's one exception, rule T8)
Result           ok; reasons (EVERY blocking reason, named, with its detail); facts (measured either way:
                 layout_eligible, age_h, tier, duration_s, ...); parts (a Lineup's per-span results)

Layout eligibility is measured for every item and reported as the fact `layout_eligible`; for an on-screen role it is
also the blocking reason 'layout_ineligible' (since RULING 93, 23:58 ET Nov 13: only a channel with no registry id; the
frames of each clip are judged at the pin stage, visual_pin.layout_block).
"""
import math
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from difflib import SequenceMatcher

import canon
import sentence_law
import stand_alone
import transcript_store

# ── law constants: their ONE home (design doc section 4 cites where each lives today; tests/eligibility pins them
#    equal to those modules until the wiring patch makes those modules import them from here) ──
UNIVERSE_HOURS = 72                         # S5 editorial_select.py:41; transcript_ingest.py:55
TIER_HOURS = (48, UNIVERSE_HOURS)           # S5 editorial_select.py:57 (DEC-13 a: 48 h first, 72 h max)
MIN_COVERAGE_CHANNELS = 2                   # G1 editorial_select.py:47
MIN_LAYOUT_CHANNELS = 2                     # G3 editorial_select.py:48
HOOK_S = (8.0, 12.0)                        # T10 editorial_select.py:49: a TARGET that ranks, never rejects (law L-o)
CLIP_S = (12.0, 20.0)                       # T10 editorial_select.py:50: a TARGET (law L-o)
RUNTIME_S = (60.0, 70.0)                    # L1b law L-o (PBX 2026-11-12 01:50): the hard length rule, total runtime
TAIL_S = 14.30                              # what a final adds to its segments' word spans (credits card, outro, cut
                                            # leads / tails, pads): the approved preview's finals 71.08 s (DoD 14:47)
                                            # minus its four word spans 56.78 s (references/pulse_preview_2026-11-11)
MAX_WINDOW_SENTENCES = 3                    # T9 editorial_select.py:52; recorded only since ruling 35
N_CLIPS = (2, 3)                            # L1 >= 2: edl_rules.py:220; <= 3: editorial_select.py:54
MAX_SPANS_PER_VIDEO = 2                     # L4 editorial_select.py:55 (MAX_VERIFIED_QUOTES_PER_VIDEO)
MAX_CLIPS_PER_CHANNEL = 2                   # L5 editorial_select.py:1291; select_passages.py:291
ADJ_MAX_START_S = 8.0                       # T13 editorial_select.py:367 (D4 b)
ADJ_MAX_PER_DIRECTION = 2                   # T13 editorial_select.py:368 (D4 cap)
SAME_STATEMENT_RUN = 5                      # T13 / G6 editorial_select.py:1045
MIN_STATEMENT_TOKENS = 5                    # T14 story_semantics.py:372 (quote_in: a quote counts with >= 5 tokens)
HOOK_LEAD_S = sentence_law.HEAD_LEAD_MIN_S  # T12 sentence_law.py:57 (D1; G17a's hook lead; GPT-cut F12)
CLIP_SCORER_MIN = stand_alone.CLIP_MIN_SCORE  # T8 stand_alone.py:30
BITCOIN_TERMS = re.compile(r"\b(bitcoins?|btcs?)\b", re.I)          # T11 / G2 editorial_select.py:59
# RULING 34 (orchestrator 03:12 ET Nov 13; the render's side merged at 55315124): the miner's about-Bitcoin screen,
# verbatim, is the per-segment topic test of a moments package. It is sealed into every moments pin (package_pin:
# moments_package.btc_screen), and the render's stand_alone.check_edl applies exactly the sealed pattern.
BTC_SCREEN_SOURCE = "pp-ingest pipeline/ingest/mine.py@8e6afb61"
BTC_SCREEN = re.compile(r"\b(bitcoins?|btc|sats|satoshis?|halving|hash ?rate|lightning network|self[- ]custody|"
                        r"cold storage|microstrategy|mstr|ibit|saylor)\b", re.I)
V2F_VIDEO_IDS = frozenset({"RBFN4CB60To", "Pxrak-iMT0g", "QCgW8RlTu5Q"})   # S3 editorial_select.py:60
CONTINUATION_OPENERS = frozenset(stand_alone.CONJUNCTIONS)          # T8 = editorial_select.py:127
INTERJECTIONS = frozenset({"oh", "ah", "wow", "yeah", "yes", "right", "okay", "mhm", "hmm", "huh", "wait", "sure",
                           "exactly", "true"})                     # T9 / T13 editorial_select.py:372
BACKREF_WORDS = frozenset({"this", "that", "these", "those", "it", "its", "they", "them", "their"})   # :369
BACKREF_PHRASES = ("what just happened", "what happened", "the hack", "the breach")                   # :370
NOT_ENTITY = frozenset({"I", "The", "This", "That", "These", "Those", "It", "And", "But", "So", "We", "You", "They",
                        "He", "She", "A", "An", "In", "On", "Of", "To", "Yeah", "Oh", "Okay", "Well", "Now", "Look"})  # :374
SUBJECT = ("bitcoin", "btc")                # stand_alone.subject_terms for a Bitcoin story (stand_alone.py:70)
ROLES = ("evidence", "hook", "clip")
ON_SCREEN = ("hook", "clip")


# ── data ──

@dataclass(eq=False)
class Source:
    """One video's transcript as the record wrote it. tokens: ({'word', 'start', 'end'}, ...) in order; timing
    'word' = each token carries its own timestamps (a word record), 'segment' = times interpolated inside caption /
    segment lines (never enough for an on-screen role). file_head: the first token is the media's first word; False
    unless the caller asserts it (a window transcript starts mid-file). vod: True only when the caller establishes an
    upload (not a Short / live / upcoming stream); None = not established = ineligible."""
    video_id: str
    channel_id: object
    channel_name: object
    published_at: object
    transcript_sha256: object
    transcript_method: object
    tokens: tuple
    timing: str = "segment"
    file_head: bool = False
    vod: object = None
    title: str = ""
    _sentences: object = field(default=None, repr=False)
    _ready: object = field(default=None, repr=False)

    @property
    def sentences(self):
        if self._sentences is None:
            self._sentences = split_sentences(self.tokens)
        return self._sentences


@dataclass(eq=False)
class Span:
    """Whole sentences k0..k1 (indices into source.sentences) of one Source."""
    source: Source
    k0: int
    k1: int

    def _valid(self):
        n = len(self.source.sentences)
        return isinstance(self.k0, int) and isinstance(self.k1, int) and 0 <= self.k0 <= self.k1 < n

    @property
    def w0(self):
        return self.source.sentences[self.k0][0]

    @property
    def w1(self):
        return self.source.sentences[self.k1][1]

    @property
    def text(self):
        """The span as spoken (law L-h: transcript_store.read_text of the record's own words, never rewritten)."""
        return spoken(self.source.tokens[self.w0:self.w1 + 1])

    @property
    def start(self):
        return self.source.tokens[self.w0]["start"]

    @property
    def end(self):
        return self.source.tokens[self.w1]["end"]

    @property
    def key(self):
        return (self.source.video_id, self.source.transcript_sha256, self.k0, self.k1)


@dataclass(eq=False)
class Lineup:
    """story: evidence spans (one sentence each in select_by_id); claim: one of them; hook / clips once chosen."""
    story: tuple
    claim: object
    hook: object = None
    clips: tuple = ()


@dataclass
class Context:
    now: datetime
    registry: list
    role: str = "evidence"
    story: object = None          # ((video_id, canon tokens), ...): the statements an on-screen span must carry
    event: str = ""               # the claim sentence, verbatim: its proper names are the event's names (D4 a)
    ledger: tuple = ()            # story_ledger entries (dicts with 'evidence': [{'video_id', 'quote_tokens', ...}])
    scorer: object = None         # {span.key: (score, fault)}: clip-scorer verdicts handed in by the caller

    def __post_init__(self):
        if not isinstance(self.now, datetime) or self.now.tzinfo is None:
            raise ValueError("Context.now must be an aware datetime (the run clock, UTC)")
        if self.role not in ROLES:
            raise ValueError(f"role {self.role!r} not in {ROLES}")
        self._by_cid = {c["channel_id"]: c for c in self.registry or [] if isinstance(c, dict) and c.get("channel_id")}

    def channel(self, channel_id):
        return self._by_cid.get(channel_id)


@dataclass
class Reason:
    name: str
    detail: str


@dataclass
class Result:
    ok: bool
    reasons: list
    facts: dict
    parts: dict = field(default_factory=dict)

    def names(self):
        return [r.name for r in self.reasons]

    def why(self):
        return "; ".join(f"{r.name}: {r.detail}" for r in self.reasons)

    def to_dict(self):
        return {"ok": self.ok, "reasons": [[r.name, r.detail] for r in self.reasons], "facts": self.facts,
                "parts": {k: v.to_dict() for k, v in self.parts.items()}}


# ── text helpers (every comparison through canon, law L-k) ──

def spoken(tokens):
    """Tokens as spoken text (law L-h)."""
    return transcript_store.read_text(" ".join((t.get("word") or "").strip() for t in tokens))


def split_sentences(tokens):
    """Whole sentences as token-index ranges: a sentence ends after a terminal mark that is not an abbreviation or
    '...' (sentence_law.is_terminal, rule T1); the record's last words form its last (possibly unfinished) sentence."""
    out, s0 = [], 0
    for i, t in enumerate(tokens):
        if sentence_law.is_terminal(t.get("word")):
            out.append((s0, i))
            s0 = i + 1
    if s0 < len(tokens):
        out.append((s0, len(tokens) - 1))
    return out


def heads(text):
    """Canonical words with contractions reduced to their heads (stand_alone._words; editorial_select._lc_words)."""
    return canon.canon_tokens(text, heads=True)


def numbers(text):
    return {t for t in canon.canon_tokens(text) if re.fullmatch(r"\d+(?:\.\d+)?", t)}


def names_bitcoin(text):
    """Rule T11 / G2: Bitcoin is named by BOTH of today's tests (the cluster screen's regex, editorial_select.py:59,
    and stand_alone's canonical-token test, stand_alone.py:75-77); where they disagree the text does not count."""
    return bool(BITCOIN_TERMS.search(text or "")) and stand_alone.topical("hook", text, subject=SUBJECT)[0]


def same_statement(a, b):
    """editorial_select._same_statement on canonical tokens: a shared run of SAME_STATEMENT_RUN consecutive tokens, or
    the shorter one wholly inside the other."""
    if not a or not b:
        return False
    run = max(m.size for m in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    return run >= min(SAME_STATEMENT_RUN, len(a), len(b))


def event_names(event):
    """The event's names in the id contract: the proper names of the claim sentence (its source's own words); today
    these came from the derived query's entity list (editorial_select.py:391-399). The sentence's first word is a name
    only when it names Bitcoin or recurs capitalised later ('As of this morning, Bitcoin ...' gives Bitcoin, not 'As')."""
    toks = re.findall(r"[A-Za-z][A-Za-z0-9]*", event or "")
    later = {t for t in toks[1:] if t[0].isupper()}
    return {t for i, t in enumerate(toks) if t[0].isupper() and t not in NOT_ENTITY and len(t) >= 2
            and (i > 0 or t in later or BITCOIN_TERMS.fullmatch(t))}


def states(sentence, statement):
    """A sentence states a story statement (both canonical tokens): it holds a run of SAME_STATEMENT_RUN consecutive
    tokens of it, or the whole statement when that is shorter. Asymmetric on purpose: same_statement() lets a
    one-word sentence ('Right.') match any statement holding that word."""
    if not sentence or not statement:
        return False
    run = max(m.size for m in SequenceMatcher(None, sentence, statement, autojunk=False).get_matching_blocks())
    return run >= min(SAME_STATEMENT_RUN, len(statement))


def _anchor_entities(anchor, event=""):
    """editorial_select._anchor_entities: the event's names the anchor itself says, plus the anchor's capitalised
    words after its first (minus common sentence openers)."""
    names = {n for n in event_names(event)
             if re.search(r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9])", anchor or "", re.I)}
    toks = re.findall(r"[A-Za-z][A-Za-z0-9]*", anchor or "")
    return names | {t for i, t in enumerate(toks) if i > 0 and t[0].isupper() and t not in NOT_ENTITY}


def backward_reference(text, anchor, event=""):
    """D4 (a), deterministic (editorial_select.backward_reference, editorial_select.py:402-415): a deictic / pronoun,
    a definite back-reference, a named entity or a number shared with the anchor. Entities: the event's names (the
    claim's, standing in for the derived query's entity list) said in the anchor, and the anchor's own capitalised
    words. The 'event nouns' half read the derived query's action / object phrases, which the id contract does not
    have: that half is dropped (stricter); the entity half takes the claim's names where today took the query's."""
    lw = heads(text)
    low = " ".join(lw)
    found = sorted(BACKREF_WORDS & set(lw))
    found += [p for p in BACKREF_PHRASES if re.search(r"\b" + re.escape(p) + r"\b", low)]
    found += [f"entity {e}" for e in sorted(_anchor_entities(anchor, event))
              if re.search(r"(?<![A-Za-z0-9])" + re.escape(e) + r"(?![A-Za-z0-9])", text or "", re.I)]
    found += [f"number {n}" for n in sorted(numbers(anchor) & numbers(text))]
    return ", ".join(found) or None


def interjection_only(text):
    lw = heads(text)
    return set(lw) <= INTERJECTIONS          # an empty sentence is transparent too (editorial_select._n_sentences)


def ends_statement(word):
    """editorial_select._ends_statement: '.' or '!' that is not an abbreviation; never '?'."""
    return sentence_law.is_terminal(word) and not (word or "").rstrip().rstrip("\"')]”’").endswith("?")


def sentence_ready(src):
    """Rule S7 (law L-e; transcript_store.sentence_ready): word timestamps and a record the sentence law can read:
    punctuation restored, or no stretch that needs restoring."""
    if src._ready is None:
        import punctuation
        src._ready = bool(src.timing == "word" and src.tokens and (
            src.transcript_method == "whisper_words_punct" or not punctuation.needs_restoration(list(src.tokens))))
    return src._ready


def _parse_time(s):
    """An upload time: aware ISO-8601 only. A missing or timezone-less time is no measurement (S5, Grok47-select F15)."""
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo is not None else None


def _time(tok, key):
    """A token's start / end as a finite number, or None: a missing, non-numeric or non-finite (NaN / inf) time is no
    measurement (never read as 0; every comparison with NaN is False, which would pass a gap rule: audit C2)."""
    v = tok.get(key)
    return float(v) if type(v) in (int, float) and math.isfinite(v) else None


def age_hours(published_at, now):
    d = _parse_time(published_at)
    return None if d is None else (now - d).total_seconds() / 3600


def layout_ok(reg):
    """Rule S6: a registry channel with an id. RULING 93 (orchestrator 23:58 ET Nov 13): DEC-12d is measured per CLIP,
    not per channel. No channel is layout_ineligible by name: every clip, any channel, is judged on its own frames by
    the pin-stage visual check (visual_pin.layout_block: a ticker or crawl, or a lower third the 9:16 crop would cut
    mid-word or that covers the speaker). The registry's has_chyron is a hint that orders that check, nothing more."""
    return bool(reg and reg.get("channel_id"))


# ── the predicate ──

def eligible(item, ctx):
    if isinstance(item, Lineup):
        return _lineup(item, ctx)
    if isinstance(item, Span):
        return _span(item, ctx, ctx.role)
    if isinstance(item, Source):
        reasons, facts = _source(item, ctx, ctx.role)
        return Result(not reasons, reasons, facts)
    return Result(False, [Reason("bad_item", f"not a Source, Span or Lineup: {type(item).__name__}")], {})


def _source(src, ctx, role):
    reasons, facts = [], {"video_id": src.video_id}
    R = lambda name, detail: reasons.append(Reason(name, detail))
    reg = ctx.channel(src.channel_id) if src.channel_id else None
    facts["channel"] = reg.get("display_name") if reg else src.channel_name
    facts["channel_id"] = src.channel_id
    if not (src.channel_id and src.channel_name):
        R("no_channel_identity", "the transcript carries no channel id / name (E-FAIL-030): no channel's evidence")
    elif reg is None:
        R("not_partner_channel", f"channel_id {src.channel_id} is not in the registry (DEC-6)")
    elif reg.get("enabled") is not True:
        R("not_partner_channel", f"{reg.get('display_name')} is not enabled in the registry")
    facts["layout_eligible"] = layout_ok(reg)
    if src.video_id in V2F_VIDEO_IDS:
        R("v2f_material", f"{src.video_id} is a v2f source video")
    if src.vod is not True:
        R("not_vod", "not established as an upload (a Short, live or upcoming stream is not)" if src.vod is None
          else "a Short, live or upcoming stream is not an upload")
    age = age_hours(src.published_at, ctx.now)
    facts["age_h"] = None if age is None else round(age, 2)
    if age is None:
        R("not_current", f"no timezone-aware upload time ({src.published_at!r}): freshness not measured")
    elif age < 0:
        R("not_current", f"upload time {src.published_at} is after the run clock (invalid metadata)")
    elif age > UNIVERSE_HOURS:
        R("not_current", f"uploaded {age:.1f} h before the run > {UNIVERSE_HOURS} h")
    facts["tier"] = None if age is None or age < 0 or age > UNIVERSE_HOURS else \
        next(f"{h}h" for h in TIER_HOURS if age <= h)
    if not src.transcript_sha256:
        R("no_transcript_identity", "no transcript sha256")
    if not src.tokens:
        R("no_transcript", "no transcript words")
    if role in ON_SCREEN:
        if not facts["layout_eligible"]:
            R("layout_ineligible", f"{facts['channel']}: no registry channel id")   # ruling 93: never by name
        if not sentence_ready(src):
            R("not_sentence_ready", "no sentence-ready word record (law L-e): " +
              ("segment timing only" if src.timing != "word" else "a stretch reads unpunctuated"))
    return reasons, facts


def _span(span, ctx, role):
    src = span.source
    reasons, facts = _source(src, ctx, role)
    R = lambda name, detail: reasons.append(Reason(name, detail))
    if not span._valid():
        R("bad_span", f"sentences {span.k0}..{span.k1} not in 0..{len(src.sentences) - 1}")
        return Result(False, reasons, facts)
    toks, S = src.tokens, src.sentences
    w0, w1 = span.w0, span.w1
    text = span.text
    facts.update(k0=span.k0, k1=span.k1, text=text, start=span.start, end=span.end)
    # T2 / T3 whole sentences
    if w0 == 0 and not src.file_head:
        R("fragment", "starts at the first word of a window that begins mid-file: no evidence of a sentence start")
    elif w0 > 0 and not sentence_law.is_terminal(toks[w0 - 1].get("word")):
        R("fragment", f"previous word {toks[w0 - 1].get('word')!r} has no terminal punctuation")
    last = toks[w1].get("word")
    if not sentence_law.is_terminal(last):
        R("fragment", f"ends on {last!r}: no terminal punctuation")
    elif not ends_statement(last) and role != "hook":   # RULING 37 (03:12 ET Nov 13): a question may end the HOOK only;
        R("not_statement", "ends on a question")         # the clips-alone verdict judges the join after it (package.py)
    # T5 lexical evidence at both boundaries (E-FAIL-013: an unpunctuated stretch has no boundary)
    for k in ([w0 - 1] if w0 > 0 else []) + [w1]:
        if not sentence_law.is_punctuated(toks, k):
            R("unpunctuated", f"boundary after word {k} lies in an unpunctuated stretch")
            break
    # T6
    import story_semantics
    if story_semantics.injection_markers(text):
        R("injection_markers", "instruction-shaped text")
    # T14 a statement has words enough to be one (today's verbatim-quote floor)
    if len(canon.canon_tokens(text)) < MIN_STATEMENT_TOKENS:
        R("too_short", f"fewer than {MIN_STATEMENT_TOKENS} words: no statement (story_semantics.quote_in)")
    if role not in ON_SCREEN:
        return Result(not reasons, reasons, facts)

    # T7 / T8 the first word heard
    first = (toks[w0].get("word") or "").strip().lstrip("\"'([“‘$")
    if not first or not (first[0].isupper() or first[0].isdigit()):
        R("start_case", f"starts lower-case ({(toks[w0].get('word') or '').strip()!r})")
    targets = facts.setdefault("targets_missed", [])       # law L-o: these rank, never reject
    conj, rest = leading_conjunctions(text)
    if conj:
        targets.append(f"opens on the conjunction{'s' if len(conj) > 1 else ''} {' '.join(conj)!r}")
    if rest:                       # pronoun / reply-word openers are not in L-o: still hard, after any conjunction too
        sc = (ctx.scorer or {}).get(span.key) if role == "clip" else None
        ok, why = stand_alone.opener(role, rest, *(sc if sc else (None, None)))
        if not ok:
            R("opener", why + (f" (after {' '.join(conj)!r})" if conj else ""))
    # T9 sentence count
    n = sum(1 for k in range(span.k0, span.k1 + 1)
            if not interjection_only(spoken(toks[S[k][0]:S[k][1] + 1])))
    facts["n_sentences"] = n
    if n == 0:
        R("no_content", "interjections only")
    elif n > MAX_WINDOW_SENTENCES:                 # ruling 35 (03:12 ET Nov 13): RETIRED as a rule, recorded only. The 20 s
        targets.append(f"{n} sentences > {MAX_WINDOW_SENTENCES} (T9, retired by ruling 35: the 20 s clip limit and "
                       f"the per-source limit govern length)")
    # T10 duration of the span's own words: a target (law L-o); not measured = fail closed (the runtime needs it)
    lo, hi = HOOK_S if role == "hook" else CLIP_S
    a, b = _time(toks[w0], "start"), _time(toks[w1], "end")
    if src.timing == "word" and a is not None and b is not None:
        d = round(b - a, 2)
        facts["duration_s"] = d
        if not lo <= d <= hi:
            targets.append(f"{d} s outside the {role} target {lo}-{hi} s")
    else:
        facts["duration_s"] = None
        R("duration", "no word timestamps: the duration is not measured")
    # T11 subject. Ruling 34: the literal regex is retired. The HOOK must pass the miner's about-Bitcoin screen itself;
    # a clip is judged per line-up (stand_alone.check_edl with the screen: the screen, or it completes the previous
    # claim), and the medley must name Bitcoin once (check_edl's medley_names_bitcoin).
    if role == "hook" and not BTC_SCREEN.search(text):
        R("no_bitcoin", "the hook does not pass the miner's about-Bitcoin screen (ruling 34)")
    # T12 the hook's lead-in
    if role == "hook":
        if w0 == 0:
            if not src.file_head:
                R("hook_lead", "a window's first word: the lead-in before it is not measured")
        else:
            a, b = _time(toks[w0], "start"), _time(toks[w0 - 1], "end")
            gap = None if a is None or b is None else a - b
            facts["lead_s"] = None if gap is None else round(gap, 3)
            if gap is None:
                R("hook_lead", "a word time is missing: the lead-in before the hook is not measured")
            elif gap < HOOK_LEAD_S - 1e-9:
                R("hook_lead", f"{gap * 1000:.0f} ms of transcript gap before the first word < "
                               f"{HOOK_LEAD_S * 1000:.0f} ms (G17a will fail it; GPT-cut F12)")
    # T13 anchored on a story statement, D4 adjacency
    _anchor(span, ctx, reasons, facts)
    return Result(not reasons, reasons, facts)


def leading_conjunctions(text):
    """(the conjunctions a sentence opens on, the text from the first other word): law L-o makes a conjunction opener
    a target, so the opener rules that stay hard (pronoun, reply word) are applied to the first word after them."""
    ws = stand_alone._words(text)
    i = 0
    while i < len(ws) and ws[i] in CONTINUATION_OPENERS:
        i += 1
    return ws[:i], " ".join(ws[i:])


def _stands_alone(span, targets):
    """The hook's first-word rules (T7, T8) for a sentence read on its own (the claim): None if it stands alone. A
    leading conjunction is a target under law L-o (appended to targets), as for a hook or a clip; a pronoun or reply
    word, also after a conjunction, is not."""
    toks = span.source.tokens
    first = (toks[span.w0].get("word") or "").strip().lstrip("\"'([“‘$")
    if not first or not (first[0].isupper() or first[0].isdigit()):
        return f"starts lower-case ({first!r})"
    conj, rest = leading_conjunctions(span.text)
    if conj:
        targets.append(f"the claim opens on the conjunction{'s' if len(conj) > 1 else ''} {' '.join(conj)!r}")
    if not rest:
        return "no word after the conjunction"
    ok, why = stand_alone.opener("hook", rest)
    return None if ok else why + (f" (after {' '.join(conj)!r})" if conj else "")


STATEMENT_NEAR_S = 30.0                    # T13 / F5: editorial_select ANCHOR_PAD_S (:126): a statement is found near
                                           # its own time, never twenty minutes away on five shared words


def statement_entry(span):
    """A story statement as the anchor rule reads it: (video_id, canonical tokens, start, end)."""
    return (span.source.video_id, canon.canon_tokens(span.text), _time(span.source.tokens[span.w0], "start"),
            _time(span.source.tokens[span.w1], "end"))


def near(t0, t1, st):
    """Within STATEMENT_NEAR_S of a statement's own span (st = (start, end)). An unknown time is no measurement: never
    near (law L-m; audit C2), so a sentence is never taken for a statement on an unmeasured position."""
    if None in (t0, t1) or not st or None in st:
        return False
    return t0 <= st[1] + STATEMENT_NEAR_S and t1 >= st[0] - STATEMENT_NEAR_S


def _anchor(span, ctx, reasons, facts):
    R = lambda name, detail: reasons.append(Reason(name, detail))
    statements = [(e[1], tuple(e[2:4]) if len(e) >= 4 else None) for e in (ctx.story or ())
                  if e[0] == span.source.video_id]
    if ctx.story is None:
        R("no_story_statement", "no story statements given: the anchor rule is not measured (fail closed)")
        return
    toks, S = span.source.tokens, span.source.sentences
    stext = lambda k: spoken(toks[S[k][0]:S[k][1] + 1])
    def stated(k):
        t0, t1 = _time(toks[S[k][0]], "start"), _time(toks[S[k][1]], "end")
        return any(states(canon.canon_tokens(stext(k)), st) and near(t0, t1, when) for st, when in statements)
    core = [k for k in range(span.k0, span.k1 + 1) if stated(k)]
    facts["story_sentences"] = core
    if not core:
        R("no_story_statement", "holds no sentence that states the story (editorial_select anchored_window)")
        return
    a, b = min(core), max(core)
    anchor = " ".join(stext(c) for c in core)       # the statements only: an inner sentence never matches itself (C2)
    t_a, t_b = _time(toks[S[a][0]], "start"), _time(toks[S[b][1]], "end")
    for k in range(a + 1, b):                      # between two statements: D4 (a), and (b) from either neighbour
        if k in core or interjection_only(stext(k)):
            continue
        prev_end = _time(toks[S[max(c for c in core if c < k)][1]], "end")
        next_start = _time(toks[S[min(c for c in core if c > k)][0]], "start")
        st = _time(toks[S[k][0]], "start")
        if None in (prev_end, next_start, st):
            R("adjacent_not_admissible", f"inner sentence {k}: a word time is missing (D4 b not measured)")
        elif st - prev_end > ADJ_MAX_START_S and next_start - st > ADJ_MAX_START_S:
            R("adjacent_not_admissible", f"inner sentence {k} starts > {ADJ_MAX_START_S} s from both statements (D4 b)")
        elif not backward_reference(stext(k), anchor, ctx.event):
            R("adjacent_not_admissible", f"inner sentence {k} has no backward reference, shared entity or number (D4 a)")
    admitted = {"prev": 0, "next": 0}
    for d, ks in (("prev", range(a - 1, span.k0 - 1, -1)), ("next", range(b + 1, span.k1 + 1))):
        for k in ks:
            t = stext(k)
            st = _time(toks[S[k][0]], "start")
            gap = None if None in (st, t_a, t_b) else ((st - t_b) if d == "next" else (t_a - st))
            if gap is None:
                R("adjacent_not_admissible", f"{d} sentence {k}: a word time is missing (D4 b not measured)")
            elif gap > ADJ_MAX_START_S:
                R("adjacent_not_admissible", f"{d} sentence {k} starts {gap:.2f} s from the statement (> {ADJ_MAX_START_S} s, D4 b)")
            elif interjection_only(t):
                continue                                      # D4a: transparent, not counted
            elif admitted[d] >= ADJ_MAX_PER_DIRECTION:
                R("adjacent_not_admissible", f"{d} sentence {k}: {ADJ_MAX_PER_DIRECTION} already admitted (D4 cap)")
            elif not backward_reference(t, anchor, ctx.event):
                R("adjacent_not_admissible", f"{d} sentence {k} has no backward reference, shared entity or number (D4 a)")
            else:
                admitted[d] += 1


def _delivered(span, ledger):
    """G6 (story_ledger.delivered_match): the span is the same statement as delivered evidence in the same video."""
    toks = canon.canon_tokens(span.text)
    for e in ledger or ():
        for x in (e.get("evidence") or []) if isinstance(e, dict) else []:
            if isinstance(x, dict) and x.get("video_id") == span.source.video_id and same_statement(
                    toks, canon.canon_tokens(x["quote"]) if x.get("quote") else list(x.get("quote_tokens") or [])):
                return e
    return None


def _lineup(lu, ctx):
    reasons, facts, parts = [], {}, {}
    R = lambda name, detail: reasons.append(Reason(name, detail))
    story = tuple(lu.story or ())
    if not story:
        R("empty_story", "no story statements")
    ok_members, btc_age = [], {}
    for i, sp in enumerate(story):
        r = _span(sp, ctx, "evidence") if isinstance(sp, Span) else \
            Result(False, [Reason("bad_item", "story member is not a Span")], {})
        parts[f"story[{i}]"] = r
        if not r.ok:
            R("story_member", f"story[{i}]: {r.why()}")
            continue
        ok_members.append(sp)
        if names_bitcoin(sp.text):                            # G2 at sentence granularity, in its tier
            a = r.facts["age_h"]
            btc_age[sp.source.channel_id] = min(a, btc_age.get(sp.source.channel_id, a))
    members = [sp for sp in story if isinstance(sp, Span)]
    chans = {sp.source.channel_id for sp in members}
    facts["story_channels"] = sorted(str(c) for c in chans)
    if len(chans) < MIN_COVERAGE_CHANNELS:
        R("story_one_channel", f"{len(chans)} channel(s) < {MIN_COVERAGE_CHANNELS} independent channels")
    facts["bitcoin_channels"] = len(btc_age)
    if len(btc_age) < MIN_COVERAGE_CHANNELS:
        R("story_bitcoin_screen", f"Bitcoin is named by {len(btc_age)} channel(s) < {MIN_COVERAGE_CHANNELS} (DEC-13 c)")
    facts["tier"] = next((f"{h}h" for h in TIER_HOURS if sum(1 for a in btc_age.values() if a <= h)
                          >= MIN_COVERAGE_CHANNELS), None)
    lay = {sp.source.channel_id for sp in ok_members if layout_ok(ctx.channel(sp.source.channel_id))}
    facts["story_layout_channels"] = len(lay)
    if len(lay) < MIN_LAYOUT_CHANNELS:
        R("story_layout_channels", f"{len(lay)} layout-eligible channel(s) state it < {MIN_LAYOUT_CHANNELS}")
    if not any(lu.claim is sp for sp in story):
        R("claim_not_in_story", "the claim is not one of the story's sentences")
    elif not names_bitcoin(lu.claim.text):
        R("claim_no_bitcoin", "the claim sentence does not name Bitcoin")
    else:
        facts["claim"] = lu.claim.text
        why = _stands_alone(lu.claim, facts.setdefault("targets_missed", []))   # read alone downstream (headline)
        if why:
            R("claim_not_standalone", why)
    for sp in members:
        hit = _delivered(sp, ctx.ledger)
        if hit:
            R("already_delivered", f"{sp.source.video_id}: '{sp.text[:60]}' was delivered in {hit.get('run')}")
            break
    if lu.hook is None and not lu.clips:
        return Result(not reasons, reasons, facts, parts)

    on = replace(ctx, story=tuple(statement_entry(sp) for sp in members),
                 event=lu.claim.text if isinstance(lu.claim, Span) and lu.claim._valid() else "")
    segs = ([("hook", lu.hook)] if lu.hook is not None else []) + [(f"clip_{i + 1:02d}", c) for i, c in
                                                                   enumerate(lu.clips or ())]
    if lu.hook is None:
        R("lineup_shape", "no hook")
    if not N_CLIPS[0] <= len(lu.clips or ()) <= N_CLIPS[1]:
        R("lineup_shape", f"{len(lu.clips or ())} clips, need {N_CLIPS[0]}-{N_CLIPS[1]}")
    for label, sp in segs:
        r = _span(sp, on, "hook" if label == "hook" else "clip") if isinstance(sp, Span) else \
            Result(False, [Reason("bad_item", f"{label} is not a Span")], {})
        parts[label] = r
        if not r.ok:
            R("segment", f"{label}: {r.why()}")
    spans = [(label, sp) for label, sp in segs if isinstance(sp, Span)]
    clips = [sp for label, sp in spans if label != "hook"]
    clip_ch = {sp.source.channel_id for sp in clips}
    facts["lineup_channels"] = sorted(str(c) for c in {sp.source.channel_id for _, sp in spans})
    if len(clip_ch) < 2:
        R("lineup_channels", f"clips from {len(clip_ch)} channel(s) < 2 (edl_rules R5)")
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            (la, a), (lb, b) = spans[i], spans[j]
            if a.source.video_id == b.source.video_id and _overlap(a, b):
                R("overlap", f"{la} and {lb} overlap in {a.source.video_id}")
    per_vid = {}
    for _, sp in spans:
        per_vid[sp.source.video_id] = per_vid.get(sp.source.video_id, 0) + 1
    for vid, n in per_vid.items():
        if n > MAX_SPANS_PER_VIDEO:
            R("per_video", f"{n} ranges from {vid} > {MAX_SPANS_PER_VIDEO}")
    durs = [parts[label].facts.get("duration_s") for label, _ in spans if label in parts]
    if spans and all(isinstance(d, (int, float)) for d in durs):
        est = round(sum(durs) + TAIL_S, 2)
        facts["content_s"], facts["runtime_s_estimate"] = round(sum(durs), 2), est
        if not RUNTIME_S[0] <= est <= RUNTIME_S[1]:
            R("runtime", f"estimated runtime {est} s (segments {round(sum(durs), 2)} s + {TAIL_S} s credits / outro / "
                         f"edges) outside {RUNTIME_S[0]:.0f}-{RUNTIME_S[1]:.0f} s (law L-o)")
    elif spans:
        R("runtime", "a segment's duration is not measured: the runtime is not measured")
    per_ch = {}
    for sp in clips:
        per_ch[sp.source.channel_id] = per_ch.get(sp.source.channel_id, 0) + 1
    for ch, n in per_ch.items():
        if n > MAX_CLIPS_PER_CHANNEL:
            R("per_channel", f"{n} clips from channel {ch} > {MAX_CLIPS_PER_CHANNEL}")
    return Result(not reasons, reasons, facts, parts)


def _overlap(a, b):
    """Any shared time in one video (rule L3, stricter than R2's 1.0 s); the same record compares sentence indices."""
    if a.source is b.source:
        return not (a.k1 < b.k0 or b.k1 < a.k0)
    try:
        return not (a.end <= b.start or b.end <= a.start)
    except TypeError:
        return True                                           # unmeasured times: fail closed
