# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_0826
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 279 s finish=stop usage in 12500 / out 3338 usd_reported=0.000801 usd~0.088 (upper-bound price)

The code implements RULING 119 (3) by removing `heimdall:z-ai/glm-5.3-flash` from all decision chains in `model_providers.json` and updating the corresponding pinning tests in `test_ledger_build.py`.

### Analysis
1.  **Chain Removal**: I have verified that `heimdall:z-ai/glm-5.3-flash` was removed from all 16 lists in `model_providers.json`, including the default roles and the `heimdall_first` and `plan_b` routing lists.
2.  **Standing Rulings**:
    *   **RULING 06:12**: Qwen remains absent from all `context_verdict:step_a` lists.
    *   **RULING 115**: The `coherence_verdict:hook` remains exclusively `["xai:grok-4.20-0309-reasoning"]`.
    *   **RULING 96/102**: The remaining models shifted up to fill the gaps, maintaining the established priority order.
3.  **Test Verification**:
    *   `test_ruling_82_the_context_verdict_chain` correctly reflects the new `today` chain: `[X, DS, Q]`.
    *   `test_ruling_96s_lists_and_xai_answering_nothing` correctly validates the "closed up" lists.
    *   The "Grok down" scenario in the tests correctly identifies that `exclusion_verdict`, `context_verdict:step_c`, and `coherence_verdict:coherence` now fail closed (return `None`) because GLM (the last fallback) is gone and DeepSeek is skipped as the writer's family.
    *   The "Step A first screen" logic correctly identifies a `HOLD` state when DeepSeek is the writer and Grok is down/capped, as GLM is no longer available to provide a verdict.

The implementation is precise, follows the "fail closed" principle (M12), and adheres to all governing laws.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 97 s finish=stop usage in 11955 / out 2737 usd_reported=0.003641 usd~0.077 (upper-bound price)

I have reviewed the diff for `pp-selectid` (RULING 119: removal of `glm-5.3-flash` from all model chains).

### Analysis

**1. Compliance with RULING 119 (3)**
*   **Requirement:** "take glm out of every chain until I say; the next healthy member takes its place."
*   **Observation:** The diff removes `"heimdall:z-ai/glm-5.3-flash"` from 16 distinct lists in `pipeline/model_providers.json`.
    *   `context_verdict` (default, heimdall_first, today)
    *   `fidelity_verdict`
    *   `exclusion_verdict`
    *   `speaker_verdict`
    *   `viewer_takeaway`
    *   `context_verdict:step_a_first`
    *   `context_verdict:step_a_second`
    *   `context_verdict:step_c`
    *   `coherence_verdict:coherence`
    *   `coherence_verdict:hook` (Note: `glm` was not in the hook list per Ruling 115, but the diff shows removal from other lists. Let's verify the hook list in the diff. Line 103-104 shows `coherence_verdict:hook` context. The diff at lines 103-104 doesn't show a removal for hook, but the text says "16 lists". Let's count the removals in the diff:
        1.  Line 9: `context_verdict` (default?)
        2.  Line 17: `context_verdict` (another routing?)
        3.  Line 25: `context_verdict` (another routing?)
        4.  Line 33: `exclusion_verdict`
        5.  Line 41: `fidelity_verdict`? No, line 41 is in a block starting line 37. Let's trace carefully.
        
        Let's look at the JSON structure changes:
        *   Block 1 (lines 5-12): Removes glm from a list.
        *   Block 2 (lines 13-20): Removes glm from a list.
        *   Block 3 (lines 21-28): Removes glm from a list.
        *   Block 4 (lines 29-35): Removes glm from a list.
        *   Block 5 (lines 36-44): Removes glm from a list.
        *   Block 6 (lines 45-52): Removes glm from a list.
        *   Block 7 (lines 53-60): `heimdall_first.context_verdict` removes glm.
        *   Block 8 (lines 61-68): `heimdall_first.fidelity_verdict` removes glm.
        *   Block 9 (lines 69-73): `heimdall_first.exclusion_verdict` removes glm.
        *   Block 10 (lines 74-79): `heimdall_first.speaker_verdict` removes glm.
        *   Block 11 (lines 80-85): `heimdall_first.viewer_takeaway` removes glm.
        *   Block 12 (lines 86-90): `heimdall_first.context_verdict:step_a_first` removes glm.
        *   Block 13 (lines 91-97): `heimdall_first.context_verdict:step_a_second` removes glm.
        *   Block 14 (lines 98-102): `heimdall_first.context_verdict:step_c` removes glm.
        *   Block 15 (lines 106-111): `heimdall_first.coherence_verdict:coherence` removes glm.
        *   Block 16 (lines 116-121): `plan_b.context_verdict:step_c` removes glm.
        
        Total 16 removals. This matches the description.
*   **Verification of "Next Member Takes Place":**
    *   `step_a_first`: Was `[glm, deepseek, grok]` (implied by Ruling 96/06:12). Now `[deepseek, grok]`. Correct.
    *   `fidelity`: Was `[glm, qwen, grok]`. Now `[qwen, grok]`. Correct.
    *   `exclusion`: Was `[glm, deepseek, grok]`. Now `[deepseek, grok]`. Correct.
    *   `coherence`: Was `[grok, deepseek, glm]`. Now `[grok, deepseek]`. Correct.
    *   `step_a_second`: Was `[grok, deepseek, glm, gemini, local]`. Now `[grok, deepseek, gemini, local]`. Correct.

**2. Compliance with Standing Rulings**
*   **Ruling 06:12 (Nov 14):** "QWEN IS STRUCK FROM STEP A".
    *   Check `step_a_first`: `[deepseek, grok]`. No Qwen. Pass.
    *   Check `step_a_second`: `[grok, deepseek, gemini, local]`. No Qwen. Pass.
*   **Ruling 96 (Nov 14):** "glm last for coherence".
    *   Check `coherence`: `[grok, deepseek]`. Glm is gone. The relative order of remaining items is preserved. Pass.
*   **Ruling 115 (Nov 15):** "Hook is Grok alone".
    *   Check `coherence_verdict:hook`: The diff does not show a change to the hook list itself (lines 103-104 show context, but no `-` line for glm in the hook list, likely because it wasn't there or the diff hunk doesn't cover it). The text says "16 lists". The hook list was likely already `[grok]` or `[grok, ...]` without glm. The test `test_ruling_96s...` asserts `ch["coherence_verdict:hook"] == [X]` (Grok). This is unchanged. Pass.
*   **Ruling 102 (Nov 14):** "Step A unavailable must never end a clip... held for this build".
    *   The code logic for holding is in `pipeline/package.py` (not in diff). The config change ensures that if `deepseek` (writer) is skipped and `grok` is capped/down, the list is exhausted, triggering the hold logic. This is consistent.

**3. Test Verification**
*   `test_ruling_82_the_context_verdict_chain`:
    *   Old: `["xai:grok...", "heimdall:deepseek...", "heimdall:z-ai/glm...", "heimdall:qwen..."]`
    *   New: `["xai:grok...", "heimdall:deepseek...", "heimdall:qwen..."]`
    *   This matches the removal of glm.
*   `test_ruling_96s_lists_and_xai_answering_nothing`:
    *   `fidelity_verdict`

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_0826 (RULING 119 (3): glm out of every chain)

Seats (Heimdall only, ruling 118): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 2 of 3 (mimo cut off at
16,000 tokens with no answer; cycle 2 gives it 32,000). qwen P1_OR_WORSE 0; gemma 0. Cycle 1: $0.0063 of Heimdall, not
capped. No P1.

gemma checked every point the QUESTION asks: glm removed from all 16 lists; qwen absent from every step-A list (06:12 Nov
14); the hook Grok alone (115); the remaining members moved up in their ruled order (96 / 102); the tests' picks with Grok
down and deepseek writing (exclusion, step C, coherence: no leg, fail closed; step A's first screen: held).

P3 noted, not changed: qwen "the ruling_102 line gains a trailing comma": JSON syntax only (the new ruling_119 note follows it
in the routing object); the file parses (json.load) and every list test passes.

CHANGED AFTER CYCLE 1: nothing.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_0826/C2_STEP.diff (229 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 57c2e64..061a9f0 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -203,7 +203,6 @@
   6 |      "xai:grok-4.20-0309-reasoning",
   7 |      "anthropic:claude-opus-5-5",
   8 |      "heimdall:deepseek/deepseek-v4.1-flash",
   9 | -    "heimdall:z-ai/glm-5.3-flash",
  10 |      "heimdall:qwen/qwen3.8-27b",
  11 |      "local:gemma3:27b"
  12 |     ],
  13 | @@ -214,7 +213,6 @@
  14 |      "xai:grok-4.20-0309-reasoning",
  15 |      "anthropic:claude-opus-5-5",
  16 |      "heimdall:deepseek/deepseek-v4.1-flash",
  17 | -    "heimdall:z-ai/glm-5.3-flash",
  18 |      "heimdall:qwen/qwen3.8-27b",
  19 |      "local:gemma3:27b"
  20 |     ],
  21 | @@ -226,7 +224,6 @@
  22 |      "anthropic:claude-opus-5-5",
  23 |      "xai:grok-4.20-0309-reasoning",
  24 |      "heimdall:deepseek/deepseek-v4.1-flash",
  25 | -    "heimdall:z-ai/glm-5.3-flash",
  26 |      "heimdall:qwen/qwen3.8-27b",
  27 |      "local:gemma3:27b"
  28 |     ],
  29 | @@ -263,7 +260,6 @@
  30 |      "xai:grok-4.20-0309-reasoning",
  31 |      "anthropic:claude-opus-5-5",
  32 |      "heimdall:deepseek/deepseek-v4.1-flash",
  33 | -    "heimdall:z-ai/glm-5.3-flash",
  34 |      "heimdall:qwen/qwen3.8-27b"
  35 |     ],
  36 |     "what": "moments.exclusion_verdict: the hard exclusions of law L-u on one moment in its context"
  37 | @@ -273,7 +269,6 @@
  38 |      "anthropic:claude-opus-5-5",
  39 |      "xai:grok-4.20-0309-reasoning",
  40 |      "heimdall:deepseek/deepseek-v4.1-flash",
  41 | -    "heimdall:z-ai/glm-5.3-flash",
  42 |      "heimdall:qwen/qwen3.8-27b",
  43 |      "local:gemma3:27b"
  44 |     ],
  45 | @@ -284,7 +279,6 @@
  46 |      "xai:grok-4.20-0309-reasoning",
  47 |      "anthropic:claude-opus-5-5",
  48 |      "heimdall:deepseek/deepseek-v4.1-flash",
  49 | -    "heimdall:z-ai/glm-5.3-flash",
  50 |      "heimdall:qwen/qwen3.8-27b",
  51 |      "local:gemma3:27b"
  52 |     ],
  53 | @@ -322,7 +316,6 @@
  54 |    },
  55 |    "heimdall_first": {
  56 |     "context_verdict": [
  57 | -    "heimdall:z-ai/glm-5.3-flash",
  58 |      "heimdall:deepseek/deepseek-v4.1-flash",
  59 |      "xai:grok-4.20-0309-reasoning"
  60 |     ],
  61 | @@ -331,42 +324,35 @@
  62 |      "heimdall:deepseek/deepseek-v4.1-flash"
  63 |     ],
  64 |     "fidelity_verdict": [
  65 | -    "heimdall:z-ai/glm-5.3-flash",
  66 |      "heimdall:qwen/qwen3.8-27b",
  67 |      "xai:grok-4.20-0309-reasoning"
  68 |     ],
  69 |     "exclusion_verdict": [
  70 | -    "heimdall:z-ai/glm-5.3-flash",
  71 |      "heimdall:deepseek/deepseek-v4.1-flash",
  72 |      "xai:grok-4.20-0309-reasoning"
  73 |     ],
  74 |     "speaker_verdict": [
  75 |      "xai:grok-4.20-0309-reasoning",
  76 |      "heimdall:deepseek/deepseek-v4.1-flash",
  77 | -    "heimdall:z-ai/glm-5.3-flash",
  78 |      "heimdall:qwen/qwen3.8-27b"
  79 |     ],
  80 |     "viewer_takeaway": [
  81 |      "xai:grok-4.20-0309-reasoning",
  82 |      "heimdall:deepseek/deepseek-v4.1-flash",
  83 | -    "heimdall:z-ai/glm-5.3-flash",
  84 |      "heimdall:qwen/qwen3.8-27b"
  85 |     ],
  86 |     "context_verdict:step_a_first": [
  87 | -    "heimdall:z-ai/glm-5.3-flash",
  88 |      "heimdall:deepseek/deepseek-v4.1-flash",
  89 |      "xai:grok-4.20-0309-reasoning"
  90 |     ],
  91 |     "context_verdict:step_a_second": [
  92 |      "xai:grok-4.20-0309-reasoning",
  93 |      "heimdall:deepseek/deepseek-v4.1-flash",
  94 | -    "heimdall:z-ai/glm-5.3-flash",
  95 |      "google:gemini-2.5-pro",
  96 |      "local_judge:gemma3:27b"
  97 |     ],
  98 |     "context_verdict:step_c": [
  99 |      "xai:grok-4.20-0309-reasoning",
 100 | -    "heimdall:z-ai/glm-5.3-flash",
 101 |      "heimdall:deepseek/deepseek-v4.1-flash"
 102 |     ],
 103 |     "coherence_verdict:hook": [
 104 | @@ -381,8 +367,7 @@
 105 |     ],
 106 |     "coherence_verdict:coherence": [
 107 |      "xai:grok-4.20-0309-reasoning",
 108 | -    "heimdall:deepseek/deepseek-v4.1-flash",
 109 | -    "heimdall:z-ai/glm-5.3-flash"
 110 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 111 |     ]
 112 |    },
 113 |    "plan_b": {
 114 | @@ -461,8 +446,7 @@
 115 |     ],
 116 |     "context_verdict:step_c": [
 117 |      "xai:grok-4.20-0309-reasoning",
 118 | -    "heimdall:deepseek/deepseek-v4.1-flash",
 119 | -    "heimdall:z-ai/glm-5.3-flash"
 120 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 121 |     ],
 122 |     "coherence_verdict:hook": [
 123 |      "xai:grok-4.20-0309-reasoning"
 124 | @@ -476,6 +460,7 @@
 125 |    "ruling_115": "RULING 115 (orchestrator 13:24 ET Nov 15), amending 85 / 88 / 96 for the HOOK only: the hook job is asked ALONE (one candidate a call) at production's seed by GROK, and Grok alone, in every routing (heimdall_first, today, plan_b): the calibrated floors (pipeline/hook_calibration.json, hook_bar.py) are Grok's, so no other model may decide a hook while Grok is out (no rating = no hook, law L-m). qwen answers every hook in SHADOW (recorded, never deciding; proof_ledger: shadow 'coherence_verdict:hook'). A hook passes when each of scroll / alone / setup is at least its floor.",
 126 |    "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement.",
 127 |    "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and after ruling 96's deepseek, which stays second (glm agreed with Grok on 94 % of the replay's coherence decisions, with one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here; in Plan B mode the router already reads Plan B's coherence list, Grok -> Gemini -> OpenAI -> Anthropic), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. NOT CHANGED: the coherence role's default list (Grok -> deepseek), which the spotlight's closing-line and the medley's takeaway value verdicts use: the replay has no data for them (the orchestrator is asked, STATE 06:14, question B). Every other list is ruling 96's, unchanged.",
 128 | -  "ruling_102": "RULING 102 (orchestrator 13:02 ET Nov 14): STEP_A_UNAVAILABLE MUST NEVER END A CLIP. Step A's second family, in order: Heimdall deepseek (its own deadline, ruling 100) -> Heimdall glm -> GEMINI through the fenced key -> the local gemma3:27b on GPU0 through the integrator's judge service (ruling 87's last resort, recorded as such on the pin and on STATE line 1). Grok stays first (ruling 88 (c): Grok confirms a Heimdall pass); the second verdict is still off the first verdict's vendor and family. The first leg that ANSWERS gives the second verdict; an unavailable leg moves on at once, it is never a refusal and never cached. Only if no leg answers is the clip held for THIS build (STEP_A_HELD, not refused), and retried next build."
 129 | +  "ruling_102": "RULING 102 (orchestrator 13:02 ET Nov 14): STEP_A_UNAVAILABLE MUST NEVER END A CLIP. Step A's second family, in order: Heimdall deepseek (its own deadline, ruling 100) -> Heimdall glm -> GEMINI through the fenced key -> the local gemma3:27b on GPU0 through the integrator's judge service (ruling 87's last resort, recorded as such on the pin and on STATE line 1). Grok stays first (ruling 88 (c): Grok confirms a Heimdall pass); the second verdict is still off the first verdict's vendor and family. The first leg that ANSWERS gives the second verdict; an unavailable leg moves on at once, it is never a refusal and never cached. Only if no leg answers is the clip held for THIS build (STEP_A_HELD, not refused), and retried next build.",
 130 | +  "ruling_119": "RULING 119 (3) (orchestrator 08:25 ET Nov 16): glm-5.3-flash is overloaded on the gateway (the Heimdall team confirmed a worker shortage): OUT OF EVERY CHAIN until the orchestrator says; each list closes up, so the next member takes glm's place (no model is added: qwen stays struck from step A by the 06:12 Nov 14 rulings, and ruling 96's other lists are kept as they stand). A held moment moves to the next member at once inside the router (a missed deadline or an open breaker is never a refusal); step A's first screen is now deepseek -> Grok."
 131 |   }
 132 |  }
 133 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
 134 | index 091079d..8364c0a 100644
 135 | --- a/tests/package/test_ledger_build.py
 136 | +++ b/tests/package/test_ledger_build.py
 137 | @@ -816,13 +816,14 @@ class TestDriverRefuses(unittest.TestCase):
 138 |                           before)
 139 |  
 140 |      def test_ruling_82_the_context_verdict_chain(self):
 141 | -        """RULING 82 (20:02 Nov 13): with the frozen legs out, step A's chain is xAI first, then the three Heimdall
 142 | -        models in the ruled order; glm-5.3-flash is a Heimdall back-end of its own family."""
 143 | +        """RULING 82 (20:02 Nov 13): with the frozen legs out, step A's chain is xAI first, then the Heimdall models in
 144 | +        the ruled order; RULING 119 (08:25 Nov 16): glm out of every chain, the list closes up. glm-5.3-flash stays a
 145 | +        Heimdall back-end of its own family (the orchestrator may put it back)."""
 146 |          sys.path.insert(0, HERE)
 147 |          import proof_ly as PL
 148 |          self.assertEqual(PL.chains()["context_verdict"], ["xai:grok-4.20-0309-reasoning",
 149 |                                                            "heimdall:deepseek/deepseek-v4.1-flash",
 150 | -                                                          "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b"])
 151 | +                                                          "heimdall:qwen/qwen3.8-27b"])
 152 |          with open(os.path.join(REPO, "pipeline", "model_providers.json")) as f:
 153 |              glm = json.load(f)["backends"]["heimdall:z-ai/glm-5.3-flash"]
 154 |          self.assertEqual((glm["vendor"], glm["family"], glm["model"]), ("heimdall", "glm", "z-ai/glm-5.3-flash"))
 155 | @@ -927,26 +928,28 @@ class TestRuling85NoXai(unittest.TestCase):
 156 |  
 157 |      def test_ruling_96s_lists_and_xai_answering_nothing(self):
 158 |          """RULING 96 (01:40 ET Nov 14), final until re-measured, on ruling 88's structure, as the orchestrator's 06:12
 159 | -        rulings amend it: (1) glm last for coherence, no Heimdall model for clips-alone; (2) qwen struck from step A."""
 160 | +        rulings amend it: (1) glm last for coherence, no Heimdall model for clips-alone; (2) qwen struck from step A.
 161 | +        RULING 119 (08:25 ET Nov 16): glm out of EVERY chain (overloaded), each list closing up; nothing is added."""
 162 |          PL = self.pl()
 163 |          X, DS, G, Q = ("xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash",
 164 |                         "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b")
 165 |          GEM = "google:gemini-2.5-pro"
 166 |          ch = PL.chains("heimdall_first")
 167 | -        self.assertEqual(ch["fidelity_verdict"], [G, Q, X])                       # 96: glm -> qwen -> Grok
 168 | -        self.assertEqual(ch["exclusion_verdict"], [G, DS, X])                      # 96: glm -> deepseek -> Grok
 169 | -        self.assertEqual(ch["context_verdict:step_a_first"], [G, DS, X])           # 06:12 (2): glm -> deepseek, no qwen
 170 | -        self.assertEqual(ch["context_verdict:step_a_second"], [X, DS, G, GEM, "local_judge:gemma3:27b"])   # (c) Grok
 171 | -        #   confirms; RULING 102 (13:02 Nov 14): then deepseek, glm, Gemini, the local judge (ruling 87's last resort)
 172 | -        self.assertEqual(ch["context_verdict"], [G, DS, X])                        # the role's default: no qwen either
 173 | +        self.assertEqual(ch["fidelity_verdict"], [Q, X])                          # 96 without glm: qwen -> Grok
 174 | +        self.assertEqual(ch["exclusion_verdict"], [DS, X])                         # 96 without glm: deepseek -> Grok
 175 | +        self.assertEqual(ch["context_verdict:step_a_first"], [DS, X])              # 06:12 (2) without glm; no qwen
 176 | +        self.assertEqual(ch["context_verdict:step_a_second"], [X, DS, GEM, "local_judge:gemma3:27b"])   # (c) Grok
 177 | +        #   confirms; RULING 102 (13:02 Nov 14): then deepseek, Gemini, the local judge (ruling 87's last resort)
 178 | +        self.assertEqual(ch["context_verdict"], [DS, X])                           # the role's default: no qwen either
 179 | +        self.assertNotIn(G, [b for v in list(ch.values()) + list(PL.chains("today").values()) for b in v])   # 119
 180 |          self.assertNotIn(Q, [b for k, v in ch.items() if k.startswith("context_verdict:step_a") for b in v])
 181 |          self.assertEqual(ch["coherence_verdict:hook"], [X])                        # RULING 115 (amends 88 (b) / 96 for
 182 |          #   the hook): Grok ALONE, the rater the calibrated floors are measured on (qwen in shadow, never deciding)
 183 | -        self.assertEqual(ch["context_verdict:step_c"], [X, G, DS])                 # (b) / (e): no qwen
 184 | -        self.assertEqual(ch["coherence_verdict:coherence"], [X, DS, G])           # 06:12 (1): glm the LAST fallback
 185 | +        self.assertEqual(ch["context_verdict:step_c"], [X, DS])                    # (b) / (e): no qwen; 119: no glm
 186 | +        self.assertEqual(ch["coherence_verdict:coherence"], [X, DS])              # 06:12 (1)'s last fallback glm: out
 187 |          self.assertEqual(ch["coherence_verdict:clips_alone"], [X, GEM])           # 06:12 (1): no Heimdall model
 188 |          today = PL.chains("today")                                                 # (d) and (e) hold today too
 189 | -        self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS, G]))
 190 | +        self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS]))
 191 |          self.assertEqual((today["coherence_verdict:hook"], PL.plan_b_chains()["coherence_verdict:hook"]), ([X], [X]))
 192 |          #   RULING 115: the hook is Grok's alone in every routing (no uncalibrated rating is ever cached as a hook's)
 193 |          r = PL.P.Router(env_path="/nonexistent", routing="heimdall_first", chains=ch)
 194 | @@ -957,24 +960,22 @@ class TestRuling85NoXai(unittest.TestCase):
 195 |              ("fidelity_verdict", None), ("exclusion_verdict", None), ("speaker_verdict", None),
 196 |              ("viewer_takeaway", None), ("context_verdict", "step_c"), ("coherence_verdict", "hook"),
 197 |              ("coherence_verdict", "clips_alone"), ("coherence_verdict", "coherence"))}
 198 | -        self.assertEqual(got, {("fidelity_verdict", None): G, ("exclusion_verdict", None): G,
 199 | -                               ("speaker_verdict", None): G, ("viewer_takeaway", None): G,
 200 | -                               ("context_verdict", "step_c"): G, ("coherence_verdict", "hook"): None,   # ruling 115:
 201 | -                               #   no other model decides a hook while Grok is out (no rating = no hook, law L-m)
 202 | +        self.assertEqual(got, {("fidelity_verdict", None): Q, ("exclusion_verdict", None): None,   # RULING 119: glm
 203 | +                               ("speaker_verdict", None): Q, ("viewer_takeaway", None): Q,         # out, deepseek
 204 | +                               ("context_verdict", "step_c"): None, ("coherence_verdict", "hook"): None,   # writes,
 205 | +                               #   Grok is down: no leg is a fail-closed no verdict (law L-m), never another model
 206 |                                 ("coherence_verdict", "clips_alone"): GEM,          # Plan B's other outside family
 207 | -                               ("coherence_verdict", "coherence"): G})            # the gap is closed: glm, last
 208 | +                               ("coherence_verdict", "coherence"): None})         # glm, its last fallback, is out
 209 |          r.down[GEM] = "Gemini answers nothing (the test)"
 210 |          self.assertIsNone(self.pick(r, "coherence_verdict", {w.vendor}, {w.family}, kind="clips_alone"))   # closed
 211 | -        r.down[G] = "glm answers nothing (the test)"
 212 | -        self.assertIsNone(self.pick(r, "coherence_verdict", {w.vendor}, {w.family}, kind="coherence"))     # closed
 213 | -        del r.down[G], r.down[GEM]
 214 | +        del r.down[GEM]
 215 | +        self.assertIsNone(self.pick(r, "context_verdict", {w.vendor}, {w.family}, kind="step_a_first"))   # held
 216 | +        #   (ruling 102): deepseek writes and Grok is down, so step A's first screen has no leg for THIS build
 217 | +        r.down.clear()
 218 |          first = self.pick(r, "context_verdict", {w.vendor}, {w.family}, kind="step_a_first")
 219 |          fb = r.backends[first]
 220 |          second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
 221 | -        self.assertEqual((first, second), (G, DS))                                 # two Heimdall families, Grok down
 222 | -        r.down.clear()
 223 | -        second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
 224 | -        self.assertEqual(second, X)                                                # (c): Grok confirms when it answers
 225 | +        self.assertEqual((first, second), (X, DS))                                 # Grok's first, deepseek's off it
 226 |  
 227 |  if __name__ == "__main__":
 228 |      unittest.main()
 229 | 
```

---

pp-selectid: RULING 119 (3) (orchestrator 08:25 ET Nov 16): glm out of every chain. Files: pipeline/model_providers.json
(the chains; one note), tests/package/test_ledger_build.py (the two tests that pin the lists).

THE ORDER, verbatim: "(3) glm-5.3-flash is overloaded on the gateway (the Heimdall team confirmed a worker shortage) and held
a moment at step A's first screen twice this morning: take glm out of every chain until I say; the next healthy member takes
its place. A held moment is retried on the next member at once, not after the breaker."

THE CHANGE: heimdall:z-ai/glm-5.3-flash is removed from EVERY chain in the config (16 lists: the roles' default chains and
the heimdall_first / today routing lists); each list closes up, so the next member takes glm's place. NOTHING IS ADDED:
qwen stays struck from step A (the orchestrator's 06:12 Nov 14 rulings: "QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43
refusals let through)"), and ruling 96's other lists stand as they are without glm. The back-end's own definition stays
(the orchestrator may put it back). Lists after the change (heimdall_first): step A's first screen deepseek -> Grok; step
A's second Grok -> deepseek -> Gemini -> the local judge; context_verdict deepseek -> Grok; fidelity qwen -> Grok;
exclusion deepseek -> Grok; speaker and viewer_takeaway Grok -> deepseek -> qwen; step C Grok -> deepseek; coherence Grok
-> deepseek; today's step C Grok -> deepseek.

"RETRIED ON THE NEXT MEMBER AT ONCE": unchanged code already does it: Router.call moves to the chain's next member at once
when one misses its deadline, is breaker-open (Router._skip / breaker_open) or answers out of contract
(providers.call_parsed); ruling 102 holds a moment only when no member answers. The moment held this morning
(c03abcbc, builds 39-40) was held because glm missed its deadline, deepseek is the writer's family (skipped by L-x), and
Grok's step-A upper bound ($0.83) does not fit the day's dollar left (ruling 118's cap: SpendLimit, recorded in its
package). After this change, while deepseek writes and the day's dollar is short, step A's first screen still holds new
moments (deepseek skipped, Grok capped): that is stated, not hidden; the free panel (ruling 118) is the fix for it.

UNCHANGED GUARDS (not in the diff): providers.Router._skip (pipeline/providers.py, "def _skip": the writer's vendor /
family); Router.call's failover; package.prescreen's ruling-102 hold (pipeline/package.py "def held_why" / "def
is_held"); ruling 118's cap (Router._reserve).

TESTS: test_ledger_build test_ruling_82_the_context_verdict_chain (the 'today' context chain Grok -> deepseek -> qwen) and
test_ruling_96s_lists_and_xai_answering_nothing (every heimdall_first and today list as above; glm in NO list; with Grok down
and deepseek writing, the router's own picks: fidelity, speaker, takeaway -> qwen; exclusion, step C, the hook, coherence ->
no leg (fail closed); clips-alone -> Gemini; step A's first screen -> no leg (held); with Grok up: Grok first, deepseek
second off it). Mutations C1-C3 (glm back in step A's first screen; qwen put in glm's place in step A; glm back first for
fidelity) after a control run. All suite files.

PLEASE CHECK: (1) that glm is in no chain and nothing was added; (2) that no list breaks a standing ruling (06:12: no qwen
in step A; 96; 102; 115: the hook Grok alone); (3) the tests.


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
