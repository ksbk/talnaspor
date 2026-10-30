"""Construct validated PX-Web statistical queries."""

from collections.abc import Mapping

from talnaspor.pxweb import PXMetadata
from talnaspor.validation import validate_value


def build_query(
    metadata: PXMetadata,
    selections: Mapping[str, str],
) -> dict[str, object]:
    """Build a PX-Web query from validated dimension selections."""
    expected_codes = {variable.code for variable in metadata.variables}

    if set(selections) != expected_codes:
        raise ValueError("Selections must cover every table dimension exactly")

    query: list[dict[str, object]] = []

    for variable in metadata.variables:
        value = validate_value(
            selections[variable.code],
            variable.values,
        )

        query.append(
            {
                "code": variable.code,
                "selection": {
                    "filter": "item",
                    "values": [value],
                },
            }
        )

    return {
        "query": query,
        "response": {"format": "json-stat2"},
    }
