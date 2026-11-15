"""The 01:55 variants (orchestrator note 2026-11-12): windows as targets (law L-o), PBX's moments-first rule, and
sentence-disjoint line-up counts. The order's own rule set (same_dev_hard) must stay exactly what was measured."""
import copy
import hashlib
import json
import os

import pytest
from conftest import judge_reply, legal_lineup, oracle_reply

from pipeline.oracle import lineup as L
from pipeline.oracle import llm
from pipeline.oracle import prompts as P
from pipeline.oracle import run as R

NOW = "2026-11-10T09:31:52+00:00"
SENT_DAY = "/home/ultron/heimdall_probe/pp_redteam/oracle/20261110_093150"


def by_id(rows):
    return {r["id"]: r for r in rows}


def test_the_measured_rule_text_is_pinned():
    # the same_dev_hard artefacts of 2026-11-12 were produced with exactly this text
    assert hashlib.sha256(L.RULES.encode()).hexdigest() == "ff55a17e1614f03d30b2796bbf84acc19317bde04c1f003c7b3ed768ef02f116"
    assert L.RULES.splitlines()[0].endswith("Bitcoin news video made only of partner channels' own words)")
    assert "One hook of 8-12 seconds, then 2 or 3 clips of 12-20 seconds each" in L.RULES
    assert "TARGETS" in L.RULES_SAME_TARGETS and "TARGETS" in L.RULES_MOMENTS and "TARGETS" not in L.RULES
    assert "need NOT be about one" in L.RULES_MOMENTS and "need NOT" not in L.RULES_SAME_TARGETS


@pytest.mark.skipif(not os.path.exists(os.path.join(SENT_DAY, "oracle_prompt.txt")), reason="artefacts not here")
def test_the_prompts_actually_sent_reproduce_byte_for_byte():
    from pipeline.oracle import export as X
    rows = R.oracle_rows(X.read_rows(os.path.join(SENT_DAY, "BITCOIN_STATEMENTS_20261110_093150.jsonl")))
    now = json.load(open(os.path.join(SENT_DAY, "BITCOIN_STATEMENTS_20261110_093150.manifest.json")))["started"]
    sent = open(os.path.join(SENT_DAY, "oracle_prompt.txt")).read()
    assert sent == f"SYSTEM:\n{P.ORACLE_SYSTEM}\n\nUSER:\n{P.oracle_prompt(rows, now)}"
    o = json.load(open(os.path.join(SENT_DAY, "ORACLE.json")))
    js = open(os.path.join(SENT_DAY, "judge_L2_prompt.txt")).read()
    assert js == f"SYSTEM:\n{P.JUDGE_SYSTEM}\n\nUSER:\n{P.judge_prompt(o['lineups'][1], by_id(rows), now)}"


def test_windows_are_violations_only_when_hard(day_rows):
    lu = legal_lineup()
    lu["hook"] = ["vidAAAAAAAA:0", "vidAAAAAAAA:1"]                      # 15.0 s hook
    hard, summ = L.check(lu, by_id(day_rows), windows_hard=True)
    soft, summ2 = L.check(lu, by_id(day_rows), windows_hard=False)
    assert any("hook: 15.0 s outside 8-12 s" in b for b in hard)
    assert soft == [] and summ2["window_misses"] == ["hook: 15.0 s outside 8-12 s"]
    lu["clips"] = lu["clips"][:2]                                      # content floor stays hard either way
    lu["hook"] = ["vidAAAAAAAA:0"]
    assert any("content" in b for b in L.check(lu, by_id(day_rows), windows_hard=False)[0])


def test_disjoint_max_counts_line_ups_that_share_no_sentence(day_rows):
    a = legal_lineup()
    b = copy.deepcopy(a)                                               # shares everything with a
    c = {"hook": ["vidCCCCCCCC:13"], "clips": [["vidAAAAAAAA:2"], ["vidBBBBBBBB:8"]]}   # disjoint from a
    assert L.disjoint_max([a]) == [0]
    assert len(L.disjoint_max([a, b])) == 1
    assert L.disjoint_max([a, b, c]) in ([0, 2], [1, 2])
    assert L.disjoint_max([]) == []


def moment_judge_reply(verdict="LEGAL", false=()):
    checks = {k: k not in false for k in L.MOMENT_CHECKS}
    return json.dumps({"development": "Bitcoin's weekend sell-off and the ETF outflows", "checks": checks,
                       "failed": sorted(false), "verdict": verdict, "reason": "checked"})


def test_a_moments_day_uses_its_rules_checks_and_own_directory(tmp_path, day_rows, fake):
    from conftest import row
    rows = day_rows + [row("vidDDDDDDDD", 0, "Delta", "UCd", 0.0, 8.5, "Bitcoin miners sold 4,000 BTC this week."),
                       row("vidDDDDDDDD", 1, "Delta", "UCd", 8.6, 15.0, "That is the most since April."),
                       row("vidDDDDDDDD", 2, "Delta", "UCd", 15.1, 23.6, "Hashprice fell to a record low."),
                       row("vidEEEEEEEE", 0, "Echo", "UCe", 0.0, 10.5, "Bitcoin's funding turned negative across "
                           "every major venue."),
                       row("vidEEEEEEEE", 1, "Echo", "UCe", 10.6, 21.0, "That tells you leverage has been flushed "
                           "out of the market.")]
    second = {"development": "UNIQUE-M", "current_because": "WHY-M", "hook": ["vidDDDDDDDD:0"],
              "clips": [["vidDDDDDDDD:1", "vidDDDDDDDD:2"], ["vidEEEEEEEE:0", "vidEEEEEEEE:1"], ["vidAAAAAAAA:2"]]}
    o = fake([oracle_reply([legal_lineup(), second])])
    j = fake([moment_judge_reply(), moment_judge_reply()])
    d = R.run_day(str(tmp_path), rows, NOW, o, j, llm.Ledger(str(tmp_path / "S.jsonl")), variant="moments")
    assert os.path.exists(tmp_path / "moments" / "DAY.json") and not os.path.exists(tmp_path / "DAY.json")
    assert not any(m in u for _, u in j.prompts for m in ("UNIQUE-M", "WHY-M"))   # the moments judge is blind too
    assert "need NOT be about one" in o.prompts[0][1] and "up to 8" in o.prompts[0][1]
    assert '"two_channels_never_misattributed": true/false' in j.prompts[0][1]
    assert d["accepted"] == 2 and d["distinct_accepted"] == 2 and d["availability"] == "AVAILABLE"
    # second's 21.0 s clip vidEEEEEEEE:0-1 misses its 12-20 s target: legal under L-o, not with the windows hard
    assert d["accepted_hard_windows"] == 1 and d["distinct_accepted_hard_windows"] == 1


def test_a_moments_verdict_with_the_old_check_names_is_judge_failed():
    with pytest.raises(L.JudgeFailed):
        L.parse_judge(judge_reply(), L.MOMENT_CHECKS)                  # one_development_two_channels is not a moment check
    assert L.parse_judge(moment_judge_reply(), L.MOMENT_CHECKS)["verdict"] == "LEGAL"


def test_the_variant_judge_is_blind_to_the_builder(tmp_path, day_rows, fake):
    lu = legal_lineup()
    lu["development"], lu["current_because"] = "UNIQUE-DEV", "UNIQUE-WHY"
    j = fake([moment_judge_reply()])
    R.run_day(str(tmp_path), day_rows, NOW, fake([oracle_reply([lu])]), j, llm.Ledger(str(tmp_path / "S.jsonl")),
              variant="same_dev")
    text = (j.prompts[0][0] + j.prompts[0][1]).lower()
    for leak in ("unique-dev", "unique-why", "oracle", "selector", "gpt", "openai", "claude", "pipeline"):
        assert leak not in text, leak


def test_more_than_the_variant_maximum_is_oracle_failed(day_rows):
    many = [legal_lineup()] * 9
    with pytest.raises(L.OracleFailed, match="1-8"):
        L.parse_oracle(oracle_reply(many), by_id(day_rows), max_lineups=8)
    assert len(L.parse_oracle(oracle_reply([legal_lineup()] * 8), by_id(day_rows), 8)["lineups"]) == 8


# ── distinct developments (integrator Q1) ──

def test_grouping_needs_every_lineup_exactly_once():
    assert R.parse_groups(json.dumps({"groups": [{"lineups": [1, 3], "development": "a"},
                                                 {"lineups": [2], "development": "b"}], "reason": "r"}), 3) == \
        [{"lineups": [1, 3], "development": "a"}, {"lineups": [2], "development": "b"}]
    for bad in ("", "{}", json.dumps({"groups": [{"lineups": [1], "development": "a"}], "reason": "r"}),   # 2 missing
                json.dumps({"groups": [{"lineups": [1, 2], "development": "a"}, {"lineups": [2], "development": "b"}],
                            "reason": "r"}),                                                              # 2 twice
                json.dumps({"groups": [{"lineups": ["1", 2], "development": "a"}], "reason": "r"}),
                json.dumps({"groups": [{"lineups": [1, 2], "development": " "}], "reason": "r"})):
        with pytest.raises(R.GroupingFailed):
            R.parse_groups(bad, 2)


def test_distinct_developments_from_a_blind_grouping(tmp_path, day_rows, fake):
    lus = [legal_lineup(), copy.deepcopy(legal_lineup())]
    for k, lu in enumerate(lus):                         # the writer's own words must never reach the grouping
        lu["development"], lu["current_because"] = f"UNIQUE-DEV-{k}", f"UNIQUE-WHY-{k}"
    R.run_day(str(tmp_path), day_rows, NOW, fake([oracle_reply(lus)]), fake([judge_reply(), judge_reply()]),
              llm.Ledger(str(tmp_path / "S.jsonl")))
    g = fake([json.dumps({"groups": [{"lineups": [1, 2], "development": "the weekend fall"}], "reason": "same"})])
    rec = R.group_developments(str(tmp_path), day_rows, NOW, g, llm.Ledger(str(tmp_path / "S.jsonl")))
    day = json.load(open(tmp_path / "DAY.json"))
    assert rec["status"] == "OK" and day["distinct_developments"] == 1 and day["distinct_accepted"] == 1
    assert "UNIQUE" not in g.prompts[0][1] and "oracle" not in g.prompts[0][1].lower()
    bad = fake(["", ""])                                                 # a grouping that never answers: not measured
    R.group_developments(str(tmp_path), day_rows, NOW, bad, llm.Ledger(str(tmp_path / "S.jsonl")))
    assert json.load(open(tmp_path / "DAY.json"))["distinct_developments"] is None


def test_story_first_hard_max_asks_for_disjoint_lineups_and_is_judged_like_the_order(tmp_path, day_rows, fake):
    o, j = fake([oracle_reply()]), fake([judge_reply()])
    d = R.run_day(str(tmp_path), day_rows, NOW, o, j, llm.Ledger(str(tmp_path / "S.jsonl")), variant="same_dev_hard_max")
    assert os.path.exists(tmp_path / "same_dev_hard_max" / "DAY.json")
    assert "up to 8" in o.prompts[0][1] and L.RULES in o.prompts[0][1] and "TARGETS" not in o.prompts[0][1]
    assert j.prompts[0][1] == P.judge_prompt(legal_lineup(), by_id(day_rows), NOW)     # the order's judge, verbatim
    assert d["accepted"] == 1
