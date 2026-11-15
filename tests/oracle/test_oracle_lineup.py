"""Strict reply schemas and deterministic line-up checks (pipeline/oracle/lineup.py). Must-fail fixtures first."""
import copy
import json

import pytest
from conftest import judge_reply, legal_lineup, oracle_reply

from pipeline.oracle import lineup as L


def by_id(rows):
    return {r["id"]: r for r in rows}


# ── the oracle's reply: malformed / empty / unknown ids are ORACLE_FAILED, never NONE ──

@pytest.mark.parametrize("text", ["", "   \n", "null", "[]", "not json", '{"verdict": "LINEUPS"}', "{}"])
def test_an_empty_or_malformed_reply_is_oracle_failed(day_rows, text):
    with pytest.raises(L.OracleFailed):
        L.parse_oracle(text, by_id(day_rows))


@pytest.mark.parametrize("bad", ["vidAAAAAAAA", "vidAAAAAAAA:x", "vidAAAAAAAA: 0", "vid AAAAAAAA:0", "A:0", 7, None,
                                 "vidAAAAAAAA:0;vidAAAAAAAA:1"])
def test_a_malformed_sentence_id_is_oracle_failed(day_rows, bad):
    lu = legal_lineup()
    lu["clips"][0] = [bad]
    with pytest.raises(L.OracleFailed, match="malformed|list of sentence ids"):
        L.parse_oracle(oracle_reply([lu]), by_id(day_rows))


def test_an_id_that_is_not_in_the_universe_is_oracle_failed(day_rows):
    lu = legal_lineup()
    lu["clips"][2] = ["vidCCCCCCCC:10", "vidCCCCCCCC:99"]          # well-formed, not a row of the day
    with pytest.raises(L.OracleFailed, match="not in the day's statements"):
        L.parse_oracle(oracle_reply([lu]), by_id(day_rows))


@pytest.mark.parametrize("mutate", [
    lambda o: o.update(verdict="MAYBE"),
    lambda o: o.update(verdict="NONE", none_reason="", lineups=[]),           # NONE without a reason
    lambda o: o.update(verdict="NONE", none_reason="nothing"),                # NONE that still lists a line-up
    lambda o: o.update(lineups=[]),                                           # LINEUPS with none
    lambda o: o.update(none_reason="nothing reached three channels"),        # LINEUPS that also says there is none
    lambda o: o.update(lineups=[legal_lineup()] * 4),                        # more than 3
    lambda o: o.update(extra="x"),                                            # unknown key
    lambda o: o.pop("none_reason"),                                           # missing key
    lambda o: o["lineups"][0].pop("development"),
    lambda o: o["lineups"][0].update(clips=[]),
    lambda o: o["lineups"][0].update(hook=[]),
    lambda o: o["lineups"][0].update(development="  "),
    lambda o: o["lineups"][0].update(note="x"),
])
def test_a_partial_or_contradictory_reply_is_oracle_failed(day_rows, mutate):
    o = json.loads(oracle_reply())
    mutate(o)
    with pytest.raises(L.OracleFailed):
        L.parse_oracle(json.dumps(o), by_id(day_rows))


def test_a_valid_reply_parses_and_none_keeps_its_reason(day_rows):
    p = L.parse_oracle(oracle_reply(), by_id(day_rows))
    assert p["verdict"] == "LINEUPS" and p["lineups"][0]["hook"] == ["vidAAAAAAAA:0"]
    n = L.parse_oracle(oracle_reply([], "NONE", "no development reached two channels"), by_id(day_rows))
    assert n == {"verdict": "NONE", "none_reason": "no development reached two channels", "lineups": []}


# ── the judge's reply: LEGAL only when every check is exactly true ──

@pytest.mark.parametrize("text", [
    "", "{}", "garbage",
    judge_reply("LEGAL", false=("current",)),                                 # LEGAL with a false check
    judge_reply("ILLEGAL"),                                                   # ILLEGAL with every check true
])
def test_an_inconsistent_or_empty_verdict_is_judge_failed(text):
    with pytest.raises(L.JudgeFailed):
        L.parse_judge(text)


@pytest.mark.parametrize("mutate", [
    lambda o: o["checks"].update(current="true"),                             # a string is not a boolean
    lambda o: o["checks"].update(current=1),                                  # nor is an int
    lambda o: o["checks"].pop("no_altcoin_content"),                          # a check left out
    lambda o: o["checks"].update(extra=True),
    lambda o: o.update(failed=["current"]),                                   # failed names a true check
    lambda o: o.update(verdict="PASS"),
    lambda o: o.update(reason=""),
])
def test_a_mistyped_or_partial_verdict_is_judge_failed(mutate):
    o = json.loads(judge_reply())
    mutate(o)
    with pytest.raises(L.JudgeFailed):
        L.parse_judge(json.dumps(o))


def test_consistent_verdicts_parse():
    assert L.parse_judge(judge_reply())["verdict"] == "LEGAL"
    v = L.parse_judge(judge_reply("ILLEGAL", false=("current", "hook_stands_alone")))
    assert v["verdict"] == "ILLEGAL" and v["failed"] == ["current", "hook_stands_alone"]


# ── deterministic checks ──

def test_the_legal_fixture_passes_every_check(day_rows):
    bad, summ = L.check(legal_lineup(), by_id(day_rows))
    assert bad == [], bad
    assert summ["channels"] == ["Alpha", "Beta", "Gamma"] and summ["content_s"] == 53.0


def test_an_altcoin_sentence_smuggled_into_a_lineup_fails(day_rows):
    lu = legal_lineup()
    lu["clips"][2] = ["vidCCCCCCCC:11", "vidCCCCCCCC:12"]                    # 'Ethereum fell even harder ...'
    bad, _ = L.check(lu, by_id(day_rows))
    assert any("altcoin content in vidCCCCCCCC:12 (ethereum)" in b for b in bad), bad


@pytest.mark.parametrize("edit, expect", [
    (lambda lu: lu.update(hook=["vidAAAAAAAA:0", "vidAAAAAAAA:1"]), "hook: 15.0 s outside 8-12 s"),
    (lambda lu: lu["clips"].__setitem__(0, ["vidBBBBBBBB:4", "vidBBBBBBBB:6"]), "not consecutive"),
    (lambda lu: lu["clips"].__setitem__(0, ["vidBBBBBBBB:5", "vidCCCCCCCC:10"]), "more than one video"),
    (lambda lu: lu["clips"].__setitem__(1, ["vidBBBBBBBB:7", "vidBBBBBBBB:8"]), "does not end on a statement"),
    (lambda lu: lu["clips"].__setitem__(2, ["vidBBBBBBBB:4", "vidBBBBBBBB:5"]), "already used"),
    (lambda lu: lu.update(clips=lu["clips"][:1]), "1 clips (needs 2-3)"),
    (lambda lu: lu.update(clips=lu["clips"][:2]), "content 38.5 s < 46.5 s"),
    (lambda lu: lu["clips"].__setitem__(2, ["vidBBBBBBBB:6"]), "outside 12-20 s"),
])
def test_each_structural_rule_fails_its_fixture(day_rows, edit, expect):
    lu = copy.deepcopy(legal_lineup())
    edit(lu)
    bad, _ = L.check(lu, by_id(day_rows))
    assert any(expect in b for b in bad), (expect, bad)


def test_one_channel_and_the_per_video_and_per_channel_limits(day_rows):
    rows = by_id(day_rows)
    extra = dict(rows["vidBBBBBBBB:4"], id="vidBBBBBBBB:9", sentence_index=9, start_s=80.0, end_s=94.0,
                 duration_s=14.0, text="Bitcoin dominance rose to 61 percent.")
    rows[extra["id"]] = extra
    lu = {"hook": ["vidAAAAAAAA:0"], "clips": [["vidBBBBBBBB:4", "vidBBBBBBBB:5"], ["vidBBBBBBBB:6", "vidBBBBBBBB:7"],
                                               ["vidBBBBBBBB:9"]]}
    bad, _ = L.check(lu, rows)
    assert any("3 segments from video vidBBBBBBBB > 2" in b for b in bad), bad
    assert any("3 clips from one channel (UCb) > 2" in b for b in bad), bad
    solo = {"hook": ["vidCCCCCCCC:10"], "clips": [["vidCCCCCCCC:11", "vidCCCCCCCC:12"], ["vidCCCCCCCC:13"]]}
    bad, _ = L.check(solo, rows)
    assert any("1 channel(s) < 2" in b for b in bad), bad


def test_altcoin_screen_reads_canonical_words():
    assert L.altcoin_terms("Bitcoin rose while ETH and Ethereum fell.") == ["eth", "ethereum"]
    assert L.altcoin_terms("Welcome back to Altcoin Daily, today Bitcoin.") == []      # a channel name, not content
    assert L.altcoin_terms("This is not altcoin season.") == ["altcoin"]
    assert L.altcoin_terms("Bitcoin, either way, is up.") == []                        # 'either' is not 'ether'


def test_layout_column_marks_lineups_that_die_without_ineligible_channels(day_rows):
    rows = by_id(day_rows)
    _, summ = L.check(legal_lineup(), rows)
    assert L.layout_survives(summ)[0] is True
    for i in ("vidBBBBBBBB:4", "vidBBBBBBBB:5", "vidBBBBBBBB:6", "vidBBBBBBBB:7"):
        rows[i] = dict(rows[i], layout_eligible=False)                     # Beta has a burned-in chyron
    _, summ = L.check(legal_lineup(), rows)
    ok, why = L.layout_survives(summ)
    assert ok is False and "without Beta" in why, why


def test_a_sentence_cut_by_a_speaker_change_is_not_a_whole_sentence_even_mid_segment(day_rows):
    rows = {r["id"]: r for r in day_rows}
    lu = legal_lineup()
    first = lu["clips"][0][0]
    rows[first] = dict(rows[first], complete=False)              # '>>' ended it, not its own punctuation
    bad, _ = L.check(lu, rows)
    assert any("not a whole sentence" in b and first in b for b in bad)
