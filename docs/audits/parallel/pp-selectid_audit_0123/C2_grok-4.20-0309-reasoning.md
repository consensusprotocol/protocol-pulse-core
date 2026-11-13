# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 36 s finish=stop usage in 19522 / out 1405 usd~0.133 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0123 (fixed diff)**

**Findings (verified only from the provided diff):**  
No P0s. No P1s.  

**P2-1.** `caption_parts` returns a `covered` tuple derived from the *actual* tokens placed in `pre`/`post` (or the selection edges), yet the *acceptance* decision is made on the caption record's global `first`/`last` (lines 41-46). Concrete scenario: a caption record whose overall `first` is at 0 but that has a 50 s gap exactly in `[t0-90, t0-40]` will still pass the `first <= t0-90` test, return non-None parts, and produce a measured=True verdict whose reported window starts at t0-40. The caller (`_window_text`, `context_around`, exclusion prompt) therefore sees a shorter actual context than the returned `(from_s, to_s)` implies. The test only exercises the edge-tol cases, not internal gaps. This is now P2 (law explicitly accepts "or to the media's edge"; the measurement is present). `context_integrity.py:41-54`.

**P2-2.** `caption_source` scans *every* `transcript.*.json` and recomputes `segments_sha256` on each; a video with many full-video transcripts (e.g. after re-ingests) therefore incurs linear I/O on every ledger build. No caching or index is used. Concrete: 20 transcripts for one vid → 20 open/read/hash operations even when the first match is chosen. Minor performance, not correctness. `ledger_build.py:252-265`.

All standing laws are satisfied by the diff:  
- (a) Tampered/non-ready window records cannot reach a moment — every claim is re-checked in `window_source` (hash, method, segments, words_sha, spelling, clock, punctuation, span, channel, `sentence_ready`), with exact why-strings asserted in the tamper test.  
- (b) A window clip cannot be judged with <90/60 s (or missing) context; `caption_parts` returns `(None,None)` (coverage test, edge-tol test, `no_caption_context` report) → `exclusion_for` hard-codes exclude/measured=False (L-j).  
- (c) The caption record is exactly the one whose segments-sha matched the ledger row at mining time; >1 match is now explicitly ambiguous → no context (fail-closed). Only full-video slots are scanned.  
- (d) Full-video path is byte-identical: `if getattr(src, "window", None) is not None` routes *only* windows through the new code; old `window()`/`E.spoken()` path unchanged.  
- (e) Every test fails exactly on the defect it names (index counts, 9 tamper cases with string matches, coverage matrix, ambiguous caption, exclusion prompt contents, no-caption measured=False).

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
GLM caught the post-list-comprehension boundary (word starting exactly at t1 was dropped) and the untested tamper branches (segments_sha, method, channel contradiction, words_off_segments edge). Qwen highlighted the missing duration check for the "media's edge" case. Grok correctly asserted that the original code already failed closed on missing context but missed that the measurement itself was absent. I had flagged the caption-uniqueness and context-measurement gaps but overlooked the concrete `StopIteration` risk in `context_around` on empty parts and the fact that the original `covered` tuple lied about achieved span.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- K1 (short context): Fully agree. The `EDGE_TOL_S` + global `first`/`last` check + test `test_the_caption_coverage_is_measured_never_assumed` implements the law's own "or to the media's edge" clause. The returned `covered` tuple is now truthful.  
- K2 (caption record uniqueness): Fully agree. Requiring *exactly one* matching record and failing closed on ambiguity is the correct minimal fix; it eliminates the P0 scenario GLM described without changing acceptance rules.  
I partially disagree with GLM's original P0-1 severity: the store *could* have held duplicate shas, but the integrator's render path already failed closed before render, so blast radius was smaller than stated. The fix is still required for cleanliness.

**3. NEW FINDINGS FROM THIS REVIEW**  
Only the two P2s above. The combined Cycle 1 analysis revealed no additional defects that survive the fixes. The new test fixtures exactly match the worker's `make_record` format, the tamper matrix is exhaustive for the contract, and `proof_ledger.py` now exercises the full `--word-pass` path.

**4. REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Window record checks   | P0      | None    | All tamper paths now tested; sentence_ready double-checked |
| Context measurement    | P0/P1   | P2      | EDGE_TOL_S + first/last test + fail-closed path added |
| Caption selection      | P0      | None    | Ambiguity now explicitly rejected; only full-video slots scanned |
| Full-video path        | P2      | None    | Guard `if getattr(src, "window", None)` guarantees no change |
| Test coverage          | P1      | P2      | Every named defect now has a dedicated test |

**5. FINAL PRIORITY LIST**  
- **P2 (medium):** `context_integrity.py:53` — clarify in docstring that `covered` reflects the *selected* pre/post tokens (subject to gaps) while acceptance uses the caption record's overall span.  
No P0s or P1s remain. Nothing blocks shipping.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The single highest-leverage change is the measured coverage check inside `caption_parts` (lines 41-46) paired with the explicit ambiguous-record rejection in `caption_source` — it turns two conditional P0s into verifiable, tested fail-closed behavior while touching only the new window path.

**7. PRODUCTION READY?**  
Yes with conditions: (1) the integrator must confirm that every caption record written to `transcript.*.json` carries an accurate top-level `"duration"` field (used at line 45); (2) the `no_caption_context` and `window_passed_over` counters in the build report must be monitored on first production run.  

**SHIP: yes with conditions**