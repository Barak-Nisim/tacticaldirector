"""Calls the Claude API to narrate a TacticalResult in game-master style.

This module never recomputes or reorders the tactical scores -- it only
narrates the deterministic output of tacticaldirector.scoring. Requires
ANTHROPIC_API_KEY (see .env.example); not exercised by the test suite or
CI, which run with mocked responses.
"""

from __future__ import annotations

import json

import anthropic
from dotenv import load_dotenv

from tacticaldirector.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from tacticaldirector.models import TacticalResult

MODEL = "claude-opus-4-8"

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "narration": {"type": "string"},
        "table_talk": {"type": "string"},
        "lowest_ranked_note": {"type": "string"},
    },
    "required": ["narration", "table_talk", "lowest_ranked_note"],
    "additionalProperties": False,
}


def generate_narrative(result: TacticalResult) -> dict:
    load_dotenv()
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(result)}],
        output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
    )

    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)
