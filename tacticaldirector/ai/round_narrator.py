"""Calls the Claude API to narrate one already-resolved Play Mode round in
game-master style.

Sibling to ai/narrator.py, not an edit to it -- the single-round advisor's
narrator stays untouched. This module never recomputes or overrides a
round's outcome; it only narrates the deterministic result already
produced by tacticaldirector.play.resolution.resolve_round(). Requires
ANTHROPIC_API_KEY (see .env.example); not exercised by the test suite or
CI, which run with mocked responses.
"""

from __future__ import annotations

import json

import anthropic
from dotenv import load_dotenv

from tacticaldirector.ai.prompts import ROUND_SYSTEM_PROMPT, build_round_user_prompt
from tacticaldirector.models import PlaySession, RoundOutcome

MODEL = "claude-opus-4-8"

ROUND_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "gm_take": {"type": "string"},
        "table_talk": {"type": "string"},
    },
    "required": ["gm_take", "table_talk"],
    "additionalProperties": False,
}


def narrate_round(session: PlaySession, outcome: RoundOutcome) -> dict:
    load_dotenv()
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=ROUND_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_round_user_prompt(session, outcome)}],
        output_config={"format": {"type": "json_schema", "schema": ROUND_OUTPUT_SCHEMA}},
    )

    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)
