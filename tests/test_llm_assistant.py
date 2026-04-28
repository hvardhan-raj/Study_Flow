from llm import AssistantContext, LLMService


class FakeClient:
    model = "fake-model"

    def __init__(self, available: bool, response: str = "", has_model: bool | None = None) -> None:
        self.available = available
        self.response = response
        self._has_model = available if has_model is None else has_model
        self.prompts: list[str] = []

    def is_available(self) -> bool:
        return self.available

    def has_model(self) -> bool:
        return self._has_model

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


def test_llm_status_reports_missing_model_when_ollama_is_running_without_target_model() -> None:
    service = LLMService(client=FakeClient(True, has_model=False))

    status = service.status()

    assert status["available"] is False
    assert "not installed" in status["message"]


def test_llm_status_reports_offline_setup_guidance() -> None:
    service = LLMService(client=FakeClient(False))

    status = service.status()

    assert status["available"] is False
    assert status["provider"] == "Ollama"
    assert "offline guidance" in status["message"]


def test_llm_service_handles_all_canned_assistant_prompts_offline() -> None:
    service = LLMService(client=FakeClient(False))
    context = AssistantContext(
        due_today=[{"name": "Photosynthesis", "subject": "Biology"}],
        overdue=[{"name": "Kinematics Review", "subject": "Physics"}],
        weak_subjects=[{"subject": "Physics", "risk": "High", "pct": 42}],
        upcoming_reminders=[{"title": "Midterm checkpoint", "when": "Tomorrow 09:00"}],
        digest={"summary": "1 overdue, 1 due today"},
    )

    prompts = {
        "What should I study today?": "Kinematics Review",
        "Explain Photosynthesis with a quick recall plan.": "Photosynthesis",
        "Which subject needs attention?": "Physics",
        "Am I on track for my exam?": "Midterm checkpoint",
    }

    for prompt, expected in prompts.items():
        response = service.answer(prompt, context)
        assert response["source"] == "offline"
        assert expected in response["text"]
        assert "-" in response["text"]
