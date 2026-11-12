"""One provider interface (law L-x): fallback, circuit breaker, queue-aware backoff, budgets, the spend tripwire,
the reply cache, the local back-end's lease, and no vendor or model name outside providers.json."""
import glob
import json
import os
import re

import pytest

from pipeline.ingest import config, providers, spend
from pipeline.ingest.providers import BackendError, Invalid
import helpers as H


def validate_obj(content):
    try:
        obj = json.loads(content)
    except ValueError as e:
        raise Invalid(str(e))
    if obj != {"ok": True}:
        raise Invalid("not ok")
    return obj


OK = json.dumps({"ok": True})


def test_the_first_back_end_answers():
    a, b = H.FakeBackend("a", [OK]), H.FakeBackend("b", [OK])
    out = H.make_router([a, b]).run("mine", "p", None, validate_obj)
    assert out.backend == "a" and out.obj == {"ok": True} and len(b.calls) == 0


def test_a_dead_back_end_falls_back_and_nothing_is_lost():
    a = H.FakeBackend("a", fn=lambda p: BackendError("network", "connection refused"))
    b = H.FakeBackend("b", [OK])
    out = H.make_router([a, b]).run("mine", "p", None, validate_obj)
    assert out.backend == "b"
    assert len(a.calls) == 3                       # 1 + transport_retries (2)
    assert out.tried[0][0] == "a" and out.tried[0][1] == "failed"


def test_every_back_end_failing_raises_with_each_reason():
    a = H.FakeBackend("a", fn=lambda p: BackendError("http_4xx", "bad request"))
    b = H.FakeBackend("b", fn=lambda p: "not json")
    with pytest.raises(providers.AllBackendsFailed) as e:
        H.make_router([a, b]).run("mine", "p", None, validate_obj)
    assert [t[0] for t in e.value.tried] == ["a", "b"]
    assert len(a.calls) == 1                       # a 4xx is not retried on the same back-end
    assert len(b.calls) == 3                       # an invalid reply is asked again with the reason, 3 attempts


def test_an_invalid_reply_is_asked_again_with_the_reason():
    a = H.FakeBackend("a", ['{"ok": false}', OK])
    out = H.make_router([a]).run("mine", "PROMPT", None, validate_obj)
    assert out.attempt == 2
    assert a.calls[0] == "PROMPT" and "YOUR PREVIOUS REPLY WAS REJECTED: not ok" in a.calls[1]


def test_empty_content_with_length_is_a_failed_call():
    """INGEST-FAIL-04: HTTP 200 with no content (reasoning ate the budget) is never an answer."""
    a = H.FakeBackend("a", fn=lambda p: BackendError("empty", "no content (finish_reason length)"))
    b = H.FakeBackend("b", [OK])
    out = H.make_router([a, b]).run("mine", "p", None, validate_obj)
    assert out.backend == "b"


def test_the_openai_compatible_client_raises_empty_on_length(monkeypatch):
    cfg = {"kind": "openai_compat", "model": "m", "base_url": "http://x", "key_env": "K", "enabled": True,
           "cost_from_usage": True}

    class KR:
        def get(self, name=None, prefix=None):
            return ["k"]
    b = providers.OpenAICompatBackend("x", cfg, KR())
    canned = json.dumps({"model": "m", "choices": [{"message": {"content": "", "reasoning": "..."},
                                                    "finish_reason": "length"}], "usage": {"cost": 0.002}}).encode()
    monkeypatch.setattr(b, "_request", lambda path, req=None, timeout=None: (200, canned, {}, 1.0))
    with pytest.raises(BackendError) as e:
        b.complete("p", None, 100)
    assert e.value.kind == "empty" and e.value.cost_usd == 0.002


def test_the_circuit_opens_after_consecutive_failures_and_the_back_end_is_skipped():
    t = [1000.0]
    a = H.FakeBackend("a", fn=lambda p: BackendError("network", "down"))
    b = H.FakeBackend("b", fn=lambda p: OK)
    r = H.make_router([a, b], clock=lambda: t[0])
    for _ in range(3):
        assert r.run("mine", "p", None, validate_obj).backend == "b"
    calls = len(a.calls)
    out = r.run("mine", "p2", None, validate_obj)
    assert out.backend == "b" and len(a.calls) == calls          # open: not even tried
    assert out.tried[0][1] == "skipped" and "circuit open" in out.tried[0][2]
    t[0] += 301                                                  # half-open: one probe
    a.fn = lambda p: OK
    assert r.run("mine", "p3", None, validate_obj).backend == "a"
    assert r.health["a"].snapshot()["open"] is False


def test_429_pauses_the_back_end_and_honours_retry_after():
    t = [0.0]
    slept = []
    a = H.FakeBackend("a", [BackendError("http_429", "busy", retry_after=0.02), OK])
    cfg = H.router_cfg(["a"])
    r = providers.Router(cfg, keyring=providers.Keyring("/nonexistent"), backends={"a": a}, clock=lambda: t[0],
                         sleep=lambda s: (slept.append(s), t.__setitem__(0, t[0] + s)))
    out = r.run("mine", "p", None, validate_obj)
    assert out.backend == "a" and r.throttle["a"].hits == 1 and slept and sum(slept) >= 0.02


def test_a_daily_budget_refuses_and_the_next_back_end_answers():
    a = H.FakeBackend("a", [OK], cfg={"daily_budget_usd": 0.5})
    b = H.FakeBackend("b", [OK])
    r = H.make_router([a, b])
    r.spend.add("a", 0.6)
    out = r.run("mine", "p", None, validate_obj)
    assert out.backend == "b" and out.tried[0][1] == "skipped" and "budget" in out.tried[0][2]


def test_the_heimdall_tripwire_routes_away_and_never_halts():
    h = H.FakeBackend("h", [OK], cfg={"spend_meter": "heimdall"}, usage_total=95.0)
    b = H.FakeBackend("b", [OK])
    r = H.make_router([h, b])
    changes = []
    m = spend.HeimdallMeter(H.router_cfg(["h"])["heimdall_meter"], h, on_change=lambda s, snap: changes.append(s))
    r.meter = m
    m.measure()                                    # 95 of a 100 cap at 90 %: tripped
    assert m.state() == "tripped" and changes == ["tripped"]
    out = r.run("mine", "p", None, validate_obj)
    assert out.backend == "b" and "heimdall spend tripped" in out.tried[0][2]


def test_an_unmeasured_heimdall_spend_is_never_read_as_below_the_tripwire():
    h = H.FakeBackend("h", [OK], cfg={"spend_meter": "heimdall"}, usage_total=RuntimeError("credits down"))
    b = H.FakeBackend("b", [OK])
    r = H.make_router([h, b])
    r.meter = spend.HeimdallMeter(H.router_cfg(["h"])["heimdall_meter"], h)
    r.meter.measure()
    assert r.meter.state() == "unmeasured"
    assert r.run("mine", "p", None, validate_obj).backend == "b"


def test_the_meter_adds_this_services_spend_since_the_reading():
    h = H.FakeBackend("h", cfg={"spend_meter": "heimdall"}, usage_total=80.0)
    m = spend.HeimdallMeter(H.router_cfg(["h"])["heimdall_meter"], h)
    m.measure()
    assert m.state() == "ok"
    m.add_local(11.0)                               # 80 + 11 >= 90
    assert m.state() == "tripped"


def test_a_validated_reply_is_reused_and_an_invalid_cache_is_asked_again(tmp_path):
    a = H.FakeBackend("a", [OK, OK])
    r = H.make_router([a], cache_dir=str(tmp_path))
    first = r.run("mine", "p", None, validate_obj)
    second = r.run("mine", "p", None, validate_obj)
    assert not first.cached and second.cached and len(a.calls) == 1
    strict = lambda c: (_ for _ in ()).throw(Invalid("validator changed"))   # noqa: E731
    with pytest.raises(providers.AllBackendsFailed):
        r.run("mine", "p", None, strict)            # the cached reply no longer passes: asked again (and fails)
    assert len(a.calls) >= 2 and a.calls[1] == "p"


def test_a_disabled_back_end_with_a_cache_is_not_used(tmp_path):
    a = H.FakeBackend("a", [OK])
    b = H.FakeBackend("b", [OK])
    r = H.make_router([a, b], cache_dir=str(tmp_path))
    assert r.run("mine", "p", None, validate_obj).backend == "a"
    a.cfg["enabled"] = False
    assert r.run("mine", "p", None, validate_obj).backend == "b"


def test_the_local_back_end_refuses_without_the_gpu0_lease():
    cfg = {"kind": "ollama_local", "model": "local-model", "enabled": True}
    b = providers.OllamaLocalBackend("local", cfg, providers.Keyring("/nonexistent"), lease=lambda: False)
    with pytest.raises(BackendError) as e:
        b.complete("p", None, 100)
    assert e.value.kind == "disabled" and "lease" in e.value.detail
    assert not providers.OllamaLocalBackend("local", cfg, providers.Keyring("/nonexistent")).enabled()


def test_keys_never_appear_in_repr_or_errors(tmp_path):
    env = tmp_path / ".env"
    env.write_text("SECRET_KEY=sk-test-123456\nHEIMDALL_API_KEY_2='hk-abc'\nHEIMDALL_API_KEY=hk-def\n")
    kr = providers.Keyring(str(env))
    assert "sk-test" not in repr(kr) and kr.get(prefix="HEIMDALL_API_KEY") == ["hk-abc", "hk-def"]
    b = providers.OpenAICompatBackend("x", {"model": "m", "base_url": "http://127.0.0.1:9", "key_env": "SECRET_KEY",
                                            "timeout_s": 2}, kr)
    with pytest.raises(BackendError) as e:
        b.complete("p", None, 10)
    assert "sk-test" not in str(e.value) and "sk-test" not in repr(b)


def test_the_real_config_has_two_enabled_back_ends_per_role_and_known_kinds():
    cfg = providers.load_config()
    for role, rc in cfg["roles"].items():
        usable = [b for b in rc["chain"] if cfg["backends"][b].get("enabled", True)
                  and cfg["backends"][b]["kind"] != "ollama_local"]
        assert len(usable) >= 2, role
    assert {b["kind"] for b in cfg["backends"].values()} <= set(providers.KINDS)


def test_no_vendor_or_model_name_outside_the_provider_config():
    """Law L-x: roles name back-ends only through providers.json."""
    cfg = providers.load_config()
    names = set()
    for bid, b in cfg["backends"].items():
        names |= {bid, b["model"]}
        if b.get("base_url"):
            names.add(b["base_url"])
    pat = re.compile(r"qwen|claude-|grok-|gemini-|gemma|deepseek|heimdallm\.com|api\.x\.ai|anthropic\.com", re.I)
    for path in glob.glob(os.path.join(config.PKG_DIR, "*.py")) + [os.path.join(config.REPO, "tools", "ingest_watch.py")]:
        if os.path.basename(path) == "providers.py":
            continue                                # the protocol adapters (no model names; see the next check)
        src = open(path).read()
        hits = [n for n in names if n in src] + pat.findall(src)
        assert not hits, f"{os.path.basename(path)} names {hits}"
    src = open(os.path.join(config.PKG_DIR, "providers.py")).read()
    assert not [b["model"] for b in cfg["backends"].values() if b["model"] in src]


def test_a_recovered_back_end_is_not_reopened_by_the_outages_old_failures():
    """Found by test_service: the failure-fraction rule re-read the outage's failures on the first success after the
    breaker closed, so a recovered back-end flapped open for another open_s."""
    t = [0.0]
    h = providers.Health(H.router_cfg(["a"])["health"], clock=lambda: t[0])
    for _ in range(8):
        h.record(False, None, "network")
    assert h.snapshot()["open"]
    t[0] += 301
    assert h.allow() == (True, "half-open probe")
    h.record(True, 1.0, "ok")
    for _ in range(5):
        h.record(True, 1.0, "ok")
        assert h.allow() == (True, "")


def test_a_success_never_trips_the_failure_rules():
    h = providers.Health(dict(H.router_cfg(["a"])["health"], consecutive_failures=99), clock=lambda: 0.0)
    for _ in range(5):
        h.record(False, None, "network")
    for _ in range(5):
        h.record(True, 1.0, "ok")
    assert h.snapshot()["open"] is False


def test_a_runtime_override_moves_a_back_end_and_is_recorded(tmp_path):
    changes = []
    path = tmp_path / "overrides.json"
    ov = providers.Overrides(str(path), on_change=lambda old, new: changes.append(new))
    b = providers.OpenAICompatBackend("gw", {"model": "m", "base_url": "https://gw.example/api/v1"},
                                      providers.Keyring("/nonexistent"))
    b.overrides = ov
    assert b.base == "https://gw.example/api/v1"
    path.write_text(json.dumps({"gw": {"base_url": "http://127.0.0.1:9/api/v1/"}}))
    assert b.base == "http://127.0.0.1:9/api/v1" and changes == [{"gw": {"base_url": "http://127.0.0.1:9/api/v1/"}}]
    os.unlink(path)
    assert b.base == "https://gw.example/api/v1" and changes[-1] == {}
    path.write_text("{not json")
    assert b.base == "https://gw.example/api/v1"            # unreadable = no override, never a crash
