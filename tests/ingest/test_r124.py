"""tests/ingest/test_r124.py: the local model stays the last resort whatever the spend meter says (ruling 118; r124).

Found at r123's restart (21:31 ET Nov 17): the startup line listed the local back-end FIRST among the callable ones.
Router.order (integrator B1, orchestrator 02:45) moves the metered back-ends after the others while the spend meter is
not 'ok' (90 % of the cap, or no reading for an hour), and every gateway model is metered: with the local model callable
(r123), an unmeasured meter would have sent every mining request to GPU1 first (a model load per request) against
ruling 118's order, "the next Heimdall model ..., then the local model on a free card under the lease". A back-end
marked last_resort now stays after every other back-end of its chain; B1 otherwise unchanged (the meter notifies, the
metered back-ends are never taken out, others first).
"""
import json

import pytest

import helpers as H
from pipeline.ingest import providers, spend

OK = json.dumps({"ok": True})


def validate_obj(content):
    obj = json.loads(content)
    if obj != {"ok": True}:
        raise providers.Invalid("not ok")
    return obj


def tripped(router, h):
    m = spend.CreditMeter(H.router_cfg(["h"])["spend_meter"], h)
    router.meter = m
    m.measure()                                    # 95 of a 100 cap: at 90 %, tripped
    assert m.state() == "tripped"


def test_a_last_resort_back_end_stays_last_while_the_meter_is_not_ok():
    h = H.FakeBackend("h", [OK], cfg={"spend_meter": True}, usage_total=95.0)
    h2 = H.FakeBackend("h2", [OK], cfg={"spend_meter": True})
    loc = H.FakeBackend("loc", [OK], cfg={"last_resort": True})
    r = H.make_router([h, h2, loc])
    tripped(r, h)
    assert r.order("mine") == ["h", "h2", "loc"]
    out = r.run("mine", "p", None, validate_obj)
    assert out.backend == "h" and loc.calls == []
    h.fn = h2.fn = (lambda p: providers.BackendError("network", "down"))      # the gateway down: the last resort answers
    assert r.run("mine", "p2", None, validate_obj).backend == "loc"


def test_b1_still_puts_another_back_end_first_and_never_takes_the_metered_ones_out():
    h = H.FakeBackend("h", [OK, OK], cfg={"spend_meter": True}, usage_total=95.0)
    b = H.FakeBackend("b", [OK])
    loc = H.FakeBackend("loc", [OK], cfg={"last_resort": True})
    r = H.make_router([h, b, loc])
    tripped(r, h)
    assert r.order("mine") == ["b", "h", "loc"]
    assert r.run("mine", "p", None, validate_obj).backend == "b"
    r.meter = None                                  # no meter (or 'ok'): the configured chain as it is
    assert r.order("mine") == ["h", "b", "loc"]


def test_the_real_chains_keep_ruling_118s_order_whatever_the_meter_says():
    cfg = providers.load_config()
    r = providers.Router(cfg, keyring=providers.Keyring("/nonexistent"))

    class Meter:
        def __init__(self, s):
            self.s = s

        def state(self):
            return self.s
    for st in ("ok", "unmeasured", "tripped"):
        r.meter = Meter(st)
        for role in ("mine", "hook", "spotlight"):
            assert r.order(role) == cfg["roles"][role]["chain"], (st, role)
            assert r.effective(role)[-1] == cfg["roles"][role]["chain"][-1], (st, role)


def test_last_resort_must_be_true_or_false():
    cfg = H.router_cfg(["a", "b"])
    cfg["backends"]["b"]["last_resort"] = "yes"
    with pytest.raises(ValueError, match="last_resort"):
        providers.validate_config(cfg)


def test_last_resort_back_ends_keep_their_order_and_a_metered_one_appears_once():
    """Audit r124 c1 (muse P2 x2): several last-resort back-ends keep their chain order after every other one; a
    back-end both metered and last-resort is placed once, among the last-resort ones."""
    h = H.FakeBackend("h", [OK], cfg={"spend_meter": True}, usage_total=95.0)
    hl = H.FakeBackend("hl", [OK], cfg={"spend_meter": True, "last_resort": True})
    b = H.FakeBackend("b", [OK])
    l1 = H.FakeBackend("l1", [OK], cfg={"last_resort": True})
    l2 = H.FakeBackend("l2", [OK], cfg={"last_resort": True})
    r = H.make_router([l2, hl, h, l1, b])
    tripped(r, h)
    assert r.order("mine") == ["b", "h", "l2", "hl", "l1"]
