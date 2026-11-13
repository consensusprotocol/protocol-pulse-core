# pp-selectid audit of the 22:40 rulings diff: cycle 2 dispositions (synthesis by the pp-selectid session, 22:59 ET Nov 12)

**Run.** Cycle 2 cross-reviewed the fixed diff (C2_STEP.diff, 86,345 bytes; prompt 118,468 bytes) with the cycle-1
reviews and C1_CONSENSUS.md. No reviewer kept a P0.
- grok-4.20-0309-reasoning (xAI): SHIP yes with conditions. No P0 / P1; one P2 (no_voice closes over build's locals).
- qwen/qwen3.8-27b (Heimdall, effort none): no P0, no P1. It accepts the cycle-1 refutations (the no-voice
  double-lock on flagged joins; a single settle per timeout).
- z-ai/glm-5.3-flash (Heimdall, effort none): SHIP yes with conditions; two P1s (N3, N8), both implemented.

**Spend:** about $0.55 at upper-bound prices.

## Implemented

| finding | disposition |
|---|---|
| glm N8 (P1): prove, without stubbing the gates, that a NO-VOICE package can reach exactly PASS on every required row | IMPLEMENTED: TestNoVoiceRealGates runs the real vo_fidelity.check and context_integrity.check_contexts (canned model replies) on a no-voice package, then the inventory, package_pin.gate_problems over REQUIRED_GATES + MEDLEY_GATES (empty), and to_pin. The test found a REAL gap, fixed: the pin's moments_package did not carry the no_voice record. It does now, beside "bridge" and "supply_exception" |
| glm N3 (P1): ruling 5's failover record must cover the takeaway writes, not only the angle call | IMPLEMENTED: each write's attempt record carries writer_tried, its Reply.tried |
| glm (cycle 1 P1-1, carried): a published time without an offset failed only at the pin, after every paid verdict | IMPLEMENTED: cheap_checks adds package_pin.recency_problems as rule RECENCY, before any paid verdict. Test: test_a_published_time_without_an_offset_fails_before_any_paid_verdict |

## Kept, with the reason

| finding | disposition |
|---|---|
| grok P2: no_voice() closes over build()'s locals (cleared, doomed, dropped, writers_*) | KEPT: it is a nested helper of one build call, and the closure IS the build's state, the same objects the line-up loop uses. Passing fifteen names would add surface, not safety. The Rig tests exercise it through build() |
| glm N2 (P2): the budget is not checked between the paid gates of one write | KEPT and documented: the stop is a SEARCH budget, checked before every line-up and every write. A write already through its gates finishes, and nothing more is spent after it |
| glm N1 / N4 / N6, qwen P2s (the pos sentinel, the test's padding, emoji U+FE0F / keycaps, the RECENCY wording) | KEPT as P2 follow-ups; none changes what passes |
