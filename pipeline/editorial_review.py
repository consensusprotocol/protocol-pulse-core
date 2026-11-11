#!/usr/bin/env python3
"""pipeline/editorial_review.py — AUTO's four-law editorial review, produced locally.

Before stage_validate, the local model (story_semantics.LocalLLM, gemma3:27b on GPU0) reads the
selected EDL and emits EDITORIAL_REVIEW.json in exactly the shape editorial_gate.py judges:
  clips[]   {index, adds_type, adds, adds_new_information}       (LAW 1)
  vo_jobs   {intro|bridge_N: {job, why, earned}}  (only for body VO that exists)   (LAW 2)
  takeaway  {text, concrete, supported}                           (LAW 3)
  sequence  {hook, development, payoff, progresses}               (LAW 4)
No external model is used. Deterministic code (editorial_gate) validates completeness and still
rejects known filler VO whatever the model says. If the model is inconclusive or its output cannot
be parsed, the review is written WITHOUT affirmations, so the gate HOLDs (missing/inconclusive =
HOLD). This module adds no scoring dimension; it only fills the gate's existing fields.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

import story_semantics as sm
from editorial_gate import ALLOWED_ADD_TYPES, ALLOWED_VO_JOBS

REVIEW_PROMPT = """You are the editor of a short Bitcoin news video assembled from other creators' clips.
Judge the sequence below honestly. You are not obliged to approve it.

STORY: {story}

{note}
HOOK ({hook_channel}):
<excerpt id="hook">{hook}</excerpt>

{clips}

BODY VOICE-OVER (narration we would add between clips):
{vo}

Answer four questions.
1. For EACH clip: what NEW information does it add beyond the hook and the clips before it?
   adds_type is one of {add_types}. adds_new_information is true only if it adds something the
   viewer has not already heard; repetition or vague commentary is false.
2. For EACH body voice-over line listed above (if any): its one job, one of {vo_jobs}, and whether
   it earns its place (false if it is filler or says nothing a viewer needs).
3. One concrete takeaway a viewer leaves with, supported by what the clips actually say.
   concrete=false if it is vague; supported=false if the clips do not establish it.
4. Does the sequence progress hook -> development -> payoff? Name what each part does.
   progresses=false if clips repeat each other or there is no payoff.
If you cannot judge, set "inconclusive": true and say why.

Return ONLY JSON:
{{"clips": [{{"index": <the CLIP number shown above, e.g. 1>, "adds_type": "...", "adds": "one sentence", "adds_new_information": true/false}}],
 "vo_jobs": {{"<vo key>": {{"job": "...", "why": "one sentence", "earned": true/false}}}},
 "takeaway": {{"text": "one sentence", "concrete": true/false, "supported": true/false}},
 "sequence": {{"hook": "...", "development": "...", "payoff": "...", "progresses": true/false}},
 "inconclusive": false, "inconclusive_reason": ""}}"""


def body_vo(edl):
    """The body VO lines the gate judges (intro, bridges). Signoff/credits are separate."""
    vo = edl.get("vo") or {}
    out = []
    if str(vo.get("intro") or "").strip():
        out.append(("intro", vo["intro"].strip()))
    for i, b in enumerate(vo.get("bridges") or [], 1):
        t = str((b or {}).get("text") or "").strip()
        if t:
            out.append((f"bridge_{i}", t))
    return out


def build_prompt(edl, story=None):
    clips = sorted(edl.get("clips") or [], key=lambda c: c.get("index", 0))
    cl = "\n".join(f'CLIP {c["index"]} ({c.get("channel", "")}):\n<excerpt id="clip{c["index"]}">'
                   f'{sm.quote_data(c.get("text", ""), 900)}</excerpt>' for c in clips)
    vo = "\n".join(f"- {k}: {sm.quote_data(t, 300)}" for k, t in body_vo(edl)) or "(none)"
    return REVIEW_PROMPT.format(story=sm.quote_data(story or edl.get("angle") or edl.get("topic", ""), 300),
                                note=sm.UNTRUSTED_NOTE, hook_channel=(edl.get("hook") or {}).get("channel", ""),
                                hook=sm.quote_data((edl.get("hook") or {}).get("text", ""), 900), clips=cl, vo=vo,
                                add_types=", ".join(sorted(ALLOWED_ADD_TYPES)), vo_jobs=", ".join(sorted(ALLOWED_VO_JOBS)))


def _validator(edl):
    want = sorted(c.get("index") for c in edl.get("clips") or [])
    vo_keys = {k for k, _ in body_vo(edl)}

    def v(d):
        # LocalLLM.chat_json's contract: validate RAISES on an invalid reply (its return value is ignored).
        # Returning the message instead accepted every reply (Nov 11 recut: clips judged as 0/1 for 1/2).
        if not isinstance(d, dict):
            raise ValueError("not an object")
        if d.get("inconclusive") is True:
            return
        got = sorted(j.get("index") for j in d.get("clips") or [] if isinstance(j, dict))
        if got != want:
            raise ValueError(f"clips must judge exactly the CLIP numbers {want}, got {got}")
        if not vo_keys <= set((d.get("vo_jobs") or {}).keys()):
            raise ValueError(f"vo_jobs must cover {sorted(vo_keys)}")
        for k in ("takeaway", "sequence"):
            if not isinstance(d.get(k), dict):
                raise ValueError(f"{k} must be an object")
    return v


def generate_review(llm, edl, story=None):
    """Returns the EDITORIAL_REVIEW dict. Never raises for model trouble: an unparseable or
    inconclusive answer yields a review with no affirmations (the gate then HOLDs)."""
    prompt = build_prompt(edl, story)
    rec = {"reviewed_by": f"{llm.model}@ultron-local", "review_type": "model",
           "generated_at": datetime.now(timezone.utc).isoformat(),
           "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "external_model_used": False}
    try:
        d = llm.chat_json(prompt, max_tokens=1200, validate=_validator(edl))
    except sm.LLMParseError as e:
        return {**rec, "inconclusive": True, "inconclusive_reason": f"local model output unusable: {e}",
                "raw_attempts": getattr(e, "attempts", None)}
    if d.get("inconclusive") is True:
        return {**rec, "inconclusive": True, "inconclusive_reason": str(d.get("inconclusive_reason") or ""),
                "model_output": d}
    vo_keys = {k for k, _ in body_vo(edl)}
    return {**rec, "inconclusive": False,
            "clips": d.get("clips"),
            "vo_jobs": {k: v for k, v in (d.get("vo_jobs") or {}).items() if k in vo_keys},
            "takeaway": d.get("takeaway"), "sequence": d.get("sequence")}


def write_review(llm, edl, run_dir, story=None):
    review = generate_review(llm, edl, story)
    with open(os.path.join(run_dir, "EDITORIAL_REVIEW.json"), "w") as f:
        json.dump(review, f, indent=2)
    return review
