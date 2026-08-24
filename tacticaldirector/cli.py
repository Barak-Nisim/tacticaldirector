"""TacticalDirector CLI: tacticaldirector advise <scenario.yaml> [options]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tacticaldirector.loader import load_encounter
from tacticaldirector.report.markdown import render
from tacticaldirector.scoring import score_encounter


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


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "advise":
        return _run_advise(args)
    if args.command == "serve":
        return _run_serve(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
