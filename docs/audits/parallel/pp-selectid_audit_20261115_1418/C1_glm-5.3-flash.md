# glm-5.3-flash (z-ai/glm-5.3-flash) 258 s finish=stop usage in 11543 / out 6846 usd_reported=0.001207 usd~0.137 (upper-bound price)

# Code Audit: replay114 (RULING 114)

**Scope**: `tests/package/replay114.py` + `tests/package/test_replay114.py`. Nothing in `pipeline/` changes; no build reads these outputs; Heimdall-only, cap $0.15. I audit against the stated order and the stated checks (1)–(5).

---

## Findings

### [P1] F1 — `pick()` can return fewer than `n` records silently, and the spread arithmetic breaks when `k` divides unevenly
`replay114.py:55-66`

```python
rest = [r for r in rows if r not in first]
k = min(n - len(first), len(rest))
return first + [rest[int(i * len(rest) / k)] for i in range(k)] if k > 0 else first[:n]
```

Three defects in one expression:

1. **`r not in first` uses `==` on dicts.** Two *distinct* records with identical content (same prompt/max_tokens/seed/system — plausible: replay111 asked the same record text at different stages) compare equal, so the second one is dropped from `rest` and the "30 **distinct** records" guarantee silently becomes 29. The order says "30 of the 93 records … (the same 5 I sent the team among them)". Identity should be by `record` key, not dict equality: `rest = [r for r in rows if r["record"] not in {x["record"] for x in first}]`.
2. **`k` can be 0 while `n - len(first) > 0`** when `len(rest) == 0` — then the ternary yields `first[:n]`, which is fine, but if `len(rest) > 0` and `n - len(first) == 0`, `k=0` and the ternary's *else* branch returns `first[:n]` — correct. However when `k > 0`, `int(i * len(rest) / k)` for `i in range(k)` can pick the **same index twice** (e.g. `len(rest)=7, k=5`: indices 0,1,2,4,5 — fine; but `len(rest)=3, k=3` → 0,1,2 fine; `len(rest)=5, k=4` → 0,1,2,3 — fine; the real risk: `len(rest)=4, k=3` → 0,1,2 — fine). Actually the classic failure: `len(rest)=6, k=5` → `int(i*6/5)` = 0,1,2,3,4 — fine. The genuinely broken case is **duplicates in `rest`** (see 1) making `len(rest)` overcount relative to distinct records, so the "spread evenly" claim in the report is computed over a multiset, not a set.
3. **No guard that `len(first) <= n`.** If a future order names more than `n` out_tokens (NAMED grows, `--n` lowered), `first` alone exceeds `n` and the function returns more than `n` records; `run()` then spends past the intended sample. Today NAMED=5, N=30, so latent.

Also: `pick` raises `ValueError` if any named out_tokens value is missing — good fail-closed behavior, but the error message doesn't say which value, which will cost a debugging round-trip when replay111's fixture changes.

**Fix**: key by `record`; `k = max(0, min(n - len(first), len(rest)))`; include the missing token in the `ValueError`; assert `len(got) == len(set(r["record"] for r in got))`.

---

### [P2] F2 — Spend ledger: read-modify-write race and a lost-update window; also `usd_reported` key mismatch risk
`replay114.py:131-146, 167-172`

`add_spend` does read→add→tmp→`os.replace` with no lock. "One call at a time" is enforced only by convention (the driver is single-threaded today), but the order says "no call starts once it holds STOP_USD" — the check `if spent() >= stop_usd` happens **before** the call, and the cost is added **after** it, so a call that starts just under the cap can overshoot: with ~$0.0003/call and a $0.14 stop against a $0.15 order, the overshoot is bounded (~1 call, ~$0.0003) — acceptable, but the *last* call's cost is added even if it pushes past the cap, and there's no final reconciliation. Also `add_spend(row.get("usd_reported"))` — if the response's usage lacks `usd_reported` (the fake gateway's usage has `cost`, not `usd_reported`!), the ledger adds 0.0 and the run never stops. Note the test's `Gateway` returns `{"cost": 0.0001}` while the driver reads `usage.get("usd_reported")` — the test passes only because it never exercises the cap via the real key. **The test's fake and the driver's read disagree on the usage key** — that's exactly the kind of drift the test should catch. (The driver's `usd_reported=usage.get("usd_reported")` at line 125 reads the *parsed* usage dict from `backend.complete`'s return, whose shape is replay111's contract — but the fake gateway's `usage` block is what `Capture` sees, and `Capture` stores `usage=j.get("usage")` — so the row's `usd_reported` comes from the *raw* usage, while `out` comes from `completion_tokens` **or** `usage.get("out")` — two different usage shapes consulted in one function. Pick one contract and assert it.)

Wait — checking more carefully: `ask()` line 123-124: `u = cap.seen.get("usage") or {}` then `out = int(u.get("completion_tokens") or u.get("out") or 0)`. And line 125: `usd_reported=usage.get("usd_reported")` — **`usage` here is the value returned by `backend.complete`, not `u`**. So the row's `out_tokens` comes from the *response* usage, while `usd_reported` comes from the *backend's* return. If the backend's return usage lacks `usd_reported` (or the response's usage uses `cost`), the ledger silently adds 0.0 forever and the $0.14 stop never fires — the run runs to 30 records × 2 legs = 60 calls, potentially past $0.15. This is the exact "cap" the order mandates. I rate it P1→P2 boundary; since the cap is $0.15 and 60 calls × $0.0003 ≈ $0.018, the practical exposure is tiny, but the mechanism is wrong: **the stop is checked against a ledger that may never be credited.** I'll call it P2 given the 5× headroom.

Actually, re-reading: `text, usage, secs = backend.complete(...)` — `usage` is the backend's third return. If replay111's FormatBackend returns the *vendor-reported* usage (the driver docstring says "vendor-reported (usage.cost)"), then `usage.get("usd_reported")` must match replay111's contract. The test's fake never exercises this because `Gateway`'s usage has `cost` and the test never asserts `usd_reported` in a row. **The test asserts the ledger total (0.0006) but that comes from `add_spend(row.get("usd_test...`** — no: the test's `RT.run(3, ...)` with `stop_usd=0.0005` — the ledger holds 0.0006 after 6 calls, so `spent() >= 0.0005` → the third `run(4, ...)` stops. For the ledger to reach 0.0006, `add_spend` must have been called with 0.0001 six times — which requires `row.get("usd_reported")` = 0.0001, which requires `backend.complete`'s returned `usage` to carry `usd_reported` — but the fake `Gateway`'s usage has only `cost`. So either the real `FormatBackend.complete` synthesizes `usd_reported` from the response's `usage.cost` (plausible, replay111's contract), or **the test's 0.0006 assertion is passing by accident** (e.g. `usage` returned by the real backend, when mocked-transported, is built from the response's usage dict — `cost` → `usd_reported`? No: the test does NOT mock `complete`, only `urlopen`, so the real `FormatBackend.complete` runs, parses the fake response, and if it maps `usage.cost` → its returned usage's `usd_reported`, the test is genuinely exercising the path). This hinges on replay111's `FormatBackend.complete` contract, which is not in the diff. **Flag: the test's correctness depends on an unseen contract (replay111.py:56-87); the diff should state that `complete` returns usage with `usd replay114`...** — I'll flag it as P2: the audit cannot verify the ledger-credit path from this diff alone, and the test's `assertAlmostEqual(RT.spent(spend), 0.0006)` silently depends on it.

### [P2] F3 — `Capture.__call__` loses the response body on JSON decode failure and the error row loses `finish_reason`/`id`
`replay114.py:86-90`

`j = json.loads(raw)` — if the gateway returns a 200 with a non-JSON body (vllm's known failure mode, the very thing being measured), `json.loads` raises, `cap.seen` holds status+headers but the exception propagates to `ask()`'s `except`, which builds the error row from `cap.seen` — good, the headers survive. But `id`/`finish_reason`/`usage` are lost even though the body was read. Minor: wrap the parse, keep `raw[:2000]` in the row as `raw_text` for diagnosis. The order (b) says record "the answer's shape (closed JSON, or replay111.shape) and its text (diagnosis only, never a verdict)" — a 200-with-garbage currently produces an error row with no text at all, which *under-reports* exactly the phenomenon under study. P2.

### [A] F4 — `shape_of` catches only `ValueError` — correct for `json.loads`, but `json.JSONDecodeError` is a subclass, so fine. No finding.

### [P2] F5 — `run()`'s resume skips by `(record, leg)` but the *order* of legs depends on `i % 2` of the *pick* index, not the record
`replay114.py:161-164`

On resume, `pick()` is recomputed; if replay111's `OUT_OF_CONTRACT.jsonl` changed since the first run (it's a proof artifact, presumably frozen — but nothing enforces it), the pick order shifts, `i % 2` flips which leg goes first for a record, and the "legs alternate which goes first" property of the *experiment* is preserved only per-run, not per-record. The order says "The legs alternate which goes first" — the design intent (counterbalance order effects) is preserved in aggregate, so this is acceptable; but if the source file is regenerated, the *same record* could get its "with" leg first in run 1 and... no — the skip is by (record, leg), so a resumed record's remaining leg runs in whatever position the new pick gives it. Fine. However: **`done` is built from `x["record"]`/`x["leg"]` without guarding against a truncated last line** (a crash mid-`f.write` leaves a partial JSON line; `map(json.loads, f)` raises, the whole run dies at startup). P2: wrap in a try/JSONDecodeError-continue, or write-then-flush-then-atomic-rename per row like `add_spend` does. Given "one call at a time" and small rows, the torn-line window is one `write` — real but small.

### [P3] F6 — `report()` divides nothing but assumes both legs present; `SUMMARY.json`/`REPORT.md` written even with 0 rows
`replay114.py:183, 207`

`s["with"]`/`s["without"]` are always created (from the comprehension over `("with","without")`), so no KeyError — good. But with an empty RESULTS.jsonl, `report()` writes a REPORT.md whose table shows 0/0/0 — fine, arguably correct. However `main()` with `--report-only` on a *missing* RESULTS.jsonl raises FileNotFoundError with no friendly message. P3.

### [P3] F7 — `Capture` merges headers via `{**headers, **self.extra}` — if `providers` ever passes `x-bf-tunnel-instance` itself, the extra silently wins
`replay1`14.py:78`

`{**headers, **self.extra}`: the extra header overrides the base. Today providers doesn't send it (the test asserts its absence on the "without" leg, which would catch it), so this is the *desired* precedence, but it's worth a comment. Also: if `headers` (from providers) is a `dict`-like with different casing (`X-BF-Tunnel-Instance`), the dict-merge produces duplicate headers differing in case — HTTP headers are case-insensitive, but the test's `req.header_items()`... the test's Gateway lowercases, so the test would catch a case mismatch only if providers changed. P3.

### [P3] F8 — `row.update(seconds=..., **cap.seen, ...)` — `cap.seen` keys can collide with the row's own keys
`repl`ay114.py:121, 125

In the error path, `row.update(seconds=..., error=..., **cap.seen)` — if `cap.seen` ever contained a key `error` or `seconds`, it would overwrite. Today `Capture.seen` only ever holds `status/response_headers/id/finish_reason/usage/response_model`, so no collision. Latent. P3.

### [P3] F9 — `N, STOP_USD = 30, 0.14` — the order's cap is $0.15, the stop is $0.14
`replay114.py:46`

Intentional (headroom for the last call), documented in the docstring ("$0.0.14 of the order's $0.15" — typo: `$0.0.14` should be `$0.14`, line 21). P3 typo.

### [P3] F10 — `report()`'s differing-headers counter compares case-sensitively via `a.get(k) != b.get(k)` after lowercasing the *key set* but not the lookup
`replay114.py:190-191`

```python
keys.update(k.lower() for k in set(a) | set(b) if a.get(k) != b.get(k))
```

`k` iterates the union of the *original-case* keys; `a.get(k)`/`b.get(k)` are case-sensitive lookups on the original dicts. If the gateway returns `X-BF-Instance` on one leg and `x-bf-instance` on the other (same header, different case — legal, and exactly what a "which instance answered" probe wants to detect), the comparison `a.get(k) != b.get(k)` misses it: `a.get("X-BF-Instance")` hits, `b.get("X-BF-Instance")` returns None → counted as differing — actually that *over*-counts (reports a difference where the semantic value is the same, just case-differing key). And the converse: if both legs return the same header name in different case with the *same value*, it's counted as differing — a false positive in the "instance changed?" report. Since the report's purpose is "whether any response header shows the instance changed", a case-only difference reported as a difference is a **false signal**. P2→P3: the report is diagnosis, not a gate, so P3. But it's the report's *headline* question. I'll say P2, because the order's (c) asks precisely this question and the answer can be wrong-by-case.

Hmm, let me settle: the report is explicitly "diagnosis only, never a verdict" for text, and the header question is the report's purpose. A case-only key difference producing a spurious "differs" entry is a wrong *report* (not a wrong gate). The order says "If the header changes nothing, say so: it may not be forwarded" — a false "differs" would say the header *did* something. I'll grade **P2**.

### [P3] F10b — `bf = sorted({k for r in rows for k in (r.get("response_headers") or {}) if k.lower().startswith("x-bf")})` — collects keys, not values; the report lists which x-bf headers *exist* but never their values
`replay114.py:192`

The order (b) says record "every response header (so we can see which instance answered, e.g. any x-bf-* header)". The SUMMARY/REPORT list the *names* of x-bf headers seen, but the *values* (the instance names — "an instance name would show there", the order's own words) are only in RESULTS.jsonl, not surfaced in the report. The report's purpose (c) — "whether any response header shows the instance changed" — is answered by `headers_differing_within_a_pair` (names only) plus the reader digging into RESULTS.jsonl. **The report never prints the actual instance-identifying values.** P2: the deliverable answers "did a header differ" but not "what did it say", which is what the orchestrator asked to see ("e.g. any x-bf-* header" — they want the value, e.g. `x-bf-instance: pinga282` vs `vllm-7`). The test even constructs exactly this signal (`x-bf-instance: pinga282` vs `vllm-7`) and the report would show only the *name* `x-bf-instance` in `headers_differing_within_a_pair` and in `x_bf_response_headers` — the values pinga282/vllm-7 never reach REPORT.md. That's the single most important datum of the ruling, present in the rows, absent from the report. **P2, arguably the most consequential report defect.** Let me check once more... `s["x_bf_response_headers"] = bf` — names only. `headers_differing_within_a_pair` — counts of names. REPORT.md lines: the bf names, the differing counts, the response_models (values! — `response_models` DOES print values, via Counter of `response_model`). So the report prints response_model *values* but not x-bf header *values*. Inconsistent, and the instance name is the point. Confirmed P2.

### [P2] F11 — `ask()`'s `out_tokens` fallback `u.get("out")` reads a key the response usage never carries
`replay114.py:124`

`out = int(u.get("completion_tokens") or u.get("out") or 0)` — the OpenAI-shaped usage has `completion_tokens`; `out` is presumably replay111's internal usage shape. But `u` is `cap.seen["usage"]` = the *raw response's* usage, which is OpenAI-shaped (`completion_tokens`, as the test's Gateway confirms). So `u.get("out")` is dead code on the raw path — unless the gateway itself returns replay111-internal shape, which the test's fake (authoritative for the contract) says it doesn't. Dead fallback = harmless, but it signals the same contract confusion as F2 (two usage shapes consulted). P3.

### [P3] F12 — `run()`'s `print` of the stop message uses `spent()` twice (two reads of the ledger) — benign.

### [P3] F13 — Test `TestAsk.setUp` calls `RT.backend()` which builds the real router (`RY.build_router(("none",), spend_path=None)`) — if replay111's `build_router` reads a key from the environment or a keyfile, the "offline" test isn't fully offline; the test sets `self.b.key = lambda name: KEY` which suggests the backend's key is a *callable* — if the real `backend.key` is an attribute (string) not a callable, `self.b.key = lambda...` would *change the type* and the real `complete` might call it. The test passes, so it's callable-or-attribute-compatible; latent fragility. P3.

### [P3] F14 — `Gateway.__call__` pops from `answers`; a third call raises IndexError instead of a clean failure
P3.

### [P doubles-check] — `test_the_header_only_on_its_leg...` asserts `g.seen[0]["body"] == g.seen[1]["body"]` — this is the (1) check, good. It asserts the four request fields; it does NOT assert the prompt/system equality... it does: the whole body equality covers it. Good. It does not assert that the "with" leg's *extra* header didn't perturb anything else — body equality covers the body; headers: it asserts presence/absence of the tunnel header but not that the *other* request headers (Content-Type, Authorization) are identical between legs. The order's (1) — "byte-for-byte replay111's apart from the one header" — is only partially tested: body yes, other headers no. If `capturing()` accidentally dropped, say, a providers-set `User-Agent` on the "with" leg, no test would notice. P3 (the merge is a dict-merge that only adds, so it can't drop — but the test doesn't pin it).

### [P2] F15 — `run()`'s alternating-legs logic: `for leg in (("with","without") if i % 2 == 0 else ("without","with"))` — on resume, a record whose "with" leg is done but "without" isn't runs only the "without" leg, which is correct; but the *pair* completeness is never enforced at the end
`replay114.py:161-176`

If the cap stops the run mid-pair (the test even exercises this: `RT.run(4, ..., stop_usd=0.0005)` stops after 6 calls = 3 complete pairs — wait, 6 calls with 3 records × 2 legs = 3 pairs, so the test's stop lands on a pair boundary by luck of the numbers), the report's `pairs` will have 1-legged records, and `headers_differing_within_a_pair` silently excludes them. The report does print per-leg `calls`, so a 1-legged record shows up as a call-count imbalance — detectable but not surfaced. The order's (c) report compares "with / without" — an unpaired record *dilutes* the comparison. The report should state how many records contributed to the paired comparison. P2: the headline statistic's denominator is unstated. Actually `s["records"] = len(pairs)` counts 1-legged records too, and the REPORT.md says "N of replay111's 93 unclosed records, each asked WITH ... and WITHOUT" — **that sentence is false when a record has one leg** (the cap can stop mid-pair). P2.

### [P3] F16 — `report()`'s `s["at"]` uses `time.strftime("%z")` — fine.

### [P3] F17 — `unclosed()` reads `RY.OUT`-relative path; if replay111's OUT dir moved, FileNotFoundError at import... no, at call. Fail-closed, fine.

### [P2] F18 — `ask()`'s error path: `row.update(seconds=..., error=..., **cap.seen)` — `cap.seen` may be `{}` if the failure happened *before* urlopen (e.g. `json.dumps(body)` fails, or `Request` construction). Then the row has no `status`/`response_headers` — acceptable (nothing was received). But if the failure is a `URLError` (not HTTPError) — e.g. timeout, connection refused — `cap.seen` is `{}` and the row has an error with no status. Correct. But note: `providers._with_backoff` retries 429/5xx *inside* `backend.complete`... wait, no: `Capture` replaces `P._http_json`, and `_with_backoff` wraps the *caller* of `_http_json` inside providers, so retries happen with the Capture in place — each retry overwrites `cap.seen`, so the row records only the **last** attempt's headers/status. The order (b) says record "every response header" — per call. With retries, intermediate attempts' headers (which might name different instances! — the very thing being probed) are discarded. **If the gateway round-robins, a 429-then-200 sequence loses the 429's instance header.** P2: the measurement discards exactly the evidence it's hunting, on the retry path. The order says "One call at a time" and the retry is part of one logical call, but the *headers* of each attempt are the experiment's data. I'd argue this is the strongest finding: the probe's purpose is to see which instance answers, and the retry path silently keeps only the last. P2 (not P1: retries are rare, and the primary comparison — 200-both-legs — is unaffected).

---

## What's right (so the other models don't just pile on)

- **The (1) check — request fidelity** — is genuinely tested: full-body equality between legs, plus the four contract fields (seed, response_format, reasoning_effort, model) pinned. The `capturing()`/finally-restore of `P._http_json` is clean, exception-safe, and the test's `Gateway` records `header_items()` lowercased, which makes the header-presence assertions robust to case.
- **No-key-in-rows** (check 2) is tested thoroughly: `assertNotIn(KEY)`, `assertNotIn("Bearer")`, `assertNotIn("authorization")` case-insensitively, on both the success row and the error row, and the error-row-keeps-headers case is separately tested. The `Capture` never stores request headers by construction — the design (store only response-side fields) makes the "never log Authorization" requirement structural, not incidental. Good.
- **The cap** (check 3): stop-before-call, cost-after, resume-by-(record,leg), and the test exercises resume + cap + "real ledger never touched" (the `before`/`os.path.exists` guard is a nice touch — it checks the *real* SPEND_R114.json's existence, not just the patched path). The tmp+`os.replace` atomic write is correct.
- **`shape_of`** correctly delegates to `replay111.shape` for non-parsing text, keeping the "truncated" classification identical to replay111's — no second, divergent definition of "unclosed". Good.
- **Alternating legs** implemented as specified; the test pins the exact leg order `["with","without","without","with","with","without"]` — the i%2 flip is exercised, including the resumed run.
- **`add_spend`'s tmp+replace** is atomic; `spent()`'s exception→0.0 is fail-soft but consistent with "vendor-reported, best-effort ledger" — though see F2's "ledger never credited" concern.
- **The test's `TestRun`** patches `RT.unclosed`, `RT.WT`, `RT.SPEND` — and the docstring notes the earlier bug (ledger path bound at definition time) is fixed and *tested* (`self.assertEqual(os.path.exists(real), before)`). That's the kind of regression note that earns trust.

---

## Severity summary

| # | Finding | Sev |
|---|---|---|
| F1 | `pick()` dedups by dict-`==`, not by `record` key; duplicate-content records silently shrink the sample; no `len(first) <= n` guard | P1 |
| F2 | Ledger-credit path depends on unseen replay111 contract (`usage`→`usd_reported`); test's 0.0006 assertion may pass via that unseen mapping; two usage shapes consulted in one function | P2 |
| F3 | 200-with-garbage-JSON loses body/id/finish_reason in the row; under-reports the phenomenon under study | P2 |
| F5 | Torn last line in RESULTS.jsonl kills resume at startup (no torn-line tolerance) | P2 |
| F10 | Case-differing duplicate header keys counted as "differs" — false "instance changed" signal in the report's headline question | P2 |
| F10b | Report never prints x-bf header *values* (the instance names) — the ruling's key datum lives only in RESULTS.jsonl | P2 |
| F15 | REPORT.md's "each asked WITH and WITHOUT" is false when the cap stops mid-pair; paired-comparison denominator unstated | P2 |
| F18 | Retry path (429/5xx via `_with_backoff`) overwrites `cap.seen` — intermediate attempts' instance headers discarded | P2 |
| F6, F7, F8, F9, F11, F12, F13, F14, (1)-partial-assert | nits: --report-only on missing file; header-merge precedence; seen-key collision; $0.0.14 typo; dead `out` fallback; double ledger read; backend().key fragility; Gateway IndexError; other-headers-not-pinned | P3 |

**On the governing laws**: this diff touches no pipeline code, so SENTENCE LAW / SELECTION LOCK / L-a…L-l are not engaged. M12 (fail closed) is honored: errors become rows, never passes; the cap stops, never skips. LAW 20/M2: thresholds ($0.14, N=30) are constants — good. The "no new renderer/compositor/selector" (M1) constraint: satisfied, it's a measurement driver. GPU0/publishing: N/A.

**Verdict**: mergeable after F1; the report defects (F10b, F15) should be fixed before the ruling is *read*, because the report is the deliverable the orchestrator acts on — a report that never shows the instance name answers the question "did the header change anything" with names instead of values.

P1_OR_WORSE: 1