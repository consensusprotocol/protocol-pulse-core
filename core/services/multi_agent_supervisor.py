"""
Multi-Agent Supervisor: orchestrates Alex and Sarah using LangGraph (or a simple pipeline).
Alex pulls live on-chain data (block height, hashrate, difficulty) via NodeService and provides
"Ground Truth." Sarah then layers macro strategy on top using audience analytics.
The Supervisor compiles both into a launch-ready content package with headlines, viral hooks,
and target audience segments. Used by admin supervisor dashboard and content pipeline.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MultiAgentSupervisor:
    def __init__(self):
        self._node = None
        self._ai = None

    def get_ground_truth(self) -> Dict:
        """Alex: live on-chain data from NodeService."""
        try:
            from services.node_service import NodeService
            return NodeService.get_network_stats() or {}
        except Exception as e:
            logger.warning("get_ground_truth failed: %s", e)
            return {}

    def get_macro_layer(self, ground_truth: Dict) -> Dict:
        """Sarah: macro strategy and audience segments based on ground truth."""
        try:
            from services.ai_service import AIService
            ai = AIService()
            prompt = f"""You are Sarah, Protocol Pulse's macro strategist. Given this Bitcoin network ground truth:

Block height: {ground_truth.get('height', 'N/A')}
Hashrate: {ground_truth.get('hashrate', 'N/A')}
Difficulty progress: {ground_truth.get('difficulty_progress', 'N/A')}

Provide a brief macro layer (2-3 sentences): what this means for sovereign stackers and operators. Then suggest:
- One headline for a brief
- One viral hook (tweet-length)
- Target audience segment (e.g. "miners", "long-term holders", "new entrants").

Output JSON: {"macro_summary": "...", "headline": "...", "viral_hook": "...", "audience_segment": "..."}"""
            raw = ai.generate_content_openai(prompt)
            if not raw:
                return {}
            import json
            text = raw.strip()
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            return json.loads(text)
        except Exception as e:
            logger.warning("get_macro_layer failed: %s", e)
            return {}

    def build_content_package(self, topic: Optional[str] = None) -> Dict:
        """
        Compile Alex (ground truth) + Sarah (macro) into a launch-ready content package.
        Returns { ground_truth, macro_layer, headlines, viral_hooks, audience_segments }.
        """
        ground_truth = self.get_ground_truth()
        macro_layer = self.get_macro_layer(ground_truth)
        return {
            "ground_truth": ground_truth,
            "macro_layer": macro_layer,
            "headlines": [macro_layer.get("headline", "Bitcoin Network Update")],
            "viral_hooks": [macro_layer.get("viral_hook", "")],
            "audience_segments": [macro_layer.get("audience_segment", "operators")],
        }


multi_agent_supervisor = MultiAgentSupervisor()
