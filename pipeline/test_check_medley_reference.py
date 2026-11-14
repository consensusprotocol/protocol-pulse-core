"""check_medley_reference (orchestrator note 2026-11-12 '23:35'): the PBX-approved L-y medley reproduces with the
current code, and each kind of changed decision fails it. The changes are made on a scratch copy: small files copied,
media linked, the protected reference itself never touched."""
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

import check_medley_reference as C

REF = C.REF


@unittest.skipUnless(os.path.isfile(os.path.join(REF, "PIN.json")), "the medley reference is not on this machine")
class TestMedleyReference(unittest.TestCase):
    def copy(self):
        d = tempfile.mkdtemp(prefix="medley_copy_")
        self.addCleanup(shutil.rmtree, d)
        for n in os.listdir(REF):
            src = os.path.join(REF, n)
            if n == "qa":
                os.mkdir(os.path.join(d, n))
                for q in os.listdir(src):
                    os.symlink(os.path.join(src, q), os.path.join(d, n, q))
            elif os.path.isdir(src):
                os.symlink(src, os.path.join(d, n))
            else:
                shutil.copy(src, os.path.join(d, n))
                os.chmod(os.path.join(d, n), 0o644)
        return d

    def edit(self, d, name, fn):
        p = os.path.join(d, name)
        if os.path.islink(p):
            target = os.readlink(p)
            os.unlink(p)
            shutil.copy(target, p)
            os.chmod(p, 0o644)
        with open(p) as f:
            obj = json.load(f)
        obj = fn(obj) or obj
        with open(p, "w") as f:
            json.dump(obj, f)

    def run_check(self, d, layout=False):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = C.main(d, layout=layout)
        return rc, buf.getvalue()

    def assertChanged(self, d, *reasons, layout=False):        # exit 1 AND for the reason the change made
        rc, out = self.run_check(d, layout)
        self.assertEqual(rc, 1, out)
        for r in reasons:
            self.assertIn(r, out)

    def test_the_reference_reproduces(self):
        rc, out = self.run_check(REF)
        self.assertEqual(rc, 0, out)
        self.assertIn("PULSE MEDLEY REFERENCE: REPRODUCED", out)
        self.assertNotIn("CHANGED", out)

    def test_an_unchanged_copy_reproduces(self):               # positive control for the must-fail copies below
        rc, out = self.run_check(self.copy())
        self.assertEqual(rc, 0, out)

    def test_an_intro_line_fails(self):
        d = self.copy()
        self.edit(d, "edl.json", lambda e: e["vo"].update(intro="Here is what three Bitcoiners said today."))
        self.assertChanged(d, "CHANGED: shape: R11 FAIL", "VO slots (False, [2]) != reference (True, [2])")

    def test_a_bridge_between_clips_fails(self):
        d = self.copy()
        self.edit(d, "edl.json", lambda e: e["vo"]["bridges"].insert(0, {"text": "Now listen.", "after_clip": 1}))
        self.assertChanged(d, "CHANGED: shape: R11 FAIL", "VO slots (False, [2]) != reference (False, [1, 2])")

    def test_a_moved_selection_lock_fails(self):
        d = self.copy()
        self.edit(d, "edl.json", lambda e: e["clips"][0]["selection_lock"].update(i1=e["clips"][0]["selection_lock"]["i1"] + 1))
        self.assertChanged(d, "CHANGED: clip_01: selection lock (51, 111) != reference (51, 112)",
                           "CHANGED: clip_01: cut_in selection lock modified after selection",   # the INPUT moved:
                           "CHANGED: clip_01: cut_out selection lock modified after selection")  # the recomputed cut

    def test_a_moved_cut_fails(self):
        d = self.copy()

        def move(cuts):
            cuts[2]["cut_out"] = round(cuts[2]["cut_out"] + 0.05, 3)
        self.edit(d, "cuts_final.json", move)
        self.assertChanged(d, "CHANGED: clip_02: cut_out 31.56 != reference 31.61")

    def test_a_changed_lead_in_fails(self):
        d = self.copy()
        self.edit(d, "TRANSITIONS.json", lambda t: t["lead_tail"].update(clip_01=[0.5, 0.07]))
        self.assertChanged(d, "CHANGED: clip_01: lead-in / tail (0.01, 0.07) != reference [0.5, 0.07]")

    def test_a_dropped_lead_in_entry_fails(self):
        d = self.copy()
        def drop(t):
            del t["lead_tail"]["clip_02"]
        self.edit(d, "TRANSITIONS.json", drop)
        self.assertChanged(d, "CHANGED: flow: TRANSITIONS.json covers ['clip_01', 'hook']",
                           "CHANGED: clip_02: lead-in / tail (0.04, 0.04) != reference None")

    def test_a_render_junction_the_plan_does_not_place_fails(self):
        d = self.copy()
        self.rewrite_log(d, "Transitions (crossfade): [(0, 6, 'dissolve')]")
        self.assertChanged(d, "CHANGED: 16x9: junctions [] != the render's [(0, 6, 'dissolve')]")

    def test_a_render_log_without_its_transitions_line_fails(self):
        d = self.copy()
        self.rewrite_log(d, "Concat (no transitions line)")
        self.assertChanged(d, "CHANGED: 16x9: the render log has 0 'Transitions' line(s)")

    def rewrite_log(self, d, line):
        p = os.path.join(d, "render_16x9.log")
        with open(p) as f:
            s = f.read()
        self.assertEqual(s.count("Transitions (crossfade): []"), 1)
        with open(p, "w") as f:
            f.write(s.replace("Transitions (crossfade): []", line))

    def test_a_changed_or_dropped_layout_fails(self):           # the hook only: classify is the slow part
        d = self.copy()
        self.edit(d, "VERTICAL_LAYOUT.json", lambda v: {"hook": dict(v["hook"], shots=[
            dict(s, **{"class": "single"}) for s in v["hook"]["shots"]])})
        self.assertChanged(d, "CHANGED: layout reference covers ['hook']",
                           "CHANGED: hook: layout [('stack2', 0.0, 4.67)] != reference [('single', 0.0, 4.67)]",
                           layout=True)

    def test_a_dropped_segment_fails_before_any_zip(self):
        d = self.copy()
        self.edit(d, "PIN.json", lambda p: p.update(segments=p["segments"][:-1]))
        self.assertChanged(d, "CHANGED: segments: EDL 3, PIN 2")

    def test_reordered_pin_segments_are_never_paired_by_position(self):
        d = self.copy()
        self.edit(d, "PIN.json", lambda p: p.update(segments=[p["segments"][0], p["segments"][2], p["segments"][1]]))
        self.assertChanged(d, "CHANGED: clip_01: PIN segment Sjb6lUiL0m4 != EDL c1JGheQBPH4")

    def test_a_transition_style_the_code_does_not_write_fails(self):
        d = self.copy()
        self.edit(d, "TRANSITIONS.json", lambda t: t.update(style="A"))
        self.assertChanged(d, "CHANGED: flow: transition style 'A' != the current code's 'crossfade'")

    def test_the_command_line_reproduces_without_layout(self):     # the path regression.sh step 8 calls
        import subprocess
        import sys
        r = subprocess.run([sys.executable, C.__file__, os.path.relpath(REF, C.REPO), "--no-layout"],   # RELATIVE, as
                           cwd=C.REPO, capture_output=True, text=True, timeout=300)                 # step 8 passes it
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PULSE MEDLEY REFERENCE: REPRODUCED", r.stdout)

    def test_a_missing_reference_is_2(self):
        rc, out = self.run_check(os.path.join(tempfile.gettempdir(), "no_such_medley_reference"))
        self.assertEqual(rc, 2, out)

if __name__ == "__main__":
    unittest.main()
