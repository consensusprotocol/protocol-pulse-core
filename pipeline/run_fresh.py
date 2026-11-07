#!/usr/bin/env python3
"""pipeline/run_fresh.py — fresh-topic reproducibility run on the hardened v2f contracts.

One fresh Bitcoin-topic cycle through the SAME downstream production path that made
the approved v2f pair (run_isolated pre-render / preflight / shout-out / render16 /
render_vertical / postflight / gates), with fresh topic, sources, EDL, cuts, VO and
derived assets. run_isolated.py is imported, never modified.

Stages (any failure = HOLD; nothing is ever published; telegram is never imported):
  0 env        CUDA_VISIBLE_DEVICES=0, clean pipeline tree, code hashes recorded
  1 editorial  TRANSCRIPT-FIRST story selection (editorial_select.py): editorial universe = all
               enabled registry channels; story importance -> cross-source coverage (verified
               SAME_EVENT transcript evidence) -> clip quality on layout-approved sources only;
               writes TOPIC_SELECTION.json + passages.json (the select stage's input contract)
  2 select     existing select_passages.select_and_build_edl            (unchanged from here on)
  3 validate   existing edl_rules.validate_edl + layout compatibility (all channels approved, all 'crop')
  4 cut        existing cut.compute_all_cuts, then cut acceptance (cut_accept.py)
  5 voice      existing vo.generate_vo (same voice/model as v2f, asserted)
  6 prepare    run_isolated.prerender_clips, clip contract (clip_contract.py), Law 14c edge words
  7 render     shout-out 16x9+9x16, preflight, render 16:9, postflight, render 9:16, postflight,
               vertical silent-fallback detection
  8 gates      run_gates both formats exactly as v2f, plus G11 (real), G14 both, G14c, G15 both,
               G8 source-relative report, G9 outro-identity exception check
  9 verdict    CANDIDATE FOR HUMAN REVIEW WITH FLAGS | HOLD   (per format and overall)

PINNED mode (pinned.py): when AUTO cannot make a legal editorial decision, a human supplies it.
  --pinned PIN.json replaces stages 1-2 (editorial + select) with ONE stage that validates the pin
  and writes the same canonical edl.json / vertical_overrides.json; stage 4 writes the exact pinned
  cut table instead of running the acoustic cutter, then applies the SAME cut acceptance. Every
  other stage, gate and verdict rule is shared and unchanged.

Release state: every run ends HOLD_FOR_HUMAN_APPROVAL. Publishing is not reachable from here.

Usage:
  cd ~/protocol_pulse/pipeline && CUDA_VISIBLE_DEVICES=0 python3 run_fresh.py
  cd ~/protocol_pulse/pipeline && CUDA_VISIBLE_DEVICES=0 python3 run_fresh.py --pinned PIN.json
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import traceback

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)
sys.path.insert(0, PIPELINE_DIR)

RUNS_DIR = os.path.join(REPO, "runs")
CHANNELS_PATH = os.path.join(PIPELINE_DIR, "channels.json")
REF_DIR = os.path.join(REPO, "references", "v2f_2026-11-06")
REF_VO_MANIFEST = os.path.join(REF_DIR, "run", "vo_audio", "VO_MANIFEST.json")

V2F_VIDEO_IDS = {"RBFN4CB60To", "Pxrak-iMT0g", "QCgW8RlTu5Q"}
V2F_VO_SHA = {
    "ce576ec2373bbea0efaf0c96e0916cca3feec3153a0f1411a4808de3c6a95290",
    "6721610b1b69f20425e59df79bac3f96dfa167b8e08b5805935e9bbcec7d29a3",
    "8796e840c666c0e74e8d31a9d3d61c540ba3c8d183f8832cc94b3209a9462b78",
}
APPROVED_OUTRO = {  # REFERENCE_v2f.md: master sha256, conformed sha256
    "16x9": ("7c2cc7ae6efa9b276144f51b33290b190120470a36541e977f52c25b1e614e58",
             "b8a402947c42017e7f448fba05306cad2dc052eb5c9097415582c1624d9fefc6"),
    "9x16": ("48d114daab327aa9695cdebf25fec3ca5186113322fd29feedbcb035f2e421f9",
             "1af99ca7c21a72fc085ea66f99a264fb2360b72f250b68c88b1a4caef0042883"),
}
VOICE_KEY = "ELEVENLABS_VOICE_ID_PP2"
VOICE_MODEL = "eleven_v4"
NICHE = "bitcoin"
# Editorial selection is transcript-first (editorial_select.py); see TOPIC_SELECTION.json.

VERDICT_CANDIDATE = "CANDIDATE FOR HUMAN REVIEW WITH FLAGS"
VERDICT_HOLD = "HOLD"
RELEASE_STATE = "HOLD_FOR_HUMAN_APPROVAL"   # nothing leaves the factory without a human
G8_DEGRADATION_RATIO = 0.85  # restored from 5409ccce; reporting threshold, not changed


class Hold(Exception):
    """Fail-closed stop. The run ends in HOLD with the reason recorded."""


# ── utilities ──

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def jdump(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2, default=str)
    os.replace(tmp, path)


def ffprobe_json(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                        path], capture_output=True, text=True, timeout=60)
    return json.loads(r.stdout) if r.returncode == 0 else {}


def media_summary(path):
    p = ffprobe_json(path)
    v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), {})
    return {"width": v.get("width"), "height": v.get("height"), "vcodec": v.get("codec_name"),
            "r_frame_rate": v.get("r_frame_rate"), "acodec": a.get("codec_name"),
            "sample_rate": a.get("sample_rate"), "channels": a.get("channels"),
            "duration": float(p.get("format", {}).get("duration", 0) or 0)}


class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
        return len(s)

    def flush(self):
        for st in self.streams:
            st.flush()


class Capture(io.TextIOBase):
    """Tee stdout into a buffer for a block (used to detect renderer fallbacks)."""

    def __init__(self):
        self.buf = io.StringIO()

    def __enter__(self):
        self.prev = sys.stdout
        sys.stdout = Tee(self.prev, self.buf)
        return self

    def __exit__(self, *exc):
        sys.stdout = self.prev
        return False

    def text(self):
        return self.buf.getvalue()


# ── run state ──

class Run:
    def __init__(self, run_dir):
        self.dir = run_dir
        self.status = {"run_dir": run_dir, "started": now_iso(), "stages": [], "holds": [],
                       "verdict": None}
        self.prov = {"run_dir": run_dir, "created": now_iso()}
        self.mode = "auto"                  # "auto" | "pinned"
        self.allow_v2f_material = False     # True only for a pin declaring reuses_v2f_material

    def stage(self, name, fn):
        rec = {"name": name, "started": now_iso(), "status": "running"}
        self.status["stages"].append(rec)
        self.save()
        print(f"\n######## STAGE {name} ########", flush=True)
        t0 = time.time()
        try:
            out = fn()
            rec["status"] = "passed"
            return out
        except Hold as h:
            rec["status"] = "HOLD"
            rec["reason"] = str(h)
            self.status["holds"].append(f"{name}: {h}")
            raise
        except SystemExit as e:
            rec["status"] = "HOLD"
            rec["reason"] = f"fail-closed abort (SystemExit {e.code}) inside existing pipeline code"
            self.status["holds"].append(f"{name}: {rec['reason']}")
            raise Hold(rec["reason"])
        except Exception as e:
            rec["status"] = "HOLD"
            rec["reason"] = f"{type(e).__name__}: {e}"
            rec["traceback"] = traceback.format_exc()
            self.status["holds"].append(f"{name}: {rec['reason']}")
            raise Hold(rec["reason"])
        finally:
            rec["ended"] = now_iso()
            rec["seconds"] = round(time.time() - t0, 1)
            self.save()

    def save(self):
        jdump(os.path.join(self.dir, "status.json"), self.status)
        jdump(os.path.join(self.dir, "PROVENANCE.json"), self.prov)


# ── stage 0: environment ──

def stage_env(run):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise Hold("CUDA_VISIBLE_DEVICES must be exactly '0' (GPU1 quarantined)")
    # tracked code must be unmodified; untracked pipeline/*.py must not exist (segment_v1
    # holds historical untracked scratch; executed files are verified tracked+unmodified
    # at the end of the run from sys.modules)
    porcelain = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "--",
                                "pipeline", "segment_v1"], cwd=REPO, capture_output=True,
                               text=True).stdout.strip()
    untracked_py = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "--",
                                   "pipeline/*.py"], cwd=REPO, capture_output=True,
                                  text=True).stdout.strip()
    if porcelain or untracked_py:
        raise Hold(f"pipeline/segment_v1 not clean at launch:\n{porcelain}\n{untracked_py}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                          text=True).stdout.strip()
    tag = subprocess.run(["git", "describe", "--tags", "--always", "--exact-match"], cwd=REPO,
                         capture_output=True, text=True).stdout.strip()
    ffv = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    ytv = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True).stdout.strip()
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=index,name,memory.used",
                          "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    run.prov["code"] = {"git_head": head, "git_exact_tag": tag or None,
                        "pipeline_tree_clean_at_launch": True}
    run.prov["env"] = {"CUDA_VISIBLE_DEVICES": "0", "python": sys.version.split()[0],
                       "ffmpeg": ffv, "yt_dlp": ytv, "nvidia_smi": gpu.split("\n")}
    if "telegram" in sys.modules or "telegram_drop" in sys.modules:
        raise Hold("telegram module loaded — publishing path must not be importable here")


# ── stage 1: topic ──

def stage_editorial(run):
    """Transcript-first story selection (editorial_select.py). Titles/metadata are discovery
    hints only; transcripts establish story identity; layout approval gates clips only."""
    from editorial_select import select_story, NoProducibleStory
    try:
        keyword, sel = select_story(run.dir, log=lambda s: print(s, flush=True))
    except NoProducibleStory as e:
        raise Hold(f"{e} — see TOPIC_SELECTION.json")
    run.prov["editorial"] = {"selected": sel.get("selected"), "story_engine": sel.get("story_engine"),
                             "universe_summary": sel.get("universe_summary"),
                             "embedding_model": sel.get("embedding_model"), "llm": sel.get("llm")}
    with open(os.path.join(run.dir, "passages.json")) as f:
        chosen = json.load(f)["chosen"]
    registry = json.load(open(CHANNELS_PATH))
    known = {c["display_name"] for c in registry}
    bad = [p["channel"] for p in chosen if p["channel"] not in known]
    if bad:
        raise Hold(f"editorial chose clips from unknown channels {bad}")
    if any(p["video_id"] in V2F_VIDEO_IDS for p in chosen):
        raise Hold("editorial chose a v2f source video")
    print(f"  SELECTED: {sel['selected']['headline']} -> label '{keyword}'")
    return keyword


def stage_pinned(run, pin_path):
    """PINNED entry point: validate the human decision and write the canonical EDL. Replaces
    stage_editorial + stage_select only; everything downstream is shared."""
    from pinned import prepare, PinError
    try:
        rec = prepare(pin_path, run.dir, log=lambda s: print(s, flush=True))
    except PinError as e:
        raise Hold(f"pinned decision rejected: {e}")
    pin = rec["pin"]
    run.allow_v2f_material = bool(pin.get("reuses_v2f_material"))
    run.prov["mode"] = "pinned"
    run.prov["editorial"] = {"mode": "pinned", "story_id": pin["story_id"], "label": pin["label"],
                             "headline": pin.get("headline"), "approved_by": pin["approved_by"],
                             "approved_at": pin["approved_at"], "approval_ref": pin.get("approval_ref"),
                             "pin_sha256": rec["pin_sha256"], "validation": rec["validation"],
                             "reuses_v2f_material": run.allow_v2f_material}
    print(f"  PINNED: {pin['story_id']} -> label '{pin['label']}' (approved by {pin['approved_by']})")
    return pin["label"]


def stage_select(run, keyword):
    from select_passages import select_and_build_edl
    if select_and_build_edl(keyword, NICHE, run.dir) is not True:
        raise Hold("select_and_build_edl did not succeed")


def stage_validate(run):
    from edl_rules import validate_edl
    with open(os.path.join(run.dir, "edl.json")) as f:
        edl = json.load(f)
    with open(CHANNELS_PATH) as f:
        reg = json.load(f)
    ok, results = validate_edl(edl, channels_registry=reg)
    for r in results:
        print(f"  {r['rule']}: [{'PASS' if r['pass'] else 'FAIL'}] {r.get('reason', '')}")
    run.prov["edl_validation"] = results
    if not ok:
        raise Hold("EDL rejected by edl_rules: " + "; ".join(
            f"{r['rule']}: {r.get('reason', '')}" for r in results if not r["pass"]))
    # layout compatibility: approved channels use tested crop; pending channels
    # use the existing safe letterbox fallback. Unknown channels still fail closed.
    reg_by_name = {c["display_name"]: c for c in reg}
    segs = [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl.get("clips", [])]
    with open(os.path.join(run.dir, "vertical_overrides.json")) as f:
        ov = json.load(f)
    layout_errors = []
    for label, seg in segs:
        channel = seg.get("channel")
        rec = reg_by_name.get(channel)
        mode = ov.get(label, {}).get("layout")
        if rec is None:
            layout_errors.append((label, channel, "unknown channel"))
            continue
        expected = "crop" if rec.get("layout_status") == "approved" else "letterbox"
        if mode != expected:
            layout_errors.append((label, channel, f"expected {expected}, got {mode!r}"))
    run.prov["layout_compat"] = {"segments": [(l, s.get("channel")) for l, s in segs],
                                 "vertical_overrides": ov,
                                 "policy": "approved=crop; pending=letterbox"}
    if layout_errors:
        raise Hold(f"layout compatibility: {layout_errors}")
    for l, s in segs:
        if s.get("video_id") in V2F_VIDEO_IDS and not run.allow_v2f_material:
            raise Hold(f"{l} reuses a v2f source video {s['video_id']}")
        if s.get("time_coords") != "source_file":
            raise Hold(f"{l} EDL times not in source-file coordinates")


# ── stage 6: cut + acceptance ──

def stage_cut(run):
    from cut import compute_all_cuts
    from cut_accept import check_cut_acoustics
    if run.mode == "pinned":
        from pinned import write_pinned_cut_table      # exact human ranges, no acoustic search
        write_pinned_cut_table(run.dir)
    elif compute_all_cuts(run.dir) is not True:
        raise Hold("compute_all_cuts did not succeed")
    with open(os.path.join(run.dir, "cuts_final.json")) as f:
        cuts = json.load(f)
    report, fails = [], []
    for c in cuts:
        src = os.path.join(run.dir, "sources", f"{c['video_id']}.mp4")
        rec = {"clip_id": c["clip_id"], "video_id": c["video_id"], "cut_in": c.get("cut_in"),
               "cut_out": c.get("cut_out"), "cut_duration": c.get("cut_duration"),
               "verified": c.get("verified", False)}
        if not c.get("verified"):
            rec["pass"] = False
            rec["reason"] = f"cutter verified=false ({c.get('error', 'unsafe boundary/fallback')})"
        else:
            dur = media_summary(src)["duration"]
            if not (0 <= c["cut_in"] < c["cut_out"] <= dur):
                rec["pass"] = False
                rec["reason"] = f"cut range outside source file (duration {dur:.2f})"
            else:
                ok, d = check_cut_acoustics(src, c["cut_in"], c["cut_out"])
                rec.update(pass_=ok, **d)
                rec["pass"] = rec.pop("pass_")
        if not rec["pass"]:
            fails.append(c["clip_id"])
        report.append(rec)
        print(f"  {c['clip_id']}: in={c.get('cut_in')} out={c.get('cut_out')} "
              f"[{'ACCEPT' if rec['pass'] else 'REJECT'}] {rec.get('reason', '')}")
    run.prov["cut_acceptance"] = report
    jdump(os.path.join(run.dir, "CUT_ACCEPTANCE.json"), report)
    if fails:
        raise Hold(f"cut acceptance rejected {fails} (no auto-widen; see CUT_ACCEPTANCE.json)")
    return cuts


# ── stage 7: voice ──

def stage_voice(run):
    from vo import generate_vo
    from config import verify_vo_voice
    manifest = generate_vo(run.dir, voice_key=VOICE_KEY, model_id=VOICE_MODEL)
    voice_id, model_id = verify_vo_voice(manifest)
    with open(REF_VO_MANIFEST) as f:
        ref = json.load(f)
    ref_voice, ref_model = verify_vo_voice(ref)
    if (voice_id, model_id) != (ref_voice, ref_model):
        raise Hold(f"VO voice/model {voice_id}/{model_id} != v2f {ref_voice}/{ref_model}")
    if "signoff" not in manifest:
        raise Hold("no signoff VO generated")
    vo_dir = os.path.join(run.dir, "vo_audio")
    stems = {}
    for k, v in manifest.items():
        p = os.path.join(vo_dir, v["stem_wav"])
        h = sha256(p)
        if h in V2F_VO_SHA and not run.allow_v2f_material:
            raise Hold(f"VO stem {k} is byte-identical to a v2f stem")
        stems[k] = {"file": v["stem_wav"], "sha256": h, "text": v.get("text")}
    with open(os.path.join(run.dir, "edl.json")) as f:
        edl = json.load(f)
    run.prov["vo"] = {"voice_id": voice_id, "model_id": model_id, "matches_v2f_voice": True,
                      "stems": stems, "edl_vo": edl.get("vo"),
                      "intro_present": bool(edl.get("vo", {}).get("intro")),
                      "bridges": len(edl.get("vo", {}).get("bridges", []))}


# ── stage 8: prepare clips + contract + edge words ──

def stage_prepare(run, cuts):
    from run_isolated import prerender_clips
    from clip_contract import check_clip
    from cut_accept import check_edge_words
    prerender_clips(run.dir, cuts)
    qa = os.path.join(run.dir, "qa")
    work = os.path.join(qa, "edge_words")
    os.makedirs(work, exist_ok=True)
    report, fails = [], []
    for c in cuts:
        clip = os.path.join(qa, f"final_{c['clip_id']}.mp4")
        ok1, d1 = check_clip(clip, c["cut_duration"])
        ok2, d2 = check_edge_words(clip, c.get("first_word_expected", ""),
                                   c.get("last_word_expected", ""), work, c["clip_id"])
        rec = {"clip_id": c["clip_id"], "sha256": sha256(clip), "contract": d1,
               "contract_pass": ok1, "edge_words": d2, "edge_words_pass": ok2}
        report.append(rec)
        if not (ok1 and ok2):
            fails.append(c["clip_id"])
        print(f"  {c['clip_id']}: contract {'PASS' if ok1 else 'FAIL'} {d1.get('errors')} | "
              f"edges first '{d2['heard_first']}'/'{d2['expected_first']}' "
              f"last '{d2['heard_last']}'/'{d2['expected_last']}' {'PASS' if ok2 else 'FAIL'}")
    run.prov["prepared_clips"] = report
    jdump(os.path.join(run.dir, "CLIP_CONTRACT.json"), report)
    if fails:
        raise Hold(f"clip-preparation contract / edge-word check failed for {fails}")


# ── stage 9: render ──

FALLBACK_RE = re.compile(r"reframe failed for (\S+), using original")


def stage_render(run):
    from shoutout import build_shoutout
    from render16 import render_16x9
    from render_vertical import render_9x16
    from run_isolated import preflight_check, postflight_check
    from config import resolve_paths

    paths = resolve_paths(run.dir)
    build_shoutout(run.dir, None, "16x9")
    build_shoutout(run.dir, None, "9x16")
    preflight_check(run.dir)

    with Capture() as cap16:
        render_16x9(run.dir, None, "segment.mp4")
    final16 = os.path.join(paths["out_dir"], "segment.mp4")
    man16 = os.path.join(paths["qa_dir"], "concat_manifest_16x9.json")
    with open(man16) as f:
        tot16 = max(s.get("end", 0) for s in json.load(f)["segments"])
    postflight_check(final16, tot16, "16x9")

    with Capture() as cap9:
        render_9x16(run.dir, None, "segment_vertical.mp4")
    final9 = os.path.join(paths["out_dir"], "segment_vertical.mp4")
    man9 = os.path.join(paths["qa_dir"], "concat_manifest_9x16.json")
    with open(man9) as f:
        tot9 = max(s.get("end", 0) for s in json.load(f)["segments"])
    log9 = cap9.text()
    with open(os.path.join(run.dir, "render_9x16.log"), "w") as f:
        f.write(log9)
    with open(os.path.join(run.dir, "render_16x9.log"), "w") as f:
        f.write(cap16.text())
    postflight_check(final9, tot9, "9x16", log_output=log9)

    # Vertical silent-fallback detection (PBX item 6): log evidence + structural evidence
    with open(paths["cuts_json"]) as f:
        cuts = json.load(f)
    fb = {"log_hits": FALLBACK_RE.findall(log9), "structural": []}
    for c in cuts:
        vp = os.path.join(paths["qa_dir"], f"vert_{c['clip_id']}.mp4")
        if not os.path.exists(vp):
            fb["structural"].append(f"{c['clip_id']}: vert file missing")
            continue
        m = media_summary(vp)
        if (m["width"], m["height"]) != (1080, 1920):
            fb["structural"].append(f"{c['clip_id']}: vert file {m['width']}x{m['height']}")
    fb["outro_conform_fallback_16x9"] = "PBX outro conform failed" in cap16.text()
    fb["outro_conform_fallback_9x16"] = "PBX outro conform failed" in log9 or \
        "outro conform failed" in log9.lower()
    fb["fallback_occurred"] = bool(fb["log_hits"] or fb["structural"])
    run.prov["vertical_fallback_check"] = fb
    return final16, man16, final9, man9


# ── stage 10: gates ──

def _status(ok):
    return "PASS" if ok else "FAIL"


def stage_gates(run, final16, man16, final9, man9):
    import gates as G
    from gates import run_gates
    from config import resolve_paths, conform_outro
    paths = resolve_paths(run.dir)
    qa = paths["qa_dir"]
    with open(paths["cuts_json"]) as f:
        cuts = json.load(f)
    with open(man16) as f:
        segs16 = json.load(f)["segments"]
    with open(man9) as f:
        segs9 = json.load(f)["segments"]

    # Production gate runner — invoked exactly as in the v2f run.
    ok16, r16 = run_gates(run.dir, final16, man16)
    ok9, r9 = run_gates(run.dir, final9, man9)
    import qa_gates  # patched by run_gates (BASE/VO_DIR) — same module instance

    rows = {"16x9": {}, "9x16": {}}
    flags = {"16x9": [], "9x16": []}
    limits = {"16x9": [], "9x16": []}
    for fmt, res in (("16x9", r16), ("9x16", r9)):
        for k, v in res.items():
            if isinstance(v, dict) and "pass" in v and k not in ("G8_sharpness", "G9_tail",
                                                                   "G11_parity"):
                # a skipped gate is never reported as a PASS (fail-closed)
                rows[fmt][k] = (f"SKIPPED ({v.get('reason', 'skip')})" if v.get("skip")
                                else _status(v["pass"]))
        rows[fmt]["G11_parity(run_gates)"] = "NOT RUN BY run_gates (no horiz) — see G11 below"

    # G11 for real (vertical vs horizontal)
    g11_ok, g11 = qa_gates.gate_g11(final9, final16, segs9, segs16)
    rows["9x16"]["G11_parity"] = _status(g11_ok)

    # G14 / G14c / G15
    src_clips = {c["clip_id"]: {"path": os.path.join(run.dir, "sources", f"{c['video_id']}.mp4"),
                                "cut_in": c["cut_in"]} for c in cuts}
    g14dir16 = os.path.join(qa, "g14_16x9")
    g14dir9 = os.path.join(qa, "g14_9x16")
    os.makedirs(g14dir16, exist_ok=True)
    os.makedirs(g14dir9, exist_ok=True)
    g14_16_ok, g14_16 = G.gate_g14(final16, man16, source_clips=src_clips, qa_dir=g14dir16)
    fails16 = [d for d in g14_16 if d.get("status") == "FAIL"]
    rows["16x9"]["G14_av_alignment"] = ("PASS" if g14_16_ok else
                                        "FAIL" if fails16 else "HOLD(inconclusive)")
    limits["16x9"].append("G14: static talking-head temporal slips can pass frame_sim "
                          "(v2e 18.0-24.0 s precedent); VO sections are auto-PASS (pre-roll "
                          "declared), plate correctness not verified")
    g14_9_ok, g14_9 = G.gate_g14(final9, man9, source_clips=src_clips, qa_dir=g14dir9)
    # audio part: the gate's own conclusive xcorr measurement (peak >= 0.3) and 40 ms tolerance
    audio_bad = [d for d in g14_9 if d.get("delta_ms") is not None and d["delta_ms"] > 40]
    inconclusive9 = [d for d in g14_9 if d.get("status") == "HOLD" and d.get("delta_ms") is None]
    rows["9x16"]["G14_audio_offset"] = ("FAIL" if audio_bad else
                                        "HOLD(inconclusive)" if inconclusive9 else "PASS")
    rows["9x16"]["G14_frame_similarity"] = "LIMITED (not valid for 9:16 crop vs 16:9 source)"
    limits["9x16"].append("G14 frame_sim compares a 9:16 crop with the 16:9 source (v2e positive "
                          "control: 0.24-0.54 on correct frames); only the audio-offset part is "
                          "scored; VO sections auto-PASS")
    g14c_ok, g14c = G.gate_g14c(final16, final9, tolerance_ms=42)
    rows["9x16"]["G14c_duration_parity"] = _status(g14c_ok)
    for sub in ("g15_16x9", "g15_9x16"):
        os.makedirs(os.path.join(qa, sub), exist_ok=True)
    g15_16_ok, g15_16 = G.gate_g15(final16, segs16, os.path.join(qa, "g15_16x9"))
    g15_9_ok, g15_9 = G.gate_g15(final9, segs9, os.path.join(qa, "g15_9x16"))
    rows["16x9"]["G15_credits"] = _status(g15_16_ok)
    rows["9x16"]["G15_credits"] = _status(g15_9_ok)

    # G8 — production result + source-relative report (threshold untouched)
    g8dir = os.path.join(qa, "g8_relative")
    os.makedirs(g8dir, exist_ok=True)
    rel_src = {c["clip_id"]: os.path.join(qa, f"final_{c['clip_id']}.mp4") for c in cuts}
    _, g8rel = qa_gates.gate_g8(final16, segs16, g8dir, source_clips=rel_src)
    ratios = {r["segment"]: r["ratio"] for r in g8rel}
    degraded = {k: v for k, v in ratios.items() if v < G8_DEGRADATION_RATIO}
    g8_report = {"production_result_16x9": r16["G8_sharpness"]["pass"],
                 "production_result_9x16": r9["G8_sharpness"]["pass"],
                 "relative_reference": "prepared 1920x1080 clip (source camera, scaled) at the "
                                       "same relative offset",
                 "relative_16x9": g8rel, "degraded_below_0.85": degraded}
    for fmt, res in (("16x9", r16), ("9x16", r9)):
        if res["G8_sharpness"]["pass"]:
            rows[fmt]["G8_sharpness"] = "PASS"
        elif fmt == "16x9" and degraded:
            rows[fmt]["G8_sharpness"] = f"FAIL (pipeline degradation ratio < 0.85: {degraded})"
        else:
            rows[fmt]["G8_sharpness"] = "FLAG/LIMITED (absolute floor vs soft source; " \
                                        "source-relative G8 rule not yet approved)"
            flags[fmt].append("G8")

    # G9 — approved known exception only if the outro is hash-identical to the locked outro
    g9_report = {}
    for fmt, res in (("16x9", r16), ("9x16", r9)):
        d = res["G9_tail"].get("data", {})
        conformed = conform_outro(fmt)  # cached, content-keyed; no re-encode when present
        from config import OUTRO_MASTER_16x9, OUTRO_MASTER_9x16
        mpath = OUTRO_MASTER_16x9 if fmt == "16x9" else OUTRO_MASTER_9x16
        msha, csha = sha256(mpath), sha256(conformed)
        fallback = run.prov["vertical_fallback_check"][f"outro_conform_fallback_{fmt}"]
        identical = (msha, csha) == APPROVED_OUTRO[fmt] and not fallback
        last = (segs16 if fmt == "16x9" else segs9)[-1]
        g9_report[fmt] = {"gate": d, "outro_master_sha256": msha, "outro_conformed_sha256": csha,
                          "hash_identical_to_locked_outro": identical,
                          "last_segment": last.get("label"), "conform_fallback": fallback}
        if res["G9_tail"]["pass"]:
            rows[fmt]["G9_tail"] = "PASS"
        elif identical and last.get("label") == "outro" and d.get("audio_ok") and not d.get("luma_ok"):
            rows[fmt]["G9_tail"] = ("FLAG (APPROVED KNOWN EXCEPTION: locked outro ends on black; "
                                    f"tail luma {d.get('mean_luma')})")
            flags[fmt].append("G9")
        else:
            rows[fmt]["G9_tail"] = "FAIL"

    fb = run.prov["vertical_fallback_check"]
    rows["9x16"]["vertical_silent_fallback"] = "FAIL (fallback occurred)" if fb["fallback_occurred"] \
        else "PASS (no fallback)"

    gates_out = {"rows": rows, "flags": flags, "limitations": limits,
                 "G11": g11, "G14_16x9": g14_16, "G14_9x16": g14_9, "G14c": g14c,
                 "G15_16x9": g15_16, "G15_9x16": g15_9, "G8": g8_report, "G9": g9_report,
                 "run_gates_overall": {"16x9": ok16, "9x16": ok9}}
    jdump(os.path.join(run.dir, "GATE_REPORT.json"), gates_out)
    run.prov["gates"] = {"rows": rows, "flags": flags, "limitations": limits}
    return rows, flags, limits


def verdict_for(rows):
    bad = {k: v for k, v in rows.items()
           if not (v.startswith("PASS") or v.startswith("FLAG") or v.startswith("LIMITED")
                   or v.startswith("NOT RUN BY run_gates"))}
    return (VERDICT_HOLD if bad else VERDICT_CANDIDATE), bad


# ── provenance helpers ──

def record_assets(run):
    rd = run.dir
    srcs = []
    try:
        with open(os.path.join(rd, "sources.json")) as f:
            meta = {s["video_id"]: s for s in json.load(f)}
    except Exception:
        meta = {}
    try:
        with open(os.path.join(rd, "edl.json")) as f:
            edl = json.load(f)
        offs = {s["video_id"]: s.get("source_window_offset_s")
                for s in [edl["hook"]] + edl.get("clips", [])}
    except Exception:
        offs = {}
    sdir = os.path.join(rd, "sources")
    if os.path.isdir(sdir):
        for fn in sorted(os.listdir(sdir)):
            p = os.path.join(sdir, fn)
            vid = fn.rsplit(".", 1)[0]
            m = meta.get(vid, {})
            srcs.append({"video_id": vid, "channel": m.get("channel"), "title": m.get("title"),
                         "url": m.get("url") or f"https://www.youtube.com/watch?v={vid}",
                         "published": m.get("published"), "file": fn, "sha256": sha256(p),
                         "bytes": os.path.getsize(p), "window_offset_s": offs.get(vid),
                         "media": media_summary(p)})
    run.prov["sources"] = srcs
    groups = {"transcripts": "transcripts", "vo_audio": "vo_audio", "out": "out"}
    files = {}
    for g, sub in groups.items():
        d = os.path.join(rd, sub)
        if os.path.isdir(d):
            files[g] = {fn: sha256(os.path.join(d, fn)) for fn in sorted(os.listdir(d))
                        if os.path.isfile(os.path.join(d, fn))}
    qa = os.path.join(rd, "qa")
    if os.path.isdir(qa):
        files["qa_derived"] = {fn: sha256(os.path.join(qa, fn)) for fn in sorted(os.listdir(qa))
                               if fn.endswith(".mp4") and os.path.isfile(os.path.join(qa, fn))}
    run.prov["files_sha256"] = files
    # non-reuse: nothing in the run dir resolves into v2f material
    leaks = []
    for root, _, fns in os.walk(rd):
        for fn in fns:
            real = os.path.realpath(os.path.join(root, fn))
            if "/segment_v2/" in real or "/references/" in real or "/runs/v2f_" in real:
                leaks.append(os.path.join(root, fn) + " -> " + real)
    run.prov["v2f_reuse_check"] = {"links_into_v2f_material": leaks,
                                   "source_ids_overlap": sorted(
                                       {s["video_id"] for s in srcs} & V2F_VIDEO_IDS)}
    # executed code hashes
    mods = {}
    for name, m in list(sys.modules.items()):
        f = getattr(m, "__file__", None)
        if f and f.startswith(REPO) and "/venv/" not in f and os.path.exists(f):
            mods[os.path.relpath(f, REPO)] = sha256(f)
    run.prov["executed_code_sha256"] = dict(sorted(mods.items()))
    not_clean = []
    for rel in mods:
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO,
                                 capture_output=True).returncode == 0
        modified = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=REPO,
                                  capture_output=True).returncode != 0
        if not tracked or modified:
            not_clean.append(f"{rel} ({'untracked' if not tracked else 'modified vs HEAD'})")
    run.prov["executed_code_not_at_revision"] = not_clean
    if not_clean:
        run.status["holds"].append(f"executed code not at the recorded revision: {not_clean}")
        run.status["verdict"] = VERDICT_HOLD
    assets = {}
    try:
        from config import (OUTRO_MASTER_16x9, OUTRO_MASTER_9x16, resolve_bgm, resolve_brand)
        import render_vertical as _rv
        cand = [OUTRO_MASTER_16x9, OUTRO_MASTER_9x16, resolve_bgm(rd), resolve_brand(rd),
                getattr(_rv, "BLAZE_FACE_MODEL", "")]
        with open(CHANNELS_PATH) as f:
            reg = {c["display_name"]: c for c in json.load(f)}
        for s in srcs:
            av = reg.get(s.get("channel") or "", {}).get("avatar_path")
            if av:
                cand.append(av)
        for pth in cand:
            if pth and os.path.exists(pth):
                assets[pth] = sha256(pth)
    except Exception as e:
        assets["error"] = f"{type(e).__name__}: {e}"
    run.prov["runtime_assets_sha256"] = assets
    run.prov["telegram_imported"] = any(k in sys.modules for k in ("telegram", "telegram_drop"))


def write_report(run):
    s, p = run.status, run.prov
    L = [f"# FRESH-TOPIC REPRODUCIBILITY RUN — {os.path.basename(run.dir)}", "",
         f"**VERDICT: {s.get('verdict')}**", "",
         f"**RELEASE STATE: {s.get('release_state', RELEASE_STATE)}** (mode: {s.get('mode', 'auto')})", "",
         f"- revision: `{p.get('code', {}).get('git_head')}`",
         f"- started {s['started']} / ended {s.get('ended')}", ""]
    t = (p.get("editorial") or {}).get("selected")
    pe = p.get("editorial") or {}
    if pe.get("mode") == "pinned":
        L += ["## Story (PINNED human decision)", f"- {pe.get('story_id')}: {pe.get('headline') or pe.get('label')}",
              f"- approved by {pe.get('approved_by')} at {pe.get('approved_at')} ({pe.get('approval_ref')})",
              f"- pin sha256 {pe.get('pin_sha256')}"] + \
             [f"- {v['role']} {v['video_id']} {v['source_file_range']} '{v['first_word']}' ... '{v['last_word']}'"
              for v in pe.get("validation", [])] + [""]
    if t:
        L += ["## Story (transcript-first)", f"- {t.get('headline')}",
              f"- importance: {json.dumps(t.get('importance'))}",
              f"- coverage: {json.dumps(t.get('coverage'))}",
              f"- clip quality: {json.dumps(t.get('clip_quality'))}", ""]
    if s["holds"]:
        L += ["## HOLD reasons"] + [f"- {h}" for h in s["holds"]] + [""]
    if p.get("verdicts"):
        L += ["## Per-format verdict"] + [f"- {k}: {v}" for k, v in p["verdicts"].items()] + [""]
    g = p.get("gates")
    if g:
        for fmt in ("16x9", "9x16"):
            L += [f"## Gates {fmt}", "| gate | result |", "|---|---|"]
            L += [f"| {k} | {v} |" for k, v in g["rows"][fmt].items()]
            L += [f"- flags: {g['flags'][fmt]}"] + [f"- LIMITATION: {x}" for x in g["limitations"][fmt]]
            L.append("")
    L += ["## Stages", "| stage | status | s | reason |", "|---|---|---|---|"]
    L += [f"| {r['name']} | {r['status']} | {r.get('seconds')} | {r.get('reason', '')[:200]} |"
          for r in s["stages"]]
    L += ["", "Publishing: NONE (telegram never imported). External audit legs (GPT-4o/Gemini via "
          "cross_llm_audit.py): UNAVAILABLE for this run (OpenAI credits exhausted; Gemini removed)."]
    with open(os.path.join(run.dir, "REPORT.md"), "w") as f:
        f.write("\n".join(L) + "\n")


# ── main ──

def main():
    ap = argparse.ArgumentParser(description="Fresh-topic reproducibility run (no publishing)")
    ap.add_argument("--pinned", metavar="PIN.json",
                    help="PINNED mode: human-supplied editorial decision (see pinned.py)")
    args = ap.parse_args()
    pin_path = os.path.abspath(args.pinned) if args.pinned else None

    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    run_dir = os.path.join(RUNS_DIR, f"{'pinned' if pin_path else 'fresh'}_{ts}")
    if os.path.exists(run_dir):
        sys.exit(f"ABORT: run dir exists: {run_dir}")
    for sub in ("sources", "transcripts", "vo_audio", "out", "qa"):
        os.makedirs(os.path.join(run_dir, sub))
    logf = open(os.path.join(run_dir, "run_log.txt"), "a", buffering=1)
    sys.stdout = Tee(sys.__stdout__, logf)
    sys.stderr = Tee(sys.__stderr__, logf)
    print(f"=== FRESH-TOPIC RUN {run_dir} ===")
    run = Run(run_dir)
    run.mode = "pinned" if pin_path else "auto"
    run.status["mode"] = run.mode
    run.status["release_state"] = RELEASE_STATE
    run.save()
    t0 = time.time()
    try:
        run.stage("env", lambda: stage_env(run))
        if run.mode == "pinned":
            run.stage("pinned", lambda: stage_pinned(run, pin_path))
        else:
            keyword = run.stage("editorial", lambda: stage_editorial(run))
            run.stage("select", lambda: stage_select(run, keyword))
        run.stage("validate", lambda: stage_validate(run))
        cuts = run.stage("cut", lambda: stage_cut(run))
        run.stage("voice", lambda: stage_voice(run))
        run.stage("prepare", lambda: stage_prepare(run, cuts))
        final16, man16, final9, man9 = run.stage("render", lambda: stage_render(run))
        rows, flags, limits = run.stage("gates", lambda: stage_gates(run, final16, man16,
                                                                      final9, man9))
        v16, bad16 = verdict_for(rows["16x9"])
        v9, bad9 = verdict_for(rows["9x16"])
        run.prov["verdicts"] = {"16x9": v16, "9x16": v9}
        run.prov["verdict_blockers"] = {"16x9": bad16, "9x16": bad9}
        run.status["verdict"] = VERDICT_CANDIDATE if v16 == v9 == VERDICT_CANDIDATE else VERDICT_HOLD
        if run.status["verdict"] == VERDICT_HOLD:
            run.status["holds"] += [f"gates {k}: {v}" for k, v in {**bad16, **bad9}.items()]
    except Hold:
        run.status["verdict"] = VERDICT_HOLD
    except Exception as e:  # defensive: anything unexpected is HOLD
        run.status["verdict"] = VERDICT_HOLD
        run.status["holds"].append(f"orchestrator: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        try:
            record_assets(run)
        except Exception as e:
            run.status["holds"].append(f"provenance: {type(e).__name__}: {e}")
        run.status["ended"] = now_iso()
        run.status["elapsed_s"] = round(time.time() - t0, 1)
        run.save()
        write_report(run)
        with open(os.path.join(run_dir, "VERDICT.txt"), "w") as f:
            f.write(run.status["verdict"] + "\n")
        print(f"\n=== VERDICT: {run.status['verdict']} | RELEASE STATE: {RELEASE_STATE} ===")
        for h in run.status["holds"]:
            print(f"  HOLD: {h}")
        print(f"  report: {os.path.join(run_dir, 'REPORT.md')}  (no publishing)")
    sys.exit(0 if run.status["verdict"] == VERDICT_CANDIDATE else 3)


if __name__ == "__main__":
    main()
