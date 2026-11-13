# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1420
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 745 s finish=length usage in 15971 / out 24000 usd~0.408 (upper-bound price)

# Audit: pp-selectid — Ruling 66 candidate registry (candidates.py, package.build, proof_ledger)

Scope: I reviewed only the diff provided. I verified the state machine, seeding, budget accounting and driver flow against the 14:02 ruling text and the stated readings K1–K5. Where the diff references code not shown (e.g. `package.load_candidate`, `Rig`, `medley()`), I note it as unverifiable rather than guessing.

## P0

None found.

## P1

**P1-1 — `candidates.due` sorts by `found_at` string, but `found_at` can be `None` or differently-formatted, silently breaking "newest first".**
`candidates.py:103` sorts on `(str(found_at), source, index)`. `found_at` comes from `record.get("now")` (`candidates.py:70`), which is only guaranteed to exist if every historical `package.json` has a `now` key. If any of the 38 records lacks `now`, `found_at` is `None`, `str(None)` = `"None"`, which sorts **before** every ISO timestamp (since "N" < "2"), so that candidate would be tried *first*, not last — inverting "newest first" for that entry. Also, if any record's `now` was written with a different ISO format (e.g. no timezone, or space separator), lexicographic comparison of the strings is not chronological. Concrete scenario: a record with `now` = `"2026-11-13T09:22:00"` (no `+00:00`) vs another with `"2026-11-13T09:22:00+00:00"`; the naive one sorts after the aware one at the same second, and across records the ordering can be wrong. The ruling says "newest first" without qualification. Fix: parse with `_at()` in the sort key (falling back to a sentinel) instead of comparing formatted strings. (I cannot verify the actual format of the 38 records from the diff; this is conditional on format variance, but the `None` case is real: `record.get("now")` has no default.)

**P1-2 — `run_due` decrements the judged-line-up budget by what the *candidate try* reports, but a candidate try that fails before any line-up is judged reports 0, and the driver's fallback then gives the angle build the full 8 — correct — yet a candidate try that judges some line-ups *and* the angle build afterwards can exceed 8 total.**
Wait — re-reading: `run_due` receives `lineups` and decrements; the driver then passes `left` to the angle build. So the total is 8 across all builds. That part is consistent. The subtler issue: `try_one` in `proof_ledger.py` (line ~306) returns `judged = (o.get("search") or {}).get("lineups", 0)`. `out["search"]["lineups"]` is `total` in `package.build` (line 202 of the diff context: `out["search"] = {"lineups": total, ...}`), which counts **all** line-ups judged in that build — including, I infer, line-ups judged *before* the candidate stage? No: with `candidate=...`, build tries only that line-up, so `total` should be 0 or 1. But the diff does not show where `total` is incremented, so I cannot verify that a candidate build's `search.lineups` is exactly 1 when the candidate is judged and 0 when it fails before judging (e.g. "does not open on its angle's hook" — closed as "clip" before any pool stage). If `total` counts the candidate's own line-up as judged even when the candidate fails pre-judgement (hook-open failure), the budget is over-decremented; if it counts 0 when the candidate *was* judged, the budget is under-decremented and the build could exceed 8 judged line-ups total. **Unverifiable from the diff** — the increment site of `total` is not shown. Flagging as P1 because the ruling's "inside the 8 judged line-ups" (K4) depends on it. Recommend: assert in the driver that `sum(judged) + angle_build.lineups <= 8`.

**P1-3 — `seed()` applies a legacy record's candidate outcome even when the same record's tried entry was just added as a *new* candidate, potentially closing a freshly-seeded candidate from a pre-registry try whose outcome was "line"→resting, then... actually this is the intended path.** Let me re-examine: `seed()` (candidates.py:84-90) applies `record["candidate"]`'s outcome when `not record.get("registry")`. The guard `reg["candidates"][k]["state"] != "closed"` means a "line" outcome on a just-seeded open candidate sets it to "resting" — correct per 14:02. But: the legacy record's `candidate` outcome is applied **even if the record's tried entry with that line-up did not have `medley_ok`** — no wait, the legacy try's line-up must have passed earlier to be a candidate at all; if the line-up never passed, it's not in the registry and the outcome is silently dropped (line 87: `if k in reg["candidates"]`). Is that right? A pre-registry try of a line-up that passed in an *even earlier* record: the earlier record seeds the candidate; the later legacy try's outcome applies. But if the later legacy try's line-up passed in the *same* record's tried list *and* was tried as a candidate in the same record — the tried entry has `candidate` flag set (line 75: `t.get("candidate") is not None` → `continue`), 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 32 s finish=stop usage in 15833 / out 330 usd~0.087 (upper-bound price)

**P0: none**  
**P1: none**  
**P2: pipeline/package.py:199** (the final "class" ternary can only be verified to produce "line" when medley_ok+attempts+not-relined are all true on the candidate's tried entry and no package/budget_stop occurred; the exact definition of "attempts" and interaction with rewrite_alone/relined= is outside this diff and must be confirmed against the full medley path).  
**P2: tests/package/proof_ledger.py:290** (when --from-candidate is used the registry outcome is written but "candidate_tries" and "registry":True are never added to the record; the non-candidate path always adds them).  
**P2: pipeline/candidates.py:101** (_at() + timedelta assumes every "until" string is a valid ISO timestamp with Z or offset; malformed legacy registry entries would raise at due() time).  

All other aspects (state machine exactly matching the 14:02 "resting 6 h then one fresh-write try → closed", due() newest-first snapshot preventing double-tries, shared 8-judged-lineup budget via run_due → remaining build, read-before-write + atomic registry save, write_seed=1000 isolating fresh writes while preserving verdict seed, seed() deduplication, candidate vs non-candidate paths, test coverage of the four outcome classes) verify cleanly from the diff. Real-data seeding behavior (old candidates closed as "clip" by current load_candidate) also matches K2.  

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 41 s finish=stop usage in 17498 / out 2491 usd~0.090 (upper-bound price)

# Code Audit: pp-selectid-1420 (Ruling 66 Implementation)

## P0 Findings

**1. `pipeline/candidates.py:101` — Timezone Naive/Naive Comparison Crash**
The `due()` function compares `e["until"]` (an ISO string) against `now` (a `datetime` object).
```python
elif e["state"] == "resting" and e.get("until") and _at(e["until"]) <= now:
```
`_at()` uses `datetime.fromisoformat`. If the registry was seeded by a process using naive datetimes (e.g., `datetime.utcnow()` or local time without tzinfo), `e["until"]` will be naive. If `now` is timezone-aware (as in `proof_ledger.py` where `now` is likely UTC-aware), this raises `TypeError: can't compare offset-naive and offset-aware datetimes`.
*Scenario:* A candidate enters "resting" state. 6 hours later, the build runs. If the `now` passed to `run_due` is aware but the stored `until` is naive (or vice versa), the pipeline crashes with an unhandled exception, violating **M12 FAIL CLOSED** (it should reject/hold, not crash the driver).
*Fix:* Ensure `_at()` and the `now` parameter are consistently timezone-aware (e.g., force `tzinfo=timezone.utc` if missing).

**2. `tests/package/proof_ledger.py:296-299` — Silent "Clip" Classification for Infrastructure Errors**
```python
try:
    with open(os.path.join(REPO, e["source"], "package.json")) as f:
        c = PK.load_candidate(json.load(f), e["index"], source=e["source"])
except (OSError, ValueError, KeyError, TypeError) as ex:
    return None, "clip", f"it cannot be rebuilt from its record ({type(ex).__name__}: {ex})", 0
```
If the source file is missing (`OSError`) or the JSON is corrupt, the candidate is marked as `"clip"` (closed for good). Ruling 66 states a candidate is closed for good when a *clip* is delivered, ages out, or fails a gate. An infrastructure error (missing file) is not a clip failure.
*Scenario:* A transient disk I/O error or a race condition where the file is being written causes the candidate to be permanently closed. This violates the spirit of **LAW 20** (never change what a check accepts to make a render pass) and **M12** (missing data should reject/hold, not produce a definitive "closed" state that loses the candidate).
*Fix:* Distinguish between "clip no longer valid" (ValueError from `load_candidate` logic) and "infrastructure failure" (OSError). Infrastructure failures should likely raise or mark as "inconclusive" rather than "clip".

## P1 Findings

**3. `pipeline/candidates.py:103` — Sorting Logic Ambiguity with Mixed States**
```python
return sorted(out, key=lambda x: (str(x[1].get("found_at") or ""), x[1]["source"], x[1]["index"]), reverse=True)
```
The sort key is `(found_at, source, index)`.
*Issue:* `found_at` is a string. ISO 8601 strings sort lexicographically correctly *only if* they are in the same format and timezone. If `found_at` is missing (`None`), it becomes `""`, which sorts *before* any date string. With `reverse=True`, `""` (missing date) will be sorted *last* (oldest). This is likely correct (unknown age = try last), but if `found_at` is present in some records and missing in others, the "newest first" guarantee relies on string comparison.
*More Critical:* The `source` and `index` are used as tie-breakers. If two candidates have the exact same `found_at` (unlikely but possible if seeded in the same second), they are sorted by `source` (path) and `index`. This is deterministic but arbitrary. The ruling says "newest first". If "newest" is strictly by time, this is fine. However, if `found_at` is not set for legacy records (see `seed` function, line 70: `at = record.get("now")`), and `now` is missing, `found_at` is `None`.
*Scenario:* Legacy records without `now` get `found_at=None`. They sort last. This is acceptable, but the code should explicitly handle `None` to avoid `str(None)` = `"None"` which might sort unexpectedly against ISO dates (e.g., `"None"` > `"2026..."` because 'N' > '2').
*Fix:* Use a robust sort key that handles `None` explicitly, e.g., `key=lambda x: (x[1].get("found_at") or "0000-00-00T00:00:00", ...)`.

**4. `pipeline/package.py:197-200` — "Line" vs "Clip" Classification Edge Case**
```python
out["candidate"]["class"] = (
    "package" if out["packages"] else
    "budget" if not t_ or out.get("budget_stop") or t_.get("budget") else
    "line" if t_.get("medley_ok") and t_.get("attempts") and not t_.get("relined") else "clip")
```
*Issue:* The condition for `"line"` requires `t_.get("attempts")`. What is `attempts`? It is not defined in the diff. If `attempts` is 0 or missing, a candidate that passed the medley (`medley_ok=True`) but failed the write gates (no package) will be classified as `"clip"` instead of `"line"`.
*Scenario:* A candidate's clips pass the medley. The write fails. If `attempts` is not set to a truthy value in the `tried` record, the candidate is closed for good (`"clip"`) instead of resting for 6 hours (`"line"`). This violates

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1420 (RULING 66's standing part: the candidate registry): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes", P2s only.
  - qwen: "SHIP: NO", on two "P0"s and two P1s.
  - glm: no P0. Its first attempt failed on transport (IncompleteRead, 18 min). The re-run finished at its 24k-token limit (finish=length), with P1s its own text mostly resolves.
- No P0 holds as stated. One consensus item is applied before cycle 2 (C1).

## Applied (the consensus item)

| # | finding | the change |
|---|---|---|
| C1 | A stored registry time that _at() cannot compare crashes due() mid-build: grok P2 (a malformed "until" raises at due() time), qwen P0-1 (a naive time against the aware now), glm P1-8 (a TypeError there would kill the run) | _at() reads a time without a zone as UTC; every time this module writes is UTC-aware already, from the driver's datetime.now(timezone.utc) and the records' now.isoformat(). The driver now evaluates CA.due(reg, now) inside its refusal block, so a malformed stored time refuses the run (exit 2) before anything is written. Test: test_a_stored_time_without_a_zone_is_utc_and_a_malformed_one_raises. |

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P1-4: "attempts" is not defined in the diff, so a line failure may be classed "clip" | rec["attempts"] is the tried entry's list in the unchanged loop (`rec = {..., "attempts": [], ...}`). EVERY write appends to it: `rec["attempts"].append(att)` after a write, and `rec["attempts"].append({"writer_error": ...})` on a writer error. A line-up that reached a write therefore has a non-empty list. Test: test_the_outcome_class_and_the_fresh_writes asserts "line" for two writes failing on the takeaway. |
| R2 | qwen P1-5 = glm P1-2: build(candidate=) may spend a judged line-up on a verdict served from its recording, or count none for one judged afresh | The unchanged budget line (ruling 65's): `total += 0 if med.get("replayed") or med.get("cached") else 1`, and out["search"]["lineups"] = total, which try_one returns as `judged`. test_a_cached_clips_alone_verdict_is_free (test_medley) asserts lineups 0 for a cached verdict. |
| R3 | qwen P1-3 = glm P1-1: a missing found_at sorts as the string "None" (first, inverting newest-first) | The key is `str(x[1].get("found_at") or "")`: None becomes "", never "None". |
| R4 | qwen P2-7: res["now"] could be None and crash the seeding | The driver sets res["now"] = now.isoformat() (res.update) before package.json is written and before CA.seed reads it. |
| R5 | grok P2: --from-candidate never adds "registry": True | `res["registry"] = True` sits after both branches (the --from-candidate one and the due-candidates one). Only candidate_tries is the due path's own. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | qwen P0-2: an OSError reading a candidate's record closes it as "clip" (for good), though it is not a gate failure | The records are tracked files under test

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1420/C2_STEP.diff (488 lines)
```
   1 | diff --git a/pipeline/candidates.py b/pipeline/candidates.py
   2 | new file mode 100644
   3 | index 0000000..36640fc
   4 | --- /dev/null
   5 | +++ b/pipeline/candidates.py
   6 | @@ -0,0 +1,121 @@
   7 | +"""RULING 66 (orchestrator 13:18 Nov 13; its standing part ruled 14:02): A PASSED LINE-UP IS KEPT.
   8 | +
   9 | +"Any line-up that passes the clips-alone verdict is recorded as a CANDIDATE (clips, order, the verdict, the gated
  10 | +takeaway and title if written) and stays a candidate until one of its clips is delivered, ages out, or fails a gate.
  11 | +Every build first tries the open candidates, newest first, before asking for new angles."
  12 | +14:02: "a candidate whose clips still pass but whose LINE fails again (the takeaway, or the title after ruling 65's
  13 | +extra write) is CLOSED for 6 hours, then may be tried once more with fresh writes; it is closed for good when a clip
  14 | +is delivered, ages out or fails a gate. Open candidates are tried newest first inside the 8 judged line-ups, recorded
  15 | +verdicts free, before any angle is asked."
  16 | +
  17 | +The registry ({"records": [build dirs seeded], "candidates": {key: entry}}) is seeded from the build records
  18 | +themselves (each build's package.json: its tried line-ups, their verdicts and writes), so a candidate is exactly a
  19 | +record's tried entry and package.load_candidate rebuilds it. A try's outcome class comes from package.build
  20 | +(out["candidate"]["class"]):
  21 | +  "package": it became a package (its clips go to a pin)        -> closed
  22 | +  "clip":    a clip left the pool or failed a gate, its clips-alone verdict failed now, or it could not be rebuilt
  23 | +             from its record                                     -> closed for good
  24 | +  "line":    its clips passed but a line failed again            -> resting 6 h, then ONE try with fresh writes;
  25 | +                                                                    a line failing that try too -> closed
  26 | +  "budget":  a budget stopped it before an outcome               -> as it was
  27 | +Pure functions; the driver (tests/package/proof_ledger.py) reads and writes the file."""
  28 | +from datetime import datetime, timedelta, timezone
  29 | +
  30 | +RESTING_H = 6.0                 # 14:02: "CLOSED for 6 hours, then may be tried once more with fresh writes"
  31 | +FRESH_SEED = 1000               # the writes of that one more try: seeds no recorded write used (package.build)
  32 | +
  33 | +
  34 | +def key(lineup):
  35 | +    return "+".join(lineup)
  36 | +
  37 | +
  38 | +def _at(s):
  39 | +    """A stored time; one without a zone is UTC (every time this module writes carries one). Raises ValueError on a
  40 | +    malformed one (the driver evaluates due() before it writes anything, audit 1420 C1)."""
  41 | +    t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
  42 | +    return t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)
  43 | +
  44 | +
  45 | +def new_registry():
  46 | +    return {"records": [], "candidates": {}}
  47 | +
  48 | +
  49 | +def outcome(entry, cls, at, build, why=""):
  50 | +    """Record one try of a candidate and apply ruling 66's rule for its class."""
  51 | +    entry["history"].append({"build": build, "at": at, "class": cls, "fresh": bool(entry.get("trying_fresh")),
  52 | +                             "why": str(why or "")[:300]})
  53 | +    entry.pop("trying_fresh", None)
  54 | +    if cls in ("package", "clip"):
  55 | +        entry["state"], entry["until"] = "closed", None
  56 | +    elif cls == "line":
  57 | +        if entry.get("fresh_used"):
  58 | +            entry["state"], entry["until"] = "closed", None
  59 | +        else:
  60 | +            entry["state"], entry["until"] = "resting", (_at(at) + timedelta(hours=RESTING_H)).isoformat()
  61 | +    elif cls != "budget":
  62 | +        raise ValueError(f"unknown outcome class {cls!r}")
  63 | +
  64 | +
  65 | +def seed(reg, record, source):
  66 | +    """Seed the registry from one build record, once per record (reg["records"]). Every tried line-up that passed the
  67 | +    clips-alone verdict and is not itself a candidate's try becomes a candidate (one per line-up, the earliest record
  68 | +    that passed it). A line-up the record packaged is closed. A record written before the registry existed applies
  69 | +    the outcome of the candidate it tried (its out["candidate"]). -> the keys added."""
  70 | +    if source in reg["records"]:
  71 | +        return []
  72 | +    reg["records"].append(source)
  73 | +    added, at = [], record.get("now")
  74 | +    pk = record.get("package") or {}
  75 | +    packaged = [s.get("moment_id") for s in pk.get("segments") or []]
  76 | +    for i, t in enumerate(record.get("tried") or []):
  77 | +        lu = t.get("lineup")
  78 | +        if t.get("medley_ok") is not True or not isinstance(lu, list) or not lu or t.get("candidate") is not None:
  79 | +            continue
  80 | +        k = key(lu)
  81 | +        if k not in reg["candidates"]:
  82 | +            reg["candidates"][k] = {"lineup": list(lu), "source": source, "index": i, "found_at": at,
  83 | +                                    "state": "open", "until": None, "fresh_used": False, "history": []}
  84 | +            added.append(k)
  85 | +        if lu == packaged and reg["candidates"][k]["state"] != "closed":
  86 | +            outcome(reg["candidates"][k], "package", at, source, "packaged by the build that passed it")
  87 | +    c = record.get("candidate")
  88 | +    if c and not record.get("registry"):                # a try made before the registry: its outcome, once
  89 | +        k = key(c.get("lineup") or [])
  90 | +        if k in reg["candidates"] and reg["candidates"][k]["state"] != "closed":
  91 | +            res = str(c.get("result") or "")
  92 | +            cls = c.get("class") or ("package" if res.startswith("PACKAGE") else "clip")
  93 | +            outcome(reg["candidates"][k], cls, at, source, res or c.get("closed"))
  94 | +    return added
  95 | +
  96 | +
  97 | +def due(reg, now):
  98 | +    """The candidates to try now, newest first (by the time their line-up passed): every open one (its recorded
  99 | +    verdicts and writes, free), and every resting one whose 6 h are over (fresh writes). -> [(key, entry, fresh)]."""
 100 | +    out = []
 101 | +    for k, e in reg["candidates"].items():
 102 | +        if e["state"] == "open":
 103 | +            out.append((k, e, False))
 104 | +        elif e["state"] == "resting" and e.get("until") and _at(e["until"]) <= now:
 105 | +            out.append((k, e, True))
 106 | +    return sorted(out, key=lambda x: (str(x[1].get("found_at") or ""), x[1]["source"], x[1]["index"]), reverse=True)
 107 | +
 108 | +
 109 | +def run_due(reg, now, try_one, lineups, build=""):
 110 | +    """RULING 66: try the due candidates newest first, inside `lineups` judged line-ups (a recorded verdict is free), and
 111 | +    stop at the first package. try_one(entry, fresh, lineups_left) -> (out, cls, why, judged).
 112 | +    -> (the package's out or None, [one summary per try], the judged line-ups left)."""
 113 | +    tries = []
 114 | +    for k, e, fresh in due(reg, now):
 115 | +        if lineups <= 0:
 116 | +            break
 117 | +        if fresh:
 118 | +            e["fresh_used"], e["trying_fresh"] = True, True
 119 | +        out, cls, why, judged = try_one(e, fresh, lineups)
 120 | +        lineups -= int(judged or 0)
 121 | +        outcome(e, cls, now.isoformat(), build, why)
 122 | +        tries.append({"key": k, "source": e["source"], "index": e["index"], "fresh": fresh, "class": cls,
 123 | +                      "why": str(why or "")[:300], "judged": int(judged or 0), "state": e["state"],
 124 | +                      "until": e["until"]})
 125 | +        if cls == "package":
 126 | +            return out, tries, lineups
 127 | +    return None, tries, lineups
 128 | diff --git a/pipeline/package.py b/pipeline/package.py
 129 | index 5f5b4b8..978628c 100644
 130 | --- a/pipeline/package.py
 131 | +++ b/pipeline/package.py
 132 | @@ -2042,7 +2042,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 133 |      RULING 66, A PASSED LINE-UP IS KEPT: candidate (load_candidate) tries ONLY that line-up, after the same pool stages:
 134 |      no angle is asked for (its own angle and back-end), its clips must still form it (candidate_lineup), and it is
 135 |      judged and written with its own seeds, so its recorded calls are served from their recordings; it is never
 136 | -    re-lined or swapped (a failing gate closes it: out["candidate"]).
 137 | +    re-lined or swapped (a failing gate closes it: out["candidate"]). Its outcome class (candidates.outcome) is
 138 | +    out["candidate"]["class"]: "package", "clip" (closed for good), "line" (its clips passed, a line failed) or
 139 | +    "budget". candidate["write_seed"] (ruling 66 at 14:02: a candidate's one more try "with fresh writes") is added to
 140 | +    every write's seed, so no recorded write is served again; 0 (the default) keeps the recorded ones.
 141 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 142 |      t0 = time.time()
 143 |      usd0 = _spent(spend)
 144 | @@ -2177,8 +2180,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 145 |      if candidate is not None:                         # RULING 66 (13:18): A PASSED LINE-UP IS KEPT: its own angle and
 146 |          cand_segs, why_c = candidate_lineup(router, candidate, cleared, ctx.now)   # line-up; no angle is asked for
 147 |          out["candidate"] = {"source": candidate.get("source"), "index": candidate.get("index"),
 148 | -                            "lineup": list(candidate["lineup"]), "closed": why_c}
 149 | +                            "lineup": list(candidate["lineup"]), "closed": why_c,
 150 | +                            "fresh": bool(candidate.get("write_seed"))}
 151 |          if why_c is not None:
 152 | +            out["candidate"].update(result=why_c, **{"class": "clip"})
 153 |              out["why_none"] = f"ruling 66: the candidate is closed: {why_c}"
 154 |              log(f"  {out['why_none']}")
 155 |              return out
 156 | @@ -2374,6 +2379,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 157 |              f"{sum(m['duration_s'] for m in order):.1f} s, added {added}) ({time.time() - t0:.0f} s)")
 158 |          return pk
 159 |  
 160 | +    wseed = int((candidate or {}).get("write_seed") or 0)  # ruling 66 (14:02): a candidate's fresh writes
 161 |      total = 0                                             # ruling 41: line-ups judged in this build, over every angle
 162 |      judged, bad_pairs, spins = {}, set(), 0               # 12:00: verdicts by line-up; ruling 63's unfollowable pairs
 163 |      with ThreadPoolExecutor(max_workers=8) as pool:
 164 | @@ -2491,12 +2497,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 165 |                          break
 166 |                      w_over = package_over(line)
 167 |                      if w_over:
 168 | -                        rec["why"] = w_over
 169 | +                        rec["why"], rec["budget"] = w_over, True      # ruling 66: a budget, not an outcome
 170 |                          break
 171 |                      w_used += 1
 172 |                      try:
 173 |                          wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 174 | -                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup,
 175 | +                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup + wseed,
 176 |                                                      avoid_vendor=writer_avoid or None, other=written)
 177 |                      except NoBridgeFits as e:                  # the seconds rule it out: re-line, no write is paid
 178 |                          if join is not None:
 179 | @@ -2602,7 +2608,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 180 |                          pk, fid, cx, cheap_t, rw = rewrite_alone(
 181 |                              router, slot, pk, fields, fid, [v for v in cheap + fid["violations"]], angle, segs, cleared,
 182 |                              ctx, a_by, sources, levels, writers_v, writers_f, writer_avoid or None,
 183 | -                            seed=7 + w_used + 10 * ai + 100 * n_lineup)
 184 | +                            seed=7 + w_used + 10 * ai + 100 * n_lineup + wseed)
 185 |                          att["rewrite"] = rw
 186 |                          cheap, det, dup, rt_ok, r4_res = cheap_t
 187 |                          log(f"    the {slot} alone (ruling 65): " + ("PASS" if rw.get("passed") else
 188 | @@ -2669,6 +2675,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 189 |                      out["packages"].append(pk)
 190 |                      rec["result"] = "PACKAGE"
 191 |                      break
 192 | +                rec["relined"] = relined                    # ruling 66: a clip was dropped (or a line-up rule)
 193 |                  if not out["packages"] and not relined and ok_m and not med["flagged"] and \
 194 |                          take_failed >= NO_VOICE_AFTER and last_fields is not None and not out.get("budget_stop"):
 195 |                      nv = no_voice(angle, segs, med, last_fields, exception, dropped, rec, ai, n_lineup)
 196 | @@ -2687,6 +2694,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 197 |      if candidate is not None:                             # RULING 66: what became of the candidate
 198 |          t_ = next((t for t in out["tried"] if t.get("candidate") is not None), {})
 199 |          out["candidate"]["result"] = t_.get("result") or t_.get("why") or out.get("why_none") or "not tried"
 200 | +        out["candidate"]["class"] = (                     # candidates.outcome reads it
 201 | +            "package" if out["packages"] else
 202 | +            "budget" if not t_ or out.get("budget_stop") or t_.get("budget") else
 203 | +            "line" if t_.get("medley_ok") and t_.get("attempts") and not t_.get("relined") else "clip")
 204 |      s_est, s_rep = (a - b for a, b in zip(_spent(spend), usd0))
 205 |      out["search"] = {"lineups": total, "limit": lineups, "usd_reported": round(s_rep, 4),
 206 |                       "usd_estimate": round(s_est, 4), "seconds": round(time.time() - t0, 1)}
 207 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 208 | index ed6cbba..0b0f059 100644
 209 | --- a/tests/package/proof_ledger.py
 210 | +++ b/tests/package/proof_ledger.py
 211 | @@ -20,7 +20,11 @@
 212 |  Writes tests/package/proof/ledger_<UTC stamp, to the second>/ (a run never writes into an existing one): inputs.json,
 213 |  package.json, package.log, step_a.json and, on a package, MOMENTS_PIN_LEDGER.json.
 214 |  
 215 | -RULING 66 (13:18), A PASSED LINE-UP IS KEPT: --from-candidate BUILD_DIR[:N] tries ONLY the line-up that passed the
 216 | +RULING 66 (13:18; its standing part ruled 14:02), A PASSED LINE-UP IS KEPT: every build first tries the due
 217 | +candidates of the registry (tests/package/proof/CANDIDATES.json, seeded from the build records; pipeline/candidates.py),
 218 | +newest first, inside the 8 judged line-ups (a recorded verdict is free), each as package.build(candidate=...); only when
 219 | +none gives a package are angles asked, with the judged line-ups left. The registry is read (and seeded) before anything
 220 | +is written and saved after the record. --from-candidate BUILD_DIR[:N] tries ONLY the line-up that passed the
 221 |  clips-alone verdict in that earlier build's record (its tried[N]; default the first that passed), after the same pool
 222 |  stages: its own angle, play order and seeds (package.load_candidate), so its recorded calls are served from their
 223 |  recordings and only what is missing is paid for; never re-lined, swapped or a new angle.
 224 | @@ -31,6 +35,7 @@ Usage: python3 tests/package/proof_ledger.py --delivered PIN [PIN ...] [--since
 225 |                         tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json
 226 |  """
 227 |  import argparse
 228 | +import glob
 229 |  import json
 230 |  import os
 231 |  import sys
 232 | @@ -44,6 +49,7 @@ sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
 233 |  sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 234 |  sys.path.insert(0, HERE)
 235 |  import eligibility as E  # noqa: E402
 236 | +import candidates as CA  # noqa: E402
 237 |  import ledger_build as LB  # noqa: E402
 238 |  import moments as M  # noqa: E402
 239 |  import package as PK  # noqa: E402
 240 | @@ -53,6 +59,9 @@ import proof_saved_runs as PS  # noqa: E402
 241 |  import providers as P  # noqa: E402
 242 |  import speakers as SP  # noqa: E402
 243 |  
 244 | +REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
 245 | +
 246 | +
 247 |  def delivered_pins(paths):
 248 |      """The pins already delivered -> (every clip span {video_id, start, end, pin} for package.usable's overlap check,
 249 |      the newest approved_at, [{path, story_id, approved_at, clips}]). Raises ValueError (or OSError / KeyError /
 250 | @@ -108,9 +117,17 @@ def main(argv=None):
 251 |              with open(os.path.join(cdir, "package.json")) as f:
 252 |                  cand = PK.load_candidate(json.load(f), int(idx) if idx else None,
 253 |                                           source=os.path.relpath(os.path.abspath(cdir), REPO))
 254 | +        reg = CA.new_registry()                          # RULING 66: the candidates, seeded from every build record
 255 | +        if os.path.exists(REGISTRY):
 256 | +            with open(REGISTRY) as f:
 257 | +                reg = json.load(f)
 258 | +        for p in sorted(glob.glob(os.path.join(HERE, "proof", "ledger_*", "package.json"))):
 259 | +            with open(p) as f:
 260 | +                CA.seed(reg, json.load(f), os.path.relpath(os.path.dirname(p), REPO))
 261 | +        CA.due(reg, now)                                 # every stored time reads (audit 1420 C1), or exit 2
 262 |      except (OSError, ValueError, KeyError, TypeError) as e:
 263 | -        print(f"REFUSED: the delivered pins, 'since' or the candidate cannot be read ({type(e).__name__}: {e})",
 264 | -              file=sys.stderr)
 265 | +        print(f"REFUSED: the delivered pins, 'since', the candidate or the candidate registry cannot be read "
 266 | +              f"({type(e).__name__}: {e})", file=sys.stderr)
 267 |          return 2
 268 |      out_dir = os.path.join(HERE, "proof", f"ledger_{now.strftime('%Y%m%d_%H%M%S')}")
 269 |      try:
 270 | @@ -150,14 +167,46 @@ def main(argv=None):
 271 |          f"starts at ${PL.LY_STOP_USD:.2f})")
 272 |      own, used = PL.meter(router), PL.reply_meter(router)
 273 |      t0 = time.time()
 274 | -    res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
 275 | -                   work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 276 | -                   spend=lambda: (own["est"], own["best"]),
 277 | -                   step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 278 | -                   hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 279 | -                   scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 280 | -                   scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
 281 | -                   candidate=cand)                                                     # ruling 66
 282 | +    kw = dict(delivered=delivered, optout=M.optout_ids(), log=say,
 283 | +              work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 284 | +              spend=lambda: (own["est"], own["best"]),
 285 | +              step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 286 | +              hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
 287 | +              scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
 288 | +              scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir))
 289 | +    name, at = os.path.relpath(out_dir, REPO), now.isoformat()
 290 | +    if cand is not None:                                 # --from-candidate: that candidate alone (ruling 66, 13:18)
 291 | +        res = PK.build(router, moments, sources, ctx, candidate=cand, **kw)
 292 | +        k = CA.key(cand["lineup"])
 293 | +        if k in reg["candidates"]:
 294 | +            CA.outcome(reg["candidates"][k], res["candidate"]["class"], at, name, res["candidate"].get("result"))
 295 | +    else:                                                # RULING 66 (14:02): the due candidates first, newest first
 296 | +        last = {}
 297 | +
 298 | +        def try_one(e, fresh, left):
 299 | +            try:
 300 | +                with open(os.path.join(REPO, e["source"], "package.json")) as f:
 301 | +                    c = PK.load_candidate(json.load(f), e["index"], source=e["source"])
 302 | +            except (OSError, ValueError, KeyError, TypeError) as ex:
 303 | +                return None, "clip", f"it cannot be rebuilt from its record ({type(ex).__name__}: {ex})", 0
 304 | +            if fresh:
 305 | +                c["write_seed"] = CA.FRESH_SEED          # "then may be tried once more with fresh writes"
 306 | +            say(f"  RULING 66: the candidate {e['source']} tried[{e['index']}] {e['lineup']}" +
 307 | +                (" with fresh writes" if fresh else "") + f", {left} judged line-up(s) left")
 308 | +            o = PK.build(router, moments, sources, ctx, candidate=c, lineups=left, **kw)
 309 | +            last["out"] = o
 310 | +            return o, o["candidate"]["class"], o["candidate"].get("result"), (o.get("search") or {}).get("lineups", 0)
 311 | +        res, tries, left = CA.run_due(reg, now, try_one, PK.LINEUPS_PER_BUILD, build=name)
 312 | +        say(f"  RULING 66: {len(tries)} candidate(s) tried: " + "; ".join(
 313 | +            f"{t['source']}[{t['index']}] {t['class']} -> {t['state']}" for t in tries) if tries else
 314 | +            "  RULING 66: no candidate is due")
 315 | +        if res is None and left > 0:
 316 | +            res = PK.build(router, moments, sources, ctx, lineups=left, **kw)
 317 | +        elif res is None:                                # every judged line-up went to candidates: no angle asked
 318 | +            res = dict(last["out"], package=None, packages=[],
 319 | +                       why_none="ruling 66: the 8 judged line-ups were spent on candidates; no angle asked")
 320 | +        res["candidate_tries"] = tries
 321 | +    res["registry"] = True                               # its outcomes are in the registry already (CA.seed)
 322 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 323 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 324 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 325 | @@ -185,6 +234,10 @@ def main(argv=None):
 326 |          f"vendor-reported after this build (before it: ${spent0:.2f})")
 327 |      with open(os.path.join(out_dir, "package.json"), "w") as f:
 328 |          json.dump(res, f, indent=1, default=str)
 329 | +    CA.seed(reg, json.loads(json.dumps(res, default=str)), name)   # this build's passed line-ups join the registry
 330 | +    with open(REGISTRY + ".tmp", "w") as f:
 331 | +        json.dump(reg, f, indent=1)
 332 | +    os.replace(REGISTRY + ".tmp", REGISTRY)
 333 |      logf.close()
 334 |      return 0
 335 |  
 336 | diff --git a/tests/package/test_candidates.py b/tests/package/test_candidates.py
 337 | new file mode 100644
 338 | index 0000000..810a3bc
 339 | --- /dev/null
 340 | +++ b/tests/package/test_candidates.py
 341 | @@ -0,0 +1,115 @@
 342 | +#!/usr/bin/env python3
 343 | +"""RULING 66's standing part (orchestrator 14:02 Nov 13): the candidate registry (pipeline/candidates.py)."""
 344 | +import os
 345 | +import sys
 346 | +import unittest
 347 | +from datetime import datetime, timedelta, timezone
 348 | +
 349 | +HERE = os.path.dirname(os.path.abspath(__file__))
 350 | +REPO = os.path.dirname(os.path.dirname(HERE))
 351 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 352 | +import candidates as CA  # noqa: E402
 353 | +
 354 | +T0 = datetime(2026, 11, 13, 19, 0, tzinfo=timezone.utc)
 355 | +
 356 | +
 357 | +def record(now, tried, package=None, candidate=None, registry=False):
 358 | +    return {"now": now.isoformat(), "tried": tried, "package": package, "candidate": candidate,
 359 | +            **({"registry": True} if registry else {})}
 360 | +
 361 | +
 362 | +def t(lineup, ok=True, cand=None):
 363 | +    return {"lineup": lineup, "medley_ok": ok, **({"candidate": cand} if cand else {})}
 364 | +
 365 | +
 366 | +class TestRegistry(unittest.TestCase):
 367 | +    def test_a_passed_line_up_is_a_candidate_once_and_a_packaged_one_is_closed(self):
 368 | +        reg = CA.new_registry()
 369 | +        self.assertEqual(CA.seed(reg, record(T0, [t(["a", "b", "c"], ok=False), t(["a", "b", "d"])]), "r1"),
 370 | +                         ["a+b+d"])
 371 | +        self.assertEqual(CA.seed(reg, record(T0, [t(["a", "b", "d"])]), "r1"), [])          # a record seeds once
 372 | +        self.assertEqual(CA.seed(reg, record(T0 + timedelta(hours=1), [t(["a", "b", "d"])]), "r2"), [])   # one entry
 373 | +        self.assertEqual((reg["candidates"]["a+b+d"]["source"], reg["candidates"]["a+b+d"]["index"]), ("r1", 1))
 374 | +        CA.seed(reg, record(T0, [t(["x", "y", "z"])], package={"segments": [{"moment_id": m} for m in "xyz"]}), "r3")
 375 | +        self.assertEqual(reg["candidates"]["x+y+z"]["state"], "closed")                  # its own build packaged it
 376 | +        CA.seed(reg, record(T0, [t(["a", "b", "d"], cand="r1")]), "r4")                  # a candidate's own try
 377 | +        self.assertEqual(set(reg["candidates"]), {"a+b+d", "x+y+z"})                     # is never a new candidate
 378 | +
 379 | +    def test_a_try_made_before_the_registry_counts_once(self):
 380 | +        reg = CA.new_registry()
 381 | +        CA.seed(reg, record(T0, [t(["a", "b", "d"])]), "r1")
 382 | +        legacy = record(T0, [t(["a", "b", "d"], cand="r1")],
 383 | +                        candidate={"source": "r1", "index": 0, "lineup": ["a", "b", "d"], "result": "PACKAGE"})
 384 | +        CA.seed(reg, legacy, "r2")
 385 | +        self.assertEqual(reg["candidates"]["a+b+d"]["state"], "closed")
 386 | +        reg2 = CA.new_registry()
 387 | +        CA.seed(reg2, record(T0, [t(["a", "b", "d"])]), "r1")
 388 | +        CA.seed(reg2, dict(legacy, registry=True), "r2")                                # a registry build: no again
 389 | +        self.assertEqual(reg2["candidates"]["a+b+d"]["state"], "open")
 390 | +
 391 | +    def test_the_14_02_rules(self):
 392 | +        e = {"history": [], "state": "open", "until": None, "fresh_used": False}
 393 | +        CA.outcome(e, "budget", T0.isoformat(), "b1")
 394 | +        self.assertEqual(e["state"], "open")                                              # a budget is no outcome
 395 | +        CA.outcome(e, "line", T0.isoformat(), "b2")                                       # a line failed again
 396 | +        self.assertEqual((e["state"], e["until"]), ("resting", (T0 + timedelta(hours=6)).isoformat()))
 397 | +        e["fresh_used"] = True                                                            # its one more try
 398 | +        CA.outcome(e, "line", (T0 + timedelta(hours=7)).isoformat(), "b3")
 399 | +        self.assertEqual(e["state"], "closed")
 400 | +        for cls in ("clip", "package"):
 401 | +            e2 = {"history": [], "state": "open", "until": None, "fresh_used": False}
 402 | +            CA.outcome(e2, cls, T0.isoformat(), "b")
 403 | +            self.assertEqual(e2["state"], "closed", cls)
 404 | +        with self.assertRaises(ValueError):
 405 | +            CA.outcome(e2, "maybe", T0.isoformat(), "b")
 406 | +
 407 | +    def test_due_is_newest_first_and_a_rested_one_gets_fresh_writes(self):
 408 | +        reg = CA.new_registry()
 409 | +        CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "old")
 410 | +        CA.seed(reg, record(T0 + timedelta(hours=2), [t(["d", "e", "f"])]), "new")
 411 | +        CA.seed(reg, record(T0 + timedelta(hours=1), [t(["g", "h", "i"])]), "mid")
 412 | +        CA.outcome(reg["candidates"]["g+h+i"], "line", T0.isoformat(), "b")              # resting until T0 + 6 h
 413 | +        self.assertEqual([(k, f) for k, _, f in CA.due(reg, T0 + timedelta(hours=3))],
 414 | +                         [("d+e+f", False), ("a+b+c", False)])
 415 | +        self.assertEqual([(k, f) for k, _, f in CA.due(reg, T0 + timedelta(hours=6))],
 416 | +                         [("d+e+f", False), ("g+h+i", True), ("a+b+c", False)])
 417 | +
 418 | +    def test_a_stored_time_without_a_zone_is_utc_and_a_malformed_one_raises(self):
 419 | +        reg = CA.new_registry()
 420 | +        CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "r")
 421 | +        e = reg["candidates"]["a+b+c"]
 422 | +        e.update(state="resting", until="2026-11-13T19:00:00")                       # no zone: UTC
 423 | +        self.assertEqual([k for k, _, f in CA.due(reg, T0)], ["a+b+c"])
 424 | +        e["until"] = "tomorrow"
 425 | +        with self.assertRaises(ValueError):
 426 | +            CA.due(reg, T0)
 427 | +
 428 | +    def test_run_due_stops_at_a_package_inside_the_judged_line_ups(self):
 429 | +        reg = CA.new_registry()
 430 | +        for h, lu in enumerate((["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"])):
 431 | +            CA.seed(reg, record(T0 + timedelta(hours=h), [t(lu)]), f"r{h}")
 432 | +        seen = []
 433 | +
 434 | +        def try_one(e, fresh, left):
 435 | +            seen.append((CA.key(e["lineup"]), fresh, left))
 436 | +            return ({"package": "pk"} if e["lineup"][0] == "d" else None,
 437 | +                    {"g": "clip", "d": "package"}[e["lineup"][0]], "why", 1)
 438 | +        out, tries, left = CA.run_due(reg, T0 + timedelta(hours=3), try_one, 8, build="b")
 439 | +        self.assertEqual(out, {"package": "pk"})
 440 | +        self.assertEqual(seen, [("g+h+i", False, 8), ("d+e+f", False, 7)])                # newest first; then stop
 441 | +        self.assertEqual((left, [x["class"] for x in tries]), (6, ["clip", "package"]))
 442 | +        self.assertEqual(reg["candidates"]["a+b+c"]["state"], "open")                    # never reached: still open
 443 | +        out, tries, left = CA.run_due(reg, T0 + timedelta(hours=3), lambda e, f, l: (None, "budget", "", 0), 0)
 444 | +        self.assertEqual((out, tries, left), (None, [], 0))                              # no line-up left: no try
 445 | +
 446 | +    def test_the_fresh_try_is_marked_and_a_line_failing_it_closes(self):
 447 | +        reg = CA.new_registry()
 448 | +        CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "r")
 449 | +        CA.outcome(reg["candidates"]["a+b+c"], "line", T0.isoformat(), "b1")
 450 | +        out, tries, _ = CA.run_due(reg, T0 + timedelta(hours=6, minutes=1), lambda e, f, l: (None, "line", "w", 1), 8)
 451 | +        self.assertEqual((tries[0]["fresh"], tries[0]["state"]), (True, "closed"))
 452 | +        self.assertTrue(reg["candidates"]["a+b+c"]["history"][-1]["fresh"])
 453 | +
 454 | +
 455 | +if __name__ == "__main__":
 456 | +    unittest.main()
 457 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 458 | index b590b0f..33c7418 100644
 459 | --- a/tests/package/test_medley.py
 460 | +++ b/tests/package/test_medley.py
 461 | @@ -1670,6 +1670,26 @@ class TestRuling66Candidate(unittest.TestCase):
 462 |          self.assertEqual(out["tried"][0]["why"], "ruling 66: the candidate fails its clips-alone verdict now: closed")
 463 |          self.assertEqual(out["candidate"]["result"], out["tried"][0]["why"])
 464 |  
 465 | +    def test_the_outcome_class_and_the_fresh_writes(self):
 466 | +        """14:02: the class candidates.outcome reads: "package"; "clip" (closed before any call, or its clips-alone
 467 | +        verdict fails now); "line" (its clips pass, its writes fail). write_seed shifts every write's seed."""
 468 | +        c = PK.load_candidate(self.record(), source="r")
 469 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c).run()
 470 | +        self.assertEqual(out["candidate"]["class"], "package")
 471 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], uncuttable={"y"}, candidate=c).run()
 472 | +        self.assertEqual((out["candidate"]["class"], out["candidate"]["result"][:16]), ("clip", "no longer cleare"))
 473 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, Rig.LINE)], [], candidate=c).run()
 474 | +        self.assertEqual(out["candidate"]["class"], "clip")
 475 | +        bad = dict(TestRuling65Caption.OK, ok=False, violations=[{"slot": "takeaway", "rule": "VERDICT_NO",
 476 | +                                                                    "detail": "x"}])
 477 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None, None], fids=[bad, bad],
 478 | +                  candidate=dict(c, write_seed=1000))
 479 | +        out = rig.run()
 480 | +        self.assertIsNone(out["package"])
 481 | +        self.assertEqual((out["candidate"]["class"], out["candidate"]["fresh"]), ("line", True))
 482 | +        self.assertEqual(rig.seeds, [("medley", 8), ("write", 1108), ("write", 1109)])   # fresh writes, the verdict
 483 | +                                                                                          # still its recorded seed
 484 | +
 485 |      def test_exactly_its_clips_never_a_subset(self):
 486 |          ms = [pm("h", "A", 13.0), pm("x", "B", 13.0), pm("y", "C", 13.0), pm("z", "D", 11.0)]
 487 |          rec = self.record(tried=[{"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "y", "z"],
 488 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse: the builder of medley packages and sealed pins).
Your role: a strict reviewer of the build driver's selection logic. Only state what you can verify from the diff; if
uncertain, say so; do not guess.

Background (static):
- package.build() screens the pool (cached step A, the clip scorer's verdicts, L-v 2 and CUTTABLE, G17a, hook ratings,
  the second vendor), then asks a writer model for ANGLES. It judges line-ups on the clips ALONE (medley(); a budget of
  8 JUDGED line-ups per build, where a verdict served from its recording is free), writes and gates the passing ones,
  and returns a package or why none.
- The router serves a recorded reply to byte-identical bytes (role, back-end, prompt, max_tokens, seed) as
  cached=True, free and deliverable.
- Ruling 66's first part (audited and committed, 912370bf):
  - package.load_candidate(record, index) rebuilds a tried line-up that passed the clips-alone verdict from an
    earlier build's record (package.json): its angle and the angle's back-end, its clips in order, and its seeds
    (ai, n_lineup).
  - build(candidate=...) then tries ONLY that line-up, after the same pool stages, with its own seeds, so its recorded
    calls are served. It closes the candidate (out["candidate"]) when a clip left the pool, the hook no longer opens,
    exactly its clips no longer form a line-up, or its clips-alone verdict fails now.
  - proof_ledger --from-candidate BUILD_DIR[:N] runs it.

The ruling this diff implements (ORCHESTRATOR, verbatim):
13:18: "66. A PASSED LINE-UP IS KEPT. Any line-up that passes the clips-alone verdict is recorded as a CANDIDATE
(clips, order, the verdict, the gated takeaway and title if written) and stays a candidate until one of its clips is
delivered, ages out, or fails a gate. Every build first tries the open candidates, newest first, before asking for new
angles."
14:02, answering my question: "66, YOUR QUESTION: a candidate whose clips still pass but whose LINE fails again (the
takeaway, or the title after ruling 65's extra write) is CLOSED for 6 hours, then may be tried once more with fresh
writes; it is closed for good when a clip is delivered, ages out or fails a gate. Open candidates are tried newest
first inside the 8 judged line-ups, recorded verdicts free, before any angle is asked. Build it after the re-seal is
out."

The change:
1. pipeline/candidates.py (new, pure functions; the driver does the file I/O). The registry is {"records": [build
   dirs seeded], "candidates": {"id+id+id": entry}}.
   - seed(reg, record, source), once per record:
     - every tried entry with medley_ok True, a list line-up, and no "candidate" flag (not itself a candidate's try)
       becomes a candidate: one per line-up, from the earliest record;
     - a line-up the record packaged is closed;
     - a record written BEFORE the registry (no "registry" flag) applies the outcome of the candidate it tried
       (out["candidate"]): "package" for a PACKAGE result, else its class, else "clip".
   - outcome(entry, cls, at, build, why):
     - "package" and "clip" -> closed;
     - "line" -> resting until at + 6 h, or closed if its fresh try was already used;
     - "budget" -> unchanged;
     - any other class raises.
   - due(reg, now), newest first by found_at: every open entry (fresh False), and every resting one whose 6 h are
     over (fresh True).
   - run_due(reg, now, try_one, lineups, build): tries the due candidates in that order while judged line-ups are
     left (lineups -= judged), applies each outcome, and stops at the first "package". A fresh try sets fresh_used
     first.
2. package.build():
   - out["candidate"]["class"] is "package" | "clip" (closed before any call, the verdict fails now, a clip dropped
     or re-lined) | "line" (its clips passed, at least one write, not re-lined, no package) | "budget" (not tried,
     budget_stop, or ruling 5's per-package budget, now marked rec["budget"]).
   - rec["relined"] is recorded after the writes.
   - candidate["write_seed"] (default 0) is added to every write's seed (write_takeaway, and ruling 65's
     rewrite_alone): "fresh writes" seeds no recorded write used. The clips-alone verdict keeps its recorded seed.
   - out["candidate"]["fresh"] records it.
3. tests/package/proof_ledger.py:
   - BEFORE anything is written (in the existing refusal block, exit 2 on failure), the registry
     tests/package/proof/CANDIDATES.json is read (or started empty) and seeded from every
     tests/package/proof/ledger_*/package.json.
   - Then, without --from-candidate: CA.run_due with try_one = load_candidate from the entry's record. A record that
     cannot rebuild it gives class "clip", with the reason and no build call. Otherwise
     build(candidate=..., lineups=left), with write_seed = 1000 on a fresh try.
   - If no candidate packages: the normal build (angles) with the judged line-ups left. With none left, no angle is
     asked (why_none says so).
   - With --from-candidate: that candidate alone, and its outcome is applied to the registry.
   - The record gets candidate_tries and "registry": True.
   - After package.json is written, the record is seeded (its new passed line-ups join), and the registry is saved
     atomically (tmp + os.replace).
4. Tests: test_candidates.py (6, new) and test_medley (+1: the class for package / clip / clip / line, and the fresh
   seeds 1108 / 1109 with the verdict's seed 8). All 13 suites OK.

Real data (read only): seeding the 38 build records gives 6 candidates.
- Closed as packaged: 07:37's (pin d2657bbe) and 12:22's (the 18:33 PACKAGE, now rendering as 0c68b589).
- Open: 10:48's, 09:22's, 08:39's and 04:05's.
- load_candidate refuses all four open ones ("does not open on its angle's hook (ruling 59 c)": records made before
  ruling 59), so a build closes them as "clip", with that reason, before any pool stage or paid call.

Stated readings (say so if you read the ruling differently):
- K1: "recorded as a CANDIDATE": the build record already holds everything (clips, order, verdict, writes).
  - The registry indexes records and keeps each candidate's state.
  - Seeding from all records makes every line-up that ever passed a candidate, including those from before the
    registry.
- K2: "fails a gate" closes it for good. That covers: a clip left the pool; its hook, line-up rules or clips-alone
  verdict fail now; a clip is dropped (exclusion, L-v 2, CUTTABLE, step A re-screen); and it cannot be rebuilt as
  judged (e.g. it does not open on its angle's own rated hook, ruling 59 c).
- K3: "a LINE fails again": its clips passed now, and at least one write was made and failed its gates without a
  re-line. The first try replays its recorded writes (free; ruling 65 may still rescue a caption or title). Its
  6-hour retry writes with fresh seeds (write_seed 1000), and the clips-alone verdict keeps its recorded seed.
- K4: "inside the 8 judged line-ups": the candidates and the angle build share one budget of 8 JUDGED line-ups.
  Ruling 41's per-build $3 search budget applies inside each build() call; candidate tries are mostly served from
  recordings.
- K5: a candidate never reached (the budget ran out, or a package came first) stays as it was.

Check in particular:
- the 6-hour / one-fresh-try / closed-for-good state machine against the 14:02 text;
- that no candidate is tried twice in one build, and none is re-added after closing;
- that "line" can never be assigned to a clip-level failure, nor "clip" to a pure line failure;
- the budget accounting across candidates and the angle build;
- the driver's read-before-write and the atomic registry save;
- that nothing changes for a build with no due candidate (the normal build, 8 line-ups, write_seed 0).

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
