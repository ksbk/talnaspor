import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from talnaspor.jsonstat import decode_jsonstat

FIXTURE = Path(__file__).parent / "fixtures" / "cpi_2026m09.json"

CPI_QUERY: dict[str, object] = {
    "query": [
        {"code": "Month", "selection": {"filter": "item", "values": ["2026M09"]}},
        {"code": "Index", "selection": {"filter": "item", "values": ["CPI"]}},
        {"code": "Item", "selection": {"filter": "item", "values": ["change_A"]}},
    ],
    "response": {"format": "json-stat2"},
}


def load_fixture() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def test_decodes_real_cpi_response() -> None:
    result = decode_jsonstat(FIXTURE.read_text(encoding="utf-8"), CPI_QUERY)

    assert result.label == "Consumer price index by Month, Index and Item"
    assert result.decimals == 1
    assert result.dimension_labels == {"Month": "Month", "Index": "Index", "Item": "Item"}
    assert len(result.observations) == 1

    observation = result.observations[0]
    assert observation.value == 5.9
    assert observation.codes == {"Month": "2026M09", "Index": "CPI", "Item": "change_A"}
    assert observation.labels == {
        "Month": "2026M09",
        "Index": "Consumer price index",
        "Item": "Annual change, %",
    }
    assert observation.status is None


def test_maps_values_by_category_position_not_request_order() -> None:
    data = {
        "class": "dataset",
        "label": "Population",
        "id": ["Year", "Unit"],
        "size": [2, 1],
        "dimension": {
            "Year": {
                "label": "Year",
                "category": {
                    "index": {"2025": 0, "2026": 1},
                    "label": {"2025": "2025", "2026": "2026"},
                },
            },
            "Unit": {
                "label": "Unit",
                "category": {"index": {"0": 0}, "label": {"0": "Population 1 January"}},
            },
        },
        "value": [383726, 389444],
        "status": {"1": "p"},
    }
    query: dict[str, object] = {
        "query": [
            {"code": "Year", "selection": {"filter": "item", "values": ["2026", "2025"]}},
            {"code": "Unit", "selection": {"filter": "item", "values": ["0"]}},
        ]
    }

    result = decode_jsonstat(json.dumps(data), query)

    assert [(o.codes["Year"], o.value, o.status) for o in result.observations] == [
        ("2025", 383726, None),
        ("2026", 389444, "p"),
    ]
    assert isinstance(result.observations[0].value, int)
    assert result.decimals is None


def set_class(data: dict[str, Any]) -> None:
    data["class"] = "collection"


def reorder_ids(data: dict[str, Any]) -> None:
    data["id"] = ["Index", "Month", "Item"]


def substitute_category(data: dict[str, Any]) -> None:
    month = data["dimension"]["Month"]["category"]
    month["index"] = {"2026M08": 0}
    month["label"] = {"2026M08": "2026M08"}


def add_extra_value(data: dict[str, Any]) -> None:
    data["value"] = [5.9, 6.1]


def wrong_size(data: dict[str, Any]) -> None:
    data["size"] = [2, 1, 1]


def null_value(data: dict[str, Any]) -> None:
    data["value"] = [None]


def boolean_value(data: dict[str, Any]) -> None:
    data["value"] = [True]


def string_value(data: dict[str, Any]) -> None:
    data["value"] = ["5.9"]


def missing_label(data: dict[str, Any]) -> None:
    data["dimension"]["Item"]["category"]["label"] = {}


def missing_dimension(data: dict[str, Any]) -> None:
    del data["dimension"]["Index"]


@pytest.mark.parametrize(
    "corrupt",
    [
        set_class,
        reorder_ids,
        substitute_category,
        add_extra_value,
        wrong_size,
        null_value,
        boolean_value,
        string_value,
        missing_label,
        missing_dimension,
    ],
)
def test_rejects_corrupted_response(corrupt: Callable[[dict[str, Any]], None]) -> None:
    data = load_fixture()
    corrupt(data)

    with pytest.raises(ValueError):
        decode_jsonstat(json.dumps(data), CPI_QUERY)


def test_rejects_response_for_a_different_query() -> None:
    query: dict[str, object] = {
        "query": [
            {"code": "Month", "selection": {"filter": "item", "values": ["2026M09"]}},
            {"code": "Index", "selection": {"filter": "item", "values": ["CPI"]}},
            {"code": "Item", "selection": {"filter": "item", "values": ["change_M"]}},
        ]
    }

    with pytest.raises(ValueError, match="do not match requested"):
        decode_jsonstat(FIXTURE.read_text(encoding="utf-8"), query)


def test_rejects_non_json_response() -> None:
    with pytest.raises(ValueError):
        decode_jsonstat("<html>Service unavailable</html>", CPI_QUERY)
