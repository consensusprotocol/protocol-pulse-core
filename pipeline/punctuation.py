#!/usr/bin/env python3
"""pipeline/punctuation.py — sentence punctuation for VERBATIM transcripts (sentence law, 2026-11-11).

Whisper sometimes decodes a whole window without punctuation (Yahoo Finance, Nov 10: 140 lowercase words,
no mark). The sentence law needs to know where sentences end. The verbatim decode's WORDS stay exactly
as they are (selection locks, edge-word timings and G18 need every spoken word; a prompted decode drops
disfluent repetitions such as Yahoo's "of course of course"). Only punctuation is taken from a second
decode of the same audio steered by a neutral punctuated prompt, and only onto words both decodes agree
on (difflib alignment of normalised word keys). Words the decodes disagree on get no punctuation, so no
sentence boundary can come from them (fail closed: the window is rejected, the next-ranked one is tried).

Replaces the per-gap language-model adjudicator, which called 19 of 19 Yahoo gaps sentence ends,
'the | Wolf' and 'of | all' included (E-FAIL-013).
"""
import difflib
import re

import sentence_law as L

PROMPT = "Hello, and welcome. Here is the next part of the conversation."
TRAIL = re.compile(r"[.,!?;:]+$")


def _key(word):
    """A word's alignment key: the pipeline's one canonical form (pipeline/canon.py), spaces removed, with one
    alignment tolerance: a currency / percent word right after a number is dropped (one decode writes '$74,000',
    the other '74,000'; the mark must still transfer). Pure punctuation has no key and never receives a mark."""
    import canon
    t = canon.canon_tokens(word)
    return "".join(w for k, w in enumerate(t) if not (w in ("dollars", "percent") and k and re.fullmatch(r"\d+(\.\d+)?", t[k - 1])))


def needs_restoration(words):
    """True when any word sits in a stretch the sentence law reads as unpunctuated."""
    return any(not L.is_punctuated(words, k) for k in range(len(words)))


def transfer(words, ref):
    """Copy each reference word's trailing punctuation onto the aligned verbatim word (equal blocks
    only; a verbatim word keeps its own punctuation). Returns (new words, marks moved)."""
    a, b = [_key(w["word"]) for w in words], [_key(w["word"]) for w in ref]
    out, moved = [dict(w) for w in words], 0
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for j in range(blk.size):
            w, r = out[blk.a + j], ref[blk.b + j]
            m = TRAIL.search(r["word"].strip())
            if a[blk.a + j] and m and not TRAIL.search(w["word"].strip()):
                w["word"] = w["word"].strip() + m.group(0)
                moved += 1
    return out, moved


VERBATIM = {"beam_size": 5, "vad_filter": False}     # select_passages' verbatim decode (large-v3)


def transfer_case(words, ref):
    """Editorial word pass only (law L-e; audit batch13 U-1): copy a reference word's sentence-initial capital onto
    the aligned verbatim word when BOTH decodes end a sentence right before it (the result's previous word and the
    reference's previous word are terminal, sentence_law.is_terminal) and the reference capitalises it, so
    editorial_select.start_is_boundary reads the same evidence the mark came from. Never the first word (no sentence
    end before it), never lower-cases; only that first letter changes, word keys never do.
    Returns (new words, words recased)."""
    a, b = [_key(w["word"]) for w in words], [_key(w["word"]) for w in ref]
    out, cased = [dict(w) for w in words], 0
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for j in range(blk.size):
            i, k = blk.a + j, blk.b + j
            w, r, v = out[i], ref[k]["word"].strip(), out[i]["word"].strip()
            if (i and k and a[i] and r[:1].isupper() and v[:1].islower() and L.is_terminal(out[i - 1]["word"])
                    and L.is_terminal(ref[k - 1]["word"])):
                w["word"] = w["word"].replace(v, v[0].upper() + v[1:], 1)
                cased += 1
    return out, cased


def reference_decode(source_path, model, settings=None):
    """The punctuation reference: the same ASR settings as the verbatim decode, plus PROMPT. settings = the
    caller's verbatim decode settings (default VERBATIM; the editorial word pass passes its batched ones)."""
    segs, _ = model.transcribe(source_path, language="en", word_timestamps=True, initial_prompt=PROMPT,
                               **(settings or VERBATIM))
    return [{"word": w.word.strip()} for s in segs for w in (s.words or [])]


def ensure(record, source_path, model, model_name="large-v3", settings=None, case=False):
    """The transcript record with sentence punctuation. Verbatim word keys never change. model_name is the
    caller's name for `model` (recorded as provenance); settings as in reference_decode; case=True (the editorial
    word pass) also transfers sentence-initial capitals (transfer_case)."""
    if record.get("punctuation") or not needs_restoration(record["words"]):
        return record
    ref = reference_decode(source_path, model, settings)
    words, moved = transfer(record["words"], ref)
    extra = {}
    if case:
        words, extra["cases_transferred"] = transfer_case(words, ref)
    assert [_key(w["word"]) for w in words] == [_key(w["word"]) for w in record["words"]]
    return dict(record, words=words, punctuation={
        "source": "asr_reference", "model": model_name, "prompt": PROMPT, "marks_transferred": moved, **extra,
        "still_unpunctuated": needs_restoration(words), "reference_text": " ".join(w["word"] for w in ref)})
