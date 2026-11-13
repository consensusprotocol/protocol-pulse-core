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

GPU0 (law L-r): every call runs under the GPU0 lease, in batches of at most BATCH calls; each batch ends with
gpu0.release_all (the model unloaded, GPU0 left as found) and the lease released. A render always comes first: before
EVERY call the judge checks YIELD_FLAG; whoever launches a render touches it, waits for the lease to come free, starts
the render and removes the flag once the render holds the lease. A held lease (LeaseBusy) is waited out between
batches, never forced. Outputs are appended one JSON line per job, so a stopped replay resumes where it stopped.

Usage: CUDA_VISIBLE_DEVICES=0 python3 pipeline/local_judge.py replay [--since ISO] [--out PATH]"""
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["replay", "list"])
    ap.add_argument("--since", default=SINCE)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(PIPELINE), "data", "local_judge", "replay_answers.jsonl"))
    a = ap.parse_args(argv)
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
