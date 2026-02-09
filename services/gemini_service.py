import os
import json
import logging

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    _GENAI_AVAILABLE = False


class GeminiService:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logging.warning("GEMINI_API_KEY missing. Narrative intelligence offline.")
            self.client = None
            self.text_model = None
            self.pro_model = None
        elif not _GENAI_AVAILABLE:
            logging.warning("google-genai not installed. Install with: pip install google-genai")
            self.client = None
            self.text_model = None
            self.pro_model = None
        else:
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = "gemini-2.0-flash"
            self.text_model = "gemini-2.5-flash"
            self.pro_model = "gemini-2.5-pro"
            logging.info("Gemini service initialized successfully")

    def generate_bitcoin_article(self, topic, article_type="news"):
        """Generate Bitcoin-focused content using Gemini"""
        if not self.client:
            return "Error: Gemini unavailable (no API key)."
        prompts = {
            "news": f"Write a professional Bitcoin news article about: {topic}. Include current market context, technical analysis insights, and potential implications for Bitcoin adoption.",
            "analysis": f"Create a comprehensive Bitcoin analysis about: {topic}. Include technical indicators, on-chain metrics, institutional sentiment, and price predictions.",
            "breaking": f"Write urgent Bitcoin breaking news about: {topic}. Focus on immediate market impact, key stakeholders affected, and short-term price implications."
        }
        
        try:
            system_instruction = "You are a professional Bitcoin journalist writing for Protocol Pulse, a leading Web3 media network. Create engaging, factual content that provides valuable insights for both newcomers and Bitcoin veterans."
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=prompts.get(article_type, prompts["news"]),
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=1500
                )
            )
            
            return response.text or "Error: Empty response from Gemini"
            
        except Exception as e:
            logging.error(f"Gemini Bitcoin article error: {e}")
            return f"Error generating Bitcoin content: {str(e)}"

    def generate_defi_article(self, topic, focus_area="general"):
        """Generate DeFi-focused content using Gemini"""
        if not self.client:
            return "Error: Gemini unavailable (no API key)."
        focus_prompts = {
            "general": f"Write a comprehensive DeFi article about: {topic}. Explain the technology clearly, highlight user benefits, and discuss potential risks.",
            "protocols": f"Analyze the DeFi protocol: {topic}. Cover its mechanism, tokenomics, yield opportunities, security considerations, and competitive position.",
            "trends": f"Explore the emerging DeFi trend: {topic}. Include adoption metrics, ecosystem impact, regulatory considerations, and future outlook."
        }
        
        try:
            system_instruction = "You are a DeFi expert analyst writing for Protocol Pulse. Create informative content that helps readers understand complex DeFi concepts while providing actionable insights and risk assessments."
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=focus_prompts.get(focus_area, focus_prompts["general"]),
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.6,
                    max_output_tokens=1500
                )
            )
            
            return response.text or "Error: Empty response from Gemini"
            
        except Exception as e:
            logging.error(f"Gemini DeFi article error: {e}")
            return f"Error generating DeFi content: {str(e)}"

    def analyze_market_sentiment(self, text_data):
        """Analyze crypto market sentiment using Gemini with structured output"""
        if not self.client:
            return {"error": "Gemini unavailable (no API key)."}
        try:
            system_instruction = (
                "Analyze cryptocurrency market sentiment from the provided text. "
                "Respond with JSON containing: sentiment (bullish/bearish/neutral), "
                "confidence (0-1), key_factors (array of strings), and summary (string)."
            )
            
            class MarketSentiment(BaseModel):
                sentiment: str
                confidence: float
                key_factors: list[str]
                summary: str
            
            response = self.client.models.generate_content(
                model=self.pro_model,
                contents=f"Analyze the sentiment of this cryptocurrency market text: {text_data}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=MarketSentiment,
                    temperature=0.3
                )
            )
            
            if response.text:
                return json.loads(response.text)
            else:
                return {"error": "Empty response from Gemini"}
            
        except Exception as e:
            logging.error(f"Gemini sentiment analysis error: {e}")
            return {"error": str(e)}

    def generate_podcast_script(self, topic, duration_minutes=10):
        """Generate podcast script for Bitcoin/DeFi topics using Gemini"""
        if not self.client:
            return "Error: Gemini unavailable (no API key)."
        try:
            system_instruction = (
                f"Create an engaging {duration_minutes}-minute podcast script for Protocol Pulse. "
                "Structure: compelling intro hook, main content with 3-4 key points, "
                "practical insights for listeners, and memorable outro with call-to-action. "
                "Make it conversational and accessible."
            )
            
            prompt = f"Create a podcast script about: {topic}"
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.8,
                    max_output_tokens=2000
                )
            )
            
            return response.text or "Error: Empty response from Gemini"
            
        except Exception as e:
            logging.error(f"Gemini podcast script error: {e}")
            return f"Error generating podcast script: {str(e)}"

    def summarize_content(self, text, max_words=150):
        """Summarize content with focus on crypto/Web3 key points"""
        if not self.client:
            return "Error: Gemini unavailable (no API key)."
        try:
            prompt = (
                f"Summarize the following text in {max_words} words or less, "
                f"focusing on key points relevant to cryptocurrency, blockchain, and Web3:\n\n{text}"
            )
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=max_words + 50
                )
            )
            
            return response.text or "Error: Empty response from Gemini"
            
        except Exception as e:
            logging.error(f"Gemini summarization error: {e}")
            return f"Error summarizing content: {str(e)}"

    def generate_content(self, prompt, system_prompt=None):
        """Generate general content using Gemini - primary method for content generation"""
        if not self.client:
            return None
        try:
            config = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=3000
            )
            
            if system_prompt:
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                    max_output_tokens=3000
                )
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=prompt,
                config=config
            )
            
            return response.text or None
            
        except Exception as e:
            logging.error(f"Gemini content generation error: {e}")
            return None

    def test_connection(self):
        """Test the Gemini API connection"""
        if not self.client:
            return False
        try:
            response = self.client.models.generate_content(
                model=self.text_model,
                contents="Say 'Gemini API connection successful!' in exactly those words.",
                config=types.GenerateContentConfig(max_output_tokens=50)
            )
            
            if response.text:
                result = response.text.strip()
                return "Gemini API connection successful!" in result
            return False
            
        except Exception as e:
            logging.error(f"Gemini connection test failed: {e}")
            return False
    
    def enhance_image_with_spice(self, image_path):
        """Enhance advertisement image using Gemini's spice prompt"""
        if not self.client:
            return None
        try:
            system_instruction = "You are an expert image enhancement AI. Analyze the image and provide enhancement suggestions using the spice prompt."
            
            prompt = "Spice up in dramatic red/black/white, futuristic cyberpunk, premium sleek high-tech—DO NOT change core subject/composition."
            
            response = self.client.models.generate_content(
                model=self.text_model,
                contents=f"Analyze this image and suggest enhancements: {prompt}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=500
                )
            )
            
            # Note: Gemini doesn't directly return enhanced images like OpenAI
            # This provides analysis that could be used for enhancement workflows
            logging.info(f"Gemini enhancement analysis: {response.text}")
            
            # Return None to fall back to OpenAI for actual image editing
            return None
            
        except Exception as e:
            logging.error(f"Gemini image enhancement error: {str(e)}")
            return None

# Initialize the service (never crash app if key missing or SDK fails)
try:
    gemini_service = GeminiService()
except Exception as e:
    logging.warning("Gemini service failed to initialize: %s", e)
    gemini_service = GeminiService.__new__(GeminiService)
    gemini_service.client = None
    gemini_service.text_model = None
    gemini_service.pro_model = None