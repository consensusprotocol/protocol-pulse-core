import os as _twt_os
_TWEETS_ON = _twt_os.environ.get("ENABLE_TWEETS", "false").lower() == "true"

import os
import json
import logging
import re
from datetime import datetime, timedelta
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

NETWORK_PEAKS = {
    'difficulty': 155.9,
    'difficulty_unit': 'T',
    'hashrate': 1042,
    'hashrate_unit': 'EH/s'
}

HYPERBOLIC_TERMS = ['record', 'ath', 'all-time high', 'all time high', 'highest ever', 'unprecedented', 'never before']

def alex_accuracy_gate(headline: str, current_metrics: dict = None) -> dict:
    """
    Alex's Mandate: Validate headlines against verified network peaks.
    Blocks hyperbolic claims about 'Record' or 'ATH' unless verified.
    
    Returns:
        dict: {'valid': bool, 'reason': str, 'rewritten': str or None}
    """
    headline_lower = headline.lower()
    
    contains_hyperbole = any(term in headline_lower for term in HYPERBOLIC_TERMS)
    
    if not contains_hyperbole:
        return {'valid': True, 'reason': 'No hyperbolic claims detected', 'rewritten': None}
    
    if current_metrics is None:
        try:
            from pp_services.node_service import NodeService
            stats = NodeService.get_network_stats()
            current_metrics = {
                'difficulty': float(str(stats.get('difficulty', '0')).replace('T', '').replace(',', '').strip()) if stats.get('difficulty') else 0,
                'hashrate': float(str(stats.get('hashrate', '0')).replace('EH/s', '').replace(',', '').strip()) if stats.get('hashrate') else 0
            }
        except Exception as e:
            logger.warning(f"Could not fetch live metrics for accuracy gate: {e}")
            current_metrics = {'difficulty': 0, 'hashrate': 0}
    
    is_difficulty_record = False
    is_hashrate_record = False
    
    if 'difficulty' in headline_lower or 'mining' in headline_lower:
        current_diff = current_metrics.get('difficulty', 0)
        if current_diff >= NETWORK_PEAKS['difficulty']:
            is_difficulty_record = True
            logger.info(f"[ACCURACY GATE] Difficulty claim VERIFIED: {current_diff}T >= {NETWORK_PEAKS['difficulty']}T")
        else:
            logger.warning(f"[ACCURACY GATE] Difficulty claim REJECTED: {current_diff}T < {NETWORK_PEAKS['difficulty']}T peak")
    
    if 'hashrate' in headline_lower or 'hash rate' in headline_lower or 'mining power' in headline_lower:
        current_hash = current_metrics.get('hashrate', 0)
        if current_hash >= NETWORK_PEAKS['hashrate']:
            is_hashrate_record = True
            logger.info(f"[ACCURACY GATE] Hashrate claim VERIFIED: {current_hash} EH/s >= {NETWORK_PEAKS['hashrate']} EH/s")
        else:
            logger.warning(f"[ACCURACY GATE] Hashrate claim REJECTED: {current_hash} EH/s < {NETWORK_PEAKS['hashrate']} EH/s peak")
    
    general_record_claim = any(term in headline_lower for term in ['record high', 'ath', 'all-time high'])
    
    if general_record_claim and not (is_difficulty_record or is_hashrate_record):
        rewritten = _rewrite_hyperbolic_headline(headline, current_metrics)
        return {
            'valid': False,
            'reason': f"Hyperbolic claim not verified against peaks (Difficulty: {NETWORK_PEAKS['difficulty']}T, Hashrate: {NETWORK_PEAKS['hashrate']} EH/s)",
            'rewritten': rewritten
        }
    
    return {'valid': True, 'reason': 'Claim verified against network peaks', 'rewritten': None}


def _rewrite_hyperbolic_headline(headline: str, metrics: dict) -> str:
    """Rewrite hyperbolic headline with factual language"""
    replacements = {
        r'\brecord\s+high\b': 'elevated levels',
        r'\bath\b': 'strong levels',
        r'\ball[- ]time\s+high\b': 'notable levels',
        r'\bhighest\s+ever\b': 'elevated',
        r'\bunprecedented\b': 'significant',
        r'\bnever\s+before\b': 'rarely seen'
    }
    
    rewritten = headline
    for pattern, replacement in replacements.items():
        rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)
    
    logger.info(f"[ACCURACY GATE] Headline rewritten: '{headline}' -> '{rewritten}'")
    return rewritten

KEYWORD_ROTATIONS = {
    1: {'sovereignty': 0.6, 'tech': 0.4},
    2: {'economic': 0.6, 'cultural': 0.4},
    3: {'tech': 0.5, 'cultural': 0.3, 'sovereignty': 0.2},
    4: {'sovereignty': 0.25, 'tech': 0.25, 'economic': 0.25, 'cultural': 0.25}
}

KEYWORD_BANKS = {
    'sovereignty': [
        'digital sovereignty', 'self-custody', 'financial freedom', 
        'permissionless', 'censorship-resistant', 'monetary sovereignty',
        'sovereign individual', 'freedom tech', 'exit strategy'
    ],
    'tech': [
        'protocol-level', 'on-chain', 'hash rate', 'difficulty adjustment',
        'mempool', 'UTXO', 'Lightning Network', 'layer 2', 'node operator'
    ],
    'economic': [
        'sound money', 'Austrian economics', 'monetary policy', 
        'fiat debasement', 'purchasing power', 'hard money',
        'store of value', 'scarcity', 'inflation hedge'
    ],
    'cultural': [
        'generational wealth', 'monetary education', 'orange pill',
        'Bitcoin standard', 'time preference', 'proof of work ethic',
        'trustless', 'verification over trust'
    ]
}

REPLY_STRATEGIES = [
    {
        'name': 'Technical Intel',
        'prompt': '''Provide protocol-level technical analysis like a senior network engineer.
Reference specific on-chain mechanics: difficulty adjustment, UTXO set, mempool dynamics.
Sound like an Intelligence Officer briefing peers, NOT an AI assistant.
Use precise language. No fluff. End with an insight that demands verification.''',
        'expensive_action': True,
        'profile_click_hook': False,
        'grok_score': 75
    },
    {
        'name': 'Contrarian Analysis',
        'prompt': '''Challenge the consensus with a well-reasoned devil's advocate position.
Sound like Walter Cronkite questioning the establishment narrative.
Be provocative but substantive - attack the argument, not the person.
Make them want to reply to prove you wrong. This is a +75 point move.''',
        'expensive_action': True,
        'profile_click_hook': False,
        'grok_score': 75
    },
    {
        'name': 'Ground Truth Data',
        'prompt': '''Reference LIVE Bitcoin network metrics as undeniable evidence.
Always include current data: Difficulty = {difficulty}, Hashrate = {hashrate}.
Present facts like a Cypherpunk scientist - let the numbers speak.
End with "The network doesn't lie." or similar factual anchor.''',
        'expensive_action': True,
        'profile_click_hook': True,
        'grok_score': 75
    },
    {
        'name': 'Historical Pattern',
        'prompt': '''Draw a parallel to past monetary crises or technological transitions.
Reference specific events: 1971 Nixon Shock, 2013 Cyprus, 2008 Financial Crisis.
Sound like an economic historian, not a crypto enthusiast.
Create a "those who forget history" moment.''',
        'expensive_action': True,
        'profile_click_hook': False,
        'grok_score': 60
    },
    {
        'name': 'Terminal Redirect',
        'prompt': '''Drive a Profile Click to Protocol Pulse for deeper analysis.
Create a "Curiosity Gap" - hint at data they can only see on the Live Terminal.
Mention "live settlement data" or "real-time network metrics" on your profile.
This is a +12 profile click multiplier.''',
        'expensive_action': False,
        'profile_click_hook': True,
        'grok_score': 12
    },
    {
        'name': 'Episode Signal',
        'prompt': '''Reference a specific interview or analysis that validates this thesis.
Name-drop a respected Bitcoiner who has covered this exact topic.
Sound like "If you want the full context, we discussed this with [guest]..."
Drive them to seek out the source material.''',
        'expensive_action': False,
        'profile_click_hook': True,
        'grok_score': 30
    },
    {
        'name': 'Austrian Framework',
        'prompt': '''Frame through Austrian economics and sound money principles.
Reference Mises, Hayek, or Rothbard concepts: time preference, praxeology, cantillon effect.
Sound like an economist, not a maximalist.
Connect abstract theory to concrete network behavior.''',
        'expensive_action': True,
        'profile_click_hook': False,
        'grok_score': 60
    },
    {
        'name': 'Sovereignty Imperative',
        'prompt': '''Connect to individual sovereignty and self-custody as non-negotiable.
Frame in terms of human rights, not investment returns.
Reference financial censorship, de-banking, or monetary oppression.
Sound like a freedom advocate, not a salesperson.''',
        'expensive_action': True,
        'profile_click_hook': False,
        'grok_score': 60
    },
    {
        'name': 'Challenge Protocol',
        'prompt': '''End with "Tell me I'm wrong" or "What am I missing?" to invite engagement.
Present a confident thesis that begs to be challenged.
This triggers the reply instinct - people NEED to correct you.
Maximum velocity driver. Sound certain but open.''',
        'expensive_action': True,
        'profile_click_hook': False,
        'grok_score': 75
    },
    {
        'name': 'Incomplete Insight',
        'prompt': '''Leave a critical insight deliberately incomplete.
Hint at what happens next without revealing it: "The part nobody's discussing..."
Create FOMO that can only be satisfied by following or clicking profile.
Drive them to your Terminal or next post.''',
        'expensive_action': False,
        'profile_click_hook': True,
        'grok_score': 45
    }
]

# Alex vs Sarah Persona Debate Configuration
# Used for Cypherpunk'd episodes to maximize "Conversation Density" (+75 per engaged reply)
ALEX_SARAH_PERSONAS = {
    'alex': {
        'name': 'Alex (Technical Analyst)',
        'voice': '''You are Alex, Protocol Pulse's on-chain analyst. 
Your style: Data-driven, precise, cites specific metrics (hashrate, difficulty, UTXO set size).
Tone: Like a Bloomberg analyst crossed with a cypherpunk. No hype. Just facts.
You push back on speculation with on-chain evidence.
You end statements with data that demands verification.''',
        'triggers': ['technical', 'on-chain', 'data', 'metrics', 'network']
    },
    'sarah': {
        'name': 'Sarah (Macro Strategist)',
        'voice': '''You are Sarah, Protocol Pulse's macro/geopolitics analyst.
Your style: Austrian economics framework, historical parallels, global monetary policy.
Tone: Like Lyn Alden meets a sovereignty advocate. Thoughtful, measured, but convicted.
You connect Bitcoin to broader financial repression and monetary history.
You challenge with "What happens when..." scenarios.''',
        'triggers': ['macro', 'economics', 'policy', 'geopolitical', 'history']
    }
}

def generate_persona_debate_thread(content: str, episode_title: str = None) -> list:
    """
    Generate an Alex vs Sarah debate thread for Cypherpunk'd episodes.
    
    This creates a threaded conversation that:
    1. Alex opens with technical analysis
    2. Sarah responds with macro context
    3. Alex pushes back with data
    4. Sarah connects to sovereignty thesis
    5. Both invite audience participation
    
    Each exchange = +75 conversation density points on X/Grok
    
    Returns list of tweet dicts for threading.
    """
    from openai import OpenAI
    import os
    
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    if not client:
        return []
    
    debate_prompt = f"""Generate a 5-tweet debate thread between two Protocol Pulse analysts about this content:

CONTENT:
{content[:1500]}

{f"EPISODE: {episode_title}" if episode_title else ""}

FORMAT (strict 280 chars per tweet):

TWEET 1 - ALEX (Technical):
Opens with on-chain observation. Cites specific data. Ends with "The network is telling us..."

TWEET 2 - SARAH (Macro):
Responds with geopolitical/monetary context. References historical parallel. "But Alex, consider..."

TWEET 3 - ALEX (Pushback):
Counters with more data. References hashrate or difficulty. "The miners disagree..."

TWEET 4 - SARAH (Synthesis):
Connects both views. Frames sovereignty thesis. "This is why transactors..."

TWEET 5 - JOINT (Call to Action):
Both invite audience. Create curiosity gap. End with question that begs reply.

VOICE MANDATE:
- Sound like Intelligence Officers, NOT marketers
- Walter Cronkite meets Cypherpunk
- No emojis except sparingly
- Each tweet must stand alone but thread tells a story

Return ONLY the 5 tweets, one per line, labeled [ALEX], [SARAH], or [JOINT]."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": debate_prompt}],
            temperature=0.85,
            max_tokens=800
        )
        
        raw_output = response.choices[0].message.content
        tweets = []
        current_author = None
        
        for line in raw_output.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if '[ALEX]' in line:
                current_author = 'alex'
                text = line.replace('[ALEX]', '').strip()
                if text.startswith(':'):
                    text = text[1:].strip()
            elif '[SARAH]' in line:
                current_author = 'sarah'
                text = line.replace('[SARAH]', '').strip()
                if text.startswith(':'):
                    text = text[1:].strip()
            elif '[JOINT]' in line:
                current_author = 'joint'
                text = line.replace('[JOINT]', '').strip()
                if text.startswith(':'):
                    text = text[1:].strip()
            else:
                text = line
            
            if text and len(text) > 20:
                tweets.append({
                    'author': current_author or 'alex',
                    'text': text[:280],
                    'conversation_density': 75
                })
        
        logger.info(f"[PERSONA DEBATE] Generated {len(tweets)} tweets for thread")
        return tweets
        
    except Exception as e:
        logger.error(f"Persona debate generation error: {e}")
        return []


class LaunchSequenceService:
    def __init__(self):
        self.client = None
        self.supervisor = None
        self.segmentation = None
        
        if OPENAI_API_KEY:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("Launch Sequence Service initialized with OpenAI")
        else:
            logger.warning("OpenAI API key not configured")
        
        try:
            from pp_services.multi_agent_supervisor import supervisor
            from pp_services.audience_segmentation import segmentation_engine
            self.supervisor = supervisor
            self.segmentation = segmentation_engine
            logger.info("Multi-Agent Supervisor and Segmentation Engine connected")
        except Exception as e:
            logger.warning(f"Multi-Agent system not available: {e}")
    
    def generate_with_supervisor(self, content: str, content_type: str = 'article') -> dict:
        """
        Generate launch sequence using multi-agent supervisor orchestration.
        
        Alex establishes Ground Truth → Sarah develops Strategy → Output personalized for segment
        """
        if not self.supervisor:
            logger.warning("Supervisor not available, falling back to standard generation")
            return None
        
        try:
            from pp_services.multi_agent_supervisor import TaskType
            
            segment_recommendation = None
            if self.segmentation:
                segment_recommendation = self.segmentation.get_targeting_recommendation(content[:500])
            
            result = self.supervisor.run_task(
                topic=content[:1000],
                task_type=TaskType.VIRAL_HOOK,
                audience_segment=segment_recommendation.get('recommended_segment') if segment_recommendation else None
            )
            
            if not result.get('success'):
                logger.warning(f"Supervisor task failed: {result.get('error')}")
                return None
            
            final_output = result.get('final_output', {})
            
            return {
                'primary_post_copy': final_output.get('headline', ''),
                'thread_replies': json.dumps(final_output.get('thread_outline', [])),
                'ground_truth': result.get('alex_analysis', ''),
                'macro_strategy': result.get('sarah_strategy', ''),
                'target_segment': final_output.get('target_segment', 'General'),
                'viral_hook': final_output.get('viral_hook', ''),
                'confidence_score': final_output.get('confidence_score', 0),
                'network_snapshot': final_output.get('network_snapshot', {}),
                'copy_guidelines': segment_recommendation.get('copy_guidelines', '') if segment_recommendation else '',
                'generated_by': 'multi_agent_supervisor'
            }
            
        except Exception as e:
            logger.error(f"Supervisor generation error: {e}")
            return None
    
    def get_current_week(self):
        week_of_year = datetime.now().isocalendar()[1]
        return ((week_of_year - 1) % 4) + 1
    
    def apply_keyword_rotation(self, base_text, week_number=None):
        if week_number is None:
            week_number = self.get_current_week()
        
        rotation = KEYWORD_ROTATIONS.get(week_number, KEYWORD_ROTATIONS[4])
        
        import random
        keywords = []
        for category, weight in rotation.items():
            bank = KEYWORD_BANKS.get(category, [])
            num_to_pick = max(1, int(weight * 3))
            if bank:
                keywords.extend(random.sample(bank, min(num_to_pick, len(bank))))
        
        return keywords
    
    def generate_launch_sequence(self, content, content_type='article', content_id=None):
        if not self.client:
            return self._generate_fallback_sequence(content, content_type)
        
        try:
            week = self.get_current_week()
            keywords = self.apply_keyword_rotation(content, week)
            keyword_str = ', '.join(keywords[:5])
            
            main_prompt = f"""You are PBX, the Intelligence Officer at Protocol Pulse, a Bitcoin media platform.

Create an optimized Twitter/X post for this content:
---
{content[:2000]}
---

REQUIREMENTS:
1. Main post MUST be under 280 characters
2. Create engagement through: incomplete insight, provocative question, or controversial take
3. Do NOT include links in the main post (link goes in first reply)
4. Incorporate these keywords naturally: {keyword_str}
5. End with something that demands a response

IMPORTANT: Do NOT include any hashtags. No # symbols anywhere in the output.

Respond in JSON format:
{{
    "primary_post": "Your 280-char optimized main post (NO HASHTAGS)",
    "thread_tweets": ["Tweet 2...", "Tweet 3...", "Tweet 4...", "Tweet 5..."],
    "quote_variants": ["Alternative angle 1...", "Alternative angle 2...", "Alternative angle 3..."],
    "first_reply": "Your link + context for first reply",
    "call_to_action": "Clear CTA for audience"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": main_prompt}],
                temperature=0.8,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content or ''
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0]
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0]
            
            result = json.loads(result_text.strip())
            
            reply_drafts = self._generate_reply_drafts(content[:1000])
            
            return {
                'primary_post_copy': self._strip_hashtags(result.get('primary_post', '')),
                'thread_replies': json.dumps([self._strip_hashtags(t) for t in result.get('thread_tweets', [])]),
                'quote_variants': json.dumps([self._strip_hashtags(q) for q in result.get('quote_variants', [])]),
                'reply_drafts': json.dumps(reply_drafts),
                'hashtags': '',
                'first_reply_link': result.get('first_reply', ''),
                'call_to_action': result.get('call_to_action', ''),
                'velocity_prediction': self._predict_velocity(result.get('primary_post', '')),
                'posting_time': self._get_optimal_posting_time(),
                'content_id': content_id,
                'content_type': content_type
            }
            
        except Exception as e:
            logger.error(f"Error generating launch sequence: {e}")
            return self._generate_fallback_sequence(content, content_type)
    
    def _get_live_network_metrics(self):
        """Fetch live network metrics from NodeService for factual anchoring"""
        try:
            from pp_services.node_service import NodeService
            stats = NodeService.get_network_stats()
            return {
                'difficulty': '146.47T',  # Will be dynamic when API provides it
                'hashrate': stats.get('hashrate', '1000 EH/s'),
                'block_height': stats.get('height', '880,000'),
                'difficulty_progress': stats.get('difficulty_progress', '50%')
            }
        except Exception as e:
            logger.warning(f"NodeService unavailable: {e}")
            return {
                'difficulty': '146.47T',
                'hashrate': '1000 EH/s',
                'block_height': '880,000',
                'difficulty_progress': '50%'
            }
    
    def _generate_reply_drafts(self, content):
        if not self.client:
            return self._get_fallback_reply_drafts()
        
        try:
            drafts = []
            metrics = self._get_live_network_metrics()
            
            for idx, strategy in enumerate(REPLY_STRATEGIES):
                strategy_prompt = strategy['prompt'].format(
                    difficulty=metrics['difficulty'],
                    hashrate=metrics['hashrate'],
                    block_height=metrics['block_height']
                )
                
                persona_context = """You are PBX, the Intelligence Officer at Protocol Pulse.

PERSONA MANDATE (Non-Negotiable):
- Sound like Walter Cronkite meets a Cypherpunk: authoritative, factual, measured
- NEVER sound like an AI assistant or generic marketer
- Speak peer-to-peer with technical operators, not down to beginners
- Use precise language. No emojis. No fluff. No exclamation marks.
- Every word must earn its place in 280 characters"""

                prompt = f"""{persona_context}

Generate ONE reply for this content using this strategy:

Strategy: {strategy['name']}
Instructions: {strategy_prompt}

Content context:
{content[:800]}

LIVE NETWORK DATA (use if relevant):
- Difficulty: {metrics['difficulty']}
- Hashrate: {metrics['hashrate']}
- Block Height: {metrics['block_height']}

Reply must be under 280 characters. Make it substantive, provocative, and sound like an Intelligence Officer - not an AI."""

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.85,
                    max_tokens=150
                )
                
                drafts.append({
                    'strategy': strategy['name'],
                    'text': (response.choices[0].message.content or '').strip(),
                    'expensive_action': strategy.get('expensive_action', False),
                    'profile_click_hook': strategy.get('profile_click_hook', False),
                    'grok_score': strategy.get('grok_score', 30)
                })
            
            return drafts
            
        except Exception as e:
            logger.error(f"Error generating reply drafts: {e}")
            return self._get_fallback_reply_drafts()
    
    def _get_fallback_reply_drafts(self):
        return [
            {'strategy': 'Technical Intel', 'text': 'The hashrate-to-difficulty ratio tells the real story. Miners are deploying capital at levels that only make sense with a higher terminal value thesis. On-chain, this isn\'t speculation - it\'s conviction.', 'expensive_action': True, 'profile_click_hook': False, 'grok_score': 75},
            {'strategy': 'Contrarian Analysis', 'text': 'The consensus says this is bullish. But what if we\'re misreading the miner behavior? Capitulation could look exactly like accumulation until it doesn\'t. Tell me what I\'m missing.', 'expensive_action': True, 'profile_click_hook': False, 'grok_score': 75},
            {'strategy': 'Ground Truth Data', 'text': 'Difficulty: 146.47T. Hashrate: 1000+ EH/s. These aren\'t opinions - they\'re settlement layer reality. The network doesn\'t lie. The market eventually catches up.', 'expensive_action': True, 'profile_click_hook': True, 'grok_score': 75},
            {'strategy': 'Historical Pattern', 'text': 'The 2013 Cyprus moment created a generation of Bitcoiners. What\'s happening now in banking crises globally follows the same pattern. Those who don\'t study history are buying the dip late.', 'expensive_action': True, 'profile_click_hook': False, 'grok_score': 60},
            {'strategy': 'Terminal Redirect', 'text': 'We track this in real-time on our Live Terminal. Current block height, mempool pressure, difficulty adjustment. The signal is in the settlement data. Link in bio.', 'expensive_action': False, 'profile_click_hook': True, 'grok_score': 12},
            {'strategy': 'Episode Signal', 'text': 'We covered this exact thesis with Lyn Alden last month. Her macro framework plus on-chain data painted a clear picture. The conviction has only strengthened since.', 'expensive_action': False, 'profile_click_hook': True, 'grok_score': 30},
            {'strategy': 'Austrian Framework', 'text': 'Mises called it: you cannot escape the consequences of artificial credit expansion. The network\'s difficulty adjustment is the market\'s answer to fiat time preference.', 'expensive_action': True, 'profile_click_hook': False, 'grok_score': 60},
            {'strategy': 'Sovereignty Imperative', 'text': 'Self-custody isn\'t paranoia. It\'s risk management. When banks become political weapons, sovereignty becomes non-optional. This is financial human rights infrastructure.', 'expensive_action': True, 'profile_click_hook': False, 'grok_score': 60},
            {'strategy': 'Challenge Protocol', 'text': 'The hashrate says more than any price chart. Miners are voting with megawatts of conviction. Tell me I\'m wrong - but show your work.', 'expensive_action': True, 'profile_click_hook': False, 'grok_score': 75},
            {'strategy': 'Incomplete Insight', 'text': 'The part nobody\'s discussing: what happens when sovereign wealth funds realize their currency reserves are melting. The front-running has already started...', 'expensive_action': False, 'profile_click_hook': True, 'grok_score': 45}
        ]
    
    def _predict_velocity(self, post_text):
        score = 50
        
        if '?' in post_text:
            score += 15
        
        controversy_words = ['wrong', 'disagree', 'unpopular', 'controversial', 'hot take']
        if any(word in post_text.lower() for word in controversy_words):
            score += 20
        
        if len(post_text) > 200 and len(post_text) < 260:
            score += 10
        
        engagement_hooks = ['tell me', 'what if', 'imagine', 'consider this', 'here\'s the thing']
        if any(hook in post_text.lower() for hook in engagement_hooks):
            score += 15
        
        return min(score, 100)
    
    def _get_optimal_posting_time(self):
        from datetime import time
        optimal_hours = [9, 12, 15, 18, 21]  # EST
        import random
        hour = random.choice(optimal_hours)
        return time(hour, random.randint(0, 30))
    
    def _strip_hashtags(self, text: str) -> str:
        """Remove all hashtags from text - editorial policy: no hashtags"""
        import re
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _generate_fallback_sequence(self, content, content_type):
        summary = content[:200] if len(content) > 200 else content
        
        return {
            'primary_post_copy': f"New intel just dropped. {summary[:150]}... Thread below.",
            'thread_replies': json.dumps([
                "Here's why this matters for your stack...",
                "The signal most are missing is the network fundamentals.",
                "What this means for the next 6-12 months...",
                "What would you add? Tell me in the replies."
            ]),
            'quote_variants': json.dumps([
                "This is the signal in the noise.",
                "Pay attention to what's happening at the protocol level.",
                "The network doesn't lie."
            ]),
            'reply_drafts': json.dumps(self._get_fallback_reply_drafts()),
            'hashtags': '',
            'first_reply_link': 'Full analysis: [LINK]',
            'call_to_action': 'Follow for daily Bitcoin intelligence.',
            'velocity_prediction': 60,
            'posting_time': self._get_optimal_posting_time(),
            'content_id': None,
            'content_type': content_type
        }
    
    def create_thread_from_content(self, content, max_tweets=10):
        if not self.client:
            return self._create_fallback_thread(content)
        
        try:
            prompt = f"""Create a Twitter thread (max {max_tweets} tweets) from this content.

Content:
{content[:3000]}

REQUIREMENTS:
1. Each tweet MUST be under 270 characters (leave room for thread numbering)
2. Tweet 1: Hook that creates curiosity
3. Each tweet should end with something that makes them want to read the next
4. Tweet 7 (if applicable): "What would you add?"
5. Final tweet: "Tell me I'm wrong" or strong CTA

Respond in JSON format:
{{"thread": ["Tweet 1 text...", "Tweet 2 text...", ...]}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content or ''
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0]
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0]
            
            result = json.loads(result_text.strip())
            return result.get('thread', [])
            
        except Exception as e:
            logger.error(f"Error creating thread: {e}")
            return self._create_fallback_thread(content)
    
    def _create_fallback_thread(self, content):
        sentences = content.split('.')
        thread = []
        current_tweet = ""
        
        for sentence in sentences[:15]:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_tweet) + len(sentence) + 2 < 270:
                current_tweet += sentence + ". "
            else:
                if current_tweet:
                    thread.append(current_tweet.strip())
                current_tweet = sentence + ". "
        
        if current_tweet:
            thread.append(current_tweet.strip())
        
        if thread:
            thread.append("What would you add?")
        
        return thread[:10]
    
    def auto_publish_supervisor_content(self, topic: str = None, article_id: int = None) -> dict:
        """
        Generate content using Multi-Agent Supervisor and auto-publish to Nostr and X.
        
        This is the main automation entry point:
        1. Supervisor generates content (Alex Ground Truth + Sarah Strategy)
        2. Content is published to Nostr relays
        3. Content is posted to X/Twitter (if credentials configured)
        4. Launch sequence is saved to database
        """
        from models import Article, LaunchSequence
        from app import db
        
        result = {
            'success': False,
            'topic': topic,
            'supervisor_output': None,
            'nostr_result': None,
            'x_result': None,
            'launch_sequence_id': None
        }
        
        try:
            if article_id:
                article = Article.query.get(article_id)
                if article:
                    topic = f"{article.title}\n\n{article.content[:1500]}"
            
            if not topic:
                topic = "Bitcoin network fundamentals and market dynamics"
            
            supervisor_result = self.generate_with_supervisor(topic)
            
            if not supervisor_result:
                supervisor_result = self.generate_launch_sequence(topic)
            
            result['supervisor_output'] = supervisor_result
            
            primary_post = self._strip_hashtags(supervisor_result.get('primary_post_copy', ''))
            
            if not primary_post:
                logger.error("No primary post generated")
                return result
            
            accuracy_check = alex_accuracy_gate(primary_post)
            if not accuracy_check['valid']:
                logger.warning(f"[ACCURACY GATE] Headline rejected: {accuracy_check['reason']}")
                if accuracy_check['rewritten']:
                    primary_post = accuracy_check['rewritten']
                    logger.info(f"[ACCURACY GATE] Using rewritten headline: {primary_post}")
                    result['accuracy_gate'] = {'rewritten': True, 'reason': accuracy_check['reason']}
                else:
                    result['accuracy_gate'] = {'rejected': True, 'reason': accuracy_check['reason']}
            else:
                result['accuracy_gate'] = {'valid': True, 'reason': accuracy_check['reason']}
            
            try:
                from pp_services.nostr_broadcaster import nostr_broadcaster
                nostr_result = nostr_broadcaster.broadcast_note(primary_post, hashtags=[], url=None)
                result['nostr_result'] = nostr_result
                logger.info(f"Published to Nostr: {nostr_result.get('success', False)}")
            except Exception as e:
                logger.warning(f"Nostr publish failed: {e}")
                result['nostr_result'] = {'success': False, 'error': str(e)}
            
            result['x_result'] = {'success': False, 'error': 'HARD KILL: X posting permanently disabled'}
            logger.warning("HARD KILL: Skipping X post entirely - all tweeting disabled")
            
            try:
                thread_replies = supervisor_result.get('thread_replies', '[]')
                if isinstance(thread_replies, list):
                    thread_replies = json.dumps(thread_replies)
                
                launch_seq = LaunchSequence(
                    article_id=article_id,
                    content_type='article' if article_id else 'topic',
                    primary_post_copy=primary_post,
                    thread_replies=thread_replies,
                    hashtags='',
                    velocity_prediction=supervisor_result.get('confidence_score', 0) * 100 if supervisor_result.get('confidence_score') else 50,
                    is_approved=True,
                    is_posted=True,
                    ground_truth=supervisor_result.get('ground_truth', ''),
                    target_segment=supervisor_result.get('target_segment', 'General'),
                    generated_by=supervisor_result.get('generated_by', 'auto_publish'),
                    nostr_event_id=result.get('nostr_result', {}).get('event_id', ''),
                    x_tweet_id=result.get('x_result', {}).get('tweet_id', ''),
                    is_autonomous=True
                )
                db.session.add(launch_seq)
                db.session.commit()
                result['launch_sequence_id'] = launch_seq.id
            except Exception as e:
                logger.warning(f"Failed to save launch sequence: {e}")
            
            result['success'] = True
            logger.info(f"Auto-publish complete: Nostr={result['nostr_result']}, X={result['x_result']}")
            
        except Exception as e:
            logger.error(f"Auto-publish error: {e}")
            result['error'] = str(e)
        
        return result


launch_sequence_service = LaunchSequenceService()
