"""Command-line interface: ``tidytrail clean input.csv``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._version import __version__
from .core import clean_csv, format_report, write_csv, write_log


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tidytrail",
        description="Clean messy CSV exports and keep an auditable log of every change.",
    )
    parser.add_argument("--version", action="version", version=f"tidytrail {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    clean = subparsers.add_parser("clean", help="clean a CSV file")
    clean.add_argument("input", type=Path, help="CSV file to clean (it is never modified)")
    clean.add_argument("-o", "--output", type=Path, help="where to write the cleaned CSV")
    clean.add_argument("--log", type=Path, help="where to write the JSON change log")
    clean.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would change without writing the cleaned CSV",
    )
    clean.add_argument(
        "--dayfirst",
        action="store_true",
        help="read ambiguous dates such as 01/02/2026 as day/month instead of month/day",
    )
    clean.add_argument("--force", action="store_true", help="overwrite existing output files")
    return parser


def _run_clean(args: argparse.Namespace) -> int:
    source: Path = args.input
    if not source.is_file():
        print(f"error: {source} is not a file", file=sys.stderr)
        return 2

    output = args.output or source.with_name(f"{source.stem}.cleaned.csv")
    log_path = args.log or (None if args.dry_run else output.with_suffix(".changes.json"))

    if output.resolve() == source.resolve():
        print("error: the output file must be different from the input file", file=sys.stderr)
        return 2
    targets = [log_path] if args.dry_run else [output, log_path]
    for target in targets:
        if target is not None and target.exists() and not args.force:
            print(f"error: {target} already exists (use --force to overwrite)", file=sys.stderr)
            return 2

    try:
        result = clean_csv(source, dayfirst=args.dayfirst)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not result.header:
        print("Nothing to clean: no header row found.")
        return 0

    print(format_report(result))
    if not args.dry_run:
        write_csv(result, output)
        print(f"\nCleaned file written to {output}")
    else:
        print("\nDry run: no cleaned file was written.")
    if log_path is not None:
        write_log(result, log_path, source=str(source))
        print(f"Change log written to {log_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "clean":
        return _run_clean(args)
    return 2  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
