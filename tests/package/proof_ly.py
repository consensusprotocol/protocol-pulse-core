#!/usr/bin/env python3
"""ORCHESTRATOR ORDER 20:30 ET Nov 12 (law L-y, VOICEOVER IS MINIMAL): re-run tonight's universe and the saved ones
through the packager's new default, the MEDLEY (pipeline/package.py build()). The table goes to the top of STATE:
- packages per universe;
- how many needed zero bridges and how many needed one;
- the gate pass rate on the single takeaway line;
- time and dollars per package.
The top package of the newest universe becomes a sealed pin (MOMENTS_PIN_LY.json).

LEGS (20:30: "local/Heimdall/xAI legs; Anthropic and OpenAI credit status: probe once, use if back"). The probe at
20:32 ET found Anthropic "credit balance is too low" (HTTP 400) and OpenAI 429 credit_balance_exhausted, so both stay
out. Local gemma runs on GPU0, which this builder never uses (L-r, the session's standing order), so every local leg
is out too. What is left:
- the writer (angle + takeaway) is Heimdall: deepseek-v4.1-flash, then qwen3.8-27b. This is the config's own
  angle_write order once the frozen vendors drop out.
- every verdict avoids the writer's vendor (L-x), so it runs on xAI grok-4.20.
- the second recogniser is ElevenLabs scribe_v1.
CPU and network only. The inputs are read-only: the saved runs and the main store's transcripts.

SPEND: a ledger of this order's own (tests/package/proof/SPEND_LY.json) holds the price-table estimate beside the
vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). RULING 48 (orchestrator 07:02 Nov 13):
its guard is LY_LIMIT_USD on VENDOR-REPORTED dollars, the estimate counted only for a call whose vendor reports none
(Router limit_basis="reported"); at LY_STOP_USD no new build starts (proof_ledger) and the orchestrator is told.

Usage: python3 tests/package/proof_ly.py --runs fresh_20261112_050611 ... [--table]
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
import moments as M  # noqa: E402
import package as PK  # noqa: E402
import package_pin  # noqa: E402
import proof_moments as PM  # noqa: E402
import providers as P  # noqa: E402
import speakers as SP  # noqa: E402

REPLIES = os.path.join(HERE, "fixtures", "replies")
OUT = os.path.join(HERE, "proof")
SPEND = os.path.join(OUT, "SPEND_LY.json")
LY_LIMIT_USD = 20.0                # RULING 83 (b) (20:33 Nov 13): $20.00 VENDOR-REPORTED for this order (ruling 48's
LY_LIMIT_BASIS = "reported"        # $12 before; the old $40 cap by the price-table estimate read ~12x high);
LY_STOP_USD = 16.0                 # the estimate counts only where a vendor reports none. At $16 no build starts.
                                   # Each paid call still RESERVES its price-table upper bound while in flight.
TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
DEADLINE_LOG = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_HEIMDALL_DEADLINES.jsonl")   # item 55
RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
        "fresh_20261111_192645", "fresh_20261111_190259", "fresh_20261110_093150", "fresh_20261107_080503",
        "fresh_20261107_065702", "fresh_20261106_213852")           # newest first: the first is tonight's
NEWEST = RUNS[0]
FROZEN = ("local:", "anthropic:", "openai:", "openai_stt:")         # GPU0 (never this builder's); out of credit 20:32
WRITERS = ["heimdall:deepseek/deepseek-v4.1-flash", "heimdall:qwen/qwen3.8-27b",      # ruling 5 (22:40): a writer
           "xai:grok-4.20-0309-reasoning"]       # call over 5 min fails over deepseek -> qwen -> xAI; the writes then
                                                 # stay on the angle's vendor and every verdict avoids it (L-x)
SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"


def chains():
    """Every role's configured chain without the frozen legs; the writer = two Heimdall families."""
    cfg = json.load(open(P.CONFIG))
    out = {r: [b for b in v["chain"] if not b.startswith(FROZEN)] for r, v in cfg["roles"].items()}
    out["angle_write"] = list(WRITERS)
    return out


def ledger():
    try:
        d = json.load(open(SPEND))
    except (OSError, ValueError):
        d = {}
    est = float(d.get("usd_estimate", 0.0))
    best = float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
    return est, best, d


def meter(router):
    """THIS process's own spend, from every call the router accounts (Router._settle). The shared ledger's total moves
    with the other workers too, so a per-package budget read from it would charge one universe for another's calls.
    -> {"est": price-table estimate, "best": the vendor's own figure where reported, else the estimate}."""
    import threading
    tot, lock, settle = {"est": 0.0, "best": 0.0}, threading.Lock(), router._settle

    def _settle(key, backend=None, usage=None, usd=0.0, role=""):
        settle(key, backend, usage, usd, role)
        if backend is not None:
            rep = (usage or {}).get("usd_reported")
            with lock:
                tot["est"] += float(usd or 0.0)
                tot["best"] += float(rep) if P._num(rep) else float(usd or 0.0)
    router._settle = _settle
    return tot


def reply_meter(router):
    """What the package COSTS, independent of the cache: every reply a build uses, live or served from its recording
    (the recording keeps the call's usage, estimate and latency), summed. Step A is a once-per-moment, package-
    independent screen (law L-s) kept in its own store, and it is not in this sum. -> {"est", "best", "model_s", "calls"}"""
    import threading
    tot, lock = {"est": 0.0, "best": 0.0, "model_s": 0.0, "calls": 0}, threading.Lock()
    call, transcribe = router.call, router.transcribe

    def add(r):
        rep = (r.usage or {}).get("usd_reported")
        with lock:
            tot["est"] += float(r.usd or 0.0)
            tot["best"] += float(rep) if P._num(rep) else float(r.usd or 0.0)
            tot["model_s"] += float(r.seconds or 0.0)
            tot["calls"] += 1

    def call_(*a, **k):
        r = call(*a, **k)
        add(r)
        return r

    def transcribe_(*a, **k):
        res, r = transcribe(*a, **k)
        add(r)
        return res, r
    router.call, router.transcribe = call_, transcribe_
    return tot


def code_sha():
    """The code this run used: HEAD plus the working tree's diff of pipeline/ and this driver (the results name it)."""
    head = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    diff = subprocess.run(["git", "-C", REPO, "diff", "HEAD", "--", "pipeline", "tests/package"], capture_output=True).stdout
    return f"{head}+{hashlib.sha256(diff).hexdigest()[:12]}" if diff else head


def run_one(run, router, work_dir, log, own, used=None, as_of_now=False):
    rec_m = json.load(open(os.path.join(PM.OUT, run, "moments.json")))
    words, captions, ctx, saved = PM.universe_sources(run)
    sources = {s.video_id: s for s in words}
    suffix = ""
    if as_of_now:                                       # L-v 3 against TONIGHT's clock, not the universe's: a pin
        from datetime import datetime, timezone          # rendered now must not carry 'right now' words from a
        import eligibility as E                          # source older than 24 h (step A re-judged with that date)
        ctx = E.Context(datetime.now(timezone.utc), PM.PS.REG, ledger=PM.PS.ledger_entries())
        suffix = "_now"
    e0, b0 = own["est"], own["best"]
    u0 = dict(used) if used is not None else None
    t0 = time.time()
    res = PK.build(router, rec_m["moments"], sources, ctx, delivered=(), optout=M.optout_ids(), log=log,
                   work_dir=work_dir, store=os.path.join(OUT, run, f"step_a{suffix}.json"),
                   spend=lambda: (own["est"], own["best"]))       # ruling 5: the budget reads the reported cost
    e1, b1 = own["est"], own["best"]
    res.update(run=run, seconds=round(time.time() - t0, 1), usd_estimate=round(e1 - e0, 4),
               usd_best_known=round(b1 - b0, 4), code=code_sha(), chains=router.chains,
               at=time.strftime("%Y-%m-%d %H:%M:%S %Z"), as_of=ctx.now.isoformat())
    if u0 is not None:                                   # the package's own cost, cached replies included
        res["full"] = {k: round(used[k] - u0[k], 4) for k in ("est", "best", "model_s", "calls")}
    os.makedirs(os.path.join(OUT, run), exist_ok=True)
    if res["package"]:
        pk = res["package"]
        pk["usd_best_known"] = res["usd_best_known"]
        SP.attribute_package(router, pk, sources, log=log)                # 00:05 ET Nov 13 item 3: sealed in the pin
        try:
            path, pin = package_pin.write_pin(pk, run, os.path.join(OUT, run), name=f"MOMENTS_PIN_LY{suffix.upper()}.json")
            res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
                          "package_sha256": pin["moments_package"]["package_sha256"]}
            log(f"{run}: PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best "
                f"known) pin {path}")
        except package_pin.PinRefused as e:                # recorded, never a pass; the next universe still runs
            res["pin_refused"] = str(e)
            log(f"{run}: PIN REFUSED: {e}")
    else:
        log(f"{run}: no package ({res.get('why_none')}); usable {res['usable']}, cleared "
            f"{res['prescreen']['cleared']}")
    json.dump(res, open(os.path.join(OUT, run, f"package_ly{suffix}.json"), "w"), indent=1, default=str)
    return res


def table():
    rows = ["| universe | usable / cleared step A | line-ups judged on the clips alone (passed) | package | segments, "
            "seconds of clips | bridges | takeaways: passed / judged / written (first write: passed / judged) | runtime estimate | time | "
            "$ estimate / $ best known (*) | why none |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    tot = {"universes": 0, "packages": 0, "zero": 0, "one": 0, "passed": 0, "judged": 0, "first_passed": 0,
           "first_judged": 0, "s": [], "est": [], "best": [], "framing": 0, "flagged_lineups": 0, "lineups": 0,
           "budget_stops": []}
    for run in RUNS:
        f = os.path.join(OUT, run, "package_ly.json")
        if not os.path.exists(f):
            rows.append(f"| {run} | not run | | | | | | | | | |")
            continue
        r = json.load(open(f))
        tot["universes"] += 1
        tried = [t for t in r.get("tried") or [] if t.get("medley") is not None]
        med_ok = sum(1 for t in tried if t.get("medley_ok") is True)
        if not r.get("package") and (r.get("budget_stop") or "budget" in (r.get("why_none") or "")):
            tot["budget_stops"].append(run)
        live = os.path.join(OUT, run, "package_ly_budget_stop.json")    # a LIVE build the budget stopped (kept)
        if os.path.exists(live):
            b = json.load(open(live))
            tot.setdefault("live_stops", []).append(
                f"{run}: a first live build {b.get('why_none')}; a second live build (its own angle call) is the "
                f"row above")
        tot["lineups"] += len(tried)
        tot["flagged_lineups"] += sum(1 for t in tried if t.get("medley_ok") and t["medley"].get("flagged"))
        takes = r.get("takeaways") or []
        tot["framing"] += sum(1 for x in takes if x.get("context_framing"))
        judged = [x for x in takes if x.get("passed") is not None]
        firsts = [x for x in judged if x.get("write") == 1]
        tot["passed"] += sum(1 for x in judged if x["passed"])
        tot["judged"] += len(judged)
        tot["written"] = tot.get("written", 0) + len(takes)
        tot["first_passed"] += sum(1 for x in firsts if x["passed"])
        tot["first_judged"] += len(firsts)
        pk = r.get("package")
        if pk:
            nb = 0 if not pk.get("bridge") else 1
            tot["packages"] += 1
            tot["zero" if nb == 0 else "one"] += 1
            tot["s"].append((r.get("full") or {}).get("model_s", r["seconds"]))
            tot["est"].append((r.get("full") or {}).get("est", r.get("usd_estimate") or 0.0))
            tot["best"].append((r.get("full") or {}).get("best", r.get("usd_best_known") or 0.0))
            segs = f"{len(pk['segments'])}, {sum(s['duration_s'] for s in pk['segments']):.1f} s"
            bridge = "0" if nb == 0 else f"1 ({pk['bridge']['join']}: {pk['bridge']['why']})".replace("|", "/")
            pkg, rt, why = f"YES: \"{pk['title']}\"".replace("|", "/"), f"{pk['runtime_s_estimate']} s", ""
        else:
            segs = bridge = rt = "-"
            pkg = "no"
            why = (r.get("why_none") or "; ".join(f"angle {t['angle']}: {t.get('why') or '-'}" for t in r.get("tried") or [])
                   )[:240].replace("|", "/")
        rows.append(f"| {run} | {r['usable']} / {r['prescreen']['cleared']} | {len(tried)} ({med_ok}) | {pkg} | {segs} | "
                    f"{bridge} | {sum(1 for x in judged if x['passed'])} / {len(judged)} / {len(takes)} "
                    f"({sum(1 for x in firsts if x['passed'])} / {len(firsts)}) | {rt} | "
                    + (f"{r['full']['model_s']:.0f} s of model calls ({r['full']['calls']}); this pass {r['seconds']} s | "
                       f"${r['full']['est']:.2f} / ${r['full']['best']:.3f}" if r.get("full") else
                       f"{r['seconds']} s | ${r.get('usd_estimate')} / ${r.get('usd_best_known')}") + f" | {why} |")
    n = tot["packages"]
    mean = lambda xs: (sum(xs) / len(xs)) if xs else 0.0
    _, _, d = ledger()
    summary = (f"\n**Totals:**\n"
               f"- {tot['universes']} universes run; {n} packages.\n"
               f"- Bridges: {tot['zero']} packages needed none, {tot['one']} needed one.\n"
               f"- Takeaways written: {tot.get('written', 0)}; judged by their own gates: {tot['judged']} (a write "
               f"stopped first by another gate, the runtime, the shape or a lost clip, is not judged).\n"
               f"- The takeaway line passed its gates in {tot['passed']} of {tot['judged']} judged writes "
               f"({tot['first_passed']} of {tot['first_judged']} on the first write); context-integrity failures "
               f"caused by the VO's framing, recorded beside it: {tot['framing']} writes.\n"
               f"- Line-ups judged on the clips alone: {tot['lineups']}; of those that passed, {tot['flagged_lineups']} "
               f"had one join a viewer could not follow (the bridge offered).\n"
               f"- Universes without a package because the per-package budget (05:25 item 5, twice) stopped the "
               f"search before every angle was tried: {len(tot['budget_stops'])} {tot['budget_stops'] or ''}"
               f"{'; in a LIVE build: ' + ' | '.join(tot['live_stops']) if tot.get('live_stops') else ''}.\n"
               f"- Per package (every reply its build used, cached or live; step A, a once-per-moment screen, "
               f"excluded): {mean(tot['s']):.0f} s of model calls mean, ${mean(tot['est']):.2f} estimate, "
               f"${mean(tot['best']):.2f} best known.\n"
               f"- This order's ledger: ${d.get('usd_estimate', 0):.2f} estimate; vendor-reported "
               f"${d.get('usd_reported', 0):.4f} + unreported calls' estimate ${d.get('usd_unreported_estimate', 0):.2f}.\n")
    note = ("\n(*) $ estimate: the price table's upper bound (the spend guard reads it). $ best known: the vendor's own "
            "figure where the reply carries one (xAI cost_in_usd_ticks, Heimdall usage.cost), else that call's estimate "
            "(ElevenLabs STT reports none).\n")
    text = ("# pp-selectid: the L-y medley re-run (generated by tests/package/proof_ly.py --table)\n\n" +
            "\n".join(rows) + "\n" + note + summary)
    open(TABLE, "w").write(text)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", default=list(RUNS))
    ap.add_argument("--table", action="store_true", help="only (re)write the table from the saved results")
    ap.add_argument("--work-dir", default=os.path.join(SCRATCH, "lv2"))
    ap.add_argument("--as-of-now", action="store_true", help="L-v 3 against the current clock (writes *_now files)")
    a = ap.parse_args(argv)
    if a.table:
        print(table())
        return 0
    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=LY_LIMIT_USD,
                      limit_basis=LY_LIMIT_BASIS, chains=chains(), deadline_log=DEADLINE_LOG)
    own = meter(router)
    used = reply_meter(router)
    os.makedirs(a.work_dir, exist_ok=True)
    for run in a.runs:
        os.makedirs(os.path.join(OUT, run), exist_ok=True)
        logf = open(os.path.join(OUT, run, "package_ly_now.log" if a.as_of_now else "package_ly.log"), "a")
        say = lambda s: (print(f"[{run}] {s}", flush=True), logf.write(s + "\n"), logf.flush())
        say(f"=== {time.strftime('%H:%M:%S %Z')} L-y medley build, code {code_sha()}, chains {json.dumps(router.chains)}")
        try:
            run_one(run, router, a.work_dir, say, own, used, a.as_of_now)
        except P.SpendLimit as e:
            say(f"STOPPED: {e}")
            break
        finally:
            logf.close()
    if router.notices:
        print("NOTICES:", router.notices)
    print(table())
    return 0


if __name__ == "__main__":
    sys.exit(main())
