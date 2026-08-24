"""Loads a combat scenario (character + enemies + terrain) from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from tacticaldirector.models import Character, Encounter, Enemy, Terrain


def load_encounter(path: str | Path) -> Encounter:
    return parse_encounter(Path(path).read_text(encoding="utf-8"))


def parse_encounter(yaml_text: str) -> Encounter:
    raw = yaml.safe_load(yaml_text)

    char_raw = raw["character"]
    character = Character(
        name=char_raw["name"],
        archetype=char_raw["archetype"].lower(),
        level=int(char_raw.get("level", 1)),
        hp_current=int(char_raw["hp_current"]),
        hp_max=int(char_raw["hp_max"]),
        resources_current=int(char_raw.get("resources_current", 0)),
        resources_max=int(char_raw.get("resources_max", 0)),
    )

    enemies = tuple(
        Enemy(name=e["name"], threat_tier=int(e["threat_tier"])) for e in raw.get("enemies", [])
    )

    terrain_raw = raw.get("terrain", {})
    terrain = Terrain(
        high_ground=bool(terrain_raw.get("high_ground", False)),
        cover=bool(terrain_raw.get("cover", False)),
        hazard=bool(terrain_raw.get("hazard", False)),
    )

    return Encounter(
        character=character,
        enemies=enemies,
        terrain=terrain,
        round_number=int(raw.get("round_number", 1)),
    )


def dump_encounter(encounter: Encounter) -> str:
    """Serializes an Encounter back to the same YAML shape parse_encounter
    reads -- used for the report's engineering view."""
    c = encounter.character
    raw = {
        "character": {
            "name": c.name,
            "archetype": c.archetype,
            "level": c.level,
            "hp_current": c.hp_current,
            "hp_max": c.hp_max,
            "resources_current": c.resources_current,
            "resources_max": c.resources_max,
        },
        "enemies": [{"name": e.name, "threat_tier": e.threat_tier} for e in encounter.enemies],
        "terrain": {
            "high_ground": encounter.terrain.high_ground,
            "cover": encounter.terrain.cover,
            "hazard": encounter.terrain.hazard,
        },
        "round_number": encounter.round_number,
    }
    return yaml.safe_dump(raw, sort_keys=False, allow_unicode=True)
