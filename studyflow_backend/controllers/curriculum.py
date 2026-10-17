from __future__ import annotations

import logging
from collections.abc import Callable
from colorsys import hls_to_rgb
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import DifficultyLevel, Subject, Topic
from services import SchedulerService, SubjectService, TopicService

logger = logging.getLogger(__name__)


class CurriculumController(QObject):
    changed = Signal()

    def __init__(
        self,
        db_factory: Callable[[], Any],
        view_model: Any,
        today_provider: Callable[[], Any],
        on_intelligence_refresh: Callable[..., None] | None = None,
        toast_callback: Callable[[str, str, str], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db_factory
        self._view_model = view_model
        self._today_provider = today_provider
        self._on_intelligence_refresh = on_intelligence_refresh or (lambda **k: None)
        self._toast_callback = toast_callback or (lambda level, title, msg: None)
        self._curriculum_filter = "All"
        self._curriculum_search = ""

    def _scheduler(self, db: Session) -> SchedulerService:
        today_val = self._today_provider()
        return SchedulerService(db, today_provider=lambda: today_val)

    @Property(str, notify=changed)
    def curriculumFilter(self) -> str:
        return self._curriculum_filter

    @Property(str, notify=changed)
    def curriculumSearch(self) -> str:
        return self._curriculum_search

    @Property("QVariantList", notify=changed)
    def curriculumTree(self) -> list[dict[str, Any]]:
        return self._view_model.curriculum_tree()

    @Property(int, notify=changed)
    def curriculumSubjectCount(self) -> int:
        return self._view_model.curriculum_subject_count()

    @Property(int, notify=changed)
    def curriculumTopicCount(self) -> int:
        return self._view_model.curriculum_topic_count()

    @Property(int, notify=changed)
    def curriculumMasteryAverage(self) -> int:
        return self._view_model.curriculum_mastery_average()

    @Property("QVariantList", notify=changed)
    def subjectOptions(self) -> list[dict[str, Any]]:
        return self._view_model.subject_options()

    @Property("QVariantList", constant=True)
    def difficultyOptions(self) -> list[str]:
        return ["Easy", "Medium", "Hard"]

    @Slot(str)
    def setCurriculumFilter(self, filter_name: str) -> None:
        clean = (filter_name or "All").strip()
        if self._curriculum_filter != clean:
            self._curriculum_filter = clean
            self.changed.emit()

    @Slot(str)
    def setCurriculumSearch(self, query: str) -> None:
        clean = (query or "").strip()
        if self._curriculum_search != clean:
            self._curriculum_search = clean
            self.changed.emit()

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        color = value.strip().lstrip("#")
        if len(color) != 6:
            return (59, 130, 246)
        return tuple(int(color[index : index + 2], 16) for index in range(0, 6, 2))

    def _subject_color_distance(self, left: str, right: str) -> float:
        left_rgb = self._hex_to_rgb(left)
        right_rgb = self._hex_to_rgb(right)
        return sum((left_rgb[index] - right_rgb[index]) ** 2 for index in range(3)) ** 0.5

    def generate_subject_color(self) -> str:
        with self._db() as db:
            existing = [
                str(color)
                for color in db.scalars(
                    select(Subject.color).where(func.coalesce(Subject.archived, 0) == 0)
                )
                if color
            ]
        for step in range(1, 360):
            hue = ((step * 137.508) % 360) / 360.0
            red, green, blue = hls_to_rgb(hue, 0.80, 0.52)
            candidate = f"#{round(red * 255):02X}{round(green * 255):02X}{round(blue * 255):02X}"
            if all(self._subject_color_distance(candidate, current) >= 28 for current in existing):
                return candidate
        return "#A7C5FF"

    @Slot(str, str)
    def addSubject(self, name: str, color: str | None = None) -> None:
        clean_name = name.strip()
        if not clean_name:
            self._toast_callback("error", "Subject Required", "Provide a subject name to continue.")
            return
        selected_color = color.strip() if color and color.strip() else self.generate_subject_color()
        with self._db() as db:
            SubjectService(db).create_subject(name=clean_name, color_tag=selected_color)
        self._on_intelligence_refresh(train=True)
        self._toast_callback("success", "Subject Created", f"{clean_name} was added.")
        self.changed.emit()

    @Slot(str)
    def deleteSubject(self, subject_id: str) -> None:
        subject_name = "Subject"
        with self._db() as db:
            subject = db.get(Subject, int(subject_id))
            if subject is not None:
                subject_name = subject.name
            SubjectService(db).delete_subject(subject_id)
        self._on_intelligence_refresh(train=True)
        self._toast_callback(
            "success", "Subject Deleted", f"{subject_name} and its topics were removed."
        )
        self.changed.emit()

    @Slot(str, str, str)
    def addTopic(self, subject_id: str, name: str, difficulty: str) -> None:
        level = DifficultyLevel((difficulty or "Medium").lower())
        clean_name = name.strip()
        with self._db() as db:
            TopicService(db, scheduler=self._scheduler(db)).create_topic(
                subject_id=subject_id, name=clean_name, difficulty=level
            )
        self._on_intelligence_refresh(train=True)
        self._toast_callback(
            "success", "Topic Added", f"{clean_name} was added to your curriculum."
        )
        self.changed.emit()

    @Slot(str)
    def deleteTopic(self, topic_id: str) -> None:
        topic_name = "Topic"
        with self._db() as db:
            topic = db.get(Topic, int(topic_id))
            if topic is not None:
                topic_name = topic.name
            TopicService(db, scheduler=self._scheduler(db)).delete_topic(topic_id)
        self._on_intelligence_refresh(train=True)
        self._toast_callback("success", "Topic Deleted", f"{topic_name} was removed.")
        self.changed.emit()

    @Slot(str, int)
    def updateTopicProgress(self, topic_id: str, progress: int) -> None:
        with self._db() as db:
            TopicService(db, scheduler=self._scheduler(db)).update_topic(
                topic_id, progress=progress
            )
        self._on_intelligence_refresh()
        self.changed.emit()
