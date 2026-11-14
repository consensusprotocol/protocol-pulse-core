### The order this change answers (orchestrator 10:05 ET Nov 14, to pp-ingest, verbatim)
"ORCHESTRATOR 10:05 to PP-INGEST, your question. RULING 87 AMENDED (the false outage of 09:16-09:22: one 502 on a
calibration call, then silence, and the clock ran while every probe was answering). 'Down' means NO SUCCESSFUL ANSWER
of any kind for 15 minutes: any answered call OR answered probe resets the clock to zero. While the clock is running
the probe goes every 2 minutes, so a single failed call followed by one good probe is never 'down'. A probe must be a
real model call on the family that failed (and one other), not a ping. Plan B opens only when the clock reaches 15
minutes with zero answers; it closes on 3 good probes as now. Every switch still goes on line 1 in capitals; a switch
later found false is marked so, as pp-ingest did (well reported). Your side: the watcher's reading of the signal. The
builder owns the module: it gets the same text now."

### Background
- The shared module (pp-selectid pipeline/heimdall_health.py, the builder's; loaded by path ONCE at the watcher's
  start; API note / mode / probe_due / probe_result) keeps the clock in one JSON state file under an flock. Until its
  amendment, note(True) cleared failing_since and probe_result(True) did NOT ("a probe answer is no verdict answer").
  A second false outage happened at 10:12 ET (the builder's 09:55 build: three glm calls past their deadline at 09:57,
  then no real call; the watcher's probes answered 6 of 6; plan_b 10:12, the paid route open 10:17:43-10:18:53, 0
  calls).
- The builder's amended module (pp-selectid 3cf4c42f, committed 10:32 ET, audited 2 cycles as its audit 1008; loaded by the RUNNING watcher since its restart at 10:36:55 ET, with the watcher's old probe):
  probe_result(True) clears failing_since_utc (and failing_families) and stamps last_answer_utc in BOTH modes, unless
  the answer is older than the failure that started the clock; a failed probe never starts the clock; plan_b closes
  on 3 answers in a row. NEW, optional keywords: note(False, family="<family>") adds the family to failing_families;
  probe_due(families=[...]): while the clock runs in heimdall_first, a prober that can ask NONE of the failed
  families does not claim the slot (the side that can does); in plan_b any prober claims. Families compare as plain
  strings (the builder's: deepseek, glm, qwen; it has no muse).
- The watcher's probe until now: router.run(probe role) over [qwen probe, glm probe], first answer ends it. muse (the
  checker's second family, whose 502 at 09:01 ET started the first false clock) was never probed.
- The watcher's ruling 98 paid route reads the module's failing_since_utc (opens on plan_b AND >= 20 min); with the
  amended module clearing it on any answer in both modes, the route follows the amended definition unchanged.

### The change under review (a6921162 against 2ec81efc: pipeline/ingest/downsignal.py, providers.json, tests/ingest/test_signal.py, design 14)
- providers.json: a "family" on every back-end of the signal's vendor (qwen, glm, muse, deepseek); a new probe-only
  back-end for muse (60 s deadline, one in flight); the probe role's chain = one probe back-end per family the watcher
  calls (qwen, glm, muse) and its note.
- downsignal._start_probe: EVERY back-end of the probe role is asked at once (a thread each, router.run(...,
  only=bid, use_cache=False)); any answer is the probe's answer; the probe is reported with the time of the LATEST
  answer received (not when the slowest family ended: the module's time check); none callable: no probe.
- noted(): each family's FIRST failure after the latest answer is kept (pending["families"]); _flush notes each
  family once, in time order, with family=; a first failure of a back-end naming no family is noted first without
  one, so the clock starts at the first failure. Only when the loaded module's note() takes `family`
  (_takes(fn, name), the pattern of the existing `who` check); otherwise one failure noted as before.
- probe_due gets families=[the probe back-ends' families] when the loaded module takes it.
- No extra note(True) after an answered probe: the amended probe_result does the reset, with its time check.
- tests: the probe asks every family at once (one failing, one answering: answered, both asked); the latest-answer
  time (two answers / one answer and one slow failure, a clock per thread); families on note / probe_due against a
  fake amended module, each once at its first failure; a familyless first failure first; an older module given
  neither keyword; the live config: every enabled back-end of the vendor in any role names a family the probe asks;
  the clock tests run against the amended module at the builder's path. Seven mutations, each caught.

### Questions for the reviewers
1. Does any path report a probe answer with a time later than the latest real answer (which could reset a clock
   started by a newer failure)?
2. Can a failure be lost or noted out of order (an answer's note after a failure's within one flush; a family's first
   failure replaced by a later one)?
3. With an older module (no family / families), are the calls exactly as before?
4. Does the parallel probe hold any lock, thread or slot past its deadline, or start a second probe in its slot?
