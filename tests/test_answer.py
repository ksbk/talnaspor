import json
from pathlib import Path
from unittest.mock import patch

import pytest

from talnaspor.answer import LATEST, answer, format_period, format_value
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
