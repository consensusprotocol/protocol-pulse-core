# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_2313
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 234 s finish=stop usage in 11747 / out 4934 usd_reported=0.000976 usd~0.109 (upper-bound price)

The audit of feature `pp-selectid-20261116_2313` reveals a critical failure in the implementation of **RULING 130 (2)** within the medley/no-voice path.

### [P0] Ruling 130 Violation in Medley/No-Voice Path
The core requirement of Ruling 130 (2) is that the lock pre-check must run **BEFORE** any paid vision check, and a clip the render cannot cut (a "hold") must not cost money.

In the main line-up loop (`pipeline/package.py` lines 57-89), this is correctly implemented: the code checks for `no_verdict` and `relined` (the "hold" state) before entering the block that executes `bg` (exclusion/truth checks) and `see(segs)` (the paid vision check).

However, in the **medley/no-voice path** (`pipeline/package.py` lines 16-32), the implementation is incomplete:
```python
18 |         if lock_check is not None:
19 |             try:
20 |                 nv_pre = lock_check(order)
21 |             except Exception as e:
22 |                 nv_pre = LP.failed(e)
23 |         if nv_pre.get("error") or not nv_pre.get("segments"):
24 |             out["lock_stop"] = note["why_not"]
25 |             return None
26 |         see(order) # <--- PAID VISION CHECK
```
The `lock_check` (via `LP.check`) returns a result where `ok=False` and `segments` is populated when a clip is "held" by the render. In this scenario:
1. `nv_pre.get("error")` is `None`.
2. `not nv_pre.get("segments")` is `False`.
3. The `if` condition fails, and the code proceeds to `see(order)`.

Consequently, any line-up in the medley path that is "held" by the lock will still trigger a paid vision check, directly violating the governing law. The user's description in the "THE CHANGE" section (b) claims that on a hold it returns `None`, but the provided code does not implement this logic.

### Other Observations
- **`lock_off` Logic**: Correct. It returns an error and empty segments, which triggers the `return None` path in both the main loop and the medley path, ensuring it never produces a "pass" (Law L-m).
- **`bg` Initialization**: Correct. By initializing `bg = {}` and wrapping the population in `if not relined and not no_verdict`, the code ensures that the subsequent `writes` loop (which reads `bg`) is either skipped (because `w_used == writes`) or operates on a valid set of results.
- **Tests**: The tests in `test_medley.py` (e.g., `test_ruling_130_a_clip_the_lock_holds_is_never_seen`) appear to target the main line-up loop via the `Rig` class and do not cover the specific medley/no-voice branch in `package.build`, allowing this P0 to slip through.

P1_OR_WORSE: 1

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 85 s finish=stop usage in 11034 / out 6853 usd_reported=0.005399 usd~0.136 (upper-bound price)



# Code Audit — RULING 130 (2): Lock Pre-Check Before Paid Vision

## Scope

I reviewed the 224-line diff implementing RULING 130 (2): reordering the render's lock pre-check (rulings 68/72) to execute **before** any paid check (vision `see()`, exclusion `exclusion_for`, truth `truth_for`), in both the main line-up loop and the no-voice line-up, plus the `--lock-precheck on|off` driver flag and its tests.

---

## Findings

### [P2] `bg = {}` orphan-future invariant is comment-only

In the main loop, when the lock passes but `vbad` subsequently triggers a re-line, the pool futures already submitted into `bg` are never collected (the writes loop is skipped via `w_used = writes`). This is **pre-existing** behaviour (the original code had the same pattern), but the new code makes the invariant more load-bearing: `bg` is now conditionally populated (`bg = {}` vs. the full dict), and the only thing preventing a silent no-op is that the writes loop's first test breaks on `w_used`. A future refactor of the writes loop that moves the `w_used` check later, or adds a second reader of `bg`, would silently discard submitted work.

Suggestion: add a one-line assertion or a `# INVARIANT: bg is read only at package.py:3878 inside the writes loop; w_used=writes guarantees we never reach it when bg=={}` comment at the `bg = {}` site, or better, gate the pool submissions behind a flag that the writes loop also checks.

Not a merge-blocker because the current code is correct and the pattern is unchanged from the original.

---

### [P3] `lock_for` iterator is per-call, not per-build

```python
def lock_for(mode, out_dir, say):
    if mode != "on":
        return lock_off
    n = iter(range(1, 10 ** 6))
    return lambda segs: LP.check(segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say)
```

Each invocation of `lock_for` creates a fresh counter. This matches the original (which used a default-argument iterator `n=iter(range(1, 10**6))` on the lambda), so numbering restarts if the build is re-entered. In practice the build is single-shot per process, so this is cosmetic. No action needed.

---

### [P3] No defensive `isinstance(pre, dict)` guard

If `lock_check(segs)` ever returned `None` (contract violation), `pre.get("error")` would raise `AttributeError` outside the `try/except` (the `except` only wraps the call, not the subsequent attribute access). The contract of `lock_precheck.check` and `LP.failed` guarantees a dict, and the original code had the same exposure, so this is not a regression. Noting for completeness.

---

## Verification of the five requested checks

| # | Question | Verdict |
|---|----------|---------|
| 1 | No paid check runs for a line-up the lock holds or gives no verdict on | **PASS.** Main loop: `bg` and `see(segs)` are inside `if not relined and not no_verdict:`. No-voice: `see(order)` is after the `return None` on lock failure. Tests `test_ruling_130_a_clip_the_lock_holds_is_never_seen` and the no-verdict assertion confirm `visual_calls` excludes held/never-seen clips. |
| 2 | A passing line-up is unchanged in every other respect | **PASS.** When the lock passes (no error, segments present, no held), `relined` and `no_verdict` stay `False`, so `bg` is populated identically to the original, `see(segs)` runs, `vbad` is computed, and the writes loop reads `bg` at the same site. The lock_check body itself is unchanged. |
| 3 | The no-voice path | **PASS.** `lock_check(order)` runs first; on error/no-segments it returns `None` before `see(order)`. On pass, `see(order)` and `vbad` proceed as before. The test asserts the held clip `"z"` is never in `visual_calls`. |
| 4 | `lock_off` can never be a pass | **PASS.** It returns `{"ok": False, "segments": [], "error": "not asked …"}`. Both the main loop (`pre.get("error")` truthy → no-verdict path) and the no-voice path (`nv_pre.get("error")` truthy → `return None`) treat it as a stop. `ok: False` + empty `segments` cannot satisfy any pass condition. |
| 5 | The tests | **PASS.** Three new/modified tests in `test_medley.py` (held-clip-never-seen, no-verdict-clip-never-seen, no-voice-held-clip-never-seen) and three in `test_ledger_build.py` (lock_off writes nothing, lock_for numbers requests, bad value refuses). The `lock_stub` with `calls` list correctly records lock invocations and the assertions on `visual_calls` verify the ordering. The 6/6 mutation kill rate is reported. |

---

## Law compliance

- **M12 (fail closed):** `lock_off` and any lock exception produce a no-verdict (budget class, search stops), never a pass. ✓
- **LAW 20 / M2:** No gate threshold is modified; the lock_check body is unchanged. ✓
- **Smallest diff / no new renderer:** The change is a reordering plus a conditional guard; no new module, renderer, or selector. ✓
- **L-d (protected preview):** Not touched by this diff. ✓

---

## Verdict



## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_2313 (RULING 130 (2): the render's lock before any paid vision check)

Seats (Heimdall only): qwen3.8-27b (effort medium, 24,000), gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 2 of 3
(mimo EMPTY at 32,000). P1_OR_WORSE: qwen 0, gemma 1. Cycle 1 $0.0096 of Heimdall, not capped.

gemma's [P0] ("the no-voice path proceeds to see(order) on a HOLD: nv_pre.get('error') is None and the segments are
populated, so the 'if' fails"): NOT SO. Its excerpt leaves out the OUTER guard. dev51 package.py, the no-voice block:
  :3457  if nv_pre is not None and not nv_pre.get("ok"):          <- a HOLD has ok False: this branch is taken
  :3458      note["why_not"] = f"ruling 68 / 72: the render's lock: {... or 'a clip holds'}"
  :3459      if nv_pre.get("error") or not nv_pre.get("segments"):   <- only no-verdict also sets lock_stop
  :3460          out["lock_stop"] = note["why_not"]
  :3461      return None                                        <- every not-ok answer (hold or no verdict) returns
  :3462  see(order)                                             <- reached only with ok True
Its claim that the tests miss this branch is also not so: test_medley TestRuling72Lock
test_the_no_voice_line_up_asks_the_lock_too drives the no-voice line-up ([h, x, y, z], z added) with the lock holding z
and asserts z is never seen (rig.visual_calls); mutation K2 (a see(order) put back before that lock) was KILLED by it.
No change. qwen: 0. Unchanged: dev51, mutations K1-K6 6 of 6 killed after a control run; 40 suite files by exit code,
854 tests.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_2313/C2_STEP.diff (224 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 70e79be..c8e7874 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -3448,15 +3448,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
   6 |                                 **({"value": {k: value.get(k) for k in ("text", "ok", "measured", "adds", "no_restate",
   7 |                                                                         "missed", "short", "why", "words", "backend")}}
   8 |                                    if value is not None else {})}}
   9 | -        see(order)                                        # RULING 70: the added clip is seen too
  10 | -        vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order      # ruling 93 (not measured
  11 | -                if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))}   # included, law L-m)
  12 | -        if vbad:
  13 | -            note["why_not"] = ("rulings 70 / 93: " + "; ".join(f"{k}: {v}" for k, v in vbad.items()))[:400]
  14 | -            return None
  15 |          nv_pre = None
  16 | -        if lock_check is not None:                         # RULINGS 68 / 72: its own line-up
  17 | -            try:
  18 | +        if lock_check is not None:                         # RULINGS 68 / 72: its own line-up; RULING 130 (2): FIRST,
  19 | +            try:                                           # before its vision checks are paid
  20 |                  nv_pre = lock_check(order)
  21 |              except Exception as e:                        # noqa: BLE001  audit 1744 C1: no verdict, never a pass
  22 |                  nv_pre = LP.failed(e)
  23 | @@ -3465,6 +3459,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  24 |              if nv_pre.get("error") or not nv_pre.get("segments"):
  25 |                  out["lock_stop"] = note["why_not"]        # no verdict: the search stops, as for a voiced line-up
  26 |              return None
  27 | +        see(order)                                        # RULING 70: the added clip is seen too
  28 | +        vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order      # ruling 93 (not measured
  29 | +                if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))}   # included, law L-m)
  30 | +        if vbad:
  31 | +            note["why_not"] = ("rulings 70 / 93: " + "; ".join(f"{k}: {v}" for k, v in vbad.items()))[:400]
  32 | +            return None
  33 |          pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
  34 |          pk["medley"] = nv_med
  35 |          cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
  36 | @@ -3710,22 +3710,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  37 |                  if med["flagged"]:
  38 |                      k = joins(labs).index(med["flagged"][0])
  39 |                      join = (k, med["joins"][med["flagged"][0]]["why"])
  40 | -                bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
  41 | -                                       pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
  42 |                  extra, relined, w_used, written = "", False, 0, ()
  43 | -                see(segs)                                   # RULING 70: every clip seen before any write is paid
  44 | -                vbad = {m["moment_id"]: ((m.get("visual") or {}).get("why") if not (m.get("visual") or {}).get(
  45 | -                            "measured") else None) or VP.layout_block(m.get("visual"))     # ruling 93: per clip (L-m
  46 | -                        for m in segs if VP.layout_block(m.get("visual"))                  # included); the cause named
  47 | -                        and not (m is segs[0] and opens_16x9(m))}          # ruling 123 (2): the 16:9-only HOOK only
  48 | -                if vbad or segs[0].get("visual_hook_block"):
  49 | -                    vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
  50 | -                    dropped |= set(vbad)
  51 | -                    doomed |= set(vbad)
  52 | -                    rec["why"] = "ruling 70: " + "; ".join(f"{k}: {v}" for k, v in vbad.items())[:400] + ": re-lined"
  53 | -                    relined, w_used = True, writes      # no write is paid
  54 | -                pre = None
  55 | -                if not relined and lock_check is not None:  # RULINGS 68 / 72: the render's own lock, before any write
  56 | +                pre, no_verdict = None, False
  57 | +                if lock_check is not None:                  # RULINGS 68 / 72: the render's own lock, before any write;
  58 | +                    #   RULING 130 (2) (orchestrator 23:00 ET Nov 16): and FIRST, before the paid checks of the clips
  59 | +                    #   (vision, exclusion, the second pass), so a clip the render cannot cut never costs money
  60 |                      try:
  61 |                          pre = lock_check(segs)
  62 |                      except Exception as e:                # noqa: BLE001  audit 1744 C1: no verdict, never a pass
  63 | @@ -3740,13 +3729,28 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  64 |                      if pre.get("error") or not pre["segments"]:      # no verdict is never a pass (law L-m): nothing
  65 |                          rec["why"] = f"ruling 68 / 72: no lock verdict: {pre.get('error')}"[:500]   # is written, the
  66 |                          rec["budget"], out["lock_stop"] = True, rec["why"]   # search stops, the line-up stays a
  67 | -                        w_used = writes                                     # candidate (class "budget")
  68 | +                        w_used, no_verdict = writes, True                   # candidate (class "budget")
  69 |                      elif held:                             # the render would hold these clips: out, re-lined
  70 |                          dropped |= set(held)
  71 |                          doomed |= set(held)
  72 |                          rec["why"] = ("ruling 72: the render's lock holds " +
  73 |                                        "; ".join(f"{k}: {v}" for k, v in held.items()))[:500] + ": re-lined"
  74 |                          relined, w_used = True, writes
  75 | +                bg = {}                                     # ruling 130 (2): only for a line-up the lock let through
  76 | +                if not relined and not no_verdict:
  77 | +                    bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
  78 | +                                           pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
  79 | +                    see(segs)                               # RULING 70: every clip seen before any write is paid
  80 | +                    vbad = {m["moment_id"]: ((m.get("visual") or {}).get("why") if not (m.get("visual") or {}).get(
  81 | +                                "measured") else None) or VP.layout_block(m.get("visual"))     # ruling 93: per clip
  82 | +                            for m in segs if VP.layout_block(m.get("visual"))                  # (L-m included); the
  83 | +                            and not (m is segs[0] and opens_16x9(m))}      # cause named; ruling 123 (2): the 16:9-only
  84 | +                    if vbad or segs[0].get("visual_hook_block"):                               # HOOK only
  85 | +                        vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
  86 | +                        dropped |= set(vbad)
  87 | +                        doomed |= set(vbad)
  88 | +                        rec["why"] = "ruling 70: " + "; ".join(f"{k}: {v}" for k, v in vbad.items())[:400] + ": re-lined"
  89 | +                        relined, w_used = True, writes  # no write is paid
  90 |                  take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
  91 |                  alone_n, alone_by, t_refused, t_alone, last_fid, last_rw65 = 0, None, [], False, None, False
  92 |                  v_lost, v_redo, v_novoice, v_plan, val = [], False, None, None, None   # RULING 91 (medley half):
  93 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  94 | index 544684c..b3f5a13 100644
  95 | --- a/tests/package/proof_ledger.py
  96 | +++ b/tests/package/proof_ledger.py
  97 | @@ -220,6 +220,25 @@ def delivered_pins(paths):
  98 |  STOP_CEILING_USD = 1.25          # ORDER 17:50 ET Nov 16: --stop-usd at most this ('ADD 25 CENTS': a day cap of $1.25)
  99 |  
 100 |  
 101 | +def lock_off(segs):
 102 | +    """RULING 130 (2) with the 23:02 question (orchestrator, Nov 16): the lock pre-check's second recogniser is
 103 | +    ElevenLabs Scribe, OUTSIDE dollars per span (the integrator, 23:0x Nov 16). With --lock-precheck off no request is
 104 | +    written: the answer is NO VERDICT (never a pass, law L-m), so a line-up that reaches the lock stays a candidate
 105 | +    (class "budget") with nothing paid after it. -> lock_precheck.check's shape."""
 106 | +    return {"ok": False, "request_id": None, "segments": [],
 107 | +            "error": "not asked: --lock-precheck off (ruling 130 (2): the pre-check's Scribe is outside dollars; no "
 108 | +                     "request is sent until the orchestrator releases it)"}
 109 | +
 110 | +
 111 | +def lock_for(mode, out_dir, say):
 112 | +    """RULING 130 (2): the build's lock pre-check: lock_precheck.check, one numbered request per line-up asked
 113 | +    ('pp-selectid.<build>.<n>'), when mode is 'on'; else lock_off (nothing sent). -> the lock_check callable."""
 114 | +    if mode != "on":
 115 | +        return lock_off
 116 | +    n = iter(range(1, 10 ** 6))
 117 | +    return lambda segs: LP.check(segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say)
 118 | +
 119 | +
 120 |  def read_only(path):
 121 |      """ORDER 17:50 ET Nov 16 ("spend the fresh dollar on ONE line-up at a time, the likeliest first; do not screen the
 122 |      whole held pool at Grok"): the --only file, {"ids": [this build's moment ids, at least one], "why": a reason}.
 123 | @@ -383,6 +402,9 @@ def main(argv=None):
 124 |      ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
 125 |      ap.add_argument("--routing", choices=P.ROUTINGS, default=None,
 126 |                      help="RULING 85: 'today' or 'heimdall_first' (default: model_providers.json routing.mode)")
 127 | +    ap.add_argument("--lock-precheck", choices=("on", "off"), default="on",
 128 | +                    help="RULING 130 (2): 'off' sends no lock pre-check request (its Scribe is outside dollars); a "
 129 | +                         "line-up that reaches the lock then waits as a candidate")
 130 |      ap.add_argument("--only", metavar="FILE", help="ORDER 17:50 ET Nov 16: {'ids': [moment ids], 'why': text}: this "
 131 |                      "build takes only those moments of the pool, every gate as before (one line-up at a time)")
 132 |      ap.add_argument("--stop-usd", type=float, default=None, help="ORDER 17:50 ET Nov 16: this build's outside-dollar "
 133 | @@ -526,8 +548,7 @@ def main(argv=None):
 134 |                stories_path=PK.STORIES,                                             # ruling 118 (4): read only
 135 |                ledger_aliases=inputs.get("duplicates_of") or {},    # its ledger ids: a dropped duplicate -> the kept row
 136 |                visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
 137 | -              lock_check=lambda segs, n=iter(range(1, 10 ** 6)): LP.check(       # rulings 68 / 72: before any write
 138 | -                  segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say))
 139 | +              lock_check=lock_for(a.lock_precheck, out_dir, say))    # rulings 68 / 72 / 130 (2): off sends nothing
 140 |      name, at = os.path.relpath(out_dir, REPO), now.isoformat()
 141 |      if cand is not None:                                 # --from-candidate: that candidate alone (ruling 66, 13:18)
 142 |          res = PK.build(router, moments, sources, ctx, candidate=cand, **kw)
 143 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 144 | index 384c887..b13522c 100644
 145 | --- a/tests/package/test_ledger_build.py
 146 | +++ b/tests/package/test_ledger_build.py
 147 | @@ -1025,5 +1025,36 @@ class TestOrder1750OneLineUpAtATime(unittest.TestCase):
 148 |          self.assertEqual(PLG.build_router("heimdall_first", {}, os.devnull).limit_usd, PLG.PL.LY_LIMIT_USD)
 149 |  
 150 |  
 151 | +class TestRuling130LockOff(unittest.TestCase):
 152 | +    """RULING 130 (2): --lock-precheck off writes no request and answers NO VERDICT, never a pass."""
 153 | +
 154 | +    def test_lock_off_answers_no_verdict_and_writes_nothing(self):
 155 | +        sys.path.insert(0, HERE)
 156 | +        import proof_ledger as PLG
 157 | +        import lock_precheck as LP
 158 | +        before = sorted(os.listdir(LP.REQUESTS)) if os.path.isdir(LP.REQUESTS) else []
 159 | +        got = PLG.lock_off([{"moment_id": "x", "video_id": "v", "start": 0.0, "end": 9.0}])
 160 | +        self.assertEqual((got["ok"], got["segments"], got["request_id"]), (False, [], None))
 161 | +        self.assertIn("not asked", got["error"])
 162 | +        self.assertEqual(sorted(os.listdir(LP.REQUESTS)) if os.path.isdir(LP.REQUESTS) else [], before)
 163 | +
 164 | +    def test_lock_for_sends_numbered_requests_when_on_and_nothing_when_off(self):
 165 | +        sys.path.insert(0, HERE)
 166 | +        import proof_ledger as PLG
 167 | +        self.assertIs(PLG.lock_for("off", "/x/ledger_1", print), PLG.lock_off)
 168 | +        with mock.patch.object(PLG.LP, "check", side_effect=lambda segs, rid, log=None: {"rid": rid}) as chk:
 169 | +            f = PLG.lock_for("on", "/x/ledger_1", print)
 170 | +            self.assertEqual([f([1])["rid"], f([2])["rid"]], ["pp-selectid.ledger_1.1", "pp-selectid.ledger_1.2"])
 171 | +        self.assertEqual(chk.call_count, 2)
 172 | +
 173 | +    def test_a_bad_lock_precheck_value_refuses_the_run(self):
 174 | +        sys.path.insert(0, HERE)
 175 | +        import proof_ledger as PLG
 176 | +        pins = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 177 | +                                                                                 "MOMENTS_PIN_LY.json")]
 178 | +        with mock.patch("sys.stderr", new=io.StringIO()), refused_only(), self.assertRaises(SystemExit):
 179 | +            PLG.main(["--delivered", *pins, "--lock-precheck", "maybe"])
 180 | +
 181 | +
 182 |  if __name__ == "__main__":
 183 |      unittest.main()
 184 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 185 | index 5996416..935d77a 100644
 186 | --- a/tests/package/test_medley.py
 187 | +++ b/tests/package/test_medley.py
 188 | @@ -2901,6 +2901,18 @@ class TestRuling72Lock(unittest.TestCase):
 189 |          import lock_precheck as LP
 190 |          self.assertEqual(LP.pin_problems(out["package"]), [])                       # the pin stage's own check
 191 |  
 192 | +    def test_ruling_130_a_clip_the_lock_holds_is_never_seen(self):
 193 | +        """RULING 130 (2) (23:00 ET Nov 16): the render's lock is asked FIRST: a clip it holds is never sent to the paid
 194 | +        vision check; the line-up the search forms next is seen once its own lock passes."""
 195 | +        calls = []
 196 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
 197 | +                  lock_check=lock_stub({"x": ("hold", None)}, calls=calls))
 198 | +        out = rig.run()
 199 | +        self.assertEqual(calls, [["h", "x", "y"], ["h", "y", "z"]])
 200 | +        self.assertNotIn("x", rig.visual_calls)                                  # held by the lock: never seen
 201 | +        self.assertTrue({"y", "z"} <= set(rig.visual_calls), rig.visual_calls)    # the next line-up: seen after it
 202 | +        self.assertIsNotNone(out["package"])
 203 | +
 204 |      def test_no_verdict_writes_nothing_and_stops_the_search(self):
 205 |          rig = Rig(self.MS, [["h", "x", "y", "z"], ["x", "h", "y", "z"]], [(True, [], None, Rig.LINE)] * 2, [None],
 206 |                    lock_check=lock_stub(error=True))
 207 | @@ -2909,6 +2921,8 @@ class TestRuling72Lock(unittest.TestCase):
 208 |          self.assertEqual((rig.write_calls, len(rig.medley_calls)), ([], 1))       # no write, no second angle
 209 |          self.assertTrue(out["tried"][0]["budget"])
 210 |          self.assertIn("no lock verdict", out["lock_stop"])
 211 | +        self.assertNotIn("y", rig.visual_calls)        # ruling 130 (2): the line-up's clip is never seen (h and x
 212 | +        #                                                are seen earlier only as the hook stage's openers)
 213 |          c = PK.load_candidate(TestRuling66Candidate().record(), source="proof/ledger_x")
 214 |          out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c,
 215 |                    lock_check=lock_stub(error=True)).run()
 216 | @@ -2980,6 +2994,7 @@ class TestRuling72Lock(unittest.TestCase):
 217 |          self.assertEqual(calls, [["h", "x", "y"], ["h", "x", "y", "z"]])          # its own line-up, the added clip
 218 |          self.assertIsNone(out["package"])
 219 |          self.assertIn("ruling 68 / 72: the render's lock", out["tried"][0]["no_voice"]["why_not"])
 220 | +        self.assertNotIn("z", rig.visual_calls)        # RULING 130 (2): the added clip the lock holds is never seen
 221 |  
 222 |  
 223 |  class TestRuling76Window(unittest.TestCase):
 224 | 
```

---

pp-selectid: RULING 130 (2) (orchestrator 23:00 ET Nov 16), verbatim: "ORDER OF GATES: run the lock pre-check on every
line-up candidate BEFORE any paid vision check, so a clip the render cannot cut never costs money and the search moves to
the next line-up while clips are fresh. Coordinate with the integrator's lock pre-check service; land it audited."
Files: pipeline/package.py, tests/package/test_medley.py, tests/package/proof_ledger.py, tests/package/test_ledger_build.py.

WHY: tonight's one line-up that passed ruling 117 paid 2 vision checks and 1 coherence call ($0.129) and was then refused
by the render's lock (ruling 72) on What Bitcoin Did d6adeb54; its BTC Sessions clip held at the lock too.

THE CHANGE (package.build's line-up loop, and the no-voice line-up):
(a) The lock block (lock_check(segs): rulings 68 / 72; its body UNCHANGED: a held clip is dropped and the line-up
    re-lined; no verdict: rec "budget", out["lock_stop"], w_used = writes) now runs FIRST, right after the clips-alone
    verdict passes. Only when it neither holds a clip nor gives no verdict (not relined and not no_verdict) are the
    background checks started (bg: exclusion_for and truth_for, the second pass) and the clips seen (see(segs), ruling
    70's paid vision check) with the vbad re-line as before. Before, bg and see(segs) ran first and the lock only on a
    line-up the vision check let through. bg is read in ONE place, UNCHANGED (package.py:3878 in the copy: got = {...
    for mid, f in bg.items()}), inside the writes loop, which a re-lined or no-verdict line-up never enters
    (w_used = writes: the loop's first test, package.py:3760, breaks), so bg = {} there is never read.
(b) The no-voice line-up (its own order, ruling 3 / 91): lock_check(order) first; on a hold or no verdict it returns
    None before see(order); its vision check and vbad only after a passing lock.
(c) The driver: --lock-precheck on|off (default on). lock_for(mode, out_dir, say): 'on' is lock_precheck.check
    (UNCHANGED, lock_precheck.py:171) with one numbered request per line-up ('pp-selectid.<build>.<n>', as before); 'off'
    is lock_off: NO request written, the answer is NO VERDICT ({"ok": False, "segments": [], "error": "not asked ..."}),
    so the build's unchanged no-verdict path keeps the line-up as a candidate (class "budget"), nothing paid after it.
    Why 'off' exists: the pre-check's second recogniser is ElevenLabs Scribe, outside dollars per span (the integrator,
    23:0x Nov 16); the orchestrator has not yet ruled whether daytime builds may spend them (STATE line 1, 23:02).

TESTS: test_medley TestRuling72Lock: new, a clip the lock holds is never sent to the vision check and the next line-up
is seen after its lock passes; the no-voice test: its added clip the lock holds is never seen; the no-verdict test: the
line-up's clip is never seen. test_ledger_build TestRuling130LockOff: lock_off writes nothing and answers no verdict;
lock_for numbers its requests when on and is lock_off when off; a bad --lock-precheck value refuses the run. Mutations
K1-K6 after a control run: 6 of 6 killed. Suites: 40 files by exit code, 854 tests.

PLEASE CHECK: (1) that no paid check (vision, exclusion, the second pass) can run for a line-up the lock holds or gave
no verdict on; (2) that a passing line-up is unchanged in every other respect (bg is read only in the writes loop);
(3) the no-voice path; (4) lock_off can never be a pass; (5) the tests.


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
