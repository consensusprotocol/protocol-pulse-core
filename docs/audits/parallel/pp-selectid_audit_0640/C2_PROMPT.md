# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0640
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 351 s finish=stop usage in 12406 / out 9645 usd~0.182 (upper-bound price)

# Audit: pp-selectid-0640 — step-A verdict handling in the build loop

Scope: only the diff provided (pipeline/package.py, tests/package/test_medley.py). Where the diff doesn't show a function's body (prescreen, swap_lineup, CI.a_failures, the surrounding build loop), I flag it as unverifiable rather than guess.

---

## P0 findings

None. I could not construct a scenario from the diff alone where a clip reaches the angle prompt or a line-up without two passing verdicts, or where the gates' verdict is on the writer's vendor, that the code as shown doesn't handle.

---

## P1 findings

**P1-1. `second_screen` silently drops clips whose first verdict's back-end is unknown from the *pass* path, but they are also absent from the parallel jobs — correctness OK, yet the `None` group's failure is recorded only after the parallel phase, and the `groups`/`jobs` construction can double-count nothing but can *lose* the `n` cap.**
File: pipeline/package.py, new lines 19–28 of second_screen (diff lines 19–28).

Scenario: `jobs` is built with `n=len(chunk)` per group, so each group's batch is screened with `n` = the group's size. But `prescreen`'s signature (diff line 5, unchanged) shows `n=PRESCREEN_N` as the default; the original call site (diff line 96, old) did **not** pass `n`, meaning the old behaviour capped the re-screen at PRESCREEN_N. The new pre-angle call passes `n=len(chunk)` — if `PRESCREEN_N < PRESCREEN_BATCH` and a group exceeds PRESCREEN_N, the pre-angle second screen now screens more clips than the first screen did. That's likely intended ("it is 10-13 clips, cheap"), but it changes spend: the first screen (unchanged, presumably still capped at PRESCREEN_N) and the second screen can now disagree about which clips were screened at all. If `prescreen` truncates `ms[:n]` (as the rig's stub does, test line 174: `for m in ms[:n]`), a clip beyond the cap in the *first* screen would have no first verdict in `a_by` at all — and `second_screen` would then read `(a_by.get(mid) or {}).get("backend")` → `None` → STEP_A_UNKNOWN_BACKEND, failing a clip that was never screened once. That is fail-closed, so not a correctness bug, but it's a behavioural coupling worth confirming: **is `PRESCREEN_N >= len(cleared)` guaranteed at this call site?** I cannot verify from the diff; if not, clips can be failed as "unknown backend" when the real cause is the cap.

Wait — re-reading: the first screen's call site is not in the diff (it's above the shown hunk at line 50). So this is conditional. Downgrade to: **verify PRESCREEN_N covers the cleared pool, else the UNKNOWN_BACKEND reason masks a cap truncation.** P1 because the reason string would mislead the 06:22 post-mortem trail.

**P1-2. `off_writers` picks the *first* qualifying verdict, not the *latest* — after a write adds a vendor, a clip can be judged by a verdict that is off the new writer's vendor but on the *first* writer's... no, it checks both. Real issue: `off_writers` never re-checks that the chosen verdict's back-end differs from the writers' *family* when the family set grows via `writers_f.add(wr.family)` where the family equals another vendor's family.**
File: package.py, diff lines 74–83 and 91–92.

`off_writers` skips a verdict if `b.vendor in writers_v or b.family in writers_f`. Consider: angle from heimdall:deepseek → writers_v={"heimdall"}, writers_f={"deepseek"}. A clip's passing verdicts are [xai:grok (first), heimdall:deepseek (second)]. `off_writers` returns the xai:grok verdict. Good. Now a write comes from heimdall:qwen → writers_f={"deepseek","qwen"}, writers_v={"heimdall"}. The clip's verdicts: xai:grok (vendor xai ∉ writers_v, family grok ∉ writers_f) → still chosen. Good. But: angle from **xai:grok** → writers_v={"xai"}, writers_f={"grok"}. Passing verdicts [xai:grok, heimdall:deepseek]. `off_writers` returns heimdall:deepseek. Then a write from heimdall:deepseek adds vendor "heimdall", family "deepseek" → now BOTH of the clip's verdicts are on a writer's vendor/family (xai:grok: vendor xai ∈ writers_v? writers_v={"xai","heimdall"} yes; heimdall:deepseek: vendor heimdall ∈ writers_v yes). `off_writers` returns None → `a_by[mid] = off_writers(mid) or a_by[mid]` keeps the **stale** heimdall:deepseek verdict — which is now on the writer's vendor. The very next lines (diff 93–94) compute `stale` with exactly this test, so the clip is correctly re-screened. So the `or a_by[mid]` fallback is only a transient inconsistency, immediately corrected by the stale check. **However**: the fallback `off_writers(mid) or a_by[mid]` at diff line 83 (before any write, right after the angle call) has no following stale re-screen in the same iteration — the stale re-screen happens only after a *write*. Between the angle call and the first write, the gates therefore judge with `a_by[mid]` which — when the angle came from heimdall:deepseek and the clip's secon

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 36 s finish=stop usage in 12428 / out 652 usd~0.078 (upper-bound price)

**P0: none**

**P1: none**

**P2:**
- pipeline/package.py:54 (build): second_screen is called on all CUTTABLE moments after hook-onset but before the 3-channel check and angle_write. The subsequent `cleared = {mid: m for mid, m in cleared.items() if mid in a_two}` filter guarantees no moment reaches the angle prompt (or any later lineup) without two passing verdicts; the test at test_medley.py:226-235 verifies this both in the prompt content and in medley_calls.
- pipeline/package.py:74 (off_writers): after angle_write and after every write (lines 82, 91), a_by[mid] is overwritten with the first verdict from a_two whose backend is outside the accumulating writers_v/writers_f sets. When the writer is xai:grok the Heimdall verdict is selected (and vice-versa); the rig test at test_medley.py:249-253 confirms no re-screen occurs in the Heimdall-in-time case and that the final a_seen backends match the off-writer choice.
- pipeline/package.py:110 (re-screen block): if prescreen returns no verdict or any failure for a stale clip, it is added to `bad`, recorded in out["prescreen"]["rescreen_failed"], added to both `dropped` and `doomed`, and excluded from every subsequent angle/line-up. swap_lineup is called on exactly those bad mids only; the test at test_medley.py:262-270 exercises the exact 05:48 failure mode (one clip fails re-screen → single swap → new lineup re-judged on clips-alone before next write) and confirms the final package contains only the surviving clips.
- pipeline/package.py:34 (second_screen): explicit fail-closed paths for no a2, fails.get(mid), same-vendor/family backend, or unknown first backend produce STEP_A_UNAVAILABLE / STEP_A_SAME_VENDOR / STEP_A_UNKNOWN_BACKEND entries; test at test_medley.py:282-304 verifies the grouping, the same-vendor detection, and that these never become passes.
- pipeline/package.py:25 (ThreadPoolExecutor): jobs are independent (per first-verdict vendor/family group), submitted with store=None, results collected sequentially via .result() after all futures complete; no mutable state (two/fail/a_by/cleared) is written inside the worker threads. No infinite loop, double-counting of moments, or inconsistent a_two/a_by mutation is present in the diff.
- tests/package/test_medley.py:209 (Rig.prescreen): the canned prescreen respects the avoid-vendor/family contract, can simulate a third vendor for the “both real vendors are writers” case, and drives all new test methods; the existing 78 tests remain green and the other test suites are stated unchanged.

All checked laws (L-m, L-x, L-j, item 44, item 45, fail-closed on missing verdict, dynamic off-writer selection after writes) are satisfied by the diff. No behaviour change for the Heimdall-in-time angle path is introduced beyond the guaranteed off-vendor verdict.

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 99 s finish=stop usage in 13481 / out 3341 usd~0.091 (upper-bound price)

# Audit: pp-selectid-0640 (Step-A Dual-Vendor Verdicts)

## P0 Findings

**None.** The core safety invariants (L-m fail-closed, L-x vendor separation, item 44/45 ordering) are correctly implemented. The critical fail-open bug (K2: stale verdict reused when re-screen returns nothing) is fixed. No clip can reach the angle prompt or a line-up without passing step A on both vendors.

## P1 Findings

### P1-1: `second_screen` — unhandled exception in `f.result()` aborts the entire build
**File:** `pipeline/package.py`, line 28 (in `second_screen`)

```python
res = [f.result() for f in futs]
```

If any `prescreen` call raises an uncaught exception (network timeout, provider crash, JSON parse error in the router), `f.result()` re-raises it. This propagates out of `second_screen` → out of `build()` → the entire build crashes with a traceback rather than failing closed with a structured `out["why_none"]` or `out["prescreen"]["second_vendor"]` entry.

**Scenario:** Heimdall's GPU node is under load; the second-screen batch for the `xai` group times out after 300 s. The `ThreadPoolExecutor` future holds a `TimeoutError`. `f.result()` raises it. The build dies. No package, no structured log, no `ATTESTATION.json`.

**Law violated:** M12 (fail closed — an exception should reject, not crash the process). The rest of `build()` handles provider failures gracefully (the `prescreen` function itself catches per-clip failures into `fails`), but the *orchestration* of parallel calls does not.

**Fix:** Wrap `f.result()` in a try/except per future; on exception, mark all clips in that chunk as `STEP_A_UNAVAILABLE: <exception>`.

---

### P1-2: `second_screen` — `a_by[mid]` is read without a guard for missing keys
**File:** `pipeline/package.py`, line 40 (in `second_screen`)

```python
two[mid] = [a_by[mid], a2]
```

The function iterates `cleared.items()` and looks up `a_by.get(mid)` on line 21 (safe, returns `None`), but on line 40 it does a direct `a_by[mid]` index. If `a_by` does not contain a key for a moment in `cleared` (e.g., the first `prescreen` call in `build()` failed to produce a verdict for that moment but it was still added to `cleared` by an earlier stage), this raises `KeyError`.

**Scenario:** A moment passes L-v 2 and CUTTABLE but the first `prescreen` batch had a transient error that was swallowed (the `prescreen` function returns it in `fails`, but `build()` may have added it to `cleared` before checking `fails` — this depends on code not in the diff). If `a_by` lacks the key, `second_screen` crashes.

**Mitigating factor:** The diff shows `a_by` is populated by the first `prescreen` call in `build()` (line 54 context: `a_by` is passed in). If the first screen always populates `a_by` for every moment in `cleared`, this is safe. But the code does not enforce this invariant.

**Fix:** Use `a_by.get(mid)` and treat `None` as `STEP_A_UNKNOWN_BACKEND`.

---

### P1-3: `off_writers` — `writers_f` is a set of families, but `b.family not in writers_f` may not match the intended semantics
**File:** `pipeline/package.py`, line 79 (in `off_writers`)

```python
if b is not None and b.vendor not in writers_v and b.family not in writers_f:
```

`writers_f` is built as `{angle_reply.family}` (line 72) and then `writers_f.add(wr.family)` after each write (line 90). The check `b.family not in writers_f` is correct *if* `writers_f` contains all families that have written. However, the initial `writers_f = {angle_reply.family}` only captures the angle writer's family. If the angle writer is `heimdall:deepseek` (family `deepseek`), and a later write is by `heimdall:qwen` (family `qwen`), then `writers_f = {"deepseek", "qwen"}`. A verdict from `xai:grok` (family `grok`) passes. This is correct.

But consider: the angle writer is `xai:grok` (vendor `xai`, family `grok`). `writers_v = {"xai"}`, `writers_f = {"grok"}`. A verdict from `heimdall:deepseek` (vendor `heimdall`, family `deepseek`) passes both checks. Correct.

**No bug here.** Retracting this finding. The logic is sound.

---

### P1-4: Re-screen after write — `a_two.setdefault(mid, []).append(got_a[mid])` may append a verdict that is *on* a writer's vendor
**File:** `pipeline/package.py`, line 109 (in the re-screen block)

```python
a_two.setdefault(mid, []).append(got_a[mid])
```

The re-screen calls `prescreen(router, stale, sources, ctx, writers_v, writers_f, ...)`, which avoids `writers_v` and `writers_f`. So `got_a[mid]` should be off the writers. However, `a_two` is also used by `off_writers` (line 77), which iterates `a_two.get(mid, ())` and checks `b.vendor not in writers_v and b.family not in writers_f`. If a *later* write adds a new vendor/family to `writers_v`/`writers_f`, a verdict that was off the writers *at the time it was added* may now be *on* a writer. `off_writers` handles this correctly (it re-checks against the current `writers_v`/`writers_f`),

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0640 (ORDER 06:22 items 45 and 44): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers package.py and test_medley.py. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- qwen: "SHIP: yes with conditions" (its P1-1 and P1-2);
- glm: "SHIP: yes with conditions" (four conditions); no P0.

## Consensus: IMPLEMENTED

| # | finding (reviewers) | change |
|---|---|---|
| F1 | An exception out of one parallel prescreen call would crash the whole build, not fail its clips closed (qwen P1-1, glm P1-3 / condition 4's spirit) | second_screen runs each chunk through one(): a raising chunk returns STEP_A_UNAVAILABLE: <exception> for each of its clips, never a pass, never a crash. Tested (a raising prescreen fails all four clips closed). |

## Single-reviewer findings: IMPLEMENTED (no change to what any check accepts)

| # | finding | change |
|---|---|---|
| S1 | glm P2-8: the STEP_A_SAME_VENDOR reason says "not off the first's vendor" while the check also compares the family | the reason names both ("not off the first's vendor X and family Y"). |
| S2 | glm P2-9: the "no swap fits -> re-lined" branch of item 44 is untested | tested: y fails its re-screen, no clip can replace it, the line-up re-lines, y stays out (rescreen_failed), no second line-up is judged. |
| S3 | glm condition 1: the both-writers case is tested only with the rig's third vendor | the production-shape fact is now asserted: when Grok writes the angles, every write avoids Heimdall (rig.write_avoid == [{"heimdall"}]). See K3. |

## Misreadings and non-defects (verified from the code)

| # | claim | the code |
|---|---|---|
| K1 | qwen P1-2: `two[mid] = [a_by[mid], a2]` can raise KeyError | second_screen groups a clip by `a_by.get(mid)`'s back-end; a clip with no first verdict lands in the None group, which never reaches that line. Also build() makes `cleared` from `a_by` (`m["moment_id"] in a_by and not fails...`), so every cleared clip has a first verdict. |
| K2 | glm P1-1: a clip beyond PRESCREEN_N could reach second_screen without a first verdict and read as UNKNOWN_BACKEND | `cleared` holds only moments the first screen answered and passed (same line as K1). second_screen passes n=len(chunk), so nothing of a chunk is truncated. |
| K3 | glm P2-3: with both vendors writing, the re-screen has no back-end, and the swap could loop | (1) It cannot arise with the configured chains. writer_avoid = the angle_write chain's vendors minus the angle's vendor, and write_takeaway passes it to router.call (package.py, write_takeaway: `avoid_vendor=avoid_vendor`). After a Grok angle, no write can come from Heimdall, so the writers stay one vendor. Now asserted (S3). (2) It is bounded anyway. Each failed re-screen adds its clips to `doomed`, the swap and re-line exclude `dropped \| doomed`, and `total < lineups` (8) plus the search budget stop the loop. The rig's third vendor exercises item 44's mechanics for a future chain with t

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0640/C2_STEP.diff (342 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index d266dbe..27dfb5b 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -444,6 +444,48 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
   6 |      return a_by, fails, vendors, families
   7 |  
   8 |  
   9 | +def second_screen(router, cleared, a_by, sources, ctx, log=print):
  10 | +    """ORDER 06:22 item 45: step A from a SECOND vendor on every cuttable clip, BEFORE the angle step. The writer is
  11 | +    known only when the angle call answers (Heimdall first, Grok on its failure: angle_write), and a verdict never
  12 | +    comes from the writer's vendor (L-x). The only step-A vendors are the writers' own two (context_verdict: xai, then
  13 | +    heimdall), so each clip is screened again OFF its first verdict's vendor and family: whichever vendor then writes,
  14 | +    a verdict off it already exists, and no line-up is built on a clip that a re-screen would fail (the 05:48 build).
  15 | +    The clips are grouped by their first verdict's back-end, and the groups' step-A batches run in parallel (each
  16 | +    call takes about 3 min on Heimdall). -> ({moment id: [first verdict, second verdict]} for the clips that pass
  17 | +    both, {moment id: [why not]} for the rest). No second verdict, a failing one, or one from the first's vendor or
  18 | +    family is never a pass (law L-m)."""
  19 | +    groups = {}
  20 | +    for mid, m in cleared.items():
  21 | +        b = router.backends.get((a_by.get(mid) or {}).get("backend"))
  22 | +        groups.setdefault((b.vendor, b.family) if b is not None else None, []).append(m)
  23 | +    jobs = [(k, g[i:i + PRESCREEN_BATCH]) for k, g in groups.items() if k is not None
  24 | +            for i in range(0, len(g), PRESCREEN_BATCH)]
  25 | +    def one(k, chunk):                  # a chunk whose screen raises fails closed, never the build (audit 0640 C1)
  26 | +        try:
  27 | +            return prescreen(router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log)
  28 | +        except Exception as e:
  29 | +            return {}, {m["moment_id"]: [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:120]}"]
  30 | +                        for m in chunk}, set(), set()
  31 | +    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as ex:
  32 | +        res = list(ex.map(lambda j: one(*j), jobs))
  33 | +    two, fail = {}, {}
  34 | +    for (k, chunk), (got, fails, _, _) in zip(jobs, res):
  35 | +        for m in chunk:
  36 | +            mid, a2 = m["moment_id"], got.get(m["moment_id"])
  37 | +            b2 = router.backends.get((a2 or {}).get("backend"))
  38 | +            if fails.get(mid) or a2 is None:
  39 | +                fail[mid] = list(fails.get(mid) or ["STEP_A_UNAVAILABLE: no second verdict (law L-m)"])
  40 | +            elif b2 is None or b2.vendor == k[0] or (k[1] and b2.family == k[1]):
  41 | +                fail[mid] = [f"STEP_A_SAME_VENDOR: the second verdict came from {a2.get('backend')}, not off the "
  42 | +                             f"first's vendor {k[0]} and family {k[1]} (law L-m)"]
  43 | +            else:
  44 | +                two[mid] = [a_by[mid], a2]
  45 | +    for m in groups.get(None, []):
  46 | +        fail[m["moment_id"]] = ["STEP_A_UNKNOWN_BACKEND: the first verdict's back-end is unknown, so no second vendor "
  47 | +                                "can be chosen (law L-m)"]
  48 | +    return two, fail
  49 | +
  50 | +
  51 |  ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words. The clips
  52 |  play BACK TO BACK as a medley, with NO narration between them; the host speaks ONE closing line at the end. Below are
  53 |  clips (verbatim quotes, each with its channel and length) that passed our checks. The channels were not in one
  54 | @@ -1251,9 +1293,16 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  55 |      out["prescreen"]["trim_cut"] = trim_cut
  56 |      log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
  57 |          f"(G17a at the pin stage: genuine quiet before the first onset)")
  58 | +    a_two, off_fail = second_screen(router, cleared, a_by, sources, ctx, log=log)        # ORDER 06:22 item 45
  59 | +    out["prescreen"]["second_vendor"] = {mid: f"PASS ({a_two[mid][1].get('backend')})" if mid in a_two else
  60 | +                                         "FAIL: " + "; ".join(off_fail.get(mid) or ["no second verdict"])
  61 | +                                         for mid in cleared}
  62 | +    cleared = {mid: m for mid, m in cleared.items() if mid in a_two}
  63 | +    log(f"  {len(cleared)} of them clear step A from both vendors too (order 06:22 item 45: whichever vendor writes, "
  64 | +        f"a verdict off it exists) ({time.time() - t0:.0f} s)")
  65 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
  66 | -        out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass and CUTTABLE, from fewer than 3 "
  67 | -                           f"channels")
  68 | +        out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass, CUTTABLE and step A from both "
  69 | +                           f"vendors, from fewer than 3 channels")
  70 |          return out
  71 |      clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s | "{quote_data(m["text"], 600)}"'
  72 |                        for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
  73 | @@ -1277,6 +1326,17 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  74 |      out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
  75 |      out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
  76 |      writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
  77 | +
  78 | +    def off_writers(mid):
  79 | +        """ORDER 06:22 item 45: the moment's passing step-A verdict from a back-end off every writer's vendor and
  80 | +        family so far (the first screen's first), else None (the re-screen after a write decides, item 44)."""
  81 | +        for a_ in a_two.get(mid, ()):
  82 | +            b = router.backends.get(a_.get("backend"))
  83 | +            if b is not None and b.vendor not in writers_v and b.family not in writers_f:
  84 | +                return a_
  85 | +        return None
  86 | +    for mid in cleared:
  87 | +        a_by[mid] = off_writers(mid) or a_by[mid]
  88 |      writer_avoid = {router.backends[n].vendor for n in router.chain("angle_write") if n in router.backends} - \
  89 |          {angle_reply.vendor}                   # every write stays on the angle's vendor, so a judge is always left
  90 |      log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)")
  91 | @@ -1483,15 +1543,31 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  92 |                          continue
  93 |                      writers_v.add(wr.vendor)
  94 |                      writers_f.add(wr.family)
  95 | +                    for m in segs:                             # item 45: the verdict off every writer, when one exists
  96 | +                        a_by[m["moment_id"]] = off_writers(m["moment_id"]) or a_by[m["moment_id"]]
  97 |                      stale = [m for m in segs if (lambda b: b is None or b.vendor in writers_v or b.family in writers_f)(
  98 |                          router.backends.get((a_by.get(m["moment_id"]) or {}).get("backend")))]
  99 |                      if stale:                                  # audit C2 K5: never judged by the writer's vendor
 100 | -                        got_a, _, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f, store=None)
 101 | -                        for mid, a_ in got_a.items():
 102 | -                            a_by[mid] = a_
 103 | -                        if any(CI.a_failures(a_by.get(m["moment_id"], {})) for m in stale):
 104 | -                            rec["why"] = "step A, re-screened off the writer's vendor, fails a clip: re-lined"
 105 | -                            dropped |= {m["moment_id"] for m in stale if CI.a_failures(a_by.get(m["moment_id"], {}))}
 106 | +                        got_a, fails_a, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f,
 107 | +                                                         n=len(stale), store=None)
 108 | +                        bad = {}
 109 | +                        for m in stale:
 110 | +                            mid = m["moment_id"]
 111 | +                            if got_a.get(mid) is not None and not fails_a.get(mid):
 112 | +                                a_by[mid] = got_a[mid]
 113 | +                                a_two.setdefault(mid, []).append(got_a[mid])
 114 | +                            else:                              # no verdict off the writers is never a pass (L-m)
 115 | +                                bad[mid] = list(fails_a.get(mid) or ["STEP_A_UNAVAILABLE: no verdict off the writers "
 116 | +                                                                     "(law L-m)"])
 117 | +                        if bad:                                # ORDER 06:22 item 44: only these clips go, for good,
 118 | +                            dropped |= set(bad)                # with their reason; the next-best cuttable clip takes
 119 | +                            doomed |= set(bad)                 # each place (ruling 41's swap); the clips-alone verdict
 120 | +                            out["prescreen"].setdefault("rescreen_failed", {}).update(bad)     # re-judges the line-up
 121 | +                            swapped, swaps = swap_lineup(segs, set(bad), cleared, frozenset(dropped | doomed))
 122 | +                            rec["why"] = (f"step A, re-screened off the writer's vendor, fails {sorted(bad)} (out for "
 123 | +                                          f"good): " + (f"swapped {swaps}, re-judged (order 06:22 item 44)"
 124 | +                                                        if swapped is not None else
 125 | +                                                        "no swap fits the line-up rules: re-lined"))
 126 |                              relined = True
 127 |                              break
 128 |                      if join is not None and fields["bridge"] is None:
 129 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 130 | index 3cb6fa9..34f0a80 100644
 131 | --- a/tests/package/test_medley.py
 132 | +++ b/tests/package/test_medley.py
 133 | @@ -425,23 +425,53 @@ class Rig:
 134 |              "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
 135 |  
 136 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 137 | -                 spend=None, no_hook=()):
 138 | +                 spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None):
 139 |          import providers as P
 140 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 141 |          self.takeaways, self.spend = list(takeaways or []), spend
 142 |          self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 143 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 144 | +        self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 145 | +        self.screens, self.events, self.a_seen = [], [], []
 146 | +        self.write_from = write_from or ("heimdall:deepseek", "heimdall", "deepseek")
 147 |          many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
 148 |          self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}])
 149 |          call = self.router.call
 150 | -        self.router.call = lambda role, prompt, *a, **k: (self.prompts.append((role, prompt)),
 151 | -                                                          call(role, prompt, *a, **k))[1]
 152 | +
 153 | +        def rcall(role, prompt, *a, **k):
 154 | +            self.prompts.append((role, prompt))
 155 | +            self.events.append(role)
 156 | +            r = call(role, prompt, *a, **k)
 157 | +            if role == "angle_write" and angle_from:              # the angle from a named back-end (ORDER 06:22)
 158 | +                r = P.Reply(r.text, angle_from[0], angle_from[1], family=angle_from[2])
 159 | +            return r
 160 | +        self.router.call = rcall
 161 |          B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 162 |          self.router.backends = {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall", "deepseek"),
 163 | -                                "heimdall:qwen": B("heimdall", "qwen")}
 164 | +                                "heimdall:qwen": B("heimdall", "qwen"), "openai:gpt": B("openai", "gpt")}
 165 |          self.router.chain = lambda role: ["heimdall:deepseek", "heimdall:qwen", "xai:grok"]
 166 |          self.write_avoid = []
 167 |  
 168 | +    def prescreen(self, router, ms, sources, ctx_, writer_vendor, writer_family=None, n=PK.PRESCREEN_N,
 169 | +                  batch=PK.PRESCREEN_BATCH, store=None, log=print):
 170 | +        """Step A as the real prescreen calls it: on the first back-end off the given vendors and families
 171 | +        (context_verdict: xai, then heimdall; a third vendor only for the rig); per (vendor, moment) failures."""
 172 | +        av, af = self.P._as_set(writer_vendor), self.P._as_set(writer_family)
 173 | +        name = next((x for x in ("xai:grok", "heimdall:deepseek", "openai:gpt")
 174 | +                     if self.router.backends[x].vendor not in av and self.router.backends[x].family not in af), None)
 175 | +        self.screens.append((name, [m["moment_id"] for m in ms]))
 176 | +        self.events.append(f"step_a:{name}")
 177 | +        got, fails = {}, {}
 178 | +        for m in ms[:n]:
 179 | +            mid = m["moment_id"]
 180 | +            v = self.router.backends[name].vendor if name else None
 181 | +            if name is None or (v, mid) in self.unavailable:
 182 | +                fails[mid] = ["STEP_A_UNAVAILABLE: ProviderError"]
 183 | +                continue
 184 | +            got[mid] = dict(self.A_OK, backend=name)
 185 | +            fails[mid] = list(self.a_fail.get((v, mid), []))
 186 | +        return got, fails, set(), set()
 187 | +
 188 |      def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
 189 |          self.medley_calls.append([m["moment_id"] for m in segs])
 190 |          ok, flagged, ratings, line = self.medleys.pop(0)
 191 | @@ -454,13 +484,14 @@ class Rig:
 192 |              raise PK.NoBridgeFits("no bridge of 3-12 words fits (the real write_takeaway's precondition)")
 193 |          self.write_calls.append(([m["moment_id"] for m in segs], join))
 194 |          self.write_avoid.append(avoid_vendor)
 195 | +        self.a_seen.append({m["moment_id"]: a_by[m["moment_id"]]["backend"] for m in segs})
 196 |          b = self.writes.pop(0)
 197 |          fields = {"takeaway": {"text": self.takeaways.pop(0) if self.takeaways else self.LINE, "cites": []}, "bridge": b,
 198 |                    "bridge_after": join[0] if join is not None and b is not None else None,
 199 |                    "title": {"text": "Nobody bends the rules", "cites": []},
 200 |                    "caption": {"text": "nobody bends these rules", "cites": []},
 201 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
 202 | -        return self.P.Reply("{}", "heimdall:deepseek", "heimdall", family="deepseek"), fields
 203 | +        return self.P.Reply("{}", self.write_from[0], self.write_from[1], family=self.write_from[2]), fields
 204 |  
 205 |      def run(self):
 206 |          fid = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "xai:grok",
 207 | @@ -469,8 +500,7 @@ class Rig:
 208 |          cx = {"ok": True, "violations": [], "measured": True, "replayed": False, "backends": {"B": "xai", "C": "xai"}}
 209 |          stubs = {
 210 |              "_writers": lambda router: ({"heimdall"}, {"deepseek"}),
 211 | -            "prescreen": lambda router, ms, *a, **k: ({m["moment_id"]: dict(self.A_OK) for m in ms},
 212 | -                                                      {m["moment_id"]: [] for m in ms}, set(), set()),
 213 | +            "prescreen": self.prescreen,
 214 |              "current_levels": lambda *a, **k: [],
 215 |              "medley": self.medley, "write_takeaway": self.write,
 216 |              "paid_gates": lambda *a, **k: (fid, cx),
 217 | @@ -837,6 +867,124 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 218 |          self.assertIsNotNone(out["package"])
 219 |  
 220 |  
 221 | +class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 222 | +    """ORDER 06:22: 45, step A from BOTH vendors on every cuttable clip before the angle step; 44, a failed re-screen
 223 | +    after a write swaps out that clip only, and the line-up carries on."""
 224 | +    MS = TestBuildLoop.MS
 225 | +
 226 | +    def test_every_cuttable_clip_is_screened_by_the_second_vendor_before_the_angle_step(self):
 227 | +        rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None],      # the writer never sees y
 228 | +                  a_fail={("heimdall", "y"): ["REFERENT_OUTSIDE"]})
 229 | +        out = rig.run()
 230 | +        self.assertEqual(rig.screens[0], ("xai:grok", ["h", "x", "y", "z"]))          # the first screen, off heimdall
 231 | +        self.assertEqual(rig.screens[1], ("heimdall:deepseek", ["h", "x", "y", "z"]))  # the second, off xai
 232 | +        self.assertLess(rig.events.index("step_a:heimdall:deepseek"), rig.events.index("angle_write"))
 233 | +        sv = out["prescreen"]["second_vendor"]
 234 | +        self.assertEqual(sv["h"], "PASS (heimdall:deepseek)")
 235 | +        self.assertTrue(sv["y"].startswith("FAIL: REFERENT_OUTSIDE"), sv["y"])
 236 | +        angle_prompt = next(p for r, p in rig.prompts if r == "angle_write")
 237 | +        self.assertNotIn("id=y ", angle_prompt)                    # never offered to the angles
 238 | +        self.assertIn("id=z ", angle_prompt)
 239 | +        self.assertEqual(rig.medley_calls, [["h", "x", "z"]])     # no line-up is built on it
 240 | +        self.assertIsNotNone(out["package"])
 241 | +
 242 | +    def test_a_clip_with_no_second_verdict_is_out(self):           # law L-m: nothing measured is never a pass
 243 | +        rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None],
 244 | +                  unavailable={("heimdall", "y")})
 245 | +        out = rig.run()
 246 | +        self.assertTrue(out["prescreen"]["second_vendor"]["y"].startswith("FAIL: STEP_A_UNAVAILABLE"))
 247 | +        self.assertEqual(rig.medley_calls, [["h", "x", "z"]])
 248 | +
 249 | +    def test_the_verdict_used_is_the_one_off_the_writers_vendor(self):
 250 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
 251 | +        rig.run()                                                  # the angle from vendor "fake": the first verdict
 252 | +        self.assertEqual(set(rig.a_seen[0].values()), {"xai:grok"})
 253 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 254 | +                  angle_from=("xai:grok", "xai", "grok"), write_from=("xai:grok", "xai", "grok"))
 255 | +        out = rig.run()                                            # Grok wrote the angles: Heimdall's verdict counts
 256 | +        self.assertEqual(set(rig.a_seen[0].values()), {"heimdall:deepseek"})
 257 | +        self.assertEqual(rig.write_avoid, [{"heimdall"}])          # and every write avoids Heimdall, so with the two
 258 | +        # real vendors the writers never span both and a verdict off them always exists (audit 0640 C1, glm cond. 1)
 259 | +        self.assertEqual(len(rig.screens), 2)                      # and no re-screen was needed after the write
 260 | +        self.assertIsNotNone(out["package"])
 261 | +
 262 | +    def test_a_clip_that_fails_its_re_screen_is_swapped_out_alone_and_the_line_up_carries_on(self):
 263 | +        """The 05:48 build: a line-up passed the clips-alone verdict, a re-screen failed ONE clip, and the line-up was
 264 | +        lost. Now only that clip goes (for good, with its reason), the next-best clip takes its place, the clips-alone
 265 | +        verdict re-judges, and the build goes on to the writer. (Both vendors write here, so the rig's third vendor
 266 | +        re-screens.)"""
 267 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
 268 | +                  [None, None], angle_from=("xai:grok", "xai", "grok"), a_fail={("openai", "y"): ["REFERENT_OUTSIDE"]})
 269 | +        out = rig.run()
 270 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])
 271 | +        self.assertEqual(out["prescreen"]["rescreen_failed"], {"y": ["REFERENT_OUTSIDE"]})
 272 | +        self.assertIn("swapped {'y': 'z'}", out["tried"][0]["why"])
 273 | +        self.assertIn("(out for good)", out["tried"][0]["why"])
 274 | +        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "z"])
 275 | +        self.assertEqual(rig.screens[2], ("openai:gpt", ["h", "x", "y"]))         # every verdict on a writer's vendor
 276 | +        self.assertEqual(rig.screens[3], ("openai:gpt", ["z"]))                   # only what changed is re-judged
 277 | +
 278 | +    def test_a_re_screen_that_gives_no_verdict_is_never_a_pass(self):
 279 | +        """The old branch read the stale verdict back when the re-screen returned nothing for a clip (a fail-open,
 280 | +        flagged with ORDER 06:22): no verdict off the writers keeps the clip out."""
 281 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
 282 | +                  [None, None], angle_from=("xai:grok", "xai", "grok"), unavailable={("openai", "y")})
 283 | +        out = rig.run()
 284 | +        self.assertEqual(list(out["prescreen"]["rescreen_failed"]), ["y"])
 285 | +        self.assertTrue(out["prescreen"]["rescreen_failed"]["y"][0].startswith("STEP_A_UNAVAILABLE"))
 286 | +        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "z"])
 287 | +
 288 | +    def test_when_no_swap_fits_the_line_up_re_lines_and_the_clip_stays_out(self):     # audit 0640 C1, glm P2-9
 289 | +        rig = Rig(self.MS, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], uncuttable={"z"},   # z never offered
 290 | +                  angle_from=("xai:grok", "xai", "grok"), a_fail={("openai", "y"): ["REFERENT_OUTSIDE"]})
 291 | +        out = rig.run()
 292 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])     # nothing else fits: no second line-up is judged
 293 | +        self.assertIn("no swap fits the line-up rules: re-lined", out["tried"][0]["why"])
 294 | +        self.assertEqual(out["prescreen"]["rescreen_failed"], {"y": ["REFERENT_OUTSIDE"]})
 295 | +        self.assertIsNone(out["package"])
 296 | +
 297 | +    def test_a_chunk_whose_second_screen_raises_fails_closed(self):     # audit 0640 C1, qwen P1-1 / glm P1-3
 298 | +        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 299 | +        router = type("R", (), {"backends": {"xai:grok": B("xai", "grok")}})()
 300 | +
 301 | +        def boom(*a, **k):
 302 | +            raise RuntimeError("the router is unreachable")
 303 | +        saved = PK.prescreen
 304 | +        PK.prescreen = boom
 305 | +        try:
 306 | +            two, fail = PK.second_screen(router, {m["moment_id"]: m for m in self.MS},
 307 | +                                         {m["moment_id"]: {"backend": "xai:grok"} for m in self.MS}, {}, ctx())
 308 | +        finally:
 309 | +            PK.prescreen = saved
 310 | +        self.assertEqual(two, {})
 311 | +        self.assertEqual(sorted(fail), ["h", "x", "y", "z"])
 312 | +        self.assertTrue(all(f[0].startswith("STEP_A_UNAVAILABLE: RuntimeError") for f in fail.values()))
 313 | +
 314 | +    def test_second_screen_fails_closed_on_an_unknown_back_end_or_the_same_vendor(self):
 315 | +        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 316 | +        router = type("R", (), {"backends": {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall",
 317 | +                                                                                                  "deepseek")}})()
 318 | +        ms = {m["moment_id"]: m for m in self.MS}
 319 | +        a_by = {"h": {"backend": "xai:grok"}, "x": {"backend": "xai:grok"}, "y": {"backend": "nowhere:model"},
 320 | +                "z": {"backend": "heimdall:deepseek"}}
 321 | +        seen = []
 322 | +
 323 | +        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print):
 324 | +            seen.append((sorted(wv), [m["moment_id"] for m in chunk]))
 325 | +            name = "heimdall:deepseek" if "xai" in wv else "heimdall:deepseek"     # z's second verdict: same vendor
 326 | +            return {m["moment_id"]: {"backend": name} for m in chunk}, {m["moment_id"]: [] for m in chunk}, set(), set()
 327 | +        saved = PK.prescreen
 328 | +        PK.prescreen = fake
 329 | +        try:
 330 | +            two, fail = PK.second_screen(router, ms, a_by, {}, ctx())
 331 | +        finally:
 332 | +            PK.prescreen = saved
 333 | +        self.assertEqual(sorted(seen), [(["heimdall"], ["z"]), (["xai"], ["h", "x"])])   # grouped by first vendor
 334 | +        self.assertEqual(sorted(two), ["h", "x"])
 335 | +        self.assertTrue(fail["y"][0].startswith("STEP_A_UNKNOWN_BACKEND"))
 336 | +        self.assertTrue(fail["z"][0].startswith("STEP_A_SAME_VENDOR"))
 337 | +
 338 | +
 339 |  class TestRuling41Search(unittest.TestCase):
 340 |      """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 341 |      place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 342 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
This branch builds sealed pins of short video medleys (a hook + 2-4 clips from other channels); the integrator
renders them. Your role: a strict reviewer of the build loop's step-A verdict handling.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- Step A (law L-s) is a per-clip context verdict: who speaks, whose view, outside referents, retractions. It runs ONCE
  per moment per build, batched (PRESCREEN_BATCH = 8 excerpts per call), on the router's "context_verdict" chain.
- Law L-x: a verdict never comes from the WRITER's vendor or model family. The writer is the "angle_write" chain:
  Heimdall deepseek, then Heimdall qwen, then xai Grok, each with a 300 s deadline (ruling 5). The context_verdict
  chain is xai Grok, then Heimdall deepseek. There are only these two vendors.
- Before this change: step A ran off the EXPECTED writer's vendor (Heimdall), so on xai. When the angle call failed
  over to Grok (xai), every verdict was on the writer's vendor, and the build re-screened a line-up's clips off xai
  only AFTER the line-up passed the clips-alone verdict and its first write. In the 05:48 build that re-screen failed
  ONE clip, the whole line-up was discarded ("re-lined"), and no other line-up fit: no package.
- Laws: nothing measured is never a pass (L-m); fail closed (L-j); never change what a check accepts to make
  something pass.

The orders this diff implements (ORCHESTRATOR ORDER 06:22, verbatim):
44. "A failed re-screen removes that clip only (it stays out for good, with its reason). The other three had passed:
    swap in the next-best cuttable clip for the failed slot (ruling 41's swap), re-judge only what changed (the new
    clip's step A on both vendors, the clips-alone verdict), and carry on to the writer. Never discard a passing
    line-up for one replaceable clip."
45. "Run the off-vendor step A re-screen on every CUTTABLE clip BEFORE the angle step, so no line-up is ever built on
    a clip that will fail it. It is 10-13 clips, cheap, and it ends this failure class."

The change (pipeline/package.py):
1. second_screen(router, cleared, a_by, sources, ctx): groups the cuttable clips by their FIRST verdict's back-end
   (vendor, family), and screens each group again with prescreen() avoiding that vendor and family. The batches run
   in parallel (a Heimdall step-A call takes about 3 min). It returns {id: [first verdict, second verdict]} for clips
   passing both, and {id: [why not]} for the rest. Fail closed: no second verdict (STEP_A_UNAVAILABLE), a failing one,
   one from the first's vendor or family (STEP_A_SAME_VENDOR), or an unknown first back-end (STEP_A_UNKNOWN_BACKEND).
2. build(): after L-v 2 + CUTTABLE and the hook-onset stage, BEFORE the 3-channel check and the angle call, only the
   clips in second_screen's first result stay in `cleared`. out["prescreen"]["second_vendor"] records PASS (backend)
   or FAIL with the reasons.
3. After the angle call: off_writers(mid) returns the first of the clip's passing verdicts whose back-end is off every
   writer's vendor and family so far, and a_by[mid] takes it.
4. After each write (a write may add a vendor or family to the writers): a_by is re-picked with off_writers for the
   line-up. Any clip still on a writer's vendor or family ("stale") is re-screened (prescreen avoiding all writers).
   A clip whose re-screen fails OR gives no verdict is out for good (dropped and doomed, with its reasons in
   out["prescreen"]["rescreen_failed"]). The line-up is then swapped with ruling 41's swap_lineup at those places,
   and the loop judges the swapped line-up on the clips alone next, then writes. If no swap fits, it re-lines as
   before.
   - A K2 flag fixed here: the old branch assigned a_by only for the clips the re-screen returned, then tested
     CI.a_failures(a_by[...]). A clip whose re-screen call failed (no verdict) kept its STALE verdict from the
     writer's vendor and passed. Now no verdict is never a pass.

The tests (tests/package/test_medley.py):
- The build test rig's step A is now vendor-aware: like the real prescreen through the router, it answers on the
  first back-end off the given vendors and families (xai, then heimdall; a third vendor "openai" exists only in the
  rig, to exercise item 44 when both real vendors are writers). Its failures are set per (vendor, moment).
- New tests: the second screen runs on Heimdall over every cuttable clip before the angle call; a clip failing it, or
  with no second verdict, is never offered to the angles or a line-up; the verdict used is the one off the writer's
  vendor (Grok writing -> Heimdall's verdict, with no re-screen); a re-screen failing one clip swaps it out alone and
  the line-up carries on to a package, re-screening only the new clip; a re-screen with no verdict keeps the clip out;
  second_screen fails closed on an unknown back-end or a same-vendor answer.
- test_medley: 78 tests OK (72 before). The other suites (angles, gates, hook_onset, house_style, ledger_build,
  speakers, providers, moments, eligibility, select_by_id) are unchanged and OK.

Check in particular:
- that NO clip reaches the angle prompt or any line-up without a passing step-A verdict from each of the two vendors
  (items 45, L-m), and that the verdict actually used by the gates is off every writer's vendor and family (L-x),
  also after a write adds a vendor or family;
- that a failed or missing re-screen removes ONLY that clip, keeps it out of every later angle and line-up with its
  reason, and that the swapped line-up is judged on the clips alone before any write (item 44);
- the threading in second_screen: shared state, exceptions, ordering;
- anything that could loop, double-count spend, or leave `cleared`, `a_by` or `a_two` inconsistent;
- whether any existing behaviour changed for a build where the angle comes from Heimdall in time.

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
