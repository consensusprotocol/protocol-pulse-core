# Audit 1057 (ruling 99, the circuit breaker), cycle 2: consensus

All three reviewers: SHIP yes with conditions.
- grok-4.20: no P0, no P1. Its mediums (the state's location, every leg open, the .lock file) were refuted or recorded
  in cycle 1. Its conditions:
  - the state's home documented (it is: the module docstring and ruling 87's precedent);
  - a dead-trial re-claim (tested at the module, since the claim lives in the shared file);
  - the count on STATE line 1 from a real build (the first build after this commit; its log line is quoted on STATE).
- qwen3.8-27b:
  - (1) "ab's scope in _late": `ab` is _late's own first parameter, `def _late(self, ab, value, error)`
    (providers.py:934), and the late-runaway check is inside _late.
  - (2) a malformed trial_at: `ta is not None and ...` short-circuits, so it cannot raise. Pinned by a test now.
- glm-5.3-flash:
  - (1) "show that the usage block fires only on the late path": it is inside _late, which only _within's late thread
    calls, from the one call site (providers.py:1253-1254). A test now pins exactly one breaker event for a call that
    ran away.
  - (2) document the dropped late runaway while the breaker is open: done (module docstring). Its tokens stay on record
    in the late_answer line.
  - (3) reset misses on a trial-failure re-open, as every open does: done (unobservable today, so no mutation can see
    it; a latent count removed).

Upper-bound cost: about $0.34 (grok, $0.113, $0.145). Audit 1057 in all: about $0.70. Outside SPEND_LY.json.

## Implemented after cycle 2 (no change in behaviour)

- circuit_breaker.record: m["misses"] = 0 on a trial-failure re-open (glm 3).
- The module docstring: an outcome of a call in flight from before an open changes nothing and is no event (glm 2).
- Tests: a malformed trial_at claims the trial without a crash (qwen 2); one runaway call gives exactly one event (glm
  1).
- 10 breaker tests; the mutation check, 20 of 20 killed.
- FINAL.diff = C2_STEP.diff plus these four (the line, the docstring sentence, the two assertions).
