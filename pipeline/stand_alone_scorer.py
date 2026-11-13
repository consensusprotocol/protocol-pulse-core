#!/usr/bin/env python3
"""pipeline/stand_alone_scorer.py: the render's own STAND_ALONE clip scorer at the PIN STAGE (orchestrator 2026-11-13
'09:58' item 56). The builder may use no GPU, so moments that open on a word the scorer must affirm (a conjunction, a
reply fragment, a trimmed leading word) were left out unjudged. This asks THE SAME judge earlier: stand_alone.clip_scorer
(the one code path run_fresh.stage_validate uses, on the GPU0 LocalLLM, gemma3:27b, temperature 0) and
stand_alone.affirmed (the one threshold). Validate re-checks at render as now. Nothing is loosened.
RULING 60 ('11:01'): a MOMENTS request (kind "moments", every builder pin) is judged STAND-ALONE ONLY
(story_semantics.ALONE_PROMPT via rate_alone; no event; affirmed = score >= 3.5); a "story" request keeps
CLIP_PROMPT with its event and the story threshold.

CONTRACT (the builder):
- REQUEST: write data/stand_alone_scorer/requests/<request_id>.json (write <name>.tmp, then rename):
  {"request_id": str, "kind": "moments" | "story" (default "story"), "event": str (story only; absent or null for
  moments), "passages": [{"moment_id": str, "pid": str, "channel": str, "duration": number, "text": str}, ...]}. ONE scorer call per request, exactly validate's shape: the passages are scored together, as
  validate scores every segment of an EDL that needs the scorer in one call. To be byte-identical with validate:
  a moments pin is kind "moments" (no event; a story pin: event "Pinned: <headline, else label>"), pid "hook" / "clip_NN" by position, channel the registry
  display name, duration the locked words' span (seconds; the prompt rounds it), text the approved text.
- RESULT: data/stand_alone_scorer/results/<moment_id>.<sha256(text)[:16]>.<SCORER_SHA[:12]>.json: a list of verdicts
  for that moment and text under this scorer code, one per distinct prompt: {request_id, kind, event, pid, channel,
  duration, prompt_sha256, score, reason, fault, affirmed, threshold, model, digest, scorer_sha, at}. score None with
  an error = the reply was unparseable: NOT affirmed.
- The request moves to requests/done/ when answered, to requests/failed/ (with "why") when malformed.
- SCORER_SHA: sha256 over pipeline/stand_alone.py + pipeline/story_semantics.py (the threshold, the prompt, the model
  call). A verdict under another SCORER_SHA is not this code's.
- The model's validated replies are cached by their exact prompt (story_semantics.chat_json), so validate asking the
  byte-identical prompt reads the same answer.
GPU0 (law L-r): local_judge's discipline. The lease is taken per batch of BATCH requests, gpu0.release_all at every batch
end; local_judge.YIELD_FLAG is checked before taking the lease, once it is held, and before every request (a render
always first).
Usage: CUDA_VISIBLE_DEVICES=0 python3 pipeline/stand_alone_scorer.py serve | once"""
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
import stand_alone as SA  # noqa: E402

ROOT = os.environ.get("PP_SCORER_DIR", os.path.join(REPO, "data", "stand_alone_scorer"))
OWNER = "pin-stage clip scorer (integrator, GPU0)"
BATCH = 8
SAFE = re.compile(r"^[A-Za-z0-9_.:~-]{1,120}$")
KINDS = ("moments", "story")          # ruling 60: a moments pin is judged stand-alone only, with no event


def scorer_sha():
    h = hashlib.sha256()
    for name in ("stand_alone.py", "story_semantics.py"):
        with open(os.path.join(PIPELINE, name), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


class Recording:
    """The model, with every prompt it is asked recorded (prompt_sha256 comes from the call itself, never rebuilt)."""

    def __init__(self, llm):
        self.llm, self.prompts = llm, []

    def chat_json(self, prompt, **kw):
        self.prompts.append(prompt)
        return self.llm.chat_json(prompt, **kw)


def problems(r):
    """[why] for a malformed request (empty = well formed)."""
    out = []
    if not isinstance(r, dict):
        return ["not an object"]
    if not isinstance(r.get("request_id"), str) or not SAFE.match(r["request_id"]):
        out.append("request_id must be 1-120 of [A-Za-z0-9_.:-]")
    kind = r.get("kind", "story")
    if kind not in KINDS:
        out.append(f"kind must be one of {KINDS}")
    elif kind == "story" and (not isinstance(r.get("event"), str) or not r["event"].strip()):
        out.append("event must be a non-empty string (kind story)")
    elif kind == "moments" and r.get("event") is not None:
        out.append("a moments request carries no event (ruling 60: stand-alone only)")
    ps = r.get("passages")
    if not isinstance(ps, list) or not 1 <= len(ps) <= 16:
        return out + ["passages must be a list of 1-16"]
    for i, p in enumerate(ps):
        if not isinstance(p, dict):
            out.append(f"passage {i}: not an object")
            continue
        for k in ("moment_id", "pid", "channel", "text"):
            if not isinstance(p.get(k), str) or not p[k].strip():
                out.append(f"passage {i}: {k} must be a non-empty string")
        if isinstance(p.get("moment_id"), str) and not SAFE.match(p["moment_id"]):
            out.append(f"passage {i}: moment_id must be 1-120 of [A-Za-z0-9_.:-]")
        d = p.get("duration")
        if not isinstance(d, (int, float)) or isinstance(d, bool) or not 0 <= d < 600:
            out.append(f"passage {i}: duration must be a number of seconds")
    if len({p.get("pid") for p in ps if isinstance(p, dict)}) != len(ps):
        out.append("pids must be distinct")
    return out


def result_path(moment_id, text, sha):
    return os.path.join(ROOT, "results",
                        f"{moment_id}.{hashlib.sha256(text.encode()).hexdigest()[:16]}.{sha[:12]}.json")


def answer(path, llm, sha, log=print):
    """One request: one scorer call; every passage's verdict appended to its result file; the request moved."""
    import gpu0
    with open(path) as f:
        try:
            r = json.load(f)
        except ValueError as e:
            r, why = None, [f"not JSON: {e}"]
    why = problems(r) if r is not None else why
    name = os.path.basename(path)
    if why:
        os.makedirs(os.path.join(ROOT, "requests", "failed"), exist_ok=True)
        with open(os.path.join(ROOT, "requests", "failed", name), "w") as f:
            json.dump({"request": r, "why": why}, f, indent=1)
        os.remove(path)
        log(f"  {name}: malformed: {'; '.join(why)}")
        return
    rec, err, moments = Recording(llm), None, r.get("kind", "story") == "moments"
    try:
        ratings = SA.clip_scorer(r.get("event"), llm=rec, moments=moments)([dict(p) for p in r["passages"]])
    except gpu0.Gpu0Stop:
        raise
    except Exception as e:                                       # no verdict, never invented: NOT affirmed
        ratings, err = {}, f"{type(e).__name__}: {str(e)[:300]}"
    psha = hashlib.sha256(rec.prompts[-1].encode()).hexdigest() if rec.prompts else None
    for p in r["passages"]:
        score, reason, fault = ratings.get(p["pid"], (None, None, None))
        entry = {"request_id": r["request_id"], "kind": r.get("kind", "story"), "event": r.get("event"), "pid": p["pid"],
                 "channel": p["channel"],
                 "duration": p["duration"], "prompt_sha256": psha, "score": score, "reason": reason, "fault": fault,
                 "affirmed": SA.affirmed(score, fault, moments), "threshold": SA.CLIP_MIN_SCORE, "model": getattr(llm, "model", None),
                 "digest": getattr(llm, "digest", None), "scorer_sha": sha,
                 "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 **({"error": err or "no rating for this pid in the reply"} if score is None else {})}
        out = result_path(p["moment_id"], p["text"], sha)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        prev = []
        if os.path.exists(out):
            with open(out) as f:
                prev = json.load(f)
        tmp = out + ".tmp"
        with open(tmp, "w") as f:
            json.dump(prev + [entry], f, indent=1)
        os.replace(tmp, out)
    os.makedirs(os.path.join(ROOT, "requests", "done"), exist_ok=True)
    os.replace(path, os.path.join(ROOT, "requests", "done", name))
    log(f"  {name}: {len(r['passages'])} passage(s), affirmed "
        f"{sum(SA.affirmed(*ratings.get(p['pid'], (None, None, None))[::2], moments) for p in r['passages'])}"
        f"{' ERROR ' + err if err else ''}")


def pending():
    return sorted(glob.glob(os.path.join(ROOT, "requests", "*.json")))


def serve_once(log=print):
    """Answer up to BATCH pending requests under one GPU0 lease. -> how many were answered (0: none pending, a render
    asked, or the lease is held)."""
    import gpu0
    import story_semantics as sm
    todo = pending()
    if not todo or LJ.render_wants_gpu0():
        return 0
    sha, n = scorer_sha(), 0
    try:
        with gpu0.lease(OWNER, wait_s=0):
            if LJ.render_wants_gpu0():                           # it asked while the lease was being taken
                return 0
            llm = sm.LocalLLM().start()
            try:
                for path in todo[:BATCH]:
                    if LJ.render_wants_gpu0():
                        break
                    answer(path, llm, sha, log=log)
                    n += 1
            finally:
                gpu0.release_all()                               # GPU0 left as found before the lease goes
    except gpu0.LeaseBusy as e:
        log(f"  GPU0 lease busy ({e})")
    return n


def latest(moment_id, text, sha, kind="moments", event=None):
    """The newest entry WITH a score for this moment, text, scorer code, kind and event (an entry without one is not
    a verdict: batch 62 c1, glm), else the newest for them, else None."""
    p = result_path(moment_id, text, sha)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        es = [e for e in json.load(f) if e.get("kind", "story") == kind and e.get("event") == event]
    return next((e for e in reversed(es) if e.get("score") is not None), es[-1] if es else None)


def enqueue_candidates(path, sha):
    """The builder's candidates file (docs/audits/parallel/pp-selectid_SCORER_CANDIDATES.json: {generated_at, build,
    candidates: [{pid, video_id, channel, duration, text, text_sha256, trimmed_leading}]}): one single-passage request
    per candidate not yet rated under this scorer code, kind "moments" (ruling 60). -> (candidates, refused)."""
    with open(path) as f:
        c = json.load(f)
    refused = {}
    for x in c.get("candidates") or []:
        pid, text = str(x.get("pid")), x.get("text")
        if not isinstance(text, str) or hashlib.sha256(text.encode()).hexdigest() != x.get("text_sha256"):
            refused[pid] = "text_sha256 is not the sha256 of text"
            continue
        if (latest(pid, text, sha) or {}).get("score") is not None:
            continue                                                 # rated before: reused, never asked twice
        r = {"request_id": f"cand.{pid}.{x['text_sha256'][:12]}", "kind": "moments",
             "passages": [{"moment_id": pid, "pid": "clip_01", "channel": x.get("channel"), "duration": x.get("duration"),
                           "text": text}]}
        why = problems(r)
        if why:
            refused[pid] = "; ".join(why)
            continue
        q = os.path.join(ROOT, "requests", r["request_id"] + ".json")
        if not os.path.exists(q):
            with open(q + ".tmp", "w") as f:
                json.dump(r, f)
            os.replace(q + ".tmp", q)
    return c, refused


def write_verdicts(c, refused, sha, src):
    """The builder's verdicts file: {rated_at, build, candidates_generated_at, scorer, verdicts: {pid: {text_sha256,
    score, reason, fault, affirmed, prompt_sha256} | {text_sha256, error}}}. -> its path."""
    v = {}
    for x in c.get("candidates") or []:
        pid = str(x.get("pid"))
        if pid in refused:
            v[pid] = {"text_sha256": x.get("text_sha256"), "affirmed": False, "error": refused[pid]}
            continue
        e = latest(pid, x["text"], sha) or {}
        v[pid] = {"text_sha256": x["text_sha256"], "score": e.get("score"), "reason": e.get("reason"),
                  "fault": e.get("fault"), "affirmed": bool(e.get("affirmed")), "prompt_sha256": e.get("prompt_sha256"),
                  **({"error": e.get("error") or "not rated"} if e.get("score") is None else {})}
    out = {"rated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "build": c.get("build"),
           "candidates_file": src, "candidates_generated_at": c.get("generated_at"),
           "scorer": {"model": "gemma3:27b", "kind": "moments", "rubric": "ruling 60: stand-alone only",
                      "prompt": "story_semantics.ALONE_PROMPT via stand_alone.clip_scorer(moments=True)",
                      "threshold": SA.CLIP_MIN_SCORE, "rule": "stand_alone.affirmed(moments=True): score >= threshold",
                      "event": None, "scorer_sha": sha},
           "affirmed": sum(1 for x in v.values() if x.get("affirmed")), "verdicts": v}
    d = os.path.join(ROOT, "verdicts")
    os.makedirs(d, exist_ok=True)
    stamp = re.sub(r"[^0-9A-Za-z]", "", str(c.get("generated_at") or "unknown"))[:20]
    path = os.path.join(d, f"verdicts_{stamp}.json")
    for p in (path, os.path.join(d, "latest.json")):
        with open(p + ".tmp", "w") as f:
            json.dump(out, f, indent=1)
        os.replace(p + ".tmp", p)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["serve", "once"])
    ap.add_argument("--poll", type=float, default=10.0)
    ap.add_argument("--candidates", default=None, help="the builder's candidates file, watched while serving")
    a = ap.parse_args(argv)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        sys.exit("the pin-stage scorer runs on GPU0: CUDA_VISIBLE_DEVICES=0 (law L-r)")
    os.makedirs(os.path.join(ROOT, "requests"), exist_ok=True)
    sha, seen, open_ = scorer_sha(), None, None
    log = lambda m: print(time.strftime("%H:%M:%S"), m, flush=True)
    print(f"pin-stage scorer: {ROOT} | scorer_sha {sha[:12]}", flush=True)
    while True:
        if a.candidates and os.path.exists(a.candidates):
            try:
                with open(a.candidates) as f:
                    gen = json.load(f).get("generated_at")
            except (OSError, ValueError):
                gen = None                                       # being written: read on the next poll
            if gen and gen != seen:
                c, refused = enqueue_candidates(a.candidates, sha)
                seen, open_ = gen, (c, refused)
                log(f"candidates {gen}: {len(c.get('candidates') or [])}, refused {len(refused)}, queued "
                    f"{len(pending())}")
        n = serve_once(log=log)
        if open_ is not None and not any(os.path.basename(p).startswith("cand.") for p in pending()):
            path = write_verdicts(*open_, sha, a.candidates)
            log(f"verdicts written: {path} (affirmed {json.load(open(path))['affirmed']} of "
                f"{len(open_[0].get('candidates') or [])})")
            open_ = None
        if a.cmd == "once" and not pending() and open_ is None:
            return 0
        if n == 0:
            time.sleep(a.poll)


if __name__ == "__main__":
    sys.exit(main())
