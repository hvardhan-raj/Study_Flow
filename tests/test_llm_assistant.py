from llm import AssistantContext, LLMService


class FakeClient:
    model = "fake-model"

    def __init__(self, available: bool, response: str = "") -> None:
        self.available = available
        self.response = response
        self.prompts: list[str] = []

    def is_available(self) -> bool:
        return self.available

    def generate(self, prompt: str, context: AssistantContext) -> str:
        self.prompts.append(prompt)
        return self.response


def test_llm_service_uses_offline_guidance_when_ollama_unavailable() -> None:
    service = LLMService(client=FakeClient(False))
    context = AssistantContext(
        due_today=[{"name": "Photosynthesis"}],
        overdue=[],
        weak_subjects=[],
        upcoming_reminders=[],
        digest={"summary": "1 review due"},
    )

    response = service.answer("What should I study today?", context)

    assert response["source"] == "offline"
    assert "Photosynthesis" in response["text"]


def test_llm_service_uses_ollama_when_available() -> None:
    service = LLMService(client=FakeClient(True, "Use active recall first."))
    context = AssistantContext([], [], [], [], {})

    response = service.answer("Help me", context)

    assert response == {"text": "Use active recall first.", "source": "ollama"}


def test_llm_status_reports_offline_setup_guidance() -> None:
    service = LLMService(client=FakeClient(False))

    status = service.status()

    assert status["available"] is False
    assert status["provider"] == "Ollama"
    assert "offline guidance" in status["message"]
