"""FAMILY 2 - coordinates and provenance (E-FAIL-002: the offset recorded must be the file's; E-FAIL-001: a lock
is sealed at selection and never recomputed; GPT-select F09 / F10, Grok47-select F5 / F6).

A synthetic two-source selection run (adv_helpers.write_source: speech-like audio with its exact word transcript,
each source a window downloaded at a KNOWN full-video offset) goes through the public entry points:
  select_passages.select_and_build_edl   download cache + transcript cache + sentence-law anchor + lock
  sentence_law.write_lock_cut_table      cuts inside the locked pauses
  sentence_law.gate_g16 / verify_lock    the lock checked against the transcript (and the media) on disk
yt-dlp is replaced by a stand-in that fails like a machine without network (it must not even be called on a cache
hit) and Whisper by a stub that refuses to load, so nothing leaves the CPU.
"""
import json
import os
import shutil

import pytest

import adv_helpers as H

HOOK_VID, CLIP_VID = "VIDAAAAAAAA", "VIDBBBBBBBB"
HOOK_OFFSET, CLIP_OFFSET = 45, 120


@pytest.fixture(scope="module")
def template(tmp_path_factory):
    """One clean run directory (sources, transcripts, passages.json), built once and copied per test."""
    rd = str(tmp_path_factory.mktemp("f2_template") / "run")
    os.makedirs(rd)
    hook, hw, hr = H.write_source(rd, HOOK_VID, H.HOOK_TEXT, offset=HOOK_OFFSET, seed=1)
    clip, cw, cr = H.write_source(rd, CLIP_VID, H.CLIP_TEXT, offset=CLIP_OFFSET, seed=2)
    H.passages_json(rd, hook, clip)
    return {"dir": rd, "hook": hook, "clip": clip, "hw": hw, "hr": hr, "cw": cw, "cr": cr}


@pytest.fixture
def run(template, tmp_path, monkeypatch):
    import select_passages as SP
    rd = str(tmp_path / "run")
    shutil.copytree(template["dir"], rd)
    fake = H.FakeYtDlp()
    monkeypatch.setattr(SP, "subprocess", fake)
    return {**template, "dir": rd, "ytdlp": fake}


@pytest.fixture(scope="module")
def cut_template(template, tmp_path_factory):
    """The template after select + cut table + G16 PASS, made ONCE (the lock-binding tests copy it)."""
    import select_passages as SP
    import sentence_law as L
    rd = str(tmp_path_factory.mktemp("f2_cut") / "run")
    shutil.copytree(template["dir"], rd)
    real, SP.subprocess = SP.subprocess, H.FakeYtDlp()
    try:
        H.control(SP.select_and_build_edl("bitcoin", "bitcoin", rd) is True, "select on the clean template")
    finally:
        SP.subprocess = real
    cuts = L.write_lock_cut_table(rd)
    H.control(all(c["verified"] for c in cuts), f"cut table on the clean template: {cuts}")
    ok, table = L.gate_g16(rd)
    H.control(ok, f"G16 on the clean template: {table}")
    return {**template, "dir": rd}


@pytest.fixture
def cut_run(cut_template, tmp_path, monkeypatch):
    import select_passages as SP
    rd = str(tmp_path / "run")
    shutil.copytree(cut_template["dir"], rd)
    monkeypatch.setattr(SP, "subprocess", H.FakeYtDlp())
    return {**cut_template, "dir": rd}


def _select(run):
    import select_passages as SP
    return SP.select_and_build_edl("bitcoin", "bitcoin", run["dir"])


def _edl(run):
    return json.load(open(os.path.join(run["dir"], "edl.json")))


def _replace_source(run, vid, passage, seed, voice, offset):
    """New bytes under the same name: the same speech timing (every pause where it was), other content, and the
    download record rewritten for them (a re-download properly recorded), so only a binding of the transcript /
    lock to the media bytes can tell (R-10), not the download record (R-09)."""
    x, _, dur, _ = H.source_audio(passage, seed=seed, voice=voice)
    H.make_media(os.path.join(run["dir"], "sources", f"{vid}.mp4"), x)
    H.write_section(run["dir"], vid, offset, offset + dur)


class TestKnownOffset:
    def test_a_window_at_a_known_offset_is_recorded_in_file_coordinates(self, run):
        assert _select(run) is True
        assert run["ytdlp"].calls == []                                  # a valid cache hit downloads nothing
        e = _edl(run)
        for seg, words, (i0, i1), off, p in ((e["hook"], run["hw"], run["hr"], HOOK_OFFSET, run["hook"]),
                                             (e["clips"][0], run["cw"], run["cr"], CLIP_OFFSET, run["clip"])):
            assert seg["time_coords"] == "source_file"
            assert seg["source_window_offset_s"] == off                  # the requested whole-second start
            assert seg["word_start"] == words[i0]["start"] and seg["word_end"] == words[i1]["end"]
            assert abs(seg["word_start"] + off - p["start"]) < 1e-6     # file + offset = full-video time
            assert seg["selection_lock"]["first_word"] == p["text"].split()[0]
            assert seg["selection_lock"]["last_word"] == p["text"].split()[-1]

    def test_cuts_sit_in_the_pauses_around_the_locked_words_and_g16_passes(self, cut_run):
        import sentence_law as L
        run = cut_run                                    # selected + cut table written (cut_template)
        cuts = {c["clip_id"]: c for c in json.load(open(os.path.join(run["dir"], "cuts_final.json")))}
        e = _edl(run)
        for label, seg in (("hook", e["hook"]), ("clip_01", e["clips"][0])):
            c = cuts[label]
            assert c["verified"] is True, c
            assert seg["word_start"] - 0.6 < c["cut_in"] < seg["word_start"]       # inside the 0.5 s pause
            assert seg["word_end"] < c["cut_out"] < seg["word_end"] + 0.6
        ok, table = L.gate_g16(run["dir"])
        assert ok, table


class TestDirtyCache:
    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F09 (OPEN): a cached download is relabelled with the newly "
                                           "requested offset; REQUESTS.md R-09")
    def test_a_cached_window_of_another_request_is_never_relabelled(self, run):
        """sources/<hook>.mp4 is an OLD download of the window at 285 s (the host repeats the hook sentences at
        300 s); the editor's verified passage is at 60 s, so the new request starts at 45 s. Whatever happens,
        the EDL must never record 45 s for a file that starts at 285 s."""
        import select_passages as SP
        rd = run["dir"]
        old, ow, (oi0, _) = H.write_source(rd, HOOK_VID, H.HOOK_TEXT, offset=285, seed=7)   # the stale cache
        first = ow[oi0]["start"]                           # the passage's place in a window (same layout)
        hook = {**run["hook"], "start": HOOK_OFFSET + first, "end": HOOK_OFFSET + first + old["duration"]}
        H.passages_json(rd, hook, run["clip"])
        ok = SP.select_and_build_edl("bitcoin", "bitcoin", rd)
        assert ok is False or _edl(run)["hook"]["source_window_offset_s"] == 285, _edl(run)["hook"]

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F10 (OPEN): the transcript cache is keyed by video id, not "
                                           "by the bytes it transcribed; REQUESTS.md R-10")
    def test_a_transcript_of_other_bytes_is_never_used(self, cut_run, whisper_attempts):
        """The source's bytes changed under the same name (same timing, other content); its cached transcript
        describes the old bytes. select must transcribe the new bytes (here: refused, so no EDL) or stop."""
        run = cut_run
        os.remove(os.path.join(run["dir"], "edl.json"))
        _replace_source(run, HOOK_VID, H.HOOK_TEXT, seed=99, voice=3.0, offset=HOOK_OFFSET)
        try:
            ok = _select(run)
        except RuntimeError as e:                          # a re-transcription attempt refused by the Whisper stub
            H.control("forbidden" in str(e), f"select raised something else: {e}")
            ok = False
        assert ok is False or whisper_attempts(), "the old transcript was used for new bytes"

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F23 (OPEN): yt-dlp's exit status is ignored and a partial "
                                           "file already under the name is taken as the download; REQUESTS.md R-22")
    def test_a_failed_download_never_supplies_a_source(self, run):
        """sources/<hook>.mp4 is a 10-100 KB leftover (too small for a cache hit, so yt-dlp runs); yt-dlp exits 1
        and writes nothing. Nothing from that video may be selected."""
        x, words, _, (_, i1) = H.source_audio(H.HOOK_TEXT, seed=1)
        cut = int((words[i1]["end"] + 2.0) * 48000)                    # a truncated download: the hook, then 2 s
        p = os.path.join(run["dir"], "sources", f"{HOOK_VID}.mp4")
        H.make_media(p, x[:cut:3], sr=16000, audio_kbps=12, size=(16, 16))
        os.remove(os.path.join(run["dir"], "sources", f"{HOOK_VID}.section.json"))   # a partial download has none
        H.control(10_000 < os.path.getsize(p) <= 100_000, f"leftover size {os.path.getsize(p)}")
        ok = _select(run)
        H.control(any(f"watch?v={HOOK_VID}" in " ".join(c) for c in run["ytdlp"].calls), "yt-dlp was asked (and failed)")
        assert ok is False, "a failed download supplied the hook"

    def test_yt_dlp_failure_on_a_cache_miss_selects_nothing(self, run):
        """Control: no cached file and a failing yt-dlp = no source = no EDL (and yt-dlp WAS asked)."""
        os.remove(os.path.join(run["dir"], "sources", f"{HOOK_VID}.mp4"))
        os.remove(os.path.join(run["dir"], "sources", f"{HOOK_VID}.section.json"))
        assert _select(run) is False
        assert any(f"watch?v={HOOK_VID}" in " ".join(c) for c in run["ytdlp"].calls)


class TestSelectContract:
    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F08 (OPEN, D: SELECT = hook + >= 2 clips + the required "
                                           "channels): success with one clip; REQUESTS.md R-23")
    def test_select_with_fewer_than_two_clips_is_not_a_success(self, run):
        ok = _select(run)                                   # the template has a hook and ONE clip
        assert ok is False or len(_edl(run)["clips"]) >= 2, f"SELECT reported success with {len(_edl(run)['clips'])} clip"

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F08 (OPEN; R5: >= 2 distinct channels): success with one "
                                           "channel; REQUESTS.md R-23")
    def test_select_with_one_channel_is_not_a_success(self, run):
        H.passages_json(run["dir"], run["hook"], run["clip"], hook_channel="DataDash", clip_channel="DataDash")
        ok = _select(run)
        assert ok is False or len({_edl(run)["hook"]["channel"]} | {c["channel"] for c in _edl(run)["clips"]}) >= 2

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="Claude-gates T3 / named answer #3 (OPEN): the EDL never names the "
                                           "source's next word, so G3b's leak check never runs; REQUESTS.md R-18")
    def test_every_segment_names_the_next_source_word_for_g3b(self, run):
        H.control(_select(run) is True, "select on the clean template")
        e = _edl(run)
        missing = [lab for lab, s in [("hook", e["hook"])] + [(f"clip_{c['index']:02d}", c) for c in e["clips"]]
                   if not s.get("next_source_word")]
        assert not missing, missing


class TestLockBinding:
    """Each test starts from cut_run: selected, cut table written, G16 PASS (the control, made once)."""

    def test_a_lock_checked_against_another_transcript_is_refused(self, cut_run):
        """The transcript on disk is not the one the lock was made on (one word changed): verify_lock, the cut
        table and G16 all refuse it."""
        import sentence_law as L
        run = cut_run
        tp = os.path.join(run["dir"], "transcripts", f"{HOOK_VID}.json")
        d = json.load(open(tp))
        d["words"][run["hr"][0] + 2]["word"] = "nearly"
        with open(tp, "w") as f:
            json.dump(d, f)
        lock = _edl(run)["hook"]["selection_lock"]
        assert any("transcript changed" in e for e in L.verify_lock(lock, tp))
        ok, table = L.gate_g16(run["dir"])
        assert not ok and any("transcript changed" in e for e in table[0]["errors"]), table
        cut = next(c for c in L.write_lock_cut_table(run["dir"]) if c["clip_id"] == "hook")
        assert cut["verified"] is False and "transcript changed" in cut["error"]

    def test_a_lock_edited_after_selection_is_refused(self, cut_run):
        import sentence_law as L
        run = cut_run
        lock = dict(_edl(run)["hook"]["selection_lock"])
        lock["last_word"] = "September."
        assert any("modified after selection" in e for e in L.verify_lock(lock))

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="PP-02 (new): verify_lock compares only the transcript's digest, never "
                                           "the lock's words with the transcript's words at i0..i1; REQUESTS.md R-11")
    def test_a_lock_whose_words_are_not_its_transcripts_words_is_refused(self, cut_run):
        """A lock built from ANOTHER transcript's words but carrying the digest of the file on disk (a rewrite
        between hashing and reading, a concurrent attempt in the same run directory): verify_lock must see that
        its first / last word and text are not that transcript's words at its indices."""
        import sentence_law as L
        run = cut_run
        tp = os.path.join(run["dir"], "transcripts", f"{HOOK_VID}.json")
        i0, i1 = run["hr"]
        other = [dict(w) for w in run["hw"]]
        other[i0]["word"], other[i1]["word"] = "Ether", "carefully."
        lock = L.make_lock(HOOK_VID, other, i0, i1, L.sha256_file(tp), run["hook"]["text"], None, 1.0, "test")
        assert L.verify_lock(lock, tp) != []

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F10 / Grok47-select F6 (OPEN): the lock and the cut table "
                                           "bind the transcript's digest, never the source media's; REQUESTS.md R-10")
    def test_g16_refuses_a_source_whose_bytes_changed_after_the_lock(self, cut_run):
        """Same name, same speech timing, other content (a re-download of another rendition, a rerun on a dirty
        run directory): every cut is still 'legal' by the envelope, but it is no longer the audio the editor's
        sentence was located in. G16 must refuse the changed bytes."""
        import sentence_law as L
        run = cut_run
        _replace_source(run, HOOK_VID, H.HOOK_TEXT, seed=99, voice=3.0, offset=HOOK_OFFSET)
        ok, table = L.gate_g16(run["dir"])
        assert not ok, table
