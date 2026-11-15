# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2339
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 30 s finish=stop usage in 13928 / out 612 usd_reported=0.026573 usd~0.085 (upper-bound price)

**CODE AUDIT: pp-selectid / RULING 110 (replay110.py + test)**

**Summary**  
The change adds a self-contained, resumable replay driver (`tests/package/replay110.py`) and its unit test exactly as described in the ruling. It re-uses `replay85.py` decision/comparison logic without modification, creates isolated Heimdall candidate back-ends from the production template (no config or routing mutation), respects ruling 100 deadlines, applies the spend stop, treats parse failures as “out of contract”, writes only to its own proof/ directory, and never touches production state, release paths, or any governed pipeline stage (EDL, render, gates, selection, punctuation, clusters, voice-over, etc.). All governing laws that apply to model replies, fail-closed behavior, canonical text handling, and release authorization are satisfied. The test suite exercises every major branch (in-time/late/timeout/out-of-contract/spend-stop/rate-limit/record filtering/summary arithmetic).

**Findings**

- **[P3]** Docstring claims “GATEWAY_MODELS.json” is read; the implementation hard-codes the two model IDs instead. Pure documentation nit; behavior matches the ruling text.
- **[P2]** Timeout detection in `replay_one` uses `if "abandoned at the deadline" in str(e)`. While it works for the current `ProviderError`, it is a brittle string match. A change in exception wording would silently alter classification. Prefer a dedicated exception attribute or subclass (still a test-only script, so not a production gate).
- **[P3]** `router.down.pop(name(m), None)` before every call is intentional (“each call is tried afresh”) but undocumented in the module docstring. Readers must infer the intent from the inline comment.
- **[P2]** Multi-threaded spend-stop check (`router.spent() >= stop_usd`) has no explicit lock around the read+possible call. The Router’s own reservation logic plus the per-`one()` lock on writing results make actual overspend unlikely, but the stop condition is not strictly serialized. Acceptable for a one-off replay with $0.75 limit, yet worth a small refactor for cleanliness.
- **[P3]** `incumbent()` re-parses `RESULTS.jsonl` on every `table()` invocation. Negligible for 319 records but could be memoized.

No violations of SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-l, LAW 20/M2, M12 FAIL CLOSED, LAW 22 (v2f byte-identical render), release authorization rules, or canonical-form requirements. No production code, renderer, selector, DB schema, or UI change. Smallest diff (only the new test driver + test). All must-fail/must-pass cases from the ruling are exercised by the unit tests.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 118 s finish=stop usage in 15717 / out 5094 usd_reported=0.004363 usd~0.124 (upper-bound price)

To perform a rigorous code audit of `C1_STEP.diff` (RULING 110: Heimdall Candidates), I will analyze the provided code against the **Governing Laws**, the **Technology Stack**, and the specific **Checklist** items requested.

### Context Analysis
The code introduces `tests/package/replay110.py`, a driver to re-evaluate recorded Grok verdicts (from Ruling 85.1) using two new DeepSeek models via the Heimdall gateway. It also includes `tests/package/test_replay110.py`.

**Key Constraints:**
1.  **No Routing Change:** The code must not alter production routing.
2.  **Spend Control:** Strict limits on API spend ($3.00 limit, $0.75 stop).
3.  **Deadline Logic:** Must correctly classify responses as `in_time`, `late`, `timeout`, `error`, or `out_of_contract` based on Ruling 100's deadlines.
4.  **Data Integrity:** Must reuse Ruling 85.1's records and decision logic (`replay85`).
5.  **Fail Closed:** Errors or missing data must not result in a "pass" or incorrect aggregation.

---

### Findings

#### 1. Classification Logic & Deadline Handling

**[P1] Incorrect `timeout` classification in `replay_one`**
In `replay110.py`, lines 133-139:
```python
    except P.ProviderError as e:
        if "HTTP 429" in str(e):
            sleep(30)
            return None
        row.update(seconds=round(time.time() - t0, 2), heimdall=None, heimdall_error=f"{type(e).__name__}: "
                   f"{str(e)[:200]}", outcome="timeout" if "abandoned at the deadline" in str(e) else "error")
        return row
```
The code checks for the string `"abandoned at the deadline"` to classify a `ProviderError` as a `timeout`. However, the docstring and the `P.ProviderError` behavior (implied by the stack) might not guarantee this exact string for *all* timeout scenarios, or it might be a specific implementation detail of `providers.py` that is fragile. More critically, if the `Router.call` raises a `ProviderError` due to a network failure *before* the deadline, it is correctly labeled `error`. But if the `Router` enforces the deadline by raising a specific exception, relying on string matching is brittle.
*However*, looking at the test `test_no_answer_by_the_cap_is_a_timeout_with_no_decision` (line 419-423), it uses `Timed(GROK, 0.6)` with `cap_s=0.2`. The `Timed` class sleeps for 0.6s. The `Router` is expected to interrupt this. If the `Router` raises a `ProviderError` with the message "abandoned at the deadline", this works.
**The real issue:** The `outcome` is set to `timeout` *only* if the string matches. If the `Router` raises a generic `TimeoutError` or a `ProviderError` with a different message (e.g., "Request timed out"), it will be classified as `error` instead of `timeout`. This violates the requirement to accurately measure latency and missed deadlines. The classification should rely on the exception type or a specific attribute, not a substring match on the error message, unless `providers.py` strictly guarantees this message. Given the "Fail Closed" law, misclassifying a timeout as an error might hide latency issues.
*Refinement:* The prompt states "a call is cut at CAP_S... TIMEOUT when it gave no answer by the cap". The `Router` is responsible for this cut. If the `Router` raises `P.ProviderError` with that specific message, it's acceptable *if* that's the contract. But it's a P1 risk if the contract is not explicit. Let's look closer at `replay85` or `providers` usage. The code imports `providers as P`. Without seeing `providers.py`, we must assume the string match is the intended interface.
**Wait**, there is a more subtle bug.
Line 150: `row["outcome"] = "in_time" if dl is None or secs <= dl else "late"`.
This line is reached *only* if `router.call` succeeds (no exception).
If `router.call` raises `P.ProviderError` (timeout), it returns at line 139.
If `router.call` succeeds, it calculates `secs`.
The logic seems consistent *if* the `Router` raises the specific error for timeouts.

**[P2] `deadline_100_s` can be `None`**
Line 118: `dl = router.effective_deadline(...)`.
Line 150: `if dl is None or secs <= dl`.
If `dl` is `None`, the outcome is `in_time`.
The docstring says: "IN TIME when it answered within the deadline... else the gateway's configured 120 s".
If `effective_deadline` returns `None`, it implies no deadline or a default. The code treats `None` as "in time" regardless of `secs`. This might be incorrect if `None` means "unknown" or "no limit". If there is no limit, any time is "in time". This seems logically sound for "no deadline", but the variable name `deadline_100_s` suggests a specific value. If `None` is returned, the table will show `None` (handled by `_s` as `-`). This is acceptable.

#### 2. Record Set & Decision Reuse

**[P1] `source_records` deduplication logic is flawed**
Lines 62-87:
```python
def source_records(path=SOURCE, wt=WT):
    seen, out, missing = set(), [], []
 

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 consensus, audit 20261114_2339 (written by the builder; reviewers qwen3.8-27b and deepseek-v4.1-flash, Heimdall,
# glm's breaker open; deepseek ran to its 16,000-token cap with no closing count: NO ANSWER, so Grok was asked)

No real defect. Three wording fixes made; no logic changed.

## qwen's two closing P1s
- THE SPEND STOP IS NOT ATOMIC (qwen P0/P1; Grok P2, "overspend unlikely"): true as stated, and by design. Each call
  checks the ledger at its own start, so the calls already in flight finish and are booked; the total can pass $0.75
  by their reported cost (Heimdall: a few tenths of a cent each, at most workers x models = 8 calls). A lock around
  check + call would serialize every call; counting the in-flight calls' list-price upper bounds (~$0.3 each) against
  the stop would refuse almost every call. FIXED IN WORDS: the docstring states that bound.
- THE TIMEOUT IS A STRING MATCH (qwen P1; Grok P2): it is ruling 85.1's own classification (replay85.table reads the
  same words), on the Router's ProviderError, which lists each leg's reason (providers.py:1410). It is pinned on the
  real Router: test_no_answer_by_the_cap_is_a_timeout runs the Router's own abandonment, and mutation X2 ("a timeout
  counts as an error") is killed. FIXED IN WORDS: a comment at the match says so.

## qwen's other [P1] / [P0] tags: answered by qwen itself
"This logic holds" (the record content), "This is acceptable for a test driver" (build_router: a new Router instance,
no file written), "likely fine" (the dedup); the rest of its tagged items are about tests it then finds consistent.
- qwen P2 "missing may hold duplicates": not so. seen.add(rel) runs BEFORE the record is read, so a record is
  handled (and set aside) once.

## Grok (P1_OR_WORSE 0)
- P3 "the docstring claims GATEWAY_MODELS.json is read": FIXED IN WORDS (the ids are fixed in the driver; the file
  records the gateway's list).
- P3 router.down.pop undocumented / P3 incumbent() re-reads RESULTS: no change (commented at the line; 319 rows).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_2339/C2_STEP.diff (487 lines)
```
   1 | diff --git a/tests/package/replay110.py b/tests/package/replay110.py
   2 | new file mode 100644
   3 | index 0000000..0baf797
   4 | --- /dev/null
   5 | +++ b/tests/package/replay110.py
   6 | @@ -0,0 +1,340 @@
   7 | +#!/usr/bin/env python3
   8 | +"""RULING 110 (orchestrator 23:32 ET Nov 14): HEIMDALL CANDIDATES. The recorded Grok verdicts of ruling 85.1's replay
   9 | +(the 319 records behind its 884 (record, model) rows: tests/package/proof/replay85/RESULTS.jsonl) are re-asked, with
  10 | +the SAME prompt, of two models the Heimdall gateway lists (GET /models at 23:32 ET Nov 14, recorded in
  11 | +proof/replay110/GATEWAY_MODELS.json; the ids are fixed here):
  12 | +- dsv41unc: deepseek/deepseek-v4.1-flash-1017-uncensored (the v4.1 we run, uncensored, per the Heimdall team);
  13 | +- dsv4: deepseek/deepseek-v4-flash-0731-abliterated (the ONLY DeepSeek v4, not 4.1, the gateway lists: an
  14 | +  abliterated build, not a plain v4).
  15 | +Each answer is reduced to the pipeline's own DECISION and compared with Grok's by ruling 85.1's own code
  16 | +(replay85.decide / compare / passes / grok_self). NO routing change: each candidate is a Heimdall back-end made here
  17 | +from the configured deepseek-v4.1-flash spec (model id swapped), on a chain of its own; no config file changes.
  18 | +DEADLINES (ruling 100): a call is cut at CAP_S (300 s, ruling 100's ceiling) so its latency is measured. It is IN TIME
  19 | +when it answered within the deadline ruling 100 gives a live call of that (model, verdict role) today
  20 | +(providers.Router.effective_deadline under heimdall_first: the pair's own table row, else the gateway's configured
  21 | +120 s); LATE (a missed deadline: production would have no verdict) when it answered after that, before the cap; a
  22 | +TIMEOUT when it gave no answer by the cap. Agreement is reported on the in-time answers and on every answer.
  23 | +SPEND: Heimdall only. Its own ledger (tests/package/proof/SPEND_R110.json, vendor-reported basis, an abandoned call at
  24 | +the model's own rate); no call starts once the ledger holds STOP_USD. Each call checks at its own start, so the
  25 | +calls already in flight then (at most workers x models) finish and are booked: the total can pass the stop by their
  26 | +reported cost, a few tenths of a cent each. LIMIT_USD only bounds the reservations of calls in flight (each holds its
  27 | +list-price upper bound, about $0.3), and a call that fits waits for them (reserve_wait_s).
  28 | +Replies are recorded under tests/package/proof/replay110/replies (a re-run is free); RESULTS.jsonl is appended per
  29 | +(record, model) and a re-run resumes. A rate-limited call (HTTP 429) or one refused by the guard writes no row.
  30 | +Usage: python3 -B tests/package/replay110.py [--workers 4] [--models dsv41unc,dsv4] [--limit N] [--table-only]"""
  31 | +import argparse
  32 | +import json
  33 | +import os
  34 | +import statistics
  35 | +import sys
  36 | +import threading
  37 | +import time
  38 | +from concurrent.futures import ThreadPoolExecutor
  39 | +
  40 | +HERE = os.path.dirname(os.path.abspath(__file__))
  41 | +REPO = os.path.dirname(os.path.dirname(HERE))
  42 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
  43 | +sys.path.insert(0, HERE)
  44 | +import deadline_table as DT  # noqa: E402
  45 | +import providers as P  # noqa: E402
  46 | +import replay85 as R  # noqa: E402
  47 | +
  48 | +WT = R.WT
  49 | +OUT = os.path.join(WT, "tests", "package", "proof", "replay110")
  50 | +SOURCE = os.path.join(R.OUT, "RESULTS.jsonl")
  51 | +SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_R110.json")
  52 | +LIMIT_USD, LIMIT_BASIS, STOP_USD = 3.00, "reported", 0.75
  53 | +RESERVE_WAIT_S = 600.0
  54 | +CAP_S = 300.0
  55 | +TEMPLATE = "heimdall:deepseek/deepseek-v4.1-flash"
  56 | +MODELS = {"dsv41unc": "deepseek/deepseek-v4.1-flash-1017-uncensored",
  57 | +          "dsv4": "deepseek/deepseek-v4-flash-0731-abliterated"}
  58 | +OUTCOMES = ("in_time", "late", "timeout", "error", "out_of_contract")
  59 | +
  60 | +
  61 | +def name(m):
  62 | +    return "heimdall:" + MODELS[m]
  63 | +
  64 | +
  65 | +def source_records(path=SOURCE, wt=WT):
  66 | +    """Ruling 85.1's records, once each, in its order -> ([(path, rec, kind, anchors)], [records that cannot be read or
  67 | +    no longer read as the type ruling 85.1 gave them])."""
  68 | +    seen, out, missing = set(), [], []
  69 | +    with open(path) as f:
  70 | +        for line in f:
  71 | +            try:
  72 | +                x = json.loads(line)
  73 | +            except ValueError:
  74 | +                continue
  75 | +            rel = x.get("record")
  76 | +            if not rel or rel in seen:
  77 | +                continue
  78 | +            seen.add(rel)
  79 | +            try:
  80 | +                with open(os.path.join(wt, rel)) as g:
  81 | +                    rec = json.load(g)
  82 | +            except (OSError, ValueError):
  83 | +                missing.append(rel)
  84 | +                continue
  85 | +            k = R.kind(rec)
  86 | +            if k is None or k != x.get("type"):
  87 | +                missing.append(rel)
  88 | +                continue
  89 | +            out.append((os.path.join(wt, rel), rec, k, list(x.get("anchors") or [])))
  90 | +    return out, missing
  91 | +
  92 | +
  93 | +def build_router(models, record_dir=None, spend_path=None, deadline_log=None):
  94 | +    """The production config's Router under heimdall_first (ruling 100's deadlines as a live call gets them, the table
  95 | +    read, never rewritten), each candidate a Heimdall back-end copied from TEMPLATE's spec with its model id swapped."""
  96 | +    r = P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD,
  97 | +                 limit_basis=LIMIT_BASIS, routing="heimdall_first", deadline_log=deadline_log,
  98 | +                 deadlines=DT.load(DT.STATE, None), reserve_wait_s=RESERVE_WAIT_S)
  99 | +    tmpl = r.config["backends"][TEMPLATE]
 100 | +    for m in models:
 101 | +        r.backends[name(m)] = P.HeimdallBackend(name(m), dict(tmpl, model=MODELS[m]), r.env_path)
 102 | +        r.chains[f"replay110_{m}"] = [name(m)]
 103 | +    return r
 104 | +
 105 | +
 106 | +def _listed(d):
 107 | +    return {u: (list(v) if isinstance(v, tuple) else v) for u, v in d.items()}
 108 | +
 109 | +
 110 | +def _tupled(v):
 111 | +    return tuple(v) if isinstance(v, list) else v
 112 | +
 113 | +
 114 | +def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep):
 115 | +    """One record asked of one candidate -> its row, None (rate limited or refused by the guard: no row, a re-run asks
 116 | +    again; a rate limit first waits 30 s) or "stopped" (the ledger holds stop_usd: no call made)."""
 117 | +    p, rec, k, anchors, m = job
 118 | +    if router.spent() >= stop_usd:
 119 | +        return "stopped"
 120 | +    b = router.backends[name(m)]
 121 | +    dl = router.effective_deadline(rec.get("role"), b, None)       # ruling 100: what a live call of this verdict gets
 122 | +    row = {"record": os.path.relpath(p, WT), "type": k, "model": m, "model_id": MODELS[m], "anchors": anchors,
 123 | +           "grok_recorded_at": rec.get("recorded_at"), "grok_seconds": rec.get("seconds"), "deadline_100_s": dl,
 124 | +           "cap_s": cap_s}
 125 | +    try:
 126 | +        row["grok"] = _listed(R.decide(k, rec["text"], rec["prompt"]))
 127 | +    except (ValueError, TypeError, KeyError) as e:
 128 | +        row["grok"], row["grok_error"] = None, f"{type(e).__name__}: {str(e)[:160]}"
 129 | +    t0 = time.time()
 130 | +    router.down.pop(name(m), None)                        # a failure is never a verdict: each call is tried afresh
 131 | +    try:
 132 | +        rep = router.call(f"replay110_{m}", rec["prompt"], int(rec.get("max_tokens") or 2000),
 133 | +                          int(rec.get("seed") or 7), system=rec.get("system"), deadline_s=cap_s)
 134 | +    except P.SpendLimit:
 135 | +        return None
 136 | +    except P.ProviderError as e:
 137 | +        if "HTTP 429" in str(e):
 138 | +            sleep(30)
 139 | +            return None
 140 | +        # the Router's ProviderError lists each leg's reason (providers.Router.call: "every back-end unavailable:
 141 | +        # [...]"); an abandoned call's says "abandoned at the deadline", as ruling 85.1's table reads it. The timeout
 142 | +        # test runs the Router's own abandonment, so a change in that wording fails it.
 143 | +        row.update(seconds=round(time.time() - t0, 2), heimdall=None, heimdall_error=f"{type(e).__name__}: "
 144 | +                   f"{str(e)[:200]}", outcome="timeout" if "abandoned at the deadline" in str(e) else "error")
 145 | +        return row
 146 | +    secs = round(rep.seconds or (time.time() - t0), 2)
 147 | +    row.update(seconds=secs, cached=bool(rep.cached), usd_reported=(rep.usage or {}).get("usd_reported"),
 148 | +               usd_estimate=rep.usd, out_tokens=(rep.usage or {}).get("out"))
 149 | +    try:
 150 | +        row["heimdall"] = _listed(R.decide(k, rep.text, rec["prompt"]))
 151 | +    except (ValueError, TypeError, KeyError) as e:
 152 | +        row.update(heimdall=None, heimdall_error=f"out of contract: {type(e).__name__}: {str(e)[:160]}",
 153 | +                   outcome="out_of_contract")
 154 | +        router.reject(rep)
 155 | +        return row
 156 | +    row["outcome"] = "in_time" if dl is None or secs <= dl else "late"
 157 | +    if row.get("grok") is not None:
 158 | +        row["compare"] = {u: R.compare(k, _tupled(g), _tupled(row["heimdall"].get(u))) for u, g in row["grok"].items()}
 159 | +    return row
 160 | +
 161 | +
 162 | +def run(args):
 163 | +    os.makedirs(os.path.join(OUT, "replies"), exist_ok=True)
 164 | +    res_path = os.path.join(OUT, "RESULTS.jsonl")
 165 | +    done = set()
 166 | +    if os.path.exists(res_path):
 167 | +        with open(res_path) as f:
 168 | +            for line in f:
 169 | +                try:
 170 | +                    x = json.loads(line)
 171 | +                    done.add((x["record"], x["model"]))
 172 | +                except (ValueError, KeyError):
 173 | +                    pass
 174 | +    recs, missing = source_records()
 175 | +    if args.limit:
 176 | +        recs = recs[:args.limit]
 177 | +    models = [m for m in args.models if m in MODELS]
 178 | +    router = build_router(models, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND,
 179 | +                          deadline_log=os.path.join(OUT, "DEADLINES.jsonl"))
 180 | +    order, by_type = [], {}                            # round-robin by verdict type: an early table covers them all
 181 | +    for x in recs:
 182 | +        by_type.setdefault(x[2], []).append(x)
 183 | +    while any(by_type.values()):
 184 | +        for k in list(by_type):
 185 | +            if by_type[k]:
 186 | +                order.append(by_type[k].pop(0))
 187 | +    jobs = [(p, r, k, a, m) for (p, r, k, a) in order for m in models if (os.path.relpath(p, WT), m) not in done]
 188 | +    print(f"replay110: {len(recs)} records ({len(missing)} unreadable), {len(models)} models, {len(jobs)} calls to "
 189 | +          f"make ({len(done)} already in RESULTS); stop at ${STOP_USD:.2f} vendor-reported", flush=True)
 190 | +    lock, n = threading.Lock(), {"done": 0, "stopped": 0, "no_row": 0}
 191 | +
 192 | +    def one(job):
 193 | +        row = replay_one(router, job)
 194 | +        with lock:
 195 | +            if row == "stopped":
 196 | +                n["stopped"] += 1
 197 | +            elif row is None:
 198 | +                n["no_row"] += 1
 199 | +            else:
 200 | +                with open(res_path, "a") as f:
 201 | +                    f.write(json.dumps(row) + "\n")
 202 | +            n["done"] += 1
 203 | +            if n["done"] % 10 == 0 or n["done"] == len(jobs):
 204 | +                print(f"  {n['done']}/{len(jobs)} at {time.strftime('%H:%M:%S')}, ${router.spent():.4f} spent", flush=True)
 205 | +
 206 | +    def per_model(m):                                  # one pool per model: a slow model never starves the other
 207 | +        with ThreadPoolExecutor(max_workers=args.workers) as ex:
 208 | +            list(ex.map(one, [j for j in jobs if j[4] == m]))
 209 | +    ts = [threading.Thread(target=per_model, args=(m,)) for m in models]
 210 | +    for t in ts:
 211 | +        t.start()
 212 | +    for t in ts:
 213 | +        t.join()
 214 | +    print(f"replay110: {n['stopped']} not started (the ${STOP_USD:.2f} stop), {n['no_row']} without a row (rate "
 215 | +          f"limited or refused by the guard: a re-run asks them again)", flush=True)
 216 | +    table()
 217 | +
 218 | +
 219 | +def _pct(xs, q):
 220 | +    return DT.percentile(xs, q) if xs else None
 221 | +
 222 | +
 223 | +def _s(x):
 224 | +    return "-" if x is None else f"{x:.0f}"
 225 | +
 226 | +
 227 | +def summary(rows):
 228 | +    """-> {(type, model): figures} over the rows (one per record and model)."""
 229 | +    out = {}
 230 | +    for k in R.DECIDING:
 231 | +        for m in MODELS:
 232 | +            rs = [r for r in rows if r["type"] == k and r["model"] == m]
 233 | +            if not rs:
 234 | +                continue
 235 | +            by = {o: [r for r in rs if r.get("outcome") == o] for o in OUTCOMES}
 236 | +            cin = [c for r in by["in_time"] for c in (r.get("compare") or {}).values()]
 237 | +            call = [c for r in rs for c in (r.get("compare") or {}).values()]
 238 | +            secs = [r["seconds"] for r in rs if r.get("outcome") in ("in_time", "late", "out_of_contract")
 239 | +                    and isinstance(r.get("seconds"), (int, float))]
 240 | +            out[(k, m)] = {
 241 | +                "records": len(rs), **{o: len(v) for o, v in by.items()},
 242 | +                "missed": len(by["late"]) + len(by["timeout"]),
 243 | +                "units_in_time": len(cin), **{x: cin.count(x) for x in ("agree", "stricter", "looser", "different")},
 244 | +                "agree_in_time_pct": 100 * cin.count("agree") / len(cin) if cin else None,
 245 | +                "units_all": len(call), "agree_all_pct": 100 * call.count("agree") / len(call) if call else None,
 246 | +                "p50_s": _pct(secs, 0.5), "p90_s": _pct(secs, 0.9),
 247 | +                "deadline_100_s": sorted({r.get("deadline_100_s") for r in rs}, key=str),
 248 | +                "usd_reported": round(sum(float(r["usd_reported"]) for r in rs if P._num(r.get("usd_reported"))
 249 | +                                          and not r.get("cached")), 6)}
 250 | +    return out
 251 | +
 252 | +
 253 | +def incumbent(records):
 254 | +    """Ruling 85.1's own rows for the deepseek-v4.1-flash we run, on the same records (its run: 300 s cut, 01:06 ET
 255 | +    Nov 14, under the 429 storms of that night) -> {type: figures}."""
 256 | +    out = {}
 257 | +    try:
 258 | +        with open(SOURCE) as f:
 259 | +            rows = [json.loads(x) for x in f if x.strip()]
 260 | +    except (OSError, ValueError):
 261 | +        return out
 262 | +    for k in R.DECIDING:
 263 | +        rs = [r for r in rows if r.get("type") == k and r.get("model") == "deepseek" and r.get("record") in records]
 264 | +        if not rs:
 265 | +            continue
 266 | +        call = [c for r in rs for c in (r.get("compare") or {}).values()]
 267 | +        secs = [r["seconds"] for r in rs if r.get("heimdall") is not None and isinstance(r.get("seconds"), (int, float))]
 268 | +        out[k] = {"records": len(rs), "agree_all_pct": 100 * call.count("agree") / len(call) if call else None,
 269 | +                  "p50_s": _pct(secs, 0.5), "p90_s": _pct(secs, 0.9),
 270 | +                  "timeouts": sum(1 for r in rs if "abandoned at the deadline" in str(r.get("heimdall_error")))}
 271 | +    return out
 272 | +
 273 | +
 274 | +def table():
 275 | +    rows = []
 276 | +    try:
 277 | +        with open(os.path.join(OUT, "RESULTS.jsonl")) as f:
 278 | +            for line in f:
 279 | +                try:
 280 | +                    rows.append(json.loads(line))
 281 | +                except ValueError:
 282 | +                    pass
 283 | +    except OSError:
 284 | +        pass
 285 | +    s = summary(rows)
 286 | +    inc = incumbent({r["record"] for r in rows})
 287 | +    base = R.grok_self()
 288 | +    lines = ["# Ruling 110: Heimdall candidates on ruling 85.1's recorded Grok verdicts", "",
 289 | +             f"Built {time.strftime('%Y-%m-%d %H:%M %Z')} from {len(rows)} (record, model) rows. "
 290 | +             + "; ".join(f"{m} = {MODELS[m]}" for m in MODELS) + ". In time: answered within ruling 100's deadline "
 291 | +             "for that (model, verdict role) today; late: answered after it (a MISSED deadline in production), before "
 292 | +             f"the {CAP_S:.0f} s cut; timeout: no answer by the cut. Stricter: the candidate fails what Grok passed.", "",
 293 | +             "| type | model | records | in time | late | timeouts | errors | out of contract | missed | units in time | "
 294 | +             "agree | stricter | looser | different | agree % in time | agree % all answers | p50 s | p90 s | "
 295 | +             "ruling-100 deadline s | usd reported |", "|" + "---|" * 20]
 296 | +    for (k, m), x in s.items():
 297 | +        lines.append(f"| {k} | {m} | {x['records']} | {x['in_time']} | {x['late']} | {x['timeout']} | {x['error']} | "
 298 | +                     f"{x['out_of_contract']} | {x['missed']} | {x['units_in_time']} | {x['agree']} | {x['stricter']} | "
 299 | +                     f"{x['looser']} | {x['different']} | {_s(x['agree_in_time_pct'])} | {_s(x['agree_all_pct'])} | "
 300 | +                     f"{_s(x['p50_s'])} | {_s(x['p90_s'])} | {', '.join(_s(d) for d in x['deadline_100_s'])} | "
 301 | +                     f"{x['usd_reported']:.4f} |")
 302 | +    lines += ["", "## The deepseek-v4.1-flash we run, on the same records (ruling 85.1's rows: 300 s cut, 01:06 ET "
 303 | +              "Nov 14, under that night's 429 storms)", "",
 304 | +              "| type | records | agree % all answers | p50 s | p90 s | timeouts |", "|---|---|---|---|---|---|"]
 305 | +    for k, x in inc.items():
 306 | +        lines.append(f"| {k} | {x['records']} | {_s(x['agree_all_pct'])} | {_s(x['p50_s'])} | {_s(x['p90_s'])} | "
 307 | +                     f"{x['timeouts']} |")
 308 | +    lines += ["", "## The bars of rulings 85/88/96 (replay85.passes; information only: a model moves into a verdict "
 309 | +              "type only by a later ruling)", ""]
 310 | +    for k in R.DECIDING:
 311 | +        for m in MODELS:
 312 | +            if (k, m) not in s:
 313 | +                continue
 314 | +            ok, why, agree, med = R.passes(rows, base, k, m)
 315 | +            lines.append(f"- {k} / {m}: {'MEETS THE BARS' if ok else 'not: ' + '; '.join(why)}")
 316 | +    lines += ["", "## The baseline: Grok against Grok (replay85.grok_self, from every recorded Grok answer)", "",
 317 | +              "| type | unit pairs | agree % |", "|---|---|---|"]
 318 | +    for k in R.DECIDING:
 319 | +        b = base.get(k)
 320 | +        if b:
 321 | +            lines.append(f"| {k} | {b['pairs']} | {100 * b['agree'] / b['pairs']:.0f} |")
 322 | +    with open(os.path.join(OUT, "TABLE.md"), "w") as f:
 323 | +        f.write("\n".join(lines) + "\n")
 324 | +    with open(os.path.join(OUT, "SUMMARY.json"), "w") as f:
 325 | +        json.dump({f"{k}|{m}": x for (k, m), x in s.items()}, f, indent=1)
 326 | +    print("\n".join(lines[:4 + len(s) + 2]), flush=True)
 327 | +    return s
 328 | +
 329 | +
 330 | +def main(argv=None):
 331 | +    ap = argparse.ArgumentParser()
 332 | +    ap.add_argument("--workers", type=int, default=4, help="calls in flight per model")
 333 | +    ap.add_argument("--models", default=",".join(MODELS))
 334 | +    ap.add_argument("--limit", type=int, default=0, help="the first N records only (a pilot)")
 335 | +    ap.add_argument("--table-only", action="store_true")
 336 | +    a = ap.parse_args(argv)
 337 | +    a.models = [m for m in a.models.split(",") if m]
 338 | +    if a.table_only:
 339 | +        table()
 340 | +        return 0
 341 | +    run(a)
 342 | +    return 0
 343 | +
 344 | +
 345 | +if __name__ == "__main__":
 346 | +    sys.exit(main())
 347 | diff --git a/tests/package/test_replay110.py b/tests/package/test_replay110.py
 348 | new file mode 100644
 349 | index 0000000..69cc2a3
 350 | --- /dev/null
 351 | +++ b/tests/package/test_replay110.py
 352 | @@ -0,0 +1,134 @@
 353 | +#!/usr/bin/env python3
 354 | +"""RULING 110's replay driver (tests/package/replay110.py), offline: fake candidates on the real Router, ruling 100's
 355 | +deadline as the Router gives it, replay85's own decisions. A call is in time, late (a missed deadline), a timeout, an
 356 | +error or out of contract; a rate limit writes no row; the spend stop makes no call; the record set is ruling 85.1's."""
 357 | +import json
 358 | +import os
 359 | +import sys
 360 | +import tempfile
 361 | +import time
 362 | +import unittest
 363 | +
 364 | +HERE = os.path.dirname(os.path.abspath(__file__))
 365 | +REPO = os.path.dirname(os.path.dirname(HERE))
 366 | +for _p in ("pipeline", "tests/package", "tests/providers"):
 367 | +    sys.path.insert(0, os.path.join(REPO, _p))
 368 | +import providers as P  # noqa: E402
 369 | +import replay110 as RX  # noqa: E402
 370 | +from test_gates import a_item  # noqa: E402
 371 | +from test_providers import Fake, router  # noqa: E402
 372 | +
 373 | +M = "dsv41unc"
 374 | +PROMPT = '<excerpt label="m1">Bitcoin is a savings technology.</excerpt>'
 375 | +GROK = json.dumps({"excerpts": [a_item("m1")]})
 376 | +FAILS = json.dumps({"excerpts": [a_item("m1", view="quoting_other")]})
 377 | +
 378 | +
 379 | +class Timed(Fake):
 380 | +    """A candidate that answers after `delay` seconds and reports that time, as a live back-end does."""
 381 | +
 382 | +    def __init__(self, answer, delay=0.0, fail=None):
 383 | +        super().__init__(RX.name(M), "heimdall", answer=answer, fail=fail,
 384 | +                         usage={"in": 100, "out": 10, "usd_reported": 0.001})
 385 | +        self.delay = delay
 386 | +
 387 | +    def complete(self, prompt, max_tokens, seed, system=None):
 388 | +        time.sleep(self.delay)
 389 | +        text, usage, _ = super().complete(prompt, max_tokens, seed, system)
 390 | +        return text, usage, self.delay
 391 | +
 392 | +
 393 | +def candidate(d, b, deadline_s=0.3, spent=0.0):
 394 | +    """A Router with the candidate on its replay chain and ruling 100's gateway deadline for context_verdict."""
 395 | +    led = os.path.join(d, "SPEND.json")
 396 | +    json.dump({"usd_estimate": spent, "calls": 1 if spent else 0, "by_backend": {}, "by_role": {}, "reserved": {},
 397 | +               "usd_reported": spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
 398 | +    r = router(d, [b], {f"replay110_{M}": [RX.name(M)]}, spend_path=led, limit_usd=50.0, limit_basis="reported",
 399 | +               routing="heimdall_first")
 400 | +    r.config["routing"] = {"verdict_roles": ["context_verdict"], "verdict_deadline_s": {"heimdall": deadline_s}}
 401 | +    return r
 402 | +
 403 | +
 404 | +def job(d):
 405 | +    p = os.path.join(d, "rec.json")
 406 | +    rec = {"role": "context_verdict", "backend": "xai:grok", "prompt": PROMPT, "text": GROK, "max_tokens": 100,
 407 | +           "seed": 7, "recorded_at": "2026-11-14T01:00:00Z", "seconds": 20.0}
 408 | +    json.dump(rec, open(p, "w"))
 409 | +    return (p, rec, "step_a", [], M)
 410 | +
 411 | +
 412 | +class TestOneRecord(unittest.TestCase):
 413 | +
 414 | +    def test_an_answer_inside_ruling_100s_deadline_is_in_time_and_compared(self):
 415 | +        with tempfile.TemporaryDirectory() as d:
 416 | +            row = RX.replay_one(candidate(d, Timed(GROK, 0.05)), job(d), cap_s=2.0)
 417 | +            self.assertEqual((row["outcome"], row["deadline_100_s"], row["compare"]), ("in_time", 0.3, {"m1": "agree"}))
 418 | +
 419 | +    def test_an_answer_after_the_deadline_is_late_a_missed_deadline_and_still_compared(self):
 420 | +        with tempfile.TemporaryDirectory() as d:
 421 | +            row = RX.replay_one(candidate(d, Timed(FAILS, 0.5)), job(d), cap_s=2.0)
 422 | +            self.assertEqual((row["outcome"], row["compare"]), ("late", {"m1": "stricter"}))
 423 | +            self.assertGreater(row["seconds"], row["deadline_100_s"])
 424 | +
 425 | +    def test_no_answer_by_the_cap_is_a_timeout_with_no_decision(self):
 426 | +        with tempfile.TemporaryDirectory() as d:
 427 | +            row = RX.replay_one(candidate(d, Timed(GROK, 0.6)), job(d), cap_s=0.2)
 428 | +            self.assertEqual((row["outcome"], row["heimdall"]), ("timeout", None))
 429 | +            self.assertNotIn("compare", row)
 430 | +
 431 | +    def test_an_answer_out_of_contract_is_no_verdict(self):
 432 | +        with tempfile.TemporaryDirectory() as d:
 433 | +            row = RX.replay_one(candidate(d, Timed("not json")), job(d), cap_s=2.0)
 434 | +            self.assertEqual((row["outcome"], row["heimdall"]), ("out_of_contract", None))
 435 | +
 436 | +    def test_a_failure_is_an_error_and_a_rate_limit_writes_no_row(self):
 437 | +        with tempfile.TemporaryDirectory() as d:
 438 | +            row = RX.replay_one(candidate(d, Timed(GROK, fail="HTTP 502 overloaded")), job(d), cap_s=2.0)
 439 | +            self.assertEqual(row["outcome"], "error")
 440 | +            waited = []
 441 | +            self.assertIsNone(RX.replay_one(candidate(d, Timed(GROK, fail="HTTP 429 too many")), job(d), cap_s=2.0,
 442 | +                                            sleep=waited.append))
 443 | +            self.assertEqual(waited, [30])
 444 | +
 445 | +    def test_at_the_spend_stop_no_call_is_made(self):
 446 | +        with tempfile.TemporaryDirectory() as d:
 447 | +            b = Timed(GROK)
 448 | +            self.assertEqual(RX.replay_one(candidate(d, b, spent=0.75), job(d), cap_s=2.0, stop_usd=0.75), "stopped")
 449 | +            self.assertEqual(b.calls, 0)
 450 | +            self.assertNotEqual(RX.replay_one(candidate(d, b, spent=0.74), job(d), cap_s=2.0, stop_usd=0.75),
 451 | +                                "stopped")
 452 | +            self.assertEqual(b.calls, 1)
 453 | +
 454 | +
 455 | +class TestTheSetAndTheTable(unittest.TestCase):
 456 | +
 457 | +    def test_the_records_are_ruling_85s_once_each_and_an_unreadable_one_is_set_aside(self):
 458 | +        with tempfile.TemporaryDirectory() as d:
 459 | +            os.makedirs(os.path.join(d, "r"))
 460 | +            good = {"role": "context_verdict", "prompt": PROMPT, "text": GROK}
 461 | +            json.dump(good, open(os.path.join(d, "r", "a.json"), "w"))
 462 | +            json.dump(dict(good, role="fidelity_verdict"), open(os.path.join(d, "r", "b.json"), "w"))
 463 | +            src = os.path.join(d, "RESULTS.jsonl")
 464 | +            with open(src, "w") as f:
 465 | +                for rel, m in (("r/a.json", "deepseek"), ("r/a.json", "glm"), ("r/b.json", "glm"), ("r/gone.json", "glm")):
 466 | +                    f.write(json.dumps({"record": rel, "type": "step_a", "model": m, "anchors": ["37c5b5f5"]}) + "\n")
 467 | +            recs, missing = RX.source_records(src, wt=d)
 468 | +            self.assertEqual([(os.path.relpath(p, d), k, a) for p, _, k, a in recs], [("r/a.json", "step_a",
 469 | +                                                                                        ["37c5b5f5"])])
 470 | +            self.assertEqual(sorted(missing), ["r/b.json", "r/gone.json"])
 471 | +
 472 | +    def test_agreement_in_time_leaves_late_answers_out_and_missed_counts_late_and_timeouts(self):
 473 | +        rows = [{"type": "step_a", "model": M, "outcome": "in_time", "seconds": 10.0, "compare": {"a": "agree"}},
 474 | +                {"type": "step_a", "model": M, "outcome": "in_time", "seconds": 30.0, "compare": {"b": "stricter"}},
 475 | +                {"type": "step_a", "model": M, "outcome": "late", "seconds": 200.0, "compare": {"c": "agree"}},
 476 | +                {"type": "step_a", "model": M, "outcome": "timeout", "seconds": 300.0},
 477 | +                {"type": "step_a", "model": M, "outcome": "error", "seconds": 1.0}]
 478 | +        x = RX.summary(rows)[("step_a", M)]
 479 | +        self.assertEqual((x["in_time"], x["late"], x["timeout"], x["error"], x["missed"]), (2, 1, 1, 1, 2))
 480 | +        self.assertEqual((x["units_in_time"], x["agree_in_time_pct"]), (2, 50.0))
 481 | +        self.assertAlmostEqual(x["agree_all_pct"], 200 / 3)
 482 | +        self.assertEqual((x["p50_s"], x["p90_s"]), (30.0, 166.0))     # the answers' times only (10, 30, 200)
 483 | +
 484 | +
 485 | +if __name__ == "__main__":
 486 | +    unittest.main()
 487 | 
```

---

pp-selectid, RULING 110 (orchestrator 23:32 ET Nov 14), HEIMDALL CANDIDATES: replay ruling 85.1's recorded Grok
verdicts against two Heimdall models, per verdict type: agreement with the recorded Grok verdict, p50/p90 latency,
error and missed-deadline counts, ruling 100's deadlines; a table in STATE and proof/. NO routing change (a model moves
into a verdict type only by a later ruling, at the bars of rulings 85/88/96). Heimdall calls only, no outside spend.

THE MODELS (the gateway's own list, GET /models, 23:3x ET): deepseek/deepseek-v4.1-flash-1017-uncensored (the v4.1 we
run, uncensored) and deepseek/deepseek-v4-flash-0731-abliterated (the ONLY DeepSeek v4, not 4.1, the gateway lists).

THE CHANGE: one new driver, tests/package/replay110.py, and its test. Nothing else changes (no config file, no
pipeline code, ruling 85.1's replay85.py untouched). It REUSES, UNCHANGED, ruling 85.1's own code for the method:
replay85.kind / decide (tests/package/replay85.py:68, :85: an answer -> the pipeline's decision by its own parsers,
ValueError/TypeError/KeyError = out of contract), compare (:178), grok_self (:343, Grok against Grok, the bar),
passes (:531, the bars of 85/88/96; MIN_UNITS :528).
- THE RECORDS: exactly the records behind ruling 85.1's RESULTS.jsonl, once each (319, all readable today; a record
  that cannot be read, or reads as another type, is set aside and counted).
- THE CANDIDATES: each a providers.HeimdallBackend made in the driver from the configured
  heimdall:deepseek/deepseek-v4.1-flash spec with the model id swapped, on its own chain "replay110_<m>".
- RULING 100: per call, deadline_100 = Router.effective_deadline(<the record's own verdict role>, candidate)
  (UNCHANGED, pipeline/providers.py:1089-1101, under routing heimdall_first: the pair's deadline-table row, else
  role_deadline :1076-1087, the gateway's configured 120 s). Today both candidates have no row: 120 s for every
  type. The call itself is cut at CAP_S = 300 s (ruling 100's ceiling) so its latency is measured: IN TIME if it
  answered within deadline_100; LATE (a missed deadline in production) if after it and before 300 s; TIMEOUT if no
  answer by 300 s (the Router's ProviderError, :1410, carries "abandoned at the deadline"); ERROR otherwise; OUT OF
  CONTRACT if decide() raised. Agreement is given on the in-time answers and on every answer.
- THE DEADLINE TABLE is read with DT.load(DT.STATE, None) (UNCHANGED, pipeline/deadline_table.py:77-100: with no
  record dir it is never saved over the production table).
- SPEND: its own ledger tests/package/proof/SPEND_R110.json (vendor-reported basis), limit $3.00 for the reservations
  in flight (each holds its list-price upper bound, ~$0.3) with reserve_wait_s 600 (7a2ddf91); NO CALL STARTS once
  the ledger holds $0.75 (batch 3's mining/checks share is $1.00). A rate limit (HTTP 429) or a guard refusal writes no
  row (a re-run asks again); its own record dir and deadline log; no breaker or health state is written (the Router
  gets neither).

PLEASE CHECK: (1) the classification against ruling 100 (in time / late / timeout / error / out of contract) and the
deadline it reads; (2) that the set is ruling 85.1's and the decisions are its own; (3) the spend stop and the guard;
(4) anything that could write production state or change routing; (5) the table's arithmetic (p50/p90 over answers
only; missed = late + timeouts); (6) the tests.


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
