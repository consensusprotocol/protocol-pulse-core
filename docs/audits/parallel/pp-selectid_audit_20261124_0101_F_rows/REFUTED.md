# Findings checked against the code (01:30 ET Nov 24)
Seats: qwen27b and gemma answered (effort high, 65,536 tokens); gpt-oss stops at the gateway's 32,768-token cap.

1. qwen F1 [high] "fallback_fields' join guard indexes join[0] without checking join is a non-empty sequence": FIXED
   (a list or tuple, non-empty, an int that is not a bool, between two of the line-up's clips; test
   TestRuling156FallbackLines.test_audit_a2_... with (), [], "x", (True, ...), ("0", ...)).
2. qwen F2 [high] "lv2_settled treats 'pending' as passed in line-up calls": the lock's verdicts are only "pass",
   "adopt", "hold" and "error" (lock_precheck.decide), so no line-up reading was "pending"; made impossible by
   construction anyway: lv2_settled accepts "pass" / "adopt" only, and the prescreen's pending reading is its own
   function lv2_pending (test: "pending" leaves the record unchanged in lv2_settled).
3. qwen F3 [medium] "seg_marks counts a REFERENT_OUTSIDE that ends as information": FIXED. seg_marks reads the same
   step-A record as the pin's row (a_by): a clip whose only code is REFERENT_OUTSIDE with no referent saying
   "changes the claim: yes" adds no kind; no record to read: counted (test_the_search_counts_a_referent_...).
4. qwen F4 [low] (the prescreen row says PASS, not the settlement): rejected by the panel; the line-up's row and the
   pin's second_pass record carry "word_check".
5. qwen, cycle 2, not voted: "lock_verdicts can raise when pre has no usable segments": FIXED (a list of the
   line-up's length or {}; tests with {}, {"segments": None}, an error record).
6. qwen, cycle 2, not voted: "the join guard does not validate join[1]": join[1] is never read by fallback_fields
   (only join[0], the clip the bridge follows).
