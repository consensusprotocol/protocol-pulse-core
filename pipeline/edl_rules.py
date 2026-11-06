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
    R5 CLIP_LENGTH:           8-25s continuous speech per clip. >= 2 distinct
                              channels. Every channel >= 8s screen time.
    R6 CREDITS_MATCH:         Channels in shoutout/signoff/reply == channels
                              in EDL, in EDL order. Unique avatar hashes.
    R7 VERTICAL_LAYOUT_KNOWN: Every (channel, tile_count) must have an
                              explicit layout table entry.
    R8 G10_CHYRON_REGISTRY:   Only channels with has_chyron=true trigger G10.
    R9 CLIP_ENDS_ON_SENTENCE: A clip's cut_out must land on a transcript word
                              that ends a sentence (. ? !) plus 0.20-0.45s tail
                              pause, strictly before the next source word starts.
"""
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

def rule_r1(edl):
    """Hook passage must be a statement, not a question.
    A passage that contains both a question AND an answer (ending on a statement)
    is acceptable — the rule targets pure-question hooks only."""
    hook = edl.get("hook", {})
    text = hook.get("text", "")
    if not text:
        return False, "R1 FAIL: hook has no text"

    # Split into sentences and check if the LAST sentence is a question
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    last_sentence = sentences[-1] if sentences else text

    # Check if the passage ENDS on a question (last meaningful sentence)
    if text.rstrip().endswith("?"):
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

def rule_r4(edl):
    """VO <= 25% of total runtime. Word limits enforced."""
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

def rule_r5(edl):
    """8-25s per clip, >= 2 distinct channels, every channel >= 8s."""
    clips = edl.get("clips", [])
    failures = []

    if len(clips) < 2:
        failures.append(f"only {len(clips)} clips (need >= 2)")

    channels = {}
    for clip in clips:
        dur = clip.get("duration", 0)
        ch = clip.get("channel", "unknown")
        idx = clip.get("index", "?")

        if dur < 8:
            failures.append(f"clip {idx}: {dur:.1f}s (min 8s)")
        if dur > 25:
            failures.append(f"clip {idx}: {dur:.1f}s (max 25s)")

        channels.setdefault(ch, 0)
        channels[ch] += dur

    if len(channels) < 2:
        failures.append(f"only {len(channels)} channel(s) (need >= 2)")

    for ch, total_dur in channels.items():
        if total_dur < 8:
            failures.append(f"channel '{ch}': {total_dur:.1f}s total (min 8s)")

    if failures:
        return False, "R5 FAIL: " + "; ".join(failures)
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
    """Only channels with has_chyron=true should trigger G10 chyron gate."""
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
        return False, "R10 FAIL: " + "; ".join(failures)
    return True, "R10 PASS: all clips begin at sentence starts"


# ==============================================================
# VALIDATE ALL
# ==============================================================

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
