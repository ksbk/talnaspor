import json
from pathlib import Path
from unittest.mock import patch

import pytest

from talnaspor.answer import (
    LATEST,
    answer,
    before_latest,
    compare,
    format_period,
    format_value,
    shift_period,
)
from talnaspor.pxweb import PXMetadata
from talnaspor.tables import TABLES

FIXTURES = Path(__file__).parent / "fixtures" / "is"


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def metadata(key: str) -> PXMetadata:
    return PXMetadata.model_validate_json(read(f"{key}_metadata.json"))


def submitted_values(query: object) -> dict[str, list[str]]:
    assert isinstance(query, dict)
    return {entry["code"]: entry["selection"]["values"] for entry in query["query"]}


def test_answers_cpi_annual_change() -> None:
    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata("cpi")),
        patch("talnaspor.answer.get_data", return_value=read("cpi_2026m09.json")) as get_data,
    ):
        result = answer("cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"})

    assert result.text == (
        "Vísitala neysluverðs, ársbreyting í september 2026: 5,9%. "
        "Heimild: Hagstofa Íslands, Vísitala neysluverðs og breytingar, grunnur 1988=100."
    )
    assert result.value == 5.9
    assert result.value_text == "5,9%"
    assert result.unit == "%"
    assert result.period == "2026M09"
    assert result.labels["Liður"] == "Ársbreyting, %"
    assert result.page_url == TABLES["cpi"].page_url
    assert submitted_values(get_data.call_args.args[1]) == {
        "Mánuður": ["2026M09"],
        "Vísitala": ["CPI"],
        "Liður": ["change_A"],
    }


def test_answers_latest_population() -> None:
    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata("population")),
        patch("talnaspor.answer.get_data", return_value=read("population_2026.json")) as get_data,
    ):
        result = answer("population", {"Ár": LATEST, "Eining": "0"})

    assert submitted_values(get_data.call_args.args[1])["Ár"] == ["2026"]
    assert result.text == (
        "Mannfjöldi 1. janúar 2026: 394.324 íbúar. "
        "Heimild: Hagstofa Íslands, Hagskinna, Lykiltölur mannfjöldans 1703-2026."
    )
    assert result.value == 394324
    assert result.source == "Hagstofa Íslands, Hagskinna"


def test_rejects_response_for_a_different_period() -> None:
    # The latest CPI month in the metadata is 2026M10; the fixture answers 2026M09.
    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata("cpi")),
        patch("talnaspor.answer.get_data", return_value=read("cpi_2026m09.json")),
        pytest.raises(ValueError, match="do not match requested"),
    ):
        answer("cpi", {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"})


def test_rejects_unavailable_value_with_status() -> None:
    data = json.loads(read("population_2026.json"))
    data["value"] = [None]
    data["status"] = {"0": ".."}

    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata("population")),
        patch("talnaspor.answer.get_data", return_value=json.dumps(data)),
        pytest.raises(ValueError, match=r"status '\.\.'"),
    ):
        answer("population", {"Ár": "2026", "Eining": "0"})


def test_rejects_unsupported_measure_before_retrieval() -> None:
    with (
        patch("talnaspor.answer.get_metadata") as get_metadata,
        pytest.raises(ValueError, match="Unsupported measure"),
    ):
        answer("cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "A_rate_6M"})

    get_metadata.assert_not_called()


def test_table_measures_exist_in_metadata() -> None:
    for key, table in TABLES.items():
        variables = {variable.code: variable for variable in metadata(key).variables}
        assert table.time_code in variables
        assert set(table.measures) <= set(variables[table.measure_code].values)


@pytest.mark.parametrize(
    ("value", "decimals", "unit", "expected"),
    [
        (5.9, 1, "%", "5,9%"),
        (6, 1, "%", "6,0%"),
        (1.49, 0, "%", "1,49%"),
        (394324, 0, "íbúar", "394.324 íbúar"),
        (-30, 0, "manns", "-30 manns"),
        (650.2, 1, "stig", "650,2 stig"),
        (1234.5, None, "stig", "1.234,5 stig"),
    ],
)
def test_formats_values_in_icelandic(
    value: float, decimals: int | None, unit: str, expected: str
) -> None:
    assert format_value(value, decimals, unit) == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [("2026M09", "september 2026"), ("2026M01", "janúar 2026"), ("2026", "2026")],
)
def test_formats_periods_in_icelandic(code: str, expected: str) -> None:
    assert format_period(code) == expected


def test_compares_population_over_default_span() -> None:
    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata("population")),
        patch(
            "talnaspor.answer.get_data", return_value=read("population_2016_2026.json")
        ) as get_data,
    ):
        result = compare("population", {"Ár": LATEST, "Eining": "0"}, before_latest(10))

    assert submitted_values(get_data.call_args.args[1])["Ár"] == ["2016", "2026"]
    assert result.text == (
        "Mannfjöldi 1. janúar 2016: 326.036 íbúar. "
        "Mannfjöldi 1. janúar 2026: 394.324 íbúar. "
        "Breyting: +68.288 íbúar (+20,9%). "
        "Heimild: Hagstofa Íslands, Hagskinna, Lykiltölur mannfjöldans 1703-2026."
    )
    assert (result.start.value, result.end.value, result.difference) == (326036, 394324, 68288)
    assert isinstance(result.difference, int)
    assert result.selections == {"Ár": ["2016", "2026"], "Eining": ["0"]}
    assert result.labels == {"Eining": "Mannfjöldi 1. janúar"}


def test_compares_percentages_in_percentage_points() -> None:
    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata("cpi")),
        patch("talnaspor.answer.get_data", return_value=read("cpi_2025m09_2026m09.json")),
    ):
        result = compare(
            "cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"}, "2025M09"
        )

    assert result.text == (
        "Vísitala neysluverðs, ársbreyting í september 2025: 4,1%. "
        "Vísitala neysluverðs, ársbreyting í september 2026: 5,9%. "
        "Breyting: +1,8 prósentustig. "
        "Heimild: Hagstofa Íslands, Vísitala neysluverðs og breytingar, grunnur 1988=100."
    )
    assert result.difference == 1.8
    assert result.relative_change_text is None


def test_reports_a_decrease_with_a_minus_sign() -> None:
    data = json.loads(read("population_2016_2026.json"))
    data["value"] = [394324, 326036]

    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata("population")),
        patch("talnaspor.answer.get_data", return_value=json.dumps(data)),
    ):
        result = compare("population", {"Ár": "2026", "Eining": "0"}, "2016")

    assert result.difference_text == "-68.288 íbúar"
    assert result.relative_change_text == "-17,3%"


def test_rejects_comparing_a_period_with_itself() -> None:
    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata("population")),
        patch("talnaspor.answer.get_data") as get_data,
        pytest.raises(ValueError, match="distinct values"),
    ):
        compare("population", {"Ár": LATEST, "Eining": "0"}, "2026")

    get_data.assert_not_called()


@pytest.mark.parametrize(
    ("code", "steps", "expected"),
    [
        ("2026", -10, "2016"),
        ("2026M10", -12, "2025M10"),
        ("2026M01", -1, "2025M12"),
        ("2026M12", 1, "2027M01"),
    ],
)
def test_shifts_periods(code: str, steps: int, expected: str) -> None:
    assert shift_period(code, steps) == expected


def test_rejects_shifting_unknown_period_format() -> None:
    with pytest.raises(ValueError, match="Cannot shift"):
        shift_period("2026Q3", -1)


def test_answers_in_english_with_official_labels() -> None:
    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata("cpi")),
        patch("talnaspor.answer.get_data", return_value=read("cpi_2026m09.json")),
    ):
        result = answer("cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"}, "en")

    assert result.text == (
        "Consumer price index, annual change in September 2026: 5.9%. "
        "Source: Statistics Iceland, Consumer price index and changes, base 1988=100."
    )
    assert result.labels["Vísitala"] == "Consumer price index"
    assert result.page_url == TABLES["cpi"].page_url_en


def test_compares_in_english() -> None:
    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata("population")),
        patch("talnaspor.answer.get_data", return_value=read("population_2016_2026.json")),
    ):
        result = compare("population", {"Ár": LATEST, "Eining": "0"}, before_latest(10), "en")

    assert result.text == (
        "Population 1 January 2016: 326,036 people. "
        "Population 1 January 2026: 394,324 people. "
        "Change: +68,288 people (+20.9%). "
        "Source: Statistics Iceland, Population - key figures 1703-2026."
    )
    assert result.labels == {"Eining": "Population 1 January"}


def test_compares_percentages_in_percentage_points_in_english() -> None:
    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata("cpi")),
        patch("talnaspor.answer.get_data", return_value=read("cpi_2025m09_2026m09.json")),
    ):
        result = compare(
            "cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"}, "2025M09", "en"
        )

    assert result.difference_text == "+1.8 percentage points"


@pytest.mark.parametrize(
    ("value", "decimals", "unit", "expected"),
    [(5.9, 1, "%", "5.9%"), (394324, 0, "people", "394,324 people"), (1234.5, 1, "", "1,234.5")],
)
def test_formats_values_in_english(value: float, decimals: int, unit: str, expected: str) -> None:
    assert format_value(value, decimals, unit, "en") == expected


@pytest.mark.parametrize(
    ("code", "expected"), [("2026M09", "September 2026"), ("2026Á2", "Q2 2026"), ("2026", "2026")]
)
def test_formats_periods_in_english(code: str, expected: str) -> None:
    assert format_period(code, "en") == expected


def test_every_measure_has_english_wording() -> None:
    for table in TABLES.values():
        assert table.title_en and table.page_url_en.startswith("https://px.hagstofa.is/pxen/")
        for code, measure in table.measures.items():
            assert measure.template_en and measure.unit_en
            assert code in table.labels_en.get(table.measure_code, {})
