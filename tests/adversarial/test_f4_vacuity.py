"""FAMILY 4 - vacuity (law L-m: nothing measured is never a pass; law L-l: a model reply counts only whole).

1. Every gate of the REQUIRED inventory (release_auth.INVENTORY) is called through its public function with
   vacuous input: empty segments / plans / manifests, zero samples, None, NaN. Expected: FAIL, or an explicit
   skip that the production mapping records as SKIPPED (run_fresh.stage_gates: a result with skip=True is never
   a PASS) - never a plain PASS. A gate that PASSES on nothing is a strict xfail tied to its finding.
2. Defence in depth: whatever a gate returns on nothing, the production evidence rule (run_fresh._samples; the
   stage itself needs GPU0) counts zero samples and release_auth.blockers blocks the row.
3. A model reply that is empty / prose / truncated / not JSON / JSON of the wrong shape / NaN, through the V1
   vision panel (visual_check.ask_panel -> verify_pack.panel_ok, HTTP seam faked) and every editorial decision
   that reads a model (adjudicate, verify_support via adjudicate, rate_passages, derive_story_query,
   label_cluster, sentence_on_event, adjacent_admissible; LocalLLM.chat_json with only _post faked): never a
   pass, a count, a rating or an admission.
"""
import json
import math
import os
import traceback
import warnings

import numpy as np
import pytest

import adv_helpers as H

NAN = float("nan")


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    d = tmp_path_factory.mktemp("f4_media")
    x, _, _ = H.speech_like(["Bitcoin closed the week below its average.", "That is a level traders watch."],
                            lead_s=0.3, tail_s=0.5, seed=4)
    final = H.make_media(str(d / "final.mp4"), x)
    silent = H.make_video(str(d / "silent.mp4"), 64, 36, 2.0)
    return {"final": final, "silent": silent, "dir": str(d)}


@pytest.fixture
def qa(tmp_path, monkeypatch):
    import qa_gates as Q
    monkeypatch.setattr(Q, "whisper_segment", lambda *a, **k: "")          # ASR hears nothing (no Whisper)
    return str(tmp_path)


def TH(s=0.0, e=2.0, label="hook", **kw):
    return {"label": label, "type": "talking_head", "start": s, "end": e, **kw}


SHOUT = {"label": "shoutout", "type": "shoutout", "start": 2.0, "end": 3.0}


def production_reading(result):
    """What run_fresh.stage_gates writes for a gate result: an explicit skip is SKIPPED, else PASS iff ok is True."""
    ok, data = result if isinstance(result, tuple) else (result, None)
    if isinstance(data, dict) and data.get("skip"):
        return "SKIPPED"
    return "PASS" if ok is True else "FAIL"


def _manifest(tmp, segs, name="m.json"):
    p = os.path.join(tmp, name)
    with open(p, "w") as f:
        json.dump({"segments": segs}, f)
    return p


class _Silent:
    def span(self, *a, **k):                              # any arity: a changed call is not read as a gate crash
        return ""


def _g16_run(tmp, edl, cuts):
    os.makedirs(os.path.join(tmp, "run"), exist_ok=True)
    rd = os.path.join(tmp, "run")
    for name, obj in (("edl.json", edl), ("cuts_final.json", cuts)):
        with open(os.path.join(rd, name), "w") as f:
            json.dump(obj, f)
    return rd


def _xf(finding, req):
    return pytest.mark.xfail(strict=True, raises=AssertionError, reason=f"{finding}: PASS on nothing measured; REQUESTS.md {req}")


F05 = _xf("GPT-gates F05 / Claude-gates V4-V5 / Grok-gates 13 (OPEN)", "R-13")
F23 = _xf("GPT-cut F23 (OPEN)", "R-14")
PP03 = _xf("PP-03 (new: pipeline gates not named by F05 / F23)", "R-15")


def _cases():
    import qa_gates as Q
    import gates as G
    import sentence_law as L
    import word_diff as WD
    import edge_shots as ES
    import vertical_layout as V
    import run_fresh as RF
    no_face = lambda *a, **k: []                                    # noqa: E731  (no SCRFD, no GPU)
    return [
        # G3b_cut_out_clean
        ("G3b empty segments", lambda m, t: Q.gate_g3b(m["final"], [], t), F05),
        ("G3b talking head with no expected last word", lambda m, t: Q.gate_g3b(m["final"], [TH()], t), F05),
        ("G3b reading empty", lambda m, t: Q.gate_g3b(m["final"], [TH(last_word="week")], t), None),
        ("G3b NaN segment", lambda m, t: Q.gate_g3b(m["final"], [TH(NAN, NAN, last_word="week")], t), None),
        # G3c_acoustic_tail
        ("G3c empty segments", lambda m, t: Q.gate_g3c(m["final"], [], t, "16x9"), F05),
        ("G3c NaN segment", lambda m, t: Q.gate_g3c(m["final"], [TH(NAN, NAN)], t, "16x9"), None),
        ("G3c no audio", lambda m, t: Q.gate_g3c(m["silent"], [TH()], t, "9x16"), None),
        # G4s_layout_truth
        ("G4s empty plans", lambda m, t: V.gate_g4s({}, {}, detect=no_face), PP03),
        ("G4s a clip with no shots", lambda m, t: V.gate_g4s({"hook": {"shots": []}}, {"hook": m["final"]},
                                                             detect=no_face), PP03),
        ("G4s NaN shot", lambda m, t: V.gate_g4s({"hook": {"shots": [{"start": NAN, "end": NAN, "class": "single"}]}},
                                                {"hook": m["final"]}, detect=no_face), None),
        # G5_tech
        ("G5 no audio, wrong frame", lambda m, t: Q.gate_g5(m["silent"], "16x9"), None),
        # G8_sharpness
        ("G8 empty segments", lambda m, t: Q.gate_g8(m["final"], [], t), F05),
        ("G8 no source clips", lambda m, t: Q.gate_g8(m["final"], [TH()], t), None),
        ("G8 NaN segment", lambda m, t: Q.gate_g8(m["final"], [TH(NAN, NAN)], t, source_clips={"hook": m["final"]}),
         None),
        # G9_tail / outro_locked
        ("G9 no audio", lambda m, t: Q.gate_g9(m["silent"], t, "16x9"), None),
        ("outro_locked identity unknown", lambda m, t: (RF.tail_rows(True, False, None)["outro_locked"] == "PASS",
                                                        None), None),
        # G12_credits / G15_credits
        ("G12 no shoutout", lambda m, t: Q.gate_g12(m["final"], [], 0, t), None),
        ("G12 zero expected rings", lambda m, t: Q.gate_g12(m["final"], [TH(), SHOUT], 0, t), None),
        ("G12 expected None", lambda m, t: Q.gate_g12(m["final"], [SHOUT], None, t), None),
        ("G15 no shoutout", lambda m, t: G.gate_g15(m["final"], [], t, channels=[]), None),
        ("G15 no credited channels", lambda m, t: G.gate_g15(m["final"], [SHOUT], t, channels=[]), None),
        ("G15 channels None", lambda m, t: G.gate_g15(m["final"], [SHOUT], t, channels=None), None),
        # G16_sentence_boundary
        ("G16 hook without lock or cut", lambda m, t: L.gate_g16(_g16_run(t, {"hook": {"video_id": "v"}}, [])), None),
        # G17_onset_tail
        ("G17a no prepared clips", lambda m, t: L.gate_g17_prepared({}), F23),
        ("G17c hook without lock or cut", lambda m, t: L.gate_g17_edges(_g16_run(t, {"hook": {"video_id": "v"}}, [])),
         None),
        # G18_word_for_word
        ("G18 empty segments and clips", lambda m, t: WD.gate_g18(m["final"], [], {}, transcriber=_Silent()), F23),
        ("G18 empty lock text, nothing heard", lambda m, t: WD.gate_g18(
            m["final"], [TH()], {"hook": {"lock_text": "", "source": m["final"], "cut_in": 0, "cut_out": 2}},
            transcriber=_Silent()), F23),
        ("G18 nothing heard", lambda m, t: WD.gate_g18(
            m["final"], [TH()], {"hook": {"lock_text": "Bitcoin closed the week below its average.",
                                          "source": m["final"], "cut_in": 0, "cut_out": 2}},
            transcriber=_Silent()), None),
        ("G18 talking head without a lock", lambda m, t: WD.gate_g18(m["final"], [TH()], {}, transcriber=_Silent()),
         None),
        # G19_edge_shots
        ("G19 empty segments", lambda m, t: ES.gate_g19(m["final"], [], {}, 24), PP03),
        ("G19 talking head without a speech record", lambda m, t: ES.gate_g19(m["final"], [TH()], {}, 24), None),
        # G20_signoff_names_all
        ("G20 empty", lambda m, t: G.gate_g20(m["final"], [], [], t), None),
        ("G20 nothing heard", lambda m, t: G.gate_g20(m["final"], [TH(), SHOUT], ["DataDash"], t), None),
        # G14_av_alignment (16:9) / G14_audio_offset (9:16)
        ("G14 16x9 empty manifest", lambda m, t: G.gate_g14(m["final"], _manifest(t, []), source_clips={}, qa_dir=t),
         PP03),
        ("G14 9x16 empty manifest", lambda m, t: G.gate_g14(m["final"], _manifest(t, []), source_clips={}, qa_dir=t,
                                                           frames=False), PP03),
        ("G14 talking head without a source", lambda m, t: G.gate_g14(m["final"], _manifest(t, [TH()]),
                                                                     source_clips={}, qa_dir=t), None),
        ("G14 NaN segment", lambda m, t: G.gate_g14(m["final"], _manifest(t, [TH(NAN, NAN)]),
                                                   source_clips={"hook": {"path": m["final"], "cut_in": 0}},
                                                   qa_dir=t), None),
    ]


CASES = _cases()


RAISED = object()


def call_gate(call, media, qa):
    """The probe's one exception rule: an exception raised INSIDE the gate fails the stage (a HOLD: RAISED, never a
    PASS) and is reported as a warning (never silent); one raised by this test's own code (a wrong signature, a broken
    stub) is a probe bug, and a resource failure (MemoryError, RecursionError) is not a gate's decision: both
    propagate (final audit round U-1)."""
    try:
        return call(media, qa)
    except (MemoryError, RecursionError):
        raise
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        if not tb or os.path.abspath(tb[-1].filename).startswith(H.HERE):
            raise
        warnings.warn(f"the gate raised {type(e).__name__}: {e} (counted as a stage failure, never a PASS)")
        return RAISED


@pytest.mark.parametrize("label,call", [pytest.param(lab, fn, marks=mark or (), id=lab) for lab, fn, mark in CASES])
def test_a_required_gate_never_passes_on_nothing(media, qa, label, call):
    res = call_gate(call, media, qa)
    if res is RAISED:
        return
    assert production_reading(res) != "PASS", res


def test_every_required_row_has_a_vacuity_probe():
    """The probe list covers the whole REQUIRED inventory (a row added to the inventory without a probe fails)."""
    import release_auth as RA
    covered = {"G3b_cut_out_clean": "G3b", "G3c_acoustic_tail": "G3c", "G4s_layout_truth": "G4s", "G5_tech": "G5",
               "G8_sharpness": "G8", "G9_tail": "G9", "outro_locked": "outro_locked", "G12_credits": "G12",
               "G15_credits": "G15", "G16_sentence_boundary": "G16", "G17_onset_tail": "G17",
               "G18_word_for_word": "G18", "G19_edge_shots": "G19", "G20_signoff_names_all": "G20",
               "V1_visual_checklist": "V1", "G14_av_alignment": "G14 16x9", "G14_audio_offset": "G14 9x16",
               "vertical_silent_fallback": "vertical_silent_fallback"}
    required = set().union(*RA.INVENTORY.values())
    assert required <= set(covered), sorted(required - set(covered))
    probes = [lab for lab, _, _ in CASES] + ["V1", "vertical_silent_fallback"]       # V1: below; fallback: backstop
    missing = [row for row, key in covered.items() if row in required and not any(p.startswith(key) for p in probes)]
    assert not missing, missing


# ─────────────────────────────── partial and stale samples (G8) ───────────────────────────────

@pytest.fixture(scope="module")
def g8_media(tmp_path_factory):
    d = tmp_path_factory.mktemp("f4_g8")
    sharp = H.make_media(str(d / "sharp_src.mp4"), dur=10.0, size=(320, 180), pattern="testsrc2")
    short = H.make_media(str(d / "short_sharp.mp4"), dur=2.5, size=(320, 180), pattern="testsrc2")
    black = H.make_media(str(d / "black_now.mp4"), dur=2.5, size=(320, 180), pattern="black")
    return {"sharp_src": sharp, "short_sharp": short, "black_now": black}


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-gates F28 (OPEN): G8 accepts one measured sample as if all five were "
                                       "measured; REQUESTS.md R-20")
def test_g8_never_passes_on_one_of_five_samples(g8_media, tmp_path):
    """The segment claims 10 s, the final holds 2.5 s: four of G8's five sample times have no frame."""
    import qa_gates as Q
    ok, table = Q.gate_g8(g8_media["short_sharp"], [TH(0.0, 10.0)], str(tmp_path),
                          source_clips={"hook": g8_media["short_sharp"]})
    H.control(len(table[0]["out_variances"]) == 1, f"one sample was measured: {table}")
    assert ok is False, table


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-gates F10 / Claude-gates C1 (OPEN): a failed frame extraction leaves "
                                       "an earlier render's frame to be measured; REQUESTS.md R-21")
def test_g8_never_measures_a_frame_of_an_earlier_render(g8_media, tmp_path):
    """qa/ still holds what an earlier, good render's G8 wrote there (the gate's own files, whatever their names);
    the current final is black and too short for four of the five sample times. The black render must not pass on
    the earlier render's frames."""
    import qa_gates as Q
    qa_dir = tmp_path / "qa"
    qa_dir.mkdir()
    ok0, t0 = Q.gate_g8(g8_media["sharp_src"], [TH(0.0, 10.0)], str(qa_dir), source_clips={"hook": g8_media["sharp_src"]})
    H.control(ok0 is True and len(t0[0]["out_variances"]) == 5, f"the earlier render passed on 5 samples: {t0}")
    ok, table = Q.gate_g8(g8_media["black_now"], [TH(0.0, 10.0)], str(qa_dir),
                          source_clips={"hook": g8_media["sharp_src"]})
    assert ok is False and len(table[0]["out_variances"]) <= 1, table


# ─────────────────────────────── release-level backstop ───────────────────────────────

def test_whatever_a_gate_returns_on_nothing_release_blocks_it(media, qa):
    """For every vacuous probe that reads PASS at gate level TODAY (the filter is the reading, not the xfail mark, so
    this stays true as the gate fixes land), the production evidence rule counts 0 samples and release_auth blocks
    that row (the second wall behind the gate); the rule is also checked on the vacuous result shapes themselves
    ((True, []), an explicit skip, None), so the test never checks nothing. vertical_silent_fallback: no vertical
    clip checked = 0 samples."""
    import release_auth as RA
    import run_fresh as RF
    rows = H.passing_rows(RA)
    rowname = {"G3b": "G3b_cut_out_clean", "G3c": "G3c_acoustic_tail", "G4s": "G4s_layout_truth",
               "G8": "G8_sharpness", "G17a": "G17_onset_tail", "G18": "G18_word_for_word", "G19": "G19_edge_shots",
               "G14 16x9": "G14_av_alignment", "G14 9x16": "G14_audio_offset"}

    def blocked(fmt, row, data):
        ev = {f: {k: {"executed": True, "samples": 3} for k in r} for f, r in rows.items()}
        ev[fmt][row] = {"executed": True, "samples": RF._samples(data)}
        return RF._samples(data) == 0 and row in RA.blockers(fmt, rows[fmt], ev)

    for data in ([], {}, {"skip": True, "pass": True}, None, [None, {}, []]):        # the vacuous shapes themselves
        assert blocked("16x9", "G8_sharpness", data), data
    for lab, fn, mark in CASES:
        key = next((k for k in rowname if lab.startswith(k)), None)
        if key is None or key == "G18" and "lock" in lab:  # G18 empty lock: stage_gates' own 'missing' rule FAILS it
            continue
        res = call_gate(fn, media, qa)
        if res is RAISED or production_reading(res) != "PASS":
            continue                                       # not a vacuous PASS (any more): nothing to back up
        fmt = "9x16" if key == "G14 9x16" else "16x9"
        assert blocked(fmt, rowname[key], res[1]), (lab, res)
    assert blocked("9x16", "vertical_silent_fallback", [])


# ─────────────────────────────── model replies: V1 vision panel ───────────────────────────────

def _answers(fn):
    import visual_check as VC
    return {"answers": {k: fn(k) for k, _ in VC.CHECKLIST}}


WRONG_SHAPE = [json.dumps({"answers": []}), json.dumps({"answers": "yes"}), json.dumps({"answers": None}),
               json.dumps({"answers": {"credits_round_and_match": {"answer": "yes"}}}),          # one line only
               json.dumps({"verdict": "PASS"}), "ANSWERS_AS_STRINGS"]


def _v1(monkeypatch, tmp_path, content):
    import visual_check as VC
    import verify_pack as VP
    from PIL import Image
    sheet = str(tmp_path / "sheet.jpg")
    Image.new("RGB", (64, 36)).save(sheet)
    monkeypatch.setattr(VC, "_key", lambda: "test-key")
    monkeypatch.setattr(VC, "_call", lambda req, timeout: (content, {"choices": [{"message": {"content": content},
                                                                                   "finish_reason": "stop"}]}))
    ok, per = VC.ask_panel(sheet, "9x16")
    return ok, VP.panel_ok(per)


@pytest.mark.parametrize("content", H.GARBAGE_REPLIES + WRONG_SHAPE)
def test_v1_never_passes_on_a_garbage_reply(monkeypatch, tmp_path, content):
    if content == "ANSWERS_AS_STRINGS":                            # every line 'yes' but not an object
        content = json.dumps(_answers(lambda k: "yes"))
    assert _v1(monkeypatch, tmp_path, content) == (False, False)


@pytest.mark.parametrize("bad", ["no", "yes, mostly", "n/a", "", None, True, "YES!"])
def test_v1_one_line_not_exactly_yes_fails(monkeypatch, tmp_path, bad):
    import visual_check as VC
    first = VC.CHECKLIST[0][0]
    content = json.dumps(_answers(lambda k: {"answer": bad if k == first else "yes", "why": "x"}))
    assert _v1(monkeypatch, tmp_path, content) == (False, False)


def test_v1_control_a_whole_yes_reply_passes(monkeypatch, tmp_path):
    """Harmless variation (case, whitespace) is accepted: the control proves the fake reaches the verdict."""
    content = "```json\n" + json.dumps(_answers(lambda k: {"answer": " YES ", "why": "looked"})) + "\n```"
    assert _v1(monkeypatch, tmp_path, content) == (True, True)


# ─────────────────────────────── model replies: editorial decisions ───────────────────────────────

Q_EVENT = {"underlying_event": "Bitcoin ETFs saw $1.66B of net outflows last week", "action": "outflows",
           "affected_object": "Bitcoin ETFs", "entities": [{"name": "Bitcoin ETFs"}], "must_not_confuse_with": []}
EXCERPTS = [{"chunk_id": "vid1:0300-0330",
             "text": "Bitcoin ETFs saw one point six six billion dollars of outflows last week, the data shows."}]
GOOD_ADJ = {"verdict": "CURRENT_EVENT", "supporting_chunk_ids": ["vid1:0300-0330"],
            "evidence_quote": "Bitcoin ETFs saw one point six six billion dollars of outflows last week",
            "confidence": 0.9, "reason": "states it"}
GOOD_SUP = {"support": "SUPPORTS", "same_actor_action_object": True, "presented_as": "current", "reason": "x"}
VIDEO = {"title": "t", "channel": "c", "published_at": "2026-11-11"}
BAD = H.GARBAGE_REPLIES + [json.dumps({**GOOD_SUP, "same_actor_action_object": "true"}),
                           json.dumps({**GOOD_SUP, "presented_as": None}), json.dumps({"support": "SUPPORTS"}),
                           json.dumps(GOOD_ADJ).replace('"confidence": 0.9', '"confidence": NaN'),   # NaN in a
                           json.dumps({**GOOD_ADJ, "confidence": 1.5}),                              # validated field
                           json.dumps({**GOOD_ADJ, "supporting_chunk_ids": "vid1:0300-0330"})]


def test_control_whole_replies_are_counted():
    import story_semantics as SM
    v = SM.adjudicate(H.fake_llm([json.dumps(GOOD_ADJ), json.dumps(GOOD_SUP)]), Q_EVENT, VIDEO, EXCERPTS, "2026-11-12")
    assert v["counted_as_same_event"] is True, v


@pytest.mark.parametrize("raw", BAD)
def test_adjudicate_never_counts_a_garbage_reply(raw):
    import story_semantics as SM
    v = SM.adjudicate(H.fake_llm([raw]), Q_EVENT, VIDEO, EXCERPTS, "2026-11-12")
    assert v["counted_as_same_event"] is False and v["verdict"] in ("INCONCLUSIVE", "UNRELATED", "TOPIC_ONLY",
                                                                    "BACKGROUND", "CURRENT_EVENT"), v
    v = SM.adjudicate(H.fake_llm([json.dumps(GOOD_ADJ), raw]), Q_EVENT, VIDEO, EXCERPTS, "2026-11-12")
    assert v["counted_as_same_event"] is False and v["support"] != "SUPPORTS", v


@pytest.mark.parametrize("raw", H.GARBAGE_REPLIES + [
    json.dumps({"ratings": [{"id": "p1", "score": 9, "fault": "none"}]}),
    json.dumps({"ratings": [{"id": "p1", "score": "5", "fault": "none"}]}),
    '{"ratings": [{"id": "p1", "score": NaN, "fault": "none"}]}',
    json.dumps({"ratings": [{"id": "p1", "score": 5, "fault": "great"}]}),
    json.dumps({"ratings": [{"id": "p1", "score": 5, "fault": "none"}, {"id": "p1", "score": 1, "fault": "none"}]}),
    json.dumps({"ratings": []})])
def test_rate_passages_never_rates_from_a_garbage_reply(raw):
    import story_semantics as SM
    passages = [{"pid": "p1", "channel": "c", "duration": 10.0, "text": "Bitcoin fell."},
                {"pid": "p2", "channel": "d", "duration": 11.0, "text": "ETFs saw outflows."}]
    out, err = SM.rate_passages(H.fake_llm([raw]), Q_EVENT, passages)
    assert out == {} and err, (out, err)


@pytest.mark.parametrize("raw", H.GARBAGE_REPLIES)
def test_derive_story_query_never_invents_a_query(raw):
    import story_semantics as SM
    with pytest.raises(SM.LLMParseError):
        SM.derive_story_query(H.fake_llm([raw]), {"headline": "Bitcoin ETFs shed $1.66B", "summary": "s",
                                                  "source": "x"}, "2026-11-12")


@pytest.mark.parametrize("raw", H.GARBAGE_REPLIES)
def test_label_cluster_never_labels_from_a_garbage_reply(raw):
    import story_semantics as SM
    chunks = [{"chunk_id": f"v{i}:0000-0030", "video_id": f"v{i}", "channel_name": f"C{i}",
               "text": "Bitcoin ETFs saw heavy outflows last week as investors pulled money."} for i in range(2)]
    r = SM.label_cluster(H.fake_llm([raw]), chunks, np.eye(2, dtype=np.float32), {"chunk_idx": [0, 1]}, "2026-11-12")
    assert r["current_ok"] is False and not r.get("is_specific_event"), r


@pytest.mark.parametrize("raw", H.GARBAGE_REPLIES)
def test_sentence_and_adjacency_checks_never_admit_on_a_garbage_reply(raw):
    import editorial_select as ES
    ok, why = ES.sentence_on_event(H.fake_llm([raw]), Q_EVENT, "Bitcoin ETFs saw 1.66 billion dollars of outflows.")
    assert ok is False, why
    ok, why = ES.adjacent_admissible(H.fake_llm([raw]), Q_EVENT, "Bitcoin fell to 74,000 dollars today.",
                                     "That 74,000 dollar level is the one to watch.")
    assert ok is False, why
