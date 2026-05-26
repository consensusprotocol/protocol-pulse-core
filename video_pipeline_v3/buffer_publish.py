"""Buffer GraphQL publishing module for Protocol Pulse clip engine."""
import os, json, logging, requests
from datetime import datetime, timedelta

logger = logging.getLogger("BufferPublish")

BUFFER_API_URL = "https://api.buffer.com"
CHANNEL_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "buffer_channels.json")

def _get_key():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
    return os.environ.get("BUFFER_GRAPHQL_KEY", "")

def _load_channels():
    if os.path.exists(CHANNEL_CONFIG):
        with open(CHANNEL_CONFIG) as f:
            return json.load(f)
    return {}

def publish_to_buffer(text, channel_ids, schedule_minutes_from_now=None):
    """Publish a text post to one or more Buffer channels.
    
    Args:
        text: Post text
        channel_ids: list of Buffer channel IDs
        schedule_minutes_from_now: optional, schedule N minutes from now
    Returns: list of results
    """
    key = _get_key()
    if not key:
        logger.error("No BUFFER_GRAPHQL_KEY in .env")
        return []

    results = []
    for cid in channel_ids:
        mutation = """mutation CreatePost($input: CreatePostInput!) {
            createPost(input: $input) {
                ... on PostActionSuccess { post { id text dueAt } }
                ... on MutationError { message }
            }
        }"""
        
        variables = {
            "input": {
                "text": text,
                "channelId": cid,
                "schedulingType": "automatic",
                "mode": "addToQueue"
            }
        }
        
        if schedule_minutes_from_now:
            due = (datetime.utcnow() + timedelta(minutes=schedule_minutes_from_now)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            variables["input"]["mode"] = "customScheduled"
            variables["input"]["dueAt"] = due

        try:
            r = requests.post(
                BUFFER_API_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"query": mutation, "variables": variables},
                timeout=15
            )
            data = r.json()
            if "errors" in data:
                logger.error(f"Buffer error for {cid}: {data['errors'][0].get('message','?')}")
                results.append({"channel_id": cid, "ok": False, "error": data["errors"][0].get("message","")})
            else:
                post = data.get("data",{}).get("createPost",{}).get("post",{})
                logger.info(f"Buffer: posted to {cid} -> {post.get('id','?')}")
                results.append({"channel_id": cid, "ok": True, "post_id": post.get("id","")})
        except Exception as e:
            logger.error(f"Buffer failed for {cid}: {e}")
            results.append({"channel_id": cid, "ok": False, "error": str(e)})
    
    return results


def publish_clip_to_brand(text, brand="protocol_pulse", platforms=None):
    """Publish to all channels for a specific brand.
    
    Args:
        text: Post text
        brand: "protocol_pulse", "btc_boomers", "cypherpunkd", "bitcoin_day"
        platforms: optional list like ["twitter","tiktok","instagram"] — defaults to all
    """
    config = _load_channels()
    brand_channels = config.get("channels", {}).get(brand, {})
    
    if platforms:
        channel_ids = [brand_channels[p] for p in platforms if p in brand_channels]
    else:
        channel_ids = list(brand_channels.values())
    
    if not channel_ids:
        logger.error(f"No channels found for brand {brand}")
        return []
    
    return publish_to_buffer(text, channel_ids)


def generate_smart_comment(transcript_snippet, creator_name, sponsor_name=None):
    """Generate a transcript-aware first comment with sponsor shoutout.
    
    Non-AI sounding, value-added, relevant to actual content discussed.
    """
    try:
        import requests as req
        prompt = f"""Write a brief, engaging comment for a social media post featuring a clip from {creator_name}.

TRANSCRIPT SNIPPET: {transcript_snippet[:500]}

RULES:
- Sound like a real human, NOT an AI
- Reference something specific from the transcript
- Add genuine value or insight
- Keep it under 200 characters for X, 300 for other platforms
- NO hashtag spam (max 2 relevant hashtags)
- NO generic phrases like "great content" or "must watch"
{f'- Naturally mention sponsor: {sponsor_name} (e.g. "S/o to {sponsor_name} for supporting independent Bitcoin voices")' if sponsor_name else ''}

Write ONLY the comment text, nothing else."""

        r = req.post("http://localhost:11434/api/chat",
            json={"model": "qwen3-coder:30b", "messages": [{"role": "user", "content": prompt}],
                  "stream": False, "options": {"temperature": 0.7, "num_predict": 100}},
            timeout=30)
        if r.ok:
            text = r.json().get("message", {}).get("content", "").strip()
            # Remove thinking tags if present
            import re
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
            return text
    except Exception as e:
        logger.warning(f"Smart comment generation failed: {e}")
    
    # Fallback
    return f"Incredible insight from {creator_name} here. This is why we built Protocol Pulse — to surface the signal from the noise. #Bitcoin"


def post_with_first_comment(main_text, comment_text, brand="protocol_pulse", platforms=None):
    """Post content + follow up with a first comment."""
    # Post main content
    results = publish_clip_to_brand(main_text, brand, platforms)
    
    # TODO: Buffer GraphQL may support comments via reply/thread
    # For now, log the comment for manual posting or future automation
    logger.info(f"FIRST COMMENT (to be posted): {comment_text}")
    
    return results
