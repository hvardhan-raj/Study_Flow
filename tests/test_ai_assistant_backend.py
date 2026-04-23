from studyflow_backend.service import StudyFlowBackend


def test_assistant_prompts_and_context_are_available(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "assistant_state.json")

    assert len(backend.assistantPrompts) == 4
    assert {"dueToday", "overdue", "weakSubjects", "nextTopic"} <= set(backend.assistantContextSummary)
    assert backend.assistantMessages[0]["role"] == "assistant"


def test_send_assistant_message_appends_user_and_assistant_messages(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "assistant_state.json")
    original_count = len(backend.assistantMessages)

    response = backend.sendAssistantMessage("What should I study today?")

    assert response["role"] == "assistant"
    assert response["source"] in {"offline", "ollama"}
    assert len(backend.assistantMessages) == original_count + 2
    assert backend.assistantMessages[-2]["role"] == "user"


def test_clear_assistant_chat_restores_intro_message(tmp_path) -> None:
    backend = StudyFlowBackend(tmp_path / "assistant_state.json")

    backend.sendAssistantMessage("Which subject needs attention?")
    backend.clearAssistantChat()

    assert len(backend.assistantMessages) == 1
    assert backend.assistantMessages[0]["role"] == "assistant"
