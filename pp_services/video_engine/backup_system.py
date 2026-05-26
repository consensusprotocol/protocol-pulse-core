"""
AUTOMATED BACKUP SYSTEM
=========================
Daily snapshots of databases, configs, and state files.
Includes retention policy, integrity verification, and restore capability.

Usage:
    python -m services.video_engine.backup_system             # Run backup now
    python -m services.video_engine.backup_system --list       # List backups
    python -m services.video_engine.backup_system --restore    # Restore latest
"""

import os
import json
import shutil
import hashlib
import logging
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("BackupSystem")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKUP_ROOT = _PROJECT_ROOT / "data" / "backups"
BACKUP_ROOT.mkdir(parents=True, exist_ok=True)

# Retention policy
MAX_DAILY_BACKUPS = 7
MAX_WEEKLY_BACKUPS = 4
MAX_MONTHLY_BACKUPS = 3

# Files to back up
BACKUP_TARGETS = {
    "databases": [
        "instance/protocol_pulse.db",
        "data/video_engine/pipeline_state.db",
        "data/video_engine/monitoring.db",
        "data/video_engine/cost_tracking.db",
        "data/video_engine/ab_testing.db",
        "data/sovereign_intel.db",
    ],
    "configs": [
        "config/editorial_config.json",
        ".env.example",
    ],
    "state": [
        "state/editorial_memory.json",
        "state/content_calendar.json",
        "logs/watchdog_state.json",
        "logs/governance_usage.json",
    ],
    "data": [
        "data/video_engine/quality_scores.json",
        "data/pulse_events.jsonl",
    ],
}


class BackupManager:
    """Manage automated backups with retention policies."""

    def create_backup(self, label: str = None) -> Dict:
        """Create a full backup snapshot.

        Returns:
            {"backup_id": str, "path": str, "files": int, "size_mb": float}
        """
        now = datetime.utcnow()
        backup_id = now.strftime("%Y%m%d_%H%M%S")
        if label:
            backup_id += f"_{label}"

        backup_dir = BACKUP_ROOT / backup_id
        backup_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "backup_id": backup_id,
            "created_at": now.isoformat(),
            "label": label or "automated",
            "files": [],
            "total_size": 0,
            "integrity_checks": {},
        }

        for category, paths in BACKUP_TARGETS.items():
            cat_dir = backup_dir / category
            cat_dir.mkdir(parents=True, exist_ok=True)

            for rel_path in paths:
                src = Path(rel_path)
                if not src.exists():
                    continue

                # For SQLite databases, use safe copy (VACUUM INTO or copy)
                dst = cat_dir / src.name
                try:
                    if rel_path.endswith(".db"):
                        self._backup_sqlite(str(src), str(dst))
                    else:
                        shutil.copy2(str(src), str(dst))

                    # Calculate checksum
                    checksum = self._file_checksum(str(dst))
                    file_size = dst.stat().st_size

                    manifest["files"].append({
                        "source": rel_path,
                        "backup_path": str(dst.relative_to(backup_dir)),
                        "size": file_size,
                        "checksum": checksum,
                        "category": category,
                    })
                    manifest["total_size"] += file_size
                    manifest["integrity_checks"][rel_path] = checksum

                except Exception as e:
                    logger.warning(f"Failed to backup {rel_path}: {e}")
                    manifest["files"].append({
                        "source": rel_path,
                        "error": str(e),
                        "category": category,
                    })

        # Save manifest
        manifest_path = backup_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # Apply retention policy
        self._apply_retention()

        size_mb = manifest["total_size"] / (1024 * 1024)
        logger.info(f"Backup created: {backup_id} "
                    f"({len(manifest['files'])} files, {size_mb:.1f} MB)")

        return {
            "backup_id": backup_id,
            "path": str(backup_dir),
            "files": len(manifest["files"]),
            "size_mb": round(size_mb, 2),
        }

    def _backup_sqlite(self, src: str, dst: str):
        """Safely backup a SQLite database."""
        try:
            # Use SQLite backup API for consistency
            src_conn = sqlite3.connect(src)
            dst_conn = sqlite3.connect(dst)
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
        except Exception:
            # Fallback to file copy
            shutil.copy2(src, dst)

    def _file_checksum(self, path: str) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]

    def _apply_retention(self):
        """Apply backup retention policy."""
        backups = self.list_backups()
        if not backups:
            return

        now = datetime.utcnow()

        # Sort by date (newest first)
        backups.sort(key=lambda b: b.get("created_at", ""), reverse=True)

        # Keep strategy: last 7 daily, 4 weekly, 3 monthly
        to_keep = set()

        # Daily: keep last 7
        for b in backups[:MAX_DAILY_BACKUPS]:
            to_keep.add(b["backup_id"])

        # Weekly: keep one per week for last 4 weeks
        weeks_kept = 0
        last_week = None
        for b in backups:
            try:
                dt = datetime.fromisoformat(b["created_at"])
                week = dt.isocalendar()[1]
                if week != last_week:
                    to_keep.add(b["backup_id"])
                    weeks_kept += 1
                    last_week = week
                if weeks_kept >= MAX_WEEKLY_BACKUPS:
                    break
            except Exception:
                pass

        # Monthly: keep one per month for last 3 months
        months_kept = 0
        last_month = None
        for b in backups:
            try:
                dt = datetime.fromisoformat(b["created_at"])
                month = (dt.year, dt.month)
                if month != last_month:
                    to_keep.add(b["backup_id"])
                    months_kept += 1
                    last_month = month
                if months_kept >= MAX_MONTHLY_BACKUPS:
                    break
            except Exception:
                pass

        # Delete expired backups
        for b in backups:
            if b["backup_id"] not in to_keep:
                backup_path = BACKUP_ROOT / b["backup_id"]
                if backup_path.exists():
                    shutil.rmtree(str(backup_path))
                    logger.info(f"Deleted expired backup: {b['backup_id']}")

    def list_backups(self) -> List[Dict]:
        """List all available backups."""
        backups = []
        for path in sorted(BACKUP_ROOT.iterdir(), reverse=True):
            if not path.is_dir():
                continue
            manifest_path = path / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text())
                    backups.append({
                        "backup_id": manifest.get("backup_id", path.name),
                        "created_at": manifest.get("created_at", ""),
                        "label": manifest.get("label", ""),
                        "files": len(manifest.get("files", [])),
                        "size_mb": round(
                            manifest.get("total_size", 0) / (1024 * 1024), 2),
                    })
                except Exception:
                    backups.append({
                        "backup_id": path.name,
                        "created_at": "",
                        "files": 0,
                        "size_mb": 0,
                    })
        return backups

    def restore_backup(self, backup_id: str = None) -> Dict:
        """Restore from a backup. Uses latest if backup_id not specified."""
        backups = self.list_backups()
        if not backups:
            return {"error": "No backups available"}

        if backup_id:
            backup = next((b for b in backups if b["backup_id"] == backup_id), None)
            if not backup:
                return {"error": f"Backup {backup_id} not found"}
        else:
            backup = backups[0]  # Latest
            backup_id = backup["backup_id"]

        backup_dir = BACKUP_ROOT / backup_id
        manifest_path = backup_dir / "manifest.json"

        if not manifest_path.exists():
            return {"error": "Backup manifest not found"}

        manifest = json.loads(manifest_path.read_text())
        restored = []
        errors = []

        for file_info in manifest.get("files", []):
            if "error" in file_info:
                continue

            src = backup_dir / file_info["backup_path"]
            dst = Path(file_info["source"])

            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dst))

                # Verify checksum
                checksum = self._file_checksum(str(dst))
                if checksum != file_info.get("checksum"):
                    errors.append(f"Checksum mismatch: {file_info['source']}")
                else:
                    restored.append(file_info["source"])

            except Exception as e:
                errors.append(f"Failed to restore {file_info['source']}: {e}")

        return {
            "backup_id": backup_id,
            "restored": len(restored),
            "errors": errors,
            "files": restored,
        }

    def verify_backup(self, backup_id: str) -> Dict:
        """Verify integrity of a backup."""
        backup_dir = BACKUP_ROOT / backup_id
        manifest_path = backup_dir / "manifest.json"

        if not manifest_path.exists():
            return {"valid": False, "error": "Manifest not found"}

        manifest = json.loads(manifest_path.read_text())
        valid = True
        issues = []

        for file_info in manifest.get("files", []):
            if "error" in file_info:
                continue

            backup_file = backup_dir / file_info["backup_path"]
            if not backup_file.exists():
                valid = False
                issues.append(f"Missing: {file_info['backup_path']}")
                continue

            checksum = self._file_checksum(str(backup_file))
            if checksum != file_info.get("checksum"):
                valid = False
                issues.append(f"Checksum mismatch: {file_info['backup_path']}")

        return {
            "backup_id": backup_id,
            "valid": valid,
            "files_checked": len(manifest.get("files", [])),
            "issues": issues,
        }


# ─── Performance Profiler ───

class PipelineProfiler:
    """Profile pipeline stage performance and identify bottlenecks."""

    PROFILE_DB = Path(__file__).resolve().parent.parent.parent / "data" / "video_engine" / "profiling.db"

    def __init__(self):
        self.PROFILE_DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.PROFILE_DB))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS stage_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                stage TEXT NOT NULL,
                duration_seconds REAL NOT NULL,
                memory_mb REAL,
                cpu_percent REAL,
                io_read_mb REAL,
                io_write_mb REAL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_prof_date ON stage_profiles(date);
            CREATE INDEX IF NOT EXISTS idx_prof_stage ON stage_profiles(stage);
        """)
        conn.commit()
        conn.close()

    def record_profile(self, date: str, stage: str,
                      duration: float, memory_mb: float = 0,
                      cpu_percent: float = 0, metadata: Dict = None):
        """Record a stage performance profile."""
        conn = sqlite3.connect(str(self.PROFILE_DB))
        conn.execute(
            """INSERT INTO stage_profiles
               (date, stage, duration_seconds, memory_mb, cpu_percent, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (date, stage, duration, memory_mb, cpu_percent,
             json.dumps(metadata or {}), datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def get_bottlenecks(self, days: int = 7) -> List[Dict]:
        """Identify the slowest stages (bottlenecks)."""
        conn = sqlite3.connect(str(self.PROFILE_DB))
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        rows = conn.execute(
            """SELECT stage,
                      AVG(duration_seconds) as avg_duration,
                      MAX(duration_seconds) as max_duration,
                      MIN(duration_seconds) as min_duration,
                      COUNT(*) as runs
               FROM stage_profiles
               WHERE date >= ?
               GROUP BY stage
               ORDER BY avg_duration DESC""",
            (cutoff,)
        ).fetchall()
        conn.close()

        return [{
            "stage": r["stage"],
            "avg_duration": round(r["avg_duration"], 1),
            "max_duration": round(r["max_duration"], 1),
            "min_duration": round(r["min_duration"], 1),
            "runs": r["runs"],
            "is_bottleneck": r["avg_duration"] > 60,  # >60s = bottleneck
        } for r in rows]

    def get_trend(self, stage: str, days: int = 30) -> List[Dict]:
        """Get performance trend for a specific stage."""
        conn = sqlite3.connect(str(self.PROFILE_DB))
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        rows = conn.execute(
            """SELECT date, duration_seconds, memory_mb
               FROM stage_profiles
               WHERE stage = ? AND date >= ?
               ORDER BY date""",
            (stage, cutoff)
        ).fetchall()
        conn.close()

        return [{
            "date": r["date"],
            "duration": round(r["duration_seconds"], 1),
            "memory_mb": round(r["memory_mb"], 1) if r["memory_mb"] else 0,
        } for r in rows]


# ─── Audit Trail ───

class AuditTrail:
    """Track all changes to content and configuration."""

    AUDIT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "video_engine" / "audit_trail.db"

    def __init__(self):
        self.AUDIT_DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.AUDIT_DB))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                actor TEXT NOT NULL DEFAULT 'system',
                action TEXT NOT NULL,
                before_state TEXT,
                after_state TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_type, entity_id);
            CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events(actor);
            CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_events(created_at);
        """)
        conn.commit()
        conn.close()

    def log(self, event_type: str, entity_type: str,
            action: str, entity_id: str = None,
            actor: str = "system",
            before_state: str = None,
            after_state: str = None,
            metadata: Dict = None):
        """Log an audit event."""
        conn = sqlite3.connect(str(self.AUDIT_DB))
        conn.execute(
            """INSERT INTO audit_events
               (event_type, entity_type, entity_id, actor, action,
                before_state, after_state, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_type, entity_type, entity_id, actor, action,
             before_state, after_state,
             json.dumps(metadata or {}),
             datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def log_content_change(self, content_type: str, content_id: str,
                          action: str, actor: str = "system",
                          before: str = None, after: str = None):
        """Shortcut for content changes (article edits, config changes, etc.)."""
        self.log(
            event_type="content_change",
            entity_type=content_type,
            entity_id=content_id,
            action=action,
            actor=actor,
            before_state=before[:1000] if before else None,
            after_state=after[:1000] if after else None,
        )

    def log_pipeline_event(self, stage: str, action: str,
                          metadata: Dict = None):
        """Shortcut for pipeline events."""
        self.log(
            event_type="pipeline",
            entity_type="stage",
            entity_id=stage,
            action=action,
            metadata=metadata,
        )

    def log_config_change(self, config_name: str, before: str, after: str,
                         actor: str = "system"):
        """Shortcut for config changes."""
        self.log(
            event_type="config_change",
            entity_type="config",
            entity_id=config_name,
            action="update",
            actor=actor,
            before_state=before[:2000] if before else None,
            after_state=after[:2000] if after else None,
        )

    def get_events(self, entity_type: str = None,
                  entity_id: str = None,
                  limit: int = 50,
                  days: int = 7) -> List[Dict]:
        """Query audit events."""
        conn = sqlite3.connect(str(self.AUDIT_DB))
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        query = "SELECT * FROM audit_events WHERE created_at > ?"
        params = [cutoff]

        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        return [{
            "id": r["id"],
            "event_type": r["event_type"],
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "actor": r["actor"],
            "action": r["action"],
            "has_before": bool(r["before_state"]),
            "has_after": bool(r["after_state"]),
            "created_at": r["created_at"],
        } for r in rows]

    def get_content_history(self, content_type: str,
                           content_id: str) -> List[Dict]:
        """Get full edit history for a piece of content."""
        conn = sqlite3.connect(str(self.AUDIT_DB))
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """SELECT * FROM audit_events
               WHERE entity_type = ? AND entity_id = ?
               ORDER BY created_at""",
            (content_type, content_id)
        ).fetchall()
        conn.close()

        return [{
            "action": r["action"],
            "actor": r["actor"],
            "before": r["before_state"],
            "after": r["after_state"],
            "timestamp": r["created_at"],
        } for r in rows]


# ─── CLI ───

def main():
    parser = argparse.ArgumentParser(description="Backup System")
    parser.add_argument("--list", action="store_true", help="List backups")
    parser.add_argument("--restore", nargs="?", const="latest",
                       help="Restore from backup (default: latest)")
    parser.add_argument("--verify", type=str, help="Verify backup integrity")
    parser.add_argument("--label", type=str, help="Label for the backup")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s %(levelname)s: %(message)s')

    manager = BackupManager()

    if args.list:
        backups = manager.list_backups()
        if not backups:
            print("No backups found.")
            return
        print(f"\n{'ID':<30} {'Date':<25} {'Files':<8} {'Size':<10} {'Label'}")
        print("-" * 85)
        for b in backups:
            print(f"{b['backup_id']:<30} {b['created_at'][:19]:<25} "
                  f"{b['files']:<8} {b['size_mb']:.1f} MB   {b.get('label', '')}")
        return

    if args.verify:
        result = manager.verify_backup(args.verify)
        print(f"Backup: {args.verify}")
        print(f"Valid: {result['valid']}")
        if result.get("issues"):
            for issue in result["issues"]:
                print(f"  ISSUE: {issue}")
        return

    if args.restore:
        backup_id = None if args.restore == "latest" else args.restore
        result = manager.restore_backup(backup_id)
        if result.get("error"):
            print(f"ERROR: {result['error']}")
        else:
            print(f"Restored {result['restored']} files from {result['backup_id']}")
            if result.get("errors"):
                for err in result["errors"]:
                    print(f"  ERROR: {err}")
        return

    # Default: create backup
    result = manager.create_backup(label=args.label)
    print(f"Backup created: {result['backup_id']}")
    print(f"Files: {result['files']}, Size: {result['size_mb']:.1f} MB")


if __name__ == "__main__":
    main()
