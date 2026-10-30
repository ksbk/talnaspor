"""Construct validated PX-Web statistical queries."""

from collections.abc import Mapping

from talnaspor.pxweb import PXMetadata
from talnaspor.validation import validate_value


def build_query(
    metadata: PXMetadata,
    selections: Mapping[str, str | list[str]],
) -> dict[str, object]:
    """Build a PX-Web query from validated dimension selections.

    Each selection is one value code, or a list of distinct value codes.
    """
    expected_codes = {variable.code for variable in metadata.variables}

    if set(selections) != expected_codes:
        raise ValueError("Selections must cover every table dimension exactly")

    query: list[dict[str, object]] = []

    for variable in metadata.variables:
        selected = selections[variable.code]
        requested = [selected] if isinstance(selected, str) else selected

        if not requested or len(set(requested)) != len(requested):
            raise ValueError(f"Selection for {variable.code} must list distinct values")

        values = [validate_value(value, variable.values) for value in requested]

        query.append(
            {
                "code": variable.code,
                "selection": {
                    "filter": "item",
                    "values": values,
                },
            }
        )

    return {
        "query": query,
        "response": {"format": "json-stat2"},
    }
