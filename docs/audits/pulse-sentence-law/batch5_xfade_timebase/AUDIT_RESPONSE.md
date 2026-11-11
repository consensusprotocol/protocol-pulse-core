# Batch 5 (xfade timebase after a hard cut) — dispositions

Cross-LLM (GPT-4o + Gemini; Grok blocked by the xAI ceiling) and Heimdall (deepseek + qwen27b): no
consensus finding against the fix.
- Cross-LLM U-1 "Law 22 unverified": the frozen v2f path has no TRANSITIONS file and never builds a
  transition graph (test_transitions TestFrozenPath); pipeline/regression.sh PASS. Law 22 is re-proven by a
  full v2f re-render at the HEAD the three fresh runs use (after 4b lands).
- Cross-LLM U-2 / UI-1 "scope does not match pulse-sentence-law": the folder is the mission's audit
  feature name; this diff is the Phase 3 render fix found by recut run 5. Rejected.
- Heimdall test_transitions (qwen27b, agree 0) "malformed _seg call": misread; the test runs (13 passed),
  and on the old graph it fails with the production message ("First input link main timebase (1/1000000)
  do not match ... (1/24)").
