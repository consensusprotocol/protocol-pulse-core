"""
SENTINEL — Protocol Pulse Intelligence Daemon
==============================================
Always-running asyncio daemon that ingests live Bitcoin network data via
mempool.space WebSocket + REST, runs PCAF v0 rule-based anomaly detection,
and dispatches tiered alerts (CRITICAL/WATCH/NOTE) via Telegram + ElevenLabs TTS.

Started as a background daemon thread at Flask boot.
Flask reads state from /tmp/sentinel_state.json (written every 5s).
"""

import asyncio
import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import aiohttp
import websockets

from services.config_loader import convergence_config
from services.convergence_engine import ConvergenceEngine

logger = logging.getLogger("sentinel")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[SENTINEL %(levelname)s] %(asctime)s — %(message)s"))
    logger.addHandler(_h)

# ── Paths ────────────────────────────────────────────────────────────────────
STATE_FILE = "/tmp/sentinel_state.json"
ALERTS_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sentinel_alerts.db")

# ── ENV ──────────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALERT_CHAT_ID = os.environ.get("TELEGRAM_ALERT_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", ""))
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_MARK = os.environ.get("ELEVENLABS_VOICE_MARK", "TxGEqnHWrfWFTfGW9XjX")
DRY_RUN = os.environ.get("SENTINEL_DRY_RUN", "") == "1"

# ── mempool.space endpoints ─────────────────────────────────────────────────
WS_URL = "wss://mempool.space/api/v1/ws"
API_BASE = "https://mempool.space/api"

# ── Alert cooldowns (seconds) ───────────────────────────────────────────────
CRITICAL_COOLDOWN = 4 * 3600  # 4 hours
WATCH_COOLDOWN = 2 * 3600     # 2 hours
NOTE_COOLDOWN = 1800           # 30 min


# ═══════════════════════════════════════════════════════════════════════════
#  STATE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SentinelState:
    mempool: dict = field(default_factory=lambda: {
        "count": 0,
        "vsize": 0,
        "total_fee": 0,
        "fee_histogram": [],
        "whale_txs": [],
        "rbf_count": 0,
        "updated_at": 0.0,
    })
    network: dict = field(default_factory=lambda: {
        "block_height": 0,
        "hashrate_3d": 0.0,
        "difficulty": 0.0,
        "next_difficulty_adj_pct": 0.0,
        "orphan_count_6h": 0,
        "avg_block_time_10": 600.0,
        "recent_blocks": [],
        "updated_at": 0.0,
    })
    lightning: dict = field(default_factory=lambda: {
        "capacity_btc": 0.0,
        "channel_count": 0,
        "node_count": 0,
        "updated_at": 0.0,
    })
    pcaf_v0: dict = field(default_factory=lambda: {
        "anomaly_score": 0,
        "active_rules": [],
        "top_signal": "",
        "confidence_pct": 0,
        "updated_at": 0.0,
    })
    alerts: dict = field(default_factory=lambda: {
        "active": [],
        "last_critical_at": 0.0,
        "last_watch_at": 0.0,
    })
    convergence: dict = field(default_factory=lambda: {
        "state": "IDLE",
        "last_evaluated": 0.0,
        "signals": [],
        "contradiction": False,
        "contradiction_detail": "",
        "pattern_results": {},
        "schema_version": 1,
    })

    def to_dict(self):
        return {
            "mempool": dict(self.mempool),
            "network": {k: v for k, v in self.network.items() if k != "recent_blocks"},
            "lightning": dict(self.lightning),
            "pcaf_v0": dict(self.pcaf_v0),
            "alerts": {
                "active": list(self.alerts["active"][-50:]),
                "last_critical_at": self.alerts["last_critical_at"],
                "last_watch_at": self.alerts["last_watch_at"],
            },
            "convergence": dict(self.convergence),
        }


# ═══════════════════════════════════════════════════════════════════════════
#  ALERT DB
# ═══════════════════════════════════════════════════════════════════════════

def _init_alerts_db():
    os.makedirs(os.path.dirname(ALERTS_DB), exist_ok=True)
    conn = sqlite3.connect(ALERTS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tier TEXT NOT NULL,
            rule TEXT NOT NULL,
            message TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            data_json TEXT,
            created_at REAL NOT NULL,
            ack_at REAL
        )
    """)
    conn.commit()
    conn.close()


def _save_alert(tier: str, rule: str, message: str, score: int, data: dict = None):
    try:
        conn = sqlite3.connect(ALERTS_DB)
        conn.execute(
            "INSERT INTO alerts (tier, rule, message, score, data_json, created_at) VALUES (?,?,?,?,?,?)",
            (tier, rule, message, score, json.dumps(data or {}), time.time()),
        )
        # Keep last 500
        conn.execute("DELETE FROM alerts WHERE id NOT IN (SELECT id FROM alerts ORDER BY id DESC LIMIT 500)")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Failed to save alert: %s", e)


def get_alerts(limit=50, offset=0):
    try:
        conn = sqlite3.connect(ALERTS_DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def ack_alert(alert_id: int):
    try:
        conn = sqlite3.connect(ALERTS_DB)
        conn.execute("UPDATE alerts SET ack_at = ? WHERE id = ?", (time.time(), alert_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
#  ALERT DISPATCHER
# ═══════════════════════════════════════════════════════════════════════════

class AlertDispatcher:
    """Sends alerts via Telegram + ElevenLabs TTS voice for CRITICAL tier."""

    def _send_telegram(self, text: str) -> bool:
        if DRY_RUN:
            logger.info("[DRY RUN] Telegram: %s", text[:100])
            return True
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ALERT_CHAT_ID:
            logger.warning("Telegram not configured — skipping")
            return False
        try:
            import requests
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": TELEGRAM_ALERT_CHAT_ID,
                "text": f"🚨 SENTINEL ALERT\n\n{text}",
                "parse_mode": "HTML",
            }, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error("Telegram send failed: %s", e)
            return False

    def _send_voice(self, text: str) -> bool:
        if DRY_RUN:
            logger.info("[DRY RUN] Voice: %s", text[:100])
            return True
        if not ELEVENLABS_API_KEY or not TELEGRAM_BOT_TOKEN:
            logger.warning("ElevenLabs or Telegram not configured — skipping voice")
            return False
        try:
            import requests
            # Synthesize with ElevenLabs
            tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_MARK}"
            tts_resp = requests.post(tts_url, json={
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {"stability": 0.7, "similarity_boost": 0.8},
            }, headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            }, timeout=30)
            if tts_resp.status_code != 200:
                logger.error("ElevenLabs TTS failed: %d %s", tts_resp.status_code, tts_resp.text[:200])
                return False
            mp3_path = f"/tmp/alert_{int(time.time())}.mp3"
            with open(mp3_path, "wb") as f:
                f.write(tts_resp.content)
            # Send voice to Telegram
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
            with open(mp3_path, "rb") as f:
                resp = requests.post(tg_url, data={
                    "chat_id": TELEGRAM_ALERT_CHAT_ID,
                }, files={"voice": ("alert.mp3", f, "audio/mpeg")}, timeout=30)
            os.unlink(mp3_path)
            return resp.status_code == 200
        except Exception as e:
            logger.error("Voice alert failed: %s", e)
            return False

    def send_critical(self, text: str) -> dict:
        tg = self._send_telegram(text)
        voice = self._send_voice(text)
        return {"telegram": tg, "voice": voice, "tier": "CRITICAL"}

    def send_watch(self, text: str) -> dict:
        tg = self._send_telegram(text)
        return {"telegram": tg, "tier": "WATCH"}

    def send_note(self, text: str) -> dict:
        # Notes are terminal-only, no external delivery
        return {"tier": "NOTE"}


# ═══════════════════════════════════════════════════════════════════════════
#  SENTINEL DAEMON
# ═══════════════════════════════════════════════════════════════════════════

class SentinelDaemon:
    """Async daemon: WebSocket + REST ingestion, PCAF v0, alert dispatch."""

    def __init__(self):
        self.state = SentinelState()
        self.dispatcher = AlertDispatcher()
        self._lock = threading.Lock()
        self._cooldowns: dict = {}  # rule -> last_alert_time
        self._running = False
        self._hashrate_24h_ago: Optional[float] = None
        self._hashrate_24h_ago_ts: float = 0.0
        self._convergence_engine: Optional[ConvergenceEngine] = None
        _init_alerts_db()

    # ── State access (thread-safe for Flask) ───────────────────────────────
    def get_state_dict(self) -> dict:
        with self._lock:
            return self.state.to_dict()

    def _write_state_file(self):
        try:
            data = self.get_state_dict()
            tmp = STATE_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(data, f)
            os.replace(tmp, STATE_FILE)
        except Exception as e:
            logger.error("State file write failed: %s", e)

    # ── REST Polling ───────────────────────────────────────────────────────
    async def _poll_rest(self, session: aiohttp.ClientSession):
        """Poll REST endpoints for data not available via WebSocket."""
        try:
            # Mempool stats
            async with session.get(f"{API_BASE}/mempool", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    with self._lock:
                        self.state.mempool["count"] = data.get("count", 0)
                        self.state.mempool["vsize"] = data.get("vsize", 0)
                        self.state.mempool["total_fee"] = data.get("total_fee", 0)
                        self.state.mempool["updated_at"] = time.time()
        except Exception as e:
            logger.warning("Mempool REST poll failed: %s", e)

        try:
            # Fee histogram (mempool-blocks)
            async with session.get(f"{API_BASE}/v1/fees/mempool-blocks", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    blocks = await resp.json()
                    histogram = self._build_fee_histogram(blocks)
                    with self._lock:
                        self.state.mempool["fee_histogram"] = histogram
        except Exception as e:
            logger.warning("Fee histogram poll failed: %s", e)

        try:
            # Hashrate
            async with session.get(f"{API_BASE}/v1/mining/hashrate/3d", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    hr_list = data.get("hashrates", [])
                    if hr_list:
                        latest = hr_list[-1].get("avgHashrate", 0)
                        eh_s = latest / 1e18
                        with self._lock:
                            # Track 24h-ago hashrate for cliff detection
                            if self._hashrate_24h_ago is None or time.time() - self._hashrate_24h_ago_ts > 3600:
                                if len(hr_list) > 1:
                                    self._hashrate_24h_ago = hr_list[0].get("avgHashrate", 0) / 1e18
                                    self._hashrate_24h_ago_ts = time.time()
                            self.state.network["hashrate_3d"] = round(eh_s, 2)
                            self.state.network["updated_at"] = time.time()
        except Exception as e:
            logger.warning("Hashrate poll failed: %s", e)

        try:
            # Difficulty
            async with session.get(f"{API_BASE}/v1/difficulty-adjustment", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    with self._lock:
                        self.state.network["difficulty"] = data.get("difficultyChange", 0.0)
                        self.state.network["next_difficulty_adj_pct"] = round(data.get("progressPercent", 0.0), 2)
        except Exception as e:
            logger.warning("Difficulty poll failed: %s", e)

        try:
            # Recent blocks (for orphan detection + pool concentration)
            async with session.get(f"{API_BASE}/v1/blocks", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    blocks = await resp.json()
                    if blocks and len(blocks) >= 10:
                        recent_10 = blocks[:10]
                        with self._lock:
                            self.state.network["block_height"] = recent_10[0].get("height", 0)
                            self.state.network["recent_blocks"] = [
                                {"pool": b.get("extras", {}).get("pool", {}).get("name", "Unknown"),
                                 "height": b.get("height", 0),
                                 "timestamp": b.get("timestamp", 0)}
                                for b in recent_10
                            ]
                            # Avg block time from last 10
                            times = [b.get("timestamp", 0) for b in recent_10]
                            if len(times) >= 2:
                                diffs = [times[i] - times[i + 1] for i in range(len(times) - 1)]
                                self.state.network["avg_block_time_10"] = round(sum(diffs) / len(diffs), 1)
                            self.state.network["updated_at"] = time.time()
        except Exception as e:
            logger.warning("Blocks poll failed: %s", e)

        try:
            # Lightning
            async with session.get(f"{API_BASE}/v1/lightning/statistics/latest", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    cap_sat = data.get("latest", {}).get("total_capacity", 0)
                    with self._lock:
                        self.state.lightning["capacity_btc"] = round(cap_sat / 1e8, 2)
                        self.state.lightning["channel_count"] = data.get("latest", {}).get("channel_count", 0)
                        self.state.lightning["node_count"] = data.get("latest", {}).get("node_count", 0)
                        self.state.lightning["updated_at"] = time.time()
        except Exception as e:
            logger.warning("Lightning poll failed: %s", e)

        try:
            # Whale tx detection (recent mempool txs)
            async with session.get(f"{API_BASE}/mempool/recent", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    txs = await resp.json()
                    whales = []
                    for tx in txs:
                        value_sat = tx.get("value", 0)
                        if value_sat > 5_000_000_000:  # > 50 BTC in sats
                            whales.append({
                                "txid": tx.get("txid", ""),
                                "value_btc": round(value_sat / 1e8, 2),
                                "timestamp": time.time(),
                            })
                    if whales:
                        with self._lock:
                            existing = self.state.mempool["whale_txs"]
                            existing_ids = {w["txid"] for w in existing}
                            for w in whales:
                                if w["txid"] not in existing_ids:
                                    existing.insert(0, w)
                                    # Whale NOTE alert for >100 BTC
                                    if w["value_btc"] > 100:
                                        self._fire_alert(
                                            "NOTE", "WHALE_TX",
                                            f"Whale transaction detected: {w['value_btc']} BTC unconfirmed {w['txid'][:8]}...",
                                            10, w,
                                        )
                            self.state.mempool["whale_txs"] = existing[:20]
        except Exception as e:
            logger.warning("Whale tx poll failed: %s", e)

    def _build_fee_histogram(self, mempool_blocks: list) -> list:
        """Build 10-band fee histogram from mempool-blocks response."""
        bands = [
            (1, 5), (6, 10), (11, 20), (21, 30), (31, 50),
            (51, 75), (76, 100), (101, 150), (151, 300), (301, 9999),
        ]
        result = []
        for min_f, max_f in bands:
            band = {"min_fee": min_f, "max_fee": max_f, "vsize": 0, "count": 0}
            result.append(band)

        for block in mempool_blocks:
            fee_range = block.get("feeRange", [])
            block_vsize = block.get("blockVSize", 0)
            if fee_range and len(fee_range) >= 2:
                med_fee = fee_range[len(fee_range) // 2]
                for band in result:
                    if band["min_fee"] <= med_fee <= band["max_fee"]:
                        band["vsize"] += block_vsize
                        band["count"] += block.get("nTx", 0)
                        break
        return result

    # ── WebSocket ingestion ────────────────────────────────────────────────
    async def _ws_loop(self):
        """Persistent WebSocket to mempool.space for live data."""
        backoff = 1
        while self._running:
            try:
                async with websockets.connect(WS_URL, ping_interval=30, ping_timeout=10) as ws:
                    logger.info("WebSocket connected to mempool.space")
                    backoff = 1
                    await ws.send(json.dumps({
                        "action": "want",
                        "data": ["blocks", "mempool-blocks", "live-2h-chart", "stats"],
                    }))
                    async for raw in ws:
                        if not self._running:
                            break
                        try:
                            data = json.loads(raw)
                            self._process_ws_message(data)
                        except json.JSONDecodeError:
                            pass
            except Exception as e:
                logger.warning("WebSocket error: %s — reconnecting in %ds", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    def _process_ws_message(self, data: dict):
        """Handle a WebSocket message from mempool.space."""
        with self._lock:
            if "mempoolInfo" in data:
                info = data["mempoolInfo"]
                self.state.mempool["count"] = info.get("size", self.state.mempool["count"])
                self.state.mempool["vsize"] = info.get("vsize", self.state.mempool["vsize"])
                self.state.mempool["total_fee"] = info.get("total_fee", self.state.mempool["total_fee"])
                self.state.mempool["updated_at"] = time.time()
            if "block" in data:
                block = data["block"]
                self.state.network["block_height"] = block.get("height", self.state.network["block_height"])
                self.state.network["updated_at"] = time.time()
            if "blocks" in data:
                for block in data["blocks"]:
                    self.state.network["block_height"] = max(
                        block.get("height", 0), self.state.network["block_height"]
                    )
                self.state.network["updated_at"] = time.time()

    # ── PCAF v0 Rule Engine ────────────────────────────────────────────────
    def run_pcaf_v0(self, state: Optional[SentinelState] = None) -> tuple:
        """Run all PCAF v0 rules. Returns (score, list_of_signals)."""
        if state is None:
            state = self.state
        score = 0
        signals = []
        force_critical = False

        # Rule 1: Hashrate Concentration
        blocks = state.network.get("recent_blocks", [])
        if len(blocks) >= 10:
            pool_counts = {}
            for b in blocks[:10]:
                pool = b.get("pool", "Unknown")
                pool_counts[pool] = pool_counts.get(pool, 0) + 1
            for pool, count in pool_counts.items():
                pct = count * 10  # out of 10 blocks = % * 10
                if pct > 40:
                    score += 30
                    signals.append(f"Hashrate concentration: {pool} at {pct}% of last 10 blocks")
                    break

        # Rule 2: Mempool Congestion Precursor
        mem_count = state.mempool.get("count", 0)
        fee_hist = state.mempool.get("fee_histogram", [])
        next_block_fee = 0
        if fee_hist:
            # Highest band with transactions = next block fee
            for band in reversed(fee_hist):
                if band.get("count", 0) > 0:
                    next_block_fee = band.get("min_fee", 0)
                    break
        rbf_count = state.mempool.get("rbf_count", 0)
        if mem_count > 180_000 and next_block_fee > 80 and rbf_count > 45:
            score += 25
            signals.append(f"{mem_count} unconfirmed txs, next-block fee {next_block_fee} sat/vB — congestion imminent")

        # Rule 3: Orphan Rate
        orphan_count = state.network.get("orphan_count_6h", 0)
        if orphan_count > 2:
            score += 20
            signals.append(f"{orphan_count} orphan blocks detected in 6-hour window")

        # Rule 4: Block Time Anomaly
        avg_bt = state.network.get("avg_block_time_10", 600)
        if avg_bt > 900:
            score += 15
            signals.append(f"Block timing anomaly: avg {avg_bt}s/block over last 10 blocks")
        elif avg_bt < 300:
            score += 10
            signals.append(f"Block timing anomaly: avg {avg_bt}s/block over last 10 blocks (fast)")

        # Rule 5: Hashrate Cliff
        if self._hashrate_24h_ago and self._hashrate_24h_ago > 0:
            current_hr = state.network.get("hashrate_3d", 0)
            if current_hr > 0:
                drop_pct = ((self._hashrate_24h_ago - current_hr) / self._hashrate_24h_ago) * 100
                if drop_pct > 25:
                    score += 35
                    force_critical = True
                    signals.append(f"Hashrate cliff: {drop_pct:.1f}% drop vs 24h prior")
                elif drop_pct > 15:
                    score += 35
                    signals.append(f"Hashrate cliff: {drop_pct:.1f}% drop vs 24h prior")

        score = min(score, 100)
        return score, signals, force_critical if 'force_critical' in dir() else (score, signals, force_critical)

    def _update_pcaf(self):
        """Run PCAF and update state + dispatch alerts."""
        score, signals, force_critical = self.run_pcaf_v0()
        with self._lock:
            self.state.pcaf_v0["anomaly_score"] = score
            self.state.pcaf_v0["active_rules"] = signals
            self.state.pcaf_v0["top_signal"] = signals[0] if signals else ""
            self.state.pcaf_v0["confidence_pct"] = min(score + 10, 100) if signals else 0
            self.state.pcaf_v0["updated_at"] = time.time()

        # Determine tier and fire alert
        if force_critical or score >= 85:
            tier = "CRITICAL"
        elif score >= 55:
            tier = "WATCH"
        elif score >= 30:
            tier = "NOTE"
        else:
            return

        for signal in signals:
            self._fire_alert(tier, signal.split(":")[0].strip(), signal, score)

    def _fire_alert(self, tier: str, rule: str, message: str, score: int, data: dict = None):
        """Dispatch alert with cooldown check."""
        now = time.time()
        cooldown_key = f"{tier}:{rule}"

        # Cooldown check
        cooldown = {
            "CRITICAL": CRITICAL_COOLDOWN,
            "WATCH": WATCH_COOLDOWN,
            "NOTE": NOTE_COOLDOWN,
        }.get(tier, NOTE_COOLDOWN)

        last_sent = self._cooldowns.get(cooldown_key, 0)
        if now - last_sent < cooldown:
            return

        self._cooldowns[cooldown_key] = now
        _save_alert(tier, rule, message, score, data)

        # Add to in-memory state
        alert_record = {
            "tier": tier,
            "rule": rule,
            "message": message,
            "score": score,
            "created_at": now,
        }
        with self._lock:
            self.state.alerts["active"].insert(0, alert_record)
            self.state.alerts["active"] = self.state.alerts["active"][:50]
            if tier == "CRITICAL":
                self.state.alerts["last_critical_at"] = now
            elif tier == "WATCH":
                self.state.alerts["last_watch_at"] = now

        # External delivery
        if tier == "CRITICAL":
            self.dispatcher.send_critical(message)
        elif tier == "WATCH":
            self.dispatcher.send_watch(message)
        # NOTE = terminal only

        logger.info("ALERT [%s] %s — score %d", tier, message, score)

    # ── Convergence Engine ───────────────────────────────────────────────
    async def _update_convergence(self, session: aiohttp.ClientSession):
        """Run convergence evaluation cycle and update state."""
        try:
            if self._convergence_engine is None:
                self._convergence_engine = ConvergenceEngine(session, convergence_config)
            result = await self._convergence_engine.run_evaluation_cycle()
            with self._lock:
                self.state.convergence = result

            # Fire alert if convergence state escalates to ALERT or CRITICAL
            conv_state = result.get("state", "IDLE")
            if conv_state == "CRITICAL":
                self._fire_alert(
                    "CRITICAL", "CONVERGENCE",
                    f"Convergence CRITICAL — {len(result.get('signals', []))} signals aligned",
                    90, {"convergence": result},
                )
            elif conv_state == "ALERT":
                self._fire_alert(
                    "WATCH", "CONVERGENCE",
                    f"Convergence ALERT — {len(result.get('signals', []))} signals aligned",
                    60, {"convergence": result},
                )
        except Exception as e:
            logger.error("Convergence evaluation failed: %s", e)

    # ── Main Loop ──────────────────────────────────────────────────────────
    async def run(self):
        """Main async entry — run WebSocket + REST polling + PCAF + Convergence concurrently."""
        self._running = True
        logger.info("Sentinel daemon starting...")

        async with aiohttp.ClientSession() as session:
            ws_task = asyncio.create_task(self._ws_loop())

            poll_counter = 0
            while self._running:
                await asyncio.sleep(5)
                poll_counter += 1

                # REST poll every 30s
                if poll_counter % 6 == 0:
                    await self._poll_rest(session)

                # PCAF every 60s
                if poll_counter % 12 == 0:
                    self._update_pcaf()

                # Convergence every 60s (same cadence as PCAF)
                if poll_counter % 12 == 0:
                    await self._update_convergence(session)

                # Write state every 5s
                self._write_state_file()

            ws_task.cancel()

    async def run_once_for_test(self):
        """One-shot: poll REST, run PCAF, write state. For testing."""
        self._running = True
        async with aiohttp.ClientSession() as session:
            await self._poll_rest(session)
        self._update_pcaf()
        self._write_state_file()
        self._running = False


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC API (Flask-safe)
# ═══════════════════════════════════════════════════════════════════════════

_daemon: Optional[SentinelDaemon] = None
_thread: Optional[threading.Thread] = None


def get_state() -> dict:
    """Read state from file — Flask-safe, no asyncio dependency."""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return SentinelState().to_dict()


def start_sentinel():
    """Start the Sentinel daemon in a background thread. No-op if already running."""
    global _daemon, _thread
    if _thread and _thread.is_alive():
        logger.info("Sentinel already running")
        return

    _daemon = SentinelDaemon()

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_daemon.run())
        except Exception as e:
            logger.error("Sentinel daemon crashed: %s", e)
        finally:
            loop.close()

    _thread = threading.Thread(target=_run, daemon=True, name="sentinel-daemon")
    _thread.start()
    logger.info("Sentinel daemon thread started")
