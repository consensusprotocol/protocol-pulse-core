# qwen3.8-27b (qwen/qwen3.8-27b) 733 s finish=stop usage in 11087 / out 18026 usd_reported=0.013368 usd~0.304 (upper-bound price)



# Code Audit — RULING 146 (1) + (2), `pp-selectid` branch

## Scope confirmed

The diff implements two soft-pass relaxations, active **only** in the never-empty pass (`soft=True`):

1. **RULING 146 (1):** A clip whose *sole* visual refusal is the source's own burned-in graphics (ticker, crawl, lower-third, channel bug) is unblocked and the package is sealed 16:9-only, flagged per-clip.
2. **RULING 146 (2):** A hook whose *sole* measured G17a failure is a quiet-before-onset shortfall (matching the specific `why` string) is marked `soft: True` and allowed to open, flagged "The opening clip may start abruptly."

Both are added to `SOFT_GATES` so the pin mechanism treats them as review flags, not hard stops.

---

## Answers to the four requested checks

**(1) Can a 9:16 version ever carry a clip whose burned text our crop cuts?**
**No.** `soft_graphics` overwrites `m["visual"]["formats"]` to `["16x9"]`. `package_pin.formats_of` then seals the *entire* package 16:9-only (same mechanism as RULING 123's hook). No 9:16 render is produced. The `RENDER_16X9_ONLY` guard in `graphics_only` adds a second safety: if the render cannot pass a 16:9-only pin, `graphics_only` returns `None` and the clip stays hard.

**(2) Can a third person, an unmeasured record, or a mid-word cut pass?**
**No, all three stay HARD.**
- Third person: `graphics_only` returns `None` when `hook_block(rec) is not None` (RULING 70).
- Unmeasured / stale record: `graphics_only` requires `measured is True` and `version == VERSION`.
- Mid-word cut: `ONSET_QUIET` matches only the substring `"ms of genuine quiet before the hook's first onset <"`. A mid-word `why` (e.g. `"the cut lands inside a word"`) does not match, so `soft` is never set and `_can_open` rejects. The test `test_an_unmeasured_or_other_onset_failure_stays_hard` confirms both cases.

**(3) Is the clean pass unchanged?**
**Yes.** Every new code path is gated by `soft` (the never-empty flag): `for m in (cleared.values() if soft else ())`, `for m in (rated_open if soft else ())`, `and not (soft and soft_graphics(m))`, and the inventory FLAGGED rows use `if soft and …`. With `soft=False` (clean pass) none of the new logic executes. The test `test_a_clip_with_the_shows_ticker_seals_16x9_only_flagged` asserts `clean["package"] is None` for the ticker case, confirming the clean pass still rejects.

**(4) Are the tests adequate?**
The four tests cover: unit-level `graphics_only` / `soft_graphics` (including third-person, unmeasured, stale, empty, and no-graphics cases); end-to-end ticker → 16:9-only seal with exact flag text; end-to-end quiet-shortfall → flagged open; and the two hard-stay cases (unmeasured, mid-word). The clean-pass non-regression is asserted in the same end-to-end tests. Coverage is solid for the stated scope.

---

## Findings

### [P2] `ONSET_QUIET` regex is coupled to a specific English sentence in the `why` field

```python
ONSET_QUIET = re.compile(r"ms of genuine quiet before the hook's first onset <")
```

This matches a *prose* substring produced by the onset-measurement code. If that code's wording changes (e.g. "70ms" without a space, "quiet before the hook's first onset is below", or a different unit), the regex silently stops matching and the soft pass is never triggered. The failure mode is **fail-closed** (the onset stays HARD, the package is not produced), so there is no safety risk, but the RULING 146 (2) feature would silently stop working with no error or log.

**Recommendation:** Either (a) have the onset-measurement code set a structured field (e.g. `h["failure_kind"] = "quiet_shortfall"`) and match on that, or (b) add a unit test that asserts the *actual* `why` string produced by `sentence_law.edge_plan` / `head_tail` matches `ONSET_QUIET`, so a wording change breaks the test rather than silently disabling the feature.

### [P2] `soft_graphics` mutates the moment's visual record inside a dict-comprehension filter

```python
vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order
        if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))
        and not (soft and soft_graphics(m))}
```

`soft_graphics(m)` reassigns `m["visual"]` to a new dict with `formats=["16x9"]`. This is a **side effect in a filter predicate**, evaluated in two separate dict comprehensions (main line-up ≈ L3869, no-voice order ≈ L4178). The mutation is intentional and idempotent (the second call reads the cached `graphics_16x9`), but:

- A reader scanning the filter sees a pure predicate; the mutation is only discoverable by reading `soft_graphics`'s body.
- If a future refactor moves the `vbad` computation or adds a third call site, the mutation's visibility and ordering become harder to reason about.

**Recommendation:** Extract the mutation into a separate loop before the `vbad` comprehension, or at minimum add a comment at the call site: `# soft_graphics mutates m["visual"] → formats=["16x9"]`.

### [P2] `burned_block` / face-coverage interaction is not explicitly tested

The RULING 146 (1) docstring states: *"OUR 9:16 crop cutting burned text **or a face** stays HARD."* The `graphics_only` function returns `sorted({x["kind"] for x in rec["burned_in"] if burned_block(x)})`. If `burned_block` can return `True` for a non-graphics item (e.g. a face or a person tracked in `burned_in` with `covers_speaker: True`), that kind would be included in the returned list and the clip would be soft-passed, contradicting the ruling.

The test fixture uses `covers_speaker: False` and `kind: "ticker"`. There is no test with `covers_speaker: True` or a non-graphics `kind`.

**Recommendation:** Add a test case where `burned_in` contains an item with `covers_speaker: True` (or a `kind` outside `GRAPHIC_WORDS`) and assert that `graphics_only` returns `None` (or that the item is excluded). If `burned_block` already excludes such items, the test documents the contract.

### [P2] `SOFT_GATES` is a module-level constant consulted by the pin mechanism in *all* passes

`hook_onset` and `graphics` are added to `SOFT_GATES` unconditionally. The pin mechanism presumably checks `if gate_name in SOFT_GATES` to decide whether a FAIL becomes a FLAG. In the clean pass, the `hook_onset` row is a normal PASS/FAIL (the `soft` flag is not set, so the FLAGGED override in `inventory` is not applied). However, if the pin mechanism sees `hook_onset` in `SOFT_GATES` and the row is FAIL (not FLAGGED), it may treat it as a soft gate and flag it rather than hard-stop, **changing clean-pass behaviour**.

The diff comments suggest the `soft` flag on the record is what distinguishes soft from hard, and the pin mechanism may only consult `SOFT_GATES` when the record carries `soft: True`. But this is not visible in the diff.

**Recommendation:** Verify (or add a test) that in the clean pass, a `hook_onset` FAIL (e.g. a 70 ms quiet shortfall *without* the `soft` flag) is still a hard stop. The existing test `test_a_hook_with_a_quiet_shortfall_opens_flagged` asserts `make(False).run()["package"] is None`, which covers this, but only for the *build* level. A pin-level test would close the gap.

### [P3] No test for `RENDER_16X9_ONLY = False`

When `RENDER_16X9_ONLY` is `False`, `graphics_only` returns `None` and the entire RULING 146 (1) feature is disabled. This is a deployment-level constant, so a test is low priority, but a one-line `mock.patch.object(VP, "RENDER_16X9_ONLY", False)` test would document the kill-switch.

### [P3] `graphics` inventory row: unbounded flag list

The `graphics` row builds one flag sentence per clip with `graphics_16x9`. In a package with many clips (e.g. 6+), the `flags` list grows. `REVIEW_FLAGS_MAX = 3` (defined in `package_pin.py`) may cap the number of *rows* or the number of *flag sentences*. If it caps sentences, a 4-clip graphics package would exceed the limit and be rejected, silently defeating the never-empty pass. If it caps rows, one `graphics` row is fine regardless of sentence count.

**Recommendation:** Confirm the semantics of `REVIEW_FLAGS_MAX` and add a test with ≥ 4 graphics clips.

---

## Law-compliance summary

| Law | Status |
|---|---|
| SENTENCE LAW | Not touched. |
| SELECTION LOCK | Not touched. |
| SNAP LIMIT / NEIGHBOUR | Not touched. |
| ONSET/TAIL (D1) | The integrator still holds G17a HARD in its lock/cut table. The build's never-empty pass flags it. The D1 rule is "unchanged" at the render level. **Compliant** (see P2 on SOFT_GATES interaction). |
| CREDITS | Not touched. |
| L-a … L-l | Not touched. |
| LAW 20 / M2 | A failed gate is a hard stop *in the clean pass*. In the never-empty pass, the orchestrator explicitly ruled these two failures SOFT (flagged, not passed). The integrator's render still enforces G17a HARD. **Compliant with the ruling; see P2 on SOFT_GATES scope.** |
| M12 FAIL CLOSED | All new paths are fail-closed: unmeasured → hard, third person → hard, mid-word → hard, `RENDER_16X9_ONLY` false → hard, regex non-match → hard. **Compliant.** |
| LAW 22 (v2f byte-identical) | The v2f reference goes through the clean pass (`soft=False`); no new code executes. **Compliant.** |
| Smallest diff / M1 | No new renderer, compositor, or selector. Changes are confined to `visual_pin.py` (one new function), `package.py` (soft-pass logic + inventory), `package_pin.py` (two SOFT_GATES entries), and tests. **Compliant.** |

---

## Mutation-kill note

The diff states "7 of 8 killed (F7, 'graphics' in SOFT_GATES, is equivalent: gate_problems checks only required rows and graphics is optional)." This is correct: the `graphics` row is optional (not in `required_gates`), so removing it from `SOFT_GATES` does not change `gate_problems` output. The mutation is equivalent, not a missed kill.

---

P1_OR_WORSE: 0