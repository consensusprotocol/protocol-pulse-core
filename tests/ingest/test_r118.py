"""tests/ingest/test_r118.py: the orchestrator's 10:50 ET order of Nov 16.

(1) The pipeline's own transcript (the main tree's transcript ingest, READ ONLY) is taken before any caption download
    and when a VOD lists no English captions; a record failing a check never is; a caption 429 stops the captions
    alone (the gate is tested in test_watch_fetch), and the pipeline's own caption breaker stops this ingest's
    downloads too.
(3) The outage clock runs on the watcher's OWN state file: another session's deadline misses never move it.
(4) The self-check: videos waiting and nothing mined for 30 minutes, on STATE line 1 and acted on.
Ruling 118's chain and ruling 119 (3) are checked on the real config in test_providers and test_signal.
"""
import hashlib
import json
import os
import shutil
import types
from datetime import datetime, timezone

import pytest

import helpers as H
from pipeline.ingest import config, fetch, service, spend, stall
from pipeline.ingest import queue as Q

NOW = 1794470000.0          # 2026-11-12 ~08:33 UTC
MODULE = "/home/ultron/worktrees/pp-selectid/pipeline/heimdall_health.py"     # the builder's, read only


@pytest.fixture
def q(tmp_path):
    return Q.Queue(str(tmp_path / "q.sqlite"), clock=lambda: NOW)


def add(q, v, **kw):
    q.add_video(v, H.CHAN["channel_id"], "Bitcoin test video", "uploads_playlist", **kw)
    return q.video(v)


def pipeline_record(v, method="whisper", tamper=None, name=None, raw=None):
    """A record of the pipeline's own transcript ingest in this test's pipeline store (conftest: fetch.PIPELINE_STORE)."""
    rec, _ = H.caption_record(v)
    rec = dict(rec, transcript_method=method, transcript_model="test model")
    if tamper:
        tamper(rec)
    d = os.path.join(fetch.PIPELINE_STORE, v)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name or f"transcript.{method.split(':')[0]}.json")
    with open(p, "w") as f:
        f.write(raw if raw is not None else json.dumps(rec, indent=1))
    return p, rec


def downloads(monkeypatch, status="throttled"):
    """Every caption download this ingest would make, answered `status` (none should be made where a test says so)."""
    ts, made = config.ts(), []
    monkeypatch.setattr(ts, "fetch_captions", lambda meta, work: (made.append(meta["video_id"]), (status, None))[1])
    return made


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def staged(v, method="whisper"):
    return os.path.join(config.ts()._vdir(v), f"transcript.{method}.json")


def attempts(v):
    p = os.path.join(config.ts()._vdir(v), "attempts.jsonl")
    return [json.loads(x) for x in open(p)] if os.path.exists(p) else []


# ── (1) the pipeline's own transcript ──

def test_the_pipelines_own_transcript_is_taken_byte_for_byte_and_no_caption_is_downloaded(q, monkeypatch):
    v = H.vid("W")
    src, rec = pipeline_record(v)
    before = sha(src)
    made = downloads(monkeypatch)
    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
    row = q.video(v)
    assert made == [] and row["transcript_method"] == "whisper" and row["transcript_sha256"] == rec["transcript_sha256"]
    assert sha(staged(v)) == before == sha(src)                       # the bytes the pipeline wrote; its file untouched
    assert config.ts().canonical_transcript(v)["transcript_sha256"] == rec["transcript_sha256"]
    meta = json.load(open(os.path.join(config.ts()._vdir(v), "meta.json")))
    assert meta["written_by"] == "pipeline.ingest.fetch" and meta["captions_auto_en"] == ["en", "en-orig"]
    a = [x for x in attempts(v) if x.get("step") == "transcript"]
    assert a and a[-1]["status"] == "taken_from_pipeline_store" and a[-1]["source"] == src
    assert [e["video_id"] for e in q.rows("SELECT video_id FROM events WHERE kind='pipeline_transcript'")] == [v]
    assert row["next_at"] == NOW                                     # due to the miner at once


def test_a_vod_without_english_captions_takes_the_pipelines_transcript(q, monkeypatch):
    """BLOy6SetrUs (Yahoo Finance, Nov 16): no English captions on YouTube, a Whisper record in the pipeline's store."""
    made = downloads(monkeypatch)
    a, b = H.vid("N"), H.vid("N")
    pipeline_record(a)
    gate = H.FakeGate(probes={x: H.probe_json(x, timestamp=NOW - 3600, automatic_captions={}, title=f"Episode {x}")
                              for x in (a, b)})
    assert fetch.process(q, gate, add(q, a), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
    assert fetch.process(q, gate, add(q, b), H.CHAN, set(), now_ts=NOW) == Q.CAPTIONS_PENDING   # none there: waits
    assert made == [] and q.video(a)["transcript_method"] == "whisper"


def _tamper_text(r):
    r["segments"][0]["text"] += " (edited)"


def _other_channel(r):
    r["channel_id"] = "UC" + "z" * 22


def _other_video(r):
    r["video_id"] = "zzzzzzzzzzz"


def _empty(r):
    r["segments"] = []
    r["transcript_sha256"] = config.ts().segments_sha256([])


@pytest.mark.parametrize("how", ["text", "channel", "video", "name", "empty", "garbage"])
def test_a_record_failing_any_check_is_never_taken(q, monkeypatch, how):
    v = H.vid("F")
    kw = {"text": dict(tamper=_tamper_text), "channel": dict(tamper=_other_channel),
          "video": dict(tamper=_other_video), "name": dict(name="transcript.yt_auto.json"),
          "empty": dict(tamper=_empty), "garbage": dict(raw="{not json")}[how]
    pipeline_record(v, **kw)
    made = downloads(monkeypatch)
    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.CAPTIONS_PENDING
    assert made == [v] and not os.path.exists(staged(v)) and not os.path.exists(staged(v, "yt_auto"))
    assert fetch.pipeline_transcript(v, H.CHAN["channel_id"]) is None


def test_the_best_record_by_the_stores_rank_is_taken_and_one_already_here_is_kept(q, monkeypatch):
    v = H.vid("B")
    pipeline_record(v, method="yt_auto:en-orig")
    src, rec = pipeline_record(v, method="whisper")
    assert fetch.pipeline_transcript(v, H.CHAN["channel_id"])[0] == src
    downloads(monkeypatch)
    os.makedirs(os.path.dirname(staged(v)), exist_ok=True)
    shutil.copyfile(src, staged(v))                                  # taken before (an earlier try): kept, not copied
    os.chmod(staged(v), 0o444)
    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
    assert q.video(v)["transcript_method"] == "whisper" and not os.path.exists(staged(v, "yt_auto"))


def test_a_copy_that_differs_from_the_record_checked_is_never_linked_in(q, monkeypatch):
    v = H.vid("K")
    pipeline_record(v)
    real = shutil.copyfile

    def swap(a, b):                                                  # the file changed between the check and the copy
        real(a, b)
        r = json.load(open(b))
        r["segments"][0]["text"] = "swapped"
        json.dump(r, open(b, "w"))
    monkeypatch.setattr(fetch.shutil, "copyfile", swap)
    made = downloads(monkeypatch)
    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.CAPTIONS_PENDING
    assert made == [v] and not os.path.exists(staged(v))
    assert [x["status"] for x in attempts(v) if x.get("step") == "transcript"] == ["pipeline_store_copy_refused"]
    assert not [f for f in os.listdir(config.ts()._vdir(v)) if f.endswith(".tmp")]


@pytest.mark.parametrize("probe,state", [(dict(media_type="short", duration=58), Q.SHORT),
                                         (dict(live_status="is_live", media_type="livestream", duration=None,
                                               release_timestamp=NOW - 1800), Q.LIVE),
                                         (dict(live_status="is_upcoming", release_timestamp=NOW + 3600,
                                               duration=None), Q.UPCOMING)])
def test_a_short_a_live_or_an_upcoming_stream_is_never_given_a_transcript(q, monkeypatch, probe, state):
    v = H.vid("S")
    pipeline_record(v)
    downloads(monkeypatch)
    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600, **probe)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == state
    assert not os.path.exists(staged(v)) and q.video(v)["transcript_method"] is None


def test_while_the_pipelines_caption_breaker_is_open_no_download_is_tried_here(q, monkeypatch):
    """Both ingests download captions from this one machine: a 429 the pipeline's ingest was given stops this one's
    downloads too (its breaker file, read only); a closed or unreadable one does not."""
    v = H.vid("P")
    made = downloads(monkeypatch)
    os.makedirs(os.path.dirname(fetch.PIPELINE_CIRCUIT), exist_ok=True)
    with open(fetch.PIPELINE_CIRCUIT, "w") as f:
        json.dump({"open_until": NOW + 900, "reason": "HTTP 429 on x"}, f)
    gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.CAPTIONS_PENDING
    row = q.video(v)
    assert made == [] and row["reason"].startswith("captions throttled") and row["next_at"] == NOW + 600
    assert "the pipeline's own caption breaker is open" in attempts(v)[-1]["why"]
    for body, written, tried in (('{"open_until": %f}' % (NOW - 1), NOW - 60, True),   # closed
                                 ("{broken", NOW - 60, False),     # being written now (only a 429 writes it): open
                                 ("{broken", NOW - 3600, True)):   # broken and old: never stops the captions for good
        with open(fetch.PIPELINE_CIRCUIT, "w") as f:
            f.write(body)
        os.utime(fetch.PIPELINE_CIRCUIT, (written, written))
        n = len(made)
        q.x("UPDATE videos SET next_at=0, state=?", (Q.CAPTIONS_PENDING,))
        assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW) == Q.CAPTIONS_PENDING
        assert len(made) == n + int(tried), (body, written)
    assert made == [v, v]


def test_inside_the_moments_life_a_video_without_captions_is_looked_at_every_30_minutes():
    inside, outside = NOW - 3600, NOW - (config.EXPIRY_H + 1) * 3600
    assert [fetch._caption_retry_at(NOW, inside, n) - NOW for n in range(6)] == [600, 1200, 1800, 1800, 1800, 1800]
    assert [fetch._caption_retry_at(NOW, outside, n) - NOW for n in range(6)] == [600, 1200, 2400, 4800, 7200, 7200]
    assert fetch._caption_retry_at(NOW, None, 3) - NOW == 4800


# ── (3) the outage clock: the watcher's own file ──

@pytest.fixture
def own(monkeypatch, tmp_path):
    """A service wired to a copy of the builder's module whose shared STATE is a file of this test (never the real
    one), with no state path given: the watcher's default."""
    if not os.path.exists(MODULE):
        pytest.skip("the builder's module is not at its path")
    src = open(MODULE).read()
    shared = tmp_path / "SHARED_HEIMDALL_HEALTH.json"
    mod = tmp_path / "hh_copy.py"
    mod.write_text(src + f"\nSTATE = {str(shared)!r}\n")
    p = config.paths()
    for k in ("ingest", "moments"):
        shutil.rmtree(p[k], ignore_errors=True)
    doc = tmp_path / "STATE.md"
    doc.write_text("# STATE\nbody\n")
    monkeypatch.setattr(config, "STATE_DOC", str(doc))
    from test_signal import probe_cfg, T0
    t, made = [T0], []

    def make():
        cfg = probe_cfg(chain=("hv_p1", "hv_p2"))
        cfg["backends"]["hv1"] = {"kind": "openai_compat", "vendor": "hv", "model": "model-hv1", "enabled": True}
        cfg["backends"]["local"] = {"kind": "openai_compat", "vendor": "lv", "model": "model-local", "enabled": True}
        for r in ("mine", "hook", "flagcheck", "judge"):
            cfg["roles"][r]["chain"] = ["hv1", "local"]
        cfg["spend_meter"]["backend"] = "hv1"
        cpath = tmp_path / "providers.json"
        cpath.write_text(json.dumps(cfg))
        b = {x: H.FakeBackend(x, fn=lambda p: "OK") for x in ("hv1", "local", "hv_p1", "hv_p2")}
        s = service.Service(providers_path=str(cpath), backends=b, gate=H.FakeGate(), log=lambda m: None,
                            keyring=__import__("pipeline.ingest.providers", fromlist=["Keyring"]).Keyring("/x"),
                            sleep=lambda x: None, clock=lambda: t[0], signal_module=str(mod))
        made.append(s)
        return s, b
    yield make, t, shared, doc, T0
    for s in made:
        s.close()


def test_another_sessions_running_clock_never_moves_the_watchers_own(own):
    """The false outages of Nov 14 (09:16, 10:12 ET): the builder's deadline misses started the clock of the ONE shared
    file and the watcher announced its switch. Now the shared file may say a clock has run 20 minutes (and even
    plan_b): the watcher reads and writes only its own file, which no call of its own has failed on."""
    make, t, shared, doc, T0 = own
    iso = lambda x: datetime.fromtimestamp(x, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    shared.write_text(json.dumps({"mode": "heimdall_first", "last_answer_utc": iso(T0 - 3600),
                                  "failing_since_utc": iso(T0 - 1200), "last_probe_utc": None, "probe_streak": 0,
                                  "failing_families": ["builders"], "switches": [], "notes": 5}))
    before = sha(shared)
    s, b = make()
    hs = s.hsig
    assert hs.state_path == config.paths()["signal_state"] != hs.hh.STATE == str(shared)
    for _ in range(3):
        hs.tick(wait=True)
        t[0] += 31
    assert sha(shared) == before                                     # never read as ours, never written
    if os.path.exists(hs.state_path):                                # (the module writes its file at a first note)
        own_state = json.load(open(hs.state_path))
        assert own_state["mode"] == "heimdall_first" and not own_state.get("failing_since_utc")
    assert hs.mode in (None, "heimdall_first") and "SWITCHED TO PLAN B" not in doc.read_text()
    assert b["hv_p1"].calls == [] and b["hv_p2"].calls == []          # no failure of its own: no probe either
    hs.noted({"backend": "hv1", "kind": "timeout", "role": "mine"})  # its own failed call starts its own clock
    hs.tick(wait=True)
    own_state = json.load(open(hs.state_path))
    assert len(b["hv_p1"].calls) == 1 and own_state["failing_since_utc"] is None      # probed, answered: reset
    assert sha(shared) == before


# ── (4) the self-check ──

def waiting(q, v, state, reason, discovered, next_at=NOW + 3600, published=None):
    q.add_video(v, H.CHAN["channel_id"], "t", "rss")
    q.x("UPDATE videos SET state=?, reason=?, discovered_ts=?, next_at=?, published_ts=? WHERE video_id=?",
        (state, reason, discovered, next_at, published, v))


def mined(q, v, at):
    q.add_video(v, H.CHAN["channel_id"], "t", "rss")
    q.x("UPDATE videos SET state=?, mined_ts=?, discovered_ts=?, published_ts=? WHERE video_id=?",
        (Q.MINED, at, at - 600, at - 900, v))


def test_a_stall_is_found_only_when_something_waits_and_nothing_was_mined_for_30_minutes(q):
    mined(q, "m0000000001", NOW - 7200)
    assert stall.check(q, NOW)["stalled"] is False                                   # nothing waits
    waiting(q, "w0000000001", Q.UPCOMING, "upcoming", NOW - 5000)
    waiting(q, "w0000000002", Q.LIVE, "is_live", NOW - 5000)
    waiting(q, "w0000000003", Q.CAPTIONS_PENDING, "captions throttled (HTTP 429; ...)", NOW - 20 * 3600,
            published=NOW - 20 * 3600)                                               # outside its moments' life
    assert stall.check(q, NOW)["stalled"] is False
    waiting(q, "w0000000004", Q.CAPTIONS_PENDING, "captions throttled (HTTP 429; ...)", NOW - 600)
    chk = stall.check(q, NOW)
    assert chk["stalled"] is False and chk["since"] == NOW - 600                     # it came in 10 minutes ago
    assert stall.check(q, NOW + 1200)["stalled"] is True                             # 30 minutes on: a stall
    mined(q, "m0000000002", NOW + 900)
    assert stall.check(q, NOW + 1200)["stalled"] is False                            # mined 5 minutes ago


def test_the_stall_line_says_what_each_waits_on_and_the_act_makes_them_due_now(q):
    mined(q, "m0000000001", NOW - 7200)
    waiting(q, "w0000000001", Q.CAPTIONS_PENDING, "captions throttled (HTTP 429; ...)", NOW - 2400)
    waiting(q, "w0000000002", Q.CAPTIONS_PENDING, "captions throttled (HTTP 429; ...)", NOW - 2000)
    waiting(q, "w0000000003", Q.PROBE_RETRY, "rate_limited: yt-dlp breaker open for 389 s", NOW - 2000)
    waiting(q, "w0000000004", Q.CAPTIONS_PENDING, "VOD without English captions yet", NOW - 1900)
    waiting(q, "w0000000005", Q.MINING, None, NOW - 1900, next_at=NOW + 50)          # in flight: never touched
    chk = stall.check(q, NOW)
    assert chk["stalled"] and chk["since"] == NOW - 2400 and len(chk["waiting"]) == 5
    assert stall.act(q, chk, NOW) == 4
    nxt = {r["video_id"]: r["next_at"] for r in q.rows("SELECT video_id, next_at FROM videos")}
    assert [nxt[f"w000000000{i}"] for i in range(1, 6)] == [NOW] * 4 + [NOW + 50]
    line = stall.line(chk, NOW, NOW, 4)
    assert line.startswith(spend.STALL_PREFIX) and "|" not in line and "\n" not in line
    assert "5 VIDEO(S) WAITING, NOTHING MINED FOR 30 MIN OR MORE: 2 CAPTIONS REFUSED BY YOUTUBE (HTTP 429), " \
           "1 NO ENGLISH CAPTIONS YET, 1 PROBE BEHIND THE YT-DLP BREAKER, 1 TRANSCRIBED, BEING MINED; ACTED" in line
    assert line == stall.line(stall.check(q, NOW + 600), NOW + 600, NOW, 4)          # stable while it lasts


def test_the_watcher_says_the_stall_after_the_batch_spend_acts_every_30_minutes_and_clears_it(q, tmp_path):
    doc = tmp_path / "STATE.md"
    sw = "10:18 ET: MINER OFF THE PAID ROUTE (BACK ON HEIMDALL) |"
    doc.write_text(f"BATCH 3 ingest spend: $0.1637 (CLOSED) | {sw}\nPP-INGEST CYCLES TO 10:34 ET (x)\n# STATE\n")
    (tmp_path / "ingest").mkdir()
    logs, clock = [], [NOW]
    me = types.SimpleNamespace(q=q, p={"notify": str(tmp_path / "ingest" / "NOTIFY.txt")}, log=logs.append,
                               stall_error=None)
    import pipeline.ingest.config as C
    old = C.STATE_DOC
    C.STATE_DOC = str(doc)
    try:
        mined(q, "m0000000001", NOW - 7200)
        waiting(q, "w0000000001", Q.CAPTIONS_PENDING, "captions throttled (HTTP 429; ...)", NOW - 2400)
        q.kv_set("stall_since", repr(NOW - 2400))                   # a record left unreadable (audit r118 c1, qwen):
        q.kv_set("stall_acted", "not a time")                       # acted on, never a crash
        service.Service._stall_notice(me, NOW)
        first, second = doc.read_text().split("\n")[:2]
        segs = first.split(spend.SEP)
        assert segs[0].startswith("BATCH 3") and segs[1].startswith(spend.STALL_PREFIX) and segs[2] == sw
        assert second.startswith("PP-INGEST CYCLES TO") and me.stall_error is None
        assert q.video("w0000000001")["next_at"] == NOW
        q.x("UPDATE videos SET next_at=? WHERE video_id='w0000000001'", (NOW + 5000,))   # tried, put off again
        service.Service._stall_notice(me, NOW + 300)                 # 5 minutes on: no second act
        assert q.video("w0000000001")["next_at"] == NOW + 5000
        service.Service._stall_notice(me, NOW + 1801)                # 30 minutes on: acted again
        assert q.video("w0000000001")["next_at"] == NOW + 1801
        assert len(q.rows("SELECT id FROM events WHERE kind='stall_act'")) == 2
        mined(q, "m0000000002", NOW + 1900)
        service.Service._stall_notice(me, NOW + 1960)
        first = doc.read_text().split("\n")[0]
        assert spend.STALL_PREFIX not in doc.read_text() and first.split(spend.SEP)[1] == sw
        assert q.rows("SELECT COUNT(*) AS n FROM events WHERE kind='stall_over'")[0]["n"] == 1
    finally:
        C.STATE_DOC = old


def test_line_1_holds_the_stall_after_the_batch_spend_and_an_alarm_in_any_hand_edited_order(tmp_path):
    doc, notify = tmp_path / "STATE.md", tmp_path / "ingest" / "NOTIFY.txt"
    st = spend.STALL_PREFIX + "10:05 ET: 1 VIDEO(S) WAITING"
    doc.write_text(f"{st} | ALARM FOR PBX: x. Waiting since 10:00 ET. | BATCH 3 ingest spend: $1 | "
                   "10:12 ET: SWITCHED TO PLAN B (y) |\nPP-INGEST CYCLES TO 10:34 ET (x)\nbody\n")
    spend.write_batch_notice("BATCH 3 ingest spend: $2", doc=str(doc), notify_path=str(notify))
    first = doc.read_text().split("\n")[0].split(spend.SEP)
    assert first == ["BATCH 3 ingest spend: $2", "ALARM FOR PBX: x. Waiting since 10:00 ET.", st,
                     "10:12 ET: SWITCHED TO PLAN B (y) |"]
    for bad in (st + " | x", st + "\nx", "MINING IS FINE"):
        with pytest.raises(ValueError):
            spend.write_stall_notice(bad, doc=str(doc), notify_path=str(notify))
    spend.write_stall_notice(None, doc=str(doc), notify_path=str(notify))
    assert doc.read_text().split("\n")[0].split(spend.SEP) == ["BATCH 3 ingest spend: $2",
                                                               "ALARM FOR PBX: x. Waiting since 10:00 ET.",
                                                               "10:12 ET: SWITCHED TO PLAN B (y) |"]
