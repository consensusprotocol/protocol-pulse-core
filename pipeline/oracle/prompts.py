#!/usr/bin/env python3
"""pipeline/oracle/prompts.py — the two prompts (structure: task, tone, rules, data, instructions, format, reminder).

oracle_prompt  the day's statements and the written rules ONLY: no selector output, no candidate list, no hint of
               what any earlier stage decided (blind supply oracle).
judge_prompt   one line-up in playback order and the same rules: no word on who built it (the oracle and the
               selector's line-ups are shown identically) and no builder's rationale.
Times are seconds into each source video; '~' marks a time placed by character offset inside a caption line or
Whisper segment (pipeline/oracle/export.py), never a measured word boundary.
"""
import json

from pipeline.oracle import lineup as L

ORACLE_SYSTEM = ("You are a senior editor of a Bitcoin news video built only from partner channels' own words. "
                 "You read every statement before you decide. You use only the statements given and cite them by "
                 "their ids exactly as written. If no line-up satisfies every rule, you say NONE and why; you never "
                 "bend a rule to produce one. Only state what you can verify from the statements.")

JUDGE_SYSTEM = ("You check ONE proposed line-up for a Bitcoin news video against written rules. Judge only what "
                "the text shows. If you cannot verify from the text given that a rule holds, that rule does not "
                "hold. Do not guess.")


def _utc(ts):
    return (ts or "?")[:16].replace("T", " ") + " UTC"


def _times(r):
    mark = "" if r["timing"] == "word" else "~"
    return f"{mark}{r['start_s']:.1f}-{mark}{r['end_s']:.1f}"


def statements_block(rows):
    """Rows grouped by video (in export order), one sentence per line."""
    out, cur = [], None
    for r in rows:
        if r["video_id"] != cur:
            cur = r["video_id"]
            out.append(f"\n== VIDEO {cur} | channel: {r['channel']} | published {_utc(r['published_at'])} "
                       f"({r['age_h']:.0f} h before the video is made) | title: {json.dumps(r['title'] or '', ensure_ascii=False)}")
        out.append(f"{r['id']} | {_times(r)} | {r['text']}")
    return "\n".join(out).lstrip("\n")


def oracle_prompt(rows, now_utc, variant="same_dev_hard"):
    if variant != "same_dev_hard":
        return _oracle_prompt_distinct(rows, now_utc, variant)
    return f"""TASK
You are given every candidate statement that partner YouTube channels made about Bitcoin in the 72 hours before
the video is made ({_utc(now_utc)}), sentence by sentence. Build up to {L.MAX_LINEUPS} line-ups that satisfy EVERY
rule below, best first, or answer NONE with the reason. Prefer line-ups about different developments; if only one
development qualifies, alternative line-ups of it are allowed.

{L.RULES}

HOW THE STATEMENTS ARE SHOWN
- Grouped by video: channel, publish time (UTC), hours before the video is made, title.
- One sentence per line: id | start-end in seconds into that video | text. '~' marks a time estimated from caption
  timing (about +-1 s). A segment lasts from the start of its first sentence to the end of its last.
- Within one video, consecutive numbers are consecutive sentences. A jump in the numbers means the sentences in
  between are not available: a segment may not span a jump. Only the sentences shown exist.
- The text comes from captions or speech recognition; small transcription errors are normal.

STATEMENTS
{statements_block(rows)}

INSTRUCTIONS
1. Find the specific Bitcoin developments that at least two different channels state as current news.
2. For each, choose a hook (1-{L.MAX_SENTENCES} consecutive sentences of one video, {L.HOOK_S[0]:g}-{L.HOOK_S[1]:g} s) that stands alone, then {L.CLIPS[0]}-{L.CLIPS[1]} clips
   ({L.CLIP_S[0]:g}-{L.CLIP_S[1]:g} s each), so that the line-up comes from at least two channels.
3. Check every rule against the exact sentences you chose, including the durations and the {L.MIN_CONTENT_S:g} s total.
4. If no line-up satisfies every rule, answer NONE and say which rule the day's statements cannot meet.

OUTPUT
Return ONLY a JSON object:
{{"verdict": "LINEUPS" or "NONE",
 "none_reason": "" for LINEUPS, else why no line-up satisfies the rules,
 "lineups": [ {{"development": the development in one sentence,
               "current_because": why it is current news (which statements, when),
               "hook": [sentence ids in order],
               "clips": [[sentence ids in order], [sentence ids in order], ...]}} ] (empty for NONE)}}

REMINDER: every id exactly as shown; each segment is consecutive sentences of one video; hook {L.HOOK_S[0]:g}-{L.HOOK_S[1]:g} s,
clips {L.CLIP_S[0]:g}-{L.CLIP_S[1]:g} s, total at least {L.MIN_CONTENT_S:g} s, at least two channels, one current development, no altcoin content."""


def lineup_block(lu, rows_by_id):
    out = []
    for n, (label, ids) in enumerate(L.segments(lu), 1):
        rows = [rows_by_id[i] for i in ids]
        r0 = rows[0]
        dur = rows[-1]["end_s"] - r0["start_s"]
        est = "~" if any(r["timing"] != "word" for r in rows) else ""
        out.append(f"SEGMENT {n} - {'HOOK' if label == 'hook' else 'CLIP'} - channel: {r0['channel']} - video "
                   f"published {_utc(r0['published_at'])} ({r0['age_h']:.0f} h before the video is made) - title: "
                   f"{json.dumps(r0['title'] or '', ensure_ascii=False)} - {est}{r0['start_s']:.1f}-{est}{rows[-1]['end_s']:.1f} s "
                   f"({est}{dur:.1f} s)")
        out += [f"  [{r['id']}] {r['text']}" for r in rows]
    return "\n".join(out)


def judge_prompt(lu, rows_by_id, now_utc, variant="same_dev_hard"):
    if variant != "same_dev_hard":
        return _judge_prompt_variant(lu, rows_by_id, now_utc, variant)
    checks = ", ".join(f'"{k}": true/false' for k in L.JUDGE_CHECKS)
    return f"""TASK
The video is made at {_utc(now_utc)}. Below is one proposed line-up: it plays in this order, the hook first, then
the clips, followed by a credits card and an outro. Decide whether it satisfies EVERY rule.

{L.RULES}

HOW THE LINE-UP IS SHOWN
Each segment names its channel, when its video was published, and its start-end in seconds into that video ('~' =
estimated from caption timing, about +-1 s), then its sentences as transcribed (captions or speech recognition;
small transcription errors are normal).

PROPOSED LINE-UP
{lineup_block(lu, rows_by_id)}

INSTRUCTIONS
Decide each check for THIS line-up, exactly as the rules are written:
- one_development_two_channels: rule 1 (one specific development, stated by at least two different channels;
  every segment states it or a direct consequence of / reaction to it)
- current: rule 2
- hook_stands_alone: rule 3
- whole_standalone_sentences: rule 4
- enough_for_60_70_s: rule 5 (use the times shown)
- no_altcoin_content: rule 6
- format_limits: the format limits

OUTPUT
Return ONLY a JSON object:
{{"development": the one development this line-up states, in one sentence ("none" if there is no single one),
 "checks": {{{checks}}},
 "failed": [the names of the checks that are false],
 "verdict": "LEGAL" if every check is true, else "ILLEGAL",
 "reason": one or two sentences}}

REMINDER: a rule you cannot verify from the text shown does not hold; LEGAL only if every check is true."""


# ── the 01:55 variants (same development with target windows; moments first): as many disjoint line-ups as exist ──

_SHOWN = """HOW THE STATEMENTS ARE SHOWN
- Grouped by video: channel, publish time (UTC), hours before the video is made, title.
- One sentence per line: id | start-end in seconds into that video | text. '~' marks a time estimated from caption
  timing (about +-1 s). A segment lasts from the start of its first sentence to the end of its last.
- Within one video, consecutive numbers are consecutive sentences. A jump in the numbers means the sentences in
  between are not available: a segment may not span a jump. Only the sentences shown exist.
- The text comes from captions or speech recognition; small transcription errors are normal."""

_FIND = {
    "same_dev_hard_max": ("1. Find the specific Bitcoin developments that at least two different channels state as current news.\n"
                          "2. For one development, choose a hook (1-{n} consecutive sentences of one video, {h0:g}-{h1:g} s) that "
                          "stands alone, then {c0}-{c1} clips ({k0:g}-{k1:g} s each), so that the line-up comes from at least two "
                          "channels."),
    "same_dev": ("1. Find the specific Bitcoin developments that at least two different channels state as current news.\n"
                 "2. For one development, choose a hook (1-{n} consecutive sentences of one video, about {h0:g}-{h1:g} s) that "
                 "stands alone, then {c0}-{c1} clips (about {k0:g}-{k1:g} s each), so that the line-up comes from at least two "
                 "channels. Prefer segments inside these targets; go outside them only when a statement needs it."),
    "moments": ("1. Find the strongest stand-alone moments about Bitcoin: specific current claims, numbers, insights or "
                "strong views, from at least two different channels.\n"
                "2. Build a line-up: a hook (1-{n} consecutive sentences of one video, about {h0:g}-{h1:g} s) that stands "
                "alone, then {c0}-{c1} clips (about {k0:g}-{k1:g} s each), from at least two channels in all. Order them so "
                "a short truthful voiceover could link them and no segment sounds like another channel's reply, "
                "confirmation or source unless it is one. Prefer segments inside the duration targets; go outside them "
                "only when a moment needs it.")}
_ABOUT = {"same_dev": "the development in one sentence", "same_dev_hard_max": "the development in one sentence",
          "moments": "what the line-up is about, in one sentence (its moments may differ)"}
_ONE = {"same_dev": "one current development per line-up", "moments": "every segment current and never misattributed",
        "same_dev_hard_max": "hook 8-12 s, clips 12-20 s, one current development per line-up"}


def _oracle_prompt_distinct(rows, now_utc, variant):
    v = L.VARIANTS[variant]
    find = _FIND[variant].format(n=L.MAX_SENTENCES, h0=L.HOOK_S[0], h1=L.HOOK_S[1], c0=L.CLIPS[0], c1=L.CLIPS[1],
                                 k0=L.CLIP_S[0], k1=L.CLIP_S[1])
    each = ("Each line-up is about one development; different line-ups may be about different developments or tell the "
            "same development with different statements." if variant in ("same_dev", "same_dev_hard_max") else
            "A line-up's segments need not share a development (rule 1).")
    return f"""TASK
You are given every candidate statement that partner YouTube channels made about Bitcoin in the 72 hours before
the video is made ({_utc(now_utc)}), sentence by sentence. Build as many DISTINCT line-ups as these statements
support, up to {v['max_lineups']}, best first: distinct means that no sentence is used in two line-ups. Every line-up must satisfy
EVERY rule below. {each} If no line-up satisfies every rule, answer NONE with the reason.

{v['rules']}

{_SHOWN}

STATEMENTS
{statements_block(rows)}

INSTRUCTIONS
{find}
3. Then build further line-ups from sentences no earlier line-up uses, until no further line-up satisfies every
   rule or you have {v['max_lineups']}.
4. Check every rule against the exact sentences you chose, including the {L.MIN_CONTENT_S:g} s total.
5. If no line-up satisfies every rule, answer NONE and say which rule the day's statements cannot meet.

OUTPUT
Return ONLY a JSON object:
{{"verdict": "LINEUPS" or "NONE",
 "none_reason": "" for LINEUPS, else why no line-up satisfies the rules,
 "lineups": [ {{"development": {_ABOUT[variant]},
               "current_because": why it is current (which statements, when),
               "hook": [sentence ids in order],
               "clips": [[sentence ids in order], [sentence ids in order], ...]}} ] (empty for NONE)}}

REMINDER: every id exactly as shown; each segment is consecutive sentences of one video; no sentence in two
line-ups; total at least {L.MIN_CONTENT_S:g} s; at least two channels; {_ONE[variant]}; no altcoin content."""


_CHECK_TEXT = {
    "one_development_two_channels": "rule 1 (one specific development, stated by at least two different channels; "
                                    "every segment states it or a direct consequence of / reaction to it)",
    "two_channels_never_misattributed": "rule 1 (at least two different channels; the order allows a truthful short "
                                        "voiceover bridge; no segment is heard as another channel's reply, "
                                        "confirmation or source unless it is one)",
    "current": "rule 2", "hook_stands_alone": "rule 3", "whole_standalone_sentences": "rule 4",
    "enough_for_60_70_s": "rule 5 (use the times shown; a single segment's duration is a target, not a limit)",
    "no_altcoin_content": "rule 6", "format_limits": "the format limits"}


def _judge_prompt_variant(lu, rows_by_id, now_utc, variant):
    v = L.VARIANTS[variant]
    checks = ", ".join(f'"{k}": true/false' for k in v["checks"])
    what = ("the one development this line-up states, in one sentence (\"none\" if there is no single one)"
            if variant == "same_dev" else "what this line-up is about, in one sentence")
    lines = "\n".join(f"- {k}: {_CHECK_TEXT[k]}" for k in v["checks"])
    return f"""TASK
The video is made at {_utc(now_utc)}. Below is one proposed line-up: it plays in this order, the hook first, then
the clips, followed by a credits card and an outro. Decide whether it satisfies EVERY rule.

{v['rules']}

HOW THE LINE-UP IS SHOWN
Each segment names its channel, when its video was published, and its start-end in seconds into that video ('~' =
estimated from caption timing, about +-1 s), then its sentences as transcribed (captions or speech recognition;
small transcription errors are normal).

PROPOSED LINE-UP
{lineup_block(lu, rows_by_id)}

INSTRUCTIONS
Decide each check for THIS line-up, exactly as the rules are written:
{lines}

OUTPUT
Return ONLY a JSON object:
{{"development": {what},
 "checks": {{{checks}}},
 "failed": [the names of the checks that are false],
 "verdict": "LEGAL" if every check is true, else "ILLEGAL",
 "reason": one or two sentences}}

REMINDER: a rule you cannot verify from the text shown does not hold; LEGAL only if every check is true."""
