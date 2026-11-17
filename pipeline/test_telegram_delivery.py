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

    def test_ruling_93_a_16x9_only_run_sends_its_16x9_alone_and_says_so(self):
        """Ruling 93 as amended: a run whose EDL seals formats ['16x9'] sends the 16:9 final and its sheet ALONE (its
        9:16 failed V1 and its file is gone: it is never read). Must-fail: the same run without sealed formats sends
        nothing (not authorised)."""
        from test_release_auth import sealed_run, vertical_fails, ABSENT
        rd = sealed_run(self.tmp, ["16x9"], vertical_fails(), no_vertical=True)
        RA.attest(rd, {"ok": True, "why": []})
        rec, sent = self.deliver(rd)
        vids = [s for s in sent if s[0] == "video"]
        self.assertEqual([(s[1], s[2]["width"], s[2]["height"]) for s in vids], [("segment.mp4", 1920, 1080)])
        self.assertIn(TG.SIXTEEN_NINE_ONLY, vids[0][2]["caption"])
        self.assertEqual([(s[0], s[1]) for s in sent if s[0] not in ("video", "message")],
                         [("photo", "contact_sheet_16x9.jpg")])
        self.assertEqual([m["format"] for m in rec["messages"] if "format" in m], ["16x9"])
        rd = sealed_run(self.tmp, ABSENT, vertical_fails())
        RA.attest(rd, {"ok": True, "why": []})
        with self.assertRaisesRegex(RuntimeError, "not authorised for release"):
            self.deliver(rd)
        self.assertFalse(os.path.exists(os.path.join(rd, "TELEGRAM_DELIVERY.json")))

    def test_ruling_93_an_edl_whose_formats_differ_from_the_attestation_sends_nothing(self):
        from test_release_auth import sealed_run, vertical_fails
        rd = sealed_run(self.tmp, ["16x9"], vertical_fails())
        RA.attest(rd, {"ok": True, "why": []})
        att = json.load(open(os.path.join(rd, "ATTESTATION.json")))
        snap = TG.snapshot(rd, att)
        snap["edl"]["formats"] = ["16x9", "9x16"]           # the plan re-reads the formats from the verified EDL
        with self.assertRaisesRegex(RuntimeError, "not the attested"):
            TG._plan(rd, None, True, att, snap)

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


NOTE_115 = "hook passed on the calibrated bar"      # ruling 115 (2)'s words, as PBX must read them
NOTE_116 = "line-up passed on the calibrated bar"   # ruling 116's (the builder's lineup_bar.NOTE)
MARK = {"note": NOTE_115, "bar": "BAR-TEXT scroll>=3 alone>=4 setup>=3", "floors": {"scroll": 3, "alone": 4, "setup": 3},
        "calibration_sha256": "f" * 64, "ruling": "115"}
LINEUP = {"note": NOTE_116, "bar": "LINEUP-TEXT", "floors": {"clips_alone": {"clips": 3}, "coherence": {
    "clips": 3, "vo_point": 3}}, "calibration_sha256": "e" * 64, "ruling": "116"}
BOTH = {"hook_bar": MARK, "lineup_bar": LINEUP}
NOTE_119 = "a clip passed stand-alone on the calibrated bar"   # ruling 120's words (the builder's stand_alone_bar note)
STAND = {"note": NOTE_119, "floor": 3.0, "scorer_sha": "edd54964a5ab15f4a17d74ecbe40bcbccf2fdf2818df97881e8f7039a4721f53",
         "segments": [2], "ruling": "119"}
PKG = "ab" * 32


MAJORITY = "word check settled by two of three readings"     # ruling 131 (A)'s words, as PBX must read them
CURRENCY = "currency format"                                 # ruling 131 (B)'s


class TestLockLines(Base):
    """RULING 131 (orchestrator 08:25 ET Nov 17): a lock settled by two of the three readings ((A): the render lock's
    own record, or a pin segment sealed with an attested rule naming ruling 131 (A)) or a currency symbol read as
    formatting ((B): the render lock's currency_format) is MARKED in the release note, in plain words, when used."""

    def run_with(self, hook_lock=None, clip_lock=None, segments=None, record_sha=PKG, edl_sha=PKG, raw=None):
        edl = json.load(open(os.path.join(make_run(self.tmp, attest=False), "edl.json")))
        edl["moments_package_sha256"] = edl_sha
        if hook_lock is not None:
            edl["hook"]["selection_lock"] = hook_lock
        if clip_lock is not None:
            edl["clips"][0]["selection_lock"] = clip_lock
        rd = make_run(self.tmp, edl=edl)
        if segments is not None or raw is not None:
            with open(os.path.join(rd, "PINNED_DECISION.json"), "w") as f:
                f.write(raw if raw is not None else json.dumps(
                    {"mode": "pinned", "pin": {"segments": segments,
                                               "moments_package": {"type": "moments", "package_sha256": record_sha}}}))
        return rd

    def marks(self, rd):
        _, sent = self.deliver(rd)
        vids = [s for s in sent if s[0] == "video"]
        self.assertEqual(len(vids), 2)
        out = [[l for l in s[2]["caption"].split("\n") if l in (MAJORITY, CURRENCY)] for s in vids]
        self.assertEqual(out[0], out[1])                              # every format's note alike
        return out[0], vids[0][2]["caption"].split("\n")

    def test_a_render_lock_settled_two_of_three_says_so_under_the_run_line(self):
        rd = self.run_with(clip_lock={"text": "x", "adjudication": {"rule": "ruling 131 (A) (orchestrator 2026-11-17 "
                                                                            "'08:25')", "pairs": []}})
        got, lines = self.marks(rd)
        self.assertEqual(got, [MAJORITY])
        self.assertEqual(lines[2], MAJORITY)

    def test_a_pin_sealed_on_two_of_three_says_so(self):
        rd = self.run_with(segments=[{"approved_text": "x"},
                                     {"attested": {"rule": "ruling 72 + ruling 131 (A) (orchestrator 08:25 ET Nov 17)"}}])
        self.assertEqual(self.marks(rd)[0], [MAJORITY])

    def test_currency_format_says_so_after_the_majority_line(self):
        rd = self.run_with(hook_lock={"text": "x", "currency_format": [["", "dollars"]]},
                           clip_lock={"text": "y", "adjudication": {"rule": "ruling 131 (A) x"}})
        self.assertEqual(self.marks(rd)[0], [MAJORITY, CURRENCY])

    def test_no_line_when_neither_is_used(self):
        rd = self.run_with(clip_lock={"text": "x", "adjudication": {"rule": "ruling 17 (orchestrator 2026-11-12 "
                                                                            "'10:20')"}},
                           segments=[{"attested": {"rule": "ruling 72 + ruling 84 (20:41 Nov 13): adopt_spoken"}}])
        self.assertEqual(self.marks(rd)[0], [])

    def test_a_sealed_pin_that_is_not_the_edls_stops(self):
        rd = self.run_with(segments=[{"attested": {"rule": "ruling 72 + ruling 131 (A)"}}], record_sha="cd" * 32)
        sent = []
        with self.assertRaisesRegex(RuntimeError, "ruling 131's marks: the sealed pin"):
            TG.deliver_run(rd, send=lambda kind, path, fields, data=None: sent.append(kind) or len(sent))
        self.assertEqual(sent, [])

    def test_an_unreadable_attested_record_stops(self):
        rd = self.run_with(segments=[{"attested": "ruling 131 (A)"}])
        sent = []
        with self.assertRaisesRegex(RuntimeError, "ruling 131's marks: the pin record cannot say"):
            TG.deliver_run(rd, send=lambda kind, path, fields, data=None: sent.append(kind) or len(sent))
        self.assertEqual(sent, [])

class TestBarLines(Base):
    """Rulings 115 (2) / 116 (orchestrator 13:24 ET Nov 15; the builder's Q3 on ruling 106's default, 15:54): a package
    sealed on a calibrated bar (the hook's, the line-up's) says so in the Telegram note, one plain line per mark. The
    pin carries each mark in moments_package (outside the seal); the run's PINNED_DECISION.json (pinned.prepare) holds
    that pin and is not an attested file, so a mark counts only for the package the attested EDL was built from."""

    def marked_run(self, marks=BOTH, record_sha=PKG, edl_sha=PKG, topic=None, raw=None):
        edl = json.load(open(os.path.join(make_run(self.tmp, attest=False), "edl.json")))
        if edl_sha is not None:
            edl["moments_package_sha256"] = edl_sha
        if topic:
            edl["topic"] = topic
        rd = make_run(self.tmp, edl=edl)
        mp = dict({"type": "moments", "package_sha256": record_sha}, **marks)
        with open(os.path.join(rd, "PINNED_DECISION.json"), "w") as f:
            f.write(raw if raw is not None else json.dumps({"mode": "pinned", "pin": {"moments_package": mp}}))
        return rd

    def refused(self, rd, needle):
        sent = []
        with self.assertRaisesRegex(RuntimeError, needle):
            TG.deliver_run(rd, send=lambda kind, path, fields, data=None: sent.append(kind) or len(sent))
        self.assertEqual(sent, [])                                    # nothing reached the chat
        self.assertFalse(os.path.exists(os.path.join(rd, "TELEGRAM_DELIVERY.json")))

    def test_a_marked_pin_says_so_in_one_plain_line_per_mark_under_the_run_line(self):
        rd = self.marked_run()
        _, sent = self.deliver(rd)
        vids = [s for s in sent if s[0] == "video"]
        self.assertEqual(len(vids), 2)
        for s in vids:                                                # every video's note, each format
            lines = s[2]["caption"].split("\n")
            self.assertEqual(lines[2:4], [NOTE_115, NOTE_116], lines)  # head, run line, the hook's, the line-up's
            self.assertEqual([l for l in lines if "calibrated bar" in l], [NOTE_115, NOTE_116])
            for words in ("BAR-TEXT", "LINEUP-TEXT", "clips_alone"):    # never a mark's own words
                self.assertNotIn(words, s[2]["caption"])
        for s in sent:
            if s[0] != "video":                                        # lines in the note: not the sheets or kit
                self.assertNotIn("calibrated bar", json.dumps(s[2]))
        written = json.load(open(os.path.join(rd, "TELEGRAM_DELIVERY.json")))
        self.assertEqual([[l for l in m["caption"].split("\n") if "calibrated bar" in l]
                          for m in written["messages"] if "format" in m], [[NOTE_115, NOTE_116]] * 2)

    def test_each_mark_is_read_on_its_own(self):
        for marks, want in (({"hook_bar": MARK}, [NOTE_115]), ({"lineup_bar": LINEUP}, [NOTE_116])):
            with self.subTest(marks=sorted(marks)):
                _, sent = self.deliver(self.marked_run(marks=marks))
                lines = sent[0][2]["caption"].split("\n")
                self.assertEqual([l for l in lines if "calibrated bar" in l], want)
                self.assertEqual(lines[2], want[0])
                self.assertTrue(lines[3].startswith("Story: "), lines)

    def test_ruling_119_the_stand_alone_floor_mark_is_one_more_plain_line_after_the_bars(self):
        for marks, want in ((dict(BOTH, stand_alone_bar=STAND), [NOTE_115, NOTE_116, NOTE_119]),
                            ({"stand_alone_bar": STAND}, [NOTE_119]),
                            ({"hook_bar": MARK, "stand_alone_bar": STAND}, [NOTE_115, NOTE_119])):
            with self.subTest(marks=sorted(marks)):
                _, sent = self.deliver(self.marked_run(marks=marks))
                vids = [s for s in sent if s[0] == "video"]
                self.assertEqual(len(vids), 2)
                for s in vids:
                    lines = s[2]["caption"].split("\n")
                    self.assertEqual(lines[2:2 + len(want)], want, lines)
                    self.assertTrue(lines[2 + len(want)].startswith("Story: "), lines)
                    self.assertEqual(s[2]["caption"].count(NOTE_119), 1)
                    self.assertNotIn("edd54964", s[2]["caption"])             # never the mark's own fields
                for s in sent:
                    if s[0] != "video":
                        self.assertNotIn(NOTE_119, json.dumps(s[2]))
        for bad in ({"note": "stand-alone affirmed"}, dict(STAND, note=NOTE_116), None, NOTE_119):
            with self.subTest(bad=bad):
                self.refused(self.marked_run(marks=dict(BOTH, stand_alone_bar=bad)),
                             r"STOP: calibrated bar marks.*stand_alone_bar is not ruling 119's mark")
        self.refused(self.marked_run(marks={"stand_alone_bar": STAND}, record_sha="cd" * 32), r"not the attested EDL's")

    def test_the_lines_survive_a_caption_cut_whole(self):
        rd = self.marked_run(topic="Bitcoin " * 300)                   # the story alone is past CAPTION_MAX
        _, sent = self.deliver(rd)
        cap = sent[0][2]["caption"]
        self.assertTrue(cap.endswith("...(see GATE_REPORT)"), cap[-40:])
        self.assertLessEqual(len(cap), TG.CAPTION_MAX)
        self.assertEqual(cap.split("\n")[2:4], [NOTE_115, NOTE_116])

    def test_no_mark_or_no_pin_record_no_line(self):
        for rd in (self.marked_run(marks={}), make_run(self.tmp)):     # an unmarked pin; an auto run (no record)
            _, sent = self.deliver(rd)
            for s in sent:
                self.assertNotIn("calibrated bar", json.dumps(s[2]))

    def test_a_mark_that_is_not_its_rulings_sends_nothing(self):
        bad = ({"note": "hook passed"}, {"note": NOTE_115.upper()}, {"note": NOTE_115 + " (and approved)"}, {"bar": "x"},
               None, NOTE_115, [NOTE_115], {}, {"note": "line-up passed"})
        for key, swapped in (("hook_bar", {"note": NOTE_116}), ("lineup_bar", {"note": NOTE_115})):
            for mark in bad + (swapped,):                              # the other mark's sentence is not this one's
                with self.subTest(key=key, mark=mark, alone=False):    # beside a valid other mark
                    self.refused(self.marked_run(marks=dict(BOTH, **{key: mark})),
                                 rf"STOP: calibrated bar marks.*{key} is not ruling 11")
            with self.subTest(key=key, alone=True):                    # a bad mark alone
                self.refused(self.marked_run(marks={key: None}), rf"STOP: calibrated bar marks.*{key} is not ruling 11")

    def test_a_mark_on_another_package_sends_nothing(self):
        for marks in (BOTH, {"hook_bar": MARK}, {"lineup_bar": LINEUP}):
            with self.subTest(marks=sorted(marks)):
                self.refused(self.marked_run(marks=marks, record_sha="cd" * 32), r"not the attested EDL's")
        self.refused(self.marked_run(record_sha=None, edl_sha=None), r"not the attested EDL's")   # no digest at all
        self.refused(self.marked_run(record_sha="", edl_sha=""), r"not the attested EDL's")

    def test_an_unreadable_pin_record_sends_nothing(self):
        for raw in ("{not json", '{"mode": "pinned"}', '{"pin": []}', '{"pin": null}', "[]"):
            with self.subTest(raw=raw):
                self.refused(self.marked_run(raw=raw),                   # since rulings 136 / 137 the pin's
                             r"STOP: calibrated bar marks \(rulings 115 \(2\) / 116 / 119\): the pin record cannot say"
                             r"|the pin record is unreadable")                # review flags fail it at authorise


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
