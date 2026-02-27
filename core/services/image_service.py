# AI-Powered Header Image Generation Service for Protocol Pulse
# Generates minimalist, Dilbert-style header images for Bitcoin/DeFi articles

import os
import json
import logging
import requests
from datetime import datetime
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class ImageGenerationService:
    def __init__(self):
        """Initialize the image generation service with OpenAI DALL-E. OPENAI_API_KEY is optional."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or OpenAI is None:
            if OpenAI is None:
                logging.warning("openai package not available - image generation disabled.")
            else:
                logging.warning("OPENAI_API_KEY missing - image generation disabled. Header images will use defaults.")
            self.openai_client = None
        else:
            try:
                self.openai_client = OpenAI(api_key=api_key)
                logging.info("Image generation service initialized successfully")
            except Exception as e:
                logging.warning("Failed to initialize image generation service: %s", e)
                self.openai_client = None

        self.base_style_prompt = """
        Ultra-minimalist geometric header image for a Bitcoin/DeFi news article.
        **Style:** Extremely clean, abstract geometric composition. Think Swiss design meets cryptocurrency. Maximum simplicity with powerful visual impact.
        **Color Palette:** ONLY deep red (#DC2626), pure black (#000000), and pure white (#FFFFFF). Use red very sparingly as accent only.
        **Composition:** Ultra-minimal. Single geometric shape or 2-3 basic shapes maximum. Vast amounts of negative white space. Think logo-level simplicity.
        **Subject Matter:** Pure abstract geometric representation. Simple circles, triangles, lines, or basic Bitcoin "₿" symbol. No complex scenes, no people, no detailed objects. Maximum abstraction.
        **Mood/Tone:** Professional, pristine, editorial. Like Financial Times or Wall Street Journal header graphics.
        **ABSOLUTELY CRITICAL:** 
        - NO words, text, letters, numbers, or any typography whatsoever
        - NO complex illustrations or detailed imagery
        - NO gradients or textures - flat colors only
        - Maximum geometric simplicity
        - Professional news publication aesthetic
        """

    def generate_article_header_image(self, article_title: str, article_summary: str) -> str:
        """Generate a header image for an article using DALL-E"""
        if not self.openai_client:
            logging.warning("Image generation service not available - using default image")
            return self._get_default_image()

        # Construct the full prompt for DALL-E
        full_prompt = (
            self.base_style_prompt +
            f"\n\n**Article Topic/Essence:** '{article_title}' and its core idea summarized as: '{article_summary[:150]}'."
        )

        try:
            logging.info(f"Generating header image for: {article_title}")
            
            # Generate image using DALL-E 3
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                n=1,
                size="1024x1024",
                quality="standard"
            )
            
            if not response.data or len(response.data) == 0:
                logging.error("No image data received from DALL-E")
                return self._get_default_image()
            
            image_url = response.data[0].url
            if not image_url:
                logging.error("No image URL received from DALL-E")
                return self._get_default_image()
            
            # Download and save the image locally
            local_path = self._save_image_locally(image_url, article_title)
            
            logging.info(f"✅ Generated header image: {local_path}")
            return local_path

        except Exception as e:
            logging.error(f"Error generating image for '{article_title}': {e}")
            return self._get_default_image()

    def _save_image_locally(self, image_url: str, article_title: str) -> str:
        """Download and save the generated image locally"""
        try:
            # Create images directory if it doesn't exist
            os.makedirs('static/images/headers', exist_ok=True)
            
            # Generate filename from article title
            safe_filename = "".join(c for c in article_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_filename = safe_filename.replace(' ', '_')[:50]  # Limit length
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"header_{safe_filename}_{timestamp}.png"
            local_path = f"static/images/headers/{filename}"
            
            # Download the image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Save to local file
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # Return the relative URL for use in templates
            return f"/static/images/headers/{filename}"
            
        except Exception as e:
            logging.error(f"Error saving image locally: {e}")
            return self._get_default_image()

    def _get_default_image(self) -> str:
        """Return a default image URL when generation fails"""
        return "/static/images/default-header.png"

    def extract_summary_from_content(self, content: str) -> str:
        """Extract TL;DR summary from article content for image generation"""
        try:
            # Look for TL;DR in the content
            if "TL;DR:" in content:
                start = content.find("TL;DR:") + 6
                end = content.find("</", start)
                if end > start:
                    summary = content[start:end].strip()
                    # Clean up HTML tags
                    summary = summary.replace("<strong>", "").replace("</strong>", "")
                    summary = summary.replace("<em>", "").replace("</em>", "")
                    return summary[:200]  # Limit summary length
            
            # Fallback: use first paragraph
            if "<p class=\"article-paragraph\">" in content:
                start = content.find("<p class=\"article-paragraph\">") + 30
                end = content.find("</p>", start)
                if end > start:
                    summary = content[start:end].strip()[:200]
                    return summary
            
            return "Breaking news in Bitcoin and DeFi markets"
            
        except Exception as e:
            logging.error(f"Error extracting summary: {e}")
            return "Protocol Pulse news update"

# Global service instance
image_service = ImageGenerationService()