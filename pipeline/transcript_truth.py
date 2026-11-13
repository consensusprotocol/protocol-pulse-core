#!/usr/bin/env python3
"""pipeline/transcript_truth.py — SPEAKER AND TRANSCRIPT TRUTH (law L-v, orchestrator 2026-11-12 '02:30').

(2) Every gate trusts one Whisper transcript. For EVERY selected segment, a second, independent recognition pass runs
    on the SOURCE audio through the router's "transcribe" chain (law L-x: pipeline/model_providers.json). Any
    disagreement on a number, a name or a negation, in either direction, drops the moment.
(1) The same pass's diarisation reports the speaker turns inside the segment: a moment may not span a speaker change,
    and "not measured" never passes; a person is NAMED only from verified evidence, never from a diarisation label.

audio_window() fetches the audio of [start - pad, end + pad] of a YouTube video on CPU (yt-dlp download sections +
ffmpeg to 16 kHz mono WAV) into a caller-given directory (the integrator already holds the downloaded window:
verify_segment() takes any audio path). No GPU, no Whisper. Keys by name inside the router's back-ends.
"""
import json
import os
import re
import subprocess

import canon

NEGATIONS = frozenset({"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "cannot", "can't",
                       "won't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "shouldn't",
                       "wouldn't", "couldn't", "hasn't", "haven't", "hadn't"})
_NUM = re.compile(r"^-?\d+(\.\d+)?$")
PAD_S = 1.5                  # the audio fetched after the clip
PAD_BEFORE_S = 4.0           # ruling 38 (03:12 ET Nov 13): the audio before the clip, so the recogniser hears the
                             # sentence before it (1.5 s ended inside measured pauses: "the window starts at the clip")
PAUSE_MIN_S = 0.700          # ruling 38: a measured pause this long with no recognised word also opens a clip
CANON_RUN = 6                # recogniser words read together at an edge, so a spoken number is one canonical token


def audio_window(video_id, start, end, out_dir, pad=PAD_S, pad_before=PAD_BEFORE_S):
    """WAV (16 kHz mono) of [start - pad_before, end + pad] (clamped at the video head), fetched with yt-dlp's
    download sections -> (path, the window's real start in video seconds)."""
    os.makedirs(out_dir, exist_ok=True)
    a, b = max(0.0, start - pad_before), end + pad
    stem = f"{video_id}_{int(a * 1000)}_{int(b * 1000)}"
    base = os.path.join(out_dir, stem)
    wav = base + ".wav"
    if os.path.exists(wav):
        return wav, a
    subprocess.run(["yt-dlp", "-q", "--no-playlist", "-f", "bestaudio", "--download-sections", f"*{a:.2f}-{b:.2f}",
                    "--force-keyframes-at-cuts", "-o", base + ".%(ext)s", f"https://www.youtube.com/watch?v={video_id}"],
                   check=True, timeout=300, capture_output=True)
    src = next(os.path.join(out_dir, f) for f in sorted(os.listdir(out_dir))
               if os.path.splitext(f)[0] == stem and not f.endswith(".wav"))       # exact stem: never a longer id
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True,
                   timeout=120)
    return wav, a


def second_pass(router, wav):
    """The second, independent recognition pass through the router's "transcribe" chain (law L-x): ({"text",
    "segments": [{"speaker", "start", "end", "text"}]}, the Reply naming the back-end)."""
    return router.transcribe("transcribe", wav)


FILLERS = frozenset({"um", "uh", "erm", "hmm", "mm", "ah", "oh", "yeah", "okay", "ok"})


def critical_tokens(text):
    """The tokens law L-v 2 protects: numbers (canonical values), negations, and proper names (capitalised words that
    are not English words: vo_fidelity.lexicon; never a filler, never the unit letter of a number such as the K of
    '16K')."""
    import vo_fidelity as VF
    toks = canon.canon_tokens(text)
    nums = [t for t in toks if _NUM.match(t)]
    negs = [t for t in toks if t in NEGATIONS or t.endswith("n't")]
    words = re.findall(r"(?<![\w$])[A-Za-z][A-Za-z'’-]*", text or "")
    names = sorted({w for w in words if w[0].isupper() and w not in ("I",) and w.lower() not in FILLERS and
                    re.sub(r"['’]s$", "", w).lower() not in VF.lexicon()})
    return {"numbers": nums, "negations": negs, "names": names}


def compare(selected_text, second_text):
    """BOTH directions, with counts (audit p2 C4): every number and negation of the selected sentences is read as
    often in the second pass's text of the same span, and the second pass reads none the first did not (a dropped
    "not" is as fatal as an added one); every name of either side appears on the other (case folded).
    -> {"ok", "disagree": {...}, "critical": first, "second_critical": second}."""
    from collections import Counter
    a, b = critical_tokens(selected_text), critical_tokens(second_text)
    dis = {}
    for k in ("numbers", "negations"):
        ca, cb = Counter(a[k]), Counter(b[k])
        dis[k] = sorted(set((ca - cb).elements()) | set((cb - ca).elements()))
    fold = lambda ns: {n.lower().rstrip("'’s") for n in ns}
    ta, tb = set(canon.canon_tokens(selected_text)), set(canon.canon_tokens(second_text))
    dis["names"] = sorted({n for n in a["names"] if n.lower().rstrip("'’s") not in tb | fold(b["names"])} |
                          {n for n in b["names"] if n.lower().rstrip("'’s") not in ta | fold(a["names"])})
    return {"ok": not any(dis.values()), "disagree": dis, "critical": a, "second_critical": b}


def _inside(x, start_rel, end_rel):
    if x.get("start") is None or x.get("end") is None:
        return False
    mid = (float(x["start"]) + float(x["end"])) / 2
    return start_rel - 0.15 <= mid <= end_rel + 0.15


def span_text(second, start_rel, end_rel):
    """The second pass's words of [start_rel, end_rel] (seconds in the audio): word by word when the back-end gives
    word timing (each word whose midpoint lies inside), else its segments overlapping the span."""
    if second.get("words"):
        return " ".join(w["text"] for w in second["words"] if _inside(w, start_rel, end_rel)).strip()
    return " ".join(s["text"] for s in second["segments"]
                    if s.get("start") is not None and s.get("end") is not None and s["end"] > start_rel + 0.25
                    and s["start"] < end_rel - 0.25).strip()


def speaker_turns(second, start_rel, end_rel):
    """Speakers of the second pass's segments overlapping [start_rel, end_rel] (seconds inside the audio): one label =
    no change inside (False); more = a change (True); none = NOT measured (None, which never passes)."""
    if second.get("words"):
        sp = [w.get("speaker") for w in second["words"] if _inside(w, start_rel, end_rel)]
    else:
        sp = [s.get("speaker") for s in second["segments"]
              if s.get("start") is not None and s.get("end") is not None and s["end"] > start_rel + 0.25
              and s["start"] < end_rel - 0.25]
    labels = sorted({x for x in sp if x})
    return {"labels": labels, "turn_change_inside": (len(labels) > 1) if labels else None}


TERMINAL = (".", "!", "?")
REPAIR_DASHES = ("-", "\u2013", "\u2014")


def _w(t):
    return re.sub(r"[^\w']", "", (t or "").lower().replace("’", "'"))


def self_repair(words, i, first):
    """Orchestrator ruling 8 (08:29): words[i] is a SELF-REPAIR of the clip's first word when it is a truncated
    repetition of it by the same speaker: it ends in a dash, its letters are a non-empty proper prefix of the next
    word's, the next word is the clip's first word, and both carry the same speaker label (a missing label is not the
    same speaker). Heard by the second recogniser and not by the primary, it belongs to the sentence it opens: not a
    missing sentence start, not an L-v 2 disagreement. Exactly one such token; anything else is not one. The next word
    must BE the clip's first word (the same letters, case and punctuation aside; audit 0742 C1 K1: no 4-letter match)."""
    if not 0 <= i < len(words) - 1:
        return False
    r, f = words[i], words[i + 1]
    t = (r.get("text") or "").strip()
    stem, fw, fst = _w(t.rstrip("".join(REPAIR_DASHES))), _w(f.get("text")), _w(first)
    return (t.endswith(REPAIR_DASHES) and bool(stem) and bool(fst) and fw == fst and len(stem) < len(fw)
            and fw.startswith(stem) and r.get("speaker") is not None and r.get("speaker") == f.get("speaker"))


def _canon_from(ws, i):
    """The first canonical token of the recogniser's words from i on (a spoken number read as one token, the L-v 2
    canonicaliser: 'Twenty-five percent' -> '25')."""
    c = canon.canon_tokens(" ".join(w.get("text") or "" for w in ws[i:i + CANON_RUN]))
    return c[0] if c else None


def _canon_to(ws, i):
    """The last canonical token of the recogniser's words up to i ('to sixty-eight thousand.' -> '68000')."""
    c = canon.canon_tokens(" ".join(w.get("text") or "" for w in ws[max(0, i - CANON_RUN + 1):i + 1]))
    return c[-1] if c else None


def edges(second, wav_start, start, end, text):
    """CUTTABLE (orchestrator 06:45 ruling C, ruling 7 (1)): the INDEPENDENT recogniser's own sentence boundaries at
    the segment's edges, from its word timing on the SOURCE audio. The clip's first / last word is found by its first
    four letters OR by the L-v 2 canonicaliser on a short run of the recogniser's words (ruling 39: 'sixty-eight
    thousand.' is the clip's '68,000.'). IN: the recogniser's word at the clip's first word (within 0.6 s) follows a
    word ending in terminal punctuation; or (ruling 38) the recogniser heard no word for at least PAUSE_MIN_S before the
    clip's opening word (a measured pause), or the window reaches the FILE HEAD and holds no word before the clip (the
    clip opens on the file's first spoken word). OUT: the recogniser's word at the clip's last word (within 0.8 s) ends
    in terminal punctuation, and the recogniser heard a next word (it did not stop at the window's edge). Store or
    caption punctuation is never evidence. -> {"cuttable", "in", "out"}."""
    # the recogniser's words in its own (time) order: all 99 recorded transcriptions are time-ordered (audit 0338 C1)
    ws = [w for w in second.get("words") or [] if w.get("start") is not None]
    toks = re.findall(r"[\w'’$%.,-]+", re.sub(r"\s+\.(?=\w)", ".", text or ""))     # 'U .S.' is one word 'U.S.' 
    first, last = _w(toks[0]) if toks else "", _w(toks[-1]) if toks else ""
    # ruling 39: the run of up to CANON_RUN words may reach past the 0.6 / 0.8 s windows; only the CANDIDATE word must
    # sit inside them, the run only reads a spoken number whole (audit 0338 C2, glm N1)
    ct = canon.canon_tokens(text or "")
    c_first, c_last = (ct[0], ct[-1]) if ct else (None, None)
    out = {"in": {"ok": False, "why": "no word timing from the recogniser"},
           "out": {"ok": False, "why": "no word timing from the recogniser"}}
    if not ws or not first:
        return dict(out, cuttable=False)
    t_in, t_out = start - wav_start, end - wav_start
    ci = [i for i, w in enumerate(ws) if abs(float(w["start"]) - t_in) <= 0.6 and
          (_w(w["text"]).startswith(first[:4]) or (c_first is not None and _canon_from(ws, i) == c_first))]
    co = [i for i, w in enumerate(ws) if abs(float(w.get("end") or w["start"]) - t_out) <= 0.8 and
          (_w(w["text"]).rstrip(".")[:4] == last.rstrip(".")[:4] or (c_last is not None and _canon_to(ws, i) == c_last))]
    if ci:                                      # the occurrence NEAREST the clip's start, never an earlier one of the
        i = min(ci, key=lambda k: abs(float(ws[k]["start"]) - t_in))    # same word (audit 0338: grok C2, glm C1 P2-2)
        j, repair = i - 1, None
        if self_repair(ws, j, first):           # ruling 8: the speaker's false start opens the sentence
            repair, j = ws[j]["text"], j - 1
        prev = ws[j]["text"] if j >= 0 else None
        t_open = float(ws[j + 1]["start"])      # the clip's opening word (its self-repair, when there is one)
        gap = t_open - (float(ws[j].get("end") or ws[j]["start"]) if j >= 0 else 0.0)   # no word before: from the
        ends = prev is not None and prev.rstrip().endswith(TERMINAL)                     # window's start
        # (b) is measured on the INDEPENDENT recogniser's word timing, as ruling 38 words it; the acoustic check of the
        # cut itself is the render's (cut_accept.check_cut_acoustics and G16 hold a cut not inside a measured pause)
        head = prev is None and wav_start <= 0.0
        pause = gap >= PAUSE_MIN_S - 1e-9
        out["in"] = {"ok": ends or pause or head, "word": ws[i]["text"], "before": prev,
                     "pause_ms": int(round(gap * 1000)),
                     "why": "a sentence ends before the clip" if ends else
                     ("the clip opens on the file's first spoken word (the window reaches the file head and holds no "
                      "word before it, ruling 38)" if head else
                      (f"a measured pause of {gap * 1000:.0f} ms with no recognised word before the clip "
                       f"(>= {PAUSE_MIN_S * 1000:.0f} ms, ruling 38)" if pause else
                       ("the window starts at the clip: no word before it" if prev is None else
                        f"the recogniser runs on into the clip ('{prev}', {gap * 1000:.0f} ms before it)")))}
        if repair:
            out["in"].update(self_repair=repair, why=out["in"]["why"] + f"; the speaker's false start '{repair}' "
                             "opens the sentence (ruling 8: a self-repair, part of the sentence)")
    else:
        out["in"] = {"ok": False, "why": f"the recogniser has no '{first}' within 0.6 s of the clip's start"}
    if co:                                      # the occurrence nearest the clip's end (audit 0338, as at the IN)
        i = min(co, key=lambda k: abs(float(ws[k].get("end") or ws[k]["start"]) - t_out))
        nxt = ws[i + 1]["text"] if i + 1 < len(ws) else None
        ok = ws[i]["text"].rstrip().endswith(TERMINAL) and nxt is not None
        out["out"] = {"ok": ok, "word": ws[i]["text"], "after": nxt,
                      "why": "a sentence ends at the clip's last word" if ok else
                      ("the recogniser's sentence continues past the clip" if nxt is not None else
                       "the window ends at the clip: no word after it")}
    else:
        out["out"] = {"ok": False, "why": f"the recogniser has no '{last}' within 0.8 s of the clip's end"}
    return dict(out, cuttable=out["in"]["ok"] and out["out"]["ok"])


def verify_segment(router, video_id, start, end, text, work_dir, wav=None, wav_start=None):
    """Both checks for one selected segment -> a record (the second pass's text kept as evidence). ok only when the
    critical tokens agree in both directions AND exactly one speaker was measured inside."""
    if wav is None:
        wav, wav_start = audio_window(video_id, start, end, work_dir)
    sec, rep = second_pass(router, wav)
    off = start - (wav_start if wav_start is not None else max(0.0, start - PAD_BEFORE_S))
    span = span_text(sec, off, off + (end - start)) or sec["text"]
    sw = [w for w in sec.get("words") or [] if _inside(w, off, off + (end - start))]
    toks = re.findall(r"[\w'’$%.,-]+", text or "")
    repair = None
    if len(sw) > 1 and toks and self_repair(sw, 0, toks[0]):     # ruling 8: only a LEADING self-repair, only one
        repair, span = sw[0]["text"], " ".join(w["text"] for w in sw[1:]).strip()
    cmp_ = compare(text, span)
    turns = speaker_turns(sec, off, off + (end - start))
    return {"video_id": video_id, "start": start, "end": end, "model": rep.backend, "replayed": rep.replayed,
            "second_pass_text": span, "self_repair": repair, "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"],
            "critical": cmp_["critical"], "speakers": turns, "audio": os.path.basename(wav),
            "edges": edges(sec, wav_start if wav_start is not None else max(0.0, start - PAD_BEFORE_S), start, end,
                           text),
            "ok": cmp_["ok"] and turns["turn_change_inside"] is False}
