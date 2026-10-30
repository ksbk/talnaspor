"""HTTP access to Statistics Iceland's PX-Web API."""

import json
import re

import requests
from pydantic import BaseModel, ConfigDict, Field, model_validator


class PXVariable(BaseModel):
    """A statistical dimension and its available value codes."""

    model_config = ConfigDict(extra="allow")

    code: str
    text: str
    values: list[str]
    valueTexts: list[str] = Field(default_factory=list)


class PXMetadata(BaseModel):
    """Validated metadata for a PX-Web table."""

    model_config = ConfigDict(extra="allow")

    title: str
    variables: list[PXVariable]

    @model_validator(mode="after")
    def check_invariants(self) -> "PXMetadata":
        """Reject metadata that could produce ambiguous queries or labels."""
        if not self.variables:
            raise ValueError("Metadata must define at least one variable")

        codes = [variable.code for variable in self.variables]
        if len(codes) != len(set(codes)):
            raise ValueError("Variable codes must be unique")

        for variable in self.variables:
            if not variable.values:
                raise ValueError(f"Variable {variable.code} has no values")
            if len(variable.values) != len(set(variable.values)):
                raise ValueError(f"Variable {variable.code} has duplicate values")
            if variable.valueTexts and len(variable.valueTexts) != len(variable.values):
                raise ValueError(f"Variable {variable.code} has mismatched value texts")

        return self


def get_metadata(table_url: str) -> PXMetadata:
    """Retrieve and validate metadata for a PX-Web table."""
    response = requests.get(table_url, timeout=15)
    response.raise_for_status()

    return PXMetadata.model_validate_json(response.text)


def get_data(
    table_url: str,
    query: dict[str, object],
) -> str:
    """Submit a PX-Web query and return the JSON response text."""
    response = requests.post(
        table_url,
        data=json.dumps(query),
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    return response.text


def get_units(table_url: str, query: dict[str, object], labels: list[str]) -> str | None:
    """Return the unit Statistics Iceland states for a query's values, if any.

    The JSON formats carry no units, so the same query is requested in PX format,
    whose UNITS keyword may be general or specific to a category of the content
    dimension. A unit specific to one of the given category labels takes precedence.
    """
    response = requests.post(
        table_url,
        data=json.dumps({**query, "response": {"format": "px"}}),
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    codepage = re.search(rb'CODEPAGE="([^"]+)"', response.content)
    text = response.content.decode(codepage[1].decode() if codepage else "utf-8", "replace")

    general: str | None = None
    unit: str
    for key, unit in re.findall(r'^UNITS(?:\("([^"]*)"\))?="([^"]*)";', text, re.MULTILINE):
        if key in labels:
            return unit
        if not key:
            general = unit
    return general
