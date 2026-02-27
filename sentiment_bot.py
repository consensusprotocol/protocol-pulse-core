import time
#!/usr/bin/env python3
import os, random, time, tweepy
from datetime import datetime
from openai import OpenAI

# Rate limiting for statement tweets
SENTIMENT_DAILY_LIMIT = 2
SENTIMENT_POSTS_FILE = "data/sentiment_posts.json"

def _check_sentiment_rate_limit():
    """Check if we can post another sentiment tweet today"""
    import json
    import os
    from datetime import datetime
    
    os.makedirs("data", exist_ok=True)
    
    if os.path.exists(SENTIMENT_POSTS_FILE):
        with open(SENTIMENT_POSTS_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {"daily_posts": {}}
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    count = data.get("daily_posts", {}).get(today, 0)
    
    return count < SENTIMENT_DAILY_LIMIT, count

def _record_sentiment_post():
    """Record that we posted a sentiment tweet"""
    import json
    import os
    from datetime import datetime
    
    os.makedirs("data", exist_ok=True)
    
    if os.path.exists(SENTIMENT_POSTS_FILE):
        with open(SENTIMENT_POSTS_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {"daily_posts": {}}
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if "daily_posts" not in data:
        data["daily_posts"] = {}
    data["daily_posts"][today] = data["daily_posts"].get(today, 0) + 1
    
    with open(SENTIMENT_POSTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)




# Operating hours: 10 AM - 6 PM Eastern Time (UTC-5)
POSTING_START_HOUR_UTC = 15  # 10 AM ET in UTC
POSTING_END_HOUR_UTC = 23    # 6 PM ET in UTC

def _is_within_posting_hours():
    """Check if current time is within 10am-6pm ET"""
    now_utc = datetime.utcnow()
    current_hour = now_utc.hour
    return POSTING_START_HOUR_UTC <= current_hour < POSTING_END_HOUR_UTC

def _get_todays_post_count():
    """Get how many sentiment tweets posted today"""
    import json
    os.makedirs("data", exist_ok=True)
    if os.path.exists(SENTIMENT_POSTS_FILE):
        try:
            with open(SENTIMENT_POSTS_FILE, 'r') as f:
                data = json.load(f)
        except:
            data = {"daily_posts": {}}
    else:
        data = {"daily_posts": {}}
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return data.get("daily_posts", {}).get(today, 0)

def _should_post_now():
    """Check if we should post now based on hours, limit, and randomization"""
    if not _is_within_posting_hours():
        return False, "Outside hours (10am-6pm ET)"
    
    count = _get_todays_post_count()
    if count >= SENTIMENT_DAILY_LIMIT:
        return False, f"Limit reached ({count}/{SENTIMENT_DAILY_LIMIT})"
    
    # Random probability: 25% if 0 posts, 15% if 1 post
    prob = 0.25 if count == 0 else 0.15
    if random.random() > prob:
        return False, f"Random skip ({int(prob*100)}%)"
    
    return True, "Posting"

THOUGHT_LEADERS = ["saylor", "NatBrunell", "DocumentingBTC", "BitcoinMagazine", "maxkeiser", "APompliano", "aantonop", "ODELL", "dergigi", "jimmysong", "PrestonPysh", "stephanlivera", "adam3us", "excellion", "Breedlove22", "LynAldenContact", "jackmallers", "balajis", "naval", "RaoulGMI", "WClementeIII", "woonomic", "gladstein", "MartyBent", "TheBitcoinLayer", "BitcoinPierre", "francispouliot_", "CaitlinLong_", "SwanBitcoin", "WhatBitcoinDid", "BTCsessions", "PeterMcCormack", "americanhodl", "nvk", "100trillionUSD", "TuurDemeester"]

def get_twitter_read():
    return tweepy.Client(bearer_token=os.getenv("TWITTER_BEARER_TOKEN"))

def get_twitter_write():
    return tweepy.Client(consumer_key=os.getenv("TWITTER_API_KEY"), consumer_secret=os.getenv("TWITTER_API_SECRET"), access_token=os.getenv("TWITTER_ACCESS_TOKEN"), access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"))

def get_grok():
    key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
    return OpenAI(api_key=key, base_url="https://api.x.ai/v1") if key else None

def get_news_fallback():
    grok = get_grok()
    if grok:
        try:
            r = grok.chat.completions.create(model="grok-3", messages=[{"role":"user","content":f"What are 5 specific things being discussed on Bitcoin Twitter TODAY {datetime.now().strftime('%B %d, %Y')}? Focus on macro, adoption, regulation, freedom, monetary policy."}], max_tokens=300)
            return [l.strip().lstrip('•-0123456789.) ') for l in r.choices[0].message.content.strip().split('\n') if l.strip()][:5]
        except Exception as e:
            print(f"  Grok error: {e}")
    return None

def scan_leaders():
    client = get_twitter_read()
    tweets = []
    print(f"[{datetime.now()}] Scanning thought leaders...")
    random.shuffle(THOUGHT_LEADERS)
    for handle in THOUGHT_LEADERS[:20]:
        try:
            user = client.get_user(username=handle)
            if user.data:
                result = client.get_users_tweets(id=user.data.id, max_results=5, tweet_fields=["public_metrics","text"], exclude=["retweets","replies"])
                if result.data:
                    for t in result.data:
                        tweets.append({"handle":handle, "text":t.text, "engagement":t.public_metrics.get("like_count",0)+t.public_metrics.get("retweet_count",0)*2})
            time.sleep(1)
        except Exception as e:
            if "429" in str(e): break
    print(f"  Got {len(tweets)} tweets")
    return tweets

def get_themes(tweets):
    if not tweets: return None
    sorted_t = sorted(tweets, key=lambda x:x["engagement"], reverse=True)
    themes = []
    for t in sorted_t[:15]:
        if len(t["text"])>30 and not t["text"].startswith("http"):
            themes.append(f"@{t['handle']}: {t['text'][:150]}")
        if len(themes)>=5: break
    return themes if themes else None

def fact_check(tweet):
    grok = get_grok()
    if not grok:
        return True, tweet
    print("  Fact-checking...")
    try:
        r = grok.chat.completions.create(model="grok-3", messages=[{"role":"user","content":f"""Check for MAJOR factual errors only. Tweet: {tweet}
IGNORE opinions, analysis, macro takes. ONLY flag clearly wrong facts.
Reply "ACCURATE" or "INACCURATE: [reason]"."""}], max_tokens=80)
        result = r.choices[0].message.content.strip()
        if "INACCURATE" not in result.upper():
            print("  ✅ Verified")
            return True, tweet
        print(f"  ⚠️ {result[:60]}")
        return False, result
    except Exception as e:
        return True, tweet

def generate_tweet(themes=None):
    """
    Generate ONE high-energy tweet.
    If thought leader tweets are available, channel the best one.
    Otherwise use themes as fallback, but with maximum conviction.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # ── Strategy 1: Channel a specific high-performing tweet ──
    raw_tweets = getattr(generate_tweet, '_cached_tweets', None)
    if raw_tweets is None:
        raw_tweets = scan_leaders()
        generate_tweet._cached_tweets = raw_tweets
    if not raw_tweets:
        raw_tweets = getattr(generate_tweet, '_cached_tweets', None)
    if raw_tweets is None:
        raw_tweets = scan_leaders()
        generate_tweet._cached_tweets = raw_tweets

    if raw_tweets:
        # Sort by engagement, pick the best unused one
        used_file = "logs/used_tweets.json"
        os.makedirs("logs", exist_ok=True)
        used = {}
        if os.path.exists(used_file):
            try:
                used = json.loads(open(used_file).read())
            except:
                used = {}

        # Clean entries older than 48h
        import time as _time
        cutoff = _time.time() - (48 * 3600)
        used = {k: v for k, v in used.items() if v > cutoff}

        available = [t for t in raw_tweets if t.get("id", t.get("text", "")[:50]) not in used]
        if not available:
            used = {}
            available = raw_tweets

        best = sorted(available, key=lambda x: x.get("engagement", 0), reverse=True)

        if best:
            source = best[0]
            author = source.get("author", source.get("username", "unknown"))
            text = source.get("text", "")
            likes = source.get("likes", source.get("engagement", 0))
            retweets = source.get("retweets", 0)
            replies = source.get("replies", 0)

            # Mark as used
            key = source.get("id", text[:50])
            used[key] = _time.time()
            try:
                open(used_file, "w").write(json.dumps(used))
            except:
                pass

            prompt = f"""You are ghostwriting a tweet for Protocol Pulse, a Bitcoin-maximalist media brand run by a cypherpunk who believes in financial sovereignty, Austrian economics, and signal over noise.

Here is a high-performing tweet from Bitcoin Twitter right now:

AUTHOR: @{author}
TEXT: "{text}"
ENGAGEMENT: {likes} likes, {retweets} retweets, {replies} replies

Your job: Write ONE original tweet that captures the SAME energy, conviction, and specificity of this post — but in Protocol Pulse's own voice. Do NOT summarize. Do NOT water down. Channel the same intensity and take a clear position.

RULES:
- Match the emotional register (angry = angry, data-driven = use data, sarcastic = match it)
- Be SPECIFIC — use numbers, names, events, dollar amounts when possible
- Take a POSITION — never hedge with "hints at" or "could mean" or "seems like"
- Max 2 sentences. Under 200 characters preferred, 280 absolute max.
- No hashtags
- No emojis
- Sound like a human with strong opinions who has been in Bitcoin for years
- If the original makes a bold claim, make an equally bold or bolder claim
- NEVER invent specific numbers, prices, or dates. Only use numbers if they appeared in the source tweet. If unsure, keep it qualitative.
- Write like someone who reads Mises, runs a mining operation, and hosts a podcast
- One voice, one take, full conviction

BAD examples (NEVER write like this):
- "quiet accumulation hints at a deeper shift in how value is stored"
- "interesting developments suggest growing institutional interest"
- "the landscape continues to evolve in meaningful ways"
- "Bitcoin defends individual sovereignty in a world that thrives on control"
- "Bitcoin's security budget is a barometer of trust in decentralized finance"

GOOD examples (THIS is the energy):
- "MicroStrategy added 12,000 BTC while CNBC debates if it's a bubble. The scoreboard doesn't care about your opinion."
- "The Fed printed $3T in 18 months. Bitcoin's supply schedule didn't flinch. That's the whole thesis."
- "Nation-states are mining Bitcoin with subsidized energy while your congressman still thinks it's used for drugs."
- "You don't need a 200-page report to understand Bitcoin. The money printer goes brr. There are only 21 million. End of story."
- "BlackRock now holds more Bitcoin than El Salvador. Tell me again how institutions aren't taking this seriously."

Output ONLY the tweet text. Nothing else. No quotes. No commentary."""

            print(f"  Source: @{author} — {text[:80]}...")

            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.9
                )
                tweet = response.choices[0].message.content.strip().strip('"').strip("'").strip()
                if len(tweet) > 280:
                    tweet = tweet[:277] + "..."
                return tweet
            except Exception as e:
                print(f"  GPT error: {e}")

    # ── Strategy 2: Themes fallback (but with conviction, not summaries) ──
    if themes:
        theme_text = themes if isinstance(themes, str) else chr(10).join(themes) if isinstance(themes, list) else str(themes)

        prompt = f"""You are ghostwriting a tweet for Protocol Pulse, a Bitcoin-maximalist cypherpunk media brand.

Current topics on Bitcoin Twitter:
{theme_text}

Pick the SINGLE most interesting topic and write ONE punchy, opinionated tweet about it.

RULES:
- Pick ONE topic only. Do not blend or summarize multiple topics.
- Take a strong position. No hedging.
- Be specific — reference real people and events. NEVER invent numbers, prices, or statistics you are not 100% certain about.
- ONE or TWO sentences max. Under 200 chars preferred, 280 max.
- No hashtags. No emojis.
- Sound like a Bitcoiner who has been in the game for 10 years and is tired of nonsense.

BAD: "quiet accumulation hints at a deeper shift in how value is stored"
BAD: "Bitcoin defends individual sovereignty in a world that thrives on control"
GOOD: "The Fed printed $3T in 18 months. Bitcoin's supply schedule didn't flinch. That's the whole thesis."
GOOD: "Nation-states are mining Bitcoin with subsidized energy while your congressman still thinks it's used for drugs."

Output ONLY the tweet. Nothing else."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.9
            )
            tweet = response.choices[0].message.content.strip().strip('"').strip("'").strip()
            if len(tweet) > 280:
                tweet = tweet[:277] + "..."
            return tweet
        except Exception as e:
            print(f"  GPT themes error: {e}")

    # ── Strategy 3: Pure fallback ──
    prompt = """Write one Bitcoin tweet for Protocol Pulse.
Pick ONE specific angle: an on-chain stat, a fiat comparison with numbers, a bold prediction, or a sovereignty truth.
ONE sentence. Under 180 chars. No hashtags. No emojis. Specific > vague. Bold > safe.
Output ONLY the tweet."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.9
        )
        return response.choices[0].message.content.strip().strip('"').strip("'")
    except:
        return "21 million. No exceptions. No bailouts. No counterfeiting. That is the point."



def generate_verified():
    generate_tweet._cached_tweets = None  # fresh scan for this cycle
    tweets = scan_leaders()
    themes = get_themes(tweets) or get_news_fallback() or ["Bitcoin macro"]
    print(f"\n📊 Themes: {len(themes)}")
    for attempt in range(3):
        print(f"\n[Attempt {attempt+1}]")
        tweet = generate_tweet(themes)
        print(f"\n📝 Generated:\n{tweet}\n")
        ok, _ = fact_check(tweet)
        if ok: return tweet
    return tweet

def post_tweet(text):
    """Post tweet to X/Twitter"""
    try:
        client = get_twitter_write()
        response = client.create_tweet(text=text)
        return response.data["id"]
    except Exception as e:
        print(f"Post error: {e}")
        return None

def test():
    print("\n🧪 TEST MODE\n")
    tweet = generate_verified()
    print(f"\n{'='*50}\n🔥 FINAL TWEET:\n{tweet}\n{'='*50}")
    print(f"Length: {len(tweet)}/280")

def post():
    tweet = generate_verified()
    print(f"\n{tweet}\n")
    if os.getenv("ENABLE_LIVE_POSTING","").lower()=="true":
        tid = post_tweet(tweet)
        print(f"✅ Posted! ID: {tid}")
    else:
        print("🔸 DRY RUN - set ENABLE_LIVE_POSTING=true")

def run():
    """
    Sentiment bot - posts 2 tweets per day between 10AM-6PM ET
    Uses randomized timing to spread posts naturally
    """
    print("🔥 Sentiment Bot started")
    print("📋 Config: 2 tweets/day, 10AM-6PM ET, randomized timing")
    
    while True:
        try:
            # Check if we should post
            should_post, reason = _should_post_now()
            count = _get_todays_post_count()
            
            now_utc = datetime.utcnow()
            print(f"[{now_utc.strftime('%H:%M UTC')}] Posts today: {count}/2 | {reason}")
            
            if should_post:
                tweet = generate_verified()
                if tweet:
                    print(f"📝 Generated: {tweet[:80]}...")
                    
                    if os.getenv("ENABLE_LIVE_POSTING", "").lower() == "true":
                        tid = post_tweet(tweet)
                        if tid:
                            _record_sentiment_post()
                            print(f"✅ Posted! ID: {tid} | Today: {count + 1}/2")
                        else:
                            print("❌ Failed to post")
                    else:
                        print("🔸 DRY RUN - set ENABLE_LIVE_POSTING=true")
                else:
                    print("❌ Failed to generate tweet")
            
            # Sleep 15-30 minutes between checks (randomized)
            sleep_mins = random.randint(15, 30)
            print(f"💤 Sleeping {sleep_mins} minutes...")
            time.sleep(sleep_mins * 60)
            
        except Exception as e:
            print(f"❌ Error in run loop: {e}")
            time.sleep(300)  # Sleep 5 min on error




if __name__ == "__main__":
    import sys
    {"test":test, "post":post, "run":run}.get(sys.argv[1] if len(sys.argv)>1 else "", lambda: print("Usage: python sentiment_bot.py [test|post|run]"))()
