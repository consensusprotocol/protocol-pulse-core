import os
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class PulseOperative:
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        self.initialized = False
        self.bot = None
        self.application = None
        
        if self.token:
            try:
                from telegram import Bot
                from telegram.ext import Application, CommandHandler, MessageHandler, filters
                self.Bot = Bot
                self.Application = Application
                self.CommandHandler = CommandHandler
                self.MessageHandler = MessageHandler
                self.filters = filters
                self.initialized = True
                logger.info("Telegram Pulse Operative initialized")
            except ImportError:
                logger.warning("python-telegram-bot not installed")
        else:
            logger.info("TELEGRAM_BOT_TOKEN not configured - Pulse Operative disabled")
    
    async def start_bot(self):
        if not self.initialized:
            return
        
        self.application = self.Application.builder().token(self.token).build()
        
        self.application.add_handler(self.CommandHandler("start", self.cmd_start))
        self.application.add_handler(self.CommandHandler("brief", self.cmd_brief))
        self.application.add_handler(self.CommandHandler("price", self.cmd_price))
        self.application.add_handler(self.CommandHandler("fees", self.cmd_fees))
        self.application.add_handler(self.CommandHandler("whale", self.cmd_whale))
        self.application.add_handler(self.CommandHandler("help", self.cmd_help))
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        
        logger.info("Pulse Operative bot started and polling")
    
    def run_bot_sync(self):
        if not self.initialized:
            logger.warning("Telegram bot not initialized - skipping")
            return
        
        try:
            self.application = self.Application.builder().token(self.token).build()
            
            self.application.add_handler(self.CommandHandler("start", self.cmd_start))
            self.application.add_handler(self.CommandHandler("brief", self.cmd_brief))
            self.application.add_handler(self.CommandHandler("price", self.cmd_price))
            self.application.add_handler(self.CommandHandler("fees", self.cmd_fees))
            self.application.add_handler(self.CommandHandler("whale", self.cmd_whale))
            self.application.add_handler(self.CommandHandler("help", self.cmd_help))
            
            self.application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Telegram bot run error: {e}")
    
    async def stop_bot(self):
        if self.application:
            try:
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.error(f"Bot stop error: {e}")
    
    async def cmd_start(self, update, context):
        welcome = """
📡 *PROTOCOL PULSE: INTELLIGENCE FEED INITIALIZED*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Welcome to the Command Center. You are now connected to the only 24/7 autonomous intelligence loop in freedom tech.

*What to Expect:*

🔹 *Alex-Verified Briefs:* Every piece of news here has cleared the Cronkite Accuracy Gate. No slop, no hallucination—just the ground truth.

🔹 *Whale Radar:* Real-time pings for every move >1,000 BTC. If the money moves, you know first.

🔹 *Sarah's Strategy:* High-level macro takeaways delivered daily to help you navigate the 2026 volatility.

*Commands:*
/brief - AI intelligence briefing
/price - Current BTC metrics
/fees - Network fee analysis  
/whale - Large transactions
/help - Command reference

*Take Action:*
🔗 Initialize Your Identity at protocolpulse.io to earn your first +100 Signal Points
💎 Earn Sovereign Credits for Partner Drops

_Stay Sharp. Stay Sovereign._ ⚡
        """
        await update.message.reply_text(welcome, parse_mode='Markdown')
    
    async def cmd_help(self, update, context):
        help_text = """
*PULSE OPERATIVE COMMANDS*
━━━━━━━━━━━━━━━━━━━━━

/brief - Generate AI intelligence briefing
/price - BTC price, 24h change, market cap
/fees - Current mempool fees
/whale - Recent 500+ BTC transactions
/start - Welcome message

_All data sourced from live network APIs._
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cmd_price(self, update, context):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://api.coingecko.com/api/v3/simple/price',
                    params={'ids': 'bitcoin', 'vs_currencies': 'usd', 'include_24hr_change': 'true', 'include_market_cap': 'true'}
                )
                data = response.json()
                
                price = data['bitcoin']['usd']
                change = data['bitcoin']['usd_24h_change']
                mcap = data['bitcoin']['usd_market_cap']
                
                emoji = "🟢" if change > 0 else "🔴"
                
                message = f"""
🟠 *BITCOIN PRICE UPDATE*
━━━━━━━━━━━━━━━━━━━━━

💰 *Price:* ${price:,.0f}
{emoji} *24h:* {change:+.2f}%
📊 *Market Cap:* ${mcap/1e12:.2f}T

_Updated: {datetime.utcnow().strftime('%H:%M UTC')}_
                """
                await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Price command error: {e}")
            await update.message.reply_text("⚠️ Unable to fetch price data. Try again.")
    
    async def cmd_fees(self, update, context):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get('https://mempool.space/api/v1/fees/recommended')
                fees = response.json()
                
                mempool_resp = await client.get('https://mempool.space/api/mempool')
                mempool = mempool_resp.json()
                
                pending = mempool.get('count', 0)
                size_mb = mempool.get('vsize', 0) / 1000000
                
                message = f"""
⛽ *NETWORK FEE ANALYSIS*
━━━━━━━━━━━━━━━━━━━━━

🚀 *High Priority:* {fees['fastestFee']} sat/vB
⚡ *Medium:* {fees['halfHourFee']} sat/vB  
🐢 *Economy:* {fees['economyFee']} sat/vB

📦 *Mempool:* {pending:,} txs ({size_mb:.1f} MB)

{"🟢 LOW FEES - Good time to transact!" if fees['fastestFee'] < 10 else "🟡 Moderate fees" if fees['fastestFee'] < 30 else "🔴 High fees - Consider waiting"}

_Source: mempool.space_
                """
                await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Fees command error: {e}")
            await update.message.reply_text("⚠️ Unable to fetch fee data. Try again.")
    
    async def cmd_whale(self, update, context):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                blocks_resp = await client.get('https://mempool.space/api/blocks')
                blocks = blocks_resp.json()
                
                whales = []
                for block in blocks[:2]:
                    tx_resp = await client.get(f"https://mempool.space/api/block/{block['id']}/txs")
                    txs = tx_resp.json()
                    
                    for tx in txs:
                        total = sum(out.get('value', 0) for out in tx.get('vout', []))
                        btc = total / 100000000
                        if btc >= 500:
                            whales.append({'txid': tx['txid'][:16], 'btc': btc})
                
                if whales:
                    whale_lines = "\n".join([f"🐋 {w['btc']:,.0f} BTC - `{w['txid']}...`" for w in whales[:5]])
                    message = f"""
🌊 *WHALE WATCHER*
━━━━━━━━━━━━━━━━━━━━━

*Recent Large Transactions (500+ BTC):*

{whale_lines}

_View full feed: protocolpulse.com/whale-watcher_
                    """
                else:
                    message = "🌊 No whale activity detected in recent blocks."
                
                await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Whale command error: {e}")
            await update.message.reply_text("⚠️ Unable to fetch whale data. Try again.")
    
    async def cmd_brief(self, update, context):
        await update.message.reply_text("🔄 Generating intelligence briefing...")
        
        try:
            from pp_services.ai_service import ai_service
            
            prompt = """Generate a concise 60-second Bitcoin intelligence briefing for today. Include:
1. Current network status (use real mempool data if available)
2. One key development from the past 24 hours
3. One transactor insight or recommendation

Format for Telegram with emojis. Keep it under 200 words. Be factual and avoid hype."""
            
            brief = ai_service.generate_content(prompt, max_tokens=300)
            
            message = f"""
🔴 *DAILY INTELLIGENCE BRIEFING*
━━━━━━━━━━━━━━━━━━━━━
{datetime.utcnow().strftime('%B %d, %Y')}

{brief}

_Generated by Protocol Pulse AI_
            """
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Brief generation error: {e}")
            await update.message.reply_text("⚠️ Unable to generate briefing. Try /price or /fees instead.")
    
    async def send_message(self, text: str, chat_id: str = None, parse_mode: str = 'Markdown'):
        if not self.initialized:
            return {'success': False, 'error': 'Bot not initialized'}
        
        try:
            bot = self.Bot(self.token)
            target_chat = chat_id or self.chat_id
            if not target_chat:
                return {'success': False, 'error': 'No chat_id specified'}
            
            await bot.send_message(chat_id=target_chat, text=text, parse_mode=parse_mode)
            return {'success': True}
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def send_audio(self, audio_path: str, caption: str = None, chat_id: str = None):
        if not self.initialized:
            return {'success': False, 'error': 'Bot not initialized'}
        
        try:
            bot = self.Bot(self.token)
            target_chat = chat_id or self.chat_id
            
            with open(audio_path, 'rb') as audio_file:
                await bot.send_audio(
                    chat_id=target_chat,
                    audio=audio_file,
                    caption=caption,
                    parse_mode='Markdown'
                )
            return {'success': True}
        except Exception as e:
            logger.error(f"Send audio error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def post_clip(self, video_path: str, caption: str, chat_id: str = None):
        if not self.initialized:
            return {'success': False, 'error': 'Bot not initialized'}
        
        try:
            bot = self.Bot(self.token)
            target_chat = chat_id or self.chat_id
            
            with open(video_path, 'rb') as video_file:
                await bot.send_video(
                    chat_id=target_chat,
                    video=video_file,
                    caption=caption,
                    parse_mode='Markdown'
                )
            return {'success': True}
        except Exception as e:
            logger.error(f"Post clip error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        return {
            'initialized': self.initialized,
            'token_configured': bool(self.token),
            'channel_configured': bool(self.chat_id),
            'bot_running': self.application is not None
        }

pulse_operative = PulseOperative()
