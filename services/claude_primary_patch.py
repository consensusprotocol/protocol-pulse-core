
"""
Claude-First Article Generation Patch
======================================
This module patches the ContentGenerator to use Claude (Anthropic) as the 
primary article generator, with Grok review before publishing.
"""

import os
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def patch_content_generator():
    """
    Patch the ContentGenerator to:
    1. Use Claude (Anthropic) as primary generator
    2. Fall back to Gemini if Claude fails
    3. Skip OpenAI entirely (quota issues)
    4. Add Grok review step before returning
    """
    
    from services.ai_service import AIService
    from services.grok_review_service import grok_review_service
    
    # Store original method
    original_generate = AIService.generate_content_openai
    
    def generate_with_claude_first(self, prompt, system_prompt=None):
        """Try Claude first, then Gemini, skip OpenAI."""
        
        # Try Anthropic (Claude) first
        if self.anthropic_client:
            try:
                logger.info("Generating content with Claude (Anthropic)...")
                result = self.generate_content_anthropic(prompt, system_prompt)
                if result and len(result) > 100:
                    logger.info(f"Claude generated {len(result)} chars")
                    return result
            except Exception as e:
                logger.warning(f"Claude generation failed: {e}")
        
        # Try Gemini second
        if self.gemini_available:
            try:
                logger.info("Falling back to Gemini...")
                from services.gemini_service import gemini_service
                result = gemini_service.generate_content(prompt)
                if result and len(result) > 100:
                    logger.info(f"Gemini generated {len(result)} chars")
                    return result
            except Exception as e:
                logger.warning(f"Gemini generation failed: {e}")
        
        # Only try OpenAI if explicitly enabled and has quota
        if os.environ.get("FORCE_OPENAI") == "true" and self.openai_client:
            try:
                logger.info("Trying OpenAI as last resort...")
                return original_generate(self, prompt, system_prompt)
            except Exception as e:
                logger.error(f"OpenAI also failed: {e}")
        
        raise ValueError("All AI providers failed to generate content")
    
    # Apply patch
    AIService.generate_content_openai = generate_with_claude_first
    logger.info("✅ Patched AIService to use Claude first")
    
    return True


def add_grok_review_to_pipeline():
    """
    Inject Grok review into the article publishing pipeline.
    Articles must pass Grok review before being published.
    """
    from services.grok_review_service import grok_review_service
    from services import automation
    
    # Store original function
    original_generate = automation.generate_breaking_article_with_tracking
    
    @wraps(original_generate)
    def generate_with_review():
        """Generate article, then run Grok review before publishing."""
        result = original_generate()
        
        if not result.get("success") or not result.get("article_id"):
            return result
        
        # Get the article
        from app import app, db
        from models import Article
        
        with app.app_context():
            article = Article.query.get(result["article_id"])
            if not article:
                return result
            
            # Run Grok review
            logger.info(f"Running Grok review on article {article.id}...")
            review = grok_review_service.review_article(article.title, article.content)
            
            # Store review metadata
            article.review_score = review.get("score", 0)
            article.review_notes = review.get("fact_check_notes", "")
            
            if not review.get("approved", True):
                # Don't publish, keep as draft
                article.published = False
                logger.warning(f"Article {article.id} failed Grok review: {review.get('issues')}")
                result["grok_approved"] = False
                result["grok_issues"] = review.get("issues", [])
            else:
                logger.info(f"Article {article.id} passed Grok review with score {review.get('score')}")
                result["grok_approved"] = True
                result["grok_score"] = review.get("score")
            
            db.session.commit()
        
        return result
    
    # Apply patch
    automation.generate_breaking_article_with_tracking = generate_with_review
    logger.info("✅ Added Grok review to article pipeline")
    
    return True


# Auto-apply patches when imported
if __name__ != "__main__":
    try:
        patch_content_generator()
        add_grok_review_to_pipeline()
    except Exception as e:
        logger.warning(f"Could not apply content generator patches: {e}")
