import random
from dataclasses import replace

from tacticaldirector.loader import load_encounter
from tacticaldirector.models import ACTION_LABELS, OUTCOME_TIERS, Enemy
from tacticaldirector.play import resolution
from tacticaldirector.scoring import score_encounter


def _sample_encounter():
    return load_encounter("examples/sample_encounter.yaml")


class _FixedRng:
    """Stand-in for random.Random that always returns fixed values, so
    resolve_round's branching logic can be tested precisely without guessing
    real Mersenne Twister output."""

    def __init__(self, roll, chance=1.0):
        self._roll = roll
        self._chance = chance

    def randint(self, a, b):
        return self._roll

    def random(self):
        return self._chance


# ---------- pure helper functions ----------


def test_target_number_maps_high_score_to_easy_target():
    assert resolution._target_number(4.0) == 6


def test_target_number_maps_low_score_to_hard_target_clamped():
    assert resolution._target_number(0.0) == resolution.MAX_TARGET


def test_target_number_is_always_within_bounds():
    for score in (0.0, 1.0, 2.0, 2.75, 3.5, 4.0):
        target = resolution._target_number(score)
        assert resolution.MIN_TARGET <= target <= resolution.MAX_TARGET


def test_outcome_tier_boundaries():
    assert resolution._outcome_tier(15, 10) == "Critical Success"
    assert resolution._outcome_tier(10, 10) == "Success"
    assert resolution._outcome_tier(6, 10) == "Partial"
    assert resolution._outcome_tier(4, 10) == "Fail"


def test_reprisal_damage_scales_with_threat_and_multiplier():
    enemies = (Enemy(name="A", threat_tier=2), Enemy(name="B", threat_tier=2))

    assert resolution._reprisal_damage(enemies, 1.0) == 6  # (2+2)*1.5
    assert resolution._reprisal_damage(enemies, 0.5) == 3
    assert resolution._reprisal_damage(enemies, 0.0) == 0


def test_reprisal_damage_is_zero_with_no_enemies():
    assert resolution._reprisal_damage((), 1.0) == 0


# ---------- resolve_round: attack ----------


def test_attack_critical_success_defeats_highest_threat_enemy_no_reprisal():
    encounter = _sample_encounter()
    scored = score_encounter(encounter)
    target = resolution._target_number(
        next(a for a in scored.ranked_actions if a.action == "attack").overall_score
    )

    new_encounter, outcome, status = resolution.resolve_round(
        encounter, "attack", _FixedRng(roll=target + 5)
    )

    assert outcome.outcome_tier == "Critical Success"
    assert outcome.enemy_defeated == "Orc Raider"
    assert len(new_encounter.enemies) == len(encounter.enemies) - 1
    assert outcome.hp_delta == 0
    assert new_encounter.character.hp_current == encounter.character.hp_current
    assert status == "in_progress"


def test_attack_fail_defeats_nothing_and_deals_extra_reprisal():
    encounter = _sample_encounter()

    new_encounter, outcome, status = resolution.resolve_round(
        encounter, "attack", _FixedRng(roll=-100)
    )

    assert outcome.outcome_tier == "Fail"
    assert outcome.enemy_defeated is None
    assert len(new_encounter.enemies) == len(encounter.enemies)
    expected_damage = resolution._reprisal_damage(
        encounter.enemies, resolution.OFFENSIVE_FAIL_MULTIPLIER
    )
    assert outcome.hp_delta == -expected_damage
    assert new_encounter.character.hp_current == max(
        0, encounter.character.hp_current - expected_damage
    )
    assert status == "in_progress"


def test_skirmisher_gets_attack_bonus_against_a_lone_enemy():
    base = _sample_encounter()
    skirmisher = replace(base.character, archetype="skirmisher")
    lone_enemy_encounter = replace(
        base, character=skirmisher, enemies=(Enemy(name="Last One", threat_tier=2),)
    )
    scored = score_encounter(lone_enemy_encounter)
    target = resolution._target_number(
        next(a for a in scored.ranked_actions if a.action == "attack").overall_score
    )
    # a roll 3 below target would fail without the +3 Opportunist bonus,
    # but should land as exactly a Success once the bonus applies
    new_encounter, outcome, _ = resolution.resolve_round(
        lone_enemy_encounter, "attack", _FixedRng(roll=target - 3)
    )

    assert outcome.roll == target
    assert outcome.outcome_tier == "Success"
    assert outcome.enemy_defeated == "Last One"
    assert len(new_encounter.enemies) == 0
    assert "Opportunist" in (outcome.skill_note or "")


# ---------- resolve_round: use_ability ----------


def test_use_ability_spends_one_resource_for_non_mage_when_available():
    encounter = _sample_encounter()  # warrior, resources 1/3
    scored = score_encounter(encounter)
    target = resolution._target_number(
        next(a for a in scored.ranked_actions if a.action == "use_ability").overall_score
    )

    new_encounter, outcome, _ = resolution.resolve_round(
        encounter, "use_ability", _FixedRng(roll=target + 5)
    )

    assert outcome.resource_delta == -1
    assert new_encounter.character.resources_current == 0


def test_use_ability_with_no_resources_gets_harder_target_and_spends_nothing():
    base = _sample_encounter()
    depleted = replace(base, character=replace(base.character, resources_current=0))
    scored = score_encounter(depleted)
    base_target = resolution._target_number(
        next(a for a in scored.ranked_actions if a.action == "use_ability").overall_score
    )

    _, outcome, _ = resolution.resolve_round(
        depleted, "use_ability", _FixedRng(roll=base_target + 2)
    )

    assert outcome.resource_delta == 0
    assert outcome.target_number == min(resolution.MAX_TARGET, base_target + 3)


def test_mage_arcane_focus_spends_two_resources_and_gets_roll_bonus():
    base = _sample_encounter()
    mage_encounter = replace(
        base, character=replace(base.character, archetype="mage", resources_current=3)
    )
    scored = score_encounter(mage_encounter)
    target = resolution._target_number(
        next(a for a in scored.ranked_actions if a.action == "use_ability").overall_score
    )
    # a roll 2 below target would fail without the +3 Arcane Focus bonus
    new_encounter, outcome, _ = resolution.resolve_round(
        mage_encounter, "use_ability", _FixedRng(roll=target - 2)
    )

    assert outcome.roll == target + 1
    assert outcome.resource_delta == -2
    assert new_encounter.character.resources_current == 1
    assert "Arcane Focus" in (outcome.skill_note or "")


def test_support_rally_can_refund_the_resource_on_success():
    base = _sample_encounter()
    support_encounter = replace(base, character=replace(base.character, archetype="support"))
    scored = score_encounter(support_encounter)
    target = resolution._target_number(
        next(a for a in scored.ranked_actions if a.action == "use_ability").overall_score
    )

    new_encounter, outcome, _ = resolution.resolve_round(
        support_encounter, "use_ability", _FixedRng(roll=target + 5, chance=0.0)
    )

    original_resources = support_encounter.character.resources_current
    assert outcome.resource_delta == 0
    assert new_encounter.character.resources_current == original_resources
    assert "Rally" in (outcome.skill_note or "")


# ---------- resolve_round: defend ----------


def test_warrior_second_wind_always_fully_negates_defend_reprisal():
    base = _sample_encounter()
    warrior_encounter = replace(base, character=replace(base.character, archetype="warrior"))

    _, outcome, _ = resolution.resolve_round(warrior_encounter, "defend", _FixedRng(roll=-100))

    assert outcome.hp_delta == 0
    assert "Second Wind" in (outcome.skill_note or "")


def test_non_warrior_defend_partial_tier_reduces_but_does_not_zero_damage():
    base = _sample_encounter()
    mage_encounter = replace(base, character=replace(base.character, archetype="mage"))
    scored = score_encounter(mage_encounter)
    target = resolution._target_number(
        next(a for a in scored.ranked_actions if a.action == "defend").overall_score
    )

    _, outcome, _ = resolution.resolve_round(
        mage_encounter, "defend", _FixedRng(roll=target - 3)
    )

    assert outcome.outcome_tier == "Partial"
    expected_damage = resolution._reprisal_damage(mage_encounter.enemies, 0.75)
    assert outcome.hp_delta == -expected_damage


# ---------- resolve_round: retreat ----------


def test_retreat_success_ends_session_with_no_damage():
    encounter = _sample_encounter()
    scored = score_encounter(encounter)
    target = resolution._target_number(
        next(a for a in scored.ranked_actions if a.action == "retreat").overall_score
    )

    _, outcome, status = resolution.resolve_round(
        encounter, "retreat", _FixedRng(roll=target + 5)
    )

    assert status == "retreated"
    assert outcome.hp_delta == 0


def test_retreat_failure_keeps_the_player_in_the_encounter():
    encounter = _sample_encounter()
    scored = score_encounter(encounter)
    target = resolution._target_number(
        next(a for a in scored.ranked_actions if a.action == "retreat").overall_score
    )

    _, outcome, status = resolution.resolve_round(
        encounter, "retreat", _FixedRng(roll=target - 3)
    )

    assert status == "in_progress"
    assert outcome.outcome_tier == "Partial"
    assert outcome.hp_delta < 0


def test_unknown_action_is_rejected():
    encounter = _sample_encounter()
    try:
        resolution.resolve_round(encounter, "flee_screaming", _FixedRng(roll=10))
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


# ---------- property tests across many seeded playthroughs ----------


def test_state_stays_valid_across_many_seeded_playthroughs():
    for seed in range(50):
        rng = random.Random(seed)
        encounter = _sample_encounter()
        status = "in_progress"
        rounds = 0

        while status == "in_progress" and rounds < 50:
            action = rng.choice(list(ACTION_LABELS))
            encounter, outcome, status = resolution.resolve_round(encounter, action, rng)

            assert encounter.character.hp_current >= 0
            assert encounter.character.resources_current >= 0
            assert len(encounter.enemies) >= 0
            assert outcome.outcome_tier in OUTCOME_TIERS
            assert status in {"in_progress", "victory", "defeat", "retreated"}
            rounds += 1

        assert rounds > 0


def test_resolve_round_never_sets_gm_narration():
    # purity guard: resolve_round is the deterministic core and must never
    # itself produce or attach AI narration -- that's only ever done by the
    # wiring layer (CLI/web) after the fact, via dataclasses.replace, per
    # ai/round_narrator.py's design.
    rng = random.Random(3)
    _, outcome, _ = resolution.resolve_round(_sample_encounter(), "attack", rng)

    assert outcome.gm_narration is None
