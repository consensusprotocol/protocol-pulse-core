# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 418 s finish=stop usage in 8688 / out 30570 usd_reported=0.003031 usd~0.485 (upper-bound price)

# Code Audit: pp-selectid — RULING 123 (2) A 16:9-Only Hook

## Review of the Four Requested Checks

**(1) Exception fires only when no both-format hook exists** — The guard `if rated_open and not [m for m in rated_open if not m.get("visual_hook_block")]` correctly requires that *every* rated opener carries a `visual_hook_block`. If any rated opener lacks one (i.e., a both-format hook exists), the list comprehension is non-empty, `not [...]` is `False`, and the exception block is skipped entirely. ✅ Correct.

**(2) Only the hook is excused, and only for the 9:16 crop** — Both per-segment layout checks gate the skip on `m is order[0]` / `m is segs[0]` **and** `opens_16x9(m)`. `opens_16x9` requires the `sixteen_nine_only` flag, `formats == ["16x9"]`, and `crop_only` still naming the record — so only the first segment (the hook) and only for ruling 93's crop are excused. As a clip, `opens_16x9` is never consulted for non-first segments. ✅ Correct.

**(3) The seal says 16:9 only** — `m["visual"] = dict(m["visual"], formats=["16x9"])` writes the sealed formats; the test asserts `package_pin.formats_of(...) == ["16x9"]`. ✅ Correct.

**(4) The tests** — Four tests cover: crop_only qualification (ticker / covers_speaker / whole_in_16x9=False / nothing refused / older version / unmeasured / third-person all return None), the happy path (package built, sealed 16:9), a both-format hook winning (exception doesn't fire), and the moment refused as a clip. Coverage is solid. ✅ Correct.

---

## Findings

**[P2] `crop_only` guard may return `None` after the record is sealed, breaking `opens_16x9` in the per-segment checks.**
`crop_only` contains the guard `(formats(rec) and not RENDER_16X9_ONLY)`. The build sequence is:
1. `build()` calls `crop_only` on the **unsealed** record → returns truthy → unblocks and seals with `formats=["16x9"]`.
2. Later, the per-segment layout check calls `opens_16x9(m)` → which calls `crop_only(v)` on the **now-sealed** record.

If `formats(rec)` reads `rec.get("formats")` (returning `["16x9"]`, truthy) and `RENDER_16X9_ONLY` is `False` (the normal both-format render mode), the guard fires and `crop_only` returns `None`. `opens_16x9` then returns `False`, the per-segment check does **not** skip ruling 93 for the hook, and the package is rejected — the exact opposite of the ruling's intent.

The test `test_with_no_both_format_hook_it_opens_a_package_sealed_16x9_only` asserts `assertIsNotNone(out["package"])`, which would catch this if the guard fires. So either the guard does not fire (because `formats()` returns falsy for `["16x9"]`, or `RENDER_16X9_ONLY` is `True` in this context), or the test fails. Since neither `formats()` nor `RENDER_16X9_ONLY` is visible in this diff, the interaction cannot be confirmed safe. **Recommend explicitly verifying that `crop_only` still returns truthy on a sealed `formats=["16x9"]` record**, or restructuring `opens_16x9` to not re-call `crop_only` after sealing (e.g., cache the crop_only result alongside `sixteen_nine_only`).

**[P3] Redundant local import in `opens_16x9`.**
`import visual_pin as VP` inside `opens_16x9` is unnecessary — `VP` is already used unqualified throughout `build()` (lines 28, 52 of the diff), confirming it is imported at module scope. The local import shadows the module-level name for no benefit.

---

P1_OR_WORSE: 0