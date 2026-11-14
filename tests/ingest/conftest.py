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
