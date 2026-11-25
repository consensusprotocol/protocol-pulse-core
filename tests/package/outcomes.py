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
Usage: python3 tests/package/outcomes.py --yield YYYY-MM-DD   (the ET day's YIELD line, from the file)
       python3 tests/package/outcomes.py --render RUN EXIT PIN [SAID_FILE [SECONDS]]   (the launcher: the render call)"""
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
KINDS = ("SEALED", "HARD_REJECTED", "NO_ELIGIBLE_STORY", "INDETERMINATE", "BUDGET_STOPPED", "RENDER_FAILED",
         "DEADLINE_STOPPED")                    # R3 (build 172): the launch's one wall-clock budget ran out
BUILDER_KINDS = KINDS[:5] + ("DEADLINE_STOPPED",)   # RENDER_FAILED is the render's (the integrator's lines)
STAGES = ("pool", "step A", "second pass + CUTTABLE", "hook onset", "hooks", "step A, second family", "line-ups",
          "writes", "seal")                     # the yield's stages, in the order a build meets them
UNANSWERED = re.compile(r"no verdict|not measured|NO JUDGE ANSWERED|STEP_A_HELD|HELD \(ruling 102\)|gives no answer|"
                        r"gave no answer|no answer|every back-end unavailable|ProviderError|no readable verdict|"
                        r"did not answer|not rated", re.I)
BUDGET = re.compile(r"SpendLimit|--lock-precheck off|the search spent|package spent \d+ s of|spend stop|"
                    r"CompletionReserve|completion reserve|CeilingRefused|BUDGET_REFUSED", re.I)   # C: money
MOMENT_ID = re.compile(r"\b[0-9a-f]{20}\b")
BACKEND = re.compile(r"\b(?:heimdall|xai|openai|anthropic|google|elevenlabs|local_judge):[\w./-]+")
ROLE = re.compile(r"\b(\w+_verdict|angle_write|transcribe|visual_check|coherence_panel)\b")
STORY_ID = re.compile(r"\bS-[0-9a-f]{8}\b")
RUN = re.compile(r"^ledger_(\d{8})_(\d{6})$")


NOTES = {   # THE ACCEPTANCE TEST, item 2 (b) (orchestrator 08:50 ET Nov 24): every outcome carries "a reason PBX can read
    #   in one sentence": the line's "note", plain words, no ruling numbers, no ids (the technical reason is "detail")
    ("SEALED", "seal"): "The video passed every check and was sealed for review.",
    ("NO_ELIGIBLE_STORY", "inputs"): "Nothing had changed since the last attempt, so the build did not run again.",
    ("NO_ELIGIBLE_STORY", "pool"): "There were not enough usable clips from three different channels to make a video.",
    ("NO_ELIGIBLE_STORY", "start"): "A clip in the set would have been too old by the time the video reached the render, "
                                    "so the build was stopped before it began.",
    ("HARD_REJECTED", "step A"): "Our fact-check turned down too many clips, leaving fewer than three channels.",
    ("HARD_REJECTED", "step A, second family"): "A second fact-check turned down the clips that could open the video.",
    ("HARD_REJECTED", "second pass + CUTTABLE"): "A second listen to the audio turned down clips (words heard "
                                                 "differently, or a cut in the middle of a sentence), leaving too few "
                                                 "to make a video.",
    ("HARD_REJECTED", "hook onset"): "No clip could open the video with a clean start.",
    ("HARD_REJECTED", "hooks"): "None of the clips was strong enough to open the video.",
    ("HARD_REJECTED", "visual"): "Something on screen in a clip made it unusable, such as a news ticker or text our "
                                 "cut would slice.",
    ("HARD_REJECTED", "lock pre-check"): "The render's word check would not accept the words of a clip.",
    ("HARD_REJECTED", "line-ups"): "The clips that passed could not be arranged into a video of the right length from "
                                   "three channels.",
    ("HARD_REJECTED", "writes"): "Our writers could not produce lines that passed the fact and quality checks.",
    ("HARD_REJECTED", "seal"): "The finished package failed its final check before sealing.",
    ("HARD_REJECTED", "out edge"): "A clip ended in the middle of a sentence and could not be extended.",
    ("INDETERMINATE", "visual"): "A model did not answer the picture check of some clips, so the build stopped "
                                 "without a decision.",
    ("INDETERMINATE", "hooks"): "A model did not answer the rating of the opening clips, so the build stopped "
                                "without a decision.",
    ("INDETERMINATE", "step A"): "A model did not answer the fact-check of some clips, so the build stopped without a "
                                 "decision.",
    ("INDETERMINATE", "step A, second family"): "A model did not answer the second fact-check of some clips, so the "
                                                "build stopped without a decision.",
    ("INDETERMINATE", "second pass + CUTTABLE"): "The second listen to the audio could not be made for some clips, so "
                                                 "the build stopped without a decision.",
    ("INDETERMINATE", "hook onset"): "The start of some clips could not be measured, so the build stopped without a "
                                     "decision.",
    ("INDETERMINATE", "lock pre-check"): "The render's word check gave no answer in time, so the build stopped "
                                         "without a decision.",
    ("INDETERMINATE", "gates"): "A model did not answer a check of our lines, so the build stopped without a decision.",
    ("INDETERMINATE", "out edge"): "A model did not answer whether a clip ends on a complete thought, so the build "
                                   "stopped without a decision.",
    ("INDETERMINATE", "line-ups"): "Our writers did not produce a usable plan for the video, so the build stopped "
                                   "without a decision.",
    ("INDETERMINATE", "start"): "The build stopped before it finished, so nothing was decided.",
    ("BUDGET_STOPPED", "start"): "The day's spending limit had already been reached, so the build did not start.",
    ("BUDGET_STOPPED", "spend"): "The day's spending limit was reached before all the checks could run.",
    ("BUDGET_STOPPED", "line-ups"): "The build used up its time or money for trying line-ups before finding a video.",
    ("RENDER_FAILED", "render"): "The video was sealed, but the render did not start.",
    ("RENDER_FAILED", "delivery"): "The video was rendered, but its delivery failed.",
    ("DEADLINE_STOPPED", "render"): "The video was sealed, but the render ran out of its time and was stopped.",
    ("DEADLINE_STOPPED", "delivery"): "The video was rendered, but its delivery ran out of time and was stopped.",
    ("HARD_REJECTED", "render"): "The video was sealed, but the render's final check refused it.",
}
NOTE_LOCK_OFF = "The render's word check was not asked, to save money, so no video could be sealed."
NOTE_RESERVE = ("Money was held back to finish a video, so some speculative checks were not paid for and nothing was "
                "decided on them.")                 # LEAN (5): the completion reserve refused a speculative call
NOTE_DEFAULT = {"SEALED": NOTES[("SEALED", "seal")],
                "HARD_REJECTED": "The clips were turned down by our checks, so no video was made.",
                "NO_ELIGIBLE_STORY": "There was no story with enough usable clips to make a video.",
                "INDETERMINATE": "A check could not be answered, so the build stopped without a decision.",
                "BUDGET_STOPPED": "The spending limit stopped the build before it could finish.",
                "RENDER_FAILED": "The render did not finish.",
                "DEADLINE_STOPPED": "The build ran out of its time before it finished, so it was stopped and nothing "
                                    "was sealed."}


def plain_note(outcome, stage, gate=""):
    """The outcome's one plain sentence for PBX (no ruling numbers, no ids)."""
    if outcome == "BUDGET_STOPPED" and "not asked" in str(gate or ""):
        return NOTE_LOCK_OFF
    if outcome == "BUDGET_STOPPED" and "completion reserve" in str(gate or ""):
        return NOTE_RESERVE
    return NOTES.get((outcome, stage)) or NOTE_DEFAULT.get(outcome) or "The build ended without a video."


MEASURE_KINDS = ("passed", "measured_failure", "budget_refused", "provider_unavailable", "unmeasured")


def measure_class(t):
    """LEAN (3): one tried line-up's clips-alone verdict, by kind: "passed", "measured_failure" (a verdict that was
    measured and said no), or why it was NOT measured: "budget_refused" (the spend stop or the completion reserve),
    "provider_unavailable" (no back-end answered) or "unmeasured" (anything else). The line-up's own "measure" (written
    by package._build since lean (3)) when present, else read from its verdict record (older records). None for a try
    that formed no line-up."""
    if not isinstance(t, dict) or not t.get("lineup"):
        return None
    m = t.get("measure")
    if isinstance(m, str) and m.lower() in MEASURE_KINDS:
        return m.lower()
    med = t.get("medley") if isinstance(t.get("medley"), dict) else {}
    if t.get("medley_ok") is True:
        return "passed"
    if med.get("measured") is True:
        return "measured_failure"
    return _class_of(str(med.get("error") or ""))


PROVIDER = re.compile(r"ProviderError|ReplayMiss|every back-end unavailable|NO JUDGE ANSWERED|gives no answer|"
                      r"gave no answer|no answer|did not answer", re.I)


def _class_of(text):
    """LEAN (3): why something was not measured, from its reason text: budget_refused / provider_unavailable /
    unmeasured (package.unmeasured_class's three kinds, read back from a record)."""
    if BUDGET.search(text) or re.search(r"CompletionReserve|completion reserve", text):
        return "budget_refused"
    if PROVIDER.search(text):
        return "provider_unavailable"
    return "unmeasured"


def verdict_classes(pk, fp=None):
    """LEAN (3) ("the outcome line keeps measured-failure, unmeasured, provider-unavailable and budget-refused
    apart"): {"lineups": {kind: n} over every line-up both passes tried (measure_class), "undone": {kind: n} over the
    checks the build left undone (FINGERPRINT.json's list, else undone()): money and anything refused for money is
    budget_refused, no answer is provider_unavailable, anything else unmeasured}."""
    pk = pk if isinstance(pk, dict) else {}
    soft = ((pk.get("never_empty") or {}).get("soft_record") or {}) if isinstance(pk.get("never_empty"), dict) else {}
    tried = [t for t in list(pk.get("tried") or []) + list(soft.get("tried") or []) if isinstance(t, dict)]
    lu = {k: 0 for k in MEASURE_KINDS}
    for t in tried:
        k = measure_class(t)
        if k:
            lu[k] += 1
    items = (fp or {}).get("undone") if isinstance((fp or {}).get("undone"), list) else undone(pk, pk.get("spotlight"))
    fails = {}                                           # a held moment's own reason (its "why" here is generic)
    for p in (pk.get("prescreen"), soft.get("prescreen")):
        for mid, f in ((p or {}).get("failed") or {}).items() if isinstance(p, dict) else ():
            fails.setdefault(mid, " ".join(map(str, f)) if isinstance(f, list) else str(f))
        for mid, f in ((p or {}).get("second_vendor") or {}).items() if isinstance(p, dict) else ():
            fails[mid] = (fails.get(mid, "") + " " + str(f)).strip()   # C: the second screen's own reason (a refusal
            #   for money names the reserve or the spend stop): a record written before C reads right too
    ud = {k: 0 for k in MEASURE_KINDS[2:]}
    for x in items or []:
        if not isinstance(x, dict):
            continue
        ud["budget_refused" if x.get("kind") in ("money", "budget") else   # C: refused for money, never "no answer"
           _class_of(str(x.get("why") or "") + " " + fails.get(x.get("id"), ""))] += 1
    return {"lineups": lu, "undone": ud}


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
    if re.match(r"\d+ cleared moments pass the second pass, CUTTABLE and step A from (?:both vendors|the first "
                r"vendor)", w):                    # A: the lean path's wording (the second vendor pending)
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


UNDONE_STAGE = {"vision": "visual", "hook rating": "hooks", "held": "step A", "lock": "lock pre-check",
                "out edge": "out edge", "second_pass": "second pass + CUTTABLE", "trim_cut": "second pass + CUTTABLE",
                "hook_onset": "hook onset", "verdict": "gates"}   # an undone check's kind -> the yield's stage
VISION_UNMEASURED = "is not measured (law L-m)"    # visual_pin.layout_block / hook_block: a sheet never judged
LOCK_OFF = "--lock-precheck off"                  # ruling 130 (2): a lock pre-check not asked by choice, not an outage


def _errors(x):
    """The objects anywhere inside x whose "verdict" is "error" (a segment the render's lock gave no verdict on in
    time, wherever the record nests it): structure, never a string search (audit 2155g C1)."""
    if isinstance(x, dict):
        return int(x.get("verdict") == "error") + sum(_errors(v) for v in x.values())
    if isinstance(x, (list, tuple)):
        return sum(_errors(v) for v in x)
    return 0


def _unanswered(x, seen):
    """Every verdict record anywhere inside x that says it was not measured ({"measured": false}: no model answered,
    the stand-in judges included, or nothing could be measured), once per distinct record; a lock segment with no
    verdict is _errors()'s."""
    out = []
    if isinstance(x, dict):
        if x.get("measured") is False and x.get("verdict") != "error":
            k = json.dumps(x, sort_keys=True, default=str)
            if k not in seen:
                seen.add(k)
                out.append(str(x.get("error") or x.get("why") or "not measured")[:160])
        for v in x.values():
            out += _unanswered(v, seen)
    elif isinstance(x, (list, tuple)):
        for v in x:
            out += _unanswered(v, seen)
    return out


def undone(res, sp=None, refused=()):
    """RULING 107 (1), with RULING 163 (4) (orchestrator 08:22 ET Nov 24: "a build that ended with ANYTHING unmeasured
    or unanswered records each such item as left undone, so the identical build re-runs when a vendor returns"): every
    check a finished build left undone -> [{"kind", "id", "why"}] (proof_ledger.open_work counts them; FINGERPRINT.json
    keeps them). As before: the moments ruling 102 held (the clean pass's, the spotlight's, and the never-empty pass's
    own), every lock segment with no verdict, the clean record's unmeasured vision sheets, word checks / hook onsets /
    trimmed cuts NOT MEASURED, and every paid call refused for money (`refused`). Added (the verifier's outage drill,
    Nov 24: an outage run recorded '0 item(s) left undone' and its re-run 1 s later was refused NOTHING NEW): the
    never-empty pass's openers whose vision was never measured, the openers no checker rated (the hook pool's error),
    every verdict record that says it was not measured, the search stopped for the lock's want of a verdict (never
    one not asked by choice), and the out edge's unverified clips (ruling 162 (1))."""
    d = lambda x: x if isinstance(x, dict) else {}       # audit 20261124_0109 H (qwen F1): a malformed record is read
    ls = lambda x: list(x) if isinstance(x, (list, tuple, set)) else []   # as empty, never a crash
    res, sp = d(res), d(sp)
    items = []
    pre = d(res.get("prescreen"))
    h = d(pre.get("held_102"))
    items += [{"kind": "held", "id": m, "why": "step A gave no answer (ruling 102 HELD)"}
              for m in ls(h.get("first")) + ls(h.get("second")) + ls(sp.get("held_102"))]
    bg = d(pre.get("budget_102"))                        # C: step A refused FOR MONEY: budget, never a provider's
    items += [{"kind": "budget", "id": m, "why": "step A was refused for money (the spend stop or the completion "
                                                 "reserve): no verdict, budget_refused"}
              for m in ls(bg.get("first")) + ls(bg.get("second")) + ls(sp.get("budget_102"))]
    ne = d(res.get("never_empty"))
    soft = d(ne.get("soft_record"))
    soft_pre = d(soft.get("prescreen"))
    s = d(soft_pre.get("held_102"))
    items += [{"kind": "held", "id": m, "why": "step A gave no answer in the never-empty pass (ruling 102 HELD)"}
              for m in sorted(set(ls(s.get("first")) + ls(s.get("second"))) - set(ls(h.get("first")) + ls(h.get("second"))))]
    sb = d(soft_pre.get("budget_102"))
    items += [{"kind": "budget", "id": m, "why": "step A was refused for money in the never-empty pass (the spend "
                                                 "stop or the completion reserve): no verdict, budget_refused"}
              for m in sorted(set(ls(sb.get("first")) + ls(sb.get("second"))) - set(ls(bg.get("first")) +
                                                                                    ls(bg.get("second"))))]
    items += [{"kind": "lock", "id": None, "why": "the render's lock gave no verdict in time"}] * (_errors(res) + _errors(sp))
    items += [{"kind": "vision", "id": None, "why": "a vision check not measured"}] * int(
        d(res.get("visual")).get("unmeasured") or 0)
    items += [{"kind": k, "id": mid, "why": str(v)[:160]} for k, mid, v in sorted(
        {(k, mid, str(v)) for p in (pre, soft_pre) for k in ("second_pass", "hook_onset", "trim_cut")
         for mid, v in d(p.get(k)).items() if str(v).startswith("NOT MEASURED")})]
    items += [{"kind": "money", "id": str(b), "why": "a paid call the spend stop refused"} for b in ls(refused)]
    # RULING 163 (4): what an outage leaves unmeasured or unanswered
    if ne and not res.get("package"):            # the never-empty pass decided and its vision is in no counter
        for mid, why in sorted(d(d(soft.get("hook_pool")).get("visual_blocked")).items()):
            if VISION_UNMEASURED in str(why):
                items.append({"kind": "vision", "id": mid, "why": "an opener's vision check not measured"})
    unrated = [max(0, int(d(hp).get("can_open") or 0) - int(d(hp).get("rated") or 0))
               for hp in (res.get("hook_pool"), soft.get("hook_pool")) if d(hp).get("error")]
    items += [{"kind": "hook rating", "id": None, "why": "an opener no checker rated (the hook pool's error)"}] * \
        (max(unrated) if unrated else 0)
    seen = set()
    items += [{"kind": "verdict", "id": None, "why": w} for w in _unanswered(ls(res.get("tried")), seen) +
              _unanswered(ls(soft.get("tried")), seen)]
    for stop in (res.get("lock_stop"), sp.get("lock_stop")):
        if isinstance(stop, str) and stop and LOCK_OFF not in stop:
            items.append({"kind": "lock", "id": None, "why": stop[:160]})
    for oe in (res.get("out_edge"), soft.get("out_edge")):
        uv = d(oe).get("unverified")
        for mid in sorted(uv if isinstance(uv, (dict, list, tuple, set)) else []):
            items.append({"kind": "out edge", "id": str(mid), "why": "the clip's out edge gave no answer"})
    return items


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
            ("step A, second family", sum(not str(v).startswith("PENDING") for v in sv.values()),   # A: pending is
             sum(str(v).startswith("FAIL") and k not in soft2 for k, v in sv.items())),           # never entered
            ("line-ups", len(lineups), sum(t.get("result") != "PACKAGE" for t in lineups)),
            ("writes", writes, max(0, writes - sum(t.get("result") == "PACKAGE" for t in lineups))),
            ("seal", made, made - min(made, sealed))]
    return [{"stage": s, "entered": e, "refused": r} for s, e, r in rows]


def outcome_of(build_dir, rc=None, error=None, refused=None, build_no=None, backfilled=False, titles=None,
               stopped_at=None):
    """One build record -> its ONE outcome line (the agreed schema). rc / error / refused: how the driver ended
    (its exit code, the exception that ended it, its start refusal's words). Its "note" is PBX's one plain sentence
    (plain_note); the technical reason is its "detail"."""
    line = _outcome_of(build_dir, rc, error, refused, build_no, backfilled, titles, stopped_at=stopped_at)
    return dict(line, detail=line.get("note"), note=plain_note(line["outcome"], line["stage"], line.get("gate")))


def _outcome_of(build_dir, rc=None, error=None, refused=None, build_no=None, backfilled=False, titles=None, stopped_at=None):
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
            "dollars": usd, "pin": None, "backfilled": bool(backfilled), "note": None, "yield": yield_of(pk, inp),
            "verdict_classes": verdict_classes(pk, fp) if pk else None}   # LEAN (3): the four kinds kept apart
    pin = (pk or {}).get("pin") or (pk or {}).get("spotlight_pin")
    deadline = type(error).__name__ == "DeadlineStopped"     # R3: the launch's one budget ran out (providers)
    for name in ("MOMENTS_PIN_LEDGER.json", "SPOTLIGHT_PIN.json"):
        p = _load(os.path.join(build_dir, name))
        if p:
            sha = ((p.get("moments_package") or {}).get("package_sha256") or (pin or {}).get("package_sha256") or "")
            return dict(base, outcome="SEALED", stage="seal", gate="every gate exactly PASS or FLAGGED, sealed",
                        clip=None, model=None, pin=sha[:12] or None, note=p.get("story_id"))
    if deadline:                                         # R3: after a seal it stays SEALED (the pin was whole)
        return dict(base, outcome="DEADLINE_STOPPED", stage=stopped_at or "start",
                    gate=f"the build's deadline: {str(error)[:200]}", clip=None, model=None,
                    note=NOTE_DEFAULT["DEADLINE_STOPPED"])
    if os.path.exists(os.path.join(build_dir, "NOTHING_NEW.json")) and pk is None:
        nn = _load(os.path.join(build_dir, "NOTHING_NEW.json")) or {}
        return dict(base, outcome="NO_ELIGIBLE_STORY", stage="inputs", gate="nothing new (ruling 107 (1))", clip=None,
                    model=None, dollars=0.0, note=f"the inputs are {nn.get('same_as')}'s: no model asked, $0.00")
    if refused or rc == 3:
        return dict(base, outcome="BUDGET_STOPPED", stage="start", gate="no build starts at the stop (ruling 48)",
                    clip=None, model=None, dollars=0.0, note=str(refused or "")[:400] or None)
    if pk is None:
        code = getattr(error, "code", None)
        why = (f"the build crashed: {type(error).__name__}" if isinstance(error, Exception) else
               f"the build was stopped ({type(error).__name__}" + (f", exit {code}" if code is not None else "") + ")"
               if error is not None else "the build stopped before writing its record")
        return dict(base, outcome="INDETERMINATE", stage="start", gate=why, clip=None, model=None,
                    note=(str(error)[:300] if error is not None else None))
    if pk.get("package") and pk.get("pin_refused"):
        return dict(base, outcome="HARD_REJECTED", stage="seal", gate="the pin refused the package",
                    clip=None, model=None, note=str(pk["pin_refused"])[:400])
    why, pre, hp, tried = _pass_of(pk)
    money = fp.get("spend_refused") or []
    if money:
        held = len(((pk.get("completion_reserve") or {}).get("refused") or []) if isinstance(
            pk.get("completion_reserve"), dict) else [])  # LEAN (5): the ones the completion reserve refused
        return dict(base, outcome="BUDGET_STOPPED", stage="spend",
                    gate=f"the spend stop refused {len(money)} paid call(s) (ruling 48)" +
                         (f", {held} of them held back by the completion reserve (lean 5)" if held else ""),
                    clip=None, model=sorted(set(map(str, money)))[0], note=str(why or "")[:400] or None)
    left = [x for x in (fp["undone"] if isinstance(fp.get("undone"), list) else undone(pk, pk.get("spotlight")))
            if isinstance(x, dict) and x.get("kind") not in ("money", "budget")]   # RULING 163 (4): anything unanswered
    #   or unmeasured; C: what money refused is the spend's own line above, never "unanswered"
    #   (the driver's own list when its FINGERPRINT.json has one; an older record's, read again from package.json)
    if left:
        kinds = collections.Counter(x["kind"] for x in left)
        err = next((str(x.get("error")) for x in (hp, (pk.get("hook_pool") or {})) if x.get("error")), "")
        return dict(base, outcome="INDETERMINATE", stage=UNDONE_STAGE.get(left[0]["kind"], left[0]["kind"]),
                    gate=(f"{len(left)} check(s) left unanswered or unmeasured: " +
                          ", ".join(f"{n} {k}" for k, n in kinds.most_common()))[:200],
                    clip=next((x["id"] for x in left if x.get("id")), None),
                    model=_first_model(err.split("not rated:", 1)[-1]) if err else None,
                    note=str(why or "")[:400] or None)
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


def record_build(build_dir, rc=None, error=None, refused=None, build_no=None, path=None, build_id=None, seconds=None,
                 stopped_at=None):
    """The driver's one call at the end of every build (proof_ledger.main's finally), with its wall-clock seconds per
    stage (proof_ledger.StageClock). -> the line written, or None when this run already has one."""
    titles = {x["story_id"]: x["story"] for x in lines(path) if x.get("story_id") and x.get("story")}
    line = dict(outcome_of(build_dir, rc=rc, error=error, refused=refused, build_no=build_no, titles=titles,
                           stopped_at=stopped_at),
                build_id=build_id, seconds=seconds if isinstance(seconds, dict) else None)
    line.update(ceiling_note())                          # E: a one-build ceiling exception is on its line
    return line if write_once(line, path) else None


def ceiling_note():
    """E (the owner, 15:55 ET Nov 25): the outcome line names the reservation ceiling a build ran under when it is NOT
    the $1.50 default (a one-build exception passed by the launcher, e.g. build 173's $3.00); {} at the default."""
    if os.path.join(REPO, "pipeline") not in sys.path:
        sys.path.insert(0, os.path.join(REPO, "pipeline"))
    import spend_ceiling as SC
    cap = SC.cap_usd()
    if abs(cap - SC.CAP_USD) < 1e-9:
        return {}
    return {"ceiling_usd": cap, "ceiling_note": f"a one-build exception (lean_ops --ceiling-usd {cap:.2f}); the daily "
                                                f"operating target stays ${SC.CAP_USD:.2f}"}


NOT_READY = "the pin is not READY"           # scripts/pulse_check_run.sh's words when check_pin_only refuses the pin


def amend_render(run, exit_code, said="", pin=None, path=None, seconds=None):
    """THE ACCEPTANCE LIST, item 9 (the render call, the integrator's terms, Nov 24): after the launcher hands the pin
    this run sealed to /home/ultron/protocol_pulse/scripts/pulse_check_run.sh, the build's ONE line records the call:
    "render": {"exit", "pin"}. Exit 0: it started (the line stays SEALED; the render's own lines are the integrator's).
    Any other exit: RENDER_FAILED at "render", unless the script's readiness check (check_pin_only) refused the pin,
    which is HARD_REJECTED at "render". The line is rewritten in place under the flock (one line a run, still).
    -> the amended line, or None when the run has no builder line."""
    path = path or OUTCOMES
    with open(path + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            rows, hit = [], None
            with open(path) as f:
                for x in f:
                    try:
                        r = json.loads(x)
                    except ValueError:
                        rows.append(x.rstrip("\n"))
                        continue
                    if r.get("side") == "builder" and r.get("run") == run and hit is None:
                        r = dict(r, render={"exit": int(exit_code), "pin": pin})
                        if isinstance(seconds, (int, float)):        # the time per stage: the render call's own
                            r["seconds"] = dict(r.get("seconds") or {}, **{"render call": round(float(seconds), 1)})
                        if int(exit_code) != 0:
                            refused = NOT_READY in str(said or "")
                            r.update(outcome="HARD_REJECTED" if refused else "RENDER_FAILED", stage="render",
                                     gate=("the render's readiness check refused the pin" if refused else
                                           f"the render did not start (exit {int(exit_code)})"),
                                     detail=str(said or "")[-400:] or None)
                            r["note"] = ("The video was sealed, but the render's final check refused it." if refused
                                         else "The video was sealed, but the render did not start.")
                        hit = r
                        rows.append(json.dumps(r))
                    else:
                        rows.append(x.rstrip("\n"))
            if hit is not None:
                tmp = f"{path}.{os.getpid()}.tmp"
                with open(tmp, "w") as f:
                    f.write("\n".join(rows) + "\n")
                os.replace(tmp, path)
            return hit
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


DEADLINE_EXIT = 124                          # GNU timeout's exit when it stopped the command (the render's own exits
#   are 0, 1, 3, 64, 70, 71 and 75: never 124)


def amend_stage(run, stage, exit_code, seconds=None, pin=None, said="", path=None):
    """R3 (build 172): the LEAN launch's render ("render", run with --foreground --no-telegram, so its exit is
    run_fresh's own) and delivery ("delivery") on the build's ONE line, under the flock, one line a run still:
    stage: {"exit", "seconds", "pin"} and the time per stage. DEADLINE_EXIT (the launch's one deadline stopped it):
    DEADLINE_STOPPED at the stage. The render: 0 rendered and 3 held by its own gates (the integrator's verdict) leave
    the line SEALED; its readiness check refusing the pin is HARD_REJECTED; any other exit RENDER_FAILED. The delivery:
    0 delivered; any other exit RENDER_FAILED at "delivery". -> the amended line, or None (no builder line)."""
    path = path or OUTCOMES
    code = int(exit_code)
    with open(path + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            rows, hit = [], None
            with open(path) as f:
                for x in f:
                    try:
                        r = json.loads(x)
                    except ValueError:
                        rows.append(x.rstrip("\n"))
                        continue
                    if r.get("side") == "builder" and r.get("run") == run and hit is None:
                        r = dict(r, **{stage: {"exit": code, "pin": pin, "seconds": seconds}})
                        if isinstance(seconds, (int, float)):
                            r["seconds"] = dict(r.get("seconds") or {}, **{stage: round(float(seconds), 1)})
                        new = None
                        if code == DEADLINE_EXIT:
                            new = ("DEADLINE_STOPPED", f"the launch's deadline stopped the {stage} after "
                                                       f"{seconds if seconds is not None else '?'} s")
                        elif stage == "render" and NOT_READY in str(said or ""):
                            new = ("HARD_REJECTED", "the render's readiness check refused the pin")
                        elif stage == "render" and code not in (0, 3):
                            new = ("RENDER_FAILED", f"the render ended with exit {code}")
                        elif stage == "delivery" and code != 0:
                            new = ("RENDER_FAILED", f"the delivery ended with exit {code}")
                        if new:
                            r.update(outcome=new[0], stage=stage, gate=new[1], detail=str(said or "")[-400:] or None,
                                     note=plain_note(new[0], stage, new[1]))
                        hit = r
                        rows.append(json.dumps(r))
                    else:
                        rows.append(x.rstrip("\n"))
            if hit is not None:
                tmp = f"{path}.{os.getpid()}.tmp"
                with open(tmp, "w") as f:
                    f.write("\n".join(rows) + "\n")
                os.replace(tmp, path)
            return hit
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


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
    if len(sys.argv) in (5, 6, 7) and sys.argv[1] == "--render":   # --render RUN EXIT PIN [SAID_FILE [SECONDS]]
        said = open(sys.argv[5]).read() if len(sys.argv) >= 6 and os.path.exists(sys.argv[5]) else ""
        try:
            secs = float(sys.argv[6]) if len(sys.argv) == 7 else None
        except ValueError:
            secs = None
        got = amend_render(sys.argv[2], int(sys.argv[3]), said, pin=sys.argv[4], seconds=secs)
        print(f"outcome line {'amended: ' + got['outcome'] if got else 'NOT FOUND for ' + sys.argv[2]}")
        sys.exit(0 if got else 1)
    print(__doc__.split("Usage:")[1].strip(), file=sys.stderr)
    sys.exit(2)
