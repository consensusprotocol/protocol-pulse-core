"""Read-only extraction from the editorial transcript store, shared by the corpus builder and the harness's
verbatim check (format v1, docs/audits/parallel/pp-tests_STATE.md).

Tokens and sentence indices `k` are computed exactly as pp-selectid d809a1f8 does it:
select_by_id.tokens_from_record (word records: one token per word; segment records: words with times spread
over the line by character position) and eligibility.split_sentences (a sentence ends after a token that
sentence_law.is_terminal accepts). Sentence text is transcript_store.read_text of the words joined by spaces
(law L-h: the record's own words, never rewritten).

`speaker` / `turn` come from the caption's own markers only: a segment opening '>>' starts a new unnamed turn,
a segment opening 'NAME:' names it. Whisper records carry no markers: speaker None, turn None.

Never writes to the store. The store root is $PP_EDITORIAL_STORE (default: the main tree's, read-only)."""
import hashlib
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import sentence_law  # noqa: E402  (committed main code: the terminal-mark rule T1)

STORE = os.environ.get("PP_EDITORIAL_STORE", "/home/ultron/protocol_pulse/data/editorial")
K_BASIS = ("pp-selectid d809a1f8: select_by_id.tokens_from_record + eligibility.split_sentences "
           "(sentence_law.is_terminal); text = transcript_store.read_text")
_SPLIT_TOKEN = re.compile(r"\s+(?=[.,][0-9A-Za-z])")          # transcript_store._SPLIT_TOKEN
_LABEL = re.compile(r"^([A-Z][A-Za-z .'-]{1,30}):\s")


def read_text(text):
    """transcript_store.read_text (E-FAIL-036 / 037)."""
    return _SPLIT_TOKEN.sub("", html.unescape(text))


def record_path(video_id, method):
    """The store file of `video_id` whose transcript_method equals `method` exactly."""
    d = os.path.join(STORE, "transcripts", video_id)
    for name in sorted(os.listdir(d)):
        if name.startswith("transcript.") and name.endswith(".json"):
            p = os.path.join(d, name)
            with open(p, "rb") as f:
                raw = f.read()
            if json.loads(raw).get("transcript_method") == method:
                return p
    raise FileNotFoundError(f"{video_id}: no record with transcript_method={method!r} under {d}")


def load(video_id, method):
    """(relative record path, sha256 of its bytes, record, meta) for one store record."""
    p = record_path(video_id, method)
    with open(p, "rb") as f:
        raw = f.read()
    meta = {}
    mp = os.path.join(STORE, "transcripts", video_id, "meta.json")
    if os.path.exists(mp):
        with open(mp) as f:
            meta = json.load(f)
    return os.path.relpath(p, STORE), hashlib.sha256(raw).hexdigest(), json.loads(raw), meta


def tokens(rec):
    ws = rec.get("words")
    if ws:
        return "word", [{"word": str(w.get("word") or "").strip(), "start": w.get("start"), "end": w.get("end"),
                         "seg": None} for w in ws if str(w.get("word") or "").strip()]
    out = []                       # segment records: times spread linearly by character position inside the line,
    for si, seg in enumerate(rec.get("segments") or []):     # exactly pp-selectid's approximation (so k matches theirs);
                                                              # 'segment' timing is never enough for an on-screen cut
        text, t0, t1 = str(seg.get("text") or ""), float(seg.get("start") or 0), float(seg.get("end") or 0)
        words, pos = text.split(), 0
        n = max(1, len(text))
        for w in words:
            i = text.index(w, pos)
            pos = i + len(w)
            out.append({"word": w, "start": round(t0 + (t1 - t0) * i / n, 3),
                        "end": round(t0 + (t1 - t0) * pos / n, 3), "seg": si})
    return "segment", out


def split_sentences(toks):
    out, s0 = [], 0
    for i, t in enumerate(toks):
        if sentence_law.is_terminal(t.get("word")):
            out.append((s0, i))
            s0 = i + 1
    if s0 < len(toks):
        out.append((s0, len(toks) - 1))
    return out


def _turns(rec):
    """Per segment: (speaker label or None, turn counter) from the caption's own '>>' / 'NAME:' markers."""
    spk, turn, out = None, 0, []
    for seg in rec.get("segments") or []:
        t = html.unescape(seg.get("text") or "").lstrip()
        if t.startswith(">>"):
            spk, turn = None, turn + 1
            t = t[2:].lstrip()
        m = _LABEL.match(t)
        if m and m.group(1).strip() != spk:
            spk, turn = m.group(1).strip(), turn + 1
        out.append((spk, turn))
    return out


def sentences(rec):
    """(timing, [{'k', 'start', 'end', 'text', 'speaker', 'turn'}]) for a whole record."""
    timing, toks = tokens(rec)
    turns = _turns(rec) if timing == "segment" else None
    out = []
    for k, (a, b) in enumerate(split_sentences(toks)):
        sp, tn = (turns[toks[a]["seg"]] if turns else (None, None))
        out.append({"k": k, "start": toks[a]["start"], "end": toks[b]["end"],
                    "text": read_text(" ".join(t["word"] for t in toks[a:b + 1])), "speaker": sp, "turn": tn})
    return timing, out


def window(sents, k0, k1, before_s, after_s):
    """Whole sentences overlapping [start(k0) - before_s, end(k1) + after_s]."""
    t0, t1 = sents[k0]["start"], sents[k1]["end"]
    return [s for s in sents if s["end"] > t0 - before_s and s["start"] < t1 + after_s]
