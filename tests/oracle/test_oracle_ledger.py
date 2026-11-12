"""The spend guard holds across processes (audit F1 / F3) and no key text leaves the process (audit F11)."""
import json
import multiprocessing as mp

import pytest

from pipeline.oracle import llm

GPT = {"in": 2.0, "out": 10.0}


def _hold(path, ready, done):
    led = llm.Ledger(path, cap=1.0)
    led.allow(GPT, 0, 60_000, "other process")                  # 0.60 reserved by ANOTHER process
    ready.set()
    done.wait(30)


def test_a_reservation_in_another_process_counts_and_a_dead_process_reservation_is_charged(tmp_path):
    path = str(tmp_path / "SPEND.jsonl")
    ctx = mp.get_context("fork")
    ready, done = ctx.Event(), ctx.Event()
    child = ctx.Process(target=_hold, args=(path, ready, done))
    child.start()
    try:
        assert ready.wait(30)
        led = llm.Ledger(path, cap=1.0)
        assert led.in_flight() == pytest.approx(0.6)
        with pytest.raises(llm.SpendStop):                      # 0.60 elsewhere + 0.60 here > 1.00
            led.allow(GPT, 0, 60_000, "this process")
    finally:
        done.set()
        child.join(30)
    led = llm.Ledger(path, cap=1.0)              # the ended process's call may have been billed: charged, not dropped
    assert led.in_flight() == 0.0 and led.spent() == pytest.approx(0.6)
    rows = [json.loads(x) for x in open(path)]
    assert rows[-1]["usd_source"].startswith("orphaned: worst case")
    with pytest.raises(llm.SpendStop):
        led.allow(GPT, 0, 60_000, "another 0.60")
    assert led.allow(GPT, 0, 30_000, "0.30 fits")


def test_settle_records_the_row_and_drops_the_reservation_in_one_step(tmp_path):
    led = llm.Ledger(str(tmp_path / "SPEND.jsonl"), cap=1.0)
    tok = led.allow(GPT, 0, 50_000, "a")                         # 0.50 reserved
    led.settle(tok, usd=0.05, tag="a")
    assert led.spent() == 0.05 and led.in_flight() == 0.0
    led.allow(GPT, 0, 90_000, "b")                               # 0.05 + 0.90 fits only because a settled


def test_an_unpriced_call_is_refused_once_the_cap_is_reached(tmp_path):
    led = llm.Ledger(str(tmp_path / "SPEND.jsonl"), cap=1.0)
    led.allow_unpriced("heimdall")
    led.record(usd=1.0, tag="earlier")
    with pytest.raises(llm.SpendStop):
        led.allow_unpriced("heimdall")


def test_redact_masks_every_loaded_key_and_key_shaped_tokens(tmp_path):
    env = tmp_path / ".env"
    env.write_text("SOME_KEY=abc123secretvalue987\n")
    v = llm.env_key("SOME_KEY", str(env))
    text = (f"Error: Incorrect API key provided: {v}; also sk-proj-********************abcd and "
            f"Authorization: Bearer abc.def.ghi and xai-AbCdEf123456")
    out = llm.redact(text)
    assert v not in out and "abcd" not in out and "abc.def.ghi" not in out and "xai-AbCdEf" not in out
    assert out.count("[REDACTED]") == 4
    assert json.loads(json.dumps(llm.redact("plain text, no key"))) == "plain text, no key"
