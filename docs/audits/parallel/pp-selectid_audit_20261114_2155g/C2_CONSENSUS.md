# Cycle 2 consensus: pp-selectid audit 20261114_2155g (ruling 107 (1): the guard)

qwen3.8-27b reports P1_OR_WORSE 0 (its "N5" heading resolves in its own text) and glm-5.3-flash 1. They disagreed, so
Grok was asked as the third: 0. Both cycle-1 fixes (errors found by structure, routing in the fingerprint) are
confirmed.

glm's N1 (only the newest finished build decides) is REFUTED AS A DEFECT. It is a deliberate, documented and tested
choice:
- the docstring says the NEWEST earlier FINISHED build decides;
- test_only_the_newest_finished_build_counts asserts that a newer finished build with another fingerprint ("G")
  shields an older match ("F");
- mutation G4 ("an older match counts") is killed by that test.
Its cost is the conservative side: after a code change and a revert, one extra build runs. glm itself finds no P0 and
says the guard never skips a build that has new work.
Noted P3s (no change): the result files are hashed by name, size and mtime (a missed skip costs money, never
correctness); a code-read error stops the build before any router (fail closed); held work is read where ruling 102
records it.

AUDIT COST: $0.0393 vendor-reported (cap $1.00):
- C1: qwen and glm $0.0060;
- C2: qwen, glm and Grok $0.0333.
VERDICT: lands, before the batch's second full build.
