#!/usr/bin/env python3
"""RULING 111 (orchestrator 01:52 ET Nov 15): THE V4 FORMAT RE-TRY. Ruling 110 left the v4 abliterated
(deepseek/deepseek-v4-flash-0731-abliterated) unmeasured: 136 of its 319 answers were not valid JSON. Here it is asked
in the gateway's JSON mode (response_format {"type": "json_object"}) with a set reasoning_effort, on the same 319
records (ruling 85.1's), with the same decisions, comparison and bars (replay85.decide / compare / passes) and the
same calls, deadlines, cut, rate limits and guard (replay110.replay_one).
THE GATEWAY (probed at 01:5x ET Nov 15): for this model it takes response_format json_object, response_format
json_schema and reasoning_effort, so no repair re-ask is needed. json_object is used. The contracts name each prompt's
own labels, clip keys, joins and hook ids, so a json_schema would have to be ours, made per prompt, and could steer the
answer. Every contract check stays with the pipeline's own parsers.
THE EFFORT: none and medium are both asked on the first SAMPLE records (ruling 85.1's order, which covers every
verdict type). The better is kept for all 319 by choose(): the higher valid-answer rate, then the higher agreement on
valid answers, then the lower p50. When neither effort gave a single valid answer, no full run is made. At medium the
reasoning counts against the output budget production gives every call (max_out, 16,000 tokens): an answer cut by it
is "truncated" and counts against medium, as it would in production.
OUT OF CONTRACT: each such answer's text is kept in its row ("raw_text": diagnosis only, never a verdict) and named by
shape(): empty, code fence, valid JSON that is not the contract (fields, labels or values), prose around the JSON,
truncated, invalid JSON.
SPEND: Heimdall only, on its own ledger (tests/package/proof/SPEND_R111.json, vendor-reported). No call starts once
the ledger holds STOP_USD: the order's cap of $0.40, less what calls in flight may still add. At most --workers (6)
are in flight; ruling 110 measured this model at a median $0.00006 and at most $0.0011 a call (at medium), so they
add at most about $0.007.
Usage: python3 -B tests/package/replay111.py [--workers 6] [--sample 40] [--table-only]"""
import argparse
import collections
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
import replay110 as RX  # noqa: E402

WT = R.WT
OUT = os.path.join(WT, "tests", "package", "proof", "replay111")
SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_R111.json")
LIMIT_USD, STOP_USD, SAMPLE = 3.00, 0.38, 40
MODEL = "deepseek/deepseek-v4-flash-0731-abliterated"
FORMAT = {"type": "json_object"}
VARIANTS = ("none", "medium")
PREFIX = "replay111"
SHAPES = ("empty", "code fence", "valid JSON, not the contract", "prose around the JSON", "truncated", "invalid JSON")


def bname(v):
    return f"heimdall:{MODEL}#effort-{v}"


class FormatBackend(P.HeimdallBackend):
    """providers.HeimdallBackend.complete with the same body (model, max_tokens, seed, temperature, the same messages),
    plus the gateway's JSON mode and a reasoning effort. It is copied, not inherited, because the production back-end
    builds its body inside complete(). test_replay111 pins that the two bodies differ by those two fields only."""

    def __init__(self, name, spec, env_path, effort):
        super().__init__(name, spec, env_path)
        self.effort = effort

    def complete(self, prompt, max_tokens, seed, system=None):
        key = self.key("HEIMDALL_API_KEY")
        content = prompt if not P.is_vision(prompt) else \
            [{"type": "text", "text": prompt["text"]}] + [{"type": "image_url", "image_url": {
                "url": "data:image/jpeg;base64," + i}} for i in prompt["images"]]
        body = {"model": self.model, "max_tokens": self.max_out(max_tokens), "seed": seed,
                "temperature": self.spec.get("temperature", 0),
                "messages": [{"role": "system", "content": (system or "") + " Reply with one JSON object only."},
                             {"role": "user", "content": content}],
                "response_format": FORMAT, "reasoning_effort": self.effort}
        t0 = time.time()
        base = self._base()
        j = P._with_backoff(lambda: P._http_json(base + "/chat/completions", body, {"Authorization": "Bearer " + key},
                                                 self.timeout), final_codes=(401, 402, 403))
        u = j.get("usage") or {}
        try:
            text = j["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError):
            raise P.RequestRejected("heimdall: no choices") from None
        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)},
                          **P._reported(u.get("cost"))), time.time() - t0


def build_router(variants, record_dir=None, spend_path=None, deadline_log=None):
    """replay110.build_router's Router, with one FormatBackend per effort on its own chain "replay111_<effort>"."""
    r = P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD,
                 limit_basis=RX.LIMIT_BASIS, routing="heimdall_first", deadline_log=deadline_log,
                 deadlines=DT.load(DT.STATE, None), reserve_wait_s=RX.RESERVE_WAIT_S)
    tmpl = r.config["backends"][RX.TEMPLATE]
    for v in variants:
        r.backends[bname(v)] = FormatBackend(bname(v), dict(tmpl, model=MODEL), r.env_path, v)
        r.chains[f"{PREFIX}_{v}"] = [bname(v)]
    return r


def shape(text, out_tokens=None, cap=None):
    """The shape of an answer the parsers refused -> one of SHAPES (the first that applies, in that order)."""
    t = (text or "").strip()
    if not t:
        return "empty"
    if t.startswith("```"):
        return "code fence"
    try:
        json.loads(t)
        return "valid JSON, not the contract"
    except ValueError as e:
        pos = getattr(e, "pos", None)
    a, b = t.find("{"), t.rfind("}")
    if 0 <= a < b and (a > 0 or b < len(t) - 1):
        try:
            json.loads(t[a:b + 1])
            return "prose around the JSON"
        except ValueError:
            pass
    if (cap and out_tokens and out_tokens >= cap) or t.count("{") > t.count("}") or \
            (pos is not None and pos >= len(t) - 1):
        return "truncated"
    return "invalid JSON"


def scores(rows, v):
    """One effort's figures over its rows: answers, valid answers, the valid-answer rate, the agreement on valid
    answers, p50."""
    rs = [r for r in rows if r["model"] == v]
    ans = [r for r in rs if r.get("outcome") in ("in_time", "late", "out_of_contract")]
    ok = [r for r in ans if r.get("outcome") in ("in_time", "late")]
    cmp_ = [c for r in ok for c in (r.get("compare") or {}).values()]
    secs = [r["seconds"] for r in ans if isinstance(r.get("seconds"), (int, float))]
    return {"rows": len(rs), "answers": len(ans), "valid": len(ok),
            "valid_rate": len(ok) / len(ans) if ans else 0.0,
            "agree_valid": cmp_.count("agree") / len(cmp_) if cmp_ else 0.0,
            "p50_s": statistics.median(secs) if secs else None}


def choose(rows, variants=VARIANTS):
    """-> (the better effort, {effort: scores}): the higher valid-answer rate, then the higher agreement on valid
    answers, then the lower p50. None when no effort gave a single valid answer (no full run is worth making)."""
    sc = {v: scores(rows, v) for v in variants}
    best = max(variants, key=lambda v: (round(sc[v]["valid_rate"], 9), round(sc[v]["agree_valid"], 9),
                                        -(sc[v]["p50_s"] if sc[v]["p50_s"] is not None else float("inf"))))
    return (best if sc[best]["valid"] else None), sc


def anchor_failures(rows):
    """Every anchor decision (a delivered pin's own clip, line-up or line: replay85.anchor_units) Grok passed and the
    candidate failed -> [{"record", "type", "model", "unit", "pins"}]."""
    anchors, out = R.anchor_texts(), []
    for r in rows:
        for u, pins in R.anchor_units(r, anchors).items():
            if (r.get("compare") or {}).get(u) == "stricter":
                out.append({"record": r["record"], "type": r["type"], "model": r["model"], "unit": u, "pins": pins})
    return out


def ask_one(router, job, names, cap_s=RX.CAP_S):
    """One record asked of one effort as this order asks it: replay110.replay_one on the effort's own chain, with
    this order's stop (STOP_USD) and every out-of-contract text kept."""
    return RX.replay_one(router, job, cap_s=cap_s, stop_usd=STOP_USD, keep_raw=True, names=names, prefix=PREFIX)


def _pct(n, d):
    return f"{100 * n / d:.0f}%" if d else "-"


def _p(v):
    return "-" if v is None else f"{v:.0f}%"


def _rows(path):
    rows = []
    try:
        with open(path) as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return rows


def run(args):
    os.makedirs(os.path.join(OUT, "replies"), exist_ok=True)
    res_path = os.path.join(OUT, "RESULTS.jsonl")
    recs, missing = RX.source_records()
    router = build_router(VARIANTS, record_dir=os.path.join(OUT, "replies"), spend_path=SPEND,
                          deadline_log=os.path.join(OUT, "DEADLINES.jsonl"))
    names, lock = {v: bname(v) for v in VARIANTS}, threading.Lock()

    def ask(jobs, label):
        n = {"done": 0, "stopped": 0, "no_row": 0}

        def one(job):
            row = ask_one(router, job, names)
            with lock:
                if row == "stopped":
                    n["stopped"] += 1
                elif row is None:
                    n["no_row"] += 1
                else:
                    if row.get("outcome") == "out_of_contract":
                        cap = router.backends[names[job[4]]].max_out(int(job[1].get("max_tokens") or 2000))
                        row["shape"] = shape(row.get("raw_text"), row.get("out_tokens"), cap)
                    with open(res_path, "a") as f:
                        f.write(json.dumps(row) + "\n")
                n["done"] += 1
                if n["done"] % 20 == 0 or n["done"] == len(jobs):
                    print(f"  {label}: {n['done']}/{len(jobs)} at {time.strftime('%H:%M:%S')}, "
                          f"${router.spent():.4f} spent", flush=True)
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(one, jobs))
        print(f"replay111 {label}: {n['stopped']} not started (the ${STOP_USD:.2f} stop), {n['no_row']} without a row",
              flush=True)

    def done():
        return {(x["record"], x["model"]) for x in _rows(res_path) if "record" in x and "model" in x}

    sample = recs[:args.sample]
    seen = done()
    ask([(p, r, k, a, v) for (p, r, k, a) in sample for v in VARIANTS if (os.path.relpath(p, WT), v) not in seen],
        f"the sample ({len(sample)} records x {len(VARIANTS)} efforts)")
    keys = {os.path.relpath(p, WT) for p, _, _, _ in sample}
    best, sc = choose([x for x in _rows(res_path) if x.get("record") in keys])
    with open(os.path.join(OUT, "CHOICE.json"), "w") as f:
        json.dump({"best": best, "sample_records": len(sample), "scores": sc,
                   "rule": "the higher valid-answer rate, then the higher agreement on valid answers, then the lower p50"},
                  f, indent=1)
    if best is None:
        print(f"replay111: no effort gave a valid answer on the sample: no full run ({json.dumps(sc)})", flush=True)
        table()
        return
    print(f"replay111: effort {best} kept ({json.dumps(sc)})", flush=True)
    seen = done()
    ask([(p, r, k, a, best) for (p, r, k, a) in recs if (os.path.relpath(p, WT), best) not in seen],
        f"all {len(recs)} records on effort {best}")
    table()


SOURCE_110 = os.path.join(RX.OUT, "RESULTS.jsonl")
CUT_NOTE = "each call cut at 300 s (replay110)."


def table():
    rows = _rows(os.path.join(OUT, "RESULTS.jsonl"))
    try:
        with open(os.path.join(OUT, "CHOICE.json")) as f:
            choice = json.load(f)
    except (OSError, ValueError):
        choice = {}
    best = choice.get("best")
    keys = {r["record"] for r in rows if r.get("model") == best} if best else set()
    sample_keys = None
    if choice.get("sample_records"):
        recs, _ = RX.source_records()
        sample_keys = {os.path.relpath(p, WT) for p, _, _, _ in recs[:choice["sample_records"]]}
    full = [r for r in rows if r.get("model") == best]
    s = RX.summary(full, models=[best]) if best else {}
    old = RX.summary([r for r in _rows(SOURCE_110) if r.get("model") == "dsv4" and r.get("record") in keys],
                     models=["dsv4"])
    base = R.grok_self()
    lines = ["# Ruling 111: the v4 abliterated in the gateway's JSON mode", "",
             f"Built {time.strftime('%Y-%m-%d %H:%M %Z')}. {MODEL}, response_format {json.dumps(FORMAT)}, "
             f"reasoning_effort {best}. Ruling 85.1's records; ruling 100's deadline (the gateway's 120 s); "
             f"{CUT_NOTE}", "",
             "## The effort, on the sample (the first records in ruling 85.1's order)", "",
             "| effort | rows | answers | valid | valid-answer rate | agreement on valid answers | p50 s |",
             "|---|---|---|---|---|---|---|"]
    for v, x in (choice.get("scores") or {}).items():
        lines.append(f"| {v}{' (kept)' if v == best else ''} | {x['rows']} | {x['answers']} | {x['valid']} | "
                     f"{100 * x['valid_rate']:.0f}% | {100 * x['agree_valid']:.0f}% | {RX._s(x['p50_s'])} |")
    if not best:
        lines += ["", "## No full run: no effort gave a single valid answer on the sample"]
    lines += ["", f"## All {len(keys)} records, effort {best} (ruling 110's columns, then the two this order adds)", "",
              "| type | records | in time | late | timeouts | errors | out of contract | missed | units in time | agree | "
              "stricter | looser | different | agree % in time | p50 s | p90 s | usd reported | VALID-ANSWER RATE | "
              "AGREEMENT ON VALID ANSWERS | ruling 110 (no JSON mode): valid-answer rate / agreement |", "|" + "---|" * 20]
    for (k, m), x in s.items():
        ans = x["in_time"] + x["late"] + x["out_of_contract"]
        o = old.get((k, "dsv4")) or {}
        oans = o.get("in_time", 0) + o.get("late", 0) + o.get("out_of_contract", 0)
        lines.append(f"| {k} | {x['records']} | {x['in_time']} | {x['late']} | {x['timeout']} | {x['error']} | "
                     f"{x['out_of_contract']} | {x['missed']} | {x['units_in_time']} | {x['agree']} | {x['stricter']} | "
                     f"{x['looser']} | {x['different']} | {_p(x['agree_in_time_pct'])} | {RX._s(x['p50_s'])} | "
                     f"{RX._s(x['p90_s'])} | {x['usd_reported']:.4f} | {_pct(x['in_time'] + x['late'], ans)} | "
                     f"{_p(x['agree_all_pct'])} | {_pct(o.get('in_time', 0) + o.get('late', 0), oans)} / "
                     f"{_p(o.get('agree_all_pct'))} |")
    bad = [r for r in full if r.get("outcome") == "out_of_contract"]
    shapes = collections.Counter(r.get("shape") or "unclassified" for r in bad)
    lines += ["", f"## Out of contract: {len(bad)} answers (texts in RESULTS.jsonl and OUT_OF_CONTRACT.jsonl)", ""]
    lines += [f"- {n} {sh}" for sh, n in shapes.most_common()] or ["- none"]
    for k in R.DECIDING:
        per = collections.Counter(r.get("shape") for r in bad if r["type"] == k)
        if per:
            lines.append(f"  - {k}: " + ", ".join(f"{n} {sh}" for sh, n in per.most_common()))
    fails = anchor_failures(full)
    lines += ["", f"## Anchor decisions Grok passed that it failed: {len(fails)}", ""]
    lines += [f"- {x['type']} {x['record']} unit {x['unit']} (pins {', '.join(x['pins'])})" for x in fails] or ["- none"]
    lines += ["", "## The bars of rulings 85/88/96, per verdict type (replay85.passes)", ""]
    bars = {}
    for k in R.DECIDING:
        if (k, best) not in s:
            continue
        ok, why, agree, med = R.passes(full, base, k, best)
        bars[k] = {"meets": ok, "why": why}
        lines.append(f"- {k}: {'MEETS THE BARS' if ok else 'DOES NOT: ' + '; '.join(why)}")
    with open(os.path.join(OUT, "TABLE.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(OUT, "OUT_OF_CONTRACT.jsonl"), "w") as f:
        for r in bad:
            f.write(json.dumps({k_: r.get(k_) for k_ in ("record", "type", "model", "heimdall_error", "shape",
                                                        "out_tokens", "raw_text")}) + "\n")
    with open(os.path.join(OUT, "SUMMARY.json"), "w") as f:
        json.dump({"choice": choice, "sample_keys": len(sample_keys or ()),
                   "table": {f"{k}|{m}": x for (k, m), x in s.items()}, "shapes": dict(shapes),
                   "anchor_failures": fails, "bars": bars}, f, indent=1)
    print("\n".join(lines), flush=True)
    return s, shapes, fails, bars


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6, help="calls in flight")
    ap.add_argument("--sample", type=int, default=SAMPLE, help="the records both efforts are asked first")
    ap.add_argument("--table-only", action="store_true")
    a = ap.parse_args(argv)
    if a.table_only:
        table()
        return 0
    run(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
