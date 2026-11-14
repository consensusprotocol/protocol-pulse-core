"""FAMILY 2 - coordinates and provenance (E-FAIL-002: the offset recorded must be the file's; E-FAIL-001: a lock
is sealed at selection and never recomputed; GPT-select F09 / F10, Grok47-select F5 / F6).

A synthetic three-source selection run (adv_helpers.write_source: speech-like audio with its exact word transcript,
each source a window downloaded at a KNOWN full-video offset; a hook and two clips from three channels, so the
selection contract D / R-23 holds and its fix keeps every control valid: integrator B2) goes through the public
entry points:
  select_passages.select_and_build_edl   download cache + transcript cache + sentence-law anchor + lock
  sentence_law.write_lock_cut_table      cuts inside the locked pauses
  sentence_law.gate_g16 / verify_lock    the lock checked against the transcript (and the media) on disk
yt-dlp is replaced by a stand-in that fails like a machine without network (it must not even be called on a cache
hit). Whisper never loads: select's load goes through law L-r's GPU0 lease (pipeline/gpu0.py), which refuses this CPU
suite (a Gpu0Stop), and the faster_whisper stub (conftest.py) refuses any load outside it; nothing leaves the CPU. A
test that needs a transcription to FAIL in the ordinary way injects it at select's seam (_whisper_transcribe -> None).
"""
import json
import os
import shutil

import pytest

import adv_helpers as H

HOOK_VID, CLIP_VID, CLIP2_VID = "VIDAAAAAAAA", "VIDBBBBBBBB", "VIDCCCCCCCC"
HOOK_OFFSET, CLIP_OFFSET, CLIP2_OFFSET = 45, 120, 200


@pytest.fixture(scope="module")
def template(tmp_path_factory):
    """One clean run directory (sources, transcripts, passages.json), built once and copied per test: a hook and TWO
    clips, three channels (DataDash, Natalie Brunell, Yahoo Finance)."""
    rd = str(tmp_path_factory.mktemp("f2_template") / "run")
    os.makedirs(rd)
    hook, hw, hr = H.write_source(rd, HOOK_VID, H.HOOK_TEXT, offset=HOOK_OFFSET, seed=1)
    clip, cw, cr = H.write_source(rd, CLIP_VID, H.CLIP_TEXT, offset=CLIP_OFFSET, seed=2)
    clip2, c2w, c2r = H.write_source(rd, CLIP2_VID, H.CLIP2_TEXT, offset=CLIP2_OFFSET, seed=3)
    H.passages_json(rd, hook, [clip, clip2])
    return {"dir": rd, "hook": hook, "clip": clip, "clip2": clip2, "hw": hw, "hr": hr, "cw": cw, "cr": cr,
            "c2w": c2w, "c2r": c2r}


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
    H.control(len(cuts) == 3 and all(c["verified"] for c in cuts), f"cut table on the clean template: {cuts}")
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


def _tree(d):
    """The whole state of a run directory: {relative path: (size, mtime_ns)} of every file, None for a directory."""
    out = {}
    for root, dirs, files in os.walk(d):
        for name in dirs:
            out[os.path.relpath(os.path.join(root, name), d) + os.sep] = None
        for name in files:
            st = os.stat(os.path.join(root, name))
            out[os.path.relpath(os.path.join(root, name), d)] = (st.st_size, st.st_mtime_ns)
    return out


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
        assert [c["channel"] for c in e["clips"]] == list(H.CHANNELS[1:]) and e["hook"]["channel"] == H.CHANNELS[0]
        for seg, words, (i0, i1), off, p in ((e["hook"], run["hw"], run["hr"], HOOK_OFFSET, run["hook"]),
                                             (e["clips"][0], run["cw"], run["cr"], CLIP_OFFSET, run["clip"]),
                                             (e["clips"][1], run["c2w"], run["c2r"], CLIP2_OFFSET, run["clip2"])):
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
        for label, seg in (("hook", e["hook"]), ("clip_01", e["clips"][0]), ("clip_02", e["clips"][1])):
            c = cuts[label]
            assert c["verified"] is True, c
            assert seg["word_start"] - 0.6 < c["cut_in"] < seg["word_start"]       # inside the 0.5 s pause
            assert seg["word_end"] < c["cut_out"] < seg["word_end"] + 0.6
        ok, table = L.gate_g16(run["dir"])
        assert ok, table


class TestDirtyCache:
    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F09 (OPEN): a cached download is relabelled with the newly "
                                           "requested offset; REQUESTS.md R-09 (this pin flips only when R-09 AND "
                                           "R-22 hold: a refused cache hit must not fall back to the file under "
                                           "the name)")
    def test_a_cached_window_of_another_request_is_never_relabelled(self, run):
        """sources/<hook>.mp4 is an OLD download of the window at 285 s (its own download record says so; the host
        repeats the hook sentences at 300 s); the editor's verified passage is at 60 s, so the new request starts at
        45 s. The window holding the verified passage cannot be downloaded here (no network) and the shortlist has
        no other hook, so the only correct outcome is no EDL. Recording 45 s for a file that starts at 285 s is the
        defect; recording 285 s would put the 300 s repeat in place of the verified 60 s passage, which is not the
        editor's moment either (integrator, R-09 pin: `ok is False` only)."""
        import select_passages as SP
        rd = run["dir"]
        old, ow, (oi0, _) = H.write_source(rd, HOOK_VID, H.HOOK_TEXT, offset=285, seed=7)   # the stale cache
        first = ow[oi0]["start"]                           # the passage's place in a window (same layout)
        hook = {**run["hook"], "start": HOOK_OFFSET + first, "end": HOOK_OFFSET + first + old["duration"]}
        H.passages_json(rd, hook, [run["clip"], run["clip2"]])
        ok = SP.select_and_build_edl("bitcoin", "bitcoin", rd)
        assert ok is False, _edl(run)["hook"]

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F10 (OPEN): the transcript cache is keyed by video id, not "
                                           "by the bytes it transcribed; REQUESTS.md R-10")
    def test_a_transcript_of_other_bytes_is_never_used(self, cut_run, monkeypatch):
        """The source's bytes changed under the same name (same timing, other content); its cached transcript
        describes the old bytes. select must transcribe the new bytes or stop; it must never use the old
        transcript. Here a transcription is refused at law L-r's GPU0 lease (this CPU suite holds none): the
        refusal is a Gpu0Stop that leaves select at once, so it is this pin's proof that the new bytes were sent to
        Whisper (integrator cycle 2: the fixed code then flips this pin to XPASS instead of erroring). The stop must
        come from the HOOK's transcription: select's seam is wrapped (the real function runs, its cache check is
        this pin's subject) to record which source it was transcribing; a stop on another source is a control
        failure."""
        import gpu0
        import select_passages as SP
        run = cut_run
        os.remove(os.path.join(run["dir"], "edl.json"))
        _replace_source(run, HOOK_VID, H.HOOK_TEXT, seed=99, voice=3.0, offset=HOOK_OFFSET)
        real, asked = SP._whisper_transcribe, []

        def recording(path, vid, run_dir):
            asked.append(vid)
            return real(path, vid, run_dir)
        monkeypatch.setattr(SP, "_whisper_transcribe", recording)
        try:
            ok = _select(run)
        except gpu0.LeaseMissing as e:                     # the new bytes went to Whisper (refused at the lease)
            H.control(str(e).startswith("whisper:") and asked[-1:] == [HOOK_VID],
                      f"a lease refusal that is not the hook's transcription: {asked} {e}")
            ok = "transcribed"
        assert ok in (False, "transcribed"), "the old transcript was used for new bytes"

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F23 (OPEN): yt-dlp's exit status is ignored and a partial "
                                           "file already under the name is taken as the download; REQUESTS.md R-22")
    def test_a_failed_download_never_supplies_a_source(self, run):
        """sources/<hook>.mp4 is a 10-100 KB leftover of an interrupted download (too small for a cache hit, so
        yt-dlp runs); yt-dlp exits 1 and writes nothing. Nothing from that video may be selected.
        Every OTHER record is consistent with the leftover, so only R-22 can flip this probe (integrator, R-22 pin;
        PP-E11): its transcript is what a transcription of THOSE bytes yields (the words up to the cut, duration and
        media_sha256 of the leftover: R-10's binding holds), and it has no download record (a partial download writes
        none: R-09's record check makes it a cache miss either way, which is where R-22 decides)."""
        x, words, _, (_, i1) = H.source_audio(H.HOOK_TEXT, seed=1)
        cut_s = words[i1]["end"] + 2.0                                 # a truncated download: the hook, then 2 s
        part = x[:int(cut_s * 48000):3]
        p = os.path.join(run["dir"], "sources", f"{HOOK_VID}.mp4")
        H.make_media(p, part, sr=16000, audio_kbps=12, size=(16, 16))
        os.remove(os.path.join(run["dir"], "sources", f"{HOOK_VID}.section.json"))   # a partial download has none
        H.control(10_000 < os.path.getsize(p) <= 100_000, f"leftover size {os.path.getsize(p)}")
        with open(os.path.join(run["dir"], "transcripts", f"{HOOK_VID}.json"), "w") as f:
            json.dump({"words": [w for w in words if w["end"] <= cut_s], "language": "en",
                       "duration": round(len(part) / 16000, 3), "media_sha256": H.sha256(p)}, f)
        ok = _select(run)
        H.control(any(f"watch?v={HOOK_VID}" in " ".join(c) for c in run["ytdlp"].calls), "yt-dlp was asked (and failed)")
        assert ok is False, "a failed download supplied the hook"

    def test_yt_dlp_failure_on_a_cache_miss_selects_nothing(self, run):
        """Control: no cached file and a failing yt-dlp = no source = no EDL (and yt-dlp WAS asked)."""
        os.remove(os.path.join(run["dir"], "sources", f"{HOOK_VID}.mp4"))
        os.remove(os.path.join(run["dir"], "sources", f"{HOOK_VID}.section.json"))
        assert _select(run) is False
        assert any(f"watch?v={HOOK_VID}" in " ".join(c) for c in run["ytdlp"].calls)

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="PP-05 (new): a source whose transcription failed crashes select's slot "
                                           "fallback (KeyError) instead of a STOP; REQUESTS.md R-27")
    def test_a_failed_transcription_stops_select_cleanly(self, run, monkeypatch):
        """The hook's source is cached (valid download record) but has no transcript, and transcribing it fails:
        select_passages._whisper_transcribe returns None, its documented failure (Whisper raised an ordinary error on
        a run: an unreadable file, a decode error). select must refill the hook slot from the shortlist or STOP
        (return False, its documented failure); a KeyError out of it is neither. The failure is injected at that seam
        (integrator cycle 2): under law L-r this CPU suite's Whisper use stops at the GPU0 lease before any decode,
        and that stop is a different path, pinned PASSING by the next test."""
        import select_passages as SP
        os.remove(os.path.join(run["dir"], "transcripts", f"{HOOK_VID}.json"))
        real, asked = SP._whisper_transcribe, []

        def failing(path, vid, run_dir):
            asked.append(vid)
            return None if vid == HOOK_VID else real(path, vid, run_dir)
        monkeypatch.setattr(SP, "_whisper_transcribe", failing)
        try:
            ok = _select(run)
        except KeyError as e:                              # the measured crash (a different exception is FAILED)
            H.control(HOOK_VID in asked, f"select raised before the hook's transcription was attempted: {e!r}")
            raise AssertionError(f"select crashed after a failed transcription: KeyError {e}") from e
        H.control(HOOK_VID in asked, "the hook's transcription was attempted (and failed)")
        assert ok is False

    def test_a_gpu_stop_during_transcription_leaves_select_and_writes_nothing(self, run, whisper_attempts):
        """Law L-r (integrator cycle 2's question: does select stop cleanly on a lease refusal? It does): the hook has
        no transcript, so select loads Whisper; the load meets the GPU0 lease first (this CPU suite holds none and
        hides every GPU). The refusal is a Gpu0Stop, a BaseException: it passes select's `except Exception` (never
        'transcription failed', E-FAIL-052) and leaves select at once, for run_fresh's stage runner to HOLD on. select
        leaves the run directory exactly as it found it (every file's size and mtime, every directory: no EDL, no
        transcript, no record), and nothing reaches faster_whisper."""
        import gpu0
        os.remove(os.path.join(run["dir"], "transcripts", f"{HOOK_VID}.json"))
        before = _tree(run["dir"])
        with pytest.raises(gpu0.LeaseMissing, match=r"^whisper:large-v3: GPU0 loads need CUDA_VISIBLE_DEVICES=0"):
            _select(run)
        assert _tree(run["dir"]) == before, "select changed the run directory before its GPU stop"
        assert whisper_attempts() == []


class TestSelectContract:
    """R-23 (the D contract: hook + >= 2 clips + >= 2 distinct channels), each half pinned ALONE (integrator B2):
    each probe breaks one half and keeps the other, so it flips only with that half's fix."""

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F08 (OPEN, D: SELECT = hook + >= 2 clips + the required "
                                           "channels): success with one clip; REQUESTS.md R-23 (clip half)")
    def test_select_with_fewer_than_two_clips_is_not_a_success(self, run):
        """The editor's slots: a hook and ONE clip, two channels (DataDash, Natalie Brunell): the channel half
        holds, only the clip count is short. The shortlist has no other clip, so the only correct outcome is no
        EDL."""
        H.passages_json(run["dir"], run["hook"], [run["clip"]])
        ok = _select(run)
        if ok:
            e = _edl(run)
            H.control(len({e["hook"]["channel"]} | {c["channel"] for c in e["clips"]}) >= 2,
                      f"the channel half holds: {e['hook']['channel']}, {[c['channel'] for c in e['clips']]}")
        assert ok is False, f"SELECT reported success with {len(_edl(run)['clips'])} clip"

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="GPT-select F08 (OPEN; R5: >= 2 distinct channels): success with one "
                                           "channel; REQUESTS.md R-23 (channel half)")
    def test_select_with_one_channel_is_not_a_success(self, run):
        """Hook and BOTH clips credited to one channel: the clip half holds (two clips), only the channel count is
        short, under either reading of R5 (the hook's channel counted or not)."""
        H.passages_json(run["dir"], run["hook"], [run["clip"], run["clip2"]], hook_channel="DataDash",
                        clip_channels=("DataDash", "DataDash"))
        ok = _select(run)
        if ok:
            H.control(len(_edl(run)["clips"]) == 2, f"the clip half holds: {len(_edl(run)['clips'])} clips")
        assert ok is False, "SELECT reported success with one channel"

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
        its first / last word and text are not that transcript's words at its indices. The error R-11 names ('not
        the transcript's words') is matched, so an unrelated verify_lock error can never flip this pin (integrator,
        R-11 pin); the control proves this lock is otherwise valid (digest and lock seal)."""
        import sentence_law as L
        run = cut_run
        tp = os.path.join(run["dir"], "transcripts", f"{HOOK_VID}.json")
        i0, i1 = run["hr"]
        other = [dict(w) for w in run["hw"]]
        other[i0]["word"], other[i1]["word"] = "Ether", "carefully."
        lock = L.make_lock(HOOK_VID, other, i0, i1, L.sha256_file(tp), run["hook"]["text"], None, 1.0, "test")
        errs = L.verify_lock(lock, tp)
        H.control(not any("transcript changed" in e or "modified after selection" in e for e in errs),
                  f"the lock's digest and seal are valid: {errs}")
        assert any("not the transcript's words" in e for e in errs), errs

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
