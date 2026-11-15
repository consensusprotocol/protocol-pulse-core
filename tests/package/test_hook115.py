#!/usr/bin/env python3
"""RULING 115 (3): the hook question with PBX's examples (tests/package/hook115.py). Offline: the rating call is a
stub; the negatives are read from the proof builds (read only)."""
import os
import sys
import unittest
import unittest.mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hook115 as X  # noqa: E402
import package as PK  # noqa: E402

POS = [{"moment_id": f"ref-{i}", "text": f"Bitcoin {i} {{x}}.", "channel_name": f"P{i}"} for i in range(5)]
NEG = [{"moment_id": f"neg-{i}", "text": f"You know, {i}.", "channel_name": f"N{i}"} for i in range(5)]


class TestPrompt(unittest.TestCase):
    def test_the_block_sits_after_the_first_paragraph_and_the_question_is_unchanged(self):
        p = X.prompt_v2(POS, NEG)
        filled = p.format(hooks='CANDIDATE id="c"', keys='"c": 1')          # braces in a text are escaped
        head = PK.HOOKS_PROMPT.split("\n\n")[0]
        self.assertTrue(filled.startswith(head + "\n\nHOW PBX JUDGES OPENERS"))
        self.assertIn(PK.HOOK_QUESTION, filled)                              # ONE definition of the hook's job
        self.assertIn('"Bitcoin 3 {x}." (P3)', filled)
        self.assertIn('"You know, 4." (N4)', filled)
        self.assertLess(filled.index("OPENERS PBX APPROVED"), filled.index("OPENERS THAT FAIL"))
        self.assertLess(filled.index("OPENERS THAT FAIL"), filled.index('CANDIDATE id="c"'))
        self.assertNotIn("4 or more", filled)                                # no example carries a rating

    def test_leave_one_out_drops_only_the_rated_item(self):
        p = X.prompt_v2(POS, NEG, leave_out="ref-2")
        self.assertNotIn("Bitcoin 2 ", p)
        self.assertIn("Bitcoin 1 ", p)
        p = X.prompt_v2(POS, NEG, leave_out="neg-0")
        self.assertNotIn("You know, 0.", p)
        self.assertIn("You know, 1.", p)


class TestRate(unittest.TestCase):
    def test_alone_no_cache_the_prompt_only_for_the_call_and_the_verdict(self):
        seen = []

        def fake(router, ms, ctx, wv, wf, cache="unset", seed=None):
            seen.append((len(ms), cache, seed, PK.HOOKS_PROMPT))
            return {ms[0]["moment_id"]: {"scroll": 4, "alone": 5, "setup": 3, "why": "w"}}, None
        before = PK.HOOKS_PROMPT
        with unittest.mock.patch.object(PK, "_writers", lambda r: (set(), set())):
            r = X.rate(None, POS[0], "THE V2 PROMPT", None, rate_fn=fake)
        self.assertEqual(seen, [(1, None, 7, "THE V2 PROMPT")])
        self.assertEqual((r["own"], PK.HOOKS_PROMPT), (4, before))           # restored after the call
        rows = [dict(kind="approved", own=4)] * 5 + [dict(kind="negative", own=3)] * 5
        self.assertTrue(X.verdict(rows)["passes"])
        for bad in ([dict(kind="approved", own=3)] + rows[1:], rows[:5] + [dict(kind="negative", own=4)] + rows[6:],
                    rows[:9], [dict(kind="approved", error="x")] + rows[1:]):
            self.assertFalse(X.verdict(bad)["passes"])

    def test_a_rating_by_another_model_never_counts(self):
        rows = [dict(kind="approved", own=4, backend="xai:g")] * 5 + [dict(kind="negative", own=3, backend="xai:g")] * 5
        self.assertTrue(X.verdict(rows, "xai:g")["passes"])
        other = [dict(rows[0], backend="heimdall:q")] + rows[1:]
        self.assertEqual((X.verdict(other, "xai:g")["passes"], X.verdict(other, "xai:g")["approved"][0]), (False, None))

    def test_run_both_variants_every_item_and_the_stop(self):
        """run() with the calls stubbed: each model asks the ten in both variants (leave-one-out drops the rated
        item from the prompt), the rows carry the answering model, and past STOP_USD no call is made."""
        import tempfile
        from unittest import mock
        asked = []

        class R:
            def __init__(self, model):
                self.model, self.n = model, 0

            def spent(self):
                return 0.30 if self.model == "heimdall:qwen/qwen3.8-27b" and self.n >= 3 else 0.0

        def rate(router, m, prompt, ctx, rate_fn=None):
            router.n += 1
            asked.append((router.model, m["moment_id"], m["text"][:10] in prompt.split("OPENERS PBX APPROVED")[1]))
            return {"scroll": 5, "alone": 5, "setup": 5, "own": 5, "why": "w", "backend": router.model}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(X, "OUT", d), \
                mock.patch.object(X, "SPEND", os.path.join(d, "S.json")), mock.patch.object(X, "rate", rate), \
                mock.patch.object(X, "build_router", R), mock.patch.object(X.H, "ref_moments", lambda: POS), \
                mock.patch.object(X, "negatives", lambda: NEG), mock.patch.object(X.H, "registry", lambda: []):
            with open(os.path.join(d, "S.json"), "w") as f:            # the report names the REPORTED figure,
                f.write('{"usd_reported": 0.1, "usd_estimate": 1.0}')     # never the estimate (15:17 ET Nov 15)
            out = X.run(["grok", "qwen"])
            self.assertEqual(out["spent_usd_reported"], 0.1)
            self.assertTrue(os.path.exists(os.path.join(d, "QUESTION_V2_TEST.json")))
            X.report()
            self.assertIn("by xai:grok-4.20-0309-reasoning", open(os.path.join(d, "REPORT.md")).read())
        g = out["models"]["xai:grok-4.20-0309-reasoning"]
        self.assertEqual([len(v["rows"]) for v in g.values()], [10, 10])
        self.assertTrue(all(inside for model, mid, inside in asked[:10]))          # as ordered: every example in
        self.assertFalse(any(inside for model, mid, inside in asked[10:15]))      # leave-one-out: not itself
        q = out["models"]["heimdall:qwen/qwen3.8-27b"]["as ordered"]["rows"]
        self.assertEqual(sum("error" in r for r in q), 7)                          # stopped after 3 calls
        self.assertEqual(sum(1 for model, *_ in asked if model.startswith("heimdall")), 3)

    def test_the_five_negatives_are_read_rated_2_with_their_text(self):
        neg = X.negatives()
        self.assertEqual([n["channel_name"] for n in neg], [c for _, c in X.NEGATIVES])
        self.assertTrue(neg[0]["text"].startswith("You know, it's still an asset"))
        self.assertTrue(all(n["moment_id"].startswith("neg-") and n["text"] for n in neg))


if __name__ == "__main__":
    import unittest.mock  # noqa: F401
    unittest.main()
