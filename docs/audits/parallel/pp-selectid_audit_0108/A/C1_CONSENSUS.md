# Audit 0108, package A (the router, the health state, the config, the driver), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes (no P0/P1); qwen3.8-27b SHIP no (two P0s); glm-5.3-flash cut at its 24k-token budget
(finish=length; several "P0" items it re-derives to P1/P2 in its own text).

## Implemented

1. glm (P0-7 re-derived to P1): Router.mode() let heimdall_health.HealthUnreadable, a new exception type, escape
   Router.call. The call sites catch ProviderError, so the build would have crashed rather than recorded "no verdict".
   FIXED: an unreadable health state is ProviderError (no verdict, law L-m), never guessed (tested).
2. glm (P1): announce() rewrote STATE line 1 outside any lock, so a switch written by the probe's thread at the same
   moment could lose a head. FIXED: both go through _prepend(), under the STATE file's own flock, with a per-thread
   tmp name.
3. glm (P0-3 re-derived to P1): the local judge took a torn answer file (read mid-write) as final: Unavailable, the
   40-minute window lost. FIXED: an unreadable answer is polled again until the deadline, and the deadline's message
   names it (tested: a half-written file, then the answer).
4. qwen P0-2: _SEEN (the heartbeat throttle) is shared by the probe thread and the build's threads. Its writes were
   already inside the flock; qwen's "updated after the lock" is not so. The read was outside, so a race could only
   write the same state twice. A module lock now guards both.

## Refuted, with evidence

- glm P0-6, its "highest-risk item" (a hard-coded avoid_vendor={"heimdall"} would skip nothing under heimdall_first's
  re-keying, so a writer's family could judge its own line). There is NO such literal anywhere in pipeline/ or the
  drivers (grep: no `{"heimdall"}`, no `== "heimdall"`). Every avoid set is built from a reply (r.vendor, r.family) or
  from router.backends, which the re-keying itself sets. Router._skip also avoids by FAMILY, and the families stay
  distinct under either routing, so L-s holds even if a vendor string mismatched.
- qwen P0-1 (the local judge "blocks the main thread for 40 minutes"). Ruling 87 names it for exactly one case: step
  A's second verdict when only ONE outside family answers in Plan B. The integrator's judge swaps gemma onto GPU0
  behind a live render, so minutes are its normal answer time. deadline_floor_s 2400 is the agreed wait. The second
  screen runs its batches in a thread pool, and no answer in time is no verdict (fail closed).
- glm P1 (roles not named in plan_b keep their Heimdall chain): this is the design under test (`chain("mine")` stays
  Heimdall). The miner's Plan B is pp-ingest's question, still open with the orchestrator. A Heimdall-only role with
  Heimdall down fails closed.
- glm P1 (the coherence gap: xAI down AND deepseek writing leaves coherence no family). This is ruled. Ruling 88 (d)
  takes glm out of coherence and (e) bars qwen. The gap is documented by TestRuling85NoXai, and the question (glm as
  coherence's last fallback, or fail closed) is on STATE in capitals since 22:13 Nov 13, unanswered.
- glm P0-2, P0-4, P0-5, P0-9, P0-12, P0-13: re-derived in its own text to P2, benign or "not a bug".
