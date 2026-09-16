"""Tests for the AI narrator. The Claude API is always mocked here -- these
tests never make a network call and never require ANTHROPIC_API_KEY.
"""

import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tacticaldirector.ai.narrator import generate_narrative
from tacticaldirector.loader import load_encounter
from tacticaldirector.scoring import score_encounter

FAKE_NARRATIVE = {
    "narration": "Holding your ground behind cover is the strongest play here.",
    "table_talk": "The orcs circle, weapons ready, waiting for an opening.",
    "lowest_ranked_note": "Retreating gives up too much ground while HP is still manageable.",
}


def _sample_result():
    encounter = load_encounter("examples/sample_encounter.yaml")
    return score_encounter(encounter)


def _mock_client_with_response(payload: dict) -> MagicMock:
    mock_client = MagicMock()
    mock_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=json.dumps(payload))]
    )
    mock_client.messages.create.return_value = mock_response
    return mock_client


@patch("tacticaldirector.ai.narrator.anthropic.Anthropic")
def test_generate_narrative_parses_mocked_response(mock_anthropic, monkeypatch, tmp_path):
    monkeypatch.setenv("TACTICALDIRECTOR_NARRATIVE_CACHE_DIR", str(tmp_path))
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)

    narrative = generate_narrative(_sample_result())

    assert narrative == FAKE_NARRATIVE
    mock_anthropic.return_value.messages.create.assert_called_once()


@patch("tacticaldirector.ai.narrator.anthropic.Anthropic")
def test_generate_narrative_uses_structured_output_schema(mock_anthropic, monkeypatch, tmp_path):
    monkeypatch.setenv("TACTICALDIRECTOR_NARRATIVE_CACHE_DIR", str(tmp_path))
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)

    generate_narrative(_sample_result())

    _, kwargs = mock_anthropic.return_value.messages.create.call_args
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "narration" in kwargs["output_config"]["format"]["schema"]["required"]


@patch("tacticaldirector.ai.narrator.anthropic.Anthropic")
def test_generate_narrative_prompt_includes_top_ranked_action(
    mock_anthropic, monkeypatch, tmp_path
):
    monkeypatch.setenv("TACTICALDIRECTOR_NARRATIVE_CACHE_DIR", str(tmp_path))
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)
    result = _sample_result()

    generate_narrative(result)

    _, kwargs = mock_anthropic.return_value.messages.create.call_args
    user_message = kwargs["messages"][0]["content"]
    assert result.ranked_actions[0].label in user_message


# ---------- Narrative cache ----------


@patch("tacticaldirector.ai.narrator.anthropic.Anthropic")
def test_generate_narrative_second_identical_encounter_is_served_from_cache(
    mock_anthropic, monkeypatch, tmp_path
):
    monkeypatch.setenv("TACTICALDIRECTOR_NARRATIVE_CACHE_DIR", str(tmp_path))
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)

    first = generate_narrative(_sample_result())
    second = generate_narrative(_sample_result())

    assert first == second == FAKE_NARRATIVE
    mock_anthropic.return_value.messages.create.assert_called_once()


@patch("tacticaldirector.ai.narrator.anthropic.Anthropic")
def test_generate_narrative_cache_misses_when_character_hp_changes(
    mock_anthropic, monkeypatch, tmp_path
):
    monkeypatch.setenv("TACTICALDIRECTOR_NARRATIVE_CACHE_DIR", str(tmp_path))
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)
    encounter = load_encounter("examples/sample_encounter.yaml")
    hurt = replace(
        encounter,
        character=replace(encounter.character, hp_current=encounter.character.hp_current - 1),
    )

    generate_narrative(score_encounter(encounter))
    generate_narrative(score_encounter(hurt))

    assert mock_anthropic.return_value.messages.create.call_count == 2


@patch("tacticaldirector.ai.narrator.anthropic.Anthropic")
def test_generate_narrative_cache_misses_when_an_enemy_threat_tier_changes(
    mock_anthropic, monkeypatch, tmp_path
):
    monkeypatch.setenv("TACTICALDIRECTOR_NARRATIVE_CACHE_DIR", str(tmp_path))
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)
    encounter = load_encounter("examples/sample_encounter.yaml")
    first_enemy = encounter.enemies[0]
    deadlier = replace(
        encounter,
        enemies=(replace(first_enemy, threat_tier=first_enemy.threat_tier + 1),)
        + encounter.enemies[1:],
    )

    generate_narrative(score_encounter(encounter))
    generate_narrative(score_encounter(deadlier))

    assert mock_anthropic.return_value.messages.create.call_count == 2
