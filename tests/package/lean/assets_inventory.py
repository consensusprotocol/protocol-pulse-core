#!/usr/bin/env python3
"""B3 (a) (the owner, 08:38 ET Nov 25): EVERY file the release renderer and its QA gates read at run time that is NOT in
git, where it is, and what reads it: docs/audits/lean/ops172/ASSETS.json, checked by `lean_ops.py launch` (and `run`)
by path and size (sha256 too where the render itself pins one) before anything is spent. Read only: stat and, for the
pinned files only, sha256; the key file and the cookie file are never opened (the key file is the namespace's own
read-only bind, lean_ops.ns_script; the cookie file is stat'ed only).

The list is the render's run-time reads traced through scripts/pulse_check_run.sh -> pipeline/run_fresh.py --pinned
--foreground --no-telegram (lean-release), each with its reader. Files the code names directly are taken from the code
(config.OUTRO_MASTER_*, run_fresh.APPROVED_OUTRO / REF_VO_MANIFEST, face_scrfd.MODEL / MODEL_SHA256, scene_shoutout's
PP_MARK and fonts, channels.json avatar_path); the rest are listed with their reader.
Not files here (checked elsewhere): the pin (the build's own output), a post-live source's cache (pin-dependent; it
resolves through the namespace's data/ overlay), Ollama's gemma3:27b (a service: the render's own preflight checks it),
/home/ultron/pp_spend (the ledger-init creates it first, B1).
Usage: python3 -B tests/package/lean/assets_inventory.py [--write]"""
import glob
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.realpath(os.path.join(HERE, "..", "..", ".."))
REL = "/home/ultron/worktrees/pp-lean-release"
LIVE = "/home/ultron/protocol_pulse"
OUT = os.path.join(REPO, "docs", "audits", "lean", "ops172", "ASSETS.json")
HF = os.path.expanduser("~/.cache/huggingface/hub")
SITE = os.path.expanduser("~/.local/lib/python3.10/site-packages")


def code_value(module_file, name):
    """A constant as the release's code writes it (the module is parsed, never imported: nothing runs)."""
    import ast
    with open(module_file) as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(f"{name} not in {module_file}")


def tracked(path):
    if not path.startswith(LIVE + "/"):
        return False
    rel = os.path.relpath(path, LIVE)
    return subprocess.run(["git", "-C", REL, "ls-files", "--error-unmatch", rel], capture_output=True).returncode == 0


def entries():
    rf, fs, cfg = (os.path.join(REL, "pipeline", x) for x in ("run_fresh.py", "face_scrfd.py", "config.py"))
    ss = os.path.join(REL, "segment_v1", "scene_shoutout.py")
    outro = code_value(rf, "APPROVED_OUTRO")
    e = [
        (code_value(cfg, "OUTRO_MASTER_16x9"), outro["16x9"][0], "config.py:108; run_fresh.py:1532 (outro_locked)"),
        (code_value(cfg, "OUTRO_MASTER_9x16"), outro["9x16"][0], "config.py:109; preflight.py:136"),
        (f"{LIVE}/brand/2026-11/conformed/outro_16x9_{outro['16x9'][0][:16]}.mp4", outro["16x9"][1],
         "config.py:152 via render16.py:620; run_fresh.py:1530-1535 (outro_locked)"),
        (f"{LIVE}/brand/2026-11/conformed/outro_9x16_{outro['9x16'][0][:16]}.mp4", outro["9x16"][1],
         "config.py:152 via render_vertical.py:1205; run_fresh.py:1530-1535"),
        (code_value(ss, "PP_MARK"), None, "segment_v1/scene_shoutout.py:25 (the credits card's logo)"),
        (f"{LIVE}/video_pipeline_v3/assets/music/confident_02.mp3", None, "config.py:197 -> render16.py:250"),
        (os.path.join(LIVE, "references", "v2f_2026-11-06", "run", "vo_audio", "VO_MANIFEST.json"), None,
         "run_fresh.py:61-62, 952-956 (the voice stage; missing: HOLD)"),
        (f"{LIVE}/segment_v1/qa_v6/blaze_face_short_range.tflite", None, "render_vertical.py:46; run_fresh.py:1829"),
        (os.path.expanduser("~/.insightface/models/buffalo_l/det_10g.onnx"), code_value(fs, "MODEL_SHA256"),
         "face_scrfd.py:12-13, 26-34 (pinned: another file STOPS the layout stage)"),
        (f"{SITE}/resemblyzer/pretrained.pt", None, "segment_v1/qa_gates.py:181-184"),
        (f"{SITE}/cv2/data/haarcascade_frontalface_default.xml", None, "segment_v1/qa_gates.py:567-568, 603-604 (G4)"),
    ]
    for p in code_value(ss, "FONT_BOLD_PATHS")[:1] + code_value(ss, "FONT_REG_PATHS")[:1]:
        e.append((p, None, "segment_v1/scene_shoutout.py:27-33 (a font; LiberationSans its fallback)"))
    for m in sorted(glob.glob(f"{LIVE}/video_pipeline_v3/assets/music/*.mp3")):
        if not m.endswith("/confident_02.mp3"):
            e.append((m, None, "preflight.py:139 (music: any one); config.py:193 (a track by mood)"))
    with open(os.path.join(REL, "pipeline", "channels.json")) as f:
        for c in json.load(f):
            a = c.get("avatar_path")
            if a and c.get("enabled", True) and not tracked(a):
                e.append((a, None, f"channels.json avatar_path ({c.get('display_name')}): preflight.py:142-143; "
                                   f"credit_rings.py:91 (G15)"))
    for snap, files in (("models--Systran--faster-whisper-large-v3", ("model.bin", "config.json",
                                                                     "preprocessor_config.json", "tokenizer.json",
                                                                     "vocabulary.json")),
                        ("models--Systran--faster-whisper-medium", ("model.bin", "config.json", "tokenizer.json",
                                                                    "vocabulary.txt"))):
        for d in sorted(glob.glob(os.path.join(HF, snap, "snapshots", "*")))[-1:]:
            for x in files:
                e.append((os.path.join(d, x), None, "gpu0.py:897-904 (whisper: select_passages.py:160, "
                                                    "cut_accept.py:158, word_diff.py:152; qa_gates.py:94 G1/G20)"))
    opt = [(f"{LIVE}/data/signoff_history.json", "signoff.py:30, 45-49 (falls back to the tracked copy)"),
           (f"{LIVE}/data/yt_cookies.txt", "select_passages.py:121-123 (optional; stat only, never opened)")]
    return e, opt


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv):
    e, opt = entries()
    files, bad = [], []
    for path, pinned, reader in e:
        st = os.stat(path) if os.path.isfile(path) else None
        row = {"path": path, "size": st.st_size if st else None, "reader": reader, "tracked": tracked(path)}
        if pinned:
            row["sha256"] = pinned
            got = sha(path) if st else None
            if got != pinned:
                bad.append(f"{path}: sha256 {str(got)[:12]} is not the pinned {pinned[:12]}")
        if st is None:
            bad.append(f"{path}: MISSING")
        files.append(row)
    for path, reader in opt:
        st = os.stat(path) if os.path.isfile(path) else None
        files.append({"path": path, "size": st.st_size if st else None, "reader": reader, "optional": True,
                      "tracked": tracked(path)})
    inv = {"taken_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "release": REL,
           "files": files, "not_files": ["the pin (the build's output)", "post-live sources (pin-dependent, data/ overlay)",
                                         "Ollama gemma3:27b (a service; the render's preflight checks it)",
                                         "/home/ultron/pp_spend (created by the ledger-init)"]}
    for r in files:
        print(f"{r['size'] if r['size'] is not None else 'MISSING':>12}  {'opt ' if r.get('optional') else ''}"
              f"{'pinned ' if r.get('sha256') else ''}{r['path']}")
    print(f"{len(files)} files; problems: {bad or 'none'}")
    if "--write" in argv and not bad:
        with open(OUT, "w") as f:
            json.dump(inv, f, indent=1)
        print(f"written: {OUT}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
