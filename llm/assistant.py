from __future__ import annotations

import json
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_BASE_URL = "http://localhost:11434"
MODEL_LIST_CACHE_TTL_SECONDS = 3.0


@dataclass(frozen=True)
class AssistantContext:
    due_today: list[dict[str, Any]]
    overdue: list[dict[str, Any]]
    weak_subjects: list[dict[str, Any]]
    upcoming_reminders: list[dict[str, Any]]
    digest: dict[str, Any]
    recent_messages: list[dict[str, Any]] | None = None


class OllamaClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, model: str = DEFAULT_MODEL, timeout: float = 1.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._models_cache: list[str] = []
        self._models_cache_at = 0.0

    def list_models(self, force_refresh: bool = False) -> list[str]:
        if not force_refresh and (time.monotonic() - self._models_cache_at) < MODEL_LIST_CACHE_TTL_SECONDS:
            return list(self._models_cache)
        try:
            with urlopen(f"{self.base_url}/api/tags", timeout=self.timeout) as response:
                if response.status != 200:
                    self._models_cache = []
                    self._models_cache_at = time.monotonic()
                    return []
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError):
            self._models_cache = []
            self._models_cache_at = time.monotonic()
            return []
        except json.JSONDecodeError:
            self._models_cache = []
            self._models_cache_at = time.monotonic()
            return []
        models = payload.get("models", [])
        self._models_cache = [str(item.get("name", "")).strip() for item in models if str(item.get("name", "")).strip()]
        self._models_cache_at = time.monotonic()
        return list(self._models_cache)

    def is_available(self) -> bool:
        return bool(self.list_models())

    def has_model(self) -> bool:
        models = self.list_models()
        return self.model in models

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
        try:
            answer = self.generate(prompt, context)
        except (OSError, URLError, TimeoutError, json.JSONDecodeError):
            answer = ""
        for token in answer.split():
            yield token + " "

    def _build_prompt(self, prompt: str, context: AssistantContext) -> str:
        def format_list(items, formatter):
            return "\n".join(f"- {formatter(item)}" for item in items[:5]) or "- none"

        due = format_list(
            context.due_today,
            lambda x: f"{x['name']} ({x.get('subject', 'no subject')}, {x.get('scheduledText', 'today')}, status={x.get('status', 'due')})",
        )
        overdue = format_list(
            context.overdue,
            lambda x: f"{x['name']} ({x.get('subject', 'no subject')}, {x.get('scheduledText', 'overdue')}, status={x.get('status', 'overdue')})",
        )
        weak = format_list(
            context.weak_subjects,
            lambda x: f"{x['subject']} — {x['risk']} risk, {x.get('pct', '?')}% confidence",
        )
        upcoming = format_list(
            context.upcoming_reminders,
            lambda x: f"{x['title']} at {x['when']}",
        )
        history = format_list(
            context.recent_messages or [],
            lambda x: f"{x.get('role', 'assistant')}: {str(x.get('text', '')).strip()}",
        )

        return f"""
You are StudyFlow’s intelligent study assistant.

Your job is to give specific, context-aware study guidance using ONLY the provided data.

---------------------
CONTEXT

Due Today:
{due}

Overdue:
{overdue}

Weak Subjects:
{weak}

Upcoming Reminders:
{upcoming}

Digest:
{context.digest.get('summary', 'none')}

Recent Chat:
{history}

---------------------
STUDENT QUESTION
{prompt.strip()}

---------------------
INSTRUCTIONS

- Use ONLY the context above (do not invent topics)
- Prioritize in this order:
  1. Overdue items
  2. Due today
  3. Weak subjects
- Mention concrete topic names, subjects, or reminders from the context whenever possible
- Give practical study steps, sequencing, and time-boxes
- Keep response compact but useful (3 to 5 bullets)

---------------------
OUTPUT FORMAT

- Priority: ...
- Next: ...
- Then: ...
- Watch out: ...
(- Optional: Why)

---------------------
AVOID

- Generic advice (e.g., "study regularly")
- Long explanations
- Repeating the question
"""


class LLMService:
    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    def _available_models(self) -> list[str]:
        if hasattr(self.client, "list_models"):
            models = self.client.list_models()
            return [str(model).strip() for model in models if str(model).strip()]
        if hasattr(self.client, "has_model") and self.client.has_model():
            return [str(self.client.model)]
        if hasattr(self.client, "is_available") and self.client.is_available():
            return ["available"]
        return []

    def status(self) -> dict[str, Any]:
        models = self._available_models()
        available = bool(models)
        has_model = str(self.client.model) in models if models else False
        if models == ["available"]:
            has_model = hasattr(self.client, "has_model") and self.client.has_model()
        status_message = "Ollama is not running. StudyFlow will use offline guidance until local LLM is available."
        if available and has_model:
            status_message = f"Ollama is running with {self.client.model}."
        elif available:
            status_message = f"Ollama is running, but model {self.client.model} is not installed. StudyFlow is using offline guidance."
        return {
            "available": available and has_model,
            "model": self.client.model,
            "provider": "Ollama",
            "message": status_message,
        }

    def answer(self, prompt: str, context: AssistantContext) -> dict[str, Any]:
        clean_prompt = prompt.strip()
        if not clean_prompt:
            return {"text": "Ask me what to study, what needs attention, or how to prepare for an exam.", "source": "offline"}

        if self.client.has_model():
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

        if any(phrase in prompt_lower for phrase in ("what should i study", "study today", "today", "next", "start with")):
            return self._study_today_answer(due_today, overdue, weak_subjects)
        if any(phrase in prompt_lower for phrase in ("attention", "weak", "subject", "struggling", "behind", "focus on")):
            return self._attention_answer(weak_subjects, overdue)
        if any(phrase in prompt_lower for phrase in ("exam", "track", "checkpoint", "test", "midterm", "final")):
            return self._exam_track_answer(context)
        if any(phrase in prompt_lower for phrase in ("explain", "revise", "recall plan", "review this", "teach me")):
            topic = self._extracted_topic_name(prompt) or self._best_topic_name(due_today, overdue)
            return self._topic_coaching_answer(topic, context)
        return self._general_coaching_answer(context)

    def _study_today_answer(
        self,
        due_today: list[dict[str, Any]],
        overdue: list[dict[str, Any]],
        weak_subjects: list[dict[str, Any]],
    ) -> str:
        if overdue:
            first = overdue[0]
            next_due = due_today[0]["name"] if due_today else "your next due topic"
            weak_subject = weak_subjects[0]["subject"] if weak_subjects else first.get("subject", "that area")
            return "\n".join(
                [
                    f"- Priority: clear overdue review `{first['name']}` first because overdue items are the highest risk.",
                    f"- Next: spend 20 minutes on recall only, then check errors and rate confidence before switching to `{next_due}`.",
                    f"- Then: add one short reinforcement block for `{weak_subject}` so the same gap does not repeat tomorrow.",
                    "- Watch out: do not open new material until the overdue item is closed.",
                ]
            )
        if due_today:
            first = due_today[0]
            subject_names = [str(item.get("subject", "")).strip() for item in due_today if str(item.get("subject", "")).strip()]
            mixed = ", ".join(list(dict.fromkeys(subject_names))[:3]) or str(first.get("subject", "your due subjects"))
            return "\n".join(
                [
                    f"- Priority: start with `{first['name']}` because it is already due today.",
                    f"- Next: do a 15-minute recall pass, then mark mistakes before moving across `{mixed}`.",
                    "- Then: finish a second short pass only on the topics you could not answer cleanly.",
                    "- Watch out: if time is limited, breadth first is better than spending everything on one easy topic.",
                ]
            )
        if weak_subjects:
            subject = weak_subjects[0]["subject"]
            return "\n".join(
                [
                    f"- Priority: no urgent cards are due, so use a maintenance block on `{subject}`.",
                    "- Next: pick one low-confidence topic in that subject and do recall before rereading notes.",
                    "- Then: log a confidence rating so the next schedule update has better signal.",
                ]
            )
        return "\n".join(
            [
                "- Priority: there are no urgent study items queued right now.",
                "- Next: add topics or schedule one 15-minute review block to keep the streak active.",
                "- Then: ask for a topic explanation once you have a concrete item loaded into the planner.",
            ]
        )

    def _attention_answer(self, weak_subjects: list[dict[str, Any]], overdue: list[dict[str, Any]]) -> str:
        if weak_subjects:
            top = weak_subjects[0]
            overdue_hint = f" You also have overdue work in `{overdue[0]['name']}`." if overdue else ""
            return "\n".join(
                [
                    f"- Priority: `{top['subject']}` needs the most attention because it is marked `{top['risk']}` risk at {top['pct']}% confidence.{overdue_hint}",
                    f"- Next: schedule two short blocks for `{top['subject']}` and start with the lowest-confidence topic, not the easiest one.",
                    "- Then: retest from memory after each block instead of only rereading notes.",
                ]
            )
        if overdue:
            return "\n".join(
                [
                    f"- Priority: your biggest risk is overdue work, starting with `{overdue[0]['name']}`.",
                    "- Next: clear the overdue queue before rebalancing subjects.",
                    "- Then: reassess weak areas after the backlog is smaller.",
                ]
            )
        return "\n".join(
            [
                "- Priority: your subject balance looks stable right now.",
                "- Next: keep the current spaced-repetition cadence and review whichever topic becomes due first.",
            ]
        )

    def _exam_track_answer(self, context: AssistantContext) -> str:
        weak_subject = context.weak_subjects[0]["subject"] if context.weak_subjects else "your weakest subject"
        if context.upcoming_reminders:
            next_item = context.upcoming_reminders[0]
            return "\n".join(
                [
                    f"- Priority: use `{next_item['title']}` as the next checkpoint for exam readiness.",
                    f"- Next: clear overdue and due-today reviews before doing timed practice on `{weak_subject}`.",
                    "- Then: convert mistakes into tomorrow's first recall block instead of leaving them inside notes.",
                ]
            )
        return "\n".join(
            [
                "- Priority: you are broadly on track if you keep clearing due cards daily.",
                f"- Next: turn `{weak_subject}` into a 25-minute active-recall block and follow it with one timed check.",
                "- Then: review the mistakes the next day so exam prep compounds instead of resetting.",
            ]
        )

    def _topic_coaching_answer(self, topic: str, context: AssistantContext) -> str:
        related_subject = self._topic_subject(topic, context) or "the current subject"
        next_due = self._best_topic_name(context.due_today, context.overdue)
        return "\n".join(
            [
                f"- Priority: explain `{topic}` by writing everything you remember before checking notes.",
                f"- Next: in `{related_subject}`, do one worked example, one recall question, and one mini self-test on `{topic}`.",
                f"- Then: compare it with `{next_due}` if that is the next scheduled review so your revision stays aligned with the queue.",
                "- Watch out: if you need to reread immediately, the recall step is too shallow and should be repeated.",
            ]
        )

    def _general_coaching_answer(self, context: AssistantContext) -> str:
        if context.overdue or context.due_today or context.weak_subjects:
            return self._study_today_answer(context.due_today, context.overdue, context.weak_subjects)
        return "\n".join(
            [
                "- Priority: your study queue is light, so the assistant has limited live context to work with.",
                "- Next: add a topic, schedule a review, or ask about a specific subject for a more precise answer.",
            ]
        )

    def _best_topic_name(self, due_today: list[dict[str, Any]], overdue: list[dict[str, Any]]) -> str:
        if overdue:
            return str(overdue[0]["name"])
        if due_today:
            return str(due_today[0]["name"])
        return "the selected topic"

    def _topic_subject(self, topic: str, context: AssistantContext) -> str:
        target = topic.strip().lower()
        for pool in (context.overdue, context.due_today):
            for item in pool:
                if str(item.get("name", "")).strip().lower() == target:
                    return str(item.get("subject", "")).strip()
        return ""

    def _extracted_topic_name(self, prompt: str) -> str:
        match = re.match(r"\s*explain\s+(.+?)(?:\s+with\s+a\s+quick\s+recall\s+plan\.?)?\s*$", prompt, re.IGNORECASE)
        if not match:
            return ""
        return match.group(1).strip() or ""
