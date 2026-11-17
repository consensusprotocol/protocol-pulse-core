# Cycle 1 consensus (pp-selectid_audit_20261117_1057, ruling 135)

SEATS ANSWERED: 1 of 3 (qwen3.8-27b: P0/P1 none, a traced review; gemma-4-31b-it and mimo-v2.6-flash-rl spent their
whole token caps with no answer). One seat is thin: cycle 2 adds gpt-oss-20b at effort medium (the seat the
integrator's ruling 135 audits answered on) and drops mimo (empty twice today).

## Changed since cycle 1's diff
1. canon.same_words gained `stray` (the integrator's own cycle-2 finding, Heimdall batch 104 c2: "one reading ALONE
   hears" a stray letter, but same_words sees only two sides): a single consonant is dropped only on the side named in
   stray. The integrator passes none in the lock (a lone letter there is a token; 131 (A)'s vote of three decides it)
   and stray="y" in ruling 72's comparison (the second recogniser's side). This side mirrors it: class_131 passes none;
   class_84 passes stray="x", because its FIRST argument is the spoken text, the second recogniser's reading. canon.py
   is the integrator's final (commit 8cb2e0b7, sha256 3c20e27f75b2), byte-identical.
2. tests/package/test_attest.py: "a filler on the approved side alone" now is spelling only (135 (d)); a lone letter the
   LOCK (approved side) carries still holds; the second recogniser's stray 'h' is no word.
3. Mutations M1-M28 after a control run: 28 of 28 killed (M27: stray removed in class_84; M28: stray on both sides).
