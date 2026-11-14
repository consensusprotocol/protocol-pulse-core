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

RULING 66 (13:18; its standing part ruled 14:02), A PASSED LINE-UP IS KEPT: every build first tries the due
candidates of the registry (tests/package/proof/CANDIDATES.json, seeded from the build records; pipeline/candidates.py),
newest first, inside the 8 judged line-ups (a recorded verdict is free), each as package.build(candidate=...); only when
none gives a package are angles asked, with the judged line-ups left. The registry is read (and seeded) before anything
is written and saved after the record. --from-candidate BUILD_DIR[:N] tries ONLY the line-up that passed the
clips-alone verdict in that earlier build's record (its tried[N]; default the first that passed), after the same pool
stages: its own angle, play order and seeds (package.load_candidate), so its recorded calls are served from their
recordings and only what is missing is paid for; never re-lined, swapped or a new angle.

RULING 90 (22:40 ET Nov 13; LAW since 22:52, with 91 and 92), THE SPOTLIGHT: after the medley search, every build
tries one spotlight (pipeline/spotlight.py): built when the search ends with no medley, or for a moment no medley used
(a sealed medley's clips are out of it). Its free pool goes to the clip scorer with the medley's own candidates at the
build's start (package.build's scorer_extra). A sealed spotlight is SPOTLIGHT_PIN.json in the build's directory and a
row of tests/package/proof/SPOTLIGHTS.json (one per channel per ET day).

Usage: python3 tests/package/proof_ledger.py --delivered PIN [PIN ...] [--since ISO] [--hours 72]
                                             [--from-candidate BUILD_DIR[:N]]
  tonight: --delivered tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json \\
                       tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json
"""
import argparse
import glob
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
import candidates as CA  # noqa: E402
import heimdall_health as HH  # noqa: E402
import shadow86 as SH  # noqa: E402
import ledger_build as LB  # noqa: E402
import moments as M  # noqa: E402
import package as PK  # noqa: E402
import package_pin  # noqa: E402
import proof_ly as PL  # noqa: E402
import proof_saved_runs as PS  # noqa: E402
import providers as P  # noqa: E402
import speakers as SP  # noqa: E402
import spotlight as SPOT  # noqa: E402
import lock_precheck as LP  # noqa: E402

REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
STATE_MD = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_STATE.md")   # ruling 87: a switch on line 1


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
                       "pin": pin["story_id"], "text": s.get("approved_text")} for s in segs]   # ruling 76 (b)
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
    ap.add_argument("--hours", type=float, default=package_pin.WINDOW_H,
                    help="the adapter's publish window (horizon_h); RULING 76: at most 12 h, never widened")
    ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
    ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
    ap.add_argument("--routing", choices=P.ROUTINGS, default=None,
                    help="RULING 85: 'today' or 'heimdall_first' (default: model_providers.json routing.mode)")
    ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
                    help="RULING 66: try ONLY the line-up that passed the clips-alone verdict in this earlier build's "
                         "record (its tried[N]; default the first that passed), as it was judged")
    a = ap.parse_args(argv)
    now = datetime.now(timezone.utc)
    if not 0 < a.hours <= package_pin.WINDOW_H:          # ruling 76: "rather than widen the window"
        print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {package_pin.WINDOW_H:g}]", file=sys.stderr)
        return 2
    try:                                                 # read before anything is written (glm C2 N-4)
        delivered, last, pins = delivered_pins(a.delivered)
        since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
        if since.tzinfo is None:
            raise ValueError("--since has no time zone")
        if since > now:
            raise ValueError(f"since {since.isoformat()} is after now")
        cand = None
        if a.from_candidate:                             # RULING 66: read before anything is written
            cdir, sep, idx = a.from_candidate.rpartition(":")
            cdir, idx = (cdir, idx) if sep and idx.isdigit() else (a.from_candidate, "")
            with open(os.path.join(cdir, "package.json")) as f:
                cand = PK.load_candidate(json.load(f), int(idx) if idx else None,
                                         source=os.path.relpath(os.path.abspath(cdir), REPO))
        reg = CA.new_registry()                          # RULING 66: the candidates, seeded from every build record
        if os.path.exists(REGISTRY):
            with open(REGISTRY) as f:
                reg = json.load(f)
        for p in sorted(glob.glob(os.path.join(HERE, "proof", "ledger_*", "package.json"))):
            with open(p) as f:
                CA.seed(reg, json.load(f), os.path.relpath(os.path.dirname(p), REPO))
        CA.due(reg, now)                                 # every stored time reads (audit 1420 C1), or exit 2
        pub, notes = {}, {}                              # RULING 76 (a): the open candidates' clips' publish times,
        for k, e in reg["candidates"].items():           # from the record that found them (its inputs.json holds every
            if e["state"] != "closed":                   # moment of its line-ups); unknown: expired, never fresh
                src = os.path.join(e["source"], "inputs.json")
                try:
                    with open(os.path.join(REPO, src)) as f:
                        pub.update({m["moment_id"]: m.get("published_at") for m in json.load(f).get("moments") or []
                                    if m.get("moment_id") in e["lineup"]})
                    notes[k] = f"publish times from {src}"
                except (OSError, ValueError, AttributeError, TypeError) as ex:   # audit 1810 C2: attributable
                    notes[k] = f"{src} could not be read ({type(ex).__name__}): no known publish time"
        gone = CA.expire(reg, pub, now, package_pin.WINDOW_H, notes)
        CA.registered(reg)                               # and every line-up (the search leaves them alone), or exit 2
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"REFUSED: the delivered pins, 'since', the candidate or the candidate registry cannot be read "
              f"({type(e).__name__}: {e})", file=sys.stderr)
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
        f"({'--since' if a.since else 'the newest delivered pin'}), publish window {a.hours} h" +
        (f"; RULING 66: ONLY the candidate {cand['source']} tried[{cand['index']}] {cand['lineup']}" if cand else ""))
    say(f"  delivered: {', '.join(p['story_id'] + ' (' + p['approved_at'] + ')' for p in pins)}; "
        f"{len(delivered)} clip spans out")
    say(f"  RULING 76: {len(gone)} candidate(s) expired (over {package_pin.WINDOW_H:g} h on the render clock)" +
        (f": {gone}" if gone else ""))
    rows, rep = LB.rows(since, now, horizon_h=a.hours)
    say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
    wp, wp_rep = LB.word_pass_index(a.word_pass)
    say(f"  word pass: {json.dumps(wp_rep)}")
    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp,
                                               ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"))
    inputs["word_pass"] = wp_rep
    with open(os.path.join(out_dir, "inputs.json"), "w") as f:
        json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
                   "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
                  f, indent=1, default=str)
    rt = json.load(open(P.CONFIG)).get("routing") or {}
    routing = a.routing or rt.get("mode") or "today"
    shadow = None                                # RULING 86: Grok in shadow on the first heimdall_first pins
    if routing == "heimdall_first" and SH.clean_streak() < int(rt.get("shadow_until_clean_pins") or 3):
        shadow = rt.get("shadow") or None
    router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
                      routing=routing, shadow=shadow, shadow_log=os.path.join(out_dir, "SHADOW86.jsonl"),
                      health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD)    # ruling 87
    say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
        + (f"; SHADOW (ruling 86): {shadow}" if shadow else ""))
    spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
    if spent0 >= PL.LY_STOP_USD:
        say(f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
            f"vendor reports none), at or over the ${PL.LY_STOP_USD:.2f} stop: no build starts; the orchestrator decides")
        logf.close()
        return 3
    say(f"  spend (ruling 48): ${spent0:.2f} of ${PL.LY_LIMIT_USD:.2f} vendor-reported before this build (no build "
        f"starts at ${PL.LY_STOP_USD:.2f})")
    own, used = PL.meter(router), PL.reply_meter(router)
    t0 = time.time()
    spotlit = SPOT.load_spotlit(SPOTLIGHTS)              # RULING 90: free; its pool goes to the clip scorer with the
    sp_pool, _ = SPOT.pool(moments, sources, ctx, delivered, M.optout_ids(), spotlit)   # medley's own candidates
    kw = dict(delivered=delivered, optout=M.optout_ids(), log=say, scorer_extra=sp_pool,
              work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
              spend=lambda: (own["est"], own["best"]),
              step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
              hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
              scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
              scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
              visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
              lock_check=lambda segs, n=iter(range(1, 10 ** 6)): LP.check(       # rulings 68 / 72: before any write
                  segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say))
    name, at = os.path.relpath(out_dir, REPO), now.isoformat()
    if cand is not None:                                 # --from-candidate: that candidate alone (ruling 66, 13:18)
        res = PK.build(router, moments, sources, ctx, candidate=cand, **kw)
        res["candidate_tries"] = [{"key": CA.key(cand["lineup"]), "source": cand["source"], "index": cand["index"],
                                   "fresh": bool(cand.get("write_seed")), "class": res["candidate"]["class"],
                                   "why": str(res["candidate"].get("result") or "")[:300],
                                   "judged": (res.get("search") or {}).get("lineups", 0)}]   # audit 1420 C2
    else:                                                # RULING 66 (14:02): the due candidates first, newest first
        last = {}

        def try_one(e, fresh, left):
            try:
                with open(os.path.join(REPO, e["source"], "package.json")) as f:
                    c = PK.load_candidate(json.load(f), e["index"], source=e["source"])
            except (OSError, ValueError, KeyError, TypeError) as ex:
                return None, "clip", f"it cannot be rebuilt from its record ({type(ex).__name__}: {ex})", 0
            if fresh:
                c["write_seed"] = CA.FRESH_SEED          # "then may be tried once more with fresh writes"
            say(f"  RULING 66: the candidate {e['source']} tried[{e['index']}] {e['lineup']}" +
                (" with fresh writes" if fresh else "") + f", {left} judged line-up(s) left")
            try:
                o = PK.build(router, moments, sources, ctx, candidate=c, lineups=left, **kw)
            except Exception as ex:                  # noqa: BLE001  audit 1420 C2: a build that raised is no outcome;
                say(f"  RULING 66: its build raised ({type(ex).__name__}: {str(ex)[:200]}): it stays as it was, and "
                    f"every judged line-up left is charged")              # what it spent is unknown: no more search
                return None, "budget", f"its build raised {type(ex).__name__}: {str(ex)[:200]}", left
            last["out"] = o
            return o, o["candidate"]["class"], o["candidate"].get("result"), (o.get("search") or {}).get("lineups", 0)
        res, tries, left = CA.run_due(reg, now, try_one, PK.LINEUPS_PER_BUILD, build=name)
        say(f"  RULING 66: {len(tries)} candidate(s) tried: " + "; ".join(
            f"{t['source']}[{t['index']}] {t['class']} -> {t['state']}" for t in tries) if tries else
            "  RULING 66: no candidate is due")
        if res is None and left > 0:                     # the search never re-forms a registered line-up
            res = PK.build(router, moments, sources, ctx, lineups=left, registered=CA.registered(reg), **kw)
        elif res is None:                                # every judged line-up went to candidates: no angle asked
            res = dict(last.get("out") or {"usable": None, "prescreen": {}, "tried": []}, package=None, packages=[],
                       why_none="ruling 66: the 8 judged line-ups were spent on candidates; no angle asked")
        res["candidate_tries"] = tries
    # RULING 90: the spotlight after the medley search (the medley is always tried first): built when the search
    # ends with no medley, or for a moment no medley used (a sealed medley's clips are out of it)
    sp_delivered = delivered + ([{"video_id": sg["video_id"], "start": float(sg["start"]), "end": float(sg["end"]),
                                  "pin": "this build's medley", "text": sg["text"]}
                                 for sg in res["package"]["segments"]] if res.get("package") else [])
    sp = SPOT.build(router, moments, sources, ctx, delivered=sp_delivered, optout=kw["optout"], log=say,
                    work_dir=a.work_dir, store=kw["store"], step_a_cache=kw["step_a_cache"], hook_cache=kw["hook_cache"],
                    scorer_verdicts_path=PK.SCORER_VERDICTS, visual_cache=kw["visual_cache"],
                    layout_cache=os.path.join(HERE, "proof", "LAYOUT_CACHE.json"), lock_check=kw["lock_check"],
                    spotlit=spotlit)
    res["spotlight"] = {k: sp.get(k) for k in ("package", "why_none", "finalists", "near", "moments", "pool",
                                                "scorer_waited_s", "lock_stop", "scorer")}
    try:                                                 # RULING 95: when the next qualifying episode could arrive
        res["next_attempt"] = SPOT.next_attempt(rows, wp, now)
    except Exception as e:                               # noqa: BLE001  a report, never the build
        res["next_attempt"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
               full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
               since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
    if res["package"]:
        SP.attribute_package(router, res["package"], sources, log=say)     # 00:05 ET Nov 13 item 3: sealed in the pin
        try:
            lock = LP.pin_problems(res["package"]) + \
                package_pin.window_problems(res["package"]["segments"])   # ruling 68; ruling 76 (c), render clock
            if lock:
                raise package_pin.PinRefused("; ".join(lock))
            path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
                                              name="MOMENTS_PIN_LEDGER.json")
            res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
                          "package_sha256": pin["moments_package"]["package_sha256"]}
            import shutil                                # ruling 70: each segment's sheet beside the pin
            for sg in pin["segments"]:
                sh = (sg.get("visual") or {}).get("sheet") or {}
                if sh.get("name"):
                    src = os.path.join(a.work_dir, "visual", sh["name"])
                    if os.path.exists(src):
                        shutil.copyfile(src, os.path.join(out_dir, sh["name"]))
            say(f"PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known) "
                f"pin {path}")
        except package_pin.PinRefused as e:
            res["pin_refused"] = str(e)
            say(f"PIN REFUSED: {e}")
    else:
        say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
    if sp.get("package"):                                # RULING 90: the spotlight pin, its own file
        try:
            lock = LP.pin_problems(sp["package"]) + package_pin.window_problems(sp["package"]["segments"])
            again = SPOT.load_spotlit(SPOTLIGHTS)        # one per channel per day, read again at the pin
            if again is None or any(r["channel_id"] == sp["package"]["segments"][0]["channel_id"] and
                                    r.get("day_et") == SPOT.et_day(now) for r in again):
                lock.append("ruling 90: this channel already has a spotlight today, or the record cannot be read")
            if lock:
                raise package_pin.PinRefused("; ".join(lock))
            path, pin = package_pin.write_pin(sp["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
                                              name="SPOTLIGHT_PIN.json")
            res["spotlight_pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
                                    "package_sha256": pin["moments_package"]["package_sha256"]}
            import shutil                                # ruling 70: the segment's sheet beside the pin
            sh = (pin["segments"][0].get("visual") or {}).get("sheet") or {}
            if sh.get("name") and os.path.exists(os.path.join(a.work_dir, "visual", sh["name"])):
                shutil.copyfile(os.path.join(a.work_dir, "visual", sh["name"]), os.path.join(out_dir, sh["name"]))
            sg = sp["package"]["segments"][0]
            SPOT.record_spotlit(SPOTLIGHTS, {"channel_id": sg["channel_id"], "channel": sg["channel"],
                                             "day_et": SPOT.et_day(now), "story_id": pin["story_id"],
                                             "package_sha256": pin["moments_package"]["package_sha256"],
                                             "at": now.isoformat(timespec="seconds"), "build": name})
            say(f"SPOTLIGHT PIN {path} ({sg['channel']}, {sg['duration_s']} s, closing line "
                f"{sp['package']['vo']['closing']!r})")
        except (package_pin.PinRefused, ValueError, OSError) as e:
            res["spotlight_pin_refused"] = f"{type(e).__name__}: {e}"
            say(f"SPOTLIGHT PIN REFUSED: {e}")
    else:
        na = (res.get("next_attempt") or {}).get("conversation") or {}
        say(f"  RULING 95: the newest conversation upload: {na.get('channel')} {na.get('video_id')} published "
            f"{na.get('published_at')} (expires {na.get('expires_at')}), {na.get('turns_per_min')} turns a minute, "
            f"rows {na.get('passes')}, word pass {na.get('word_pass_ready')} ready / {na.get('word_pass_waiting')} "
            f"waiting" if na else "  RULING 95: no conversation upload in the window")
        say(f"no spotlight ({sp.get('why_none')})" + "".join(
            f"; nearest {x['moment_id']} {x.get('channel')} {x.get('seconds')} s (hook {x.get('hook_own')}, alone "
            f"{x.get('alone')}): {x.get('out')}" for x in sp.get("near") or []))
    hp = res.get("hook_pool") or {}                      # RULING 76 (d): the four counts STATE line 1 carries;
    #   `moments` is the adapter's pool from LB.build_inputs, BEFORE usable() filters it (audit 1810 C3)
    res["ruling_76"] = {"inside_12h": sum(not PK.expired(m, now) for m in moments),
                        "cleared": (res.get("prescreen") or {}).get("cleared"),
                        "cuttable": (res.get("prescreen") or {}).get("cuttable"),
                        "hooks_4": len(hp.get("passing") or []) if isinstance(hp.get("passing"), list) else None}
    say(f"  RULING 76 (d): {res['ruling_76']['inside_12h']} moments inside 12 h, {res['ruling_76']['cleared']} "
        f"cleared, {res['ruling_76']['cuttable']} cuttable, {res['ruling_76']['hooks_4']} hooks >= 4")
    res["routing"] = router.routing                # RULING 85: which routing decided this build
    res["mode_at_end"] = router.mode()             # RULING 87: plan_b when Heimdall was down at the end
    if router.shadow:                              # RULING 86: every shadow answer in (the pin, if any, is already
        left = router.shadow_wait(900.0)           # written and logged above), then the side-by-side
        res["shadow86"] = SH.report(out_dir, res, missing=left)
        say(f"  SHADOW (ruling 86): {res['shadow86'].get('summary')}")
    try:                                         # the record is written whatever the ledger says (audit 0707 C1)
        after = round(router.spent(), 4)         # (after the shadows: their spend is in it)
    except Exception as e:                       # noqa: BLE001
        after = f"unreadable: {type(e).__name__}: {str(e)[:120]}"
    res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": PL.LY_LIMIT_USD,
                              "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
    vis = res.get("visual") or {}
    say(f"  visual (ruling 70): {vis.get('calls', 0)} sheet(s) asked ({vis.get('unmeasured', 0)} not measured), "
        f"{vis.get('cached', 0)} cached, {vis.get('flags', 0)} flag(s); cost ${vis.get('usd_reported', 0):.4f} "
        f"vendor-reported" + (f" + ${vis.get('usd_estimate', 0):.4f} price-table estimate for "
                              f"{vis.get('estimated_calls', 0)} call(s) with no vendor figure"
                              if vis.get("estimated_calls") else ""))
    say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${PL.LY_LIMIT_USD:.2f} "
        f"vendor-reported after this build (before it: ${spent0:.2f})")
    try:                                                 # audit 1420 C2: a registry failure never loses the record;
        if cand is not None and CA.key(cand["lineup"]) in reg["candidates"]:      # 1420b C2: its flag tells the truth
            CA.outcome(reg["candidates"][CA.key(cand["lineup"])], res["candidate"]["class"], at, name,
                       res["candidate"].get("result"))
        CA.seed(reg, json.loads(json.dumps(dict(res, registry=True), default=str)), name)   # its passed line-ups
        with open(REGISTRY + ".tmp", "w") as f:
            json.dump(reg, f, indent=1)
        os.replace(REGISTRY + ".tmp", REGISTRY)
        res["registry"] = True                           # its outcomes are in the saved registry
    except Exception as e:                               # noqa: BLE001
        res["registry"], res["registry_error"] = False, f"{type(e).__name__}: {str(e)[:200]}"   # a later seed
        say(f"  RULING 66: the candidate registry was NOT saved ({res['registry_error']}); the record (package.json) "
            f"is written with registry false")           # applies this record's outcome (CA.seed)
    with open(os.path.join(out_dir, "package.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    logf.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
