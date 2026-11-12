"""pipeline/ingest/contract.py: sentence ids and the pp.moment/1 contract.

The ids are pp-selectid's (MOMENTS / PACKAGE INPUT CONTRACT v0, docs/audits/parallel/pp-selectid_STATE.md):
  tokens    = select_by_id.tokens_from_record(record)        ('word' | 'segment', tokens)
  sentences = eligibility.split_sentences(tokens)            whole sentences as token-index ranges
  text      = eligibility.spoken(tokens[w0..w1])             verbatim as spoken (law L-h)
  moment_id = sha256('video_id|transcript_sha256|w0|w1')[:20]
The defining modules are IMPORTED, never copied: from pipeline/ once merged, else read-only from the pp-selectid
worktree (PP_SELECTID_PIPELINE). fingerprint() digests their defining functions and their output on a fixed probe, so a
moment mined under another definition is detected and re-derived (verify_line), never silently re-read.
"""
import hashlib
import importlib.util
import inspect
import json
import os
import sys

from . import config  # noqa: F401  (puts pipeline/ on sys.path)

SCHEMA = "pp.moment/1"
SELECTID_DEFAULT = "/home/ultron/worktrees/pp-selectid/pipeline"
SPEAKER_MARKERS = (">>", "&gt;&gt;")


class ContractUnavailable(RuntimeError):
    pass


_MODS = None


def _load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or not os.path.exists(path):
        raise ContractUnavailable(f"{name}: {path} not found")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return mod


def modules():
    """(eligibility, select_by_id, origin). Raises ContractUnavailable: no ids without the contract's definitions."""
    global _MODS
    if _MODS is None:
        try:
            import eligibility
            import select_by_id
            origin = os.path.dirname(os.path.abspath(select_by_id.__file__))
        except ImportError:
            d = os.environ.get("PP_SELECTID_PIPELINE", SELECTID_DEFAULT)
            try:
                eligibility = _load_file("eligibility", os.path.join(d, "eligibility.py"))
                select_by_id = _load_file("select_by_id", os.path.join(d, "select_by_id.py"))
            except ContractUnavailable:
                raise
            except Exception as e:
                raise ContractUnavailable(f"contract modules in {d} failed to import: {type(e).__name__}: {e}")
            origin = d
        for fn in ("tokens_from_record",):
            if not callable(getattr(select_by_id, fn, None)):
                raise ContractUnavailable(f"select_by_id.{fn} missing")
        for fn in ("split_sentences", "spoken", "eligible", "Source", "Span", "Context"):
            if not hasattr(eligibility, fn):
                raise ContractUnavailable(f"eligibility.{fn} missing")
        _MODS = (eligibility, select_by_id, origin)
    return _MODS


PROBE_RECORD = {"segments": [
    {"start": 0.0, "end": 4.0, "text": "It went from above $81 ,000 to below $75 ,000 in the U .S. market."},
    {"start": 4.0, "end": 7.5, "text": "&gt;&gt; Dr. Smith said the S&amp;P fell 1 .3% ... then what?"},
    {"start": 7.5, "end": 9.0, "text": "Bitcoin held. And e.g. miners sold"}]}


_FP = None


def fingerprint():
    global _FP
    if _FP is None:
        E, S, origin = modules()
        import sentence_law
        ts = config.ts()
        h = hashlib.sha256()
        for f in (S.tokens_from_record, E.split_sentences, E.spoken, sentence_law.is_terminal, ts.read_text):
            h.update(inspect.getsource(f).encode())
        h.update(ts._SPLIT_TOKEN.pattern.encode())
        timing, toks = S.tokens_from_record(PROBE_RECORD)
        sents = E.split_sentences(toks)
        h.update(json.dumps([timing, [list(s) for s in sents],
                             [E.spoken(toks[a:b + 1]) for a, b in sents]]).encode())
        _FP = h.hexdigest()[:24]
    return _FP


def moment_id(video_id, transcript_sha256, w0, w1):
    return hashlib.sha256(f"{video_id}|{transcript_sha256}|{w0}|{w1}".encode()).hexdigest()[:20]


def record_tokens(rec):
    _, S, _ = modules()
    return S.tokens_from_record(rec)


def sentences(rec):
    """Every sentence of a record: {'k','w0','w1','text','start','end','complete'}. complete = it ends on a terminal
    mark (the record's last words may form an unfinished sentence: never offered as a moment)."""
    E, _, _ = modules()
    import sentence_law
    timing, toks = record_tokens(rec)
    out = []
    for k, (w0, w1) in enumerate(E.split_sentences(toks)):
        out.append({"k": k, "w0": w0, "w1": w1, "text": E.spoken(toks[w0:w1 + 1]),
                    "start": toks[w0].get("start"), "end": toks[w1].get("end"),
                    "complete": bool(sentence_law.is_terminal(toks[w1].get("word")))})
    return timing, toks, out


def turn_change_inside(toks, w0, w1):
    """True when a caption speaker marker ('>>') starts a token after the span's first: a measured speaker change.
    None otherwise: the absence of a marker is not a measurement (auto captions carry none; law L-m)."""
    for t in toks[w0 + 1:w1 + 1]:
        if str(t.get("word") or "").startswith(SPEAKER_MARKERS):
            return True
    return None


def source_for(rec, meta, timing, toks):
    """eligibility.Source of a whole caption / word record of a VOD (file_head: the record starts at the media's
    first word; vod: the fetcher established an upload or a finished stream, never a Short / live / upcoming)."""
    E, _, _ = modules()
    return E.Source(video_id=rec["video_id"], channel_id=meta.get("channel_id"), channel_name=meta.get("channel_name"),
                    published_at=meta.get("published_at"), transcript_sha256=rec.get("transcript_sha256"),
                    transcript_method=rec.get("transcript_method"), tokens=toks, timing=timing, file_head=True,
                    vod=True, title=meta.get("exact_title") or "")


def eligibility_at_mining(src, registry, k0, k1, now):
    """eligibility.eligible(Span, role clip) as judged at mining time; the packager re-judges with its own clock and
    word timing. A failure to evaluate is recorded as a failed evaluation, never as ok."""
    E, _, _ = modules()
    try:
        res = E.eligible(E.Span(src, k0, k1), E.Context(now=now, registry=registry, role="clip"))
        return {"role": "clip", "ok": bool(res.ok), "reasons": [[r.name, r.detail] for r in res.reasons],
                "targets_missed": list(res.facts.get("targets_missed") or [])}
    except Exception as e:
        return {"role": "clip", "ok": False, "reasons": [["not_evaluated", f"{type(e).__name__}: {e}"[:300]]],
                "targets_missed": []}


def verify_line(line, rec):
    """A ledger line still names its text under the current definitions: (True, '') or (False, why)."""
    try:
        timing, toks, sents = sentences(rec)
    except Exception as e:
        return False, f"record unreadable: {type(e).__name__}: {e}"
    if rec.get("transcript_sha256") != line.get("transcript_sha256"):
        return False, "transcript sha differs"
    k0, k1 = line["sentences"]
    if not (0 <= k0 <= k1 < len(sents)):
        return False, f"sentences {k0}..{k1} out of range"
    w0, w1 = sents[k0]["w0"], sents[k1]["w1"]
    if [w0, w1] != list(line["words"]):
        return False, f"words {line['words']} != {[w0, w1]} under the current definitions"
    E, _, _ = modules()
    if E.spoken(toks[w0:w1 + 1]) != line["text"]:
        return False, "text differs under the current definitions"
    if moment_id(line["video_id"], line["transcript_sha256"], w0, w1) != line["moment_id"]:
        return False, "moment_id differs"
    return True, ""
