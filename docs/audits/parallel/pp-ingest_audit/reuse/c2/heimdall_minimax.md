# heimdall_minimax (minimax/minimax-m3.1-flash, 360.9 s, $0.010, finish stop)

# CYCLE 2 REVIEW — pp-ingest (F1 calibration reuse, 32fd1d99 + cycle‑1 fixes)

*(I did not answer in cycle 1; this is my first full pass, written with the other three reviews in hand.)*

---

## 1. WHAT THE OTHERS CAUGHT THAT I WOULD HAVE MISSED

Because cycle 1 was empty for me, the honest framing is: I re-derived the core findings independently and **concur with all of them**; the cycle‑1 consensus is correct and I found no path that contradicts it.

Specifically, the three things I would most likely have under-weighted, and which the others nailed:

- **The `set(cal) != set(eff)` short-circuit is what makes `cal[b]` safe.** qwen raised a `KeyError` risk at service.py:602 and then corrected himself; I re-verified: `set(cal) != set(eff) or not all(...)` short-circuits, so the `all(...)` generator (and the later `cal[b]` lookups) only run when the key sets are identical, and `eff ⊆ router.backends`. **No `KeyError` is reachable.** Confirmed.
- **The `unmeasured` clause at service.py:603 is redundant** (of == 16 == right already implies unmeasured == 0, since `of` counts *answered* quotes). glm is right; harmless.
- **The "next calibration a day after the LIVE one, not after the restart" coupling** (service.py:608, `check_calibrated = t.timestamp()`) is the single most important line in the change, and the cycle‑1 fake-clock test now pins it. Without it the reuse would silently extend the exposure window of a stale measurement by one restart interval per restart — the exact failure the change is meant to avoid.

I also agree with the three "recorded, not changed" items (metrics surface, watch.py Shorts detection, purge dry-run `deleted` counts): all are outside this diff and were audited elsewhere.

---

## 2. WHERE I AGREE / DISAGREE

| Other finding | Verdict | Why |
|---|---|---|
| glm: every reuse gate fails closed to a LIVE calibration | **Agree** | I walked all six gates independently; same conclusion. The crash record is `{}` (service.py:561) → "none stored"; the cached-era record has no `asked_at` → `config.aware(None)` → `None` → refused; a future `asked_at` gives a negative age → refused by `0 <= …`; two `asked_at` values → `len(asked) != 1` → `t is None` → refused. |
| glm: `unmeasured` check redundant | **Agree** | `of == 16` ⇒ every quote answered ⇒ `unmeasured == 0`. |
| muse: `_reuse_tried` is a one-shot latch; a refusal falls through to the live path | **Agree** | service.py:619‑621 sets the latch *before* the call; a refusal leaves `check_allowed is None`, so service.py:622‑623 runs `_calibrate_checkers()` live. Fails closed. |
| muse: a refusal is now logged with its reason | **Agree** | service.py:605‑606. This is the cycle‑1 fix and it is the right shape (the four refusal tests assert the reason). |
| qwen: the `KeyError` risk at service.py:602 | **Disagree (as corrected by qwen himself)** | The set-equality short-circuit makes it unreachable. |
| Consensus: "an outage calibration is never reused" | **Agree, with a precision** | Precisely: a calibration in which **nobody** passed is never reused. A calibration where back‑end A passed and B was in an outage *is* reused, with `allowed = [A]` — correct, since A was measured live and passed, and B is excluded by `of < 16`. |
| Consensus: the outage retry (CHECK_RETRY_S doubling) is untouched | **Agree, and I checked the coupling explicitly** | A *passing* calibration always sets `check_recal_s = CHECK_RECALIBRATE_S` (service.py:553‑554, `if allowed or not could`), and a *failing* one is never reusable. So the reuse's `check_recal_s = CHECK_RECALIBRATE_S` (service.py:608) can never stomp a shortened retry wait. The doubling survives restarts unchanged. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

**N‑1 (P2) — The stored calibration carries no prompt/probe version, so a change of definitions does not invalidate it.**
`ledger.check_valid` (ledger.py:223) already refuses a *check answer* whose `prompt_version` is not the current one. The **calibration** record has no equivalent guard: `_calibrate_checkers` stores only `model, right, of, unmeasured, asked_at, seconds, wrong` (service.py:564‑567). If `flagcheck.DEFINITIONS["imperative"]` is edited and `PROMPT_VERSION` bumped (the sharpened‑accusation work shows definitions do move), a stored calibration measured under the *old* definition is still reused for up to a day, and the back-end is allowed to release hard flags under the *new* one without ever having been measured on it. Same hole for a change to the probe set itself (`PROBES`): the count `n = len(watcher_probes())` stays 16 while the content changes.
*Fix:* store `prompt_version` (and/or `sha256` of the 16 watcher quotes) in the record and require it to match in the reuse gate — one extra key, one extra condition, mirroring `ledger.check_valid`.

**N‑2 (P2) — Liveness is inferred, not asserted.** The reuse trusts "has `asked_at`" as a proxy for "was asked live". Today that holds (the F1 change added `fresh=True` and `asked_at` together), but nothing in the record says so. A future writer of the same kv key — e.g. a CLI that stores a *cached* calibration for reporting — would be silently trusted by the reuse gate.
*Fix:* store `"live": True` in the record and require it.

**N‑3 (P3) — `asked_at` is stamped with the wall clock, the age gate uses the service clock.** `_calibrate_checkers` stamps `asked = config.iso()` (service.py:538), i.e. `datetime.now(timezone.utc)`, while the gate compares against `self.clock()` (service.py:598), the *injected* clock. In production they agree; under a test harness with a fake clock, or if the service's clock is ever corrected, the age judgement is made against a different clock than the stamp. (This is why the reuse tests must write the kv by hand rather than going through `_calibrate_checkers`.)
*Fix:* stamp `asked_at` from `self.clock()` (or compare with `config.now()`), so the stamp and the gate share one clock.

**N‑4 (P3) — `kv_get` can raise `TypeError`, which the reuse does not catch.** service.py:583‑586 catches only `ValueError`. `Queue.kv_get` does `json.loads(r[0]["v"])`; a NULL column would raise `TypeError` and escape `_reuse_calibration` → `check_once` → the `_loop` handler. It fails closed (the latch is already set, `check_allowed` stays `None`, the live calibration runs next loop) but it is a noisy `loop_error` instead of a clean refusal. *Fix:* `except (TypeError, ValueError)`.

**N‑5 (P3) — the reuse is invisible in live.json.** `stats.live` publishes `second_model_checks_12h.calibration` (stats.py:140‑143) — the raw record — but nothing says the *current* `check_allowed` came from a reuse rather than from a live calibration. The event `check_calibration_reused` is in the queue only. The orchestrator reading live.json cannot see that the checker is running on a measurement up to a day old. *Fix:* one key in the live.json block (`"calibration_reused_at"`), or fold it into the existing record.

**N‑6 (P3) — two cosmetic log defects.** (a) The reuse line prints `t.isoformat()[:19]Z` (service.py:610): the `Z` is appended to whatever offset the stored `asked_at` carries; today it is always UTC (`config.iso()`), but the gate accepts any zoned time, so the label can lie. (b) The age-refusal message prints `asked -0.5 h ago` for a *future* `asked_at` (service.py:599) — the parenthetical comment explains it, the log line does not. *Fix:* "asked in the future (the clock went back)".

**N‑7 (P3, F1 wording) — the reuse log does not use F1's own words.** F1 requires the calibration log line to say *live* or *replayed*. The reuse line says "calibration reused (asked live at …)", which is truthful but not the required vocabulary. *Fix:* "reused (not replayed: the record was asked live at …)".

**N‑8 (observation, not a defect) — the change does not help the exact incident it cites.** The 09:16 false plan_b came from a restart whose live calibration ended on a muse 502 — i.e. a calibration in which **nobody passed**. Such a record is (correctly, per F1) never reusable, so the *next* restart asks the 32 quotes live again and may fail again. The change removes the 32 calls only in the case where the previous calibration **passed**. That is the right trade (F1 forbids reusing an outage calibration), but the incident narrative in the docstring ("each restart's live calibration ended on muse's 502s") overstates what the change fixes. Worth a docstring sentence, not a code change.

**N‑9 (P3) — the A19 `fail()` accumulation is correct but unbounded.** `unresolved[v]` grows with one `"; "`-joined clause per failing delivery; a video in many deliveries yields a long string. It is written into `purge_last` (service.py:795) and printed by the CLI (tools/ingest_watch.py:194‑195). Bounded in practice (deliveries per video are few), but a cap (e.g. first 5 + "…") would be prudent for a kv value that lands in live.json. No correctness impact.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `service._reuse_calibration` (the reuse gate) | — (no answer) | **9/10** | All six gates fail closed; the day-after-the-LIVE-one coupling is correct and now test-pinned. −1 for N‑1/N‑2 (no version/liveness marker in the record). |
| `service.check_once` / the check loop | — | **9/10** | The one-shot latch, the fall-through to the live path, and the untouched outage doubling are all correct. −1 for N‑4 (uncaught `TypeError`). |
| `flagcheck` (WATCHER_FLAGS / watcher_probes factoring) | — | **10/10** | Pure factoring, no behaviour change; `watcher_checkers` now and the reuse gate now read the same 16 quotes from one place. |
| `purge.py` A19 fixes (in-diff) | — | **9/10** | `fail()` accumulation and the dry-run counting are correct; −1 for N‑9 (unbounded string). |
| `tools/ingest_watch.py` (in-diff) | — | **9/10** | The unresolved listing is right; −1 for the same unbounded string. |
| **Overall** | — | **9/10 — production-ready with two P2 follow-ups** | |

---

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none.

**P2 MEDIUM**
1. **N‑1** — `pipeline/ingest/service.py:564‑567` + `:588‑592`: store `prompt_version` (and/or a hash of the 16 watcher quotes) in the calibration record and require it to match in the reuse gate; otherwise a calibration measured under old definitions is reused under new ones for up to a day.
2. **N‑2** — `pipeline/ingest/service.py:564‑567` + `:588`: store an explicit `"live": True` in the record and require it, instead of inferring liveness from the presence of `asked_at`.

**P3 LOW**
3. **N‑3** — `service.py:538` vs `:598`: stamp `asked_at` from `self.clock()` (or compare with `config.now()`), so the stamp and the age gate share one clock.
4. **N‑4** — `service.py:583‑586`: catch `(TypeError, ValueError)` around `kv_get`/`json.loads`.
5. **N‑5** — `stats.py:140‑143`: say in live.json that the current `check_allowed` came from a reuse.
6. **N‑6/N‑7** — `service.py:599`, `:610`: "asked in the future (the clock went back)"; "reused (not replayed: the record was asked live at …)"; do not append `Z` to a non-UTC offset.
7. **N‑9** — `purge.py:248‑249`: cap the accumulated `unresolved` reasons.
8. **N‑8** — `service.py:574‑582`: one docstring sentence saying the change removes the start's calls only when the previous calibration **passed**.

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Add a `prompt_version` (and an explicit `"live": true`) to the stored calibration record and require both in the reuse gate** — it is the only hole left through which a back-end could be allowed to release hard flags on a measurement that was never taken under the definitions now in force.

---

## 7. PRODUCTION READY?

**Yes, with conditions.**

Ship it. The reuse gate is tight, every path fails closed to a live calibration, the outage retry and the daily schedule are provably untouched, and the cycle‑1 fixes (the refusal reason, the fake-clock test pinning "a day after the LIVE one") close the two things that were genuinely open.

Conditions, precisely:

1. **Before or immediately after the merge** (P2, one-line-each): add `prompt_version` and `"live": true` to the record written at `service.py:564‑567` and require them in the gate at `service.py:588‑592`. If the record is written without them, the gate must **refuse** (fail closed) — do not make the new fields optional, or the first record written by the old code would be trusted.
2. **P3s may follow** in the next change; none of them affects correctness of the shipped behaviour.
3. **Operational note to carry into the runbook:** the reuse only removes the start's 32 live calls when the *previous* calibration **passed**. A watcher whose last calibration failed (the 09:16 incident's shape) will still ask all 32 quotes live at the next start — by design, since F1 forbids reusing an outage calibration. Do not read the change as "restarts no longer cost 32 calls" in general.
4. **Do not** relax any of the six gates to make a reuse succeed in the field (e.g. accepting a record whose key set is a subset of `eff`, or accepting a `asked_at` without a zone). Every one of them is load-bearing for the fail-closed property the other three reviewers and I verified independently.