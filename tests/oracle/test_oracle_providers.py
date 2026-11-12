"""Law L-x (orchestrator note 02:45): one provider interface, >= 2 interchangeable back-ends per role, the run goes on
when a vendor is down, local Ultron model first, generator and blind judge never the same vendor, no model name
outside the provider config, Heimdall's 90 % tripwire notifies and falls back instead of halting."""
import glob
import os

import pytest

from pipeline.oracle import llm
from pipeline.oracle import providers as PV

PKG = os.path.dirname(PV.__file__)
TOOL = os.path.join(os.path.dirname(os.path.dirname(PKG)), "tools", "backtest_oracle.py")


class Vendor(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.status_code = status


@pytest.fixture
def fake_backends(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(llm, "env_key", lambda name, path=None: "k")
    monkeypatch.setattr(PV, "heimdall_usage", lambda: (10.0, 500.0))
    monkeypatch.delenv("PP_GPU0_LEASE_HELD", raising=False)
    script = {}

    def kind(b, system, user, schema):
        calls.append(b["model"])
        r = script.get(b["model"], "ok")
        if isinstance(r, Exception):
            raise r
        return '{"ok": true}', {"model": b["model"]}, {"tokens_in": max(10, (len(system) + len(user)) // 3),
                                                      "tokens_out": 5, "seconds": 0.1}
    for k in ("ollama", "openai", "anthropic"):
        monkeypatch.setitem(PV._KIND, k, kind)
    return calls, script, llm.Ledger(str(tmp_path / "S.jsonl"))


def test_no_model_or_endpoint_appears_outside_the_provider_config():
    names = {b["model"] for b in PV.BACKENDS.values()} | {b["base_url"] for b in PV.BACKENDS.values() if b.get("base_url")}
    names |= set(PV.BACKENDS)
    for path in glob.glob(os.path.join(PKG, "*.py")) + [TOOL]:
        if os.path.basename(path) == "providers.py":
            continue
        src = open(path, encoding="utf-8").read()
        assert not [n for n in names if n in src], (path, [n for n in names if n in src])


def test_every_role_has_two_vendors_and_starts_on_ultron():
    for role, chain in PV.ROLES.items():
        assert len(chain) >= 2 and len({PV.BACKENDS[b]["vendor"] for b in chain}) >= 2, role
        assert PV.BACKENDS[chain[0]]["vendor"] == "ultron" and PV.BACKENDS[chain[0]].get("gpu0"), role
        assert role in PV.DECIDED_BY


def test_a_vendor_that_is_down_or_out_of_credit_moves_the_role_to_the_next(fake_backends):
    calls, script, ledger = fake_backends
    script["gpt-6.1-sol"] = Vendor(429)                                 # insufficient_quota tonight
    text, raw, row = PV.call("writer", "s", "u", {}, ledger, "t")
    assert row["backend"] == "grok-4.7" and calls == ["gpt-6.1-sol", "grok-4.7"]
    assert row["tried"][0]["skipped"].startswith("local GPU0 model") and "HTTP 429" in row["tried"][1]["error"]


def test_a_non_vendor_error_is_not_swallowed_and_the_spend_guard_is_never_bypassed(fake_backends):
    calls, script, ledger = fake_backends
    script["gpt-6.1-sol"] = ValueError("bad request body")
    with pytest.raises(ValueError):
        PV.call("writer", "s", "u", {}, ledger, "t")
    script["gpt-6.1-sol"] = llm.SpendStop("cap")
    with pytest.raises(llm.SpendStop):
        PV.call("writer", "s", "u", {}, ledger, "t")


def test_the_judge_never_shares_the_writers_vendor(fake_backends):
    calls, script, ledger = fake_backends
    _, _, row = PV.call("judge", "s", "u", {}, ledger, "t", avoid_vendors={"anthropic"})
    assert row["vendor"] != "anthropic" and row["backend"] == "grok-4.7"


def test_local_runs_only_inside_the_gpu0_lease_and_only_once_validated_for_the_role(fake_backends, monkeypatch):
    calls, script, ledger = fake_backends
    assert PV.available("local-gemma3-27b")[0] is False
    monkeypatch.setenv("PP_GPU0_LEASE_HELD", "1")
    _, _, row = PV.call("judge", "s", "u", {}, ledger, "t")                  # lease held, A/B not passed yet
    assert row["backend"] == "claude-fable-5-2" and "not yet validated" in row["tried"][0]["skipped"]
    monkeypatch.setitem(PV.LOCAL_VALIDATED, "judge", True)
    _, _, row = PV.call("judge", "s", "u", {}, ledger, "t")
    assert row["backend"] == "local-gemma3-27b" and row["usd"] == 0.0
    _, _, row = PV.call("judge", "s", "u", {}, ledger, "t", chain=["local-gemma3-27b"])   # the A/B harness path
    assert row["backend"] == "local-gemma3-27b"


def test_heimdall_at_90_percent_notifies_and_falls_back(fake_backends, monkeypatch, tmp_path):
    calls, script, ledger = fake_backends
    monkeypatch.setattr(PV, "heimdall_usage", lambda: (451.0, 500.0))
    chain = ["heimdall-glm-5.3-flash", "grok-4.7"]
    _, _, row = PV.call("judge", "s", "u", {}, ledger, "t", chain=chain, notify_dir=str(tmp_path))
    assert row["backend"] == "grok-4.7" and "HEIMDALL SPEND AT 90%" in row["tried"][0]["skipped"]
    assert open(tmp_path / PV.NOTIFY_FILE).read().startswith("HEIMDALL SPEND AT 90%")


def test_no_backend_answering_is_all_failed_never_an_answer(fake_backends):
    calls, script, ledger = fake_backends
    for b in ("gpt-6.1-sol", "grok-4.7", "deepseek/deepseek-v4.1-flash"):
        script[b] = Vendor(503)
    with pytest.raises(PV.AllBackendsFailed) as e:
        PV.call("writer", "s", "u", {}, ledger, "t")
    assert len(e.value.tried) == 4


def test_spend_is_priced_from_the_config_and_recorded_with_the_backend(fake_backends):
    calls, script, ledger = fake_backends
    PV.call("writer", "s", "u", {}, ledger, "t")
    import json
    row = [json.loads(x) for x in open(ledger.path)][-1]
    assert row["backend"] == "gpt-6.1-sol" and row["vendor"] == "openai"
    assert row["usd"] == llm.cost(PV.BACKENDS["gpt-6.1-sol"]["price"], 10, 5)


def test_a_gateway_that_bills_per_call_is_recorded_at_its_own_figure_and_an_unpriced_one_is_flagged(
        fake_backends, monkeypatch):
    calls, script, ledger = fake_backends
    import json

    def billed(b, system, user, schema):
        return '{"ok": true}', {"model": b["model"]}, {"tokens_in": 10, "tokens_out": 5, "seconds": 0.1,
                                                       "usd_reported": 0.0123}
    monkeypatch.setitem(PV._KIND, "openai", billed)
    _, _, row = PV.call_backend("heimdall-glm-5.3-flash", "s", "u", {}, ledger, "t")
    assert row["usd"] == 0.0123 and row["usd_source"] == "gateway-reported" and "usd_reported" not in row
    _, _, row = PV.call_backend("grok-4.7", "s", "u", {}, ledger, "t")      # a priced back-end keeps the price table
    assert row["usd_source"] == "price table" and row["usd"] == llm.cost(PV.BACKENDS["grok-4.7"]["price"], 10, 5)
    monkeypatch.setitem(PV._KIND, "openai", lambda b, s, u, sc: ('{}', {}, {"tokens_in": 1, "tokens_out": 1,
                                                                             "seconds": 0.1}))
    _, _, row = PV.call_backend("heimdall-qwen3.8-27b", "s", "u", {}, ledger, "t")
    worst = PV.BACKENDS["heimdall-qwen3.8-27b"]["reserve_usd"]
    assert row["usd"] == worst and row["usd_source"] == "unreported: worst case"   # never silently 'free'
    assert ledger.spent() == round(0.0123 + llm.cost(PV.BACKENDS["grok-4.7"]["price"], 10, 5) + worst, 4)
    assert [json.loads(x)["usd_source"] for x in open(ledger.path)] == ["gateway-reported", "price table",
                                                                       "unreported: worst case"]
    assert ledger.in_flight() == 0.0


def test_a_prompt_longer_than_the_local_context_is_never_sent_and_the_role_moves_on(fake_backends, monkeypatch):
    calls, script, ledger = fake_backends
    monkeypatch.setenv("PP_GPU0_LEASE_HELD", "1")
    monkeypatch.setitem(PV.LOCAL_VALIDATED, "writer", True)               # so the context guard is what skips it
    b = PV.BACKENDS["local-gemma3-27b"]
    room = b["num_ctx"] - b["max_tokens"]
    assert llm.est_tokens("s", "x" * (int(room * llm.CHARS_PER_TOKEN_MIN) - 2)) <= room   # the edge: still fits ...
    big = "x" * (int(room * llm.CHARS_PER_TOKEN_MIN) + 2)                                # ... one token over: never sent
    _, _, row = PV.call("writer", "s", big, {}, ledger, "t")
    assert row["backend"] == "gpt-6.1-sol" and "gemma3:27b" not in calls       # the cut prompt was never sent
    assert "> context" in row["tried"][0]["skipped"]
    with pytest.raises(PV.ContextTooLong):
        PV.call_backend("local-gemma3-27b", "s", big, {}, ledger, "t")


def test_the_token_estimate_never_undercounts_the_tokenizers_measured_on_the_stored_prompts():
    for chars_per_token in (1.84, 2.07, 2.93, 3.06):                    # judge (min, max), writer (min, max)
        text = "x" * 100_000
        assert llm.est_tokens(text) >= len(text) / chars_per_token


def test_a_local_reply_that_reached_the_context_limit_is_a_failure_not_an_answer(monkeypatch):
    b = PV.BACKENDS["local-gemma3-27b"]

    class Resp:
        def read(self):
            import json
            return json.dumps({"message": {"content": "{}"}, "prompt_eval_count": b["num_ctx"] - 10,
                               "eval_count": 10}).encode()
    monkeypatch.setattr(PV.urllib.request, "urlopen", lambda req, timeout=None: Resp())
    with pytest.raises(PV.ContextTooLong):
        PV._ollama(b, "s", "u", {})


def test_a_gateway_that_cut_the_prompt_is_caught_and_its_paid_call_still_recorded(fake_backends, monkeypatch):
    calls, script, ledger = fake_backends
    import json
    big = "y" * 60_000

    def cut(b, system, user, schema):
        return '{"ok": true}', {"model": b["model"]}, {"tokens_in": 4_000, "tokens_out": 5, "seconds": 0.1,
                                                       "usd_reported": 0.002}
    monkeypatch.setitem(PV._KIND, "openai", cut)
    with pytest.raises(PV.ContextTooLong, match="input was cut"):
        PV.call_backend("heimdall-glm-5.3-flash", "s", big, {}, ledger, "t")
    assert [json.loads(x)["usd"] for x in open(ledger.path)] == [0.002]            # billed, so recorded


class TooLong(Exception):
    def __init__(self):
        super().__init__("Error code: 400 - This model's maximum context length is 131072 tokens")
        self.status_code = 400


def test_a_context_length_refusal_moves_the_role_to_the_next_backend(fake_backends):
    calls, script, ledger = fake_backends
    script["gpt-6.1-sol"] = TooLong()
    _, _, row = PV.call("writer", "s", "u", {}, ledger, "t")
    assert row["backend"] == "grok-4.7" and "refused the prompt as too long" in row["tried"][1]["skipped"]
    assert ledger.in_flight() == 0.0                                                # the reservation was released


def test_the_heimdall_tripwire_is_checked_on_every_call_not_once_per_batch(fake_backends, monkeypatch):
    calls, script, ledger = fake_backends
    PV.call_backend("heimdall-glm-5.3-flash", "s", "u", {}, ledger, "t")             # 10 of 500: fine
    monkeypatch.setattr(PV, "heimdall_usage", lambda: (460.0, 500.0))
    with pytest.raises(PV.VendorDown, match="HEIMDALL SPEND AT 90%"):
        PV.call_backend("heimdall-glm-5.3-flash", "s", "u", {}, ledger, "t")
    monkeypatch.setattr(PV, "heimdall_usage", lambda: (0.0, 0.0))
    assert PV.available("heimdall-glm-5.3-flash")[0] is False                       # no credits is not 'fine'


def test_a_local_server_error_moves_the_role_on_like_any_vendor_outage(fake_backends, monkeypatch):
    import io
    import urllib.error
    calls, script, ledger = fake_backends
    monkeypatch.setenv("PP_GPU0_LEASE_HELD", "1")
    monkeypatch.setitem(PV.LOCAL_VALIDATED, "judge", True)
    script["gemma3:27b"] = urllib.error.HTTPError("http://127.0.0.1:11434/api/chat", 503, "busy", {}, io.BytesIO())
    _, _, row = PV.call("judge", "s", "u", {}, ledger, "t")
    assert row["backend"] == "claude-fable-5-2" and "503" in row["tried"][0]["error"]
    script["gemma3:27b"] = ConnectionResetError("reset by peer")
    assert PV.call("judge", "s", "u", {}, ledger, "t")[2]["backend"] == "claude-fable-5-2"


def test_a_remote_reply_without_a_prompt_token_count_is_not_trusted(fake_backends, monkeypatch):
    calls, script, ledger = fake_backends
    monkeypatch.setitem(PV._KIND, "openai", lambda b, s, u, sc: ('{}', {}, {"tokens_out": 3, "seconds": 0.1,
                                                                             "usd_reported": 0.001}))
    with pytest.raises(PV.ContextTooLong, match="no prompt-token count"):
        PV.call_backend("heimdall-glm-5.3-flash", "s", "u", {}, ledger, "t")


def test_a_timeout_after_sending_is_charged_at_worst_case_and_a_refusal_is_not(fake_backends):
    calls, script, ledger = fake_backends
    import json
    script["grok-4.7"] = TimeoutError("read timed out")
    with pytest.raises(TimeoutError):
        PV.call_backend("grok-4.7", "s", "u", {}, ledger, "t")
    script["grok-4.7"] = Vendor(429)
    with pytest.raises(Vendor):
        PV.call_backend("grok-4.7", "s", "u", {}, ledger, "t")
    rows = [json.loads(x) for x in open(ledger.path)]
    assert [r["usd_source"] for r in rows] == ["failed after sending: worst case"]       # the 429 was not billed
    assert rows[0]["usd"] > 0 and ledger.in_flight() == 0.0


def test_the_judge_avoids_the_vendor_that_actually_wrote_after_a_failover(fake_backends):
    calls, script, ledger = fake_backends
    script["gpt-6.1-sol"] = Vendor(429)                          # the writer chain fails over: grok writes
    writer, judge = PV.paired_calls(judge_chain=["grok-4.7", "claude-fable-5-2"])
    assert writer("s", "u", {}, ledger, "w")[2]["vendor"] == "xai"
    _, _, row = judge("s", "u", {}, ledger, "j")
    assert row["backend"] == "claude-fable-5-2" and "produced what this role judges" in row["tried"][0]["skipped"]


def test_no_model_id_shape_or_vendor_endpoint_appears_outside_the_provider_config():
    import re
    shapes = re.compile(r"(gpt-\d|claude-[a-z]+-\d|grok-\d|gemma\d|deepseek[-/]|qwen\d|glm-\d|z-ai/|api\.x\.ai|"
                        r"api\.openai|api\.anthropic|heimdallm\.com|11434)")
    for path in glob.glob(os.path.join(PKG, "*.py")) + [TOOL]:
        if os.path.basename(path) == "providers.py":
            continue
        hits = shapes.findall(open(path, encoding="utf-8").read())
        assert not hits, (path, hits)
