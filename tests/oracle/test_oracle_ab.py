"""The A/B harness (law L-x): a reply that cannot be parsed is a failure, never an agreement; a must-fail item is
caught only by ILLEGAL; a back-end of the writer's vendor is never asked; dollars are per call."""
import json

from conftest import judge_reply
from pipeline.oracle import ab as AB
from pipeline.oracle import lineup as L
from pipeline.oracle import llm
from pipeline.oracle import providers as PV


def _judge(verdict):
    return judge_reply(verdict, () if verdict == "LEGAL" else (L.JUDGE_CHECKS[0],))


def test_run_role_scores_agreement_failures_must_fail_and_skips_the_writers_vendor(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "env_key", lambda name, path=None: "k")
    monkeypatch.setattr(PV, "heimdall_usage", lambda: (10.0, 500.0))
    replies = {"u1": _judge("LEGAL"), "u2": "not json", "u3": _judge("LEGAL"), "u4": _judge("ILLEGAL")}

    def fake(b, system, user, schema):                  # keyed by prompt: items run in parallel, in any order
        return replies[user], {"model": b["model"]}, {"tokens_in": 100, "tokens_out": 50, "seconds": 2.0,
                                                      "usd_reported": 0.001}
    monkeypatch.setitem(PV._KIND, "openai", fake)
    swap = {"checks": L.JUDGE_CHECKS, "must_fail_on": L.JUDGE_CHECKS[0], "meta": {"base_lineup": 1}}
    items = [("a/L1", "s", "u1", "LEGAL", L.JUDGE_CHECKS), ("a/L2", "s", "u2", "LEGAL", L.JUDGE_CHECKS),
             ("a/swap_hard", "s", "u3", "ILLEGAL", swap), ("b/swap_hard", "s", "u4", "ILLEGAL", swap)]
    ledger = llm.Ledger(str(tmp_path / "S.jsonl"))
    res = AB.run_role("judge", items, ["heimdall-glm-5.3-flash", "grok-4.7"], ledger, str(tmp_path), {"xai"},
                      parallel=4)
    h = res["heimdall-glm-5.3-flash"]
    assert (h["items"], h["failed"], h["agree"]) == (4, 1, 2)          # the unparseable reply is no agreement
    assert (h["must_fail_items"], h["must_fail_caught"]) == (2, 1)     # LEGAL on a swapped clip is a miss
    assert (h["more_lenient"], h["stricter"]) == (1, 0)                # ... and is counted as the dangerous error
    assert h["usd"] == 0.004 and h["usd_source"] == ["gateway-reported"] and h["median_s"] == 2.0
    assert "produced what this role judges" in res["grok-4.7"]["skipped"]
    saved = json.load(open(tmp_path / "AB_judge.json"))
    rows = saved["results"]["heimdall-glm-5.3-flash"]["rows"]
    assert saved["items"] == 4 and [r["item"] for r in rows] == [x[0] for x in items]     # item order kept
    assert rows[1]["status"] == "FAILED" and rows[1]["usd"] == 0.001                     # a paid failure is still paid


def test_once_the_spend_guard_stops_one_call_no_further_item_is_sent(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "env_key", lambda name, path=None: "k")
    sent = []

    def fake(b, system, user, schema):
        sent.append(user)
        return _judge("LEGAL"), {"model": b["model"]}, {"tokens_in": 10, "tokens_out": 10, "seconds": 1.0}
    monkeypatch.setitem(PV._KIND, "openai", fake)
    ledger = llm.Ledger(str(tmp_path / "S.jsonl"), cap=0.0)          # grok is priced: its first reservation stops
    items = [(f"a/L{k}", "s", f"u{k}", "LEGAL", L.JUDGE_CHECKS) for k in range(1, 6)]
    res = AB.run_role("judge", items, ["grok-4.7"], ledger, str(tmp_path), {"openai"}, parallel=1)
    g = res["grok-4.7"]
    assert sent == [] and (g["measured"], g["not_sent"], g["failed"]) == (0, 5, 0) and g["agree"] == 0
    assert "SpendStop" in g["rows"][0]["error"] and all("spend guard" in r["error"] for r in g["rows"][1:])


def test_grouping_reference_is_renumbered_to_the_prompts_numbering():
    ref = [{"lineups": [2, 5]}, {"lineups": [7]}]
    assert AB._renumber(ref) == [{"lineups": [1, 2]}, {"lineups": [3]}]
    assert AB._agree("grouping", [{"lineups": [3]}, {"lineups": [2, 1]}], ref)
    assert not AB._agree("grouping", [{"lineups": [1]}, {"lineups": [2, 3]}], ref)


def test_guard_stopped_items_are_not_measured_and_a_rerun_merges_per_item(tmp_path):
    ok = {"status": "OK", "agree": True, "verdict": "ILLEGAL", "expected": "ILLEGAL", "seconds": 3.0, "usd": 0.1}
    first = {"results": {"b": {"rows": [dict(ok, item="r/L1", verdict="LEGAL", expected="LEGAL"),
                                        dict(ok, item="r/mustfail", usd=0.4),          # a withdrawn first swap
                                        {"item": "r/swap_hard", "status": "FAILED", "usd": 0.0,
                                         "error": "SpendStop: spend guard: 59.0 spent > cap 60.00 USD"},
                                        {"item": "s/L1", "status": "FAILED", "error": "not sent: the spend guard was reached"},
                                        {"item": "s/L2", "status": "FAILED", "seconds": 9.0, "usd": 0.2,
                                         "error": "JudgeFailed: not JSON"}]}}}
    second = {"results": {"b": {"rows": [dict(ok, item="r/swap_hard"), dict(ok, item="s/L1", verdict="LEGAL",
                                                                          expected="LEGAL", usd=0.3)]}}}
    paths = []
    for k, d in enumerate((first, second)):
        paths.append(str(tmp_path / f"AB_judge_{k}.json"))
        json.dump(d, open(paths[-1], "w"))
    one = AB.summarize([r for r in first["results"]["b"]["rows"] if not r["item"].endswith(AB.WITHDRAWN)])
    assert (one["measured"], one["not_sent"], one["failed"]) == (1, 2, 1)       # the guard is not a failure
    m = AB.merge(paths)["b"]
    assert (m["items"], m["measured"], m["not_sent"], m["failed"]) == (4, 3, 0, 1)
    assert (m["must_fail_caught"], m["must_fail_measured"]) == (1, 1) and m["agree"] == 3
    assert m["withdrawn"] == 1                                                    # never counted as a result ...
    assert m["usd"] == round(0.1 + 0.4 + 0.2 + 0.1 + 0.3, 6) and m["calls_paid"] == 5   # ... but it was paid


def test_a_swap_counts_as_caught_only_when_the_judge_fails_it_on_the_swapped_rule():
    arg = {"checks": L.JUDGE_CHECKS, "must_fail_on": "one_development_two_channels", "meta": {}}
    on_rule = L.parse_judge(judge_reply("ILLEGAL", ("one_development_two_channels",)))
    wrong_reason = L.parse_judge(judge_reply("ILLEGAL", ("enough_for_60_70_s",)))
    assert AB._agree("judge", on_rule, "ILLEGAL", arg)
    assert not AB._agree("judge", wrong_reason, "ILLEGAL", arg)          # audit F5: right verdict, wrong reason
    assert AB._agree("judge", wrong_reason, "ILLEGAL", L.JUDGE_CHECKS)   # a recorded item compares the verdict only


def test_every_finished_item_is_saved_and_a_stopped_batch_reads_as_partial(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "env_key", lambda name, path=None: "k")
    monkeypatch.setattr(PV, "heimdall_usage", lambda: (10.0, 500.0))
    seen = []

    def fake(b, system, user, schema):
        if seen:                                       # by the second call the first item is already on disk
            saved = json.load(open(tmp_path / "AB_judge.json"))
            assert saved["complete"] is False and saved["rows_done"] == len(seen)
        seen.append(user)
        return _judge("LEGAL"), {"model": b["model"]}, {"tokens_in": 10, "tokens_out": 5, "seconds": 1.0,
                                                       "usd_reported": 0.0}
    monkeypatch.setitem(PV._KIND, "openai", fake)
    items = [(f"a/L{k}", "s", f"u{k}", "LEGAL", L.JUDGE_CHECKS) for k in range(1, 4)]
    AB.run_role("judge", items, ["heimdall-glm-5.3-flash"], llm.Ledger(str(tmp_path / "S.jsonl")), str(tmp_path),
                {"openai"}, parallel=1)
    final = json.load(open(tmp_path / "AB_judge.json"))
    assert final["complete"] is True and final["rows_done"] == final["rows_planned"] == 3
    part = dict(final, complete=False)
    json.dump(part, open(tmp_path / "AB_partial.json", "w"))
    assert AB.merge([str(tmp_path / "AB_partial.json")])["heimdall-glm-5.3-flash"]["partial"] is True


def test_two_samples_of_one_item_combine_by_the_worst_whatever_their_order(tmp_path):
    swap = {"item": "a/swap_hard", "status": "OK", "expected": "ILLEGAL", "reference": "ILLEGAL", "seconds": 1.0,
            "usd": 0.001}
    caught = dict(swap, verdict="ILLEGAL", agree=True, failed_checks=["one_development_two_channels"])
    passed = dict(swap, verdict="LEGAL", agree=False, failed_checks=[])
    results = []
    for first, second in ((caught, passed), (passed, caught)):
        paths = []
        for k, row in enumerate((first, second)):
            paths.append(str(tmp_path / f"{len(results)}_{k}.json"))
            json.dump({"results": {"b": {"rows": [row]}}}, open(paths[-1], "w"))
        results.append(AB.merge(paths)["b"])
    for m in results:                                    # one LEGAL sample makes the item lenient, never caught
        assert (m["measured"], m["must_fail_caught"], m["more_lenient"]) == (1, 0, 1)
        assert (m["sampled_twice"], m["samples_disagree"]) == (1, 1) and m["calls_paid"] == 2
