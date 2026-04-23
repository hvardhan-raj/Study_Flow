from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from models import DifficultyLevel, NlpFeedback
from nlp.difficulty_predictor import NaiveBayesDifficultyModel, NLPService, tokenize


@dataclass(frozen=True)
class TrainingExample:
    topic_name: str
    difficulty: DifficultyLevel


@dataclass(frozen=True)
class TrainingResult:
    accuracy: float
    example_count: int
    model_path: Path


def load_training_examples(csv_path: Path) -> list[TrainingExample]:
    with csv_path.open("r", encoding="utf-8", newline="") as file_handle:
        reader = csv.DictReader(file_handle)
        return [
            TrainingExample(
                topic_name=row["topic_name"].strip(),
                difficulty=DifficultyLevel(row["difficulty"].strip().lower()),
            )
            for row in reader
            if row.get("topic_name") and row.get("difficulty")
        ]


def feedback_to_examples(feedback_items: list[NlpFeedback]) -> list[TrainingExample]:
    return [
        TrainingExample(topic_name=item.topic_name_raw, difficulty=item.actual_difficulty)
        for item in feedback_items
        if not item.used_for_retraining
    ]


def train_model(
    examples: list[TrainingExample],
    *,
    service: NLPService,
    minimum_examples: int = 9,
) -> TrainingResult:
    if len(examples) < minimum_examples:
        raise ValueError(f"Need at least {minimum_examples} examples to train the NLP model")

    randomized = examples[:]
    random.Random(42).shuffle(randomized)
    split_index = max(1, int(len(randomized) * 0.75))
    train_examples = randomized[:split_index]
    test_examples = randomized[split_index:] or randomized[-1:]

    model = _fit_model(train_examples)
    correct = 0
    for example in test_examples:
        probabilities = model.predict_proba([example.topic_name])[0]
        predicted_label = max(probabilities.items(), key=lambda item: item[1])[0]
        if predicted_label == example.difficulty.value:
            correct += 1

    accuracy = correct / len(test_examples)
    model_path = service.save_model(model)
    return TrainingResult(accuracy=accuracy, example_count=len(examples), model_path=model_path)


def _fit_model(examples: list[TrainingExample]) -> NaiveBayesDifficultyModel:
    label_counts: Counter[str] = Counter()
    token_counts: dict[str, Counter[str]] = defaultdict(Counter)
    total_token_counts: dict[str, int] = defaultdict(int)
    vocabulary: set[str] = set()

    for example in examples:
        label = example.difficulty.value
        label_counts[label] += 1
        for token in tokenize(example.topic_name):
            token_counts[label][token] += 1
            total_token_counts[label] += 1
            vocabulary.add(token)

    return NaiveBayesDifficultyModel(
        label_counts=label_counts,
        token_counts=dict(token_counts),
        total_token_counts=dict(total_token_counts),
        vocabulary=vocabulary,
    )
