# claude-opus-5-5 (effort high) 215 s stop_reason=end_turn usage=in 73056 / out 21615

# pp-selectid: Cycle 2 audit (chunk B: tests, proof and docs of the fixed diff)

**About my Cycle 1 output.** The "YOUR CYCLE 1 OUTPUT" slot in this package is empty: it holds only the placeholder "[See below — you wrote this]". I cannot quote, defend or score against text I cannot see. I treat the three Cycle 1 reviews and the consensus as the baseline, and I review chunk B on its own.

**Scope.** Chunk B contains:
- `SELECT_BY_ID_DESIGN.md`
- `BIBLE_ADDITIONS.md`
- `test_eligibility.py`
- `test_select_by_id.py`
- `proof_saved_runs.py` and `proof_table.py`
- `smoke_wiring_patch.py`
- `standins.py`

`eligibility.py`, `select_by_id.py` and the REQUESTS patch are in chunk A, which I cannot see. Any claim about them is inferred from what the tests assert and is marked **UNVERIFIED**. I ran nothing.

---

## 1. What the others caught that the baseline Cycle 1 may have missed

All three Cycle 1 reviewers converged on five points:
- **The D4 "sandwich":** a non-story sentence between two story sentences was never checked.
- **Missing timestamps read as 0.**
- **R1 dropping today's model gates.**
- **Transport errors escaping the Ollama adapter.**
- **Vacuous tests.**

Fable alone found two more:
- **The Recorder** caches unvalidated replies and its key omits the seed.
- **The retry loop** can route around the ledger rule.

Opus alone found that **`registry` and `os` were undefined** in the patch hunk.

I cannot say which of these my Cycle 1 text missed, because I cannot see that text.

---

## 2. Agreement and disagreement with Cycle 1 findings, judged against the fixed chunk B

| Finding | Status in chunk B | My position |
|---|---|---|
| **U1** sandwich skipped D4 (Fable 3, Opus 1, Sonnet 1) | Consensus says fixed in `_anchor`. **No regression test is visible.** `test_anchor_and_adjacency` (488-500) tests only neighbours to the right of a single anchor. The only sandwich exercised is the passing Yahoo range (1757: `yah_rows[0], yah_rows[-1]` with "But I don't check it…" between them). | **Agree with the finding; the fix is unproven.** The must-fail half of U1 has no test. |
| **U2** missing time read as 0 (Sonnet 2) | `test_a_missing_word_time_is_no_measurement` (514-531) covers the hook lead and D4 (b). The index arithmetic is correct: `toks[5]` is "Asia.", `toks[-9]` is "That". | **Agree, mostly fixed.** "duration: not measured" for a missing span start or end is not tested. |
| **U3** ledger gates and INFRA_HOLD | The smoke test (1299, 1323) checks only `emergent_clusters[0]["gate"]`, with a single synthetic cluster (1278). | **Partially verified.** The "not evaluated" gate for later clusters and pools, and the INFRA_HOLD path, are never exercised. |
| **U4** vacuous tests | `test_strict_json_and_ids` (1891-1906) now asserts per-reason messages. The disabled-partner check is unconditional (397). `row_of` replaces hard-coded ids. | **Agree, fixed.** |
| **M1** R1 drops floors, verify_support, verify_reaction (Fable 1, Opus 2) | Floors are superseded by L-o. `ModelChecks` test (1945-1998) covers past→rejected, undecidable→model_error, NEW_SUBJECT→rejected, and asks only non-statement segments. | **Partially agree.** The checks work, but see N1 (L-o not applied downstream) and N4 (`checks` appears optional). |
| **M2** transport errors escape and no `finally` (Opus 3, Sonnet 4) | Test 2007-2022: `URLError`→model_error, GPU0 `RuntimeError` propagates. | **Partially agree.** See N5: the discrimination is by exception type and the test uses urllib's type, which may not be what `LocalLLM._post` raises. The `finally` close is not asserted anywhere (FakeEmbedder.close and ScriptedLLM.stop are no-ops with no counters). |
| **Fable 2** Recorder caches before validation; seed not in key | Test 2024-2039: seed is now in the key, and an empty reply is not written. | **Only half fixed, as far as the test shows.** Nothing tests that a non-empty but rejected reply (prose, fabricated id) is not cached. If it is cached, a rerun replays the same rejected chain without asking the model, which breaks L-l and L-f(e). Production Recorder is UNVERIFIED. |
| **Fable 4** ledger evaded by retry | `test_an_already_delivered_story_is_final_for_the_group` (1934-1943): a delivered member now gives a final decline. | **Partially agree.** It is closed within a group. A later group or pool (72 h, wire) can still pick other sentences or videos about the same delivered event, because identity is per statement (design G6, line 144). Today's DEC-9 is worded per event. This should be disclosed as a narrowing. |
| **Sonnet 3** `file_head` default | Every test source now passes `file_head=True` explicitly (295-299, 631, 790). | **Likely fixed.** The default in `eligibility.py` is UNVERIFIED. R4 stays an integrator prerequisite (BIBLE PS1). |
| **Opus** `registry` / `os` undefined in patch | The smoke test now applies and runs the patch end to end. | **Probably resolved, but no smoke or pytest output is in the package.** |

---

## 3. New findings (not raised in Cycle 1)

**N1. L-o loosens selection while validation is described as unchanged, which reopens the selection/validate disagreement the design exists to remove.**
- Under L-o the predicate now accepts three things the old windows refused:
  - a hook or clip opening on a conjunction: tests 461-462 and 539, where "so …" is only a target;
  - a 2-3 s hook: test 472-474, `assertNotIn("duration")`;
  - a 35 s span: test 685.
- The design doc says stand-alone at validate is "unchanged (downstream of the EDL)" (line 167). Its own section 4 lists validate-time rules that reject these cases:
  - T8 (line 127): stand_alone.py rejects a hook conjunction;
  - T10 (line 129): edl_rules R5 8-25 s and select_passages:333.
- Unless the chunk A patch also changes stand_alone, edl_rules and select_passages (UNVERIFIED), select_by_id will choose line-ups that the run holds after the word pass and the cut. That is exactly the class described in E-FAIL-PS4 (line 219).

**N2. The design doc and BIBLE are stale against the fixed code.**
- T8 (127) and T10 (129) still describe rejection, not targets.
- Section 4.4 (146-154) has no runtime 60-70 s row (`runtime` reason, tests 562-566).
- Section 5 (162-166) still says verify_support and verify_reaction "MAY" or "the integrator may keep" them, and that floors stay "(DEC-13 kept hook >= 4.0)". Both are superseded by M1 and L-o.
- Line 71 gives the Recorder key as `sha256(model, prompt, max_tokens)`; the seed is now in it (2031).
- Section 6 (169-172) has no content.
- `standins.py` docstring (1373-1376) names GeminiStandIn as the substitute, but `main` uses AnthropicStandIn and GrokJudge (1012-1013).

**N3. The must-pass test no longer reproduces the PBX-approved line-up, and that is not flagged for PBX.**
- Test 1769-1771 asserts that the approved trio is now rejected (`runtime`, ~54.4 s).
- The test and the smoke test (1283-1288, 1311) instead accept a fourth clip that PBX never approved: "Bitcoin slips below Strategy's 75,451 … And I keep seeing stories". It is a second, back-to-back Yahoo Finance clip.
- L-d (approved preview) and L-o (60-70 s) now conflict once DEC-12d removes Bitcoin Magazine. That is a PBX decision, not something a test rewrite should settle silently.

**N4. `checks` looks optional: omitting it silently skips two of today's gates.**
- Most tests call `choose_story` and `choose_lineup` without `checks` and get acceptance (1743, 1759, 1774).
- If the production entry `run_pools(..., checks=None)` also has that default (UNVERIFIED), an integrator who forgets the argument loses verify_support and D4 (c) with no error.
- Production paths should make it a required argument. Tests can pass an explicit no-op that is named as such.

**N5. The adapter decides "transport error versus GPU0 guard" by exception type.**
- The test uses `urllib.error.URLError` and `RuntimeError("LLM runner not on GPU0 only")` (2018-2022).
- Two cases would crash the run instead of recording `model_error`:
  - if `LocalLLM._post` raises httpx errors (not `OSError`);
  - if it raises `RuntimeError` for a non-guard reason such as an Ollama HTTP 500.
- Fix: the test should use whatever `LocalLLM._post` actually raises (UNVERIFIED). The guard should be a dedicated exception class.

**N6. The production model was never run against the contract.**
- Every proof reply came from claude-fable-5-2 (generator) and Grok (judge).
- The design says LocalLLM's lenient JSON repair is deliberately not used (line 70), and the strict parser rejects code fences (test 1875).
- `AnthropicStandIn` ignores `max_tokens` and `seed` (32k output, 1576), so the proof never exercised the token budget gemma3:27b will get.
- If gemma fences its JSON or truncates, every group is rejected three times and every run holds. Whether `_post` sets Ollama `format: json` is UNVERIFIED.
- The three Cycle 1 reviewers are from the same vendor as the generator stand-in, so the proof and its review are not independent.

**N7. The claim and the hook now apply different opener rules, and the doc does not say so.**
- The claim "But that said, Bitcoin fell…" is rejected (`claim_not_standalone`, 590-594).
- A hook "so bitcoin…" only misses a target (534-539).
- Design G5 (143) says the claim stands on its own "like a hook (T7 / T8)", which is no longer true after L-o. Being stricter is acceptable, but it must be written down.

**N8. The reply-word exception relies on a scorer that R1 likely never runs.**
- The opener exception needs `ctx.scorer` with a score of at least 3.5 (466-469).
- R1 no longer runs `rate_passages` (floors superseded), so `scorer` is presumably empty in production. Every "Yeah, …" clip then fails closed, which makes the exception dead code.
- Using 3.5 as a gate also arguably conflicts with L-o ("score floors rank, never reject").
- PBX should rule on it, or the doc should note it is dead.

**N9. Gaps in the proof and tests.**
- **Weak re-check:** the eligibility re-check in `finish` (906-907) uses a fresh `Context` with no ledger, no `event` and no checks. The "second angle" cannot see `already_delivered`.
- **Untested reply shapes:** no test covers a line-up range with `last < first`, a 1- or 3-element range, or a bool or float id inside a range. The design lists these (line 44).
- **Unpinned `enabled` flag:** no test pins that every active `channels.json` partner has a boolean `enabled`. With "absent = not enabled" (107), a registry entry missing the key silently drops that channel's supply.
- **Hard-coded path:** the proof reads `MAIN = "/home/ultron/protocol_pulse"` (740), not the worktree, so it cannot be reproduced in CI.

**N10. The runtime rule rests on an estimate.**
- The hard 60-70 s rule (L-o) is judged on `runtime_s_estimate`: 37.5 s of speech is estimated at ~50 s (562-566). Its constants are in chunk A and UNVERIFIED.
- Unless the rendered timeline is re-checked against 60-70 s (UNVERIFIED), the hard rule is only enforced on a guess. That is close to the L-m concern that nothing measured is never a pass.

---

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Reply contract / parsing (via tests) | n/a (my text not in package) | 85 | Per-reason assertions, decline finality, gap ranges and prompt neutralisation are all tested. A few range shapes are untested (N9). |
| Eligibility predicate (via tests) | n/a | 72 | U2, layout, freshness and L-o targets are tested. There is no sandwich must-fail (U1), and the L-o / validate mismatch remains (N1). |
| Model calls: adapter, Recorder, ModelChecks | n/a | 62 | Seed is keyed and transport is mapped. Caching of rejected replies is unproven, guard discrimination is by exception type, and `checks` appears optional (Fable 2, N4, N5). |
| R1 wiring (smoke) | n/a | 65 | The patch runs end to end with a fabricated-id hold. One cluster only; `finally`, INFRA_HOLD and "not evaluated" are unexercised; no output log is attached. |
| Proof / stand-ins | n/a | 55 | The proof is thorough on resolution and re-check, but has never touched gemma3:27b, the re-check is weak, and the path is hard-coded (N6, N9). |
| Docs (design, BIBLE) | n/a | 50 | Stale against M1, L-o, the seed key and runtime; section 6 is empty; the L-d / L-o conflict is undisclosed (N2, N3). |
| **Overall** | consensus 66-72 | **63** | Fail-closed and verbatim properties hold. Readiness rests on unrun production-model behaviour and on downstream alignment. |

---

## 5. Final priority list

### P0: ship blockers

1. **Run gemma3:27b through `OllamaModel` before merge (N6).**
   - Use the saved universes and the preview, with production `max_tokens` and seeds.
   - Record the per-attempt validity rate and the reasons replies were rejected.
   - If fenced or prose replies dominate, use Ollama JSON mode in the adapter. Do not add repair.

### P1: high

2. **Align L-o downstream or hold it back (N1).**
   - stand_alone (hook conjunction), edl_rules R5 (8-25 s) and select_passages:333 must accept what eligibility now accepts. Otherwise eligibility keeps the old windows until they do.
   - Enforce 60-70 s on the rendered timeline, not only on the estimate (N10).
3. **Recorder: cache only accepted or declined replies (Fable 2).**
   - Add a test that a non-empty rejected reply (prose, fabricated id) is not written and is asked again on rerun.
   - Extend test 2024-2039.
4. **Add a sandwich must-fail test (U1):** `[* , "Meanwhile the weather turned cold in Chicago.", *]` → `adjacent_not_admissible`, next to the passing Yahoo case.
5. **Take the L-d / L-o conflict to PBX (N3):** the approved trio is now rejected, and the must-pass test accepts an unapproved fourth Yahoo clip (1769-1776, 1283-1288).
6. **Make `checks` required on the production entry (N4).**

### P2: medium

7. **Make GPU0 guard detection independent of exception type (N5).** Use a dedicated exception class, and test with LocalLLM's real transport exceptions.
8. **Extend the smoke test:**
   - two or more clusters, asserting the "not evaluated" gate;
   - an injected word-pass failure, asserting HOLD (infrastructure);
   - counters on `stop` and `close` to prove the `finally`;
   - the run's output attached to the package.
9. **Bring the design doc up to date (N2, N7, N8):**
   - T8, T10 and section 4.4 (runtime row);
   - section 5 (ModelChecks, floors superseded);
   - line 71 (seed in the key);
   - section 6 (content);
   - G5's stricter claim opener;
   - the dead reply-word scorer exception;
   - the `standins.py` docstring.
10. **Disclose the cross-group ledger narrowing (Fable 4):** delivered identity is per statement, not per event (G6, line 144).
11. **Strengthen tests and the proof (N9):**
    - range shapes (`last < first`, 1 or 3 elements, bool id in a range);
    - pin `enabled` for every registry entry;
    - duration "not measured";
    - give `finish` the run's ledger;
    - replace the hard-coded `MAIN` path.

---

## 6. The single highest-leverage change

Before merging R1, run the patched path end to end with the real gemma3:27b through `OllamaModel` on the saved universes, because every proof reply so far came from a frontier stand-in and the strict no-repair parser could turn every production run into a hold.

---

## 7. Production ready?

**No.** It becomes "yes, with conditions" when all of the following hold:

1. A gemma3:27b dry run on at least the 10 saved universes plus the preview yields an accepted, eligibility-re-checked line-up wherever the stand-in did. Any shortfall must be explained by named rejection reasons, not parse failures.
2. Downstream validators agree with eligibility under L-o (or L-o is deferred), and 60-70 s is checked on the cut.
3. The Recorder never serves a rejected reply, proven by a test.
4. The U1 must-fail test exists and passes, and the smoke and pytest logs for chunks A and B are attached.
5. PBX has ruled on the four-clip line-up that replaces the approved preview, and on the dead reply-word scorer exception.

What is already good enough to keep: no path in chunk B lets a non-id reply, a fabricated or cross-source id, or a one-channel story or line-up be accepted. Every text that leaves the module is `Span.text` of source tokens. These conclusions agree with all three Cycle 1 reviewers.