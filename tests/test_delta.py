from tacticaldirector.loader import load_encounter
from tacticaldirector.models import RoundOutcome
from tacticaldirector.play.delta import build_deltas
from tacticaldirector.scoring import score_encounter


def _sample_result():
    return score_encounter(load_encounter("examples/sample_encounter.yaml"))


def _fake_outcome(scores_by_action: dict) -> RoundOutcome:
    return RoundOutcome(
        round_number=1,
        action="attack",
        label="Attack",
        top_recommended_action="attack",
        scores_by_action=scores_by_action,
        roll=10,
        target_number=10,
        outcome_tier="Success",
        hp_delta=0,
        resource_delta=0,
        enemy_defeated=None,
        narrative_hint="",
    )


def test_no_previous_outcome_means_no_deltas():
    result = _sample_result()

    deltas = build_deltas(result, None)

    assert len(deltas) == 4
    for i, d in enumerate(deltas, start=1):
        assert d.current_rank == i
        assert d.previous_score is None
        assert d.previous_rank is None
        assert d.score_change is None
        assert d.rank_change is None


def test_deltas_are_empty_but_present_for_every_ranked_action():
    result = _sample_result()

    deltas = build_deltas(result, None)

    assert {d.action for d in deltas} == {a.action for a in result.ranked_actions}


def test_delta_reflects_a_score_that_improved_and_moved_up():
    result = _sample_result()
    top_action = result.ranked_actions[0]
    other_actions = [a.action for a in result.ranked_actions if a.action != top_action.action]

    # pretend this action scored lowest, and strictly lower than the other
    # three, so it unambiguously ranked last (4th) last round
    previous = {top_action.action: 0.0}
    for i, action in enumerate(other_actions, start=1):
        previous[action] = float(i)

    deltas = build_deltas(result, _fake_outcome(previous))
    top_delta = next(d for d in deltas if d.action == top_action.action)

    assert top_delta.previous_score == 0.0
    assert top_delta.previous_rank == 4
    assert top_delta.score_change == round(top_action.overall_score - 0.0, 2)
    assert top_delta.rank_change == top_delta.previous_rank - top_delta.current_rank
    assert top_delta.rank_change > 0


def test_delta_is_zero_when_score_is_unchanged():
    result = _sample_result()
    previous = {a.action: a.overall_score for a in result.ranked_actions}

    deltas = build_deltas(result, _fake_outcome(previous))

    for d in deltas:
        assert d.score_change == 0.0
        assert d.rank_change == 0


def test_action_missing_from_previous_scores_has_no_delta():
    result = _sample_result()
    some_action = result.ranked_actions[0].action
    previous = {a.action: a.overall_score for a in result.ranked_actions if a.action != some_action}

    deltas = build_deltas(result, _fake_outcome(previous))
    missing_delta = next(d for d in deltas if d.action == some_action)

    assert missing_delta.previous_score is None
    assert missing_delta.previous_rank is None
    assert missing_delta.score_change is None
    assert missing_delta.rank_change is None
