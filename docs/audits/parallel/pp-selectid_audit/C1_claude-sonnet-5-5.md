# claude-sonnet-5-5 (effort high) 281 s stop_reason=end_turn usage=in 112645 / out 37543

## Short answers

- **Q1 (fail-open):** I found no path by which a non-id reply is accepted.
  - `parse_reply` requires one `{...}` object. It rejects duplicate keys (`_no_dup`), NaN/Infinity (`parse_constant`), and concatenated objects (`json.loads` raises "Extra data").
  - `_keys` rejects extra or missing keys.
  - `_id` uses `type(x) is not int`, which excludes bools, floats and strings. `Table.row` repeats the type check.
  - `Table.span` rejects cross-source ranges and k-gaps.
  - `check_story` and `check_lineup` reject one-channel stories and one-channel line-ups. `eligible()` then re-judges the whole selection.
  - Any exception (`ModelError`, `SpendLimit`, `ReplayMiss`, or an unexpected exception) never returns "accepted".
  - The fail-open holes are in the predicate's rules (D1, D2, D3 below), not in id handling.
- **Q3 (verbatim):** I found no path from model text to the claim, a segment, passages.json or the ledger.
  - The only keys the model can return are ids.
  - The claim, hook and clip text come from `Span.text`, which is `read_text` of record tokens.
  - Raw replies only reach `attempts[].raw` in TOPIC_SELECTION, which is forensic.
- **Q2, Q4, Q5:** see the defects below.

## Defects

**1. MEDIUM | eligibility.py `_anchor`**
```python
a, b = min(core), max(core)
anchor = spoken(toks[S[a][0]:S[b][1] + 1])
for d, ks in (("prev", range(a - 1, span.k0 - 1, -1)), ("next", range(b + 1, span.k1 + 1))):
```
- **Issue:** The "core" is treated as the whole range min..max. A sentence between two story sentences is never run through D4 (a), the 8 s rule (b) or the cap. The design doc (T13) says every sentence outside the story statements must pass.
- **Failing scenario:**
  - The story ids are sentences k and k+2 of one video, and k+1 is an off-topic remark that is not an interjection.
  - The span [k, k+2] passes T9, T10 and T13 with k+1 unchecked.
  - That is looser than today's adjacency rule.
- **Fix:** Loop over every sentence in `k0..k1` that is not itself a story statement. Check it against the nearest core edge, or require the core to be contiguous.

**2. MEDIUM | eligibility.py `_span` (T12) and `_anchor`**
```python
gap = (toks[w0].get("start") or 0) - (toks[w0 - 1].get("end") or 0)
st = toks[S[k][0]].get("start") or 0
t_a, t_b = toks[S[a][0]].get("start") or 0, toks[S[b][1]].get("end") or 0
```
- **Issue:** A missing timestamp is read as 0, so it counts as a pass. This violates the "unmeasured fails closed" rule (L-j, M12) that the module docstring itself states.
- **Failing scenario:**
  - The word before a hook has `end=None`. Then `gap = start`, say 95 s, and `hook_lead` passes without a lead being measured.
  - A neighbour sentence with `start=None` gives `gap = 0 - t_b`, which is negative. D4 (b) passes, and the "within 8 s" check is never made.
  - The duration check only requires the span's own first and last words to be numeric.
- **Fix:** If any timestamp used in a gap is not an int or float, add a named reason (`hook_lead` / `adjacent_not_admissible`: "not measured").

**3. MEDIUM | eligibility.py `Source.file_head: bool = True`, and the patch's `word_source`**
- **Issue:** The default says "the first token is the media's first word". The patch builds `EL.Source(...)` for word records without passing `file_head`. The `words_fn` hook can return a record that is not a full-video record. REQUESTS R4 describes exactly that for `backtest._run_transcript`, and it is presented as optional.
- **Failing scenario:**
  - A backtest `words_fn` returns a window transcript.
  - T2 then accepts the window's first word as a sentence start.
  - T12 skips the lead measurement at `w0 == 0`.
- **Fix:**
  - Default `file_head` to False, so a source has to assert it.
  - `word_source` should set it only for full-video store records.
  - Make R4 a prerequisite of R1.

**4. MEDIUM | select_by_id.py `OllamaModel.complete` and the patch's `_select_story`**
```python
return self.llm._post(prompt, max_tokens, seed), {...}
```
- **Issue:** `_ask` catches only `ModelError`, and only the proof stand-ins raise it. Any error from the production adapter's `_post` call propagates out of `run_pools` and `select_story`. I cannot see which exception types `LocalLLM._post` raises. The patch has no try/finally, so `L.stop()` and `E.close()` are skipped. This contradicts the `ModelError` docstring ("network, HTTP...: nothing selected").
- **Failing scenario:** The Ollama call times out. The run dies with a traceback instead of `NoProducibleStory`, and the GPU0 Ollama and embedder stay loaded.
- **Fix:** Wrap `_post` in `OllamaModel.complete` and map failures to `ModelError`. Put `L.stop()` and `E.close()` in a `finally`.

**5. MEDIUM | REQUESTS patch, ledger and gates (law L-f / DEC-13 d)**
- **Issue:**
  - The patch removes `e["gate"] = why` for skipped pools and `_close_cluster_ledger`.
  - It sets `emergent[i]["gate"]` only for groups that appear in `res["groups"]`. Clusters after the winner in its pool, clusters in later tiers, and the wire candidates' `decision` get no gate.
  - The per-cluster `claim` and counted quotes are no longer written.
  - Gate strings read `st.get('why')` / `lo.get('why')`, but `Outcome.to_dict()` has no `why` key. An evaluated cluster's gate is therefore "story rejected: " or "line-up declined: " with no reason.
- **Failing scenario:** A 48h cluster selects a story. The 72h clusters end with no gate, and L-f's "every cluster's ledger entry names ... the gate that stopped it" fails.
- **Fix:** Set a gate for every `emergent` entry (default "not evaluated: <pool> produced a story"). Fill `why` from the last attempt's `rejected` or `eligibility`.

**6. LOW | REQUESTS patch, undefined or unverifiable names**
- **Issue:** The patch uses `registry` (`EL.Context(now, registry, ...)`) and `os.path.join`. Neither is visible in the replaced hunk, and the removed code only used `by_cid`. I cannot confirm either is defined in `_select_story`.
- **Failing scenario:** If `registry` is not a local, the patched function raises `NameError` before any selection.
- **Fix:** Build the registry from `by_cid.values()`, and confirm `import os` at module level.

**7. LOW–MEDIUM | select_by_id.py `lineup_table` and `LINEUP_PROMPT`**
- **Issue:** `story_table` is capped at `STORY_MAX_ROWS`. `lineup_table` has no row cap, and the instructions come after `<sentences>`.
- **Failing scenario:** Several starred sentences, each with ±30 s of rows over three videos, exceed `LLM_CTX`. A silently truncated prompt can lose the "Return ONLY this JSON" instruction.
- **Fix:** Cap the line-up rows, keeping the stars and their nearest neighbours. Assert the prompt length against the context.

**8. LOW | tests that can pass vacuously**
- `test_strict_json_and_ids` asserts only `status == "rejected"`. The `story=[ids[0], True]` case would also be rejected if bools were accepted as id 1. This holds if row 1 and `ids[0]` are both DataDash rows (the `starts[1]` comment suggests row 1 is DataDash), which would give a one-channel story.
- `test_partner_identity_v2f_vod` only exercises the disabled-partner case `if saylor.get("channel_id")`. It is skipped if Saylor has no id.
- `test_every_plus_mark_holds...` hard-codes row ids `[1, 55, 56, 89, 110]`.
- The "must-pass preview" test feeds the model the approved ids from a scripted model, so it proves eligibility accepts them, not that selection finds them.

## Verdict

SCORE: 72/100
VERDICT: NOT READY. The id contract is tight. Defects 1 and 2 make the predicate looser than its own spec, and 4 and 5 break fail-closed and ledger behaviour in the wiring.