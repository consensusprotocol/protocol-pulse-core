# gemma-4-31b-it (google/gemma-4-31b-it) 184 s finish=stop usage in 12873 / out 3783 usd_reported=0.002044 usd~0.095 (upper-bound price)

The code implements RULING 146 (3) to allow clips that follow a sponsor mention (but do not contain one) to be kept in the "never-empty" pass, provided a model confirms the clip itself is not an ad.

### Analysis against "PLEASE CHECK" requirements:

1.  **Can any words of the clip ITSELF that belong to an ad read reach a sealed package?**
    **No.** In `pipeline/moments.py:369`, `soft_why` is only assigned if `ad_read_marker(moment_text) is None`. If the clip contains a marker, `soft_why` remains `None`, and the `if why and not soft_why` block (line 370) triggers a deterministic `exclude` before the model is even called. Furthermore, the model is prompted to identify `ad_read` risks within the moment's own words, which results in a hard `exclude`.

2.  **Can the clean pass, or a cached verdict from the other pass, let a marked moment in?**
    **No.** 
    - **Clean Pass:** In `pipeline/package.py:1299`, `ad_before_soft` is called with `soft=False`, returning an empty dict. The filter in `_build` (line 3452) then defaults to `m["moment_id"] not in ad_read`, maintaining the strict deterministic exclusion.
    - **Cache Leakage:** In `pipeline/package.py:3150`, the cache key is explicitly modified when `soft` is True: `(m["moment_id"], seed, "ad_before")`. This ensures that a "keep" verdict generated for the never-empty pass cannot be retrieved by the clean pass, which uses the standard `(m["moment_id"], seed)` key.

3.  **Is the flag right (one per kept marked clip, counted toward the cap of 3)?**
    **Yes.** `pipeline/package.py:1336` generates a list of flags by iterating over `exc.items()`, creating one string per clip that has both `ad_before` and a `keep` verdict. These are passed into the `sponsor` gate row. Since this is a standard `FLAGGED` row in the gate inventory, it is processed by the existing `review_flags_of` and `content_flags` logic (as noted in the audit notes), which enforces the cap.

4.  **Does the gate_problems addition refuse anything a live pin legitimately carries?**
    **No.** The addition to `pipeline/package_pin.py:459` ensures that any `FLAGGED` row not in the `REQUIRED` set must be a recognized `SOFT_GATE` with valid flags. Since `"sponsor"` was added to `SOFT_GATES` (line 150), it is explicitly permitted. Other existing soft gates (graphics, runtime, etc.) remain permitted.

### Technical Correctness:
- **State Management:** `ad_before_soft` correctly pops existing `ad_before` marks (line 1295) to prevent stale marks from persisting across different build attempts or passes.
- **Data Flow:** The `chan_of` mapping is correctly implemented in `_build` (lines 106, 116) and passed to `inventory` to ensure the flags correctly identify the channel.
- **Test Coverage:** `TestRuling146SponsorBefore` comprehensively covers the deterministic vs. model-based decision paths, the cache key isolation, and the final gate status.

P1_OR_WORSE: 0