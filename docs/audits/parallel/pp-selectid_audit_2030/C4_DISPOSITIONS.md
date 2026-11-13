# pp-selectid audit of the L-y diff, ROUND 2: cycle 4 dispositions (synthesis by the pp-selectid session, 21:32 ET Nov 12)

**Run.** Cycle 4 cross-reviews the fixed diff (C4_STEP.diff, 133,013 bytes; prompt 174,137 bytes) with the cycle-3
reviews and C3_CONSENSUS.md. Every reviewer: SHIP yes with conditions; no P0.
- grok-4.20-0309-reasoning (xAI): no P1. "All Cycle-1 P0s addressed". It confirms its own cycle-3 P0 was wrong.
- z-ai/glm-5.3-flash (Heimdall, effort none): two P1s, both on messages; implemented below.
- qwen/qwen3.8-27b (Heimdall, effort none): no P1. It accepts the refutation of its ledger P0 (Router._lock is an
  flock per call).

**Spend:** about $0.74 at the config's upper-bound prices. Round 2 cost about $1.58; both rounds together about $3.0
(the estimate is an upper bound).

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K8 | ly_shape left a bridges_after_clip entry outside 1..n-1 to a count mismatch with a vague message (glm P1 (a); grok P2) | IMPLEMENTED: such an entry (0, past the last clip, not an int) fails by name: "after_clip [0]: a bridge between clips sits after clip 1..n-1 (after the hook it is the intro)". Test: test_an_after_clip_that_is_not_a_clip_index_is_named (0, 3, "1", None). It failed before too; only the reason is clearer. No package build() makes reaches it |

## Unique, implemented (wording only)

- glm P1 (b): with no bridge written, the RUNTIME redo now says "(no takeaway length lands it)", not "shorten the
  bridge". build() never reaches that branch: a no-bridge line-up inside the medley's seconds always has a budget,
  and when it has none, NoBridgeFits re-lines before any write.

## Kept (P2), with the reason

- grok P2: the spend guard reads the estimate, not the vendors' reported figures. Kept on purpose: the estimate is the
  conservative upper bound, and the reported figure is shown beside it.
- grok P2: confirmed_by accepts any non-empty string, list or dict. This is the factory's R11 contract word for word
  (bool and numbers fail).
- qwen P2: medley_content_range plans the line-up for no bridge, so a flagged join at the top of the range re-lines
  through NoBridgeFits. Kept: the re-line pays no write. The table reports re-lines.
- qwen P2 / glm N3: proof_ly's meter wraps Router._settle in the driver only; each worker owns its own Router.
- glm N6: the test rig re-states write_takeaway's precondition. The real one has its own 94-length test.
- glm N7: a falsy-{} bridge record counts as no bridge in the table. No producer writes one; assemble_medley writes
  None or a full record.
