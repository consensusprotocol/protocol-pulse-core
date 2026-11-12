"""One day through the oracle and the judge with scripted replies (pipeline/oracle/run.py): failures are recorded
as failures (never NONE, never a pass), the judge never sees who built a line-up, artefacts are saved."""
import json
import os

from conftest import judge_reply, legal_lineup, oracle_reply

from pipeline.oracle import llm
from pipeline.oracle import run as R

NOW = "2026-11-10T09:31:52+00:00"


def day(tmp_path, rows, oracle, judge, fake):
    o, j = fake(oracle), fake(judge)
    ledger = llm.Ledger(str(tmp_path / "SPEND.jsonl"))
    d = R.run_day(str(tmp_path), rows, NOW, o, j, ledger)
    return d, o, j


def test_an_empty_reply_twice_is_oracle_failed_never_none(tmp_path, day_rows, fake):
    d, o, j = day(tmp_path, day_rows, ["", ""], [], fake)
    rec = json.load(open(tmp_path / "ORACLE.json"))
    assert rec["status"] == "ORACLE_FAILED" and d["availability"].startswith("NOT_MEASURED (ORACLE_FAILED")
    assert d["oracle_verdict"] is None and "NONE" not in d["availability"]
    assert [a["error"][:20] for a in rec["attempts"]] == ["ORACLE_FAILED: empty"] * 2
    assert not j.prompts


def test_an_unknown_id_is_oracle_failed_and_its_retry_names_the_error(tmp_path, day_rows, fake):
    lu = legal_lineup()
    lu["hook"] = ["vidAAAAAAAA:42"]
    d, o, _ = day(tmp_path, day_rows, [oracle_reply([lu])] * 2, [], fake)
    assert d["oracle_status"] == "ORACLE_FAILED"
    assert "vidAAAAAAAA:42" in o.prompts[1][1] and "not valid" in o.prompts[1][1]


def test_malformed_then_valid_uses_the_valid_attempt_and_keeps_the_failure(tmp_path, day_rows, fake):
    d, _, _ = day(tmp_path, day_rows, ['{"verdict": "LINEUPS"', oracle_reply()], [judge_reply()], fake)
    rec = json.load(open(tmp_path / "ORACLE.json"))
    assert rec["status"] == "OK" and rec["attempt_used"] == 2 and rec["attempts"][0]["error"].startswith("ORACLE_FAILED")
    assert d["availability"] == "AVAILABLE" and d["lineups"][0]["accepted"] is True
    assert os.path.exists(tmp_path / "oracle_attempt1_raw.json") and os.path.exists(tmp_path / "JUDGE_L1.json")


def test_an_altcoin_lineup_is_never_accepted_even_if_a_judge_would_call_it_legal(tmp_path, day_rows, fake):
    lu = legal_lineup()
    lu["clips"][2] = ["vidCCCCCCCC:11", "vidCCCCCCCC:12"]                # Ethereum smuggled in
    d, o, j = day(tmp_path, day_rows, [oracle_reply([lu])] * 2, [judge_reply()] * 2, fake)
    assert d["availability"].startswith("NOT_AVAILABLE") and d["lineups"][0]["accepted"] is False
    assert any("altcoin" in v for v in d["lineups"][0]["violations"])
    assert not j.prompts                                                  # structurally illegal: never judged
    assert "Every line-up you returned breaks a rule" in o.prompts[1][1]


def test_none_is_recorded_as_none_with_its_reason(tmp_path, day_rows, fake):
    d, _, j = day(tmp_path, day_rows, [oracle_reply([], "NONE", "only one channel per development")], [], fake)
    assert d["availability"] == "NONE (oracle)" and d["none_reason"] == "only one channel per development"
    assert not j.prompts


def test_a_judge_that_never_answers_whole_is_not_measured_never_available(tmp_path, day_rows, fake):
    d, _, j = day(tmp_path, day_rows, [oracle_reply()], ["", judge_reply("LEGAL", false=("current",))], fake)
    assert d["lineups"][0]["judge"]["status"] == "JUDGE_FAILED" and d["lineups"][0]["accepted"] is False
    assert d["availability"].startswith("NOT_MEASURED (JUDGE_FAILED") and len(j.prompts) == 2


def test_an_illegal_verdict_is_not_available(tmp_path, day_rows, fake):
    d, _, _ = day(tmp_path, day_rows, [oracle_reply()], [judge_reply("ILLEGAL", false=("current",))], fake)
    assert d["availability"] == "NOT_AVAILABLE (the blind judge said every checked line-up fails our rules)"
    assert d["lineups"][0]["judge"]["failed"] == ["current"]


def test_an_api_error_and_the_spend_guard_are_recorded_attempts(tmp_path, day_rows, fake):
    d, _, _ = day(tmp_path, day_rows, [RuntimeError("HTTP 500"), llm.SpendStop("cap")], [], fake)
    rec = json.load(open(tmp_path / "ORACLE.json"))
    assert rec["status"] == "ORACLE_FAILED" and rec["spend_stop"] is True
    assert "spend guard" in d["availability"] and rec["attempts"][0]["error"].startswith("RuntimeError")


def test_the_judge_is_blind_to_the_builder_and_its_rationale(tmp_path, day_rows, fake):
    lu = legal_lineup()
    lu["development"] = "UNIQUE-DEVELOPMENT-TEXT"
    lu["current_because"] = "UNIQUE-RATIONALE-TEXT"
    _, _, j = day(tmp_path, day_rows, [oracle_reply([lu])], [judge_reply()], fake)
    system, user = j.prompts[0]
    text = (system + user).lower()
    for leak in ("unique-development-text", "unique-rationale-text", "oracle", "selector", "gpt", "openai", "claude",
                 "pipeline", "built by", "editorial_select"):
        assert leak not in text, leak
    assert "vidAAAAAAAA:0" in user and "Bitcoin fell below $74,000" in user


def test_the_oracle_sees_only_statements_and_rules(tmp_path, day_rows, fake):
    _, o, _ = day(tmp_path, day_rows, [oracle_reply()], [judge_reply()], fake)
    user = o.prompts[0][1]
    for leak in ("layout_eligible", "transcript_sha256", "has_chyron", "TOPIC_SELECTION", "candidate story",
                 "coverage_qualified", "producible", "decision"):
        assert leak not in user, leak
    assert "vidCCCCCCCC:12 | 114.6-121.0 | Ethereum fell even harder" in user


def test_a_sentence_longer_than_the_clip_budget_is_not_shown(tmp_path, day_rows, fake):
    long = dict(day_rows[2], id="vidAAAAAAAA:3", sentence_index=3, start_s=30.1, end_s=90.0, duration_s=59.9)
    d, o, _ = day(tmp_path, day_rows + [long], [oracle_reply()], [judge_reply()], fake)
    assert "vidAAAAAAAA:3" not in o.prompts[0][1] and d["rows_hidden_longer_than_clip_budget"] == 1


def test_a_failed_reask_after_all_lineups_failed_the_checks_is_not_measured_never_not_available(tmp_path, day_rows,
                                                                                                fake):
    lu = legal_lineup()
    lu["clips"][2] = ["vidCCCCCCCC:11", "vidCCCCCCCC:12"]                # Ethereum: every line-up fails a check
    d, o, j = day(tmp_path, day_rows, [oracle_reply([lu]), RuntimeError("HTTP 503 after the re-ask")], [], fake)
    rec = json.load(open(tmp_path / "ORACLE.json"))
    assert rec["status"] == "OK" and rec["attempt_used"] == 1 and "503" in rec["attempts"][1]["error"]
    assert d["availability"].startswith("NOT_MEASURED (re-ask not answered") and not j.prompts


def test_a_reask_that_never_happened_because_a_schema_retry_used_its_attempt_is_not_measured(tmp_path, day_rows,
                                                                                               fake):
    lu = legal_lineup()
    lu["clips"][2] = ["vidCCCCCCCC:11", "vidCCCCCCCC:12"]                # every line-up fails a check
    d, o, _ = day(tmp_path, day_rows, ['{"verdict": "LINEUPS"', oracle_reply([lu])], [], fake)
    rec = json.load(open(tmp_path / "ORACLE.json"))
    assert rec["attempt_used"] == 2 and rec["reask_answered"] is False and len(o.prompts) == 2
    assert d["availability"].startswith("NOT_MEASURED (re-ask not answered")      # audit round 2, F5


def test_a_rerun_archives_every_derived_file_and_a_stale_one_is_never_fresh(tmp_path, day_rows, fake):
    day(tmp_path, day_rows, [oracle_reply()], [judge_reply()], fake)
    R.group_developments(str(tmp_path), day_rows, NOW, fake([]), llm.Ledger(str(tmp_path / "S.jsonl")))
    assert R.fresh(str(tmp_path), "GROUPS.json")                          # stamped with this ORACLE.json
    for name in ("WITNESS.json", "SCORE.json", "witness_L1_prompt.txt"):
        (tmp_path / name).write_text("{}")
    day(tmp_path, day_rows, [oracle_reply([legal_lineup(), legal_lineup()])], [judge_reply()] * 2, fake)
    moved = sorted(os.listdir(tmp_path / "previous_1"))
    assert {"GROUPS.json", "WITNESS.json", "SCORE.json", "witness_L1_prompt.txt", "ORACLE.json"} <= set(moved)
    assert not os.path.exists(tmp_path / "GROUPS.json")
    stale = json.load(open(tmp_path / "previous_1" / "GROUPS.json"))
    (tmp_path / "GROUPS.json").write_text(json.dumps(stale))              # an old file put back by hand
    assert not R.fresh(str(tmp_path), "GROUPS.json")                      # its stamp names the old ORACLE.json
