# Cycle 2 consensus (pp-selectid_audit_20261117_1351, ruling 141 (2): STAND_ALONE soft, the builder's half)

SEATS ANSWERED: 3 of 3. qwen3.8-27b and gemma-4-31b-it: P0/P1 none. gpt-oss-20b: one P1: stand_plain's fallback to the
raw stand_alone.opener string can put a code ("fault starts_mid_thought") in front of PBX if opener's wording changes;
ruling 138 (3) says no codes. qwen raised the same as a P2 in cycle 1.

## ACCEPTED AND FIXED (the only change from cycle 2 to cycle 3)
stand_plain's last line no longer returns the raw reason: any wording other than opener's two clip refusals now reads
"the clip scorer does not confirm it stands alone" (a fixed plain sentence). New test: opener patched to an unknown
wording, the fixed sentence comes back. Unreachable today (opener's not-ok clip wordings are exactly the two matched,
plus "empty segment" for a moment with no text, which never reaches the pool), and safe if that changes.
Suites after the fix: tests/package test_ruling_137 / test_medley / test_angles 316 passed; dev59 suites (before the
one-line fix) 41 files / 899 tests, exit 0.

## Cycle 3 is asked to confirm the fix only.
