from __future__ import annotations

import json
import os
import random
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

DEFAULT_MODEL = os.getenv("STUDYFLOW_OLLAMA_MODEL", "llama3.2:3b")
DEFAULT_BASE_URL = os.getenv("STUDYFLOW_OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_LIST_CACHE_TTL_SECONDS = 3.0

Intent = Literal[
    "study_plan",
    "diagnosis",
    "exam_readiness",
    "topic_explain",
    "quiz",
    "progress",
    "motivation",
    "general",
]

Tone = Literal[
    "direct",
    "analytical",
    "coach",
    "timetable",
    "reassuring",
    "concise",
]


@dataclass(frozen=True)
class AssistantContext:
    due_today: list[dict[str, Any]]
    overdue: list[dict[str, Any]]
    weak_subjects: list[dict[str, Any]]
    upcoming_reminders: list[dict[str, Any]]
    digest: dict[str, Any]
    recent_messages: list[dict[str, Any]] | None = None


class AssistantClient(Protocol):
    model: str

    def generate(self, prompt: str, context: AssistantContext) -> str: ...

    def has_model(self) -> bool: ...

    def is_available(self) -> bool: ...

    def list_models(self, force_refresh: bool = False) -> list[str]: ...

    def effective_model(self) -> str: ...


class OllamaClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._models_cache: list[str] = []
        self._models_cache_at = 0.0

    def effective_model(self) -> str:
        models = self.list_models()
        if self.model in models:
            return self.model
        return models[0] if models else ""

    def list_models(self, force_refresh: bool = False) -> list[str]:
        if not force_refresh and (time.monotonic() - self._models_cache_at) < MODEL_LIST_CACHE_TTL_SECONDS:
            return list(self._models_cache)

        try:
            with urlopen(f"{self.base_url}/api/tags", timeout=self.timeout) as response:
                if response.status != 200:
                    return self._cache_models([])
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError):
            return self._cache_models([])

        models = payload.get("models", [])
        names = [
            str(item.get("name", "")).strip()
            for item in models
            if str(item.get("name", "")).strip()
        ]
        return self._cache_models(names)

    def _cache_models(self, models: list[str]) -> list[str]:
        self._models_cache = models
        self._models_cache_at = time.monotonic()
        return list(self._models_cache)

    def is_available(self) -> bool:
        return bool(self.list_models())

    def has_model(self) -> bool:
        return self.model in self.list_models()

    def generate(self, prompt: str, context: AssistantContext) -> str:
        intent = ResponsePlanner.detect_intent(prompt)
        tone = ResponsePlanner.pick_tone(intent, context)
        built_prompt = self._build_prompt(prompt, context, intent=intent, tone=tone)
        model_name = self.effective_model() or self.model

        payload = {
            "model": model_name,
            "prompt": built_prompt,
            "stream": False,
            "options": {
                "temperature": 0.75,
                "top_p": 0.9,
                "repeat_penalty": 1.18,
            },
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

    def _build_prompt(
        self,
        prompt: str,
        context: AssistantContext,
        intent: Intent,
        tone: Tone,
    ) -> str:
        def format_list(items: list[dict[str, Any]], formatter) -> str:
            return "\n".join(f"- {formatter(item)}" for item in items[:6]) or "- none"

        due = format_list(
            context.due_today,
            lambda x: (
                f"{x.get('name', 'unknown')} "
                f"({x.get('subject', 'no subject')}, "
                f"{x.get('scheduledText', 'today')}, "
                f"status={x.get('status', 'due')})"
            ),
        )

        overdue = format_list(
            context.overdue,
            lambda x: (
                f"{x.get('name', 'unknown')} "
                f"({x.get('subject', 'no subject')}, "
                f"{x.get('scheduledText', 'overdue')}, "
                f"status={x.get('status', 'overdue')})"
            ),
        )

        weak = format_list(
            context.weak_subjects,
            lambda x: (
                f"{x.get('subject', 'unknown')} — "
                f"{x.get('risk', 'unknown')} risk, "
                f"{x.get('pct', '?')}% confidence"
            ),
        )

        upcoming = format_list(
            context.upcoming_reminders,
            lambda x: f"{x.get('title', 'reminder')} at {x.get('when', 'soon')}",
        )

        history = format_list(
            context.recent_messages or [],
            lambda x: f"{x.get('role', 'assistant')}: {str(x.get('text', '')).strip()}",
        )

        return f"""
You are StudyFlow’s intelligent study assistant.

Use ONLY the provided context. Do not invent subjects, deadlines, topics, marks, or exam dates.

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
DETECTED INTENT
{intent}

RESPONSE TONE
{tone}

---------------------
RESPONSE RULES

1. Adapt the structure to the question. Do NOT always use the same bullet pattern.
2. Avoid repeating the same opening or wording from Recent Chat.
3. Do NOT always start with "Priority".
4. Do NOT always use "Next", "Then", and "Watch out".
5. Prefer concrete topic names from context.
6. Keep the answer useful but natural. Length can vary:
   - simple question: 1-3 short paragraphs
   - plan request: timetable or checklist
   - diagnosis request: verdict + reason
   - topic explanation: simple explanation + recall check
   - exam readiness: honest status + recovery move
   - quiz request: ask 1 question at a time
7. If there is overdue work, acknowledge it, but do not repeat the same overdue sentence every time.
8. If the user asks emotionally, answer like a supportive coach, not a report.
9. If the user asks analytically, answer with reasoning.
10. Never give generic advice like "study regularly".

---------------------
FORMAT IDEAS

Use whichever format fits. Do not use all of them.

For study plan:
"Next 45 minutes:
0-20 min: ...
20-35 min: ...
35-45 min: ..."

For diagnosis:
"Verdict: ...
Reason: ...
Best move: ..."

For exam readiness:
"You're not off track, but ...
Main risk: ...
Recovery move: ..."

For motivation:
"You're not failing. The issue is ...
Do this one thing now: ..."

For topic explanation:
"Simple idea:
...
Recall check:
..."

For quiz:
Ask only one question and wait for the student answer.

Now answer naturally.
"""


class ResponsePlanner:
    @staticmethod
    def detect_intent(prompt: str) -> Intent:
        p = prompt.lower().strip()

        if any(x in p for x in ("quiz", "test me", "ask me", "mcq", "question me")):
            return "quiz"

        if any(x in p for x in ("explain", "teach", "what is", "revise", "concept", "help me understand")):
            return "topic_explain"

        if any(x in p for x in ("am i on track", "on track", "behind", "can i recover", "will i pass", "exam", "final", "midterm", "checkpoint")):
            return "exam_readiness"

        if any(x in p for x in ("improving", "progress", "better than before", "trend", "performance")):
            return "progress"

        if any(x in p for x in ("weak", "attention", "struggling", "lowest confidence", "focus on", "problem area")):
            return "diagnosis"

        if any(x in p for x in ("what should i study", "study today", "study now", "start with", "today", "next")):
            return "study_plan"

        if any(x in p for x in ("stressed", "scared", "panic", "demotivated", "tired", "give up", "cooked")):
            return "motivation"

        return "general"

    @staticmethod
    def pick_tone(intent: Intent, context: AssistantContext) -> Tone:
        overdue_count = len(context.overdue)

        if intent == "study_plan":
            return random.choice(["timetable", "direct", "concise"])

        if intent == "diagnosis":
            return random.choice(["analytical", "direct"])

        if intent == "exam_readiness":
            if overdue_count >= 5:
                return random.choice(["direct", "coach"])
            return random.choice(["analytical", "reassuring"])

        if intent == "topic_explain":
            return random.choice(["coach", "concise"])

        if intent == "quiz":
            return "concise"

        if intent == "progress":
            return random.choice(["analytical", "reassuring"])

        if intent == "motivation":
            return random.choice(["coach", "reassuring"])

        return random.choice(["direct", "coach", "concise"])


class LLMService:
    def __init__(self, client: AssistantClient | None = None) -> None:
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

    def _effective_model(self) -> str:
        if hasattr(self.client, "effective_model"):
            model = str(self.client.effective_model()).strip()
            if model:
                return model

        models = self._available_models()
        preferred_model = str(getattr(self.client, "model", "")).strip()
        if preferred_model and preferred_model in models:
            return preferred_model
        if models:
            return models[0]
        if hasattr(self.client, "has_model") and self.client.has_model():
            return preferred_model
        return ""

    def status(self) -> dict[str, Any]:
        models = self._available_models()
        preferred_model = str(getattr(self.client, "model", "")).strip()
        effective_model = self._effective_model()
        available = bool(effective_model)
        has_model = preferred_model in models if models else False

        if models == ["available"]:
            has_model = hasattr(self.client, "has_model") and self.client.has_model()
            available = has_model
            effective_model = preferred_model if has_model else ""

        status_message = "Ollama is not running. StudyFlow will use offline guidance until local LLM is available."

        if available and has_model:
            status_message = f"Ollama is running with {effective_model}."
        elif available and effective_model:
            status_message = (
                f"Ollama is running, but model {preferred_model} is not installed. "
                f"StudyFlow is using {effective_model} instead."
            )

        return {
            "available": available,
            "model": effective_model or preferred_model,
            "provider": "Ollama",
            "message": status_message,
        }

    def answer(self, prompt: str, context: AssistantContext) -> dict[str, Any]:
        clean_prompt = prompt.strip()

        if not clean_prompt:
            return {
                "text": "Ask me what to study, what feels weak, or how ready you are for the exam.",
                "source": "offline",
            }

        if self._effective_model() or self.client.has_model():
            try:
                response = self.client.generate(clean_prompt, context)
                response = self._clean_response(response)

                if response:
                    return {"text": response, "source": "ollama"}

            except (OSError, URLError, TimeoutError, json.JSONDecodeError):
                pass

        return {
            "text": self._offline_answer(clean_prompt, context),
            "source": "offline",
        }

    def stream_answer(self, prompt: str, context: AssistantContext) -> Iterable[str]:
        response = self.answer(prompt, context)["text"]

        for token in response.split():
            yield token + " "

    def _offline_answer(self, prompt: str, context: AssistantContext) -> str:
        intent = ResponsePlanner.detect_intent(prompt)
        tone = ResponsePlanner.pick_tone(intent, context)

        if intent == "study_plan":
            return self._study_plan_answer(context, tone)

        if intent == "diagnosis":
            return self._diagnosis_answer(context, tone)

        if intent == "exam_readiness":
            return self._exam_readiness_answer(context, tone)

        if intent == "topic_explain":
            topic = self._extracted_topic_name(prompt) or self._best_topic_name(context)
            return self._topic_explain_answer(topic, context, tone)

        if intent == "quiz":
            topic = self._extracted_topic_name(prompt) or self._best_topic_name(context)
            return self._quiz_answer(topic, context)

        if intent == "progress":
            return self._progress_answer(context, tone)

        if intent == "motivation":
            return self._motivation_answer(context, tone)

        return self._general_answer(context, tone)

    def _study_plan_answer(self, context: AssistantContext, tone: Tone) -> str:
        topic = self._best_topic_name(context)
        subject = self._topic_subject(topic, context) or self._top_weak_subject(context)
        has_overdue = bool(context.overdue)

        if tone == "timetable":
            intro = "Use this as your next study block:"
            if has_overdue:
                intro = "Clear the backlog first. New topics can wait."

            return (
                f"{intro}\n\n"
                f"Next 45 minutes:\n"
                f"0-20 min: Recall `{topic}` without notes\n"
                f"20-30 min: Check mistakes and mark weak points\n"
                f"30-40 min: Redo only the parts you missed\n"
                f"40-45 min: Rate confidence for `{subject}`\n\n"
                "Stop after the block and update the planner."
            )

        if has_overdue:
            return (
                f"Start with `{topic}`. It is more urgent than opening anything new.\n\n"
                "- Do one recall pass, check mistakes, and only then decide the next topic.\n"
                "- The goal is not to study more; it is to remove the oldest risk first."
            )

        return (
            f"Start with `{topic}` from `{subject}`.\n\n"
            "Keep it short: recall first, notes second, test last. "
            "That gives better signal than rereading for a long time."
        )

    def _diagnosis_answer(self, context: AssistantContext, tone: Tone) -> str:
        weak = context.weak_subjects[0] if context.weak_subjects else None
        overdue = context.overdue[0] if context.overdue else None

        if weak:
            subject = weak.get("subject", "your weak subject")
            risk = weak.get("risk", "unknown")
            pct = weak.get("pct", "?")
            overdue_note = (
                f" You also have overdue work in `{overdue.get('name', 'an overdue topic')}`."
                if overdue
                else ""
            )

            if tone == "analytical":
                return (
                    f"Verdict: `{subject}` needs the most attention.\n\n"
                    f"- Reason: it is marked `{risk}` risk with {pct}% confidence."
                    f"{overdue_note}\n\n"
                    "- Best move: do a recall test before notes. If recall fails, schedule a second small block today."
                )

            return (
                f"Focus on `{subject}` first.\n\n"
                f"- Signal: {pct}% confidence and `{risk}` risk.\n"
                "- Best move: do not pick the easiest chapter just to feel productive."
            )

        if overdue:
            return (
                f"Your weak area is not a subject right now; it is backlog.\n\n"
                f"Start with `{overdue.get('name')}` and clear the oldest overdue review before judging subject strength."
            )

        return (
            "No clear weak subject is visible from the current data.\n\n"
            "Add confidence ratings after your next recall block, then the assistant can identify a real weak area."
        )

    def _exam_readiness_answer(self, context: AssistantContext, tone: Tone) -> str:
        overdue_count = len(context.overdue)
        due_count = len(context.due_today)
        weak_subject = self._top_weak_subject(context)
        checkpoint = (
            str(context.upcoming_reminders[0].get("title", "your next checkpoint"))
            if context.upcoming_reminders
            else "your next checkpoint"
        )

        if overdue_count:
            if tone == "direct":
                return (
                    "You are not off track yet, but the backlog is the danger.\n\n"
                    f"Current risk: {overdue_count} overdue review(s), {due_count} due today, "
                    f"and `{weak_subject}` is the weakest area.\n\n"
                    f"- Checkpoint: `{checkpoint}`.\n"
                    "- Recovery move: clear overdue recall first, then attempt timed practice. "
                    "Doing timed practice before fixing recall will give noisy results."
                )

            return (
                "You can recover, but only if today is a cleanup day.\n\n"
                f"Main issue: {overdue_count} overdue review(s).\n"
                f"Weakest area: `{weak_subject}`.\n\n"
                f"- Checkpoint: `{checkpoint}`.\n"
                "- Your exam prep should focus on stabilizing memory before adding new material."
            )

        return (
            "You look reasonably on track from the current queue.\n\n"
            f"- Checkpoint: `{checkpoint}`.\n"
            f"Keep one recall block for `{weak_subject}`, then do a small timed check. "
            "The main goal now is consistency, not panic studying."
        )

    def _topic_explain_answer(self, topic: str, context: AssistantContext, tone: Tone) -> str:
        subject = self._topic_subject(topic, context) or "this subject"

        return (
            f"Before I explain `{topic}`, try this quick recall setup:\n\n"
            f"- Write what you already remember about `{topic}` in 3 lines.\n"
            f"- Compare it with your notes from `{subject}`.\n"
            "- Mark the first point where your memory breaks.\n\n"
            "That break point is what you should ask me to explain next."
        )

    def _quiz_answer(self, topic: str, context: AssistantContext) -> str:
        subject = self._topic_subject(topic, context) or self._top_weak_subject(context)

        return (
            f"Quiz time — one question only.\n\n"
            f"For `{topic}` in `{subject}`: explain the main idea without looking at notes.\n\n"
            "Reply with your answer, even if it is incomplete."
        )

    def _progress_answer(self, context: AssistantContext, tone: Tone) -> str:
        overdue_count = len(context.overdue)
        due_count = len(context.due_today)
        weak_subject = self._top_weak_subject(context)

        if overdue_count:
            return (
                "Progress is mixed.\n\n"
                f"Good: you have an active study queue.\n"
                f"Problem: {overdue_count} overdue review(s) are still pulling your readiness down.\n"
                f"Focus area: `{weak_subject}`.\n\n"
                "Improvement will show when overdue count drops and confidence rises after recall."
            )

        return (
            "Your revision rhythm looks stable right now.\n\n"
            f"Due today: {due_count}.\n"
            f"Main area to watch: `{weak_subject}`.\n\n"
            "To measure real progress, compare recall confidence after each block, not hours studied."
        )

    def _motivation_answer(self, context: AssistantContext, tone: Tone) -> str:
        topic = self._best_topic_name(context)

        return (
            "You are not failing. You are facing a recall backlog.\n\n"
            f"Do just one thing now: close `{topic}` with a 20-minute recall block. "
            "No perfect plan, no new chapter, no overthinking. One clean block is enough to restart momentum."
        )

    def _general_answer(self, context: AssistantContext, tone: Tone) -> str:
        if context.overdue:
            topic = self._best_topic_name(context)

            return (
                f"The most useful move right now is `{topic}`.\n\n"
                "It is already overdue, so treat it as a memory repair task, not a normal study session."
            )

        if context.due_today:
            topic = self._best_topic_name(context)

            return (
                f"`{topic}` is the next useful checkpoint.\n\n"
                "Start with recall, then check notes. That will tell you whether to continue or switch."
            )

        if context.weak_subjects:
            subject = self._top_weak_subject(context)

            return (
                f"No urgent review is visible, so use this time to strengthen `{subject}`.\n\n"
                "Pick one low-confidence topic and test recall before reading."
            )

        return (
            "I do not have enough active study data yet.\n\n"
            "Add a due topic, overdue review, or weak subject so the assistant can give a precise recommendation."
        )

    def _best_topic_name(self, context: AssistantContext) -> str:
        if context.overdue:
            return str(context.overdue[0].get("name", "the overdue topic"))

        if context.due_today:
            return str(context.due_today[0].get("name", "the due topic"))

        if context.weak_subjects:
            return str(context.weak_subjects[0].get("subject", "the weakest subject"))

        return "the selected topic"

    def _top_weak_subject(self, context: AssistantContext) -> str:
        if context.weak_subjects:
            return str(context.weak_subjects[0].get("subject", "your weakest subject"))

        if context.overdue:
            return str(context.overdue[0].get("subject", "your weakest subject"))

        if context.due_today:
            return str(context.due_today[0].get("subject", "your current subject"))

        return "your weakest subject"

    def _topic_subject(self, topic: str, context: AssistantContext) -> str:
        target = topic.strip().lower()

        for pool in (context.overdue, context.due_today):
            for item in pool:
                if str(item.get("name", "")).strip().lower() == target:
                    return str(item.get("subject", "")).strip()

        for item in context.weak_subjects:
            if str(item.get("subject", "")).strip().lower() == target:
                return str(item.get("subject", "")).strip()

        return ""

    def _extracted_topic_name(self, prompt: str) -> str:
        patterns = [
            r"\bexplain\s+(.+?)(?:\s+with|\s+in simple|\s+quickly|$)",
            r"\bteach\s+me\s+(.+?)(?:\s+with|\s+in simple|\s+quickly|$)",
            r"\brevise\s+(.+?)(?:\s+with|\s+quickly|$)",
            r"\bquiz\s+me\s+on\s+(.+?)(?:\s+with|\s+quickly|$)",
            r"\btest\s+me\s+on\s+(.+?)(?:\s+with|\s+quickly|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                topic = match.group(1).strip(" .?!")
                if topic:
                    return topic

        return ""

    def _clean_response(self, response: str) -> str:
        text = response.strip()

        # Remove accidental prompt leakage.
        forbidden_headings = [
            "CONTEXT",
            "STUDENT QUESTION",
            "DETECTED INTENT",
            "RESPONSE RULES",
            "FORMAT IDEAS",
        ]

        for heading in forbidden_headings:
            if text.upper().startswith(heading):
                return ""

        # Collapse excessive blank lines.
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text
