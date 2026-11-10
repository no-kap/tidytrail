# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `tidytrail clean` command for CSV files with a `--dry-run` mode.
- Header-row detection, column-name normalization, whitespace and blank cleanup,
  empty-row removal, and ISO date conversion (`--dayfirst` for day/month data).
- JSON change log recording every change (kind, row, column, before, after).
- Synthetic example in `examples/`, tests, and CI.
