"""The orchestrator's standing order of 08:15 ET Nov 14, written by the watcher itself (cycles.py): after each cycle
that finds something, line 1 carries each new video (channel, mined yes/no, moments, hooks, seconds from publish to
rows), and (09:02) says so when the last 3 h found nothing Bitcoin."""
import os
from datetime import datetime, timezone

import helpers as H
from pipeline.ingest import config, cycles, spend
from pipeline.ingest import queue as Q

T = datetime(2026, 11, 14, 16, 0, tzinfo=timezone.utc).timestamp()          # 11:00 ET


def queue(tmp_path):
    t = [T]
    q = Q.Queue(str(tmp_path / "q.sqlite"), clock=lambda: t[0])
    q.ensure_channel(H.CHAN)
    return q, t


def mined(q, vid, pub, seen, at, moments, windows, screened, hook_rows=0, spot_rows=None, hook_ts=None,
          state=Q.MINED):
    q.x("UPDATE videos SET state=?, published_ts=?, discovered_ts=?, mined_ts=?, moments=?, windows=?, "
        "windows_screened=?, hook_rows=?, spot_rows=?, hook_ts=? WHERE video_id=?",
        (state, pub, seen, at, moments, windows, screened, hook_rows, spot_rows, hook_ts, vid))


def cycle(q, t, vids, seconds=4.0):
    """One watch cycle that lists `vids` [(video id, state)] as new, as the service records it."""
    for v, st in vids:
        q.add_video(v, H.CHAN["channel_id"], "a title", "uploads_playlist", state=st)
    t[0] += seconds
    q.event("watch_cycle", None, None, cycle="ingest-x", channels=1, new=len(vids), errors=0, seconds=seconds)


def test_a_cycle_that_finds_something_is_reported_video_by_video(tmp_path):
    q, t = queue(tmp_path)
    a, b, c = H.vid("a"), H.vid("b"), H.vid("c")
    cycle(q, t, [(a, Q.SHORT), (b, Q.DISCOVERED), (c, Q.DISCOVERED)])
    mined(q, b, T - 600, T + 1, T + 40, 12, 4, 1, hook_rows=3, spot_rows=1, hook_ts=T + 70)
    mined(q, c, T - 300, T + 2, T + 30, 0, 5, 5, hook_ts=T + 35)
    line = cycles.compose(q, T + 100)
    assert line.startswith("PP-INGEST CYCLES TO 11:01 ET (")                    # its newest change: b's hooks, 11:01
    assert "11:00 ET cycle, 3 new: (1) " in line and f"{a} Test Channel: a Short, never mined (A2), no rows" in line
    assert (f"{b} Test Channel: mined yes 11:00 ET, 12 moments, 3 hooks + 1 spotlights, 640 s publish -> rows (seen "
            "601 s after publish via uploads_playlist, mined 39 s after)") in line
    assert (f"{c} Test Channel: mined yes 11:00 ET, 0 moments, 0 hooks (all 5 window(s) without a Bitcoin term: "
            "screened before any model call); 330 s publish -> mined") in line
    assert "NOTHING BITCOIN" not in line and "\n" not in line                   # b had a Bitcoin term


def test_a_video_still_queued_and_the_hook_pass_pending_are_said(tmp_path):
    q, t = queue(tmp_path)
    a, b = H.vid("a"), H.vid("b")
    cycle(q, t, [(a, Q.DISCOVERED), (b, Q.DISCOVERED)])
    q.x("UPDATE videos SET state=?, reason=? WHERE video_id=?", (Q.UPCOMING, "upcoming (scheduled)", a))
    mined(q, b, T - 60, T + 1, T + 20, 7, 3, 0)
    line = cycles.compose(q, T + 30)
    assert f"{a} Test Channel: mined no, queued (upcoming_waiting: upcoming (scheduled))" in line
    assert f"{b} Test Channel: mined yes 11:00 ET, 7 moments, hook pass pending, 80 s publish -> rows" in line


def test_three_hours_with_nothing_bitcoin_are_said_and_a_window_with_nothing_new_writes_no_line(tmp_path):
    q, t = queue(tmp_path)
    a, b, c = H.vid("a"), H.vid("b"), H.vid("c")
    cycle(q, t, [(a, Q.DISCOVERED), (b, Q.SHORT), (c, Q.DISCOVERED)])
    mined(q, a, T - 60, T + 1, T + 20, 0, 2, 2)
    line = cycles.compose(q, T + 30)
    assert ("NOTHING BITCOIN IN THE LAST 3 H: 3 upload(s) seen (1 Shorts, 1 not mined yet), none of the 1 mined with a "
            "Bitcoin term in any window") in line
    q2, t2 = queue(tmp_path / "other")
    d = H.vid("d")
    cycle(q2, t2, [(d, Q.DISCOVERED)])
    mined(q2, d, T - 60, T + 1, T + 20, 5, 2, 0)
    assert cycles.compose(q2, T + 4 * 3600) is None                    # no cycle ran in the window: no line
    t2[0] = T + 4 * 3600
    q2.event("watch_cycle", None, None, cycle="ingest-y", channels=1, new=0, errors=0, seconds=3.0)
    quiet = cycles.compose(q2, T + 4 * 3600 + 60)                      # a cycle ran and found nothing new: said, at
    assert quiet.startswith("PP-INGEST CYCLES TO 15:00 ET (") and (    # the cycle's own time (not the clock's)
        "none of its 1 cycle(s) found a new upload; NOTHING BITCOIN IN THE LAST 3 H: no new upload in 1 cycle(s); the "
        f"newest with one: {d} Test Channel, seen 11:00 ET Nov 14") in quiet
    assert cycles.compose(q2, T + 4 * 3600 + 600) == quiet             # later, nothing new: the same line


def test_the_cycles_line_sits_after_the_switch_line_and_is_rewritten_only_when_it_changes(tmp_path):
    doc = tmp_path / "STATE.md"
    sw = "09:16 ET: SWITCHED TO PLAN B (TEST) |"
    doc.write_text(sw + "\nmy session line | # title\nbody\n")
    notify = str(tmp_path / "ingest" / "NOTIFY.txt")
    line = "PP-INGEST CYCLES TO 11:01 ET (test): 11:00 ET cycle, 1 new: (1) x"
    spend.write_cycles_notice(line, doc=str(doc), notify_path=notify)
    assert doc.read_text() == f"{sw}\n{line}\nmy session line | # title\nbody\n"
    before = os.stat(doc).st_mtime_ns
    spend.write_cycles_notice(line, doc=str(doc), notify_path=notify)
    assert os.stat(doc).st_mtime_ns == before                          # unchanged: not rewritten
    spend.write_cycles_notice(None, doc=str(doc), notify_path=notify)
    assert doc.read_text() == f"{sw}\nmy session line | # title\nbody\n"
    for bad in ("CYCLES TO 11:01", line + "\nsecond line"):
        try:
            spend.write_cycles_notice(bad, doc=str(doc), notify_path=notify)
            raise AssertionError("accepted a line that is not a cycles line")
        except ValueError:
            pass


def test_no_test_writes_the_real_state_file():
    """conftest redirects config.STATE_DOC for every test (the health loop now writes the cycles line)."""
    real = os.path.join(config.REPO, "docs", "audits", "parallel", "pp-ingest_STATE.md")
    assert os.path.realpath(config.STATE_DOC) != os.path.realpath(real)
