"""RULING 118's day keeper (orchestrator 05:40 ET Nov 16): OUTSIDE vendors' dollars today against the HARD $1.00 cap
(builds, audits, tests together), Heimdall shown beside it (free, never capped), videos sealed today and the outside cost
per sealed video. The day is proof_ly.day_ledger's: 21:10 ET to 21:10 ET (the first one is batch 4's, SPEND_B4.json).
builds = the day's ledger, split by back-end (heimdall:* apart; the unreported estimate, unsplit, counted outside);
audits = every pp-selectid audit folder whose label falls inside the day: its Grok reviews outside, the rest Heimdall;
checks = this builder's check ledgers of the day (CHECKS), split the same way; others = --other NAME=USD (outside).
Writes tests/package/proof/DAY118_LEDGER.json and prints STATE line 1's figure.
others' Heimdall spend (free, shown, never capped): --heimdall NAME=USD.
Usage: python3 -B day118.py [--other integrator=0.00] [--heimdall integrator=0.0113] [--sealed N]"""
import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
WT = REPO
sys.path[:0] = [os.path.join(WT, p) for p in ("tests/package", "pipeline", "tests/select_by_id", "tests/moments")]
import proof_ly as PL  # noqa: E402

CAP = 1.00
OUT = os.path.join(WT, "tests/package/proof/DAY118_LEDGER.json")
CHECKS = ("panel118/SPEND_P118.json",)          # ruling 118 (2)'s replay: Heimdall only


def split_ledger(path):
    """-> (outside USD, Heimdall USD) of a providers.Router spend ledger; ($0, $0) when it does not exist yet (batch 4's
    helper, moved here with this script)."""
    try:
        d = json.load(open(path))
    except OSError:
        return 0.0, 0.0
    out = heim = 0.0
    for b, v in (d.get("by_backend") or {}).items():
        usd = float(v.get("usd_reported", 0.0) or 0.0)
        if b.startswith("heimdall:"):
            heim += usd
        else:
            out += usd
    unrep = float(d.get("usd_unreported_estimate", 0.0) or 0.0)
    rows = d.get("by_backend") or {}
    if rows and all(b.startswith("heimdall:") for b in rows):   # a Heimdall-only ledger (06:31 ET Nov 16): its
        heim += unrep                                          # unreported estimate is Heimdall's, never outside
    else:
        out += unrep                                           # a mixed ledger: no vendor split, counted outside
    return out, heim


def day_bounds(now=None):
    t = (now or datetime.now(timezone.utc)).astimezone(PL.DAY_ET)
    start = t.replace(hour=PL.DAY_START[0], minute=PL.DAY_START[1], second=0, microsecond=0)
    if t < start:
        start -= timedelta(days=1)
    return start, start + timedelta(days=1)


def main(argv):
    start, end = day_bounds()
    led = PL.day_ledger()
    cap = {"SPEND_B4.json": 1.25,                        # ORDER 19:28 ET Nov 16: ADD 25 CENTS to 21:10
           "SPEND_D20261116.json": 1.40}.get(os.path.basename(led), 1.50)   # RULING 137 (3): today $1.40, then $1.50
    prev = {}
    if os.path.exists(OUT):
        prev = json.load(open(OUT))
        if prev.get("ledger") != os.path.basename(led):
            prev = {}                                    # a new day: its own figures
    others, sealed = prev.get("others") or {}, prev.get("videos_sealed")
    others_h = (prev.get("heimdall_free") or {}).get("others") or {}
    it = iter(argv)
    for a in it:
        if a == "--other":
            k, v = next(it).split("=")
            others[k] = float(v)
        elif a == "--heimdall":
            k, v = next(it).split("=")
            others_h[k] = float(v)
        elif a == "--sealed":
            sealed = int(next(it))
    b_out, b_heim = split_ledger(led)
    a_out = a_heim = 0.0
    lo, hi = start.strftime("%Y%m%d_%H%M"), end.strftime("%Y%m%d_%H%M")
    for f in sorted(glob.glob(os.path.join(WT, "docs/audits/parallel/pp-selectid_audit_2026*/COST.json"))):
        label = f.split("pp-selectid_audit_")[1].split("/")[0]
        if not lo <= label < hi:
            continue
        for r in json.load(open(f)).get("reviews") or []:
            usd = float(r.get("usd_reported", 0.0) or 0.0)
            if "grok" in r.get("review", ""):
                a_out += usd
            else:
                a_heim += usd
    c_out = c_heim = 0.0
    for c in CHECKS:
        o, h = split_ledger(os.path.join(WT, "tests/package/proof", c))
        c_out, c_heim = c_out + o, c_heim + h
    other = sum(others.values())
    s_out = 0.0                                         # the lock pre-check's ElevenLabs Scribe, per span decoded for
    for f in glob.glob("/home/ultron/protocol_pulse/data/lock_precheck/results/*.json"):   # this builder's requests
        try:                                            # (the integrator, 23:0x ET Nov 16: outside dollars; never a
            for e in json.load(open(f)):                # reused answer)
                at = datetime.fromisoformat(str(e.get("at")).replace("Z", "+00:00")) if e.get("at") else None
                if at and start <= at < end and not e.get("reused"):
                    s_out += float(e.get("scribe_usd") or 0.0)
        except (OSError, ValueError, TypeError):
            continue
    i_out, i_unpriced = 0.0, []                         # RULING 131 (the integrator's message of 09:4x ET Nov 17): its
    try:                                                # outside ledger, one line per paid call at the vendor call; its
        import importlib.util                           # pre-check Scribe lines are counted above (lock_precheck_scribe),
        spec = importlib.util.spec_from_file_location(  # so only its other services are added; loaded by path so the
            "outside_spend_main", "/home/ultron/protocol_pulse/pipeline/outside_spend.py")   # worktree's modules stay
        osp = importlib.util.module_from_spec(spec)     # first (read only)
        spec.loader.exec_module(osp)
        _, inside, unpriced = osp.total(start.isoformat(), end.isoformat())
        i_out = sum(float(d["usd"]) for d in inside
                    if d.get("service") != "lock_precheck" and isinstance(d.get("usd"), (int, float)))
        i_unpriced = [d for d in unpriced if d.get("service") != "lock_precheck"]
    except (ImportError, OSError, ValueError, AttributeError) as e:
        i_unpriced = [{"error": f"the integrator's outside ledger could not be read: {type(e).__name__}: {e}"}]
    total = b_out + a_out + c_out + other + s_out + i_out
    heim = b_heim + a_heim + c_heim + sum(others_h.values())
    sealed = sealed or 0
    rec = {"ruling": "118, orchestrator 05:40 ET Nov 16", "day": [start.isoformat(), end.isoformat()],
           "ledger": os.path.basename(led), "cap": cap, "outside": round(total, 6),
           "parts_outside": {"builds": round(b_out, 6), "audits": round(a_out, 6), "checks": round(c_out, 6),
                             "lock_precheck_scribe": round(s_out, 6),
                             "integrator_other": round(i_out, 6), "integrator_unpriced": i_unpriced,
                             "others": others},
           "heimdall_free": {"builds": round(b_heim, 6), "audits": round(a_heim, 6), "checks": round(c_heim, 6),
                             "others": others_h},
           "videos_sealed": sealed}
    json.dump(rec, open(OUT, "w"), indent=1)
    per = f"${total / sealed:.2f}" if sealed else "n/a"
    flag = f" OUTSIDE CALLS STOPPED: THE DAY'S ${cap:.2f} IS SPENT." if total >= cap else ""
    print(f"TODAY (to {end:%H:%M} ET {end:%b %d}): OUTSIDE ${total:.2f} of ${cap:.2f}{' (ORDER 19:28: ADD 25 CENTS)' if os.path.basename(led) == 'SPEND_B4.json' else ''} (builds ${b_out:.2f}, lock pre-check Scribe ${s_out:.3f}, audits "
          f"${a_out:.2f}, checks ${c_out:.2f}" + (f", others ${other:.2f}" if others else "") +
          f", the integrator's render/other ${i_out:.3f}" +
          (f", UNPRICED {len(i_unpriced)} (not counted as $0: {[d.get('vendor') or d.get('error') for d in i_unpriced][:3]})"
           if i_unpriced else "") + f"); Heimdall "
          f"${heim:.2f} free; videos sealed {sealed}; outside cost per sealed video {per}.{flag}")


if __name__ == "__main__":
    main(sys.argv[1:])
