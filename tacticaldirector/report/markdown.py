"""Renders a TacticalResult (plus optional AI narrative) as a Markdown
tactical advisory."""

from __future__ import annotations

from tacticaldirector.models import TacticalResult


def render(result: TacticalResult, ai_narrative: dict | None = None) -> str:
    lines: list[str] = []
    c = result.encounter.character
    encounter = result.encounter

    lines.append(f"# TacticalDirector Advisory: {c.name}")
    lines.append("")
    lines.append(f"**Archetype:** {c.archetype.title()} (Level {c.level})  ")
    lines.append(f"**HP:** {c.hp_current}/{c.hp_max} ({c.hp_pct:.0%})  ")
    if c.resources_max:
        lines.append(f"**Resources:** {c.resources_current}/{c.resources_max}  ")
    lines.append(f"**Round:** {encounter.round_number}")
    lines.append("")

    if encounter.enemies:
        enemy_list = ", ".join(f"{e.name} (threat {e.threat_tier})" for e in encounter.enemies)
        lines.append(f"**Enemies:** {enemy_list}")
    else:
        lines.append("**Enemies:** none")

    terrain_flags = [
        flag
        for flag, present in (
            ("high ground", encounter.terrain.high_ground),
            ("cover", encounter.terrain.cover),
            ("hazard", encounter.terrain.hazard),
        )
        if present
    ]
    lines.append(f"**Terrain:** {', '.join(terrain_flags) if terrain_flags else 'none'}")
    lines.append("")

    lines.append("## Recommended actions (ranked)")
    lines.append("")
    for i, action in enumerate(result.ranked_actions, start=1):
        lines.append(f"### {i}. {action.label}: {action.overall_score:.2f} ({action.tier})")
        lines.append("")
        for category in action.category_scores:
            lines.append(f"- **{category.label}** ({category.score}/4): {category.reason}")
        lines.append("")

    if ai_narrative:
        lines.append("## Game Master's take")
        lines.append("")
        lines.append(ai_narrative.get("narration", "").strip())
        lines.append("")
        table_talk = ai_narrative.get("table_talk")
        if table_talk:
            lines.append(f"*{table_talk}*")
            lines.append("")
        lowest_note = ai_narrative.get("lowest_ranked_note")
        if lowest_note:
            lines.append(f"**Why the last option ranked low:** {lowest_note}")
            lines.append("")

    return "\n".join(lines)
