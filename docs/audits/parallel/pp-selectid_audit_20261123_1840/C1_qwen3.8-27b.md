# qwen3.8-27b (qwen/qwen3.8-27b) 241 s finish=stop usage in 12100 / out 8426 usd_reported=0.007529 usd~0.163 (upper-bound price)



# Code Audit — pp-selectid / RULING 146 (3) "Sponsor Before" Soft Gate

## Scope

Reviewed the 276-line diff across `pipeline/moments.py`, `pipeline/package.py`, `pipeline/package_pin.py`, and two test files. Checked all four requested questions plus general correctness against the governing laws.

---

## Findings

### [P2] `n` field in the "sponsor" gate row reports the wrong count

**Location:** `package.py`, `inventory()` — the new `"sponsor"` row (diff line 135).

```python
"n": len(exc)
```

`exc` is the **entire** exclusion-results dict (every moment that went through the exclusion model, regardless of verdict or flag). The other FLAGGED rows in the same inventory use `n` for the count of items *in that category* (e.g. `"n": len(visual)` for graphics). Here, if 12 moments pass through exclusion and only 1 is kept with an `ad_before` mark, the report reads `"n": 12` next to a single flag. A reviewer scanning the gate report will misread the scope.

**Fix:** count only the flagged entries:

```python
"n": sum(1 for e in exc.values() if e.get("ad_before") and e.get("verdict") == "keep")
```

This does not affect the cap (which counts the `flags` list, not `n`), but it makes the sealed report internally consistent and prevents a human from thinking 12 clips are sponsor-adjacent when only 1 is.

---

### [P3] `ad_before_soft` distinguishes before-markers from moment-markers by `str.endswith`

**Location:** `package.py:1305` (diff line 55).

```python
out = {k: v for k, v in ad_read.items() if soft and v.endswith("in the sentence before it")}
```

The entire soft/hard split hinges on the reason string ending with the exact phrase `"in the sentence before it"`. If `ad_read_marker` (moments.py:358, unchanged) ever reformats its return (e.g. appends a channel name, changes word order, or localises), the filter silently stops matching and **every** before-marker reverts to a hard exclude — the never-empty pass loses its only concession with no error, no log, no test failure (the existing tests hard-code the same string, so they'd pass against the old format but the production `ad_read_out` would produce the new one).

Not a correctness bug today, but a one-word refactor in `ad_read_marker` would silently disable the feature. A structured return (e.g. `{"reason": ..., "location": "before"|"moment"}`) or a dedicated sentinel would be more robust.

---

### [P3] `ad_before_soft` mutates the caller's list in place

**Location:** `package.py:1303-1308` (diff lines 53-58).

```python
for m in ms:
    m.pop("ad_before", None)
...
for m in ms:
    if m["moment_id"] in out:
        m["ad_before"] = out[m["moment_id"]]
```

The function both clears and re-sets `ad_before` on the dicts in `ms`. In the current sequential pipeline this is safe (the list is immediately re-filtered and the original is not reused), but the side-effect is invisible from the signature. A future caller that reuses the same list of moment dicts across two `_build` invocations (e.g. a retry or a dry-run) would see stale marks. A `dataclasses.replace`-style copy or a return-only design (no mutation) would remove the foot-gun.

---

## Answers to the four requested checks

| # | Question | Verdict |
|---|----------|---------|
| 1 | Can words of the clip **itself** that belong to an ad read reach a sealed package? | **No.** `ad_read_marker(moment_text)` (no `before_text`) is checked independently; a truthy result forces `soft_why = None` → deterministic hard exclude before any model call. Even if the deterministic marker list misses a phrase, the model's `ad_read` risk is a hard exclude (test `test_the_model_decides_a_marker_in_the_sentence_before`, second assertion). Two independent layers. |
| 2 | Can the clean pass, or a cached verdict from the other pass, let a marked moment in? | **No.** Clean pass: `soft=False` → `ad_before_soft` returns `{}` → no moment is marked → `before_marker_soft=False` → deterministic screen still hard-excludes. Cache key: soft pass uses `(mid, seed, "ad_before")`; clean pass uses `mid` or `(mid, seed)`. Disjoint key spaces; a cached verdict from one pass is never read by the other. Verified by `test_the_mark_is_the_passs_own_and_the_cache_key_its_own`. |
| 3 | Is the flag right (one per kept marked clip, counted toward the cap of 3)? | **Yes, with the P2 caveat on `n`.** The `flags` list is built with a list-comprehension over `exc.items()` filtered to `ad_before` + `verdict == "keep"` — exactly one entry per kept marked clip. The existing `content_flags` cap (package_pin.py:440) counts every FLAGGED row's `flags` list, so the new row's flags are included in the cap of 3. The `n` field is wrong (see P2) but does not affect the cap. |
| 4 | Does the `gate_problems` addition refuse anything a live pin legitimately carries? | **No.** The new loop only fires for gates **outside** the required set with status `FLAGGED`. All live soft rows (`graphics`, `runtime`, `hook_onset`, `pbx_exception`) are in `SOFT_GATES` and carry non-empty plain flags, so `flagged_ok` passes. The new `sponsor` row is also in `SOFT_GATES` with non-empty flags. A made-up or flag-less row is correctly refused (test `test_an_extra_flagged_row_stands_only_on_a_soft_gate_with_flags`). |

---

## Law compliance spot-check

- **LAW 20 / M2:** No gate threshold is changed. The new `sponsor` row is FLAGGED (soft), not a pass/fail gate. The deterministic screen's hard-exclude path is unchanged. No reclassification.
- **M12 FAIL CLOSED:** If the model is unavailable or returns an unparseable verdict, the existing `exclusion_verdict` code (unchanged) returns an exclude. The soft path only *delays* the decision to the model; it never converts a failure into a pass.
- **L-j:** The `sponsor` row carries `"replayed": False`. It is not in `REQUIRED_GATES`, so `release_auth`'s exact-inventory check does not require it to be PASS; it is a MONITORING/soft row. The `gate_problems` addition ensures it can't sneak in without proper flags.
- **Smallest diff / M1:** No new renderer, compositor, or selector. Changes are confined to the exclusion screen, the pool filter, the inventory row, and the gate-problems validator.

---

P1_OR_WORSE: 0