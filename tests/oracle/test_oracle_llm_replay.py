"""Keys by name, the spend guard, and the replay stand-ins (never a GPU, never a write, never an invented verdict)."""
import json
import os
import threading

import pytest

from pipeline.oracle import llm


def test_a_key_is_read_by_name_and_never_printed(tmp_path, capsys):
    env = tmp_path / ".env"
    env.write_text("# c\nOTHER=1\nexport OPENAI_API_KEY='sk-test-123'\nANTHROPIC_API_KEY=\n")
    assert llm.env_key("OPENAI_API_KEY", str(env)) == "sk-test-123"
    with pytest.raises(KeyError):
        llm.env_key("ANTHROPIC_API_KEY", str(env))                    # empty is missing
    with pytest.raises(KeyError):
        llm.env_key("XAI_API_KEY", str(env))
    assert "sk-test" not in capsys.readouterr().out


GPT = {"in": 2.0, "out": 10.0, "in_long": 4.0, "out_long": 15.0, "long_above": 272_000}
FABLE = {"in": 8.0, "out": 40.0}


def test_costs_use_the_long_context_tier():
    assert llm.cost(GPT, 100_000, 10_000) == pytest.approx(0.2 + 0.1)
    assert llm.cost(GPT, 300_000, 10_000) == pytest.approx(1.2 + 0.15)
    assert llm.cost(FABLE, 3_000, 1_000) == pytest.approx(0.024 + 0.04)
    assert llm.cost(None, 10**6, 10**6) == 0.0                         # a local / credit-metered back-end


def test_the_spend_guard_refuses_a_call_whose_worst_case_passes_the_cap(tmp_path):
    led = llm.Ledger(str(tmp_path / "SPEND.jsonl"), cap=1.0)
    led.record(usd=0.9, tag="earlier")
    with pytest.raises(llm.SpendStop):
        led.allow(FABLE, 1000, 10_000, "fable")                       # worst 0.408 > 0.1 left
    w = led.allow(GPT, 1000, 5_000, "gpt")                             # 0.052 fits
    with pytest.raises(llm.SpendStop):                                 # in flight counts until released
        led.allow(GPT, 1000, 5_000, "gpt")
    led.release(w)
    led.allow(GPT, 1000, 5_000, "gpt")


def test_concurrent_reservations_never_pass_the_cap_together(tmp_path):
    led = llm.Ledger(str(tmp_path / "SPEND.jsonl"), cap=1.0)
    ok, errors = [], []

    def go():
        try:
            ok.append(led.allow(GPT, 0, 30_000, "gpt"))               # 0.30 each: only 3 fit
        except llm.SpendStop as e:
            errors.append(e)
    ts = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(ok) == 3 and len(errors) == 5


# ── replay stand-ins ──

def test_a_cache_miss_is_not_rerun_and_escapes_every_except_exception():
    from pipeline.oracle import replay as RP
    import story_semantics as sm
    L = RP.CacheOnlyLLM(digest="d" * 64)
    with pytest.raises(RP.NotRerun):
        sm.adjudicate(L, {"underlying_event": "x"}, {"title": "t", "channel": "c"},
                      [{"chunk_id": "vidAAAAAAAA:0-1000", "text": "Bitcoin fell."}])
    assert L.miss and L.miss["max_tokens"] == 400                     # recorded, never an INCONCLUSIVE verdict
    assert not issubclass(RP.NotRerun, Exception)


def test_a_cached_reply_is_used_and_revalidated(tmp_path, monkeypatch):
    from pipeline.oracle import replay as RP
    import hashlib
    import story_semantics as sm
    monkeypatch.setattr(sm, "LLM_CACHE_DIR", str(tmp_path))
    L = RP.CacheOnlyLLM(digest="d" * 64)
    prompt = "P"
    key = hashlib.sha256(json.dumps([L.model, L.digest, sm.LLM_CTX, 300, prompt]).encode()).hexdigest()
    os.makedirs(tmp_path / key[:2])
    (tmp_path / key[:2] / f"{key}.json").write_text(json.dumps({"reply": {"label": "NEW_SUBJECT"}}))
    assert L.chat_json(prompt, max_tokens=300, validate=sm._v_react) == {"label": "NEW_SUBJECT"}
    (tmp_path / key[:2] / f"{key}.json").write_text(json.dumps({"reply": {"label": "MAYBE"}}))
    with pytest.raises(RP.NotRerun):                                   # stricter validator: asked again = miss
        L.chat_json(prompt, max_tokens=300, validate=sm._v_react)


def test_stop_never_unloads_the_shared_gpu0_model(monkeypatch):
    from pipeline.oracle import replay as RP
    import story_semantics as sm
    called = []
    monkeypatch.setattr(sm, "_unload", lambda *a: called.append(a))
    RP.CacheOnlyLLM(digest="d").stop()
    assert called == []


def test_cpu_vectors_are_never_written_to_the_store(tmp_path, monkeypatch):
    from pipeline.oracle import replay as RP
    import numpy as np
    import story_semantics as sm
    store, own = tmp_path / "store", tmp_path / "own"
    store.mkdir()
    monkeypatch.setattr(sm, "EMB_DIR", str(store))
    calls = []
    E = RP.CpuEmbedder.__new__(RP.CpuEmbedder)                         # no model load: encode is faked
    E.computed_here, E.vector_cache = [], None
    E.encode = lambda texts, query=False: calls.append(texts) or np.ones((len(texts), 768), np.float32)
    rec = {"video_id": "vidAAAAAAAA", "transcript_sha256": "a" * 64}
    chunks = [{"chunk_id": "vidAAAAAAAA:0-1000", "text": "x"}]
    ids, vecs = E.chunk_vectors(rec, chunks)
    assert vecs.shape == (1, 768) and E.computed_here == ["vidAAAAAAAA"] and os.listdir(store) == []
    E.vector_cache = str(own)                                            # its own cache: written there, reused
    E.chunk_vectors(rec, chunks)
    E.chunk_vectors(rec, chunks)
    assert len(calls) == 2 and os.listdir(store) == [] and os.listdir(own / "vidAAAAAAAA")


def test_pipeline_modules_come_from_this_checkout_not_a_shadow():
    import canon
    import editorial_select
    import story_semantics
    import transcript_store
    from pipeline import oracle
    here = os.path.dirname(oracle.PIPELINE_DIR)
    for m in (canon, editorial_select, story_semantics, transcript_store):
        assert os.path.dirname(os.path.abspath(m.__file__)) == oracle.PIPELINE_DIR, m.__file__
    assert oracle.__file__.startswith(os.path.join(here, "pipeline", "oracle"))


def test_a_not_rerun_writes_the_selectors_live_record_and_restores_checkpoint(tmp_path, monkeypatch):
    from pipeline.oracle import replay as RP
    import editorial_select as es
    run = tmp_path / "fresh_20261110_093150"
    run.mkdir()
    (run / "TOPIC_SELECTION.json").write_text(json.dumps({"started": "2026-11-10T09:31:52+00:00", "universe": [],
                                                           "candidates": []}))
    real = es.Checkpoint

    def fake_select(out_dir, **kw):                  # clusters computed after the last checkpoint, then a miss
        rec = {"started": "x"}
        es.Checkpoint(out_dir, rec)("embedded")
        rec["emergent_clusters"] = [{"screen": "48h"}]
        kw["llm"]._post("label prompt", 500, 7)
    monkeypatch.setattr(es, "select_story", fake_select)
    rec = RP.replay(str(run), str(tmp_path / "out"), embedder=None, digest="d", runs_dir=str(tmp_path))
    saved = json.load(open(tmp_path / "out" / "TOPIC_SELECTION.json"))
    assert saved["emergent_clusters"] == [{"screen": "48h"}] and rec["outcome"].startswith("NOT_RERUN")
    assert rec["gemma_miss"]["call"] == "label_cluster" and rec["stopped_at"]["phase"] == "embedded"
    assert es.Checkpoint is real


def test_the_replay_write_guard_refuses_every_write_under_the_main_tree_and_allows_reads(tmp_path):
    import pathlib
    from pipeline.oracle import replay as RP
    root = tmp_path / "main"
    (root / "data").mkdir(parents=True)
    (root / "data" / "r.json").write_text("{}")
    out = tmp_path / "out"
    with RP.no_writes_under(str(root)):
        assert open(root / "data" / "r.json").read() == "{}"                 # reading is fine
        for attempt in (lambda: open(root / "data" / "w.json", "w"), lambda: open(root / "data" / "r.json", "a"),
                        lambda: pathlib.Path(root / "data" / "p.json").write_text("x"),
                        lambda: os.replace(root / "data" / "r.json", root / "data" / "s.json"),
                        lambda: os.unlink(root / "data" / "r.json"),
                        lambda: os.makedirs(root / "data" / "new"),
                        lambda: os.open(str(root / "data" / "q.json"), os.O_WRONLY | os.O_CREAT)):
            with pytest.raises(PermissionError, match="replay write guard"):
                attempt()
        os.makedirs(root / "data", exist_ok=True)                            # an existing dir: not a write
        os.makedirs(out / "x")
        (out / "x" / "ok.json").write_text("{}")                              # outside the root: allowed
    open(root / "data" / "after.json", "w").close()                          # the guard is gone afterwards
