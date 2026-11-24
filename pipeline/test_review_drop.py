#!/usr/bin/env python3
"""The REVIEW DROP (orchestrator order 2026-11-12 '13:06'; law L-j unchanged): a run that is NOT a pass may go to the
approval chat as an engineering review, clearly labelled, beside the release path and never part of it.
must-fail  no GATE_REPORT.json; any content-integrity row (G16, G17, G12, G15, G20, V1) not PASS; 'PASS'-as-verdict,
           'CANDIDATE FOR APPROVAL' or 'approved' wording; a second drop of the same run; and the release path
           (deliver_run / release_auth.authorise) refusing a run that has only a review drop
must-pass  tonight's two droppable rows (G3c, G18 identity by omission): both finals + the note sent, every non-pass
           REQUIRED row listed with its reason, the head first, both sha256, REVIEW_DROP.json written
item 1c    a spotlight's review names its kind first under the head in every text (a text without it: STOP); a
           medley's gains no line
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_review_drop.py"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import release_auth  # noqa: E402
import telegram as T  # noqa: E402


def _video(path, w, h):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate=24:duration=1",
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "1", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", "-c:a", "aac", "-shortest", path], check=True)


class TestReviewDrop(unittest.TestCase):
    def setUp(self):
        self.run = tempfile.mkdtemp(prefix="review_drop_")
        os.makedirs(os.path.join(self.run, "out"))
        os.makedirs(os.path.join(self.run, "vo_audio"))
        _video(os.path.join(self.run, "out", "segment.mp4"), 1920, 1080)
        _video(os.path.join(self.run, "out", "segment_vertical.mp4"), 1080, 1920)
        rows = {fmt: {k: "PASS" for k in release_auth.INVENTORY[fmt]} for fmt in ("16x9", "9x16")}
        for fmt in rows:
            rows[fmt]["G3c_acoustic_tail"] = "FAIL"
            rows[fmt]["G18_word_for_word"] = "FAIL"
        self.report = {"rows": rows, "notes": {"16x9": {}, "9x16": {}},
                       "L-c": {f: {"g3c_failed_edges": [["clip_02", "out"]], "final_proof": {"clip_02": {"out": {
                           "ok": False, "why": "the final's gain is not measurable next to this edge"}}}}
                               for f in ("16x9", "9x16")},
                       "G18": {f: [{"segment": "clip_01", "pass": False, "edges": [],
                                    "identity": [["delete", "it's not you know", ""]]}] for f in ("16x9", "9x16")}}
        self._write("GATE_REPORT.json", self.report)
        self.edl = {"title": "No authority. That's the design.", "caption": "no authority. that's the design.",
                    "hook": {"video_id": "vgsSZ4mAHfQ", "channel": "Saifedean Ammous", "duration": 8.54},
                    "clips": [{"index": 1, "video_id": "c1JGheQBPH4", "channel": "What Bitcoin Did", "duration": 10.34,
                               "selection_lock": {"alternatives": [{"readings": ["think", "mean"]}]}},
                              {"index": 2, "video_id": "wdk5JZ9hPzs", "channel": "Natalie Brunell", "duration": 3.64}],
                    "moments_sources_30s_before": ["https://www.youtube.com/watch?v=vgsSZ4mAHfQ&t=5114s",
                                                   "https://www.youtube.com/watch?v=c1JGheQBPH4&t=2373s",
                                                   "https://www.youtube.com/watch?v=wdk5JZ9hPzs&t=3188s"]}
        self._write("edl.json", self.edl)
        self._write("PROVENANCE.json", {"launch_revision": "59068f44"})
        self._write("vo_audio/VO_MANIFEST.json", {"signoff": {"text": "Big thanks to Saifedean Ammous, What Bitcoin "
                                                                      "Did, and Natalie Brunell for today's clips."}})
        self.sent = []

    def tearDown(self):
        shutil.rmtree(self.run, ignore_errors=True)

    def _write(self, rel, obj):
        with open(os.path.join(self.run, rel), "w") as f:
            json.dump(obj, f)

    def _send(self, kind, path, fields, data=None):
        self.sent.append((kind, path, fields, data))
        return len(self.sent)

    def _refused(self, pattern):
        with self.assertRaisesRegex(RuntimeError, pattern):
            T.review_drop(self.run, send=self._send)
        self.assertEqual(self.sent, [])
        self.assertFalse(os.path.exists(os.path.join(self.run, "REVIEW_DROP.json")))

    def test_ruling_161_visible_sponsor_graphics_are_one_information_line_in_the_note(self):
        """RULING 161 (07:36 ET Nov 24, from PBX): what the pin (the builder's per-segment record) and the render's V1
        saw on screen is ONE plain line in the note, never a flag and never a refusal; the captions stay as they were."""
        pkg = "a" * 64
        self.edl["moments_package_sha256"] = pkg
        self._write("edl.json", self.edl)
        self._write("PINNED_DECISION.json", {"pin": {"moments_package": {"package_sha256": pkg}, "segments": [
            {"channel": "Digital Asset News", "visible_sponsor_graphics": "Kraken sign-up banner; iTrustCapital panel"},
            {"channel": "What Bitcoin Did"}]}})
        self.report["V1"] = {"16x9": {"sponsor_graphics": [{"model": "qwen/qwen3.8-27b", "what": "a Kraken banner"}]},
                             "9x16": {"ok": True}}
        self._write("GATE_REPORT.json", self.report)
        T.review_drop(self.run, send=self._send)
        note = self.sent[-1][2]["text"]
        self.assertEqual([x for x in note.split("\n") if x.startswith(T.SPONSOR_HEAD)],
                         [T.SPONSOR_HEAD + "Digital Asset News: Kraken sign-up banner; iTrustCapital panel; "
                                           "16:9 sheet, qwen3.8-27b: a Kraken banner"])
        self.assertNotIn("REVIEW FLAGS", note)
        vids = [x for x in self.sent if x[0] == "video"]
        self.assertEqual(len(vids), 2)
        for x in vids:
            self.assertNotIn(T.SPONSOR_HEAD, x[2]["caption"])

    def test_ruling_161_nothing_seen_no_line_and_an_unbound_pin_is_said(self):
        self.assertEqual(T.sponsor_lines(self.run, self.edl, self.report), [])
        edl = dict(self.edl, moments_package_sha256="a" * 64)
        self._write("PINNED_DECISION.json", {"pin": {"moments_package": {"package_sha256": "b" * 64},
                                                     "segments": [{"channel": "X", "visible_sponsor_graphics": "Y"}]}})
        self.assertEqual(T.sponsor_lines(self.run, edl, self.report),
                         [T.SPONSOR_HEAD + "the pin record is not this EDL's (not read)"])
        with open(os.path.join(self.run, "PINNED_DECISION.json"), "w") as f:
            f.write("{not json")
        self.assertEqual(T.sponsor_lines(self.run, edl, self.report),
                         [T.SPONSOR_HEAD + "the pin record is not readable (JSONDecodeError)"])

    def test_ruling_93_a_16x9_only_run_drops_its_16x9_alone(self):
        """Ruling 93 as amended: the EDL seals formats ['16x9']: the drop sends the 16:9 final alone (the 9:16 file is
        gone: never read), says so in its caption and note, and judges only the 16:9's rows (a 9:16 content-integrity
        failure does not block it). Must-fail: with both formats the same 9:16 failure refuses the drop."""
        self.edl["formats"] = ["16x9"]
        self._write("edl.json", self.edl)
        self.report["rows"]["9x16"]["G16_sentence_boundary"] = "FAIL"
        self._write("GATE_REPORT.json", self.report)
        os.remove(os.path.join(self.run, "out", "segment_vertical.mp4"))
        rec = T.review_drop(self.run, send=self._send)
        vids = [s for s in self.sent if s[0] == "video"]
        self.assertEqual([os.path.basename(s[1]) for s in vids], ["segment.mp4"])
        self.assertIn(T.SIXTEEN_NINE_ONLY, vids[0][2]["caption"])
        note = self.sent[-1][2]["text"]
        self.assertIn(T.SIXTEEN_NINE_ONLY, note)
        self.assertIn("16:9 sha256", note)
        self.assertNotIn("9:16 sha256", note)
        self.assertEqual(list(rec["sha256"]), ["16x9"])
        self.assertEqual({x[0] for x in rec["nonpass"]}, {"16x9"})

    def test_ruling_93_must_fail_both_formats_refuse_the_same_9x16_failure(self):
        self.report["rows"]["9x16"]["G16_sentence_boundary"] = "FAIL"
        self._write("GATE_REPORT.json", self.report)
        self._refused("9x16 G16_sentence_boundary FAIL")

    def test_ruling_93_malformed_formats_send_nothing(self):
        for bad in (["9x16"], "16x9", None):
            self.edl["formats"] = bad
            self._write("edl.json", self.edl)
            self._refused("formats are unreadable")

    POINT = ("L-s step A refused the moment on re-judgment (Grok, 22:07 ET): CONDITION_OUTSIDE, 'by 45' rests on "
             "~20% returns said after the clip; REFERENT_OUTSIDE, 'now'.")
    WHY9 = "ruling 93 as amended: the 9:16 crop cuts the source's burned captions mid-word"

    def test_ruling_106_b_a_withheld_format_and_a_stated_point_ride_in_every_text(self):
        """Ruling 106 (b): the REVIEW path carries the open integrity point in the caption; a format the integrator
        withholds (ruling 93 as amended) is never read or sent, and its reason is stated. Only the sent format is
        judged (the 9:16's content-integrity failure does not block a 16:9 drop). Must-fail: with no withhold the
        same run sends both finals and no point line exists."""
        self.report["rows"]["9x16"]["G16_sentence_boundary"] = "FAIL"
        self._write("GATE_REPORT.json", self.report)
        os.remove(os.path.join(self.run, "out", "segment_vertical.mp4"))
        rec = T.review_drop(self.run, send=self._send, withhold={"9x16": self.WHY9}, points=[self.POINT])
        vids = [s for s in self.sent if s[0] == "video"]
        self.assertEqual([os.path.basename(s[1]) for s in vids], ["segment.mp4"])
        cap, note = vids[0][2]["caption"], self.sent[-1][2]["text"]
        for t in (cap, note):
            self.assertTrue(t.startswith(T.REVIEW_HEAD), t)
            self.assertIn(T.REVIEW_POINT_HEAD + self.POINT, t)
            self.assertIn(T.WITHHELD_HEAD + "9:16: " + self.WHY9, t)
        self.assertLess(cap.index(self.POINT), cap.index("Not passing"))     # under the head, never trimmed away
        self.assertNotIn("9:16 sha256", note)
        self.assertEqual((rec["withheld"], rec["points"]), ({"9x16": self.WHY9}, [self.POINT]))
        self.assertEqual({x[0] for x in rec["nonpass"]}, {"16x9"})
        self.assertNotIn(T.SIXTEEN_NINE_ONLY, note)                           # not sealed: withheld, said so

    def test_ruling_106_b_must_fail_without_withhold_both_go_and_no_point_line(self):
        rec = T.review_drop(self.run, send=self._send)
        self.assertEqual([os.path.basename(s[1]) for s in self.sent if s[0] == "video"],
                         ["segment.mp4", "segment_vertical.mp4"])
        self.assertNotIn(T.REVIEW_POINT_HEAD, self.sent[-1][2]["text"])
        self.assertEqual((rec["withheld"], rec["points"]), ({}, []))

    def test_ruling_106_b_bad_withholds_and_points_send_nothing(self):
        for kw, pattern in (({"withhold": {"1x1": "x"}}, "withhold names a format"),
                            ({"withhold": {"9x16": " "}}, "withhold names a format"),
                            ({"withhold": {"9x16": "x" * (T.REVIEW_POINT_MAX + 1)}}, "withhold names a format"),
                            ({"withhold": {"9x16": "a", "16x9": "b"}}, "every format withheld"),
                            ({"points": [""]}, "each open point"),
                            ({"points": ["x" * (T.REVIEW_POINT_MAX + 1)]}, "each open point"),
                            ({"points": [7]}, "each open point"),
                            ({"points": ["an earlier verdict passed it"]}, "forbidden wording"),
                            ({"points": [c * T.REVIEW_POINT_MAX for c in "wxyz"]}, "does not fit whole")):
            with self.subTest(kw=kw):
                with self.assertRaisesRegex(RuntimeError, pattern):
                    T.review_drop(self.run, send=self._send, **kw)
                self.assertEqual(self.sent, [])
                self.assertFalse(os.path.exists(os.path.join(self.run, "REVIEW_DROP.json")))

    KIND = getattr(T, "REVIEW_SPOTLIGHT", None)     # None before item 1c: the old code fails on the missing line

    def _shape(self, shape):
        self.edl.update(package_type="moments", package_shape=shape)
        if shape == "spotlight":                    # law L-ab: exactly one segment, the hook
            self.edl["clips"] = []
        self._write("edl.json", self.edl)

    def _texts(self):
        return [s[2]["caption"] for s in self.sent if s[0] == "video"] + [self.sent[-1][2]["text"]]

    def test_item_1c_a_spotlight_review_names_its_kind_first_under_the_head_in_every_text(self):
        """Item 1c (the drop of 3f481f5a never said it was the spotlight format's demonstration): a spotlight's review
        drop names the kind on its own line, first under the head, in both captions and the note, in words the drop's
        wording check lets through (the drop is sent)."""
        self._shape("spotlight")
        rec = T.review_drop(self.run, send=self._send, points=[self.POINT])
        texts = self._texts()
        self.assertEqual(len(texts), 3)
        for t in texts:
            self.assertEqual([x for x in t.split("\n") if x][:3],
                             [T.REVIEW_HEAD, self.KIND, T.REVIEW_POINT_HEAD + self.POINT], t)
        self.assertEqual(rec["status"], "complete")

    def test_item_1c_must_fail_a_medley_review_gains_no_kind_line(self):
        self._shape("medley")
        T.review_drop(self.run, send=self._send)
        for t in self._texts():
            lines = [x for x in t.split("\n") if x]
            self.assertEqual(lines[0], T.REVIEW_HEAD)
            self.assertTrue(lines[1].startswith(("Not passing (required):", "Required rows NOT passing")), lines[1])

    def test_item_1c_a_spotlight_text_without_its_kind_line_sends_nothing(self):
        """The drop checks the texts it is about to send: a spotlight's text that lost the kind line (review_texts
        stubbed to drop it) is a STOP, with nothing sent and no REVIEW_DROP.json."""
        self._shape("spotlight")
        real = T.review_texts

        def lost(*a, **kw):
            caps, note = real(*a, **kw)
            cut = lambda t: "\n".join(x for x in t.split("\n") if x != self.KIND)  # noqa: E731
            return {f: cut(c) for f, c in caps.items()}, cut(note)
        with mock.patch.object(T, "review_texts", lost):
            self._refused("the kind line")

    def test_without_a_gate_report_nothing_is_sent(self):
        os.remove(os.path.join(self.run, "GATE_REPORT.json"))
        self._refused("no GATE_REPORT.json")

    def test_a_failing_content_integrity_row_is_never_dropped(self):
        for row in T.REVIEW_NOT_DROPPABLE:
            with self.subTest(row=row):
                rep = json.loads(json.dumps(self.report))
                rep["rows"]["9x16"][row] = "FAIL"
                self._write("GATE_REPORT.json", rep)
                self._refused(f"content-integrity rows not passing: .*{row}")

    def test_pass_as_verdict_candidate_and_approved_wording_is_refused(self):
        for field, text in (("title", "This cut PASSED review"), ("caption", "CANDIDATE FOR APPROVAL"),
                            ("title", "Approved for launch")):
            with self.subTest(text=text):
                self._write("edl.json", {**self.edl, field: text})
                self._refused("forbidden wording")

    def test_the_two_droppable_rows_are_sent_with_every_row_and_reason_listed(self):
        rec = T.review_drop(self.run, send=self._send)
        kinds = [s[0] for s in self.sent]
        self.assertEqual(kinds, ["video", "video", "message"])
        digests = {f: hashlib.sha256(open(os.path.join(self.run, rel), "rb").read()).hexdigest()
                   for f, rel in T.FINALS.items()}
        for kind, path, fields, data in self.sent[:2]:
            cap = fields["caption"]
            self.assertTrue(cap.startswith(T.REVIEW_HEAD))
            self.assertIn("G3c_acoustic_tail FAIL", cap)
            self.assertIn("G18_word_for_word FAIL", cap)
            self.assertEqual(hashlib.sha256(data).hexdigest(), digests["16x9" if "segment.mp4" in path else "9x16"])
        note = self.sent[2][2]["text"]
        self.assertTrue(note.startswith(T.REVIEW_HEAD))
        for fmt in ("16x9", "9x16"):
            self.assertIn(f"- {fmt} G3c_acoustic_tail FAIL: clip_02 out edge", note)
            self.assertIn(f"- {fmt} G18_word_for_word FAIL: clip_01: the final's decode omits 'it's not you know'", note)
            self.assertIn(digests[fmt], note)
        for part in ("Run review_drop_", "HEAD 59068f44", "Title: No authority.", "&t=2373s",
                     "one unstressed word heard as 'think' or 'mean'", "renderer's template", "(ruling 15)"):
            self.assertIn(part, note)
        saved = json.load(open(os.path.join(self.run, "REVIEW_DROP.json")))
        self.assertEqual([m["message_id"] for m in saved["messages"]], [1, 2, 3])
        self.assertEqual((saved["status"], rec["status"]), ("complete", "complete"))

    def _v1(self, fmt, answers, credits_g15="PASS"):
        """V1 FAIL in `fmt` with one checklist item answered per model as given ({model: (answer, why)})."""
        rep = json.loads(json.dumps(self.report))
        rep["rows"][fmt]["V1_visual_checklist"] = "FAIL"
        rep["rows"][fmt]["G15_credits"] = credits_g15
        self._write("GATE_REPORT.json", rep)
        item = next(iter(answers))
        per = {m: {"rows": {item: {"answer": a, "why": w, "ok": a == "yes"}}} for m, (a, w) in answers[item].items()}
        os.makedirs(os.path.join(self.run, "VERIFY"), exist_ok=True)
        self._write("VERIFY/VERIFICATION.json", {"visual": {fmt: {"ok": False, "per_model": per}}})

    def test_ruling_23_a_v1_split_is_droppable_and_quoted(self):
        self._v1("9x16", {"vertical_speaker_centred": {"qwen/qwen3.8-27b": ("no", "framed off-centre (right side)"),
                                                       "nvidia/nemotron-3.5-super-vl": ("yes", "centred in their frames")}})
        T.review_drop(self.run, send=self._send)
        note = self.sent[-1][2]["text"]
        self.assertIn("9x16 V1_visual_checklist FAIL: split on vertical_speaker_centred", note)
        self.assertIn("qwen/qwen3.8-27b 'no' (\"framed off-centre (right side)\")", note)
        self.assertIn("nvidia/nemotron-3.5-super-vl 'yes' (\"centred in their frames\")", note)

    def test_ruling_23_both_models_no_is_refused(self):
        self._v1("9x16", {"vertical_speaker_centred": {"qwen/qwen3.8-27b": ("no", "off-centre"),
                                                       "nvidia/nemotron-3.5-super-vl": ("no", "off-centre")}})
        self._refused("content-integrity rows not passing: .*V1_visual_checklist.*not a split")

    def test_ruling_23_a_credits_item_with_failed_ring_geometry_is_refused(self):
        self._v1("16x9", {"credits_round_and_match": {"qwen/qwen3.8-27b": ("no", "ring squashed"),
                                                      "nvidia/nemotron-3.5-super-vl": ("yes", "round")}},
                 credits_g15="FAIL")
        self._refused("content-integrity rows not passing: .*G15_credits")

    def test_ruling_23_a_v1_row_with_no_readable_failing_item_is_refused(self):     # cycle-2 F1
        self._v1("9x16", {"watermark_present": {"qwen/qwen3.8-27b": ("yes", "seen"),
                                                "nvidia/nemotron-3.5-super-vl": ("yes", "seen")}})
        self._refused("content-integrity rows not passing: .*no failing item can be read")

    def test_ruling_23_a_boundary_split_is_droppable_and_both_same_is_not(self):    # cycle-2 F2
        rep = json.loads(json.dumps(self.report))
        rep["rows"]["16x9"]["V1_visual_checklist"] = "FAIL"
        self._write("GATE_REPORT.json", rep)
        os.makedirs(os.path.join(self.run, "VERIFY"), exist_ok=True)
        ok_rows = {m: {"rows": {"watermark_present": {"answer": "yes", "ok": True}}}
                   for m in ("qwen/qwen3.8-27b", "nvidia/nemotron-3.5-super-vl")}
        for answers, droppable in (({"qwen/qwen3.8-27b": "yes", "nvidia/nemotron-3.5-super-vl": "no"}, True),
                                   ({"qwen/qwen3.8-27b": "yes", "nvidia/nemotron-3.5-super-vl": "yes"}, False)):
            with self.subTest(answers=answers):
                self.sent.clear()
                if os.path.exists(os.path.join(self.run, "REVIEW_DROP.json")):
                    os.remove(os.path.join(self.run, "REVIEW_DROP.json"))
                self._write("VERIFY/VERIFICATION.json", {"visual": {"16x9": {"ok": False, "per_model": ok_rows,
                            "boundaries": {"ok": False, "cuts": [{"boundary": "clip_01|vo_bridge_01", "ok": False,
                                                                  "answers": answers}]}}}})
                if droppable:
                    T.review_drop(self.run, send=self._send)
                    self.assertIn("split on clip_01|vo_bridge_01", self.sent[-1][2]["text"])
                else:
                    self._refused("not a split")

    MEDLEY_SCRIPT = ("Clips today from Natalie Brunell, What Bitcoin Did, and Stephan Livera. Go follow them for more "
                     "Bitcoin talks. Links below.")
    MEDLEY_DECODE = ("clips today from natalie brunel, whatbitcoindid, and stefan lavera.  go follow them for more bitcoin "
                     "talks.  links below.")

    def _g20(self, fmt, transcript, script, missing, extra=()):
        """The amendment '23:20' fixture: G20 FAIL in `fmt` with the gate's own evidence (GATE_REPORT G20_<fmt>)."""
        rep = json.loads(json.dumps(self.report))
        rep["rows"][fmt]["G20_signoff_names_all"] = "FAIL"
        credited = ["Natalie Brunell", "Stephan Livera", "What Bitcoin Did"]
        rep[f"G20_{fmt}"] = {"transcript": transcript, "credited": credited, "missing": list(missing),
                             "extra": list(extra), "spoken": sorted(set(credited) - set(missing)), "pass": False}
        self._write("GATE_REPORT.json", rep)
        self._write("vo_audio/VO_MANIFEST.json", {"signoff": {"text": script}})

    def test_amendment_a_g20_decoder_spelling_is_droppable_and_both_strings_quoted(self):
        self._g20("9x16", self.MEDLEY_DECODE, self.MEDLEY_SCRIPT, ["Stephan Livera"])
        T.review_drop(self.run, send=self._send)
        note = self.sent[-1][2]["text"]
        self.assertIn("9x16 G20_signoff_names_all FAIL: decoder spelling only: the script says 'Stephan Livera', the "
                      "decoder wrote 'dstefanlavera' (0.77)", note)

    def test_amendment_a_name_absent_from_the_script_is_never_droppable(self):
        self._g20("16x9", self.MEDLEY_DECODE, "Clips today from Natalie Brunell and What Bitcoin Did. Links below.",
                  ["Stephan Livera"])
        self._refused(r"G20_signoff_names_all FAIL \(the sign-off script does not name \['Stephan Livera'\]: never droppable")

    def test_amendment_another_name_in_the_decode_is_not_a_spelling(self):
        self._g20("16x9", self.MEDLEY_DECODE.replace("stefan lavera", "steven lubka"), self.MEDLEY_SCRIPT,
                  ["Stephan Livera"])
        self._refused(r"G20_signoff_names_all FAIL \('Stephan Livera': the decode's closest stretch .* \(< 0.75\): not a spelling")

    def test_amendment_a_name_heard_but_not_credited_is_refused(self):
        self._g20("16x9", self.MEDLEY_DECODE, self.MEDLEY_SCRIPT, ["Stephan Livera"], extra=["Simply Bitcoin"])
        self._refused(r"G20_signoff_names_all FAIL \(credited .* heard but not credited \['Simply Bitcoin'\]")

    def test_amendment_unreadable_g20_evidence_is_refused(self):
        rep = json.loads(json.dumps(self.report))
        rep["rows"]["16x9"]["G20_signoff_names_all"] = "FAIL"
        self._write("GATE_REPORT.json", rep)
        self._refused(r"G20_signoff_names_all FAIL \(the G20 evidence is not readable")

    SPEAKER_PIN = {"segments": [
        {"role": "hook", "channel": "Saifedean Ammous", "speaker": {
            "name": "unknown", "role": None, "line": None, "why": "several people speak and nothing shows which one",
            "people": [{"name": "Saifedean Ammous", "role": "host", "line": "channel: Saifedean Ammous"},
                       {"name": "Jason Hickel", "role": "guest", "line": "a debate with Jason Hickel"}]}},
        {"role": "clip", "channel": "What Bitcoin Did", "speaker": {
            "name": "Patrick Witt", "role": "guest", "line": "title: Patrick Witt on the strategic reserve",
            "people": [{"name": "Patrick Witt", "role": "guest", "line": "title: Patrick Witt on the strategic reserve"}]}},
        {"role": "clip", "channel": "Natalie Brunell", "speaker": {"name": "unknown", "people": []}}]}

    def test_order_0005_the_sealed_speakers_are_in_the_review_note(self):
        self._write("PINNED_DECISION.json", {"pin": self.SPEAKER_PIN})
        T.review_drop(self.run, send=self._send)
        note = self.sent[-1][2]["text"]
        self.assertIn(T.SPEAKERS_HEAD, note)
        self.assertIn("- hook (Saifedean Ammous): speaker unknown (several people speak and nothing shows which one)", note)
        self.assertIn('  named by the source: Jason Hickel (guest): "a debate with Jason Hickel"', note)
        self.assertIn('- clip 1 (What Bitcoin Did): speaker Patrick Witt (guest), evidence: "title: Patrick Witt on the '
                      'strategic reserve"', note)
        self.assertIn("- clip 2 (Natalie Brunell): speaker unknown\n  the source names nobody", note)

    def test_rulings_115_116_a_marked_pin_review_never_carries_a_bar_line(self):
        """The calibrated bars' lines ('hook passed on the calibrated bar', ruling 115 (2); 'line-up passed on the
        calibrated bar', ruling 116) belong to the release caption: a review text never says 'passed'
        (_review_forbidden), so a marked pin's review goes out without them, never refused for them."""
        self.edl["moments_package_sha256"] = "ab" * 32
        self._write("edl.json", self.edl)
        self._write("PINNED_DECISION.json", {"mode": "pinned", "pin": {"moments_package": {
            "type": "moments", "package_sha256": "ab" * 32,
            "hook_bar": {"note": "hook passed on the calibrated bar", "ruling": "115"},
            "lineup_bar": {"note": "line-up passed on the calibrated bar", "ruling": "116"}}}})
        rec = T.review_drop(self.run, send=self._send)
        self.assertEqual(rec["status"], "complete")
        self.assertEqual([s[0] for s in self.sent], ["video", "video", "message"])
        for s in self.sent:
            self.assertNotIn("calibrated bar", json.dumps(s[2]))

    def test_ruling_120_a_pin_marked_on_the_stand_alone_floor_reviews_without_its_line(self):
        """Ruling 120's line ('a clip passed stand-alone on the calibrated bar') also belongs to the release caption
        only: a review goes out without it (never refused for it), whatever other marks the pin carries."""
        self.edl["moments_package_sha256"] = "ab" * 32
        self._write("edl.json", self.edl)
        stand = {"note": "a clip passed stand-alone on the calibrated bar", "floor": 3.0, "scorer_sha":
                 "edd54964a5ab15f4a17d74ecbe40bcbccf2fdf2818df97881e8f7039a4721f53", "segments": [1], "ruling": "119"}
        for extra in ({}, {"hook_bar": {"note": "hook passed on the calibrated bar", "ruling": "115"}}):
            with self.subTest(other_marks=sorted(extra)):
                self.sent = []
                done = os.path.join(self.run, "REVIEW_DROP.json")       # one drop per run: the next case starts clean
                if os.path.exists(done):
                    os.remove(done)
                self._write("PINNED_DECISION.json", {"mode": "pinned", "pin": {"segments": [{}, {}], "moments_package":
                    dict({"type": "moments", "package_sha256": "ab" * 32, "stand_alone_bar": stand}, **extra)}})
                rec = T.review_drop(self.run, send=self._send)
                self.assertEqual(rec["status"], "complete")
                self.assertEqual([s[0] for s in self.sent], ["video", "video", "message"])
                for s in self.sent:
                    self.assertNotIn("calibrated bar", json.dumps(s[2]))
                    self.assertNotIn("passed stand-alone", json.dumps(s[2]))

    def test_order_0005_a_pin_without_speaker_records_adds_no_block(self):
        T.review_drop(self.run, send=self._send)
        self.assertNotIn(T.SPEAKERS_HEAD, self.sent[-1][2]["text"])

    def test_order_0005_a_huge_speaker_record_is_capped_and_never_blocks_the_drop(self):
        big = {"segments": [{"channel": "Saifedean Ammous", "speaker": {"name": "unknown", "why": "w" * 5000, "people": [
            {"name": f"Person {i}", "line": "x" * 500} for i in range(40)]}}]}
        self._write("PINNED_DECISION.json", {"pin": big})
        T.review_drop(self.run, send=self._send)
        note = self.sent[-1][2]["text"]
        block = note[note.index(T.SPEAKERS_HEAD):]
        self.assertIn("- (truncated)", block)
        self.assertLessEqual(len(note), T.TEXT_MAX)

    def test_order_0005_the_publish_kit_carries_the_sealed_speakers(self):
        self._write("PINNED_DECISION.json", {"pin": self.SPEAKER_PIN})
        kit = T.publish_kit(self.run)
        self.assertIn(T.SPEAKERS_HEAD, kit)
        self.assertLess(kit.index(T.SPEAKERS_HEAD), kit.index("FIRST COMMENT:"))
        self.assertIn("speaker Patrick Witt (guest)", kit)

    def test_a_review_drop_never_authorises_release_and_is_not_repeated(self):
        T.review_drop(self.run, send=self._send)
        ok, why, _ = release_auth.authorise(self.run)
        self.assertFalse(ok)
        with self.assertRaisesRegex(RuntimeError, "not authorised for release"):
            T.deliver_run(self.run, send=self._send)
        with self.assertRaisesRegex(RuntimeError, "already review-dropped"):
            T.review_drop(self.run, send=self._send)
        self.assertEqual(len(self.sent), 3)                              # nothing more was sent


if __name__ == "__main__":
    unittest.main()
