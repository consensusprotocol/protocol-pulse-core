#!/usr/bin/env python3
"""pipeline/verify_pack.py — the automated verification pack (mission 4a; DEC-8 'no hand step').

What a reviewer checks by eye, produced for every run before any delivery and attached to the drop:
  1. words   G18 word-for-word rows from GATE_REPORT.json (edges + identity per clip, both finals)
  2. joins   frames at every segment boundary of both finals (last frame before, first after, and the
             middle of a dissolve), one labelled contact sheet per format
  3. credits the credits card: three frames per format and the measured G12/G15 rows
  4. sheets  (orchestrator 06:20 ET) qa/contact_sheet_<fmt>.jpg: the timestamped contact sheet of the finished
             video (visual_check.contact_sheet), and the fixed visual checklist answered FROM the sheet by the
             Heimdall vision panel (visual_check.ask_panel); any "no" or no answer = row V1_visual_checklist FAIL.
VERIFY/VERIFICATION.json records every artefact; `complete` is True only when all of them exist (every requested
frame, both G18 tables, both credits sheets, both contact sheets), and `passed` only when the pack is complete,
built WITH the vision check, and the visual verdict of both formats is exactly True (red-team A: a pack without
the vision check, a model that answered nothing, a missing frame are never a pass; release_auth reads this).
"""
import json
import os
import subprocess

FPS = 24


def _frame(video, t, out):
    if os.path.exists(out):                          # never let a frame of an earlier render stand in (GPT-gates F10)
        os.remove(out)
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1",
                        "-q:v", "3", out], check=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None                                  # the pack is then incomplete, never a crash
    return out if os.path.exists(out) else None


def _sheet(items, out, tile_w):
    """items: [(label, path)] -> one labelled grid image (3 per row); None when ANY requested frame is missing
    (GPT-gates F09: a partial sheet is not a sheet)."""
    from PIL import Image, ImageDraw
    if not items or any(not p for _, p in items):
        return None
    ims = [(lab, Image.open(p).convert("RGB")) for lab, p in items]
    th = int(round(ims[0][1].height * tile_w / ims[0][1].width))
    cols = 3
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * (th + 28)), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for k, (lab, im) in enumerate(ims):
        x, y = (k % cols) * tile_w, (k // cols) * (th + 28)
        sheet.paste(im.resize((tile_w, th)), (x, y + 28))
        d.text((x + 6, y + 6), lab, fill=(255, 255, 255))
    sheet.save(out, quality=88)
    return out


def build(run_dir, vision=True):
    vdir = os.path.join(run_dir, "VERIFY")
    os.makedirs(vdir, exist_ok=True)
    with open(os.path.join(run_dir, "GATE_REPORT.json")) as f:
        rep = json.load(f)
    pack = {"words": rep.get("G18"), "joins": {}, "credits": {"G12": {}, "G15": {}}, "vision": bool(vision)}
    for fmt, final, tile in (("16x9", "segment.mp4", 480), ("9x16", "segment_vertical.mp4", 270)):
        final = os.path.join(run_dir, "out", final)
        with open(os.path.join(run_dir, "qa", f"concat_manifest_{fmt}.json")) as f:
            segs = json.load(f)["segments"]
        items = []
        for a, b in zip(segs, segs[1:]):
            tag = f"{a['label']}->{b['label']}"
            overlap = a["end"] - b["start"]
            pts = [("last", b["start"] - 1.0 / FPS),          # A's last clean frame (before any dissolve)
                   ("first", (b["start"] if overlap <= 1e-3 else a["end"]) + 0.5 / FPS)]
            if overlap > 1e-3:
                pts.insert(1, ("mid-dissolve", b["start"] + overlap / 2))
            for name, t in pts:
                items.append((f"{fmt} {tag} {name} {t:.2f}s",
                              _frame(final, t, os.path.join(vdir, f"join_{fmt}_{tag}_{name}.jpg"))))
        pack["joins"][fmt] = {"frames": [p for _, p in items], "sheet": _sheet(
            items, os.path.join(vdir, f"joins_{fmt}.jpg"), tile)}
        sh = next((s for s in segs if s.get("type") == "shoutout"), None)     # by type, as the gates (V7)
        if sh:
            c_items = [(f"{fmt} credits {t:.2f}s", _frame(final, t, os.path.join(vdir, f"credits_{fmt}_{k}.jpg")))
                       for k, t in enumerate((sh["start"] + 1.0, (sh["start"] + sh["end"]) / 2, sh["end"] - 0.5))]
            pack["credits"][fmt] = {"frames": [p for _, p in c_items],
                                    "sheet": _sheet(c_items, os.path.join(vdir, f"credits_{fmt}.jpg"), tile)}
        pack["credits"]["G12"][fmt] = rep.get("rows", {}).get(fmt, {}).get("G12_credits")
        pack["credits"]["G15"][fmt] = rep.get(f"G15_{fmt}")
    files = [pack["joins"][f]["sheet"] for f in ("16x9", "9x16")] + \
            [pack["credits"].get(f, {}).get("sheet") for f in ("16x9", "9x16")]
    credits_rows = [pack["credits"][g].get(f) for g in ("G12", "G15") for f in ("16x9", "9x16")]
    _sheets_and_checklist(run_dir, rep, pack, vision)
    words = pack["words"] if isinstance(pack["words"], dict) else {}
    pack["complete"] = all(isinstance(words.get(f), list) and words[f] for f in ("16x9", "9x16")) \
        and all(p and os.path.exists(p) for p in files) \
        and all(r is not None for r in credits_rows) \
        and all(os.path.exists((pack["contact_sheets"].get(f) or {}).get("path") or "") for f in ("16x9", "9x16"))
    pack["passed"] = pack["complete"] is True and pack["vision"] is True and \
        all((pack["visual"].get(f) or {}).get("ok") is True for f in ("16x9", "9x16"))
    tmp = os.path.join(vdir, "VERIFICATION.json.tmp")
    with open(tmp, "w") as f:
        json.dump(pack, f, indent=2, default=str)
    os.replace(tmp, os.path.join(vdir, "VERIFICATION.json"))
    return pack


def panel_ok(per):
    """The panel passed the sheet: EVERY vision model answered EVERY checklist line (the whole-sheet next-shot
    line is advisory, asked per cut instead) and every answer is exactly ok True (GPT-gates F07, Claude-gates
    M1: a model that answered nothing, a missing line, a truthy string are never a pass)."""
    import visual_check as VC
    keys = [k for k, _ in VC.CHECKLIST if k != NEXT_SHOT]
    if not isinstance(per, dict) or set(per) != set(VC.VISION_MODELS):
        return False
    return all(isinstance(d, dict) and isinstance(d.get("rows"), dict) and
               all(isinstance(d["rows"].get(k), dict) and d["rows"][k].get("ok") is True for k in keys)
               for d in per.values())


NEXT_SHOT = "no_next_shot_before_transition"


def _sheets_and_checklist(run_dir, rep, pack, vision):
    """Contact sheet per format (qa/) and the visual checklist answered from it; V1 rows written into
    GATE_REPORT.json (a new check on top of the gates: any "no", missing answer or route error = FAIL)."""
    import visual_check as VC
    import vertical_layout
    with open(os.path.join(run_dir, "edl.json")) as f:
        edl = json.load(f)
    note = vertical_layout.layout_note(edl)
    segs_edl = [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl.get("clips", [])]
    channels_note = ("Channels whose clips appear in this video (from the edit decision list): " +
                     ", ".join(f"{s.get('channel')} ({label})" for label, s in segs_edl) + ".")
    pack["contact_sheets"], pack["visual"] = {}, {}
    v1_rows = {}                                        # fmt -> (exact verdict, note, answers counted)
    for fmt, final in (("16x9", "segment.mp4"), ("9x16", "segment_vertical.mp4")):
        with open(os.path.join(run_dir, "qa", f"concat_manifest_{fmt}.json")) as f:
            segs = json.load(f)["segments"]
        sheet = os.path.join(run_dir, "qa", f"contact_sheet_{fmt}.jpg")
        if os.path.exists(sheet):                       # a copied run (transition options) carries the old sheet:
            os.remove(sheet)                            # never let the panel read a sheet of another render
        try:
            pack["contact_sheets"][fmt] = VC.contact_sheet(os.path.join(run_dir, "out", final), segs, fmt, sheet,
                                                           os.path.join(run_dir, "VERIFY", f"sheet_{fmt}"))
        except Exception as e:                          # no sheet = incomplete pack and a failing V1 row
            pack["contact_sheets"][fmt] = {"error": f"{type(e).__name__}: {e}"}
        if not vision:                                   # the vision check is off: V1 did not run (never a pass)
            v1_rows[fmt] = ("SKIPPED", "vision check off for this pack", 0)
            continue
        if "error" in pack["contact_sheets"][fmt]:
            pack["visual"][fmt] = {"ok": False, "error": f"no contact sheet: {pack['contact_sheets'][fmt]['error']}"}
        else:
            try:
                ok, per = VC.ask_panel(sheet, fmt, layout_note=note if fmt == "9x16" else "",
                                       channels_note=channels_note)
                # the next-shot line is answered one cut at a time (below); the whole-sheet answer stays as
                # advisory text (run 6: it misread tile labels and missed the real defect)
                ok = panel_ok(per)
                pack["visual"][fmt] = {"ok": ok, "per_model": per,
                                       "sheet_next_shot_advisory": {m: ((d or {}).get("rows") or {}).get(NEXT_SHOT)
                                                                    for m, d in (per or {}).items()}}
            except Exception as e:
                pack["visual"][fmt] = {"ok": False, "error": f"vision route: {type(e).__name__}: {e}"}
        v = pack["visual"][fmt]
        if fmt == "9x16" and "error" not in pack["contact_sheets"][fmt]:
            try:                                        # letterbox asked ONE frame per shot (E-FAIL-022)
                lp = os.path.join(run_dir, "VERTICAL_LAYOUT.json")
                layout = json.load(open(lp)) if os.path.exists(lp) else {}
                lb_ok, lb_rows = VC.letterbox_check(VC.shot_frames(
                    os.path.join(run_dir, "out", final), segs, layout, os.path.join(run_dir, "VERIFY", "shots_9x16")))
            except Exception as e:
                lb_ok, lb_rows = False, [{"error": f"{type(e).__name__}: {e}"}]
            lb_ok = lb_ok is True and bool(lb_rows)            # zero shots asked is no answer (Claude-gates M2)
            v["letterbox_per_shot"] = {"ok": lb_ok, "shots": lb_rows}
            v["ok"] = v["ok"] is True and lb_ok
        if "error" not in pack["contact_sheets"][fmt]:
            try:                                        # next shot before a cut: ONE pair of frames per cut
                bd_ok, bd_rows = VC.boundary_check(VC.boundary_pairs(
                    os.path.join(run_dir, "out", final), segs, os.path.join(run_dir, "VERIFY", f"cuts_{fmt}")))
            except Exception as e:
                bd_ok, bd_rows = False, [{"error": f"{type(e).__name__}: {e}"}]
            bd_ok = bd_ok is True and len(bd_rows) == max(0, len(segs) - 1) and bool(bd_rows)   # every cut asked
            v["boundaries"] = {"ok": bd_ok, "cuts": bd_rows}
            v["ok"] = v["ok"] is True and bd_ok
        per_model = {m: d for m, d in (v.get("per_model") or {}).items() if isinstance(d, dict)}
        nos = sorted({k for d in per_model.values() for k, r in (d.get("rows") or {}).items()
                      if not (isinstance(r, dict) and r.get("ok") is True) and k != NEXT_SHOT})
        if not (v.get("boundaries") or {"ok": True})["ok"]:
            bad = [r.get("boundary", "?") for r in v["boundaries"]["cuts"] if isinstance(r, dict) and not r.get("ok")]
            nos.append(f"next shot before the cut: {', '.join(bad)}")
        if not (v.get("letterbox_per_shot") or {"ok": True})["ok"]:
            bad = [f"{r.get('label')}#{r.get('shot')}" for r in v["letterbox_per_shot"]["shots"]
                   if isinstance(r, dict) and not r.get("ok")]
            nos.append(f"letterbox per shot: {', '.join(bad)}")
        why = "; ".join(x for x in (v.get("error"), ("no/missing: " + ", ".join(nos)) if nos else None) if x)
        answered = sum(len(d.get("rows") or {}) for d in per_model.values()) + \
            len((v.get("letterbox_per_shot") or {}).get("shots") or []) + len((v.get("boundaries") or {}).get("cuts") or [])
        v1_rows[fmt] = ("PASS", None, answered) if v["ok"] is True else ("FAIL", why or "no answer", answered)
    # V1 joins the report: re-read NOW (never rewrite a snapshot taken minutes ago) and replace atomically
    path = os.path.join(run_dir, "GATE_REPORT.json")
    with open(path) as f:
        cur = json.load(f)
    for fmt, (verdict, note, n) in v1_rows.items():
        cur.setdefault("rows", {}).setdefault(fmt, {})["V1_visual_checklist"] = verdict
        cur.setdefault("evidence", {}).setdefault(fmt, {})["V1_visual_checklist"] = \
            {"executed": verdict != "SKIPPED", "samples": n}
        notes = cur.setdefault("notes", {}).setdefault(fmt, {})
        if note:
            notes["V1_visual_checklist"] = note
        else:
            notes.pop("V1_visual_checklist", None)
    if vision:
        cur["V1"] = pack["visual"]
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cur, f, indent=2, default=str)
    os.replace(tmp, path)
