"""Explains how the Codex's live ranking changed since the previous round.

Uses each round's scores_by_action snapshot, already recorded by
resolve_round(). No new scoring logic -- purely a comparison of numbers
score_encounter already produced, both this round and last.
"""

from __future__ import annotations

from dataclasses import dataclass

from tacticaldirector.models import ACTION_LABELS, RoundOutcome, TacticalResult


@dataclass(frozen=True)
class ActionDelta:
    action: str
    label: str
    current_score: float
    current_rank: int
    previous_score: float | None
    previous_rank: int | None
    score_change: float | None
    rank_change: int | None  # positive = moved up (better) since last round


def build_deltas(
    result: TacticalResult, previous_outcome: RoundOutcome | None
) -> tuple[ActionDelta, ...]:
    previous_scores = previous_outcome.scores_by_action if previous_outcome else {}
    previous_ranked = sorted(previous_scores, key=lambda a: previous_scores[a], reverse=True)

    deltas = []
    for rank, action_score in enumerate(result.ranked_actions, start=1):
        action = action_score.action
        previous_score = previous_scores.get(action)
        previous_rank = previous_ranked.index(action) + 1 if action in previous_ranked else None
        score_change = (
            round(action_score.overall_score - previous_score, 2)
            if previous_score is not None
            else None
        )
        rank_change = previous_rank - rank if previous_rank is not None else None

        deltas.append(
            ActionDelta(
                action=action,
                label=ACTION_LABELS[action],
                current_score=action_score.overall_score,
                current_rank=rank,
                previous_score=previous_score,
                previous_rank=previous_rank,
                score_change=score_change,
                rank_change=rank_change,
            )
        )
    return tuple(deltas)
