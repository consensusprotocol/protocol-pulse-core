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

import importlib.util as _ilu_svc
import sys as _sys_svc
from pathlib import Path as _Path_svc
_svc_dir = _Path_svc(__file__).resolve().parent

def _load_svc(mod_name, filename):
    spec = _ilu_svc.spec_from_file_location(mod_name, str(_svc_dir / filename))
    mod = _ilu_svc.module_from_spec(spec)
    _sys_svc.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod

_config_loader_mod = _load_svc('_sentinel_config_loader', 'config_loader.py')
convergence_config = _config_loader_mod.convergence_config
_convergence_engine_mod = _load_svc('_sentinel_convergence_engine', 'convergence_engine.py')
ConvergenceEngine = _convergence_engine_mod.ConvergenceEngine

# Phase 2 engines
_sentiment_mod = _load_svc('_sentinel_sentiment_pulse', 'sentiment_pulse_engine.py')
SentimentPulseEngine = _sentiment_mod.SentimentPulseEngine
_sovereign_mod = _load_svc('_sentinel_sovereign_engine', 'sovereign_engine.py')
SovereignEngine = _sovereign_mod.SovereignEngine
_etf_mod = _load_svc('_sentinel_etf_monitor', 'etf_monitor.py')
ETFMonitor = _etf_mod.ETFMonitor

# Phase 2 F6: Dark Pool OTC
_dark_pool_mod = _load_svc('_sentinel_dark_pool', 'dark_pool_engine.py')
DarkPoolEngine = _dark_pool_mod.DarkPoolEngine

# Phase 2 F7: Miner Stress
_miner_stress_mod = _load_svc('_sentinel_miner_stress', 'miner_stress_engine.py')
MinerStressEngine = _miner_stress_mod.MinerStressEngine

# Phase 3 F1: Whale Coordination
_whale_coord_mod = _load_svc('_sentinel_whale_coord', 'whale_coordination_engine.py')
WhaleCoordinationEngine = _whale_coord_mod.WhaleCoordinationEngine

# Phase 3 F2: Regulatory Intelligence
_reg_intel_mod = _load_svc('_sentinel_reg_intel', 'regulatory_intel_engine.py')
RegulatoryIntelEngine = _reg_intel_mod.RegulatoryIntelEngine

# Phase 3 F3: Privacy Tech Pulse
_privacy_tech_mod = _load_svc('_sentinel_privacy_tech', 'privacy_tech_engine.py')
PrivacyTechEngine = _privacy_tech_mod.PrivacyTechEngine

# ML Phase: PCAF v1 GNN Engine + Data Collector
_pcaf_v1_engine_mod = _load_svc('_sentinel_pcaf_v1_engine', 'pcaf_v1_engine.py')
PCAFv1Engine = _pcaf_v1_engine_mod.PCAFv1Engine
_pcaf_collector_mod = _load_svc('_sentinel_pcaf_collector', 'pcaf_data_collector.py')
DataCollector = _pcaf_collector_mod.DataCollector

# ML Phase: TPA Scenario Engine
_tpa_engine_mod = _load_svc('_sentinel_tpa_engine', 'tpa_engine.py')
TPAEngine = _tpa_engine_mod.TPAEngine


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
    sentiment: dict = field(default_factory=lambda: {
        "score": 0.0, "score_30m_ago": 0.0, "trend": "stable",
        "source_breakdown": {"x": 0.0, "nostr": 0.0, "reddit": 0.0},
        "volume_24h": 0, "top_entities": [], "tier1_signal": False,
        "updated_at": 0.0,
    })
    sovereign: dict = field(default_factory=lambda: {
        "top_alerts": [], "jurisdiction_summary": {"friendly": 0, "neutral": 0, "hostile": 0},
        "custody_health": {}, "capital_flight_signal": False, "updated_at": 0.0,
    })
    etf: dict = field(default_factory=lambda: {
        "inflow_6h_btc": 0, "outflow_6h_btc": 0, "net_6h_btc": 0, "net_6h_usd": 0,
        "net_6h_direction": "neutral", "deribit_funding_rate": 0.0,
        "wallets_monitored": 0, "is_proxy": True, "updated_at": 0.0,
    })
    network_graph: dict = field(default_factory=lambda: {
        "nodes": [], "edges": [], "updated_at": 0.0,
    })
    dark_pool: dict = field(default_factory=lambda: {
        "signal": "CLEAR", "volume_4h_btc": 0.0, "tx_count_4h": 0,
        "top_destinations": [], "exchange_pct": 0.0, "updated_at": 0.0,
    })
    miner_health: dict = field(default_factory=lambda: {
        "score": 100, "label": "HEALTHY", "components": {},
        "is_90d_low": False, "updated_at": 0.0,
    })
    whale_coordination: dict = field(default_factory=lambda: {
        "signal": "CLEAR", "tx_count_90min": 0, "taint_linked": False,
        "tier1_social_active": False, "total_btc_90min": 0.0, "updated_at": 0.0,
    })
    regulatory: dict = field(default_factory=lambda: {
        "recent_alerts": [], "jurisdiction_updates": [],
        "threat_level": "LOW", "last_hostile_event": None,
        "last_friendly_event": None, "updated_at": 0.0,
    })
    privacy_tech: dict = field(default_factory=lambda: {
        "coinjoin_signal": "NORMAL", "coinjoin_7d_btc": 0.0,
        "taproot_tx_pct": 0.0, "taproot_utxo_pct": 0.0,
        "tor_node_pct": 0.0, "nostr_24h_events": 0,
        "sp_7d_count": 0, "sovereignty_index": 50.0, "updated_at": 0.0,
    })
    defi_btc: dict = field(default_factory=lambda: {
        "wbtc_supply_btc": 0.0, "cbbtc_supply_btc": 0.0,
        "total_btc_in_defi": 0.0, "delta_24h_btc": 0.0,
        "signal": "NEUTRAL", "updated_at": 0.0,
    })
    pcaf_v1: dict = field(default_factory=lambda: {
        "anomaly_score": 0, "confidence_pct": 0, "top_signal": "",
        "active_rules": [], "model_version": "v0_fallback",
        "reconstruction_error": 0.0, "graph_nodes": 0, "graph_edges": 0,
        "inference_ms": 0, "training_date": "", "updated_at": 0.0,
    })
    tpa: dict = field(default_factory=lambda: {
        "scenarios": [], "last_evaluated_at": 0.0, "next_evaluation_at": 0.0,
        "calibration_date": "", "data_quality": "initializing",
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
            "sentiment": dict(self.sentiment),
            "sovereign": dict(self.sovereign),
            "etf": dict(self.etf),
            "network_graph": dict(self.network_graph),
            "dark_pool": dict(self.dark_pool),
            "miner_health": dict(self.miner_health),
            "whale_coordination": dict(self.whale_coordination),
            "regulatory": dict(self.regulatory),
            "privacy_tech": dict(self.privacy_tech),
            "defi_btc": dict(self.defi_btc),
            "pcaf_v1": dict(self.pcaf_v1),
            "tpa": dict(self.tpa),
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
        # Phase 2 engines
        self._sentiment_engine = SentimentPulseEngine()
        self._sovereign_engine = SovereignEngine()
        self._etf_monitor = ETFMonitor()
        self._dark_pool_engine = DarkPoolEngine()
        self._miner_stress_engine = MinerStressEngine()
        self._whale_coord_engine = WhaleCoordinationEngine()
        self._regulatory_engine = RegulatoryIntelEngine()
        self._privacy_tech_engine = PrivacyTechEngine()
        # ML Phase: PCAF v1 + Data Collector
        self._pcaf_v1_engine = PCAFv1Engine()
        self._pcaf_data_collector = DataCollector()
        self._pcaf_collector_thread = None
        # ML Phase: TPA Scenario Engine
        self._tpa_engine = TPAEngine()
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
        """Run PCAF v0 + v1 (parallel) and update state + dispatch alerts."""
        score, signals, force_critical = self.run_pcaf_v0()
        with self._lock:
            self.state.pcaf_v0["anomaly_score"] = score
            self.state.pcaf_v0["active_rules"] = signals
            self.state.pcaf_v0["top_signal"] = signals[0] if signals else ""
            self.state.pcaf_v0["confidence_pct"] = min(score + 10, 100) if signals else 0
            self.state.pcaf_v0["updated_at"] = time.time()

        # PCAF v1 — GNN inference (runs alongside v0, never replaces it yet)
        try:
            if self._pcaf_v1_engine.is_ready() or self._pcaf_v1_engine.model is not None:
                v1_result = self._pcaf_v1_engine.score(self.state.to_dict())
                with self._lock:
                    self.state.pcaf_v1 = v1_result
            else:
                # Not trained yet — report v0_fallback
                with self._lock:
                    self.state.pcaf_v1["model_version"] = "v0_fallback"
                    self.state.pcaf_v1["updated_at"] = time.time()
        except Exception as e:
            logger.warning("PCAF v1 update error: %s", e)

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

    def _update_tpa(self):
        """Run Temporal Predictive Analytics scenario evaluation."""
        try:
            state_dict = self.state.to_dict()
            tpa_result = self._tpa_engine.run_cycle(state_dict)
            with self._lock:
                self.state.tpa = tpa_result
            logger.info("TPA evaluation complete: %d scenarios, quality=%s",
                        len(tpa_result.get("scenarios", [])),
                        tpa_result.get("data_quality", "unknown"))
        except Exception as e:
            logger.warning("TPA update error: %s", e)

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

    # ── Phase 2 Engines ───────────────────────────────────────────────────

    async def _update_sentiment(self, session: aiohttp.ClientSession):
        """Run sentiment pulse cycle and update state."""
        try:
            result = await self._sentiment_engine.run_cycle(session)
            with self._lock:
                self.state.sentiment = result
        except Exception as e:
            logger.error("Sentiment pulse failed: %s", e)

    async def _update_sovereign(self, session: aiohttp.ClientSession):
        """Run sovereign layer cycle and update state."""
        try:
            result = await self._sovereign_engine.run_cycle(session)
            with self._lock:
                self.state.sovereign = result
        except Exception as e:
            logger.error("Sovereign engine failed: %s", e)

    async def _update_etf(self, session: aiohttp.ClientSession):
        """Run ETF flow monitor cycle and update state."""
        try:
            # Get BTC price from state for USD conversion
            btc_price = 0
            try:
                with self._lock:
                    # Price might be in network or externally set
                    btc_price = self.state.network.get("btc_price_usd", 0)
            except Exception:
                pass
            result = await self._etf_monitor.run_cycle(session, btc_price_usd=btc_price)
            with self._lock:
                self.state.etf = result
        except Exception as e:
            logger.error("ETF monitor failed: %s", e)

    def _update_dark_pool(self):
        """Run dark pool analysis on current whale transactions."""
        try:
            with self._lock:
                whale_txs = list(self.state.mempool.get("whale_txs", []))
            result = self._dark_pool_engine.analyze(whale_txs)
            with self._lock:
                self.state.dark_pool = result
        except Exception as e:
            logger.error("Dark pool analysis failed: %s", e)

    def _update_miner_health(self):
        """Run miner stress/capitulation model."""
        try:
            with self._lock:
                network = dict(self.state.network)
                mempool = dict(self.state.mempool)
            result = self._miner_stress_engine.compute_score(
                network_state=network,
                mempool_state=mempool,
                hashrate_24h_ago=self._hashrate_24h_ago,
            )
            with self._lock:
                self.state.miner_health = result
        except Exception as e:
            logger.error("Miner health update failed: %s", e)

    def _update_whale_coordination(self):
        """Run whale coordination detection."""
        try:
            with self._lock:
                whale_txs = list(self.state.mempool.get("whale_txs", []))
                tier1_active = self.state.sentiment.get("tier1_signal", False)
            result = self._whale_coord_engine.analyze(whale_txs, tier1_active)
            with self._lock:
                self.state.whale_coordination = result
        except Exception as e:
            logger.error("Whale coordination update failed: %s", e)

    async def _update_regulatory(self, session):
        """Run regulatory intelligence cycle."""
        try:
            result = await self._regulatory_engine.run_cycle(session)
            with self._lock:
                self.state.regulatory = result
        except Exception as e:
            logger.error("Regulatory intel update failed: %s", e)

    async def _update_privacy_tech(self, session):
        """Run privacy tech metrics collection."""
        try:
            result = await self._privacy_tech_engine.run_cycle(session)
            with self._lock:
                self.state.privacy_tech = result
        except Exception as e:
            logger.error("Privacy tech update failed: %s", e)

    async def _update_defi_btc(self, session):
        """Run DeFi BTC collateralization monitor."""
        try:
            result = await self._etf_monitor.fetch_defi_btc(session)
            with self._lock:
                self.state.defi_btc = result
        except Exception as e:
            logger.error("DeFi BTC update failed: %s", e)

    def _update_network_graph(self):
        """Build network graph data from current state for D3 visualization."""
        try:
            nodes = []
            edges = []

            # Sentinel center node
            nodes.append({
                "id": "sentinel", "type": "sentinel", "label": "SENTINEL",
                "size": 20, "color": "#FF0000", "metric": "Protocol Pulse",
            })

            # Mining pools from recent blocks
            with self._lock:
                recent_blocks = self.state.network.get("recent_blocks", [])

            pool_counts = {}
            for block in recent_blocks:
                pool = block.get("extras", {}).get("pool", {}).get("name", "Unknown") if isinstance(block, dict) else "Unknown"
                pool_counts[pool] = pool_counts.get(pool, 0) + 1

            total_blocks = max(len(recent_blocks), 1)
            for pool, count in pool_counts.items():
                pct = (count / total_blocks) * 100
                color = "#FF3333" if pct > 40 else "#FFB800" if pct > 25 else "#00FF88"
                nodes.append({
                    "id": f"pool_{pool}", "type": "miner", "label": pool,
                    "size": max(8, pct / 2), "color": color,
                    "metric": f"{pct:.1f}% hashrate",
                })

            # Exchanges from custodian_wallets.json
            try:
                wallets_path = _svc_dir.parent / "data" / "custodian_wallets.json"
                with open(wallets_path) as f:
                    wallets_data = json.load(f)
                for w in wallets_data.get("wallets", []):
                    nodes.append({
                        "id": f"exch_{w['label'][:20]}", "type": "exchange",
                        "label": w["label"].split("(")[0].strip(), "size": 12,
                        "color": "#3B82F6", "metric": "custodian",
                    })
            except Exception:
                pass

            # Build edges (hub-and-spoke to sentinel)
            for node in nodes:
                if node["id"] != "sentinel":
                    edges.append({
                        "source": node["id"], "target": "sentinel",
                        "weight": node["size"] / 20,
                    })

            with self._lock:
                self.state.network_graph = {
                    "nodes": nodes, "edges": edges, "updated_at": time.time(),
                }

        except Exception as e:
            logger.error("Network graph update failed: %s", e)

    # ── Main Loop ──────────────────────────────────────────────────────────
    async def run(self):
        """Main async entry — run WebSocket + REST polling + PCAF + Convergence concurrently."""
        self._running = True
        logger.info("Sentinel daemon starting...")

        # Start PCAF v1 data collector as daemon thread
        if self._pcaf_collector_thread is None:
            self._pcaf_collector_thread = threading.Thread(
                target=self._pcaf_data_collector.run, daemon=True, name="pcaf_collector")
            self._pcaf_collector_thread.start()
            logger.info("PCAF v1 data collector thread started")

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

                # Sentiment Pulse every 30s (Phase 2 F2)
                if poll_counter % 6 == 0:
                    await self._update_sentiment(session)

                # Sovereign Layer every 5 min (Phase 2 F3)
                if poll_counter % 60 == 0:
                    await self._update_sovereign(session)

                # ETF Flow Monitor every 10 min (Phase 2 F4)
                if poll_counter % 120 == 0:
                    await self._update_etf(session)

                # Dark Pool every 5 min (Phase 2 F6)
                if poll_counter % 60 == 0:
                    self._update_dark_pool()

                # Miner Health every 10 min (Phase 2 F7)
                if poll_counter % 120 == 0:
                    self._update_miner_health()

                # Whale Coordination every 5 min (Phase 3 F1)
                if poll_counter % 60 == 0:
                    self._update_whale_coordination()

                # Regulatory Intel every 30 min (Phase 3 F2)
                if poll_counter % 360 == 0:
                    await self._update_regulatory(session)

                # Privacy Tech every 1 hour (Phase 3 F3)
                if poll_counter % 720 == 0:
                    await self._update_privacy_tech(session)

                # DeFi BTC every 30 min (Phase 3 F5)
                if poll_counter % 360 == 0:
                    await self._update_defi_btc(session)

                # Network Graph every 60s (Phase 2 F5)
                if poll_counter % 12 == 0:
                    self._update_network_graph()

                # TPA every 6 hours (ML Phase: Temporal Predictive Analytics)
                # 6h = 21600s / 5s per tick = 4320 ticks
                if poll_counter % 4320 == 0 or (poll_counter == 12 and not self.state.tpa.get("scenarios")):
                    self._update_tpa()

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
