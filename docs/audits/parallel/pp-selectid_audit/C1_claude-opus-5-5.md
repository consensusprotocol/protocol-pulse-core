# claude-opus-5-5 (effort high) 226 s stop_reason=end_turn usage=in 112645 / out 23213

# Audit: pp-selectid (select_by_id + eligibility predicate)

This review covers only the diff shown. Where a defect depends on code outside the diff (LocalLLM, transcript_store, select_passages), it is marked UNVERIFIED.

## Short answers

**Q1 (fail-open).** The reply contract itself is tight. None of the listed bad replies can be accepted:
- **Prose, code fences, two objects, NaN, duplicate keys:** rejected by `parse_reply` (startswith/endswith `{`/`}`, `object_pairs_hook=_no_dup`, `parse_constant=_no_constant`, lines 1598-1611).
- **String, float or bool ids:** rejected by `type(x) is not int` (line 1623) and `Table.row` (line 1427).
- **Unknown or missing keys:** rejected by `_keys` (line 1614).
- **Cross-source or gapped ranges:** rejected by `Table.span` (lines 1437-1440).
- **One-channel story or line-up:** rejected by `check_story` (line 1647), `check_lineup` (line 1671) and again by eligibility.

Exceptions never produce an acceptance, because `status="accepted"` is only returned after `check` returns (line 1830). However, non-`ModelError` exceptions abort the whole selection ungracefully (D3). Missing timestamps are defaulted to 0 in two rules (D6).

**Q2 (faithfulness).** Most rules match or are stricter than the cited source, and the stricter choices are disclosed. The undisclosed loosenings are D1 (D4 sandwich), D6 (timestamp defaults) and, in the wiring, D2.

**Q3 (verbatim).** I found no path for model text into the claim, segments, passages.json or ledger evidence. Every output text is `Span.text`, i.e. `spoken(tokens)`. Model raw replies only reach `attempts` records and the retry prompt.

**Q4 (wiring).** Kept: pool order and laziness (lambdas, `run_pools` lines 2089-2094), the free Bitcoin screen (line 2103), the word pass before the line-up, `words_fn`, and `NoProducibleStory` on `selected is None`. Problems are D2, D3, D4 and D5.
- `registry` (line 465) and `os` (line 565) are not defined anywhere in the visible hunk. I cannot confirm they exist in `_select_story` at c1451047. The smoke test would catch this, but its output is not part of the diff.

**Q5 (tests).** See D7. The must-fail tests mostly fail for the right reason, via `reason_names`. `test_strict_json_and_ids` is reason-agnostic.

## Defects

**1. HIGH | eligibility.py `_anchor`, lines 1194-1198**
```python
a, b = min(core), max(core)
anchor = spoken(toks[S[a][0]:S[b][1] + 1])
...
for d, ks in (("prev", range(a - 1, span.k0 - 1, -1)), ("next", range(b + 1, span.k1 + 1))):
```
- **Issue:** Sentences strictly between two core (`*`) sentences are never examined. They skip D4 (a) back-reference, D4 (b) 8 s and the cap. This is looser than the D4 rule it claims to port, and it is not disclosed. The prompt's "the rest + rows next to those * rows" (line 1561) is not enforced.
- **Scenario:** A clip `[*, "Anyway, Solana looks great.", *]` from one video is accepted. The test at lines 3475-3476 already exercises this path: Yahoo's middle sentence passes unchecked.
- **Fix:** Iterate `range(a + 1, b)` for `k not in core`. Treat each as transparent if `interjection_only`, else require `backward_reference(stext(k), anchor, ctx.event)`. Otherwise `R("adjacent_not_admissible", ...)`.

**2. HIGH | REQUESTS R1 patch, lines 456-466 (replacing old steps 4-7, incl. `_clip_quality`, line 516)**
- **Issue:** The wiring removes, as gates:
  - the `rate_passages` floors (hook ≥ 4.0, clip ≥ 3.5);
  - `verify_reaction` (D4 c);
  - `verify_support` / currentness (E1);
  - `BTC_RELEVANCE_MIN`.

  The line-up model's own choice stands in for all of them. Law L-f states "hook >= 4.0, stand-alone, topic and sentence laws unchanged". LAW 20 forbids changing what a check accepts. Section R3 D-a admits "R1 does not run them" but still ships the patch as the wiring.
- **Scenario:** The same model reply that picks a range is also its only quality judge. A hook the old scorer rated 3.0 is now selected.
- **Fix:** In R1, run `rate_passages` on the chosen verbatim ranges with the unchanged floors, plus `verify_reaction` on each non-`*` sentence. A failure means `Rejected` and a re-ask, or HOLD. Alternatively, block merge until PBX decides D-a.

**3. MEDIUM | select_by_id.py `OllamaModel.complete`, line 1694; `_ask`, lines 1814-1819; patch lines 566-578**
```python
return self.llm._post(prompt, max_tokens, seed), {...}
```
- **Issue:** Transport, HTTP or GPU-guard exceptions from `_post` are not mapped to `ModelError`, so they escape `_ask`. `L.stop()` and `E.close()` are not in a `finally`. As a result:
  - Ollama and the embedder are left holding GPU0;
  - no `rec["decision"]` is written;
  - remaining groups and pools are abandoned.

  The return type of `_post` is UNVERIFIED.
- **Scenario:** An Ollama timeout during a 72 h cluster crashes `select_story` with a traceback instead of recording `model_error` and continuing.
- **Fix:** Wrap the `_post` call in `try` and `except Exception as e: raise ModelError(type(e).__name__)`. Put `L.stop()` and `E.close()` in a `finally` in the patch.

**4. MEDIUM | patch `story_words`, lines 507 and 553-556**
```python
ts.acquire(vid, ..., prefer_words=True)   # result discarded
...
r = ts.canonical_transcript(vid)
got[vid] = word_source(vid, r) if ts.sentence_ready(r) else None
```
- **Issue:** The record that `acquire` returns (per L-e, the `whisper_words_punct` record) is thrown away and the store's canonical pick is re-read. The old code used acquire's return (old line 501-506). If `canonical_transcript` prefers captions or the verbatim record, no line-up is ever possible in production. This is UNVERIFIED: it depends on `canonical_transcript`'s preference, which the smoke test never exercises because it pre-stores the punct record.
- **Fix:** Keep `r, st = ts.acquire(...)` and use `r` when `ts.sentence_ready(r)`.

**5. MEDIUM | patch lines 568-574 and 584-586 (removed `_close_cluster_ledger` and the INFRA_HOLD branch, old lines 547 and 580-583)**
- **Issue:** Gates are written only for groups that `run_pools` visited. These clusters get no gate, contrary to L-f / DEC-13 d ("every cluster's ledger entry names ... the gate that stopped it"):
  - clusters after the winning group;
  - clusters in unevaluated later pools;
  - clusters stopped by budget.

  In addition, `entry["claim"]` is never set. A GPU or Whisper failure (`release_error`) now ends as "HOLD: no candidate is producible" instead of INFRA_HOLD.
- **Scenario:** The 48 h pool wins on cluster 0. Clusters 1..n and all 72 h entries carry no `gate`.
- **Fix:**
  - Set a "not evaluated: ..." gate on every untouched `emergent` entry.
  - Set `claim` from `st.claim.text`.
  - Emit an infra decision when `arb` has `release_error` or `results` hold infra errors.

**6. LOW | eligibility.py line 1170; lines 1196 and 1201**
```python
gap = (toks[w0].get("start") or 0) - (toks[w0 - 1].get("end") or 0)
st = toks[S[k][0]].get("start") or 0
```
- **Issue:** A missing timestamp becomes 0 and can pass the check, violating M12.
- **Scenario:**
  - Previous word's `end` is None and the hook starts at 120 s: the gap is 120 s and `hook_lead` passes.
  - A next-side sentence has `start` None: the gap is negative and D4 (b) passes.
- **Fix:** If any operand is not a number, emit `R("hook_lead" / "adjacent_not_admissible", "not measured")`.

**7. LOW | tests/select_by_id/test_select_by_id.py, lines 3605-3613; tests/eligibility, lines 2502-2503**
- **Issue 1:** `assertEqual(out.status, "rejected", raw)` is reason-agnostic, so two type checks are effectively untested:
  - With the bool check removed, `True == 1` resolves to row 1, which is DataDash, so the reply is still rejected as "story comes from one channel".
  - A float id is rejected by `Table.row`, not by `_id`.
- **Issue 2:** `TestRealPreview` passes the approved passages as their own story statements. Every sentence is then core, so D4 is never exercised. Per NOTE-PS6, the Natalie clip fails D4 otherwise.
- **Fix:** Assert the specific rejection text per bad reply ("not an integer id", "duplicate key", ...). For the preview test, use the single-sentence statements, or state that D4 is not covered.

**8. LOW | eligibility.py `_delivered`, lines 1220-1221 vs old ledger form, line 604**
- **Issue:** Old ledger evidence stored `quote_tokens = sm._norm(quote).split()`. New spans compare `canon.canon_tokens`. Where number, currency or unit tokenisation differs, the 5-token run can be missed, which weakens DEC-9 for entries written before this change. The check is also same-video only. Exact equivalence to `story_ledger.delivered_match` is UNVERIFIED.
- **Fix:** Re-canonicalise from `x["quote"]` when present instead of trusting stored `quote_tokens`, and parity-test against `story_ledger.delivered_match`.

## Notes (not counted)

- **M1 ("no new selector"):** This diff adds a selector. It relies on the 00:32 order, which is not verifiable here.
- **Unknown citation:** the docstring cites "law L-m", which does not exist in the governing laws.
- **Doc inconsistency:** the design doc says `OpenAIStandIn` served the proof, but the proof defaults to `AnthropicStandIn`.
- **Recorder key:** omits the context size, which L-f lists.
- **Downstream consumers UNVERIFIED:** passages.json now carries `"score": None` and `short_label` / `query` are gone. `select_and_build_edl` was not exercised by the smoke test.

SCORE: 66/100
VERDICT: NOT READY