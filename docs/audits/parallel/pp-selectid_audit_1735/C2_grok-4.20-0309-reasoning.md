# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 30 s finish=stop usage in 19626 / out 1422 usd~0.134 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1735 (Ruling 66 amended + 17:20)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
   GLM's P1-1 on `rewrite_alone`/`write_line` exception path (lines 102–104, 223 in fixed diff) was completely missed in my Cycle 1; I never traced that an `LLMParseError`/`ValueError` before `r.backend` assignment left `avoid_model=None` and could re-hit the same Heimdall model. Qwen's KeyError concern on `cseg[v["segment"]]` was also missed (though refuted). The `_words_in` canonical-token helper (lines 112–118) for precise STRONGER/NOT_ENTAILED attribution was not on my radar.

2. WHERE DO YOU AGREE OR DISAGREE?
   - GLM P1-1: fully agree — the original defect existed; the C1 fix (`e.backend = r.backend`, `getattr(e, "backend", None) or by`, test `test_a_reply_out_of_contract_still_sends_the_second_write_to_the_other_model`) resolves it. The test mutation would fail without it.
   - GLM P1-2 (RUNTIME on "-" possibly bridge-driven): partially agree on the conceptual risk but disagree on severity post-fix. `takeaway_budget` + `if b is None: break` (lines 266–270) prevents the write when bridge length is the true culprit; `takeaway_refusal` conservatively treats RUNTIME/R4 as takeaway-own only when length can still move.
   - Qwen P0-1 (KeyError): disagree — guarded by `v.get("segment") in cseg` (line 135) before access; `cseg = (cx or {}).get("segments") or {}` makes it safe.
   - Grok & consensus on no P0/P1 and "SHIP: yes": agree after the C1 model-avoidance fix. Loop termination, merge precondition, no judge changes, and "no gate accepts more" all hold in the fixed diff.
   - GLM P1-3 (merge_fid on stale fid): disagree — `last_fid` is only used when `lone and last_fid is not None` and `not last_rw65` (lines 347–349, 337); `takeaway_alone_gates` re-runs VF on the new takeaway + full CI, satisfying the "kept lines judged in the write that produced them" law.

3. NEW FINDINGS FROM THIS REVIEW
   None at P0/P1. One P2 (diff lines 275, 196–197): `avoid_model={alone_by} if alone_by else None` (and symmetric title path) passes a set containing a backend string. Router `.call(..., avoid_model=...)` and `_skip` treat it as iterable of names, but if the router ever changes to expect a string or list, this set will break avoidance silently. Untested with real router (only mocked in test). Also verified: `LINE_ONLY_WRITES=2` is enforced for title (rewrite_alone for-loop) and takeaway (while-guard + alone_n); `while True` always exits (budget break, success return, alone_n >= 2 break, over_budget, relined, or final `if not out["packages"]` break).

4. REVISED SCORES
   | Subsystem                  | Cycle 1 | Cycle 2 | Why changed |
   |----------------------------|---------|---------|-------------|
   | Loop termination & limits  | P1      | P0      | Explicit `if lone and not (alone_n < LINE_ONLY_WRITES ...): break` + `alone_n += 1` before write makes infinite-loop impossible; my prior concern refuted. |
   | Model avoidance on error   | P2      | P2      | GLM's finding valid; now fixed but still P2 because provider-failure-with-no-reply leaves model unknown (edge remains). |
   | takeaway_refusal attribution | P1    | P2      | `_words_in` + budget guard + dedup logic tighter than I realized; false-positive "alone" now impossible to verify in diff. |
   | merge_fid / kept verdicts  | P1      | P0      | Precondition (`last_fid` only set after paid gates, `not last_rw65`, re-run CI) holds in all paths shown. |
   | Ruling 65 unchanged        | P0      | P0      | Byte-identical prompts for non-takeaway; caption path untouched; title now gets exactly the two writes promised. |

5. FINAL PRIORITY LIST
   **P0: None.**
   **P1: None.**
   **P2 (file:line):**
   - pipeline/package.py:275 (and 197): `avoid_model={alone_by}` uses a set; router contract expects iterable of strings or None. Concrete scenario: if router changes `_skip` to `if avoid_model and backend in avoid_model` (instead of `for am in avoid_model`), avoidance works; but any `isinstance(avoid_model, set)` guard or JSON serialization would break the "second attempt on the other writer model" guarantee. Test only exercises the mocked path.
   - pipeline/package.py:130–140 (`takeaway_refusal`): RUNTIME/R4 on "-" is attributed to takeaway even if bridge text (kept) is the real length culprit. Mitigated by `b is None` break, but the refusal entry still reaches the writer prompt unnecessarily (minor prompt pollution).

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   The `takeaway_refusal` + `last_fid`/`last_rw65` gating in the `while True` loop (lines 335–337, 360–362, 347–351) so that only true takeaway-only failures trigger the two alone writes while preserving all prior gate results via `merge_fid` and `takeaway_alone_gates`.

7. PRODUCTION READY?
   Yes with conditions: (a) the new `TestRuling66Amended` tests (especially model-avoidance and out-of-contract paths) must pass against real Heimdall backends in CI, not just the mocked VF/CI; (b) production monitoring must confirm the extra alone writes do not increase average cost beyond the expected <2 % (two extra calls only on takeaway-only failures); (c) the P2 avoid_model set usage should be changed to a list or the router's documented type before merge.

**P0: None. P1: None. P2: two minor issues above (avoid_model set, RUNTIME attribution).**
SHIP: yes with conditions (real-backend test passage + monitor cost + trivial avoid_model list cast)