#!/usr/bin/env python3
"""The REVIEW DROP (orchestrator order 2026-11-12 '13:06'; law L-j unchanged): a run that is NOT a pass may go to the
approval chat as an engineering review, clearly labelled, beside the release path and never part of it.
must-fail  no GATE_REPORT.json; any content-integrity row (G16, G17, G12, G15, G20, V1) not PASS; 'PASS'-as-verdict,
           'CANDIDATE FOR APPROVAL' or 'approved' wording; a second drop of the same run; and the release path
           (deliver_run / release_auth.authorise) refusing a run that has only a review drop
must-pass  tonight's two droppable rows (G3c, G18 identity by omission): both finals + the note sent, every non-pass
           REQUIRED row listed with its reason, the head first, both sha256, REVIEW_DROP.json written
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_review_drop.py"""
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
