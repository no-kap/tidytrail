"""Core cleaning logic for tidytrail.

The cleaning functions are pure: they take rows (lists of strings) and return a
``CleanResult`` that holds the cleaned rows *and* a record of every change made.
Only the small helpers at the bottom of the file touch the file system.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from ._version import __version__

# Cell values (after trimming, case-insensitive) that are standardized to an empty cell.
BLANK_TOKENS = frozenset({"n/a", "null", "-", "--"})

# How many leading rows are inspected when looking for the header row, and how full
# (as a share of the widest row) a row must be, strictly, to count as the header.
HEADER_SCAN_ROWS = 10
HEADER_FILL_RATIO = 0.5

# A column is treated as a date column when at least this share of its
# non-empty values can be parsed as dates (and there are at least two values).
DATE_COLUMN_THRESHOLD = 0.8

_MONTH_NAME_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y")
_MONTH_FIRST_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y") + _MONTH_NAME_FORMATS
_DAY_FIRST_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y") + _MONTH_NAME_FORMATS

_WHITESPACE = re.compile(r"\s+")


@dataclass
class Change:
    """One recorded change. ``row`` is the 1-based record number in the original file."""

    kind: str
    row: int | None
    column: str | None
    before: str | None
    after: str | None


@dataclass
class CleanResult:
    header: list[str]
    rows: list[list[str]]
    changes: list[Change] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        """Number of changes per kind, e.g. ``{"whitespace": 3, "date": 2}``."""
        return dict(sorted(Counter(change.kind for change in self.changes).items()))


def normalize_column_name(name: str) -> str:
    """Lower-case a column name and join its words with single underscores."""
    return re.sub(r"[\W_]+", "_", name.strip().lower()).strip("_")


def parse_date(value: str, *, dayfirst: bool = False) -> str | None:
    """Return ``value`` as an ISO date (YYYY-MM-DD), or ``None`` if it isn't a known format.

    Slash and dash dates such as 01/02/2026 are ambiguous, so they are read
    month-first unless ``dayfirst`` is true.
    """
    formats = _DAY_FIRST_FORMATS if dayfirst else _MONTH_FIRST_FORMATS
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def find_header_index(rows: list[list[str]]) -> int | None:
    """Index of the first row that looks like the header, or ``None`` if there isn't one.

    Title lines and blank rows above the table have few filled-in cells, so the
    header is the first row that is more than half as full as the widest row.
    """
    counts = [sum(1 for cell in row if cell.strip()) for row in rows[:HEADER_SCAN_ROWS]]
    if not counts or max(counts) == 0:
        return None
    cutoff = HEADER_FILL_RATIO * max(counts)
    for index, count in enumerate(counts):
        if count > cutoff:
            return index
    return None


def _last_filled(row: list[str]) -> int:
    """1-based position of the last non-empty cell in ``row`` (0 if the row is empty)."""
    for position in range(len(row), 0, -1):
        if row[position - 1].strip():
            return position
    return 0


def clean_rows(rows: list[list[str]], *, dayfirst: bool = False) -> CleanResult:
    """Clean parsed spreadsheet rows and record every change."""
    header_index = find_header_index(rows)
    if header_index is None:
        return CleanResult(header=[], rows=[])

    changes: list[Change] = []
    warnings: list[str] = []

    if header_index > 0:
        note = f"{header_index} row(s) above header"
        changes.append(Change("header_row", header_index + 1, None, note, "removed"))

    raw_header = rows[header_index]
    body = rows[header_index + 1 :]
    width = max([_last_filled(raw_header)] + [_last_filled(row) for row in body])

    # Column names: normalize, fill in missing names, and keep names unique.
    header: list[str] = []
    used: set[str] = set()
    for position in range(width):
        raw = raw_header[position] if position < len(raw_header) else ""
        base = normalize_column_name(raw) or f"column_{position + 1}"
        name, attempt = base, 1
        while name in used:
            attempt += 1
            name = f"{base}_{attempt}"
        used.add(name)
        header.append(name)
        if name != raw:
            changes.append(Change("column_name", header_index + 1, name, raw, name))

    # Cells: trim whitespace, standardize blanks, and drop fully empty rows.
    cleaned: list[list[str]] = []
    row_numbers: list[int] = []
    for record_number, raw_row in enumerate(body, start=header_index + 2):
        if not any(cell.strip() for cell in raw_row):
            changes.append(Change("empty_row", record_number, None, None, "removed"))
            continue
        row: list[str] = []
        for position, name in enumerate(header):
            raw = raw_row[position] if position < len(raw_row) else ""
            trimmed = _WHITESPACE.sub(" ", raw).strip()
            if trimmed.lower() in BLANK_TOKENS:
                row.append("")
                changes.append(Change("blank", record_number, name, raw, ""))
            else:
                row.append(trimmed)
                if trimmed != raw:
                    changes.append(Change("whitespace", record_number, name, raw, trimmed))
        cleaned.append(row)
        row_numbers.append(record_number)

    # Dates: convert a column to ISO dates only when most of its values parse as dates.
    for position, name in enumerate(header):
        filled = [(index, row[position]) for index, row in enumerate(cleaned) if row[position]]
        parsed = [(index, value, parse_date(value, dayfirst=dayfirst)) for index, value in filled]
        hits = sum(1 for _, _, iso in parsed if iso is not None)
        if len(filled) < 2 or hits / len(filled) < DATE_COLUMN_THRESHOLD:
            continue
        for index, value, iso in parsed:
            record_number = row_numbers[index]
            if iso is None:
                warnings.append(
                    f"Row {record_number}, column '{name}': could not read {value!r} "
                    "as a date; left unchanged."
                )
            elif iso != value:
                cleaned[index][position] = iso
                changes.append(Change("date", record_number, name, value, iso))

    return CleanResult(header=header, rows=cleaned, changes=changes, warnings=warnings)


# --- File helpers -----------------------------------------------------------


def read_csv_rows(path: str | Path) -> list[list[str]]:
    """Read a UTF-8 CSV file into a list of rows."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            return [list(row) for row in csv.reader(handle)]
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"{path} is not valid UTF-8. Re-save it as 'CSV UTF-8' and try again "
            "(automatic encoding detection is on the roadmap)."
        ) from exc


def clean_csv(path: str | Path, *, dayfirst: bool = False) -> CleanResult:
    """Read a CSV file and clean it. Nothing is written to disk."""
    return clean_rows(read_csv_rows(path), dayfirst=dayfirst)


def write_csv(result: CleanResult, path: str | Path) -> None:
    """Write the cleaned table to ``path`` as UTF-8 CSV."""
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(result.header)
        writer.writerows(result.rows)


def write_log(result: CleanResult, path: str | Path, *, source: str | None = None) -> None:
    """Write the full change log to ``path`` as JSON."""
    payload = {
        "tool": "tidytrail",
        "version": __version__,
        "source": source,
        "summary": result.summary(),
        "warnings": result.warnings,
        "changes": [asdict(change) for change in result.changes],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def format_report(result: CleanResult, *, limit: int = 50) -> str:
    """Human-readable summary of what changed (the first ``limit`` changes in detail)."""
    if not result.changes and not result.warnings:
        return "No changes needed."
    lines = [f"{len(result.changes)} change(s):"]
    lines += [f"  {kind}: {count}" for kind, count in result.summary().items()]
    lines.append("")
    for change in result.changes[:limit]:
        where = f"row {change.row}" if change.row else "file"
        if change.column:
            where += f", {change.column}"
        lines.append(f"- [{change.kind}] {where}: {change.before!r} -> {change.after!r}")
    if len(result.changes) > limit:
        lines.append(f"... and {len(result.changes) - limit} more (see the JSON log).")
    for warning in result.warnings:
        lines.append(f"WARNING: {warning}")
    return "\n".join(lines)
