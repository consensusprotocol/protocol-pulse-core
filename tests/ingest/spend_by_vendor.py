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

  python3 tests/ingest/spend_by_vendor.py --smoke <scratch smoke store> --out <json>
"""
import argparse
import glob
import json
import os
import sqlite3

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENDOR = {"anthropic_frontier": "anthropic", "heimdall_qwen27b": "heimdall", "heimdall_deepseek": "heimdall",
          "heimdall_qwen": "heimdall", "xai_frontier": "xai", "grok": "xai", "gemini_frontier": "google",
          "gemini": "google", "gpt4o": "openai"}
LIST = {"google": (2.0, 12.0), "openai": (2.5, 10.0)}


def queue_rows(path, source, out):
    if not os.path.exists(path):
        return
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    for b, n, usd, mn, mx in db.execute("SELECT backend, SUM(kind!='cache'), SUM(COALESCE(cost_usd,0)), MIN(at), "
                                        "MAX(at) FROM calls GROUP BY backend"):
        out.append({"vendor": VENDOR.get(b, b), "source": source, "backend": b, "calls": n, "usd": round(usd, 4),
                    "basis": "measured (per call)", "first": mn, "last": mx})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", help="the scratch smoke store (03:0x ET)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = []
    queue_rows(os.path.join(REPO, "data/editorial/ingest/queue.sqlite"), "watcher (live; Anthropic: the 08:36-08:43 UTC "
               "outage drill only)", rows)
    if a.smoke:
        queue_rows(os.path.join(a.smoke, "ingest/queue.sqlite"), "smoke (scratch store, 03:2x ET)", rows)
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
            v = VENDOR.get(b, b)
            if v == "xai" and g["ticks_calls"] == g["calls"]:
                usd, basis = g["ticks"] / 1e10, "measured (vendor cost_in_usd_ticks; the recorded price-table " \
                                                 f"estimate was ${g['usd']:.4f})"
            else:
                usd, basis = g["usd"], "measured (per call)"
            rows.append({"vendor": v, "source": f"A/B {os.path.basename(os.path.dirname(path))} ({role})",
                         "backend": b, "calls": g["calls"], "usd": round(usd, 4), "basis": basis})
    for c in ("c1", "c2"):
        j = json.load(open(os.path.join(REPO, f"docs/audits/parallel/pp-ingest_audit/{c}/results.json")))
        for rid, r in j["results"].items():
            v, u = VENDOR.get(rid, rid), r.get("usage") or {}
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
