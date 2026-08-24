from tacticaldirector.models import Character, Encounter, Enemy, Terrain
from tacticaldirector.scoring import score_encounter, tier_for_score


def _encounter(**overrides) -> Encounter:
    character = overrides.pop(
        "character",
        Character(
            name="Kaelen",
            archetype="warrior",
            level=5,
            hp_current=30,
            hp_max=40,
            resources_current=2,
            resources_max=3,
        ),
    )
    enemies = overrides.pop("enemies", (Enemy("Orc", 2), Enemy("Orc", 2)))
    terrain = overrides.pop("terrain", Terrain())
    return Encounter(character=character, enemies=enemies, terrain=terrain, **overrides)


def test_all_four_actions_are_always_ranked():
    result = score_encounter(_encounter())

    assert len(result.ranked_actions) == 4
    assert {a.action for a in result.ranked_actions} == {
        "attack",
        "use_ability",
        "defend",
        "retreat",
    }


def test_ranked_actions_are_sorted_highest_first():
    result = score_encounter(_encounter())

    scores = [a.overall_score for a in result.ranked_actions]
    assert scores == sorted(scores, reverse=True)


def test_critical_hp_makes_retreat_the_safest_survival_score():
    critical_character = Character(
        name="Kaelen",
        archetype="warrior",
        level=5,
        hp_current=5,
        hp_max=40,  # 12.5% HP
        resources_current=2,
        resources_max=3,
    )
    result = score_encounter(_encounter(character=critical_character))

    retreat = next(a for a in result.ranked_actions if a.action == "retreat")
    attack = next(a for a in result.ranked_actions if a.action == "attack")
    retreat_risk = next(c for c in retreat.category_scores if c.id == "survival_risk")
    attack_risk = next(c for c in attack.category_scores if c.id == "survival_risk")

    assert retreat_risk.score == 4  # Optimal safety when critical
    assert attack_risk.score < retreat_risk.score


def test_healthy_hp_makes_retreat_score_low_on_survival_since_its_unneeded():
    healthy_character = Character(
        name="Kaelen",
        archetype="warrior",
        level=5,
        hp_current=38,
        hp_max=40,  # 95% HP
        resources_current=3,
        resources_max=3,
    )
    result = score_encounter(_encounter(character=healthy_character))

    retreat = next(a for a in result.ranked_actions if a.action == "retreat")
    retreat_risk = next(c for c in retreat.category_scores if c.id == "survival_risk")

    assert retreat_risk.score == 1  # retreating when healthy wastes the turn


def test_use_ability_resource_efficiency_low_when_wasting_last_resource_on_weak_fight():
    character = Character(
        name="Kaelen",
        archetype="mage",
        level=5,
        hp_current=40,
        hp_max=40,
        resources_current=1,
        resources_max=4,  # 25% remaining
    )
    weak_encounter = _encounter(character=character, enemies=(Enemy("Rat", 1),))

    result = score_encounter(weak_encounter)
    use_ability = next(a for a in result.ranked_actions if a.action == "use_ability")
    efficiency = next(c for c in use_ability.category_scores if c.id == "resource_efficiency")

    assert efficiency.score == 0


def test_use_ability_resource_efficiency_high_with_resources_against_dangerous_fight():
    character = Character(
        name="Kaelen",
        archetype="mage",
        level=5,
        hp_current=40,
        hp_max=40,
        resources_current=4,
        resources_max=4,
    )
    dangerous_encounter = _encounter(
        character=character, enemies=(Enemy("Dragon", 5), Enemy("Dragon", 5))
    )

    result = score_encounter(dangerous_encounter)
    use_ability = next(a for a in result.ranked_actions if a.action == "use_ability")
    efficiency = next(c for c in use_ability.category_scores if c.id == "resource_efficiency")

    assert efficiency.score == 4


def test_use_ability_with_no_resource_pool_scores_zero_efficiency():
    character = Character(
        name="Kaelen",
        archetype="warrior",
        level=1,
        hp_current=20,
        hp_max=20,
        resources_current=0,
        resources_max=0,
    )
    result = score_encounter(_encounter(character=character))

    use_ability = next(a for a in result.ranked_actions if a.action == "use_ability")
    efficiency = next(c for c in use_ability.category_scores if c.id == "resource_efficiency")

    assert efficiency.score == 0


def test_high_ground_favors_attack_and_penalizes_retreat_positioning():
    result = score_encounter(_encounter(terrain=Terrain(high_ground=True)))

    attack = next(a for a in result.ranked_actions if a.action == "attack")
    retreat = next(a for a in result.ranked_actions if a.action == "retreat")
    attack_pos = next(c for c in attack.category_scores if c.id == "positional_advantage")
    retreat_pos = next(c for c in retreat.category_scores if c.id == "positional_advantage")

    assert attack_pos.score == 3
    assert retreat_pos.score == 1


def test_no_enemies_gives_zero_threat_level_and_still_scores_all_actions():
    result = score_encounter(_encounter(enemies=()))

    assert result.encounter.threat_level == 0.0
    assert len(result.ranked_actions) == 4


def test_every_category_score_has_a_reason():
    result = score_encounter(_encounter())

    for action in result.ranked_actions:
        for category in action.category_scores:
            assert category.reason
            assert isinstance(category.reason, str)


def test_tier_for_score_boundaries():
    assert tier_for_score(0.0) == "Poor"
    assert tier_for_score(0.79) == "Poor"
    assert tier_for_score(0.8) == "Situational"
    assert tier_for_score(1.6) == "Solid"
    assert tier_for_score(2.4) == "Great"
    assert tier_for_score(3.2) == "Optimal"
    assert tier_for_score(4.0) == "Optimal"
