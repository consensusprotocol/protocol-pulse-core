Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.
Read ~/protocol_pulse/docs/phase_ml/pcaf_v1_foundation.md.
Read ~/protocol_pulse/docs/phase_ml/tpa_foundation.md.
Read ~/protocol_pulse/docs/cc_ml_session.md.
Read ~/protocol_pulse/services/sentinel.py (imports + SentinelState + _update_pcaf lines only).
Read ~/protocol_pulse/core/blueprints/intelligence.py (route list only — grep for @intelligence_bp.route).
Read ~/protocol_pulse/services/pcaf_v0 equivalent — grep _update_pcaf from sentinel.py.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK: ENGINEERING AUDIT — ML SESSION BUILD PROMPT
Cross-LLM review of cc_ml_session.md before production ML code is written.
This is the most critical audit in the pipeline — ML bugs are the hardest to find.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Register in utils/cross_llm_audit.py:
  FEATURE_MAP["ml-session-audit"] = ("VISUAL_DESIGN_SYSTEM.md", "main")
  EXPLICIT_FILES["ml-session-audit"] = [
      "docs/cc_ml_session.md",
      "docs/phase_ml/pcaf_v1_foundation.md",
      "docs/phase_ml/tpa_foundation.md",
      "services/sentinel.py",
      "core/blueprints/intelligence.py",
  ]

Write and run: utils/ml_session_audit.py
(GPT-4o + Grok, 2-cycle parallel, same structure as convergence_build_audit.py)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CYCLE 1 BRIEF — same brief to both models
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---AUDIT BRIEF---
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
[Insert full contents of docs/cc_ml_session.md here]

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
The prompt says "train after ≥1440 snapshots (24h)." What else must be true?
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
The prompt specifies ±20% jitter with Normal distribution for CI computation.
For a signal with 0.6 strength and +5% probability delta:
  - The jittered value = 0.6 × Normal(1.0, 0.2)
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
---END BRIEF---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CYCLE 2 — CROSS-EXAMINATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each model receives the other's Cycle 1 answers and must:
1. Identify the single most critical finding the other model caught that you missed
2. Challenge the weakest recommendation — where is the other model wrong or
   imprecise? Give the correct answer.
3. Q6 (async blocking): one approach wins. Which? Defend it technically.
4. Q2 (GraphSAGE decoder): both models proposed approaches. Which is more
   correct for THIS specific use case (unsupervised anomaly detection on
   small sparse graphs)? Could a simpler architecture work better?
5. Name one production risk that NEITHER model caught in Cycle 1.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYNTHESIS OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After both cycles, Claude synthesizes into two files:

FILE 1: docs/audits/ml_session_audit_2026-03-23.md
  Full audit report — C1 answers, C2 cross-exam, synthesis.
  Structure:
    CONFIRMED BUGS (critical — must fix before merge)
    REQUIRED FIXES (important — fix before deploy)
    IMPROVEMENTS (recommended — add if time allows)
    Q2 VERDICT: exact GNN architecture to implement
    Q6 VERDICT: exact async integration pattern
    Q10 VERDICT: most likely first-deploy bug + test

FILE 2: docs/phase_ml/cc_ml_session_FINAL.md
  PATCHED version of cc_ml_session.md.
  Every confirmed bug fixed. Every improvement incorporated.
  Every change marked: # AUDIT FIX: [description]
  This is the document CC executes — not the original.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

git add -f docs/audits/ml_session_audit_2026-03-23.md
git add docs/phase_ml/cc_ml_session_FINAL.md
git add utils/ml_session_audit.py utils/cross_llm_audit.py
git commit -m "audit(ml): PCAF v1 + TPA build-doc engineering audit — 10-question pre-build review"
git push

No confirmation. Auto-commit and push.
