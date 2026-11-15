# Cycle 1 consensus: pp-selectid audit 20261114_2049 (RULING 105, the builder's side)

Reviewers under ruling 107 (2): qwen3.8-27b and glm-5.3-flash. Each raised one P1, the same one, so they agree and
Grok was not asked. Cost: $0.0050 vendor-reported (qwen $0.0039, glm $0.0011); the list-price upper bound was $0.204.

THE P1, raised by both, is IMPLEMENTED. ruling_105_fails compared raw strings, so a formatted token the integrator
rightly passes ('401K', '401(k)', '68,000', 'forty-five') could hold on this side (law L-k: every comparison goes
through canon).
- Every token (the record's token, each decoder reading, each second reading) is now read through canon.canon, the
  integrator's canon, byte-identical. A non-string reading, or one with no token, is None, and so no match and no
  truncation: it fails closed.
- The digit test (a name never qualifies) and the truncation test run on the canonical forms.
- Test: test_formatting_is_read_through_canon_on_both_sides. '401K' / '401(k)' with '401' readings passes; '86,000'
  against '68,000' still holds as (3); a None, empty or blank token holds.

IMPLEMENTED (glm P2): decide() ran the re-check only for the PASS outcomes, so an adopt_spoken entry carrying a record
went unchecked. The re-check now runs for PASS and adopt_spoken alike: a bad record holds, a good one lets the adoption
go on. Test: test_an_adoption_that_rests_on_the_record_is_checked_too. The redundant (e or {}) guard is gone (e is
non-None there).

CONFIRMED, no change:
- glm (2): a hold outcome is never turned into a pass. The re-check can only turn a pass into a hold, and a "hold"
  outcome goes on to the unchanged hold branch.
- glm (3): seal compatibility. The key enters the seal only when a segment carries it, and the frozen 3f481f5a pin is
  tested to recompute.
- glm's other two P1s, downgraded in its own text: a non-string reading fails closed; the record's own tests are
  re-derived anyway.
- qwen's P2s (the truncation helper fails closed on unusual suffixes; the row and imports) need no change.

Tests: 19 for ruling 105, 109 with the pre-check suites. Mutations: 19 (17 before, plus raw strings with no canon,
and an adoption left unchecked); results with cycle 2.
