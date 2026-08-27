"""
buffer_poster.py — Protocol Pulse posting via Buffer's public GraphQL API.

Why this exists:
  Direct X API posting (tweepy/OAuth) now returns 402 Payment Required —
  the @ProtocolPulseHQ developer account has no write credits. Buffer's new
  public GraphQL API (free tier, all plans) publishes to X for $0 using the
  existing BUFFER_API_KEY in .env. This module is the drop-in replacement
  for post_to_x().

Endpoint: https://api.buffer.com/graphql   (NOT api.bufferapp.com — that REST
          API is dead and returns "Public API tokens are not accepted".)
Auth:     Authorization: Bearer <BUFFER_API_KEY>
Limits (free): 100 req / 15 min, 100 / 24h, 3000 / 30 days. Plenty for 2x/day.
Keys expire 30 days after creation — regenerate at publish.buffer.com/settings/api
"""
import os
import json
import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger("buffer_poster")

BUFFER_URL = "https://api.buffer.com/graphql"
ORG_ID = "672bf13d36385f4ca9125c1f"  # Protocol Pulse org

# Connected, non-disconnected, non-locked channels (verified via channels query)
CHANNELS = {
    "x":          "6a14fd85c687a22dd42796de",  # @ProtocolPulseHQ  (primary)
    "x_boomers":  "69e0d739031bfa423c0d867d",  # @btc_boomers
}

_MUTATION = """mutation($input: CreatePostInput!){
  createPost(input:$input){
    __typename
    ... on PostActionSuccess { post { id status text channelService shareMode dueAt } }
    ... on InvalidInputError { message }
    ... on UnauthorizedError { message }
    ... on LimitReachedError { message }
    ... on RestProxyError { message }
    ... on UnexpectedError { message }
    ... on NotFoundError { message }
  }
}"""


def _token():
    tok = os.environ.get("BUFFER_API_KEY", "")
    if tok:
        return tok
    env = Path.home() / "protocol_pulse" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("BUFFER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _gql(query, variables=None, timeout=40):
    payload = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    req = urllib.request.Request(
        BUFFER_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + _token(),
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def buffer_available():
    """Cheap auth probe. True if the key is live."""
    try:
        r = _gql("{ __typename }", timeout=15)
        return r.get("data", {}).get("__typename") == "Query"
    except Exception as e:
        logger.warning("Buffer probe failed: %s", str(e)[:120])
        return False


def post_to_buffer(text, channel="x", mode="shareNow", save_to_draft=False):
    """
    Publish `text` to a Buffer-connected channel.

    channel: "x" (@ProtocolPulseHQ) | "x_boomers" | raw Buffer channel id
    mode:    "shareNow"  -> publish immediately
             "addToQueue"-> next open slot in Buffer schedule
             "shareNext" -> top of the queue
    save_to_draft: True -> save as Buffer draft, do NOT publish

    Returns: {"success": bool, "post_id": str, "error": str, "raw": dict}
    """
    channel_id = CHANNELS.get(channel, channel)
    variables = {
        "input": {
            "channelId": channel_id,
            "text": text,
            "schedulingType": "automatic",
            "mode": mode,
            "assets": [],
            "saveToDraft": bool(save_to_draft),
            "source": "protocol_pulse_tweet_machine",
        }
    }
    try:
        resp = _gql(_MUTATION, variables)
    except Exception as e:
        body = ""
        try:
            body = e.read().decode()[:300]  # type: ignore[attr-defined]
        except Exception:
            pass
        logger.error("Buffer post HTTP error: %s %s", str(e)[:120], body)
        return {"success": False, "error": f"http: {str(e)[:120]} {body}", "raw": None}

    if resp.get("errors"):
        msg = resp["errors"][0].get("message", "unknown")
        logger.error("Buffer GraphQL error: %s", msg)
        return {"success": False, "error": msg, "raw": resp}

    payload = resp.get("data", {}).get("createPost", {})
    tn = payload.get("__typename")
    if tn == "PostActionSuccess":
        post = payload.get("post", {}) or {}
        logger.info("Buffer post OK id=%s status=%s mode=%s",
                    post.get("id"), post.get("status"), post.get("shareMode"))
        return {"success": True, "post_id": post.get("id"),
                "status": post.get("status"), "raw": payload}
    # typed error
    err = payload.get("message", tn or "unknown error")
    logger.error("Buffer post failed (%s): %s", tn, err)
    return {"success": False, "error": f"{tn}: {err}", "raw": payload}


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if args and args[0] == "--probe":
        print("buffer_available:", buffer_available())
        sys.exit(0)
    draft = "--draft" in args
    mode = "shareNow"
    txt = next((a for a in args if not a.startswith("--")), "Protocol Pulse x Buffer wiring test.")
    res = post_to_buffer(txt, channel="x", mode=mode, save_to_draft=draft)
    print(json.dumps(res, indent=2)[:700])
