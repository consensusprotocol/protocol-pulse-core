# Batch 116 (ruling 139 on the render lock), cycle 1 completed and cycle 2
Cycle 1: gpt-oss F1 (high), "flag_sentence_edges opens edl.json and reads clip_id unchecked". FAIL-CLOSED, not a defect:
stage_cut runs after validate wrote edl.json, and every cuts_final.json entry carries clip_id. An exception there fails
the stage, which HOLDS the run; no bad edge can pass. qwen's cycle-1 answer was lost at the Nov 18 pause.
Cycle 2: qwen27b (high): FAIL, 2 findings. gemma (medium): FAIL, 1. gpt-oss: no verdict at high or medium (reasoning
loops, token limit).
- gemma (critical), "_edge_row returns nothing when the boundary is valid": DISPROVED. pipeline/sentence_law.py:1009-1031
  returns on every path; the diff hunk ended mid-function.
- qwen (high x2), "gate_g17_edges and edges_on_final call edge_plan without trimmed, so a trimmed IN edge can be
  softened in G17": DISPROVED for the verdict. Both pass the plan to edge_word_fidelity, which measures through
  edge_word_bounds (sentence_law.py, from the cut points' own audio levels). edge_word_bounds never reads the plan, so
  trimmed or not, softened or not, G17's measurement is identical. The omission predates batch 116. Making the calls
  consistent would move the DECODER (a lockstep) for no change in any verdict: NOT DONE.
