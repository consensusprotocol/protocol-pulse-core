#!/usr/bin/env python3
"""pipeline/word_pass_worker.py: sentence-ready WINDOW word records for the top-ranked unused ledger moments, on GPU1,
continuously. Orchestrator 2026-11-12 '22:40' ruling 2 and '22:50' item 5; the contract agreed with pp-selectid.

One cycle:
1. The ledger's rows, ranked, through pp-ingest's own adapter (best_unused_moments, read-only, in its own interpreter
   from the pp-ingest worktree; its exclusions apply: delivered, opted out, hard flags, altcoin, a speaker change,
   re-uploads). A failing or refusing adapter stops the cycle: it is never read as an empty ledger.
2. The skip list: rows already in word_pass.jsonl, and videos that already have a sentence-ready full-video word
   record in the store (the builder reads those directly).
3. The pick: the top PER_CYCLE rows, at most PER_CHANNEL per channel, so the forty come from at least MIN_CHANNELS
   channels whenever the ledger has them.
4. Each video's audio is downloaded ONCE, outside any lease. Each moment's window [start - PAD_S, end + PAD_S] on the
   YouTube clock (clipped to the video) is cut from it by a decoding ffmpeg seek (sample-accurate).
5. Decoding runs in batches of BATCH under the GPU1 lease (law L-r; CUDA_VISIBLE_DEVICES=1). Each window gets the
   store's own word pass: the verbatim decode (transcript_store.WHISPER_MODEL, word timestamps) and the punctuation
   reference decode (punctuation.ensure with transcript_store.REFERENCE_MODEL, case=True). The models are unloaded
   and the lease is left after every batch, so the watchdog, the stage broadcast and the site's fallback get turns.
6. The record is written once, as STORE/transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json. Its words are on
   the YouTube clock, with window = {start_s, end_s, clock: "youtube", offset_s}, and words_sha256 covers [word,
   start, end]: the segments sha does not. A row goes to STORE/moments/word_pass.jsonl:
   {moment_id, video_id, window_record, record_sha256, sentence_ready, window, at}. sentence_ready is false when a
   stretch is still unpunctuated. A failed moment also gets a row, with its error, and is not retried in a loop.
7. The cycle's report goes to STORE/moments/word_pass_cycles.jsonl: minutes, the GPU1 peak MiB, counts, the channels,
   and the age of the newest sentence-ready moment.
Usage: CUDA_VISIBLE_DEVICES=1 python3 pipeline/word_pass_worker.py [--once] [--limit N] [--sleep S]"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import transcript_store as ts  # noqa: E402

INGEST_ROOT = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest")
STORE = ts.STORE_DIR
ROWS_FILE = os.path.join(STORE, "moments", "word_pass.jsonl")
CYCLES_FILE = os.path.join(STORE, "moments", "word_pass_cycles.jsonl")
PER_CYCLE, MIN_CHANNELS, PAD_S, BATCH, HORIZON_H = 120, 6, 45.0, 16, 72   # order '02:46': bigger cycles
FRESH_H, DAY_H = 10, 24   # orchestrators '01:55' / '02:46': the last 10 h first, then the last 24 h, then older
FETCH_WORKERS = 4         # order '02:46': audio fetched in parallel, ahead of the GPU step
PER_CHANNEL = math.ceil(PER_CYCLE / MIN_CHANNELS)
OWNER = "word-pass worker (integrator, GPU1)"
LEASE_WAIT_S = 1800

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


def log(msg):
    print(f"{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def ledger_rows(now, ingest_root=INGEST_ROOT, timeout=300):
    """(rows best first, report) from pp-ingest's adapter in its own interpreter; RuntimeError when it fails or refuses."""
    args = {"path": os.path.join(ingest_root, "data", "editorial", "moments", "moment_ledger.jsonl"),
            "since": (now - dt.timedelta(hours=HORIZON_H)).isoformat(), "now": now.isoformat(), "delivered": [],
            "store_root": os.path.join(ingest_root, "data", "editorial"), "horizon_h": HORIZON_H}
    try:
        env = {k: v for k, v in os.environ.items() if k != "PP_EDITORIAL_STORE"}   # the adapter binds its OWN store
        p = subprocess.run([sys.executable, "-c", _ROWS, ingest_root], input=json.dumps(args), capture_output=True,
                           text=True, cwd=ingest_root, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"the ledger adapter did not answer in {timeout} s") from None
    if p.returncode != 0:
        raise RuntimeError(f"the ledger adapter failed: {p.stderr.strip()[-400:]}")
    try:
        out = json.loads(p.stdout)
        rows, report = out["rows"], out["report"] or {}
        if not isinstance(rows, list) or not isinstance(report, dict):
            raise TypeError("rows / report of the wrong type")
    except (ValueError, KeyError, TypeError) as e:
        raise RuntimeError(f"the ledger adapter's answer cannot be read ({type(e).__name__}: {e})") from None
    if report.get("contract"):
        raise RuntimeError(f"the ledger adapter refused: {report['contract']}")
    return rows, report


def passed_ids(rows_file=None):
    """moment_ids that already have a row (ready, not ready or failed): never worked again by this worker."""
    rows_file, done = rows_file or ROWS_FILE, set()          # resolved at call time, never bound at import
    if os.path.exists(rows_file):
        with open(rows_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    done.add(json.loads(line)["moment_id"])
    return done


def has_full_record(video_id):
    """True when the store already holds a sentence-ready full-video word record for the video."""
    try:
        return any(r.get("transcript_method", "").startswith("whisper_words") and ts.sentence_ready(r)
                   for r in ts.transcript_records(video_id))
    except Exception:
        return False


def is_fresh(row, now, hours=FRESH_H):
    """published_at read exactly as the ledger's own _aware reads it ('Z' = UTC; a time without an offset is not
    measured, so never fresh: the adapter drops such rows anyway), inside [now - hours, now]."""
    try:
        pub = dt.datetime.fromisoformat(str(row.get("published_at")).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return pub.tzinfo is not None and now - dt.timedelta(hours=hours) <= pub <= now


def pick(rows, done, full=None, per_cycle=PER_CYCLE, per_channel=PER_CHANNEL, now=None):
    """The rows to work, up to per_cycle, never one that is done or whose video has a full record. Orders '01:55' /
    '02:46': the last FRESH_H hours, then the last DAY_H hours, then older. Each tier is filled in the adapter's own
    rank order (score):
    - for the 10 h and 24 h tiers, first at most per_channel per channel, then the rest of the tier uncapped, so a
      capped channel's newer rows still come before any older row;
    - older rows are capped, the per-channel counts carrying on."""
    now = now or dt.datetime.now(dt.timezone.utc)
    full, out, per, full_cache, taken = full or has_full_record, [], {}, {}, set()

    def take(seq, cap):
        for r in seq:
            if len(out) >= per_cycle:
                return
            if r["moment_id"] in done or r["moment_id"] in taken:
                continue
            v = r["video_id"]
            if v not in full_cache:
                full_cache[v] = full(v)
            if full_cache[v] or (cap and per.get(r["channel_id"], 0) >= per_channel):
                continue
            per[r["channel_id"]] = per.get(r["channel_id"], 0) + 1
            taken.add(r["moment_id"])
            out.append(r)

    t10 = [r for r in rows if is_fresh(r, now, FRESH_H)]
    t24 = [r for r in rows if not is_fresh(r, now, FRESH_H) and is_fresh(r, now, DAY_H)]
    take(t10, True)
    take(t10, False)
    take(t24, True)                                   # order '02:46': then the last 24 h, the same two passes
    take(t24, False)
    take([r for r in rows if not is_fresh(r, now, DAY_H)], True)
    return out, len(per)

def window(row, duration=None):
    w0 = max(0.0, float(row["start"]) - PAD_S)
    w1 = float(row["end"]) + PAD_S
    if duration:
        w1 = min(w1, float(duration))
    if w1 <= w0:
        raise ValueError(f"empty window {w0}-{w1}")
    return round(w0, 3), round(w1, 3)


def cut_wav(audio, w0, w1, out):
    """[w0, w1] of `audio` as 16 kHz mono WAV, seeking by decoding (an input -ss with transcoding is sample-accurate)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{w0:.3f}", "-to", f"{w1:.3f}", "-i", audio,
                        "-ac", "1", "-ar", "16000", out], capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(f"window cut failed: {r.stderr.strip()[-200:]}")
    return out


def shift(words, off):
    return [dict(w, start=round(w["start"] + off, 3), end=round(w["end"] + off, 3)) for w in words]


def words_sha256(words):
    return hashlib.sha256(json.dumps([[w["word"], w["start"], w["end"]] for w in words],
                                     ensure_ascii=False).encode()).hexdigest()


def decode_verbatim(wav):
    """The store's verbatim word decode of one window (WHISPER_MODEL, word timestamps), window clock."""
    it, _ = ts._whisper().transcribe(wav, language="en", batch_size=ts.WHISPER_BATCH, word_timestamps=True)
    words = [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
             for s in it for w in (s.words or [])]
    if not words:
        raise ts.AcquisitionError("no words in the window")
    return words


def decode_punct(words, wav):
    """The punctuation reference (REFERENCE_MODEL, case=True) when the verbatim words need it; else none."""
    import punctuation
    if not punctuation.needs_restoration(words):
        return words, None
    out = punctuation.ensure({"words": words}, wav, ts._reference(),
                             model_name=ts.whisper_model_id().replace(ts.WHISPER_MODEL, ts.REFERENCE_MODEL)
                             + " word_timestamps", settings={"batch_size": ts.WHISPER_BATCH}, case=True)
    return out["words"], out.get("punctuation")


def decode_batch(wavs):
    """Order '02:46': a batch's verbatim decodes all run on ONE load of WHISPER_MODEL, then the punctuation reference
    runs on ONE load of REFERENCE_MODEL. Before, every window swapped the two models (two loads per moment). Returns,
    per wav, (verbatim, words, punctuation) or the exception."""
    first = []
    for w in wavs:
        try:
            first.append(decode_verbatim(w))
        except Exception as e:
            first.append(e)
    out = []
    for w, v in zip(wavs, first):
        if isinstance(v, Exception):
            out.append(v)
            continue
        try:
            words, pun = decode_punct(v, w)
            out.append((v, words, pun))
        except Exception as e:
            out.append(e)
    return out


def make_record(meta, verbatim, words, pun, w0, w1, media_sha256):
    """The window record: words on the YouTube clock, sentence segments, the window, words_sha256."""
    yt, vb = shift(words, w0), shift(verbatim, w0)
    pun = dict(pun or {}, still_unpunctuated=bool((pun or {}).get("still_unpunctuated"))) if pun else \
        {"source": "none needed", "still_unpunctuated": False}
    return ts._make_record(meta, "whisper_words_punct",
                           ts.whisper_model_id() + " word_timestamps + punctuation reference (window)",
                           ts.sentences_from_words(yt), media_sha256=media_sha256,
                           extra={"words": yt, "verbatim_words": vb, "words_sha256": words_sha256(yt),
                                  "punctuation": pun, "window": {"start_s": w0, "end_s": w1, "clock": "youtube",
                                                                 "offset_s": w0}})


def record_path(video_id, w0, w1):
    rel = os.path.join("transcripts", video_id, "windows", f"{w0:.3f}-{w1:.3f}.whisper_words_punct.json")
    return rel, os.path.join(STORE, rel)


def write_record(rec, w0, w1):
    rel, path = record_path(rec["video_id"], w0, w1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts._write_once(path, rec)
    return rel, ts.sha256_file(path)


def append_row(row, rows_file=None):
    rows_file = rows_file or ROWS_FILE
    os.makedirs(os.path.dirname(rows_file), exist_ok=True)
    with open(rows_file, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def gpu1_used():
    try:
        out = subprocess.run(["nvidia-smi", "-i", "1", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.strip())
    except Exception:
        return None


def _fetch(vid, rows, tmp):
    """One video: its meta, its audio ONCE, every window cut. Runs in a fetch thread, never under a lease.
    -> (jobs, failures, seconds)."""
    t0, jobs, fails = time.time(), [], []
    try:
        meta = ts.ensure_meta(vid)
        audio = ts.download_audio(vid)
    except Exception as e:
        return [], [(r, f"acquisition: {type(e).__name__}: {e}") for r in rows], time.time() - t0
    try:
        media_sha = ts.sha256_file(audio)
        for r in rows:
            try:
                w0, w1 = window(r, meta.get("duration"))
                jobs.append((r, meta, media_sha, w0, w1, cut_wav(audio, w0, w1, os.path.join(tmp, f"{r['moment_id']}.wav"))))
            except Exception as e:
                fails.append((r, f"window: {type(e).__name__}: {e}"))
    finally:
        os.unlink(audio)
    return jobs, fails, time.time() - t0


def cycle(now=None, limit=PER_CYCLE):
    import gpu0
    from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
    t0, now = time.time(), now or dt.datetime.now(dt.timezone.utc)
    rows, rep = ledger_rows(now)
    picks, nch = pick(rows, passed_ids(), per_cycle=limit, now=now)
    fresh = [r for r in rows if is_fresh(r, now)]
    day = [r for r in rows if is_fresh(r, now, DAY_H)]
    report = {"at": now.isoformat(), "ledger_rows": len(rows), "ledger_excluded": rep.get("excluded"),
              "fresh_h": FRESH_H, "fresh_rows": len(fresh), "fresh_picked": sum(is_fresh(r, now) for r in picks),
              "fresh_channels": len({r["channel_id"] for r in fresh}), "day_rows": len(day),
              "day_picked": sum(is_fresh(r, now, DAY_H) for r in picks),
              "picked": len(picks), "channels": nch, "written": 0, "sentence_ready": 0, "failed": 0, "peak_gpu1_mib": 0,
              "newest_ready_published_at": None, "_ready_channels": set(),
              "fetch_s": 0.0, "lease_wait_s": 0.0, "foreign_wait_s": 0.0, "gpu_s": 0.0, "batches": 0}
    # fetch_s: the summed time of every fetch thread (downloads and cuts, overlapping the GPU); lease_wait_s: waiting
    # for the GPU1 lease that another caller holds; gpu_s: the time HOLDING the lease (decodes, model loads, record
    # writes), which contains foreign_wait_s (gpu0's wait-out of a foreign GPU1 user, from gpu0.events)
    log(f"cycle: {len(rows)} ledger rows ({len(fresh)} in the last {FRESH_H} h, {len(day)} in the last {DAY_H} h), "
        f"{len(picks)} picked ({report['fresh_picked']} from the last {FRESH_H} h, {report['day_picked']} from the "
        f"last {DAY_H} h) from {nch} channels")
    tmp = tempfile.mkdtemp(prefix="word_pass_")

    def gpu_batch(batch):
        tw = time.time()
        with gpu0.lease(OWNER, wait_s=LEASE_WAIT_S):
            tg, ev0 = time.time(), len(gpu0.events())
            report["lease_wait_s"] += tg - tw
            try:
                todo = [j for j in batch if not os.path.exists(record_path(j[0]["video_id"], j[3], j[4])[1])]
                res = dict(zip((j[0]["moment_id"] for j in todo), decode_batch([j[5] for j in todo])))
                for j in batch:
                    _one(*j, report, res.get(j[0]["moment_id"]))
                report["peak_gpu1_mib"] = max(report["peak_gpu1_mib"], gpu1_used() or 0)
            finally:
                ts.release_whisper()
                report["gpu_s"] += time.time() - tg
                report["foreign_wait_s"] += sum(e.get("waited_s", 0) for e in gpu0.events()[ev0:]
                                                if e.get("key") == "foreign_wait")
                report["batches"] += 1
    try:
        with ThreadPoolExecutor(FETCH_WORKERS) as ex:                     # order '02:46': fetched ahead, in parallel
            of = {}                                                       # future -> its video's rows
            for v in dict.fromkeys(r["video_id"] for r in picks):
                mine = [r for r in picks if r["video_id"] == v]
                of[ex.submit(_fetch, v, mine, tmp)] = mine
            pending, ready = set(of), []
            while pending or ready:
                for f in [f for f in pending if f.done()]:
                    pending.discard(f)
                    try:
                        jobs, fails, secs = f.result()
                    except Exception as e:                                # batch 55 C1: a fetch that dies still
                        jobs, fails, secs = [], [(r, f"fetch: {type(e).__name__}: {e}") for r in of[f]], 0.0   # rows
                    report["fetch_s"] += secs
                    ready += jobs
                    for r, why in fails:
                        _fail(r, report, why)
                if len(ready) >= BATCH or (ready and not pending):
                    gpu_batch(ready[:BATCH])                              # the lease per batch, left after it
                    ready = ready[BATCH:]
                elif pending:
                    wait(pending, timeout=5, return_when=FIRST_COMPLETED)
    finally:
        for f in os.listdir(tmp):
            os.unlink(os.path.join(tmp, f))
        os.rmdir(tmp)
    report["minutes"] = round((time.time() - t0) / 60, 2)
    for k in ("fetch_s", "lease_wait_s", "foreign_wait_s", "gpu_s"):
        report[k] = round(report[k], 1)
    report["channels_ready"] = len(report.pop("_ready_channels"))   # channels with a sentence-ready record this cycle
    append_row(report, CYCLES_FILE)
    log(f"cycle done: {json.dumps(report)}")
    return report


def _one(r, meta, media_sha, w0, w1, wav, report, decoded=None):
    try:
        rel, path = record_path(r["video_id"], w0, w1)
        if os.path.exists(path):                     # written before a crash, its row never appended: reuse it, never
            with open(path) as f:                    # decode twice (and write-once never overwrites; batch 51 C2 glm)
                rec = json.load(f)
            sha, reused = ts.sha256_file(path), True
        else:
            if decoded is None or isinstance(decoded, Exception):
                raise decoded or RuntimeError("no decode result for this window")
            verbatim, words, pun = decoded
            rec = make_record(meta, verbatim, words, pun, w0, w1, media_sha)
            (rel, sha), reused = write_record(rec, w0, w1), False
        ready = not rec["punctuation"].get("still_unpunctuated")
        append_row({"moment_id": r["moment_id"], "video_id": r["video_id"], "window_record": rel, "record_sha256": sha,
                    "sentence_ready": ready, "window": [w0, w1], "at": ts.now_iso(), **({"reused": True} if reused else {})})
        report["written"] += 1
        report["sentence_ready"] += int(ready)
        if ready:
            report["_ready_channels"].add(r["channel_id"])
        if ready and (report["newest_ready_published_at"] or "") < (r.get("published_at") or ""):
            report["newest_ready_published_at"] = r.get("published_at")
    except Exception as e:
        _fail(r, report, f"word pass: {type(e).__name__}: {e}")


def _fail(r, report, why):
    report["failed"] += 1
    log(f"  {r['moment_id']} ({r['video_id']}): {why}")
    append_row({"moment_id": r["moment_id"], "video_id": r["video_id"], "window_record": None, "record_sha256": None,
                "sentence_ready": False, "error": why[:300], "at": ts.now_iso()})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--limit", type=int, default=PER_CYCLE)
    ap.add_argument("--sleep", type=float, default=900.0, help="seconds between cycles when a cycle picks nothing")
    a = ap.parse_args(argv)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "1":
        sys.exit("the word-pass worker runs on GPU1: CUDA_VISIBLE_DEVICES=1 (law L-r)")
    while True:
        try:
            rep = cycle(limit=a.limit)
        except RuntimeError as e:                    # the ledger adapter failed or refused: never an empty ledger
            log(f"cycle stopped: {e}")
            rep = {"picked": 0}
        if a.once:
            return 0
        if not rep.get("picked"):
            time.sleep(a.sleep)


if __name__ == "__main__":
    sys.exit(main())
