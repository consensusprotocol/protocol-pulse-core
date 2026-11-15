"""Ruling 108 (orchestrator 21:22 ET Nov 14), BATCH 3's money: pp-ingest's spend goes to the builder's one ledger every
hour as 'BATCH <n> ingest spend: $x' FIRST on STATE line 1 (batch.py; spend.write_batch_notice). Line 1 also holds an
alarm (ruling 106 (d)) and ruling 87's switches, in that order; ruling 98's paid route stays inside the batch's share;
an abandoned call is booked at the model's own rate (ruling 107)."""
import json
import os
from datetime import datetime

import pytest

from pipeline.ingest import batch, providers, spend
from pipeline.ingest import queue as Q
from test_paid_route import fakes, paid_cfg

T0 = datetime(2026, 11, 14, 21, 10, tzinfo=batch.ET).timestamp()         # the batch's start
RATE = 2e-6                                                                 # m-h's own dollars per prompt token
CFG = {"backends": {"hb": {"vendor": "hv", "cost_from_usage": True, "price": {"in_per_mtok": 0.5}},
                    "hn": {"vendor": "hv", "cost_from_usage": True, "price": {"in_per_mtok": 0.5}},
                    "pg": {"vendor": "gv", "price": {"in_per_mtok": 5.0}}}}


def write_batch(path, name="BATCH 3", start="2026-11-14 21:10", end="2026-11-15 21:10", share=1.0, raw=None):
    with open(path, "w") as f:
        f.write(raw if raw is not None else json.dumps({"name": name, "start_et": start, "end_et": end,
                                                        "share_usd": share, "share_of": "mining and checks"}))
    st = os.stat(path)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 10_000_000_000))   # a later write is a new file to load()


@pytest.fixture
def bq(tmp_path, monkeypatch):
    spec = tmp_path / "batch.json"
    write_batch(spec)
    monkeypatch.setattr(batch, "SPEC", str(spec))
    t = [T0 - 3600]
    q = Q.Queue(str(tmp_path / "q.sqlite"), clock=lambda: t[0])
    return q, t, spec


def call(q, t, at, role="mine", backend="hb", model="m-h", kind="ok", cost=None, pt=1000):
    t[0] = at
    q.call({"role": role, "backend": backend, "model": model, "kind": kind,
            "cost_usd": (RATE * pt if pt else None) if cost == "rate" else cost,
            "usage": {"prompt_tokens": pt, "completion_tokens": 10} if pt else {}})


def ledger(path, *recs):
    with open(path, "w") as f:
        for r in recs:
            f.write((r if isinstance(r, str) else json.dumps(r)) + "\n")
    return str(path)


# ── the figure ──

def test_the_figure_runs_to_the_latest_whole_hour_by_use_with_an_abandoned_call_at_the_models_own_rate(bq, tmp_path):
    q, t, _ = bq
    for i in range(3):                                                     # history before the batch: m-h's rate
        call(q, t, T0 - 600 + i, cost="rate", pt=1000)
    call(q, t, T0 + 60, cost="rate", pt=600)                                # mining $0.0012
    call(q, t, T0 + 61, role="hook", cost="rate", pt=1000)                  # hook pass $0.0020
    call(q, t, T0 + 62, role="flagcheck", cost="rate", pt=250)              # flag checks $0.0005
    call(q, t, T0 + 63, role="probe", cost="rate", pt=50)                   # probes $0.0001
    call(q, t, T0 + 64, kind="cache", cost=0.0, pt=0)                       # a stored reply: free, not a call
    call(q, t, T0 + 100, kind="timeout", cost=None, pt=None)                # abandoned: 900 prompt tokens (mine's
    call(q, t, T0 + 3605, cost=0.03, pt=5000)                               # average on m-h) x RATE = $0.0018;
    led = ledger(tmp_path / "audit_spend.jsonl",                            # the next hour's call waits for 23:10
                 {"ts": T0 - 100, "usd": 1.0}, {"ts": T0 + 200, "usd": 0.003, "basis": "reported"},
                 {"ts": T0 + 3700, "usd": 0.5})
    assert batch.notice(q, T0 + 3599, CFG, led).startswith(
        "BATCH 3 ingest spend: $0.0000 (21:10 ET Nov 14 to 21:10 ET: ")    # the figure moves only on the hour
    line = batch.notice(q, T0 + 3610, CFG, led, quiet="NOTHING BITCOIN IN THE LAST 3 H")
    assert line == ("BATCH 3 ingest spend: $0.0086 (21:10 ET Nov 14 to 22:10 ET: mining and checks $0.0056 of the "
                    "$1.00 share (mining $0.0030, hook pass $0.0020, flag checks and calibration $0.0005, probes $0.0001), 5 model "
                    "call(s); audits $0.0030, 1 cost record(s); vendor-reported; $0.0018 booked for 1 abandoned call(s) "
                    "at the model's own rate); NOTHING BITCOIN IN THE LAST 3 H")
    assert "|" not in line and "\n" not in line                            # one notice of line 1
    left, what = batch.share_left(q, T0 + 3610, CFG)                       # the paid route counts to now: the
    rate_now = (3 * 0.002 + 0.0012 + 0.002 + 0.0005 + 0.0001 + 0.03) / (3 * 1000 + 600 + 1000 + 250 + 50 + 5000)
    spent = 0.0012 + 0.0020 + 0.0005 + 0.0001 + 0.03 + rate_now * (3 * 1000 + 600 + 5000) / 5   # the next hour's
    assert abs(left - (1.0 - spent)) < 1e-9 and what == "BATCH 3's $1.00 share for mining and checks"   # call, at
                                                                           # its own rate, moves the share, never the
                                                                           # hour already out


def test_an_abandoned_call_is_at_the_list_price_of_its_prompt_until_the_model_has_3_reported_calls(bq):
    q, t, _ = bq
    for i in range(2):
        call(q, t, T0 + i, backend="hn", model="m-new", cost=0.01, pt=1000)
    call(q, t, T0 + 10, backend="hn", model="m-new", kind="timeout", cost=None, pt=None)
    w = batch.watcher_spend(q, T0, T0 + 3600, CFG)
    assert abs(w["abandoned"] - 0.5e-6 * 1000) < 1e-12 and w["abandoned_n"] == 1     # in_per_mtok 0.5 x 1000
    call(q, t, T0 + 20, backend="hn", model="m-new", cost=0.01, pt=1000)              # a third reported call:
    w = batch.watcher_spend(q, T0, T0 + 3600, CFG)                                     # its own rate, 1e-5 a token
    assert abs(w["abandoned"] - 1e-5 * 1000) < 1e-12


def test_an_abandoned_call_with_no_prompt_size_known_is_said_never_read_as_nothing(bq, tmp_path):
    q, t, _ = bq
    call(q, t, T0 + 5, role="newrole", backend="hn", model="m-none", kind="timeout", cost=None, pt=None)
    line = batch.notice(q, T0 + 3600, CFG, str(tmp_path / "none.jsonl"))
    assert "1 abandoned call(s) NOT PRICED (no prompt size known)" in line


def test_a_cost_priced_from_the_table_and_an_unreadable_audit_record_are_said_apart(bq, tmp_path):
    q, t, _ = bq
    call(q, t, T0 + 5, role="mine_paid", backend="pg", model="m-g", cost=0.02, pt=1000)
    led = ledger(tmp_path / "a.jsonl", {"ts": T0 + 9, "usd": 0.001}, "{torn", {"ts": T0 + 9, "usd": float("nan")})
    line = batch.notice(q, T0 + 3600, CFG, led)
    assert "$0.0200 priced from the table (its vendor reports no cost)" in line
    assert "audits $0.0010, 1 cost record(s)" in line and "2 audit cost record(s) UNREADABLE (not counted)" in line


# ── the batch's file ──

def test_a_closed_batch_says_so_and_outside_a_batch_the_paid_route_has_nothing_left(bq, tmp_path):
    q, t, _ = bq
    call(q, t, T0 + 5, cost=0.25, pt=1000)
    end = T0 + 24 * 3600
    line = batch.notice(q, end + 7200, CFG, str(tmp_path / "none.jsonl"))
    assert line.startswith("BATCH 3 ingest spend: $0.2500 (CLOSED, 21:10 ET Nov 14 to 21:10 ET Nov 15: ")
    assert line.endswith("; NO BATCH OPEN SINCE 21:10 ET Nov 15: the paid route spends nothing until the next batch's "
                         "money is set")
    assert batch.share_left(q, end + 1, CFG)[0] == 0.0 and batch.share_left(q, T0 - 1, CFG)[0] == 0.0
    assert batch.share_left(q, T0 + 60, CFG)[0] == pytest.approx(0.75)


def test_a_new_batch_is_read_without_a_restart_and_an_unreadable_one_fails_closed(bq, tmp_path):
    q, t, spec = bq
    assert batch.load()["name"] == "BATCH 3"
    write_batch(spec, name="BATCH 4", start="2026-11-15 21:10", end="2026-11-16 21:10", share=0.5)
    assert batch.load()["name"] == "BATCH 4" and batch.load()["share_usd"] == 0.5
    for raw in ("{not json", json.dumps({"name": "BATCH 5", "start_et": "2026-11-15 21:10",
                                         "end_et": "2026-11-15 21:10", "share_usd": 1.0})):    # no time between
        write_batch(spec, raw=raw)
        left, why = batch.share_left(q, T0 + 60, CFG)
        assert left == 0.0 and "cannot be read" in why                    # no paid call starts
        with pytest.raises((ValueError, KeyError)):
            batch.notice(q, T0 + 60, CFG, str(tmp_path / "none.jsonl"))   # the service logs it; line 1 keeps its
                                                                           # last figure


@pytest.mark.parametrize("share", ["Infinity", "NaN", "-1"])
def test_a_share_that_is_not_a_finite_amount_is_no_batch(bq, share):
    q, t, spec = bq
    write_batch(spec, raw='{"name": "BATCH 3", "start_et": "2026-11-14 21:10", "end_et": "2026-11-15 21:10", '
                          f'"share_usd": {share}}}')
    with pytest.raises(ValueError):
        batch.load()
    assert batch.share_left(q, T0 + 60, CFG)[0] == 0.0


# ── STATE line 1 ──

SWITCHES = ("10:18 ET: BACK TO HV-FIRST (THE PROBE ANSWERED 3 TIMES IN A ROW) | 10:12 ET: SWITCHED TO PLAN B (NO "
            "ANSWER FOR 15 MINUTES) |")


def test_line_1_holds_the_batch_spend_first_then_an_alarm_then_every_switch(tmp_path):
    doc, notify = tmp_path / "STATE.md", tmp_path / "ing" / "NOTIFY.txt"
    doc.write_text(SWITCHES + "\nPP-INGEST CYCLES TO 20:03 ET (x): y\n09:00 ET: the session line\n# body\n")
    kw = {"doc": str(doc), "notify_path": str(notify)}
    spend.write_batch_notice("BATCH 3 ingest spend: $0.0000 (a)", **kw)
    assert doc.read_text().split("\n")[:3] == ["BATCH 3 ingest spend: $0.0000 (a) | " + SWITCHES,
                                               "PP-INGEST CYCLES TO 20:03 ET (x): y", "09:00 ET: the session line"]
    spend.write_alarm_notice("A real outage has stopped mining", "03:12 ET", **kw)
    spend.write_switch_head("10:40 ET: SWITCHED TO PLAN B (NEW) |", **kw)              # a switch: on line 1 still
    spend.write_cycles_notice("PP-INGEST CYCLES TO 20:13 ET (x): z", **kw)
    spend.write_batch_notice("BATCH 3 ingest spend: $0.0123 (b)", **kw)                 # the next hour: replaced
    lines = doc.read_text().split("\n")
    assert lines[0] == ("BATCH 3 ingest spend: $0.0123 (b) | ALARM FOR PBX: A real outage has stopped mining. Waiting "
                        "since 03:12 ET. | 10:40 ET: SWITCHED TO PLAN B (NEW) | " + SWITCHES)
    assert lines[1:4] == ["PP-INGEST CYCLES TO 20:13 ET (x): z", "09:00 ET: the session line", "# body"]
    spend.write_alarm_notice(None, None, **kw)
    spend.write_batch_notice(None, **kw)
    assert doc.read_text().split("\n")[0] == "10:40 ET: SWITCHED TO PLAN B (NEW) | " + SWITCHES


def test_line_1_without_a_switch_and_a_bar_or_newline_in_its_notices_refused(tmp_path):
    doc, notify = tmp_path / "STATE.md", tmp_path / "ing" / "NOTIFY.txt"
    doc.write_text("09:00 ET: the session line\n")
    kw = {"doc": str(doc), "notify_path": str(notify)}
    spend.write_cycles_notice("PP-INGEST CYCLES TO 20:13 ET (x): z", **kw)
    spend.write_batch_notice("BATCH 3 ingest spend: $0.0001 (c)", **kw)
    assert doc.read_text() == ("BATCH 3 ingest spend: $0.0001 (c)\nPP-INGEST CYCLES TO 20:13 ET (x): z\n"
                               "09:00 ET: the session line\n")
    before = doc.read_text()
    for bad in ("BATCH 3 ingest spend: $1 | 10:00 ET: SWITCHED TO PLAN B", "BATCH 3 ingest spend: $1\nx",
                "SPEND $1"):
        with pytest.raises(ValueError):
            spend.write_batch_notice(bad, **kw)
    for sentence, since in (("one | two", "03:00 ET"), ("one\ntwo", "03:00 ET"), ("", "03:00 ET"), ("x", "")):
        with pytest.raises(ValueError):
            spend.write_alarm_notice(sentence, since, **kw)
    assert doc.read_text() == before


# ── ruling 98's paid route inside the share ──

def test_no_paid_call_starts_past_the_share_with_the_calls_in_flight_held_against_it():
    left = [0.0035]
    r = providers.Router(paid_cfg(), keyring=providers.Keyring("/nonexistent"), backends=fakes(),
                         sleep=lambda s: None, role_spend=lambda role, since: 0.0)
    r.caps.share = lambda: (left[0], "BATCH 3's $1.00 share for mining and checks")
    assert r.caps.reserve("mine_paid", 0.002, 1.0) is True                 # one call in flight holds $0.002
    why = r.caps.reserve_why("mine_paid", 0.002, 1.0)                      # a second would pass $0.0035
    assert why == ("BATCH 3's $1.00 share for mining and checks is spent ($0.0035 left, $0.0020 held by calls in "
                   "flight; this call may cost $0.0020)")
    r.caps.release("mine_paid", 0.002)
    with pytest.raises(providers.AllBackendsFailed) as e:
        left[0] = 0.001                                                    # less than one call's worst case
        r.run("mine_paid", "p", None, lambda c: c, use_cache=False)
    assert all(s == "skipped" and "share for mining and checks is spent" in w for _, s, w in e.value.tried)
    left[0] = 1.0
    assert r.run("mine_paid", "p", None, lambda c: c, use_cache=False).backend == "px"


def test_a_share_that_cannot_be_read_lets_no_paid_call_start():
    b = fakes()
    r = providers.Router(paid_cfg(), keyring=providers.Keyring("/nonexistent"), backends=b,
                         sleep=lambda s: None, role_spend=lambda role, since: 0.0)
    r.caps.share = lambda: 1 / 0
    with pytest.raises(providers.AllBackendsFailed) as e:
        r.run("mine_paid", "p", None, lambda c: c, use_cache=False)
    assert all("the batch's share could not be read (ZeroDivisionError)" in w for _, _, w in e.value.tried)
    assert b["px"].calls == [] and b["pg"].calls == []


def test_a_session_line_that_starts_like_the_batch_line_is_never_taken_for_a_notice(tmp_path):
    """Only line 1 can hold the batch spend or an alarm: a session line right under the notices that happens to start
    with 'BATCH 3 ingest spend:' (pp-ingest wrote its figure there before the watcher could) stays as it is."""
    doc, notify = tmp_path / "STATE.md", tmp_path / "ing" / "NOTIFY.txt"
    session = "BATCH 3 ingest spend: $0.0000 (by hand) | 21:21 ET: the session line | # pp-ingest: STATE"
    doc.write_text(SWITCHES + "\nPP-INGEST CYCLES TO 20:03 ET (x): y\n" + session + "\n# body\n")
    spend.write_batch_notice("BATCH 3 ingest spend: $0.0042 (the watcher)", doc=str(doc), notify_path=str(notify))
    assert doc.read_text().split("\n")[:4] == ["BATCH 3 ingest spend: $0.0042 (the watcher) | " + SWITCHES,
                                               "PP-INGEST CYCLES TO 20:03 ET (x): y", session, "# body"]


def test_a_call_cut_off_in_flight_is_booked_like_an_abandoned_one_and_an_answered_error_is_not(bq):
    """The stricter reading of ruling 108's basis (ruling 106 (b)): a call that failed after 30 s or more in flight with
    no answer (no HTTP status: a dropped connection) may have been billed, so it is booked at the model's own rate; an
    error the vendor answered (a 502 with its body) and a refused connection are what they reported: nothing."""
    q, t, _ = bq
    for i in range(3):
        call(q, t, T0 + i, cost="rate", pt=1000)
    for kind, status, lat in (("network", None, 45.0), ("server", 502, 60.0), ("network", None, 0.01)):
        t[0] += 1
        q.call({"role": "mine", "backend": "hb", "model": "m-h", "kind": kind, "cost_usd": None,
                "http_status": status, "latency_s": lat})
    w = batch.watcher_spend(q, T0, T0 + 3600, CFG)
    assert w["abandoned_n"] == 1 and abs(w["abandoned"] - RATE * 1000) < 1e-12


def test_a_hand_edited_line_1_with_the_alarm_before_the_batch_spend_still_splits_exactly(tmp_path):
    """Audit b108 c1 (qwen): the batch spend and an alarm are taken from the front of line 1 in any order, so a hand
    edit cannot fold the switch line into the batch notice (the next hour's figure would have replaced it)."""
    doc, notify = tmp_path / "STATE.md", tmp_path / "ing" / "NOTIFY.txt"
    doc.write_text("ALARM FOR PBX: x. Waiting since 03:00 ET. | BATCH 3 ingest spend: $0.1 (old) | " + SWITCHES +
                   "\n# body\n")
    spend.write_batch_notice("BATCH 3 ingest spend: $0.2 (new)", doc=str(doc), notify_path=str(notify))
    assert doc.read_text().split("\n")[0] == ("BATCH 3 ingest spend: $0.2 (new) | ALARM FOR PBX: x. Waiting since "
                                              "03:00 ET. | " + SWITCHES)


def test_two_paid_calls_at_once_never_both_take_the_last_of_the_share():
    """Audit b108 c1: the check and the hold are one step under RoleCaps' lock, so of many threads asking at once
    for a share with room for one call, exactly one is held."""
    import threading
    r = providers.Router(paid_cfg(), keyring=providers.Keyring("/nonexistent"), backends=fakes(),
                         sleep=lambda s: None, role_spend=lambda role, since: 0.0)
    r.caps.share = lambda: (0.003, "the share")                            # room for one $0.002 call
    go, got = threading.Barrier(8), []

    def ask():
        go.wait()
        got.append(r.caps.reserve("mine_paid", 0.002, 1.0))
    th = [threading.Thread(target=ask) for _ in range(8)]
    for x in th:
        x.start()
    for x in th:
        x.join()
    assert sorted(got) == [False] * 7 + [True]


def test_a_same_size_edit_of_the_batch_file_is_read_again(bq):
    q, t, spec = bq
    assert batch.load()["share_usd"] == 1.0
    st = os.stat(spec)
    spec.write_text(spec.read_text().replace('"share_usd": 1.0', '"share_usd": 2.0'))     # the same size
    os.utime(spec, ns=(st.st_atime_ns, st.st_mtime_ns))                                   # and the same mtime
    assert batch.load()["share_usd"] == 2.0


def test_audit_dollars_booked_at_the_models_own_rate_are_said_apart_from_the_reported(bq, tmp_path):
    q, t, _ = bq
    led = ledger(tmp_path / "a.jsonl", {"ts": T0 + 1, "usd": 0.0087, "basis": "reported"},
                 {"ts": T0 + 2, "usd": 0.0012, "basis": "cut off after 420.3 s in flight (network): ..."},
                 {"ts": T0 + 3, "usd": 0.0014, "reported": False, "basis": "x"},
                 {"ts": T0 + 4, "usd": 0.0001, "reported": True, "basis": "reported (failed: server)"})
    assert batch.audit_spend(led, T0, T0 + 10) == pytest.approx((0.0114, 4, 0, 0.0026))
    line = batch.notice(q, T0 + 3600, CFG, led)
    assert "audits $0.0114, 4 cost record(s); vendor-reported; $0.0026 of the audits booked for reviews cut off or " \
           "abandoned, at the model's own rate)" in line


def test_the_abandoned_calls_of_a_count_cost_two_grouped_queries_whatever_their_models_and_roles(bq):
    """Audit b108 c2 (both reviewers): the history behind ruling 107's basis is read in two grouped queries, only when a
    count holds an abandoned call, not three per model and role (the paid route's check runs under RoleCaps' lock)."""
    q, t, _ = bq
    for m in range(4):
        for role in ("mine", "hook", "flagcheck"):
            call(q, t, T0 + 1, role=role, model=f"m{m}", cost="rate", pt=1000)
            call(q, t, T0 + 2, role=role, model=f"m{m}", kind="timeout", cost=None, pt=None)

    class Counting:
        n = 0

        def rows(self, sql, args=()):
            Counting.n += 1
            return q.rows(sql, args)
    c = Counting()
    w = batch.watcher_spend(c, T0, T0 + 3600, CFG)
    assert w["abandoned_n"] == 12 and Counting.n == 3                       # the window's calls, then the history
    Counting.n = 0
    batch.watcher_spend(c, T0 + 1800, T0 + 3600, CFG)                       # nothing abandoned: no history read
    assert Counting.n == 1
