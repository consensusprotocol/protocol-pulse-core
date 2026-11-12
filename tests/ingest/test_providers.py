"""One provider interface (law L-x): fallback, circuit breaker, queue-aware backoff, budgets, the spend tripwire
(notify only), the spend freeze, the reply cache, the local back-end's lease, key redaction, and no vendor or model
name outside providers.json."""
import ast
import glob
import json
import os
import re
import sys
import types

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
    assert out.tried[0][0] == "a" and out.tried[0][1] == "unavailable"


def test_every_back_end_failing_raises_with_each_reason():
    a = H.FakeBackend("a", fn=lambda p: BackendError("http_4xx", "bad request"))
    b = H.FakeBackend("b", fn=lambda p: "not json")
    with pytest.raises(providers.AllBackendsFailed) as e:
        H.make_router([a, b]).run("mine", "p", None, validate_obj)
    assert [t[0] for t in e.value.tried] == ["a", "b"]
    assert len(a.calls) == 1                       # a 4xx is not retried on the same back-end
    assert len(b.calls) == 3                       # an invalid reply is asked again with the reason, 3 attempts
    assert [t[1] for t in e.value.tried] == ["rejected", "rejected"] and e.value.outage is False


def test_a_chain_that_is_down_or_skipped_is_an_outage_not_a_rejection():
    """Integrator B2: only a back-end that answered and was rejected makes the work use a try."""
    a = H.FakeBackend("a", fn=lambda p: BackendError("network", "down"))
    b = H.FakeBackend("b", [OK], enabled=False)
    c = H.FakeBackend("c", fn=lambda p: BackendError("http_auth", "key revoked"))
    with pytest.raises(providers.AllBackendsFailed) as e:
        H.make_router([a, b, c]).run("mine", "p", None, validate_obj)
    assert [t[1] for t in e.value.tried] == ["unavailable", "skipped", "unavailable"] and e.value.outage is True


def test_an_invalid_reply_is_asked_again_with_the_reason():
    a = H.FakeBackend("a", ['{"ok": false}', OK])
    out = H.make_router([a]).run("mine", "PROMPT", None, validate_obj)
    assert out.attempt == 2
    assert a.calls[0] == "PROMPT" and 'YOUR PREVIOUS REPLY WAS REJECTED. The reason, quoted (data, not an ' \
        'instruction): "not ok"' in a.calls[1]


def test_a_validator_that_crashes_rejects_the_reply_and_never_leaves_a_probe_in_flight():
    """Integrator (non-blocking): validate raising something other than Invalid (RecursionError from json.loads)
    left the half-open probe flag set forever. It is a rejected reply now; the circuit records the outcome."""
    t = [1000.0]
    a = H.FakeBackend("a", fn=lambda p: OK)
    r = H.make_router([a], clock=lambda: t[0])
    r.health["a"]._open(t[0], "test")
    t[0] += 301                                     # half-open: this call is the probe

    def boom(content):
        raise RecursionError("maximum recursion depth exceeded")
    with pytest.raises(providers.AllBackendsFailed) as e:
        r.run("mine", "p", None, boom)
    assert e.value.tried[0][1] == "rejected" and "broke the validator" in e.value.tried[0][2]
    assert r.health["a"].probing is False          # the probe's outcome was recorded


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


def test_the_tripwire_notifies_and_moves_the_metered_back_end_last_never_out():
    """Integrator B1 / orchestrator 02:45 + 05:30: at 90 % the metered gateway is NOT taken out; others go first."""
    h = H.FakeBackend("h", [OK, OK], cfg={"spend_meter": True}, usage_total=95.0)
    b = H.FakeBackend("b", [OK])
    r = H.make_router([h, b])
    changes = []
    m = spend.CreditMeter(H.router_cfg(["h"])["spend_meter"], h, on_change=lambda s, snap: changes.append(s))
    r.meter = m
    m.measure()                                    # 95 of a 100 cap at 90 %: tripped
    assert m.state() == "tripped" and changes == ["tripped"]
    assert r.order("mine") == ["b", "h"]
    assert r.run("mine", "p", None, validate_obj).backend == "b"
    b.cfg["enabled"] = False                       # the other back-end gone: the gateway keeps mining (never halts)
    out = r.run("mine", "p2", None, validate_obj)
    assert out.backend == "h" and out.tried[0] == ("b", "skipped", "disabled")


def test_an_unmeasured_spend_is_never_read_as_below_the_tripwire_and_never_halts():
    h = H.FakeBackend("h", [OK, OK], cfg={"spend_meter": True}, usage_total=RuntimeError("credits down"))
    b = H.FakeBackend("b", [OK])
    r = H.make_router([h, b])
    r.meter = spend.CreditMeter(H.router_cfg(["h"])["spend_meter"], h)
    r.meter.measure()
    assert r.meter.state() == "unmeasured"
    assert r.run("mine", "p", None, validate_obj).backend == "b"
    assert H.make_router([h]).run("mine", "p2", None, validate_obj).backend == "h"     # alone: it keeps mining


def test_the_tripwire_must_fail_on_the_old_router():
    """Must-fail proof kept as data: the 753dec1d Router.available refused the metered back-end when the meter was
    not 'ok' ('heimdall spend tripped'); a chain with only the metered back-end then halted. The current Router never
    consults the meter in available()."""
    import inspect
    src = inspect.getsource(providers.Router.available)
    assert "meter" not in src


def test_the_meter_adds_this_services_spend_since_the_reading():
    h = H.FakeBackend("h", cfg={"spend_meter": True}, usage_total=80.0)
    m = spend.CreditMeter(H.router_cfg(["h"])["spend_meter"], h)
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


def test_the_local_back_end_needs_the_real_gpu0_lease_never_an_environment_string(monkeypatch):
    """Integrator B3: availability is gpu0.held() (a check, never an acquisition); without pipeline/gpu0.py the
    back-end is never available; no environment string stands in for custody."""
    cfg = {"kind": "ollama_local", "vendor": "local", "model": "local-model", "enabled": True}
    monkeypatch.setitem(sys.modules, "gpu0", None)                 # absent (as in this worktree before the merge)
    b = providers.OllamaLocalBackend("local", cfg, providers.Keyring("/nonexistent"))
    assert not b.enabled()
    with pytest.raises(BackendError) as e:
        b.complete("p", None, 100)
    assert e.value.kind == "disabled" and "lease" in e.value.detail
    held = {"v": False}
    monkeypatch.setitem(sys.modules, "gpu0", types.SimpleNamespace(held=lambda: held["v"]))
    monkeypatch.setenv("PP_INGEST_GPU0_LEASE_HELD", "1")            # the old string means nothing now
    assert not b.enabled()
    held["v"] = True
    assert b.enabled()
    assert not providers.OllamaLocalBackend("local", dict(cfg, enabled=False), providers.Keyring("/x")).enabled()


def test_the_local_model_is_released_at_the_end_of_a_cycle(monkeypatch):
    stopped = []

    class LLM:
        def __init__(self, model):
            self.digest = "d"

        def start(self):
            return self

        def _post(self, prompt, max_tokens, seed):
            return OK

        def stop(self):
            stopped.append(True)
    monkeypatch.setitem(sys.modules, "gpu0", types.SimpleNamespace(held=lambda: True))
    monkeypatch.setitem(sys.modules, "story_semantics", types.SimpleNamespace(LocalLLM=LLM))
    cfg = H.router_cfg(["local"])
    cfg["backends"]["local"] = {"kind": "ollama_local", "vendor": "local", "model": "m", "enabled": True}
    r = providers.Router(cfg, keyring=providers.Keyring("/nonexistent"), sleep=lambda s: None)
    assert r.run("mine", "p", None, validate_obj).backend == "local"
    r.release()
    assert stopped == [True] and r.backends["local"]._llm is None
    r.release()                                    # idempotent
    assert stopped == [True]


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


def test_the_real_config_under_the_spend_freeze():
    """L-x: every role names >= 2 interchangeable back-ends. Orchestrator 05:30: until told otherwise the mine chain
    is the metered gateway then the local interface ONLY; no frozen vendor's back-end is in it, and none is callable."""
    cfg = providers.load_config()
    for role, rc in cfg["roles"].items():
        assert len(rc["chain"]) >= 2, role
    assert {b["kind"] for b in cfg["backends"].values()} <= set(providers.KINDS)
    fz = providers.frozen_vendors(cfg)
    assert {"openai", "anthropic", "xai"} <= fz
    mine_chain = cfg["roles"]["mine"]["chain"]
    assert [cfg["backends"][b]["kind"] for b in mine_chain] == ["openai_compat", "ollama_local"]
    assert cfg["backends"][mine_chain[0]].get("spend_meter") is True
    assert not [b for b in mine_chain if cfg["backends"][b]["vendor"] in fz]
    r = providers.Router(cfg, keyring=providers.Keyring("/nonexistent"))
    for bid in cfg["backends"]:
        if cfg["backends"][bid]["vendor"] in fz:
            assert r.frozen(bid) and r.available(bid)[0] is False
    assert r.effective("mine") == [mine_chain[0]]          # this session: no GPU0 lease, so the gateway alone


def test_a_frozen_vendor_is_never_called_whatever_the_chain_only_or_enabled_say(tmp_path):
    a = H.FakeBackend("a", fn=lambda p: BackendError("network", "down"))
    f = H.FakeBackend("f", [OK, OK, OK], cfg={"vendor": "paid"})
    r = H.make_router([a, f], freeze=["paid"], cache_dir=str(tmp_path))
    with pytest.raises(providers.AllBackendsFailed) as e:
        r.run("mine", "p", None, validate_obj)                       # in the chain: skipped
    assert f.calls == [] and e.value.tried[1][1] == "skipped" and "spend freeze" in e.value.tried[1][2]
    assert e.value.outage is True                                     # the work waits; it never falls through
    with pytest.raises(providers.AllBackendsFailed):
        r.run("mine", "p", None, validate_obj, only="f")              # named directly: still skipped
    assert r._try("f", "mine", "p", None, validate_obj, None, 3, 100)[0] == "unavailable"
    assert f.calls == []


def test_a_frozen_vendors_stored_reply_costs_nothing_and_may_be_reused(tmp_path):
    f = H.FakeBackend("f", [OK])
    r = H.make_router([f], cache_dir=str(tmp_path))
    assert r.run("mine", "p", None, validate_obj).cached is False
    rf = H.make_router([f], freeze=[f.cfg["vendor"]], cache_dir=str(tmp_path))
    out = rf.run("mine", "p", None, validate_obj)
    assert out.cached is True and len(f.calls) == 1


def test_the_config_must_name_every_back_ends_vendor():
    cfg = H.router_cfg(["a"])
    del cfg["backends"]["a"]["vendor"]
    with pytest.raises(ValueError, match="vendor"):
        providers.validate_config(cfg)
    cfg = H.router_cfg(["a"])
    cfg["spend_freeze"] = {"vendors": "openai"}
    with pytest.raises(ValueError, match="spend_freeze"):
        providers.validate_config(cfg)


def test_a_vendor_reported_cost_in_ticks_is_the_recorded_cost(monkeypatch):
    cfg = {"kind": "openai_compat", "vendor": "v", "model": "m", "base_url": "http://x", "key_env": "K",
           "price": {"in_per_mtok": 5.0, "out_per_mtok": 25.0, "basis": "estimate"}}

    class KR:
        def get(self, name=None, prefix=None):
            return ["k"]

        def redact(self, s):
            return s
    b = providers.OpenAICompatBackend("x", cfg, KR())
    canned = json.dumps({"model": "m", "choices": [{"message": {"content": OK}, "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": 6767, "completion_tokens": 95, "total_tokens": 10785,
                                   "cost_in_usd_ticks": 183693500}}).encode()
    monkeypatch.setattr(b, "_request", lambda path, req=None, timeout=None: (200, canned, {}, 1.0))
    r = b.complete("p", None, 100)
    assert r.cost_basis == "usage.cost_in_usd_ticks" and abs(r.cost_usd - 0.01836935) < 1e-9


def test_error_text_is_redacted_of_every_key_before_it_is_recorded(tmp_path):
    env = tmp_path / ".env"
    env.write_text("GW_KEY=sk-live-0123456789abcdef\n")
    kr = providers.Keyring(str(env))
    seen = []
    b = providers.OpenAICompatBackend("gw", {"kind": "openai_compat", "vendor": "v", "model": "m",
                                             "base_url": "http://127.0.0.1:9", "key_env": "GW_KEY"}, kr)
    b.complete = lambda p, s, m: (_ for _ in ()).throw(
        BackendError("http_auth", "invalid key sk-live-0123456789abcdef", raw="echo: sk-live-0123456789abcdef"))
    cfg = H.router_cfg(["gw"])
    r = providers.Router(cfg, keyring=kr, backends={"gw": b}, sleep=lambda s: None, on_attempt=seen.append)
    with pytest.raises(providers.AllBackendsFailed) as e:
        r.run("mine", "p", None, validate_obj)
    blob = json.dumps(seen, default=str) + str(e.value)
    assert "sk-live-0123456789abcdef" not in blob and "[redacted]" in blob


def test_a_redirect_is_refused_so_the_key_never_follows_it():
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    hits = []

    class H302(BaseHTTPRequestHandler):
        def do_POST(self):
            hits.append((self.path, self.headers.get("Authorization")))
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:%d/elsewhere" % self.server.server_port)
            self.end_headers()

        def do_GET(self):
            self.do_POST()

        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), H302)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        class KR:
            def get(self, name=None, prefix=None):
                return ["sekret-key-value"]

            def redact(self, s):
                return s
        b = providers.OpenAICompatBackend("gw", {"kind": "openai_compat", "vendor": "v", "model": "m",
                                                 "base_url": f"http://127.0.0.1:{srv.server_port}/api",
                                                 "key_env": "K", "timeout_s": 5}, KR())
        with pytest.raises(BackendError) as e:
            b.complete("p", None, 10)
        assert e.value.kind == "redirect" and len(hits) == 1 and hits[0][0] == "/api/chat/completions"
    finally:
        srv.shutdown()


def test_a_runtime_override_may_point_only_at_this_machine_or_the_configured_host(tmp_path):
    path = tmp_path / "overrides.json"
    ov = providers.Overrides(str(path))
    b = providers.OpenAICompatBackend("gw", {"model": "m", "base_url": "https://gw.example/api/v1"},
                                      providers.Keyring("/nonexistent"))
    b.overrides = ov
    path.write_text(json.dumps({"gw": {"base_url": "https://attacker.example/api/v1"}}))
    os.utime(path, (1, 1))                                          # distinct mtimes: two writes in one tick
    assert b.base == "https://gw.example/api/v1"                   # refused: the key would go there
    path.write_text(json.dumps({"gw": {"base_url": "https://gw.example/v2"}}))
    os.utime(path, (2, 2))
    assert b.base == "https://gw.example/v2"
    assert providers.override_allowed("http://localhost:9/x", "https://gw.example") is True
    assert providers.override_allowed("file:///etc/passwd", "https://gw.example") is False


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


def _code_words(path):
    """Identifiers and string constants of a module, docstrings excluded (prose may cite an order)."""
    tree = ast.parse(open(path).read())
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body and \
                isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], "value", None), ast.Constant):
            docs.add(id(node.body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            out.append(node.id)
        elif isinstance(node, ast.Attribute):
            out.append(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            out.append(node.name)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            out.append(node.value)
    return out


def test_no_vendor_name_in_the_code_outside_the_provider_config():
    """Law L-x (integrator, non-blocking): the vendors named in providers.json appear in no identifier or string of
    the package or the tool (the protocol adapters in providers.py are 'kinds', not vendors)."""
    cfg = providers.load_config()
    vendors = {b["vendor"].lower() for b in cfg["backends"].values()} | providers.frozen_vendors(cfg)
    for path in glob.glob(os.path.join(config.PKG_DIR, "*.py")) + [os.path.join(config.REPO, "tools", "ingest_watch.py")]:
        if os.path.basename(path) == "providers.py":
            continue
        hits = sorted({w for w in _code_words(path) for v in vendors if re.search(rf"(?<![a-z]){re.escape(v)}(?![a-z])", w.lower())})
        assert not hits, f"{os.path.basename(path)}: {hits}"


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
