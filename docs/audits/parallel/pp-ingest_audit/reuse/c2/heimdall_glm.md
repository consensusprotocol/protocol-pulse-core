# heimdall_glm (z-ai/glm-5.3-flash, 245.2 s, $0.005, finish stop)

# FORENSIC CODE REVIEW — CYCLE 2 — pp-ingest (F1 calibration-reuse, 32fd1d99 + cycle-1 fixes)

**heimdall_glm (z-ai/glm-5.3-flash) — second pass.** I re-walked every gate of `_reuse_calibration` (service.py:574-613), the `check_once` once-guard (615-623), the outage-retry interaction (`_calibrate_checkers` 535-572), the flagcheck factoring (flagcheck.py:333-349), and the A19 report fixes (purge.py:236-289, 506-510; service.py:792-796; tools/ingest_watch.py:194-195). I also re-derived the questions the prompt asks, since cycle 1's consensus answered them but nobody traced the *writer* side of the kv record end-to-end against the *reader* side.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Honest accounting, finding by finding:**

**1.1 — muse's "old record without `unmeasured` could pass the truthiness check" (muse #2, service.py:602-603).** I noted in cycle 1 that the `not cal[b].get("unmeasured")` clause is *redundant* given `of == 16 == right`, but I did not work the converse case: an old record where `unmeasured` is *absent* (not 0). `not None == True`, so it passes. Muse then correctly resolved it: such a record also lacks `asked_at` (the cached-era writer never wrote it), so it dies at the asked_at gate at :594-597 before the truthiness check is ever reached. I missed the *closure* of that argument — I flagged the redundancy but didn't chase whether the missing-key case was actually reachable. Muse's chain is right: the two gates compose. **Caught by muse, missed by me.** (And it's worth stating precisely: the redundancy is *harmless* precisely because the asked_at gate stands in front of it; if anyone ever removes the asked_at gate, the `unmeasured`-absent case becomes live, so the clause is doing real defensive work.)

**1.2 — muse's clock-skew note (muse #1).** Muse observed that a backward clock jump after calibration makes a stored asked_at appear future, the `0 <=` check rejects it, and the cost is 32 unnecessary live calls — "not a correctness bug, but worth noting." I verified the future-asked_at rejection in cycle 1 (Gate 4) but did not note the *operational* consequence: a single NTP step-back at restart silently forfeits the reuse and pays the 32-call calibration. Muse is right that it's fail-closed and therefore not a defect; I'd now add that the log line at :606 (cycle 1's fix) makes it *visible* — "asked -0.3 h ago" — which is exactly the right treatment. **Caught (as an observation) by muse; I verified the mechanism but not the operational cost.**

**1.3 — qwen's self-corrected KeyError analysis (qwen #1).** Qwen's cycle-1 output is notable for *watching itself correct its own error mid-stream*: it first claimed `cal[b]` at :602 could raise KeyError when `eff` contains a back-end not in `cal`, then traced it: `set(cal) != set(eff)` at :590 returns False *before* :602 is reached, so the KeyError is unreachable. I had asserted the same conclusion in cycle 1 (Gate 2/5) but never showed the reachability argument. Qwen's final verdict — "the logic is actually quite tight" — matches mine. Nothing new, but the *argument* is now on the record, which matters for a forensic audit.

**1.4 — What nobody caught (including me), which this cycle found — see §3.** There are two genuinely new items: the `check_recal_s` reset asymmetry, and the `seconds`-field staleness in the reused record. Details below.

---

## 2. WHERE DO I AGREE OR DISAGREE?

**2.1 — muse #1 (future asked_at / clock skew): AGREE, correctly classified.** The check at :598 (`not 0 <= self.clock() - t.timestamp() < CHECK_RECALIBRATE_S`) does reject a future asked_at; the mechanism is exactly as I traced in cycle 1 (Gate 4). Muse's classification ("not a correctness bug") is right: it fails closed to a live calibration, which is the designed fallback. The cycle-1 refusal log (muse's own P1, now fixed) makes it observable. No action.

**2.2 — muse #2 (old record without `unmeasured`): AGREE, and the composition argument is the important part.** As worked through in §1.1: the missing-`unmeasured` case passes the truthiness check at :603 but cannot reach it, because the cached-era record also lacks `asked_at` and dies at :596-597. One refinement I'd add: the *current* writer (service.py:564-567) always writes `unmeasured` (it's in the copied key tuple), so the only record that could ever lack it is the cached-era one — which is exactly the one the asked_at gate catches. The gates are not independent; they're *layered*, and the layering is what makes the redundancy safe. Agree with muse's "Safe."

**2.3 — qwen #1 (the KeyError that wasn't): AGREE with the final (corrected) verdict.** The set-equality gate at :590 guarantees `cal[b]` is defined for every `b in eff` at :602. Qwen's initial claim of a "critical race condition" (its section header) was wrong; its own correction was right. I'd note the *actual* concurrency story, which nobody stated: `_reuse_calibration` runs only inside `check_once`, which runs only on the check loop's thread (service.py:871, one thread, `CHECK_EVERY_S`); `check_allowed`/`check_calibrated`/`check_recal_s` are written there and read in `check_row` (via `self.check_allowed` at :505) — but `check_row` runs on the `self.checks` executor *after* `check_once` submitted it, and the fields are assigned before any submit. There is no race. Qwen's "critical race condition" headline was wrong; its body quietly conceded it. **Partially agree: right conclusion, wrong headline.**

**2.4 — qwen #2 (purge `fail()` accumulation): AGREE.** The `fail` helper (purge.py:248-249) correctly accumulates: `unresolved[v] = f"{unresolved[v]}; {why}" if v in unresolved else why`. I verified the three call sites (:272, :281, :288) — a video failed by two deliveries (e.g. its PROVENANCE names no sha256 in run A, and no copy with the hash in run B) now reads `runA: ...; runB: ...` instead of silently keeping only the last. This is the a19 c2 fix (glm, minimax) and it's correct. The `kept_of` lookup at :490-491 (by video id, not filename) and the dry-run counting at :509-510 (glm N4) were already in the tree at cycle 1 and remain correct.

**2.5 — muse's Shorts/URL finding (watch.py:216): AGREE it's real, AGREE it's out of scope.** `"/shorts/" in (e.get("url") or "")` misses flat-playlist entries whose `url` is a `watch?v=` form; those Shorts are queued as `discovered` and later correctly gated by `fetch.py:157` (`media == "short"`). Cost: one wasted probe per Short. The cycle-1 consensus recorded it as "its own change" — right call; it's a pre-existing inefficiency, not a defect of this diff, and the *correctness* backstop (fetch's media_type) is the one that matters.

**2.6 — qwen's purge dry-run note: AGREE, already resolved.** Qwen's P1 (the dry run's `deleted` counts what *would* go) was recorded in the cycle-1 consensus as "audited in a19 c2, glm N4: the summary says 'would free' / 'would go'; the dry run is the CLI's default, never the watcher's." The code at :509-510 now carries the comment. Nothing to do.

**2.7 — glm's own cycle-1 P1s (metrics surface; A/B in-flight convention): unchanged, correctly recorded as outside this change.** I agree with the consensus's disposition of both.

**2.8 — One place I *disagree with the framing* of the cycle-1 consensus:** it says "An old record without `unmeasured` cannot pass (it has no asked_at either: muse)." That's true of the *cached-era* record, but it's worth being precise that the invariant is *not* enforced by the code — it's enforced by the *history of the writers*. If a future writer ever emits `unmeasured`-less entries *with* an asked_at, the truthiness clause at :603 would admit a back-end with unknown unmeasured count. Today that's impossible (the only writer is :564-567, which always writes it); the defense is the writer's discipline, not a check. I'd record this as a P3 note, not a change: the clause at :603 is the right *belt* and the writer is the *braces*, and a one-line comment on :603 would pin the invariant. (See §6.)

---

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2, real, new — the reuse resets the outage-retry doubling, and that's *mostly* right but the interaction is unstated):** `_reuse_calibration` at :608 sets `self.check_recal_s = CHECK_RECALIBRATE_S` unconditionally. Consider this sequence: (a) the service runs, a calibration *fails* (muse 502, nobody passed, one could) → `_calibrate_checkers` sets `check_recal_s = CHECK_RETRY_S` (600) at :556; (b) the service *restarts* before the retry fires; (c) at restart, the stored record is the *failed* calibration — nobody passed — so the reuse gate at :602-604 yields `allowed = []` and... wait, check: `why = None if allowed else "no back-end passed it"` → the reuse is *refused* (why is truthy) → live calibration. Good, that path is right. But now: (a') a calibration *passes* (allowed non-empty, `check_recal_s = 86400`); (b') the service runs 20 h; (c') a *later* calibration fails (outage) → `check_recal_s = 600`; (d') restart; (e') the stored record is the *failed* one → refused → live. Also right. Now the case that matters: (a'') calibration passes; (b'') restart 6 h later → reused, `check_recal_s = 86400` — but the *stored record's* `check_recal_s`-relevant history (was the previous calibration's doubling mid-sequence?) is discarded. Is that wrong? No: the reused record *is* a passing calibration, so the doubling state (which tracks consecutive *failures*) is correctly reset — a pass resets the doubling by design (:553-554). So the reset at :608 is *semantically correct*; the finding is that **nobody, in either cycle, traced this** — the correctness of `check_recal_s = CHECK_RECALIBRATE_S` at :608 depends on the invariant that a reused record is always a *passing* record, which is exactly what the `allowed`-non-empty requirement guarantees. It holds. But it's an *implicit* coupling: if someone later relaxes the reuse gate to admit a record where nobody passed (e.g. to skip the 32 calls when the watcher is quiet), the :608 reset would silently convert a mid-doubling outage retry into a day's wait — the exact failure F1's retry logic was written to prevent. **Record, don't change: add the coupling to the docstring of `_reuse_calibration` (one clause: "a reused record is a passing one, so resetting the doubling here is the pass's own reset").**

**N2 (P3, new — the reused record's `seconds` and `wrong` fields are stale by construction, and the log line could mislead):** the stored record (written at :564-567) carries `seconds` (the live calibration's duration) and `wrong` (the failing back-ends' wrong answers). After a reuse, `stats.live` (stats.py:141-143) reports `ck["calibration"]` = the stored record verbatim — including `seconds` from the *original* calibration, possibly ~23 h old, and `wrong` entries from back-ends that may since have been... no, wait: the model-identity gate at :590-591 pins the models, so `wrong`'s *models* are current; the *answers* are 23 h old but the record *is* 23 h old, and `asked_at` says so. Actually, on reflection this is *correct*: the record is a historical measurement, its `asked_at` dates it, and the reuse event (`check_calibration_reused`, :609) plus the log line (:610-612) say it was reused. The only genuinely misleading case: `seconds` reads as if the *reuse* took that long. It doesn't; the reuse takes ~0 s. Nobody is misled in practice (the event and log line carry the reuse). **P3, note only: no change.** I'm recording it because cycle 1's consensus said "the four refusal tests assert the reason" and "the reuse event" — but nobody asked what the *stale* fields of a reused record mean downstream. They mean what they say: a 23-h-old measurement. Fine.

**N3 (P3, new — `watcher_probes()` is called at reuse time, not stored; a PROBES edit between the calibration and the restart changes `n` silently):** the reuse gate at :601-602 computes `n = len(flagcheck.watcher_probes())` *now*. If PROBES gained a 17th watcher quote between the stored calibration and the restart, the stored record (of=16) fails `cal[b].get("of") == n` → refused → live. Correct (fail closed). But the *log reason* would be "no back-end passed it" — which is technically true but misleading: the record *passed* 16; the *bar moved*. The refusal reason at :604 conflates "nobody passed" with "the quote set changed." A more precise reason would name the count. **P3: the behavior is right, the diagnostic is slightly lossy.** Given the cycle-1 fix (muse) already made refusals logged-with-reason, this is a diagnostic-polish note, not a defect. (And the quote set changing is itself a design-16 event that would warrant a fresh calibration anyway.)

**N4 (P3, verified, new — the once-guard's failure path is exactly one wasted 30 s, and the *reason* is subtle):** if `_reuse_calibration` raises (it can't — every failure mode is caught: `json.loads` ValueError at :583-586, `config.aware` TypeError/ValueError inside, `KeyError` proven unreachable in §2.3, `watcher_probes()` is a pure filter — actually, can it raise? `PROBES` is a module-level tuple of 3-tuples; the filter `p[0] in flags` cannot raise. And `self.router.effective(ROLE)` at :587 — can *that* raise? It reads `self.cfg["roles"][role]` (present, `check_roles` at :112 guarantees it), `self.order(role)` (reads `self.meter.state()` — the meter's lock, no exception), `self.backends[b].enabled()` (a dict-get + bool). No. So `_reuse_calibration` cannot raise, and the once-guard at :619-621 never burns its one attempt on an exception. Good — but *nobody proved this in either cycle*; qwen's cycle-1 "critical race" excursion came close. The proof is now on the record: every failure path inside `_reuse_calibration` is either caught, unreachable, or a pure function of module constants. **P3, note: the once-guard is safe by construction, now demonstrated.**

**N5 (P3, new — the reuse event's `allowed` list is the *ids*, and the log line's "next calibration in" arithmetic can print a negative number in one corner):** at :612, `CHECK_RECALIBRATE_S - (self.clock() - t.timestamp())` — the two `self.clock()` calls at :598, :611, :612 are *separate* reads. With the injected test clock (a constant) they're equal; with `time.time` they can differ by microseconds. If the clock advances past `t.timestamp() + CHECK_RECALIBRATE_S` *between* the gate check at :598 and the arithmetic at :612 — impossible in practice (the gate just verified the difference is < 86400, and the elapsed time between :598 and :612 is microseconds) — the printed number would be... still positive. Actually: the gate at :598 guarantees `clock1 - t < 86400`; at :612, `clock2 - t < 86400 + (clock2 - clock1)`. For the printed value to go negative, `clock2 - clock1` would need to exceed `86400 - (clock1 - t)`, i.e. the *remaining* budget — which for a record 23.99 h old is ~36 s. So: a restart whose reuse-gate evaluation takes > 36 s (a very slow `router.effective`? no — it's microseconds) could print a negative "next calibration in". Theoretical; the *behavior* (check_calibrated = t.timestamp()) is unaffected. **P3, note only.** I include it because it's the kind of thing a third cycle would waste time on; it's provably benign.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `_reuse_calibration` gates (service.py:574-613) | 9.5/10 | 9.5/10 | Unchanged: every gate fails closed; the muse/qwen cross-examination (§2.1-2.3) confirmed the layering; my N1/N4/N5 are notes, not defects. |
| Once-guard + retry interaction (615-623, 535-572) | 9/10 | 9.5/10 | +0.5: N1's coupling (a reused record is a passing one, so the :608 reset is the pass's own reset) is now *proven*, not assumed; N4 proves the guard cannot burn its attempt on an exception. |
| flagcheck factoring (flagcheck.py:333-349) | 10/10 | 10/10 | `watcher_probes` is a pure filter; `watcher_checkers`' behavior is byte-identical (same probes, same rounds, same pass rule). |
| A19 report fixes (purge.py:236-289, 506-510; service.py:792-796; tools:194-195) | 9.5/10 | 9.5/10 | The `fail()` accumulation is correct (§2.4); the CLI's unresolved listing (tools:194-195) closes the a19 c2 loop; the dry-run counting comment (purge:509-510) matches the audited behavior. |
| Test coverage of the change | 9/10 | 9/10 | 328 collected; the four refusal cases + the fake-clock day-coupling test are mutation-checked per the consensus. My N3 (the "quote set changed" reason) and the §2.8 writer-discipline invariant are *untested* — but both are notes, not gaps that could ship a bug. |
| Docs/design (design 16, module docstring) | 9.5/10 | 9.5/10 | The refusal-logging and the restart paragraph landed as the consensus said; the module docstring (service.py:17-25) now states the start's conditional calibration accurately. |

**Overall: 9.4/10 (cycle 1: 9.3).** The cross-examination raised my confidence in the gates' *composition* (not just each gate); the new findings are all P3 notes.

---

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** none.

**P1 HIGH:** none.

**P2 MEDIUM:**
- **P2-1 (service.py:608 + 574-582):** the docstring of `_reuse_calibration` should state the N1 coupling — that a reused record is by construction a *passing* one, so resetting `check_recal_s` to `CHECK_RECALIBRATE_S` there is the same reset a passing calibration performs at :553-554, and that relaxing the reuse gate to admit a nobody-passed record would silently defeat the outage doubling. One clause. (Behavior correct today; the invariant is enforced only by the gate, and the gate is the only thing that would change.)

**P3 (record, no change):**
- (service.py:602-603) the `not cal[b].get("unmeasured")` clause's correctness for an *absent* key rests on the *writer* (564-567) always writing it; a one-line comment would pin it (§2.8).
- (service.py:604) the "no back-end passed it" reason also fires when the quote set changed (N3); a count in the reason would disambiguate.
- (stats.py:141-143) a reused record's `seconds`/`wrong` are the original calibration's, correctly dated by `asked_at` (N2).
- (service.py:612) the "next calibration in" arithmetic uses a second clock read; provably benign (N5).

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Document the one implicit invariant that carries the most correctness: **a reused calibration record is, by the gate at service.py:602-604, always a *passing* one — which is precisely what makes the unconditional `check_recal_s = CHECK_RECALIBRATE_S` at :608 the same reset a passing calibration performs, so anyone who later relaxes that gate to admit a nobody-passed record must also revisit :608, or the outage doubling (F1's own fix) silently dies.** One clause in the docstring; it protects the interaction nobody traced in either cycle.

---

## 7. PRODUCTION READY?

**Yes.** Conditions (all P2/P3, none blocking):

1. **(P2-1)** Add the one-clause note to `_reuse_calibration`'s docstring (service.py:574-582) recording the reused-record-is-passing invariant behind the :608 reset — the coupling that neither cycle traced and that a future gate relaxation would silently break.
2. **(P3, optional)** One-line comment at service.py:602-603 noting that the `unmeasured`-absent case is closed by the asked_at gate *plus* the writer's discipline (564-567), so the truthiness clause is belt, the writer braces.
3. **(P3, optional)** In the refusal reason at :604, include the counts (e.g. `of=16/17`) so a PROBES-set change is distinguishable from "nobody passed" (N3).

Everything else — the gates' fail-closed composition, the once-guard, the outage-retry interaction, the day-after-the-live-one coupling (now pinned by the fake-clock test), the refusal logging, the A19 fixes — I've verified line-by-line and, where cycle 1 left an argument implicit (the KeyError reachability, the guard's exception-safety, the doubling reset), this cycle puts the proof on the record. Ship it.