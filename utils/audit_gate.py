#!/usr/bin/env python3
"""
PROTOCOL PULSE — AUDIT GATE
Enforces: build → audit → fix → merge. No exceptions.

Usage:
  python3 audit_gate.py --session session3-media      # audit one session
  python3 audit_gate.py --session all-pending          # audit all committed but unmerged sessions
  python3 audit_gate.py --merge-all                    # merge all audit-passed branches to main

The gate will REFUSE to merge any branch that has not passed audit.
Audit pass = FINAL_CONSENSUS.md exists AND no P0 CRITICAL items remain.
"""

import os, sys, json, subprocess, argparse, time
from pathlib import Path
from datetime import datetime

BASE   = Path.home() / "protocol_pulse"
AUDITS = BASE / "docs/audits"

SESSION_FEATURES = [
    "session1-terminal",
    "session2-newsletter",
    "session3-media",
    "session4-charts",
    "session5-mining",
    "session6-schiff",
    "session7-oracle",
    "session8-nostr",
    "session9-nodes",
    "session10-articles",
]

def run(cmd, cwd=None, capture=True):
    r = subprocess.run(cmd, shell=True, cwd=cwd or BASE,
                       capture_output=capture, text=True)
    return r.stdout.strip() if capture else r.returncode

def branch_has_commit(branch):
    return bool(run(f"git log main..{branch} --oneline 2>/dev/null"))

def audit_passed(feature):
    """Returns True if audit is complete with no P0s remaining."""
    consensus = AUDITS / feature / "FINAL_CONSENSUS.md"
    if not consensus.exists():
        return False, "No audit report found"
    text = consensus.read_text()
    p0_lines = [l for l in text.split("\n") if l.strip().startswith("P0 CRITICAL")]
    if p0_lines:
        return False, f"{len(p0_lines)} P0 issues unresolved:\n" + "\n".join(p0_lines[:3])
    return True, "PASSED"

def run_audit(feature):
    """Fire the cross-LLM audit for a feature."""
    print(f"\n{'='*60}")
    print(f"RUNNING AUDIT: {feature}")
    print(f"{'='*60}")
    
    # Load .env
    env_path = BASE / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    
    os.environ.update(env)
    
    cmd = f"python3 utils/cross_llm_audit.py --feature {feature}"
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=BASE)
    return result.returncode == 0

def merge_branch(feature):
    """Merge a passed branch to main."""
    from cross_llm_audit import FEATURE_MAP
    if feature not in FEATURE_MAP:
        print(f"  ⚠️  {feature} not in FEATURE_MAP")
        return False
    _, branch = FEATURE_MAP[feature]
    print(f"\n  MERGING: {branch} → main")
    run("git checkout main", capture=False)
    run("git pull", capture=False)
    result = subprocess.run(f"git merge {branch} --no-edit", 
                           shell=True, cwd=BASE)
    if result.returncode != 0:
        print(f"  ❌ MERGE FAILED — resolve conflicts manually")
        return False
    run("git push", capture=False)
    print(f"  ✅ MERGED: {branch}")
    return True

def status_report():
    """Print full pipeline status."""
    print(f"\n{'='*70}")
    print(f"PROTOCOL PULSE — PIPELINE STATUS  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")
    print(f"{'SESSION':<28} {'BRANCH COMMIT':<14} {'AUDIT':<14} {'MERGE STATUS'}")
    print(f"{'-'*70}")
    
    sys.path.insert(0, str(BASE / "utils"))
    from cross_llm_audit import FEATURE_MAP
    
    for feat in SESSION_FEATURES:
        if feat not in FEATURE_MAP:
            continue
        _, branch = FEATURE_MAP[feat]
        
        has_commit = branch_has_commit(branch)
        passed, msg = audit_passed(feat)
        merged = not bool(run(f"git log main..{branch} --oneline 2>/dev/null"))
        
        commit_icon = "✅" if has_commit else "⏳ building"
        audit_icon  = "✅ PASSED" if passed else ("❌ " + msg[:20] if "No audit" not in msg else "⏳ pending")
        merge_icon  = "✅ LIVE" if merged else "⏳ queued"
        
        print(f"{feat:<28} {commit_icon:<14} {audit_icon:<22} {merge_icon}")
    
    print(f"{'='*70}")
    print("\nNEXT ACTIONS:")
    pending_audit = [f for f in SESSION_FEATURES 
                    if f in FEATURE_MAP 
                    and branch_has_commit(FEATURE_MAP[f][1])
                    and not audit_passed(f)[0]]
    if pending_audit:
        print(f"  Run audit on: {', '.join(pending_audit)}")
        print(f"  Command: python3 utils/audit_gate.py --session all-pending")
    
    passed_unmerged = [f for f in SESSION_FEATURES
                      if f in FEATURE_MAP
                      and audit_passed(f)[0]
                      and bool(run(f"git log main..{FEATURE_MAP[f][1]} --oneline 2>/dev/null"))]
    if passed_unmerged:
        print(f"  Ready to merge: {', '.join(passed_unmerged)}")
        print(f"  Command: python3 utils/audit_gate.py --merge-all")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", help="Feature to audit (or 'all-pending')")
    parser.add_argument("--merge-all", action="store_true", help="Merge all audit-passed branches")
    parser.add_argument("--status", action="store_true", help="Print pipeline status")
    args = parser.parse_args()
    
    # Always load .env
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    
    sys.path.insert(0, str(BASE / "utils"))
    
    if args.status or (not args.session and not args.merge_all):
        status_report()
    
    elif args.session == "all-pending":
        from cross_llm_audit import FEATURE_MAP
        pending = [f for f in SESSION_FEATURES
                  if f in FEATURE_MAP
                  and branch_has_commit(FEATURE_MAP[f][1])
                  and not audit_passed(f)[0]]
        print(f"\nAuditing {len(pending)} pending sessions: {pending}")
        for feat in pending:
            run_audit(feat)
            time.sleep(5)  # rate limit buffer between features
        status_report()
    
    elif args.session:
        run_audit(args.session)
        status_report()
    
    elif args.merge_all:
        from cross_llm_audit import FEATURE_MAP
        passed = [f for f in SESSION_FEATURES
                 if f in FEATURE_MAP
                 and audit_passed(f)[0]
                 and bool(run(f"git log main..{FEATURE_MAP[f][1]} --oneline 2>/dev/null"))]
        print(f"\nMerging {len(passed)} audit-passed branches: {passed}")
        for feat in passed:
            merge_branch(feat)
        run("./regression_test.sh", capture=False)
        print("\n✅ MERGE SPRINT COMPLETE")
