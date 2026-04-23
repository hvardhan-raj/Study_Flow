from __future__ import annotations

import math
import pickle
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from config.settings import settings
from models import DifficultyLevel, NlpFeedback

DEFAULT_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_MODEL_FILENAME = "difficulty_model.pkl"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class DifficultyPrediction:
    difficulty: DifficultyLevel | None
    confidence: float
    source: str


@dataclass
class NaiveBayesDifficultyModel:
    label_counts: Counter[str]
    token_counts: dict[str, Counter[str]]
    total_token_counts: dict[str, int]
    vocabulary: set[str]

    def predict_proba(self, texts: list[str]) -> list[dict[str, float]]:
        results: list[dict[str, float]] = []
        labels = list(self.label_counts.keys())
        total_examples = sum(self.label_counts.values())
        vocabulary_size = max(len(self.vocabulary), 1)

        for text in texts:
            tokens = tokenize(text)
            log_scores: dict[str, float] = {}
            for label in labels:
                label_prior = self.label_counts[label] / total_examples
                token_counter = self.token_counts[label]
                token_total = self.total_token_counts[label]
                score = math.log(label_prior)
                for token in tokens:
                    token_frequency = token_counter[token]
                    probability = (token_frequency + 1) / (token_total + vocabulary_size)
                    score += math.log(probability)
                log_scores[label] = score

            max_score = max(log_scores.values())
            exp_scores = {label: math.exp(score - max_score) for label, score in log_scores.items()}
            normalizer = sum(exp_scores.values()) or 1.0
            results.append({label: value / normalizer for label, value in exp_scores.items()})

        return results

    @property
    def classes_(self) -> list[str]:
        return sorted(self.label_counts.keys())


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


class NLPService:
    def __init__(
        self,
        *,
        model_path: Path | None = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.model_path = model_path or settings.local_model_path / DEFAULT_MODEL_FILENAME
        self.confidence_threshold = confidence_threshold
        self._model: NaiveBayesDifficultyModel | None = None

    def predict_difficulty(self, topic_name: str) -> DifficultyPrediction:
        model = self._load_model()
        if model is None:
            return DifficultyPrediction(difficulty=None, confidence=0.0, source="unavailable")

        probabilities = model.predict_proba([topic_name])[0]
        predicted_label, confidence = max(probabilities.items(), key=lambda item: item[1])
        if confidence < self.confidence_threshold:
            return DifficultyPrediction(difficulty=None, confidence=confidence, source="low_confidence")

        return DifficultyPrediction(
            difficulty=DifficultyLevel(predicted_label),
            confidence=confidence,
            source="model",
        )

    def log_feedback(
        self,
        *,
        topic_name: str,
        predicted_difficulty: DifficultyLevel,
        predicted_confidence: float,
        actual_difficulty: DifficultyLevel,
    ) -> NlpFeedback:
        return NlpFeedback(
            topic_name_raw=topic_name,
            predicted_difficulty=predicted_difficulty,
            predicted_confidence=predicted_confidence,
            actual_difficulty=actual_difficulty,
            used_for_retraining=False,
        )

    def reload(self) -> None:
        self._model = None

    def save_model(self, model: NaiveBayesDifficultyModel) -> Path:
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with self.model_path.open("wb") as file_handle:
            pickle.dump(model, file_handle)
        self._model = model
        return self.model_path

    def _load_model(self) -> NaiveBayesDifficultyModel | None:
        if self._model is not None:
            return self._model
        if not self.model_path.exists():
            return None
        with self.model_path.open("rb") as file_handle:
            self._model = pickle.load(file_handle)
        return self._model
