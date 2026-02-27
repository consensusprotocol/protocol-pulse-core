"""
Telegram Distribution Service for Protocol Pulse
Handles auto-posting and alert distribution via Telegram API.
"""

import os
import logging
import requests
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID') or os.environ.get('TELEGRAM_CHANNEL_ID')

def send_telegram_message(message: str, parse_mode: str = 'HTML', disable_preview: bool = False) -> bool:
    """
    Send a message to the configured Telegram channel.
    
    Args:
        message: The message text to send
        parse_mode: 'HTML' or 'Markdown'
        disable_preview: Whether to disable link previews
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_preview
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"Telegram message sent successfully")
            return True
        else:
            logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False

def send_whale_alert(btc_amount: float, txid: str, is_mega: bool = False) -> bool:
    """Send a whale transaction alert."""
    emoji = "🐋🚨" if is_mega else "🐋"
    usd_estimate = btc_amount * 100000
    
    message = f"""
{emoji} <b>WHALE ALERT</b>

<code>{btc_amount:,.2f} BTC</code> (~${usd_estimate:,.0f})
Moving on-chain

<a href="https://mempool.space/tx/{txid}">View Transaction</a>

<i>Sovereign Intelligence via Protocol Pulse</i>
"""
    return send_telegram_message(message)

def send_daily_brief(title: str, summary: str, source: str = "Sarah Chen") -> bool:
    """Send the daily macro brief."""
    message = f"""
☀️ <b>DAILY MACRO BRIEF</b>

<b>{title}</b>

{summary[:800]}

<i>Analysis by {source} | Protocol Pulse</i>
"""
    return send_telegram_message(message)

def send_network_update(hashrate: str, difficulty: str, block_height: int) -> bool:
    """Send network metrics update."""
    message = f"""
⚡ <b>NETWORK PULSE</b>

📊 Hashrate: <code>{hashrate}</code>
🎯 Difficulty: <code>{difficulty}</code>
🧱 Block: <code>{block_height:,}</code>

<i>Alex Rivera | Quant Analysis</i>
"""
    return send_telegram_message(message)

def send_article_notification(title: str, url: str, category: str = "Intel Brief") -> bool:
    """Notify about new article publication."""
    message = f"""
📰 <b>NEW {category.upper()}</b>

<b>{title}</b>

<a href="{url}">Read Full Report</a>

<i>Protocol Pulse Intelligence</i>
"""
    return send_telegram_message(message)

def get_telegram_status() -> Dict:
    """Check Telegram bot status."""
    if not TELEGRAM_BOT_TOKEN:
        return {'online': False, 'error': 'Bot token not configured'}
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'online': True,
                'bot_name': data.get('result', {}).get('username'),
                'chat_id': TELEGRAM_CHAT_ID
            }
        else:
            return {'online': False, 'error': f'API error: {response.status_code}'}
            
    except Exception as e:
        return {'online': False, 'error': str(e)}



def send_article_briefing(article_title: str, article_summary: str, article_url: str) -> bool:
    """Send a casual, value-added article notification to Telegram"""
    
    # Create casual but informative briefing
    message = f"""🔴 <b>Fresh Intel from Protocol Pulse</b>

{article_summary[:200]}...

📰 <b>{article_title}</b>

👉 <a href="{article_url}">Read the full breakdown</a>

<i>Your daily dose of Bitcoin intelligence.</i>"""

    return send_telegram_message(message, parse_mode='HTML')


def send_pulse_briefing(briefing_text: str, article_url: str = None) -> bool:
    """Send the daily pulse intelligence briefing"""
    
    message = briefing_text
    if article_url:
        message += f"\n\n👉 {article_url}"
    
    return send_telegram_message(message, parse_mode='Markdown')
