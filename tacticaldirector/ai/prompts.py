"""Prompt construction for the AI narrator.

The prompt hands the model the fully-ranked TacticalResult as JSON and asks
it to narrate the recommendation in flavorful tactical language. It is
explicitly told not to recompute scores, invent enemies or rules, or
change the ranking -- it explains the deterministic result, it doesn't
replace it.
"""

from __future__ import annotations

import json

from tacticaldirector.models import PlaySession, RoundOutcome, TacticalResult

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


# ---------------------------------------------------------------------------
# Play Mode round narration: a sibling prompt for narrating one already-
# resolved round (see ai/round_narrator.py), additive to everything above.
# The single-round advisor's SYSTEM_PROMPT/build_user_prompt are untouched.
# ---------------------------------------------------------------------------

ROUND_SYSTEM_PROMPT = (
    "You are a tabletop game master narrating one round of combat that has "
    "already been resolved by a deterministic dice-and-threshold system. You "
    "are given the round's actual mechanical result: the action taken, the "
    "roll, the target number, the outcome tier, and exactly what changed "
    "(HP, resources, whether an enemy was defeated). Your only job is to "
    "make that specific, already-decided outcome vivid and dramatic. Do not "
    "change the roll, the outcome tier, the HP or resource numbers, or "
    "which enemy fell -- the field called 'narrative_hint' in the input is "
    "the canonical fact of what happened; never contradict it or invent a "
    "different result. Do not invent named commercial game systems or "
    "rules text. Keep it grounded in what actually happened this round."
)


def build_round_payload(session: PlaySession, outcome: RoundOutcome) -> dict:
    character = session.encounter.character
    return {
        "round_number": outcome.round_number,
        "action_taken": outcome.label,
        "roll": outcome.roll,
        "target_number": outcome.target_number,
        "outcome_tier": outcome.outcome_tier,
        "narrative_hint": outcome.narrative_hint,
        "hp_delta": outcome.hp_delta,
        "resource_delta": outcome.resource_delta,
        "enemy_defeated": outcome.enemy_defeated,
        "skill_note": outcome.skill_note,
        "character": {
            "name": character.name,
            "archetype": character.archetype,
            "hp_current": character.hp_current,
            "hp_max": character.hp_max,
        },
        "enemies_remaining": [
            {"name": e.name, "threat_tier": e.threat_tier} for e in session.encounter.enemies
        ],
        "terrain": {
            "high_ground": session.encounter.terrain.high_ground,
            "cover": session.encounter.terrain.cover,
            "hazard": session.encounter.terrain.hazard,
        },
    }


def build_round_user_prompt(session: PlaySession, outcome: RoundOutcome) -> str:
    payload = build_round_payload(session, outcome)
    return (
        "Here is this round's already-resolved outcome, as JSON:\n\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        "Write:\n"
        "1. A 'gm_take' (about 60-90 words) dramatizing exactly what happened "
        "this round, grounded in narrative_hint and the actual deltas -- not "
        "a mechanical restatement of the numbers, but not a different "
        "outcome either.\n"
        "2. One line of 'table_talk': atmospheric flavor reacting to the "
        "current state of the fight, not a summary of the mechanics."
    )
