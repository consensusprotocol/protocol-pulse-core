# C1 consensus, audit 20261114_2243 (written by the builder; reviewers qwen3.8-27b and glm-5.3-flash, Heimdall;
# Grok not asked: both raised one P1, the same one)

## P1, both reviewers: the wait runs before the call's deadline (_within) starts
A caller that relied on SpendLimit coming back at once (a thread pool with its own timeout, a render) could now stall
for up to 600 s; glm: "either cap the wait by the call's deadline, or show no caller has a budget shorter than 600 s".
ACCEPTED, FIXED: the wait is OPT-IN. Router(reserve_wait_s=0.0) by default: refused at once, exactly as before, for
every caller (the integrator's render among them). Only the ledger build's router opts in
(tests/package/proof_ledger.py build_router: reserve_wait_s=proof_ly.RESERVE_WAIT_S = 600 s). It is a batch job:
step A's workers run under ThreadPoolExecutor.map with no timeout (base pipeline/package.py:588-589), the build's
shadow wait is 900 s (Router.shadow_wait), and no caller in it has a time budget of its own.
Tests: a default router refuses at once with a call in flight (tests/providers/test_reserve_wait.py); the ledger
build's router, built by build_router with every state file in a temporary folder, waits and answers
(tests/package/test_ledger_router.py). Mutations: "the ledger build does not opt in" and "every router waits by
default" are both killed.

## Tagged [P1] by qwen, answered by itself: no defect
qwen's items 5 (the meter's "best") and 7 (the spend-alone refusal) end "This seems correct" / "This is correct"; its
closing count is P1_OR_WORSE: 1 (the item above).

## P2 / P3, by decision
- glm F3 (P3), test timing: FIXED. Each sleep-then-assert is a poll with a deadline (until(...)), then the check.
- glm F4 (P2), the meter does not follow a late answer's replacement (Router._replace_booking): NOT CHANGED. It was
  never followed (before ruling 107 Q1 too); the docstring says so. The cap is the router's ledger, which does follow
  it; the meter feeds the per-package budget only.
- glm F5 (P2), other wrappers with an old signature: CHECKED repo-wide (grep of assignments to Router methods): the
  only fixed-signature wrapper was this one; reply_meter (proof_ly.py) and every test wrapper pass *a, **k.
- glm F15 (P2), a reservation leaked by a raising bare _settle(key) now blocks a waiter for up to 600 s, not 0:
  NOTED. Opt-in only, bounded, and _ledger() drops it when its process ends.
- glm F7 (P3), ledger traffic: _ledger() only reads; one flock and one read per poll per waiting call. No change.
- glm F17 (P3), the free back-end's fast path: unchanged code, covered by test_providers'
  test_the_spend_guard_reserves_the_upper_bound_and_never_passes_the_limit (a free back-end at a $1 limit).
- The other P3s (messages, constants' comments, the cross-test import): no change.
