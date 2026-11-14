# Ruling 80 (hook pass) cycle 2 (cross-validation): consensus

Reviewers (Heimdall-served): qwen3.8-27b (210 s, $0.008), muse-spark-open-816b (331 s, $0.025), glm-5.3-flash
(477 s, $0.005). VERDICTS: no P0 from any; qwen "P0 CRITICAL: None. The code is safe to ship."; muse "No new P0/P1
findings"; glm accepts both refutations (the measured caption timing: "better than my reasoning"; the hook hint: "a
later moment pass must not un-pick it") and confirms every cycle-1 fix (the three-valued carry_forward, the hook
lane's own pool, the index, the guarded notice).
Remaining, P2:
- a video left marked in flight if the hook pool's submit raises at shutdown (glm, muse): FIXED (discarded, re-raised).
- `mine_video(role=..., kind="hook")` could send the hook question under another role (glm, muse: "latent, not a bug
  today": no caller passes a role with the hook kind): recorded, not changed.
- muse N2: a hook pass that ends with failed windows after 3 tries is not retried again: by design (the ruling's 12 h
  window; the good windows' hooks are written and the failure is in hook_note).
Tests after cycle 2: tests/ingest 225 passed.
