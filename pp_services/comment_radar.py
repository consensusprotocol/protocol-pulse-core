import os
import sys
import json
import time
import random
import logging
import hashlib
import re
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DRAFTS_FILE = DATA_DIR / "radar_drafts.json"
CONFIG_FILE = DATA_DIR / "radar_config.json"
POSTED_FILE = DATA_DIR / "radar_posted.json"
LOG_FILE = Path("logs") / "comment_radar.log"
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [RADAR] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
log = logging.getLogger("comment_radar")

X_BASE = "https://api.twitter.com/2"
LIST_TWEETS = X_BASE + "/lists/{list_id}/tweets"
TWEET_SEARCH = X_BASE + "/tweets/search/recent"
USER_LOOKUP = X_BASE + "/users/by/username/{username}"
GROK_URL = "https://api.x.ai/v1/chat/completions"

DEFAULT_CONFIG = {
    "mode": "live",
    "list_id": "",
    "max_posts_per_cycle": 5,
    "min_engagement_velocity": 50,
    "min_comment_likes": 5,
    "max_tweets_per_day": 18,
    "max_replies_per_day": 18,
    "max_quote_tweets_per_day": 3,
    "post_hours_et": [8, 22],
    "confidence_threshold": 0.75,
    "radar_score_threshold": 78,
    "cooldown_minutes": 30,
    "target_accounts": [
        "aantonop", "americanhodl8", "AriDavidPaul", "BarrySilbert",
        "Beautyon_", "BitcoinMagazine", "BitcoinMatrix_", "bitcoinpierre",
        "bitstein", "Breedlove22", "BTCSessions", "c_klippsten",
        "CaitlinLong_", "CasaHODL", "CoinBureau", "CynthiaMLummis",
        "danheld", "dergigi", "DocumentingBTC", "EfratFenigson",
        "ErikVoorhees", "FossGregfoss", "FoundationBTC", "Francispoulliot",
        "GaryCardone", "gavinandresen", "giacomozucco", "gladstein",
        "haydentiff", "intocryptoverse", "jack", "JeffBooth",
        "jimmysong", "knutsvanholm", "LarkDavis", "LukeDashjr",
        "LynAldenContact", "MartyBent", "maxkeiser", "NatBrunell",
        "nic_carter", "NickSzabo4", "nvk", "ODELL",
        "PeterMcCormack", "PrestonPysh", "pwuille", "River",
        "Robin_Seyr", "saaborbtc", "saifedean", "saylor",
        "SimplyBitcoin", "Snowden", "starkness", "Start9Labs",
        "stephanlivera", "TFTC21", "TheBitcoinConf", "TheGuySwann",
        "TheMoonCarl", "ToneVays", "willywoo"
    ],
    "niche_keywords": [
        "bitcoin", "btc", "self-custody", "sovereignty", "decentralization",
        "privacy", "freedom", "censorship", "fiat", "monetary policy",
        "lightning", "mining", "hash rate", "node", "cypherpunk",
        "sound money", "hard money", "proof of work", "store of value",
        "central bank", "cbdc", "surveillance", "permissionless"
    ]
}

BANNED_PHRASES = [
    "bitcoin fixes this", "stay humble, stack sats", "stay humble stack sats",
    "have fun staying poor", "few understand", "this is the way", "bullish",
    "not your keys, not your coins", "not your keys not your coins",
    "tick tock next block", "number go up", "in it for the tech", "ser",
]

GROK_RADAR_PROMPT = """You are the social media voice of Protocol Pulse (@ProtocolPulseHQ), a Bitcoin intelligence platform. You are analyzing a viral tweet and its top comments to write a reply.

YOUR PERSONALITY:
- Sharp, witty, observant. The smartest person in the room who doesn't need to prove it.
- You have genuine opinions and aren't afraid to push back respectfully.
- You sound like a real person, not a brand. Lowercase, casual, direct.
- You deeply understand Bitcoin, macro economics, and internet culture.
- You're allergic to cliches and generic Bitcoin platitudes.

REPLY RULES:
1. Read the tweet carefully. Identify the SPECIFIC point being made.
2. Your reply must engage with THAT specific point, not Bitcoin in general.
3. Add something new: a sharper angle, missing context, a challenge, or humor.
4. Keep it under 180 characters. Ideally under 100. One thought. One punch.
5. Sound human. Use lowercase. Use contractions. No hashtags. No emojis.
6. Bitcoin connection only if genuinely relevant and specific. NOT every reply needs to mention Bitcoin. A sharp cultural observation is better than a forced Bitcoin pivot.
7. NEVER use these phrases: "Bitcoin fixes this", "few understand", "stay humble stack sats", "not your keys not your coins", "tick tock next block", "have fun staying poor", "this is the way", "bullish" (as standalone), or anything that could be a bumper sticker.
8. Match the energy: serious tweet -> thoughtful. funny -> witty. angry -> edgy.
9. If you can't add genuine value, set skip_reason and return empty drafts.
10. NEVER copy comment text. Synthesize and compress.
11. NEVER invent facts, numbers, dates, or prices.
12. NEVER sound like AI. No "It is worth noting" or "This is significant because".

PROCESS:
- Read the top comments. Understand what take resonated most.
- Your reply should be sharper and shorter than the best comment.
- Ask: would the original poster want to reply to THIS? If no, skip.

OUTPUT FORMAT (JSON only, no markdown, no backticks, no extra text):
{
  "crowd_thesis": "one line - what do the top comments agree on",
  "counterpoint": "notable dissent or none",
  "risk_flags": [],
  "skip_reason": "",
  "drafts": [
    {
      "voice": "sharp",
      "tweet": "the reply text",
      "reply_or_quote": "reply",
      "confidence": 0.85,
      "reasoning": "2-3 words why this adds value"
    }
  ]
}

Generate 1 high-quality draft. Quality over quantity. If the tweet doesn't warrant a reply, set skip_reason and return empty drafts array."""


def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

def get_config():
    cfg = load_json(CONFIG_FILE, DEFAULT_CONFIG.copy())
    for k, v in DEFAULT_CONFIG.items():
        if k not in cfg:
            cfg[k] = v
    return cfg

def save_config(cfg):
    save_json(CONFIG_FILE, cfg)

def get_x_headers():
    token = os.environ.get("TWITTER_BEARER_TOKEN", "")
    if not token:
        raise ValueError("TWITTER_BEARER_TOKEN not set")
    return {"Authorization": "Bearer " + token}

def get_grok_key():
    key = os.environ.get("XAI_API_KEY", "")
    if not key:
        raise ValueError("XAI_API_KEY not set")
    return key

def is_within_post_hours(cfg):
    utc_now = datetime.now(timezone.utc)
    et_offset = timedelta(hours=-5)
    et_now = utc_now + et_offset
    return cfg["post_hours_et"][0] <= et_now.hour < cfg["post_hours_et"][1]

def daily_post_count():
    posted = load_json(POSTED_FILE, {"date": "", "posts": []})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if posted.get("date") != today:
        return 0
    return len(posted.get("posts", []))

def record_post(tweet_id, post_type, source_url, tweet_text):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    posted = load_json(POSTED_FILE, {"date": "", "posts": []})
    if posted.get("date") != today:
        posted = {"date": today, "posts": []}
    posted["posts"].append({
        "tweet_id": tweet_id, "type": post_type,
        "source": source_url, "text": tweet_text,
        "time": datetime.now(timezone.utc).isoformat()
    })
    save_json(POSTED_FILE, posted)

def engagement_velocity(post_metrics, minutes_since_post):
    if minutes_since_post < 1:
        minutes_since_post = 1
    likes = post_metrics.get("like_count", 0)
    rts = post_metrics.get("retweet_count", 0)
    replies = post_metrics.get("reply_count", 0)
    raw = (likes * 1.0) + (rts * 1.5) + (replies * 2.0)
    return round((raw / minutes_since_post) * 60, 1)

def radar_score(confidence, velocity, comment_consensus, char_count):
    score = 0
    score += min(confidence * 30, 30)
    score += min((velocity / 500) * 25, 25)
    score += min(comment_consensus * 25, 25)
    if char_count <= 100:
        score += 20
    elif char_count <= 140:
        score += 17
    elif char_count <= 180:
        score += 12
    elif char_count <= 220:
        score += 7
    else:
        score += 3
    return round(score, 1)

def contains_banned_phrase(text):
    """Return True if text contains any banned phrase from the V5 overhaul list."""
    lower = (text or "").lower().strip()
    return any(phrase in lower for phrase in BANNED_PHRASES)


def humanize_tweet(text):
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0\U000024C2-\U0001F251"
        "\u2640-\u2642\u2600-\u2B55\u200d\u23cf"
        "\u23e9\u231a\ufe0f\u3030]+", flags=re.UNICODE)
    text = emoji_pattern.sub("", text).strip()
    ai_hooks = [r"^BREAKING:\s*", r"^BREAKING\s*[-:]\s*", r"^INTEL BRIEF:\s*",
                r"^Check out\s*", r"^Don.t miss\s*", r"^Here.s why\s*"]
    for hook in ai_hooks:
        text = re.sub(hook, "", text, flags=re.IGNORECASE)
    text = re.sub(r"#\w+", "", text).strip()
    text = re.sub(r"\s{2,}", " ", text).strip()
    if text and random.random() < 0.20:
        text = text[0].lower() + text[1:]
    if text and text.endswith(".") and random.random() < 0.15:
        text = text[:-1]
    # V5 Overhaul: cap at 180 chars
    if len(text) > 180:
        text = text[:177] + "..."
    return text.strip()


class XRadarClient:
    def __init__(self):
        self.headers = get_x_headers()
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_list_tweets(self, list_id, max_results=50):
        url = LIST_TWEETS.format(list_id=list_id)
        params = {"max_results": min(max_results, 100),
                  "tweet.fields": "public_metrics,created_at,conversation_id,author_id",
                  "user.fields": "username,name", "expansions": "author_id"}
        try:
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            log.error("List API error %s: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            log.error("List request failed: %s", e)
        return None

    def search_niche_tweets(self, keywords, max_results=20):
        sample = random.sample(keywords, min(3, len(keywords)))
        query = " OR ".join(sample) + " -is:retweet lang:en"
        params = {"query": query, "max_results": min(max_results, 100),
                  "tweet.fields": "public_metrics,created_at,conversation_id,author_id",
                  "user.fields": "username,name", "expansions": "author_id",
                  "sort_order": "relevancy"}
        try:
            resp = self.session.get(TWEET_SEARCH, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            log.error("Search API error %s: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            log.error("Search failed: %s", e)
        return None

    def get_conversation_replies(self, conversation_id, max_results=30):
        query = "conversation_id:" + str(conversation_id) + " -is:retweet"
        params = {"query": query, "max_results": min(max_results, 100),
                  "tweet.fields": "public_metrics,created_at,author_id",
                  "user.fields": "username,name", "expansions": "author_id",
                  "sort_order": "relevancy"}
        try:
            resp = self.session.get(TWEET_SEARCH, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            log.error("Conversation API error %s: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            log.error("Conversation failed: %s", e)
        return None

    def get_user_tweets(self, username, max_results=10):
        try:
            resp = self.session.get(USER_LOOKUP.format(username=username), timeout=10)
            if resp.status_code != 200:
                return None
            user_id = resp.json().get("data", {}).get("id")
            if not user_id:
                return None
        except Exception:
            return None
        url = X_BASE + "/users/" + user_id + "/tweets"
        params = {"max_results": min(max_results, 100),
                  "tweet.fields": "public_metrics,created_at,conversation_id",
                  "exclude": "retweets,replies"}
        try:
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for tweet in data.get("data", []):
                    tweet["_author_username"] = username
                return data
        except Exception:
            pass
        return None


class GrokRadar:
    def __init__(self):
        self.api_key = get_grok_key()

    def synthesize(self, post_text, post_author, top_comments):
        comment_block = ""
        for i, c in enumerate(top_comments[:15], 1):
            comment_block += str(i) + ". @" + c.get("author", "?") + " (" + str(c.get("likes", 0)) + " likes): " + c["text"] + "\n"
        if not comment_block.strip():
            comment_block = "(No significant comments found yet)"
        user_prompt = 'VIRAL POST by @' + post_author + ':\n"' + post_text + '"\n\nTOP COMMENTS (sorted by likes):\n' + comment_block + '\nAnalyze the comment sentiment and generate mirror tweet drafts. Remember: SUGGESTIVE over DECLARATIVE. Questions and implications over statements. Return valid JSON only.'
        try:
            resp = requests.post(GROK_URL,
                headers={"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"},
                json={"model": "grok-3-latest",
                      "messages": [{"role": "system", "content": GROK_RADAR_PROMPT},
                                   {"role": "user", "content": user_prompt}],
                      "temperature": 0.8, "max_tokens": 1500}, timeout=30)
            if resp.status_code != 200:
                log.error("Grok API error %s: %s", resp.status_code, resp.text[:200])
                return None
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]
            return json.loads(raw.strip())
        except json.JSONDecodeError as e:
            log.error("Grok invalid JSON: %s", e)
        except Exception as e:
            log.error("Grok failed: %s", e)
        return None


class CommentRadar:
    def __init__(self):
        self.cfg = get_config()
        self.x_client = XRadarClient()
        self.grok = GrokRadar()
        self._processed_ids = set()
        self._load_processed()

    def _load_processed(self):
        drafts = load_json(DRAFTS_FILE, {"drafts": []})
        for d in drafts.get("drafts", []):
            self._processed_ids.add(d.get("source_post_id", ""))
        posted = load_json(POSTED_FILE, {"posts": []})
        for p in posted.get("posts", []):
            self._processed_ids.add(p.get("source", ""))

    def _build_user_map(self, api_response):
        user_map = {}
        if api_response and "includes" in api_response:
            for user in api_response["includes"].get("users", []):
                user_map[user["id"]] = user.get("username", "unknown")
        return user_map

    def fetch_candidates(self):
        candidates = []
        if self.cfg.get("list_id"):
            log.info("Scanning List %s...", self.cfg["list_id"])
            data = self.x_client.get_list_tweets(self.cfg["list_id"])
            if data and "data" in data:
                user_map = self._build_user_map(data)
                for tweet in data["data"]:
                    tweet["_author_username"] = user_map.get(tweet.get("author_id"), "unknown")
                    candidates.append(tweet)
                log.info("Found %d posts from List", len(candidates))
        if len(candidates) < 10:
            accounts = self.cfg.get("target_accounts", [])
            sample = random.sample(accounts, min(12, len(accounts)))
            for username in sample:
                log.info("Scanning @%s...", username)
                data = self.x_client.get_user_tweets(username, max_results=10)
                if data and "data" in data:
                    candidates.extend(data["data"])
                time.sleep(1)
        if len(candidates) < 5:
            log.info("Supplementing with keyword search...")
            data = self.x_client.search_niche_tweets(self.cfg["niche_keywords"])
            if data and "data" in data:
                user_map = self._build_user_map(data)
                for tweet in data["data"]:
                    tweet["_author_username"] = user_map.get(tweet.get("author_id"), "unknown")
                    candidates.append(tweet)
        log.info("Total candidates: %d", len(candidates))
        return candidates

    def rank_candidates(self, candidates):
        scored = []
        for tweet in candidates:
            post_id = tweet.get("id", "")
            if post_id in self._processed_ids:
                continue
            metrics = tweet.get("public_metrics", {})
            created = tweet.get("created_at", "")
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                age_minutes = (datetime.now(timezone.utc) - created_dt).total_seconds() / 60
            except Exception:
                age_minutes = 120
            if age_minutes > 1440:
                continue
            velocity = engagement_velocity(metrics, age_minutes)
            total_engagement = metrics.get("like_count", 0) + metrics.get("retweet_count", 0)
            if total_engagement < self.cfg["min_engagement_velocity"]:
                continue
            if metrics.get("reply_count", 0) < 3:
                continue
            ptl = tweet.get("text", "").lower()
            alts = ["solana", "sol ", "ethereum", "eth ", "dogecoin", "doge ",
                    "shiba", "pepe", "memecoin", "airdrop", "presale",
                    "xrp", "cardano", "ada ", "litecoin", "ltc "]
            btcs = ["bitcoin", "btc", "satoshi", "self-custody", "sovereignty",
                    "freedom", "privacy", "decentrali", "lightning", "mining",
                    "hash rate", "proof of work", "sound money", "fiat",
                    "central bank", "cbdc", "censorship"]
            if any(a in ptl for a in alts) and not any(b in ptl for b in btcs):
                continue
            scored.append({
                "id": post_id, "text": tweet.get("text", ""),
                "author": tweet.get("_author_username", "unknown"),
                "conversation_id": tweet.get("conversation_id", post_id),
                "metrics": metrics, "velocity": velocity,
                "age_minutes": round(age_minutes), "created_at": created
            })
        scored.sort(key=lambda x: x["velocity"], reverse=True)
        top = scored[:self.cfg["max_posts_per_cycle"]]
        log.info("Top %d candidates by velocity", len(top))
        return top

    def extract_comments(self, post):
        conv_id = post["conversation_id"]
        log.info("Fetching comments for conversation %s...", conv_id)
        data = self.x_client.get_conversation_replies(conv_id)
        if not data or "data" not in data:
            log.warning("No comments found for %s", conv_id)
            return []
        user_map = self._build_user_map(data)
        comments = []
        for reply in data["data"]:
            likes = reply.get("public_metrics", {}).get("like_count", 0)
            if likes < self.cfg["min_comment_likes"]:
                continue
            comments.append({"text": reply.get("text", ""), "likes": likes,
                             "author": user_map.get(reply.get("author_id"), "anon"),
                             "id": reply.get("id", "")})
        comments.sort(key=lambda x: x["likes"], reverse=True)
        top = comments[:15]
        log.info("Found %d quality comments, using top %d", len(comments), len(top))
        return top

    def synthesize_drafts(self, post, comments):
        log.info("Synthesizing drafts for @%s post...", post["author"])
        result = self.grok.synthesize(post["text"], post["author"], comments)
        if not result:
            log.warning("Grok returned no result")
            return None
        # V5 Overhaul: handle skip_reason / NO_REPLY
        if result.get("skip_reason"):
            log.info("Grok chose to skip: %s", result["skip_reason"])
            return None
        if not result.get("drafts"):
            log.warning("Grok returned no drafts (NO_REPLY)")
            return None
        # Filter out any drafts containing banned phrases
        clean_drafts = []
        for draft in result["drafts"]:
            tweet_text = draft.get("tweet", "")
            if not tweet_text:
                continue
            # Check for NO_REPLY in draft text
            if tweet_text.strip().upper() in ("NO_REPLY", "NO REPLY"):
                log.info("Draft returned NO_REPLY, skipping")
                continue
            if contains_banned_phrase(tweet_text):
                log.info("Draft contains banned phrase, filtering: %s", tweet_text[:80])
                continue
            consensus = draft.get("confidence", 0.5)
            draft["radar_score"] = radar_score(draft.get("confidence", 0.5),
                                               post["velocity"], consensus, len(tweet_text))
            draft["tweet_raw"] = tweet_text
            draft["tweet"] = humanize_tweet(tweet_text)
            # Final banned phrase check after humanization
            if contains_banned_phrase(draft["tweet"]):
                log.info("Draft contains banned phrase after humanize, filtering: %s", draft["tweet"][:80])
                continue
            clean_drafts.append(draft)
        result["drafts"] = clean_drafts
        if not clean_drafts:
            log.info("All drafts filtered out (banned phrases or NO_REPLY)")
            return None
        log.info("Generated %d clean drafts. Scores: %s", len(result["drafts"]),
                 [d["radar_score"] for d in result["drafts"]])
        return result

    def _authors_posted_today(self):
        """Return set of authors we've already replied to today."""
        posted = load_json(POSTED_FILE, {"date": "", "posts": []})
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if posted.get("date") != today:
            return set()
        authors = set()
        for p in posted.get("posts", []):
            src = (p.get("source") or "").lower()
            if src:
                authors.add(src)
        return authors

    def process_drafts(self, post, analysis):
        if not analysis or not analysis.get("drafts"):
            return
        mode = self.cfg.get("mode", "dry_run")
        threshold = self.cfg["radar_score_threshold"]
        viable = [d for d in analysis["drafts"] if d["radar_score"] >= threshold]
        if not viable:
            best_score = max(d["radar_score"] for d in analysis["drafts"])
            log.info("No drafts above threshold (%s). Best: %s", threshold, best_score)
            self._save_draft(post, analysis, selected=None, status="below_threshold")
            return
        best = max(viable, key=lambda d: d["radar_score"])
        # V5 Overhaul: no same author twice per day
        replied_authors = self._authors_posted_today()
        if post.get("author", "").lower() in replied_authors:
            log.info("Already replied to @%s today, skipping", post["author"])
            self._save_draft(post, analysis, selected=best, status="author_limit")
            return
        if mode == "dry_run":
            log.info("[DRY RUN] Would post (%s): %s", best.get("voice", "sharp"), best["tweet"])
            log.info("  Score: %s | Confidence: %s", best["radar_score"], best["confidence"])
            log.info("  Type: %s to @%s", best["reply_or_quote"], post["author"])
            self._save_draft(post, analysis, selected=best, status="pending_review")
        elif mode == "live":
            today_count = daily_post_count()
            if today_count >= self.cfg["max_tweets_per_day"]:
                log.info("Daily limit reached (%d/%d)", today_count, self.cfg["max_tweets_per_day"])
                self._save_draft(post, analysis, selected=best, status="daily_limit")
                return
            if not is_within_post_hours(self.cfg):
                log.info("Outside posting hours, queuing")
                self._save_draft(post, analysis, selected=best, status="outside_hours")
                return
            success = self._post_tweet(best, post)
            self._save_draft(post, analysis, selected=best,
                             status="posted" if success else "post_failed")

    def _post_tweet(self, draft, source_post):
        try:
            try:
                from pp_services.x_service import post_tweet, reply_to_tweet, quote_tweet
            except ImportError:
                try:
                    from pp_services.x_automation_service import post_to_x
                    def reply_to_tweet(pid, txt): return post_to_x(txt, reply_to=pid)
                    def quote_tweet(txt, url): return post_to_x(txt + " " + url)
                    post_tweet = post_to_x
                except ImportError:
                    log.error("Could not import X posting service")
                    return False
            tweet_text = draft["tweet"]
            post_type = draft.get("reply_or_quote", "reply")
            post_id = source_post["id"]
            if post_type == "reply":
                result = reply_to_tweet(post_id, tweet_text)
            elif post_type == "quote":
                post_url = "https://x.com/" + source_post["author"] + "/status/" + post_id
                result = quote_tweet(tweet_text, post_url)
            else:
                result = post_tweet(tweet_text)
            if result:
                tweet_id = result.get("id", "unknown") if isinstance(result, dict) else "unknown"
                record_post(tweet_id, post_type, post_id, tweet_text)
                log.info("POSTED: %s", tweet_text[:80])
                return True
            log.error("Post returned no result")
            return False
        except Exception as e:
            log.error("Failed to post: %s", e)
            return False

    def _save_draft(self, post, analysis, selected, status):
        drafts = load_json(DRAFTS_FILE, {"drafts": []})
        entry = {
            "id": "radar_" + str(int(time.time())) + "_" + str(random.randint(100, 999)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "source_post_id": post["id"],
            "source_author": post["author"],
            "source_text": post["text"][:300],
            "source_url": "https://x.com/" + post["author"] + "/status/" + post["id"],
            "velocity": post["velocity"],
            "crowd_thesis": analysis.get("crowd_thesis", ""),
            "counterpoint": analysis.get("counterpoint", ""),
            "risk_flags": analysis.get("risk_flags", []),
            "all_drafts": [{"voice": d.get("voice", "unknown"), "tweet": d.get("tweet", ""),
                            "tweet_raw": d.get("tweet_raw", ""),
                            "reply_or_quote": d.get("reply_or_quote", "reply"),
                            "confidence": d.get("confidence", 0),
                            "radar_score": d.get("radar_score", 0),
                            "reasoning": d.get("reasoning", "")}
                           for d in analysis.get("drafts", [])],
            "selected": {"voice": selected.get("voice", ""),
                         "tweet": selected.get("tweet", ""),
                         "radar_score": selected.get("radar_score", 0),
                         "reply_or_quote": selected.get("reply_or_quote", "reply")
                         } if selected else None
        }
        drafts["drafts"].insert(0, entry)
        drafts["drafts"] = drafts["drafts"][:200]
        save_json(DRAFTS_FILE, drafts)
        self._processed_ids.add(post["id"])

    def run_cycle(self):
        # Auto go-live check
        go_live_at = self.cfg.get("go_live_at", "")
        if go_live_at and self.cfg.get("mode") == "dry_run":
            try:
                from datetime import datetime, timezone
                target = datetime.fromisoformat(go_live_at)
                if datetime.now(timezone.utc) >= target:
                    self.cfg["mode"] = "live"
                    self.cfg.pop("go_live_at", None)
                    save_config(self.cfg)
                    log.info("AUTO GO-LIVE TRIGGERED - switching to LIVE mode")
            except Exception:
                pass

        log.info("=" * 60)
        log.info("COMMENT RADAR v1.2 CYCLE - Mode: %s", self.cfg.get("mode", "dry_run").upper())
        log.info("=" * 60)
        candidates = self.fetch_candidates()
        if not candidates:
            log.info("No candidates found.")
            return {"processed": 0, "drafts_generated": 0}
        top_posts = self.rank_candidates(candidates)
        if not top_posts:
            log.info("No posts above engagement threshold.")
            return {"processed": 0, "drafts_generated": 0}
        processed = 0
        drafts_generated = 0
        for post in top_posts:
            log.info("--- Processing @%s (velocity: %s) ---", post["author"], post["velocity"])
            log.info("Post: %s...", post["text"][:120])
            comments = self.extract_comments(post)
            if len(comments) < 2:
                log.info("Not enough quality comments, skipping")
                continue
            analysis = self.synthesize_drafts(post, comments)
            if not analysis:
                continue
            self.process_drafts(post, analysis)
            processed += 1
            drafts_generated += len(analysis.get("drafts", []))
            time.sleep(2)
        log.info("Cycle complete: %d posts, %d drafts", processed, drafts_generated)
        return {"processed": processed, "drafts_generated": drafts_generated}


def cmd_scan():
    radar = CommentRadar()
    result = radar.run_cycle()
    print("\nScan complete: " + str(result["processed"]) + " processed, " + str(result["drafts_generated"]) + " drafts")
    print("Review: python3 services/comment_radar.py drafts")

def cmd_drafts():
    data = load_json(DRAFTS_FILE, {"drafts": []})
    drafts = data.get("drafts", [])
    if not drafts:
        print("No drafts yet. Run: python3 services/comment_radar.py scan")
        return
    print("\n" + "=" * 70)
    print("COMMENT RADAR v1.2 - DRAFT REVIEW (" + str(len(drafts)) + " total)")
    print("=" * 70 + "\n")
    for d in drafts[:20]:
        status_map = {"pending_review": "[REVIEW]", "posted": "[POSTED]",
                      "below_threshold": "[LOW SCORE]", "daily_limit": "[LIMIT]",
                      "outside_hours": "[QUEUED]", "post_failed": "[FAILED]"}
        print(status_map.get(d["status"], "[" + d["status"] + "]") + " " + d["timestamp"][:16])
        print("   Source: @" + d["source_author"] + " (velocity: " + str(d["velocity"]) + ")")
        print("   Post: " + d["source_text"][:100] + "...")
        print("   Crowd thesis: " + d["crowd_thesis"])
        print("   URL: " + d["source_url"])
        if d.get("all_drafts"):
            print("   Drafts:")
            for draft in d["all_drafts"]:
                sel = ""
                if d.get("selected") and draft["voice"] == d["selected"].get("voice"):
                    sel = " << BEST"
                print("      [" + draft["voice"].upper() + "] (score: " + str(draft["radar_score"]) + ") " + draft["tweet"][:120] + sel)
        if d.get("risk_flags") and d["risk_flags"] != ["none"]:
            print("   RISK: " + ", ".join(str(r) for r in d["risk_flags"]))
        print()
    mode = get_config().get("mode", "dry_run")
    print("Current mode: " + mode.upper())
    if mode == "dry_run":
        print("Go live: python3 services/comment_radar.py golive")

def cmd_golive():
    cfg = get_config()
    cfg["mode"] = "live"
    save_config(cfg)
    print("LIVE MODE ACTIVATED")
    print("  Daily limit: " + str(cfg["max_tweets_per_day"]))
    print("  Score threshold: " + str(cfg["radar_score_threshold"]))

def cmd_dryrun():
    cfg = get_config()
    cfg["mode"] = "dry_run"
    save_config(cfg)
    print("DRY RUN MODE - tweets logged but NOT posted")

def cmd_setlist(list_id):
    cfg = get_config()
    cfg["list_id"] = list_id
    save_config(cfg)
    print("List ID set to: " + list_id)

def cmd_stats():
    data = load_json(DRAFTS_FILE, {"drafts": []})
    posted = load_json(POSTED_FILE, {"date": "", "posts": []})
    drafts = data.get("drafts", [])
    by_status = {}
    by_voice = {}
    scores = []
    for d in drafts:
        s = d.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1
        if d.get("selected"):
            v = d["selected"].get("voice", "unknown")
            by_voice[v] = by_voice.get(v, 0) + 1
            if d["selected"].get("radar_score"):
                scores.append(d["selected"]["radar_score"])
    print("\n" + "=" * 50)
    print("COMMENT RADAR STATS")
    print("=" * 50)
    print("Total drafts: " + str(len(drafts)))
    print("Today posts: " + str(len(posted.get("posts", []))))
    for s, c in sorted(by_status.items()):
        print("  " + s + ": " + str(c))
    for v, c in sorted(by_voice.items()):
        print("  " + v + ": " + str(c))
    if scores:
        print("Avg score: " + str(round(sum(scores)/len(scores), 1)))
    print("Mode: " + get_config().get("mode", "dry_run").upper())

def cmd_clear():
    save_json(DRAFTS_FILE, {"drafts": []})
    print("Draft queue cleared")

def cmd_config():
    print(json.dumps(get_config(), indent=2))

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 services/comment_radar.py scan")
        print("  python3 services/comment_radar.py drafts")
        print("  python3 services/comment_radar.py golive")
        print("  python3 services/comment_radar.py dryrun")
        print("  python3 services/comment_radar.py setlist <ID>")
        print("  python3 services/comment_radar.py stats")
        print("  python3 services/comment_radar.py config")
        print("  python3 services/comment_radar.py clear")
        return
    cmd = sys.argv[1].lower()
    if cmd == "scan": cmd_scan()
    elif cmd == "drafts": cmd_drafts()
    elif cmd == "golive": cmd_golive()
    elif cmd == "dryrun": cmd_dryrun()
    elif cmd == "setlist":
        if len(sys.argv) < 3:
            print("Usage: python3 services/comment_radar.py setlist <LIST_ID>")
        else:
            cmd_setlist(sys.argv[2])
    elif cmd == "stats": cmd_stats()
    elif cmd == "config": cmd_config()
    elif cmd == "clear": cmd_clear()
    else: print("Unknown command: " + cmd)

if __name__ == "__main__":
    main()
