# Heimdall audit

**Question:** TASK: second audit cycle of batch 115 of the Protocol Pulse video pipeline (Python), same diff. Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

THE RULING (orchestrator 2026-11-18 09:38, ruling 148 (1)), verbatim: "For this exception pin a line-up of 30.0 s or more may seal; between 30.0 and 36.7 s it carries the flag 'This video runs NN seconds, shorter than usual.' (it counts toward the 5). Under 30 s still refused." It stands for later builds: "the 30 s floor with its flag".

Cycle 1 traced the new functions. This cycle checks the CALLERS and the release decision:
- G5_tech is REQUIRED (pipeline/release_auth.py:36). qa_gates.run_all_gates calls gate_g5(final_mp4, fmt, window=g5_window(edl_path)). gates.run_gates (pipeline/gates.py:599) sets edl_path = os.path.join(segment_dir, "edl.json"), or None when the file is missing. run_fresh passes segment_dir = the run dir.
- pinned.prepare writes PINNED_DECISION.json in the run dir: {"pin": <the whole pin>, ...}. The builder's moments_package.gates.runtime row sits inside it.

CHECK, each with file:line and a concrete failure scenario:
(a) g5_window with edl_path None: does it still return ruling 12's window without touching the new branch?
(b) A replay run (a copy of a run dir, re-gated later): does the exception follow the copied PINNED_DECISION.json? Is that right, given it is the same sealed pin?
(c) G5's duration verdict (gate_g5 :707 onwards, unchanged): with the window (44.3, 72.0) and target (60, 70), is a 57.0 s final accepted and recorded as a deviation from the target? Is a 44.0 s final refused?
(d) Can the R4 change silence a finding that should HOLD? R4 is SOFT (in EDL_SOFT); the HARD rules are judged before flag_soft_rules runs.
(e) Does any other module import or call the functions this diff renames or moves (the old inline loop in stage_validate)?

OUTPUT: findings, each <severity> <file:line> <what fails, with inputs>; "(x): no finding" with what you traced otherwise.

**Panel:** gptoss  |  **Cost:** $0.0004
## Consensus findings (majority of panel agrees)
- **[critical] pipeline/edl_rules.py:0** Missing imports for os and json used in flagged_runtime_row
  - evidence: `def flagged_runtime_row(run_dir):
    try:
        with open(os.path.join(run_dir, "PINNED_DECISION.json")) as f:
            row = ((json.load(f).get("pin") or {}).get("moments_package") or {}).get("`
  - fix: Add `import os, json` at the top of the file.
  - raised by gptoss:F1; agree: gptoss
- **[critical] pipeline/edl_rules.py:0** Undefined constant FINAL_TAIL_S referenced in g5_window logic
  - evidence: `return ((edl_rules.RUNTIME_FLAG_FLOOR_S + edl_rules.FINAL_TAIL_S, G5_RUNTIME_FLAGGED_MAX_S),
                    G5_DURATION_TARGET_S)`
  - fix: Define FINAL_TAIL_S (e.g., 14.3) or replace with the actual value.
  - raised by gptoss:F2; agree: gptoss

## Raised but not agreed
- gptoss:F3 [high] EDL_SOFT referenced but not imported (agree: 0)
- gptoss:F4 [medium] r4_sentences uses EDl_SOFT but variable name case mismatch (agree: 0)

## Added in cross-examination (not voted on)
- gptoss: [critical] Missing import of FINAL_TAIL_S constant used in g5_window logic
- gptoss: [critical] EDL_SOFT is referenced but not imported in run_fresh.py
