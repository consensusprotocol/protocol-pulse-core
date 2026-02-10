import os
import json
import logging
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None
from .grok_service import grok_service
from .gemini_service import gemini_service

class AIService:
    def __init__(self):
        # Initialize OpenAI client (optional if openai package missing or old)
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key and OpenAI is not None:
            try:
                self.openai_client = OpenAI(api_key=openai_key)
            except Exception:
                self.openai_client = None
        else:
            self.openai_client = None
        
        # Initialize Anthropic client (optional if anthropic package missing)
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key and Anthropic is not None:
            try:
                self.anthropic_client = Anthropic(api_key=anthropic_key)
            except Exception:
                self.anthropic_client = None
        else:
            self.anthropic_client = None
        
        self.default_openai_model = "gpt-4o"
        self.default_anthropic_model = "claude-3-opus-20240229"
        
        # AI service integrations - check availability
        try:
            self.grok_available = grok_service.test_connection()
        except:
            self.grok_available = False
        
        try:
            self.gemini_available = gemini_service.test_connection()
        except:
            self.gemini_available = False
    
    def generate_content_openai(self, prompt, system_prompt=None):
        """Generate content using OpenAI GPT-4o"""
        if not self.openai_client:
            raise ValueError("API key required")
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an investigative journalist for Protocol Pulse."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"OpenAI API error: {str(e)}")
            raise
    
    def generate_content_anthropic(self, prompt, system_prompt=None):
        """Generate content using Anthropic Claude"""
        if not self.anthropic_client:
            raise ValueError("API key required")
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            response = self.anthropic_client.messages.create(
                model=self.default_anthropic_model,
                max_tokens=2000,
                temperature=0.7,
                system="You are an investigative journalist for Protocol Pulse.",
                messages=messages
            )
            
            # Handle Anthropic response properly - extract text from content blocks
            if response and response.content and len(response.content) > 0:
                content_block = response.content[0]
                # Use getattr to safely access text attribute regardless of block type
                text_content = getattr(content_block, 'text', None)
                if text_content is not None:
                    return str(text_content)
                else:
                    # Fallback to string conversion for other block types
                    return str(content_block)
            return ""
            
        except Exception as e:
            logging.error(f"Anthropic API error: {str(e)}")
            raise
    
    def generate_structured_content(self, prompt, system_prompt=None, provider="openai"):
        """Generate structured content with JSON response"""
        if provider == "openai" and self.openai_client:
            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.openai_client.chat.completions.create(
                    model=self.default_openai_model,
                    messages=messages,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                if content:
                    return json.loads(content)
                else:
                    return {}
                
            except Exception as e:
                logging.error(f"OpenAI structured content error: {str(e)}")
                # Fallback to regular generation
                return self.generate_content_openai(prompt, system_prompt)
        
        elif provider == "anthropic" and self.anthropic_client:
            return self.generate_content_anthropic(prompt, system_prompt)
        
        elif provider == "openai" and not self.openai_client:
            raise ValueError("API key required")
        
        elif provider == "anthropic" and not self.anthropic_client:
            raise ValueError("API key required")
        
        else:
            raise ValueError("API key required")
    
    def summarize_text(self, text, max_words=150):
        """Summarize text content"""
        prompt = f"Summarize the following text in {max_words} words or less, focusing on key points relevant to Web3, cryptocurrency, and blockchain technology:\n\n{text}"
        
        try:
            # Try OpenAI first, fallback to Anthropic
            if self.openai_client:
                return self.generate_content_openai(prompt)
            elif self.anthropic_client:
                return self.generate_content_anthropic(prompt)
            else:
                raise ValueError("API key required")
                
        except Exception as e:
            logging.error(f"Summarization error: {str(e)}")
            return text[:500] + "..." if len(text) > 500 else text
    
    def generate_seo_metadata(self, title, content):
        """Generate SEO title and description"""
        prompt = f"""
        Generate SEO-optimized metadata for this article:
        Title: {title}
        Content: {content[:500]}...
        
        Provide a compelling SEO title (60 chars max) and meta description (155 chars max) that includes relevant Web3/crypto keywords.
        Respond in JSON format: {{"seo_title": "...", "seo_description": "..."}}
        """
        
        system_prompt = "You are an SEO expert specializing in Web3 and cryptocurrency content."
        
        try:
            if self.openai_client:
                result = self.generate_structured_content(prompt, system_prompt, "openai")
                if isinstance(result, dict):
                    return result
            elif self.anthropic_client:
                response = self.generate_content_anthropic(prompt, system_prompt)
                return {
                    "seo_title": title[:60],
                    "seo_description": content[:155] + "..." if len(content) > 155 else content
                }
            else:
                raise ValueError("API key required")
            
        except Exception as e:
            logging.error(f"SEO generation error: {str(e)}")
            return {
                "seo_title": title[:60],
                "seo_description": content[:155] + "..." if len(content) > 155 else content
            }
    
    
    def generate_content_grok(self, topic, content_type="bitcoin_news"):
        """Generate content using Grok"""
        if not self.grok_available:
            raise ValueError("API key required")
        
        try:
            if content_type == "bitcoin_news":
                return grok_service.generate_bitcoin_article(topic, "news")
            elif content_type == "bitcoin_analysis":
                return grok_service.generate_bitcoin_article(topic, "analysis")
            elif content_type == "defi_general":
                return grok_service.generate_defi_article(topic, "general")
            elif content_type == "defi_protocols":
                return grok_service.generate_defi_article(topic, "protocols")
            elif content_type == "podcast_script":
                return grok_service.generate_podcast_script(topic)
            else:
                return grok_service.generate_bitcoin_article(topic, "news")
                
        except Exception as e:
            logging.error(f"Grok content generation error: {str(e)}")
            raise
    
    def analyze_sentiment_grok(self, text):
        """Analyze sentiment using Grok"""
        if not self.grok_available:
            raise ValueError("API key required")
        
        try:
            return grok_service.analyze_market_sentiment(text)
        except Exception as e:
            logging.error(f"Grok sentiment analysis error: {str(e)}")
            return {"error": str(e)}
    
    def generate_content_gemini(self, topic, content_type="bitcoin_news"):
        """Generate content using Gemini"""
        if not self.gemini_available:
            raise ValueError("API key required")
        
        try:
            if content_type == "bitcoin_news":
                return gemini_service.generate_bitcoin_article(topic, "news")
            elif content_type == "bitcoin_analysis":
                return gemini_service.generate_bitcoin_article(topic, "analysis")
            elif content_type == "defi_general":
                return gemini_service.generate_defi_article(topic, "general")
            elif content_type == "defi_protocols":
                return gemini_service.generate_defi_article(topic, "protocols")
            elif content_type == "podcast_script":
                return gemini_service.generate_podcast_script(topic)
            else:
                return gemini_service.generate_bitcoin_article(topic, "news")
                
        except Exception as e:
            logging.error(f"Gemini content generation error: {str(e)}")
            raise
    
    def analyze_sentiment_gemini(self, text):
        """Analyze sentiment using Gemini"""
        if not self.gemini_available:
            raise ValueError("API key required")
        
        try:
            return gemini_service.analyze_market_sentiment(text)
        except Exception as e:
            logging.error(f"Gemini sentiment analysis error: {str(e)}")
            return {"error": str(e)}
    
    def get_available_providers(self):
        """Get list of available AI providers"""
        providers = []
        if self.openai_client:
            providers.append("OpenAI GPT-5")
        if self.anthropic_client:
            providers.append("Anthropic Claude")
        if self.grok_available:
            providers.append("xAI Grok")
        if self.gemini_available:
            providers.append("Google Gemini")
        return providers
    
    def enhance_ad_image(self, image_path):
        """Enhance advertisement image using AI"""
        # Try Gemini first for image enhancement
        if self.gemini_available:
            try:
                from .gemini_service import gemini_service
                enhanced_url = gemini_service.enhance_image_with_spice(image_path)
                if enhanced_url:
                    return enhanced_url
            except Exception as e:
                logging.warning(f"Gemini image enhancement failed: {e}")
        
        # Fallback to OpenAI if Gemini fails
        if not self.openai_client:
            logging.warning("OpenAI client not available for image enhancement")
            return None
        
        try:
            with open(image_path, "rb") as image_file:
                response = self.openai_client.images.edit(
                    image=image_file,
                    prompt="Spice up in dramatic red/black/white, futuristic cyberpunk, premium sleek high-tech—DO NOT change core subject/composition.",
                    n=1,
                    size="1024x1024"
                )
                
                if response.data and len(response.data) > 0:
                    return response.data[0].url
                else:
                    logging.warning("No image data returned from OpenAI")
                    return None
                    
        except Exception as e:
            logging.error(f"Image enhancement error: {str(e)}")
            return None