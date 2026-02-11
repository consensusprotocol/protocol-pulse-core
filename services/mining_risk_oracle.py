"""
Compatibility facade for legacy mining risk oracle imports.

Backed by services.mining_risk_service to avoid duplicate risk logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.mining_risk_service import get_regions_with_risk


class MiningRiskOracle:
    def _region_to_location(self, r: Dict[str, Any]) -> Dict[str, Any]:
        # Stable location id mapping expected by older callers.
        location_id = f"{(r.get('code') or '').lower()}_{(r.get('name') or '').lower().split()[0]}"
        if location_id == "us_united":
            location_id = "us_texas"
        return {
            "id": location_id,
            "code": r.get("code"),
            "name": r.get("name"),
            "region": r.get("region"),
            "overall_score": int(r.get("composite_risk") or 0),
            "regulatory_risk": int(r.get("regulatory_risk") or 0),
            "energy_cost_risk": int(r.get("energy_cost_risk") or 0),
            "stability_risk": int(r.get("stability_risk") or 0),
            "risk_label": r.get("risk_label"),
            "hashrate_share_est": r.get("hashrate_share_est", 0),
            "note": r.get("note", ""),
        }

    def get_all_locations(self) -> List[Dict[str, Any]]:
        return [self._region_to_location(r) for r in get_regions_with_risk()]

    def get_location_risk(self, location_id: str) -> Optional[Dict[str, Any]]:
        locations = self.get_all_locations()
        loc = next((l for l in locations if l["id"] == location_id), None)
        if loc:
            return loc
        # Friendly fallback aliases
        if location_id in {"us", "us_united", "us_texas"}:
            return next((l for l in locations if l.get("code") == "US"), None)
        return None


oracle = MiningRiskOracle()

