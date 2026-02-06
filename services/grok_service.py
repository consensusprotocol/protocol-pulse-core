import os
import json
import logging
from openai import OpenAI

# Grok API service using xAI's OpenAI-compatible API
class GrokService:
    def __init__(self):
        self.api_key = os.environ.get('XAI_API_KEY')
        if not self.api_key:
            logging.warning("XAI_API_KEY missing. Grok narrative intelligence offline.")
            self.client = None
            self.model = None
        else:
            self.client = OpenAI(
                base_url="https://api.x.ai/v1",
                api_key=self.api_key
            )
            self.model = "grok-3"
            logging.info("Grok service initialized successfully")

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

    def test_connection(self):
        """Test the Grok API connection"""
        if not self.client:
            return False
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say 'Grok API connection successful!' in exactly those words."}],
                max_tokens=50
            )
            
            content = response.choices[0].message.content
            if content:
                result = content.strip()
                return "Grok API connection successful!" in result
            return False
            
        except Exception as e:
            logging.error(f"Connection test failed: {e}")
            return False

# Initialize the service (key optional - never crash app)
try:
    grok_service = GrokService()
except Exception as e:
    logging.warning("Grok service failed to initialize: %s", e)
    grok_service = GrokService.__new__(GrokService)
    grok_service.client = None
    grok_service.model = None