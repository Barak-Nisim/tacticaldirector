"""After Action Report: a post-session analysis of a completed Play Mode
session, built purely from the round log already stored on the session.

No new scoring or resolution logic lives here -- this only reads what
resolve_round() already recorded each round (including which action the
Codex ranked #1 at the time), so it works for any completed session without
touching scoring.py, resolution.py's mechanics, or the persisted state.
"""

from __future__ import annotations

from dataclasses import dataclass

from tacticaldirector.models import ACTION_LABELS, PlaySession


@dataclass(frozen=True)
class RoundReview:
    round_number: int
    action_taken: str
    action_taken_label: str
    top_recommended: str
    top_recommended_label: str
    agreed_with_codex: bool
    outcome_tier: str
    narrative_hint: str


@dataclass(frozen=True)
class AfterActionReport:
    session_id: str
    scenario_id: str
    status: str
    rounds_played: int
    agreements: int
    disagreements: int
    round_reviews: tuple[RoundReview, ...]


def build_after_action_report(session: PlaySession) -> AfterActionReport:
    reviews = []
    agreements = 0

    for outcome in session.round_log:
        agreed = outcome.action == outcome.top_recommended_action
        if agreed:
            agreements += 1
        reviews.append(
            RoundReview(
                round_number=outcome.round_number,
                action_taken=outcome.action,
                action_taken_label=outcome.label,
                top_recommended=outcome.top_recommended_action,
                top_recommended_label=ACTION_LABELS[outcome.top_recommended_action],
                agreed_with_codex=agreed,
                outcome_tier=outcome.outcome_tier,
                narrative_hint=outcome.narrative_hint,
            )
        )

    rounds_played = len(session.round_log)
    return AfterActionReport(
        session_id=session.session_id,
        scenario_id=session.scenario_id,
        status=session.status,
        rounds_played=rounds_played,
        agreements=agreements,
        disagreements=rounds_played - agreements,
        round_reviews=tuple(reviews),
    )


def render_after_action_report(report: AfterActionReport) -> str:
    lines = [
        f"# After Action Report: {report.scenario_id}",
        "",
        f"**Result:** {report.status.capitalize()} ({report.rounds_played} round(s) played)",
        f"**Followed the Codex's top pick:** {report.agreements} of {report.rounds_played}"
        " round(s)",
        "",
        "## Round by round",
        "",
    ]

    for r in report.round_reviews:
        if r.agreed_with_codex:
            choice = f"took the Codex's top pick, {r.action_taken_label}"
        else:
            choice = f"chose {r.action_taken_label} over the Codex's {r.top_recommended_label}"
        lines.append(
            f"- **Round {r.round_number}:** {choice} -> {r.outcome_tier}. {r.narrative_hint}"
        )

    return "\n".join(lines)
