# Ruling 87 (the shared Heimdall-down signal), cycle 1: consensus

Reviewers (Heimdall-served; the frozen vendors skipped): qwen3.8-27b (308 s, $0.024) "ready for production with one
critical fix"; glm-5.3-flash (555 s, $0.006) "P0 CRITICAL: none - the change is production-ready as-is"; muse-spark-
open-816b (574 s, $0.031): on the change no defect (its answers to the seven questions), its own P0 / P1 items on code
outside the diff. Package: every pp-ingest file in full, the diff since ca17cb97 and CONTEXT.md (the builder's
contract verbatim, its module in full, the decisions A22-A26, seven questions); 502,794 characters. Cycle 1: $0.061.

## Fixed (each verified against the code; a test each in tests/ingest/test_signal.py)
- C1-1 (qwen P0; rated P2 here: an informational line, never a decision): a restart between the STATE write and the
  count of switches seen sent the head again (a duplicate on line 1). `spend.write_switch_head` is now idempotent (a
  head already on the line is not added again); delivery stays at-least-once (a switch is never lost).
- C1-2 (muse Q6; sharper than rated): `_fail` stored the error before its time (two attribute stores, not one atomic
  step), so the health thread could see an error with no time and `check_notice` computed `now - None` (a TypeError:
  one health-loop iteration lost). The time is now stored first and `check_notice` reads one snapshot, tolerating a
  missing time.
- C1-3 (glm D18; more frequent than rated): a probe that finished after a tick was reported only at the END of the
  next tick, after `probe_due` had said "due" again (its `last_probe_utc` not yet stamped): a second probe in the same
  slot (about 1 slot in 6) and a doubled streak. A finished probe is now reported first, and no probe starts while one
  is in flight or its outcome is unreported.
- C1-4 (glm D19): a count of switches seen that is not a number raised on every tick; it is now recorded again (no
  history announced).
- C1-5 (glm D21; in `spend._rewrite_top`, older than this change but now shared by its two new writers): any OSError
  reading STATE was taken as an empty file, so a STATE file that exists but cannot be read would have been rewritten
  as the notice alone (the whole file lost). Only a MISSING file starts empty; any other read error raises. The two
  callers that did not catch OSError now log it and try again (the purge notice's removal clears its record only after
  the notice is gone).
- C1-6 (glm D48): the signal notice is matched under any label (only the signal writes it), so a label change can
  never leave a stale line.
- Found by its test: `write_signal_notice` now creates its lock's directory, as the other notice writers do.

## Refuted (with evidence)
- glm D1 / P2 "a compressed answer lets the 15-minute clock run from a stale failure": its trace contradicts the code.
  A later answer replaces both the earlier answer AND the failure (`noted()`: `pending["answer"], pending["fail"] = t,
  None`), so the flush notes that answer alone; a failure is kept only when it came after the latest answer. muse on
  the same question: "Not a real defect".
- glm P1 "the blocking flock wedges the signal thread": while the shared lock is held no process can change the
  shared state (every write of the module takes it), so a non-blocking reader would have nothing new to report; the
  miner never waits on it (`noted()` is O(1) under a local lock; one thread owns the module, A24); `check_notice` runs
  in the health thread (never blocked) and writes the notice after 30 min, and removes it once the call returns
  (`busy_since` is cleared in `_call`'s finally): "never clears" holds only for a lock that is never released. The
  lock is the module's; a timeout there is the builder's call (REQUESTS R12).
- glm P2 "log the unnoted failures": their cause is logged by `_fail` (one line per distinct cause) and their count is
  in live.json `down_signal.counts.unnoted`.
- muse P0 "rank_score ignores risk in the overlap dedup" (mine.py:481; outside the diff): deliberate. The merged line's
  flags are the union of both observations; adding each observation's own penalty would favour the one that saw FEWER
  flags. Not changed.
- muse P1 "no queue-depth alert": `service._outage_notice` puts "MINING WAITING ON AN OUTAGE: n video(s) ..." at the
  top of STATE after 30 min; live.json carries the queue states.
- muse P1 "Shorts reach the mining queue through the URL check": fetch.py sets every probed `media_type == "short"` to
  SHORT ("never mined (L-u)") before captions or mining.
- Other items outside the diff (a ledger lock beyond service.lock, purge batching, calls-table and log rotation, the
  idle release every 5 s): recorded, not changed here.

## Open (not this change)
- Two probers, one streak (raised by all three): the module's `probe_due` does not claim the probe, so the builder's
  probe and this watcher's can both report in one slot ("3 in a row" from 2 rounds; one's failure resets the other's
  streak). The module's semantics: REQUESTS R12 asks for a claim in `probe_due`. C1-3 removed this watcher's own
  double probe.
- http_4xx counted as "not answered": confirmed (muse; the contract's "down, refused, empty or late").
- The probe waits for a global slot under full mining load (muse Q7: tens of seconds): accepted; the probe matters
  when calls fail, and then the breaker holds the mining calls back.

Tests: tests/ingest 266 passed (22 in test_signal.py).
