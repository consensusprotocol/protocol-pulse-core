#!/usr/bin/env python3
"""pipeline/oracle/ab.py — blind A/B of every model role on saved data (law L-x, orchestrator note 02:45 ET).

judge / witness / grouping   the EXACT prompts already sent (judge_L<k>_prompt.txt, witness_L<k>_prompt.txt,
                             group_prompt.txt) are replayed on each back-end; the reply is parsed by the role's own
                             strict parser and compared with the reference verdict recorded for that prompt. The judge
                             also gets one development swap per run (_swap): a line-up of the windows-HARD run that
                             the reference judge passed under this exact prompt, its last clip replaced by a clip of the
                             least-related development of the same run that gives a valid swap (blind grouping; the
                             pairs in order of canonical-word overlap, at most 20 %); every deterministic check must still pass with the
                             windows hard, so rule 1 (one development) is the only rule it breaks by construction. It
                             counts as caught only when the judge fails it ON rule 1 (audit F5: the first swaps were
                             built from windows-as-targets line-ups and could fail on the windows instead; withdrawn).
writer                       one saved day re-run per back-end (pipeline/oracle/run.py, the order's rule set) with the
                             judge fixed; quality = accepted / sentence-disjoint line-ups, failures, latency, dollars.
A back-end never judges what its own vendor wrote (the writer of every saved line-up is read from its artefacts).
Per back-end: quality, failures (malformed / empty replies, vendor errors), median latency, dollars per call (frontier:
the provider config's price table; Heimdall: the cost the gateway reports for that call; local: 0, run under the GPU0
lease by the integrator only).
"""
import copy
import glob
import json
import os
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from pipeline.oracle import lineup as L
from pipeline.oracle import llm
from pipeline.oracle import prompts as P
from pipeline.oracle import providers as PV
from pipeline.oracle import run as R
from pipeline.oracle import witness as W


def _split(path):
    t = open(path, encoding="utf-8").read()
    sys_, user = t.split("\n\nUSER:\n", 1)
    return sys_.replace("SYSTEM:\n", "", 1), user


SWAP = "/swap_hard"                   # item id suffix of the development swaps
WITHDRAWN = "/mustfail"               # the first, confounded swaps (audit F5): never counted


def is_swap(item):
    return item.endswith(SWAP)


def judge_items(out_root, stamps):
    """[(item id, system, user, expected verdict, arg)] for the judge: every recorded verdict of the order's rule set,
    plus one development swap per run where the blind grouping of the windows-hard run found two developments."""
    items = []
    for st in stamps:
        d = os.path.join(out_root, st)
        for jp in sorted(glob.glob(os.path.join(d, "JUDGE_L*.json"))):
            j = json.load(open(jp, encoding="utf-8"))
            k = j["lineup"]
            if j.get("status") != "OK":
                continue
            sys_, user = _split(os.path.join(d, f"judge_L{k}_prompt.txt"))
            items.append((f"{st}/L{k}", sys_, user, j["verdict"], L.JUDGE_CHECKS))
        items += _swap(d, st)
    return items


SWAP_MAX_OVERLAP = 0.2       # a swap is built only between developments sharing at most 20 % of their words


def _overlap(a, b):
    import canon                 # flat, one copy per process (pipeline/oracle/__init__.py)
    x, y = set(canon.canon_tokens(a)), set(canon.canon_tokens(b))
    return len(x & y) / max(1, len(x | y))


def _swap(d, st):
    """[] or [one development-swap item]; arg carries the checks, the rule the swap must fail and its provenance."""
    from pipeline.oracle import export as X
    vdir = os.path.join(d, "same_dev_hard_max")
    if not os.path.exists(os.path.join(vdir, "DAY.json")):
        return []
    with open(os.path.join(vdir, "DAY.json"), encoding="utf-8") as f:
        day = json.load(f)
    groups = day.get("development_groups") or []
    if len(groups) < 2:
        return []
    with open(os.path.join(vdir, "ORACLE.json"), encoding="utf-8") as f:
        lus = json.load(f)["lineups"]
    passed = {r["lineup"] for r in day["lineups"] if r["accepted"]}
    rows = {r["id"]: r for r in X.read_rows(os.path.join(d, f"BITCOIN_STATEMENTS_{st}.jsonl"))}
    with open(os.path.join(d, f"BITCOIN_STATEMENTS_{st}.manifest.json"), encoding="utf-8") as f:
        now = json.load(f)["started"]
    pairs = sorted(((_overlap(ga["development"], gb["development"]), i, j)
                    for i, ga in enumerate(groups) for j, gb in enumerate(groups) if i != j))
    for ov, i, j in pairs:                       # least-overlapping pair first; the first whose swap passes every
        if ov > SWAP_MAX_OVERLAP:                 # deterministic check; never between near-identical developments
            break
        base_k = min((k for k in groups[i]["lineups"] if k in passed), default=None)
        if base_k is None:
            continue
        base = lus[base_k - 1]
        for donor_k in sorted(k for k in groups[j]["lineups"] if k in passed):
            for clip in lus[donor_k - 1]["clips"]:
                lu = copy.deepcopy(base)
                lu["clips"][-1] = clip
                bad, _ = L.check(lu, rows, windows_hard=True)
                if bad:
                    continue
                meta = {"base_lineup": base_k, "base_development": groups[i]["development"], "donor_lineup": donor_k,
                        "donor_development": groups[j]["development"], "overlap": round(ov, 3),
                        "base_passed_this_prompt": True}
                return [(f"{st}{SWAP}", P.JUDGE_SYSTEM, P.judge_prompt(lu, rows, now), "ILLEGAL",
                         {"checks": L.JUDGE_CHECKS, "must_fail_on": "one_development_two_channels", "meta": meta})]
    return []


def recorded_items(out_root, stamps, role):
    """[(item id, system, user, reference, parser arg)] for witness / grouping from their saved prompts."""
    items = []
    for st in stamps:
        if role == "witness":
            vdir = os.path.join(out_root, st, "moments")
            w = json.load(open(os.path.join(vdir, "WITNESS.json"), encoding="utf-8")) if os.path.exists(
                os.path.join(vdir, "WITNESS.json")) else {"lineups": []}
            for x in w["lineups"]:
                if x.get("status") == "OK":
                    sys_, user = _split(os.path.join(vdir, f"witness_L{x['lineup']}_prompt.txt"))
                    items.append((f"{st}/W{x['lineup']}", sys_, user, x["verdict"], len(x["verdict"]["segments"])))
        else:
            for sub in ("", "same_dev"):
                vdir = os.path.join(out_root, st, sub) if sub else os.path.join(out_root, st)
                g = os.path.join(vdir, "GROUPS.json")
                if os.path.exists(g) and os.path.exists(os.path.join(vdir, "group_prompt.txt")):
                    rec = json.load(open(g, encoding="utf-8"))
                    if rec.get("status") == "OK":
                        sys_, user = _split(os.path.join(vdir, "group_prompt.txt"))
                        items.append((f"{st}/{sub or 'order'}", sys_, user, rec["groups"], len(rec["accepted"])))
    return items


def _agree(role, parsed, ref, arg=None):
    if role == "judge":
        on = arg.get("must_fail_on") if isinstance(arg, dict) else None
        return parsed["verdict"] == ref and (on is None or on in parsed["failed"])
    if role == "witness":
        return parsed["verdict"] == ref["verdict"]
    canon = lambda gs: sorted(sorted(g["lineups"]) for g in gs)
    return canon(parsed) == canon(_renumber(ref))


def _renumber(groups):
    """Reference groups name line-ups by their oracle numbers; the grouping prompt numbers them 1..n in order."""
    order = sorted(k for g in groups for k in g["lineups"])
    pos = {k: i + 1 for i, k in enumerate(order)}
    return [{"lineups": sorted(pos[k] for k in g["lineups"])} for g in groups]


def _parse(role, text, arg):
    if role == "judge":
        return L.parse_judge(text, arg["checks"] if isinstance(arg, dict) else arg)
    if role == "witness":
        return W.parse(text, arg)
    return R.parse_groups(text, arg)


SCHEMAS = {"judge": L.JUDGE_SCHEMA, "witness": W.SCHEMA, "grouping": R.GROUP_SCHEMA}


PASSING, FAILING = ("LEGAL", "PASS"), ("ILLEGAL", "FAIL")


def lenient(r):
    """The back-end passed what the reference failed: the error a fail-closed gate cannot afford."""
    ref = r.get("reference", r.get("expected"))
    return r.get("status") == "OK" and r.get("verdict") in PASSING and ref in FAILING


def strict(r):
    """The back-end failed what the reference passed: costs supply, never safety."""
    ref = r.get("reference", r.get("expected"))
    return r.get("status") == "OK" and r.get("verdict") in FAILING and ref in PASSING


def _one(role, name, item, ledger, stop, notify_dir=None):
    """One item on one back-end: its row. Seconds and dollars are kept even when the reply then fails to parse."""
    iid, sys_, user, ref, arg = item
    r = {"item": iid, "expected": ref if role == "judge" else None,
         "reference": ref if role == "judge" else ref["verdict"] if role == "witness" else len(ref)}
    if isinstance(arg, dict) and arg.get("meta"):
        r["swap"] = dict(arg["meta"], must_fail_on=arg["must_fail_on"])
    if stop.is_set():
        r.update(status="FAILED", error="not sent: the spend guard was reached")
        return r
    try:
        text, raw, use = PV.call_backend(name, sys_, user, SCHEMAS[role], ledger, f"ab {role} {iid}", notify_dir)
        r.update(seconds=use["seconds"], usd=use.get("usd") or 0.0, usd_source=use.get("usd_source"))
        parsed = _parse(role, text, arg)
        r.update(status="OK", agree=_agree(role, parsed, ref, arg),
                 verdict=parsed.get("verdict") if isinstance(parsed, dict) else len(parsed))
        if role == "judge":
            r["failed_checks"] = parsed["failed"]
    except Exception as e:                                  # malformed / empty reply, vendor error, guard: a failure
        r.update(status="FAILED", error=llm.redact(f"{type(e).__name__}: {e}")[:300])
        if type(e).__name__ == "SpendStop":
            stop.set()
    return r


def not_sent(r):
    """The spend guard stopped this item before (or as) it was sent: not measured, and not a quality failure."""
    e = r.get("error") or ""
    return r.get("status") != "OK" and (e.startswith("not sent") or e.startswith("SpendStop")
                                        or e.startswith("VendorDown: HEIMDALL SPEND AT 90%"))


def summarize(rows):
    """One back-end's summary from its item rows. 'failed' = sent and no usable reply (malformed, empty, vendor
    error); 'not_sent' = stopped by the spend guard (not measured). Dollars count every paid call, failed ones too."""
    done = [r for r in rows if r["status"] == "OK"]
    mf = [r for r in done if is_swap(r["item"])]
    lat = [r["seconds"] for r in rows if r.get("seconds") is not None]
    held = sum(1 for r in rows if not_sent(r))
    return {"items": len(rows), "measured": len(done), "not_sent": held, "failed": len(rows) - len(done) - held,
            "agree": sum(r["agree"] for r in done),
            "more_lenient": sum(1 for r in done if lenient(r)), "stricter": sum(1 for r in done if strict(r)),
            "must_fail_caught": sum(r["agree"] for r in mf), "must_fail_measured": len(mf),
            "must_fail_items": sum(1 for r in rows if is_swap(r["item"])),
            "median_s": round(statistics.median(lat), 1) if lat else None,
            "usd": round(sum(r.get("usd") or 0.0 for r in rows), 6),
            "usd_source": sorted({r.get("usd_source") for r in rows} - {None}), "rows": rows}


def _combine(samples):
    """One row for an item measured more than once (independent samples of the same prompt): order never decides.
    It agrees only if EVERY sample agreed; it is lenient if ANY sample passed what the reference failed, strict if
    any failed what the reference passed (fail closed: a back-end is judged by its worst sample)."""
    if len(samples) == 1:
        return samples[0]
    row = dict(samples[0], samples=len(samples), samples_disagree=len({x.get("verdict") for x in samples}) > 1,
               agree=all(x.get("agree") for x in samples))
    pick = next((x for x in samples if lenient(x)), None) or next((x for x in samples if strict(x)), None)
    if pick is not None:
        row.update(verdict=pick["verdict"], failed_checks=pick.get("failed_checks"))
    return row


def merge(files):
    """{back-end: summary} over several AB_<role>.json batches of one role (re-runs of what a batch did not measure,
    or a second sample of the same item): per item every measured sample is combined (_combine; order never decides),
    an item with no measured sample keeps its last failure; dollars and latency count EVERY call of every batch (a
    replaced row was still paid). A failed call on an item that another sample measured is never dropped: it is
    counted in failed_resamples (the item's verdict comes from its measured samples, the failure stays visible)."""
    per, every, skipped, withdrawn, partial = {}, {}, {}, {}, set()
    for path in files:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("complete") is False:
            partial.update(n for n, r in d["results"].items() if "skipped" not in r)
        for name, r in d["results"].items():
            if "skipped" in r:
                skipped.setdefault(name, r)
                continue
            items = per.setdefault(name, {})
            every.setdefault(name, []).extend(r["rows"])          # paid calls count even when withdrawn
            for row in r["rows"]:
                if row["item"].endswith(WITHDRAWN):
                    withdrawn[name] = withdrawn.get(name, 0) + 1
                    continue
                slot = items.setdefault(row["item"], {"ok": [], "last": None, "failed": 0})
                if row["status"] == "OK":
                    slot["ok"].append(row)
                else:
                    slot["last"] = row
                    slot["failed"] += 0 if not_sent(row) else 1
    out = {}
    for name, items in per.items():
        rows = [_combine(v["ok"]) if v["ok"] else v["last"] for v in items.values()]
        sm = summarize(rows)
        lat = [r["seconds"] for r in every[name] if r.get("seconds") is not None]
        sm.update(usd=round(sum(r.get("usd") or 0.0 for r in every[name]), 6), calls_paid=sum(
            1 for r in every[name] if r.get("seconds") is not None),
                  median_s=round(statistics.median(lat), 1) if lat else None,
                  usd_source=sorted({r.get("usd_source") for r in every[name]} - {None}), batches=len(files),
                  withdrawn=withdrawn.get(name, 0), partial=name in partial,
                  failed_resamples=sum(v["failed"] for v in items.values() if v["ok"]),
                  sampled_twice=sum(1 for r in rows if (r.get("samples") or 1) > 1),
                  samples_disagree=sum(1 for r in rows if r.get("samples_disagree")))
        out[name] = sm
    out.update({n: r for n, r in skipped.items() if n not in out})
    return out


def run_role(role, items, backends, ledger, out_dir, writer_vendors, limit=None, parallel=8):
    """AB_<role>.json: per back-end, every item's outcome and the summary. writer_vendors: every vendor that wrote
    the line-ups these items judge (read from the artefacts); a back-end of one of them is skipped."""
    os.makedirs(out_dir, exist_ok=True)
    res = {}
    for name in backends:
        ok, why = PV.available(name, avoid_vendors=set(writer_vendors), notify_dir=out_dir)
        if not ok:
            res[name] = {"skipped": why}
    todo = [(name, it) for it in items[:limit] for name in backends if name not in res]   # back-ends interleaved
    stop, lock, done_rows = threading.Event(), threading.Lock(), []

    def save(complete):
        out = dict(res)
        for name in [b for b in backends if b not in res]:
            out[name] = summarize([r for n, r in done_rows if n == name])
        path = os.path.join(out_dir, f"AB_{role}.json")
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"role": role, "items": len(items[:limit]), "complete": complete,
                       "rows_done": len(done_rows), "rows_planned": len(todo), "results": out}, f, indent=1,
                      default=str)
        os.replace(path + ".tmp", path)
        return out

    with ThreadPoolExecutor(parallel) as ex:          # every finished item is saved at once: a stopped batch keeps
        futs = {ex.submit(_one, role, n, it, ledger, stop, out_dir): n for n, it in todo}   # what it measured
        for fut in as_completed(futs):
            with lock:
                done_rows.append((futs[fut], fut.result()))
                save(False)
    order = {it[0]: i for i, it in enumerate(items[:limit])}
    done_rows.sort(key=lambda x: order[x[1]["item"]])
    return save(True)
