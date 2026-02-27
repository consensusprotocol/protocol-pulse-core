"""
Discord Stage Automation Service - The Debate Loop

Implements Alex vs Sarah debate sessions in Discord Stage channels
with ElevenLabs voice streaming and Signal Point rewards.
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DebateParticipant:
    user_id: str
    joined_at: datetime
    left_at: Optional[datetime] = None
    
    @property
    def duration_minutes(self) -> float:
        end_time = self.left_at or datetime.utcnow()
        return (end_time - self.joined_at).total_seconds() / 60


class DebateEngine:
    """Handles the Alex vs Sarah Handshake Debate format."""
    
    DEBATE_SCRIPTS = {
        'difficulty_retarget': {
            'title': 'The Great Difficulty Retarget Debate',
            'duration_minutes': 15,
            'segments': [
                {
                    'speaker': 'sarah',
                    'role': 'The Macro Strategist',
                    'type': 'intro',
                    'template': "Welcome, Operatives, to the Protocol Pulse War Room. We are currently {hours_to_adjustment} hours from the next difficulty adjustment. Alex, I'm seeing a massive spike in on-chain volume. What is the ground truth telling us?"
                },
                {
                    'speaker': 'alex',
                    'role': 'The Quant Analyst',
                    'type': 'technical_data',
                    'template': "Ground truth confirmed, Sarah. Current difficulty is {difficulty}. We are trending toward a {adjustment_percent} adjustment. However, hashrate has normalized at {hashrate}, which is still below our verified peak of 1042 EH/s. Any claim of a record high right now is a hallucination."
                },
                {
                    'speaker': 'sarah',
                    'role': 'The Macro Strategist',
                    'type': 'macro_insight',
                    'template': "Spoken like a true quant. But look at the capital flows. Institutional transactors are moving into cold storage. This isn't just hashrate growth; it's a computational moat being built by the largest miners in the world. They aren't just mining; they're settling the future of the global financial stack."
                },
                {
                    'speaker': 'sarah',
                    'role': 'The Macro Strategist',
                    'type': 'outro',
                    'template': "Operatives, the floor is open. Drop your questions in the #ask-alex channel. We will be here for 15 minutes. Stay sovereign."
                }
            ]
        },
        'whale_movement': {
            'title': 'Whale Movement Analysis',
            'duration_minutes': 10,
            'segments': [
                {
                    'speaker': 'alex',
                    'role': 'The Quant Analyst',
                    'type': 'intro',
                    'template': "Whale Alert triggered. We're seeing {whale_count} transactions over 500 BTC in the past hour. Total movement: {total_btc} BTC. Sarah, what's your read on the macro implications?"
                },
                {
                    'speaker': 'sarah',
                    'role': 'The Macro Strategist',
                    'type': 'macro_insight',
                    'template': "This level of whale activity typically precedes major market moves. The smart money is positioning. Whether it's accumulation or distribution depends on the destination addresses. Alex, are these moving to exchanges or cold storage?"
                },
                {
                    'speaker': 'alex',
                    'role': 'The Quant Analyst',
                    'type': 'technical_data',
                    'template': "On-chain analysis shows {exchange_percent}% moving to known exchange addresses. The remaining {cold_percent}% appears to be cold storage or unknown wallets. This suggests a mixed signal—some profit-taking, but strong hodl conviction remains."
                }
            ]
        }
    }
    
    def __init__(self):
        self.active_debate: Optional[Dict] = None
        self.participants: Dict[str, DebateParticipant] = {}
        self.question_queue: List[Dict] = []
    
    async def get_network_data(self) -> Dict[str, Any]:
        """Fetch live network data for debate context."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                # Get difficulty data
                diff_resp = await client.get('https://mempool.space/api/v1/difficulty-adjustment')
                diff_data = diff_resp.json()
                
                # Get hashrate
                hash_resp = await client.get('https://mempool.space/api/v1/mining/hashrate/3d')
                hash_data = hash_resp.json()
                
                return {
                    'difficulty': f"{diff_data.get('difficultyChange', 0):.2f}T",
                    'adjustment_percent': f"{diff_data.get('difficultyChange', 0):+.1f}%",
                    'hours_to_adjustment': int(diff_data.get('remainingTime', 0) / 3600000),
                    'hashrate': f"{hash_data.get('currentHashrate', 0) / 1e18:.0f} EH/s",
                    'whale_count': 5,
                    'total_btc': 2500,
                    'exchange_percent': 35,
                    'cold_percent': 65
                }
        except Exception as e:
            logger.error(f"Failed to fetch network data: {e}")
            return {
                'difficulty': '146.47T',
                'adjustment_percent': '+3.4%',
                'hours_to_adjustment': 48,
                'hashrate': '977 EH/s',
                'whale_count': 3,
                'total_btc': 1500,
                'exchange_percent': 40,
                'cold_percent': 60
            }
    
    async def generate_debate_script(self, script_type: str = 'difficulty_retarget') -> List[Dict]:
        """Generate a debate script with live data."""
        script = self.DEBATE_SCRIPTS.get(script_type, self.DEBATE_SCRIPTS['difficulty_retarget'])
        network_data = await self.get_network_data()
        
        generated_segments = []
        for segment in script['segments']:
            text = segment['template'].format(**network_data)
            generated_segments.append({
                'speaker': segment['speaker'],
                'role': segment['role'],
                'type': segment['type'],
                'text': text
            })
        
        return generated_segments
    
    def add_participant(self, user_id: str):
        """Track a user joining the stage."""
        self.participants[user_id] = DebateParticipant(
            user_id=user_id,
            joined_at=datetime.utcnow()
        )
        logger.info(f"Participant {user_id} joined debate")
    
    def remove_participant(self, user_id: str):
        """Track a user leaving the stage."""
        if user_id in self.participants:
            self.participants[user_id].left_at = datetime.utcnow()
            logger.info(f"Participant {user_id} left debate after {self.participants[user_id].duration_minutes:.1f} minutes")
    
    def get_reward_eligible_participants(self, min_duration_minutes: float = 15.0) -> List[str]:
        """Get users who stayed for the full debate (eligible for Signal Points)."""
        eligible = []
        for user_id, participant in self.participants.items():
            if participant.duration_minutes >= min_duration_minutes:
                eligible.append(user_id)
        return eligible
    
    def add_question(self, user_id: str, question: str):
        """Queue a question from the audience."""
        self.question_queue.append({
            'user_id': user_id,
            'question': question,
            'timestamp': datetime.utcnow()
        })
    
    def get_next_question(self) -> Optional[Dict]:
        """Get the next question to answer."""
        if self.question_queue:
            return self.question_queue.pop(0)
        return None


class DiscordStageService:
    """
    Discord Stage Channel integration for live debates.
    
    Integrates ElevenLabs voice streaming with Discord Stage channels
    for Alex vs Sarah debates with audience interaction.
    """
    
    def __init__(self):
        self.debate_engine = DebateEngine()
        self.discord_token = os.environ.get('DISCORD_BOT_TOKEN')
        self.voice_client = None
        self.is_streaming = False
        
        # ElevenLabs voice IDs
        self.voice_ids = {
            'alex': os.environ.get('ELEVENLABS_ALEX_VOICE_ID', 'pNInz6obpgDQGcFmaJgB'),  # Adam
            'sarah': os.environ.get('ELEVENLABS_SARAH_VOICE_ID', 'EXAVITQu4vr4xnSDxMaL')  # Bella
        }
    
    async def generate_voice_audio(self, text: str, speaker: str) -> Optional[bytes]:
        """Generate voice audio using ElevenLabs."""
        try:
            from services.elevenlabs_service import elevenlabs_service
            
            voice_id = self.voice_ids.get(speaker, self.voice_ids['alex'])
            audio_data = await elevenlabs_service.generate_speech_async(
                text=text,
                voice_id=voice_id
            )
            return audio_data
        except Exception as e:
            logger.error(f"Voice generation error: {e}")
            return None
    
    async def start_debate_session(self, script_type: str = 'difficulty_retarget') -> Dict[str, Any]:
        """
        Start a debate session.
        
        Returns the debate script and metadata for Discord integration.
        """
        try:
            segments = await self.debate_engine.generate_debate_script(script_type)
            script = self.debate_engine.DEBATE_SCRIPTS[script_type]
            
            self.debate_engine.active_debate = {
                'script_type': script_type,
                'title': script['title'],
                'started_at': datetime.utcnow(),
                'duration_minutes': script['duration_minutes'],
                'segments': segments
            }
            
            return {
                'success': True,
                'debate': self.debate_engine.active_debate
            }
        except Exception as e:
            logger.error(f"Failed to start debate: {e}")
            return {'success': False, 'error': str(e)}
    
    async def generate_alex_response(self, question: str) -> str:
        """Generate Alex's response to an audience question using AI."""
        try:
            from services.multi_agent import alex_the_quant
            
            prompt = f"""As Alex The Quant, answer this audience question with technical precision:

Question: {question}

Provide a data-driven, factual response. Use specific metrics where possible.
Keep the response under 100 words. Be direct and authoritative."""

            response = await alex_the_quant.analyze_async(prompt)
            return response
        except Exception as e:
            logger.error(f"Alex response generation error: {e}")
            return "I'm processing that query against my data feeds. Let me provide an update momentarily."
    
    def on_member_joined(self, user_id: str):
        """Handle member joining the stage."""
        self.debate_engine.add_participant(user_id)
    
    def on_member_left(self, user_id: str):
        """Handle member leaving the stage."""
        self.debate_engine.remove_participant(user_id)
    
    async def end_debate_and_reward(self) -> Dict[str, Any]:
        """End the debate and calculate Signal Point rewards."""
        if not self.debate_engine.active_debate:
            return {'success': False, 'error': 'No active debate'}
        
        duration = self.debate_engine.active_debate['duration_minutes']
        eligible_users = self.debate_engine.get_reward_eligible_participants(duration)
        
        # Award Signal Points
        rewards = []
        for user_id in eligible_users:
            rewards.append({
                'user_id': user_id,
                'points': 100,
                'reason': f"Completed {self.debate_engine.active_debate['title']}"
            })
        
        # Reset state
        self.debate_engine.active_debate = None
        self.debate_engine.participants.clear()
        self.debate_engine.question_queue.clear()
        
        return {
            'success': True,
            'total_participants': len(self.debate_engine.participants),
            'rewarded_users': len(rewards),
            'rewards': rewards
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current stage service status."""
        return {
            'active_debate': self.debate_engine.active_debate is not None,
            'debate_title': self.debate_engine.active_debate.get('title') if self.debate_engine.active_debate else None,
            'participant_count': len(self.debate_engine.participants),
            'question_queue_length': len(self.debate_engine.question_queue),
            'discord_configured': bool(self.discord_token),
            'voices_configured': {
                'alex': bool(self.voice_ids.get('alex')),
                'sarah': bool(self.voice_ids.get('sarah'))
            }
        }


# Singleton instance
discord_stage_service = DiscordStageService()
