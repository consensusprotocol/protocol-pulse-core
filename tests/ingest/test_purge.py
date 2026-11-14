"""Ruling 77: the rolling purge deletes expired media from its targets only, never a delivered video's, never a record."""
import json
import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from pipeline.ingest import config, purge

NOW = datetime.now(timezone.utc).replace(microsecond=0)
VIDS = {k: k * 11 for k in "ABCDEFGHJ"}       # 11-character YouTube-shaped ids: AAAAAAAAAAA ...


def _touch(path, hours_ago=3.0, data=b"x" * 1000):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    t = NOW.timestamp() - hours_ago * 3600
    os.utime(path, (t, t))
    return path


def _age_dir(d, hours_ago):
    t = NOW.timestamp() - hours_ago * 3600
    for root, dirs, files in os.walk(d):
        for n in files + dirs:
            os.utime(os.path.join(root, n), (t, t), follow_symlinks=False)
    os.utime(d, (t, t))


class FakeQ:
    def __init__(self, pub):
        self.pub = pub

    def video(self, vid):
        return {"published_at": self.pub[vid].isoformat()} if vid in self.pub else None


@pytest.fixture
def tree(tmp_path):
    main = tmp_path / "main"
    runs = main / "runs"
    V = VIDS
    # an undelivered, idle run: one expired video, one fresh, one with no publish time, one badly named, a symlink
    r1 = runs / "pinned_old"
    for v in ("A", "B", "C"):
        _touch(str(r1 / "sources" / f"{V[v]}.mp4"))
    _touch(str(r1 / "sources" / "notavideo.mp4"))
    elsewhere = _touch(str(tmp_path / "elsewhere" / "big.mp4"))
    os.symlink(elsewhere, str(r1 / "sources" / f"{V['H']}.mp4"))
    _touch(str(r1 / "qa" / "final_clip_01.mp4"))                      # render intermediate: never a target
    _touch(str(r1 / "out" / "segment.mp4"))                           # the render: never a target
    _touch(str(r1 / "transcripts" / f"{V['A']}.json"), data=b"{}")   # text: never a target
    _touch(str(r1 / "PROVENANCE.json"), data=json.dumps({"sources": [{"video_id": V["A"]}]}).encode())
    _age_dir(str(r1), 3)
    # a delivered run (Telegram record), and the same delivered video cached in another undelivered run
    r2 = runs / "pinned_delivered"
    _touch(str(r2 / "sources" / f"{V['D']}.mp4"))
    _touch(str(r2 / "TELEGRAM_DELIVERY.json"), data=b'{"status": "complete"}')
    _age_dir(str(r2), 3)
    r3 = runs / "pinned_other"
    _touch(str(r3 / "sources" / f"{V['D']}.mp4"))
    _age_dir(str(r3), 3)
    # a run that rendered a pin the stand-alone scorer records as delivered
    r4 = runs / "pinned_pin"
    _touch(str(r4 / "sources" / f"{V['F']}.mp4"))
    _touch(str(r4 / "status.json"), data=b'{"pin": "0c68b589aaaa"}')
    _age_dir(str(r4), 3)
    _touch(str(main / "data" / "stand_alone_scorer" / "results" / "delivered_0c68b589_clip_01.x.json"), data=b"{}")
    # a run in use: one of its files was written ten minutes ago
    r5 = runs / "pinned_active"
    _touch(str(r5 / "sources" / f"{V['E']}.mp4"))
    _age_dir(str(r5), 3)
    _touch(str(r5 / "qa" / "now.wav"), hours_ago=0.2)
    # a reference names a video; that video's media in an undelivered run is kept
    _touch(str(main / "references" / "ref1" / "run" / "edl.json"),
           data=json.dumps({"clips": [{"url": f"https://www.youtube.com/watch?v={V['G']}"}]}).encode())
    r6 = runs / "v2f_ref"
    _touch(str(r6 / "sources" / f"{V['G']}.mp4"))
    _age_dir(str(r6), 3)
    # the lock precheck's acquired section of an expired video
    lp = main / "data" / "lock_precheck" / "work" / f"{V['A']}.1.0-2.0.abc"
    _touch(str(lp / "sources" / f"{V['A']}.mp4"))
    _touch(str(lp / "lock.json"), data=b"{}")
    _age_dir(str(lp), 3)
    # word-pass temp dirs: one abandoned (13 h untouched), one of a running cycle (1 h)
    tmpd = tmp_path / "tmp"
    _touch(str(tmpd / "word_pass_dead" / "0123456789abcdef0123.wav"))
    _age_dir(str(tmpd / "word_pass_dead"), 13)
    _touch(str(tmpd / "word_pass_live" / "fedcba98765432100123.wav"))
    _age_dir(str(tmpd / "word_pass_live"), 1)
    # the main store's meta gives one publish time the queue lacks
    _touch(str(main / "data" / "editorial" / "transcripts" / V["J"] / "meta.json"),
           data=json.dumps({"published_at": (NOW - timedelta(hours=30)).isoformat()}).encode())
    _touch(str(r1 / "sources" / f"{V['J']}.mp4"))
    _age_dir(str(r1), 3)
    spec = json.load(open(config.PURGE_SPEC))
    rewrite = lambda s: s.replace("/tmp/word_pass_", str(tmpd) + "/word_pass_").replace(  # noqa: E731
        "/home/ultron/protocol_pulse", str(main))
    spec = json.loads(rewrite(json.dumps(spec)))
    pub = {V[v]: NOW - timedelta(hours=h) for v, h in (("A", 20), ("B", 5), ("D", 30), ("E", 20), ("F", 20),
                                                        ("G", 40))}
    return {"main": main, "spec": spec, "q": FakeQ(pub), "tmp": tmp_path, "elsewhere": elsewhere,
            "logs": str(tmp_path / "purge_logs")}


def _run(t, **kw):
    kw.setdefault("opened", set())
    return purge.run_pass(t["spec"], q=t["q"], now=NOW, log_dir=t["logs"], store_root=str(t["tmp"] / "store"), **kw)


def _exists(t, rel):
    return os.path.lexists(str(t["main"] / rel))


def test_a_pass_deletes_only_expired_undelivered_idle_media_and_counts_why_it_kept_the_rest(tree):
    t, V = tree, VIDS
    rep = _run(t)
    assert not rep["problems"] and rep["deleted"]["run_sources"]["files"] == 3   # A (20 h), J (30 h, meta), D's copy
    assert rep["deleted"]["lock_precheck_sources"]["files"] == 1
    assert rep["deleted"]["word_pass_temp"]["files"] == 1
    assert not _exists(t, f"runs/pinned_old/sources/{V['A']}.mp4") and not _exists(t, f"runs/pinned_old/sources/{V['J']}.mp4")
    assert not _exists(t, f"runs/pinned_other/sources/{V['D']}.mp4")  # A19: the delivered video, cached elsewhere
    for rel in (f"runs/pinned_old/sources/{V['B']}.mp4",            # published 5 h ago: not expired
                f"runs/pinned_old/sources/{V['C']}.mp4",            # publish time unknown
                "runs/pinned_old/sources/notavideo.mp4",            # no video id
                f"runs/pinned_old/sources/{V['H']}.mp4",            # a symlink: never followed or deleted
                "runs/pinned_old/qa/final_clip_01.mp4", "runs/pinned_old/out/segment.mp4",
                f"runs/pinned_old/transcripts/{V['A']}.json", "runs/pinned_old/PROVENANCE.json",
                f"runs/pinned_delivered/sources/{V['D']}.mp4",      # a delivered run's own section (A19)
                f"runs/pinned_pin/sources/{V['F']}.mp4",            # a run of a delivered pin
                f"runs/pinned_active/sources/{V['E']}.mp4",         # a run in use
                f"runs/v2f_ref/sources/{V['G']}.mp4",               # a reference's video: its copy unidentified
                f"data/lock_precheck/work/{V['A']}.1.0-2.0.abc/lock.json"):
        assert _exists(t, rel), rel
    assert os.path.exists(t["elsewhere"])
    assert os.path.exists(str(t["tmp"] / "tmp" / "word_pass_live" / "fedcba98765432100123.wav"))
    assert not os.path.exists(str(t["tmp"] / "tmp" / "word_pass_dead" / "0123456789abcdef0123.wav"))
    k = rep["kept"]
    assert k["a delivered video's kept copy (one per delivery)"]["files"] == 2                  # D's and F's own
    assert k["a delivered video whose delivery copy is not identified (every copy kept)"]["files"] == 1   # G
    one = rep["one_copy_per_delivery"]
    assert one["kept_copies"] == 2 and one["other_copies"] == {"files": 1, "bytes": 1000} and set(one["unresolved"]) == {
        V["G"]}
    assert k["not expired yet (published under 12 h ago)"]["files"] == 1
    assert k["publish time not measured"]["files"] == 1 and k["no video id in its name"]["files"] == 1
    assert k["its run or unit is in use (touched under 2 h ago)"]["files"] == 1
    assert k["a word-pass cycle's, touched under 12 h ago"]["files"] == 1
    assert k["not a regular file (a symlink is never followed)"]["files"] == 1
    assert {os.path.basename(r["run"]) for r in rep["delivered_runs"]} == {"pinned_delivered", "pinned_pin"}
    assert rep["freed_bytes"] == 5 * 1000


def test_every_deletion_is_logged_and_a_second_pass_finds_nothing_more(tree):
    rep = _run(tree)
    lines = [json.loads(l) for l in open(os.path.join(tree["logs"], "deleted.jsonl"))]
    assert len(lines) == 5 and all(l["bytes"] == 1000 and l["path"] for l in lines)
    assert {l["video_id"] for l in lines} == {VIDS["A"], VIDS["J"], VIDS["D"], None}
    d = [l for l in lines if l["video_id"] == VIDS["D"]][0]                   # A19: says which copy stayed
    assert d["other_copy_of_delivered"] is True and d["kept_copies"] == [
        os.path.realpath(str(tree["main"] / "runs" / "pinned_delivered" / "sources" / f"{VIDS['D']}.mp4"))]
    again = _run(tree)
    assert again["freed_bytes"] == 0 and len(open(os.path.join(tree["logs"], "passes.jsonl")).readlines()) == 2
    assert rep["freed_bytes"] == 5000


def test_a_dry_run_deletes_nothing_and_says_what_it_would_free(tree):
    rep = _run(tree, dry_run=True)
    assert rep["freed_bytes"] == 5000 and _exists(tree, f"runs/pinned_old/sources/{VIDS['A']}.mp4")
    assert not os.path.exists(os.path.join(tree["logs"], "deleted.jsonl"))
    assert purge.summary(rep).startswith("purge: would free")


def test_a_file_open_in_a_process_is_kept(tree):
    p = os.path.realpath(str(tree["main"] / "runs" / "pinned_old" / "sources" / f"{VIDS['A']}.mp4"))
    rep = _run(tree, opened={p})
    assert os.path.exists(p) and rep["kept"]["open in a process"]["files"] == 1


def test_an_unreadable_delivered_set_or_proc_deletes_nothing(tree, monkeypatch):
    spec = json.loads(json.dumps(tree["spec"]))
    spec["delivered"]["runs"] = str(tree["tmp"] / "missing" / "runs" / "*")
    rep = purge.run_pass(spec, q=tree["q"], now=NOW, log_dir=tree["logs"], opened=set(),
                         store_root=str(tree["tmp"] / "store"))
    assert rep["refused"] and rep["freed_bytes"] == 0 and _exists(tree, f"runs/pinned_old/sources/{VIDS['A']}.mp4")
    monkeypatch.setattr(purge, "open_paths", lambda: None)
    rep = purge.run_pass(tree["spec"], q=tree["q"], now=NOW, log_dir=tree["logs"], store_root=str(tree["tmp"] / "s"))
    assert "/proc not readable" in rep["refused"] and _exists(tree, f"runs/pinned_old/sources/{VIDS['A']}.mp4")


def test_the_spec_refuses_a_protected_path_a_relative_path_or_another_expiry(tmp_path):
    base = json.load(open(config.PURGE_SPEC))
    for bad in ("/home/ultron/protocol_pulse/references/*", "/home/ultron/protocol_pulse/runs/*/out",
                "runs/*", "/home/ultron/protocol_pulse/runs/../references"):
        s = json.loads(json.dumps(base))
        s["targets"][0]["units"] = bad
        p = tmp_path / "s.json"
        p.write_text(json.dumps(s))
        with pytest.raises(purge.SpecError):
            purge.load_spec(str(p))
    s = json.loads(json.dumps(base))
    s["expiry_h"] = 24
    p.write_text(json.dumps(s))
    with pytest.raises(purge.SpecError, match="expiry_h"):
        purge.load_spec(str(p))


def test_the_real_spec_targets_only_acquired_sources_and_the_word_pass_temp():
    spec = purge.load_spec()
    assert spec["expiry_h"] == 12 and spec["every_s"] == 600
    assert [(t["name"], t["enabled"]) for t in spec["targets"]] == [
        ("run_sources", True), ("lock_precheck_sources", True), ("word_pass_temp", True)]
    assert {"TELEGRAM_DELIVERY.json", "TELEGRAM_DELIVERY.lock", "REVIEW_DROP.json"} <= set(spec["delivered"]["markers"])
    for t in spec["targets"]:
        assert not any(b in f"{t['units']}/{t['files']}/" for b in purge.FORBIDDEN)
    assert ".json" not in spec["media_ext"] and ".txt" not in spec["media_ext"]


def test_youtube_urls_and_id_keys_name_videos_in_records():
    out = purge._ids({"a": [{"video_id": "AAAAAAAAAAA"}, "https://youtu.be/BBBBBBBBBBB?t=3",
                            {"url": "https://www.youtube.com/watch?v=CCCCCCCCCCC&t=1"}], "vid": "short"}, set())
    assert out == {"AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC"}


def test_only_videos_cut_into_a_delivery_are_protected_not_every_video_a_record_mentions(tree):
    """A failures reference (no verdict, preview, delivery, pin or EDL) protects nothing; a delivered run's review
    record that mentions an alternative does not make the alternative delivered."""
    V, main = VIDS, tree["main"]
    _touch(str(main / "references" / "editorial_failures" / "case1" / "x.json"),
           data=json.dumps({"video_id": V["B"]}).encode())
    _touch(str(main / "runs" / "pinned_delivered" / "EDITORIAL_REVIEW.json"),
           data=json.dumps({"alternatives": [{"video_id": V["A"]}]}).encode())
    _age_dir(str(main / "runs" / "pinned_delivered"), 3)
    vids, runs, problems, units = purge.delivered(tree["spec"])
    assert V["D"] in vids and V["F"] in vids and V["G"] in vids
    assert V["A"] not in vids and V["B"] not in vids and not problems
    rep = _run(tree)
    assert not _exists(tree, f"runs/pinned_old/sources/{V['A']}.mp4")


def test_a_bare_upload_date_is_read_as_the_end_of_that_day_so_nothing_is_deleted_early(tree):
    """A meta time at exactly midnight with no recorded source may be a date: the video is kept until 12 h after the
    END of that day."""
    V, main = VIDS, tree["main"]
    day = (NOW - timedelta(hours=20)).replace(hour=0, minute=0, second=0)
    _touch(str(main / "data" / "editorial" / "transcripts" / V["C"] / "meta.json"),
           data=json.dumps({"published_at": day.isoformat()}).encode())
    rep = _run(tree)
    late = day + timedelta(days=1) + timedelta(hours=12) > NOW
    assert _exists(tree, f"runs/pinned_old/sources/{V['C']}.mp4") == late
    assert purge._latest(day, "youtube_rss") == day and purge._latest(day, None) == day + timedelta(days=1)


def test_a_corrupt_record_of_a_delivered_run_stops_the_pass(tree):
    """Audit r77 c1 (glm P1): a delivered run's edl.json that cannot be parsed must not silently shrink the delivered
    set: nothing is deleted that pass."""
    _touch(str(tree["main"] / "runs" / "pinned_delivered" / "edl.json"), data=b"{not json")
    _age_dir(str(tree["main"] / "runs" / "pinned_delivered"), 3)
    rep = _run(tree)
    assert rep["refused"] and "edl.json not readable" in rep["refused"] and rep["freed_bytes"] == 0
    assert _exists(tree, f"runs/pinned_old/sources/{VIDS['A']}.mp4")


def test_an_unreadable_directory_makes_its_run_in_use(tree):
    """Audit r77 c1 (qwen): activity behind an unreadable directory is unknown, so the run counts as in use."""
    locked = tree["main"] / "runs" / "pinned_old" / "qa"
    os.chmod(str(locked), 0)
    try:
        rep = _run(tree)
    finally:
        os.chmod(str(locked), 0o755)
    assert _exists(tree, f"runs/pinned_old/sources/{VIDS['A']}.mp4")
    assert rep["kept"]["its run or unit is in use (touched under 2 h ago)"]["files"] >= 2


def test_a_file_exactly_12_h_after_its_publish_time_is_expired_as_in_the_adapter(tree):
    """Audit r77 c1 (muse P2): the boundary is the adapter's: at publish + 12 h the moment is expired and its media
    goes."""
    tree["q"].pub[VIDS["B"]] = NOW - timedelta(hours=12)
    rep = _run(tree)
    assert not _exists(tree, f"runs/pinned_old/sources/{VIDS['B']}.mp4")


@pytest.mark.parametrize("edit", [
    lambda s: s.update(targets={"a": 1}),
    lambda s: s["targets"][0].update(enabled="yes"),
    lambda s: s["delivered"].update(markers="TELEGRAM_DELIVERY.json"),
    lambda s: s["delivered"].update(runs="runs/*"),
    lambda s: s.update(publish_time={}),
])
def test_the_spec_refuses_wrong_types(tmp_path, edit):
    s = json.load(open(config.PURGE_SPEC))
    edit(s)
    p = tmp_path / "s.json"
    p.write_text(json.dumps(s))
    with pytest.raises(purge.SpecError):
        purge.load_spec(str(p))


# ── the orchestrator's 08:15 ruling 3 (A19, Nov 14): ONE COPY PER DELIVERY ──

def _sha(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _delivery(tree, name, files, prov, marker="TELEGRAM_DELIVERY.json", where="runs"):
    """A delivery unit (a run with a delivery record, or a reference with a marker) holding `files` {name: bytes} in
    its sources/ and a PROVENANCE.json naming `prov` [(video id, file, sha256)]."""
    unit = tree["main"] / where / name
    for fn, data in files.items():
        _touch(str(unit / "sources" / fn), data=data)
    _touch(str(unit / "PROVENANCE.json"), data=json.dumps({"sources": [
        {"video_id": v, "file": f, "sha256": h} for v, f, h in prov]}).encode())
    _touch(str(unit / marker), data=b"{}")
    _age_dir(str(unit), 3)
    return unit


def _copy(tree, run, vid, data):
    unit = tree["main"] / "runs" / run
    _touch(str(unit / "sources" / f"{vid}.mp4"), data=data)
    _age_dir(str(unit), 3)


K = "K" * 11


def test_one_copy_per_delivery_keeps_the_section_its_provenance_names_by_hash_and_deletes_the_other_copies(tree):
    """A19: the delivery run's own section, whose sha256 its PROVENANCE names, stays; a replay's identical copy and a
    run's different cut of the same video go (expired, idle, not open), each deletion naming the copy kept."""
    good = b"the delivered section"
    _delivery(tree, "pinned_dl", {f"{K}.mp4": good}, [(K, f"{K}.mp4", _sha(good))])
    _copy(tree, "pinned_dl_replay", K, good)
    _copy(tree, "pinned_k_cut", K, b"another cut of the video")
    tree["q"].pub[K] = NOW - timedelta(hours=30)
    rep = _run(tree)
    kept = os.path.realpath(str(tree["main"] / "runs" / "pinned_dl" / "sources" / f"{K}.mp4"))
    assert os.path.exists(kept)
    assert not _exists(tree, f"runs/pinned_dl_replay/sources/{K}.mp4") and not _exists(tree, f"runs/pinned_k_cut/sources/{K}.mp4")
    lines = [json.loads(l) for l in open(os.path.join(tree["logs"], "deleted.jsonl")) if K in l]
    assert len(lines) == 2 and all(l["other_copy_of_delivered"] and l["kept_copies"] == [kept] for l in lines)
    assert K not in rep["one_copy_per_delivery"]["unresolved"]


def test_a_delivery_whose_own_file_is_not_the_attested_one_keeps_the_copy_with_its_hash(tree):
    """The delivery's own sources/ file differs from the bytes its PROVENANCE names (re-acquired since): the copy with
    the named sha256, in another run, is the one kept; the delivery's own file is just another copy."""
    good = b"the delivered section"
    _delivery(tree, "pinned_dl", {f"{K}.mp4": b"re-acquired later"}, [(K, f"{K}.mp4", _sha(good))])
    _copy(tree, "pinned_dl_replay", K, good)
    tree["q"].pub[K] = NOW - timedelta(hours=30)
    _run(tree)
    assert _exists(tree, f"runs/pinned_dl_replay/sources/{K}.mp4") and not _exists(tree, f"runs/pinned_dl/sources/{K}.mp4")


def test_a_hash_no_copy_has_and_a_copy_that_cannot_be_read_keep_every_copy(tree, monkeypatch):
    """Fail closed: when the copy a delivery names cannot be identified (no file with its sha256; a candidate that
    cannot be read), every copy of that video is kept and the video is reported unresolved."""
    _delivery(tree, "pinned_dl", {f"{K}.mp4": b"x"}, [(K, f"{K}.mp4", "0" * 64)])
    _copy(tree, "pinned_dl_replay", K, b"x")
    tree["q"].pub[K] = NOW - timedelta(hours=30)
    rep = _run(tree)
    assert _exists(tree, f"runs/pinned_dl/sources/{K}.mp4") and _exists(tree, f"runs/pinned_dl_replay/sources/{K}.mp4")
    assert "no copy with its PROVENANCE's sha256" in rep["one_copy_per_delivery"]["unresolved"][K]
    good = b"the delivered section"
    _delivery(tree, "pinned_dl2", {f"{K}.mp4": good}, [(K, f"{K}.mp4", _sha(good))])
    monkeypatch.setattr(purge, "sha256_of", lambda p: (_ for _ in ()).throw(PermissionError(p)))
    rep = _run(tree)
    assert _exists(tree, f"runs/pinned_dl2/sources/{K}.mp4") and _exists(tree, f"runs/pinned_dl_replay/sources/{K}.mp4")
    assert K in rep["one_copy_per_delivery"]["unresolved"]


def test_a_reference_holding_the_delivered_section_lets_the_runs_copies_go(tree):
    """A reference with delivery evidence holds the attested section itself (a protected path, never a target): the
    runs' copies of that video are other copies and go; the reference's file stays."""
    good = b"the delivered section"
    ref = _delivery(tree, "pulse_ref", {f"{K}.mp4": good}, [(K, f"{K}.mp4", _sha(good))], marker="PIN.json",
                    where="references")
    _copy(tree, "pinned_replay_of_ref", K, good)
    tree["q"].pub[K] = NOW - timedelta(hours=30)
    rep = _run(tree)
    assert os.path.exists(str(ref / "sources" / f"{K}.mp4"))
    assert not _exists(tree, f"runs/pinned_replay_of_ref/sources/{K}.mp4")
    assert rep["one_copy_per_delivery"]["kept_copies"] >= 1


def test_a_delivered_run_whose_provenance_omits_a_video_it_cut_keeps_its_own_section_of_it(tree):
    """A video the delivery cut (named by its EDL) that its PROVENANCE does not list keeps the delivery's own
    section by name; with no own section either, every copy is kept (unresolved)."""
    good = b"listed"
    unit = _delivery(tree, "pinned_dl", {f"{K}.mp4": good, f"{VIDS['B']}.mp4": b"unlisted own"},
                     [(K, f"{K}.mp4", _sha(good))])
    _touch(str(unit / "edl.json"), data=json.dumps({"clips": [{"video_id": VIDS["B"]}, {"video_id": VIDS["C"]}]}).encode())
    _age_dir(str(unit), 3)
    _copy(tree, "pinned_b_other", VIDS["B"], b"unlisted own")
    tree["q"].pub[K] = NOW - timedelta(hours=30)
    tree["q"].pub[VIDS["B"]] = NOW - timedelta(hours=30)
    tree["q"].pub[VIDS["C"]] = NOW - timedelta(hours=30)      # audit a19 c1 (glm C15): expired, so only the rule keeps it
    rep = _run(tree)
    assert _exists(tree, f"runs/pinned_dl/sources/{VIDS['B']}.mp4")             # its own section, by name
    assert not _exists(tree, f"runs/pinned_b_other/sources/{VIDS['B']}.mp4")
    assert VIDS["C"] in rep["one_copy_per_delivery"]["unresolved"]               # cut, no hash, no own section
    assert _exists(tree, f"runs/pinned_old/sources/{VIDS['C']}.mp4")             # expired and idle: kept as unresolved
    assert rep["kept"]["a delivered video whose delivery copy is not identified (every copy kept)"]["files"] >= 1


@pytest.mark.parametrize("fn", [f"{K}.mp4", "section_1.mp4"])
def test_an_attested_section_in_a_references_run_sources_is_kept_and_named_and_the_runs_copies_go(tree, fn):
    """Audit a19 c1 (glm P1; qwen's P1 refuted): the attested copy sits in a reference's run/sources/ (never a
    target), its PROVENANCE naming a plain file name (the video id's, or another): it is found there, kept, and named
    in each deletion's kept_copies by the video it was kept for; the runs' copies of the video go; it is resolved."""
    good = b"the delivered section"
    ref = tree["main"] / "references" / "v2f_like"
    _touch(str(ref / "run" / "sources" / fn), data=good)
    _touch(str(ref / "PROVENANCE.json"), data=json.dumps({"sources": [
        {"video_id": K, "file": fn, "sha256": _sha(good)}]}).encode())
    _touch(str(ref / "PIN.json"), data=b"{}")
    _age_dir(str(ref), 3)
    _copy(tree, "pinned_replay", K, good)
    _copy(tree, "pinned_k_cut", K, b"another cut of the video")
    tree["q"].pub[K] = NOW - timedelta(hours=30)
    rep = _run(tree)
    kept = os.path.realpath(str(ref / "run" / "sources" / fn))
    assert os.path.exists(kept)
    assert not _exists(tree, f"runs/pinned_replay/sources/{K}.mp4") and not _exists(tree, f"runs/pinned_k_cut/sources/{K}.mp4")
    lines = [json.loads(l) for l in open(os.path.join(tree["logs"], "deleted.jsonl")) if l.strip()]
    lines = [l for l in lines if l["video_id"] == K]
    assert len(lines) == 2 and all(l["other_copy_of_delivered"] and l["kept_copies"] == [kept] for l in lines)
    assert K not in rep["one_copy_per_delivery"]["unresolved"]


def test_the_hash_cache_is_bounded(tmp_path, monkeypatch):
    """Audit a19 c1 (glm C5): the watcher runs for days; the sha256 cache is emptied when it reaches its bound, and
    a hash read after that is still right."""
    monkeypatch.setattr(purge, "_SHA", {})
    monkeypatch.setattr(purge, "SHA_CACHE_MAX", 3)
    paths = [_touch(str(tmp_path / f"f{i}.mp4"), data=str(i).encode()) for i in range(5)]
    for p in paths:
        assert purge.sha256_of(p) == _sha(open(p, "rb").read())
        assert len(purge._SHA) <= 3
