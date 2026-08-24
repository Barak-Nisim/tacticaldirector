from tacticaldirector.loader import dump_encounter, load_encounter, parse_encounter


def test_load_encounter_parses_sample():
    encounter = load_encounter("examples/sample_encounter.yaml")

    assert encounter.character.name == "Kaelen"
    assert encounter.character.archetype == "warrior"
    assert encounter.character.hp_current == 18
    assert encounter.character.hp_max == 45
    assert len(encounter.enemies) == 3
    assert encounter.terrain.cover is True
    assert encounter.terrain.high_ground is False
    assert encounter.round_number == 4


def test_character_hp_and_resource_percentages():
    encounter = load_encounter("examples/sample_encounter.yaml")

    assert round(encounter.character.hp_pct, 2) == 0.4
    assert round(encounter.character.resource_pct, 2) == round(1 / 3, 2)


def test_encounter_threat_level_averages_enemy_tiers():
    encounter = load_encounter("examples/sample_encounter.yaml")

    # (3 + 3 + 1) / 3 = 2.33...
    assert round(encounter.threat_level, 2) == round(7 / 3, 2)


def test_encounter_with_no_enemies_has_zero_threat_level():
    encounter = parse_encounter(
        """
        character:
          name: Solo
          archetype: mage
          hp_current: 10
          hp_max: 10
          resources_current: 2
          resources_max: 2
        """
    )

    assert encounter.enemies == ()
    assert encounter.threat_level == 0.0


def test_dump_encounter_round_trips_through_parse_encounter():
    original = load_encounter("examples/sample_encounter.yaml")

    dumped = dump_encounter(original)
    reloaded = parse_encounter(dumped)

    assert reloaded.character == original.character
    assert reloaded.enemies == original.enemies
    assert reloaded.terrain == original.terrain
    assert reloaded.round_number == original.round_number
