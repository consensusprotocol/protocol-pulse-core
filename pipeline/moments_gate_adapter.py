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
"""
import os

import context_integrity as CI
import moments as M
import providers as P
import vo_fidelity as VF

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RECORD = os.environ.get("PP_GATES_RECORD_DIR") or os.path.join(REPO, "tests", "package", "fixtures", "gate_replies")
SPEND = os.environ.get("PP_GATES_SPEND") or os.path.join(REPO, "tests", "moments", "proof", "SPEND.json")
ENV = P.ENV_PATH
THREAD_SAFE = True                     # the router's ledger and recordings are safe across the harness's threads
_router = None


class GateNotMeasured(Exception):
    """The gate could not measure this case (the harness's ERROR)."""


def router():
    global _router
    if _router is None:
        _router = P.Router(env_path=ENV, record_dir=RECORD, replay=os.environ.get("PP_GATES_REPLAY") == "1",
                           spend_path=SPEND, limit_usd=float(os.environ.get("PP_GATES_LIMIT_USD", "64.28")))
    return _router


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
    levels = case.get("current_levels") if isinstance(case.get("current_levels"), list) else None
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
