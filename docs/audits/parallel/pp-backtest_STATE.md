# pp-backtest — STATE (session pipeline_pp_backtest, worktree ~/worktrees/pp-backtest, branch pp-backtest)

## LIVE STATE (updated 2026-11-12 04:55 ET)

- STATUS: DONE (commit hash in the line below once pushed). Report: docs/audits/BACKTEST_SUPPLY_REPORT.md
  (sections 1-9; hand-written analysis = section 5, from pp-backtest_ANALYSIS.md). Raw artefacts (prompts, raw replies,
  parsed records, spend ledger, A/B files): /home/ultron/heimdall_probe/pp_redteam/oracle/<stamp>/ and .../ab/.
- DONE WHEN, item by item:
  1. Export: 10 saved universes -> BITCOIN_STATEMENTS_<stamp>.jsonl (3,018-5,384 rows each), read as spoken through
     the repo's own transcript_store.read_text / canon / sentence_law (imported); three independent exports
     byte-identical; tested (incl. two processes with different hash seeds).
  2. Blind writer + blind judge for every saved day, with raw artefacts: 10 of 10 AVAILABLE, 16 accepted line-ups
     (gpt-6.1-sol / claude-fable-5-2); strict schemas; malformed / empty = ORACLE_FAILED, never NONE.
  3. Scoring without GPU (HEAD replay CPU-only; gemma steps NOT_RERUN): recall 0 of 6 completed as-run records
     (4 not measured), 0 of 1 completed cold-backtest record, not measured at HEAD; precision not measured (no record
     accepted a line-up); loss stages as run COVERAGE 7, CLUSTER_FORMATION 1, WINDOWS 1, CURRENTNESS 1, NOT_REACHED 6;
     layout column: 3 of 16 die without Bitcoin Magazine.
  4. Report committed and pushed (this commit); tests/oracle 167 passed incl. the must-fail fixtures (empty reply,
     malformed ids, id not in the universe, altcoin smuggled); regression_test.sh 26 PASS / 0 FAIL.
- Notes 01:55 / 02:30: windows HARD 31 accepted / 22 developments; windows as targets 41 / 22; moments 48 (all four
  witness checks keep 7 on 6 of 10 runs); report sections 7-8, analysis 5.5-5.6.
- Note 02:45 (L-x): one provider interface, >= 2 vendors per role, failover, judge avoids the vendor that actually
  wrote, no model name outside the config, local first but only once validated per role (tests). Blind A/B per role
  (section 9, analysis 5.7): grouping has a matching fallback (heimdall-glm 16 of 16); judge and witness fallbacks
  either pass what the reference fails (heimdall-glm, local gemma3:27b) or fail everything (grok-4.7); the local
  writer cannot take a universe (context). Measured local judge (integrator, GPU0 lease): 10 of 25, below the bar ->
  the judge default stays frontier (providers.DECIDED_BY). Local witness: integrator's run still in progress at this
  commit (19 of 48); local grouping: PENDING (REQUESTS R5).
- AUDIT: three rounds on the code, one on tests / docs / report (pp-backtest_AUDIT.md): GPT-4o + Grok-3 (GPT-4o out
  of credit in round 3; Gemini NOT RUN: no key in the main .env, REQUESTS R6) and an independent claude-fable-5-2
  review each round (12 + 16 + 8 + 8 findings); every finding fixed or answered; three changed reported results.
- Spend: 57.40 USD of the 60 USD guard (ledger, per call, Heimdall's own reported cost included). The ledger may
  understate by up to ~0.5 USD: calls in flight in batches stopped by hand before the shared ledger existed (audit
  round 3, A-F3). Heimdall credits 34.2 of 500 (6.8 %: tripwire not reached). The independent audit reviews: 10.34 USD on
  their own ledgers (five claude-fable-5-2 calls, one of them the empty 32k-capped reply).
- Not done here, stated: VO fidelity (no voiceover is written by the backtest); declared remote context windows;
  re-running the target-mode variants with sentences over 20 s shown (lower bounds as reported).
- Stop hook: it audits the MAIN tree and asks to commit files another session is editing there; not touched (B14 / R7).
- BLOCKED: nothing.

## Assumptions (K1; most defensible reading, taken without asking)

- A1 "day" = one saved run (a run dir with a saved universe). Runs are named by their UTC start stamp
  (BITCOIN_STATEMENTS_<YYYYMMDD_HHMMSS>.jsonl); the report also groups them by ET date. Several runs share a
  date and most of a universe; each is exported and scored on its own.
- A2 Transcript records are read READ-ONLY from the main tree's transcript store
  (/home/ultron/protocol_pulse/data/editorial/transcripts) by the exact sha256 each run recorded in its
  TOPIC_SELECTION.json universe (hash-checked on read). The run dirs hold no transcripts themselves (0 files in
  every runs/fresh_*/transcripts); without the store there is no saved universe at all. Nothing is written there.
- A3 "Layout eligibility" = the selector's own predicate editorial_select.layout_eligible (registered channel id
  and not has_chyron: today Bitcoin Magazine and CoinDesk are ineligible). layout_status approved / pending is
  reported beside it for information only (DEC-5: it no longer gates selection).
- A4 The live run (fresh_20261112_050611, started 00:06 ET) is exported from its saved universe (read-only); its
  selector outcome is scored only if its editorial stage has finished when scoring runs, else IN_PROGRESS.
- A5 regression_test.sh needs untracked, gitignored assets (video_pipeline_v3/assets/outro_branded.mp4, music/*.mp3)
  that a fresh worktree lacks (the script stops under set -e at the music glob). They were COPIED (never symlinked)
  from the main tree into this worktree, as the sibling worktree pp-selectid has them; gitignored, never committed.
- A6 Product rules given to both models: the order's six rules plus the format the selector builds (hook 8-12 s,
  2-3 clips of 12-20 s, 1-3 whole sentences, ends on a statement, <= 2 segments per video, <= 2 clips per channel,
  content >= 46.5 s so the video runs >= 60 s with the ~13.5 s credits card and outro). The 01:55 note made the
  windows targets (L-o): both readings are reported. Sentences longer than 20 s (unpunctuated stretches) are hidden
  from every oracle variant (counted per run): this can only undercount supply.

## Saved universes (runs/fresh_* with TOPIC_SELECTION.json universe + transcript shas)

| run | started (ET) | outcome of the run | universe videos | with transcript sha | statements exported (Bitcoin-naming) | shown to the writer (<= 20 s) |
|---|---|---|---|---|---|---|
| fresh_20261106_213852 | Nov 6 16:38 | HOLD | 109 | 96 | 5384 (1641) | 5263 |
| fresh_20261107_065702 | Nov 7 01:57 | HOLD | 112 | 102 | 3751 (1127) | 3657 |
| fresh_20261107_080503 | Nov 7 03:05 | HOLD | 115 | 105 | 5097 (1502) | 4978 |
| fresh_20261110_093150 | Nov 10 04:31 | HOLD (protected preview's day) | 95 | 87 | 3018 (892) | 2945 |
| fresh_20261111_190259 | Nov 11 14:03 | CRASH (E-FAIL-030) | 117 | 96 | 3670 (1206) | 3581 |
| fresh_20261111_192645 | Nov 11 14:26 | stopped (DEC-12) | 117 | 96 | 3738 (1226) | 3647 |
| fresh_20261111_213954 | Nov 11 16:39 | HOLD | 119 | 98 | 3964 (1316) | 3867 |
| fresh_20261112_001448 | Nov 11 19:14 | stopped (E-FAIL-036..038) | 117 | 97 | 3764 (1246) | 3667 |
| fresh_20261112_013452 | Nov 11 20:34 | stopped (21:10 order) | 115 | 95 | 3751 (1248) | 3664 |
| fresh_20261112_050611 | Nov 12 00:06 | HOLD (no candidate producible) | 121 | 109 | 3862 (1272) | 3773 |

No universe saved: fresh_20261106_133059 (old TOPIC_SELECTION format, no universe), fresh_20261106_174439 (no
TOPIC_SELECTION.json), fresh_20261107_064831 (universe empty).
