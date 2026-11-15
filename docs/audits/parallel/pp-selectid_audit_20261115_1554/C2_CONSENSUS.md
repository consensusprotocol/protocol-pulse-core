# C2 CONSENSUS — pp-selectid audit 20261115_1554 (RULING 116 Q3: the calibrated line-up bar)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0) and glm-5.3-flash (0): they agree, Grok was not asked. Cycle 2: $0.0066; the
audit $0.0543 vendor-reported. No P1 in either cycle; no third cycle. Both checked cycle 1's change (the takeaway-only
rewrite reads the package's own hook label) and every site of the QUESTION's check (2).

P2s noted, NOT changed (the landed code is the audited code):
- glm "lineup_bar_mark names the clips-alone verdict's calibration sha only; the two verdicts could straddle a
  re-seal". With valid_h null and one fixed source the file is not re-sealed in a build; a re-seal mid-build would also
  change the file's mtime, and both verdicts would then name their own sha in their own records (pk["checks"]). If
  ever needed, the mark can carry both; it is the integrator's note line either way, never a gate.
- glm "a failed stat caches (None, minute) for the rest of that minute": the hook bar's same rule; a file that appears
  within the minute is read at the next minute (the standard bar meanwhile, the stricter one).
- qwen "the rig's coherence stub differs from production's signature": it takes (router, pk, *a, **k) and reads
  k["hook"], as build() calls it (hook=...); the stub's output is production's shape.
- qwen "floors_for returns a copy": deliberate (no caller can change the live bar).

FINAL DIFF: FINAL.diff (written at landing). Suites: all 40 files, 797 tests; mutations 13 of 13 killed after a
control run.
