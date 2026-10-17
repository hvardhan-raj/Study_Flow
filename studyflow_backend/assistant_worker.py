from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QThread, Signal

from llm import AssistantContext, LLMService

logger = logging.getLogger(__name__)


class AssistantWorker(QThread):
    """Background worker thread for generating LLM assistant responses without freezing Qt UI."""

    tokenReceived = Signal(str)
    responseReady = Signal(dict)
    finishedWithError = Signal(str)

    def __init__(
        self,
        llm_service: LLMService,
        prompt: str,
        context: AssistantContext,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._llm_service = llm_service
        self._prompt = prompt
        self._context = context

    def run(self) -> None:
        try:
            tokens: list[str] = []
            source = "offline"

            try:
                for token in self._llm_service.stream_answer(self._prompt, self._context):
                    tokens.append(token)
                    self.tokenReceived.emit(token)
                status = self._llm_service.status()
                source = "ollama" if status.get("available") and status.get("model") else "offline"
            except Exception:
                logger.debug("Falling back to synchronous answer in AssistantWorker")
                ans = self._llm_service.answer(self._prompt, self._context)
                full_text = ans.get("text", "")
                source = ans.get("source", "offline")
                tokens = [full_text]
                self.tokenReceived.emit(full_text)

            final_text = "".join(tokens).strip()
            self.responseReady.emit({"text": final_text, "source": source})
        except Exception as e:
            logger.exception("AssistantWorker encountered an unexpected error")
            self.finishedWithError.emit(str(e))
