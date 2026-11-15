# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 53 s finish=stop usage in 7581 / out 993 usd_reported=0.029107 usd~0.063 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1524 (C1_STEP.diff)**

**Summary of change**  
The diff implements STATE Q2 (15:04 ET 2026-11-15, default at 15:24): `hook_answer()` tolerates *only* a complete JSON object followed by trailing closing braces + whitespace (the exact Grok out-of-contract pattern observed in SHADOW86.jsonl and the alone-test). `json.loads` is tried first; `raw_decode` + explicit rest validation is used only on failure. Anything else (text, other punctuation, leading junk, partial object, etc.) still raises `ValueError` exactly as before. The hook contract checks, per-candidate error handling, cache semantics, and all other `json.loads` sites are untouched. A one-line test driver fix ensures `usd_reported` (ledger figure) is emitted instead of the price-table estimate. New unit test exercises the exact allowed/invalid cases plus the spend path.

**Verification against requested checks**  
(1) Nothing but a complete object followed *only* by closing braces/whitespace is accepted. The `not rest.strip() or rest.replace("}", "").strip()` guard + `rest.count("}")` is precise; all other suffixes raise.  
(2) Hook contract (`set(v) == {"hooks"}`, per-id dict shape, `HOOK_PARTS | {"why"}`, numeric ratings, string `why`, etc.) runs *after* `hook_answer` and still rejects malformed objects.  
(3) No other verdict path, cache, provider, or test was altered; only `hook_ratings.parse` and the new helper are affected.  
(4) `spent_reported()` reads the ledger's `usd_reported` line (rounded to 6 decimals); test writes a fixture containing both reported/estimate values and asserts the reported figure.  
(5) `test_q2_an_answer_whose_only_extra_is_trailing_closing_braces_is_read` + updated `test_hook115` cover happy path, note emission, clean JSON, all listed bad cases, and the spend correction. Mutation suite (braces ignored, text accepted, note omitted, estimate used) kills the 4 bad variants.

**Compliance with governing laws**  
- **SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, L-a through L-l, LAW 20/M2, M12 FAIL-CLOSED, L-d protected preview, v2f byte-identity**: No impact. This is isolated to hook-rating JSON ingest (editorial selection stage). No transcript, cut-point, fade, credit, sign-off, edge-word, claim, or render logic is touched. No gate threshold changed, no failing gate reclassified, no exception turned into a pass for non-JSON cases.  
- **L-k (ONE CANONICAL FORM)**: Irrelevant — this is provider response parsing, not content/word comparison. `canon.py` paths untouched.  
- **L-l (MODEL REPLY COUNTS ONLY WHOLE)**: Satisfied. `ValueError` from `hook_answer` is still treated as unrated (continues to next model per existing `except` block). Only *structurally valid* objects that also pass the full `HOOK_PARTS` contract are used; partial/malformed replies remain INCONCLUSIVE for that candidate.  
- **L-j (RELEASE AUTHORISED ON THESE BYTES)**: Unaffected; ATTESTATION, gate inventory, and `release_auth` logic not modified.  
- **Smallest diff / no new renderer / GPU0 only / M1**: Compliant.  

**Findings**  
[P3] Double invocation of `hook_answer(r.text)[1]` to obtain the dropped count is redundant (first parse could forward the tuple). Negligible cost but unnecessary string re-parsing.  
[P2] Model-specific tolerance for Grok's trailing-brace pattern, even though narrowly scoped and audit-first via STATE Q2, introduces a maintenance burden. Long-term fix should be at the provider/output layer rather than parser workaround. Does not breach any listed law but should be monitored.  
[P3] `BRACES_NOTE` and inline timestamps are hard-coded literals; future audit notes should pull date from a constant or generation header for consistency with regression/reference tagging.  
[P3] Test uses `self.canned(ok + extra)` with duplicated `bad, bad` arguments in the error case loop — style nit, does not affect correctness.  

All suites (medley, hook115, spotlight, hook_bar, release_auth, dec13_clusters, etc.) pass. No regression against v2f, protected preview, or must-fail fixtures. Change is safe to merge.

**P1_OR_WORSE: 0**