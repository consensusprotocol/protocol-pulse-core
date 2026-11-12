# qwen3.8-27b (qwen/qwen3.8-27b) 111 s finish=stop usage in 21533 / out 3788 usd~0.121 (upper-bound price)

# Code Audit: pp-selectid-0829 (C1_STEP.diff)

## P0 Findings

### P0-1: `vo_fidelity.majority` allows a slot to pass when the majority of runs failed it
**File:** `pipeline/vo_fidelity.py`, lines 220–235 (in diff)

The voting logic at line 220 is:
```python
failed = [s for s, vs in votes.items() if 2 * vs.count("pass") <= len(runs)]
```
For 3 runs, a slot is marked `failed` only when `pass_count <= 1`. A 2-1 split (2 pass, 1 fail) is **not** added to `failed`.

However, the verdict `ok` at line 234 is:
```python
"ok": 2 * n_measured > len(runs) and not failed
```
This means a slot with votes `["pass", "pass", "fail"]` passes the majority gate. **This is correct per the ruling** ("majority decides"). But the deeper issue is in the **violation aggregation** (lines 221–230):

When a slot is in `failed`, it collects violations from **all** runs where `v.get("slot") in (s, "-")`. But when a slot is **not** in `failed` (i.e., it passed by majority), **no violations are collected for that slot at all**, even if one of the failing runs had a specific violation on that slot. This is actually correct behavior (the majority passed it), so this is not a bug.

**Re-evaluation:** The logic is actually sound. A 2-1 pass means the slot passes. A 1-2 or 0-3 means it fails and violations are collected. The `n_measured` check ensures at least 2 of 3 runs were measured. **No P0 here.**

### P0-2: `self_repair` in `verify_segment` drops the token from `span` but the `compare` function may still see a mismatch
**File:** `pipeline/transcript_truth.py`, lines 171–176 (in diff)

```python
if len(sw) > 1 and toks and self_repair(sw, 0, toks[0]):
    repair, span = sw[0]["text"], " ".join(w["text"] for w in sw[1:]).strip()
cmp_ = compare(text, span)
```

The `span` is rebuilt from `sw[1:]`, dropping the self-repair token. The `text` parameter is the **primary** transcript's text for the clip. The `compare` function compares `text` against `span`. If the primary transcript does **not** contain the self-repair token (which is the premise: "heard by the second recogniser and not by the primary"), then `text` starts with the first real word, and `span` now also starts with the first real word. This should align.

**However**, there is a subtle issue: `self_repair(sw, 0, toks[0])` checks that `sw[0]` is a truncated prefix of `sw[1]` and that `sw[1]` matches `toks[0]` (the first token of the primary text). But `toks` is derived from `text` via `re.findall(r"[\w'’$%.,-]+", text or "")`. If the primary text's first word is "Bitcoin" and the second recogniser's `sw[1]` is "bitcoin" (lowercase), `_w()` normalizes both to "bitcoin", so the 4-letter prefix check `fw[:4] == _w(first)[:4]` passes. This is fine.

**But**: what if the primary text's first word is "Bitcoin" and the second recogniser's `sw[0]` is "Bit-" and `sw[1]` is "bitcoin"? The `self_repair` function checks `fw.startswith(stem)` where `stem = _w("Bit-".rstrip("-")) = "bit"` and `fw = _w("bitcoin") = "bitcoin"`. `"bitcoin".startswith("bit")` is True. `len("bit") < len("bitcoin")` is True. The speaker check passes. So it is correctly identified.

**Potential issue:** The `edges()` function (lines 153–163) also calls `self_repair(ws, j, first)` where `first` is the clip's first word from the **primary** transcript. But in `edges()`, `ws` is the second recogniser's words, and `first` is passed from the `text` parameter. The `self_repair` function compares `fw[:4] == _w(first)[:4]`. If the primary's first word is "Bitcoin" and the second recogniser's `ws[i+1]` is "bitcoin", this works. But what if the primary's first word is "Bit" (a different word entirely)? Then `_w(first)[:4] = "bit"` and `fw[:4] = "bit"`, so it would incorrectly match. However, the `fw.startswith(stem)` check requires that the second recogniser's word is a **fuller** version of the truncated token, and the 4-letter prefix is a heuristic. This is a **weak heuristic** but is bounded by the orchestrator's ruling. **Not a P0, but a P2 concern.**

### P0-3: `package.runtime()` mirror may not be faithful to the deployed factory
**File:** `pipeline/package.py`, lines 17–24 (in diff)

The new `runtime()` uses:
```python
vo = sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in vo_lines if t and t.strip())
return round(sum(m["duration_s"] for m in segs) + vo + FINAL_TAIL_S, 2)
```

The docstring says it mirrors `edl_rules._r4_moments` from main `a5ec0f17`. The key question: does the deployed factory's `_r4_moments` use the **same** `R4_WPS` (2.5), `R4_PREROLL_S` (1.0), and `FINAL_TAIL_S` (14.30)? The diff does not show `edl_rules.py`, so I **cannot verify** the mirror is faithful. The test at line 488–490 hardcodes `14.30` and `2.5`, which matches the docstring, but if the deployed factory uses different constants, the mirror is wrong.

**This is a P1, not P0**, because the test pins the expected values, and the docstring explicitly states the source. But if the deployed factory changes, this will silently diverge.

## P1 Findings

### P1-1: `min_vo_words` and `r4_max_vo_words` algebra may be inconsistent with the new `runtime()`
**File:** `pipeline/package.py`, lines 32–48 (in diff)

`r4_max_vo_words`:
```python
vo_max = R4_MOMENTS_SHARE * (content_s + FINAL_TAIL_S) / (1 - R4_MOMENTS_SHARE)
return max(0, int(R4_WPS * (vo_max - R4_PREROLL_S * n_vo)))
```

Let's verify the algebra. The constraint is:
```
VO_s <= SHARE * (content_s + VO_s + TAIL)
VO_s * (1 - SHARE) <= SHARE * (content_s + TAIL)
VO_s <= SHARE * (content_s + TAIL) / (1 - SHARE)
```
This matches. Then `VO_s = w / R4_WPS + PRE * n_vo`, so:
```
w / R4_WPS + PRE * n_vo <= vo_max
w <= R4_WPS * (vo_max - PRE * n_vo)
```
This also matches. **The algebra is correct.**

`min_vo_words`:
```python
return max(0, int(R4_WPS * (RUNTIME_S[0] - content_s - FINAL_TAIL_S - R4_PREROLL_S * n_vo) + 0.999))
```
The constraint is:
```
content_s + w / R4_WPS + PRE * n_vo + TAIL >= 60
w / R4_WPS >= 60 - content_s - TAIL - PRE * n_vo
w >= R4_WPS * (60 - content_s - TAIL - PRE * n_vo)
```
This matches. **The algebra is correct.**

### P1-2: `content_range` upper bound may be too tight
**File:** `pipeline/package.py`, line 58 (in diff)

```python
return lo, RUNTIME_S[1] - FINAL_TAIL_S - VO_S[0] - R4_PREROLL_S * n_vo
```

`VO_S[0]` is the minimum VO seconds (from config). The upper bound is `70 - TAIL - VO_min - PRE * n_vo`. This assumes the **minimum** VO is used, which is correct for the upper bound on content (more content means less VO needed, but VO has a minimum). However, if `VO_S[0]` is not the actual minimum VO seconds used by the factory, this could be off. **Cannot verify without `config.py`.**

### P1-3: `vo_fidelity.majority` does not validate that all runs have the same `lines`
**File:** `pipeline/vo_fidelity.py`, lines 203–246 (in diff)

The function signature is `majority(runs, lines)`, but it does not check that each run in `runs` was actually computed on the same `lines`. If a caller passes runs from different line sets, the votes will be misaligned. The docstring says "runs: check() results on the same segments and lines," but there is no runtime check. **This is a P2** because the caller (`run_given_package.py`) always uses the same `lines`.

### P1-4: `self_repair` in `edges()` may skip a token that is not actually a self-repair
**File:** `pipeline/transcript_truth.py`, lines 153–163 (in diff)

In `edges()`, the code does:
```python
j, repair = i - 1, None
if self_repair(ws, j, first):
    repair, j = ws[j]["text"], j - 1
prev = ws[j]["text"] if j >= 0 else None
```

If `self_repair` returns True, `j` is decremented by 1, and `prev` is the word before the self-repair. But what if `j - 1` is out of bounds? The code checks `j >= 0` before accessing `ws[j]`, so this is safe. However, if `i = 0`, then `j = -1`, and `self_repair(ws, -1, first)` is called. The `self_repair` function checks `0 <= i < len(words) - 1`, so for `i = -1`, it returns False. This is safe.

**But**: what if `i = 1` and `j = 0`? Then `self_repair(ws, 0, first)` is called. If it returns True, `j` becomes `-1`, and `prev = None`. The `out["in"]` will have `"ok": False` because `prev is None`. This is correct: if the self-repair is the first word in the window, there is no word before it, so the sentence start is not confirmed. **This is correct behavior.**

### P1-5: `run_given_package.py` `--to-existed` hardcodes a file path
**File:** `tests/package/run_given_package.py`, line 454 (in diff)

```python
facts = "/home/ultron/protocol_pulse/docs/audits/parallel/integrator_RULING7_FACTS.md"
```

This is a hardcoded absolute path. If the code is run on a different machine or in a different directory, this will fail. **This is a P2** because it is a test driver, not production code, but it is a maintenance hazard.

## P2 Findings

### P2-1: `self_repair` 4-letter prefix heuristic is weak
**File:** `pipeline/transcript_truth.py`, line 141 (in diff)

```python
fw[:4] == _w(first)[:4]
```

This only checks the first 4 letters. If the primary's first word is "Bit" and the second recogniser's word is "bitcoin", this matches. But if the primary's first word is "Bit" and the second recogniser's word is "biting", this also matches, which is incorrect. The `fw.startswith(stem)` check requires that the second recogniser's word starts with the truncated token, but the 4-letter prefix is a separate check. In practice, this is unlikely to cause a false positive because the truncated token must be a prefix of the second recogniser's word, and the 4-letter prefix is a sanity check. **Low risk.**

### P2-2: `vo_fidelity.majority` does not handle the case where `runs` is empty
**File:** `pipeline/vo_fidelity.py`, line 212 (in diff)

```python
if not runs or len(runs) % 2 == 0:
    raise ValueError(f"majority needs an odd number of runs, got {len(runs)}")
```

This correctly raises an error for an empty list. **No issue.**

### P2-3: `package.inventory` `vo_fidelity_verdict` row may have inconsistent `n` field
**File:** `pipeline/package.py`, lines 101–104 (in diff)

```python
"vo_fidelity_verdict": dict(row(bool((fid.get("verdict") or {}).get("ok")), fid.get("backend"),
                                fid.get("replayed"), n=fid.get("runs", 1), measured=bool(fid.get("measured"))),
                            **({"votes": fid["majority"]["votes"], "splits": fid["majority"]["splits"]}
                               if fid.get("majority") else {})),
```

If `fid` is from a single run (not majority), `fid.get("runs")` is not set, so `n` defaults to 1. If `fid` is from `majority()`, `fid["runs"]` is set to the number of runs. This is consistent. **No issue.**

### P2-4: `run_given_package.py` `--precheck` does not check for audio file existence
**File:** `tests/package/run_given_package.py`, lines 389–394 (in diff)

```python
for x in sorted(os.listdir(AUDIO)):
    parts = x[:-4].rsplit("_", 2) if x.endswith(".wav") else []
    if len(parts) == 3 and parts[0] == sg["video_id"] and int(parts[1]) / 1000.0 <= float(sg["start"]) - 1.0 \
            and int(parts[2]) / 1000.0 >= float(sg["end"]) + 1.0:
        w_, ws_ = os.path.join(AUDIO, x), int(parts[1]) / 1000.0
        break
```

If no audio file is found, `w_` and `ws_` remain `None`, and `TT.verify_segment` is called with `wav=None`. The `verify_segment` function handles `wav=None` by using a default `wav_start`, so this is safe. **No issue.**

## Verdict

The diff is well-structured and the algebra in `package.py` is correct. The `vo_fidelity.majority` logic is sound, and the `self_repair` implementation matches the orchestrator's ruling. The main concerns are:

1. **P1-3**: `vo_fidelity.majority` does not validate that all runs use the same `lines`. This is a minor issue because the caller always uses the same `lines`, but it is a latent bug.
2. **P1-5**: Hardcoded file path in `run_given_package.py`. This is a maintenance hazard.
3. **P2-1**: The 4-letter prefix heuristic in `self_repair` is weak but low-risk.

**SHIP: yes with conditions**

Conditions:
1. Add a runtime check in `vo_fidelity.majority` to verify that all runs have the same `lines` (or at least the same number of lines and slots).
2. Replace the hardcoded file path in `run_given_package.py` with a relative path or an environment variable.
3. Consider strengthening the `self_repair` prefix check to use the full word length, not just 4 letters, to reduce the risk of false positives.