"""
TELEGRAM ALERTS - Real-time Signal Notifications
=================================================
Sends alerts to Telegram when signals trigger or regime changes.

FEATURES:
- Instant alerts for new signals
- Regime change notifications
- Daily summary digest
- Clean, professional formatting (no emojis)

SETUP:
1. Create a Telegram bot via @BotFather
2. Get your bot token
3. Get your chat ID (send message to bot, check updates)
4. Set environment variables:
   - TELEGRAM_BOT_TOKEN
   - TELEGRAM_CHAT_ID
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Add services to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sovereign_intel_terminal import (
    SovereignIntelTerminal,
    Signal,
    Regime,
    Direction,
    SignalStrength,
    get_db
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TelegramAlerts")


class TelegramAlertBot:
    """
    Sends formatted alerts to Telegram.
    Clean, professional formatting - no emojis.
    """
    
    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        self.terminal = SovereignIntelTerminal()
        self.last_regime_file = "data/last_regime.json"
        self.last_signals_file = "data/last_signals.json"
    
    @property
    def is_configured(self) -> bool:
        """Check if Telegram is configured."""
        return bool(self.bot_token and self.chat_id)
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message to Telegram."""
        if not self.is_configured:
            logger.warning("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        try:
            response = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }, timeout=10)
            
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    def _get_direction_symbol(self, direction: str) -> str:
        """Get symbol for direction."""
        if direction == "bullish":
            return "[BULLISH]"
        elif direction == "bearish":
            return "[BEARISH]"
        return "[NEUTRAL]"
    
    def _load_last_state(self, filepath: str) -> Dict:
        """Load last known state."""
        try:
            if os.path.exists(filepath):
                with open(filepath) as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def _save_last_state(self, filepath: str, state: Dict):
        """Save current state."""
        os.makedirs("data", exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2, default=str)
    
    def format_signal_alert(self, signal: Dict) -> str:
        """Format a signal as Telegram message."""
        direction = self._get_direction_symbol(signal.get("direction", "neutral"))
        strength = signal.get("strength", 1)
        
        if strength >= 3:
            priority = "HIGH PRIORITY"
        elif strength >= 2:
            priority = "MODERATE"
        else:
            priority = "LOW"
        
        message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SIGNAL ALERT | {priority}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>{signal.get('name', 'Signal')}</b>
{direction}

OBSERVATION:
{signal.get('observation', 'N/A')}

IMPLICATION:
{signal.get('implication', 'N/A')}

ACTION:
{signal.get('action', 'N/A')}

INVALIDATION:
{signal.get('invalidation', 'N/A')}

Edge Decay: {signal.get('edge_decay_hours', 'N/A')}h
Source: {signal.get('source', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sovereign Intel Terminal
"""
        return message.strip()
    
    def format_regime_change_alert(self, old_regime: str, new_regime: str, confidence: float) -> str:
        """Format a regime change as Telegram message."""
        regime_actions = {
            "capitulation": "Consider accumulation. Scale in slowly over 2-4 weeks.",
            "accumulation": "Build positions. Prioritize spot over leverage.",
            "risk_on": "Trail stops. Use pullbacks as entry opportunities.",
            "distribution": "Take profits. Reduce leverage. Raise stops.",
            "euphoria": "This is NOT the time to buy. Scale out positions.",
            "risk_off": "Reduce exposure. Watch for capitulation signals.",
            "ranging": "Exercise patience. Avoid large positions."
        }
        
        message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGIME CHANGE ALERT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{old_regime.upper()} --> {new_regime.upper()}

Confidence: {confidence*100:.0f}%

RECOMMENDED ACTION:
{regime_actions.get(new_regime, 'Monitor closely.')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sovereign Intel Terminal
"""
        return message.strip()
    
    def format_daily_summary(self, analysis: Dict) -> str:
        """Format daily summary as Telegram message."""
        regime = analysis.get("regime", "ranging")
        confidence = analysis.get("regime_confidence", 0.5)
        signals = analysis.get("signals", [])
        
        # Count directions
        bullish = len([s for s in signals if s.get("direction") == "bullish"])
        bearish = len([s for s in signals if s.get("direction") == "bearish"])
        
        if bullish > bearish:
            bias = "BULLISH"
        elif bearish > bullish:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"
        
        message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DAILY SOVEREIGN INTEL SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Regime: {regime.upper()}
Confidence: {confidence*100:.0f}%
Bias: {bias}

Active Signals: {len(signals)}
"""
        
        # Add top signals
        for i, sig in enumerate(signals[:3], 1):
            direction = self._get_direction_symbol(sig.get("direction", "neutral"))
            message += f"\n{i}. {sig.get('name', 'Signal')} {direction}"
        
        if len(signals) > 3:
            message += f"\n   +{len(signals) - 3} more signals..."
        
        message += f"""

{datetime.now(timezone.utc).strftime('%B %d, %Y %H:%M UTC')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sovereign Intel Terminal
"""
        return message.strip()
    
    def check_and_alert(self) -> Dict[str, Any]:
        """
        Run analysis and send alerts for:
        - New signals (not seen before)
        - Regime changes
        
        Returns summary of what was sent.
        """
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alerts_sent": 0,
            "regime_change": False,
            "new_signals": []
        }
        
        # Run analysis
        if os.environ.get("FRED_API_KEY"):
            analysis = self.terminal.run_full_with_macro()
        else:
            analysis = self.terminal.run()
        
        current_regime = analysis.get("regime", "ranging")
        current_signals = analysis.get("signals", [])
        
        # Load last known state
        last_regime_data = self._load_last_state(self.last_regime_file)
        last_signals_data = self._load_last_state(self.last_signals_file)
        
        last_regime = last_regime_data.get("regime")
        last_signal_names = set(last_signals_data.get("signal_names", []))
        
        # Check for regime change
        if last_regime and last_regime != current_regime:
            message = self.format_regime_change_alert(
                last_regime, 
                current_regime, 
                analysis.get("regime_confidence", 0.5)
            )
            if self.send_message(message):
                results["alerts_sent"] += 1
                results["regime_change"] = True
                logger.info(f"Regime change alert sent: {last_regime} -> {current_regime}")
        
        # Check for new signals
        current_signal_names = set(s.get("name", "") for s in current_signals)
        new_signal_names = current_signal_names - last_signal_names
        
        for signal in current_signals:
            if signal.get("name") in new_signal_names:
                # Only alert for moderate+ strength signals
                if signal.get("strength", 1) >= 2:
                    message = self.format_signal_alert(signal)
                    if self.send_message(message):
                        results["alerts_sent"] += 1
                        results["new_signals"].append(signal.get("name"))
                        logger.info(f"New signal alert sent: {signal.get('name')}")
        
        # Save current state
        self._save_last_state(self.last_regime_file, {
            "regime": current_regime,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self._save_last_state(self.last_signals_file, {
            "signal_names": list(current_signal_names),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return results
    
    def send_daily_summary(self) -> bool:
        """Send daily summary digest."""
        if os.environ.get("FRED_API_KEY"):
            analysis = self.terminal.run_full_with_macro()
        else:
            analysis = self.terminal.run()
        
        message = self.format_daily_summary(analysis)
        return self.send_message(message)
    
    def send_test_message(self) -> bool:
        """Send a test message to verify setup."""
        message = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST MESSAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Telegram alerts are configured correctly.

You will receive:
- High priority signal alerts
- Regime change notifications  
- Daily summary digests

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sovereign Intel Terminal
"""
        return self.send_message(message.strip())


# ============================================================================
# SETUP HELPER
# ============================================================================

def print_setup_instructions():
    """Print Telegram setup instructions."""
    print("""
======================================================================
                    TELEGRAM ALERTS SETUP                              
======================================================================

STEP 1: Create a Telegram Bot
-----------------------------
1. Open Telegram and search for @BotFather
2. Send: /newbot
3. Follow prompts to name your bot
4. Copy the bot token (looks like: 123456789:ABCdefGHIjklMNOpqrSTUvwxYZ)

STEP 2: Get Your Chat ID
------------------------
1. Start a chat with your new bot
2. Send any message to it
3. Visit: https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
4. Find "chat":{"id": YOUR_CHAT_ID}

STEP 3: Set Environment Variables
---------------------------------
In Replit Secrets (or export):

   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here

STEP 4: Test the Connection
---------------------------
   python3 services/telegram_alerts.py test

STEP 5: Enable Alerts
---------------------
Add to your scheduled task or run:

   python3 services/telegram_alerts.py check

This will send alerts for new signals and regime changes.

======================================================================
""")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    bot = TelegramAlertBot()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "setup":
            print_setup_instructions()
        
        elif cmd == "test":
            if not bot.is_configured:
                print("ERROR: Telegram not configured!")
                print("   Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
                print("   Run: python3 services/telegram_alerts.py setup")
            else:
                print("Sending test message...")
                if bot.send_test_message():
                    print("SUCCESS: Test message sent! Check your Telegram.")
                else:
                    print("ERROR: Failed to send test message.")
        
        elif cmd == "check":
            if not bot.is_configured:
                print("ERROR: Telegram not configured!")
            else:
                print("Checking for alerts...")
                results = bot.check_and_alert()
                print(f"SUCCESS: Check complete")
                print(f"   Alerts sent: {results['alerts_sent']}")
                print(f"   Regime change: {results['regime_change']}")
                print(f"   New signals: {results['new_signals']}")
        
        elif cmd == "summary":
            if not bot.is_configured:
                print("ERROR: Telegram not configured!")
            else:
                print("Sending daily summary...")
                if bot.send_daily_summary():
                    print("SUCCESS: Summary sent!")
                else:
                    print("ERROR: Failed to send summary.")
        
        else:
            print("Usage: python3 telegram_alerts.py [setup|test|check|summary]")
    
    else:
        # Default: show setup if not configured, otherwise check for alerts
        if bot.is_configured:
            results = bot.check_and_alert()
            print(f"Alerts sent: {results['alerts_sent']}")
        else:
            print_setup_instructions()
