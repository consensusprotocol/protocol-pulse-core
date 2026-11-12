# claude-fable-5-2 (effort high) 408 s stop_reason=end_turn usage=in 112645 / out 40023

# Review: pp-selectid (select_by_id + eligibility + R1 wiring patch)

Scope: the diff only. Anything that depends on files not shown (`editorial_select.py` outside the hunk, `story_semantics.LocalLLM`, `stand_alone`, `select_passages`) is marked unverifiable. I ran nothing; every finding is from reading the code.

## Short answers

**Q1 (fail-open).** I found no path where a non-id reply, a cross-video or gapped range, or a one-channel story or line-up is accepted. A model error or an unexpected exception gives no selection or a crash, never a pass. Three missing measurements do pass silently (defect 7).

**Q2 (faithfulness).** Freshness, partner channel, layout, durations, sentence count, overlap, per-video and per-channel rules are equal or stricter as written. D4 adjacency is looser in two undisclosed ways (defects 3, 6), the story anchor is loose (defect 5), and the ledger rule can be routed around by the retry loop (defect 4).

**Q3 (verbatim).** I found no path for model-written text into the claim, a segment text, `passages.json` or the ledger evidence; all come from `Span.text`. Raw replies are stored only under `select_by_id[].attempts[].raw`.

**Q4 (wiring).** Pool order, laziness, the free screen, the word pass before the line-up call, `words_fn` and `NoProducibleStory` are kept. The patch conflicts with L-f and L-l (defects 1, 2). Three smaller points:
- **Ledger gates (DEC-13 d):** clusters after the winner and clusters in an unevaluated tier no longer get a `gate`, because `_close_cluster_ledger` and the "not evaluated" branch are removed.
- **Empty gate reason:** `lo.get('why')` never exists on a rejected line-up, so the gate reads "line-up rejected:" with no reason.
- **Lost distinction:** the "HOLD (infrastructure)" decision is gone.

**Q5 (tests).** The must-fail and must-pass tests mostly fail and pass for the stated reason. Several assertions are vacuous, and the production branch is never run (defect 8).

## Defects

**1. HIGH | REQUESTS R1 patch and `select_by_id.to_passages`**
- **Code:** `"score": None, "clip_score": None, "relevance": None`; R3 D-a: "R1 does not run them (the line-up call's choice stands for them)"; the patch deletes the `_clip_quality(...)` call.
- **Issue:** L-f says "hook >= 4.0, stand-alone, topic and sentence laws unchanged". R1 removes the hook >= 4.0 and clip >= 3.5 floors, `verify_support` (presented as current) and `verify_reaction` (D4 c). It is disclosed as a "decision", but the patch as delivered ships the looser behaviour, which LAW 20 forbids.
- **Scenario:** the model picks a rule-legal 9 s hook that today's scorer would rate 2.5. It is accepted and rendered with no floor.
- **Fix:** inside R1, run `rate_passages` on the chosen verbatim ranges and `verify_support` on the claim sentence, as rejection reasons in `choose_lineup`. Otherwise do not merge R1 until PBX rules on D-a.

**2. HIGH | `select_by_id.Recorder`, wired into production by R1**
- **Code:** `hashlib.sha256(json.dumps([self.name, prompt, max_tokens])...)`; `if os.path.exists(p): ... return rec["raw"]`; patch: `model = SB.Recorder(model, os.path.join(sm.LLM_CACHE_DIR, "select_by_id"))`.
- **Issue:** every raw reply is cached before validation, and the key omits the seed. L-l requires that a cached reply which fails validation is asked again, and L-f(e) caches only validated replies. The test confirms the seed is ignored: `rec.complete("p", 10, 8)` is served from disk.
- **Scenario:** attempts 2 and 3 are rejected for the same reason, so their prompts are identical and attempt 3 is served from disk without a model call. An empty or truncated reply is replayed on every rerun with the same prompt.
- **Fix:** write the file only after `check()` accepts or declines (a commit hook from `_ask`), and add the seed to the key.

**3. MEDIUM | `eligibility._anchor`**
- **Code:** `a, b = min(core), max(core)` … `for d, ks in (("prev", range(a - 1, span.k0 - 1, -1)), ("next", range(b + 1, span.k1 + 1)))`.
- **Issue:** a sentence between two story sentences is never checked for D4 (a), (b) or the cap, and its text is added to `anchor`. The design doc says "each sentence outside that core passes (a), (b), cap". The prompt says "blank = may not be used", so the judge is looser than the hint.
- **Scenario:** range `[*, unrelated sponsor line, *]` passes `adjacent_not_admissible`.
- **Fix:** judge every non-core `k` in `k0..k1` against its nearest core sentence. The approved Yahoo middle sentence ("But I don't check it…") contains "it", so it should still pass (a).

**4. MEDIUM | `_lineup` G6 with `select_by_id._ask`**
- **Code:** `hit = _delivered(sp, ctx.ledger)`; `PLAIN["already_delivered"] = "this story was already delivered"`; `reason = entry["rejected"] = str(e); continue`.
- **Issue:** identity is per sentence, and the rejection is re-asked. DEC-9 says a delivered event is never selected again.
- **Scenario:** yesterday's evidence was A1 and B1. The reply holds A1 and is rejected; the retry names A2 and C1 (the same event in neighbouring sentences) and is accepted.
- **Fix:** make `already_delivered` final for the group, as a decline is. Alternatively, test all offered sentences of the group against the ledger before the story call.

**5. MEDIUM | `eligibility.states` with `lineup_table`**
- **Code:** `return run >= min(SAME_STATEMENT_RUN, len(statement))`; `stars = [k for k in range(len(S)) if any(E.states(...))]`.
- **Issue:** any sentence anywhere in the video that shares five consecutive tokens with a story statement becomes a `*` and can be the only "story statement" of a clip. Stopword runs count. The line-up table also has no row cap.
- **Scenario:** statement "At the end of the day Bitcoin fell below 74,000…"; twenty minutes later, "At the end of the day Bitcoin is still the best asset of the decade…" is starred and passes `no_story_statement`.
- **Fix:** also require the starred sentence to lie within about `LINEUP_PAD_S` of the story span's own (interpolated) time, or require the run to cover at least half of the shorter side. Cap line-up rows.

**6. MEDIUM | `eligibility.event_names`**
- **Code:** `{t for t in toks if t[0].isupper() and t not in NOT_ENTITY and len(t) >= 2}`, matched with `re.I` in `_anchor_entities` and `backward_reference`.
- **Issue:** the claim's sentence-initial word counts as a proper name and is matched case-insensitively. Today's names came from the derived query's entity list. The parity test only uses a claim that starts with "Bitcoin".
- **Scenario:** claim "As of this morning, Bitcoin is below $74,000." gives the names {As, Bitcoin}. Any neighbour containing "as" then passes D4 (a) as "entity As".
- **Fix:** skip token 0 unless it also appears capitalised later in the claim or matches `BITCOIN_TERMS`. Match case-sensitively.

**7. MEDIUM | `eligibility.Source` defaults and T12**
- **Code:** `file_head: bool = True`, `vod: bool = True`; `gap = (toks[w0].get("start") or 0) - (toks[w0 - 1].get("end") or 0)`.
- **Issue:** no constructor in the diff sets `vod` or `file_head` (`sources_from_universe`, the patch's `word_source`, the proof's `source_of`). S4 can therefore never fire, and every record's first word is treated as a file head. A missing previous `end` reads as 0, giving a large gap that passes `hook_lead`. The module's own rule is "nothing measured is never a pass".
- **Scenario:** a window record (E-FAIL-PS1, if R4 is not applied) is used as a hook from word 0 with no measured lead.
- **Fix:** default both to `None` and fail closed for on-screen roles; pass them from the universe; treat a non-numeric timestamp as `hook_lead` / `adjacent_not_admissible`.

**8. MEDIUM | tests**
- **Vacuous cases in `test_strict_json_and_ids`:** `'{"story": [1, 2], "story": [3, 4], "claim": 1}'` is rejected even without `_no_dup`, because claim 1 is not in [3, 4]. The NaN and `True` cases are likewise rejected by other checks.
- **Conditional assertion:** `if saylor.get("channel_id"):` skips the disabled-channel assertion when the id is absent.
- **Smoke test:** the fabricated-id run accepts any `NoProducibleStory`; the reason is not checked.
- **Proof re-check:** `recheck = E.eligible(...)` re-runs the same predicate on the same objects, so it cannot disagree.
- **Production branch never run:** `ScriptedLLM` has `digest = None`, so `if getattr(L, "digest", None): model = SB.Recorder(... os.path.join(sm.LLM_CACHE_DIR ...))` is never executed. `OllamaModel` over a real `LocalLLM._post` is also never run; the proof used a stand-in model, not gemma3:27b.
- **Fix:** use valid ids in both duplicate values; assert the rejection string; assert "fabricated id" in the held run's `TOPIC_SELECTION`; give `ScriptedLLM` a digest; add one recorded gemma3:27b exchange.

## Unverifiable from the diff

- **Names in the patched function:** `registry` and `os` are used but not visible in the hunk context. `u["_rec"]` must exist on universe entries, or every group is empty.
- **`LocalLLM._post`:** its signature, return type, JSON mode and whether the GPU0 placement guard lives there or in `chat_json`.
- **`now`:** `Context` raises on a naive datetime.
- **Downstream consumers:** whether `select_passages` or `run_fresh` tolerate `score: None`, the reduced `passages["story"]`, and a full sentence returned as the label (`return st.claim.text, rec`).

SCORE: 66/100
VERDICT: NOT READY