"""RULING 131 (orchestrator 08:25 ET Nov 17): "every outside dollar your services spend (Scribe and any other) is to be
written into the day ledger the builder reads, so the day's $1.00 is one true number."

ONE append-only JSON line per paid outside call, written at the vendor call site itself (second_recogniser.scribe_words,
signoff.generate_signoff's xAI call, vo.generate_vo's TTS call), so no caller can spend without a line:
  data/spend/integrator_outside.jsonl   (runtime data, never committed)
  {"at": UTC ISO, "service": who spent it (SERVICE: "render", "lock_precheck", "replay", set by each entry point;
   "unknown" otherwise), "vendor", "usd" (None when the code cannot price the call), "basis" ("vendor-reported ..." or
   how the estimate is made), "units", "ref"}
The builder sums "usd" over its day window (total()). A ledger write that fails is printed loudly and never undoes or
hides the call's result: the money is already spent."""
import fcntl
import json
import os
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.environ.get("PP_OUTSIDE_LEDGER", os.path.join(REPO, "data", "spend", "integrator_outside.jsonl"))
SERVICE = "unknown"               # the entry point names its service (run_fresh "render", lock_precheck, replay)


def record(vendor, usd, basis, units=None, ref=None):
    """Append one paid call's line -> the line (written or not)."""
    line = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "service": SERVICE, "vendor": vendor,
            "usd": None if usd is None else round(float(usd), 6), "basis": basis, "units": units or {}, "ref": ref}
    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        with open(LEDGER, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)              # one line per write, whole, between processes
            f.write(json.dumps(line, sort_keys=True) + "\n")
    except OSError as e:
        print(f"  OUTSIDE SPEND NOT RECORDED ({type(e).__name__}: {e}): {json.dumps(line)}", flush=True)
    return line


def lines(path=None):
    """Every readable line of the ledger (a torn or foreign line is skipped)."""
    out = []
    try:
        with open(path or LEDGER) as f:
            for raw in f:
                try:
                    d = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(d, dict) and isinstance(d.get("at"), str):
                    out.append(d)
    except FileNotFoundError:
        pass
    return out


def _when(s):
    from datetime import datetime, timezone
    t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def total(since, until, path=None):
    """(USD over [since, until), the lines in it, the lines without a price) for a day window. since / until: ISO
    times with an offset (the builder's '2026-11-16T21:10:00-05:00') or UTC 'Z'. A line without a price is reported
    as unpriced, never counted as zero; a line whose time cannot be read is left out of every window."""
    a, b, inside = _when(since), _when(until), []
    for d in lines(path):
        try:
            if a <= _when(d["at"]) < b:
                inside.append(d)
        except ValueError:
            continue
    usd = sum(float(d["usd"]) for d in inside if isinstance(d.get("usd"), (int, float)))
    return round(usd, 6), inside, [d for d in inside if not isinstance(d.get("usd"), (int, float))]
