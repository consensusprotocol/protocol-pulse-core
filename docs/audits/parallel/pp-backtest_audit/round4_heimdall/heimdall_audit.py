"""Two-cycle audit on Heimdall reviewers only (orchestrator spend freeze, 05:30 ET: no paid vendor).
Cycle 1: each Heimdall back-end reviews the package (its question + diff) and returns findings in a schema.
Cycle 2: each back-end sees the package and EVERY cycle-1 finding and rules CONFIRMED / REFUTED / UNSURE on each, with
evidence, and may add what all of them missed. Consensus is computed here, without a model: a cycle-1 finding is
consensus when at least 2 back-ends CONFIRMED it in cycle 2. A reply that is empty, cut or malformed is NOT MEASURED.
Heimdall's per-call cost goes to this run's own ledger. Usage: heimdall_audit.py OUT_DIR PACKAGE[:NAME] ..."""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/home/ultron/worktrees/pp-backtest")
from pipeline.oracle import llm, providers as PV  # noqa: E402

BACKENDS = ["heimdall-deepseek-v4.1-flash", "heimdall-glm-5.3-flash", "heimdall-qwen3.8-27b"]
FINDING = {"type": "object", "additionalProperties": False, "required": ["severity", "where", "evidence", "defect", "fix"],
           "properties": {"severity": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                          "where": {"type": "string"}, "evidence": {"type": "string"}, "defect": {"type": "string"},
                          "fix": {"type": "string"}}}
C1 = {"type": "object", "additionalProperties": False, "required": ["findings", "verdict"],
      "properties": {"findings": {"type": "array", "items": FINDING}, "verdict": {"type": "string"}}}
C2 = {"type": "object", "additionalProperties": False, "required": ["rulings", "missed", "verdict"],
      "properties": {"rulings": {"type": "array", "items": {
          "type": "object", "additionalProperties": False, "required": ["finding", "status", "why"],
          "properties": {"finding": {"type": "string"},
                         "status": {"type": "string", "enum": ["CONFIRMED", "REFUTED", "UNSURE"]},
                         "why": {"type": "string"}}}},
          "missed": {"type": "array", "items": FINDING}, "verdict": {"type": "string"}}}
SYSTEM = ("You are an independent senior code reviewer. Only state what you can verify from the package; quote the "
          "evidence (file and line); if uncertain, say so. Keep each finding short. Return only the JSON object.")


def ask(name, user, schema, ledger, tag):
    try:
        text, raw, row = PV.call_backend(name, SYSTEM, user, schema, ledger, tag)
        return {"backend": name, "ok": True, "reply": json.loads(text), "usd": row["usd"], "seconds": row["seconds"],
                "tokens_in": row["tokens_in"], "tokens_out": row["tokens_out"]}
    except Exception as e:                          # empty / cut / malformed / vendor error: NOT MEASURED
        return {"backend": name, "ok": False, "error": llm.redact(f"{type(e).__name__}: {e}")[:300]}


def audit(out_dir, package, name):
    os.makedirs(out_dir, exist_ok=True)
    ledger = llm.Ledger(os.path.join(out_dir, "AUDIT_SPEND.jsonl"), cap=2.0)
    pkg = open(package, encoding="utf-8").read()
    with ThreadPoolExecutor(3) as ex:
        c1 = list(ex.map(lambda b: ask(b, pkg, C1, ledger, f"audit {name} c1 {b}"), BACKENDS))
    found = []
    for r in c1:
        for k, f in enumerate((r["reply"]["findings"] if r["ok"] else []), 1):
            found.append(dict(f, id=f"{r['backend'].split('-')[1]}#{k}", by=r["backend"]))
    listing = "\n".join(f"[{f['id']}] {f['severity']} {f['where']}: {f['defect']} (evidence: {f['evidence'][:300]})"
                        for f in found) or "(no cycle-1 findings)"
    c2_user = (pkg + "\n\nCYCLE 2. Independent reviewers made the findings below on THIS package. For EACH one, rule "
               "CONFIRMED (the defect is real, shown by the code quoted), REFUTED (the code shows it is not a defect: "
               "say where) or UNSURE, with a short why; use the id in brackets as 'finding'. Then list under 'missed' "
               "any real defect all of them missed.\n\nFINDINGS\n" + listing)
    with ThreadPoolExecutor(3) as ex:
        c2 = list(ex.map(lambda b: ask(b, c2_user, C2, ledger, f"audit {name} c2 {b}"), BACKENDS))
    votes = {f["id"]: {"CONFIRMED": [], "REFUTED": [], "UNSURE": []} for f in found}
    for r in c2:
        for x in (r["reply"]["rulings"] if r["ok"] else []):
            if x["finding"].strip("[] ") in votes:
                votes[x["finding"].strip("[] ")][x["status"]].append(r["backend"])
    consensus = [dict(f, confirmed_by=votes[f["id"]]["CONFIRMED"], refuted_by=votes[f["id"]]["REFUTED"])
                 for f in found if len(votes[f["id"]]["CONFIRMED"]) >= 2]
    rec = {"package": name, "cycle1": c1, "cycle2": c2, "findings": found, "votes": votes, "consensus": consensus,
           "spent_usd": ledger.spent()}
    with open(os.path.join(out_dir, f"HEIMDALL_AUDIT_{name}.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, default=str)
    lines = [f"# Heimdall-only audit, package {name} (spend freeze 05:30 ET; reviewers: {', '.join(BACKENDS)})", "",
             "| cycle | back-end | measured | findings / rulings | verdict | s | USD |", "|---|---|---|---|---|---|---|"]
    for cyc, rs in (("1", c1), ("2", c2)):
        for r in rs:
            n = (len(r["reply"]["findings"]) if cyc == "1" else len(r["reply"]["rulings"])) if r["ok"] else "-"
            lines.append(f"| {cyc} | {r['backend']} | {'yes' if r['ok'] else 'NOT MEASURED: ' + r['error'][:120]} | "
                         f"{n} | {(r['reply']['verdict'][:160] if r['ok'] else '-')} | {r.get('seconds', '-')} | "
                         f"{r.get('usd', '-')} |")
    lines += ["", f"Consensus (CONFIRMED by >= 2 of the 3 in cycle 2): {len(consensus)} of {len(found)} cycle-1 findings.",
              ""]
    for f in consensus:
        lines += [f"## {f['id']} {f['severity']}: {f['where']}", f"- Defect: {f['defect']}", f"- Evidence: {f['evidence']}",
                  f"- Fix: {f['fix']}", f"- Confirmed by: {', '.join(f['confirmed_by'])}; refuted by: "
                  f"{', '.join(f['refuted_by']) or 'none'}", ""]
    lines += ["## Every cycle-1 finding and its cycle-2 votes", ""]
    for f in found:
        v = votes[f["id"]]
        lines.append(f"- [{f['id']}] {f['severity']} {f['where']}: {f['defect'][:220]} -- confirmed "
                     f"{len(v['CONFIRMED'])}, refuted {len(v['REFUTED'])}, unsure {len(v['UNSURE'])}")
    missed = [(r["backend"], m) for r in c2 if r["ok"] for m in r["reply"]["missed"]]
    if missed:
        lines += ["", "## Added in cycle 2 (one reviewer each; not consensus)", ""]
        lines += [f"- {b}: {m['severity']} {m['where']}: {m['defect'][:220]}" for b, m in missed]
    with open(os.path.join(out_dir, f"HEIMDALL_AUDIT_{name}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(name, "cycle1 measured", sum(r["ok"] for r in c1), "cycle2 measured", sum(r["ok"] for r in c2),
          "findings", len(found), "consensus", len(consensus), "spent", ledger.spent(), flush=True)


if __name__ == "__main__":
    out = sys.argv[1]
    for spec in sys.argv[2:]:
        path, _, name = spec.partition(":")
        audit(out, path, name or os.path.basename(path))
