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
PAD_S = 1.5


def audio_window(video_id, start, end, out_dir, pad=PAD_S):
    """WAV (16 kHz mono) of [start - pad, end + pad] (clamped at the video head), fetched with yt-dlp's download
    sections -> (path, the window's real start in video seconds)."""
    os.makedirs(out_dir, exist_ok=True)
    a, b = max(0.0, start - pad), end + pad
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


def _w(t):
    return re.sub(r"[^\w']", "", (t or "").lower().replace("’", "'"))


def edges(second, wav_start, start, end, text):
    """CUTTABLE (orchestrator 06:45 ruling C, ruling 7 (1)): the INDEPENDENT recogniser's own sentence boundaries at
    the segment's edges, from its word timing on the SOURCE audio. IN: the recogniser's word at the clip's first word
    (same word, within 0.6 s) follows a word ending in terminal punctuation. OUT: the recogniser's word at the clip's last
    word (within 0.8 s) ends in terminal punctuation, and the recogniser heard a next word (it did not stop at the
    window's edge). Store or caption punctuation is never evidence. -> {"cuttable", "in", "out"}."""
    ws = [w for w in second.get("words") or [] if w.get("start") is not None]
    toks = re.findall(r"[\w'’$%.,-]+", re.sub(r"\s+\.(?=\w)", ".", text or ""))     # 'U .S.' is one word 'U.S.' 
    first, last = _w(toks[0]) if toks else "", _w(toks[-1]) if toks else ""
    out = {"in": {"ok": False, "why": "no word timing from the recogniser"},
           "out": {"ok": False, "why": "no word timing from the recogniser"}}
    if not ws or not first:
        return dict(out, cuttable=False)
    t_in, t_out = start - wav_start, end - wav_start
    ci = [i for i, w in enumerate(ws) if abs(float(w["start"]) - t_in) <= 0.6 and _w(w["text"]).startswith(first[:4])]
    co = [i for i, w in enumerate(ws) if abs(float(w.get("end") or w["start"]) - t_out) <= 0.8
          and _w(w["text"]).rstrip(".")[:4] == last.rstrip(".")[:4]]
    if ci:
        i = ci[0]
        prev = ws[i - 1]["text"] if i > 0 else None
        out["in"] = {"ok": prev is not None and prev.rstrip().endswith(TERMINAL), "word": ws[i]["text"],
                     "before": prev, "why": "a sentence ends before the clip" if prev and prev.rstrip().endswith(TERMINAL)
                     else ("the window starts at the clip: no word before it" if prev is None else
                           f"the recogniser runs on into the clip ('{prev}')")}
    else:
        out["in"] = {"ok": False, "why": f"the recogniser has no '{first}' within 0.6 s of the clip's start"}
    if co:
        i = co[-1]
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
    off = start - (wav_start if wav_start is not None else max(0.0, start - PAD_S))
    span = span_text(sec, off, off + (end - start)) or sec["text"]
    cmp_ = compare(text, span)
    turns = speaker_turns(sec, off, off + (end - start))
    return {"video_id": video_id, "start": start, "end": end, "model": rep.backend, "replayed": rep.replayed,
            "second_pass_text": span, "transcript_ok": cmp_["ok"], "disagree": cmp_["disagree"],
            "critical": cmp_["critical"], "speakers": turns, "audio": os.path.basename(wav),
            "edges": edges(sec, wav_start if wav_start is not None else max(0.0, start - PAD_S), start, end, text),
            "ok": cmp_["ok"] and turns["turn_change_inside"] is False}
