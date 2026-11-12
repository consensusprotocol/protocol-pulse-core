# claude-fable-5-2 independent review (276.1 s, 108062 in / 27569 out, 1.9673 USD, stop end_turn)

VERDICT: NOT READY. Q1: the strict parsers hold. I found no path in parse_oracle, parse_judge, parse_groups or witness.parse where an empty or malformed reply becomes NONE, LEGAL or PASS, and SpendStop is never fallen through. The defects are in the accounting around them: recall counts unmeasured records as misses (HIGH), the swap items escape the writer-vendor exclusion, the spend guard has holes for unpriced and failed-after-billing calls, and a local 5xx does not fall through the chain. Q2: L-j and L-l are compliant in the parsers; L-m is violated in the recall count and partial in the re-ask budget and the CLUSTER_FORMATION blame; L-o is partial (rows over 20 s hidden in target mode); L-x is partial (HTTPError fall-through, swap vendor, notify skipped in A/B, local default before its A/B). The sentence, snap, onset, credits and v2f laws are not touched by this diff and cannot be assessed. Q3: no tests are in this package, so nothing is verified. Fix the HIGH and MEDIUM findings and submit the tests before merge.

## F1 HIGH: pipeline/oracle/report.py:1919-1924; pipeline/oracle/score.py:2925,2949
- Defect: A record that crashed, stopped at NOT_RERUN (replay_head stops at the first gemma cache miss) or has no passages.json is counted in the recall denominator as a miss. That reports an unmeasured item as a result (L-m) and contradicts score.py's own docstring ('never as 0 % or 100 %').
- Evidence: `if day["availability"] == "AVAILABLE": recall[name][1] += 1; recall[name][0] += int(bool(recs[name].get("recall_hit")))` and `state["recall_hit"] = any(...) if chosen else False`; `state["complete"]` is computed but never read by the recall count.
- Fix: Count a record in recall only when `state['complete']` is true (for replay_head, outcome starts with COMPLETE) and the selection is readable. Otherwise report it as 'not measured' with its own count.

## F2 MEDIUM: tools/backtest_oracle.py:3421-3423 vs pipeline/oracle/ab.py:132,140-141
- Defect: The writer vendor of the same_dev_hard_max line-ups (source of every must-fail swap) is never added to `writer_vendors`, so a back-end of that vendor can judge its own vendor's line-up (L-x). `same_dev` is included although judge_items reads no item from it.
- Evidence: `subs = {"judge": ("", "same_dev"), ...}` but `_swap` builds its item from `vdir = os.path.join(d, "same_dev_hard_max")` and that directory's ORACLE.json.
- Fix: Derive the avoided vendors from the directories the items actually come from ("" and "same_dev_hard_max" for the judge), or carry the writer vendor on each item and skip per item.

## F3 MEDIUM: pipeline/oracle/llm.py:1038-1043; pipeline/oracle/providers.py:1564-1582
- Defect: Three spend-guard holes. Unpriced Heimdall calls in the 8-thread A/B pool reserve nothing and ignore held reservations, so they can overshoot the cap together. If the gateway reports no `usage.cost` the call is recorded at 0 USD, so the cap never bites. A priced call that fails after billing (stream timeout, client-side error) is released with no ledger row.
- Evidence: `allow_unpriced`: `if spent >= self.cap: raise SpendStop` (no reservation, in-flight ignored); `row.update(usd=0.0, usd_source=... "unpriced")`; on any exception `ledger.release(token)` with the comment 'failed before the vendor billed it'.
- Fix: Give every remote back-end a worst-case price and reserve it. Refuse unpriced calls when spent + in-flight >= cap. Treat a missing gateway cost as the worst case. On an exception after the request was sent, settle the reservation at worst case instead of releasing it.

## F4 MEDIUM: pipeline/oracle/providers.py:1437-1442, 1491, 1608-1612
- Defect: urllib's HTTPError carries `.code`, not `.status_code`, and its class name is not in the list (nor is ConnectionResetError). A 5xx from the local Ollama server is therefore not a vendor-side failure: `call` re-raises instead of moving on. Under the lease the local model is first in every chain, so both attempts fail and the day is ORACLE_FAILED / JUDGE_FAILED while frontier back-ends are up (L-x: the run continues when a vendor is down).
- Evidence: `status = getattr(e, "status_code", None) ...; name in ("APIConnectionError", ..., "URLError", "TimeoutError", "ConnectionError", "RemoteDisconnected", "VendorDown")`; `_ollama` uses `urllib.request.urlopen`.
- Fix: Read `getattr(e, 'code', None)` as well and use `isinstance(e, (urllib.error.URLError, OSError))` rather than class-name matching. Add a test with a local 503.

## F5 MEDIUM: pipeline/oracle/run.py:2350-2351, 2530-2537
- Defect: The schema retry and the violation re-ask share one budget of 2. If attempt 1 is a schema or API failure and attempt 2 is valid but every line-up fails the checks, the documented re-ask is never sent. The day is recorded as 'NOT_AVAILABLE (every proposed line-up failed the deterministic checks)' and counted as measured, although the protocol's answer is missing (L-m).
- Evidence: `... and n < ORACLE_ATTEMPTS:` gates the violation re-ask; `elif not legal and len(o["attempts"]) > (o.get("attempt_used") or 0)` is the only NOT_MEASURED guard.
- Fix: Give the violation re-ask its own attempt, or mark the day NOT_MEASURED when the used attempt is the last one, is all-violating and no violation re-ask was sent.

## F6 MEDIUM: pipeline/oracle/run.py:2396-2399, 2454; pipeline/oracle/lineup.py:700-705
- Defect: Rows longer than 20 s are hidden from the writer in every variant. Under L-o (windows are targets) such a sentence can be a legal clip, so target-mode supply is understated, and the prompt tells the writer 'Only the sentences shown exist'. The report does not label target-mode counts as a lower bound for this reason.
- Evidence: `return [r for r in rows if r["duration_s"] <= L.CLIP_S[1]]` with docstring 'can be in no segment'; variants `same_dev` and `moments` have `"windows_hard": False`.
- Fix: Apply the 20 s filter only when `windows_hard` is true, or state the cap in the report and count the hidden rows per variant.

## F7 MEDIUM: pipeline/oracle/export.py:391-398, 404-406
- Defect: Only `segments` are hash-checked, while sentences, text and times are built from `words` when present. A record whose words changed after the run (e.g. L-e punctuation restored) passes the check and silently changes the 'frozen' universe. If two records share a segments sha, the first filename wins. Uncertain: transcript_store is not in the diff, so the sha may already bind the words.
- Evidence: `if ts.segments_sha256(rec["segments"]) != sha: raise ExportError` but `if rec.get("words"): return [(w["word"].strip(), ...) for w in rec["words"]]`; the loop returns the first sorted `transcript.*.json` whose sha field matches.
- Fix: Hash-check the words that are actually read (or record and verify a words sha in the manifest). Raise ExportError when more than one record matches the sha.

## F8 MEDIUM: pipeline/oracle/score.py:2853-2859; pipeline/oracle/report.py:1914-1915
- Defect: For an incomplete DEC-13 record (crash, or replay NOT_RERUN) with no carrier, the loss is blamed on CLUSTER_FORMATION and counted in the section 3 table. Later pools (72 h tier, wire headlines) may never have run, so this may be a stage the record never reached; only a note separates it. Uncertain whether emergent_clusters already holds both tiers when the run stops.
- Evidence: `else: best, stage = None, "CLUSTER_FORMATION"; note = (... None if complete else "clusters formed; the run stopped before every headline was evaluated")`; report: `stage_counts[name][s] += 1`.
- Fix: Return NOT_REACHED (undecided) whenever `complete` is false and no carrier was decided. Reserve CLUSTER_FORMATION for complete records.

## F9 LOW: pipeline/oracle/ab.py:244; pipeline/oracle/providers.py:1477-1479, 1561
- Defect: In the A/B pool the per-call 90 % tripwire falls back but writes no NOTIFY file when the threshold is crossed mid-batch (L-x: 'notifies and falls back'). The round-1 fix 'tripwire on every call' is only half applied on this path.
- Evidence: `PV.call_backend(name, sys_, user, SCHEMAS[role], ledger, f"ab {role} {iid}")` passes no notify_dir; `if notify_dir: ... f.write("HEIMDALL SPEND AT 90%...")`.
- Fix: Pass `notify_dir=out_dir` through `_one` to `call_backend`.

## F10 LOW: pipeline/oracle/providers.py:1396-1403
- Defect: L-x makes local the default only 'where a measured A/B shows it meets the bar'. For judge, grouping and witness the A/B is pending, yet local is first, so any oracle / witness / group command run inside the lease gets verdicts from an unvalidated judge. PARTIAL compliance.
- Evidence: `"judge": ["local-gemma3-27b", "claude-fable-5-2", ...]` with `DECIDED_BY = {r: "pending: the local A/B runs under the GPU0 lease ..."}`.
- Fix: Keep local out of the default chain (A/B only) for each role until its DECIDED_BY names a passing A/B file.

## F11 LOW: pipeline/oracle/providers.py:1587
- Defect: A remote reply with no usage (tokens_in 0 or missing) skips the cut-prompt check, so the truncation guard fails open exactly when there is no data (L-j / M12).
- Evidence: `if b["kind"] != "ollama" and row.get("tokens_in") and row["tokens_in"] < chars / MAX_CHARS_PER_TOKEN:`
- Fix: Raise ContextTooLong, or a failed call, when a remote back-end returns no prompt-token count.

## F12 LOW: pipeline/oracle/ab.py:146-151
- Defect: The docstring promises the LEAST-related development, but the loop falls through to ever more related pairs. A swap between near-identical developments is then still scored as must-fail on rule 1, which can mark a correct judge as wrong. `min()` also raises ValueError if a group has no accepted line-up.
- Evidence: `for ov, i, j in pairs: base_k = min(k for k in groups[i]["lineups"] if k in passed)` ... returns the first pair whose swap passes `L.check`.
- Fix: Cap the overlap (skip the day above a threshold) and guard the empty case with `default=None`.

## F13 LOW: pipeline/oracle/lineup.py:833; pipeline/oracle/export.py:458
- Defect: A row cut by a '>>' speaker change or a transcript end, not by terminal punctuation, can sit first or mid-segment and pass the deterministic 'whole sentences' check. A segment can also span two speakers unseen, because the prompt shows no '>>'.
- Evidence: `if not rows[-1]["ends_statement"]:` is the only sentence check; `"complete": sentence_law.is_terminal(last)` is exported and never read.
- Fix: Require `complete` on every row of a segment and reject a segment that crosses a speaker-change flush.

## F14 LOW: pipeline/oracle/ab.py:124 vs pipeline/oracle/export.py:370 and pipeline/oracle/__init__.py:553-554
- Defect: ab.py loads a second copy of canon as `pipeline.canon`, against the package's own 'one copy of each in a process' rule (the E-FAIL-021 class it cites).
- Evidence: `from pipeline import canon` versus `import canon  # flat, as the pipeline imports them`.
- Fix: Use `import canon` in ab.py.

## F15 LOW: pipeline/oracle/replay.py:1744, 1779-1782; tools/backtest_oracle.py:3222
- Defect: cache_digest samples an unsorted glob, so the 'most common' digest can vary between runs. 'Nothing here writes outside the replay's own output directory' cannot be verified: select_story, backtest.py and the inherited Embedder / LocalLLM methods are not in the diff, and they are pointed at the live store with nothing enforcing read-only.
- Evidence: `glob.glob(os.path.join(sm.LLM_CACHE_DIR, "*", "*.json"))[:400]`; `os.environ.setdefault("PP_EDITORIAL_STORE", "/home/ultron/protocol_pulse/data/editorial")   # read-only reads`.
- Fix: Sort the glob and count every file (or take the digest from the saved run). Run the replay against a read-only mount or a guard that fails on any open-for-write under the main tree, with a test.

## F16 MEDIUM: package header vs docs/audits/pulse-sentence-law/CURRENT.diff:1-3
- Defect: The diff contains no sentence-law, snap, onset, credits, gate or v2f code and no tests. Q2 for those laws and all of Q3 cannot be verified from this package. That includes the test claims made here (byte-identical export, round-1 fixes F2/F4/F5/F8).
- Evidence: Header: 'Feature: pulse-sentence-law'; diff: 'PACKAGE A of 2: the instrument's CODE (all new files; package B holds its tests, docs and the generated report)'.
- Fix: Review package B (tests) together with A, and audit this commit under its own name and law list.
