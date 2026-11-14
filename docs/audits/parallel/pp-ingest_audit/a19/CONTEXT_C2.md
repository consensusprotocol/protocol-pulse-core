### The order (orchestrator 08:15 ET Nov 14, to pp-ingest, ruling 3, verbatim)
"(3) A19: ONE COPY PER DELIVERY. Keep the acquired source section(s) the delivered pin's PROVENANCE names, by hash;
delete the other cached copies. Report the disk freed."

### Background
Ruling 77's rolling purge (purge.py, the watcher's own loop every 600 s) deletes MEDIA of videos published more than
12 h ago from the targets purge.json names (runs/*/sources/, the lock precheck's sources/, abandoned word-pass temp),
never from references/, out/, qa/, VERIFY/, transcripts or records. Until now a DELIVERED video's media was kept
"wherever it lies" (STATE A19: read literally, so every cached copy of a delivered video was kept: re-renders,
replays, recuts; the orchestrator has now ruled one copy per delivery). A delivery = a run with a delivery record
(TELEGRAM_DELIVERY.json / .lock, REVIEW_DROP.json), a run that rendered a pin the stand-alone scorer records as
delivered, or a reference with delivery evidence (PBX_VERDICT.md, TELEGRAM_PREVIEW.json, TELEGRAM_DELIVERY.json,
PIN.json, run/edl.json). A delivered run's PROVENANCE.json lists its sources as {video_id, file: "<id>.mp4", sha256,
bytes, ...}, the file in the run's own sources/.

### The change (016965a4; diff against d64b24ba below)
- purge.delivered() also returns the delivery units with their videos [(dir, {video ids})].
- purge.kept_copies(units, copies, exts): per delivery, each PROVENANCE source (video_id, file, sha256): its own
  sources/<file> (or run/sources/<file>; file must be a plain basename) when its sha256 matches, else the first
  (sorted) target copy of that video with the sha256; found -> kept (by real path); not found, or no sha256 named
  -> the video is UNRESOLVED (every copy kept). A video the delivery cut that its PROVENANCE does not list, or every
  video of a delivery whose PROVENANCE names no sources: the delivery's own section(s) <unit>/sources/<id>.* and
  run/sources/<id>.* are kept by name; none -> unresolved. sha256_of(): cached by (real path, size, mtime_ns); an
  unreadable candidate is never taken for the attested copy.
- run_pass: collects the targets' copies of delivered videos first, computes the kept set, then for a delivered
  video's file: kept copy -> kept ("a delivered video's kept copy (one per delivery)"); unresolved -> kept ("... not
  identified (every copy kept)"); else it is "another cached copy" and goes through the usual rules (publish time
  measured and > 12 h ago, its unit idle 2 h, not open in a process); a deletion (and a dry run's would_delete) names
  the kept copies of that video; rep["one_copy_per_delivery"] {kept_copies, unresolved, other_copies {files, bytes}};
  summary() reports it. The problems check (an unreadable delivered set or /proc refuses the whole pass) is unchanged
  and runs first.
- purge.json: the order text and the delivered note say it. Design section 12.

### Measured before going live (a read-only dry run of this code on the real runs, no logs written)
15 deliveries (10 runs, 5 references), 15 delivered videos; every PROVENANCE hash found (0 unresolved); 46 copies kept
(30 in runs, 16 in references); would free 3.36 GB: 121 other copies of delivered videos (115 run sources, 6 lock
precheck sections), all in old pinned / replay / recut runs. 3 more copies (QCgW8RlTu5Q, the v2f reference's video,
1.18 GB each, in the Nov 7 runs) stay: the purge never deletes a file whose publish time is not measured.

### The readings (to be STATE assumptions)
- A43 "the delivered pin's PROVENANCE ... by hash": each delivery's own PROVENANCE; ONE copy per DELIVERY (two
  deliveries of the same video keep a copy each); its own sources/ copy preferred when the hash matches.
- A44 a delivery without PROVENANCE sources (an older run, the Nov 11 preview and v2f references) keeps its own acquired
  section(s) by name: no hash is named, and they are the delivery's own copies; with none, every copy is kept.
- A45 the references' own copies are never targets (protected paths) and count as their delivery's kept copy, so the
  runs' copies of a reference's video are other copies.

### Questions for the reviewers
1. Can a delivery's attested copy ever be deleted (path forms, symlinks, realpath compare, a unit that is both a
   target and a delivery, a hash cache gone stale)? Can an unresolved video lose a copy?
2. Is the sha256 identity right (cache key, partial reads, a file replaced in place), and is the cost per pass sane?
3. Anything else that read "a delivered video's media is kept" (stats, the CLI, the tests) and now misleads?
4. Do the tests prove it, and which must-fail case is missing?

### The tests (tests/ingest/test_purge.py, new; the fixture and _run / _exists are the file's)
```python
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
    rep = _run(tree)
    assert _exists(tree, f"runs/pinned_dl/sources/{VIDS['B']}.mp4")             # its own section, by name
    assert not _exists(tree, f"runs/pinned_b_other/sources/{VIDS['B']}.mp4")
    assert VIDS["C"] in rep["one_copy_per_delivery"]["unresolved"]               # cut, no hash, no own section
    assert _exists(tree, f"runs/pinned_old/sources/{VIDS['C']}.mp4")             # (its publish time is unknown too)
```

### Cycle 1 (147c4884): what changed since 016965a4 (details in C1_CONSENSUS.md)
- purge.kept_copies returns {real path: (video id, why)}: run_pass's kept_of (each deletion's deleted.jsonl
  `kept_copies`) lists the copies kept FOR that video id, computed only for another copy of a delivered video (it was
  derived from the kept file's name, which a PROVENANCE `file` not named by its video id would have missed).
- purge.sha256_of: the module-level cache is emptied at SHA_CACHE_MAX = 4,096 entries (the watcher runs for days).
- tests: an attested copy in a reference's run/sources/ (PROVENANCE file "<id>.mp4" and "section_1.mp4"): kept,
  named in kept_copies, the runs' copies go, resolved; the cache bound; the omitted-video test's video given an
  expired publish time so only the unresolved rule keeps it. Each fails with its fix reverted (mutation-checked).
- design 12: the own run/sources/<file>, the cache bound, kept_copies by video id, and the one case not looked for (an
  attested copy only in ANOTHER unit's non-target directory: unresolved, every copy kept).
- qwen's c1 P1 (run/sources/ not collected into copies) is refuted in C1_CONSENSUS.md: copies lists only the files the
  purge may delete; kept_copies checks the delivery's own sources/ and run/sources/ first.
