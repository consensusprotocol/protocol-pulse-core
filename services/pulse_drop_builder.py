from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict

from app import app, db
import models
from services.channel_monitor import channel_monitor_service
from services.highlight_extractor import highlight_extractor_service
from services.commentary_generator import commentary_generator_service
from services.global_relay import global_relay_service


class PulseDropBuilderService:
    """Force-run builder for end-to-end Pulse Drop alpha execution."""

    def force_build(self) -> Dict:
        with app.app_context():
            # Hard reset recent rows to guarantee deterministic alpha run.
            cutoff = datetime.utcnow() - timedelta(days=2)
            models.PulseSegment.query.filter(models.PulseSegment.created_at >= cutoff).delete()
            db.session.commit()

            harvest = channel_monitor_service.run_harvest(hours_back=24, max_total=5)
            extract = highlight_extractor_service.run(hours_back=24, single_alpha_per_video=True)
            commentary = commentary_generator_service.run(
                hours_back=24,
                tone="Sovereign, High-Intelligence, No-Nonsense.",
            )
            segments = (
                models.PulseSegment.query.order_by(models.PulseSegment.priority.desc(), models.PulseSegment.created_at.desc())
                .limit(50)
                .all()
            )
            relay = global_relay_service.broadcast_pulse_drop(
                reel_link="https://protocolpulse.io/pulse-drop",
                segments=[
                    {"label": s.label, "start_sec": s.start_sec, "video_id": s.video_id}
                    for s in segments[:8]
                ],
            )
            return {
                "ok": True,
                "harvest": harvest,
                "extract": extract,
                "commentary": commentary,
                "relay": relay,
                "segments_count": len(segments),
                "has_audio_all": all(bool(s.commentary_audio) for s in segments) if segments else False,
                "route": "/pulse-drop",
            }


pulse_drop_builder_service = PulseDropBuilderService()

