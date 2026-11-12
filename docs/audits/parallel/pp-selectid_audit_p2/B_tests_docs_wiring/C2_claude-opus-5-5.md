# claude-opus-5-5 (effort high) 209 s stop_reason=end_turn usage=in 74978 / out 20370

# Cycle 2 review: pp-selectid-p2, chunk B (tests, docs, harnesses), fixed diff

**Note on the packet.** The "YOUR CYCLE 1 OUTPUT" section is empty. I cannot quote what I said before, so I take the three Claude reviewers' chunk-B scores (fable, opus, sonnet) as my Cycle 1 baseline. Line numbers below are STEP.diff line numbers.

**Scope.** This chunk does not contain:
- `package.py`, `package_pin.py`, `vo_fidelity.py`, `context_integrity.py`, `transcript_truth.py` or `providers.py`;
- the R7 patch text (`pp-selectid_REQUESTS.md` is not in this chunk).

So the C1 fix is visible here only through its tests and harnesses. The test is not whether the fix was described, but whether the tests prove it.

---

## 1. What the others caught, and what Cycle 1 missed

- **Fable P0-1, opus P0-1, sonnet P1-1 (unbound self-reported checks).** This was the central defect and it was correctly identified. The fix (a sealed gate inventory) addresses it in principle. As shown below, the consumer side of the fix is still not demonstrated.
- **Sonnet P1-4 (manifest support).** Sonnet noted that the production-claim test accepts the unrelated support "Links to every source are below". That test is unchanged in the fixed diff (L1539-1544) and still passes. Everyone else, including the consensus, let it go.
- **Sonnet P1-3 (Step A runs before the writer's vendor is known).** This is real. The fixed tooling makes it concrete: see N3.
- **Fable P1-3 (`package.build` untested).** Still true. It is now worse: `PK.inventory`, the function the whole C1 fix trusts, has no test.

## 2. Agree / disagree

| Finding | Position | Why |
|---|---|---|
| Unbound, truthy checks (all Claude reviewers) | **Agree; partly fixed** | Fixed and tested: <br>• `to_pin` refuses NOT RUN, FAIL, replayed and lowercase "pass" (L1278-1287). <br>• The seal changes when the title changes (L1275-1277). <br>• Deployed `moments_vo` refuses `"true"` (L1116-1122). <br>Not proven: that the consumer recomputes the seal (see N1). |
| Malformed `moments_package` silently becomes a plain pin | **Agree; fix claimed, untested** | `smoke_r7` covers only a removed package (L1123-1126), not `[]`, `null`, `checks: null` or a missing `edl_vo`. |
| L-v 2 optional in the driver | **Agree; fixed** | `--work-dir` is now required (L673). A `None` work_dir is supposed to yield `second_pass` NOT RUN, which the pin refuses. That depends on `PK.inventory`, which is untested. |
| Pin clobbering in `proof_packages` (sonnet P1-5) | **Agree; fixed** | `name=` is now passed (L659-660). |
| Empty or partial `claims` pass (C2) | **Agree; fixed and tested** | L1520-1526 covers `[]` and half coverage. |
| `Canned` ignores `avoid_vendor` (sonnet) | **Agree; still true** | It now records `avoid_family` too. The assertion that uses it is partly vacuous (see N4). |
| Config test checks only `chain[0]` | **Agree; fixed** | L2076-2081 now checks every writer against every verdict role, coherence included. |
| Grok: Q2 93, Q3 88, "no package is returned when a hard gate fails" | **Disagree** | None of the gate code is in this chunk. Grok asserts properties of code it could not see (`package.build`, the R7 consumer). These scores are not evidence-based. |

## 3. New findings (not raised by anyone in Cycle 1)

**N1. The seal is never tested at the consumer. Its only end-to-end assertion is tautological.**
- L1097-1099 asserts `edl["moments_package_sha256"] == package_pin.seal(...)`.
  - `to_pin` computes the sha with `seal`.
  - If deployed `pinned.py` just copies `mp["package_sha256"]` (the cycle-1 behaviour), this still passes.
- The tamper test (L1111-1115) only shows that `seal()` returns a different hash for a different title. It never calls `pinned.build_edl(tampered, …)`.
- So "R7 refuses any mismatch between the recomputed sha and the pin" (consensus C1) is unproven against the deployed `pinned.py` 380a06f3.

**N2. The field the consumer gates on is outside the seal.**
- `seal(segments, edl_vo, signoff_expected, title, caption, gates)` (L1097, L1114) does not include `checks`.
- Deployed `moments_vo` decides on `checks.context_integrity_ok` (bad2, L1116-1122).
- If `pinned.py` reads `checks` rather than deriving the verdict from the sealed `gates`, then flipping `checks` from false to true leaves the seal valid.
- Either drop `checks` from the pin or have `pinned.py` derive it from `gates` (exactly `"PASS"`, `replayed` false) inside the recompute.

**N3. Tonight's pinned package broke the design's Step A rule, and `package_pin` did not notice.**
- `run_given_package.py` L917 runs `CI.step_a(router, contexts, writer_vendor=None)`.
- The context chain leads with `anthropic:claude-opus-5-5` (L826). The author is `{"vendor": "anthropic", "family": "claude"}` (L825).
- The design (L92-93) says Step A is "never on the writers' vendor or family".
- Step A's `speaker_verified` decides which speakers the author's text may name (L921-925 feeds `segs_v` into VF's ATTRIBUTION). That is a same-family judge licensing a same-family writer.
- Two further points:
  - The inventory records `by` for each row, but `package_pin` evidently does not check `by` against the writer set. `smoke_r7` pins `"by": "smoke"` (L1070).
  - The author vendor itself is "assumed a Claude session" (L793-794).
- No speaker was verified tonight, so there was no harm. The rule is still unenforced.

**N4. The vendor-separation assertion for context integrity is partly vacuous.**
- L1388: `judged = [c for c in r.calls if c[0] != "viewer_takeaway" or c[1] is not None]` silently drops any `viewer_takeaway` call made without `avoid_vendor`.
- B0 (the clips alone) and B (the package, including the VO) share that role, and `Canned` does not record prompts.
- So if B lost its `avoid_vendor`, the test still passes.
- Fix: record a prompt marker and assert that exactly the B call carries `("openai", "gpt")`.

**N5. A speaker can be "verified" by evidence outside the selection.**
- L1474-1476 passes a case where "Welcome back to my channel" is in the unselected context and the selection follows it.
- The host-intro-then-guest-answers pattern (90 s window, L162) therefore yields `speaker_verified=True`. `run_given_package` L924 then sets `speaker = channel`.
- This allows "<Host> thinks …" over a guest's words, a direct L-v 1 / Q3 false attribution.
- Diarisation only checks for a change inside the clip (design L203), not between the evidence and the clip.

**N6. Under rulings 3 and 5 the decision rule inverts severity.**
- An answer of "uncertain" fails the package:
  - `entails`: L1407;
  - `stronger_certainty`: L1414.
- A stronger answer ("no" / "yes") with no quoted words is only a note and passes (L1427-1439).
- So a judge that is sure the clip is not entailed, but omits the quote, passes the package where a hesitant judge would fail it.
- The 41/41 must-fail run measures only corpus cases. Recommend one re-ask demanding the quote; if it is still unquoted, treat it as UNCERTAIN (a failure).
- This needs an orchestrator re-ruling. I am flagging it, not overriding it.

**N7. Production claims pass on irrelevant manifest words, and no manifest is even supplied.**
- L1539-1544 has the claim "Clips from Coin Bureau and Stephan Livera." supported by "Links to every source are below".
- `self.verdict` passes no manifest to `VF.check`.
- **Likely false PASS (not verified):** a caption "Clips from five shows" on a 3-clip package. NUMBER treats a bare ≤10 as a production count, and the verdict accepts any manifest sentence.
- C-class support must be the manifest field that states the claim, e.g. the channel list or `len(segments)`.

**N8. The inventory is unit-tested only as an input.**
- `PK.inventory(fid, dup, rt_ok, r4, ctx_, a_by, exc, tru, ok_c, coh)` (L997) has no test. Nothing shows that:
  - a FAIL / `None` / exception maps to a non-PASS row;
  - a replayed reply sets `replayed: true`;
  - `n: 0` is refused;
  - PRICE_NOW with no measured levels is not PASS.
- `run_given_package` prints `ALL PASS` excluding `price_now_measured` (L995).
- `to_pin` is not tested for refusing:
  - `PASS` with `n: 0` or `by: None`;
  - a REQUIRED gate row deleted;
  - `replayed` missing or `"false"`.

**N9. Recordings are deliverable whenever the run is live.**
- A recording served in a live run is `cached`, and `replayed` stays false (L1989-1990; design L57-58).
- The recording directories are committed fixtures (L252, L619).
- An edited or stale recording, for example one from before a model update, is accepted as a fresh measurement with `replayed: false`.
- Either record `cached` in each inventory row and require a hash of the recording's provenance, or refuse `cached` for delivery.

**N10. Smaller items.**
- `yield_table` L1650-1656 counts any pin whose existing gate rows say PASS as a package. It does not check `REQUIRED_GATES`, `replayed` or the seal; it should call `package_pin`'s verifier.
- Spend limits on the same ledger differ by script:
  - 40.0 in `ab_roles` L1740 and `run_exam_record` L746;
  - 64.28 in `proof_moments` (L280);
  - env-overridable in `ci_mustfail_check` L549.
  Unify them in the ledger.
- `run_given_package` hard-codes model names (L826-833, against L-x) and a session `/tmp` path (L820).
- The `speaker_turns → None` comment claims "the pin refuses an unmeasured second pass" (L461-462). No test shows that `verify_segment` returns `ok: False` when `turn_change_inside is None`.

## 4. Revised scores

| Q | Cycle 1 (Claude chunk-B baseline) | Cycle 2 | Why |
|---|---|---|---|
| Q1 fail-open | 35 | **50** | Gains: pin refusals are tested; `--work-dir` is required; empty claims fail. Remaining: consumer seal not proven (N1); `checks` outside the seal (N2); inventory untested (N8); uncited "no" passes (N6); cached recordings deliverable (N9). |
| Q2 vendor separation | 45 | **52** | Gains: family-aware avoid sets; config test covers every writer and coherence; A/B judge outside compared vendors. Remaining: Step A ran on the author's vendor/family, and the pin does not check `by` (N3); vacuous B assertion (N4); author vendor assumed. |
| Q3 verbatim / model text | 40 | **45** | Gain: title, caption and VO are under the seal. Remaining: off-selection speaker verification (N5); vacuous manifest support (N7); verbatim lock mocked in smoke (L1085-1092). |
| Q4 deterministic rules | 35 | **48** | Gains: NAME catches Title Case; PRICE_NOW has present-tense and history cases; supports need ≥3 words and the line's own cite. Remaining: no test for PRICE_NOW with empty or `None` levels; production counts unchecked. |
| Q5 tests + R7 | 50 | **55** | Gains: pin clobber fixed; both-order judge; random salt in `ci_mustfail`. Remaining: tamper test never reaches `build_edl`; no `package.build` or `inventory` test. |

## 5. Final priority list

**P0, must change before any pin is rendered**
1. `smoke_r7.py` L1111-1115: run `pinned.build_edl` on the tampered pin (title, `edl_vo`, segment text, gates) and assert `PinError`. Without this, C1's consumer half is unproven (N1).
2. Seal coverage (N2): either remove `checks` from the pin or have `pinned.py` derive both verdicts from the sealed `gates`. Add a smoke case that flips `checks` to true on a FAIL inventory.
3. Add a `PK.inventory` unit test (N8): each input failure, exception, `None`, replayed reply, `n: 0` and unmeasured PRICE_NOW must give a non-PASS row. Add `to_pin` refusals for a missing row, `n: 0`, `by: None` and a non-bool `replayed`.

**P1**

4. `package_pin`: refuse any verdict row whose `by` vendor or family is in the package's recorded writer set. Decide whether Step A is covered and make the doc (L92-93) and `run_given_package` L917 agree (N3).
5. Speaker verification (N5): the evidence must lie inside the selection, or diarisation must show one speaker from the evidence through the clip. Add a failing test using the L1474 shape.
6. Manifest support (N7): a C claim must be supported by the specific manifest field, and the test at L1539-1544 must flip to failing.
7. Uncited "no" / "yes" (N6): re-ask once for the quote, otherwise UNCERTAIN. Needs the orchestrator's re-ruling.
8. Fix the filter at `test_gates.py` L1388 (N4). Make `Canned` honour `avoid_vendor` (raise if the only backend matches).
9. Add an end-to-end `package.build` test on a fake router: a failing gate yields no package; plain-VO fallback; drop-and-repack; coherence below 4 moves to the next angle.
10. Add `smoke_r7` cases for `moments_package` `[]` / `null`, `checks: null`, a missing `edl_vo`, and a duplicate `after_clip`.
11. Cached recordings (N9): carry `cached` in the inventory and decide whether it is deliverable.

**P2**

12. `yield_table` L1650: verify through `package_pin`.
13. Unify spend limits (L280, L549, L746, L1740) in the ledger.
14. Move the chains in `run_given_package` L826-833 to a `--chain` flag or config; remove the `/tmp` path at L820.
15. Make the empty salt in `run_exam_record` / `ab_roles` (L720, L1834) match the harness's salting.
16. Test the second pass: `verify_segment` with `turn_change_inside=None` gives `ok=False`.

## 6. Single highest-leverage change

Make `pinned.build_edl` recompute the seal over the pin, derive its pass/fail only from the sealed exactly-PASS inventory, and prove it in `smoke_r7` by feeding it tampered pins. Today every assurance stops at `package_pin`'s side of the file.

## 7. Production ready?

**No for unattended release. Yes with conditions for the single REVIEW ONLY Telegram delivery (L-q).**

The conditions for that delivery are:

- **(a)** P0 items 1-3 land and pass.
- **(b)** For tonight's pin specifically, a human confirms:
  - no VO, title or caption line names a person (no speaker was verified; this neutralises N5);
  - the caption's production claims match the clip count and channel list (this neutralises N7).
- **(c)** Release authorisation re-verifies the seal itself rather than reading `edl["moments_checks"]`.
- **(d)** The Step A vendor question (N3) is ruled on and recorded before a second package is built.