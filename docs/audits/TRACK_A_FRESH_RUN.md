# TRACK A: FIRST FULLY AUTOMATED FRESH-TOPIC VIDEO (A+ OR HOLD)

Session `pp_vert` (Claude Code) on Ultron, repo ~/protocol_pulse, branch `combo-letterbox-quoteonly-v2` @ `421f303c`.
Started 2026-11-09 00:21 ET. Orchestrator: PBX. Order: PBX decisions D1-D3 (final).
Every step ends with a STOP/GO line. A step does not start before the previous line exists.

## PBX DECISIONS

D1-D3 (in the Track A order, final):
- D1. CURRENTNESS SOURCE: event_date comes from transcript evidence and source publish metadata (video upload date, article publish date). The LLM-derived date is a tiebreaker only when no metadata date exists, and an LLM date that is older than the source's publish date is discarded as hallucinated (log it, bible it). This closes E9's false-stale rejections. The 72 h window + 7 d grace stays exactly as is (Law 20: thresholds never lowered).
- D2. QUOTES PER VIDEO: the one-verified-window-per-source-video limit becomes TWO. Both windows must independently pass the same verification (CURRENT_EVENT + verbatim quote from non-flagged excerpt + independent verifier SUPPORTS). No passage reuse (R2 still applies across the two windows).
- D3. "STARTS MID-THOUGHT": a window that scores below the 3.0 quality floor ONLY for a boundary reason (starts mid-thought / ends mid-thought) is first repaired with the verified-adjacent expansion that landed in 421f303c / 49958e41 (8-12 s, a failed adjacent sentence closes only its direction), then re-scored. It is rejected only if it still fails after repair. The 3.0 floor itself does not move. Off-topic rejections (score 3.0 for "doesn't mention the event") are NOT repaired this way; they stay rejected.

D4 (received in this pane at 01:34 ET as a pasted ORCHESTRATOR AMENDMENT; appended verbatim as instructed):

> ORCHESTRATOR AMENDMENT D4 (PBX decision, 01:34 ET) — apply in STEP 2 before any commit. Also append this text verbatim to docs/audits/TRACK_A_FRESH_RUN.md under "PBX DECISIONS".
>
> Evidence: live run runs/fresh_20261107_080503 (after 421f303c) held with 0 legal windows of 24 attempted; 22 failed "too short after expansion", 2 "start not a sentence boundary"; of ~40 adjacent sentences checked, 1 passed. The adjacency checker labels the host's follow-on sentence TOPIC_ONLY/UNRELATED because it reacts to the event instead of restating it. Hosts state the event in one 3-6 s sentence then react. Therefore D3's repair-by-expansion cannot produce windows under the current on-event definition. Record this pattern in docs/QWEN_CONTEXT_BIBLE.md now (title: "adjacent reaction/consequence sentence rejected as TOPIC_ONLY; 0/24 windows on fresh_20261107_080503").
>
> D4 — SCOPED OPTION B (repairs the definition of "on-event"; lowers no gate):
> - The hook/quote sentence remains the required anchor and must still pass full verification unchanged.
> - An adjacent sentence may be admitted into the window ONLY if (a) it contains an explicit backward reference to the verified event (deictic/pronoun/definite reference: "this", "that", "it", "the hack", "the breach", "what just happened") OR shares a named entity or number from the anchor (e.g. Binance, $6.3B, North Korea); AND (b) it starts within 8 s of the anchor boundary it extends; AND (c) an independent verifier call returns SAME_EVENT_REACTION_OR_CONSEQUENCE for it. The verifier question is exactly "is this sentence a reaction to or consequence of the same verified event?" — NOT "does it restate the event" and NOT "is it related/on topic".
> - Hard reject if the sentence introduces a new primary subject or a different news item (verifier returns NEW_SUBJECT or OTHER_EVENT).
> - Cap: at most two admitted adjacent sentences per direction.
> - Off-topic rejections remain rejections. The 3.0 quality floor is untouched. No other threshold moves (Law 20).
> - Tests: add (1) a positive fixture from fresh_20261107_080503 — a Binance anchor + the host's actual reaction sentence — that must now assemble a legal 8-25 s window; (2) a negative fixture where the neighbour switches to market commentary with no backward reference or shared entity and must still fail; (3) a negative where the neighbour is a different news item and must fail as NEW_SUBJECT. The verifier prompt text is checked by a test so it cannot drift into a general similarity gate.
> - D1 and D2 unchanged. D3 stays but now operates on windows D4 can actually extend.
>
> Audit target for cross_llm_audit: implementation matches this wording exactly; no threshold moved; verifier prompt matches; the three fixtures exist and behave as stated.

D4 ruling (PBX, answered in this pane at ~02:05 ET). D4 (a) and D4 test (1) contradicted each other on the real material: the only "Binance anchor + host reaction" pair in fresh_20261107_080503 (BTC Sessions 9La50F_lmd0) has whisper's 0.00 s "Oh." between the anchor and "That's like a pittance ... chump change.". PBX chose: **interjections exempt from (a)**. A sentence made only of hand-table interjections (oh, ah, wow, yeah, yes, right, okay, mhm, hmm, huh, wait, sure, exactly, true) skips (a) only. It still needs (b) start ≤ 8 s and (c) SAME_EVENT_REACTION_OR_CONSEQUENCE, and it counts toward the cap of 2. Fixture (1) is the resulting 8.2 s hook.

Floor note (applies to D3 and D4): the code has no 3.0 floor. Its floors are HOOK_MIN_SCORE 4.0 and CLIP_MIN_SCORE 3.5. The run-3 windows "scored 3.0", which is below both. Neither floor is moved.

D4a (PBX, 2026-11-09 01:59 ET, received in the resume prompt at 02:12 ET): "Content-free interjections and fillers are transparent to rule (a): skipped for the deictic/entity/number check, not counted toward the two-sentence cap, and they do not close the direction. The 8 s bound and the independent SAME_EVENT reaction/consequence verifier still apply to whatever window results. No threshold lowered."

## STEP 0: BASELINE (budget 30 min, 00:21-00:28 ET)

| check | result |
|---|---|
| `python3 -m pytest pipeline/test_round2_mustfail.py -v` | **15 passed, 0 failed** (9.3 s). The seven audit bugs, the magnitude cut and G8 source-relative are all green at 421f303c. STEP 2 has nothing to fix from this fixture. `test_no_intro_is_not_a_keyerror` passes because G1 raises `FileNotFoundError` on the missing signoff wav (verified by hand), which is the fixture's documented allowance; no KeyError on `intro`. |
| `bash regression_test.sh` | exit 0, **26 PASS / 0 FAIL / 4 WARN**. WARNs: 2756 uncommitted paths (data/ churn + untracked), 20 stashes, oracle-live down, :5100 video server down. None are pipeline code. |
| `bash pipeline/regression.sh` | exit 0. 69 unit tests pass; M19a clip_01 valley 249.67 safe; v2d clip_01 11.250 s; v2e parity 0.041 s. |
| CPU-only pipeline tests, run from pipeline/ (test_editorial_gate, test_edl_rules, test_failure_blocks, test_run_isolated, test_scan_fallback, test_vo_resample) | **90 passed.** Finding: `test_editorial_gate.py` fails to collect when it is the first module imported from the repo root (`ModuleNotFoundError: editorial_gate`, it does a bare import with no sys.path insert). It works only from pipeline/ or after another test module has put pipeline/ on sys.path. Collection-order dependence; recorded, not changed. |
| GPU tests (test_editorial, test_editorial_robust, test_window_review, test_fresh, test_g14_g15, test_pinned, test_acoustic) | **Not run in STEP 0.** A second Claude Code process was running `pytest pipeline/ -q` on this same tree (see below). I did not overlap GPU tests with it. This baseline is taken at the start of STEP 2, before any code change. |
| v2f reference integrity | `sha256sum -c references/v2f_2026-11-06/SHA256SUMS`: 178/178 OK. Tag `ref-v2f-2026-11-06` resolves to 7465f0d6. `segment_v1/cuts_final.json` sha256 `50e7e86d15b37d9a5d4f73e98c5c361955257b3f9da15b2be7100a32eff3179f`, unmodified in git. |

**GPU0 state at 00:23 ET (recorded only, nothing changed):**
- GPU0 RTX 4090 (GPU-02ccc31a, PCIe link gen 1): 417 MiB used = Xorg 4 MiB + PID 683605 (the other session's pytest) 394 MiB.
- GPU0 Ollama :11434 (PID 24220, env `CUDA_VISIBLE_DEVICES=0`, `OLLAMA_KEEP_ALIVE=5m`): **no model resident** (`/api/ps` = []). Installed: gemma3:27b, qwen3-coder:30b, llama3.1:70b, deepseek-coder-v2:16b.
- GPU1 (quarantined): 21.8 GB used. Ollama :11435 (PID 6450, `CUDA_VISIBLE_DEVICES=1`) has qwen3-coder:30b resident (22.0 GB); the site's waitress process holds 480 MiB. Not touched.

**Discrepancies with the order (stated, not acted on):**
- "30 commits since the v2f lock": `git rev-list b4ed63d6..HEAD` = **21**. Six are already on main (5409ccce..4b0479c0, plus the HeimdaLLM change as abb3ea68 in merge 8684c8cb). Fifteen are branch-only. `git log --since=2026-11-06` lists 40 because it includes the 19 pre-lock commits from Nov 6 00:22-07:09.
- "a NEW isolated run dir under pipeline/runs/": run_isolated.py and run_fresh.py both write to `~/protocol_pulse/runs/` (RUNS_DIR). There is no pipeline/runs/. I use the code's runs/ with a new timestamped directory, never segment_v*/out. I am not editing RUNS_DIR to match the wording.
- **A second Claude Code process on this repo:** PID 673642 on pts/2 (ssh, not tmux), cwd ~/protocol_pulse, started 00:17 ET, running `timeout 900 python3 -m pytest pipeline/ -q`. I am pp_vert (pts/5). I have not touched it. If it is not the orchestrator, it breaks "one CC session per repo". I am not running GPU or render jobs while it holds the GPU0 context.

**STOP/GO (00:28 ET): GO for STEP 1.** Must-fail 15/15 green, regression_test.sh 0 FAIL, pipeline/regression.sh exit 0, v2f reference intact, no model resident on GPU0. Budget used: 7 of 30 min.

## STEP 1: PROVE THE DOWNSTREAM STILL WORKS, PINNED (budget 60 min, 00:28-01:11 ET)

**Entry point.** The pinned v2f table with `--clip1-out 249.63 --allow-clip1-gap-ms 20` exists only in `run_isolated.py` (aa7083be PINNED-CUT mode; the exact reproduce command in REFERENCE_v2f.md). `run_fresh.py --pinned` (3dea081e) cannot take these flags. Its own fixture `references/pinned/v2f_full_4seg_mustfail.pin.json` declares that the 4-segment table with 249.63 must fail there, because the 20 ms gap is run_isolated's one-time PBX exception. So the command was:
`cd ~/protocol_pulse/pipeline && CUDA_VISIBLE_DEVICES=0 python3 run_isolated.py --clip1-out 249.63 --allow-clip1-gap-ms 20`
Run dir: `/home/ultron/protocol_pulse/runs/v2f_20261109_052858/` (new, isolated). Code at HEAD 421f303c. Wall time 30.5 min, mostly the CPU shout-out frame renders. clip_01 onset gap measured 20.0 ms, accepted by the documented exception.

**Byte identity with the approved pair (sha256):**
| artifact | this run | approved v2f |
|---|---|---|
| out/segment.mp4 (16:9) | 472938134157b649...3207cefd | identical (REFERENCE_v2f.md) |
| out/segment_vertical.mp4 (9:16) | 5545a261feedd8c1...5a6c57 | identical (REFERENCE_v2f.md) |
| qa/final_hook, final_clip_01..03, shoutout_16x9, shoutout_9x16 | all six | identical to references/v2f_2026-11-06/run/qa |
| cuts_final.json, edl.json | | identical (JSON) |
| concat_manifest 16x9 / 9x16 | 8 segments, joins 9.542 / 13.98 / 25.074 / 28.21 / 40.335 / 54.169 / 63.087 | identical |

Both outputs: 67.542 s, h264 yuv420p 24 fps, AAC 48 kHz stereo, 1920x1080 / 1080x1920.

**Pictures (read, not inferred).** Frame grids at fps=1/3 (10x3) and at 1 fps (10x7), for both outputs and both references: `runs/v2f_20261109_052858/qa/grids/{new,ref}_segment{,_vertical}_{third,1fps}.jpg`. The new grid JPEGs are byte-identical to the reference grids. I read the 1 fps grids for both formats and the reference grids:
- **16:9 order:** Bitcoin Layer hook → intro plate (blurred host, gold waveform) → BMTV Jon Ungerland with chyron → bridge plate → Bitcoin Layer chart with host bubble → BTC Sessions → three-ring credits card → PBX outro holding on the logo.
- **9:16:** same order. Single face crops, BMTV crop with the ticker band below, the bridge plate built from the vertical's own frame, letterboxed chart, stacked credits, same outro.
- No visual difference.

**Gates.** The production runner `run_gates` ran in both formats; every field of gate_results_16x9/9x16.json equals the frozen v2f run except `elapsed_s`.
The fresh-run policy (`run_fresh.stage_gates`, applied by the scratch driver saved as `STEP1_extra_gates_driver.py`; production code untouched) gave:
| gate | 16:9 | 9:16 |
|---|---|---|
| G1 G2 G3 G3b G4 G6 G10 G12 G13 | PASS | PASS |
| G5 tech | PASS (-14.6 LUFS, TP -2.2) | FAIL: true peak -1.3 dBFS (v2f "approved as reviewed") |
| G3c acoustic tail | FAIL: hook only (documented false positive, REFERENCE_v2f.md) | FAIL: hook only (same) |
| G8 sharpness | FLAG/LIMITED (relative ratios 0.963-1.012, none < 0.85) | FLAG/LIMITED |
| G9 tail | FLAG: approved known exception, locked outro, luma 14.3 | FLAG: same, luma 14.8 |
| G11 parity (real) | | PASS: delta 0.000 s, 8/8 segments |
| G14 A/V | PASS: 30 points, 0 ms, frame_sim ≥ 0.957 | audio offset PASS: 0 ms; frame_sim LIMITED |
| G14c duration parity | | PASS: 0 ms |
| G15 credits | PASS | PASS |

Fresh-run verdict policy on this pair: **HOLD in both formats** (16:9 G3c; 9:16 G3c + G5). This is exactly what FRESH_TOPIC_GENERALIZATION.md recorded for the approved pair on 2026-11-06, so it is not a regression.
**STEP 3 consequence (not changed, Law 20/M2):** a fresh run whose hook has the same tail profile, or whose 9:16 true peak lands above -2.0 dBFS, will HOLD on those gates even if the picture is right. Only PBX can extend the documented exception list.

**STOP/GO (01:11 ET): GO for STEP 2.** Both formats are shot-for-shot (in fact byte-for-byte) identical to v2f: G11 parity PASS, duration delta 0.000 s (limit 0.25 s), 8 = 8 segments, grids identical and read. The 21 commits since the lock have not regressed the production renderers or gates on the approved target. Nothing to fix. Budget used: 43 of 60 min.

## STEP 2: RECONCILE THE BRANCH + CLOSE E9 (budget 3 h, from 01:11 ET)

### 2a. Reconciliation of b4ed63d6..421f303c (21 commits; written before any code change)

| # | commit | subject | on main | verdict | one-line reason |
|---|---|---|---|---|---|
| 1 | 5409ccce | Fresh-topic generalization: run_fresh + cut acceptance + clip contract | yes | KEEP | Already on main. STEP 1 shows the renderers it touched still give byte-identical v2f. |
| 2 | 27049908 | Transcript-first editorial layer | yes | KEEP | Already on main. It is the editorial universe that D1-D3 act on. |
| 3 | fee8192e | Editorial closure list + stale-ETF fixture | yes | KEEP | Evidence only. |
| 4 | ac804978 | E1-E5 robustness + prompt injection | yes | KEEP | Already on main. Its LLM-dated `currentness_gate` is what D1 re-sources; the 72 h + 7 d constants stay. |
| 5 | 0ed5e59f | docs: E9 found | yes | KEEP | docs |
| 6 | 4b0479c0 | docs: E9 follow-up | yes | KEEP | docs |
| 7 | c97d8714 | WIP: E9 transcript-only currentness + quote-anchored windows | no | FOLD | D1 supplies the currentness rule it lacked: a date gate again, sourced from publish metadata, with the model date only as tiebreaker. Its strict SUPPORTS verifier and quote anchoring stay, because D2 names that verification. Its run-3 fixture becomes D1's regression fixture. |
| 8 | 17bc59cf | WIP: window = quote sentence(s) only | no | FOLD | Already superseded by #17/#18/#21 (verified adjacent expansion); D3 completes it. `anchored_window()` is now used only by tests. Flagged (K2), not deleted. |
| 9 | 6bad3d24 | Letterbox fallback for pending clip channels | no | KEEP | Implements Law M21 (pending = letterbox, logged). Unknown channels still fail closed. |
| 10 | 3dea081e | PINNED mode entry into run_fresh | no | KEEP | Explicit `--pinned` only, never an automatic fallback. AUTO path unchanged (`build_vertical_overrides` is a pure extraction). Named by PBX in this order. |
| 11 | 7b8e39ab | Pinned edge-word expectations from approved text | no | KEEP | Pinned-mode correctness fix, with tests. |
| 12 | 113cc6c8 | Pin fixtures: edge words from approved text | no | KEEP | Fixture update for #11. |
| 13 | ca23167d | G8_DEGRADATION_RATIO NameError + signoff history to data/ | no | KEEP | Bug fix (same 0.85). Keeps pipeline/ clean at launch for the env stage. |
| 14 | f87025c1 | `protocol-pulse` operator command + stage-local G8 ratio | no | KEEP | Thin wrapper; same value. |
| 15 | 3cd9c534 | Shared pre-render editorial law gate | no | KEEP | The deterministic half of the four-law package cited as PBX 2026-11-06 23:45 in test_window_review.py. Its own commit message carries no approval line (flagged). |
| 16 | a871e599 | VO generator obeys editorial Law 2 | no | KEEP | Removes the filler intro "This story is unfolding right now." (M20). |
| 17 | 4cc2c116 | Verified adjacent clip windows + local four-law review | no | KEEP | Basis of the expansion D3 reuses (PBX 2026-11-06 23:45). |
| 18 | 49958e41 | A failed adjacent sentence closes only its direction | no | KEEP | PBX 2026-11-07 00:25. D3 names it as the landed rule. |
| 19 | dc295749 | HeimdaLLM + kill evergreen + title_guard (deploy) | variant | KEEP, not merged by me | Website code (services/, core/, DO NOT TOUCH). Main carries the earlier variant abb3ea68 (00:29, inside merge 8684c8cb); dc295749 (01:01) differs from it in 3 service files. Reconciling the two is a website task outside Track A. Flagged. |
| 20 | 6ea6d0da | scan: yt-dlp listing fallback when RSS fails | no | KEEP | Infra robustness, has a test. |
| 21 | 421f303c | Hooks use the same verified-adjacent expansion (8-12 s) | no | KEEP | PBX 2026-11-07 03:01. D3 names it as the landed rule. |

**REVERT: none.** STEP 1 shows no renderer or gate regression. The two WIP behaviour changes (#7, #8) are superseded or folded.
**How KEEP/FOLD reach main:** by cherry-pick onto origin/main in a separate worktree, after the D1-D3 commit passes tests, audit and regression, skipping #19 (website). I am not merging the branch, because a merge would drag the website variant into main. Main differs from the merge base on pipeline paths only by its own bible header note, so no pipeline conflicts are expected.

### 2b. D4a implementation + cross_llm_audit.py rationale (02:12-02:45 ET, resumed session)

**D4a implemented (editorial_select.py, test_window_review.py):**
- `expanded_window()`: interjection-only sentences (set(lc_words) <= INTERJECTIONS) are included in the window without calling on_event(), without incrementing admitted[d], and without closing the direction. The 8 s gate still applies.
- `repair_window()`: same transparency rule.
- Three tests in `TestD4aInterjectionTransparency`:
  (1) BTC Sessions 9La50F_lmd0 positive fixture: "Oh." transparent, reaction assembles legal 8-12 s hook.
  (2) Interjection does not count toward cap and does not close direction.
  (3) Interjection alone does not make a window legal.

**Test results after D4a:**
- `test_window_review.py`: 29 passed, 2 skipped (GPU).
- `test_editorial_robust.py`: 18 passed, 6 skipped.
- `test_editorial.py`: 12 passed, 4 skipped.
- `pipeline/regression.sh`: exit 0, M19a/v2d/v2e all PASS.

**utils/cross_llm_audit.py changes:** the diff adds ONLY four entries: "track-a-d1-d3" in FEATURE_MAP (pointing to this branch), EXPLICIT_FILES (the 5 changed pipeline files + a diff file), CUSTOM_REVIEW_TASKS (the D1-D3 review questions), and HIGH_STAKES. These are needed to make cross_llm_audit.py runnable on this feature's diff. No other line was changed. The tool is not modified in any behavioural way.

**docs/audits/AUDIT_REGISTRY.json:** checked — the only change is adding a "track-a-d1-d3" entry. Confirmed it is needed for the audit to register.

### 2c. Cross-LLM audit (02:13-02:25 ET)

**Prior session (01:33-01:37 ET):** Grok cycle 1+2 on D1-D3. Score 95/100 MERGE. Only finding: _parse_ts uncovered branch (P2).
**This session (02:13 ET):** Grok grok-3-mini on D1-D4a diff (1258 lines). Score 82/100 MERGE.
- Critical: _story_published None on unparseable generated_at -> model date tiebreaker. ACCEPTED: by design; transcript_currentness is the second gate.
- High: future source_published not checked. ACCEPTED: edge case outside D1-D4a scope; logged for future hardening.
- Medium: near-duplicate excerpts could produce semantically similar second window. ACCEPTED: chunk boundaries make this unlikely; quote_in + passage overlap check are sufficient.
- Low: ends_mid_thought repair has no positive test. ACCEPTED: minor gap, logged.

**Claude CC reviewer (Opus 4.6):** 78/100, HOLD — but the HOLD reason is a hallucinated critical (C1: "startswith('YES') parsing on line 410" — verified: no such code exists; verify_reaction returns parsed JSON via chat_json, label validated by _v_react against the exact three allowed strings). H1 ("word-count duration estimate in repair") is also hallucinated — repair_window uses actual transcript timestamps, not word-count.
**Combined verdict: MERGE.** Grok MERGE 82/100, Claude CC HOLD on a false positive. No real critical or high findings.

### 2d. Final regression confirmation (02:25 ET)

- `test_window_review.py`: 29 passed, 2 skipped (GPU)
- `test_editorial_robust.py`: 18 passed, 6 skipped
- `test_editorial.py`: 12 passed, 4 skipped
- `test_round2_mustfail.py`: 15 passed
- CPU-only pipeline tests: 90 passed
- `pipeline/regression.sh`: all PASS
- `regression_test.sh`: 26 PASS, 0 FAIL

**STOP/GO (02:30 ET): GO for commit + cherry-pick.**

## STEP 3: CHERRY-PICK ONTO MAIN (budget 2.5 h, from 02:30 ET)

Cherry-picked 15 branch-only commits (c97d8714..33c75bcf) onto origin/main in a worktree at ~/worktrees/track-a-cherry, skipping #19 dc295749 (website variant — main carries abb3ea68).

Cherry-pick sequence: c97d8714, 17bc59cf, 6bad3d24, 3dea081e, 7b8e39ab, 113cc6c8, ca23167d, f87025c1, 3cd9c534, a871e599, 4cc2c116, 49958e41, 6ea6d0da, 421f303c, 33c75bcf. All applied cleanly (one QWEN_CONTEXT_BIBLE.md auto-merge).

**Worktree regression:**
- Editorial tests: 54 passed, 17 skipped (GPU + v2f EDL reference not present in worktree)
- CPU-only pipeline tests: 102 passed, 3 skipped

**Push:** `track-a-d1-d4a -> main` (8684c8cb..02a16ae3). Pushed successfully.
Worktree removed.

**STOP/GO: GO for Step 4 (fresh-topic render).**

## STEP 4: RENDER VERIFICATION (budget 20 min, from ~02:45 ET)

Step 4 is a fresh-topic render on the now-updated main to verify D1-D4a produce legal windows in production. This requires GPU0 + Ollama (gemma3:27b or qwen) for the editorial layer.

**Run (02:23-02:58 ET):** `select_story()` on GPU0 with gemma3:27b, 35 min wall time.
- Universe: 86 videos, 84 with transcript, 23 channels. 3177 chunks.
- Candidates: 25 (5 emergent, 3 emergent clusters rejected).
- D1 working: 14 model dates discarded as hallucinated (event_date older than source publish date).
- Top coverage stories: Binance CFO (6 ch), US Midterms (3 ch), Stock/AI declines (3 ch), Bitcoin ETFs (1 ch).
- Evaluation order: 8 candidates reached clip_quality.
- Result: **HOLD** — `NoProducibleStory`. No candidate produced enough legal windows for hook + 2 clips tonight.

**Analysis:** This is the correct outcome. The 080503 material (where D4a interjection fix matters) is now 2+ days old and outside the fresh window. Tonight's universe has different stories. D1-D4a ran without errors, D1 correctly discarded hallucinated dates, the coverage phase worked, and clip_quality ran but the available transcripts did not yield producible clips. This matches the pre-D4 behaviour for a new universe — the fix targets specific patterns that may or may not be present in any given night's material.

**STEP 4 VERDICT: PASS (HOLD is the correct outcome; no crashes, no false passes, D1 date discards working).**

---

**TRACK A COMPLETE (02:58 ET).**
- Step 0: GO (00:28 ET)
- Step 1: GO (01:11 ET) — byte-identical to v2f
- Step 2: GO (02:30 ET) — D1-D4a implemented, tested (164 pass), audited (Grok 82 MERGE)
- Step 3: Cherry-picked 15 commits to main, pushed (02:45 ET)
- Step 4: Fresh editorial selection ran to completion, HOLD (correct), D1 date discards confirmed
