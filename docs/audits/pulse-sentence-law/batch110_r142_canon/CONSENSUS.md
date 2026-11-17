# Batch 110 (ruling 142 (1) + (2): the sign fix and the word-form pair; decoder lockstep): consensus

| Cycle | qwen27b | gpt-oss |
|---|---|---|
| 1 (H1-H4) | PASS (0.92), 26.7k characters of reasoning | no verdict (token cap). Its trace took H1-H4 one by one, concluded "no defect", then looped. |
| 2 (break-it T1-T3) | PASS (0.92), 48.0k characters | FAIL: F1, NOT a defect |

**gpt-oss c2 F1, NOT a defect.**
- The claim: the `crit` set comprehension is a syntax error because an `if` clause comes before the second `for`.
- Why not: Python's comprehension grammar allows `if` clauses between `for` clauses (`{t for o in ops if keep(o) for t in toks(o) if crit(t)}`). pipeline/pinned.py compiles (py_compile), and test_ruling17_lock's TestRuling142 runs through that line.

**Consensus:** no defect.

**Own evidence:**
- MUST_FAIL_OLD_CODE.log: 4 must-fail tests fail on 2a472f82; 2 controls pass on both (a real sign keeps its sign; a name whose letters differ still holds under L-v 2).
- MUTATIONS.log: 6 of 6 killed.
- The builder's mirror: 45ad6040 (pp-selectid_audit_20261117_1451).
