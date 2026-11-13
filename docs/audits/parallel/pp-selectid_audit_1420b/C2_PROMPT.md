# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1420b
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 123 s finish=stop usage in 7301 / out 3348 usd~0.072 (upper-bound price)

# Audit: pp-selectid-1420b — cycle-2 consensus increment

## P0

None found.

## P1

**P1-1 — F3: the guarded registry block still runs *before* `package.json` is written, not after; the "record stands" guarantee is weaker than claimed.**
`tests/package/proof_ledger.py:74-92` (diff lines). The diff shows the guarded block (registry outcome, `CA.seed`, tmp-write, `os.replace`) placed immediately after the `say(...)` of the spend line and *before* `with open(os.path.join(out_dir, "package.json"), "w")` — wait, re-reading the diff: the `json.dump(res, ...)` to `package.json` is at diff line 76-77, and the guarded block at 82-92 follows it. So the order is: package.json written, then the guarded registry block. That matches the claim. However, the guard catches only around the registry writes; `logf.close()` and `return 0` follow outside. If `CA.outcome` inside the guarded block raises *after* mutating `reg` in place (e.g., `CA.seed` partially applied, then the tmp `json.dump` fails), the catch logs and the record stands — good. But note: `res["registry"] = True` (diff line 73) is set **unconditionally before** the guarded block, even when the save later fails. The saved `package.json` then claims `registry: true` while the registry on disk was never updated — a downstream reader trusting that flag (the driver "reads and seeds the registry before anything is written") will skip re-seeding, and the paid build's line-ups are silently lost from the registry. Concrete scenario: `os.replace` fails (disk full, permissions) → catch logs → package.json says `registry: true` → next run's driver trusts it → the 8 judged line-ups' passed line-ups never join the registry → repeated paid re-search. This is exactly the loss F3 was meant to prevent, just deferred one step. Severity: P1 (paid-work loss, silent, contradicts the F3 claim "a failure there is logged and the record stands" — the record stands but lies).

**P1-2 — F2: the "never past the judged line-ups" clamp can *under-charge*, letting candidates + angle build exceed 8 judged line-ups in the recorded-verdict case.**
`pipeline/candidates.py:22-24` (diff lines). The clamp is `judged = min(judged, lineups)`-equivalent via the branch, but when `try_one` reports `judged` within range it is trusted as-is. That is F2 as specified. The residual risk: `run_due` stops at the first package (`if cls == "package": return out, tries, lineups`), so the *remaining* due candidates are not tried — fine. But the driver's angle build then gets `lineups=left` where `left` came from the trusted in-range counts. If a `try_one` implementation reports a *cached/recorded* verdict as `judged=0` (free, per ruling 66) yet the underlying recording itself consumed judged line-ups at *its* creation time, the 8-per-build accounting is per-build, so this is consistent. I cannot verify from the diff whether any `try_one` (e.g., the proof_ledger's own `try_one` at diff line 55-63) can report `judged > lineups` — the clamp handles that. What I cannot verify: whether `lineups` can go negative through the `elif` path at diff line 66-67 (`res = PK.build(..., lineups=left, ...)` with `left` possibly 0 — guarded by `left > 0`). Looks guarded. Downgrade: this is really a **P2** — see P2-1.

**P1-3 — F1: a malformed `found_at` raises in `due()`, but the claim "the driver already evaluates it in its refusal block (exit 2, nothing written)" is not verifiable from this diff.**
`pipeline/candidates.py:10-12`. `_at()` behavior on a malformed string is not shown in the diff; the claim that the driver's refusal block catches it (exit 2, nothing written) references code outside the diff. If `_at` raises inside `run_due`'s loop instead (i.e., the driver calls `run_due` before its refusal block, or `_at` is also called on `e["until"]` at diff line 7 which is *not* guarded by the new `old` fallback), a crash there happens after... actually the driver "reads and seeds the registry before anything is written" — seeding happens before, so a crash in `due()` after seeding but before `package.json` leaves the registry seeded with this build's earlier state? No — the driver seeds the registry *from its own record* only at the end. The read at the start is a read. So a malformed `found_at` crash in `due()` happens before anything is written — consistent with fail-closed (M12), provided the driver's first write is indeed `package.json`. From the diff alone I can verify: `due()` raises on malformed `found_at` only if `_at` raises; `_at`'s contract is not in the diff. Flag as unverifiable-from-diff; the stated behavior is plausible but not proven here.

## P2

**P2-1 — F2: the clamp's `why` message and the charged count are consistent, but the clamp silently *under-credits* a try that legitimately judged more than `lineups`... (see P1-2, downgraded).** The clamp at `candidates.py:22-24` sets `judged = lineups` when out

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 147 s finish=stop usage in 7420 / out 699 usd~0.055 (upper-bound price)

**P2: pipeline/candidates.py:11** (F1)  
Concrete scenario: due() now builds sort key with `_at(x[1]["found_at"])` (or `datetime.min` UTC for missing). The added test (test_candidates.py:106-109) confirms ordering for valid ISO-with-offset, same-time, and missing-key cases (newest-first, missing treated as oldest). Cannot verify from diff alone that a malformed `found_at` (e.g. non-ISO string or int) raises inside due() *and* that the driver's pre-write refusal block (exit 2, no package.json/registry update) still fires, because no caller changes or top-level try around `due(reg, now)` appear in the diff.

**P2: pipeline/candidates.py:22** (F2)  
Concrete scenario: run_due passes current `lineups` to try_one, then clamps any returned `judged` to `[0, lineups]` (updating `why` when out-of-range) before subtracting. The new test (test_candidates.py:118-120) confirms a try_one returning 99 when 8 left results in judged=8, left=0 and "all are charged" in why. Verifiable that candidates cannot push total judged > initial 8; the for-loop structure + `if cls == "package"` return + initial lineups=0 test (unchanged) together prevent over-charge. Matches "recorded verdicts free" ruling.

**P1: tests/package/proof_ledger.py:58** (F3)  
Concrete scenario: nested try around `PK.build(..., candidate=c)` catches any Exception, logs, returns `(None, "budget", msg, left)` *without* setting `last["out"]`. run_due still calls `outcome(..., "budget", ...)`, charges remaining lineups, and continues. The later `last.get("out") or {minimal dict}` (line 70) and guarded registry block (lines 82-92) after `package.json` write are present. Verifiable that driver no longer crashes on build raise, package.json is never lost, and candidate is not forcibly closed/rested. The `--from-candidate` path now also populates `candidate_tries` (line 44). However, the diff does not show the outer exception context for the whole `main()`, so cannot verify *all* new paths are non-crashing.

**P2: tests/package/test_candidates.py:104** (test coverage)  
New `test_due_sorts_by_time_not_by_text` and out-of-range test match the F1/F2 claims that are visible in the diff. No test for malformed `found_at`, for a candidate build that raises, or for multiple due candidates when a prior one clamps lineups to 0. All 13 suites pass per header, but coverage of the exact F3 exception/guard paths is not visible.

No P0s. All four stated fixes (F1-F4) are implemented in the visible code; the registry-write guard, candidate_tries shape for --from-candidate, and lineups clamping are exactly as described. Uncertain on malformed-time refusal path and full outer exception surface because they live outside the diff.

**SHIP: yes with conditions** (add malformed-found_at test + confirm due()-raise path still hits exit-2 before any write)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 48 s finish=stop usage in 7910 / out 2182 usd~0.056 (upper-bound price)

# Audit: pp-selectid-1420b (C1_STEP.diff)

## Findings

### P1: `run_due` can return a negative `lineups` count, breaking the driver's "no line-ups left" logic
**File:** `pipeline/candidates.py` (diff lines 21–24)

The F2 fix clamps `judged` to `lineups` when it is out of range, but it does **not** clamp the *result* of the subtraction. If `try_one` returns a negative `judged` (e.g., `-1`), the code executes:
```python
if not 0 <= judged <= lineups:
    why, judged = f"{why} (...)", lineups
lineups -= judged
```
Wait, looking closer at the diff:
```python
judged = int(judged or 0)
if not 0 <= judged <= lineups:                            # audit 1420 C2: never past the judged line-ups
    why, judged = f"{why} (it reported {judged} judged line-ups of {lineups} left: all are charged)", lineups
lineups -= judged
```
If `judged` is negative (e.g., `-5`), the condition `0 <= -5` is `False`, so it enters the `if` block. It sets `judged = lineups` (which is positive, e.g., 8). Then `lineups -= 8`. This is safe.

However, consider the case where `lineups` is already 0.
If `lineups` is 0, and `try_one` returns `judged=0`.
`0 <= 0 <= 0` is True. `lineups -= 0` -> 0. Safe.

What if `try_one` returns `judged=1` when `lineups=0`?
`0 <= 1 <= 0` is False.
`judged` becomes `lineups` (0).
`lineups -= 0` -> 0. Safe.

The logic `judged = lineups` effectively caps the charge at the remaining budget. This seems robust against negative or excessive `judged` values from `try_one`.

**Re-evaluating P1:** Is there a scenario where `lineups` becomes negative?
Only if `judged` > `lineups` AND the clamp didn't happen. But the clamp *is* the assignment `judged = lineups`. So `lineups` can never decrease by more than its current value. `lineups` remains non-negative.

**Correction:** The P1 finding is invalid. The clamp logic is sound.

### P2: `proof_ledger.py` `--from-candidate` path does not update the registry state for the candidate
**File:** `tests/package/proof_ledger.py` (diff lines 44–47 vs 83–85)

In the `--from-candidate` branch (lines 39–47), the code constructs `res["candidate_tries"]` manually. It does **not** call `CA.outcome` on the registry entry *before* the final guarded block.
However, in the final guarded block (lines 82–92), it *does* call `CA.outcome` if `cand is not None` and the key exists in `reg["candidates"]`.
```python
if cand is not None and CA.key(cand["lineup"]) in reg["candidates"]:
    CA.outcome(reg["candidates"][CA.key(cand["lineup"])], res["candidate"]["class"], at, name,
               res["candidate"].get("result"))
```
This looks correct. The state is updated in the guarded block.

**Potential Issue:** The `res["candidate_tries"]` entry in the `--from-candidate` path (line 47) uses:
```python
"judged": (res.get("search") or {}).get("lineups", 0)
```
In the normal `run_due` path, `judged` comes from the `try_one` return value, which is validated/clamped. Here, it comes from `res["search"]["lineups"]`. If `package.build` returns a `search` dict with a `lineups` value that is inconsistent with the actual budget spent (e.g., it reports 0 but actually consumed 3), the `candidate_tries` record will be inaccurate. However, this is a *record* of what the build *reported*, not the registry state. The registry state is driven by `CA.outcome` which uses `res["candidate"]["class"]`. The `judged` count in `candidate_tries` is informational for the audit trail. This is acceptable, but worth noting that the `judged` field in `candidate_tries` for `--from-candidate` is not subject to the F2 clamp logic.

### P2: `due()` raises on malformed `found_at`, but `run_due` does not catch it
**File:** `pipeline/candidates.py` (diff lines 10–12)

The F1 fix states: "A malformed `found_at` now raises in `due()`".
`due()` is called by `run_due()`.
`run_due()` is called by `proof_ledger.main()`.
In `proof_ledger.main()`, the call to `CA.run_due` is **not** inside a `try/except` block.
```python
res, tries, left = CA.run_due(reg, now, try_one, PK.LINEUPS_PER_BUILD, build=name)
```
If `due()` raises a `ValueError` (or similar) due to a malformed timestamp in the registry, the driver will crash *before* writing `package.json`.
The prompt says: "the driver already evaluates in its refusal block (exit 2, nothing written)".
Does the driver have a refusal block that catches exceptions from `run_due`?
Looking at the diff, `run_due` is called at line 64. There is no `try/except` around it in the provided diff.
If the registry contains a malformed `found_at` (e.g., from a previous bug or manual edit), `due()` will raise, `run_due` will propagate it, and `main()` will crash.
This violates M12 (Fail Closed: missing data... rejects; it never produces a pass) in the sense that it crashes rather than producing a controlled failure record. However, crashing *before* writing is safer than writing a corrupt record.
But the prompt says "th

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1420b (the increment: audit 1420's cycle-2 consensus): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes with conditions": a malformed-found_at test, and confirm due() refuses before any write.
  - qwen: "SHIP: yes with conditions". Its P1 is self-refuted ("The clamp logic is sound").
  - glm: "SHIP: yes with conditions": P1-1 (the registry flag), P1-2 (glm: P2), P1-3 (unverifiable from the
    increment).
- No P0.

## Applied (consensus: tests only)

| # | finding | the change |
|---|---|---|
| C1 | grok and glm (4): a test for a zoneless and a malformed found_at | test_candidates: test_a_found_at_without_a_zone_is_utc_and_a_malformed_one_raises. A zoneless found_at sorts as UTC (20:00 before 19:00Z); "tomorrow" raises ValueError. |
| C2 | grok (condition), qwen P2, glm P1-3: confirm a malformed stored time refuses the run before anything is written | The driver evaluates `CA.due(reg, now)` inside its refusal block (tests/package/proof_ledger.py:127, audit 1420 C1), before out_dir exists. The registry does not change between that call and run_due's, so run_due's due() reads the same, already-read times. New driver test: test_a_malformed_candidate_registry_refuses_the_run_before_anything_is_written (test_ledger_build). It points REGISTRY at a temp file with found_at "tomorrow" and asserts exit 2, "registry" named on stderr, the file not rewritten, and no new ledger_* dir or CANDIDATES.json. |

## Answered

| # | finding | the answer |
|---|---|---|
| A1 | glm condition (2): does the final log line read keys missing from the minimal no-package dict? | It reads res.get('why_none'), res['usable'] and res['prescreen'].get('cleared'). The minimal dict carries "usable": None and "prescreen": {}, plus package None, packages [] and why_none. |
| A2 | glm condition (3): does outcome "budget" leave the candidate as it was? | Yes. outcome() changes the state only for "package" / "clip" (closed) and "line" (resting or closed), and raises on any class but "budget". test_the_14_02_rules asserts "budget" leaves an open candidate open. |
| A3 | grok P1 (F3): are all new paths non-crashing? | try_one catches a build exception (no outcome, every line-up left charged). The minimal dict covers a run with no try's out. The post-write block guards the registry's outcome, seed and save. The refusal block catches OSError, ValueError, KeyError and TypeError around the read, seed and due(). |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-1: res["registry"] = True is written even if the registry save then fails | It matters only for a --from-candidate record, the only kind with a top-level "candidate". Its lost outcome leaves that candidate as it was, and it is tried again. A due-path record's tries are never re-read from the record. The failure is logged in the run's log. |
| G2 | glm P1-2 (glm: P2), qwen and grok P2s | The clamp holds the 8 (its tests); the rest is informational. |


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1420b/C2_STEP.diff (169 lines)
```
   1 | diff --git a/pipeline/candidates.py b/pipeline/candidates.py
   2 | index 36640fc..d89ed67 100644
   3 | --- a/pipeline/candidates.py
   4 | +++ b/pipeline/candidates.py
   5 | @@ -97,7 +97,9 @@ def due(reg, now):
   6 |              out.append((k, e, False))
   7 |          elif e["state"] == "resting" and e.get("until") and _at(e["until"]) <= now:
   8 |              out.append((k, e, True))
   9 | -    return sorted(out, key=lambda x: (str(x[1].get("found_at") or ""), x[1]["source"], x[1]["index"]), reverse=True)
  10 | +    old = datetime.min.replace(tzinfo=timezone.utc)             # no time: the oldest (audit 1420 C2: by time)
  11 | +    return sorted(out, key=lambda x: (_at(x[1]["found_at"]) if x[1].get("found_at") else old, x[1]["source"],
  12 | +                                      x[1]["index"]), reverse=True)
  13 |  
  14 |  
  15 |  def run_due(reg, now, try_one, lineups, build=""):
  16 | @@ -111,11 +113,13 @@ def run_due(reg, now, try_one, lineups, build=""):
  17 |          if fresh:
  18 |              e["fresh_used"], e["trying_fresh"] = True, True
  19 |          out, cls, why, judged = try_one(e, fresh, lineups)
  20 | -        lineups -= int(judged or 0)
  21 | +        judged = int(judged or 0)
  22 | +        if not 0 <= judged <= lineups:                            # audit 1420 C2: never past the judged line-ups
  23 | +            why, judged = f"{why} (it reported {judged} judged line-ups of {lineups} left: all are charged)", lineups
  24 | +        lineups -= judged
  25 |          outcome(e, cls, now.isoformat(), build, why)
  26 |          tries.append({"key": k, "source": e["source"], "index": e["index"], "fresh": fresh, "class": cls,
  27 | -                      "why": str(why or "")[:300], "judged": int(judged or 0), "state": e["state"],
  28 | -                      "until": e["until"]})
  29 | +                      "why": str(why or "")[:300], "judged": judged, "state": e["state"], "until": e["until"]})
  30 |          if cls == "package":
  31 |              return out, tries, lineups
  32 |      return None, tries, lineups
  33 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  34 | index 0b0f059..91fd2a7 100644
  35 | --- a/tests/package/proof_ledger.py
  36 | +++ b/tests/package/proof_ledger.py
  37 | @@ -177,9 +177,10 @@ def main(argv=None):
  38 |      name, at = os.path.relpath(out_dir, REPO), now.isoformat()
  39 |      if cand is not None:                                 # --from-candidate: that candidate alone (ruling 66, 13:18)
  40 |          res = PK.build(router, moments, sources, ctx, candidate=cand, **kw)
  41 | -        k = CA.key(cand["lineup"])
  42 | -        if k in reg["candidates"]:
  43 | -            CA.outcome(reg["candidates"][k], res["candidate"]["class"], at, name, res["candidate"].get("result"))
  44 | +        res["candidate_tries"] = [{"key": CA.key(cand["lineup"]), "source": cand["source"], "index": cand["index"],
  45 | +                                   "fresh": bool(cand.get("write_seed")), "class": res["candidate"]["class"],
  46 | +                                   "why": str(res["candidate"].get("result") or "")[:300],
  47 | +                                   "judged": (res.get("search") or {}).get("lineups", 0)}]   # audit 1420 C2
  48 |      else:                                                # RULING 66 (14:02): the due candidates first, newest first
  49 |          last = {}
  50 |  
  51 | @@ -193,7 +194,12 @@ def main(argv=None):
  52 |                  c["write_seed"] = CA.FRESH_SEED          # "then may be tried once more with fresh writes"
  53 |              say(f"  RULING 66: the candidate {e['source']} tried[{e['index']}] {e['lineup']}" +
  54 |                  (" with fresh writes" if fresh else "") + f", {left} judged line-up(s) left")
  55 | -            o = PK.build(router, moments, sources, ctx, candidate=c, lineups=left, **kw)
  56 | +            try:
  57 | +                o = PK.build(router, moments, sources, ctx, candidate=c, lineups=left, **kw)
  58 | +            except Exception as ex:                  # noqa: BLE001  audit 1420 C2: a build that raised is no outcome;
  59 | +                say(f"  RULING 66: its build raised ({type(ex).__name__}: {str(ex)[:200]}): it stays as it was, and "
  60 | +                    f"every judged line-up left is charged")              # what it spent is unknown: no more search
  61 | +                return None, "budget", f"its build raised {type(ex).__name__}: {str(ex)[:200]}", left
  62 |              last["out"] = o
  63 |              return o, o["candidate"]["class"], o["candidate"].get("result"), (o.get("search") or {}).get("lineups", 0)
  64 |          res, tries, left = CA.run_due(reg, now, try_one, PK.LINEUPS_PER_BUILD, build=name)
  65 | @@ -203,7 +209,7 @@ def main(argv=None):
  66 |          if res is None and left > 0:
  67 |              res = PK.build(router, moments, sources, ctx, lineups=left, **kw)
  68 |          elif res is None:                                # every judged line-up went to candidates: no angle asked
  69 | -            res = dict(last["out"], package=None, packages=[],
  70 | +            res = dict(last.get("out") or {"usable": None, "prescreen": {}, "tried": []}, package=None, packages=[],
  71 |                         why_none="ruling 66: the 8 judged line-ups were spent on candidates; no angle asked")
  72 |          res["candidate_tries"] = tries
  73 |      res["registry"] = True                               # its outcomes are in the registry already (CA.seed)
  74 | @@ -234,10 +240,17 @@ def main(argv=None):
  75 |          f"vendor-reported after this build (before it: ${spent0:.2f})")
  76 |      with open(os.path.join(out_dir, "package.json"), "w") as f:
  77 |          json.dump(res, f, indent=1, default=str)
  78 | -    CA.seed(reg, json.loads(json.dumps(res, default=str)), name)   # this build's passed line-ups join the registry
  79 | -    with open(REGISTRY + ".tmp", "w") as f:
  80 | -        json.dump(reg, f, indent=1)
  81 | -    os.replace(REGISTRY + ".tmp", REGISTRY)
  82 | +    try:                                                 # audit 1420 C2: a registry failure never loses the record
  83 | +        if cand is not None and CA.key(cand["lineup"]) in reg["candidates"]:
  84 | +            CA.outcome(reg["candidates"][CA.key(cand["lineup"])], res["candidate"]["class"], at, name,
  85 | +                       res["candidate"].get("result"))
  86 | +        CA.seed(reg, json.loads(json.dumps(res, default=str)), name)   # this build's passed line-ups join it
  87 | +        with open(REGISTRY + ".tmp", "w") as f:
  88 | +            json.dump(reg, f, indent=1)
  89 | +        os.replace(REGISTRY + ".tmp", REGISTRY)
  90 | +    except Exception as e:                               # noqa: BLE001
  91 | +        say(f"  RULING 66: the candidate registry was NOT saved ({type(e).__name__}: {str(e)[:200]}); the record "
  92 | +            f"(package.json) is written")
  93 |      logf.close()
  94 |      return 0
  95 |  
  96 | diff --git a/tests/package/test_candidates.py b/tests/package/test_candidates.py
  97 | index 810a3bc..14bcc8b 100644
  98 | --- a/tests/package/test_candidates.py
  99 | +++ b/tests/package/test_candidates.py
 100 | @@ -63,6 +63,22 @@ class TestRegistry(unittest.TestCase):
 101 |          with self.assertRaises(ValueError):
 102 |              CA.outcome(e2, "maybe", T0.isoformat(), "b")
 103 |  
 104 | +    def test_due_sorts_by_time_not_by_text(self):
 105 | +        reg = CA.new_registry()
 106 | +        CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "utc")                              # 19:00Z
 107 | +        CA.seed(reg, dict(record(T0, [t(["d", "e", "f"])]), now="2026-11-13T14:30:00-05:00"), "et")   # 19:30Z
 108 | +        CA.seed(reg, dict(record(T0, [t(["g", "h", "i"])]), now=None), "none")             # no time: the oldest
 109 | +        self.assertEqual([k for k, _, _ in CA.due(reg, T0)], ["d+e+f", "a+b+c", "g+h+i"])
 110 | +
 111 | +    def test_a_found_at_without_a_zone_is_utc_and_a_malformed_one_raises(self):
 112 | +        reg = CA.new_registry()
 113 | +        CA.seed(reg, dict(record(T0, [t(["a", "b", "c"])]), now="2026-11-13T20:00:00"), "zoneless")   # 20:00 UTC
 114 | +        CA.seed(reg, record(T0, [t(["d", "e", "f"])]), "utc")                                          # 19:00 UTC
 115 | +        self.assertEqual([k for k, _, _ in CA.due(reg, T0)], ["a+b+c", "d+e+f"])
 116 | +        reg["candidates"]["a+b+c"]["found_at"] = "tomorrow"
 117 | +        with self.assertRaises(ValueError):
 118 | +            CA.due(reg, T0)
 119 | +
 120 |      def test_due_is_newest_first_and_a_rested_one_gets_fresh_writes(self):
 121 |          reg = CA.new_registry()
 122 |          CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "old")
 123 | @@ -101,6 +117,9 @@ class TestRegistry(unittest.TestCase):
 124 |          self.assertEqual(reg["candidates"]["a+b+c"]["state"], "open")                    # never reached: still open
 125 |          out, tries, left = CA.run_due(reg, T0 + timedelta(hours=3), lambda e, f, l: (None, "budget", "", 0), 0)
 126 |          self.assertEqual((out, tries, left), (None, [], 0))                              # no line-up left: no try
 127 | +        out, tries, left = CA.run_due(reg, T0 + timedelta(hours=3), lambda e, f, l: (None, "budget", "w", 99), 8)
 128 | +        self.assertEqual((left, tries[0]["judged"]), (0, 8))                             # out of range: all charged
 129 | +        self.assertIn("all are charged", tries[0]["why"])
 130 |  
 131 |      def test_the_fresh_try_is_marked_and_a_line_failing_it_closes(self):
 132 |          reg = CA.new_registry()
 133 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 134 | index f2b6bbc..076c82d 100644
 135 | --- a/tests/package/test_ledger_build.py
 136 | +++ b/tests/package/test_ledger_build.py
 137 | @@ -714,6 +714,31 @@ class TestDriverRefuses(unittest.TestCase):
 138 |              self.assertIn("nostart.json", str(cm.exception))
 139 |          self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_")), before)
 140 |  
 141 | +    def test_a_malformed_candidate_registry_refuses_the_run_before_anything_is_written(self):
 142 | +        """Ruling 66 (audit 1420b C1: grok, qwen, glm): the registry is read, seeded and its times read (CA.due) in
 143 | +        the refusal block: a malformed stored time refuses the run (exit 2) and nothing is written."""
 144 | +        sys.path.insert(0, HERE)
 145 | +        import proof_ledger as PLG
 146 | +        pins = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 147 | +                                                                                 "MOMENTS_PIN_LY.json")]
 148 | +        proof = os.path.join(HERE, "proof")
 149 | +        before = sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json")
 150 | +        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()) as err:
 151 | +            reg = os.path.join(d, "CANDIDATES.json")
 152 | +            with open(reg, "w") as f:
 153 | +                json.dump({"records": [], "candidates": {"x+y+z": {
 154 | +                    "lineup": ["x", "y", "z"], "source": "r", "index": 0, "found_at": "tomorrow", "state": "open",
 155 | +                    "until": None, "fresh_used": False, "history": []}}}, f)
 156 | +            with open(reg) as f:
 157 | +                was = f.read()
 158 | +            with mock.patch.object(PLG, "REGISTRY", reg):
 159 | +                self.assertEqual(PLG.main(["--delivered", *pins]), 2)
 160 | +            self.assertIn("registry", err.getvalue())
 161 | +            with open(reg) as f:
 162 | +                self.assertEqual(f.read(), was)                                     # never rewritten
 163 | +        self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json"),
 164 | +                         before)
 165 | +
 166 |      def test_a_moment_overlapping_any_delivered_span_is_out_whatever_the_pins_age(self):
 167 |          """Audit 2315 C3 K7 (grok, glm): the adapter's delivered_ids (ledger moment ids, 24 h) stay empty: tonight's
 168 |          pins carry no ledger id. L-p is carried by package.usable, which drops any moment that overlaps a delivered
 169 | 
```

---

You are auditing an INCREMENT on branch pp-selectid: the consensus fixes from audit 1420's cycle 2, applied to ruling
66's standing part (the candidate registry, pipeline/candidates.py, and the build driver tests/package/proof_ledger.py).
Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background: candidates.due(reg, now) lists the candidates to try newest first. candidates.run_due tries them inside the
build's 8 JUDGED line-ups (a verdict served from its recording is free: ruling 66 at 14:02, "recorded verdicts free"),
stopping at the first package; try_one(entry, fresh, left) -> (out, class, why, judged). The driver
(proof_ledger.main) reads and seeds the registry before anything is written, tries the due candidates, then the
normal build with the line-ups left, writes package.json, then seeds the registry from its own record and saves it.

The increment (the cycle-2 consensus of audit 1420):
F1 (grok P2, qwen P1): due() sorted by the found_at STRING; ISO strings with different offsets do not sort by time.
   Now: by _at(found_at) (a zoneless time is UTC), and a missing one is the oldest (datetime.min, UTC). A malformed
   found_at now raises in due(), which the driver already evaluates in its refusal block (exit 2, nothing written).
F2 (grok P1 "mechanically enforced", qwen P1 "validate judged"): run_due trusted try_one's judged count. Now an
   out-of-range count (< 0 or > the line-ups left) charges every line-up left, so the 8 are never exceeded, and the
   try's why says so. (Grok's other proposal, charging 1 for every cached candidate, is not taken: the ruling makes
   recorded verdicts free.)
F3 (glm P1-2, qwen P2-NEW-2): a failure around the registry could lose a paid build's record, and a candidate build
   that raised crashed the driver. Now:
   - try_one catches an exception from package.build: no outcome ("budget": the candidate stays as it was), and
     every judged line-up left is charged (what it spent is unknown: no further search).
   - With no line-up left and no try's out, the record is a minimal no-package dict.
   - The --from-candidate outcome, the record's seeding and the registry save all run AFTER package.json is written,
     in one guarded block: a failure there is logged and the record stands.
F4 (grok C1 P2, glm C2 P2): the --from-candidate record lacked candidate_tries; it now has one entry.
Tests: test_candidates 8 (new: time sort across offsets, and a missing time; an out-of-range judged count charges all).
All 13 suites OK.

Check in particular: that F1 really orders by time and that a malformed time still refuses before anything is written;
that F2 can never let the candidates plus the angle build exceed 8 judged line-ups; that F3 never closes or rests a
candidate on a crash, never loses package.json, and that the driver cannot crash on the new paths; F4's record shape.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


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
