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
-> the segment's "speaker": {"name", "role", "line", "basis", "why", "people", "measured", "backend", "replayed"}.
"people" means named in the source's own lines. Code verifies that the name is in the line it cites; the role
(host / guest / other) is the verdict's reading of that line, shown beside it for the reader (audit 0007 C1 K3: qwen,
glm). A call that fails is retried once with a new seed; a second failure stays "unknown" with measured false, which
claims no name (audit 0007 C1 K2).
"""
import json
import os
import re

import eligibility as E

CONTEXT_BEFORE, CONTEXT_AFTER = 8, 2      # sentences of the word record around the clip, for who speaks it
BASIS_MIN_WORDS = 3                       # a basis is a phrase, never one word
MAX_DESCRIPTION_LINES = 60
ROLES = ("host", "guest", "other")
UNKNOWN = "unknown"
STORE = os.path.join(os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse"), "data", "editorial")

PROMPT = """You identify who is SPEAKING in one clip of a Bitcoin video, so the people in it can be credited and tagged.

Tone: factual. Name a person only when the text below shows it. "unknown" is a correct, expected answer, and a wrong
name is worse than "unknown". Never infer from the topic, the style or the title alone.

THE SOURCE'S OWN LINES (its title, its channel and its description, one per line):
{lines}

THE TRANSCRIPT AROUND THE CLIP (the clip is between <clip> and </clip>; speaker turns are not marked):
{context}

Do this:
1. List every person these source lines name who appears in the video (host, guest or other), each with the ONE
   source line that names them, copied character for character.
2. Decide who speaks the words inside <clip>. Name a person only if the TRANSCRIPT shows it, for example:
   - the transcript just before the clip addresses them by name, and the clip answers;
   - the clip speaks of their own work, role or company in the first person, and a source line ties that to them.
   Copy the exact words from the clip or the transcript around it that show it (the basis, at least three words).
   A title or description that names a guest does NOT show who speaks a given clip. If nothing in the transcript
   shows it, the speaker is "unknown", and "why" says what is missing.

Example: an interview whose title names a guest, where the clip and the transcript around it hold no name, no
first-person tie and no address -> "speaker": {{"name": "unknown", "basis": "", "why": "both the host and the guest
speak in this episode, and nothing in or around the clip shows which one this is"}}

Return ONLY this JSON object:
{{"people": [{{"name": "...", "role": "host|guest|other", "line": "..."}}],
 "speaker": {{"name": "<one of the people, or unknown>", "basis": "<exact words from the transcript, or empty>",
 "why": "..."}}}}

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


def attribute(router, seg, src, meta, seed=7):
    """One segment's speaker record. A call that fails, or a reply out of contract, is "unknown" with measured false."""
    import providers as P
    base = {"name": UNKNOWN, "role": None, "line": None, "basis": None, "people": [], "measured": False}
    if src is None or "k0" not in seg or "k1" not in seg:
        return dict(base, why="no word record for the clip's context")
    lines = source_lines(meta or {})
    if not lines:
        return dict(base, why="the source's title, channel and description are not in the store", measured=True)
    before, clip, after = context(src, int(seg["k0"]), int(seg["k1"]))
    prompt = PROMPT.format(lines="\n".join(lines), context=f"{before}\n<clip>{clip}</clip>\n{after}".strip())
    r = None
    try:
        r = router.call("speaker_verdict", prompt, 900, seed)
        rec = check(_json(r.text), lines, clip, f"{before} {after}")
    except Exception as e:                      # any failure claims no name (audit 0007 C1, glm P1-1): Router.call
        if r is not None and not isinstance(e, (P.ProviderError, P.SpendLimit)):    # re-raises a back-end's own
            router.reject(r)                                                         # error
        return dict(base, why=f"not measured: {type(e).__name__}: {str(e)[:160]}")
    return dict(rec, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)))


def attribute_package(router, pk, sources, meta_for=store_meta, log=print):
    """Every segment of a package gets its speaker record, in place (before the pin is sealed)."""
    for i, s in enumerate(pk["segments"]):
        src, meta = sources.get(s["video_id"]), meta_for(s["video_id"])
        sp = attribute(router, s, src, meta)
        if not sp["measured"] and sp["why"].startswith("not measured"):      # once more, a new sample (C1 K2)
            sp = attribute(router, s, src, meta, seed=8)
        s["speaker"] = sp
        log(f"    speaker {i}: {s['video_id']} -> {sp['name']}"
            + (f" ({sp['role']}; basis {sp['basis']!r})" if sp["name"] != UNKNOWN else f" ({sp.get('why')})")
            + f"; the source names {[p['name'] for p in sp['people']]}")
    return pk
