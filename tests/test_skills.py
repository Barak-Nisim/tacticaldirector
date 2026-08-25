import random

from tacticaldirector.models import Character, Encounter, Enemy, Terrain
from tacticaldirector.play.skills import (
    SKILLS,
    defend_reprisal_override,
    maybe_refund_resource,
    resource_cost_for_use_ability,
    roll_bonus_for_action,
)


def _character(archetype: str, resources_current: int = 3) -> Character:
    return Character(
        name="Test",
        archetype=archetype,
        level=1,
        hp_current=10,
        hp_max=10,
        resources_current=resources_current,
        resources_max=3,
    )


def _encounter(archetype: str, enemy_count: int = 2, resources_current: int = 3) -> Encounter:
    enemies = tuple(Enemy(name=f"Foe {i}", threat_tier=2) for i in range(enemy_count))
    return Encounter(
        character=_character(archetype, resources_current), enemies=enemies, terrain=Terrain()
    )


def test_all_four_archetypes_have_a_skill():
    assert set(SKILLS) == {"warrior", "mage", "skirmisher", "support"}


def test_mage_arcane_focus_costs_two_resources_when_affordable():
    encounter = _encounter("mage", resources_current=3)

    assert resource_cost_for_use_ability("mage", encounter) == 2


def test_mage_arcane_focus_falls_back_to_one_resource_when_low():
    encounter = _encounter("mage", resources_current=1)

    assert resource_cost_for_use_ability("mage", encounter) == 1


def test_non_mage_always_costs_one_resource():
    encounter = _encounter("warrior", resources_current=3)

    assert resource_cost_for_use_ability("warrior", encounter) == 1


def test_mage_gets_roll_bonus_on_use_ability_when_affording_full_cost():
    encounter = _encounter("mage", resources_current=3)

    adjustment = roll_bonus_for_action("mage", "use_ability", encounter)

    assert adjustment.roll_bonus == 3
    assert "Arcane Focus" in adjustment.note


def test_mage_gets_no_bonus_when_resources_too_low():
    encounter = _encounter("mage", resources_current=1)

    adjustment = roll_bonus_for_action("mage", "use_ability", encounter)

    assert adjustment.roll_bonus == 0


def test_skirmisher_gets_bonus_on_attack_against_lone_enemy():
    encounter = _encounter("skirmisher", enemy_count=1)

    adjustment = roll_bonus_for_action("skirmisher", "attack", encounter)

    assert adjustment.roll_bonus == 3
    assert "Opportunist" in adjustment.note


def test_skirmisher_gets_no_bonus_with_multiple_enemies():
    encounter = _encounter("skirmisher", enemy_count=2)

    adjustment = roll_bonus_for_action("skirmisher", "attack", encounter)

    assert adjustment.roll_bonus == 0


def test_other_archetypes_get_no_roll_bonus():
    encounter = _encounter("warrior", enemy_count=1)

    assert roll_bonus_for_action("warrior", "attack", encounter).roll_bonus == 0
    assert roll_bonus_for_action("support", "use_ability", encounter).roll_bonus == 0


def test_warrior_defend_reprisal_is_always_overridden():
    assert defend_reprisal_override("warrior") is True
    assert defend_reprisal_override("mage") is False


def test_support_rally_refund_only_applies_to_successful_use_ability():
    rng = random.Random(1)

    assert maybe_refund_resource("support", "attack", "Success", rng) is False
    assert maybe_refund_resource("mage", "use_ability", "Success", rng) is False
    assert maybe_refund_resource("support", "use_ability", "Fail", rng) is False


def test_support_rally_refund_is_seeded_and_reproducible():
    outcomes_a = [
        maybe_refund_resource("support", "use_ability", "Success", random.Random(seed))
        for seed in range(20)
    ]
    outcomes_b = [
        maybe_refund_resource("support", "use_ability", "Success", random.Random(seed))
        for seed in range(20)
    ]

    assert outcomes_a == outcomes_b
    assert any(outcomes_a)  # some seeds should refund
    assert not all(outcomes_a)  # some seeds should not
