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

RULING 107 (1) (orchestrator 20:20 ET Nov 14), "a build that judges nothing new must cost $0.00": a full build ends by
writing FINGERPRINT.json (fingerprint(): its pool, deliveries, ET day, code by content, candidates and the integrator's
outputs it read, as they stand at its end, with open_work(): what it left undone). The next build fingerprints its own
inputs before any model is asked. When they equal the newest finished build's and that build left nothing undone, it
writes NOTHING_NEW.json and stops: no router, no call, $0.00.

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
import hashlib
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
import circuit_breaker as CB  # noqa: E402
import deadline_table as DT  # noqa: E402
import shadow86 as SH  # noqa: E402
import ledger_build as LB  # noqa: E402
import moments as M  # noqa: E402
import package as PK  # noqa: E402
import hook_bar as HB  # noqa: E402
import package_pin  # noqa: E402
import proof_ly as PL  # noqa: E402
import proof_saved_runs as PS  # noqa: E402
import providers as P  # noqa: E402
import speakers as SP  # noqa: E402
import spotlight as SPOT  # noqa: E402
import lock_precheck as LP  # noqa: E402
import tail_variant as TV  # noqa: E402

REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
DIRECTIVES = os.path.join(HERE, "proof", "RULING_104_DIRECTIVES.json")   # ruling 104: the orchestrator's directives
STATE_MD = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_STATE.md")   # ruling 87: a switch on line 1
FINGERPRINT = "FINGERPRINT.json"     # RULING 107 (1): a finished build's inputs, written at its end for the next build
NOTHING_NEW = "NOTHING_NEW.json"     # RULING 107 (1): a build that found nothing new and asked no model


def _sha(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, default=str).encode()).hexdigest()


def _file_sha(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def code_content(repo=REPO, here=HERE):
    """The build's code BY CONTENT: every pipeline/*.py and pipeline/*.json, and every driver module of tests/package
    (not its tests). A STATE or data commit moves HEAD but changes no judgment, so HEAD is not in it."""
    files = sorted(glob.glob(os.path.join(repo, "pipeline", "*.py")) + glob.glob(os.path.join(repo, "pipeline", "*.json"))
                   + [f for f in glob.glob(os.path.join(here, "*.py")) if not os.path.basename(f).startswith("test_")])
    h = hashlib.sha256()
    for f in files:
        with open(f, "rb") as fh:
            h.update(os.path.relpath(f, repo).encode() + b"\0" + fh.read() + b"\0")
    return h.hexdigest()


def fingerprint(moments, delivered, pins, since, now, reg, routing=None):
    """RULING 107 (1) (orchestrator 20:20 ET Nov 14): "a build that judges nothing new must cost $0.00". Everything a
    build's judgments and outcome depend on: the pool's moment records (each with its words, span and sources), what
    was delivered and since when, the ET day (the show date every step-A prompt carries), the code and its config BY
    CONTENT, the candidate registry and which of its candidates are due now (ruling 66: a resting one comes due after
    6 h), the ruling-90 spotlights record, the ruling-104 directives, and the outputs of the integrator's services this
    build reads: the pre-check results for the pool's videos and the clip scorer's verdicts. -> (sha256, its parts)."""
    vids = {m.get("video_id") for m in moments}
    try:
        res = sorted((n, os.path.getsize(os.path.join(LP.RESULTS, n)), os.path.getmtime(os.path.join(LP.RESULTS, n)))
                     for n in os.listdir(LP.RESULTS) if n.split(".", 1)[0] in vids)
    except OSError:
        res = None
    parts = {"moments": _sha(moments), "delivered": _sha([delivered, [p.get("story_id") for p in pins], since.isoformat()]),
             "day_et": SPOT.et_day(now), "code": code_content(), "candidates": _sha(reg.get("candidates")),
             "due": sorted([k, fresh] for k, _, fresh in CA.due(reg, now)),
             "spotlights": _file_sha(SPOTLIGHTS), "directives": _file_sha(DIRECTIVES),
             "precheck_results": _sha(res), "scorer_verdicts": _file_sha(PK.SCORER_VERDICTS),
             "routing": routing}                 # --routing decides which models judge (audit 2155g C1, glm F4)
    return _sha(parts), parts


def _errors(x):
    """The number of objects anywhere inside x whose "verdict" is "error" (a segment the render's lock gave no verdict on
    in time, wherever the record nests it)."""
    if isinstance(x, dict):
        return int(x.get("verdict") == "error") + sum(_errors(v) for v in x.values())
    if isinstance(x, (list, tuple)):
        return sum(_errors(v) for v in x)
    return 0


def open_work(res, sp):
    """RULING 107 (1): what a finished build left undone, which the next build must try again whatever its inputs:
    the moments ruling 102 held (no leg answered), any segment the render's lock gave no verdict on in time, and any
    visual check left unmeasured. -> int (0: nothing left)."""
    pre, sp = (res or {}).get("prescreen") or {}, sp or {}
    h = pre.get("held_102") or {}
    held = len(h.get("first") or []) + len(h.get("second") or []) + len(sp.get("held_102") or [])
    no_verdict = _errors(res) + _errors(sp)        # by structure, never a string search (audit 2155g C1, qwen)
    vis = (res or {}).get("visual") or {}
    return held + no_verdict + int(vis.get("unmeasured") or 0)


HOOK_SHADOW = {"coherence_verdict:hook": "heimdall:qwen/qwen3.8-27b"}   # RULING 115: recorded, never deciding


def build_shadow(routing, rt, streak):
    """The build's shadow back-ends: RULING 86, Grok (routing.shadow) on the first heimdall_first pins, until
    `shadow_until_clean_pins` clean pins in a row (`streak`: a callable, read only under heimdall_first); RULING 115,
    qwen on every hook, in every build. Recorded, never deciding."""
    shadow = None
    if routing == "heimdall_first" and streak() < int(rt.get("shadow_until_clean_pins") or 3):
        shadow = rt.get("shadow") or None
    return dict(shadow or {}, **HOOK_SHADOW)


def nothing_new(proof_dir, out_dir, fp):
    """RULING 107 (1): the newest earlier FINISHED build (its FINGERPRINT.json) when its fingerprint is this build's and
    it left nothing undone; else None. A build that stopped early writes none, and neither does a --from-candidate
    one (it tries one line-up, not the pool), so neither can stand for a full build."""
    for d in sorted(glob.glob(os.path.join(proof_dir, "ledger_*")), reverse=True):
        if os.path.abspath(d) == os.path.abspath(out_dir):
            continue
        try:
            with open(os.path.join(d, FINGERPRINT)) as f:
                prev = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(prev, dict) and prev.get("fingerprint") == fp and prev.get("open_work") == 0:
            return os.path.basename(d)
        return None
    return None


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


def build_router(routing, shadow, shadow_log):
    """The build's router: ruling 48's ledger and limit, the routing's chains (frozen legs out), the evidence file
    (item 55), ruling 86's shadow, ruling 87's shared Heimdall health and Plan B chains, ruling 99's circuit breaker,
    ruling 100's deadline table (recomputed daily from the build's own recorded answers)."""
    return P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
                    limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
                    routing=routing, shadow=shadow, shadow_log=shadow_log,
                    health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD,      # ruling 87
                    breakers=CB.STATE,                                                         # ruling 99
                    deadlines=DT.load(DT.STATE, PL.REPLIES),                                   # ruling 100
                    reserve_wait_s=PL.RESERVE_WAIT_S)          # batch 3: a call that fits waits for calls in flight


def applied(router):
    """RULING 100: which rows of the deadline table the build's router uses: a verdict pair on which a deadline applies
    today, the role's (a gateway with a configured deadline: Heimdall) or the caller's (step A's first screen passes one
    to every leg of its chain under heimdall_first, Grok's included: package.first_bounds). -> applies(key)."""
    fb = PK.first_bounds(router).get("deadline_s")
    first = set(router.chain("context_verdict", "step_a_first")) if fb else set()

    def applies(key):
        name, _, role = key.partition("|")
        b = router.backends.get(name)
        dl = fb if role == "context_verdict" and name in first else None
        return b is not None and router.effective_deadline(role, b, dl) is not None and \
            role in set((router.config.get("routing") or {}).get("verdict_roles") or ())
    return applies


def directives(path=None):
    """RULING 104: the orchestrator's directives ({"directives": [{"parent", "ends", "alternative_to", "by", "why"}]}),
    written by the builder only on the orchestrator's written yes, quoting it. -> {parent id: directive}; none when the
    file is absent; an unreadable file or a malformed row is never guessed at: no directive (the rules stand)."""
    try:
        with open(path or DIRECTIVES) as f:
            rows = json.load(f).get("directives") or []
    except (OSError, ValueError, AttributeError):
        return {}
    if not isinstance(rows, list):                       # glm, audit 1835 C1: {"directives": 5} is no directive
        return {}
    import re
    story = re.compile(r"moments-[A-Za-z0-9_]+-[0-9a-f]{8}")         # the pins' own story id form (package_pin.to_pin)
    return {d["parent"]: d for d in rows if isinstance(d, dict) and isinstance(d.get("parent"), str) and
            re.fullmatch(r"[0-9a-f]{20}", d["parent"]) and
            ((isinstance(d.get("ends"), str) and d["ends"].strip() and "reseal" not in d) or   # a variant, or the SAME
             (d.get("reseal") is True and "ends" not in d)) and                             # moment re-sealed (93
            isinstance(d.get("alternative_to"), str) and story.fullmatch(d["alternative_to"]) and   # amended + 106)
            isinstance(d.get("by"), str) and d["by"].strip()}


def spot_place(pk, again, now):
    """RULING 90 at the pin, read again: the spotlight's channel must have no spotlight on this ET day, unless the
    package is ruling 104's ALTERNATIVE (the orchestrator's directive) to that day's named story (spotlight.day_taken).
    again: the spotlights record, None when it cannot be read (then no pin). -> (why it cannot take the place or None,
    the story it is the alternative to or None)."""
    alt = ((pk.get("spotlight") or {}).get("derived_from") or {}).get("alternative_to")
    segs = pk.get("segments") or []
    if not segs or not isinstance(segs[0], dict):            # cycle 2 (all three): never a crash, never a pin
        return "ruling 90: a spotlight without its segment has no channel to place", alt
    if again is None or SPOT.day_taken(again, segs[0].get("channel_id"), SPOT.et_day(now), alt):
        return "ruling 90: this channel already has a spotlight today, or the record cannot be read", alt
    return None, alt


def with_variants(moments, sources, ctx, inputs, say, results_dir=None, directives_path=None):
    """RULING 104 (14:12 Nov 14): the build's pool with the tail-side variants (tail_variant.for_pool: a current lock
    pre-check hold on the parent's span, a cut the render cannot make, the spotlight's seconds ceiling), so every gate
    judges them from the start, the clip scorer included (its pool is made from these moments). A parent whose current
    hold is final is replaced by its variant; a parent over the ceiling stays beside it. inputs["ruling_104"] records
    them, the replaced parents, and why each parent has a variant or none. -> the new list of moments."""
    variants, notes, replaced = TV.for_pool(moments, sources, ctx, results_dir or LP.RESULTS, SPOT.SPOT_S[1],
                                            directives=directives(directives_path))
    inputs["ruling_104"] = {"variants": [v["moment_id"] for v in variants], "replaced": sorted(replaced),
                            "notes": notes}
    say(f"  RULING 104 (the tail-side twin): {len(variants)} variant(s) in the pool, {len(replaced)} held parent(s) "
        f"replaced by theirs (ruling 103: the hold is final)" + "".join(f"; {k}: {w}" for k, w in sorted(notes.items())))
    return [m for m in moments if m["moment_id"] not in replaced] + variants


def start_refused(spent0):
    """RULING 48, with the orchestrator's stop of 13:02 Nov 14 (the $16 stop passed with leave; at $19 stop and tell on
    STATE line 1 in capitals): no build starts at or over PL.LY_STOP_USD. -> the refusal line, or None."""
    if spent0 >= PL.LY_STOP_USD:
        return (f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
                f"vendor reports none), at or over the ${PL.LY_STOP_USD:.2f} stop: no build starts; the orchestrator "
                f"decides (13:02 Nov 14: SAY IT ON STATE LINE 1 IN CAPITALS)")
    return None


def ruling_102_line(pre, sp):
    """RULING 102 (13:02 Nov 14): the build's line, for STATE line 1: the moments HELD for this build (no leg answered;
    never refused, never cached, retried next build) and every step-A verdict the local judge gave (ruling 87's last
    resort, recorded as such on the pin). -> str or "" (nothing held, no local verdict)."""
    pre, sp = pre or {}, sp or {}
    h = pre.get("held_102") or {}
    first, second, spot = list(h.get("first") or []), list(h.get("second") or []), list(sp.get("held_102") or [])
    last = sorted(set(pre.get("last_resort_87") or {}) | set(sp.get("last_resort_87") or {}))
    if not (first or second or spot or last):
        return ""
    return (f"  RULING 102: HELD for this build, retried next build (no leg answered; never refused): {len(first)} at "
            f"step A's first screen, {len(second)} at the medley's second screen {second}, {len(spot)} at the "
            f"spotlight's {spot}; THE LOCAL JUDGE (RULING 87'S LAST RESORT) GAVE {len(last)} STEP-A VERDICT(S)"
            + (f": {last}" if last else ""))


def ruling_101_line(par):
    """RULING 101 (12:16 Nov 14): the build's line on step A's order, with the extra spend when Grok's confirm ran in
    parallel (its verdicts the second screen could not use: the dollars sequential would have saved). -> str or ""."""
    if not par:
        return ""
    if par.get("parallel"):
        asked = par.get("asked", 0) or 0
        extra = (par.get("usd", 0) or 0) * (asked - (par.get("used", 0) or 0)) / max(1, asked)
        return (f"  RULING 101 (step A in parallel): {par.get('n_new')} new moments; the filter ({par.get('leg')}) "
                f"would have held the build about {(par.get('est_wait_s') or 0) / 60:.0f} min. Grok's confirm was asked "
                f"on {asked} at once ({par.get('verdicts')} verdicts, ${par.get('usd', 0) or 0:.4f} vendor-reported); "
                f"the second screen used {par.get('used')}, so about ${extra:.4f} was spent that sequential would have "
                f"saved" + (f"; {par['error']}" if par.get("error") else ""))
    wait = par.get("est_wait_s")
    return (f"  RULING 101: step A sequential ({par.get('n_new')} new moments" +
            (f"; the filter's wait about {wait / 60:.1f} min on {par.get('leg')}" if isinstance(wait, (int, float))
             else f", not over {PK.STEP_A_PARALLEL_NEW}") + (f": {par['why']})" if par.get("why") else ")"))


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
    wp_refused = wp_rep.get("refused") or []             # final: the worker never re-works them (the inputs keep ids);
    #   a name of its own: main() later binds `refused` to start_refused()'s answer
    say(f"  word pass: {json.dumps(dict(wp_rep, refused=len(wp_refused)))}")
    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp,
                                               ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"),
                                               word_pass_refused=wp_refused)
    inputs["word_pass"] = wp_rep
    try:                                                 # RULING 95: when the next qualifying episode could arrive. It
        next_try = SPOT.next_attempt(rows, wp, now, refused=wp_refused)   # reads the inputs alone, so it is computed
    except Exception as e:                               # noqa: BLE001  here, recorded with them, and is a report,
        next_try = {"error": f"{type(e).__name__}: {str(e)[:200]}"}       # never the build
    moments = with_variants(moments, sources, ctx, inputs, say)   # RULING 104: beside their parents, every gate again
    with open(os.path.join(out_dir, "inputs.json"), "w") as f:
        json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
                   "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments,
                   "next_attempt": next_try}, f, indent=1, default=str)
    pool = json.loads(json.dumps(moments, default=str))   # RULING 107 (1): the pool as it came in, before any stage
    fp, fp_parts = fingerprint(pool, delivered, pins, since, now, reg, a.routing)
    same = None if cand is not None else nothing_new(os.path.join(HERE, "proof"), out_dir, fp)
    if same:                                     # nothing new: no router, no model, $0.00 (ruling 107 (1))
        with open(os.path.join(out_dir, NOTHING_NEW), "w") as f:
            json.dump({"fingerprint": fp, "parts": fp_parts, "same_as": same, "at": now.isoformat()}, f, indent=1)
        say(f"NOTHING NEW (ruling 107 (1)): this build's inputs are {same}'s (fingerprint {fp[:12]}), and that build "
            f"left nothing undone: no model is asked, $0.00")
        logf.close()
        return 0
    rt = json.load(open(P.CONFIG)).get("routing") or {}
    routing = a.routing or rt.get("mode") or "today"
    shadow = build_shadow(routing, rt, SH.clean_streak)   # RULING 86 (Grok) / RULING 115 (qwen on every hook)
    router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"))
    say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
        + (f"; SHADOW (ruling 86 / 115): {shadow}" if shadow else ""))
    live, live_why = PK.hook_live_bar()          # RULING 115: the bar in every build line, its floors and its sha
    say(f"  RULING 115: {HB.text(live)}; the hook list {router.chain('coherence_verdict', 'hook')}"
        + (f" [{live_why}]" if live_why else ""))
    say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
        f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
    spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
    refused = start_refused(spent0)
    if refused:
        say(refused)
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
    res["next_attempt"] = next_try                       # RULING 95, computed beside the inputs above
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
            why_place, alt = spot_place(sp["package"], again, now)
            if why_place:
                lock.append(why_place)
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
                                             "at": now.isoformat(timespec="seconds"), "build": name,
                                             **({"alternative_to": alt} if alt else {})})    # ruling 104
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
            f"waiting / {na.get('word_pass_refused')} refused (never re-worked)" if na else
            "  RULING 95: no conversation upload in the window")
        say(f"no spotlight ({sp.get('why_none')})" + "".join(
            f"; nearest {x['moment_id']} {x.get('channel')} {x.get('seconds')} s (hook {x.get('hook_own')}, alone "
            f"{x.get('alone')}): {x.get('out')}" for x in sp.get("near") or []))
    line102 = ruling_102_line(res.get("prescreen"), sp)  # RULING 102: held, never refused; the local judge's verdicts
    if line102:
        say(line102)
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
    line101 = ruling_101_line((res.get("prescreen") or {}).get("parallel_101"))   # RULING 101: the extra spend
    if line101:
        say(line101)
    vis = res.get("visual") or {}
    say(f"  visual (ruling 70): {vis.get('calls', 0)} sheet(s) asked ({vis.get('unmeasured', 0)} not measured), "
        f"{vis.get('cached', 0)} cached, {vis.get('flags', 0)} flag(s); cost ${vis.get('usd_reported', 0):.4f} "
        f"vendor-reported" + (f" + ${vis.get('usd_estimate', 0):.4f} price-table estimate for "
                              f"{vis.get('estimated_calls', 0)} call(s) with no vendor figure"
                              if vis.get("estimated_calls") else ""))
    say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${PL.LY_LIMIT_USD:.2f} "
        f"vendor-reported after this build (before it: ${spent0:.2f})")
    evs = router.breaker_events                  # RULING 99: the circuit breaker's count, for STATE line 1
    try:
        bs = CB.summary(CB.STATE)
        res["breakers_ruling_99"] = dict(bs, this_build=evs)
        say(f"  RULING 99 (circuit breaker): this build opened {sum(e['kind'] == 'breaker_open' for e in evs)} and "
            f"closed {sum(e['kind'] == 'breaker_close' for e in evs)}; open now: "
            + ("; ".join(f"{o['model']} until {o['until']} ({o['why']})" for o in bs["open"]) or "none")
            + f"; in 24 h: {bs['opens']} opened, {bs['closes']} closed")
    except Exception as e:                       # noqa: BLE001 (the record is written whatever the breaker says)
        say(f"  RULING 99 (circuit breaker): its state cannot be read: {type(e).__name__}: {str(e)[:160]}")
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
    if cand is None:                             # RULING 107 (1): the next build compares its inputs with these, as
        fp_end, parts_end = fingerprint(pool, delivered, pins, since, now, reg, a.routing)   # at this build's END
        left = open_work(res, sp)
        with open(os.path.join(out_dir, FINGERPRINT), "w") as f:
            json.dump({"fingerprint": fp_end, "parts": parts_end, "open_work": left, "build": name}, f, indent=1)
        say(f"  RULING 107 (1): fingerprint {fp_end[:12]}, {left} item(s) left undone")
    logf.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
