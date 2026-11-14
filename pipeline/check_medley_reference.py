#!/usr/bin/env python3
"""The PBX-approved L-y medley of 2026-11-12 is a protected reference for SHAPE, clip-to-clip FLOW, LAYOUT and the
single closing line (references/pulse_medley_2026-11-12, docs/references/REFERENCE_PULSE_MEDLEY_2026-11-12.md;
orchestrator note '23:35'). With the CURRENT code and the reference's own frozen files, its decisions must reproduce:
  shape      edl_rules R11 passes on its EDL, and pinned.moments_vo builds the same VO slots from its PIN (the intro, and
             each line's after_clip). The wording is not compared: the takeaway predates the house-style rules.
  selection  every segment's selection lock (i0 / i1), from pinned.validate_range on the frozen transcript.
  cut        every cut_in / cut_out within one 10 ms hop, from sentence_law.write_lock_cut_table (the table stage_cut
             writes for a machine-placed pin), run on a scratch copy of the EDL.
  flow       each prepared clip's genuine lead-in / tail (sentence_law.head_tail) within 10 ms of TRANSITIONS.json; the
             junctions pulse_transitions.plan places, equal to those each render log printed (hard cuts here).
  layout     every prepared clip's 9:16 shot classes and boundaries (vertical_layout.classify).
Recency is not checked: clip_02 was 33 h old at delivery, and law L-v 3 is a publishing rule, not shape.
Exit 0 = reproduced, 1 = a decision changed, 2 = reference missing.
Usage: python3 pipeline/check_medley_reference.py [REF_DIR] [--no-layout]"""
import ast
import json
import os
import re
import shutil
import sys
import tempfile

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
REF = os.path.join(REPO, "references", "pulse_medley_2026-11-12")
TOL_S = 0.0101


def _load(ref, name):
    with open(os.path.join(ref, name)) as f:
        return json.load(f)


def main(ref=REF, layout=True):
    ref = os.path.abspath(ref)                    # the scratch dir's links must resolve from /tmp (step 8 passes it relative)
    if not os.path.isfile(os.path.join(ref, "PIN.json")):
        print(f"SKIP: protected reference missing: {ref}")
        return 2
    import edl_rules
    import pinned
    import pulse_transitions as TR
    import run_fresh
    import sentence_law as L
    pin, edl, tr = _load(ref, "PIN.json"), _load(ref, "edl.json"), _load(ref, "TRANSITIONS.json")
    cuts = {c["clip_id"]: c for c in _load(ref, "cuts_final.json")}
    segs = [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl["clips"]]
    bad = []
    if len(segs) != len(pin["segments"]) or set(cuts) != {lab for lab, _ in segs}:      # never a silent zip
        return _report([f"segments: EDL {len(segs)}, PIN {len(pin['segments'])}, cuts {sorted(cuts)}"])
    ok, msg = edl_rules.rule_r11(edl)
    if not ok:
        bad.append(f"shape: {msg}")
    try:
        vo = pinned.moments_vo(pin["moments_package"], edl["clips"], pin["segments"])
        slots = lambda v: (bool(v["intro"]), [b["after_clip"] for b in v["bridges"]])     # noqa: E731  (no words)
        if slots(vo) != slots(edl["vo"]):
            bad.append(f"shape: VO slots {slots(vo)} != reference {slots(edl['vo'])}")
    except pinned.PinError as e:
        bad.append(f"shape: the PIN's VO no longer builds: {e}")
    labels = [lab for lab, _ in segs]
    for (label, seg), ps in zip(segs, pin["segments"]):
        vid = ps["video_id"]
        if vid != seg["video_id"]:                                  # paired by identity, not by position alone
            bad.append(f"{label}: PIN segment {vid} != EDL {seg['video_id']}")
            continue
        acq = {"path": os.path.join(ref, "sources", f"{vid}.mp4"), "offset": seg["source_window_offset_s"],
               "transcript": _load(ref, os.path.join("transcripts", f"{vid}.json"))}
        try:
            v = pinned.validate_range(ps, acq)
            got, want = (v["i0"], v["i1"]), (seg["selection_lock"]["i0"], seg["selection_lock"]["i1"])
            if got != want:
                bad.append(f"{label}: selection lock {got} != reference {want}")
            print(f"  {label}: '{v['first_word']}' ... '{v['last_word']}' lock {got} (reference {want})")
        except pinned.PinError as e:
            bad.append(f"{label}: selection: {e}")
    tmp = tempfile.mkdtemp(prefix="medley_ref_")
    try:
        shutil.copy(os.path.join(ref, "edl.json"), tmp)
        for d in ("sources", "transcripts"):
            os.symlink(os.path.join(ref, d), os.path.join(tmp, d))
        table = L.write_lock_cut_table(tmp)
    finally:
        shutil.rmtree(tmp)
    if sorted(c["clip_id"] for c in table) != sorted(cuts):
        bad.append(f"cut table rows {sorted(c['clip_id'] for c in table)} != reference {sorted(cuts)}")
    for c in table:
        want = cuts.get(c["clip_id"])
        if want is None:
            continue                                                # reported by the row check above
        for k in ("cut_in", "cut_out"):
            if k not in c or abs(c[k] - want[k]) > TOL_S:
                bad.append(f"{c['clip_id']}: {k} {c.get(k, c.get('error'))} != reference {want[k]}")
        print(f"  {c['clip_id']}: cut {c.get('cut_in')}-{c.get('cut_out')} (reference {want['cut_in']}-{want['cut_out']})")
    chans = {lab: seg.get("channel") for lab, seg in segs}          # flow inputs from the EDL, never from the reference
    style = run_fresh.TRANSITION_STYLE                              # the style every run writes (run_fresh.stage 8)
    if tr["style"] != style:
        bad.append(f"flow: transition style {tr['style']!r} != the current code's {style!r}")
    if set(tr["lead_tail"]) != set(labels) or tr["channels"] != chans:
        bad.append(f"flow: TRANSITIONS.json covers {sorted(tr['lead_tail'])} with channels {tr['channels']}; the EDL "
                   f"{chans}")
    lead_tail = {}
    for cid in labels:
        ht = L.head_tail(L.SourceAudio(os.path.join(ref, "qa", f"final_{cid}.mp4")))
        lead_tail[cid] = (ht["lead_ms"] / 1000.0, ht["tail_ms"] / 1000.0)
        want = tr["lead_tail"].get(cid)
        if not want or abs(lead_tail[cid][0] - want[0]) > TOL_S or abs(lead_tail[cid][1] - want[1]) > TOL_S:
            bad.append(f"{cid}: lead-in / tail {lead_tail[cid]} != reference {want}")
    for fmt in ("16x9", "9x16"):
        man = _load(ref, os.path.join("qa", f"concat_manifest_{fmt}.json"))
        plan = TR.plan([(s["label"], None, s["type"]) for s in man["segments"]], chans, lead_tail, style)
        got = [(j["after"], j["frames"], j["kind"]) for j in plan]
        with open(os.path.join(ref, f"render_{fmt}.log")) as f:
            lines = re.findall(r"^\s*Transitions \((\w+)\): (\[.*\])\s*$", f.read(), re.M)
        if len(lines) != 1 or lines[0][0] != style:
            bad.append(f"{fmt}: the render log has {len(lines)} 'Transitions' line(s) for style {style}: {lines}")
            continue
        try:
            want = ast.literal_eval(lines[0][1])
        except (ValueError, SyntaxError) as e:
            bad.append(f"{fmt}: the render log's junctions do not parse: {e}")
            continue
        if got != want:
            bad.append(f"{fmt}: junctions {got} != the render's {want}")
        print(f"  {fmt}: junctions {got} (render {want})")
    if layout:
        import vertical_layout as V
        ref_plans = _load(ref, "VERTICAL_LAYOUT.json")
        if set(ref_plans) != set(labels):
            bad.append(f"layout reference covers {sorted(ref_plans)}, the EDL {labels}")
        for cid, rp in ref_plans.items():
            p = V.classify(os.path.join(ref, "qa", f"final_{cid}.mp4"))
            got = [(s["class"], round(s["start"], 2), round(s["end"], 2)) for s in p["shots"]]
            want = [(s["class"], round(s["start"], 2), round(s["end"], 2)) for s in rp["shots"]]
            if got != want:
                bad.append(f"{cid}: layout {got} != reference {want}")
            print(f"  {cid}: layout {got}")
    return _report(bad)


def _report(bad):
    for b in bad:
        print("  CHANGED:", b)
    print("PULSE MEDLEY REFERENCE:", "REPRODUCED" if not bad else f"{len(bad)} DECISION(S) CHANGED")
    return 0 if not bad else 1


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sys.exit(main(args[0] if args else REF, layout="--no-layout" not in sys.argv))
