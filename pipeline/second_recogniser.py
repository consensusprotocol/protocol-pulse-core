#!/usr/bin/env python3
"""pipeline/second_recogniser.py — ruling 7 (orchestrator 2026-11-12 '06:45'): the INDEPENDENT second recogniser and the
review model's complete-thought verdict, run only for a locked edge the primary decode cannot prove (no terminal
punctuation). Both results are written to run_dir/second_pass/<video_id>.json, where sentence_law.ruling7_inputs reads
them for the cutter and the gates.

- second recogniser: ElevenLabs scribe_v1 on the SOURCE audio of the acquired window (sources/<id>.mp4), word
  timestamps (CPU; network; $0.012 per audio minute). The key is read by name (relay.get_key), never printed.
- complete thought (ruling 7 (4), OUT only): the review model (the local LLM) answers on the clip's locked text ALONE,
  {"complete_thought": "yes" | "no", "reason"}; anything else is no verdict (fail closed). Keyed by the lock's sha256.
"""
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
import uuid

URL = "https://api.elevenlabs.io/v1/speech-to-text"
MODEL = "scribe_v1"
COMPLETE_PROMPT = (
    "Below is the text of ONE short video clip, alone, with no context. Answer one question about its LAST clause: is "
    "it syntactically complete, a whole thought that a sentence can end on (not cut off before its object, its verb, "
    "or the rest of its clause)? Judge the grammar only, not whether you agree.\n\nCLIP TEXT:\n{text}\n\n"
    'Reply with JSON only: {{"complete_thought": "yes" or "no", "reason": "<one short sentence>"}}')


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def scribe_words(src_mp4, timeout=300):
    """(words [{"word", "start", "end"}], text, audio seconds) from scribe_v1 on the source file's audio. The source file
    IS the acquired window (select_passages._download_window downloads only the requested section), so its word times
    are the primary decode's file times."""
    from relay import get_key
    key = get_key("ELEVENLABS_API_KEY")
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "window.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src_mp4, "-vn", "-ac", "1", "-ar", "16000", wav],
                       check=True, timeout=120)
        seconds = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                        "csv=p=0", wav], capture_output=True, text=True).stdout.strip() or 0)
        boundary = uuid.uuid4().hex
        fields = {"model_id": MODEL, "timestamps_granularity": "word", "tag_audio_events": "false", "diarize": "true"}
        body = b"".join(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
                        for k, v in fields.items())
        with open(wav, "rb") as f:
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"window.wav\"\r\n"
                     f"Content-Type: audio/wav\r\n\r\n").encode() + f.read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(URL, data=body, headers={"xi-api-key": key,
                                                          "Content-Type": f"multipart/form-data; boundary={boundary}"})
    d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    words = [{"word": w.get("text"), "start": w.get("start"), "end": w.get("end")}
             for w in d.get("words") or [] if isinstance(w, dict) and w.get("type", "word") == "word"]
    return words, d.get("text") or "", seconds


def complete_thought(llm, text):
    """Ruling 7 (4): the review model on the clip text ALONE -> True only for an exact 'yes'; (verdict, reason)."""
    def validate(o):
        if not isinstance(o, dict) or o.get("complete_thought") not in ("yes", "no"):
            raise ValueError("complete_thought must be 'yes' or 'no'")
    try:
        o = llm.chat_json(COMPLETE_PROMPT.format(text=text), max_tokens=200, validate=validate)
    except Exception as e:                                # no verdict = not confirmed (fail closed)
        return None, f"{type(e).__name__}: {str(e)[:200]}"
    return o["complete_thought"] == "yes", str(o.get("reason") or "")[:300]


def ensure(run_dir, video_id, lock, need_out, llm_factory):
    """Write / extend run_dir/second_pass/<video_id>.json: the scribe words (once per acquired window, bound to the
    source file's sha256) and, when an OUT edge needs it, the complete-thought verdict on THIS lock's text."""
    d = os.path.join(run_dir, "second_pass")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{video_id}.json")
    src = os.path.join(run_dir, "sources", f"{video_id}.mp4")
    src_sha = _sha256(src)
    rec = None
    if os.path.exists(p):
        with open(p) as f:
            rec = json.load(f)
        if not (isinstance(rec, dict) and rec.get("source_sha256") == src_sha and isinstance(rec.get("words"), list)
                and isinstance(rec.get("complete_thought"), dict) and isinstance(rec.get("complete_reason"), dict)):
            rec = None                                    # another file, or a malformed record: recognise again
    if rec is None:
        words, text, secs = scribe_words(src)
        rec = {"model": f"elevenlabs:{MODEL}", "source_sha256": src_sha, "audio_s": round(secs, 2),
               "usd": round(secs / 60 * 0.012, 4), "text": text, "words": words, "complete_thought": {},
               "complete_reason": {}}
    sha, text = lock.get("sha256"), (lock.get("text") or "").strip()
    if need_out and isinstance(sha, str) and sha and text and sha not in rec["complete_thought"]:   # no digest or text: none
        llm = llm_factory()
        try:
            ok, why = complete_thought(llm, text)
        finally:
            stop = getattr(llm, "stop", None)
            if stop:
                stop()
        if ok is not None:
            rec["complete_thought"][sha] = ok
        rec["complete_reason"][sha] = why
    tmp = p + f".{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=1)
    os.replace(tmp, p)
    return rec
