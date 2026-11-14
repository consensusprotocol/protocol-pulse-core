# glm-5.3-flash (z-ai/glm-5.3-flash) 118 s finish=stop usage in 5706 / out 3573 usd~0.071 (upper-bound price)

# CYCLE 2 REVIEW — pp-selectid-0230 (probe_due claims the slot)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output (referenced via the consensus):

- **The "who" coordination risk (qwen3.8-27b, `<low>` heimdall_health.py:11).** I flagged pp-ingest's call site as unverifiable but underweighted the *deployment-ordering* aspect: until pp-ingest's watcher restarts with `who="pp-ingest probe"`, its claims record `last_probe_by=""`. The consensus shows this was resolved (pp-ingest confirmed it passes `who` from its next restart, and the argument is optional until then). I did not treat it as a deployment-sequencing condition; I should have.
- **The exact-equality timing in the test (qwen3.8-27b, `<low>` test:60/66).** I verified the 120s boundary logic but did not explicitly note that the test's correctness hinges on `probe_result` stamping exactly `at(16)` — i.e., that the mocked `now` is honored by `probe_result` too. Qwen's walk-through (120 < 120 → False → claim at 18) is the right concrete trace, and the "tight but correct" verdict matches mine; I just didn't articulate the fragility (a +1s stamp would flip the at(18) claim to False).
- **The `_Locked` re-entrancy caveat (glm-5.3-flash, second `<medium>`).** I asserted the lock covers read+stamp+save but did not raise the question of whether `_save` itself re-locks (non-re-entrant flock → deadlock). GLM correctly noted it's pre-existing (probe_result already saves under the lock) and therefore not introduced by this diff — but it's a legitimate "cannot verify from diff" item I skipped.

What they caught that I also caught (no credit either way): the claim-anchored vs answer-anchored cadence drift (glm's first `<medium>`), the mode-check early return not burning the slot, the BACK_AFTER=3 arithmetic in the new test.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding (source) | Verdict | Why |
|---|---|---|
| Cadence drift: effective period = PROBE_EVERY_S + probe duration when the probe answers late; next due anchored to the later stamp (glm, heimdall_health.py:26) | **Agree, correctly classified as documented, not a defect** | The new docstring (diff lines 15–17) explicitly declares both anchors: "probe_result re-stamps … (answer-anchored), and a claimer that never reports leaves the slot spent from its claim (claim-anchored)". With a 30 s probe, the next due is T+2:00 from the answer, not T+2:00 from the claim — drift, but *bounded* (≤ one probe duration) and declared. Not a regression: the old code had the same drift via probe_result's stamp. |
| `_save` under `_Locked` — re-entrancy question (glm, heimdall_health.py:26–29) | **Agree it's unverifiable from the diff; agree it's pre-existing** | The diff shows `_save(path, s)` called at line 29 *inside* `with _Locked(path):` (line 20). If `_Locked` were non-re-entrant flock and `_save` re-locked, the *unchanged* `probe_result` would already deadlock the same way, so this diff introduces nothing new. Cannot confirm either way from the diff — correctly flagged, correctly discounted. |
| pp-ingest passes no `who` until its restart → `last_probe_by=""` (qwen, heimdall_health.py:11; glm's third `<medium>`) | **Agree — cosmetic/audit-trail only, correctly resolved as a condition** | The stamp, not the name, enforces exclusivity (line 26–28: the `lp` check reads `last_probe_utc`, not `last_probe_by`), so a `who=""` claimer still blocks the second prober. Functional behavior is intact; only the audit trail is degraded. The consensus records the condition as MET (pp-ingest passes `who` from its next restart). |
| `probe_due` is now imperative, not a predicate — rename suggestion (qwen, heimdall_health.py:26–27) | **Partially agree** | Factually correct: it mutates state and writes disk. But the docstring (lines 12–18) now documents the claim semantics precisely, the diff is deliberately smallest-possible, and renaming would touch pp-ingest's call site (external repo) — churn without behavioral gain. Agree with the observation, disagree that a rename is warranted *now*. |
| Test timing tightness: at(18) claim depends on `probe_result` stamping exactly at(16) (qwen, test:60–66) | **Agree it's tight; agree it's correct as written** | Traced: `probe_result(True, **k(16))` → `last_probe_utc = T0+16m`; `probe_due` at `at(18)`: (18−16)·60 = 120 s; guard is `< PROBE_EVERY_S` (120), 120 < 120 is False → proceeds to claim. Correct. It would break only if `probe_result` ignored the injected `now` — but the test passes `**k(16)` which includes `now=`, and the *existing* tests (e.g., the 3-in-a-row test above, lines 52–53) already rely on the same injection convention, so this is an established, exercised pattern, not a new assumption. |
| grok-4.20: "None verifiable from diff" at every severity | **Agree, with a caveat** | Grok's reasoning is sound on every point it lists (single-lock claim, 15-min rule untouched at line 22, never-reporter limited to one slot, 3-in-row logic untouched). The caveat: "no findings" is only as good as the checks performed, and grok's listed checks are exactly the right ones — the read+stamp+save are under one `_Locked` (diff lines 20–29), so two concurrent callers cannot both see a stale `last_probe_utc`. I independently reach the same conclusion. |

**Disagreements: none substantive.** The one place I'd push back mildly is on treating the cadence drift as anything more than a documented characteristic — it is neither new nor fixable without changing the declared anchoring semantics.

## 3. NEW FINDINGS FROM THIS REVIEW

**<medium> tests/providers/test_heimdall_health.py:62 vs :70 — the two probers' *order* flips between the first claim and the loop, and the test silently depends on the flipped order.**
Line 62: `[... for w in ("pp-selectid", "pp-ingest")]` → expects `[True, False]` (pp-selectid claims).
Line 70: `[... for w in ("pp-ingest", "pp-selectid")]` → expects `[True, False]` (pp-ingest claims).
This is intentional (it demonstrates *either* prober can win a slot), and each iteration's assertion (`claims == [True, False]`) is order-correct for the list it builds. But nothing in the test asserts *which* who won the slot in the loop iterations (line 64's `last_probe_by` check covers only the first claim). Concrete scenario: if a regression made `probe_due` ignore `who` when stamping (e.g., always stamp the literal `"pp-selectid probe"`), lines 62–67 would still pass, and the loop at 69–74 would still pass — only line 64 would catch a who-related regression, and only for the first claim. Minor coverage gap, not a code defect. Nobody in Cycle 1 (including me) noted that the `last_probe_by` assertion covers exactly one of the three claims.

**<medium> tests/providers/test_heimdall_health.py:65 — `probe_result(True, **k(16))` after the at(16) claim, but the at(17) `probe_due` calls (line 66) happen *before* the result's re-stamp would matter — verify the sequencing is deliberate.** Trace: claim at 16 (stamp = 16); `probe_result` at 16 (re-stamp = 16, no-op); `probe_due` at 17: (17−16) = 60 s < 120 → `[False, False]`. Correct. Then the loop: at(18): (18−16) = 120 → claim. The sequencing is correct; the reason it's worth noting is that the test's `probe_result` at line 65 uses `k(16)` — the *claim* time, not a later "probe finished" time — so it exercises the answer-anchored re-stamp with a zero-duration probe. That's fine (the docstring's answer-anchoring is about *which* stamp is later, and 16 = 16), but it means the test never exercises the case where the answer's stamp is *later* than the claim's (the drift case glm described). Nobody caught that the test suite has no coverage of the answer-anchored-when-later path. Coverage note, not a defect.

**<low> heimdall_health.py:28 — `who` is stored even when empty, overwriting a previous non-empty `last_probe_by`.** Concrete: pp-selectid claims at T (records "pp-selectid probe"); pp-ingest's *old* watcher (pre-restart, passing no `who`) claims the *next* slot at T+2m → `last_probe_by` becomes `""`, erasing the previous claimer's name. The state's audit trail oscillates. Purely informational; the exclusivity mechanism (the `lp` timestamp) is unaffected. Neither reviewer's Cycle 1 note (qwen's `<low>`, glm's third `<medium>`) made this overwrite-oscillation explicit — they discussed the missing-who case, not that a mixed-who/empty-who deployment *erases* prior attribution.

**<info> heimdall_health.py:22–23 — the early return when `mode != "plan_b" and not failing_since_utc` does not save, correctly leaving a healthy-mode caller's read side-effect-free.** Both glm (fourth `<medium>`) and I noted this; recording it as verified-unchanged: the 15-minute rule lives in `note()`/`mode()` (not in this diff's hunk beyond the context line), and the 3-in-a-row return (`probe_result`'s BACK_AFTER logic) is untouched — the diff's context at line 33 shows `probe_result`'s signature unchanged, and the hunk ends before its body.

**<info> Nothing else in the state changes.** The diff touches exactly three keys' writers: `last_probe_utc` (now written by probe_due *and* probe_result — the latter unchanged), `last_probe_by` (newly written by probe_due), and nothing else. `_load`/`_save`/`_Locked`/`_t`/`_iso` are used, not modified. The `mode`/`note`/`probe_result` bodies are outside the hunks; the only behavioral additions are the claim-stamp and the `who` parameter.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| heimdall_health.py — claim correctness (lock, stamp, return) | 9/10 | 9/10 | Read+stamp+save under one `_Locked` (lines 20–29) — verified; no concurrent-claim window. No new evidence. |
| heimdall_health.py — cadence/anchoring semantics | 8/10 | 8/10 | Drift is real but documented (docstring lines 15–17) and pre-existing in magnitude; the never-reporter case is bounded to one slot (line 26: guard returns False while `now - lp < PROBE_EVERY_S`, and the claim's own stamp opens the next slot exactly PROBE_EVERY_S later). |
| heimdall_health.py — state hygiene (`who=""` overwrite) | — | 8/10 | New: the mixed-versions overwrite-oscillation of `last_probe_by` (line 28) — cosmetic, bounded, self-healing once pp-ingest restarts. |
| providers.py:43 — router call site | 9/10 | 9/10 | Passes `who="pp-selectid probe"`; the `except` (line 46) still swallows everything so the probe never stops a build — unchanged, and the claim+result now both carry the same who. |
| tests — slot-exclusivity coverage | 8/10 | 8/10 | The new test (lines 55–74) does its job: one True per slot, three slots for three answers, both probers win a slot. Gaps: `last_probe_by` asserted for only 1 of 3 claims; no exercise of answer-stamp-later-than-claim. |
| tests — timing robustness | 8/10 | 8/10 | Exact-120s boundary is correct as written and rests on the established `now`-injection convention; not flaky in practice since `now` is fully mocked. |

No score changed; the Cycle 2 findings are coverage/hygiene notes, not correctness changes.

## 5. FINAL PRIORITY LIST

- **P0 CRITICAL:** none.
- **P1 HIGH:** none.
- **P2 MEDIUM:**
  1. tests/providers/test_heimdall_health.py:64 — `last_probe_by` is asserted for only the first of the three claims; add a who-assertion inside the loop (line 70–71) so a who-stamping regression in later slots is caught. (Coverage, not correctness.)
  2. tests/providers/test_heimdall_health.py:65 — no test exercises `probe_result` stamping *later* than the claim (the answer-anchored-when-later path the docstring promises, lines 15–16); one test with `probe_result(True, **k(16.5))`-style timing would close it. (Coverage, not correctness.)
  3. heimdall_health.py:28 — mixed-versions deployment: pp-ingest's pre-restart watcher claims with `who=""` and overwrites a prior non-empty `last_probe_by`; acceptable, but the audit trail oscillates until pp-ingest's restart. Already resolved by the consensus condition (pp-ingest passes `who` from its next restart) — keep it as a tracked condition, not a code change.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add the who-assertion inside the test loop (test:70–71) — it's the only gap that lets a *future* regression in the new claim-attribution path (the entire point of `who`) ship unnoticed, and it's a one-line fix.

## 7. PRODUCTION READY?

**Yes with conditions** — both conditions already recorded as MET in the Cycle 1 consensus; they are deployment/verification conditions, not code changes:

1. **pp-ingest passes a non-empty `who`** ("pp-ingest probe") from its next restart; until then, claims with `who=""` are functionally correct (the timestamp, not the name, enforces exclusivity) but lose attribution. Verified MET per pp-ingest's own message.
2. **The docstring's anchoring semantics are the contract** (heimdall_health.py:15–17): next due = PROBE_EVERY_S after the *later* of (claim, answer) stamp; a never-reporting claimer costs exactly one slot. Any future change to that anchoring (e.g., answer-anchored-only) must update the docstring *and* the test's timing expectations, since the test's at(18) boundary depends on it.

No P0/P1. The claim-under-one-lock mechanism is correct, the 15-minute rule and 3-in-a-row logic are untouched, a never-reporting claimer costs exactly one slot, and nothing outside `last_probe_utc`/`last_probe_by` changes. SHIP: yes with conditions.