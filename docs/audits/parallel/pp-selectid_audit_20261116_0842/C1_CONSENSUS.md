# C1 CONSENSUS — pp-selectid audit 20261116_0842 (RULING 119 (1): the candidates path's stand-alone floor)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: qwen 0,
gemma 0, mimo 0. Cycle 1: $0.0063 of Heimdall, not capped.

A CORRECTION TO THE QUESTION (the integrator's finding, 08:44 ET): its "UNCHANGED GUARDS" line was WRONG to say the render's
validate "(stand_alone.check_edl, all clips together, 3.5) still checks every pin". Validate re-asks the scorer ONLY for the
clips that need asking (a clip after the hook opening on a conjunction or reply fragment, or a trimmed clip), ALONE, at 3.5,
with its own call or the production cache, and never reads the pin's scorer_verdict or a stand_alone_bar; so a floor on
this side alone would seal pins the render then HOLDs at validate (shown with production's check_edl and a canned 3.0). qwen's
P2 ("if affirmed_verdict is also used by the final render validation") points at exactly this. THE LANDING THEREFORE: both
ends together or not at all (the integrator's half affirms exactly the marked segments at validate, on the same code and
weights and the pin's own seal, never touching the scorer's files), and only on the orchestrator's explicit yes (STATE
08:49, no default: a loosened integrity gate, ruling 106).

CHANGED AFTER CYCLE 1 (in cycle 2's diff):
1. THE WEIGHTS: the calibration was measured on scorer code edd54964a5ab... AND the model's weights (the Ollama digest of
   gemma3:27b). The floor now also requires the VERDICT's own "digest" to EQUAL the full digest
   a418f5838eaf7fe2cfe0a3046c8384b68ba43a4435542c942f9db00a5f342203 (the measured one: APPROVED_CLIPS_SCORER.json's
   scorer.digest; the integrator adds each verdict's full digest to its verdicts file in its half, and its validate
   compares the running gemma3:27b's digest exactly too). A verdict without it, with another, or with only a prefix of it
   gets no floor (fail closed); the sealed verdict carries it; package_pin.affirmed_verdict requires it, exactly.
   Tests: no digest, another, or a bare 12-hex prefix: 3.5 only, and the pin check refuses each.
2. mimo P3 / qwen P3 (a 12-character prefix match on a 64-character sha256): the scorer code is compared EXACTLY, the
   full sha256 edd54964a5ab15f4a17d74ecbe40bcbccf2fdf2818df97881e8f7039a4721f53; the mark's scorer_sha is that full value.
   No prefix comparison is left anywhere.
3. The comment beside the constants in package_pin said "The render's validate (all clips together, 3.5) is unchanged and
   still checks every pin": FALSE (the correction above). Rewritten to say what validate does and that the floor holds
   there only through the integrator's half, landed together on the orchestrator's yes.

Cycle 2 was first started at 08:51 on the diff with a 12-hex digest prefix and stopped at 08:53 when the integrator gave
the full digest; its one answered review (qwen, P1_OR_WORSE 0, on the superseded diff) is kept as
C2stopped_qwen3.8-27b.md with its prompt and diff, and its Heimdall dollars stay counted in COST.json.
Mutations F1-F10 (F7, F8: any weights; F9, F10: a bare 12-hex prefix of the weights) run on this diff after a control run;
results at landing.

P3 noted, not changed: mimo "affirmed_render is written but read only by a test": it is the record of the render's own
verdict beside the floor's, kept for the build's record and the pin, where the integrator can read why a clip was admitted.
