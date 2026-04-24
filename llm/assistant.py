from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_BASE_URL = "http://localhost:11434"


@dataclass(frozen=True)
class AssistantContext:
    due_today: list[dict[str, Any]]
    overdue: list[dict[str, Any]]
    weak_subjects: list[dict[str, Any]]
    upcoming_reminders: list[dict[str, Any]]
    digest: dict[str, Any]


class OllamaClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, model: str = DEFAULT_MODEL, timeout: float = 0.2) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            with urlopen(f"{self.base_url}/api/tags", timeout=self.timeout) as response:
                return response.status == 200
        except (OSError, URLError, TimeoutError):
            return False

    def generate(self, prompt: str, context: AssistantContext) -> str:
        payload = {
            "model": self.model,
            "prompt": self._build_prompt(prompt, context),
            "stream": False,
        }
        request = Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=max(self.timeout, 10.0)) as response:
            result = json.loads(response.read().decode("utf-8"))
        return str(result.get("response", "")).strip()

    def stream(self, prompt: str, context: AssistantContext) -> Iterable[str]:
        answer = self.generate(prompt, context)
        for token in answer.split():
            yield token + " "

    def _build_prompt(self, prompt: str, context: AssistantContext) -> str:
        due = ", ".join(item["name"] for item in context.due_today[:5]) or "none"
        overdue = ", ".join(item["name"] for item in context.overdue[:5]) or "none"
        weak = ", ".join(f"{item['subject']} ({item['risk']} risk)" for item in context.weak_subjects[:5]) or "none"
        upcoming = ", ".join(f"{item['title']} at {item['when']}" for item in context.upcoming_reminders[:5]) or "none"
        return (
            "You are StudyFlow's local study assistant. Give concise, practical study guidance grounded only in this data.\n"
            f"Due today: {due}\n"
            f"Overdue: {overdue}\n"
            f"Weak subjects: {weak}\n"
            f"Upcoming reminders: {upcoming}\n"
            f"Digest: {context.digest.get('summary', '')}\n"
            f"Student question: {prompt}\n"
        )


class LLMService:
    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    def status(self) -> dict[str, Any]:
        available = self.client.is_available()
        return {
            "available": available,
            "model": self.client.model,
            "provider": "Ollama",
            "message": (
                f"Ollama is running with {self.client.model}."
                if available
                else "Ollama is not running. StudyFlow will use offline guidance until local LLM is available."
            ),
        }

    def answer(self, prompt: str, context: AssistantContext) -> dict[str, Any]:
        clean_prompt = prompt.strip()
        if not clean_prompt:
            return {"text": "Ask me what to study, what needs attention, or how to prepare for an exam.", "source": "offline"}

        if self.client.is_available():
            try:
                response = self.client.generate(clean_prompt, context)
                if response:
                    return {"text": response, "source": "ollama"}
            except (OSError, URLError, TimeoutError, json.JSONDecodeError):
                pass

        return {"text": self._offline_answer(clean_prompt, context), "source": "offline"}

    def stream_answer(self, prompt: str, context: AssistantContext) -> Iterable[str]:
        response = self.answer(prompt, context)["text"]
        for token in response.split():
            yield token + " "

    def _offline_answer(self, prompt: str, context: AssistantContext) -> str:
        prompt_lower = prompt.lower()
        overdue = context.overdue
        due_today = context.due_today
        weak_subjects = context.weak_subjects

        if "what should i study" in prompt_lower or "today" in prompt_lower:
            return self._study_today_answer(due_today, overdue, weak_subjects)
        if "attention" in prompt_lower or "weak" in prompt_lower or "subject" in prompt_lower:
            return self._attention_answer(weak_subjects, overdue)
        if "exam" in prompt_lower or "track" in prompt_lower:
            return self._exam_track_answer(context)
        if "explain" in prompt_lower:
            topic = self._best_topic_name(due_today, overdue)
            return (
                f"Start by writing what you remember about {topic}, then check gaps with your notes. "
                "Use one worked example, one recall question, and one quick self-test before rating confidence."
            )
        return self._study_today_answer(due_today, overdue, weak_subjects)

    def _study_today_answer(
        self,
        due_today: list[dict[str, Any]],
        overdue: list[dict[str, Any]],
        weak_subjects: list[dict[str, Any]],
    ) -> str:
        if overdue:
            subjects = []
            for item in overdue:
                subject = str(item.get("subject", ""))
                if subject and subject not in subjects:
                    subjects.append(subject)
            first = overdue[0]
            if len(subjects) >= 2:
                mixed = ", ".join(subjects[: min(3, len(subjects))])
                return (
                    f"Start with overdue review: {first['name']}. Then rotate across {mixed} instead of staying in one subject. "
                    "If time is tight, do one short recall block per subject before looping back."
                )
            return (
                f"Start with overdue review: {first['name']}. Spend 20-30 minutes on active recall, "
                "then rate it honestly. After that, move to the highest-urgency due-today card."
            )
        if due_today:
            first = due_today[0]
            subjects = []
            for item in due_today:
                subject = str(item.get("subject", ""))
                if subject and subject not in subjects:
                    subjects.append(subject)
            if len(subjects) >= 2:
                mixed = ", ".join(subjects[: min(3, len(subjects))])
                return (
                    f"Start with {first['name']}, then mix reviews across {mixed}. "
                    "When time is limited, take one topic from each subject before doing a second pass."
                )
            return (
                f"Start with {first['name']} because it is due today. Use a short recall pass, "
                "review mistakes, then finish with one confidence rating."
            )
        if weak_subjects:
            subject = weak_subjects[0]["subject"]
            return f"No urgent cards are due. Use a maintenance block on {subject}, your weakest current area."
        return "No urgent study items are queued. Add topics or do a light 15-minute review to keep momentum."

    def _attention_answer(self, weak_subjects: list[dict[str, Any]], overdue: list[dict[str, Any]]) -> str:
        if weak_subjects:
            top = weak_subjects[0]
            return (
                f"{top['subject']} needs the most attention. It is marked {top['risk']} risk with "
                f"{top['pct']}% confidence. Schedule two short review blocks and focus on low-confidence topics first."
            )
        if overdue:
            return f"Your biggest risk is overdue work. Clear {overdue[0]['name']} first, then reassess the dashboard."
        return "Your subject balance looks stable. Keep the current spaced-repetition cadence."

    def _exam_track_answer(self, context: AssistantContext) -> str:
        if context.upcoming_reminders:
            next_item = context.upcoming_reminders[0]
            return (
                f"Use {next_item['title']} as your next checkpoint. If it is exam-related, "
                "prioritize weak-topic recall first, then do timed practice."
            )
        return (
            "You look on track if you keep clearing due cards daily. For exams, convert each weak topic "
            "into a 25-minute active-recall block and review mistakes the next day."
        )

    def _best_topic_name(self, due_today: list[dict[str, Any]], overdue: list[dict[str, Any]]) -> str:
        if overdue:
            return str(overdue[0]["name"])
        if due_today:
            return str(due_today[0]["name"])
        return "the selected topic"
