"""Shared helpers for tests/adversarial (CPU only; see conftest.py).

  sentence generator   seeded (hypothesis is not installed): a finance sentence built from slots, its SURFACE
                       variants (the same spoken words written differently: entities, unicode, split tokens,
                       currency / percent order, number words, case, punctuation) and its MEANING mutants (one
                       slot's value changed: digits swapped, teen / ty, scale, negation, actor, sign, unit)
  synthetic media      ffmpeg on CPU, libx264 ultrafast, tiny frames: speech-like audio (noise bursts per word,
                       room tone between words, pauses between sentences) with its exact word transcript
  run directories      a complete release run that release_auth authorises (family 3 mutates it)
  fake model           the real story_semantics.LocalLLM.chat_json loop with only its HTTP call replaced
"""
import json
import math
import os
import random
import shutil
import subprocess
import tempfile
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
FIXTURES = os.path.join(REPO, "tests", "fixtures", "adversarial")
MAIN_TREE_REFS = os.environ.get("PP_REFS_DIR", "/home/ultron/protocol_pulse/references")   # read-only (order:
#   allowed data); PP_REFS_DIR overrides it on another machine. A missing reference FAILS (law L-m), never skips.


class NetworkBlocked(BaseException):
    """Raised by conftest's socket guard for any AF_INET / AF_INET6 connect. A BaseException on purpose: a production
    `except Exception` cannot swallow it and a test's pytest.raises(RuntimeError) cannot take it for the refusal it
    expects (a regressed send path FAILS its test instead of satisfying it)."""


def control(ok, msg):
    """A precondition of a test (its setup or a control inside it) that must hold for the test to mean anything.
    pytest.fail, not assert: every strict xfail is raises=AssertionError, so a broken control or fixture shows as
    FAILED / ERROR instead of being counted as the pinned defect (frontier review, audit A #2)."""
    if not ok:
        import pytest
        pytest.fail(f"CONTROL (test setup, not the pinned defect): {msg}", pytrace=True)


def load_fixture(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)


# ── sentence generator ──

ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen").split()
TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()


def words_int(n, hyphen=False):
    """An integer as a speaker says it ('eighty one thousand', 'eighty-one thousand')."""
    if n < 20:
        return ONES[n]
    if n < 100:
        t, u = divmod(n, 10)
        return TENS[t - 2] + (("-" if hyphen else " ") + ONES[u] if u else "")
    if n < 1000:
        h, r = divmod(n, 100)
        return ONES[h] + " hundred" + (" " + words_int(r, hyphen) if r else "")
    for v, name in ((10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (10 ** 3, "thousand")):
        if n >= v:
            q, r = divmod(n, v)
            return words_int(q, hyphen) + " " + name + (" " + words_int(r, hyphen) if r else "")


SUBJECTS = ["Bitcoin", "Ether", "MicroStrategy", "BlackRock's fund", "the S&P 500", "Coinbase"]
ACTOR_SWAPS = [("the Fed", "the Treasury"), ("the SEC", "the CFTC"), ("BlackRock", "Fidelity"),
               ("the ECB", "the Fed"), ("Michael Saylor", "Jack Mallers")]
NEGATIONS = [("has", "hasn't"), ("has", "has not"), ("is", "isn't"), ("did", "didn't"), ("will", "won't"),
             ("can", "can't"), ("was", "wasn't")]
TEEN_TY = [(13, 30), (14, 40), (15, 50), (16, 60), (17, 70), (18, 80), (19, 90)]
SCALES = ["million", "billion", "trillion"]
SCALE_SUFFIX = {"million": "M", "billion": "B", "trillion": "T"}
VERB_AFTER = {"has": "broken out", "hasn't": "broken out", "has not": "broken out", "is": "holding",
              "isn't": "holding", "did": "break out", "didn't": "break out", "will": "break out",
              "won't": "break out", "can": "hold", "can't": "hold", "was": "holding", "wasn't": "holding"}


def _dollars(n, style):
    """A whole-dollar amount (n in thousands range) written in one surface style."""
    if style == "symbol":
        return f"${n:,}"
    if style == "split":                                   # a Whisper word split into tokens ('$81 ,000')
        s = f"${n:,}"
        return s.replace(",", " ,", 1)
    if style == "words":
        return words_int(n) + " dollars"
    if style == "words_hyphen":
        return words_int(n, hyphen=True) + " dollars"
    if style == "suffix" and n % 1000 == 0:
        return f"${n // 1000}k"
    if style == "thousand" and n % 1000 == 0:
        return f"{n // 1000} thousand dollars"
    if style == "narrow_nbsp" and n >= 1000:
        return f"${n // 1000}\u202f{n % 1000:03d}"
    if style == "digits_dollars":
        return f"{n:,} dollars"
    return f"${n:,}"


DOLLAR_STYLES = ["symbol", "split", "words", "words_hyphen", "suffix", "thousand", "narrow_nbsp", "digits_dollars"]


def _percent(p, style):
    if style == "symbol":
        return f"{p}%"
    if style == "word":
        return f"{p} percent"
    if style == "spoken":
        return words_int(p) + " percent"
    if style == "per_cent":
        return f"{p} per cent"
    if style == "spaced":
        return f"{p} %"
    return f"{p}%"


PERCENT_STYLES = ["symbol", "word", "spoken", "per_cent", "spaced"]


def _scaled(x, scale, style):
    """'$1.66 billion' in one surface style (x a short decimal string)."""
    if style == "symbol":
        return f"${x} {scale}"
    if style == "spoken_order":
        return f"{x} {scale} dollars"
    if style == "suffix":
        return f"${x}{SCALE_SUFFIX[scale]}"
    if style == "split" and "." in x:
        a, b = x.split(".")
        return f"${a} .{b} {scale}"
    if style == "words" and "." not in x:
        return words_int(int(x)) + f" {scale} dollars"
    return f"${x} {scale}"


SCALED_STYLES = ["symbol", "spoken_order", "suffix", "split", "words"]


def _surface(text, rng):
    """Whole-sentence surface changes a listener cannot hear: entities, unicode quotes / dashes, case,
    trailing punctuation, no-break spaces."""
    t = text
    k = rng.randrange(6)
    if k == 0:
        t = t.replace("&", "&amp;").replace("'", "&#39;").replace('"', "&quot;")
    elif k == 1:
        t = t.replace("'", "\u2019").replace(" - ", " \u2014 ")
    elif k == 2:
        t = t.upper()
    elif k == 3:
        t = t.rstrip(".") + "..."
    elif k == 4:
        t = t.replace(" ", "\u00a0", 2)
    else:
        t = "\u201c" + t + "\u201d"
    return t


class Case:
    """One generated sentence: base text, surface variants (equal), meaning mutants (unequal, labelled)."""

    def __init__(self, base, variants, mutants, kind, numbers=None):
        self.base, self.variants, self.mutants, self.kind = base, variants, mutants, kind
        self.numbers = numbers or {}

    def __repr__(self):
        return f"Case({self.kind}: {self.base!r})"


def gen_cases(seed, n):
    """n seeded cases; every case has >= 6 canonical tokens, its mutation strictly INSIDE the sentence (the
    first and last words are never mutated, so anchoring sites that pin the edges are tested on the middle)."""
    rng = random.Random(seed)
    out = []
    makers = [_case_dollars, _case_percent, _case_scale, _case_negation, _case_actor, _case_sign]
    for i in range(n):
        out.append(makers[i % len(makers)](rng))
    return out


def _case_dollars(rng):
    a, b = rng.sample(range(1, 10), 2)                     # two different digits: 81,000 vs 18,000
    n, m = (10 * a + b) * 1000, (10 * b + a) * 1000
    subj = rng.choice(SUBJECTS)
    fmt = "Yesterday {subj} closed above {amt} after a quiet weekend in Asia."
    base = fmt.format(subj=subj, amt=_dollars(n, "symbol"))
    variants = [_surface(fmt.format(subj=subj, amt=_dollars(n, st)), rng) for st in DOLLAR_STYLES]
    mutants = [("digits swapped", fmt.format(subj=subj, amt=_dollars(m, rng.choice(DOLLAR_STYLES)))),
               ("off by one thousand", fmt.format(subj=subj, amt=_dollars(n + 1000, "symbol"))),
               ("ten times", fmt.format(subj=subj, amt=_dollars(n * 10, "symbol")))]
    return Case(base, variants, mutants, "dollars", {"value": n, "mutant": m})


def _case_percent(rng):
    p, q = rng.choice(TEEN_TY)
    if rng.random() < 0.5:
        p, q = q, p
    subj = rng.choice(SUBJECTS)
    fmt = "Over the month {subj} fell {pct} while gold barely moved at all."
    base = fmt.format(subj=subj, pct=_percent(p, "symbol"))
    variants = [_surface(fmt.format(subj=subj, pct=_percent(p, st)), rng) for st in PERCENT_STYLES]
    mutants = [("teen / ty", fmt.format(subj=subj, pct=_percent(q, rng.choice(PERCENT_STYLES)))),
               ("percent read as dollars", fmt.format(subj=subj, pct=f"${p}")),
               ("percentage points", fmt.format(subj=subj, pct=f"{p} percentage points"))]
    return Case(base, variants, mutants, "percent", {"value": p, "mutant": q})


def _case_scale(rng):
    x = rng.choice(["1.66", "40", "2.5", "12", "7.25"])
    scale = rng.choice(SCALES)
    other = rng.choice([s for s in SCALES if s != scale])
    fmt = "Last week spot ETFs saw {amt} of net outflows according to the filings."
    base = fmt.format(amt=_scaled(x, scale, "symbol"))
    variants = [_surface(fmt.format(amt=_scaled(x, scale, st)), rng) for st in SCALED_STYLES]
    mutants = [("scale", fmt.format(amt=_scaled(x, other, rng.choice(SCALED_STYLES))))]
    if "." in x:
        mutants.append(("decimal dropped", fmt.format(amt=_scaled(x.split(".")[0], scale, "symbol"))))
    return Case(base, variants, mutants, "scale", {"value": x, "scale": scale, "mutant": other})


def _case_negation(rng):
    pos, neg = rng.choice(NEGATIONS)
    subj = rng.choice(SUBJECTS)
    fmt = "Analysts say {subj} {aux} {verb} of its range this week despite the noise."
    v = VERB_AFTER[pos]
    base = fmt.format(subj=subj, aux=pos, verb=v)
    variants = [_surface(base, rng) for _ in range(3)]
    mutants = [("negation", fmt.format(subj=subj, aux=neg, verb=VERB_AFTER[neg]))]
    return Case(base, variants, mutants, "negation")


def _case_actor(rng):
    a, b = rng.choice(ACTOR_SWAPS)
    if rng.random() < 0.5:
        a, b = b, a
    fmt = "On Monday {actor} said it would review its policy on digital assets next quarter."
    base = fmt.format(actor=a)
    variants = [_surface(base, rng) for _ in range(3)]
    mutants = [("actor swapped", fmt.format(actor=b))]
    return Case(base, variants, mutants, "actor")


def _case_sign(rng):
    p = rng.choice([3, 5, 7, 12])
    fmt = "In the session the dollar index moved {chg} against the euro before the close."
    base = fmt.format(chg=f"-{p}%")
    variants = [_surface(fmt.format(chg=c), rng) for c in (f"-{p}%", f"- {p}%", f"minus {p} percent",
                                                             f"−{p}%", f"minus {words_int(p)} percent")]
    mutants = [("sign flipped", fmt.format(chg=f"+{p}%")), ("sign dropped", fmt.format(chg=f"{p}%"))]
    return Case(base, variants, mutants, "sign")


def words_of(text, t0=0.0, step=0.30, dur=0.25):
    """A word-timestamp transcript of `text` (whitespace words), one word every `step` s."""
    return [{"word": w, "start": round(t0 + k * step, 3), "end": round(t0 + k * step + dur, 3)}
            for k, w in enumerate(text.split())]


CONTEXT_BEFORE = "Good morning and welcome back to the channel. Here is what moved overnight."
CONTEXT_AFTER = "That is the story for today. Thanks for watching and see you tomorrow."


def in_context(text):
    return f"{CONTEXT_BEFORE} {text} {CONTEXT_AFTER}"


# ── synthetic media (CPU: ffmpeg, libx264 ultrafast, tiny frames) ──

def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True, timeout=120)


# PERF: synthetic media (speech_like + make_media) and the G8 frame grabs on the frozen 9:16 final are the suite's
# dominant CPU cost (2:00 at low load, up to ~4:00 on the shared box; budget 5:00). Build media once per module and
# copy it (test_f2 template / cut_template) rather than per test.
def speech_like(sentences, word_s=0.30, gap_s=0.08, pause_s=0.50, lead_s=0.60, tail_s=1.20, sr=48000,
                seed=0, level_db=-20.0, room_db=-62.0, shift_s=0.0, voice=1.0):
    """(samples float32, words, duration): speech-like audio with its exact transcript. Each word is a noise
    burst with 8 ms raised-cosine ramps at level_db (RMS), room tone at room_db everywhere else; gap_s between
    words of a sentence, pause_s between sentences. shift_s prepends that much room tone (the same speech later
    in the file: a different window start). voice changes the burst's spectral colour (different content,
    same timing)."""
    rng = np.random.default_rng(seed)
    t, words = lead_s + shift_s, []
    for si, sent in enumerate(sentences):
        toks = sent.split()
        for wi, w in enumerate(toks):
            words.append({"word": w, "start": round(t, 3), "end": round(t + word_s, 3), "probability": 0.99})
            t += word_s + (gap_s if wi < len(toks) - 1 else 0.0)
        t += pause_s if si < len(sentences) - 1 else 0.0
    dur = t + tail_s
    n = int(round(dur * sr))
    x = rng.standard_normal(n).astype(np.float64) * (10 ** (room_db / 20))
    ramp = int(0.008 * sr)
    win = np.ones(int(round(word_s * sr)))
    win[:ramp] = 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, ramp))
    win[-ramp:] = win[:ramp][::-1]
    for w in words:
        a = int(round(w["start"] * sr))
        burst = rng.standard_normal(len(win))
        if voice != 1.0:                                   # a different colour: same envelope, other content
            burst = np.convolve(burst, np.ones(int(3 * voice)) / int(3 * voice), mode="same")
        burst *= (10 ** (level_db / 20)) / (np.sqrt(np.mean(burst ** 2)) + 1e-12)
        x[a:a + len(win)] += burst[:len(x) - a] * win[:len(x) - a]
    return x.astype(np.float32), words, round(dur, 3)


def write_wav(path, x, sr=48000):
    y = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((y * 32767).astype("<i2").tobytes())


def make_media(path, x=None, sr=48000, size=(64, 36), dur=None, pattern="testsrc2", fps=24, audio_kbps=192):
    """An mp4 (libx264 ultrafast, tiny frames) with the given mono samples as AAC audio (or silence)."""
    tmpd = tempfile.mkdtemp(prefix="adv_media_")
    try:
        if x is None:
            x = np.zeros(int(round((dur or 1.0) * sr)), np.float32)
        wav = os.path.join(tmpd, "a.wav")
        write_wav(wav, x, sr)
        d = len(x) / sr
        src = (f"{pattern}=s={size[0]}x{size[1]}:r={fps}:d={d:.3f}" if pattern in ("testsrc2", "testsrc")
               else f"color=c={pattern}:s={size[0]}x{size[1]}:r={fps}:d={d:.3f}")
        _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src, "-i", wav, "-map", "0:v", "-map", "1:a",
              "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a",
              f"{audio_kbps}k", "-ar", str(sr), "-ac", "1", "-shortest", path])
    finally:
        shutil.rmtree(tmpd, True)
    return path


def make_video(path, w, h, dur=1.0, color="black", fps=24):
    """A silent-picture final at the given dimensions (no audio)."""
    _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:r={fps}:d={dur}",
          "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", path])
    return path


# ── a synthetic selection run (select_passages.select_and_build_edl on CPU, no network, no Whisper) ──

FILLER = ["Good morning everyone and welcome back to the show.", "Here is what moved in the market overnight.",
          "Grab a coffee because there is a lot to cover today.", "Let us start with the biggest story."]
AFTER = ["We will come back to that later in the show.", "Now let us look at the other headlines.",
         "Stay with us for the rest of the hour.", "That is all for this part of the program."]
HOOK_TEXT = ["Bitcoin closed the week below its fifty week moving average for the first time since September.",
             "That is a level many traders watch very closely."]
CLIP_TEXT = ["Spot Bitcoin funds saw heavy outflows for the third week in a row as investors pulled money.",
             "The selling was concentrated in the largest funds while smaller ones barely moved.",
             "Analysts say the flows usually turn when the price stabilises."]
PAD_S = 15.0                                                    # select_passages._download_window's pad


def source_audio(passage, first_word_at=PAD_S + 0.25, seed=0, voice=1.0, filler=FILLER, after=AFTER):
    """(samples, words, duration, passage_word_range): filler sentences, the passage sentences (first word at
    `first_word_at` s into the file), then more sentences, as select_passages expects a downloaded window."""
    sents = list(filler) + list(passage) + list(after)
    _, w0, _ = speech_like(sents, lead_s=0.6, seed=seed)
    k = sum(len(s.split()) for s in filler)
    lead = 0.6 + (first_word_at - w0[k]["start"])
    x, words, dur = speech_like(sents, lead_s=lead, seed=seed, voice=voice)
    n = sum(len(s.split()) for s in passage)
    return x, words, dur, (k, k + n - 1)


def write_section(run_dir, vid, dl_start, dl_end):
    """sources/<vid>.section.json, the download record pp-tests_REQUESTS.md R-09 proposes (dl_start, dl_end, the
    sha256 of the file): written by every fixture so the wall stays valid when that fix lands (frontier review,
    audit A #1). Today's code ignores it."""
    path = os.path.join(run_dir, "sources", f"{vid}.mp4")
    with open(os.path.join(run_dir, "sources", f"{vid}.section.json"), "w") as f:
        json.dump({"dl_start": dl_start, "dl_end": round(dl_end, 3), "sha256": sha256(path)}, f)


def write_source(run_dir, vid, passage, offset, seed=0, voice=1.0, filler=FILLER, after=AFTER, transcript=True):
    """sources/<vid>.mp4 (+ transcripts/<vid>.json) for a window downloaded at `offset` (full-video seconds).
    Returns the passage record select_passages reads (full-video times) and the file's words."""
    os.makedirs(os.path.join(run_dir, "sources"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "transcripts"), exist_ok=True)
    x, words, dur, (i0, i1) = source_audio(passage, seed=seed, voice=voice, filler=filler, after=after)
    media = make_media(os.path.join(run_dir, "sources", f"{vid}.mp4"), x)
    write_section(run_dir, vid, offset, offset + dur)
    if transcript:
        with open(os.path.join(run_dir, "transcripts", f"{vid}.json"), "w") as f:
            json.dump({"words": words, "language": "en", "duration": dur, "media_sha256": sha256(media)}, f)
    start, end = offset + words[i0]["start"], offset + words[i1]["end"]
    return {"video_id": vid, "start": round(start, 3), "end": round(end, 3), "text": " ".join(passage),
            "duration": round(end - start, 3)}, words, (i0, i1)


def passages_json(run_dir, hook, clip, hook_channel="DataDash", clip_channel="Natalie Brunell"):
    h = {**hook, "kind": "hook", "channel": hook_channel, "clip_score": 5.0, "relevance": 1.0, "score": 5.0,
         "handle": "@x", "title": "t"}
    c = {**clip, "kind": "clip", "channel": clip_channel, "clip_score": 5.0, "relevance": 1.0, "score": 5.0,
         "handle": "@y", "title": "t"}
    with open(os.path.join(run_dir, "passages.json"), "w") as f:
        json.dump({"chosen": [h, c], "passages": [h, c]}, f)
    return h, c


class FakeYtDlp:
    """A stand-in for select_passages' `subprocess` module (monkeypatch.setattr(select_passages, "subprocess",
    FakeYtDlp())): run() 'fails' like yt-dlp without network (exit 1, nothing written) and is recorded; every
    other attribute is the real module's. A test that expects no download asserts calls == []."""

    def __init__(self):
        self.calls = []

    def run(self, cmd, *a, **k):
        self.calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 1, "", "ERROR: network disabled in tests/adversarial")

    def __getattr__(self, name):
        return getattr(subprocess, name)


# ── a complete release run (release_auth authorises it; family 3 mutates it) ──

_FINALS = {}


def _finals():
    """Two one-second finals at the release dimensions, made once per process (black, libx264 ultrafast)."""
    if not _FINALS:
        d = tempfile.mkdtemp(prefix="adv_finals_")
        for name, (w, h), color in (("segment.mp4", (1920, 1080), "black"),
                                    ("segment_vertical.mp4", (1080, 1920), "black"),
                                    ("other_vertical.mp4", (1080, 1920), "gray")):
            make_video(os.path.join(d, name), w, h, 1.0, color)
        _FINALS["dir"] = d
    return _FINALS["dir"]


def passing_rows(ra):
    rows = {fmt: {k: "PASS" for k in ra.INVENTORY[fmt] | ra.MONITORING[fmt]} for fmt in ra.FORMATS}
    for fmt in ra.FORMATS:
        for k, allowed in ra.NONBLOCKING[fmt].items():
            rows[fmt][k] = sorted(allowed)[0]
    return rows


def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


MEASURED = ("edl.json", "out/segment.mp4", "out/segment_vertical.mp4", "qa/concat_manifest_16x9.json",
            "qa/concat_manifest_9x16.json")


def release_run(parent, rows=None, attest=True, run_state=None):
    """A run directory exactly as run_fresh leaves a clean candidate: both finals, EDL, both manifests, contact
    sheets, GATE_REPORT.json (rows, execution evidence, the digests the gates measured, G18 readings) and the
    verification pack; attested ALL_PASS unless attest=False."""
    import release_auth as RA
    from PIL import Image
    rd = tempfile.mkdtemp(prefix="fresh_adv_", dir=parent)
    for sub in ("out", "qa", "VERIFY"):
        os.makedirs(os.path.join(rd, sub))
    for name in ("segment.mp4", "segment_vertical.mp4"):
        shutil.copy(os.path.join(_finals(), name), os.path.join(rd, "out", name))
    shot = {"start": 0.0, "end": 0.5, "class": "single", "flagged": False}
    edl = {"topic": "Bitcoin price dip", "headline": "Bitcoin price dip",
           "hook": {"channel": "Yahoo Finance", "video_id": "YAH0000000a",
                    "selection_lock": {"text": "Bitcoin fell to 74,000 dollars today."},
                    "vertical_layout": {"shots": [shot], "flagged": False}},
           "clips": [{"index": 1, "channel": "Natalie Brunell", "video_id": "NAT0000000b",
                      "selection_lock": {"text": "It is a bear market rally."},
                      "vertical_layout": {"shots": [shot], "flagged": False}}]}
    with open(os.path.join(rd, "edl.json"), "w") as f:
        json.dump(edl, f)
    for fmt in RA.FORMATS:
        with open(os.path.join(rd, "qa", f"concat_manifest_{fmt}.json"), "w") as f:
            json.dump({"format": fmt, "segments": [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 0.5},
                                                   {"label": "outro", "type": "outro", "start": 0.5, "end": 1.0}]}, f)
        Image.new("RGB", (120, 80), (10, 10, 15)).save(os.path.join(rd, "qa", f"contact_sheet_{fmt}.jpg"))
    rows = rows or passing_rows(RA)
    heard = [{"segment": "hook", "heard": edl["hook"]["selection_lock"]["text"]},
             {"segment": "clip_01", "heard": edl["clips"][0]["selection_lock"]["text"]}]
    report = {"inventory_version": RA.INVENTORY_VERSION, "rows": rows,
              "evidence": {fmt: {k: {"executed": True, "samples": 3} for k in r} for fmt, r in rows.items()},
              "notes": {}, "measured_files": {rel: sha256(os.path.join(rd, rel)) for rel in MEASURED},
              "G18": {"16x9": heard, "9x16": heard}}
    with open(os.path.join(rd, "GATE_REPORT.json"), "w") as f:
        json.dump(report, f)
    with open(os.path.join(rd, "VERIFY", "VERIFICATION.json"), "w") as f:
        json.dump({"complete": True, "vision": True, "passed": True, "visual": {x: {"ok": True} for x in RA.FORMATS}}, f)
    if attest:
        RA.attest(rd, run_state or {"ok": True, "why": []})
    return rd


def edit_json(path, fn):
    with open(path) as f:
        d = json.load(f)
    fn(d)
    with open(path, "w") as f:
        json.dump(d, f)


def other_vertical():
    return os.path.join(_finals(), "other_vertical.mp4")


# ── windowed source envelope (sentence_law.SourceAudio's 10 ms grid, decoded only around a cut) ──

class WindowAudio:
    """sentence_law.SourceAudio's envelope (mono 16 kHz, 10 ms RMS, dBFS) of [t0, t1] only, on the same absolute
    10 ms grid (t0 is floored to a multiple of 10 ms): what edge_word_bounds reads (sl) without decoding a
    multi-hour source. Equal to the whole-file decode on every reference edge (checked 2026-11-12)."""

    def __init__(self, path, t0, t1):
        t0 = math.floor(max(0.0, t0) * 100) / 100
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", path, "-t", f"{t1 - t0:.3f}", "-vn",
                            "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True, timeout=120)
        x = np.frombuffer(r.stdout, np.float32)
        n = len(x) // 160
        self.path, self.dur = path, t0 + len(x) / 16000
        self.t = t0 + np.arange(n) * 0.010
        self.db = 20 * np.log10(np.sqrt(np.mean(x[:n * 160].reshape(n, 160).astype(np.float64) ** 2, axis=1)) + 1e-9)

    def sl(self, a, b):
        m = (self.t >= a - 1e-9) & (self.t < b - 1e-9)
        return self.t[m], self.db[m]


# ── fake model: the real chat_json loop, only the HTTP call replaced ──

def fake_llm(replies):
    """A story_semantics.LocalLLM whose _post returns the given raw replies in order (then repeats the last).
    No digest = no reply cache (nothing written); no GPU guard, no network."""
    import story_semantics as sm
    llm = object.__new__(sm.LocalLLM)
    llm.model, llm.host, llm.calls, llm.cache_hits = "fake-model", "127.0.0.1:9", 0, 0
    llm.serve_pid, llm.placement_checked, llm.digest = None, True, None
    seq = list(replies)

    def _post(prompt, max_tokens, seed):
        llm.calls += 1
        return seq.pop(0) if len(seq) > 1 else seq[0]
    llm._post = _post
    return llm


# garbage a model can return: empty, prose, truncated JSON, JSON of the wrong shape, null, a number
GARBAGE_REPLIES = ["", "   ", "I think the answer is yes.", "{", '{"verdict": ', "null", "[]", "[1, 2, 3]",
                   "42", '"yes"', "true", '{"answer": "yes"}', '{"result": {}}', "```json\n{}\n```",
                   '{"verdict": null}', "NaN"]
