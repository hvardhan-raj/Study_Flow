from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from PySide6.QtCore import Property, QCoreApplication, QObject, Signal, Slot

from llm import AssistantContext, LLMService
from studyflow_backend.assistant_worker import AssistantWorker
from time_utils import ensure_local_timezone, local_now

logger = logging.getLogger(__name__)


class AssistantController(QObject):
    changed = Signal()
    busyChanged = Signal(bool)
    messageFinished = Signal(dict)

    def __init__(
        self,
        llm_service: LLMService | None = None,
        context_provider: Callable[[list[dict[str, Any]] | None], AssistantContext] | None = None,
        due_topic_provider: Callable[[], str] | None = None,
        save_callback: Callable[[], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._llm_service = llm_service or LLMService()
        self._context_provider = context_provider or (
            lambda recent=None: AssistantContext([], [], [], [], {}, recent)
        )
        self._due_topic_provider = due_topic_provider or (lambda: "my next due topic")
        self._save_callback = save_callback or (lambda: None)
        self._assistant_status = self._llm_service.status()
        self._assistant_busy = False
        self._assistant_messages: list[dict[str, Any]] = self._default_assistant_messages()
        self._active_worker: AssistantWorker | None = None

    def initialize_state(self, messages: list[dict[str, Any]] | None) -> None:
        if messages:
            self._assistant_messages = [self._normalize_assistant_message(msg) for msg in messages]
        else:
            self._assistant_messages = self._default_assistant_messages()

    @property
    def messages_payload(self) -> list[dict[str, Any]]:
        return list(self._assistant_messages)

    def _default_assistant_messages(self) -> list[dict[str, Any]]:
        return [
            self._normalize_assistant_message(
                {
                    "role": "assistant",
                    "text": "I can help you plan today’s reviews.",
                    "source": "system",
                }
            )
        ]

    def _normalize_assistant_message(self, message: dict[str, Any]) -> dict[str, Any]:
        item = dict(message)
        item.setdefault("role", "assistant")
        item.setdefault("text", "")
        item.setdefault("source", "offline")
        timestamp = item.get("timestamp")
        if isinstance(timestamp, datetime):
            parsed_timestamp = timestamp
        elif isinstance(timestamp, str):
            try:
                parsed_timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                parsed_timestamp = local_now()
        else:
            parsed_timestamp = local_now()
        item["timestamp"] = ensure_local_timezone(parsed_timestamp).isoformat()
        item["time"] = parsed_timestamp.strftime("%H:%M")
        return item

    @Property("QVariantMap", notify=changed)
    def assistantStatus(self) -> dict[str, Any]:
        return self._assistant_status

    @Property("QVariantList", notify=changed)
    def assistantMessages(self) -> list[dict[str, Any]]:
        return self._assistant_messages

    @Property("QVariantList", constant=True)
    def assistantPrompts(self) -> list[dict[str, str]]:
        due_topic = self._due_topic_provider()
        return [
            {"label": "Study Today", "prompt": "What should I study today?"},
            {"label": "Explain Topic", "prompt": f"Explain {due_topic} with a quick recall plan."},
            {"label": "Weak Areas", "prompt": "Which subject needs attention?"},
            {"label": "Exam Track", "prompt": "Am I on track for my exam?"},
        ]

    @Property("QVariantMap", notify=changed)
    def assistantContextSummary(self) -> dict[str, Any]:
        context = self._context_provider(None)
        return {
            "dueToday": len(context.due_today),
            "overdue": len(context.overdue),
            "weakSubjects": len(
                [item for item in context.weak_subjects if item.get("risk") != "Low"]
            ),
            "nextTopic": (
                context.overdue[0]["name"]
                if context.overdue
                else (context.due_today[0]["name"] if context.due_today else "No due topics")
            ),
        }

    @Property(bool, notify=busyChanged)
    def assistantBusy(self) -> bool:
        return self._assistant_busy

    def _set_busy(self, busy: bool) -> None:
        if self._assistant_busy != busy:
            self._assistant_busy = busy
            self.busyChanged.emit(busy)

    @Slot(str, result="QVariantMap")
    def sendAssistantMessage(self, prompt: str, async_exec: bool | None = None) -> dict[str, Any]:
        clean = prompt.strip()
        if not clean:
            return {"text": "", "source": "empty"}

        user_message = self._normalize_assistant_message(
            {"role": "user", "text": clean, "source": "user"}
        )
        self._assistant_messages.append(user_message)

        is_gui = QCoreApplication.instance() is not None
        use_async = is_gui if async_exec is None else async_exec

        if not use_async:
            context = self._context_provider(self._assistant_messages[-6:])
            response = self._llm_service.answer(clean, context)
            self._assistant_status = self._llm_service.status()
            assistant_message = self._normalize_assistant_message(
                {
                    "role": "assistant",
                    "text": response["text"],
                    "source": response["source"],
                }
            )
            self._assistant_messages.append(assistant_message)
            self._assistant_messages = self._assistant_messages[-40:]
            self._save_callback()
            self.changed.emit()
            return assistant_message

        # Async streaming execution via QThread
        self._set_busy(True)
        placeholder_message = self._normalize_assistant_message(
            {"role": "assistant", "text": "...", "source": "generating"}
        )
        self._assistant_messages.append(placeholder_message)
        self.changed.emit()

        context = self._context_provider(self._assistant_messages[-7:-1])
        worker = AssistantWorker(self._llm_service, clean, context, parent=self)
        self._active_worker = worker

        def _on_token(token: str) -> None:
            if self._assistant_messages and self._assistant_messages[-1]["role"] == "assistant":
                current_text = self._assistant_messages[-1]["text"]
                if current_text == "...":
                    self._assistant_messages[-1]["text"] = token
                else:
                    self._assistant_messages[-1]["text"] += token
                self.changed.emit()

        def _on_response_ready(payload: dict[str, Any]) -> None:
            if self._assistant_messages and self._assistant_messages[-1]["role"] == "assistant":
                self._assistant_messages[-1]["text"] = payload.get("text", "")
                self._assistant_messages[-1]["source"] = payload.get("source", "offline")
            self._assistant_status = self._llm_service.status()
            self._assistant_messages = self._assistant_messages[-40:]
            self._set_busy(False)
            self._save_callback()
            self.changed.emit()
            self.messageFinished.emit(payload)

        def _on_error(err_msg: str) -> None:
            logger.error("Assistant generation error: %s", err_msg)
            if self._assistant_messages and self._assistant_messages[-1]["role"] == "assistant":
                self._assistant_messages[-1]["text"] = "I had trouble generating a response."
                self._assistant_messages[-1]["source"] = "error"
            self._set_busy(False)
            self._save_callback()
            self.changed.emit()

        worker.tokenReceived.connect(_on_token)
        worker.responseReady.connect(_on_response_ready)
        worker.finishedWithError.connect(_on_error)
        worker.start()
        return placeholder_message

    @Slot()
    def clearAssistantChat(self) -> None:
        self._assistant_messages = self._default_assistant_messages()
        self._save_callback()
        self.changed.emit()
