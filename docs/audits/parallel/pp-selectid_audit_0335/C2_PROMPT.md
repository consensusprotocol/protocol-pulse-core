# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0335
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 95 s finish=stop usage in 5294 / out 2464 usd~0.053 (upper-bound price)

# Audit: pp-selectid-0335 — T9 retirement (ruling 35)

## Scope of what I can verify
The diff touches exactly two files: `pipeline/eligibility.py` (the `_span` function, lines 437–444 region) and `tests/eligibility/test_eligibility.py` (TestSpan, lines 258–265 region). Everything below is judged from the diff plus the stated context; where the diff doesn't show a file, I say so.

## What the diff actually does

**eligibility.py, hunk 1 (line 9–10):** comment-only change on the `MAX_WINDOW_SENTENCES = 3` line. The constant's value is unchanged. The added comment says "recorded only since ruling 35" and the test mirrors the constant against `editorial_select.py` — consistent with the stated intent that the constant stays.

**eligibility.py, hunk 2 (lines 18–22):** the `elif n > MAX_WINDOW_SENTENCES:` branch previously called `R("too_many_sentences", ...)`; now it appends a string to `targets`. From the diff I can see:
- `R(...)` presumably adds to a reasons collection (the test asserts `names()` no longer contains it), and `targets` presumably feeds `facts["targets_missed"]` (the test asserts `facts["targets_missed"]` contains the string). Both are inferred from the test, not shown in the diff — but the test is the contract, and it exercises exactly this.
- The new string is `f"{n} sentences > {MAX_WINDOW_SENTENCES} (T9, retired by ruling 35: the 20 s clip limit and the per-source limit govern length)"`.
- The `n == 0` → `R("no_content", ...)` branch is untouched and still a reason (test line 41 confirms `no_bitcoin` reasons still work; `no_content` itself isn't re-asserted in the diff, but the code line is unchanged).

**test change:** the 4-sentence fixture (`Span(four, 0, 3)`) now asserts (a) `too_many_sentences` NOT in `names()`, (b) a `targets_missed` entry starting `"4 sentences > 3 (T9, retired by ruling 35"`. The `assertTrue(any(...))` with a `facts` failure message is good practice.

## Findings

### P1-1 — The recorded string's wording is now load-bearing in a test, and it's brittle to the constant's value
`tests/eligibility/test_eligibility.py:37` asserts the literal substring `"4 sentences > 3 (T9, retired by ruling 35"`. This hard-codes both the count (4) and the constant (3) in prose. If `MAX_WINDOW_SENTENCES` ever changes (the comment at eligibility.py:9 says the constant is kept and mirrored against `editorial_select.py:52`), this test breaks even though the behavior is correct. Minor, but it's exactly the kind of duplicated constant the diff's own comment warns about. **Suggestion:** build the expected string from `E.MAX_WINDOW_SENTENCES` and the fixture's sentence count, or at least assert only the stable prefix `"4 sentences > 3 (T9, retired by ruling 35"`. (Actually the assertion already uses a prefix via `in`, so only the "3" is duplicated — downgrade to P2 if you weigh the `in`-prefix.)

*Regrade: this is really P2; I list it under P1 only because the section asks for severity-ordered findings. Treat as P2.*

### P2-1 — `targets_missed` semantics: retired rule now shares the "missed target" channel with live targets
`eligibility.py:20–22` puts the retired T9 count into `facts["targets_missed"]`, the same list that carries L-o's *live* length targets (HOOK_S/CLIP_S, per lines 23–25 of the diff, which remain reasons-adjacent: the comment says "a target (law L-o); not measured = fail closed"). The ruling says T9 is "recorded only" — that's satisfied — but readers of `targets_missed` now cannot distinguish a *retired, informational* entry from a *live, governing* target without parsing the parenthetical. The stated readers are:
- `moments.py` — copies it into the moment's eligibility record (informational; no behavior change claimed),
- `eligibility.py:621` — appends to it (not shown in the diff; I cannot verify what it appends or whether it, e.g., dedupes or formats).

**Scenario:** a future reader (or a dashboard) treats "targets_missed" as "things that governed the decision" and surfaces the T9 note as a rejection cause. Not a defect today; a documentation/semantics cost. If you want it airtight, the ruling-35 note could live in a separate facts key (e.g. `facts["retired_targets"]`) — but that's a larger diff than "smallest diff" (M1) warrants. Note, don't fix.

### P2-2 — Coverage: only the 4-sentence case is tested; the 3-sentence boundary and the n==0 interaction are not re-verified in this diff
The test exercises `n = 4 > 3` (retired → recorded). Not shown/changed:
- `n == 3` (exactly at the limit): previously no reason, now no reason and — presumably — no `targets_missed` entry. If the new `elif` were accidentally converted to a bare `if` + unconditional append, or if the `elif` chain were disturbed, the 3-sentence case would silently gain a spurious target. The diff shows the `elif` preserved, so this is likely fine, but no test pins it. Pre-existing gap, not introduced here

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 15 s finish=stop usage in 5388 / out 235 usd~0.033 (upper-bound price)

**P0 findings:** none verifiable from diff  
**P1 findings:** none verifiable from diff  
**P2 findings:**  
- pipeline/eligibility.py:10 (comment): MAX_WINDOW_SENTENCES constant comment updated to note "recorded only since ruling 35". Matches supplied ruling text.  
- pipeline/eligibility.py:18-22: sole behavioral change is replacement of R("too_many_sentences", ...) with targets.append(...) recording the same text in facts["targets_missed"]; n==0 "no_content" path and all surrounding code untouched in the hunk.  
- tests/eligibility/test_eligibility.py:35-38: test updated to assert absence of "too_many_sentences" in .names() while confirming the exact target string now appears in facts["targets_missed"]. No other test logic altered.  

Nothing else in eligibility.py is modified by the diff. Cannot verify from diff alone whether "too_many_sentences" is referenced elsewhere in the same file, whether other length rules depend on that exact string, or the full lifecycle of facts["targets_missed"] (initialization, consumption in moments.py:?, eligibility.py:621).  

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 28 s finish=stop usage in 5700 / out 1048 usd~0.033 (upper-bound price)

# Code Audit: pp-selectid-0335 (C1_STEP.diff)

## Findings

### P1: `pipeline/eligibility.py:439-441` — Unverified variable scope for `targets`
The diff introduces `targets.append(...)` inside the `_span` function. However, the provided diff context (lines 14-25) does **not** show the definition or initialization of the `targets` variable.
- **Scenario:** If `targets` is not defined in the local scope of `_span` (e.g., if it was previously only used in a different branch or if the variable name is actually `facts["targets_missed"]`), this line will raise a `NameError` at runtime for any span with `n > 3`.
- **Verification Limit:** I cannot verify the existence of `targets` from the diff alone. The comment on line 23 mentions `facts["targets_missed"]`, and the test on line 37 checks `four_r.facts["targets_missed"]`. It is highly likely that `targets` is a local alias for `facts["targets_missed"]` defined earlier in the function (outside the diff hunk), but this is an assumption. If `targets` is not a valid local variable, this is a P0 crash. If it is an alias, it is correct. **Flagging as P1 due to inability to verify scope.**

### P2: `pipeline/eligibility.py:439` — String formatting consistency
The new target string is:
`f"{n} sentences > {MAX_WINDOW_SENTENCES} (T9, retired by ruling 35: the 20 s clip limit and the per-source limit govern length)"`
- **Scenario:** This is a long, static string. While functionally correct, it embeds policy rationale into the data structure. This is acceptable per the "recorded only" instruction, but ensure downstream consumers (e.g., `moments.py`) do not parse this string for logic. The prompt states `facts["targets_missed"]` is "information only," so this is compliant.

### P2: `tests/eligibility/test_eligibility.py:37` — Test assertion fragility
The test asserts:
`self.assertTrue(any("4 sentences > 3 (T9, retired by ruling 35" in t for t in four_r.facts["targets_missed"]), ...)`
- **Scenario:** This is a substring match. If the wording of the target string in `eligibility.py` changes slightly (e.g., punctuation, capitalization), the test will fail. This is standard for such tests but worth noting for maintainability.

## Compliance Check

1.  **Nothing else in eligibility changes:**
    -   The diff only modifies the `elif n > MAX_WINDOW_SENTENCES` block.
    -   The `n == 0` case (`no_content`) is unchanged (line 16-17).
    -   The `MAX_WINDOW_SENTENCES` constant is unchanged (line 9-10).
    -   **Verdict:** Compliant.

2.  **No other hard length rule depends on this reason:**
    -   The prompt states: "The hard length rules stay elsewhere and are not touched: `package.usable()` refuses a moment over `SEG_MAX_S = 20 s`... the line-up's seconds must land the runtime inside 60-70 s."
    -   The diff removes the *rejection* reason `too_many_sentences`. It does not modify `SEG_MAX_S` or the runtime check.
    -   **Verdict:** Compliant. The change correctly shifts T9 from a hard gate to a soft target, as per Ruling 35.

3.  **`facts["targets_missed"]` is information only:**
    -   The prompt states: "Its only other readers: `moments.py` copies it into the moment's eligibility record, and `eligibility.py:621` appends to it."
    -   The diff appends to `targets` (assumed to be `facts["targets_missed"]`).
    -   **Verdict:** Compliant, assuming `targets` is indeed `facts["targets_missed"]`.

## SHIP: yes with conditions

**Condition:** Verify that the variable `targets` is defined in the local scope of `_span` in `pipeline/eligibility.py` (likely as `targets = facts["targets_missed"]` or similar) before line 439. If `targets` is not a valid local variable, this is a **P0** `NameError` and must be fixed before shipping.

If `targets` is correctly scoped, the change is minimal, compliant with Ruling 35, and correctly demotes the sentence count limit from a hard rejection to a recorded target.

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0335 (ruling 35: too_many_sentences retired): cycle 1 consensus

Synthesis by the pp-selectid session, 03:19 ET Nov 13, written before cycle 2.

**Run.** C1_STEP.diff covers eligibility.py and test_eligibility.py. No P0. Verdicts:
- grok: no P0 and no P1, "SHIP: yes";
- qwen: "yes with conditions" (verify that `targets` is in scope);
- glm: "SHIP: yes", conditional on a grep for other consumers.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | Is `targets` bound where the retired rule appends to it (qwen P1)? | VERIFIED. eligibility.py:425 binds `targets = facts.setdefault("targets_missed", [])` in the same on-screen branch, before T7/T8 and T9. The test that reads the recorded target passes, which proves the append ran. |
| K2 | Does any other consumer of the reason string "too_many_sentences" exist (glm P2-4)? | VERIFIED by grep over every .py in the worktree, including pipeline/test_*.py. The only other hit is select_by_id.PLAIN:591, a reason-to-plain-words table for the older selector's model feedback. With the reason never raised, that entry is never read. KEPT, flagged (K2 law: not silently deleted). No gate, count or report reads the string. |
| K3 | The test is brittle on the literal "3", and the cap boundary is untested (glm P1-1 regraded to P2, glm P2-2) | IMPLEMENTED: the expected string is built from E.MAX_WINDOW_SENTENCES. A 3-sentence span (at the cap) records no T9 target. |

## Kept

- **glm P2-1 (retired and live targets share targets_missed):** KEPT. The recorded string names itself retired ("T9, retired by ruling 35"), and nothing ranks on the list.
- **qwen P2 (string formatting):** cosmetic, no change.

## Verification

- test_eligibility 29 OK, plus the boundary assertion.
- test_moments, test_select_by_id and test_ledger_build OK.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0335/C2_STEP.diff (44 lines)
```
   1 | diff --git a/pipeline/eligibility.py b/pipeline/eligibility.py
   2 | index 571718b0..24a1e721 100644
   3 | --- a/pipeline/eligibility.py
   4 | +++ b/pipeline/eligibility.py
   5 | @@ -45,7 +45,7 @@ RUNTIME_S = (60.0, 70.0)                    # L1b law L-o (PBX 2026-11-12 01:50)
   6 |  TAIL_S = 14.30                              # what a final adds to its segments' word spans (credits card, outro, cut
   7 |                                              # leads / tails, pads): the approved preview's finals 71.08 s (DoD 14:47)
   8 |                                              # minus its four word spans 56.78 s (references/pulse_preview_2026-11-11)
   9 | -MAX_WINDOW_SENTENCES = 3                    # T9 editorial_select.py:52
  10 | +MAX_WINDOW_SENTENCES = 3                    # T9 editorial_select.py:52; recorded only since ruling 35
  11 |  N_CLIPS = (2, 3)                            # L1 >= 2: edl_rules.py:220; <= 3: editorial_select.py:54
  12 |  MAX_SPANS_PER_VIDEO = 2                     # L4 editorial_select.py:55 (MAX_VERIFIED_QUOTES_PER_VIDEO)
  13 |  MAX_CLIPS_PER_CHANNEL = 2                   # L5 editorial_select.py:1291; select_passages.py:291
  14 | @@ -437,8 +437,9 @@ def _span(span, ctx, role):
  15 |      facts["n_sentences"] = n
  16 |      if n == 0:
  17 |          R("no_content", "interjections only")
  18 | -    elif n > MAX_WINDOW_SENTENCES:
  19 | -        R("too_many_sentences", f"{n} sentences > {MAX_WINDOW_SENTENCES}")
  20 | +    elif n > MAX_WINDOW_SENTENCES:                 # ruling 35 (03:12 ET Nov 13): RETIRED as a rule, recorded only. The 20 s
  21 | +        targets.append(f"{n} sentences > {MAX_WINDOW_SENTENCES} (T9, retired by ruling 35: the 20 s clip limit and "
  22 | +                       f"the per-source limit govern length)")
  23 |      # T10 duration of the span's own words: a target (law L-o); not measured = fail closed (the runtime needs it)
  24 |      lo, hi = HOOK_S if role == "hook" else CLIP_S
  25 |      a, b = _time(toks[w0], "start"), _time(toks[w1], "end")
  26 | diff --git a/tests/eligibility/test_eligibility.py b/tests/eligibility/test_eligibility.py
  27 | index c23143ab..46c20050 100644
  28 | --- a/tests/eligibility/test_eligibility.py
  29 | +++ b/tests/eligibility/test_eligibility.py
  30 | @@ -258,7 +258,12 @@ class TestSpan(unittest.TestCase):
  31 |          self.assertTrue(any("target" in t for t in short.facts["targets_missed"]), short.facts)
  32 |          four = source(["Bitcoin fell.", "Bitcoin rose.", "Bitcoin fell again.", "Bitcoin is flat now after all that."])
  33 |          sp = E.Span(four, 0, 3)
  34 | -        self.assertIn("too_many_sentences", E.eligible(sp, ctx("hook", story=statements(sp))).names())
  35 | +        four_r = E.eligible(sp, ctx("hook", story=statements(sp)))           # ruling 35: retired, recorded only
  36 | +        self.assertNotIn("too_many_sentences", four_r.names())
  37 | +        self.assertTrue(any(f"4 sentences > {E.MAX_WINDOW_SENTENCES} (T9, retired by ruling 35" in t
  38 | +                            for t in four_r.facts["targets_missed"]), four_r.facts)          # audit 0335 C1, glm
  39 | +        three = E.eligible(E.Span(four, 0, 2), ctx("hook", story=statements(E.Span(four, 0, 2))))
  40 | +        self.assertFalse(any("T9" in t for t in three.facts["targets_missed"]), three.facts)   # at the cap: nothing
  41 |          alt = self.hook(["Solana rallied twenty percent this week after the exchange listing news broke on "
  42 |                           "Monday morning, leading every large cap token higher into the weekend close."])
  43 |          self.assertIn("no_bitcoin", alt.names())                                                 # an altcoin sentence
  44 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
pipeline/eligibility.py decides whether a span of a word-timed transcript may be shown on screen as a hook or a clip.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: ORCHESTRATOR RULING 35 (03:12 ET Nov 13): "too_many_sentences: retired. The 20 s clip limit and the per-source
limit govern length." Rule T9 (MAX_WINDOW_SENTENCES = 3) came from the OLD story selector (editorial_select.py:52).
In the latest build's funnel it kept 17 of 70 moments off screen, 7 of them for that reason alone. The hard length
rules stay elsewhere and are not touched:
- package.usable() refuses a moment over SEG_MAX_S = 20 s per source video (L-u), or with an unmeasured duration;
- the line-up's seconds must land the runtime inside 60-70 s (L-o).
Law L-o already treats the clip and hook length targets this way: they are recorded in facts["targets_missed"], and
they rank nothing and reject nothing.

The change:
1. pipeline/eligibility.py: a span of more than MAX_WINDOW_SENTENCES (non-interjection) sentences no longer adds the
   reason "too_many_sentences". The count is recorded in facts["targets_missed"] instead. The constant stays (a test
   mirrors it against editorial_select.py). n == 0 ("no_content": interjections only) is unchanged.
2. tests/eligibility/test_eligibility.py: the 4-sentence hook no longer carries the reason, and records the target.

Check in particular:
- that nothing else in eligibility changes;
- that no other hard length rule depends on this reason;
- that facts["targets_missed"] is information only. Its only other readers: moments.py copies it into the moment's
  eligibility record, and eligibility.py:621 appends to it.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".


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
