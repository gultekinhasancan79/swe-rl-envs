"""Command line entry point for ``runlog``."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .records import RecordError
from .report import format_json, format_text
from .rollup import build_rollup

EXIT_OK = 0
EXIT_BAD_RECORD = 2
EXIT_MISSING_FILE = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runlog",
        description="Summarize pipeline run-record files into one report.",
    )
    parser.add_argument(
        "paths",
        metavar="RECORD_FILE",
        nargs="+",
        help="newline-delimited JSON record file(s), typically one per shard",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "--skip-bad-lines",
        action="store_true",
        help="drop unparseable lines instead of failing the whole report",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        rollup = build_rollup(args.paths, strict=not args.skip_bad_lines)
    except FileNotFoundError as exc:
        print(f"runlog: no such record file: {exc.filename}", file=sys.stderr)
        return EXIT_MISSING_FILE
    except RecordError as exc:
        print(f"runlog: {exc}", file=sys.stderr)
        return EXIT_BAD_RECORD

    renderer = format_json if args.format == "json" else format_text
    print(renderer(rollup))
    return EXIT_OK
