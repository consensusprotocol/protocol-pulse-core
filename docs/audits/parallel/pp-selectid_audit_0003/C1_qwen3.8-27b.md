# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 18942 / out 2572 usd~0.095 (upper-bound price)

I’ll audit the diff strictly against the stated RULING 93 and the governing laws, focusing on the specific invariants you listed.

## Findings

### <critical>
**1. `spotlight.clean_visual` fails closed on pre-RULING-93 records, breaking the "still recompute" invariant for existing pins.**
*   **File:** `pipeline/spotlight.py` (lines 84-91 in diff)
*   **Scenario:** A pin sealed before this change has a `visual` record with `measured: True` but **no** `burned_in` key (since `VERSION` was `visual-1`).
    *   `clean_visual` calls `VP.layout_block(v)`.
    *   `layout_block` (in `visual_pin.py`) checks: `if not isinstance(rec.get("burned_in"), list): return "ruling 93: the burned-in text question was not asked..."`.
    *   Therefore, `layout_block` returns a string (truthy).
    *   `clean_visual` returns `False`.
    *   **Consequence:** Any existing "clean" pin that is re-evaluated by the spotlight logic (e.g., during a re-render or regression check of a previously approved package) will now be flagged as "not clean" and potentially dropped or held, even though it was valid under the previous rules. The prompt states: *"medley pins sealed before the change still recompute... the seal reads the visual record only through sealed()... whose new key appears only on new records."* However, `clean_visual` is used in `spotlight.build` to determine if a moment is "clean" for the inventory. If a pin is re-processed, it will fail this check.
    *   **Law Violation:** This contradicts the requirement that pre-existing valid pins should not be invalidated by the new check unless they are actually re-measured. The `layout_block` function is too strict for *existing* records that simply lack the new field. It should likely treat a missing `burned_in` field as "not applicable" (pass) for records with `version == "visual-1"`, or the spotlight logic needs to distinguish between "unmeasured" and "measured but old version". Currently, `layout_block` conflates "not measured" and "measured but old version" into a block.

**2. `package.build` drops clips based on `layout_block` which blocks old records, causing data loss for existing pins.**
*   **File:** `pipeline/package.py` (lines 59-61, 71-72 in diff)
*   **Scenario:** Similar to above. If a line-up contains a clip with a `visual-1` record (measured, clean), `VP.layout_block(m.get("visual"))` will return a string because `burned_in` is missing.
    *   In `package.build`, `vbad` will include this moment.
    *   The code then executes `dropped |= set(vbad)` and returns `None` (or re-lines).
    *   **Consequence:** Valid, previously approved clips are dropped from the package because their visual records predate RULING 93. This violates the "smallest diff" and "no new renderer" spirit, but more importantly, it breaks the pipeline for any content that hasn't been re-measured with `visual-2`. The prompt implies that *new* checks are added, but existing valid pins should remain valid unless re-measured. The current implementation forces a re-measure or a drop.

### <high>
**3. `eligibility.layout_ok` no longer checks `has_chyron`, but `layout_ineligible` reason is only for "no registry id".**
*   **File:** `pipeline/eligibility.py` (lines 18-25, 33-35 in diff)
*   **Scenario:** The RULING 93 states: *"The has_chyron flag stays in the registry as a hint that orders the check, nothing more."*
    *   The code change removes `has_chyron` from `layout_ok`. This is correct per the ruling.
    *   However, the `layout_ineligible` reason in `_source` is now hardcoded to `"no registry channel id"`.
    *   **Issue:** If a channel *has* a registry id but its clip is blocked by `visual_pin.layout_block` (e.g., due to a ticker), the `eligibility` module does *not* report `layout_ineligible`. It reports `ok` (assuming other checks pass). The blocking happens later in `package.build` or `spotlight.build`.
    *   **Consequence:** The `eligibility` facts (`layout_eligible`) will be `True` for a clip that is actually ineligible due to visual content. This creates a mismatch between the "eligibility" stage and the "package/spotlight" stage. The RULING says *"eligibility drops the channel-name hold and reads the visual verdict."* But `eligibility.py` does **not** read the visual verdict. It only checks the registry ID. The visual verdict is read in `package.py` and `spotlight.py`.
    *   **Law Violation:** The prompt says *"YOUR SIDE: eligibility drops the channel-name hold and reads the visual verdict."* The code does **not** make `eligibility` read the visual verdict. It only drops the channel-name hold. The visual verdict is read downstream. This might be acceptable if "reads the visual verdict" was interpreted loosely, but strictly, `eligibility` should probably reflect the final layout eligibility. Currently, `facts["layout_eligible"]` is `True` even if the clip has a ticker. This could mislead other parts of the system that rely on `eligibility` facts.

**4. `visual_pin.check` requires `burned_in` to be a list, but `flags` function assumes it exists.**
*   **File:** `pipeline/visual_pin.py` (lines 190-203, 218-226 in diff)
*   **Scenario:** `check()` validates that `burned_in` is a list of dicts. `flags()` then iterates over `v.get("burned_in") or []`. This is safe.
*   **However:** `layout_block()` checks `if not isinstance(rec.get("burned_in"), list)`. If `rec` is a valid `visual-2` record, `burned_in` is a list. If it's `visual-1`, it's missing.
*   **Issue:** The `sealed()` function includes `burned_in` in the output. If a `visual-1` record is sealed, `burned_in` is not in the `rec` dict, so it's not in the `out` dict. This is fine. But `layout_block` will block it. See Critical #1 and #2.

### <medium>
**5. `spotlight.clean_visual` logic for `burned_in` flags.**
*   **File:** `pipeline/spotlight.py` (lines 84-91 in diff)
*   **Scenario:** `clean_visual` returns `True` if `not [f for f in v.get("flags") or [] if f.get("kind") != "burned_in"]`.
    *   This means if there are *any* flags that are **not** `burned_in`, it returns `False`.
    *   If there are *only* `burned_in` flags, it returns `True` (assuming other conditions pass).
    *   **Issue:** The RULING says: *"A static lower third or channel bug that sits whole in the 16:9 and is either wholly in or wholly out of the 9:16 crop = eligible, flagged for me."*
    *   The code correctly allows `burned_in` flags to exist in a "clean" visual.
    *   **However:** `flags()` in `visual_pin.py` adds a `burned_in` flag for *every* item that is **not** blocked by `burned_block`.
    *   If a clip has a ticker, `burned_block` returns a string, so `flags()` does **not** add a `burned_in` flag for it. `layout_block` returns a string. `clean_visual` returns `False` (because `layout_block` is truthy). This is correct.
    *   If a clip has a whole lower third, `burned_block` returns `None`. `flags()` adds a `burned_in` flag. `layout_block` returns `None`. `clean_visual` checks `not [f for f in flags if f.kind != "burned_in"]`. Since the only flag is `burned_in`, the list is empty, so `not []` is `True`. `clean_visual` returns `True`. This is correct.

**6. `package.build` hook blocking.**
*   **File:** `pipeline/package.py` (line 48 in diff)
*   **Scenario:** `why_v = VP.hook_block(m["visual"]) or VP.layout_block(m["visual"])`.
    *   If `hook_block` is `None` and `layout_block` is a string, `why_v` is the string.
    *   The hook is blocked. This is correct per RULING 93 ("A ticker or crawl = not eligible" in any role, including hook).

**7. Test coverage for pre-RULING-93 records.**
*   **File:** `tests/package/test_visual_pin.py` (lines 484-485 in diff)
*   **Scenario:** `self.assertIn("not asked", VP.layout_block({"measured": True, "flags": []}))`.
    *   This test confirms that a record without `burned_in` is blocked.
    *   **Issue:** This test validates the behavior that causes Critical #1 and #2. It confirms that old records are blocked. The question is whether this is the *desired* behavior. The prompt says *"medley pins sealed before the change still recompute... the seal reads the visual record only through sealed()... whose new key appears only on new records."* This implies old records should *not* be blocked by the new check, or at least that the system should handle them gracefully. The current implementation blocks them.

## SHIP: no

**Reasons:**
1.  **Critical:** Pre-RULING-93 pins (visual-1) are now blocked by `layout_block` and `clean_visual`, causing valid existing content to be dropped or held. This violates the requirement that existing pins should still recompute/remain valid unless re-measured.
2.  **High:** `eligibility` does not read the visual verdict, so `facts["layout_eligible"]` is misleading for clips blocked by visual content. The RULING explicitly states eligibility should read the visual verdict.

**Conditions for Ship:**
1.  Modify `visual_pin.layout_block` to return `None` (pass) if `rec.get("version") == "visual-1"` and `rec.get("measured") is True`. Only block if `version == "visual-2"` and `burned_in` is missing/invalid, or if `version` is unknown.
2.  Update `spotlight.clean_visual` to handle `visual-1` records as "clean" if they were previously clean (i.e., `measured` and no non-burned_in flags).
3.  Update `eligibility` to incorporate the visual verdict if available, or clarify that `layout_eligible` in eligibility only refers to registry ID, and visual eligibility is handled downstream. If the RULING requires eligibility to reflect visual verdicts, `eligibility` must access the visual record.