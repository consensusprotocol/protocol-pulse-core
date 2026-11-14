# glm-5.3-flash (z-ai/glm-5.3-flash) 142 s finish=stop usage in 30029 / out 4069 usd~0.151 (upper-bound price)

# AUDIT — pp-selectid, CYCLE 2 (ruling 102 + $19 stop; second pass, with the other models' cycle-1 findings in hand)

Scope: I verified only what the diff + stated facts support. Line numbers are the diff's own. I'm the second reviewer; my cycle-1 output is referenced as "mine" below.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting:

- **qwen's confirm_ahead vendor/family analysis (its <high> (b))** — I did not trace `hf`'s construction in cycle 1. Its *conclusion* was wrong (the consensus refuted it from the diff's own line: `hf = {b.family for b in router.backends.values() if b.vendor != CONFIRM_VENDOR}` — the filter is by **vendor**, so Grok's family "grok" is never in hf), but its *method* — actually enumerating the exclusion sets against the chain — was the right discipline, and the consensus's response (a new end-to-end test, `test_through_the_real_chain_grok_answers_ahead_and_no_fallback_is_ever_asked`, test_ruling_102.py:875–889) is exactly the right closure. I missed that the test gap existed.
- **glm's M3 (the pin note's wording under Plan B)** — I did not check whether the note's *words* ("no faster leg of step A's second family answered") would be false when the FIRST screen's last leg is the judge under ruling 87's Plan B chain.glm caught it; the fix (the note now covers both cases, package.py:80–82) is in the diff and the test asserts both parts (test_ruling_102.py:815). I missed the Plan-B interaction.
- **grok-4.20's note on `test_heimdall_health.py:914` needing `r.mode = lambda: "plan_b"`** — a consequence of the announcement's new conditional (providers.py:327–334): outside Plan B the words changed, so the old test's assertion would fail. I did not flag that the *existing* suite needed updating; the diff does it (test_heimdall_health.py:932).

What nobody caught, including me, in cycle 1 — see §3.

## 2. WHERE DO I AGREE OR DISAGREE?

**glm M1 (held_why swallows a real verdict's failure; the "refusal vs held" test is mock-only) — partially agree, and the diff already answers most of it.**
- Agree: `test_a_verdict_that_fails_the_clip_is_a_refusal_not_held` (test_ruling_102.py:720–726) mocks `PK.CI.a_failures` to return `["REFERENT_OUTSIDE"]`; the real path where `step_a` *raises* while validating an in-contract reply is not exercised. That's a genuine evidence gap.
- Disagree with the "retried forever with no escalation" framing as a *defect*: the ruling says "held for THIS build... retried next build" and names no counter. A deterministic bug in `step_a`'s validation would indeed repeat every build, but it stays *visible* — the RULING 102 line (proof_ledger.py:384–397, printed at proof_ledger.py:431–433) counts and names the held moments on STATE line 1 every build, so the orchestrator sees a repeat. That's the ruling's own mechanism. Documented, not a finding.

**glm M2 (mixed reason lists; a moment in two prescreen chunks) — agree, and it's closed.** The consensus's rebuttal is verifiable from the diff: prescreen's chunks are `[todo[i:i+batch] for i in range(0, len(todo), batch)]` (package.py:588, unchanged), a partition — a moment is in exactly one chunk; second_screen (package.py:194) and the writers' re-screen (package.py:266) *replace* the list, never append. And `is_held`'s `all(...)` semantics are themselves tested for the mixed case (test_ruling_102.py:804: one held + one refusal → refused). Within this diff, reason lists are single-element. No sequence breaks it.

**qwen's <critical> (confirm_ahead asks nobody) — disagree, refuted.** Its quoted code is not the code. The diff computes both sets by the back-end's *vendor* (package.py:172–173), so Grok's family never lands in `hf` and Grok's vendor never in `hv`. The new test (test_ruling_102.py:875–889) proves it end-to-end: with Grok up, every new moment gets Grok's verdict and legs[1:] are called 0 times; with Grok down, `asked=3`, `by={}`, and still 0 calls on the other legs. Also note the corrected expectation in test_medley.py:540: the ahead-set is now `{"heimdall", "heimdall/glm", "openai"}` — the writers' vendor plus every non-xAI vendor — which is exactly what the new code produces. qwen's own test (test_ruling_102.py:891–903) asserts the exact sets, `wf == {deepseek, glm, gemini, gemma}` with no "grok". Closed.

**grok-4.20's five <medium> "no breaking sequence" notes — agree.** They're verification statements, not defects. I independently re-checked the two that interact with this diff's new code:
- *The 40-minute judge wait*: `LocalJudgeBackend.WAIT_S` 2400 s is unchanged (stated fact, providers.py:305); ruling 102 adds the judge as the second family's *last* leg, so the added wait is bounded by the ruling's own allowance and only reached when three legs already failed. The announcement (providers.py:330–334) fires once per router (`_announced_local`, unchanged) — the test at test_ruling_102.py:845–852 runs two screens and asserts `judge.calls == 2` with one announcement.
- *The $19 stop*: `start_refused` (proof_ledger.py:374–381) replaces the inline check at proof_ledger.py:418–425; `spent0 >= 19.0` → refuse, `18.99` → proceed (test_ruling_102.py:863–868). The $20 cap is the unchanged per-call reserve (stated facts; proof_ly.py:443–450's comment). No sequence starts at ≥$19 or ends >$20 that didn't before — the *only* behavioral change to spend is the stop moving 16→19, which *loosens* it.

**qwen's <high> (a) — agree, documented.** It's the same 40-minutes/held-forever point as glm M1; the ruling's own visibility mechanism (STATE line 1, every build) is the answer. No counter is ruled; adding one would exceed the ruling.

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 — <medium> `second_screen`'s HELD default reason is built with an f-string whose continuation line's indentation produces a different string than the test asserts... no — verified, it matches.** (Withdrawn; recorded so the count is honest.) Actually one real one:

**N1 — <medium> `step_a_plan`'s `why` can be None while `parallel` is False when `len(new) > STEP_A_PARALLEL_NEW` but the confirm leg exists and Heimdall leads and the wait is over the threshold — no.** Re-derive: `parallel = why is None and len(new) > STEP_A_PARALLEL_NEW` (package.py:161). `why` is None only when heim ∧ wait > threshold ∧ confirm is not None. So parallel=True requires all three. Conversely, if `len(new) <= STEP_A_PARALLEL_NEW` the early return (package.py:139–142) sets `why` to the "not over" string. Every False-parallel path carries a reason. Verified, no gap.

**N1 (real) — <medium> `confirm_ahead`'s exclusion sets now include the *writers' own* non-xAI vendors, so a Heimdall-written build's confirm-ahead excludes Heimdall twice — harmless, but the *spotlight* path is not covered by the new test.** Where: package.py:172–173; test coverage test_ruling_102.py:875–903. The new tests exercise `confirm_ahead` directly with `wv={"heimdall/deepseek"}`. In `build`, `confirm_ahead` is called with the *live* `wv, wf` (package.py:201–202), which at that point is the writers' sets — the same shape. No divergence found. (Recorded as verified, not a defect.)

**N2 — <medium> `ruling_102_line`'s spotlight count can double-count a moment the medley already counted.** Where: proof_ledger.py:384–397, fed by package.py:214/227 (medley's `held_102`) and spotlight.py:361 (the spotlight's own `held_102`). A moment held at the medley's second screen is *stopped* in the medley (package.py:235: `cleared = {mid: m for mid, m in cleared.items() if mid in a_two}`) — it never reaches the spotlight's `clean`, so the spotlight's list can't contain it. Conversely the spotlight's `clean` comes from its own earlier stages. I traced both populations: the medley's `h["second"]` ⊆ `cleared`-then-dropped; the spotlight's `sp["held_102"]` ⊆ the spotlight's `clean`. They're disjoint *by construction* (a moment stopped at the medley never becomes a spotlight candidate), but nothing in the diff asserts it, and the line prints both counts side by side, so a future change to the medley→spotlight handoff would silently double-count on STATE line 1. Evidence gap, not a breaking sequence. **Medium, evidence-only.**

**N3 — <medium> `pin_last_resort` (package.py:242–245) keys the note by `sg["label"]` but looks the verdicts up by `sg["moment_id"]` in `a_two` — if a pin's segment's moment was judged by the local judge at the *first* screen only (its second verdict came from elsewhere), `last_resort_of(a_two.get(mid))` still returns the judge's backend, because `a_two[mid]` is the *list of both* verdicts.** Where: package.py:244, `last_resort_of` at package.py:72–75. Trace: `a_two[mid]` accumulates both screens' A-items (package.py:261–262 appends the re-screen's; second_screen's return is the second). `last_resort_of` filters the *whole list* for `local_judge:`-prefixed backends. So the note's `verdicts` maps label → the judge's backend whenever *either* verdict was the judge's — which is exactly what the ruling asks ("recorded as such on the pin" when the judge gave one of the pin's step-A verdicts). Verified correct; the test (test_ruling_102.py:741–761) exercises the second-screen case, not the first-screen-judge case, but the code path is the same filter. Evidence gap only.

**N4 — <medium> the spotlight's `last_resort` note (spotlight.py:348–349) keys `verdicts` by `m["moment_id"]`, while the medley's (package.py:244) keys by `sg["label"]` — two different key conventions for the same field across the two pin types.** Both tests assert their own convention (test_ruling_102.py:760: `{sg["label"]: LJ}`; :830: `{m["moment_id"]: LJ}`), and the ruling says only "recorded as such on the pin", not how. Cosmetic/consistency, no breaking sequence. **Medium, cosmetic.**

**N5 — checked and cleared: the seal.** `inventory` adds `last_resort` to `context_a` only when non-None (package.py:311–314), the test proves a pin without it is key-identical to the old shape (test_ruling_102.py:808–816, including the "every other key equal" assertion at :816), and `gate_problems` checks only status/replayed (stated fact, package_pin.py:347) — so no existing pin's seal changes and no new key can fail the gate. `seal` hashes the gates as they stand (stated fact), so *new* pins simply include the key when present. No sequence seals a wrong pin.

**N6 — checked and cleared: the announcement's ProviderError guard.** providers.py:326–329 wraps `self.mode()` in try/except ProviderError → plan_b=False, so an unreadable health state yields the ruling-102 words rather than raising inside the announcement path. The ruling-87 words are still guaranteed under Plan B because the except only fires when `mode()` itself raises — and if it does, we're not provably in Plan B, so the ruling-102 default is the safer of the two. No hang, no missed announcement (the `_announced_local` flag is set regardless, once).

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| held_why / is_held / HELD semantics | (not scored) | A– | Semantics correct; the "refusal vs held" test is mock-only (glm M1) — evidence, not behavior |
| second_screen / prescreen HELD paths | (not scored) | A | Every no-answer path now HELD, never cached; chunks partition, lists single-element; tests cover the real chain |
| confirm_ahead Grok-only (ruling 101) | (not scored) | A | qwen's <critical> refuted from the diff's own line; new end-to-end test closes the evidence gap |
| step_a_plan / _confirm_leg | (not scored) | A– | Every sequential path carries a `why`; the parallel/confirm interaction is tested for down, breaker-open, and writer cases (test_medley.py:514–530) |
| Local-judge record (pin + STATE) | (not scored) | A– | Both pin types record it; seal-unchanged proven; key-convention divergence (label vs moment_id) is cosmetic; first-screen-judge case untested |
| $19 stop / $20 cap | (not scored) | A | start_refused replaces the inline check; 18.99/19.0 boundary tested; cap mechanism untouched |
| STATE announcement | (not scored) | A | Plan B words preserved; ProviderError guard; once-per-router; both wordings tested |

No score dropped. The cycle-1 consensus's one *taken* defect (glm M3's note wording) is fixed in this diff and tested.

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none.

**P2 MEDIUM (all evidence/consistency, none breaking):**
1. **test_ruling_102.py:720–726** — the "a verdict that fails the clip is a refusal" test mocks `PK.CI.a_failures`; add a case where the *real* `step_a` validation raises on an in-contract reply, proving it lands HELD (not refusal) and is retried. (glm M1's residue.)
2. **proof_ledger.py:384–397 + package.py:227 / spotlight.py:361** — nothing asserts the medley's and the spotlight's `held_102` populations are disjoint; a future handoff change would double-count on STATE line 1. One test.
3. **test_ruling_102.py:741–761** — the pin's `last_resort` note is tested only for a second-screen judge verdict; add the first-screen-judge case (the code path is the same filter, but the ruling's "recorded as such" deserves the proof).
4. **package.py:244 vs spotlight.py:348–349** — the note's `verdicts` keys are `sg["label"]` (medley) vs `m["moment_id"]` (spotlight). Pick one convention or document both; the ruling doesn't care, but the next auditor will.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add the one missing test: a real `step_a` validation failure on an in-contract reply must land HELD and be retried — it's the only ruling-102 behavior the suite proves only by mock, and it's the exact distinction (refusal vs held) the ruling exists to settle.

## 7. PRODUCTION READY?

**Yes with conditions** — both conditions are tests, not code:

1. Add the real-`step_a`-raises→HELD test (P2-1) — it is the ruling's core distinction, currently proven only by mocking `a_failures`.
2. Add the disjointness test for the two `held_102` populations (P2-2) — it protects the STATE-line-1 counts the orchestrator reads.

Everything else ships as-is: the ruling's four-leg order is enforced and tested leg-by-leg (test_ruling_102.py:690–698), no-answer is HELD at every path and never cached (prescreen :92–95, second_screen :193–195, the re-screen :266–267, the spotlight :357–358), the judge's verdicts are recorded on both pin types without disturbing any existing seal (package.py:311–314, spotlight.py:348–349; test :808–816), the confirm-ahead is Grok-only and proven end-to-end (test :875–903), the plan never goes parallel without a usable confirm leg (package.py:157–162, tested :520–530), and the $19 stop fires exactly at the boundary (proof_ledger.py:374–381, test :863–868) with the $20 cap mechanism untouched.