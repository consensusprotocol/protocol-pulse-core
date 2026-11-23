# qwen3.8-27b (qwen/qwen3.8-27b) 208 s finish=stop usage in 11691 / out 7257 usd_reported=0.006612 usd~0.144 (upper-bound price)



# CYCLE 2 — CODE AUDIT (pp-selectid-20261123_1840)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Nothing material. All three Cycle 1 seats converged on the same four answers (NO / NO / YES / NO) and zero P0/P1 findings. Qwen's three P-level observations (the `n` field, the `str.endswith` coupling, the in-place mutation) were all valid *observations* but correctly dismissed by the consensus as non-defects:

- **`n` = `len(exc)`:** I initially flagged this as a readability concern, but the consensus is right — the sibling `graphics` row uses `n = len(visual)` (one visual record per clip, flagged or not). The `n` field means "how many items this row's check examined," not "how many are flagged." The `flags` list carries the per-clip detail. Consistent.
- **`str.endswith("in the sentence before it")`:** The two reason strings are fixed literals produced by `ad_read_marker` (moments.py:365, unchanged in this diff). The test `test_the_mark_is_the_passs_own_and_the_cache_key_its_own` feeds both forms. A future reformat would break the test, not silently pass. Not a latent bug.
- **In-place mutation of `ms`:** `with_verdict` gives `_build` its own copies; the `pop` at the top of `ad_before_soft` clears any stale mark before re-setting. The test pins this. By design.

I had no independent findings that the other seats missed.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | My position |
|---|---|
| Gemma: all four checks pass, P1_OR_WORSE 0 | **Agree.** |
| GPT-OSS: all four checks pass, no findings at any severity | **Agree.** |
| Qwen P2 (`n` field): **Disagree** it's a defect. The consensus is correct; `n` is "items examined," not "items flagged." |
| Qwen P3 (`str.endswith`): **Disagree** it's a risk. The strings are fixed literals in unchanged code; the test would catch a reformat. |
| Qwen P3 (mutation): **Disagree** it's a foot-gun. The pass owns its copies; the pop-first pattern is test-pinned. |
| Consensus: all three Qwen findings dismissed, no changes | **Agree.** |

## 3. NEW FINDINGS FROM THIS REVIEW

I re-traced every code path in the diff independently. Specifically I checked:

- **Edge case: marker in BOTH the clip and the sentence before.** `ad_read_marker(moment_text, before_text)` returns the moment's own marker (the "in the moment" form). The `soft_why` computation calls `ad_read_marker(moment_text)` independently — it returns non-None, so `soft_why = None`, and the deterministic exclude fires. Even if `ad_read_marker` checked the before first (it doesn't, but hypothetically), the independent call in `exclusion_verdict` line 27 would catch it. **No gap.**

- **Cache key type safety.** Clean pass seed=7: key is a bare string `mid`. Clean pass seed≠7: key is a 2-tuple `(mid, seed)`. Soft pass: key is a 3-tuple `(mid, seed, "ad_before")`. Python treats these as distinct dict keys. No cross-pass leakage possible. **No gap.**

- **`chan_of` missing a moment_id.** The flag uses `(chan_of or {}).get(mid) or 'its channel'`. If the dict lacks the key, the flag degrades to "its channel" — still a valid, non-empty flag. The `flagged_ok` check only requires non-empty flags, not a specific format. **No gap.**

- **`exc` empty (no moments went through exclusion).** The `any(...)` guard on the sponsor row evaluates to False; the row is not added. No crash, no empty FLAGGED row. **No gap.**

- **`ad_before` set to a falsy value.** `ad_before_soft` only assigns non-empty reason strings. The `pop` at the top clears any prior value. `bool(m.get("ad_before"))` in `exclusion_for` correctly distinguishes marked from unmarked. **No gap.**

- **`gate_problems` new loop vs. existing checks.** The new loop only fires for `g not in required`. The existing checks fire for `g in required`. Disjoint. No double-reporting. **No gap.**

- **Test rig fidelity.** The `test_medley.py` rig's `exclusion_for` stub now propagates `ad_before` exactly as the real function does (`**({"ad_before": m["ad_before"]} if m.get("ad_before") else {})`). The rig is faithful. **No gap.**

**No new findings at any severity.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `moments.exclusion_verdict` (soft_why logic) | Clean | Clean | Re-verified the two-layer guard (deterministic + model). No change. |
| `package.ad_before_soft` (mark lifecycle) | Clean | Clean | Pop-first, filter, re-set. Test-pinned. No change. |
| `package.exclusion_for` (cache key isolation) | Clean | Clean | Three distinct key shapes. No cross-pass leakage. No change. |
| `package._build` (pool filter) | Clean | Clean | `not in ad_read or in ad_soft` correctly keeps before-only moments. No change. |
| `package.inventory` (sponsor row) | Clean | Clean | One flag per kept marked clip. `n` is by-design. `chan_of` fallback safe. No change. |
| `package_pin.SOFT_GATES` + `gate_problems` | Clean | Clean | Sponsor is soft; new loop is disjoint from existing checks. No change. |
| Tests (`TestRuling146SponsorBefore`) | Clean | Clean | Covers deterministic vs. model paths, cache isolation, clean-pass invariance, gate_problems. 11/11 mutations killed. No change. |

## 5. FINAL PRIORITY LIST

| Severity | Finding | Location |
|---|---|---|
| — | None. | — |

No P0, P1, P2, or P3 findings.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The two-layer guard in `exclusion_verdict` (deterministic `ad_read_marker(moment_text)` check on line 27, then the model's `ad_read` risk) is the load-bearing safety: it is the only thing standing between a sponsor-adjacent clip and a sealed package, and it is correct.

## 7. PRODUCTION READY?

**Yes.** No conditions. All four audit checks pass. The clean pass is provably unchanged. Cache keys are disjoint. The flag is one-per-kept-clip and counted in the cap of 3. The `gate_problems` addition only adds refusals for non-soft FLAGGED rows, which no live pin carries. Tests cover every decision path and all 11 mutations are killed.

P1_OR_WORSE: 0