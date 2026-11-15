# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1019
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 33 s finish=stop usage in 7013 / out 729 usd_reported=0.018562 usd~0.053 (upper-bound price)

**CODE AUDIT REPORT — pp-selectid-20261115_1019 (proof_ledger + test_ruling_107_guard)**

**Summary of change**: The patch renames the word-pass refused list to `wp_refused` to eliminate a rebinding collision with `start_refused()` later in `main()`. It moves the `next_attempt` (Ruling 95) calculation immediately after `build_inputs()` (still before any spend-check rebinding or router decision), stores the result in `inputs.json` even on “nothing new” paths, and updates the driver test harness plus adds an explicit test that the refused count is taken from the inputs alone. The patch is explicitly labeled “Reporting only: no gate, verdict or selection changes.”

**Compliance with governing laws**:
- All core media laws (SENTENCE LAW, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, L-a through L-l, CREDITS, L-b EDGE WORDS WHOLE, L-c DISSENT IS RIGHT UNTIL DISPROVED, L-d PROTECTED PREVIEW, L-e PUNCTUATED BEFORE READ, L-f CHANNELS FIRST, L-g WRITTEN FORMS, L-h TEXT READ AS SPOKEN, L-i THE CLAIM IS THE EVENT, L-j RELEASE IS AUTHORISED ON THESE BYTES, L-k ONE CANONICAL FORM, L-l A MODEL REPLY COUNTS ONLY WHOLE, LAW 20/M2, M12 FAIL CLOSED, LAW 22) are untouched. No selection logic, gate thresholds, EDL bytes, render paths, punctuation restoration, cluster ordering, canon.py usage, or v2f reference rendering is altered.
- The change lives entirely inside test/proof ledger reporting. No new renderer, compositor or selector (M1). No DB schema changes, therefore the index requirement is irrelevant. Smallest diff principle satisfied.
- No violations found.

**Findings**:
- **[P2]** Surviving mutation (the one that forces `res["next_attempt"] = {}` late in the build record on the router path) is not killed. The new test only exercises the early “nothing-new” path; the harness short-circuits before a full router build populates the final `res` dict. This leaves a coverage gap for the exact bytes that would be written to a real proof ledger JSON when a build proceeds. The original defect was also a test-surviving scoping bug; repeating that pattern is undesirable. Must be fixed before merge.
- **[P3]** The added multi-line comment in `proof_ledger.py:12-13` and the test docstring are excessively long and contain build-specific timestamps (“10:10 ET Nov 15”, “Build 6”). While they document the history correctly, they reduce readability and will age poorly. Move detailed narrative to the commit message or a ruling appendix; keep source comments concise.
- **[P3]** `except Exception as e: # noqa: BLE001` is used twice for the reporting path. Acceptable here because the contract is “a report, never the build”, but a narrower exception list would be preferable for future maintainability.

No P0 or P1 defects. The name-collision fix is correct, `next_try` is computed from the intended inputs, no downstream variable is mutated before the build record is populated, the test harness extension is sound, and all new code passes the existing 685-test suite plus the added ruling-95 case. The single P2 item blocks clean merge under the quality gate.

P1_OR_WORSE: 1

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 39 s finish=stop usage in 7470 / out 3018 usd_reported=0.002499 usd~0.068 (upper-bound price)

**Audit Report: pp-selectid-20261115_1019 (C1_STEP.diff)**

**Context:** This diff addresses a variable name collision in `tests/package/proof_ledger.py` where `refused` (word pass IDs) was being overwritten by `start_refused()` (spend check result) before being passed to `spotlight.next_attempt`. The fix renames the variable to `wp_refused` and moves the `next_attempt` calculation earlier in the execution flow to ensure it uses the correct data.

### Findings

**1. [P3] Comment Clarity / Historical Context**
In `proof_ledger.py` (lines 11-13 of the diff), the comment explaining the rename is quite verbose and references specific build times ("build 6, 10:10 ET Nov 15"). While accurate for the audit trail, this level of detail in a code comment can become noise. However, given the "Governing Laws" emphasis on strict provenance and the fact that this is a test/proof ledger package, this is acceptable. No action required, but noted as a style nit.

**2. [P3] Exception Handling Scope**
The `try/except` block around `SPOT.next_attempt` (lines 20-23) catches `Exception`. The comment states "a report, never the build". This aligns with **M12 FAIL CLOSED** (missing data/exception rejects, never produces a pass) in the context of *reporting* metadata. Since `next_attempt` is purely informational (written to `inputs.json` and `res`), failing it should not block the build. The code correctly isolates this failure. No defect found.

**3. [P2] Potential Logic Shift in `next_attempt` Timing**
The diff moves the calculation of `next_try` from *after* the router/guard logic (line 38-41 in old code) to *before* `with_variants` and the `inputs.json` write (line 20-23 in new code).
*   **Old:** `next_attempt` was calculated late, potentially after some state changes in `rows` or `wp` if those objects were mutated in place by intermediate steps.
*   **New:** `next_attempt` is calculated immediately after `build_inputs`.
*   **Analysis:** The prompt asks to check if "nothing between the new computation and the build record could change what next_attempt reads".
    *   `rows`: Passed to `build_inputs`. If `build_inputs` mutates `rows` in place, the `next_attempt` call (which happens *after* `build_inputs` in the new code? No, wait. Let's look at the order).
    *   **Order in New Code:**
        1. `rows, rep = LB.rows(...)`
        2. `wp, wp_rep = LB.word_pass_index(...)`
        3. `wp_refused = ...`
        4. `inputs = LB.build_inputs(rows, ..., word_pass_refused=wp_refused)`
        5. `next_try = SPOT.next_attempt(rows, wp, now, refused=wp_refused)`
        6. `moments = with_variants(...)`
    *   If `LB.build_inputs` mutates `rows` or `wp` in place, `SPOT.next_attempt` will see the mutated state. In the old code, `next_attempt` was called much later (line 39), so it would *also* see any mutations from `build_inputs` and `with_variants`.
    *   **Crucial Check:** Does `SPOT.next_attempt` depend on `moments` or `inputs`? The signature is `SPOT.next_attempt(rows, wp, now, refused=wp_refused)`. It does *not* take `inputs` or `moments`. It takes `rows` and `wp`.
    *   If `build_inputs` does not mutate `rows` or `wp`, the timing change is safe. If it *does* mutate them, the new code captures the state *after* `build_inputs` but *before* `with_variants`. The old code captured the state *after* `with_variants`.
    *   **Risk:** If `with_variants` mutates `rows` or `wp`, the new `next_attempt` value will differ from the old one. However, `next_attempt` is a "report" of when the *next* qualifying episode could arrive. It likely depends on the *input* rows, not the *processed* moments. Therefore, calculating it based on the raw `rows` (post-`build_inputs` if `build_inputs` cleans them, or pre-`build_inputs` if it doesn't) is likely more correct than calculating it after `with_variants` has potentially filtered or transformed the data.
    *   **Verdict:** This is likely an improvement in correctness (using input state for input-based reports), but it is a behavioral change. The test `test_ruling_95_counts_the_refused_from_the_inputs_alone` verifies the count logic. It does not explicitly verify that `rows`/`wp` are not mutated by `build_inputs` in a way that breaks `next_attempt`. Given `next_attempt` is a "report", this is low risk, but worth noting.

**4. [P1] Missing Verification of `rows`/`wp` Immutability**
The prompt asks: "(1) that nothing between the new computation and the build record could change what next_attempt reads".
The new computation is at line 21. The build record (`res`) is updated at line 42.
Between line 21 and 42, the code executes:
*   `moments = with_variants(...)` (Line 24)
*   `json.dump(...)` (Line 25-30)
*   `pool = ...` (Line 31)
*   `fp, fp_parts = fingerprint(...)` (Line 32)
*   `same = ...` (Line 33)
*   ... (Router logic, lines 34-41)

If `with_variants`, `fingerpr

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_1019 (ruling 95's refused count in the driver: a name collision)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0, "[P1] None. The fix correctly resolves the name collision"). glm's ruling-99
breaker was open until 11:11 ET, so the next family reviewed: deepseek-v4.1-flash gave NO ANSWER (finish=length,
16,000 tokens of reasoning, empty content). Grok was therefore asked (ruling 107 (2)): grok-4.20-0309-reasoning. Its
text says "No P0 or P1 defects", but its closing line counts 1, because it calls its one [P2] "must be fixed before
merge". Cycle 1: $0.0245 vendor-reported.

AGREED BY ALL: the collision fix is correct. next_try is computed from the intended inputs, and nothing between it and
the build record changes what it read. No other name collides (`wp_refused` and `next_try` are each bound once in
main()). Moving ruling 95 before the guard changes no build outcome, and "a report, never the build" is kept.

1. Grok [P2] / qwen [P2] "the surviving mutation: res["next_attempt"] = {} on the router path is untested". ACCEPTED AS
   A STATED GAP, WITH A RUNTIME CHECK INSTEAD.
   - Why no test: the line is a plain copy of next_try, a value computed once (bound once, tested in inputs.json by
     test_ruling_95_counts_the_refused_from_the_inputs_alone, which kills D1 and D2). Reaching the line needs the driver
     past build_router to package.json: a fake router with breaker_events, spent, chains, backends, config,
     effective_deadline and first_bounds, plus the shadow, circuit-breaker, registry and fingerprint paths. That is
     dozens of lines of brittle fakes for one assignment.
   - The runtime check: the first real build after this lands is checked. Its package.json "next_attempt" must equal its
     inputs.json "next_attempt", with the refused counted, and its ruling-95 log line must print the refused. The result
     goes on that build's STATE line.
   - Grok's point stands as a lesson. The defect being fixed was itself a surviving "untested wiring" mutation, so this
     record names the gap and the check rather than calling it harmless.
2. Grok [P3] / qwen [P3] "the comments carry build-specific history". DONE: the source comment is now one line ("a name
   of its own: main() later binds `refused` to start_refused()'s answer"), and the test docstring states the behaviour.
   The history lives in the commit message and in this audit.
3. Grok [P3] / qwen [P3] "except Exception on the report path". NO CHANGE: it is the same guard the base had at :510
   ("a report, never the build", noqa BLE001), moved with the call. A report must never end a build.
4. qwen [P2] "the timing shift". Settled in qwen's own text: next_attempt reads rows, the word-pass index, now and the
   refused ids, and none of them changes after build_inputs.

THE CODE NOW: the same fix, with the comment and the docstring trimmed. Suites: 685 pass. Mutations: 4 of 5 killed after
a control run; D5 (the record's copy, past the router) surv

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1019/C2_STEP.diff (89 lines)
```
   1 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
   2 | index 63860a3..2f200ba 100644
   3 | --- a/tests/package/proof_ledger.py
   4 | +++ b/tests/package/proof_ledger.py
   5 | @@ -403,17 +403,22 @@ def main(argv=None):
   6 |      rows, rep = LB.rows(since, now, horizon_h=a.hours)
   7 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
   8 |      wp, wp_rep = LB.word_pass_index(a.word_pass)
   9 | -    refused = wp_rep.get("refused") or []                # final: the worker never re-works them (the inputs keep ids)
  10 | -    say(f"  word pass: {json.dumps(dict(wp_rep, refused=len(refused)))}")
  11 | +    wp_refused = wp_rep.get("refused") or []             # final: the worker never re-works them (the inputs keep ids);
  12 | +    #   a name of its own: main() later binds `refused` to start_refused()'s answer
  13 | +    say(f"  word pass: {json.dumps(dict(wp_rep, refused=len(wp_refused)))}")
  14 |      moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp,
  15 |                                                 ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"),
  16 | -                                               word_pass_refused=refused)
  17 | +                                               word_pass_refused=wp_refused)
  18 |      inputs["word_pass"] = wp_rep
  19 | +    try:                                                 # RULING 95: when the next qualifying episode could arrive. It
  20 | +        next_try = SPOT.next_attempt(rows, wp, now, refused=wp_refused)   # reads the inputs alone, so it is computed
  21 | +    except Exception as e:                               # noqa: BLE001  here, recorded with them, and is a report,
  22 | +        next_try = {"error": f"{type(e).__name__}: {str(e)[:200]}"}       # never the build
  23 |      moments = with_variants(moments, sources, ctx, inputs, say)   # RULING 104: beside their parents, every gate again
  24 |      with open(os.path.join(out_dir, "inputs.json"), "w") as f:
  25 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
  26 | -                   "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
  27 | -                  f, indent=1, default=str)
  28 | +                   "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments,
  29 | +                   "next_attempt": next_try}, f, indent=1, default=str)
  30 |      pool = json.loads(json.dumps(moments, default=str))   # RULING 107 (1): the pool as it came in, before any stage
  31 |      fp, fp_parts = fingerprint(pool, delivered, pins, since, now, reg, a.routing)
  32 |      same = None if cand is not None else nothing_new(os.path.join(HERE, "proof"), out_dir, fp)
  33 | @@ -506,10 +511,7 @@ def main(argv=None):
  34 |                      spotlit=spotlit)
  35 |      res["spotlight"] = {k: sp.get(k) for k in ("package", "why_none", "finalists", "near", "moments", "pool",
  36 |                                                  "scorer_waited_s", "lock_stop", "scorer")}
  37 | -    try:                                                 # RULING 95: when the next qualifying episode could arrive
  38 | -        res["next_attempt"] = SPOT.next_attempt(rows, wp, now, refused=refused)
  39 | -    except Exception as e:                               # noqa: BLE001  a report, never the build
  40 | -        res["next_attempt"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
  41 | +    res["next_attempt"] = next_try                       # RULING 95, computed beside the inputs above
  42 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
  43 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
  44 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
  45 | diff --git a/tests/package/test_ruling_107_guard.py b/tests/package/test_ruling_107_guard.py
  46 | index c1b3e31..8411c19 100644
  47 | --- a/tests/package/test_ruling_107_guard.py
  48 | +++ b/tests/package/test_ruling_107_guard.py
  49 | @@ -161,8 +161,9 @@ class TestTheDriverAsksNoModel(Paths):
  50 |      PIN_PATHS = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
  51 |                                                                                    "MOMENTS_PIN_LY.json")]
  52 |  
  53 | -    def run_driver(self, left, wp_rep=None, seen=None):
  54 | -        """wp_rep: the word pass's report the stubbed index gives; seen: filled with build_inputs' keyword arguments."""
  55 | +    def run_driver(self, left, wp_rep=None, seen=None, rows=None):
  56 | +        """wp_rep: the word pass's report the stubbed index gives; seen: filled with build_inputs' keyword arguments;
  57 | +        rows: the ledger rows the stubbed adapter gives (default none)."""
  58 |          proof = os.path.join(self.tmp.name, "drv", "proof")
  59 |          os.makedirs(proof)
  60 |          delivered, last, pins = PLG.delivered_pins(self.PIN_PATHS)
  61 | @@ -185,7 +186,7 @@ class TestTheDriverAsksNoModel(Paths):
  62 |          stubs = [mock.patch.object(PLG, "HERE", os.path.join(self.tmp.name, "drv")),
  63 |                   mock.patch.object(PLG, "REGISTRY", os.path.join(proof, "CANDIDATES.json")),
  64 |                   mock.patch.object(PLG.PS, "ledger_entries", lambda *a, **k: []),
  65 | -                 mock.patch.object(PLG.LB, "rows", lambda *a, **k: ([], {"excluded": {}})),
  66 | +                 mock.patch.object(PLG.LB, "rows", lambda *a, **k: (list(rows or []), {"excluded": {}})),
  67 |                   mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, dict(wp_rep or {"rows": 0}))),
  68 |                   mock.patch.object(PLG.LB, "build_inputs", inputs),
  69 |                   mock.patch.object(PLG, "with_variants", lambda moments, *a, **k: moments),
  70 | @@ -223,6 +224,18 @@ class TestTheDriverAsksNoModel(Paths):
  71 |          self.assertEqual(json.load(open(os.path.join(runs[0], "inputs.json")))["inputs"]["word_pass"]["refused"],
  72 |                           ["Xa1", "Yb2"])
  73 |  
  74 | +    def test_ruling_95_counts_the_refused_from_the_inputs_alone(self):
  75 | +        """Ruling 95 reads the inputs beside build_inputs (before main() rebinds any name for the spend check), and
  76 | +        inputs.json records it, even for a build that stops with nothing new."""
  77 | +        at = datetime.now(timezone.utc).isoformat()
  78 | +        rows = [{"video_id": "v1", "channel_name": "Talk", "published_at": at, "moment_id": m,
  79 | +                 "episode": {"turns_per_min": 2.0}, "mined": {"pass": "moment", "prompt_version": "mine/2"}}
  80 | +                for m in ("Xa1", "Yb2", "Zc3")]
  81 | +        rc, runs = self.run_driver(left=0, wp_rep={"rows": 2, "ready": 0, "refused": ["Xa1", "Yb2"]}, rows=rows)
  82 | +        na = json.load(open(os.path.join(runs[0], "inputs.json")))["next_attempt"]["conversation"]
  83 | +        self.assertEqual((rc, na["rows"], na["word_pass_ready"], na["word_pass_refused"], na["word_pass_waiting"]),
  84 | +                         (0, 3, 0, 2, 1))
  85 | +
  86 |      def test_work_left_undone_goes_on_to_the_router(self):
  87 |          rc, runs = self.run_driver(left=1)
  88 |          self.assertEqual(rc, "router")
  89 | 
```

---

pp-selectid: RULING 95'S REFUSED COUNT IN THE BUILD DRIVER, A NAME COLLISION FIXED. Reporting only: no gate, verdict
or selection changes.

THE DEFECT (mine; it landed in e19ec46c under audit 20261115_0951, where the mutation that dropped this keyword
SURVIVED, untested). In tests/package/proof_ledger.py main(), the word pass's refused ids were bound to `refused` at
:406 and passed to build_inputs at :410 (right) and to spotlight.next_attempt at :510 (wrong). Between the two, at :438
(UNCHANGED, base 1ffe2302), main() rebinds the same name: `refused = start_refused(spent0)`, the spend check's answer,
None when a build may start. So ruling 95 got refused=None. Builds 6 and 7 (10:10 and 10:16 ET Nov 15) printed
"19 waiting / 0 refused" and "17 waiting / 0 refused" for Bitcoin Magazine, whose rows were 12 and then 17 refused.
build_inputs' counts were right (16 and 21 refused).

THE FIX (tests/package/proof_ledger.py):
1. The list is named `wp_refused`, a name nothing else in main() binds. A comment says why.
2. Ruling 95's record (spotlight.next_attempt, UNCHANGED) is computed right after build_inputs, from the inputs alone
   (rows, the word-pass index, now, wp_refused). This is BEFORE the spend check and before any router. The record is
   written into inputs.json as "next_attempt", so even a build that stops with nothing new (ruling 107 (1)) records it.
   The build record's res["next_attempt"] is that same value; its try/except (a report, never the build) is kept.
   The value is the same as before, because next_attempt reads nothing the build later changes.

TESTS: test_ruling_107_guard's run_driver gains an optional `rows` (the stubbed adapter's rows). A new test,
test_ruling_95_counts_the_refused_from_the_inputs_alone, runs the real driver to its nothing-new stop with 3 rows, 2 of
them refused, and reads inputs.json: 3 rows, 0 ready, 2 refused, 1 waiting. Mutations: 4 of 5 killed after a control
run (the unmutated copy passes all 51 tests in the two files):
- ruling 95 without the refused: killed;
- not recorded in inputs.json: killed;
- build_inputs without the refused: killed;
- the log giving ids: killed.
The 1 that survives: res["next_attempt"] set to {} in the build record, past the router, which no test reaches (the
harness stops at nothing-new or at build_router). Suites: 685 pass.

PLEASE CHECK: (1) that nothing between the new computation and the build record could change what next_attempt reads
(rows, wp, now, wp_refused); (2) that no other name in main() collides (`wp_refused`, `next_try`); (3) that moving
ruling 95 before the guard changes no build outcome and keeps the "a report, never the build" behaviour; (4) the test
and its harness change; (5) whether the surviving mutation matters.


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
