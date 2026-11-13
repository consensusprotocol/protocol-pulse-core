#!/usr/bin/env python3
"""pipeline/lock_precheck.py: RULING 68 (orchestrator 2026-11-13 '14:03'): the render's own ruling-17 lock at the PIN
STAGE. A pin's approved text taken from the word pass (distil-large-v3, batched) can differ from the render's decoder
(large-v3, beam 5) on the same audio (bible E-FAIL-081: 'punch you' for 'punch in', a dropped repeat), and the render
then holds at stage pinned. This runs THE SAME steps earlier, per line-up span: pinned.acquire (the render's acquisition
window and decoder: select_passages._download_window + _whisper_transcribe), pinned.validate_range and
pinned.segment_lock (make_lock, trimmed_lock, adjudicate_lock: build_edl's one code path). The lock text is offered to
the builder as the source of approved text BEFORE the paid verdicts; a span sent with an approved text gets the render's
ruling-17 outcome for it. The render re-checks at stage pinned as now. Nothing is loosened.

CONTRACT (the builder):
- REQUEST: data/lock_precheck/requests/<request_id>.json (write <name>.tmp, then rename):
  {"request_id": str, "segments": [{"video_id": str, "start": number, "end": number, "role": "hook" | "clip",
  optional "approved_text": str, optional "trimmed_leading": str with "untrimmed_start": number}, ...]}
  start / end on the source video's clock, exactly as the pin will carry them. A video's acquisition window is built
  from ITS segments in the request ([min start, max end], padded by _download_window), exactly as pinned.acquire builds
  it from the pin: send a line-up's segments together, as the pin will hold them.
- RESULT: data/lock_precheck/results/<video_id>.<start %.3f>-<end %.3f>.<DECODER_SHA[:12]>.json: a list of entries,
  newest last, each {request_id, video_id, start, end, role, window [lo, hi], offset, source_file_sha256,
  transcript_sha256, decoder_sha, faster_whisper, approved_text (null: none sent), outcome, reason, lock {i0, i1,
  first_word, last_word, text, sha256}, adjudication, scribe_usd, reused, timing {download_s, decode_s, lock_s}, at}.
  outcome: "decoded" (no approved text sent: lock.text is the render's text for the span; an approved text with the
  same canonical tokens meets no difference at the render), "no_difference", "adopted" (ruling 17: the second recogniser
  reads the approved words), "two_readings" (ruling 18), "hold" (the render's stage pinned would hold: reason is its
  PinError), "error" (no verdict, never a pass: the acquisition or the decode failed).
  An identical span, window and approved text under the same DECODER_SHA is answered from its last entry ("reused":
  true; no decode, no second-recogniser spend).
- The request moves to requests/done/ when answered, to requests/failed/ (with "why") when malformed.
- DECODER_SHA: sha256 over CODE, the acquisition, decoder and lock code. An entry under another DECODER_SHA is not
  this code's.
GPU0 (law L-r): stand_alone_scorer's discipline. Downloads run before the lease; a batch of BATCH requests is decoded
under ONE lease, local_judge.YIELD_FLAG checked before taking it, once it is held and before every video (a render
always first), gpu0.release_all at the batch end; the locks and the second recogniser (network) run after it is left.
Usage: CUDA_VISIBLE_DEVICES=0 python3 pipeline/lock_precheck.py serve | once"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys
import time

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import local_judge as LJ  # noqa: E402  (the yield flag)
import pinned  # noqa: E402

ROOT = os.environ.get("PP_LOCK_PRECHECK_DIR", os.path.join(REPO, "data", "lock_precheck"))
OWNER = "pin-stage lock pre-check (integrator, GPU0)"
BATCH = 4
SAFE = re.compile(r"^[A-Za-z0-9_.:~-]{1,120}$")
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
CODE = ("select_passages.py", "punctuation.py", "pinned.py", "sentence_law.py", "canon.py", "gpu0.py")


def decoder_sha():
    h = hashlib.sha256()
    for name in CODE:
        with open(os.path.join(PIPELINE, name), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def problems(r):
    if not isinstance(r, dict):
        return ["not an object"]
    why = [] if isinstance(r.get("request_id"), str) and SAFE.match(r["request_id"]) else \
        [f"request_id must match {SAFE.pattern}"]
    segs = r.get("segments")
    if not isinstance(segs, list) or not segs:
        return why + ["segments must be a non-empty list"]
    for i, s in enumerate(segs):
        if not isinstance(s, dict):
            why.append(f"segments[{i}] is not an object")
            continue
        if not isinstance(s.get("video_id"), str) or not VIDEO_ID.match(s["video_id"]):
            why.append(f"segments[{i}].video_id is not a YouTube id")
        t = (s.get("start"), s.get("end"))
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in t) or not 0 <= t[0] < t[1]:
            why.append(f"segments[{i}]: need numbers 0 <= start < end")
        if s.get("role") not in ("hook", "clip"):
            why.append(f"segments[{i}].role must be 'hook' or 'clip'")
        if "approved_text" in s and not (isinstance(s["approved_text"], str) and s["approved_text"].strip()):
            why.append(f"segments[{i}].approved_text must be a non-empty string when present")
        if ("trimmed_leading" in s) != ("untrimmed_start" in s):
            why.append(f"segments[{i}]: trimmed_leading and untrimmed_start go together")
    return why


def window(segs, vid):
    """pinned.acquire's window for vid: [min start, max end] over that video's segments."""
    mine = [s for s in segs if s["video_id"] == vid]
    return min(s["start"] for s in mine), max(s["end"] for s in mine)


def work_dir(vid, lo, hi, sha):
    """One acquisition directory per video, window and decoder code: _download_window and _whisper_transcribe cache by
    path, so a different window or code never reads another's file."""
    return os.path.join(ROOT, "work", f"{vid}.{lo:.3f}-{hi:.3f}.{sha[:12]}")


def result_path(vid, start, end, sha):
    return os.path.join(ROOT, "results", f"{vid}.{start:.3f}-{end:.3f}.{sha[:12]}.json")


def _entries(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def latest(video_id, start, end, sha=None, window=None, approved_text=None):
    """The newest entry for this span under this decoder code (default: the current), this acquisition window (default:
    the span alone, the video's only segment in its line-up) and approved text (None: a decode request), else None."""
    sha = sha or decoder_sha()
    want = [float(x) for x in (window or (start, end))]
    es = [e for e in _entries(result_path(video_id, start, end, sha))
          if e["start"] == start and e["end"] == end and e["window"] == want and e.get("approved_text") == approved_text]
    return es[-1] if es else None


def _videos(r):
    return list(dict.fromkeys(s["video_id"] for s in r["segments"]))


def _cached(r, sha):
    """True when every segment of r has a non-error entry for its span, window and approved text (answered from it)."""
    for s in r["segments"]:
        e = latest(s["video_id"], s["start"], s["end"], sha, window(r["segments"], s["video_id"]), s.get("approved_text"))
        if e is None or e["outcome"] == "error":
            return False
    return True


def prefetch(r, sha):
    """Every video's window downloaded BEFORE the lease (the call pinned.acquire makes; it caches by path, so acquire
    under the lease finds the file). -> {vid: seconds}."""
    from select_passages import _download_window
    out = {}
    for vid in _videos(r):
        lo, hi = window(r["segments"], vid)
        t = time.time()
        _download_window(vid, lo, hi, work_dir(vid, lo, hi, sha))
        out[vid] = round(time.time() - t, 1)
    return out


def decode(r, sha, log=print):
    """UNDER the lease: pinned.acquire per video (its download a cache hit). -> {vid: (acquisition or None, error or
    None, seconds)}, or None when a render asked before the request was done (it stays pending)."""
    import gpu0
    out = {}
    for vid in _videos(r):
        if LJ.render_wants_gpu0():
            return None
        lo, hi = window(r["segments"], vid)
        wd = work_dir(vid, lo, hi, sha)
        if not os.path.exists(os.path.join(wd, "sources", f"{vid}.mp4")):
            out[vid] = (None, "the source window did not download (before the lease)", 0.0)
            continue
        t = time.time()
        try:
            mine = [dict(s, source={"kind": "youtube"}) for s in r["segments"] if s["video_id"] == vid]
            out[vid] = (pinned.acquire({"segments": mine}, wd, log=log)[vid], None, round(time.time() - t, 1))
        except gpu0.Gpu0Stop:
            raise
        except Exception as e:                                   # no decode, never a pass
            out[vid] = (None, f"{type(e).__name__}: {str(e)[:300]}", round(time.time() - t, 1))
    return out


def _outcome(s, lock):
    if not s.get("approved_text"):
        return "decoded"
    return "adopted" if "adjudication" in lock else "two_readings" if "alternatives" in lock else "no_difference"


def answer(path, r, dl, dec, sha, log=print):
    """After the lease: every segment's lock (pinned.segment_lock, with the second recogniser where ruling 17 calls
    it) appended to its result file; the request moved to done/."""
    import faster_whisper
    for s in r["segments"]:
        vid, (lo, hi) = s["video_id"], window(r["segments"], s["video_id"])
        prev = latest(vid, s["start"], s["end"], sha, (lo, hi), s.get("approved_text"))
        if prev is not None and prev["outcome"] != "error":
            entry = dict(prev, request_id=r["request_id"], role=s["role"], reused=True,
                         at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        else:
            a, err, dsec = dec.get(vid, (None, "not decoded", 0.0))
            spent, lock, reason, t = [], None, err, time.time()

            def recognise(src):                                  # the real second recogniser, its spend recorded
                words, usd = pinned._second_recogniser_words(src)
                spent.append(usd)
                return words, usd
            outcome = "error"
            if a is not None:
                try:
                    v = pinned.validate_range(s, a)
                    lock = pinned.segment_lock(s, a, v, recognise=recognise, log=log)
                    outcome, reason = _outcome(s, lock), None
                except pinned.PinError as e:                     # what the render's stage pinned would hold on
                    outcome, reason = "hold", str(e)
                except Exception as e:
                    reason = f"{type(e).__name__}: {str(e)[:300]}"
            entry = {"request_id": r["request_id"], "video_id": vid, "start": s["start"], "end": s["end"],
                     "role": s["role"], "window": [float(lo), float(hi)],
                     "offset": a["offset"] if a else None,
                     "source_file_sha256": a["provenance"].get("source_file_sha256") if a else None,
                     "transcript_sha256": lock["transcript_sha256"] if lock else None, "decoder_sha": sha,
                     "faster_whisper": faster_whisper.__version__, "approved_text": s.get("approved_text"),
                     "outcome": outcome, "reason": reason,
                     "lock": {k: lock.get(k) for k in ("i0", "i1", "first_word", "last_word", "text", "sha256")}
                     if lock else None,
                     "adjudication": (lock.get("adjudication") or lock.get("alternatives")) if lock else None,
                     "scribe_usd": round(sum(spent), 4), "reused": False,
                     "timing": {"download_s": dl.get(vid, 0.0), "decode_s": dsec, "lock_s": round(time.time() - t, 1)},
                     "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        out = result_path(vid, s["start"], s["end"], sha)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        tmp = out + ".tmp"
        with open(tmp, "w") as f:
            json.dump(_entries(out) + [entry], f, indent=1)
        os.replace(tmp, out)
        log(f"  {r['request_id']}: {vid} {s['start']:.3f}-{s['end']:.3f}: {entry['outcome']}"
            f"{' (reused)' if entry['reused'] else ''}{': ' + entry['reason'][:160] if entry['reason'] else ''}")
    os.makedirs(os.path.join(ROOT, "requests", "done"), exist_ok=True)
    os.replace(path, os.path.join(ROOT, "requests", "done", os.path.basename(path)))


def _load(path):
    try:
        with open(path) as f:
            r = json.load(f)
    except ValueError as e:
        return None, [f"not JSON: {e}"]
    return r, problems(r)


def pending():
    return sorted(glob.glob(os.path.join(ROOT, "requests", "*.json")))


def serve_once(log=print):
    """Answer up to BATCH pending requests: downloads first, the decodes under ONE GPU0 lease, the locks after it.
    -> how many were answered (0: none pending, a render asked, or the lease is held)."""
    import gpu0
    todo = pending()[:BATCH]
    if not todo or LJ.render_wants_gpu0():
        return 0
    sha, ready, n = decoder_sha(), [], 0
    for path in todo:
        r, why = _load(path)
        if why:
            os.makedirs(os.path.join(ROOT, "requests", "failed"), exist_ok=True)
            with open(os.path.join(ROOT, "requests", "failed", os.path.basename(path)), "w") as f:
                json.dump({"request": r, "why": why}, f, indent=1)
            os.remove(path)
            log(f"  {os.path.basename(path)}: malformed: {'; '.join(why)}")
            n += 1
        elif _cached(r, sha):
            answer(path, r, {}, {}, sha, log=log)
            n += 1
        else:
            ready.append((path, r, prefetch(r, sha)))
    decoded = {}
    if ready and not LJ.render_wants_gpu0():
        try:
            with gpu0.lease(OWNER, wait_s=0):
                if LJ.render_wants_gpu0():                       # it asked while the lease was being taken
                    return n
                try:
                    for path, r, _ in ready:
                        d = decode(r, sha, log=log)
                        if d is None:                            # a render asked: the rest stay pending
                            break
                        decoded[path] = d
                finally:
                    gpu0.release_all()                           # GPU0 left as found before the lease goes
        except gpu0.LeaseBusy as e:
            log(f"  GPU0 lease busy ({e})")
    for path, r, dl in ready:
        if path in decoded:
            answer(path, r, dl, decoded[path], sha, log=log)
            n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=("serve", "once"))
    ap.add_argument("--sleep", type=float, default=5.0)
    a = ap.parse_args(argv)
    for d in ("requests", "results", "work"):
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)

    def log(m):
        print(f"{time.strftime('%H:%M:%S')} {m}", flush=True)
    log(f"lock pre-check: decoder_sha {decoder_sha()[:12]}, root {ROOT}")
    while True:
        n = serve_once(log=log)
        if a.mode == "once":
            return 0
        if not n:
            time.sleep(a.sleep)


if __name__ == "__main__":
    sys.exit(main())
