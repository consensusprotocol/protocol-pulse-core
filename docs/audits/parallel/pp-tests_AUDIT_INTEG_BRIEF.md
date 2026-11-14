# AUDIT BRIEF — pp-tests (tests only): the integrator's merge audit of phase 1 answered, and vo_fidelity v1.1

## THE LAWS (the session's rules, the two orders verbatim, and what to check)

Session pipeline_pp_tests writes TESTS ONLY (tests/adversarial/, docs/audits/parallel/pp-tests_*.md); it never edits
pipeline/, scripts/ or segment_v1/. Rules: never change what a check accepts in order to make something pass; nothing
measured is never a pass (L-m); fail closed (L-j); every pinned defect is `xfail(strict=True, raises=AssertionError)`
and every precondition is `pytest.fail` (adv_helpers.control), so a broken setup shows FAILED, never as the defect;
CPU only, no network, no GPU. Only report what you can verify from the diff. If uncertain, say so.

### Order 1 — the integrator's merge audit (verbatim)
NOT MERGED until these BLOCKING findings are answered (fix, or a reason the integrator can verify):
- B1 test_f3_release_auth.py: pytest.importorskip("release_auth") / ("telegram") lets the whole family vanish as
  SKIPPED (exit 0) on an import error. Use plain imports.
- B2 test_f2_provenance.py template builds a hook + ONE clip, which R-23 makes illegal: once R-23 lands, every cut_run
  test errors and the R-09 / R-22 pins XPASS for the wrong reason; the channel half of R-23 has no independent pin.
  Give the template a hook + two clips from two channels and pin each half of R-23 separately.
- B3 REQUESTS R-19 loosens the quote check; a request may not loosen what a check accepts; restate or withdraw.
- B4 REQUESTS R-02 / R-03: the proposed token-run check verifies an EMPTY quote; quote_in's 5-token minimum must be
  kept, with a test pinning an empty / short quote as unverified.
Not blocking (to fix with the above): the tautological CPU-guard test; F3's required set taken from the unit under
test; F4 call_gate's RAISED-as-pass path; garbage-reply tests without positive controls; pytest.raises without
match; the R-04 control vs its fix; the R-22 / R-09 / R-11 / R-17 pins; process-global conftest side effects (socket
patch, faster_whisper stub, sys.path) never undone; a network guard weaker than claimed (DNS, sendto, child
processes); production_reading / blocked() being the test's own model of run_fresh.stage_gates; the probes literal
list; the adjudicate verdict filter that includes the positive verdict; the 9:16 swap test's possibly empty list; the
L-b fixture-vs-fixture assertion; WindowAudio equivalence untested; the network test's try without else; LAW 24 (eight
xfails call qa_gates directly); _finals temp-dir leak; R-08 must fail closed; PP-E1 / E5 / E6 / E9 / E11 wording; the
G8 table "SETTLED" claim.

### Order 2 — orchestrator 05:25 ET (verbatim essentials)
The VO gate is being corrected to classify each VO / title / caption line as (A) ATTRIBUTION (says or implies what a
named speaker / show said, thinks or did: strict; same polarity, SAME OR WEAKER certainty; the attribution verb must
match the clip's own hedge: "thinks" for "I think", "feels" for "I feel like", "says" only for a flat assertion), (B)
FACT in the brand's voice (strict: maps to selected sentences, never from the trend brief), (C) PRODUCTION (must match
the manifest), (D) HOST COMMENTARY (the host's own opinion, question, tease or takeaway attributed to nobody: allowed
without clip support only if (i) no checkable fact / number / price / date / named person or company, (ii) does not
characterise any speaker's view or relation to another speaker, (iii) not a financial imperative or prediction, (iv)
not an accusation, (v) cannot be mistaken for a quote). A line the classifier cannot place is strict (A / B).
"Extend the vo_fidelity corpus NOW (append a v1.1 section, keep v1 ids stable): >= 15 MUST-PASS honest class-(D)
lines written against real selected sentences (takeaways, questions, teases), >= 10 MUST-PASS hedge-matched
attributions ("X thinks ..." over a clip that says "I think ..."), and >= 20 MUST-FAIL lines that LOOK like commentary
but smuggle something: a number or price, a named person, a recharacterisation ("even the bulls are nervous"), a
certainty upgrade ("thinks" clip -> "knows" / "confirms"), an invented relation ("and X answers him"), a prediction, an
imperative, an accusation, a present-tense price claim stale against the same universe (title "Bitcoin ran from 16K
to 126K" on a night the universe's news is Bitcoin near $73,000). Each case carries its expected class and verdict."
Order 05:30: spend freeze; the frontier baseline is cancelled; $3 total for audits.

### What to check, most important first
1. Each v1.1 case's EXPECTED label (in build_corpora.py: v11(...) calls; the clips are POOL / HPOOL entries whose
   selected sentences are quoted in each case's why): is every must-pass D line honest under (i)-(v)? Does every
   hedge-matched attribution keep the clip's hedge and conditions? Does every must-fail line really break the rule
   named in `rule`, and nothing else in its package (a confound)?
2. Each B1-B4 answer: correct, complete, verifiable. Each new or changed strict xfail fails for exactly its reason
   and can flip only with its own fix (R-09, R-22, R-23 x2, R-27, R-28, R-11, R-17, R-04).
3. Any test that can now pass vacuously, or that changed what a check accepts.
4. conftest.py: the guards' install / remove (scoped to tests/adversarial), the child-process allowlist, no GPU.
5. Doc claims (REQUESTS, BIBLE) that the code or tests do not show.
At most 15 findings, most severe first: SEVERITY (CRITICAL / HIGH / MEDIUM / LOW), file + quoted evidence, why, fix.

### Testing philosophy (the wall's own rules)
Fail loudly and specifically: a pinned defect is the ONLY way its test can fail; controls are pytest.fail; pins of production text (the stage_gates lines, the inventory, the CUDA setter scan) are deliberately brittle so that a change in production is a visible decision.
