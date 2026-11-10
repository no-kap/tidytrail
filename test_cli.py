import csv
import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from tidytrail import __version__
from tidytrail.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
MESSY = EXAMPLES / "messy_roster.csv"
EXPECTED = EXAMPLES / "messy_roster.cleaned.csv"


def run(*args):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main([str(arg) for arg in args])
    return code, out.getvalue(), err.getvalue()


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def test_clean_matches_the_expected_example(tmp_path):
    output = tmp_path / "out.csv"
    code, stdout, _ = run("clean", MESSY, "-o", output)
    assert code == 0
    assert read_csv(output) == read_csv(EXPECTED)
    assert "14 change(s)" in stdout


def test_clean_writes_a_json_log(tmp_path):
    output = tmp_path / "out.csv"
    run("clean", MESSY, "-o", output)
    log = json.loads((tmp_path / "out.changes.json").read_text(encoding="utf-8"))
    assert log["tool"] == "tidytrail"
    assert log["version"] == __version__
    assert log["summary"]["date"] == 3
    assert len(log["changes"]) == 14


def test_dry_run_writes_nothing(tmp_path):
    output = tmp_path / "out.csv"
    code, stdout, _ = run("clean", MESSY, "-o", output, "--dry-run")
    assert code == 0
    assert "Dry run" in stdout
    assert list(tmp_path.iterdir()) == []


def test_dry_run_can_still_write_a_requested_log(tmp_path):
    log = tmp_path / "log.json"
    code, _, _ = run("clean", MESSY, "--dry-run", "--log", log)
    assert code == 0
    assert log.exists()


def test_input_file_is_never_modified(tmp_path):
    source = tmp_path / "data.csv"
    source.write_text(MESSY.read_text(encoding="utf-8"), encoding="utf-8")
    before = source.read_bytes()
    run("clean", source)
    assert source.read_bytes() == before
    assert (tmp_path / "data.cleaned.csv").exists()


def test_refuses_to_overwrite_existing_output_without_force(tmp_path):
    output = tmp_path / "out.csv"
    output.write_text("keep me", encoding="utf-8")
    code, _, stderr = run("clean", MESSY, "-o", output)
    assert code == 2
    assert "already exists" in stderr
    assert output.read_text(encoding="utf-8") == "keep me"
    code, _, _ = run("clean", MESSY, "-o", output, "--force")
    assert code == 0


def test_output_cannot_be_the_input(tmp_path):
    source = tmp_path / "data.csv"
    source.write_text("a,b\n1,2\n", encoding="utf-8")
    code, _, stderr = run("clean", source, "-o", source, "--force")
    assert code == 2
    assert "different from the input" in stderr


def test_missing_input_file_is_an_error(tmp_path):
    code, _, stderr = run("clean", tmp_path / "nope.csv")
    assert code == 2
    assert "not a file" in stderr


def test_non_utf8_file_gives_a_clear_error(tmp_path):
    source = tmp_path / "latin.csv"
    source.write_bytes("name\ncaf\xe9\n".encode("latin-1"))
    code, _, stderr = run("clean", source)
    assert code == 2
    assert "UTF-8" in stderr


def test_empty_file_is_handled(tmp_path):
    source = tmp_path / "empty.csv"
    source.write_text("", encoding="utf-8")
    code, stdout, _ = run("clean", source)
    assert code == 0
    assert "Nothing to clean" in stdout
    assert not (tmp_path / "empty.cleaned.csv").exists()


def test_dayfirst_flag(tmp_path):
    source = tmp_path / "dates.csv"
    source.write_text("when\n03/04/2026\n05/06/2026\n", encoding="utf-8")
    output = tmp_path / "out.csv"
    run("clean", source, "-o", output, "--dayfirst")
    assert read_csv(output) == [["when"], ["2026-04-03"], ["2026-06-05"]]
