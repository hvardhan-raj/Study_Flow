from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlalchemy.orm import Session

from models import ConfidenceRating, Revision
from services import SchedulerService
from time_utils import naive_local_now

logger = logging.getLogger(__name__)


def _rating_from_int(value: int) -> ConfidenceRating:
    return {
        1: ConfidenceRating.AGAIN,
        2: ConfidenceRating.HARD,
        3: ConfidenceRating.GOOD,
        4: ConfidenceRating.EASY,
    }[max(1, min(int(value), 4))]


class TaskController(QObject):
    changed = Signal()

    def __init__(
        self,
        db_factory: Callable[[], Any],
        view_model: Any,
        today_provider: Callable[[], date],
        on_revision_completed: Callable[[], None] | None = None,
        on_minutes_recorded: Callable[[int], None] | None = None,
        toast_callback: Callable[[str, str, str], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db_factory
        self._view_model = view_model
        self._today_provider = today_provider
        self._on_revision_completed = on_revision_completed or (lambda: None)
        self._on_minutes_recorded = on_minutes_recorded or (lambda m: None)
        self._toast_callback = toast_callback or (lambda level, title, msg: None)
        self._task_filter = "all"

    def _scheduler(self, db: Session) -> SchedulerService:
        today_val = self._today_provider()
        return SchedulerService(db, today_provider=lambda: today_val)

    @Property(str, notify=changed)
    def taskFilter(self) -> str:
        return self._task_filter

    @Slot(str)
    def setTaskFilter(self, filter_name: str) -> None:
        clean = (filter_name or "all").strip().lower()
        if self._task_filter != clean:
            self._task_filter = clean
            self.changed.emit()

    @Property("QVariantList", notify=changed)
    def tasks(self) -> list[dict[str, Any]]:
        return self._view_model.tasks()

    @Property("QVariantList", notify=changed)
    def filteredTasks(self) -> list[dict[str, Any]]:
        all_tasks = self.tasks
        if self._task_filter == "due_today":
            return [t for t in all_tasks if t.get("bucket") == "due_today"]
        if self._task_filter == "overdue":
            return [t for t in all_tasks if t.get("bucket") == "overdue"]
        if self._task_filter == "upcoming":
            return [t for t in all_tasks if t.get("bucket") == "upcoming"]
        if self._task_filter == "completed":
            return [t for t in all_tasks if t.get("completed")]
        return all_tasks

    @Slot(str, int)
    def completeRevision(self, revision_id: str, rating: int) -> None:
        safe_rating = max(1, min(int(rating), 4))
        try:
            with self._db() as db:
                revision = db.get(Revision, int(revision_id))
                if revision is None:
                    return
                topic_name = revision.topic.name if revision.topic else "revision"
                self._scheduler(db).record_revision(
                    revision.id,
                    rating=_rating_from_int(safe_rating),
                    completed_at=naive_local_now(),
                )
            self._on_minutes_recorded(25)
            self._on_revision_completed()
            self._toast_callback(
                "success", "Revision Completed", f"Recorded review for {topic_name}."
            )
            self.changed.emit()
        except Exception:
            logger.exception("Failed to complete revision %s", revision_id)
            self._toast_callback("error", "Error", "Could not complete revision.")

    @Slot(str, int)
    def reviewTopic(self, topic_id: str, rating: int) -> None:
        safe_rating = max(1, min(int(rating), 4))
        try:
            with self._db() as db:
                scheduler = self._scheduler(db)
                scheduler.review(
                    topic_id, _rating_from_int(safe_rating), completed_at=naive_local_now()
                )
            self._on_minutes_recorded(25)
            self._on_revision_completed()
            self.changed.emit()
        except Exception:
            logger.exception("Failed to review topic %s", topic_id)

    @Slot(str)
    def markTaskDone(self, task_id: str) -> None:
        try:
            with self._db() as db:
                revision = db.get(Revision, int(task_id))
                if revision is None or revision.status != "open":
                    self._toast_callback(
                        "error", "Task Update Failed", "That task is no longer available."
                    )
                    return
                topic_name = revision.topic.name
                self._scheduler(db).record_revision(
                    revision.id, rating=ConfidenceRating.GOOD, completed_at=naive_local_now()
                )
            self._on_minutes_recorded(25)
            self._on_revision_completed()
            self._toast_callback("success", "Task Done", f"Completed review of {topic_name}.")
            self.changed.emit()
        except Exception:
            logger.exception("Failed to mark task %s as done", task_id)
            self._toast_callback("error", "Error", "Could not update task.")

    @Slot(str, str)
    def rescheduleRevision(self, revision_id: str, new_date_str: str) -> None:
        try:
            target_date = date.fromisoformat(new_date_str)
            with self._db() as db:
                revision = db.get(Revision, int(revision_id))
                if revision is not None and revision.status == "open":
                    revision.due_at = datetime.combine(target_date, revision.due_at.time())
            self._toast_callback("info", "Rescheduled", "Revision scheduled for new date.")
            self.changed.emit()
        except Exception:
            logger.exception("Failed to reschedule revision %s", revision_id)

    @Slot(str)
    def skipRevision(self, revision_id: str) -> None:
        try:
            with self._db() as db:
                revision = db.get(Revision, int(revision_id))
                if revision is not None and revision.status == "open":
                    revision.status = "skipped"
            self._toast_callback("info", "Skipped", "Revision was skipped.")
            self.changed.emit()
        except Exception:
            logger.exception("Failed to skip revision %s", revision_id)
