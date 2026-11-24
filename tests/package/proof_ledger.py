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
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

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

FLAGGED_DAY = os.path.join(HERE, "proof", "FLAGGED_DAY.json")   # RULING 136 (2): the flagged pins of the 21:10 day


def flagged_today(path=FLAGGED_DAY, day=None):
    """RULING 136 (2): how many flagged packages this builder sealed in the current 21:10-21:10 day (the day ledger's
    name keys it; an unreadable or another day's file counts 0)."""
    day = day or os.path.basename(PL.day_ledger())
    try:
        d = json.load(open(path))
    except (OSError, ValueError):
        return 0
    return len(d.get("pins") or []) if isinstance(d, dict) and d.get("day") == day else 0


def record_flagged(pin, path=FLAGGED_DAY, day=None):
    """RULING 136 (2): a flagged pin was sealed: add it to the day's count."""
    day = day or os.path.basename(PL.day_ledger())
    try:
        d = json.load(open(path))
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict) or d.get("day") != day:
        d = {"day": day, "pins": []}
    d["pins"].append({"story_id": pin["story_id"], "review_flags": pin["moments_package"].get("review_flags")})
    json.dump(d, open(path, "w"), indent=1)
import proof_saved_runs as PS  # noqa: E402
import providers as P  # noqa: E402
import speakers as SP  # noqa: E402
import spotlight as SPOT  # noqa: E402
import lock_precheck as LP  # noqa: E402
import tail_variant as TV  # noqa: E402
import outcomes as OC  # noqa: E402

REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
DIRECTIVES = os.path.join(HERE, "proof", "RULING_104_DIRECTIVES.json")   # ruling 104: the orchestrator's directives
STATE_MD = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_STATE.md")   # ruling 87: a switch on line 1
FINGERPRINT = "FINGERPRINT.json"     # RULING 107 (1): a finished build's inputs, written at its end for the next build
NOTHING_NEW = "NOTHING_NEW.json"     # RULING 107 (1): a build that found nothing new and asked no model


UNDER_TEST = "PP_SELECTID_DRIVER_UNDER_TEST"   # set only by tests/package/conftest.py, inside pytest
MAIN_TREE = os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse")   # the integrator's tree: the build reads
#   code from it (the render scorer's files, owner_rules, the lock pre-check's service) and its results
TREES = (("this builder's tree", REPO, ("pipeline", "tests/package", "tests/select_by_id", "tests/moments",
                                        "tests/eligibility", "tests/providers")),
         ("the integrator's tree", MAIN_TREE, ("pipeline", "video_pipeline_v3")))
CODE_FILES = (".py", ".sh")


def tree_state(root, dirs):
    """THE ACCEPTANCE TEST, item 1 (orchestrator 08:50 ET Nov 24: "The build refuses to start if either tree is dirty,
    and the record names the commit it ran"): one git tree -> {"root", "head", "dirty"}. Dirty: a tracked code file
    (.py / .sh) in its code folders modified or staged, or an untracked .py / .sh there; data, caches, proof records,
    logs and lock files are not code. "head": its HEAD commit, or None when git cannot read it (then it is dirty: an
    unreadable tree is never clean)."""
    try:
        head = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=30).stdout.strip() or None
        st = subprocess.run(["git", "-C", root, "status", "--porcelain=v1", "-uall", "--", *dirs], capture_output=True,
                            text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        return {"root": root, "head": None, "dirty": [f"(git could not read it: {type(e).__name__})"]}
    if st.returncode != 0 or not head:
        return {"root": root, "head": head, "dirty": [f"(git could not read it: {st.stderr.strip()[:120]})"]}
    dirty = []
    for line in st.stdout.splitlines():
        xy, path = line[:2], line[3:].split(" -> ")[-1].strip('"')
        if not path.endswith(CODE_FILES):
            continue
        how = ("not committed, not tracked" if xy == "??" else "staged, not committed" if xy[1] == " " else
               "changed, not committed")
        dirty.append(f"{path} ({how})")
    return {"root": root, "head": head, "dirty": dirty}


def trees_state():
    """-> [(name, tree_state)] of both trees the build runs on."""
    return [(name, tree_state(root, dirs)) for name, root, dirs in TREES]


def dirty_refusal(states):
    """The one plain line a dirty tree refuses the build with, for a person to read, or None when both are clean."""
    bad = [(n, st) for n, st in states if st["dirty"]]
    if not bad:
        return None
    return ("REFUSED: the build did not start because code was changed and not committed: " + "; ".join(
        f"in {n} ({st['root']}): {', '.join(st['dirty'][:12])}" + (f" and {len(st['dirty']) - 12} more"
                                                                    if len(st["dirty"]) > 12 else "")
        for n, st in bad) + ". Commit (and push) or put away those changes, then start the build again.")


def entry_of():
    """VERIFIER ROWS 12 / 16 (FIX_VERIFICATION_2026-11-24: "Nothing in the pushed driver records or refuses another
    entry point"): how this build was entered. A build runs only as THIS file run as __main__ (the committed launcher,
    tests/package/record/build_and_record.sh, runs nothing else); a wrapper that imports this module and calls main()
    (builds 166-168's by_hand_*.py) is refused. Inside pytest, with UNDER_TEST set by the tests' conftest, the tests
    may call main(); the record says so. -> {"ok", "why", "driver", "argv0", "main", "code", "dirty", "under_test"}:
    "code" the git HEAD, "dirty" the code files (.py / .sh) git reports changed under pipeline/ and tests/package/."""
    mm = sys.modules.get("__main__")
    mf = getattr(mm, "__file__", None)
    own = bool(mf) and os.path.realpath(mf) == os.path.realpath(os.path.abspath(__file__))
    test = os.environ.get(UNDER_TEST) == "1" and "_pytest" in sys.modules
    try:
        head = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=30).stdout.strip() or None
        st = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", "pipeline", "tests/package"],
                            capture_output=True, text=True, timeout=60).stdout.splitlines()
        dirty = sorted(x[3:] for x in st if not x.startswith("??") and x[3:].endswith((".py", ".sh")))
        me = os.path.relpath(os.path.abspath(__file__), REPO)
        blob = subprocess.run(["git", "-C", REPO, "hash-object", me], capture_output=True, text=True,
                              timeout=30).stdout.strip() or None             # RULING 163 (5): the driver that ran,
        at_head = subprocess.run(["git", "-C", REPO, "rev-parse", f"HEAD:{me}"], capture_output=True, text=True,
                                 timeout=30).stdout.strip() or None          # by its git sha, and HEAD's
    except (OSError, subprocess.SubprocessError) as e:
        head, dirty, blob, at_head = None, [f"unreadable: {type(e).__name__}"], None, None
    why = None if own or test else (f"this build was entered through {mf or 'no file (python -c or an import)'}, "
                                    f"not {os.path.relpath(os.path.abspath(__file__), REPO)} run as __main__: no "
                                    f"by-hand wrapper builds (verifier rows 12 / 16)")
    return {"ok": why is None, "why": why, "driver": os.path.relpath(os.path.abspath(__file__), REPO),
            "driver_sha": blob, "driver_committed": bool(blob) and blob == at_head,
            "argv0": sys.argv[0] if sys.argv else None, "main": mf, "code": head, "dirty": dirty,
            "under_test": bool(test and not own)}


STAGES_TIMED = ("pool", "step A", "second ear", "out-edge question", "hooks", "vision", "line-ups", "writes", "gates",
                "seal")             # the orchestrator, 09:55 ET Nov 24: "wall-clock time PER STAGE in the build record"
#   (the render call's own is the launcher's, on the outcome line)
STAGE_OF = [(st, re.compile(rx)) for st, rx in (    # a log line -> the stage whose work printed it; first match wins
    ("pool", r"^===|^  entry|^  commits|^  delivered:|^  adapter:|^  word pass:|^  ledger rows|ORDER 17:50|RULING 104|"
             r"RULING 76: \d|routing \(ruling 85\)|RULING 152 \(1\): the writers|RULING 115:|RULING 116:|RULING 100 |"
             r"before this build|RULING 66: no candidate|usable, \d+ of them|the clip scorer's verdicts"),
    ("seal", r"^PACKAGE|PIN REFUSED|^SPOTLIGHT PIN|^no package|^no spotlight|^NOTHING NEW|RULING 76 \(d\)"),
    ("out-edge question", r"(?i)out[- ]edge|complete thought|ruling 162 \(1\)"),
    ("vision", r"visual \(ruling 70\)"),
    ("gates", r"fidelity|context|coherence|value \(ruling 91\)|RULING 150|clips alone|stand.alone|house style"),
    ("writes", r"write \d|RULING 156|the takeaway alone|writer"),
    ("line-ups", r"angle \d+ line-up|angles? from|join table|story angle|^  search:|ruling 72: the render's lock|RULING 66"),
    ("hooks", r"hooks \(ruling 59\)|can open a medley|hook bar|NEVER EMPTY \(stage 2b\)|G17a"),
    ("second ear", r"second recognition pass|CUTTABLE|L-v 2|stage 2a\): \d+ moment\(s\) whose words"),
    ("step A", r"step A|RULING 101|NEVER EMPTY \(stage 1\)|second family|HELD|RULING 146 \(3\)"),
)]


class StageClock:
    """The build's wall-clock seconds per stage (STAGES_TIMED), from its own log: each line's time since the line
    before is the work of the stage that line reports (STAGE_OF), or of the stage before it when it names none (the
    start, the inputs and the router's setup are the pool's)."""

    def __init__(self, t0=None):
        self.last, self.stage, self.secs = (t0 or time.time()), "pool", {}

    def mark(self, line):
        now = time.time()
        st = next((s for s, rx in STAGE_OF if rx.search(str(line))), self.stage)
        self.secs[st] = self.secs.get(st, 0.0) + max(0.0, now - self.last)
        self.last, self.stage = now, st

    def totals(self):
        return {s: round(self.secs[s], 1) for s in STAGES_TIMED if s in self.secs}


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


_errors = OC._errors                               # kept under its old name (moved to outcomes.py)


def open_work(res, sp, refused=()):
    """RULING 107 (1), with RULING 163 (4): how many checks a finished build left undone, which the next build must
    try again whatever its inputs (outcomes.undone names each: ruling 102's holds, the lock's missing verdicts, vision
    and word checks never measured, the openers no checker rated, every verdict that was not measured, the money the
    stop refused). -> int (0: nothing left)."""
    return len(OC.undone(res, sp, refused))


HOOK_SHADOW = {"coherence_verdict:hook": "heimdall:qwen/qwen3.8-27b"}   # RULING 115: recorded, never deciding


def build_shadow(routing, rt, streak):
    """The build's shadow back-ends: RULING 86, routing.shadow on the first heimdall_first pins, until
    `shadow_until_clean_pins` clean pins in a row (`streak`: a callable, read only under heimdall_first), but since
    RULING 118 only its uncapped (Heimdall) entries: ruling 86's Grok shadow is dropped; RULING 115, qwen on every hook,
    in every build. Recorded, never deciding."""
    shadow = None
    if routing == "heimdall_first" and streak() < int(rt.get("shadow_until_clean_pins") or 3):
        shadow = rt.get("shadow") or None
    shadow = {k: v for k, v in (shadow or {}).items()          # RULING 118 (a): an outside vendor's dollars are kept for
              if str(v).split(":", 1)[0] in PL.UNCAPPED}       # the seal: no outside shadow; a Heimdall one stays
    return dict(shadow, **HOOK_SHADOW)


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


STOP_CEILING_USD = PL.DAY_CAP_USD   # RULING 137 (3); THE ONE SPEND SETTING (amendment C, Nov 24): proof_ly's
#                                 RULING 137 (3) (orchestrator 11:05 ET Nov 17): the day cap is $1.50 all-in from the
#   21:10 ET day of Nov 17 (today's stop $1.40, given as --stop-usd); --stop-usd at most this. Was 1.25 (ORDER 17:50 ET
#   Nov 16, 'ADD 25 CENTS').


def lock_off(segs):
    """RULING 130 (2) with the 23:02 question (orchestrator, Nov 16): the lock pre-check's second recogniser is
    ElevenLabs Scribe, OUTSIDE dollars per span (the integrator, 23:0x Nov 16). With --lock-precheck off no request is
    written: the answer is NO VERDICT (never a pass, law L-m), so a line-up that reaches the lock stays a candidate
    (class "budget") with nothing paid after it. -> lock_precheck.check's shape."""
    return {"ok": False, "request_id": None, "segments": [],
            "error": "not asked: --lock-precheck off (ruling 130 (2): the pre-check's Scribe is outside dollars; no "
                     "request is sent until the orchestrator releases it)"}


def lock_for(mode, out_dir, say):
    """RULING 130 (2): the build's lock pre-check: lock_precheck.check, one numbered request per line-up asked
    ('pp-selectid.<build>.<n>'), when mode is 'on'; else lock_off (nothing sent). -> the lock_check callable."""
    if mode != "on":
        return lock_off
    n = iter(range(1, 10 ** 6))
    return lambda segs: LP.check(segs, f"pp-selectid.{os.path.basename(out_dir)}.{next(n)}", log=say)


def read_only(path):
    """ORDER 17:50 ET Nov 16 ("spend the fresh dollar on ONE line-up at a time, the likeliest first; do not screen the
    whole held pool at Grok"): the --only file, {"ids": [this build's moment ids, at least one], "why": a reason}.
    -> {"ids", "why", "file"}, or ValueError."""
    with open(path) as f:
        d = json.load(f)
    ids = d.get("ids") if isinstance(d, dict) else None
    if not (isinstance(ids, list) and ids and all(isinstance(x, str) and x for x in ids)) or \
            not isinstance(d.get("why"), str) or not d["why"].strip():
        raise ValueError(f"--only {path}: needs {{'ids': [moment ids], 'why': text}}")
    return {"ids": list(dict.fromkeys(ids)), "why": d["why"].strip(), "file": path}


def only_moments(moments, only):
    """The --only set: the pool's moments it names, in the pool's order (a trimmed variant is made later, beside its
    parent, as for any moment). -> (moments, record: file, why, asked, kept, missing)."""
    want = set(only["ids"])
    kept = [m for m in moments if m["moment_id"] in want]
    have = {m["moment_id"] for m in kept}
    return kept, {"file": only["file"], "why": only["why"], "asked": len(only["ids"]), "kept": len(kept),
                  "missing": [x for x in only["ids"] if x not in have]}


def build_router(routing, shadow, shadow_log, limit=None):
    """The build's router: ruling 48's ledger and limit, the routing's chains (frozen legs out), the evidence file
    (item 55), ruling 86's shadow, ruling 87's shared Heimdall health and Plan B chains, ruling 99's circuit breaker,
    ruling 100's deadline table (recomputed daily from the build's own recorded answers)."""
    return P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND,
                    limit_usd=PL.LY_LIMIT_USD if limit is None else limit,        # ORDER 17:50: --stop-usd
                    limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
                    routing=routing, shadow=shadow, shadow_log=shadow_log,
                    health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD,      # ruling 87
                    breakers=CB.STATE,                                                         # ruling 99
                    deadlines=DT.load(DT.STATE, PL.REPLIES),                                   # ruling 100
                    reserve_wait_s=PL.RESERVE_WAIT_S,          # batch 3: a call that fits waits for calls in flight
                    uncapped=PL.UNCAPPED)                      # ruling 118 (b): Heimdall recorded, never capped


WRITER_PROBE_S = 45.0                            # RULING 152 (1): one probe answer waits at most this long


def writer_probe(router, timeout_s=WRITER_PROBE_S):
    """RULING 152 (1) (orchestrator 19:36 ET Nov 23): "Probe which families answer BEFORE the build and skip the ones
    that do not." Every Heimdall leg of the router's writer chain (proof_ly.WRITERS) is asked a one-word question, all
    at once, timeout_s each, as a ruling-87 probe (role "probe87:<name>": live, never recorded nor served from a
    recording). A family that does not answer is marked down for this run, so no writer call waits out its deadline on
    it; Grok (the chain's non-Heimdall leg) is never probed and stays last. A replayed run (router.replay) probes
    nothing: its recordings decide. -> {name: {"answers": bool, "seconds": float[, "why": str]}}."""
    import threading
    if getattr(router, "replay", False):
        return {}
    names = [n for n in router.chain("angle_write") if P.gateway(router.backends[n]) == "heimdall"]
    out, lock = {}, threading.Lock()

    def ask(n):
        router.chains.setdefault(f"probe87:{n}", [n])
        t0 = time.time()
        try:
            r = router.call(f"probe87:{n}", "Reply with the single word OK.", 64, 7, deadline_s=timeout_s)
            text = (getattr(r, "text", "") or "").strip()
            v = {"answers": bool(text), "seconds": round(time.time() - t0, 1), **({} if text else {"why": "empty"})}
        except Exception as e:                             # noqa: BLE001  any failure: not answering today
            v = {"answers": False, "seconds": round(time.time() - t0, 1), "why": f"{type(e).__name__}: {str(e)[:120]}"}
        with lock:
            out[n] = v
    ts = [threading.Thread(target=ask, args=(n,), daemon=True) for n in names]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout_s + 15)
    with lock:
        for n in names:
            v = out.setdefault(n, {"answers": False, "seconds": timeout_s, "why": "no answer in time"})
            if not v["answers"]:
                router.down[n] = f"did not answer the writer probe (ruling 152 (1)): {v.get('why', '')}"[:200]
        return dict(out)


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


def start_refused(spent0, stop=None):
    """RULING 48, with the orchestrator's stop of 13:02 Nov 14 (the $16 stop passed with leave; at $19 stop and tell on
    STATE line 1 in capitals): no build starts at or over PL.LY_STOP_USD (or this build's --stop-usd, ORDER 17:50 ET
    Nov 16). -> the refusal line, or None."""
    stop = PL.LY_STOP_USD if stop is None else stop
    if spent0 >= stop:
        return (f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
                f"vendor reports none), at or over the ${stop:.2f} stop: no build starts; the orchestrator "
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
    """The build, entered only through this file (entry_of), and RULING 160 (2b): EXACTLY ONE outcome line a build in
    data/builds/outcomes.jsonl (outcomes.record_build), written here whatever ends the build once its record folder
    exists: its end, NOTHING NEW, the start refusal, a crash or a stop (SIGTERM is turned into SystemExit, so this
    finally runs). A refusal before the folder is made (exit 2) is no build and writes no line."""
    entry = entry_of()
    if not entry["ok"]:                                  # (and again in _main: a wrapper calling _main is refused)
        print(f"REFUSED: {entry['why']}", file=sys.stderr)
        return 2
    if not entry["under_test"]:
        try:
            signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
        except ValueError:                               # not the main thread: the default stays
            pass
    box, rc, err = {"clock": StageClock()}, None, None      # the time per stage, from the build's very start
    try:
        rc = _main(argv, box)
        return rc
    except BaseException as e:                           # noqa: BLE001  recorded, then raised as it was
        err = e
        raise
    finally:
        if box.get("out_dir"):
            try:
                line = OC.record_build(box["out_dir"], rc=rc, error=err, refused=box.get("refused"),
                                       build_no=box.get("build_no"),     # outcomes.OUTCOMES (audit L2, qwen F1)
                                       build_id=box.get("build_id"), seconds=box["clock"].totals())
                if line:
                    print(f"  RULING 160 (2b): outcome {line['outcome']} at {line['stage']}: {line['gate']}",
                          flush=True)
            except BaseException as e:                   # noqa: BLE001  never masks the build's own end; a stop or
                print(f"  RULING 160 (2b): the outcome line was NOT written: {type(e).__name__}: {e}",   # an interrupt
                      file=sys.stderr, flush=True)       # inside the write is said too (audit L2, qwen F3)


def _main(argv, box):
    entry = entry_of()                                   # verifier rows 12 / 16: checked here too, so a wrapper that
    if not entry["ok"]:                                  # calls _main() directly is refused the same way
        print(f"REFUSED: {entry['why']}", file=sys.stderr)
        return 2
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
    ap.add_argument("--lock-precheck", choices=("on", "off"), default="on",
                    help="RULING 130 (2): 'off' sends no lock pre-check request (its Scribe is outside dollars); a "
                         "line-up that reaches the lock then waits as a candidate")
    ap.add_argument("--only", metavar="FILE", help="ORDER 17:50 ET Nov 16: {'ids': [moment ids], 'why': text}: this "
                    "build takes only those moments of the pool, every gate as before (one line-up at a time)")
    ap.add_argument("--stop-usd", type=float, default=None, help="ORDER 17:50 ET Nov 16: this build's outside-dollar "
                    f"limit (no build starts at it; the router stops outside calls at it), in (0, {STOP_CEILING_USD}]")
    ap.add_argument("--build-no", type=int, default=None, help="RULING 160 (2b): the launcher's build number, on the "
                    "build's outcome line")
    ap.add_argument("--build-id", default=None, help="the launcher's unique build id (amendment C), in the record and on "
                    "the outcome line")
    ap.add_argument("--out-dir-file", default=None, help="amendment C: this run writes its own record folder's path here "
                    "the moment it makes it, so the launcher never guesses 'the newest folder'")
    ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
                    help="RULING 66: try ONLY the line-up that passed the clips-alone verdict in this earlier build's "
                         "record (its tried[N]; default the first that passed), as it was judged")
    a = ap.parse_args(argv)
    now = datetime.now(timezone.utc)
    if not 0 < a.hours <= package_pin.WINDOW_H:          # ruling 76: "rather than widen the window"; RULING 159 (3)(a):
        print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {package_pin.WINDOW_H:g}]", file=sys.stderr)
        return 2                                         # ruling 144's one-build exception switch is removed
    try:                                                 # read before anything is written (glm C2 N-4)
        delivered, last, pins = delivered_pins(a.delivered)
        since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
        if since.tzinfo is None:
            raise ValueError("--since has no time zone")
        if since > now:
            raise ValueError(f"since {since.isoformat()} is after now")
        cand = None
        only = read_only(a.only) if a.only else None     # ORDER 17:50 ET Nov 16: read before anything is written
        if a.stop_usd is not None and not 0 < a.stop_usd <= STOP_CEILING_USD:
            raise ValueError(f"--stop-usd {a.stop_usd} is outside (0, {STOP_CEILING_USD}]")
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
    trees = trees_state()                                # THE ACCEPTANCE TEST, item 1: both trees clean, or no build
    refusal = dirty_refusal(trees)
    if refusal and not entry["under_test"]:
        print(refusal, file=sys.stderr)
        return 2
    entry = dict(entry, trees={n: {"root": st["root"], "head": st["head"], "dirty": st["dirty"]} for n, st in trees})
    out_dir = os.path.join(HERE, "proof", f"ledger_{now.strftime('%Y%m%d_%H%M%S')}")
    if entry["under_test"] and os.path.realpath(os.path.dirname(out_dir)) == \
            os.path.realpath(os.path.join(REPO, "tests", "package", "proof")):   # audit L2 (qwen, cycle 2): a run
        print("REFUSED: a run under test never writes into the real build records", file=sys.stderr)   # that only
        return 2                                                                  # claims to be a test makes none
    try:
        os.makedirs(out_dir)                     # never into an earlier run's evidence (glm C3 P2-1)
    except FileExistsError:
        print(f"REFUSED: {out_dir} exists", file=sys.stderr)
        return 2
    box.update(out_dir=out_dir, build_no=a.build_no, build_id=a.build_id)   # RULING 160 (2b): one outcome from here
    if a.out_dir_file:                                   # amendment C: the launcher reads THIS run's folder from here
        with open(a.out_dir_file, "w") as f:
            f.write(out_dir + "\n")
    logf = open(os.path.join(out_dir, "package.log"), "a")
    clock = box.get("clock") or StageClock()
    say = lambda s: (clock.mark(s), print(s, flush=True), logf.write(s + "\n"), logf.flush())
    ctx = E.Context(now, PS.REG, ledger=PS.ledger_entries())
    say(f"=== {time.strftime('%H:%M:%S %Z')} LEDGER medley build, code {PL.code_sha()}, now (render clock) "
        f"{now.isoformat(timespec='seconds')}, since {since.isoformat(timespec='seconds')} "
        f"({'--since' if a.since else 'the newest delivered pin'}), publish window {a.hours} h" +
        (f"; RULING 66: ONLY the candidate {cand['source']} tried[{cand['index']}] {cand['lineup']}" if cand else ""))
    say("  commits (the acceptance test, item 1): " + "; ".join(
        f"{n} {t['root']} at {str(t['head'])[:12]}" + (f" (UNDER TEST, changed: {t['dirty']})" if t["dirty"] else "")
        for n, t in entry["trees"].items()))
    say(f"  entry (verifier rows 12 / 16, ruling 163 (5)): {entry['driver']} (git sha {str(entry['driver_sha'])[:12]}, "
        f"{'the committed one' if entry['driver_committed'] else 'NOT the committed one'}) as __main__ (argv0 "
        f"{entry['argv0']}), HEAD {str(entry['code'])[:12]}, changed code files {entry['dirty'] or 'none'}")
    say(f"  delivered: {', '.join(p['story_id'] + ' (' + p['approved_at'] + ')' for p in pins)}; "
        f"{len(delivered)} clip spans out")
    say(f"  RULING 76: {len(gone)} candidate(s) expired (over {package_pin.WINDOW_H:g} h on the render clock)" +
        (f": {gone}" if gone else ""))
    rows, rep = LB.rows(since, now, horizon_h=a.hours)   # pp-ingest's adapter, its own 12 h expiry (rulings 76 + 77)
    say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
    wp, wp_rep = LB.word_pass_index(a.word_pass)
    wp_refused = wp_rep.get("refused") or []             # final: the worker never re-works them (the inputs keep ids);
    #   a name of its own: main() later binds `refused` to start_refused()'s answer
    say(f"  word pass: {json.dumps(dict(wp_rep, refused=len(wp_refused)))}")
    moments, sources, inputs = LB.build_inputs(rows, ctx, log=say, word_pass=wp,
                                               ledger_store=os.path.join(LB.INGEST_ROOT, "data", "editorial"),
                                               word_pass_refused=wp_refused)
    inputs["word_pass"] = wp_rep
    if only is not None:                                 # ORDER 17:50 ET Nov 16: one candidate set, before variants
        moments, inputs["only"] = only_moments(moments, only)
        say(f"  ORDER 17:50: --only: {inputs['only']['kept']} of {inputs['only']['asked']} listed moments in this pool "
            f"({only['why']})" + (f"; not in it: {inputs['only']['missing']}" if inputs['only']['missing'] else ""))
    try:                                                 # RULING 95: when the next qualifying episode could arrive. It
        next_try = SPOT.next_attempt(rows, wp, now, refused=wp_refused)   # reads the inputs alone, so it is computed
    except Exception as e:                               # noqa: BLE001  here, recorded with them, and is a report,
        next_try = {"error": f"{type(e).__name__}: {str(e)[:200]}"}       # never the build
    moments = with_variants(moments, sources, ctx, inputs, say)   # RULING 104: beside their parents, every gate again
    with open(os.path.join(out_dir, "inputs.json"), "w") as f:
        json.dump({"entry": entry, "build_no": a.build_no, "build_id": a.build_id,   # rows 12 / 16; 160 (2b)
                   "since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
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
    limit = PL.LY_LIMIT_USD if a.stop_usd is None else a.stop_usd   # ORDER 17:50 ET Nov 16: --stop-usd
    stop = PL.LY_STOP_USD if a.stop_usd is None else a.stop_usd
    router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"), limit=limit)
    say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
        + (f"; SHADOW (ruling 86 / 115): {shadow}" if shadow else ""))
    wprobe = writer_probe(router)                # RULING 152 (1): the writers that answer, in order, then Grok
    say("  RULING 152 (1): the writers " + " -> ".join(n for n in router.chain("angle_write") if n not in router.down)
        + f", {PK.WRITER_DEADLINE_S:g} s each; probe: " + ("; ".join(
            f"{n.split(':', 1)[1]} {'answers' if v['answers'] else 'SKIPPED (' + str(v.get('why')) + ')'} {v['seconds']} s"
            for n, v in wprobe.items()) or "none (a replayed run)"))
    live, live_why = PK.hook_live_bar()          # RULING 115: the bar in every build line, its floors and its sha
    say(f"  RULING 115: {HB.text(live)}; the hook list {router.chain('coherence_verdict', 'hook')}"
        + (f" [{live_why}]" if live_why else ""))
    import lineup_bar as LNB                     # RULING 116: the line-up bar, named in every build line too
    lbar, lbar_why = PK._live_lineup_bar()
    say(f"  RULING 116: {LNB.text(lbar)}" + (f" [{lbar_why}]" if lbar_why else ""))
    say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
        f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
    spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
    refused = start_refused(spent0, stop)
    if refused:
        say(refused)
        box["refused"] = refused                         # RULING 160 (2b): BUDGET_STOPPED at the start
        logf.close()
        return 3
    say(f"  spend (ruling 48): ${spent0:.2f} of ${limit:.2f} vendor-reported before this build (no build "
        f"starts at ${stop:.2f})")
    own, used = PL.meter(router), PL.reply_meter(router)
    t0 = time.time()
    spotlit = SPOT.load_spotlit(SPOTLIGHTS)              # RULING 90: free; its pool goes to the clip scorer with the
    sp_pool, _ = SPOT.pool(moments, sources, ctx, delivered, M.optout_ids(), spotlit)   # medley's own candidates
    kw = dict(delivered=delivered, optout=M.optout_ids(), log=say, scorer_extra=sp_pool,
              never_empty=True, flagged_today=flagged_today(),                     # RULINGS 136 / 137 (stage 1)
              work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
              spend=lambda: (own["est"], own["best"]),
              step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
              hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"),          # ruling 59 (a): cached
              join_cache=os.path.join(HERE, "proof", "JOIN_CACHE.json"),          # ruling 117: cached
              scorer_verdicts_path=PK.SCORER_VERDICTS,                            # ruling 56 / 60: read only
              scorer_candidates_path=PK.SCORER_CANDIDATES, build_name=os.path.basename(out_dir),
              stories_path=PK.STORIES,                                             # ruling 118 (4): read only
              ledger_aliases=inputs.get("duplicates_of") or {},    # its ledger ids: a dropped duplicate -> the kept row
              visual_cache=os.path.join(HERE, "proof", "VISUAL_CACHE.json"),       # ruling 70
              out_edge_cache=os.path.join(HERE, "proof", "OUT_EDGE_CACHE.json"),   # ITEM 3: the question's answers,
              #   keyed by the exact transcript, cut and prompt version (out_edge._key); the replay's frozen answers
              lock_check=lock_for(a.lock_precheck, out_dir, say))    # rulings 68 / 72 / 130 (2): off sends nothing
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
                    spotlit=spotlit, out_edge_cache=kw["out_edge_cache"])         # ITEM 3
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
            if pin["moments_package"].get("review_flags"):        # RULING 136 (2): a flagged pin counts for the day
                record_flagged(pin)
                res["pin"]["review_flags"] = pin["moments_package"]["review_flags"]
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
    res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": limit, "stop": stop,
                              "basis": PL.LY_LIMIT_BASIS, **({"order_17_50_stop": a.stop_usd}
                                                             if a.stop_usd is not None else {})}
    line101 = ruling_101_line((res.get("prescreen") or {}).get("parallel_101"))   # RULING 101: the extra spend
    if line101:
        say(line101)
    vis = res.get("visual") or {}
    say(f"  visual (ruling 70): {vis.get('calls', 0)} sheet(s) asked ({vis.get('unmeasured', 0)} not measured), "
        f"{vis.get('cached', 0)} cached, {vis.get('flags', 0)} flag(s); cost ${vis.get('usd_reported', 0):.4f} "
        f"vendor-reported" + (f" + ${vis.get('usd_estimate', 0):.4f} price-table estimate for "
                              f"{vis.get('estimated_calls', 0)} call(s) with no vendor figure"
                              if vis.get("estimated_calls") else ""))
    say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${limit:.2f} "
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
    res["stage_seconds"] = clock.totals()                # the time per stage (09:55 ET Nov 24), as it stands here
    with open(os.path.join(out_dir, "package.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    if cand is None:                             # RULING 107 (1): the next build compares its inputs with these, as
        fp_end, parts_end = fingerprint(pool, delivered, pins, since, now, reg, a.routing)   # at this build's END
        money = list(router.spend_refused)       # the calls this build's router refused for money: left undone
        items = OC.undone(res, sp, money)         # RULING 163 (4): each named in the record
        left = len(items)
        with open(os.path.join(out_dir, FINGERPRINT), "w") as f:
            json.dump({"fingerprint": fp_end, "parts": parts_end, "open_work": left, "undone": items,
                       "spend_refused": money, "build": name}, f, indent=1)
        say(f"  RULING 107 (1): fingerprint {fp_end[:12]}, {left} item(s) left undone"
            + (f" ({len(money)} of them paid call(s) the spend stop refused)" if money else ""))
    logf.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
