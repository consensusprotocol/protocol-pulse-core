#!/usr/bin/env python3
"""RULING 160 (2b) (orchestrator 07:33 ET Nov 24): "EVERY BUILD ENDS IN EXACTLY ONE RECORDED OUTCOME, written to a
machine-readable line (data/builds/outcomes.jsonl in each repo, one JSON object per build: time, story, outcome, the
stage and gate that decided it, the clip id, the model that failed if any, dollars): SEALED, HARD_REJECTED,
NO_ELIGIBLE_STORY, INDETERMINATE, BUDGET_STOPPED, RENDER_FAILED. ... This is also the YIELD record I ordered on Nov 17:
per stage, entered and refused, from this file, on line 1 once a day."

The schema agreed with the integrator (its message and the builder's reply, 07:2x-07:4x ET Nov 24): time (ISO, ET
offset), build (the launcher's number), run (the record folder: the pin's story_id carries it), story, story_id,
outcome, stage, gate, clip, model, dollars (vendor-reported for this build: spend_ruling_48 after minus before), side
("builder"), pin (the seal prefix or null), note, backfilled, and "yield" (the builder's: an ordered list of
{"stage", "entered", "refused"}). The render's lines are the integrator's (RENDER_FAILED is only theirs).

outcome_of(build_dir) classifies ONE build record (nothing is asked of any model); the driver calls record_build()
once at the end of every build, whatever ended it (tests/package/proof_ledger.main's finally), and write_once() never
writes a second line for the same run. How a record maps (first that applies):
  - a pin written (MOMENTS_PIN_LEDGER.json / SPOTLIGHT_PIN.json): SEALED;
  - NOTHING_NEW.json (ruling 107 (1)): NO_ELIGIBLE_STORY at "inputs";
  - the start refusal (ruling 48, exit 3): BUDGET_STOPPED at "start";
  - no package.json (a crash, a stop): INDETERMINATE, "the build stopped before writing its record" (or the error);
  - the spend stop refused a paid call this build needed (FINGERPRINT.json spend_refused): BUDGET_STOPPED;
  - else the deciding pass's reason (the never-empty pass when it ran, else the clean pass): classify().
INDETERMINATE (ruling 160 (2a)) is a hard check that could not be answered deciding the build: ruling 102's HELD,
"not measured", "NO JUDGE ANSWERED", a lock pre-check with no verdict, a back-end that never answered; HARD_REJECTED
is every refusal that was answered; NO_ELIGIBLE_STORY is a pool that could not make a medley before any model judged
it (ruling 109's free stages) and NOTHING NEW.
Usage: python3 tests/package/outcomes.py --yield YYYY-MM-DD   (the ET day's YIELD line, from the file)"""
import collections
import fcntl
import json
import os
import re
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUTCOMES = os.path.join(REPO, "data", "builds", "outcomes.jsonl")
ET = ZoneInfo("America/New_York")
KINDS = ("SEALED", "HARD_REJECTED", "NO_ELIGIBLE_STORY", "INDETERMINATE", "BUDGET_STOPPED", "RENDER_FAILED")
BUILDER_KINDS = KINDS[:5]                       # RENDER_FAILED is the render's (the integrator's lines)
STAGES = ("pool", "step A", "second pass + CUTTABLE", "hook onset", "hooks", "step A, second family", "line-ups",
          "writes", "seal")                     # the yield's stages, in the order a build meets them
UNANSWERED = re.compile(r"no verdict|not measured|NO JUDGE ANSWERED|STEP_A_HELD|HELD \(ruling 102\)|gives no answer|"
                        r"gave no answer|no answer|every back-end unavailable|ProviderError|no readable verdict|"
                        r"did not answer|not rated", re.I)
BUDGET = re.compile(r"SpendLimit|--lock-precheck off|the search spent|package spent \d+ s of|spend stop", re.I)
MOMENT_ID = re.compile(r"\b[0-9a-f]{20}\b")
BACKEND = re.compile(r"\b(?:heimdall|xai|openai|anthropic|google|elevenlabs|local_judge):[\w./-]+")
ROLE = re.compile(r"\b(\w+_verdict|angle_write|transcribe|visual_check|coherence_panel)\b")
STORY_ID = re.compile(r"\bS-[0-9a-f]{8}\b")
RUN = re.compile(r"^ledger_(\d{8})_(\d{6})$")


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def time_of(run):
    """The build's start on the ET clock (ISO with the offset), from its record folder's UTC stamp."""
    m = RUN.match(run or "")
    if not m:
        return None
    t = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    return t.astimezone(ET).isoformat(timespec="seconds")


def story_of(build_dir, titles=None):
    """(story title or None, story_id or None): the --only set's 'why' (ORDER 17:50: a story-first attempt names its
    story there); a routine build has none. titles: {story_id: title} known from other records (a 'why' may name only
    the id)."""
    only = _load(os.path.join(build_dir, "ONLY.json"))
    why = str((only or {}).get("why") or "")
    if not why:
        inp = _load(os.path.join(build_dir, "inputs.json")) or {}
        why = str(((inp.get("inputs") or {}).get("only") or {}).get("why") or "")
    sid = STORY_ID.search(why)
    if not sid:
        return None, None
    sid = sid.group(0)
    m = re.search(r"'([^']{6,160})'\s*\(" + sid + r"\)", why) or re.search(sid + r"\)?:?\s*'([^']{6,160})'", why)
    return (m.group(1) if m else (titles or {}).get(sid)), sid


def _mid(text):
    m = MOMENT_ID.search(text or "")
    return m.group(0) if m else None


def _first_model(text):
    m = BACKEND.search(text or "")
    if m:
        return m.group(0)
    r = ROLE.search(text or "")
    return r.group(1) if r else None


def _pass_of(pk):
    """The pass that decided the build: the never-empty pass's record when it ran, else the clean pass's."""
    ne = pk.get("never_empty") or {}
    if ne:
        sr = ne.get("soft_record") or {}
        return ne.get("soft_why_none"), sr.get("prescreen") or {}, sr.get("hook_pool") or {}, sr.get("tried") or []
    return pk.get("why_none"), pk.get("prescreen") or {}, pk.get("hook_pool") or {}, pk.get("tried") or []


def _held(pre):
    h = (pre or {}).get("held_102") or {}
    return sorted(set(h.get("first") or []) | set(h.get("second") or [])) if isinstance(h, dict) else []


def _angle_stage(reason):
    r = reason or ""
    for pat, st in ((r"exclusion / L-v 2 / CUTTABLE|second recognition|L-v 2", "second pass + CUTTABLE"),
                    (r"rulings? 70|ruling 93|visual", "visual"),
                    (r"ruling 68 / 72|the render's lock|ruling 72", "lock pre-check"),
                    (r"step A, re-screened", "step A, second family"),
                    (r"write\(s\) failed|context integrity|fidelity|coherence|value|takeaway|COMMENTARY", "writes"),
                    (r"no line-up", "line-ups")):
        if re.search(pat, r):
            return st
    return "line-ups"


def classify(why, pre=None, hook_pool=None, tried=None):
    """The deciding reason of a pass that sealed nothing -> {"outcome", "stage", "gate", "clip", "model"}. Every
    why_none package.build can write maps here (tests/package/test_outcomes.py enumerates them)."""
    w, pre = str(why or ""), pre or {}
    held = _held(pre)
    out = lambda o, st, g, clip=None, model=None: {"outcome": o, "stage": st, "gate": g[:200], "clip": clip,
                                                   "model": model}
    if BUDGET.search(w):
        return out("BUDGET_STOPPED", "line-ups" if "search spent" in w else _angle_stage(w),
                   "the search budget (ruling 41)" if "search spent" in w else
                   ("the lock pre-check not asked (--lock-precheck off, ruling 130 (2))" if "lock-precheck off" in w
                    else "the spend stop (ruling 48)"), model=_first_model(w))
    if re.match(r"the pool spans \d+ channel\(s\) after the free stages", w):
        return out("NO_ELIGIBLE_STORY", "pool", "a medley needs 3 channels after the free stages (ruling 109)")
    if re.match(r"\d+ moments cleared step A from fewer than 3 channels", w):
        if held:
            return out("INDETERMINATE", "step A", f"step A gave no answer for {len(held)} moment(s) (ruling 102 HELD)",
                       clip=held[0])
        return out("HARD_REJECTED", "step A", "step A's refusals leave fewer than 3 channels")
    if w.startswith("no work_dir"):
        return out("INDETERMINATE", "second pass + CUTTABLE", "no work dir: the second recognition pass cannot run")
    if w.startswith("no hook in the pool"):
        if "failed the second vendor's step A" in w:
            o = "INDETERMINATE" if (UNANSWERED.search(w) or held) else "HARD_REJECTED"
            return out(o, "step A, second family", "every hook on the bar failed step A's second family",
                       clip=_mid(w), model=_first_model(w))
        if "the visual check" in w:
            o = "INDETERMINATE" if re.search(r"not measured|not seen", w) else "HARD_REJECTED"
            return out(o, "visual", "the visual check refuses every opener (rulings 70 / 93)",
                       clip=_mid(w), model=_first_model(w) if o == "INDETERMINATE" else None)
        if UNANSWERED.search(w):                   # the back-end named after "not rated:", never the bar's rater
            tail = w.split("not rated:", 1)[1] if "not rated:" in w else w
            return out("INDETERMINATE", "hooks", "the hook rating had no answer", model=_first_model(tail))
        return out("HARD_REJECTED", "hooks", "no opener passes the calibrated hook bar (ruling 115)")
    if re.match(r"\d+ cleared moments pass the second pass, CUTTABLE and step A from both vendors", w):
        sp = pre.get("second_pass") or {}
        sv = pre.get("second_vendor") or {}
        open_ = [k for k, v in list(sp.items()) + list(sv.items()) if UNANSWERED.search(str(v))]
        if open_ or held:
            return out("INDETERMINATE", "second pass + CUTTABLE",
                       f"a hard check gave no answer for {len(open_) + len(held)} moment(s)", clip=(open_ + held)[0])
        bad = [k for k, v in sp.items() if v != "PASS"]
        return out("HARD_REJECTED", "second pass + CUTTABLE",
                   "the second pass, CUTTABLE or step A's second family leave fewer than 3 channels",
                   clip=bad[0] if len(bad) == 1 else None)
    if w.startswith("ruling 66: the candidate is closed"):
        return out("HARD_REJECTED", "line-ups", "ruling 66: the candidate line-up is closed")
    if w.startswith("ruling 66: the 8 judged line-ups were spent on candidates"):
        return out("BUDGET_STOPPED", "line-ups", "ruling 41 / 66: the judged line-ups were spent on candidates")
    if w.startswith("no readable angles"):
        return out("INDETERMINATE", "line-ups", "no angle in contract from the writers", model=_first_model(w))
    if w.startswith("no angle gave a line-up to try"):
        return out("HARD_REJECTED", "line-ups", "no line-up fits the medley's rules")
    if w.startswith("no angle gave a package"):
        reasons = [str(t.get("why") or t.get("result") or "") for t in (tried or [])] or \
            [x for x in re.split(r";\s*(?=angle \d+:)", w.partition(": ")[2]) if x]
        first = next((r for r in reasons if r), w)
        if any(UNANSWERED.search(r) for r in reasons):
            r = next(r for r in reasons if UNANSWERED.search(r))
            return out("INDETERMINATE", _angle_stage(r), re.sub(r"^angle \d+:\s*", "", r)[:200], clip=_mid(r),
                       model=_first_model(r))
        return out("HARD_REJECTED", _angle_stage(first), re.sub(r"^angle \d+:\s*", "", first)[:200],
                   clip=_mid(first))
    return out("INDETERMINATE", "unknown", f"a reason this classifier does not know: {w[:160]}")


def yield_of(pk, inp=None):
    """RULING 160 (2b), the YIELD: per stage of the deciding pass, the moments (line-ups, writes) that entered it and
    how many it refused. From the record only; a stage the pass never reached is 0 / 0."""
    pk, inp = pk or {}, inp or {}
    _, pre, hp, tried = _pass_of(pk)
    n_in = len(inp.get("moments") or [])
    usable = pk.get("usable") if isinstance(pk.get("usable"), int) else None
    sp, ho, sv = pre.get("second_pass") or {}, pre.get("hook_onset") or {}, pre.get("second_vendor") or {}
    soft2 = set(pre.get("soft_second") or {})
    passing = hp.get("passing") if isinstance(hp.get("passing"), list) else []
    lineups = [t for t in tried if t.get("lineup")]
    writes = sum(len(t.get("attempts") or []) for t in lineups)
    sealed = 1 if (pk.get("pin") or pk.get("spotlight_pin")) else 0
    made = 1 if pk.get("package") else 0
    rows = [("pool", n_in, max(0, n_in - usable) if usable is not None else 0),
            ("step A", int(pre.get("screened") or 0), max(0, int(pre.get("screened") or 0) -
                                                         int(pre.get("cleared") or 0))),
            ("second pass + CUTTABLE", len(sp), sum(v != "PASS" for v in sp.values())),
            ("hook onset", len(ho), sum(str(v).startswith("FAIL") for v in ho.values())),
            ("hooks", int(hp.get("can_open") or 0), max(0, int(hp.get("can_open") or 0) - len(passing))),
            ("step A, second family", len(sv), sum(str(v).startswith("FAIL") and k not in soft2 for k, v in sv.items())),
            ("line-ups", len(lineups), sum(t.get("result") != "PACKAGE" for t in lineups)),
            ("writes", writes, max(0, writes - sum(t.get("result") == "PACKAGE" for t in lineups))),
            ("seal", made, made - min(made, sealed))]
    return [{"stage": s, "entered": e, "refused": r} for s, e, r in rows]


def outcome_of(build_dir, rc=None, error=None, refused=None, build_no=None, backfilled=False, titles=None):
    """One build record -> its ONE outcome line (the agreed schema). rc / error / refused: how the driver ended
    (its exit code, the exception that ended it, its start refusal's words)."""
    run = os.path.basename(os.path.normpath(build_dir))
    pk = _load(os.path.join(build_dir, "package.json"))
    inp = _load(os.path.join(build_dir, "inputs.json")) or {}
    fp = _load(os.path.join(build_dir, "FINGERPRINT.json")) or {}
    title, sid = story_of(build_dir, titles)
    spend = (pk or {}).get("spend_ruling_48") or {}
    usd = round(spend["after"] - spend["before"], 4) if all(
        isinstance(spend.get(k), (int, float)) and not isinstance(spend.get(k), bool) for k in ("before", "after")) \
        else None
    base = {"time": time_of(run), "build": build_no, "run": run, "story": title, "story_id": sid, "side": "builder",
            "dollars": usd, "pin": None, "backfilled": bool(backfilled), "note": None, "yield": yield_of(pk, inp)}
    pin = (pk or {}).get("pin") or (pk or {}).get("spotlight_pin")
    for name in ("MOMENTS_PIN_LEDGER.json", "SPOTLIGHT_PIN.json"):
        p = _load(os.path.join(build_dir, name))
        if p:
            sha = ((p.get("moments_package") or {}).get("package_sha256") or (pin or {}).get("package_sha256") or "")
            return dict(base, outcome="SEALED", stage="seal", gate="every gate exactly PASS or FLAGGED, sealed",
                        clip=None, model=None, pin=sha[:12] or None, note=p.get("story_id"))
    if os.path.exists(os.path.join(build_dir, "NOTHING_NEW.json")) and pk is None:
        nn = _load(os.path.join(build_dir, "NOTHING_NEW.json")) or {}
        return dict(base, outcome="NO_ELIGIBLE_STORY", stage="inputs", gate="nothing new (ruling 107 (1))", clip=None,
                    model=None, dollars=0.0, note=f"the inputs are {nn.get('same_as')}'s: no model asked, $0.00")
    if refused or rc == 3:
        return dict(base, outcome="BUDGET_STOPPED", stage="start", gate="no build starts at the stop (ruling 48)",
                    clip=None, model=None, dollars=0.0, note=str(refused or "")[:400] or None)
    if pk is None:
        why = (f"the build crashed: {type(error).__name__}" if isinstance(error, Exception) else
               "the build was stopped (exit {})".format(getattr(error, "code", rc)) if error is not None else
               "the build stopped before writing its record")
        return dict(base, outcome="INDETERMINATE", stage="start", gate=why, clip=None, model=None,
                    note=(str(error)[:300] if error is not None else None))
    if pk.get("package") and pk.get("pin_refused"):
        return dict(base, outcome="HARD_REJECTED", stage="seal", gate="the pin refused the package",
                    clip=None, model=None, note=str(pk["pin_refused"])[:400])
    why, pre, hp, tried = _pass_of(pk)
    money = fp.get("spend_refused") or []
    if money:
        return dict(base, outcome="BUDGET_STOPPED", stage="spend",
                    gate=f"the spend stop refused {len(money)} paid call(s) (ruling 48)", clip=None,
                    model=sorted(set(map(str, money)))[0], note=str(why or "")[:400] or None)
    c = classify(why or pk.get("why_none"), pre, hp, tried)
    return dict(base, **c, note=str(why or pk.get("why_none") or "")[:500] or None)


def write_once(line, path=None):
    """Append the line unless a line for the same run is already there (EXACTLY ONE a build), under a flock; the file's
    directory is made on first use. -> True when written."""
    path = path or OUTCOMES
    if line.get("outcome") not in KINDS:
        raise ValueError(f"not an outcome: {line.get('outcome')!r}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            have = set()
            if os.path.exists(path):
                with open(path) as f:
                    for x in f:
                        try:
                            have.add((json.loads(x).get("side"), json.loads(x).get("run")))
                        except ValueError:
                            continue
            if (line.get("side"), line.get("run")) in have:
                return False
            with open(path, "a") as f:
                f.write(json.dumps(line, sort_keys=False) + "\n")
            return True
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def record_build(build_dir, rc=None, error=None, refused=None, build_no=None, path=None):
    """The driver's one call at the end of every build (proof_ledger.main's finally). -> the line written, or None
    when this run already has one."""
    titles = {x["story_id"]: x["story"] for x in lines(path) if x.get("story_id") and x.get("story")}
    line = outcome_of(build_dir, rc=rc, error=error, refused=refused, build_no=build_no, titles=titles)
    return line if write_once(line, path) else None


def lines(path=None):
    out = []
    try:
        with open(path or OUTCOMES) as f:
            for x in f:
                try:
                    out.append(json.loads(x))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def yield_line(day, path=None):
    """The ET day's YIELD line for STATE line 1: the builder's builds of that day, their outcomes, and per stage the
    moments that entered and were refused, summed over the day's builds (one moment tried by two builds counts
    twice)."""
    ls = [x for x in lines(path) if x.get("side") == "builder" and str(x.get("time") or "").startswith(day)]
    if not ls:
        return f"YIELD {day}: no build recorded."
    kinds = collections.Counter(x["outcome"] for x in ls)
    tot = collections.OrderedDict((s, [0, 0]) for s in STAGES)
    for x in ls:
        for y in x.get("yield") or []:
            if y.get("stage") in tot:
                tot[y["stage"]][0] += int(y.get("entered") or 0)
                tot[y["stage"]][1] += int(y.get("refused") or 0)
    usd = sum(float(x.get("dollars") or 0.0) for x in ls)
    return (f"YIELD {day} ({len(ls)} builds: " + ", ".join(f"{n} {k}" for k, n in kinds.most_common()) +
            f"; ${usd:.2f} vendor-reported), per stage entered / refused, summed over the builds: " +
            "; ".join(f"{s} {e} / {r}" for s, (e, r) in tot.items()) + ".")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--yield":
        print(yield_line(sys.argv[2]))
        sys.exit(0)
    print(__doc__.split("Usage:")[1].strip(), file=sys.stderr)
    sys.exit(2)
