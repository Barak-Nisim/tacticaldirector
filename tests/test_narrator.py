"""Tests for the AI narrator. The Claude API is always mocked here -- these
tests never make a network call and never require ANTHROPIC_API_KEY.
"""

import json
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
def test_generate_narrative_parses_mocked_response(mock_anthropic):
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)

    narrative = generate_narrative(_sample_result())

    assert narrative == FAKE_NARRATIVE
    mock_anthropic.return_value.messages.create.assert_called_once()


@patch("tacticaldirector.ai.narrator.anthropic.Anthropic")
def test_generate_narrative_uses_structured_output_schema(mock_anthropic):
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)

    generate_narrative(_sample_result())

    _, kwargs = mock_anthropic.return_value.messages.create.call_args
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "narration" in kwargs["output_config"]["format"]["schema"]["required"]


@patch("tacticaldirector.ai.narrator.anthropic.Anthropic")
def test_generate_narrative_prompt_includes_top_ranked_action(mock_anthropic):
    mock_anthropic.return_value = _mock_client_with_response(FAKE_NARRATIVE)
    result = _sample_result()

    generate_narrative(result)

    _, kwargs = mock_anthropic.return_value.messages.create.call_args
    user_message = kwargs["messages"][0]["content"]
    assert result.ranked_actions[0].label in user_message
