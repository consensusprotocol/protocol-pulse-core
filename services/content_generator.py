import logging
import os
from datetime import datetime, timedelta

# --- THE FIX: MODULE IMPORT ONLY ---
import models 
# ------------------------------------

from app import app, db
from services.ai_service import AIService
from services.reddit_service import RedditService
from services.x_service import get_social_feedback
from services import x_service
from services.image_service import image_service
from services.gemini_service import gemini_service
from services.node_service import NodeService
from services.fact_checker import fact_checker, verify_article_before_publish
from services.supported_sources_loader import get_partner_youtube_channels, load_supported_sources

def is_topic_duplicate_via_gemini(proposed_topic):
    """
    AI GATEKEEPER: Check if the proposed topic duplicates any recent article.
    Returns True if duplicate (should skip), False if unique (proceed).
    """
    try:
        with app.app_context():
            # Fetch last 10 published article titles
            recent_articles = models.Article.query.filter_by(published=True).order_by(
                models.Article.created_at.desc()
            ).limit(10).all()
            
            if not recent_articles:
                return False  # No articles to compare, proceed
            
            headlines_list = "\n".join([f"- {a.title}" for a in recent_articles])
            
            prompt = f"""You are a senior news editor preventing duplicate coverage.

PROPOSED NEW TOPIC: "{proposed_topic}"

LAST 10 PUBLISHED HEADLINES:
{headlines_list}

CRITICAL QUESTION: Is the proposed topic covering the EXACT SAME news event as ANY of these existing headlines?

RULES:
- Focus on the CORE EVENT, not wording
- "Bitcoin reaches new high" and "BTC price surges to record" = SAME EVENT
- "Nations adopt Bitcoin reserves" and "Countries add BTC to treasuries" = SAME EVENT
- "Bitcoin mining difficulty rises" and "New mining hardware released" = DIFFERENT EVENTS

Reply with ONLY one word: "DUPLICATE" or "UNIQUE" - nothing else."""

            response = gemini_service.generate_content(prompt)
            if response:
                answer = response.strip().upper()
                if "DUPLICATE" in answer:
                    logging.info(f"🚫 GATEKEEPER BLOCKED: '{proposed_topic[:50]}...' is duplicate of existing story")
                    return True
                logging.info(f"✅ GATEKEEPER APPROVED: '{proposed_topic[:50]}...' is unique")
            return False
    except Exception as e:
        logging.warning(f"Gatekeeper check failed: {e}")
        return False  # On error, allow generation to proceed

class ContentGenerator:
    def __init__(self):
        self.ai_service = AIService()
        self.reddit_service = RedditService()
        self.gemini_service = gemini_service

        # Partner sources: single source of truth from core/config/supported_sources.json
        self._supported_sources = None

        # EDITORIAL ACCURACY MANDATE - Applied to all content types
        self.accuracy_mandate = """
=== EDITORIAL ACCURACY MANDATE - ZERO TOLERANCE FOR FABRICATION ===

GROUND TRUTH DATA LOCKDOWN (January 23, 2026):
- Bitcoin Difficulty: 146.47 T (NOT an all-time high - below November 2025 peak of 155.9 T)
- Network Hashrate: ~977 EH/s (approximately 1042 EH/s in some readings)
- These figures are CURRENT and VERIFIED - use them when discussing network security

RECORD HIGH PROHIBITION:
- NEVER claim "all-time high," "record high," "unprecedented," or "new record" for difficulty
- The November 2025 peak was 155.9 T - current difficulty is BELOW that threshold
- Only use "record" terminology if difficulty exceeds 155.9 T (which it does NOT today)

STRICTLY PROHIBITED - IMMEDIATE REJECTION IF VIOLATED:
- NEVER hallucinate hashrate figures (do not invent numbers not listed above)
- NEVER assume difficulty is always increasing - it can DECREASE during miner stress periods
- NEVER fabricate "network strengthening" narratives without verified data
- NEVER use phrases like "surge," "soaring," or "record-breaking" for metrics you cannot verify

TECHNICAL STORYTELLING - EDITORIAL APPROACH:
Write every piece as a peer-to-peer intelligence briefing for "transactors" (active Bitcoin users),
NOT for "tourists" (passive chart-watchers seeking price speculation):
- Transactors care about: network security, difficulty adjustments, hashrate distribution, mining economics, protocol fundamentals
- Tourists care about: price predictions, moon shots, get-rich-quick narratives (AVOID THIS)
- Frame content as actionable intelligence that helps transactors make informed decisions about their Bitcoin holdings

THE BITCOIN LENS - PHILOSOPHICAL GROUNDING:
Every article must connect technical Bitcoin metrics back to the philosophy of "The Hardest Money":
- Difficulty at 146.47 T represents computational security protecting the soundest monetary base layer
- 977 EH/s of hashpower demonstrates global commitment to decentralized, censorship-resistant money
- Each difficulty adjustment proves the protocol's self-regulating nature vs fiat's arbitrary manipulation
- Frame all network metrics as evidence of Bitcoin's position as incorruptible, trustless money

BEFORE DRAFTING ANY ARTICLE, YOU MUST:
1. Use the GROUND TRUTH DATA above for January 23, 2026
2. DO NOT rely on training data or assumptions about network conditions
3. State the ACTUAL current date and ACTUAL current metrics correctly
4. Connect network fundamentals to Bitcoin's role as sound money vs fiat debasement

IF WRITING ABOUT BITCOIN NETWORK METRICS:
- Use the verified metrics above: Difficulty 146.47 T, Hashrate ~977 EH/s
- Use qualified language: "current difficulty stands at 146.47 T," "network hashrate of approximately 977 EH/s"
- If you cannot verify a claim beyond the ground truth data, DO NOT MAKE IT

Hallucinating record highs when the network is below November 2025's 155.9 T peak is STRICTLY PROHIBITED.
"""

        # HEADLINE STYLE MANDATE - Both questions AND statements
        self.headline_style_mandate = """
=== HEADLINE STYLE VARIETY MANDATE ===

PROTOCOL PULSE HEADLINES MUST VARY BETWEEN TWO STYLES:

STYLE A - QUESTION HEADLINES (Provocative, Engagement-Focused):
Examples:
- "Is El Salvador's Bitcoin Strategy Paying Off?"
- "Can Lightning Network Handle 1 Million Transactions Per Day?"
- "Will China's Mining Ban Strengthen Bitcoin Long-Term?"
- "Are Institutional Investors Finally Taking Bitcoin Seriously?"

STYLE B - STATEMENT HEADLINES (Authoritative, Fact-Forward):
Examples:
- "El Salvador Reports $30 Million Bitcoin Tourism Revenue"
- "Lightning Network Processes Record 1.2 Million Daily Transactions"
- "Bitcoin Mining Hashrate Redistributes Following China Exodus"
- "BlackRock ETF Accumulates 250,000 Bitcoin in Six Months"

SELECTION RULE: 
Generate a random number 1-10 mentally. If odd, use STYLE A (Question). If even, use STYLE B (Statement).

BOTH STYLES MUST:
- Be factually accurate and grounded in verified data
- Avoid clickbait or sensationalism
- Use specific numbers when available (not vague "record high" claims)
- Convey the core news value in under 15 words
- Apply the same rigorous accuracy standards to both formats

NEVER:
- Use question headlines that have obvious "No" answers (bad journalism)
- Use statement headlines with unverified claims
- Mix styles within the same headline (no "Bitcoin Hits $100K - But Is It Sustainable?")
"""

        # INTELLIGENCE OFFICER LOCKED STRUCTURE - Mandatory 6-section format with HIGH-VALUE MANDATE
        self.locked_structure_mandate = """
=== INTELLIGENCE OFFICER DIRECTIVE - LOCKED OUTPUT STRUCTURE ===

YOU ARE FORBIDDEN FROM RETURNING AN ARTICLE UNLESS IT CONTAINS ALL SIX SECTIONS:

1. <div class="tldr-section">: A punchy, 3-sentence summary of why today's specific metrics matter for sovereignty.
   - Use the ground truth data as FOUNDATION, then BUILD A NARRATIVE around it
   - Do NOT just repeat the numbers - explain their SIGNIFICANCE
   
2. <h2 class="article-header">The Report</h2>: Factual account (350+ words)
   - Network status with verified metrics
   - Recent global events affecting Bitcoin
   - Mining economics and fee market conditions
   
3. <h2 class="article-header">Exclusive Data Analysis</h2>: Deep on-chain intelligence (300+ words)
   - UNIQUE on-chain metrics not found in mainstream coverage (UTXO age bands, realized cap, SOPR, MVRV)
   - Historical comparison: how do current metrics compare to previous cycles?
   - Pattern recognition: what do the data patterns suggest about market structure?
   - Include specific numbers and percentages that provide EXCLUSIVE value
   
4. <h2 class="article-header">The Bitcoin Lens</h2>: Philosophical analysis + Expert Perspectives (400+ words)
   - Deep analysis on network resilience vs fiat debasement
   - Connect current metrics to long-term monetary sovereignty
   - Include perspectives from Bitcoin thought leaders (Saifedean Ammous, Michael Saylor, Lyn Alden, etc.)
   - Quote or reference specific expert viewpoints that reinforce the narrative
   - Second-order thinking: what do these numbers MEAN for the future?
   
5. <h2 class="article-header">Transactor Intelligence</h2>: Actionable advice (250+ words)
   - Specific guidance for miners based on current difficulty/fees
   - Recommendations for high-value users regarding fee optimization
   - Timing considerations for transactions based on mempool conditions
   - CONCRETE ACTIONS readers can take today (not vague suggestions)
   - Risk/reward analysis for specific strategies
   
6. <h2 class="article-header">Sources</h2>: Formatted list of data sources
   - Include at least 5 credible sources (mempool.space, Glassnode, Bitcoin Magazine, etc.)

=== HIGH-VALUE ARTICLE MANDATE ===

YOUR GOAL: Make this article SO VALUABLE that readers CANNOT find equivalent information elsewhere.

EXCLUSIVE VALUE CREATION:
- Include data points NOT covered by mainstream crypto news (Coindesk, Cointelegraph)
- Provide ORIGINAL analysis that connects multiple data sources
- Deliver insights that would cost $1000+ from paid research services
- Every paragraph must answer "What can the reader DO with this information?"

EXPERT INTEGRATION:
- Reference specific quotes or positions from Bitcoin experts
- Connect current events to established Bitcoin thought (Austrian economics, cypherpunk philosophy)
- Provide the "expert friend" perspective readers don't have access to

RESEARCH DEPTH:
- Connect on-chain data to macroeconomic trends
- Reference historical precedents with specific dates and outcomes
- Include contrarian perspectives and why they might be wrong

ANTI-LOOP RULE:
- Do NOT repeat exact phrasing used in homepage terminal modules ("FEES: X sat/vB", "BLOCK: Y")
- EXPAND on those metrics with second-order analysis - tell readers what to DO with the information
- Every section must contain UNIQUE content not duplicated elsewhere in the article

MINIMUM LENGTH REQUIREMENT:
- Total article body must be 1200+ words (excluding HTML tags)
- If your output is shorter, you have FAILED - expand with deeper analysis
- The TL;DR is NOT the article - it's a summary. BUILD THE FULL NARRATIVE.

NARRATIVE BRIDGE:
Use the ground truth metrics as the FOUNDATION, but you MUST build a 1,500-word deep-dive 
around them. The numbers are the starting point, not the entire article.
"""

        # Default prompts for different content types - HIGH-VALUE STORYTELLING APPROACH
        self.default_prompts = {
            'news_article': """
            Write an EXCEPTIONALLY HIGH-VALUE intelligence briefing about {topic} for TRANSACTORS (active Bitcoin users who self-custody). Your goal is to create content SO valuable that readers cannot find equivalent analysis anywhere else.
            
            HEADLINE STYLE: {headline_style}
            
            MANDATORY SECTIONS (in order):
            1. TL;DR - 3 punchy sentences on why this matters for sovereignty
            2. The Report - Factual news with verified metrics (350+ words)
            3. Exclusive Data Analysis - On-chain metrics, historical comparisons, UNIQUE insights (300+ words)
            4. The Bitcoin Lens - Philosophy + expert perspectives from thought leaders (400+ words)
            5. Transactor Intelligence - Specific, actionable advice with concrete steps (250+ words)
            6. Sources - At least 5 credible sources
            
            HIGH-VALUE REQUIREMENTS:
            - Include ON-CHAIN METRICS not covered by mainstream (UTXO age, realized cap, SOPR, MVRV)
            - Reference expert perspectives (Saifedean Ammous, Michael Saylor, Lyn Alden, Parker Lewis)
            - Provide SPECIFIC NUMBERS and percentages, not vague claims
            - Every section must answer: "What can the reader DO with this information?"
            - Connect to historical precedents with specific dates
            
            """ + """CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX - ONLY CLEAN HTML
            
            Target length: 1200-1800 words
            """,
            
            'analysis_piece': """
            Write a PREMIUM-TIER expert analysis about {topic} that delivers insights worth $1000+ from paid research services. Target audience: sophisticated Bitcoin holders who want EXCLUSIVE intelligence.
            
            HEADLINE STYLE: {headline_style}
            
            MANDATORY SECTIONS (in order):
            1. TL;DR - Executive summary for busy transactors
            2. The Report - Comprehensive factual foundation (400+ words)
            3. Exclusive Data Analysis - Deep on-chain intelligence with SPECIFIC metrics (400+ words)
            4. The Bitcoin Lens - Expert perspectives and philosophical grounding (500+ words)
            5. Transactor Intelligence - Actionable strategy with risk/reward analysis (300+ words)
            6. Sources - 6+ credible sources including on-chain data providers
            
            EXCLUSIVE VALUE REQUIREMENTS:
            - Reference specific on-chain data (Glassnode, CryptoQuant metrics)
            - Include contrarian perspectives and counter-arguments
            - Connect macro trends to Bitcoin thesis
            - Provide the "expert friend" perspective readers don't have access to
            
            """ + """CRITICAL FORMATTING REQUIREMENTS - OUTPUT MUST BE CLEAN HTML:
            - Start with TL;DR using: <div class="tldr-section"><em><strong>TL;DR: [summary here]</strong></em></div>
            - Use <h2 class="article-header"> for main section headers
            - Use <h3 class="article-subheader"> for sub-section headers  
            - Use <p class="article-paragraph"> for all paragraphs
            - End with Sources section: <h2 class="article-header">Sources</h2> followed by <ul class="sources-list"><li>source 1</li><li>source 2</li></ul>
            - NO MARKDOWN SYNTAX - ONLY CLEAN HTML
            
            Target length: 1500-2500 words
            """,
            
            'breaking_news': """
            Write an URGENT high-value intelligence briefing about {topic}. Breaking news that transactors need NOW, but still with exclusive analysis they cannot find elsewhere.
            
            HEADLINE STYLE: {headline_style}
            
            MANDATORY SECTIONS:
            1. TL;DR - Urgent summary with immediate action items
            2. The Report - What happened, verified facts only (300+ words)
            3. Exclusive Data Analysis - Rapid on-chain response metrics (200+ words)
            4. The Bitcoin Lens - Expert quick-take perspectives (250+ words)
            5. Transactor Intelligence - IMMEDIATE actions to take (200+ words)
            6. Sources - Credible sources only
            
            """ + """CRITICAL FORMATTING - CLEAN HTML ONLY:
            - Start with TL;DR: <div class="tldr-section"><em><strong>TL;DR: [summary]</strong></em></div>
            - Use <h2 class="article-header"> for section headers
            - Use <p class="article-paragraph"> for paragraphs
            - End with Sources: <ul class="sources-list"><li>sources</li></ul>
            
            Target length: 800-1000 words
            """
        }
    
    def generate_article(self, topic, prompt_id=None, content_type='news_article', source_type='ai_generated', headline_style=None):
        """
        Generate a complete article based on topic and prompt
        
        Args:
            topic: Article topic or source content
            prompt_id: Optional custom prompt ID
            content_type: Type of content (news_article, analysis_piece, breaking_news)
            source_type: Source type (ai_generated, reddit, x)
            headline_style: 'question' for question headlines, 'statement' for fact-forward headlines, 
                           None for random selection (default behavior)
        """
        import random
        
        # Determine headline style if not specified
        if headline_style is None:
            headline_style = random.choice(['question', 'statement'])
        
        # Map headline style to prompt instructions - VERY EXPLICIT to override AI tendencies
        headline_instructions = {
            'question': 'HEADLINE FORMAT: Use a QUESTION-STYLE headline that provokes thought. Example: "Is Bitcoin Mining Becoming More Decentralized?" The headline MUST end with a question mark (?).',
            'statement': '''HEADLINE FORMAT: MANDATORY STATEMENT-STYLE HEADLINE - NO QUESTIONS ALLOWED.

DO NOT use a question for the headline. DO NOT end with "?" 
Your headline MUST be a declarative statement of fact.

WRONG FORMATS (DO NOT USE):
- "How Does X Impact Y?" ❌
- "Is Bitcoin X?" ❌  
- "Why Are Y?" ❌
- "Will Z Happen?" ❌

CORRECT FORMATS (USE THESE):
- "Bitcoin Network Processes Record 1 Million Daily Transactions" ✓
- "Anthropic Partners with Coinbase for AI-Powered Custody Verification" ✓
- "Lightning Network Capacity Surpasses 5,000 BTC Milestone" ✓
- "BlackRock ETF Holdings Reach 250,000 Bitcoin" ✓

Your headline MUST be a factual statement. Start with a noun (Bitcoin, Lightning, Protocol, Company name, etc.), NOT with "How", "Why", "Is", "Are", "Will", "Does", or "Can".'''
        }
        headline_prompt = headline_instructions.get(headline_style, headline_instructions['statement'])
        
        try:
            # AI GATEKEEPER: Check for duplicates before generating
            if is_topic_duplicate_via_gemini(topic):
                logging.info(f"⏭️ Skipping generation: Gatekeeper detected duplicate topic")
                return {
                    'success': False,
                    'error': 'Duplicate topic detected by AI gatekeeper',
                    'skipped': True
                }
            
            # Integrate Reddit if source_type is reddit
            if source_type == 'reddit':
                try:
                    with app.app_context():
                        reddit_trends = self.reddit_service.get_trending_topics(['cryptocurrency', 'bitcoin', 'defi', 'web3'], limit=3)
                        if reddit_trends:
                            reddit_context = f"Recent Reddit trends: {reddit_trends[0].get('title', '')} - {reddit_trends[0].get('selftext', '')[:200]}..."
                            topic = f"{topic}. {reddit_context}"
                except Exception as e:
                    logging.warning(f"Failed to fetch Reddit trends: {str(e)}")
            
            # Integrate X (Twitter) social feedback for nuance
            if source_type == 'x' or source_type == 'twitter':
                try:
                    with app.app_context():
                        feedback = x_service.get_feedback(topic)
                        if feedback:
                            topic = f"{topic} (X feedback: {feedback})"
                            logging.info(f"Added X feedback for topic: {topic[:50]}...")
                except Exception as e:
                    logging.warning(f"Failed to fetch X feedback: {str(e)}")
            
            # Get custom prompt if provided
            prompt_template = self._get_prompt_template(prompt_id, content_type)
            
            # Format the prompt with the topic
            # Enhanced prompt with new editorial guidelines AND headline directive
            enhanced_prompt = f"""
            Write a comprehensive news article about: {topic}
            
            === HEADLINE STYLE REQUIREMENT ===
            {headline_prompt}
            YOUR HEADLINE MUST FOLLOW THIS STYLE. This is not optional.
            
            Apply the Protocol Pulse editorial mandate: Begin with clear factual reporting, 
            then provide thoughtful context connecting to history, economics, and society. 
            Include unique analysis with data and credible sources. Write through a Bitcoin-first 
            lens where Bitcoin is money, the only truly decentralized currency, and foundation 
            of freedom and sovereignty.
            
            Structure as two distinct sections:
            1. 'The Report' - Factual news account with context and analysis
            2. 'The Bitcoin Lens' - Bitcoin-focused commentary and philosophical perspective
            
            Make it engaging, authoritative, and educational while orange-pilling readers 
            about Bitcoin's unique importance to humanity.
            """
            
            logging.info(f"📝 Generating article with {headline_style.upper()} headline style")
            # Format the prompt, handling missing placeholders gracefully
            try:
                formatted_prompt = prompt_template.format(topic=enhanced_prompt, headline_style=headline_prompt)
            except KeyError:
                # If template doesn't have headline_style placeholder, just format topic
                formatted_prompt = prompt_template.format(topic=enhanced_prompt)
            
            # GROUND TRUTH VERIFICATION: Fetch real-time Bitcoin metrics before generating
            network_stats = None
            try:
                network_stats = NodeService.get_network_stats()
                logging.info(f"Ground truth metrics fetched: Height={network_stats.get('height')}, Hashrate={network_stats.get('hashrate')}")
            except Exception as e:
                logging.warning(f"Failed to fetch network stats for ground truth: {e}")
            
            # Build real-time metrics context for the AI
            metrics_context = ""
            if network_stats:
                metrics_context = f"""
VERIFIED REAL-TIME BITCOIN NETWORK DATA (as of {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}):
- Current Block Height: {network_stats.get('height', 'Unknown')}
- Current Hashrate: {network_stats.get('hashrate', 'Unknown')}
- Network Status: {network_stats.get('status', 'Unknown')}
- Difficulty Adjustment Progress: {network_stats.get('difficulty_progress', 'Unknown')}
- Blocks Until Adjustment: {network_stats.get('remaining_blocks', 'Unknown')}

YOU MUST USE THESE VERIFIED METRICS. Do not invent different numbers.
If the hashrate is below previous peaks, DO NOT claim "record high" or "all-time high".
If difficulty progress indicates an upcoming DECREASE, report that accurately.
"""
            else:
                metrics_context = """
WARNING: Real-time network data unavailable. 
DO NOT report specific Bitcoin metrics (hashrate, difficulty, price) in this article.
Focus on qualitative analysis only. No fabricated numbers allowed.
"""
            
            # Add system prompt for consistency - New Editorial Guidelines + Accuracy Mandate + Locked Structure + Headline Variety
            system_prompt = f"""
            You are a world-class journalist writing for Protocol Pulse with the trust and authority 
            of Walter Cronkite but in a natural, human style that feels engaging and real. 
            
            {metrics_context}
            
            {self.accuracy_mandate}
            
            {self.headline_style_mandate}
            
            === HEADLINE DIRECTIVE FOR THIS ARTICLE ===
            {headline_prompt}
            THIS IS A MANDATORY REQUIREMENT. Your headline MUST follow this style.
            
            {self.locked_structure_mandate}
            
            EDITORIAL MANDATE: Write every article like a world-class journalist with the trust and 
            authority of Walter Cronkite but in a natural, human style that feels engaging and real. 
            Begin with a clear and factual account of the news, then provide thoughtful context that 
            connects events to history, economics, and society. Always deliver unique analysis that 
            uncovers deeper meaning, using data, historical parallels, and quotes from credible sources 
            to establish authority. Avoid jargon where a simpler, clearer explanation will do. 
            
            Every piece must be written through a Bitcoin-first lens: reinforce that Bitcoin is money, 
            the only truly decentralized currency, and the foundation of freedom, privacy, and sovereignty. 
            When other crypto projects are mentioned, they should be framed as secondary, never rivaling 
            Bitcoin's role. 
            
            MANDATORY 5-SECTION STRUCTURE:
            1. TL;DR (punchy 3-sentence summary)
            2. 'The Report' (factual news reporting - 300+ words)
            3. 'The Bitcoin Lens' (philosophical analysis - 300+ words)
            4. 'Transactor Intelligence' (actionable advice for miners and users - 200+ words)
            5. 'Sources' (formatted list of data sources)
            
            This reinforces the separation between unbiased news, philosophical commentary, and actionable intelligence.
            
            CRITICAL: OUTPUT ONLY CLEAN HTML - NO MARKDOWN SYNTAX ALLOWED.
            Use <div class="tldr-section"><em><strong>TL;DR: content</strong></em></div> for summaries.
            Use <h2 class="article-header"> for all main sections.
            Use <h3 class="article-subheader"> for sub-sections within each main section.
            Use <p class="article-paragraph"> for all paragraphs.
            Never use **, ***, ##, ### or any markdown syntax - only HTML tags.
            
            MINIMUM: 800 words total. Build the full narrative around the ground truth metrics.
            """
            
            # Generate the main content using OpenAI (primary for better structure compliance) with fallbacks
            # With auto-retry for validation failures
            content = None
            max_retries = 2
            
            for attempt in range(max_retries + 1):
                # Try OpenAI first (better at following structured output requirements)
                try:
                    content = self.ai_service.generate_content_openai(formatted_prompt, system_prompt)
                except Exception as e:
                    logging.warning(f"OpenAI generation failed: {e}")
                
                # Fallback to Gemini if OpenAI fails
                if not content:
                    try:
                        content = self.gemini_service.generate_content(formatted_prompt, system_prompt)
                    except Exception as e:
                        logging.warning(f"Gemini generation failed: {e}")
                
                # Fallback to Anthropic if available
                if not content:
                    try:
                        content = self.ai_service.generate_content_anthropic(formatted_prompt, system_prompt)
                    except Exception as e:
                        logging.warning(f"Anthropic generation failed: {e}")
                
                if not content:
                    raise Exception("Failed to generate content with any AI service")
                
                # VALIDATION: Check for mandatory 5-section structure and minimum length
                validation_result = self._validate_article_structure(content)
                
                if validation_result['valid']:
                    logging.info(f"Article validation passed: {validation_result['word_count']} words, all sections present")
                    break
                else:
                    if attempt < max_retries:
                        logging.warning(f"Article validation failed (attempt {attempt + 1}): {validation_result['errors']}. Retrying...")
                        # Add retry instruction to prompt
                        formatted_prompt += f"\n\nPREVIOUS ATTEMPT FAILED VALIDATION: {', '.join(validation_result['errors'])}. You MUST include all 6 sections (TL;DR, The Report, Exclusive Data Analysis, The Bitcoin Lens, Transactor Intelligence, Sources) and write at least 1200 words."
                        content = None  # Reset for retry
                    else:
                        logging.warning(f"Article validation failed after {max_retries + 1} attempts: {validation_result['errors']}")
            
            # Extract title from content or generate separately
            title = self._extract_or_generate_title(content, topic)
            
            # Clean up title - remove markdown and common prefixes
            title = self._clean_title(title)
            
            # No summary - TL;DR is embedded in content
            summary = ""
            
            # Generate SEO metadata
            seo_data = self.ai_service.generate_seo_metadata(title, content) or {}
            
            # Generate tags
            tags = self._generate_tags(topic, content)
            
            # Determine category
            category = self._determine_category(topic, content)
            
            # No header images - user preference is to only include tweet screenshots inside articles
            header_image_url = None
            
            # POST-PROCESSING: Verify headline matches requested style
            title = self._enforce_headline_style(title, headline_style, topic)
            
            # FACT-CHECK VERIFICATION: Verify claims before returning article
            fact_check_result = None
            fact_check_warnings = []
            try:
                is_verified, verification_report = verify_article_before_publish(content)
                fact_check_result = verification_report

                if not is_verified:
                    fact_check_warnings = verification_report.get('errors', [])
                    logging.warning(f"FACT-CHECK WARNINGS for article '{title[:50]}': {fact_check_warnings}")
                else:
                    logging.info(f"FACT-CHECK PASSED for article '{title[:50]}': {verification_report.get('claims_verified', 0)} claims verified")
            except Exception as e:
                logging.warning(f"Fact-check failed to run: {e}")
            
            return {
                'title': title,
                'content': content,
                'summary': "",  # No summary - TL;DR is embedded in content
                'category': category,
                'tags': tags,
                'seo_title': seo_data.get('seo_title', title),
                'seo_description': seo_data.get('seo_description', title[:150]),
                'header_image_url': header_image_url,
                'fact_check': fact_check_result,
                'fact_check_warnings': fact_check_warnings,
                'fact_check_passed': len(fact_check_warnings) == 0
            }
            
        except Exception as e:
            logging.error(f"Error generating article: {str(e)}")
            return None
    
    def generate_from_reddit_trend(self, reddit_post):
        """Generate article based on Reddit trending post"""
        try:
            # Combine title and text for context
            context = f"Title: {reddit_post.get('title', '')}\n"
            if reddit_post.get('selftext'):
                context += f"Content: {reddit_post.get('selftext', '')}\n"
            
            # Add comments for additional context
            if reddit_post.get('comments'):
                context += "Top comments:\n"
                for comment in reddit_post.get('comments', [])[:3]:
                    context += f"- {comment.get('body', '')}\n"
            
            topic = f"Based on this Reddit discussion: {context}"
            
            # Generate article with news format
            return self.generate_article(topic, content_type='news_article', source_type='reddit')
            
        except Exception as e:
            logging.error(f"Error generating article from Reddit trend: {str(e)}")
            return None

    def get_partner_youtube_channel_ids(self, featured_only=False):
        """Prioritize partner YouTube channels from core/config/supported_sources.json."""
        return [c["channel_id"] for c in get_partner_youtube_channels(featured_only=featured_only)]

    def _get_prompt_template(self, prompt_id, content_type):
        """Get prompt template from database or use default"""
        if prompt_id:
            try:
                with app.app_context():
                    custom_prompt = models.ContentPrompt.query.get(prompt_id)
                    if custom_prompt and custom_prompt.active:
                        return custom_prompt.prompt_text
            except Exception as e:
                logging.warning(f"Failed to get custom prompt {prompt_id}: {str(e)}")
        
        return self.default_prompts.get(content_type, self.default_prompts['news_article'])
    
    def _enforce_headline_style(self, title: str, headline_style: str, topic: str) -> str:
        """
        Post-process headline to ensure it matches the requested style.
        If headline is wrong style, use AI to rewrite it.
        """
        if not title or not headline_style:
            return title
        
        is_question = title.strip().endswith('?')
        
        # Check if headline matches requested style
        if headline_style == 'statement' and is_question:
            logging.info(f"🔄 Headline mismatch: Got question '{title[:50]}...' but need statement - rewriting")
            try:
                rewrite_prompt = f"""Rewrite this headline as a factual STATEMENT, NOT a question.

CURRENT HEADLINE (WRONG - is a question): {title}

TOPIC CONTEXT: {topic[:200]}

REQUIREMENTS:
- Must be a declarative statement, NOT a question
- Do NOT end with "?"
- Keep it under 15 words
- Be specific with facts/numbers when available
- Start with a noun (company name, "Bitcoin", "Lightning", etc.)

Examples of correct statement headlines:
- "Marathon Digital Expands Solar Mining Operations Across Texas"
- "Bitcoin Network Hashrate Reaches 900 EH/s"
- "Lightning Network Surpasses 5,000 BTC Capacity"

Return ONLY the new headline, nothing else."""
                
                new_title = self.ai_service.generate_content_openai(rewrite_prompt)
                if new_title:
                    new_title = new_title.strip().strip('"').strip("'")
                    if not new_title.endswith('?'):
                        logging.info(f"✅ Headline rewritten: '{new_title[:50]}...'")
                        return new_title
            except Exception as e:
                logging.warning(f"Failed to rewrite headline: {e}")
        
        elif headline_style == 'question' and not is_question:
            logging.info(f"🔄 Headline mismatch: Got statement '{title[:50]}...' but need question - rewriting")
            try:
                rewrite_prompt = f"""Rewrite this headline as a thought-provoking QUESTION.

CURRENT HEADLINE (WRONG - is a statement): {title}

TOPIC CONTEXT: {topic[:200]}

REQUIREMENTS:
- Must be a question that ends with "?"
- Should provoke thought and have a substantive answer
- Keep it under 15 words
- Start with "Is", "Are", "Will", "Can", "How", "What", or "Why"

Examples of correct question headlines:
- "Is Bitcoin Mining Becoming More Decentralized?"
- "Can Lightning Network Handle 1 Million Daily Transactions?"
- "Will Solar-Powered Mining Change the Industry?"

Return ONLY the new headline, nothing else."""
                
                new_title = self.ai_service.generate_content_openai(rewrite_prompt)
                if new_title:
                    new_title = new_title.strip().strip('"').strip("'")
                    if new_title.endswith('?'):
                        logging.info(f"✅ Headline rewritten: '{new_title[:50]}...'")
                        return new_title
            except Exception as e:
                logging.warning(f"Failed to rewrite headline: {e}")
        
        return title
    
    def _clean_title(self, title: str) -> str:
        """Clean up title - remove markdown formatting, HTML tags, and common prefixes"""
        if not title:
            return title
        
        import re
        
        # Remove ALL HTML/XML tags (including <h1>, <headline>, </headline>, etc.)
        title = re.sub(r'<[^>]+>', '', title)
        
        # Remove markdown bold markers
        title = re.sub(r'\*\*', '', title)
        
        # Remove markdown headers (with or without space after #)
        title = re.sub(r'^#{1,6}\s*', '', title)
        
        # Remove common prefixes
        prefixes_to_remove = [
            'Headline:',
            'Title:',
            'Breaking:',
            'BREAKING:',
        ]
        for prefix in prefixes_to_remove:
            if title.strip().startswith(prefix):
                title = title.strip()[len(prefix):].strip()
        
        # Remove quotes at start/end
        title = title.strip().strip('"').strip("'").strip()
        
        return title
    
    def _validate_article_structure(self, content):
        """
        Validate article has all 6 mandatory sections and meets minimum word count.
        Returns dict with 'valid' boolean, 'errors' list, and 'word_count'.
        """
        import re
        
        errors = []
        
        # Check for mandatory sections (6 sections for high-value articles)
        required_sections = [
            ('tldr-section', 'TL;DR section'),
            ('The Report', 'The Report section'),
            ('Exclusive Data Analysis', 'Exclusive Data Analysis section'),
            ('The Bitcoin Lens', 'The Bitcoin Lens section'),
            ('Transactor Intelligence', 'Transactor Intelligence section'),
            ('Sources', 'Sources section')
        ]
        
        for marker, name in required_sections:
            if marker not in content:
                errors.append(f"Missing {name}")
        
        # Count words (strip HTML tags first)
        clean_text = re.sub(r'<[^>]+>', ' ', content)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        word_count = len(clean_text.split())
        
        if word_count < 1200:
            errors.append(f"Only {word_count} words (minimum 1200 required for high-value articles)")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'word_count': word_count
        }
    
    def _extract_or_generate_title(self, content, topic):
        """Extract title from content or generate one using Conversational SEO"""
        try:
            # Try to extract title from the first line if it looks like a headline
            first_line = content.split('\n')[0].strip()
            if len(first_line) < 100 and len(first_line) > 10:
                # Remove common article prefixes and any "Protocol Pulse" branding
                title = first_line.replace('# ', '').replace('## ', '').strip()
                title = title.replace('Protocol Pulse News:', '').replace('Protocol Pulse:', '').strip()
                if title and not title.endswith('.'):
                    return title
            
            # Generate title using AI with CONVERSATIONAL SEO (question-based logic)
            title_prompt = f"""Create a compelling, SEO-friendly headline for an article about: {topic}. 

CONVERSATIONAL SEO MANDATE:
- Use QUESTION-BASED headlines that AI assistants and voice search will surface
- Examples of good question headlines:
  * "How Will the January 22 Difficulty Rise Affect Miners?"
  * "What Does 146.47 T Difficulty Mean for Network Security?"
  * "Why Are Bitcoin Miners Accumulating Before the Halving?"
  * "Is the Current Hashrate Sustainable for Small Miners?"

RULES:
- CRITICAL: Do NOT include 'Protocol Pulse' or any publication name
- Prefer "How", "What", "Why", "Is", "Will" question starters
- If a question doesn't fit naturally, use declarative headlines that answer implied questions
- Keep under 70 characters
- Focus on transactor concerns (network security, mining economics, sovereignty)"""
            title = self.ai_service.generate_content_openai(title_prompt)
            
            if title:
                # Clean up the title - remove any Protocol Pulse branding that slipped through
                title = title.strip().replace('"', '').replace("'", '')
                title = title.replace('Protocol Pulse News:', '').replace('Protocol Pulse:', '').strip()
                return title[:100]  # Limit length
            
            # Fallback to topic-based title (no branding)
            clean_topic = topic[:60].replace('Protocol Pulse', '').strip()
            return clean_topic if clean_topic else topic[:60]
            
        except Exception as e:
            logging.error(f"Error generating title: {str(e)}")
            # Fallback without any branding - just use topic
            clean_topic = topic[:60].replace('Protocol Pulse', '').strip()
            return clean_topic if clean_topic else topic[:60]
    
    def _generate_tags(self, topic, content):
        """Generate relevant tags for the article"""
        try:
            # Bitcoin and DeFi focused tags
            common_tags = [
                'Bitcoin', 'BTC', 'DeFi', 'Cryptocurrency', 'Blockchain',
                'Decentralized Finance', 'Lightning Network', 'Yield Farming', 'Mining', 'Staking',
                'Privacy', 'Regulation', 'Innovation', 'Technology'
            ]
            
            # Use AI to suggest relevant tags
            tag_prompt = f"Based on this topic '{topic}' and content preview '{content[:200]}...', suggest 5-7 relevant tags from Web3/crypto space. Return as comma-separated list."
            
            ai_tags = self.ai_service.generate_content_openai(tag_prompt)
            
            if ai_tags:
                # Clean and combine tags
                suggested_tags = [tag.strip() for tag in ai_tags.split(',')]
                # Combine with common tags and remove duplicates
                all_tags = list(set(suggested_tags + common_tags))
                return ', '.join(all_tags[:8])  # Limit to 8 tags
            
            return ', '.join(common_tags[:5])
            
        except Exception as e:
            logging.error(f"Error generating tags: {str(e)}")
            return 'Web3, Cryptocurrency, Blockchain, Technology, News'
    
    def _determine_category(self, topic, content):
        """Determine the most appropriate category for the article"""
        categories = {
            'Bitcoin': ['bitcoin', 'btc', 'mining', 'halving', 'lightning', 'satoshi'],
            'DeFi': ['defi', 'yield', 'liquidity', 'dex', 'lending', 'aave', 'uniswap', 'compound'],
            'Regulation': ['regulation', 'sec', 'government', 'legal', 'compliance'],
            'Privacy': ['privacy', 'anonymous', 'surveillance', 'encryption'],
            'Innovation': ['innovation', 'development', 'technology', 'breakthrough']
        }
        
        topic_lower = topic.lower()
        content_lower = content[:500].lower()
        combined_text = f"{topic_lower} {content_lower}"
        
        # Score each category
        category_scores = {}
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score, default to Web3
        if category_scores:
            return max(category_scores.keys(), key=lambda x: category_scores[x])
        
        return 'Web3'