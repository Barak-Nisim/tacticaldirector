from dataclasses import replace

from tacticaldirector.intel import predict_enemy_intents, render_enemy_intel
from tacticaldirector.loader import load_encounter
from tacticaldirector.models import Encounter, Enemy, Terrain


def _sample_encounter():
    return load_encounter("examples/sample_encounter.yaml")


def test_no_intents_when_no_enemies():
    encounter = replace(_sample_encounter(), enemies=())

    assert predict_enemy_intents(encounter) == ()


def test_every_enemy_gets_an_intent():
    encounter = _sample_encounter()

    intents = predict_enemy_intents(encounter)

    assert len(intents) == len(encounter.enemies)
    assert {i.enemy_name for i in intents} == {e.name for e in encounter.enemies}


def test_highest_threat_enemy_presses_the_attack_when_hp_is_critical():
    base = _sample_encounter()
    low_hp = replace(base.character, hp_current=5, hp_max=45)  # well below 35%
    encounter = replace(base, character=low_hp)

    intents = predict_enemy_intents(encounter)
    top_threat = max(e.threat_tier for e in encounter.enemies)
    leader_intent = next(i for i in intents if i.threat_tier == top_threat)

    assert leader_intent.predicted_action == "Press the attack"
    assert "critical" in leader_intent.reason.lower()


def test_leader_maneuvers_for_position_when_player_holds_high_ground():
    encounter = Encounter(
        character=replace(_sample_encounter().character, hp_current=40, hp_max=45),
        enemies=(Enemy(name="Bandit Captain", threat_tier=4),),
        terrain=Terrain(high_ground=True),
    )

    intents = predict_enemy_intents(encounter)

    assert intents[0].predicted_action == "Maneuver for position"
    assert "high ground" in intents[0].reason.lower()


def test_low_threat_enemy_supports_from_range():
    encounter = Encounter(
        character=replace(_sample_encounter().character, hp_current=40, hp_max=45),
        enemies=(
            Enemy(name="Warlord", threat_tier=5),
            Enemy(name="Scout", threat_tier=1),
        ),
        terrain=Terrain(),
    )

    intents = predict_enemy_intents(encounter)
    scout_intent = next(i for i in intents if i.enemy_name == "Scout")

    assert scout_intent.predicted_action == "Support from range"


def test_secondary_enemy_holds_behind_cover_when_available():
    encounter = Encounter(
        character=replace(_sample_encounter().character, hp_current=40, hp_max=45),
        enemies=(
            Enemy(name="Warlord", threat_tier=5),
            Enemy(name="Soldier", threat_tier=3),
        ),
        terrain=Terrain(cover=True),
    )

    intents = predict_enemy_intents(encounter)
    secondary_intent = next(i for i in intents if i.enemy_name == "Soldier")

    assert secondary_intent.predicted_action == "Hold behind cover"


def test_render_is_empty_string_with_no_intents():
    assert render_enemy_intel(()) == ""


def test_render_includes_every_enemy_and_reason():
    encounter = _sample_encounter()
    intents = predict_enemy_intents(encounter)

    text = render_enemy_intel(intents)

    assert "Enemy intelligence" in text
    for intent in intents:
        assert intent.enemy_name in text
        assert intent.predicted_action in text
