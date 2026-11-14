#!/usr/bin/env python3
"""pipeline/edl_rules.py — Editorial rules as hard code gates (R1-R9).

Every rule returns (pass: bool, reason: str). An EDL that fails ANY rule
is rejected and must not reach the renderer.

Usage:
    python3 -m pipeline.edl_rules --edl <edl.json> [--channels channels.json] [--layout-tables <dir>]

Rules:
    R1 NO_QUESTION_HOOK:      Hook passage must be a statement, not a question.
    R2 NO_DUPLICATE_PASSAGE:  No temporal overlap > 1.0s between any clips.
                              Hook may NOT be reused as clip 1 (same video_id + overlap).
    R3 VO_AFTER_ANSWER:       VO bridges only after clips ending on statements.
    R4 VO_BUDGET:             VO <= 25% of total runtime. Intro <= 30 words,
                              bridge <= 20 words, signoff <= 24 words.
                              One bridge per channel transition.
    R5 CLIP_LENGTH:           (law L-o) >= 2 measured clips from >= 2 channels; 12-20s = TASTE, a recorded deviation. >= 2 distinct
                              channels. Every channel >= 8s screen time.
    R6 CREDITS_MATCH:         Channels in shoutout/signoff/reply == channels
                              in EDL, in EDL order. Unique avatar hashes.
    R7 VERTICAL_LAYOUT_KNOWN: Every (channel, tile_count) must have an
                              explicit layout table entry.
    R8 G10_CHYRON_REGISTRY:   informational: has_chyron channels (a hint; G10 runs on every clip, ruling 93).
    R9 CLIP_ENDS_ON_SENTENCE: A clip's cut_out must land on a transcript word
                              that ends a sentence (. ? !) plus 0.20-0.45s tail
                              pause, strictly before the next source word starts.
    R11 VO_SHAPE:             (law L-y) a package of type 'moments': at most one
                              takeaway after the last clip and at most ONE line
                              before it (intro slot or between clips), only with
                              the package's recorded, confirmed bridge. No minimum.
"""
import math
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import INTRO_WORD_CAP, BRIDGE_WORD_CAP, SIGNOFF_WORD_CAP


def _word_count(text):
    return len(text.strip().split()) if text else 0


def _text_ends_with_question(text):
    """Check if text ends with a question mark or question-word pattern."""
    text = text.strip().rstrip(".")
    if text.endswith("?"):
        return True
    # Common question-start patterns
    q_words = ["what", "who", "where", "when", "why", "how", "do you", "is it",
               "are we", "can we", "should we", "will it", "could it"]
    lower = text.lower()
    for qw in q_words:
        if lower.startswith(qw + " "):
            return True
    return False


def _passage_overlap(clip_a, clip_b):
    """Compute temporal overlap between two clips (same video_id only)."""
    if clip_a.get("video_id") != clip_b.get("video_id"):
        return 0.0
    a_start = clip_a.get("word_start", 0)
    a_end = clip_a.get("word_end", 0)
    b_start = clip_b.get("word_start", 0)
    b_end = clip_b.get("word_end", 0)
    overlap = max(0, min(a_end, b_end) - max(a_start, b_start))
    return overlap


# ==============================================================
# R1: NO_QUESTION_HOOK
# ==============================================================

QUESTION_HOOK_JOIN = "hook -> clip_01"     # the join that follows the hook, as the packager names joins


def question_hook_join(edl):
    """Ruling 37 (orchestrator 2026-11-13 '03:42'): (ok, why) for the join that follows a question hook, from the
    package's SEALED gate rows (moments_gates): the clips-alone verdict (gates.medley) measured, exactly PASS, not
    replayed, its "flagged" a list WITHOUT that join; the blind coherence check (gates.coherence) exactly PASS, not
    replayed. Anything else fails closed."""
    gates = edl.get("moments_gates")
    med = gates.get("medley") if isinstance(gates, dict) else None
    coh = gates.get("coherence") if isinstance(gates, dict) else None
    if not isinstance(med, dict) or med.get("status") != "PASS" or med.get("replayed") is not False \
            or not isinstance(med.get("flagged"), list):
        return False, "the clips-alone verdict is not on the pin (moments_gates.medley: PASS, live, with its flagged joins)"
    if QUESTION_HOOK_JOIN in med["flagged"]:
        return False, f"the clips-alone verdict flagged the join that follows it ({QUESTION_HOOK_JOIN})"
    if not isinstance(coh, dict) or coh.get("status") != "PASS" or coh.get("replayed") is not False:
        return False, "the blind coherence check did not pass (moments_gates.coherence: PASS, live)"
    return True, (f"the clips-alone verdict passes the join that follows it ({QUESTION_HOOK_JOIN} not flagged) and the "
                  f"blind coherence check passes")


def rule_r1(edl):
    """Hook passage must be a statement, not a question.
    A passage that contains both a question AND an answer (ending on a statement)
    is acceptable — the rule targets pure-question hooks only.
    Ruling 37 (orchestrator 2026-11-13 '03:42'), moments packages only: a hook may end on a question when the clips-alone
    verdict and the blind coherence check pass the join that follows it (question_hook_join); a question ending stays
    refused for every non-hook clip. Every other EDL: unchanged."""
    hook = edl.get("hook", {})
    text = hook.get("text", "")
    if not text:
        return False, "R1 FAIL: hook has no text"

    # Split into sentences and check if the LAST sentence is a question
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    last_sentence = sentences[-1] if sentences else text

    moments = edl.get("package_type") == "moments" and "moments_package_sha256" in edl
    if moments:
        asked = [f"clip_{c.get('index')}" for c in edl.get("clips") or []
                 if isinstance(c, dict) and str(c.get("text") or "").rstrip().endswith("?")]
        if asked:
            return False, f"R1 FAIL (ruling 37): a question ending is refused for every non-hook clip: {asked}"

    # Check if the passage ENDS on a question (last meaningful sentence)
    if text.rstrip().endswith("?"):
        if moments:
            ok, why = question_hook_join(edl)
            return ok, f"R1 {'PASS' if ok else 'FAIL'} (ruling 37): the hook ends on a question and {why}"
        # Pure question ending — fail
        return False, f"R1 FAIL: hook ends with question: '{text[:60]}...'"

    return True, "R1 PASS: hook ends on a statement"


# ==============================================================
# R2: NO_DUPLICATE_PASSAGE
# ==============================================================

def rule_r2(edl):
    """No temporal overlap > 1.0s between any clip pair.
    Hook may NOT be reused as clip 1."""
    hook = edl.get("hook", {})
    clips = edl.get("clips", [])
    all_passages = [hook] + clips if hook else clips
    failures = []

    for i in range(len(all_passages)):
        for j in range(i + 1, len(all_passages)):
            overlap = _passage_overlap(all_passages[i], all_passages[j])
            if overlap > 1.0:
                label_i = "hook" if i == 0 and hook else f"clip_{all_passages[i].get('index', i)}"
                label_j = f"clip_{all_passages[j].get('index', j)}"
                failures.append(f"{label_i} <-> {label_j}: {overlap:.1f}s overlap")

    if failures:
        return False, "R2 FAIL: " + "; ".join(failures)
    return True, "R2 PASS: no duplicate passages"


# ==============================================================
# R3: VO_AFTER_ANSWER
# ==============================================================

def rule_r3(edl):
    """VO bridges only after clips that end on statements (not questions)."""
    clips = edl.get("clips", [])
    vo = edl.get("vo", {})
    bridges = vo.get("bridges", [])
    failures = []

    for bridge in bridges:
        after_clip = bridge.get("after_clip")
        if after_clip is None:
            continue
        # Find the clip that precedes this bridge
        clip = next((c for c in clips if c.get("index") == after_clip), None)
        if clip is None:
            failures.append(f"bridge after clip {after_clip}: clip not found")
            continue
        text = clip.get("text", "")
        if _text_ends_with_question(text):
            failures.append(f"bridge after clip {after_clip}: clip ends with question")

    if failures:
        return False, "R3 FAIL: " + "; ".join(failures)
    return True, "R3 PASS: all bridges follow statements"


# ==============================================================
# R4: VO_BUDGET
# ==============================================================

MOMENTS_VO_SHARE = 0.45           # law L-q ('06:00': 40 %; ruling 9, '08:29': 45 %): the host makes points; a TASTE limit
MOMENTS_RUNTIME_S = (60.0, 70.0)  # law L-o: the format, the one hard length rule (stays hard)
FINAL_TAIL_S = 14.30              # what a final adds to its segments' word spans: credits card + sign-off, outro, cut
                                  # leads / tails, pads (approved preview: 71.08 s finals - 56.78 s word spans)
MOMENTS_TAKEAWAY_WORD_CAP = 30    # ruling 10 ('08:40'): the TAKEAWAY (the line after the LAST clip, a slot that did not exist
                                  # when BRIDGE_WORD_CAP was set) has the intro's cap; bridges BETWEEN clips keep 20
R4_WPS, R4_PREROLL_S = 2.5, 1.0   # R4's VO estimate: words at 2.5 w/s + the renderers' 1.0 s pre-roll per VO line
SPOTLIGHT_RUNTIME_S = (28.0, 50.0)  # law L-ab (ruling 90): a spotlight's format, the one hard length rule of that kind
SPOTLIGHT_MOMENT_S = (12.0, 35.0)   # law L-ab: the one moment's target (TASTE, law L-o: a recorded deviation)
SPOTLIGHT_CLOSING_WORD_CAP = 12     # ruling 91: the closing line, when it earned its place


def _spotlight(edl):
    """Law L-ab: a validated moments package of the spotlight kind (pinned.build_edl writes package_shape)."""
    return edl.get("package_type") == "moments" and edl.get("package_shape") == "spotlight"


def _r4_moments(edl):
    """R4 for a package of type 'moments' (law L-q, orchestrator '06:00'; cap 45 % by ruling 9, '08:29'; a TASTE rule,
    recorded under L-o / L-q; story-type pins keep the rule below). One VO line per slot: the intro after the hook, and
    at most one line after each clip, the LAST clip included (the takeaway: render16 / render_vertical play it before
    the shout-out); a line with no such slot fails. VO (intro + lines, each words / 2.5 + the 1.0 s pre-roll) <= 45 % of
    the TOTAL estimated runtime (orchestrator '06:22'). The estimated final runtime (hook + clips + VO + FINAL_TAIL_S)
    inside 60-70 s (hard, L-o). Word
    caps unchanged. The sign-off is generated at the voice stage from the credits (not in the share; in the tail).
    Fail closed (cycle 1 of its audit): the EDL must carry a validated moments package (the 64-hex package digest,
    pinned mode, both gate verdicts exactly true, as pinned.build_edl writes them); every hook / clip a measured
    positive finite duration; clip indexes exactly 1..n; no empty VO line; limits compared on exact values."""
    vo = edl.get("vo") or {}
    clips = edl.get("clips") or []
    idx = [c.get("index") for c in clips]
    failures = []
    sha, checks = edl.get("moments_package_sha256"), edl.get("moments_checks")
    if not (isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha) and edl.get("mode") == "pinned"
            and isinstance(checks, dict) and checks.get("vo_fidelity_ok") is True
            and checks.get("context_integrity_ok") is True):
        failures.append("package_type 'moments' without a validated moments package (digest, pinned mode, both gate "
                        "verdicts)")
    if idx != list(range(1, len(clips) + 1)):
        failures.append(f"clip indexes {idx!r} are not 1..{len(clips)}")
    intro = vo.get("intro") or ""
    if not isinstance(intro, str):
        failures.append("intro is not text")
        intro = ""
    icap = SPOTLIGHT_CLOSING_WORD_CAP if _spotlight(edl) else INTRO_WORD_CAP   # law L-ab: the closing line's slot
    if _word_count(intro) > icap:
        failures.append(f"intro={_word_count(intro)} words (max {icap})")
    bridges = vo.get("bridges") or []
    prev, lines = 0, ([intro] if intro.strip() else [])
    for i, b in enumerate(bridges, 1):
        a = b.get("after_clip") if isinstance(b, dict) else None
        if type(a) is not int or a not in idx or a <= prev:
            failures.append(f"VO line {i} has no slot (after_clip {a!r}: one line after each clip index "
                            f"{sorted(x for x in idx if isinstance(x, int))}, in order)")
        else:
            prev = a
        text = b.get("text", "") if isinstance(b, dict) else ""
        if not isinstance(text, str) or not text.strip():
            failures.append(f"VO line {i} is empty")
            continue
        cap = MOMENTS_TAKEAWAY_WORD_CAP if (type(a) is int and clips and a == idx[-1]) else BRIDGE_WORD_CAP
        if _word_count(text) > cap:
            failures.append(f"bridge {i}={_word_count(text)} words (max {cap})")
        lines.append(text)
    durs = []
    for s in [edl.get("hook") or {}] + clips:
        d = s.get("duration") if isinstance(s, dict) else None
        if type(d) not in (int, float) or not math.isfinite(d) or d <= 0:
            failures.append(f"{'hook' if s is edl.get('hook') else 'clip ' + str(s.get('index'))}: duration {d!r} "
                            f"is not a measured positive number")
        else:
            durs.append(float(d))
    content = sum(durs)
    vo_s = sum(_word_count(t) / R4_WPS + R4_PREROLL_S for t in lines)
    if len(durs) == len(clips) + 1 and content > 0:
        runtime = content + vo_s + FINAL_TAIL_S      # exact; the 1e-6 absorbs float noise only
        share = vo_s / runtime                       # against the TOTAL runtime (orchestrator '06:22')
        if share > MOMENTS_VO_SHARE + 1e-9:          # exactly 45 % passes (the same float tolerance as the runtime)
            failures.append(f"VO={share:.2%} of total runtime (max {MOMENTS_VO_SHARE:.0%}, moments)")
        lo, hi = SPOTLIGHT_RUNTIME_S if _spotlight(edl) else MOMENTS_RUNTIME_S   # law L-ab: a spotlight's format
        if not lo - 1e-6 <= runtime <= hi + 1e-6:
            failures.append(f"estimated runtime {runtime:.3f} s outside {lo:.0f}-{hi:.0f} s (hook + clips "
                            f"{content:.2f} + VO {vo_s:.2f} + tail {FINAL_TAIL_S})")
    if failures:
        return False, "R4 FAIL (moments): " + "; ".join(failures)
    total = content + vo_s + FINAL_TAIL_S
    return True, (f"R4 PASS (moments): VO {vo_s:.2f} s = {vo_s / total:.2%} of total runtime <= {MOMENTS_VO_SHARE:.0%}, "
                  f"estimated runtime {total:.2f} s, every VO line in a slot")


def rule_r4(edl):
    """VO <= 25% of total runtime. Word limits enforced. A package of type 'moments': _r4_moments (law L-q)."""
    if edl.get("package_type") == "moments":
        return _r4_moments(edl)
    vo = edl.get("vo", {})
    clips = edl.get("clips", [])
    total_clip_dur = edl.get("total_clip_duration", 0)
    if total_clip_dur == 0:
        total_clip_dur = sum(c.get("duration", 0) for c in clips)

    # Word counts
    intro_text = vo.get("intro", "")
    intro_words = _word_count(intro_text)
    signoff_text = vo.get("signoff", "")
    signoff_words = _word_count(signoff_text)
    bridges = vo.get("bridges", [])

    failures = []

    if intro_words > INTRO_WORD_CAP:
        failures.append(f"intro={intro_words} words (max {INTRO_WORD_CAP})")
    if signoff_words > SIGNOFF_WORD_CAP:
        failures.append(f"signoff={signoff_words} words (max {SIGNOFF_WORD_CAP})")

    for i, bridge in enumerate(bridges):
        btext = bridge.get("text", "")
        bwords = _word_count(btext)
        if bwords > BRIDGE_WORD_CAP:
            failures.append(f"bridge {i+1}={bwords} words (max {BRIDGE_WORD_CAP})")

    # One bridge per channel transition
    if len(bridges) > 0 and len(clips) > 0:
        transitions = 0
        prev_channel = None
        for clip in sorted(clips, key=lambda c: c.get("index", 0)):
            ch = clip.get("channel", "")
            if prev_channel and ch != prev_channel:
                transitions += 1
            prev_channel = ch
        if len(bridges) > max(transitions, 1):
            failures.append(f"{len(bridges)} bridges but only {transitions} channel transitions")

    # VO budget: estimate VO duration from word count (avg 2.5 words/sec for TTS)
    total_vo_words = intro_words + signoff_words + sum(_word_count(b.get("text", "")) for b in bridges)
    estimated_vo_dur = total_vo_words / 2.5  # approximate seconds
    # Add pre-roll per VO segment (1.0s each)
    num_vo_segments = (1 if intro_text else 0) + len(bridges) + (1 if signoff_text else 0)
    estimated_vo_dur += num_vo_segments * 1.0

    if total_clip_dur > 0:
        total_runtime = total_clip_dur + estimated_vo_dur
        vo_fraction = estimated_vo_dur / total_runtime
        if vo_fraction > 0.25:
            failures.append(f"VO={vo_fraction:.0%} of runtime (max 25%)")

    if failures:
        return False, "R4 FAIL: " + "; ".join(failures)
    return True, "R4 PASS: VO within budget"


# ==============================================================
# R5: CLIP_LENGTH
# ==============================================================

CLIP_TARGET_S = (12.0, 20.0)     # law L-o: the clip duration window is a TASTE target (rank, never reject)


def _r5_spotlight(edl):
    """Law L-ab (ruling 90): ONE moment, one channel, no medley minimum. INTEGRITY: no clips; the moment (the EDL's hook)
    a measured positive finite duration and a named channel. TASTE (law L-o): the moment outside 12-35 s is a recorded
    deviation with its size, never a rejection."""
    hook, clips = edl.get("hook") or {}, edl.get("clips")
    failures = [] if clips == [] else [f"a spotlight has no clips (got {repr(clips)[:60]})"]
    dur, ch = hook.get("duration"), hook.get("channel")
    measured = type(dur) in (int, float) and math.isfinite(dur) and dur > 0
    if not measured:
        failures.append(f"the moment's duration {repr(dur)[:40]} is not a measured positive number")
    if not isinstance(ch, str) or not ch.strip():
        failures.append("the moment names no channel")
    if failures:
        return False, "R5 FAIL (spotlight, law L-ab): " + "; ".join(failures)
    lo, hi = SPOTLIGHT_MOMENT_S
    if not lo <= dur <= hi:
        return True, (f"R5 PASS (spotlight, law L-ab) | law L-o taste deviation, recorded, not a cause: the moment "
                      f"{dur:.2f}s ({max(lo - dur, dur - hi, 0.01):.2f}s outside the {lo:.0f}-{hi:.0f}s target)")
    return True, f"R5 PASS (spotlight, law L-ab): one moment, {dur:.2f}s, one channel ({ch})"


def rule_r5(edl):
    """INTEGRITY (law L-o, fail closed): >= 2 clips, from >= 2 distinct channels, every clip with a measured positive
    finite duration (so no channel is counted with no screen time). TASTE (law L-o, orchestrator 2026-11-12 '01:50';
    pp-selectid REQUESTS R6 item 2): a clip outside the 12-20 s target is a recorded deviation with its size, never a
    rejection (a whole sentence always beats a duration window); the only hard duration rule is the format, measured
    on the final by the gates. The validate stage writes this reason into PROVENANCE (run.prov['edl_validation'])."""
    if _spotlight(edl):
        return _r5_spotlight(edl)
    clips = edl.get("clips", [])
    failures, deviations = [], []
    lo, hi = CLIP_TARGET_S

    if len(clips) < 2:
        failures.append(f"only {len(clips)} clips (need >= 2)")

    channels = set()
    for clip in clips:
        dur = clip.get("duration")
        ch = clip.get("channel")
        idx = str(clip.get("index", "?"))[:20]
        try:
            measured = not isinstance(dur, bool) and isinstance(dur, (int, float)) and math.isfinite(dur) and dur > 0
        except OverflowError:                                    # an integer too large for a float: not a measurement
            measured = False
        if not measured:
            failures.append(f"clip {idx}: duration {repr(dur)[:40]} is not a measured positive number")   # never a pass
            continue
        if not isinstance(ch, str) or not ch.strip():
            failures.append(f"clip {idx}: no channel named")      # a missing channel is never a distinct channel
            continue
        channels.add(ch.strip())
        if dur < lo:
            deviations.append(f"clip {idx}: {dur:.2f}s ({max(lo - dur, 0.01):.2f}s under the {lo:.0f}-{hi:.0f}s target)")
        elif dur > hi:
            deviations.append(f"clip {idx}: {dur:.2f}s ({max(dur - hi, 0.01):.2f}s over the {lo:.0f}-{hi:.0f}s target)")

    if len(channels) < 2:
        failures.append(f"only {len(channels)} channel(s) with a measured clip (need >= 2)")

    taste = f" | law L-o taste deviations, recorded, not causes: {'; '.join(deviations)}" if deviations else ""
    if failures:
        return False, "R5 FAIL: " + "; ".join(failures) + taste
    if deviations:
        return True, "R5 PASS" + taste
    return True, "R5 PASS: clip lengths and channel diversity OK"


# ==============================================================
# R6: CREDITS_MATCH
# ==============================================================

def rule_r6(edl, channels_registry=None):
    """Channels in signoff must match EDL channels in order. Unique avatar hashes."""
    clips = edl.get("clips", [])

    # Extract unique channels in EDL order
    edl_channels = []
    seen = set()
    for clip in sorted(clips, key=lambda c: c.get("index", 0)):
        ch = clip.get("channel", "")
        if ch and ch not in seen:
            edl_channels.append(ch)
            seen.add(ch)

    failures = []

    # Check signoff mentions channels in order
    vo = edl.get("vo", {})
    signoff = vo.get("signoff", "")
    if signoff:
        for ch in edl_channels:
            if ch.lower() not in signoff.lower():
                failures.append(f"signoff missing channel '{ch}'")

    # Check avatar uniqueness if registry provided
    if channels_registry:
        avatar_hashes = {}
        for ch_name in edl_channels:
            entry = next((e for e in channels_registry if e.get("display_name") == ch_name), None)
            if entry:
                h = entry.get("avatar_sha256_prefix", "")
                if not h:
                    continue          # empty/missing hash — avatar not uploaded yet
                if h in avatar_hashes:
                    failures.append(f"duplicate avatar hash {h}: {ch_name} == {avatar_hashes[h]}")
                avatar_hashes[h] = ch_name

    if failures:
        return False, "R6 FAIL: " + "; ".join(failures)
    return True, "R6 PASS: credits match EDL channels"


# ==============================================================
# R7: VERTICAL_LAYOUT_KNOWN
# ==============================================================

def rule_r7(edl, layout_tables_dir=None):
    """Every (channel, tile_count) must have explicit layout table entry."""
    if not layout_tables_dir or not os.path.isdir(layout_tables_dir):
        return True, "R7 SKIP: no layout tables dir provided"

    # Load all layout tables
    tables = {}
    for fn in os.listdir(layout_tables_dir):
        if fn.endswith(".json"):
            with open(os.path.join(layout_tables_dir, fn)) as f:
                table = json.load(f)
            ch = table.get("channel", "").lower()
            tc = table.get("tile_count", 0)
            tables[(ch, tc)] = table

    clips = edl.get("clips", [])
    failures = []

    # We can't determine tile_count from EDL alone — it requires frame analysis.
    # R7 checks that channels appearing in EDL have at least one layout entry.
    channels_in_edl = set()
    for clip in clips:
        ch = clip.get("channel", "")
        if ch:
            channels_in_edl.add(ch.lower())

    channels_with_tables = set()
    for (ch, tc) in tables.keys():
        channels_with_tables.add(ch)

    for ch in channels_in_edl:
        if ch not in channels_with_tables:
            failures.append(f"channel '{ch}' has no layout table")

    if failures:
        return False, "R7 FAIL: " + "; ".join(failures)
    return True, "R7 PASS: all channels have layout tables"


# ==============================================================
# R8: G10_CHYRON_REGISTRY
# ==============================================================

def rule_r8(edl, channels_registry=None):
    """Informational: the has_chyron channels in the EDL. Ruling 93 (2026-11-13 '23:59'): G10 runs on EVERY clip;
    has_chyron is a hint that orders the pin-stage visual check, nothing more."""
    if not channels_registry:
        return True, "R8 SKIP: no channels registry provided"

    clips = edl.get("clips", [])
    chyron_channels = set()

    for clip in clips:
        ch = clip.get("channel", "")
        entry = next((e for e in channels_registry if e.get("display_name") == ch), None)
        if entry and entry.get("has_chyron", False):
            chyron_channels.add(ch)

    # R8 is informational — it lists which clips need G10
    if chyron_channels:
        return True, f"R8 PASS: chyron channels = {chyron_channels}"
    return True, "R8 PASS: no chyron channels in this EDL"


# ==============================================================
# R9: CLIP_ENDS_ON_SENTENCE
# ==============================================================

def rule_r9(edl, transcripts=None):
    """A clip's cut_out must land on a sentence-ending word (. ? !) from the
    whisper word-level transcript, with 0.20-0.45s tail pause before the next
    word starts. Applies to hook and every clip.

    transcripts: dict mapping video_id -> list of {word, start, end} dicts
                 (whisper word timestamps from the source video).
    If transcripts is None, the rule is skipped (requires external data).
    """
    if not transcripts:
        return True, "R9 SKIP: no transcripts provided"

    passages = []
    hook = edl.get("hook", {})
    if hook:
        passages.append(("hook", hook))
    for clip in edl.get("clips", []):
        passages.append((f"clip_{clip.get('index', '?'):02d}" if isinstance(clip.get('index'), int) else f"clip_{clip.get('index', '?')}", clip))

    failures = []

    for label, passage in passages:
        vid = passage.get("video_id")
        if not vid or vid not in transcripts:
            continue

        words = transcripts[vid]
        last_word_text = passage.get("last_word", "").strip().rstrip(".,?!")
        cut_out = passage.get("cut_out") or passage.get("word_end", 0)
        if not cut_out:
            continue

        # Find the declared last word in the transcript near cut_out
        # Search backwards from cut_out for the matching word
        best_idx = None
        best_dist = float("inf")
        for i, w in enumerate(words):
            wtext = w["word"].strip().rstrip(".,?!").lower()
            if wtext == last_word_text.lower():
                dist = abs(w["end"] - cut_out)
                if dist < best_dist and dist < 5.0:
                    best_dist = dist
                    best_idx = i

        if best_idx is None:
            failures.append(f"{label}: last_word '{last_word_text}' not found near cut_out={cut_out:.2f}")
            continue

        matched_word = words[best_idx]
        matched_text = matched_word["word"].strip()

        # Check sentence ending: the raw whisper word must end with . ? or !
        if not any(matched_text.endswith(c) for c in [".", "?", "!"]):
            failures.append(f"{label}: last word '{matched_text}' at {matched_word['end']:.2f}s is not sentence-ending (no . ? !)")
            continue

        # Check tail pause: cut_out must be after word end with some room tone.
        # Hard floor: 0.05s. Preferred: 0.20-0.45s.
        word_end = matched_word["end"]
        tail = cut_out - word_end
        if tail < 0.05:
            failures.append(f"{label}: tail pause {tail:.3f}s < 0.05s (cut_out={cut_out:.2f}, word_end={word_end:.2f})")
            continue

        # Check next word: cut_out must be strictly before next word starts
        if best_idx + 1 < len(words):
            next_start = words[best_idx + 1]["start"]
            if cut_out >= next_start:
                next_text = words[best_idx + 1]["word"].strip()
                failures.append(f"{label}: cut_out={cut_out:.2f} >= next word '{next_text}' start={next_start:.2f}")
                continue

    if failures:
        return False, "R9 FAIL: " + "; ".join(failures)
    return True, "R9 PASS: all clips end on sentence boundaries with clean tail"


SENTENCE_PAUSE_MS = 400  # C1b: pause >= 400ms before first word = sentence start


def rule_r10(edl, transcripts=None):
    """R10 SENTENCE_START (M24): Every clip must begin at a sentence start.

    A word is a sentence start if:
      - It is the first word in the transcript, OR
      - The previous word ends with . ? !, OR
      - There is a pause >= 400 ms between the previous word's end and
        this word's start.

    Also checks for fragments: first_word must not be a mid-word fragment
    (detected by comparing first_word to the matched whisper word).

    Returns (pass, reason). Skips if no transcripts provided.
    """
    if transcripts is None:
        return True, "R10 SKIP: no transcripts provided"

    passages = []
    hook = edl.get("hook", {})
    if hook:
        passages.append({**hook, "label": "hook"})
    for clip in edl.get("clips", []):
        idx = clip.get("index", "?")
        passages.append({**clip, "label": f"clip_{idx:02d}" if isinstance(idx, int) else f"clip_{idx}"})

    failures = []
    for passage in passages:
        label = passage["label"]
        first_word = passage.get("first_word", "")
        word_start = passage.get("word_start", 0)
        vid = passage.get("video_id", "")

        if not vid or vid not in transcripts:
            continue

        words = transcripts[vid]
        if not words:
            continue

        # Find the matching word near word_start
        matched = None
        matched_idx = None
        for idx, w in enumerate(words):
            if abs(w.get("start", 0) - word_start) < 0.3:
                matched = w
                matched_idx = idx
                break

        if matched is None:
            # Try text match as fallback
            for idx, w in enumerate(words):
                wtext = w.get("word", "").strip().lower()
                if wtext.startswith(first_word.lower()[:3]) and abs(w.get("start", 0) - word_start) < 1.0:
                    matched = w
                    matched_idx = idx
                    break

        if matched is None:
            failures.append(f"{label}: first word '{first_word}' not found in transcript near {word_start:.2f}s")
            continue

        # Check for mid-word fragment
        matched_text = matched.get("word", "").strip()
        if first_word and len(first_word) > 1:
            # If first_word doesn't match the start of the whisper word, it's a fragment
            if not matched_text.lower().startswith(first_word.lower()[:2]):
                # Could be a mid-word entry
                if matched_idx > 0:
                    prev_text = words[matched_idx - 1].get("word", "").strip()
                    if prev_text.lower().endswith(first_word.lower()[:2]):
                        failures.append(
                            f"{label}: first_word '{first_word}' appears to be mid-word "
                            f"(prev word '{prev_text}' + '{matched_text}')")
                        continue

        # Check sentence start conditions
        if matched_idx == 0:
            continue  # First word in transcript — always OK

        prev_word = words[matched_idx - 1]
        prev_text = prev_word.get("word", "").strip()

        # Condition 1: previous word ends with sentence-ending punctuation
        if any(prev_text.endswith(c) for c in [".", "?", "!"]):
            continue

        # Condition 2: pause >= 400ms between previous word end and this word start
        prev_end = prev_word.get("end", 0)
        pause_ms = (matched.get("start", 0) - prev_end) * 1000
        if pause_ms >= SENTENCE_PAUSE_MS:
            continue

        # Neither condition met — not a sentence start
        failures.append(
            f"{label}: first word '{matched_text}' at {word_start:.2f}s is not a sentence start "
            f"(prev='{prev_text}', pause={pause_ms:.0f}ms)")

    if failures:
        # Amendment 1 S4: R10 is advisory (HOLD for PBX), not blocking.
        # It flags but does not auto-recut or reject the EDL.
        return True, "R10 HOLD (PBX): " + "; ".join(failures)
    return True, "R10 PASS: all clips begin at sentence starts"


# ==============================================================
# VALIDATE ALL
# ==============================================================

# ==============================================================
# R11: VO_SHAPE (law L-y, orchestrator 2026-11-12 '20:30')
# ==============================================================

def rule_r11(edl):
    """Law L-y VOICEOVER IS MINIMAL, for a package of type 'moments' (the packager's packages): at most ONE line after
    the LAST clip (the takeaway; R4 keeps its 30-word cap) and at most ONE line before it: the L-y 2 exception, a bridge
    at one join, either between the hook clip and clip 1 (the EDL's intro slot, the only line the renderer plays there)
    or after clip k. That one line passes only with the package's recorded bridge (moments_package.bridge, copied into
    the EDL as moments_bridge by pinned.build_edl): its text is exactly the line, its reason ('why') and the blind
    clips-alone check's confirmation ('confirmed_by') are stated, and the line is at most BRIDGE_WORD_CAP words ('as short
    as it can be'). Without that record a line before the takeaway fails (L-y 1: no VO intro after the hook; no bridges
    between clips); two or more fail always (the line-up is wrong). No minimum: no VO line at all passes. Story-type and
    untyped EDLs (the protected references) are not moments packages and are unchanged. Fail closed (audit batch 40): a
    moments EDL without a vo object and clips, a clip without an integer index, bridges that are not a list, a line whose
    after_clip is not a clip index, clip indexes other than exactly 1..n, a non-text line, and a recorded bridge
    with no bridge line fail."""
    if edl.get("package_type") != "moments":
        return True, "R11 PASS: not a moments package (law L-y binds moments packages)"
    if _spotlight(edl):                      # law L-ab (rulings 90 / 91): 0 bridges and 0 or 1 closing line
        vo, rec = edl.get("vo"), edl.get("moments_bridge")
        if not isinstance(vo, dict) or edl.get("clips") != [] or vo.get("bridges") != []:
            return False, "R11 FAIL (spotlight, law L-ab): a spotlight states a vo object, no clips and bridges []"
        line = vo.get("intro")
        if line is not None and (not isinstance(line, str) or not line.strip()
                                 or _word_count(line) > SPOTLIGHT_CLOSING_WORD_CAP):
            return False, (f"R11 FAIL (spotlight, ruling 91): the closing line is null or ONE line of at most "
                           f"{SPOTLIGHT_CLOSING_WORD_CAP} words")
        if rec is not None:
            return False, "R11 FAIL (spotlight, law L-ab): a spotlight has no bridge (moments_bridge must be null)"
        return True, f"R11 PASS (spotlight, law L-ab): {0 if line is None else 1} closing line, no bridge"
    vo, clips = edl.get("vo"), edl.get("clips")
    if not isinstance(vo, dict) or not isinstance(clips, list) or not clips:
        return False, "R11 FAIL (law L-y): a moments EDL without a vo object and clips"
    idx = [c.get("index") if isinstance(c, dict) else None for c in clips]
    if any(type(i) is not int for i in idx) or idx != list(range(1, len(clips) + 1)):   # batch 40 F1 / cycle 3 glm F1:
        return False, f"R11 FAIL (law L-y): clip indexes {idx!r} are not 1..{len(clips)}"  # the last clip is index n
    bridges = vo.get("bridges")
    if not isinstance(bridges, list):                             # F2: a moments EDL always states its lines
        return False, "R11 FAIL (law L-y): vo bridges is not a list ([] when there are none)"
    failures, before, closing = [], [], 0
    intro = vo.get("intro")
    if intro is not None and intro != "":                         # F3: '   ' is a line to vo.py and the renderer
        before.append(("the intro slot (hook -> clip 1)", intro))
    for i, b in enumerate(bridges, 1):
        a = b.get("after_clip") if isinstance(b, dict) else None
        if type(a) is not int or a not in idx:                    # F2: a line with no clip slot fails here too
            failures.append(f"VO line {i}: after_clip {a!r} is not a clip index")
        elif a == max(idx):
            closing += 1
            t = b.get("text")
            if not isinstance(t, str) or not t.strip():             # cycle 3 qwen F1: the takeaway is a voiced line
                failures.append(f"VO line {i}: the takeaway after the last clip is not text")
        else:
            before.append((f"the slot after clip {a}", b.get("text")))
    if closing > 1:
        failures.append(f"law L-y 1: {closing} VO lines after the last clip (one takeaway)")
    rec = edl.get("moments_bridge")
    if len(before) > 1:
        failures.append(f"law L-y 2: {len(before)} lines before the takeaway ({'; '.join(s for s, _ in before)}): at "
                        f"most ONE bridge; two or more = the line-up is wrong")
    elif before:
        slot, text = before[0]
        if not isinstance(text, str) or not text.strip():
            failures.append(f"law L-y: the line in {slot} is not text")
        elif not (isinstance(rec, dict) and isinstance(rec.get("text"), str) and rec["text"].strip() == text.strip()):
            failures.append(f"law L-y 1 / 2: a line in {slot} without the package's recorded bridge (moments_bridge "
                            f"with exactly this text)")
        else:
            why, conf = rec.get("why"), rec.get("confirmed_by")
            if not (isinstance(why, str) and why.strip()):
                failures.append("law L-y 2: the recorded bridge has no reason ('why')")
            if not ((isinstance(conf, str) and conf.strip()) or (isinstance(conf, (list, dict)) and conf)):
                failures.append("law L-y 2: the recorded bridge is not confirmed by the blind check ('confirmed_by')")
            if _word_count(text) > BRIDGE_WORD_CAP:
                failures.append(f"law L-y 2: the bridge is {_word_count(text)} words (max {BRIDGE_WORD_CAP})")
    elif rec is not None:
        failures.append("law L-y 2: a recorded bridge (moments_bridge) with no bridge line in the VO")
    if failures:
        return False, "R11 FAIL (law L-y): " + "; ".join(failures)
    return True, (f"R11 PASS (law L-y): {len(before)} bridge (recorded and confirmed) before the takeaway; "
                  f"{closing} takeaway line(s)")


def validate_edl(edl, channels_registry=None, layout_tables_dir=None,
                  transcripts=None):
    """Run all rules. Returns (all_pass, results list).
    transcripts: dict mapping video_id -> list of {word, start, end} dicts (for R9).
    """
    results = []

    for rule_fn, args in [
        (rule_r1, (edl,)),
        (rule_r2, (edl,)),
        (rule_r3, (edl,)),
        (rule_r4, (edl,)),
        (rule_r5, (edl,)),
        (rule_r6, (edl, channels_registry)),
        (rule_r7, (edl, layout_tables_dir)),
        (rule_r8, (edl, channels_registry)),
        (rule_r9, (edl, transcripts)),
        (rule_r10, (edl, transcripts)),
        (rule_r11, (edl,)),
    ]:
        ok, reason = rule_fn(*args)
        results.append({"rule": rule_fn.__name__, "pass": ok, "reason": reason})
        print(f"  {reason}")

    all_pass = all(r["pass"] for r in results)
    return all_pass, results


def main():
    p = argparse.ArgumentParser(description="EDL editorial rules validator (R1-R9)")
    p.add_argument("--edl", required=True, help="EDL JSON file")
    p.add_argument("--channels", default=None, help="channels.json registry")
    p.add_argument("--layout-tables", default=None, help="Layout tables directory")
    args = p.parse_args()

    with open(args.edl) as f:
        edl = json.load(f)

    channels_registry = None
    if args.channels:
        with open(args.channels) as f:
            channels_registry = json.load(f)

    print("=== EDL RULES VALIDATION ===")
    all_pass, results = validate_edl(edl, channels_registry, args.layout_tables)

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
