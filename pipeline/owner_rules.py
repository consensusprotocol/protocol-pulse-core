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

VERSION = "owner_rules 1 (ruling 162, 2026-11-24)"

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


def out_edge(router, clip_text, before_text, next_sentences, seed=7, role="out_edge", max_tokens=2000,
             no_answer=(Exception,), **call_kw):
    """RULING 162 (1): does the clip's last sentence finish the speaker's thought? router.call(role, prompt,
    max_tokens=, seed=, **call_kw) -> a reply with .text and .backend (the builder's providers.Router, or the render's
    HeimdallText). -> {"complete": True / False / None, "finishes_at": the 0-based index into next_sentences of the
    sentence that finishes the thought, or None, "why", "backend", "measured", "version"}.
    measured False (an exception of the `no_answer` kinds, a reply that is not the JSON asked for): the edge is
    UNVERIFIED (ruling 160 (2a)): never a pass, never a refusal; the caller says which check could not be answered.
    An exception of any other kind propagates (the builder's spend stop, a kill)."""
    after = [str(s).strip() for s in next_sentences or [] if str(s).strip()]
    prompt = OUT_EDGE_PROMPT.format(
        before=" ".join(str(before_text or "").split()) or "(the clip starts the recording)",
        clip=" ".join(str(clip_text or "").split()),
        after="\n".join(f"[{i}] {s}" for i, s in enumerate(after)) or "(none: the recording ends with the clip)")
    try:
        rep = router.call(role, prompt, max_tokens=max_tokens, seed=seed, **call_kw)
    except no_answer as e:
        return _unmeasured(f"no answer: {type(e).__name__}: {str(e)[:300]}")
    backend = getattr(rep, "backend", None)
    obj = _first_json(getattr(rep, "text", "") or "", "complete") or {}
    a = str(obj.get("complete", "")).strip().lower()
    if a not in ("yes", "no"):
        return _unmeasured(f"unreadable reply: {str(getattr(rep, 'text', ''))[:300]!r}", backend)
    fin = obj.get("finishes_at")
    if isinstance(fin, str) and fin.strip().isdigit():
        fin = int(fin.strip())
    elif isinstance(fin, float) and fin.is_integer():           # batch 127 c1 (glm F1): 2.0 is sentence 2
        fin = int(fin)
    if a == "yes" or isinstance(fin, bool) or not isinstance(fin, int) or not 0 <= fin < len(after):
        fin = None
    return {"complete": a == "yes", "finishes_at": fin, "why": " ".join(str(obj.get("why") or "").split())[:300],
            "backend": backend, "measured": True, "version": VERSION}


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


def line_faults(text, names):
    """RULING 162 (2): what makes `text`, one line of ours, a listing: "names '<name>'" for each of `names` (the
    credited channels' display names and aliases) whose canon tokens stand in the line's (canon.canon_tokens: case,
    punctuation and number words folded) in order and side by side, a possessive or plural ending on the last word
    allowed, and "says '<phrase>'" for each LISTING_PHRASES phrase in it. [] when nothing makes it one. A one-word
    channel name that is also a plain word ('Strike', 'Unchained') is matched as that word: such a line is held."""
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
    return faults


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
