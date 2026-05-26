#!/usr/bin/env python3
"""
ML SESSION — BUILD-DOC ENGINEERING AUDIT
Protocol Pulse Intelligence Terminal · PCAF v1 GNN + TPA
Pre-build cross-LLM engineering review of cc_ml_session.md.

2-cycle parallel audit:
  Cycle 1: GPT-4o + Grok answer 10 engineering questions independently
  Cycle 2: Cross-examination (each sees the other's C1 answers)
  Synthesis: Claude merges into audit report + patched build doc

Usage:
    python3 utils/ml_session_audit.py

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
PHASE_ML = BASE / "docs" / "phase_ml"
AUDIT_OUT = AUDITS / "ml-session-audit"
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
        if len(text) > 30000:
            return text[:30000] + "\n\n... [TRUNCATED at 30000 chars] ..."
        return text
    return f"(file not found: {path})"

CC_ML_SESSION = _read("docs/cc_ml_session.md")
PCAF_FOUNDATION = _read("docs/phase_ml/pcaf_v1_foundation.md")
TPA_FOUNDATION = _read("docs/phase_ml/tpa_foundation.md")
SENTINEL_PY = _read("services/sentinel.py")
INTELLIGENCE_BP = _read("core/blueprints/intelligence.py")
QWEN_BIBLE = _read("docs/QWEN_CONTEXT_BIBLE.md")
PIPELINE_LAWS = _read("PIPELINE_LAWS.md")


# ─── CYCLE 1 BRIEF ──────────────────────────────────────────────────────────

CYCLE1_BRIEF = f"""---AUDIT BRIEF---
You are a senior ML engineer and production systems architect auditing a build
prompt for two major features before the code is written. The other model is
doing the same review simultaneously. You will challenge each other in Cycle 2.

The prompt covers:
1. PCAF v1 — GraphSAGE GNN Autoencoder for Bitcoin chain-state anomaly detection
2. TPA — Temporal Predictive Analytics, Monte Carlo scenario simulation engine

Your job: find every implementation flaw, ML correctness error, integration risk,
and missing detail that would cause a production failure. Be an engineer, not a
product manager. The code that gets written from this prompt runs on a live
Bitcoin intelligence terminal serving real users.

FULL BUILD PROMPT CONTENT:
{CC_ML_SESSION}

PCAF V1 FOUNDATION DOCUMENT:
{PCAF_FOUNDATION}

TPA FOUNDATION DOCUMENT:
{TPA_FOUNDATION}

EXISTING CODEBASE — services/sentinel.py (the daemon this integrates into):
{SENTINEL_PY}

EXISTING CODEBASE — core/blueprints/intelligence.py (API/SSE layer):
{INTELLIGENCE_BP}

QWEN CONTEXT BIBLE (known failure patterns in this codebase):
{QWEN_BIBLE}

PIPELINE LAWS:
{PIPELINE_LAWS[:3000]}

CRITICAL CODEBASE FACTS:
- Flask app runs from ~/protocol_pulse/core/ (gunicorn cwd = core/)
- Two services/ packages: core/services/ (Flask) and services/ (top-level: sentinel.py)
- This caused a production bug (BUG 1 in QWEN_CONTEXT_BIBLE)
- Fix uses importlib.util.spec_from_file_location() in blueprints
- sentinel.py runs asyncio daemon in a background thread started at Flask boot
- SentinelState written to /tmp/sentinel_state.json every 5s via tmp+os.replace
- SSE stream at /api/intelligence/stream reads that file every 2s
- PyTorch 2.6.0 + CUDA 12.4 installed on RTX 4090
- GPU 0: shared (Kokoro TTS), GPU 1: ~22GB free, GPU 2: Qwen/Ollama, GPU 3: free

Answer these 10 questions with maximum technical depth:

Q1 — TORCH_GEOMETRIC INSTALLATION RISK:
The prompt installs torch_geometric with pyg_lib/scatter/sparse from a PyG CDN.
PyTorch 2.6 + CUDA 12.4 is an unusual combination. What is the exact pip command
that will work? What are the most likely failure modes? What is the fallback if
pyg_lib/scatter/sparse can't install — will SAGEConv still work without them?
Verify your answer with the PyG compatibility matrix.

Q2 — GRAPHSAGE AUTOENCODER CORRECTNESS:
The foundation doc specifies a GraphSAGE encoder + decoder autoencoder.
SAGEConv is designed for node classification, not graph-level reconstruction.
What are the specific implementation challenges with using SAGEConv in a decoder
(the decoder receives no edge information about where to reconstruct)?
Is GraphSAGE the right choice or should we use a different GNN variant?
Give the exact PyTorch code for a correct forward pass.

Q3 — GRAPH CONSTRUCTION DATA CONTRACT:
The graph construction spec mixes 4 node types with different feature dimensions
(all padded to 8). What happens when SentinelState has:
  - Zero whale txs in the mempool (empty TX nodes)
  - Only 1 mining pool detected (1 POOL node)
  - Mempool data stale by >15 minutes
For each case: will PyTorch Geometric crash, produce garbage, or degrade
gracefully? Write the exact guard code for each case.

Q4 — TRAINING DATA QUALITY GATE:
The prompt says "train after >=1440 snapshots (24h)." What else must be true?
A corpus of 1440 snapshots with 30% collected during a mempool congestion event
will produce a model that flags normal mempool as anomalous.
Design the minimum viable data quality checks that must pass before training.
Be specific: what statistics to compute on the corpus, what thresholds to set.

Q5 — ANOMALY SCORE CALIBRATION FLAW:
The calibration method uses percentile thresholds from the validation set.
If the validation set (10% of training data) was collected during a quiet
weekend period, the thresholds will be too sensitive (too many false positives
during busy weekdays). How do we ensure the thresholds are calibrated against
a representative time distribution? Design the correct calibration methodology.

Q6 — SENTINEL INTEGRATION: ASYNC VS SYNC:
sentinel.py runs an asyncio event loop. The PCAF v1 inference call is:
  result = self._pcaf_v1_engine.score(state_dict)
But torch inference with GPU can take 50-150ms. Running this synchronously in
the asyncio loop WILL block the event loop during that time, causing:
  - Delayed mempool WebSocket messages
  - Missed blocks
  - SSE stream jank
How must PCAF v1 inference be integrated to avoid blocking the event loop?
Write the exact async wrapper pattern.

Q7 — TPA SIGNAL CHECKER COMPLETENESS:
The TPA has 27 precursor signals mapped to SentinelState paths.
Review the current SentinelState structure (from sentinel.py).
For each of the 5 scenarios: list which signals CAN be checked today vs which
signals require data that isn't yet in SentinelState.
For any missing data: is it a 1-hour fix (add to existing feed) or a
multi-day build (new data source)?

Q8 — MONTE CARLO CORRECTNESS:
The prompt specifies +/-20% jitter with Normal distribution for CI computation.
For a signal with 0.6 strength and +5% probability delta:
  - The jittered value = 0.6 * Normal(1.0, 0.2)
  - What % of samples will produce negative strength (jitter pulls below 0)?
  - Should negative jitter be clipped to 0 or allowed to go negative?
  - Write the exact numpy code that correctly handles this edge case.

Q9 — TPA SHARE URL SECURITY:
The prompt says "snapshot URL" for sharing scenario states. What is in the URL?
If it's a hash of current probabilities, two problems:
  (a) The URL becomes stale immediately as probabilities update
  (b) If probabilities are deterministic from signals, anyone can reproduce them
Design the correct snapshot persistence mechanism: what gets stored where,
for how long, and how is the public URL secured without requiring auth?

Q10 — THE BUG YOU'D BET ON:
Given everything in the build prompt and the existing codebase (especially
the services/* import shadowing history in QWEN_CONTEXT_BIBLE.md):
What is the single most likely production bug on first deploy of PCAF v1?
Not theoretical — the bug that WILL happen. Describe it precisely.
Then describe the specific test that would catch it before production.
---END BRIEF---"""


# ─── CYCLE 2 CROSS-EXAMINATION TEMPLATE ─────────────────────────────────────
def build_cycle2_prompt(model_name: str, own_c1: str, other_name: str, other_c1: str) -> str:
    return f"""# ML SESSION BUILD-DOC AUDIT — CYCLE 2 CROSS-EXAMINATION
# Protocol Pulse Intelligence Terminal · PCAF v1 GNN + TPA
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

3. On Q6 (async blocking): one approach wins. Which? Defend it technically.
   Give the exact code pattern that should be used.

4. On Q2 (GraphSAGE decoder): both models proposed approaches. Which is more
   correct for THIS specific use case (unsupervised anomaly detection on
   small sparse graphs)? Could a simpler architecture work better?

5. Name one production risk that NEITHER model caught in Cycle 1.

Give your FINAL position on all 10 questions, incorporating cross-exam findings.
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


def claude_synthesize(prompt: str, max_tokens: int = 16000) -> str:
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
    print(f"ML SESSION BUILD-DOC — ENGINEERING AUDIT")
    print(f"PCAF v1 GNN Autoencoder + TPA Monte Carlo Engine")
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
Protocol Pulse's ML Session features: PCAF v1 (GNN Autoencoder) + TPA (Temporal Predictive Analytics).

Two models (GPT-4o and Grok-3) independently answered 10 deep ML engineering questions
about the implementation plan, then cross-examined each other's answers.
Your job: produce a definitive engineering audit report.

## GPT-4o CYCLE 1
{c1_results.get('gpt4o', 'FAILED')[:14000]}

## GROK CYCLE 1
{c1_results.get('grok', 'FAILED')[:14000]}

## GPT-4o CYCLE 2 (after seeing Grok's C1)
{c2_results.get('gpt4o', 'FAILED')[:10000]}

## GROK CYCLE 2 (after seeing GPT-4o's C1)
{c2_results.get('grok', 'FAILED')[:10000]}

---

Produce a comprehensive ML BUILD-DOC ENGINEERING AUDIT REPORT with these exact sections:

# ML SESSION BUILD-DOC — ENGINEERING AUDIT REPORT
# Protocol Pulse Intelligence Terminal · PCAF v1 + TPA
# Date: {datetime.now().strftime('%Y-%m-%d')}
# Models: GPT-4o, Grok-3 (2 cycles each)
# Synthesized by: Claude Sonnet 4.6

For each of the 10 questions:

## Q1 VERDICT: TORCH_GEOMETRIC INSTALLATION
Exact pip commands. Fallback strategy if pyg_lib fails.

## Q2 VERDICT: GRAPHSAGE AUTOENCODER ARCHITECTURE
Which model's approach is correct? Give the definitive architecture + forward pass code.

## Q3 VERDICT: GRAPH CONSTRUCTION DATA CONTRACT
Guard code for all edge cases (empty TX, single pool, stale data).

## Q4 VERDICT: TRAINING DATA QUALITY GATE
Complete quality gate checklist with specific thresholds.

## Q5 VERDICT: ANOMALY SCORE CALIBRATION
Correct calibration methodology that handles time-distribution bias.

## Q6 VERDICT: ASYNC INTEGRATION PATTERN
Which model's approach wins? Give the exact async wrapper code.

## Q7 VERDICT: TPA SIGNAL COMPLETENESS
Per-scenario signal availability matrix. Missing data assessment.

## Q8 VERDICT: MONTE CARLO CORRECTNESS
Exact numpy code with edge case handling.

## Q9 VERDICT: TPA SHARE URL SECURITY
Correct snapshot persistence mechanism.

## Q10 VERDICT: MOST LIKELY FIRST-DEPLOY BUG
Which model's predicted bug is more likely? The definitive fix + test.

## CONFIRMED BUGS (critical — must fix before merge)
Numbered list of every confirmed bug found across both cycles.

## REQUIRED FIXES (important — fix before deploy)
For each confirmed bug: the exact code change needed.

## IMPROVEMENTS (recommended — add if time allows)
Engineering improvements both models endorse.

## PRODUCTION RISKS
Risk register ordered by likelihood x impact.
"""

    audit_report = claude_synthesize(synthesis_prompt, max_tokens=16000)
    audit_path = AUDITS / "ml_session_audit_2026-03-23.md"
    audit_path.write_text(audit_report)
    print(f"  Audit report: {audit_path} ({len(audit_report):,} chars)")
    print(f"  Duration: {time.time() - t2:.1f}s\n")

    # ═══════════════════════════════════════════════════════════════════════
    #  CLAUDE SYNTHESIS → PATCHED BUILD DOC
    # ═══════════════════════════════════════════════════════════════════════
    print("── CLAUDE SYNTHESIS: PATCHED BUILD DOC ─────────────────────────────")
    t3 = time.time()

    original_build_doc = CC_ML_SESSION

    patch_prompt = f"""You are producing the PATCHED, AUDIT-HARDENED version of the ML Session build
document for Protocol Pulse. This covers PCAF v1 (GNN Autoencoder) + TPA (Monte Carlo engine).

You have:
1. The original build doc (cc_ml_session.md)
2. The PCAF v1 foundation document
3. The TPA foundation document
4. A comprehensive engineering audit report from GPT-4o and Grok-3 (2 cycles)

## ORIGINAL BUILD DOC
{original_build_doc}

## PCAF V1 FOUNDATION
{PCAF_FOUNDATION[:12000]}

## TPA FOUNDATION
{TPA_FOUNDATION[:12000]}

## ENGINEERING AUDIT REPORT (all findings)
{audit_report}

## EXISTING CODE CONTEXT
- sentinel.py is asyncio + aiohttp daemon in a background thread
- intelligence.py uses importlib.util to load sentinel by absolute path
- Two services/ packages exist — core/services/ shadows top-level services/
- NEVER use `from pp_services.X import Y` — always importlib.util path loading
- PyTorch 2.6.0 + CUDA 12.4 on RTX 4090 (GPU 1 for PCAF training/inference)
- SentinelState written to /tmp/sentinel_state.json every 5s
- SSE stream reads that file every 2s

---

Produce the FINAL, PATCHED build document. This is the document CC executes — not the original.
Structure it identically to the original cc_ml_session.md but with every confirmed bug
fixed, every missing detail added, every improvement incorporated.

Mark every change from the original with: # AUDIT FIX: [description]

The document must include:
1. STEP 0 — INSTALL (with audit-confirmed pip commands)
2. STEP 1 — PCAF V1 AUDIT (already done — reference audit report)
3. STEP 2 — TPA AUDIT (already done — reference audit report)
4. STEP 3 — BUILD PCAF V1 (all files, with audit fixes applied)
5. STEP 4 — BUILD TPA (all files, with audit fixes applied)
6. STEP 5 — FINAL INTEGRATION
7. All TESTS (rewritten where audit found problems)
8. All COMMIT instructions

Key fixes that MUST be incorporated:
- Torch_geometric installation fallback strategy
- GraphSAGE decoder architecture fix (from Q2 verdict)
- Graph construction guard code (from Q3 verdict)
- Training data quality gate (from Q4 verdict)
- Anomaly score calibration fix (from Q5 verdict)
- Async integration pattern for PCAF inference (from Q6 verdict)
- TPA signal completeness fixes (from Q7 verdict)
- Monte Carlo edge case handling (from Q8 verdict)
- Share URL security (from Q9 verdict)
- First-deploy bug prevention (from Q10 verdict)
"""

    patched_doc = claude_synthesize(patch_prompt, max_tokens=16000)
    patched_path = PHASE_ML / "cc_ml_session_FINAL.md"
    patched_path.write_text(patched_doc)
    print(f"  Patched build doc: {patched_path} ({len(patched_doc):,} chars)")
    print(f"  Duration: {time.time() - t3:.1f}s\n")

    # ═══════════════════════════════════════════════════════════════════════
    #  UPDATE AUDIT REGISTRY
    # ═══════════════════════════════════════════════════════════════════════
    try:
        import subprocess
        rp = AUDITS / "AUDIT_REGISTRY.json"
        existing = json.loads(rp.read_text()) if rp.exists() else {}
        audits = [a for a in existing.get("audits", []) if a.get("feature") != "ml-session-audit"]
        audits.append({
            "feature": "ml-session-audit",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "models": ["gpt4o", "grok"],
            "type": "build_doc_engineering_audit",
            "cycles": 2,
            "questions": 10,
            "scope": "PCAF v1 GNN + TPA Monte Carlo",
        })
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(BASE), text=True).strip()
        rp.write_text(json.dumps({
            "last_audit": datetime.now(timezone.utc).isoformat(),
            "feature": "ml-session-audit",
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
    print(f"ML SESSION BUILD-DOC AUDIT COMPLETE — {total:.0f}s total")
    print(f"{'='*70}")
    print(f"\nOutputs:")
    print(f"  {AUDIT_OUT}/C1_GPT4O.md      — GPT-4o Cycle 1")
    print(f"  {AUDIT_OUT}/C1_GROK.md       — Grok Cycle 1")
    print(f"  {AUDIT_OUT}/C2_GPT4O.md      — GPT-4o Cycle 2 (cross-exam)")
    print(f"  {AUDIT_OUT}/C2_GROK.md       — Grok Cycle 2 (cross-exam)")
    print(f"  {AUDITS}/ml_session_audit_2026-03-23.md  — Full audit report")
    print(f"  {PHASE_ML}/cc_ml_session_FINAL.md        — Patched build doc (FINAL)")
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
