#!/usr/bin/env python3
"""pipeline/word_diff.py — G18 WORD-FOR-WORD (PBX 2026-11-11, mission 4a).

Every clip in the final is transcribed (faster-whisper large-v3, en, beam 5, word timestamps, no VAD, NO
prompt: a prompt would bias the ASR towards the expected words and hide a clipped edge) and must say:
  (a) EDGES: its first and last two words are the first and last two words of its selection lock
      (a clipped start, a lost ending or a run-on into the next sentence fails here: D1-D3);
  (b) IDENTITY: exactly the words of the source span it was cut from [cut_in, cut_out], transcribed
      the same way in isolation (a transition, concat or render that eats, repeats or adds a word fails).
The middle of a clip cannot differ from its lock except by ASR rendering (the cut only places its two
edges), so the full diff against the lock is REPORTED for the human, not gated: two whisper passes over the
same audio render numbers ('$74,000' / '74 000' / 'seventy four thousand dollars') and disfluent repeats
('of course of course' / 'of course') differently (measured on the Nov 10 fixture, 2026-11-11).
Both sides are canonicalised alike: case, punctuation, number fragments ('88 ,000'), spelled numbers,
currency/percent words after a number, immediate repeats of 1-3 words.
"""
import difflib
import os
import re
import subprocess
import tempfile

ASR = {"model": "large-v3", "language": "en", "beam_size": 5, "word_timestamps": True, "vad_filter": False}
EDGE_WORDS = 2

_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
_SCALES = {"hundred": 100, "thousand": 1000}   # whisper writes '74,000' but keeps '1.3 billion' as words
_AFTER_NUMBER = {"dollars", "dollar", "percent", "per", "cent"}


def _spelled_numbers(tokens):
    """'seventy four thousand' -> '74000', 'one hundred and twenty' -> '120'. Only a well-formed phrase is
    joined: a unit after a unit or after a teen ('one two', 'eleven three') starts a new number, so a
    count like 'one two three' stays three tokens (Heimdall: additive joining hid differences)."""
    out, i = [], 0
    while i < len(tokens):
        if tokens[i] in _UNITS or tokens[i] in _TENS:
            total, cur, j, last = 0, 0, i, None
            while j < len(tokens):
                t = tokens[j]
                if t in _UNITS:
                    if last in ("unit",) or (last == "tens" and _UNITS[t] >= 10):
                        break
                    cur += _UNITS[t]
                    last = "unit"
                elif t in _TENS:
                    if last in ("unit", "tens"):
                        break
                    cur += _TENS[t]
                    last = "tens"
                elif t == "hundred" and last in ("unit",):
                    cur *= 100
                    last = "hundred"
                elif t in _SCALES and t != "hundred" and last is not None:
                    total += max(cur, 1) * _SCALES[t]
                    cur, last = 0, "scale"
                elif (t == "and" and last in ("hundred", "scale") and j + 1 < len(tokens)
                      and (tokens[j + 1] in _UNITS or tokens[j + 1] in _TENS)):
                    last = "and"
                else:
                    break
                j += 1
            out.append(str(total + cur))
            i = j
        else:
            out.append(tokens[i])
            i += 1
    return out


_NUM = re.compile(r"\d+(p\d+)?")


def _decimals(tokens):
    """Spoken decimals as the written form's single token: 'one point three' -> '1p3' (like '1.3'), and
    'five and a half' -> '5p5' (like '5.5'; recut run 6 G18: '5 .5%' vs 'five and a half percent', the same
    audio). Only after a number: 'a year and a half' stays words. Before 2026-11-11 a decimal split into
    two digit tokens and the repeat-collapser then merged '5 5' into '5', so 5.5 % and 5 % compared equal."""
    out, k = [], 0
    while k < len(tokens):
        w = tokens[k]
        if w.isdigit() and tokens[k + 1:k + 2] == ["point"] and k + 2 < len(tokens) and tokens[k + 2].isdigit():
            out.append(f"{w}p{tokens[k + 2]}")
            k += 3
        elif w.isdigit() and tokens[k + 1:k + 4] == ["and", "a", "half"]:
            out.append(f"{w}p5")
            k += 4
        else:
            out.append(w)
            k += 1
    return out


def norm(text):
    t = (text or "").lower().replace("’", "'")
    t = re.sub(r"(\d)\s+([.,]\d)", r"\1\2", t)            # '88 ,000' -> '88,000', '1 .3' -> '1.3'
    t = re.sub(r"(\d)\s+(?=\d{3}\b)", r"\1", t)             # '74 000' -> '74000'
    t = re.sub(r"\$\s+(\d)", r"$\1", t)
    t = re.sub(r"\b(\w)\s+\.(?=\w)", r"\1.", t)              # 'u .s.' -> 'u.s.'
    t = re.sub(r"\b([a-z])\.(?=[a-z]\b)", r"\1", t)            # 'u.s.' -> 'us.' (single-letter abbreviations)
    t = re.sub(r"(?<=\d)[,](?=\d{3}\b)", "", t)             # '74,000' -> '74000'
    t = re.sub(r"(?<=\d)\.(?=\d)", "p", t)                   # '5.5' -> '5p5': a decimal stays ONE token
    t = re.sub(r"[^\w\s']", " ", t)                         # punctuation, '$', '%' (both sides alike)
    t = re.sub(r"(?<!\w)'|'(?!\w)", "", t)                  # quote marks, not apostrophes
    tokens = _decimals(_spelled_numbers(t.split()))          # 'one point three' / 'five and a half' -> '1p3' / '5p5'
    tokens = [w for k, w in enumerate(tokens) if not (w in _AFTER_NUMBER and k and (
        _NUM.fullmatch(tokens[k - 1]) or tokens[k - 1] in ("million", "billion", "trillion")))]
    return _collapse_repeats(tokens)


def _collapse_repeats(tokens):
    out = []
    for w in tokens:
        out.append(w)
        for n in (3, 2, 1):
            if len(out) >= 2 * n and out[-n:] == out[-2 * n:-n]:
                del out[-n:]
                break
    return out


def diff(expected, heard):
    """Word-level differences [(op, expected_words, heard_words)] after canonicalisation; [] if equal."""
    e, h = norm(expected), norm(heard)
    out = []
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, e, h, autojunk=False).get_opcodes():
        if op != "equal":
            out.append((op, " ".join(e[a0:a1]), " ".join(h[b0:b1])))
    return out


def edges(lock_text, heard, n=EDGE_WORDS):
    """[] when the heard text starts and ends with the lock's first/last n canonical words."""
    e, h = norm(lock_text), norm(heard)
    out = []
    if h[:n] != e[:n]:
        out.append(("start", " ".join(e[:n]), " ".join(h[:n])))
    if h[-n:] != e[-n:]:
        out.append(("end", " ".join(e[-n:]), " ".join(h[-n:])))
    return out


class Transcriber:
    def __init__(self):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(ASR["model"], device="cuda", compute_type="float16")

    def span(self, media, t0, t1):
        if t1 - t0 < 0.05:
            return ""
        with tempfile.TemporaryDirectory(prefix="g18_") as tmp:
            wav = os.path.join(tmp, "span.wav")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", media,
                            "-vn", "-ac", "1", "-ar", "16000", wav], check=True, timeout=120)
            segs, _ = self.model.transcribe(wav, language=ASR["language"], beam_size=ASR["beam_size"],
                                            word_timestamps=ASR["word_timestamps"], vad_filter=ASR["vad_filter"])
            return " ".join(w.word.strip() for s in segs for w in (s.words or []))


def gate_g18(final_path, segments, clips, transcriber=None):
    """segments: the final's manifest entries. clips: {label: {"lock_text", "source", "cut_in", "cut_out"}}.
    Returns (ok, rows); each row carries the gated edge + identity diffs and the reported lock diff."""
    tr = transcriber or Transcriber()
    by_label = {s["label"]: s for s in segments}
    rows, ok_all = [], True
    for s in segments:                       # every talking head in the final must be a checked clip
        if s.get("type") == "talking_head" and s["label"] not in clips:
            rows.append({"segment": s["label"], "pass": False, "error": "talking head without a selection lock"})
            ok_all = False
    for label, c in clips.items():
        seg = by_label.get(label)
        if seg is None:
            rows.append({"segment": label, "pass": False, "error": "segment missing from the manifest"})
            ok_all = False
            continue
        heard = tr.span(final_path, seg["start"], seg["end"])
        src = tr.span(c["source"], c["cut_in"], c["cut_out"])
        row = {"segment": label, "heard": heard, "source_span_heard": src, "lock_text": c["lock_text"],
               "edges": edges(c["lock_text"], heard), "identity": diff(src, heard),
               "lock_diff_reported": diff(c["lock_text"], heard)}
        row["pass"] = not row["edges"] and not row["identity"]
        ok_all &= row["pass"]
        rows.append(row)
    return ok_all, rows
