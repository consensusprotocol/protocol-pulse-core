"""Witness checks on moments line-ups (pipeline/oracle/witness.py, orchestrator note 02:30): a clip in its original
context, no implied relation across videos, one excerpt per channel, no accusation / imperative / ad read."""
import json

import pytest
from conftest import legal_lineup

from pipeline.oracle import witness as W


def by_id(rows):
    return {r["id"]: r for r in rows}


def seg(n, view="own_sincere", sincere=True, **flags):
    return {"segment": n, "speaker_view": view, "own_sincere_assertion": sincere, "reason": "r",
            **{f: flags.get(f, False) for f in W.FLAGS}}


def reply(segs, relation=False, verdict=None):
    ok = all(s["own_sincere_assertion"] and not any(s[f] for f in W.FLAGS) for s in segs) and not relation
    return json.dumps({"segments": segs, "implied_relation_across_videos": relation,
                       "verdict": verdict or ("PASS" if ok else "FAIL"), "reason": "r"})


def test_a_whole_consistent_verdict_parses():
    assert W.parse(reply([seg(1), seg(2), seg(3)]), 3)["verdict"] == "PASS"
    assert W.parse(reply([seg(1), seg(2, "sarcastic", False), seg(3)]), 3)["verdict"] == "FAIL"


@pytest.mark.parametrize("text", [
    "", "{}", "not json",
    reply([seg(1), seg(2)]),                                            # a segment left out (3 asked)
    reply([seg(1), seg(1), seg(2)]),                                    # a segment twice
    reply([seg(1), seg(2, "uncertain", True), seg(3)]),                 # 'uncertain' claimed sincere
    reply([seg(1), seg(2, "question", True), seg(3)]),                  # a question claimed sincere
    reply([seg(1), seg(2), seg(3, ad_read=True)], verdict="PASS"),       # PASS that contradicts a flag
    reply([seg(1), seg(2), seg(3)], relation=True, verdict="PASS"),     # PASS with an implied relation
    reply([seg(1), seg(2), dict(seg(3), speaker_view="opinion")]),      # an unknown view
])
def test_a_partial_or_contradictory_witness_reply_is_witness_failed(text):
    with pytest.raises(W.WitnessFailed):
        W.parse(text, 3)


def test_checks_fail_closed_when_the_witness_did_not_run(day_rows):
    ch = W.checks_of(legal_lineup(), by_id(day_rows), None)
    assert ch["sincere_in_context"] is None and ch["no_implied_relation"] is None
    assert ch["no_accusation_imperative_ad"] is None                   # every model check: not measured
    assert ch["one_excerpt_per_channel"] is False                      # Beta supplies two clips in the fixture


def test_a_witness_failed_lineup_is_left_out_of_every_witness_count_but_the_base(tmp_path, day_rows):
    from pipeline.oracle import run as R
    lu = legal_lineup()
    (tmp_path / "ORACLE.json").write_text(json.dumps({"lineups": [lu, lu]}))
    (tmp_path / "DAY.json").write_text(json.dumps({"lineups": [{"lineup": 1, "accepted": True},
                                                                {"lineup": 2, "accepted": True}]}))
    ok = {c: True for c in W.CHECKS}
    failed = W.checks_of(lu, by_id(day_rows), None)                    # WITNESS_FAILED: None per model check
    (tmp_path / "WITNESS.json").write_text(json.dumps({"lineups": [
        {"lineup": 1, "status": "OK", "checks": ok}, {"lineup": 2, "status": "WITNESS_FAILED", "checks": failed}],
        "oracle_sha256": R.oracle_sha(str(tmp_path))}))
    assert len(W.survivors(str(tmp_path), ())) == 2                     # base: the judge's acceptance only
    for c in W.CHECKS[1:]:
        assert len(W.survivors(str(tmp_path), (c,))) == 1               # None never counts as a pass
    assert len(W.survivors(str(tmp_path), W.CHECKS)) == 1


def test_each_check_reads_its_own_field(day_rows):
    v = json.loads(reply([seg(1), seg(2, buy_sell_imperative=True), seg(3), seg(4)], relation=True))
    ch = W.checks_of(legal_lineup(), by_id(day_rows), v)
    assert ch == {"one_excerpt_per_channel": False, "sincere_in_context": True, "no_implied_relation": False,
                  "no_accusation_imperative_ad": False}
