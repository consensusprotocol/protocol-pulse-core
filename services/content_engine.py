from __future__ import annotations
import os
import logging
from typing import Dict, Optional, List
from datetime import datetime
from app import db
from services.ai_service import AIService
from services.gemini_service import gemini_service

def strip_html_fences(content):
    """Remove ```html fences that Claude sometimes wraps around content."""
    if not content:
        return content
    content = content.strip()
    if content.startswith("```html"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


try:
    from services.grok_service import grok_service
except Exception:
    grok_service = None
try:
    from services.substack_service import SubstackService
except ModuleNotFoundError:
    SubstackService = None
try:
    from services.elevenlabs_service import ElevenLabsService
except ModuleNotFoundError:
    ElevenLabsService = None
try:
    from services.heygen_service import HeyGenService
except ModuleNotFoundError:
    HeyGenService = None
try:
    from substack import Api
    from substack.post import Post
except ModuleNotFoundError:
    Api = None
    Post = None


class ContentEngine:
    """
    Main content generation and publishing engine for Protocol Pulse
    Coordinates AI generation, Substack publishing, and cross-platform distribution
    """
    
    # EDITORIAL ACCURACY MANDATE - Applied to all generated content
    ACCURACY_MANDATE = """
=== EDITORIAL ACCURACY MANDATE - ZERO TOLERANCE FOR FABRICATION ===

🚨 CRITICAL DATE AWARENESS 🚨
TODAY'S DATE: February 18, 2026
YOU ARE WRITING NEWS, NOT PREDICTIONS.

ABSOLUTELY FORBIDDEN - WILL CAUSE IMMEDIATE REJECTION:
- DO NOT invent specific prices (e.g., "$67,400 on February 18")
- DO NOT invent specific dates for events (e.g., "on February 14, MicroStrategy...")
- DO NOT invent institutional holdings numbers (e.g., "214,400 BTC")
- DO NOT invent hashrate figures (e.g., "650 EH/s")
- DO NOT invent Fed decisions, regulatory rulings, or policy changes
- DO NOT write as if you have access to real-time data you don't have
- DO NOT use phrases like "as of today" or "currently trading at" with invented numbers

WHAT TO DO INSTEAD:
- Write about TRENDS and THEMES, not specific numbers
- Use phrases like "Bitcoin continues to..." or "The network has seen..."
- Reference PAST events that actually happened (pre-2025)
- Focus on PHILOSOPHY, PRINCIPLES, and ANALYSIS over data points
- If you need specific data, say "according to recent reports" without inventing numbers

SAFE TOPICS THAT WON'T GET REJECTED:
- Bitcoin's role in financial sovereignty
- Decentralization principles and why they matter
- Historical context (halving cycles, adoption milestones)
- Philosophical perspectives on sound money
- Educational content about how Bitcoin works
- Analysis of long-term trends (without specific predictions)

UNSAFE TOPICS THAT WILL GET REJECTED:
- Specific price movements with numbers
- Specific institutional purchases with amounts
- Specific hashrate or difficulty numbers
- Specific regulatory decisions with dates
- Any "breaking news" with invented details

BEFORE DRAFTING ANY ARTICLE, YOU MUST:
1. VERIFY the latest Bitcoin metrics (Difficulty, Hashrate, Price) via real-time data fetch ONLY
2. DO NOT rely on training data or assumptions about network conditions
3. State the ACTUAL current date and ACTUAL current metrics correctly
4. If real-time data is not provided in the source material, DO NOT report on metrics

STRICTLY PROHIBITED - IMMEDIATE REJECTION IF VIOLATED:
- NEVER claim "all-time high," "record high," "unprecedented," or "new record" for ANY Bitcoin metric
- NEVER hallucinate hashrate figures (e.g., do not invent "1.2 ZH/s" or any number)
- NEVER assume difficulty is increasing - it can DECREASE during miner stress periods
- NEVER fabricate "network strengthening" narratives without verified data
- NEVER use phrases like "surge," "soaring," or "record-breaking" for metrics you cannot verify

REALITY CHECK - As of January 2026:
- Bitcoin hashrate has DECLINED approximately 15% from its October 2024 peak
- Difficulty ATH: 155.9T (November 2025). Do not claim "all-time high" unless current difficulty exceeds this.
- Difficulty adjustments can be NEGATIVE (downward) - this is normal during miner stress
- The network is NOT always hitting "new highs" - it fluctuates based on miner economics

IF WRITING ABOUT BITCOIN NETWORK METRICS:
- Only report what is EXPLICITLY stated in verified source material
- If source says "difficulty adjustment" without direction, ask for clarification or omit
- Use qualified language: "according to [source]," "data from [provider] shows"
- If you cannot verify a claim, DO NOT MAKE IT

Hallucinating record highs when the network is experiencing miner stress is STRICTLY PROHIBITED and will result in content rejection.
"""

    REVIEW_PROMPT_LIVE_FACT = (
        "Review this article for accuracy, depth, and Bitcoin facts. "
        "Verify against current data: block reward is 3.125 BTC in 2026 (post-halving), not 6.25. "
        "Decision: APPROVE or REJECT. Reason: detailed. Score: 1-10."
    )
    
    def __init__(self):
        self.ai_service = AIService()
        self.substack_service = None
        self.elevenlabs_service = None
        self.heygen_service = None
        if SubstackService is not None:
            try:
                self.substack_service = SubstackService()
            except Exception as e:
                logging.warning("Substack service initialization failed: %s", e)
        else:
            logging.warning("Substack service not available (module not found)")
        if ElevenLabsService is not None:
            try:
                self.elevenlabs_service = ElevenLabsService()
            except Exception as e:
                logging.warning("ElevenLabs service initialization failed: %s", e)
        if HeyGenService is not None:
            try:
                self.heygen_service = HeyGenService()
            except Exception as e:
                logging.warning("HeyGen service initialization failed: %s", e)
        logging.info("Content Engine initialized")

    def _single_review_openai(self, title: str, content: str, topic: str) -> Dict:
        """One reviewer via OpenAI. Returns {decision, reason, score}."""
        import json
        try:
            prompt = f"""{self.REVIEW_PROMPT_LIVE_FACT}

TITLE: {title}
TOPIC: {topic}
CONTENT (excerpt): {(content or '')[:4000]}

Respond with JSON only: {{"decision": "APPROVE" or "REJECT", "reason": "...", "score": N}}"""
            response = self.ai_service.generate_content_openai(prompt)
            data = json.loads(response)
            return {
                "decision": (data.get("decision") or "REJECT").upper()[:7],
                "reason": data.get("reason", ""),
                "score": int(data.get("score", 0)),
                "provider": "openai",
            }
        except Exception as e:
            logging.warning("OpenAI review failed: %s", e)
            return {"decision": "ABSTAIN", "reason": str(e), "score": 0, "provider": "openai"}

    def _single_review_anthropic(self, title: str, content: str, topic: str) -> Dict:
        """One reviewer via Anthropic. Returns {decision, reason, score}."""
        import json
        try:
            prompt = f"""{self.REVIEW_PROMPT_LIVE_FACT}

TITLE: {title}
TOPIC: {topic}
CONTENT (excerpt): {(content or '')[:4000]}

Respond with JSON only: {{"decision": "APPROVE" or "REJECT", "reason": "...", "score": N}}"""
            response = self.ai_service.generate_content_anthropic(prompt)
            data = json.loads(response)
            return {
                "decision": (data.get("decision") or "REJECT").upper()[:7],
                "reason": data.get("reason", ""),
                "score": int(data.get("score", 0)),
                "provider": "anthropic",
            }
        except Exception as e:
            logging.warning("Anthropic review failed: %s", e)
            return {"decision": "REJECT", "reason": str(e), "score": 0, "provider": "anthropic"}

    def multi_ai_review(self, title: str, content: str, topic: str = "") -> Dict:
        """
        Chain reviews from multiple models with GROK AS MANDATORY GATE.
        
        Grok has real-time fact-checking ability and acts as the final editorial gate.
        If Grok rejects an article, it is BLOCKED regardless of other reviewers.
        If Grok finds factual errors, it provides revised title/content.
        
        Returns {decision, reason, score, reviews, grok_review, revised_title, revised_content_sections}.
        """
        reviews: List[Dict] = []
        grok_review: Optional[Dict] = None

        from services.grok_review_service import grok_review_service
        if grok_review_service.client:
            grok_result = grok_review_service.review_article(title, content, topic)
            grok_result["provider"] = "grok"
            reviews.append(grok_result)
            grok_review = grok_result
            logging.info(f"GROK GATE: decision={grok_result.get('decision')}, "
                         f"score={grok_result.get('score')}, "
                         f"critical_errors={grok_result.get('critical_errors', [])}")
        else:
            logging.warning("GROK NOT AVAILABLE - fact-checking gate disabled, rejecting by default")
            return {
                "decision": "REJECT",
                "reason": "Grok fact-checker not available - cannot verify article accuracy",
                "score": 0,
                "reviews": [],
                "grok_review": None,
                "revised_title": None,
                "revised_content_sections": None,
            }

        if grok_review and grok_review.get("decision") == "REJECT":
            critical = grok_review.get("critical_errors", [])
            reason_parts = []
            if critical:
                reason_parts.append(f"GROK BLOCKED: {len(critical)} factual error(s): {'; '.join(critical[:3])}")
            else:
                reason_parts.append(f"GROK REJECTED: {grok_review.get('fact_check_notes', 'Failed fact-check')}")
            
            return {
                "decision": "REJECT",
                "reason": " | ".join(reason_parts)[:500],
                "score": grok_review.get("score", 0),
                "reviews": reviews,
                "grok_review": grok_review,
                "revised_title": grok_review.get("revised_title"),
                "revised_content_sections": grok_review.get("revised_content_sections"),
            }

        if getattr(self.ai_service, "openai_client", None):
            reviews.append(self._single_review_openai(title, content, topic))
        if getattr(self.ai_service, "anthropic_client", None):
            reviews.append(self._single_review_anthropic(title, content, topic))
        if gemini_service and getattr(gemini_service, "client", None):
            r = gemini_service.review_article(title, content, topic)
            r["provider"] = "gemini"
            reviews.append(r)

        valid_reviews = [r for r in reviews if (r.get("decision") or "").upper() != "ABSTAIN"]
        if not valid_reviews:
            return {
                "decision": "APPROVE",
                "reason": "Grok approved; other reviewers abstained",
                "score": grok_review.get("score", 70) if grok_review else 7,
                "reviews": reviews,
                "grok_review": grok_review,
                "revised_title": grok_review.get("revised_title") if grok_review else None,
                "revised_content_sections": None,
            }
        approve_count = sum(1 for r in valid_reviews if (r.get("decision") or "").upper() == "APPROVE")
        avg_score = sum(r.get("score", 0) for r in valid_reviews) / len(valid_reviews)
        
        decision = "APPROVE"
        reason = f"GROK APPROVED + Multi-AI: {approve_count}/{len(valid_reviews)} approve, avg score {avg_score:.1f}"

        return {
            "decision": decision,
            "reason": reason,
            "score": int(avg_score),
            "reviews": reviews,
            "grok_review": grok_review,
            "revised_title": grok_review.get("revised_title") if grok_review else None,
            "revised_content_sections": grok_review.get("revised_content_sections") if grok_review else None,
        }

    def review_article_with_gemini(self, title: str, content: str) -> Dict:
        """
        Single-review path (backward compatible). Prefer multi_ai_review for QC.
        Returns AI review decision: APPROVE or REJECT with reasoning
        """
        result = self.multi_ai_review(title, content, topic="")
        return {
            "decision": result["decision"],
            "reason": result["reason"],
            "score": result["score"],
        }

    def approve_and_publish_article(self, article_id: int) -> Dict:
        """
        Automated AI review and publishing workflow
        Uses Gemini as Editor-in-Chief for quality control
        """
        result = {
            "success": False,
            "substack_url": None,
            "errors": [],
            "review": None
        }
        
        try:
            # Get article from database
            import models
            article = db.session.get(models.Article, article_id)
            if not article:
                result["errors"].append("Article not found")
                return result

            # Hard freeze: block *any* publish when flag is off.
            from services.content_generator import auto_publish_enabled, validate_article_for_publish
            if not auto_publish_enabled():
                article.published = False
                db.session.commit()
                result["errors"].append("Auto-publish disabled by ENABLE_AUTO_PUBLISH flag")
                result["message"] = "Publish blocked (ENABLE_AUTO_PUBLISH=false)"
                return result

            ok, validation_errors = validate_article_for_publish(article)
            if not ok:
                article.published = False
                db.session.commit()
                result["errors"].extend(validation_errors)
                result["message"] = "Publish rejected by validation gate"
                return result
            
            review = self.multi_ai_review(article.title, article.content, topic="")
            result["review"] = {"decision": review["decision"], "reason": review["reason"], "score": review["score"]}
            result["reviews"] = review.get("reviews", [])
            if review.get("decision") == "APPROVE":
                revised_title = review.get("revised_title")
                if revised_title and revised_title.strip():
                    logging.info(f"GROK REVISED TITLE (approve_and_publish): '{article.title}' -> '{revised_title}'")
                    article.title = revised_title.strip()
                
                article.published = True
                article.published_at = datetime.utcnow()

                image_path = None
                
                # Publish to Substack
                substack_url = self.publish_to_substack(
                    title=article.title, 
                    body_markdown=article.content, 
                    image_path=image_path
                )
                
                if substack_url:
                    article.substack_url = substack_url
                    db.session.commit()
                    
                    result["success"] = True
                    result["substack_url"] = substack_url
                    result["message"] = f"AI approved and published (Score: {review.get('score')}/10)"
                    
                    logging.info(f"Article {article_id} AI-approved and published: {substack_url}")
                else:
                    result["errors"].append("Failed to publish to Substack")
                    
            else:
                # AI rejected - save as draft for potential revision
                article.published = False
                db.session.commit()
                result["message"] = f"AI rejected: {review.get('reason')} (Score: {review.get('score')}/10)"
                logging.info(f"Article {article_id} AI-rejected: {review.get('reason')}")
            
            return result
            
        except Exception as e:
            result["errors"].append(f"AI review workflow error: {e}")
            logging.error(f"AI review workflow failed for article {article_id}: {e}")
            return result

    def generate_and_publish_article(self, topic: str, content_type: str = "bitcoin_news", 
                                   auto_publish: bool = False) -> Dict:
        """

        # TOPIC DIVERSITY CHECK
        try:
            from services.article_automation import _is_topic_oversaturated
            if _is_topic_oversaturated(topic):
                self.logger.info(f"TOPIC DIVERSITY: Skipping - oversaturated topic")
                return {"success": False, "skipped": True, "reason": "topic_oversaturated"}
        except ImportError:
            pass
        Complete content generation and publishing pipeline
        
        Args:
            topic: Article topic or source content
            content_type: Type of content (bitcoin_news, defi_analysis, market_update)
            auto_publish: Whether to auto-publish to Substack
            
        Returns:
            Dictionary with generation results and URLs
        """
        result = {
            "success": False,
            "article_id": None,
            "substack_url": None,
            "audio_file": None,
            "video_url": None,
            "errors": []
        }
        
        try:
            # Step 1: Generate article content
            logging.info(f"Generating {content_type} article for topic: {topic}")
            
            if content_type == "bitcoin_news":
                article_data = self._generate_bitcoin_article(topic)
            elif content_type == "defi_analysis":
                article_data = self._generate_defi_article(topic)
            elif content_type == "market_update":
                article_data = self._generate_market_article(topic)
            else:
                article_data = self._generate_general_article(topic, content_type)
            
            if not article_data:
                result["errors"].append("Failed to generate article content")
                return result
            
            # Step 2: Save article to database
            article = self._save_article_to_db(article_data)
            if article:
                result["article_id"] = article.id
                logging.info(f"Article saved to database with ID: {article.id}")
            else:
                result["errors"].append("Failed to save article to database")
                return result
            
            # Step 3: Generate multimedia content
            if self.elevenlabs_service:
                try:
                    audio_file = self._generate_audio_content(article_data)
                    if audio_file:
                        result["audio_file"] = audio_file
                        logging.info(f"Generated audio file: {audio_file}")
                except Exception as e:
                    result["errors"].append(f"Audio generation failed: {e}")
            
            if self.heygen_service:
                try:
                    video_url = self._generate_video_content(article_data, content_type)
                    if video_url:
                        result["video_url"] = video_url
                        logging.info(f"Generated video: {video_url}")
                except Exception as e:
                    result["errors"].append(f"Video generation failed: {e}")
            
            # Step 4: Multi-AI Review and Auto-Publishing Pipeline
            from services.content_generator import auto_publish_enabled, validate_article_for_publish
            if auto_publish and not auto_publish_enabled():
                result["status"] = "draft"
                result["message"] = "Auto-publish frozen by ENABLE_AUTO_PUBLISH=false"
                result["success"] = True
                return result

            ok, validation_errors = validate_article_for_publish(article_data)
            if not ok:
                # Save exists already, but never publish invalid content.
                try:
                    article.published = False
                    db.session.commit()
                except Exception:
                    pass
                result["status"] = "rejected"
                result["errors"].extend(validation_errors)
                result["message"] = "Article rejected by validation gate"
                result["success"] = True
                return result

            # Draft gate: body (after strip_duplicate_tldr) < 3000 words -> must stay draft
            try:
                from services.content_generator import should_article_be_draft_by_word_count
                if should_article_be_draft_by_word_count(article_data.get("content") or ""):
                    article.published = False
                    db.session.commit()
                    result["status"] = "draft"
                    result["message"] = "Article saved as draft (body < 3000 words)"
                    result["success"] = True
                    return result
            except Exception:
                pass

            if auto_publish:
                try:
                    review = self.multi_ai_review(
                        article_data["title"],
                        article_data["content"],
                        topic or "",
                    )
                    result["review"] = {"decision": review["decision"], "reason": review["reason"], "score": review["score"]}
                    result["reviews"] = review.get("reviews", [])
                    if review.get("decision") == "APPROVE":
                        revised_title = review.get("revised_title")
                        if revised_title and revised_title.strip():
                            logging.info(f"GROK REVISED TITLE: '{article.title}' -> '{revised_title}'")
                            article.title = revised_title.strip()
                            article_data["title"] = revised_title.strip()
                        
                        from services.content_generator import validate_article_for_publish
                        ok, val_errs = validate_article_for_publish(article)
                        if not ok:
                            article.published = False
                            db.session.commit()
                            result["errors"].extend(val_errs)
                            result["message"] = "Publish rejected by validation gate (full body required)"
                        else:
                            article.published = True
                            db.session.commit()
                            result["message"] = f"AI approved and published on site (Score: {review.get('score')}/10)"
                            logging.info(f"AI approved and published on site: {article.id}")
                            if self.substack_service:
                                try:
                                    substack_url = self.publish_to_substack(
                                        title=article_data["title"],
                                        body_markdown=article_data["content"],
                                        image_path=None
                                    )
                                    if substack_url:
                                        article.substack_url = substack_url
                                        db.session.commit()
                                        result["substack_url"] = substack_url
                                except Exception as sub_err:
                                    result["errors"].append(f"Substack publishing failed: {sub_err}")
                    else:
                        # AI rejected - save as draft
                        article.published = False
                        db.session.commit()
                        result["message"] = f"AI rejected: {review.get('reason')} (Score: {review.get('score')}/10)"
                        logging.info(f"AI rejected article: {review.get('reason')}")
                        
                except Exception as e:
                    result["errors"].append(f"AI review pipeline failed: {e}")
            else:
                # Save as draft for later review
                result["status"] = "draft"
                result["message"] = "Article saved as draft"
            
            result["success"] = True
            return result
            
        except Exception as e:
            logging.error(f"Content generation pipeline failed: {e}")
            result["errors"].append(f"Pipeline error: {e}")
            return result

    def _generate_bitcoin_article(self, topic: str) -> Optional[Dict]:
        """Generate Bitcoin-focused news article"""
        try:
            prompt = f"""
            {self.ACCURACY_MANDATE}
            
            You are the senior editor at Protocol Pulse, a Bitcoin-native intelligence outlet. Your voice: Matt Taibbi's edge, Lyn Alden's precision, Michael Lewis's storytelling instinct. You write articles people screenshot and send to friends.

Topic: {topic}

STRUCTURAL ARCHITECTURE:
1. THE HOOK (1-2 sentences, max 30 words) - Open with the most interesting, surprising, or counterintuitive fact. NEVER open with "[Company] has [done thing]."
2. THE FACTS (2-3 sentences) - Core news: who, what, how much, when. Specific numbers. No analysis.
3. THE ANALYSIS (2-3 paragraphs, 60% of article) - Who wins? Who loses? What changes? Use 1-1-3 cadence. Embed ONE shareable bold line using <strong> tags.
4. THE BITCOIN LENS (1-2 sentences, ONLY if natural) - If no natural Bitcoin connection, SKIP entirely.
5. THE CLOSE (1-2 sentences) - Forward-looking prediction or provocative statement. NEVER "The question remains..." or "Will X or Y?"

WRITING RULES: Alternate sentence lengths. State every point ONCE. Show over tell. Use exact numbers. Confident but not arrogant. Conversational tone.

BANNED PHRASES (instant failure): "It is worth noting", "This underscores", "This highlights", "Furthermore", "Moreover", "In conclusion", "The broader landscape", "The question remains", "Only time will tell", "Paradigm", "Burgeoning", "Emblematic", "Grapples with", "At the forefront", "Microcosm", "A testament to", "The intersection of", "The convergence of", "In the realm of", "Compelling narrative", "The evolving landscape", "As we move forward", "Rapidly evolving", "A beacon of", "A pillar of", "Serves as a", "Fostering", "Unmatched", "Unparalleled", "Steadfast", "Stalwart", "Bedrock", "Gold standard", "Sets it apart", "In a league of its own", "Stands as a silent testament"

STRUCTURAL BANS: Never open with "[Company] has [done thing]". Never close with "Will X happen, or will Y?". Never end an altcoin story with generic Bitcoin superiority.

FORMAT: Use <h1 class="article-header">, <div class="tldr-section">, <p class="article-paragraph">. Clean HTML only. No markdown. Target 450-650 words.
            
            CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            
            IMPORTANT: Start with a compelling headline wrapped in <h1 class="article-header">Headline Here</h1> before the TL;DR section.
            
            Focus exclusively on Bitcoin. Target length: 800-1200 words
            """
            
            content = self.ai_service.generate_content_anthropic(prompt)
            if not content:
                content = self.ai_service.generate_content_openai(prompt)
            if content:
                return self._parse_article_content(content, "Bitcoin")
            return None
            
        except Exception as e:
            logging.error(f"Bitcoin article generation failed: {e}")
            return None

    def _generate_defi_article(self, topic: str) -> Optional[Dict]:
        """Generate DeFi analysis article"""
        try:
            prompt = f"""
            {self.ACCURACY_MANDATE}
            
            You are the senior editor at Protocol Pulse, a Bitcoin-native intelligence outlet. Your voice: Matt Taibbi's edge, Lyn Alden's precision, Michael Lewis's storytelling instinct. You write articles people screenshot and send to friends.

Topic: {topic}

STRUCTURAL ARCHITECTURE:
1. THE HOOK (1-2 sentences, max 30 words) - Open with the most interesting, surprising, or counterintuitive fact. NEVER open with "[Company] has [done thing]."
2. THE FACTS (2-3 sentences) - Core news: who, what, how much, when. Specific numbers. No analysis.
3. THE ANALYSIS (2-3 paragraphs, 60% of article) - Who wins? Who loses? What changes? Use 1-1-3 cadence. Embed ONE shareable bold line using <strong> tags.
4. THE BITCOIN LENS (1-2 sentences, ONLY if natural) - If no natural Bitcoin connection, SKIP entirely.
5. THE CLOSE (1-2 sentences) - Forward-looking prediction or provocative statement. NEVER "The question remains..." or "Will X or Y?"

WRITING RULES: Alternate sentence lengths. State every point ONCE. Show over tell. Use exact numbers. Confident but not arrogant. Conversational tone.

BANNED PHRASES (instant failure): "It is worth noting", "This underscores", "This highlights", "Furthermore", "Moreover", "In conclusion", "The broader landscape", "The question remains", "Only time will tell", "Paradigm", "Burgeoning", "Emblematic", "Grapples with", "At the forefront", "Microcosm", "A testament to", "The intersection of", "The convergence of", "In the realm of", "Compelling narrative", "The evolving landscape", "As we move forward", "Rapidly evolving", "A beacon of", "A pillar of", "Serves as a", "Fostering", "Unmatched", "Unparalleled", "Steadfast", "Stalwart", "Bedrock", "Gold standard", "Sets it apart", "In a league of its own", "Stands as a silent testament"

STRUCTURAL BANS: Never open with "[Company] has [done thing]". Never close with "Will X happen, or will Y?". Never end an altcoin story with generic Bitcoin superiority.

FORMAT: Use <h1 class="article-header">, <div class="tldr-section">, <p class="article-paragraph">. Clean HTML only. No markdown. Target 450-650 words.
            
            CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            
            Focus on DeFi protocols and decentralized finance. Target length: 1000-1500 words
            """
            
            content = self.ai_service.generate_content_anthropic(prompt)
            if content:
                return self._parse_article_content(content, "DeFi")
            return None
            
        except Exception as e:
            logging.error(f"DeFi article generation failed: {e}")
            return None

    def _generate_market_article(self, topic: str) -> Optional[Dict]:
        """Generate market update article"""
        try:
            prompt = f"""
            {self.ACCURACY_MANDATE}
            
            You are the senior editor at Protocol Pulse, a Bitcoin-native intelligence outlet. Your voice: Matt Taibbi's edge, Lyn Alden's precision, Michael Lewis's storytelling instinct. You write articles people screenshot and send to friends.

Topic: {topic}

STRUCTURAL ARCHITECTURE:
1. THE HOOK (1-2 sentences, max 30 words) - Open with the most interesting, surprising, or counterintuitive fact. NEVER open with "[Company] has [done thing]."
2. THE FACTS (2-3 sentences) - Core news: who, what, how much, when. Specific numbers. No analysis.
3. THE ANALYSIS (2-3 paragraphs, 60% of article) - Who wins? Who loses? What changes? Use 1-1-3 cadence. Embed ONE shareable bold line using <strong> tags.
4. THE BITCOIN LENS (1-2 sentences, ONLY if natural) - If no natural Bitcoin connection, SKIP entirely.
5. THE CLOSE (1-2 sentences) - Forward-looking prediction or provocative statement. NEVER "The question remains..." or "Will X or Y?"

WRITING RULES: Alternate sentence lengths. State every point ONCE. Show over tell. Use exact numbers. Confident but not arrogant. Conversational tone.

BANNED PHRASES (instant failure): "It is worth noting", "This underscores", "This highlights", "Furthermore", "Moreover", "In conclusion", "The broader landscape", "The question remains", "Only time will tell", "Paradigm", "Burgeoning", "Emblematic", "Grapples with", "At the forefront", "Microcosm", "A testament to", "The intersection of", "The convergence of", "In the realm of", "Compelling narrative", "The evolving landscape", "As we move forward", "Rapidly evolving", "A beacon of", "A pillar of", "Serves as a", "Fostering", "Unmatched", "Unparalleled", "Steadfast", "Stalwart", "Bedrock", "Gold standard", "Sets it apart", "In a league of its own", "Stands as a silent testament"

STRUCTURAL BANS: Never open with "[Company] has [done thing]". Never close with "Will X happen, or will Y?". Never end an altcoin story with generic Bitcoin superiority.

FORMAT: Use <h1 class="article-header">, <div class="tldr-section">, <p class="article-paragraph">. Clean HTML only. No markdown. Target 450-650 words.
            
            CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            
            Cover both Bitcoin price action and DeFi market trends. Target length: 600-900 words
            """
            
            content = self.ai_service.generate_content_anthropic(prompt)
            if not content:
                content = self.ai_service.generate_content_openai(prompt)
            if content:
                return self._parse_article_content(content, "Market Update")
            return None
            
        except Exception as e:
            logging.error(f"Market article generation failed: {e}")
            return None

    def _generate_general_article(self, topic: str, content_type: str) -> Optional[Dict]:
        """Generate general Web3/crypto article"""
        try:
            prompt = f"""
            {self.ACCURACY_MANDATE}
            
            You are the senior editor at Protocol Pulse, a Bitcoin-native intelligence outlet. Your voice: Matt Taibbi's edge, Lyn Alden's precision, Michael Lewis's storytelling instinct. You write articles people screenshot and send to friends.

Topic: {topic}

STRUCTURAL ARCHITECTURE:
1. THE HOOK (1-2 sentences, max 30 words) - Open with the most interesting, surprising, or counterintuitive fact. NEVER open with "[Company] has [done thing]."
2. THE FACTS (2-3 sentences) - Core news: who, what, how much, when. Specific numbers. No analysis.
3. THE ANALYSIS (2-3 paragraphs, 60% of article) - Who wins? Who loses? What changes? Use 1-1-3 cadence. Embed ONE shareable bold line using <strong> tags.
4. THE BITCOIN LENS (1-2 sentences, ONLY if natural) - If no natural Bitcoin connection, SKIP entirely.
5. THE CLOSE (1-2 sentences) - Forward-looking prediction or provocative statement. NEVER "The question remains..." or "Will X or Y?"

WRITING RULES: Alternate sentence lengths. State every point ONCE. Show over tell. Use exact numbers. Confident but not arrogant. Conversational tone.

BANNED PHRASES (instant failure): "It is worth noting", "This underscores", "This highlights", "Furthermore", "Moreover", "In conclusion", "The broader landscape", "The question remains", "Only time will tell", "Paradigm", "Burgeoning", "Emblematic", "Grapples with", "At the forefront", "Microcosm", "A testament to", "The intersection of", "The convergence of", "In the realm of", "Compelling narrative", "The evolving landscape", "As we move forward", "Rapidly evolving", "A beacon of", "A pillar of", "Serves as a", "Fostering", "Unmatched", "Unparalleled", "Steadfast", "Stalwart", "Bedrock", "Gold standard", "Sets it apart", "In a league of its own", "Stands as a silent testament"

STRUCTURAL BANS: Never open with "[Company] has [done thing]". Never close with "Will X happen, or will Y?". Never end an altcoin story with generic Bitcoin superiority.

FORMAT: Use <h1 class="article-header">, <div class="tldr-section">, <p class="article-paragraph">. Clean HTML only. No markdown. Target 450-650 words.
            
            CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX (**, ***, ##, ###) - ONLY CLEAN HTML
            - Ensure proper spacing with empty lines between sections
            
            Focus on Bitcoin and DeFi as primary topics. Target length: 800-1200 words
            """
            
            content = self.ai_service.generate_content_anthropic(prompt)
            if not content:
                content = self.ai_service.generate_content_openai(prompt)
            if content:
                return self._parse_article_content(content, content_type.title())
            return None
            
        except Exception as e:
            logging.error(f"General article generation failed: {e}")
            return None

    def _parse_article_content(self, content: str, category: str) -> Dict:
        """Parse AI-generated content into structured article data"""
        import re

        title = ""
        summary = ""
        article_content = content.strip()

        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.DOTALL)
        if h1_match:
            title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
            article_content = content[:h1_match.start()] + content[h1_match.end():]
            article_content = article_content.strip()

        if not title:
            h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', content, re.DOTALL)
            if h2_match:
                title = re.sub(r'<[^>]+>', '', h2_match.group(1)).strip()

        if not title:
            lines = content.strip().split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('<div') and not stripped.startswith('<em') and not stripped.startswith('<strong'):
                    title = re.sub(r'<[^>]+>', '', stripped).replace('#', '').strip()
                    break

        if not title:
            title = f"Bitcoin Intelligence Report: {category} Update"

        if len(title) > 200:
            title = title[:197] + "..."

        tldr_match = re.search(r'TL;DR[:\s]*(.*?)(?:</strong>|</em>|</div>|<h2)', content, re.DOTALL | re.IGNORECASE)
        if tldr_match:
            summary = re.sub(r'<[^>]+>', '', tldr_match.group(1)).strip()
        if not summary:
            p_match = re.search(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
            if p_match:
                summary = re.sub(r'<[^>]+>', '', p_match.group(1)).strip()[:300]

        return {
            "title": title,
            "content": article_content or content,
            "summary": summary or "AI-generated article summary",
            "category": category,
            "tags": f"{category}, Bitcoin, DeFi, Protocol Pulse",
            "seo_title": title[:200] if title else "Protocol Pulse Article",
            "seo_description": summary[:300] if summary else "Latest Bitcoin and DeFi insights"
        }


    def _is_duplicate(self, title, hours=48):
        """Check if a similar article was published recently."""
        from datetime import datetime, timedelta
        from app import db
        import models
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = models.Article.query.filter(
            models.Article.created_at > cutoff,
            models.Article.published == True
        ).all()
        
        new_words = set(title.lower().split())
        
        for article in recent:
            existing_words = set(article.title.lower().split())
            if not existing_words:
                continue
            overlap = len(new_words & existing_words) / max(len(new_words | existing_words), 1)
            if overlap > 0.45:
                return True, article.title
            
            # Also check if first 4 words match (catches "Bitcoin's Quiet Revolution: ...")
            new_start = ' '.join(title.lower().split()[:4])
            existing_start = ' '.join(article.title.lower().split()[:4])
            if new_start == existing_start and len(new_start) > 15:
                return True, article.title
        
        return False, None

    def _save_article_to_db(self, article_data: Dict) -> Optional[models.Article]:
        """Save article to database"""

        # DEDUP CHECK: reject near-duplicate titles
        title = article_data.get("title", "")
        is_dup, dup_title = self._is_duplicate(title)
        if is_dup:
            self.logger.warning(f"DEDUP: Rejected '{title[:50]}' - too similar to '{dup_title[:50]}'")
            return None
        try:
            # Clean content to handle special characters
            def clean_text(text, is_title=False):
                if isinstance(text, str):
                    import re
                    # Remove HTML/XML tags and markdown headers for titles
                    if is_title:
                        text = re.sub(r'<[^>]+>', '', text)
                        text = re.sub(r'^#{1,6}\s*', '', text.strip())
                    # Replace problematic Unicode characters
                    text = text.replace('\u2019', "'")  # Smart apostrophe
                    text = text.replace('\u2018', "'")  # Smart apostrophe
                    text = text.replace('\u201c', '"')  # Smart quote
                    text = text.replace('\u201d', '"')  # Smart quote
                    text = text.replace('\u2013', '-')  # En dash
                    text = text.replace('\u2014', '--') # Em dash
                    return text.encode('utf-8', errors='ignore').decode('utf-8').strip()
                return text
            
            header_url = (article_data.get("header_image_url") or "").strip()
            if not header_url or header_url == "/static/images/default-header.png":
                try:
                    from services.image_service import generate_article_header_image
                    img_path = generate_article_header_image(article_data.get("title", "Bitcoin News"))
                    # Verify the file actually exists on disk
                    if img_path and not os.path.exists(img_path.lstrip("/")):
                        self.logger.warning(f"Image generation returned path but file missing: {img_path}")
                        img_path = None
                    if img_path:
                        header_url = img_path
                except Exception as img_err:
                    logging.warning(f"Image generation failed: {img_err}")
            if not header_url:
                header_url = "/static/images/default-header.png"
            import models
            article = models.Article(
                title=clean_text(article_data["title"], is_title=True),
                content=clean_text(article_data["content"]),
                summary="",  # No summary - TL;DR is embedded in content
                category=clean_text(article_data["category"]),
                tags=clean_text(article_data["tags"]),
                seo_title=clean_text(article_data["seo_title"], is_title=True),
                seo_description=clean_text(article_data["seo_description"]),
                source_type="ai_generated",
                published=False,  # Require manual approval by default
                author="Al Ingle",
                header_image_url=header_url,
            )
            
            db.session.add(article)
            db.session.commit()
            
            return article
            
        except Exception as e:
            logging.error(f"Database save failed: {e}")
            db.session.rollback()
            return None

    def _generate_audio_content(self, article_data: Dict) -> Optional[str]:
        """Generate audio version of article"""
        try:
            if not self.elevenlabs_service:
                return None
                
            # Determine voice type based on content category
            category = article_data.get("category", "").lower()
            if "bitcoin" in category:
                voice_type = "professional_male"
            elif "defi" in category:
                voice_type = "authoritative"
            elif "market" in category:
                voice_type = "professional_female"
            else:
                voice_type = "conversational"
            
            # Generate audio
            audio_file = self.elevenlabs_service.generate_article_summary_audio(
                article_data["title"], 
                article_data["content"],
                voice_type
            )
            
            return audio_file
            
        except Exception as e:
            logging.error(f"Audio generation failed: {e}")
            return None

    def _generate_video_content(self, article_data: Dict, content_type: str) -> Optional[str]:
        """Generate video version of article"""
        try:
            if not self.heygen_service:
                return None
                
            # Generate appropriate video based on content type
            if content_type == "bitcoin_news":
                video_url = self.heygen_service.create_bitcoin_news_video(
                    article_data["title"],
                    article_data["summary"]
                )
            elif content_type == "defi_analysis":
                video_url = self.heygen_service.create_defi_analysis_video(
                    article_data["content"][:500]  # Truncate for video
                )
            else:
                video_url = self.heygen_service.create_social_media_video(
                    article_data["summary"]
                )
            
            return video_url
            
        except Exception as e:
            logging.error(f"Video generation failed: {e}")
            return None

    def _publish_to_substack(self, article_data: Dict, content_type: str) -> Optional[str]:
        """Publish article to Substack using your exact implementation"""
        return self.publish_to_substack(
            article_data["title"], 
            article_data["content"], 
            None  # No header images - user preference
        )

    def publish_to_substack(self, title: str, body_markdown: str, image_path: str = None) -> Optional[str]:
        """Your exact Substack publishing implementation"""
        if Api is None or Post is None:
            logging.warning("Substack (substack package) not available - skip publish")
            return None
        try:
            api = Api(
                email=os.environ.get("SUBSTACK_EMAIL"),
                password=os.environ.get("SUBSTACK_PASSWORD"),
                publication_url=os.environ.get("SUBSTACK_PUBLICATION_URL")
            )
            user_id = api.get_user_id()

            post = Post(
                title=title,
                subtitle="Generated by Protocol Pulse AI",
                user_id=user_id
            )

            # Add body as paragraph (convert Markdown to Substack blocks if needed; simple for now)
            post.add({"type": "paragraph", "content": body_markdown})

            # Optional header image (from DALL-E path/URL)
            if image_path:
                uploaded = api.get_image(image_path)  # Handles upload
                post.add({"type": "captionedImage", "src": uploaded.get("url")})

            draft = api.post_draft(post.get_draft())
            # Optional: Set section if needed - api.put_draft(draft.get("id"), ...)
            api.prepublish_draft(draft.get("id"))
            published = api.publish_draft(draft.get("id"))
            post_url = published.get("canonical_url")
            self.send_slack_notification(f"Article published to Substack: {post_url}")
            return post_url
        except Exception as e:
            self.send_slack_notification(f"Substack error: {e}")
            logging.error(f"Substack publishing error: {e}")
            return None

    def send_slack_notification(self, message: str):
        """Send notification to Slack (placeholder for now)"""
        try:
            # TODO: Implement Slack integration when API keys are provided
            logging.info(f"Slack notification: {message}")
        except Exception as e:
            logging.error(f"Slack notification failed: {e}")

    def generate_content_from_reddit_trend(self, reddit_post: Dict) -> Dict:
        """Generate content based on Reddit trending topic"""
        try:
            topic = f"{reddit_post.get('title', '')} - {reddit_post.get('selftext', '')[:500]}"
            
            # Determine content type based on post
            if any(keyword in topic.lower() for keyword in ['defi', 'protocol', 'yield', 'liquidity']):
                content_type = "defi_analysis"
            elif any(keyword in topic.lower() for keyword in ['price', 'market', 'pump', 'dump']):
                content_type = "market_update"
            else:
                content_type = "bitcoin_news"
            
            return self.generate_and_publish_article(topic, content_type, auto_publish=False)
            
        except Exception as e:
            logging.error(f"Reddit trend content generation failed: {e}")
            return {"success": False, "errors": [str(e)]}

    def get_smart_playlist(self, user_segment: str = None) -> Dict:
        """
        Generate a smart playlist based on user segment (K-means clustering).
        Maps segments to curated series for personalized content.
        """
        segment_playlists = {
            'sovereign_node': {
                'series_name': 'The Privacy & Decentralization Stream',
                'keywords': ['tor', 'node', 'self-custody', 'p2p', 'privacy', 'decentralized', 'sovereign'],
                'sarah_intro': "Based on your high sovereignty score, I suggest starting with the Privacy Series. These episodes focus on self-custody, running your own node, and maintaining financial privacy in an increasingly surveilled world."
            },
            'miner': {
                'series_name': 'The Hashpower Mastery Series',
                'keywords': ['hashrate', 'difficulty', 'energy', 'asic', 'mining', 'pool', 'profitability'],
                'sarah_intro': "Your mining focus is clear. This series covers hashrate dynamics, difficulty adjustments, energy optimization, and the economics of ASIC operations. Essential intel for serious miners."
            },
            'institution': {
                'series_name': 'The Sound Money Macro Series',
                'keywords': ['etf', 'central bank', 'fiat', 'institutional', 'treasury', 'hedge', 'macro'],
                'sarah_intro': "For institutional-grade analysis, start with the Sound Money Macro Series. We cover ETF flows, central bank policy impacts, and how Bitcoin fits into traditional portfolio allocation frameworks."
            },
            'trader': {
                'series_name': 'The Technical Intelligence Stream',
                'keywords': ['technical', 'price', 'chart', 'momentum', 'resistance', 'support', 'breakout'],
                'sarah_intro': "Your trading focus requires precision intel. This series delivers technical analysis, key levels to watch, and momentum indicators across multiple timeframes."
            },
            'developer': {
                'series_name': 'The Protocol Engineering Deep Dives',
                'keywords': ['lightning', 'taproot', 'script', 'protocol', 'upgrade', 'bip', 'code'],
                'sarah_intro': "For the technically inclined, our Protocol Engineering series explores Lightning Network developments, Taproot applications, and the future of Bitcoin scripting."
            }
        }
        
        segment = user_segment or 'institution'
        playlist = segment_playlists.get(segment, segment_playlists['institution'])
        
        return {
            'segment': segment,
            'series_name': playlist['series_name'],
            'keywords': playlist['keywords'],
            'sarah_intro': playlist['sarah_intro']
        }


# Initialize the content engine
content_engine = ContentEngine()