#!/usr/bin/env python3
"""Total model spend of the pp-ingest session by vendor, from every record it wrote (read-only), as of the call.

Sources: the watcher's queue (calls: every attempt with its cost), the smoke store's queue, the A/B attempts log, the
two audit cycles' results.json. Basis per vendor:
  heimdall   measured: usage.cost of every reply (the gateway reports it)
  anthropic  measured: usage tokens x the published list price ($4 / $20 per MTok, Claude Opus 5.5)
  xai        measured where usage.cost_in_usd_ticks was recorded (1 USD = 1e10 ticks); else estimated (marked)
  google     ESTIMATE: usage tokens x the published list price ($2 / $12 per MTok, prompts <= 200k); the vendor
             reports no cost
  openai     ESTIMATE: usage tokens x gpt-4o's list price ($2.50 / $10 per MTok); the vendor reports no cost
Calls whose usage was never saved (audit cycle 1's frontier legs: results.json was overwritten by the re-run of the
Heimdall leg; the 03:0x ET one-window proofs printed to the terminal) are estimated from the same-size calls and marked.
Every audit's results.json under docs/audits/parallel/pp-ingest_audit/ is summed (each ruling's cycles included). A
back-end id not in VENDOR takes its vendor from providers.json (ruling 87's probe back-ends). --carry <an earlier
evidence json> copies the rows of the scratch stores that no longer exist (the smoke, the freeze drill), marked so.

  python3 tests/ingest/spend_by_vendor.py --smoke <scratch smoke store> --out <json>
  python3 tests/ingest/spend_by_vendor.py --carry docs/audits/parallel/pp-ingest_audit/spend_by_vendor_20261113.json \
      --out <json>
"""
import argparse
import glob
import json
import os
import sqlite3

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENDOR = {"anthropic_frontier": "anthropic", "heimdall_qwen27b": "heimdall", "heimdall_deepseek": "heimdall",
          "heimdall_glm53flash": "heimdall", "heimdall_muse": "heimdall",
          "heimdall_qwen": "heimdall", "xai_frontier": "xai", "grok": "xai", "gemini_frontier": "google",
          "gemini": "google", "gpt4o": "openai"}
LIST = {"google": (2.0, 12.0), "openai": (2.5, 10.0)}
try:
    CFG_VENDOR = {b: c.get("vendor") for b, c in json.load(open(os.path.join(REPO, "pipeline/ingest/providers.json")))
                  ["backends"].items()}
except (OSError, ValueError, KeyError):
    CFG_VENDOR = {}


def vendor_of(b):
    return VENDOR.get(b) or CFG_VENDOR.get(b) or ("heimdall" if str(b).startswith("heimdall") else b)


def queue_rows(path, source, out):
    if not os.path.exists(path):
        return
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    for b, n, usd, mn, mx in db.execute("SELECT backend, SUM(kind!='cache'), SUM(COALESCE(cost_usd,0)), MIN(at), "
                                        "MAX(at) FROM calls GROUP BY backend"):
        out.append({"vendor": vendor_of(b), "source": source, "backend": b, "calls": n, "usd": round(usd, 4),
                    "basis": "measured (per call)", "first": mn, "last": mx})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", help="the scratch smoke store (03:0x ET)")
    ap.add_argument("--drill", help="the scratch store of the freeze drill (tests/ingest/drill_freeze.py)")
    ap.add_argument("--carry", help="an earlier evidence json: its smoke / freeze drill rows when those stores are gone")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = []
    queue_rows(os.path.join(REPO, "data/editorial/ingest/queue.sqlite"), "watcher (live; Anthropic: the 08:36-08:43 UTC "
               "outage drill only)", rows)
    if a.smoke:
        queue_rows(os.path.join(a.smoke, "ingest/queue.sqlite"), "smoke (scratch store, 03:2x ET)", rows)
    if a.drill:
        queue_rows(os.path.join(a.drill, "ingest/queue.sqlite"), "freeze drill (scratch store, 06:06-06:13 ET)", rows)
    if a.carry:
        for r in json.load(open(a.carry))["rows"]:
            if (r["source"].startswith("smoke (") and not a.smoke) or (r["source"].startswith("freeze drill (") and
                                                                       not a.drill):
                rows.append(dict(r, source=r["source"] + f" [carried from {os.path.basename(a.carry)}: the scratch "
                                                         "store is gone]"))
    for path in glob.glob(os.path.join(REPO, "data/editorial/ingest/ab/*/attempts.jsonl")):
        agg = {}
        for line in open(path):
            r = json.loads(line)
            if r.get("kind") == "cache":
                continue
            u = r.get("usage") or {}
            k = (r["backend"], r.get("role"))
            g = agg.setdefault(k, {"calls": 0, "usd": 0.0, "ticks": 0, "ticks_calls": 0})
            g["calls"] += 1
            if isinstance(u.get("cost_in_usd_ticks"), (int, float)):
                g["ticks"] += u["cost_in_usd_ticks"]
                g["ticks_calls"] += 1
            g["usd"] += r.get("cost_usd") or 0.0
        for (b, role), g in agg.items():
            v = vendor_of(b)
            if v == "xai" and g["ticks_calls"] == g["calls"]:
                usd, basis = g["ticks"] / 1e10, "measured (vendor cost_in_usd_ticks; the recorded price-table " \
                                                 f"estimate was ${g['usd']:.4f})"
            else:
                usd, basis = g["usd"], "measured (per call)"
            rows.append({"vendor": v, "source": f"A/B {os.path.basename(os.path.dirname(path))} ({role})",
                         "backend": b, "calls": g["calls"], "usd": round(usd, 4), "basis": basis})
    for path in sorted(glob.glob(os.path.join(REPO, "data/editorial/ingest/flagcheck/**/attempts.jsonl"),
                              recursive=True)):              # ruling 40: the flag check and option A's dry run
        agg = {}
        for line in open(path):
            r = json.loads(line)
            if r.get("kind") == "cache":
                continue
            g = agg.setdefault(r["backend"], {"calls": 0, "usd": 0.0})
            g["calls"] += 1
            g["usd"] += r.get("cost_usd") or 0.0
        rel = os.path.relpath(os.path.dirname(path), os.path.join(REPO, "data/editorial/ingest/flagcheck"))
        for b, g in agg.items():
            rows.append({"vendor": vendor_of(b), "source": f"ruling 40 flag check {rel}", "backend": b,
                         "calls": g["calls"], "usd": round(g["usd"], 6), "basis": "measured (per call)"})
    root = os.path.join(REPO, "docs/audits/parallel/pp-ingest_audit")
    for path in sorted(glob.glob(os.path.join(root, "**", "results.json"), recursive=True)):
        c = os.path.relpath(os.path.dirname(path), root)
        j = json.load(open(path))
        failed = list((j.get("error_costs") or {}).items()) + [
            (e["reviewer"], e["error_cost"]) for e in j.get("earlier_attempts") or [] if e.get("error_cost")]
        for rid, ec in failed:                         # a failed call is spend too (usage.cost when the gateway sent it)
            rows.append({"vendor": vendor_of(rid),
                         "source": f"audit {c} (failed: {ec.get('kind')})", "backend": rid, "calls": 1,
                         "usd": round(ec.get("cost_usd") or 0.0, 4),
                         "basis": "measured (usage.cost of the failed reply)" if ec.get("cost_usd") is not None
                         else "UNMEASURED (no usage returned)"})
        for rid, r in j["results"].items():
            v, u = vendor_of(rid), r.get("usage") or {}
            if v == "xai" and isinstance(u.get("cost_in_usd_ticks"), (int, float)):
                usd, basis = u["cost_in_usd_ticks"] / 1e10, "measured (vendor cost_in_usd_ticks)"
            elif v in LIST:
                pi, po = LIST[v]
                usd = (u.get("prompt_tokens", 0) * pi + u.get("completion_tokens", 0) * po) / 1e6
                basis = f"ESTIMATE (usage x list price ${pi}/${po} per MTok)"
            else:
                usd, basis = r.get("cost_usd") or 0.0, "measured (usage.cost)"
            rows.append({"vendor": v, "source": f"audit {c}", "backend": rid, "calls": 1, "usd": round(usd, 4),
                         "basis": basis, "usage": {k: u.get(k) for k in ("prompt_tokens", "completion_tokens")}})
    # unsaved usage: estimated from the same-size calls (marked)
    rows += [
        {"vendor": "xai", "source": "audit c1 (usage not saved)", "backend": "grok", "calls": 1, "usd": 0.09,
         "basis": "ESTIMATE (= the c2 call: same package size)"},
        {"vendor": "google", "source": "audit c1 (usage not saved)", "backend": "gemini", "calls": 1, "usd": 0.35,
         "basis": "ESTIMATE (~80k prompt + ~16k output at $2/$12)"},
        {"vendor": "openai", "source": "audit c1 (usage not saved)", "backend": "gpt4o", "calls": 1, "usd": 0.18,
         "basis": "ESTIMATE (~67k prompt + ~1.2k output at $2.50/$10)"},
        {"vendor": "heimdall", "source": "freeze audit c1, first run: glm + minimax empty, muse timed out (usage not "
         "saved by the driver then)", "backend": "heimdall_glm/minimax/muse", "calls": 3, "usd": 0.05,
         "basis": "UPPER BOUND (111k prompt + 16k output each at the gateway's listed prices)"},
        {"vendor": "heimdall", "source": "audit c1 deepseek, 2 empty replies (usage not saved)",
         "backend": "heimdall_deepseek", "calls": 2, "usd": 0.08, "basis": "UPPER BOUND (73k prompt + 16k output "
         "each at the config's estimate $0.3/$1.2)"},
        {"vendor": "anthropic", "source": "one-window proof 03:0x ET (STATE 03:31)", "backend": "anthropic_frontier",
         "calls": 1, "usd": 0.028, "basis": "measured, printed to the terminal (not in a file)"},
        {"vendor": "heimdall", "source": "one-window proof 03:0x ET (STATE 03:31)", "backend": "heimdall_qwen27b",
         "calls": 1, "usd": 0.0008, "basis": "measured, printed to the terminal (not in a file)"},
        {"vendor": "xai", "source": "one-window proof 03:0x ET", "backend": "xai_frontier", "calls": 1, "usd": 0.02,
         "basis": "ESTIMATE (2,371 prompt / 9,697 total tokens at the per-token rate of the measured judge calls)"},
        {"vendor": "google", "source": "one-window proof 03:0x ET (truncated at 4,000 tokens)",
         "backend": "gemini_frontier", "calls": 1, "usd": 0.05, "basis": "ESTIMATE (~2.4k + 4k tokens at $2/$12)"},
        {"vendor": "heimdall", "source": "ruling 40: the check's smoke, 2 rows x 3 questions (Nov 13 03:2x ET)",
         "backend": "heimdall_glm53flash", "calls": 6, "usd": 0.000137,
         "basis": "measured (usage.cost of each reply; printed, scratch run)"},
        {"vendor": "heimdall", "source": "ruling 40: choosing the checker, 24 quotes x 4 configurations (Nov 13 "
         "03:3x ET)", "backend": "heimdall_glm53flash/heimdall_muse", "calls": 96, "usd": 0.003662,
         "basis": "measured (usage.cost of each reply; printed, scratch run)"},
        {"vendor": "heimdall", "source": "ruling 40: option A dry run's smoke, 1 window x 2 arms (Nov 13 03:3x ET)",
         "backend": "heimdall_qwen27b", "calls": 2, "usd": 0.001315,
         "basis": "measured (usage.cost of each reply; scratch run)"},
    ]
    tot = {}
    for r in rows:
        t = tot.setdefault(r["vendor"], {"usd": 0.0, "estimated_usd": 0.0, "calls": 0})
        t["usd"] = round(t["usd"] + r["usd"], 4)
        t["calls"] += r["calls"] or 0
        if not r["basis"].startswith("measured"):
            t["estimated_usd"] = round(t["estimated_usd"] + r["usd"], 4)
    res = {"totals": tot, "total_usd": round(sum(t["usd"] for t in tot.values()), 2), "rows": rows}
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res["totals"], indent=1), res["total_usd"])


if __name__ == "__main__":
    main()
