# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 55 s finish=stop usage in 8788 / out 407 usd~0.054 (upper-bound price)

**P2: pipeline/package.py:41** (concrete scenario: pair with bag-of-words overlap of exactly 79% of shorter length). The Counter-based pre-filter correctly rejects before difflib.SequenceMatcher because multiset intersection is a strict upper bound on possible in-order hit; no false-negative matches are possible (verifiable from the comment and the 80% test cases that follow).

**P2: pipeline/package.py:74** (concrete scenario: three moments A-B-C where A matches B and B matches C on different channels, earliest publish time is A). The union-find + root_of path compression + final min-per-group correctly collapses the transitive group and keeps only the earliest readable published_at (tie broken by moment_id); the "aligned through another copy" fallback reason is emitted for the indirect duplicate.

**P2: tests/package/test_medley.py:168** (concrete scenario: moment with published_at=None vs one with valid ISO time). The at() helper treats missing/unparseable time as (1, 0.0, id) so it is never selected as original; same-channel pairs are excluded from reposted (matches K3 exactly, verifiable in both the loop guard and the unit test that asserts dup=={}).

**P2: pipeline/package.py:91** (post-usable, pre-STAND_ALONE/trim/step-A). Placement matches the ruling's "before the angle step" and "keep the ORIGINAL publisher's … credit the original" verbatim; n_usable is captured before filtering so out["usable"] semantics are preserved (explicit comment references audit 0310).

No P0 or P1 findings. All governing laws verifiable in the diff (L-k canonical form via canon.canon_tokens, L-j exact bytes/attestation untouched, no renderer/selector change, fail-closed on unreadable times, etc.) are respected. The 308-moment real run (2.3 s) and full test suite pass are stated in the diff.

**SHIP: yes**