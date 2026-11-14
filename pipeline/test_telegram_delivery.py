#!/usr/bin/env python3
"""Delivery contract (mission 4a / DEC-8; red-team 2026-11-11 A): telegram.deliver_run sends ONLY a run that
release_auth.authorise passes, captioned 'HOLD FOR APPROVAL - all release gates passed, no waivers'; a run that
is not authorised sends NOTHING (no REVIEW ONLY drop). Every payload is checked before the first send; each file's
digest is checked again right before it is sent; every message is checkpointed, a rerun resumes without
duplicates, an unknown outcome is never resent automatically, a complete drop is never repeated. Both aspects at
real dimensions; safe frames named in the 9:16 caption; the publishing kit closes the release drop. No network:
the sender is injected. Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_telegram_delivery.py"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)

import release_auth as RA  # noqa: E402
import telegram as TG  # noqa: E402
from test_release_auth import edit_json, make_run, passing_rows  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="tg_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def deliver(self, rd, option=None, fail_at=None, exc=None, sheets=True):
        sent = []

        def send(kind, path, fields, data=None):
            if fail_at is not None and len(sent) == fail_at:
                raise exc
            if kind != "message":                       # exactly the attested bytes are uploaded
                rel = {"segment.mp4": "out/segment.mp4", "segment_vertical.mp4": "out/segment_vertical.mp4"}.get(
                    os.path.basename(path), "qa/" + os.path.basename(path))
                self.assertEqual(hashlib.sha256(data).hexdigest(),
                                 json.load(open(os.path.join(rd, "ATTESTATION.json")))["files"][rel])
            sent.append((kind, os.path.basename(path), fields))
            return len(sent)
        rec = TG.deliver_run(rd, option=option, send=send, sheets=sheets)
        return rec, sent


class TestAuthorisedDrop(Base):
    def test_an_authorised_run_goes_out_in_both_aspects_with_sheets_and_kit(self):
        rd = make_run(self.tmp)
        rec, sent = self.deliver(rd)
        vids = [s for s in sent if s[0] == "video"]
        self.assertEqual([(s[1], s[2]["width"], s[2]["height"]) for s in vids],
                         [("segment.mp4", 1920, 1080), ("segment_vertical.mp4", 1080, 1920)])
        for s in vids:
            self.assertTrue(s[2]["caption"].startswith(TG.HOLD_OK), s[2]["caption"])
        self.assertEqual([(s[0], s[1]) for s in sent if s[0] not in ("video", "message")],
                         [("photo", "contact_sheet_16x9.jpg"), ("photo", "contact_sheet_9x16.jpg")])
        self.assertEqual(sent[-1][0], "message")
        written = json.load(open(os.path.join(rd, "TELEGRAM_DELIVERY.json")))
        self.assertEqual(written["status"], "complete")
        self.assertTrue(written["authorised"])
        self.assertEqual([m["format"] for m in written["messages"] if "format" in m], ["16x9", "9x16"])

    def test_the_caption_carries_the_duration_and_the_vertical_names_its_safe_frames(self):
        edl = json.load(open(os.path.join(make_run(self.tmp, attest=False), "edl.json")))
        shot = {"start": 0.0, "end": 9.4, "class": "screen", "flagged": True}
        edl["hook"]["vertical_layout"] = {"shots": [shot], "flagged": True}
        rd = make_run(self.tmp, edl=edl)
        _, sent = self.deliver(rd)
        self.assertIn(" s", [l for l in sent[0][2]["caption"].split("\n") if "1920x1080" in l][0])
        vert = [s for s in sent if s[1] == "segment_vertical.mp4"][0][2]["caption"]
        self.assertIn("9:16 SAFE FRAME hook (Yahoo Finance): layout=screen 0.00-9.40 s", vert)

    def test_monitoring_rows_are_reported_in_the_caption_not_deciding(self):
        rows = passing_rows()
        rows["16x9"]["G1_voice"] = "FAIL"
        _, sent = self.deliver(make_run(self.tmp, rows=rows))
        first = sent[0][2]["caption"].split("\n")[0]
        self.assertEqual(first, TG.HOLD_OK + " | 1 MONITORING check(s) NOT passed (not release-deciding)")
        self.assertIn("Monitoring (reported, not release-deciding): G1_voice FAIL", sent[0][2]["caption"])

    def test_an_option_is_labelled_first_and_carries_no_kit(self):
        rd = make_run(self.tmp)
        _, sent = self.deliver(rd, option="B", sheets=False)
        self.assertTrue(sent[0][2]["caption"].startswith("OPTION B (transition choice)"), sent[0][2]["caption"])
        self.assertEqual([s[0] for s in sent], ["video", "video"])

    def test_the_release_drop_ends_with_the_publishing_kit(self):
        # orchestrator 2026-11-11 15:30: a suggested title, a description crediting and linking every source,
        # and the first-comment line "credits:" + every creator's @handle, a line break, the orange heart alone
        _, sent = self.deliver(make_run(self.tmp))
        kit = sent[-1][2]["text"]
        self.assertIn("SUGGESTED TITLE: Bitcoin price dip", kit)
        self.assertIn("- Yahoo Finance @YahooFinance: https://www.youtube.com/@YahooFinance", kit)
        self.assertIn("- Natalie Brunell @nataliebrunell: https://www.youtube.com/@nataliebrunell", kit)
        self.assertTrue(kit.endswith("credits: @YahooFinance @nataliebrunell\n\U0001F9E1"), kit[-80:])


    def test_a_moments_kit_carries_the_sealed_title_and_caption(self):
        # 17:12 (pin 0c68b589, Telegram 67848): the kit suggested 'bitcoin | Pulse Check' from the EDL's topic, not
        # the ONE sealed title and caption the moments EDL carries (law L-t)
        edl = json.load(open(os.path.join(make_run(self.tmp, attest=False), "edl.json")))
        edl.update(topic="bitcoin", headline=None, title="No single owner controls the bitcoin network",
                   caption="bitcoin is not a partisan issue. no ceo or committee keeps its rules.")
        _, sent = self.deliver(make_run(self.tmp, edl=edl))
        kit = sent[-1][2]["text"]
        self.assertIn("SUGGESTED TITLE: No single owner controls the bitcoin network | Pulse Check", kit)
        self.assertIn("DESCRIPTION:\nbitcoin is not a partisan issue. no ceo or committee keeps its rules. Every clip",
                      kit)
        self.assertNotIn("SUGGESTED TITLE: bitcoin", kit)


class TestNothingIsSentUnlessAuthorised(Base):
    def refused(self, rd, label, needle):
        """Nothing sent, for THIS reason (cycle 2 F8: any RuntimeError is not enough)."""
        sent = []
        with self.assertRaises(RuntimeError, msg=label) as cm:
            TG.deliver_run(rd, send=lambda k, p, f, data=None: sent.append(k) or 1)
        self.assertEqual(sent, [], label)
        self.assertIn(needle, str(cm.exception), label)

    def test_a_failing_row_a_waiver_string_an_incomplete_pack_or_no_attestation_send_nothing(self):
        for fmt, row, v in (("9x16", "G4s_layout_truth", "FAIL"), ("16x9", "G8_sharpness", "FLAG/LIMITED (soft)"),
                            ("16x9", "G17_onset_tail", "PASS (L-c)")):
            rows = passing_rows()
            rows[fmt][row] = v
            self.refused(make_run(self.tmp, rows=rows), f"{row} = {v}", f"{fmt} {row}")
        rd = make_run(self.tmp, attest=False)
        edit_json(os.path.join(rd, "VERIFY", "VERIFICATION.json"), lambda d: d.__setitem__("complete", False))
        RA.attest(rd, {"ok": True, "why": []})
        self.refused(rd, "incomplete pack", "pack incomplete")
        self.refused(make_run(self.tmp, attest=False), "no attestation", "no readable attestation")

    def test_a_final_changed_after_authorisation_is_refused_before_it_is_sent(self):
        rd = make_run(self.tmp)
        real = TG._plan

        def plan_then_tamper(*a, **k):                  # the 9:16 changes between authorise and its send
            p = real(*a, **k)
            with open(os.path.join(rd, "out", "segment_vertical.mp4"), "ab") as f:
                f.write(b"\0")
            return p
        TG._plan = plan_then_tamper
        try:
            sent = []
            with self.assertRaises(RuntimeError) as cm:
                TG.deliver_run(rd, send=lambda k, p, f, data=None: sent.append(os.path.basename(p)) or 1)
        finally:
            TG._plan = real
        self.assertIn("changed after it was authorised", str(cm.exception))
        self.assertEqual(sent, [])                      # every payload is verified before the FIRST send (F7)

    def test_wrong_dimensions_or_an_oversize_final_stop_before_the_first_send(self):
        rd = make_run(self.tmp, attest=False)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=24:d=1",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                        os.path.join(rd, "out", "segment.mp4")], check=True)
        m = os.path.join(rd, "GATE_REPORT.json")
        edit_json(m, lambda d: d["measured_files"].__setitem__("out/segment.mp4", RA.sha256(os.path.join(rd, "out", "segment.mp4"))))
        RA.attest(rd, {"ok": True, "why": []})
        self.refused(rd, "1280x720 16:9 final", "16x9 final is 1280x720")
        rd = make_run(self.tmp)
        saved = TG.VIDEO_MAX_BYTES
        TG.VIDEO_MAX_BYTES = 10
        try:
            self.refused(rd, "oversize final", "Bot API limit")
        finally:
            TG.VIDEO_MAX_BYTES = saved

    def test_a_headline_number_the_video_does_not_say_stops_the_drop(self):
        """Claude-gates T13 / GPT audit batch 16 #7: numbers with their sign and unit, against G18's readings of the
        final's audio (the fixture's readings say 'Bitcoin fell to 74,000 dollars today.')."""
        edl = json.load(open(os.path.join(make_run(self.tmp, attest=False), "edl.json")))
        for head in ("Bitcoin falls to $74,000 on November 8th",      # E-FAIL-038's invented date
                     "Bitcoin falls 74,000 percent",                   # a percentage the video states as dollars
                     "Bitcoin -74,000"):                               # a sign the video does not say
            edl["headline"] = head
            self.refused(make_run(self.tmp, edl=edl), head, "the headline states numbers the video does not say")
        for head in ("Bitcoin falls to $74,000", "Bitcoin falls to 74,000"):
            edl["headline"] = head
            self.assertEqual(TG.headline_numbers_said(make_run(self.tmp, edl=edl)), [], head)
        rd = make_run(self.tmp, edl=dict(edl, headline="Bitcoin falls to $74,000"), attest=False)
        edit_json(os.path.join(rd, "GATE_REPORT.json"), lambda d: d.pop("G18"))
        self.assertEqual(TG.headline_numbers_said(rd), ["74000 dollars"])     # no readings: nothing is said

    def test_a_headline_number_needs_its_subject_and_direction_in_both_formats(self):
        """cycle-2 #8: 'Bitcoin rose ten percent' is not supported by 'Bitcoin fell five percent; gold rose ten
        percent' (wrong asset for the 10, wrong direction), and support in ONE format is not enough."""
        rd = make_run(self.tmp, attest=False)

        def heard(text16, text9):
            def fn(d):
                d["G18"] = {"16x9": [{"segment": "hook", "heard": text16}], "9x16": [{"segment": "hook", "heard": text9}]}
            edit_json(os.path.join(rd, "GATE_REPORT.json"), fn)
        edl = json.load(open(os.path.join(rd, "edl.json")))
        edl["headline"] = "Bitcoin rose ten percent"
        json.dump(edl, open(os.path.join(rd, "edl.json"), "w"))
        heard("Bitcoin fell five percent; gold rose ten percent.", "Bitcoin fell five percent; gold rose ten percent.")
        self.assertEqual(TG.headline_numbers_said(rd), ["10 percent"])
        heard("Bitcoin fell ten percent today.", "Bitcoin fell ten percent today.")
        self.assertEqual(TG.headline_numbers_said(rd), ["10 percent"])        # the opposite direction
        heard("Bitcoin rose ten percent today.", "Something else entirely.")
        self.assertEqual(TG.headline_numbers_said(rd), ["10 percent"])        # one format only
        heard("Today Bitcoin rose 10% on the news.", "Bitcoin rose ten percent today.")
        self.assertEqual(TG.headline_numbers_said(rd), [])


class TestCheckpoint(Base):
    def test_a_refused_send_resumes_without_duplicates(self):
        rd = make_run(self.tmp)
        with self.assertRaises(TG.SendRejected):
            self.deliver(rd, fail_at=1, exc=TG.SendRejected("429 Too Many Requests"))
        rec = json.load(open(os.path.join(rd, "TELEGRAM_DELIVERY.json")))
        self.assertEqual([m["key"] for m in rec["messages"]], ["video:16x9"])
        self.assertEqual(rec["status"], "in_progress")
        _, sent = self.deliver(rd)                      # resumes after the 16:9
        self.assertEqual(sent[0][1], "segment_vertical.mp4")
        self.assertNotIn("segment.mp4", [s[1] for s in sent])
        with self.assertRaises(RuntimeError) as cm:     # a complete drop is never repeated
            self.deliver(rd)
        self.assertIn("already delivered", str(cm.exception))

    def test_an_unknown_outcome_is_never_resent_automatically(self):
        rd = make_run(self.tmp)
        with self.assertRaises(RuntimeError):
            self.deliver(rd, fail_at=2, exc=RuntimeError("STOP: Telegram sendPhoto: outcome unknown (ReadTimeout)"))
        rec = json.load(open(os.path.join(rd, "TELEGRAM_DELIVERY.json")))
        self.assertEqual(rec["unknown"], ["sheet:16x9"])
        with self.assertRaises(RuntimeError) as cm:
            self.deliver(rd)
        self.assertIn("outcome unknown", str(cm.exception))

    def test_a_message_in_flight_at_a_crash_is_never_resent(self):
        """GPT audit (batch 16) #3: the process dies after Telegram accepted a message but before its checkpoint:
        the record carries it IN FLIGHT (written before the request), so the rerun refuses instead of duplicating."""
        rd = make_run(self.tmp)

        class Killed(BaseException):                   # a kill: not an Exception, nothing after it runs
            pass
        with self.assertRaises(Killed):
            self.deliver(rd, fail_at=1, exc=Killed())
        rec = json.load(open(os.path.join(rd, "TELEGRAM_DELIVERY.json")))
        self.assertEqual(rec["in_flight"], "video:9x16")
        with self.assertRaises(RuntimeError) as cm:
            self.deliver(rd)
        self.assertIn("outcome unknown", str(cm.exception))

    def test_one_delivery_at_a_time(self):
        import fcntl
        rd = make_run(self.tmp)
        held = open(os.path.join(rd, "TELEGRAM_DELIVERY.lock"), "w")
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with self.assertRaises(RuntimeError) as cm:
                self.deliver(rd)
            self.assertIn("another delivery", str(cm.exception))
        finally:
            fcntl.flock(held, fcntl.LOCK_UN)
            held.close()

    def test_the_same_finals_are_never_sent_twice_under_another_option(self):
        """cycle-2 #1: the delivery ledger and lock are per RUN, not per option label."""
        rd = make_run(self.tmp)
        self.deliver(rd)
        with self.assertRaises(RuntimeError) as cm:
            self.deliver(rd, option="B", sheets=False)
        self.assertIn("already (partly) sent", str(cm.exception))

    def test_only_an_explicit_refusal_is_a_known_outcome(self):
        """cycle-2 #2: '{}', a mistyped 'ok' or a malformed result is an UNKNOWN outcome (never resent), not a
        refusal; only {'ok': false, 'error_code': int} is a refusal; success needs an integer message id."""
        import types
        from unittest import mock
        import requests
        relay = types.ModuleType("relay")
        relay.get_key = lambda name: "X-" + name

        class Resp:
            def __init__(self, body):
                self.body = body

            def json(self):
                return self.body
        for body, expect in (({}, RuntimeError), ({"ok": "true", "result": {"message_id": 5}}, RuntimeError),
                             ({"ok": True, "result": {}}, RuntimeError), ({"ok": True, "result": {"message_id": "5"}}, RuntimeError),
                             ({"ok": False}, RuntimeError), ({"ok": False, "error_code": 429, "description": "slow"}, TG.SendRejected)):
            with mock.patch.dict(sys.modules, {"relay": relay}), \
                    mock.patch.object(requests, "post", lambda url, **kw: Resp(body)):
                with self.assertRaises(expect) as cm:
                    TG._send_bot_api("message", "", {"text": "x"})
            if expect is RuntimeError:
                self.assertNotIsInstance(cm.exception, TG.SendRejected, body)
                self.assertIn("outcome unknown", str(cm.exception), body)
        with mock.patch.dict(sys.modules, {"relay": relay}), \
                mock.patch.object(requests, "post", lambda url, **kw: Resp({"ok": True, "result": {"message_id": 77}})):
            self.assertEqual(TG._send_bot_api("message", "", {"text": "x"}), 77)

    def test_metadata_changed_after_authorisation_is_refused(self):
        """cycle-2 #3: the EDL (headline!) and the gate report (G18 readings) are read only from attested bytes."""
        for rel in ("edl.json", "GATE_REPORT.json"):
            rd = make_run(self.tmp)
            real = TG.release_auth.authorise if hasattr(TG, "release_auth") else None
            import release_auth as RA_

            def authorise_then_tamper(run_dir, _rel=rel, _real=RA_.authorise):
                out = _real(run_dir)
                with open(os.path.join(run_dir, _rel), "a") as f:
                    f.write(" ")
                return out
            from unittest import mock
            with mock.patch.object(RA_, "authorise", authorise_then_tamper):
                sent = []
                with self.assertRaises(RuntimeError) as cm:
                    TG.deliver_run(rd, send=lambda k, p, f, data=None: sent.append(k) or 1)
            self.assertIn("changed after it was authorised", str(cm.exception))
            self.assertEqual(sent, [], rel)

    def test_the_sender_never_puts_the_token_in_an_error(self):
        import types
        from unittest import mock
        relay = types.ModuleType("relay")
        relay.get_key = lambda name: "SECRET-" + name
        import requests

        def boom(url, **kw):
            raise requests.ConnectionError(f"HTTPSConnectionPool: Max retries exceeded with url: {url}")
        with mock.patch.dict(sys.modules, {"relay": relay}), mock.patch.object(requests, "post", boom):
            with self.assertRaises(RuntimeError) as cm:
                TG._send_bot_api("message", "", {"text": "x"})
        self.assertNotIn("SECRET", str(cm.exception))
        self.assertIn("outcome unknown", str(cm.exception))


class TestLimits(unittest.TestCase):
    def test_caption_fits_including_its_marker(self):
        self.assertEqual(len(TG._fit("x" * 5000, TG.CAPTION_MAX)), TG.CAPTION_MAX)
        self.assertEqual(TG._fit("short", TG.CAPTION_MAX), "short")

    def test_photo_limits_at_their_boundaries(self):
        """Audit M1: size (PHOTO_MAX_BYTES), width + height (10000) and aspect ratio (20) boundaries."""
        from unittest import mock
        from PIL import Image
        tmp = tempfile.mkdtemp(prefix="photo_")
        self.addCleanup(shutil.rmtree, tmp, True)

        def img(w, h):
            p = os.path.join(tmp, f"{w}x{h}.jpg")
            Image.new("RGB", (w, h)).save(p)
            return p
        self.assertTrue(TG._photo_ok(img(5000, 5000)))                      # w + h == 10000
        self.assertFalse(TG._photo_ok(img(5000, 5001)))
        self.assertTrue(TG._photo_ok(img(4000, 200)))                       # ratio == 20
        self.assertFalse(TG._photo_ok(img(4001, 200)))
        p = img(100, 100)
        with mock.patch("os.path.getsize", return_value=TG.PHOTO_MAX_BYTES):
            self.assertTrue(TG._photo_ok(p))
        with mock.patch("os.path.getsize", return_value=TG.PHOTO_MAX_BYTES + 1):
            self.assertFalse(TG._photo_ok(p))
        bad = os.path.join(tmp, "truncated.jpg")
        open(bad, "wb").write(b"\xff\xd8\xff")                          # not an image: document, not a crash
        self.assertFalse(TG._photo_ok(bad))

    def test_the_legacy_entry_point_is_gone(self):
        with self.assertRaises(RuntimeError) as cm:
            TG.send_telegram_preview("/tmp/whatever")
        self.assertIn("removed", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
