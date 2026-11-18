"""tests/ingest/test_r123.py: the local model on a free card under the lease (ruling 118; the 10:50 order of Nov 16 (2)).

The last back-end of the mine, hook and spotlight chains is the local model on GPU1 (law L-r's layout, PBX 2026-11-12:
GPU0 renders and their gates, GPU1 everything else). Each request goes through the main tree's lease client
(services/gpu_lease_client.py, gpu0.ollama_call): the GPU1 lease taken within a bound, the memory proven free, the
request with keep_alive 0, the unload confirmed before the lease is released. A card not free within the bound is
'busy': not retried on the card; the work waits. After a request that reached the card, the card is left free for
yield_s, so another owner takes its turn. No test takes a real lease: tests/ingest/conftest.py gives every test a
refusing client; these tests install their own, and the one that runs the main tree's real client file gives it a
stand-in for gpu0.
"""
import io
import json
import os
import sys
import types
import urllib.error

import pytest

import helpers as H
from pipeline.ingest import config, providers
from pipeline.ingest.providers import BackendError

OK = json.dumps({"ok": True})
REAL_CLIENT = os.path.join(config.MAIN_TREE, "services", "gpu_lease_client.py")


def validate_obj(content):
    obj = json.loads(content)
    if obj != {"ok": True}:
        raise providers.Invalid("not ok")
    return obj


def local(**over):
    cfg = dict({"kind": "ollama_local", "vendor": "local", "model": "m", "enabled": True, "lease_wait_s": 45,
                "yield_s": 0, "num_ctx": 8192, "timeout_s": 120}, **over)
    return providers.OllamaLocalBackend("local", cfg, providers.Keyring("/nonexistent"))


class Client:
    """A stand-in for the lease client: replies (str) or exceptions, in order; every call recorded."""

    class Gpu1Unavailable(RuntimeError):
        pass

    def __init__(self, *script):
        self.script, self.calls = list(script), []

    def chat_gpu1(self, model, messages, owner, options=None, fmt=None, wait_s=600.0, timeout=120):
        self.calls.append(dict(model=model, messages=messages, owner=owner, options=options, fmt=fmt, wait_s=wait_s,
                               timeout=timeout))
        r = self.script.pop(0) if self.script else OK
        if isinstance(r, BaseException):
            raise r
        return r


@pytest.fixture
def client(monkeypatch):
    def install(*script):
        c = Client(*script)
        monkeypatch.setitem(sys.modules, providers.LEASE_CLIENT_MODULE, c)
        return c
    return install


def test_the_local_model_is_asked_only_after_every_gateway_model_failed_and_as_the_pipeline_asks_it(client):
    c = client(OK)
    a = H.FakeBackend("a", fn=lambda p: BackendError("network", "down"))
    b = H.FakeBackend("b", fn=lambda p: BackendError("timeout", "slow"))
    r = H.make_router([a, b, local()])
    out = r.run("mine", "the window's question", None, validate_obj)
    assert out.backend == "local" and out.obj == {"ok": True} and out.model == "m" and a.calls and b.calls
    assert c.calls == [dict(model="m", messages=[{"role": "user", "content": "the window's question"}],
                            owner=providers.LEASE_OWNER,
                            options={"temperature": 0, "seed": 7, "num_ctx": 8192, "num_predict": 1000},
                            fmt="json", wait_s=45.0, timeout=120.0)]          # num_predict: the role's reply budget
    a.fn = lambda p: OK                                                      # the gateway answers: the card is not asked
    assert r.run("mine", "another", None, validate_obj).backend == "a" and len(c.calls) == 1


def test_a_card_not_free_is_busy_asked_once_and_the_work_waits_through_the_real_lease_client(monkeypatch):
    """The main tree's own client file, run with a stand-in gpu0 (never the real lease): a GPU stop (a BaseException;
    LeaseBusy here) is renamed by the client and read as 'busy': one request, no retry on the card, nothing out of the
    chain but AllBackendsFailed with outage (the videos wait)."""
    assert os.path.isfile(REAL_CLIENT), "the main tree's lease client (main fb973fd0) is the local back-end's only way"

    class Gpu0Stop(BaseException):
        pass

    class LeaseBusy(Gpu0Stop):
        pass
    asked = []

    def ollama_call(gpu, model, path, body, owner, wait_s=600.0, timeout=300):
        asked.append(dict(gpu=gpu, model=model, path=path, body=body, owner=owner, wait_s=wait_s, timeout=timeout))
        raise LeaseBusy("the GPU1 lease is held by word-pass worker (integrator, GPU1) (pid 1)")
    monkeypatch.setitem(sys.modules, "pp_gpu0", types.SimpleNamespace(Gpu0Stop=Gpu0Stop, ollama_call=ollama_call))
    monkeypatch.delitem(sys.modules, providers.LEASE_CLIENT_MODULE)        # the conftest's: the real file loads
    monkeypatch.setattr(providers, "LEASE_CLIENT", REAL_CLIENT)
    a = H.FakeBackend("a", fn=lambda p: BackendError("network", "down"))
    r = H.make_router([a, local()])
    with pytest.raises(providers.AllBackendsFailed) as e:
        r.run("mine", "q", None, validate_obj)
    assert sys.modules[providers.LEASE_CLIENT_MODULE].__file__ == REAL_CLIENT
    assert e.value.outage and e.value.tried[-1][:2] == ("local", "unavailable")
    assert e.value.tried[-1][2].startswith("busy: GPU1 LeaseBusy: the GPU1 lease is held by word-pass worker")
    assert len(asked) == 1 and asked[0]["gpu"] == 1 and asked[0]["path"] == "/api/chat" and asked[0]["model"] == "m"
    assert asked[0]["body"] == {"messages": [{"role": "user", "content": "q"}], "stream": False, "format": "json",
                                "options": {"temperature": 0, "seed": 7, "num_ctx": 8192, "num_predict": 1000}}
    assert asked[0]["owner"] == providers.LEASE_OWNER and asked[0]["wait_s"] == 45.0 and asked[0]["timeout"] == 120.0


def test_the_card_is_left_free_after_every_request_that_reached_it_never_after_a_refusal(client):
    t, slept = [100.0], []
    b = local(yield_s=3)

    def sleep(s):
        slept.append(s)
        t[0] += s
    b._clock, b._sleep = (lambda: t[0]), sleep
    busy = Client.Gpu1Unavailable("GPU1 Gpu0Foreign: a foreign GPU1 user, still there after a 45.0s wait")
    down = urllib.error.HTTPError("http://127.0.0.1:11435/api/chat", 500, "Internal Server Error", {},
                                  io.BytesIO(b"the model runner stopped"))
    c = client(OK, busy, down, OK)
    assert b.complete("p", None, 10).content == OK and slept == []          # nothing to wait for before the first
    with pytest.raises(BackendError) as e:
        b.complete("p", None, 10)
    assert e.value.kind == "busy" and slept == [3.0]                        # waited: the card was left free 3 s
    with pytest.raises(BackendError) as e:
        b.complete("p", None, 10)
    assert e.value.kind == "server" and slept == [3.0]                      # the refusal never reached the card
    t[0] += 1.0
    assert b.complete("p", None, 10).content == OK and slept == [3.0, 2.0]  # the failed request did: 3 s from its end
    assert len(c.calls) == 4


def test_enabled_reads_the_config_and_the_clients_file_and_never_loads_it(tmp_path, monkeypatch):
    """Integrator B3 (nothing stands in for custody): enabled() is a check, never a load or a lease; the client is
    loaded at the first request, checked for the API used here, and never kept when it is not that API."""
    mark = tmp_path / "loaded"
    f = tmp_path / "gpu_lease_client.py"
    f.write_text(f"open({str(mark)!r}, 'w').write('loaded')\n")             # loading it is visible; it has no API
    monkeypatch.delitem(sys.modules, providers.LEASE_CLIENT_MODULE)
    monkeypatch.setattr(providers, "LEASE_CLIENT", str(f))
    assert local().enabled() and not local(enabled=False).enabled()
    with pytest.raises(BackendError) as e:
        local(enabled=False).complete("p", None, 10)
    assert e.value.kind == "disabled" and not mark.exists()                 # nothing loaded, no lease
    with pytest.raises(BackendError) as e:
        local().complete("p", None, 10)
    assert e.value.kind == "disabled" and "Gpu1Unavailable" in e.value.detail and mark.exists()
    assert providers.LEASE_CLIENT_MODULE not in sys.modules                 # not kept: a fixed file loads next time
    monkeypatch.setattr(providers, "LEASE_CLIENT", str(tmp_path / "absent.py"))
    assert not local().enabled()
    with pytest.raises(BackendError) as e:
        local().complete("p", None, 10)
    assert e.value.kind == "disabled"


def test_no_test_reaches_the_real_lease_client():
    """The suite's guard (tests/ingest/conftest.py): the real config's local back-end, asked in any test, is refused
    as a card that is not free, and the real client file is never the one named."""
    cfg = providers.load_config()
    bid = cfg["roles"]["mine"]["chain"][-1]
    b = providers.make_backend(bid, cfg["backends"][bid], providers.Keyring("/nonexistent"))
    assert isinstance(b, providers.OllamaLocalBackend) and b.enabled()
    with pytest.raises(BackendError) as e:
        b.complete("p", None, 10)
    assert e.value.kind == "busy" and "tests never take a GPU lease" in e.value.detail
    assert providers.LEASE_CLIENT != REAL_CLIENT
