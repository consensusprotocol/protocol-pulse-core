#!/usr/bin/env python3
"""Law L-d: the PBX-approved preview of 2026-11-11 is a protected reference (references/pulse_preview_2026-11-11,
docs/references/REFERENCE_PULSE_PREVIEW_2026-11-11.md). With the CURRENT code and the reference's own frozen
sources, its decisions must reproduce:
  selection  every segment's selection lock (first / last word, i0 / i1) from the PIN's approved text, the way
             pinned.py anchors it (sentence_law.anchor, start - 3 s .. end + 3 s)
  cut        every segment's accepted cut_in / cut_out (sentence_law.edge_plan + accepted_cut) within one 10 ms hop
  layout     every prepared clip's 9:16 shot classes and boundaries (vertical_layout.classify), on the
             reference's prepared clips
Edge FADES are not compared: the reference's named defect 2 (Natalie's 'rally' under the fade) is corrected
by law L-b, which changes them by design. Exit 0 = reproduced, 1 = a decision changed, 2 = reference missing.
Usage: python3 pipeline/check_preview_reference.py [--no-layout]"""
import json
import os
import sys

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
REF = os.path.join(REPO, "references", "pulse_preview_2026-11-11")
TOL_S = 0.0101


def main(layout=True):
    if not os.path.isfile(os.path.join(REF, "PIN.json")):
        print(f"SKIP: protected reference missing: {REF}")
        return 2
    import sentence_law as L
    pin = json.load(open(os.path.join(REF, "PIN.json")))
    edl = json.load(open(os.path.join(REF, "edl.json")))
    cuts = {c["clip_id"]: c for c in json.load(open(os.path.join(REF, "cuts_final.json")))}
    segs = [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl["clips"]]
    bad = []
    if len(segs) != len(pin["segments"]) or set(cuts) != {lab for lab, _ in segs}:      # never a silent zip
        bad.append(f"segments: EDL {len(segs)}, PIN {len(pin['segments'])}, cuts {sorted(cuts)}")
    for (label, seg), ps in zip(segs, pin["segments"]):
        vid = ps["video_id"]
        words = json.load(open(os.path.join(REF, "transcripts", f"{vid}.json")))["words"]
        a = L.anchor(words, ps["approved_text"], t0=ps["start"] - 3.0, t1=ps["end"] + 3.0)
        lock = seg["selection_lock"]
        if a is None or (a[0], a[1]) != (lock["i0"], lock["i1"]):
            bad.append(f"{label}: selection lock {a} != reference ({lock['i0']}, {lock['i1']})")
            continue
        src = os.path.join(REF, "sources", f"{vid}.mp4")
        sa = L.SourceAudio(src)
        pick = L.accepted_cut(src, L.edge_plan(sa, words, a[0], a[1]), sa=sa)
        ref = cuts[label]
        if pick is None:
            bad.append(f"{label}: no accepted cut (reference {ref['cut_in']}-{ref['cut_out']})")
            continue
        for k in ("cut_in", "cut_out"):
            if abs(pick[k] - ref[k]) > TOL_S:
                bad.append(f"{label}: {k} {pick[k]} != reference {ref[k]}")
        print(f"  {label}: '{lock['first_word']}' ... '{lock['last_word']}' cut {pick['cut_in']}-{pick['cut_out']} "
              f"(reference {ref['cut_in']}-{ref['cut_out']})")
    if layout:
        import vertical_layout as V
        ref_plans = json.load(open(os.path.join(REF, "VERTICAL_LAYOUT.json")))
        if set(ref_plans) != {lab for lab, _ in segs}:
            bad.append(f"layout reference covers {sorted(ref_plans)}, the cut has {[lab for lab, _ in segs]}")
        for cid, rp in ref_plans.items():
            plan = V.classify(os.path.join(REF, "qa", f"final_{cid}.mp4"))
            got = [(s["class"], round(s["start"], 2), round(s["end"], 2)) for s in plan["shots"]]
            want = [(s["class"], round(s["start"], 2), round(s["end"], 2)) for s in rp["shots"]]
            if got != want:
                bad.append(f"{cid}: layout {got} != reference {want}")
            print(f"  {cid}: layout {got}")
    for b in bad:
        print("  CHANGED:", b)
    print("PULSE PREVIEW REFERENCE:", "REPRODUCED" if not bad else f"{len(bad)} DECISION(S) CHANGED")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(layout="--no-layout" not in sys.argv))
