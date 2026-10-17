from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from models import StudySession, Topic
from time_utils import ensure_local_timezone, local_now, naive_local_now

logger = logging.getLogger(__name__)


class SessionController(QObject):
    changed = Signal()

    def __init__(
        self,
        db_factory: Callable[[], Any],
        save_callback: Callable[[], None] | None = None,
        toast_callback: Callable[[str, str, str], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db_factory
        self._save_callback = save_callback or (lambda: None)
        self._toast_callback = toast_callback or (lambda level, title, msg: None)
        self._active_session: dict[str, Any] | None = None
        self._study_minutes: list[int] = []

    def initialize_state(
        self,
        active_session: dict[str, Any] | None,
        study_minutes: list[int] | None,
    ) -> None:
        self._active_session = self._normalize_active_session(active_session)
        self._study_minutes = list(study_minutes or [])

    @property
    def active_session_payload(self) -> dict[str, Any] | None:
        return self._active_session

    @property
    def study_minutes_payload(self) -> list[int]:
        return list(self._study_minutes)

    def record_minutes(self, minutes: int) -> None:
        self._study_minutes.append(max(1, minutes))
        self._study_minutes = self._study_minutes[-14:]
        self._save_callback()
        self.changed.emit()

    def _normalize_active_session(
        self, active_session: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if not isinstance(active_session, dict):
            return None
        session_id = active_session.get("id")
        started_at = active_session.get("started_at")
        topic = active_session.get("topic", "")
        subject = active_session.get("subject", "")
        try:
            parsed_id = int(session_id)
            parsed_started_at = ensure_local_timezone(datetime.fromisoformat(str(started_at)))
        except (TypeError, ValueError):
            return None
        return {
            "id": parsed_id,
            "started_at": parsed_started_at.isoformat(),
            "topic": str(topic or ""),
            "subject": str(subject or ""),
        }

    @Property("QVariantMap", notify=changed)
    def activeSession(self) -> dict[str, Any]:
        if self._active_session is None:
            return {
                "active": False,
                "label": "Start Session",
                "detail": "No active study session",
                "topic": "",
                "subject": "",
                "elapsedMinutes": 0,
                "elapsedSeconds": 0,
                "startedAt": "",
                "timerText": "00:00:00",
            }
        started_at = ensure_local_timezone(
            datetime.fromisoformat(self._active_session["started_at"])
        )
        elapsed_seconds = max(0, round((local_now() - started_at).total_seconds()))
        elapsed_minutes = max(0, elapsed_seconds // 60)
        topic = self._active_session.get("topic", "")
        subject = self._active_session.get("subject", "")
        detail = f"{elapsed_minutes} min on {topic}" if topic else f"{elapsed_minutes} min active"
        if subject:
            detail += f" ({subject})"
        return {
            "active": True,
            "label": "End Session",
            "detail": detail,
            "topic": topic,
            "subject": subject,
            "elapsedMinutes": elapsed_minutes,
            "elapsedSeconds": elapsed_seconds,
            "startedAt": started_at.isoformat(),
            "timerText": f"{elapsed_seconds // 3600:02d}:{(elapsed_seconds % 3600) // 60:02d}:{elapsed_seconds % 60:02d}",
        }

    @Property("QVariantList", notify=changed)
    def studyMinutes(self) -> list[int]:
        return self._study_minutes

    @Slot(str)
    def startStudySession(self, topic_id: str) -> None:
        clean_id = str(topic_id).strip()
        if not clean_id:
            return
        if self._active_session is not None:
            self.endStudySession()

        try:
            with self._db() as db:
                topic = db.get(Topic, int(clean_id))
                if topic is None:
                    return
                session_record = StudySession(
                    topic_id=topic.id,
                    started_at=naive_local_now(),
                )
                db.add(session_record)
                db.flush()
                self._active_session = {
                    "id": session_record.id,
                    "started_at": local_now().isoformat(),
                    "topic": topic.name,
                    "subject": topic.subject.name if topic.subject else "",
                }
            self._save_callback()
            self._toast_callback(
                "info", "Session Started", f"Now studying {self._active_session['topic']}."
            )
            self.changed.emit()
        except Exception:
            logger.exception("Failed to start study session for topic %s", clean_id)
            self._toast_callback("error", "Error", "Could not start session.")

    @Slot()
    def endStudySession(self) -> None:
        if self._active_session is None:
            return
        session_id = self._active_session["id"]
        started_at = ensure_local_timezone(
            datetime.fromisoformat(self._active_session["started_at"])
        )
        duration_minutes = max(1, round((local_now() - started_at).total_seconds() / 60))
        topic_name = self._active_session.get("topic", "study block")

        try:
            with self._db() as db:
                session_record = db.get(StudySession, session_id)
                if session_record is not None:
                    session_record.ended_at = naive_local_now()
                    session_record.duration_minutes = duration_minutes
            self._study_minutes.append(duration_minutes)
            self._study_minutes = self._study_minutes[-14:]
            self._active_session = None
            self._save_callback()
            self._toast_callback(
                "success", "Session Ended", f"Completed {duration_minutes} min on {topic_name}."
            )
            self.changed.emit()
        except Exception:
            logger.exception("Failed to end study session %s", session_id)
            self._active_session = None
            self.changed.emit()
