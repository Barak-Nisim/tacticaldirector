"""Tests for the Play Mode round narrator. The Claude API is always mocked
here -- these tests never make a network call and never require
ANTHROPIC_API_KEY.
"""

import json
import random
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tacticaldirector.ai.round_narrator import narrate_round
from tacticaldirector.loader import load_encounter
from tacticaldirector.models import PlaySession
from tacticaldirector.play.resolution import resolve_round

FAKE_ROUND_NARRATIVE = {
    "gm_take": "Steel rings against steel as the blow lands true, driving the raider back.",
    "table_talk": "The wind shifts. Somewhere behind the treeline, something else is watching.",
}


def _sample_session_and_outcome():
    encounter = load_encounter("examples/sample_encounter.yaml")
    rng = random.Random(1)
    new_encounter, outcome, status = resolve_round(encounter, "attack", rng)
    session = PlaySession(
        session_id="test-session",
        scenario_id="sample_encounter",
        seed=1,
        encounter=new_encounter,
        round_log=(outcome,),
        status=status,
    )
    return session, outcome


def _mock_client_with_response(payload: dict) -> MagicMock:
    mock_client = MagicMock()
    mock_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=json.dumps(payload))]
    )
    mock_client.messages.create.return_value = mock_response
    return mock_client


@patch("tacticaldirector.ai.round_narrator.anthropic.Anthropic")
def test_narrate_round_parses_mocked_response(mock_anthropic):
    mock_anthropic.return_value = _mock_client_with_response(FAKE_ROUND_NARRATIVE)
    session, outcome = _sample_session_and_outcome()

    narrative = narrate_round(session, outcome)

    assert narrative == FAKE_ROUND_NARRATIVE
    mock_anthropic.return_value.messages.create.assert_called_once()


@patch("tacticaldirector.ai.round_narrator.anthropic.Anthropic")
def test_narrate_round_uses_structured_output_schema(mock_anthropic):
    mock_anthropic.return_value = _mock_client_with_response(FAKE_ROUND_NARRATIVE)
    session, outcome = _sample_session_and_outcome()

    narrate_round(session, outcome)

    _, kwargs = mock_anthropic.return_value.messages.create.call_args
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    schema = kwargs["output_config"]["format"]["schema"]
    assert set(schema["required"]) == {"gm_take", "table_talk"}


@patch("tacticaldirector.ai.round_narrator.anthropic.Anthropic")
def test_narrate_round_prompt_includes_the_actual_outcome(mock_anthropic):
    mock_anthropic.return_value = _mock_client_with_response(FAKE_ROUND_NARRATIVE)
    session, outcome = _sample_session_and_outcome()

    narrate_round(session, outcome)

    _, kwargs = mock_anthropic.return_value.messages.create.call_args
    user_message = kwargs["messages"][0]["content"]
    assert outcome.narrative_hint in user_message
    assert outcome.outcome_tier in user_message
    assert str(outcome.roll) in user_message
