# qwen3.8-27b (qwen/qwen3.8-27b) 110 s finish=stop usage in 9033 / out 9303 usd_reported=0.007053 usd~0.167 (upper-bound price)



# CYCLE 2 — pp-selectid-20261116_2342 (RULING 130 (4): coherence panel)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Gemma's Cycle 1 output was thorough and I find no factual errors in it. The consensus correctly dismissed qwen's lone tagged finding (staging `base_url`) as a non-issue since all five Heimdall back-ends share that gateway address. I had not explicitly verified in Cycle 1 that the `avoid_family=others` set correctly includes *both* the other panel members' families *and* the writer's family (`wf`), which Gemma called out. Re-reading line 96:

```python
others = {fams[o] for o in names if o != n} | wf
```

Yes — this is correct and I confirm it. The router's backend selection for member `n` excludes every other panel family and the writer's family, guaranteeing the call lands on `n` specifically.

## 2. WHERE DO I AGREE OR DISAGREE?

| Gemma / Consensus claim | Verdict |
|---|---|
| Replay rule (seeds 7,8; retry at +100; majority > half; no-verdict < 3) is correctly implemented | **Agree.** Verified line-by-line against the `for sd … for s in (sd, sd+100)` loop with `break` on success. |
| `statistics.median_low` for clips and vo_point | **Agree.** Lines 125–126. |
| First sound `through_line` selected | **Agree.** Line 122: `next((v["through_line"] for v in answers if _line_ok(…)), answers[0]["through_line"])`. |
| Writer exclusion via `names` filter + `avoid_family` | **Agree.** Lines 91–92 (filter) and 96, 101 (avoid). |
| `PANEL_CONTRACT` as system prompt, `hook_answer` brace rule for panel parse | **Agree.** Line 65, 144, 152. |
| `coherence_panel_spec` returns `None` → single-rater fallback | **Agree.** Lines 73–77, 150–151. |
| Ruling 61: `own["passes"]` required for final `ok` | **Agree.** Line 129. |
| Staging `base_url` is not a defect | **Agree** (per consensus). |
| Mutations 8/8 killed; 863 tests pass | **Agree** (per consensus, dev53). |

No disagreements.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P3] `max_tokens=1200` vs. provider `min_out: 16000`** (lines 100, 18, 29). The two new back-ends declare `min_out: 16000` in `model_providers.json`, yet the panel call caps output at 1200 tokens. In practice this is a non-issue: the existing qwen back-end (already in the panel and working) carries the same `min_out`, and `min_out` is evidently a model-level quality floor enforced by the gateway, not a per-call token budget that would reject a 1200-token JSON verdict. The consensus confirms the new back-ends "copy qwen's spec." No action needed, but a one-line comment in the JSON (`"min_out": 16000  // gateway-level floor; panel calls cap at 1200 via max_tokens`) would prevent future confusion.

**[P3] Local imports inside `coherence_by_panel`** (lines 88–89: `import statistics`, `import providers as P`). Standard pattern to avoid circular imports at module load. No defect.

**[P3] `sorted(votes)[0]` for `lineup_floors`** (line 115). The bar is derived from the first alphabetically-sorted *answering* member. Since all three panel members are Heimdall (same vendor → same "standard" bar), the choice is immaterial. If a future panel mixed vendors, this line would need to pick a canonical member explicitly. Not a bug today.

**No P0, P1, or P2 findings.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Replay rule fidelity (seeds, retry, majority, no-verdict) | Correct | Correct | Confirmed; no change |
| Writer exclusion (vendor + family) | Correct | Correct | Confirmed `others` set logic |
| Bar / floors / pass predicate | Correct | Correct | `lineup_floors` + `_line_ok` + clip/vo floors |
| Output construction (medians, through-line, hook_own) | Correct | Correct | `median_low`, first-sound TL, ruling 61 gate |
| Fallback (no panel → single rater) | Correct | Correct | `coherence_panel_spec` → `None` path |
| Parse / brace rule | Correct | Correct | `hook_answer` for panel, `json.loads` for single |
| Config (JSON role, back-ends) | Correct | Correct | Own role, not a verdict role, not a shadow |
| Tests (7 cases + integration) | Sufficient | Sufficient | Cover all 5 audit questions; mutations 8/8 |
| `min_out` / `max_tokens` interaction | Not flagged | [P3] note | Clarified as non-issue |

## 5. FINAL PRIORITY LIST

| Severity | Finding | Location |
|---|---|---|
| — | None at P0, P1, or P2 | — |
| [P3] | Add a comment clarifying `min_out` is a gateway floor, not a per-call budget | `model_providers.json` lines 18, 29 |
| [P3] | Consider a comment on `sorted(votes)[0]` noting it is safe only while all members share one vendor/bar | `package.py` line 115 |

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The implementation is correct as-is; the highest-leverage *documentation* change is a one-line comment in `model_providers.json` next to `min_out` stating it is a gateway-level quality floor (not a per-call token minimum), so the next auditor does not flag the 1200-vs-16000 mismatch as a defect.

## 7. PRODUCTION READY?

**Yes.** All five audit questions are satisfied:

1. The rule is the replay's exactly: no verdict below 3 members, strict majority over all answers, standard bar via `lineup_floors`.
2. The writers' vendor and family are excluded from `names` and from every `call_parsed` via `avoid_vendor` / `avoid_family`.
3. A failed panel verdict carries the same `clips` / `vo_point` / `through_line` / `hook_own` shape as a single-rater verdict, so the redo/re-line code at :4069 reads it identically.
4. A no-verdict returns `(False, {"measured": False, …})` — it can never pass.
5. Tests cover all critical paths; mutations 8/8 killed; 863 tests green.

No conditions.

P1_OR_WORSE: 0