"""tests/ingest: one throw-away store per test session (transcript_store binds its root once per process)."""
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

_STORE = tempfile.mkdtemp(prefix="pp_ingest_test_store_")
os.environ["PP_INGEST_STORE"] = _STORE
os.environ.pop("PP_EDITORIAL_STORE", None)
os.environ.pop("PP_INGEST_ALLOW_MAIN_STORE", None)
os.environ.pop("PP_INGEST_HEIMDALL_BASE", None)
os.environ.pop("PP_INGEST_CHANNELS", None)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _state_doc_in_tmp(tmp_path, monkeypatch):
    """Every test writes its STATE notices to its own file, never the real STATE: the watcher's health loop writes the
    cycles line (cycles.py), so any service test would otherwise reach the real file. A test that sets its own
    STATE_DOC still does (its monkeypatch comes later)."""
    from pipeline.ingest import config
    monkeypatch.setattr(config, "STATE_DOC", str(tmp_path / "STATE_of_this_test.md"))


@pytest.fixture(autouse=True)
def _batch_in_tmp(tmp_path_factory, monkeypatch):
    """Ruling 108: every test reads its own batch file, never pipeline/ingest/batch.json (the real batch's window and
    share would decide the paid route by the day the suite runs). The default is a batch around every clock the tests
    use with a share no older test reaches (ruling 98's daily cap stays what they test); test_batch sets its own."""
    import json
    from pipeline.ingest import batch
    p = tmp_path_factory.mktemp("batch") / "batch_of_this_test.json"    # beside the test's own files, not among them
    p.write_text(json.dumps({"name": "BATCH 9", "start_et": "2026-01-01 00:00", "end_et": "2027-12-31 00:00",
                             "share_usd": 1000.0, "share_of": "mining and checks"}))
    monkeypatch.setattr(batch, "SPEC", str(p))
    return p


@pytest.fixture(autouse=True)
def _pipeline_store_in_tmp(tmp_path_factory, monkeypatch):
    """The 10:50 order (1) of Nov 16: the fetch step reads the pipeline's own transcript store and caption breaker (the
    main tree's, READ ONLY). Every test reads its own empty ones, never the main tree's (a real video id there would
    decide a test by the day it runs); a test that needs a record writes it here (fetch.PIPELINE_STORE)."""
    from pipeline.ingest import fetch
    d = tmp_path_factory.mktemp("pipeline_store")
    monkeypatch.setattr(fetch, "PIPELINE_STORE", str(d / "transcripts"))
    monkeypatch.setattr(fetch, "PIPELINE_CIRCUIT", str(d / "state" / "caption_circuit.json"))
    return d
