from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, pow

from models import ConfidenceRating

MIN_DIFFICULTY = 1.0
MAX_DIFFICULTY = 10.0
MIN_STABILITY = 0.1


@dataclass(frozen=True)
class FSRSParameters:
    """Single-user FSRS defaults tuned around the standard 4-button flow."""

    desired_retention: float = 0.9
    initial_stability_again: float = 0.4
    initial_stability_hard: float = 1.2
    initial_stability_good: float = 3.0
    initial_stability_easy: float = 7.0
    difficulty_delta: float = 0.35
    mean_reversion: float = 0.2
    recall_gain: float = 1.6
    recall_stability_power: float = 0.15
    recall_retrievability_gain: float = 1.1
    lapse_gain: float = 1.9
    lapse_difficulty_power: float = 0.2
    lapse_stability_power: float = 0.3
    lapse_retrievability_gain: float = 2.0
    hard_penalty: float = 0.8
    easy_bonus: float = 1.25


@dataclass(frozen=True)
class FSRSState:
    difficulty: float
    stability: float


@dataclass(frozen=True)
class FSRSReviewResult:
    difficulty: float
    stability: float
    interval_days: int
    retrievability: float


class FSRSScheduler:
    """FSRS-style card state transitions with deterministic parameters."""

    def __init__(self, parameters: FSRSParameters | None = None) -> None:
        self.parameters = parameters or FSRSParameters()

    def initial_state(self, *, topic_difficulty: float, rating: ConfidenceRating | None = None) -> FSRSState:
        if rating is None:
            return FSRSState(
                difficulty=self._clamp_difficulty(topic_difficulty),
                stability=self._initial_topic_stability(topic_difficulty),
            )
        return FSRSState(
            difficulty=self._next_difficulty(topic_difficulty, rating, topic_difficulty),
            stability=self._initial_stability_for_rating(rating),
        )

    def review(
        self,
        *,
        state: FSRSState,
        rating: ConfidenceRating,
        elapsed_days: float,
        baseline_difficulty: float,
    ) -> FSRSReviewResult:
        elapsed = max(float(elapsed_days), 0.0)
        retrievability = self.retrievability(state.stability, elapsed)
        next_difficulty = self._next_difficulty(state.difficulty, rating, baseline_difficulty)
        if rating == ConfidenceRating.AGAIN:
            next_stability = self._next_forget_stability(state, retrievability)
        elif elapsed <= 0:
            next_stability = self._initial_stability_for_rating(rating)
        else:
            next_stability = self._next_recall_stability(state, rating, retrievability)

        interval_days = self.interval_days(next_stability)
        return FSRSReviewResult(
            difficulty=next_difficulty,
            stability=next_stability,
            interval_days=interval_days,
            retrievability=retrievability,
        )

    def retrievability(self, stability: float, elapsed_days: float) -> float:
        stability = max(stability, MIN_STABILITY)
        return max(0.0, min(1.0, pow(0.9, elapsed_days / stability)))

    def interval_days(self, stability: float) -> int:
        retention = min(max(self.parameters.desired_retention, 0.7), 0.97)
        interval = stability * log(retention) / log(0.9)
        return max(1, round(interval))

    def _next_difficulty(self, current: float, rating: ConfidenceRating, baseline: float) -> float:
        rating_step = {
            ConfidenceRating.AGAIN: -2,
            ConfidenceRating.HARD: -1,
            ConfidenceRating.GOOD: 0,
            ConfidenceRating.EASY: 1,
        }[rating]
        adjusted = current - self.parameters.difficulty_delta * rating_step
        reverted = (1 - self.parameters.mean_reversion) * adjusted + self.parameters.mean_reversion * baseline
        return self._clamp_difficulty(reverted)

    def _next_recall_stability(self, state: FSRSState, rating: ConfidenceRating, retrievability: float) -> float:
        hard_penalty = self.parameters.hard_penalty if rating == ConfidenceRating.HARD else 1.0
        easy_bonus = self.parameters.easy_bonus if rating == ConfidenceRating.EASY else 1.0
        gain = (
            exp(self.parameters.recall_gain)
            * (11 - state.difficulty)
            * pow(max(state.stability, MIN_STABILITY), -self.parameters.recall_stability_power)
            * (exp((1 - retrievability) * self.parameters.recall_retrievability_gain) - 1)
            * hard_penalty
            * easy_bonus
        )
        return max(MIN_STABILITY, state.stability * (1 + gain))

    def _next_forget_stability(self, state: FSRSState, retrievability: float) -> float:
        lapse = (
            self.parameters.lapse_gain
            * pow(max(state.difficulty, MIN_DIFFICULTY), -self.parameters.lapse_difficulty_power)
            * (pow(max(state.stability, MIN_STABILITY) + 1, self.parameters.lapse_stability_power) - 1)
            * exp((1 - retrievability) * self.parameters.lapse_retrievability_gain)
        )
        return max(MIN_STABILITY, lapse)

    def _initial_stability_for_rating(self, rating: ConfidenceRating) -> float:
        return {
            ConfidenceRating.AGAIN: self.parameters.initial_stability_again,
            ConfidenceRating.HARD: self.parameters.initial_stability_hard,
            ConfidenceRating.GOOD: self.parameters.initial_stability_good,
            ConfidenceRating.EASY: self.parameters.initial_stability_easy,
        }[rating]

    def _initial_topic_stability(self, topic_difficulty: float) -> float:
        if topic_difficulty >= 7.0:
            return 1.2
        if topic_difficulty >= 5.0:
            return 1.8
        return 2.6

    def _clamp_difficulty(self, value: float) -> float:
        return round(max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, value)), 3)
