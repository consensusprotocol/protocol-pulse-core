#!/usr/bin/env python3
"""Ruling 141 (2): the stand-alone scorer's ratings of (a) 20 moments it rated BEFORE its outage (15:26 ET Nov 16),
re-rated NOW, and (b) the clips of PBX-approved videos, rated NOW. Same code path as the service:
SA.clip_scorer(None, llm=Recording(LocalLLM), moments=True)(passages), under the GPU0 lease, released at the end.
Writes nothing into data/stand_alone_scorer (a scratch report only)."""
import collections
import datetime
import glob
import hashlib
import json
import os
import sys

REPO = "/home/ultron/protocol_pulse"
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import gpu0  # noqa: E402
import stand_alone as SA  # noqa: E402
import stand_alone_scorer as SS  # noqa: E402
import story_semantics as sm  # noqa: E402

OUT = sys.argv[1]
ET = datetime.timezone(datetime.timedelta(hours=-5))
OUTAGE = datetime.datetime(2026, 11, 16, 15, 26, tzinfo=ET)
SHA = SS.scorer_sha()


def sha16(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def old_verdict(mid, text):
    p = os.path.join(REPO, "data", "stand_alone_scorer", "results", f"{mid}.{sha16(text)}.{SHA[:12]}.json")
    if not os.path.exists(p):
        return None
    for v in json.load(open(p)):
        try:
            t = datetime.datetime.fromisoformat(v["at"].replace("Z", "+00:00"))
        except (KeyError, ValueError, AttributeError):
            continue
        if v.get("score") is not None and t < OUTAGE:
            return v
    return None


# (a) moments rated before the outage, by text digest, from the builder's recorded inputs
seen, pool = set(), collections.defaultdict(list)
for f in sorted(glob.glob("/home/ultron/worktrees/pp-selectid/tests/package/proof/*/inputs.json")):
    try:
        d = json.load(open(f))
    except ValueError:
        continue
    items = d if isinstance(d, list) else (d.get("moments") or d.get("rows") or [])
    for m in items if isinstance(items, list) else []:
        if not isinstance(m, dict) or not m.get("moment_id") or not isinstance(m.get("text"), str):
            continue
        key = (m["moment_id"], sha16(m["text"]))
        if key in seen:
            continue
        seen.add(key)
        v = old_verdict(m["moment_id"], m["text"])
        if v:
            pool[int(float(v["score"]))].append((m, v))
pick = []
for s in (5, 4, 3, 2, 1):
    pick += pool.get(s, [])[:4 if s in (5, 4) else 4]
pick = pick[:20]
print("pre-outage pool by old score:", {k: len(v) for k, v in sorted(pool.items())}, "| picked", len(pick), flush=True)

# (b) PBX-approved videos' clips (the delivered pins named in the build log), from their runs' EDLs
APPROVED = ("37c5b5f5", "41f29b1f", "1b4a63d0", "3f481f5a")
approved = []
for pd in sorted(glob.glob(os.path.join(REPO, "runs", "pinned_*", "PINNED_DECISION.json"))):
    rd = os.path.dirname(pd)
    if "_replay_" in rd:
        continue
    txt = open(pd).read()
    tag = next((a for a in APPROVED if a in txt), None)
    if not tag or any(x[0] == tag for x in approved):
        continue
    try:
        e = json.load(open(os.path.join(rd, "edl.json")))
    except (OSError, ValueError):
        continue
    for label, s in [("hook", e.get("hook") or {})] + [(f"clip_{c.get('index')}", c) for c in e.get("clips") or []]:
        t = s.get("text") or (s.get("selection_lock") or {}).get("text")
        if isinstance(t, str) and t.strip():
            approved.append((tag, label, s.get("channel"), t, float(s.get("duration") or s.get("cut_out", 0) - s.get("cut_in", 0) or 10.0)))
print("approved clips found:", len(approved), sorted({a[0] for a in approved}), flush=True)


def passages(rows):
    return [{"pid": f"p{i:02d}", "moment_id": mid, "text": text, "channel": ch or "?", "duration": round(dur, 2)}
            for i, (mid, text, ch, dur) in enumerate(rows)]


report = {"scorer_sha": SHA, "outage_start": OUTAGE.isoformat(), "pre_outage": [], "approved": []}
with gpu0.lease("integrator ruling 141 re-rate (free, local)", wait_s=300):
    llm = sm.LocalLLM().start()
    try:
        rec = SS.Recording(llm)
        rate = SA.clip_scorer(None, llm=rec, moments=True)
        for i in range(0, len(pick), 5):                          # five a call (the builder's requests carry several)
            chunk = pick[i:i + 5]
            ps = passages([(m["moment_id"], m["text"], m.get("channel_name"), float(m.get("duration_s") or 10.0))
                           for m, _ in chunk])
            got = rate(ps)
            for p, (m, v) in zip(ps, chunk):
                s, why, fault = got.get(p["pid"], (None, None, None))
                report["pre_outage"].append({"moment_id": m["moment_id"], "channel": m.get("channel_name"),
                                             "old": {"score": v["score"], "fault": v.get("fault"), "at": v["at"]},
                                             "now": {"score": s, "fault": fault, "reason": why}})
                print(f"  {m['moment_id'][:8]} {str(m.get('channel_name'))[:16]:16} old {v['score']} {v.get('fault')} | now {s} {fault}", flush=True)
        for i in range(0, len(approved), 5):
            chunk = approved[i:i + 5]
            ps = passages([(f"{a[0]}:{a[1]}", a[3], a[2], a[4]) for a in chunk])
            got = rate(ps)
            for p, a in zip(ps, chunk):
                s, why, fault = got.get(p["pid"], (None, None, None))
                report["approved"].append({"video": a[0], "segment": a[1], "channel": a[2], "now": {"score": s, "fault": fault, "reason": why}})
                print(f"  APPROVED {a[0]} {a[1]:8} {str(a[2])[:16]:16} now {s} {fault} | {str(why)[:90]}", flush=True)
        report["model"], report["digest"] = getattr(llm, "model", None), getattr(llm, "digest", None)
        report["prompt_sha256"] = hashlib.sha256(rec.prompts[-1].encode()).hexdigest() if rec.prompts else None
    finally:
        gpu0.release_all()
json.dump(report, open(OUT, "w"), indent=1)
pre = [r for r in report["pre_outage"] if r["now"]["score"] is not None]
same = sum(1 for r in pre if float(r["now"]["score"]) == float(r["old"]["score"]))
print(f"SUMMARY: pre-outage re-rated {len(pre)}, same score {same}, mean old "
      f"{sum(float(r['old']['score']) for r in pre)/max(1,len(pre)):.2f} now {sum(float(r['now']['score']) for r in pre)/max(1,len(pre)):.2f}; "
      f"approved rated {len(report['approved'])}, affirmed (>= 3.5) {sum(1 for r in report['approved'] if (r['now']['score'] or 0) >= 3.5)}; "
      f"model {report.get('model')} digest {str(report.get('digest'))[:12]} prompt {str(report.get('prompt_sha256'))[:12]}", flush=True)
