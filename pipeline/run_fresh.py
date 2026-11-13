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
  4 cut        cuts placed inside the pauses bounding each LOCKED sentence (sentence_law.py; human
               PINs: the exact pinned table), then cut acceptance (cut_accept.py); no snapping
  4b sentence_law  G16 SENTENCE_BOUNDARY before rendering (hard stop)
  5 voice      existing vo.generate_vo (same voice/model as v2f, asserted)
  6 prepare    run_isolated.prerender_clips, clip contract (clip_contract.py), Law 14c edge words
               (expected words = the selection lock, never recomputed)
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
import contextlib
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
import sentence_law as L  # noqa: E402  (sentence law: selection locks, G16/G17)

RUNS_DIR = os.path.join(REPO, "runs")
CHANNELS_PATH = os.path.join(PIPELINE_DIR, "channels.json")
REF_DIR = os.path.join(REPO, "references", "v2f_2026-11-06")
REF_VO_MANIFEST = os.path.join(REF_DIR, "run", "vo_audio", "VO_MANIFEST.json")
# ruling 27 (orchestrator 2026-11-12 '23:20'): a run is bound to the git TREE of what it executes and reads from git,
# not to HEAD: pipeline/ (its modules, the registry channels.json, its data), segment_v1/ (the frozen scripts, the
# brand mark, the face model), scripts/ (the launcher) and video_pipeline_v3/relay.py (the key loader). docs/ and *.md
# outside them are not code: a docs commit while a run is in flight is accepted. Untracked runtime assets (the brand/
# outros, the music) are not in any tree: runtime_assets_sha256 records them per run.
EXEC_PATHS = ("pipeline", "segment_v1", "scripts", "video_pipeline_v3/relay.py")

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


import gpu0  # noqa: E402  (law L-r: the one owner of GPU0; pipeline/ is this file's directory)


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
        self.machine_cuts = False          # True only for machine-built PINs (enables snap)
        self.allow_v2f_material = False     # True only for a pin declaring reuses_v2f_material
        self.sampler = None                 # L-r: gpu0.PeakSampler, started in stage_env
        self.gpu0_stack = contextlib.ExitStack()   # L-r: holds the GPU0 lease from stage_env to the end of main

    def _attempts(self, name, fn):
        """Law L-r item 3. A CUDA out-of-memory gets ONE retry of the same step: everything this run owns is released
        (outside the except clause, the exception chain's frames broken first, so the model that failed can be freed)
        and nvidia-smi must show GPU0 free; BOTH attempts go to PROVENANCE (gpu0_oom: the first with its error and
        traceback, the second with its outcome: passed, out of memory again, or the failure that ended it); a second
        out-of-memory is a HOLD naming every GPU0 process, and any other failure of the retry still carries the first
        out-of-memory. Every other GPU0 stop is a HOLD carrying its real cause, never another error. Retrying a stage
        repeats it whole: the stages that change files in place (lead-in pads, shot snaps) do so inside stage_prepare,
        which regenerates every clip from its source first."""
        first = None                                      # the first attempt's out-of-memory record, once there is one

        def retry_ended(outcome):
            self.prov["gpu0_oom"][name].append({"attempt": 2, "at": now_iso(), "outcome": outcome[:600]})
            self.save()
        for attempt in (1, 2):
            if self.sampler:
                self.sampler.set(name)
            oom = tb = None
            try:
                out = fn()
                if first is not None:
                    retry_ended("passed")
                return out
            except gpu0.Gpu0Stop as e:
                if not isinstance(e, gpu0.GpuOOM):
                    why = f"GPU0 {type(e).__name__}: {e}"
                    if first is None:
                        raise Hold(f"infrastructure: {name}: {why}") from None
                    retry_ended(f"failed: {why}")
                    raise Hold(f"infrastructure: {name}: CUDA out of memory on attempt 1 ({first['error'][:200]}); "
                               f"the retry then stopped: {why}") from None
                oom, tb = f"{type(e).__name__}: {str(e)[:400]}", traceback.format_exc()[-3000:]
                gpu0.drop_traceback(e)
            except Hold as h:
                if first is None:
                    raise
                retry_ended(f"held: {h}")
                raise Hold(f"infrastructure: {name}: CUDA out of memory on attempt 1 ({first['error'][:200]}); the "
                           f"retry then held: {h}") from None
            except Exception as e:
                if not gpu0.is_oom(e):
                    if first is None:
                        raise
                    retry_ended(f"failed: {type(e).__name__}: {e}")
                    raise Hold(f"infrastructure: {name}: CUDA out of memory on attempt 1 ({first['error'][:200]}); the "
                               f"retry then failed: {type(e).__name__}: {e}") from None
                oom, tb = f"{type(e).__name__}: {str(e)[:400]}", traceback.format_exc()[-3000:]
                gpu0.drop_traceback(e)
            # here, outside the except clause: the failed call's frames are no longer pinned by a live exception
            entry = {"attempt": attempt, "at": now_iso(), "error": oom, "traceback": tb}
            try:
                entry["gpu0_memory"], entry["gpu0_processes"] = gpu0.memory(), gpu0.processes()
                on = gpu0.describe(entry["gpu0_processes"])
            except gpu0.Gpu0Stop as e2:
                entry["gpu0_unreadable"] = str(e2)
                on = f"GPU0 unreadable ({e2})"
            self.prov.setdefault("gpu0_oom", {}).setdefault(name, []).append(entry)
            self.save()
            if attempt == 2:
                raise Hold(f"infrastructure: {name}: CUDA out of memory twice ({oom[:240]}); on GPU0: {on}")
            first = entry
            print(f"  GPU0 OUT OF MEMORY in stage {name}: {oom[:200]}; releasing everything this run owns, retrying "
                  f"once", flush=True)
            try:
                entry["release"] = gpu0.release_all()
            except gpu0.Gpu0Stop as e2:
                raise Hold(f"infrastructure: {name}: CUDA out of memory ({oom[:200]}) and GPU0 did not come free: "
                           f"{type(e2).__name__}: {e2}") from None
            self.save()

    def stage(self, name, fn):
        rec = {"name": name, "started": now_iso(), "status": "running"}
        self.status["stages"].append(rec)
        self.save()
        print(f"\n######## STAGE {name} ########", flush=True)
        t0 = time.time()
        try:
            out = self._attempts(name, fn)
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
            if self.sampler:
                self.sampler.set(None)
                if name in self.sampler.peaks:
                    rec["gpu0_peak_mib"] = self.sampler.peaks[name]
                if name in self.sampler.peaks_by_gpu.get(1, {}):           # law L-r: a table per GPU
                    rec["gpu1_peak_mib"] = self.sampler.peaks_by_gpu[1][name]
            self.save()

    def save(self):
        jdump(os.path.join(self.dir, "status.json"), self.status)
        jdump(os.path.join(self.dir, "PROVENANCE.json"), self.prov)


# ── stage 0: environment ──

def stage_env(run):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise Hold("CUDA_VISIBLE_DEVICES must be exactly '0': renders and their gates run on GPU0 (law L-r layout)")
    code = launch_code()                          # ruling 27: one snapshot of the executable trees
    tag = subprocess.run(["git", "describe", "--tags", "--always", "--exact-match"], cwd=REPO,
                         capture_output=True, text=True).stdout.strip()
    ffv = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    ytv = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True).stdout.strip()
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=index,name,memory.used",
                          "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    run.prov["code"] = {**code, "git_exact_tag": tag or None}
    run.prov["env"] = {"CUDA_VISIBLE_DEVICES": "0", "python": sys.version.split()[0],
                       "ffmpeg": ffv, "yt_dlp": ytv, "nvidia_smi": gpu.split("\n")}
    if "telegram" in sys.modules or "telegram_drop" in sys.modules:
        raise Hold("telegram module loaded — publishing path must not be importable here")
    # L-r: the run holds the GPU0 lease to the end of main (custody of scripts/pulse_check_run.sh's fd 8, else its
    # own), nothing foreign may hold GPU0 memory at its start, and GPU0 memory is sampled per stage from here on
    run.gpu0_stack.enter_context(gpu0.lease(f"run_fresh {os.path.basename(run.dir)} (pid {os.getpid()})"))
    foreign = gpu0.foreign()
    if foreign:
        raise Hold(f"infrastructure: env: GPU0 memory is held by a process that is not this run's: "
                   f"{gpu0.describe(foreign)}")
    run.prov["gpu0"] = {"at_start": {"memory_mib": gpu0.memory(), "processes": gpu0.processes(),
                                     "ollama_resident": gpu0.ollama_resident(), "holder": gpu0.holder()}}


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
    free_gpu0_for_whisper(run, "pinned")   # pinned.acquire runs Whisper on GPU0 (E-FAIL-052: the preflight's model OOM'd it)
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


def stage_review(run):
    """AUTO only: local model writes EDITORIAL_REVIEW.json for the four-law gate in stage_validate.
    No external model. Missing/inconclusive review -> the gate HOLDs (this stage never approves)."""
    import story_semantics as sm
    from editorial_review import write_review
    with open(os.path.join(run.dir, "edl.json")) as f:
        edl = json.load(f)
    ed = run.prov.get("editorial") or {}
    story = ((ed.get("selected") or {}).get("headline")  # AUTO mode
             or ed.get("headline")                        # pinned mode
             or edl.get("topic"))
    llm = sm.LocalLLM().start()
    try:
        review = write_review(llm, edl, run.dir, story)
    finally:
        llm.stop()
    run.prov["editorial_review"] = {k: review.get(k) for k in ("reviewed_by", "review_type", "generated_at",
                                                               "prompt_sha256", "inconclusive",
                                                               "inconclusive_reason", "external_model_used")}
    print(f"  review by {review['reviewed_by']}: inconclusive={review.get('inconclusive')}")


def moments_screen(edl):
    """Ruling 34: (compiled screen or None, why) for a moments EDL. The miner's about-Bitcoin screen carried on the
    pin (moments_package.btc_screen = {"pattern", "source"}, copied by pinned.build_edl as moments_btc_screen), only
    for a moments package stand_alone_subject binds to the subject 'bitcoin'. Absent, malformed (not a str of at most
    500 characters) or not compiling: None, so every segment must name Bitcoin, as before (never looser)."""
    if "moments_package_sha256" not in edl or not stand_alone_subject(edl, {}):   # the story path: never a screen
        return None, "not a bound moments package"
    sc = edl.get("moments_btc_screen")
    if sc is None:
        return None, "the pin carries no btc_screen: every segment names Bitcoin"
    pat = sc.get("pattern") if isinstance(sc, dict) else None
    if not isinstance(pat, str) or not pat.strip() or len(pat) > 500:
        return None, f"btc_screen malformed ({type(sc).__name__}): every segment names Bitcoin"
    try:
        return re.compile(pat, re.I), f"the pin's btc_screen ({sc.get('source') or 'source not stated'})"
    except re.error as e:
        return None, f"btc_screen does not compile ({e}): every segment names Bitcoin"


def stand_alone_subject(edl, story):
    """The words every segment must use (stand_alone.subject_terms). A moments-first package (law L-q; pp-selectid
    REQUESTS R7 item 4, 'its subject for a Bitcoin package is Bitcoin'): its pin label, never its written title (the
    pinned angle is 'Pinned: <title>'; the title is a package line its own VO-fidelity gate checked), and only the label
    'bitcoin' itself. Anything else carrying the moments marker is an EMPTY subject, which fails closed
    (stand_alone.topical: no hook names it): another label (even one naming Bitcoin, e.g. 'bitcoin cash'), a marker
    that is not the 64-hex digest pinned.build_edl writes, a non-pinned EDL, or one without the package's two passed
    gate verdicts (moments_checks, copied by build_edl from the validated package). Every other run, unchanged: the
    selected story's object / event, else the EDL angle / topic."""
    import stand_alone
    if "moments_package_sha256" in edl:
        sha, checks = edl["moments_package_sha256"], edl.get("moments_checks")
        bound = (isinstance(sha, str) and bool(re.fullmatch(r"[0-9a-f]{64}", sha)) and edl.get("mode") == "pinned"
                 and isinstance(checks, dict) and checks.get("vo_fidelity_ok") is True
                 and checks.get("context_integrity_ok") is True)
        label = edl.get("topic")
        return stand_alone.subject_terms("", "bitcoin") \
            if bound and isinstance(label, str) and label.strip().lower() == "bitcoin" else set()
    return stand_alone.subject_terms(story.get("affected_object", ""),
                                     story.get("underlying_event") or edl.get("angle") or edl.get("topic", ""))


def stage_validate(run):
    from edl_rules import validate_edl
    from editorial_gate import run_gate
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

    # Shared AUTO/PIN editorial law gate. This is the last editorial acceptance
    # point before cutting. It always writes STORYBOARD.md + EDITORIAL_GATE.json
    # and fails closed when review judgments are absent or any law fails.
    gate = run_gate(run.dir, edl)
    run.prov["editorial_gate"] = gate
    for name, rec in gate.get("laws", {}).items():
        print(f"  {name}: [{'PASS' if rec.get('pass') else 'FAIL'}] " + "; ".join(rec.get("reasons") or []))
    if gate.get("verdict") != "READY_FOR_RENDER":
        failed = [name for name, rec in gate.get("laws", {}).items() if not rec.get("pass")]
        raise Hold("editorial law gate HOLD: " + ", ".join(failed))

    # Orchestrator 08:30 (direction 2): every segment stands alone and belongs to a Bitcoin story. The clip
    # scorer (the selection criterion) is asked only about clips that open on a conjunction / reply fragment.
    import stand_alone

    def rate(passages):
        import story_semantics as sm
        llm = sm.LocalLLM().start()
        try:
            ratings, err = sm.rate_passages(llm, {"underlying_event": edl.get("angle") or edl.get("topic", "")},
                                            passages)
        finally:
            llm.stop()
        if err:
            raise RuntimeError(f"clip scorer reply unparseable: {err}")
        return ratings
    story = {}
    if os.path.exists(os.path.join(run.dir, "passages.json")):           # auto: the selected story's query
        with open(os.path.join(run.dir, "passages.json")) as f:
            story = json.load(f).get("story") or {}
    subject = stand_alone_subject(edl, story)
    screen, screen_why = moments_screen(edl)                            # ruling 34: moments packages only
    sa = stand_alone.check_edl(edl, rate=rate, subject=subject, screen=screen)
    sa["screen_why"] = screen_why
    run.prov["stand_alone"] = sa
    for r in sa["rows"]:
        print(f"  STAND_ALONE {r['segment']}: [{'PASS' if r['pass'] else 'FAIL'}] opener: {r['opener']['why']} | "
              f"topic: {r['topic']['why']}")
    if "medley_names_bitcoin" in sa:
        print(f"  STAND_ALONE medley: [{'PASS' if sa['medley_names_bitcoin']['pass'] else 'FAIL'}] "
              f"{sa['medley_names_bitcoin']['why']} | screen: {screen_why}")
    if not sa["ok"]:
        raise Hold("stand-alone/topic: " + "; ".join(
            [f"{r['segment']}: " + " / ".join(x["why"] for x in (r["opener"], r["topic"]) if not x["pass"])
             for r in sa["rows"] if not r["pass"]]
            + ([f"medley: {sa['medley_names_bitcoin']['why']}"] if not sa.get("medley_names_bitcoin", {"pass": True})["pass"]
               else [])) + (f" (scorer: {sa['rate_error']})" if sa["rate_error"] else ""))

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
        if mode != "auto":                    # DEC-5: per-shot plan measured after prepare
            layout_errors.append((label, channel, f"expected auto, got {mode!r}"))
    run.prov["layout_compat"] = {"segments": [(l, s.get("channel")) for l, s in segs],
                                 "vertical_overrides": ov,
                                 "policy": "DEC-5: auto (per-shot plan after prepare)"}
    if layout_errors:
        raise Hold(f"layout compatibility: {layout_errors}")
    for l, s in segs:
        if s.get("video_id") in V2F_VIDEO_IDS and not run.allow_v2f_material:
            raise Hold(f"{l} reuses a v2f source video {s['video_id']}")
        if s.get("time_coords") != "source_file":
            raise Hold(f"{l} EDL times not in source-file coordinates")


# ── stage 6: cut + acceptance ──

def stage_cut(run):
    """Human PINs: the exact pinned table. Everything else: cuts placed inside the pauses that bound
    each LOCKED sentence (sentence_law.write_lock_cut_table) -- a cut never moves outside that
    silence and never adds or drops a word (2026-11-11: the +-2 s snap and the edge-word recompute of
    ad7295ea/4cf5a31a are gone). The SAME acceptance check runs on every cut; a rejection HOLDs."""
    from cut_accept import check_cut_acoustics
    use_pinned_table = not machine_placed_cuts(run)
    if use_pinned_table:
        from pinned import write_pinned_cut_table
        write_pinned_cut_table(run.dir)
    else:
        L.write_lock_cut_table(run.dir)
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
                for s in ("in", "out"):     # DEC-10 d: an edge the cutter placed at its envelope minimum is
                    if c.get(f"valley_{s}"):    # rejected only by (i)-(iii): G16 (next stage, HOLD) judges it by
                        d[s] = {"pass": None, "m19": d[s],      # neighbour_clear with the cut's own fades, not
                                "deferred_to": "G16 neighbour_clear (DEC-10 c-ii)"}   # cut_accept's M19 quota
                ok = all(c.get(f"valley_{s}") or bool(d[s].get("pass")) for s in ("in", "out"))
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
        raise Hold(f"cut acceptance rejected {fails} (see CUT_ACCEPTANCE.json)")
    return cuts


def stage_sentence_law(run):
    """G16 SENTENCE_BOUNDARY before anything is rendered: every cut holds exactly its locked
    sentence(s), both edges are legal sentence boundaries and the cuts sit inside those pauses."""
    ok, table = L.gate_g16(run.dir)
    run.prov["G16_pre_render"] = table
    jdump(os.path.join(run.dir, "SENTENCE_LAW.json"), {"pass": ok, "segments": table})
    for r in table:
        print(f"  {r['segment']}: {r.get('locked', '')} [{'PASS' if r['pass'] else 'FAIL'}] "
              + "; ".join(r["errors"]))
    if not ok:
        raise Hold("G16 sentence law: " + "; ".join(
            f"{r['segment']}: {', '.join(r['errors'])}" for r in table if not r["pass"]))


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
    # law L-a, before anything is rendered: the sign-off script names exactly the credited channels (the
    # card's list: the hook's channel first, then the clips'); G20 checks the rendered voice after render
    import credit_rings
    import gates as G
    with open(os.path.join(run.dir, "edl.json")) as f:
        credited = credit_rings.credit_channels(json.load(f))
    with open(os.path.join(PIPELINE_DIR, "channels.json")) as f:
        named = G.spoken_channels(manifest["signoff"].get("text", ""), json.load(f), credited)
    if named != set(credited):
        raise Hold(f"law L-a: the sign-off script names {sorted(named)}, the card credits {credited}")
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

def free_gpu0_for_whisper(run, stage, need_free_mib=6000):
    """GPU0 is shared (other sessions load Ollama models on :11434, e.g. a 22 GB qwen3-coder at 06:02 on
    Nov 11, which OOM'd the recut's prepare). Before a Whisper stage, unload the GPU0 Ollama models and
    wait for room, exactly as the editorial stage does (story_semantics.release_gpu0_for_whisper); a
    release that cannot be proven is an infrastructure HOLD, never an OOM mid-stage. L-r: through
    gpu0.swap_to (every other GPU0 model unloaded, a foreign process refused, the measured need proven free);
    a refusal is a Gpu0Stop that Run.stage turns into a HOLD carrying the real cause."""
    import story_semantics as sm
    try:
        ev = sm.release_gpu0_for_whisper(sm.LocalLLM(), need_free_mib=need_free_mib, wait_s=180)
    except RuntimeError as e:
        raise Hold(f"infrastructure: {stage}: {e}")
    run.prov.setdefault("gpu0_release", {})[stage] = ev


FADE_RETRY_MAX = 6   # further legal cut points tried per failing edge (machine-placed cuts only)


def machine_placed_cuts(run):
    """True when every cut of this run is placed by the sentence law (AUTO or a machine_cuts PIN); False for
    a human PIN's exact cut table. The ONE rule shared by stage_cut and the fade retry."""
    return not (run.mode == "pinned" and not run.machine_cuts)


def _retry_fade_edges(run, c, d1, prerender_clips, check_clip, fps, qp):
    """The clip contract failed ONLY on a fade edge of a MACHINE-placed cut (a click or breath at the cut
    point: Nov 11 recut clip_02, cut_out 37.87 on a tick): try the next legal points of the same locked pause
    for the failing edge(s) (sentence_law.cut_candidates: inside the range, cut_accept-clean, nearest the
    target first), re-preparing and re-checking with the real contract. Transactional: the cut is changed
    only if the re-prepared clip passes the WHOLE contract; otherwise the original cut and clip are restored.
    The contract and G16 are unchanged. Returns (ok, d1); every attempt is recorded on the cut."""
    errs = d1.get("errors") or []
    sides = {"out" if e.startswith("fade-out missing") else "in" if e.startswith("fade-in missing") else None
             for e in errs}
    if not errs or None in sides or not machine_placed_cuts(run):
        return False, d1
    with open(os.path.join(run.dir, "edl.json")) as f:
        edl = json.load(f)
    seg = edl["hook"] if c["clip_id"] == "hook" else \
        next((x for x in edl.get("clips", []) if f"clip_{x['index']:02d}" == c["clip_id"]), None)
    if not seg or not seg.get("selection_lock"):
        c.setdefault("contract_retries", []).append({"result": "no selection lock for this clip: not retried"})
        return False, d1
    lock = seg["selection_lock"]
    with open(os.path.join(run.dir, "transcripts", f"{c['video_id']}.json")) as f:
        words = json.load(f)["words"]
    src = os.path.join(run.dir, "sources", f"{c['video_id']}.mp4")
    cand = L.cut_candidates(src, L.edge_plan(L.SourceAudio(src), words, lock["i0"], lock["i1"]))
    from cut_accept import check_cut_acoustics
    pad = float(c.get("lead_in_pad_s") or 0)
    tried = c.setdefault("contract_retries", [])
    clip = os.path.join(run.dir, "qa", f"final_{c['clip_id']}.mp4")
    trial = dict(c)
    d = d1
    for side in sorted(sides):
        if not any(e.startswith(f"fade-{side}") for e in d.get("errors") or []):
            continue                                # the other edge's accepted trial cleared this one: keep it
        key = "cut_out" if side == "out" else "cut_in"
        fixed = False
        for x in [v for v in cand[side] if abs(v - c[key]) > 1e-6][:FADE_RETRY_MAX]:
            t2 = dict(trial, **{key: x})
            t2["cut_duration"] = round(t2["cut_out"] - t2["cut_in"], 3)
            if not check_cut_acoustics(src, t2["cut_in"], t2["cut_out"])[0]:
                tried.append({key: x, "result": "cut_accept rejected the pair"})
                continue
            prerender_clips(run.dir, [t2])
            if pad > 0:
                L.apply_lead_in_pad(run.dir, t2, fps, qp)
            ok, d = check_clip(clip, t2["cut_duration"] + pad)
            tried.append({key: x, "result": "PASS" if ok else d.get("errors")})
            print(f"  {c['clip_id']}: fade retry {key} {x}: {'PASS' if ok else d.get('errors')}")
            if not any(e.startswith(f"fade-{side}") for e in d.get("errors") or []):
                trial, fixed = t2, True
                break
        if not fixed:
            break
    if not (d.get("errors") or []) and (trial["cut_in"], trial["cut_out"]) != (c["cut_in"], c["cut_out"]):
        c.update(cut_in=trial["cut_in"], cut_out=trial["cut_out"], cut_duration=trial["cut_duration"])
        return True, d
    prerender_clips(run.dir, [c])                   # not fully clean: restore the original cut and clip
    if pad > 0:
        L.apply_lead_in_pad(run.dir, c, fps, qp)
    tried.append({"result": "no legal point clears the contract: original cut and clip restored"})
    return False, d1


BT601_MATRICES = ("smpte170m", "bt470bg")


def to_bt709(run_dir, video_ids):
    """Ruling 30 (orchestrator 2026-11-13 '01:55'): a source whose MATRIX is BT.601 (color_space smpte170m / bt470bg)
    is converted to BT.709 before any clip is prepared, so its frames read, and its final's tail measures, as a 709
    source's do (pin #1: Sjb6lUiL0m4 is smpte170m; its 9:16 and 16:9 finals came out untagged and G9 read 13.6 / 13.9
    through RGB while the luma plane was the 709 sources' own). The colorspace filter maps the matrix (and the
    primaries / transfer the source declares, else BT.601's own) to BT.709. It is a lossless x264 encode (qp 0) with
    every frame's timestamp passed through (-vsync 0), so the cuts' source times and the one lossy encode of prepare
    are unchanged. The audio is copied. Output tags: bt709 / bt709 / bt709 / tv. The original is kept as
    sources_bt601/<vid>.mp4. 709 and untagged sources are not touched. Returns {video_id: record}."""
    out = {}
    for vid in sorted(set(video_ids)):
        src = os.path.join(run_dir, "sources", f"{vid}.mp4")
        tags = media_tags(src)
        if tags.get("color_space") not in BT601_MATRICES:
            continue
        keep = os.path.join(run_dir, "sources_bt601", f"{vid}.mp4")
        ip = tags.get("color_primaries") if tags.get("color_primaries") not in (None, "", "unknown") else tags["color_space"]
        it = tags.get("color_transfer") if tags.get("color_transfer") not in (None, "", "unknown") else tags["color_space"]
        ir = "pc" if tags.get("color_range") == "pc" else "tv"     # a full-range source keeps its own range in
        vf = (f"colorspace=space=bt709:primaries=bt709:trc=bt709:range=tv:format=yuv420p:"   # (batch 54 C1, glm)
              f"ispace={tags['color_space']}:iprimaries={ip}:itrc={it}:irange={ir}")
        tmp = src + ".bt709.mp4"
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:v:0", "-map", "0:a?", "-vf", vf,
                            "-vsync", "0", "-c:v", "libx264", "-qp", "0", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-color_range", "tv", "-c:a", "copy", "-movflags", "+faststart", tmp],
                           capture_output=True, text=True, timeout=1800)
        if r.returncode != 0 or not os.path.exists(tmp):
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise Hold(f"ruling 30: the BT.601 -> BT.709 conversion of {vid} failed: {r.stderr.strip()[-200:]}")
        before = sha256(src)
        os.makedirs(os.path.dirname(keep), exist_ok=True)              # only once the encode has succeeded
        os.replace(src, keep)
        os.replace(tmp, src)
        out[vid] = {"from": {k: tags.get(k) for k in ("color_space", "color_primaries", "color_transfer", "color_range")},
                    "filter": vf, "original": os.path.relpath(keep, run_dir), "original_sha256": before,
                    "converted_sha256": sha256(src), "lossless": "libx264 qp 0, -vsync 0, audio copied"}
    return out


def media_tags(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=color_space,color_primaries,color_transfer,color_range", "-of", "json", path],
                       capture_output=True, text=True, timeout=60)
    try:
        return (json.loads(r.stdout).get("streams") or [{}])[0]
    except ValueError:
        return {}


def stage_prepare(run, cuts):
    from run_isolated import prerender_clips as _prerender_isolated

    def prerender_clips(run_dir, table):
        """L-r: run_isolated.py is a protected file (Law 22; test_fresh.TestProtected), so its NVENC encodes are
        swapped to here, at their one caller (the fade retry below receives this same function)."""
        gpu0.swap_to("nvenc")
        return _prerender_isolated(run_dir, table)
    from clip_contract import check_clip
    from cut_accept import check_edge_words
    from config import FPS, NVENC_QP_INTERMEDIATE
    run.prov["bt709_conversion"] = {**(run.prov.get("bt709_conversion") or {}),       # ruling 30, before any clip;
                                    **to_bt709(run.dir, [c["video_id"] for c in cuts])}  # a re-run keeps the record
    for vid, rec in run.prov["bt709_conversion"].items():
        print(f"  {vid}: BT.601 ({rec['from'].get('color_space')}) source converted to BT.709 (lossless)")
    prerender_clips(run.dir, cuts)
    pads = {}
    for c in cuts:
        if float(c.get("lead_in_pad_s") or 0) > 0:
            # D1: a file-head sentence without 80 ms of genuine lead-in gets the declared room-tone pad
            pads[c["clip_id"]] = L.apply_lead_in_pad(run.dir, c, FPS, NVENC_QP_INTERMEDIATE)
            print(f"  {c['clip_id']}: lead-in pad {pads[c['clip_id']]}")
    run.prov["lead_in_pads"] = pads
    qa = os.path.join(run.dir, "qa")
    work = os.path.join(qa, "edge_words")
    os.makedirs(work, exist_ok=True)
    free_gpu0_for_whisper(run, "prepare")          # the edge-word check loads Whisper on GPU0
    report, fails = [], []
    moved = False
    for c in cuts:
        clip = os.path.join(qa, f"final_{c['clip_id']}.mp4")
        ok1, d1 = check_clip(clip, c["cut_duration"] + float(c.get("lead_in_pad_s") or 0))
        if not ok1:
            before = (c["cut_in"], c["cut_out"])
            ok1, d1 = _retry_fade_edges(run, c, d1, prerender_clips, check_clip, FPS, NVENC_QP_INTERMEDIATE)
            moved |= (c["cut_in"], c["cut_out"]) != before
        # expected words come from the selection lock (cuts_final), never from the cut position
        ok2, d2 = check_edge_words(clip, c.get("first_word_expected", ""),
                                   c.get("last_word_expected", ""), work, c["clip_id"])
        snap = None
        if ok1 and ok2:                         # V1 (run 6): no frame of a neighbouring shot outside the speech
            import shot_snap
            snap = shot_snap.apply(clip, c, FPS, NVENC_QP_INTERMEDIATE)
            if snap["snapped"]:
                print(f"  {c['clip_id']}: shot snap: {snap['why']}")
        rec = {"clip_id": c["clip_id"], "sha256": sha256(clip), "contract": d1,
               "contract_pass": ok1, "edge_words": d2, "edge_words_pass": ok2, "shot_snap": snap}
        report.append(rec)
        if not (ok1 and ok2):
            fails.append(c["clip_id"])
        print(f"  {c['clip_id']}: contract {'PASS' if ok1 else 'FAIL'} {d1.get('errors')} | "
              f"edges first '{d2['heard_first']}'/'{d2['expected_first']}' "
              f"last '{d2['heard_last']}'/'{d2['expected_last']}' {'PASS' if ok2 else 'FAIL'}")
    run.prov["prepared_clips"] = report
    jdump(os.path.join(run.dir, "CLIP_CONTRACT.json"), report)
    if moved:                                   # the final G16 and every later stage read the moved cut
        jdump(os.path.join(run.dir, "cuts_final.json"), cuts)
    if fails:
        raise Hold(f"clip-preparation contract / edge-word check failed for {fails}")


# ── transitions (Phase 3, DEC-4) ──

TRANSITION_STYLE = "crossfade"   # DEC-4 production default: 6-frame dissolve + audio crossfade


def write_transitions(run, style):
    """TRANSITIONS.json for both renderers: style, each clip's measured genuine lead-in / tail (the
    only time a transition may overlap) and channel (transitions only between different channels)."""
    with open(os.path.join(run.dir, "cuts_final.json")) as f:
        cuts = json.load(f)
    with open(os.path.join(run.dir, "edl.json")) as f:
        edl = json.load(f)
    segs = {"hook": edl["hook"], **{f"clip_{c['index']:02d}": c for c in edl.get("clips", [])}}
    lead_tail = {}
    for c in cuts:
        ht = L.head_tail(L.SourceAudio(os.path.join(run.dir, "qa", f"final_{c['clip_id']}.mp4")))
        lead_tail[c["clip_id"]] = [ht["lead_ms"] / 1000.0, ht["tail_ms"] / 1000.0]
    rec = {"style": style, "lead_tail": lead_tail,
           "channels": {cid: seg.get("channel") for cid, seg in segs.items()}}
    jdump(os.path.join(run.dir, "TRANSITIONS.json"), rec)
    run.prov["transitions"] = rec


# ── stage 8b: vertical layout (DEC-2 / DEC-5) ──

def stage_layout(run, cuts):
    """Measure every prepared clip per shot (vertical_layout.classify: SCRFD faces, fixed rules) and
    record the plan: vertical_overrides.json (renderer input), VERTICAL_LAYOUT.json (all samples) and
    edl.json segment 'vertical_layout' (shot classes, flagged safe frames) for gates and the caption."""
    import vertical_layout as V
    qa = os.path.join(run.dir, "qa")
    with open(os.path.join(run.dir, "vertical_overrides.json")) as f:
        ov = json.load(f)
    with open(os.path.join(run.dir, "edl.json")) as f:
        edl = json.load(f)
    segs = {"hook": edl["hook"], **{f"clip_{c['index']:02d}": c for c in edl.get("clips", [])}}
    plans = {}
    for c in cuts:
        cid = c["clip_id"]
        plan = V.classify(os.path.join(qa, f"final_{cid}.mp4"))
        plans[cid] = plan
        ov[cid] = {"layout": "auto", "plan": {k: v for k, v in plan.items() if k != "samples"}}
        segs[cid]["vertical_layout"] = {"shots": [{k: sh[k] for k in ("start", "end", "class", "flagged")}
                                                  for sh in plan["shots"]], "flagged": plan["flagged"]}
        print(f"  {cid}: " + " | ".join(f"{sh['class']} {sh['start']:.2f}-{sh['end']:.2f}"
                                        + (" (SAFE FRAME, flagged)" if sh["flagged"] else "")
                                        for sh in plan["shots"]))
    jdump(os.path.join(run.dir, "vertical_overrides.json"), ov)
    jdump(os.path.join(run.dir, "VERTICAL_LAYOUT.json"), plans)
    jdump(os.path.join(run.dir, "edl.json"), edl)
    run.prov["vertical_layout"] = {cid: [(sh["class"], sh["start"], sh["end"]) for sh in p["shots"]]
                                   for cid, p in plans.items()}


# ── stage 9: render ──

FALLBACK_RE = re.compile(r"reframe failed for (\S+), using original")


def stage_render(run):
    from shoutout import build_shoutout
    from render16 import render_16x9
    from render_vertical import render_9x16
    from run_isolated import preflight_check, postflight_check
    from config import resolve_paths

    paths = resolve_paths(run.dir)
    write_transitions(run, TRANSITION_STYLE)
    build_shoutout(run.dir, None, "16x9")
    build_shoutout(run.dir, None, "9x16")
    preflight_check(run.dir)

    limiter = -3.5 if run.machine_cuts else -3.0
    with Capture() as cap16:
        render_16x9(run.dir, None, "segment.mp4", alimiter_dbfs=limiter)
    final16 = os.path.join(paths["out_dir"], "segment.mp4")
    man16 = os.path.join(paths["qa_dir"], "concat_manifest_16x9.json")
    with open(man16) as f:
        tot16 = max(s.get("end", 0) for s in json.load(f)["segments"])
    postflight_check(final16, tot16, "16x9")

    with Capture() as cap9:
        render_9x16(run.dir, None, "segment_vertical.mp4", alimiter_dbfs=limiter)
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
    # ruling 29 (orchestrator '01:55'): the final mix measured and corrected to target BEFORE the gates (two-pass
    # loudnorm on the 16:9, its exact audio muxed into the 9:16, both re-measured); G5 unchanged
    import loudness
    run.prov["loudness"] = loudness.correct_finals(final16, final9)
    print(f"  loudness: {run.prov['loudness'].get('action')}")

    # Vertical silent-fallback detection (PBX item 6): log evidence + structural evidence
    with open(paths["cuts_json"]) as f:
        cuts = json.load(f)
    fb = {"log_hits": FALLBACK_RE.findall(log9), "structural": [], "checked": []}
    for c in cuts:
        vp = os.path.join(paths["qa_dir"], f"vert_{c['clip_id']}.mp4")
        if not os.path.exists(vp):
            fb["structural"].append(f"{c['clip_id']}: vert file missing")
            continue
        m = media_summary(vp)
        if (m["width"], m["height"]) != (1080, 1920):
            fb["structural"].append(f"{c['clip_id']}: vert file {m['width']}x{m['height']}")
        fb["checked"].append(c["clip_id"])          # counted only once its file was probed (cycle 2 F1)
    fb["outro_conform_fallback_16x9"] = "PBX outro conform failed" in cap16.text()
    fb["outro_conform_fallback_9x16"] = "PBX outro conform failed" in log9 or \
        "outro conform failed" in log9.lower()
    fb["fallback_occurred"] = bool(fb["log_hits"] or fb["structural"])
    run.prov["vertical_fallback_check"] = fb

    # G4 input (DEC-2/DEC-5): each talking-head entry carries its clip-level layout. A clip whose shots are
    # all one class gets that class's rule; a clip mixing classes gets G4's 'screenshare' rule at clip
    # level, and the per-shot G4 in stage_gates applies the face rule of EVERY shot (the binding check);
    # G4s checks every label against the picture.
    with open(os.path.join(run.dir, "VERTICAL_LAYOUT.json")) as f:
        plans = json.load(f)
    for man in (man16, man9):
        with open(man) as f:
            m = json.load(f)
        for sg in m["segments"]:
            plan = plans.get(sg["label"]) if sg.get("type") == "talking_head" else None
            if plan:
                classes = {sh["class"] for sh in plan["shots"]}
                cls = classes.pop() if len(classes) == 1 else "mixed"
                sg["layout"] = {"single": "single", "stack2": "2face", "stack3": "3face"}.get(cls, "screenshare")
                sg["source_faces"] = int(cls[-1]) if cls.startswith("stack") else 1
        jdump(man, m)
    return final16, man16, final9, man9


# ── stage 10: gates ──

def _status(ok):
    return "PASS" if ok else "FAIL"


def _samples(x):
    """How many things a gate measured (release_auth requires >= 1 for every REQUIRED row: red-team A, 'the gates
    ran'): a list = its entries; a dict = its MEASUREMENTS only (numbers, non-empty lists / objects), never its
    labels, hashes or flags (claude-fable audit batch 16 #2: a six-key report literal is not six samples); a
    skipped or empty result measured nothing."""
    def measured(v):
        return (type(v) in (int, float)) or (isinstance(v, (list, dict)) and bool(v)) or \
            (isinstance(v, str) and bool(v.strip()))
    if isinstance(x, list):                          # entries that carry something (never None / empty)
        return sum(1 for v in x if measured(v))
    if not isinstance(x, dict) or x.get("skip"):
        return 0
    return sum(1 for v in x.values() if (type(v) in (int, float)) or (isinstance(v, (list, dict)) and v))


def tail_rows(g9_pass, conform_fallback, identical=True):
    """G9_tail is the DEC-1 calibrated gate alone (no exception path). outro_locked: the luma floor is
    the approved reference's LOCKED outro tail, so a conform fallback (some other outro) fails closed
    on its own row even when its tail clears the floor (Heimdall DEC-1 audit: keep the two apart), and so
    does an outro whose master or conformed file is not hash-identical to the locked one (GPT-cut F09)."""
    return {"G9_tail": _status(g9_pass), "outro_locked": _status(identical and not conform_fallback)}


def stage_gates(run, final16, man16, final9, man9):
    free_gpu0_for_whisper(run, "gates")            # G17b / G18 load Whisper on GPU0
    # Keep the source-relative sharpness threshold local to this stage so QA does not
    # depend on module-global lookup state during long production runs. Threshold unchanged.
    g8_degradation_ratio = 0.85
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
    # the bytes every gate below measures (release_auth: the attested files must be these files)
    measured = {os.path.relpath(p, run.dir): sha256(p) for p in (final16, final9, man16, man9)}

    # Production gate runner — invoked exactly as in the v2f run.
    # G8 needs its sources (2026-11-11: it was never given any, so it always failed "no_source" and was
    # waived): 16:9 = the prepared clips (source camera, 1920x1080), 9:16 = the reframed vertical clips.
    src16 = {c["clip_id"]: os.path.join(qa, f"final_{c['clip_id']}.mp4") for c in cuts}
    src9 = {c["clip_id"]: os.path.join(qa, f"vert_{c['clip_id']}.mp4") for c in cuts}
    ok16, r16 = run_gates(run.dir, final16, man16, source_clips=src16, prepared_clips=src16)   # ruling 21: G3c on
    ok9, r9 = run_gates(run.dir, final9, man9, source_clips=src9, prepared_clips=src9)         # the prepared clips
    import qa_gates  # patched by run_gates (BASE/VO_DIR) — same module instance

    rows = {"16x9": {}, "9x16": {}}
    flags = {"16x9": [], "9x16": []}
    limits = {"16x9": [], "9x16": []}
    notes = {"16x9": {}, "9x16": {}}          # why a row reads what it reads (rows hold exact verdicts only)
    evidence = {"16x9": {}, "9x16": {}}       # that the gate ran, and on how many samples

    def put(fmt, row, verdict, data, note=None):
        """One gate row: an exact verdict (release_auth.VERDICTS, no prefixes, no waiver text), what it measured,
        and the reason in notes."""
        rows[fmt][row] = verdict
        evidence[fmt][row] = {"executed": verdict != "SKIPPED", "samples": _samples(data)}
        if note:
            notes[fmt][row] = note
        elif row in notes[fmt]:
            del notes[fmt][row]

    for fmt, res in (("16x9", r16), ("9x16", r9)):
        for k, v in res.items():
            if isinstance(v, dict) and "pass" in v and k not in ("G8_sharpness", "G9_tail",
                                                                   "G11_parity"):
                # a skipped gate is never reported as a PASS (fail-closed)
                if v.get("skip"):
                    put(fmt, k, "SKIPPED", None, v.get("reason", "skip"))
                else:
                    put(fmt, k, _status(v["pass"] is True), v.get("table", v.get("data")))
        # G11 inside run_gates has no horizontal final (it skips); the real G11 is the 9x16 row below

    # G11 for real (vertical vs horizontal)
    g11_ok, g11 = qa_gates.gate_g11(final9, final16, segs9, segs16)
    put("9x16", "G11_parity", _status(g11_ok), g11)

    # G14 / G14c / G15
    speech = G.g14_run_speech(run.dir, cuts)         # ruling 13: G14 samples the LOCKED words minus measured pauses
    src_clips = {c["clip_id"]: {"path": os.path.join(run.dir, "sources", f"{c['video_id']}.mp4"),
                                "cut_in": c["cut_in"], "words": speech[c["clip_id"]]} for c in cuts}
    g14dir16 = os.path.join(qa, "g14_16x9")
    g14dir9 = os.path.join(qa, "g14_9x16")
    os.makedirs(g14dir16, exist_ok=True)
    os.makedirs(g14dir9, exist_ok=True)
    # a declared lead-in pad is room tone, not source material: G14 measures from the pad's end
    pads = {c["clip_id"]: float(c.get("lead_in_pad_s") or 0) for c in cuts}

    def _g14_manifest(man, tag):
        with open(man) as f:
            m = json.load(f)
        for sg in m["segments"]:
            if sg.get("type") == "talking_head" and pads.get(sg["label"]):
                sg["start"] = round(sg["start"] + pads[sg["label"]], 3)
        path = os.path.join(qa, f"g14_manifest_{tag}.json")
        jdump(path, m)
        return path
    man16_g14, man9_g14 = _g14_manifest(man16, "16x9"), _g14_manifest(man9, "9x16")
    g14_16_ok, g14_16 = G.gate_g14(final16, man16_g14, source_clips=src_clips, qa_dir=g14dir16)
    fails16 = [d for d in g14_16 if d.get("status") == "FAIL"]
    put("16x9", "G14_av_alignment", "PASS" if g14_16_ok else "FAIL" if fails16 else "HOLD", g14_16,
        None if g14_16_ok or fails16 else "inconclusive")
    limits["16x9"].append("G14: static talking-head temporal slips can pass frame_sim "
                          "(v2e 18.0-24.0 s precedent); VO sections are auto-PASS (pre-roll "
                          "declared), plate correctness not verified")
    # 9:16: the audio-offset part only (frame similarity of a 9:16 crop against the 16:9 source is not valid);
    # the gate's own per-segment verdict (DEC-12e): >= 3 conclusive matching samples, zero mismatches
    g14_9_ok, g14_9 = G.gate_g14(final9, man9_g14, source_clips=src_clips, qa_dir=g14dir9, frames=False)
    fails9 = [d for d in g14_9 if d.get("status") == "FAIL"]
    put("9x16", "G14_audio_offset", "PASS" if g14_9_ok else "FAIL" if fails9 else "HOLD", g14_9,
        None if g14_9_ok or fails9 else "inconclusive")
    put("9x16", "G14_frame_similarity", "LIMITED", None, "not valid for 9:16 crop vs 16:9 source")
    limits["9x16"].append("G14 frame_sim compares a 9:16 crop with the 16:9 source (v2e positive "
                          "control: 0.24-0.54 on correct frames); only the audio-offset part is "
                          "scored; VO sections auto-PASS")
    g14c_ok, g14c = G.gate_g14c(final16, final9, tolerance_ms=42)
    put("9x16", "G14c_duration_parity", _status(g14c_ok), g14c)
    for sub in ("g15_16x9", "g15_9x16"):
        os.makedirs(os.path.join(qa, sub), exist_ok=True)
    import credit_rings                             # DEC-11: G15 also checks each disc is the credited avatar
    with open(os.path.join(run.dir, "edl.json")) as f:
        credited = credit_rings.credit_channels(json.load(f))
    g15_16_ok, g15_16 = G.gate_g15(final16, segs16, os.path.join(qa, "g15_16x9"), channels=credited)
    g15_9_ok, g15_9 = G.gate_g15(final9, segs9, os.path.join(qa, "g15_9x16"), channels=credited)
    put("16x9", "G15_credits", _status(g15_16_ok), g15_16)
    put("9x16", "G15_credits", _status(g15_9_ok), g15_9)
    # G20 SIGNOFF_NAMES_ALL (law L-a): the rendered sign-off names exactly the credited channels
    for sub in ("g20_16x9", "g20_9x16"):
        os.makedirs(os.path.join(qa, sub), exist_ok=True)
    g20_16_ok, g20_16 = G.gate_g20(final16, segs16, credited, os.path.join(qa, "g20_16x9"))
    g20_9_ok, g20_9 = G.gate_g20(final9, segs9, credited, os.path.join(qa, "g20_9x16"))
    put("16x9", "G20_signoff_names_all", _status(g20_16_ok), g20_16)
    put("9x16", "G20_signoff_names_all", _status(g20_9_ok), g20_9)

    # G8 — production result + source-relative report (threshold untouched)
    g8dir = os.path.join(qa, "g8_relative")
    os.makedirs(g8dir, exist_ok=True)
    rel_src = {c["clip_id"]: os.path.join(qa, f"final_{c['clip_id']}.mp4") for c in cuts}
    _, g8rel = qa_gates.gate_g8(final16, segs16, g8dir, source_clips=rel_src)
    ratios = {r["segment"]: r["ratio"] for r in g8rel}
    degraded = {k: v for k, v in ratios.items() if v < g8_degradation_ratio}
    g8_report = {"production_result_16x9": r16["G8_sharpness"]["pass"],
                 "production_result_9x16": r9["G8_sharpness"]["pass"],
                 "relative_reference": "prepared 1920x1080 clip (source camera, scaled) at the "
                                       "same relative offset",
                 "relative_16x9": g8rel, "degraded_below_0.85": degraded}
    for fmt, res in (("16x9", r16), ("9x16", r9)):
        # DEC-1 floor + DEC-3 soft-source rule live in the gate itself; no waiver (DEC-8)
        put(fmt, "G8_sharpness", _status(res["G8_sharpness"]["pass"] is True), res["G8_sharpness"].get("table"))

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
        for row, verdict in tail_rows(res["G9_tail"]["pass"] is True, fallback, identical).items():
            put(fmt, row, verdict, d if row == "G9_tail" else      # outro: the two hashes that were computed
                [h for h in (msha, csha) if isinstance(h, str) and len(h) == 64])

    # G4 per shot + G4s layout truth (DEC-2 / DEC-5)
    import vertical_layout as V
    with open(os.path.join(run.dir, "VERTICAL_LAYOUT.json")) as f:
        plans = json.load(f)
    prepared = {cid: os.path.join(qa, f"final_{cid}.mp4") for cid in plans}
    g4_shots, g4s = {}, {}
    for fmt, final, man, sgs in (("16x9", final16, man16, segs16), ("9x16", final9, man9, segs9)):
        g4dir = os.path.join(qa, f"g4_shots_{fmt}")
        os.makedirs(g4dir, exist_ok=True)
        with open(man) as f:
            shout = json.load(f).get("shoutout_start", 0)
        ok, g4_shots[fmt] = qa_gates.gate_g4(final, V.per_shot_manifest(sgs, plans), fmt, shout, g4dir)
        put(fmt, "G4_faces_per_shot", _status(ok), g4_shots[fmt])
        ok, g4s[fmt] = V.gate_g4s(plans, prepared, vert_final=final9 if fmt == "9x16" else None,
                                  vert_segments=segs9 if fmt == "9x16" else None)
        put(fmt, "G4s_layout_truth", _status(ok), g4s[fmt])

    # G16 SENTENCE_BOUNDARY: re-run on the final cut state (format-independent; same row in both)
    g16_ok, g16 = L.gate_g16(run.dir)
    for fmt in ("16x9", "9x16"):
        put(fmt, "G16_sentence_boundary", _status(g16_ok), g16)

    # G17 ONSET/TAIL: prepared clips (>= 80 ms genuine lead-in/tail) + each final (edge words >= 85 %)
    g17a_ok, g17a = L.gate_g17_prepared({c["clip_id"]: os.path.join(qa, f"final_{c['clip_id']}.mp4")
                                          for c in cuts})
    g17b16_ok, g17b16 = L.gate_g17_output(final16, segs16, cuts, run.dir)
    g17b9_ok, g17b9 = L.gate_g17_output(final9, segs9, cuts, run.dir)
    # G17c (law L-b): the first and last word of every prepared clip, with their decay, at full level
    # (within 1 dB of the unfaded source); format-independent, part of the G17 row in both formats
    g17c_ok, g17c = L.gate_g17_edges(run.dir)
    for fmt, b_ok, b in (("16x9", g17b16_ok, g17b16), ("9x16", g17b9_ok, g17b9)):
        put(fmt, "G17_onset_tail", _status(g17a_ok and b_ok and g17c_ok), None)
        evidence[fmt]["G17_onset_tail"]["samples"] = min(_samples(g17a), _samples(b), _samples(g17c))

    # law L-c: a check that disagrees with the others on an EDGE WORD is right until an acoustic comparison
    # with the source proves otherwise: G17c (the kept word and decay equal the unfaded source) and G16 (no
    # audible part of the neighbour word, neighbour_clear). A dissenting G3b reading needs that proof, else
    # HOLD; a G3c head / tail failure on an edge is overruled only by it, else it stands.
    # Amended (orchestrator addendum 2026-11-11 '22:00', GPT-cut F03): the G17c comparison that proves an edge
    # is measured on the FINAL of that format (the bytes being approved, sentence_law.edges_on_final), never on
    # the prepared clip; when it cannot prove the edge, the dissent / the failure stands and the run HOLDS.
    lc = {}
    for fmt, res, final, sgs in (("16x9", r16, final16, segs16), ("9x16", r9, final9, segs9)):
        g3b = (res.get("G3b_cut_out_clean") or {}).get("table") or []
        dissent = [e["segment"] for e in g3b if isinstance(e, dict) and e.get("dissent") and e.get("last_found")]
        g3c = (res.get("G3c_acoustic_tail") or {}).get("table") or []
        failed = [(e["segment"], side) for e in g3c if isinstance(e, dict)
                  for side, key in (("out", "tail_ok"), ("in", "head_ok")) if e.get(key) is False]
        proof = L.edges_on_final(final, sgs, run.dir) if (dissent or failed) else {}

        def _edge_proved(seg, side, proof=proof):
            return g16_ok and ((proof.get(seg) or {}).get(side) or {}).get("ok") is True
        unproved = [sg for sg in dissent if not _edge_proved(sg, "out")]
        if rows[fmt].get("G3b_cut_out_clean") == "PASS" and unproved:
            put(fmt, "G3b_cut_out_clean", "HOLD", g3b, f"dissent unproved on the final: {', '.join(unproved)}")
        explained = all(isinstance(e, dict) and (e.get("pass") is True or any(e.get(k) is False for k in ("tail_ok", "head_ok")))
                        for e in g3c) and bool(g3c)    # every failing entry fails ONLY by edge flags (cycle 2 F5)
        if rows[fmt].get("G3c_acoustic_tail") == "FAIL" and failed and explained and \
                all(_edge_proved(sg, sd) for sg, sd in failed):
            put(fmt, "G3c_acoustic_tail", "PASS", g3c, "L-c: " + ", ".join(f"{sg} {sd}" for sg, sd in failed) +
                " proved by the comparison of the final's audio with the source")
        lc[fmt] = {"g3b_dissent": dissent, "g3b_unproved": unproved, "g3c_failed_edges": failed,
                   "final_proof": proof}

    # G18 WORD-FOR-WORD (mission 4a): every clip's first/last words are its locked sentences' and its
    # words are exactly those of the source span it was cut from (both finals; whisper on GPU0)
    import word_diff as WD
    with open(os.path.join(run.dir, "edl.json")) as f:
        edl_now = json.load(f)
    locks = {"hook": edl_now["hook"].get("selection_lock"),
             **{f"clip_{c['index']:02d}": c.get("selection_lock") for c in edl_now.get("clips", [])}}
    g18_clips = {c["clip_id"]: {"lock_text": (locks.get(c["clip_id"]) or {}).get("text", ""),
                                "source": os.path.join(run.dir, "sources", f"{c['video_id']}.mp4"),
                                "cut_in": c["cut_in"], "cut_out": c["cut_out"],
                                "pad_s": float(c.get("lead_in_pad_s") or 0.0),
                                "adjudicated": bool((locks.get(c["clip_id"]) or {}).get("adjudication")),
                                "alternatives": (locks.get(c["clip_id"]) or {}).get("alternatives"),
                                "prepared": os.path.join(qa, f"final_{c['clip_id']}.mp4"),   # the PREPARED clip
                                "fade_in_s": float(c.get("fade_in_ms") or 0) / 1000,          # ruling 22: the
                                "fade_out_s": float(c.get("fade_out_ms") or 0) / 1000}        # interior between fades
                 # (qa/final_<clip>.mp4, the file G17c measures; the finals are out/segment*.mp4)
                 for c in cuts}
    run.prov["lock_adjudication"] = {cid: (locks.get(cid) or {}).get("adjudication") for cid in g18_clips
                                     if (locks.get(cid) or {}).get("adjudication")}         # ruling 17
    run.prov["lock_alternatives"] = {cid: (locks.get(cid) or {}).get("alternatives") for cid in g18_clips
                                     if (locks.get(cid) or {}).get("alternatives")}        # ruling 18
    missing = [cid for cid, c in g18_clips.items() if not c["lock_text"]]
    tr = WD.Transcriber()
    g18 = {}
    for fmt, final, sgs in (("16x9", final16, segs16), ("9x16", final9, segs9)):
        ok, g18[fmt] = WD.gate_g18(final, sgs, g18_clips, transcriber=tr)
        put(fmt, "G18_word_for_word", _status(ok and not missing), g18[fmt],
            f"no selection lock: {missing}" if missing else None)
    del tr
    if missing:
        g18["missing_selection_lock"] = missing

    # G19 EDGE SHOTS (recut run 6 V1): no hard shot change inside a talking head outside its speech, on the
    # finished video (the guard behind prepare's shot_snap); speech times are prepare's own record
    import edge_shots
    from config import FPS
    with open(os.path.join(run.dir, "CLIP_CONTRACT.json")) as f:
        snap_rec = {r["clip_id"]: (r.get("shot_snap") or {}) for r in json.load(f)}
    g19 = {}
    for fmt, final, sgs in (("16x9", final16, segs16), ("9x16", final9, segs9)):
        ok, g19[fmt] = edge_shots.gate_g19(final, sgs, snap_rec, FPS)
        put(fmt, "G19_edge_shots", _status(ok), g19[fmt])

    fb = run.prov["vertical_fallback_check"]
    put("9x16", "vertical_silent_fallback", _status(fb["fallback_occurred"] is False),
        fb.get("checked") or [],                     # the vertical clips checked (render log + dimensions)
        "fallback occurred" if fb["fallback_occurred"] else "no fallback")

    import release_auth
    gates_out = {"inventory_version": release_auth.INVENTORY_VERSION, "rows": rows, "notes": notes,
                 "evidence": evidence, "measured_files": measured, "flags": flags, "limitations": limits,
                 "G11": g11, "G14_16x9": g14_16, "G14_9x16": g14_9, "G14c": g14c,
                 "G15_16x9": g15_16, "G15_9x16": g15_9, "G20_16x9": g20_16, "G20_9x16": g20_9, "G17c": g17c, "L-c": lc, "G8": g8_report, "G9": g9_report, "G16": g16,
                 "G17": {"prepared": g17a, "16x9": g17b16, "9x16": g17b9}, "G18": g18, "G19": g19,
                 "G4_per_shot": g4_shots, "G4s": g4s,
                 "run_gates_overall": {"16x9": ok16, "9x16": ok9}}
    jdump(os.path.join(run.dir, "GATE_REPORT.json"), gates_out)
    run.prov["gates"] = {"rows": rows, "notes": notes, "flags": flags, "limitations": limits}
    return rows, flags, limits


def verdict_for(rows, fmt, evidence):
    """(verdict, {row: why}) by release_auth's exact inventory for that format: a missing, unknown, skipped,
    inconclusive or unexecuted row is a blocker (red-team A; no prefix rules). evidence is required (None or a
    malformed mapping = no evidence); release_auth.NO_EVIDENCE_CHECK asks the rows-only question."""
    import release_auth
    bad = release_auth.blockers(fmt, rows, evidence)
    return (VERDICT_HOLD if bad else VERDICT_CANDIDATE), bad


# ── provenance helpers ──

def launch_code(repo=None):
    """The launch half of the attestation (ruling 27): tracked files under EXEC_PATHS unmodified and no untracked
    pipeline/*.py (segment_v1 holds historical untracked scratch; every executed module is verified tracked and
    unmodified at the end of the run from sys.modules), else a Hold. Returns {"git_head", "exec_trees",
    "pipeline_tree_clean_at_launch": True}."""
    repo = repo or REPO
    porcelain = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "--", *EXEC_PATHS],
                               cwd=repo, capture_output=True, text=True).stdout.strip()
    untracked_py = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "--", "pipeline/*.py"],
                                  cwd=repo, capture_output=True, text=True).stdout.strip()
    if porcelain or untracked_py:
        raise Hold(f"executable paths {list(EXEC_PATHS)} not clean at launch:\n{porcelain}\n{untracked_py}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    return {"git_head": head, "pipeline_tree_clean_at_launch": True, "exec_trees": exec_trees(head, repo)}


def exec_trees(rev, repo=None):
    """Ruling 27: {path: git object id of EXEC_PATHS[path] at `rev`}. A path git cannot resolve there (missing, or git
    failing) is recorded as 'UNREADABLE: <git's message>', never as an id: executed_code refuses it (fail closed)."""
    out = {}
    for p in EXEC_PATHS:
        r = subprocess.run(["git", "rev-parse", "--verify", f"{rev}:{p}"], cwd=repo or REPO,
                           capture_output=True, text=True)
        oid = r.stdout.strip()
        out[p] = oid if r.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", oid) else \
            f"UNREADABLE: {(r.stderr.strip() or oid or 'no output')[:200]}"
    return out


def executed_code(launch, modules=None, repo=None):
    """({rel path: sha256} of every loaded module of this checkout, [why not at the launch revision]). A module whose
    NAME is a pipeline module (any *.py of pipeline/, segment_v1/, video_pipeline_v3/) but whose file is outside
    this checkout, a module under another protocol_pulse / worktrees checkout, an executable tree (EXEC_PATHS) changed
    since launch or a file under them differing from the launch revision (ruling 27: HEAD moving for a docs commit is
    not a reason), and a module untracked or modified against the launch revision are all reasons."""
    repo = repo or REPO
    modules = sys.modules if modules is None else modules
    first_party = {os.path.splitext(fn)[0] for d in ("pipeline", "segment_v1", "video_pipeline_v3")
                   if os.path.isdir(os.path.join(repo, d)) for fn in os.listdir(os.path.join(repo, d)) if fn.endswith(".py")}
    mods, why = {}, []
    for name, m in list(modules.items()):
        f = getattr(m, "__file__", None)
        if not f or not os.path.exists(f):
            continue
        f = os.path.realpath(f)
        if f.startswith(repo + os.sep) and "/venv/" not in f:
            mods[os.path.relpath(f, repo)] = sha256(f)
        elif name in first_party:                 # a pipeline module (imported top-level) from anywhere else, even
            why.append(f"{name} from {f} (outside this checkout {repo})")   # under site-packages / venv (cycle-2 #7)
        elif re.search(r"/(protocol_pulse|worktrees)/", f) and \
                not any(x in f for x in ("site-packages", "dist-packages", "/venv/")):
            why.append(f"{name} from {f} (outside this checkout {repo})")
    if launch != "HEAD":                          # ruling 27: the executable trees, not HEAD (a docs commit is fine)
        t0, t1 = exec_trees(launch, repo), exec_trees("HEAD", repo)
        bad = [f"{p} at {rev}: {t[p]}" for rev, t in (("launch", t0), ("end", t1)) for p in EXEC_PATHS
               if t[p].startswith("UNREADABLE")]
        if bad:
            why.append("executable tree not readable: " + "; ".join(bad))
        moved = [f"{p} {t0[p]} -> {t1[p]}" for p in EXEC_PATHS if t0[p] != t1[p] and not t1[p].startswith("UNREADABLE")]
        if moved:
            why.append("executable tree changed during the run: " + "; ".join(moved))
        diff = subprocess.run(["git", "diff", "--name-only", launch, "--", *EXEC_PATHS], cwd=repo,
                              capture_output=True, text=True)
        if diff.returncode != 0:                                  # could not compare: never a pass
            why.append(f"git diff against the launch revision failed: {diff.stderr.strip()[:200]}")
        elif diff.stdout.strip():                                 # working tree vs the launch commit, uncommitted too
            why.append(f"executable paths differ from the launch revision: {diff.stdout.split()}")
    for rel in sorted(mods):
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=repo,
                                 capture_output=True).returncode == 0
        modified = subprocess.run(["git", "diff", "--quiet", launch, "--", rel], cwd=repo,
                                  capture_output=True).returncode != 0
        if not tracked or modified:
            why.append(f"{rel} ({'untracked' if not tracked else 'modified vs the launch revision'})")
    return dict(sorted(mods.items())), why


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
    # executed code hashes: every loaded module of THIS checkout, compared with the LAUNCH revision (not
    # whatever HEAD is now: GPT-cut F24); a pipeline module loaded from anywhere else is code that did not come
    # from this run's revision (Claude-gates C4; by module NAME, not path spelling: GPT audit batch 16 #8)
    launch = (run.prov.get("code") or {}).get("git_head")
    mods, not_clean = executed_code(launch or "HEAD")
    run.prov.setdefault("code", {}).update(               # ruling 27: the evidence, both ends (HEAD is informational)
        git_head_at_end=subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                                       text=True).stdout.strip(), exec_trees_at_end=exec_trees("HEAD"))
    if not launch:                                   # no recorded launch revision: nothing to compare with (F6)
        not_clean.append("no launch revision recorded")
    run.prov["executed_code_sha256"] = mods
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
    g0 = p.get("gpu0") or {}
    total = ((g0.get("at_start") or {}).get("memory_mib") or [None, None])[1]
    if "left" in g0:
        L += ["", f"- GPU0 at the run's end (law L-r leave): {g0['left']}"]
    L += ["", f"## Peak memory per stage and GPU (law L-r: every GPU has one owner at a time; nvidia-smi memory.used "
              f"sampled every 1 s, a lower bound; GPU0 total {total} MiB; the run owns GPU0, GPU1 belongs to others)",
          "| stage | GPU0 peak MiB | GPU1 peak MiB | out-of-memory attempts | retry |", "|---|---|---|---|---|"]
    for r in s["stages"]:
        oom = (p.get("gpu0_oom") or {}).get(r["name"], [])
        fails = [e for e in oom if e.get("error")]
        retry = "-" if not fails else ("passed" if any(e.get("outcome") == "passed" for e in oom) else "held")
        L.append(f"| {r['name']} | {r.get('gpu0_peak_mib', 'not sampled')} | {r.get('gpu1_peak_mib', 'not sampled')} | "
                 f"{len(fails)} | {retry} |")
    vc = p.get("visual_checklist") or {}
    if vc:
        L += ["", "## Visual checklist (answered FROM the contact sheets qa/contact_sheet_<fmt>.jpg; any no = HOLD)"]
        for fmt, v in vc.items():
            L.append(f"- {fmt}: {'PASS' if v.get('ok') else 'FAIL'}" + (f" ({v['error']})" if v.get("error") else ""))
            for model, rows in (v.get("answers") or {}).items():
                for k, r in (rows or {}).items():
                    r = r if isinstance(r, dict) else {"answer": repr(r)}
                    L.append(f"  - {model} | {k}: **{r.get('answer')}** {str(r.get('why', ''))[:160]}")
    L += ["", "Publishing: NONE (telegram never imported). External audit legs (GPT-4o/Gemini via "
          "cross_llm_audit.py): UNAVAILABLE for this run (OpenAI credits exhausted; Gemini removed)."]
    with open(os.path.join(run.dir, "REPORT.md"), "w") as f:
        f.write("\n".join(L) + "\n")


# ── release attestation ──

def attest_run(run, deliverable=True, why_not=None, code_checked=True):
    """ATTESTATION.json (release_auth.attest), written last: holds anywhere => HOLD (GPT-cut F10), and the run is
    ok only when it ended a candidate with no hold, its tree was clean at launch and every executed module is at
    the launch revision (GPT-cut F24, Claude-gates C4). A replay (code_checked=False) has no provenance pass of its
    own: it is attested for its verdict and is never deliverable."""
    import release_auth
    if run.status.get("holds"):
        run.status["verdict"] = VERDICT_HOLD
    code = run.prov.get("code") or {}
    why = list(run.status.get("holds") or [])
    if run.status.get("verdict") != VERDICT_CANDIDATE:
        why.append(f"verdict {run.status.get('verdict')}")
    if code_checked and code.get("pipeline_tree_clean_at_launch") is not True:
        why.append("tree not recorded clean at launch")
    if code_checked and run.prov.get("executed_code_not_at_revision") != []:
        why.append(f"executed code not at the launch revision: {run.prov.get('executed_code_not_at_revision')}")
    state = {"ok": not why, "why": why, "verdict": run.status.get("verdict"), "mode": run.mode,
             "git_head": code.get("git_head"), "ended": run.status.get("ended")}
    att = release_auth.attest(run.dir, state, deliverable=deliverable, why_not=why_not)
    run.status["attestation"] = {"verdict": att["verdict"], "deliverable": att["deliverable"]}
    if att["verdict"] != "ALL_PASS" and run.status.get("verdict") == VERDICT_CANDIDATE:
        run.status["verdict"] = VERDICT_HOLD          # the attestation is the release truth; never two answers
        run.status["holds"].append("attestation: " + "; ".join(
            [f"{fmt} {k}: {v}" for fmt, b in att["blockers"].items() for k, v in b.items()]
            + att["verification"]["why"] + att["other_blockers"] + [f"missing {m}" for m in att["missing_files"]]))
    return att


# ── main ──

TAIL_STAGES = ("prepare", "layout", "render", "gates")


def run_tail(run, cuts, start="prepare", vision=True):
    """prepare -> layout -> render -> gates -> verify -> verdict, from `start`. main runs all of it;
    replay.py re-runs a COPY of an existing run from any of these stages with the same functions, so a fix
    is checked by the production code without a download, a transcription or the editorial stages."""
    k = TAIL_STAGES.index(start)
    if k <= 0:
        run.stage("prepare", lambda: stage_prepare(run, cuts))
    if k <= 1:
        run.stage("layout", lambda: stage_layout(run, cuts))
    if k <= 2:
        final16, man16, final9, man9 = run.stage("render", lambda: stage_render(run))
    else:
        final16, final9 = (os.path.join(run.dir, "out", n) for n in ("segment.mp4", "segment_vertical.mp4"))
        man16, man9 = (os.path.join(run.dir, "qa", f"concat_manifest_{f}.json") for f in ("16x9", "9x16"))
    rows, flags, limits = run.stage("gates", lambda: stage_gates(run, final16, man16, final9, man9))
    # mission 4a / DEC-8: the automated verification pack (words, joins, credits) for the drop
    import verify_pack
    pack = run.stage("verify", lambda: verify_pack.build(run.dir, vision=vision))
    # the verdict is computed from the report ON DISK (the file the attestation binds); the pack wrote the V1 rows
    # into it, and a pack that wrote none (or no evidence) leaves V1 missing = a blocker (GPT-cut F02)
    with open(os.path.join(run.dir, "GATE_REPORT.json")) as f:
        rep = json.load(f)
    rows, evidence = rep.get("rows") or {}, rep.get("evidence") or {}
    run.prov["visual_checklist"] = {fmt: {"ok": v.get("ok"), "error": v.get("error"),
                                          "answers": {m: (d or {}).get("rows") for m, d in (v.get("per_model") or {}).items()}}
                                    for fmt, v in (pack.get("visual") or {}).items()}
    run.prov["contact_sheets"] = pack.get("contact_sheets")
    v16, bad16 = verdict_for(rows.get("16x9"), "16x9", evidence)
    v9, bad9 = verdict_for(rows.get("9x16"), "9x16", evidence)
    run.prov["verdicts"] = {"16x9": v16, "9x16": v9}
    run.prov["verdict_blockers"] = {"16x9": bad16, "9x16": bad9}
    run.status["verdict"] = VERDICT_CANDIDATE if v16 == v9 == VERDICT_CANDIDATE else VERDICT_HOLD
    if run.status["verdict"] == VERDICT_HOLD:
        run.status["holds"] += [f"gates {k}: {v}" for k, v in {**bad16, **bad9}.items()]


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
    if pin_path:
        with open(pin_path) as f:
            pin_data = json.load(f)
        run.machine_cuts = pin_data.get("machine_cuts", False)
    run.status["mode"] = run.mode
    run.status["release_state"] = RELEASE_STATE
    run.save()
    t0 = time.time()
    run.sampler = gpu0.PeakSampler().start()        # L-r item 5: every stage sampled, env included
    try:
        run.stage("env", lambda: stage_env(run))
        if run.mode == "pinned":
            run.stage("pinned", lambda: stage_pinned(run, pin_path))
        else:
            keyword = run.stage("editorial", lambda: stage_editorial(run))
            run.stage("select", lambda: stage_select(run, keyword))
        run.stage("review", lambda: stage_review(run))
        run.stage("validate", lambda: stage_validate(run))
        cuts = run.stage("cut", lambda: stage_cut(run))
        run.stage("sentence_law", lambda: stage_sentence_law(run))
        run.stage("voice", lambda: stage_voice(run))
        run_tail(run, cuts)
    except Hold:
        run.status["verdict"] = VERDICT_HOLD
    except gpu0.Gpu0Stop as e:  # L-r: a GPU0 stop outside any stage is a HOLD carrying its real cause
        run.status["verdict"] = VERDICT_HOLD
        run.status["holds"].append(f"orchestrator: infrastructure: GPU0 {type(e).__name__}: {e}")
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
        if run.sampler:                        # L-r item 5: peak GPU0 memory per stage, in PROVENANCE and REPORT.md
            run.prov.setdefault("gpu0", {})["peaks_mib"] = run.sampler.stop()
            run.prov["gpu0"]["sampler_errors"] = run.sampler.errors
        run.prov.setdefault("gpu0", {})["swaps"] = gpu0.events()
        try:                                   # L-r: unload this run's models now, so the report records the outcome
            run.prov["gpu0"]["left"] = gpu0.leave() if gpu0.held() else "no lease held"
        except gpu0.Gpu0Stop as e:             # the next owner would find a model of this run: said, not hidden
            run.prov["gpu0"]["left"] = f"FAILED: {type(e).__name__}: {e}"
            run.status["gpu0_leave_failed"] = run.prov["gpu0"]["left"]
        try:                                   # LAST: the terminal state, any hold included (release_auth)
            attest_run(run)
        except Exception as e:
            run.status["verdict"] = VERDICT_HOLD
            run.status["holds"].append(f"attestation: {type(e).__name__}: {e}")
        run.save()
        write_report(run)
        with open(os.path.join(run_dir, "VERDICT.txt"), "w") as f:
            f.write(run.status["verdict"] + "\n")
        print(f"\n=== VERDICT: {run.status['verdict']} | RELEASE STATE: {RELEASE_STATE} ===")
        for h in run.status["holds"]:
            print(f"  HOLD: {h}")
        print(f"  report: {os.path.join(run_dir, 'REPORT.md')}  (no publishing)")
        if run.status.get("gpu0_leave_failed"):
            print(f"  GPU0 leave: {run.status['gpu0_leave_failed']}", flush=True)
        run.gpu0_stack.close()                 # the GPU0 lease (law L-r) is held to here
    sys.exit(0 if run.status["verdict"] == VERDICT_CANDIDATE else 3)


if __name__ == "__main__":
    main()
