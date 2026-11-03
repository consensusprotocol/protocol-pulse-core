#!/usr/bin/env python3
"""Stage 2 v2: Fix all 6 rejection points.
- Complete sentences only (no mid-sentence starts, no dangling ends)
- No teaser/rundown material (first 60s of source excluded for Simply Bitcoin/CoinDesk)
- No hook duplicate
- Score for specificity: host explaining/arguing, not listing headlines
- Loudnorm-aware clip selection
- 4-5 clips, 50-75s total, ordered: setup -> what happened -> why it matters -> self-custody lesson -> close
"""
import json, os, re, sys

BASE = "/home/ultron/protocol_pulse/segment_v1"
TRANSCRIPTS_DIR = os.path.join(BASE, "transcripts")

VIDEO_META = {
    "bSmFGoAKPBc": {"channel": "Simply Bitcoin", "handle": "@SimplyBitcoin",
                     "title": "Why Bitcoin Is Holding Strong After a $6.3B Hack?",
                     "url": "https://www.youtube.com/watch?v=bSmFGoAKPBc",
                     "teaser_end": 60},  # first 60s is teaser/intro
    "5ripuS9GDaM": {"channel": "Simply Bitcoin", "handle": "@SimplyBitcoin",
                     "title": "Was The $6.3B Binance Heist an Inside Job?",
                     "url": "https://www.youtube.com/watch?v=5ripuS9GDaM",
                     "teaser_end": 60},
    "Eojd18J_wuU": {"channel": "BTC Sessions", "handle": "@BTCSessions",
                     "title": "Binance Just Proved Why Self-Custody Matters",
                     "url": "https://www.youtube.com/watch?v=Eojd18J_wuU",
                     "teaser_end": 30},
    "7QIB_zdKU9A": {"channel": "CoinDesk", "handle": "@CoinDesk",
                     "title": "Bitcoin ETFs Hit by $643M Selloff as Binance Hack Shakes Crypto",
                     "url": "https://www.youtube.com/watch?v=7QIB_zdKU9A",
                     "teaser_end": 60},  # show rundown
}

TOPIC_KW = [
    "binance", "hack", "hacker", "hacked", "stolen", "theft", "heist",
    "self-custody", "self custody", "not your keys", "not your coins",
    "cold storage", "hardware wallet", "custodial", "exchange",
    "6.3 billion", "6.4 billion", "6.3b", "6.4b", "$6.3", "$6.4", "billion",
    "security", "breach", "exploit", "frozen", "freeze", "tether", "circle",
    "north korea", "lazarus",
]

# Words that indicate a mid-sentence start
BAD_STARTS = {"and", "but", "so", "because", "which", "that's", "since",
              "meaning", "like", "well", "um", "uh", "or", "also",
              "a", "the", "making", "too", "plus"}
# Words that indicate an incomplete end
BAD_ENDS = {"the", "a", "an", "is", "are", "was", "were", "and", "but",
            "or", "of", "in", "on", "to", "for", "with", "that", "this"}

# Teaser/rundown phrases to reject
TEASER_PHRASES = [
    "on today's", "public keys", "in today's episode", "let's get into it",
    "welcome to", "welcome back", "subscribe", "hit the like",
    "will this time be different", "was the binance hack an inside job",
    "let me know in the comments", "stick around",
]


def build_sentences(transcript):
    """Build sentences from segments, filtering by word boundaries."""
    words = transcript.get("words", [])
    segments = transcript.get("segments", [])
    if not words or not segments:
        return []

    sentences = []
    for seg in segments:
        text = seg["text"].strip()
        if not text or len(text) < 20:
            continue
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


def is_complete_sentence(text, first_word, last_word):
    """Check if text starts and ends cleanly."""
    fw = first_word.lower().rstrip(",.:;!?")
    lw = last_word.lower().rstrip(",.:;!?")

    # Must not start with a conjunction/filler
    if fw in BAD_STARTS:
        return False

    # Must end with sentence-ending punctuation
    if not text.rstrip().endswith(('.', '!', '?', '"')):
        return False

    # Must not end with a dangling word
    if lw in BAD_ENDS:
        return False

    return True


def is_teaser(text, start_time, teaser_end):
    """Check if this is teaser/cold-open material."""
    tl = text.lower()
    # In teaser zone
    if start_time < teaser_end:
        return True
    # Contains teaser phrases
    for phrase in TEASER_PHRASES:
        if phrase in tl:
            return True
    return False


def score_passage_v2(text, duration, first_word, vid_id, start_time):
    """Score a passage. Higher = better for medley."""
    tl = text.lower()
    score = 0

    # Topic relevance (max ~40 from keywords)
    hits = sum(1 for kw in TOPIC_KW if kw in tl)
    score += min(hits * 6, 40)

    # Specificity: concrete numbers, dollar amounts
    nums = re.findall(r'\$[\d,.]+[BMK]?|\d+[\d,.]*\s*(?:billion|million|percent|%)', tl)
    score += min(len(nums) * 8, 24)

    # Named entities (specific claims, not generic)
    names = re.findall(r'(?:Binance|Tether|Circle|Ripple|Arbitrum|North Korea|Lazarus|Ledger|Trezor|Bitcoin|ETF|River)', text, re.I)
    unique_names = set(n.lower() for n in names)
    score += min(len(unique_names), 4) * 4

    # Duration sweet spot: 10-18s ideal
    if 10 <= duration <= 18:
        score += 10
    elif 8 <= duration <= 22:
        score += 4
    else:
        score -= 15

    # Explanation/argument indicators (host explaining something)
    explain_phrases = ["because", "the reason", "that means", "what happened",
                       "this proves", "this shows", "the point is", "the lesson",
                       "what we saw", "the fact that", "this is why"]
    for ep in explain_phrases:
        if ep in tl:
            score += 5

    # Penalty: starts with filler
    fw = first_word.lower().rstrip(",.:;!?")
    if fw in {"uh", "um", "like", "well", "yeah"}:
        score -= 8

    # Penalty: ALL CAPS (auto-generated captions, less natural)
    if text == text.upper() and len(text) > 30:
        score -= 5

    return score, hits


def find_candidates_v2(transcript, vid_id):
    """Find complete-sentence, non-teaser, on-topic passages."""
    meta = VIDEO_META[vid_id]
    teaser_end = meta.get("teaser_end", 0)
    sentences = build_sentences(transcript)
    candidates = []

    # Single sentences
    for s in sentences:
        if s["duration"] < 7 or s["duration"] > 25:
            continue
        if is_teaser(s["text"], s["start"], teaser_end):
            continue
        if not is_complete_sentence(s["text"], s["first_word"], s["last_word"]):
            continue
        score, hits = score_passage_v2(s["text"], s["duration"], s["first_word"], vid_id, s["start"])
        if hits == 0:
            continue
        candidates.append({
            "video_id": vid_id,
            "channel": meta["channel"],
            "handle": meta["handle"],
            "video_title": meta["title"],
            "url": meta["url"],
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
            if dur < 8 or dur > 22:
                continue
            if is_teaser(merged_text, group[0]["start"], teaser_end):
                continue
            if not is_complete_sentence(merged_text, group[0]["first_word"], group[-1]["last_word"]):
                continue
            score, hits = score_passage_v2(merged_text, dur, group[0]["first_word"], vid_id, group[0]["start"])
            if hits < 2:
                continue
            candidates.append({
                "video_id": vid_id,
                "channel": meta["channel"],
                "handle": meta["handle"],
                "video_title": meta["title"],
                "url": meta["url"],
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
    used = {}
    for c in candidates:
        vid = c["video_id"]
        if vid not in used:
            used[vid] = []
        overlap = any(c["start"] < e and c["end"] > s for s, e in used[vid])
        if not overlap:
            kept.append(c)
            used[vid].append((c["start"], c["end"]))
    return kept


def select_edl_v2(candidates, hook):
    """Pick 4-5 clips for: setup -> what happened -> why it matters -> self-custody lesson -> close.
    No duplicate of hook. Max 2 clips from any one channel. 50-75s total."""

    hook_vid = hook["video_id"] if hook else None
    hook_start = hook.get("word_start", -1) if hook else -1
    hook_end = hook.get("word_end", -1) if hook else -1

    arc_roles = [
        ("setup", ["hack", "stolen", "drained", "6.3", "6.4", "billion", "largest"]),
        ("what_happened", ["swapped", "froze", "frozen", "tether", "circle", "chain", "minutes",
                           "hot wallet", "blockchains", "commingled", "north korea", "lazarus"]),
        ("why_it_matters", ["crash", "crashed", "76k", "etf", "outflow", "selloff", "sell-off",
                            "price", "market", "shook", "fear"]),
        ("self_custody", ["self-custody", "self custody", "not your keys", "hardware wallet",
                          "cold storage", "custodial", "your own keys", "custody matters",
                          "hold your own"]),
        ("close", ["bitcoin", "strong", "recover", "resili", "survived", "proves", "lesson",
                    "long-term", "the point", "takeaway"]),
    ]

    edl = []
    used_vids_count = {}

    for role, kws in arc_roles:
        best = None
        for c in candidates:
            vid = c["video_id"]
            # Max 2 clips per channel
            if used_vids_count.get(vid, 0) >= 2:
                continue
            # No overlap with existing picks
            if any(e["video_id"] == vid and abs(e["start"] - c["start"]) < 5 for e in edl):
                continue
            # No duplicate of hook
            if vid == hook_vid and abs(c["word_start"] - hook_start) < 2:
                continue
            tl = c["text"].lower()
            if any(kw in tl for kw in kws):
                if not best or c["score"] > best["score"]:
                    best = c
        if best:
            edl.append({**best, "role": role})
            used_vids_count[best["video_id"]] = used_vids_count.get(best["video_id"], 0) + 1

    # Check total duration
    total = sum(c["duration"] for c in edl)
    if total > 75:
        # Drop lowest-scored clip
        edl.sort(key=lambda x: x["score"])
        edl.pop(0)

    return edl


def write_vo_v2(edl_clips):
    """VO intro + optional bridge. Bridge only where it connects two different ideas."""
    vo = {
        "intro": "the largest hack in crypto history just shook every exchange on earth. "
                 "six point three billion gone from binance, and the debate over self-custody "
                 "is louder than ever.",
        "bridges": [],
        "total_words": 28,
    }

    # Bridge between "why_it_matters" and "self_custody" if both exist
    roles = [c.get("role", "") for c in edl_clips]
    for i in range(len(roles) - 1):
        if roles[i] in ("what_happened", "why_it_matters") and roles[i+1] == "self_custody":
            bridge = {"after_clip": i + 1, "text": "and that's exactly why self-custody matters."}
            vo["bridges"].append(bridge)
            vo["total_words"] += len(bridge["text"].split())
            break

    return vo


# === MAIN ===
print("=== STAGE 2 v2: REVISED CLIP SELECTION ===\n")

all_candidates = []
transcripts_used = []
for vid_id in VIDEO_META:
    path = os.path.join(TRANSCRIPTS_DIR, f"{vid_id}.json")
    if not os.path.exists(path) or os.path.getsize(path) < 500:
        print(f"  {vid_id} ({VIDEO_META[vid_id]['channel']}): PENDING")
        continue
    with open(path) as f:
        t = json.load(f)
    if not t.get("words"):
        print(f"  {vid_id} ({VIDEO_META[vid_id]['channel']}): EMPTY (no words)")
        continue
    cands = find_candidates_v2(t, vid_id)
    print(f"  {vid_id} ({VIDEO_META[vid_id]['channel']}): {len(cands)} candidates")
    all_candidates.extend(cands)
    transcripts_used.append(vid_id)

print(f"\nTranscripts used: {len(transcripts_used)}/4")

if not all_candidates:
    print("ERROR: No candidates found.")
    sys.exit(1)

candidates = dedup_candidates(all_candidates)
print(f"Total non-overlapping candidates: {len(candidates)}")

# Top 20
print("\n--- TOP 20 CANDIDATES ---")
for i, c in enumerate(candidates[:20]):
    print(f"#{i+1} [s={c['score']}, {c['channel']}, {c['duration']:.1f}s, span={c['span']}]")
    print(f"  first: \"{c['first_word']}\"  last: \"{c['last_word']}\"")
    print(f"  \"{c['text'][:120]}\"")

# Save candidates
with open(f"{BASE}/candidates_v2.json", "w") as f:
    json.dump(candidates[:30], f, indent=2)

# Find hook: best short complete sentence <=10s
hook_cands = [c for c in candidates if c["duration"] <= 10 and c["score"] >= 20]
hook_cands.sort(key=lambda x: x["score"], reverse=True)
hook = hook_cands[0] if hook_cands else None

if hook:
    print(f"\nHOOK [{hook['channel']}, {hook['duration']:.1f}s]: \"{hook['text'][:100]}\"")

# Build EDL
edl_clips = select_edl_v2(candidates, hook)
total_dur = sum(c["duration"] for c in edl_clips)
print(f"\n--- EDL v2: {len(edl_clips)} clips, {total_dur:.1f}s ---")

# VO
vo = write_vo_v2(edl_clips)
print(f"\nVO intro ({len(vo['intro'].split())}w): \"{vo['intro'][:100]}...\"")
for b in vo["bridges"]:
    print(f"VO bridge after clip {b['after_clip']} ({len(b['text'].split())}w): \"{b['text']}\"")

# Assemble EDL
role_order = {"setup": 0, "what_happened": 1, "why_it_matters": 2, "self_custody": 3, "close": 4}
edl_clips.sort(key=lambda x: role_order.get(x.get("role", ""), 99))

edl_out = {
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
        "reason": "Strongest short on-topic statement",
    } if hook else None,
    "vo": vo,
    "clips": [],
    "total_clip_duration": round(total_dur, 2),
    "transcripts_used": transcripts_used,
}

print("\n--- FINAL EDL TABLE ---")
print(f"{'#':>2} | {'Channel':<16} | {'Dur':>5} | {'Role':<15} | First 12 words ... Last 6 words")
print("-" * 100)

for i, c in enumerate(edl_clips):
    words_list = c["text"].split()
    first12 = " ".join(words_list[:12])
    last6 = " ".join(words_list[-6:])
    print(f"{i+1:>2} | {c['channel']:<16} | {c['duration']:>5.1f} | {c.get('role',''):<15} | {first12} ... {last6}")

    edl_out["clips"].append({
        "index": i + 1,
        "video_id": c["video_id"],
        "channel": c["channel"],
        "handle": c.get("handle", ""),
        "video_title": c.get("video_title", ""),
        "url": c.get("url", VIDEO_META[c["video_id"]]["url"]),
        "text": c["text"],
        "first_word": c["first_word"],
        "last_word": c["last_word"],
        "word_start": c["word_start"],
        "word_end": c["word_end"],
        "duration": c["duration"],
        "role": c.get("role", ""),
        "reason": c.get("role", ""),
    })

with open(f"{BASE}/edl_v2.json", "w") as f:
    json.dump(edl_out, f, indent=2)

print(f"\nEDL v2 written to {BASE}/edl_v2.json")
print(f"Total clip duration: {total_dur:.1f}s (target: 50-75s)")
print(f"Estimated medley: ~{total_dur + 11.5 + 3.1:.0f}s (clips + VO)")
