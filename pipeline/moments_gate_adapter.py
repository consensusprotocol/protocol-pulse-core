#!/usr/bin/env python3
"""The pp-tests exam adapter (pipeline_pp_tests, branch pp-tests: tests/adversarial/test_moments_gates.py; corpora
format v1, pp.ci_case/1, pp.vo_case/1, pp.excl_case/1). The harness strips "expected" and "provenance" and calls:

  context_integrity(case) -> {"verdict": "pass" | "fail" | "uncertain", "why"}     law L-s
  vo_fidelity(case)       -> {"verdict": "pass" | "fail" | "uncertain", "why"}     law L-o 11 / L-t
  exclusion(case)         -> {"verdict": "keep" | "exclude" | "uncertain", "why"}  law L-u

These are the SAME gates the packager runs (context_integrity.check_contexts, vo_fidelity.check,
moments.exclusion_verdict) behind the same provider config (law L-x). The harness forbids network connections, so the
gates' model replies are recorded on a run that may call out (PP_GATES_REPLAY unset; this session's
tests/package/run_exam_record.py, which strips "expected" exactly as the harness does) and served offline under the
harness (PP_GATES_REPLAY=1). A gate that could not MEASURE (an exchange never recorded, every back-end unavailable, an
unreadable verdict) RAISES GateNotMeasured, which the harness counts as an ERROR (audit p2 M5): it is never a pass and
never a free rejection either (law L-m). A deterministic failure is a measured "fail".

The orchestrator's 09:03 ET Nov 14 order: the exam runs heimdall_first, bounded by VENDOR-REPORTED dollars on its OWN
ledger. make_router() is the ONE configuration the live recording (tests/package/run_exam_record.py) and the harness's
offline replay both use, so the replay walks exactly the chains the recording walked.
"""
import os
import re

import context_integrity as CI
import eligibility as E
import moments as M
import providers as P
import vo_fidelity as VF

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RECORD = os.environ.get("PP_GATES_RECORD_DIR") or os.path.join(REPO, "tests", "package", "fixtures", "gate_replies")
SPEND = os.environ.get("PP_GATES_SPEND") or os.path.join(REPO, "tests", "moments", "proof", "SPEND.json")
ENV = P.ENV_PATH
THREAD_SAFE = True                     # the router's ledger and recordings are safe across the harness's threads
UNIVERSE_HOURS = 24.0                  # R-29: package.current_levels' window (L-v 3): a level only from news this fresh
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")   # R-29: a news headline / summary read sentence by sentence
_router = None


class GateNotMeasured(Exception):
    """The gate could not measure this case (the harness's ERROR)."""


def make_router(chains=None):
    """The exam's router (the orchestrator's 09:03 order). Env: PP_GATES_ROUTING (default "heimdall_first"),
    PP_GATES_LIMIT_USD (default 5.00, the exam's bound) counted on PP_GATES_LIMIT_BASIS (default "reported": the
    vendors' own dollars), PP_GATES_SPEND (the exam's own ledger), PP_GATES_RECORD_DIR, PP_GATES_REPLAY=1 (offline).
    chains: pinned legs (run_exam_record --chain), else the routing's own lists."""
    return P.Router(env_path=ENV, record_dir=RECORD, replay=os.environ.get("PP_GATES_REPLAY") == "1",
                    spend_path=SPEND, chains=chains or None,
                    limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "5.00")),
                    limit_basis=os.environ.get("PP_GATES_LIMIT_BASIS", "reported"),
                    routing=os.environ.get("PP_GATES_ROUTING", "heimdall_first"))


def router():
    global _router
    if _router is None:
        _router = make_router()
    return _router


def universe_levels(universe, hours=UNIVERSE_HOURS):
    """R-29 (pp-tests' REQUESTS; the orchestrator's 09:03 order "fix it now"): the Bitcoin price levels a v1.1 case's
    universe (tonight's news) states as CURRENT, read the way package.current_levels reads sources: every sentence of a
    news item's headline and summary that names Bitcoin (eligibility.names_bitcoin), from an item published at most
    `hours` before the universe's own clock (built_at), through vo_fidelity.current_level_values. An item whose time
    cannot be read is skipped, as package.current_levels skips such a source. [] is a measurement: no current level,
    so any line stating a price as current fails PRICE_NOW. A universe with no zoned clock or no news list raises
    ValueError: the harness's ERROR, never a guess."""
    now = E._parse_time(universe["built_at"])
    if now is None:
        raise ValueError(f"the universe's clock built_at={universe.get('built_at')!r} is not a zoned time")
    if not isinstance(universe["news"], list):
        raise ValueError("the universe's news is not a list")
    out = set()
    for item in universe["news"]:
        age = E.age_hours(item.get("published_at"), now)
        if age is None or age > hours:
            continue
        for part in (item.get("headline") or "", item.get("summary") or ""):
            for sentence in SENTENCE_SPLIT.split(part):
                if sentence.strip() and E.names_bitcoin(sentence):
                    out |= set(VF.current_level_values(sentence))
    return sorted(out)


def _join(sentences):
    return " ".join(s["text"] for s in sentences or [])


def _measured(fn):
    """A case the adapter cannot read is NOT measured (the harness's ERROR), never a verdict (audit C2 K8)."""
    import functools

    @functools.wraps(fn)
    def run(case):
        try:
            return fn(case)
        except (KeyError, TypeError, ValueError, IndexError, AttributeError) as e:
            raise GateNotMeasured(f"the case cannot be read: {type(e).__name__}: {str(e)[:200]}") from None
    return run


@_measured
def context_integrity(case):
    w = case["window"]
    n0, n1 = w["selected"]
    parts, prev_turn = [], None
    for s in w["sentences"]:                     # the caption's own speaker-turn markers, when it has them
        t = s["text"]
        if s.get("turn") is not None and prev_turn is not None and s["turn"] != prev_turn:
            t = "[another speaker] " + t
        if s.get("speaker"):
            t = f"{s['speaker']}: " + t
        prev_turn = s.get("turn")
        parts.append((t, n0 <= s["n"] <= n1))
    pkg = case["package"]
    segs = [{"label": s["label"], "video_id": s["video_id"], "channel": s["channel"], "text": s["text"],
             "role": s.get("role")} for s in pkg["segments"]]
    moment = [s["label"] for s in pkg["segments"] if s.get("role") == "moment"]
    if len(moment) != 1:
        return {"verdict": "fail", "why": f"the case names {len(moment)} moment segments (expected 1)"}
    src = case.get("source") or {}
    contexts = {moment[0]: {"text": CI.mark(parts), "title": src.get("title") or "", "channel": src.get("channel") or "",
                            "published": str(src.get("published_at") or "unknown")[:16],
                            "show_date": pkg.get("date") or "unknown"}}
    bridges = list(pkg["vo"].get("bridges") or [])
    package = {"segments": segs, "vo": {"intro": pkg["vo"].get("intro") or "", "bridges": bridges,
                                        "bridges_after_clip": list(pkg["vo"].get("bridges_after_clip") or
                                                                   range(1, len(bridges) + 1)),
                                        "signoff": pkg["vo"].get("signoff") or ""},
               "title": pkg.get("title") or "", "caption": pkg.get("caption") or ""}
    try:
        res = CI.check_contexts(router(), package, contexts, writer_vendor=None)
    except P.ReplayMiss as e:
        raise GateNotMeasured(f"no recorded verdict (replay): {str(e)[:160]}") from None
    if not res.get("measured"):
        raise GateNotMeasured("; ".join(v["detail"] for v in res["violations"])[:300])
    if res["ok"]:
        return {"verdict": "pass", "why": "own sincere assertion; referents and conditions inside; entailed; no false relation"}
    return {"verdict": "fail", "why": "; ".join(f"{v['segment']}: {v['rule']} {v['detail']}" for v in res["violations"])[:600]}


@_measured
def vo_fidelity(case):
    man = case.get("manifest") or {}
    segments = {}
    for s in case["segments"]:                  # a speaker is named only when the case states it (law L-v 1)
        segments[s["label"]] = {"show": s["channel"], "speaker": s.get("speaker") or None,
                                "names": [s["speaker"]] if s.get("speaker") else [], "video_id": s["video_id"],
                                "text": _join(s["sentences"])}
    lines = [{"slot": f"{ln['slot']}_{i}", "text": ln["text"], "cites": list(ln.get("cites") or [])}
             for i, ln in enumerate(case["lines"])]
    if case.get("title") is not None:            # R-29 (v1.1): the title is judged like a line, as the packager passes it
        if not isinstance(case["title"], str) or not case["title"].strip():
            raise ValueError("the case's title is not a non-empty string")
        lines.append({"slot": "title", "text": case["title"], "cites": []})
    levels = case.get("current_levels") if isinstance(case.get("current_levels"), list) else None
    if levels is None and case.get("universe") is not None:   # R-29 (v1.1): tonight's news gives the current levels
        levels = universe_levels(case["universe"])
    try:
        res = VF.check(router(), segments, lines, writer_vendor=None, manifest=man, current_levels=levels)
    except P.ReplayMiss as e:
        raise GateNotMeasured(f"no recorded verdict (replay): {str(e)[:160]}") from None
    if not res["deterministic"]["ok"]:
        return {"verdict": "fail", "why": "; ".join(f"{v['slot']}: {v['rule']} {v['detail']}"
                                                     for v in res["deterministic"]["violations"])[:600]}
    if not res.get("measured"):
        raise GateNotMeasured("; ".join(v["detail"] for v in res["verdict"]["violations"])[:300])
    if res["ok"]:
        return {"verdict": "pass", "why": "every claim bound to its speaker's words; verdict yes with verbatim support"}
    return {"verdict": "fail", "why": "; ".join(f"{v['slot']}: {v['rule']} {v['detail']}" for v in res["violations"])[:600]}


@_measured
def exclusion(case):
    try:
        res = M.exclusion_verdict(router(), _join(case["moment"]["sentences"]),
                                  _join((case.get("context") or {}).get("before")),
                                  _join((case.get("context") or {}).get("after")))
    except P.ReplayMiss as e:
        raise GateNotMeasured(f"no recorded verdict (replay): {str(e)[:160]}") from None
    if not res.get("measured"):
        raise GateNotMeasured(res["why"])
    return {"verdict": res["verdict"], "why": res["why"]}
