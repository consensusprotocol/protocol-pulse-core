# glm-5.3-flash (z-ai/glm-5.3-flash) 106 s finish=stop usage in 18222 / out 2753 usd~0.096 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid-0003, ruling 93)

## 1. What did they catch that I missed?

- **glm's fail-open truncation** (burned_in cut at TEXTS_MAX=12 with no marker, so a ticker listed 13th passes) — the strongest finding of the cycle. I did not flag it in Cycle 1. The fix (sort blocking-first, then `burned_in_truncated` count, test at test_visual_pin.py:499–502) is correct and the test proves the ticker survives the cut.
- **glm's wordless bug** (`text: null` rejected by the contract → clip unmeasured). Also missed by me. Fix (null → `""` at visual_pin.py:206, test at :497–498) is right.
- **glm's dual-reason reporting** (hook+layout both blocked → only hook reason shown). Missed. Fix at package.py:48 (`"; ".join(...)`) is correct.
- **grok's redundant-import claim** — grok was *wrong* (spotlight.py has no module-level VP; the local import at spotlight.py:91 is required). Claude's consensus refutation is correct; I agree with the refutation.
- **qwen's two "criticals"** (pre-visual-2 records blocked; existing pins invalidated) — qwen's mechanism is right but his severity is wrong: `visual_pin.key()` holds VERSION, so a visual-1 record is never served to a build; sealed pins read only through `sealed()`, which copies `burned_in` only when present. Fail-closed on a record that never answered question 4 is *intended* (L-m). I agree with the refutation; these are not criticals.

## 2. Agree / disagree

| Finding | Verdict | Why |
|---|---|---|
| glm: burned_in truncation fail-open | **Agree** | Verified: `check()` cut to 12, no marker; contrast `on_screen_text_truncated` precedent. Now fixed + tested. |
| glm: wordless bug | **Agree** | Verified: contract demanded `str`; a logo-only bug returns `text: null`. Now fixed + tested. |
| glm: dual-reason hook+layout | **Agree** | Verified: `or` short-circuit hid ruling-93 reason. Now fixed + tested (test_medley.py:378–388). |
| qwen: pre-93 records blocked (×2) | **Disagree (as critical)** | VERSION in cache key; sealed() copies new key only when present. Fail-closed is intended. |
| qwen: eligibility doesn't read visual verdict | **Disagree** | Frames exist only at pin stage; eligibility runs on the ledger. The ruling's "reads the visual verdict" is satisfied by the pin-stage gate in both builds. |
| grok: redundant local import | **Disagree** | spotlight.py binds VP only inside build(); the import at :91 is needed. |

## 3. New findings (Cycle 2)

**<medium> N1 — package.py:72–74: the `vbad` dict comprehension's value expression is wrong for the "measured but ruling-93-blocked" case.** Read carefully:

```python
vbad = {m["moment_id"]: ((m.get("visual") or {}).get("why") if not (m.get("visual") or {}).get(
            "measured") else None) or VP.layout_block(m.get("visual"))     # ruling 93: per clip (L-m
        for m in segs if VP.layout_block(m.get("visual"))}                 # included); the cause named
```

The intent (per the comment and the consensus: "a measured line-up clip blocked by ruling 93 now reports ruling 93's reason, not the record's stale why; an unmeasured clip still reports its own why") is: unmeasured → record's `why`; measured → `layout_block`'s reason. Trace a **measured** record with a stale `why` (e.g. a prior backend timeout note) that now has a ticker: `not measured` is False → value = `None or VP.layout_block(...)` → the ruling-93 reason. Correct. Trace an **unmeasured** record: value = `why or layout_block(...)` → the record's `why` if present, else layout_block's "not measured (law L-m)". Correct. **But** the *filter* is `VP.layout_block(m.get("visual"))` — for an unmeasured record, `layout_block` returns "its visual check is not measured (law L-m)", so the filter catches it; fine. Now trace a record with `measured: True`, `burned_in` present, **no** blocking item, but a stale `why`: filter → `layout_block` returns None → not in `vbad` → proceeds. That is the intended behavior (the stale why is informational). So the logic holds. **The residual defect:** the value for an unmeasured record *prefers the record's `why` even when `layout_block` would name ruling 93* — but for an unmeasured record `layout_block` can only say "not measured", which is the same fact. No divergence. **Conclusion: N1 is not a defect; I withdraw it.** What remains verifiable: the *line-up* sweep at package.py:60–62 uses only `layout_block` and reports "rulings 70 / 93: not measured, or not eligible on its frames" — a *generic* message, while the *no-voice* sweep at :72–74 names the cause. Asymmetric, cosmetic.

**<medium> N2 — spotlight.py:120–122: the stop() message precedence.** The ternary: `not measured` → else `VP.layout_block(v) or f"not clean ({flags})"`. For a record that is measured, has a ruling-70 flag **and** a ticker, the ruling-93 reason prints and the ruling-70 flag kinds are hidden. glm noted this in Cycle 1 and *withdrew it*; I confirm the withdrawal — the precedence (not-measured → ruling-93 → ruling-70-flags) is the right order of informativeness, and the clip is held either way. Cosmetic only.

**<medium> N3 — visual_pin.py:209: the sort key `burned_block(x) is None` is a bare boolean, so the sort is stable but the *order among blocking items* is their original order, and among eligible items likewise — fine. However, the sort runs *before* the TEXTS_MAX cut, and `burned_block` reads `x["text"][:80]` — after check() has already truncated text to TEXT_CHARS=200, so the 80-char slice in the reason string is safe. No defect.** What *is* worth noting: `burned_block` is called on the *post-truncation* items (check() output), so a reason's 80-char preview reflects the truncated text — consistent, since sealed() stores the truncated form. No defect.

**<medium> N4 — test_medley.py:397: `out["package"]["gates"]["visual"]["flags"]` asserts the flag carries `segment=1` added by the package's gate sheet, not by flags() — this passes only if the package's gate-assembly adds `segment` to every flag. Not verifiable from this diff (the gate-assembly code is not shown); if it does not, this test fails.** Flag as *unverifiable from the diff* rather than a defect; the test will catch it either way.

**<medium> N5 — eligibility.py:35: `R("layout_ineligible", f"{facts['channel']}: no registry channel id")` — the reason detail no longer distinguishes "no registry entry at all" from "registry entry without an id".** Both are the same failure mode operationally (no id → no frames-fetchable channel), and the ruling says "never by name", so the detail naming the channel is the *fact's* channel, not a hold. Cosmetic.

**<medium> N6 — the ruling's "The render's G10 stays as it is and runs on EVERY clip (not only has_chyron channels), still monitoring" — nothing in this diff touches the render's G10.** That is the render session's side, not this branch's; the ruling assigns it there. Not a defect of this diff, but the audit checklist item "no channel is held by name anywhere in this path" is satisfied only for the *builder* side; the render side is out of scope of this diff. Note it, don't block on it.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| eligibility.py | 9/10 | 9/10 | Unchanged; the hold-by-name is gone, the no-registry-id hold remains, tests updated coherently. |
| visual_pin.py | 8/10 | 9/10 | Both glm fail-opens (truncation, wordless bug) fixed and tested; contract, sort-then-cut, sealed() all verified. |
| package.py | 8/10 | 8.5/10 | Dual-reason fix correct; the :72–74 comprehension traces correctly; only the generic-vs-named message asymmetry remains. |
| spotlight.py | 8/10 | 8.5/10 | clean_visual is the single predicate everywhere (inventory row :104, build gate :117); precedence in stop() is right. |
| Tests | 8/10 | 9/10 | Every fixed defect has a must-fail→must-pass test; the ruling-93 contract test is thorough (bad kinds, partly, "no" as bool, "none" as list). |
| **Overall** | 8.2/10 | **8.8/10** | All Cycle-1 defects closed with tests; remaining items are cosmetic or out-of-diff. |

## 5. Final priority list

- **P0 CRITICAL:** none.
- **P1 HIGH:** none.
- **P2 MEDIUM:**
  1. package.py:60–62 vs :72–74 — the line-up sweep's `why_not` is generic ("rulings 70 / 93: not measured, or not eligible on its frames") while the no-voice sweep names the cause; a ruling-93-blocked line-up clip's *specific* reason (which item, which text) never reaches the orchestrator's sheet. Cosmetic; the clip is held either way.
  2. test_medley.py:397 — the `segment=1` assertion depends on gate-assembly code not shown in this diff; unverifiable here, will fail loudly if wrong.
  3. eligibility.py:35 — the layout_ineligible detail no longer distinguishes "no registry entry" from "entry without id". Cosmetic.
  4. (Out of diff, note only) the render's G10 "runs on EVERY clip" — the render session's side; this branch cannot verify it.

## 6. The single highest-leverage change

Propagate the *specific* ruling-93 reason (which burned-in item, which text) into the line-up sweep's `why_not` at package.py:60–62, so the orchestrator's sheet names the cause as the no-voice sweep already does — everything else in this diff is already correct and tested.

## 7. Production ready?

**Yes with conditions** — both conditions are P2, neither blocks the ruling's invariants:

1. Name the specific ruling-93 cause in the line-up sweep's `why_not` (package.py:60–62), matching the no-voice sweep's specificity (:72–74).
2. Confirm the `segment=1` flag-assembly behavior that test_medley.py:397 depends on (code not in this diff) — the test will catch it, but confirm before merge.

Every invariant in the checklist holds: no channel held by name (eligibility.py:25, tests at test_eligibility.py:289–302, test_select_by_id.py:527–533); a ticker/crawl/cut/covering item cannot reach a pin (visual_pin.py:235–258, gated in both builds); unmeasured and pre-93 records never pass (visual_pin.py:253–256, L-m); a whole static item is eligible, flagged, and clean (visual_pin.py:230–232, spotlight.py:86–93, tested); sealed() adds the new key only when present, so pre-93 pins keep their digest (visual_pin.py:265–267).