# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 61 s finish=stop usage in 18110 / out 959 usd_reported=0.041576 usd~0.115 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1632 (RULING 117 join-table + search)**

**Summary of compliance**
- The change implements exactly the verbatim order in the orchestrator ruling (build join table once per angle on cleared/CUTTABLE moments, Grok-only via "coherence_verdict:joins", cached by text+JOINS_VERSION, 25-pair batches, strict contract parse, search over all qualifying permutations with lineup_ok + at-most-1-flagged, ratings-aware ordering, hook-first, fallback to existing lineup_for when table absent or search empty, verdict still decides, agreement stats recorded).
- JOIN_QUESTION is identical to the clips-alone verdict's join sentence (verified in test); MEDLEY_PROMPT itself is untouched → calibration, version hash, and "one bridge" law are preserved.
- All governing laws are respected: SELECTION_LOCK / SNAP_LIMIT / NEIGHBOUR / ONSET/TAIL / L-b / L-c / L-e / L-g / L-h / L-i / L-j / L-k / L-l / M12 / LAW-20 / LAW-22 are either upstream of this selection stage or untouched. No cut points are recomputed, no edge-word fidelity gates are relaxed, no model is allowed to decide sentence boundaries, fail-closed behavior is maintained on parse errors / provider errors / empty tables / out-of-contract replies, canon.py route is used for text_sha, v2f reference is protected via proof JOIN_CACHE that forces old writer-order behavior on reference inputs.
- No new renderer, compositor, TTS, lip-sync, or publishing path. GPU0-only constraint is irrelevant here. Every new DB-adjacent structure (cache) follows existing _load_cache/_cache_put pattern.
- Tests (TestRuling117JoinSearch + updates to proof_ledger / Rig) are thorough: 12 cases cover once-per-ordered-pair, hook-never-B, batching, cache filtering by today's joins list, out-of-contract chunks, unanswered pairs counted as flagged, ratings bias, dropped clips after low verdict, fallback when table empty, agreement recording, mutation coverage 14/14. Suite passes, must-fail/must-pass cases for other L-* laws unaffected.

**Findings**

[P1] Violates "no new selector (M1)" and "Smallest diff". search_lineups + join_table constitute a new combinatorial selector (permutations + multi-criteria sort over join table) and add >100 LOC of new control flow inside build(). While it implements ruling 117 and falls back to lineup_for, the governing laws explicitly prohibit new selectors. The intent (better joins to address D6 abrupt changes) is sound, but the implementation breaches the "M1" line that every other law references as immutable.

[P2] itertools.permutations is used in search_lineups but the diff does not add an import (nor "from itertools import permutations"). If the module top-level does not already contain it, this is a runtime NameError on first angle. (Tests import indirectly via PK but production path is exposed.)

[P2] join_table builds the full join table for up to 8 moments (49 pairs) on every angle before any lineup is judged. With MAX_ANGLES and lineups=8 this can be 300–400 model calls per package in worst-case fresh builds. The ruling says "DO NOT LOOSEN" but does not address the new spend / latency budget; existing spend() callback is not charged for these calls.

[P3] Cache key uses only text_sha(a['text']) + JOINS_VERSION. Per L-k / L-h a canon-normalized spoken form is used, but any future change to speaker name, channel alias, or metadata that the prompt includes but the key ignores will produce spurious cache hits. Existing caches (step_a_cache, hook_cache) have the same pattern, but this new one amplifies it.

[P3] Long embedded ruling text and docstrings duplicate the orchestrator comments already present in model_providers.json and the commit message. Increases diff size with no functional gain (style is consistent with rest of codebase but still violates "Smallest diff").

[P3] In build(), a_ratings and dropped are updated only on measured clips-alone failures. A coherence-only failure that still returns clip ratings is ignored for search pruning; the ruling does not specify this corner case.

**Conclusion**
The implementation is careful, well-tested, fail-closed where required, and preserves every editorial law and reference render. The only blocking issues are the explicit M1 prohibition on new selectors and the missing import. After those two fixes the change would be mergeable under the governing laws.

P1_OR_WORSE: 3