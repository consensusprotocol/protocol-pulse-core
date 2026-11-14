# heimdall_glm (z-ai/glm-5.3-flash, 555.4 s, $0.006, finish stop)

# FORENSIC CODE REVIEW — pp-ingest, ruling 87 change (downsignal + breaker-free probe)

Scope: the diff since ca17cb97 (downsignal.py, providers.py breaker/transport_retries, providers.json probe role + down_signal, spend.py switch/notice writers, service.py signal loop, stats.py, config.py). I reviewed the diff against the full working-tree files provided. Where the diff touches shared code, I cite the working-tree line numbers.

---

## SECTION 1: CORRECTNESS

### 1.1 The main flow, step by step

Flow: router thread finishes a Heimdall call → `_on_attempt` → `DownSignal.noted` (pending, under `self.lock`) → signal thread `tick()` every 5 s → `_flush()` → module `note()` → every 30 s `mode()` + `probe_due()` → probe thread → `_report_probe()` → `probe_result()` → `_seen()` reads switches → `spend.write_switch_head` → STATE line 1.

**Verified correct:**

- `noted()` filtering (downsignal.py:122–137): `kind in NO_CALL` skips `cache`/`disabled`; `rec.get("role") == self.probe_role` skips probe calls; `self.router.vendor(bid) != self.vendor` skips other vendors. Matches the stated contract. Note `vendor(bid)` (providers.py:716–717) returns `None` for an unknown bid, which correctly fails the `!=` comparison only when vendor is heimdall — actually `None != "heimdall"` is True → skipped. Correct.
- `_flush()` compression (downsignal.py:181–196): swaps `pending` under the lock, then writes at most one drill note, one answer note, one failure note. The failure note uses the *failure's* time (`p["fail"]`), the answer note the *answer's* time. Since `noted()` sets `pending["fail"] = None` on any later answer (downsignal.py:133), the invariant "the failure, if any, came after the answer" (downsignal.py:188) holds. Good.
- `_call()` wraps every module call in try/except and clears `busy_since` in `finally` (downsignal.py:169–179). A `HealthUnreadable` becomes `_fail`, never a crash. Good.
- Probe: `_start_probe` runs `router.run(..., use_cache=False)` in its own daemon thread (downsignal.py:198–213); `AllBackendsFailed` where nothing was *called* (`called` False) yields `answered=None` → `probes_not_made`, no `probe_result` (downsignal.py:222–226). Matches "a probe whose back-ends could not be called is no probe". Good.
- `_seen()` (downsignal.py:232–270): first sight (kv `None`/`""` or count > len) records the count without announcing history — matches "the history before this watcher was wired is not announced". Each unseen switch: `head()` → `write_switch_head` → evidence → event → kv increment. A STATE write failure returns *before* the kv increment (downsignal.py:257–264), so it is retried next tick. Correct.

**Defects found:**

**D1 (real, moderate): `_flush()` can note a stale answer *after* a fresher failure, resetting the builder's 15-minute clock.** Sequence: (a) Heimdall answers at T0 → `pending["answer"]=T0`; (b) the signal thread's 5 s tick is delayed (GIL, another loop, a slow `_seen`); (c) Heimdall fails at T1 → `pending["fail"]=T1`; (d) Heimdall answers again at T2 → `pending["answer"]=T2, pending["fail"]=None`; (e) tick finally runs: notes answer(T0), then failure(T1) — but the T2 answer was *compressed away* by (d) overwriting (a). The module's `note(False, now=T1)` clears `failing_since`... no wait, it *sets* it; then no note(True, T2) is ever written. The module's state now says failing since T1 with no later answer, when in fact T2 answered. The 15-minute clock then runs from T1 even though the gateway recovered at T2. Mitigation: the *next* successful call after T2 will note again (heartbeat permitting — but the module's HEARTBEAT_S=30 dedup means a note(True) within 30 s of the last written answer is dropped, and `_SEEN` is per-process, so the builder's process's answers don't suppress ours). So the error self-heals on the next answer more than 30 s after the last written one. Given the 15-minute window and 5 s flush, the practical impact is a clock that can be restarted from a stale failure by up to one missed answer. **Verdict: real but bounded; the module's 15-min rule and the next note(True) absorb it.** This is exactly question 1; the answer is "yes, it's a defect, but the 15-minute rule plus the next note(True) more than 30 s after the last written answer heals it; the window of error is one compressed answer, not a stuck state." One subtlety makes it slightly worse: the module's heartbeat (heimdall_health.py `note`, `_SEEN` check) drops an answer note if this *process* wrote one within 30 s — so if the watcher answers constantly, a note(True) at T2 may be dropped by the module *itself* even if we had sent it, and the module's `failing_since` would then persist. But the module's `mode()` (called every 30 s by `tick`) applies the 15-minute rule on the clock, and any subsequent note(True) clears `failing_since`. Net: self-healing, no permanent wedge. Downgrade to P2.

**D2 (real, low): `_flush()` notes the drill *before* the answer/failure, and the drill note's `now` is the flush time, not the drill time.** downsignal.py:184–186: `note(False, now=_utc(self.clock()), ..., drill=True)`. The drill count is a counter only; the module records `last_drill_utc` = flush time. Cosmetic (drills are never counted, heimdall_health.py `note` drill branch). No impact.

**D3 (real, low): `noted()`'s drill detection reads `overrides` without its lock, and `Overrides.get` may itself trigger a file read + `on_change` callback (providers.py:527–544) *from the router's thread*.** `Overrides.get` (providers.py:527) takes `self.lock`, but `on_change` (→ `Service._override_change` → `self.q.event` + `self.log`) runs *inside* that lock, on the calling (router) thread. Meanwhile `DownSignal._drill` (downsignal.py:139–140) calls `self.overrides.get(bid, "base_url")` from `noted()` — i.e., from the router's thread, inside `_on_attempt`, which is already inside the router's `_emit` (providers.py:763–768, which swallows exceptions). So: (a) the first call after an mtime change does the file read + event write synchronously in the mining thread — a bounded, one-time cost, acceptable; (b) `_emit` swallows any exception, so a crash in the override reload would silently skip the note — but `noted()` also has its own blanket try/except (downsignal.py:136–137). Double protection; the only loss is the note. Fine.

**D4 (real, low): `_seen()` reads the state file *without* the module's flock.** downsignal.py:235–236: `open(self.state_path)` + `json.load`. The module's `_save` (heimdall_health.py) writes to a tmp file and `os.replace` — atomic, so a reader either sees the old or the new file, never a torn read. **Correct** — the diff's claim "written atomically by the module" (change notes) is accurate. However: if the state file is *replaced* (deleted and recreated, e.g. the builder resets it), `switches` shrinks; `int(seen) > len(sw)` triggers the "wired" branch which resets the count — correct. If the file is replaced with *more* switches but the same count... impossible. If the builder's process writes a switch while we read: `os.replace` is atomic on POSIX, and the open fd keeps the old inode. Safe.

**D5 (real, low): `head()`'s `up` derivation.** downsignal.py:116: `self.up = next(m for m in self.hh.MODES if m != DOWN)`. If the module ever had 3 modes, `load_module` already rejects it (downsignal.py:57–58: `len(mod.MODES) != 2`). Safe.

**D6 (real, low): `head()`'s SWITCH_PATTERN vs the module's actual words.** spend.py:23: `SWITCH_PATTERN = r"\d\d:\d\d ET: (?:SWITCHED TO PLAN B|BACK TO [A-Z0-9_-]+-FIRST)"`. `head()` (downsignal.py:84) produces `"BACK TO " + up.upper().replace("_", "-")` → for `heimdall_first` → `"BACK TO HEIMDALL-FIRST"` → matches `[A-Z0-9_-]+-FIRST`. ✓. And the whole head is uppercased and whitespace-joined (downsignal.py:95), so `NOTICE_RE`'s `[A-Z0-9_-]+` prefixes match. But: the head *also* contains the why/who/plan-B tail, and `NOTICE_RE` is `^`-anchored without `$` — `re.match` (spend.py:46) matches a prefix, so a long head still matches. ✓. However `head()`'s why text is uppercased *user-ish* text (the module's why, e.g. "no Heimdall family answered inside its deadline for 15 minutes (since 2026-11-14T01:08:00Z)") — contains `(`, `)`, `:`, digits, `.` — all fine for a prefix match. ✓.

**D7 (real, moderate): `write_switch_head`'s "newest first" prepend can reorder relative to a *concurrent* notice writer's line, and the switch line's position is enforced by *reordering the whole block* on every notice write.** spend.py:52–53: `block = [h for h in block if SWITCH_RE.match(h)] + [h for h in block if not SWITCH_RE.match(h)]`. This runs in `_rewrite_top`, which is called by *every* notice writer (spend, outage, purge, signal). So any notice write re-sorts the block, putting switch lines first. Since there is at most one switch line (the callable-`line` path in `write_switch_head` merges all switch lines into one: spend.py:208, `lambda old: " ".join([head] + old)`), the reorder is: [the one switch line] + [other notices]. Correct and stable. But note the *outage* writer's `keep=lambda h: False` (spend.py:73) and the *spend* writer's `keep` (spend.py:179) — neither keeps switch lines (they're not `mine(h)`), so they land in `others` (spend.py:51) and survive. ✓. One more: `_rewrite_top`'s `mine` for the switch writer is `lambda h: bool(SWITCH_RE.match(h))` (spend.py:208) — and the *signal notice* writer's `mine` is `h.startswith(prefix)` where prefix is `"<LABEL> DOWN SIGNAL NOT READ"`. A switch line starts with `"\d\d:..."` so it never matches the signal prefix. ✓. And the signal notice's own line starts with the label, not a digit, so it never matches SWITCH_RE. ✓. Clean.

**D8 (real, low): `check_notice`'s "busy" branch.** downsignal.py:301–305: `busy = self.busy_since` read without a lock (it's a plain attribute written by the signal thread). Python attribute reads are atomic; worst case a slightly stale value. But: `busy_since` is set in `_call` *before* the module call and cleared in `finally` (downsignal.py:170, 176). If the module's flock is held by the builder's process for >30 min (SIGNAL_NOTICE_S), the health thread writes the notice. Then when `_call` returns, `_recovered` clears `self.error` but the *notice* is only removed when `check_notice` next runs with `why=None` (downsignal.py:314–316). ✓. However: if the signal thread is *itself* stuck in `_call` (lock held), the health thread's `check_notice` still runs (different thread) — good, that's the design. But `self.q.kv_get`/`kv_set` in `check_notice` (downsignal.py:308, 313, 316) take the queue's RLock — if the signal thread is stuck in the module's flock *while holding* the queue lock... it isn't; `_call` holds no queue lock. ✓.

**D9 (real, low): `_report_probe`'s `probe_out` race.** downsignal.py:215–217: `with self.lock: out, self.probe_out = self.probe_out, None`. The probe thread writes `self.probe_out` under the same lock (downsignal.py:210–211). ✓. But `tick`'s `wait=True` path (downsignal.py:164–165) joins the probe thread *then* calls `_report_probe` — and the *next* `tick` (5 s later, no wait) would also call `_report_probe`; if the probe finished between the join and the report... no, `_report_probe` runs after the join in the same tick. And `wait` is only used by tests. Fine.

**D10 (real, low): the probe's `AllBackendsFailed` classification.** downsignal.py:204–207: `called = any(s in ("unavailable", "rejected") for _, s, _ in e.tried)`. If both probe back-ends are *skipped* (e.g. frozen — impossible, heimdall isn't frozen; or disabled — possible if someone disables them; or budget — they have no `daily_budget_usd`), `called` is False → `answered=None` → "no probe back-end could be called" → `probes_not_made`, no `probe_result`. Correct: the module's `probe_due` will fire again in 2 min. But there's a subtle case: back-end 1 *skipped* (circuit... no, breaker:false skips the circuit check — providers.py:751), back-end 2 *unavailable* → `called=True` → `answered=False` → `probe_result(False)` → resets `probe_streak` to 0. Correct per the module ("a probe answer" = any family answering; a failed probe resets the streak — heimdall_health.py `probe_result`: `probe_streak = ... + 1 if answered else 0`). ✓.

**D11 (real, moderate): the probe role's `attempts: 1` + `transport_retries: 0` + breaker-free, but the *throttle* still applies.** providers.py:843: `th.wait()` runs before every attempt. If the *shared* Throttle of a probe back-end was hit by... no, the probe back-ends are dedicated (heimdall_qwen27b_probe ≠ heimdall_qwen27b), each with its own Throttle (providers.py:705, one per bid). But: the probe back-ends share the *key* (`key_env_prefix: HEIMDALL_API_KEY`) and the *gateway* with the miner. The Throttle is per-back-end-object, so a 429 on the miner's heimdall_qwen27b does not pause the probe's heimdall_qwen27b_probe. That's the design ("its own breaker and throttle so a probe never queues behind the mining", providers.json:83). ✓. But the *gateway* can still 429 the probe; then the probe's own Throttle pauses it (2 s→60 s), and with `attempts:1, transport_retries:0` the 429 is... let's trace: `_try` → `BackendError("http_429")` → `r.retryable` True but `transport_left=0` → `h.record(False, ...)` (a `_NoHealth`, no-op) → return `("unavailable", ...)` → `run` tries the next back-end. ✓. Then `AllBackendsFailed` with both unavailable → `called=True` → `probe_result(False)`. Correct.

**D12 (real, low): `_try`'s `h.record` for a breaker-free role.** providers.py:869, 888, 900: `h.record(...)` where `h` is `_NoHealth` — a no-op. But providers.py:836: `h = self.health[bid] if rc.get("breaker", True) is not False else _NoHealth`. Note `rc.get("breaker", True) is not False` — for a role *without* a "breaker" key, `rc.get` returns `True`, `True is not False` → True → the real Health. For `"breaker": false`, `False is not False` → False → `_NoHealth`. ✓. And `run`'s `breaker = rc.get("breaker", True) is not False` (providers.py:776) — same. ✓. But: `run`'s BaseException handler (providers.py:794–801) — for a breaker-free role it re-raises *without* calling `abandon()`. Since `_NoHealth.abandon` is a no-op anyway, and the real Health's `probing` flag was never set (allow() was never called — `available(bid, breaker=False)` returns `(True, "")` without touching the breaker, providers.py:751), this is correct: a breaker-free role took no probe slot. ✓. Matches the comment.

**D13 (real, low): `available(bid, breaker=False)` still checks the *budget* (providers.py:748–750).** The probe back-ends have no `daily_budget_usd`, so this is dead code for them, but if someone adds one, a probe would be skipped on budget → `AllBackendsFailed` with both skipped → `called=False` → no `probe_result` → the module's `probe_due` keeps firing. Correct, no wedge.

**D14 (real, low): `stats.live`'s `signal` parameter.** stats.py:138–139: `if signal is not None: out["down_signal"] = signal`. When the signal is unwired (`self.hsig is None`), live.json simply lacks the key — the docstring says "live.json says so at once" (downsignal.py:21–22) for the *unreadable* case, which is covered by `snapshot()`'s `not_read`. But when `hsig` is None (no down_signal in config), there's no indication at all. Acceptable: the config gates it.

**D15 (real, low): `Service.__init__`'s `signal_module`/`signal_state` are passed as `module_path=signal_module, state_path=signal_state` (service.py:97–99).** In `DownSignal.__init__` (downsignal.py:112): `self.module_path, self.state_path, ... = module_path or ds["module"], state_path, None, None`. If `signal_module=None` (the default), `module_path or ds["module"]` → ds["module"]. ✓. If `signal_state=None`, `self.state_path = state_path` → None, then in the try: `self.state_path = state_path or self.hh.STATE` (downsignal.py:115) → the module's default. ✓. But if the module *fails to load* (the except at downsignal.py:117–118), `self.state_path` stays whatever it was — for `signal_state=None` it's `None` (set at downsignal.py:112 before the try). Then `_seen()` (downsignal.py:235) does `open(self.state_path)` → `open(None)` → TypeError... but `_seen` is only called from `tick`, which returns early when `self.hh is None` (downsignal.py:146–147). ✓. And `snapshot()` (downsignal.py:320) reports `state_file: None` — honest. ✓.

**D16 (real, low): `noted()`'s `self.router.vendor(bid)` — a `KeyError` if `bid` is not in `self.backends`.** providers.py:716–717: `(self.cfg["backends"].get(bid) or {}).get("vendor")` — `.get`, no KeyError. ✓.

**D17 (real, low): the signal loop's jitter.** service.py:682–684: `self._loop("signal", self.hsig.tick, downsignal.SIGNAL_EVERY_S)` — `_loop`'s default `jitter=0.0` (service.py:642), so no jitter. Fine; 5 s.

**D18 (real, low): `tick`'s `next_mode` gating.** downsignal.py:150–151: `if now >= self.next_mode: self.next_mode = now + SIGNAL_MODE_S`. If `mode()` or `probe_due()` raises (they can't — `_call` catches), or if the *probe* takes >30 s, the next `mode()` is 30 s after the *start* of this block, not after its completion. Since `_start_probe` is non-blocking, the 30 s cadence holds. ✓. But: if `probe_due()` returns True and `_start_probe` is called, and the probe thread is still alive at the next 30 s boundary, the `probe_thread.is_alive()` check (downsignal.py:154) skips starting another. ✓. However, the *probe result* is only reported when the thread finishes and the next `tick` runs `_report_probe` (downsignal.py:166). If the probe takes 70 s (two 60 s deadlines... no, `attempts:1` per back-end, 2 back-ends, sequential in `run` → up to 120 s + throttle waits), the result lands at the next tick after completion. Meanwhile `probe_due` may fire again? No: `probe_thread.is_alive()` gates it (downsignal.py:154). But after the thread *finishes* and before `_report_probe` runs (same tick, line 166), the *next* tick's 30 s boundary could call `probe_due` → True (the module's `last_probe_utc` is only set by `probe_result`, which hasn't run yet) → `_start_probe` again → a second probe while the first's result is still pending. Window: one tick (5 s). Impact: an extra probe call, `probe_streak` incremented twice for what the module sees as two probes. Given the module's BACK_AFTER=3, this could make "3 answers in a row" come from 2 rounds — exactly question 2. **Answer to Q2: it's our side's race (a second `_start_probe` between the first's completion and its `_report_probe`), but the module's `probe_result` counts *calls*, not *rounds*, so 3 answers from 2 rounds is by the module's own semantics ("BACK_AFTER answers in a row", heimdall_health.py `probe_result`) — the ruling says "3 probe answers in a row", and the module counts answers, not rounds. So the behavior matches the module's contract; the 5 s window makes it rare.** Both sides share it: the module's `probe_due` doesn't claim the probe (no reservation), so *any* two callers (the builder's process and ours) can probe simultaneously — that's the module's design, documented in the diff's question. Not a defect of this change; it's the module's semantics. P3.

**D19 (real, low): `_seen`'s `int(seen)` can raise on a corrupt kv.** downsignal.py:246: `int(seen) > len(sw)` — `kv_get` returns the stored string; if someone puts "abc" in the kv, `int("abc")` → ValueError → propagates out of `_seen` → out of `tick` → caught by `_loop` (service.py:647–649) → logged, retried next 5 s. Every tick. Until fixed. Minor: a `try/except ValueError` would be kinder. P3.

**D20 (real, low): `head()`'s timezone.** downsignal.py:92: `t.astimezone(ET)`. If the module's `utc` field is a *naive* ISO string, `datetime.fromisoformat` gives a naive dt, and the code checks `t.tzinfo is not None` (downsignal.py:89) → falls to `seen_ts`. ✓. But the module's `_iso` (heimdall_health.py) writes `strftime("%Y-%m-%dT%H:%M:%SZ")` — the "Z" suffix; `head`'s `.replace("Z", "+00:00")` handles it. ✓.

**D21 (real, moderate): `write_switch_head`'s `notify_path` write happens *before* the STATE rewrite, and the STATE rewrite can fail.** spend.py:203–208: the NOTIFY log gets the switch, then `_rewrite_top` runs. If `_rewrite_top`'s `open(doc)` fails (STATE.md missing), `text = ""` (spend.py:42–43), then `lines = []`, `head = []`, the switch line is written to a *new* STATE.md. That's... actually reasonable (the file is recreated with just the notice). But it would clobber a STATE.md that was, say, momentarily unreadable due to a permission hiccup. Given `_rewrite_top`'s tmp+replace, the risk is the `open(doc)` for read failing — the file exists but is unreadable. Then the notice block is rebuilt from scratch, losing any non-notice content. In practice STATE.md is a notice-only file (the design: notices at top, the rest below). If the rest existed, it's preserved via `lines` — but only if the read succeeded. A read failure loses it. P3.

**D22 (real, low): `NOTICE_RE`'s switch pattern requires exactly two digits for the hour.** spend.py:23: `\d\d:\d\d ET:`. `head()`'s `strftime("%H:%M")` gives exactly that. ✓. But the *module's* `_prepend` (heimdall_health.py) writes `"%H:%M" ET: SWITCHED TO PLAN B (WHY) |` — if the builder's process ever writes to *our* STATE.md (it doesn't; A22 says state_md=None), it would use the module's `_prepend` which *merges into line 1* rather than our notice-block discipline. A22 (downsignal.py:17–19) documents exactly this: "The module is given no STATE path: its own head writer would leave a lock file beside STATE.md and bypass the notices' lock." ✓ — a correct and well-reasoned decision.

**D23 (real, low): `_rewrite_top`'s `keep` for the switch writer.** spend.py:208: `keep` defaults to `lambda h: False`, and `line` is the callable. So on a *second* switch, `line(old_switch_lines)` = `" ".join([head] + old)` — the old switch line(s) are preserved via the callable, and `kept` is empty. ✓. But: the callable receives `[h for h in head if mine(h)]` — the *old* switch lines. If there were somehow two switch lines (impossible via this writer, but possible if the file was hand-edited), they'd be joined. ✓.

**D24 (real, low): the outage writer's `keep=lambda h: False` (spend.py:73) — when the outage clears, the outage line is removed; the switch line (in `others`) survives. ✓. But the *spend* writer's `keep` (spend.py:179): `keep=(lambda h: False) if state == "tripped" else (lambda h: h.startswith(prefixes[0]))`. When the meter returns to "ok", `line=None`, `keep` keeps one "AT 90%" line. The switch line survives in `others`. ✓.

**D25 (real, low): `Service.close()` doesn't stop the signal thread.** service.py:143–150: shuts down `videos` and `executor`, calls `router.release()`, closes the store lock. The signal thread is a daemon (service.py:683) and `_loop` checks `self.stop` — but `close()` doesn't set `self.stop`. In `run()`, `self.stop.set()` happens in the signal handler, then threads are joined (service.py:695–696), *then* `close()`. So in the `run` path, the signal thread is joined (30 s timeout) before `close`. In the `once`/test path, `close()` is called without `stop.set()` — the signal thread was never started (it's only started in `run`). ✓.

**D26 (real, low): `mine_once`'s `free == 3` early-return skips `self._last_mining` update.** service.py:529–533: if no mining is due, it returns 0 *after* possibly releasing the router, and does NOT update `_last_mining`... wait, it does: line 530–532 checks the idle condition, then line 533 `self._last_mining = self.clock()` — but that's *outside* the `if free == 3` block? Let me re-read: lines 529–533:
```
if free == 3 and not self.q.due(Q.MINE_DUE, 1):
    if self.clock() - getattr(self, "_last_mining", 0.0) >= IDLE_RELEASE_S:
        self.router.release()
    return 0
self._last_mining = self.clock()
```
So when idle, `_last_mining` is NOT updated → the next tick (5 s later) checks again: `clock() - _last_mining` keeps growing → `release()` is called every 5 s after the idle threshold. `Router.release()` (providers.py:753–758) calls `release()` on every back-end; `OllamaLocalBackend.release` (providers.py:508–514) returns early if `self._busy` or if `self._llm is None` — so it's cheap. But it's called every 5 s forever while idle. Harmless (the local back-end is disabled in this session), but a `self._last_mining = self.clock()` inside the idle branch would be cleaner. This is pre-existing (not in the diff) — noting only because the diff's context touches this function. Actually, checking the diff: the diff does NOT touch `mine_once`. Out of scope; skip.

**D27 (real, moderate): the probe's `router.run` uses `self.probe_role`'s chain order, but `run`'s `order(role)` (providers.py:727–733) applies the *meter* reordering.** When the spend meter is not "ok", metered back-ends go last. BOTH probe back-ends have `"spend_meter": true` (providers.json:84, 92). So the reorder is a no-op (both move to the end of a two-element chain = same order). ✓. But: the *meter* itself is `CreditMeter` whose `state()` returns "unmeasured" before the first `measure()` — and `Service.__init__` creates the DownSignal *before* the meter (service.py:97–103), and `run()` calls `self.meter.measure()` (service.py:673) before starting threads. But `cmd_once` (tools/ingest_watch.py:52) also measures. However, if the service runs without `run()` (tests), the meter's state is "unmeasured" → `order("probe")` reorders → no-op. ✓.

**D28 (real, low): `_try`'s `rc = self.cfg["roles"][role]` (providers.py:835) — a second lookup; `run` already has `rc`.** Style; no bug.

**D29 (real, low): the probe's `max_tokens: 512` with `json_schema: false`-style... no, the probe back-ends have no `json_schema` key → `self.cfg.get("json_schema")` is falsy → no `response_format` (providers.py:350–352). And `run` passes `schema=None` (downsignal.py:202). `_key` (providers.py:808–810) does `json.dumps(schema, sort_keys=True)` → `json.dumps(None)` → "null". ✓. And `_cached` is skipped (`use_cache=False`). ✓.

**D30 (real, low): `_any_text` (downsignal.py:70–73) raises `providers.Invalid` for empty content — but `run`'s `_try` catches it via `validate(r.content)` (providers.py:880–886) → "invalid" → retried? No: `attempts:1`, so after 1 invalid, `_try` returns `("rejected", "invalid after 1 attempts: ...")` → next back-end. ✓. But note: an *empty* reply from the gateway (e.g. `content: ""`) would already be caught by `OpenAICompatBackend.complete`'s `if not isinstance(content, str) or not content.strip()` → `BackendError("empty")` (providers.py:370–372) → "unavailable". So `_any_text`'s Invalid path is nearly dead code (only for whitespace-only... which `complete` also catches). Harmless.

**D31 (real, low): the probe's `tag="probe87"` (downsignal.py:202) — a string, not a dict.** `Queue.call` (queue.py:223–234) does `tag.get(...)` only `if isinstance(tag, dict)` (queue.py:230–231). ✓.

**D32 (real, low): `noted()`'s `rec.get("role")` — for a *cache* hit, `_emit` (providers.py:823–825) includes `"role": role`; for a real call, `rec` (providers.py:844–845) includes `"role": role`. The probe role's *cache* emissions: `use_cache=False` in the probe's `run` call, so no cache emissions for the probe. But the *miner's* cache hits (role "mine") ARE noted? `noted` checks `kind in NO_CALL` — "cache" is in NO_CALL → skipped. ✓. And "disabled" (the `BackendError("disabled")` path, providers.py:243, 484–487) → `_emit` with `kind="disabled"`? Let's check: `_try`'s error path (providers.py:860–861) emits `kind=r.kind` — for a `disabled` BackendError, kind="disabled" → in NO_CALL → skipped. ✓. But wait: `available()` (providers.py:746–747) returns `(False, "disabled")` for a disabled back-end *before* `_try` — that's a `tried.append((bid, "skipped", why))`, no `_emit` at all. The "disabled" *kind* only comes from `_try`'s `b.complete()` raising `BackendError("disabled", ...)` (providers.py:243, 484) — which happens when the key is missing or the lease is lost *between* `available()` and `_try`. Then `_emit` gives kind="disabled" → NO_CALL → skipped. Is that right? A "no key" case: no call was made → correct. A "GPU0 lease not held" case: no call → correct. ✓.

**D33 (real, moderate): the `noted()` → `q.call(rec)` ordering in `_on_attempt` (service.py:163–171).** `noted` is called *first*, then `q.call`. If `q.call` raises (DB locked, disk full), the note was already made but the call record lost. `_on_attempt` is called from `_emit` which swallows exceptions (providers.py:763–768). So a DB failure loses the call record but the signal note survives. Acceptable; the signal is more critical than the log. But: `noted` itself is wrapped in its own try/except (downsignal.py:136–137), so a note failure doesn't prevent `q.call`. ✓.

**D34 (real, low): `DownSignal.__init__`'s `paths` parameter.** service.py:98 passes `self.p` (the full paths dict). downsignal.py:104: `self.evidence, self.notify = paths["signal"], paths["notify"]`. `paths["signal"]` is new (config.py:100). If an old caller passes a paths dict without "signal" → KeyError. Only `Service` calls it. ✓.

**D35 (real, low): the evidence file's directory.** `paths["signal"]` = `<ingest>/down_signal.jsonl`; `Service.__init__` creates the `ingest` dir (service.py:77–78). `_evidence` (downsignal.py:289–294) opens it for append — the dir exists. ✓.

**D36 (real, low): `check_notice`'s `since` when `self.error` is truthy but `error_since` is None.** downsignal.py:303: `why, since = self.error, self.error_since`. `_fail` (downsignal.py:278) sets `self.error_since = self.error_since or self.clock()` — never None after the first `_fail`. ✓. But: `elif busy is not None and now - busy >= SIGNAL_NOTICE_S` (downsignal.py:304) — `busy_since` is set in `_call` *before* the try (downsignal.py:170) and cleared in `finally` (downsignal.py:176). If the module call *hangs* (the flock is held), `busy_since` stays set → after 30 min, the notice. ✓. But: `_call` is only called from the signal thread; if the signal *thread* dies (an uncaught exception in `tick` — `_loop` catches, service.py:647–649, so it doesn't die), `busy_since` could stay set forever → a permanent notice. `_loop` catches `Exception`, not `BaseException` — a `KeyboardInterrupt` in the signal thread would... in a thread, KeyboardInterrupt goes to the main thread. SystemExit in a daemon thread: `_loop`'s while loop would exit, the thread dies, `busy_since` stays. Then `check_notice` writes the notice 30 min later and it's never removed. Edge; P3.

**D37 (real, low): `snapshot()`'s `mode: None if self.error else self.mode` (downsignal.py:321).** If the module failed to load, `self.error` is set → mode None. ✓. If the module loads but the *state* is unreadable, `_fail` sets error → mode None (the last known mode is hidden). Matches "never read as up or down". ✓. But: `self.mode` is updated by `_flush`/`_report_probe`/`tick`'s `mode()` — if the *last* `_call` succeeded but an *earlier* one failed and `error` was never cleared... `_recovered` (downsignal.py:280–287) clears it on the next successful `_call`. ✓.

**D38 (real, low): the `wired` log at start (service.py:664–668).** `sg["wired"]` is `self.hh is not None` — if the module failed to load, it prints `NOT READ: <the error>`. ✓.

**D39 (real, low): `providers.json`'s `down_signal.module` is an absolute path to another worktree** (providers.json:98). If the worktree is moved/removed, `load_module` fails → `_fail` → the signal is "not read" → the notice after 30 min. The miner is unaffected (the design). ✓. But: the *test* `test_the_live_config_wires_the_signal_to_heimdall_only` presumably loads it — if the worktree is absent in CI, the test fails. Not verifiable from the code; noted.

**D40 (real, low): `validate_config`'s down_signal check (providers.py:123–132) — `cfg["backends"][b]["vendor"]`** — `b` is guaranteed in `cfg["backends"]` by the earlier role-chain check (providers.py:115–117). ✓.

**D41 (real, low): the probe role's `attempts: 1` but `_try`'s `while attempt < attempts` (providers.py:842) — `attempt` increments only on a *successful* complete (providers.py:875).** With `attempts:1`: one `complete` call; if it returns a reply that fails `validate`, `attempt` becomes 1, loop exits, return "rejected". If it raises a retryable BackendError with `transport_left=0`, return "unavailable". ✓. Exactly one gateway call per back-end. Matches "one call per back-end" (providers.json:111).

**D42 (real, low): the probe's throttle.** `th.wait()` (providers.py:843) — the probe back-ends' Throttle starts at `first_s: 2.0` (providers.json:121). First call: `until=0.0` → no wait. ✓.

**D43 (real, moderate): the probe's `spend_meter: true` (providers.json:84, 92) means probe costs are added to the *meter's* `local_since` (providers.py:858–859, 873–874).** The meter's `state()` (spend.py:126–130) adds `local_since` to `measured_spend`. So probe spend counts toward the 90% tripwire. Correct — "Plan B's spend counts on the same ledger and the same cap" (the change's ruling quote). ✓. But: the *metered* reorder in `order(role)` (providers.py:731–732) — when the meter trips, the *probe* back-ends (both metered) would go last in the *probe* role's chain — a no-op (both). But the *mine* role's chain: heimdall_qwen27b (metered) + local_gemma (not metered) → local first. Under the freeze, local_gemma is disabled → `effective("mine")` = [heimdall_qwen27b] only. The reorder puts the (only) metered back-end... there are no others, so the chain is unchanged. ✓. Matches "when there is none, Heimdall keeps mining" (the design, §6).

**D44 (real, low): `stats.live`'s `signal` — `write_live` (stats.py:151–158) passes `**kw` → `live(q, **kw)`.** service.py:557–558 passes `signal=...`. ✓.

**D45 (real, low): the diff's `service.py` hunk adds `signal_module=None, signal_state=None` to `Service.__init__` (service.py:74–75) — but `cmd_run` (tools/ingest_watch.py:44–46) calls `Service()` with no args.** So the live service uses the config's module path. ✓.

**D46 (real, low): `_seen`'s evidence record for a switch includes `head=h` which may be None** (downsignal.py:266) — for a switch whose `to` is neither DOWN nor up (impossible given the module's 2 modes, but the code guards). Then the log says "an unknown switch: ..." (downsignal.py:269). ✓.

**D47 (real, low): `head()`'s `rec.get("by")` — the module's `_switch` (heimdall_health.py) writes `"by": who`.** For the builder's switches, `who` is whatever they passed. `head` renders `BY <who>` uppercased. ✓.

**D48 (real, low): the `NOTICE_RE` change (spend.py:25–26) — the signal notice's prefix is `[A-Z0-9_-]+ DOWN SIGNAL NOT READ`.** `write_signal_notice`'s prefix (spend.py:217) is `f"{label} {SIGNAL_SUFFIX}"` where label is `self.meter.label` → "HEIMDALL" (from providers.json spend_meter.label). But `DownSignal.label` is `ds["label"]` → also "HEIMDALL" (providers.json:97). Two *different* sources for the same label! If they diverge, the notice written by `check_notice` (label=ds["label"]) would be matched by `NOTICE_RE` (any `[A-Z0-9_-]+`), and `write_signal_notice`'s own `mine` (spend.py:221, `h.startswith(prefix)`) uses the *same* label passed in — consistent within one call. But across restarts or if someone edits one label: the notice's `mine` wouldn't match the old line → the old line lands in `others` → duplicated notices. Currently they're both "HEIMDALL" (providers.json:97 vs :114). Fragile but correct today. P3.

**D49 (real, low): `write_signal_notice`'s `label` default is "GATEWAY" (spend.py:212) but `check_notice` passes `label=self.label` (downsignal.py:310, 315).** ✓.

**D50 (real, low): the outage notice's `keep=lambda h: False` (spend.py:73) — when the outage clears, `line=None`, `keep` discards the outage line. But the *switch* line: `mine(h)` for the outage writer is `h.startswith(OUTAGE_PREFIX)` — the switch line doesn't match → `others` → preserved. ✓.

### 1.2 Race conditions

- **`pending` under `self.lock`** (downsignal.py:129–135, 182–183): correct. The only shared mutable state touched by router threads is `pending` (under the lock) and, via `_drill`, the `Overrides` object (which has its own lock). ✓.
- **`self.mode`, `self.n`, `self.last_probe`, `self.head_error`, `self.error`, `self.error_since`, `self.busy_since`**: written by the signal thread, read by the health thread (`check_notice`, `snapshot`) without a lock. Python's GIL makes each attribute read/write atomic; the worst case is a torn *pair* (e.g. `error` updated but `error_since` not yet) — but `_fail` sets both in one statement (downsignal.py:278: `self.error, self.error_since = why, self.error_since or self.clock()`), which is a tuple assignment, atomic in CPython. ✓. `snapshot`'s `dict(self.n)` (downsignal.py:324) — `self.n` is mutated by the signal thread; `dict()` on a dict being mutated is safe in CPython (it may miss a concurrent increment, but won't crash). ✓.
- **`probe_out`**: written by the probe thread under `self.lock` (downsignal.py:210–211), read+cleared by the signal thread under the same lock (downsignal.py:216–217). ✓.
- **`probe_thread`**: written by the signal thread (downsignal.py:212–213), read by the signal thread (downsignal.py:154, 164). Single-threaded. ✓.
- **The kv `signal_switches_seen`**: read+written by the signal thread only (`_seen` is called from `tick`). But `snapshot` reads it (downsignal.py:324) — a concurrent read of a value being written; `kv_get` takes the queue's lock. ✓.

### 1.3 N+1 / performance

- `_seen` reads the whole state file every 5 s (downsignal.py:235–236). The state file is small (a few switches). ✓.
- `_flush` → `note` → the module's `_load`+`_save` (a full JSON read+write under the flock) — at most 3 notes per 5 s tick. ✓.
- `check_notice`'s `kv_get`/`kv_set` every 60 s (the health loop). ✓.
- No N+1.

### 1.4 Edge cases

- **Empty/missing state file**: `_seen` catches `FileNotFoundError` → return (downsignal.py:240–241). ✓. The module's `_load` (heimdall_health.py) returns a default for a missing file. ✓.
- **Corrupt state file**: the module raises `HealthUnreadable` → `_call` → `_fail`. `_seen`'s own read: `json.JSONDecodeError` (a ValueError) → caught (downsignal.py:242–244) → `_fail`. ✓.
- **Module missing**: `_fail` at construction; `tick` returns early; `check_notice` writes the notice after 30 min. ✓.
- **Both probe back-ends skipped**: `answered=None` → no `probe_result` → the module's `probe_due` fires again. ✓.
- **The builder's process holds the flock**: `_call` blocks (the module's `_Locked.__enter__` does a *blocking* `flock(LOCK_EX)`, heimdall_health.py). The signal thread blocks; the miner's threads don't (they only touch `pending`). After 30 min, the health thread's notice. ✓ — this is exactly the design (A24). But: the *signal thread* is blocked, so `_flush` also blocks → pending outcomes accumulate (bounded: `pending` is 3 fields, overwritten). ✓.
- **`overrides.json` unreadable**: `Overrides.get` → `m = None` → `new = {}` → no drill. ✓.

### 1.5 Silent failures

- `_evidence` swallows OSError (downsignal.py:293–294) — documented ("evidence, never a gate"). ✓.
- `_emit` swallows exceptions (providers.py:767–768) — pre-existing.
- `noted`'s blanket except (downsignal.py:136–137) — documented. ✓.
- `_flush`'s `unnoted` counter (downsignal.py:193) — a note that failed is counted, not retried. The *next* outcome will note again. But if the module is persistently failing, `unnoted` grows and the state goes stale — but `_fail` was called, so `error` is set, and the notice fires. ✓.

---

## SECTION 2: LAW COMPLIANCE

- **L-x (NO SINGLE MODEL, ULTRON FIRST)**: **COMPLIANT.** The probe role has 2 back-ends (providers.json:109); `load_config` enforces ≥2 (providers.py:140–143). No vendor/model name in code: `SWITCH_PATTERN` (spend.py:23) uses `[A-Z0-9_-]+` generically; the label comes from config (spend.py:217, downsignal.py:102). The module *path* is in providers.json (providers.json:98), not code. `downsignal.py` references `providers.Invalid`/`AllBackendsFailed` (interface, not vendors). `MINER_PLAN_B` (downsignal.py:43–44) mentions "Heimdall" — a *label*, and the design says "no vendor / model name outside the provider config"; "Heimdall" here is the signal's label, which the config also carries. Borderline but defensible: the string "Heimdall" appears in downsignal.py:43, 274, 282 (log/error text) and service.py:666. Strictly, the *label* is in the config; the code hardcodes the word in prose. I'd call this PARTIAL→COMPLIANT (the design's own test `test_no_vendor_name_in_the_code_outside_the_provider_config` presumably passes, so the builders consider prose exempt). Note: `spend.py:22`'s comment says "the label from providers.json down_signal" — the *code* uses the label, the *comment* names it. Fine.
- **L-l (a reply counts only whole; nothing repaired)**: **COMPLIANT.** The probe's `_any_text` (downsignal.py:70–73) raises `Invalid` on empty; no repair. `run`'s validator path unchanged.
- **L-j / L-m (fail closed; nothing measured is never a pass)**: **COMPLIANT.** Unreadable state → never guessed (downsignal.py:20–23, 272–278); `snapshot`'s `mode: None` (downsignal.py:321); the notice after 30 min (downsignal.py:298–316). A probe nobody could answer is `probes_not_made`, not a failure (downsignal.py:223–226). An unanswered question... (that's flagcheck, not this diff). The signal notice's "never 'up' or 'down' by guess" (spend.py:213–215). ✓.
- **L-h / L-k / L-e / L-q / L-u / L-v / L-r**: untouched by this diff; the surrounding code (mine.py, contract.py) is unchanged. Not re-verified.
- **Secrets (keys read by name from the env file; never printed, logged or written)**: **COMPLIANT.** The probe back-ends use `key_env_prefix: HEIMDALL_API_KEY` (providers.json:81, 90) — read via `Keyring` (providers.py:213–215). `Keyring.__repr__` (providers.py:192–193) shows only a count. `redact` (providers.py:223–229) is applied to error detail/raw (providers.py:854–856). The probe's `tag="probe87"` (downsignal.py:202) — no key. The evidence/notify records (downsignal.py:222, 291) — no key. ✓. One nit: `_call`'s error message (downsignal.py:174) includes `str(e)[:200]` from the module — the module's errors are file/JSON errors, no keys. ✓.
- **SPEND FREEZE**: **COMPLIANT.** The probe back-ends are vendor "heimdall" (providers.json:80, 89) — not in `spend_freeze.vendors` (providers.json:6). `available` (providers.py:744–745) enforces the freeze; `run`'s `order(role)` → the probe chain is heimdall-only. The probe adds spend to the metered account (D43) — the freeze caps *frontier* vendors, not Heimdall. ✓. "If both are down the videos queue" — unchanged; the signal doesn't alter what the miner calls (service.py:18–21, downsignal.py:22–23). ✓.
- **Integrator B1–B4**: B1 (notify, never halt) — the signal notice is a NOTIFY (spend.py:213–215); the miner never depends on the signal. ✓. B2–B4 untouched.

---

## SECTION 3: SECURITY

- **SQL injection**: no new SQL. The diff's only SQL-adjacent code is `kv_get`/`kv_set` (parameterized, queue.py:109–114) and `q.event` (queue.py:104–107, parameterized). ✓.
- **Auth bypass**: N/A (no routes).
- **Rate limiting**: the probe adds at most 1 call per back-end per ~2 min (the module's PROBE_EVERY_S=120, heimdall_health.py) — but *our* gating is `SIGNAL_MODE_S=30` + `probe_due()`. Worst case: our tick every 5 s, `probe_due` true, the probe completes in <5 s, `_report_probe` at the next tick, `probe_result` sets `last_probe_utc` → the next `probe_due` is 120 s later. But the D18 race: between the probe thread finishing and `_report_probe`, the 30 s boundary could re-`probe_due` → a second probe. Bounded: ~1 extra probe per 30 s. With `max_inflight:1` per probe back-end and the 60 s timeout, the gateway sees ≤2 concurrent probe calls. Negligible. ✓.
- **Secrets in code**: none. The module path (providers.json:98) is a filesystem path, not a secret. ✓.
- **Unvalidated input**: `head()`'s `rec.get("why")`/`rec.get("by")` come from the shared state file (the builder's process writes them) — they're uppercased and whitespace-joined (downsignal.py:95) before insertion into STATE.md. No shell, no HTML. `_seen`'s `json.load` of the state file: a hostile state file could be huge (memory) — the builder's own file, trusted. `int(seen)` (downsignal.py:246) — from our own kv. ✓. `spend._rewrite_top`'s `line` callable — internal. ✓. The `Overrides` file (providers.py:527–544) — `override_allowed` (providers.py:150–159) validates the scheme/hostname. ✓ (pre-existing, but the diff's `_drill` reads it).

---

## SECTION 4: FRONTEND QUALITY

N/A — this is a headless service. The "UI" is STATE.md, live.json, and the evidence file.

- **STATE line 1**: the switch head is one physical line, newest first, kept first (spend.py:52–53, 195–209). Matches the ruling ("IN CAPITALS with the time, at the start of the caller's STATE line 1 (one physical line)"). ✓. The `head()` output (downsignal.py:93–95) is human-readable: `01:08 ET: SWITCHED TO PLAN B (NO HEIMDALL FAMILY ANSWERED INSIDE ITS DEADLINE FOR 15 MINUTES (SINCE 2026-11-14T00:53:00Z); BY PP-SELECTID; THE MINER'S PLAN B: QUEUE AND WAIT (SPEND FREEZE)) |`. Dense but parseable. The nested parentheses are slightly awkward. P3.
- **live.json `down_signal`** (stats.py:138–139): `snapshot()` (downsignal.py:318–325) exposes wired/module/state_file/evidence/vendor/mode/not_read/not_read_since/call_waiting_s/last_probe/counts/switches_seen/miner_plan_b. Good observability. ✓.
- **Evidence file** (downsignal.jsonl): one JSON line per note/probe/switch/wired/unreadable/readable. ✓.
- **Loading/error/empty states**: the evidence file's "wired" record (downsignal.py:250–251) marks the start; "unreadable"/"readable" mark failures. ✓.

---

## SECTION 5: BACKEND QUALITY

- **try/except**: `_call` (downsignal.py:169–179) catches everything; `noted` (downsignal.py:122–137) catches everything; `_evidence` catches OSError; `_loop` (service.py:642–651) catches Exception. The signal thread cannot crash the service. ✓.
- **Timeouts**: the probe back-ends: `timeout_s: 60` (providers.json:84, 92) → `OpenAICompatBackend.timeout` (providers.py:211) → the urllib socket timeout (providers.py:333). ✓. The module's flock: *blocking* — no timeout. Mitigated by the health thread's notice (D36). A `flock` with `LOCK_NB` + retry would be better but the design (A24) accepts it. P2.
- **Retry**: the probe: `attempts:1, transport_retries:0` — deliberately none (providers.json:111). The *note* path: no retry; `unnoted` counted; the next outcome notes again. If the module is down, `_fail` → the notice. ✓.
- **Graceful degradation**: the miner never waits on the signal (A24, downsignal.py:10–12, 22–23). ✓.
- **Cron/loop failure**: `_loop` catches and logs (service.py:647–649). ✓.
- **Memory leaks**: `pending` is 3 fields, swapped. `self.n` is a fixed dict. `probe_out` is one tuple. The evidence file grows unboundedly (one line per note — at 1 note/5 s = 17k lines/day ≈ 2 MB/day). No rotation. P3 (the design's other logs — replies_log — are daily-rotated; the evidence file is not). Actually: notes are only written when there's an outcome; a healthy Heimdall writes at most 1 note/30 s (the module's heartbeat is *our* compression: we note at most 1 answer+1 failure per 5 s tick, and the module's own HEARTBEAT_S=30 dedups *its* writes... no, the module's heartbeat dedups *note* calls, which we make at most 2×/5 s. So the evidence file gets our `_evidence` calls, which are: probes, switches, unreadable/readable — *not* every note. `_flush`'s notes go to the module (state file), not our evidence. So the evidence file only grows on probes (≤1/2 min) and switches. ~720 lines/day. Negligible. ✓.
- **Logging**: `_fail` (downsignal.py:272–278) logs the why; `_recovered` (downsignal.py:280–287) logs the recovery; the probe logs its outcome (downsignal.py:225, 269); the switch logs the head (downsignal.py:269). Enough context. ✓. One gap: `_flush`'s `unnoted` (downsignal.py:193) is counted but never logged — a silent note failure. P3.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**Already excellent:**
- The one-thread-owns-the-module design (A24) with a lock-free `noted()` is exactly right: the miner's latency is never coupled to a shared-file flock. Most implementations would have put the note inline.
- The drill/override distinction (A26, downsignal.py:139–140) — recording drills without counting them — is the kind of operational foresight (outage drills polluting the production signal) that separates good from great.
- `write_switch_head`'s "one physical line, newest first, always first" (spend.py:195–209) with the reorder discipline in `_rewrite_top` (spend.py:52–53) is a clean solution to a genuinely annoying concurrent-notice problem.
- The breaker-free probe role (`_NoHealth`, providers.py:624–633) — "the probe is the breaker's evidence, not its patient" — is a precise, well-argued design.

**Material gaps:**

1. **The module's flock is acquired blocking, with no timeout** (heimdall_health.py `_Locked.__enter__`; our `_call`, downsignal.py:169–179). If the builder's process wedges while holding the lock, our signal thread wedges too. The mitigation (the health thread's notice after 30 min, downsignal.py:304–305) *detects* it but does not *recover* — the signal thread stays wedged, so notes stop, probes stop, and the notice stays. A `LOCK_NB` + retry-with-backoff (or a timeout via signal.alarm, or a dedicated lock-acquire thread) would let the signal thread report "not read" *and keep trying*. Bloomberg/Coinbase would not accept a monitoring component that can deadlock.

2. **No persistence of `pending` across a crash.** If the process dies between `noted()` and `_flush()`, the outcome is lost. For a 15-minute-rule signal, losing 5 s of outcomes is immaterial — but the *last* outcome before a crash could be the one that would have tripped the rule. Given the module's own 15-min window and the builder's process noting independently, this is acceptable. Not a gap worth fixing.

3. **The evidence file has no rotation** — but the volume is negligible (D5/§5). Not a gap.

4. **`_seen`'s trust in the state file's `switches` list**: if the builder's module ever *truncates* the list (it only appends), our kv count would exceed `len(sw)` → the "wired" branch → the count resets, history re-announced. Correct behavior. If the builder *reorders* the list, we'd re-announce. Their module appends. ✓.

5. **The probe's cost is invisible in the A/B** — it's a different role, so `ab.summarize` (ab.py:339) filters `role == "mine"`. Probe spend appears only in the meter and `calls`. Fine.

6. **No metric for "signal latency"** — how long from a Heimdall failure to the module's mode flip. `counts` has `failures_noted` but not the distribution. A professional observability layer would want it. P3.

---

## SECTION 7: SCORES

- Backend logic: 88/100 (D1, D18, the blocking flock; everything else correct and well-argued)
- Frontend/UI: 85/100 (STATE/live/evidence are clear; nested-parenthesis heads, no signal-latency metric)
- Error handling: 90/100 (every path caught; the only gap is the wedged-signal-thread case, which is *detected* but not *recovered*)
- Security: 92/100 (nothing exposed; the state file is trusted — appropriately)
- Performance: 93/100 (O(1) noted, 5 s tick, negligible I/O; the 5 s `_seen` read is the only recurring cost)
- Law compliance: 95/100 (all laws honored; "Heimdall" appears in prose in downsignal.py, defensible)
- World-class gap: 82/100 (the blocking flock wedge is the one thing Bloomberg would fix)
- **OVERALL: 88/100**

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | none — the change is production-ready as-is | — | —

P1 HIGH | Give the module's flock a non-blocking acquire with retry (or a watchdog) so a wedged builder's process degrades our signal thread to "not read" *without* wedging it | downsignal.py:169–179 (via heimdall_health._Locked) | today a held flock wedges the signal thread permanently: notes, probes and switch-announcements all stop; only the 30-min notice fires, and it never clears

P2 MEDIUM | Note the *latest* answer even when a failure was compressed: keep the last two answers in `pending` (or note the answer's time when it is newer than the failure) | downsignal.py:129–135, 181–196 | D1: a compressed answer lets the module's 15-min clock run from a stale failure; self-heals but can delay the "back to heimdall_first" by one note cycle

P2 MEDIUM | Guard `int(seen)` in `_seen` against a corrupt kv value | downsignal.py:246 | a non-numeric `signal_switches_seen` makes every tick log a loop error forever

P2 MEDIUM | Log `_flush`'s `unnoted` failures (the count exists, the log line doesn't) | downsignal.py:193 | a persistently failing note is invisible until the 30-min notice, losing the diagnostic

P3 LOW | Flatten `head()`'s nested parentheses (the why already contains them) | downsignal.py:93–95 | readability of STATE line 1

P3 LOW | Derive the signal-notice label from one source (today `DownSignal.label` = down_signal.label, and the *meter's* label = spend_meter.label; both "HEIMDALL" by coincidence) | downsignal.py:102, spend.py:217, providers.json:97/114 | a divergence silently duplicates notice lines (D48)

P3 LOW | Add a signal-latency note (failure→mode-flip) to `counts` | downsignal.py:110–111 | the ruling's 15-min rule is currently unmeasurable

P3 LOW | Consider a second `_start_probe` guard: skip if `probe_out` is still pending | downsignal.py:154, 215–217 | D18: a 5 s window can double-probe; the module counts answers, so it's semantically harmless

---

## SECTION 9: THE ONE THING

Make the signal thread *unwedgeable*: acquire the builder's flock non-blocking with a bounded retry so that a stuck shared lock costs you the signal's *freshness*, never the signal's *liveness* — everything else in this change is already built to survive.

---

## SECTION 10: FINAL VERDICT

Ready for production. The design (one-writer thread, O(1) noted, breaker-free probe, drill discipline, fail-closed unreadable) is genuinely strong and the failure modes are thought through. Fix the blocking flock (P1) and the compressed-answer note (P2) before the next Heimdall incident — both are small, and both are exactly what the signal exists for.