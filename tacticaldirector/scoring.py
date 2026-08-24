"""Pure deterministic tactical scoring engine: Encounter -> TacticalResult.

No I/O, no network calls -- same discipline as RiskLens and MarketSignal.
Four actions (Attack, Use Ability, Defend, Retreat) are always evaluated
against four categories (Offensive Value, Survival Risk, Resource
Efficiency, Positional Advantage), each on a 0-4 scale (Poor to Optimal)
against fixed, documented rules below. Every score comes with a short
deterministic reason string -- there is no hidden model deciding the
number, and no AI involved in this module at all.
"""

from __future__ import annotations

from tacticaldirector.models import (
    ACTION_LABELS,
    ACTION_LEVELS,
    CATEGORY_LABELS,
    ActionScore,
    CategoryScore,
    Encounter,
    TacticalResult,
)

TIER_BOUNDARIES = (
    (0.8, "Poor"),
    (1.6, "Situational"),
    (2.4, "Solid"),
    (3.2, "Great"),
    (float("inf"), "Optimal"),
)


def tier_for_score(score: float) -> str:
    for boundary, tier in TIER_BOUNDARIES:
        if score < boundary:
            return tier
    return "Optimal"


def _clamp(score: int) -> int:
    return max(0, min(4, score))


OFFENSIVE_ARCHETYPES = {"warrior", "mage", "skirmisher"}
ABILITY_OFFENSE = {"mage": 4, "warrior": 3, "skirmisher": 3, "support": 1}


def _offensive_value(action: str, encounter: Encounter) -> tuple[int, str]:
    archetype = encounter.character.archetype

    if action == "attack":
        if archetype in OFFENSIVE_ARCHETYPES:
            return 4, f"A {archetype}'s attack is a core part of their kit."
        return 2, "Support archetypes can attack, but it isn't their primary strength."

    if action == "use_ability":
        score = ABILITY_OFFENSE.get(archetype, 2)
        if archetype == "mage":
            return score, "A mage's ability is typically their primary damage source."
        if archetype == "support":
            return score, "A support's ability is usually utility-focused, not offensive."
        return score, f"A {archetype}'s ability adds meaningful damage alongside attacking."

    if action == "defend":
        return 1, "Defending can create openings, but doesn't directly advance the fight."

    return 0, "Retreating deals no damage this turn."


def _survival_risk(action: str, encounter: Encounter) -> tuple[int, str]:
    hp_pct = encounter.character.hp_pct
    enemies_count = len(encounter.enemies)

    if action == "attack":
        score = 2
        reasons = []
        if hp_pct < 0.35:
            score -= 1
            reasons.append(f"HP is low ({hp_pct:.0%})")
        if enemies_count >= 3:
            score -= 1
            reasons.append(f"{enemies_count} enemies present")
        reason = (
            "Staying in the fight is risky: " + ", ".join(reasons) + "."
            if reasons
            else "A reasonably safe attack given the current HP and enemy count."
        )
        return _clamp(score), reason

    if action == "use_ability":
        score = 2 + (1 if encounter.character.archetype == "support" else 0)
        if hp_pct < 0.35:
            score -= 1
        reason = (
            "A support's ability often has some self-preservation value."
            if encounter.character.archetype == "support"
            else "Using an ability carries similar risk to attacking this turn."
        )
        return _clamp(score), reason

    if action == "defend":
        score = 4 - (1 if encounter.terrain.hazard else 0)
        reason = (
            "Defending near a hazard is safer than attacking, but not risk-free."
            if encounter.terrain.hazard
            else "Defending is close to always the safest option available."
        )
        return _clamp(score), reason

    # retreat
    if hp_pct < 0.35:
        return 4, f"HP is critical ({hp_pct:.0%}); disengaging is the safest play."
    if hp_pct < 0.75:
        return 3, "HP is dropping; retreating is a reasonable safety option."
    return 1, "HP is healthy, so retreating wastes the turn without a safety need."


def _resource_efficiency(action: str, encounter: Encounter) -> tuple[int, str]:
    if action in ("attack", "defend", "retreat"):
        return 3, "This action conserves resources by default."

    # use_ability
    character = encounter.character
    if character.resources_max == 0:
        return 0, "No resource pool is available for this character."

    resource_pct = character.resource_pct
    threat = encounter.threat_level

    if resource_pct <= 0.25 and threat < 2:
        return 0, "Spending a nearly-depleted resource pool on a low-threat encounter."
    if resource_pct <= 0.25 and threat >= 2:
        return 2, "Resources are low, but this encounter is threatening enough to warrant it."
    if resource_pct > 0.25 and threat >= 4:
        return 4, "Plenty of resources remain and this is a genuinely dangerous encounter."
    return 3, "A reasonable use of available resources for this encounter."


def _positional_advantage(action: str, encounter: Encounter) -> tuple[int, str]:
    terrain = encounter.terrain

    if action == "attack":
        score = 2
        if terrain.high_ground:
            score += 1
        if terrain.hazard and not terrain.cover:
            score -= 1
        reason = (
            "High ground favors attacking."
            if terrain.high_ground
            else "No notable terrain edge for attacking."
        )
        return _clamp(score), reason

    if action == "use_ability":
        score = 2 + (1 if terrain.cover else 0)
        reason = (
            "Cover makes it safer to commit to using an ability."
            if terrain.cover
            else "No cover to protect an extended action."
        )
        return _clamp(score), reason

    if action == "defend":
        score = 2 + (1 if terrain.cover else 0) + (1 if terrain.hazard else 0)
        reason = (
            "Defending near cover and/or a hazard is a strong positional choice."
            if (terrain.cover or terrain.hazard)
            else "No particular terrain benefit to defending here."
        )
        return _clamp(score), reason

    # retreat
    score = 2
    if terrain.hazard:
        score += 1
    if terrain.high_ground:
        score -= 1
    reason = (
        "Retreating from high ground gives up a positional advantage."
        if terrain.high_ground
        else "Retreating away from a hazard is a sound positional choice."
        if terrain.hazard
        else "No particular terrain factor either way."
    )
    return _clamp(score), reason


CATEGORY_FUNCTIONS = (
    ("offensive_value", _offensive_value),
    ("survival_risk", _survival_risk),
    ("resource_efficiency", _resource_efficiency),
    ("positional_advantage", _positional_advantage),
)


def score_encounter(encounter: Encounter) -> TacticalResult:
    action_scores = []

    for action, label in ACTION_LABELS.items():
        category_scores = []
        for category_id, scorer in CATEGORY_FUNCTIONS:
            score, reason = scorer(action, encounter)
            category_scores.append(
                CategoryScore(
                    id=category_id,
                    label=CATEGORY_LABELS[category_id],
                    score=score,
                    reason=reason,
                )
            )

        overall = sum(c.score for c in category_scores) / len(category_scores)
        action_scores.append(
            ActionScore(
                action=action,
                label=label,
                overall_score=overall,
                tier=tier_for_score(overall),
                category_scores=tuple(category_scores),
            )
        )

    ranked = tuple(sorted(action_scores, key=lambda a: a.overall_score, reverse=True))

    return TacticalResult(encounter=encounter, ranked_actions=ranked)


__all__ = ["score_encounter", "tier_for_score", "ACTION_LEVELS"]
