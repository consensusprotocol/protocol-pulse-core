# r124: the local model stays the last resort whatever the spend meter says (Nov 17, 21:3x ET)

## Why
- r123 (live since 21:31 ET Nov 17) made the chains' last back-end, the local model on GPU1 under its lease, callable.
  Its startup line then listed the callable back-ends with the LOCAL MODEL FIRST: "callable now: ['local_gemma',
  'heimdall_qwen27b', ...]", because the spend meter had not measured yet in that instant.
- Router.order (integrator B1, Nov 12; orchestrator 02:45 "fall back to the other back-ends rather than halting", 05:30
  "Heimdall mining continues"): while the spend meter is not 'ok' (90 % of the $460 cap, or no reading younger than
  60 min), the METERED back-ends move to the end of every chain, so the others go first; the metered ones are never
  taken out. Every Heimdall back-end is metered (spend_meter: true), so with the local back-end callable, an unmeasured
  or tripped meter would have sent EVERY mining, hook and spotlight request to GPU1 first (a 20 GB model load per
  request, one at a time), against ruling 118 (orchestrator 10:50 ET Nov 16): "Plan B for mining ... is the next
  Heimdall model (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo ...), then the local model on a free card under
  the lease. Heimdall is free and effectively unlimited for us; a video may wait minutes, never hours."
- The meter has been 'ok' at every reading of this watcher's log (never unmeasured, never tripped); its last reading,
  21:31 ET, was 12.4 % of the cap, so no request has gone to the local model. The conflict is latent; r124 closes it
  before the meter could ever go stale (60 min after its last good reading).

## The change
- pipeline/ingest/providers.py Router.order: while the meter is not 'ok', the order is [the others] + [the metered
  ones] + [the last-resort ones] (each in chain order); a back-end is last-resort when providers.json says
  "last_resort": true. Router._last_resort(bid) reads it like _metered. validate_config: "last_resort" must be a bool.
  With the meter 'ok' (or no meter), the chain is used as configured (unchanged).
- pipeline/ingest/providers.json: local_gemma "last_resort": true (and its note).
- tests/ingest/test_r124.py (new): a tripped meter keeps a last-resort back-end last and the gateway answers first; B1
  still puts another (non-metered, non-last-resort) back-end first and never takes the metered ones out; the real
  mine / hook / spotlight chains keep ruling 118's order at every meter state; a non-bool flag is refused.

## Unchanged code the change relies on (not in the diff)
- providers.py Router.effective(role) = [b for b in self.order(role) if b in backends, not frozen (unless lifted),
  enabled()]; Router.run tries `self.order(role)` (or `only`).
- spend.py CreditMeter.state(): 'unmeasured' when no reading is younger than stale_after_s (3600 s), 'tripped' at or
  above 90 % of cap_usd, else 'ok'.
- tests/ingest/test_providers.py test_the_tripwire_notifies_and_moves_the_metered_back_end_last_never_out and
  test_an_unmeasured_spend_is_never_read_as_below_the_tripwire_and_never_halts (B1's own tests) pass unchanged.

## What to check
- B1 holds: the meter only notifies; a metered back-end is never removed; a non-metered, non-last-resort back-end
  still goes first while the meter is not 'ok'.
- Ruling 118's order holds at every meter state for the real chains.
- A back-end both metered and last-resort ends up last (once).

Suite: tests/ingest 443 passed (4 new in test_r124.py). Mutations M65-M68: 4 of 4 killed (M65 restores r123's order:
the tests fail on the code live now); the unmutated control passed.
