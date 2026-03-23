#!/usr/bin/env python3
"""
CONVERGENCE DETECTION — BUILD-DOC ENGINEERING AUDIT
Protocol Pulse Intelligence Terminal · Phase 2 · Feature 1

Pre-build cross-LLM engineering review of the implementation instructions.
Same 2-cycle parallel structure as convergence_audit.py:
  Cycle 1: GPT-4o + Grok answer 9 engineering questions independently
  Cycle 2: Cross-examination (each sees the other's C1 answers)
  Synthesis: Claude merges into audit report + patched build doc

Usage:
    python3 utils/convergence_build_audit.py

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
AUDIT_OUT = AUDITS / "convergence-build-audit"
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
        text = p.read_text()
        # Truncate very large files to avoid token overflow
        if len(text) > 30000:
            return text[:30000] + "\n\n... [TRUNCATED at 30000 chars] ..."
        return text
    return f"(file not found: {path})"

SENTINEL_PY = _read("services/sentinel.py")
INTELLIGENCE_BP = _read("core/blueprints/intelligence.py")
APP_PY_HEAD = _read("core/app.py")[:6000]  # first ~220 lines
INTEL_HTML_HEAD = _read("core/templates/intelligence_terminal.html")[:5000]
V1_SPEC = _read("docs/phase2/convergence_detection_v1_spec.md")
QWEN_BIBLE = _read("docs/QWEN_CONTEXT_BIBLE.md")
PIPELINE_LAWS = _read("PIPELINE_LAWS.md")

# Grep for convergence/SSE patterns in the template
import subprocess
try:
    _sse_grep = subprocess.check_output(
        ["grep", "-n", "-C", "3", "EventSource\\|onmessage\\|updateState\\|connectSSE",
         str(BASE / "core/templates/intelligence_terminal.html")],
        text=True, stderr=subprocess.DEVNULL
    )
except subprocess.CalledProcessError:
    _sse_grep = "(no matches)"

# Check which API keys exist for external feeds
try:
    _env_text = (BASE / ".env").read_text()
    _feed_keys = []
    for k in ["YAHOO", "DERIBIT", "HODLHODL", "CIRCLE", "DEFI_LLAMA", "COINGECKO"]:
        if k in _env_text:
            _feed_keys.append(k)
    FEED_KEYS_PRESENT = ", ".join(_feed_keys) if _feed_keys else "NONE — all external feeds will use unauthenticated public endpoints"
except Exception:
    FEED_KEYS_PRESENT = "Could not read .env"


# ─── THE BUILD DOC (subject of audit) ───────────────────────────────────────
# This is the full build doc from the user's prompt, stored here as context
BUILD_DOC = """[BUILD DOC — CONVERGENCE DETECTION PHASE 2 F1]

FILES TO CREATE:
1. services/signal_feeds.py — External data feed fetchers (8 fetchers: VIX, SPY, WTI, Deribit funding, stablecoin flows via DeFi Llama, HodlHodl P2P, RSS news, custodian wallet flows)
2. services/baseline_store.py — Rolling 30-day baseline SQLite store (signal_daily_values + pattern_events tables)
3. services/convergence_engine.py — Pattern state machine (~500 lines): SignalExtractor, PatternEvaluator, ConvergenceEngine classes
4. data/convergence_config.yaml — Externalized thresholds
5. data/custodian_wallets.json — Known ETF custodian BTC wallet addresses
6. data/miner_wallets.json — Known mining pool coinbase payout addresses

FILES TO MODIFY:
- services/sentinel.py — Add convergence dict to SentinelState, instantiate ConvergenceEngine in daemon init, call run_evaluation_cycle() every 60s
- core/blueprints/intelligence.py — Add GET /api/intelligence/convergence endpoint, include convergence in SSE stream
- core/templates/intelligence_terminal.html — Add Convergence Matrix panel (Q6 spec states)

INTEGRATION:
- signal_feeds.py uses requests (synchronous HTTP)
- sentinel.py is asyncio daemon
- convergence_engine.run_evaluation_cycle() called from sentinel main loop every 60s
- baseline_store.py uses SQLite (sentinel writes, Flask reads)
- SSE stream reads from /tmp/sentinel_state.json (already atomic via os.replace)

TESTS (7 inline tests before commit):
1. Pattern evaluation (MCC fires at 3/5)
2. State machine no-skip (IDLE→CRITICAL raises ValueError)
3. Signal decay forces confirmed=False
4. Atomic file write verification
5. External feeds fail gracefully
6. Convergence in SSE stream
7. Contradiction detection (IES+LSC stablecoin conflict)

KEY ARCHITECTURE DECISIONS:
- Rule-based, no ML (binding from audit)
- 60-second evaluation loop
- Signal freshness decay: linear from decay_onset to max_valid_age
- State transitions: IDLE→FORMING→WATCH→CRITICAL→RESOLVED (no skipping)
- Thresholds in YAML, not hardcoded
"""


# ─── THE BRIEF ──────────────────────────────────────────────────────────────

CYCLE1_BRIEF = f"""---ENGINEERING AUDIT BRIEF---
You are a senior Python/Flask engineer doing a pre-build code review of the
implementation instructions below. You have full access to the existing codebase.
Your job: find every bug, gap, conflict, and improvement BEFORE the code is written.
The other model is doing the same review. You will challenge each other in Cycle 2.

THE BUILD DOC (subject of this audit):

{BUILD_DOC}

THE EXISTING CODEBASE CONTEXT:

## services/sentinel.py (the daemon this integrates into)
{SENTINEL_PY}

## core/blueprints/intelligence.py (the API/SSE layer)
{INTELLIGENCE_BP}

## core/app.py (first ~220 lines — blueprint registration + sentinel start)
{APP_PY_HEAD}

## core/templates/intelligence_terminal.html (CSS vars + grid + SSE handler)
{INTEL_HTML_HEAD}

## SSE handler grep (EventSource/onmessage patterns in template):
{_sse_grep}

## V1 SPEC (sections 1-6 — signal definitions and state machine):
{V1_SPEC[:15000]}

## QWEN CONTEXT BIBLE (known failure patterns in this codebase):
{QWEN_BIBLE}

## PIPELINE LAWS:
{PIPELINE_LAWS[:3000]}

## API keys for external feeds: {FEED_KEYS_PRESENT}

CRITICAL CODEBASE FACTS:
- Flask app runs from ~/protocol_pulse/core/ (gunicorn cwd = core/)
- Two services/ packages: core/services/ (Flask) and services/ (top-level: sentinel.py)
- This caused a production bug (BUG 1 in QWEN_CONTEXT_BIBLE)
- Fix uses importlib.util.spec_from_file_location() in blueprints
- sentinel.py runs asyncio daemon in a background thread started at Flask boot
- SentinelState written to /tmp/sentinel_state.json every 5s via tmp+os.replace
- SSE stream at /api/intelligence/stream reads that file every 2s
- All new files in services/ (top-level) have the same import shadowing risk
- intelligence_terminal.html grid: 3-column (1fr 1fr 1.5fr)
- No YAHOO, DERIBIT, HODLHODL, or CIRCLE API keys exist in .env
- sentinel.py already uses aiohttp for HTTP requests (not requests library)

Answer these 9 questions. Be an engineer, not a product manager.
Find real bugs. The other model will challenge your answers.

Q1 — IMPORT CHAIN AUDIT:
The build doc introduces 3 new services/ files (signal_feeds.py,
baseline_store.py, convergence_engine.py). Given the known core/services
shadowing bug, trace the exact import path for each new file from:
  (a) sentinel.py (top-level, asyncio loop)
  (b) intelligence.py blueprint (runs from core/, uses importlib.util for sentinel)
  (c) app.py startup (sentinel start via importlib.util)
For each, identify if the import will succeed or fail. If it will fail,
write the exact fix. Show your work — trace the Python module resolution.

Q2 — SENTINEL INTEGRATION CORRECTNESS:
The build doc says to add convergence_engine to sentinel.py's main loop.
sentinel.py is an asyncio daemon. signal_feeds.py fetchers use requests
(synchronous HTTP). convergence_engine.run_evaluation_cycle() calls these
fetchers. This is synchronous code in an async loop.
Will this block the event loop? How? What is the correct integration pattern?
Should signal_feeds use aiohttp instead of requests? Give the exact implementation.

Q3 — SQLITE CONCURRENCY:
The build doc creates baseline_store.py backed by SQLite.
sentinel.py writes to it (async context, background thread).
Flask routes read from it (sync context, gunicorn worker threads).
Two gunicorn workers + sentinel daemon = 3 concurrent SQLite writers/readers.
What are the locking semantics? Will this cause database locked errors?
What WAL mode settings, connection_timeout values, and check_same_thread
parameters are required? Give the exact sqlite3.connect() call.

Q4 — TEST SUITE VALIDITY:
Review all 7 tests in the build doc. For each test:
  (a) Will it actually run given the import chain in Q1?
  (b) Does it test what it claims to test?
  (c) Is there a gap — something the test claims to verify but doesn't actually catch?
Rewrite any test that has a validity problem. Add any missing test that would
have caught the production bugs already documented in QWEN_CONTEXT_BIBLE.md.

Q5 — EXTERNAL FEED RELIABILITY AUDIT:
Review the 8 fetchers in signal_feeds.py. For each:
  (a) Verify the API endpoint is correct and publicly accessible (no auth required)
  (b) Verify the response parsing logic will work for the current API response format
  (c) Identify the most likely failure mode
  (d) Is the cache TTL appropriate for the signal's freshness requirements?
Yahoo Finance endpoints in particular have a history of undocumented breaking changes.
What is the fallback if Yahoo Finance blocks the scraper?

Q6 — FRONTEND INTEGRATION COMPLETENESS:
The build doc modifies intelligence_terminal.html to add the Convergence Matrix panel.
Review the existing template's CSS variable names, grid structure, and JS SSE handler.
Does the panel CSS in the build doc use the correct existing CSS variable names?
Does the SSE handler modification correctly slot into the existing onmessage handler
without breaking the existing Mempool, PCAF, and Data Rail updates?
What exact JS code is needed to integrate renderConvergencePanel() into the
existing event stream handler? Write the exact integration code.

Q7 — CONVERGENCE_CONFIG.YAML COMPLETENESS:
The build doc specifies convergence_config.yaml with threshold externalization.
Review the spec's signal table and persistence requirements.
List every threshold, window, and persistence requirement from the spec that
must be in the config file but is NOT explicitly listed in the build doc's
yaml structure. If any are missing, the hardcoded fallbacks in the engine
will silently override the config — which defeats the purpose.

Q8 — WORLD-CLASS IMPROVEMENTS:
You've audited the implementation plan. Now: what one engineering decision
in this build doc, if changed, would make the result significantly more robust,
maintainable, or impressive? Not a product feature — a technical architecture
decision. Something a senior engineer would insist on before approving the PR.
Be specific. Show the better implementation.

Q9 — THE BUG YOU'D BET ON:
Given everything you've read — the build doc, the existing codebase, the
QWEN_CONTEXT_BIBLE failure patterns — what is the single most likely
production bug that will occur on the FIRST deploy of this feature?
Not a theoretical risk. The bug that will actually happen based on this
specific codebase's history. Describe it precisely and give the fix.
"""


# ─── CYCLE 2 CROSS-EXAMINATION TEMPLATE ─────────────────────────────────────
def build_cycle2_prompt(model_name: str, own_c1: str, other_name: str, other_c1: str) -> str:
    return f"""# CONVERGENCE BUILD AUDIT — CYCLE 2 CROSS-EXAMINATION
# Protocol Pulse Intelligence Terminal · Phase 2 · Feature 1
# You are: {model_name}. The other model is: {other_name}.

## YOUR CYCLE 1 ANSWERS
{own_c1[:14000]}

## {other_name.upper()}'s CYCLE 1 ANSWERS
{other_c1[:14000]}

---

## CROSS-EXAMINATION INSTRUCTIONS

You've now seen what {other_name} said. This is your final engineering review.

1. Identify the single most critical finding from {other_name}'s response that
   you missed or underweighted in your own Cycle 1. Be specific about why it matters.

2. Challenge the weakest recommendation from {other_name}'s response —
   where is the other model wrong or imprecise? Be technical and specific.

3. On Q2 (async/sync conflict): provide the definitive resolution.
   One of you is more correct. State which approach wins and why.
   Give the exact code pattern that should be used.

4. On Q9 (the most likely production bug): both models named one bug.
   Which is more likely given this specific codebase? Justify with
   evidence from QWEN_CONTEXT_BIBLE.md and the existing code patterns.

5. Name one production risk that NEITHER model caught in Cycle 1.
   This should be a genuine integration risk based on reading the actual
   codebase code above, not a theoretical edge case.

Give your FINAL position on all 9 questions, incorporating cross-exam findings.
Be concise but technically precise.
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


def claude_synthesize(prompt: str, max_tokens: int = 12000) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


# ─── MAIN ───────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*70}")
    print(f"CONVERGENCE BUILD-DOC — ENGINEERING AUDIT")
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
    t0 = time.time()
    c1_results, c1_errors = fire_both(CYCLE1_BRIEF)

    for name, text in c1_results.items():
        (AUDIT_OUT / f"C1_{name.upper()}.md").write_text(text)
    for name, err in c1_errors.items():
        (AUDIT_OUT / f"C1_{name.upper()}.md").write_text(f"FAILED: {err}")

    print(f"\n  Cycle 1: {list(c1_results.keys())} succeeded, {list(c1_errors.keys())} failed")
    print(f"  Duration: {time.time() - t0:.1f}s\n")

    if len(c1_results) < 2:
        print("Need at least 2 models for cross-examination. Saving C1 and exiting.")
        sys.exit(1)

    # ═══════════════════════════════════════════════════════════════════════
    #  CYCLE 2 — Cross-examination
    # ═══════════════════════════════════════════════════════════════════════
    print("── CYCLE 2: CROSS-EXAMINATION ──────────────────────────────────────")
    t1 = time.time()

    c2_results, c2_errors = {}, {}
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

    print(f"\n  Cycle 2: {list(c2_results.keys())} succeeded, {list(c2_errors.keys())} failed")
    print(f"  Duration: {time.time() - t1:.1f}s\n")

    # ═══════════════════════════════════════════════════════════════════════
    #  CLAUDE SYNTHESIS → AUDIT REPORT
    # ═══════════════════════════════════════════════════════════════════════
    print("── CLAUDE SYNTHESIS: AUDIT REPORT ──────────────────────────────────")
    t2 = time.time()

    synthesis_prompt = f"""You are synthesizing a 2-cycle cross-LLM BUILD-DOC engineering audit for
Protocol Pulse's Convergence Detection feature (Phase 2, Feature 1).

Two models (GPT-4o and Grok-3) independently answered 9 deep engineering questions
about the implementation plan, then cross-examined each other's answers.
Your job: produce a definitive engineering audit report.

## GPT-4o CYCLE 1
{c1_results.get('gpt4o', 'FAILED')[:12000]}

## GROK CYCLE 1
{c1_results.get('grok', 'FAILED')[:12000]}

## GPT-4o CYCLE 2 (after seeing Grok's C1)
{c2_results.get('gpt4o', 'FAILED')[:8000]}

## GROK CYCLE 2 (after seeing GPT-4o's C1)
{c2_results.get('grok', 'FAILED')[:8000]}

---

Produce a comprehensive BUILD-DOC ENGINEERING AUDIT REPORT with these exact sections:

# CONVERGENCE BUILD-DOC — ENGINEERING AUDIT REPORT
# Protocol Pulse Intelligence Terminal · Phase 2 · Feature 1
# Date: {datetime.now().strftime('%Y-%m-%d')}
# Models: GPT-4o, Grok-3 (2 cycles each)
# Synthesized by: Claude Sonnet 4.6

For each of the 9 questions:

## Q1 VERDICT: IMPORT CHAIN
Synthesize both models' findings. State the exact import fixes needed.

## Q2 VERDICT: ASYNC/SYNC INTEGRATION
Which model's approach is correct? Give the definitive code pattern.

## Q3 VERDICT: SQLITE CONCURRENCY
Exact sqlite3.connect() call and WAL mode settings required.

## Q4 VERDICT: TEST SUITE
Which tests are broken? Rewritten test code for any that need fixing.

## Q5 VERDICT: EXTERNAL FEEDS
Per-feed reliability assessment. Which endpoints will break first?

## Q6 VERDICT: FRONTEND INTEGRATION
Exact JS integration code for the SSE handler.

## Q7 VERDICT: CONFIG COMPLETENESS
Complete list of missing config keys.

## Q8 VERDICT: WORLD-CLASS IMPROVEMENT
The one architecture decision that both models agree should change.

## Q9 VERDICT: MOST LIKELY PRODUCTION BUG
Which model's predicted bug is more likely? The definitive fix.

## CONFIRMED BUGS (must-fix before build starts)
Numbered list of every confirmed bug found across both cycles.

## REQUIRED FIXES
For each confirmed bug: the exact code change needed.

## IMPROVEMENTS (recommended but not blocking)
Engineering improvements both models endorse.

## PRODUCTION RISKS
Risk register ordered by likelihood × impact.
"""

    audit_report = claude_synthesize(synthesis_prompt, max_tokens=16000)
    audit_path = AUDITS / "convergence_build_audit_2026-03-23.md"
    audit_path.write_text(audit_report)
    print(f"  Audit report: {audit_path} ({len(audit_report):,} chars)")
    print(f"  Duration: {time.time() - t2:.1f}s\n")

    # ═══════════════════════════════════════════════════════════════════════
    #  CLAUDE SYNTHESIS → PATCHED BUILD DOC
    # ═══════════════════════════════════════════════════════════════════════
    print("── CLAUDE SYNTHESIS: PATCHED BUILD DOC ─────────────────────────────")
    t3 = time.time()

    # Read the original build doc file for patching context
    original_build_doc_text = ""
    orig_path = BASE / "docs" / "phase2" / "cc_convergence_build.md"
    if orig_path.exists():
        original_build_doc_text = orig_path.read_text()[:20000]
    else:
        original_build_doc_text = BUILD_DOC

    patch_prompt = f"""You are producing the PATCHED, AUDIT-HARDENED build document for
Protocol Pulse's Convergence Detection engine (Phase 2, Feature 1).

You have:
1. The original build doc
2. A comprehensive engineering audit report from GPT-4o and Grok-3 (2 cycles)

## ORIGINAL BUILD DOC
{original_build_doc_text}

## ENGINEERING AUDIT REPORT (all findings)
{audit_report}

## EXISTING CODE CONTEXT
sentinel.py is asyncio + aiohttp. The daemon runs in a background thread.
intelligence.py uses importlib.util to load sentinel by absolute path.
app.py starts sentinel via importlib.util from core/ directory.
Grid is 3-column (1fr 1fr 1.5fr). SSE handler is in updateState() function.
Two services/ packages exist — core/services/ shadows top-level services/.
No external feed API keys exist in .env (Yahoo, Deribit, etc all unauthenticated).
sentinel.py already does atomic file writes (tmp + os.replace).

---

Produce the FINAL, PATCHED build document. This is the document that will be
executed to build the feature. It must be BETTER than the original in every way.

Structure it identically to the original build doc but with every confirmed bug
fixed, every missing detail added, every improvement incorporated.

Mark every change from the original with: # AUDIT FIX: [description]

The document must include:
1. FILES TO CREATE (all 6, with audit fixes applied)
2. FILES TO MODIFY (all 3, with audit fixes applied)
3. INTEGRATION HARDENING CHECKLIST (updated)
4. TESTS (rewritten where audit found problems)
5. COMMIT instructions

Key fixes that MUST be incorporated:
- Import chain fixes for the core/services shadowing bug
- Async/sync integration pattern (the correct one from the audit)
- SQLite WAL mode + connection parameters
- Test rewrites for broken tests
- External feed fallback strategy
- Frontend JS integration code
- Complete config YAML
- Any production bug fixes identified in Q9
"""

    patched_doc = claude_synthesize(patch_prompt, max_tokens=16000)
    patched_path = PHASE2 / "cc_convergence_build_FINAL.md"
    patched_path.write_text(patched_doc)
    print(f"  Patched build doc: {patched_path} ({len(patched_doc):,} chars)")
    print(f"  Duration: {time.time() - t3:.1f}s\n")

    # ═══════════════════════════════════════════════════════════════════════
    #  UPDATE AUDIT REGISTRY
    # ═══════════════════════════════════════════════════════════════════════
    try:
        rp = AUDITS / "AUDIT_REGISTRY.json"
        existing = json.loads(rp.read_text()) if rp.exists() else {}
        audits = [a for a in existing.get("audits", []) if a.get("feature") != "convergence-build-audit"]
        audits.append({
            "feature": "convergence-build-audit",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "models": ["gpt4o", "grok"],
            "type": "build_doc_engineering_audit",
            "cycles": 2,
        })
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(BASE), text=True).strip()
        rp.write_text(json.dumps({
            "last_audit": datetime.now(timezone.utc).isoformat(),
            "feature": "convergence-build-audit",
            "commit": sha,
            "audits": audits[-20:]
        }, indent=2))
        print(f"  AUDIT_REGISTRY.json updated\n")
    except Exception as e:
        print(f"  Warning: could not update registry: {e}\n")

    # ═══════════════════════════════════════════════════════════════════════
    #  DONE
    # ═══════════════════════════════════════════════════════════════════════
    total = time.time() - t0
    print(f"{'='*70}")
    print(f"CONVERGENCE BUILD-DOC AUDIT COMPLETE — {total:.0f}s total")
    print(f"{'='*70}")
    print(f"\nOutputs:")
    print(f"  {AUDIT_OUT}/C1_GPT4O.md      — GPT-4o Cycle 1")
    print(f"  {AUDIT_OUT}/C1_GROK.md       — Grok Cycle 1")
    print(f"  {AUDIT_OUT}/C2_GPT4O.md      — GPT-4o Cycle 2 (cross-exam)")
    print(f"  {AUDIT_OUT}/C2_GROK.md       — Grok Cycle 2 (cross-exam)")
    print(f"  {audit_path}  — Full audit report")
    print(f"  {patched_path}   — Patched build doc (FINAL)")
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
