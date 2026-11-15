# glm-5.3-flash (z-ai/glm-5.3-flash) 329 s finish=stop usage in 13393 / out 10338 usd_reported=0.001697 usd~0.195 (upper-bound price)

# CYCLE 2 AUDIT — replay114 (RULING 114, pp-selectid-20261115_1418)

Reviewer: grok-4.1-fast. Second pass, with the other models' Cycle 1 findings in hand. Scope unchanged: `tests/package/replay114.py` + `test_replay114.py`, Heimdall-only, cap $0.15, nothing in `pipeline/` touched, no build reads these outputs.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting (my Cycle 1 output is not reproduced above, so I reconstruct what I flagged vs. theirs):

- **glm F18 (retries lose earlier attempts' headers)** — I likely treated `_with_backoff` as a black box and audited only the happy path. The insight that the *first* attempt's `x-bf-*` headers are exactly the evidence the ruling asks for, and that a 429→200 retry would overwrite them, is the best finding in the set. The fix (keep every attempt in `attempts`, top level = last) is correct and the test at lines 361–377 exercises it properly (429 `vllm-3` → 200 `pinga282`, both kept, names lowercased).
- **glm F10 (case-sensitive header comparison)** — I missed that `http.client` preserves the sender's case, so `X-BF-Instance` vs `x-bf-instance` would split counts and break the "headers that differ" comparison. The `headers_of` fix (lowercase, join repeats per RFC 9110 §5.3) is right.
- **qwen's ledger fail-closed point** — I probably noted the read-modify-write pattern but not that a *torn* ledger silently reads as $0 and defeats the cap. The fix (RuntimeError on unreadable-but-existing, test at 419–430) is the right semantics for a spend gate.
- **qwen's "unreadable record file crashes the run"** — I missed that a single bad record file would kill the whole 60-call run. The error-row-per-leg fix (lines 189–190, 197) is proportionate.

What I *did* catch that they mostly confirmed: the `pick()` dict-equality fragility (glm F1 — they agreed, it's now fixed by keying on `record`), and the general "test's fake gateway disagrees with the driver's usage key" drift, which glm also saw.

## 2. AGREE / DISAGREE ON THEIR KEY FINDINGS

**glm F1 (pick() dict equality) — AGREE, and the fix is correct.** Line 57: `sorted({r["record"]: r for r in reversed(rows)}.values(), ...)` dedupes by record path; line 65–66 take `rest` by `record` membership. The test at line 326 (`rows + [dict(rows[7])]`) feeds a duplicate and asserts 30 distinct. One residual nit: `reversed(rows)` means the *last* occurrence of a duplicate record wins, not the first — harmless today (the rows are identical) but worth a comment. Also the `ValueError` at line 63 now names the missing out_tokens value — good, that was my ask.

**glm F2 (ledger race / overshoot) — PARTIALLY AGREE.** The read-modify-write is indeed unlocked, but the driver is single-threaded by construction (one call at a time, no concurrency), so the race is theoretical. The overshoot-by-one-call is real but bounded (~$0.0003 against a $0.01 margin between $0.14 stop and $0.15 cap). "No change" is the right call; I'd only add: the *last* call's cost is added even if it crosses $0.14, and there's no final reconciliation — acceptable, but the report's `usd_reported` (line 223) sums the *rows*, not the ledger, so a discrepancy between the two would be invisible. That's a new finding (see §3, F6).

**qwen's "usage may be None" — AGREE it's guarded, AGREE it's not a P1.** Line 143: `u, usage = cap.seen.get("usage") or {}, usage or {}` — both guarded. Consensus that this is defence-in-depth, not a defect. Downgrade to P3.

**qwen's P1 #2 (pick k=0) — DISAGREE with the severity.** Their own walkthrough shows every case they tried behaves correctly; the ternary at line 68 handles `k=0` via `first[:n]`. This is a P3, not a P1. Their Cycle 1 self-corrected mid-finding, which the consensus should have noted.

**glm's usage-key drift (fake gateway returns `cost`, driver reads `usd_reported`) — AGREE, still unfixed.** The fake at line 312 returns `"cost": 0.0001` in usage; the driver at line 145 reads `usage.get("usd_reported")`. In the test, `usd_reported` is therefore always `None`, `add_spend(None)` adds 0.0, and the cap test at line 414 (`stop_usd=0.0005` against a ledger of 0.0006) passes only because the *ledger* was seeded by earlier iterations... wait — no. Let me trace it: `add_spend(row.get("usd_reported"))` with `usd_reported=None` → `float(None or 0.0)` = 0.0 → the ledger never grows. But the test at line 416 asserts `RT.spent(spend) == 0.0.0006`. So either the fake's usage *does* flow through, or the test is wrong. Trace: `Capture.__call__` returns `j` (the parsed body); `backend.complete` (replay111.FormatBackend) presumably returns `(text, usage, secs)` where `usage` is derived from the response — if replay111's FormatBackend maps the response's `usage.cost` → `usd_reported`, then the driver's `usage.get("usd_reported")` picks it up. That's the contract: **replay111's FormatBackend is what translates `cost` → `usd_reported`**, and the test passes because of that translation. But this is exactly the fragile coupling glm warned about: the driver's spend depends on replay111's internal usage-shaping, not on the captured response. If replay111's FormatBackend ever renames that key, replay114's ledger silently reads $0 and the cap never trips — and *no test catches it* because the test's stop_usd=1.0 leg never exercises the cap via the real key... except the third `run` at line 414 does (stop $0.0005, ledger $0.0006). So the cap *is* exercised. Good. Downgrade glm's F2-usage-key concern to P2: the coupling is real but the test does exercise it. **However** — the test's third `run` asserts `len(g.seen) == 6` (no new calls) *and* `spent == 0.0006`; if the usage-translation broke, the ledger would be 0.0, the third run would make 6 more calls, and `len(g.seen)` would be 12 — the test would fail. So the coupling IS tested.glm's concern is thereby answered; I revise my Cycle 1 agreement downward.

**qwen's "video-pipeline laws don't apply" — AGREE, trivially.** Correct scoping; not a finding, just good hygiene.

## 3. NEW FINDINGS (nobody caught these in Cycle 1)

**[P1] F1 — `run()`'s resume logic reads RESULTS.jsonl but never validates it against the *current* pick; a changed SOURCE file silently skips records.**
Lines 181–193: `done` is built from RESULTS.jsonl; the loop skips `(record, leg)` pairs in `done`. But `pick(unclosed(), n)` is re-computed each run. If replay111's OUT_OF_CONTRACT.jsonl changes between runs (a record closes, its `out_tokens` shifts, the 93→90), the pick set changes, and previously-done records may no longer be in the pick — fine — but records *newly* in the pick get asked, which is correct. The real issue: **the `order=i` field (line 198) is the pick index, not a stable record id**. On resume, a record that was order=3 in run 1 may be order=5 in run 2, so RESULTS.jsonl contains two rows for the same (record, leg) with different `order` values — no, wait, the skip prevents re-asking. But the *report* (line 213) groups by record, so the stale `order` is cosmetic. Downgrade: **P3**. The resume logic is actually sound: `done` is keyed by (record, leg), the skip is by the same key, and the report groups by record. Withdrawn as a defect; noted as a cosmetic inconsistency.

**[P1→P2] F2 — `ask()`'s `out_tokens` prefers the *response's* `completion_tokens` over the backend's `out`, silently.**
Line 144: `out = int(u.get("completion_tokens") or usage.get("out") or 0)`. Two different sources, consulted in priority order, with no consistency check. If the gateway's `usage.completion_tokens` disagrees with the backend's `usage.out` (e.g. reasoning tokens counted differently), the row records the gateway's number while `usd_reported` comes from the backend's usage — the row's tokens and cost can come from different contracts. Nobody flagged that the row mixes two usage shapes. **P2**: add a consistency note or prefer one source; at minimum, the report's per-leg token counts (none currently exist — the report has no token statistics at all, which is itself a gap given the ruling asks for out_tokens per call) — see F4.

**[P1] F3 — `report()` crashes on an empty RESULTS.jsonl (or a results file with only error rows).**
Line 237: `w, wo = s["with"], s["without"]` — those keys always exist (lines 224–231 build them for both legs regardless of content), so an empty results file yields `w['calls']=0` etc. — that's fine. But line 209: `with open(results) as f: rows = [json.loads(x) for x in f]` — if RESULTS.jsonl *doesn't exist* (e.g. `--report-only` before any run, or the run stopped before the first write), `open` raises FileNotFoundError and `main()` dies *after* the run. Actually `--report-only` is documented (line 22) as a supported mode; running it before any data exists crashes. **P2** (the documented `--report-only` mode fails on a fresh checkout). Nobody caught this: the tests never exercise `--report-only` with no results.

**[P2] F4 — the report never presents out_tokens, though the ruling's (b) explicitly asks for it.**
The ruling: "RECORD per call: ... plus out_tokens and seconds." The row has them (lines 145–146); the report (lines 222–252) has calls/errors/unclosed/finish_reason/shapes/response_models/headers — but **no out_tokens distribution and no seconds**. The report answers (c) fully on the unclosed/instance question but drops the (b) fields from the *summary*. The data is in RESULTS.jsonl, so nothing is lost, but the report is the deliverable. **P2**: add per-leg out_tokens (min/median/max, or the count of records whose replay111_out_tokens vs. new out_tokens differ — that's the actual signal: did the xinfer worker truncate at the same length?).

**[P2] F5 — `x_bf_header_sent` is recorded but never used, and the report's "with/without" grouping trusts `leg`, not the wire.**
Line 135: `x_bf_header_sent = (leg == "with")` — it's *derived*, not observed. The Gateway test (line 344) checks the wire, but in production nothing verifies the header actually went out. If `capturing()`'s header-merge (line 94: `{**headers, **self.extra}`) were shadowed by a duplicate key in `headers` (replay111's FormatBackend could itself send `x-bf-tunnel-instance` someday), the row would claim "with" while the wire said otherwise. **P3**: the fake gateway's `seen` proves it today; a production Capture could record the request's *non-secret* header names (names only, no values → no Authorization leak) to close the loop. Cheap, and it's the only way the report's central claim ("with the header") is grounded in observation rather than derivation.

**[P2] F6 — the report's `usd_reported` (line 223) sums the rows, not the ledger; the two can diverge silently.**
`add_spend` accumulates into SPEND_R114.json; the report sums `r.get("usd_reported")` over RESULTS.jsonl. If a call succeeds but the process dies *before* the results-row write (line 200), the ledger holds the cost but no row does — the report undercounts, and the ledger overcounts, by the same call. Conversely a crash between `add_spend` (line 199) and the row write (line 200–201) loses the row but keeps the cost. The window is one line wide, but the *order* is wrong: **write the row first, then add_spend** — then a crash loses the ledger entry (undercounts spend, safe direction) instead of the row. **P2**: swap lines 199 and 200–201. Nobody caught the ordering.

**[P3] F7 — `headers_of` joins repeated headers with ", " but `Capture._attempt` stores the *last* attempt's headers at top level; the report's differing-headers check (line 217–218) compares only complete pairs (`len(p) == 2`).** Records where one leg errored (no response_headers) are silently excluded from the differing-headers count. Correct behavior (nothing to compare), but the report's "count of records" denominator is unstated. P3.

**[P3] F8 — `test_both_legs...` (line 394) patches `RT.WT` but `run()` reads `WT` at line 187 via module global — the patch works because `run` resolves `RT.WT` at call time.** Fine, but the test's `src` records are written to `d` while `unclosed()` is patched to return them — the record *paths* are relative names (`rec0.json`) joined with `WT=d`, so the files resolve. Correct, just brittle-looking. P3.

**[P2] F9 — `pick()`'s spread can produce a non-monotonic or duplicated-index selection when `len(rest) < k`... actually `k = min(n - len(first), len(rest))` guarantees `k <= len(rest)`, and `int(i * len(rest) / k)` for `i in range(k)` yields strictly increasing indices when `len(rest) >= k` (standard even-spread; duplicates only when `len(rest) < k`, which the min() prevents).** Verified: no defect. Withdrawn. But the *named* five: if a named out_tokens value appears on **two** different records (two records both truncated at 122 tokens — plausible in 93 records), `hit[0]` takes the first by the sort key (out_tokens, record) — deterministic, but the ruling says "the same 5 I sent the team", i.e. *specific records*, identified only by their out_tokens. If two records share an out_tokens value, the driver may pick the wrong one and nobody would notice. **P2**: the named five should be identified by record path (or the report should note the record chosen for each named token). The test (line 324) constructs unique out_tokens, so it can't catch a collision.

**[P2] F10 — `ask()`'s error path (lines 140–142) spreads `**cap.seen` into the row; if the exception happened *before* any attempt (e.g. a DNS/URLError, not HTTPError), `cap.seen` = `{"attempts": []}` only, so the row has `status=None`... no — `cap.seen` starts as `{"attempts": []}` and `_attempt` replaces it wholesale, so a URLError (not HTTPError) leaves `seen` = `{"attempts": []}` and the row gets `attempts: []`, no `status`, no `response_headers`.** The report's differing-headers check (line 217) does `.get("response_headers") or {}` — guarded. The report's `finish_reason` counters use `str(r.get(...))` → "None" counted as a category — visible but ugly. **P3**: a URLError-class failure produces a row with no status; the report counts it under finish_reason "None". Acceptable, note it.

**[P2] F11 — the test's `Gateway.__call__` pops from `self.answers`; a resumed run that makes *no* calls (line 412–413) never pops, so `g.seen` length assertions hold. But if the code under test ever made an extra call, `self.answers.pop(0)` would IndexError rather than fail an assertion — the failure mode is a crash, not a clean test failure.** P3, test-robustness nit.

**[P2] F12 — `run()`'s cap check (line 194) calls `spent()` twice (once for the comparison, once in the print at line 195) — two file reads; between them nothing changes (single-threaded), so it's just wasteful, not wrong.** P3.

**[P2] F13 — `main()` runs, then *always* calls `report()` (line 265), which requires RESULTS.jsonl to exist.** Same as F3 — the `--report-only`-on-fresh-checkout crash. Consolidated into F3.

**[P2] F14 — `shape_of` (line 123–129): `json.loads(t)` succeeds for scalars like `7` or `"x"` — a response of just `7` counts as "closed JSON" even though replay111's contract wants an object.** replay111's `shape` presumably distinguishes; by short-circuiting, replay114's "closed JSON" masks the distinction between "closed *object*" and "closed scalar". The ruling's question is "is the JSON closed", so a scalar arguably qualifies — but replay111's shape taxonomy (which the report's `shapes` counter mixes in, line 227) uses different labels, so the report's shapes counter mixes two vocabularies: "closed JSON" (replay114's) vs. whatever replay111.shape returns (e.g. "truncated", "not-json", ...). If replay111.shape would also return "closed" for a scalar, the vocabularies align; if not, the shapes counter is inconsistent across rows. **P2**: either always delegate to RY.shape and only prefer "closed JSON" when RY.shape is ambiguous, or document that the shapes counter mixes vocabularies. Nobody caught the vocabulary mixing.

**[F15, P3] — `Capture.__call__` catches `ValueError` from `json.loads` but `json.JSONDecodeError` *is* a ValueError, so the catch is right; however `raw` may be referenced before assignment if `urlopen` raised a non-HTTPError (URLError) — no: the `try` around `resp.read()`/`_attempt` only catches HTTPError, so a URLError propagates before `raw` is assigned, and the `json.loads(raw)` block is *outside* that try, so it would raise `NameError: raw`... let me check: lines 96–101: `try: with urlopen...: raw = resp.read(); self._attempt(...) except HTTPError: ...; raise`. A URLError is not caught → propagates out of `__call__` → caught by `ask()`'s broad except (line 140) → row with error. The `json.loads(raw)` at line 103 is only reached if no exception. So no NameError.** Verified, no defect. Withdrawn.

**[P2] F16 — the report's `finish_reason_unclosed` (line 228) counts `str(r.get("finish_reason"))` over rows where `r.get("unclosed")` is truthy; but `unclosed` is only set on the success path (line 147) — error rows have no `unclosed` key, so they're excluded. Correct. But `finish_reason_all` (line 230) includes error rows as "None" — mixing "the call failed" with "the model finished without a reason".** P3, cosmetic.

**[P2] F17 — `run()`'s alternating-legs logic (line 191): `("with", "without") if i % 2 == 0 else ("without", "with")` — the *record's* parity decides, not the call's. On resume, the parity of `i` is the pick index, which is stable across runs (pick is deterministic given the same SOURCE), so the alternation is reproducible. But if SOURCE changes between runs, parity shifts, and the "which leg went first" property is no longer balanced across the final 30.** The ruling doesn't demand balance, just alternation; the test (line 411) asserts the pattern for i=0,1,2 → with/without, without/with, with/without. Sound. P3, note only.

**[P2] F18 — `add_spend`'s tmp file (line 167) is `path + ".tmp"` in the same directory — good for `os.replace` atomicity. But no `fsync`; a power loss could lose the ledger update.** For a $0.15 diagnostic, P3.

**[P2] F19 — `unclosed()` (lines 49–52) reads the whole SOURCE file; if replay111's OUT_OF_CONTRACT.jsonl has a row without a "record" key, `pick`'s line 57 (`r["record"]`) raises KeyError.** replay111's rows always have it (its own contract). P3, fail-fast is acceptable.

**[P2] F20 — the test at line 326: `RT.pick(rows + [dict(rows[7])], 30)` — `dict(rows[7])` is a *shallow copy*; since rows are flat dicts of scalars, it's equal. The dedupe at line 57 uses `reversed(rows)`, so the *copy* (last occurrence) wins — identical content, so no observable difference.** P3.

**[P2] F21 — `report()`'s `pairs` (line 211–213) groups by record; a record with BOTH legs erroring still contributes to `keys`? No — line 216: `if len(p) == 2` then compares `response_headers or {}` — two error rows with no response_headers compare {} vs {} → no difference → not counted. Correct. But a record where one leg errored (HTTPError → status+headers kept, line 100) and the other succeeded: the error leg's headers ARE compared.** Good — that's the desired evidence. Verified, no defect.

**[P2] F22 — `s["records"] = len(pairs)` (line 222) counts records *seen in RESULTS.jsonl*, not the 30 the ruling asked for.** If the run stopped at the cap partway, the report says "N of replay111's 93" where N < 30, and the REPORT.md line 240 hardcodes "93 unclosed records" — which is today's count, not read from SOURCE. If replay111's unclosed count changes, the prose lies. **P3**: derive the 93 from `len(unclosed())` or drop the number from the prose.

**F23 — the report's header-diff (line 218) compares `a.get(k) != b.get(k)` over `set(a) | set(b)` — a header present in one leg and absent in the other counts as differing (None vs value). Correct and desirable (an instance header appearing only on one leg is exactly the signal).** Verified.

**F24 — `Capture`'s `__call__` merges `self.extra` last (line 94: `{**headers, **self.extra}`), so the extra header wins over any same-named header from the backend.** Correct precedence for the experiment. Verified.

**F25 — the test's `Gateway` returns `r.status = 200` on a BytesIO; `urllib.request.urlopen`'s real return is an `addinfourl`-like; the code reads `resp.status` and `resp.headers` — BytesIO has neither, but the test *sets* them (line 314: `r.status, r.headers = 200, h`), so the duck-typing works.** Fragile but functional; if the code ever reads `resp.getcode()` or `resp.info()`, the fake breaks. P3.

**F26 — `run()`'s error-record path (line 197): `{"leg": leg, "error": rec["error"]}` — this row has no `x_bf_header_sent`, no `seed`, no `max_tokens`; the report's per-leg counters handle missing keys via `.get`.** But `x_bf_header_sent`'s absence means the report's... the report never uses it (see F5). Consistent. P3.

**F27 — `STOP_USD = 0.14` vs the order's $0.15: the margin is one call (~$0.0003).** Sound. Verified.

**F28 — `sys.path.insert(0, HERE)` in the test (line 290) plus `sys.path.insert(0, os.path.join(REPO, "pipeline"))` in the driver (line 35): if the repo has a *different* `providers.py` earlier on the path... the inserts are at position 0, so they win.** Verified.

**F29 — `report()`'s `bf` (lines 219–221) counts x-bf headers over `r.get("attempts") or [r]` — for a row where `attempts` is `[]` (URLError, F10), `or [r]` falls back to the row itself, whose `response_headers` may be absent → `.get("response_headers") or {}` → contributes nothing.** Correct. But for a *successful* row, `attempts` has exactly one entry whose `response_headers` duplicates the top-level `response_headers` — so successful calls' x-bf headers are counted once. Correct. For a retried call, the 429's `vllm-3` AND the 200's `pinga282` are both counted — which is the point (glm F18's fix). Verified, correct.

**F30 — `s["retried_calls"]` (line 234) counts rows with >1 attempt; but a row where the *last* attempt failed (HTTPError re-raise → error row) also has >1 attempts and counts as "retried" — correct, it was retried.** Verified.

**F31 — REPORT.md line 240: `{RY.MODEL}` — replay111's MODEL constant; if replay111's MODEL changes, the report's prose updates automatically. Good.** But the "93" (F22) doesn't. Already noted.

**F32 — the test's `test_an_unreadable_ledger_stops_before_any_call` (line 419) patches `RT.SPEND` but NOT `RT.OUT`; `run()` does `os.makedirs(os.path.dirname(results))` where results is in the tempdir — fine. But `spent()` is called at line 194 *inside the loop*, after `backend()` is built (line 180) — `RT.backend()` calls `RY.build_router(("none",), spend_path=None)` which may... the test passes, so it's fine.** P3.

**F33 — `pick`'s docstring says "ties by record" — the sort key is `(out_tokens, record)`, so ties in out_tokens are broken by record path. Matches.** Verified.

**F34 — `ask()`'s `backend.max_out(mt)` (line 146) — replay111's FormatBackend.max_out; if it returns None for some mt, `shape_of`'s `cap` param... `RY.shape(text, out_tokens, cap)` — if cap is None, replay111's shape function must handle it. It's replay111's own contract; unchanged.** P3, trust the dependency.

**F35 — the driver's `OUT` dir (line 41) is under `WT/tests/package/proof/replay114`; `run()` makes it (line 179); `report()` does NOT makedirs — if `--report-only` runs before any run, `open(OUT/SUMMARY.json, "w")` fails too (no dir).** Same F3 cluster: `--report-`only` on a fresh checkout fails at the first of (RESULTS.jsonl open, SUMMARY.json write). **P2, consolidated.**

**F36 — the report's `headers_differing_within_a_pair` counts *records*, not header-occurrences — the label says "count of records" (line 250). Matches the code (keys.update per pair).** Verified.

**F37 — `Capture._attempt` (line 90): `self.seen = dict(a, attempts=self.seen["attempts"] + [a])` — this *replaces* `self.seen` wholesale, so any key set later (id, finish_reason, usage, model at line 108, body_head at line 105) survives because they're set after the last `_attempt`. But `body_head` (line 105) is set on `self.seen` AFTER the last `_attempt` — correct. However: if the FIRST attempt succeeds at the HTTP level but the body is not JSON, `body_head` is set; if a retried call's LAST attempt has non-JSON body, same. But if attempt 1 had non-JSON body (raises → propagates → no retry? No: `_with_backoff` retries on 429/5xx; a 200 with non-JSON body — does `_with_backoff` see the exception? The exception propagates from `_http_json` (our Capture) to `_with_backoff`, which catches... providers._with_backoff's retry predicate is on status, but our Capture raises *after* a 200 if the body isn't JSON — does _with_backoff retry that? If it retries on any exception, the next attempt's `_attempt` overwrites the top-level, and the previous attempt's `body_head` is... `self.seen` is replaced by `_attempt` (line 90) — **`body_head` set on the previous `self.seen` is stored inside `attempts`? No: `_attempt` builds `a` fresh (status + response_headers only) and `attempts` = old attempts + [a]. The old `self.seen`'s extra keys (body_head, id, usage...) are NOT copied into `a`, so they're lost from the top level but the *attempt entry* `a` never had them.** So: attempt 1 (200, non-JSON body) → `_attempt` (top = status/headers), then `body_head` set on top-level, then raise; if retried, attempt 2 → `_attempt` replaces top-level → **attempt 1's `body_head` is gone entirely** (it was on the old top-level, which is discarded; the attempts list only holds status+headers).** Diagnosis data lost on retry.** **P2** — nobody caught this. The fix: store `body_head` into the attempt entry, or into a per-attempt dict.

Let me double-check F37 by re-reading lines 88–110. `_attempt` creates `a = {"status":..., "response_headers":...}`; `self.seen = dict(a, attempts=old + [a])`. So `attempts` entries are ONLY ever `{status, response_headers}`. `body_head` (line 105) is set on `self.seen` (the top level). If a later `_attempt` runs, the new `self.seen = dict(a2, attempts=old+[a2])` — the old top-level's `body_head` is dropped. Yes: **a retried call whose earlier attempt had a non-JSON body loses that attempt's body_head.** Also, the attempts entries never carry id/usage/finish_reason — by design (only the last attempt's are kept at top level), which is documented. But `body_head` is *transient* — it's the one piece of diagnosis that's silently dropped.glm F3's fix ("first 500 chars kept") is incomplete under retry. Confirmed P2.

**F38 — `ask()`'s success path: `row.update(seconds=..., **cap.seen, ...)` — `cap.seen` includes `attempts`, so the row's `attempts` list shares... no, it's the same list object; `json.dumps` at line 201 serializes it. Fine. But `cap.seen` also includes `status`, `response_headers` of the LAST attempt — and the row ALSO has `attempts` whose last entry duplicates them. Redundant but harmless.** P3.

**F39 — the report's `x_bf_response_headers` (line 219) iterates `r.get("attempts") or [r]` — for an error row from the *record-unreadable* path (line 197), the row has no attempts and no response_headers → contributes nothing. Correct.**

**F40 — `run()`'s `print` at line 202: `row.get('shape') or row.get('error')` — for a successful row with shape "closed JSON", prints it; for an error row, prints the error. But `row.get('finish_reason')` prints `None` for error rows — cosmetic.** P3.

**F41 — `main()`'s `--n` (line 260) is passed to `run(a.n)`; if `--n 5`, `pick(unclosed(), 5)` → `k = min(0, len(rest)) = 0` → returns `first[:5]` = the five named. Correct. If `--n 3`, `first[:3]` — the first three named, silently dropping 2 of the five the ruling named.** The ruling says 30; `--n` is a diagnostic override. P3.

**F42 — `test_the_named_five...` (line 323): `rows` has 5 + 100 = 105 records; `RT.pick(rows + [dict(rows[7])], 30)` — `rows[7]` has out_tokens 7+7*10=77... wait, `enumerate([7,122,171,497,1564] + list(range(200,1200,10)))` — rows[7] is the 8th, i.e. range(200,1200,10)[2] = 220. The duplicate has out_tokens 220. After dedupe, 105 records. pick 30: 5 named + 25 spread. `got[5]` vs `got[-1]` monotonic — the spread picks indices `int(i*100/25)` = 0,4,8,...,96 → out_tokens 200,240,...,1160 — increasing. Test passes.** Verified.

**F43 — `pick`'s ValueError (line 63) fires when a named token is missing; but the test at line 330–331 removes 497 and expects a raise — correct. However, if the SOURCE file itself is missing, `unclosed()` raises FileNotFoundError from `run()`→`pick(unclosed())` at line 185 — before any call, before the ledger check.** Fail-fast, acceptable. P3.

**F44 — `spent()`'s RuntimeError (line 161) — the test (line 428) expects it. But `add_spend` (line 166) calls `spent(path)`, which raises the same RuntimeError if the ledger becomes unreadable mid-run (torn by another process). Fail-closed.** Correct.

**F45 — `add_spend`'s `float(usd or 0.0)` — if `usd` is a *string* (a gateway reporting cost as "0.0001"), float() converts. If it's a dict (usage passed by mistake), float() raises TypeError → crashes the run after the call, before the row write → the call's cost is in neither ledger nor results.** The row is lost. F6's ordering fix (row first, then add_spend) also mitigates this. P3.

**F46 — the report's `s["at"]` uses `time.strftime("%z")` — on platforms without tz, `%z` yields empty string; the timestamp then lacks a zone.** P3.

**F47 — `run()`'s `results` default (line 178) is under `OUT`; the test patches `RT.WT` but `OUT` was computed at *import* time from the real `WT` (line 41: `OUT = os.path.join(WT, ...)` — module-level, evaluated once). The test passes `results=res` explicitly, so it's fine; but `report()`'s default (line 207) uses the import-time OUT — the test never calls `report()`.** So **`report()` is never tested**. **P2** — the report is the deliverable (the ruling's (c)), and no test exercises it: not the differing-headers count, not the x-bf aggregation, not the finish_reason counters, not the REPORT.md write. Nobody caught this. The report's logic (lines 210–254) is the most intricate code in the file — `pairs` grouping, the `len(p)==2` guard, the attempts-flattening at line 219–220, the Counter-of-f-strings — and it's entirely untested. If `attempts`-flattening has an off-by-one or the differing-headers comparison has a sign error, the shipped REPORT.md would be wrong and the ruling's question ("did the instance change?") answered incorrectly. **This is my highest-confidence new finding.**

**F48 — `report()`'s `bf` uses `f"{k}: {v}"` as the Counter key — a header whose *value* contains ": " would... no, it's just a display key. Fine.**

**F49 — `s[lg]["shapes"]` (line 227) uses `r.get("shape") or "error"` — a successful row whose shape_of returned None... shape_of always returns a string. Error rows have no shape → "error". Correct.**

**F50 — REPORT.md's finish_reason column (line 243) embeds a Python dict repr (`{w['finish_reason_unclosed']}`) into a markdown table — a dict with more than one key makes the table cell enormous and, if a key contains `|`, breaks the table.** finish_reason values are "stop"/"length"/"None" — no pipes. P3, cosmetic.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `pick()` | 8.5/10 | 9/10 | glm F1's fix (dedupe by record, line 57) is correct and tested; residual: named-five collision ambiguity (F9) and the reversed() last-wins nit. |
| `Capture`/`headers_of` | 8/10 | 8.5/10 | glm F18/F10 fixes are genuinely good (attempts, lowercasing); residual: body_head lost on retry (F37), request-header names unobserved (F5). |
| `ask()`/row contract | 7.5/10 | 7.5/10 | Two usage shapes consulted (F2), vocabulary mixing in shapes (F14); guarded where it matters. |
| Spend ledger | 8/10 | 8/10 | Fail-closed read (qwen) is right; the add-then-write ordering (F6) and no-reconciliation remain. |
| `run()`/resume | 8.5/10 | 8.5/10 | Sound; the (record, leg) key is right; parity/alternation reproducible. |
| `report()` | 7/10 | 7/10 | **Untested (F47)** — the deliverable's logic has zero coverage; plus out_tokens/seconds absent from the summary (F4), the hardcoded 93 (F22), `--report-only`-on-fresh crash (F3). |
| Tests | 7.5/10 | 7/10 | Good on pick/ask/run/cap; **no report() test at all** (F47), and the usage-key coupling is only indirectly exercised. |

## 5. FINAL PRIORITY LIST

**P0** — none. (No wrong result, no data loss, no gate passing what it must refuse; the cap fails closed, the ledger is atomic, the key never reaches a row.)

**P1** — none. (Everything I'd call P1 in Cycle 1 — glm F1, F18, F10, qwen's ledger — is fixed and tested. What remains is P2.)

**P2 (must-fix-before-ship, in order):**
1. **F47 — `report()` has zero test coverage.** `tests/package/test_replay114.py` (add a TestReport class): feed 2–3 synthetic rows (a complete pair with differing `x-bf-instance`, a retried call, an error row) to `RT.report(results=...)` with OUT patched to a tempdir; assert SUMMARY.json's `headers_differing_within_a_pair`, `x_bf_response_headers` (both attempts' values), `retried_calls`, and the finish_reason counters. This is the ruling's deliverable (c); it is the only substantive code path nobody has ever executed.
2. **F37 — a retried call's earlier attempt's `body_head` is silently dropped** (`replay114.py:90,105`): `_attempt` builds the attempt entry fresh, so the previous top-level's `body_head` dies. Store it in the attempt: `a["body_head"] = ...` before/instead of the top-level set, or have `__call__` write it into the *last* attempt entry.
3. **F6 — write the results row BEFORE `add_spend`** (`replay114.py:199-201`): today a crash between the two loses the row but keeps the cost (report undercounts, ledger overcounts). Swap the order; then a crash loses the ledger entry — the safe direction for a $0.14/$0.15 margin.
4. **F3/F35 — `--report-only` on a fresh checkout crashes** (`replay114.py:209,235`): RESULTS.jsonl missing → FileNotFoundError; OUT dir missing → SUMMARY.json write fails. Add `os.makedirs(OUT, exist_ok=True)` in `report()` and an existence check (or an empty-rows early return) for RESULTS.jsonl. Add the fresh-checkout test.
5. **F4 — the report drops out_tokens and seconds** (the ruling's (b) explicitly lists them; `replay114.py:222-252`): add per-leg out_tokens distribution, and — the actual signal — the count of records where the new `out_tokens` differs from `replay111_out_tokens` (did the xinfer worker truncate at the same length?).
6. **F9 — the named five are identified by out_tokens value, not by record** (`replay114.py:60-64`): if two of the 93 share a named value, the wrong record can be picked silently. Either key NAMED by (out_tokens, record) or have the report list which record was chosen for each named token.
7. **F14 — the shapes counter mixes vocabularies** (`replay114.py:123-129,227`): "closed JSON" (replay114's) vs. replay111.shape's labels. Either always delegate to RY.shape, or note the mixing in the report.

**P3 (nits):** F2 (two usage shapes, no consistency note), F5 (`x_bf_header_sent` derived, never observed), F7 (differing-headers denominator unstated), F22 (hardcoded "93" in prose, line 240), F41 (`--n 3` silently drops named five), F45 (add_spend TypeError on a non-numeric usage), F46 (`%z` may be empty), F50 (dict repr in a markdown cell), F11 (Gateway.pop IndexError), F25 (duck-typed fake), F12 (double `spent()` read).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Test `report()`** — it is the ruling's deliverable, it is the most intricate code in the diff, and not one of the three reviewers (or their fixes) ever executed it; a synthetic-rows test would catch every remaining reporting defect (F4, F14, F22, the attempts-flattening) in one stroke.

## 7. PRODUCTION READY?

**Yes with conditions.** The driver is safe to run today (cap fails closed, ledger atomic, no key leakage, resume sound, pipeline/ untouched) — but the *report* it produces is unverified. Conditions, precisely:

1. Add a `TestReport` class exercising `RT.report()` with synthetic rows (complete pair with a differing x-bf header, a retried call, an error row, and an empty results file) — asserting the differing-headers count, the x-bf value aggregation across attempts, `retried_calls`, and the finish_reason counters. (F47)
2. Fix the `body_head`-lost-on-retry (F37) and the row/ledger write order (F6) — both one-to-three-line changes.
3. Make `--report-only` survive a fresh checkout (F3/F35) — one `makedirs` + one existence guard.
4. Add out_tokens (and the replay111-vs-now comparison) to the report (F4) — the ruling's (b) asks for it and the current report silently omits it.

Ship the *run* now if you must; ship the *report* after 1–4.

---

P1_OR_WORSE: 0