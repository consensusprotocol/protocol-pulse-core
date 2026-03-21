#!/usr/bin/env python3
"""
substack_publisher.py
Publishes Protocol Pulse articles to Substack using session cookie auth.

AUTH SETUP (one-time):
1. Go to substack.com in Chrome/Firefox
2. Log in via magic link
3. DevTools (F12) -> Application -> Cookies -> substack.com
4. Copy value of "substack.sid" cookie
5. Add to /home/ultron/protocol_pulse/.env:
   SUBSTACK_SID=your_cookie_value_here
   SUBSTACK_PUBLICATION_ID=4276014
   SUBSTACK_PUBLICATION_URL=https://protocolpulse.substack.com

The session cookie persists for ~1 year. Refresh it if publishing fails with 401/403.
"""

import os, sys, re, json, logging
from datetime import datetime
from pathlib import Path
import urllib.request, urllib.parse

BASE = Path("/home/ultron/protocol_pulse")
sys.path.insert(0, str(BASE))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("substack_publisher")

SUBSTACK_BASE = "https://substack.com"
PUBLICATION_URL = "https://protocolpulse.substack.com"


def _load_env():
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def _get_headers() -> dict:
    """Build request headers with session cookie."""
    _load_env()
    sid = os.getenv("SUBSTACK_SID", "")
    pub_url = os.getenv("SUBSTACK_PUBLICATION_URL", PUBLICATION_URL)
    
    return {
        "Cookie": f"substack.sid={sid}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Origin": pub_url,
        "Referer": f"{pub_url}/publish/post",
    }


def _api_request(method: str, path: str, body: dict = None) -> dict | None:
    """Make authenticated request to Substack API."""
    _load_env()
    pub_url = os.getenv("SUBSTACK_PUBLICATION_URL", PUBLICATION_URL).rstrip("/")
    url = f"{pub_url}/api/v1{path}"
    
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_get_headers(), method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="ignore")[:300]
        logger.error(f"HTTP {e.code} on {method} {url}: {body_text}")
        if e.code in (401, 403):
            logger.error("AUTH FAILED — refresh SUBSTACK_SID cookie in .env")
        return None
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return None


def html_to_substack_doc(html_content: str, title: str) -> dict:
    """
    Convert Protocol Pulse HTML article to Substack editor_v2 doc format.
    Substack uses a Prosemirror-based JSON document format.
    """
    content_nodes = []
    
    # Strip h1 (title shown separately)
    html = re.sub(r"<h1[^>]*>.*?</h1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    # Strip tldr-section (becomes subtitle)
    tldr_match = re.search(r"<div[^>]*tldr-section[^>]*>(.*?)</div>", html, re.DOTALL | re.IGNORECASE)
    tldr_text = ""
    if tldr_match:
        tldr_text = re.sub(r"<[^>]+>", "", tldr_match.group(1)).strip()
        tldr_text = re.sub(r"TL;DR:\s*", "", tldr_text).strip()
        html = html.replace(tldr_match.group(0), "")

    # Parse paragraphs and headers
    elements = re.findall(
        r"(<h2[^>]*>.*?</h2>|<h3[^>]*>.*?</h3>|<p[^>]*>.*?</p>|<ul[^>]*>.*?</ul>)",
        html, re.DOTALL | re.IGNORECASE
    )
    
    for el in elements:
        clean = re.sub(r"<[^>]+>", "", el).strip()
        if not clean:
            continue
        
        if re.match(r"<h2", el, re.IGNORECASE):
            content_nodes.append({
                "type": "heading",
                "attrs": {"level": 2, "textAlign": "left"},
                "content": [{"type": "text", "text": clean}]
            })
        elif re.match(r"<h3", el, re.IGNORECASE):
            content_nodes.append({
                "type": "heading", 
                "attrs": {"level": 3, "textAlign": "left"},
                "content": [{"type": "text", "text": clean}]
            })
        elif re.match(r"<ul", el, re.IGNORECASE):
            items = re.findall(r"<li[^>]*>(.*?)</li>", el, re.DOTALL | re.IGNORECASE)
            list_items = []
            for item in items:
                item_clean = re.sub(r"<[^>]+>", "", item).strip()
                if item_clean:
                    list_items.append({
                        "type": "listItem",
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": item_clean}]}]
                    })
            if list_items:
                content_nodes.append({"type": "bulletList", "content": list_items})
        else:
            # Paragraph — handle inline bold
            para_nodes = []
            parts = re.split(r"(<strong>.*?</strong>)", el, flags=re.DOTALL | re.IGNORECASE)
            for part in parts:
                text = re.sub(r"<[^>]+>", "", part).strip()
                if not text:
                    continue
                if re.search(r"<strong>", part, re.IGNORECASE):
                    para_nodes.append({"type": "text", "marks": [{"type": "bold"}], "text": text})
                else:
                    para_nodes.append({"type": "text", "text": text})
            if para_nodes:
                content_nodes.append({
                    "type": "paragraph",
                    "attrs": {"textAlign": "left"},
                    "content": para_nodes
                })

    # Add Protocol Pulse attribution footer
    content_nodes.append({
        "type": "paragraph",
        "attrs": {"textAlign": "left"},
        "content": [{"type": "text", "text": "— Published by Protocol Pulse | protocolpulse.io"}]
    })
    
    return {
        "type": "doc",
        "content": content_nodes
    }, tldr_text


def create_draft(title: str, html_content: str, subtitle: str = "",
                 cover_image_url: str = None) -> dict | None:
    """Create a draft post on Substack."""
    _load_env()
    pub_id = int(os.getenv("SUBSTACK_PUBLICATION_ID", "4276014"))
    
    doc, auto_subtitle = html_to_substack_doc(html_content, title)
    final_subtitle = subtitle or auto_subtitle or ""
    
    payload = {
        "draft_title": title,
        "draft_subtitle": final_subtitle[:100],
        "draft_body": json.dumps(doc),
        "audience": "everyone",
        "type": "newsletter",
        "publication_id": pub_id,
        "draft_section_id": None,
        "draft_podcast_url": None,
        "draft_podcast_duration": None,
        "draft_video_upload_id": None,
        "write_comment_permissions": "everyone",
        "should_send_email": True,
        "show_guest_bios": False,
        "draft_bylines": [{"id": 316907961, "is_guest": False}],
    }
    
    if cover_image_url and cover_image_url.startswith("http"):
        payload["cover_image"] = cover_image_url
    
    result = _api_request("POST", "/drafts", payload)
    if result and result.get("id"):
        draft_id = result["id"]
        logger.info(f"Draft created: id={draft_id} title='{title[:60]}'")
        return result
    
    logger.error(f"Draft creation failed: {result}")
    return None


def publish_draft(draft_id: int) -> dict | None:
    """Publish an existing draft."""
    result = _api_request("POST", f"/drafts/{draft_id}/publish", {
        "send": True,
        "share_automatically": False,
    })
    if result:
        logger.info(f"Published draft {draft_id}")
    return result


def publish_article_to_substack(article_id: int = None, article_dict: dict = None,
                                 auto_publish: bool = True) -> str | None:
    """
    Main entry: publish a Protocol Pulse article to Substack.
    
    Args:
        article_id: DB article ID (loads from DB)
        article_dict: Dict with title/content/summary/cover_image_url (skips DB)
        auto_publish: If True, publish immediately. If False, save as draft only.
    
    Returns:
        Published post URL or None
    """
    _load_env()
    
    if not os.getenv("SUBSTACK_SID"):
        logger.error("SUBSTACK_SID not set — add session cookie to .env")
        logger.error("Instructions: substack.com -> DevTools -> Application -> Cookies -> substack.sid")
        return None
    
    # Load article
    if article_id and not article_dict:
        try:
            from app import app
            import models
            with app.app_context():
                a = models.Article.query.get(article_id)
                if not a:
                    logger.error(f"Article {article_id} not found")
                    return None
                slug = a.slug or str(a.id)
                article_dict = {
                    "title": a.title,
                    "content": a.content,
                    "summary": a.summary or "",
                    "cover_image_url": a.cover_image_url or "",
                    "url": f"https://protocolpulse.io/articles/{slug}",
                }
        except Exception as e:
            logger.error(f"DB load failed: {e}")
            return None
    
    if not article_dict:
        logger.error("No article data provided")
        return None
    
    # Add PP attribution link to content
    content = article_dict.get("content", "")
    pp_url = article_dict.get("url", "https://protocolpulse.io")
    read_more = f'''<p><a href="{pp_url}">Read the full brief on Protocol Pulse →</a></p>'''
    if "protocolpulse.io" not in content:
        content = content + read_more
    
    # Create draft
    draft = create_draft(
        title=article_dict["title"],
        html_content=content,
        subtitle=article_dict.get("summary", "")[:100],
        cover_image_url=article_dict.get("cover_image_url"),
    )
    
    if not draft:
        return None
    
    draft_id = draft["id"]
    
    if not auto_publish:
        logger.info(f"Draft saved (not published): id={draft_id}")
        return f"https://protocolpulse.substack.com/publish/post/{draft_id}"
    
    # Publish
    pub_result = publish_draft(draft_id)
    if pub_result:
        post_url = pub_result.get("canonical_url") or f"https://protocolpulse.substack.com/p/{draft.get('slug', draft_id)}"
        logger.info(f"Published to Substack: {post_url}")
        return post_url
    
    return None


def test_auth() -> bool:
    """Test if SUBSTACK_SID is valid."""
    _load_env()
    result = _api_request("GET", "/drafts?limit=1")
    if result is not None:
        print("AUTH OK — Substack session valid")
        return True
    else:
        print("AUTH FAILED — check SUBSTACK_SID in .env")
        return False


if __name__ == "__main__":
    import sys
    if "--test-auth" in sys.argv:
        test_auth()
    elif "--publish-latest" in sys.argv:
        # Publish latest article
        try:
            from dotenv import load_dotenv
            load_dotenv(BASE / ".env")
            from app import app
            import models
            with app.app_context():
                a = models.Article.query.filter_by(published=True).order_by(models.Article.id.desc()).first()
                if a:
                    print(f"Publishing: [{a.id}] {a.title}")
                    url = publish_article_to_substack(article_id=a.id)
                    print(f"Result: {url}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python3 substack_publisher.py --test-auth | --publish-latest")
