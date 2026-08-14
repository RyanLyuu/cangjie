from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapter import default_run_dir
from .service import TypeResolutionService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the v2 Java-to-Cangjie type-resolution protocol")
    parser.add_argument("--project", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--temperature", required=True)
    parser.add_argument("--suffix", default="")
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--events-in", default="", help="JSONL ToolObservation/ResolutionDecision events")
    parser.add_argument("--overrides", default="", help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--apply", action="store_true", help="materialize v2 records into schema slots")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    schema_dir = Path(f"data/java/schemas{args.suffix}/{args.model}/{args.temperature}/{args.project}")
    if not schema_dir.is_dir():
        raise SystemExit(f"schema directory not found: {schema_dir}")
    output_dir = Path(args.output_dir) if args.output_dir else default_run_dir(
        args.project, args.model, args.temperature, args.suffix
    )
    _, _, summary = TypeResolutionService().resolve_project(
        schema_dir,
        project=args.project,
        include_tests=args.include_tests,
        events_path=args.events_in or args.overrides or None,
        apply=args.apply,
        output_dir=output_dir,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
