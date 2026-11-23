# qwen3.8-27b (qwen/qwen3.8-27b) 79 s finish=stop usage in 7449 / out 6556 usd_reported=0.016196 usd~0.121 (upper-bound price)



# Code Audit — RULING 150 (pp-selectid)

## Findings

### [P2] RULING 150 flag can indirectly hard-stop via REVIEW_FLAGS_MAX

The new `VALUE_FLAG` is added to the `takeaway_value` row's `flags` list. The description confirms the unchanged `REVIEW_FLAGS_MAX = 3` (package_pin.py:55) "counts every flag." If a package already carries 3 flags from other gates (e.g., `runtime`, `hook_onset`, `graphics`), the RULING 150 flag becomes the 4th and trips the cap, producing a `gate_problems` entry that blocks the package. The ruling's intent is that a measured-but-not-clear-yes value verdict is *soft* (the line ships, flagged for review), yet the cap converts it into a hard stop. The ruling text does not exempt this flag from the cap, so the code is technically compliant, but the interaction defeats the softness in the common never-empty-pass scenario where other soft gates (runtime, hook_onset) are also flagged.

**Suggestion:** Either (a) document in the ruling that the RULING 150 flag counts toward the cap (accepting the risk), or (b) exclude `takeaway_value` flags from the `REVIEW_FLAGS_MAX` count, or (c) raise the cap to 4 for the never-empty pass. As written, a package that would otherwise ship with a flagged closing line can be rejected solely because the flag pushed the count to 4.

---

### [P3] Inconsistent access style in the inventory condition (line 38)

```python
if value.get("soft") and value.ok is not True else {}
```

`value.get("soft")` uses dict-style access; `value.ok` uses attribute access. Both work only because the runtime object supports both (the test passes, confirming this). The inconsistency is a readability hazard: a future reader may "fix" one to match the other and break the code, or may not realise the object is not a plain `dict`. The `_build` side stores it as `dict(val, soft=True)`, which *is* a plain dict — so if `inventory` receives that same dict, `value.ok` would raise `AttributeError`. The test passing implies `inventory` receives a wrapped object, but the diff does not show the wrapping. Worth a one-line comment or a uniform `value.get("ok")`.

---

### [P3] `val["ok"]` is a hard key access (KeyError on missing key)

In the `_build` write loop, `val["ok"]` is accessed directly (not `.get("ok")`). If the value-measurement backend returns a dict without an `"ok"` key (e.g., a partial failure that still sets `measured=True`), this raises `KeyError`. Under M12 (fail closed) the build would abort, which is the correct *outcome*, but the error message would be a bare `KeyError: 'ok'` rather than a descriptive "value verdict missing required field." A `val.get("ok")` with an explicit `if val.get("ok") is None: raise` (or log + reject) would make the failure self-documenting in the build log.

---

### [P3] `rec["value_soft"]["answers"]` silently drops keys absent from `val`

```python
"answers": {k: val.get(k) for k in ("adds", "no_restate", "missed", "short")}
```

If the measured verdict omits any of these four sub-fields (e.g., the backend only returned `adds` and `no_restate`), the record stores `None` for the missing ones. This is not a correctness bug (the line still ships, the flag is still correct), but the audit trail in `rec["value_soft"]` would show `{"adds": "yes", "no_restate": "no", "missed": None, "short": None}`, which a reviewer might misread as "the verdict said 'missed' is None" rather than "the field was not reported." A small sentinel or a note in the log line would disambiguate.

---

## Answers to the four requested checks

1. **Can the clean pass or an unmeasured verdict get a line through?** No. Clean pass: `soft` is `False`, so the RULING 150 branch is unreachable; the unchanged `if not val["ok"] and not val.get("soft")` fires and the line is lost. Unmeasured: `val.get("measured") is True` is `False`, same result. Both are covered by `test_the_clean_pass_never_takes_it` and `test_no_verdict_stays_hard`.

2. **Do fidelity, context, length and banned words stay HARD?** Yes. The `soft` flag is set only on the value-verdict dict. The subsequent paid gates (fidelity + context at package.py:4420, length, banned words) are separate checks that read the line text and the source independently; none of them consult `val["soft"]`. The log line and the ruling text both confirm this.

3. **Is the FLAGGED row's text the shipped closing line?** Yes. The inventory row's `text` field is `value.get("text")` (the takeaway text stored by the value measurement), and the flag string is `VALUE_FLAG.format(line=value.get("text"))` — the same source. The test asserts `row["text"] == TM.Rig.LINE` and the flag contains the same string.

4. **Any path where the never-empty pass seals a line with no value verdict at all?** No. The soft branch requires `val.get("measured") is True`. If the value gate never ran or returned an unmeasured result, `val["ok"]` is `False` (or the build fails under M12), and the line is lost via the unchanged hard path. There is no code path that sets `soft=True` without a measured verdict.

---

P1_OR_WORSE: 0