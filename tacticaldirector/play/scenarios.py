"""Locates and describes the built-in starter scenarios.

Flavor metadata (label, blurb) is kept here rather than in the scenario
YAML files themselves, so loader.py's Encounter parsing stays exactly
what it's always been -- unaware of Play Mode entirely.
"""

from __future__ import annotations

from pathlib import Path

SCENARIOS_DIR = Path(__file__).parent.parent.parent / "examples" / "scenarios"

SCENARIO_BLURBS: dict[str, dict[str, str]] = {
    "broken_bridge_ambush": {
        "label": "Broken Bridge Ambush",
        "blurb": (
            "A balanced fight on a narrow, half-collapsed bridge. "
            "Cover favors those who hold their ground."
        ),
    },
    "goblin_warcamp": {
        "label": "Goblin Warcamp",
        "blurb": "Many low-threat enemies, no single big danger. A numbers game.",
    },
    "lone_sentinel": {
        "label": "The Lone Sentinel",
        "blurb": (
            "One high-threat guardian, and a character already worn down. "
            "Caution may be the better part of valor."
        ),
    },
    "ambush_at_dusk": {
        "label": "Ambush at Dusk",
        "blurb": (
            "Resources are thin and the terrain is dangerous. "
            "Every ability spent has to count."
        ),
    },
}


def list_scenarios() -> list[dict[str, str]]:
    """Returns metadata for every scenario YAML file present, sorted by id."""
    if not SCENARIOS_DIR.exists():
        return []

    scenarios = []
    for path in sorted(SCENARIOS_DIR.glob("*.yaml")):
        scenario_id = path.stem
        meta = SCENARIO_BLURBS.get(scenario_id, {})
        scenarios.append(
            {
                "id": scenario_id,
                "label": meta.get("label", scenario_id.replace("_", " ").title()),
                "blurb": meta.get("blurb", "A hand-crafted encounter."),
                "path": str(path),
            }
        )
    return scenarios


def scenario_path(scenario_id: str) -> Path:
    return SCENARIOS_DIR / f"{scenario_id}.yaml"
