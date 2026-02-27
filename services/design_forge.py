"""
Design Forge - AI-Powered Ethos Statement Generator
Generates minimalist, high-status apparel designs using Gemini API.
Part of the Real-Time Sovereign Apparel (RTSA) Engine.
"""

import os
import logging
import json
import base64
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


ETHOS_PROMPT_TEMPLATE = """You are the Design Forge for Protocol Pulse, a world-class Bitcoin intelligence network.

Generate an "Ethos Statement" for premium apparel based on the current network sentiment.

CURRENT NETWORK STATE:
- Sentiment State: {state}
- Sentiment Score: {score}/100
- Primary Keywords: {keywords}
- Event Trigger: {trigger}

BRANDING RULES (CRITICAL - Follow exactly):
1. MINIMALISM: Maximum 5 words. Fewer is better.
2. AUTHORITATIVE: Use terms like "Settlement", "Liquidity", "Sovereignty", "Moat", "Conviction", "Protocol", "Network", "Signal", "Inevitable"
3. NO CRINGE: Never use "moon", "lambo", "wagmi", "hodl", "ngmi", or meme language
4. TONE: Institutional, confident, inevitable. Like a Fortune 500 annual report meets cypherpunk manifesto.
5. STYLE: All caps or title case. No exclamation marks.

EXAMPLE OUTPUTS BY STATE:
- ABSOLUTE_SINGULARITY + ETF keywords: "INSTITUTIONAL SETTLEMENT: INEVITABLE"
- CONSENSUS_FORMING + adoption: "THE NETWORK KNOWS"
- FRAGMENTED_SIGNAL + volatility: "CONVICTION FORGED IN CHAOS"
- CRITICAL_CONTENTION + FUD: "VOLATILITY IS THE TOLL"
- EQUILIBRIUM + accumulation: "SILENT ACCUMULATION"

OUTPUT FORMAT (JSON only, no markdown):
{{
    "statement": "YOUR ETHOS STATEMENT HERE",
    "placement": "center_chest" or "left_chest_badge",
    "text_color": "#FFFFFF" or "#DC2626",
    "sarah_note": "A 1-sentence description in Sarah's voice explaining the significance"
}}

Generate a statement that operatives would proudly wear as a physical record of this network moment."""


def generate_ethos_statement(
    state: str,
    score: float,
    keywords: list,
    trigger: str = "state_change"
) -> Optional[Dict]:
    """
    Generate an Ethos Statement using Gemini API.
    
    Args:
        state: Current sentiment state (e.g., 'ABSOLUTE_SINGULARITY')
        score: Sentiment score 0-100
        keywords: List of primary keywords from sentiment engine
        trigger: What triggered this generation (state_change, whale_event, etc.)
    
    Returns:
        Dict with statement, placement, text_color, sarah_note or None on failure
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY not configured for Design Forge")
        return None
    
    try:
        keywords_str = ", ".join([k.get('keyword', str(k)) if isinstance(k, dict) else str(k) for k in keywords[:5]])
        
        prompt = ETHOS_PROMPT_TEMPLATE.format(
            state=state,
            score=score,
            keywords=keywords_str or "Bitcoin, Network",
            trigger=trigger
        )
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 500,
                "responseMimeType": "application/json"
            }
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'candidates' in data and len(data['candidates']) > 0:
            content = data['candidates'][0].get('content', {})
            parts = content.get('parts', [])
            if parts:
                text = parts[0].get('text', '{}')
                result = json.loads(text)
                
                statement = result.get('statement', '')
                if len(statement.split()) > 6:
                    words = statement.split()[:5]
                    statement = ' '.join(words)
                
                return {
                    'statement': statement.upper(),
                    'placement': result.get('placement', 'center_chest'),
                    'text_color': result.get('text_color', '#FFFFFF'),
                    'sarah_note': result.get('sarah_note', f"This garment serves as a physical record of the {datetime.utcnow().strftime('%Y-%m-%d')} network inflection. Wear the signal.")
                }
        
        logger.error(f"Unexpected Gemini response format: {data}")
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"Design Forge JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"Design Forge error: {e}")
        return None


def generate_design_image(
    statement: str,
    text_color: str = "#FFFFFF",
    placement: str = "center_chest"
) -> Optional[str]:
    """
    Generate a transparent PNG design for Printful using Gemini Imagen 3.
    
    Args:
        statement: The ethos statement text
        text_color: Hex color for text (#FFFFFF or #DC2626)
        placement: Design placement style
    
    Returns:
        Base64 encoded PNG data or None on failure
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY not configured for image generation")
        return None
    
    try:
        color_name = "pure white" if text_color == "#FFFFFF" else "crimson red"
        
        if placement == "left_chest_badge":
            prompt = f"""Create a minimalist typography design for a t-shirt left chest badge.
Text: "{statement}"
Style: Clean, modern, institutional typography similar to JetBrains Mono font.
Color: {color_name} text only, no background.
Size: Small badge format, approximately 3x2 inches.
Background: MUST be completely transparent (no background at all).
Design must be print-ready with clean edges."""
        else:
            prompt = f"""Create a minimalist typography design for a t-shirt center chest print.
Text: "{statement}"
Style: Clean, bold, modern typography similar to JetBrains Mono font. High contrast.
Color: {color_name} text only, no background.
Size: Large center chest format, approximately 12x4 inches.
Background: MUST be completely transparent (no background at all).
Design must be print-ready with crisp, clean edges."""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.4
            }
        }
        
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        if 'candidates' in data and len(data['candidates']) > 0:
            content = data['candidates'][0].get('content', {})
            parts = content.get('parts', [])
            for part in parts:
                if 'inlineData' in part:
                    return part['inlineData'].get('data')
        
        logger.warning("Image generation did not return inline data - text-only response")
        return None
        
    except Exception as e:
        logger.error(f"Design image generation error: {e}")
        return None


def create_svg_design(
    statement: str,
    text_color: str = "#FFFFFF",
    placement: str = "center_chest"
) -> str:
    """
    Create an SVG design as fallback when image generation is unavailable.
    Uses JetBrains Mono styling.
    
    Returns:
        SVG string
    """
    if placement == "left_chest_badge":
        width, height = 200, 80
        font_size = 14
        y_offset = 45
    else:
        width, height = 600, 150
        font_size = 32
        y_offset = 90
    
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&amp;display=swap');
        .statement {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: {font_size}px;
            fill: {text_color};
            text-anchor: middle;
            dominant-baseline: middle;
        }}
    </style>
    <text x="{width // 2}" y="{y_offset}" class="statement">{statement}</text>
</svg>'''
    
    return svg


def forge_complete_design(
    state: str,
    score: float,
    keywords: list,
    trigger: str = "state_change"
) -> Optional[Dict]:
    """
    Complete design forge pipeline: Generate statement + design.
    
    Returns:
        Dict with all design data or None on failure
    """
    statement_data = generate_ethos_statement(state, score, keywords, trigger)
    if not statement_data:
        logger.error("Failed to generate ethos statement")
        return None
    
    image_data = generate_design_image(
        statement_data['statement'],
        statement_data['text_color'],
        statement_data['placement']
    )
    
    svg_fallback = create_svg_design(
        statement_data['statement'],
        statement_data['text_color'],
        statement_data['placement']
    )
    
    return {
        'statement': statement_data['statement'],
        'placement': statement_data['placement'],
        'text_color': statement_data['text_color'],
        'sarah_note': statement_data['sarah_note'],
        'image_base64': image_data,
        'svg_fallback': svg_fallback,
        'trigger_state': state,
        'trigger_score': score,
        'trigger_keywords': keywords,
        'generated_at': datetime.utcnow().isoformat()
    }


FOUNDATIONAL_STATEMENTS = [
    {
        'statement': 'SETTLEMENT IS INEVITABLE',
        'placement': 'center_chest',
        'text_color': '#FFFFFF',
        'sarah_note': 'The foundational truth of the Bitcoin network. Every transaction settles. Every block confirms. Inevitability is the protocol.'
    },
    {
        'statement': 'NOT YOUR KEYS',
        'placement': 'left_chest_badge',
        'text_color': '#DC2626',
        'sarah_note': 'The first law of sovereign custody. A warning and a declaration. Three words that separate operators from tourists.'
    },
    {
        'statement': 'VERIFY EVERYTHING',
        'placement': 'center_chest',
        'text_color': '#FFFFFF',
        'sarah_note': 'The cypherpunk imperative. Trust no third party. Run your own node. Verify your own reality.'
    },
    {
        'statement': 'CONVICTION OVER TIME',
        'placement': 'center_chest',
        'text_color': '#FFFFFF',
        'sarah_note': 'The only strategy that matters. Volatility tests conviction. Time rewards patience. The network favors the patient.'
    },
    {
        'statement': 'SIGNAL OVER NOISE',
        'placement': 'left_chest_badge',
        'text_color': '#DC2626',
        'sarah_note': 'The Protocol Pulse ethos. In a world of manufactured narratives, we extract signal. We are the radar.'
    }
]


def get_foundational_statements() -> list:
    """Return the 5 foundational ethos statements for always-available merch"""
    return FOUNDATIONAL_STATEMENTS
