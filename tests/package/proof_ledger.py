#!/usr/bin/env python3
"""ORCHESTRATOR 22:40 ruling 2: build the medley from the INGEST LEDGER and seal a pin.

- The rows are pp-ingest's adapter (best_unused_moments), read-only.
- Only rows on a sentence-ready WORD record are used, each re-anchored by its text (pipeline/ledger_build.py). That
  is the store's full-video record, or else the integrator's word-pass WINDOW record (moments/word_pass.jsonl,
  --word-pass), whose L-s context comes from the caption record the ledger mined.
- "now" is the RENDER clock (ruling 1): L-v 3 and currency are judged against tonight, not against a universe snapshot.
- Novelty (L-p): every clip span of the pins already delivered (--delivered, required; tonight: the 37c5b5f5 review,
  run 165629, and the 41f29b1f medley) is passed to package.usable as delivered. usable drops ANY moment that overlaps
  a delivered span of the same video, whatever the pin's age, and that check alone carries L-p here. The adapter's
  delivered_ids (ledger moment ids, previous 24 h) stay empty: the delivered pins carry no ledger moment id, and an
  overlap check is stricter than an id check (audit 2315 C3 K7: grok, glm).
- "since": ruling 2's words are "best_unused_moments since the last delivered video". The default is the newest
  delivered pin's approved_at: a line mined after the last delivered package was sealed cannot be in it. --hours is
  the adapter's publish window. The pins are read BEFORE anything is written; a missing or broken pin, or a pin with
  no clip or no zoned approved_at, refuses the run (exit 2) with why (audit 2315 C2: grok, qwen, glm).
- The same legs, ledger and meters as proof_ly.py: Heimdall writes, xAI judges, scribe_v1 is the second recogniser.
  Writer calls have ruling 5's deadline; the budget is ruling 5's.
Writes tests/package/proof/ledger_<UTC stamp, to the second>/ (a run never writes into an existing one): inputs.json,
package.json, package.log, step_a.json and, on a package, MOMENTS_PIN_LEDGER.json.

Usage: python3 tests/package/proof_ledger.py --delivered PIN [PIN ...] [--since ISO] [--hours 72]
  tonight: --delivered tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json \\
                       tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
sys.path.insert(0, HERE)
import eligibility as E  # noqa: E402
import ledger_build as LB  # noqa: E402
import moments as M  # noqa: E402
import package as PK  # noqa: E402
import package_pin  # noqa: E402
import proof_ly as PL  # noqa: E402
import proof_saved_runs as PS  # noqa: E402
import providers as P  # noqa: E402
import speakers as SP  # noqa: E402

def delivered_pins(paths):
    """The pins already delivered -> (every clip span {video_id, start, end, pin} for package.usable's overlap check,
    the newest approved_at, [{path, story_id, approved_at, clips}]). Raises ValueError (or OSError / KeyError /
    TypeError) on a pin that cannot be read, has no clip, or has no zoned approved_at: never a partial delivered set."""
    if not paths:
        raise ValueError("no delivered pin named")
    spans, newest, pins = [], None, []
    for p in paths:
        try:
            with open(p) as f:
                pin = json.load(f)
            at = datetime.fromisoformat(str(pin["approved_at"]).replace("Z", "+00:00"))
            if at.tzinfo is None:
                raise ValueError("approved_at has no time zone")
            segs = pin["segments"]
            if not isinstance(segs, list) or not segs:
                raise ValueError("no clip")
            spans += [{"video_id": str(s["video_id"]), "start": float(s["start"]), "end": float(s["end"]),
                       "pin": pin["story_id"]} for s in segs]
            pins.append({"path": os.path.relpath(os.path.abspath(p), REPO), "story_id": pin["story_id"],
                         "approved_at": at.isoformat(), "clips": len(segs)})
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:       # which pin (glm C3 P2-3)
            raise ValueError(f"{p}: {type(e).__name__}: {e}") from None
        newest = at if newest is None or at > newest else newest
    return spans, newest, pins


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--delivered", nargs="+", required=True, metavar="PIN",
                    help="every pin already delivered: their clip spans are out (L-p), and 'since' defaults to the "
                         "newest one's approved_at")
    ap.add_argument("--since", help="ISO time with a zone; default: the newest delivered pin's approved_at")
    ap.add_argument("--hours", type=float, default=72.0, help="the adapter's publish window (horizon_h)")
    ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
    ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
    a = ap.parse_args(argv)
    now = datetime.now(timezone.utc)
    try:                                                 # read before anything is written (glm C2 N-4)
        delivered, last, pins = delivered_pins(a.delivered)
        since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
        if since.tzinfo is None:
            raise ValueError("--since has no time zone")
        if since > now:
            raise ValueError(f"since {since.isoformat()} is after now")
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"REFUSED: the delivered pins or 'since' cannot be read ({type(e).__name__}: {e})", file=sys.stderr)
        return 2
    out_dir = os.path.join(HERE, "proof", f"ledger_{now.strftime('%Y%m%d_%H%M%S')}")
    try:
        os.makedirs(out_dir)                     # never into an earlier run's evidence (glm C3 P2-1)
    except FileExistsError:
        print(f"REFUSED: {out_dir} exists", file=sys.stderr)
        return 2
    logf = open(os.path.join(out_dir, "package.log"), "a")
    say = lambda s: (print(s, flush=True), logf.write(s + "\n"), logf.flush())
    ctx = E.Context(now, PS.REG, ledger=PS.ledger_entries())
    say(f"=== {time.strftime('%H:%M:%S %Z')} LEDGER medley build, code {PL.code_sha()}, now (render clock) "
        f"{now.isoformat(timespec='seconds')}, since {since.isoformat(timespec='seconds')} "
        f"({'--since' if a.since else 'the newest delivered pin'}), publish window {a.hours} h")
    say(f"  delivered: {', '.join(p['story_id'] + ' (' + p['approved_at'] + ')' for p in pins)}; "
        f"{len(delivered)} clip spans out")
    rows, rep = LB.rows(since, now, horizon_h=a.hours)
    say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
    wp, wp_rep = LB.word_pass_index(a.word_pass)
    say(f"  word pass: {json.dumps(wp_rep)}")
    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp)
    inputs["word_pass"] = wp_rep
    with open(os.path.join(out_dir, "inputs.json"), "w") as f:
        json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
                   "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
                  f, indent=1, default=str)
    router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
                      chains=PL.chains())
    own, used = PL.meter(router), PL.reply_meter(router)
    t0 = time.time()
    res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
                   work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
                   spend=lambda: (own["est"], own["best"]))
    res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
               full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
               since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
    if res["package"]:
        SP.attribute_package(router, res["package"], sources, log=say)     # 00:05 ET Nov 13 item 3: sealed in the pin
        try:
            path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
                                              name="MOMENTS_PIN_LEDGER.json")
            res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
                          "package_sha256": pin["moments_package"]["package_sha256"]}
            say(f"PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known) "
                f"pin {path}")
        except package_pin.PinRefused as e:
            res["pin_refused"] = str(e)
            say(f"PIN REFUSED: {e}")
    else:
        say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
    with open(os.path.join(out_dir, "package.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    logf.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
