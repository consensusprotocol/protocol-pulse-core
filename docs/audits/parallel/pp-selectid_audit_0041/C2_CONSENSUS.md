# Audit 0041 (rulings 94 + 95), cycle 2: outcome

- grok-4.20: P0 none, P1 none; SHIP yes with conditions. Both conditions are report-only, in next_attempt:
  - (1) rs[0]'s channel and publish time stand for the video: the adapter's rows of one video carry one channel and
    one publish time (ledger_build refuses a video naming two channels);
  - (2) expires_at parses P.utc_z's own output, "YYYY-MM-DDTHH:MM:SSZ" or None (None leaves the expiry unset).
  Recorded, unchanged.
- qwen3.8-27b: P0 none, P1 none. The placeholder score is gone; pending_verdict cannot reach the medley (only
  spotlight.build passes it); a third-person hook cannot be sealed without an affirming verdict (the ALONE >= 4 gate,
  and check_edl with no rate fails closed); the trim is checked for its clean cut and its affirmation.
- glm-5.3-flash: had not answered when the change was committed (its cycle-1 review was in). It then failed with HTTP
  503 (Service Unavailable): no cycle-2 review from glm (C2_glm-5.3-flash.md holds the failure). Cycle 2 rests on grok
  and qwen, both P0 none and P1 none.
