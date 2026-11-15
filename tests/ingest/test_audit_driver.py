"""Ruling 107 (2) on pp-ingest's audit driver (tests/ingest/xllm_audit.py), in force for batch 3 by ruling 108: the
package is the diff, two Heimdall families review it, the audit is capped before any call, every review's cost is
booked (an abandoned one at the model's own rate) to COST.json and to the ledger ruling 108's batch line reads. No test
here reaches the network: urlopen and the back-end factory refuse unless a test hands its own fake."""
import json
import os
import sys
import urllib.request

import pytest

import xllm_audit as XA
from pipeline.ingest import batch, config, providers


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("a driver test reached the network")
    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    monkeypatch.setattr(XA.providers, "make_backend", refuse)
    monkeypatch.setattr(XA.providers, "Keyring", lambda path: None)        # the key file is never opened here


def fake_git(monkeypatch, diff="diff --git a/pipeline/ingest/x.py b/pipeline/ingest/x.py\n+the new line\n",
             numstat="10\t5\tpipeline/ingest/x.py\n"):
    def out(cmd, cwd=None, text=None):
        if cmd[:2] == ["git", "rev-parse"]:
            return "abc1234\n"
        if cmd[:3] == ["git", "diff", "--numstat"]:
            return numstat
        if cmd[:2] == ["git", "diff"]:
            return diff
        raise AssertionError(cmd)
    monkeypatch.setattr(XA.subprocess, "check_output", out)


def test_the_package_is_the_diff_and_its_context_never_the_whole_files(monkeypatch, tmp_path):
    fake_git(monkeypatch)
    ctx = tmp_path / "CONTEXT.md"
    ctx.write_text("the orders this change answers")
    pkg = XA.package("base0", str(ctx))
    assert "+the new line" in pkg and "the orders this change answers" in pkg and "git diff base0" in pkg
    assert "### File:" not in pkg and "WHAT THIS FEATURE DOES" not in pkg     # no whole file, no design document
    assert XA.changed_lines("base0") == 15
    fake_git(monkeypatch, diff=" \n")
    with pytest.raises(SystemExit, match="nothing to review"):
        XA.package("base0")


def test_the_reviewers_are_two_heimdall_families_and_a_third_only_by_name():
    assert XA.chosen(None) == (["heimdall_qwen", "heimdall_glm"], {})
    assert XA.chosen({"heimdall_muse"})[0] == ["heimdall_muse"]
    run, skipped = XA.chosen({"grok", "heimdall_glm"})                         # pp-ingest's freeze holds
    assert run == ["heimdall_glm"] and "spend freeze" in skipped["grok"]
    with pytest.raises(SystemExit):
        XA.chosen({"nobody"})


class Fake:
    def __init__(self, rid):
        self.rid = rid

    def complete(self, prompt, schema, max_tokens):
        if self.rid == "heimdall_glm":
            raise providers.BackendError("timeout", "read timed out")          # abandoned: no cost reported
        return providers.Reply("P0: none", "m", "p", 1.0, {"prompt_tokens": 9000, "completion_tokens": 900}, 0.002,
                               "usage.cost", "stop")


def run_main(monkeypatch, out, *extra, cycle=1):
    monkeypatch.setattr(sys, "argv", ["xllm_audit.py", "--cycle", str(cycle), "--base", "base0", "--out", str(out)] +
                        list(extra))
    XA.main()


def test_a_cycle_that_could_pass_the_cap_is_refused_before_any_call(monkeypatch, tmp_path):
    fake_git(monkeypatch)                                                     # 15 changed lines: the $0.30 cap
    monkeypatch.setattr(XA, "_rates", lambda root=None: {"heimdall_qwen": (1e-5, 30), "heimdall_glm": (1e-5, 30)})
    (tmp_path / "audit").mkdir()
    (tmp_path / "audit" / "COST.json").write_text(json.dumps({"total_usd": 0.29, "cycles": {}}))
    with pytest.raises(SystemExit, match=r"REFUSED: this audit has spent \$0.2900 of its \$0.30 cap"):
        run_main(monkeypatch, tmp_path / "audit" / "c2")                     # make_backend refuses: no call was made
    assert not (tmp_path / "audit" / "c2" / "results.json").exists()


def test_every_review_is_booked_and_the_batch_line_reads_the_same_dollars(monkeypatch, tmp_path):
    fake_git(monkeypatch)
    monkeypatch.setattr(XA, "_rates", lambda root=None: {"heimdall_qwen": (2e-7, 30), "heimdall_glm": (4e-8, 31)})
    monkeypatch.setattr(XA.providers, "make_backend", lambda rid, cfg, kr: Fake(rid))
    led = config.paths()["audit_spend"]
    if os.path.exists(led):
        os.remove(led)
    run_main(monkeypatch, tmp_path / "audit" / "c1")
    cost = json.loads((tmp_path / "audit" / "COST.json").read_text())
    rev = cost["cycles"]["c1"]["reviews"]
    assert rev["heimdall_qwen"] == {"usd": 0.002, "basis": "reported"}
    assert rev["heimdall_glm"]["usd"] == pytest.approx(4e-8 * 9000)           # its own rate x the prompt the other
    assert rev["heimdall_glm"]["basis"].startswith("abandoned: the model's own rate (31 reported reviews) x 9000")
    assert cost["total_usd"] == pytest.approx(0.002 + 4e-8 * 9000) and cost["cap_usd"] == 0.30
    usd, n, bad, booked = batch.audit_spend(led, 0, 4e9)                      # ruling 108's line: the same dollars
    assert (round(usd, 6), n, bad) == (round(cost["total_usd"], 6), 2, 0)
    assert booked == pytest.approx(4e-8 * 9000)                                # glm's, at its own rate
    (tmp_path / "audit" / "C1_CONSENSUS.md").write_text("consensus")
    run_main(monkeypatch, tmp_path / "audit" / "c2", "--c1", str(tmp_path / "audit" / "c1"), "--consensus",
             str(tmp_path / "audit" / "C1_CONSENSUS.md"), cycle=2)          # cycle 2 adds to the same audit
    cost = json.loads((tmp_path / "audit" / "COST.json").read_text())
    g2 = cost["cycles"]["c2"]["reviews"]["heimdall_glm"]                       # its own cycle 2 prompt (its own c1
    assert g2["usd"] > 0 and g2["basis"].startswith("abandoned: the model's own rate")   # review in it)
    assert set(cost["cycles"]) == {"c1", "c2"} and cost["total_usd"] == pytest.approx(
        0.002 + 4e-8 * 9000 + 0.002 + g2["usd"], abs=2e-6)                       # COST.json rounds to 6 places
    run_main(monkeypatch, tmp_path / "audit" / "c1", "--only", "heimdall_qwen")   # a leg run again costs again
    cost = json.loads((tmp_path / "audit" / "COST.json").read_text())
    assert len(cost["cycles"]["c1"]["reviews"]) == 3 and cost["total_usd"] == pytest.approx(
        3 * 0.002 + 4e-8 * 9000 + g2["usd"], abs=2e-6)


def test_an_abandoned_review_is_at_the_list_price_of_its_prompt_until_3_reported_reviews():
    booked = XA.book({"heimdall_qwen": {"cost_usd": 0.001, "usage": {"prompt_tokens": 9000}}},
                     {"heimdall_glm": "timeout"}, {"heimdall_glm": {"kind": "timeout", "cost_usd": None}},
                     {"heimdall_glm": "x" * 27000, "heimdall_qwen": "x" * 27000}, {"heimdall_glm": (4e-8, 2)})
    model = XA.REVIEWERS["heimdall_glm"]["model"]
    price = [b["price"]["in_per_mtok"] for b in providers.load_config()["backends"].values() if b.get("model") == model]
    assert booked["heimdall_glm"]["usd"] == pytest.approx(price[0] / 1e6 * 9000)
    assert "the list price of the prompt (fewer than 3 reported reviews)" in booked["heimdall_glm"]["basis"]
    failed = XA.book({}, {"heimdall_glm": "server"}, {"heimdall_glm": {"kind": "server", "cost_usd": 0.0004}}, {}, {})
    assert failed["heimdall_glm"] == {"usd": 0.0004, "basis": "reported (failed: server)"}


def test_the_caps_estimate_is_a_worst_case_the_whole_reply_budget_at_list_price():
    """Audit b108 c1: qwen's reported $0.009 passed the doubled own-rate guess ($0.006: a long reply). The check now
    holds each reviewer's prompt and whole reply budget at its model's list price."""
    prompt = "x" * 96929
    est = XA.estimate(lambda rid: prompt, None, {"heimdall_qwen": (9.6e-8, 33), "heimdall_glm": (4e-8, 31)})
    floor = sum((len(prompt) / 3.0 * XA._price(rid)["in_per_mtok"] + XA.max_out(XA.REVIEWERS[rid]) *
                 XA._price(rid)["out_per_mtok"]) / 1e6 for rid in XA.DEFAULT)
    assert est >= floor and est >= 0.009 + 0.001                       # above the reported cycle 1 of b108


def test_a_review_cut_off_in_flight_is_booked_and_a_quick_failure_says_it_is_not():
    """b108 c1: glm's connection was dropped after 420 s and the record said 'failed before any cost'. A review cut
    off after 30 s in flight with no answer is booked at the model's own rate; a quick or answered failure says it is
    not booked."""
    ok = {"heimdall_qwen": {"cost_usd": 0.001, "usage": {"prompt_tokens": 9000}}}
    cut = XA.book(ok, {"heimdall_glm": "x"}, {"heimdall_glm": {"kind": "network", "cost_usd": None, "seconds": 420.3,
                                                               "http_status": None}},
                  {"heimdall_qwen": "x" * 27000, "heimdall_glm": "x" * 27000}, {"heimdall_glm": (4e-8, 31)})
    assert cut["heimdall_glm"]["usd"] == pytest.approx(4e-8 * 9000)
    assert cut["heimdall_glm"]["basis"].startswith("cut off after 420.3 s in flight (network): the model's own rate")
    for ec in ({"kind": "network", "seconds": 0.2, "http_status": None},
               {"kind": "server", "seconds": 60.0, "http_status": 502}):
        quick = XA.book(ok, {"heimdall_glm": "x"}, {"heimdall_glm": dict(ec, cost_usd=None)}, {},
                        {"heimdall_glm": (4e-8, 31)})
        assert quick["heimdall_glm"]["usd"] == 0.0 and quick["heimdall_glm"]["basis"].endswith(": not booked")


def test_an_abandoned_reviews_prompt_is_its_own_at_the_measured_tokens_per_character():
    """Audit b108 c2: cycle 2 prompts differ by reviewer (each carries its own cycle 1 review), so an abandoned review
    is priced on ITS prompt, at the tokens per character measured on the reviews that answered."""
    ok = {"heimdall_qwen": {"cost_usd": 0.001, "usage": {"prompt_tokens": 9000}}}
    b = XA.book(ok, {"heimdall_glm": "x"}, {"heimdall_glm": {"kind": "timeout", "cost_usd": None}},
                {"heimdall_qwen": "x" * 36000, "heimdall_glm": "x" * 48000}, {"heimdall_glm": (4e-8, 31)})
    assert b["heimdall_glm"]["usd"] == pytest.approx(4e-8 * 48000 * 9000 / 36000)      # 12,000 tokens
    assert "x 12000 prompt tokens" in b["heimdall_glm"]["basis"]
