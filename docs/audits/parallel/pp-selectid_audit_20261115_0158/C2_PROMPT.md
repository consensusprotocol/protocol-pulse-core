# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_0158
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 342 s finish=stop usage in 15703 / out 9772 usd_reported=0.001699 usd~0.194 (upper-bound price)

# Audit: pp-selectid — RULING 111 (v4 format re-try)

Scope: `tests/package/replay110.py` (modified), `tests/package/replay111.py` (new), `tests/package/test_replay111.py` (new). I reviewed the diff as given; findings below.

---

## replay110.py (modified)

**[P2] `replay_one`'s `names` lookup silently falls back to `name(m)` — masking misconfiguration.** Line 21: `b = router.backends[(names or {}).get(m) or name(m)]`. If the caller passes a `names` map that lacks the model key, or the map's value is `""`/`None`, the code silently uses the *ruling-110* backend name. In replay111's usage this is always populated (`names = {v: bname(v) for v in VARIANTS}`), but a typo'd key yields the wrong backend with no error — the row would then report a different `model_id` than the one actually called. Fail-closed (M12) would prefer a KeyError. Mitigated by the test at lines 467–478 which exercises the happy path only. Should fix: assert the key exists when `names` is provided.

**[P3] `row["model_id"] = b.model` changes ruling-110's row semantics.** Previously `model_id: MODELS[m]` (a constant); now it's the backend's `model` attribute. For ruling 110's own backends these should coincide, but if any backend's `model` differs from the `MODELS` registry (e.g. a dated/aliased deployment), old-vs-new comparisons in `summary`/`table` silently compare different model_ids. The claim "its 9 tests pass unchanged" is asserted, not proven here. Verify `MODELS[m] == b.model` for every ruling-110 backend, or keep the old expression when `names` is not passed.

**[P3] `router.down.pop(b.name, ...)` vs. old `router.down.pop(name(m), ...)`.** Same key question as above; if `b.name != name(m)` for any legacy backend, the "failure is never a verdict: tried afresh" semantics change. Same verification.

**[P3] Docstring of `replay_one` now documents ruling-111 behaviour inside ruling-110's file.** Fine, but the "RULING 111" reference in replay110.py's docstring creates a cross-file coupling; a future reader of replay110 alone won't know what ruling 111 is. Nit.

**[P2] `summary(rows, models=MODELS)` — the default binds at import time.** If `MODELS` is ever mutated (e.g. a test or a future driver extends it), the default argument captures the *object*, so mutation is actually picked up (good), but if `MODELS` is *rebound* in replay110 after import, callers of `summary` with no args see the old binding. In practice replay111 always passes `models=` explicitly (line 320: `RX.summary(full, models=[best])`), so this is latent only. Nit-to-P2.

---

## replay111.py (new)

**[P1] `FormatBackend.complete` diverges from production's body in more than the two fields.** The test (lines 439–455) pins that the bodies differ by exactly `response_format` and `reasoning_effort` — but only for *one* prompt shape and *one* spec. Specifically:

- Line 138: the system message is `(system or "") + " Reply with one JSON object only."` — if production's `HeimdallBackend.complete` (pipeline/providers.py:415-4434) does *not* append that suffix, the bodies differ by a third field's *content*. The test would catch it (bodies[1] != bodies[0] after popping the two keys) — good — but only if the test's SPEC and prompt exercise the same code path. It does. However, the appended instruction is itself a prompt change: the order says "the same calls... as production asks" plus two fields. If production's complete() already appends a similar instruction, the test passes while the semantics differ. **Verify the copied body is byte-identical to production's for the same (prompt, max_tokens, seed, system) — the test does this, so this is contingent on the test's fidelity, which is good.** Downgrade to P3 if the test truly pins it; the risk is that `P._http_json` / `P._with_backoff` signatures drift and the copy silently diverges. The docstring acknowledges the copy-not-inherit choice; a drift-catcher (the test) exists. Acceptable, but the copy will rot.

- **[P1] `FormatBackend.complete` does not replicate production's response parsing/normalisation.** Production's `complete` (providers.py:415-434) presumably handles `reasoning`-in-own-field (the probe noted "medium: the reasoning arrives in its own field, not in the content"). This copy reads only `j["choices"][0]["message"].get("content")`. For effort=medium, if the gateway puts reasoning in `message.reasoning_content` and *shortens* `content` (or returns content=None when only reasoning is produced), the copied parser returns `""` → the answer is counted as an out-of-contract "empty" shape, when production would have... well, production doesn't use reasoning_effort at all. But the *order* says the effort variants are compared by valid-answer rate; if medium's content is systematically shorter (reasoning tokens counted in `completion_tokens` but reasoning text not in `content`), then `max_to

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 27 s finish=stop usage in 17488 / out 1321 usd_reported=0.001755 usd~0.072 (upper-bound price)

To: Protocol Pulse Audit Team
Re: Code Audit — `pp-selectid-20261115_0158` (Ruling 111)

I have reviewed the diff for `tests/package/replay110.py`, `tests/package/replay111.py`, and `tests/package/test_replay111.py` against the Governing Laws and the specific "PLEASE CHECK" items.

### Findings

**1. [P1] `FormatBackend` System Prompt Mutation**
In `replay111.py`, the `FormatBackend.complete` method constructs the system message as:
```python
"messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object only."}, ...]
```
The test `test_the_json_mode_and_the_effort_are_the_only_fields_added_to_productions_body` asserts that `bodies[1]` (the new backend) equals `bodies[0]` (the production backend) *after* popping `response_format` and `reasoning_effort`. However, the production backend (`P.HeimdallBackend`) does **not** append `" Reply with one JSON object only."` to the system prompt.
*   **Violation:** The test will fail because the `messages` field in the body will differ.
*   **Law Impact:** This violates the intent of "exactly as production asks" (L-l / Ruling 111 Order). If the test is fixed to ignore the system prompt, the code is still altering the prompt, which may steer the model (contrary to the note that "a schema... could steer the answer," though a system prompt suffix is less risky, it is still a deviation from the "unchanged" baseline). If the test is not fixed, the code is broken.
*   **Fix:** Remove the suffix from the system prompt in `FormatBackend` to match production exactly, or update the test to explicitly allow this specific suffix (but the former is preferred for "smallest diff" and "no steering").

**2. [P2] `shape()` Truncation Logic Edge Case**
In `replay111.py`, the `shape` function checks for truncation:
```python
if (cap and out_tokens and out_tokens >= cap) or t.count("{") > t.count("}") or \
        (pos is not None and pos >= len(t) - 1):
    return "truncated"
```
The condition `pos >= len(t) - 1` relies on `json.JSONDecodeError.pos`. If the JSON is invalid due to a syntax error at the very end (e.g., missing closing brace), `pos` is often `len(t)`. However, if the error is "Expecting value" at the end, `pos` might be `len(t)`.
*   **Issue:** The test case `('{"a": "an answer cut mid-wor', "truncated")` passes because `pos` will be near the end. However, the logic `t.count("{") > t.count("}")` is a heuristic. If a valid JSON string contains unbalanced braces inside a string value (e.g., `{"a": "}"}`), this heuristic fails.
*   **Law Impact:** Low risk for "diagnosis only" (Ruling 111), but it may misclassify "invalid JSON" as "truncated" or vice versa, affecting the "3 commonest failure shapes" report.
*   **Fix:** The heuristic is acceptable for a diagnostic tool, but the `pos` check should be `pos == len(t)` or `pos > len(t) - 2` to be more robust against off-by-one errors in different JSON parsers.

**3. [P3] `choose()` Tie-Breaking with `None` p50**
In `replay111.py`, `choose` uses:
```python
-(sc[v]["p50_s"] if sc[v]["p50_s"] is not None else float("inf"))
```
If both variants have `None` p50 (no valid answers), they tie on p50. The logic is sound. However, if one has `None` and the other has a value, the one with `None` gets `-inf` (lowest priority), which is correct (we prefer lower p50, so `None` is worst).
*   **Note:** This is correct. No change needed.

**4. [P3] Spend Stop Logic**
`ask_one` uses `stop_usd=STOP_USD` ($0.38). `replay_one` checks `if router.spent() >= stop_usd: return "stopped"`.
*   **Law Impact:** Complies with "No call starts once the ledger holds STOP_USD".
*   **Note:** The test `test_this_orders_stop_not_ruling_110s` verifies this. Correct.

**5. [P3] Ruling 110 Backwards Compatibility**
`replay_one` defaults: `keep_raw=False`, `names=None`, `prefix="replay110"`.
*   **Law Impact:** Complies with "ruling 110's behaviour is unchanged by the defaults".
*   **Note:** The test `test_an_out_of_contract_answers_text_is_kept_only_when_asked` verifies `raw_text` is absent when `keep_raw=False`. Correct.

**6. [P3] Table Arithmetic**
`valid-answer rate = (in_time + late) / (in_time + late + out_of_contract)`.
`agreement on valid answers = agree / total_units_in_valid_answers`.
*   **Law Impact:** Complies with the order's definition.
*   **Note:** The code in `scores` and `table` implements this correctly.

### Summary of Critical Issues

The primary blocker is the **System Prompt Mutation** in `FormatBackend`. The test asserts equality with production, but the code modifies the system prompt. This will cause the test suite to fail immediately.

P1_OR_WORSE: 1

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 consensus, audit 20261115_0158 (written by the builder; qwen3.8-27b P1_OR_WORSE 1, glm-5.3-flash 3; both raised a
# P1, so they agree and Grok was not asked)

## qwen P1, "production does not append ' Reply with one JSON object only.'": NOT SO
providers.HeimdallBackend.complete (base :420-421) appends it, and the body test proves it: production's body and
FormatBackend's are equal once the two added fields are removed. No change.

## glm P1, "the copy could differ from production on another prompt shape": ACCEPTED, test widened
The body test now also asks a VISION prompt of both back-ends and pins that the bodies are equal but for the two
fields. Mutation Y3 (the body drifts from production's) is killed.

## glm P1, "medium's reasoning counts against the output budget": TRUE AND INTENDED, now documented
The reasoning counts against the same output budget (max_out, 16,000 tokens) that production gives every call; the
01:5x probe showed completion_tokens includes the reasoning. An answer that budget cuts is "truncated" by shape() and
counts against medium in choose(), as it would in production. Stated in the docstring.

## glm P1 -> P2 (glm's own downgrade), the overshoot past the stop: BOUNDED BY MEASUREMENT, documented
At most --workers (6) calls are in flight when the ledger reaches $0.38. Ruling 110 measured this model at medium at a
median of $0.000058 and a maximum of $0.001122 a call, so they add at most about $0.007, inside the $0.02 margin to the
order's $0.40.

## glm, choose() (glm's own P3), and a real gap found here: FIXED
When no effort gives a single valid answer on the sample, choose() returns None and no full run is made: nothing would
be measured. Test added (choose returns None for 0 valid; a single valid answer is enough); mutation Y13 is killed.

## glm P2s
- "valid JSON, wrong fields" can also be right fields with refused labels or values: RENAMED "valid JSON, not the
  contract".
- SOURCE_110 / CUT_NOTE defined below table(): moved above it.
- the names fallback: a key missing from names falls to replay110's name(), which raises KeyError for any non-110
  key, so a misconfiguration fails loudly. The cost fragment ("_reported if the gateway reports cost only when...")
  states no defect; production reads usage.cost the same way. No change.
After the fixes: test_replay111 (9) and test_replay110 (9) pass; 13 of 13 mutations killed.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_0158/C2_STEP.diff (576 lines)
```
   1 | diff --git a/tests/package/replay110.py b/tests/package/replay110.py
   2 | index 73e53ca..3205447 100644
   3 | --- a/tests/package/replay110.py
   4 | +++ b/tests/package/replay110.py
   5 | @@ -105,15 +105,18 @@ def _tupled(v):
   6 |      return tuple(v) if isinstance(v, list) else v
   7 |  
   8 |  
   9 | -def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep):
  10 | +def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep, keep_raw=False, names=None,
  11 | +               prefix="replay110"):
  12 |      """One record asked of one candidate -> its row, None (rate limited or refused by the guard: no row, a re-run asks
  13 | -    again; a rate limit first waits 30 s) or "stopped" (the ledger holds stop_usd: no call made)."""
  14 | +    again; a rate limit first waits 30 s) or "stopped" (the ledger holds stop_usd: no call made). RULING 111: keep_raw
  15 | +    keeps an out-of-contract answer's text in its row ("raw_text": for diagnosis only, never a verdict); names maps a
  16 | +    candidate key to its back-end's name (default: name()), and its chain is "<prefix>_<key>"."""
  17 |      p, rec, k, anchors, m = job
  18 |      if router.spent() >= stop_usd:
  19 |          return "stopped"
  20 | -    b = router.backends[name(m)]
  21 | +    b = router.backends[(names or {}).get(m) or name(m)]
  22 |      dl = router.effective_deadline(rec.get("role"), b, None)       # ruling 100: what a live call of this verdict gets
  23 | -    row = {"record": os.path.relpath(p, WT), "type": k, "model": m, "model_id": MODELS[m], "anchors": anchors,
  24 | +    row = {"record": os.path.relpath(p, WT), "type": k, "model": m, "model_id": b.model, "anchors": anchors,
  25 |             "grok_recorded_at": rec.get("recorded_at"), "grok_seconds": rec.get("seconds"), "deadline_100_s": dl,
  26 |             "cap_s": cap_s}
  27 |      try:
  28 | @@ -121,9 +124,9 @@ def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep):
  29 |      except (ValueError, TypeError, KeyError) as e:
  30 |          row["grok"], row["grok_error"] = None, f"{type(e).__name__}: {str(e)[:160]}"
  31 |      t0 = time.time()
  32 | -    router.down.pop(name(m), None)                        # a failure is never a verdict: each call is tried afresh
  33 | +    router.down.pop(b.name, None)                         # a failure is never a verdict: each call is tried afresh
  34 |      try:
  35 | -        rep = router.call(f"replay110_{m}", rec["prompt"], int(rec.get("max_tokens") or 2000),
  36 | +        rep = router.call(f"{prefix}_{m}", rec["prompt"], int(rec.get("max_tokens") or 2000),
  37 |                            int(rec.get("seed") or 7), system=rec.get("system"), deadline_s=cap_s)
  38 |      except P.SpendLimit:
  39 |          return None
  40 | @@ -149,6 +152,8 @@ def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep):
  41 |      except (ValueError, TypeError, KeyError) as e:
  42 |          row.update(heimdall=None, heimdall_error=f"out of contract: {type(e).__name__}: {str(e)[:160]}",
  43 |                     outcome="out_of_contract")
  44 | +        if keep_raw:                                  # ruling 111 (b): the text as it came, for diagnosis only
  45 | +            row["raw_text"] = rep.text
  46 |          router.reject(rep)
  47 |          return row
  48 |      row["outcome"] = "in_time" if dl is None or secs <= dl else "late"
  49 | @@ -222,11 +227,11 @@ def _s(x):
  50 |      return "-" if x is None else f"{x:.0f}"
  51 |  
  52 |  
  53 | -def summary(rows):
  54 | -    """-> {(type, model): figures} over the rows (one per record and model)."""
  55 | +def summary(rows, models=MODELS):
  56 | +    """-> {(type, model): figures} over the rows (one per record and model), for each key of `models`."""
  57 |      out = {}
  58 |      for k in R.DECIDING:
  59 | -        for m in MODELS:
  60 | +        for m in models:
  61 |              rs = [r for r in rows if r["type"] == k and r["model"] == m]
  62 |              if not rs:
  63 |                  continue
  64 | diff --git a/tests/package/replay111.py b/tests/package/replay111.py
  65 | new file mode 100644
  66 | index 0000000..021ea25
  67 | --- /dev/null
  68 | +++ b/tests/package/replay111.py
  69 | @@ -0,0 +1,341 @@
  70 | +#!/usr/bin/env python3
  71 | +"""RULING 111 (orchestrator 01:52 ET Nov 15): THE V4 FORMAT RE-TRY. Ruling 110 left the v4 abliterated
  72 | +(deepseek/deepseek-v4-flash-0731-abliterated) unmeasured: 136 of its 319 answers were not valid JSON. Here it is asked
  73 | +in the gateway's JSON mode (response_format {"type": "json_object"}) with a set reasoning_effort, on the same 319
  74 | +records (ruling 85.1's), with the same decisions, comparison and bars (replay85.decide / compare / passes) and the
  75 | +same calls, deadlines, cut, rate limits and guard (replay110.replay_one).
  76 | +THE GATEWAY (probed at 01:5x ET Nov 15): for this model it takes response_format json_object, response_format
  77 | +json_schema and reasoning_effort, so no repair re-ask is needed. json_object is used. The contracts name each prompt's
  78 | +own labels, clip keys, joins and hook ids, so a json_schema would have to be ours, made per prompt, and could steer the
  79 | +answer. Every contract check stays with the pipeline's own parsers.
  80 | +THE EFFORT: none and medium are both asked on the first SAMPLE records (ruling 85.1's order, which covers every
  81 | +verdict type). The better is kept for all 319 by choose(): the higher valid-answer rate, then the higher agreement on
  82 | +valid answers, then the lower p50. When neither effort gave a single valid answer, no full run is made. At medium the
  83 | +reasoning counts against the output budget production gives every call (max_out, 16,000 tokens): an answer cut by it
  84 | +is "truncated" and counts against medium, as it would in production.
  85 | +OUT OF CONTRACT: each such answer's text is kept in its row ("raw_text": diagnosis only, never a verdict) and named by
  86 | +shape(): empty, code fence, valid JSON that is not the contract (fields, labels or values), prose around the JSON,
  87 | +truncated, invalid JSON.
  88 | +SPEND: Heimdall only, on its own ledger (tests/package/proof/SPEND_R111.json, vendor-reported). No call starts once
  89 | +the ledger holds STOP_USD: the order's cap of $0.40, less what calls in flight may still add. At most --workers (6)
  90 | +are in flight; ruling 110 measured this model at a median $0.00006 and at most $0.0011 a call (at medium), so they
  91 | +add at most about $0.007.
  92 | +Usage: python3 -B tests/package/replay111.py [--workers 6] [--sample 40] [--table-only]"""
  93 | +import argparse
  94 | +import collections
  95 | +import json
  96 | +import os
  97 | +import statistics
  98 | +import sys
  99 | +import threading
 100 | +import time
 101 | +from concurrent.futures import ThreadPoolExecutor
 102 | +
 103 | +HERE = os.path.dirname(os.path.abspath(__file__))
 104 | +REPO = os.path.dirname(os.path.dirname(HERE))
 105 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 106 | +sys.path.insert(0, HERE)
 107 | +import deadline_table as DT  # noqa: E402
 108 | +import providers as P  # noqa: E402
 109 | +import replay85 as R  # noqa: E402
 110 | +import replay110 as RX  # noqa: E402
 111 | +
 112 | +WT = R.WT
 113 | +OUT = os.path.join(WT, "tests", "package", "proof", "replay111")
 114 | +SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_R111.json")
 115 | +LIMIT_USD, STOP_USD, SAMPLE = 3.00, 0.38, 40
 116 | +MODEL = "deepseek/deepseek-v4-flash-0731-abliterated"
 117 | +FORMAT = {"type": "json_object"}
 118 | +VARIANTS = ("none", "medium")
 119 | +PREFIX = "replay111"
 120 | +SHAPES = ("empty", "code fence", "valid JSON, not the contract", "prose around the JSON", "truncated", "invalid JSON")
 121 | +
 122 | +
 123 | +def bname(v):
 124 | +    return f"heimdall:{MODEL}#effort-{v}"
 125 | +
 126 | +
 127 | +class FormatBackend(P.HeimdallBackend):
 128 | +    """providers.HeimdallBackend.complete with the same body (model, max_tokens, seed, temperature, the same messages),
 129 | +    plus the gateway's JSON mode and a reasoning effort. It is copied, not inherited, because the production back-end
 130 | +    builds its body inside complete(). test_replay111 pins that the two bodies differ by those two fields only."""
 131 | +
 132 | +    def __init__(self, name, spec, env_path, effort):
 133 | +        super().__init__(name, spec, env_path)
 134 | +        self.effort = effort
 135 | +
 136 | +    def complete(self, prompt, max_tokens, seed, system=None):
 137 | +        key = self.key("HEIMDALL_API_KEY")
 138 | +        content = prompt if not P.is_vision(prompt) else \
 139 | +            [{"type": "text", "text": prompt["text"]}] + [{"type": "image_url", "image_url": {
 140 | +                "url": "data:image/jpeg;base64," + i}} for i in prompt["images"]]
 141 | +        body = {"model": self.model, "max_tokens": self.max_out(max_tokens), "seed": seed,
 142 | +                "temperature": self.spec.get("temperature", 0),
 143 | +                "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object only."},
 144 | +                             {"role": "user", "content": content}],
 145 | +                "response_format": FORMAT, "reasoning_effort": self.effort}
 146 | +        t0 = time.time()
 147 | +        base = self._base()
 148 | +        j = P._with_backoff(lambda: P._http_json(base + "/chat/completions", body, {"Authorization": "Bearer " + key},
 149 | +                                                 self.timeout), final_codes=(401, 402, 403))
 150 | +        u = j.get("usage") or {}
 151 | +        try:
 152 | +            text = j["choices"][0]["message"].get("content") or ""
 153 | +        except (KeyError, IndexError, TypeError):
 154 | +            raise P.RequestRejected("heimdall: no choices") from None
 155 | +        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)},
 156 | +                          **P._reported(u.get("cost"))), time.time() - t0
 157 | +
 158 | +
 159 | +def build_router(variants, record_dir=None, spend_path=None, deadline_log=None):
 160 | +    """replay110.build_router's Router, with one FormatBackend per effort on its own chain "replay111_<effort>"."""
 161 | +    r = P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD,
 162 | +                 limit_basis=RX.LIMIT_BASIS, routing="heimdall_first", deadline_log=deadline_log,
 163 | +                 deadlines=DT.load(DT.STATE, None), reserve_wait_s=RX.RESERVE_WAIT_S)
 164 | +    tmpl = r.config["backends"][RX.TEMPLATE]
 165 | +    for v in variants:
 166 | +        r.backends[bname(v)] = FormatBackend(bname(v), dict(tmpl, model=MODEL), r.env_path, v)
 167 | +        r.chains[f"{PREFIX}_{v}"] = [bname(v)]
 168 | +    return r
 169 | +
 170 | +
 171 | +def shape(text, out_tokens=None, cap=None):
 172 | +    """The shape of an answer the parsers refused -> one of SHAPES (the first that applies, in that order)."""
 173 | +    t = (text or "").strip()
 174 | +    if not t:
 175 | +        return "empty"
 176 | +    if t.startswith("```"):
 177 | +        return "code fence"
 178 | +    try:
 179 | +        json.loads(t)
 180 | +        return "valid JSON, not the contract"
 181 | +    except ValueError as e:
 182 | +        pos = getattr(e, "pos", None)
 183 | +    a, b = t.find("{"), t.rfind("}")
 184 | +    if 0 <= a < b and (a > 0 or b < len(t) - 1):
 185 | +        try:
 186 | +            json.loads(t[a:b + 1])
 187 | +            return "prose around the JSON"
 188 | +        except ValueError:
 189 | +            pass
 190 | +    if (cap and out_tokens and out_tokens >= cap) or t.count("{") > t.count("}") or \
 191 | +            (pos is not None and pos >= len(t) - 1):
 192 | +        return "truncated"
 193 | +    return "invalid JSON"
 194 | +
 195 | +
 196 | +def scores(rows, v):
 197 | +    """One effort's figures over its rows: answers, valid answers, the valid-answer rate, the agreement on valid
 198 | +    answers, p50."""
 199 | +    rs = [r for r in rows if r["model"] == v]
 200 | +    ans = [r for r in rs if r.get("outcome") in ("in_time", "late", "out_of_contract")]
 201 | +    ok = [r for r in ans if r.get("outcome") in ("in_time", "late")]
 202 | +    cmp_ = [c for r in ok for c in (r.get("compare") or {}).values()]
 203 | +    secs = [r["seconds"] for r in ans if isinstance(r.get("seconds"), (int, float))]
 204 | +    return {"rows": len(rs), "answers": len(ans), "valid": len(ok),
 205 | +            "valid_rate": len(ok) / len(ans) if ans else 0.0,
 206 | +            "agree_valid": cmp_.count("agree") / len(cmp_) if cmp_ else 0.0,
 207 | +            "p50_s": statistics.median(secs) if secs else None}
 208 | +
 209 | +
 210 | +def choose(rows, variants=VARIANTS):
 211 | +    """-> (the better effort, {effort: scores}): the higher valid-answer rate, then the higher agreement on valid
 212 | +    answers, then the lower p50. None when no effort gave a single valid answer (no full run is worth making)."""
 213 | +    sc = {v: scores(rows, v) for v in variants}
 214 | +    best = max(variants, key=lambda v: (round(sc[v]["valid_rate"], 9), round(sc[v]["agree_valid"], 9),
 215 | +                                        -(sc[v]["p50_s"] if sc[v]["p50_s"] is not None else float("inf"))))
 216 | +    return (best if sc[best]["valid"] else None), sc
 217 | +
 218 | +
 219 | +def anchor_failures(rows):
 220 | +    """Every anchor decision (a delivered pin's own clip, line-up or line: replay85.anchor_units) Grok passed and the
 221 | +    candidate failed -> [{"record", "type", "model", "unit", "pins"}]."""
 222 | +    anchors, out = R.anchor_texts(), []
 223 | +    for r in rows:
 224 | +        for u, pins in R.anchor_units(r, anchors).items():
 225 | +            if (r.get("compare") or {}).get(u) == "stricter":
 226 | +                out.append({"record": r["record"], "type": r["type"], "model": r["model"], "unit": u, "pins": pins})
 227 | +    return out
 228 | +
 229 | +
 230 | +def ask_one(router, job, names, cap_s=RX.CAP_S):
 231 | +    """One record asked of one effort as this order asks it: replay110.replay_one on the effort's own chain, with
 232 | +    this order's stop (STOP_USD) and every out-of-contract text kept."""
 233 | +    return RX.replay_one(router, job, cap_s=cap_s, stop_usd=STOP_USD, keep_raw=True, names=names, prefix=PREFIX)
 234 | +
 235 | +
 236 | +def _pct(n, d):
 237 | +    return f"{100 * n / d:.0f}%" if d else "-"
 238 | +
 239 | +
 240 | +def _p(v):
 241 | +    return "-" if v is None else f"{v:.0f}%"
 242 | +
 243 | +
 244 | +def _rows(path):
 245 | +    rows = []
 246 | +    try:
 247 | +        with open(path) as f:
 248 | +            for line in f:
 249 | +                try:
 250 | +                    rows.append(json.loads(line))
 251 | +                except ValueError:
 252 | +                    pass
 253 | +    except OSError:
 254 | +        pass
 255 | +    return rows
 256 | +
 257 | +
 258 | +def run(args):
 259 | +    os.makedirs(os.path.join(OUT, "replies"), exist_ok=True)
 260 | +    res_path = os.path.join(OUT, "RESULTS.jsonl")
 261 | +    recs, missing = RX.source_records()
 262 | +    router = build_router(VARIANTS, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND,
 263 | +                          deadline_log=os.path.join(OUT, "DEADLINES.jsonl"))
 264 | +    names, lock = {v: bname(v) for v in VARIANTS}, threading.Lock()
 265 | +
 266 | +    def ask(jobs, label):
 267 | +        n = {"done": 0, "stopped": 0, "no_row": 0}
 268 | +
 269 | +        def one(job):
 270 | +            row = ask_one(router, job, names)
 271 | +            with lock:
 272 | +                if row == "stopped":
 273 | +                    n["stopped"] += 1
 274 | +                elif row is None:
 275 | +                    n["no_row"] += 1
 276 | +                else:
 277 | +                    if row.get("outcome") == "out_of_contract":
 278 | +                        cap = router.backends[names[job[4]]].max_out(int(job[1].get("max_tokens") or 2000))
 279 | +                        row["shape"] = shape(row.get("raw_text"), row.get("out_tokens"), cap)
 280 | +                    with open(res_path, "a") as f:
 281 | +                        f.write(json.dumps(row) + "\n")
 282 | +                n["done"] += 1
 283 | +                if n["done"] % 20 == 0 or n["done"] == len(jobs):
 284 | +                    print(f"  {label}: {n['done']}/{len(jobs)} at {time.strftime('%H:%M:%S')}, "
 285 | +                          f"${router.spent():.4f} spent", flush=True)
 286 | +        with ThreadPoolExecutor(max_workers=args.workers) as ex:
 287 | +            list(ex.map(one, jobs))
 288 | +        print(f"replay111 {label}: {n['stopped']} not started (the ${STOP_USD:.2f} stop), {n['no_row']} without a row",
 289 | +              flush=True)
 290 | +
 291 | +    def done():
 292 | +        return {(x["record"], x["model"]) for x in _rows(res_path) if "record" in x and "model" in x}
 293 | +
 294 | +    sample = recs[:args.sample]
 295 | +    seen = done()
 296 | +    ask([(p, r, k, a, v) for (p, r, k, a) in sample for v in VARIANTS if (os.path.relpath(p, WT), v) not in seen],
 297 | +        f"the sample ({len(sample)} records x {len(VARIANTS)} efforts)")
 298 | +    keys = {os.path.relpath(p, WT) for p, _, _, _ in sample}
 299 | +    best, sc = choose([x for x in _rows(res_path) if x.get("record") in keys])
 300 | +    with open(os.path.join(OUT, "CHOICE.json"), "w") as f:
 301 | +        json.dump({"best": best, "sample_records": len(sample), "scores": sc,
 302 | +                   "rule": "the higher valid-answer rate, then the higher agreement on valid answers, then the lower p50"},
 303 | +                  f, indent=1)
 304 | +    if best is None:
 305 | +        print(f"replay111: no effort gave a valid answer on the sample: no full run ({json.dumps(sc)})", flush=True)
 306 | +        table()
 307 | +        return
 308 | +    print(f"replay111: effort {best} kept ({json.dumps(sc)})", flush=True)
 309 | +    seen = done()
 310 | +    ask([(p, r, k, a, best) for (p, r, k, a) in recs if (os.path.relpath(p, WT), best) not in seen],
 311 | +        f"all {len(recs)} records on effort {best}")
 312 | +    table()
 313 | +
 314 | +
 315 | +SOURCE_110 = os.path.join(RX.OUT, "RESULTS.jsonl")
 316 | +CUT_NOTE = "each call cut at 300 s (replay110)."
 317 | +
 318 | +
 319 | +def table():
 320 | +    rows = _rows(os.path.join(OUT, "RESULTS.jsonl"))
 321 | +    try:
 322 | +        with open(os.path.join(OUT, "CHOICE.json")) as f:
 323 | +            choice = json.load(f)
 324 | +    except (OSError, ValueError):
 325 | +        choice = {}
 326 | +    best = choice.get("best")
 327 | +    keys = {r["record"] for r in rows if r.get("model") == best} if best else set()
 328 | +    sample_keys = None
 329 | +    if choice.get("sample_records"):
 330 | +        recs, _ = RX.source_records()
 331 | +        sample_keys = {os.path.relpath(p, WT) for p, _, _, _ in recs[:choice["sample_records"]]}
 332 | +    full = [r for r in rows if r.get("model") == best]
 333 | +    s = RX.summary(full, models=[best]) if best else {}
 334 | +    old = RX.summary([r for r in _rows(SOURCE_110) if r.get("model") == "dsv4" and r.get("record") in keys],
 335 | +                     models=["dsv4"])
 336 | +    base = R.grok_self()
 337 | +    lines = ["# Ruling 111: the v4 abliterated in the gateway's JSON mode", "",
 338 | +             f"Built {time.strftime('%Y-%m-%d %H:%M %Z')}. {MODEL}, response_format {json.dumps(FORMAT)}, "
 339 | +             f"reasoning_effort {best}. Ruling 85.1's records; ruling 100's deadline (the gateway's 120 s); "
 340 | +             f"{CUT_NOTE}", "",
 341 | +             "## The effort, on the sample (the first records in ruling 85.1's order)", "",
 342 | +             "| effort | rows | answers | valid | valid-answer rate | agreement on valid answers | p50 s |",
 343 | +             "|---|---|---|---|---|---|---|"]
 344 | +    for v, x in (choice.get("scores") or {}).items():
 345 | +        lines.append(f"| {v}{' (kept)' if v == best else ''} | {x['rows']} | {x['answers']} | {x['valid']} | "
 346 | +                     f"{100 * x['valid_rate']:.0f}% | {100 * x['agree_valid']:.0f}% | {RX._s(x['p50_s'])} |")
 347 | +    if not best:
 348 | +        lines += ["", "## No full run: no effort gave a single valid answer on the sample"]
 349 | +    lines += ["", f"## All {len(keys)} records, effort {best} (ruling 110's columns, then the two this order adds)", "",
 350 | +              "| type | records | in time | late | timeouts | errors | out of contract | missed | units in time | agree | "
 351 | +              "stricter | looser | different | agree % in time | p50 s | p90 s | usd reported | VALID-ANSWER RATE | "
 352 | +              "AGREEMENT ON VALID ANSWERS | ruling 110 (no JSON mode): valid-answer rate / agreement |", "|" + "---|" * 20]
 353 | +    for (k, m), x in s.items():
 354 | +        ans = x["in_time"] + x["late"] + x["out_of_contract"]
 355 | +        o = old.get((k, "dsv4")) or {}
 356 | +        oans = o.get("in_time", 0) + o.get("late", 0) + o.get("out_of_contract", 0)
 357 | +        lines.append(f"| {k} | {x['records']} | {x['in_time']} | {x['late']} | {x['timeout']} | {x['error']} | "
 358 | +                     f"{x['out_of_contract']} | {x['missed']} | {x['units_in_time']} | {x['agree']} | {x['stricter']} | "
 359 | +                     f"{x['looser']} | {x['different']} | {_p(x['agree_in_time_pct'])} | {RX._s(x['p50_s'])} | "
 360 | +                     f"{RX._s(x['p90_s'])} | {x['usd_reported']:.4f} | {_pct(x['in_time'] + x['late'], ans)} | "
 361 | +                     f"{_p(x['agree_all_pct'])} | {_pct(o.get('in_time', 0) + o.get('late', 0), oans)} / "
 362 | +                     f"{_p(o.get('agree_all_pct'))} |")
 363 | +    bad = [r for r in full if r.get("outcome") == "out_of_contract"]
 364 | +    shapes = collections.Counter(r.get("shape") or "unclassified" for r in bad)
 365 | +    lines += ["", f"## Out of contract: {len(bad)} answers (texts in RESULTS.jsonl and OUT_OF_CONTRACT.jsonl)", ""]
 366 | +    lines += [f"- {n} {sh}" for sh, n in shapes.most_common()] or ["- none"]
 367 | +    for k in R.DECIDING:
 368 | +        per = collections.Counter(r.get("shape") for r in bad if r["type"] == k)
 369 | +        if per:
 370 | +            lines.append(f"  - {k}: " + ", ".join(f"{n} {sh}" for sh, n in per.most_common()))
 371 | +    fails = anchor_failures(full)
 372 | +    lines += ["", f"## Anchor decisions Grok passed that it failed: {len(fails)}", ""]
 373 | +    lines += [f"- {x['type']} {x['record']} unit {x['unit']} (pins {', '.join(x['pins'])})" for x in fails] or ["- none"]
 374 | +    lines += ["", "## The bars of rulings 85/88/96, per verdict type (replay85.passes)", ""]
 375 | +    bars = {}
 376 | +    for k in R.DECIDING:
 377 | +        if (k, best) not in s:
 378 | +            continue
 379 | +        ok, why, agree, med = R.passes(full, base, k, best)
 380 | +        bars[k] = {"meets": ok, "why": why}
 381 | +        lines.append(f"- {k}: {'MEETS THE BARS' if ok else 'DOES NOT: ' + '; '.join(why)}")
 382 | +    with open(os.path.join(OUT, "TABLE.md"), "w") as f:
 383 | +        f.write("\n".join(lines) + "\n")
 384 | +    with open(os.path.join(OUT, "OUT_OF_CONTRACT.jsonl"), "w") as f:
 385 | +        for r in bad:
 386 | +            f.write(json.dumps({k_: r.get(k_) for k_ in ("record", "type", "model", "heimdall_error", "shape",
 387 | +                                                        "out_tokens", "raw_text")}) + "\n")
 388 | +    with open(os.path.join(OUT, "SUMMARY.json"), "w") as f:
 389 | +        json.dump({"choice": choice, "sample_keys": len(sample_keys or ()),
 390 | +                   "table": {f"{k}|{m}": x for (k, m), x in s.items()}, "shapes": dict(shapes),
 391 | +                   "anchor_failures": fails, "bars": bars}, f, indent=1)
 392 | +    print("\n".join(lines), flush=True)
 393 | +    return s, shapes, fails, bars
 394 | +
 395 | +
 396 | +def main(argv=None):
 397 | +    ap = argparse.ArgumentParser()
 398 | +    ap.add_argument("--workers", type=int, default=6, help="calls in flight")
 399 | +    ap.add_argument("--sample", type=int, default=SAMPLE, help="the records both efforts are asked first")
 400 | +    ap.add_argument("--table-only", action="store_true")
 401 | +    a = ap.parse_args(argv)
 402 | +    if a.table_only:
 403 | +        table()
 404 | +        return 0
 405 | +    run(a)
 406 | +    return 0
 407 | +
 408 | +
 409 | +if __name__ == "__main__":
 410 | +    sys.exit(main())
 411 | diff --git a/tests/package/test_replay111.py b/tests/package/test_replay111.py
 412 | new file mode 100644
 413 | index 0000000..83e3cdd
 414 | --- /dev/null
 415 | +++ b/tests/package/test_replay111.py
 416 | @@ -0,0 +1,159 @@
 417 | +#!/usr/bin/env python3
 418 | +"""RULING 111's re-try driver (tests/package/replay111.py), offline. The v4 is asked in the gateway's JSON mode with a set
 419 | +effort, and otherwise exactly as production asks; an out-of-contract answer's text is kept and its shape named; the
 420 | +better effort is chosen by the stated rule; every anchor decision Grok passed and the candidate failed is listed."""
 421 | +import json
 422 | +import os
 423 | +import sys
 424 | +import tempfile
 425 | +import unittest
 426 | +from unittest import mock
 427 | +
 428 | +HERE = os.path.dirname(os.path.abspath(__file__))
 429 | +REPO = os.path.dirname(os.path.dirname(HERE))
 430 | +for _p in ("pipeline", "tests/package", "tests/providers"):
 431 | +    sys.path.insert(0, os.path.join(REPO, _p))
 432 | +import providers as P  # noqa: E402
 433 | +import replay110 as RX  # noqa: E402
 434 | +import replay111 as RY  # noqa: E402
 435 | +from test_providers import Fake, router  # noqa: E402
 436 | +from test_replay110 import GROK, Timed, candidate, job  # noqa: E402
 437 | +
 438 | +SPEC = {"vendor": "heimdall", "model": RY.MODEL, "base_url": "http://gateway.invalid/api/v1",
 439 | +        "price_usd_per_1m": [3, 15], "family": "deepseek", "temperature": 0, "min_out": 16000}
 440 | +
 441 | +
 442 | +class Answer:
 443 | +    def read(self):
 444 | +        return json.dumps({"choices": [{"message": {"content": '{"ok": 1}'}}],
 445 | +                           "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0001}}).encode()
 446 | +
 447 | +
 448 | +class TestTheBackend(unittest.TestCase):
 449 | +
 450 | +    def test_the_json_mode_and_the_effort_are_the_only_fields_added_to_productions_body(self):
 451 | +        bodies = []
 452 | +
 453 | +        def urlopen(req, timeout=None):
 454 | +            bodies.append(json.loads(req.data))
 455 | +            return Answer()
 456 | +        prod = P.HeimdallBackend("heimdall:" + RY.MODEL, SPEC, "/nonexistent")
 457 | +        fmt = RY.FormatBackend(RY.bname("none"), SPEC, "/nonexistent", "none")
 458 | +        for b in (prod, fmt):
 459 | +            b.key = lambda name: "test-key"
 460 | +        vision = {"text": "the sheet", "images": ["aGVsbG8="]}
 461 | +        with mock.patch.object(P.urllib.request, "urlopen", urlopen):
 462 | +            prod.complete("the prompt", 300, 7, "the system")
 463 | +            text, usage, _ = fmt.complete("the prompt", 300, 7, "the system")
 464 | +            prod.complete(vision, 300, 7)
 465 | +            fmt.complete(vision, 300, 7)
 466 | +        for i in (1, 3):
 467 | +            added = {k: bodies[i].pop(k) for k in ("response_format", "reasoning_effort")}
 468 | +            self.assertEqual(added, {"response_format": {"type": "json_object"}, "reasoning_effort": "none"})
 469 | +            self.assertEqual(bodies[i], bodies[i - 1])                 # all else exactly as production sends it
 470 | +        self.assertEqual((text, usage["usd_reported"]), ('{"ok": 1}', 0.0001))
 471 | +
 472 | +
 473 | +class TestTheCall(unittest.TestCase):
 474 | +
 475 | +    def test_an_out_of_contract_answers_text_is_kept_only_when_asked(self):
 476 | +        with tempfile.TemporaryDirectory() as d:
 477 | +            kept = RX.replay_one(candidate(d, Timed("not json")), job(d), cap_s=2.0, keep_raw=True)
 478 | +            plain = RX.replay_one(candidate(d, Timed("not json")), job(d), cap_s=2.0)
 479 | +            self.assertEqual((kept["outcome"], kept["raw_text"]), ("out_of_contract", "not json"))
 480 | +            self.assertNotIn("raw_text", plain)                            # ruling 110's rows are unchanged
 481 | +
 482 | +    def test_a_named_back_end_on_its_own_chain_answers_for_its_key(self):
 483 | +        with tempfile.TemporaryDirectory() as d:
 484 | +            led = os.path.join(d, "SPEND.json")
 485 | +            json.dump({"usd_estimate": 0.0, "calls": 0, "by_backend": {}, "by_role": {}, "reserved": {},
 486 | +                       "usd_reported": 0.0, "usd_unreported_estimate": 0.0}, open(led, "w"))
 487 | +            b = Fake(RY.bname("none"), "heimdall", answer=GROK, usage={"in": 10, "out": 10, "usd_reported": 0.001})
 488 | +            r = router(d, [b], {"replay111_none": [b.name]}, spend_path=led, limit_usd=50.0, limit_basis="reported",
 489 | +                       routing="heimdall_first")
 490 | +            r.config["routing"] = {"verdict_roles": ["context_verdict"], "verdict_deadline_s": {"heimdall": 120}}
 491 | +            p, rec, k, a, _ = job(d)
 492 | +            row = RX.replay_one(r, (p, rec, k, a, "none"), cap_s=2.0, names={"none": b.name}, prefix="replay111")
 493 | +            self.assertEqual((row["outcome"], row["model"], row["model_id"], b.calls), ("in_time", "none", b.model, 1))
 494 | +
 495 | +
 496 | +class TestThisOrdersCall(unittest.TestCase):
 497 | +
 498 | +    def named(self, d, spent, answer):
 499 | +        led = os.path.join(d, "SPEND.json")
 500 | +        json.dump({"usd_estimate": spent, "calls": 1, "by_backend": {}, "by_role": {}, "reserved": {},
 501 | +                   "usd_reported": spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
 502 | +        b = Fake(RY.bname("none"), "heimdall", answer=answer, usage={"in": 10, "out": 10, "usd_reported": 0.001})
 503 | +        r = router(d, [b], {"replay111_none": [b.name]}, spend_path=led, limit_usd=50.0, limit_basis="reported",
 504 | +                   routing="heimdall_first")
 505 | +        r.config["routing"] = {"verdict_roles": ["context_verdict"], "verdict_deadline_s": {"heimdall": 120}}
 506 | +        p, rec, k, a, _ = job(d)
 507 | +        return r, b, (p, rec, k, a, "none")
 508 | +
 509 | +    def test_this_orders_stop_not_ruling_110s(self):
 510 | +        for held in (0.40, RY.STOP_USD):                                # the order's cap, and its stop below it
 511 | +            with tempfile.TemporaryDirectory() as d:
 512 | +                r, b, j = self.named(d, held, GROK)
 513 | +                self.assertEqual((RY.ask_one(r, j, {"none": b.name}, cap_s=2.0), b.calls), ("stopped", 0))
 514 | +        with tempfile.TemporaryDirectory() as d:
 515 | +            r, b, j = self.named(d, RY.STOP_USD - 0.01, "not json")
 516 | +            row = RY.ask_one(r, j, {"none": b.name}, cap_s=2.0)
 517 | +            self.assertEqual((row["outcome"], row["raw_text"], b.calls), ("out_of_contract", "not json", 1))
 518 | +
 519 | +
 520 | +class TestTheShapes(unittest.TestCase):
 521 | +
 522 | +    def test_each_shape(self):
 523 | +        cases = [("", "empty"), ("   ", "empty"),
 524 | +                 ('```json\n{"a": 1}\n```', "code fence"),
 525 | +                 ('{"a": 1}', "valid JSON, not the contract"),
 526 | +                 ('Here it is: {"a": 1} as asked.', "prose around the JSON"),
 527 | +                 ('{"a": [1, 2', "truncated"),
 528 | +                 ('{"a": "an answer cut mid-wor', "truncated"),          # the error is at the string's start
 529 | +                 ('{"a": 1 "b": 2}', "invalid JSON")]
 530 | +        for text, want in cases:
 531 | +            self.assertEqual(RY.shape(text), want, text)
 532 | +        self.assertEqual(RY.shape('{"a": 1 "b": 2}', out_tokens=16000, cap=16000), "truncated")   # at its token cap
 533 | +        self.assertEqual(RY.shape('{"a": 1 "b": 2}', out_tokens=900, cap=16000), "invalid JSON")
 534 | +
 535 | +
 536 | +def rows_of(v, valid, out_of_contract, agree, secs):
 537 | +    """`valid` in-contract answers (the first `agree` of them agree with Grok) and `out_of_contract` others."""
 538 | +    rs = [{"model": v, "outcome": "in_time", "seconds": secs,
 539 | +           "compare": {f"u{i}": "agree" if i < agree else "stricter"}} for i in range(valid)]
 540 | +    return rs + [{"model": v, "outcome": "out_of_contract", "seconds": secs} for _ in range(out_of_contract)]
 541 | +
 542 | +
 543 | +class TestTheChoice(unittest.TestCase):
 544 | +
 545 | +    def test_the_higher_valid_answer_rate_wins(self):
 546 | +        rows = rows_of("none", 9, 1, 8, 3.0) + rows_of("medium", 7, 3, 7, 3.0)
 547 | +        self.assertEqual(RY.choose(rows)[0], "none")
 548 | +
 549 | +    def test_at_the_same_rate_the_higher_agreement_wins_then_the_lower_p50(self):
 550 | +        rows = rows_of("none", 9, 1, 7, 3.0) + rows_of("medium", 9, 1, 9, 3.0)
 551 | +        self.assertEqual(RY.choose(rows)[0], "medium")
 552 | +        rows = rows_of("none", 9, 1, 9, 3.0) + rows_of("medium", 9, 1, 9, 10.0)
 553 | +        self.assertEqual(RY.choose(rows)[0], "none")
 554 | +
 555 | +    def test_no_effort_with_a_valid_answer_means_no_full_run(self):
 556 | +        rows = rows_of("none", 0, 10, 0, 3.0) + rows_of("medium", 0, 10, 0, 9.0)
 557 | +        self.assertIsNone(RY.choose(rows)[0])
 558 | +        self.assertEqual(RY.choose(rows_of("none", 0, 10, 0, 3.0) + rows_of("medium", 1, 9, 1, 9.0))[0], "medium")
 559 | +
 560 | +
 561 | +class TestTheAnchors(unittest.TestCase):
 562 | +
 563 | +    def test_every_anchor_decision_grok_passed_and_the_candidate_failed_is_listed(self):
 564 | +        rows = [{"record": "r1", "type": "step_a", "model": "none", "compare": {"u1": "stricter", "u2": "stricter"}},
 565 | +                {"record": "r2", "type": "step_a", "model": "none", "compare": {"u1": "stricter"}},
 566 | +                {"record": "r3", "type": "step_a", "model": "none", "compare": {"u1": "agree"}}]
 567 | +        units = {"r1": {"u1": ["37c5b5f5"]}, "r2": {}, "r3": {"u1": ["0c68b589"]}}
 568 | +        with mock.patch.object(RY.R, "anchor_texts", lambda: []), \
 569 | +                mock.patch.object(RY.R, "anchor_units", lambda row, anchors: units[row["record"]]):
 570 | +            got = RY.anchor_failures(rows)
 571 | +        self.assertEqual(got, [{"record": "r1", "type": "step_a", "model": "none", "unit": "u1", "pins": ["37c5b5f5"]}])
 572 | +
 573 | +
 574 | +if __name__ == "__main__":
 575 | +    unittest.main()
 576 | 
```

---

pp-selectid, RULING 111 (orchestrator 01:52 ET Nov 15), THE V4 FORMAT RE-TRY.

THE ORDER: re-run deepseek/deepseek-v4-flash-0731-abliterated on all 319 records of ruling 85.1's replay, with the
contract enforced the gateway's way: response_format json (json_object, or json_schema if the gateway takes it) and
reasoning effort none. Try efforts none and medium on a 40-record sample first and keep the better. Keep the raw text
of every out-of-contract answer (diagnosis only, never a verdict) and report the 3 commonest failure shapes. Give
ruling 110's table, plus per verdict type the valid-answer rate, the agreement on valid answers and every anchor
decision Grok passed that it failed, and whether each type now meets the bars of 85/88/96. Heimdall only, cap $0.40,
no routing change.

THE GATEWAY (probed at 01:5x ET with three tiny calls): for this model it takes response_format json_object,
response_format json_schema and reasoning_effort (none: 1 s, no reasoning; medium: the reasoning arrives in its own
field, not in the content). No repair re-ask is needed.
json_object IS USED, NOT json_schema: the contracts name each prompt's own labels, clip keys, joins and hook ids, so a
schema would be ours, made per prompt, and could steer the answer. Every contract check stays with the pipeline's own
parsers (replay85.decide).

THE CHANGE:
1. tests/package/replay110.py (ruling 110's driver, 45455462 / 397f2760): replay_one gains keep_raw (an
   out-of-contract answer's text goes into its row as "raw_text"), names (a key -> back-end name map) and prefix
   (its chain "<prefix>_<key>"); summary gains models. The defaults are ruling 110's behaviour: its 9 tests pass
   unchanged, and a test in test_replay111 shows its rows carry no raw_text.
2. tests/package/replay111.py (new):
   - FormatBackend: providers.HeimdallBackend.complete (UNCHANGED, base pipeline/providers.py:415-434) copied, with
     response_format {"type": "json_object"} and reasoning_effort added to the body. A test pins that its body equals
     production's, minus those two fields.
   - ask_one: replay110.replay_one with this order's stop (STOP_USD $0.38, under the $0.40 cap), keep_raw and the
     effort's own chain. A test shows that at $0.40 and at $0.38 no call starts.
   - shape(): empty, code fence, valid JSON with the wrong fields, prose around the JSON, truncated (out tokens at the
     cap, more { than }, or the error at the very end), invalid JSON.
   - choose(): the higher valid-answer rate, then the higher agreement on valid answers, then the lower p50.
   - anchor_failures(): every unit replay85.anchor_units (UNCHANGED) names as an anchor's own decision, where the
     candidate is "stricter" than Grok.
   - table(): ruling 110's columns, plus the valid-answer rate, the agreement on valid answers, ruling 110's v4
     figures beside, the shapes, the anchor failures and replay85.passes per type.
   - Own ledger SPEND_R111.json, record dir proof/replay111/replies, chains replay111_none / replay111_medium (no cache
     shared with ruling 110's replies).
TESTS: tests/package/test_replay111.py (8). 12 of 12 mutations killed.

PLEASE CHECK: (1) that FormatBackend asks exactly what production asks plus the two fields; (2) shape()'s order and
rules, especially "truncated"; (3) choose()'s rule and its ties; (4) the spend stop under the $0.40 cap; (5) that
ruling 110's behaviour is unchanged by the defaults; (6) the table's arithmetic (valid-answer rate = in time + late
over in time + late + out of contract; agreement on valid answers = over every valid answer's units); (7) the tests.


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
