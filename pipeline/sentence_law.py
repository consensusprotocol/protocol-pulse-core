#!/usr/bin/env python3
"""pipeline/sentence_law.py — PBX SENTENCE-BOUNDARY LAW (Nov 5 2026; hardened Nov 11 2026, D1-D3).

A clip starts on the first word of a sentence and ends on the last word of a sentence, and both
cut points sit in the silence between that sentence and its neighbour. The words a clip must
contain are fixed at SELECTION time (the "selection lock") and are never recomputed from a moved
cut (the D2 tautology of ad7295ea/4cf5a31a).

BOUNDARY RULE (law constants, stated once, used by selection, cutting and gate G16):
  A sentence boundary exists between transcript word k and word k+1 iff BOTH
  (L) LEXICAL   punctuated transcript: word k ends in '.', '!' or '?' and is not an abbreviation
                (U.S., Mr., a.m., ...) or a trailing '...';
                a transcript stretch with fewer than 1 terminal mark per 60 words (within +-60 words) is
                UNPUNCTUATED: no gap in it is a sentence boundary (fail closed). Transcripts get their
                punctuation at transcription time (pipeline/punctuation.py: marks from a second,
                prompted decode of the same audio, onto aligned verbatim words only). The per-gap
                local-model adjudicator was removed 2026-11-11: it called 19 of 19 Yahoo Finance gaps
                sentence ends, 'the | Wolf' included (E-FAIL-013).
  (A) ACOUSTIC  the source audio holds a PAUSE between them: a run of >= PAUSE_MIN_S (80 ms, Law
                14c) of 10 ms RMS frames below the QUIET LINE, inside [start(k), end(k+1)] (whisper
                word edges are estimates and collapse at sentence boundaries, Law 14/14c, so the
                search spans both words; the longest run wins).
                QUIET LINE = min(speech - 12 dB (M19a), max(speech - 25 dB (cut_accept), bed + 6 dB
                (M19/G3c))); speech = median of frames above the 30th percentile, bed = 10th
                percentile (noise-floor estimate) of non-digital-silence frames, both over
                [start(k) - 3 s, end(k+1) + 3 s]. Every cut must ALSO pass cut_accept unchanged.
CUTTABLE EDGES (G17 + M19):
  IN   cut_in inside the pause before the first word with >= LEAD_MIN_S (80 ms) of it kept.
       File head (first transcript word): the lead-in is the GENUINE quiet audio before the first
       onset; frames below DIGITAL_FLOOR_DBFS (-100 dBFS: encoder priming, file-head padding) are
       not room tone. If it is < 80 ms the render must add a LEAD_PAD_S room-tone pad (D1).
  OUT  cut_out inside the pause after the last word with >= TAIL_MIN_S (80 ms) of it kept and
       >= GUARD_S (60 ms, M19) before the next onset -> the pause must be >= 140 ms.
"""
import hashlib
import json
import os
import re
import subprocess
from difflib import SequenceMatcher

import numpy as np

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)

HOP_S = 0.010
SR = 16000
PAUSE_MIN_S = 0.080
LEAD_MIN_S = 0.080
TAIL_MIN_S = 0.080
GUARD_S = 0.060
LEAD_TARGET_S = 0.250       # preferred lead-in kept before the first onset (Law 14: breath kept)
TAIL_TARGET_S = 0.300       # M19: cut_out = min(offset + 0.30, onset - 0.06)
LEAD_PAD_S = 0.250          # D1 room-tone pad (6 frames at 24 fps)
QUIET_BELOW_SPEECH_DB = 25.0
VALLEY_BELOW_SPEECH_DB = 12.0
BED_PLUS_DB = 6.0
DIGITAL_FLOOR_DBFS = -100.0
LEVEL_WINDOW_S = 3.0
ONSET_SUSTAIN_S = 0.030
EDGE_EPS_S = 0.011          # one 10 ms hop of measurement slack
ANCHOR_MIN_RATIO = 0.80
PUNCT_WINDOW_WORDS = 60
WORD_DURATION_RATIO_MIN = 0.85  # G17: rendered edge word keeps >= 85 % of its duration
_TERMINAL = (".", "!", "?")
_ABBREV = {"mr", "mrs", "ms", "dr", "st", "vs", "etc", "jr", "sr", "inc", "ltd", "corp", "prof", "approx"}


class LawError(Exception):
    """A clip cannot be made sentence-complete (window must be rejected)."""


# ── text ──

def tokens(text):
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower().replace("’", "'").replace("'", "")) if t]


def is_terminal(word):
    w = (word or "").strip().rstrip("\"')]”’")
    if not w.endswith(_TERMINAL) or w.endswith(".."):
        return False
    if re.fullmatch(r"\.(?:[A-Za-z]\.)+|(?:[A-Za-z]\.){2,}", w):
        return False                      # U.S. / .S. / a.m. / e.g.
    if w.endswith(".") and w[:-1].lower() in _ABBREV:
        return False
    return True


def is_punctuated(words, k):
    lo, hi = max(0, k - PUNCT_WINDOW_WORDS), min(len(words), k + PUNCT_WINDOW_WORDS + 1)
    win = words[lo:hi]
    marks = sum(1 for w in win if is_terminal(w["word"]))
    return marks * PUNCT_WINDOW_WORDS >= len(win)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ── audio ──

class SourceAudio:
    """10 ms RMS envelope (dBFS) of a whole media file, mono 16 kHz, decoded once."""

    def __init__(self, path):
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
                            "-f", "f32le", "-"], capture_output=True, check=True, timeout=300)
        x = np.frombuffer(r.stdout, np.float32)
        h = int(SR * HOP_S)
        n = len(x) // h
        if n == 0:
            raise RuntimeError(f"no audio decoded from {path}")
        self.path = path
        self.dur = len(x) / SR
        self.t = np.arange(n) * HOP_S
        self.db = 20 * np.log10(np.sqrt(np.mean(x[:n * h].reshape(n, h).astype(np.float64) ** 2, axis=1)) + 1e-9)

    def sl(self, t0, t1):
        m = (self.t >= t0 - 1e-9) & (self.t < t1 - 1e-9)
        return self.t[m], self.db[m]

    def levels(self, t0, t1):
        _, d = self.sl(max(0.0, t0), min(self.dur, t1))
        live = d[d > DIGITAL_FLOOR_DBFS]
        if len(live) < 10:
            raise LawError(f"no audio in [{t0:.2f}, {t1:.2f}]")
        speech = float(np.median(live[live > np.percentile(live, 30)]))
        bed = float(np.percentile(live, 10))
        quiet = min(speech - VALLEY_BELOW_SPEECH_DB, max(speech - QUIET_BELOW_SPEECH_DB, bed + BED_PLUS_DB))
        return {"speech_db": round(speech, 1), "bed_db": round(bed, 1), "quiet_db": round(quiet, 1),
                "loud_db": round(speech - VALLEY_BELOW_SPEECH_DB, 1)}


def quiet_runs(t, db, quiet_db, genuine=False):
    """Contiguous runs of frames below quiet_db as (start, end); end = first non-quiet frame time.
    genuine=True also excludes digital silence (< DIGITAL_FLOOR_DBFS) from a run."""
    mask = db < quiet_db
    if genuine:
        mask &= db > DIGITAL_FLOOR_DBFS
    runs, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            runs.append((float(t[i]), float(t[j]) if j < n else float(t[-1]) + HOP_S))
            i = j
        else:
            i += 1
    return runs


def first_onset(t, db, loud_db, start=None):
    """First frame >= loud_db sustained ONSET_SUSTAIN_S, at or after `start`."""
    k = int(round(ONSET_SUSTAIN_S / HOP_S))
    for i in range(len(db)):
        if (start is None or t[i] >= start - 1e-9) and i + k <= len(db) and np.all(db[i:i + k] >= loud_db):
            return float(t[i])
    return None


def last_offset(t, db, loud_db, end=None):
    """End time of the last frame >= loud_db (sustained), at or before `end`."""
    k = int(round(ONSET_SUSTAIN_S / HOP_S))
    for i in range(len(db) - 1, -1, -1):
        if (end is None or t[i] <= end + 1e-9) and i - k + 1 >= 0 and np.all(db[i - k + 1:i + 1] >= loud_db):
            return float(t[i]) + HOP_S
    return None


def find_pause(sa, a, b):
    """Longest pause (>= PAUSE_MIN_S) overlapping [a, b]. Returns dict or None."""
    lv = sa.levels(a - LEVEL_WINDOW_S, b + LEVEL_WINDOW_S)
    t, d = sa.sl(max(0.0, a - 0.5), min(sa.dur, b + 0.5))
    runs = [(s, e) for s, e in quiet_runs(t, d, lv["quiet_db"])
            if e - s >= PAUSE_MIN_S - 1e-9 and e > a and s < b]
    if not runs:
        return None, lv
    s, e = max(runs, key=lambda r: r[1] - r[0])
    return {"start": round(s, 3), "end": round(e, 3), "ms": int(round((e - s) * 1000))}, lv


# ── lexical adjudication for unpunctuated transcripts ──

# ── boundaries ──

def boundary(sa, words, k):
    """Sentence boundary between word k and k+1 (k = -1: file head; k = len-1: file end)."""
    n = len(words)
    rec = {"after_word": words[k]["word"] if k >= 0 else "<file head>",
           "before_word": words[k + 1]["word"] if k + 1 < n else "<file end>"}
    if k < 0:                                            # file head: lexical start by definition
        lv = sa.levels(max(0.0, words[0]["start"] - LEVEL_WINDOW_S), min(sa.dur, words[0]["end"] + LEVEL_WINDOW_S))
        t, d = sa.sl(0.0, min(sa.dur, words[0]["end"] + 0.5))
        onset = first_onset(t, d, lv["quiet_db"])
        if onset is None:
            return {**rec, "valid": False, "reason": "no onset found at file head", "levels": lv}
        runs = [r for r in quiet_runs(t, d, lv["quiet_db"], genuine=True) if abs(r[1] - onset) < 1e-6]
        lead = runs[0][1] - runs[0][0] if runs else 0.0
        return {**rec, "valid": True, "lexical": "file head", "file_head": True, "levels": lv,
                "onset": round(onset, 3), "genuine_lead_ms": int(round(lead * 1000)),
                "pause": {"start": round(onset - lead, 3), "end": round(onset, 3), "ms": int(round(lead * 1000))}}
    if k + 1 >= n:                                       # file end
        lv = sa.levels(max(0.0, words[k]["start"] - LEVEL_WINDOW_S), min(sa.dur, words[k]["end"] + LEVEL_WINDOW_S))
        t, d = sa.sl(max(0.0, words[k]["start"]), sa.dur)
        off = last_offset(t, d, lv["quiet_db"])
        if off is None:
            return {**rec, "valid": False, "reason": "no offset found at file end", "levels": lv}
        return {**rec, "valid": is_terminal(words[k]["word"]), "lexical": "punctuation", "file_end": True,
                "levels": lv, "pause": {"start": round(off, 3), "end": round(sa.dur, 3),
                                        "ms": int(round((sa.dur - off) * 1000))}}
    pause, lv = find_pause(sa, words[k]["start"], words[k + 1]["end"])
    rec.update(levels=lv, pause=pause)
    if pause is None:
        return {**rec, "valid": False, "reason": f"no pause >= {int(PAUSE_MIN_S * 1000)} ms between the words"}
    if not is_punctuated(words, k):
        return {**rec, "valid": False, "lexical": "unpunctuated",
                "reason": "unpunctuated transcript stretch: no sentence evidence (fail closed)"}
    rec["lexical"] = "punctuation"
    if not is_terminal(words[k]["word"]):
        return {**rec, "valid": False, "reason": f"'{words[k]['word']}' does not end a sentence"}
    return {**rec, "valid": True}


def edge_plan(sa, words, i0, i1):
    """Boundaries around words[i0..i1] and the legal cut ranges they allow."""
    bin_ = boundary(sa, words, i0 - 1)
    bout = boundary(sa, words, i1)
    plan = {"in": bin_, "out": bout}
    if bin_["valid"]:
        p = bin_["pause"]
        if bin_.get("file_head"):
            # keep every genuine sample before the onset; codec zeros before it are not room tone
            # (the cut drops them and the declared pad replaces them when the lead is < 80 ms)
            pad = 0.0 if bin_["genuine_lead_ms"] >= LEAD_MIN_S * 1000 else LEAD_PAD_S
            bin_.update(cut_lo=0.0, cut_hi=p["start"], cut=p["start"], lead_in_pad_s=pad, cuttable=True)
        elif p["end"] - p["start"] >= LEAD_MIN_S - 1e-9:
            bin_.update(cut_lo=p["start"], cut_hi=round(p["end"] - LEAD_MIN_S, 3), cuttable=True,
                        cut=round(max(p["start"], p["end"] - LEAD_TARGET_S), 3), lead_in_pad_s=0.0)
        else:
            bin_.update(cuttable=False, reason=f"pause {p['ms']} ms < lead-in {int(LEAD_MIN_S * 1000)} ms")
    if bout["valid"]:
        p = bout["pause"]
        guard = 0.0 if bout.get("file_end") else GUARD_S
        if p["end"] - p["start"] >= TAIL_MIN_S + guard - 1e-9:
            bout.update(cut_lo=round(p["start"] + TAIL_MIN_S, 3), cut_hi=round(p["end"] - guard, 3),
                        cut=round(min(p["start"] + TAIL_TARGET_S, p["end"] - guard), 3), cuttable=True)
        else:
            bout.update(cuttable=False, reason=f"pause {p['ms']} ms < tail {int(TAIL_MIN_S * 1000)} ms + "
                                               f"guard {int(guard * 1000)} ms")
    plan["ok"] = bool(bin_.get("cuttable") and bout.get("cuttable"))
    return plan


# ── selection lock ──

def anchor(words, text, min_ratio=ANCHOR_MIN_RATIO, t0=None, t1=None):
    """Locate the editor's selected text in a word-timestamp transcript (text alignment, never time
    arithmetic; [t0, t1] only narrows the search). The span's first and last tokens must equal the
    selection's. Returns (i0, i1, ratio) or None."""
    qt = tokens(text)
    toks = [(t, wi) for wi, w in enumerate(words)
            if (t0 is None or w["start"] >= t0) and (t1 is None or w["start"] <= t1) for t in tokens(w["word"])]
    seq = [t for t, _ in toks]
    if len(qt) < 3 or not seq:
        return None
    blk = max(SequenceMatcher(None, qt, seq, autojunk=False).get_matching_blocks(), key=lambda b: b.size)
    if blk.size < 3:
        return None
    base, best = blk.b - blk.a, None
    for s in range(max(0, base - 8), min(len(seq), base + 9)):
        if seq[s] != qt[0]:
            continue
        for e in range(s + max(1, len(qt) - 9), min(len(seq), s + len(qt) + 9)):
            if seq[e] != qt[-1]:
                continue
            r = SequenceMatcher(None, qt, seq[s:e + 1], autojunk=False).ratio()
            if best is None or r > best[0] + 1e-9:
                best = (r, s, e)
    if best is None or best[0] < min_ratio:
        return None
    r, s, e = best
    i0, i1 = toks[s][1], toks[e][1]
    if tokens(words[i0]["word"])[0] != qt[0] or tokens(words[i1]["word"])[-1] != qt[-1]:
        return None
    return i0, i1, round(r, 3)


def _lock_digest(lock):
    body = {k: v for k, v in lock.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def make_lock(video_id, words, i0, i1, transcript_sha256, selected_text, selected_window=None,
              align_ratio=None, created_by=""):
    lock = {"schema": "pulse.selection_lock.v1", "video_id": video_id, "transcript_sha256": transcript_sha256,
            "i0": i0, "i1": i1, "first_word": words[i0]["word"].strip(), "last_word": words[i1]["word"].strip(),
            "text": " ".join(w["word"].strip() for w in words[i0:i1 + 1]), "n_words": i1 - i0 + 1,
            "selected_text": selected_text, "selected_window": selected_window, "align_ratio": align_ratio,
            "created_by": created_by}
    lock["sha256"] = _lock_digest(lock)
    return lock


def verify_lock(lock, transcript_path=None):
    errs = []
    if not lock or lock.get("schema") != "pulse.selection_lock.v1":
        return ["no selection lock"]
    if _lock_digest(lock) != lock.get("sha256"):
        errs.append("selection lock modified after selection (sha256 mismatch)")
    if transcript_path is not None and sha256_file(transcript_path) != lock["transcript_sha256"]:
        errs.append("transcript changed since selection (sha256 mismatch)")
    return errs


# ── cut placement from the locks (replaces the +-2 s snap search) ──

def _segments(edl):
    yield "hook", edl["hook"]
    for c in edl.get("clips", []):
        yield f"clip_{c['index']:02d}", c


def _accepted_cut_pair(src, plan, step=HOP_S):
    """The cut pair nearest the plan's targets, searched ONLY inside the legal (locked-pause) ranges,
    that also passes cut_accept's unchanged OUT-pause and IN-speech checks. None if no pair does."""
    from cut_accept import envelope, speech_median_db, check_cut_out, check_cut_in
    pi, po = plan["in"], plan["out"]

    def grid(lo, hi, target):
        n = int(round((hi - lo) / step))
        pts = sorted({round(min(hi, lo + i * step), 3) for i in range(n + 1)} | {round(target, 3)})
        return sorted(pts, key=lambda x: (abs(x - target), x))
    t, db = envelope(src, pi["cut_lo"] - 1.0, po["cut_hi"] + 1.0)
    med = speech_median_db(t, db, pi["cut"], po["cut"])
    out_ok = next((x for x in grid(po["cut_lo"], po["cut_hi"], po["cut"]) if check_cut_out(t, db, x, med)[0]), None)
    in_ok = next((x for x in grid(pi["cut_lo"], pi["cut_hi"], pi["cut"]) if check_cut_in(t, db, x, med)[0]), None)
    if out_ok is None or in_ok is None:
        return None
    from cut_accept import check_cut_acoustics
    return (in_ok, out_ok) if check_cut_acoustics(src, in_ok, out_ok)[0] else None


def write_lock_cut_table(run_dir):
    """cuts_final.json with every cut placed inside the pause that bounds its LOCKED sentence(s):
    the cut can never add or drop a word. A segment whose locked edges are not cuttable is written
    verified=false with the reason (acceptance then HOLDs; no search outside the pause)."""
    with open(os.path.join(run_dir, "edl.json")) as f:
        edl = json.load(f)
    cuts = []
    for label, seg in _segments(edl):
        lock = seg.get("selection_lock")
        entry = {"clip_id": label, "video_id": seg["video_id"], "channel": seg.get("channel", ""),
                 "fade_out_ms": 30, "fade_in_ms": 20, "verified": False}
        tpath = os.path.join(run_dir, "transcripts", f"{seg['video_id']}.json")
        errs = verify_lock(lock, tpath if os.path.exists(tpath) else None)
        if errs:
            cuts.append({**entry, "error": "; ".join(errs)})
            continue
        with open(tpath) as f:
            words = json.load(f)["words"]
        plan = edge_plan(SourceAudio(os.path.join(run_dir, "sources", f"{seg['video_id']}.mp4")), words,
                         lock["i0"], lock["i1"])
        entry.update(first_word_expected=lock["first_word"], last_word_expected=lock["last_word"],
                     selection_lock_sha256=lock["sha256"],
                     pause_in=plan["in"].get("pause"), pause_out=plan["out"].get("pause"))
        if not plan["ok"]:
            why = [f"{s.upper()}: {plan[s].get('reason') or 'not cuttable'}" for s in ("in", "out")
                   if not plan[s].get("cuttable")]
            cuts.append({**entry, "error": "locked sentence edges not cuttable: " + "; ".join(why)})
            continue
        pick = _accepted_cut_pair(os.path.join(run_dir, "sources", f"{seg['video_id']}.mp4"), plan)
        if pick is None:
            cuts.append({**entry, "error": (
                f"no point inside the locked pauses passes cut_accept (IN {plan['in']['cut_lo']}-"
                f"{plan['in']['cut_hi']}, OUT {plan['out']['cut_lo']}-{plan['out']['cut_hi']})")})
            continue
        cut_in, cut_out = pick
        cuts.append({**entry, "cut_in": cut_in, "cut_out": cut_out, "cut_duration": round(cut_out - cut_in, 3),
                     "lead_in_pad_s": plan["in"]["lead_in_pad_s"], "verified": True})
    with open(os.path.join(run_dir, "cuts_final.json"), "w") as f:
        json.dump(cuts, f, indent=2)
    return cuts


# ── G16 SENTENCE_BOUNDARY (pre-render and final gate) ──


def gate_g16(run_dir, source_path_fn=None):
    """Every clip's cut must hold exactly its locked sentence(s): lock intact, expected words equal the
    lock (never recomputed), both edges legal sentence boundaries, cut points inside those pauses
    (or a declared room-tone pad at a file head without lead-in). Returns (ok, table)."""
    with open(os.path.join(run_dir, "edl.json")) as f:
        edl = json.load(f)
    with open(os.path.join(run_dir, "cuts_final.json")) as f:
        cuts = {c["clip_id"]: c for c in json.load(f)}
    table, ok_all = [], True
    for label, seg in _segments(edl):
        row = {"segment": label, "video_id": seg.get("video_id"), "errors": []}
        lock = seg.get("selection_lock")
        tpath = os.path.join(run_dir, "transcripts", f"{seg.get('video_id')}.json")
        row["errors"] += verify_lock(lock, tpath if os.path.exists(tpath) else None)
        cut = cuts.get(label)
        if cut is None:
            row["errors"].append("no cut in cuts_final.json")
        elif not cut.get("verified") or "cut_in" not in cut or "cut_out" not in cut:
            row["errors"].append(f"cut not verified: {cut.get('error', 'no cut points')}")
        if not row["errors"]:
            if (cut.get("first_word_expected"), cut.get("last_word_expected")) != (lock["first_word"], lock["last_word"]):
                row["errors"].append(
                    f"expected words '{cut.get('first_word_expected')}'/'{cut.get('last_word_expected')}' differ from "
                    f"the selection lock '{lock['first_word']}'/'{lock['last_word']}' (recomputed after selection)")
            with open(tpath) as f:
                words = json.load(f)["words"]
            src = (source_path_fn or (lambda v: os.path.join(run_dir, "sources", f"{v}.mp4")))(seg["video_id"])
            sa = SourceAudio(src)
            plan = edge_plan(sa, words, lock["i0"], lock["i1"])
            row["in"] = _edge_row(plan["in"], cut["cut_in"], "in", cut)
            row["out"] = _edge_row(plan["out"], cut["cut_out"], "out", cut)
            row["errors"] += [f"IN: {row['in']['why']}"] if not row["in"]["pass"] else []
            row["errors"] += [f"OUT: {row['out']['why']}"] if not row["out"]["pass"] else []
            row["locked"] = f"'{lock['first_word']}' ... '{lock['last_word']}' ({lock['n_words']} words)"
        row["pass"] = not row["errors"]
        ok_all &= row["pass"]
        table.append(row)
    return ok_all, table


def _edge_row(b, cut_t, side, cut):
    r = {"cut": cut_t, "boundary_valid": b.get("valid"), "pause": b.get("pause"), "lexical": b.get("lexical"),
         "after_word": b.get("after_word"), "before_word": b.get("before_word")}
    if not b.get("valid"):
        return {**r, "pass": False, "why": f"no sentence boundary: {b.get('reason')}"}
    if not b.get("cuttable"):
        return {**r, "pass": False, "why": f"boundary not cuttable: {b.get('reason')}"}
    r.update(cut_lo=b["cut_lo"], cut_hi=b["cut_hi"])
    if side == "in" and b.get("file_head"):
        need = b["lead_in_pad_s"]
        have = float(cut.get("lead_in_pad_s") or 0.0)
        in_range = b["cut_lo"] - EDGE_EPS_S <= cut_t <= b["cut_hi"] + EDGE_EPS_S
        ok = in_range and have + 1e-9 >= need
        return {**r, "pass": ok, "genuine_lead_ms": b["genuine_lead_ms"], "pad_needed_s": need, "pad_declared_s": have,
                "why": "ok" if ok else (f"source starts speaking {b['genuine_lead_ms']} ms after its genuine audio "
                                        f"begins (< {int(LEAD_MIN_S * 1000)} ms) and no {need:.2f} s lead-in pad is declared"
                                        if in_range else f"cut_in {cut_t:.3f} cuts into the source's first words")}
    ok = b["cut_lo"] - EDGE_EPS_S <= cut_t <= b["cut_hi"] + EDGE_EPS_S
    return {**r, "pass": ok, "why": "ok" if ok else
            f"cut_{side} {cut_t:.3f} outside the legal range {b['cut_lo']:.3f}-{b['cut_hi']:.3f} "
            f"(pause {b['pause']['start']:.3f}-{b['pause']['end']:.3f} between '{b['after_word']}' and '{b['before_word']}')"}


# ── D1 lead-in pad: room tone + held first frame before a file-head sentence ──

def room_tone(src_path, t0, t1, seconds, sr=48000):
    """`seconds` of the source's own quietest genuine room tone found in [t0, t1] (>= 40 ms run),
    looped with 10 ms crossfades. Raises LawError if the source has none (fail closed)."""
    sa = SourceAudio(src_path)
    lv = sa.levels(t0, t1)
    t, d = sa.sl(t0, t1)
    runs = [(s, e) for s, e in quiet_runs(t, d, lv["quiet_db"], genuine=True) if e - s >= 0.040 - 1e-9]
    if not runs:
        raise LawError("no genuine room tone in the segment to build a lead-in pad")
    s, e = min(runs, key=lambda r: float(np.median(d[(t >= r[0] - 1e-9) & (t < r[1] - 1e-9)])))
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{s:.3f}", "-i", src_path, "-t", f"{e - s:.3f}", "-vn",
                        "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True, timeout=60)
    x = np.frombuffer(r.stdout, np.float32).reshape(-1, 2).astype(np.float64)
    m, n = int(0.010 * sr), int(round(seconds * sr))
    if len(x) <= 2 * m:
        raise LawError("room-tone run too short to loop")
    out = x.copy()
    ramp = np.linspace(0.0, 1.0, m)[:, None]
    while len(out) < n:
        out = np.concatenate([out[:-m], out[-m:] * (1 - ramp) + x[:m] * ramp, x[m:]])
    out = out[:n]
    k = int(0.020 * sr)
    out[:k] *= np.linspace(0.0, 1.0, k)[:, None]           # M19 20 ms fade-in at the new head
    return out.astype(np.float32), {"from_s": round(s, 3), "to_s": round(e, 3)}


def apply_lead_in_pad(run_dir, cut, fps, qp):
    """Prepend cut['lead_in_pad_s'] of room tone + the held first frame to qa/final_<clip>.mp4
    (atomic replace). The pad is declared in cuts_final.json, so every gate knows it is there."""
    import wave
    pad = float(cut["lead_in_pad_s"])
    clip = os.path.join(run_dir, "qa", f"final_{cut['clip_id']}.mp4")
    src = os.path.join(run_dir, "sources", f"{cut['video_id']}.mp4")
    tone, info = room_tone(src, cut["cut_in"], cut["cut_out"], pad)
    wav = os.path.join(run_dir, "qa", f"leadpad_{cut['clip_id']}.wav")
    with wave.open(wav, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(48000)
        f.writeframes((np.clip(tone, -1, 1) * 32767).astype(np.int16).tobytes())
    part = clip + ".pad.mp4"
    fmt = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-i", wav, "-filter_complex",
                    f"[0:v]tpad=start_duration={pad:.3f}:start_mode=clone,setpts=PTS-STARTPTS[v];"
                    f"[1:a]{fmt}[p];[0:a]{fmt}[c];[p][c]concat=n=2:v=0:a=1[a]",
                    "-map", "[v]", "-map", "[a]", "-r", str(fps), "-c:v", "h264_nvenc", "-preset", "p4",
                    "-rc", "constqp", "-qp", str(qp), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-ac", "2", "-movflags", "+faststart", part],
                   check=True, capture_output=True, timeout=300)
    os.replace(part, clip)
    return {"pad_s": pad, "room_tone_source_s": info, "wav": os.path.basename(wav)}


# ── G17 ONSET/TAIL INTEGRITY (rendered audio) ──

def head_tail(sa):
    """Genuine lead-in before the first onset and genuine tail after the last offset of a rendered
    segment, each measured with levels LOCAL to that edge (first / last LEVEL_WINDOW_S seconds)."""
    w = min(sa.dur, LEVEL_WINDOW_S)
    lh, lt = sa.levels(0.0, w), sa.levels(sa.dur - w, sa.dur)
    th, dh = sa.sl(0.0, w)
    tt, dt = sa.sl(sa.dur - w, sa.dur)
    onset, off = first_onset(th, dh, lh["quiet_db"]), last_offset(tt, dt, lt["quiet_db"])
    lead = next((e - s for s, e in quiet_runs(th, dh, lh["quiet_db"], genuine=True)
                 if onset is not None and abs(e - onset) < 1e-6), 0.0)
    tail = next((e - s for s, e in quiet_runs(tt, dt, lt["quiet_db"], genuine=True)
                 if off is not None and abs(s - off) < 1e-6), 0.0)
    return {"onset": onset, "offset": off, "lead_ms": int(round(lead * 1000)), "tail_ms": int(round(tail * 1000)),
            "levels": {"head": lh, "tail": lt}}


def gate_g17_prepared(clip_paths):
    """G17a on each prepared clip {clip_id: path} (qa/final_<clip>.mp4: the rendered segment audio
    before the music bed): >= 80 ms genuine quiet before the first onset and after the last offset."""
    table, ok_all = [], True
    for cid, p in clip_paths.items():
        ht = head_tail(SourceAudio(p))
        lead_ok, tail_ok = ht["lead_ms"] >= LEAD_MIN_S * 1000, ht["tail_ms"] >= TAIL_MIN_S * 1000
        row = {"segment": cid, **{k: ht[k] for k in ("onset", "offset", "lead_ms", "tail_ms")},
               "quiet_db": {k: v["quiet_db"] for k, v in ht["levels"].items()},
               "lead_ok": lead_ok, "tail_ok": tail_ok, "pass": lead_ok and tail_ok}
        ok_all &= row["pass"]
        table.append(row)
    return ok_all, table


def gate_g17_output(final_path, segments, cuts, run_dir, source_path_fn=None):
    """G17b on a final output: the first and last word of every clip keep >= 85 % of their duration.
    The render may only add silence around a word: the speech onset (offset) measured in the output
    must not come later (earlier) than in the source, relative to the clip start, by more than 15 % of
    the locked edge word's transcript duration (clamped 0.10-1.00 s). Returns (ok, table)."""
    with open(os.path.join(run_dir, "edl.json")) as f:
        locks = {label: seg.get("selection_lock") for label, seg in _segments(json.load(f))}
    by = {c["clip_id"]: c for c in cuts}
    out = SourceAudio(final_path)
    table, ok_all = [], True
    for seg in segments:
        if seg.get("type") != "talking_head":
            continue
        label, c, lock = seg["label"], by.get(seg["label"]), locks.get(seg["label"])
        row = {"segment": label}
        if c is None or not lock:
            row.update(pass_=False, why="no cut or no selection lock")
        else:
            pad = float(c.get("lead_in_pad_s") or 0.0)
            src = (source_path_fn or (lambda v: os.path.join(run_dir, "sources", f"{v}.mp4")))(c["video_id"])
            sa = SourceAudio(src)
            ls = sa.levels(c["cut_in"], c["cut_out"])
            ts, ds = sa.sl(c["cut_in"], c["cut_out"])
            lo = out.levels(seg["start"], seg["end"])
            to, do = out.sl(seg["start"] + pad, seg["end"])
            s_on, s_off = first_onset(ts, ds, ls["loud_db"]), last_offset(ts, ds, ls["loud_db"])
            o_on, o_off = first_onset(to, do, lo["loud_db"]), last_offset(to, do, lo["loud_db"])
            with open(os.path.join(run_dir, "transcripts", f"{c['video_id']}.json")) as f:
                words = json.load(f)["words"]
            dur = lambda w: min(1.0, max(0.10, w["end"] - w["start"]))
            d0, d1 = dur(words[lock["i0"]]), dur(words[lock["i1"]])
            if None in (s_on, s_off, o_on, o_off):
                row.update(pass_=False, why="speech onset/offset not measurable")
            else:
                late = (o_on - seg["start"] - pad) - (s_on - c["cut_in"])
                early = (s_off - c["cut_in"]) - (o_off - seg["start"] - pad)
                head_ok = late <= (1 - WORD_DURATION_RATIO_MIN) * d0 + HOP_S
                tail_ok = early <= (1 - WORD_DURATION_RATIO_MIN) * d1 + HOP_S
                row.update(onset_late_ms=int(round(late * 1000)), offset_early_ms=int(round(early * 1000)),
                           first_word_ratio=round(max(0.0, 1 - max(0.0, late) / d0), 3),
                           last_word_ratio=round(max(0.0, 1 - max(0.0, early) / d1), 3),
                           head_ok=head_ok, tail_ok=tail_ok, pass_=head_ok and tail_ok)
        row["pass"] = row.pop("pass_")
        ok_all &= row["pass"]
        table.append(row)
    return ok_all, table
