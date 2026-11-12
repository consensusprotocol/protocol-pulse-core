"""Scoring against the selector's records (pipeline/oracle/score.py): a line-up is traced by its own sentences."""
import pytest
from conftest import legal_lineup

from pipeline.oracle import score as S


def by_id(rows):
    return {r["id"]: r for r in rows}


def cluster(members, screen="48h", gate=None, channels=("Alpha", "Beta")):
    return {"channels": list(channels), "member_chunk_ids": members, "screen": screen, "gate": gate}


def cand(idx, decision, **kw):
    return {"origin": "transcript_cluster", "cluster_index": idx, "headline": f"claim {idx}", "decision": decision,
            "importance_gate": [], **kw}


A_HOOK, B_CLIP, C_CLIP = "vidAAAAAAAA:0-12000", "vidBBBBBBBB:39000-62000", "vidCCCCCCCC:99000-116000"


def test_classify_maps_every_recorded_decision_to_its_stage():
    cases = {"inconclusive: currentness missing: no verified transcript evidence": "CURRENTNESS",
             "rejected: coverage 1 < 2 independent channels": "COVERAGE",
             "rejected: only 1 layout-eligible channel(s) with evidence (clips need >= 2)": "LAYOUT_ELIGIBILITY",
             "rejected: no quote-anchored boundary window in layout-eligible evidence": "WINDOWS",
             "rejected: no hook passage scored >= 4.0": "HOOK_SCORE",
             "rejected: every hook scoring >= 4.0 failed the stand-alone/topic rule": "STAND_ALONE",
             "rejected: clip quality: 1 usable clips across 2 channel(s)": "ASSEMBLY",
             "INFRA_HOLD: word-level transcription blocked": "INFRA", "producible": "PRODUCIBLE",
             "coverage_qualified": "NOT_REACHED", None: "NOT_REACHED"}
    for d, stage in cases.items():
        assert S.classify({"decision": d})[0] == stage, d
    assert S.classify({"decision": None, "importance_gate": ["bitcoin_relevance 2 < 3"]})[0] == "IMPORTANCE"
    assert S.classify({"decision": "x", "merged_into": "other"})[0] == "DEDUPE"


def test_no_cluster_holding_two_of_its_channels_is_cluster_formation_only_in_a_complete_record(day_rows):
    rec = {"emergent_clusters": [cluster([A_HOOK, "vidZZZZZZZZ:0-9000"])], "candidates": [],
           "decision": "HOLD: no candidate is producible"}
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "CLUSTER_FORMATION" and t["n_near"] == 1 and not t["carriers"]
    del rec["decision"]                                  # the run stopped: later pools / headlines never ran
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "NOT_REACHED" and "no cluster held" in t["note"]      # audit round 2, F8


def test_a_carrier_cluster_stopped_by_the_bitcoin_screen(day_rows):
    rec = {"emergent_clusters": [cluster([A_HOOK, B_CLIP], screen="Bitcoin screen: 1 channel(s) < 2")], "candidates": []}
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "BITCOIN_SCREEN" and set(t["best_carrier"]["channels_held"]) == {"Alpha", "Beta"}


def verdicts(*counted, also=()):
    v = lambda vid, ok: {"video_id": vid, "channel": vid[3], "counted_as_same_event": ok, "verdict": "CURRENT_EVENT",
                         "excerpts": [{"chunk_id": f"{vid}:0-1000"}]}
    return {"status": "done", "verdicts": [v(x, True) for x in counted] + [v(x, False) for x in also]}


HOOK_WIN = {"kind": "hook", "video_id": "vidAAAAAAAA", "start": 0.0, "end": 9.5, "channel": "Alpha", "clip_score": 3.0,
            "clip_fault": "none", "stand_alone": {"why": "opens on 'bitcoin'"}}
CLIP_WIN = dict(HOOK_WIN, kind="clip", video_id="vidCCCCCCCC", start=100.0, end=114.5, channel="Gamma", clip_score=4.0)


def test_the_furthest_carrier_decides_and_its_windows_are_reported(day_rows):
    rec = {"emergent_clusters": [cluster([A_HOOK, B_CLIP]), cluster([A_HOOK, C_CLIP])],
           "candidates": [cand(0, "rejected: coverage 1 < 2 independent channels", coverage=verdicts("vidAAAAAAAA")),
                          cand(1, "rejected: no hook passage scored >= 4.0",
                               coverage=verdicts("vidAAAAAAAA", "vidCCCCCCCC"),
                               clip_quality={"candidates": [HOOK_WIN, CLIP_WIN]})]}
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "HOOK_SCORE" and t["best_carrier"]["cluster"] == 1
    assert [w["ids"] for w in t["best_carrier"]["survival"]["windows_on_lineup"]] == [["vidAAAAAAAA:0"], ["vidCCCCCCCC:10", "vidCCCCCCCC:11"]]


def test_the_lineup_is_lost_at_coverage_even_when_its_candidate_went_further(day_rows):
    rec = {"emergent_clusters": [cluster([A_HOOK, C_CLIP])],
           "candidates": [cand(0, "rejected: no hook passage scored >= 4.0",
                               coverage=verdicts("vidAAAAAAAA", also=("vidCCCCCCCC",)),
                               clip_quality={"candidates": [HOOK_WIN]})]}
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "COVERAGE" and "for 1 of its channels (Alpha)" in t["best_carrier"]["detail"]


def test_the_lineup_is_lost_at_layout_when_the_record_marked_a_counted_channel_ineligible(day_rows):
    cov = verdicts("vidAAAAAAAA", "vidBBBBBBBB")
    for v in cov["verdicts"]:
        v["layout_eligible"] = v["video_id"] != "vidBBBBBBBB"           # the run's own decision (a chyron channel)
    rec = {"emergent_clusters": [cluster([A_HOOK, B_CLIP])],
           "candidates": [cand(0, "rejected: no quote-anchored boundary window in layout-eligible evidence",
                               coverage=cov)]}
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "LAYOUT_ELIGIBILITY" and "layout-eligible: Alpha" in t["best_carrier"]["detail"]


def test_todays_registry_never_rewrites_what_the_record_decided_about_layout(day_rows):
    rows = by_id(day_rows)
    for i in ("vidBBBBBBBB:4", "vidBBBBBBBB:5", "vidBBBBBBBB:6", "vidBBBBBBBB:7"):
        rows[i] = dict(rows[i], layout_eligible=False)                   # ineligible TODAY (registry changed since)
    cov = verdicts("vidAAAAAAAA", "vidBBBBBBBB")
    for v in cov["verdicts"]:
        v["layout_eligible"] = True                                      # eligible when the run decided
    rec = {"emergent_clusters": [cluster([A_HOOK, B_CLIP])],
           "candidates": [cand(0, "rejected: no quote-anchored boundary window in layout-eligible evidence",
                               coverage=cov)]}
    assert S.trace(legal_lineup(), rows, rec)["loss_stage"] == "WINDOWS"   # audit F2: not blamed on layout


def test_a_run_that_stopped_before_deciding_is_not_reached(day_rows):
    unfinished = dict(verdicts("vidAAAAAAAA"), status="in_progress")
    rec = {"emergent_clusters": [cluster([A_HOOK, B_CLIP])], "candidates": [cand(0, None, coverage=unfinished)]}
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "NOT_REACHED" and t["undecided_carriers"] == 1
    rec["emergent_clusters"].append(cluster([A_HOOK, C_CLIP]))
    rec["candidates"].append(cand(1, "rejected: coverage 1 < 2 independent channels", coverage=verdicts("vidAAAAAAAA")))
    t = S.trace(legal_lineup(), by_id(day_rows), rec)                       # incomplete record: the undecided
    assert t["loss_stage"] == "NOT_REACHED" and t["undecided_carriers"] == 1  # carrier might have got further
    assert "furthest decided carrier: COVERAGE" in t["note"]
    rec["decision"] = "HOLD: no candidate is producible"                    # a complete record decides it
    assert S.trace(legal_lineup(), by_id(day_rows), rec)["loss_stage"] == "COVERAGE"


def test_label_rejection_and_selection(day_rows):
    rec = {"emergent_clusters": [cluster([A_HOOK, B_CLIP], gate="label: not a specific current event")],
           "candidates": []}
    assert S.trace(legal_lineup(), by_id(day_rows), rec)["loss_stage"] == "LABEL"
    rec = {"emergent_clusters": [cluster([A_HOOK, B_CLIP])], "candidates": [cand(0, "producible")],
           "selected": {"headline": "claim 0"}}
    assert S.trace(legal_lineup(), by_id(day_rows), rec)["loss_stage"] == "SELECTED"


def test_a_headline_whose_excerpts_hold_two_channels_is_a_carrier(day_rows):
    v = lambda vid, cid: {"video_id": vid, "counted_as_same_event": False, "excerpts": [{"chunk_id": cid}]}
    rec = {"emergent_clusters": [], "candidates": [
        {"origin": "story_engine", "headline": "Bitcoin below $74K", "decision":
         "inconclusive: currentness missing: no verified transcript evidence of a current development",
         "coverage": {"verdicts": [v("vidAAAAAAAA", A_HOOK), v("vidCCCCCCCC", C_CLIP)]}}]}
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "CURRENTNESS" and t["best_carrier"]["path"] == "story_engine coverage"


def test_pre_dec13_records_trace_through_the_label_excerpts(day_rows):
    rec = {"emergent_clusters": [{"channels": ["Alpha", "Beta", "Gamma"], "label": {
        "headline": "old claim", "excerpt_chunk_ids": [A_HOOK, B_CLIP]}, "rejected": "not a specific current event"}],
        "candidates": []}
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "LABEL" and t["best_carrier"]["membership"].startswith("label excerpts only")


def test_equivalence_needs_a_shared_sentence_in_two_channels(day_rows):
    rows = by_id(day_rows)
    one = [{"video_id": "vidAAAAAAAA", "start": 0.0, "end": 9.5}]
    two = one + [{"video_id": "vidCCCCCCCC", "start": 100.0, "end": 114.5}]
    assert S.equivalent(one, legal_lineup(), rows) == (False, ["Alpha"])
    assert S.equivalent(two, legal_lineup(), rows) == (True, ["Alpha", "Gamma"])


def test_a_split_development_is_cluster_formation_with_each_near_clusters_own_stage(day_rows):
    # E-FAIL-023 class: the development sits in two clusters, each holding ONE of the line-up's channels
    rec = {"emergent_clusters": [cluster([A_HOOK, "vidZZZZZZZZ:0-9000"]), cluster([C_CLIP, "vidYYYYYYYY:0-9000"])],
           "candidates": [cand(0, "rejected: coverage 1 < 2 independent channels"),
                          cand(1, "inconclusive: currentness missing: no verified transcript evidence")],
           "decision": "HOLD: no candidate is producible"}
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "CLUSTER_FORMATION" and not t["carriers"] and t["n_near"] == 2
    assert t["near_furthest_stage"] == "COVERAGE" and t["near_furthest"]["cluster"] == 0
    assert [n["stage"] for n in t["near_carriers"]] == ["COVERAGE", "CURRENTNESS"]


def test_a_backtest_without_word_records_decided_nothing_at_clip_quality(day_rows):
    rec = {"emergent_clusters": [cluster([A_HOOK, C_CLIP])],
           "candidates": [cand(0, "rejected: clip quality: 0 usable clips across 1 channel(s)",
                               coverage=verdicts("vidAAAAAAAA", "vidCCCCCCCC"),
                               clip_quality={"candidates": [HOOK_WIN], "other_failures": [
                                   ["vidCCCCCCCC", "backtest: no word record (a live run would transcribe it)"]]})]}
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "NOT_RERUN" and t["undecided_carriers"] == 1
    assert "no word transcript offline for Gamma" in t["best_carrier"]["detail"]


def test_cluster_formation_is_only_blamed_where_clusters_were_formed(day_rows):
    crashed = {"emergent_clusters": [], "candidates": [], "crashed": {"error": "TypeError"}}
    t = S.trace(legal_lineup(), by_id(day_rows), crashed)
    assert t["loss_stage"] == "NOT_REACHED" and "before clustering" in t["note"]
    old = {"emergent_clusters": [{"channels": ["Alpha"], "label": {"headline": "x", "excerpt_chunk_ids": []}}],
           "candidates": []}
    assert S.trace(legal_lineup(), by_id(day_rows), old)["loss_stage"] == "NOT_REACHED"      # stopped, partial
    t = S.trace(legal_lineup(), by_id(day_rows), dict(old, decision="HOLD: no candidate is producible"))
    assert t["loss_stage"] == "CLUSTER_FORMATION" and "label's excerpts only" in t["note"]


def test_the_selected_candidate_does_not_lift_a_lineup_whose_own_statements_it_dropped(day_rows):
    rec = {"emergent_clusters": [cluster([A_HOOK, B_CLIP])],
           "candidates": [cand(0, "producible", coverage=verdicts("vidAAAAAAAA", also=("vidBBBBBBBB",)))],
           "selected": {"headline": "claim 0"}}
    t = S.trace(legal_lineup(), by_id(day_rows), rec)
    assert t["loss_stage"] == "COVERAGE"            # audit F10a: the story was chosen, this line-up's pair was not


def test_a_report_is_never_written_around_an_unfilled_placeholder(tmp_path):
    from pipeline.oracle import report as RP
    a = tmp_path / "ANALYSIS.md"
    a.write_text("judge: @GLM_JUDGE@")
    with pytest.raises(ValueError, match="unfilled placeholders"):
        RP.analysis_text(str(a))
    a.write_text("judge: NOT MEASURED (batch incomplete)")
    assert RP.analysis_text(str(a)) == "judge: NOT MEASURED (batch incomplete)"
