"""Seeded, deterministic round resolution for Play Mode.

Given the current encounter, a chosen action, and an injected random.Random,
resolves what happens this round: a d20 roll against a target number derived
from the advisor's own scoring.py output, an outcome tier, and the resulting
state changes (enemy defeated, HP/resource deltas). Never touches the global
random module -- every call is reproducible given the same Random instance,
which is what makes a session replayable from its seed and what makes this
module fully unit-testable.

This module calls score_encounter() from the untouched advisor core to
derive target numbers; it never recomputes or overrides a ranking.
"""

from __future__ import annotations

import random
from dataclasses import replace

from tacticaldirector.models import ACTION_LABELS, Encounter, Enemy, RoundOutcome
from tacticaldirector.play.skills import (
    defend_reprisal_override,
    maybe_refund_resource,
    resource_cost_for_use_ability,
    roll_bonus_for_action,
)
from tacticaldirector.scoring import score_encounter

MIN_TARGET = 5
MAX_TARGET = 19

# outcome tier -> reprisal damage multiplier (used by Attack, Use Ability,
# Defend's mitigation, and a failed Retreat's reprisal)
REPRISAL_MULTIPLIER = {
    "Critical Success": 0.0,
    "Success": 0.5,
    "Partial": 0.75,
    "Fail": 1.0,
}
# Attack and Use Ability hit harder than the table above on an outright Fail
OFFENSIVE_FAIL_MULTIPLIER = 1.5


def _target_number(overall_score: float) -> int:
    raw = round(20 - overall_score * 3.5)
    return max(MIN_TARGET, min(MAX_TARGET, raw))


def _outcome_tier(roll: int, target: int) -> str:
    if roll >= target + 5:
        return "Critical Success"
    if roll >= target:
        return "Success"
    if roll >= target - 5:
        return "Partial"
    return "Fail"


def _highest_threat_enemy(enemies: tuple[Enemy, ...]) -> Enemy | None:
    if not enemies:
        return None
    return max(enemies, key=lambda e: e.threat_tier)


def _reprisal_damage(enemies: tuple[Enemy, ...], multiplier: float) -> int:
    if not enemies:
        return 0
    base = sum(e.threat_tier for e in enemies) * 1.5
    return round(base * multiplier)


def _narrative_hint(
    action: str, outcome_tier: str, enemy_defeated: str | None, retreated: bool
) -> str:
    if retreated:
        return "The retreat succeeds. You disengage cleanly."
    if action == "retreat":
        return "The retreat attempt fails; the enemy presses the advantage."
    if enemy_defeated:
        return f"{enemy_defeated} is defeated."
    if action == "defend":
        return {
            "Critical Success": "The defense holds perfectly. No damage gets through.",
            "Success": "The defense holds. Damage is reduced.",
            "Partial": "The defense partly holds.",
            "Fail": "The defense fails to hold.",
        }[outcome_tier]
    return {
        "Critical Success": "A decisive strike, but the target holds on.",
        "Success": "A solid hit, but not enough to finish the target.",
        "Partial": "A glancing blow. Little effect.",
        "Fail": "The attempt misses cleanly.",
    }[outcome_tier]


def resolve_round(
    encounter: Encounter, action: str, rng: random.Random
) -> tuple[Encounter, RoundOutcome, str]:
    """Resolves one round. Returns (updated_encounter, outcome, status), where
    status is one of "in_progress", "victory", "defeat", "retreated"."""
    if action not in ACTION_LABELS:
        raise ValueError(f"Unknown action: {action}")

    archetype = encounter.character.archetype
    result = score_encounter(encounter)
    action_score = next(a for a in result.ranked_actions if a.action == action)

    target = _target_number(action_score.overall_score)
    roll = rng.randint(1, 20)

    adjustment = roll_bonus_for_action(archetype, action, encounter)
    adjusted_roll = roll + adjustment.roll_bonus
    outcome_tier = _outcome_tier(adjusted_roll, target)

    character = encounter.character
    enemies = encounter.enemies
    hp_delta = 0
    resource_delta = 0
    enemy_defeated: str | None = None
    skill_note = adjustment.note
    retreated = False

    if action == "attack":
        if outcome_tier in ("Critical Success", "Success"):
            target_enemy = _highest_threat_enemy(enemies)
            if target_enemy is not None:
                enemies = tuple(e for e in enemies if e is not target_enemy)
                enemy_defeated = target_enemy.name
        multiplier = (
            OFFENSIVE_FAIL_MULTIPLIER
            if outcome_tier == "Fail"
            else REPRISAL_MULTIPLIER[outcome_tier]
        )
        hp_delta = -_reprisal_damage(enemies, multiplier)

    elif action == "use_ability":
        cost = resource_cost_for_use_ability(archetype, encounter) if character.resources_max else 0
        available = min(cost, character.resources_current)
        resource_delta = -available
        if available < cost:
            target = min(MAX_TARGET, target + 3)
            outcome_tier = _outcome_tier(adjusted_roll, target)

        if outcome_tier in ("Critical Success", "Success"):
            target_enemy = _highest_threat_enemy(enemies)
            if target_enemy is not None:
                enemies = tuple(e for e in enemies if e is not target_enemy)
                enemy_defeated = target_enemy.name
            if maybe_refund_resource(archetype, action, outcome_tier, rng):
                resource_delta = 0
                skill_note = ((skill_note or "") + " Rally refunded the resource spent.").strip()

        multiplier = (
            OFFENSIVE_FAIL_MULTIPLIER
            if outcome_tier == "Fail"
            else REPRISAL_MULTIPLIER[outcome_tier]
        )
        hp_delta = -_reprisal_damage(enemies, multiplier)

    elif action == "defend":
        if defend_reprisal_override(archetype):
            multiplier = 0.0
            skill_note = "Second Wind: reprisal fully negated."
        else:
            multiplier = REPRISAL_MULTIPLIER[outcome_tier]
        hp_delta = -_reprisal_damage(enemies, multiplier)

    else:  # retreat
        if outcome_tier in ("Critical Success", "Success"):
            retreated = True
        else:
            hp_delta = -_reprisal_damage(enemies, REPRISAL_MULTIPLIER[outcome_tier])

    new_hp = max(0, character.hp_current + hp_delta)
    new_resources = max(0, character.resources_current + resource_delta)
    new_character = replace(character, hp_current=new_hp, resources_current=new_resources)

    new_encounter = Encounter(
        character=new_character,
        enemies=enemies,
        terrain=encounter.terrain,
        round_number=encounter.round_number + 1,
    )

    if retreated:
        status = "retreated"
    elif new_hp <= 0:
        status = "defeat"
    elif not enemies:
        status = "victory"
    else:
        status = "in_progress"

    outcome = RoundOutcome(
        round_number=encounter.round_number,
        action=action,
        label=ACTION_LABELS[action],
        roll=adjusted_roll,
        target_number=target,
        outcome_tier=outcome_tier,
        hp_delta=hp_delta,
        resource_delta=resource_delta,
        enemy_defeated=enemy_defeated,
        narrative_hint=_narrative_hint(action, outcome_tier, enemy_defeated, retreated),
        skill_note=skill_note,
    )

    return new_encounter, outcome, status
