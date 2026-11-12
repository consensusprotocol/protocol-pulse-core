**Q1: CORRECTNESS**  
Yes for all changed functions visible in the diff. `_tok`, `_lc_words`, `_numbers`, `align_quote` and `_norm` now delegate to `canon.*` (lines 11-12, 23-25, 36-37, 44-45, 173-174) exactly as their new docstrings require; no time/index arithmetic, unit conversions or clip-state mutation appears. `select_story`/`_select_story` accept optional `transcript_fn`/`words_fn` and route through them without calling `ts.acquire` or Whisper (lines 83, 92-98, 446). `preflight.py` and `backtest.py` contain only explicit early returns or `NoProducibleStory` on missing data; no silent `except: pass` paths that could emit PASS. `pulse_check_run.sh` now runs preflight before `run_fresh` and gates delivery on `release_auth` (lines 236-241, 248-250). All relative `sys.path` fixes (lines 110, 115, 128, 141, 154, 187) are deterministic within the checkout.

**Q2: LAW COMPLIANCE**  
- L-k (ONE CANONICAL FORM): COMPLIANT — every text path now routes through `canon` (cited lines above).  
- L-e (PUNCTUATED BEFORE READ): COMPLIANT — `sentence_ready` guard and `words_fn` path preserved (lines 92, 370).  
- L-j (RELEASE ON THESE BYTES): COMPLIANT — preflight + `release_auth` + attestation ordering added (shell lines 236-241, 248).  
- L-d (protected preview), SELECTION LOCK, SNAP LIMIT, ONSET/TAIL, CREDITS, L-a/b/c: no code touching cut points, EDL locks, edge fades or avatar rings is present, so unchanged.  
- No gate threshold, comparison or v2f reference path is altered. No path can move a cut outside a locked sentence or recompute first/last words after selection.

**Q3: TESTS**  
`test_backtest.py` and `test_preflight.py` exercise the new hooks: saved-day discovery (priority order), word-source fallback, `transcript_fn`/`words_fn` preventing acquisition/GPU release, exception-as-fail, foreign-job detection, dirty-git detection, secret leakage, wrapper ordering, and disabled-channel avatar tolerance. Assertions are concrete (exact strings, call counts, exit codes) and would fail on vacuous success. Must-fail fixtures are not present in this diff (they live in the referenced `test_pulse_20261110_mustfail.py`).

**Q4: VERDICT**  
No defects.  
READY