"""Data model for TacticalDirector: character, encounter, and computed
action scores.

This is an original, generic combat model inspired by common tabletop RPG
mechanics (a character with HP, a limited resource pool, and an archetype;
enemies with a threat tier; terrain flags). It does not reproduce any
published ruleset's specific rules text and doesn't claim compatibility
with a particular commercial game.
"""

from __future__ import annotations

from dataclasses import dataclass

ACTION_LEVELS = {
    0: "Poor",
    1: "Situational",
    2: "Solid",
    3: "Great",
    4: "Optimal",
}

ARCHETYPES = {"warrior", "mage", "skirmisher", "support"}

ACTION_LABELS = {
    "attack": "Attack",
    "use_ability": "Use Ability",
    "defend": "Defend",
    "retreat": "Retreat",
}

CATEGORY_LABELS = {
    "offensive_value": "Offensive Value",
    "survival_risk": "Survival Risk",
    "resource_efficiency": "Resource Efficiency",
    "positional_advantage": "Positional Advantage",
}


@dataclass(frozen=True)
class Character:
    name: str
    archetype: str  # one of ARCHETYPES
    level: int
    hp_current: int
    hp_max: int
    resources_current: int
    resources_max: int

    @property
    def hp_pct(self) -> float:
        return self.hp_current / self.hp_max if self.hp_max else 0.0

    @property
    def resource_pct(self) -> float:
        return self.resources_current / self.resources_max if self.resources_max else 0.0


@dataclass(frozen=True)
class Enemy:
    name: str
    threat_tier: int  # 1 (trivial) - 5 (deadly)


@dataclass(frozen=True)
class Terrain:
    high_ground: bool = False
    cover: bool = False
    hazard: bool = False


@dataclass(frozen=True)
class Encounter:
    character: Character
    enemies: tuple[Enemy, ...]
    terrain: Terrain
    round_number: int = 1

    @property
    def threat_level(self) -> float:
        if not self.enemies:
            return 0.0
        return sum(e.threat_tier for e in self.enemies) / len(self.enemies)


@dataclass(frozen=True)
class CategoryScore:
    id: str
    label: str
    score: int
    reason: str


@dataclass(frozen=True)
class ActionScore:
    action: str
    label: str
    overall_score: float
    tier: str
    category_scores: tuple[CategoryScore, ...]


@dataclass(frozen=True)
class TacticalResult:
    encounter: Encounter
    ranked_actions: tuple[ActionScore, ...]  # sorted highest overall_score first


# ---------------------------------------------------------------------------
# Play Mode: multi-round sessions layered on top of the advisor above. These
# dataclasses describe game state; the resolution logic that produces them
# lives in tacticaldirector/play/. Nothing above this line is used by, or
# aware of, Play Mode.
# ---------------------------------------------------------------------------

OUTCOME_TIERS = ("Critical Success", "Success", "Partial", "Fail")

SESSION_STATUSES = {"in_progress", "victory", "defeat", "retreated"}


@dataclass(frozen=True)
class Skill:
    id: str
    label: str
    archetype: str  # one of ARCHETYPES
    description: str


@dataclass(frozen=True)
class RoundOutcome:
    round_number: int
    action: str  # one of ACTION_LABELS
    label: str
    top_recommended_action: str  # the Codex's #1 pick this round, one of ACTION_LABELS
    scores_by_action: dict[str, float]  # every action's overall_score this round, for deltas
    roll: int
    target_number: int
    outcome_tier: str  # one of OUTCOME_TIERS
    hp_delta: int
    resource_delta: int
    enemy_defeated: str | None
    narrative_hint: str
    skill_note: str | None = None


@dataclass(frozen=True)
class PlaySession:
    session_id: str
    scenario_id: str
    seed: int
    encounter: Encounter
    round_log: tuple[RoundOutcome, ...]
    status: str  # one of SESSION_STATUSES
