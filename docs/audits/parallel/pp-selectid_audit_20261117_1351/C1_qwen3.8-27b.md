# qwen3.8-27b (qwen/qwen3.8-27b) 315 s finish=stop usage in 12181 / out 12301 usd_reported=0.011081 usd~0.221 (upper-bound price)



# Code Audit — pp-selectid / RULING 141 (2): STAND_ALONE SOFT

## Scope

Reviewed the 271-line diff across `pipeline/package.py`, `pipeline/package_pin.py`, and `tests/package/test_ruling_137.py` implementing RULING 141 (2): in the never-empty (soft) pass, a moment left out *only* by the render's STAND_ALONE opener rule is admitted back as a clip, flagged with the exact prefix the integrator matches. The topic rule (ruling 34), the hook row, the medley-names-Bitcoin check, and unmarked clips remain hard.

---

## Findings

### [P2] `stand_plain` regex fallback silently degrades the flag text

**Location:** `package.py` lines 22–30 (`stand_plain`)

The two `re.match` calls parse the human-readable string returned by `SA.opener("clip", …)`. If the upstream format ever shifts (a reworded conjunction, an added clause, a different fault label), *both* regexes miss and the function falls through to `return why` — the raw `SA.opener` string. The flag is still well-formed (the prefix is prepended by `inventory`), so the integrator's prefix match still works and no gate is bypassed. However, the plain-language reason the reviewer sees in the pin record would be the internal `SA.opener` phrasing rather than the intended "it opens on 'but' and the clip scorer has no verdict for it" sentence, and the test `test_the_reason_in_plain_words` would not catch the regression because it tests the happy path.

**Suggestion:** Add a `test_the_reason_falls_back_to_raw_when_format_shifts` case that monkey-patches `SA.opener` to return an unexpected string and asserts `stand_plain` returns it verbatim (documenting the fallback contract). Alternatively, raise/log a warning when neither regex matches so a format drift is visible in the build log.

---

### [P2] No end-to-end test for `soft=True` with a *hard* stand_alone failure in the pin row

**Location:** `tests/package/test_ruling_137.py`, `TestRuling141StandAloneSoft`

`test_the_row_flags_only_in_the_soft_pass` covers `soft=True` *with* soft rows (→ FLAGGED) and `soft=False` (→ FAIL). The end-to-end rig test covers the topic-rule moment "w" staying in `no_role`, but there is no test that drives the *pin inventory* with `soft=True` and a stand_alone check that fails on a **hard** condition (e.g. the hook row fails, or the medley doesn't name Bitcoin) and asserts the row status is `"FAIL"` (not `"FLAGGED"`) and that `gate_problems` is **non-empty** (i.e. the seal is blocked).

This matters because `"stand_alone"` is now in `SOFT_GATES`. The safety net is that `stand_with_soft` omits `soft_rows` when `stand_soft_rows` returns `None`, so the inventory's `if soft and stand.get("soft_rows")` guard prevents the FLAGGED status. But that guard is the *only* thing keeping a hard failure from being silently downgraded to a flag by the pin's soft-gate handling. A regression in `stand_with_soft` (e.g. always emitting `soft_rows={}`) would turn a hard FAIL into a FLAGGED with an empty flag list, and no existing test would catch it.

**Suggestion:** Add a test that calls `PK.inventory(…, stand=stand_with_soft(segs_with_hook_failure), soft=True, …)` and asserts `status == "FAIL"` and that the gate is a problem.

---

### [P2] `stand_soft_rows` couples segment order to `labels()` positionally

**Location:** `package.py` line 41

```python
by, out = dict(zip(labels(len(segs)), segs)), {}
```

The mapping from label → segment is purely positional: `segs[0]` is "hook", `segs[1]` is "clip_01", etc. This is correct today because `stand_alone_check` and the lineup builder always produce segments in that order. But the function's contract is "given a check result and the segments it checked, find the soft rows." If a future caller passes segments in a different order (or a subset), the mapping silently misaligns and a moment's `stand_soft` mark could be attributed to the wrong label, causing either a false soft (a hard failure treated as soft) or a false hard (a soft failure treated as hard).

**Suggestion:** Either (a) document the positional invariant in the docstring with an explicit `# INVARIANT: segs must be in label order`, or (b) build the map from each segment's own identity if one is available (e.g. `m.get("label")`), making the function order-independent.

---

### [P3] Double period when `SA.opener`'s raw string ends with "."

**Location:** `package.py` line 156 (inventory)

```python
STAND_SOFT_PREFIX.format(channel=…) + f"{why}."
```

If the fallback path in `stand_plain` returns a raw `why` that already ends with a period, the flag reads `"…may not stand alone: some reason.."`. Cosmetic only; the integrator matches the prefix, not the tail.

---

### [P3] `stand_back` dict-comprehension is dense

**Location:** `package.py` lines 101–102

```python
stand_back = {m["moment_id"]: p for m in ms if soft and m["moment_id"] in no_role and m["moment_id"] not in trims
              and no_topic(m) is None for p in [stand_plain(m)] if p}
```

Four filter conditions plus a nested `for p in [stand_plain(m)] if p` in a single comprehension is hard to audit. A short loop with an early-continue per condition would be easier to review and to add a log line to. Not a defect, but the audit prompt asks for the smallest diff that is also readable.

---

## Explicit answers to the five "PLEASE CHECK" items

| # | Question | Verdict |
|---|----------|---------|
| 1 | Can anything the topic rule, medley-names-Bitcoin, or hook rule refuses get through? | **No.** `stand_back` requires `no_topic(m) is None`. `stand_soft_rows` returns `None` (hard) if the hook row fails, any topic row fails, or `medley_names_bitcoin.pass` is not `True`. The hook role is separately gated by `SA.opener("hook")` in `_can_open`, which every conjunction opener fails. |
| 2 | Is the clean pass unchanged? | **Yes.** `stand_back` is gated on `soft`. The `stand_soft` mark is popped before any downstream read. In the clean pass no moment carries the mark, so `stand_soft_rows` always returns `None` and `stand_ok` ≡ bare `stand_alone_check`. |
| 3 | Do `lineup_ok` / `lineup_for` / the pin row agree? | **Yes.** All three route through the same `stand_soft_rows` predicate. `lineup_ok` and `lineup_for` use `stand_ok` (pass iff check passes *or* only soft rows fail). The pin inventory uses `stand_with_soft` (same predicate) and emits FLAGGED only when `soft_rows` is non-empty. |
| 4 | Is the prefix exact? | **Yes.** `STAND_SOFT_PREFIX = "The clip ({channel}) may not stand alone: "` matches the integrator's documented match string. The test `test_a_clip_left_out_only_by_the_opener_rule_seals_flagged_only_in_the_never_empty_pass` asserts the full rendered sentence byte-for-byte. |
| 5 | Are the tests adequate? | **Mostly.** Seven new tests cover the plain reason, every hard branch of `stand_soft_rows`, the end-to-end rig (clean vs. soft, topic-rule exclusion, hook exclusion, carried-mark pop, lineup acceptance/rejection, and the pin row's soft-only flagging). The two gaps noted above (P2 #2: no pin-row test for a hard failure in the soft pass; P2 #1: no fallback-format test) are the only missing cases. |

---

## Law compliance spot-check

- **LAW 20 / M2:** No gate threshold is changed. A failing stand_alone check is still a hard stop in the clean pass and in the soft pass when a hard condition (topic, hook, medley) is the cause. The soft path only *flags* (does not waive) the opener-rule failure. No reclassification of a failing gate as a false positive.
- **M12 FAIL CLOSED:** `stand_soft_rows` returns `None` (hard) on any missing or unexpected data (`m is None`, missing `opener`/`topic` sub-dict, missing `medley_names_bitcoin`). `stand_plain` returns the raw string rather than fabricating a pass. No path produces a pass from missing data.
- **L-d PROTECTED PREVIEW:** No change touches the preview reference, its selection locks, or its cut points.
- **LAW 22 (v2f byte-identical):** No renderer, compositor, or selector code is modified. The change is confined to the builder's admission logic and the pin's gate record.

---

P1_OR_WORSE: 0