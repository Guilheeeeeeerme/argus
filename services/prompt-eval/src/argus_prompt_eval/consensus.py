"""Deterministic, fail-closed sensor / edge / model consensus."""

import math
from dataclasses import dataclass


def probability(value: object) -> float:
    if isinstance(value, bool):
        raise TypeError("boolean score")
    score = float(value)
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError("invalid score")
    return score


@dataclass(frozen=True)
class ConsensusDecision:
    is_positive: bool
    score: float
    reason: str


@dataclass(frozen=True)
class ConsensusEngine:
    sensor_weight: float = 0.25
    edge_weight: float = 0.35
    gemini_weight: float = 0.40
    threshold: float = 0.55
    edge_minimum: float = 0.4

    def evaluate(
        self,
        *,
        sensor_score,
        edge_score,
        gemini_score,
        prompt_hit: bool,
        veto: bool = False,
    ) -> ConsensusDecision:
        try:
            sensor, edge, gemini = map(
                probability, (sensor_score, edge_score, gemini_score)
            )
            weights = tuple(
                map(
                    probability,
                    (self.sensor_weight, self.edge_weight, self.gemini_weight),
                )
            )
            threshold, minimum = map(probability, (self.threshold, self.edge_minimum))
            if (
                not math.isclose(sum(weights), 1)
                or type(prompt_hit) is not bool
                or type(veto) is not bool
            ):
                raise ValueError("invalid consensus configuration")
        except (TypeError, ValueError, OverflowError):
            return ConsensusDecision(False, 0, "malformed_consensus")
        score = sum(w * v for w, v in zip(weights, (sensor, edge, gemini)))
        positive = not veto and (score >= threshold or (prompt_hit and edge >= minimum))
        return ConsensusDecision(
            positive, score, "sensor_veto" if veto else "consensus"
        )
