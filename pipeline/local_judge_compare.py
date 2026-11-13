#!/usr/bin/env python3
"""pipeline/local_judge_compare.py: the local judge's replay measured against tonight's recorded vendor verdicts
(orchestrator 2026-11-13 '07:28' item 2: "PROVE IT BEFORE IT COUNTS ... report agreement per verdict type, with every
disagreement listed"). CPU only. The verdicts are read with the BUILDER'S OWN rules, imported from the pp-selectid
worktree in this process alone (its pipeline directory first on sys.path, this one's removed):
- step A: context_integrity._strict with A_KEYS, exactly the prompt's labels; a moment passes when a_failures() is
  empty. Agreement = the same pass / fail, and the same failing rules.
- the clips-alone verdict: package.medley's contract (through_line, clips = the prompt's labels rated 1-5, joins =
  package.joins of them, each {followable: bool, why: str}); ok = a stated through-line (>= 4 words, not NO_LINE),
  every clip >= COHERENCE_MIN, at most LY_MAX_BRIDGES joins not followable. Agreement = the same ok, the same flagged
  joins, the same followable per join.
- the angle step (a WRITER: its "agreement" is overlap, stated as such): the prompt's own rules (4-8 known ids, the
  hook first, at least 3 channels); per vendor angle the best moment-set Jaccard against the local angles, and whether
  a local hook is a vendor hook.
For a PRE-FILTER the direction matters and is reported apart: local FAIL where the vendor PASSES would drop a good
candidate before the vendor sees it (the costly error); local PASS where the vendor FAILS is harmless (the vendor
still judges it).
Usage: python3 pipeline/local_judge_compare.py ANSWERS.jsonl REPORT_PREFIX"""
import json
import os
import re
import subprocess
import sys

PIPELINE = os.path.dirname(os.path.abspath(__file__))
BUILDER = "/home/ultron/worktrees/pp-selectid/pipeline"
sys.path = [BUILDER] + [p for p in sys.path if os.path.abspath(p or ".") != PIPELINE]
import context_integrity as CI  # noqa: E402  (the builder's)
import package as P  # noqa: E402  (the builder's)


def step_a(job, text):
    labels = re.findall(r'<excerpt label="([^"]+)"', job["prompt"])
    A = CI._strict(text, {"excerpts"}, {"excerpts": CI.A_KEYS})
    by = {e["label"]: e for e in A["excerpts"] if isinstance(e.get("label"), str)}
    if set(by) != set(labels) or len(A["excerpts"]) != len(labels):
        raise ValueError(f"step A must answer exactly the labels {labels}")
    return {lb: CI.a_failures(by[lb]) for lb in labels}


def clips_alone(job, text):
    labs = re.findall(r'CLIP label="([^"]+)"', job["prompt"])
    js = P.joins(labs)
    v = json.loads(text.strip())
    if not isinstance(v, dict) or set(v) != {"through_line", "clips", "joins"} or not isinstance(v["clips"], dict) \
            or set(v["clips"]) != set(labs) or any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()) \
            or not isinstance(v["joins"], dict) or set(v["joins"]) != set(js) \
            or any(not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
                   or not isinstance(x["why"], str) for x in v["joins"].values()):
        raise ValueError("clips-alone verdict out of contract")
    tl = v["through_line"] if isinstance(v["through_line"], str) else ""
    flagged = [j for j in js if v["joins"][j]["followable"] is False]
    ok = bool(tl.strip()) and not P.NO_LINE.search(tl) and len(tl.split()) >= 4 and \
        min(v["clips"].values()) >= P.COHERENCE_MIN and len(flagged) <= P.LY_MAX_BRIDGES
    return {"ok": ok, "flagged": flagged, "followable": {j: v["joins"][j]["followable"] for j in js},
            "clips": v["clips"], "through_line": tl}


def angle(job, text):
    cands = {m.group(1): m.group(2).strip() for m in re.finditer(r"id=([0-9a-f]{20}) \| ([^|]+)\|", job["prompt"])}
    v = json.loads(text.strip())
    out = []
    for a in (v.get("angles") or []) if isinstance(v, dict) else []:
        ms = a.get("moments") if isinstance(a, dict) else None
        valid = (isinstance(ms, list) and 4 <= len(ms) <= 8 and len(set(ms)) == len(ms) and all(m in cands for m in ms)
                 and a.get("hook") == ms[0] and len({cands[m] for m in ms}) >= 3 and isinstance(a.get("angle"), str))
        out.append({"valid": bool(valid), "moments": list(ms) if isinstance(ms, list) else [], "hook": a.get("hook")
                    if isinstance(a, dict) else None, "angle": a.get("angle") if isinstance(a, dict) else None})
    if not out:
        raise ValueError("no angles")
    return out


READ = {"step_a": step_a, "clips_alone": clips_alone, "angle": angle}


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 0.0


def main(answers, prefix):
    with open(answers + ".jobs.json") as f:
        jobs = {j["id"]: j for j in json.load(f)}
    local = {}
    with open(answers) as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("text") is not None or r["id"] not in local:          # an answer outranks a failed call
                local[r["id"]] = r
    rep = {fam: {"jobs": 0, "local_out_of_contract": [], "vendor_out_of_contract": 0, "vendor_answers_not_compared": [],
                 "seconds": []} for fam in READ}
    rows = {fam: [] for fam in READ}
    for jid, job in jobs.items():
        if jid not in local:
            continue
        fam, r = job["family"], rep[job["family"]]
        r["jobs"] += 1
        r["seconds"].append(local[jid]["seconds"])
        try:
            lv = READ[fam](job, local[jid]["text"] or "")
        except Exception as e:
            r["local_out_of_contract"].append({"id": jid, "why": f"{type(e).__name__}: {str(e)[:160]}",
                                               "error": local[jid].get("error")})
            continue
        # ONE vendor answer per job (batch 61 C3 / C4): the earliest that reads in contract, so every count is per
        # moment / line-up / angle prompt; any other answer to the same prompt is listed, not counted
        cmp_ = None
        for vend in sorted(job["vendor"], key=lambda v: v.get("recorded_at") or ""):
            try:
                vv = READ[fam](job, vend["text"])
            except Exception:
                r["vendor_out_of_contract"] += 1
                continue
            if cmp_ is None:
                cmp_ = {"id": jid, "backend": vend["backend"], "vendor": vv, "local": lv}
            else:
                r["vendor_answers_not_compared"].append({"id": jid, "backend": vend["backend"]})
        if cmp_ is not None:
            rows[fam].append(cmp_)
    # step A: per moment
    a = rep["step_a"]
    a.update(moments=0, same_verdict=0, same_rules=0, local_fail_vendor_pass=[], local_pass_vendor_fail=[],
             rule_disagreements=[])
    for x in rows["step_a"]:
        for lb, vr in x["vendor"].items():
            lr = x["local"][lb]
            a["moments"] += 1
            a["same_verdict"] += (not vr) == (not lr)
            a["same_rules"] += sorted(vr) == sorted(lr)
            d = {"id": x["id"], "label": lb, "vendor": x["backend"], "vendor_rules": vr, "local_rules": lr}
            if lr and not vr:
                a["local_fail_vendor_pass"].append(d)
            elif vr and not lr:
                a["local_pass_vendor_fail"].append(d)
            elif sorted(vr) != sorted(lr):
                a["rule_disagreements"].append(d)
    # clips alone: per verdict and per join
    c = rep["clips_alone"]
    c.update(verdicts=0, same_ok=0, same_flagged=0, joins=0, same_join=0, local_fail_vendor_pass=[],
             local_pass_vendor_fail=[], flag_disagreements=[], join_disagreements=[], rating_abs_diff=[])
    for x in rows["clips_alone"]:
        v, l = x["vendor"], x["local"]
        c["verdicts"] += 1
        c["same_ok"] += v["ok"] == l["ok"]
        c["same_flagged"] += sorted(v["flagged"]) == sorted(l["flagged"])
        d = {"id": x["id"], "vendor": x["backend"], "vendor_ok": v["ok"], "local_ok": l["ok"], "vendor_flagged":
             v["flagged"], "local_flagged": l["flagged"], "vendor_clips": v["clips"], "local_clips": l["clips"]}
        if l["ok"] and not v["ok"]:
            c["local_pass_vendor_fail"].append(d)
        elif v["ok"] and not l["ok"]:
            c["local_fail_vendor_pass"].append(d)
        elif sorted(v["flagged"]) != sorted(l["flagged"]):
            c["flag_disagreements"].append(d)
        for j, f in v["followable"].items():
            c["joins"] += 1
            c["same_join"] += f == l["followable"][j]
            if f != l["followable"][j]:
                c["join_disagreements"].append({"id": x["id"], "join": j, "vendor": f, "local": l["followable"][j]})
        c["rating_abs_diff"] += [abs(v["clips"][k] - l["clips"][k]) for k in v["clips"]]
    # angle: overlap
    g = rep["angle"]
    g.update(compared=0, local_valid_angles=0, local_angles=0, best_jaccard=[], first_jaccard=[], hook_shared=0,
             first_hook_same=0, rows=[])
    for x in rows["angle"]:
        vv = [y for y in x["vendor"] if y["valid"]]
        lv = [y for y in x["local"] if y["valid"]]
        g["local_angles"] += len(x["local"])
        g["local_valid_angles"] += len(lv)
        if not vv:
            continue
        g["compared"] += 1
        best = [max((jaccard(y["moments"], z["moments"]) for z in lv), default=0.0) for y in vv]
        g["best_jaccard"] += best
        g["first_jaccard"].append(jaccard(vv[0]["moments"], lv[0]["moments"]) if lv else 0.0)
        shared = bool({y["hook"] for y in vv} & {z["hook"] for z in lv})
        g["hook_shared"] += shared
        g["first_hook_same"] += bool(lv) and vv[0]["hook"] == lv[0]["hook"]
        g["rows"].append({"id": x["id"], "vendor": x["backend"], "vendor_angles": len(vv), "local_valid": len(lv),
                          "best_jaccard": [round(b, 2) for b in best], "hook_shared": shared,
                          "vendor_hooks": [y["hook"] for y in vv], "local_hooks": [z["hook"] for z in lv]})
    rep["prefilter_rules"] = prefilter_rules(rows)
    for fam in READ:
        s = rep[fam].pop("seconds")
        rep[fam]["local_seconds"] = {"n": len(s), "mean": round(sum(s) / len(s), 1) if s else None,
                                     "max": max(s) if s else None}
    head = subprocess.run(["git", "-C", BUILDER, "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    rep["_meta"] = {"model": next((r.get("model") for r in local.values()), None),
                    "digest": next((r.get("digest") for r in local.values() if r.get("digest")), None),
                    "builder_rules": f"{BUILDER} @ {head.stdout.strip() if head.returncode == 0 else 'unknown'}",
                    "answers": answers}
    with open(prefix + ".json", "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps(summary(rep), indent=1))
    return rep


def prefilter_rules(rows):
    """Candidate PRE-FILTER rules measured on the recorded cases (law L-aa: an A/B on recorded cases). A local REJECT
    skips the vendor verdict: 'saved' = it rejected what the vendor also rejected; 'lost' = it rejected what the vendor
    PASSED (a good candidate never seen by the vendor). Only a rule with lost == 0 can be proposed for use."""
    out = {"step_a": {}, "clips_alone": {}}
    rules = sorted({r for x in rows["step_a"] for lb in x["local"] for r in x["local"][lb]})
    for rule in rules:                                      # reject a moment when the local judge fails THIS rule
        saved = lost = 0
        for x in rows["step_a"]:
            for lb, vr in x["vendor"].items():
                if rule in x["local"][lb]:
                    saved += bool(vr)
                    lost += not vr
        out["step_a"][f"local fails {rule}"] = {"saved": saved, "lost": lost}
    for t in (1, 2, 3):                                     # reject a line-up when the local judge rates a clip <= t
        saved = lost = 0
        for x in rows["clips_alone"]:
            if min(x["local"]["clips"].values()) <= t:
                saved += not x["vendor"]["ok"]
                lost += x["vendor"]["ok"]
        out["clips_alone"][f"a local clip rating <= {t}"] = {"saved": saved, "lost": lost}
    saved = lost = 0
    for x in rows["clips_alone"]:                           # reject a line-up when the local judge states no line
        if not x["local"]["through_line"].strip() or P.NO_LINE.search(x["local"]["through_line"]):
            saved += not x["vendor"]["ok"]
            lost += x["vendor"]["ok"]
    out["clips_alone"]["no local through-line"] = {"saved": saved, "lost": lost}
    return out


def pct(n, d):
    return f"{n}/{d} ({100.0 * n / d:.0f} %)" if d else "0/0"


def summary(rep):
    a, c, g = rep["step_a"], rep["clips_alone"], rep["angle"]
    mean = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
    return {"step_a": {"prompts": a["jobs"], "local_out_of_contract": len(a["local_out_of_contract"]),
                       "moments": a["moments"], "same_verdict": pct(a["same_verdict"], a["moments"]),
                       "same_rules": pct(a["same_rules"], a["moments"]),
                       "local_FAIL_vendor_PASS (lost candidates)": len(a["local_fail_vendor_pass"]),
                       "local_PASS_vendor_FAIL (harmless)": len(a["local_pass_vendor_fail"]),
                       "local_s": a["local_seconds"]},
            "clips_alone": {"verdicts": c["verdicts"], "local_out_of_contract": len(c["local_out_of_contract"]),
                            "same_ok": pct(c["same_ok"], c["verdicts"]), "same_flagged": pct(c["same_flagged"], c["verdicts"]),
                            "same_join": pct(c["same_join"], c["joins"]),
                            "local_FAIL_vendor_PASS (lost line-ups)": len(c["local_fail_vendor_pass"]),
                            "local_PASS_vendor_FAIL (harmless)": len(c["local_pass_vendor_fail"]),
                            "mean_rating_abs_diff": mean(c["rating_abs_diff"]), "local_s": c["local_seconds"]},
            "angle": {"compared": g["compared"], "local_out_of_contract": len(g["local_out_of_contract"]),
                      "local_valid_angles": f"{g['local_valid_angles']}/{g['local_angles']}",
                      "mean_best_jaccard": mean(g["best_jaccard"]), "mean_first_jaccard": mean(g["first_jaccard"]),
                      "hook_shared": pct(g["hook_shared"], g["compared"]),
                      "first_hook_same": pct(g["first_hook_same"], g["compared"]), "local_s": g["local_seconds"]},
            "prefilter_rules": rep.get("prefilter_rules")}


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
