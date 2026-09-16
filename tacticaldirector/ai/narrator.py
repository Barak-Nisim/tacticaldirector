"""Calls the Claude API to narrate a TacticalResult in game-master style.

This module never recomputes or reorders the tactical scores -- it only
narrates the deterministic output of tacticaldirector.scoring. Requires
ANTHROPIC_API_KEY (see .env.example); not exercised by the test suite or
CI, which run with mocked responses.

Re-submitting an identical encounter is served from narrative_cache
instead of re-spending tokens on a response that would come back
identical -- see that module for what counts as identical.
"""

from __future__ import annotations

import json

import anthropic
from dotenv import load_dotenv

from tacticaldirector.ai.narrative_cache import get_cached_narrative, store_narrative
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
    cached = get_cached_narrative(result)
    if cached is not None:
        return cached

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
    narrative = json.loads(text)
    store_narrative(result, narrative)
    return narrative
