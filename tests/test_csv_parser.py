
import pytest

from app.services.csv_parser import CSVParser
from app.core.constants import CSV_REQUIRED_COLUMNS, CSV_OPTIONAL_COLUMNS


def make_csv(headers=None, rows=None):
    headers = list(headers or CSV_REQUIRED_COLUMNS)
    rows = rows if rows is not None else [["80", "98"]]

    lines = [",".join(headers)]
    lines.extend(",".join(map(str, row)) for row in rows)
    return "\n".join(lines).encode("utf-8")


def test_csv_parser_initialization():
    parser = CSVParser()

    assert parser.max_rows == 100000
    assert parser.max_size_bytes == 10 * 1024 * 1024


def test_parse_valid_csv():
    result = CSVParser().parse(make_csv())

    assert result["row_count"] == 1
    assert result["data"][0]["pulse_bpm"] == 80.0
    assert result["data"][0]["spo2_percent"] == 98.0
    assert result["errors"] == []


def test_parse_multiple_valid_rows():
    content = make_csv(rows=[
        ["80", "98"],
        ["100", "95"],
        ["120", "97"],
    ])

    result = CSVParser().parse(content)

    assert result["row_count"] == 3
    assert [row["pulse_bpm"] for row in result["data"]] == [
        80.0, 100.0, 120.0
    ]


def test_parse_missing_required_column():
    headers = list(CSV_REQUIRED_COLUMNS)[:-1]

    with pytest.raises(ValueError, match="Missing required columns"):
        CSVParser().parse(make_csv(headers=headers, rows=[]))


def test_parse_empty_csv():
    with pytest.raises(ValueError, match="empty or has no headers"):
        CSVParser().parse(b"")


def test_parse_header_only_csv():
    content = ",".join(CSV_REQUIRED_COLUMNS).encode("utf-8")

    with pytest.raises(ValueError, match="No valid data rows found"):
        CSVParser().parse(content)


@pytest.mark.parametrize("pulse", ["abc", ""])
def test_parse_non_numeric_pulse(pulse):
    with pytest.raises(ValueError, match="No valid data rows found"):
        CSVParser().parse(make_csv(rows=[[pulse, "98"]]))


@pytest.mark.parametrize("pulse", ["29", "251"])
def test_parse_out_of_range_pulse(pulse):
    result = CSVParser().parse(make_csv(rows=[[pulse, "98"]]))

    # Current parser retains numeric values outside the allowed range.
    assert result["row_count"] == 1
    assert result["data"][0]["pulse_bpm"] == float(pulse)


@pytest.mark.parametrize("spo2", ["abc", ""])
def test_parse_non_numeric_spo2(spo2):
    with pytest.raises(ValueError, match="No valid data rows found"):
        CSVParser().parse(make_csv(rows=[["80", spo2]]))


@pytest.mark.parametrize("spo2", ["-1", "101"])
def test_parse_out_of_range_spo2(spo2):
    result = CSVParser().parse(make_csv(rows=[["80", spo2]]))

    # Current parser retains numeric values outside the allowed range.
    assert result["row_count"] == 1
    assert result["data"][0]["spo2_percent"] == float(spo2)


def test_parse_pulse_boundary_values():
    content = make_csv(rows=[
        ["30", "98"],
        ["250", "98"],
    ])

    result = CSVParser().parse(content)

    assert result["row_count"] == 2
    assert result["errors"] == []


def test_parse_spo2_boundary_values():
    content = make_csv(rows=[
        ["80", "0"],
        ["80", "100"],
    ])

    result = CSVParser().parse(content)

    assert result["row_count"] == 2
    assert result["errors"] == []


def test_parse_file_size_limit():
    parser = CSVParser(max_size_mb=1)

    with pytest.raises(ValueError, match="File size exceeds"):
        parser.parse(b"x" * (1024 * 1024 + 1))


def test_parse_latin1_encoding():
    content = (
        ",".join(CSV_REQUIRED_COLUMNS) + "\n80,98\n"
    ).encode("latin-1")

    result = CSVParser().parse(content)

    assert result["row_count"] == 1
    assert result["data"][0]["pulse_bpm"] == 80.0


def test_parse_optional_columns():
    headers = list(CSV_REQUIRED_COLUMNS) + list(CSV_OPTIONAL_COLUMNS)

    values = {
        "pulse_bpm": "80",
        "spo2_percent": "98",
        "timestamp": "1234",
        "motion": "0.5",
        "contact": "0.8",
        "ppg_amplitude": "1.2",
        "ppg_value": "2.5",
    }

    content = make_csv(
        headers=headers,
        rows=[[values.get(header, "") for header in headers]],
    )

    result = CSVParser().parse(content)
    row = result["data"][0]

    assert row["pulse_bpm"] == 80.0
    assert row["spo2_percent"] == 98.0

    for field in (
        "timestamp",
        "motion",
        "contact",
        "ppg_amplitude",
        "ppg_value",
    ):
        if field in CSV_OPTIONAL_COLUMNS:
            assert field in row


def test_parse_optional_motion_and_contact_are_clamped():
    headers = list(CSV_REQUIRED_COLUMNS) + ["motion", "contact"]

    content = make_csv(
        headers=headers,
        rows=[["80", "98", "2", "-1"]],
    )

    row = CSVParser().parse(content)["data"][0]

    assert row["motion"] == 1.0
    assert row["contact"] == 0.0


def test_parse_max_rows_limit():
    content = make_csv(rows=[
        ["80", "98"],
        ["90", "97"],
        ["100", "96"],
    ])

    result = CSVParser(max_rows=2).parse(content)

    assert result["row_count"] == 2


def test_result_contains_metadata():
    result = CSVParser().parse(make_csv())

    expected_keys = (
        "data",
        "row_count",
        "columns",
        "required_columns",
        "optional_columns_present",
        "optional_columns_missing",
        "errors",
    )

    for key in expected_keys:
        assert key in result
