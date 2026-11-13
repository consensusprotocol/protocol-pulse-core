#!/usr/bin/env python3
"""pipeline/speakers.py: ORCHESTRATOR 00:05 ET Nov 13, item 3. Every pin segment names its SPEAKER where the source
names the person, with the evidence: PBX tags the right people, and law L-v 1 needs it. An unknown speaker is
"unknown", never a guess.

Evidence is text, and code checks it:
- source_lines(meta): the source's own lines, from the store's meta.json (yt-dlp, at acquisition): "title: ...",
  "channel: ...", then each description line that is not a bare link.
- context(src, k0, k1): the clip's own words in the word record, with CONTEXT_BEFORE sentences before it and
  CONTEXT_AFTER after it.
- One verdict (role speaker_verdict) proposes, as JSON, two things: the people the source's lines name, each with the
  line that names them; and who speaks THIS clip, with a basis quoted from the transcript.
- check() keeps only what the text shows:
  - a person stands only if their line is part of one of the source's lines and holds their name; the person
    carries that WHOLE source line as evidence;
  - the speaker is named only if they are one of those people AND the basis (>= BASIS_MIN_WORDS words) is verbatim in
    the clip or the transcript around it.
  A source line alone never names a clip's speaker: a title that names a guest does not show who speaks a given
  clip. Otherwise the speaker is "unknown", with why, and every person the source names is still listed (people) for
  tagging.
RULING 69 (orchestrator 15:29 Nov 13): "the attribution step reads the caption turn markers and addresses by name
across the whole turn that contains the clip, not only the windows around it; a speaker is named when the turn
structure plus one address or self-introduction shows it." captions() reads the episode's caption record with its
speaker-change markers ('>>'); turn_of() finds, in code, the ONE turn that holds the clip (no marker inside it), across
another person's interjections of at most BACKCHANNEL_WORDS words (A, a one-word "Yeah." by B, A again: one turn of A).
The verdict quotes any address by name and any self-introduction inside that turn; check_turn() keeps one only when its
quote is verbatim in the turn and holds a name of one of the people. A self-introduction names its speaker; an address
names the OTHER person only when the source's lines name exactly two people. A lower third (ruling 70) is one more
piece of evidence, never alone: it names nobody by itself, and one that contradicts the decision makes it "unknown".
-> the segment's "speaker": {"name", "role", "line", "basis", "why", "people", "measured", "backend", "replayed",
"turn" (ruling 69's evidence, when a caption turn was read)}.
"people" means named in the source's own lines. Code verifies that the name is in the line it cites; the role
(host / guest / other) is the verdict's reading of that line, shown beside it for the reader (audit 0007 C1 K3: qwen,
glm). A call that fails is retried once with a new seed; a second failure stays "unknown" with measured false, which
claims no name (audit 0007 C1 K2).
"""
import hashlib
import html
import json
import os
import re

import context_integrity as CI
import eligibility as E

CONTEXT_BEFORE, CONTEXT_AFTER = 8, 2      # sentences of the word record around the clip, for who speaks it
BASIS_MIN_WORDS = 3                       # a basis is a phrase, never one word
MAX_DESCRIPTION_LINES = 60
ROLES = ("host", "guest", "other")
UNKNOWN = "unknown"
STORE = os.path.join(os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse"), "data", "editorial")
INGEST_STORE = os.path.join(os.environ.get("PP_INGEST", "/home/ultron/worktrees/pp-ingest"), "data", "editorial")
BACKCHANNEL_WORDS = 3                     # ruling 69: another person's interjection this short does not end a turn,
BACKCHANNEL = frozenset("""yeah yes yep yup right okay ok sure mm mhm hmm uh-huh mm-hmm exactly absolutely totally
wow true indeed correct no nope oh ah huh""".split())    # when every word of it is one of these (audit 1545 C1)
TURN_MAX_CHARS = 12000                    # the turn shown to the verdict (a longer one is cut around the clip)
MARKER_TOL_S = 0.5                        # caption lines carry their display time: a marker this near an edge is it
NAME_WORD_MIN = 2                         # a word of a person's name, for the turn quotes AND the lower third (audit
                                          # 1545 C2: one rule; an initial such as "W." never counts)

PROMPT = """You identify who is SPEAKING in one clip of a Bitcoin video, so the people in it can be credited and tagged.

Tone: factual. Name a person only when the text below shows it. "unknown" is a correct, expected answer, and a wrong
name is worse than "unknown". Never infer from the topic, the style or the title alone.

THE SOURCE'S OWN LINES (its title, its channel and its description, one per line):
{lines}

THE TRANSCRIPT AROUND THE CLIP (the clip is between <clip> and </clip>; speaker turns are not marked):
{context}

THE CLIP'S TURN (from the episode's own captions, whose markers show where the speaker changes; the clip lies inside
this one turn of ONE speaker, other people's interjections of at most three words left out):
{turn}

Do this:
1. List every person these source lines name who appears in the video (host, guest or other), each with the ONE
   source line that names them, copied character for character.
2. Decide who speaks the words inside <clip>. Name a person only if the TRANSCRIPT shows it, for example:
   - the transcript just before the clip addresses them by name, and the clip answers;
   - the clip speaks of their own work, role or company in the first person, and a source line ties that to them.
   Copy the exact words from the clip or the transcript around it that show it (the basis, at least three words).
   A title or description that names a guest does NOT show who speaks a given clip. If nothing in the transcript
   shows it, the speaker is "unknown", and "why" says what is missing.
3. In THE CLIP'S TURN only (when one is given), find: (a) an ADDRESS BY NAME, where the speaker of the turn speaks TO one
   of the people by name ("..., Scott?", "Mark, what do you think"), not merely about them; (b) a SELF-INTRODUCTION,
   where the speaker of the turn names themself ("I'm Mark Yusko", "this is Natalie"). For each, copy at least three
   exact words from the turn holding the name, and give the person as listed in step 1. None found: null.

Example: an interview whose title names a guest, where the clip and the transcript around it hold no name, no
first-person tie and no address -> "speaker": {{"name": "unknown", "basis": "", "why": "both the host and the guest
speak in this episode, and nothing in or around the clip shows which one this is"}}

Return ONLY this JSON object:
{{"people": [{{"name": "...", "role": "host|guest|other", "line": "..."}}],
 "speaker": {{"name": "<one of the people, or unknown>", "basis": "<exact words from the transcript, or empty>",
 "why": "..."}},
 "turn": {{"address": {{"name": "<the person addressed>", "quote": "<exact words>"}} or null,
          "self_intro": {{"name": "<the person>", "quote": "<exact words>"}} or null}}}}

Remember: copy every line and the basis exactly; "unknown" whenever the transcript does not show who speaks."""


def _norm(s):
    """Case, punctuation and spacing aside: the text a quote must match."""
    return " ".join(re.sub(r"[^\w']+", " ", str(s or "").casefold()).split())


def _within(needle, hay):
    """Whole words in order: the normalised needle, word for word, inside the normalised hay; never from the middle of
    a word ("i wrote" is not inside "hi wrote"; audit 0007 C2, grok P2-2)."""
    n, h = _norm(needle), _norm(hay)
    return bool(n) and f" {n} " in f" {h} "


def store_meta(video_id, store=STORE):
    """The store's meta.json for a video (title, channel, description), or {} when it is not there."""
    try:
        with open(os.path.join(store, "transcripts", video_id, "meta.json")) as f:
            meta = json.load(f)
        return meta if isinstance(meta, dict) else {}
    except (OSError, ValueError):
        return {}


def source_lines(meta):
    out = []
    if isinstance(meta.get("exact_title"), str) and meta["exact_title"].strip():
        out.append(f"title: {meta['exact_title'].strip()}")
    if isinstance(meta.get("channel_name"), str) and meta["channel_name"].strip():
        out.append(f"channel: {meta['channel_name'].strip()}")
    desc = meta.get("description") if isinstance(meta.get("description"), str) else ""
    for line in desc.split("\n"):
        line = line.strip()
        if line and not re.fullmatch(r"\S*https?://\S*", line) and len(out) < MAX_DESCRIPTION_LINES + 2:
            out.append(line)
    return out


def context(src, k0, k1, before=CONTEXT_BEFORE, after=CONTEXT_AFTER):
    """(the sentences before, the clip, the sentences after) in the word record's own words."""
    sents = src.sentences
    a, b = max(0, k0 - before), min(len(sents) - 1, k1 + after)

    def say(i, j):
        return E.spoken(src.tokens[sents[i][0]:sents[j][1] + 1]) if i <= j else ""
    return say(a, k0 - 1), say(k0, k1), say(k1 + 1, b)


def captions(video_id, stores=None):
    """RULING 69: the episode's caption record WITH speaker-change markers ('>>'): transcript.yt_auto.json from the
    first store whose copy carries any (the main tree's, then pp-ingest's: a live episode's captions arrive later).
    -> ([(t, text, opens_turn)] in caption order, {"file", "sha256"}), or (None, None). Rolling repeats of a line are
    read once; a '>>' inside a line opens a turn there."""
    for st in stores or (STORE, INGEST_STORE):
        p = os.path.join(st, "transcripts", video_id, "transcript.yt_auto.json")
        try:
            with open(p, "rb") as f:
                raw = f.read()
            segs = json.loads(raw).get("segments") or []
        except (OSError, ValueError, AttributeError):
            continue
        units, last, pending = [], None, False
        try:                                          # audit 1545 C1: a malformed record is skipped, never a crash
            for s in segs:
                t = html.unescape(str(s.get("text") or "")).strip()
                if not t or t == last:
                    continue
                last, t0 = t, float(s["start"])
                if t0 != t0 or (units and t0 < units[-1][0]):      # NaN, or out of order: not a record to read
                    raise ValueError("caption times are not in order")
                for k, part in enumerate(t.split(">>")):
                    opens, part = (k > 0) or pending, part.strip()
                    pending = opens and not part              # a bare '>>': the next words open the turn
                    if part:
                        units.append((t0, part, opens))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if any(u[2] for u in units):
            return units, {"file": p, "sha256": hashlib.sha256(raw).hexdigest()}
    return None, None


def turn_of(units, start, end, bc=BACKCHANNEL_WORDS, tol=MARKER_TOL_S):
    """RULING 69: the ONE turn of one speaker that holds the clip [start, end], from the caption markers -> ({"text",
    "start", "end", "backchannels": [the interjections skipped]}, None) or (None, why). The turn runs from the last
    marker at or before the clip to the next marker after it; across a stretch of at most `bc` words between two
    markers (another person's interjection) it goes on, both ways: the speaker before and after it is the same."""
    if not units:
        return None, "no caption record with speaker-change markers"
    opens = [i for i, u in enumerate(units) if u[2]]
    if any(start + tol < units[i][0] < end - tol for i in opens):
        return None, "a speaker-change marker falls inside the clip"
    before = [i for i in opens if units[i][0] <= start + tol]
    if not before:
        return None, "no speaker-change marker before the clip"
    nxt = lambda i: min([j for j in opens if j > i], default=len(units))
    prv = lambda i: max([j for j in opens if j < i], default=None)
    words = lambda i, j: sum(len(units[k][1].split()) for k in range(i, j))

    def backchannel(i, j):                               # audit 1545 C1: short AND only backchannel words
        ws = [re.sub(r"[^\w'-]", "", w.casefold()) for k in range(i, j) for w in units[k][1].split()]
        return 0 < len(ws) <= bc and all(w in BACKCHANNEL for w in ws if w)
    a = before[-1]
    b = nxt(a)
    spans, skipped = [(a, b)], []
    while b < len(units) and nxt(b) < len(units) and backchannel(b, nxt(b)):   # A | b: B's interjection | A again
        skipped.append(" ".join(units[k][1] for k in range(b, nxt(b))))
        spans.append((nxt(b), nxt(nxt(b))))
        b = nxt(nxt(b))
    while prv(a) is not None and prv(prv(a)) is not None and backchannel(prv(a), a):   # A again | B's | the turn
        p = prv(a)
        skipped.insert(0, " ".join(units[k][1] for k in range(p, a)))
        spans.insert(0, (prv(p), p))
        a = prv(p)
    idx = [k for x, y in spans for k in range(x, y)]
    text = " ".join(units[k][1] for k in idx)
    if len(text) > TURN_MAX_CHARS:                       # cut around the clip, never losing it
        mid = next((n for n, k in enumerate(idx) if units[k][0] >= start - tol), 0)
        lo = len(" ".join(units[k][1] for k in idx[:mid]))
        a0 = max(0, min(lo - TURN_MAX_CHARS // 2, len(text) - TURN_MAX_CHARS))
        a1 = a0 + TURN_MAX_CHARS
        if a0 > 0:                                       # audit 1545 C1: on word boundaries only
            a0 = text.find(" ", a0) + 1 or a0
        if a1 < len(text):
            a1 = text.rfind(" ", a0, a1) if text.rfind(" ", a0, a1) > a0 else a1
        text = text[a0:a1].strip()
    return {"text": text, "start": units[idx[0]][0], "end": units[idx[-1]][0], "backchannels": skipped}, None


def check_turn(t, people, turn_text):
    """RULING 69: the verdict's turn evidence, kept only where code sees it -> {"address", "self_intro"} (each a
    {"name", "quote"} or None). A quote stands when it is >= BASIS_MIN_WORDS words, verbatim in the turn, and holds a
    word of the person's name; the person must be one of the people."""
    out = {"address": None, "self_intro": None}
    if not isinstance(t, dict) or not turn_text:
        return out
    for k in out:
        x = t.get(k)
        if not isinstance(x, dict) or not isinstance(x.get("name"), str) or not isinstance(x.get("quote"), str):
            continue
        who = next((p for p in people if _norm(p["name"]) == _norm(x["name"])), None)
        q = x["quote"]
        if who is not None and len(_norm(q).split()) >= BASIS_MIN_WORDS and _within(q, turn_text) and \
                any(_within(w, q) for w in _norm(who["name"]).split() if len(w) >= NAME_WORD_MIN):
            out[k] = {"name": who["name"], "quote": q.strip()}
    return out


def decide(rec, turn_ev, people, lower_third=None):
    """RULING 69: the speaker from the turn evidence, beside the basis rule's (check) -> the record. A self-introduction
    names its speaker; an address names the other person only when the source's lines name exactly two. Two rules that
    name different people, or a lower third that contradicts the decision, are "unknown". A lower third alone names
    nobody (ruling 70: one more piece of evidence, never alone)."""
    by = None
    if turn_ev.get("self_intro"):
        by = (turn_ev["self_intro"]["name"], f"self-introduction in the clip's turn: {turn_ev['self_intro']['quote']}")
    elif turn_ev.get("address"):
        others = [p for p in people if _norm(p["name"]) != _norm(turn_ev["address"]["name"])]
        if len(people) == 2 and len(others) == 1:
            by = (others[0]["name"], f"addresses {turn_ev['address']['name']} in the clip's turn: "
                                     f"{turn_ev['address']['quote']}")
    out = dict(rec)
    if by is not None:
        p = next(p for p in people if _norm(p["name"]) == _norm(by[0]))
        if rec["name"] != UNKNOWN and _norm(rec["name"]) != _norm(p["name"]):
            return dict(rec, name=UNKNOWN, role=None, line=None, basis=None,
                        why=f"the clip's turn shows {p['name']!r} but the transcript basis shows {rec['name']!r}")
        out.update(name=p["name"], role=p["role"], line=p["line"], basis=by[1])
    lt = lower_third if isinstance(lower_third, str) and _norm(lower_third) else None
    if lt is not None:
        hit = next((p for p in people if any(_within(w, lt) for w in _norm(p["name"]).split()
                                             if len(w) >= NAME_WORD_MIN)), None)
        if out["name"] != UNKNOWN and hit is not None and _norm(hit["name"]) != _norm(out["name"]):
            return dict(out, name=UNKNOWN, role=None, line=None, basis=None,
                        why=f"the lower third {lt!r} contradicts {out['name']!r}")
        if out["name"] != UNKNOWN and hit is not None:
            out["basis"] = f"{out['basis']}; the lower third reads {lt!r}"
    return out


def _json(text):
    """The reply's JSON object: its outermost {...}, whatever fence or prose surrounds it (audit 0007 C1 glm P1-2,
    C2 grok P2-1)."""
    t = str(text or "")
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < a:
        raise ValueError("no JSON object in the reply")
    return json.loads(t[a:b + 1])


def check(v, lines, clip, around):
    """The verdict, kept only where the text shows it (never the model's word) -> the speaker record (no backend)."""
    if not isinstance(v, dict) or not isinstance(v.get("people"), list) or not isinstance(v.get("speaker"), dict):
        raise ValueError("speaker verdict out of contract")
    people = []
    for p in v["people"]:
        if not isinstance(p, dict) or not isinstance(p.get("name"), str) or not isinstance(p.get("line"), str):
            continue
        nn = _norm(p["name"])
        whole = next((x for x in lines if _within(p["line"], x)), None)
        if not nn or whole is None or not _within(p["name"], whole) or any(_norm(q["name"]) == nn for q in people):
            continue                             # not a source line, or the line does not name them
        people.append({"name": p["name"].strip(), "role": p.get("role") if p.get("role") in ROLES else "other",
                       "line": whole})
    sp = v["speaker"]
    name, basis = sp.get("name"), sp.get("basis")
    rec = {"name": UNKNOWN, "role": None, "line": None, "basis": None,
           "why": str(sp.get("why") or "")[:300], "people": people}
    if isinstance(name, str) and _norm(name) not in ("", UNKNOWN):
        match = next((p for p in people if _norm(p["name"]) == _norm(name)), None)
        nb = _norm(basis)
        if match is None:
            rec["why"] = f"{name.strip()!r} is not a person the source's lines name"
        elif len(nb.split()) < BASIS_MIN_WORDS or not (_within(basis, clip) or _within(basis, around)):
            rec["why"] = (f"the basis for {name.strip()!r} is not {BASIS_MIN_WORDS}+ words found in the clip or the "
                          f"transcript around it")
        else:
            rec.update(name=match["name"], role=match["role"], line=match["line"], basis=str(basis).strip())
    return rec


def attribute(router, seg, src, meta, seed=7, caps=None, lower_third=None):
    """One segment's speaker record. A call that fails, or a reply out of contract, is "unknown" with measured false.
    caps: captions(video id) (ruling 69: the turn markers), read by the caller."""
    import providers as P
    base = {"name": UNKNOWN, "role": None, "line": None, "basis": None, "people": [], "measured": False}
    if src is None or "k0" not in seg or "k1" not in seg:
        return dict(base, why="no word record for the clip's context")
    lines = source_lines(meta or {})
    if not lines:
        return dict(base, why="the source's title, channel and description are not in the store", measured=True)
    before, clip, after = context(src, int(seg["k0"]), int(seg["k1"]))
    units, cap_src = caps if caps else (None, None)
    try:                                                 # audit 1545 C1: a turn that cannot be read is no turn
        turn, turn_why = turn_of(units, float(seg["start"]), float(seg["end"])) if units else \
            (None, "no caption record with speaker-change markers")
    except (KeyError, TypeError, ValueError, IndexError) as e:
        turn, turn_why = None, f"the caption turn could not be read: {type(e).__name__}: {str(e)[:120]}"
    prompt = PROMPT.format(lines="\n".join(lines), context=f"{before}\n<clip>{clip}</clip>\n{after}".strip(),
                           turn=turn["text"] if turn else f"(none: {turn_why})")
    r = None
    try:
        r = router.call("speaker_verdict", prompt, 900, seed)
        v = _json(r.text)
        rec = check(v, lines, clip, f"{before} {after}")
        ev = check_turn(v.get("turn"), rec["people"], turn["text"] if turn else "")
        rec = decide(rec, ev, rec["people"], lower_third)
        rec["turn"] = {"read": turn is not None, "why": turn_why, **({"source": cap_src, "start": turn["start"],
                                                                      "end": turn["end"],
                                                                      "backchannels": turn["backchannels"]}
                                                                     if turn else {}), **ev}
    except Exception as e:                      # any failure claims no name (audit 0007 C1, glm P1-1): Router.call
        if r is not None and not isinstance(e, (P.ProviderError, P.SpendLimit)):    # re-raises a back-end's own
            router.reject(r)                                                         # error
        return dict(base, why=f"not measured: {type(e).__name__}: {str(e)[:160]}")
    return dict(rec, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)))


def attribute_package(router, pk, sources, meta_for=store_meta, log=print, captions_for=captions):
    """Every segment of a package gets its speaker record, in place (before the pin is sealed)."""
    for i, s in enumerate(pk["segments"]):
        try:
            src = CI.source_for(s, sources)                   # the one lookup rule (audit 0208 C1: glm, qwen)
        except KeyError:
            src = None                                        # -> "unknown", not measured: never a name
        meta = meta_for(s["video_id"])
        try:
            caps = captions_for(s["video_id"])                # ruling 69: the caption turn markers
        except Exception:                                     # noqa: BLE001  audit 1545 C1: never the package
            caps = None
        lt = ((s.get("visual") or {}).get("lower_third") or {}).get("name")   # ruling 70: one more piece, never alone
        sp = attribute(router, s, src, meta, caps=caps, lower_third=lt)
        if not sp["measured"] and sp["why"].startswith("not measured"):      # once more, a new sample (C1 K2)
            sp = attribute(router, s, src, meta, seed=8, caps=caps, lower_third=lt)
        s["speaker"] = sp
        log(f"    speaker {i}: {s['video_id']} -> {sp['name']}"
            + (f" ({sp['role']}; basis {sp['basis']!r})" if sp["name"] != UNKNOWN else f" ({sp.get('why')})")
            + f"; the source names {[p['name'] for p in sp['people']]}")
    return pk
