"""The store guard, the contract's ids and fingerprint, and the STATE notice."""
import hashlib
import os

import pytest

import helpers as H
from pipeline.ingest import config, contract, spend


class TestStoreGuard:
    def test_the_main_tree_is_refused(self, monkeypatch):
        monkeypatch.delenv("PP_INGEST_ALLOW_MAIN_STORE", raising=False)
        for p in (config.MAIN_STORE, config.MAIN_TREE, os.path.join(config.MAIN_TREE, "data")):
            with pytest.raises(config.StoreGuard):
                config.check_store(p)

    def test_the_integrator_can_allow_it(self, monkeypatch):
        monkeypatch.setenv("PP_INGEST_ALLOW_MAIN_STORE", "1")
        assert config.check_store(config.MAIN_STORE) == os.path.realpath(config.MAIN_STORE)

    def test_transcript_store_writes_where_the_service_writes(self):
        ts = config.ts()
        assert os.path.realpath(ts.STORE_DIR) == config.store_root() == os.path.realpath(os.environ["PP_INGEST_STORE"])
        assert not os.path.realpath(ts.STORE_DIR).startswith(os.path.realpath(config.MAIN_TREE))


class TestContract:
    def test_moment_id_is_the_published_formula(self):
        assert contract.moment_id("abcDEF12345", "f" * 64, 7, 42) == \
            hashlib.sha256(f"abcDEF12345|{'f' * 64}|7|42".encode()).hexdigest()[:20]

    def test_sentences_are_read_as_spoken(self):
        rec, meta = H.caption_record(H.vid(), extra=["The S&amp;P fell while $81 ,000 held in the U .S. market."])
        timing, toks, sents = contract.sentences(rec)
        assert timing == "segment"
        assert sents[-1]["text"] == "The S&P fell while $81,000 held in the U.S. market."
        assert all(s["complete"] for s in sents)

    def test_fingerprint_is_stable_and_changes_with_the_definitions(self, monkeypatch):
        fp = contract.fingerprint()
        assert fp == contract.fingerprint() and len(fp) == 24
        monkeypatch.setattr(contract, "_FP", None)
        E, S, _ = contract.modules()
        monkeypatch.setattr(E, "split_sentences", lambda toks: [(0, len(toks) - 1)])
        assert contract.fingerprint() != fp

    def test_verify_line_catches_a_line_that_no_longer_names_its_text(self):
        rec, meta = H.caption_record(H.vid())
        timing, toks, sents = contract.sentences(rec)
        E, _, _ = contract.modules()
        w0, w1 = sents[1]["w0"], sents[2]["w1"]
        line = {"video_id": rec["video_id"], "transcript_sha256": rec["transcript_sha256"], "sentences": [1, 2],
                "words": [w0, w1], "text": E.spoken(toks[w0:w1 + 1]),
                "moment_id": contract.moment_id(rec["video_id"], rec["transcript_sha256"], w0, w1)}
        assert contract.verify_line(line, rec) == (True, "")
        assert contract.verify_line(dict(line, text=line["text"] + " Extra."), rec)[0] is False
        assert contract.verify_line(dict(line, words=[w0, w1 + 1]), rec)[0] is False
        assert contract.verify_line(dict(line, sentences=[1, 99]), rec)[0] is False


class TestStateNotice:
    def doc(self, tmp_path, body="# STATE\n\n## LIVE STATE\n- x\n"):
        p = tmp_path / "STATE.md"
        p.write_text(body)
        return str(p)

    def test_the_90_percent_notice_goes_on_top_once(self, tmp_path):
        d = self.doc(tmp_path)
        snap = {"spend_usd": 415.0, "cap_usd": 460.0, "measured_at": "2026-11-12T08:00:00Z"}
        spend.write_state_notice("tripped", snap, doc=d)
        spend.write_state_notice("tripped", dict(snap, spend_usd=420.0), doc=d)
        lines = open(d).read().split("\n")
        assert lines[0].startswith("HEIMDALL SPEND AT 90%") and "$420.0" in lines[0]
        assert sum(1 for l in lines if l.startswith("HEIMDALL SPEND")) == 1 and lines[1] == "# STATE"

    def test_unmeasured_is_noted_and_cleared_and_the_90_notice_stays(self, tmp_path):
        d = self.doc(tmp_path)
        spend.write_state_notice("tripped", {"spend_usd": 415.0, "cap_usd": 460.0}, doc=d)
        spend.write_state_notice("unmeasured", {"measured_at": None, "last_error": "x"}, doc=d)
        lines = open(d).read().split("\n")
        assert lines[0].startswith("HEIMDALL SPEND UNMEASURED") and lines[1].startswith("HEIMDALL SPEND AT 90%")
        spend.write_state_notice("ok", {}, doc=d)
        lines = open(d).read().split("\n")
        assert lines[0].startswith("HEIMDALL SPEND AT 90%") and lines[1] == "# STATE"

    def test_ok_leaves_a_clean_state_untouched(self, tmp_path):
        d = self.doc(tmp_path)
        before = open(d).read()
        spend.write_state_notice("ok", {}, doc=d)
        assert open(d).read() == before
