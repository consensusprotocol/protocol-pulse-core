# pp-selectid PHASE 2 audit: cycle 2 dispositions (synthesis by the pp-selectid session, 2026-11-12 ~07:25 ET)

**Run.** Cycle 2 ran on the FIXED code in three chunks, each under the tool's 220,000-byte limit:
- A1_core: package, providers, package_pin, the adapter, the config;
- A2_core: vo_fidelity, context_integrity, moments, transcript_truth, trend_brief;
- B_tests_docs_wiring.

Each chunk carried the cycle-1 reviews and C1_CONSENSUS.md.

**Reviewers:** claude-opus-5-5 and claude-sonnet-5-5 (effort high) and grok-4.20-0309-reasoning. claude-fable-5-2 was
left out of cycle 2 for cost. The tool's gpt-4o leg was left out because OpenAI has no credit.
- **P0 count.** Grok: no P0 in any chunk. Opus and sonnet: P0s in A1 / A2 (below) and in B (tests of the seal's
  consumer).
- **Verdicts.** Every reviewer's verdict is "No / yes with conditions" for unattended release. Opus B and sonnet B:
  "yes with conditions" for the single REVIEW ONLY delivery (L-q).

The rule is the same as cycle 1: consensus (two or more reviewers) is implemented; a unique finding is evaluated on its
evidence. Two edits made after the cycle-2 snapshot are listed at the end.

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | **full token coverage** in the classifying verdict: overlap is not coverage (opus A2 P0-1, sonnet A2 P0-1) | IMPLEMENTED: every content token of every line sentence must lie inside some claim's `words`; an unlocatable sentence fails |
| K2 | **production claims bound to the manifest** (sonnet A2 P0-2, opus A2 P1-3, opus B P1-6) | IMPLEMENTED: a production claim's words may carry only production terms (credited shows, the package's counts, "next", "links", "clips", the show / date); `strict_features` runs on them with the manifest terms allowed, and a fact, name, quote, time word or price in them fails (NOT_PRODUCTION) |
| K3 | **the seal is recomputed and the lines must equal the VO** (opus A1 P1-3, sonnet A1 P1-1, opus B P0-1/2, sonnet B P1-1) | IMPLEMENTED in package_pin.to_pin: the inventory, title, caption and VO are re-read from the package's own `lines`; a mismatch between `lines` and `vo` / `title` / `caption` refuses; no zip truncation (bridges and after_clip counts must match). The consumer half (pinned.py recomputing the seal) is REQUESTS R7 1b, the integrator's file |
| K4 | **`replayed` tri-state** (opus A1 P1-4, sonnet A1 P1-2) | IMPLEMENTED: an inventory row's `replayed` is the measured reply's own boolean; None (not stated) refuses the pin |
| K5 | **step A independent of the ACTUAL writers** (sonnet A1 P0-1, opus A1 P1-6, opus B P1-4) | IMPLEMENTED in package.build: after the writer answers, a moment whose stored step A came from the writer's vendor or family is re-screened before its verdict counts |
| K6 | **time-sensitive / price risk measured, not self-reported** (opus A1 P1-7, sonnet A1 P1-4) | IMPLEMENTED in package.usable: a clip whose own words carry a recency word (vo_fidelity.time_words) or a current-kind price (price_mentions) is time-sensitive regardless of the miner's flags (L-v 3) |
| K7 | **an empty reply fails over** (sonnet A1 P1-5, opus A1 N8) | IMPLEMENTED: an empty text from any back-end is RequestRejected (the chain continues for this call) |
| K8 | **the adapter raises on a malformed case** (opus A1 P2-10, sonnet A1 P1-6) | IMPLEMENTED: a case the adapter cannot read raises GateNotMeasured (the harness's ERROR) |
| K9 | **every segment judged in context** (opus A2 P1-6; sonnet A2 P1-6 for missing timing) | IMPLEMENTED: check_contexts fails (CONTEXT_UNAVAILABLE) unless every segment has its context; a window whose moment has no word time is unavailable |
| K10 | **speaker evidence tied to the selection** (opus A2 P1-8, sonnet A2 P1-7, opus B P1-5) | IMPLEMENTED: "host" is verified only when the quoted evidence lies INSIDE the selected words; evidence elsewhere in the window no longer names the speaker (L-v 1, fail closed) |
| K11 | **tests of the seal's producer and consumer** (opus B P0-1/3, sonnet B P1-1/2/4) | IMPLEMENTED: inventory unit tests (every unmeasured, failed, replayed or empty input gives a non-PASS row); smoke_r7 feeds TAMPERED pins (title, VO, segment text, a FAIL row with flags still true) to the deployed build_edl and records what it refuses; a verify_segment test with no diarisation gives ok false |

## Refuted or kept, with evidence

| finding | disposition |
|---|---|
| a late exclusion / second-pass failure can ship after coherence (grok A1) | REFUTED: build() resolves both futures and drops a failing moment BEFORE coherence; the pin refuses NOT RUN |
| Router.down permanent on one oversized prompt (grok A1) | REFUTED: an over-context prompt is RequestRejected (this call only) since cycle 1; only an unavailable back-end is down for the run |
| the entails-without-a-limit NOTE path should fail (grok A2, sonnet A2 P1-5) | KEPT: it is the orchestrator's ruling 5 (06:22); an "uncertain" still fails, and the exam's 41 must-fail cases stay rejected (tests/package/exam/ci_mustfail_*.json) |
| B0 should avoid the writer's vendor (opus A2 P2, sonnet A2) | KEPT: B0 sees the clips ALONE (no VO, title or caption: no generator text), so there is nothing of the writer's to judge |
| heat unbounded in the trend brief (grok A2) | REFUTED: check_brief rejects heat outside 0-1 (trend_brief.py:118) |
| seal float precision (grok A1) | REFUTED: both sides round to 3 decimals from the same pin values |
| measure WPS / FIXED_S on a real render (grok B) | OPEN ITEM (design section 8): measured on tonight's render |
| local-first verdict chains need the exam first (sonnet A1 P1-7) | KEPT as documented: local answers only under the integrator's GPU0 lease; tonight every verdict ran on a frontier back-end; the A/B decides |
| `checks` outside the seal (opus B P0-2) | IMPLEMENTED on this side (K3: the flags are derived from the sealed inventory at to_pin); the consumer must read the inventory, not the flags: REQUESTS R7 1b |

## Edits after the cycle-2 snapshot

- run_exam_record.py and ab_roles.py read the phase-2 guard from PP_GATES_LIMIT_USD (they hard-coded $40).
- The orchestrator's 06:45 order (CUTTABLE, ruling 7):
  - transcript_truth.edges and the "cuttable" inventory row;
  - word-range context marking;
  - the pin's cut_evidence.

These are recorded here and are part of the commit that follows.
