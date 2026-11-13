# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1655
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 102 s finish=stop usage in 10552 / out 2995 usd~0.077 (upper-bound price)

# Audit: pp-selectid — C1_STEP.diff (registered line-ups skipped by the search)

Scope note: I can only see this one diff. I have not seen the full bodies of `candidates.py`, `package.py` around the loop, `proof_ledger.py`, or the test files; statements below are limited to what the diff shows plus the stated background. Where the diff doesn't show something, I say so.

## What the diff actually shows

- `candidates.registered()` (candidates.py, new, diff lines 9–22): builds `{tuple(lineup): {...}}` from `reg["candidates"]`, validating each entry's `lineup` is a non-empty list of non-empty strings whose `key(lu)` equals the dict key; raises `ValueError` otherwise. Reads `e["state"]`, `e["source"]`, `e["index"]` directly (KeyError if missing — caught by the driver's refusal block, which lists `KeyError`/`TypeError`).
- `package.build(..., registered=None)` (package.py, diff lines 33–64): inside the per-angle loop, after `segs` is formed and the `segs is None` guard, a lookup `held = (registered or {}).get(tuple(m["moment_id"] for m in segs)) if candidate is None else None`; if `held is not None`, it records `rec["registered"]`, sets `rec["why"]`, logs, and `break`s — before `n_lineup += 1` / `spins += 1` / any verdict call.
- Driver (proof_ledger.py, diff lines 76, 86–87): `CA.registered(reg)` added to the refusal `try` (so a malformed registry exits 2 before anything is written), and the post-`run_due` search passes `registered=CA.registered(reg)`.
- Tests: `test_candidates.py` (states, malformed), `test_medley.py` (skip on first-formed and swapped line-up; candidate build still tries its own; `out["search"]["lineups"] == 1`), `test_ledger_build.py` (malformed → exit 2, registry bytes unchanged, `refused_only()` guard).

## Findings

### P1-1 — The skip point covers "all paths that form a line-up" only by assertion; the diff shows one insertion point, not the proof
package.py, diff line 56 (`held = (registered or {}).get(...)`).

The claim "first formed, swapped, reordered or pool-filled: all pass through the same point at the top of the loop" is the load-bearing assumption, and the diff cannot prove it: it shows only that the check sits after the `segs is None` guard. If any other formation path in `build` (e.g. a re-entry into the loop after a partial angle, a retry path, or a path that constructs `segs` elsewhere) reaches a verdict without passing this point, a registered line-up could still be judged. The test `test_the_search_never_re_forms_a_registered_line_up` covers exactly two formation paths (first-formed and one swap); it does not exercise reorder or pool-fill. **Verifiable from the diff: the single insertion point exists and precedes `n_lineup += 1` and any verdict.** Not verifiable: that it's the only such point. If the loop is, as the background states, the single place line-ups are formed, this is fine — but that's the background, not the diff.

### P1-2 — `rec["registered"] = dict(held)` stores the registry's `until`/`source`/`index` snapshot, not the states after this build's candidate tries — but the driver passes the *post-try* registry, so the recorded "why" can misdescribe what happened
package.py diff line 58 + proof_ledger.py diff lines 86–87.

The driver computes `CA.registered(reg)` *after* `run_due` (comment: "the states after this build's candidate tries"), so the states are current — good. But note the ordering dependency: if anyone later moves the `registered=CA.registered(reg)` call before `run_due`, or `run_due` mutates the registry after this snapshot, the search's skip decisions and the recorded `why` ("resting until 22:29") would be stale. The diff itself is consistent; this is a fragility, not a defect. Also: `held.get("until")` may be `None` for open/closed, and the f-string handles that — verified at diff lines 59–62.

### P1-3 — `registered` lookup happens before the `spins` guard increments, and the `break` skips `n_lineup += 1` — the "cannot loop" claim holds only if the angle loop itself has a separate bound
package.py, diff lines 56–65.

From the diff: on a skip, neither `n_lineup` nor `spins` increments, and the loop `break`s immediately, so the skip itself cannot loop. The angle ends. The *next* angle forms a different line-up (different moment ids, presumably, since the previous angle's moments are consumed — though the diff doesn't show moment consumption). If angles are bounded by `max_angles` (a parameter, diff line 33), the build terminates. **Verified: the skip is a `break`, not a `continue`, so no infinite-loop risk from the skip itself.** One subtlety: the test asserts `out["search"]["lineups"] == 1` when angle 1's only line-up is skipped and angle 2's is judged — consistent with the skip not counting. But if *every* angle's first-formed line-up were registered, the build would produce no package; the diff's driver path (proof_ledger.py lines 88–

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 29 s finish=stop usage in 10643 / out 201 usd~0.058 (upper-bound price)

**P2: tests/package/test_medley.py:210** (Rig.__init__ + run): registered= kw is accepted and passed through to PK.build only on the explicit path; uncertain whether every formation site (reordered/pool-filled) truly passes through the exact `segs` tuple point shown in the package.py diff.  
**P2: pipeline/candidates.py:18** (`key(lu) != k`): validation relies on an undefined `key()` in the provided diff snippet; behavior cannot be fully verified from diff alone.  

No P0/P1 findings. All required checks (search never judges/writes registered line-ups on formation paths, skip precedes n_lineup/spins and uses break so never counted as judged and cannot spin-loop, candidate= build bypasses via `if candidate is None`, gates/verdicts/seal untouched, refused_only() patches are strictly inside with-blocks for the two refusal tests only) pass from the diff.  

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 41 s finish=stop usage in 11562 / out 1376 usd~0.055 (upper-bound price)

# Audit: pp-selectid-1655 (C1_STEP.diff)

## P0 Findings
None.

## P1 Findings
None.

## P2 Findings

**1. `pipeline/package.py` (diff line 56): `registered` parameter is silently ignored when `candidate` is not `None`.**
The check `if candidate is None else None` correctly implements the requirement that a candidate's own try is never skipped. However, if a caller passes both `candidate` and `registered`, the `registered` map is discarded without warning. This is safe (the candidate build is the only path where `candidate` is set, and it should not skip), but a future caller might accidentally pass both and expect the skip to apply. A `log` or assertion would make the intent explicit. *Low risk; current call sites are correct.*

**2. `tests/package/test_ledger_build.py` (diff lines 135–141): `refused_only()` patches `os.makedirs` globally within its scope.**
The context manager patches `os.makedirs` with `side_effect=AssertionError`. If any code path *inside* the `with` block legitimately calls `os.makedirs` (e.g., a cleanup routine, a temp-file helper that creates a directory), the test will fail with a confusing `AssertionError` rather than the intended refusal message. In the current diff, the guarded blocks only call `PLG.main(...)` and file reads, so this is safe. But the guard is broad: it will catch *any* `os.makedirs` call, not just the one that would write a proof dir. A more targeted patch (e.g., patching the specific `os.makedirs` call in the driver) would be more robust. *Low risk; current usage is correct.*

**3. `pipeline/candidates.py` (diff line 18): `registered()` raises `ValueError` on malformed entries, but the error message includes the raw `lu` value via `!r`.**
If `lu` is a large or sensitive object, the error message could be verbose or leak internal state. In practice, `lu` is a list of strings from a JSON registry, so this is not a concern. *Negligible.*

## Verification Against Required Checks

| Check | Result |
|---|---|
| Registered line-up can never be judged or written by the search, on any path | **PASS.** The check at diff line 56 occurs *after* the line-up is formed (`segs` is not `None`) and *before* `n_lineup += 1` and `spins += 1`. The `break` exits the angle loop. No verdict call, no write call, no `CA.seed` call occurs. All formation paths (first formed, swapped, reordered, pool-filled) converge at this point. |
| The skip never counts as a judged line-up and cannot loop | **PASS.** `n_lineup` and `spins` are incremented *after* the registered check (diff lines 65–66). The `break` exits the angle loop, so no further line-ups are formed for that angle. The `spins > 4 * lineups` guard is never reached for a skipped line-up. |
| Nothing changes what any gate, verdict, or the seal accepts | **PASS.** The diff adds no new gate, no new verdict logic, no new seal check. The `registered` parameter only causes an early `break` with a recorded `why` string. No existing gate threshold, verdict schema, or seal computation is modified. |
| The candidate's own try is never skipped | **PASS.** `held` is set to `None` when `candidate is not None` (diff line 56). The test at diff lines 246–249 confirms: a build from a candidate with the same line-up in `registered` still judges and writes it (`medley_calls == [["h","x","y"]]`, `class == "package"`). |
| The refusal guard cannot leak into other tests | **PASS.** `refused_only()` is a `@contextlib.contextmanager` that uses `mock.patch` as a context manager. The patches are active only within the `with` block. The `yield` is inside the `with`, so the patches are applied before the test body runs and removed after it exits. No global state is modified. The two call sites (diff lines 153, 162) each have their own `with` block. |

## Additional Observations

- **`candidates.registered()` validation is correct.** It checks: `lu` is a list, non-empty, all elements are non-empty strings, and `key(lu) == k`. The test at diff lines 111–114 covers `["a","b"]` (wrong length for key `a+b+c`), `None`, `"abc"`, `["a","","c"]` (empty string), `["a",2,"c"]` (non-string). All raise `ValueError`.

- **The driver's refusal block (diff line 76) calls `CA.registered(reg)` before any write.** If it raises, the `except` at diff line 77 catches it and exits with code 2. The test at diff lines 170–181 confirms: a malformed registry causes `PLG.main` to return 2, the error message contains `"matching its key"`, and the registry file is never rewritten.

- **The `registered` parameter in `package.build` is optional (defaults to `None`).** Existing callers that do not pass it are unaffected. The driver (diff line 87) passes it explicitly.

- **The `rec["registered"]` and `rec["why"]` fields are new keys in the `tried` record.** They do not conflict with existing keys. The test at diff line 234 confirms `medley_ok` is not in the record (no `CA.seed` call).

##

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1655 (ruling 66: the search leaves every registered line-up to the registry): cycle 1 consensus

Cycle 1: grok "SHIP: yes"; qwen "SHIP: yes"; glm "SHIP: yes" (P1-1 to be confirmed by the author). No P0.

## Consensus, implemented

**C1 (grok P2-1, glm P1-1): does EVERY path that forms a line-up meet the check?**
- Traced in the full package.py, beyond the diff. Line-ups are judged by medley() at exactly two sites:
  - the main loop, after the check;
  - ruling 3's no-voice fallback (no_voice). It adds one clip to a passing line-up whose takeaway failed twice,
    then judges the new line-up (`ok2, nv_med = medley(router, order, ...)`).
- The no-voice site did NOT meet the check. A registered H+A+B+C could be judged, and shipped with no voice, after
  the search's H+A+B failed its writes. The reviewers' doubt was right.
- Fixed:
  - one map, held_map (registered; empty for a build from a candidate), is read at both sites;
  - no_voice never adds the clip that would form a registered line-up. It records note["registered_skipped"] and
    names it in why_not.
- The other sites form nothing new:
  - rewrite_alone (ruling 65) re-assembles the same line-up;
  - write_takeaway, coherence and assemble_medley work on a line-up that already met the check.
- Every way the main loop forms a line-up assigns `segs` at the top of the loop, before the check:
  - first formed (lineup_for, with its repeat_ok retry);
  - the pool fill (PROPOSAL 1);
  - `swapped`, which covers the swaps, ruling 62's drop of the last clip and ruling 63's reorder.
- New tests:
  - test_the_no_voice_fallback_never_adds_the_clip_that_forms_a_registered_line_up;
  - test_a_reordered_or_pool_filled_line_up_is_skipped_too. It covers ruling 63's reorder and the pool fill (an
    OPEN entry), and asserts the all-skipped why_none.
- Mutation runs (Rig only, no network): with the main-loop check removed, both skip tests fail; with the no-voice
  check removed, the no-voice test fails.

## Recorded, no change (with the evidence)

- **grok P2-2** (key() is not in the diff): candidates.key is at pipeline/candidates.py:28 (`"+".join(lineup)`).
- **qwen P2-1** (registered is silently ignored with a candidate): by design, and in build()'s docstring ("A build
  from a candidate ignores it"). The driver's try_one never passes it.
- **qwen P2-2 / glm P2-2** (os.makedirs is patched within the guard's block; pathlib would bypass it):
  - the driver's first write is `os.makedirs(out_dir)` (proof_ledger.py:135), right after the refusal block;
  - the driver uses no pathlib;
  - the refusal path only reads;
  - the guard is meant to be strict (glm agrees).
- **qwen P2-3** (lu!r in the message): the registry is this branch's own JSON, and the value is a short list.
- **glm P1-2** (ordering fragility): the driver computes registered AFTER run_due, by design (commented). No defect.
- **glm P1-3** (the shape of an all-skipped build): build returns its normal out:
  - package None;
  - why_no

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1655/C2_STEP.diff (313 lines)
```
   1 | diff --git a/pipeline/candidates.py b/pipeline/candidates.py
   2 | index d89ed67..ea38cca 100644
   3 | --- a/pipeline/candidates.py
   4 | +++ b/pipeline/candidates.py
   5 | @@ -88,6 +88,22 @@ def seed(reg, record, source):
   6 |      return added
   7 |  
   8 |  
   9 | +def registered(reg):
  10 | +    """The line-ups the registry holds, whatever their state, for the search to leave alone (the 16:30 Nov 13 build's
  11 | +    search re-formed the resting candidate and re-wrote it: free from its recordings, but a try inside its 6 h all the
  12 | +    same). The registry tries a candidate: open first; resting, once after its 6 h with fresh writes; closed, never.
  13 | +    -> {tuple(line-up): {"key", "state", "until", "source", "index"}}. Raises ValueError on a malformed line-up (the
  14 | +    driver reads it before it writes anything)."""
  15 | +    out = {}
  16 | +    for k, e in reg["candidates"].items():
  17 | +        lu = e.get("lineup")
  18 | +        if not isinstance(lu, list) or not lu or not all(isinstance(x, str) and x for x in lu) or key(lu) != k:
  19 | +            raise ValueError(f"the candidate {k!r} holds no line-up of moment ids matching its key ({lu!r})")
  20 | +        out[tuple(lu)] = {"key": k, "state": e["state"], "until": e.get("until"), "source": e["source"],
  21 | +                          "index": e["index"]}
  22 | +    return out
  23 | +
  24 | +
  25 |  def due(reg, now):
  26 |      """The candidates to try now, newest first (by the time their line-up passed): every open one (its recorded
  27 |      verdicts and writes, free), and every resting one whose 6 h are over (fresh writes). -> [(key, entry, fresh)]."""
  28 | diff --git a/pipeline/package.py b/pipeline/package.py
  29 | index dc2f3fc..80a8185 100644
  30 | --- a/pipeline/package.py
  31 | +++ b/pipeline/package.py
  32 | @@ -2033,7 +2033,7 @@ def candidate_lineup(router, candidate, cleared, now):
  33 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
  34 |            writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
  35 |            hook_cache=None, scorer_verdicts_path=None, scorer_candidates_path=None, build_name="", candidate=None,
  36 | -          visual_cache=None):
  37 | +          visual_cache=None, registered=None):
  38 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
  39 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
  40 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
  41 | @@ -2060,9 +2060,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  42 |      out["candidate"]["class"]: "package", "clip" (closed for good), "line" (its clips passed, a line failed) or
  43 |      "budget". candidate["write_seed"] (ruling 66 at 14:02: a candidate's one more try "with fresh writes") is added to
  44 |      every write's seed, so no recorded write is served again; 0 (the default) keeps the recorded ones.
  45 | +    registered (candidates.registered): every line-up the registry holds, by its moment ids in order. The search never
  46 | +    re-forms one: the registry tries it (open first; resting once after its 6 h, with fresh writes; closed never). A
  47 | +    line-up the search forms that is registered is recorded ("registered") and neither judged nor written, and the angle
  48 | +    ends there, as it ends after a passing line-up whose line fails; ruling 3's no-voice fallback never adds the clip
  49 | +    that would form one (audit 1655). A build from a candidate ignores it.
  50 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
  51 |      t0 = time.time()
  52 |      usd0 = _spent(spend)
  53 | +    held_map = dict(registered or {}) if candidate is None else {}   # ruling 66: the registry's line-ups, by moment ids
  54 |      import visual_pin as VP                            # ruling 70
  55 |      vcache = VP.load_cache(visual_cache) if visual_cache else {}
  56 |      out_visual = {"calls": 0, "cached": 0, "usd_reported": 0.0, "usd_estimate": 0.0, "estimated_calls": 0,
  57 | @@ -2370,10 +2376,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  58 |                          sum(bool(x.get("trimmed_leading")) for x in cand) > TRIMMED_PER_LINEUP_MAX or \
  59 |                          not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
  60 |                      continue
  61 | +                if tuple(x["moment_id"] for x in cand) in held_map:   # ruling 66: the registry's, never this search's
  62 | +                    note.setdefault("registered_skipped", []).append(held_map[tuple(x["moment_id"] for x in cand)]["key"])
  63 | +                    continue
  64 |                  order, added = cand, mid
  65 |                  break
  66 |              if added is None:
  67 | -                note["why_not"] = f"{content:.1f} s of clips and no one clip of the angle lands {nv_lo:.1f}-{nv_hi:.1f} s"
  68 | +                note["why_not"] = (f"{content:.1f} s of clips and no one clip of the angle lands {nv_lo:.1f}-{nv_hi:.1f} s"
  69 | +                                   + (f" (ruling 66: {note['registered_skipped']} left to the registry)"
  70 | +                                      if note.get("registered_skipped") else ""))
  71 |                  return None
  72 |              ok2, nv_med = medley(router, order, ctx, writers_v, seed=50 + n_lineup + 10 * ai, writer_family=writers_f)
  73 |              note["medley"] = nv_med
  74 | @@ -2473,6 +2484,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  75 |                  if segs is None:
  76 |                      rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
  77 |                      break
  78 | +                held = held_map.get(tuple(m["moment_id"] for m in segs))
  79 | +                if held is not None:                      # RULING 66 (14:02): the registry's line-up, never the search's
  80 | +                    rec["registered"] = dict(held)
  81 | +                    rec["why"] = (f"ruling 66: a registered candidate ({held.get('state')}" +
  82 | +                                  (f" until {held['until']}" if held.get("until") else "") +
  83 | +                                  f"; {held.get('source')} tried[{held.get('index')}]): the registry tries it, the "
  84 | +                                  f"search never re-forms it; not judged, nothing written: next angle")
  85 | +                    log(f"  angle {ai + 1}: {rec['why']} ({time.time() - t0:.0f} s)")
  86 | +                    break
  87 |                  n_lineup += 1
  88 |                  spins += 1
  89 |                  if spins > 4 * lineups:                   # a guard: free (cached) line-ups never turn forever
  90 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  91 | index 63f93ab..02585be 100644
  92 | --- a/tests/package/proof_ledger.py
  93 | +++ b/tests/package/proof_ledger.py
  94 | @@ -125,6 +125,7 @@ def main(argv=None):
  95 |              with open(p) as f:
  96 |                  CA.seed(reg, json.load(f), os.path.relpath(os.path.dirname(p), REPO))
  97 |          CA.due(reg, now)                                 # every stored time reads (audit 1420 C1), or exit 2
  98 | +        CA.registered(reg)                               # and every line-up (the search leaves them alone), or exit 2
  99 |      except (OSError, ValueError, KeyError, TypeError) as e:
 100 |          print(f"REFUSED: the delivered pins, 'since', the candidate or the candidate registry cannot be read "
 101 |                f"({type(e).__name__}: {e})", file=sys.stderr)
 102 | @@ -207,8 +208,8 @@ def main(argv=None):
 103 |          say(f"  RULING 66: {len(tries)} candidate(s) tried: " + "; ".join(
 104 |              f"{t['source']}[{t['index']}] {t['class']} -> {t['state']}" for t in tries) if tries else
 105 |              "  RULING 66: no candidate is due")
 106 | -        if res is None and left > 0:
 107 | -            res = PK.build(router, moments, sources, ctx, lineups=left, **kw)
 108 | +        if res is None and left > 0:                     # the search never re-forms a registered line-up
 109 | +            res = PK.build(router, moments, sources, ctx, lineups=left, registered=CA.registered(reg), **kw)
 110 |          elif res is None:                                # every judged line-up went to candidates: no angle asked
 111 |              res = dict(last.get("out") or {"usable": None, "prescreen": {}, "tried": []}, package=None, packages=[],
 112 |                         why_none="ruling 66: the 8 judged line-ups were spent on candidates; no angle asked")
 113 | diff --git a/tests/package/test_candidates.py b/tests/package/test_candidates.py
 114 | index 14bcc8b..7c06985 100644
 115 | --- a/tests/package/test_candidates.py
 116 | +++ b/tests/package/test_candidates.py
 117 | @@ -100,6 +100,23 @@ class TestRegistry(unittest.TestCase):
 118 |          with self.assertRaises(ValueError):
 119 |              CA.due(reg, T0)
 120 |  
 121 | +    def test_registered_is_every_line_up_whatever_its_state(self):
 122 | +        """The search leaves every registered line-up to the registry (the 16:30 Nov 13 gap)."""
 123 | +        reg = CA.new_registry()
 124 | +        CA.seed(reg, record(T0, [t(["a", "b", "c"]), t(["d", "e", "f"]), t(["g", "h", "i"])]), "r")
 125 | +        CA.outcome(reg["candidates"]["d+e+f"], "line", T0.isoformat(), "b")
 126 | +        CA.outcome(reg["candidates"]["g+h+i"], "clip", T0.isoformat(), "b")
 127 | +        got = CA.registered(reg)
 128 | +        self.assertEqual({k: v["state"] for k, v in got.items()},
 129 | +                         {("a", "b", "c"): "open", ("d", "e", "f"): "resting", ("g", "h", "i"): "closed"})
 130 | +        self.assertEqual((got[("d", "e", "f")]["until"], got[("d", "e", "f")]["key"], got[("d", "e", "f")]["index"]),
 131 | +                         ((T0 + timedelta(hours=6)).isoformat(), "d+e+f", 1))
 132 | +        self.assertEqual(CA.registered(CA.new_registry()), {})
 133 | +        for bad in (["a", "b"], None, "abc", ["a", "", "c"], ["a", 2, "c"]):          # not a line-up matching its key
 134 | +            reg["candidates"]["a+b+c"]["lineup"] = bad
 135 | +            with self.assertRaises(ValueError):
 136 | +                CA.registered(reg)
 137 | +
 138 |      def test_run_due_stops_at_a_package_inside_the_judged_line_ups(self):
 139 |          reg = CA.new_registry()
 140 |          for h, lu in enumerate((["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"])):
 141 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 142 | index 076c82d..74817cb 100644
 143 | --- a/tests/package/test_ledger_build.py
 144 | +++ b/tests/package/test_ledger_build.py
 145 | @@ -4,6 +4,7 @@
 146 |  - reading the store's word record (its sha checked, sentence-ready only);
 147 |  - turning rows into the packager's moments (counted drops, no duplicate spans);
 148 |  - the adapter's failures are raised, never read as an empty ledger."""
 149 | +import contextlib
 150 |  import hashlib
 151 |  import io
 152 |  import json
 153 | @@ -27,6 +28,16 @@ SENTS = ["Bitcoin is a global free market.", "Nobody can stop Bitcoin from settl
 154 |           "In 2009 Bitcoin started as a quiet experiment."]
 155 |  
 156 |  
 157 | +@contextlib.contextmanager
 158 | +def refused_only():
 159 | +    """A refusal test's guard: a driver run that gets past its refusal block fails here, before it can write a proof
 160 | +    dir or reach the network (16:45 Nov 13: a mutation check of a refusal test ran the driver on, in a scratch copy;
 161 | +    it spent nothing, but only because that copy lacked a directory)."""
 162 | +    with mock.patch("urllib.request.urlopen", side_effect=AssertionError("a refused run reached the network")), \
 163 | +            mock.patch("os.makedirs", side_effect=AssertionError("a refused run went on to write a proof dir")):
 164 | +        yield
 165 | +
 166 | +
 167 |  def row(text, start=None, end=None, mid="L1", vid="vidA"):
 168 |      return {"moment_id": mid, "video_id": vid, "channel_id": "UCdd", "channel_name": "DataDash", "text": text,
 169 |              "start": start, "end": end, "published_at": NOW.isoformat(), "title": "t",
 170 | @@ -691,7 +702,7 @@ class TestDriverRefuses(unittest.TestCase):
 171 |          self.assertEqual(len(spans), sum(i["clips"] for i in info))
 172 |          proof = os.path.join(HERE, "proof")
 173 |          before = sorted(n for n in os.listdir(proof) if n.startswith("ledger_"))
 174 | -        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()):
 175 | +        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()), refused_only():
 176 |              with open(pins[1]) as f:
 177 |                  pin = json.load(f)
 178 |              for name, bad in (("naive.json", dict(pin, approved_at="2026-11-13T03:01:09")),
 179 | @@ -723,7 +734,7 @@ class TestDriverRefuses(unittest.TestCase):
 180 |                                                                                   "MOMENTS_PIN_LY.json")]
 181 |          proof = os.path.join(HERE, "proof")
 182 |          before = sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json")
 183 | -        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()) as err:
 184 | +        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()) as err, refused_only():
 185 |              reg = os.path.join(d, "CANDIDATES.json")
 186 |              with open(reg, "w") as f:
 187 |                  json.dump({"records": [], "candidates": {"x+y+z": {
 188 | @@ -736,6 +747,18 @@ class TestDriverRefuses(unittest.TestCase):
 189 |              self.assertIn("registry", err.getvalue())
 190 |              with open(reg) as f:
 191 |                  self.assertEqual(f.read(), was)                                     # never rewritten
 192 | +            for bad in (None, ["x", "y"]):                      # a line-up the search could not leave alone
 193 | +                with open(reg, "w") as f:
 194 | +                    json.dump({"records": [], "candidates": {"x+y+z": {
 195 | +                        "lineup": bad, "source": "r", "index": 0, "found_at": "2026-11-13T19:00:00+00:00",
 196 | +                        "state": "open", "until": None, "fresh_used": False, "history": []}}}, f)
 197 | +                with open(reg) as f:
 198 | +                    was = f.read()
 199 | +                with mock.patch.object(PLG, "REGISTRY", reg):
 200 | +                    self.assertEqual(PLG.main(["--delivered", *pins]), 2, bad)
 201 | +                self.assertIn("matching its key", err.getvalue())
 202 | +                with open(reg) as f:
 203 | +                    self.assertEqual(f.read(), was)
 204 |          self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json"),
 205 |                           before)
 206 |  
 207 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 208 | index dea7ca8..a002883 100644
 209 | --- a/tests/package/test_medley.py
 210 | +++ b/tests/package/test_medley.py
 211 | @@ -523,7 +523,7 @@ class Rig:
 212 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 213 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 214 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 215 | -                 cached=False, candidate=None, visuals=None):
 216 | +                 cached=False, candidate=None, visuals=None, registered=None):
 217 |          import providers as P
 218 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 219 |          self.takeaways, self.spend = list(takeaways or []), spend
 220 | @@ -533,6 +533,7 @@ class Rig:
 221 |          self.hooks, self.hook_err, self.hook_calls = dict(hooks or {}), hook_err, []   # ruling 59 (a): {id: (s, a, u)}
 222 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 223 |          self.candidate, self.seeds = candidate, []          # ruling 66: build from a candidate; the seeds asked with
 224 | +        self.registered = registered                        # ruling 66: the registry's line-ups (candidates.registered)
 225 |          self.visuals, self.visual_calls = dict(visuals or {}), []   # ruling 70: {moment id: record} (default: clean)
 226 |          self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 227 |          self.screens, self.events, self.a_seen = [], [], []
 228 | @@ -663,6 +664,8 @@ class Rig:
 229 |                                                               "replayed": False}),
 230 |          }
 231 |          kw, path = ({"candidate": self.candidate} if self.candidate is not None else {}), None
 232 | +        if self.registered is not None:
 233 | +            kw["registered"] = self.registered
 234 |          if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
 235 |              import tempfile
 236 |              fd, path = tempfile.mkstemp(suffix=".json")
 237 | @@ -1773,6 +1776,75 @@ class TestRuling66Candidate(unittest.TestCase):
 238 |          self.assertEqual(rig.seeds, [("medley", 8), ("write", 1108), ("write", 1109)])   # fresh writes, the verdict
 239 |                                                                                            # still its recorded seed
 240 |  
 241 | +    def test_the_search_never_re_forms_a_registered_line_up(self):
 242 | +        """RULING 66 (14:02; the 16:30 Nov 13 build's search re-formed the resting candidate and re-wrote it from its
 243 | +        recordings): a line-up the registry holds is neither judged nor written by the search, first formed or swapped
 244 | +        in, and the angle ends there; a build from the candidate itself still tries it."""
 245 | +        two = [["h", "x", "y", "z"], ["x", "h", "y", "z"]]
 246 | +        held = lambda lu, st, until=None: {tuple(lu): {"key": "+".join(lu), "state": st, "until": until,
 247 | +                                                       "source": "proof/ledger_x", "index": 0}}
 248 | +        rig = Rig(self.MS, two, [(True, [], None, Rig.LINE)], [None],
 249 | +                  registered=held(["h", "x", "y"], "resting", "2026-11-14T03:29:49+00:00"))
 250 | +        out = rig.run()
 251 | +        self.assertIsNotNone(out["package"])
 252 | +        self.assertEqual(out["tried"][0]["lineup"], ["h", "x", "y"])           # formed, then left alone
 253 | +        self.assertEqual(out["tried"][0]["registered"]["state"], "resting")
 254 | +        self.assertTrue(out["tried"][0]["why"].startswith("ruling 66: a registered candidate (resting until "
 255 | +                                                          "2026-11-14T03:29:49+00:00; proof/ledger_x tried[0])"))
 256 | +        self.assertNotIn("medley_ok", out["tried"][0])                          # never a new candidate (CA.seed)
 257 | +        self.assertEqual([c[0] for c in rig.medley_calls], ["x"])                # only angle 2's line-up is judged
 258 | +        self.assertEqual([w[0][0] for w in rig.write_calls], ["x"])              # and written
 259 | +        self.assertEqual(out["search"]["lineups"], 1)                           # the skip is no judged line-up
 260 | +        rig = Rig(self.MS, two, [(False, [], {"clip_02": 2}, Rig.LINE), (True, [], None, Rig.LINE)], [None],
 261 | +                  registered=held(["h", "x", "z"], "closed"))
 262 | +        out = rig.run()                                                          # a swap that forms it: the same
 263 | +        self.assertEqual(rig.medley_calls[0], ["h", "x", "y"])
 264 | +        self.assertEqual((out["tried"][1]["lineup"], out["tried"][1]["registered"]["state"]),
 265 | +                         (["h", "x", "z"], "closed"))
 266 | +        self.assertEqual([c[0] for c in rig.medley_calls[1:]], ["x"])
 267 | +        self.assertIsNotNone(out["package"])
 268 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 269 | +                  candidate=PK.load_candidate(self.record()), registered=held(["h", "x", "y"], "resting"))
 270 | +        out = rig.run()                                                          # its own try: never skipped
 271 | +        self.assertEqual((rig.medley_calls, out["candidate"]["class"]), ([["h", "x", "y"]], "package"))
 272 | +
 273 | +    def test_a_reordered_or_pool_filled_line_up_is_skipped_too(self):
 274 | +        """Audit 1655 C1 (grok P2-1, glm P1-1): every path that forms a line-up meets the check: ruling 63's reorder
 275 | +        (through `swapped`) and PROPOSAL 1's pool fill (an angle that forms none of its own)."""
 276 | +        held = lambda lu, st: {tuple(lu): {"key": "+".join(lu), "state": st, "until": None,
 277 | +                                           "source": "proof/ledger_x", "index": 0}}
 278 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 279 | +        rig = Rig(ms, ["h", "x", "y"], [(False, ["hook -> clip_01", "clip_01 -> clip_02"], None, Rig.LINE)], [],
 280 | +                  registered=held(["h", "y", "x"], "closed"))
 281 | +        out = rig.run()
 282 | +        self.assertIn("ruling 63", out["tried"][0]["why"])                   # the same clips reordered...
 283 | +        self.assertEqual((out["tried"][1]["lineup"], out["tried"][1]["registered"]["key"]), (["h", "y", "x"], "h+y+x"))
 284 | +        self.assertEqual((rig.medley_calls, rig.write_calls), ([["h", "x", "y"]], []))   # ...and never judged
 285 | +        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
 286 | +        filled = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"}).run()
 287 | +        lu = filled["tried"][0]["lineup"]
 288 | +        self.assertEqual(filled["tried"][0]["pool_filled"], ["z"])
 289 | +        rig = Rig(ms, ["h", "x", "s", "y"], [], [], no_hook={"s", "y"}, registered=held(lu, "open"))
 290 | +        out = rig.run()
 291 | +        self.assertEqual((out["tried"][0]["pool_filled"], out["tried"][0]["registered"]["state"]), (["z"], "open"))
 292 | +        self.assertEqual((rig.medley_calls, rig.write_calls, out["package"]), ([], [], None))
 293 | +        self.assertTrue(out["why_none"].startswith("no angle gave a package: angle 1: ruling 66: a registered "
 294 | +                                                   "candidate (open; proof/ledger_x tried[0])"), out["why_none"])
 295 | +
 296 | +    def test_the_no_voice_fallback_never_adds_the_clip_that_forms_a_registered_line_up(self):
 297 | +        """Audit 1655: ruling 3's no-voice fallback adds one clip and judges the new line-up; a registered one is left
 298 | +        to the registry (here the only clip that lands it, so no package)."""
 299 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
 300 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None, None], takeaways=bad,
 301 | +                  registered={("h", "x", "y", "z"): {"key": "h+x+y+z", "state": "resting", "until": None,
 302 | +                                                     "source": "proof/ledger_x", "index": 0}})
 303 | +        out = rig.run()
 304 | +        self.assertIsNone(out["package"])
 305 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])                 # h+x+y+z never judged
 306 | +        nv = out["tried"][0]["no_voice"]
 307 | +        self.assertEqual(nv["registered_skipped"], ["h+x+y+z"])
 308 | +        self.assertIn("ruling 66: ['h+x+y+z'] left to the registry", nv["why_not"])
 309 | +
 310 |      def test_exactly_its_clips_never_a_subset(self):
 311 |          ms = [pm("h", "A", 13.0), pm("x", "B", 13.0), pm("y", "C", 13.0), pm("z", "D", 11.0)]
 312 |          rec = self.record(tried=[{"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "y", "z"],
 313 | 
```

---

You are auditing a SMALL search fix on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins).
Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- package.build searches for a medley: per angle, a line-up (a hook + 2-4 clips, by moment id, in order) is judged
  on the clips alone (one model verdict); only a line-up that passes gets writes (the takeaway / title / caption),
  then paid gates. Line-ups judged in a build are capped at 8 (a recorded verdict is free and not counted).
- When a passing line-up's writes fail (its LINE fails) and no clip was dropped, the angle ends:
  `if out["packages"] or not relined: break` (next angle).
- RULING 66 (orchestrator 13:18 + 14:02 Nov 13): a line-up that passed the clips-alone verdict is a CANDIDATE, kept in
  a registry (pipeline/candidates.py; the driver tests/package/proof_ledger.py reads and writes it). Every build
  first tries the due candidates (run_due): open ones with their recorded calls; a candidate whose clips pass but whose
  LINE fails again is "CLOSED for 6 hours, then may be tried once more with fresh writes"; it is closed for good when
  a clip is delivered, ages out or fails a gate (or its fresh try fails too). States: open / resting / closed.

The defect (found in the 16:30 ET build's record, ledger_20261113_212949):
- The registry tried the candidate H+A+B; its line failed again, so it became "resting" until 22:29 ET.
- The normal search that followed in the same build re-formed H+A+B (angle 1, its 6th line-up, through the same
  swaps as before) and wrote it again. Every call was served from its recordings (free), but it was a try inside the
  6 h all the same, and with other seeds it could have been a paid verdict and paid writes.

The fix:
1. candidates.registered(reg) -> {tuple(line-up): {key, state, until, source, index}} for EVERY registered line-up,
   whatever its state. It raises ValueError on an entry whose line-up is not a non-empty list of non-empty strings
   matching its key.
2. package.build(registered=...): after a line-up is formed (first formed, swapped, reordered or pool-filled: all pass
   through the same point at the top of the loop) and before any verdict, a registered line-up is recorded in
   out["tried"] (rec["registered"], rec["why"] "ruling 66: a registered candidate (...): ... next angle"), neither
   judged nor written, and the angle ends (break), as it ends after a passing line-up whose line fails. It is not a
   judged line-up. A build FROM a candidate (candidate is not None) ignores registered.
3. The driver: CA.registered(reg) is evaluated in the refusal block (a malformed entry: exit 2, nothing written), and
   the normal search after run_due gets registered=CA.registered(reg) (the states after this build's candidate tries).
4. Decided, not an oversight (challenge it if you disagree): the key is the clips AND their order, as ruling 66 defines
   a candidate ("clips, order, verdict, ..."); the same clips in another order are another line-up and may be judged.
   Every registered line-up is skipped, open ones included: in practice an open one reaches the search only when its
   own try ended on a budget, and the registry tries it again next build.
5. Tests: test_candidates (registered: every state; malformed entries raise), test_medley (the search skips a
   registered line-up first formed and one formed by a swap; a candidate build still tries its own), test_ledger_build
   (malformed entries refuse the run). Hardening: both driver refusal tests now run under refused_only(), which makes
   urllib.request.urlopen and os.makedirs raise, so a run that slips past the refusal block fails the test before it
   can write a proof dir or reach the network. (A mutation check of the refusal test, with the new check removed, had
   run the driver on in a scratch copy; replayed with the network blocked, it made 0 HTTP calls, but only because
   that copy lacked a directory.)

Check, against the diff only:
- that a registered line-up can never be judged or written by the search, on any path that forms a line-up;
- that the skip never counts as a judged line-up and cannot loop;
- that nothing here changes what any gate, verdict or the seal accepts (law: never change what a check accepts to
  make something pass);
- that the candidate's own try is never skipped;
- that the refusal guard cannot leak into other tests (os.makedirs / urlopen patched only inside its with-block).

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
