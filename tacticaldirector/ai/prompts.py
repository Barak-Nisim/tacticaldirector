"""Prompt construction for the AI narrator.

The prompt hands the model the fully-ranked TacticalResult as JSON and asks
it to narrate the recommendation in flavorful tactical language. It is
explicitly told not to recompute scores, invent enemies or rules, or
change the ranking -- it explains the deterministic result, it doesn't
replace it.
"""

from __future__ import annotations

import json

from tacticaldirector.models import TacticalResult

SYSTEM_PROMPT = (
    "You are a tactical game master's assistant. You are given the fully-ranked "
    "output of a deterministic tactical scoring engine: four possible actions, "
    "each already scored 0-4 (Poor to Optimal) across four categories, with a "
    "short reason attached to every score. Do not recompute or reorder the "
    "ranking, and do not invent enemies, rules, or outcomes that are not in the "
    "input. Write flavorful, game-master-style narration explaining the "
    "reasoning, not a mechanical restatement of the numbers."
)


def build_payload(result: TacticalResult) -> dict:
    c = result.encounter.character
    return {
        "character": {
            "name": c.name,
            "archetype": c.archetype,
            "level": c.level,
            "hp_current": c.hp_current,
            "hp_max": c.hp_max,
            "resources_current": c.resources_current,
            "resources_max": c.resources_max,
        },
        "enemies": [
            {"name": e.name, "threat_tier": e.threat_tier} for e in result.encounter.enemies
        ],
        "terrain": {
            "high_ground": result.encounter.terrain.high_ground,
            "cover": result.encounter.terrain.cover,
            "hazard": result.encounter.terrain.hazard,
        },
        "round_number": result.encounter.round_number,
        "ranked_actions": [
            {
                "action": a.label,
                "overall_score": a.overall_score,
                "tier": a.tier,
                "categories": [
                    {"label": cat.label, "score": cat.score, "reason": cat.reason}
                    for cat in a.category_scores
                ],
            }
            for a in result.ranked_actions
        ],
    }


def build_user_prompt(result: TacticalResult) -> str:
    payload = build_payload(result)
    return (
        "Here is the ranked tactical scoring output, as JSON:\n\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        "Write:\n"
        "1. A short game-master-style narration (about 100-150 words) explaining "
        "why the top-ranked action is the strongest choice right now.\n"
        "2. One line of 'table talk' flavor reacting to the encounter as it "
        "stands (atmosphere, not mechanics).\n"
        "3. A brief note on why the lowest-ranked action ranked last."
    )
