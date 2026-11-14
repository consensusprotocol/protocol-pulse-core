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

def norm(text, collapse=False):
    """G18's comparison form: the pipeline's one canonical form (pipeline/canon.py: case, punctuation, split number
    fragments, spelled numbers, decimals, currency / percent, signs), then G18's one tolerance, both sides alike:
    'dollars' right after a number is dropped (whisper writes '$74,000' for a spoken 'seventy-four thousand';
    '5 percent' vs '5 dollars' still differ: GPT-cut F04). collapse=True also folds immediate repeats of 1-3
    words ('of course of course'); a difference that only that removes is NOT dropped from the evidence: G18
    adjudicates it acoustically (GPT-cut F05, gate_g18)."""
    import canon
    t = canon.canon_tokens(text)
    t = [w for k, w in enumerate(t) if not (w == "dollars" and k and re.fullmatch(r"\d+(\.\d+)?", t[k - 1]))]
    return _collapse_repeats(t) if collapse else t


def _collapse_repeats(tokens):
    out = []
    for w in tokens:
        out.append(w)
        for n in (3, 2, 1):
            if len(out) >= 2 * n and out[-n:] == out[-2 * n:-n]:
                del out[-n:]
                break
    return out


def _alt_positions(expected, alts):
    """Ruling 18: {norm index of the expected text: set of attested readings} for each recorded alternative (its
    token_index is a canon index; norm() drops 'dollars' after a number, shifting what follows)."""
    import canon
    t = canon.canon_tokens(expected)
    out = {}
    for x in alts or []:
        a = x.get("token_index")
        if not isinstance(a, int) or not 0 <= a < len(t):
            continue
        drop = [k for k, w in enumerate(t) if w == "dollars" and k and re.fullmatch(r"\d+(\.\d+)?", t[k - 1])]
        if a in drop:
            continue
        out[a - sum(1 for k in drop if k < a)] = set(x.get("readings") or [])
    return out


def diff(expected, heard, collapse=False, alts=None):
    """Word-level differences [(op, expected_words, heard_words)] after canonicalisation; [] if equal. alts (ruling
    18): at an alternative's position, a one-word replacement by another attested reading is not a difference."""
    e, h = norm(expected, collapse), norm(heard, collapse)
    pos = _alt_positions(expected, alts) if not collapse else {}
    out = []
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, e, h, autojunk=False).get_opcodes():
        if op == "replace" and a1 - a0 == 1 and b1 - b0 == 1 and a0 in pos and e[a0] in pos[a0] and h[b0] in pos[a0]:
            continue
        if op != "equal":
            out.append((op, " ".join(e[a0:a1]), " ".join(h[b0:b1])))
    return out


def _omitted_or_repeated_only(expected, heard, alts=None):
    """Ruling 22: True when the heard text differs from the expected ONLY by omitted expected words or by repeats of
    the expected words just before them (nothing substituted, nothing added); attested alternatives (ruling 18)
    count as the expected word."""
    e, h = norm(expected), norm(heard)
    pos = _alt_positions(expected, alts)
    ops = [o for o in difflib.SequenceMatcher(None, e, h, autojunk=False).get_opcodes() if o[0] != "equal"]
    if not ops:
        return False
    for op, a0, a1, b0, b1 in ops:
        if op == "delete":
            continue
        n = b1 - b0
        if op == "insert" and 0 < n and (h[b0:b1] == e[max(0, a0 - n):a0] or h[b0:b1] == e[a0:a0 + n]):
            continue                                     # a repeat of the locked words just before or after it
        if op == "replace" and a1 - a0 == 1 and b1 - b0 == 1 and a0 in pos and e[a0] in pos[a0] and h[b0] in pos[a0]:
            continue                                     # an attested reading, not a substitution
        return False
    return True


def edges(lock_text, heard, n=EDGE_WORDS, alts=None):
    """[] when the heard text starts and ends with the lock's first/last n canonical words (ruling 18: at an
    alternative's position any attested reading counts as the lock's word)."""
    e, h = norm(lock_text), norm(heard)
    for k, rd in _alt_positions(lock_text, alts).items():
        hk = k if k < n else len(h) - (len(e) - k)
        if e[k] in rd and 0 <= hk < len(h) and h[hk] in rd and (k < n or k >= len(e) - n):
            e[k] = h[hk]
    out = []
    if h[:n] != e[:n]:
        out.append(("start", " ".join(e[:n]), " ".join(h[:n])))
    if h[-n:] != e[-n:]:
        out.append(("end", " ".join(e[-n:]), " ".join(h[-n:])))
    return out


class Transcriber:
    def __init__(self):
        import gpu0
        self.model = gpu0.whisper(ASR["model"])      # L-r: loaded through swap_to on first use

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
        # ruling 17: a lock adjudicated by two independent decodes IS the reference the final is compared against;
        # ruling 18: so is a lock that records the attested readings of its one ambiguous token
        alts = [x for x in (c.get("alternatives") or []) if isinstance(x, dict)]
        if len(alts) > 1:                        # ruling 18 records at most ONE ambiguous token (audit batch34 F2)
            rows.append({"segment": label, "pass": False, "error": f"{len(alts)} alternatives in one lock"})
            ok_all = False
            continue
        ref = c["lock_text"] if (c.get("adjudicated") or alts) else src
        row = {"segment": label, "heard": heard, "source_span_heard": src, "lock_text": c["lock_text"],
               "edges": edges(c["lock_text"], heard, alts=alts), "identity": diff(ref, heard, alts=alts),
               "lock_diff_reported": diff(c["lock_text"], heard)}
        if c.get("adjudicated"):
            row["identity_reference"] = "the adjudicated lock text (ruling 17)"
        if alts:
            import sentence_law as L
            row["identity_reference"] = "the lock text with its attested alternatives (ruling 18)"
            row["alternatives"] = []
            for x in alts:
                t0, t1 = (float(v) for v in x["source_span"])
                try:                                # G17c's comparison on the prepared clip (the clip the final mixes)
                    ok_a, det_a = L.span_fidelity(c["source"], c["prepared"], t0, t1, c["cut_in"],
                                                  float(c.get("pad_s") or 0.0))
                except Exception as e:                  # not measurable: the token is not proved
                    ok_a, det_a = False, {"why": f"{type(e).__name__}: {e}"}
                try:                                    # the final bytes (music bed + loudnorm): evidence, not deciding
                    ok_f, det_f = L.span_fidelity(c["source"], final_path, t0, t1, c["cut_in"],
                                                  float(c.get("pad_s") or 0.0), offset_s=float(seg["start"]))
                except Exception as e:
                    ok_f, det_f = False, {"why": f"{type(e).__name__}: {e}"}
                row["alternatives"].append({"readings": x.get("readings"), "acoustic_prepared": {"ok": ok_a, **det_a},
                                            "final_bytes_evidence": {"ok": ok_f, **det_f}})
                if not ok_a:
                    row["acoustic_mismatch"] = True
        if row["identity"] and not diff(ref, heard, collapse=True):
            # only repeats differ (two whisper passes render a disfluent repeat differently, Nov 10 fixture): the
            # difference stays in the row and is decided by the audio: the final's segment must BE the source span
            import sentence_law as L
            try:
                same, det = L.span_matches(c["source"], final_path, c["cut_in"], c["cut_out"], float(seg["start"]),
                                           float(c.get("pad_s") or 0.0))
            except Exception as e:                   # not measurable: the difference stands
                same, det = False, {"why": f"{type(e).__name__}: {e}"}
            row["repeat_only_adjudication"] = {"same_audio": same, **det}
            if same:
                row["identity_repeats_only"], row["identity"] = row["identity"], []
        if row["identity"] and _omitted_or_repeated_only(c["lock_text"], heard, alts) and c.get("prepared"):
            # ruling 22 (orchestrator 2026-11-12 '13:06'): the final's decode is a proxy, the audio is the truth: a
            # difference that only OMITS or REPEATS locked words is decided acoustically: the prepared clip (speech
            # stem) over its interior (between the edge fades) must be the source span, G17c's comparison (-90 dBFS
            # floor, 1 dB). Identical = the omission is recorded and does not fail; not identical = it stands.
            import sentence_law as L
            t0 = float(c["cut_in"]) + float(c.get("fade_in_s") or 0.0)
            t1 = float(c["cut_out"]) - float(c.get("fade_out_s") or 0.0)
            try:
                same, det = L.span_fidelity(c["source"], c["prepared"], t0, t1, float(c["cut_in"]),
                                            float(c.get("pad_s") or 0.0))
            except Exception as e:                   # not measurable: the difference stands
                same, det = False, {"why": f"{type(e).__name__}: {e}"}
            row["omission_adjudication"] = {"same_audio": same, **det}
            if same:
                row["identity_omitted_only"], row["identity"] = row["identity"], []
        row["pass"] = not row["edges"] and not row["identity"] and not row.get("acoustic_mismatch")
        ok_all &= row["pass"]
        rows.append(row)
    return ok_all, rows
