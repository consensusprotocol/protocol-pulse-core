# glm-5.3-flash (z-ai/glm-5.3-flash) 108 s finish=stop usage in 12591 / out 3158 usd~0.085 (upper-bound price)

# pp-selectid — CYCLE 2 AUDIT (final)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **The FAIL-row evidence path through `inventory()` (glm P1-3).** I noted the unguarded `r['opener']['why']` / `r['topic']['why']` reads but did not demand a test. Cycle 2's diff adds `test_inventory_writes_a_FAIL_row_with_its_evidence` (test_medley.py:243-254) and the consensus (K2) confirms `check_edl` always emits `opener`/`topic` dicts with `why` (stand_alone.py:116-121). I missed that this was both testable in this diff and already answered — the crash-converts-FAIL-to-exception concern is closed.
- **The `out["usable"]` semantics fix (glm P2-2 → consensus K4).** I flagged the count change; the fixed diff restores it (`n_usable = len(ms)` at package.py:1024, used at :1027) and moves the excluded count to `out["no_role"]` + the log line. I did not propose this remediation.
- **The GPU-free import question (glm P2-4 → consensus K3).** I never raised it; the consensus verified `stand_alone.py` imports only `re` at module level, so the pin stage stays GPU-free. Correct and worth having on the record.

What I caught that they mostly ratified: the EDL-shape/subject fidelity question (glm P1-1, qwen P1-1), which the consensus resolved as VERIFIED via byte-identical `stand_alone.py`, `check_edl` reading only `text`+subject+rate, and `to_pin` always labeling moments pins "bitcoin" (package_pin.py:179).

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| glm P1-1 / qwen P1-1 (EDL keys, hardcoded "bitcoin") | **Agree, resolved** | Consensus K1 is decisive: `check_edl` (stand_alone.py:99-123) reads only `s.get("text")` for verdicts; channel/duration feed only the scorer's passages, unused at `rate=None`. Subject: `to_pin` sets `"label": "bitcoin"` for every moments pin, so the hardcode matches the render's `stand_alone_subject` for the only shape that reaches this code. The docstring (package.py:17-18) now cites the audit. Residual: if a non-"bitcoin" moments pin ever exists, the pin-stage subject diverges — latent, correctly documented. |
| glm P1-2 / qwen P1-2 (no_role stricter than render) | **Agree, intended** | Fail-closed direction is the allowed one under the standing laws; the pronoun case (fails hook, passes clip → stays) is pinned by test:210-211. The equivalence "opener-fail ⇒ check_edl-fail at rate=None" is asserted in the docstring and exercised by the held-pin reproduction test (test:199-205), which is the strongest available evidence without the GPU. |
| glm P1-3 (FAIL-row evidence) | **Agree, fixed** | New test drives the FAIL path; `check_edl`'s guaranteed row shape makes the unguarded reads safe. |
| glm P2-1 (required_gates for non-medley shapes) | **Agree, still unverified** | `required_gates(pk)` body is still not in the diff (package_pin.py:161+). The new test at :260 builds gates from `required_gates(pk)` for `pk = {"shape": "medley"}` and expects "stand_alone" among them, which confirms the medley path; the non-medley path remains unseen. Low risk, unchanged. |
| glm P2-2 (usable semantics) | **Agree, fixed** | See above; the log line and `out["no_role"]` now carry the excluded count. |
| qwen P1-3 (lineup_for stricter) | **Agree, intended** | Test:213-221 demonstrates both the old pick preserved without the flag and the new pick with it, plus the no-Bitcoin-clip refusal. This is the feature, not a defect. |
| qwen P2-4 (machine-parseable rows) | **Agree with consensus** | The gate's `status` is what `gate_problems` reads; rows are human evidence. Keeping text is right. |
| qwen P2-6 (Rig not in diff) | **Agree, minor** | `Rig` is pre-existing test infrastructure (used at test:234; the class predates this diff — the diff hunk at :184 starts a new class after existing tests). Not a diff defect. |
| grok's blanket "no P0, no P1, SHIP: yes" | **Agree** | Its line-cited verification of the threading (package.py:52,93,107 → inventory:134 → package_pin:153 → test:244) matches what I can see. |

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2) — `stand_alone_check` at the second inventory call site can raise on a segment not in `cleared`.** package.py:113 and :1357-1358 (diff lines 89, 113) both do `cleared[sg["moment_id"]]` — a direct subscript, not `.get`. Every segment of a sealed package should be in `cleared` (it was angle-written from it), but if a later stage ever adds a segment (e.g., a no-voice `added_clip`, which test:277 shows exists as a concept: `mp["no_voice"]["added_clip"]`), the KeyError would abort `build()` rather than produce a FAIL row. Fail-closed under M12, so P2, not P1. Nobody flagged the direct-subscript specifically; glm's P1-3 was about the evidence rows, not this. Note the no-voice test (test:268-277) calls `PK.stand_alone_check(pk["segments"])` directly and passes, so for the current shapes it holds — this is a robustness note, not a bug.

**N2 (P2) — `no_role` dict ordering is insertion-order-dependent on `ms`.** package.py:1025: `no_role = {m["moment_id"]: r for m in ms for r in [no_role_on_screen(m)] if r}`. Test:236 asserts `list(out["no_role"]) == ["b"]` — fine — but the *order* of `no_role` keys follows `ms` (usable() order), not the angle order. If any consumer assumes angle order, it will be surprised. Nobody mentioned this; purely informational since nothing in the diff consumes the order.

**N3 (P2) — the double-`stand_alone_check` cost.** Each candidate line-up inside `lineup_for`'s permutation loop (package.py:619) runs `check_edl` (regex work, cheap), and then the sealed package runs it again at inventory (:113/:1357). With `rate=None` this is pure-`re` CPU, microseconds — acceptable, but the redundancy is worth noting: the inventory row and the lineup filter could disagree only if `cleared` mutated between the two, which it does not (segments are the chosen ones). No action needed; nobody counted these.

**N4 (verified, not a finding) — the "nothing here can PASS a line-up the render would hold" invariant.** Both directions hold: (a) pin-FAIL ⇒ render-FAIL, because `check_edl` is byte-identical and the call is the same (rate=None is *the* no-scorer case, and the render's scorer can only flip FAIL→PASS, never PASS→FAIL — the scorer "affirms", it does not veto); (b) pin-PASS ⇒ render-PASS, because the render's scorer can only add affirmation. Wait — direction (b) is the one to state carefully: the pin seals with rate=None; the render runs WITH a scorer. A clip that fails the opener but the scorer affirms (3.0, fault other → affirmed) would FAIL at the pin but PASS at the render. That is the documented, intended over-strictness (qwen P1-3, consensus "KEPT"). The invariant as stated in the task — "the pin stage must never seal a line-up that the render's own checks would hold" — is satisfied: sealing is prevented, not forced. The reverse (render holds something the pin refused) costs a re-pick, not a broken seal. This asymmetry is the correct one and the tests pin it.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| stand_alone_check fidelity (package.py:10-23 / 553-577) | B+ (EDL keys, subject unproven) | A− | Consensus K1: byte-identical module, verdict reads only text+subject+rate, `to_pin` label pinned; reproduction test seals it. −1 for the latent non-"bitcoin" label case, documented. |
| no_role_on_screen (package.py:26-33) | B (equivalence asserted, not shown) | A− | Held-pin test + pronoun test + the fail-closed direction argument; the conjunction/reply-fragment/“And/Yeah/Well” cases are enumerated (test:208). |
| lineup_for integration (package.py:36-37, 55-56, 98-103) | B | A | Both call sites pass the flag; old behavior preserved when flag absent (test:218); pronoun-hook fallback (test:223-229) mirrors need_onset semantics. |
| inventory / gate row (package.py:120-143) | B− (FAIL path untested) | A | FAIL-row test added; `check_edl`'s guaranteed row shape closes the KeyError concern; missing-row refusal tested (test:180-183, 252-254). |
| package_pin.MEDLEY_GATES (package_pin.py:148-158) | B (required_gates body unseen) | B+ | Comment rewritten one-origin-per-line (qwen P2-5 done); medley path tested; non-medley `required_gates` still not in the diff. |
| build() integration (package.py:60-79) | B (usable semantics) | A | `n_usable` restores meaning; `out["no_role"]` + log line; no_role precedes prescreen (test:231-238 proves the moment never reaches angle_write). |
| Tests | B+ | A− | 8 new tests, all behaviors from the change spec covered; −1 for no non-medley `required_gates` assertion and the `Rig`/fixture opacity qwen noted. |

Nothing moved a verdict; the fixes were exactly the ones the consensus demanded.

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none. (All Cycle 1 P1s are fixed or resolved by verified evidence: glm P1-1 → K1; glm P1-3 → K2 + test:243-254.)

**P2 MEDIUM:**
1. **package.py:113, 1357-1358 (diff :89, :113)** — `cleared[sg["moment_id"]]` direct subscript in both `stand=stand_alone_check(...)` call sites; a segment absent from `cleared` (e.g., a future no-voice `added_clip` path) raises KeyError inside `build()` instead of yielding a FAIL row. Fail-closed, hence P2. (N1)
2. **package_pin.py:161+ (`required_gates`)** — body still not shown; the non-medley return value is unverified. If a non-medley shape ever inherited MEDLEY_GATES, older pins' recomputes are unaffected (integrator checks REQUIRED_GATES only) but new pins of that shape would newly demand `stand_alone`. Add one assertion: `required_gates({"shape": "other"})` excludes "stand_alone". (glm P2-1, still open)
3. **package.py:17-18 (diff :17-18) / docstring** — the hardcoded `subject_terms("", "bitcoin")` is correct only while `to_pin` labels every moments pin "bitcoin" (package_pin.py:179). If a second label ever appears, the pin-stage subject silently diverges from the render's. Parameterize from `pk["label"]` or keep the documented limitation. (qwen P1-1 residual)
4. **package.py:1025 (diff :65)** — `out["no_role"]` key order follows `usable()` order, not play order; document or sort if any consumer ever cares. (N2, informational)

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add the one-line test `required_gates({"shape": "non-medley"})` excludes `"stand_alone"` — it is the only consensus-flagged item (glm P2-1) still resting on neither code-in-diff nor a test, and it guards the only path (a non-medley pin newly refused) that could surprise after this ships.

## 7. PRODUCTION READY?

**Yes with conditions** — narrower than Cycle 1's, both cheap:

1. Add the non-medley `required_gates` assertion (P2-2 above) — one line, closes the last unverified consensus item.
2. Either parameterize `stand_alone_check`'s subject from the package label or add a comment/test pinning "every moments pin is labelled bitcoin" (package_pin.py:179) so the hardcode's dependency is enforced, not just documented.

Everything else — the held-pin reproduction, the no-role rule with the pronoun carve-out, the FAIL-row evidence, the restored `usable` semantics, the gate refusal — is tested and consistent with the standing laws (L-m, L-j, stricter-pre-check-allowed, pin-never-seals-what-the-render-holds). The over-strictness relative to the render's scorer is the intended, documented, fail-closed direction, and the tests pin both its presence and its boundaries.