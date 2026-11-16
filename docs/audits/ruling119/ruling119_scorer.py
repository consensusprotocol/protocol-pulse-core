#!/usr/bin/env python3
"""Ruling 119 (1) (orchestrator 08:25 ET Nov 16, relayed by the builder pp-selectid): the stand-alone clip scorer,
exactly as production runs it, on every clip of PBX's approved and published videos, three askings each.

THE SCORER: the production code of the main tree, unchanged and imported as is: stand_alone.clip_scorer(moments=True),
i.e. story_semantics.rate_alone (ALONE_PROMPT) on story_semantics.LocalLLM (gemma3:27b on the GPU0 Ollama,
temperature 0, seed 7 (+1 per retry), num_ctx 16384, max_tokens 1200); affirmed = stand_alone.affirmed(score, fault,
moments=True), score >= 3.5. GPU0 is taken as the scorer service takes it (law L-r): the lease; the render's yield
flag checked before the lease, once it is held and before every asking; gpu0.release_all before the lease goes.

THE ONE DEPARTURE: production caches a validated reply by its exact prompt (chat_json, DEC-13 e), so a second asking
of the same prompt never reaches the model. Here the cache is off (the instance's digest unset), so each of the three
askings is a real model call. The reply the production cache already holds for the same prompt, if any, is reported
beside them as "cached".

TWO PRODUCTION SHAPES (a clip's score can depend on the other clips in the same prompt):
  pin    every clip of the video in ONE asking, pid hook / clip_NN by position: the shape of a pin request to the
         scorer service and of the render's validate (stand_alone.check_edl) when every clip needs a verdict;
  alone  each clip in its own asking, pid clip_01: the shape of the scorer service's candidates path, whose verdicts
         the builder's selection reads.
INPUTS: text = each clip's approved_text as its pin seals it; channel = the pin's; duration = the approved run's EDL
span in seconds (the prompt rounds it), as the delivered-spans requests of Nov 13 carried it.

Usage: CUDA_VISIBLE_DEVICES=0 CUDA_DEVICE_ORDER=PCI_BUS_ID python3 -B ruling119_scorer.py run --out OUT.json
       python3 -B ruling119_scorer.py dry --out OUT.json   (inputs and the production cache only; no GPU, no model)
Exit: 0 done; 2 stopped for a render (resumable: run again); 3 GPU0 lease not had; 4 bad inputs."""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

REPO = "/home/ultron/protocol_pulse"
PIPELINE = os.path.join(REPO, "pipeline")
sys.path.insert(0, PIPELINE)
import stand_alone as SA  # noqa: E402
import story_semantics as sm  # noqa: E402

ET = ZoneInfo("America/New_York")
ASKINGS = 3
MAX_TOKENS = 1200                      # rate_alone's own
PROMPT_TEXT_CUT = 700                  # rate_alone quotes each text with quote_data(text, 700)
OWNER = "ruling 119 (1) approved-clip scorer run (integrator, GPU0)"
LEASE_WAIT_S = 1200

VIDEOS = [
    {"video": "preview", "note": "the protected preview of 2026-11-11 (law L-d, PBX-approved); a story-path video, "
                                 "judged here with the moments scorer like the others",
     "pin": "references/pulse_preview_2026-11-11/PIN.json", "edl": "references/pulse_preview_2026-11-11/edl.json"},
    {"video": "37c5b5f5", "note": "reference pulse_moments_2026-11-12",
     "pin": "references/pulse_moments_2026-11-12/PIN.json", "edl": "references/pulse_moments_2026-11-12/edl.json"},
    {"video": "41f29b1f", "note": "reference pulse_medley_2026-11-12",
     "pin": "references/pulse_medley_2026-11-12/PIN.json", "edl": "references/pulse_medley_2026-11-12/edl.json"},
    {"video": "0c68b589", "note": "reference pulse_fresh_2026-11-13 = run pinned_20261113_211048, published 18:10 "
                                  "ET Nov 13 as a YouTube Short",
     "pin": "references/pulse_fresh_2026-11-13/PIN.json", "edl": "references/pulse_fresh_2026-11-13/edl.json"},
    {"video": "13949b7c", "note": "frozen pin MOMENTS_PIN_LEDGER_215708; its only run, pinned_20261113_221758, held "
                                  "at prepare (17:24 ET Nov 13) and ruling 76 withdrew the pin: the EDL is that run's",
     "pin": "data/moments_pins/MOMENTS_PIN_LEDGER_215708.json", "edl": "runs/pinned_20261113_221758/edl.json"},
    {"video": "3f481f5a", "note": "the Blockware spotlight, frozen pin SPOTLIGHT_PIN_230148, run "
                                  "pinned_20261115_013448 (posted by PBX)",
     "pin": "data/moments_pins/SPOTLIGHT_PIN_230148.json", "edl": "runs/pinned_20261115_013448/edl.json",
     "spotlight": True},
]


def now_et():
    return datetime.now(ET).isoformat(timespec="seconds")


def sha256_text(t):
    return hashlib.sha256(t.encode()).hexdigest()


def sha256_file(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_inputs():
    """The clips of every video, checked against their pins and EDLs. Raises ValueError on any mismatch."""
    out = []
    for v in VIDEOS:
        pin_path, edl_path = os.path.join(REPO, v["pin"]), os.path.join(REPO, v["edl"])
        with open(pin_path) as f:
            pin = json.load(f)
        with open(edl_path) as f:
            edl = json.load(f)
        seal = (pin.get("moments_package") or {}).get("package_sha256")
        if v["video"] != "preview":
            if not (seal or "").startswith(v["video"]):
                raise ValueError(f"{v['video']}: the pin's seal is {seal!r}")
            if edl.get("moments_package_sha256") != seal:
                raise ValueError(f"{v['video']}: the EDL is bound to {edl.get('moments_package_sha256')!r}, "
                                 f"not the pin's seal")
        segs = pin["segments"]
        esegs = [edl["hook"]] + list(edl.get("clips") or [])
        if len(segs) != len(esegs):
            raise ValueError(f"{v['video']}: {len(segs)} pin segments, {len(esegs)} EDL segments")
        clips = []
        for i, (s, e) in enumerate(zip(segs, esegs)):
            text = s.get("approved_text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{v['video']} segment {i}: no approved_text")
            if (s.get("channel") or "") != (e.get("channel") or ""):
                raise ValueError(f"{v['video']} segment {i}: channel {s.get('channel')!r} vs EDL {e.get('channel')!r}")
            pid = "hook" if i == 0 else f"clip_{e.get('index', i):02d}"
            if i == 0 and s.get("role") != "hook":
                raise ValueError(f"{v['video']}: the first segment's role is {s.get('role')!r}")
            role = "spotlight" if v.get("spotlight") else pid
            clips.append({"video": v["video"], "role": role, "pid_pin": pid, "pid_alone": "clip_01",
                          "channel": s.get("channel"), "duration": float(e["duration"]),
                          "text": text, "text_sha256": sha256_text(text), "text_chars": len(text),
                          "text_cut_in_prompt": len(text) > PROMPT_TEXT_CUT,
                          "edl_text_same": (e.get("text") == text),
                          "source": {"video_id": s.get("video_id"), "start": s.get("start"), "end": s.get("end")}})
        out.append({"video": v["video"], "note": v["note"], "pin_file": v["pin"], "pin_file_sha256": sha256_file(pin_path),
                    "seal": seal, "edl_file": v["edl"], "edl_file_sha256": sha256_file(edl_path),
                    "approved_by_in_pin": pin.get("approved_by"), "clips": clips})
    return out


def units(videos):
    """Every asking unit: (shape, video, unit_key, [clips])."""
    us = []
    for v in videos:
        us.append(("pin", v["video"], "all", v["clips"]))
    for v in videos:
        for c in v["clips"]:
            us.append(("alone", v["video"], c["role"], [c]))
    return us


def passages(shape, clips):
    return [{"pid": c["pid_pin"] if shape == "pin" else c["pid_alone"], "channel": c["channel"],
             "duration": c["duration"], "text": c["text"]} for c in clips]


class Recorder:
    """The model, with the prompt it is asked and the reply it gives recorded."""

    def __init__(self, llm):
        self.llm, self.prompts, self.replies = llm, [], []

    def chat_json(self, prompt, **kw):
        self.prompts.append(prompt)
        r = self.llm.chat_json(prompt, **kw)
        self.replies.append(r)
        return r


class NoModel:
    """Dry run: records the exact prompt production would send, and never answers."""

    def __init__(self):
        self.prompts = []

    def chat_json(self, prompt, **kw):
        self.prompts.append(prompt)
        raise sm.LLMParseError("dry run: no model", [])


def cached_reply(model, digest, prompt):
    """The reply the production cache holds for this exact prompt (chat_json's key), or None."""
    if not digest:
        return None
    key = hashlib.sha256(json.dumps([model, digest, sm.LLM_CTX, MAX_TOKENS, prompt]).encode()).hexdigest()
    path = os.path.join(sm.LLM_CACHE_DIR, key[:2], key + ".json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f).get("reply")
    except Exception:
        return None


def rating_in(reply, pid):
    """rate_alone's own reading of one id in a reply: score clamped 1-5, an unknown fault 'unspecified'."""
    for x in (reply or {}).get("ratings", []) or []:
        try:
            if str(x["id"]) == pid:
                fault = x.get("fault") if x.get("fault") in sm.ALONE_FAULTS else "unspecified"
                score = max(1.0, min(5.0, float(x["score"])))
                return {"score": score, "fault": fault, "reason": x.get("reason", ""),
                        "affirmed": SA.affirmed(score, fault, moments=True)}
        except Exception:
            pass
    return None


def prompt_of(clips, shape):
    rec = NoModel()
    try:
        SA.clip_scorer(None, llm=rec, moments=True)(passages(shape, clips))
    except RuntimeError:
        pass
    return rec.prompts[0]


def save(path, doc):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1)
    os.replace(tmp, path)


def summary(doc):
    s = {}
    for shape in ("pin", "alone"):
        rows, lowest = [], None
        for v in doc["videos"]:
            for c in v["clips"]:
                a = [x for x in c["askings"][shape] if x.get("score") is not None]
                errs = [x for x in c["askings"][shape] if x.get("score") is None]
                scores = [x["score"] for x in a]
                if scores:
                    lowest = min(scores) if lowest is None else min(lowest, min(scores))
                rows.append({"video": c["video"], "role": c["role"], "scores": scores,
                             "faults": [x["fault"] for x in a], "affirmed": [x["affirmed"] for x in a],
                             "errors": len(errs),
                             "repeats": len({(x["score"], x["fault"]) for x in a}) <= 1 and not errs and len(a) == ASKINGS})
        s[shape] = {
            "clips": len(rows),
            "affirmed_in_every_asking": sum(1 for r in rows if r["affirmed"] and all(r["affirmed"]) and not r["errors"]
                                            and len(r["affirmed"]) == ASKINGS),
            "refused_in_some_asking": [r for r in rows if not all(r["affirmed"]) or r["errors"]],
            "split_verdicts": [r for r in rows if r["affirmed"] and any(r["affirmed"]) and not all(r["affirmed"])],
            "same_score_and_fault_in_all_three": sum(1 for r in rows if r["repeats"]),
            "lowest_score_of_an_approved_clip": lowest}
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("run", "dry"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        videos = load_inputs()
    except (ValueError, KeyError, OSError) as e:
        print(f"BAD INPUTS: {e}")
        return 4
    doc = None
    if a.mode == "run" and os.path.exists(a.out):
        with open(a.out) as f:
            doc = json.load(f)                                   # resume: keep every asking already made
        if [c["text_sha256"] for v in doc["videos"] for c in v["clips"]] != \
                [c["text_sha256"] for v in videos for c in v["clips"]]:
            print("BAD INPUTS: the existing output holds other clips")
            return 4
    if doc is None:
        doc = {"schema": "pp.ruling119_scorer/1",
               "what": "ruling 119 (1): the stand-alone clip scorer, exactly as production runs it, on every clip of "
                       "PBX's approved and published videos, three askings each (see 'scorer', 'departure', 'shapes')",
               "requested": "the builder pp-selectid, 08:2x ET Nov 16, quoting the orchestrator's ruling 119 (1) of "
                            "08:25 ET; run by the integrator on GPU0",
               "scorer": {"code": "main tree " + os.popen(f"git -C {REPO} rev-parse HEAD").read().strip()
                                  + " (release branch combo-letterbox-quoteonly-v2)",
                          "scorer_sha": __import__("stand_alone_scorer").scorer_sha(),
                          "entry": "stand_alone.clip_scorer(None, llm=..., moments=True)(passages)",
                          "prompt": "story_semantics.ALONE_PROMPT via story_semantics.rate_alone (ruling 60)",
                          "model": sm.LLM_MODEL, "host": sm.LLM_HOST, "temperature": 0,
                          "seed": "7 on the first attempt, 8 and 9 on a retry (chat_json)", "num_ctx": sm.LLM_CTX,
                          "max_tokens": MAX_TOKENS, "attempts": sm.LLM_ATTEMPTS,
                          "threshold": SA.CLIP_MIN_SCORE,
                          "rule": "stand_alone.affirmed(score, fault, moments=True): score >= 3.5, the fault not read",
                          "text_cut": f"rate_alone quotes each text to its first {PROMPT_TEXT_CUT} characters"},
               "departure": "production caches a validated reply by its exact prompt, so it never asks the same prompt "
                            "twice; here the cache was off (the LocalLLM's digest unset after start), so each asking "
                            "reached the model. 'cached' is the reply the production cache held for the same prompt "
                            "when the run began (null: none).",
               "shapes": {"pin": "every clip of the video in one asking, pid hook / clip_NN by position (a pin request "
                                 "to the scorer service; the render's validate when every clip needs a verdict)",
                          "alone": "each clip in its own asking, pid clip_01 (the scorer service's candidates path, "
                                   "whose verdicts the builder's selection reads)"},
               "videos": videos, "rounds_order": "round 1: every video in the pin shape, then every clip alone; "
                                                 "rounds 2 and 3 the same",
               "started": now_et(), "finished": None, "summary": None}
        digest = sm.model_digest(sm.LLM_HOST, sm.LLM_MODEL)
        doc["scorer"]["digest"] = digest
        for v in doc["videos"]:
            for c in v["clips"]:
                c["askings"] = {"pin": [], "alone": []}
                c["cached"] = {}
                c["prompt_sha256"] = {}
            pr = prompt_of(v["clips"], "pin")
            rep = cached_reply(sm.LLM_MODEL, digest, pr)
            for c in v["clips"]:
                c["prompt_sha256"]["pin"] = sha256_text(pr)
                c["cached"]["pin"] = rating_in(rep, c["pid_pin"]) if rep else None
            for c in v["clips"]:
                pa = prompt_of([c], "alone")
                rep = cached_reply(sm.LLM_MODEL, digest, pa)
                c["prompt_sha256"]["alone"] = sha256_text(pa)
                c["cached"]["alone"] = rating_in(rep, "clip_01") if rep else None
    if a.mode == "dry":
        save(a.out, doc)
        for v in doc["videos"]:
            print(f"{v['video']}: seal {str(v['seal'])[:16]} | {len(v['clips'])} clips | {v['pin_file']}")
            for c in v["clips"]:
                print(f"   {c['role']:9} {c['channel'][:20]:20} {c['duration']:6.2f}s {c['text_chars']:4}ch "
                      f"cut={c['text_cut_in_prompt']} edl_same={c['edl_text_same']} sha {c['text_sha256'][:12]} "
                      f"cached pin={c['cached']['pin']} alone={c['cached']['alone']}")
        print(f"askings to make: {ASKINGS * len(units(doc['videos']))} "
              f"({len(doc['videos'])} pin-shape units, {sum(len(v['clips']) for v in doc['videos'])} alone units)")
        return 0
    return run(doc, a.out)


def run(doc, out):
    import gpu0
    import local_judge as LJ
    by_key = {(v["video"], c["role"]): c for v in doc["videos"] for c in v["clips"]}

    def done(shape, video, key, clips):
        return min(len(c["askings"][shape]) for c in clips)

    if LJ.render_wants_gpu0():
        print(f"{now_et()} a render wants GPU0 (yield flag): not starting")
        return 2
    try:
        with gpu0.lease(OWNER, wait_s=LEASE_WAIT_S):
            print(f"{now_et()} GPU0 lease held")
            if LJ.render_wants_gpu0():
                print(f"{now_et()} a render wants GPU0: stopping")
                return 2
            llm = sm.LocalLLM().start()
            doc["scorer"]["digest_at_start"] = llm.digest
            llm.digest = None                                  # THE DEPARTURE: no cache read, no cache write
            try:
                for rnd in range(1, ASKINGS + 1):
                    for shape, video, key, clips in units(doc["videos"]):
                        if done(shape, video, key, clips) >= rnd:
                            continue
                        if LJ.render_wants_gpu0():
                            print(f"{now_et()} a render wants GPU0: stopping after {rnd - 1} full rounds")
                            save(out, doc)
                            return 2
                        rec = Recorder(llm)
                        calls0, t0, err = llm.calls, time.time(), None
                        try:
                            ratings = SA.clip_scorer(None, llm=rec, moments=True)(passages(shape, clips))
                        except gpu0.Gpu0Stop:
                            raise
                        except Exception as e:                    # no verdict, never invented: not affirmed
                            ratings, err = {}, f"{type(e).__name__}: {str(e)[:300]}"
                        meta = {"round": rnd, "at": now_et(), "seconds": round(time.time() - t0, 1),
                                "model_calls": llm.calls - calls0,
                                "prompt_sha256": sha256_text(rec.prompts[0]) if rec.prompts else None}
                        line = []
                        for c in clips:
                            pid = c["pid_pin"] if shape == "pin" else c["pid_alone"]
                            score, reason, fault = ratings.get(pid, (None, None, None))
                            entry = {**meta, "score": score, "fault": fault, "reason": reason,
                                     "affirmed": SA.affirmed(score, fault, moments=True)}
                            if score is None:
                                entry["error"] = err or "no rating for this id in the reply"
                            by_key[(video, c["role"])]["askings"][shape].append(entry)
                            line.append(f"{c['role']} {score} {fault}")
                        save(out, doc)
                        print(f"{now_et()} r{rnd} {shape:5} {video:8} {meta['seconds']:5.1f}s calls "
                              f"{meta['model_calls']}: " + "; ".join(line) + (f" ERROR {err}" if err else ""),
                              flush=True)
            finally:
                ev = gpu0.release_all()
                print(f"{now_et()} GPU0 released: unloaded {ev.get('unloaded') if isinstance(ev, dict) else ev}")
    except gpu0.LeaseBusy as e:
        print(f"{now_et()} GPU0 lease not had in {LEASE_WAIT_S} s: {e}")
        save(out, doc)
        return 3
    doc["finished"] = now_et()
    doc["summary"] = summary(doc)
    save(out, doc)
    print(json.dumps(doc["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
