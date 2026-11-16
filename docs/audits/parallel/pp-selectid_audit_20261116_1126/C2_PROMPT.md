# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1126
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 204 s finish=stop usage in 11322 / out 3102 usd_reported=0.000736 usd~0.080 (upper-bound price)

The code implements RULING 121 (1) exactly as specified. The spend guard's reserve logic has been shifted from a 1:1 character-to-token ratio to a `chars / 3` ratio (rounded up), incorporating a 1.25x margin and a strict output cap for the xAI reasoning model to ensure calls fit within the $1.00 daily limit.

### Analysis

1.  **Reserve Arithmetic**: `Backend.prompt_tokens_reserve` correctly implements the `ceil(chars / 3)` logic using the Python integer division trick `-(-a // b)`. It correctly handles both vision and text prompts, adding the 200-token frame and 6,000 tokens per image.
2.  **Spend Guard Integration**: `Backend.upper_usd` now uses this reserve and the `max_out` value, multiplied by `RESERVE_MARGIN` (1.25), and rounded to 6 decimal places. This value is passed to `Router._reserve`, ensuring the reservation is taken before the call is executed.
3.  **xAI Output Cap**: `XAIBackend.max_out` now respects the `max_out_cap` (12,000) defined in `model_providers.json`. This prevents the reasoning model's $8\times$ multiplier from reserving excessive funds (e.g., 32,000 tokens for a 4,000-token request), which previously blocked calls from running within a $1.00 budget.
4.  **Verification against History**: `TestRuling121Reserve.test_no_recorded_grok_step_a_call_cost_more_than_its_reserve` explicitly validates the new reserve against the 438 recorded Grok calls, confirming the tightest margin is $\ge \$0.10$, as required by the ruling.
5.  **Regression Testing**: Existing `SpendLimit` tests in `test_providers.py` were correctly updated to reflect the new reserve calculations (e.g., increasing prompt lengths to trigger the same limits).
6.  **Fail-Closed Behavior**: The implementation maintains the `SpendLimit` exception, which ensures that if a reserve cannot be secured, the call is refused before execution (M12).

### Findings

No defects found. The implementation is mathematically correct and adheres to all governing laws and the specific requirements of Ruling 121.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 58 s finish=stop usage in 10760 / out 4539 usd_reported=0.003737 usd~0.100 (upper-bound price)

I will begin by analyzing the provided code diff against the governing laws and the specific instructions in the "PLEASE CHECK" section.

### Analysis of `pipeline/providers.py` and `pipeline/model_providers.json`

**1. The Reserve Arithmetic (RULING 121 (1))**
The order states: "Reserve on a token estimate instead: characters / 3 for the prompt... the call's real max output, list price, times 1.25."

*   **Code:**
    ```python
    @staticmethod
    def prompt_tokens_reserve(prompt, system=None):
        n_img, text = (len(prompt["images"]), prompt["text"]) if is_vision(prompt) else (0, prompt)
        return -(-(len(text) + len(system or "")) // RESERVE_CHARS_PER_TOKEN) + 200 + IMAGE_TOKENS_UPPER * n_img
    ```
    *   `RESERVE_CHARS_PER_TOKEN = 3`.
    *   `-(-(x) // 3)` is the standard integer ceiling division for positive integers. This correctly implements `ceil(characters / 3)`.
    *   It adds `200` for the message frame.
    *   It adds `IMAGE_TOKENS_UPPER * n_img` for vision prompts.
    *   **Verdict:** The token estimation logic matches the ruling.

*   **Code:**
    ```python
    def upper_usd(self, prompt, max_tokens, system=None):
        return round(RESERVE_MARGIN * self.usd({"in": self.prompt_tokens_reserve(prompt, system),
                                                "out": self.max_out(max_tokens)}), 6)
    ```
    *   `RESERVE_MARGIN = 1.25`.
    *   It uses `self.max_out(max_tokens)` for the output tokens.
    *   **Verdict:** The multiplication by 1.25 and the use of the "real max output" matches the ruling.

**2. The xAI Output Cap**
The order states: "max_out_cap": 12000 on the xAI reasoning back-end... A reply cut at the cap is out of contract... never a verdict made from part of a reply."

*   **Code:**
    ```python
    def max_out(self, max_tokens):
        n = max(int(self.spec.get("min_out", 8000)), max_tokens * 8)
        cap = self.spec.get("max_out_cap")
        return min(n, int(cap)) if cap else n
    ```
    *   `model_providers.json` adds `"max_out_cap": 12000` to the `xai:grok` backend.
    *   The logic calculates the standard reasoning expansion (`max_tokens * 8`) but caps it at 12,000.
    *   **Verdict:** This correctly implements the cap. The `complete` method (not shown in diff but implied by context) sends this value to the API. The test `test_grok_is_sent_the_capped_output` verifies that `seen[0]["max_tokens"]` is 12000.

**3. "Nothing else reads upper_usd as a strict bound"**
The prompt asks to check if `upper_usd` is used elsewhere in a way that assumes it is a *strict* upper bound on cost, rather than a *reserve* (which is an over-estimate for safety).

*   **Context:** `upper_usd` is used in `Router._reserve`.
    ```python
    def _reserve(self, b, upper):
        # ...
        # Raises SpendLimit when spent + reserved + this call's upper bound would pass the limit.
    ```
*   **Analysis:** The reserve is *intended* to be an over-estimate (hence the 1.25 margin and chars/3 divisor). The purpose of a reserve in a spend guard is to block calls if the *potential* cost exceeds the limit. It is not a billing statement.
*   **Potential Issue:** Does any code use `upper_usd` to *bill* or *report* actual costs?
    *   The diff shows `prompt_usd` is used for abandoned calls (Ruling 83a).
    *   `upper_usd` is specifically for the *reserve*.
    *   The docstring for `upper_usd` was updated to clarify it is the "spend guard's reserve".
    *   **Verdict:** No violation found. The separation between `prompt_usd` (for booking abandoned calls) and `upper_usd` (for reserving) is maintained.

**4. The Tests**

*   **`TestRuling121Reserve.test_the_reserve_is_characters_over_3_the_real_cap_list_price_x_1_25`**:
    *   Checks `max_out` logic: `max_out(4000)` -> `min(max(8000, 32000), 12000)` -> 12000. Correct.
    *   Checks `upper_usd` arithmetic.
    *   **Verdict:** Passes logic check.

*   **`TestRuling121Reserve.test_no_recorded_grok_step_a_call_cost_more_than_its_reserve`**:
    *   Iterates through recorded fixtures.
    *   Asserts `margin[0] >= 0.10`.
    *   Asserts that calls with `out > 12000` are dated before 2026-11-14.
    *   **Verdict:** This is a regression test against historical data. It relies on the fixtures being present and correct. The logic `old.upper_usd(...) - usd(d)` checks if the *old* reserve (without cap, but with new char/3 logic? No, `old` is `self.xai(cap=False)`) covers the cost. Wait, let's look closer.
    *   `old = self.xai(cap=False)`. This backend has `max_out` returning `max(8000, 8*max_tokens)`.
    *   `new = self.xai()`. This backend has `max_out` capped at 12000.
    *   The test checks: `old.upper_usd(...) - usd(d) >= 0.10`.
    *   This verifies that even the *uncapped* reserve (using the new char/3 logic) was sufficient to cover the actual cost of historical calls, with a margin.
    *   Th

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_1126 (RULING 121 (1): the reserve and the xAI output cap)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 2 of 3 (mimo cut off at 32,000
tokens, no answer). P1_OR_WORSE: qwen 0, gemma 0. Cycle 1 $0.0077 of Heimdall, not capped.

qwen's headings tagged [P0]/[P1] are checks it states and answers itself, each "Correct", with its count at 0:
- Router.call takes every paid call's reserve from upper_usd: yes, providers.py:1366 (unchanged): "upper =
  b.upper_usd(prompt, max_tokens, system)", then _reserve; so the new reserve reaches every paid call.
- The cap reaches the request: XAIBackend.complete sends "max_tokens": self.max_out(max_tokens) (providers.py:475,
  unchanged); test_grok_is_sent_the_capped_output asserts 12,000 in the body sent.
- max_tokens 0 or negative: max(min_out 8000, ...) then min(cap): never under 8,000, never over 12,000.
P2s noted, not changed: prompt_tokens_reserve beside prompt_tokens_upper (the latter still books an abandoned call and
the reported-rate estimate, by design: an abandoned call is never under-booked); the constant's comment.

ADDED AFTER CYCLE 1 (in cycle 2's diff): tests/package/test_visual_pin.py's ruling-70 test "the upper bound counts each
image" asserted the reserve grows by exactly IMAGE_TOKENS_UPPER per image; with ruling 121's x 1.25 it grows by 1.25 x
6,000 (each image is still 6,000 tokens: asserted directly on prompt_tokens_reserve). Re-sized like the three guard
tests in test_providers. All 40 suite files pass on dev43. Mutations R1-R7 after a control run: 7 of 7 killed.
A CORRECTION TO THE QUESTION: the 4 recorded calls with over 12,000 output tokens were one on Nov 12 and three on Nov 13
(none since), as the question says; my STATE line of 11:21 wrongly said "all Nov 12". The test asserts it (4, all before Nov 14).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_1126/C2_STEP.diff (223 lines)
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
 223 | 
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


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
