# Audit 20261124_0826_N_r162_1: findings checked against the code

Seats. Cycle 1: qwen27b FAIL (1 finding), gemma PASS, gpt-oss no answer (its output is capped at effort high). Cycle 2 (cross-examination): qwen27b and gemma answered and added nothing; gpt-oss gave no answer.

## qwen27b F1 [critical], gemma agreeing: "a moment cut inside a sentence, or a window record, is kept when the out-edge model calls it complete"

**Refuted. The OUT edge's sentence end is enforced by a second, independent check, unchanged and outside this diff.**

- The second recogniser's CUTTABLE check runs on every clip of every package (pipeline/transcript_truth.py:279).
  - OUT passes only when the recogniser's word at the clip's last word ends in terminal punctuation AND the recogniser heard a next word: `ok = ws[i]["text"].rstrip().endswith(TERMINAL) and nxt is not None`.
- This change makes a failing OUT edge HARD.
  - pipeline/package.py:197, soft_edges(): `if not bad or "out" in bad or ...: return None`.
  - So the voiced line-up's per-clip check drops the clip (package.py:4715-4716), as do the no-voice line-up's (package.py:4265) and the spotlight's (spotlight.py, "L-v 2 / CUTTABLE").
  - The inventory's "cuttable" row is FAIL, and package_pin requires it PASS.
- owner_rules.out_edge (the complete-thought question) is asked IN ADDITION, because a clip can end on a full stop while the thought runs on: the afd8977d opener.
- So a clip seals only when BOTH hold: the recogniser hears its sentence end at the out point, AND the complete-thought question says its last sentence finishes the thought.
- A moment cut inside a source sentence (or a window record) that passes both ends on a sentence the recogniser hears and on a complete thought. The ruling asks exactly that: "The OUT edge of every clip must fall at the end of a sentence or a complete thought".
- Only the EXTENSION is withheld from such a moment, because a whole-sentence span would move its IN edge (tail_variant.extend raises).
