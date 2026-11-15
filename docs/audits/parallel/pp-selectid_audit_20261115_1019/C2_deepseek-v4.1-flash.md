# deepseek-v4.1-flash (deepseek/deepseek-v4.1-flash) 244 s finish=stop usage in 6671 / out 11200 usd_reported=0.002497 usd~0.188 (upper-bound price)

# CYCLE 2 REVIEW — pp-selectid-20261115_1019

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Grok's [P2] on the surviving mutation** is the sharpest finding, and I under-weighted it. The original defect was itself a surviving "untested wiring" mutation (the keyword drop in `build_inputs` survived audit 20261115_0951). The fix leaves a structurally identical gap: `res["next_attempt"] = next_try` on the router path is reached by no test. I treated the "computed once, stored twice" structure as sufficient; Grok correctly noted that the *assignment* itself is the untested wiring, and that repeating the pattern that caused the original bug is undesirable.

**Qwen's [P2] on the timing shift** is also something I treated too lightly. Moving the computation from after the router to immediately after `build_inputs` is a behavioral change, even if it is likely an improvement. I did not explicitly ask whether `build_inputs` or `with_variants` could mutate `rows` or `wp`.

**The consensus's decision to accept the gap with a runtime check** is a process control I would not have proposed; it is a reasonable engineering trade-off given the cost of a full-build fake, but it is not a test.

## 2. WHERE DO I AGREE OR DISAGREE?

- **Collision fix correct** — AGREE. `wp_refused` is bound once (line 11), `next_try` is bound once (lines 20/22 in the try/except), and `refused` is still bound at line 438 for `start_refused()`. No other name collides.
- **Grok [P2] surviving mutation** — AGREE it is a real gap. PARTIALLY AGREE with the consensus mitigation. A runtime check on the first real build is a one-time manual verification, not a regression guard. If the assignment is later broken, no test catches it. I would still prefer a cheap test if one exists, but I accept that reaching the line requires a full-build fake.
- **Qwen [P2] timing shift** — PARTIALLY AGREE. The value is computed once and stored, so `inputs.json["next_attempt"]` and `res["next_attempt"]` are guaranteed consistent by structure. The only open question is whether the value is *correct*, which rests on the unverified assumption that `build_inputs` and `with_variants` do not mutate `rows` or `wp`. The new position is at least as correct as the old (which read post-`with_variants` state), but the assumption should be made explicit.
- **Grok/qwen [P3] comments** — AGREE, and the consensus says they are now trimmed to one line. Good.
- **Grok [P3] `except Exception`** — AGREE with no change. It is the same guard the base had at :510, moved with the call. A report must never end a build.

## 3. NEW FINDINGS FROM THIS REVIEW

- **[P2] The non-mutation assumption is untested.** `tests/package/proof_ledger.py:20` computes `next_try` from `rows` and `wp` immediately after `build_inputs`. If `build_inputs` or `with_variants` mutates either in place, the new computation reads a different state than the old one, and no test would catch it. A cheap guard: in `test_ruling_95_counts_the_refused_from_the_inputs_alone`, deep-copy `rows` and `wp` before the driver runs and assert they are unchanged after. This makes the assumption explicit and kills a mutation that mutates `rows` inside `build_inputs`.
- **[P3] Test depends on `next_attempt["conversation"]` shape.** `tests/package/test_ruling_107_guard.py:82` indexes `na["conversation"]`. If `SPOT.next_attempt`'s return shape changes, the test fails with a `KeyError` rather than a clear assertion. Use `.get("conversation", {})` or assert the key exists first.
- **[P3] Time-dependent test input.** `tests/package/test_ruling_107_guard.py:77` uses `datetime.now(timezone.utc).isoformat()` for `published_at`. The counts checked (3/0/2/1) should be stable, but a row exactly at a publish-window boundary could flake. A fixed timestamp would be more robust.
- **[P3] Comment imprecision.** `tests/package/proof_ledger.py:20` says "reads the inputs alone", but `next_attempt` reads `rows`, `wp`, `now`, `wp_refused` — the raw inputs, not the `inputs` dict. Minor, but the comment could mislead a future reader into thinking it reads `inputs`.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Correctness of fix | Pass | Pass | Confirmed by all reviewers; no new defect found. |
| Test coverage | Pass | **P2** | The router-path assignment remains untested; the new test only covers the nothing-new path. |
| Behavioral risk (timing shift) | Not flagged | **P2** | Moving the computation before `with_variants` is a real change; correctness rests on an unverified non-mutation assumption. |
| Code clarity | P3 | Pass | Comments trimmed per consensus. |
| Regression risk | Low | Low | No gate, verdict, or selection changes. |

## 5. FINAL PRIORITY LIST

- **[P2] `tests/package/proof_ledger.py:41`** — `res["next_attempt"] = next_try` on the router path is untested. Add a test that reaches a completed build, or add an assertion in the existing router test that `res["next_attempt"]` equals `inputs.json["next_attempt"]`.
- **[P2] `tests/package/proof_ledger.py:20`** — the timing shift assumes `build_inputs` and `with_variants` do not mutate `rows` or `wp`. Add a deep-copy comparison in the new test to make this explicit.
- **[P3] `tests/package/test_ruling_107_guard.py:82`** — test depends on `next_attempt["conversation"]` shape; use `.get` or assert the key.
- **[P3] `tests/package/test_ruling_107_guard.py:77`** — time-dependent `published_at`; consider a fixed timestamp.
- **[P3] `tests/package/proof_ledger.py:20`** — comment "reads the inputs alone" is imprecise; it reads the raw inputs, not the `inputs` dict.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add a test that reaches a completed build and asserts `res["next_attempt"] == inputs.json["next_attempt"]` — this closes the surviving-mutation gap and makes the "computed once, recorded twice" invariant explicit rather than structural.

## 7. PRODUCTION READY?

**Yes with conditions.** The fix is correct, the collision is resolved, and no gate, verdict, or selection changes. Conditions: (a) the runtime check on the first real build is actually performed and recorded on that build's STATE line; (b) a follow-up test closes the router-path gap; (c) the non-mutation assumption for `rows`/`wp` is verified by test or documented in the commit message.

P1_OR_WORSE: 0