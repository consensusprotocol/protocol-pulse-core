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
VERIFY/VERIFICATION.json records every artefact; `complete` is True only when all of them exist.
"""
import json
import os
import subprocess

FPS = 24


def _frame(video, t, out):
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1",
                        "-q:v", "3", out], check=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None                                  # the pack is then incomplete, never a crash
    return out if os.path.exists(out) else None


def _sheet(items, out, tile_w):
    """items: [(label, path)] -> one labelled grid image (3 per row)."""
    from PIL import Image, ImageDraw
    ims = [(lab, Image.open(p).convert("RGB")) for lab, p in items if p]
    if not ims:
        return None
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
    pack = {"words": rep.get("G18"), "joins": {}, "credits": {"G12": {}, "G15": {}}}
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
        sh = next((s for s in segs if s["label"] == "shoutout"), None)
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
    pack["complete"] = bool(pack["words"]) and all(p and os.path.exists(p) for p in files) \
        and all(r is not None for r in credits_rows) \
        and all(os.path.exists((pack["contact_sheets"].get(f) or {}).get("path") or "") for f in ("16x9", "9x16"))
    with open(os.path.join(vdir, "VERIFICATION.json"), "w") as f:
        json.dump(pack, f, indent=2, default=str)
    return pack


def _sheets_and_checklist(run_dir, rep, pack, vision):
    """Contact sheet per format (qa/) and the visual checklist answered from it; V1 rows written into
    GATE_REPORT.json (a new check on top of the gates: any "no", missing answer or route error = FAIL)."""
    import visual_check as VC
    import vertical_layout
    with open(os.path.join(run_dir, "edl.json")) as f:
        edl = json.load(f)
    note = vertical_layout.layout_note(edl)
    pack["contact_sheets"], pack["visual"] = {}, {}
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
        if not vision:
            continue
        if "error" in pack["contact_sheets"][fmt]:
            pack["visual"][fmt] = {"ok": False, "error": f"no contact sheet: {pack['contact_sheets'][fmt]['error']}"}
        else:
            try:
                ok, per = VC.ask_panel(sheet, fmt, layout_note=note if fmt == "9x16" else "")
                pack["visual"][fmt] = {"ok": ok, "per_model": per}
            except Exception as e:
                pack["visual"][fmt] = {"ok": False, "error": f"vision route: {type(e).__name__}: {e}"}
        v = pack["visual"][fmt]
        nos = sorted({k for d in (v.get("per_model") or {}).values() for k, r in (d.get("rows") or {}).items()
                      if not r.get("ok")})
        rep.setdefault("rows", {}).setdefault(fmt, {})["V1_visual_checklist"] = \
            "PASS" if v["ok"] else f"FAIL ({v.get('error') or 'no/missing: ' + ', '.join(nos)})"
    if vision:
        rep["V1"] = pack["visual"]
        with open(os.path.join(run_dir, "GATE_REPORT.json"), "w") as f:
            json.dump(rep, f, indent=2, default=str)
