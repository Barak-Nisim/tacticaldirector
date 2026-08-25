import random
from dataclasses import replace

from tacticaldirector.loader import load_encounter
from tacticaldirector.play.after_action import (
    build_after_action_report,
    render_after_action_report,
)
from tacticaldirector.play.resolution import resolve_round
from tacticaldirector.play.session import start_session


def _play_out_a_session(seed: int, actions: list[str]):
    encounter = load_encounter("examples/sample_encounter.yaml")
    session = start_session("broken_bridge_ambush", encounter, seed)
    rng = random.Random(seed)

    for action in actions:
        if session.status != "in_progress":
            break
        new_encounter, outcome, status = resolve_round(session.encounter, action, rng)
        session = replace(
            session,
            encounter=new_encounter,
            round_log=session.round_log + (outcome,),
            status=status,
        )

    return session


def test_report_has_no_rounds_for_a_fresh_session():
    session = start_session(
        "broken_bridge_ambush", load_encounter("examples/sample_encounter.yaml"), seed=1
    )

    report = build_after_action_report(session)

    assert report.rounds_played == 0
    assert report.agreements == 0
    assert report.disagreements == 0
    assert report.round_reviews == ()


def test_report_counts_agreements_and_disagreements_correctly():
    session = _play_out_a_session(seed=1, actions=["attack", "attack", "attack"])

    report = build_after_action_report(session)

    assert report.rounds_played == len(session.round_log)
    assert report.agreements + report.disagreements == report.rounds_played
    for review, outcome in zip(report.round_reviews, session.round_log, strict=True):
        assert review.agreed_with_codex == (outcome.action == outcome.top_recommended_action)
        assert review.round_number == outcome.round_number
        assert review.outcome_tier == outcome.outcome_tier


def test_report_reflects_final_session_status():
    session = _play_out_a_session(seed=1, actions=["attack"] * 10)

    report = build_after_action_report(session)

    assert report.status == session.status
    assert report.session_id == session.session_id
    assert report.scenario_id == "broken_bridge_ambush"


def test_render_includes_result_and_every_round():
    session = _play_out_a_session(seed=1, actions=["attack", "attack", "attack"])
    report = build_after_action_report(session)

    text = render_after_action_report(report)

    assert "After Action Report" in text
    assert report.status.capitalize() in text
    for review in report.round_reviews:
        assert f"Round {review.round_number}" in text
