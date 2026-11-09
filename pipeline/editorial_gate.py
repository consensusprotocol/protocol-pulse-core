#!/usr/bin/env python3
"""Shared pre-render editorial law gate for AUTO and PIN.

This module does not try to turn editorial taste into deterministic heuristics.
Deterministic code enforces:
- review provenance and required fields
- known filler VO rejection
- allowed evidence/job vocabularies
- fail-closed behavior when judgments are missing or inconclusive

A human or model supplies the actual editorial judgments in EDITORIAL_REVIEW.json.
The gate runs before stage_cut.
"""
import json
import os
import re

ALLOWED_ADD_TYPES = {"fact", "number", "consequence", "contradiction", "interpretation"}
ALLOWED_VO_JOBS = {"context", "connection", "contradiction", "compression"}
ALLOWED_REVIEW_TYPES = {"human", "model", "model_plus_human"}

KNOWN_FILLER_VO = {
    "this story is unfolding right now",
}


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def _fail(name, reasons):
    return {"law": name, "pass": False, "reasons": reasons}


def _pass(name, reason):
    return {"law": name, "pass": True, "reasons": [reason]}


def evaluate_editorial_gate(edl, review):
    """Return a fail-closed editorial gate result for an EDL + supplied review."""
    result = {
        "schema": "protocol_pulse_editorial_gate_v1",
        "topic": edl.get("topic"),
        "reviewed_by": None,
        "review_type": None,
        "laws": {},
        "verdict": "HOLD",
    }

    if not isinstance(review, dict):
        result["laws"]["L0_REVIEW"] = _fail(
            "L0_REVIEW", ["EDITORIAL_REVIEW.json missing or invalid"]
        )
        return result

    reviewed_by = str(review.get("reviewed_by") or "").strip()
    review_type = str(review.get("review_type") or "").strip()
    result["reviewed_by"] = reviewed_by or None
    result["review_type"] = review_type or None
    provenance_errors = []
    if not reviewed_by:
        provenance_errors.append("reviewed_by is required")
    if review_type not in ALLOWED_REVIEW_TYPES:
        provenance_errors.append(
            "review_type must be one of " + ", ".join(sorted(ALLOWED_REVIEW_TYPES))
        )
    if provenance_errors:
        result["laws"]["L0_REVIEW"] = _fail("L0_REVIEW", provenance_errors)
    else:
        result["laws"]["L0_REVIEW"] = _pass("L0_REVIEW", "review provenance present")

    # LAW 1: every post-hook clip must add genuinely new information.
    clips = sorted(edl.get("clips") or [], key=lambda c: c.get("index", 0))
    judgments = review.get("clips")
    law1_errors = []
    if not isinstance(judgments, list):
        law1_errors.append("clips review must be a list with one judgment per clip")
        judgments = []
    by_index = {j.get("index"): j for j in judgments if isinstance(j, dict)}
    for clip in clips:
        idx = clip.get("index")
        j = by_index.get(idx)
        if not j:
            law1_errors.append(f"clip {idx}: missing new-information judgment")
            continue
        add_type = str(j.get("adds_type") or "").strip()
        adds = str(j.get("adds") or "").strip()
        adds_new = j.get("adds_new_information")
        if add_type not in ALLOWED_ADD_TYPES:
            law1_errors.append(f"clip {idx}: invalid adds_type {add_type!r}")
        if not adds:
            law1_errors.append(f"clip {idx}: adds explanation is required")
        if adds_new is not True:
            law1_errors.append(f"clip {idx}: reviewer did not affirm new information")
    if law1_errors:
        result["laws"]["LAW_1_NEW_INFORMATION"] = _fail(
            "LAW_1_NEW_INFORMATION", law1_errors
        )
    else:
        result["laws"]["LAW_1_NEW_INFORMATION"] = _pass(
            "LAW_1_NEW_INFORMATION", "every post-hook clip is affirmed to add new information"
        )

    # LAW 2: body VO must have a defined job or be absent. Signoff/credits are separate.
    vo = edl.get("vo") or {}
    vo_jobs = review.get("vo_jobs")
    if not isinstance(vo_jobs, dict):
        vo_jobs = {}
    law2_errors = []

    body_vo = []
    intro = str(vo.get("intro") or "").strip()
    if intro:
        body_vo.append(("intro", intro))
    for i, bridge in enumerate(vo.get("bridges") or [], 1):
        text = str((bridge or {}).get("text") or "").strip()
        if text:
            body_vo.append((f"bridge_{i}", text))

    for key, text in body_vo:
        if _norm(text) in KNOWN_FILLER_VO:
            law2_errors.append(f"{key}: known filler VO rejected: {text!r}")
            continue
        j = vo_jobs.get(key)
        if not isinstance(j, dict):
            law2_errors.append(f"{key}: non-empty VO requires a job judgment")
            continue
        job = str(j.get("job") or "").strip()
        why = str(j.get("why") or "").strip()
        earned = j.get("earned")
        if job not in ALLOWED_VO_JOBS:
            law2_errors.append(f"{key}: invalid VO job {job!r}")
        if not why:
            law2_errors.append(f"{key}: VO job explanation is required")
        if earned is not True:
            law2_errors.append(f"{key}: reviewer did not affirm VO earns its place")

    if law2_errors:
        result["laws"]["LAW_2_VO_HAS_A_JOB"] = _fail(
            "LAW_2_VO_HAS_A_JOB", law2_errors
        )
    else:
        reason = "body VO absent" if not body_vo else "all body VO has an affirmed editorial job"
        result["laws"]["LAW_2_VO_HAS_A_JOB"] = _pass("LAW_2_VO_HAS_A_JOB", reason)

    # LAW 3: one concrete, supported viewer takeaway.
    takeaway = review.get("takeaway")
    law3_errors = []
    if not isinstance(takeaway, dict):
        law3_errors.append("takeaway judgment is required")
    else:
        text = str(takeaway.get("text") or "").strip()
        if not text:
            law3_errors.append("takeaway text is required")
        if takeaway.get("concrete") is not True:
            law3_errors.append("reviewer did not affirm takeaway is concrete")
        if takeaway.get("supported") is not True:
            law3_errors.append("reviewer did not affirm takeaway is supported by selected material")
    if law3_errors:
        result["laws"]["LAW_3_CONCRETE_TAKEAWAY"] = _fail(
            "LAW_3_CONCRETE_TAKEAWAY", law3_errors
        )
    else:
        result["laws"]["LAW_3_CONCRETE_TAKEAWAY"] = _pass(
            "LAW_3_CONCRETE_TAKEAWAY", "concrete supported takeaway present"
        )

    # LAW 4: hook -> development -> payoff must progress.
    sequence = review.get("sequence")
    law4_errors = []
    if not isinstance(sequence, dict):
        law4_errors.append("sequence judgment is required")
    else:
        for key in ("hook", "development", "payoff"):
            if not str(sequence.get(key) or "").strip():
                law4_errors.append(f"sequence.{key} is required")
        if sequence.get("progresses") is not True:
            law4_errors.append("reviewer did not affirm hook -> development -> payoff progression")
    if law4_errors:
        result["laws"]["LAW_4_SEQUENCE_PROGRESSES"] = _fail(
            "LAW_4_SEQUENCE_PROGRESSES", law4_errors
        )
    else:
        result["laws"]["LAW_4_SEQUENCE_PROGRESSES"] = _pass(
            "LAW_4_SEQUENCE_PROGRESSES", "sequence is affirmed to progress to a payoff"
        )

    result["verdict"] = (
        "READY_FOR_RENDER"
        if all(x.get("pass") for x in result["laws"].values())
        else "HOLD"
    )
    return result


def storyboard_markdown(edl, review, gate):
    """Human-readable storyboard inspection report."""
    lines = [
        "# Protocol Pulse Editorial Storyboard",
        "",
        f"**Topic:** {edl.get('topic', '')}",
        f"**Editorial verdict:** {gate.get('verdict', 'HOLD')}",
        f"**Reviewed by:** {gate.get('reviewed_by') or 'MISSING'}",
        f"**Review type:** {gate.get('review_type') or 'MISSING'}",
        "",
        "## Storyboard",
        "",
        "### Hook",
        str((edl.get("hook") or {}).get("text") or ""),
        "",
    ]
    judgments = review.get("clips") if isinstance(review, dict) else []
    judgments = judgments if isinstance(judgments, list) else []
    by_index = {j.get("index"): j for j in judgments if isinstance(j, dict)}
    for clip in sorted(edl.get("clips") or [], key=lambda c: c.get("index", 0)):
        idx = clip.get("index")
        j = by_index.get(idx) or {}
        lines += [
            f"### Clip {idx} - {clip.get('channel', '')}",
            str(clip.get("text") or ""),
            "",
            f"**Adds type:** {j.get('adds_type', 'MISSING')}",
            f"**Adds:** {j.get('adds', 'MISSING')}",
            f"**New information affirmed:** {j.get('adds_new_information', 'MISSING')}",
            "",
        ]

    vo = edl.get("vo") or {}
    lines += ["## VO", ""]
    lines.append(f"**Intro:** {vo.get('intro') or 'NONE'}")
    for i, bridge in enumerate(vo.get("bridges") or [], 1):
        lines.append(f"**Bridge {i}:** {(bridge or {}).get('text') or 'NONE'}")
    lines.append("")

    takeaway = review.get("takeaway") if isinstance(review, dict) else {}
    sequence = review.get("sequence") if isinstance(review, dict) else {}
    lines += [
        "## Viewer Takeaway",
        "",
        str((takeaway or {}).get("text") or "MISSING"),
        "",
        "## Sequence",
        "",
        f"**Hook function:** {(sequence or {}).get('hook', 'MISSING')}",
        f"**Development:** {(sequence or {}).get('development', 'MISSING')}",
        f"**Payoff:** {(sequence or {}).get('payoff', 'MISSING')}",
        f"**Progresses:** {(sequence or {}).get('progresses', 'MISSING')}",
        "",
        "## Laws",
        "",
    ]
    for name, rec in gate.get("laws", {}).items():
        status = "PASS" if rec.get("pass") else "FAIL"
        lines.append(f"### {name}: {status}")
        for reason in rec.get("reasons") or []:
            lines.append(f"- {reason}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def load_review(run_dir):
    path = os.path.join(run_dir, "EDITORIAL_REVIEW.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def run_gate(run_dir, edl):
    """Evaluate and always write machine + human-readable gate artifacts."""
    review = load_review(run_dir)
    gate = evaluate_editorial_gate(edl, review)
    with open(os.path.join(run_dir, "EDITORIAL_GATE.json"), "w") as f:
        json.dump(gate, f, indent=2)
    with open(os.path.join(run_dir, "STORYBOARD.md"), "w") as f:
        f.write(storyboard_markdown(edl, review or {}, gate))
    return gate
