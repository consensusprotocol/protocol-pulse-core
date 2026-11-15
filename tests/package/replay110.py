#!/usr/bin/env python3
"""RULING 110 (orchestrator 23:32 ET Nov 14): HEIMDALL CANDIDATES. The recorded Grok verdicts of ruling 85.1's replay
(the 319 records behind its 884 (record, model) rows: tests/package/proof/replay85/RESULTS.jsonl) are re-asked, with
the SAME prompt, of two models the Heimdall gateway lists (GET /models at 23:32 ET Nov 14, recorded in
proof/replay110/GATEWAY_MODELS.json; the ids are fixed here):
- dsv41unc: deepseek/deepseek-v4.1-flash-1017-uncensored (the v4.1 we run, uncensored, per the Heimdall team);
- dsv4: deepseek/deepseek-v4-flash-0731-abliterated (the ONLY DeepSeek v4, not 4.1, the gateway lists: an
  abliterated build, not a plain v4).
Each answer is reduced to the pipeline's own DECISION and compared with Grok's by ruling 85.1's own code
(replay85.decide / compare / passes / grok_self). NO routing change: each candidate is a Heimdall back-end made here
from the configured deepseek-v4.1-flash spec (model id swapped), on a chain of its own; no config file changes.
DEADLINES (ruling 100): a call is cut at CAP_S (300 s, ruling 100's ceiling) so its latency is measured. It is IN TIME
when it answered within the deadline ruling 100 gives a live call of that (model, verdict role) today
(providers.Router.effective_deadline under heimdall_first: the pair's own table row, else the gateway's configured
120 s); LATE (a missed deadline: production would have no verdict) when it answered after that, before the cap; a
TIMEOUT when it gave no answer by the cap. Agreement is reported on the in-time answers and on every answer.
SPEND: Heimdall only. Its own ledger (tests/package/proof/SPEND_R110.json, vendor-reported basis, an abandoned call at
the model's own rate); no call starts once the ledger holds STOP_USD. Each call checks at its own start, so the
calls already in flight then (at most workers x models) finish and are booked: the total can pass the stop by their
reported cost, a few tenths of a cent each. LIMIT_USD only bounds the reservations of calls in flight (each holds its
list-price upper bound, about $0.3), and a call that fits waits for them (reserve_wait_s).
Replies are recorded under tests/package/proof/replay110/replies (a re-run is free); RESULTS.jsonl is appended per
(record, model) and a re-run resumes. A rate-limited call (HTTP 429) or one refused by the guard writes no row.
Usage: python3 -B tests/package/replay110.py [--workers 4] [--models dsv41unc,dsv4] [--limit N] [--table-only]"""
import argparse
import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import deadline_table as DT  # noqa: E402
import providers as P  # noqa: E402
import replay85 as R  # noqa: E402

WT = R.WT
OUT = os.path.join(WT, "tests", "package", "proof", "replay110")
SOURCE = os.path.join(R.OUT, "RESULTS.jsonl")
SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_R110.json")
LIMIT_USD, LIMIT_BASIS, STOP_USD = 3.00, "reported", 0.75
RESERVE_WAIT_S = 600.0
CAP_S = 300.0
TEMPLATE = "heimdall:deepseek/deepseek-v4.1-flash"
MODELS = {"dsv41unc": "deepseek/deepseek-v4.1-flash-1017-uncensored",
          "dsv4": "deepseek/deepseek-v4-flash-0731-abliterated"}
OUTCOMES = ("in_time", "late", "timeout", "error", "out_of_contract")


def name(m):
    return "heimdall:" + MODELS[m]


def source_records(path=SOURCE, wt=WT):
    """Ruling 85.1's records, once each, in its order -> ([(path, rec, kind, anchors)], [records that cannot be read or
    no longer read as the type ruling 85.1 gave them])."""
    seen, out, missing = set(), [], []
    with open(path) as f:
        for line in f:
            try:
                x = json.loads(line)
            except ValueError:
                continue
            rel = x.get("record")
            if not rel or rel in seen:
                continue
            seen.add(rel)
            try:
                with open(os.path.join(wt, rel)) as g:
                    rec = json.load(g)
            except (OSError, ValueError):
                missing.append(rel)
                continue
            k = R.kind(rec)
            if k is None or k != x.get("type"):
                missing.append(rel)
                continue
            out.append((os.path.join(wt, rel), rec, k, list(x.get("anchors") or [])))
    return out, missing


def build_router(models, record_dir=None, spend_path=None, deadline_log=None):
    """The production config's Router under heimdall_first (ruling 100's deadlines as a live call gets them, the table
    read, never rewritten), each candidate a Heimdall back-end copied from TEMPLATE's spec with its model id swapped."""
    r = P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD,
                 limit_basis=LIMIT_BASIS, routing="heimdall_first", deadline_log=deadline_log,
                 deadlines=DT.load(DT.STATE, None), reserve_wait_s=RESERVE_WAIT_S)
    tmpl = r.config["backends"][TEMPLATE]
    for m in models:
        r.backends[name(m)] = P.HeimdallBackend(name(m), dict(tmpl, model=MODELS[m]), r.env_path)
        r.chains[f"replay110_{m}"] = [name(m)]
    return r


def _listed(d):
    return {u: (list(v) if isinstance(v, tuple) else v) for u, v in d.items()}


def _tupled(v):
    return tuple(v) if isinstance(v, list) else v


def replay_one(router, job, cap_s=CAP_S, stop_usd=STOP_USD, sleep=time.sleep):
    """One record asked of one candidate -> its row, None (rate limited or refused by the guard: no row, a re-run asks
    again; a rate limit first waits 30 s) or "stopped" (the ledger holds stop_usd: no call made)."""
    p, rec, k, anchors, m = job
    if router.spent() >= stop_usd:
        return "stopped"
    b = router.backends[name(m)]
    dl = router.effective_deadline(rec.get("role"), b, None)       # ruling 100: what a live call of this verdict gets
    row = {"record": os.path.relpath(p, WT), "type": k, "model": m, "model_id": MODELS[m], "anchors": anchors,
           "grok_recorded_at": rec.get("recorded_at"), "grok_seconds": rec.get("seconds"), "deadline_100_s": dl,
           "cap_s": cap_s}
    try:
        row["grok"] = _listed(R.decide(k, rec["text"], rec["prompt"]))
    except (ValueError, TypeError, KeyError) as e:
        row["grok"], row["grok_error"] = None, f"{type(e).__name__}: {str(e)[:160]}"
    t0 = time.time()
    router.down.pop(name(m), None)                        # a failure is never a verdict: each call is tried afresh
    try:
        rep = router.call(f"replay110_{m}", rec["prompt"], int(rec.get("max_tokens") or 2000),
                          int(rec.get("seed") or 7), system=rec.get("system"), deadline_s=cap_s)
    except P.SpendLimit:
        return None
    except P.ProviderError as e:
        if "HTTP 429" in str(e):
            sleep(30)
            return None
        # the Router's ProviderError lists each leg's reason (providers.Router.call: "every back-end unavailable:
        # [...]"); an abandoned call's says "abandoned at the deadline", as ruling 85.1's table reads it. The timeout
        # test runs the Router's own abandonment, so a change in that wording fails it.
        row.update(seconds=round(time.time() - t0, 2), heimdall=None, heimdall_error=f"{type(e).__name__}: "
                   f"{str(e)[:200]}", outcome="timeout" if "abandoned at the deadline" in str(e) else "error")
        return row
    except Exception as e:                            # noqa: BLE001  a call that failed in a way the Router does not
        row.update(seconds=round(time.time() - t0, 2), heimdall=None,   # name (00:46 ET Nov 15: a reply cut
                   heimdall_error=f"{type(e).__name__}: {str(e)[:200]}", outcome="error")   # mid-body) is an ERROR
        return row                                    # row, never the end of the model's run
    secs = round(rep.seconds or (time.time() - t0), 2)
    row.update(seconds=secs, cached=bool(rep.cached), usd_reported=(rep.usage or {}).get("usd_reported"),
               usd_estimate=rep.usd, out_tokens=(rep.usage or {}).get("out"))
    try:
        row["heimdall"] = _listed(R.decide(k, rep.text, rec["prompt"]))
    except (ValueError, TypeError, KeyError) as e:
        row.update(heimdall=None, heimdall_error=f"out of contract: {type(e).__name__}: {str(e)[:160]}",
                   outcome="out_of_contract")
        router.reject(rep)
        return row
    row["outcome"] = "in_time" if dl is None or secs <= dl else "late"
    if row.get("grok") is not None:
        row["compare"] = {u: R.compare(k, _tupled(g), _tupled(row["heimdall"].get(u))) for u, g in row["grok"].items()}
    return row


def run(args):
    os.makedirs(os.path.join(OUT, "replies"), exist_ok=True)
    res_path = os.path.join(OUT, "RESULTS.jsonl")
    done = set()
    if os.path.exists(res_path):
        with open(res_path) as f:
            for line in f:
                try:
                    x = json.loads(line)
                    done.add((x["record"], x["model"]))
                except (ValueError, KeyError):
                    pass
    recs, missing = source_records()
    if args.limit:
        recs = recs[:args.limit]
    models = [m for m in args.models if m in MODELS]
    router = build_router(models, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND,
                          deadline_log=os.path.join(OUT, "DEADLINES.jsonl"))
    order, by_type = [], {}                            # round-robin by verdict type: an early table covers them all
    for x in recs:
        by_type.setdefault(x[2], []).append(x)
    while any(by_type.values()):
        for k in list(by_type):
            if by_type[k]:
                order.append(by_type[k].pop(0))
    jobs = [(p, r, k, a, m) for (p, r, k, a) in order for m in models if (os.path.relpath(p, WT), m) not in done]
    print(f"replay110: {len(recs)} records ({len(missing)} unreadable), {len(models)} models, {len(jobs)} calls to "
          f"make ({len(done)} already in RESULTS); stop at ${STOP_USD:.2f} vendor-reported", flush=True)
    lock, n = threading.Lock(), {"done": 0, "stopped": 0, "no_row": 0}

    def one(job):
        row = replay_one(router, job)
        with lock:
            if row == "stopped":
                n["stopped"] += 1
            elif row is None:
                n["no_row"] += 1
            else:
                with open(res_path, "a") as f:
                    f.write(json.dumps(row) + "\n")
            n["done"] += 1
            if n["done"] % 10 == 0 or n["done"] == len(jobs):
                print(f"  {n['done']}/{len(jobs)} at {time.strftime('%H:%M:%S')}, ${router.spent():.4f} spent", flush=True)

    def per_model(m):                                  # one pool per model: a slow model never starves the other
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(one, [j for j in jobs if j[4] == m]))
    ts = [threading.Thread(target=per_model, args=(m,)) for m in models]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    print(f"replay110: {n['stopped']} not started (the ${STOP_USD:.2f} stop), {n['no_row']} without a row (rate "
          f"limited or refused by the guard: a re-run asks them again)", flush=True)
    table()


def _pct(xs, q):
    return DT.percentile(xs, q) if xs else None


def _s(x):
    return "-" if x is None else f"{x:.0f}"


def summary(rows):
    """-> {(type, model): figures} over the rows (one per record and model)."""
    out = {}
    for k in R.DECIDING:
        for m in MODELS:
            rs = [r for r in rows if r["type"] == k and r["model"] == m]
            if not rs:
                continue
            by = {o: [r for r in rs if r.get("outcome") == o] for o in OUTCOMES}
            cin = [c for r in by["in_time"] for c in (r.get("compare") or {}).values()]
            call = [c for r in rs for c in (r.get("compare") or {}).values()]
            secs = [r["seconds"] for r in rs if r.get("outcome") in ("in_time", "late", "out_of_contract")
                    and isinstance(r.get("seconds"), (int, float))]
            out[(k, m)] = {
                "records": len(rs), **{o: len(v) for o, v in by.items()},
                "missed": len(by["late"]) + len(by["timeout"]),
                "units_in_time": len(cin), **{x: cin.count(x) for x in ("agree", "stricter", "looser", "different")},
                "agree_in_time_pct": 100 * cin.count("agree") / len(cin) if cin else None,
                "units_all": len(call), "agree_all_pct": 100 * call.count("agree") / len(call) if call else None,
                "p50_s": _pct(secs, 0.5), "p90_s": _pct(secs, 0.9),
                "deadline_100_s": sorted({r.get("deadline_100_s") for r in rs}, key=str),
                "usd_reported": round(sum(float(r["usd_reported"]) for r in rs if P._num(r.get("usd_reported"))
                                          and not r.get("cached")), 6)}
    return out


def incumbent(records):
    """Ruling 85.1's own rows for the deepseek-v4.1-flash we run, on the same records (its run: 300 s cut, 01:06 ET
    Nov 14, under the 429 storms of that night) -> {type: figures}."""
    out = {}
    try:
        with open(SOURCE) as f:
            rows = [json.loads(x) for x in f if x.strip()]
    except (OSError, ValueError):
        return out
    for k in R.DECIDING:
        rs = [r for r in rows if r.get("type") == k and r.get("model") == "deepseek" and r.get("record") in records]
        if not rs:
            continue
        call = [c for r in rs for c in (r.get("compare") or {}).values()]
        secs = [r["seconds"] for r in rs if r.get("heimdall") is not None and isinstance(r.get("seconds"), (int, float))]
        out[k] = {"records": len(rs), "agree_all_pct": 100 * call.count("agree") / len(call) if call else None,
                  "p50_s": _pct(secs, 0.5), "p90_s": _pct(secs, 0.9),
                  "timeouts": sum(1 for r in rs if "abandoned at the deadline" in str(r.get("heimdall_error")))}
    return out


def table():
    rows = []
    try:
        with open(os.path.join(OUT, "RESULTS.jsonl")) as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    s = summary(rows)
    inc = incumbent({r["record"] for r in rows})
    base = R.grok_self()
    lines = ["# Ruling 110: Heimdall candidates on ruling 85.1's recorded Grok verdicts", "",
             f"Built {time.strftime('%Y-%m-%d %H:%M %Z')} from {len(rows)} (record, model) rows. "
             + "; ".join(f"{m} = {MODELS[m]}" for m in MODELS) + ". In time: answered within ruling 100's deadline "
             "for that (model, verdict role) today; late: answered after it (a MISSED deadline in production), before "
             f"the {CAP_S:.0f} s cut; timeout: no answer by the cut. Stricter: the candidate fails what Grok passed.", "",
             "| type | model | records | in time | late | timeouts | errors | out of contract | missed | units in time | "
             "agree | stricter | looser | different | agree % in time | agree % all answers | p50 s | p90 s | "
             "ruling-100 deadline s | usd reported |", "|" + "---|" * 20]
    for (k, m), x in s.items():
        lines.append(f"| {k} | {m} | {x['records']} | {x['in_time']} | {x['late']} | {x['timeout']} | {x['error']} | "
                     f"{x['out_of_contract']} | {x['missed']} | {x['units_in_time']} | {x['agree']} | {x['stricter']} | "
                     f"{x['looser']} | {x['different']} | {_s(x['agree_in_time_pct'])} | {_s(x['agree_all_pct'])} | "
                     f"{_s(x['p50_s'])} | {_s(x['p90_s'])} | {', '.join(_s(d) for d in x['deadline_100_s'])} | "
                     f"{x['usd_reported']:.4f} |")
    lines += ["", "## The deepseek-v4.1-flash we run, on the same records (ruling 85.1's rows: 300 s cut, 01:06 ET "
              "Nov 14, under that night's 429 storms)", "",
              "| type | records | agree % all answers | p50 s | p90 s | timeouts |", "|---|---|---|---|---|---|"]
    for k, x in inc.items():
        lines.append(f"| {k} | {x['records']} | {_s(x['agree_all_pct'])} | {_s(x['p50_s'])} | {_s(x['p90_s'])} | "
                     f"{x['timeouts']} |")
    lines += ["", "## The bars of rulings 85/88/96 (replay85.passes; information only: a model moves into a verdict "
              "type only by a later ruling)", ""]
    for k in R.DECIDING:
        for m in MODELS:
            if (k, m) not in s:
                continue
            ok, why, agree, med = R.passes(rows, base, k, m)
            lines.append(f"- {k} / {m}: {'MEETS THE BARS' if ok else 'not: ' + '; '.join(why)}")
    lines += ["", "## The baseline: Grok against Grok (replay85.grok_self, from every recorded Grok answer)", "",
              "| type | unit pairs | agree % |", "|---|---|---|"]
    for k in R.DECIDING:
        b = base.get(k)
        if b and b.get("pairs"):
            lines.append(f"| {k} | {b['pairs']} | {100 * b['agree'] / b['pairs']:.0f} |")
    with open(os.path.join(OUT, "TABLE.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(OUT, "SUMMARY.json"), "w") as f:
        json.dump({f"{k}|{m}": x for (k, m), x in s.items()}, f, indent=1)
    print("\n".join(lines[:4 + len(s) + 2]), flush=True)
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4, help="calls in flight per model")
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--limit", type=int, default=0, help="the first N records only (a pilot)")
    ap.add_argument("--table-only", action="store_true")
    a = ap.parse_args(argv)
    a.models = [m for m in a.models.split(",") if m]
    if a.table_only:
        table()
        return 0
    run(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
