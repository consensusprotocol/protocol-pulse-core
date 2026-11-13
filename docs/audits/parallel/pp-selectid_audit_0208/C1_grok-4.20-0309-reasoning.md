# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 428 s finish=stop usage in 12428 / out 316 usd~0.070 (upper-bound price)

**Findings:**
- No P0/P1/P2 findings verifiable from diff. No concrete inputs -> wrong result scenarios (a)-(e) can be constructed from the provided code alone.
- (a) No: all shown lookups (context_integrity.py:10, package.py:216+229+234+243+252, speakers.py:265) use `.get("source_key") or video_id` / `src_of`; full-video path never injects source_key.
- (b) No: ledger_build.py:143 (`dup = next((mid for a, b, mid in kept if a < sp.end and sp.start < b)`) + 167 (`rec["source_key"] = key`) + per-`wsrc` reanchor (line 138) + test at 310-324 prevent same-speech or cross-edge clips.
- (c) No: full-video `if src is not None:` block (ledger_build.py:75-100) retains exact prior reanchor/seen/(vid,k0,k1) logic and `sources[vid]`.
- (d) Uncertain (downstream pin/render/novelty/dedup not present in diff).
- (e) No: all tests updated to assert new per-moment window + dedup + src_of behavior (e.g. test at 296-325, 333/351 now use `m["source_key"]`); they would pass the diff and fail the pre-change 63/74-row loss.

**Verdict**  
SHIP: yes