#!/usr/bin/env python3
"""pipeline/oracle/witness.py — the reviewers' witness checks on moments-first line-ups (orchestrator note 02:30 ET).

For every moments line-up the blind judge accepted, a second blind call (the 'witness' role of the provider config,
never the writer's vendor) reads each clip INSIDE its original conversation (the transcript from 90 s before to 60 s after
the clip, same record, caption speaker changes marked) and rules, per segment: whose view it is (the speaker's own
sincere assertion, or attributed / hypothetical / sarcastic / a question / read aloud / an ad read / uncertain), and
whether it is a named accusation, a buy / sell imperative or an ad read; and, for the line-up, whether a viewer would
take a speaker as answering, agreeing with or contradicting a speaker from ANOTHER video. One excerpt per channel is
checked here, deterministically. Decision rule (claude.md section 2): any 'uncertain' is a fail; a reply that is not
whole and consistent is WITNESS_FAILED, and a line-up whose witness check failed never counts as passing it.
"""
import json
import os

from pipeline.oracle import export as X
from pipeline.oracle import lineup as L
from pipeline.oracle import llm
from pipeline.oracle import prompts as P
from pipeline.oracle import run as R
import transcript_store as ts  # noqa: E402

BEFORE_S, AFTER_S = 90.0, 60.0
VIEWS = ("own_sincere", "attributed", "hypothetical", "sarcastic", "question", "reading_aloud", "ad_read", "uncertain")
FLAGS = ("named_accusation", "buy_sell_imperative", "ad_read")
CHECKS = ("one_excerpt_per_channel", "sincere_in_context", "no_implied_relation", "no_accusation_imperative_ad")
SYSTEM = ("You check whether verbatim clips keep their meaning once lifted out of their original conversation and "
          "placed next to clips from other videos. Judge only from the text shown. Any uncertainty is a fail.")
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["segments", "implied_relation_across_videos", "verdict", "reason"],
          "properties": {
              "segments": {"type": "array", "items": {
                  "type": "object", "additionalProperties": False,
                  "required": ["segment", "speaker_view", "own_sincere_assertion"] + list(FLAGS) + ["reason"],
                  "properties": {"segment": {"type": "integer"}, "speaker_view": {"type": "string", "enum": list(VIEWS)},
                                 "own_sincere_assertion": {"type": "boolean"},
                                 **{f: {"type": "boolean"} for f in FLAGS}, "reason": {"type": "string"}}}},
              "implied_relation_across_videos": {"type": "boolean"},
              "verdict": {"type": "string", "enum": ["PASS", "FAIL"]}, "reason": {"type": "string"}}}


class WitnessFailed(ValueError):
    pass


def context(store_dir, rows, before=BEFORE_S, after=AFTER_S):
    """The original conversation around one segment (rows = its export rows): [(start_s, text, is_clip,
    speaker_change)] for every sentence of the SAME transcript record that overlaps [start - before, end + after]."""
    r0 = rows[0]
    rec = X.load_record(store_dir, r0["video_id"], r0["transcript_sha256"])
    if rec is None:
        raise WitnessFailed(f"no record {r0['video_id']} {r0['transcript_sha256'][:12]} in the store")
    toks, _ = X.tokens(rec)
    sents = X.sentences(toks)
    for r in rows:                       # the record must still give the export's sentences (audit round 3, F4)
        si = r["sentence_index"]
        if si >= len(sents) or ts.read_text(" ".join(toks[i][0] for i in sents[si])) != r["text"]:
            raise WitnessFailed(f"{r['id']}: the record no longer gives the exported sentence (changed since the export)")
    lo, hi = rows[0]["start_s"] - before, rows[-1]["end_s"] + after
    clip = {r["sentence_index"] for r in rows}
    out = []
    for si, idx in enumerate(sents):
        st, en = toks[idx[0]][1], toks[idx[-1]][2]
        if en < lo or st > hi:
            continue
        change = idx[0] > 0 and ts.read_text(toks[idx[0] - 1][0]) == ">>"
        out.append((round(st, 1), ts.read_text(" ".join(toks[i][0] for i in idx)), si in clip, change))
    return out


def prompt(lu, rows_by_id, now_utc, store_dir):
    parts = []
    for n, (label, ids) in enumerate(L.segments(lu), 1):
        rows = [rows_by_id[i] for i in ids]
        lines = []
        for st, text, is_clip, change in context(store_dir, rows):
            lines.append(f"  {'>> ' if change else ''}{'[CLIP] ' if is_clip else ''}[{st:.0f} s] {text}")
        r0 = rows[0]
        parts.append(f"SEGMENT {n} ({'HOOK' if label == 'hook' else 'CLIP'}) - channel: {r0['channel']} - video "
                     f"{json.dumps(r0['title'] or '', ensure_ascii=False)} published {P._utc(r0['published_at'])}\n"
                     f"  clip as heard: {' '.join(rows_by_id[i]['text'] for i in ids)}\n"
                     f"  ORIGINAL CONTEXT (90 s before to 60 s after; [CLIP] marks the clip's own sentences; '>>' marks "
                     f"a new speaker where the captions show one):\n" + "\n".join(lines))
    return f"""TASK
A 60-70 s Bitcoin video made at {P._utc(now_utc)} plays these clips from partner channels in this order (a short
voiceover may link them). Each clip is verbatim, but it is heard WITHOUT its original conversation. Decide, from the
original context shown for each, whether the clip keeps its meaning, and whether the line-up as a whole implies
something its speakers did not say.

LINE-UP (in playback order)
{chr(10).join(parts)}

FOR EACH SEGMENT
- speaker_view: whose view the clip states: "own_sincere" (the speaker's own sincere assertion), "attributed" (the
  speaker reports someone else's view), "hypothetical", "sarcastic", "question", "reading_aloud" (a tweet, headline
  or script read out), "ad_read" (a sponsor or ad message, or third-party media played in the video), "uncertain".
- own_sincere_assertion: true only if speaker_view is "own_sincere" AND nothing in the context (a condition, a time
  frame, a reversal or retraction, a quoted opponent, a joke) changes what the clip asserts when heard alone.
- named_accusation: the clip accuses a named person or company of a crime, fraud or dishonesty.
- buy_sell_imperative: the clip tells the viewer to buy, sell, hold or use leverage.
- ad_read: the clip is an ad read or sponsor message (or third-party media played in the video).
FOR THE LINE-UP
- implied_relation_across_videos: true if a viewer would take a speaker as answering, agreeing with, confirming or
  contradicting a speaker from a DIFFERENT video.
- verdict: "PASS" only if every segment is own_sincere_assertion true with no named_accusation, buy_sell_imperative or
  ad_read, and implied_relation_across_videos is false; otherwise "FAIL". Anything uncertain is a fail.

OUTPUT
Return ONLY a JSON object: {{"segments": [{{"segment": 1, "speaker_view": ..., "own_sincere_assertion": true/false,
"named_accusation": true/false, "buy_sell_imperative": true/false, "ad_read": true/false, "reason": short}}, ...],
"implied_relation_across_videos": true/false, "verdict": "PASS" or "FAIL", "reason": one or two sentences}}"""


def parse(text, n_segments):
    """The witness verdict, whole and consistent, or WitnessFailed."""
    try:
        o = json.loads(text) if isinstance(text, str) and text.strip() else None
    except ValueError as e:
        raise WitnessFailed(f"not JSON: {e}")
    if not isinstance(o, dict) or set(o) != set(SCHEMA["required"]):
        raise WitnessFailed("reply keys")
    segs = o["segments"]
    if not isinstance(segs, list) or sorted(s.get("segment") for s in segs if isinstance(s, dict)) != \
            list(range(1, n_segments + 1)) or len(segs) != n_segments:
        raise WitnessFailed(f"segments must be 1..{n_segments}, each once")
    for s in segs:
        if set(s) != set(SCHEMA["properties"]["segments"]["items"]["required"]) or s["speaker_view"] not in VIEWS \
                or not all(type(s[k]) is bool for k in ("own_sincere_assertion",) + FLAGS):
            raise WitnessFailed(f"malformed segment {str(s)[:120]}")
        if s["own_sincere_assertion"] and s["speaker_view"] != "own_sincere":
            raise WitnessFailed(f"segment {s['segment']}: own_sincere_assertion with view {s['speaker_view']}")
    if type(o["implied_relation_across_videos"]) is not bool or o["verdict"] not in ("PASS", "FAIL"):
        raise WitnessFailed("line-up fields")
    ok = all(s["own_sincere_assertion"] and not any(s[f] for f in FLAGS) for s in segs) \
        and not o["implied_relation_across_videos"]
    if (o["verdict"] == "PASS") != ok:
        raise WitnessFailed(f"verdict {o['verdict']} contradicts the fields")
    return o


def checks_of(lu, rows_by_id, verdict):
    """{check: bool} for one line-up; None per model check when the witness call failed (never a pass)."""
    chans = [rows_by_id[ids[0]]["channel_id"] for _, ids in L.segments(lu)]
    out = {"one_excerpt_per_channel": len(chans) == len(set(chans))}
    if verdict is None:
        out.update({k: None for k in CHECKS[1:]})
    else:
        segs = verdict["segments"]
        out.update(sincere_in_context=all(s["own_sincere_assertion"] for s in segs),
                   no_implied_relation=not verdict["implied_relation_across_videos"],
                   no_accusation_imperative_ad=not any(s[f] for s in segs for f in FLAGS))
    return out


def run_witness(vdir, rows, now_utc, call, ledger, store_dir=X.MAIN_STORE, attempts=2):
    """WITNESS.json for one moments day dir: per accepted line-up, its checks (model calls + the deterministic one)."""
    with open(os.path.join(vdir, "DAY.json"), encoding="utf-8") as f:
        day = json.load(f)
    with open(os.path.join(vdir, "ORACLE.json"), encoding="utf-8") as f:
        lus = json.load(f).get("lineups") or []
    by_id = {r["id"]: r for r in rows}
    res = []
    for row in day["lineups"]:
        if not row["accepted"]:
            continue
        k, lu = row["lineup"], lus[row["lineup"] - 1]
        rec = {"lineup": k, "status": "WITNESS_FAILED", "attempts": []}
        try:
            user = prompt(lu, by_id, now_utc, store_dir)
        except Exception as e:                             # missing / altered record, store error: this line-up only
            rec["attempts"].append({"error": llm.redact(f"context: {type(e).__name__}: {e}")[:400]})
            user = None
        if user:
            with open(os.path.join(vdir, f"witness_L{k}_prompt.txt"), "w", encoding="utf-8") as f:
                f.write(f"SYSTEM:\n{SYSTEM}\n\nUSER:\n{user}")
            for n in range(1, attempts + 1):
                try:
                    text, raw, usage = call(SYSTEM, user, SCHEMA, ledger, f"witness {os.path.basename(os.path.dirname(vdir))} L{k} #{n}")
                    with open(os.path.join(vdir, f"witness_L{k}_attempt{n}_raw.json"), "w", encoding="utf-8") as f:
                        json.dump(raw, f, indent=1, default=str)
                    v = parse(text, len(L.segments(lu)))
                except Exception as e:                     # API error, SpendStop, malformed: not measured
                    rec["attempts"].append({"attempt": n, "error": llm.redact(f"{type(e).__name__}: {e}")[:400]})
                    if type(e).__name__ == "SpendStop":
                        break
                    continue
                rec.update(status="OK", verdict=v)
                rec["attempts"].append({"attempt": n, "usage": usage})
                break
        rec["checks"] = checks_of(lu, by_id, rec.get("verdict"))
        res.append(rec)
    models = sorted({(a.get("usage") or {}).get("model") for x in res for a in x["attempts"] if a.get("usage")} - {None})
    out = {"variant": "moments", "witness_models": models, "context_s": [BEFORE_S, AFTER_S], "lineups": res,
           "oracle_sha256": R.oracle_sha(vdir)}
    with open(os.path.join(vdir, "WITNESS.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True, default=str)
    return out


def survivors(vdir, require):
    """Accepted moments line-ups (their ORACLE line-up dicts) passing every check in `require` (a check that did not
    run is a fail), from DAY.json / ORACLE.json / WITNESS.json. A WITNESS.json that does not belong to the current
    ORACLE.json is stale and yields nothing (audit F8); only line-ups DAY.json accepted are ever counted."""
    if not R.fresh(vdir, "WITNESS.json"):
        raise WitnessFailed(f"{vdir}: WITNESS.json does not belong to the current ORACLE.json (stale)")
    with open(os.path.join(vdir, "ORACLE.json"), encoding="utf-8") as f:
        lus = json.load(f).get("lineups") or []
    with open(os.path.join(vdir, "DAY.json"), encoding="utf-8") as f:
        accepted = {r["lineup"] for r in json.load(f)["lineups"] if r["accepted"]}
    with open(os.path.join(vdir, "WITNESS.json"), encoding="utf-8") as f:
        w = {x["lineup"]: x["checks"] for x in json.load(f)["lineups"]}
    return [lus[k - 1] for k, ch in sorted(w.items())
            if k in accepted and all(ch.get(c) is True for c in require)]
