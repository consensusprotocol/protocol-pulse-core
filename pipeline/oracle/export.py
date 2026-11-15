#!/usr/bin/env python3
"""pipeline/oracle/export.py — BITCOIN_STATEMENTS_<run>.jsonl: the candidate sentences of one saved universe.

  universe   the run's own TOPIC_SELECTION.json universe. Every video with a transcript sha is read from the
             transcript store by THAT sha (hash-checked): a record that is missing is a counted gap in the
             manifest, never replaced by another record; a record whose content no longer matches its sha (the store
             was altered after the run) stops the whole export (ExportError): that universe cannot be reproduced.
  text       read as spoken (law L-h): transcript_store.read_text over the record's own words, once (entities
             decoded, split Whisper tokens read whole); `canon` = canon.canon(text) (law L-k). Neither is
             re-implemented here.
  sentences  a sentence ends where sentence_law.is_terminal says (through editorial_select._word_sentences, the
             selector's own split). Caption markup that is not speech belongs to no sentence: a speaker change
             ('>>') ends the sentence before it; a lone bracketed annotation ('[Music]') is dropped.
  times      word records keep their words' timestamps (timing 'word'). Caption lines and Whisper segments carry
             one start / end per line, so a sentence inside them is placed by character offset (timing
             'caption_line' / 'segment'): an estimate, labelled as one.
  candidate  a sentence that names Bitcoin (editorial_select.BITCOIN_TERMS, the selector's free screen) or lies
             within NEIGHBOURHOOD sentences of one in the same video, so every window of 1-3 whole sentences
             holding a Bitcoin sentence is made of exported rows only.
Deterministic: rows sorted by (published_at, video_id, sentence_index), keys sorted, fixed separators, rounded
times; the same universe, store and channel registry (layout fields come from the registry; its sha256 is in the
manifest) give byte-identical files (tests/oracle/test_oracle_export.py).
"""
import glob
import hashlib
import json
import os
import re

import canon  # noqa: E402  (flat, as the pipeline imports them: pipeline/oracle/__init__.py puts pipeline/ on sys.path)
import editorial_select as es  # noqa: E402
import punctuation  # noqa: E402
import sentence_law  # noqa: E402
import transcript_store as ts  # noqa: E402

MAIN_STORE = "/home/ultron/protocol_pulse/data/editorial"      # read-only: the store every saved run read
NEIGHBOURHOOD = es.MAX_WINDOW_SENTENCES - 1
SPEAKER = re.compile(r"(&gt;&gt;|>>)")                          # caption speaker change, raw or decoded
ANNOTATION = re.compile(r"\[[^\]\s]+\]")                        # '[Music]', '[Applause]': not speech
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{6,20}")


class ExportError(Exception):
    pass


def load_record(store_dir, video_id, sha):
    """The transcript record of `video_id` whose sha is `sha`, hash-checked; None when the store has none. Two records
    carrying the same sha are ambiguous (which one did the run read?): ExportError, never the first by name."""
    if not VIDEO_ID.fullmatch(video_id or ""):
        raise ExportError(f"invalid video_id {video_id!r}")
    found = []
    for p in sorted(glob.glob(os.path.join(store_dir, "transcripts", video_id, "transcript.*.json"))):
        with open(p, encoding="utf-8") as f:
            rec = json.load(f)
        if rec.get("transcript_sha256") != sha:
            continue
        if ts.segments_sha256(rec["segments"]) != sha:
            raise ExportError(f"transcript hash mismatch: {p}")
        found.append((p, rec))
    if len(found) > 1:
        raise ExportError(f"{len(found)} records of {video_id} carry sha {sha[:12]}: {[p for p, _ in found]}")
    return found[0][1] if found else None


def tokens(rec):
    """([(raw token, start, end)], timing) in speech order."""
    if rec.get("words"):
        return [(w["word"].strip(), float(w["start"]), float(w["end"])) for w in rec["words"]
                if (w.get("word") or "").strip()], "word"
    timing = "segment" if rec["transcript_method"].split(":")[0] == "whisper" else "caption_line"
    cues = []                                                    # the lines of one cue share its time span
    for s in rec["segments"]:
        if cues and cues[-1][:2] == [s["start"], s["end"]]:
            cues[-1][2].append(s["text"])
        else:
            cues.append([s["start"], s["end"], [s["text"]]])
    out = []
    for a, b, texts in cues:
        t = SPEAKER.sub(r" \1 ", " ".join(texts))
        n = max(len(t), 1)
        out += [(m.group(0), a + (b - a) * m.start() / n, a + (b - a) * m.end() / n)
                for m in re.finditer(r"\S+", t)]
    return out, timing


def sentences(toks):
    """[[token index, ...]] per sentence. The split is the selector's (is_terminal on each token read as spoken);
    a speaker change ends the sentence before it; markers and annotations belong to no sentence."""
    out, run = [], []

    def flush():
        ws = [{"word": ts.read_text(toks[i][0])} for i in run]
        out.extend([run[k] for k in range(a, b + 1)] for a, b in es._word_sentences(ws))
        run.clear()
    for i, (tok, _, _) in enumerate(toks):
        read = ts.read_text(tok)
        if read == ">>":
            flush()
        elif not ANNOTATION.fullmatch(read):
            run.append(i)
    flush()
    return out


def video_rows(rec, u, registry_by_cid):
    """All sentences of one video as rows (candidate or not) + the video's counts."""
    toks, timing = tokens(rec)
    sents = sentences(toks)
    ch = registry_by_cid.get(u.get("channel_id")) or {}
    rows = []
    for si, idx in enumerate(sents):
        text = ts.read_text(" ".join(toks[i][0] for i in idx))
        last = ts.read_text(toks[idx[-1]][0])
        st, en = toks[idx[0]][1], toks[idx[-1]][2]
        rows.append({"id": f"{u['video_id']}:{si}", "video_id": u["video_id"], "sentence_index": si,
                     "channel": u.get("channel"), "channel_id": u.get("channel_id"), "title": u.get("title"),
                     "published_at": u.get("published_at"), "age_h": round(float(u.get("age_h") or 0), 2),
                     "start_s": round(st, 2), "end_s": round(en, 2), "duration_s": round(en - st, 2),
                     "timing": timing, "text": text, "canon": canon.canon(text),
                     "bitcoin": bool(es.BITCOIN_TERMS.search(text)),
                     "complete": sentence_law.is_terminal(last), "ends_statement": es._ends_statement(last),
                     "layout_eligible": es.layout_eligible(ch) if ch else False,
                     "layout_eligible_run": bool(u.get("layout_eligible")),
                     "layout_status": ch.get("layout_status"), "has_chyron": bool(ch.get("has_chyron")),
                     "transcript_method": rec["transcript_method"], "transcript_sha256": rec["transcript_sha256"]})
    btc = [r["sentence_index"] for r in rows if r["bitcoin"]]
    keep = {i for j in btc for i in range(j - NEIGHBOURHOOD, j + NEIGHBOURHOOD + 1)}
    words = rec.get("words") or []
    counts = {"video_id": u["video_id"], "channel": u.get("channel"), "method": rec["transcript_method"],
              "timing": timing, "sentences": len(rows), "bitcoin_sentences": len(btc),
              "candidate_rows": sum(1 for r in rows if r["sentence_index"] in keep),
              "longest_sentence_s": max((r["duration_s"] for r in rows), default=0.0),
              "punctuation_gap": bool(words) and punctuation.needs_restoration(words),
              # what was actually read (the words when present: segments_sha256 covers only the segments), so a
              # later export can show the record it read is the same one (audit round 2, F7)
              "read_sha256": hashlib.sha256(json.dumps(toks, ensure_ascii=False).encode("utf-8")).hexdigest()}
    return [r for r in rows if r["sentence_index"] in keep], counts


def export_run(run_dir, store_dir=MAIN_STORE, registry=None):
    """(rows, manifest) for one saved run. Pure: reads the run's TOPIC_SELECTION.json and the store, writes nothing."""
    with open(os.path.join(run_dir, "TOPIC_SELECTION.json"), encoding="utf-8") as f:
        sel = json.load(f)
    if registry is None:
        with open(es.CHANNELS_PATH, encoding="utf-8") as f:
            registry = json.load(f)
    by_cid = {c["channel_id"]: c for c in registry if c.get("channel_id")}
    universe = sel.get("universe") or []
    rows, per_video, gaps = [], [], []
    for u in sorted(universe, key=lambda u: u["video_id"]):
        sha = u.get("transcript_sha256")
        if not sha:
            gaps.append({"video_id": u["video_id"], "channel": u.get("channel"),
                         "gap": f"no transcript in the run ({u.get('transcript_status')})"})
            continue
        rec = load_record(store_dir, u["video_id"], sha)
        if rec is None:
            gaps.append({"video_id": u["video_id"], "channel": u.get("channel"), "gap": "record not in the store"})
            continue
        r, counts = video_rows(rec, u, by_cid)
        rows += r
        per_video.append(counts)
    rows.sort(key=lambda r: (r["published_at"] or "", r["video_id"], r["sentence_index"]))
    universe_sha = hashlib.sha256(json.dumps(sorted(universe, key=lambda u: u["video_id"]), sort_keys=True,
                                             ensure_ascii=False).encode("utf-8")).hexdigest()
    manifest = {"run": os.path.basename(os.path.normpath(run_dir)), "started": sel.get("started"),
                "today": sel.get("today"), "universe_sha256": universe_sha, "universe_videos": len(universe),
                "with_transcript_sha": sum(1 for u in universe if u.get("transcript_sha256")),
                "exported_videos": len(per_video), "gaps": gaps, "rows": len(rows),
                "bitcoin_rows": sum(1 for r in rows if r["bitcoin"]),
                "sentences_total": sum(v["sentences"] for v in per_video),
                "channels": sorted({r["channel"] for r in rows if r["channel"]}),
                "screen": es.BITCOIN_TERMS.pattern, "neighbourhood": NEIGHBOURHOOD, "per_video": per_video,
                "registry_sha256": hashlib.sha256(json.dumps(registry, sort_keys=True, ensure_ascii=False)
                                                  .encode("utf-8")).hexdigest()}
    return rows, manifest


def dumps_rows(rows):
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows)


def write_export(run_dir, out_dir, store_dir=MAIN_STORE, registry=None):
    """Write BITCOIN_STATEMENTS_<stamp>.jsonl + .manifest.json into out_dir; returns (jsonl path, manifest)."""
    rows, manifest = export_run(run_dir, store_dir, registry)
    stamp = manifest["run"].replace("fresh_", "")
    body = dumps_rows(rows).encode("utf-8")
    manifest["rows_sha256"] = hashlib.sha256(body).hexdigest()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"BITCOIN_STATEMENTS_{stamp}.jsonl")
    for p, data in ((path, body), (path.replace(".jsonl", ".manifest.json"),
                                   (json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=1) + "\n")
                                   .encode("utf-8"))):
        tmp = p + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, p)
    return path, manifest


def read_rows(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
