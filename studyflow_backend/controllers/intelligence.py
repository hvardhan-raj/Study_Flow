from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from studyflow_backend.ml_engine import LearningMLEngine
from time_utils import local_now

logger = logging.getLogger(__name__)


class IntelligenceController(QObject):
    changed = Signal()

    def __init__(
        self,
        ml_engine: LearningMLEngine,
        on_notification_added: Callable[[str, str, str, str], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._ml_engine = ml_engine
        self._on_notification_added = on_notification_added or (lambda t, b, i, c: None)

    @Property("QVariantMap", notify=changed)
    def intelligenceDashboard(self) -> dict[str, Any]:
        return self._ml_engine.get_intelligence_dashboard()

    @Slot()
    def refreshIntelligence(self) -> None:
        model_ready = self.intelligenceDashboard.get("model_ready", False)
        self._ml_engine.request_refresh(train=not model_ready)

    @Slot()
    def shutdown(self) -> None:
        self._ml_engine.stop()

    @Slot(str, result=str)
    def exportLearningReport(self, output_path: str | None = None) -> str:
        clean = (output_path or "").strip()
        if clean:
            target = Path(clean)
        else:
            from config.settings import settings

            target = settings.app_data_dir / "data" / "learning_report.txt"
        target.parent.mkdir(parents=True, exist_ok=True)

        dashboard = self.intelligenceDashboard
        lines = [
            "StudyFlow Learning Report",
            f"Generated: {local_now().strftime('%Y-%m-%d %H:%M')}",
            f"Retention Score: {dashboard.get('retention_score', 0)}%",
            f"Engine Mode: {dashboard.get('engine_mode', 'heuristic')}",
            "",
            "High Risk Topics:",
        ]
        for topic in dashboard.get("high_risk_topics", []):
            lines.append(f" - {topic.get('topic')}: Risk {topic.get('forgetting_risk')}")
        lines.append("")
        lines.append("Recommended Topics:")
        for topic in dashboard.get("recommended_topics", []):
            lines.append(f" - {topic.get('topic')}: Priority {topic.get('priority_score')}")

        target.write_text("\n".join(lines), encoding="utf-8")
        self._on_notification_added(
            "Report Exported",
            f"Exported learning report to {target.name}.",
            "R",
            "#10B981",
        )
        return str(target)
