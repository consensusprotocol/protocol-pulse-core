# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 38 s finish=stop usage in 41609 / out 1491 usd_reported=0.064637 usd~0.245 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1410 (RULING 115 (1)+(2) — Calibrated Hook Bar)**

The diff implements the verbatim order: hook job asked **ALONE** (one call per candidate) at production seed 7 by Grok only (`coherence_verdict:hook` list reduced to that single backend in every routing), with floors derived from the five PBX-approved hooks in `ALONE_TEST.json` (scroll=3, alone=4, setup=3 after applying the "never below 3" rule). The sealed `hook_calibration.json` (sha256 over canonical body, measured_at, rater, question_version, asking="alone") is the single source of truth. `hook_bar.bar()` / `passes()` / `text()` enforce validity, rater match, 24 h freshness, and "every part >= its floor by the calibrated rater". `hook_own()` now returns `passes` (used by `_can_open`, `medley`, `coherence`, `last_clip_only`, spotlight opener stage and its gate row). The hook slot in coherence/medley/ruling-62 verdicts uses the bar (not `COHERENCE_MIN=4`); clips after the hook keep the original `>=4` rule. qwen shadows every hook (role:kind lookup, own shadow chain) but never decides. The mark (`hook_bar_mark()`) is placed **outside** the package seal and pin seal, carried to Telegram note.

All governing laws were checked:

- **SENTENCE LAW / SNAP LIMIT / NEIGHBOUR / ONSET/TAIL / L-b / L-c / L-e / L-g / L-h / L-k / L-l**: untouched (no transcript, punctuation, cut-point, edge-word, or ASR changes).
- **SELECTION LOCK / L-d PROTECTED PREVIEW / LAW 22 (v2f byte-identical re-render)**: the calibration floors were deliberately taken from the protected preview + approved moments; `can_open` / `hook_order` / `lineup_for` logic is unchanged except for the new `passes` flag. v2f reference continues to pass (its hook meets the new floors).
- **L-f CHANNELS FIRST / L-i THE CLAIM IS THE EVENT**: untouched (editorial_select / story_semantics path is upstream and not modified).
- **L-a SIGN-OFF NAMES ALL / CREDITS / L-j RELEASE IS AUTHORISED ON THESE BYTES**: the added `hook_bar` dict lives **outside** the seal (`package_pin.to_pin` explicitly excludes it from `pin_seal`; `release_auth` still sees exact REQUIRED gates on final bytes). MONITORING rows remain non-deciding.
- **M12 FAIL CLOSED / LAW 20 / M2**: no gate was reclassified. No valid calibration, missing part, wrong rater, stale file, hand-edited sha, or out-of-contract reply → no hook passes. One candidate error does not stop the others being asked; first error is returned.
- **L-m (mentioned in ruling)**: explicit ("no rating = no hook").
- **ONE CANONICAL FORM (L-k)**: no new string comparisons outside `canon.py`.
- **Smallest diff / no new renderer/compositor/selector (M1) / GPU0 only**: one new 134-line module (`hook_bar.py`), calibration file, and targeted edits to rating, verdict, and logging paths. No renderer changes.

**Test coverage** is excellent: `test_hook_bar.py` (sealing, staleness, floors-below-3, hand-edit, add_example, live calibration cross-check against `ALONE_TEST.json`), `conftest.py` rig (pinned floors for all other tests, `real_hook_bar=True` for the live-file test), updated `test_medley`, `test_spotlight`, `test_ledger_build`, `test_hook112`, `test_providers`. 687/687 package+providers tests pass; 31/31 mutations killed. Shadow, kind-specific chain, "one error does not stop others", mark outside seal, and "setup now counts" are explicitly exercised. Production hook list is now Grok-only; qwen shadow is recorded but non-deciding.

**Findings**

[P1] The order explicitly says "Nothing else about the hook path changes (may-open rules, G17a, step A, CUTTABLE stay)". The implementation changed coherence/medley min calculation (exclude hook label) and `last_clip_only` (require `own["passes"]` separately). While this is *necessary* for a scroll=3 floor to be usable in medley (otherwise every passing hook would fail `>= COHERENCE_MIN`), it is a larger semantic diff than the ruling permitted. This should have been flagged for PBX confirmation before the audit package. (The comment "this is the one reading of 'nothing else changes' we took" acknowledges the tension but does not resolve it.)

[P2] `hook_bar.bar(..., rater=None)` skips the rater check, yet `passes()` still requires exact backend match against the calibration's rater. This is correct for `hook_live_bar()` but creates an asymmetric contract that is easy to misuse if another caller passes a non-None rater that does not match. Add an explicit comment or make the rater check mandatory when a non-None value is supplied.

[P2] `providers._shadow_of` and `_shadow_ask` now accept a `kind` parameter and build a dedicated chain `"shadow86:coherence_verdict:hook"`. The shadow log records `"kind"`, which is good. However, the shadow thread still uses the *deciding* reply's `cached` / `replayed` flags for the shadow record. A cached Grok decision will suppress the qwen shadow on subsequent builds, reducing shadow coverage over time. Shadow should always fire (or at least fire on a percentage of cached hits) to keep the shadow data fresh for future recalibrations.

[P3] `hook_calibration.json` embeds the full approved hooks (including long texts and PBX's "why" strings). This makes the file larger than necessary for runtime use and increases the chance of accidental hand-edits that break the sha256 seal. The approved list should be moved to a separate `ALONE_TEST.json`-sourced proof file; the calibration should contain only the derived floors, metadata, and sha.

[P3] Several places still mention the old `HOOK_MIN` / `rating >= 4` in comments or log strings before the new bar text is appended (e.g. `test_medley.py:1400`, some legacy strings in `package.py`). Clean-up is incomplete.

[P3] Nit: `hook_bar.write()` uses `indent=1`; the rest of the repo uses `indent=2` or `4`. Minor style inconsistency.

The implementation is otherwise meticulous, fail-closed, heavily tested, and complies with the release-authorisation, canonical-form, and protected-reference laws. The single [P1] is the scope creep versus the literal "nothing else changes" sentence in the order.

**P1_OR_WORSE: 1**