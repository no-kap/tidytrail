# tidytrail

[![CI](https://github.com/no-kap/tidytrail/actions/workflows/ci.yml/badge.svg)](https://github.com/no-kap/tidytrail/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Python library and command-line tool that cleans messy CSV exports and writes an
**auditable log of every change**, with a **dry-run mode** so you can review changes
before anything is written.

> **Status: early development (v0.0.1).** CSV files only for now. The package is not on
> PyPI yet. See the [roadmap](#roadmap) for what's planned.

## Why tidytrail?

Exports from school, agency, and business systems are rarely clean: title lines above the
table, inconsistent column names, stray spaces, `N/A` placeholders, and dates in three
different formats. Cleaning them by hand is slow, and silent cleanup scripts make it hard
to trust the result. tidytrail's goal is simple: **never change anything without recording
it**, so you can always see what happened and why.

## Install

From source (Python 3.10+):

```bash
git clone https://github.com/no-kap/tidytrail.git
cd tidytrail
python -m pip install -e .
```

## Quick start

```bash
# See what would change. Nothing is written.
tidytrail clean examples/messy_roster.csv --dry-run

# Clean it. Writes my_output.csv and my_output.changes.json
tidytrail clean examples/messy_roster.csv -o my_output.csv
```

Your input file is **never modified**. The cleaned CSV and the change log are new files.
(The repository's `examples/` folder already contains the expected output and log for
reference.)

### Before and after

`examples/messy_roster.csv` (synthetic data):

```text
Fall 2026 Roster Export,,,,
,,,,
 Student ID ,First Name,Last  Name,Enrollment Date,Grade Level
1001,  Ava ,Nguyen,09/01/2026,2
1002,Liam,"O'Brien ",9/2/2026,2
1003,Sofia,N/A,2026-09-03,2
,,,,
1004,Noah,Patel,"September 4, 2026",2
```

becomes:

```text
student_id,first_name,last_name,enrollment_date,grade_level
1001,Ava,Nguyen,2026-09-01,2
1002,Liam,O'Brien,2026-09-02,2
1003,Sofia,,2026-09-03,2
1004,Noah,Patel,2026-09-04,2
```

and every one of the 14 changes is listed in the log:

```text
- [header_row] row 3: '2 row(s) above header' -> 'removed'
- [column_name] row 3, student_id: ' Student ID ' -> 'student_id'
- [whitespace] row 4, first_name: '  Ava ' -> 'Ava'
- [blank] row 6, last_name: 'N/A' -> ''
- [date] row 4, enrollment_date: '09/01/2026' -> '2026-09-01'
...
```

## What it cleans

| Change kind    | What happens |
|----------------|--------------|
| `header_row`   | Title lines and blank rows above the real header are removed. |
| `column_name`  | Names become lower-case with underscores; missing or duplicate names are made unique. |
| `whitespace`   | Leading, trailing, and repeated spaces in cells are trimmed. |
| `blank`        | `N/A`, `null`, `-`, and `--` become empty cells. |
| `empty_row`    | Completely empty rows are removed. |
| `date`         | Columns where most values are dates are converted to `YYYY-MM-DD`. |

Dates like `03/04/2026` are ambiguous. They are read month-first by default; pass
`--dayfirst` for day/month data. Values in a date column that can't be read are left
unchanged and reported as warnings.

## Command-line options

```text
tidytrail clean INPUT [-o OUTPUT] [--log LOG] [--dry-run] [--dayfirst] [--force]
```

| Option | Meaning |
|--------|---------|
| `-o, --output` | Where to write the cleaned CSV (default: `INPUT.cleaned.csv`). |
| `--log` | Where to write the JSON change log (default: next to the output). |
| `--dry-run` | Show what would change and write no cleaned file. |
| `--dayfirst` | Read ambiguous dates as day/month. |
| `--force` | Overwrite existing output files (otherwise tidytrail refuses). |

## Use it as a library

```python
from tidytrail import clean_csv, format_report, write_csv, write_log

result = clean_csv("examples/messy_roster.csv")
print(format_report(result))          # human-readable summary
write_csv(result, "cleaned.csv")      # cleaned table
write_log(result, "changes.json")     # full audit log
```

## Limitations (v0.0.1)

- CSV only, UTF-8 only. Other encodings produce a clear error rather than guessing.
- Header detection assumes the header row is at least half as full as the widest row.
- Only the date formats listed in `src/tidytrail/core.py` are recognized.

## Roadmap

- [ ] Excel (`.xlsx`) support
- [ ] Encoding and delimiter detection
- [ ] Merged-cell handling
- [ ] Duplicate-row detection (reported, never silently removed)
- [ ] Declarative cleaning rules in a YAML file
- [ ] First release on PyPI

Ideas and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
