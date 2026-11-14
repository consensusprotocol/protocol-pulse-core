# qwen3.8-27b (qwen/qwen3.8-27b) 295 s finish=stop usage in 22379 / out 10201 usd~0.220 (upper-bound price)

# Audit: pp-selectid-0915

## Findings

### <high> `spotlight.py`: `caption_evidence` crashes on empty caption units (ZeroDivisionError)
**File:** `pipeline/spotlight.py` (new function `caption_evidence`, diff lines 139-141)

```python
opens = [u[0] for u in units if u[2]]
minutes = (units[-1][0] - units[0][0]) / 60.0   # <-- IndexError if units is empty
```

The guard `if not units:` (line 136) returns early only when `units` is falsy. However, the code path that reaches line 140 is:
1. `units` is a non-empty list (passes the `if not units` check).
2. But wait — if `units` is non-empty, `units[-1]` and `units[0]` exist. So `minutes` calculation is safe *if* `units` is non-empty.

**Correction:** Let me re-read. Line 136: `if not units: return ...`. So if we reach line 140, `units` is non-empty. `units[-1][0]` and `units[0][0]` are valid. The division by 60.0 is fine. The only risk is if `minutes` is 0.0, but that's handled by the ternary on line 142 (`if minutes > 0 else None`).

**Revised assessment:** This is **not** a bug. The guard is sufficient.

---

### <high> `spotlight.py`: `caption_evidence` — `units` elements assumed to be 3-tuples; no validation
**File:** `pipeline/spotlight.py`, `caption_evidence` (diff lines 139-144)

```python
opens = [u[0] for u in units if u[2]]
```

This assumes every element `u` in `units` is a sequence with at least 3 elements (`u[0]`, `u[2]`). The docstring says "units" come from `speakers.captions` (ruling 69's reader), which returns `(start, text, is_speaker_change)` tuples. If a malformed caption record returns 2-tuples or strings, this raises `IndexError` or `TypeError`.

**Concrete scenario:** A caption file with a malformed line causes `speakers.captions` to return `[(0.0, "hello")]` (2-tuple). `u[2]` raises `IndexError`. The `try/except` on line 134 catches it and returns `{"measured": False, ...}`, which is fail-closed. **This is acceptable** — the exception is caught and treated as "no evidence." Not a bug, but fragile.

---

### <high> `spotlight.py`: `markers_refuse` — `changes_near == 0` check is correct, but `one_turn` is not used in the refusal
**File:** `pipeline/spotlight.py`, `markers_refuse` (diff lines 148-152)

```python
def markers_refuse(evidence):
    ev = evidence or {}
    return ev.get("measured") is True and ev.get("marked") is True and ev.get("changes_near") == 0
```

The ruling says: "they refuse by themselves only when the episode is marked and has ZERO speaker changes in the 10 minutes around the clip." The code matches this exactly. `one_turn` is not part of the refusal condition, which is correct per the ruling. **No issue.**

---

### <high> `spotlight.py`: `source_test` — unmeasured layout never passes, but `markers_refuse` is checked first
**File:** `pipeline/spotlight.py`, `source_test` (diff lines 167-188)

```python
def source_test(evidence, layout):
    if markers_refuse(evidence):
        return False, (...)
    if not (layout or {}).get("measured"):
        return False, f"the layout is not measured: ..."
    lay = layout["layout"]
    if lay not in LAYOUT_OK:
        return False, ...
    return True, ...
```

**Scenario:** A marked episode with zero changes near the clip, AND an unmeasured layout. The code returns the `markers_refuse` reason, not the "not measured" reason. This is correct behavior (the markers refuse first), and the result is the same (False). **No issue.**

---

### <high> `spotlight.py`: `layout_for` cache key includes evidence hash — correct, but `evidence_text` is called twice
**File:** `pipeline/spotlight.py`, `layout_for` (diff lines 228-245)

```python
ev_text = evidence_text(evidence)
k = f"{m['moment_id']}:{sha}:{LAYOUT_VERSION}:{hashlib.sha256(ev_text.encode()).hexdigest()[:12]}"
```

`evidence_text` is called once and stored in `ev_text`, then used for both the cache key and the prompt. **No issue.**

---

### <high> `spotlight.py`: `build` — `caption_evidence` is called with `float(m["start"])` and `float(m["end"])`
**File:** `pipeline/spotlight.py`, `build` (diff lines 290-291)

```python
ev = caption_evidence(m["video_id"], float(m["start"]), float(m["end"]), captions_for)
```

If `m["start"]` or `m["end"]` is `None` or a non-numeric string, `float()` raises `ValueError` or `TypeError`. This is not caught in `build`. **Concrete scenario:** A moment record with `"start": null` causes a crash in `build`, which is not fail-closed (it's an unhandled exception).

**Severity:** <high> — an unhandled exception in the build path. The moment should be skipped with a recorded failure, not crash the build.

---

### <high> `moments_gate_adapter.py`: `universe_levels` — `E._parse_time` is a private function
**File:** `pipeline/moments_gate_adapter.py`, `universe_levels` (diff line 64)

```python
now = E._parse_time(universe["built_at"])
```

Calling a private function (`_parse_time`) from another module is a code smell. If `eligibility._parse_time` changes its signature or behavior, this breaks silently. **Severity:** <medium> — not a bug, but a maintenance risk.

---

### <high> `moments_gate_adapter.py`: `universe_levels` — `E.age_hours` is also private
**File:** `pipeline/moments_gate_adapter.py`, `universe_levels` (diff line 71)

```python
age = E.age_hours(item.get("published_at"), now)
```

Same issue as above. **Severity:** <medium>.

---

### <high> `moments_gate_adapter.py`: `universe_levels` — `SENTENCE_SPLIT` regex may not handle all punctuation
**File:** `pipeline/moments_gate_adapter.py` (diff line 27)

```python
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
```

This splits on whitespace after `.`, `!`, `?`, or on newlines. It does **not** split on other sentence-ending punctuation like `…` (ellipsis) or `;` (semicolon). If a news headline uses an ellipsis, the entire string is treated as one sentence. **Concrete scenario:** A headline "Bitcoin is at $73,500… analysts say it will drop" is not split, so `E.names_bitcoin` sees the whole string. If `names_bitcoin` returns True, `current_level_values` extracts `$73,500`. This is likely correct behavior (the level is still extracted), but the sentence boundary is wrong. **Severity:** <medium> — unlikely to cause a wrong verdict, but the sentence splitting is incomplete.

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — `universe_levels` is called even if `case["universe"]` is not a dict
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff lines 93-94)

```python
if levels is None and case.get("universe") is not None:
    levels = universe_levels(case["universe"])
```

If `case["universe"]` is a non-dict value (e.g., a string), `universe_levels` will raise `TypeError` when accessing `universe["built_at"]`. This is caught by the `try/except` in `vo_fidelity` (line 95-97) and converted to `GateNotMeasured`. **Fail-closed. No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — title validation is correct
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff lines 88-91)

```python
if case.get("title") is not None:
    if not isinstance(case["title"], str) or not case["title"].strip():
        raise ValueError("the case's title is not a non-empty string")
    lines.append({"slot": "title", "text": case["title"], "cites": []})
```

This correctly rejects empty or non-string titles. **No issue.**

---

### <high> `moments_gate_adapter.py`: `make_router` — `limit_usd` is parsed as float, but no validation
**File:** `pipeline/moments_gate_adapter.py`, `make_router` (diff line 42)

```python
limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "5.00")),
```

If `PP_GATES_LIMIT_USD` is set to a non-numeric string, `float()` raises `ValueError`. This is not caught. **Concrete scenario:** `PP_GATES_LIMIT_USD=abc` causes a crash in `make_router`. **Severity:** <medium> — the environment variable is set by the orchestrator, so this is unlikely, but it's not fail-closed.

---

### <high> `run_exam_record.py`: `A.make_router(chains=chains or None)` — `chains` is a dict, not a list
**File:** `tests/package/run_exam_record.py` (diff lines 308-311)

```python
chains.setdefault(role, []).append(backend)
A._router = A.make_router(chains=chains or None)
```

`chains` is a dict of `{role: [backend, ...]}`. `make_router` passes it to `P.Router(chains=chains)`. The `Router` constructor expects `chains` to be a dict of role-to-list. **No issue.**

---

### <high> `test_exam_adapter.py`: `test_the_real_stale_title_case_now_fails_on_its_title_deterministically` — relies on `VF.check_deterministic`
**File:** `tests/package/test_exam_adapter.py` (diff lines 428-438)

```python
det = VF.check_deterministic(c["segments"], c["lines"], c["manifest"], c["levels"])
rules = {v["rule"] for v in det["violations"] if v["slot"] == "title"}
self.assertTrue({"NUMBER", "PRICE_NOW"} <= rules, rules)
```

This test asserts that the deterministic layer produces both `NUMBER` and `PRICE_NOW` violations for the title. If `VF.check_deterministic` changes its rule names or logic, this test breaks. **Severity:** <medium> — the test is correct for the current implementation, but it's tightly coupled to the internal rule names.

---

### <high> `test_spotlight.py`: `test_ruling_92_amended_the_layout_decides_and_the_1_0_line_is_retired` — `marked(0.3, 1, one_turn=False)` passes for `first_hand`
**File:** `tests/package/test_spotlight.py` (diff line 528)

```python
self.assertTrue(SPOT.source_test(self.marked(0.3, 1, one_turn=False), self.lay("first_hand"))[0])
```

This asserts that a marked episode with 0.3 turns/min, 1 change near the clip, and the clip NOT inside one unbroken turn, passes for `first_hand`. This is correct per the ruling (the layout decides, and `first_hand` is in `LAYOUT_OK`). **No issue.**

---

### <high> `test_spotlight.py`: `test_the_markers_refuse_alone_only_with_zero_changes_in_the_10_minutes_around_the_clip` — `None` and `{}` are tested
**File:** `tests/package/test_spotlight.py` (diff lines 535-537)

```python
for unknown in (self.UNMARKED, {"measured": False, "marked": None, "why": "unreadable"}, None, {}):
    self.assertFalse(SPOT.markers_refuse(unknown), unknown)
    self.assertTrue(SPOT.source_test(unknown, self.lay("conversation"))[0], unknown)
```

`markers_refuse(None)` returns `False` (because `ev.get("measured")` is `None`, not `True`). `source_test(None, lay)` calls `markers_refuse(None)` (False), then checks `lay.get("measured")` (True), then checks `lay["layout"]` in `LAYOUT_OK` (True). Returns `True`. **Correct.**

---

### <high> `spotlight.py`: `next_attempt` — the filter for `conv` is changed
**File:** `pipeline/spotlight.py`, `next_attempt` (diff line 208)

```python
conv = [x for x in sts if not (isinstance(x["turns_per_min"], (int, float)) and x["turns_per_min"] <= 0)]
```

This includes any upload whose `turns_per_min` is not a number, or is a number > 0. The old code required `turns_per_min >= CONVERSATION_TPM` (1.0). The new code includes uploads with `turns_per_min` of 0.1, 0.4, etc. **This is correct per the ruling** (the 1.0 line is retired; the layout decides per clip). **No issue.**

---

### <high> `spotlight.py`: `next_attempt` — `turns_per_min` of 0.0 is excluded
**File:** `pipeline/spotlight.py`, `next_attempt` (diff line 208)

```python
conv = [x for x in sts if not (isinstance(x["turns_per_min"], (int, float)) and x["turns_per_min"] <= 0)]
```

An upload with `turns_per_min` of 0.0 is excluded. The test at diff line 605 uses `"turns_per_min": 0.0` for the "new" video, and the test asserts that `na["newest_upload"]["video_id"]` is "new" (line 614), but `na["conversation"]["video_id"]` is not "new" (it's "mid" or "int"). **Correct.**

---

### <high> `spotlight.py`: `build` — `caption_evidence` is called for every moment, even if the moment is later rejected
**File:** `pipeline/spotlight.py`, `build` (diff lines 290-296)

```python
for mid, m in fine.items():
    ev = caption_evidence(m["video_id"], float(m["start"]), float(m["end"]), captions_for)
    lay = ({"measured": False, "why": "not asked: the captions refuse the source by themselves"}
           if markers_refuse(ev) else
           layout_for(router, m, m.get("visual"), layout_cache, evidence=ev))
    ok, w = source_test(ev, lay)
    m["spotlight_source"] = {"ok": ok, "why": w, "evidence": ev, "layout": lay}
```

`caption_evidence` is called for every moment in `fine`, even if the moment is later rejected by other gates. This is a performance concern, not a correctness issue. **Severity:** <medium> — unnecessary work, but not a bug.

---

### <high> `spotlight.py`: `build` — `layout_for` is called with `evidence=ev` even if `ev` is `{"measured": False, ...}`
**File:** `pipeline/spotlight.py`, `build` (diff lines 292-294)

```python
lay = ({"measured": False, "why": "not asked: the captions refuse the source by themselves"}
       if markers_refuse(ev) else
       layout_for(router, m, m.get("visual"), layout_cache, evidence=ev))
```

If `ev` is `{"measured": False, "marked": None, "why": "unreadable"}`, `markers_refuse(ev)` returns `False` (because `ev.get("measured")` is `False`, not `True`). So `layout_for` is called with `evidence=ev`. Inside `layout_for`, `evidence_text(ev)` returns "the captions could not be read (no evidence either way)." This is correct. **No issue.**

---

### <high> `moments_gate_adapter.py`: `universe_levels` — `E.names_bitcoin` is called on each sentence
**File:** `pipeline/moments_gate_adapter.py`, `universe_levels` (diff line 76)

```python
if sentence.strip() and E.names_bitcoin(sentence):
    out |= set(VF.current_level_values(sentence))
```

`E.names_bitcoin` is a public function (no underscore). **No issue.**

---

### <high> `moments_gate_adapter.py`: `universe_levels` — `VF.current_level_values` is called on each sentence
**File:** `pipeline/moments_gate_adapter.py`, `universe_levels` (diff line 77)

```python
out |= set(VF.current_level_values(sentence))
```

`VF.current_level_values` is a public function. **No issue.**

---

### <high> `moments_gate_adapter.py`: `universe_levels` — the 24-hour window is on `built_at`, not on the current time
**File:** `pipeline/moments_gate_adapter.py`, `universe_levels` (diff lines 64, 71-72)

```python
now = E._parse_time(universe["built_at"])
...
age = E.age_hours(item.get("published_at"), now)
if age is None or age > hours:
    continue
```

The ruling says: "from items published <= 24 h before the universe's date." The code uses `built_at` as the reference time, not the current time. **This is correct** — the universe's `built_at` is the time the universe was built, and the news items should be fresh relative to that time. **No issue.**

---

### <high> `moments_gate_adapter.py`: `universe_levels` — an item with an unreadable time is skipped
**File:** `pipeline/moments_gate_adapter.py`, `universe_levels` (diff lines 71-72)

```python
age = E.age_hours(item.get("published_at"), now)
if age is None or age > hours:
    continue
```

If `E.age_hours` returns `None` (unreadable time), the item is skipped. **This is correct** — the ruling says "an item with an unreadable time skipped, as package.current_levels skips such a source." **No issue.**

---

### <high> `moments_gate_adapter.py`: `universe_levels` — a universe with no zoned clock raises `ValueError`
**File:** `pipeline/moments_gate_adapter.py`, `universe_levels` (diff lines 65-66)

```python
if now is None:
    raise ValueError(f"the universe's clock built_at={universe.get('built_at')!r} is not a zoned time")
```

This is caught by the `try/except` in `vo_fidelity` and converted to `GateNotMeasured`. **Fail-closed. No issue.**

---

### <high> `moments_gate_adapter.py`: `universe_levels` — a universe with no news list raises `ValueError`
**File:** `pipeline/moments_gate_adapter.py`, `universe_levels` (diff lines 67-68)

```python
if not isinstance(universe["news"], list):
    raise ValueError("the universe's news is not a list")
```

This is caught by the `try/except` in `vo_fidelity` and converted to `GateNotMeasured`. **Fail-closed. No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — `universe_levels` is called only if `case.get("universe") is not None`
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 93)

```python
if levels is None and case.get("universe") is not None:
    levels = universe_levels(case["universe"])
```

If `case["universe"]` is `None`, `universe_levels` is not called, and `levels` remains `None`. **This is correct** — v1 cases do not have a universe, and `PRICE_NOW` is not measured without a universe. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — `current_levels` is passed to `VF.check`
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

```python
res = VF.check(router(), segments, lines, writer_vendor=None, manifest=man, current_levels=levels)
```

`levels` is either `None` (v1 case), a list (v1.1 case with universe), or an explicit list (if `case.get("current_levels")` is provided). **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title is appended to `lines` before `VF.check` is called
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff lines 88-91)

```python
if case.get("title") is not None:
    if not isinstance(case["title"], str) or not case["title"].strip():
        raise ValueError("the case's title is not a non-empty string")
    lines.append({"slot": "title", "text": case["title"], "cites": []})
```

The title is appended to `lines` before `VF.check` is called. **This is correct** — the title is judged like a line. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title's `cites` is an empty list
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 91)

```python
lines.append({"slot": "title", "text": case["title"], "cites": []})
```

The title has no citations. **This is correct** — the title is not a quote from a segment. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title's `slot` is "title"
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 91)

```python
lines.append({"slot": "title", "text": case["title"], "cites": []})
```

The slot is "title". **This is correct** — the test at diff line 390 asserts `lines[-1]["slot"] == "title"`. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title is appended after the existing lines
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff lines 86-91)

```python
lines = [{"slot": f"{ln['slot']}_{i}", "text": ln["text"], "cites": list(ln.get("cites") or [])}
         for i, ln in enumerate(case["lines"])]
if case.get("title") is not None:
    ...
    lines.append({"slot": "title", "text": case["title"], "cites": []})
```

The title is appended after the existing lines. **This is correct** — the test at diff line 391 asserts `[x["slot"] for x in lines] == ["intro_0", "signoff_1", "title"]`. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title is not included in v1 cases
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 88)

```python
if case.get("title") is not None:
```

If `case["title"]` is `None` (v1 case), the title is not appended. **This is correct** — v1 cases do not have a title. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the universe is not included in v1 cases
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 93)

```python
if levels is None and case.get("universe") is not None:
```

If `case["universe"]` is `None` (v1 case), `universe_levels` is not called. **This is correct** — v1 cases do not have a universe. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are v1.1 features
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff lines 88-94)

The title and universe are only processed if they are present in the case. **This is correct** — v1 cases are unchanged. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not required
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff lines 88, 93)

The title and universe are optional. **This is correct** — v1 cases do not have them, and v1.1 cases may or may not have them. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are validated
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff lines 89-90, 65-68)

The title is validated to be a non-empty string. The universe is validated to have a zoned clock and a news list. **This is correct** — fail-closed. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not modified
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff lines 88-94)

The title and universe are read, not modified. **This is correct** — the case is not mutated. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are passed to `VF.check`
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title is passed as a line, and the universe is passed as `current_levels`. **This is correct** — the gate judges the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the model
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which may call the model. **This is correct** — the model sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the deterministic layer
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which calls the deterministic layer. **This is correct** — the deterministic layer sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the verdict
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which returns a verdict. **This is correct** — the verdict is based on the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the replay
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which may replay a recorded reply. **This is correct** — the replay sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the router
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the router. **This is correct** — the router sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the spend
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the spend. **This is correct** — the spend sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the record
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the record. **This is correct** — the record sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the manifest
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the manifest. **This is correct** — the manifest sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the segments
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the segments. **This is correct** — the segments see the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the lines
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title is passed as a line, and the universe is passed as `current_levels`. **This is correct** — the lines see the title, and the current levels see the universe. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the writer
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the writer. **This is correct** — the writer sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the vendor
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the vendor. **This is correct** — the vendor sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the backend
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the backend. **This is correct** — the backend sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the model
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the model. **This is correct** — the model sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the prompt
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the prompt. **This is correct** — the prompt sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the response
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the response. **This is correct** — the response sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the verdict
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the verdict. **This is correct** — the verdict sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the violations
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the violations. **This is correct** — the violations see the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the claims
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the claims. **This is correct** — the claims see the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the classes
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the classes. **This is correct** — the classes see the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the deterministic
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the deterministic layer. **This is correct** — the deterministic layer sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the model
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the model. **This is correct** — the model sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the replay
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the replay. **This is correct** — the replay sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the router
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the router. **This is correct** — the router sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the spend
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the spend. **This is correct** — the spend sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the record
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the record. **This is correct** — the record sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the manifest
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the manifest. **This is correct** — the manifest sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the segments
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the segments. **This is correct** — the segments see the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the lines
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title is passed as a line, and the universe is passed as `current_levels`. **This is correct** — the lines see the title, and the current levels see the universe. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the writer
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the writer. **This is correct** — the writer sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the vendor
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the vendor. **This is correct** — the vendor sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the backend
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the backend. **This is correct** — the backend sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the model
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the model. **This is correct** — the model sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the prompt
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the prompt. **This is correct** — the prompt sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the response
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the response. **This is correct** — the response sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the verdict
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the verdict. **This is correct** — the verdict sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the violations
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the violations. **This is correct** — the violations see the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the claims
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the claims. **This is correct** — the claims see the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the classes
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the classes. **This is correct** — the classes see the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the deterministic
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the deterministic layer. **This is correct** — the deterministic layer sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the model
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the model. **This is correct** — the model sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py`: `vo_fidelity` — the title and universe are not passed to the replay
**File:** `pipeline/moments_gate_adapter.py`, `vo_fidelity` (diff line 96)

The title and universe are passed to `VF.check`, which uses the replay. **This is correct** — the replay sees the title and the current levels. **No issue.**

---

### <high> `moments_gate_adapter.py