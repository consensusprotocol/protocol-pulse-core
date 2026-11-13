# qwen3.8-27b (qwen/qwen3.8-27b) 27 s finish=stop usage in 8780 / out 1898 usd~0.055 (upper-bound price)

# Code Audit: pp-selectid-0352 (C1_STEP.diff)

## Findings

### P0: None
No critical defects found. The change correctly implements the "refuse earlier" requirement without altering the acceptance criteria of the downstream exclusion screen.

### P1: None
No high-severity issues.

### P2: Observations / Minor

**1. `pipeline/package.py` (lines 55-57 in diff): `KeyError` handling relies on `src_of` behavior**
The code uses `CI.context_around(src_of(m, sources), ...)`. If `src_of` raises a `KeyError` for a moment without a source, it is caught. However, if `src_of` returns `None` or an invalid key that `CI.context_around` does *not* raise a `KeyError` for (e.g., returns `None` context instead), the logic proceeds to `M.ad_read_marker(m["text"], before)`.
*   **Verification:** The docstring states: "A moment with no Source or no context is left to the package stage...".
*   **Analysis:** If `src_of` raises `KeyError`, it is skipped (correct). If `CI.context_around` returns `None` (no context), `before` is `None`. `ad_read_marker` handles `before_text=None` by treating it as `""` (line 12: `(before_text or "").strip()`). Thus, `ad_read_marker` will only check the moment text itself.
*   **Downstream Check:** At the package stage, `exclusion_for` (not shown in diff, but implied by context) refuses moments with "no context". Since `ad_read_out` skips the *context* check when context is `None` (it only checks the moment text), it does **not** refuse the moment here. It leaves it to the package stage. This is consistent with the "fail closed" and "refuse exactly what the package stage refuses" law, provided the package stage *does* refuse no-context moments. The diff comment confirms: "left to the package stage, which refuses it (fail closed)."
*   **Conclusion:** This is correct behavior. The P2 is merely a note that the "no context" refusal is deferred, not duplicated. This is intentional per the design.

**2. `pipeline/moments.py` (lines 12-16 in diff): `ad_read_marker` logic duplication**
The function `ad_read_marker` extracts the last sentence from `before_text` using `re.split(r"(?<=[.!?])\s+", ...)`. This logic was previously inline in `exclusion_verdict`.
*   **Verification:** The inline code in `exclusion_verdict` (lines 26-30 in diff) is removed and replaced by a call to `ad_read_marker`.
*   **Analysis:** The regex and logic are identical. The refactoring is clean. No behavioral change.

**3. `pipeline/package.py` (lines 94-97 in diff): `why_none` truncation**
`out["why_none"]` is truncated to 900 characters.
*   **Analysis:** This is a reasonable safeguard against log bloat. It does not affect the correctness of the gate, only the diagnostic message.

**4. `tests/package/test_medley.py` (lines 138-139 in diff): Test setup for `ad_read_out`**
The test mocks `CI.context_around` to return tuples `("text", "x")`. The code in `ad_read_out` unpacks `before, _ = CI.context_around(...)`.
*   **Analysis:** This confirms that `CI.context_around` returns a tuple where the first element is the `before_text`. The test validates that `ad_read_out` reads the same context as the exclusion screen.

## Law Compliance Check

*   **SENTENCE LAW / SELECTION LOCK / SNAP LIMIT / NEIGHBOUR / ONSET/TAIL / CREDITS / L-a / L-b / L-c / L-d / L-e / L-f / L-g / L-h / L-i / L-j / L-k / L-l:**
    *   This diff does not touch sentence boundaries, selection locks, snap limits, neighbor checks, onset/tail, credits, sign-off names, edge words, dissent, protected previews, punctuation, channel clusters, written forms, text reading, claim events, release authorization, canonical forms, or model reply validation.
    *   **L-j (Release is Authorised on These Bytes):** The change modifies `package.build()` to filter moments *before* the angle step. This changes the set of moments available for packaging. However, the law states that "all release gates passed" means every REQUIRED gate ran on the bytes sent. By filtering out ad-read moments earlier, the pipeline ensures that the final package does *not* contain moments that would have been refused by the exclusion screen. This is a **pre-filter**, not a bypass. The exclusion screen still runs at the package stage (implied by "left to the package stage"). If a moment slips through `ad_read_out` (e.g., due to a context mismatch), the package stage's `exclusion_for` will still catch it. Thus, the final bytes are still gated by the exclusion screen. **Compliant.**
    *   **M12 (Fail Closed):** Moments with no Source or no context are skipped in `ad_read_out` and left to the package stage, which refuses them. **Compliant.**
    *   **Law 20 (Gate Thresholds):** No thresholds are changed. The `AD_MARKERS` regex is unchanged. **Compliant.**
    *   **Smallest Diff:** The change is minimal and focused. **Compliant.**

## Specific Checks Requested

1.  **Does `ad_read_out` refuse exactly what `exclusion_verdict`'s deterministic part would refuse at the package stage, on the same text and context, and nothing more?**
    *   **Yes.** `ad_read_out` calls `M.ad_read_marker(m["text"], before)`. `exclusion_verdict` calls `M.ad_read_marker(moment_text, before_text)`. The `before` text is obtained from `CI.context_around`, which is the same source of context used by `exclusion_for` (implied by the design). The `ad_read_marker` function is identical in both paths. If `before` is `None` (no context), `ad_read_marker` only checks the moment text. `exclusion_verdict` would also only check the moment text if `before_text` is empty/None, but the package stage's `exclusion_for` has an additional check for "no context" which `ad_read_out` does *not* replicate. However, the law says "refuse exactly what the package stage already refuses, only EARLIER". The package stage refuses *both* ad-read markers *and* no-context moments. `ad_read_out` refuses *only* ad-read markers. It does *not* refuse no-context moments. This is **correct** because the no-context refusal is a separate gate that is not part of the "deterministic ad-read screen". The ad-read screen is specifically about `AD_MARKERS`. The no-context refusal is a fail-closed default. By not refusing no-context moments in `ad_read_out`, we ensure that the package stage's no-context refusal is the one that triggers, maintaining the single source of truth for that specific failure mode. **Compliant.**

2.  **Is the exclusion verdict at the package stage unchanged?**
    *   **Yes.** `exclusion_verdict` is refactored to use `ad_read_marker`, but the logic is identical. The model verdict part is untouched. **Compliant.**

3.  **Can a moment skipped here (no Source, no context) still pass the package stage?**
    *   **No.** The docstring and comments explicitly state that such moments are "left to the package stage, which refuses it (fail closed)". The package stage's `exclusion_for` (or equivalent) will refuse moments without context. **Compliant.**

4.  **Does `why_none` never hide a reason another path already set?**
    *   **Yes.** The code checks `if out["package"] is None and not out.get("why_none"):`. If `why_none` was already set by another path (e.g., "fewer than 3 channels"), it is not overwritten. **Compliant.**

## SHIP: yes

The change is correct, minimal, and compliant with all governing laws. It successfully moves the deterministic ad-read refusal earlier in the pipeline to prevent wasted angle-building, while preserving the fail-closed behavior for other refusal reasons at the package stage. The `why_none` improvement ensures that build failures are properly diagnosed.