# Cycle 1 consensus (pp-selectid_audit_20261118_0821, ruling 147: the batch 114 mirror + the exception pin's cap)

SEATS ANSWERED: 2 of 3. gemma-4-31b-it: P0/P1 none. gpt-oss-20b: its 32,000-token cap ran out, no answer.
qwen3.8-27b: one P1 (its summary counts it twice), REFUTED:
qwen [P1] "SOFT_GATES does not contain EXCEPTION_GATE, so the existing assertIn test fails": REFUTED. SOFT_GATES has held
the literal "pbx_exception" since the ruling-144 landing (fc191b4e; package_pin.py:46, unchanged here, so outside this
diff's hunks), and EXCEPTION_GATE is that same string (package_pin.py:52). The test passes: test_lock_precheck +
test_ruling_105 + test_attest + test_ruling_137 + test_angles + test_medley 398 passed; dev61 suites 41 files / 924,
exit 0.
qwen's P2s / P3s on sentence_law.py (ONSET/TAIL text, gate_g16's trimmed path, a refusal message) concern the
integrator's file, copied byte-identical (sha256 48e5b639...) and audited on its side (two cycles PASS); not this
side's to change. The double content_flags / flags_cap call in to_pin: cosmetic.

## No change from cycle 1 to cycle 2.
