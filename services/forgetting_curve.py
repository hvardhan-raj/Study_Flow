from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonalFeatures:
    """Legacy compatibility placeholder for the removed personalized scheduler."""

    days_since_review: int = 0
    num_past_reviews: int = 0
    avg_confidence: float = 0.0
    topic_difficulty_score: float = 0.5
    num_missed_revisions: int = 0
    time_of_day: int = 0


class ForgettingCurveModel:
    """Offline single-user build no longer trains a separate forgetting-curve model."""

    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def predict_interval(self, **_kwargs) -> None:
        return None

    def train_if_needed(self, *_args, **_kwargs) -> None:
        return None

    def build_features_for_topic(self, **_kwargs) -> PersonalFeatures:
        return PersonalFeatures()

    def load(self, *_args, **_kwargs) -> None:
        return None
