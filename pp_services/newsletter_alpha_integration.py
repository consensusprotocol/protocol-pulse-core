"""
NEWSLETTER ALPHA INTEGRATION
============================
Integrates Sovereign Intel Terminal with the daily newsletter.

TWO TIERS:
- FREE: Regime + top signal + market snapshot
- PREMIUM: Full signal board + all actionable intelligence + triggers

This module generates HTML sections that plug into the existing newsletter.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Add services to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sovereign_intel_terminal import (
    SovereignIntelTerminal, 
    Signal, 
    Regime,
    Direction,
    SignalStrength
)

logger = logging.getLogger("NewsletterAlpha")


class NewsletterAlphaGenerator:
    """
    Generates HTML sections for newsletter integration.
    """
    
    def __init__(self):
        self.terminal = SovereignIntelTerminal()
        
        # Color scheme matching your newsletter
        self.colors = {
            "background": "#0d0d0d",
            "card_bg": "#1a1a1a",
            "border": "#ff3131",
            "accent": "#ff3131",
            "text": "#ffffff",
            "text_muted": "#888888",
            "bullish": "#00ff88",
            "bearish": "#ff4444",
            "neutral": "#ffaa00",
        }
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run full analysis and return results."""
        # Check for FRED key
        if os.environ.get("FRED_API_KEY"):
            return self.terminal.run_full_with_macro()
        else:
            return self.terminal.run()
    
    def _get_direction_color(self, direction: str) -> str:
        """Get color for direction."""
        if direction == "bullish":
            return self.colors["bullish"]
        elif direction == "bearish":
            return self.colors["bearish"]
        return self.colors["neutral"]
    
    def _get_direction_icon(self, direction: str) -> str:
        """Get icon for direction."""
        if direction == "bullish":
            return "↑"
        elif direction == "bearish":
            return "↓"
        return "→"
    
    def _get_strength_badge(self, strength: int) -> str:
        """Get badge HTML for signal strength."""
        if strength >= 3:
            return f'<span style="background: {self.colors["bearish"]}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">HIGH PRIORITY</span>'
        elif strength >= 2:
            return f'<span style="background: {self.colors["neutral"]}; color: black; padding: 2px 8px; border-radius: 4px; font-size: 11px;">MONITOR</span>'
        return f'<span style="background: {self.colors["text_muted"]}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">AWARENESS</span>'
    
    def _get_regime_description(self, regime: str) -> Dict[str, str]:
        """Get regime description and recommendation."""
        descriptions = {
            "capitulation": {
                "title": "CAPITULATION",
                "emoji": "🩸",
                "description": "Market in extreme fear. Historically where generational wealth is made.",
                "action": "Consider accumulation. Scale in slowly over 2-4 weeks.",
                "color": self.colors["bullish"]
            },
            "accumulation": {
                "title": "ACCUMULATION",
                "emoji": "🎯",
                "description": "Smart money accumulating while retail sells. Early bull phase.",
                "action": "Build positions. Prioritize spot over leverage.",
                "color": self.colors["bullish"]
            },
            "risk_on": {
                "title": "RISK ON",
                "emoji": "🚀",
                "description": "Market trending up with momentum. Favorable for longs.",
                "action": "Trail stops. Use pullbacks as entry opportunities.",
                "color": self.colors["bullish"]
            },
            "distribution": {
                "title": "DISTRIBUTION",
                "emoji": "⚠️",
                "description": "Smart money distributing to retail. Late cycle warning.",
                "action": "Take profits. Reduce leverage. Raise stops.",
                "color": self.colors["neutral"]
            },
            "euphoria": {
                "title": "EUPHORIA",
                "emoji": "🎪",
                "description": "Extreme greed. Everyone bullish. Tops form here.",
                "action": "This is NOT the time to buy. Scale out positions.",
                "color": self.colors["bearish"]
            },
            "risk_off": {
                "title": "RISK OFF",
                "emoji": "🛡️",
                "description": "Market trending down. Favor cash and caution.",
                "action": "Reduce exposure. Watch for capitulation signals.",
                "color": self.colors["bearish"]
            },
            "ranging": {
                "title": "RANGING",
                "emoji": "⏳",
                "description": "No clear direction. Patience required.",
                "action": "Avoid large positions. Wait for clarity.",
                "color": self.colors["neutral"]
            }
        }
        return descriptions.get(regime, descriptions["ranging"])
    
    def generate_free_tier_html(self, analysis: Dict[str, Any]) -> str:
        """
        Generate FREE tier alpha section.
        Shows: Regime + market snapshot + top signal only
        """
        regime = analysis.get("regime", "ranging")
        regime_info = self._get_regime_description(regime)
        signals = analysis.get("signals", [])
        
        # Get top signal
        top_signal = signals[0] if signals else None
        
        # Get market data from the report
        # Parse from stored datapoints
        report = analysis.get("report", "")
        
        html = f'''
        <!-- ALPHA INTELLIGENCE SECTION - FREE TIER -->
        <div style="background: linear-gradient(135deg, {self.colors["card_bg"]} 0%, #0a0a0a 100%); border: 1px solid {self.colors["border"]}; border-radius: 12px; padding: 24px; margin: 24px 0;">
            
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: {self.colors["accent"]}; margin: 0; font-size: 18px; letter-spacing: 2px;">
                    ⚡ SOVEREIGN INTEL BRIEF ⚡
                </h2>
                <p style="color: {self.colors["text_muted"]}; margin: 8px 0 0 0; font-size: 12px;">
                    {datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")}
                </p>
            </div>
            
            <!-- Regime Box -->
            <div style="background: {self.colors["background"]}; border-left: 4px solid {regime_info['color']}; padding: 16px; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 32px;">{regime_info['emoji']}</span>
                    <div>
                        <h3 style="color: {regime_info['color']}; margin: 0; font-size: 20px;">
                            REGIME: {regime_info['title']}
                        </h3>
                        <p style="color: {self.colors["text"]}; margin: 4px 0 0 0; font-size: 14px;">
                            {regime_info['description']}
                        </p>
                    </div>
                </div>
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid {self.colors["border"]};">
                    <p style="color: {self.colors["text_muted"]}; margin: 0; font-size: 13px;">
                        <strong style="color: {self.colors["text"]};">Operator Action:</strong> {regime_info['action']}
                    </p>
                </div>
            </div>
        '''
        
        # Top Signal (if exists)
        if top_signal:
            direction_color = self._get_direction_color(top_signal.get("direction", "neutral"))
            direction_icon = self._get_direction_icon(top_signal.get("direction", "neutral"))
            strength_badge = self._get_strength_badge(top_signal.get("strength", 1))
            
            html += f'''
            <!-- Top Signal -->
            <div style="background: {self.colors["background"]}; border: 1px solid {direction_color}; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h4 style="color: {direction_color}; margin: 0; font-size: 16px;">
                        {direction_icon} {top_signal.get("name", "Signal")}
                    </h4>
                    {strength_badge}
                </div>
                <p style="color: {self.colors["text"]}; margin: 0 0 12px 0; font-size: 14px;">
                    {top_signal.get("observation", "")}
                </p>
                <p style="color: {self.colors["text_muted"]}; margin: 0; font-size: 13px;">
                    <strong style="color: {self.colors["text"]};">Action:</strong> {top_signal.get("action", "")}
                </p>
            </div>
            '''
        
        # Upgrade CTA
        html += f'''
            <!-- Upgrade CTA -->
            <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, rgba(255,49,49,0.1) 0%, rgba(255,49,49,0.05) 100%); border-radius: 8px; border: 1px dashed {self.colors["border"]};">
                <p style="color: {self.colors["text"]}; margin: 0 0 12px 0; font-size: 14px;">
                    🔒 <strong>{len(signals) - 1 if len(signals) > 1 else 0} more signals</strong> available for Premium subscribers
                </p>
                <p style="color: {self.colors["text_muted"]}; margin: 0 0 16px 0; font-size: 13px;">
                    Full signal board • Invalidation triggers • Macro correlations • Backtest data
                </p>
                <a href="https://protocolpulse.substack.com/subscribe" style="display: inline-block; background: {self.colors["accent"]}; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 14px;">
                    UPGRADE TO PREMIUM →
                </a>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; margin-top: 16px;">
                <p style="color: {self.colors["text_muted"]}; margin: 0; font-size: 11px;">
                    SOVEREIGN INTEL TERMINAL │ Receipts Over Vibes │ Signal Over Noise
                </p>
            </div>
        </div>
        '''
        
        return html
    
    def generate_premium_tier_html(self, analysis: Dict[str, Any]) -> str:
        """
        Generate PREMIUM tier alpha section.
        Shows: Everything - full signal board, all intelligence, triggers, macro
        """
        regime = analysis.get("regime", "ranging")
        regime_info = self._get_regime_description(regime)
        regime_confidence = analysis.get("regime_confidence", 0.5)
        signals = analysis.get("signals", [])
        
        html = f'''
        <!-- ALPHA INTELLIGENCE SECTION - PREMIUM TIER -->
        <div style="background: linear-gradient(135deg, {self.colors["card_bg"]} 0%, #0a0a0a 100%); border: 2px solid {self.colors["border"]}; border-radius: 12px; padding: 24px; margin: 24px 0;">
            
            <!-- Premium Badge -->
            <div style="text-align: center; margin-bottom: 16px;">
                <span style="background: linear-gradient(135deg, {self.colors["accent"]} 0%, #cc0000 100%); color: white; padding: 4px 16px; border-radius: 20px; font-size: 11px; letter-spacing: 2px;">
                    ★ PREMIUM INTELLIGENCE ★
                </span>
            </div>
            
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: {self.colors["accent"]}; margin: 0; font-size: 22px; letter-spacing: 2px;">
                    ⚡ SOVEREIGN INTEL TERMINAL ⚡
                </h2>
                <p style="color: {self.colors["text_muted"]}; margin: 8px 0 0 0; font-size: 12px;">
                    {datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")} │ {len(signals)} Active Signals
                </p>
            </div>
            
            <!-- Regime Box -->
            <div style="background: {self.colors["background"]}; border-left: 4px solid {regime_info['color']}; padding: 16px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 36px;">{regime_info['emoji']}</span>
                        <div>
                            <h3 style="color: {regime_info['color']}; margin: 0; font-size: 22px;">
                                REGIME: {regime_info['title']}
                            </h3>
                            <p style="color: {self.colors["text"]}; margin: 4px 0 0 0; font-size: 14px;">
                                {regime_info['description']}
                            </p>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: {self.colors["text_muted"]}; font-size: 12px;">CONFIDENCE</span>
                        <div style="color: {regime_info['color']}; font-size: 24px; font-weight: bold;">
                            {regime_confidence*100:.0f}%
                        </div>
                    </div>
                </div>
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid {self.colors["border"]};">
                    <p style="color: {self.colors["bullish"]}; margin: 0; font-size: 14px; font-weight: bold;">
                        ✓ {regime_info['action']}
                    </p>
                </div>
            </div>
        '''
        
        # Signal Board Table
        if signals:
            html += f'''
            <!-- Signal Board -->
            <div style="margin-bottom: 20px;">
                <h4 style="color: {self.colors["text"]}; margin: 0 0 12px 0; font-size: 14px; letter-spacing: 1px;">
                    📊 SIGNAL BOARD
                </h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <thead>
                        <tr style="border-bottom: 1px solid {self.colors["border"]};">
                            <th style="text-align: left; padding: 8px; color: {self.colors["text_muted"]};">Signal</th>
                            <th style="text-align: right; padding: 8px; color: {self.colors["text_muted"]};">Value</th>
                            <th style="text-align: right; padding: 8px; color: {self.colors["text_muted"]};">Z-Score</th>
                            <th style="text-align: center; padding: 8px; color: {self.colors["text_muted"]};">Direction</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            
            for sig in signals:
                direction_color = self._get_direction_color(sig.get("direction", "neutral"))
                direction_icon = self._get_direction_icon(sig.get("direction", "neutral"))
                zscore = sig.get("zscore")
                zscore_str = f"{zscore:.2f}σ" if zscore else "N/A"
                
                html += f'''
                        <tr style="border-bottom: 1px solid {self.colors["card_bg"]};">
                            <td style="padding: 10px 8px; color: {self.colors["text"]};">{sig.get("name", "")}</td>
                            <td style="padding: 10px 8px; color: {self.colors["text"]}; text-align: right; font-family: monospace;">{sig.get("value", 0):.4f}</td>
                            <td style="padding: 10px 8px; color: {self.colors["text_muted"]}; text-align: right; font-family: monospace;">{zscore_str}</td>
                            <td style="padding: 10px 8px; text-align: center;">
                                <span style="color: {direction_color}; font-size: 16px;">{direction_icon}</span>
                            </td>
                        </tr>
                '''
            
            html += '''
                    </tbody>
                </table>
            </div>
            '''
        
        # Detailed Signal Intelligence
        if signals:
            html += f'''
            <!-- Detailed Intelligence -->
            <div style="margin-bottom: 20px;">
                <h4 style="color: {self.colors["text"]}; margin: 0 0 12px 0; font-size: 14px; letter-spacing: 1px;">
                    🎯 ACTIONABLE INTELLIGENCE
                </h4>
            '''
            
            for i, sig in enumerate(signals, 1):
                direction_color = self._get_direction_color(sig.get("direction", "neutral"))
                direction_icon = self._get_direction_icon(sig.get("direction", "neutral"))
                strength_badge = self._get_strength_badge(sig.get("strength", 1))
                
                html += f'''
                <div style="background: {self.colors["background"]}; border-left: 3px solid {direction_color}; padding: 14px; margin-bottom: 12px; border-radius: 0 6px 6px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h5 style="color: {direction_color}; margin: 0; font-size: 15px;">
                            {i}. {direction_icon} {sig.get("name", "")}
                        </h5>
                        {strength_badge}
                    </div>
                    <div style="font-size: 13px; line-height: 1.6;">
                        <p style="color: {self.colors["text"]}; margin: 0 0 8px 0;">
                            <strong>Observation:</strong> {sig.get("observation", "")}
                        </p>
                        <p style="color: {self.colors["text"]}; margin: 0 0 8px 0;">
                            <strong>Implication:</strong> {sig.get("implication", "")}
                        </p>
                        <p style="color: {self.colors["bullish"]}; margin: 0 0 8px 0;">
                            <strong>✓ Action:</strong> {sig.get("action", "")}
                        </p>
                        <p style="color: {self.colors["bearish"]}; margin: 0;">
                            <strong>✗ Invalidation:</strong> {sig.get("invalidation", "")}
                        </p>
                    </div>
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid {self.colors["card_bg"]}; display: flex; gap: 16px; font-size: 11px; color: {self.colors["text_muted"]};">
                        <span>Edge Decay: {sig.get("edge_decay_hours", "N/A")}h</span>
                        <span>Source: {sig.get("source", "N/A")}</span>
                        <span>Data Points: {sig.get("datapoints_used", "N/A")}</span>
                    </div>
                </div>
                '''
            
            html += '</div>'
        
        # Operator Checklist
        html += f'''
            <!-- Operator Checklist -->
            <div style="background: {self.colors["background"]}; border: 1px solid {self.colors["border"]}; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                <h4 style="color: {self.colors["accent"]}; margin: 0 0 12px 0; font-size: 14px;">
                    ☑️ OPERATOR CHECKLIST ({regime_info['title']})
                </h4>
                <div style="font-size: 13px; color: {self.colors["text"]};">
        '''
        
        checklists = {
            "capitulation": [
                "This is where generational wealth is made",
                "Begin accumulation if dry powder available",
                "Scale in slowly - don't catch exact bottom",
                "Ignore the noise - focus on signal"
            ],
            "accumulation": [
                "Scale into positions during fear spikes",
                "Prioritize spot over leverage",
                "Set DCA schedule if not active",
                "Move coins to cold storage"
            ],
            "risk_on": [
                "Trend is favorable for longs",
                "Use pullbacks as entry opportunities",
                "Monitor leverage for crowding",
                "Trail stops as position develops"
            ],
            "distribution": [
                "Take profits at target levels",
                "Reduce or eliminate leverage",
                "Raise stops to protect gains",
                "Do NOT FOMO into breakouts"
            ],
            "euphoria": [
                "This is NOT the time to buy",
                "Scale out remaining positions",
                "Secure profits to cold storage",
                "Prepare dry powder for correction"
            ],
            "risk_off": [
                "Reduce risk exposure",
                "Favor cash/stables over positions",
                "Watch for capitulation signals",
                "Prepare shopping list"
            ],
            "ranging": [
                "Exercise patience - no clear edge",
                "Avoid large new positions",
                "Focus on improving systems",
                "Wait for regime clarity"
            ]
        }
        
        for item in checklists.get(regime, checklists["ranging"]):
            html += f'<p style="margin: 8px 0;">☐ {item}</p>'
        
        html += f'''
                </div>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; padding-top: 16px; border-top: 1px solid {self.colors["border"]};">
                <p style="color: {self.colors["text_muted"]}; margin: 0; font-size: 11px;">
                    This is intelligence, not financial advice. Self-custody your Bitcoin.
                </p>
                <p style="color: {self.colors["accent"]}; margin: 8px 0 0 0; font-size: 12px; letter-spacing: 1px;">
                    SOVEREIGN INTEL TERMINAL │ Receipts Over Vibes │ Signal Over Noise
                </p>
            </div>
        </div>
        '''
        
        return html
    
    def generate_newsletter_section(self, is_premium: bool = False) -> Dict[str, Any]:
        """
        Main entry point: generates newsletter section based on tier.
        
        Returns dict with:
        - html: The HTML content
        - analysis: The raw analysis data
        - tier: "free" or "premium"
        """
        # Run analysis
        analysis = self.run_analysis()
        
        # Generate appropriate HTML
        if is_premium:
            html = self.generate_premium_tier_html(analysis)
            tier = "premium"
        else:
            html = self.generate_free_tier_html(analysis)
            tier = "free"
        
        return {
            "html": html,
            "analysis": analysis,
            "tier": tier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signals_count": len(analysis.get("signals", [])),
            "regime": analysis.get("regime", "ranging")
        }


# ============================================================================
# INTEGRATION FUNCTIONS FOR newsletter_engine.py
# ============================================================================

def get_alpha_section_for_newsletter(is_premium: bool = False) -> str:
    """
    Simple function to get alpha HTML section for newsletter.
    Call this from your newsletter_engine.py
    """
    generator = NewsletterAlphaGenerator()
    result = generator.generate_newsletter_section(is_premium=is_premium)
    return result["html"]


def get_alpha_data_for_newsletter() -> Dict[str, Any]:
    """
    Get raw alpha data for custom integration.
    """
    generator = NewsletterAlphaGenerator()
    return generator.run_analysis()


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    
    generator = NewsletterAlphaGenerator()
    
    tier = "free"
    if len(sys.argv) > 1:
        tier = sys.argv[1]
    
    is_premium = tier.lower() == "premium"
    
    result = generator.generate_newsletter_section(is_premium=is_premium)
    
    # Save HTML to file for preview
    filename = f"data/newsletter_alpha_{tier}.html"
    with open(filename, "w") as f:
        f.write(f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Newsletter Alpha Section - {tier.upper()}</title>
    <style>
        body {{
            background: #0d0d0d;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            max-width: 600px;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
{result["html"]}
</body>
</html>
        ''')
    
    print(f"✅ Generated {tier.upper()} tier newsletter section")
    print(f"   Saved to: {filename}")
    print(f"   Regime: {result['regime'].upper()}")
    print(f"   Signals: {result['signals_count']}")
    print(f"\n   Preview: Open {filename} in browser")
