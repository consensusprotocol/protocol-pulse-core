# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 44 s finish=stop usage in 26177 / out 422 usd~0.141 (upper-bound price)

**No P0/P1/P2 findings verifiable from the diff.**

All listed check points pass:
- every fail-closed path (scorer_verdicts on missing/malformed/wrong-event/wrong-sha/wrong-threshold/error/mismatched-affirmed/text_sha; verdict_of/with_verdict drops on mismatch; trim_refused; no_role_on_screen when no affirming verdict; scorer_problems/trim_problems; stand_alone_check rate=None case).
- sha matching (render_scorer_sha reads the two files in fixed order; verdict_of and with_verdict require exact text_sha256 on *current* text; trimmed variant never inherits original's verdict — test at package_pin:736 explicitly confirms).
- admitted opener can never open a line-up (placement calls SA.opener("hook") which rejects conjunction/reply; lineup_for respects it; test at TestRuling56Scorer:755-759).
- pin's three checks (scorer_problems, updated trim_problems refusing scorer_pending, gate_problems) and seal backward-compat (scorer_pending kept in SEALED_LATER but never produced; affirmed_verdict strict on text_sha/score/fault/scorer_sha/event).
- atomic only-on-change write (write_candidates uses .tmp + os.replace, compares exact (pid, text_sha256) set before writing).
- no remaining reader of scorer_pending or TRIM_SCORER_PENDING (removed from stand_alone_check, inventory, TRIM_SCORER_PENDING constant, test asserts hasattr false and refusal).
- no check accepts more than before except via affirmation by the render's own scorer (gemma3:27b via render_scorer_sha) of *exactly* the sealed text (verdict_of, affirmed_verdict, rate(), no_role_on_screen clip role only, K1-K5 all match diff comments and test cases).

Tests (including rewritten ruling-49 cases and 8 new TestRuling56Scorer cases), evidence dry-run, and seal recompute for old pins all verify. K1-K5 readings match the diff.

SHIP: yes