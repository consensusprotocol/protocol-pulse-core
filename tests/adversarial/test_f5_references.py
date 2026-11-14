"""FAMILY 5 - reference integrity (CPU only; READ-ONLY on /home/ultron/protocol_pulse/references by absolute path).

The frozen reference references/v2f_2026-11-06 (PBX-approved v2f) and the protected preview
references/pulse_preview_2026-11-11 (law L-d):
  hashes     every file SHA256SUMS lists has its digest, nothing unlisted, the directories are read-only; the
             worktree's tracked copy of the preview is the same bytes
  manifests  each concat manifest describes its final: ordered, starts at 0, ends at the final's duration, its
             talking heads are the EDL's segments in order, shout-out then outro last, 16:9 and 9:16 one timeline
  L-a        the sign-off's spoken channels, the credits card and the clips used are one set: v2f must pass; the
             preview is the documented must-fail (DataDash, the hook's channel, is not said)
  L-b        no recorded fade overlaps an edge word: measured with sentence_law.edge_word_bounds on the sources
             and pinned (tests/fixtures/adversarial/reference_lb_edges.json); the documented must-fail (the
             preview's Natalie Brunell tail) must be flagged
  G8 9:16    the open claim 'the reference fails 9:16 G8', settled on the saved files through the public gate
             with the production wiring (qa/vert_<clip> sources) and the harness wiring (no sources)
  L-j        the preview's recorded (legacy) gate report is not releasable under the current contract
A missing reference is a FAILURE here (nothing measured is never a pass), not a skip.
"""
import functools
import hashlib
import json
import os
import stat
import subprocess

import pytest

import adv_helpers as H

ROOT = H.MAIN_TREE_REFS
PREVIEW = os.path.join(ROOT, "pulse_preview_2026-11-11")
V2F_ROOT = os.path.join(ROOT, "v2f_2026-11-06")
V2F = os.path.join(V2F_ROOT, "run")
RUNS = {"pulse_preview_2026-11-11": PREVIEW, "v2f_2026-11-06": V2F}
FRAME = 1 / 24


def _need(path):
    H.control(os.path.exists(path), f"reference missing on this machine: {path} (a missing reference is a FAIL, law "
                                    f"L-m; set PP_REFS_DIR to the directory holding the references)")
    return path


@pytest.fixture(autouse=True, scope="module")
def _references_present():
    """One clear, early answer when the reference root is absent: every test of this family ERRORS with it (the
    other families still run and measure; a session exit would stop them too)."""
    for p in (ROOT, PREVIEW, V2F_ROOT, V2F):
        _need(p)


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def _sums(root):
    out = {}
    for line in open(_need(os.path.join(root, "SHA256SUMS"))):
        if line.strip():
            d, p = line.rstrip("\n").split(None, 1)
            out[os.path.normpath(p.strip().lstrip("*"))] = d
    return out


def _duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True, timeout=60)
    return float(r.stdout.strip())


def _registry():
    return json.load(open(os.path.join(H.REPO, "pipeline", "channels.json")))


# ─────────────────────────────── hashes ───────────────────────────────

@pytest.mark.parametrize("root", [PREVIEW, V2F_ROOT], ids=["preview", "v2f"])
def test_every_listed_file_has_its_recorded_sha256_and_nothing_is_unlisted(root):
    sums = _sums(root)
    assert sums
    bad = [p for p, d in sums.items() if not os.path.isfile(os.path.join(root, p)) or _sha(os.path.join(root, p)) != d]
    assert not bad, bad
    on_disk = {os.path.normpath(os.path.relpath(os.path.join(dp, f), root))
               for dp, _, fs in os.walk(root) for f in fs} - {"SHA256SUMS"}
    assert on_disk - set(sums) == set(), sorted(on_disk - set(sums))[:10]


@pytest.mark.parametrize("root", [PREVIEW, V2F_ROOT], ids=["preview", "v2f"])
def test_the_protected_reference_is_read_only(root):
    for dp, dirs, fs in os.walk(_need(root)):
        for p in [dp] + [os.path.join(dp, f) for f in fs]:
            assert not os.stat(p).st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH), p


def test_the_worktree_copy_of_the_preview_is_the_same_bytes():
    sums = _sums(PREVIEW)
    wt = os.path.join(H.REPO, "references", "pulse_preview_2026-11-11")
    if not os.path.isdir(wt):
        pytest.fail("the worktree carries no references/pulse_preview_2026-11-11 (it is tracked in git)")
    assert open(os.path.join(wt, "SHA256SUMS"), "rb").read() == open(os.path.join(PREVIEW, "SHA256SUMS"), "rb").read()
    tracked = [os.path.normpath(os.path.relpath(os.path.join(dp, f), wt)) for dp, _, fs in os.walk(wt) for f in fs]
    tracked = [p for p in tracked if p != "SHA256SUMS"]
    assert tracked
    bad = [p for p in tracked if sums.get(p) != _sha(os.path.join(wt, p))]
    assert not bad, bad


# ─────────────────────────────── manifests ───────────────────────────────

def _edl_labels(edl):
    return ["hook"] + [f"clip_{c['index']:02d}" for c in edl.get("clips", [])]


@pytest.mark.parametrize("name", list(RUNS))
@pytest.mark.parametrize("fmt", ["16x9", "9x16"])
def test_each_manifest_describes_its_final(name, fmt):
    run = RUNS[name]
    segs = json.load(open(_need(os.path.join(run, "qa", f"concat_manifest_{fmt}.json"))))["segments"]
    edl = json.load(open(os.path.join(run, "edl.json")))
    final = os.path.join(run, "out", "segment.mp4" if fmt == "16x9" else "segment_vertical.mp4")
    starts = [s["start"] for s in segs]
    assert starts == sorted(starts) and segs[0]["start"] == 0.0
    for a, b in zip(segs, segs[1:]):                      # contiguous, or a dissolve (< 0.5 s of overlap)
        assert -1e-3 <= a["end"] - b["start"] < 0.5, (a, b)
    assert [s["label"] for s in segs if s.get("type") == "talking_head"] == _edl_labels(edl)
    assert [s.get("type") for s in segs[-2:]] == ["shoutout", "outro"]
    assert abs(segs[-1]["end"] - _duration(final)) <= FRAME + 1e-3, (segs[-1]["end"], _duration(final))


@pytest.mark.parametrize("name", list(RUNS))
def test_the_two_formats_share_one_timeline(name):
    run = RUNS[name]
    a, b = (json.load(open(os.path.join(run, "qa", f"concat_manifest_{f}.json")))["segments"] for f in ("16x9", "9x16"))
    assert [(s["label"], s.get("type"), s["start"], s["end"]) for s in a] == \
        [(s["label"], s.get("type"), s["start"], s["end"]) for s in b]


# ─────────────────────────────── L-a: sign-off == card == clips ───────────────────────────────

def _la_sets(run):
    import credit_rings
    import gates as G
    edl = json.load(open(os.path.join(run, "edl.json")))
    card = credit_rings.credit_channels(edl)
    clips = {edl["hook"]["channel"]} | {c["channel"] for c in edl["clips"]}
    text = json.load(open(os.path.join(run, "vo_audio", "VO_MANIFEST.json")))["signoff"]["text"]
    return set(G.spoken_channels(text, _registry(), card)), card, clips, text


def test_l_a_v2f_signoff_card_and_clips_are_one_set():
    spoken, card, clips, text = _la_sets(V2F)
    assert len(card) == len(set(card)) == 3
    assert spoken == set(card) == clips, (text, spoken, card, clips)


def test_l_a_the_preview_is_the_documented_must_fail():
    """The card (measured on the rendered card: G15's registered-avatar discs) and the clips name four channels;
    the sign-off says three: DataDash (the hook's channel) is missing (E-FAIL-031)."""
    spoken, card, clips, text = _la_sets(PREVIEW)
    measured_card = {a["channel"] for a in json.load(open(os.path.join(PREVIEW, "GATE_REPORT.json")))["G15_16x9"]["avatars"]
                     if a.get("r", 0) >= 0.90}
    assert set(card) == clips == measured_card == {"DataDash", "Natalie Brunell", "Yahoo Finance", "Bitcoin Magazine"}
    assert spoken == set(card) - {"DataDash"}, (text, spoken)


# ─────────────────────────────── L-b: no fade overlaps an edge word ───────────────────────────────

@functools.lru_cache(maxsize=None)
def _lb_measure(name):
    """Measured once per run per session (read-only; the callers never mutate it)."""
    import sentence_law as L
    run = RUNS[name]
    cuts = json.load(open(_need(os.path.join(run, "cuts_final.json"))))
    cuts = cuts if isinstance(cuts, list) else cuts["cuts"]
    rows = {}
    for c in cuts:
        sa = H.WindowAudio(os.path.join(run, "sources", f"{c['video_id']}.mp4"), c["cut_in"] - 3, c["cut_out"] + 3)
        wb = L.edge_word_bounds(sa, None, c["cut_in"], c["cut_out"])
        fi, fo = c.get("fade_in_ms", 20) / 1000, c.get("fade_out_ms", 30) / 1000
        rows[c["clip_id"]] = {"cut_in": c["cut_in"], "cut_out": c["cut_out"], "fade_in_ms": c.get("fade_in_ms", 20),
                              "fade_out_ms": c.get("fade_out_ms", 30), "first_word_onset": round(wb["onset"], 3),
                              "last_word_end": round(wb["end"], 3),
                              "in_overlap_ms": int(round((c["cut_in"] + fi - wb["onset"]) * 1000)),
                              "out_overlap_ms": int(round((wb["end"] - (c["cut_out"] - fo)) * 1000))}
    return rows


LB = H.load_fixture("reference_lb_edges.json")


def _ffmpeg_version():
    return subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=30).stdout.splitlines()[0]


@pytest.mark.parametrize("name", list(RUNS))
def test_l_b_recorded_fades_against_edge_words_are_the_measured_table(name):
    got = _lb_measure(name)
    assert got == LB["measured"][name], (
        f"measured now with {_ffmpeg_version()!r}; pinned with {LB['ffmpeg_version']!r}"
        + (" -- the DECODER changed: re-measure the table (tests/fixtures/adversarial/reference_lb_edges.json)"
           if _ffmpeg_version() != LB["ffmpeg_version"] else " -- same decoder: the reference or edge_word_bounds changed"),
        got)


def test_l_b_the_documented_must_fail_is_an_overlap():
    """Each documented must-fail edge MEASURED now on the reference (integrator merge audit: the first version compared
    the pinned fixture with itself)."""
    H.control(LB["documented_must_fail"], "the fixture names the documented must-fail edges")
    for name, clip, side in LB["documented_must_fail"]:
        m = _lb_measure(name)[clip]
        assert m[f"{side}_overlap_ms"] > 0, (name, clip, side, m)
    m = _lb_measure("pulse_preview_2026-11-11")["clip_01"]
    assert m["out_overlap_ms"] > 50 and m["fade_out_ms"] == 83, m          # '...Monday rally.' (E-FAIL-032)


def test_window_audio_reads_the_edges_the_whole_file_decode_reads():
    """adv_helpers.WindowAudio (decodes only around a cut) gives sentence_law.edge_word_bounds the same first-word
    onset and last-word end as sentence_law.SourceAudio (the whole-file decode production uses), on every reference
    edge whose source is at most 1,300 s (integrator merge audit: the claim was enforced by no test). Measured
    2026-11-12: 7 of the 8 edges; v2f clip_03's source is 3,863 s long, too long to decode whole in this suite."""
    import sentence_law as L
    compared = []
    for name, run in RUNS.items():
        cuts = json.load(open(os.path.join(run, "cuts_final.json")))
        for c in cuts if isinstance(cuts, list) else cuts["cuts"]:
            src = os.path.join(run, "sources", f"{c['video_id']}.mp4")
            if _duration(src) > 1300:
                continue
            wa = H.WindowAudio(src, c["cut_in"] - 3, c["cut_out"] + 3)
            a = L.edge_word_bounds(wa, None, c["cut_in"], c["cut_out"])
            b = L.edge_word_bounds(_whole(src), None, c["cut_in"], c["cut_out"])
            assert (round(a["onset"], 3), round(a["end"], 3)) == (round(b["onset"], 3), round(b["end"], 3)), \
                (name, c["clip_id"], a, b)
            compared.append((name, c["clip_id"]))
    H.control(len(compared) >= 7, f"edges compared: {compared}")


@functools.lru_cache(maxsize=4)
def _whole(path):
    import sentence_law as L
    return L.SourceAudio(path)


# ─────────────────────────────── G8 9:16: settle the open claim ───────────────────────────────

def _g8(tmp_path, wiring, label="clip_03"):
    """The public gate on the saved 9:16 final, one segment. (The final has one keyframe, so each frame grab near
    clip_03 decodes ~1,000-1,270 frames; the full four-segment table is measured once and kept in
    pp-tests_REQUESTS.md.)"""
    import qa_gates as Q
    segs = json.load(open(os.path.join(V2F, "qa", "concat_manifest_9x16.json")))["segments"]
    seg = next(s for s in segs if s["label"] == label)
    src = {label: os.path.join(V2F, "qa", f"vert_{label}.mp4")} if wiring == "production" else None
    ok, table = Q.gate_g8(os.path.join(V2F, "out", "segment_vertical.mp4"), [seg], str(tmp_path),
                          source_clips=src, fmt="9x16")
    return ok, table[0], Q.G8_SHARPNESS_FLOOR["9x16"]


def test_g8_9x16_v2f_passes_through_the_production_wiring_at_its_floor(tmp_path):
    """Claude-gates #5: measured on the saved finals, run_fresh.stage_gates' wiring (9:16 sources = the
    reframed vertical clips): PASS, clip_03 out median exactly the calibrated floor (zero margin, A5)."""
    ok, row, floor = _g8(tmp_path, "production")
    assert ok is True, row
    assert len(row["out_variances"]) == 5 and len(row["src_variances"]) == 5, row
    assert abs(row["out_median"] - floor) < 0.005 and row["ratio"] >= 0.85, (row, _ffmpeg_version(), LB["ffmpeg_version"])


def test_g8_9x16_v2f_fails_without_sources_the_harness_reading(tmp_path):
    """E-FAIL-042: called without its source clips (the Law 22 harness), G8 cannot measure degradation and
    FAILS (fail closed) - the recorded 'v2f fails 9:16 G8' is this reading, not the production verdict. Measured on
    the hook (near the file's only keyframe; every segment reads no_source the same way: REQUESTS.md table)."""
    ok, row, floor = _g8(tmp_path, "no_sources", label="hook")
    assert ok is False and row["degradation_reason"] == "no_source" and row["src_median"] == 0.0, row
    assert row["out_median"] >= floor, row                  # the picture itself clears the floor


# ─────────────────────────────── L-j on the preview's recorded report ───────────────────────────────

def test_the_preview_recorded_gate_report_is_not_releasable():
    """The preview's GATE_REPORT predates law L-j: 'HOLD(inconclusive)', a '(run_gates)' placeholder row, FAIL
    rows and no execution evidence. The current contract must refuse it (it was reviewed, never released)."""
    import release_auth as RA
    rep = json.load(open(os.path.join(PREVIEW, "GATE_REPORT.json")))
    for fmt in RA.FORMATS:
        bad = RA.blockers(fmt, rep["rows"].get(fmt), rep.get("evidence"))
        assert bad, fmt
    bad16 = RA.blockers("16x9", rep["rows"]["16x9"], RA.NO_EVIDENCE_CHECK)
    assert "G11_parity(run_gates)" in bad16 and "G14_av_alignment" in bad16, bad16
