#!/usr/bin/env python3
"""Stage 2a-c: Build candidate passages, select EDL, pick hook, write VO script.
Runs incrementally — processes whatever transcripts exist."""
import json, os, re, sys

TRANSCRIPTS_DIR = "/home/ultron/protocol_pulse/segment_v1/transcripts"
BASE = "/home/ultron/protocol_pulse/segment_v1"

VIDEO_META = {
    "bSmFGoAKPBc": {"channel": "Simply Bitcoin", "handle": "@SimplyBitcoin",
                     "title": "Why Bitcoin Is Holding Strong After a $6.3B Hack?",
                     "url": "https://www.youtube.com/watch?v=bSmFGoAKPBc"},
    "5ripuS9GDaM": {"channel": "Simply Bitcoin", "handle": "@SimplyBitcoin",
                     "title": "Was The $6.3B Binance Heist an Inside Job?",
                     "url": "https://www.youtube.com/watch?v=5ripuS9GDaM"},
    "Eojd18J_wuU": {"channel": "BTC Sessions", "handle": "@BTCSessions",
                     "title": "Binance Just Proved Why Self-Custody Matters",
                     "url": "https://www.youtube.com/watch?v=Eojd18J_wuU"},
    "7QIB_zdKU9A": {"channel": "CoinDesk", "handle": "@CoinDesk",
                     "title": "Bitcoin ETFs Hit by $643M Selloff as Binance Hack Shakes Crypto",
                     "url": "https://www.youtube.com/watch?v=7QIB_zdKU9A"},
}

TOPIC_KW = [
    "binance", "hack", "hacker", "hacked", "stolen", "theft", "heist",
    "self-custody", "self custody", "not your keys", "not your coins",
    "cold storage", "hardware wallet", "custodial", "exchange",
    "6.3 billion", "6.3b", "$6.3", "billion",
    "security", "breach", "exploit", "withdraw", "frozen", "freeze",
]

FILLER_STARTS = {"and", "but", "so", "because", "which", "that's", "since",
                 "meaning", "like", "well", "you know", "um", "uh"}
DANGLING_PRONOUNS = {"he", "she", "they", "them", "him", "her"}


def build_sentences(transcript):
    """Group words into sentence-like spans using segment boundaries and punctuation."""
    words = transcript["words"]
    segments = transcript["segments"]
    if not words or not segments:
        return []

    sentences = []
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        # Find words belonging to this segment
        seg_words = [w for w in words
                     if w["start"] >= seg["start"] - 0.3
                     and w["end"] <= seg["end"] + 0.3]
        if not seg_words:
            continue
        sentences.append({
            "text": text,
            "start": seg["start"],
            "end": seg["end"],
            "word_start": seg_words[0]["start"],
            "word_end": seg_words[-1]["end"],
            "first_word": seg_words[0]["word"].strip(),
            "last_word": seg_words[-1]["word"].strip(),
            "words": seg_words,
            "duration": seg["end"] - seg["start"],
        })
    return sentences


def score_passage(text, duration, first_word):
    """Score a candidate passage for medley suitability."""
    tl = text.lower()
    score = 0

    # Topic relevance
    hits = sum(1 for kw in TOPIC_KW if kw in tl)
    score += hits * 8

    # Specificity: numbers, dollar amounts, percentages
    nums = re.findall(r'\$[\d,.]+[BMK]?|\d+[\d,.]*\s*(?:billion|million|percent|%|thousand)', tl)
    score += len(nums) * 12

    # Named entities (specific claims)
    names = re.findall(r'(?:Binance|Tether|Circle|CZ|Changpeng|Zhao|Ledger|Trezor|SafePal|ETF|Bitcoin|Bybit)', text, re.I)
    score += min(len(set(n.lower() for n in names)), 4) * 5

    # Duration sweet spot: 10-20s ideal
    if 10 <= duration <= 20:
        score += 12
    elif 8 <= duration <= 25:
        score += 5
    else:
        score -= 10

    # Self-containment penalties
    fw = first_word.lower().strip()
    if fw in FILLER_STARTS:
        score -= 12
    if fw in DANGLING_PRONOUNS:
        score -= 8

    # Ends with strong punctuation
    if text.rstrip().endswith(('.', '!', '?')):
        score += 3

    return score, hits


def find_candidates(transcript, vid_id):
    """Find 8-25s on-topic passages."""
    sentences = build_sentences(transcript)
    candidates = []

    # Single sentences
    for s in sentences:
        if s["duration"] < 6 or s["duration"] > 28:
            continue
        score, hits = score_passage(s["text"], s["duration"], s["first_word"])
        if hits == 0:
            continue
        candidates.append({
            "video_id": vid_id,
            "channel": VIDEO_META[vid_id]["channel"],
            "handle": VIDEO_META[vid_id]["handle"],
            "video_title": VIDEO_META[vid_id]["title"],
            "text": s["text"],
            "start": s["start"],
            "end": s["end"],
            "duration": round(s["duration"], 2),
            "first_word": s["first_word"],
            "last_word": s["last_word"],
            "word_start": s["word_start"],
            "word_end": s["word_end"],
            "score": score,
            "topic_hits": hits,
            "span": 1,
        })

    # Merge 2-3 adjacent sentences
    for span in (2, 3):
        for i in range(len(sentences) - span + 1):
            group = sentences[i:i+span]
            merged_text = " ".join(g["text"] for g in group)
            dur = group[-1]["end"] - group[0]["start"]
            if dur < 8 or dur > 25:
                continue
            score, hits = score_passage(merged_text, dur, group[0]["first_word"])
            if hits < 2:
                continue
            candidates.append({
                "video_id": vid_id,
                "channel": VIDEO_META[vid_id]["channel"],
                "handle": VIDEO_META[vid_id]["handle"],
                "video_title": VIDEO_META[vid_id]["title"],
                "text": merged_text,
                "start": group[0]["start"],
                "end": group[-1]["end"],
                "duration": round(dur, 2),
                "first_word": group[0]["first_word"],
                "last_word": group[-1]["last_word"],
                "word_start": group[0]["word_start"],
                "word_end": group[-1]["word_end"],
                "score": score,
                "topic_hits": hits,
                "span": span,
            })

    return candidates


def dedup_candidates(candidates):
    """Remove overlapping candidates, keeping highest score."""
    candidates.sort(key=lambda x: x["score"], reverse=True)
    kept = []
    used = {}  # vid_id -> [(start, end)]
    for c in candidates:
        vid = c["video_id"]
        if vid not in used:
            used[vid] = []
        overlap = any(c["start"] < e and c["end"] > s for s, e in used[vid])
        if not overlap:
            kept.append(c)
            used[vid].append((c["start"], c["end"]))
    return kept


def select_edl(candidates):
    """Pick 4-6 clips for story arc: setup -> scale -> analysis -> lesson -> resilience."""
    arc = [
        ("setup", ["hack", "breach", "stolen", "attack"]),
        ("scale", ["billion", "6.3", "largest", "history", "record"]),
        ("analysis", ["inside", "how", "exploit", "launder", "social engineer"]),
        ("lesson", ["self-custody", "self custody", "not your keys", "hardware wallet",
                     "cold storage", "custod"]),
        ("resilience", ["holding", "strong", "recover", "resili", "bounce", "survived"]),
    ]

    edl = []
    used_vids_count = {}

    for role, kws in arc:
        best = None
        for c in candidates:
            vid = c["video_id"]
            if used_vids_count.get(vid, 0) >= 2:
                continue
            # Check already picked (overlap)
            if any(e["video_id"] == vid and abs(e["start"] - c["start"]) < 5 for e in edl):
                continue
            tl = c["text"].lower()
            if any(kw in tl for kw in kws):
                if not best or c["score"] > best["score"]:
                    best = c
        if best:
            edl.append({**best, "role": role})
            used_vids_count[best["video_id"]] = used_vids_count.get(best["video_id"], 0) + 1

    # Pad if under 50s
    total = sum(c["duration"] for c in edl)
    if total < 50:
        for c in candidates:
            if total >= 75:
                break
            vid = c["video_id"]
            if used_vids_count.get(vid, 0) >= 2:
                continue
            if any(e["video_id"] == vid and abs(e["start"] - c["start"]) < 5 for e in edl):
                continue
            edl.append({**c, "role": "additional"})
            total += c["duration"]
            used_vids_count[vid] = used_vids_count.get(vid, 0) + 1

    return edl


def find_hook(candidates):
    """Single most interesting complete sentence <=8s."""
    short = [c for c in candidates if c["duration"] <= 10 and c["score"] >= 20]
    short.sort(key=lambda x: x["score"], reverse=True)
    if short:
        return short[0]
    # Fallback: best candidate overall, note it needs trimming
    if candidates:
        return {**candidates[0], "hook_note": "May need trimming to <=8s"}
    return None


def write_vo_script(edl_clips, hook):
    """Write VO script: 2-sentence intro + bridges where needed. <=60 words total."""
    vo = {
        "intro": "the largest hack in crypto history just shook every exchange on earth. "
                 "six point three billion gone from binance, and the debate over self-custody is louder than ever.",
        "bridges": [],
    }

    # Check if we need bridges between clips with different sub-topics
    for i in range(len(edl_clips) - 1):
        cur_role = edl_clips[i].get("role", "")
        next_role = edl_clips[i+1].get("role", "")
        # Bridge only between major topic shifts
        if cur_role in ("setup", "scale") and next_role in ("lesson", "resilience"):
            vo["bridges"].append({
                "after_clip": i + 1,
                "text": "but for bitcoiners, the lesson isn't new.",
            })
        elif cur_role == "analysis" and next_role in ("lesson", "resilience"):
            vo["bridges"].append({
                "after_clip": i + 1,
                "text": "and that's exactly why self-custody matters.",
            })

    total_words = len(vo["intro"].split())
    for b in vo["bridges"]:
        total_words += len(b["text"].split())
    vo["total_words"] = total_words

    return vo


# === MAIN ===
print("=== STAGE 2: SELECT PASSAGES AND BUILD EDL ===\n")

all_candidates = []
for vid_id in VIDEO_META:
    path = os.path.join(TRANSCRIPTS_DIR, f"{vid_id}.json")
    if not os.path.exists(path):
        print(f"  {vid_id} ({VIDEO_META[vid_id]['channel']}): PENDING (no transcript yet)")
        continue
    with open(path) as f:
        t = json.load(f)
    cands = find_candidates(t, vid_id)
    print(f"  {vid_id} ({VIDEO_META[vid_id]['channel']}): {len(cands)} candidates")
    all_candidates.extend(cands)

if not all_candidates:
    print("ERROR: No candidates found. Need at least one transcript.")
    sys.exit(1)

# Dedup
candidates = dedup_candidates(all_candidates)
print(f"\nTotal non-overlapping candidates: {len(candidates)}")

# Top 15
print("\n--- TOP 15 CANDIDATES ---")
for i, c in enumerate(candidates[:15]):
    print(f"#{i+1} [s={c['score']}, {c['channel']}, {c['duration']:.1f}s, {c['span']}seg]")
    print(f"  \"{c['text'][:120]}\"")
    print(f"  words: {c['word_start']:.2f}-{c['word_end']:.2f}")

# Save all candidates
with open(f"{BASE}/candidates.json", "w") as f:
    json.dump(candidates[:15], f, indent=2)

# Build EDL
edl_clips = select_edl(candidates)
total_dur = sum(c["duration"] for c in edl_clips)
print(f"\n--- EDL: {len(edl_clips)} clips, {total_dur:.1f}s ---")

# Find hook
hook = find_hook(candidates)
if hook:
    print(f"\nHOOK [{hook['channel']}, {hook['duration']:.1f}s]: \"{hook['text'][:100]}\"")

# VO script
vo = write_vo_script(edl_clips, hook)
print(f"\nVO intro ({len(vo['intro'].split())}w): \"{vo['intro']}\"")
for b in vo["bridges"]:
    print(f"VO bridge after clip {b['after_clip']} ({len(b['text'].split())}w): \"{b['text']}\"")
print(f"Total VO words: {vo['total_words']}")

# Assemble final EDL
edl = {
    "topic": "Binance $6.3B Hack: Self-Custody Is the Only Way",
    "angle": "The largest crypto hack in history just proved what Bitcoiners have been saying all along.",
    "hook": {
        "video_id": hook["video_id"],
        "channel": hook["channel"],
        "handle": hook.get("handle", ""),
        "video_title": hook.get("video_title", ""),
        "text": hook["text"],
        "first_word": hook["first_word"],
        "last_word": hook["last_word"],
        "word_start": hook["word_start"],
        "word_end": hook["word_end"],
        "duration": hook["duration"],
        "reason": "Most impactful short statement on the hack",
    } if hook else None,
    "vo": vo,
    "clips": [],
    "total_clip_duration": round(total_dur, 2),
}

role_order = {"setup": 0, "scale": 1, "analysis": 2, "lesson": 3, "resilience": 4, "additional": 5}
edl_clips.sort(key=lambda x: role_order.get(x.get("role", "additional"), 99))

for i, c in enumerate(edl_clips):
    edl["clips"].append({
        "index": i + 1,
        "video_id": c["video_id"],
        "channel": c["channel"],
        "handle": c.get("handle", ""),
        "video_title": c.get("video_title", ""),
        "url": VIDEO_META[c["video_id"]]["url"],
        "text": c["text"],
        "first_word": c["first_word"],
        "last_word": c["last_word"],
        "word_start": c["word_start"],
        "word_end": c["word_end"],
        "duration": c["duration"],
        "role": c.get("role", "additional"),
        "reason": c.get("role", "additional"),
    })
    print(f"  #{i+1} [{c.get('role','')}] {c['channel']} ({c['duration']:.1f}s): \"{c['text'][:80]}...\"")

with open(f"{BASE}/edl.json", "w") as f:
    json.dump(edl, f, indent=2)
print(f"\nEDL written to {BASE}/edl.json")
print(f"VO script in edl.json['vo']")
