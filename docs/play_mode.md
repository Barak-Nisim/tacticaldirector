# Play Mode

Play Mode is a multi-round game layered on top of the Codex advisor described in
[`scoring_methodology.md`](scoring_methodology.md). It does not change the advisor: every round,
`score_encounter()` runs exactly as it always has, and Play Mode's resolution engine
(`tacticaldirector/play/`) consumes that output rather than recomputing or overriding it. This
document explains the resolution mechanic in the same plain terms as the advisor's own docs, and
is implemented in `tacticaldirector/play/resolution.py`, unit-tested in `tests/test_resolution.py`.

## How a round resolves

1. **The Codex ranks the four actions** for the current state, exactly as in single-round mode.
2. **You choose one.** Its target number comes from its own `overall_score` (0-4), not a separate
   stat system:

   ```
   target_number = clamp(round(20 - overall_score * 3.5), 5, 19)
   ```

   A score of 4.0 gives a target around 6 (easy); a score of 0.0 gives a target around 19 (hard,
   clamped from the raw 20). The die roll is always traceable back to the number already on
   screen.
3. **A d20 is rolled** (`random.Random.randint(1, 20)`, always an explicitly seeded/injected
   instance, never Python's global `random` state) against that target:

   | Roll vs. target | Outcome tier |
   |---|---|
   | `roll >= target + 5` | Critical Success |
   | `roll >= target` | Success |
   | `roll >= target - 5` | Partial |
   | otherwise | Fail |

4. **The action's effect** depends on the tier:

   - **Attack** targets the highest-threat remaining enemy. Critical Success or Success defeats
     that enemy outright, one hit per enemy (no separate enemy-HP subsystem). Fail deals 1.5x the
     baseline enemy reprisal instead of the usual amount.
   - **Use Ability** behaves like Attack, and costs 1 resource if available. If the character can't
     afford the cost, the target number gets a flat +3 penalty instead of blocking the action
     entirely, so it's usable but weaker when resources are thin.
   - **Defend** doesn't target an enemy. Its outcome tier instead sets how much of the enemies'
     reprisal damage is mitigated this round: fully negated on a Critical Success, halved on a
     Success, reduced by a quarter on a Partial, unmitigated on a Fail.
   - **Retreat** ends the session immediately as `retreated` (a clean, non-loss exit, no damage) on
     a Critical Success or Success. On a Partial or Fail, the escape attempt fails, the character
     takes the round's reprisal, and they remain in the encounter.

5. **Enemy reprisal**, when it applies, is:

   ```
   base = sum(threat_tier for each remaining enemy) * 1.5
   damage = round(base * outcome_multiplier)
   ```

   | Outcome tier | Multiplier (Attack / Use Ability) | Multiplier (Defend mitigation) |
   |---|---|---|
   | Critical Success | 0.0 | 0.0 |
   | Success | 0.5 | 0.5 |
   | Partial | 0.75 | 0.75 |
   | Fail | 1.5 | 1.0 |

   Damage is subtracted from the character's current HP, floored at 0.

6. **The session ends** the moment all enemies are defeated (`victory`), HP reaches 0 (`defeat`),
   or a Retreat succeeds (`retreated`). Otherwise it's `in_progress` and the Codex re-ranks against
   the now-updated encounter for the next round.

Because a defeated enemy is removed from the encounter, the *existing* `Encounter.threat_level`
property and the *existing* enemy-count check in `scoring.py`'s Survival Risk category respond
automatically on the next round's ranking. No new scoring logic was written for this; it's the
same reason Play Mode's core mechanic is "one hit, one enemy" instead of a separate per-enemy HP
bar.

## Archetype skills

Each archetype gets one skill, implemented as a small, pure modifier on the roll or the resource
cost above, not a new mechanic:

| Archetype | Skill | Effect |
|---|---|---|
| Warrior | Second Wind | On Defend, reprisal is always fully negated, regardless of outcome tier. |
| Mage | Arcane Focus | On Use Ability, +3 to the roll, at a cost of 2 resources instead of 1 when 2 are available (falls back to the normal 1-resource cost otherwise). |
| Skirmisher | Opportunist | On Attack, +3 to the roll when only one enemy remains. |
| Support | Rally | On a successful Use Ability, a 50% chance to refund the resource just spent. |

## Optional AI round narration

By default a round's outcome is a deterministic, plain-language string from `resolution.py`. Passing
`--narrate` to `tacticaldirector play` adds an opt-in "Game Master's take" per round: after the
round is fully resolved, `ai/round_narrator.py` sends the already-decided result (roll, target,
outcome tier, HP/resource deltas, `narrative_hint`) to Claude and prints a short dramatization plus
a line of table talk. It never changes the roll or the outcome -- `narrative_hint` is the canonical
fact and the prompt forbids contradicting it. The narration is stored on `RoundOutcome.gm_narration`
in the session file (`PlaySession.narrate` records that the session opted in). It needs
`ANTHROPIC_API_KEY`; without one the CLI prints a warning and plays on without narration, and a
failed API call skips only that round's narration rather than ending the session. The web UI does
not expose this yet.

## A note on reproducibility

A session's `seed` makes it reproducible only within the surface that ran it. The CLI's
interactive/scripted loop keeps one continuous `random.Random(seed)` instance for the whole
session; the web UI re-seeds per round as `random.Random(seed + rounds_played)`, since each HTTP
request is a fresh process with no live RNG state to carry over. Both are internally consistent
and reproducible on repeat runs of the same surface, but the same seed will not produce an
identical round-by-round sequence between the CLI and the web UI. This is a deliberate, documented
tradeoff, not a bug.

## What Play Mode does not do (yet)

Round *resolution* is never AI-driven: outcomes are deterministic, plain-language strings from
`resolution.py`, and the optional `--narrate` layer (above) only dramatizes a result it cannot
change. The web UI has no round narration yet. See [`enhancements.md`](enhancements.md) for other
deliberately deferred ideas (multi-character parties, status effects, a fifth "Use Item" action,
and more).
