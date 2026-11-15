"""BITCOIN_STATEMENTS export (pipeline/oracle/export.py): frozen input, text read as spoken, byte-identical output."""
import hashlib
import json
import os

import pytest

from pipeline.oracle import export as X
import canon
import transcript_store as ts

REGISTRY = [{"channel_id": "UCcap", "display_name": "Caps TV", "has_chyron": False, "layout_status": "pending"},
            {"channel_id": "UCwrd", "display_name": "Words Show", "has_chyron": True, "layout_status": "approved"}]


def store_record(store, vid, method, segments, words=None, cid="UCcap", name="Caps TV"):
    segs = [{"start": a, "end": b, "text": t} for a, b, t in segments]
    rec = {"schema": 1, "video_id": vid, "channel_id": cid, "channel_name": name, "transcript_method": method,
           "transcript_model": "test", "segments": segs, "transcript_sha256": ts.segments_sha256(segs)}
    if words is not None:
        rec["words"] = [{"word": w, "start": a, "end": b} for w, a, b in words]
    d = os.path.join(store, "transcripts", vid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"transcript.{method.split(':')[0]}.json"), "w") as f:
        json.dump(rec, f)
    return rec


@pytest.fixture
def saved_day(tmp_path):
    store, run = str(tmp_path / "store"), tmp_path / "runs" / "fresh_20261110_093150"
    run.mkdir(parents=True)
    cap = store_record(store, "capVIDEO01", "yt_auto:en-orig", [
        (0.0, 4.0, "Welcome back everyone."),
        (4.0, 8.0, "The S&amp;P 500 slipped while Bitcoin fell"),
        (8.0, 12.0, "below $74,000 overnight. [Music] It was a rough"),
        (12.0, 16.0, "weekend. &gt;&gt; Thanks, Tom. Now to oil."),
        (16.0, 20.0, "Crude rose two percent."), (20.0, 24.0, "Gold was flat."), (24.0, 28.0, "Silver fell."),
        (28.0, 32.0, "Copper rose."), (32.0, 36.0, "That is all.")])
    wrd = store_record(store, "wrdVIDEO02", "whisper_words_punct", [(0.0, 9.0, "unused")], words=[
        ("It", 0.0, 0.2), ("went", 0.2, 0.4), ("from", 0.4, 0.6), ("above", 0.6, 0.9), ("$81", 0.9, 1.3),
        (",000", 1.3, 1.6), ("to", 1.7, 1.8), ("below", 1.8, 2.1), ("$75", 2.1, 2.4), (",000.", 2.4, 2.8),
        ("BTC", 3.0, 3.3), ("is", 3.3, 3.4), ("lower.", 3.4, 3.9)], cid="UCwrd", name="Words Show")
    universe = [
        {"video_id": "capVIDEO01", "channel": "Caps TV", "channel_id": "UCcap", "title": "Markets",
         "published_at": "2026-11-10T01:00:00+00:00", "age_h": 8.5, "layout_eligible": True,
         "transcript_sha256": cap["transcript_sha256"], "transcript_status": "cached"},
        {"video_id": "wrdVIDEO02", "channel": "Words Show", "channel_id": "UCwrd", "title": "BTC",
         "published_at": "2026-11-10T02:00:00+00:00", "age_h": 7.5, "layout_eligible": True,
         "transcript_sha256": wrd["transcript_sha256"], "transcript_status": "cached"},
        {"video_id": "noTRANSCR3", "channel": "Caps TV", "channel_id": "UCcap", "title": "x",
         "published_at": "2026-11-10T03:00:00+00:00", "age_h": 6.5, "transcript_sha256": None,
         "transcript_status": "missing"}]
    (run / "TOPIC_SELECTION.json").write_text(json.dumps({"started": "2026-11-10T09:31:52+00:00",
                                                          "today": "2026-11-10", "universe": universe}))
    return str(run), store


def test_the_export_is_byte_identical_twice(saved_day, tmp_path):
    run, store = saved_day
    p1, m1 = X.write_export(run, str(tmp_path / "a"), store, REGISTRY)
    p2, m2 = X.write_export(run, str(tmp_path / "b"), store, REGISTRY)
    for a, b in ((p1, p2), (p1.replace(".jsonl", ".manifest.json"), p2.replace(".jsonl", ".manifest.json"))):
        assert hashlib.sha256(open(a, "rb").read()).digest() == hashlib.sha256(open(b, "rb").read()).digest()
    assert os.path.basename(p1) == "BITCOIN_STATEMENTS_20261110_093150.jsonl"
    assert m1["rows_sha256"] == hashlib.sha256(open(p1, "rb").read()).hexdigest()


def test_text_is_read_as_spoken_through_the_repo_forms(saved_day):
    rows, man = X.export_run(*saved_day, registry=REGISTRY)
    texts = {r["id"]: r["text"] for r in rows}
    assert texts["capVIDEO01:1"] == "The S&P 500 slipped while Bitcoin fell below $74,000 overnight."   # entity decoded
    assert texts["wrdVIDEO02:0"] == "It went from above $81,000 to below $75,000."                      # split tokens joined
    assert all(r["canon"] == canon.canon(r["text"]) for r in rows)
    assert all(r["text"] == ts.read_text(r["text"]) for r in rows)


def test_caption_markup_is_not_speech_and_a_speaker_change_ends_a_sentence(saved_day):
    rows, _ = X.export_run(*saved_day, registry=REGISTRY)
    texts = [r["text"] for r in rows if r["video_id"] == "capVIDEO01"]
    assert "It was a rough weekend." in texts                                 # '[Music]' dropped
    assert "Thanks, Tom." in texts and not any(">>" in t for t in texts)     # '>>' split, not kept
    cap = next(r for r in rows if r["text"] == "It was a rough weekend.")
    assert cap["timing"] == "caption_line" and 10.0 < cap["start_s"] < 12.0  # placed by character offset


def test_only_the_bitcoin_neighbourhood_is_exported_and_counted(saved_day):
    rows, man = X.export_run(*saved_day, registry=REGISTRY)
    cap = sorted(r["sentence_index"] for r in rows if r["video_id"] == "capVIDEO01")
    assert cap == [0, 1, 2, 3]                       # Bitcoin at sentence 1: 1 +- 2 (sentence 4.. not exported)
    per = {v["video_id"]: v for v in man["per_video"]}
    assert per["capVIDEO01"]["sentences"] > len(cap) and per["capVIDEO01"]["bitcoin_sentences"] == 1
    assert [g["video_id"] for g in man["gaps"]] == ["noTRANSCR3"]
    w = [r for r in rows if r["video_id"] == "wrdVIDEO02"]
    assert [r["bitcoin"] for r in w] == [False, True] and w[0]["timing"] == "word"   # 'BTC' is the free screen too


def test_layout_eligibility_is_the_selectors_predicate(saved_day):
    rows, _ = X.export_run(*saved_day, registry=REGISTRY)
    assert {r["channel"]: r["layout_eligible"] for r in rows} == {"Caps TV": True, "Words Show": False}   # has_chyron


def test_an_altered_record_fails_closed(saved_day):
    run, store = saved_day
    p = os.path.join(store, "transcripts", "capVIDEO01", "transcript.yt_auto.json")
    rec = json.load(open(p))
    rec["segments"][1]["text"] = "Bitcoin rose."                              # sha no longer matches its text
    json.dump(rec, open(p, "w"))
    with pytest.raises(X.ExportError, match="hash mismatch"):
        X.export_run(run, store, REGISTRY)


def test_a_missing_record_is_a_counted_gap_never_a_substitute(saved_day):
    run, store = saved_day
    os.unlink(os.path.join(store, "transcripts", "wrdVIDEO02", "transcript.whisper_words_punct.json"))
    rows, man = X.export_run(run, store, REGISTRY)
    assert not any(r["video_id"] == "wrdVIDEO02" for r in rows)
    assert {"video_id": "wrdVIDEO02", "channel": "Words Show", "gap": "record not in the store"} in man["gaps"]


REAL_RUN = "/home/ultron/protocol_pulse/runs/fresh_20261110_093150"


@pytest.mark.skipif(not (os.path.exists(REAL_RUN) and os.path.isdir(X.MAIN_STORE)), reason="main store not here")
def test_real_nov10_export_is_deterministic_and_reads_split_numbers_whole():
    a, b = X.export_run(REAL_RUN)[0], X.export_run(REAL_RUN)[0]
    assert X.dumps_rows(a) == X.dumps_rows(b) and len(a) > 1000
    assert not any("$81 ,000" in r["text"] or "&amp;" in r["text"] for r in a)
    assert all(r["canon"] == canon.canon(r["text"]) for r in a[:300])


def test_the_manifest_names_the_registry_the_layout_fields_came_from(saved_day):
    _, man = X.export_run(*saved_day, registry=REGISTRY)
    changed = [dict(c, has_chyron=not c.get("has_chyron")) for c in REGISTRY]
    _, man2 = X.export_run(*saved_day, registry=changed)
    assert len(man["registry_sha256"]) == 64 and man["registry_sha256"] != man2["registry_sha256"]


def test_two_records_with_the_same_sha_are_ambiguous_never_the_first_by_name(saved_day):
    import shutil
    run, store = saved_day
    d = os.path.join(store, "transcripts", "capVIDEO01")
    shutil.copy(os.path.join(d, "transcript.yt_auto.json"), os.path.join(d, "transcript.a_copy.json"))
    with pytest.raises(X.ExportError, match="records of capVIDEO01 carry sha"):
        X.export_run(run, store, REGISTRY)


def test_the_witness_refuses_a_record_that_no_longer_gives_the_exported_sentence(saved_day):
    from pipeline.oracle import witness as W
    run, store = saved_day
    rows, _ = X.export_run(run, store, REGISTRY)
    r = next(x for x in rows if x["video_id"] == "wrdVIDEO02")
    assert W.context(store, [r])                                         # unchanged: the context reads
    with pytest.raises(W.WitnessFailed, match="no longer gives the exported sentence"):
        W.context(store, [dict(r, text=r["text"] + " Extra words.")])     # audit round 3, F4


def test_the_export_is_byte_identical_across_processes_with_different_hash_seeds(saved_day, tmp_path):
    import subprocess
    import sys
    run, store = saved_day
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    code = ("import json, sys; sys.path.insert(0, %r); from pipeline.oracle import export as X; "
            "reg = json.load(open(%r)); p, m = X.write_export(%r, %r, %r, reg); print(p)")
    reg = tmp_path / "registry.json"
    reg.write_text(json.dumps(REGISTRY))
    outs = []
    for seed in ("1", "2"):                              # set / dict-hash order would differ between these
        out = tmp_path / f"out{seed}"
        out.mkdir()
        env = dict(os.environ, PYTHONHASHSEED=seed)
        p = subprocess.run([sys.executable, "-c", code % (repo, str(reg), str(run), str(out), store)], env=env,
                           capture_output=True, text=True, check=True).stdout.strip()
        outs.append((open(p, "rb").read(), open(p.replace(".jsonl", ".manifest.json"), "rb").read()))
    assert outs[0] == outs[1]
    man = json.loads(outs[0][1])
    assert not {k for k in man if any(w in k for w in ("generated", "written", "now", "time"))}   # no wall clock
