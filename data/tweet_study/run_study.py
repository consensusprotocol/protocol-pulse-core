#!/usr/bin/env python3
"""Twitter Engagement Study for Protocol Pulse voice blueprint."""

import os
import sys
import json
import time
import re
import math
from datetime import datetime, timezone
from collections import Counter
from urllib.parse import quote

import requests
import pandas as pd

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BEARER = os.environ.get("TWITTER_BEARER_TOKEN")
if not BEARER:
    print("ERROR: TWITTER_BEARER_TOKEN not set")
    sys.exit(1)

OUTPUT_DIR = os.path.expanduser("~/protocol_pulse/data/tweet_study")
RAW_FILE = os.path.join(OUTPUT_DIR, "raw_tweets.json")
REPORT_FILE = os.path.join(OUTPUT_DIR, "TWEET_VOICE_STUDY.md")

HEADERS = {"Authorization": f"Bearer {BEARER}"}
BASE = "https://api.twitter.com"

ACCOUNTS = {
    "conviction_data": ["saylor", "PrestonPysh", "gladstein", "WClementeIII", "APompliano"],
    "depth_nuance": ["LynAldenContact", "adam3us", "nic__carter", "NickSzabo4"],
    "irreverent_deadpan": ["maxkeiser", "MartyBent", "PeterMcCormack", "americanhodl", "daborosgrams"],
    "high_eng_hybrids": ["CryptoHayes", "ErikVoorhees"],
}

TIER_LABELS = {
    "conviction_data": "Conviction + Data",
    "depth_nuance": "Depth + Nuance",
    "irreverent_deadpan": "Irreverent / Deadpan",
    "high_eng_hybrids": "High-Eng Hybrids",
}

PROFANITY = {"damn", "hell", "shit", "fuck", "ass", "bullshit", "lmao", "lol"}
DATA_RE = re.compile(r'\d+|[\$%]|\d+[BMKbmk]\b')
EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001f926-\U0001f937"
    "\U00010000-\U0010ffff"
    "\u2640-\u2642"
    "\u2600-\u2B55"
    "\u200d\u23cf\u23e9\u231a\ufe0f\u3030"
    "]+",
    flags=re.UNICODE
)

# ─── RATE LIMIT STATE ────────────────────────────────────────────────────────
call_count = 0
failed_handles = []


def call_twitter_api(url, params=None):
    """Single function for all Twitter API calls with rate limit handling."""
    global call_count
    call_count += 1

    time.sleep(1.1)  # mandatory delay

    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)

    # Log rate limits every 5 calls
    remaining = resp.headers.get("x-rate-limit-remaining")
    reset = resp.headers.get("x-rate-limit-reset")
    if call_count % 5 == 0 and remaining:
        print(f"  [rate limit] remaining: {remaining}, call #{call_count}")

    # Handle rate limiting
    if remaining and int(remaining) < 5 and reset:
        wait = int(reset) - int(time.time()) + 5
        if wait > 0:
            print(f"  [rate limit] Low quota ({remaining}). Sleeping {wait}s...")
            time.sleep(wait)

    if resp.status_code == 429:
        if reset:
            wait = int(reset) - int(time.time()) + 5
            wait = max(wait, 15)
        else:
            wait = 60
        print(f"  [429] Rate limited. Sleeping {wait}s then retrying...")
        time.sleep(wait)
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code == 429:
            print(f"  [429] Retry failed. Stopping gracefully.")
            return None

    if resp.status_code != 200:
        print(f"  [HTTP {resp.status_code}] {url}")
        return None

    return resp.json()


# ─── STEP 1: HANDLE VERIFICATION ─────────────────────────────────────────────
def verify_handles():
    """Verify all handles, return dict of handle -> {id, followers, tier}."""
    verified = {}
    all_handles = []
    handle_tier = {}
    for tier, handles in ACCOUNTS.items():
        for h in handles:
            all_handles.append(h)
            handle_tier[h] = tier

    print(f"Verifying {len(all_handles)} handles...")
    for h in all_handles:
        url = f"{BASE}/2/users/by/username/{h}"
        params = {"user.fields": "public_metrics"}
        data = call_twitter_api(url, params)
        if data is None or "data" not in data:
            err = data.get("errors", [{}])[0].get("detail", "unknown") if data else "no response"
            print(f"  FAILED: @{h} - {err}")
            failed_handles.append(h)
            continue
        user = data["data"]
        followers = user.get("public_metrics", {}).get("followers_count", 0)
        verified[h] = {
            "id": user["id"],
            "followers": followers,
            "tier": handle_tier[h],
            "name": user.get("name", h),
        }
        print(f"  OK: @{h} (id={user['id']}, followers={followers:,})")

    print(f"\nVerified: {len(verified)}/{len(all_handles)} accounts")
    if failed_handles:
        print(f"Failed: {', '.join('@'+h for h in failed_handles)}")
    return verified


# ─── STEP 2: TWEET COLLECTION ────────────────────────────────────────────────
def classify_tweet(tweet):
    """Classify tweet as original, reply, or quote."""
    refs = tweet.get("referenced_tweets", [])
    if not refs:
        return "original"
    for r in refs:
        if r["type"] == "replied_to":
            return "reply"
        if r["type"] == "quoted":
            return "quote"
    return "original"


def enrich_tweet(tweet, handle, followers, tier):
    """Add computed fields to a tweet."""
    text = tweet.get("text", "")
    pm = tweet.get("public_metrics", {})
    words = text.split()

    enriched = {
        "id": tweet["id"],
        "handle": handle,
        "tier": tier,
        "followers": followers,
        "text": text,
        "created_at": tweet.get("created_at", ""),
        "likes": pm.get("like_count", 0),
        "retweets": pm.get("retweet_count", 0),
        "replies": pm.get("reply_count", 0),
        "quotes": pm.get("quote_count", 0),
        "impressions": pm.get("impression_count", None),
        "tweet_type": classify_tweet(tweet),
        "char_count": len(text),
        "word_count": len(words),
        "has_url": bool(tweet.get("entities", {}).get("urls")),
        "has_media": "media" in tweet.get("entities", {}) if tweet.get("entities") else False,
        "has_data": bool(DATA_RE.search(text)),
        "has_question": "?" in text,
        "has_em_dash": "\u2014" in text or "\u2013" in text,
        "has_profanity": bool(PROFANITY & set(w.lower().strip(".,!?\"'()") for w in words)),
        "has_emoji": bool(EMOJI_RE.search(text)),
    }

    # Scoring
    raw = enriched["likes"] + (enriched["retweets"] * 2) + (enriched["replies"] * 3) + (enriched["quotes"] * 4)
    enriched["raw_engagement"] = raw
    enriched["engagement_rate"] = raw / followers if followers > 0 else 0

    # Sentence count (rough)
    sentences = re.split(r'[.!?]+', text)
    enriched["sentence_count"] = len([s for s in sentences if s.strip()])

    # Ending punctuation
    stripped = text.rstrip()
    if stripped.endswith("?"):
        enriched["ending_punct"] = "question"
    elif stripped.endswith("!"):
        enriched["ending_punct"] = "exclamation"
    elif stripped.endswith("."):
        enriched["ending_punct"] = "period"
    else:
        enriched["ending_punct"] = "none"

    # Starts with number
    enriched["starts_with_number"] = bool(re.match(r'^[\$]?\d', text))

    return enriched


def pull_tweets(verified):
    """Pull tweets for all verified accounts."""
    all_tweets = []
    impressions_available = True
    idx = 0

    for handle, info in verified.items():
        idx += 1
        user_id = info["id"]
        followers = info["followers"]
        tier = info["tier"]
        tweets_for_account = []

        params = {
            "max_results": 100,
            "tweet.fields": "created_at,public_metrics,entities,referenced_tweets",
            "exclude": "retweets",
        }
        url = f"{BASE}/2/users/{user_id}/tweets"

        for page in range(2):  # 2 pages of 100
            data = call_twitter_api(url, params)
            if data is None:
                print(f"  [{idx}/{len(verified)}] @{handle}: API error on page {page+1}, skipping rest")
                break

            page_tweets = data.get("data", [])
            if not page_tweets:
                break

            # Check impressions on first tweet
            if page == 0 and idx == 1:
                first_pm = page_tweets[0].get("public_metrics", {})
                if "impression_count" not in first_pm:
                    impressions_available = False
                    print("  [info] Impressions unavailable on this API tier")

            for t in page_tweets:
                enriched = enrich_tweet(t, handle, followers, tier)
                tweets_for_account.append(enriched)

            # Pagination
            next_token = data.get("meta", {}).get("next_token")
            if next_token:
                params["pagination_token"] = next_token
            else:
                break

        # Thread detection: check for self-replies within 2 min
        tweets_for_account.sort(key=lambda t: t["created_at"])
        for i, tw in enumerate(tweets_for_account):
            tw["is_thread_starter"] = False
            if tw["tweet_type"] == "original" and i + 1 < len(tweets_for_account):
                next_tw = tweets_for_account[i + 1]
                if next_tw["tweet_type"] == "reply":
                    try:
                        t1 = datetime.fromisoformat(tw["created_at"].replace("Z", "+00:00"))
                        t2 = datetime.fromisoformat(next_tw["created_at"].replace("Z", "+00:00"))
                        if abs((t2 - t1).total_seconds()) <= 120:
                            tw["is_thread_starter"] = True
                    except:
                        pass

        all_tweets.extend(tweets_for_account)

        # Progress
        if tweets_for_account:
            avg_rate = sum(t["engagement_rate"] for t in tweets_for_account) / len(tweets_for_account)
            print(f"  [{idx}/{len(verified)}] @{handle}: {len(tweets_for_account)} tweets pulled, avg eng rate: {avg_rate:.6f}")
        else:
            print(f"  [{idx}/{len(verified)}] @{handle}: 0 tweets pulled")

        # Remove pagination_token for next account
        params.pop("pagination_token", None)

    return all_tweets, impressions_available


# ─── STEP 3-4: ANALYSIS ──────────────────────────────────────────────────────
def analyze(tweets):
    """Run all analyses, return report sections."""
    df = pd.DataFrame(tweets)
    if df.empty:
        return "No data collected."

    n = len(df)
    # Top 10% threshold
    top10_threshold = df["engagement_rate"].quantile(0.90)
    df["top10"] = df["engagement_rate"] >= top10_threshold
    top_df = df[df["top10"]]

    sections = {}

    # ── Section 1: Top 15 tweets ──
    top15 = df.nlargest(15, "engagement_rate")
    rows = []
    for rank, (_, t) in enumerate(top15.iterrows(), 1):
        text_short = t["text"][:120].replace("|", "/").replace("\n", " ")
        date_short = t["created_at"][:10] if t["created_at"] else ""
        rows.append(
            f"| {rank} | @{t['handle']} | {t['engagement_rate']:.6f} | "
            f"{t['likes']:,} | {t['retweets']:,} | {t['replies']:,} | "
            f"{text_short} | {date_short} |"
        )
    sections["top15"] = "\n".join(rows)

    # ── Section 2: Per-account ranking ──
    acct = df.groupby("handle").agg(
        followers=("followers", "first"),
        avg_rate=("engagement_rate", "mean"),
        median_rate=("engagement_rate", "median"),
        best_rate=("engagement_rate", "max"),
        tier=("tier", "first"),
    ).sort_values("avg_rate", ascending=False).reset_index()
    acct_rows = []
    for rank, (_, a) in enumerate(acct.iterrows(), 1):
        acct_rows.append(
            f"| {rank} | @{a['handle']} | {a['followers']:,} | "
            f"{a['avg_rate']:.6f} | {a['median_rate']:.6f} | {a['best_rate']:.6f} |"
        )
    sections["per_account"] = "\n".join(acct_rows)

    # ── Section 3: Structure patterns ──
    def struct_pct(sub):
        n_sub = len(sub)
        if n_sub == 0:
            return {}
        return {
            "avg_chars": sub["char_count"].mean(),
            "avg_words": sub["word_count"].mean(),
            "pct_questions": sub["has_question"].mean() * 100,
            "pct_data": sub["has_data"].mean() * 100,
            "pct_original": (sub["tweet_type"] == "original").mean() * 100,
            "pct_media": sub["has_media"].mean() * 100,
            "pct_thread": sub["is_thread_starter"].mean() * 100 if "is_thread_starter" in sub else 0,
            "pct_url": sub["has_url"].mean() * 100,
        }

    full_s = struct_pct(df)
    top_s = struct_pct(top_df)

    struct_rows = []
    metrics = [
        ("Avg chars", "avg_chars", ".0f"),
        ("Avg words", "avg_words", ".0f"),
        ("% questions", "pct_questions", ".1f"),
        ("% with data/numbers", "pct_data", ".1f"),
        ("% original (not reply/QT)", "pct_original", ".1f"),
        ("% with media", "pct_media", ".1f"),
        ("% thread starters", "pct_thread", ".1f"),
        ("% with URL", "pct_url", ".1f"),
    ]
    for label, key, fmt in metrics:
        fv = full_s.get(key, 0)
        tv = top_s.get(key, 0)
        delta = tv - fv
        sign = "+" if delta >= 0 else ""
        struct_rows.append(f"| {label} | {fv:{fmt}} | {tv:{fmt}} | {sign}{delta:{fmt}} |")
    sections["structure"] = "\n".join(struct_rows)

    # ── Section 4: Style patterns ──
    # Em dash correlation
    em_yes = df[df["has_em_dash"]]["engagement_rate"].mean() if df["has_em_dash"].any() else 0
    em_no = df[~df["has_em_dash"]]["engagement_rate"].mean() if (~df["has_em_dash"]).any() else 0
    if em_yes > em_no * 1.1:
        em_verdict = "em dashes HELP (higher engagement)"
    elif em_no > em_yes * 1.1:
        em_verdict = "em dashes HURT (lower engagement)"
    else:
        em_verdict = "neutral (no significant difference)"

    sections["em_dash"] = (
        f"- Tweets WITH em dash: avg engagement rate = {em_yes:.6f}\n"
        f"- Tweets WITHOUT em dash: avg engagement rate = {em_no:.6f}\n"
        f"- Verdict: {em_verdict}"
    )

    def style_metrics(sub):
        n_sub = len(sub)
        if n_sub == 0:
            return {}
        endings = sub["ending_punct"].value_counts(normalize=True) * 100
        return {
            "pct_emoji": sub["has_emoji"].mean() * 100,
            "pct_profanity": sub["has_profanity"].mean() * 100,
            "pct_period": endings.get("period", 0),
            "pct_question": endings.get("question", 0),
            "pct_none": endings.get("none", 0),
            "pct_starts_number": sub["starts_with_number"].mean() * 100,
            "avg_sentences": sub["sentence_count"].mean(),
        }

    full_style = style_metrics(df)
    top_style = style_metrics(top_df)

    style_labels = [
        ("% with emoji", "pct_emoji"),
        ("% with profanity", "pct_profanity"),
        ("% ending in period", "pct_period"),
        ("% ending in question mark", "pct_question"),
        ("% ending in no punctuation", "pct_none"),
        ("% starting with a number", "pct_starts_number"),
        ("Avg sentences per tweet", "avg_sentences"),
    ]
    style_rows = []
    for label, key in style_labels:
        fmt = ".1f" if "Avg" not in label else ".2f"
        fv = full_style.get(key, 0)
        tv = top_style.get(key, 0)
        style_rows.append(f"| {label} | {fv:{fmt}} | {tv:{fmt}} |")
    sections["style"] = "\n".join(style_rows)

    # ── Section 5: Tone words (top 50 by engagement rate) ──
    top50 = df.nlargest(50, "engagement_rate")
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "each",
        "every", "both", "few", "more", "most", "other", "some", "such", "no",
        "nor", "not", "only", "own", "same", "so", "than", "too", "very",
        "just", "don", "now", "and", "but", "or", "if", "this", "that", "it",
        "its", "i", "me", "my", "we", "our", "you", "your", "he", "him",
        "his", "she", "her", "they", "them", "their", "what", "which", "who",
        "whom", "these", "those", "am", "about", "up", "down", "s", "t", "re",
        "ve", "ll", "d", "m", "rt", "https", "co", "http", "amp",
    }

    all_words = []
    bigrams_list = []
    trigrams_list = []
    for text in top50["text"]:
        words = re.findall(r'[a-zA-Z]+', text.lower())
        cleaned = [w for w in words if w not in stop_words and len(w) > 2]
        all_words.extend(cleaned)
        for i in range(len(cleaned) - 1):
            bigrams_list.append(f"{cleaned[i]} {cleaned[i+1]}")
        for i in range(len(cleaned) - 2):
            trigrams_list.append(f"{cleaned[i]} {cleaned[i+1]} {cleaned[i+2]}")

    word_counts = Counter(all_words).most_common(20)
    bigram_counts = Counter(bigrams_list).most_common(10)
    trigram_counts = Counter(trigrams_list).most_common(5)

    # Named entities (rough: capitalized words in original text)
    entities = []
    for text in top50["text"]:
        caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities.extend(caps)
    # Also find $TICKER patterns
    for text in top50["text"]:
        tickers = re.findall(r'\$[A-Z]{2,6}\b', text)
        entities.extend(tickers)
    entity_counts = Counter(entities).most_common(15)

    sections["nouns"] = ", ".join(f"{w} ({c})" for w, c in word_counts[:10])
    sections["verbs"] = "(basic extraction -- full NLP not available)"
    sections["bigrams"] = ", ".join(f'"{b}" ({c})' for b, c in bigram_counts[:8])
    sections["trigrams"] = ", ".join(f'"{t}" ({c})' for t, c in trigram_counts[:5]) if trigram_counts else "N/A"
    sections["entities"] = ", ".join(f"{e} ({c})" for e, c in entity_counts[:10])

    # ── Section 6: Tier comparison ──
    tier_stats = df.groupby("tier").agg(
        avg_rate=("engagement_rate", "mean"),
        handles=("handle", lambda x: list(x.unique())),
    )
    tier_rows = []
    for tier_key in ["conviction_data", "depth_nuance", "irreverent_deadpan", "high_eng_hybrids"]:
        if tier_key not in tier_stats.index:
            continue
        row = tier_stats.loc[tier_key]
        handles_in_tier = row["handles"]
        # Find best and worst
        tier_df = df[df["tier"] == tier_key]
        per_handle = tier_df.groupby("handle")["engagement_rate"].mean()
        best = per_handle.idxmax()
        worst = per_handle.idxmin()
        tier_rows.append(
            f"| {TIER_LABELS[tier_key]} | {row['avg_rate']:.6f} | @{best} | @{worst} |"
        )
    sections["tiers"] = "\n".join(tier_rows)

    # ── Section 7: PBX Voice Laws ──
    # Data-driven rules (NO em dashes per instructions)
    laws = []

    # Rule: questions
    q_full = df["has_question"].mean() * 100
    q_top = top_df["has_question"].mean() * 100
    if q_top > q_full:
        best_q = top_df[top_df["has_question"]].nlargest(1, "engagement_rate")
        ex = best_q.iloc[0]["text"][:120] if len(best_q) > 0 else ""
        laws.append(
            f'**Rule {len(laws)+1}:** Ask questions. They appear in {q_top:.0f}% of top tweets vs {q_full:.0f}% overall. '
            f'Example tweet: "{ex}"'
        )

    # Rule: data/numbers
    d_full = df["has_data"].mean() * 100
    d_top = top_df["has_data"].mean() * 100
    best_d = top_df[top_df["has_data"]].nlargest(1, "engagement_rate")
    ex = best_d.iloc[0]["text"][:120] if len(best_d) > 0 else ""
    if d_top > d_full:
        laws.append(
            f'**Rule {len(laws)+1}:** Lead with data. Numbers appear in {d_top:.0f}% of top tweets vs {d_full:.0f}% overall. '
            f'Example tweet: "{ex}"'
        )
    else:
        laws.append(
            f'**Rule {len(laws)+1}:** Data is a tool, not a crutch. Numbers appear in {d_top:.0f}% of top tweets vs {d_full:.0f}% overall. '
            f'Use them when they hit hard, not to fill space. Example tweet: "{ex}"'
        )

    # Rule: tweet length
    avg_chars_top = top_df["char_count"].mean()
    avg_chars_full = df["char_count"].mean()
    direction = "shorter" if avg_chars_top < avg_chars_full else "longer"
    laws.append(
        f'**Rule {len(laws)+1}:** Top tweets trend {direction}. Top 10% average: {avg_chars_top:.0f} chars vs {avg_chars_full:.0f} overall.'
    )

    # Rule: emoji
    e_full = df["has_emoji"].mean() * 100
    e_top = top_df["has_emoji"].mean() * 100
    if e_top < e_full:
        laws.append(
            f'**Rule {len(laws)+1}:** Skip the emoji. Top tweets use them {e_top:.0f}% of the time vs {e_full:.0f}% overall. '
            f'Let the words carry the weight.'
        )
    else:
        laws.append(
            f'**Rule {len(laws)+1}:** Emoji can work. Top tweets use them {e_top:.0f}% of the time vs {e_full:.0f}% overall.'
        )

    # Rule: profanity
    p_full = df["has_profanity"].mean() * 100
    p_top = top_df["has_profanity"].mean() * 100
    laws.append(
        f'**Rule {len(laws)+1}:** Casual language appears in {p_top:.0f}% of top tweets vs {p_full:.0f}% overall. '
        f'{"Use it sparingly for punch." if p_top > p_full else "Keep it clean for authority."}'
    )

    # Rule: originals vs replies
    o_full = (df["tweet_type"] == "original").mean() * 100
    o_top = (top_df["tweet_type"] == "original").mean() * 100
    laws.append(
        f'**Rule {len(laws)+1}:** Original tweets dominate. {o_top:.0f}% of top tweets are originals vs {o_full:.0f}% overall. '
        f'Post your own takes, not reactions.'
    )

    # Rule: em dash
    if em_yes > em_no * 1.1:
        laws.append(
            f'**Rule {len(laws)+1}:** Use the em dash for rhythm. Tweets with dashes average {em_yes:.6f} engagement vs {em_no:.6f} without.'
        )
    elif em_no > em_yes * 1.1:
        laws.append(
            f'**Rule {len(laws)+1}:** Dashes slow tweets down. Tweets without dashes average {em_no:.6f} engagement vs {em_yes:.6f} with them.'
        )

    # Rule: URL
    u_full = df["has_url"].mean() * 100
    u_top = top_df["has_url"].mean() * 100
    if u_top < u_full:
        laws.append(
            f'**Rule {len(laws)+1}:** Drop the link. URLs appear in {u_top:.0f}% of top tweets vs {u_full:.0f}% overall. '
            f'Twitter deprioritizes external links.'
        )

    # Rule: starts with number
    sn_top = top_df["starts_with_number"].mean() * 100
    sn_full = df["starts_with_number"].mean() * 100
    if sn_top > sn_full * 1.2:
        laws.append(
            f'**Rule {len(laws)+1}:** Open with a number for impact. {sn_top:.0f}% of top tweets start with a digit vs {sn_full:.0f}% overall.'
        )

    sections["laws"] = "\n\n".join(laws)

    # ── Section 8: Example blend tweets ──
    # Find tweets that combine data + casual/humor + depth
    blend_candidates = df[
        (df["has_data"]) & (df["engagement_rate"] > df["engagement_rate"].quantile(0.8))
    ].nlargest(20, "engagement_rate")

    blend_picks = []
    seen_handles = set()
    for _, t in blend_candidates.iterrows():
        if t["handle"] in seen_handles and len(blend_picks) >= 3:
            continue
        seen_handles.add(t["handle"])
        blend_picks.append(t)
        if len(blend_picks) >= 5:
            break

    # Fill if needed
    if len(blend_picks) < 5:
        extras = df.nlargest(20, "engagement_rate")
        for _, t in extras.iterrows():
            if t["handle"] not in seen_handles or len(blend_picks) < 5:
                if t["id"] not in [b["id"] for b in blend_picks]:
                    blend_picks.append(t)
                    seen_handles.add(t["handle"])
            if len(blend_picks) >= 5:
                break

    blend_lines = []
    for i, t in enumerate(blend_picks, 1):
        text = t["text"][:200].replace("\n", " ")
        reasons = []
        if t["has_data"]:
            reasons.append("hard data")
        if t["has_question"]:
            reasons.append("engages with a question")
        if t["has_profanity"]:
            reasons.append("casual tone")
        if t["engagement_rate"] > df["engagement_rate"].quantile(0.95):
            reasons.append("top 5% engagement")
        why = ", ".join(reasons) if reasons else "high engagement and clear conviction"
        blend_lines.append(f'{i}. **@{t["handle"]}**: "{text}" -- Works because: {why}')

    sections["blend"] = "\n\n".join(blend_lines)

    # ── Section 5E: Reply analysis ──
    top_replies = top_df[top_df["tweet_type"].isin(["reply", "quote"])]
    reply_section = f"Top 10% contains {len(top_replies)} replies/quote tweets.\n"
    if len(top_replies) > 0:
        avg_len = top_replies["char_count"].mean()
        reply_section += f"- Average reply length: {avg_len:.0f} chars\n"
        reply_section += f"- {top_replies['has_data'].mean()*100:.0f}% include data points\n"
        reply_section += f"- {top_replies['has_question'].mean()*100:.0f}% include questions\n"
    sections["replies"] = reply_section

    return sections, df


def build_report(sections, df, verified, impressions_available):
    """Build the final markdown report."""
    n_accounts = len(verified)
    n_tweets = len(df)
    date = datetime.now().strftime("%Y-%m-%d")
    failed_str = ", ".join(f"@{h}" for h in failed_handles) if failed_handles else "none"
    api_tier = "Basic" if not impressions_available else "Pro"

    report = f"""# Protocol Pulse Tweet Voice Study
## Data collected: {date}
## Accounts analyzed: {n_accounts} (failed handles: {failed_str})
## Total tweets analyzed: {n_tweets}
## Twitter API tier: {api_tier}

---

## 1. TOP 15 HIGHEST-ENGAGEMENT TWEETS

| Rank | Account | Eng Rate | Likes | RTs | Replies | Text (first 120 chars) | Date |
|------|---------|----------|-------|-----|---------|----------------------|------|
{sections['top15']}

## 2. PER-ACCOUNT ENGAGEMENT RANKING

| Rank | Account | Followers | Avg Eng Rate | Median Eng Rate | Best Tweet Eng Rate |
|------|---------|-----------|-------------|----------------|-------------------|
{sections['per_account']}

## 3. STRUCTURE PATTERNS

### Full Dataset vs Top 10%
| Metric | Full Dataset | Top 10% | Delta |
|--------|-------------|---------|-------|
{sections['structure']}

## 4. STYLE PATTERNS

### Em Dash Correlation
{sections['em_dash']}

### Other Style Metrics
| Metric | Full Dataset | Top 10% |
|--------|-------------|---------|
{sections['style']}

## 5. TONE WORDS (from top 50 tweets)

### Most common nouns: {sections['nouns']}
### Most common verbs: {sections['verbs']}
### Most common bigrams: {sections['bigrams']}
### Most common trigrams: {sections['trigrams']}
### Most common named entities: {sections['entities']}

## 5E. REPLY ANALYSIS (top 10% replies/QTs)

{sections['replies']}

## 6. TIER COMPARISON

| Tier | Avg Eng Rate | Best Account | Worst Account |
|------|-------------|-------------|--------------|
{sections['tiers']}

## 7. PBX VOICE LAWS v1 (Data Edition)

{sections['laws']}

## 8. EXAMPLE TWEETS THAT NAIL THE BLEND

{sections['blend']}
"""
    return report


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("PROTOCOL PULSE TWITTER ENGAGEMENT STUDY")
    print("=" * 60)

    # Step 1
    print("\n--- STEP 1: Handle Verification ---")
    verified = verify_handles()
    if not verified:
        print("No accounts verified. Aborting.")
        sys.exit(1)

    # Step 2
    print("\n--- STEP 2: Tweet Collection ---")
    all_tweets, impressions_available = pull_tweets(verified)

    # Save raw data FIRST
    print(f"\nSaving {len(all_tweets)} tweets to {RAW_FILE}...")
    with open(RAW_FILE, "w") as f:
        json.dump(all_tweets, f, indent=2, default=str)
    print(f"Raw data saved ({os.path.getsize(RAW_FILE):,} bytes)")

    if not all_tweets:
        print("No tweets collected. Check API access.")
        sys.exit(1)

    # Steps 3-4: Analysis
    print("\n--- STEPS 3-4: Scoring & Analysis ---")
    sections, df = analyze(all_tweets)

    # Step 5: Report
    print("\n--- STEP 5: Building Report ---")
    report = build_report(sections, df, verified, impressions_available)
    with open(REPORT_FILE, "w") as f:
        f.write(report)
    print(f"Report saved to {REPORT_FILE}")

    print("\n" + "=" * 60)
    print("STUDY COMPLETE")
    print(f"Total API calls: {call_count}")
    print(f"Total tweets: {len(all_tweets)}")
    print(f"Accounts: {len(verified)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
