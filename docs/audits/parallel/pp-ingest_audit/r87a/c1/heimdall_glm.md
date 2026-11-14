# heimdall_glm (z-ai/glm-5.3-flash, 651.1 s, $0.007, finish stop)

# FORENSIC CODE REVIEW — pp-ingest, ruling 87 amended (a6921162 vs 2ec81efc)

Scope: the diff (downsignal.py, providers.json, test_signal.py) reviewed against the full working-tree files provided. I only report what I can verify from the code shown.

---

## SECTION 1: CORRECTNESS

### 1.1 The four reviewer questions, answered first

**Q1 — Does any path report a probe answer with a time later than the latest real answer?**

No, with one caveat. In `_start_probe.run()` (downsignal.py:372-374):

```python
at = [ts for a, _, ts in got if a is True]       # an answered probe: the LATEST answer's time
self.probe_out = {"t": max(at) if at else self.clock(), ...}
```

`at` collects the third tuple element only from entries where the first element `is True`, i.e. only successful answers. Each successful `ask()` (downsignal.py:351) stamps `self.clock()` **after** `router.run` returns, so `max(at)` is the latest answer's completion time. Correct.

The caveat: the failure entries carry `ts=None` (downsignal.py:354-356), so when *no* back-end answers, `t = self.clock()` — the time the *last* thread finished, which can be up to 60 s after the (nonexistent) answers. That's the documented "else when the last one ended" behavior and only affects the `answered=False`/`None` report, where the module's time check is not the mechanism that resets anything. Fine.

One subtle ordering point: `outs` is a plain dict written by 3+ threads concurrently (downsignal.py:346-358). CPython dict item assignment is atomic under the GIL, and each thread writes a *distinct* key (`outs[bid]`), so there is no lost-update race. The subsequent read `got = [outs[b] for b in sorted(outs)]` (downsignal.py:368) happens after `a.join()` for every thread (downsignal.py:367), so it's properly synchronized by the joins. Correct, though it relies on the GIL's dict-assignment atomicity rather than an explicit lock — acceptable in this codebase's idiom but worth noting.

**Q2 — Can a failure be lost or noted out of order?**

Two findings here.

**(a) Within one flush, the answer's note is always written before the failures' — correct by construction.** `_flush` (downsignal.py:316-340) builds `notes = [(True, p["answer"], None)]` then appends failures, and iterates in order. Since `noted()` (downsignal.py:176-183) clears `fail`/`families` whenever an answer arrives, any failure recorded in `pending` necessarily happened *after* the recorded answer (or there is no answer). The comment "the failures, if any, came after the answer" (downsignal.py:323) is accurate. ✔

**(b) A family's first failure is kept, not replaced — correct.** `noted()` (downsignal.py:181-183):

```python
fam = self._family(bid)
if fam and fam not in self.pending["families"]:
    self.pending["families"][fam] = t
```

First failure per family wins; later failures of the same family within the same pending window are dropped. That matches the design ("each family once, at its first failure after the latest answer"). ✔

**(c) BUT — there is a real ordering defect in the familyless-failure branch.** `_flush` (downsignal.py:324-330):

```python
if p["fail"] is not None and self.note_family and p["families"]:
    fams = sorted(p["families"].items(), key=lambda kv: kv[1])
    if p["fail"] < fams[0][1]:
        notes.append((False, p["fail"], None))
    notes += [(False, t, f) for f, t in fams]
else:
    notes.append((False, p["fail"], None))
```

The design says: "a first failure of a back-end naming no family is noted first, without one, so the clock starts at it" (design §14; the diff's test list: "a familyless first failure first"). The code implements this by comparing `p["fail"] < fams[0][1]` — the familyless failure's time against the *earliest* family failure. That's correct when the familyless failure is genuinely first. But consider: familyless failure at t=10, family failure (glm) at t=5. Then `p["fail"]=10`, `fams[0][1]=5`, so `10 < 5` is False, the familyless note is appended *after* the family note, and the module's clock would start at t=5 (the family note) rather than t=10. Is that wrong? Actually no — the module's clock should start at the *first* failure, which is t=5 (the family one). The familyless note at t=10 arriving second is the correct time order. So the logic is: familyless failure noted first *only if* it is actually earlier. That is the right behavior, and the design's wording ("a first failure of a back-end naming no family is noted first") is slightly stronger than the code, but the code's behavior (strict time order, familyless-without-family noted at its own time) is the defensible reading. However — note the failure of the *familyless* back-end is noted **without** a family, and if the familyless failure is later than all family failures, the module receives: family note (t=5), then familyless note (t=10). If the module's `note(False, family=...)` treats a familyless note as "a failure with no family" and starts/keeps the clock at it, the clock would be *reset forward* to t=10 even though a failure at t=5 was already recorded. Whether that's a bug depends on the module's semantics (not shown). The watcher's side is self-consistent; I flag it as a **semantic coupling risk**, not a verified defect.

**(d) A subtler loss: `noted()` clears `families` on answer, but a failure arriving between the answer's note-time and the flush.** Sequence: answer at t=1 noted into pending; failure at t=2 noted (fail=2, families={glm:2}); flush at t=3 notes (True,1) then (False,2,glm). Fine. Now: failure at t=1 (fail=1, fam glm:1); answer at t=2 → `pending["answer"]=2, fail=None, families={}`; failure at t=3 (fail=3, fam glm:3). Flush notes (True,2) then (False,3,glm). The t=1 failure is *lost* — but it's lost by design: the answer at t=2 proves the family answered after it, so the amended clock resets at t=2 anyway. The design says "each family once, at its first failure after the latest answer" — t=3 is the first failure after the latest answer (t=2). Correct. ✔

**(e) One genuine ordering hazard: `noted()` runs under `self.lock` but `_flush` swaps `pending` under the same lock, then calls the module *outside* it.** If a note call to the module fails (`m is None`, downsignal.py:336-337), the outcome is counted in `n["unnoted"]` and dropped — it is not re-queued. So a transient module failure (lock held, state unreadable) loses that note. The design accepts this ("the router's threads only leave a pending outcome... so a held or stuck shared lock never stalls the miner"), and the next real call will re-note. But consider: the *last* failure before a long quiet period is lost to a module error; the module's clock then keeps running from an earlier failure (or none), and the 15-min rule fires late or never. The watcher's own `mode()` call every 30 s (downsignal.py:206) re-reads the state, so the *mode* is still the module's truth; only the note is lost. Acceptable, but it means "no answer of any kind for 15 minutes" can be *undercounted* (clock started later than the true first failure) → a false *up* persists longer than 15 min. Given the amended rule's purpose (kill false *downs*), this errs in the safer direction. Noted, not a defect.

**Q3 — With an older module (no `family`/`families`), are the calls exactly as before?**

Almost. Verified:

- `note`: `**({"family": fam} if fam else {})` (downsignal.py:334-335). When `note_family` is False, `fam` is always... wait, no. `note_family` gates the *whole* family branch (downsignal.py:324), so when False, the else-branch appends `(False, p["fail"], None)` — `fam=None` — and the `**({} if fam else {})` yields no kwarg. But when `note_family` is True and a *specific* note has `fam=None` (the familyless failure, or the answer note), the kwarg is also omitted. So: older module → no `family` kwarg ever. ✔ Exactly as before.
- `probe_due`: `families` added to `self.probe_kw` only when `_takes(self.hh.probe_due, "families")` (downsignal.py:154-155). Older module → not in `probe_kw` → not passed. ✔
- `_start_probe` itself doesn't change its call into the router based on module capabilities — it always asks every back-end of the probe role. With an older module, the *probe behavior* changes (parallel, all families) even though the module is old. That's intentional per the diff ("the watcher's ruling 87 amended probe" is a watcher-side change), and the amended *reset* semantics only come from the amended module. With the old module + parallel probe: `probe_result(True)` did not reset the clock in the old module, so a false-down could still occur — but the diff's background says the running watcher loaded the amended module at 10:36:55. The *code* handles both; the *deployed pairing* is amended-module + amended-watcher. ✔ (Worth noting: the watcher now probes muse even against the old module, which costs one extra 60-s-deadline call per probe and changes probe cadence — a behavioral, not correctness, difference.)

**Q4 — Does the parallel probe hold any lock, thread or slot past its deadline, or start a second probe in its slot?**

- **Locks:** `ask()` calls `router.run(...)` which acquires `self.sems[bid]`/`self.gsem` (providers.py:945) and the throttle/health locks transiently. The probe role has `breaker: false` (providers.json:130) → `_NoHealth` (providers.py:642-651), so no health-lock. Each probe back-end has `max_inflight: 1` (providers.json:84, 92, 101) → its own semaphore; three different back-ends → three different semaphores, no contention. The global semaphore (`gsem`, 20) is acquired by 3 probe threads — fine. No lock is held across the 60-s deadline; the semaphore is released in the `with` (providers.py:945-951). ✔
- **Threads:** `run()` joins all ask-threads (downsignal.py:367) before writing `probe_out` under `self.lock` (downsignal.py:373). The ask-threads are daemon, so a stuck `router.run` (e.g. a hung socket beyond the 60-s timeout — shouldn't happen, but) would block `run()` forever, and `probe_out` would never be set → `_probing()` (downsignal.py:297-302) returns True forever → no further probe. Is there a watchdog? No. `router.run` → `_try` → `b.complete` → `_request` with `timeout=60` (providers.json:84/92/101, `timeout_s: 60`) → `urllib` socket timeout. Plus `Throttle.wait()` (providers.py:664-670) sleeps in 5-s increments while `until` is in the future — the probe role's throttle could be hit by... no, the probe back-ends are separate Throttle instances keyed by bid (providers.py:768), and the probe role is the *only* role using those back-ends. But: `Throttle.hit` is shared per back-end; if a probe gets a 429, `th.hit(retry_after)` sets `until` — with `attempts: 1` (providers.json:129) and `transport_retries: 0`, the 429 path (providers.py:963-969) checks `r.retryable and transport_left > 0` → 0, so it falls to `h.record` (a `_NoHealth`, no-op) and returns `("unavailable"|"rejected", ...)`. Wait — for the probe role, `attempts=1`, so the while loop runs once; a 429 → `th.hit` → then `r.retryable and transport_left>0` is False → `h.record(False,...)` (no-op) → return. So the thread ends. But `th.wait()` at the *top* of the loop (providers.py:942) — with attempts=1, the loop runs once, `th.wait()` waits for any *pre-existing* throttle delay on that back-end. Since only the probe uses these back-ends, the only way `until` is set is a prior probe's 429. Then the *next* probe's ask-thread waits up to 60 s (max_s) *before* its 60-s deadline call — total up to 120 s. Meanwhile the module's probe interval is 120 s (downsignal.py:44 comment). So a probe could still be in its throttle-wait when the next `probe_due` fires — but `_probing()` (downsignal.py:297-302) returns True while `probe_thread.is_alive()`, and `probe_out` is only set after all joins. So the next probe is skipped until the current one finishes. ✔ No second probe in its slot. (The `probe_out is not None` half of `_probing` covers the finished-but-unreported window; `_report_probe` runs at the *top* of the next tick, before `probe_due` — downsignal.py:202-203, 216 — so the slot is freed before the next claim. ✔)

- **One more: the ask-threads' `outs` writes.** Already covered — distinct keys, GIL-atomic. But note `ask()` catches `providers.AllBackendsFailed` and generic `Exception`; it does *not* catch `BaseException`. A `KeyboardInterrupt` in an ask-thread (only delivered to the main thread in CPython) — not an issue. A `SystemExit`? Also main-thread. Fine.

### 1.2 Other correctness findings in the diff

**F1 (real, minor): `answered` computation can mask a partial failure.** downsignal.py:369-370:

```python
answered = True if any(a is True for a, _, _ in got) else False if any(a is False for a, _, _ in got) else None
```

If qwen answers (True) and muse fails (False), `answered=True`. Correct per the amended ruling ("any answer is the probe's answer"). If *all* are `None` (nothing callable), `answered=None` → "no probe". If some are False and none True → `answered=False` → a *failed* probe, reported to `probe_result(False)`. Per the amended module, "a failed probe never starts the clock" — correct. ✔ But: the *why* string (downsignal.py:371) joins every back-end's why, including the successful one's "answered in Ns" — so a successful probe's evidence line (downsignal.py:390-391) reads e.g. "qwen answered in 2 s; glm: heimdall_glm53flash_probe unavailable (timeout:...); muse...". That's *good* forensics. ✔

**F2 (minor): `why` for the not-called case.** downsignal.py:371: `why = "; ".join(w for _, w, _ in got) or "the probe role names no back-end"`. If `outs` is empty (probe role chain empty — impossible, `load_config` requires ≥2 back-ends per role, providers.py:158-160), `got=[]`, `answered=None`, why = the fallback. Dead-but-correct branch. ✔

**F3 (minor): `ask()`'s success tuple.** downsignal.py:351: `outs[bid] = (True, f"{bid} answered in {self.clock() - t0:.0f} s", self.clock())`. The *second* element is a human string; the *third* is the timestamp. In the failure paths (downsignal.py:354-356, 358) the third element is `None`. Then `at = [ts for a, _, ts in got if a is True]` — only successes contribute. Consistent. ✔

**F4 (real, low): the drill check inside the probe.** downsignal.py:209-215: while any probe back-end is under an override, *no probe at all* is started (`drills` non-empty → skip). With three probe back-ends, a drill on *one* (e.g. the outage drill overrides `heimdall_qwen27b_probe`) now suppresses probes of *all three* families — including the families that were not affected. Before the change, the drill suppressed the (2-back-end) probe too, so this is not a regression, but the amended ruling's "a probe is a real model call on the family that failed" is weakened during any drill: a drill on qwen-probe stops glm/muse probes, so a muse-only failure's clock cannot be reset by probe until the drill ends. The drill is a test-time construct, so impact is low. Worth noting.

**F5 (real, low): `noted()`'s drill accounting.** downsignal.py:174-175: a drill increments `pending["drills"]`, and `_flush` (downsignal.py:319-322) sends ONE `note(False, drill=True)` for the whole window regardless of how many drill calls happened. The count of drill calls is thereby collapsed. Design says "recorded, never counted" — consistent. ✔

**F6 (real, medium — pre-existing, but the diff's Q2 touches it): `_flush`'s note ordering vs. the module's clock.** The answer note is sent first with `now=_utc(p["answer"])` (the *call's* time), then failures with their times. If the module's `note(answered=True, now=T1)` clears `failing_since` and stamps `last_answer=T1`, and then `note(False, now=T2, family=glm)` with T2>T1 adds the family — the module's clock starts at T2. Correct. But if the *same* flush carries an answer at T1 and a failure at T0<T1 (possible? `noted()` clears fail on answer, so a failure recorded in pending after an answer has t>answer... unless the *answer* arrived, then a *failure* arrived, then *another* answer arrived — then fail=None again. So no, within one pending window, fail > answer always, when both exist). ✔ Verified: the invariant "fail, if present, is later than answer, if present" holds because `noted()` (downsignal.py:176-183) resets both together on answer.

**F7 (real, low): `probe_kw`'s `families` is computed once at construction** (downsignal.py:153-155) from `self.router.chain(self.probe_role)`. If providers.json's probe role changes at runtime (it can't — the config is loaded once), this is fine. But it also means the *families the probe asks* are fixed at start; if a back-end is later disabled via... no, `enabled` is read from the config, also fixed. ✔ (The `Overrides` mechanism changes `base_url` only, not the chain.)

**F8 (real, low): `_family` reads `self.router.cfg["backends"]`** (downsignal.py:188-190) — the *full* config, including disabled back-ends. A failure noted from a disabled back-end can't happen (a disabled back-end is skipped, not called — providers.py:857-859 marks it "skipped", and `noted` is only called from `_on_attempt` which fires on real attempts... wait, does `_on_attempt` fire for skipped back-ends? `Router.run` (providers.py:846-860) appends to `tried` and `continue`s — no `_emit` for skipped. `_emit` fires in `_try` (providers.py:961, 986, 990) and in `_cached` (providers.py:921). So `noted` sees only: cache hits (kind="cache" → NO_CALL, correctly skipped, downsignal.py:49, 170), real attempts. ✔ But: a *cached* reply for a probe back-end — the probe role passes `use_cache=False` (downsignal.py:350), so no. And the design says "No note for a stored reply" — enforced by `NO_CALL = frozenset({"cache", "disabled"})` (downsignal.py:49) plus the `role == probe_role` exclusion (downsignal.py:170). Wait — the probe role's *own* attempts are excluded from notes (downsignal.py:170: `rec.get("role") == self.probe_role`), because "a probe call's attempt (the probe reports its own outcome, below)". But the probe's outcome reaches the module via `probe_result`, not via `note`. So the module's `last_answer` is stamped by `probe_result` (the amended module), not by `note`. Consistent. ✔

**F9 (real, medium): the `noted()` exclusion of the probe role means the *mining* calls' failures still note — but what about the *flagcheck*/*hook*/*spotlight* roles?** They're Heimdall back-ends, they're real calls, they note. Design: "every real call of the watcher to a back-end of providers.json down_signal.vendor (mining, hooks, the second-model check) is one outcome". ✔ Verified: `noted` filters only by vendor (downsignal.py:170) and probe-role, not by role otherwise.

**F10 (real, low): `snapshot()`'s new keys.** downsignal.py:512-513: `probe_families`, `failures_noted_with_family` — these go into live.json via `stats.live` (stats.py:148). Additive; no consumer breaks. ✔

**F11 (real, low): the `ask()` closure's `outs` dict and the `sorted(outs)` read.** If two ask-threads have the same `bid`... impossible, `chain` is a list of unique ids (validated: `validate_config` checks chain members exist; duplicates? `validate_config` (providers.py:116-119) does NOT check for duplicate ids in a chain. If providers.json had a duplicate, `asks` would have two threads writing `outs[bid]` — last-write-wins, and `got` would have one entry. Not a defect, just noting the validation gap. The shipped config has no duplicates (providers.json:129).

**F12 (real, low): `_start_probe`'s thread-per-back-end.** Three threads per probe, created and joined each probe. At a 120-s probe cadence, negligible. But these threads are *unbounded* if the probe role's chain grows — still bounded by the chain length. ✔

**F13 (real, medium): the probe's `router.run` with `only=bid`** (downsignal.py:350). Looking at `Router.run` (providers.py:837-885): with `only`, `chain = [only]` (providers.py:840). Then the cache check (providers.py:851-856): `use_cache=False` → skipped. Then `available(bid, breaker, lifted)` (providers.py:857): `breaker` = `rc.get("breaker", True) is not False` → the probe role has `breaker: false` → `breaker=False` → `available` returns `(True, "")` without consulting the health (providers.py:806-818, the `if breaker else (True, "")` at 818). ✔ Then `_try` with `h = _NoHealth` (providers.py:935). ✔ Then the throttle: `th.wait()` (providers.py:942) — the probe back-ends' throttles. Then the semaphore + `gsem`. Then `b.complete` with the 60-s timeout. On failure: `BackendError` → `r.retryable` (timeout → RETRY) and `transport_left = 0` → no retry → `h.record` (no-op) → return `("unavailable", ...)`. So `run` collects `tried` and, after the single-element chain, raises `AllBackendsFailed` with `outage = all(s != "rejected" ...)` → for a timeout, s="unavailable" → outage=True. In `ask()`, `called = any(s in ("unavailable","rejected") ...)` → True → `outs[bid] = (False, why, None)`. ✔ Correct: a timed-out probe back-end is a *failed* probe of that family, not "not called".

**F14 (real, low): what if the probe back-end's *key* is missing?** `Backend._key` (providers.py:259-265) raises `BackendError("disabled", ...)` — kind "disabled" is in neither RETRY nor... it's returned from `complete` as a raised BackendError; in `_try` (providers.py:948-949) it's caught, `r.kind="disabled"`, not in RETRY... wait, `RETRY = frozenset({"network","timeout","http_429","overloaded","server","empty"})` (providers.py:44) — "disabled" not in it → not retried → `h.record` (no-op) → return `("unavailable", "disabled: ...")` (since "disabled" not in REJECTED). Then `AllBackendsFailed.outage` = True. In `ask()`: `called = any(s in ("unavailable","rejected"))` → True → `(False, why, None)`. So a missing key yields a *failed* probe, not "no probe". Design: "No note for... a missing key (no call)" — that's about `noted`, and the probe role's attempts are excluded from `noted` anyway. But for `probe_result`: the design says "a probe whose back-ends could not be called is no probe". Is a missing key "could not be called"? The code says it *was* called and failed (s="unavailable"). Hmm — `available()` (providers.py:813) checks `b.enabled()`, which for OpenAICompatBackend is `cfg.get("enabled", True)` — the *config* flag, not key presence. Key presence is only discovered inside `complete`. So a missing key → the call is *attempted* → fails with "disabled" → counted as a failed probe. Defensible. The `ask()`'s `None` (not-called) case only arises when `available()` returns False — i.e. frozen/disabled/budget/circuit — but the probe role has `breaker: false` so circuit never; frozen: the probe back-ends' vendor is "heimdall", not in the freeze list (providers.json:5-6: openai, anthropic, xai, google) → never frozen; disabled: only if someone edits the config. So in practice `None` is nearly unreachable. ✔

**F15 (real, low): `_report_probe`'s retention.** downsignal.py:396-404: if the module's `probe_result` call fails, the outcome is kept while younger than `PROBE_EVERY_S` (default 120, read via `getattr(self.hh, "PROBE_EVERY_S", 120)`). With the amended module, `probe_result` also *writes* the state file — a failure there means the state is unreadable; the retry at the next tick (5 s later) is the right behavior. ✔ But note: the *evidence* line (downsignal.py:388-391) is written once, before the report — so a probe whose report ultimately fails after 120 s is still evidenced. Good.

**F16 (real, low): the `answered` tri-state vs. `probe_result(answered)`.** downsignal.py:396: `self._call("probe_result", answered, ...)` — passes the *boolean* (True/False; `None` already returned at 392-395). The amended module's `probe_result(True)` resets; `probe_result(False)` — "a failed probe never starts the clock". ✔

**F17 (pre-existing, touched by the diff): `_flush`'s drill note.** downsignal.py:319-322: the drill note is sent *before* the answer/failure notes, with `now=_utc(self.clock())` — the *flush* time, not the drill call's time. Minor imprecision in the recorded time; drills are "recorded, never counted", so no clock impact. ✔

**F18 (real, low): `head()`'s `plan_b_tail` for ruling 98.** downsignal.py:93-112, 124-130: when `paid` is configured, the tail says "NEW UPLOADS ON GROK, THEN GEMINI AFTER 20 MINUTES DOWN, CAPPED". This goes into every *switch* head. But the *builder's* switches (from the shared state, `head(rec, ...)` at downsignal.py:440) also get this tail — attributing the watcher's Plan B to the builder's switch. Design: "plus who made it and the miner's Plan B". ✔ Intentional.

**F19 (real, medium): the paid route's open condition vs. the amended module.** `_route_tick` (downsignal.py:241-263): opens when `v.get("mode") == DOWN` and `fs_t` (failing_since) is ≥ `after_down_s` old. With the amended module, `failing_since_utc` is cleared by any answer (call or probe) in both modes — so the route closes... wait, the route *closes* only when `v.get("mode") == self.up` (downsignal.py:264). If the mode is still `plan_b` but the failure clock was just cleared by an answer, the route stays open (correct: it opened at 20 min; the mode flips to up only after 3 good probes). But: the route's *spend* continues while `plan_b` even though answers are flowing. Is that per ruling 98? "OPENS... when... no Heimdall family has answered for 20 min running. CLOSES at the signal's back switch (3 good probes)." ✔ Exactly as ruled. And the diff's background: "with the amended module clearing it on any answer in both modes, the route follows the amended definition unchanged" — verified: the route's *open* condition reads `failing_since_utc` (downsignal.py:242-257), which the amended module now clears aggressively, so a route that would have opened at 10:17 (the 10:12 false outage) now... the 10:12 case: three glm calls past deadline at 09:57, then no real call, probes answering 6/6. With the amended module, `probe_result(True)` clears `failing_since` → the route never opens. ✔ That's the fix working.

**F20 (real, low): `_route_tick`'s `fs_t` parsing.** downsignal.py:244-248: `datetime.fromisoformat(str(fs).replace("Z", "+00:00"))`; `fs_t = d.timestamp() if d.tzinfo is not None else None`. A zoneless time → `fs_t=None` → "not opened" (fail closed). ✔ Matches the test `test_a_failure_clock_without_its_zone_never_opens_the_route`.

**F21 (real, low): `_cap_check`'s day.** downsignal.py:280: `datetime.fromtimestamp(now, ET).date().isoformat()` — ET day. The cap's `RoleCaps._roll` (providers.py:697-703) also uses ET. Consistent. ✔

**F22 (real, low): the `probe` role's `max_tokens: 512`** (providers.json:130) with muse's "default reasoning" — the note says 512 gives "room for the second family's default reasoning" (providers.json:131). But heimdall_muse's own note (providers.json:42) says its *default* reasoning on a 100k package used a whole 16k budget; the probe prompt is tiny ("Reply with the single word OK."), so 512 is plausible. If muse reasons past 512 → `finish_reason: length` → `content` = whatever it produced (possibly empty) → `BackendError("empty", ...)` (providers.py:388-390) → kind "empty" ∈ RETRY, but `transport_retries: 0` → no retry → "unavailable" → a failed probe. Then muse's clock... the *other* families' answers still reset the clock (amended: any answer). But the *muse* family's failure — the amended module tracks `failing_families`; a muse probe failure adds muse to failing_families (via the watcher's `note`? No — the probe's outcome goes to `probe_result`, which doesn't take a family). So a muse-only probe failure, with qwen/glm answering, resets the clock (probe_result(True)) but leaves muse in the module's failing_families? That's the module's concern, not the watcher's. The watcher's side: `probe_result(True, ...)` — the amended module "clears failing_since_utc (and failing_families)". So a muse 502 followed by a qwen probe answer clears *both* — including muse's family flag. Is that per the amended ruling? "any answered call OR answered probe resets the clock" — the *clock*, yes; whether it clears the *family* set is the module's choice (the diff's background says the amended module clears both). The watcher passes no family to `probe_result` (downsignal.py:396) — the module can't know which family answered. Design limitation, acknowledged in the diff's background ("FAMILIES... the builder's amended API"). The watcher *could* pass the answering families; it doesn't. Minor.

**F23 (real, low): `ask()`'s `t0`/latency.** downsignal.py:347: `t0 = self.clock()`; the success message computes `self.clock() - t0`. If the throttle made it wait, that's included. Cosmetic.

**F24 (real, low): the evidence record for a probe.** downsignal.py:390-391: `self._evidence({"kind": "probe", "utc": _iso(t), "answered": answered, "why": why[:300], "by": WHO})` — written once, before the report. If the report later succeeds, no second evidence line. Fine.

**F25 (real, low): `noted()`'s exception swallowing.** downsignal.py:184-185: `except Exception: pass`. A bug in `_family` (e.g. `self.router` None — impossible, set in `__init__` before any `noted`... actually `self.hsig` is created after `self.router` in `Service.__init__` (service.py:118-124), so `noted` (called via `_on_attempt` → `self.hsig.noted(rec)`, service.py:192-193) always has a valid router. ✔ But: `self.hsig` is read *before* it's assigned? `_on_attempt` checks `if self.hsig is not None` (service.py:192); `self.hsig = None` is set at service.py:117, *before* the Router is constructed (service.py:118) — and the Router's `on_attempt` fires only during calls, which happen after `__init__`. ✔

**F26 (real, low): the diff's docstring change.** downsignal.py:8: "a probe call's attempt (the probe reports its own outcome, below)" — matches the code (`noted` skips the probe role, downsignal.py:170). ✔

**F27 (real, low): `providers.json`'s muse probe duplicates the muse model/price.** The design's law: "no vendor / model name outside the provider config" — both are *in* the config. But there's a test: "a test reads every identifier and string of the package for them" (design §6). The muse model string now appears twice in providers.json (lines 40 and 98) — both in the config, so compliant. ✔

**F28 (real, low): the probe role's chain order.** providers.json:129: qwen, glm, muse. With `only=bid` per ask-thread, order is irrelevant. ✔

**F29 (real, low): `_start_probe`'s `why` when a back-end succeeds.** Its why ("qwen answered in 2 s") is joined into the failure why-string even when `answered=True` — the evidence line then mixes success and failure text. Readable. ✔

**F30 (real, low): the `at`-list when the *same* back-end answers twice.** Impossible (one ask-thread per bid, one `router.run` each, `attempts: 1`). ✔

**F31 (real, low): `probe_out`'s `t` when answered.** `max(at)` — the *latest* answer. The amended module's check: "unless the answer is older than the failure that started the clock". If the latest answer's completion is *after* the failure that started the clock (it must be — the failure preceded the probe), the reset applies. But: could the latest answer be *older* than a *newer* failure? Sequence: failure at T0 (noted, clock starts); probe starts at T1>T0; qwen answers at T2; muse fails at T3>T2 (its ask-thread's `router.run` raised after qwen's returned — possible: muse's 60-s deadline vs qwen's 2-s answer). Then `at=[T2]`, `t=T2`. The module: `probe_result(True, now=T2)` — "resets it... unless the answer is older than the failure that started it". T2 > T0 → resets. But muse *failed* at T3 > T2 — the module's clock, if it also tracks the muse failure (via the watcher's `note`? No — the probe's failures are not noted, they're the probe's outcome). So the muse failure at T3 is *invisible* to the module except as part of the probe's `answered=True` (since qwen answered). Then: no further real call, no further probe (the clock was reset, so `probe_due` returns... the module's `probe_due` — "while the clock runs" — if the clock was reset, no probe is due until a new failure). So: muse fails at T3 (inside the probe), qwen's answer at T2 resets the clock, muse's failure at T3 is never noted, the clock is cleared, and if muse then keeps failing *in mining*, those failures note (they're real calls) — but if there are no mining calls (quiet watcher), muse's continued failure is invisible until the next mining call or probe. Is that per the amended ruling? "any answered call OR answered probe resets the clock" — yes, the qwen answer *is* an answered probe. The ruling's intent (kill false downs) is served. The cost: a muse-only outage is now *less* detectable (its failures are masked by other families' answers). That's the ruling's trade, not a bug. ✔

**F32 (real, low): the `ask`-thread's `outs[bid]` write vs. the `run`-thread's read — memory visibility.** Under CPython's GIL, the `join()` provides a happens-before. ✔

**F33 (real, low): `sorted(outs)`** — deterministic order for the why-string. Nice for reproducible evidence. ✔

**F34 (real, low): the diff's test claim "Seven mutations, each caught"** — I cannot verify the tests' bodies (not shown), only their names (test_signal.py:~40 tests). The named tests cover: parallel probe (one failing, one answering), latest-answer time, families on note/probe_due, familyless-first, older module, live-config family coverage, amended-module clock tests. Matches the diff's claims. ✔ (Unverifiable beyond names.)

**F35 (real, low): `providers.json`'s muse probe `extra_body: reasoning effort none`** (providers.json:99) — consistent with heimdall_muse (line 41). But the *glm* probe (line 87-93) has NO extra_body — glm's default reasoning. The glm *main* back-end's note (line 32) says its default reasoning used a whole 16k budget on a 111k package; the probe's 512 tokens (line 130) with glm's default reasoning: the note at line 91 says "512 tokens: room for the second family's default reasoning" — but glm's default reasoning on even a tiny prompt: the calibration note (line 32) says "about 300 reply tokens" for the flag-check. So 512 is enough for the *probe* ("Reply with the single word OK."). Plausible. But it's a *measured* assumption, not a guarantee — if glm's reasoning on the trivial prompt ever exceeds 512−(prompt tokens), the glm probe fails with "empty"/length. Then: qwen and muse answers still reset the clock. Low impact. ✔

**F36 (real, low): the `probe` role's `attempts: 1`** (providers.json:129) — one attempt per back-end. With `only=bid`, `run` tries that one back-end once. If it 429s, no retry, no next back-end (chain=[only]). → failed probe of that family. Correct per "no transport retry (each back-end's 60 s deadline is the probe's)". ✔

**F37 (real, low): the `spend_meter: true` on the muse probe** (providers.json:101) — its costs (tiny) now count toward the Heimdall meter's `local_since` (providers.py:959-960, 976-977). Negligible. ✔

**F38 (real, low): the diff's `snapshot()` additions** — `probe_families` could leak... it's a list of family *names* ("qwen","glm","muse"), not secrets. ✔

**F39 (real, low): `_takes`'s failure mode.** downsignal.py:71-76: returns False when the signature can't be read (e.g. a C function or a wrapped callable). Then `note_family=False` → failures noted without family (old behavior), and `families` not passed to `probe_due`. Fail-closed to the *old* behavior. ✔ Matches the test `test_a_probe_due_whose_signature_cannot_be_read_is_called_without_a_name` (and, by symmetry, the family one).

**F40 (real, low): the `families` kwarg's *value* when some probe back-ends have no family.** downsignal.py:153: `fams = sorted({f for f in map(self._family, self.router.chain(self.probe_role)) if f})` — familyless back-ends are dropped from the *claim's* families. If the module's `probe_due(families=...)` semantics are "claim only if you can ask one of these", a familyless probe back-end's ask-ability is not represented. In the shipped config, all three probe back-ends have families. If someone added a familyless one, its family would be silently absent from the claim. Low.

**F41 (real, low): the `note` call's `family` when `note_family` is True but the *specific* failure's back-end has no family.** downsignal.py:324-330: the `if` branch requires `p["families"]` non-empty; a familyless failure with `p["fail"]` set but no families → else-branch → `(False, p["fail"], None)` → no family kwarg. ✔ But: a *mixed* case — familyless failure at T1, family failure at T2>T1, `note_family=True`, `p["families"]={glm:T2}`. Then `p["fail"]=T1 < fams[0][1]=T2` → notes = [(True,answer,None)?, (False,T1,None), (False,T2,glm)]. The familyless note (no family) goes first, then the family note. The module: the familyless note starts the clock at T1 (per the diff's background: "a first failure of a back-end naming no family is noted first, without one, so the clock starts at it"). ✔ Then the glm note at T2 adds glm to failing_families. Correct.

**F42 (real, low): what if `p["fail"]` is not None but `p["families"]` is empty AND `note_family` is True?** → else-branch → one note without family. ✔ (The `if` requires `p["families"]` truthy.)

**F43 (real, low): the `notes` list when `p["answer"]` is None and there are no failures.** `notes = [(True, None, None)]` → the loop skips it (`if t is None: continue`). ✔

**F44 (real, low): `_flush`'s `self.mode = m`** (downsignal.py:339) — the *last* note's returned mode wins. If the module's `note` returns the mode after each note, the final `self.mode` reflects the last note's post-state. Since notes are in time order, the last note's mode is the most recent. ✔

**F45 (real, low): the diff's `providers.json` note for the probe role** (line 131) — it says "EVERY back-end here... is asked at once, one call each, any answer is the probe's answer, and an answered probe is noted as an answer". "noted as an answer" — via `probe_result`, not `note` (the probe role's attempts are excluded from `noted`). The note's wording is slightly loose but the design §14 clarifies. ✔

**F46 (real, low): the `heimdall_muse_probe`'s `timeout_s: 60`** (line 101) — matches the builder's 60-s probe deadline (design §14: "the builder's 60 s deadline"). ✔

**F47 (real, low): the `ask`-threads' names** (`probe87-<bid>`, downsignal.py:362) — good for debugging. ✔

**F48 (real, low): the `run`-thread's name** (`probe87`, downsignal.py:376) — one per probe; if a previous probe's thread is somehow still alive (it can't be — `_probing` gates), a second `probe87` thread could exist. `_start_probe` is only called when `not self._probing()` (downsignal.py:208, 216-218). ✔

**F49 (real, low): `_probing`'s second check** (downsignal.py:301-302): `return self.probe_out is not None` — a finished-but-unreported probe blocks a new one. `_report_probe` runs at the *top* of the next tick (downsignal.py:202), *before* the `probe_due` check (downsignal.py:216). So the window is: probe finishes → (up to 5 s) → next tick reports it → then `probe_due` may claim. ✔ No second probe in its slot. (Test: `test_a_finished_probe_is_reported_before_another_is_started`.)

**F50 (real, low): the `probe_out`'s `logged` flag** (downsignal.py:374, 388-390) — ensures the evidence line is written exactly once even if the report is retried. ✔

**Summary of correctness:** No production-breaking defect found in the diff. The design is careful; the invariants (fail-after-answer within a pending window; first-failure-per-family; latest-answer time; no second probe in a slot) all hold. The notable *semantic* risks are: (i) the muse-family masking (F31/F22) — a ruling-87-amended consequence, not a bug; (ii) the drill suppressing all families' probes (F4); (iii) the module's `probe_result` not learning *which* family answered (F22) — a watcher-side limitation the diff acknowledges.

### 1.3 N+1 / performance

- `_flush`'s note calls: one module call per note, each acquiring the module's flock and rewriting the state JSON. With 3 families + 1 answer, up to 4 flock+JSON-write cycles per flush, every 5 s. The module's cost is unknown (not shown), but the *watcher* side is O(failures+1). Acceptable.
- `noted()` is O(1) (design: "the signal thread writes the shared file"; the router's threads only touch `pending` under a local lock). ✔ Verified: downsignal.py:166-185 — no I/O.
- The probe: 3 threads × 1 HTTP call each, at most once per 120 s. Negligible.
- `stats.live`'s `usd_all_time_by_vendor` (stats.py:86-87): a full-table aggregate over `calls` every 60 s — the docstring (stats.py:4-5) acknowledges it ("cheap at ~1,000 calls a day"). Pre-existing, not in the diff.

### 1.4 Edge cases

- **Empty probe chain:** impossible (load_config requires ≥2, providers.py:158-160); the `got`-empty branch (downsignal.py:371) is dead but correct.
- **All probe back-ends under override:** downsignal.py:209-215 — no probe; `probe_due` was already claimed (downsignal.py:216-218: `if self._call("probe_due", ...): self._start_probe()`). Wait — read carefully:

```python
if self._call("probe_due", now=_utc(now), **self.probe_kw):   # True claims the slot (11ed255f):
    self._start_probe()      # a probe this watcher then cannot make sends no probe_result and the
                             # slot stays spent from its claim (the builder's semantics)
```

And *before* that (downsignal.py:208-215):

```python
if not self._probing():
    drills = [b for b in self.router.chain(self.probe_role) if self._drill(b)]
    if drills:
        ...self.drill_logged = True
    else:
        self.drill_logged = False
        if self._call("probe_due", ...):
            self._start_probe()
```

So during a drill, `probe_due` is *not called* → no slot claimed → no wasted slot. ✔ (The comment "a slot claimed and then not probed stays spent" applies to the case where `probe_due` returns True but `_start_probe`'s threads all fail to call — e.g. all back-ends frozen. Then `ask` raises... no: `router.run(only=bid)` with a frozen bid → `available` returns (False, "spend freeze...") → `tried=[(bid,"skipped",...)]` → `AllBackendsFailed` with outage=True (all "skipped" ≠ "rejected") → `called = any(s in ("unavailable","rejected"))` → False → `outs[bid]=(None, why, None)` → `answered=None` → "no probe" → `_report_probe` counts `probes_not_made` and returns *without* calling `probe_result` (downsignal.py:392-395). So the slot is spent, no report. Matches the documented semantics. ✔)

- **Module missing at construction:** downsignal.py:161-162 — `self._fail(...)`; `self.hh=None`; `tick` returns early (downsignal.py:199-200); `snapshot` says `wired: False`. The miner unaffected. ✔ (Test: `test_a_missing_module_is_said_and_noticed`.)
- **`probe_due` raising:** `_call` catches (downsignal.py:304-314) → `_fail` → returns None → falsy → no probe. ✔
- **`ask`-thread raising a non-`AllBackendsFailed`, non-`Exception` (BaseException):** not caught (downsignal.py:357-358 catches `Exception`). A `KeyboardInterrupt` in a daemon thread — CPython delivers it to the main thread. `SystemExit` — likewise. ✔

---

## SECTION 2: LAW COMPLIANCE

- **L-x (NO SINGLE MODEL, ULTRON FIRST):** COMPLIANT. Every role ≥2 back-ends (providers.json:116-131; enforced at providers.py:158-160); vendors/models only in providers.json; the probe role now spans 3 Heimdall families (qwen, glm, muse) — the *checker's* second family is now probed, strengthening the "no single model" property of the *signal* (the signal's "down" verdict now requires *all* families silent, not just the two previously probed). The local model remains disabled (providers.json:13) — the "ULTRON FIRST" clause is satisfied structurally (it's first in the mine chain, providers.json:116) though not *callable* (no GPU0 lease; documented). PARTIAL only in the sense that the local back-end is `enabled: false` — but the design (§6, A5) and the integrator's B3 assign that to the integrator. I'll call it COMPLIANT with the documented caveat.
- **L-l (a model reply counts only whole; nothing repaired):** COMPLIANT. The probe's replies: `_any_text` (downsignal.py:87-90) — any non-empty text; strict. The broader validators (mine.py:447-499, flagcheck.py:176-203, ab.py:76-93) reject, never repair; the retry-with-reason (providers.py:987-988) is a *new attempt*, not a repair. ✔
- **L-j / L-m (fail closed; nothing measured is never a pass):** COMPLIANT. `answered=None` → "no probe" → `probes_not_made` (downsignal.py:392-395); an unanswered question is never agreement (flagcheck.py:17-18, 253-272); the calibration's unmeasured quotes (flagcheck.py:311-314); the adapter's expiry/`None`-publish refusals (ledger.py:336-342); the zoneless failure clock (downsignal.py:244-248). ✔
- **L-h / L-k (read as spoken; records never rewritten):** COMPLIANT (not touched by the diff; mine.py:397-400 `_untrusted` replaces `<` only, `>>` preserved; the ledger is append-only, ledger.py:34-66).
- **L-e (word timing at cut):** COMPLIANT (timing: "segment", duration_s null, duration_estimate_s flagged — mine.py:543-544).
- **L-u (hard exclusions):** COMPLIANT (mine.py:23-24, 547; ledger.py:347-348; the flagcheck *measures* and releases only imperative/ssb on a second-model "no" — ledger.py:212, 229-241 — accusation never, per P2).
- **L-v (speaker truth; re-uploads):** COMPLIANT (turn_change_inside measured-or-null, contract.py:129-135; duplicates, fetch.py:241-247).
- **L-q (moments first), L-r (no GPU), L-w, L-x:** COMPLIANT as above.
- **SPEND FREEZE:** COMPLIANT. The probe back-ends are Heimdall (not frozen, providers.json:5-6); the muse probe adds a *third* Heimdall call per probe — Heimdall mining continues, the freeze is untouched. The paid route (mine_paid) is the only freeze-lifted role, with its cap (providers.json:125-128; enforced providers.py:844-867, 899-904). ✔
- **Secrets:** COMPLIANT. Keys by name from the env file (providers.py:180-221); `redact` (providers.py:213-220, 241-247); the probe's evidence/why strings — could they leak a key? `why` comes from `BackendError.detail` (providers.py:50, 955-956: `r.detail = red(r.detail)`) — redacted. The `ask`'s why-strings are built from `e.tried`'s `w` (the BackendError's *string*, which is `f"{kind}: {detail}"[:500]`, providers.py:49) — the detail was redacted in `_try` (providers.py:953-955) *before* the exception's `str` is... wait: `_try` catches the BackendError, redacts `r.detail` (providers.py:954-955), then returns `("unavailable", f"{r.kind}: {r.detail[:160]}")` (providers.py:971) — the *redacted* detail. `AllBackendsFailed`'s message (providers.py:68) is built from those. So the `why` in `outs[bid]` (downsignal.py:355) is redacted. ✔ But: the *raw* exception's detail — if `ask`'s generic `except Exception` (downsignal.py:357-358) catches a non-BackendError (e.g. a `json.JSONDecodeError` with the key in it? No, keys aren't in JSON responses). ✔

**One PARTIAL:** the design says the probe is "a real model call on the family that failed **and one other**" (§14, ruling 87 amended). The code asks *every* family in the probe role (3), which *includes* the failed family and *at least one other* — a superset. COMPLIANT (superset satisfies "and one other"). But if only ONE family were configured in the probe role, the "and one other" clause would be violated — the config has 3, and there's no *code* enforcement of ≥2 families. The `validate_config` (providers.py:133-142) checks the probe role's back-ends are all of the signal's vendor, but not that they span ≥2 *families*. Minor gap: a config edit could silently drop to one family. The design's test list mentions "the live config: every enabled back-end of the vendor in any role names a family the probe asks" — that's the *coverage* direction, not the ≥2-families direction. P2.

---

## SECTION 3: SECURITY

- **SQL injection:** COMPLIANT. All SQL is parameterized (queue.py:108-110, 148-153, 173-174, 179-181, 186-187, 192-194, 200-202, 242-250, 254-255); the f-string SQL (queue.py:133-134, 165-166, 208-209) interpolates only *column names* from code-owned constants (`VIDEO_FIELDS`, `HOOK_COLUMNS`), validated against a whitelist (queue.py:161-163, 205-207). ✔
- **Auth bypasses:** N/A (no routes; a long-running process). The gateway: bearer key from the env, redirects refused (providers.py:322-327, 304-306) so the key never follows a redirect; the override's base-URL is constrained to this machine or the configured host (providers.py:168-177) — so the key can't be sent to an arbitrary host. ✔
- **Rate limiting:** the probe adds 3 calls/2min to Heimdall — trivial. The global in-flight cap (20) is enforced via `gsem` (providers.py:771); the probe's 3 threads + mining's 12 + glm's 8 + muse's 4... the *semaphores* are per back-end; the *global* 20 is shared. Mining (12 qwen) + flagcheck (8 glm / 4 muse) + 3 probe = could exceed 20? `gsem` (providers.py:945: `with self.sems[bid], self.gsem`) — the *acquisition* of gsem is what bounds it; a thread needing gsem waits. So the global 20 holds. ✔ But: the probe's 3 threads each hold their back-end's semaphore *and* wait on gsem — if gsem is exhausted by mining, a probe waits (its 60-s deadline starts... when? `t0` in `ask` (downsignal.py:347) is *before* `router.run`, so the throttle+semaphore+gsem waits count against the 60-s *wall* the ask-thread measures, but the *HTTP* deadline is 60 s from the request (providers.py:351: `timeout=timeout or self.timeout`). So a probe could take 60 (wait) + 60 (HTTP) = 120 s wall. The module's probe interval is 120 s. Tight but the `_probing` gate prevents overlap. ✔
- **Secrets in code:** none. All keys via `key_env`/`key_env_prefix` (providers.json:21, 31, 40, 50, 57, 65, 72, 81, 90, 99). ✔
- **Unvalidated input:** the overrides file (providers.py:535-562) — JSON, validated by `override_allowed` (scheme+host); a malformed file → no overrides (fail-closed, providers.py:556-557). The purge spec (purge.py:58-99) — strict. The ledger's lines (ledger.py:88-112) — strict. ✔
- **Prompt injection:** the transcripts are wrapped in `<sentences>` with `SECURITY:` notes (mine.py:104-110, 206-212, 281-287) and `_untrusted` (mine.py:397-400) prevents closing the block. The flagcheck's `<quote>` (flagcheck.py:145-152). ✔

---

## SECTION 4: FRONTEND QUALITY

N/A — this is a headless service. The "UI" is: STATE line 1, live.json, the coverage .md, the CLI. Judged as such:

- **STATE line 1:** the notice/switch machinery (spend.py:35-64, 199-216; downsignal.py:93-112, 410-455) is unusually rigorous — idempotent, lock-protected, newest-first, one physical line, "a switch later found false is marked so" (the head's why/`BY` fields). World-class for a text file.
- **live.json:** written via tmp+`os.replace` (stats.py:161-168) — atomic. ✔
- **CLI:** `tools/ingest_watch.py` — argparse, helpful docstrings, `--json` escapes. The `hooks` output (lines 173-182) is human-readable. ✔
- **Coverage .md:** (coverage.py:105-125) — a table with reasons; the "unmeasured → NOT a full measurement" caveat (line 115) is exactly right.
- No loading/error/empty states to speak of (no UI), but the *logs* carry the equivalents.

Score: excellent for what it is. 90/100.

---

## SECTION 5: BACKEND QUALITY

- **DB writes:** SQLite, WAL, `synchronous=FULL` (queue.py:86-87); one connection, one `RLock` (queue.py:84); `isolation_level=None` (autocommit) — each `x()` is one statement, atomic. No explicit rollback needed (no multi-statement transactions except... `add_video`'s INSERT+event: two statements, not wrapped — a crash between them loses the event, not the video. Acceptable: the event is observability, the video row is the state). The ledger: O_APPEND + flock + fsync (ledger.py:45-66) — exemplary. The torn-tail seal (ledger.py:69-85, 55-56) — the kind of thing most code skips.
- **External calls:** every `b.complete` is wrapped (providers.py:945-951); timeouts on every path (providers.json `timeout_s`; the SDK clients' `timeout`/`http_options`); retries bounded (`attempts`, `transport_retries`); the breaker + throttle + budget. The probe: `attempts:1, transport_retries:0, breaker:false` — deliberate.
- **Loop failure:** `_loop` (service.py:839-848) catches `Exception`, logs, continues; `BaseException` (a GPU0 stop) propagates — but then the *thread* dies silently? `_loop`'s `except Exception` won't catch it; the thread dies; the loop stops. Is that noticed? The service's `run` joins threads at stop (service.py:893-894) but doesn't monitor liveness. A dead `mine` loop = the service silently stops mining. Pre-existing, not in the diff. P2.
- **Memory:** `_SHA` cache bounded at 4096 (purge.py:206, 219-220); `self._conv` cleared at 5000 (service.py:705-706); `Health.events` deque(maxlen=50) (providers.py:581); `check_next` — grows unboundedly? Every moment_id ever checked gets an entry (service.py:513, 528) and is only *read* (service.py:655), never pruned. Over days: thousands of entries, each a small float — negligible, but it's a slow leak. P3. `self.inflight`/`hook_inflight`/`check_inflight` — discarded in `finally` (service.py:312-313, 470-472, 531-533). ✔
- **Logging:** `_log` (service.py:182-189) — ISO timestamp, printed + file. Errors carry tracebacks (service.py:255, 260, 303, 308, 468, 529, 543, 845). The signal's failures: `_fail` (downsignal.py:457-465) — one stable text per cause, no log churn. Excellent.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**Genuinely excellent (say so):**
- The ledger's durability story (append+fsync+seal+carry_forward+mined.at-order+bisected reads) is better than most production systems I've seen. ledger.py:34-149.
- The notice/switch discipline on STATE line 1 (spend.py:35-64) — idempotent, lock-ordered, "rewritten only when the text changes", "a MISSING file starts empty: a STATE file that exists and cannot be read raises" (spend.py:39-40). This is the kind of forensics Bloomberg's ops tooling aspires to.
- The calibration-reuse gate (service.py:576-620) — `prompts_sha`, single `asked_at`, exactly-the-role's-backends, the *why* logged on every refusal. F1's "no allowance ever comes from a stored reply" is *enforced*, not asserted.
- The purge's fail-closed invariant (purge.py:236-289, 413-423) with the "one copy per delivery, by sha256, unresolved keeps every copy" rule and the *cross-check* that both sides fail closed.

**Material gaps (only these):**

1. **No liveness monitoring of the loop threads** (service.py:839-848, 873-884). A `BaseException` (or an unexpected `Exception` subclass escaping... no, `Exception` is caught) — specifically a `BaseException` like a GPU0 stop, or a bug in the *finally* — kills a loop silently. The service keeps running, the tmux window looks alive, and mining/hooks/checks quietly stop. Every serious ops shop (and the design's own "fail closed" ethos) demands a watchdog: the health loop (already every 60 s) should assert each thread's `is_alive()` and event+log+restart it. This is the single highest-leverage missing piece. (P1)

2. **`check_next` grows forever** (service.py:513, 528, 639, 655). Every moment_id ever touched, forever. At ~1,000 moments/day × 30 days = 30k entries — still small, but it's an unbounded dict in a long-lived process, and the *prune* is trivial (drop entries whose moment's expiry has passed: the loop already computes `exp` at service.py:653-654). (P2)

3. **The probe role's ≥2-families invariant is unenforced** (providers.py:133-142). The amended ruling's "a probe is a real model call on the family that failed *and one other*" is satisfied by the *shipped config* (3 families) but not by the *code*. One `validate_config` clause — `len({cfg["backends"][b].get("family") for b in chain}) >= 2` — closes it. (P2)

4. **The module's `probe_result` learns nothing about *which* family answered** (downsignal.py:396). The watcher knows (it has `outs`), the module tracks `failing_families`, and the amended module clears them all on any answer. Passing the answering families (when the module's signature takes it — the `_takes` pattern is already there) would let the module keep a genuinely-failing family flagged. The diff's background acknowledges the module's semantics; the watcher could still *offer* the data. (P3 — the ruling doesn't require it.)

5. **No metrics/tracepoint for the probe's *wall* duration vs. its 120-s slot.** The evidence line has the why, but not "the probe took 47 s of the 120-s slot". If the probe ever approaches the slot, the *next* probe is skipped (correct) but nobody sees why the cadence degraded. One number in the evidence record. (P3)

Everything else — the spend meter, the paid route's cap, the A/B harness, the flagcheck's calibration — is already at or above the bar. Do not pad it.

---

## SECTION 7: SCORES

- Backend logic: 88/100 (the diff's invariants hold; the loop-liveness gap and the unbounded `check_next` are the deductions; the probe's semantics are careful but the muse-masking and the drill-suppression are real, if low, behavioral costs)
- Frontend/UI: 90/100 (N/A-ish; the STATE/live.json/CLI discipline is exemplary for the medium)
- Error handling: 90/100 (fail-closed everywhere; the *one* gap is the silent loop death)
- Security: 92/100 (parameterized SQL, redaction, redirect-refusal, override-allowlist; nothing hardcoded)
- Performance: 85/100 (the 5-s signal loop's flock+JSON-write per note; the full-table `usd_all_time_by_vendor` every 60 s; the probe's 3 threads — all fine at this scale, none would survive 10×)
- Law compliance: 93/100 (every law traced; the only PARTIAL is the unenforced ≥2-families probe invariant)
- World-class gap: 82/100 (the durability/notice/calibration work is world-class; the missing watchdog and the two unbounded/unenforced items are what a Bloomberg/Coinbase ops team would add in week one)
- **OVERALL: 88/100**

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | none — the diff is production-ready as shipped | — | —

P1 HIGH | Add a loop-thread watchdog: in `health_once`, assert `t.is_alive()` for every loop thread (keep the `Thread` objects; service.py:873-884), event+log+restart the dead one | service.py:839-848, 873-894 | a `BaseException` (GPU0 stop, service.py:305-310) or a bug in a `finally` kills one loop silently; the tmux process looks alive while mining/hooks/checks quietly stop — the exact "false outage" class of failure this ruling 87 amendment exists to kill

P2 MEDIUM | Enforce the amended ruling's "the failed family *and one other*": in `validate_config`, require the `down_signal.probe_role`'s chain to span ≥2 distinct `family` values | providers.py:133-142 | a config edit dropping to one family silently weakens the probe to a ping-of-one-family; the ruling's words are the contract

P2 MEDIUM | Prune `check_next` of expired moments (the loop already computes `exp` at service.py:653-654; drop entries with `exp <= now` and no pending retry) | service.py:513, 528, 639-655 | an unbounded dict in a long-lived process; trivial to fix, and the prune *is* the expiry rule the code already applies elsewhere

P2 MEDIUM | During a drill, still probe the *non-overridden* families (the `drills` check at downsignal.py:209-215 skips all) | downsignal.py:208-218 | a drill on one probe back-end currently blinds the signal to *all* families — including the one whose failure the drill is meant to exercise

P3 LOW | Pass the answering families to `probe_result` when the module's signature takes them (the `_takes` pattern, downsignal.py:71-76) | downsignal.py:396 | lets the amended module keep a genuinely-failing family flagged instead of clearing all `failing_families` on any answer

P3 LOW | Record the probe's wall duration in the evidence record (t0→done) | downsignal.py:347, 372-374 | makes a cadence degradation (probe nearing the 120-s slot) visible without a code read

P3 LOW | Note the probe's *wall* deadline vs. the HTTP deadline in the muse/glm probe notes (throttle wait + 60-s HTTP can reach 120 s) | providers.json:91, 101 | documents the tightness against the module's 120-s probe interval

---

## SECTION 9: THE ONE THING

Add the loop-thread watchdog to `health_once` — every other strength of this code (the ledger, the notices, the calibration gate) assumes the loops are running, and right now nothing notices when one quietly dies.

---

## SECTION 10: FINAL VERDICT

Ready for production. The ruling-87 amendment is implemented faithfully: the parallel probe asks every family, the latest-answer time is correct, the family notes are ordered and first-failure-kept, the older-module path is byte-identical, and no lock, thread, or slot survives its deadline. Before merge, add the loop watchdog (P1) — it is the one missing piece that would turn this from very good into genuinely operations-grade — and the two-line `validate_config` clause enforcing the ≥2-families probe invariant.