# TacticalDirector

[![CI](https://github.com/Barak-Nisim/tacticaldirector/actions/workflows/ci.yml/badge.svg)](https://github.com/Barak-Nisim/tacticaldirector/actions/workflows/ci.yml)

AI-assisted tactical combat advisor for tabletop RPG combat. Describe one round of combat (your character, the enemies, the terrain), and TacticalDirector scores four tactical actions, Attack, Use Ability, Defend, Retreat, against four categories, ranks them, and explains every score. Optionally, Claude adds a short "Game Master's take" narrating the top recommendation. It never picks for you.

This is an original, generic combat model inspired by common tabletop RPG mechanics. It doesn't reproduce any published ruleset's rules text and isn't tied to or affiliated with a specific commercial game.

The scoring engine is deterministic, unit-tested, and has zero dependency on any AI service. The AI layer is a separate, optional piece bolted on top of it, same split as [RiskLens](https://github.com/Barak-Nisim/risklens) and [MarketSignal](https://github.com/Barak-Nisim/marketsignal). See [`docs/architecture.md`](docs/architecture.md) for why, and [`docs/scoring_methodology.md`](docs/scoring_methodology.md) for the exact scoring rules.

## Quickstart

```bash
pip install -e ".[dev]"

# Deterministic advisory, no API key needed
tacticaldirector advise examples/sample_encounter.yaml --no-ai
```

Sample output (excerpt):

```
# TacticalDirector Advisory: Kaelen

**Archetype:** Warrior (Level 5)
**HP:** 18/45 (40%)
**Resources:** 1/3
**Round:** 4

**Enemies:** Orc Raider (threat 3), Orc Raider (threat 3), Goblin Archer (threat 1)
**Terrain:** cover

## Recommended actions (ranked)

### 1. Use Ability: 2.75 (Great)

- **Offensive Value** (3/4): A warrior's ability adds meaningful damage alongside attacking.
- **Survival Risk** (2/4): Using an ability carries similar risk to attacking this turn.
- **Resource Efficiency** (3/4): A reasonable use of available resources for this encounter.
- **Positional Advantage** (3/4): Cover makes it safer to commit to using an ability.

### 2. Defend: 2.75 (Great)
...
```

### With AI narration

Copy `.env.example` to `.env`, add an `ANTHROPIC_API_KEY`, then drop `--no-ai`:

```bash
tacticaldirector advise examples/sample_encounter.yaml
```

This adds a "Game Master's take": a short narration of the top recommendation, a line of table talk, and a note on why the lowest-ranked action ranked where it did, generated from the same scored actions above (the AI narrates them, it doesn't recompute them).

## Running your own encounter

Write a scenario file in the same shape as `examples/sample_encounter.yaml`: a character (archetype, level, HP, resources), a list of enemies (name and threat tier 1-5), and terrain flags (high ground, cover, hazard).

## Web UI

```bash
tacticaldirector serve
```

Opens a small product site at `http://127.0.0.1:8002`:

- `/` -- a landing page explaining what TacticalDirector does, why it matters, and how it's different
- `/how-it-works` -- a walkthrough of the actual scoring methodology (not a simplified version of it)
- `/app` -- the live demo: character fields, five enemy slots, and terrain checkboxes, pre-filled with the sample encounter. Submitting it ranks all four actions and shows a collapsed "View as YAML" section for anyone who wants to see the underlying data

All three pages sit on top of the same scoring engine, loader, and AI narrator the CLI uses. Not deployed publicly.

## Development

```bash
pytest      # 31 tests, all mocked where they touch the AI layer -- no network calls, no cost
ruff check .
```

## Status

Core scoring engine, CLI, deterministic and AI-narrated reports, and a local web UI are all working end to end. See [open issues](https://github.com/Barak-Nisim/tacticaldirector/issues) and [`docs/enhancements.md`](docs/enhancements.md) for what's next.

## License

MIT
