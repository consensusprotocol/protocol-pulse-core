"""
PROTOCOL PULSE NEWSLETTER ENGINE
=================================
World-class automated newsletter with:
- Bloomberg/cypherpunk design — red/black/white, monospace
- AI-powered content curation with anti-slop filters
- Sovereign context integration (Satomi watching)
- Automated daily delivery via Resend
- Self-custody focused messaging

Exceeds expectations. Every time.
"""

import os
import logging
import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Load .env at module level so RESEND_API_KEY is available in all contexts
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_PATH, override=False)
    except ImportError:
        # Manual .env parsing fallback
        with open(_ENV_PATH) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    _k = _k.strip()
                    _v = _v.strip().strip('"').strip("'")
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v


def _resend_post(url: str, key: str, payload: dict, timeout: int = 30) -> requests.Response:
    """POST to Resend API with retry logic. Retries once after 5s on failure."""
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp.status_code in (200, 201):
            return resp
        # Retry once after 5 seconds
        logger.warning(f"Resend first attempt failed (HTTP {resp.status_code}), retrying in 5s...")
        time.sleep(5)
        resp2 = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp2.status_code not in (200, 201):
            logger.error(f"Resend retry failed: HTTP {resp2.status_code} — {resp2.text[:300]}")
        return resp2
    except Exception as e:
        logger.warning(f"Resend first attempt exception: {e}, retrying in 5s...")
        time.sleep(5)
        return requests.post(url, headers=headers, json=payload, timeout=timeout)


class NewsletterEngine:
    def __init__(self):
        self.resend_key = os.environ.get("RESEND_API_KEY", "")
        self.from_email = os.environ.get("NEWSLETTER_FROM_EMAIL", "Protocol Pulse <pulse@protocolpulse.io>")
        self.site_url = os.environ.get("SITE_URL", "https://protocolpulse.io")

        if self.resend_key:
            logger.info("Newsletter Engine initialized with Resend")
        else:
            logger.warning("RESEND_API_KEY not set - newsletter disabled")

    def get_todays_articles(self, limit: int = 5) -> List[Dict]:
        """Get today's best articles with aggressive topic diversity."""
        try:
            from app import app
            from models import Article

            with app.app_context():
                cutoff = datetime.utcnow() - timedelta(hours=24)
                all_recent = Article.query.filter(
                    Article.published == True,
                    Article.created_at >= cutoff
                ).order_by(Article.created_at.desc()).all()

                if not all_recent:
                    return []

                # Separate by type
                opinion = [a for a in all_recent if a.category in ("opinion", "sentiment")]
                news = [a for a in all_recent if a.category not in ("opinion", "sentiment")]

                selected = []
                used_themes = set()

                # Theme detection — group by dominant topic keyword
                def get_theme(title):
                    t = title.lower()
                    themes = {
                        "mining": ["mining", "miner", "hashrate", "hash rate", "difficulty"],
                        "price": ["price", "rally", "crash", "correction", "plunge", "below", "above"],
                        "whale": ["whale", "wallet", "moved", "transfer", "genesis", "satoshi"],
                        "etf": ["etf", "blackrock", "fidelity", "grayscale", "spot"],
                        "regulation": ["regulation", "sec", "congress", "law", "ban", "bill"],
                        "macro": ["fed", "inflation", "rate", "treasury", "dollar", "tariff"],
                        "adoption": ["adopt", "country", "nation", "legal tender", "reserve"],
                        "lightning": ["lightning", "layer 2", "l2", "payment"],
                        "security": ["hack", "exploit", "vulnerability", "attack"],
                    }
                    for theme, keywords in themes.items():
                        if any(kw in t for kw in keywords):
                            return theme
                    return "general"

                # 1. Lead with opinion/intel briefing
                for a in opinion[:1]:
                    theme = get_theme(a.title)
                    selected.append(a)
                    used_themes.add(theme)

                # 2. Fill with DIVERSE news — max 1 article per theme
                for a in news:
                    if len(selected) >= limit:
                        break
                    theme = get_theme(a.title)
                    if theme not in used_themes:
                        selected.append(a)
                        used_themes.add(theme)

                # 3. If still short, allow second article from popular themes
                if len(selected) < limit:
                    for a in news:
                        if len(selected) >= limit:
                            break
                        if a not in selected:
                            selected.append(a)

                return [{
                    "id": a.id,
                    "title": a.title,
                    "summary": a.summary or "",
                    "url": f"{self.site_url}/articles/{a.id}",
                    "image": a.header_image_url or "",
                    "category": a.category or "Bitcoin"
                } for a in selected]

        except Exception as e:
            logger.error(f"Error getting articles: {e}")
            return []

    def generate_ai_summary(self, articles: List[Dict]) -> str:
        """Generate a razor-sharp morning briefing. No AI slop."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("XAI_API_KEY",""), base_url="https://api.x.ai/v1")

            titles_block = "\n".join(f"- [{a.get('category','news')}] {a['title']}" for a in articles[:7])
            summaries_block = "\n".join(f"  {a.get('summary', '')[:150]}" for a in articles[:3])

            response = client.chat.completions.create(
                model="grok-3",
                messages=[
                    {"role": "system", "content": """You write the morning note for a Bitcoin intelligence publication. 3 sentences max. Under 50 words total.

WRITE LIKE: A Bloomberg terminal alert that a human edited for wit.
NOT LIKE: A ChatGPT summary of news articles.

SENTENCE 1: What happened. Lead with the most specific, surprising fact. A number, a name, a move. Not a vague "markets are volatile."
SENTENCE 2: Why it matters or what it means. One sharp implication.
SENTENCE 3 (optional): What to watch. Only if there's something specific.

INSTANT REJECTION — if your draft contains ANY of these, rewrite:
- "plummeted" / "soared" / "surged" / "tumbled"
- "stark reality" / "reality check" / "wake-up call"
- "landscape" / "amidst" / "amid" / "in the wake of"
- "presenting" / "highlighting" / "underscoring" / "signaling"
- "market conditions evolve" / "remains to be seen" / "time will tell"
- "broader volatility" / "significant fluctuation" / "notable shift"
- Any sentence that could apply to any week (if you could swap the date and it still works, it's too vague)
- Any sentence telling the reader what to think or feel

GOOD EXAMPLE:
"A Satoshi-era wallet moved 11,300 BTC overnight — $750M hitting exchanges for the first time since 2012. Bitcoin dropped below $65K on the liquidation cascade. Difficulty adjusts Thursday."

BAD EXAMPLE:
"Bitcoin has plummeted below $65,000 as market chaos strikes, reflecting broader volatility and presenting a stark reality check for the network."

The good example has: specific number, specific dollar amount, specific date context, specific upcoming event.
The bad example has: generic verbs, vague references, no specifics, AI filler."""},
                    {"role": "user", "content": f"Today's articles and summaries:\n{titles_block}\n\nKey details:\n{summaries_block}\n\nWrite the morning note. 3 sentences max. Be specific."}
                ],
                max_tokens=120,
                temperature=0.7
            )

            summary = response.choices[0].message.content.strip()

            # Rejection check — if AI slop leaked through, use a hard fallback
            slop_words = ["plummeted", "soared", "tumbled", "landscape", "amidst",
                         "stark reality", "reality check", "broader volatility",
                         "significant fluctuation", "remains to be seen", "time will tell",
                         "presenting a", "highlighting the", "underscoring"]

            for slop in slop_words:
                if slop.lower() in summary.lower():
                    logger.warning(f"Summary contained slop word '{slop}', requesting rewrite")
                    # One retry with even stricter instruction
                    retry = client.chat.completions.create(
                        model="grok-3",
                        messages=[
                            {"role": "system", "content": "Rewrite this in 2 sentences. Use only specific facts. No adjectives. No commentary. Bloomberg wire style."},
                            {"role": "user", "content": f"Rewrite without AI language:\n{summary}"}
                        ],
                        max_tokens=80,
                        temperature=0.5
                    )
                    summary = retry.choices[0].message.content.strip()
                    break

            return summary

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return ""

    def get_btc_price(self) -> Dict:
        """Get BTC price with fallback sources."""
        import requests

        # Try CoinGecko first
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true", timeout=10)
            if r.status_code == 200:
                data = r.json().get("bitcoin", {})
                return {"price": data.get("usd", 0), "change": data.get("usd_24h_change", 0)}
        except:
            pass

        # Fallback: CoinCap
        try:
            r = requests.get("https://api.coincap.io/v2/assets/bitcoin", timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", {})
                return {"price": float(data.get("priceUsd", 0)), "change": float(data.get("changePercent24Hr", 0))}
        except:
            pass

        # Fallback: use last known from our price service
        try:
            from services.price_service import get_latest_prices
            prices = get_latest_prices()
            if prices and prices.get("btc"):
                return {"price": prices["btc"], "change": 0}
        except:
            pass

        return {"price": 0, "change": 0}

    def generate_subject(self, btc_data: Dict, summary: str = "") -> str:
        """Generate irresistible subject line from live data.

        Examples:
        - "BTC $69K in Extreme Fear. Here's what the network sees."
        - "Miners capitulating. Institutions accumulating. The divergence."
        - "$84,200 — hashrate ATH while sentiment bleeds. Read the signal."
        """
        price = btc_data.get("price", 0)
        change = btc_data.get("change", 0)

        # Get Fear & Greed for subject enrichment
        fg_label = ""
        fg_value = 0
        try:
            ctx_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sovereign_context", "latest.json")
            if os.path.exists(ctx_path):
                with open(ctx_path, 'r') as f:
                    ctx = json.load(f)
                fg = ctx.get("fear_greed", {})
                fg_value = fg.get("value", 0)
                fg_label = fg.get("label", "")
        except Exception:
            pass

        price_str = f"${price:,.0f}" if price else "$---"

        # Build compelling subject from real data
        if summary:
            # Use first sentence of AI summary
            statement = summary.split(".")[0].strip()
            if len(statement) > 55:
                statement = statement[:52] + "..."
            subject = f"{price_str} — {statement}"
        elif fg_value and fg_label:
            if fg_value <= 25:
                subject = f"BTC {price_str} in {fg_label}. Here's what the network sees."
            elif fg_value >= 75:
                subject = f"BTC {price_str} in {fg_label}. Distribution watch active."
            elif change > 3:
                subject = f"{price_str} — accumulation intensifies. The signal is clear."
            elif change < -3:
                subject = f"{price_str} — weak hands exit while conviction deepens."
            else:
                subject = f"{price_str} — {fg_label}. Your morning intelligence."
        else:
            if change > 2:
                subject = f"{price_str} — institutional accumulation pattern deepens"
            elif change < -2:
                subject = f"{price_str} — conviction holders accumulate the fear"
            else:
                subject = f"{price_str} — structure holds. Your daily signal."

        # Ensure subject under 80 chars
        if len(subject) > 80:
            subject = subject[:77] + "..."

        return subject

    def generate_satomi_watching(self) -> List[Dict]:
        """Pull key metrics from sovereign_context/latest.json for Satomi section."""
        try:
            ctx_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sovereign_context", "latest.json")
            if not os.path.exists(ctx_path):
                # Try alternate path
                ctx_path = os.path.join(os.path.dirname(__file__), "..", "data", "sovereign_context", "latest.json")

            with open(ctx_path, 'r') as f:
                ctx = json.load(f)

            bullets = []

            # Fear & Greed
            fg = ctx.get("fear_greed", {})
            if fg.get("value") is not None:
                fg_val = fg["value"]
                fg_label = fg.get("label", "")
                if fg_val <= 25:
                    interp = "Historical accumulation zone. Smart money moves in fear."
                elif fg_val <= 40:
                    interp = "Cautious sentiment. Conviction separates from speculation."
                elif fg_val >= 75:
                    interp = "Euphoria territory. Distribution phase historically follows."
                else:
                    interp = "Neutral ground. Watch for directional catalyst."
                bullets.append({
                    "metric": "Fear & Greed",
                    "value": f"{fg_val} ({fg_label})",
                    "interpretation": interp
                })

            # Hashrate
            net = ctx.get("network", {})
            if net.get("hashrate_eh"):
                hr = net["hashrate_eh"]
                adj = net.get("next_adj_pct", 0)
                adj_str = f"+{adj:.1f}%" if adj >= 0 else f"{adj:.1f}%"
                bullets.append({
                    "metric": "Hashrate",
                    "value": f"{hr:.1f} EH/s (next adj: {adj_str})",
                    "interpretation": "Miners expanding despite price consolidation — supply shock precursor." if adj > 0 else "Difficulty easing — marginal miners capitulating."
                })

            # Mempool
            mem = ctx.get("mempool", {})
            if mem.get("fee_mid") is not None:
                fee = mem["fee_mid"]
                unconfirmed = mem.get("unconfirmed", 0)
                if fee <= 5:
                    interp = "Low-fee window. Optimal for UTXO consolidation."
                elif fee <= 20:
                    interp = "Moderate demand. Network operating normally."
                else:
                    interp = "Fee pressure building. On-chain demand accelerating."
                bullets.append({
                    "metric": "Mempool",
                    "value": f"{fee} sat/vB mid, {unconfirmed:,} unconfirmed",
                    "interpretation": interp
                })

            # Miner conviction index
            indices = ctx.get("indices", {})
            mc = indices.get("miner_conviction", {})
            if mc.get("score") is not None:
                bullets.append({
                    "metric": "Miner Conviction",
                    "value": f"{mc['score']}/100 ({mc.get('signal', 'neutral')})",
                    "interpretation": mc.get("interpretation", "")
                })

            return bullets[:3]  # Max 3 bullets

        except Exception as e:
            logger.error(f"Satomi watching failed: {e}")
            return []

    def generate_html(self, articles: List[Dict], summary: str, btc_data: Dict) -> str:
        """Generate world-class HTML newsletter — Bloomberg meets cypherpunk.

        6-section design: Masthead, The Number, Intelligence Summary,
        The Signal, Satomi Is Watching, Footer.
        All inline styles. Mobile-first. Dark mode native.
        """

        date_str = datetime.utcnow().strftime("%B %d, %Y").upper()
        issue_number = (datetime.utcnow() - datetime(2026, 1, 1)).days

        # Price formatting
        price_raw = btc_data.get('price', 0)
        price = f"${price_raw:,.0f}" if price_raw else "$---"
        price_plain = f"{price_raw:,.0f}" if price_raw else "---"
        change = btc_data.get('change', 0)
        change_color = "#22c55e" if change >= 0 else "#ef4444"
        change_str = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"

        # Satomi watching bullets
        satomi_bullets = self.generate_satomi_watching()
        satomi_html = ""
        for b in satomi_bullets:
            satomi_html += f'''<tr>
<td style="padding: 8px 0; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 12px; color: rgba(255,255,255,0.8); line-height: 1.6;">
&gt; {b['metric']}: {b['value']} &mdash; {b['interpretation']}
</td>
</tr>'''

        if not satomi_html:
            satomi_html = '''<tr>
<td style="padding: 8px 0; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 12px; color: rgba(255,255,255,0.8); line-height: 1.6;">
&gt; All systems nominal. Sovereign infrastructure holds.
</td>
</tr>'''

        # Intelligence summary — split into 3 paragraphs if long enough
        summary_paragraphs = ""
        if summary:
            sentences = [s.strip() for s in summary.replace(". ", ".|").split("|") if s.strip()]
            if len(sentences) >= 3:
                # Group into 3 paragraphs
                summary_paragraphs = f'''<p style="margin: 0 0 16px; font-size: 14px; line-height: 1.8; color: #e5e7eb; font-family: Georgia, 'Times New Roman', Times, serif;">
{sentences[0]}
</p>
<p style="margin: 0 0 16px; font-size: 14px; line-height: 1.8; color: #e5e7eb; font-family: Georgia, 'Times New Roman', Times, serif;">
{sentences[1]}
</p>
<p style="margin: 0; font-size: 14px; line-height: 1.8; color: #e5e7eb; font-family: Georgia, 'Times New Roman', Times, serif;">
{" ".join(sentences[2:])}
</p>'''
            else:
                summary_paragraphs = f'''<p style="margin: 0; font-size: 14px; line-height: 1.8; color: #e5e7eb; font-family: Georgia, 'Times New Roman', Times, serif;">
{summary}
</p>'''

        # Signal text — extract the sharpest insight
        signal_text = ""
        if articles:
            # Use lead article summary as signal, or summary itself
            lead = articles[0]
            signal_text = lead.get("summary", "")[:200]
            if not signal_text:
                signal_text = summary
        elif summary:
            signal_text = summary
        else:
            signal_text = "Structure holds. Conviction deepens. The protocol does not care about your feelings."

        # Build article cards for intelligence section (compact)
        articles_html = ""
        for article in articles[:3]:
            cat = article.get('category', 'Bitcoin').upper()
            articles_html += f'''<tr>
<td style="padding: 16px 0; border-bottom: 1px solid #1a1a1a;">
<a href="{article['url']}" style="text-decoration: none;">
<span style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 9px; color: #ff3b5f; letter-spacing: 0.3em; text-transform: uppercase;">{cat}</span>
<p style="margin: 6px 0 0; font-size: 15px; font-weight: 600; line-height: 1.5; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">{article["title"]}</p>
</a>
</td>
</tr>'''

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Protocol Pulse</title>
</head>
<body style="margin: 0; padding: 0; background-color: #000000; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">

<!-- WRAPPER -->
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #000000;">
<tr>
<td align="center" style="padding: 0;">

<!-- MAIN CONTAINER -->
<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%; background-color: #0a0a0a;">

<!-- ═══ SECTION 1: MASTHEAD ═══ -->
<!-- Red top bar -->
<tr>
<td style="background-color: #ff3b5f; height: 4px; font-size: 0; line-height: 0;">&nbsp;</td>
</tr>

<!-- Logo block -->
<tr>
<td style="padding: 32px 40px 24px; background-color: #0a0a0a;" align="center">
<table cellpadding="0" cellspacing="0" border="0">
<tr>
<td align="center" style="padding-bottom: 12px;">
<img src="https://protocolpulse.io/static/images/protocol-pulse-logo.png"
     width="72" height="72" alt="Protocol Pulse"
     style="display:block;border:0;border-radius:10px;margin:0 auto;">
</td>
</tr>
<tr>
<td align="center">
<p style="margin: 0; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 14px; font-weight: 700; letter-spacing: 0.3em; color: #ffffff; text-transform: uppercase;">PROTOCOL PULSE</p>
</td>
</tr>
<tr>
<td align="center" style="padding-top: 6px;">
<p style="margin: 0; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 9px; letter-spacing: 0.4em; color: #ff3b5f; text-transform: uppercase;">SOVEREIGN BITCOIN INTELLIGENCE</p>
</td>
</tr>
<tr>
<td align="center" style="padding-top: 10px;">
<p style="margin: 0; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 9px; color: rgba(255,255,255,0.4);">{date_str} &nbsp;&bull;&nbsp; ISSUE #{issue_number}</p>
</td>
</tr>
</table>
</td>
</tr>

<!-- Red separator -->
<tr>
<td style="padding: 0 40px;">
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td style="border-bottom: 1px solid #ff3b5f; font-size: 0; line-height: 0; height: 1px;">&nbsp;</td></tr>
</table>
</td>
</tr>

<!-- ═══ SECTION 2: THE NUMBER ═══ -->
<tr>
<td style="padding: 32px 40px; background-color: #111111; border-left: 3px solid #ff3b5f;">
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td align="center">
<p style="margin: 0; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 48px; font-weight: 700; color: #ffffff; line-height: 1.1;">{price_plain}</p>
</td>
</tr>
<tr>
<td align="center" style="padding-top: 8px;">
<p style="margin: 0; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 9px; letter-spacing: 0.3em; color: #ff3b5f; text-transform: uppercase;">BTC/USD &nbsp;&bull;&nbsp; <span style="color: {change_color};">{change_str} 24H</span></p>
</td>
</tr>
<tr>
<td align="center" style="padding-top: 12px;">
<p style="margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-size: 13px; line-height: 1.7; color: #ffffff; max-width: 460px;">{summary.split('.')[0].strip() + '.' if summary and '.' in summary else summary or 'The protocol continues.'}</p>
</td>
</tr>
</table>
</td>
</tr>

<!-- ═══ SECTION 3: INTELLIGENCE SUMMARY ═══ -->
<tr>
<td style="padding: 32px 40px; background-color: #0a0a0a;">
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td>
<p style="margin: 0 0 16px; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 9px; letter-spacing: 0.4em; color: #ff3b5f; text-transform: uppercase;">SIGNAL INTELLIGENCE</p>
</td>
</tr>
<tr>
<td style="border-left: 3px solid #ff3b5f; padding-left: 16px;">
{summary_paragraphs}
</td>
</tr>
</table>
</td>
</tr>

<!-- Article links -->
<tr>
<td style="padding: 0 40px 24px; background-color: #0a0a0a;">
<table width="100%" cellpadding="0" cellspacing="0" border="0">
{articles_html}
</table>
</td>
</tr>

<!-- ═══ SECTION 4: THE SIGNAL ═══ -->
<tr>
<td style="padding: 0 40px;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #1a0508; border: 1px solid #ff3b5f;">
<tr>
<td style="padding: 24px;">
<p style="margin: 0 0 12px; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 9px; letter-spacing: 0.4em; color: #ff3b5f; text-transform: uppercase;">SIGNAL</p>
<p style="margin: 0 0 16px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-size: 15px; font-weight: 700; line-height: 1.7; color: #ffffff;">{signal_text}</p>
<p style="margin: 0; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 8px; color: rgba(255,255,255,0.3); letter-spacing: 0.2em;">PATTERN RECOGNITION &mdash; NOT FINANCIAL ADVICE</p>
</td>
</tr>
</table>
</td>
</tr>

<!-- ═══ SECTION 5: SATOMI IS WATCHING ═══ -->
<tr>
<td style="padding: 32px 40px; background-color: #0d0d0d;">
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td style="padding-bottom: 16px;">
<table cellpadding="0" cellspacing="0" border="0">
<tr>
<td style="vertical-align: middle; padding-right: 12px;">
<img src="{self.site_url}/static/oracle_avatar.png" alt="Satomi" width="32" height="32" style="display: block; border-radius: 50%; border: 2px solid #ff3b5f;" />
</td>
<td style="vertical-align: middle;">
<p style="margin: 0; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 9px; letter-spacing: 0.4em; color: #ff3b5f; text-transform: uppercase;">SATOMI IS WATCHING</p>
</td>
</tr>
</table>
</td>
</tr>
{satomi_html}
</table>
</td>
</tr>

<!-- ═══ SECTION 6: FOOTER ═══ -->
<!-- Red separator -->
<tr>
<td style="padding: 0 40px; background-color: #050505;">
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td style="border-bottom: 1px solid #ff3b5f; font-size: 0; line-height: 0; height: 1px;">&nbsp;</td></tr>
</table>
</td>
</tr>

<tr>
<td style="padding: 32px 40px; background-color: #050505;" align="center">
<table cellpadding="0" cellspacing="0" border="0">
<tr>
<td align="center">
<p style="margin: 0 0 16px; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 10px; letter-spacing: 0.3em; color: rgba(255,255,255,0.4); text-transform: uppercase;">PROTOCOL PULSE &mdash; INTELLIGENCE FOR SOVEREIGNS</p>
</td>
</tr>
<tr>
<td align="center">
<p style="margin: 0 0 16px; font-size: 11px; color: #374151; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
<a href="{self.site_url}/newsletter/unsubscribe" style="color: #6b7280; text-decoration: underline;">Unsubscribe</a>
&nbsp;&nbsp;&bull;&nbsp;&nbsp;
<a href="{self.site_url}/privacy" style="color: #6b7280; text-decoration: underline;">Privacy Policy</a>
</p>
</td>
</tr>
<tr>
<td align="center">
<p style="margin: 0; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace; font-size: 10px; letter-spacing: 0.3em; color: #ff3b5f;">Verify. Don't trust.</p>
</td>
</tr>
</table>
</td>
</tr>

</table>
<!-- /MAIN CONTAINER -->

</td>
</tr>
</table>
<!-- /WRAPPER -->

</body>
</html>'''
        return html

    def send_newsletter(self, to_emails: List[str], subject: str = None, html: str = None) -> Dict:
        """Send newsletter via Resend"""
        if not self.resend_key:
            return {"success": False, "error": "Resend not configured"}

        if not to_emails:
            return {"success": False, "error": "No recipients"}

        # Generate content if not provided
        if not html:
            articles = self.get_todays_articles()
            if not articles:
                return {"success": False, "error": "No articles to send"}

            summary = self.generate_ai_summary(articles)
            btc_data = self.get_btc_price()
            html = self.generate_html(articles, summary, btc_data)

        if not subject:
            btc_data = self.get_btc_price()
            subject = self.generate_subject(btc_data)

        # Send via Resend with retry logic
        try:
            sent = 0
            errors = []

            # Send in batches of 50
            for i in range(0, len(to_emails), 50):
                batch = to_emails[i:i+50]

                try:
                    response = _resend_post(
                        "https://api.resend.com/emails/batch",
                        self.resend_key,
                        [{
                            "from": self.from_email,
                            "to": email,
                            "subject": subject,
                            "html": html
                        } for email in batch],
                        timeout=30
                    )

                    if response.status_code in (200, 201):
                        sent += len(batch)
                    else:
                        err_msg = f"Batch {i}: HTTP {response.status_code} — {response.text[:200]}"
                        errors.append(err_msg)
                        logger.error(f"Newsletter batch failed: {err_msg}")
                except Exception as batch_err:
                    err_msg = f"Batch {i}: {str(batch_err)}"
                    errors.append(err_msg)
                    logger.error(f"Newsletter batch exception: {err_msg}")

            return {
                "success": sent > 0,
                "sent": sent,
                "total": len(to_emails),
                "errors": errors if errors else None
            }

        except Exception as e:
            logger.error(f"Newsletter send failed completely: {e}")
            return {"success": False, "error": str(e)}

    def get_subscribers(self) -> List[str]:
        """Get subscriber emails from database"""
        try:
            from app import app
            from models import User

            with app.app_context():
                # Get users with newsletter_subscribed = True
                users = User.query.filter_by(newsletter_subscribed=True).all()
                return [u.email for u in users if u.email]
        except:
            return []

    def run_daily_newsletter(self) -> Dict:
        """Main entry point for daily newsletter"""
        logger.info("Running daily newsletter...")

        # Check if already sent today
        sent_file = "data/newsletter_sent.json"
        today = datetime.utcnow().strftime("%Y-%m-%d")

        try:
            import os
            os.makedirs("data", exist_ok=True)

            if os.path.exists(sent_file):
                with open(sent_file, 'r') as f:
                    data = json.load(f)
                if data.get("last_sent") == today:
                    logger.info("Newsletter already sent today")
                    return {"success": False, "error": "Already sent today"}
        except:
            pass

        # Get subscribers
        subscribers = self.get_subscribers()

        if not subscribers:
            logger.warning("No subscribers found")
            return {"success": False, "error": "No subscribers"}

        # Send
        result = self.send_newsletter(subscribers)

        # Mark as sent
        if result.get("success"):
            with open(sent_file, 'w') as f:
                json.dump({"last_sent": today, "sent": result.get("sent", 0)}, f)

        logger.info(f"Newsletter result: {result}")
        return result

    def send_test(self, email: str) -> Dict:
        """Send test newsletter to single email"""
        articles = self.get_todays_articles()

        if not articles:
            # Use dummy data for test
            articles = [{
                "id": 1,
                "title": "Bitcoin Self-Custody Reaches Record Adoption",
                "summary": "More individuals than ever are taking control of their own Bitcoin. Hardware wallet sales surge as sovereignty becomes the priority for serious Bitcoiners.",
                "url": f"{self.site_url}/articles/1",
                "category": "Sovereignty"
            }, {
                "id": 2,
                "title": "Lightning Network Capacity Hits All-Time High",
                "summary": "The peer-to-peer payment layer continues to grow as more nodes come online and channel capacity expands globally.",
                "url": f"{self.site_url}/articles/2",
                "category": "Technology"
            }]

        summary = self.generate_ai_summary(articles)
        btc_data = self.get_btc_price()
        html = self.generate_html(articles, summary, btc_data)
        subject = self.generate_subject(btc_data, summary)

        return self.send_newsletter([email], subject=subject, html=html)


# Singleton
newsletter_engine = NewsletterEngine()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "test" and len(sys.argv) > 2:
            email = sys.argv[2]
            result = newsletter_engine.send_test(email)
            print(json.dumps(result, indent=2))

        elif cmd == "run":
            result = newsletter_engine.run_daily_newsletter()
            print(json.dumps(result, indent=2))

        elif cmd == "preview":
            articles = newsletter_engine.get_todays_articles()
            summary = newsletter_engine.generate_ai_summary(articles)
            btc = newsletter_engine.get_btc_price()
            html = newsletter_engine.generate_html(articles, summary, btc)

            # Save preview
            with open("newsletter_preview.html", "w") as f:
                f.write(html)
            print("Preview saved to newsletter_preview.html")

        else:
            print("Usage: python newsletter_engine.py [test <email> | run | preview]")
    else:
        print("Usage: python newsletter_engine.py [test <email> | run | preview]")
