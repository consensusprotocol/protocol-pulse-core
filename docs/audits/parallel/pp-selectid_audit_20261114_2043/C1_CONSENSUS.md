# Cycle 1 consensus: pp-selectid audit 20261114_2043 (RULING 107 Q1: abandoned calls at the model's own reported rate)

Reviewers under ruling 107 (2): qwen3.8-27b and glm-5.3-flash, with Grok as the third.
- glm: P1_OR_WORSE 0.
- qwen: stopped at its 16,000-token cap (finish=length) and repeated itself. Its "[P1]" headings are questions, each
  answered "correct" in its own text, and it gave no closing count.
- The driver read qwen's tags as a P1 disagreement and asked Grok, as the third: P1_OR_WORSE 0.
- Cost: $0.0469 vendor-reported. qwen $0.0141, glm $0.0015, Grok $0.0313. The list-price upper bound was $0.538.

NO P0 / P1 STANDS. Every reviewer confirms questions (1) to (6):
- the rate is exactly the reported dollars over the reported calls' prompt tokens, from 3 reported calls on;
- the cap is never under-booked by it (the rate is all-in, and the prompt is counted from above);
- the two lock acquisitions run in sequence in the caller's thread, with no nesting;
- the in_reported carry-over is b["in"] - n_in in both places;
- the other callers behave as before;
- the tests pin the behaviour.

IMPLEMENTED (P2):
- glm F1 / Grok P2: reported_rate now catches (SpendLimit, OSError, TypeError, ValueError) and falls back to list
  price, the higher booking, for any ledger it cannot read: a by_backend that is not an object, a row that is not
  one, a non-numeric reported_calls. _settle still raises on an unreadable ledger, as before.
  Test: test_the_rate_is_none_whenever_the_ledger_cannot_give_one, also covering no spend path and no row.
- glm F3: booking_usd's docstring states the benign gap between the rate's read and the booking's write. A reported
  call landing between them moves the rate by one call. The ledger stays balanced, because a late answer removes the
  booking as it was stored (on_cap).
- glm F14 / F14b: the docstring states that the rate applies only while the call is abandoned. A late answer with no
  vendor figure is accounted at its own token counts' estimate (ruling 83 (a)).
  Test: test_a_late_answer_without_a_figure_is_its_own_estimate_in_place_of_the_booking.

NOTED, NOT CHANGED:
- qwen P2 / glm F18 (P3): a ledger row kept before this change seeds in_reported from "in", which also counts calls
  that carried no figure. That understates the rate. The change sanctions this, and for Heimdall it is negligible:
  every recorded Heimdall answer carries usage.cost, and an abandoned call adds no tokens.
- glm F5 (rounding residue of 1e-6), F9 (prompt_usd computed twice on the list path), F4 (a defensive default),
  Grok's P3s (type hints, coupling of the test to the harness): cosmetic, no behaviour change.

Tests after the fixes: 86 provider tests pass (11 for ruling 107). Mutations: 12 of 12 killed before the fixes. The
new branches add list-price fallbacks, which the two new tests pin.
