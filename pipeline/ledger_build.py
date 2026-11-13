#!/usr/bin/env python3
"""pipeline/ledger_build.py — ORCHESTRATOR 22:40 ruling 2: the medley built from the INGEST LEDGER, the path to the first
FRESH medley. Read-only on the ledger and on the stores; no GPU; no model call here (package.build makes those).

- rows(): pp-ingest's own adapter, pipeline.ingest.ledger.best_unused_moments, with its exclusions applied: delivered,
  opted out, hard flags, altcoin or not about Bitcoin, a speaker change, re-uploads. It runs read-only in its own
  interpreter, from the pp-ingest worktree, until the integrator merges it.
- READY: a row is packageable only on a sentence-ready WORD record (law L-e). Today that is the store's full-video slot
  (transcripts/<vid>/transcript.whisper_words_punct.json, then transcript.whisper_words.json: WORD_RECORDS, in that
  order). Its segments sha is checked, and its words must spell those segments exactly (words_off_segments).
- WINDOW records: a video with no such full-video record may have WINDOW records from the integrator's word-pass
  worker (pipeline/word_pass_worker.py on branch word-pass, 514dd704).
  - Each is transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json: about +-45 s of words around one ledger
    moment, on the YouTube clock, with words_sha256.
  - Each is listed in moments/word_pass.jsonl as {moment_id, video_id, window_record, record_sha256, sentence_ready,
    window, at}.
  - word_pass_index() reads that list. window_source() checks every claim before use: the file's sha256 is the row's
    record_sha256, the segments sha, words_sha256, the words spell the segments, the YouTube clock, nothing still
    unpunctuated, and the ledger row's span inside the window.
  - One window per video: the best-ranked row whose window record passes every check (a row whose own record fails
    is passed over with why). The video's other rows re-anchor in it, or are counted out.
  - L-s context comes from the caption record the ledger mined the moment from (caption_source(): its segments sha
    is the row's transcript_sha256), cut by time (context_integrity.caption_parts). Without one, the context is
    unavailable and L-s fails closed.
- RE-ANCHOR: sentence_law.anchor, the sentence law's own text locator, finds the row's TEXT in the word record. The
  row's caption-clock times only narrow the search. The span then snaps to that record's WHOLE sentences when at most
  SNAP_WORDS words lie outside the anchored text at either edge; otherwise the row is dropped, and why is recorded.
  The moment's text becomes the word record's own words, verbatim, the words the render locks on.
- RECORD: the miner's own moments.judge() and moments.record(): eligibility on word timing (on_screen_ok). The ledger
  row's scores, risks, topics, reason and mining provenance are kept (mined.ledger_moment_id).
-> build_inputs(...) = (moments, sources, report).
"""
import hashlib
import json
import os
import sys

import eligibility as E
import moments as M
import select_by_id as S
import sentence_law as SL
import transcript_store as ts

SNAP_WORDS = 3            # words of a word-record sentence the anchored text may leave out at either edge
SNAP_GUARD = __import__("re").compile(r"^(not|no|never|none|nobody|nothing|neither|nor|cannot|can't|won't|don't|"
                                      r"hardly|scarcely|barely|rarely|seldom|"
                                      r"doesn't|didn't|isn't|aren't|wasn't|weren't|shouldn't|wouldn't|couldn't|"
                                      r"\w+n't)$|\d", __import__("re").I)
                          # a word the snap would ADD may not be a negation or carry a digit: it could flip or add a
                          # claim the ledger's scores and risks never saw (audit 2315 C1: grok P1, glm P1-1; the
                          # near-negations "hardly" ... "seldom": qwen C3)
APOSTROPHES = {"\u2019": "'", "\u2018": "'", "\u02bc": "'"}   # a typographic apostrophe is read as ' by the guard
SEARCH_PAD_S = 30.0       # the row's caption times narrow the anchor's search to [start - pad, end + pad]. Captions
                          # and word records share the full-video clock, and a caption cue starts or ends a few
                          # seconds off the words; the window only keeps a phrase said again elsewhere in the video
                          # from anchoring. A row the window misses is a counted, named drop.
INGEST_ROOT = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest")
MAIN = os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse")
STORE = os.path.join(MAIN, "data", "editorial")
WORD_RECORDS = ("transcript.whisper_words_punct.json", "transcript.whisper_words.json")
WORD_PASS = os.path.join(STORE, "moments", "word_pass.jsonl")     # the word-pass worker's rows (the integrator's)
WINDOW_TOL_S = 0.01      # the ledger row's span must lie inside its window record's [start_s, end_s] (the worker cut
                         # the window around that very span; this is only the 3-decimal rounding)
                          # the store's two word-record slots (transcript_store._store: transcript.<method>.json), read
                          # in this order: a total order, never the file system's (glm C3 P1-2)


_ROWS = """
import json, sys
from datetime import datetime
sys.path.insert(0, sys.argv[1])
from pipeline.ingest import ledger as IL
a = json.loads(sys.stdin.read())
rows, rep = IL.best_unused_moments(a["path"], datetime.fromisoformat(a["since"]), datetime.fromisoformat(a["now"]),
                                   a["delivered"], store_root=a["store_root"], horizon_h=a["horizon_h"])
sys.stdout.write(json.dumps({"rows": rows, "report": rep}, default=str))
"""


def rows(since, now, delivered_ids=(), ingest_root=INGEST_ROOT, horizon_h=72, timeout=300):
    """pp-ingest's adapter, best_unused_moments, run read-only in its OWN interpreter, from its worktree until the
    integrator merges it. Its store guard refuses a process in which another transcript_store was imported first, so
    the two never share modules. -> (rows, report). Raises RuntimeError when the adapter FAILS or REFUSES (fail
    closed: a failure is never read as an empty ledger). An empty successful read is a real result: no row passes the
    ledger's own exclusions, and the report's counts say why."""
    import subprocess
    args = {"path": os.path.join(ingest_root, "data", "editorial", "moments", "moment_ledger.jsonl"),
            "since": since.isoformat(), "now": now.isoformat(), "delivered": list(delivered_ids),
            "store_root": os.path.join(ingest_root, "data", "editorial"), "horizon_h": horizon_h}
    env = dict(os.environ, PP_SELECTID_PIPELINE=os.path.dirname(os.path.abspath(__file__)))
    try:
        p = subprocess.run([sys.executable, "-c", _ROWS, ingest_root], input=json.dumps(args), capture_output=True,
                           text=True, cwd=ingest_root, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:                   # a failure like any other: RuntimeError (glm C2 N-5)
        raise RuntimeError(f"the ledger adapter did not answer in {timeout} s") from None
    if p.returncode != 0:
        raise RuntimeError(f"the ledger adapter failed: {p.stderr.strip()[-400:]}")
    try:
        out = json.loads(p.stdout)
        got, report = out["rows"], out["report"] or {}
        if not isinstance(got, list) or not isinstance(report, dict):
            raise TypeError("'rows' is not a list or 'report' is not an object")
    except (ValueError, KeyError, TypeError) as e:
        raise RuntimeError(f"the ledger adapter's answer cannot be read ({type(e).__name__}: {str(e)[:160]})") from None
    if report.get("contract"):
        raise RuntimeError(f"the ledger adapter refused: {report['contract']}")
    return got, report


def words_off_segments(rec, tol=0.001):
    """None when the record's word list spells its segments exactly, in order (whitespace aside), and every segment
    starts at its first word's start and ends at its last word's end (to the ms the segments are rounded to); else
    why. segments_sha256 covers the segments only, and the clip is cut from the WORDS (S.tokens_from_record reads
    rec["words"]), so this is what ties those words to the sha (glm C3 (a)). The store writes its segments from the
    words: all 66 word records (35,697 segments) agree to the ms (measured by 23:44 ET Nov 12). Word times inside a
    segment stay outside the sha: that is the store's to close (words in the hash), flagged to the integrator."""
    raw, segs = rec.get("words"), rec.get("segments")
    if not isinstance(raw, list) or not all(isinstance(w, dict) for w in raw):
        return "its words are not a list of objects"          # a corrupt record is a why, never a crash (qwen C4)
    if not isinstance(segs, list) or not all(isinstance(sg, dict) for sg in segs):
        return "its segments are not a list of objects"
    ws = [w for w in raw if str(w.get("word") or "").strip()]
    if not ws:
        return "no words"
    k = 0
    for i, sg in enumerate(segs):
        need, got, first = "".join(str(sg.get("text") or "").split()), "", k
        if not need:
            return f"segment {i} is empty"
        while k < len(ws) and len(got) < len(need):
            got += "".join(str(ws[k]["word"]).split())
            k += 1
        if got != need:
            return f"segment {i}: the words spell {got[:40]!r}, the segment {need[:40]!r}"
        try:
            if (abs(float(ws[first]["start"]) - float(sg["start"])) > tol or
                    abs(float(ws[k - 1]["end"]) - float(sg["end"])) > tol):
                return f"segment {i}: its times are not its words' times"
        except (KeyError, TypeError, ValueError):
            return f"segment {i}: a word or the segment has no readable time"
    if k != len(ws):
        return f"{len(ws) - k} word(s) after the last segment"
    return None


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def word_pass_index(path=WORD_PASS):
    """The word-pass worker's rows -> ({moment_id: the LAST row of that moment, when it is sentence_ready with a
    window_record and a record_sha256}, report). A failed moment's row has neither, and the worker never retries it.
    No file yet = no window record yet: ({}, report). A file that exists but cannot be read raises: it is never read
    as an empty word pass (law L-j)."""
    rep = {"rows": 0, "unreadable": 0, "ready": 0, "not_ready": 0, "failed": 0, "file": path}
    try:
        f = open(path)
    except FileNotFoundError:
        return {}, dict(rep, file="none yet: " + path)
    last = {}
    with f:
        for line in f:
            if not line.strip():
                continue
            rep["rows"] += 1
            try:
                r = json.loads(line)
            except ValueError:
                rep["unreadable"] += 1
                continue
            if not isinstance(r, dict) or not isinstance(r.get("moment_id"), str):
                rep["unreadable"] += 1
                continue
            last[r["moment_id"]] = r
    out = {}
    for mid, r in last.items():
        if r.get("error") or r.get("window_record") is None:
            rep["failed"] += 1
        elif r.get("sentence_ready") is not True:
            rep["not_ready"] += 1
        elif isinstance(r.get("window_record"), str) and isinstance(r.get("record_sha256"), str):
            out[mid] = r
            rep["ready"] += 1
        else:
            rep["unreadable"] += 1
    return out, rep


def window_source(row, wp, ctx, store=STORE):
    """The moment's sentence-ready WINDOW record (its word_pass.jsonl row `wp`) as an eligibility Source, every claim
    checked -> (Source, path, None) or (None, None, why). The Source carries .window = {start_s, end_s, record,
    words_sha256, record_sha256}; file_head only when the window starts at the media's first second."""
    vid, rel = row["video_id"], wp["window_record"]
    name = os.path.basename(rel)
    base = os.path.join(os.path.realpath(store), "transcripts", vid, "windows")
    path = os.path.realpath(os.path.join(store, rel))
    if wp.get("video_id") != vid or os.path.dirname(path) != base:
        return None, None, f"{name}: not this video's window record (transcripts/{vid}/windows/)"
    try:
        with open(path, "rb") as f:
            raw = f.read()
        rec = json.loads(raw)
    except (OSError, ValueError):
        return None, None, f"{name}: cannot be read"
    if hashlib.sha256(raw).hexdigest() != wp["record_sha256"]:
        return None, None, f"{name}: the file is not the one word_pass.jsonl names (record_sha256)"
    if not isinstance(rec, dict) or rec.get("video_id") != vid or rec.get("transcript_method") != "whisper_words_punct":
        return None, None, f"{name}: not a punctuated word record of this video"
    try:
        sha = ts.segments_sha256(rec.get("segments") or [])
        wsha = hashlib.sha256(json.dumps([[w["word"], w["start"], w["end"]] for w in rec["words"]],
                                         ensure_ascii=False).encode()).hexdigest()
    except (KeyError, TypeError, ValueError, AttributeError):
        return None, None, f"{name}: its segments or words cannot be hashed"
    if rec.get("transcript_sha256") != sha:
        return None, None, f"{name}: its segments do not match its transcript_sha256"
    if rec.get("words_sha256") != wsha:
        return None, None, f"{name}: its words do not match its words_sha256"
    off = words_off_segments(rec)
    if off:
        return None, None, f"{name}: its words do not spell its sha-checked segments ({off})"
    win = rec.get("window") if isinstance(rec.get("window"), dict) else {}
    w0, w1 = _num(win.get("start_s")), _num(win.get("end_s"))
    if w0 is None or w1 is None or win.get("clock") != "youtube":
        return None, None, f"{name}: no window on the YouTube clock"
    if (rec.get("punctuation") or {}).get("still_unpunctuated") is not False:
        return None, None, f"{name}: a stretch is still unpunctuated (law L-e)"
    t0, t1 = _num(row.get("start")), _num(row.get("end"))
    if t0 is None or t1 is None or t0 < w0 - WINDOW_TOL_S or t1 > w1 + WINDOW_TOL_S:
        return None, None, f"{name}: the row's span {t0}-{t1} is not inside the window {w0}-{w1}"
    if rec.get("channel_id") and rec.get("channel_id") != row.get("channel_id"):
        return None, None, f"{name}: it names channel {rec.get('channel_id')}, the ledger row {row.get('channel_id')}"
    timing, toks = S.tokens_from_record(rec)
    reg = ctx.channel(row.get("channel_id")) or {}
    src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
                   row.get("published_at"), sha, "whisper_words_punct", toks, timing=timing,
                   title=row.get("title") or "", file_head=(w0 == 0.0), vod=True)
    if not E.sentence_ready(src):
        return None, None, f"{name}: not sentence-ready (law L-e)"
    src.window = {"start_s": w0, "end_s": w1, "record": rel, "words_sha256": wsha, "record_sha256": wp["record_sha256"]}
    return src, path, None


def caption_source(row, ctx, store=STORE):
    """The full-video record the ledger row was MINED from: the one whose segments sha is the row's transcript_sha256
    (the full-video slots transcripts/<vid>/transcript.*.json only; never a window). It is a window record's L-s
    context (the contract) -> (Source with .duration_s, file name) or (None, why). Two records matching is ambiguous:
    no context (audit 0123 C1, glm P0-1)."""
    vid, want = row["video_id"], row.get("transcript_sha256")
    d = os.path.join(store, "transcripts", vid)
    try:
        names = sorted(n for n in os.listdir(d) if n.startswith("transcript.") and n.endswith(".json"))
    except OSError:
        return None, "no transcript directory for the video"
    found, unreadable = [], 0
    for n in names:
        try:
            with open(os.path.join(d, n)) as f:
                rec = json.load(f)
            if not isinstance(rec, dict) or not want or rec.get("transcript_sha256") != want or \
                    ts.segments_sha256(rec.get("segments") or []) != want:
                continue
            found.append((n, rec, S.tokens_from_record(rec)))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            unreadable += 1
            continue
    if not found:
        return None, ("no record in the store matches the row's transcript_sha256" +
                      (f" ({unreadable} transcript file(s) could not be read)" if unreadable else ""))   # C2 glm N2
    if len(found) > 1:
        return None, f"{len(found)} records match the row's transcript_sha256 ({[n for n, _, _ in found]}): ambiguous"
    n, rec, (timing, toks) = found[0]
    reg = ctx.channel(row.get("channel_id")) or {}
    src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
                   row.get("published_at"), want, rec.get("transcript_method"), toks, timing=timing,
                   title=row.get("title") or "", file_head=True, vod=True)
    src.duration_s = _num(rec.get("duration"))          # the media's end, for the coverage check (caption_parts)
    return src, n


def word_source(row, ctx, store=STORE):
    """The video's sentence-ready word record from the store's full-video slot (punctuated first, its segments sha
    checked), as an eligibility Source with the row's identity -> (Source, path, passed_over), or (None, None,
    passed_over). passed_over names every record read and not used, in reading order, each with why ("<file>: <why>";
    "no word record in the store" when there is none). A Source that comes with a non-empty passed_over is a fallback
    from the punctuated record, and is visible as one (audit 2315 C2: all three reviewers).
    Identity: a record that names a channel other than the ledger row's is passed over (a measured contradiction). A
    record that names none (3 of the 23 records on ledger videos, older than the store's identity rule) keeps the
    ledger row's channel, which the adapter checks against the registry (glm C4 P2-1)."""
    vid = row["video_id"]
    paths = [p for p in (os.path.join(store, "transcripts", vid, n) for n in WORD_RECORDS) if os.path.exists(p)]
    if not paths:
        return None, None, ["no word record in the store"]
    reg = ctx.channel(row.get("channel_id")) or {}
    passed_over = []
    for p in paths:
        name = os.path.basename(p)
        try:
            with open(p) as f:
                rec = json.load(f)
        except (OSError, ValueError):
            passed_over.append(f"{name}: cannot be read")
            continue
        if not isinstance(rec, dict):
            passed_over.append(f"{name}: not a record (a JSON {type(rec).__name__})")    # qwen C4: never a crash
            continue
        try:
            sha = ts.segments_sha256(rec.get("segments") or [])
        except (KeyError, TypeError, ValueError, AttributeError):
            passed_over.append(f"{name}: its segments cannot be hashed")
            continue
        if rec.get("transcript_sha256") != sha:
            passed_over.append(f"{name}: its segments do not match its transcript_sha256")
            continue
        if rec.get("channel_id") and rec.get("channel_id") != row.get("channel_id"):
            passed_over.append(f"{name}: it names channel {rec.get('channel_id')}, the ledger row "
                               f"{row.get('channel_id')}")       # a measured contradiction (glm C4 P2-1)
            continue
        off = words_off_segments(rec)
        if off:
            passed_over.append(f"{name}: its words do not spell its sha-checked segments ({off})")
            continue
        timing, toks = S.tokens_from_record(rec)
        src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
                       row.get("published_at"), rec.get("transcript_sha256"), rec.get("transcript_method"), toks,
                       timing=timing, title=row.get("title") or "", file_head=True, vod=True)
        if E.sentence_ready(src):
            return src, p, passed_over
        passed_over.append(f"{name}: not sentence-ready (law L-e)")
    return None, None, passed_over


def reanchor(row, src):
    """The row's TEXT located in the word record and snapped to its whole sentences -> (E.Span, info) or (None, why)."""
    def num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None                                 # an unreadable time only widens the search (glm C1 P1-9)
    t0, t1 = num(row.get("start")), num(row.get("end"))
    hit = SL.anchor(src.tokens, row.get("text") or "",
                    t0=(t0 - SEARCH_PAD_S) if t0 is not None else None,
                    t1=(t1 + SEARCH_PAD_S) if t1 is not None else None)
    if hit is None:
        return None, (f"the row's text does not anchor in the word record (sentence_law.anchor"
                      + (f", searched {t0 - SEARCH_PAD_S:.0f}-{t1 + SEARCH_PAD_S:.0f} s)" if t0 is not None and
                         t1 is not None else ")"))
    i0, i1, ratio = hit
    k0 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i0 <= b), None)
    k1 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i1 <= b), None)
    if k0 is None or k1 is None:
        return None, "the anchored words fall outside the record's sentences"
    left, right = i0 - src.sentences[k0][0], src.sentences[k1][1] - i1
    if left > SNAP_WORDS or right > SNAP_WORDS:
        return None, (f"the anchored text is not whole sentences of the word record ({left} word(s) before it and "
                      f"{right} after it inside its edge sentences; at most {SNAP_WORDS})")
    added = ["".join(APOSTROPHES.get(c, c) for c in t["word"]).strip(".,!?;:\"'()\u201c\u201d\u2014\u2026")
             for t in list(src.tokens[src.sentences[k0][0]:i0]) + list(src.tokens[i1 + 1:src.sentences[k1][1] + 1])]
    # a typographic apostrophe reads as ' here (glm C2 N-3; none of the store's 66 word records holds one today)
    risky = [w for w in added if SNAP_GUARD.search(w)]
    if risky:
        return None, f"snapping to whole sentences would add {risky}: a negation or a number the ledger never judged"
    sp = E.Span(src, k0, k1)
    info = {"anchor_ratio": round(ratio, 3), "snapped_words": [left, right], "sentences": [k0, k1]}
    a, b = num(src.tokens[i0].get("start")), num(src.tokens[i1].get("end"))
    # the hit against the row's own caption times: a phrase said twice inside the window shows here (glm C3 P1-3);
    # when it cannot be measured, it says so (glm C4 P2-8)
    info["offset_s"] = ([round(a - t0, 2), round(b - t1, 2)] if None not in (t0, t1, a, b) else
                        "unmeasured: " + ("the row has no readable caption times" if None in (t0, t1) else
                                          "a hit word has no readable time"))
    return sp, info


def build_inputs(rows, ctx, store=STORE, log=print, word_pass=None):
    """Ledger rows -> (moments in the packager's form, {video_id: Source}, report). word_pass: word_pass_index()'s
    {moment_id: row} (None = no window records). Rows on a video with neither a sentence-ready full-video word record
    nor a sentence-ready window record, rows whose text does not re-anchor on whole sentences, and duplicates of one
    span are dropped, each counted with why."""
    word_pass = word_pass or {}
    report = {"rows": len(rows), "no_word_record": 0, "no_word_record_why": {}, "no_word_record_videos": {},
              "window_records": {}, "window_passed_over": {}, "no_caption_context": {},
              "fallbacks": {},
              "channel_conflict": {}, "not_anchored": {}, "malformed": {}, "duplicates": 0, "duplicates_of": {},
              "moments": 0, "videos": 0,
              "word_records": {}}
    def malformed(i, r, why):                     # counted under a key no other row can take (qwen C3, glm C3 P1-4)
        mid = r.get("moment_id") if isinstance(r, dict) else None
        report["malformed"][mid if isinstance(mid, str) and mid and mid not in report["malformed"] else f"row {i}"] = why

    by_vid = {}
    for i, r in enumerate(rows):
        if not (isinstance(r, dict) and all(isinstance(r.get(k), str) and r.get(k) for k in ("moment_id", "video_id"))):
            malformed(i, r, "no moment_id or video_id")
            continue
        by_vid.setdefault(r["video_id"], []).append((i, r))
    moments, sources, seen = [], {}, {}              # seen: (vid, k0, k1) -> the moment id that kept the span
    for vid, irs in by_vid.items():
        rs = [r for _, r in irs]
        channels = sorted({str(r.get("channel_id")) for r in rs})
        if len(channels) > 1:       # one uploader per video, checked, not assumed (audit 2315 C2: qwen P1, glm P1)
            report["channel_conflict"][vid] = {"rows": len(rs), "channel_ids": channels}
            continue
        src, path, passed_over = word_source(rs[0], ctx, store)
        if src is None:                         # the WINDOW path: the best-ranked row of this video with a
            wrow, why_w = None, []              # sentence-ready window record (rows arrive best first)
            for i, r in irs:
                wp = word_pass.get(r["moment_id"])
                if wp is None:
                    continue
                cand, cpath, why = window_source(r, wp, ctx, store)
                if cand is not None:
                    src, path, wrow = cand, cpath, r
                    break
                why_w.append(f"{r['moment_id']}: {why}")
            if why_w:
                report["window_passed_over"][vid] = why_w
            if src is None:
                why = "; ".join(passed_over + (["its window records were passed over"] if why_w else
                                               ["no sentence-ready window record"]))
                report["no_word_record"] += len(rs)
                report["no_word_record_why"][why] = report["no_word_record_why"].get(why, 0) + len(rs)
                report["no_word_record_videos"][vid] = {"rows": len(rs), "why": why}     # which videos (glm C3 P2-2)
                continue
            src.context_source, cwhy = caption_source(wrow, ctx, store)
            if src.context_source is None:
                src.context_source = None
                report["no_caption_context"][vid] = cwhy          # L-s fails closed for this video's clips
            report["window_records"][vid] = os.path.relpath(path, os.path.realpath(store))
        elif passed_over:
            report["fallbacks"][vid] = {"used": os.path.basename(path), "passed_over": passed_over}
        if getattr(src, "window", None) is None:
            report["word_records"][vid] = os.path.relpath(path, store)    # read; whether a moment came of it: moments
        for i, r in irs:
            sp, info = reanchor(r, src)
            if sp is None:
                report["not_anchored"][r["moment_id"]] = info
                continue
            if (vid, sp.k0, sp.k1) in seen:
                report["duplicates"] += 1
                report["duplicates_of"][r["moment_id"]] = seen[(vid, sp.k0, sp.k1)]       # named (glm C4 P2-5)
                continue
            try:
                m = {"scores": dict(r["scores"]), "names_person": r.get("names_person", False),
                     "risk": list(r.get("risk") or []), "topics": list(r.get("topics") or []),
                     "reason": r.get("reason") or ""}
                mined = dict(r.get("mined") or {}, ledger_moment_id=r["moment_id"], reanchored=info,
                             ledger_text=r.get("text"))
                if getattr(src, "window", None) is not None:      # provenance: the window record it was cut from
                    mined["window"] = dict(src.window, context_record=(getattr(src.context_source, "transcript_method",
                                                                                None)))
                rec = M.record(sp, m, ctx, M.judge(sp, ctx), mined)
                rec["rank_score"] = M.rank_score(rec)
            except (KeyError, TypeError, ValueError) as e:     # counted, never a crash (glm C1 P1-8)
                malformed(i, r, f"{type(e).__name__}: {str(e)[:120]}")
                continue
            seen[(vid, sp.k0, sp.k1)] = r["moment_id"]
            moments.append(rec)
            sources[vid] = src
    report["moments"], report["videos"] = len(moments), len(sources)
    log(f"  ledger rows {report['rows']}: {report['moments']} moments on {report['videos']} word records; "
        f"{report['no_word_record']} rows wait for a word record, {len(report['not_anchored'])} do not re-anchor, "
        f"{len(report['malformed'])} malformed, {report['duplicates']} duplicates; "
        f"{len(report['channel_conflict'])} video(s) name more than one channel, "
        f"{len(report['fallbacks'])} read from a fallback record; {len(report['window_records'])} window record(s) "
        f"used ({len(report['no_caption_context'])} without a caption record for L-s)")
    moments.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
    return moments, sources, report
