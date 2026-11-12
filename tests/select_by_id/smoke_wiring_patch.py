#!/usr/bin/env python3
"""The R1 wiring patch (docs/audits/parallel/pp-selectid_REQUESTS.md) applied to a TEMPORARY copy of pipeline/ and
run end to end: the patched editorial_select.select_story on the protected preview's four frozen word transcripts
(tests/select_by_id/fixtures/preview), a temporary transcript store, a hash embedder, one cluster of the four videos
and a scripted model that answers the two id prompts. No GPU, no network, nothing outside the temp dir is written.

Checks: the patch applies; select_story writes passages.json whose hook and clips are the approved DataDash hook and
Natalie Brunell / Yahoo Finance clips WORD FOR WORD (canon.same), TOPIC_SELECTION.selected.headline is the claim
sentence verbatim with ledger-form evidence, sources.json names the three videos; every story sentence got its own
independent verify_support; two clusters: the second's gate says why it was not taken (DEC-13 d); a scripted model that
names a fabricated id holds the run (NoProducibleStory), never a story; a model that is down holds it as
'HOLD (infrastructure)'; and the LLM is stopped exactly once on every path (the finally).

Usage: python3 tests/select_by_id/smoke_wiring_patch.py [--extract FILE]   (exit 0 = all checks passed)"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
REQUESTS = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_REQUESTS.md")
PREVIEW = os.path.join(HERE, "fixtures", "preview", "preview_sources.json")
EDL = os.path.join(REPO, "references", "pulse_preview_2026-11-11", "edl.json")


def extract_patch():
    text = open(REQUESTS).read()
    m = re.search(r"<!-- PATCH BEGIN -->\n```diff\n(.*?)```\n<!-- PATCH END -->", text, re.S)
    if not m:
        raise SystemExit("no patch block in REQUESTS")
    return m.group(1)


class FakeEmbedder:
    """A bag-of-words hash embedder (test_editorial_robust.FakeEmbedder's method): no model, no GPU."""
    model_id = "fake-hash-64"

    def encode(self, texts, query=False, batch=64):
        import hashlib
        import numpy as np
        out = np.zeros((len(texts), 64), np.float32)
        for i, t in enumerate(texts):
            for w in re.findall(r"[a-z]+", t.lower()):
                out[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1
        n = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(n == 0, 1, n)

    def chunk_vectors(self, rec, chunks):
        return [c["chunk_id"] for c in chunks], self.encode([c["text"] for c in chunks])

    def close(self):
        pass


class ScriptedLLM:
    """LocalLLM's surface for select_by_id.OllamaModel: model / host / digest, _post(prompt, max_tokens, seed), stop.
    It answers the story prompt with the ids of the approved passages' sentences and the line-up prompt with their
    ranges, found by their opening words (the model only ever names ids)."""
    model, host, serve_env, digest = "scripted", "local", None, "sha256:smoke"   # a digest: the Recorder branch runs

    def __init__(self, approved, fabricate=False, down=False):
        self.approved, self.fabricate, self.down, self.calls, self.checks = approved, fabricate, down, 0, []
        self.stopped = 0

    def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
        """Today's two check prompts (select_by_id.ModelChecks through LocalLLM.chat_json's contract)."""
        self.checks.append(prompt[:40])
        if prompt.startswith("Decide whether a QUOTE"):
            o = {"support": "SUPPORTS", "same_actor_action_object": True, "presented_as": "current", "reason": "s"}
        elif prompt.startswith("You check ONE SENTENCE"):
            o = {"label": "SAME_EVENT_REACTION_OR_CONSEQUENCE", "reason": "s"}
        else:
            raise AssertionError("unexpected check prompt")
        if validate:
            validate(o)
        return o

    def stop(self):
        self.stopped += 1

    @staticmethod
    def rows(prompt):
        return [(int(m.group(1)), m.group(2)) for m in re.finditer(r"^(\d+) \|(?:[^|\n]*\|){0,4} ?[*+ ]?\s*(.*)$",
                                                                   prompt, re.M)]

    def ids_of(self, prompt, opening):
        import canon
        want = canon.canon_tokens(opening)[:5]
        return [n for n, t in self.rows(prompt) if canon.canon_tokens(t.split("|")[-1])[:5] == want]

    def _post(self, prompt, max_tokens, seed):
        self.calls += 1
        if self.down:
            import urllib.error
            raise urllib.error.URLError("connection refused (scripted outage)")
        if prompt.startswith("You are the editor"):
            ids = []
            for opening in self.approved["story"]:
                ids += self.ids_of(prompt, opening)[:1]
            if self.fabricate:
                ids.append(99999)
            return json.dumps({"story": ids, "claim": ids[0]})
        if prompt.startswith("You cut a 60-second"):
            rng = lambda first, last: [self.ids_of(prompt, first)[0], self.ids_of(prompt, last)[0]]
            return json.dumps({"hook": rng(*self.approved["hook"]), "clips": [rng(*c) for c in self.approved["clips"]]})
        raise AssertionError("unexpected prompt")


def run(tmp, fabricate=False, down=False):
    sys.path.insert(0, os.path.join(tmp, "pipeline"))
    import canon
    import editorial_select as es
    import story_semantics as sm
    import transcript_store as ts
    assert os.path.dirname(es.__file__) == os.path.join(tmp, "pipeline"), es.__file__     # the PATCHED copy
    tag = "fabricated" if fabricate else "down" if down else "ok"
    store = os.path.join(tmp, f"store_{tag}")                                       # transcript records are write-once
    ts.STORE_DIR, ts.TRANSCRIPTS_DIR = store, os.path.join(store, "transcripts")
    ts.STATE_DIR, ts.MEDIA_DIR = os.path.join(store, "state"), os.path.join(store, "media")
    sm.LLM_CACHE_DIR = os.path.join(store, "llm_cache")
    reg = {c["channel_id"]: c for c in json.load(open(os.path.join(tmp, "pipeline", "channels.json"))) if c.get("channel_id")}
    d = json.load(open(PREVIEW))
    now = datetime.fromisoformat(d["now"])
    uni = []
    for v in d["videos"]:
        meta = {"schema": 1, "video_id": v["video_id"], "canonical_url": ts.canonical_url(v["video_id"]),
                "channel_id": v["channel_id"], "channel_name": v["channel_name"], "exact_title": v["title"],
                "published_at": v["published_at"], "duration": v["duration"]}
        os.makedirs(ts._vdir(v["video_id"]), exist_ok=True)
        ts._write_once(os.path.join(ts._vdir(v["video_id"]), "meta.json"), meta)
        ts._store(ts._make_record(meta, "whisper_words_punct", "large-v3 (preview fixture)",
                                  ts.sentences_from_words(v["words"]), extra={"words": v["words"]}))
        age = (now - datetime.fromisoformat(v["published_at"])).total_seconds() / 3600
        uni.append({"video_id": v["video_id"], "rss": {"title": v["title"], "published": v["published_at"]},
                    "channel": reg[v["channel_id"]], "age_h": round(age, 1)})
    stories = os.path.join(tmp, "stories.json")
    json.dump({"generated_at": d["now"], "stories": []}, open(stories, "w"))
    real_clusters = sm.emergent_clusters
    sm.emergent_clusters = lambda chunks, vecs, **kw: [{"label": i, "chunk_idx": list(range(len(chunks))),
                                                        "channels": sorted({c["channel_id"] for c in chunks})}
                                                       for i in (0, 1)]          # two clusters (audit C2)
    edl = json.load(open(EDL))
    segs = {s["channel"]: s["text"] for s in [edl["hook"]] + edl["clips"]}
    approved = {"story": [segs["DataDash"], segs["Natalie Brunell"], "U.S. Bitcoin ETFs had about $1.3 billion",
                          "And Bitcoin really hasn't participated", segs["Yahoo Finance"], "It seemed to have bounced",
                          "Bitcoin slips below Strategy's 75,451", segs["Bitcoin Magazine"]],
                "hook": (segs["DataDash"], segs["DataDash"]),
                "clips": [(segs["Natalie Brunell"], "And Bitcoin really hasn't participated"),
                          (segs["Yahoo Finance"], "It seemed to have bounced"),
                          ("Bitcoin slips below Strategy's 75,451", "And I keep seeing stories")]}   # law L-o: 60-70 s
    run_dir = os.path.join(tmp, f"run_{tag}")
    os.makedirs(run_dir)
    llm = ScriptedLLM(approved, fabricate, down)
    try:
        es.select_story(run_dir, log=lambda s: None, embedder=FakeEmbedder(), llm=llm,
                        universe_fn=lambda h: uni, stories_path=stories, topup=False, now=now)
    except es.NoProducibleStory:
        assert llm.stopped == 1, llm.stopped                                         # the finally ran, once
        t = json.load(open(os.path.join(run_dir, "TOPIC_SELECTION.json")))
        why = [a.get("rejected") for g in t["select_by_id"] for a in (g.get("story") or {}).get("attempts", [])]
        if down:
            assert t["decision"].startswith("HOLD (infrastructure)"), t["decision"]  # an outage, not a selection
            assert all(e["gate"].startswith("story model_error") for e in t["emergent_clusters"]), t["emergent_clusters"]
        else:
            assert fabricate and any("fabricated id" in (w or "") for w in why), why    # held for THAT reason
            assert t["emergent_clusters"][0]["gate"].startswith("story rejected"), t["emergent_clusters"][0]
            assert t["decision"].startswith("HOLD: no candidate"), t["decision"]
        raise
    finally:
        sm.emergent_clusters = real_clusters
    assert llm.stopped == 1, llm.stopped                                             # the finally ran, once
    n_story = len(approved["story"])
    assert sum(c.startswith("Decide whether a QUOTE") for c in llm.checks) >= n_story, llm.checks  # one per sentence
    assert any(c.startswith("You check ONE SENTENCE") for c in llm.checks), llm.checks
    t = json.load(open(os.path.join(run_dir, "TOPIC_SELECTION.json")))
    p = json.load(open(os.path.join(run_dir, "passages.json")))
    srcs = json.load(open(os.path.join(run_dir, "sources.json")))
    got = [(x["kind"], x["channel"], x["text"]) for x in p["chosen"]]
    want = [("hook", "DataDash", segs["DataDash"]), ("clip", "Natalie Brunell", segs["Natalie Brunell"]),
            ("clip", "Yahoo Finance", segs["Yahoo Finance"])]
    assert [(k, c) for k, c, _ in got] == [(k, c) for k, c, _ in want] + [("clip", "Yahoo Finance")], got
    for (_, _, a), (_, _, b) in zip(got, want):
        assert canon.same(a, b), (a, b)
    assert canon.canon_tokens(got[3][2])[:3] == ["bitcoin", "slips", "below"], got[3]
    assert 60 <= t["selected"]["eligibility"]["facts"]["runtime_s_estimate"] <= 70, t["selected"]["eligibility"]["facts"]
    cache = os.path.join(store, "llm_cache", "select_by_id")
    assert os.path.isdir(cache) and any(fs for _, _, fs in os.walk(cache)), "the Recorder branch did not record"
    sel = t["selected"]
    assert sel["selected_by"] == "select_by_id", sel
    assert canon.same(sel["headline"], segs["DataDash"]), sel["headline"]       # the claim: DataDash's sentence verbatim
    assert all({"video_id", "chunk_ids", "quote", "quote_tokens"} <= set(e) for e in sel["evidence"]), sel["evidence"]
    assert [s["channel"] for s in srcs] == ["DataDash", "Natalie Brunell", "Yahoo Finance"], srcs
    assert t["emergent_clusters"][0]["gate"] == "producible", t["emergent_clusters"][0].get("gate")
    assert t["emergent_clusters"][1]["gate"].startswith("story accepted; line-up not asked"), t["emergent_clusters"][1]
    assert t["pools"][0]["word_pass"] == {"videos": 3, "sentence_ready": 3}, t["pools"][0]   # one pass, both stories
    return got


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--extract"]:
        open(argv[1], "w").write(extract_patch())
        return 0
    tmp = tempfile.mkdtemp(prefix="pp_selectid_smoke_")
    try:
        shutil.copytree(os.path.join(REPO, "pipeline"), os.path.join(tmp, "pipeline"),
                        ignore=shutil.ignore_patterns("__pycache__", "*.mp4", "*.onnx", "fixtures", "avatars"))
        pf = os.path.join(tmp, "wiring.patch")
        open(pf, "w").write(extract_patch())
        r = subprocess.run(["patch", "-p1", "-d", tmp, "-i", pf], capture_output=True, text=True)
        if r.returncode:
            print(r.stdout, r.stderr)
            raise SystemExit("PATCH DOES NOT APPLY")
        print("patch applied:", r.stdout.strip().replace("\n", "; "))
        got = run(tmp)
        for k, c, x in got:
            print(f"  {k:4s} {c:16s} {x[:100]}")
        try:
            run(tmp, fabricate=True)
            raise SystemExit("FAIL: a fabricated id produced a story")
        except Exception as e:                                     # NoProducibleStory from the patched module
            if type(e).__name__ != "NoProducibleStory":
                raise
            print("fabricated id: HOLD (NoProducibleStory), as required")
        try:
            run(tmp, down=True)
            raise SystemExit("FAIL: a model outage produced a story")
        except Exception as e:
            if type(e).__name__ != "NoProducibleStory":
                raise
            print("model outage: HOLD (infrastructure), as required")
        print("SMOKE PASS")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
