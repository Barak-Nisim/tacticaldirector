"""TacticalDirector CLI: tacticaldirector advise <scenario.yaml> [options]"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import replace
from pathlib import Path

from tacticaldirector.loader import load_encounter
from tacticaldirector.models import ACTION_LABELS
from tacticaldirector.play.resolution import resolve_round
from tacticaldirector.play.session import save_session, start_session
from tacticaldirector.report.markdown import render
from tacticaldirector.scoring import score_encounter

SCENARIOS_DIR = Path("examples/scenarios")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tacticaldirector")
    subparsers = parser.add_subparsers(dest="command", required=True)

    advise = subparsers.add_parser("advise", help="Rank tactical actions for a combat encounter")
    advise.add_argument("scenario", help="Path to a scenario YAML file")
    advise.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip the AI narration and render the deterministic advisory only",
    )
    advise.add_argument(
        "--output",
        "-o",
        metavar="PATH",
        help="Write the report to a file instead of stdout",
    )

    serve = subparsers.add_parser("serve", help="Run the TacticalDirector web UI locally")
    serve.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8002, help="Bind port (default: 8002)")
    serve.add_argument("--reload", action="store_true", help="Auto-reload on code changes")

    play = subparsers.add_parser("play", help="Play a multi-round combat session")
    play.add_argument("scenario", help="Path to a scenario YAML file")
    play.add_argument("--seed", type=int, default=None, help="RNG seed, for a reproducible session")
    play.add_argument(
        "--script",
        default=None,
        metavar="ACTIONS",
        help="Comma-separated actions (e.g. attack,defend,retreat) for a scripted playthrough",
    )

    subparsers.add_parser("scenarios", help="List the built-in starter scenarios")

    return parser


def _run_advise(args: argparse.Namespace) -> int:
    encounter = load_encounter(args.scenario)
    result = score_encounter(encounter)

    ai_narrative = None
    if not args.no_ai:
        from tacticaldirector.ai.narrator import generate_narrative

        ai_narrative = generate_narrative(result)

    report = render(result, ai_narrative=ai_narrative)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    return 0


def _run_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "tacticaldirector.web.app:app", host=args.host, port=args.port, reload=args.reload
    )
    return 0


def _format_outcome(outcome) -> str:
    lines = [
        f">> {outcome.label}: rolled {outcome.roll} vs target {outcome.target_number}"
        f" -> {outcome.outcome_tier}",
        outcome.narrative_hint,
    ]
    if outcome.skill_note:
        lines.append(outcome.skill_note)
    if outcome.hp_delta:
        lines.append(f"HP change: {outcome.hp_delta:+d}")
    if outcome.resource_delta:
        lines.append(f"Resources change: {outcome.resource_delta:+d}")
    return "\n".join(lines)


def _run_play(args: argparse.Namespace) -> int:
    encounter = load_encounter(args.scenario)
    scenario_id = Path(args.scenario).stem
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(1_000_000)
    rng = random.Random(seed)

    session = start_session(scenario_id, encounter, seed)
    print(f"Starting session {session.session_id} (scenario: {scenario_id}, seed: {seed})\n")

    script = [a.strip() for a in args.script.split(",")] if args.script else None
    script_index = 0

    while session.status == "in_progress":
        result = score_encounter(session.encounter)
        print(render(result))

        if script is not None:
            if script_index >= len(script):
                print("Script exhausted; ending session early.", file=sys.stderr)
                break
            action = script[script_index]
            script_index += 1
            print(f"> {action}")
        else:
            action = input("Choose an action (attack/use_ability/defend/retreat): ").strip().lower()

        if action not in ACTION_LABELS:
            print(f"Unknown action: {action}", file=sys.stderr)
            continue

        new_encounter, outcome, status = resolve_round(session.encounter, action, rng)
        print("\n" + _format_outcome(outcome) + "\n")

        session = replace(
            session,
            encounter=new_encounter,
            round_log=session.round_log + (outcome,),
            status=status,
        )
        save_session(session)

    print(f"Session {session.status}. {len(session.round_log)} round(s) played.")
    return 0


def _run_scenarios(args: argparse.Namespace) -> int:
    if not SCENARIOS_DIR.exists():
        print(f"No scenarios found. Looked in {SCENARIOS_DIR}/.", file=sys.stderr)
        return 0

    paths = sorted(SCENARIOS_DIR.glob("*.yaml"))
    if not paths:
        print(f"No scenarios found. Looked in {SCENARIOS_DIR}/.", file=sys.stderr)
        return 0

    print("Available scenarios:")
    for path in paths:
        print(f"  {path.stem}  ({path})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "advise":
        return _run_advise(args)
    if args.command == "serve":
        return _run_serve(args)
    if args.command == "play":
        return _run_play(args)
    if args.command == "scenarios":
        return _run_scenarios(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
