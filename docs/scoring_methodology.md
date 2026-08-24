# Scoring Methodology

TacticalDirector scores four tactical actions, Attack, Use Ability, Defend, Retreat, on a 0-4 scale across four categories, then averages each action's category scores into an overall ranking. This document explains every rule in plain terms. The full implementation is in `tacticaldirector/scoring.py` and is unit-tested in `tests/test_scoring.py`.

## The scoring scale

Every category score uses the same 5-point scale:

| Score | Meaning |
|---|---|
| 0 | Poor |
| 1 | Situational |
| 2 | Solid |
| 3 | Great |
| 4 | Optimal |

## The four categories

### Offensive Value

How much this action advances the fight this turn.

- **Attack**: 4 for warrior, mage, or skirmisher (attacking is core to their kit); 2 for support.
- **Use Ability**: 4 for mage (primary damage source), 3 for warrior/skirmisher, 1 for support (usually utility-focused, not offensive).
- **Defend**: always 1 (can create openings, doesn't directly advance the fight).
- **Retreat**: always 0 (deals no damage this turn).

### Survival Risk (higher = safer)

- **Attack**: starts at 2, -1 if HP is below 35%, -1 if 3 or more enemies are present.
- **Use Ability**: starts at 2 (+1 for support, who often get some self-preservation value from their ability), -1 if HP is below 35%.
- **Defend**: 4, or 3 if terrain has a hazard (defending near a hazard is safer than attacking, but not risk-free).
- **Retreat**: 4 if HP is below 35% (disengaging is the safest play when HP is critical), 3 if HP is below 75%, 1 if HP is healthy (retreating wastes the turn without a safety need).

### Resource Efficiency

- **Attack, Defend, Retreat**: always 3 (these conserve resources by default).
- **Use Ability**: 0 if there's no resource pool at all. Otherwise, depends on remaining resource percentage vs. encounter threat level (average enemy threat tier):
  - Resources at or below 25% and threat below 2: **0** (spending a nearly-depleted pool on a low-threat encounter).
  - Resources at or below 25% and threat at or above 2: **2** (low resources, but the encounter is threatening enough to warrant it).
  - Resources above 25% and threat at or above 4: **4** (plenty of resources remain and this is a genuinely dangerous encounter).
  - Otherwise: **3** (a reasonable use of available resources).

### Positional Advantage

Terrain flags: high ground, cover, hazard.

- **Attack**: starts at 2, +1 for high ground, -1 if hazard is present without cover.
- **Use Ability**: starts at 2, +1 for cover (safer to commit to an extended action).
- **Defend**: starts at 2, +1 for cover, +1 for hazard (defending near cover and/or a hazard is a strong positional choice).
- **Retreat**: starts at 2, +1 for hazard (retreating away from a hazard is sound), -1 for high ground (retreating from high ground gives up a positional advantage).

All category scores are clamped to the 0-4 range after adjustments.

## Overall score and tiers

An action's overall score is the plain average of its four category scores:

```
overall_score = (offensive_value + survival_risk + resource_efficiency + positional_advantage) / 4
```

The overall score maps to a tier for readability:

| Score range | Tier |
|---|---|
| 0.0 – 0.8 | Poor |
| 0.8 – 1.6 | Situational |
| 1.6 – 2.4 | Solid |
| 2.4 – 3.2 | Great |
| 3.2 – 4.0 | Optimal |

All four actions are always scored and shown, sorted highest to lowest. There is no hidden curve and no machine-learned model deciding the ranking; anyone reading a TacticalDirector report can recompute every number by hand from the category scores and reasons already on the page.

## What the AI layer does and doesn't do

The AI narrator (`ai/narrator.py`) receives the fully-computed `TacticalResult` as structured JSON (the ranked actions, their category scores and reasons) and is explicitly instructed to narrate the top recommendation and add a line of table talk, not to recompute or reorder the ranking, and not to invent enemies or rules that weren't part of the input. If you disagree with a ranking, the fix is in the scoring rules above, not in the AI layer.
