# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1750
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 273 s finish=stop usage in 10767 / out 6114 usd_reported=0.001092 usd~0.124 (upper-bound price)

The code implements the requested `--only` and `--stop-usd` options for the build driver to restrict the moment pool and control spending.

### Analysis

1.  **`--only` Logic**: The implementation of `read_only` and `only_moments` correctly validates the JSON input (requiring non-empty `ids` and `why`), deduplicates the requested IDs while preserving order, and filters the `moments` pool before it reaches the variant generator. This ensures that only the specified moments are processed through the pipeline gates, satisfying the "one line-up at a time" requirement without skipping any quality gates.
2.  **`--stop-usd` Logic**: The `STOP_CEILING_USD` constant (1.25) is correctly enforced. The `limit` and `stop` values are properly propagated to the `Router` (to cap paid calls) and `start_refused` (to block the build from starting if the threshold is met). The `res["spend_ruling_48"]` record is updated to include these custom values for auditability.
3.  **Governing Laws**: The changes are confined to the build driver's orchestration layer. They do not modify the renderer, the selector, the canon, or any of the QA gates. Therefore, they do not violate any of the Governing Laws (Sentence Law, Selection Lock, etc.).
4.  **Test Coverage**: The new test class `TestOrder1750OneLineUpAtATime` covers the critical paths: invalid input handling, pool filtering/deduplication, and the spending stop mechanism.

### Findings

**[P1] Test-Code Mismatch on Validation Errors**
In `tests/package/proof_ledger.py`, the `main()` function raises a `ValueError` when `--only` or `--stop-usd` validation fails (lines 22, 82). However, the corresponding tests in `tests/package/test_ledger_build.py` (lines 172-175) assert that `PLG.main(...)` returns the integer `2`. 
Because `main()` raises an unhandled exception rather than returning `2`, these tests will crash with a `ValueError` instead of passing. The `main()` function needs to catch these validation errors and return `2`, or the tests must be updated to use `assertRaises`.

P1_OR_WORSE: 1

## MIMO-V2.6-FLASH-RL — CYCLE 1 OUTPUT
# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 190 s finish=stop usage in 9994 / out 17682 usd_reported=0.001969 usd~0.295 (upper-bound price)

# AUDIT: pp-selectid-20261116_1750

## Review of the three requested areas

### (1) Can `--only` add a moment or skip a gate?

**No — it cannot add a moment.** `only_moments` filters with `kept = [m for m in moments if m["moment_id"] in want]`, so only moments already in the pool survive. The `missing` list correctly reports IDs that were asked for but not found.

**No — it cannot skip a gate.** The filter is applied after `inputs` are built and before `with_variants`; every downstream stage (eligibility, step A, second screen, hook bar, visual check, story-first, writer, verdicts) sees the reduced pool and runs unchanged.

**However**, if every named ID is absent from the pool, the pool becomes empty with no refusal — see P2-1 below.

### (2) The stop's ceiling and its wiring

- **Ceiling:** `STOP_CEILING_USD = 1.25` matches the order's "$1.25" day cap. Validation `0 < X <= 1.25` correctly accepts 1.25 and rejects 1.26, 0, −1, 2. ✓
- **Wiring:** `limit` and `stop` are both derived from `a.stop_usd` (lines 102–103), passed to `build_router(limit=limit)` and `start_refused(spent0, stop)` (line 113). The record's `spend_ruling_48` names `cap`, `stop`, and `order_17_50_stop`. ✓
- **Gap:** The order says "Stop outside calls at $0.80 **unless a package is one call from its seal**." The `--stop-usd` sets a hard `limit_usd` with no exception — see P1-1 below.

### (3) The tests

The three tests cover: bad `--only` files and bad `--stop-usd` values (exit 2, nothing written), `read_only` dedup/why, `only_moments` pool-order/missing, `start_refused` with and without stop, and `build_router` limit with and without. Coverage is solid for the unit-level functions. Gaps noted as P3 below.

---

## FINDINGS

**[P1] The order's "unless a package is one call from its seal" exception is not implemented.**
The order (3) verbatim: *"Stop outside calls at $0.80 unless a package is one call from its seal."* `--stop-usd` sets `Router(limit_usd=X)` which the description itself characterises as *"no paid call reserved past it"* — a hard, unconditional stop. If spend is at $0.80 and a package is one call from its seal, the call is refused and the package cannot be sealed. The description acknowledges Ruling 122(1) is not built, but the "unless" clause is part of the ORDER itself, not Ruling 122(1), and is silently dropped. Either implement the exception (e.g., a Router flag or a pre-call check) or explicitly document the deviation and get orchestrator sign-off.

**[P2] `--only` with all IDs absent from the pool yields an empty pool with no refusal.**
`only_moments` returns `kept = []` when no pool moment matches any requested ID. The log line reports `0 of N listed moments`, but the build proceeds with an empty pool. Downstream stages may complete with no output (misleading "success") or crash unpredictably. Add a refusal: if `kept == []`, exit 2 with a clear message before any stage runs.

**[P3] No boundary test for `--stop-usd 1.25`.**
The test rejects `"1.26"` but never asserts that `"1.25"` (the ceiling) is accepted. Add `self.assertEqual(PLG.main([... "--stop-usd", "1.25"]), 0)` (or equivalent) to lock the boundary.

**[P3] No test for `--only` combined with `--from-candidate`.**
Both options can be supplied together; the interaction (filtering a previous build's moments) is untested. Add a test or explicitly reject the combination.

**[P3] `read_only` error message uses Python dict syntax, not JSON.**
The message says `needs {'ids': [moment ids], 'why': text}` but the file format is JSON (`{"ids": ...}`). Cosmetic, but misleading to an operator reading the error.

**[P3] `refused_only()` context manager is used but not defined in the diff.**
Presumably a pre-existing helper, but if it is not defined the test fails with `NameError`. Cannot verify from the diff alone.

**[P3] Cannot verify `main()` catches `FileNotFoundError` for a missing `--only` file.**
`read_only` calls `open(path)` which raises `FileNotFoundError` (an `OSError`, not `ValueError`). The test expects exit 2. If `main()` only catches `ValueError`, the test fails. Likely handled by existing code, but unverifiable from this diff.

---

P1_OR_WORSE: 1

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 64 s finish=stop usage in 10218 / out 5157 usd_reported=0.004152 usd~0.108 (upper-bound price)

I will analyze the provided diff for `tests/package/proof_ledger.py` and `tests/package/test_ledger_build.py` against the "Governing Laws" and the specific "PLEASE CHECK" instructions.

### Analysis of `--only` Implementation

1.  **Logic Verification**:
    *   `read_only` parses the JSON file. It validates that `ids` is a list of non-empty strings and `why` is a non-empty string. It deduplicates `ids` using `dict.fromkeys`.
    *   `only_moments` filters the `moments` list. It iterates through the original `moments` list and keeps those whose `moment_id` is in the `want` set. This preserves the original pool order. It correctly identifies `missing` ids.
    *   In `main`, `only_moments` is called *before* `with_variants`. This means the pool is reduced before any variant generation or downstream processing.
    *   **Check (1): Can `--only` add a moment or skip a gate?**
        *   It cannot add a moment because it only filters the existing `moments` list.
        *   It does not skip gates. The code comment states: "Every stage and gate of the build is unchanged: it simply sees a smaller pool". The filtering happens on the input data (`moments`), not on the control flow of the gates. The gates (eligibility, step A, etc.) will run on the reduced set. This complies with the intent of "spend the fresh dollar on ONE line-up at a time".

2.  **Error Handling**:
    *   If the file is missing or invalid, `read_only` raises `ValueError`.
    *   In `main`, `read_only` is called inside a block that likely handles exceptions or is wrapped in a try/except that leads to `exit 2`. The test `test_a_bad_only_file_or_stop_refuses_the_run_before_anything_is_written` verifies that `PLG.main` returns `2` for bad inputs and that no `ledger_` directories are created. This confirms fail-closed behavior (M12).

### Analysis of `--stop-usd` Implementation

1.  **Logic Verification**:
    *   `STOP_CEILING_USD` is set to `1.25`.
    *   In `main`, `a.stop_usd` is validated: `if a.stop_usd is not None and not 0 < a.stop_usd <= STOP_CEILING_USD: raise ValueError`. This enforces the range $(0, 1.25]$.
    *   `limit` and `stop` variables are determined:
        *   If `a.stop_usd` is provided, `limit = a.stop_usd` and `stop = a.stop_usd`.
        *   Otherwise, `limit = PL.LY_LIMIT_USD` and `stop = PL.LY_STOP_USD`.
    *   `build_router` is called with `limit=limit`.
    *   `start_refused` is called with `stop=stop`.
    *   **Check (2): The stop's ceiling and its wiring.**
        *   The ceiling is enforced in `main` before any state is written.
        *   The wiring passes the custom limit to the `Router` (which controls spend reservation) and the custom stop to `start_refused` (which prevents the build from starting if current spend >= stop).
        *   The `spend_ruling_48` record includes `cap: limit` and `stop: stop`, and conditionally `order_17_50_stop: a.stop_usd`. This ensures the audit trail reflects the specific constraints of this run.

2.  **Potential Issue**:
    *   The `Router` is initialized with `limit_usd=limit`. The `start_refused` check uses `stop`.
    *   If `--stop-usd` is provided, both `limit` and `stop` are set to the same value.
    *   Is it possible for `limit` and `stop` to diverge? The order says "Stop outside calls at $0.80... day cap of $1.25".
    *   The implementation sets `limit` (router cap) and `stop` (start refusal threshold) to the *same* value provided by `--stop-usd`.
    *   Let's re-read the order: "Stop outside calls at $0.80 unless a package is one call from its seal." and "ADD 25 CENTS: then start at once with the same plan and a day cap of $1.25."
    *   The `--stop-usd` argument description says: "this build's outside-dollar limit (no build starts at it; the router stops outside calls at it)".
    *   So, `--stop-usd` serves as *both* the start-refusal threshold and the router's spend limit. This matches the implementation.
    *   However, the order mentions a specific "day cap of $1.25" if "ADD 25 CENTS" is received. The `STOP_CEILING_USD` is 1.25. The user can pass `--stop-usd 1.25`.
    *   The default behavior (no `--stop-usd`) uses `PL.LY_LIMIT_USD` and `PL.LY_STOP_USD`.
    *   The logic seems sound for the specific "ORDER 17:50" context where a single parameter controls the budget for this specific run.

### Analysis of Tests

1.  **`test_a_bad_only_file_or_stop_refuses_the_run_before_anything_is_written`**:
    *   Tests invalid `--only` files (empty ids, no why, not list, blank id, missing file).
    *   Tests invalid `--stop-usd` values (0, -1, 1.26, 2).
    *   Asserts exit code 2.
    *   Asserts no `ledger_` directories are created (fail-closed).
    *   This is a strong test for M12 (Fail Closed).

2.  **`test_only_keeps_the_named_moments_in_the_pools_order_and_names_the_missing`**:
    *   Tests `read_only` deduplication and validat

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_1750 (ORDER 17:50: --only and --stop-usd in the build driver)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: qwen 0,
gemma 1, mimo 1. Cycle 1 $0.0072 of Heimdall, not capped.

gemma's P1 ("main raises ValueError instead of returning 2"): NOT SO. Both checks run INSIDE the driver's refusal block
(dev48 proof_ledger.py:406 and the --stop-usd check after it), whose handler (:436, unchanged) catches ValueError, prints
REFUSED and returns 2; the tests assert exactly that and pass (no proof dir written).
mimo's P1 ("the order's 'unless a package is one call from its seal' is not implemented: --stop-usd is a hard stop"):
TRUE THAT THE STOP IS HARD, by design: the exception is the operator's, said in tonight's plan on STATE line 1: when a
build stops on its $0.80 limit one paid call short of a seal, the SAME --only set is run again with --stop-usd 1.00; the
calls it already made are served from the step-A, hook, join, visual caches and the recorded replies, so only the
missing call is paid. No change.
mimo's P2 (an --only set none of whose ids is in the pool gives an empty pool): the build then records "0 of N listed
moments" and no package; it spends nothing. Kept (the generator writes only ids it read from the newest record).
mimo's P3s (a test of the 1.25 boundary; --only with --from-candidate): noted; tonight's runs never combine them.
qwen's [P1] headings are checks it answers itself (count 0).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_1750/C2_STEP.diff (204 lines)
```
   1 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
   2 | index ec6d16f..544684c 100644
   3 | --- a/tests/package/proof_ledger.py
   4 | +++ b/tests/package/proof_ledger.py
   5 | @@ -217,11 +217,38 @@ def delivered_pins(paths):
   6 |      return spans, newest, pins
   7 |  
   8 |  
   9 | -def build_router(routing, shadow, shadow_log):
  10 | +STOP_CEILING_USD = 1.25          # ORDER 17:50 ET Nov 16: --stop-usd at most this ('ADD 25 CENTS': a day cap of $1.25)
  11 | +
  12 | +
  13 | +def read_only(path):
  14 | +    """ORDER 17:50 ET Nov 16 ("spend the fresh dollar on ONE line-up at a time, the likeliest first; do not screen the
  15 | +    whole held pool at Grok"): the --only file, {"ids": [this build's moment ids, at least one], "why": a reason}.
  16 | +    -> {"ids", "why", "file"}, or ValueError."""
  17 | +    with open(path) as f:
  18 | +        d = json.load(f)
  19 | +    ids = d.get("ids") if isinstance(d, dict) else None
  20 | +    if not (isinstance(ids, list) and ids and all(isinstance(x, str) and x for x in ids)) or \
  21 | +            not isinstance(d.get("why"), str) or not d["why"].strip():
  22 | +        raise ValueError(f"--only {path}: needs {{'ids': [moment ids], 'why': text}}")
  23 | +    return {"ids": list(dict.fromkeys(ids)), "why": d["why"].strip(), "file": path}
  24 | +
  25 | +
  26 | +def only_moments(moments, only):
  27 | +    """The --only set: the pool's moments it names, in the pool's order (a trimmed variant is made later, beside its
  28 | +    parent, as for any moment). -> (moments, record: file, why, asked, kept, missing)."""
  29 | +    want = set(only["ids"])
  30 | +    kept = [m for m in moments if m["moment_id"] in want]
  31 | +    have = {m["moment_id"] for m in kept}
  32 | +    return kept, {"file": only["file"], "why": only["why"], "asked": len(only["ids"]), "kept": len(kept),
  33 | +                  "missing": [x for x in only["ids"] if x not in have]}
  34 | +
  35 | +
  36 | +def build_router(routing, shadow, shadow_log, limit=None):
  37 |      """The build's router: ruling 48's ledger and limit, the routing's chains (frozen legs out), the evidence file
  38 |      (item 55), ruling 86's shadow, ruling 87's shared Heimdall health and Plan B chains, ruling 99's circuit breaker,
  39 |      ruling 100's deadline table (recomputed daily from the build's own recorded answers)."""
  40 | -    return P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
  41 | +    return P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND,
  42 | +                    limit_usd=PL.LY_LIMIT_USD if limit is None else limit,        # ORDER 17:50: --stop-usd
  43 |                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
  44 |                      routing=routing, shadow=shadow, shadow_log=shadow_log,
  45 |                      health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD,      # ruling 87
  46 | @@ -297,12 +324,14 @@ def with_variants(moments, sources, ctx, inputs, say, results_dir=None, directiv
  47 |      return [m for m in moments if m["moment_id"] not in replaced] + variants
  48 |  
  49 |  
  50 | -def start_refused(spent0):
  51 | +def start_refused(spent0, stop=None):
  52 |      """RULING 48, with the orchestrator's stop of 13:02 Nov 14 (the $16 stop passed with leave; at $19 stop and tell on
  53 | -    STATE line 1 in capitals): no build starts at or over PL.LY_STOP_USD. -> the refusal line, or None."""
  54 | -    if spent0 >= PL.LY_STOP_USD:
  55 | +    STATE line 1 in capitals): no build starts at or over PL.LY_STOP_USD (or this build's --stop-usd, ORDER 17:50 ET
  56 | +    Nov 16). -> the refusal line, or None."""
  57 | +    stop = PL.LY_STOP_USD if stop is None else stop
  58 | +    if spent0 >= stop:
  59 |          return (f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
  60 | -                f"vendor reports none), at or over the ${PL.LY_STOP_USD:.2f} stop: no build starts; the orchestrator "
  61 | +                f"vendor reports none), at or over the ${stop:.2f} stop: no build starts; the orchestrator "
  62 |                  f"decides (13:02 Nov 14: SAY IT ON STATE LINE 1 IN CAPITALS)")
  63 |      return None
  64 |  
  65 | @@ -354,6 +383,10 @@ def main(argv=None):
  66 |      ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
  67 |      ap.add_argument("--routing", choices=P.ROUTINGS, default=None,
  68 |                      help="RULING 85: 'today' or 'heimdall_first' (default: model_providers.json routing.mode)")
  69 | +    ap.add_argument("--only", metavar="FILE", help="ORDER 17:50 ET Nov 16: {'ids': [moment ids], 'why': text}: this "
  70 | +                    "build takes only those moments of the pool, every gate as before (one line-up at a time)")
  71 | +    ap.add_argument("--stop-usd", type=float, default=None, help="ORDER 17:50 ET Nov 16: this build's outside-dollar "
  72 | +                    f"limit (no build starts at it; the router stops outside calls at it), in (0, {STOP_CEILING_USD}]")
  73 |      ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
  74 |                      help="RULING 66: try ONLY the line-up that passed the clips-alone verdict in this earlier build's "
  75 |                           "record (its tried[N]; default the first that passed), as it was judged")
  76 | @@ -370,6 +403,9 @@ def main(argv=None):
  77 |          if since > now:
  78 |              raise ValueError(f"since {since.isoformat()} is after now")
  79 |          cand = None
  80 | +        only = read_only(a.only) if a.only else None     # ORDER 17:50 ET Nov 16: read before anything is written
  81 | +        if a.stop_usd is not None and not 0 < a.stop_usd <= STOP_CEILING_USD:
  82 | +            raise ValueError(f"--stop-usd {a.stop_usd} is outside (0, {STOP_CEILING_USD}]")
  83 |          if a.from_candidate:                             # RULING 66: read before anything is written
  84 |              cdir, sep, idx = a.from_candidate.rpartition(":")
  85 |              cdir, idx = (cdir, idx) if sep and idx.isdigit() else (a.from_candidate, "")
  86 | @@ -428,6 +464,10 @@ def main(argv=None):
  87 |                                                 ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"),
  88 |                                                 word_pass_refused=wp_refused)
  89 |      inputs["word_pass"] = wp_rep
  90 | +    if only is not None:                                 # ORDER 17:50 ET Nov 16: one candidate set, before variants
  91 | +        moments, inputs["only"] = only_moments(moments, only)
  92 | +        say(f"  ORDER 17:50: --only: {inputs['only']['kept']} of {inputs['only']['asked']} listed moments in this pool "
  93 | +            f"({only['why']})" + (f"; not in it: {inputs['only']['missing']}" if inputs['only']['missing'] else ""))
  94 |      try:                                                 # RULING 95: when the next qualifying episode could arrive. It
  95 |          next_try = SPOT.next_attempt(rows, wp, now, refused=wp_refused)   # reads the inputs alone, so it is computed
  96 |      except Exception as e:                               # noqa: BLE001  here, recorded with them, and is a report,
  97 | @@ -450,7 +490,9 @@ def main(argv=None):
  98 |      rt = json.load(open(P.CONFIG)).get("routing") or {}
  99 |      routing = a.routing or rt.get("mode") or "today"
 100 |      shadow = build_shadow(routing, rt, SH.clean_streak)   # RULING 86 (Grok) / RULING 115 (qwen on every hook)
 101 | -    router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"))
 102 | +    limit = PL.LY_LIMIT_USD if a.stop_usd is None else a.stop_usd   # ORDER 17:50 ET Nov 16: --stop-usd
 103 | +    stop = PL.LY_STOP_USD if a.stop_usd is None else a.stop_usd
 104 | +    router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"), limit=limit)
 105 |      say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
 106 |          + (f"; SHADOW (ruling 86 / 115): {shadow}" if shadow else ""))
 107 |      live, live_why = PK.hook_live_bar()          # RULING 115: the bar in every build line, its floors and its sha
 108 | @@ -462,13 +504,13 @@ def main(argv=None):
 109 |      say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
 110 |          f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
 111 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 112 | -    refused = start_refused(spent0)
 113 | +    refused = start_refused(spent0, stop)
 114 |      if refused:
 115 |          say(refused)
 116 |          logf.close()
 117 |          return 3
 118 | -    say(f"  spend (ruling 48): ${spent0:.2f} of ${PL.LY_LIMIT_USD:.2f} vendor-reported before this build (no build "
 119 | -        f"starts at ${PL.LY_STOP_USD:.2f})")
 120 | +    say(f"  spend (ruling 48): ${spent0:.2f} of ${limit:.2f} vendor-reported before this build (no build "
 121 | +        f"starts at ${stop:.2f})")
 122 |      own, used = PL.meter(router), PL.reply_meter(router)
 123 |      t0 = time.time()
 124 |      spotlit = SPOT.load_spotlit(SPOTLIGHTS)              # RULING 90: free; its pool goes to the clip scorer with the
 125 | @@ -624,8 +666,9 @@ def main(argv=None):
 126 |          after = round(router.spent(), 4)         # (after the shadows: their spend is in it)
 127 |      except Exception as e:                       # noqa: BLE001
 128 |          after = f"unreadable: {type(e).__name__}: {str(e)[:120]}"
 129 | -    res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": PL.LY_LIMIT_USD,
 130 | -                              "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
 131 | +    res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": limit, "stop": stop,
 132 | +                              "basis": PL.LY_LIMIT_BASIS, **({"order_17_50_stop": a.stop_usd}
 133 | +                                                             if a.stop_usd is not None else {})}
 134 |      line101 = ruling_101_line((res.get("prescreen") or {}).get("parallel_101"))   # RULING 101: the extra spend
 135 |      if line101:
 136 |          say(line101)
 137 | @@ -635,7 +678,7 @@ def main(argv=None):
 138 |          f"vendor-reported" + (f" + ${vis.get('usd_estimate', 0):.4f} price-table estimate for "
 139 |                                f"{vis.get('estimated_calls', 0)} call(s) with no vendor figure"
 140 |                                if vis.get("estimated_calls") else ""))
 141 | -    say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${PL.LY_LIMIT_USD:.2f} "
 142 | +    say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${limit:.2f} "
 143 |          f"vendor-reported after this build (before it: ${spent0:.2f})")
 144 |      evs = router.breaker_events                  # RULING 99: the circuit breaker's count, for STATE line 1
 145 |      try:
 146 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 147 | index 8364c0a..384c887 100644
 148 | --- a/tests/package/test_ledger_build.py
 149 | +++ b/tests/package/test_ledger_build.py
 150 | @@ -977,5 +977,53 @@ class TestRuling85NoXai(unittest.TestCase):
 151 |          second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
 152 |          self.assertEqual((first, second), (X, DS))                                 # Grok's first, deepseek's off it
 153 |  
 154 | +class TestOrder1750OneLineUpAtATime(unittest.TestCase):
 155 | +    """ORDER 17:50 ET Nov 16: the 21:10 reset build spends the fresh dollar on ONE line-up at a time (--only: this build
 156 | +    takes only the moments a candidate set names) and stops outside calls at $0.80 (--stop-usd; at most $1.25)."""
 157 | +
 158 | +    def pins(self):
 159 | +        return [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 160 | +                                                                                 "MOMENTS_PIN_LY.json")]
 161 | +
 162 | +    def test_a_bad_only_file_or_stop_refuses_the_run_before_anything_is_written(self):
 163 | +        sys.path.insert(0, HERE)
 164 | +        import proof_ledger as PLG
 165 | +        proof = os.path.join(HERE, "proof")
 166 | +        before = sorted(n for n in os.listdir(proof) if n.startswith("ledger_"))
 167 | +        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()), refused_only():
 168 | +            for name, body in (("empty.json", {"ids": [], "why": "w"}), ("nowhy.json", {"ids": ["a"]}),
 169 | +                               ("notlist.json", {"ids": "a", "why": "w"}), ("blank.json", {"ids": [""], "why": "w"})):
 170 | +                with open(os.path.join(d, name), "w") as f:
 171 | +                    json.dump(body, f)
 172 | +                self.assertEqual(PLG.main(["--delivered", *self.pins(), "--only", os.path.join(d, name)]), 2, name)
 173 | +            self.assertEqual(PLG.main(["--delivered", *self.pins(), "--only", os.path.join(d, "missing.json")]), 2)
 174 | +            for bad in ("0", "-1", "1.26", "2"):
 175 | +                self.assertEqual(PLG.main(["--delivered", *self.pins(), "--stop-usd", bad]), 2, bad)
 176 | +        self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_")), before)
 177 | +
 178 | +    def test_only_keeps_the_named_moments_in_the_pools_order_and_names_the_missing(self):
 179 | +        sys.path.insert(0, HERE)
 180 | +        import proof_ledger as PLG
 181 | +        with tempfile.TemporaryDirectory() as d:
 182 | +            p = os.path.join(d, "only.json")
 183 | +            with open(p, "w") as f:
 184 | +                json.dump({"ids": ["c", "a", "gone", "a"], "why": "story S-1"}, f)
 185 | +            only = PLG.read_only(p)
 186 | +            self.assertEqual((only["ids"], only["why"]), (["c", "a", "gone"], "story S-1"))
 187 | +            kept, rec = PLG.only_moments([{"moment_id": x} for x in ("a", "b", "c")], only)
 188 | +            self.assertEqual([m["moment_id"] for m in kept], ["a", "c"])
 189 | +            self.assertEqual((rec["asked"], rec["kept"], rec["missing"]), (3, 2, ["gone"]))
 190 | +
 191 | +    def test_the_stop_holds_the_start_and_the_router(self):
 192 | +        sys.path.insert(0, HERE)
 193 | +        import proof_ledger as PLG
 194 | +        self.assertIn("$0.80 stop", PLG.start_refused(0.80, 0.80))
 195 | +        self.assertIsNone(PLG.start_refused(0.79, 0.80))
 196 | +        self.assertIsNone(PLG.start_refused(0.99))                          # the day's own stop when none is given
 197 | +        self.assertIsNotNone(PLG.start_refused(PLG.PL.LY_STOP_USD))
 198 | +        self.assertEqual(PLG.build_router("heimdall_first", {}, os.devnull, limit=0.8).limit_usd, 0.8)
 199 | +        self.assertEqual(PLG.build_router("heimdall_first", {}, os.devnull).limit_usd, PLG.PL.LY_LIMIT_USD)
 200 | +
 201 | +
 202 |  if __name__ == "__main__":
 203 |      unittest.main()
 204 | 
```

---

pp-selectid: ORDER 17:50 ET Nov 16 (the 21:10 ET reset build), two options of the build DRIVER (tests/package/proof_ledger.py;
pipeline/package.py is not touched): --only FILE and --stop-usd X. Files: tests/package/proof_ledger.py,
tests/package/test_ledger_build.py.

THE ORDER, verbatim (3): "SPEND TONIGHT: spend the fresh dollar on ONE line-up at a time, the likeliest first; do not
screen the whole held pool (94 moments) at Grok: that alone would eat the dollar. Stop outside calls at $0.80 unless a
package is one call from its seal." (5): "If PBX answers before 21:10 I will send 'ADD 25 CENTS': then start at once with
the same plan and a day cap of $1.25." Ruling 122 (1)'s order of work inside the build (Grok only for the chosen line-up's
moments) is NOT built; these options give its effect from outside the build: each run takes one candidate set.

THE CHANGE:
- --only FILE: {"ids": [this build's moment ids, at least one, non-empty strings], "why": non-empty text}; read in the
  driver's refusal block (a bad or missing file: exit 2, nothing written); after the ledger build's inputs and BEFORE
  the trimmed variants (with_variants), the pool keeps only the named moments, in its own order; the record's
  inputs.only says file, why, asked, kept, missing, and the log says it. Every stage and gate of the build is unchanged:
  it simply sees a smaller pool (eligibility, step A, the second screen, the hook bar, the visual check, story-first,
  the writer, every verdict).
- --stop-usd X, 0 < X <= 1.25 (else exit 2 in the refusal block): this build's router limit (Router limit_usd: no paid
  call reserved past it) and its start stop (start_refused: no build starts at or over it); the record's
  spend_ruling_48 names cap, stop and order_17_50_stop. Without it: ruling 118's $1.00 as before.

TESTS (TestOrder1750OneLineUpAtATime): a bad or missing --only file, and --stop-usd 0, -1, 1.26, 2: exit 2 and no proof dir;
read_only (dedupe, why) and only_moments (pool order, missing named); start_refused with and without the stop;
build_router's limit with and without it. Mutations O1-O6 after a control run: the two pieces of main()'s wiring
(applying --only; giving the stop to the start check) are not reachable without a full driver run: the live build's log
line and record show them (said, not hidden).

PLEASE CHECK: (1) that --only cannot add a moment or skip a gate; (2) the stop's ceiling and its wiring; (3) the tests.


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
