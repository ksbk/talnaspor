import pytest

from talnaspor.pxweb import PXMetadata
from talnaspor.query import build_query


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
