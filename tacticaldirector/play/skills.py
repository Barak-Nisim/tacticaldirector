"""Per-archetype skill modifiers applied during round resolution.

Each function is pure given the same random.Random instance passed in --
no global random state, no I/O. Skills only ever adjust the roll or resource
cost that resolution.py already computes; they never introduce a new
mechanic of their own.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from tacticaldirector.models import Encounter, Skill

SKILLS: dict[str, Skill] = {
    "warrior": Skill(
        id="second_wind",
        label="Second Wind",
        archetype="warrior",
        description="On Defend, incoming reprisal damage is always fully negated.",
    ),
    "mage": Skill(
        id="arcane_focus",
        label="Arcane Focus",
        archetype="mage",
        description="On Use Ability, +3 to the roll, at 2 resources instead of 1 when affordable.",
    ),
    "skirmisher": Skill(
        id="opportunist",
        label="Opportunist",
        archetype="skirmisher",
        description="On Attack, +3 to the roll when only one enemy remains.",
    ),
    "support": Skill(
        id="rally",
        label="Rally",
        archetype="support",
        description="On a successful Use Ability, 50% chance to refund the resource spent.",
    ),
}


@dataclass(frozen=True)
class SkillAdjustment:
    roll_bonus: int = 0
    note: str | None = None


def resource_cost_for_use_ability(archetype: str, encounter: Encounter) -> int:
    """Mage's Arcane Focus spends 2 resources instead of 1 when affordable."""
    if archetype == "mage" and encounter.character.resources_current >= 2:
        return 2
    return 1


def roll_bonus_for_action(archetype: str, action: str, encounter: Encounter) -> SkillAdjustment:
    if archetype == "mage" and action == "use_ability":
        cost = resource_cost_for_use_ability(archetype, encounter)
        if cost == 2:
            return SkillAdjustment(
                roll_bonus=3, note="Arcane Focus: +3 to the roll, 2 resources spent."
            )
        return SkillAdjustment(note="Arcane Focus: not enough resources for the full bonus.")

    if archetype == "skirmisher" and action == "attack" and len(encounter.enemies) == 1:
        return SkillAdjustment(
            roll_bonus=3, note="Opportunist: +3 to the roll, only one enemy remains."
        )

    return SkillAdjustment()


def defend_reprisal_override(archetype: str) -> bool:
    """Warrior's Second Wind always fully negates Defend reprisal."""
    return archetype == "warrior"


def maybe_refund_resource(
    archetype: str, action: str, outcome_tier: str, rng: random.Random
) -> bool:
    """Support's Rally: 50% chance to refund the resource spent on a
    successful Use Ability."""
    if archetype != "support" or action != "use_ability":
        return False
    if outcome_tier not in ("Critical Success", "Success"):
        return False
    return rng.random() < 0.5
