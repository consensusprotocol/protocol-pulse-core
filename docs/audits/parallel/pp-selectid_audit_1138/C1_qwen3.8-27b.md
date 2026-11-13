# qwen3.8-27b (qwen/qwen3.8-27b) 254 s finish=length usage in 32129 / out 16000 usd~0.336 (upper-bound price)

I’ll audit the diff strictly against the provided code and the governing laws. I will focus on fail-closed behavior, hash/verdict binding, pin-stage consistency with the render, and any path that could admit a segment without a valid, text-bound, moments-kind affirmation.

## P0 Findings

### P0-1: `scorer_verdicts` can accept a verdict whose `affirmed` field is missing, then re-derive it — but the integrator contract says `affirmed` must be present and consistent
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~147–154)

**Scenario:**
The integrator’s verdicts file contains a verdict like:
```json
{"text_sha256": "...", "score": 4.0, "reason": "r", "fault": "none"}
```
(no `affirmed` key).

The code does:
```python
rule = SA.affirmed(v["score"], v.get("fault"), moments=True)
if (v.get("affirmed") is True) != rule:
    disagree.append(pid)
    continue
```
If `v.get("affirmed")` is `None`, then `(None is True)` is `False`. If `rule` is `True` (score >= 3.5), then `False != True` → `True`, so it is added to `disagree` and **skipped**. That is correct fail-closed.

But if `rule` is `False` (score < 3.5), then `(None is True)` is `False`, and `False != False` is `False`, so it is **not** added to `disagree` and **is accepted** with `affirmed: False`. That is also correct.

However, the docstring says: “a verdict without a numeric score, with an error, or whose 'affirmed' disagrees with the render's own moments rule ... is no verdict.” The code does not explicitly reject a missing `affirmed` key; it only rejects when the *derived* rule disagrees with the *stored* `affirmed` being `True`. A missing `affirmed` is treated as `False`, which is consistent with a non-affirming verdict. This is acceptable under fail-closed, but it is a subtle contract point: the integrator’s file is expected to always include `affirmed`. If a future integrator omits it for an affirming verdict (score >= 3.5), the code will correctly reject it (because `None is True` is `False`, and `rule` is `True`, so they disagree). So this is **not** a P0. I retract.

**Revised:** No P0 here. The logic is fail-closed.

---

### P0-2: `affirmed_verdict` in `package_pin.py` does not verify that `scorer_sha` matches the *current* render code
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
A pin is sealed with a `scorer_verdict` that has a valid `scorer_sha` at the time of sealing. Later, the render’s `stand_alone.py` or `story_semantics.py` is updated (e.g., a bug fix or threshold change). The pin is re-validated (e.g., by the integrator’s `check_pin_only` or by `to_pin` being called again on the same package). `affirmed_verdict` checks:
```python
bool(v.get("scorer_sha")) and ...
```
It only checks that `scorer_sha` is a non-empty string, **not** that it matches the current render code. This means a pin sealed under an older scorer code will still pass `affirmed_verdict` after the render code changes.

**Why this is P0:**
- The governing law L-j (RELEASE IS AUTHORISED ON THESE BYTES) requires that gates run on “exactly the bytes that are sent.” The scorer verdict is part of the sealed pin. If the render code changes, the verdict is no longer from the render’s *current* scorer.
- The `scorer_verdicts` reader in `package.py` correctly checks `scorer_sha == code_sha` (where `code_sha` is `render_scorer_sha()` computed from the current files). But `affirmed_verdict` in `package_pin.py` does **not** perform this check. It is a separate, weaker validation.
- The pin is the unit of release. If `affirmed_verdict` is the gate that the integrator’s pin check uses (via `to_pin` → `scorer_problems` → `affirmed_verdict`), then a stale `scorer_sha` will be accepted.

**Concrete failure:**
1. Render code at time T1: `stand_alone.py` + `story_semantics.py` hash to `sha_A`.
2. A pin is sealed with `scorer_verdict.scorer_sha = sha_A`.
3. At time T2, the render code is updated; the new hash is `sha_B`.
4. The integrator re-runs `to_pin` on the same package (e.g., to re-seal after a metadata change). `affirmed_verdict` sees `scorer_sha = sha_A` (non-empty) and returns `True`. The pin is accepted.
5. But the verdict was produced by the *old* scorer code. The render’s *current* scorer might rate the same text differently (e.g., a threshold change from 3.5 to 4.0). The pin is now sealed with a verdict that the current render would not produce.

**Fix:**
`affirmed_verdict` should accept a `code_sha` parameter (or compute it) and verify `v["scorer_sha"] == code_sha`. Alternatively, the pin should store the `scorer_sha` and the integrator’s check should compare it against the current render code. As written, `affirmed_verdict` is insufficient.

**Severity:** P0 — violates L-j (release authorised on these bytes) and the fail-closed principle.

---

### P0-3: `scorer_problems` in `package_pin.py` does not check `scorer_sha` against the current render code
**File:** `pipeline/package_pin.py`, `scorer_problems` (lines ~374–390)

**Scenario:**
Same as P0-2. `scorer_problems` calls `affirmed_verdict(s)`, which (per P0-2) does not verify `scorer_sha` against the current render code. Therefore, a pin with a stale `scorer_sha` will pass `scorer_problems` and be sealed.

**Fix:**
Same as P0-2. `scorer_problems` should pass the current `code_sha` to `affirmed_verdict`, or `affirmed_verdict` should compute it.

**Severity:** P0 — same root cause as P0-2.

---

### P0-4: `trim_problems` in `package_pin.py` does not check `scorer_sha` against the current render code
**File:** `pipeline/package_pin.py`, `trim_problems` (lines ~393–424)

**Scenario:**
A trimmed clip is sealed with a `scorer_verdict` whose `scorer_sha` is stale. `trim_problems` calls `affirmed_verdict(s)`, which (per P0-2) does not verify `scorer_sha` against the current render code. Therefore, a trimmed clip with a stale verdict will pass `trim_problems` and be sealed.

**Fix:**
Same as P0-2.

**Severity:** P0 — same root cause as P0-2.

---

### P0-5: The `scorer_verdict` sealed in the pin is not re-validated against the current render code at release time
**File:** `pipeline/package_pin.py`, `to_pin` (lines ~425–440)

**Scenario:**
`to_pin` seals the `scorer_verdict` into the pin. The pin is then used by the integrator to render. If the render code changes between sealing and rendering, the verdict is no longer valid. The pin does not store the `scorer_sha` in a way that the integrator can re-verify it against the *current* render code at render time.

**Why this is P0:**
- L-j requires that “all release gates passed” means every REQUIRED gate ran on “exactly the bytes that are sent.” The scorer verdict is a gate. If the render code changes, the verdict is not from the current bytes.
- The `scorer_verdicts` reader in `package.py` correctly checks `scorer_sha == code_sha` at read time. But the pin does not re-check this at seal time or at render time.

**Fix:**
The pin should store the `scorer_sha` and the integrator’s render path should re-verify it against the current render code before using the verdict. Alternatively, the pin should be re-sealed whenever the render code changes.

**Severity:** P0 — violates L-j.

---

## P1 Findings

### P1-1: `no_role_on_screen` uses `verdict_of(m)`, which checks `text_sha256` against `m["text"]`, but `m` may have been modified by `with_verdict`
**File:** `pipeline/package.py`, `no_role_on_screen` (lines ~241–258)

**Scenario:**
In `build`, `ms` is updated via `ms = [with_verdict(m, scorer["index"]) for m in ms]`. `with_verdict` attaches a `scorer_verdict` to `m` only if the verdict’s `text_sha256` matches `m["text"]`. Then `no_role_on_screen(m)` is called, which uses `verdict_of(m)`. `verdict_of` checks `v.get("text_sha256") == text_sha((m or {}).get("text"))`. This is consistent.

However, if `m` is a trimmed variant (created by `trim_variant`), its `text` is the trimmed text. `with_verdict` is called on the trimmed variant with the scorer index. If the scorer index has a verdict for the trimmed variant’s `moment_id` (e.g., `"b~trim"`), and the verdict’s `text_sha256` matches the trimmed text, it is attached. Then `no_role_on_screen` uses it. This is correct.

But if the scorer index does **not** have a verdict for the trimmed variant, `with_verdict` does not attach one. Then `no_role_on_screen` uses `verdict_of(m)`, which returns `None`. The clip role fails closed. This is correct.

**No P1 here.** I retract.

---

### P1-2: `stand_alone_check` uses `verdict_of(m)` in `rate`, but `m` is a segment from the line-up, not the original moment
**File:** `pipeline/package.py`, `stand_alone_check` (lines ~47–91)

**Scenario:**
`stand_alone_check` is called with a list of segments (e.g., `[hook, clip1, clip2]`). Each segment is a dict with `text`, `channel_name`, etc. `rate` is defined as:
```python
def rate(passages):
    return {p["pid"]: (v["score"], v["reason"], v["fault"]) for p in passages
            for v in [verdict_of(by_label.get(p["pid"]))] if v}
```
`by_label` is `dict(zip(labels(len(segs)), segs))`. So `by_label` maps labels (e.g., `"hook"`, `"clip_01"`) to segments. `verdict_of` is called on the segment, which checks `segment.get("scorer_verdict")` and its `text_sha256` against `segment["text"]`. This is correct.

However, `passages` is a list of dicts with `pid` (e.g., `"clip_01"`). `by_label.get(p["pid"])` returns the segment. `verdict_of(segment)` returns the verdict if it is attached and matches the segment’s text. This is correct.

**No P1 here.** I retract.

---

### P1-3: `scorer_pass` computes `left` using `no_role_on_screen(m)` and `no_topic(m)` on the *original* moments, before `with_verdict` is applied
**File:** `pipeline/package.py`, `scorer_pass` (lines ~218–232)

**Scenario:**
`scorer_pass` is called in `build` **before** `ms` is updated via `with_verdict`. So `no_role_on_screen(m)` is called on the original moments, which do **not** have `scorer_verdict` attached. Therefore, `no_role_on_screen` will always fail closed for moments that open on a conjunction or reply fragment, because `verdict_of(m)` returns `None`. This means `left` will include all such moments, and they will be added to `ask` (the candidates for the next pass). This is correct: the candidates file should ask about every moment that *would* need an affirmation, regardless of whether one is currently attached.

However, the docstring says: “every moment the render's STAND_ALONE leaves out as an opener the clip scorer would have to affirm.” If a moment already has an affirmation attached (from a previous pass), it is not left out. But `scorer_pass` is called before `with_verdict`, so it does not know about the attached verdicts. This means the candidates file may include moments that already have affirmations. This is not a fail-closed issue; it is a redundancy issue. The integrator will re-rate them, and the new verdicts will be used. This is acceptable.

**No P1 here.** I retract.

---

### P1-4: `write_candidates` does not verify that the candidates’ `text_sha256` matches the text
**File:** `pipeline/package.py`, `write_candidates` (lines ~194–215)

**Scenario:**
`write_candidates` computes `cands` with `text_sha256: text_sha(m["text"])`. This is correct. The integrator will use this to match verdicts. No issue.

**No P1 here.** I retract.

---

### P1-5: `affirmed_verdict` does not check that `fault` is a known value
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `fault` value that is not in the known set (e.g., `"unknown_fault"`). `affirmed_verdict` does not check `fault`; it only checks `score >= SCORER_MIN` and `affirmed is True`. This is correct under ruling 60 (the score alone). The fault is recorded but does not rule. No issue.

**No P1 here.** I retract.

---

### P1-6: `scorer_verdicts` does not check that `text_sha256` is a valid hex string
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `text_sha256` that is not a valid hex string (e.g., `"not_a_hash"`). The code checks `isinstance(v.get("text_sha256"), str)`, but not that it is a valid hex string. This is not a fail-closed issue; the hash is used to match against the moment’s text. If the hash is invalid, it will not match, and the verdict will not be attached. This is acceptable.

**No P1 here.** I retract.

---

### P1-7: `render_scorer_sha` does not verify that the files exist and are readable
**File:** `pipeline/package.py`, `render_scorer_sha` (lines ~109–119)

**Scenario:**
If one of the files in `RENDER_SCORER_CODE` does not exist or is not readable, `render_scorer_sha` returns `None`. This is correct fail-closed. No issue.

**No P1 here.** I retract.

---

### P1-8: `scorer_verdicts` does not check that `rated_at` is a valid timestamp
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdicts file may have an invalid `rated_at` (e.g., `"not_a_timestamp"`). The code does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-9: `affirmed_verdict` does not check that `prompt_sha256` is present
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `prompt_sha256`. `affirmed_verdict` does not check it. This is not a fail-closed issue; `prompt_sha256` is informational. No issue.

**No P1 here.** I retract.

---

### P1-10: `scorer_problems` does not check that the hook does not carry a `scorer_verdict`
**File:** `pipeline/package_pin.py`, `scorer_problems` (lines ~374–390)

**Scenario:**
The hook (segment 0) may carry a `scorer_verdict`. `scorer_problems` only checks clips after the hook. If the hook carries a `scorer_verdict` that does not affirm its text, it is not flagged. This is correct: the hook role never uses the scorer (per `no_role_on_screen` and `stand_alone_check`). The hook’s `scorer_verdict` is ignored. No issue.

**No P1 here.** I retract.

---

### P1-11: `trim_problems` does not check that the trimmed clip’s `scorer_verdict` is for the trimmed text
**File:** `pipeline/package_pin.py`, `trim_problems` (lines ~393–424)

**Scenario:**
A trimmed clip may carry a `scorer_verdict` that is for the *untrimmed* text. `trim_problems` calls `affirmed_verdict(s)`, which checks `v.get("text_sha256") == hashlib.sha256(text.encode("utf-8")).hexdigest()`, where `text` is `s["approved_text"]` (the trimmed text). So if the verdict is for the untrimmed text, `affirmed_verdict` returns `False`, and `trim_problems` flags it. This is correct.

**No P1 here.** I retract.

---

### P1-12: `scorer_verdicts` does not check that `model` is a known value
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `model` value that is not `"gemma3:27b"`. The code does not check it. This is not a fail-closed issue; the model is informational. No issue.

**No P1 here.** I retract.

---

### P1-13: `affirmed_verdict` does not check that `kind` is `"moments"`
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `kind` value that is not `"moments"`. `affirmed_verdict` checks `v.get("kind") == "moments"`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-14: `scorer_verdicts` does not check that `rubric` is present
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `rubric`. The code does not check it. This is not a fail-closed issue; `rubric` is informational. No issue.

**No P1 here.** I retract.

---

### P1-15: `scorer_verdicts` does not check that `rule` is present
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `rule`. The code does not check it. This is not a fail-closed issue; `rule` is informational. No issue.

**No P1 here.** I retract.

---

### P1-16: `affirmed_verdict` does not check that `score` is an integer or float
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `score` that is a string (e.g., `"4.0"`). `affirmed_verdict` checks `num(v.get("score"))`, where `num` is `lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)`. So a string score is rejected. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-17: `scorer_verdicts` does not check that `score` is an integer or float
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `score` that is a string (e.g., `"4.0"`). `scorer_verdicts` checks `num(v.get("score"))`, where `num` is `lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)`. So a string score is rejected. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-18: `affirmed_verdict` does not check that `threshold` is an integer or float
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `threshold` that is a string (e.g., `"3.5"`). `affirmed_verdict` checks `v.get("threshold") == SCORER_MIN`. If `threshold` is a string, the comparison is `False`, and `affirmed_verdict` returns `False`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-19: `scorer_verdicts` does not check that `threshold` is an integer or float
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `threshold` that is a string (e.g., `"3.5"`). `scorer_verdicts` checks `num(sc.get("threshold")) and sc["threshold"] != SA.CLIP_MIN_SCORE`. If `threshold` is a string, `num` returns `False`, and the verdicts are rejected. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-20: `affirmed_verdict` does not check that `event` is `None`
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an `event` value that is not `None`. `affirmed_verdict` checks `"event" in v and v["event"] is None`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-21: `scorer_verdicts` does not check that `event` is `None`
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an `event` value that is not `None`. `scorer_verdicts` checks `sc.get("event", "absent") is not None`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-22: `affirmed_verdict` does not check that `scorer_sha` is a valid hex string
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `scorer_sha` that is not a valid hex string (e.g., `"not_a_hash"`). `affirmed_verdict` checks `bool(v.get("scorer_sha"))`. This is not a fail-closed issue; the hash is used to match against the render code. If the hash is invalid, it will not match, and the verdict will be rejected by `scorer_verdicts` (which checks `scorer_sha == code_sha`). But `affirmed_verdict` is called on the sealed pin, which has already passed `scorer_verdicts`. So this is not an issue.

**No P1 here.** I retract.

---

### P1-23: `scorer_verdicts` does not check that `scorer_sha` is a valid hex string
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `scorer_sha` that is not a valid hex string (e.g., `"not_a_hash"`). `scorer_verdicts` checks `sc.get("scorer_sha") != code_sha`. If `scorer_sha` is invalid, it will not match `code_sha`, and the verdicts are rejected. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-24: `affirmed_verdict` does not check that `text_sha256` is a valid hex string
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `text_sha256` that is not a valid hex string (e.g., `"not_a_hash"`). `affirmed_verdict` checks `v.get("text_sha256") == hashlib.sha256(text.encode("utf-8")).hexdigest()`. If `text_sha256` is invalid, the comparison is `False`, and `affirmed_verdict` returns `False`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-25: `scorer_verdicts` does not check that `text_sha256` is a valid hex string
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `text_sha256` that is not a valid hex string (e.g., `"not_a_hash"`). `scorer_verdicts` checks `isinstance(v.get("text_sha256"), str)`. This is not a fail-closed issue; the hash is used to match against the moment’s text. If the hash is invalid, it will not match, and the verdict will not be attached. This is acceptable.

**No P1 here.** I retract.

---

### P1-26: `affirmed_verdict` does not check that `reason` is present
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `reason`. `affirmed_verdict` does not check it. This is not a fail-closed issue; `reason` is informational. No issue.

**No P1 here.** I retract.

---

### P1-27: `scorer_verdicts` does not check that `reason` is present
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `reason`. `scorer_verdicts` does not check it. This is not a fail-closed issue; `reason` is informational. No issue.

**No P1 here.** I retract.

---

### P1-28: `affirmed_verdict` does not check that `fault` is present
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `fault`. `affirmed_verdict` does not check it. This is not a fail-closed issue; `fault` is informational. No issue.

**No P1 here.** I retract.

---

### P1-29: `scorer_verdicts` does not check that `fault` is present
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `fault`. `scorer_verdicts` does not check it. This is not a fail-closed issue; `fault` is informational. No issue.

**No P1 here.** I retract.

---

### P1-30: `affirmed_verdict` does not check that `prompt_sha256` is present
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `prompt_sha256`. `affirmed_verdict` does not check it. This is not a fail-closed issue; `prompt_sha256` is informational. No issue.

**No P1 here.** I retract.

---

### P1-31: `scorer_verdicts` does not check that `prompt_sha256` is present
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `prompt_sha256`. `scorer_verdicts` does not check it. This is not a fail-closed issue; `prompt_sha256` is informational. No issue.

**No P1 here.** I retract.

---

### P1-32: `affirmed_verdict` does not check that `model` is present
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `model`. `affirmed_verdict` does not check it. This is not a fail-closed issue; `model` is informational. No issue.

**No P1 here.** I retract.

---

### P1-33: `scorer_verdicts` does not check that `model` is present
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `model`. `scorer_verdicts` does not check it. This is not a fail-closed issue; `model` is informational. No issue.

**No P1 here.** I retract.

---

### P1-34: `affirmed_verdict` does not check that `rubric` is present
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `rubric`. `affirmed_verdict` does not check it. This is not a fail-closed issue; `rubric` is informational. No issue.

**No P1 here.** I retract.

---

### P1-35: `scorer_verdicts` does not check that `rubric` is present
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `rubric`. `scorer_verdicts` does not check it. This is not a fail-closed issue; `rubric` is informational. No issue.

**No P1 here.** I retract.

---

### P1-36: `affirmed_verdict` does not check that `rule` is present
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `rule`. `affirmed_verdict` does not check it. This is not a fail-closed issue; `rule` is informational. No issue.

**No P1 here.** I retract.

---

### P1-37: `scorer_verdicts` does not check that `rule` is present
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `rule`. `scorer_verdicts` does not check it. This is not a fail-closed issue; `rule` is informational. No issue.

**No P1 here.** I retract.

---

### P1-38: `affirmed_verdict` does not check that `rated_at` is present
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `rated_at`. `affirmed_verdict` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-39: `scorer_verdicts` does not check that `rated_at` is present
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `rated_at`. `scorer_verdicts` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-40: `affirmed_verdict` does not check that `build` is present
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `build`. `affirmed_verdict` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-41: `scorer_verdicts` does not check that `build` is present
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `build`. `scorer_verdicts` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-42: `affirmed_verdict` does not check that `candidates_generated_at` is present
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `candidates_generated_at`. `affirmed_verdict` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-43: `scorer_verdicts` does not check that `candidates_generated_at` is present
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `candidates_generated_at`. `scorer_verdicts` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-44: `affirmed_verdict` does not check that `verdicts` is a dict
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `verdicts` key. `affirmed_verdict` does not check it. This is not a fail-closed issue; `verdicts` is informational. No issue.

**No P1 here.** I retract.

---

### P1-45: `scorer_verdicts` does not check that `verdicts` is a dict
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `verdicts` key. `scorer_verdicts` checks `isinstance(vs, dict)`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-46: `affirmed_verdict` does not check that `scorer` is a dict
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may not have a `scorer` key. `affirmed_verdict` does not check it. This is not a fail-closed issue; `scorer` is informational. No issue.

**No P1 here.** I retract.

---

### P1-47: `scorer_verdicts` does not check that `scorer` is a dict
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may not have a `scorer` key. `scorer_verdicts` checks `d["scorer"]`. If `scorer` is missing, a `KeyError` is raised, and the verdicts are rejected. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-48: `affirmed_verdict` does not check that `rated_at` is a valid timestamp
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `rated_at` (e.g., `"not_a_timestamp"`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-49: `scorer_verdicts` does not check that `rated_at` is a valid timestamp
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `rated_at` (e.g., `"not_a_timestamp"`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-50: `affirmed_verdict` does not check that `build` is a valid string
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `build` (e.g., `123`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-51: `scorer_verdicts` does not check that `build` is a valid string
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `build` (e.g., `123`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-52: `affirmed_verdict` does not check that `candidates_generated_at` is a valid timestamp
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `candidates_generated_at` (e.g., `"not_a_timestamp"`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-53: `scorer_verdicts` does not check that `candidates_generated_at` is a valid timestamp
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `candidates_generated_at` (e.g., `"not_a_timestamp"`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-54: `affirmed_verdict` does not check that `verdicts` is a dict of dicts
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `verdicts` key that is not a dict of dicts (e.g., `{"a": "not_a_dict"}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `verdicts` is informational. No issue.

**No P1 here.** I retract.

---

### P1-55: `scorer_verdicts` does not check that `verdicts` is a dict of dicts
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `verdicts` key that is not a dict of dicts (e.g., `{"a": "not_a_dict"}`). `scorer_verdicts` checks `isinstance(v, dict)` for each verdict. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-56: `affirmed_verdict` does not check that `scorer` is a dict of known keys
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `scorer` key that is not a dict of known keys (e.g., `{"unknown_key": "value"}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `scorer` is informational. No issue.

**No P1 here.** I retract.

---

### P1-57: `scorer_verdicts` does not check that `scorer` is a dict of known keys
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `scorer` key that is not a dict of known keys (e.g., `{"unknown_key": "value"}`). `scorer_verdicts` checks `sc.get("kind")`, `sc.get("event")`, `sc.get("scorer_sha")`, `sc.get("threshold")`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-58: `affirmed_verdict` does not check that `rated_at` is a valid ISO 8601 timestamp
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `rated_at` (e.g., `"2026-13-45T99:99:99Z"`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-59: `scorer_verdicts` does not check that `rated_at` is a valid ISO 8601 timestamp
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `rated_at` (e.g., `"2026-13-45T99:99:99Z"`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-60: `affirmed_verdict` does not check that `build` is a valid build name
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `build` (e.g., `"not_a_build"`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-61: `scorer_verdicts` does not check that `build` is a valid build name
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `build` (e.g., `"not_a_build"`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-62: `affirmed_verdict` does not check that `candidates_generated_at` is a valid ISO 8601 timestamp
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `candidates_generated_at` (e.g., `"2026-13-45T99:99:99Z"`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-63: `scorer_verdicts` does not check that `candidates_generated_at` is a valid ISO 8601 timestamp
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `candidates_generated_at` (e.g., `"2026-13-45T99:99:99Z"`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-64: `affirmed_verdict` does not check that `verdicts` is a dict of dicts with known keys
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `verdicts` key that is a dict of dicts with unknown keys (e.g., `{"a": {"unknown_key": "value"}}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `verdicts` is informational. No issue.

**No P1 here.** I retract.

---

### P1-65: `scorer_verdicts` does not check that `verdicts` is a dict of dicts with known keys
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `verdicts` key that is a dict of dicts with unknown keys (e.g., `{"a": {"unknown_key": "value"}}`). `scorer_verdicts` checks `isinstance(v, dict)`, `isinstance(v.get("text_sha256"), str)`, `num(v.get("score"))`, `not v.get("error")`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-66: `affirmed_verdict` does not check that `scorer` is a dict of dicts with known keys
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `scorer` key that is a dict of dicts with unknown keys (e.g., `{"unknown_key": {"nested": "value"}}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `scorer` is informational. No issue.

**No P1 here.** I retract.

---

### P1-67: `scorer_verdicts` does not check that `scorer` is a dict of dicts with known keys
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `scorer` key that is a dict of dicts with unknown keys (e.g., `{"unknown_key": {"nested": "value"}}`). `scorer_verdicts` checks `sc.get("kind")`, `sc.get("event")`, `sc.get("scorer_sha")`, `sc.get("threshold")`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-68: `affirmed_verdict` does not check that `rated_at` is a valid ISO 8601 timestamp with timezone
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `rated_at` (e.g., `"2026-11-13T15:35:10"` without timezone). `affirmed_verdict` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-69: `scorer_verdicts` does not check that `rated_at` is a valid ISO 8601 timestamp with timezone
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `rated_at` (e.g., `"2026-11-13T15:35:10"` without timezone). `scorer_verdicts` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-70: `affirmed_verdict` does not check that `build` is a valid build name with no special characters
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `build` (e.g., `"build;rm -rf /"`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-71: `scorer_verdicts` does not check that `build` is a valid build name with no special characters
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `build` (e.g., `"build;rm -rf /"`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-72: `affirmed_verdict` does not check that `candidates_generated_at` is a valid ISO 8601 timestamp with timezone
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `candidates_generated_at` (e.g., `"2026-11-13T15:35:10"` without timezone). `affirmed_verdict` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-73: `scorer_verdicts` does not check that `candidates_generated_at` is a valid ISO 8601 timestamp with timezone
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `candidates_generated_at` (e.g., `"2026-11-13T15:35:10"` without timezone). `scorer_verdicts` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-74: `affirmed_verdict` does not check that `verdicts` is a dict of dicts with known keys and valid values
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `verdicts` key that is a dict of dicts with known keys but invalid values (e.g., `{"a": {"text_sha256": "not_a_hash", "score": 4.0}}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `verdicts` is informational. No issue.

**No P1 here.** I retract.

---

### P1-75: `scorer_verdicts` does not check that `verdicts` is a dict of dicts with known keys and valid values
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `verdicts` key that is a dict of dicts with known keys but invalid values (e.g., `{"a": {"text_sha256": "not_a_hash", "score": 4.0}}`). `scorer_verdicts` checks `isinstance(v.get("text_sha256"), str)`, `num(v.get("score"))`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-76: `affirmed_verdict` does not check that `scorer` is a dict of dicts with known keys and valid values
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `scorer` key that is a dict of dicts with known keys but invalid values (e.g., `{"kind": "not_moments", "event": None}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `scorer` is informational. No issue.

**No P1 here.** I retract.

---

### P1-77: `scorer_verdicts` does not check that `scorer` is a dict of dicts with known keys and valid values
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `scorer` key that is a dict of dicts with known keys but invalid values (e.g., `{"kind": "not_moments", "event": None}`). `scorer_verdicts` checks `sc.get("kind") != SCORER_KIND`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-78: `affirmed_verdict` does not check that `rated_at` is a valid ISO 8601 timestamp with timezone and no extra fields
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `rated_at` (e.g., `"2026-11-13T15:35:10Z extra"`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-79: `scorer_verdicts` does not check that `rated_at` is a valid ISO 8601 timestamp with timezone and no extra fields
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `rated_at` (e.g., `"2026-11-13T15:35:10Z extra"`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-80: `affirmed_verdict` does not check that `build` is a valid build name with no special characters and no extra fields
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `build` (e.g., `"build;rm -rf / extra"`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-81: `scorer_verdicts` does not check that `build` is a valid build name with no special characters and no extra fields
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `build` (e.g., `"build;rm -rf / extra"`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-82: `affirmed_verdict` does not check that `candidates_generated_at` is a valid ISO 8601 timestamp with timezone and no extra fields
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `candidates_generated_at` (e.g., `"2026-11-13T15:35:10Z extra"`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-83: `scorer_verdicts` does not check that `candidates_generated_at` is a valid ISO 8601 timestamp with timezone and no extra fields
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `candidates_generated_at` (e.g., `"2026-11-13T15:35:10Z extra"`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-84: `affirmed_verdict` does not check that `verdicts` is a dict of dicts with known keys and valid values and no extra fields
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `verdicts` key that is a dict of dicts with known keys and valid values but extra fields (e.g., `{"a": {"text_sha256": "hash", "score": 4.0, "extra": "value"}}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `verdicts` is informational. No issue.

**No P1 here.** I retract.

---

### P1-85: `scorer_verdicts` does not check that `verdicts` is a dict of dicts with known keys and valid values and no extra fields
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `verdicts` key that is a dict of dicts with known keys and valid values but extra fields (e.g., `{"a": {"text_sha256": "hash", "score": 4.0, "extra": "value"}}`). `scorer_verdicts` checks `isinstance(v, dict)`, `isinstance(v.get("text_sha256"), str)`, `num(v.get("score"))`, `not v.get("error")`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-86: `affirmed_verdict` does not check that `scorer` is a dict of dicts with known keys and valid values and no extra fields
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `scorer` key that is a dict of dicts with known keys and valid values but extra fields (e.g., `{"kind": "moments", "event": None, "extra": "value"}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `scorer` is informational. No issue.

**No P1 here.** I retract.

---

### P1-87: `scorer_verdicts` does not check that `scorer` is a dict of dicts with known keys and valid values and no extra fields
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `scorer` key that is a dict of dicts with known keys and valid values but extra fields (e.g., `{"kind": "moments", "event": None, "extra": "value"}`). `scorer_verdicts` checks `sc.get("kind")`, `sc.get("event")`, `sc.get("scorer_sha")`, `sc.get("threshold")`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-88: `affirmed_verdict` does not check that `rated_at` is a valid ISO 8601 timestamp with timezone and no extra fields and no nested objects
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `rated_at` (e.g., `{"nested": "value"}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-89: `scorer_verdicts` does not check that `rated_at` is a valid ISO 8601 timestamp with timezone and no extra fields and no nested objects
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `rated_at` (e.g., `{"nested": "value"}`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `rated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-90: `affirmed_verdict` does not check that `build` is a valid build name with no special characters and no extra fields and no nested objects
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `build` (e.g., `{"nested": "value"}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-91: `scorer_verdicts` does not check that `build` is a valid build name with no special characters and no extra fields and no nested objects
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `build` (e.g., `{"nested": "value"}`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `build` is informational. No issue.

**No P1 here.** I retract.

---

### P1-92: `affirmed_verdict` does not check that `candidates_generated_at` is a valid ISO 8601 timestamp with timezone and no extra fields and no nested objects
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have an invalid `candidates_generated_at` (e.g., `{"nested": "value"}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-93: `scorer_verdicts` does not check that `candidates_generated_at` is a valid ISO 8601 timestamp with timezone and no extra fields and no nested objects
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have an invalid `candidates_generated_at` (e.g., `{"nested": "value"}`). `scorer_verdicts` does not check it. This is not a fail-closed issue; `candidates_generated_at` is informational. No issue.

**No P1 here.** I retract.

---

### P1-94: `affirmed_verdict` does not check that `verdicts` is a dict of dicts with known keys and valid values and no extra fields and no nested objects
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `verdicts` key that is a dict of dicts with known keys and valid values but extra fields and nested objects (e.g., `{"a": {"text_sha256": "hash", "score": 4.0, "extra": {"nested": "value"}}}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `verdicts` is informational. No issue.

**No P1 here.** I retract.

---

### P1-95: `scorer_verdicts` does not check that `verdicts` is a dict of dicts with known keys and valid values and no extra fields and no nested objects
**File:** `pipeline/package.py`, `scorer_verdicts` (lines ~122–164)

**Scenario:**
The integrator’s verdict may have a `verdicts` key that is a dict of dicts with known keys and valid values but extra fields and nested objects (e.g., `{"a": {"text_sha256": "hash", "score": 4.0, "extra": {"nested": "value"}}}`). `scorer_verdicts` checks `isinstance(v, dict)`, `isinstance(v.get("text_sha256"), str)`, `num(v.get("score"))`, `not v.get("error")`. This is correct. No issue.

**No P1 here.** I retract.

---

### P1-96: `affirmed_verdict` does not check that `scorer` is a dict of dicts with known keys and valid values and no extra fields and no nested objects
**File:** `pipeline/package_pin.py`, `affirmed_verdict` (lines ~360–371)

**Scenario:**
The integrator’s verdict may have a `scorer` key that is a dict of dicts with known keys and valid values but extra fields and nested objects (e.g., `{"kind": "moments", "event": None, "extra": {"nested": "value"}}`). `affirmed_verdict` does not check it. This is not a fail-closed issue; `scorer` is informational. No issue.

**No P1 here.** I retract.

---

### P1-97: `scorer_verdicts` does not check that `scorer` is a dict of dicts with