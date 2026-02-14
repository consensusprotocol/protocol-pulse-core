import json
import logging
import os
import re
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Grok API service using xAI's OpenAI-compatible API
class GrokService:
    def __init__(self):
        self.api_key = os.environ.get('XAI_API_KEY')
        if not self.api_key:
            logging.warning("XAI_API_KEY missing. Grok narrative intelligence offline.")
            self.client = None
            self.model = None
        elif OpenAI is None:
            logging.warning("openai package not available. Grok offline.")
            self.client = None
            self.model = None
        else:
            try:
                self.client = OpenAI(
                    base_url="https://api.x.ai/v1",
                    api_key=self.api_key
                )
                self.model = "grok-3"
                logging.info("Grok service initialized successfully")
            except Exception as e:
                logging.warning("Grok init failed: %s", e)
                self.client = None
                self.model = None

    def generate_bitcoin_article(self, topic, article_type="news"):
        """Generate Bitcoin-focused content using Grok"""
        if not self.client:
            return "Error: Grok unavailable (no API key)."
        prompts = {
            "news": f"Write a professional Bitcoin news article about: {topic}. Include market insights and technical analysis. Focus on factual reporting with expert perspective.",
            "analysis": f"Create an in-depth Bitcoin analysis piece about: {topic}. Include technical indicators, market sentiment, and potential price implications.",
            "breaking": f"Write urgent breaking news about Bitcoin: {topic}. Keep it concise, factual, and include immediate market impact."
        }
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional Bitcoin and cryptocurrency journalist writing for Protocol Pulse, a leading Web3 media network. Write engaging, accurate, and insightful content that appeals to both beginners and experts."
                    },
                    {
                        "role": "user", 
                        "content": prompts.get(article_type, prompts["news"])
                    }
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Grok API error: {e}")
            return f"Error generating content: {str(e)}"

    def generate_defi_article(self, topic, focus_area="general"):
        """Generate DeFi-focused content using Grok"""
        if not self.client:
            return "Error: Grok unavailable (no API key)."
        focus_prompts = {
            "general": f"Write a comprehensive DeFi article about: {topic}. Explain concepts clearly and include practical implications for users.",
            "protocols": f"Analyze the DeFi protocol: {topic}. Cover tokenomics, security, yield opportunities, and risks.",
            "trends": f"Explore the latest DeFi trend: {topic}. Include adoption metrics, ecosystem impact, and future outlook."
        }
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert DeFi analyst writing for Protocol Pulse. Create informative content that helps readers understand complex DeFi concepts while highlighting opportunities and risks."
                    },
                    {
                        "role": "user",
                        "content": focus_prompts.get(focus_area, focus_prompts["general"])
                    }
                ],
                max_tokens=1500,
                temperature=0.6
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Grok API error: {e}")
            return f"Error generating DeFi content: {str(e)}"

    def analyze_market_sentiment(self, text_data):
        """Analyze market sentiment of crypto-related text"""
        if not self.client:
            return {"error": "Grok unavailable (no API key)."}
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze the sentiment of cryptocurrency/Bitcoin related text. Provide a JSON response with: sentiment (bullish/bearish/neutral), confidence (0-1), key_factors (array), and summary."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this crypto market text: {text_data}"
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
            return {"error": "Empty response"}
            
        except Exception as e:
            logging.error(f"Sentiment analysis error: {e}")
            return {"error": str(e)}

    def generate_podcast_script(self, topic, duration_minutes=10):
        """Generate podcast script for Bitcoin/DeFi topics"""
        if not self.client:
            return "Error: Grok unavailable (no API key)."
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"Create an engaging {duration_minutes}-minute podcast script for Protocol Pulse. Include intro, main content with key points, and outro. Make it conversational and informative."
                    },
                    {
                        "role": "user",
                        "content": f"Create a podcast script about: {topic}"
                    }
                ],
                max_tokens=2000,
                temperature=0.8
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Podcast script error: {e}")
            return f"Error generating podcast script: {str(e)}"

    def review_article(self, title, content, topic):
        """Review article for accuracy, depth, Bitcoin facts. Returns {decision, reason, score}."""
        if not self.client:
            return {"decision": "REJECT", "reason": "Grok unavailable", "score": 0}
        try:
            prompt = f"""Review this article for accuracy, depth, and Bitcoin facts. Verify against current data: block reward is 3.125 BTC in 2026 (post-halving), not 6.25.

TITLE: {title}
TOPIC: {topic}
CONTENT (excerpt): {(content or '')[:3000]}

Decision: APPROVE or REJECT. Reason: detailed. Score: 1-10.
Respond with JSON only: {{"decision": "APPROVE" or "REJECT", "reason": "...", "score": N}}"""
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            raw = response.choices[0].message.content if response and response.choices else None
            if not raw:
                return {"decision": "REJECT", "reason": "Empty response", "score": 0}
            data = json.loads(raw)
            return {
                "decision": (data.get("decision") or "REJECT").upper()[:7],
                "reason": data.get("reason", ""),
                "score": int(data.get("score", 0)),
            }
        except Exception as e:
            logging.error("Grok review failed: %s", e)
            return {"decision": "REJECT", "reason": str(e), "score": 0}

    def generate_reel_narration_script(
        self,
        *,
        channel_name: str = "Partner",
        segments_summary: str = "",
        num_clips: int = 3,
    ) -> dict:
        """Generate Bloomberg-style news brief script for viral reel voiceover.
        Returns JSON: {intro, insights[], cta1, cta2} – each 10–20s spoken (smooth, professional).
        """
        if not self.client:
            return {"error": "Grok unavailable (no API key)."}
        try:
            prompt = f"""Generate a smooth news brief script for a short-form video reel, Bloomberg style, professional narrator.
Channel/source: {channel_name or 'Partner'}.
Segment context: {segments_summary[:800] if segments_summary else 'Bitcoin and market insights.'}
Number of clip insights to write: {max(1, min(num_clips, 5))}.

Output valid JSON only, no markdown, with these exact keys:
- "intro": one short paragraph (10–20 seconds when read aloud), sets the tone as a crisp news brief.
- "insights": array of {max(1, min(num_clips, 5))} strings; each 1–2 sentences (10–20s per clip), insight per clip.
- "cta1": one short line urging viewers to subscribe (5–10s).
- "cta2": one short line directing to protocolpulsehq.com (5–10s).

Style: authoritative, concise, no filler. Professional narrator. Two CTAs to subscribe and protocolpulsehq.com."""
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You output only valid JSON. No markdown code fences, no extra text."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1200,
                temperature=0.5,
            )
            raw = (response.choices[0].message.content or "").strip()
            if not raw:
                return {"error": "Empty response"}
            # Strip markdown code block if present
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logging.warning("Grok narration JSON parse failed: %s", e)
            return {"error": f"Invalid JSON: {e}"}
        except Exception as e:
            logging.error("Grok reel script error: %s", e)
            return {"error": str(e)}

# Initialize the service (key optional - never crash app)
try:
    grok_service = GrokService()
except Exception as e:
    logging.warning("Grok service failed to initialize: %s", e)
    grok_service = GrokService.__new__(GrokService)
    grok_service.client = None
    grok_service.model = None