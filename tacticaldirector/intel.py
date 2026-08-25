"""Deterministic prediction of what each enemy is likely to do next round.

Not part of the Codex's scoring -- a separate, simple rule set over the
same Encounter data, so it reads as a different kind of claim than "this
action scores well." No AI, no new state, no scoring.py changes; just a
plain-language guess grounded in threat tier, HP, and terrain, recomputed
fresh every time.
"""

from __future__ import annotations

from dataclasses import dataclass

from tacticaldirector.models import Encounter, Enemy


@dataclass(frozen=True)
class EnemyIntent:
    enemy_name: str
    threat_tier: int
    predicted_action: str
    reason: str


def _predict_one(enemy: Enemy, encounter: Encounter, is_leader: bool) -> tuple[str, str]:
    hp_pct = encounter.character.hp_pct

    if hp_pct < 0.35 and is_leader:
        return (
            "Press the attack",
            "Your HP is critical, and this is the most dangerous enemy present; "
            "it will likely try to finish the fight.",
        )
    if is_leader and encounter.terrain.high_ground:
        return (
            "Maneuver for position",
            "You hold the high ground, so the strongest enemy is likely to "
            "reposition before committing.",
        )
    if is_leader:
        return "Attack directly", "The highest-threat enemy usually leads the engagement."
    if enemy.threat_tier <= 1:
        return (
            "Support from range",
            "A low-threat enemy is more likely to hang back and support than lead an attack.",
        )
    if encounter.terrain.cover:
        return "Hold behind cover", "Cover favors a cautious approach for a secondary enemy."

    return "Attack directly", "No strong signal either way; a direct attack is the default."


def predict_enemy_intents(encounter: Encounter) -> tuple[EnemyIntent, ...]:
    if not encounter.enemies:
        return ()

    highest_threat = max(e.threat_tier for e in encounter.enemies)

    intents = []
    for enemy in encounter.enemies:
        is_leader = enemy.threat_tier == highest_threat
        action, reason = _predict_one(enemy, encounter, is_leader)
        intents.append(
            EnemyIntent(
                enemy_name=enemy.name,
                threat_tier=enemy.threat_tier,
                predicted_action=action,
                reason=reason,
            )
        )

    return tuple(intents)


def render_enemy_intel(intents: tuple[EnemyIntent, ...]) -> str:
    if not intents:
        return ""

    lines = ["## Enemy intelligence", ""]
    for intent in intents:
        lines.append(
            f"- **{intent.enemy_name}** (threat {intent.threat_tier}): likely to "
            f"*{intent.predicted_action}* -- {intent.reason}"
        )
    return "\n".join(lines)
