from tidytrail import clean_rows, normalize_column_name, parse_date
from tidytrail.core import find_header_index


def kinds(result):
    return [change.kind for change in result.changes]


def test_normalize_column_name():
    assert normalize_column_name("  First Name ") == "first_name"
    assert normalize_column_name("Last  Name") == "last_name"
    assert normalize_column_name("Score (%)") == "score"
    assert normalize_column_name("Café Prix") == "café_prix"
    assert normalize_column_name("###") == ""


def test_find_header_skips_title_and_blank_rows():
    rows = [["Report", "", ""], ["", "", ""], ["a", "b", "c"], ["1", "2", "3"]]
    assert find_header_index(rows) == 2


def test_find_header_returns_none_for_empty_input():
    assert find_header_index([]) is None
    assert find_header_index([["", ""], [" ", ""]]) is None


def test_header_row_change_is_recorded():
    result = clean_rows([["Title", ""], ["A", "B"], ["1", "2"]])
    assert result.header == ["a", "b"]
    assert result.rows == [["1", "2"]]
    assert "header_row" in kinds(result)


def test_duplicate_and_missing_column_names_become_unique():
    result = clean_rows([["Name", "name", "", "Name"], ["a", "b", "c", "d"]])
    assert result.header == ["name", "name_2", "column_3", "name_3"]


def test_whitespace_is_trimmed_and_collapsed():
    result = clean_rows([["a"], ["  hello   world \n"]])
    assert result.rows == [["hello world"]]
    assert kinds(result) == ["whitespace"]


def test_blank_tokens_become_empty_cells():
    result = clean_rows([["a", "b"], ["N/A", "x"], ["-", "null"]])
    assert result.rows == [["", "x"], ["", ""]]
    assert kinds(result).count("blank") == 3


def test_whitespace_only_cell_becomes_empty():
    result = clean_rows([["a", "b"], ["   ", "x"]])
    assert result.rows == [["", "x"]]
    assert kinds(result) == ["whitespace"]


def test_empty_rows_are_removed():
    result = clean_rows([["a", "b"], ["1", "2"], ["", ""], ["3", "4"]])
    assert result.rows == [["1", "2"], ["3", "4"]]
    assert kinds(result) == ["empty_row"]


def test_short_rows_are_padded_and_long_rows_are_not_truncated():
    result = clean_rows([["a", "b"], ["1"], ["2", "3", "extra"]])
    assert result.header == ["a", "b", "column_3"]
    assert result.rows == [["1", "", ""], ["2", "3", "extra"]]


def test_trailing_empty_header_cells_are_ignored():
    result = clean_rows([["a", "b", "", ""], ["1", "2", "", ""]])
    assert result.header == ["a", "b"]


def test_parse_date_formats():
    assert parse_date("2026-09-01") == "2026-09-01"
    assert parse_date("09/01/2026") == "2026-09-01"
    assert parse_date("9/2/2026") == "2026-09-02"
    assert parse_date("September 4, 2026") == "2026-09-04"
    assert parse_date("4 Sep 2026") == "2026-09-04"
    assert parse_date("not a date") is None
    assert parse_date("13/01/2026") is None  # month 13 does not exist


def test_ambiguous_dates_default_to_month_first_and_respect_dayfirst():
    assert parse_date("03/04/2026") == "2026-03-04"
    assert parse_date("03/04/2026", dayfirst=True) == "2026-04-03"


def test_date_column_is_converted_to_iso():
    rows = [["when"], ["09/01/2026"], ["2026-09-02"], ["September 3, 2026"]]
    result = clean_rows(rows)
    assert result.rows == [["2026-09-01"], ["2026-09-02"], ["2026-09-03"]]
    assert kinds(result).count("date") == 2  # the ISO value needed no change


def test_dayfirst_flag_changes_the_result():
    rows = [["when"], ["03/04/2026"], ["05/06/2026"]]
    assert clean_rows(rows).rows == [["2026-03-04"], ["2026-05-06"]]
    assert clean_rows(rows, dayfirst=True).rows == [["2026-04-03"], ["2026-06-05"]]


def test_non_date_columns_are_left_alone():
    rows = [["id", "note"], ["1-2", "hello"], ["3-4", "world"]]
    assert clean_rows(rows).rows == [["1-2", "hello"], ["3-4", "world"]]


def test_unparseable_value_in_date_column_warns_and_is_kept():
    rows = [["when"]] + [["2026-01-01"]] * 9 + [["someday"]]
    result = clean_rows(rows)
    assert result.rows[-1] == ["someday"]
    assert len(result.warnings) == 1
    assert "someday" in result.warnings[0]


def test_clean_data_produces_no_changes():
    result = clean_rows([["a", "b"], ["1", "x"], ["2", "y"]])
    assert result.changes == []
    assert result.summary() == {}


def test_empty_input_returns_empty_result():
    result = clean_rows([])
    assert result.header == [] and result.rows == [] and result.changes == []
