#!/usr/bin/env python3
"""
CONVERGENCE DETECTION — CROSS-LLM COMPETITIVE AUDIT
Protocol Pulse Intelligence Terminal · Phase 2 · Feature 1

Runs a dedicated 8-question architectural audit against GPT-4o + Grok (parallel),
then Cycle 2 cross-examination, then Claude synthesis → spec output.

Gemini key needs rotation — skipped for this audit.

Usage:
    python3 utils/convergence_audit.py

Requirements in .env:
    OPENAI_API_KEY=...
    XAI_API_KEY=...
    ANTHROPIC_API_KEY=...

Created: 2026-03-23
"""

import os, sys, json, time, threading
from pathlib import Path
from datetime import datetime, timezone

# ─── PATHS ───────────────────────────────────────────────────────────────────
BASE = Path.home() / "protocol_pulse"
AUDITS = BASE / "docs" / "audits"
PHASE2 = BASE / "docs" / "phase2"
AUDIT_OUT = AUDITS / "convergence-detection"
AUDIT_OUT.mkdir(parents=True, exist_ok=True)

# ─── LOAD .env ───────────────────────────────────────────────────────────────
env_path = BASE / ".env"
if env_path.exists():
    for line in env_path.read_text().split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

# ─── LOAD CONTEXT FILES ─────────────────────────────────────────────────────
def _read(path: str) -> str:
    p = BASE / path
    if p.exists():
        return p.read_text()
    return f"(file not found: {path})"

FOUNDATION_DOC = _read("docs/phase2/convergence_detection_foundation.md")
SENTINEL_PY = _read("services/sentinel.py")
INTELLIGENCE_BP = _read("core/blueprints/intelligence.py")
INTEL_SPEC = _read("docs/intelligence_terminal_v1_spec.md")

# ─── THE BRIEF ──────────────────────────────────────────────────────────────
CYCLE1_BRIEF = f"""You are the senior architect at Protocol Pulse, the most sophisticated autonomous
Bitcoin intelligence platform ever built. You are reviewing the Convergence Detection
feature — the Matrix Layer — before a single line of code is written.

Your mandate: make this bulletproof. Find every flaw. Challenge every assumption.
The other model is reviewing the same spec right now and will challenge your answers.

The spec defines a multi-signal convergence detection engine that watches 5 named
patterns simultaneously across on-chain, social, and macro data. It must detect
when multiple signals align within sub-60-second latency and fire WATCH/CRITICAL
alerts that are accurate enough to make Bloomberg subscribers cancel.

---

## FOUNDATION DOCUMENT (the full spec under review)

{FOUNDATION_DOC}

---

## EXISTING SENTINEL DAEMON (services/sentinel.py — this is the codebase it integrates into)

{SENTINEL_PY}

---

## INTELLIGENCE BLUEPRINT (core/blueprints/intelligence.py — the API/SSE layer)

{INTELLIGENCE_BP}

---

## INTELLIGENCE TERMINAL V1 SPEC (the product spec — Convergence Monitor is top-right panel)

{INTEL_SPEC[:8000]}

---

Now answer ALL 8 QUESTIONS with maximum specificity and technical depth.
For each question, cite specific signals, patterns, data sources, and code paths.
Do not give generic answers. Every recommendation must be implementable.

QUESTION 1 — SIGNAL DESIGN:
Are these 5 patterns and their signal sets the right ones? What's missing? What's
weak? Which specific signals within each pattern are too noisy to be reliable at
the data quality available from free/semi-public APIs? Give signal-level verdicts.

QUESTION 2 — FALSE POSITIVE KILL RATE:
Design the specific guard rails for each pattern that prevent false positives.
Consider: crypto market volatility (gold and DXY move all the time — that doesn't
mean safe-haven rotation). Time-of-day effects (Asian session vs US open).
Exchange flow noise (coins moving between exchange wallets, not leaving exchanges).
What minimum confirmation windows, signal persistence requirements, and
cross-validation rules make each pattern reliable enough to wake someone up?

QUESTION 3 — DATA DEPENDENCY AUDIT:
Rank all 25 signals (5 per pattern) by data reliability risk. Grade each:
  A — reliable, free, well-documented API
  B — workable but requires fallback
  C — brittle, likely to fail, needs alternative design
For every C-grade signal: propose a concrete alternative that achieves the same
detection goal with better data.

QUESTION 4 — TRANSFORMER VS RULE-BASED:
The original spec says "transformer-based." The foundation doc leans toward a
deterministic rule-based state machine (boolean signals → pattern matching).
Which is correct for Phase 2? Argue for the approach you believe will ship
faster, be more debuggable, and perform better given the data available.
Be specific about what a transformer would actually learn vs what it would
overfit. Give a concrete decision recommendation.

QUESTION 5 — LATENCY AUDIT:
Signals update at wildly different rates:
  - Mempool: 1 second
  - Sentiment: 30 seconds
  - On-chain derived: per block (~10 min)
  - ETF flows: 6 hours (if custodian wallet monitoring)
  - DXY/Gold: 1 minute (API)
Design the state machine evaluation logic that handles mixed-frequency signals
correctly. When a 1-second mempool spike fires but the 6-hour ETF signal hasn't
updated in 4 hours, how should the engine weight them? Give concrete logic.

QUESTION 6 — FRONTEND CHALLENGE:
The Convergence Monitor panel must be the most compelling panel in any financial
terminal. Not the prettiest — the most information-dense and actionable.
Design the exact information architecture of the panel: every element, every
state (empty/forming/watching/critical/resolved), every interaction.
What is the specific visual moment that makes a professional trader screenshot
this and post it to X? Give a pixel-level description.

QUESTION 7 — 6TH PATTERN:
What is the 6th convergence pattern that should be in the V1 library?
It must be: (a) detectable with the data sources available, (b) genuinely
unprecedented — not just a variant of the 5 existing patterns, (c) something
that would make a serious Bitcoin operator say "I can't believe no terminal
built this before." Name it, define its signal set (5 signals), give the
WATCH and CRITICAL thresholds. Make it better than anything the other model proposes.

QUESTION 8 — INTEGRATION HARDENING:
The convergence engine reads from SentinelState which is written to
/tmp/sentinel_state.json every 5 seconds by an asyncio daemon. Flask SSE stream
reads this file every 2 seconds. Where are the specific race conditions, data
freshness failures, stale signal propagation bugs, and edge cases that will
cause the Convergence Monitor panel to show wrong data? List every failure mode.
Then design the hardening that prevents each one.
"""

# ─── CYCLE 2 CROSS-EXAMINATION TEMPLATE ─────────────────────────────────────
def build_cycle2_prompt(model_name: str, own_c1: str, other_name: str, other_c1: str) -> str:
    return f"""# CONVERGENCE DETECTION — CYCLE 2 CROSS-EXAMINATION
# Protocol Pulse Intelligence Terminal · Phase 2 · Feature 1
# You are: {model_name}. The other model is: {other_name}.

## YOUR CYCLE 1 ANSWERS
{own_c1[:12000]}

## {other_name.upper()}'s CYCLE 1 ANSWERS
{other_c1[:12000]}

---

## CROSS-EXAMINATION INSTRUCTIONS

You've now seen what {other_name} said. This is your final review.

1. Identify the single most valuable insight from {other_name}'s response that
   you missed or underweighted. Be specific about why it matters.

2. Challenge the weakest recommendation from {other_name}'s response —
   specifically and technically. Explain why it won't work or is suboptimal.

3. Propose the DEFINITIVE answer to Question 4 (transformer vs rule-based)
   based on BOTH models' arguments combined. This must be a clear,
   implementable decision with zero ambiguity.

4. For Question 7 (6th pattern): evaluate both proposals.
   Pick a winner OR synthesize a better third option that combines the
   strongest elements of both. Define its complete signal set.

5. Name one failure mode in Question 8 that NEITHER model caught in Cycle 1.
   This should be a genuine integration risk, not a trivial edge case.

6. Give your FINAL revised answers for all 8 questions, incorporating
   everything you've learned from the cross-examination. Be concise but complete.
"""


# ─── LLM CALLERS ────────────────────────────────────────────────────────────

def call_gpt4o(prompt: str, results: dict, errors: dict):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=12000,
            temperature=0.3,
        )
        results["gpt4o"] = resp.choices[0].message.content
        print(f"  [GPT-4o] Done ({len(results['gpt4o']):,} chars)")
    except Exception as e:
        errors["gpt4o"] = str(e)
        print(f"  [GPT-4o] ERROR: {e}")

def call_grok(prompt: str, results: dict, errors: dict):
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url="https://api.x.ai/v1"
        )
        resp = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=12000,
            temperature=0.3,
        )
        results["grok"] = resp.choices[0].message.content
        print(f"  [GROK]   Done ({len(results['grok']):,} chars)")
    except Exception as e:
        errors["grok"] = str(e)
        print(f"  [GROK]   ERROR: {e}")

def fire_both(prompt: str) -> tuple:
    results, errors = {}, {}
    threads = [
        threading.Thread(target=call_gpt4o, args=(prompt, results, errors)),
        threading.Thread(target=call_grok,  args=(prompt, results, errors)),
    ]
    for t in threads: t.start()
    for t in threads: t.join()
    return results, errors


def claude_synthesize(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=12000,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


# ─── MAIN ───────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*70}")
    print(f"CONVERGENCE DETECTION — CROSS-LLM COMPETITIVE AUDIT")
    print(f"Protocol Pulse Intelligence Terminal · Phase 2 · Feature 1")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # Verify keys
    missing = [k for k in ["OPENAI_API_KEY", "XAI_API_KEY", "ANTHROPIC_API_KEY"]
               if not os.environ.get(k)]
    if missing:
        print(f"MISSING API KEYS: {missing}")
        sys.exit(1)
    print("All API keys present\n")

    # ═══════════════════════════════════════════════════════════════════════
    #  CYCLE 1 — GPT-4o + Grok in parallel
    # ═══════════════════════════════════════════════════════════════════════
    print("── CYCLE 1: FIRING GPT-4o + Grok IN PARALLEL ──────────────────────")
    c1_results, c1_errors = fire_both(CYCLE1_BRIEF)

    for name, text in c1_results.items():
        (AUDIT_OUT / f"C1_{name.upper()}.md").write_text(text)
    for name, err in c1_errors.items():
        (AUDIT_OUT / f"C1_{name.upper()}.md").write_text(f"FAILED: {err}")

    print(f"\n  Cycle 1: {list(c1_results.keys())} succeeded, {list(c1_errors.keys())} failed\n")

    if len(c1_results) < 2:
        print("Need at least 2 models for cross-examination. Saving C1 and exiting.")
        sys.exit(1)

    # ═══════════════════════════════════════════════════════════════════════
    #  CYCLE 2 — Cross-examination
    # ═══════════════════════════════════════════════════════════════════════
    print("── CYCLE 2: CROSS-EXAMINATION ──────────────────────────────────────")

    c2_results, c2_errors = {}, {}

    # GPT-4o sees Grok's C1, Grok sees GPT-4o's C1
    c2_prompts = {}
    if "gpt4o" in c1_results and "grok" in c1_results:
        c2_prompts["gpt4o"] = build_cycle2_prompt("GPT-4o", c1_results["gpt4o"], "Grok", c1_results["grok"])
        c2_prompts["grok"] = build_cycle2_prompt("Grok", c1_results["grok"], "GPT-4o", c1_results["gpt4o"])

    c2_threads = []
    if "gpt4o" in c2_prompts:
        c2_threads.append(threading.Thread(target=call_gpt4o, args=(c2_prompts["gpt4o"], c2_results, c2_errors)))
    if "grok" in c2_prompts:
        c2_threads.append(threading.Thread(target=call_grok, args=(c2_prompts["grok"], c2_results, c2_errors)))

    for t in c2_threads: t.start()
    for t in c2_threads: t.join()

    for name, text in c2_results.items():
        (AUDIT_OUT / f"C2_{name.upper()}.md").write_text(text)
    for name, err in c2_errors.items():
        (AUDIT_OUT / f"C2_{name.upper()}.md").write_text(f"FAILED: {err}")

    print(f"\n  Cycle 2: {list(c2_results.keys())} succeeded, {list(c2_errors.keys())} failed\n")

    # ═══════════════════════════════════════════════════════════════════════
    #  CLAUDE SYNTHESIS → AUDIT REPORT
    # ═══════════════════════════════════════════════════════════════════════
    print("── CLAUDE SYNTHESIS: AUDIT REPORT ──────────────────────────────────")

    synthesis_prompt = f"""You are synthesizing a 2-cycle cross-LLM architectural audit for
Protocol Pulse's Convergence Detection feature (Phase 2, Feature 1).

Two models (GPT-4o and Grok-3) independently answered 8 deep architecture questions
about the convergence detection engine, then cross-examined each other's answers.

## GPT-4o CYCLE 1
{c1_results.get('gpt4o', 'FAILED')[:10000]}

## GROK CYCLE 1
{c1_results.get('grok', 'FAILED')[:10000]}

## GPT-4o CYCLE 2 (after seeing Grok's C1)
{c2_results.get('gpt4o', 'FAILED')[:10000]}

## GROK CYCLE 2 (after seeing GPT-4o's C1)
{c2_results.get('grok', 'FAILED')[:10000]}

---

Produce a comprehensive audit report with these exact sections:

# CONVERGENCE DETECTION — CROSS-LLM AUDIT REPORT
# Protocol Pulse Intelligence Terminal · Phase 2 · Feature 1
# Date: {datetime.now().strftime('%Y-%m-%d')}
# Models: GPT-4o, Grok-3 (2 cycles each)
# Synthesized by: Claude Sonnet 4.6

## Q1 CONSENSUS: SIGNAL DESIGN
Synthesize both models' signal-level verdicts. For each of the 25 signals:
- Grade: STRONG / ACCEPTABLE / WEAK / REPLACE
- If WEAK or REPLACE: what's the specific fix?
- Any missing signals both models agree should be added?

## Q2 CONSENSUS: FALSE POSITIVE GUARD RAILS
For each of the 5 patterns, state the definitive guard rails:
- Minimum confirmation window
- Signal persistence requirement
- Cross-validation rules
- Time-of-day adjustments

## Q3 CONSENSUS: DATA DEPENDENCY GRADES
Table of all 25 signals with final A/B/C grade from combined analysis.
For every C-grade: the agreed replacement.

## Q4 DECISION: TRANSFORMER VS RULE-BASED
State the FINAL decision based on both models' arguments.
This is binding — no ambiguity allowed.

## Q5 CONSENSUS: MIXED-FREQUENCY STATE MACHINE
The definitive evaluation logic for handling signals at different update rates.
Include: signal freshness decay, staleness thresholds, weighting formula.

## Q6 CONSENSUS: FRONTEND PANEL SPEC
The winning panel design from both models' proposals.
Include: every element, every state, the "screenshot moment."

## Q7 WINNER: 6TH PATTERN
Evaluate both models' 6th pattern proposals.
Pick the winner or synthesize a better hybrid. Full signal set included.

## Q8 CONSENSUS: INTEGRATION HARDENING
Complete failure mode inventory from both cycles.
For each failure mode: the specific hardening fix.

## CONFLICTS
Where the models disagreed and your tiebreaker determination.

## UNANIMOUS STRENGTHS
What both models validated as already excellent in the spec.

## PRIORITY ACTION LIST
Every spec change needed, ordered by impact:
P0 CRITICAL | [change] | [which question] | [both models agree / tiebreaker]
P1 HIGH     | [change] | [which question] | [consensus level]
P2 MEDIUM   | [change] | [which question] | [consensus level]
"""

    audit_report = claude_synthesize(synthesis_prompt)
    audit_path = AUDITS / "convergence_audit_2026-03-23.md"
    audit_path.write_text(audit_report)
    print(f"  Audit report written: {audit_path} ({len(audit_report):,} chars)\n")

    # ═══════════════════════════════════════════════════════════════════════
    #  CLAUDE SYNTHESIS → V1 SPEC
    # ═══════════════════════════════════════════════════════════════════════
    print("── CLAUDE SYNTHESIS: V1 BUILD SPEC ────────────────────────────────")

    spec_prompt = f"""You are writing the FINAL, AUDIT-HARDENED build specification for
Protocol Pulse's Convergence Detection engine (Phase 2, Feature 1).

You have access to:
1. The original foundation document
2. A full cross-LLM audit report from GPT-4o and Grok-3 (2 cycles)

## ORIGINAL FOUNDATION DOCUMENT
{FOUNDATION_DOC}

## AUDIT REPORT (all findings synthesized)
{audit_report}

---

Write the complete, implementation-ready specification. This document will be
handed directly to the engineer who builds it. It must be unambiguous.

# CONVERGENCE DETECTION — V1 BUILD SPECIFICATION
# Protocol Pulse Intelligence Terminal · Phase 2 · Feature 1
# Date: {datetime.now().strftime('%Y-%m-%d')}
# Status: AUDIT-HARDENED — ready for implementation

Include ALL of the following sections:

## 1. EXECUTIVE SUMMARY
What this is, why it matters, what it replaces.

## 2. ARCHITECTURE DECISION: [TRANSFORMER / RULE-BASED]
The binding decision from Q4 with full justification.

## 3. FINAL PATTERN LIBRARY (6 PATTERNS)
For each pattern:
- Name and description
- Signal set (5 signals each) — with audit-hardened replacements for any C-grade signals
- WATCH threshold and CRITICAL threshold
- False positive guard rails (from Q2 consensus)
- Minimum confirmation window
- Signal persistence requirements

## 4. SIGNAL EXTRACTION LAYER
Complete signal dict with all 30 signals (6 patterns x 5).
For each: data source, update frequency, fallback, A/B/C grade.

## 5. MIXED-FREQUENCY STATE MACHINE
The evaluation loop design from Q5 consensus:
- Signal freshness decay logic
- Staleness thresholds per signal class
- Weighting formula
- Evaluation frequency (how often the engine runs)

## 6. DATA FEEDS
For each external data source needed:
- API endpoint
- Auth requirements
- Update frequency
- Fallback source
- Error handling

## 7. HISTORICAL BASELINE STORE
Schema, bootstrap values, update schedule.

## 8. CONVERGENCE EVENT LIFECYCLE
State diagram: FORMING → WATCH → CRITICAL → RESOLVED
Transition rules, escalation logic, dissolution logic.

## 9. ALERT DISPATCH
Alert copy templates, delivery channels, cooldown rules.

## 10. FRONTEND: CONVERGENCE MONITOR PANEL
From Q6 consensus — pixel-level spec:
- Layout within intelligence_terminal.html
- Every visual state (empty/forming/watch/critical/resolved)
- Animation and interaction specs
- The "screenshot moment"

## 11. INTEGRATION HARDENING CHECKLIST
From Q8 consensus — every failure mode and its fix:
- Race conditions
- Data freshness
- Stale signal propagation
- Edge cases

## 12. SSE STREAM ADDITIONS
What changes to /api/intelligence/stream for convergence data.

## 13. DATABASE SCHEMA
All new tables with CREATE TABLE statements.

## 14. FILE-LEVEL BUILD PLAN
Exactly what to create and modify, with line-count estimates.

## 15. TEST SUITE SPECIFICATION
What must pass before this feature merges:
- Unit tests per pattern
- Integration tests
- False positive verification
- Latency benchmarks
- Frontend render tests

## 16. SUCCESS CRITERIA (updated from foundation doc)
The final acceptance criteria incorporating audit findings.
"""

    v1_spec = claude_synthesize(spec_prompt)
    spec_path = PHASE2 / "convergence_detection_v1_spec.md"
    spec_path.write_text(v1_spec)
    print(f"  V1 spec written: {spec_path} ({len(v1_spec):,} chars)\n")

    # ═══════════════════════════════════════════════════════════════════════
    #  UPDATE AUDIT REGISTRY
    # ═══════════════════════════════════════════════════════════════════════
    try:
        rp = AUDITS / "AUDIT_REGISTRY.json"
        existing = json.loads(rp.read_text()) if rp.exists() else {}
        audits = [a for a in existing.get("audits", []) if a.get("feature") != "convergence-detection"]
        audits.append({
            "feature": "convergence-detection",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "models": ["gpt4o", "grok"],
            "type": "architectural_audit",
            "cycles": 2,
        })
        import subprocess
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(BASE), text=True).strip()
        rp.write_text(json.dumps({
            "last_audit": datetime.now(timezone.utc).isoformat(),
            "feature": "convergence-detection",
            "commit": sha,
            "audits": audits[-20:]
        }, indent=2))
        print(f"  AUDIT_REGISTRY.json updated\n")
    except Exception as e:
        print(f"  Warning: could not update registry: {e}\n")

    # ═══════════════════════════════════════════════════════════════════════
    #  DONE
    # ═══════════════════════════════════════════════════════════════════════
    print(f"{'='*70}")
    print(f"CONVERGENCE DETECTION AUDIT COMPLETE")
    print(f"{'='*70}")
    print(f"\nOutputs:")
    print(f"  {AUDIT_OUT}/C1_GPT4O.md      — GPT-4o Cycle 1")
    print(f"  {AUDIT_OUT}/C1_GROK.md       — Grok Cycle 1")
    print(f"  {AUDIT_OUT}/C2_GPT4O.md      — GPT-4o Cycle 2 (cross-exam)")
    print(f"  {AUDIT_OUT}/C2_GROK.md       — Grok Cycle 2 (cross-exam)")
    print(f"  {audit_path}  — Full audit report")
    print(f"  {spec_path}   — Hardened V1 spec")
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
