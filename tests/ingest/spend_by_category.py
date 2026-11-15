"""Read-only: pp-ingest's spend since Nov 12 00:00 ET by vendor x category, vendor-reported vs estimated, from the
evidence json of tests/ingest/spend_by_vendor.py (argv[1]) and the watcher's queue (its calls split by role)."""
import collections, json, os, sqlite3, sys
WT = "/home/ultron/worktrees/pp-ingest"
d = json.load(open(sys.argv[1]))
vendor_of = {b: c.get("vendor") for b, c in json.load(open(os.path.join(WT, "pipeline/ingest/providers.json")))["backends"].items()}
cells = collections.defaultdict(lambda: [0.0, 0.0])          # (vendor, category) -> [reported, estimated]
CAT = ("mining", "hook pass", "flag checks", "calibration", "audits", "other")

def add(v, cat, usd, reported):
    cells[(v, cat)][0 if reported else 1] += usd or 0.0

def reported(v, basis):
    b = basis.lower()
    return (v == "heimdall" and b.startswith("measured")) or (v == "xai" and "cost_in_usd_ticks" in b and b.startswith("measured"))

watcher_total = collections.defaultdict(float)
for r in d["rows"]:
    src, v = r["source"], r["vendor"]
    if src.startswith("watcher"):
        watcher_total[v] += r["usd"] or 0.0
        continue                                              # split by role from the queue below
    cat = ("audits" if src.startswith("audit") or src.startswith("freeze audit") else
           "calibration" if src.startswith("ruling 40: choosing the checker") else
           "flag checks" if src.startswith("ruling 40") else "other")
    add(v, cat, r["usd"], reported(v, r["basis"]))
import re, datetime as dt
log = open(os.path.join(WT, "data/editorial/ingest/logs/service.log")).read().splitlines()
T = lambda x: dt.datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp()
starts = [T(l.split()[0]) for l in log if " pp-ingest service: store " in l]
wins = []                                                     # each calibration's window: a live one logs its seconds;
for l in log:                                                 # an earlier one is bounded by the watcher start before it
    m = re.match(r"^(\S+) check: calibration (\(asked live, (\d+) s\)|\[)", l)
    if m:
        end = T(m.group(1))
        st = max([x for x in starts if x <= end] or [end - 120])
        wins.append((end - int(m.group(3)) - 10 if m.group(3) else (st if end - st <= 1800 else end - 120), end + 2))
con = sqlite3.connect(f"file:{WT}/data/editorial/ingest/queue.sqlite?mode=ro", uri=True)
split = collections.defaultdict(float)
for role, bid, ts, usd in con.execute("SELECT role, backend, ts, COALESCE(cost_usd,0) FROM calls"):
    v = vendor_of.get(bid) or "unknown"
    cat = {"mine": "mining", "mine_paid": "mining", "hook": "hook pass", "spotlight": "hook pass", "probe": "other"}.get(
        role, ("calibration" if any(a <= ts <= b for a, b in wins) else "flag checks") if role == "flagcheck" else "other")
    add(v, cat, usd, v in ("heimdall", "xai"))               # the watcher records Heimdall's usage.cost and xAI's ticks
    split[v] += usd or 0.0
for v in set(watcher_total) | set(split):                     # the split must sum to the evidence file's watcher rows
    assert abs(watcher_total[v] - split[v]) < 0.002, (v, watcher_total[v], split[v])
vendors = sorted({v for v, _ in cells}, key=lambda v: -sum(sum(cells[(v, c)]) for c in CAT))
fmt = lambda r, e: ("—" if r + e < 0.00005 else " + ".join(x for x in (f"${r:.2f} r" if r >= 0.005 else ("<$0.01 r" if r > 0 else ""),
                                                                      f"${e:.2f} e" if e >= 0.005 else ("<$0.01 e" if e > 0 else "")) if x))
out = {"vendors": vendors, "cells": {f"{v}|{c}": cells[(v, c)] for v in vendors for c in CAT}}
lines = ["| vendor | " + " | ".join(CAT) + " | total |", "|" + "---|" * (len(CAT) + 2)]
tr, te = 0.0, 0.0
colsum = collections.defaultdict(lambda: [0.0, 0.0])
for v in vendors:
    r = sum(cells[(v, c)][0] for c in CAT); e = sum(cells[(v, c)][1] for c in CAT)
    tr += r; te += e
    for c in CAT:
        colsum[c][0] += cells[(v, c)][0]; colsum[c][1] += cells[(v, c)][1]
    lines.append(f"| {v} | " + " | ".join(fmt(*cells[(v, c)]) for c in CAT) + f" | **{fmt(r, e)}** |")
lines.append("| **TOTAL** | " + " | ".join(fmt(*colsum[c]) for c in CAT) + f" | **{fmt(tr, te)} = ${tr + te:.2f}** |")
print("\n".join(lines))
print(json.dumps({"reported": round(tr, 4), "estimated": round(te, 4), "total": round(tr + te, 4),
                  "evidence_total": d["total_usd"]}))
