# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 246.7 s, $0.024, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest diff 116fbd5c (mine-hook/2)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GLM caught the `>>` tokenization question more precisely than I did.** I flagged it as "needs verification against `eligibility.spoken`" — GLM framed it as "unverifiable from diff alone" which is the same conclusion, but GLM correctly noted the `turn_change_inside` skips-first-token implication (contract.py:132) as evidence the first token *can* be a marker. I missed that supporting detail.

**Qwen caught nothing I missed that survived measurement.** Qwen's P1 about `>>` passing the filter and the ledger race were both refuted or non-issues. Qwen's analysis was the weakest — verbose, speculative, no line-level verification.

**What everyone missed in Cycle 1 that the consensus resolved:** The `>>` question was **measured, not debated**. `canon.canon_tokens(heads=True)` drops `>>`, `&gt;&gt;`, leading dashes and quotes. `">> And then"` → `['and','then']`. 229 ledger texts beginning with `>>` were checked: `">> Yeah, I..."` → `'yeah'` → correctly dropped as reply word. Pinned by `test_a_leading_speaker_marker_never_hides_the_first_word`. My Cycle 1 "needs verification" is now **closed: no bug**.

**What I caught that they underweighted:** The `episode_measure` `minutes: 0.0` vs `None` distinction for missing timing, and the `--rerun` TOCTOU race. Both were acknowledged in consensus as implemented/fixed.

## 2. WHERE I AGREE OR DISAGREE

| Finding | Reviewer | Verdict | Why |
|---------|----------|---------|-----|
| `>>` bypasses opener filter | Qwen P1, Muse P1 | **DISAGREE — refuted by measurement** | `canon` strips markers. Test proves it. My Cycle 1 concern is resolved. |
| OPENER sets must match builder verbatim | Muse P1 | **AGREE — and done** | `test_the_opener_words_are_the_builders_verbatim` AST-compares against `pp-selectid/stand_alone.py`. Correct approach. |
| No visibility into ruling 92 effect | GLM P1 | **AGREE — and done** | `live.json: hooks_12h.rows_by_episode` buckets by `episode_tpm`/`unmarked`/`not measured`. Right fix. |
| `--rerun` left no event, help wrong | GLM P2 | **AGREE — and done** | Now emits `hooks_rerun` event, help says second `--rerun` re-queues failures, warns to run with no hook pass in flight. |
| Empty record measured as solo | Muse P3 | **AGREE — and done** | Now `measured_from: "no segments"`, `minutes: None`. Honest. |
| Episode term in rank_score | GLM P1 | **DISAGREE — by design, correctly** | `rank_score` orders all reads including medleys. Ruling 92 is for spotlights; builder applies measure per-row. Adding it to `rank_score` would break medleys. |
| Ledger append race | Qwen | **DISAGREE — not a bug** | `O_APPEND` + `fcntl.flock` + `wlock` (service.py:284) makes this safe. Qwen misread the locking. |
| `canon` import failure handling | Muse | **AGREE — by design, correct** | Hook pass raises, `hook_video` catches, retries in 10 min, writes nothing. Fail-closed. |

## 3. NEW FINDINGS FROM THIS REVIEW

**N1. `episode_measure` double-counts markers inside a single segment text — but this is correct.** `TURN_MARK.findall` counts every `>>` occurrence in `seg["text"]`. If a segment contains `">> Alice: hi >> Bob: hello"` that's 2 markers. `contract.turn_change_inside` counts at most 1 per span (boolean). These measure different things: episode-level turns vs. span-level speaker change. No inconsistency — but worth documenting that `episode.speaker_markers` is a raw count, not deduplicated turns.

**N2. `stats.py:118` bucket boundary `>= 1.0` is arbitrary and undocumented.** `">= 1 turn / min"` vs `"< 1 turn / min"` — why 1.0? A 60-min podcast with 30 markers (0.5/min) is clearly conversational but buckets as `< 1`. The bucket is informational only (not a gate), so not a bug, but the threshold should be noted as heuristic or removed in favor of raw histogram.

**N3. `mine.py:248` `mins` calculation uses `segs[0].get("start")` not `min(all starts)`.** If segments are out of order (shouldn't happen, but no invariant enforces it), minutes is wrong. Low risk — `transcript_store` writes segments in order — but a `min()`/`max()` would be more defensive. Not worth blocking.

**N4. No finding changes the security/law assessment.** L-x (no single model), L-l (strict validation), L-m (unmarked ≠ solo), L-u (hard flags), L-r (GPU0 lease) all still compliant. No new attack surface.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `mine.py` opener filter | 7/10 (unverified `>>`) | **9/10** | Measurement + test closed the `>>` question. Sets verified against builder source. |
| `mine.py` episode_measure | 7/10 (misleading 0.0) | **9/10** | Empty-record fix shipped. Remaining `0.0` for `None` end is cosmetic. |
| `mine.py` prompt | 8/10 | **9/10** | Prompt correctly states OPENER rule with verbatim sets, conversation guidance. No overreach. |
| `queue.py` / `service.py` hook plumbing | 8/10 (TOCTOU) | **9/10** | `--rerun` now documented with concurrency warning + idempotent guard. Acceptable. |
| `stats.py` observability | 6/10 (no visibility) | **9/10** | `rows_by_episode` added. |
| `ledger.py` / adapter | 10/10 | **10/10** | Unchanged, still correct. Extra `episode` field is additive, `line_problems` allows it. |
| Overall diff | 7.5/10 | **9/10** | All P1/P2 findings addressed. Remaining issues are P3 cosmetic. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL — none.** No data-loss, security, or correctness blocker.

**P1 HIGH — none remaining.** All Cycle 1 P1s are resolved.

**P2 MEDIUM**
- `stats.py:118` — Document why `1.0 turns/min` is the bucket boundary, or replace with raw `episode_tpm` histogram. Currently a magic number with no ruling behind it.

**P3 LOW**
- `mine.py:248` — Consider `min(s.get("start") for s in segs)` / `max(s.get("end") for s in segs)` instead of `segs[0]`/`segs[-1]` for robustness against segment reordering. Not blocking.
- `mine.py:248` — When `segs[-1].get("end")` is `None`, `minutes` is `0.0` with `turns_per_min: None`. Could be `minutes: None` for consistency with the `no segments` case. Cosmetic — `turns_per_min: None` already signals "unknown".

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `episode` measure on every row plus `rows_by_episode` in `live.json` — it turns ruling 92 from an untestable prompt tweak into a measured quantity the builder can rank on and the operator can observe.

## 7. PRODUCTION READY?

**Yes, with no conditions.** The diff is additive, fail-closed, and fully tested (242 tests). The three questions for reviewers are answered: (1) opener filter is correct — `canon` strips `>>`, sets match builder verbatim; (2) episode measure is correct — both marker forms, honest `unmarked`, additive field; (3) nothing changes the moment pass, flags, adapter, or any gate — `KINDS["moment"]` untouched, `HARD_RISKS` untouched, `best_unused_moments` untouched.