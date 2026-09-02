# Enhancement Roadmap

TacticalDirector v1 is stable: scoring engine, CLI, AI narrator, and a local web UI (marketing site + real encounter form) are all working and tested. This document is the parking lot for what could come next, ranked by effort, not by priority. Nothing here is committed to; it's a menu, not a schedule.

Effort tags: **Minor** (an evening), **Moderate** (a focused day or two), **Major** (a real feature, spans multiple files/decisions).

## Scenario model & scoring

1. **[Shipped]** ~~Multi-round encounters: carry HP, resources, and terrain forward across rounds instead of scoring one round in isolation, with a running log of past recommendations.~~ Shipped as Play Mode; see [`play_mode.md`](play_mode.md).
2. **[Moderate]** Party support: score actions for multiple player characters in the same encounter, accounting for ally positioning and focus-fire.
3. **[Moderate]** Additional archetypes beyond the current four (warrior, mage, skirmisher, support), each with its own offensive/ability weighting.
4. **[Minor]** Status effects (stunned, poisoned, buffed) as an encounter input that shifts Survival Risk and Offensive Value.
5. **[Major]** A fifth action, "Use Item," scored similarly to Use Ability but against a separate consumable-item resource pool.
6. **[Moderate]** Configurable difficulty presets that shift the threat-level thresholds in Resource Efficiency, so a GM running a harder campaign gets different guidance.
7. **[Minor]** Expose the tier boundaries (currently fixed at 0.8/1.6/2.4/3.2) as an optional CLI/web override.

## Web UI / UX

8. **[Moderate]** Dynamic enemy list (add/remove rows with JS) instead of five fixed slots, once the fixed-slot form has proven itself.
9. **[Shipped]** ~~A round-by-round session view: submit one encounter, get a recommendation, then advance to the next round with updated HP/resources carried forward.~~ Shipped as Play Mode; see [`play_mode.md`](play_mode.md).
10. **[Minor]** Live HP/resource percentage bars next to the character fields as you type.
11. **[Moderate]** Save/load encounters to a local file or browser `localStorage` so a half-built scenario survives a page refresh.
12. **[Minor]** Print-friendly stylesheet for the report page (`@media print`), useful for physical tabletop sessions.
13. **[Minor]** Manual dark/light theme toggle; currently the site only follows OS preference via `prefers-color-scheme`.
14. **[Moderate]** A compact "quick advise" mode: fewer fields, sensible defaults, for GMs who want a fast answer mid-session.
15. **[Minor]** Visual threat-tier indicator (icon or color) next to each enemy row instead of a plain number select.

## AI layer

16. **[Moderate]** Stream the Game Master's take token-by-token instead of waiting for the full response before rendering.
17. **[Minor]** Tone toggle for the narration (gritty/serious vs. lighthearted), since the current voice is fixed.
18. **[Major]** Let the AI generate flavor text for the enemies themselves (appearance, tactics) grounded in their threat tier, clearly separated from the scoring-driven recommendation.
19. **[Moderate]** Multi-turn follow-up ("why not Attack?") grounded in the same structured category scores the narrator already receives.
20. **[Minor]** Cache narratives for identical encounters so re-running the same submission doesn't re-spend tokens.

## Integrations

21. **[Major]** A Discord bot wrapper so a GM can run `/advise` directly in a game session channel.
22. **[Moderate]** Formalize a JSON API endpoint (not just HTML routes) so TacticalDirector could be called programmatically by a VTT (virtual tabletop) plugin.
23. **[Major]** Roll20 / Foundry VTT companion integration that reads character sheet data directly instead of manual entry.
24. **[Moderate]** Export a session's round-by-round recommendations as a shareable Markdown recap.
25. **[Minor]** A shareable read-only link for a single report, without exposing the full form.

## Engineering & quality

26. **[Minor]** Structured logging for the web app (local-only, no external telemetry).
27. **[Moderate]** Property-based tests (Hypothesis) for `scoring.py` to fuzz HP/resource/terrain combinations beyond the current fixed edge cases.
28. **[Moderate]** Dockerfile + docker-compose as an alternative to `pip install` for local setup.
29. **[Minor]** Add `mypy` or `pyright` to CI alongside the existing `ruff` lint step.
30. **[Moderate]** Snapshot/golden-file tests for the rendered Markdown and HTML report, to catch unintended template regressions that content-substring tests might miss.

## Play Mode follow-ons

Deliberately deferred out of Play Mode v1 (see [`play_mode.md`](play_mode.md) for what shipped):

31. **[Shipped]** ~~AI-narrated round outcomes (a "Game Master's take" per round), same structured-output pattern as the existing single-round narrator.~~ Shipped for the CLI via `play --narrate` (`ai/round_narrator.py`); the resolution engine stays fully AI-free and deterministic-given-a-seed, and the narrator only dramatizes an already-decided outcome. Web UI exposure is still open.
32. **[Minor]** Let the player choose which enemy an Attack/Use Ability targets, instead of always auto-targeting the highest-threat remaining enemy.
33. **[Moderate]** Party support in Play Mode: multiple player characters acting in the same session, sharing the enemies' reprisal.
34. **[Minor]** A "replay" view that renders a completed session's full round log as a shareable Markdown recap.
35. **[Moderate]** Play Mode-specific difficulty presets (an easier or harder target-number curve), distinct from the general scoring-threshold preset idea above.
36. **[Minor]** A visible seed input on the web scenario-start form; currently only reachable via the CLI's `--seed` flag or a hidden form field.
37. **[Moderate]** A shared RNG-advancement strategy between the CLI and web UI (e.g. persisting `random.getstate()` in the session file) so the same seed reproduces identical results on both surfaces, resolving the documented divergence in `play_mode.md`.

## Bigger bets (real architecture decisions, plan formally before building)

38. **[Major]** Build-aware recommendations: weapons, abilities, armor, cooldowns, status effects, and resistances materially changing what the Codex recommends, not just HP/resources/terrain/threat tier. This is a real expansion of `scoring.py` itself (currently deliberately minimal), not an additive module like everything else built so far -- needs a scoring-model redesign, not just new data fields.
