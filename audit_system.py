# audit_system.py

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class AuditLogger:
    """
    FINAL – JSON-based audit logging system
    Hackathon + production safe
    No database, no external dependencies
    """

    def __init__(self, audit_dir: str = "audit_logs"):
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def start_session(self, filename: str) -> str:
        """
        Start a new audit session for a document
        Returns session_id
        """
        session_id = str(uuid.uuid4())

        audit_data = {
            "session_id": session_id,
            "filename": filename,
            "started_at": self._now(),
            "events": []
        }

        self._write(session_id, audit_data)
        return session_id

    def log_event(
        self,
        session_id: str,
        stage: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Log a processing event
        """
        audit = self._read(session_id)

        event = {
            "timestamp": self._now(),
            "stage": stage,
            "data": data or {}
        }

        audit["events"].append(event)
        self._write(session_id, audit)

    def close_session(
        self,
        session_id: str,
        status: str = "completed"
    ):
        """
        Mark audit session as completed or failed
        """
        audit = self._read(session_id)

        audit["completed_at"] = self._now()
        audit["status"] = status

        self._write(session_id, audit)

    def get_audit_log(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve full audit trail
        """
        return self._read(session_id)

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _audit_file(self, session_id: str) -> Path:
        return self.audit_dir / f"{session_id}.json"

    def _write(self, session_id: str, data: Dict[str, Any]):
        file = self._audit_file(session_id)
        file.write_text(json.dumps(data, indent=2))

    def _read(self, session_id: str) -> Dict[str, Any]:
        file = self._audit_file(session_id)
        if not file.exists():
            raise FileNotFoundError("Audit session not found")
        return json.loads(file.read_text())

    def _now(self) -> str:
        return datetime.utcnow().isoformat()
