# heimdall_glm (z-ai/glm-5.3-flash, 314.8 s, $0.005, finish stop)

# FORENSIC CODE REVIEW — pp-ingest, ruling 92 change (mine-hook/2)

Scope note: the review focuses on the diff (mine.py, tools/ingest_watch.py) but verifies it against the whole package, since the diff's correctness depends on the surrounding machinery (ledger, service, contract).

---

## SECTION 1: CORRECTNESS

### 1.1 The main flow, step by step

Hook pass flow: `service.hook_once` (service.py:396) → `hook_due` (queue.py:178) → `hook_video` (service.py:337) → `mine.mine_video(kind="hook")` (mine.py:439) → `build_line(..., episode)` (mine.py:486-487) → duration/opener filter (mine.py:490-503) → `service._append` (service.py:277) → `ledger.append` (ledger.py:34).

**Verified correct:**

- `episode_measure` (mine.py:238-250) counts both marker forms: `TURN_MARK = re.compile(r">>|&gt;&gt;")` (mine.py:235) matches raw `>>` and the HTML-escaped `&gt;&gt;` that YouTube manual captions actually contain. `contract.SPEAKER_MARKERS = (">>", "&gt;&gt;")` (contract.py:23) uses the same pair, and `turn_change_inside` (contract.py:129-135) matches by `str.startswith` — so a segment text `&gt;&gt;` counts once in the episode measure and once as a turn inside a span. Consistent.
- Minutes: `float(segs[-1].get("end") or 0) - float(segs[0].get("start") or 0)` (mine.py:245). For a caption record whose first segment starts at 0 this is the record's duration. The `try/except (TypeError, ValueError)` (mine.py:246-247) covers a segment with a non-numeric `end`. Note the subtlety: if `segs[-1]["end"]` is `None`, `or 0` yields 0 and minutes becomes 0.0 → `turns_per_min` None, `unmarked` still reflects markers. Fail-soft, not fail-closed, but this field is informational (see 1.4).
- `unmarked: n == 0` (mine.py:249) — matches the ruling's "one speaker throughout = solo" only as "unknown, not solo", which the docstring states correctly (mine.py:241-242). Honest.
- The `episode` field is added to every line, moment and hook (mine.py:435), computed once per video in `mine_video` (mine.py:465) and passed down (mine.py:487). `build_line`'s fallback `episode if episode is not None else episode_measure(rec)` (mine.py:435) keeps the function usable standalone. Since `episode_measure` always returns a dict (never None), the fallback is dead in the service path but harmless.
- Adding a field to a pp.moment/1 line: `ledger.line_problems` (ledger.py:88-112) checks only REQUIRED keys (ledger.py:28-31); extra fields are permitted by the contract ("fields may be added", design §5). `carry_forward` (ledger.py:187-209) copies risk/flags/role_hint/risk_checks but **not** `episode` — however, since the new line is built by `build_line` which always sets `episode` itself, nothing is lost. Verified: no path appends a line without `episode` (both `mine_video` kinds go through `build_line`).
- The `--rerun` UPDATE (ingest_watch.py:157-160): sets `hook_ts=NULL, hook_tries=0, hook_next_ts=NULL` so `hook_due` (queue.py:182-184, `hook_ts IS NULL AND COALESCE(hook_next_ts,0) <= now AND published_ts >= now-horizon`) picks the rows again. The guard `(hook_note IS NULL OR hook_note <> 're-run: mine-hook/2')` makes it idempotent — a second `--rerun` with the same version is a no-op. Correct, and the printed count matches `rowcount`.
- The rerun's window: `published_ts >= max(since, q.clock() - 12*3600)` (ingest_watch.py:159) — clamps `--hours` beyond 12 to the 12 h expiry horizon, consistent with `HOOK_HORIZON_S = EXPIRY_H*3600` (service.py:52) and the adapter's expiry. Good.

**Issues found:**

**C1. `bad_opener` runs on the *spoken* text, but the builder's rule reads canon tokens of the same text — the `>>`-prefix case.** `build_line` sets `text = E.spoken(toks[w0:w1+1])` (mine.py:419). `eligibility.spoken` decodes entities and joins split tokens; whether a leading `>>`/`&gt;&gt;` marker survives into the spoken text depends on `eligibility.spoken`/`transcript_store.read_text`, which are not in this diff. If spoken text retains a leading `>>` (the marker *starts* the span's first token — note `turn_change_inside` deliberately skips the first token, contract.py:132, implying the first token can be a marker), then `canon.canon_tokens(">> Bitcoin...")` — again, depends on canon, not shown — could yield `">>"` or `""` as the first token, which is in neither OPENER set, so `bad_opener` returns None and the hook passes. Conversely if canon strips it, fine. Either way the *filter* cannot mis-fire on the sets themselves, but the correctness of "first word" hinges on two modules (canon, eligibility) whose behavior is not verifiable from this diff. The prompt's own claim (mine.py:171-173) is that the miner never writes such a hook; the filter is a second net. **Verdict: probably correct, unverifiable from the provided code.** This is exactly what question 1 asks; the honest answer is "the sets are right, the tokenization boundary is not provable here."

**C2. `bad_opener` returns "empty" when the text has no canon tokens (mine.py:227) — a hook row with, say, only punctuation/emoji text is dropped with reason "empty", which also fails the `why.startswith("outside")` test (mine.py:499-500) so it is not added to `dropped_s`.** That is intended (the `dropped_s` list is documented as "the lengths dropped", mine.py:500), and the previous code had the same asymmetry for "duration not measured". Consistent. But note: previously a hook with unmeasurable duration was dropped; now a hook with unmeasurable duration *and* a bad opener is counted once under the opener reason (short-circuit `or`, mine.py:495-496) — the duration defect is invisible in the report. Minor reporting blindness, not a correctness bug.

**C3. `episode_measure` counts markers, not turns.** A segment `">> Alice: ..."` contributes 1; a conversation with 40 turn changes yields `speaker_markers: 40`. The ruling says "an episode whose caption turn structure shows two or more speakers" — 40 markers ⇒ ≥2 speakers, so the measure is *sufficient* for the ruling's purpose, and `unmarked` correctly means "cannot tell". But a *single* marker (n=1) also proves two speakers, and the field exposes only the raw count, so a consumer must know `n>=1 ⇒ conversational`. The ruling's "plus the visual check's layout" is not implemented — the design says the miner cannot see layout, and the change notes say the 16 Bitcoin Magazine rows died on a *channel-level* layout rule. So `episode` answers the turn-structure half of ruling 92 only. That matches the stated scope ("the measure ruling 92 names"), but a reviewer should note the ruling is only partially satisfied by this field — the layout half lives elsewhere (the builder's step A).

**C4. Race: `--rerun` while the hook loop is mid-flight.** `cmd_hooks --rerun` (ingest_watch.py:157) runs in a *separate process* from the watcher, both writing the same SQLite via `Queue.x` (queue.py:92-94, one connection, RLock — but the lock is per-Queue-instance, so cross-process it's just SQLite's own locking; `isolation_level=None` = autocommit, each UPDATE is its own transaction). Meanwhile `hook_video` (service.py:337) may be running for a video whose row was just reset: it will finish, `set_hook(hook_ts=...)` (service.py:378) — overwriting the reset. Result: that one video's re-run is lost until the next `--rerun` with a new version. Benign, self-healing, worth one line in the docstring. Also: `hook_video` reads `v` (the row) *before* the reset in the worst interleaving, so `hook_tries` it writes (service.py:378, `hook_tries=tries` computed from the stale `v["hook_tries"]`) could resurrect an old tries count — but since `hook_ts` is then set, the row is done. No corruption.

**C5. `hook_note` sentinel equality.** The rerun guard compares `hook_note <> 're-run: mine-hook/2'` (ingest_watch.py:158-160). But `hook_video`'s failure paths *overwrite* `hook_note` (service.py:372-374, 385-389) — e.g. "OUTAGE: 2 window(s) failed; retry in 10 min: ...". After a failed re-run pass, `hook_note` no longer equals the sentinel, so a *second* `--rerun` (same version) would reset those videos again. That's arguably desirable (retry the failed ones), but it breaks the documented "once per prompt version" (ingest_watch.py:225). Documentation/behavior mismatch, minor.

**C6. `hook_due`'s `published_ts >= now - horizon` (queue.py:184) vs. the rerun's clamp — consistent (both 12 h). But `hook_due` also requires `state IN (MINED, MINED_PARTIAL)`; the rerun resets only rows already in those states (ingest_watch.py:158), so a video that mined *after* the rerun is picked up naturally. Good.

**C7. N+1: none introduced.** `cmd_hooks`'s report (ingest_watch.py:162-167) is one query; the rerun is one UPDATE. `episode_measure` is computed once per video (mine.py:465), not per line — the earlier design (per-`build_line` fallback, mine.py:435) would have been O(lines × segments); the actual call passes the precomputed value. Good.

**C8. Edge: record with zero segments.** `episode_measure` → `segs=[]` → `n=0`, `mins=0.0`, `unmarked=True` (mine.py:243-249). But `contract.sentences(rec)` would already have failed earlier for an empty record, so this is unreachable in the service path. Defensive, fine.

**C9. Edge: `segs[0].get("start")` when the first segment's `start` is None.** `float(None or 0)` = 0.0 — so minutes = last_end/60, overstating duration if the record genuinely starts late. For caption records `start` is always present (the store's contract), so theoretical. The `except` clause catches only TypeError/ValueError, which `float(0)` cannot raise — the try/except (mine.py:246-247) is actually dead code for the `or 0`-guarded forms. Cosmetic.

**C10. The dropped-`dropped_s` change (mine.py:499-500).** Previously *every* dropped hook appended its duration to `dropped_s`; now only "outside" reasons. Since `dropped_s` is documented as "the lengths dropped" for the duration audit, this is a fix, not a regression — previously "duration not measured" appended `None` to a list of floats. Improvement. (Verify: old code `report.setdefault("dropped_s", []).append(d)` ran for every `why`, including `None` durations → `d` is None → appended None. Yes, the diff fixes a latent None-in-floats bug.)

**C11. Prompt-version cache interaction.** `HOOK_PROMPT_VERSION` bumped to "mine-hook/2" (mine.py:126) but the *prompt text* also changed. The reply cache key (providers.py:776-778) is `sha256([bid, model, sha256(prompt), schema, max_tokens])` — it does **not** include the prompt version. Since the prompt text changed, the key changes, so old mine-hook/1 cached replies are naturally missed. Correct. But note: if someone later edits the prompt *without* bumping the version, stale replies are still missed (key = prompt hash) — the version is documentation, not correctness. Fine.

**C12. `mine_window` for kind="hook" uses `schema(k["key"], k["max_count"])` (mine.py:397) — `count` enum 1..3 for hooks. The validator (mine.py:329, 355) independently enforces 1..`max_count`. Consistent with the test `test_the_hook_reply_is_strict[{"hooks": [C4]}-count 4 is not 1-3]`. Good.

### 1.2 Silent failures

- `report["dropped"]` counts (mine.py:497-498) — surfaced in `hook_video`'s log line (service.py:367-369, `dropped {rep['dropped'] or 0}`). Note `rep['dropped'] or 0` prints `{}` as `0` — cosmetic.
- `hook_note` truncation to 300 (service.py:352, 389) — fine.
- The rerun prints `n` but does not distinguish "0 because already re-run" from "0 because nothing in window" — the sentinel makes the former invisible. Minor.

### 1.3 Concurrency

- Hook windows executor: `HOOK_WINDOWS=4` (service.py:54) shared across hook passes; moment passes use `self.executor` (20 workers, service.py:96). Separate pools — the comment (service.py:54-55) explains why. The back-end semaphores (providers.py:679) still bound the total. Verified: `mine_video` submits to whichever executor it's given (mine.py:455); the hook pass's 4 + moment's 20 = 24 threads, but the *global* `gsem` (providers.py:681, 20) bounds actual in-flight model calls. Heimdall's own cap 12 (providers.json:24) + glm 8 + muse 4 = 24 ≥ 20. OK.
- `episode` computed on the calling thread (mine.py:465) before any future resolves — no shared-state issue; `rec` is read-only.

### 1.4 Does the episode field break any reader?

`ledger.read` → `line_problems` (ledger.py:88): extra key ignored. `best_unused_moments` (ledger.py:331-366): never touches `episode`. `carry_forward` (ledger.py:187): doesn't copy it, but the new line always has its own. `flagcheck`/`ab`/`coverage`/`stats`: don't read it. The packager (pp-selectid, external) reads the ledger — the contract allows added fields (design §5: "fields may be added"). **No break.** The one caveat: `stats.live`'s `moments` count and the adapter's `latest`-line-wins (ledger.py:314-317) mean a *re-logged* line (hook pass re-appending the same moment_id, service.py:277→285) replaces the moment line as "latest" — and the hook line's `mined.pass` is "hook", `role_hint: "hook"`. The adapter returns it with `role_hint` — that's by design (ruling 80: "the adapter returns the latest line, which must never lose a flag", design §13). But note the *moment* pass's `mined.at` is earlier; the ledger's mined.at ordering (ledger.py:122-128) relies on the append stamp — `service._append` stamps under the lock (service.py:286, `stamp=config.iso`), so ordering holds. OK.

---

## SECTION 2: LAW COMPLIANCE

- **L-x (no single model):** untouched by the diff; `hook` role chain = heimdall_qwen27b, local_gemma (providers.json:83) — two back-ends. COMPLIANT. (Note: under the freeze, `local_gemma` is `enabled: false` (providers.json:13) and requires the GPU0 lease this process never holds (providers.py:461-465) — so *effectively one* callable miner, which the design acknowledges and the service warns about (service.py:645-648). PARTIAL by design, documented, integrator's act. Not a diff issue.)
- **L-l (reply counts only whole; nothing repaired):** the new filter *drops* rows, it does not repair them (mine.py:490-503); the validator is unchanged and strict (mine.py:329-381). COMPLIANT.
- **L-j / L-m (fail closed; nothing measured is never a pass):** `unmarked: n == 0` is "unknown, not solo" (mine.py:241-242, 249) — correct. `bad_opener` returns "empty" when no tokens (mine.py:226-227) → row dropped, not passed. `turns_per_min: None` when mins==0 (mine.py:249) — None, not 0. COMPLIANT. One nuance: `episode_measure`'s `except (TypeError, ValueError): mins = 0.0` (mine.py:246-247) turns an *unmeasurable* duration into 0.0 + `turns_per_min: None` — the None carries the "not measured" signal. Acceptable.
- **L-h / L-k (read as spoken; records never rewritten):** `bad_opener` reads `l["text"]` which is `E.spoken(...)` (mine.py:419) — the canonical spoken form. The ledger line is never rewritten; the filter happens *before* append. `episode_measure` reads `rec["segments"][*]["text"]` raw (mine.py:243) — the *stored* caption text, not spoken; that's the right source for marker counting (the markers are the signal, and `read_text`/`spoken` may decode `&gt;&gt;`→`>>`, which is why the regex keeps both forms, mine.py:235). COMPLIANT.
- **L-u (hard exclusions):** unchanged; the hook row carries the same flags (mine.py:425, 433) and the adapter's exclusions (ledger.py:347-354) are untouched by the diff. COMPLIANT.
- **L-v (speaker change; re-uploads):** `turn_change_inside` unchanged (contract.py:129); the episode measure is *additive* — it does not feed any exclusion. COMPLIANT.
- **L-q (moments first):** the hook pass remains a second question over the same windows, after the moment pass (service.py:403, `hook_due` requires MINED/MINED_PARTIAL). COMPLIANT.
- **L-e (word timing at cut time):** unchanged; `timing: "segment"`, `duration_estimate_s` (mine.py:421-422); the 4-14 s filter uses the estimate — documented since ruling 80. COMPLIANT (pre-existing).
- **L-r (no GPU):** untouched; the hook pass uses the same router; `local_gemma` still gated on `gpu0.held()` (providers.py:461-465). COMPLIANT.
- **L-w, L-v2 (publish time):** `episode` adds no time semantics. N/A.
- **Ruling 92 (the change itself):** "the hook pass should favour conversations... (role_hint stays 'hook')" — the prompt now states the conversation preference (mine.py:175-176) and the episode measure rides on every row (mine.py:435). The *filter* added is the OPENER rule (ruling-80-adjacent, from the builder's evidence), not a conversation filter — the change does not *enforce* conversation, it *informs*. That matches "favour", and the change notes say the orchestrator chose not to build more. PARTIAL→COMPLIANT as specified; the conversation *preference* is prompt-only (the miner may still return solo-episode hooks, and nothing downstream prefers conversational ones). If the orchestrator expected the *pool* to become conversation-heavy, only the prompt's persuasion + the builder's own step-A layout rule deliver that. Worth flagging: **the enforcement of "favour" is entirely in the prompt** — measured, not guaranteed. That is the honest reading of "favour", but a reviewer must say it.

---

## SECTION 3: SECURITY

- **SQL injection:** the rerun UPDATE (ingest_watch.py:157-160) is fully parameterized; the only interpolation is `?`-counted. `mine.HOOK_PROMPT_VERSION` goes into a *value*, not SQL. `Queue.set_hook`/`set_state` build column lists from fixed whitelists (queue.py:63-66, 69-70, 155-158, 186-191). COMPLIANT. `f"UPDATE videos SET {cols}"` (queue.py:190) — `cols` from `dict(HOOK_COLUMNS)` keys, fixed. Safe.
- **Secrets:** no new secrets; the diff adds none. Existing: keys via `Keyring` (providers.py:147-187), redaction (providers.py:180-187, 208-214, 820-822). The rerun prints only counts. COMPLIANT.
- **Prompt injection:** the hook prompt's `<sentences>` block is guarded (mine.py:194-196) and `_untrusted` (mine.py:291-294) neutralizes `</sentences>`-closing `<`. The new interpolated sets (mine.py:209-213) are code constants, not data. The `episode`/`bad_opener` paths never round-trip model output into code. COMPLIANT.
- **Unvalidated input:** `--hours` (float) → arithmetic only; `--rerun` boolean. `cmd_hooks`'s `max(since, q.clock() - 12*3600)` (ingest_watch.py:159) — if `a.hours` is negative, `since` is in the future, the clamp fixes the *published_ts* bound but the *report* query (ingest_watch.py:164) still uses the unclamped `since` → prints nothing. Cosmetic. NoFS/shell exposure in the diff. COMPLIANT.
- **Rate limiting:** the hook pass shares the router's throttle/health (providers.py:609-637, 542-607); `HOOK_WINDOWS=4` + moment 20 bounded by `gsem`=20 (providers.py:681) and Heimdall's 12. The rerun does not add concurrency (the loop does the work). COMPLIANT.

---

## SECTION 4: FRONTEND QUALITY

No UI in this diff. The "frontend" here is the CLI report `cmd_hooks` (ingest_watch.py:162-171) and the STATE/coverage docs.

- `cmd_hooks` prints a summary + per-video lines; the rerun prints its count *before* the report, so the operator sees both. Good.
- The report's `hook_note` for a waiting video shows the note verbatim (ingest_watch.py:170) — after a failed re-run pass the note is the *failure* note, not the "re-run: mine-hook/2" sentinel, so the operator cannot tell from `hooks` output whether a video is awaiting its *first* mine-hook/2 pass or a *retry*. Minor observability gap (ties to C5).
- `--hours` default 12.0 (ingest_watch.py:223) matches the ruling's window; the help text (ingest_watch.py:224-225) documents the once-per-version semantics that C5 shows is approximate. Documentation slightly ahead of behavior.
- No loading/error/empty states to speak of — it's a synchronous CLI; errors propagate as tracebacks (no try/except in `cmd_hooks`). For an operator tool, acceptable; a crashed `--rerun` (e.g. locked DB) exits non-zero with a traceback. Adequate, not world-class.

---

## SECTION 5: BACKEND QUALITY

- **DB writes:** the rerun UPDATE is a single autocommit statement (queue.py:77, `isolation_level=None`) — atomic. `set_hook` (queue.py:186-191) likewise. No multi-statement transaction needed. The *service's* ledger append is the durability-critical write and is unchanged (fsync + flock + torn-tail seal, ledger.py:34-85). Good.
- **External calls:** the hook pass inherits the router's timeout/backoff/breaker (providers.py:311-326, 609-637, 542-607); a failed window → `hook_next_ts` retry (service.py:371-375), outage uses no try (service.py:365-366, `rejected` vs `failed`). Verified: `tries` increments only on rejected (service.py:366), matching the moment pass's semantics (service.py:298-299). COMPLIANT with the design's B2 rule.
- **Crash safety:** `hook_video`'s finally (service.py:392-394) discards from `hook_inflight`; the `RuntimeError`-on-shutdown path (service.py:410-413) un-marks the video. A crash *inside* `hook_video` after `_append` but before `set_hook` (service.py:377-378) → the rows are in the ledger, `hook_ts` unset → the next pass re-asks; cached replies make it free (providers.py:780-795) and `carry_forward` (ledger.py:187) prevents flag loss. Idempotent. Good.
- **Memory:** `episode_measure` iterates segments once, builds one small dict (mine.py:243-250). `TURN_MARK.findall` per segment — O(total caption text) once per video, not per line. Fine. `cmd_hooks --rerun`'s UPDATE touches only the 12 h window's rows (indexed by `videos_hook` on (state, published_ts), queue.py:90). Good.
- **Logging:** `hook_video` logs the dropped counts (service.py:367-369) — the new opener reasons appear in `rep['dropped']`'s dict, so the operator sees e.g. `{"opens on a conjunction (the builder's OPENER rule)": 3}`. Good. The rerun logs nothing to the event log (no `q.event("hooks_rerun", ...)`) — the only record is the `hook_note` sentinel. For a production audit trail, an event row would be better. Minor.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**Genuinely excellent (say so):**
- The torn-tail/append/fsync/flock discipline in ledger.py:34-85 and the mined.at-ordering argument (ledger.py:122-128) with a *test* for the out-of-order margin (test_ledger_coverage.py) is production-grade.
- The fail-closed posture is consistent and *tested*: unmeasured ≠ pass everywhere (spend, coverage, flagcheck, expiry, opener).
- The reply cache keyed on prompt+schema+model+max_tokens (providers.py:776-778) making retries and the rerun free is the right design and the reason the rerun is cheap.
- The diff's own hygiene: the `dropped_s`-None fix (mine.py:499-500) shows someone actually read the audit.

**Material gaps (no padding):**

1. **The conversation preference is unenforced and unmeasured.** Ruling 92's *point* was "CONVERSATION, NOT REACTION". The change adds a prompt sentence and a measurement field, but nothing (a) prefers conversational rows in the adapter's ranking (`rank_score`, mine.py:384-390, ignores `episode`), nor (b) reports the hook pool's solo-vs-conversation split. After a week of mine-hook/2, nobody can answer "did the 12 h pool's hooks become conversational?" without a manual grep. One line in `stats.live` (a `hook_rows` breakdown by `episode.unmarked` / `turns_per_min` threshold) would close the loop the ruling opened. This is the highest-leverage missing piece.
2. **`rank_score` ignores the episode measure it now carries** (mine.py:384-390). The adapter orders by it (ledger.py:368). If the ruling's intent is that conversational openers are *better*, the score is where that belief becomes operational. Even a +1 bonus for `turns_per_min >= 1` would be a defensible, measured, reversible step. (The change notes say "not built: more candidates or a spotlight question" — ranking isn't in that list, so this is a fair ask.)
3. **`bad_opener`'s "empty" reason is indistinguishable from a data defect in the report.** When a hook's spoken text yields no canon token, that's usually a caption-parsing anomaly worth surfacing distinctly (it would hint at a `spoken`/`canon` divergence — exactly question 1's risk). A dedicated `dropped["empty opener"]` vs. the generic reason costs nothing. (mine.py:226-227, 495-498.)
4. **No event row for `--rerun`** (ingest_watch.py:157-161). Every other state change is an `events` row (queue.py:102-105); this one is only a print + a note sentinel. In a 3 a.m. incident ("why did these 22 videos re-mine hooks?") the event log is the first place one looks.

---

## SECTION 7: SCORES

- Backend logic: 88/100 (the diff is small and correct; C1's unverifiable tokenization boundary and C5's sentinel fragility are the deductions)
- Frontend/UI: 78/100 (CLI-only; adequate, no error handling, note-visibility gap)
- Error handling: 90/100 (fail-closed consistently; the short-circuit `or` hides the second defect reason; rerun not event-logged)
- Security: 92/100 (parameterized, redacted, prompt-guarded; nothing new to attack)
- Performance: 90/100 (episode computed once per video; indexed rerun; no N+1 introduced)
- Law compliance: 93/100 (all laws held; ruling 92's "favour" is prompt-only persuasion, honestly documented)
- World-class gap: 80/100 (the measurement exists but nothing consumes it; no feedback loop proving the ruling worked)
- **OVERALL: 87/100**

---

## SECTION 8: PRIORITY ACTION PLAN

P1 HIGH | Add the ruling-92 feedback loop: report the hook pool's conversation split (count of hook rows by `episode.unmarked` / `turns_per_min` bucket) in `stats.live`'s `hooks_12h` | stats.py:108-113 | Without it, neither the orchestrator nor the builder can ever verify ruling 92 did anything; the change is currently unfalsifiable.

P1 HIGH | Consider an episode term in `rank_score` (e.g. bonus when `turns_per_min` ≥ 1) or document why ranking deliberately ignores it | mine.py:384-390, ledger.py:368 | The adapter's ordering is the only lever that actually "favours" conversations; right now the ruling's preference lives only in prompt persuasion.

P2 MEDIUM | Log an event row on `--rerun` (`q.event("hooks_rerun", ...)` with version and count) | tools/ingest_watch.py:157-161 | Every other state change is in `events`; this one is invisible in the incident-forensics path.

P2 MEDIUM | Fix the "once per prompt version" claim: either re-stamp the sentinel after a failed re-run pass, or amend the help text | tools/ingest_watch.py:158-160, 224-225; service.py:372-374 | `hook_video`'s failure paths overwrite `hook_note`, so a second `--rerun` re-queues failed videos — surprising, and the doc promises otherwise.

P2 MEDIUM | Make the "empty" opener reason distinct in `report["dropped"]` (it currently shares the short-circuit with duration) | mine.py:226-227, 495-496 | An empty spoken→canon tokenization is the exact symptom of the question-1 risk (spoken/canon divergence); today it is invisible.

P3 LOW | Dead try/except: `float(x or 0)` cannot raise TypeError/ValueError; either drop the guard or guard the un-`or`-ed floats | mine.py:244-247 | Misleading to readers; suggests a protection that isn't there.

P3 LOW | `rep['dropped'] or 0` prints `{}` as `0`; print the dict or its length | service.py:368 | Cosmetic; the empty dict is informative (nothing dropped).

P3 LOW | Clamp the report query's `since` in `cmd_hooks` the same way the rerun clamps it | tools/ingest_watch.py:159, 164 | `--hours 48` reports nothing while the rerun acts on 12 h; confusing.

---

## SECTION 9: THE ONE THING

Wire the episode measure you now record into something that *answers* ruling 92 — a conversation-split line in `hooks_12h` (and, ideally, a rank bonus) — because a measurement nobody aggregates is a field, not a feedback loop, and the ruling's whole premise ("conversation, not reaction") is currently unverifiable.

---

## SECTION 10: FINAL VERDICT

Ready for production. The diff is small, additive, fail-closed, and its one latent bug (the `dropped_s` None) is fixed; the ledger, flags, adapter, and every gate are untouched in the ways the change claims. Before or shortly after merge: add the ruling-92 feedback metric (P1) and reconcile the `--rerun` sentinel semantics with its documented "once per version" (P2) — neither blocks, but the first is what makes the change more than prompt-editing.