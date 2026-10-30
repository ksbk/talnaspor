"""Decode PX-Web JSON-stat2 responses into verified statistical observations."""

import math
from collections.abc import Mapping
from itertools import product
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt


class _Category(BaseModel):
    index: dict[str, int] | list[str]
    label: dict[str, str] = Field(default_factory=dict)


class _Dimension(BaseModel):
    label: str
    category: _Category


class _Dataset(BaseModel):
    model_config = ConfigDict(extra="allow")

    class_: Literal["dataset"] = Field(alias="class")
    label: str
    source: str | None = None
    id: list[str]
    size: list[int]
    dimension: dict[str, _Dimension]
    value: list[StrictInt | StrictFloat | None]
    status: str | list[str | None] | dict[str, str] | None = None
    extension: dict[str, object] = Field(default_factory=dict)


class _Selection(BaseModel):
    values: list[str]


class _QueryEntry(BaseModel):
    code: str
    selection: _Selection


class _Query(BaseModel):
    query: list[_QueryEntry]


class Observation(BaseModel):
    """One official value and the dimension categories that identify it."""

    value: int | float
    codes: dict[str, str]
    labels: dict[str, str]
    status: str | None = None


class StatData(BaseModel):
    """Observations decoded from a JSON-stat2 dataset."""

    label: str
    source: str | None
    dimension_labels: dict[str, str]
    decimals: int | None
    observations: list[Observation]


def decode_jsonstat(text: str, query: Mapping[str, object]) -> StatData:
    """Decode a JSON-stat2 response, verifying that it answers exactly the query."""
    dataset = _Dataset.model_validate_json(text)
    requested = _Query.model_validate(query).query
    codes = [entry.code for entry in requested]

    if dataset.id != codes:
        raise ValueError(f"Response dimensions {dataset.id} do not match query {codes}")
    if len(dataset.size) != len(codes) or set(dataset.dimension) != set(codes):
        raise ValueError("Response dimension metadata is inconsistent")

    ordered_categories: list[list[str]] = []
    for entry, size in zip(requested, dataset.size, strict=True):
        category = dataset.dimension[entry.code].category
        positions = _positions(category.index)
        wanted = entry.selection.values

        if len(set(wanted)) != len(wanted):
            raise ValueError(f"Query repeats values for {entry.code}")
        if set(positions) != set(wanted):
            raise ValueError(
                f"Response categories for {entry.code} {sorted(positions)} "
                f"do not match requested {sorted(wanted)}"
            )
        if sorted(positions.values()) != list(range(size)):
            raise ValueError(f"Category positions for {entry.code} do not match size {size}")
        if not set(wanted) <= set(category.label):
            raise ValueError(f"Response is missing category labels for {entry.code}")

        ordered_categories.append(sorted(wanted, key=positions.__getitem__))

    if math.prod(dataset.size) != len(dataset.value):
        raise ValueError(f"Response has {len(dataset.value)} values for shape {dataset.size}")

    observations: list[Observation] = []
    for flat_index, combination in enumerate(product(*ordered_categories)):
        cell = dict(zip(codes, combination, strict=True))
        value = dataset.value[flat_index]
        status = _status(dataset.status, flat_index)

        if value is None:
            raise ValueError(f"Missing value for {cell} (status {status!r})")
        if not math.isfinite(value):
            raise ValueError(f"Non-finite value for {cell}")

        observations.append(
            Observation(
                value=value,
                codes=cell,
                labels={
                    code: dataset.dimension[code].category.label[category]
                    for code, category in cell.items()
                },
                status=status,
            )
        )

    return StatData(
        label=dataset.label,
        source=dataset.source,
        dimension_labels={code: dataset.dimension[code].label for code in codes},
        decimals=_decimals(dataset.extension),
        observations=observations,
    )


def _positions(index: dict[str, int] | list[str]) -> dict[str, int]:
    if isinstance(index, dict):
        return index
    if len(set(index)) != len(index):
        raise ValueError("Response category index repeats codes")
    return {code: position for position, code in enumerate(index)}


def _status(status: str | list[str | None] | dict[str, str] | None, index: int) -> str | None:
    if isinstance(status, list):
        return status[index] if index < len(status) else None
    if isinstance(status, dict):
        return status.get(str(index))
    return status


def _decimals(extension: dict[str, object]) -> int | None:
    px = extension.get("px")
    if not isinstance(px, dict):
        return None
    decimals = px.get("decimals")
    return decimals if isinstance(decimals, int) and not isinstance(decimals, bool) else None
