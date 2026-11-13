"""The append-only ledger, the packager adapter (best unused moments since T) and the coverage check."""
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

import helpers as H
from pipeline.ingest import config, contract, coverage, ledger, mine
from pipeline.ingest import queue as Q

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)


def line(rec, a=0, b=1, **over):
    timing, toks, sents = contract.sentences(rec)
    E, _, _ = contract.modules()
    w0, w1 = sents[a]["w0"], sents[b]["w1"]
    l = {"schema": contract.SCHEMA, "moment_id": contract.moment_id(rec["video_id"], rec["transcript_sha256"], w0, w1),
         "video_id": rec["video_id"], "channel_id": H.CHAN["channel_id"], "channel_name": "Test Channel",
         "published_at": (NOW - timedelta(hours=5)).isoformat(), "title": "t",
         "transcript_sha256": rec["transcript_sha256"], "transcript_method": rec["transcript_method"],
         "timing": timing, "words": [w0, w1], "sentences": [a, b], "text": E.spoken(toks[w0:w1 + 1]),
         "start": 0.0, "end": 8.0, "duration_s": None, "duration_estimate_s": 8.0,
         "speaker": {"turn_change_inside": None, "label": None, "confidence": None, "named": None, "named_source": None},
         "scores": dict(H.moment(0, 0)["scores"]), "names_person": False, "risk": [], "topics": [], "reason": "r",
         "eligibility": {"role": "clip", "ok": False, "reasons": [], "targets_missed": []},
         "mined": {"by": "m@b", "at": (NOW - timedelta(hours=1)).isoformat(), "contract_fp": contract.fingerprint()},
         "flags_ext": {"about_bitcoin": True, "altcoin": False}, "source": {}}
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(l.get(k), dict):
            l[k] = dict(l[k], **v)
        else:
            l[k] = v
    return l


def _expired(l, now=NOW):
    """The contract's expiry rule, written out (rulings 76 + 77): 12 h after the video's publish time."""
    return datetime.fromisoformat(l["published_at"]) + timedelta(hours=12) <= now


@pytest.fixture
def rec():
    r, meta = H.caption_record(H.vid(), n_rep=2)
    return r


class TestLedger:
    def test_append_read_round_trip_and_torn_tail(self, tmp_path, rec):
        p = str(tmp_path / "m.jsonl")
        ledger.append(p, [line(rec, 0, 1), line(rec, 2, 3)])
        with open(p, "a") as f:
            f.write('{"schema": "pp.moment/1", "moment_id": "torn')       # a crash inside a write
        assert ledger.seal(p) is True and ledger.seal(p) is False
        ledger.append(p, [line(rec, 4, 5)])
        lines, bad = ledger.read(p)
        assert [l["sentences"] for l in lines] == [[0, 1], [2, 3], [4, 5]] and len(bad) == 1

    def test_a_line_whose_id_does_not_match_is_bad(self, tmp_path, rec):
        p = str(tmp_path / "m.jsonl")
        with open(p, "w") as f:                       # written by something else than append (it refuses them)
            for l in (line(rec, 0, 1, moment_id="0" * 20), line(rec, 0, 1, scores={"quotable": 9})):
                f.write(json.dumps(l) + "\n")
        lines, bad = ledger.read(p)
        assert lines == [] and len(bad) == 2

    def test_append_refuses_a_bad_line_and_writes_nothing(self, tmp_path, rec):
        """Integrator (non-blocking): a None title or channel id was written, then rejected by every reader."""
        p = str(tmp_path / "m.jsonl")
        with pytest.raises(ValueError, match="title missing"):
            ledger.append(p, [line(rec, 0, 1), line(rec, 2, 3, title=None)])
        assert not os.path.exists(p) or os.path.getsize(p) == 0

    def test_append_closes_a_torn_tail_left_by_a_failed_write_in_a_live_process(self, tmp_path, rec):
        """Integrator (non-blocking): seal() ran only at start, so after ENOSPC / EIO mid-run the next append's first
        line was glued to the torn tail and lost."""
        p = str(tmp_path / "m.jsonl")
        ledger.append(p, [line(rec, 0, 1)])
        with open(p, "a") as f:
            f.write('{"schema": "pp.moment/1", "moment_id": "torn')
        ledger.append(p, [line(rec, 2, 3), line(rec, 4, 5)])           # no seal() in between
        lines, bad = ledger.read(p)
        assert [l["sentences"] for l in lines] == [[0, 1], [2, 3], [4, 5]] and len(bad) == 1


class TestAdapter:
    def read(self, tmp_path, lines, **kw):
        p = str(tmp_path / "m.jsonl")
        ledger.append(p, lines)
        kw.setdefault("optout", ())
        return ledger.best_unused_moments(p, NOW - timedelta(hours=2), NOW, registry=[H.CHAN],
                                          store_root=os.environ["PP_INGEST_STORE"], **kw)

    def test_the_exclusions_are_never_skipped_by_default(self, tmp_path, rec, monkeypatch):
        """Integrator (non-blocking): registry=None / optout=() skipped the registry and opt-out exclusions. Left out,
        both are now read from their files, and an unreadable opt-out list refuses the read (law L-j)."""
        from pipeline.ingest import watch
        p = str(tmp_path / "m.jsonl")
        ledger.append(p, [line(rec)])
        root = os.environ["PP_INGEST_STORE"]
        monkeypatch.setattr(watch, "registry", lambda: ([H.CHAN], [H.CHAN]))
        monkeypatch.setattr(watch, "optouts", lambda: ({H.CHAN["channel_id"]}, None))
        out, rep = ledger.best_unused_moments(p, NOW - timedelta(hours=2), NOW, store_root=root)
        assert out == [] and rep["excluded"] == {"channel opted out": 1}
        monkeypatch.setattr(watch, "registry", lambda: ([], []))
        monkeypatch.setattr(watch, "optouts", lambda: (set(), None))
        out, rep = ledger.best_unused_moments(p, NOW - timedelta(hours=2), NOW, store_root=root)
        assert out == [] and rep["excluded"] == {"channel not enabled in the registry": 1}
        monkeypatch.setattr(watch, "optouts", lambda: (set(), "optout.json: malformed"))
        with pytest.raises(ValueError, match="refused"):
            ledger.best_unused_moments(p, NOW - timedelta(hours=2), NOW, registry=[H.CHAN])

    def test_must_pass_a_clean_moment(self, tmp_path, rec):
        out, rep = self.read(tmp_path, [line(rec)])
        assert len(out) == 1 and rep["excluded"] == {}

    @pytest.mark.parametrize("over,why", [
        ({"risk": ["ad_read"]}, "hard exclusion flag (L-u)"),
        ({"risk": ["accusation", "price_prediction"]}, "hard exclusion flag (L-u)"),
        ({"flags_ext": {"altcoin": True}}, "altcoin or not about Bitcoin"),
        ({"flags_ext": {"about_bitcoin": False}}, "altcoin or not about Bitcoin"),
        ({"flags_ext": None}, "altcoin or not about Bitcoin"),
        ({"speaker": {"turn_change_inside": True}}, "speaker change inside (caption marker)"),
        ({"source": {"duplicate_of": "abcdefghijk"}}, "re-upload"),
        ({"channel_id": "UC" + "z" * 22}, "channel not enabled in the registry"),
        ({"published_at": (NOW + timedelta(hours=1)).isoformat()}, "publish time not measured or in the future"),
    ])
    def test_must_fail_exclusions_are_pre_applied(self, tmp_path, rec, over, why):
        out, rep = self.read(tmp_path, [line(rec, **over)])
        assert out == [] and rep["excluded"] == {why: 1}

    def test_delivered_and_opted_out_are_excluded(self, tmp_path, rec):
        l = line(rec)
        out, rep = self.read(tmp_path, [l], delivered_ids=[l["moment_id"]])
        assert out == []
        out, rep = self.read(tmp_path, [line(rec)], optout={H.CHAN["channel_id"]})
        assert out == []

    def test_since_and_the_window(self, tmp_path, rec):
        old_mined_recent_pub = line(rec, 0, 1, mined={"at": (NOW - timedelta(hours=30)).isoformat()})
        old_both = line(rec, 2, 3, mined={"at": (NOW - timedelta(hours=30)).isoformat()},
                        published_at=(NOW - timedelta(hours=80)).isoformat())
        out, _ = self.read(tmp_path, [old_mined_recent_pub, old_both])
        assert [l["sentences"] for l in out] == [[0, 1]]

    def test_a_moment_expires_12_h_after_its_video_was_published_and_its_row_stays(self, tmp_path, rec):
        """Rulings 76 + 77: a moment is usable only within 12 h of its video's publish time, then never again; the
        expired row is not deleted from the ledger (the receipt that it was said and seen)."""
        fresh = line(rec, 0, 1, published_at=(NOW - timedelta(hours=11, minutes=59)).isoformat())
        gone = line(rec, 2, 3, published_at=(NOW - timedelta(hours=12)).isoformat())
        out, rep = self.read(tmp_path, [fresh, gone])
        assert [l["sentences"] for l in out] == [[0, 1]]
        assert rep["excluded"] == {"expired (rulings 76 + 77: 12 h after its video's publish time)": 1}
        assert rep["expiry_h"] == 12 and len(ledger.read(str(tmp_path / "m.jsonl"))[0]) == 2

    def test_the_earlier_of_the_recorded_expiry_and_the_publish_time_plus_12_h_counts(self, tmp_path, rec):
        """Fail closed: a recorded expires_at later than the rule's never extends a moment's life."""
        pub = NOW - timedelta(hours=3)
        late_field = line(rec, 0, 1, published_at=(NOW - timedelta(hours=13)).isoformat(),
                          expires_at=(NOW + timedelta(hours=5)).isoformat())
        early_field = line(rec, 2, 3, published_at=pub.isoformat(), expires_at=(NOW - timedelta(minutes=1)).isoformat())
        ok = line(rec, 4, 5, published_at=pub.isoformat(), expires_at=(pub + timedelta(hours=12)).isoformat())
        out, rep = self.read(tmp_path, [late_field, early_field, ok])
        assert [l["sentences"] for l in out] == [[4, 5]]
        assert rep["excluded"] == {"expired (rulings 76 + 77: 12 h after its video's publish time)": 2}

    def test_the_latest_line_wins_and_order_is_by_rank(self, tmp_path, rec):
        a1 = line(rec, 0, 1, scores={"quotable": 1})
        a2 = line(rec, 0, 1, scores={"quotable": 5})
        b = line(rec, 2, 3, scores={"quotable": 3})
        out, _ = self.read(tmp_path, [a1, b, a2])
        assert [l["sentences"] for l in out] == [[0, 1], [2, 3]] and out[0]["scores"]["quotable"] == 5

    def test_contract_drift_is_rederived_and_fails_closed(self, tmp_path, rec):
        ts = __import__("pipeline.ingest.config", fromlist=["ts"]).ts()
        if ts.canonical_transcript(rec["video_id"]) is None:
            os.makedirs(ts._vdir(rec["video_id"]), exist_ok=True)
            ts._store(rec)
        good = line(rec, 0, 1, mined={"contract_fp": "old-definitions"})
        tampered = line(rec, 2, 3, mined={"contract_fp": "old-definitions"}, text="Bitcoin to a million tomorrow.")
        out, rep = self.read(tmp_path, [good, tampered])
        assert [l["sentences"] for l in out] == [[0, 1]] and rep["drift_checked"] == 2
        assert list(rep["excluded"]) == ["contract drift: text differs under the current definitions"]

    def test_a_drifted_line_without_its_record_is_excluded(self, tmp_path):
        r, _ = H.caption_record(H.vid())                      # never stored
        out, rep = self.read(tmp_path, [line(r, mined={"contract_fp": "x"})])
        assert out == [] and "record not found" in list(rep["excluded"])[0]


def test_the_bounded_read_returns_exactly_what_a_full_read_returns(tmp_path, rec):
    """Grok c1 P0 (measured: 16-25 s per 100k lines): the adapter seeks past lines mined before
    min(since, now - horizon) - 1 day; its answer must equal the contract's rule applied to every line (rulings 76 +
    77: the horizon is 12 h and a moment 12 h past its video's publish time is never returned)."""
    import random
    p = str(tmp_path / "m.jsonl")
    rng = random.Random(7)
    bases = [line(rec, a, a + 1) for a in range(11)]
    lines = []
    for day in range(30, -1, -1):
        for j in range(400):
            at = NOW - timedelta(days=day, minutes=rng.randint(0, 30))     # in order by day, interleaved by minutes
            b = dict(rng.choice(bases))
            b.update(mined=dict(b["mined"], at=at.isoformat()), scores=dict(b["scores"], quotable=rng.randint(0, 5)),
                     published_at=(at - timedelta(hours=rng.randint(1, 100))).isoformat())
            lines.append(b)
    ledger.append(p, lines)
    since = NOW - timedelta(hours=6)
    fast, rep = ledger.best_unused_moments(p, since, NOW, registry=[H.CHAN], optout=(), store_root=None)
    expect = {}
    for l in ledger.read(p)[0]:                           # the contract's rule over every line, latest line wins
        at, pub = datetime.fromisoformat(l["mined"]["at"]), datetime.fromisoformat(l["published_at"])
        if at >= since or pub >= NOW - timedelta(hours=config.EXPIRY_H):
            expect[l["moment_id"]] = l
    expect = {k: l for k, l in expect.items() if not _expired(l)}
    assert expect and {(l["moment_id"], l["scores"]["quotable"]) for l in fast} == \
        {(l["moment_id"], l["scores"]["quotable"]) for l in expect.values()}
    assert ledger.offset_before(p, NOW - timedelta(days=5)) > 0 and rep["lines"] < len(lines) / 3


@pytest.mark.parametrize("disorder_h", [1, 20])
def test_the_bounded_read_is_exact_while_lines_are_out_of_order_by_less_than_its_margin(tmp_path, rec, disorder_h):
    """Freeze audit c1 (qwen, P0 'bisection over an unsorted file'): lines written before the append-time stamp are out
    of mined.at order by at most one mining pass; the reader's one day of margin keeps the bounded read exact for any
    disorder under a day (here up to 20 h), for every `since`."""
    import random
    p = str(tmp_path / "m.jsonl")
    rng = random.Random(disorder_h)
    bases = [line(rec, a, a + 1) for a in range(11)]
    lines = []
    for hour in range(30 * 24, -1, -1):
        for _ in range(12):
            at = NOW - timedelta(hours=hour) - timedelta(minutes=rng.randint(0, disorder_h * 60))
            b = dict(rng.choice(bases))
            b.update(mined=dict(b["mined"], at=at.isoformat()), scores=dict(b["scores"], quotable=rng.randint(0, 5)),
                     published_at=(at - timedelta(hours=rng.randint(0, 100))).isoformat())
            lines.append(b)
    ledger.append(p, lines)
    full = ledger.read(p)[0]
    nonempty = 0
    for since_h in (1, 6, 30, 80, 200):
        since = NOW - timedelta(hours=since_h)
        fast, rep = ledger.best_unused_moments(p, since, NOW, registry=[H.CHAN], optout=(), store_root=None)
        expect = {}
        for l in full:
            at, pub = datetime.fromisoformat(l["mined"]["at"]), datetime.fromisoformat(l["published_at"])
            if at >= since or pub >= NOW - timedelta(hours=config.EXPIRY_H):
                expect[l["moment_id"]] = l
        expect = {k: l for k, l in expect.items() if not _expired(l)}
        nonempty += bool(expect)
        assert {(l["moment_id"], l["scores"]["quotable"]) for l in fast} == \
            {(l["moment_id"], l["scores"]["quotable"]) for l in expect.values()}, since_h
    assert nonempty                                   # the comparison was made on returned moments, not only on none


def test_the_service_stamp_puts_the_file_in_mined_at_order(tmp_path, rec):
    """append(stamp=...) writes mined.at under the append lock: whatever the lines carried, the file is ordered."""
    p = str(tmp_path / "m.jsonl")
    clock = iter([NOW - timedelta(minutes=30 - i) for i in range(30)])
    for i in range(10):
        ls = [line(rec, 0, 1, mined={"at": (NOW - timedelta(hours=i)).isoformat()}),
              line(rec, 2, 3, mined={"at": (NOW - timedelta(days=3)).isoformat()})]
        ledger.append(p, ls, stamp=lambda: next(clock).isoformat())
    ats = [datetime.fromisoformat(l["mined"]["at"]) for l in ledger.read(p)[0]]
    assert ats == sorted(ats) and len(set(ats)) == 10


def test_a_line_whose_video_id_is_not_a_youtube_id_is_bad(tmp_path, rec):
    l = line(rec)
    assert ledger.line_problems(dict(l, video_id="../../etc/x")) and not ledger.line_problems(l)
    with pytest.raises(ValueError, match="not a YouTube id"):
        ledger.append(str(tmp_path / "m.jsonl"), [dict(l, video_id="../../etc/x")])


class TestCoverage:
    def test_mined_missed_shorts_and_watcher_misses(self, tmp_path):
        now = 1794470000.0
        q = Q.Queue(str(tmp_path / "q.sqlite"), clock=lambda: now)
        ids = {k: H.vid(k) for k in "MLSNXP"}
        ents = [{"id": ids[k], "title": k, "timestamp": now - 3600, "live_status": None, "duration": 900,
                 "url": f"https://www.youtube.com/watch?v={ids[k]}"} for k in "MLSNX"]
        ents.append({"id": ids["P"], "title": "P", "timestamp": now - 30 * 3600, "live_status": None, "duration": 900,
                     "url": ""})                            # outside 24 h
        fresh = H.vid("F")
        ents.append({"id": fresh, "title": "F", "timestamp": now - 600, "live_status": None, "duration": 900,
                     "url": ""})                            # 10 min old: inside the discovery window
        for k, st in (("M", Q.MINED), ("L", Q.LIVE), ("S", Q.SHORT), ("N", Q.NO_CAPTIONS)):
            q.add_video(ids[k], H.CHAN["channel_id"], k, "uploads_playlist")
            q.set_state(ids[k], st, published_ts=now - 3600, reason="r")
        gate = H.FakeGate(listing={H.CHAN["channel_id"]: {"channel_id": H.CHAN["channel_id"], "entries": ents}})
        rep = coverage.check(q, gate, hours=24, now_ts=now, rss=False, chans=[H.CHAN])
        assert (rep["published"], rep["shorts"], rep["eligible"], rep["mined"]) == (6, 1, 5, 1)
        reasons = {m["video_id"]: m["reason"] for m in rep["missed"]}
        assert "watcher miss" in reasons[ids["X"]] and "live" in reasons[ids["L"]] and "Whisper" in reasons[ids["N"]]
        assert "inside the discovery window" in reasons[fresh]
        assert rep["coverage"] == 0.2 and rep["measured"] is True
        md = coverage.write(rep, str(tmp_path / "cov"))
        assert "coverage 20.0 %" in open(md).read()

    def test_a_failed_listing_is_unmeasured_never_covered(self, tmp_path):
        q = Q.Queue(str(tmp_path / "q.sqlite"))
        rep = coverage.check(q, H.FakeGate(listing={}), hours=24, rss=False, chans=[H.CHAN])
        assert rep["measured"] is False and rep["coverage"] is None and len(rep["unmeasured_channels"]) == 1


def test_a_later_pass_carries_every_earlier_flag_and_the_hook_hint(rec):
    """Ruling 80: the adapter returns a moment's LATEST line, so a hook-pass line (or a re-mine) for a moment the
    ledger already holds carries the union of the earlier flags, either's names_person / altcoin, both's
    about_bitcoin, and the hook hint."""
    first = line(rec, 0, 1, risk=["accusation"], names_person=True, flags_ext={"about_bitcoin": False, "altcoin": False})
    hook = line(rec, 0, 1, risk=["time_sensitive"], role_hint="hook")
    later = line(rec, 0, 1, risk=[])                                   # a re-mine after the hook pass
    other = line(rec, 2, 3, risk=[])
    out = ledger.carry_forward([dict(hook)], [first])
    assert out[0]["risk"] == ["accusation", "time_sensitive"] and out[0]["names_person"] is True
    assert out[0]["flags_ext"] == {"about_bitcoin": False, "altcoin": False} and out[0]["role_hint"] == "hook"
    again = ledger.carry_forward([dict(later), dict(other)], [first, out[0]])
    assert again[0]["role_hint"] == "hook" and again[0]["risk"] == ["accusation", "time_sensitive"]
    assert again[1]["risk"] == [] and "role_hint" not in again[1]
