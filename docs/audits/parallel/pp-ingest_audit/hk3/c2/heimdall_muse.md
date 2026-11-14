# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 428.2 s, $0.031, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (mine-hook/3 + spotlight)

**Branch:** `pp-ingest` @ `ef431ff5` vs `197b35ec` | **Reviewer:** heimdall_muse (Cycle 2)

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Honest accounting:**

| Their finding | I missed? | Why |
|---|---|---|
| **GLM (a): hook_video crash between two mine_video calls discards hook rows** | **Yes, missed.** | I walked the happy path `lines + spot` append at `service.py:424` but did not trace the `except Exception` at `service.py:438-447` that fires *between* the two `mine_video` calls. Hook rows are in-memory only until `_append`; a spotlight exception loses them. I dismissed it as "costly but not lossy" would have been correct severity, but I didn't flag it at all. |
| **GLM (b): spot_rows observability gap when spotlight fails** | **Partially missed.** | I noted `spot_rows=len(spot) if srep is not None else None` was correct for NULL vs 0, but didn't follow the `tries >= HOOK_TRIES` fallthrough where `spot_rows=0` conflates "asked, none passed filter" with "asked, all windows rejected". GLM correctly identified the note doesn't distinguish which question failed — now fixed in C1-2. |
| **GLM: check_roles missing flagcheck** | **Missed.** | I audited `mine.KINDS` roles but didn't cross-check `flagcheck.ROLE` against `providers.json`. A missing `flagcheck` role would crash-loop calibration every 30s. C1-1 fixed it. |
| **GLM: adapter read-through for spotlight** | **Missed.** | I verified `carry_forward` and `best_unused_moments` exclusions in isolation, but never traced a spotlight row *through* `best_unused_moments` to confirm no `role_hint` filter drops it. C1-3 added the regression guard. |
| **Qwen: episode_measure called twice** | **Not missed — correctly dismissed.** | I noted it in Step 1 walkthrough as deterministic re-measure; Qwen flagged as redundant. Agree: low impact, not a bug. |
| **Qwen: "2 spotlights dilutes intent"** | **Correctly refuted.** | Qwen questioned SPOT_MAX=2 vs "ONE passage" language. Consensus correctly refuted: code, prompt, validator, and ruling 90 all allow 2 per window; prompt says "1 to 2". |

**Root cause of my misses:** I audited the diff's *new code* line-by-line but under-audited the *interaction* between the two sequential `mine_video` calls inside `hook_video` and the *cross-module* contract (flagcheck role, adapter filter). GLM's end-to-end failure-mode walkthrough was stronger there.

---

## 2. WHERE DO I AGREE OR DISAGREE?

### GLM findings:

- **(a) Crash between hook and spotlight loses hook rows — AGREE, P2.** `service.py:401-408`: `lines, rep = mine_video(kind="hook")` then `spot, srep = mine_video(kind="spotlight")` then `_append(lines+spot)`. Any exception in the second call (including `ContractUnavailable` is caught, but `episode_measure` KeyError, `mine_window` bug, etc.) hits `except Exception` at `service.py:443` which only sets `hook_next_ts` — hook rows discarded. Retry re-asks hook (cache makes it free). Not data loss, but wasted work and delayed hooks. **Fix:** append hook rows before spotlight, or wrap spotlight in its own try/except. C1 did not fix this — still open.

- **(b) spot_rows NULL vs 0 observability — AGREE, P3, now fixed.** C1-2 splits `hook_note` into `hook N, spotlight M` and event into `failed_hook`/`failed_spotlight`. Correct fix.

- **(c) hook_once vs mine_once race on same video — DISAGREE it's a bug, AGREE it's worth noting.** `hook_due` selects `MINED, MINED_PARTIAL`; `mine_once._settle` can flip `MINED_PARTIAL→MINED` concurrently. But `hook_inflight` + single-process `flock` + `hook_due` re-read each cycle makes this benign. Stale `hook_tries` snapshot could cause one extra retry at most. P4.

### Qwen findings:

- **Spotlight prompt "contradicts definition" — DISAGREE.** Prompt says "1 to 2 passages", `SPOT_MAX=2`, validator enforces 2. Ruling 90's "ONE passage" describes a spotlight *clip*, not a window cap. Internally consistent.

- **Cost query race — DISAGREE it's a bug.** `service.py:409` `SUM(cost_usd) WHERE video_id=? AND role IN ('hook','spotlight')` filters by `video_id`; concurrent writes for other videos don't affect it. SQLite WAL gives consistent snapshot. Correct.

- **episode_measure called twice — AGREE, P4.** Redundant but deterministic. Could hoist `episode` from first `mine_video` report to avoid second measure. Not worth blocking.

### Muse (my Cycle 1) findings:

- **Starvation on shared hook_windows executor — STAND BY, P3.** 4 slots shared between hook and spotlight windows of same video. With 2 videos × 8 windows × 2 questions = 32 tasks on 4 threads, hook pass latency doubles for conversations. Not a correctness bug; matches `HOOK_WINDOWS=4` design intent ("moment passes keep the rest"). Declined in consensus — agree with decline.

- **Ternary readability `max_n = HOOK_MAX_CONVERSATION if kind=="hook" and is_conversation else KINDS[kind]["max_n"]` — AGREE, P4.** Correct but misleading for spotlight readers. Minor.

---

## 3. NEW FINDINGS FROM THIS REVIEW (Cycle 2)

### N1 — `mine.py:565` max_n threading is correct but fragile (P3)

```python
max_n = HOOK_MAX_CONVERSATION if kind == "hook" and is_conversation(episode) else KINDS[kind]["max_n"]
```

For `kind="spotlight"`, this always yields `KINDS["spotlight"]["max_n"]=2`. Correct per spec (spotlight is always 2). But the condition couples `kind` check to `is_conversation` — if a future `KIND` adds conversation-sensitive max_n, this ternary silently ignores it. **Recommendation:** make it explicit:

```python
if kind == "hook" and is_conversation(episode):
    max_n = HOOK_MAX_CONVERSATION
else:
    max_n = KINDS[kind]["max_n"]
```

No behavior change; prevents future misread.

### N2 — `service.py:409` cost query double-counts on retry (P2)

```python
cost = self.q.rows("SELECT SUM(cost_usd) FROM calls WHERE video_id=? AND role IN ('hook','spotlight')", (vid,))[0]["usd"]
```

This sums *all* hook/spotlight calls for the video across *all* passes (including failed retries). On `tries=2`, `hook_cost_usd` includes cost of pass 1's failed windows + pass 2's. That's intentional for accounting ("for the video's hook passes so far" in log line `service.py:418`), but `stats.py:112` `SUM(hook_cost_usd)` then double-counts retries in `hooks_12h.usd`. **Not a bug** if the metric is defined as "total spent", but the label `usd` in `hooks_12h` should document it. Currently ambiguous whether it's "last pass" or "all passes".

### N3 — `ledger.py:205-206` carry_forward role_hint fix is correct but incomplete for re-mine (P3)

```python
if e.get("role_hint") and not l.get("role_hint"):
    l["role_hint"] = e["role_hint"]
```

This correctly carries `hook` or `spotlight` hint to a later line with no hint (e.g., a `mine` re-mine of same moment). But if a moment was first mined as `spotlight` then re-mined as `hook`, the new line has `role_hint="hook"` and keeps it — correct per "later line's own hint wins". However, the *reverse* (hook then spotlight re-mine) would keep `spotlight`, losing the hook hint. Since `best_unused_moments` doesn't filter on `role_hint`, this is currently harmless. But if the builder ever filters by `role_hint`, the last-write-wins semantics could hide a hook. **Recommendation:** document that `role_hint` is informational only and never used for filtering (already stated in design section 15, now fixed per C1-4).

### N4 — `mine.py:602-615` duration filtering uses `duration_estimate_s` fallback (P2, pre-existing)

```python
d = l["duration_s"] if l["duration_s"] is not None else l["duration_estimate_s"]
```

For `timing=="word"`, `duration_s` is measured; for `timing=="segment"`, it's `None` and `duration_estimate_s` is used. The estimate is `end - start` from segment boundaries, which can be off by seconds for long segments. A 11s spotlight estimated as 13s would be kept; a 13s spotlight estimated as 11s would be dropped. **Pre-existing**, not introduced by this diff, but spotlight's 12-35s window is more sensitive to this than hook's 4-14s because segment-timed videos are common for auto-captions. No fix needed now; flag for monitoring via `rep["dropped_s"]`.

### N5 — `providers.json` spotlight chain duplicates hook chain (P4, by design)

Both `hook` and `spotlight` use `["heimdall_qwen27b", "local_gemma"]`. Under spend freeze, both are Heimdall-only. This means a conversation's hook and spotlight windows compete for the same back-end's `max_inflight` slots (12 for qwen, 1 for local). No isolation. Acceptable per ruling — spotlight is "the hook role's chain" — but worth noting for capacity planning.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| **Correctness (hook 5 vs 3 gating)** | 9/10 | 9/10 | No change. `is_conversation` fail-closed, `max_n` threaded correctly, solo cache byte-identical — all verified. |
| **Correctness (spotlight lifecycle)** | 8/10 | 7/10 | **Downgraded.** GLM's crash-between-calls finding is real and unfixed. Hook rows lost on spotlight exception. |
| **Correctness (validator/schema/prompt agreement)** | 10/10 | 10/10 | No change. `max_n` → prompt `max_h` → schema `enum [1..max_n]` → validator `MAX_MOMENTS=max_n` all agree. No 6-hook or 3-spotlight leak. |
| **Correctness (ledger/carry_forward)** | 9/10 | 9/10 | No change. Fix from `== "hook"` to `any hint` is correct. N3 is theoretical. |
| **Correctness (queue/stats)** | 9/10 | 8/10 | **Downgraded.** N2 cost double-count on retry is ambiguous metric. |
| **Prompt quality (SPOT_PROMPT)** | 8/10 | 8/10 | No change. Covers ruling 90/92, OPENER rule, NOT list, judge question verbatim. |
| **Resilience (retry/crash paths)** | 7/10 | 6/10 | **Downgraded.** Crash between hook and spotlight calls is the gap. |
| **Test coverage** | 8/10 | 9/10 | **Upgraded.** C1-3 adapter read-through test is strong. Still missing: crash-between-calls test, 6-hook rejection test for conversation path. |
| **Overall** | **8.2/10** | **7.9/10** | Net -0.3: one real unfixed P2 found, one metric ambiguity, offset by test improvements. |

---

## 5. FINAL PRIORITY LIST

### P0 CRITICAL — Must fix before ship
**None.** No data loss, no security issue, no silent corruption. All P0s from Cycle 1 were fixed in C1.

### P1 HIGH — Should fix before ship

| # | File:Line | Issue | Fix |
|---|---|---|---|
| P1-1 | `service.py:401-408` | **Hook rows lost if spotlight throws.** `mine_video(kind="hook")` succeeds, `mine_video(kind="spotlight")` raises → `except Exception` at `443` sets only `hook_next_ts`, hook rows discarded. Retry re-asks hook (cache = free, but delays hooks by 10 min). | Wrap spotlight in its own try/except: on spotlight failure, append hook rows and record `spotlight_failed` separately. Or append hook rows before spotlight call. |

### P2 MEDIUM — Fix soon or document

| # | File:Line | Issue | Fix |
|---|---|---|---|
| P2-1 | `service.py:409` | **Cost metric ambiguous on retry.** `SUM(cost_usd) WHERE role IN ('hook','spotlight')` accumulates across passes; `stats.py:112` sums it as `hooks_12h.usd` without noting it includes retries. | Document in `stats.py` comment or rename to `hook_cost_total_usd`. |
| P2-2 | `mine.py:602-615` | **Duration estimate fallback for segment-timed videos.** `duration_estimate_s` from segment boundaries can misclassify near 12s/35s boundary. | Monitor `rep["dropped_s"]` distribution; no code change now. |
| P2-3 | `service.py:67-68` | **Shared hook_windows executor starves moment passes.** 4 slots for hook+spotlight; conversation doubles hook pass latency. | Accept per design; revisit if p95 hook pass latency exceeds threshold. |

### P3 LOW — Polish

| # | File:Line | Issue |
|---|---|---|
| P3-1 | `mine.py:565` | Ternary readability — expand to if/else. |
| P3-2 | `ledger.py:205` | Document `role_hint` is informational, never filtered. (Done in design C1-4.) |
| P3-3 | `providers.json:112` | Spotlight duplicates hook chain — note for capacity planning. |

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Wrap the spotlight `mine_video` call in `service.py:405-408` in its own try/except so a spotlight failure appends the already-mined hook rows instead of discarding them and retrying both questions.**

---

## 7. PRODUCTION READY?

**Yes, with one condition.**

**Condition:** Fix P1-1 (spotlight crash discards hook rows) *or* accept the risk with a logged TODO and a 10-minute retry delay for the affected video. The failure mode is narrow (spotlight `mine_video` must throw an uncaught exception, not just return `AllBackendsFailed` which is handled), the retry is free via cache, and no data is permanently lost. Every other P0/P1 from Cycle 1 is fixed and verified.

**Without P1-1 fix:** Ship as **Yes, with known issue** — document in `STATE.md` that a spotlight exception delays hook rows by one retry cycle (10 min).

**With P1-1 fix:** **Yes, unconditionally.** The change is otherwise correct, well-tested (305 tests), and the four C1 fixes address the real gaps.

---

### Answers to the 6 Review Questions

1. **Non-conversation getting 5 hooks / spotlight?** No. `is_conversation` requires `isinstance(t, (int,float)) and not bool and t >= 1.0`. Unmarked (`tpm=None`), unmeasured (`{}`), bool, string all return False. Conversation missing it? Only if `episode_measure` miscalculates `turns_per_min` — e.g., `>>` markers inside quoted text counted as turns. Low risk; `TURN_MARK` regex is `>>|&gt;&gt;` without context check. Acceptable.

2. **Validator/schema/prompt/max_n agreement?** Yes, always same number. `mine_video` computes `max_n` once, passes to `mine_window` which uses it for both `PROMPTS[kind](max_h=n)` and `validator(..., n, max_count)`. Schema `enum [1..max_n]` enforced by guided decoding. No 6-hook or 3-spotlight leak. Verified for both conversation (5) and solo (3) paths.

3. **Spotlight rows outside 12-35s / bad opener / missing integrity fields?** No. `mine.py:602-615` filters by `KINDS["spotlight"]["seconds"]=(12,35)` and `bad_opener`. `build_line` at `mine.py:512-547` writes every integrity field (risk, eligibility, expiry, miner_route, episode, speaker). Adapter `best_unused_moments` does not filter on `role_hint` — spotlight rows pass through. Second-model check only looks at `imperative`/`single_source_breaking` flags, not role. Purge ignores role. Stats counts via `spot_rows`. `carry_forward` now handles any hint. All correct.

4. **hook_video retries/failures/cost/columns/log/crash/rerun?** Retries: `failed = rep["failed"] + srep["failed"]`, `rejected = [f for f in failed if not outage]`, `tries += 1 if rejected else 0`, `HOOK_TRIES=3` — correct, outage never consumes try. Cost: `SUM WHERE role IN ('hook','spotlight')` — correct but accumulates retries (P2-1). Columns: `hook_ts/rows/cost/tries/version` + `spot_rows` (NULL for non-conversation) + `episode_markers/tpm` — correct. Log/event: now split `hook N, spotlight M` per C1-2 — correct. Crash: `ContractUnavailable` → `hook_next_ts` retry; generic `Exception` → `hook_next_ts` + event — correct, except P1-1 gap between calls. Rerun: `hooks --rerun` resets `hook_ts=NULL WHERE hook_version != current` — idempotent per version, correct.

5. **SPOT_PROMPT asks for what ruling 90/92 describe?** Yes. Contains: "one speaker's complete claim, number or question that a stranger understands cold and would stop scrolling for" (order verbatim), 12-35s, one speaker / `>>` rule, OPENER rule (pronoun/conjunction/reply sets), judge question verbatim with "only scroll and alone count", whole-clip stand-alone test, NOT list (greeting, date, ad, price prediction, accusation, plus "host reading news / reacting to clip" per ruling 90). Risk flags via `_FLAGS_TEXT`. No prompt injection vector beyond standard `<sentences>` block (already hardened with `<` → `‹`).

6. **Tests prove (B) and (C)? Missing must-fail cases?** (B) proven: `test_a_conversation_is_asked_for_up_to_5_hooks_a_window_and_a_solo_episode_for_3` checks prompt says "1 to 5" for conversation, "1 to 3" for solo, validator rejects 5 hooks to solo, solo prompt byte-identical. (C) proven: `test_the_spotlight_prompt_states_the_ruling...` checks prompt content, `test_the_spotlight_reply_is_strict` checks 3>2 and count 9 rejected, `test_the_spotlight_question_writes_rows_of_12_to_35_seconds...` checks duration/opener filtering and `dropped_s`, `test_the_hook_pass_of_a_conversation...` end-to-end checks spotlight rows through adapter. **Missing:** no test for crash-between-calls (P1-1), no test for 6-hook rejection on conversation path (only solo path tested), no test for spotlight cost double-count on retry.