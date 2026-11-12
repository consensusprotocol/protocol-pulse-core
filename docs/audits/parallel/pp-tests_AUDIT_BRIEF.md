# PP-TESTS GOSPEL — the adversarial test wall (session pipeline_pp_tests, 2026-11-12)

## WHAT THIS FEATURE IS
A TESTS-ONLY batch for the Protocol Pulse "Pulse Check" video pipeline (a 60-70 s Bitcoin news medley cut from other
channels' YouTube clips; nothing is published by these tests). A red-team audit found checks that pass when nothing
was measured and text comparisons that disagree with each other. Production fixes are made by another session; this
batch builds the adversarial test wall that proves each fix and catches the next regression: tests/adversarial/
(five families) + tests/fixtures/adversarial/ + docs/audits/parallel/pp-tests_*.md. No production file is changed.
  1 text / meaning fuzz: the canonical text form (pipeline/canon.py) and every comparator using it; surface variants
    ($40 trillion = 40 trillion dollars, HTML entities, split tokens, unicode, number words) must compare EQUAL;
    meaning mutants ($81,000 vs $18,000, 16% vs 60%, has vs hasn't, million vs billion, Fed vs Treasury, -5% vs +5%)
    must compare UNEQUAL; idempotence canon(canon(x)) == canon(x)
  2 coordinates / provenance: synthetic transcripts at a known offset, a source whose bytes changed under the same
    name, a dirty cache hit, a selection lock verified against another transcript
  3 authorisation mutations against the release authorisation (law L-j): missing / unknown / 'PASS (waived)' rows,
    empty evidence, a digest of another file, the 9:16 swapped, a skipped gate, a stale manifest: all must refuse
  4 vacuity: every REQUIRED gate called on empty / zero / None / NaN input and every model reply that is empty /
    malformed / not JSON / JSON of the wrong shape: FAIL or INCONCLUSIVE, never PASS
  5 reference integrity (CPU only): hashes and manifests of the two frozen references, law L-a (sign-off == card ==
    clips), law L-b (no fade over an edge word), and the open claim that the approved reference fails 9:16 G8
A test that exposes a real defect stays in place marked xfail(strict=True) with the finding id and a written request
(docs/audits/parallel/pp-tests_REQUESTS.md); a strict xfail flips to a failure the moment the fix lands.

## THE LAWS
- TESTS ONLY: nothing under pipeline/, scripts/ or segment_v1/ is edited; defects go to pp-tests_REQUESTS.md.
- CPU ONLY: no GPU (no Whisper, no face detector, no NVENC, no renders); GPU paths are stubbed or injected at their
  public seams; CUDA_VISIBLE_DEVICES is emptied; a session check asks nvidia-smi whether the suite held GPU memory.
- Exercised through the real public entry points, not private helpers (stated where a private rule is the only seam).
- Every test either passes or is a strict xfail tied to a written request; a strict xfail must fail for its stated
  reason (each was read with --runxfail), never because the test itself crashes.
- Genuine-pass AND must-fail cases in every family: a control that passes proves the mutation is what fails.
- Nothing measured is never a pass (law L-m): a missing reference is a FAILURE, not a skip.
- Fail closed (law L-j): release is authorised only on exactly the bytes the gates measured.
- Never change what a check accepts to make something pass; references are read-only and never adjusted.
- One command, under 5 minutes on CPU: python3 -m pytest tests/adversarial -q.
