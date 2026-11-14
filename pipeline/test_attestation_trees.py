#!/usr/bin/env python3
"""Ruling 27 (orchestrator 2026-11-12 '23:20'): the attestation binds a run to the git TREE of its executable paths
(run_fresh.EXEC_PATHS: pipeline/, segment_v1/, scripts/, video_pipeline_v3/relay.py), recorded at launch and verified
at the end, not to HEAD.
must-fail  a commit touching pipeline/ (or segment_v1/, scripts/, relay.py, a .md INSIDE pipeline/) during the run;
           an uncommitted edit to the registry (a file no module check sees)
must-pass  a docs commit (docs/, a root *.md) during the run: HEAD moves, the trees do not
Each case runs on a scratch git repository, never on this checkout."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import run_fresh as rf  # noqa: E402

FILES = {"pipeline/gates.py": "X = 1\n", "pipeline/channels.json": "[]\n", "segment_v1/qa_gates.py": "Y = 1\n",
         "scripts/pulse_check_run.sh": "#!/bin/bash\n", "video_pipeline_v3/relay.py": "Z = 1\n",
         "docs/audits/DoD.md": "# DoD\n", "README.md": "# repo\n"}


class TestAttestationTrees(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="attest_trees_")
        self.addCleanup(shutil.rmtree, self.repo)
        self.git("init", "-q")
        for rel, text in FILES.items():
            self.write(rel, text)
        self.commit("launch")
        self.launch = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=self.repo,
                              capture_output=True, text=True, check=True).stdout

    def write(self, rel, text):
        p = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def why(self):
        return rf.executed_code(self.launch, modules={}, repo=self.repo)[1]

    def test_the_launch_trees_are_recorded_for_every_executable_path(self):
        t = rf.exec_trees(self.launch, self.repo)
        self.assertEqual(set(t), set(rf.EXEC_PATHS))
        self.assertTrue(all(len(v or "") == 40 for v in t.values()), t)

    def test_launch_records_the_trees_of_a_clean_checkout(self):        # cycle-2 consensus: the launch half tested
        rec = rf.launch_code(self.repo)
        self.assertEqual(rec["git_head"], self.launch)
        self.assertEqual(rec["exec_trees"], rf.exec_trees(self.launch, self.repo))
        self.assertIs(rec["pipeline_tree_clean_at_launch"], True)

    def test_launch_refuses_any_dirty_executable_path_and_accepts_dirty_docs(self):
        for rel in ("scripts/pulse_check_run.sh", "segment_v1/qa_gates.py", "video_pipeline_v3/relay.py",
                    "pipeline/channels.json"):
            with self.subTest(rel=rel):
                self.git("reset", "-q", "--hard", self.launch)
                self.write(rel, "edited\n")
                with self.assertRaisesRegex(rf.Hold, "not clean at launch"):
                    rf.launch_code(self.repo)
        self.git("reset", "-q", "--hard", self.launch)
        self.write("docs/audits/DoD.md", "# DoD, being written\n")
        self.write("pipeline/new_tool.py", "N = 1\n")                     # an untracked pipeline module refuses too
        with self.assertRaisesRegex(rf.Hold, "pipeline/new_tool.py"):
            rf.launch_code(self.repo)
        os.remove(os.path.join(self.repo, "pipeline", "new_tool.py"))
        self.assertEqual(rf.launch_code(self.repo)["git_head"], self.launch)  # a dirty doc never refuses

    def test_a_docs_commit_during_the_run_is_accepted(self):              # must-pass: HEAD moves, the trees do not
        self.write("docs/audits/DoD.md", "# DoD\n## 23:11 RESULT\n")
        self.write("README.md", "# repo, updated\n")
        self.commit("docs while a run is in flight")
        self.assertNotEqual(self.git("rev-parse", "HEAD").strip(), self.launch)
        self.assertEqual(self.why(), [])

    def test_a_commit_touching_pipeline_during_the_run_is_refused(self):
        self.write("pipeline/gates.py", "X = 2\n")
        self.commit("code while a run is in flight")
        why = self.why()
        self.assertTrue(any(w.startswith("executable tree changed during the run: pipeline ") for w in why), why)

    def test_commits_to_every_other_executable_path_are_refused(self):
        for rel, path in (("segment_v1/qa_gates.py", "segment_v1"), ("scripts/pulse_check_run.sh", "scripts"),
                          ("video_pipeline_v3/relay.py", "video_pipeline_v3/relay.py"), ("pipeline/NOTES.md", "pipeline")):
            with self.subTest(rel=rel):
                self.git("reset", "-q", "--hard", self.launch)
                self.write(rel, "changed\n")
                self.commit(f"touch {rel}")
                why = self.why()
                self.assertTrue(any(w.startswith(f"executable tree changed during the run: {path} ") for w in why), why)

    def test_a_docs_commit_then_an_uncommitted_registry_edit_names_only_the_edit(self):   # cycle-1 glm F3
        self.write("docs/audits/DoD.md", "# DoD, again\n")
        self.commit("docs")
        self.write("pipeline/channels.json", "[1]\n")
        self.assertEqual(self.why(), ["executable paths differ from the launch revision: ['pipeline/channels.json']"])

    def test_an_unknown_launch_revision_fails_closed(self):              # cycle-1 glm F1: a git failure is never a pass
        why = rf.executed_code("0" * 40, modules={}, repo=self.repo)[1]
        self.assertTrue(any(w.startswith("executable tree not readable: pipeline at launch: UNREADABLE") for w in why), why)
        self.assertTrue(any(w.startswith("git diff against the launch revision failed") for w in why), why)

    def test_an_untracked_module_the_run_imports_is_refused(self):       # cycle-1 qwen F1 / glm F2: the end check
        self.write("segment_v1/scratch_v9.py", "W = 1\n")                 # (segment_v1 keeps 1700+ untracked files)
        import importlib.util
        spec = importlib.util.spec_from_file_location("scratch_v9", os.path.join(self.repo, "segment_v1", "scratch_v9.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        why = rf.executed_code(self.launch, modules={"scratch_v9": mod}, repo=self.repo)[1]
        self.assertIn("segment_v1/scratch_v9.py (untracked)", why)

    def test_an_uncommitted_registry_edit_is_refused(self):              # no module check sees a data file
        self.write("pipeline/channels.json", "[{\"display_name\": \"x\"}]\n")
        why = self.why()
        self.assertIn("executable paths differ from the launch revision: ['pipeline/channels.json']", why)


if __name__ == "__main__":
    unittest.main()
