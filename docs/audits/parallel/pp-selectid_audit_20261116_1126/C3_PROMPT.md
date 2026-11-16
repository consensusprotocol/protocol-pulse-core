# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1126
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 115 s finish=stop usage in 10865 / out 1851 usd_reported=0.000566 usd~0.060 (upper-bound price)

Since this is my second review and I have analyzed the Cycle 1 outputs from Gemma and Qwen, as well as the final fixed diff, here is my final audit.

### 1. WHAT DID THEY CATCH THAT I MISSED?
The other models were highly aligned. Qwen specifically highlighted the critical distinction between `upper_usd` (used for the spend guard reserve) and `prompt_usd` (used for booking abandoned calls), ensuring that the "over-count" logic of Ruling 121 does not accidentally inflate actual billing or reported costs. I agree that this separation is a key safety requirement.

### 2. WHERE DO I AGREE OR DISAGREE?
*   **Reserve Arithmetic:** I agree with both models. The use of `-(-a // b)` for `ceil(chars / 3)` is the correct Pythonic way to handle integer ceiling division.
*   **xAI Output Cap:** I agree. The logic in `XAIBackend.max_out` correctly implements the `max_out_cap` from `model_providers.json`, and the test `test_grok_is_sent_the_capped_output` proves this value is actually passed to the API.
*   **Historical Verification:** I agree. The test `test_no_recorded_grok_step_a_call_cost_more_than_its_reserve` directly satisfies the ruling's requirement to check against the 438 recorded calls and reports the tightest margin.
*   **Vision Prompting:** I agree with the update to `test_visual_pin.py`. Because `upper_usd` now applies a `RESERVE_MARGIN` (1.25), the difference in cost between a text and vision prompt must also be multiplied by 1.25.

### 3. NEW FINDINGS FROM THIS REVIEW
No new defects found. The combined analysis confirms that the implementation is mathematically precise and adheres to the "fail-closed" requirement of the spend guard (if the reserve cannot be secured, the call is refused before execution).

### 4. REVISED SCORES
| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| Reserve Logic | 10/10 | 10/10 | No change; implementation is correct. |
| xAI Cap | 10/10 | 10/10 | No change; cap is correctly applied and tested. |
| Regression/Tests | 10/10 | 10/10 | No change; historical and unit tests are robust. |

### 5. FINAL PRIORITY LIST
No changes required.

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
The implementation of `XAIBackend.max_out` capping at 12,000 tokens is the most critical change, as it prevents the $8\times$ reasoning multiplier from creating reserves that would block almost all calls within a $1.00 daily budget.

### 7. PRODUCTION READY?
Yes.

P1_OR_WORSE: 0

## MIMO-V2.6-FLASH-RL — CYCLE 1 OUTPUT
# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 195 s finish=stop usage in 10005 / out 18667 usd_reported=0.002055 usd~0.310 (upper-bound price)

# CYCLE 2 REVIEW — pp-selectid-20261116_1126

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

Both Gemma and Qwen found zero defects, matching my Cycle 1 assessment. Nothing material was missed. Two details they surfaced that I want to explicitly confirm:

- **Qwen's check (2)** — that `upper_usd` is never read as a strict billing bound elsewhere — was the most valuable cross-check. I verified: `upper_usd` feeds only `Router._reserve` (providers.py:1366, unchanged); `prompt_usd` (ruling 83a) and `prompt_tokens_upper` (ruling 107 Q1 reported-rate estimate) remain separate paths. The separation is intact.
- **Claude's consensus** flagged the `test_visual_pin.py` ruling-70 test re-sizing (the ×1.25 now applies to the per-image delta) and the correction that the 4 over-cap calls were one Nov 12 + three Nov 13. I verified both in the diff (lines 77–84 and 198–200).

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| Gemma: reserve arithmetic correct | **Agree** | `-(-a // b)` is exact ceiling division for positive ints; `ceil(chars/3) + 200 + 6000·n_img` matches the ruling verbatim. |
| Gemma: xAI cap reaches the request | **Agree** | `max_out` returns `min(n, 12000)`; `complete` sends `self.max_out(max_tokens)` (providers.py:475, unchanged); test asserts 12,000 in the body. |
| Qwen: nothing else reads `upper_usd` as strict bound | **Agree** | Only `_reserve` consumes it; `prompt_usd` and `prompt_tokens_upper` are separate. |
| Qwen: tests pass logic check | **Agree** | I hand-verified every arithmetic assertion (see §3). |
| Claude: `test_visual_pin.py` re-sized correctly | **Agree** | `1.25 × 6000 = 7500` matches the new `upper_usd` delta; the second assertion pins `prompt_tokens_reserve` delta at exactly 6,000. |
| Claude: 4 over-cap calls dated correctly | **Agree** | Test asserts `len(cut) == 4` and all `recorded_at < "2026-11-14"`. |

No disagreements.

## 3. NEW FINDINGS FROM THIS REVIEW

I hand-verified every numeric assertion in the diff. All check out:

**Reserve arithmetic (test_providers.py:150–158):**
- `max_out(4000)` → `min(max(8000, 32000), 12000)` = 12,000 ✓
- `max_out(1200)` → `min(max(8000, 9600), 12000)` = 9,600 ✓
- `max_out(750)` → `min(max(8000, 6000), 12000)` = 8,000 ✓
- `upper_usd("p"×7800, 4000)` = `1.25 × (2800×5e-6 + 12000×25e-6)` = 0.3925 ✓
- `upper_usd("p"×7801, 4000, system="s")` = `1.25 × (2801×5e-6 + 12000×25e-6)` = 0.392506 ✓ (7802/3 = 2600.67 → ceil 2601)

**Guard test re-sizes:**
- Test 1 (line 96): `1.25 × (50200×10e-6 + 2000×100e-6)` = 0.8775; 39.5 + 0.8775 = 40.3775 > 40 ✓
- Test 2 (line 107): reserve for `"p"` = `1.25 × (201×10e-6 + 2000×100e-6)` = 0.2525; 0.95 + 0.2525 = 1.2025 > 1.00 ✓; limit raised to 1.25 → fits ✓
- Test 3 (line 119): `1.25 × (400200×10e-6 + 2000×100e-6)` = 5.2525; 8.00 + 5.2525 = 13.2525 > 10 ✓

**Vision test (test_visual_pin.py:78–84):**
- `upper_usd` delta = `1.25 × 6000` = 7500 ✓ (price $1/token)
- `prompt_tokens_reserve` delta = 6000 ✓

**Step-A fit test (line 202–218):**
- Capped: reserve = 0.3925; 0.5835 + 0.3925 = 0.976 < 1.00 → runs ✓
- Uncapped: reserve = 1.0175; 0.5835 + 1.0175 = 1.601 > 1.00 → refused ✓
- Ledger is shared across iterations, but the second iteration expects refusal regardless (reserve alone exceeds $1.00), so correctness holds.

**New P3 findings (none rise above nit):**

- **[P3]** `test_a_step_a_call_fits_what_the_day_has_left` (test_providers.py:205–218) shares the ledger file between the two loop iterations. After the first (successful) call, the ledger gains the mocked call's cost (~$0.02), so the second iteration's spent is $0.6035 rather than $0.5835. The test still passes for the right reason (reserve alone exceeds $1.00), but resetting the ledger between iterations would make the test's intent unambiguous.
- **[P3]** `prompt_tokens_upper` (providers.py:201) and `prompt_tokens_reserve` (providers.py:205) are near-identical names serving different purposes (abandoned-call booking vs. spend-guard reserve). A future reader could confuse them. Consider a comment on `prompt_tokens_upper` explicitly saying "NOT the reserve — see prompt_tokens_reserve."

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Reserve arithmetic (`prompt_tokens_reserve`, `upper_usd`) | Correct | Correct | Hand-verified every numeric assertion; no change. |
| xAI output cap (`max_out`, `model_providers.json`) | Correct | Correct | Confirmed cap reaches API body; no change. |
| `upper_usd` isolation (not read as strict bound) | Correct | Correct | Qwen's cross-check confirmed; no change. |
| Tests (4 new + 3 re-sized + 1 visual) | Correct | Correct | All arithmetic verified by hand; no change. |
| Docstrings / comments | Correct | Correct | `_reserve` docstring and constants' comments accurately describe the new behavior. |

No score chan

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 40 s finish=stop usage in 10258 / out 3006 usd_reported=0.002620 usd~0.076 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1126
# Reviewer: Heimdall (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the core arithmetic and the xAI cap logic. However, reviewing the other models' outputs and re-examining the diff with fresh eyes, I missed two specific nuances:

1.  **The "Strict Bound" Misconception (Qwen's Point 3):** Qwen explicitly analyzed whether `upper_usd` was being used as a *billing* figure elsewhere. I assumed the separation between `prompt_usd` (abandoned calls) and `upper_usd` (reserves) was obvious from the docstrings, but I did not explicitly verify that no *other* consumer (e.g., reporting dashboards, external APIs) treats `upper_usd` as a hard cost ceiling. Qwen confirmed this separation is maintained.
2.  **The Vision Test Resizing (Gemma's Point 5 & Consensus Note):** The consensus note highlighted that `test_visual_pin.py` was updated to account for the `1.25` margin. In Cycle 1, I focused heavily on `test_providers.py` and the new `TestRuling121Reserve` class. I missed that the *existing* vision test (`test_the_upper_bound_counts_each_image`) had to be modified because `upper_usd` now includes the margin. The diff shows this change (lines 78-84), and it is correct, but I failed to flag it as a critical regression check in my initial scan.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Gemma-4-31B-IT:** **Agree.** Gemma correctly identified that the implementation is mathematically sound and adheres to Ruling 121. Its point about the `ceil(chars/3)` logic using `-(-a // b)` is accurate. It correctly noted that the xAI cap prevents the $0.80 reserve issue.
*   **Qwen3.8-27B:** **Agree.** Qwen's analysis of the "strict bound" question is the most thorough. It correctly identified that `upper_usd` is a *reserve* (over-estimate) and not a *bill*. Its verification of the `max_out` logic (`min(max(8000, 8*max_tokens), 12000)`) is correct.
*   **Claude's Consensus:** **Agree.** The consensus correctly identified the correction regarding the dates of the 4 recorded calls (Nov 12/13, not all Nov 12). It also correctly noted that `prompt_tokens_upper` remains for abandoned calls, which is a crucial distinction.

**Disagreement:** None. All models converged on the same conclusion: the code is correct.

## 3. NEW FINDINGS FROM THIS REVIEW

Upon re-reading the diff with the context of the other models' reviews, I found one subtle interaction that warrants explicit confirmation:

*   **[P2] Interaction between `RESERVE_MARGIN` and `IMAGE_TOKENS_UPPER`:**
    In `Backend.upper_usd` (line 46-47), the margin is applied to the *total* USD calculation: `round(RESERVE_MARGIN * self.usd({...}), 6)`.
    In `test_visual_pin.py` (line 82), the test asserts: `one - b.upper_usd("t", 0) == P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER`.
    This is correct *only if* the base prompt cost is negligible or if the test is checking the *delta*. Let's verify the math:
    `upper_usd(vision)` = `1.25 * (usd(in: ceil(1/3)+200+6000, out: max_out(0)))`
    `upper_usd(text)` = `1.25 * (usd(in: ceil(1/3)+200, out: max_out(0)))`
    Difference = `1.25 * (usd(in: 6000, out: 0))` = `1.25 * (6000 * price_in)`.
    The test uses `price=(1e6, 0)`, so `price_in = 1e-6` ($1 per token).
    Difference = `1.25 * (6000 * 1e-6)` = `1.25 * 0.006` = `0.0075`.
    The test asserts `P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER`. Wait. `P.IMAGE_TOKENS_UPPER` is 6000. `1.25 * 6000` is 7500.
    **CRITICAL CHECK:** The test on line 82 says:
    `self.assertEqual(one - b.upper_usd("t", 0), P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER)`
    If `one` and `b.upper_usd("t", 0)` are in **USD**, then the LHS is ~$0.0075.
    The RHS is `1.25 * 6000` = `7500`.
    **This test would FAIL.**
    
    Let's re-read the test setup: `b = Fake("x:y", "openai", price=(1e6, 0))`.
    `Fake` likely returns USD.
    `P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER` is `1.25 * 6000`. This is a **token count** multiplied by a margin, not a USD value.
    
    **Is this a bug in the test?**
    Line 82: `self.assertEqual(one - b.upper_usd("t", 0), P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER)`
    If `one` is USD, this comparison is comparing USD to Tokens.
    
    Let's look at line 83-84:
    `self.assertEqual(P.Backend.prompt_tokens_reserve({"text": "t", "images": ["a"]}) - P.Backend.prompt_tokens_reserve("t"), P.IMAGE_TOKENS_UPPER)`
    This compares **tokens** to **tokens**. This is correct.
    
    So, line 82 is comparing **USD** to **Tokens**?
    Unless `Fake`'s `upper_usd` returns something else? No, `upper_usd` returns `round(..., 6)`, which is USD.
    
    **Wait, let's look at the `Fake` class definition (not in diff, but implied).**
    If `price=(1e6, 0)`, that means $1,000,000 per 1M tokens? Or $1 per token?
    Usually, prices are per 1M tokens. If `price=(1e6, 0

## CLAUDE'S CYCLE 1 CONSENSUS
# C2 CONSENSUS — pp-selectid audit 20261116_1126 (RULING 121 (1): the reserve and the xAI output cap)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: qwen 0,
gemma 0, mimo 0. The whole audit $0.0129 of Heimdall, not capped. No P1 in either cycle. CLEARED.
On dev43: all 40 suite files pass; mutations R1-R7 after a control run: 7 of 7 killed. It lands on the 11:41 ET default
of the STATE question (APPLY, audit-first) unless the orchestrator answers otherwise; FINAL.diff at landing.

AFTER CYCLE 2, A REAL DEFECT (found at landing, 11:47 ET): tests/providers/test_reserve_wait.py sized its scenarios with
U = the OLD bound of the Fake's one-character call ($0.10201); under ruling 121's reserve it is 1.25 x that ($0.12751), so
its four tests (six workers with room for four, ...) failed: the threads never got their room. My suite loop read only
pytest's LAST output line, which was a thread traceback, so it reported no failing file (the total, 831 not 835, gave it
away). FIX: U is now the Fake's reserve as the code computes it (Fake.upper_usd("p", 1000)); the four pass. The suite
runner now judges every file by pytest's exit code. Cycle 3 checks this fix (DEFECT).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_1126/C3_STEP.diff (237 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 061a9f0..980c289 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -54,7 +54,8 @@
   6 |     ],
   7 |     "temperature": 0,
   8 |     "key_name": "XAI_API_KEY_MEDLEY",
   9 | -   "family": "grok"
  10 | +   "family": "grok",
  11 | +   "max_out_cap": 12000
  12 |    },
  13 |    "heimdall:qwen/qwen3.8-27b": {
  14 |     "vendor": "heimdall",
  15 | diff --git a/pipeline/providers.py b/pipeline/providers.py
  16 | index 2e84551..a70cdb5 100644
  17 | --- a/pipeline/providers.py
  18 | +++ b/pipeline/providers.py
  19 | @@ -68,6 +68,10 @@ class ReplayMiss(Exception):
  20 |  
  21 |  
  22 |  IMAGE_TOKENS_UPPER = 6000            # ruling 70: one image's input tokens, as the spend guard's upper bound
  23 | +RESERVE_CHARS_PER_TOKEN = 3          # RULING 121 (1) (orchestrator 11:25 ET Nov 16): the reserve counts a prompt's tokens
  24 | +RESERVE_MARGIN = 1.25                # as its characters / 3 (a deliberate over-count; English runs near 4), at list
  25 | +#   price, with the output cap the call is really sent (max_out), times 1.25; checked against every recorded Grok step-A
  26 | +#   call: no reported cost beats it (tests/providers TestRuling121Reserve)
  27 |  RATE_MIN_REPORTED = 3                # RULING 107 Q1 (orchestrator 20:40 ET Nov 14): an abandoned call is booked at
  28 |                                       # the model's own reported rate once it has this many reported calls
  29 |  RESERVE_POLL_S = 1.0                 # BATCH 3 (Nov 14): how often a call waiting for room under the limit re-reads
  30 | @@ -197,9 +201,18 @@ class Backend:
  31 |          n_img, text = (len(prompt["images"]), prompt["text"]) if is_vision(prompt) else (0, prompt)
  32 |          return len(text) + len(system or "") + 200 + IMAGE_TOKENS_UPPER * n_img
  33 |  
  34 | +    @staticmethod
  35 | +    def prompt_tokens_reserve(prompt, system=None):
  36 | +        """RULING 121 (1): a prompt's input tokens for the spend guard's reserve: its characters / RESERVE_CHARS_PER_TOKEN,
  37 | +        rounded up, + 200 for the message frame, IMAGE_TOKENS_UPPER per image of a vision prompt."""
  38 | +        n_img, text = (len(prompt["images"]), prompt["text"]) if is_vision(prompt) else (0, prompt)
  39 | +        return -(-(len(text) + len(system or "")) // RESERVE_CHARS_PER_TOKEN) + 200 + IMAGE_TOKENS_UPPER * n_img
  40 | +
  41 |      def upper_usd(self, prompt, max_tokens, system=None):
  42 | -        """The call's spend upper bound: its prompt tokens (prompt_tokens_upper) + the output cap."""
  43 | -        return self.usd({"in": self.prompt_tokens_upper(prompt, system), "out": self.max_out(max_tokens)})
  44 | +        """The spend guard's reserve for one call (RULING 121 (1)): its prompt tokens (prompt_tokens_reserve) and the
  45 | +        output cap it is really sent (max_out), at list price, times RESERVE_MARGIN."""
  46 | +        return round(RESERVE_MARGIN * self.usd({"in": self.prompt_tokens_reserve(prompt, system),
  47 | +                                                "out": self.max_out(max_tokens)}), 6)
  48 |  
  49 |      def prompt_usd(self, prompt, system=None):
  50 |          """RULING 83 (a) (orchestrator 20:33 Nov 13): what a call abandoned at its deadline is booked at: its PROMPT
  51 | @@ -453,7 +466,9 @@ class XAIBackend(Backend):
  52 |      SYSTEM = "You have no tools and no internet access. Answer in ONE message containing only the JSON object asked for."
  53 |  
  54 |      def max_out(self, max_tokens):
  55 | -        return max(int(self.spec.get("min_out", 8000)), max_tokens * 8)       # a reasoning model thinks inside it
  56 | +        n = max(int(self.spec.get("min_out", 8000)), max_tokens * 8)          # a reasoning model thinks inside it
  57 | +        cap = self.spec.get("max_out_cap")    # RULING 121: the most output it is sent, whatever the role asks (12,000:
  58 | +        return min(n, int(cap)) if cap else n  # step A's 4,000 x 8 was 32,000 and reserved $0.80 of Grok output alone)
  59 |  
  60 |      def complete(self, prompt, max_tokens, seed, system=None):
  61 |          key = self.key(self.spec.get("key_name", "XAI_API_KEY_MEDLEY"))
  62 | @@ -914,7 +929,9 @@ class Router:
  63 |      def _reserve(self, b, upper):
  64 |          """Reserve a paid call's upper bound -> a reservation key (None for a free back-end or no ledger); raises
  65 |          SpendLimit when spent (on the limit basis) + reserved + this call's upper bound would pass the limit. The
  66 | -        reservations stay price-table upper bounds whatever the basis: the guard can only stop early, never late.
  67 | +        reservations stay at list price whatever the basis; since RULING 121 (1) each is the call's reserve
  68 | +        (upper_usd: characters / 3 as its prompt tokens, its real output cap, x 1.25), checked against every recorded
  69 | +        Grok step-A call rather than counted from above.
  70 |          With reserve_wait_s > 0 (a batch build's opt-in; the default 0 keeps the refusal at once that every other
  71 |          caller, the render's among them, relies on): when spent + this call's upper bound fits and only the reservations
  72 |          of calls IN FLIGHT stand in the way, the call waits for them to settle (each ends in an answer, an error or an
  73 | diff --git a/tests/package/test_visual_pin.py b/tests/package/test_visual_pin.py
  74 | index 708919f..721f175 100644
  75 | --- a/tests/package/test_visual_pin.py
  76 | +++ b/tests/package/test_visual_pin.py
  77 | @@ -231,7 +231,9 @@ class TestVisionPrompt(unittest.TestCase):
  78 |      def test_the_upper_bound_counts_each_image(self):
  79 |          b = Fake("x:y", "openai", price=(1e6, 0))                             # $1 per input token
  80 |          one = b.upper_usd({"text": "t", "images": ["a"]}, 0)
  81 | -        self.assertEqual(one - b.upper_usd("t", 0), P.IMAGE_TOKENS_UPPER)
  82 | +        self.assertEqual(one - b.upper_usd("t", 0), P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER)   # ruling 121: x 1.25
  83 | +        self.assertEqual(P.Backend.prompt_tokens_reserve({"text": "t", "images": ["a"]}) -
  84 | +                         P.Backend.prompt_tokens_reserve("t"), P.IMAGE_TOKENS_UPPER)         # each image: 6,000 tokens
  85 |  
  86 |      def test_the_heimdall_and_xai_vision_bodies(self):
  87 |          sent = []
  88 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
  89 | index 8eef714..b41e97b 100644
  90 | --- a/tests/providers/test_providers.py
  91 | +++ b/tests/providers/test_providers.py
  92 | @@ -368,8 +368,8 @@ class TestRouter(unittest.TestCase):
  93 |                         "usd_reported": 3.46, "usd_unreported_estimate": 1.81}, open(led, "w"))
  94 |              a = Fake("openai:x", "openai", answer="{}", usage={"in": 1000, "out": 100})        # no vendor figure
  95 |              rep = Fake("openai:y", "openai", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.001})
  96 | -            p = "p" * 50_000
  97 | -            with self.assertRaises(P.SpendLimit):                   # the old basis: 39.5 + the upper bound > 40
  98 | +            p = "p" * 150_000                                       # ruling 121's reserve: 1.25 x (50,200 x $10/M +
  99 | +            with self.assertRaises(P.SpendLimit):                   # 2,000 x $100/M) = $0.88; old basis: 39.5 + it > 40
 100 |                  router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_usd=40).call("write", p)
 101 |              r = router(d, [a, rep], {"write": ["openai:x"], "judge": ["openai:y"]}, spend_path=led, limit_usd=12,
 102 |                         limit_basis="reported")
 103 | @@ -410,9 +410,9 @@ class TestRouter(unittest.TestCase):
 104 |              self.assertAlmostEqual(led_["by_backend"]["heimdall:q"]["usd_reported"], 4.5, places=6)   # recorded
 105 |              self.assertAlmostEqual(r.spent(), 0.95, places=6)                                        # never counted
 106 |              with self.assertRaises(P.SpendLimit):
 107 | -                r.call("judge", "p")                                   # 0.95 + its upper bound ($0.20) > $1.00
 108 | +                r.call("judge", "p")                    # 0.95 + its reserve ($0.25: ruling 121's x 1.25) > $1.00
 109 |              self.assertEqual((h.calls, x.calls, json.load(open(led))["reserved"]), (1, 0, {}))
 110 | -            r.limit_usd = 1.20
 111 | +            r.limit_usd = 1.25
 112 |              r.call("judge", "p")                                       # it fits under a higher cap: counted
 113 |              self.assertAlmostEqual(r.spent(), 0.96, places=6)
 114 |              every = router(d, [h, x], {"write": ["heimdall:q"]}, **kw)          # no `uncapped`: all counted, as before
 115 | @@ -428,11 +428,12 @@ class TestRouter(unittest.TestCase):
 116 |              led = os.path.join(d, "SPEND.json")
 117 |              a = Fake("openai:x", "openai", answer="{}", usage={"in": 400_000, "out": 0})        # $4.00 a call
 118 |              r = router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_usd=10)
 119 | -            p = "p" * 400_000                                     # upper bound ~ $4.00 in + $0.20 out
 120 | +            p = "p" * 1_200_000             # ruling 121's reserve: 1.25 x (400,200 x $10/M + 2,000 x $100/M) = $5.25
 121 | +            #   (its characters / 3 as tokens: this prompt bills 400,000, three characters a token)
 122 |              r.call("write", p)
 123 |              r.call("write", p)
 124 |              with self.assertRaises(P.SpendLimit):
 125 | -                r.call("write", p)                                # 8.00 + 4.20 > 10: refused BEFORE it runs
 126 | +                r.call("write", p)                                # 8.00 + 5.25 > 10: refused BEFORE it runs
 127 |              d_ = json.load(open(led))
 128 |              self.assertEqual((d_["calls"], a.calls, d_["reserved"]), (2, 2, {}))
 129 |              self.assertLessEqual(d_["usd_estimate"], 10)
 130 | @@ -730,5 +731,92 @@ class TestRuling86Shadow(TestRuling85Routing):
 131 |                               (["heimdall:qwen"], ["xai:grok"]))
 132 |              self.assertEqual((r.backends["heimdall:qwen"].calls, r.backends["xai:grok"].calls), (1, 2))
 133 |  
 134 | +class TestRuling121Reserve(unittest.TestCase):
 135 | +    """RULING 121 (1) (orchestrator 11:25 ET Nov 16): the spend guard reserves a call at its prompt's characters / 3 as
 136 | +    tokens, the output cap it is really sent, list price, times 1.25; and the xAI back-end is sent at most 12,000 output
 137 | +    tokens (step A's 4,000 x 8 was 32,000: $0.80 of Grok output at list, more than the day's $1.00 had left)."""
 138 | +    REPLIES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "package", "fixtures", "replies")
 139 | +
 140 | +    def xai(self, cap=True, answer='{"ok": true}'):
 141 | +        spec = dict(json.load(open(os.path.join(os.path.dirname(P.__file__), "model_providers.json")))["backends"][
 142 | +            "xai:grok-4.20-0309-reasoning"])
 143 | +        if not cap:
 144 | +            spec.pop("max_out_cap", None)
 145 | +        b = P.XAIBackend("xai:grok-4.20-0309-reasoning", spec, "/nonexistent")
 146 | +        b.sent = []
 147 | +        b.key = lambda name: "k"
 148 | +        return b
 149 | +
 150 | +    def test_the_reserve_is_characters_over_3_the_real_cap_list_price_x_1_25(self):
 151 | +        b = self.xai()
 152 | +        self.assertEqual((b.max_out(4000), b.max_out(1200), b.max_out(750)), (12000, 9600, 8000))
 153 | +        self.assertEqual(self.xai(cap=False).max_out(4000), 32000)
 154 | +        self.assertAlmostEqual(b.upper_usd("p" * 7800, 4000), 1.25 * ((2600 + 200) * 5e-6 + 12000 * 25e-6), places=6)
 155 | +        self.assertAlmostEqual(b.upper_usd("p" * 7801, 4000, system="s"),             # 7,802 characters / 3 =
 156 | +                               1.25 * ((2601 + 200) * 5e-6 + 12000 * 25e-6), places=6)    # 2,600.7: rounded up
 157 | +        v = {"text": "t" * 30, "images": ["i", "i"]}
 158 | +        self.assertEqual(P.Backend.prompt_tokens_reserve(v), 10 + 200 + 2 * P.IMAGE_TOKENS_UPPER)
 159 | +
 160 | +    def test_grok_is_sent_the_capped_output(self):
 161 | +        b = self.xai()
 162 | +        seen = []
 163 | +        saved = P._http_json
 164 | +        P._http_json = lambda url, body, headers, timeout: (seen.append(body) or {
 165 | +            "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {}})
 166 | +        try:
 167 | +            try:
 168 | +                b.complete("p", 4000, 7)
 169 | +            except Exception:                          # the reply's own handling is not under test: only what was sent
 170 | +                pass
 171 | +        finally:
 172 | +            P._http_json = saved
 173 | +        self.assertEqual(seen[0]["max_tokens"], 12000)
 174 | +
 175 | +    def recorded(self):
 176 | +        out = []
 177 | +        for root, _, files in os.walk(self.REPLIES):
 178 | +            for f in files:
 179 | +                if not f.endswith(".json"):
 180 | +                    continue
 181 | +                d = json.load(open(os.path.join(root, f)))
 182 | +                if str(d.get("backend")).startswith("xai:grok") and "context_verdict" in str(d.get("role")):
 183 | +                    out.append(d)
 184 | +        return out
 185 | +
 186 | +    def test_no_recorded_grok_step_a_call_cost_more_than_its_reserve(self):
 187 | +        """The ruling's check: on every recorded Grok step-A call, the reserve (with the cap it was really sent then,
 188 | +        8 x its max_tokens) is at or above its reported cost; under the 12,000 cap, every call that stayed inside it."""
 189 | +        calls, old, new = self.recorded(), self.xai(cap=False), self.xai()
 190 | +        self.assertGreaterEqual(len(calls), 438)
 191 | +        usd = lambda d: d["usage"].get("usd_reported", d.get("usd"))
 192 | +        margin, cut = min((old.upper_usd(d["prompt"], d["max_tokens"], d.get("system")) - usd(d), i)
 193 | +                          for i, d in enumerate(calls)), [d for d in calls if d["usage"]["out"] > 12000]
 194 | +        self.assertGreaterEqual(margin[0], 0.10)                         # the tightest: +$0.1075 (the $0.40 of Nov 12)
 195 | +        for d in calls:
 196 | +            if d["usage"]["out"] <= 12000:
 197 | +                self.assertLessEqual(usd(d), new.upper_usd(d["prompt"], d["max_tokens"], d.get("system")))
 198 | +        self.assertEqual(len(cut), 4)                    # one Nov 12, three Nov 13, none since: under the cap they would
 199 | +        self.assertTrue(all(str(d["recorded_at"]) < "2026-11-14" for d in cut))   # have been cut at 12,000 (out of
 200 | +        #   contract: no verdict, held), never billed past the reserve
 201 | +
 202 | +    def test_a_step_a_call_fits_what_the_day_has_left(self):
 203 | +        """The Fox step A of 11:03 ET: two excerpts, about 7,800 characters, max_tokens 4,000; $0.5835 spent of the
 204 | +        $1.00 day. Capped, it reserves $0.39 and runs; with Grok's old 32,000 cap it reserves $1.02 and is refused."""
 205 | +        with tempfile.TemporaryDirectory() as d:
 206 | +            led = os.path.join(d, "SPEND.json")
 207 | +            json.dump({"usd_estimate": 0.5835, "calls": 1, "by_backend": {"xai:grok-4.20-0309-reasoning": {
 208 | +                "calls": 1, "in": 0, "out": 0, "usd_estimate": 0.5835, "usd_reported": 0.5835}},
 209 | +                "by_role": {}, "reserved": {}, "usd_reported": 0.5835, "usd_unreported_estimate": 0.0}, open(led, "w"))
 210 | +            for cap, fits in ((True, True), (False, False)):
 211 | +                b = self.xai(cap=cap)
 212 | +                b.complete = lambda prompt, max_tokens, seed, system=None: ('{"ok": true}', {"in": 2000, "out": 3000}, 0.02)
 213 | +                r = router(d, [b], {"context_verdict": [b.name]}, spend_path=led, limit_usd=1.0, limit_basis="reported")
 214 | +                if fits:
 215 | +                    self.assertEqual(r.call("context_verdict", "p" * 7800, 4000).text, '{"ok": true}')
 216 | +                else:
 217 | +                    with self.assertRaises(P.SpendLimit):
 218 | +                        r.call("context_verdict", "p" * 7800, 4000)
 219 | +
 220 | +
 221 |  if __name__ == "__main__":
 222 |      unittest.main()
 223 | diff --git a/tests/providers/test_reserve_wait.py b/tests/providers/test_reserve_wait.py
 224 | index 50a18d2..315bcb9 100644
 225 | --- a/tests/providers/test_reserve_wait.py
 226 | +++ b/tests/providers/test_reserve_wait.py
 227 | @@ -20,7 +20,8 @@ sys.path.insert(0, HERE)
 228 |  import providers as P  # noqa: E402
 229 |  from test_providers import Fake, router  # noqa: E402
 230 |  
 231 | -U = (1 + 200) * 10 / 1e6 + 1000 * 100 / 1e6     # Fake's upper bound for prompt "p" and max_tokens 1000: $0.10201
 232 | +U = Fake("openai:u", "openai").upper_usd("p", 1000)   # Fake's reserve for prompt "p" and max_tokens 1000: since
 233 | +#   ruling 121 (1) 1.25 x $0.10201 = $0.12751 (it was the bare $0.10201)
 234 |  
 235 |  
 236 |  class Gate(Fake):
 237 | 
```

---

pp-selectid: RULING 121 (1) (orchestrator 11:25 ET Nov 16), THE SPEND GUARD'S RESERVE, and the xAI output cap.
Files: pipeline/providers.py (Backend.prompt_tokens_reserve, Backend.upper_usd, XAIBackend.max_out, the _reserve
docstring), pipeline/model_providers.json (one key), tests/providers/test_providers.py.

THE ORDER, verbatim: "(1) THE RESERVE: counting every prompt CHARACTER as a token reserves about four times what a call
can cost. Reserve on a token estimate instead: characters / 3 for the prompt (a deliberate over-count; English runs near
4), the call's real max output, list price, times 1.25. Check it against the 438 recorded Grok step-A calls: the reserve
must be at or above the reported cost of EVERY one of them (report the tightest margin); if any call beats it, raise the
divisor's safety until none does." The daily outside cap stays $1.00 (ruling 118: outside vendors only; Heimdall never
reserved).
WHAT THE MEASURE SHOWED (STATE 11:21): the xAI back-end sends Grok 8 x the nominal max_tokens (XAIBackend.max_out:
max(min_out 8000, 8 x max_tokens)), so step A (nominal 4,000) is sent 32,000 and the guard reserved $0.80 of output at
list for every step-A call. With the call's real max output, ruling 121's reserve passes the check on all 438 recorded
calls (tightest margin +$0.1075) but reserves $1.02 for a ~7,800-character step A: never inside a $1.00 day. Grok's
recorded step-A outputs ran over 12,000 tokens in 4 of 438 (one Nov 12, three Nov 13; none since; since Nov 15 the
largest was 8,871). So the cap: "max_out_cap": 12000 on the xAI reasoning back-end (only step A is sent more than that
today: the hook rating, join table, clips-alone and coherence calls are sent 8,000-9,600). A reply cut at the cap is out
of contract: no verdict, held (law L-m, ruling 102), never a verdict made from part of a reply (unchanged guards:
providers.call_parsed and context_integrity.step_a's parsing; Router.call records finish/length on the breaker).

THE CHANGE: upper_usd (the reserve every paid call takes under the ledger lock, Router.call -> _reserve) = 1.25 x list
price of {in: ceil(characters / 3) + 200 (+ 6,000 per image of a vision prompt), out: max_out(max_tokens)}.
prompt_tokens_upper (characters as tokens) is unchanged and still books an abandoned call (prompt_usd, ruling 83 (a))
and the reported-rate estimate (ruling 107 Q1). The reservation is still taken, settled and released as before
(_reserve, unchanged but for its docstring); Heimdall stays unreserved (ruling 118's `uncapped`).

TESTS (TestRuling121Reserve): the reserve's arithmetic (characters / 3 rounded up, the real cap, x 1.25, images); the
body sent to xAI carries max_tokens 12,000; THE RULING'S CHECK on every recorded Grok step-A call in the fixtures (the
reserve with the cap each call was really sent then is >= its reported cost; tightest margin >= $0.10; under the 12,000
cap, every call that stayed inside it is within the new reserve; the 4 longer ones dated); the guard's behaviour with
$0.5835 spent of $1.00: a ~7,800-character step A reserves $0.39 and runs; at 32,000 it is refused. Three older guard
tests re-sized to the new reserve (same assertions). Mutations R1-R7 after a control run.

PLEASE CHECK: (1) the reserve's arithmetic and that every paid call still reserves before it runs; (2) that nothing else
reads upper_usd as a strict bound; (3) the cap: sent to xAI, and on the breaker's runaway measure; (4) the tests.


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


THIS THIRD CYCLE CHECKS THE FIX OF CYCLE 2'S REAL DEFECT: test_reserve_wait.U encoded the pre-121 bound ($0.10201); its 4 tests failed under the new reserve (found after cycle 2 at landing); U is now the Fake's reserve from the code


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
