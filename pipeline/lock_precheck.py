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
  An identical span, window and request fields (KEY: role, approved text, trimmed fields) under the same DECODER_SHA and
  RULES is answered from its last non-error entry ("reused": true; no decode, no second-recogniser spend). Run ONE
  serving process: a result file is appended read-then-replace.
- RULING 72 (orchestrator 2026-11-13 '15:45'), LOCK AS SPOKEN ON EVERY SPAN: once ruling 17's lock stands, the second
  recogniser's reading of the lock's own words (adjudicate_lock's window, the neighbouring sentence's spill at the
  edges left out) is compared with the lock. Repeats and dropped words that both Whisper passes smooth over are what G18
  then finds after a 27-minute render.
  - No difference: the outcome stands.
  - Every difference the speaker's own immediate repetition or function words (ruling 67's class, the builder's
    pipeline/attest.py carry_class, copied): outcome "adopt_spoken". "spoken_text" is the text to seal. It has been put
    through the render's own validate_range + segment_lock (the render's ruling 17 adopts it), and "lock" is that lock.
  - Anything else: "hold", before the seal.
  ONE paid reading per acquisition window, cached in its work dir; entries carry "as_spoken" (the differences) and
  "rules" (RULES).
- The request moves to requests/done/ when answered, to requests/failed/ (with "why") when malformed. A request in the
  builder's own directory (EXTRA; the builder may not write under this tree) is READ ONLY there: never moved or
  written. It is answered once per name and content (a marker in answered/), and its copy is kept in done/ or failed/.
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
KEY = ("role", "approved_text", "trimmed_leading", "untrimmed_start")   # the request fields an answer depends on
RULES = "ruling 17 + ruling 72"         # what an entry's verdict judged; an entry under other rules is never reused
EXTRA = os.environ.get("PP_LOCK_PRECHECK_EXTRA", "/home/ultron/worktrees/pp-selectid/tests/package/proof/lock_requests")
# RULING 67's class, as the builder's pipeline/attest.py defines it (FUNCTION_WORDS and carry_class, copied in
# behaviour): English closed-class words; NO negation, number or ordinal (those are law L-v 2's critical tokens).
FUNCTION_WORDS = frozenset("""
a an the this that these those that's this's there there's here here's
i you he she it we they me him her us them my your his its our their mine yours hers ours theirs
myself yourself himself herself itself ourselves themselves one's
i'm you're he's she's it's we're they're i've you've we've they've i'll you'll he'll she'll it'll we'll they'll
i'd you'd he'd she'd we'd they'd
in on at to of for from with by about into onto upon over under up down out off through as like than via per
and or but so because if then when while though although whether
is are was were be been being am do does did have has had will would can could shall should may might must
what which who whom whose why how where
""".split())


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


def latest(video_id, start, end, sha=None, window=None, approved_text=None, **seg):
    """The newest entry for this span under this decoder code (default: the current), this acquisition window (default:
    the span alone, the video's only segment in its line-up), this approved text (None: a decode request) and every
    other KEY field given in seg (role, trimmed_leading, untrimmed_start), else None."""
    sha = sha or decoder_sha()
    want = [float(x) for x in (window or (start, end))]
    seg = dict(seg, approved_text=approved_text)
    es = [e for e in _entries(result_path(video_id, start, end, sha))
          if e["start"] == start and e["end"] == end and e["window"] == want and e.get("rules") == RULES
          and all(e.get(k) == seg[k] for k in KEY if k in seg)]
    return es[-1] if es else None


def _key(s):
    return {k: s.get(k) for k in KEY}


def _videos(r):
    return list(dict.fromkeys(s["video_id"] for s in r["segments"]))


def _cached(r, sha):
    """True when every segment of r has a non-error entry for its span, window and approved text (answered from it)."""
    for s in r["segments"]:
        e = latest(s["video_id"], s["start"], s["end"], sha, window(r["segments"], s["video_id"]), **_key(s))
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


def second_reading(a, wd):
    """The second recogniser's words on the acquired window: ONE paid call per acquisition, cached in its work dir and
    keyed by the source file's sha256. -> (words, the spend of a call made now; 0.0 when cached)."""
    p, sha = os.path.join(wd, "second_recogniser.json"), a["provenance"].get("source_file_sha256")
    if os.path.exists(p):
        with open(p) as f:
            c = json.load(f)
        if c.get("source_file_sha256") == sha:
            return c["words"], 0.0
    words, usd = pinned._second_recogniser_words(a["path"])
    with open(p + ".tmp", "w") as f:
        json.dump({"source_file_sha256": sha, "usd": usd, "words": words}, f)
    os.replace(p + ".tmp", p)
    return words, usd


def carry_class(r, p, op, texts):
    """RULING 67's class of one difference (the builder's attest.carry_class): -> "immediate repetition",
    "function word", or None. Each side's tokens must repeat the tokens right before or right after them on that side,
    or be all function words; no law L-v 2 critical token (pinned._lv2_critical) is ever in the class."""
    _tag, a, b, c, d = op
    if any(pinned._lv2_critical(t, texts) for t in r[a:b] + p[c:d]):
        return None

    def repeats(x, lo, hi):
        n = hi - lo
        return n > 0 and (x[max(lo - n, 0):lo] == x[lo:hi] or x[hi:hi + n] == x[lo:hi])
    sides = ((r, a, b), (p, c, d))
    if not all(repeats(x, lo, hi) or all(t in FUNCTION_WORDS for t in x[lo:hi]) for x, lo, hi in sides):
        return None
    return "immediate repetition" if any(repeats(*s) for s in sides) else "function word"


def _spill(L, S):
    """[lo, hi) of the reading's tokens S without the window's spill: tokens before the lock's first aligned token
    (after its last) belong to the neighbouring sentence unless they repeat the tokens right after (before) them, the
    speaker's own repeat at the sentence's edge."""
    from difflib import SequenceMatcher
    ops = SequenceMatcher(None, L, S, autojunk=False).get_opcodes()
    lo, hi = 0, len(S)
    if ops and ops[0][0] == "insert" and ops[0][1] == 0:
        d = ops[0][4]
        lo = next((d - n for n in range(d, 0, -1) if S[d - n:d] == S[d:d + n]), d)
    if ops and ops[-1][0] == "insert" and ops[-1][1] == len(L):
        c = ops[-1][3]
        hi = next((c + n for n in range(len(S) - c, 0, -1) if S[c:c + n] == S[c - n:c]), c)
    return lo, max(lo, hi)


def as_spoken(lock, words, sw):
    """RULING 72: the lock against the second recogniser's reading of its own words ([i0 start - 0.3, i1 end + 0.3],
    adjudicate_lock's window, the spill left out). -> (verdict "same" | "adopt" | "hold", differences, spoken text)."""
    import canon
    from difflib import SequenceMatcher
    t0, t1 = words[lock["i0"]]["start"] - 0.3, words[lock["i1"]]["end"] + 0.3
    sel = [w for w in sw if t0 <= (float(w["start"]) + float(w["end"])) / 2 <= t1]
    spans = canon.canon_spans([str(w["word"]) for w in sel])
    L, S = canon.canon_tokens(lock["text"]), [t for t, _, _ in spans]
    lo, hi = _spill(L, S)
    if lo >= hi:
        return "hold", [[lock["text"], ""]], ""
    S2 = S[lo:hi]
    spoken = " ".join(str(sel[i]["word"]).strip() for i in range(spans[lo][1], spans[hi - 1][2] + 1))
    ops = [o for o in SequenceMatcher(None, L, S2, autojunk=False).get_opcodes() if o[0] != "equal"]
    diffs = [[" ".join(L[a:b]), " ".join(S2[c:d])] for _, a, b, c, d in ops]
    if not ops:
        return "same", [], spoken
    ok = all(carry_class(L, S2, op, (lock["text"], spoken)) for op in ops)
    return ("adopt" if ok else "hold"), diffs, spoken


def _outcome(s, lock):
    if not s.get("approved_text"):
        return "decoded"
    return "adopted" if "adjudication" in lock else "two_readings" if "alternatives" in lock else "no_difference"


def answer(path, r, dl, dec, sha, dg=None, log=print):
    """After the lease: every segment's lock (pinned.segment_lock, with the second recogniser where ruling 17 calls
    it) appended to its result file; the request moved to done/."""
    import faster_whisper
    for s in r["segments"]:
        vid, (lo, hi) = s["video_id"], window(r["segments"], s["video_id"])
        prev = latest(vid, s["start"], s["end"], sha, (lo, hi), **_key(s))
        if prev is not None and prev["outcome"] != "error":
            entry = dict(prev, request_id=r["request_id"], reused=True,
                         at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        else:
            a, err, dsec = dec.get(vid, (None, "not decoded", 0.0))
            spent, lock, reason, t, spoken = [], None, err, time.time(), None
            wd = work_dir(vid, lo, hi, sha)

            def recognise(src):                                  # ONE paid reading per acquisition (cached), spend kept
                words, usd = second_reading(a, wd)
                spent.append(usd)
                return words, usd
            outcome = "error"
            if a is not None:
                try:
                    v = pinned.validate_range(s, a)
                    lock = pinned.segment_lock(s, a, v, recognise=recognise, log=log)
                    outcome, reason = _outcome(s, lock), None
                    verdict, diffs, text = as_spoken(lock, a["transcript"]["words"], recognise(a["path"])[0])
                    spoken = {"verdict": verdict, "differences": diffs, "text": text}      # ruling 72, every span
                    if verdict == "adopt":                       # the render's own ruling 17 must adopt the spoken text
                        s2 = dict(s, approved_text=text)
                        try:
                            lock = pinned.segment_lock(s2, a, pinned.validate_range(s2, a), recognise=recognise, log=log)
                            outcome = "adopt_spoken"
                        except pinned.PinError as e:
                            outcome, lock = "hold", None
                            reason = f"ruling 72: the spoken text {text!r} is not adopted by the render's ruling 17: {e}"
                    elif verdict == "hold":
                        reason = (f"ruling 72: the second recogniser reads the span differently beyond the speaker's own "
                                  f"repetitions and function words at {diffs} | lock: {lock['text']!r} | spoken: "
                                  f"{text!r}")
                        outcome, lock = "hold", None
                except pinned.PinError as e:                     # what the render's stage pinned would hold on
                    outcome, reason = "hold", str(e)
                except Exception as e:
                    reason = f"{type(e).__name__}: {str(e)[:300]}"
            entry = {"request_id": r["request_id"], "video_id": vid, "start": s["start"], "end": s["end"],
                     "role": s["role"], "window": [float(lo), float(hi)],
                     "offset": a["offset"] if a else None,
                     "source_file_sha256": a["provenance"].get("source_file_sha256") if a else None,
                     "transcript_sha256": lock["transcript_sha256"] if lock else None, "decoder_sha": sha,
                     "faster_whisper": faster_whisper.__version__, **{k: s.get(k) for k in KEY if k != "role"},
                     "outcome": outcome, "reason": reason,
                     "lock": {k: lock.get(k) for k in ("i0", "i1", "first_word", "last_word", "text", "sha256")}
                     if lock else None,
                     "adjudication": (lock.get("adjudication") or lock.get("alternatives")) if lock else None,
                     "as_spoken": spoken, "spoken_text": spoken["text"] if outcome == "adopt_spoken" else None,
                     "rules": RULES, "scribe_usd": round(sum(spent), 4), "reused": False,
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
    _close(path, r, dg)


def _own(path):
    return os.path.dirname(os.path.abspath(path)) == os.path.abspath(os.path.join(ROOT, "requests"))


def _marker(path, dg):
    return os.path.join(ROOT, "answered", f"{os.path.basename(path)}.{dg}")


def _close(path, r, dg, why=None):
    """Answered (why None) or malformed. An own request moves to done/ (to failed/, with why). A request in the
    builder's directory is never touched there: its copy goes to done/ or failed/ here, and a marker keyed by its name
    and the content that was read (dg) keeps it from being asked again until the builder changes it."""
    sub = os.path.join(ROOT, "requests", "failed" if why else "done")
    os.makedirs(sub, exist_ok=True)
    if _own(path):
        if why:
            with open(os.path.join(sub, os.path.basename(path)), "w") as f:
                json.dump({"request": r, "why": why}, f, indent=1)
            os.remove(path)
        else:
            os.replace(path, os.path.join(sub, os.path.basename(path)))
        return
    with open(os.path.join(sub, "extra." + os.path.basename(path)), "w") as f:
        json.dump({"request": r, "why": why, "from": path, "content_sha256_16": dg}, f, indent=1)
    os.makedirs(os.path.join(ROOT, "answered"), exist_ok=True)
    open(_marker(path, dg), "w").close()


def _digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def _load(path):
    """-> (request, problems, the read content's sha256[:16])."""
    with open(path, "rb") as f:
        raw = f.read()
    dg = hashlib.sha256(raw).hexdigest()[:16]
    try:
        r = json.loads(raw)
    except ValueError as e:
        return None, [f"not JSON: {e}"], dg
    return r, problems(r), dg


def pending():
    """Own requests, then the builder's (EXTRA) whose name and content have not been answered."""
    own = sorted(glob.glob(os.path.join(ROOT, "requests", "*.json")))
    extra = []
    for p in sorted(glob.glob(os.path.join(EXTRA, "*.json"))) if EXTRA else []:
        try:
            if not os.path.exists(_marker(p, _digest(p))):
                extra.append(p)
        except OSError:                          # renamed or removed while listed: the next pass sees it
            continue
    return own + extra


def serve_once(log=print):
    """Answer up to BATCH pending requests: downloads first, the decodes under ONE GPU0 lease, the locks after it.
    -> how many were answered (0: none pending, a render asked, the lease is held, or a GPU0 stop)."""
    import gpu0
    todo = pending()[:BATCH]
    if not todo or LJ.render_wants_gpu0():
        return 0
    sha, ready, n = decoder_sha(), [], 0
    for path in todo:
        r, why, dg = _load(path)
        if why:
            _close(path, r, dg, why)
            log(f"  {os.path.basename(path)}: malformed: {'; '.join(why)}")
            n += 1
        elif _cached(r, sha):
            answer(path, r, {}, {}, sha, dg, log=log)
            n += 1
        else:
            ready.append((path, r, prefetch(r, sha), dg))
    decoded = {}
    if ready and not LJ.render_wants_gpu0():
        try:
            with gpu0.lease(OWNER, wait_s=0):
                if LJ.render_wants_gpu0():                       # it asked while the lease was being taken
                    return n
                try:
                    for path, r, _, _ in ready:
                        d = decode(r, sha, log=log)
                        if d is None:                            # a render asked: the rest stay pending
                            break
                        decoded[path] = d
                finally:
                    gpu0.release_all()                           # GPU0 left as found before the lease goes
        except gpu0.Gpu0Stop as e:          # busy, a foreign user, out of memory: what was decoded is answered below,
            log(f"  GPU0 stop, the rest stay pending: {type(e).__name__}: {e}")   # the rest asked again (b64 c2)
    for path, r, dl, dg in ready:
        if path in decoded:
            answer(path, r, dl, decoded[path], sha, dg, log=log)
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
