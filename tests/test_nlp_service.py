from __future__ import annotations

from pathlib import Path

from models import DifficultyLevel
from nlp import NLPService, feedback_to_examples, load_training_examples, train_model

DATASET_PATH = Path(__file__).resolve().parent.parent / "nlp" / "data" / "training.csv"


def test_load_training_examples_reads_csv() -> None:
    examples = load_training_examples(DATASET_PATH)

    assert len(examples) >= 20
    assert {example.difficulty for example in examples} == {
        DifficultyLevel.EASY,
        DifficultyLevel.MEDIUM,
        DifficultyLevel.HARD,
    }


def test_train_and_predict_with_confidence_threshold(tmp_path) -> None:
    examples = load_training_examples(DATASET_PATH)
    service = NLPService(model_path=tmp_path / "difficulty_model.joblib", confidence_threshold=0.0)

    result = train_model(examples, service=service)
    prediction = service.predict_difficulty("Advanced calculus integration")

    assert result.example_count == len(examples)
    assert result.model_path.exists()
    assert prediction.difficulty in {
        DifficultyLevel.EASY,
        DifficultyLevel.MEDIUM,
        DifficultyLevel.HARD,
    }
    assert 0.0 <= prediction.confidence <= 1.0


def test_low_confidence_returns_none(tmp_path) -> None:
    examples = load_training_examples(DATASET_PATH)
    service = NLPService(model_path=tmp_path / "difficulty_model.joblib", confidence_threshold=0.99)

    train_model(examples, service=service)
    prediction = service.predict_difficulty("Completely ambiguous topic label")

    assert prediction.difficulty is None
    assert prediction.source == "low_confidence"


def test_feedback_conversion_uses_actual_difficulty() -> None:
    user_id = "user-1"
    service = NLPService(model_path=Path("unused.joblib"))
    feedback_items = [
        service.log_feedback(
            user_id=user_id,
            topic_name="Laplace transforms",
            predicted_difficulty=DifficultyLevel.MEDIUM,
            predicted_confidence=0.52,
            actual_difficulty=DifficultyLevel.HARD,
        ),
        service.log_feedback(
            user_id=user_id,
            topic_name="Fractions",
            predicted_difficulty=DifficultyLevel.EASY,
            predicted_confidence=0.91,
            actual_difficulty=DifficultyLevel.EASY,
        ),
    ]

    examples = feedback_to_examples(feedback_items)

    assert [item.topic_name for item in examples] == ["Laplace transforms", "Fractions"]
    assert [item.difficulty for item in examples] == [DifficultyLevel.HARD, DifficultyLevel.EASY]
