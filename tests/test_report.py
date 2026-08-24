from tacticaldirector.loader import load_encounter
from tacticaldirector.report.markdown import render
from tacticaldirector.scoring import score_encounter


def _sample_result():
    encounter = load_encounter("examples/sample_encounter.yaml")
    return score_encounter(encounter)


def test_render_contains_key_sections():
    report = render(_sample_result())

    assert "TacticalDirector Advisory: Kaelen" in report
    assert "## Recommended actions (ranked)" in report
    assert "Orc Raider (threat 3)" in report
    assert "cover" in report
    assert "## Game Master's take" not in report  # no AI narrative passed


def test_render_lists_all_four_actions_in_ranked_order():
    result = _sample_result()
    report = render(result)

    for i, action in enumerate(result.ranked_actions, start=1):
        assert f"### {i}. {action.label}" in report


def test_render_includes_ai_narrative_when_provided():
    ai_narrative = {
        "narration": "Holding your ground with cover is the strongest play here.",
        "table_talk": "The orcs circle, weapons ready.",
        "lowest_ranked_note": "Retreating gives up too much ground while HP is still manageable.",
    }

    report = render(_sample_result(), ai_narrative=ai_narrative)

    assert "## Game Master's take" in report
    assert "strongest play" in report
    assert "orcs circle" in report
    assert "Why the last option ranked low" in report
