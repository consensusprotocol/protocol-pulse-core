#!/usr/bin/env python3
"""pipeline/edge_shots.py — G19 EDGE SHOTS: the guard behind shot_snap on the FINISHED video.

Recut run 6: the last 3 frames of clip_02 showed Natalie Brunell's next shot (an NVIDIA / AMD / MICRON
graphic cut in the pause before her next sentence). shot_snap now holds the speaker's shot in prepare; G19
measures the final itself (both formats): inside every talking-head segment's clean span (after any dissolve
in, before any dissolve out), no hard shot change (scene score >= shot_snap.SCENE_CUT) may fall before the
first word or after the last word. The speech times are prepare's own record (CLIP_CONTRACT.json
shot_snap.speech_on_s / speech_off_s); a talking head without that record fails closed."""
from shot_snap import scene_changes


def gate_g19(final, segments, records, fps):
    """G19 EDGE SHOTS on a final: no hard shot change inside a talking-head segment outside its speech (the
    guard behind apply(): recut run 6 showed Natalie's next shot in clip_02's last 3 frames). records:
    {label: prepare's shot_snap record} with speech_on_s / speech_off_s relative to the prepared clip's first
    frame. A talking head without a record fails (fail closed). The cut INTO the next segment is the boundary
    itself and is not a violation; a dissolve's overlap belongs to neither clean span."""
    changes = [f / fps for f, _ in scene_changes(final)]
    rows, ok = [], True
    for i, s in enumerate(segments):
        if s.get("type") != "talking_head":
            continue
        r = records.get(s["label"]) or {}
        lo = max(s["start"], segments[i - 1]["end"] if i else s["start"])
        hi = min(s["end"], segments[i + 1]["start"] if i + 1 < len(segments) else s["end"])
        if r.get("speech_on_s") is None or r.get("speech_off_s") is None:
            rows.append({"segment": s["label"], "pass": False, "why": "no speech record from prepare (fail closed)"})
            ok = False
            continue
        on, off = s["start"] + r["speech_on_s"], s["start"] + r["speech_off_s"]
        bad = [round(t, 3) for t in changes if (lo + 0.5 / fps < t < on) or (off < t < hi - 0.5 / fps)]
        rows.append({"segment": s["label"], "speech": [round(on, 3), round(off, 3)], "clean_span": [round(lo, 3), round(hi, 3)],
                     "foreign_shot_at": bad, "pass": not bad})
        ok = ok and not bad
    return ok, rows
