#!/usr/bin/env python3
"""pipeline/package_pin.py — a pp.package/1 as the existing PINNED entry point's decision (pipeline/pinned.py, schema
protocol_pulse.pinned_story.v1), so the SAME factory downstream (validate -> cut -> sentence law -> voice -> render ->
gates -> release authorisation) renders a moments-first package.

- Every segment carries `approved_text` = the moment's exact words (its source sentences, verbatim) and the record's
  transcript sha256. The pin is `machine_cuts`, so the sentence law locates the words BY TEXT in the acquired
  transcript, never by offsets. Times are YouTube coordinates (the store record's own seconds in the full video).
- `approved_by` names the machine and REVIEW ONLY. No human approved this decision (law L-q).
- The package's VO (intro, bridges with the renderer's after_clip), title, caption and its GATE INVENTORY travel in
  `moments_package`, SEALED (audit p2 C1, the L-j pattern): `package_sha256` = seal() over exactly those bytes and the
  inventory. to_pin() REFUSES a package whose inventory is missing a required gate, holds anything but exactly "PASS",
  or rests on a replayed verdict (never deliverable, law L-j). REQUESTS R7's pinned.py patch recomputes the seal and
  refuses any pin whose bytes or gates differ from what was sealed.
- `cut_evidence` (orchestrator 06:45 C / ruling 7 (1)): per segment, the INDEPENDENT recogniser's own sentence
  boundary at the IN and the OUT (its words on either side, the model, the audio window), for the sentence law's
  ruling-7 check of an edge the primary decode leaves unpunctuated. Evidence, not a gate verdict: outside the seal.
- Writes nothing itself: to_pin() returns the dict; write_pin() writes it.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone

SCHEMA = "protocol_pulse.pinned_story.v1"
REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
                  "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
MEDLEY_GATES = ("medley", "ly_shape", "house_style")   # L-y (20:30): the clips-alone verdict, the medley's shape;
                                                         # ruling 6 (22:40): PBX's copy rules on every line


def required_gates(pk):
    """The rows a package's inventory must hold, each exactly PASS: REQUIRED_GATES, and for a medley (L-y) also the
    clips-alone verdict and the L-y shape."""
    return REQUIRED_GATES + (MEDLEY_GATES if (pk or {}).get("shape") == "medley" else ())


class PinRefused(Exception):
    """The package may not become a pinned decision."""


RECENCY_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def recency_problems(segments):
    """[why] for segments that do not state the recency facts the render clock checks (ruling 1, 22:40): every segment
    a bool "time_sensitive" and "source_published_at" as "YYYY-MM-DDTHH:MM:SSZ" (UTC) that parses."""
    from datetime import datetime
    out = []
    for i, s in enumerate(segments):
        if type(s.get("time_sensitive")) is not bool:
            out.append(f"segment {i}: time_sensitive must be true or false (got {s.get('time_sensitive')!r})")
        at = s.get("source_published_at")
        ok = isinstance(at, str) and bool(RECENCY_AT.match(at))
        if ok:
            try:
                datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                ok = False
        if not ok:
            out.append(f"segment {i}: source_published_at must be YYYY-MM-DDTHH:MM:SSZ (got {at!r})")
    return out


def seal(segments, edl_vo, signoff, title, caption, gates):
    """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
    words, the transcript sha, and since ruling 1 (22:40) time_sensitive and source_published_at), the VO the renderer
    will speak (intro, bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate
    inventory."""
    body = {"segments": [{"video_id": s["video_id"], "start": round(float(s["start"]), 3),
                          "end": round(float(s["end"]), 3), "text": s["approved_text"],
                          "transcript_sha256": s.get("transcript_sha256"),
                          "time_sensitive": s.get("time_sensitive"),             # ruling 1 (22:40): the render clock
                          "source_published_at": s.get("source_published_at")}   # checks L-v 3 on these
                         for s in segments],
            "vo": {"intro": edl_vo.get("intro"), "bridges": [{"text": b["text"], "after_clip": b["after_clip"]}
                                                             for b in edl_vo.get("bridges") or []]},
            "signoff": signoff, "title": title, "caption": caption, "gates": gates}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def gate_problems(gates, required=REQUIRED_GATES):
    """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live)."""
    if not isinstance(gates, dict):
        return ["no gate inventory"]
    out = []
    for g in required:
        row = gates.get(g)
        if not isinstance(row, dict) or row.get("status") != "PASS":
            out.append(f"{g}: {(row or {}).get('status') if isinstance(row, dict) else 'missing'}")
        elif row.get("replayed") is not False:
            out.append(f"{g}: replayed or not stated (never deliverable, law L-j)")
    return out


def bridge_slots(pk):
    """The line slot of each VO bridge, in order: bridge_1, bridge_2 ...; in a medley (L-y) the line after the LAST clip
    is the "takeaway" and the one bridge before it is bridge_1."""
    vo = pk.get("vo") or {}
    after = list(vo.get("bridges_after_clip") or [])
    last = len(pk.get("segments") or []) - 1
    if pk.get("shape") == "medley":
        return ["takeaway" if a == last else f"bridge_{i + 1}" for i, a in enumerate(after)]
    return [f"bridge_{i + 1}" for i in range(len(vo.get("bridges") or []))]


def line_problems(pk):
    """The gated lines must BE the VO, title and caption that will be spoken and shown (audit C2 K3)."""
    by = {x.get("slot"): x.get("text") for x in pk.get("lines") or []}
    vo = pk.get("vo") or {}
    out = []
    if by.get("intro") != vo.get("intro"):
        out.append("intro")
    bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
    slots = bridge_slots(pk)
    if len(bridges) != len(after) or any(by.get(s) != t for s, t in zip(slots, bridges)) or \
            any(k not in slots and (k.startswith("bridge_") or k == "takeaway") for k in by if k):
        out.append("bridges")
    for k in ("title", "caption"):
        if by.get(k) != pk.get(k):
            out.append(k)
    return out


def to_pin(pk, run_name):
    problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
                                                                     for x in line_problems(pk)] + \
        recency_problems(pk.get("segments") or [])
    if problems:
        raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
    segs = []
    for i, s in enumerate(pk["segments"]):
        segs.append({"role": "hook" if i == 0 else "clip", "video_id": s["video_id"], "channel": s["channel"],
                     "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
                     "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
                     "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
                     "time_coords": "youtube", "source": {"kind": "youtube"}})
    edl_vo = {"intro": pk["vo"]["intro"],
              "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
    sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"])
    return {"schema": SCHEMA, "story_id": f"moments-{run_name}-{sha[:8]}",
            "label": "bitcoin", "headline": pk["title"],
            "approved_by": "machine:pp-selectid moments-first (REVIEW ONLY, not approved by a human)",
            "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "approval_ref": f"docs/audits/parallel/pp-selectid_STATE.md (top package, {run_name})",
            "machine_cuts": True, "segments": segs,
            "moments_package": {"schema": pk["schema"], "package_sha256": sha, "type": pk["type"],
                                "vo_kind": pk.get("vo_kind"), "edl_vo": edl_vo,
                                "signoff_expected": pk["vo"]["signoff"],
                                "title": pk["title"], "caption": pk["caption"],
                                "hook_first_words": pk["hook_first_words"],
                                "vo_jobs": {**({"intro": "context" if pk.get("shape") != "medley" else "connection"}
                                               if pk["vo"]["intro"] else {}),
                                            **{s: "takeaway" if s == "takeaway" else "connection"
                                               for s in bridge_slots(pk)}},
                                "shape": pk.get("shape"),
                                "bridge": pk.get("bridge"),
                                "supply_exception": pk.get("supply_exception"),
                                "no_voice": pk.get("no_voice"),          # ruling 3 (22:40): why no VO line ships
                                "gates": pk["gates"],
                                "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
                                           "derived_from": "gates (every required row exactly PASS, checked above)",
                                           "models": pk.get("models")},
                                "runtime_s_estimate": pk["runtime_s_estimate"],
                                "cut_evidence": pk.get("cut_evidence"),
                                "sources_30s_before": [s["url_30s_before"] for s in pk["segments"]]}}


def write_pin(pk, run_name, out_dir, name="MOMENTS_PIN.json"):
    pin = to_pin(pk, run_name)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with open(path, "w") as f:
        json.dump(pin, f, indent=1)
    return path, pin
