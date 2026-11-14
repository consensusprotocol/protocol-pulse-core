#!/usr/bin/env python3
"""pipeline/local_judge.py: the GPU0 LOCAL JUDGE (orchestrator 2026-11-13 '07:28' item 2; law L-aa TIME SAVERS ARE
AUTOMATIC; law L-x ULTRON FIRST).

WHAT: the pin-stage verdicts that today go to vendors (step A, the L-s context reading of each moment; the clips-alone
verdict; the angle step) asked of a model on Ultron's GPU0, with the vendor's own prompt, max_tokens and seed.

THE MODEL: gemma3:27b on the GPU0 Ollama (:11434), num_ctx 16384 (story_semantics.LocalLLM: temperature 0, JSON
format). Ultron holds four Ollama models: gemma3:27b (17 GB), qwen3-coder:30b (18 GB, a coding model, pinned to GPU1),
deepseek-coder-v2:16b (8.9 GB, a coding model, GPU1's) and llama3.1:70b (42 GB: does not fit a 24 GB card). gemma3:27b
is the strongest general instruction model that fits GPU0, it already holds a measured REQUIREMENT_MIB in gpu0.py
(20600 MiB at this context), and it is the model of the editorial gate and the clip scorer, so no new weights are
pulled.

USE, until the orchestrator rules otherwise: a PRE-FILTER only. It may reject cheaply and rank; a clip or line-up it
passes still gets the different-vendor verdict the laws require (L-s, L-x: never one model). It can save calls, never
lower the bar. It counts only after its replay (local_judge_compare.py) is reported.
RULING 87 (orchestrator 2026-11-13 '21:18', PLAN B): when Heimdall is down and only ONE outside family answers, step
A's second verdict is this model, asked through the judge SERVICE below (serve): one call per request, the caller's
exact prompt, max_tokens and seed; an error is no verdict.

GPU0 (law L-r): every call runs under the GPU0 lease, in batches of at most BATCH calls; each batch ends with
gpu0.release_all (the model unloaded, GPU0 left as found) and the lease released. A render always comes first: before
EVERY call the judge checks YIELD_FLAG; whoever launches a render touches it, waits for the lease to come free, starts
the render and removes the flag once the render holds the lease. A held lease (LeaseBusy) is waited out between
batches, never forced. Outputs are appended one JSON line per job, so a stopped replay resumes where it stopped.

Usage: CUDA_VISIBLE_DEVICES=0 python3 pipeline/local_judge.py replay [--since ISO] [--out PATH] | serve | once"""
import argparse
import glob
import hashlib
import json
import os
import sys
import time

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)

MODEL = "gemma3:27b"
YIELD_FLAG = os.environ.get("PP_GPU0_YIELD", "/tmp/pulse_gpu0.yield")
OWNER = "local judge (integrator, GPU0 pre-filter)"
BATCH = 8
REPLIES = "/home/ultron/worktrees/pp-selectid/tests/package/fixtures/replies"   # the builder's recorded exchanges
FAMILIES = (("clips_alone", "You watch a short video made ONLY of these clips"),       # the clips-alone verdict
            ("angle", "You are the editor of PBX MAX"),                                # the angle step
            ("step_a", "You read transcripts of Bitcoin videos. For each EXCERPT"))   # step A (L-s context)
SINCE = "2026-11-13T04:00"            # the first ledger_2026* build of the night (ledger_20261113_0405)


def family(prompt):
    head = " ".join(str(prompt).split())
    return next((k for k, w in FAMILIES if head.startswith(w)), None)


def prompt_id(prompt, max_tokens, seed):
    return hashlib.sha256(json.dumps([prompt, max_tokens, seed]).encode()).hexdigest()[:20]


def recorded(since=SINCE, replies=REPLIES):
    """The builder's recorded vendor exchanges of the three families since `since` (UTC ISO):
    [{id, family, prompt, max_tokens, seed, vendor: [{backend, text, recorded_at, path}]}], one job per distinct
    (prompt, max_tokens, seed), every vendor answer to it kept."""
    jobs = {}
    for p in sorted(glob.glob(os.path.join(replies, "*", "*.json"))):
        try:
            with open(p) as f:
                r = json.load(f)
        except (OSError, ValueError):
            continue
        fam = family(r.get("prompt", ""))
        if fam is None or (r.get("recorded_at") or "") < since or not isinstance(r.get("text"), str):
            continue
        jid = prompt_id(r["prompt"], r.get("max_tokens"), r.get("seed"))
        j = jobs.setdefault(jid, {"id": jid, "family": fam, "prompt": r["prompt"], "max_tokens": r.get("max_tokens"),
                                  "seed": r.get("seed"), "vendor": []})
        j["vendor"].append({"backend": r.get("backend"), "text": r["text"], "recorded_at": r.get("recorded_at"),
                            "path": os.path.relpath(p, replies)})
    order = {k: i for i, (k, _) in enumerate(FAMILIES)}
    return sorted(jobs.values(), key=lambda j: (order[j["family"]], j["id"]))


def render_wants_gpu0():
    return os.path.exists(YIELD_FLAG)


def done_ids(out):
    """Jobs with an ANSWER in `out` (a line whose call failed is not done: the next run asks it again; batch 61 C2).
    A truncated line (a crash mid-write) is skipped, never a crash."""
    if not os.path.exists(out):
        return set()
    done = set()
    with open(out) as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("text") is not None:
                done.add(r["id"])
    return done


def run(jobs, out, batch=BATCH, log=print, idle_s=20.0):
    """Ask MODEL every job not yet answered in `out` (JSONL), BATCH calls per lease, each job at most once per run (a
    failed call waits for the next run). Yields GPU0 to a render: YIELD_FLAG is checked before taking the lease, again
    once it is held (batch 61 C1: a render that asked in between gets it back at once, nothing loaded), and before
    every call. A held lease is waited out between batches. Returns the number of answers written."""
    import gpu0
    import story_semantics as sm
    written, tried = 0, set()
    while True:
        todo = [j for j in jobs if j["id"] not in done_ids(out) and j["id"] not in tried]
        if not todo:
            return written
        if render_wants_gpu0():
            log(f"  yielding GPU0 to a render ({YIELD_FLAG}); {len(todo)} jobs left")
            time.sleep(idle_s)
            continue
        try:
            with gpu0.lease(OWNER, wait_s=0):
                if render_wants_gpu0():                              # it asked while the lease was being taken
                    continue
                llm = sm.LocalLLM(model=MODEL).start()
                try:
                    for j in todo[:batch]:
                        if render_wants_gpu0():
                            break
                        tried.add(j["id"])
                        t0, err, text = time.time(), None, None
                        try:
                            text = llm._post(j["prompt"], j["max_tokens"] or 2000, j["seed"] if j["seed"] is not None else 7)
                        except gpu0.Gpu0Stop:
                            raise
                        except Exception as e:                       # recorded; asked again by the NEXT run only
                            err = f"{type(e).__name__}: {str(e)[:300]}"
                        with open(out, "a") as f:
                            f.write(json.dumps({"id": j["id"], "family": j["family"], "model": MODEL,
                                                "digest": getattr(llm, "digest", None), "text": text, "error": err,
                                                "seconds": round(time.time() - t0, 1),
                                                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
                        written += 1
                        log(f"  {j['family']:11s} {j['id']} {time.time() - t0:5.1f} s{' ERROR ' + err if err else ''}")
                finally:
                    gpu0.release_all()                               # GPU0 left as found before the lease goes
        except gpu0.LeaseBusy as e:
            log(f"  GPU0 lease busy ({e}); waiting")
            time.sleep(idle_s)


# ── RULING 87 (orchestrator 2026-11-13 '21:18', to the builder): "if only ONE outside family answers, step A's second
# verdict is the local gemma3:27b on GPU0 through the integrator's judge service". The SERVICE:
# - REQUEST: <EXTRA>/<request_id>.json in the builder's own directory (READ ONLY there: never moved or written; answered
#   once per name and content, a marker in answered/, a copy in done/ or failed/), or ROOT/requests/ (moved when
#   answered): {"request_id", "family": "step_a", "prompt": the exact vendor prompt, "max_tokens": int, "seed": int}.
#   ONE call per request.
# - RESULT: ROOT/results/<request_id>.<prompt_id>.json, prompt_id = prompt_id(prompt, max_tokens, seed): {request_id,
#   family, prompt_id, model, digest, seed, max_tokens, text (the raw reply), error, seconds, waited_s (from the
#   request file's time to the call), at, judge_sha}. An error is NO verdict; the reply's contract is the caller's.
# - GPU0: run()'s discipline. BATCH requests per lease, the yield flag before the lease, once it is held and before
#   every call (a render always first), gpu0.release_all at the batch end; a GPU0 stop leaves the rest pending.
ROOT = os.environ.get("PP_LOCAL_JUDGE_DIR", os.path.join(os.path.dirname(PIPELINE), "data", "local_judge"))
EXTRA = os.environ.get("PP_LOCAL_JUDGE_EXTRA", "/home/ultron/worktrees/pp-selectid/tests/package/proof/judge_requests")
SERVED = ("step_a",)                                  # ruling 87: step A's second verdict, nothing else
SAFE = "^[A-Za-z0-9_.:~-]{1,120}$"


def judge_sha():
    """sha256 over the code that answers (this file; story_semantics.py, the model call)."""
    h = hashlib.sha256()
    for name in ("local_judge.py", "story_semantics.py"):
        with open(os.path.join(PIPELINE, name), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def problems(r):
    import re
    if not isinstance(r, dict):
        return ["not an object"]
    why = [] if isinstance(r.get("request_id"), str) and re.match(SAFE, r["request_id"]) else \
        [f"request_id must match {SAFE}"]
    if r.get("family") not in SERVED:
        why.append(f"family must be one of {list(SERVED)} (ruling 87)")
    elif not (isinstance(r.get("prompt"), str) and family(r["prompt"]) == r["family"]):
        why.append("prompt must be a step-A prompt (the vendor prompt, as sent)")
    for k, lo, hi in (("max_tokens", 1, 32768), ("seed", 0, 2 ** 31 - 1)):
        if not (isinstance(r.get(k), int) and not isinstance(r.get(k), bool) and lo <= r[k] <= hi):
            why.append(f"{k} must be an integer {lo}-{hi}")
    return why


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


def _marker(path, dg):
    return os.path.join(ROOT, "answered", f"{os.path.basename(path)}.{dg}")


def pending():
    """Own requests, then the builder's (EXTRA) whose name and content have not been answered."""
    own = sorted(glob.glob(os.path.join(ROOT, "requests", "*.json")))
    extra = []
    for p in sorted(glob.glob(os.path.join(EXTRA, "*.json"))) if EXTRA else []:
        try:
            with open(p, "rb") as f:
                if not os.path.exists(_marker(p, hashlib.sha256(f.read()).hexdigest()[:16])):
                    extra.append(p)
        except OSError:                                  # renamed or removed while listed: the next pass sees it
            continue
    return own + extra


def _close(path, r, dg, why=None):
    """Answered (why None) or malformed: an own request moves to done/ (failed/, with why); the builder's is never
    touched: its copy goes to done/ or failed/ here and a marker keyed by its name and content keeps it answered."""
    sub = os.path.join(ROOT, "requests", "failed" if why else "done")
    os.makedirs(sub, exist_ok=True)
    if os.path.dirname(os.path.abspath(path)) == os.path.abspath(os.path.join(ROOT, "requests")):
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


def result_path(r):
    return os.path.join(ROOT, "results", f"{r['request_id']}.{prompt_id(r['prompt'], r['max_tokens'], r['seed'])}.json")


def _answered(r, sha):
    """True when this request's answer is already on file from this code (a stop between the result and the close:
    batch 72 c1 consensus); a result whose call failed is asked again."""
    try:
        with open(result_path(r)) as f:
            e = json.load(f)
    except (OSError, ValueError):
        return False
    return e.get("error") is None and isinstance(e.get("text"), str) and e.get("judge_sha") == sha


def serve_once(log=print):
    """Answer up to BATCH pending requests under ONE GPU0 lease. -> how many were closed (answered or malformed)."""
    import gpu0
    import story_semantics as sm
    n, ready, sha = 0, [], judge_sha()
    for path in pending()[:BATCH]:
        try:
            r, why, dg = _load(path)
        except OSError:
            continue
        if why:
            _close(path, r, dg, why)
            log(f"  {os.path.basename(path)}: malformed: {'; '.join(why)}")
            n += 1
        elif _answered(r, sha):                                  # answered before a stop: closed, never asked twice
            _close(path, r, dg)
            log(f"  {r['request_id']}: its answer was already on file: closed, not asked again")
            n += 1
        else:
            ready.append((path, r, dg))
    if not ready or render_wants_gpu0():
        return n
    try:
        with gpu0.lease(OWNER, wait_s=0):
            if render_wants_gpu0():                              # it asked while the lease was being taken
                return n
            llm = sm.LocalLLM(model=MODEL).start()
            try:
                for path, r, dg in ready:
                    if render_wants_gpu0():                      # a render first: the rest stay pending
                        break
                    t0, text, err = time.time(), None, None
                    waited = round(t0 - os.path.getmtime(path), 1) if os.path.exists(path) else None
                    try:
                        text = llm._post(r["prompt"], r["max_tokens"], r["seed"])
                    except gpu0.Gpu0Stop:
                        raise
                    except Exception as e:                       # no verdict, never retried here
                        err = f"{type(e).__name__}: {str(e)[:300]}"
                    pid, out = prompt_id(r["prompt"], r["max_tokens"], r["seed"]), result_path(r)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with open(out + ".tmp", "w") as f:
                        json.dump({"request_id": r["request_id"], "family": r["family"], "prompt_id": pid,
                                   "model": MODEL, "digest": getattr(llm, "digest", None), "seed": r["seed"],
                                   "max_tokens": r["max_tokens"], "text": text, "error": err,
                                   "seconds": round(time.time() - t0, 1), "waited_s": waited,
                                   "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "judge_sha": sha},
                                  f, indent=1)
                    os.replace(out + ".tmp", out)
                    _close(path, r, dg)
                    n += 1
                    log(f"  {r['request_id']}: {time.time() - t0:.1f} s{' ERROR ' + err if err else ''}")
            finally:
                gpu0.release_all()                               # GPU0 left as found before the lease goes
    except gpu0.Gpu0Stop as e:                                   # busy, a foreign user, out of memory: the rest wait
        log(f"  GPU0 stop, the rest stay pending: {type(e).__name__}: {e}")
    return n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["replay", "list", "serve", "once"])
    ap.add_argument("--since", default=SINCE)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(PIPELINE), "data", "local_judge", "replay_answers.jsonl"))
    a = ap.parse_args(argv)
    if a.cmd in ("serve", "once"):                               # ruling 87's judge service
        if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
            sys.exit("the local judge runs on GPU0: CUDA_VISIBLE_DEVICES=0 (law L-r)")
        for d in ("requests", "results"):
            os.makedirs(os.path.join(ROOT, d), exist_ok=True)
        print(f"{time.strftime('%H:%M:%S')} judge service: {MODEL}, judge_sha {judge_sha()[:12]}, root {ROOT}, "
              f"requests also from {EXTRA}", flush=True)
        while True:
            n = serve_once(log=lambda m: print(f"{time.strftime('%H:%M:%S')} {m}", flush=True))
            if a.cmd == "once":
                return 0
            if not n:
                time.sleep(5.0)
    jobs = recorded(a.since)
    counts = {k: sum(j["family"] == k for j in jobs) for k, _ in FAMILIES}
    print(f"{len(jobs)} recorded prompts since {a.since}: {counts}")
    if a.cmd == "list":
        return 0
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        sys.exit("the local judge runs on GPU0: CUDA_VISIBLE_DEVICES=0 (law L-r)")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out + ".jobs.json", "w") as f:                          # what was asked, for the comparison
        json.dump(jobs, f)
    n = run(jobs, a.out)
    print(f"done: {n} answers written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
