# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2114
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 76 s finish=stop usage in 5901 / out 2002 usd_reported=0.000431 usd~0.048 (upper-bound price)

# Audit: C1_STEP — RULING 108 ledger/stop/limit change

**Scope reviewed:** the 60-line diff only (proof_ly.py, test_ruling_102.py), plus the stated unchanged guards. I am one of three independent reviewers; findings below.

---

## Answers to the three questions

**Q1 — Can any build path still write the closed SPEND_LY.json?**

Within the diff, no. `SPEND` is rebound to `SPEND_B3.json` at module level, and the unchanged guard `proof_ledger.build_router(..., spend_path=PL.SPEND, ...)` means every router built through that call writes the new ledger. The test additionally pins `PLG.PL.SPEND.endswith("SPEND_B3.json")`, so a regression to the old path fails the suite. Two residual risks worth noting (not defects in this diff):

- [P2] Any *other* module that references `SPEND_LY.json` by its own literal (not via `PL.SPEND`) is invisible to this diff and unpinned by the test. The test only pins the module attribute, not the filesystem. A cheap strengthening: after a run, assert `SPEND_LY.json`'s mtime is unchanged, or assert the new file exists after one router construction. As written, if some second call site hardcodes the old path, the test still passes.
- [P3] The comment "SPEND_LY.json is the closed $20 order's" is the only documentation of the closed ledger; nothing in code marks it read-only. If a future ruling reopens it, nothing fails. Acceptable for a 24 h batch.

**Q2 — Are stop and limit consistent with "never start a build that would end over the cap"?**

Yes, with one caveat about the *invariant* vs the *mechanism*.

The invariant: builds cost $0.15–$0.50, stop at $4.00, so a started build ends at ≤ $4.50 = the limit. The reservation mechanism ("each paid call RESERVES its upper bound while in flight") is what actually guarantees the limit is never passed — the stop is only an efficiency/STATE-line rule, not the cap. That's consistent, and the diff's comments state it correctly.

- [P2] The reasoning "a build runs $0.15–0.50, so none ends over $4.50" is a comment, not an enforced invariant. If a single build's upper bound ever exceeds $0.50 (price-table change, model price hike), the stop-at-$4.00 + limit-$4.50 pairing silently loses its 1×-build headroom. The test pins the *numbers* (4.00/4.50) but not the *relationship* `LY_LIMIT_USD - LY_STOP_USD >= max_build_upper_bound`. One extra assertion (`self.assertGreaterEqual(PLG.PL.LY_LIMIT_USD - PLG.PL.LY_STOP_USD, 0.50)`) would pin the headroom, not just the constants. As written, a future ruling that moves the stop to $4.40 keeps the test green while breaking the documented reasoning.
- [P3] `LY_STOP_USD = 4.00` with the refusal condition `spent0 >= LY_STOP_USD` means at exactly $4.00 no build starts — the test checks `start_refused(4.0)` is truthy and `start_refused(3.99)` is None, which correctly pins the inclusive-at-the-stop boundary. Good. Note the comment says "No build starts at or over $4.00" — consistent. No finding.
- [P3] The limit basis stays `"reported"` (unchanged), so the $4.50 cap is enforced on vendor-reported dollars only, with the price-table estimate counted only where a vendor reports none. That matches ruling 48's semantics carried forward; the ruling-108 text says "VENDOR-REPORTED" explicitly. Consistent; no finding.

**Q3 — Does the test pin the behaviour?**

Mostly yes, with one gap.

- [P2] The test pins the constants as a *tuple equality* — `assertEqual((STOP, LIMIT), (4.00, 4.50))` — which is fine, but it does not pin `LY_LIMIT_BASIS == "reported"`. The limit's meaning depends entirely on the basis (ruling 48: the estimate counts only where a vendor reports none). If someone flips the basis to `"estimate"` or `"all_in"`, the $4.50 cap changes meaning while the test stays green. One line: `self.assertEqual(PLG.PL.LY_LIMIT_BASIS, "reported")`. Given the ruling text says "VENDOR-REPORTED" explicitly, this is a should-fix, not a nit.
- [P2] The renamed test (`test_no_build_starts_at_the_stop_and_one_starts_below`) now asserts four things but its docstring cites the 13:02 Nov 14 ruling and ruling 108; the *old* test's docstring-cited ruling (the $16→$19 history) is dropped. That's fine — history lives in the diff comments — but the test no longer checks that STATE line 1 actually *says* the capitals message; it only checks the returned `why` string contains it. If `start_refused`'s contract includes writing STATE line 1, that side effect is unpinned. If the STATE-line writing happens in the caller (orchestrator), this is a [P3]; flagging as [P2] because the docstring claims "STATE line 1 says so in capitals" and the test verifies only the message *content*, not the *saying*.
- [P3] `assertTrue(PLG.PL.SPEND.endswith("SPEND_B3"))` — actually the test uses `.endswith("SPEND_B3.json")`, which would also match a hypothetical `SPEND_B3.json.bak` or `.../SPEND_B3.json2`; trivial. Also `assertIsNone(PLG

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 47 s finish=stop usage in 6434 / out 3936 usd_reported=0.003106 usd~0.078 (upper-bound price)

I will review the provided diff against the governing laws and the specific questions asked.

### Analysis

**1. Context and Scope**
The diff modifies `tests/package/proof_ly.py` and `tests/package/test_ruling_102.py`.
- `proof_ly.py` defines constants for a "Proof of Work" or audit ledger system (likely related to the "LY" or "Local Judge" mentioned in the laws, specifically RULING 87/102/108).
- The change updates the budget limits from a previous "$20 order" to a new "Batch 3" with an $8.00 total cap, specifically allocating $4.50 for builds/sealing and setting a stop threshold at $4.00.
- The ledger file path changes from `SPEND_LY.json` to `SPEND_B3.json`.

**2. Review of Specific Questions**

*   **(1) Can any build path still write the closed SPEND_LY.json?**
    *   The diff shows `SPEND = os.path.join(OUT, "SPEND_B3.json")`.
    *   The comment states: "The $20 order's SPEND_LY.json is CLOSED... never written again."
    *   The test `test_no_build_starts_at_the_stop_and_one_starts_below` asserts `self.assertTrue(PLG.PL.SPEND.endswith("SPEND_B3.json"))`.
    *   *Assumption:* `PLG.PL` refers to the `proof_ly` module imported in the test. If `proof_ledger` (or the router) uses `PL.SPEND` as the target path for writing, then no, it will not write to the old file. The diff does not show the *writer* code, but it shows the *configuration* of the writer. The configuration is updated. The risk is if there is hardcoded logic elsewhere, but based on the provided code, the source of truth for the path is updated.
    *   *Verdict:* No, based on the provided diff, the path is updated.

*   **(2) Are the stop and the limit consistent with "never start a build that would end over the cap"?**
    *   **Cap (Limit):** `LY_LIMIT_USD = 4.50`.
    *   **Stop:** `LY_STOP_USD = 4.00`.
    *   **Build Cost Range:** The comment states: "A build runs $0.15-0.50".
    *   **Logic:**
        *   If current spend is $3.99, `start_refused(3.99)` returns `None` (allows start).
        *   Max cost of a build is $0.50.
        *   $3.99 + $0.50 = $4.49.
        *   $4.49 < $4.50 (Limit).
        *   If current spend is $4.00, `start_refused(4.00)` returns a refusal string (stops start).
        *   Why stop at $4.00? Because if you start at $4.00, and the build costs $0.50, you end at $4.50. This is *at* the limit. The law/comment says "none ends over $4.50". Ending *at* $4.50 is allowed.
        *   However, the stop is at $4.00. This means you cannot start a build if you have already spent $4.00.
        *   Let's check the boundary:
            *   Spend = $3.99. Start allowed. Max end = $4.49. OK.
            *   Spend = $4.00. Start refused.
            *   Is there a gap? What if Spend = $3.995? The code uses floats. `3.995 >= 4.00` is False. Start allowed. Max end = $4.495. OK.
            *   What if Spend = $4.00? `4.00 >= 4.00` is True. Start refused.
            *   The comment says: "No build starts at or over $4.00... none ends over $4.50".
            *   If a build starts at $3.99 and costs $0.50, it ends at $4.49.
            *   If a build starts at $3.99 and costs $0.51 (hypothetically, though comment says max 0.50), it ends at $4.50.
            *   The constraint is "never start a build that would end over the cap".
            *   Cap = 4.50.
            *   Max Build Cost = 0.50.
            *   Therefore, Max Start Spend = Cap - Max Build Cost = 4.50 - 0.50 = 4.00.
            *   So, you can start if Spend < 4.00? Or Spend <= 4.00?
            *   If Spend = 4.00, and Build = 0.50, End = 4.50. This is *not* over the cap.
            *   The code refuses if `spent0 >= PL.LY_STOP_USD` (4.00).
            *   So it refuses at 4.00.
            *   This is **conservative**. It prevents starting at 4.00, even though starting at 4.00 would result in exactly 4.50 (which is allowed by "not over").
            *   Is this a defect? The comment says "No build starts at or over $4.00". This matches the code.
            *   Does it violate "never start a build that would end over the cap"? No, it's stricter. It prevents builds that would end *at* the cap if the cost is exactly max.
            *   Wait, if I start at 3.99, I end at 4.49.
            *   If I start at 4.00, I end at 4.50.
            *   The code blocks 4.00.
            *   This is safe. It might block a valid build (one that ends exactly at the limit), but it does not allow an invalid one.
            *   *Verdict:* Consistent and safe (fail-closed).

*   **(3) Does the test pin the behaviour?**
    *   The test `test_no_build_starts_at_the_stop_and_one_starts_below` checks:
        1.  `PLG.PL.LY_STOP_USD` is 4.00.
        2.  `PLG.PL.LY_LIMIT_USD` is 4.50.
        3.  `PLG.PL.SPEND` ends with `SPEND_B3.json`.
        4.  `PLG.start_refused(3.99)` is `None` (allowed).
        5.  `PLG.start_refused(4.0)` contains the r

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus: pp-selectid audit 20261114_2114 (RULING 108: batch 3's own build ledger, cap and stop)

Reviewers under ruling 107 (2): qwen3.8-27b and glm-5.3-flash. Both report P1_OR_WORSE 0, so Grok was not asked.
Cost: $0.0035 vendor-reported. The change is 30 lines, so the small cap applies: one reviewer set, two cycles, $0.30.

IMPLEMENTED (glm P2):
- the test pins LY_LIMIT_BASIS == "reported";
- the test pins one build's headroom: LY_LIMIT_USD - LY_STOP_USD >= $0.50.

NOTED, NO CHANGE:
- qwen P2 / glm P2 (the headroom is an assumption). The stop is the soft pre-check. The hard guard is the Router's
  limit: every paid call RESERVES its upper bound before it runs, and none passes $4.50 (providers.Router._reserve).
  So a build that would cost more than the headroom is stopped mid-build, never paid past the cap.
- glm P2 (a second hard-coded SPEND_LY.json): a grep finds one other use, tests/package/replay85.py. That is the
  ruling-85 replay tool, not run in batch 3; no build path uses it. proof_ledger.build_router passes PL.SPEND.
- glm P2/P3 (STATE line 1 "saying"): the builder writes STATE from the build's printed refusal, so it is not this
  module's side effect.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_2114/C2_STEP.diff (62 lines)
```
   1 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
   2 | index 154aa11..5dcf21f 100644
   3 | --- a/tests/package/proof_ly.py
   4 | +++ b/tests/package/proof_ly.py
   5 | @@ -17,7 +17,8 @@ is out too. What is left:
   6 |  - the second recogniser is ElevenLabs scribe_v1.
   7 |  CPU and network only. The inputs are read-only: the saved runs and the main store's transcripts.
   8 |  
   9 | -SPEND: a ledger of this order's own (tests/package/proof/SPEND_LY.json) holds the price-table estimate beside the
  10 | +SPEND: a ledger of this order's own (tests/package/proof/SPEND_B3.json since ruling 108; SPEND_LY.json is the closed
  11 | +$20 order's) holds the price-table estimate beside the
  12 |  vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). RULING 48 (orchestrator 07:02 Nov 13):
  13 |  its guard is LY_LIMIT_USD on VENDOR-REPORTED dollars, the estimate counted only for a call whose vendor reports none
  14 |  (Router limit_basis="reported"); at LY_STOP_USD no new build starts (proof_ledger) and the orchestrator is told.
  15 | @@ -46,13 +47,13 @@ import speakers as SP  # noqa: E402
  16 |  
  17 |  REPLIES = os.path.join(HERE, "fixtures", "replies")
  18 |  OUT = os.path.join(HERE, "proof")
  19 | -SPEND = os.path.join(OUT, "SPEND_LY.json")
  20 | -LY_LIMIT_USD = 20.0                # RULING 83 (b) (20:33 Nov 13): $20.00 VENDOR-REPORTED for this order (ruling 48's
  21 | -LY_LIMIT_BASIS = "reported"        # $12 before; the old $40 cap by the price-table estimate read ~12x high);
  22 | -LY_STOP_USD = 19.0                 # the estimate counts only where a vendor reports none. The orchestrator 13:02 Nov
  23 | -                                   # 14: the $16 stop passed with leave; at $19 no build starts and STATE line 1 says
  24 | -                                   # so in capitals; no build may end over $20 (the cap: each paid call still RESERVES
  25 | -                                   # its price-table upper bound while in flight, and none passes the limit).
  26 | +SPEND = os.path.join(OUT, "SPEND_B3.json")   # RULING 108 (orchestrator 21:20 ET Nov 14): BATCH 3 (to 21:10 ET Nov 15)
  27 | +#   keeps its own ledger. The $20 order's SPEND_LY.json is CLOSED at $11.47 (restated on ruling 107 Q1's basis, e7f68e11).
  28 | +LY_LIMIT_USD = 4.50                # RULING 108: builds + sealing's share of batch 3's $8.00 ALL-IN cap (audits $2.50,
  29 | +LY_LIMIT_BASIS = "reported"        # mining and checks $1.00), VENDOR-REPORTED; an abandoned call at the model's own
  30 | +LY_STOP_USD = 4.00                 # rate (ruling 107 Q1). No build starts at or over $4.00 (a build runs $0.15-0.50, so
  31 | +                                   # none ends over $4.50: each paid call still RESERVES its upper bound while in
  32 | +                                   # flight, and none passes the limit); STATE line 1 says so in capitals.
  33 |  TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
  34 |  DEADLINE_LOG = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_HEIMDALL_DEADLINES.jsonl")   # item 55
  35 |  RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
  36 | diff --git a/tests/package/test_ruling_102.py b/tests/package/test_ruling_102.py
  37 | index d88e5be..eccb74d 100644
  38 | --- a/tests/package/test_ruling_102.py
  39 | +++ b/tests/package/test_ruling_102.py
  40 | @@ -304,11 +304,16 @@ class TestOnThePinAndOnState(unittest.TestCase):
  41 |                        line)
  42 |          self.assertIn("THE LOCAL JUDGE (RULING 87'S LAST RESORT) GAVE 2 STEP-A VERDICT(S): ['c', 'e']", line)
  43 |  
  44 | -    def test_no_build_starts_at_19_dollars_and_one_starts_below(self):
  45 | -        """The orchestrator 13:02 Nov 14: the $16 stop passed with leave; at $19 stop and say so in capitals."""
  46 | -        self.assertIsNone(PLG.start_refused(18.99))
  47 | -        why = PLG.start_refused(19.0)
  48 | -        self.assertIn("at or over the $19.00 stop: no build starts", why)
  49 | +    def test_no_build_starts_at_the_stop_and_one_starts_below(self):
  50 | +        """The orchestrator 13:02 Nov 14: at the stop no build starts, and STATE line 1 says so in capitals. RULING 108
  51 | +        (21:20 Nov 14): batch 3's builds stop at $4.00 of their $4.50 share."""
  52 | +        self.assertEqual((PLG.PL.LY_STOP_USD, PLG.PL.LY_LIMIT_USD), (4.00, 4.50))
  53 | +        self.assertEqual(PLG.PL.LY_LIMIT_BASIS, "reported")               # vendor-reported (audit 2114 C1, glm)
  54 | +        self.assertGreaterEqual(PLG.PL.LY_LIMIT_USD - PLG.PL.LY_STOP_USD, 0.50)   # one build's headroom (C1, glm)
  55 | +        self.assertTrue(PLG.PL.SPEND.endswith("SPEND_B3.json"))          # never the closed $20 ledger again
  56 | +        self.assertIsNone(PLG.start_refused(3.99))
  57 | +        why = PLG.start_refused(4.0)
  58 | +        self.assertIn("at or over the $4.00 stop: no build starts", why)
  59 |          self.assertIn("SAY IT ON STATE LINE 1 IN CAPITALS", why)
  60 |  
  61 |  
  62 | 
```

---

pp-selectid, RULING 108 (the orchestrator, 21:20 ET Nov 14): "NEW BATCH, 'BATCH 3', STARTS NOW and runs to 21:10 ET
Nov 15. The old $20 ledger is CLOSED at its present figure... CAP $8.00 for the 24 hours... Budget inside it: builds +
sealing $4.50, audits $2.50, mining and checks $1.00."

THE CHANGE (tests/package/proof_ly.py and tests/package/test_ruling_102.py):
- SPEND: the build ledger is now tests/package/proof/SPEND_B3.json, a new file. The closed $20 order's SPEND_LY.json
  is never written again.
- LY_LIMIT_USD 20.00 -> 4.50: the Router's limit, which no paid call passes. Each call RESERVES its upper bound while
  in flight.
- LY_STOP_USD 19.00 -> 4.00: the stop, at or over which no build starts. A build runs $0.15-0.50, so none ends over
  $4.50.
- The test of the stop moves to the new numbers and checks the ledger path.

UNCHANGED GUARDS (you see only the diff):
- proof_ledger.build_router passes spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD and limit_basis=PL.LY_LIMIT_BASIS
  ("reported").
- proof_ledger.start_refused(spent0) refuses when spent0 >= PL.LY_STOP_USD.
- A missing ledger file is an empty one (Router._ledger), so the batch starts at $0.00.

PLEASE CHECK: (1) Can any build path still write the closed SPEND_LY.json? (2) Are the stop and the limit
consistent with "never start a build that would end over the cap"? (3) Does the test pin the behaviour?


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
