#!/usr/bin/env python3
"""LEAN (4) (the owner's assignment, 13:37 ET Nov 24, issue 4: "The existing story-first path still invokes the angle
writer even when story-specific angles exist"; the orchestrator: "when a story carries its own angle, the angle writer
is not called"). With lean=True and a story angle from the stories file (ruling 118 (4)), package._build asks no
angle_write call (nor ruling 64's follow-up): the story angles are the build's angles, tried as before inside their
stories; the lines are written down the writer chain's first back-end that answers, and every verdict avoids it and the
stories file's grouping models (law L-x), as on the old path. No story angle: the writer is asked, as before.
Build 167 (the two-year-low story, sealed Nov 24) asked qwen for 2 angles at 474 s; build 171 read 4 stories, 0 story
angles, and asked the writer (as it still would). Offline: the medley rig, every model stubbed."""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/eligibility", "tests/moments"):
    sys.path.insert(0, os.path.join(REPO, _p))
import package as PK  # noqa: E402
import test_medley as TM  # noqa: E402
from test_moments import pm  # noqa: E402

GROUP = {"group": ["deepseek/deepseek-v4.1-flash", "minimax/minimax-m3.1-flash"]}
MS = TM.ledgered(pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("q", "E", 13.0))
STORY = [("S-1", "Bitcoin's own story", ["Lh", "Lx", "Ly", "Lgone"])]       # the file names LEDGER ids


class StoryCase(unittest.TestCase):
    def file(self, stories):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "latest.json")
        with open(p, "w") as f:
            json.dump({"generated_at": "2026-11-16T13:43:27Z", "prompt_version": "st1-x", "models": GROUP,
                       "stories": [{"story_id": sid, "headline": hl, "channels": 3, "n_claims": 6,
                                    "moments": [{"moment_id": m, "video_id": "v" + m, "channel_name": "c",
                                                 "published_at": "2026-11-16T10:00:00Z", "claims": []} for m in ms]}
                                   for sid, hl, ms in stories]}, f)
        return p

    def rig(self, stories, lean, medleys=None, writes=()):
        r = TM.Rig(MS, ["h", "x", "y", "z", "q"], list(medleys or [(False, [], None, "none")] * 20), list(writes))
        r.stories_path = self.file(stories)
        r.build_kw = {"lean": lean}
        oe = r.out_edges
        r.out_edges = lambda *a, recover=False, **k: oe(*a, **k)   # lean (2) is test_lean_out_edge's
        return r

    @staticmethod
    def writer_calls(r):
        return [p for role, p in r.prompts if role == "angle_write"]


class TestTheStoryCarriesItsOwnAngle(StoryCase):
    def test_no_writer_call_when_a_story_gives_an_angle(self):
        """MUST-PASS: the story's angle is the build's; the angle writer is never asked; the story line-up is judged."""
        r = self.rig(STORY, True)
        out = r.run()
        self.assertEqual(self.writer_calls(r), [])
        self.assertEqual([a.get("story") for a in out["angles"]], ["S-1"])
        self.assertTrue(out["angle_writer"].startswith("not asked (lean (4))"), out.get("angle_writer"))
        self.assertNotIn("angle_follow_up", out)
        self.assertTrue(r.medley_calls)
        self.assertTrue(all(set(lu) <= {"h", "x", "y"} for lu in r.medley_calls), r.medley_calls)

    def test_the_old_path_still_asks_the_writer(self):
        """MUST-FAIL (the issue as it stands, lean=False): a story angle AND the writer's angles."""
        r = self.rig(STORY, False)
        out = r.run()
        self.assertEqual(len(self.writer_calls(r)), 1)
        self.assertEqual(out["angles"][0].get("story"), "S-1")
        self.assertNotIn("story", out["angles"][1])

    def test_no_story_angle_the_writer_is_asked_as_before(self):
        """A story of two channels gives no angle: under lean the writer is asked, as before."""
        ms2 = [("S-2", "Two channels", ["Lh", "Lx"])]
        r = self.rig(ms2, True)
        out = r.run()
        self.assertEqual(len(self.writer_calls(r)), 1)
        self.assertTrue(all("story" not in a for a in out["angles"]))
        self.assertNotIn("angle_writer", out)

    def test_a_story_package_seals_with_its_writer_and_grouping_models_kept_off_every_verdict(self):
        """MUST-PASS: the story line-up passes and seals; its angle is the story's; the lines' writer is the writer
        chain's first back-end; the verdicts avoid it and the grouping models (L-x, as on the old path)."""
        r = self.rig(STORY, True, medleys=[(True, [], None, TM.Rig.LINE)] * 2, writes=[None] * 2)
        r.router.backends["heimdall:qwen"].model = "minimax/minimax-m3.1-flash"   # a back-end running a grouping model
        seen, jt = [], r.join_table
        r.join_table = lambda router, ms_, c, wv, wf=None, **k: (seen.append((set(wv), set(wf or ()))),
                                                                 jt(router, ms_, c, wv, wf, **k))[1]
        out = r.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual(self.writer_calls(r), [])
        self.assertEqual(pk["models"]["angle"], "story S-1 (the stories file)")
        self.assertEqual(out["angle_backend"], "heimdall:deepseek")      # the writer chain's first, not asked
        self.assertEqual(out["stories"]["writers"], {"vendors": ["heimdall"], "families": ["qwen"]})
        self.assertTrue(seen and all("heimdall" in wv and {"deepseek", "qwen"} <= wf for wv, wf in seen), seen)
        self.assertEqual(r.write_calls[0][0][0], "h")                     # the story's hook opens


if __name__ == "__main__":
    unittest.main()
