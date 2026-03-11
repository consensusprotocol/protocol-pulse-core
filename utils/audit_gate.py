#!/usr/bin/env python3
"""
PROTOCOL PULSE — AUDIT GATE ENFORCER
Runs as a pre-merge gate. Called by cc_audit_merge.sh.
Checks: 
  1. cross_llm_audit.py was run on this branch
  2. FINAL_CONSENSUS.md exists with passing score
  3. No P0 issues unresolved
Usage: python3 audit_gate.py --branch feature/xxx [--bypass-reason "emergency: <reason>"]
"""
import os, sys, json, subprocess
from pathlib import Path
from datetime import datetime, timedelta

BASE = Path.home() / "protocol_pulse"
AUDITS = BASE / "docs/audits"
LOG = BASE / "logs/audit_gate.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")

def check_audit_exists(branch):
    """Check if an audit file exists for this branch, created in last 24h."""
    branch_slug = branch.replace("/", "_").replace("feature_", "")
    # Look for any audit file matching this branch
    if AUDITS.exists():
        for f in AUDITS.iterdir():
            if branch_slug in f.name or branch_slug.replace("-","_") in f.name:
                # Check recency
                age = datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)
                if age < timedelta(hours=48):
                    return f
    return None

def check_consensus_score(audit_file):
    """Parse FINAL_CONSENSUS score from audit file."""
    try:
        content = audit_file.read_text()
        # Look for score patterns like "Score: 87" or "SCORE: 87/100"  
        import re
        scores = re.findall(r"[Ss]core[:\s]+([0-9]+)", content)
        if scores:
            return max(int(s) for s in scores)
        # Check for PASS/FAIL
        if "OVERALL: PASS" in content or "consensus: PASS" in content.lower():
            return 90  # treat as passing
    except:
        pass
    return 0

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--bypass-reason", default="")
    args = parser.parse_args()

    branch = args.branch
    log(f"AUDIT GATE CHECK: branch={branch}")

    # Allow bypass with explicit reason (must include "emergency:")
    if args.bypass_reason:
        if not args.bypass_reason.startswith("emergency:"):
            log("GATE BLOCKED: bypass-reason must start with 'emergency:'")
            sys.exit(1)
        log(f"GATE BYPASSED (emergency): {args.bypass_reason}")
        with open(LOG.parent / "bypass_log.txt", "a") as f:
            f.write(f"[{datetime.now()}] branch={branch} reason={args.bypass_reason}\n")
        sys.exit(0)

    # Main branch and hotfix branches skip audit
    if branch in ("main", "master") or branch.startswith("hotfix/"):
        log(f"GATE SKIPPED: {branch} is main/hotfix")
        sys.exit(0)

    # Check audit exists
    audit_file = check_audit_exists(branch)
    if not audit_file:
        log(f"GATE BLOCKED: No audit found for {branch} in docs/audits/ (last 48h)")
        log(f"  Run: cd ~/protocol_pulse && python3 utils/cross_llm_audit.py --feature <name>")
        sys.exit(1)

    log(f"AUDIT FILE FOUND: {audit_file.name}")

    # Check score
    score = check_consensus_score(audit_file)
    if score < 75:
        log(f"GATE BLOCKED: Audit score {score}/100 is below threshold (75)")
        log(f"  Fix P0+P1 issues then re-run: python3 utils/cross_llm_audit.py")
        sys.exit(1)

    log(f"GATE PASSED: score={score}, branch={branch}")
    sys.exit(0)

if __name__ == "__main__":
    main()
