# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0614
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 230 s finish=stop usage in 8263 / out 6304 usd~0.119 (upper-bound price)

<medium> **(a) "glm last, after Grok" — the ruling's wording is ambiguous; the chosen order is defensible but the ruling text in the config does not record the deepseek question.** `pipeline/model_providers.json:48` (ruling_0612): "glm IS coherence's last fallback, after Grok (94 % ...)". The implemented list `coherence_verdict:coherence = [Grok, deepseek, glm]` (diff line 38) keeps ruling 96's deepseek second. That is a reasonable reading — "last" = appended after the existing chain — and the test pins it (`test_ledger_build.py:95`). But the ruling as quoted never says whether deepseek stays; if the orchestrator meant "glm is the *only* fallback, after Grok", the list should be `[Grok, glm]`. Not a code defect; flagging because the ruling note (line 48) does not state the decision, so a future reader cannot tell intent from the config. No concrete failure scenario; informational.

<medium> **(c) The default `coherence_verdict` list is left at Grok -> deepseek, so the medley's/spotlight's value verdicts have no glm fallback and the 06:12 gap-closing does not reach them.** Diff lines 34–39: `coherence_verdict:coherence` gains glm, but the bare `coherence_verdict` (line 12, unchanged, not shown in the diff hunk but visible at the top of the hunk at line 6–11 context) — wait, the bare `coherence_verdict` is not in the diff; the hunk at lines 26–39 shows `coherence_verdict:clips_alone` and `coherence_verdict:coherence` changed while the bare key sits above the hunk. The prompt states the value verdicts are deliberately left on the default list (Grok -> deepseek) with no replay data — so this is a *documented* decision, not an oversight. Residual risk: the same "xAI down + deepseek writing" scenario that motivated ruling 06:12 (1) still leaves the value verdicts with no verdict (fail closed, correct per M12, but a build-blocking outage of one vendor). Concrete scenario: xAI down, deepseek writes the text being judged, a value verdict is needed → no family → package fails. That is the *same* gap ruling 06:12 closed for `coherence_verdict:coherence`, left open for the value verdicts. If intentional, fine; the ruling note (line 48) does not say the value verdicts were considered. Informational.

<medium> **(c) `coherence_verdict:clips_alone` = [Grok, Gemini] — "Plan B's other outside family" is a reasonable reading, but the ruling's parenthetical about frozen legs is not in the config note, and the test's fail-closed check for clips-alone has a subtle ordering issue.** `test_ledger_build.py:108–109`: the test sets `r.down[GEM]` and asserts the pick is None for kind="clips_alone". But it does not first clear... actually it does: line 108 sets `r.down[GEM]` while Grok (X) is already down from the earlier scenario (xAI answering nothing, set at line 99's Router construction — wait, the Router is constructed at line 99 with `ch` and the test at line 100–107 asserts picks with xAI down; then line 108 adds GEM to `r.down`). So the scenario is: X down (from construction), then GEM down → clips-alone spent → None. Correct. Then line 110: `r.down[G] = "glm answers nothing"` → coherence = [X, DS, G]: X down, DS writes (family skip), G down → None. Correct. Then line 112 `del r.down[G], r.down[GEM]` restores. Then lines 113–117: step A picks. But wait — line 112 deletes G and GEM from `r.down`, yet X (Grok) remains down from construction. Line 113 picks step_a_first: [G, DS, X] → G (glm) not down, not the writer → picked. Line 114: `fb = r.backends[first]` → glm's back-end. Line 115: step_a_second with glm's vendor/family excluded → [X, G, DS] minus glm → [X, DS] → X is down → DS. Line 117 asserts `(G, DS)`. Correct — two Heimdall families, Grok down. Then line 118 `r.down.clear()` — this also clears X's down state, so line 119–120: step_a_second → [X, G, DS] minus glm → X, and X is now *not* down → X. Line 120 asserts X. Correct. One subtlety: line 118 `r.down.clear()` clears *everything*, including the "xAI answering nothing" scenario the test name promises; the final assertion (line 120) therefore tests "Grok answers" — which is what the comment says ("(c): Grok confirms when it answers"). Consistent. No defect.

<medium> **(d) Can the change make a verdict looser? Yes — two places, both pinned by ruling.** First, `coherence_verdict:clips_alout` [sic] — `coherence_verdict:clips_alone` = [Grok, Gemini] replaces [Grok, qwen, deepseek] *and* drops the Heimdall fallback entirely: previously, with Grok down, qwen or deepseek (Heimdall) could decide clips-alone; now only Gemini. If Gemini is also down, the verdict fails closed where it previously... wait, previously with Grok down the chain was [qwen, deepseek] — but if deepseek wrote the text, deepseek is skipped (L-x), leaving qwen; if qwen also out-of-contract, fail. So the old chain could still produce a verdict with Grok down; the new one cannot (unless Gemini answ

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 27 s finish=stop usage in 8314 / out 332 usd~0.050 (upper-bound price)

<medium> pipeline/model_providers.json:47 (ruling_0612 text): lists match rulings verbatim (context_verdict:step_a_first=[glm,deepseek,grok], step_a_second=[grok,glm,deepseek], context_verdict=[glm,deepseek,grok], coherence:coherence=[grok,deepseek,glm] with glm last after "ruling 96's deepseek", clips_alone=[grok,google:gemini-2.5-pro]); test_ledger_build.py:89 asserts qwen absent from every step_a key. No qwen on any step-A path verifiable in diff.  
<medium> tests/package/test_ledger_build.py:106 (updated expectation with X down + DS writing): coherence picks G=glm (last fallback), clips_alone picks GEM; both return None after those are downed (lines 109,111). Matches ruling (1) fail-closed after list exhausted; concrete input "deepseek wrote the coherence text, grok+glm down" now closed where old test expected None.  
<medium> pipeline/model_providers.json:32 (clips_alone change): exactly "Plan B's other outside family" per ruling_0612 comment; default coherence_verdict untouched (still grok->deepseek per test:98), as ruling states "every other list is ruling 96's, unchanged". No diff evidence of other lists (shadow/Plan B/default value verdicts) being edited.  
No concrete input verifiable from diff that breaks rulings or makes any verdict looser than the added glm fallback explicitly permits.  

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 8910 / out 3203 usd~0.075 (upper-bound price)

To audit the configuration change in `pipeline/model_providers.json` and `tests/package/test_ledger_build.py`, I will verify the changes against the Orchestrator's Rulings (06:12 ET Nov 14) and the governing laws (specifically L-l: Fail Closed, and the specific routing constraints).

### Analysis

**1. Verification of Ruling (1): The Coherence Gap**
*   **Ruling:** "glm IS coherence's last fallback, after Grok... Clips-alone has NO Heimdall fallback... with Grok down it goes to Plan B's other outside family... else fails closed."
*   **Diff (`coherence_verdict:coherence`):** Changed from `[Grok, Deepseek]` to `[Grok, Deepseek, Glm]`.
    *   *Check:* Does this match "glm last, after Grok"? The ruling says "after Grok". It does not explicitly say "replace Deepseek". Ruling 96 established Deepseek as the second choice. The 06:12 ruling addresses the *gap* (no family left if Grok and Deepseek fail/are writers). Adding Glm as the *last* fallback preserves the Ruling 96 order while closing the gap.
    *   *Scenario:* If Grok is down and Deepseek wrote the text (so it is skipped due to L-x/vendor conflict), the router moves to Glm. If Glm is also down or fails, the list is spent -> Fail Closed. This matches the ruling.
*   **Diff (`coherence_verdict:clips_alone`):** Changed from `[Grok, Qwen, Deepseek]` to `[Grok, Gemini]`.
    *   *Check:* "NO Heimdall fallback". Qwen and Deepseek are Heimdall. They are removed.
    *   *Check:* "Plan B's other outside family". The background states Plan B's coherence list is `Grok -> Gemini -> OpenAI -> Anthropic`. Under `heimdall_first`, OpenAI/Anthropic are frozen legs (dropped by `proof_ly.chains()`). Therefore, the only available "outside family" after Grok is Gemini.
    *   *Result:* `[Grok, Gemini]` is the correct implementation.

**2. Verification of Ruling (2): Qwen Struck from Step A**
*   **Ruling:** "QWEN ON STEP A: STRUCK... qwen... is out of step A entirely."
*   **Diff (`context_verdict:step_a_first`):** Changed from `[Glm, Deepseek, Qwen, Grok]` to `[Glm, Deepseek, Grok]`.
    *   *Result:* Qwen removed. Correct.
*   **Diff (`context_verdict:step_a_second`):** Changed from `[Grok, Qwen, Glm, Deepseek]` to `[Grok, Glm, Deepseek]`.
    *   *Result:* Qwen removed. Correct.
*   **Diff (`context_verdict` default):** Changed from `[Glm, Deepseek, Qwen, Grok]` (implied by context of removal) to `[Glm, Deepseek, Grok]`.
    *   *Result:* Qwen removed. Correct.
*   **Test Verification:** `test_ledger_build.py` line 89 asserts `assertNotIn(Q, ...)` for all `context_verdict:step_a*` keys. This confirms no Qwen remains on any Step A path.

**3. Attack (a): Is "glm last, after Grok" right as Grok -> deepseek -> glm?**
*   The ruling says "glm IS coherence's last fallback, after Grok".
*   Ruling 96 (previous) set `coherence` to `Grok -> Deepseek`.
*   The 06:12 ruling identifies a *gap* where coherence had no family if Grok and Deepseek were unavailable/conflicted.
*   By appending Glm to the end (`Grok -> Deepseek -> Glm`), we maintain the Ruling 96 priority (Grok first, Deepseek second) while satisfying the 06:12 requirement that Glm is the *last* fallback.
*   If Glm were to *replace* Deepseek, it would violate Ruling 96's established order unless explicitly revoked, which it was not. The ruling specifically addresses the *exhaustion* of the list.
*   **Verdict:** The order `Grok -> Deepseek -> Glm` is correct.

**4. Attack (b): Is any qwen left on a step-A path?**
*   Checked `step_a_first`, `step_a_second`, and the default `context_verdict`.
*   All Qwen entries are removed.
*   **Verdict:** No Qwen remains.

**5. Attack (c): Clips-alone and other lists**
*   **Clips-alone:** `Grok -> Gemini`.
    *   Is Gemini the right reading? Yes, it is the next non-frozen, non-Heimdall model in the Plan B coherence chain.
    *   Does anything else need the change?
        *   `coherence_verdict` (default): The diff does *not* show a change to the default `coherence_verdict` list in the JSON block provided (lines 34-39 only show `clips_alone` and `coherence` kinds).
        *   *Wait, let's look closer at the diff.*
        *   Lines 34-39:
            ```json
            "coherence_verdict:clips_alone": [
             "xai:grok-4.20-0309-reasoning",
            -    "heimdall:qwen/qwen3.8-27b",
            -    "heimdall:deepseek/deepseek-v4.1-flash"
            +    "google:gemini-2.5-pro"
            ],
            "coherence_verdict:coherence": [
             "xai:grok-4.20-0309-reasoning",
            -    "heimdall:deepseek/deepseek-v4.1-flash"
            +    "heimdall:deepseek/deepseek-v4.1-flash",
            +    "heimdall:z-ai/glm-5.3-flash"
            ]
            ```
        *   The default `coherence_verdict` (used by spotlight/medley value verdicts) is **not** modified in this diff.
        *   The prompt states: "The value verdicts are deliberately left on t

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 0614 (the orchestrator's 06:12 routing rulings (1) and (2)), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes (no defect); qwen3.8-27b SHIP yes (two conditions); glm-5.3-flash SHIP yes with
conditions (documentation only). No critical, no high defect from any reviewer. Upper-bound cost of the cycle: about
$0.24 ($0.050 + $0.075 + $0.119), outside SPEND_LY.json.

## Implemented

- glm (a) + condition 1 (i): the "94 %" read as Grok's figure. The ruling_0612 note now says whose it is: "glm agreed
  with Grok on 94 % of the replay's coherence decisions". It also says outright that deepseek "stays second". The note
  already had glm "after Grok and ruling 96's deepseek"; it is now explicit.
- glm (c) + condition 1 (ii), and qwen's <high>: the coherence role's DEFAULT list (Grok -> deepseek) is unchanged, and
  the note did not say so. It now records that the default list is not changed, that the spotlight's closing-line and
  the medley's takeaway value verdicts use it, that the replay has no data for them, and that the orchestrator is
  asked (STATE line 1, 06:14, question B).
  - This is not a defect of this change. The ruling names coherence and clips-alone. Moving a verdict type off
    unmeasured data would break ruling 96's own rule.
- glm condition 3 (Plan B's clips-alone): VERIFIED from the code, and the note now records it.
  - providers.Router.chain reads Plan B's lists first while Heimdall is down. The keys tried are
    ["coherence_verdict:clips_alone", "coherence_verdict"].
  - routing.plan_b has no clips-alone key of its own, so clips-alone in Plan B mode is Plan B's coherence list:
    Grok -> Gemini -> OpenAI -> Anthropic (local and openai_stt are dropped by proof_ly.plan_b_chains).
  - So no Heimdall model judges clips-alone in either mode.

## Verified, no change

- qwen condition 2 / glm "unverified": Gemini resolves.
  - backends["google:gemini-2.5-pro"] exists (key name GEMINI_API_KEY_MEDLEY, min_out 8000), and it is Plan B's
    coherence list's second entry.
  - The edit script asserted both before it wrote.
  - proof_ly.FROZEN = ("local:", "anthropic:", "openai:", "openai_stt:") is a deny-list, so a google: leg survives
    chains().
  - The test asserts chains("heimdall_first")["coherence_verdict:clips_alone"] == [Grok, Gemini], and that the xAI-down
    pick returns Gemini. It passes.
- glm condition 2: no other test pins the old lists. Verified by execution: all 19 suites pass in the scratch copy
  dev02 (518 tests). Any test pinning the old lists would fail.
- qwen <medium> ("today" routing unchanged): every build runs with --routing heimdall_first (handoff 3.1; the driver
  passes it).
  - The 06:12 rulings amend ruling 96's heimdall_first table. "today" is the legacy mode, and the test still pins its
    two lists as before (a regression check, not the live routing).
  - No change.
- glm (d): no verdict becomes looser.
  - Every changed model is appended after the old deciders (coherence), removed where the rulin

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0614/C2_STEP.diff (121 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 2991c47..ede12b2 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -324,7 +324,6 @@
   6 |     "context_verdict": [
   7 |      "heimdall:z-ai/glm-5.3-flash",
   8 |      "heimdall:deepseek/deepseek-v4.1-flash",
   9 | -    "heimdall:qwen/qwen3.8-27b",
  10 |      "xai:grok-4.20-0309-reasoning"
  11 |     ],
  12 |     "coherence_verdict": [
  13 | @@ -356,12 +355,10 @@
  14 |     "context_verdict:step_a_first": [
  15 |      "heimdall:z-ai/glm-5.3-flash",
  16 |      "heimdall:deepseek/deepseek-v4.1-flash",
  17 | -    "heimdall:qwen/qwen3.8-27b",
  18 |      "xai:grok-4.20-0309-reasoning"
  19 |     ],
  20 |     "context_verdict:step_a_second": [
  21 |      "xai:grok-4.20-0309-reasoning",
  22 | -    "heimdall:qwen/qwen3.8-27b",
  23 |      "heimdall:z-ai/glm-5.3-flash",
  24 |      "heimdall:deepseek/deepseek-v4.1-flash"
  25 |     ],
  26 | @@ -378,12 +375,12 @@
  27 |     ],
  28 |     "coherence_verdict:clips_alone": [
  29 |      "xai:grok-4.20-0309-reasoning",
  30 | -    "heimdall:qwen/qwen3.8-27b",
  31 | -    "heimdall:deepseek/deepseek-v4.1-flash"
  32 | +    "google:gemini-2.5-pro"
  33 |     ],
  34 |     "coherence_verdict:coherence": [
  35 |      "xai:grok-4.20-0309-reasoning",
  36 | -    "heimdall:deepseek/deepseek-v4.1-flash"
  37 | +    "heimdall:deepseek/deepseek-v4.1-flash",
  38 | +    "heimdall:z-ai/glm-5.3-flash"
  39 |     ]
  40 |    },
  41 |    "plan_b": {
  42 | @@ -461,6 +458,7 @@
  43 |     ]
  44 |    },
  45 |    "ruling_88": "RULING 88 (orchestrator 22:15 Nov 13), from the replay's interim, the full table to confirm: (a) fidelity and exclusion on Heimdall now (two families, Grok last); (b) step C and the hook rating move when the full table holds the interim's 98-100 % (Grok first until then); (c) step A: Heimdall FIRST, a clip Heimdall refuses is refused and Grok is never asked, a clip Heimdall passes goes to Grok to confirm; (d) clips-alone and coherence keep Grok, glm out of both; (e) qwen never decides coherence or step C. THE FULL TABLE (01:06 ET Nov 14, 884 rows): (b) holds for the hook rating (qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %): it moved, qwen -> glm -> deepseek -> Grok; it does not hold for step C (glm 97 %, deepseek 96 %; qwen 98 % but barred by (e)): Grok first.",
  46 | -  "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement."
  47 | +  "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement.",
  48 | +  "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and after ruling 96's deepseek, which stays second (glm agreed with Grok on 94 % of the replay's coherence decisions, with one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here; in Plan B mode the router already reads Plan B's coherence list, Grok -> Gemini -> OpenAI -> Anthropic), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. NOT CHANGED: the coherence role's default list (Grok -> deepseek), which the spotlight's closing-line and the medley's takeaway value verdicts use: the replay has no data for them (the orchestrator is asked, STATE 06:14, question B). Every other list is ruling 96's, unchanged."
  49 |   }
  50 |  }
  51 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
  52 | index b88bad7..3c96174 100644
  53 | --- a/tests/package/test_ledger_build.py
  54 | +++ b/tests/package/test_ledger_build.py
  55 | @@ -829,10 +829,11 @@ class TestDriverRefuses(unittest.TestCase):
  56 |  
  57 |  class TestRuling85NoXai(unittest.TestCase):
  58 |      """RULINGS 85 + 88 (22:15 Nov 13), on the real config and the real Router's skip rule (no model is called):
  59 | -    the lists per verdict type under heimdall_first; with xAI answering nothing and deepseek writing, every type but
  60 | -    one still has a Heimdall family off the writer, and step A's two verdicts come from two families. The one gap:
  61 | -    coherence keeps Grok with deepseek alone behind it (88 (d): glm out; (e): qwen never decides it), so when deepseek
  62 | -    writes and xAI is down, coherence has no family and the package fails closed."""
  63 | +    the lists per verdict type under heimdall_first; with xAI answering nothing and deepseek writing, every type
  64 | +    still has a family off the writer, and step A's two verdicts come from two families. The gap ruling 96 left
  65 | +    (coherence had Grok with deepseek alone behind it, so with deepseek writing and xAI down it had no family) is
  66 | +    closed by the orchestrator's 06:12 rulings: glm is coherence's LAST fallback; clips-alone has NO Heimdall fallback
  67 | +    (Grok, then Plan B's other outside family, Gemini, else it fails closed); qwen is struck from step A."""
  68 |  
  69 |      @staticmethod
  70 |      def pl():
  71 | @@ -850,19 +851,23 @@ class TestRuling85NoXai(unittest.TestCase):
  72 |          return None
  73 |  
  74 |      def test_ruling_96s_lists_and_xai_answering_nothing(self):
  75 | -        """RULING 96 (01:40 ET Nov 14), final until re-measured, on ruling 88's structure."""
  76 | +        """RULING 96 (01:40 ET Nov 14), final until re-measured, on ruling 88's structure, as the orchestrator's 06:12
  77 | +        rulings amend it: (1) glm last for coherence, no Heimdall model for clips-alone; (2) qwen struck from step A."""
  78 |          PL = self.pl()
  79 |          X, DS, G, Q = ("xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash",
  80 |                         "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b")
  81 | +        GEM = "google:gemini-2.5-pro"
  82 |          ch = PL.chains("heimdall_first")
  83 |          self.assertEqual(ch["fidelity_verdict"], [G, Q, X])                       # 96: glm -> qwen -> Grok
  84 |          self.assertEqual(ch["exclusion_verdict"], [G, DS, X])                      # 96: glm -> deepseek -> Grok
  85 | -        self.assertEqual(ch["context_verdict:step_a_first"], [G, DS, Q, X])        # 96: glm first (speed), deepseek
  86 | +        self.assertEqual(ch["context_verdict:step_a_first"], [G, DS, X])           # 06:12 (2): glm -> deepseek, no qwen
  87 | +        self.assertEqual(ch["context_verdict:step_a_second"], [X, G, DS])          # (c) Grok confirms; 06:12 (2)
  88 | +        self.assertEqual(ch["context_verdict"], [G, DS, X])                        # the role's default: no qwen either
  89 | +        self.assertNotIn(Q, [b for k, v in ch.items() if k.startswith("context_verdict:step_a") for b in v])
  90 |          self.assertEqual(ch["coherence_verdict:hook"], [Q, G, DS, X])              # 88 (b) / 96: the hook moved
  91 | -        self.assertEqual(ch["context_verdict:step_a_second"][0], X)               # (c): Grok confirms
  92 |          self.assertEqual(ch["context_verdict:step_c"], [X, G, DS])                 # (b) / (e): no qwen
  93 | -        self.assertEqual(ch["coherence_verdict:coherence"], [X, DS])              # (d) / (e): no glm, no qwen
  94 | -        self.assertEqual(ch["coherence_verdict:clips_alone"], [X, Q, DS])         # (d): no glm
  95 | +        self.assertEqual(ch["coherence_verdict:coherence"], [X, DS, G])           # 06:12 (1): glm the LAST fallback
  96 | +        self.assertEqual(ch["coherence_verdict:clips_alone"], [X, GEM])           # 06:12 (1): no Heimdall model
  97 |          today = PL.chains("today")                                                 # (d) and (e) hold today too
  98 |          self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS, G]))
  99 |          r = PL.P.Router(env_path="/nonexistent", routing="heimdall_first", chains=ch)
 100 | @@ -876,12 +881,17 @@ class TestRuling85NoXai(unittest.TestCase):
 101 |          self.assertEqual(got, {("fidelity_verdict", None): G, ("exclusion_verdict", None): G,
 102 |                                 ("speaker_verdict", None): G, ("viewer_takeaway", None): G,
 103 |                                 ("context_verdict", "step_c"): G, ("coherence_verdict", "hook"): Q,
 104 | -                               ("coherence_verdict", "clips_alone"): Q,
 105 | -                               ("coherence_verdict", "coherence"): None})          # THE GAP (fails closed)
 106 | +                               ("coherence_verdict", "clips_alone"): GEM,          # Plan B's other outside family
 107 | +                               ("coherence_verdict", "coherence"): G})            # the gap is closed: glm, last
 108 | +        r.down[GEM] = "Gemini answers nothing (the test)"
 109 | +        self.assertIsNone(self.pick(r, "coherence_verdict", {w.vendor}, {w.family}, kind="clips_alone"))   # closed
 110 | +        r.down[G] = "glm answers nothing (the test)"
 111 | +        self.assertIsNone(self.pick(r, "coherence_verdict", {w.vendor}, {w.family}, kind="coherence"))     # closed
 112 | +        del r.down[G], r.down[GEM]
 113 |          first = self.pick(r, "context_verdict", {w.vendor}, {w.family}, kind="step_a_first")
 114 |          fb = r.backends[first]
 115 |          second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
 116 | -        self.assertEqual((first, second), (G, Q))                                  # two Heimdall families, Grok down
 117 | +        self.assertEqual((first, second), (G, DS))                                 # two Heimdall families, Grok down
 118 |          r.down.clear()
 119 |          second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
 120 |          self.assertEqual(second, X)                                                # (c): Grok confirms when it answers
 121 | 
```

---

You are auditing a SMALL configuration change on branch pp-selectid (Protocol Pulse's moments-first video builder).
Only state what you can verify from the diff; if uncertain, say so; do not guess. Be specific: file:line and a concrete
input that breaks it.

BACKGROUND (static):
- Every model verdict goes through providers.Router. Under routing "heimdall_first" (the routing every build uses),
  each verdict type has an ordered list in pipeline/model_providers.json routing.heimdall_first ("<role>" or
  "<role>:<kind>"); the router tries the list in order, skipping a back-end that is down or whose vendor / model family
  wrote the text being judged (law L-x). proof_ly.chains() drops the frozen legs (local:, anthropic:, openai:,
  openai_stt:). An out-of-contract answer moves on to the next model (providers.call_parsed); when the list is spent
  there is no verdict, which never passes (fail closed). Writers are Heimdall deepseek -> qwen -> Grok.
- Ruling 96 (01:40 ET Nov 14) set the lists from a replay of 884 verdicts against Grok (Grok's self-agreement: step A
  85 %, clips-alone 79 %). It left a gap: coherence was Grok -> deepseek, so with xAI down and deepseek writing,
  coherence had no family.

THE ORCHESTRATOR'S RULINGS (06:12 ET Nov 14), verbatim:
(1) "THE COHERENCE GAP: glm IS coherence's last fallback, after Grok (94 % on the replay, one anchor failure in the
    whole table); an out-of-contract glm answer is no verdict; after glm, fail closed. Clips-alone has NO Heimdall
    fallback (52-62 %): with Grok down it goes to Plan B's other outside family, else fails closed."
(2) "QWEN ON STEP A: STRUCK. Step A's Heimdall filter is glm -> deepseek; qwen (mostly errors, 9 of 43 refusals let
    through) is out of step A entirely."

THE CHANGE (the diff follows):
- context_verdict:step_a_first  glm -> deepseek -> qwen -> Grok   =>  glm -> deepseek -> Grok
- context_verdict:step_a_second Grok -> qwen -> glm -> deepseek   =>  Grok -> glm -> deepseek
- context_verdict (the role's default; every step-A call names its kind, so no live caller) => glm -> deepseek -> Grok
- coherence_verdict:coherence   Grok -> deepseek                  =>  Grok -> deepseek -> glm
- coherence_verdict:clips_alone Grok -> qwen -> deepseek          =>  Grok -> google:gemini-2.5-pro (Plan B's
  coherence list is Grok -> Gemini -> OpenAI -> Anthropic; OpenAI / Anthropic are frozen legs under heimdall_first)
- a "ruling_0612" note; tests/package/test_ledger_build.py pins every list and, with xAI down and deepseek writing,
  checks coherence -> glm, clips-alone -> Gemini, each failing closed when that last model is down too, and step A's
  two verdicts from two families (glm, then deepseek).

ATTACK:
(a) Does each list match the rulings exactly? Is "glm last, after Grok" right as Grok -> deepseek -> glm (deepseek kept
    second from ruling 96), or should glm replace deepseek?
(b) Is any qwen left on a step-A path (any list a step-A call can reach)?
(c) Clips-alone: is Gemini the right reading of "Plan B's other outside family", and does anything else (the shadow,
    Plan B's own lists, the default "coherence_verdict" list the spotlight's and the medley's value verdicts use) need
    the same change? The value verdicts are deliberately left on the default list (Grok -> deepseek): no replay data.
(d) Can the change make a verdict LOOSER anywhere (a weaker model deciding where a stronger one did)?

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete scenario), then
"SHIP: yes / no / yes with conditions".


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
