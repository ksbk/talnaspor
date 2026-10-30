import pytest

from talnaspor.pxweb import PXMetadata
from talnaspor.query import build_query
from talnaspor.validation import UnavailableValue


@pytest.fixture
def metadata() -> PXMetadata:
    return PXMetadata.model_validate(
        {
            "title": "Consumer Price Index",
            "variables": [
                {
                    "code": "Month",
                    "text": "Month",
                    "values": ["2026M08", "2026M09"],
                },
                {
                    "code": "Index",
                    "text": "Index",
                    "values": ["CPI", "CPILH"],
                },
                {
                    "code": "Item",
                    "text": "Item",
                    "values": ["index", "change_A"],
                },
            ],
        }
    )


def test_builds_valid_cpi_query(metadata: PXMetadata) -> None:
    result = build_query(
        metadata,
        {
            "Month": "2026M09",
            "Index": "CPI",
            "Item": "change_A",
        },
    )

    assert result["response"] == {"format": "json-stat2"}
    assert result["query"] == [
        {
            "code": "Month",
            "selection": {"filter": "item", "values": ["2026M09"]},
        },
        {
            "code": "Index",
            "selection": {"filter": "item", "values": ["CPI"]},
        },
        {
            "code": "Item",
            "selection": {"filter": "item", "values": ["change_A"]},
        },
    ]


def test_orders_dimensions_by_metadata(metadata: PXMetadata) -> None:
    result = build_query(
        metadata,
        {
            "Item": "change_A",
            "Month": "2026M09",
            "Index": "CPI",
        },
    )

    assert isinstance(result["query"], list)
    assert [entry["code"] for entry in result["query"]] == ["Month", "Index", "Item"]


def test_rejects_missing_dimension(metadata: PXMetadata) -> None:
    with pytest.raises(ValueError, match="every table dimension"):
        build_query(
            metadata,
            {
                "Month": "2026M09",
                "Index": "CPI",
            },
        )


def test_rejects_unexpected_dimension(metadata: PXMetadata) -> None:
    with pytest.raises(ValueError, match="every table dimension"):
        build_query(
            metadata,
            {
                "Month": "2026M09",
                "Index": "CPI",
                "Item": "change_A",
                "Region": "Reykjavik",
            },
        )


def test_rejects_invalid_month(metadata: PXMetadata) -> None:
    with pytest.raises(ValueError, match="Unsupported value"):
        build_query(
            metadata,
            {
                "Month": "2027M01",
                "Index": "CPI",
                "Item": "change_A",
            },
        )


def test_builds_query_with_several_periods(metadata: PXMetadata) -> None:
    result = build_query(
        metadata,
        {"Month": ["2026M08", "2026M09"], "Index": "CPI", "Item": "index"},
    )

    assert isinstance(result["query"], list)
    assert result["query"][0] == {
        "code": "Month",
        "selection": {"filter": "item", "values": ["2026M08", "2026M09"]},
    }


@pytest.mark.parametrize("months", [[], ["2026M09", "2026M09"]])
def test_rejects_empty_or_repeated_values(metadata: PXMetadata, months: list[str]) -> None:
    with pytest.raises(ValueError, match="distinct values"):
        build_query(metadata, {"Month": months, "Index": "CPI", "Item": "index"})


def test_rejects_any_invalid_value_in_a_list(metadata: PXMetadata) -> None:
    with pytest.raises(ValueError, match="Unsupported value"):
        build_query(metadata, {"Month": ["2026M09", "2027M01"], "Index": "CPI", "Item": "index"})


def test_reports_the_range_a_table_covers(metadata: PXMetadata) -> None:
    with pytest.raises(UnavailableValue) as raised:
        build_query(metadata, {"Month": "2030M01", "Index": "CPI", "Item": "index"})

    assert (raised.value.requested, raised.value.dimension) == ("2030M01", "Month")
    assert (raised.value.first, raised.value.last) == ("2026M08", "2026M09")
