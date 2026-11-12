# claude-sonnet-5-5 (effort high) 138 s stop_reason=end_turn usage=in 74978 / out 17346

# Cycle 2 review: pp-selectid-p2 (chunk B, fixed diff)

**Two caveats first.**
- The "YOUR CYCLE 1 OUTPUT" slot in the prompt was empty. I score against the four reviewers' tables and what the diff now shows. I am Claude, not one of the named GPT or Gemini models.
- This chunk has no module code and no R7 patch text, only the design doc, tests and drivers. Anything about `package.py`, `package_pin.py`, `vo_fidelity.py` or the deployed `pinned.py` is inferred from tests, or unverifiable. I mark which.

---

## 1. What the others caught that I would have missed

I have no Cycle 1 output to compare against, so this is what I would have missed or under-weighted:

| Finding | By | Status in the fixed diff |
|---|---|---|
| Pin gate evidence is self-reported and bound to nothing | fable P0-1, opus P0-1, sonnet P1-1 | Addressed by `package_pin.seal` plus the gate inventory (`REQUIRED_GATES`). See finding N1 below for what is still unproven. |
| Fidelity verdict passes on `claims: []` or partial coverage | fable, opus, sonnet | Fixed and tested: `test_gates.py:1520-1526` (`[]` and half coverage give `VERDICT_INCOMPLETE`). |
| L-v 2 optional (`truth_dir=None`) | fable P0-2, sonnet P1-2 | `proof_packages.py:673` now requires `--work-dir`. The pin refuses a `second_pass` of "NOT RUN" (`test_angles.py:1278`). |
| Config test covered too few roles | sonnet P1-3 | Fixed: `test_providers.py:2076-2081` covers four roles against every writer in the chain. |
| Alt pin overwrites the primary pin | sonnet P1-5 | Fixed: `proof_packages.py:659` passes `name=` per alt. |
| Truthiness flag check | fable P1-1 | The smoke test now exercises a string `"true"` (`smoke_r7.py:1116-1122`). That is one case only. |

Grok's Q1 82 / Q2 93 / Q3 88 rested on R7 lines that are gone. It never noticed the flags were self-reported. I disagree with those scores. Its Q2 evidence (the router honours `avoid_vendor`) is fine, but "no vendor hard-coded" ignores that the drivers do hard-code vendors (see N4).

## 2. Agree or disagree with the key Cycle 1 findings

- **Self-attested flags (C1).** Agree it was real. The design-level fix is sound, but the integrator half is still unproven (N1).
- **Opus's "tautological sha assertion".** Agree. It is still present (`smoke_r7.py:1097-1099`).
- **Sonnet's "production test blesses partial support".** Agree, still open (N6).
- **Fable's "no `package.build` test".** Agree, and it is worse now that the inventory is the control (N2).
- **Opus's "unmeasured speaker counts as usable".** Partially agree. `test_moments.py:459-462` shows it is a candidate only, and the pin refuses an unmeasured second pass. That is acceptable if `second_pass: PASS` really requires a measured speaker (N5).
- **Sonnet's "Step A can land on the writer's vendor".** Partially agree. Step A never sees the package, so there is no self-grading. But the driver contradicts the design (N4).

## 3. New findings

**N1 (P1, escalates to P0 if the test fails). The R7 half of the C1 fix is untested at the integration point.**
- `smoke_r7.py:1111-1115` builds a tampered pin and only asserts that `package_pin.seal(...)` differs from the stored sha. It never calls `pinned.build_edl(tampered, …)`.
- Line 1097-1099 compares `edl["moments_package_sha256"]` to a seal computed from the same pin's own fields. If `build_edl` merely copies `package_sha256`, that passes. It does not prove the deployed code recomputes it.
- The final print claims "an edited pin breaks its seal". True at function level only.
- The only `build_edl` refusal exercised is `context_integrity_ok = "true"`.
- Not exercised:
  - `vo_fidelity_ok` as a string
  - `checks: null`
  - `moments_package` as `None`, `[]` or `""`. This silently becoming a plain pin was fable P1-2 and opus P1-1. Line 1123 only covers `pop`.
  - tampered `edl_vo`, title or caption with a stale sha
  - missing `edl_vo`
  - duplicate or non-int `after_clip`
- Required: one `build_edl` call per case above, each asserting `PinError`.

**N2 (P1). The producer of "PASS" has no test.**
- `to_pin` is well tested for refusing non-PASS rows (`test_angles.py:1270-1287`). But `PK.inventory(fid, dup, rt_ok, r4, ctx_, a_by, exc, tru, ok_c, coh)` (`run_given_package.py:997`) is what writes the rows. It has no test.
- Cases that must yield non-PASS:
  - `fid["verdict"] is None`
  - `measured` false
  - any reply `replayed` or `cached`
  - exclusion not `keep`
  - `tru[...]["ok"]` false
  - `n == 0` with status PASS ("ran on nothing")
  - `price_now_measured` false (see N3)
- The pin also lacks tests for:
  - an extra or missing key relative to `REQUIRED_GATES`
  - `status: True` instead of the string
  - PASS with `n == 0` or `by` null
- `package.build` itself is still untested: writer loop, rewrites, drop-and-repack, coherence, ranking. Only live proof drivers call it.

**N3 (P1). `ALL PASS` ignores `price_now_measured`.**
- `run_given_package.py:995` excludes `price_now_measured` from `all(...)`.
- If no current level is measured (empty `levels`), PRICE_NOW cannot decide anything on "is this price today's". Whether the inventory's `price_now` row then reports NOT MEASURED is not visible.
- `test_angles.py:1228-1233` tests only the case where one current level exists.
- Needed: a test that empty `levels` on a line with a price makes the gate fail or not-measured, and that the printed `ALL PASS` agrees with the inventory.

**N4 (P2). The driver contradicts the design on Step A.**
- Design `:92-93` says Step A is "never on the writers' vendor or family".
- `run_given_package.py:917` calls `CI.step_a(router, contexts, writer_vendor=None)`, and the chain puts `anthropic:claude-opus-5-5` first (`:826`), when the VO's author is Claude.
- It is probably harmless: Step A judges only source text, and speaker verification requires verbatim evidence checked in code. But the pinned package tonight was gated that way, and the inventory is supposed to evidence L-x.
- Fix: record the back-end vendor and family per row in the inventory. Have `to_pin` refuse any verdict row whose vendor or family is in the package's author set, or amend the design to carve out Step A.
- Related: the driver hard-codes `SCRATCH=/tmp/claude-1000/...` (`:820`). The `blind()` function is duplicated in `ci_mustfail_check.py`, `run_exam_record.py` and `ab_roles.py`, so it can drift from the harness. Spend limits differ across drivers: `40.0` at `run_exam_record.py:746` and `ab_roles.py:1740`, `64.28` elsewhere.

**N5 (P1). L-v 2 can degrade silently.**
- The `transcribe` chain falls back from the diarised OpenAI model to ElevenLabs Scribe. `test_providers.py:2038-2052` proves failover.
- Nothing in this diff proves that `verify_segment` returns not-ok when the fallback lacks speaker labels. `TT.speaker_turns` returns `None` for "not measured" (`test_angles.py:1298`), and `second_pass` passes only if `ok` is true.
- Needed: a test that `verify_segment` with `turn_change_inside is None` is not ok. The inventory evidence should record which transcriber ran and whether speakers were measured.

**N6 (P2). Fidelity tests still bless weak support.**
- `test_gates.py:1539-1544`: support "Links to every source are below" is accepted for the claim "Clips from Coin Bureau and Stephan Livera." That covers half of the claim. `check` is called without a manifest.
- Only a single-line `LINES` is used. No test covers a multi-slot verdict with claims for only one slot, or a title or caption with no claim.
- A three-word verbatim support such as "Bitcoin is the" meets the code's rule. The code proves provenance, not entailment, and leaves entailment to the model's "yes". The design admits this, but there is no test pinning a minimum-informativeness policy.

**N7 (P2). The seal and the published links.**
- The seal covers segments (video_id, start, end, text, transcript_sha256), VO, title, caption and the inventory. It does not cover `url_30s_before`, `channel` (indirectly via `signoff_expected` only), `angle`, `topic`, `type` or `runtime_s_estimate`.
- Those fields reach the EDL and the post.
- `url_30s_before` is a link published to viewers. Derive it at render time from `video_id` and `start`, or seal it.
- The seal is also an unkeyed sha256. It detects drift and accidental edits, not a deliberate editor who recomputes it. Release authorisation should compare against a seal recorded at gate time outside the pin file.
- `test_angles.py:1275-1277` checks seal sensitivity to the title only, not to segment text, times, `after_clip` or gate rows.

**N8 (P2). The smoke test's circularity on verbatimness (Q3).**
- `smoke_r7.py:1043-1054` builds the fake transcript from the pin's own `approved_text`, and `validate_range` and `make_lock` are stubbed (`:1085-1092`). The smoke test therefore cannot detect a segment text that is not in the source.
- The segment texts are placeholders ("sentence {i} spoken on …").
- Run the smoke test also on the real sealed `MOMENTS_PIN.json` with real transcripts. That would prove clip text equals transcript text, or show how large the `approved_text_similarity` tolerance is.

**N9 (P2). Smaller items.**
- `test_angles.py:1238-1239`: the runtime and `FIXED_S` tests restate the implementation formula. The 60-70 s hard gate rests on assumed WPS 2.6. Replace the estimate with the measured render duration at release authorisation.
- Spend reservation is tested only sequentially (`test_providers.py:2007-2022`), but drivers use 8-10 threads on one router and ledger. Add a concurrent reserve test. Also test whether `Router.down` is thread-safe.
- Nine gate attempts tonight against stochastic judges. The inventory should record the attempt count, and policy should forbid re-judging unchanged bytes until a pass.

## 4. Revised scores

Cycle 1 is "not supplied" for me. Peers' Cycle 1 range for chunk B is shown for reference.

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| Q1 fail-open | n/a (peers 35; grok 82) | **55** | The seal, the inventory and exact-PASS refusal are real improvements, and the verdict is now fail-closed on empty or partial claims. Held down because the R7 recompute, the inventory builder and `package.build` are all untested here, and N3 is open. |
| Q2 vendor separation | n/a (peers 45; grok 93) | **55** | The router and config tests are good. Held down because nothing enforces vendors at the pin and the Step A contradiction (N4) remains. |
| Q3 verbatim and model text | n/a (peers 30-45) | **50** | Miner and angle contracts are strict, and model "reason" fields are forensic only. But verbatimness is untested in smoke (N8), and the seal omits links and `angle` (N7). |
| Q4 deterministic rules | n/a (peers 30-40) | **45** | Same as before. Only PRICE_NOW, ATTRIBUTION, HEDGE, NAME, NUMBER, QUOTE, RELATION and IMPERATIVE have a test, and the other rules are unseen here. |
| Q5 tests and R7 | n/a (peers 50) | **55** | Better tests exist, but the printed claims overstate what is exercised (N1), and `package.build` and `inventory` are not tested. |

## 5. Final priority list

**P0**
- None provable from this chunk. N1 becomes P0 if a tampered pin passes `pinned.build_edl`. The first delivery being REVIEW ONLY (L-q) is the only current mitigation.

**P1**
1. `smoke_r7.py:1111-1122`: add `build_edl` refusal tests for N1's list. Replace the tautological sha assertion (`:1097-1099`) with a comparison against an independently computed seal.
2. `PK.inventory` and `PK.cheap_checks`, tests in `test_angles.py` or a new `test_inventory.py` (N2). Add the `package.build` fake-router test with writer failover and rewrites.
3. `run_given_package.py:995` and the inventory `price_now` row: an unmeasured PRICE_NOW must fail or be not-measured (N3).
4. `second_pass` PASS must require measured speakers, with the transcriber recorded (N5). Add a `verify_segment` test for undiarised output.
5. R7 production call: confirm `work_dir` or `truth_dir` is passed. The proof driver is fixed, but the R7 call text is not in this chunk.

**P2**
6. Record vendor and family in each inventory row. Make `to_pin` refuse an author-vendor verdict, or amend design `:92-93` (N4).
7. Seal or derive `url_30s_before`, `channel`, `angle` and `type`. Verify against the gate-time seal at release (N7).
8. Run the smoke test on the real pin with real transcripts (N8).
9. Test multi-slot fidelity coverage, a title or caption with no claim, and partial manifest support (N6).
10. Concurrency test for the spend ledger and `Router.down`; unify `blind()` and the spend limit constants; remove the hard-coded scratch path (N4, N9).
11. Record the gate attempt count (N9).

## 6. Single highest-leverage change

Test the producer and the verifier of the seal end to end: make `package.inventory` provably emit non-PASS for every unmeasured, replayed, vacuous or author-vendor case, and make `pinned.build_edl` refuse every tampered or mis-shaped pin in the smoke test.

## 7. Production ready?

**Yes with conditions**, for the first REVIEW ONLY delivery (L-q) only. Not yet for automatic release.

**Conditions:**
1. Items 1-4 of the P1 list are done, and the smoke test passes on the deployed `pinned.py` with every refusal case.
2. Release authorisation (R7 item 4) verifies the seal against a gate-time record, and exact PASS on every row, before anything leaves REVIEW ONLY. This is not in the diff.
3. A human confirms that the first delivery's title, caption, VO and the `url_30s_before` links match the sealed pin.
4. The design and driver Step A conflict is resolved one way or the other.