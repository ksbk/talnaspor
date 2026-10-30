"""HTTP access to Statistics Iceland's PX-Web API."""

import json
import re
import time
from typing import Any

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


# Statistics Iceland limits requests per client and answers HTTP 429 when they come too
# fast, sometimes for a minute or more. Identical requests are therefore served from a
# short cache (figures change at most daily), and a 429 is retried once after a pause.
CACHE_SECONDS = 600
MAX_RETRY_WAIT = 3.0
_cache: dict[tuple[str, str, str | None], tuple[float, requests.Response]] = {}


class RateLimited(requests.HTTPError):
    """Statistics Iceland refused the request because too many were sent (HTTP 429)."""


def clear_cache() -> None:
    _cache.clear()


def _send(method: str, url: str, **kwargs: Any) -> requests.Response:
    key = (method, url, kwargs.get("data"))
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    send = requests.get if method == "GET" else requests.post
    response = send(url, **kwargs)
    if response.status_code == 429:
        time.sleep(_retry_wait(response))
        response = send(url, **kwargs)
        if response.status_code == 429:
            raise RateLimited(f"429 Too Many Requests for url: {url}", response=response)
    response.raise_for_status()
    _cache[key] = (time.monotonic(), response)
    return response


def _retry_wait(response: requests.Response) -> float:
    try:
        return min(float(response.headers.get("Retry-After", 1)), MAX_RETRY_WAIT)
    except (TypeError, ValueError):
        return 1.0


def get_metadata(table_url: str) -> PXMetadata:
    """Retrieve and validate metadata for a PX-Web table."""
    response = _send("GET", table_url, timeout=15)

    return PXMetadata.model_validate_json(response.text)


def get_data(
    table_url: str,
    query: dict[str, object],
) -> str:
    """Submit a PX-Web query and return the JSON response text."""
    response = _send(
        "POST",
        table_url,
        data=json.dumps(query),
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    return response.text


def get_units(
    table_url: str, query: dict[str, object], labels: list[str], lang: str = "is"
) -> str | None:
    """Return the unit Statistics Iceland states for a query's values, if any.

    The JSON formats carry no units, so the same query is requested in PX format,
    whose UNITS keyword may be general or specific to a category of the content
    dimension. A unit specific to one of the given category labels takes precedence.
    English units are the UNITS[en] lines, matched against English labels.
    """
    response = _send(
        "POST",
        table_url,
        data=json.dumps({**query, "response": {"format": "px"}}),
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    codepage = re.search(rb'CODEPAGE="([^"]+)"', response.content)
    text = response.content.decode(codepage[1].decode() if codepage else "utf-8", "replace")

    general: str | None = None
    unit: str
    keyword = r"UNITS\[en\]" if lang == "en" else "UNITS"
    pattern = rf'^{keyword}(?:\("([^"]*)"\))?="([^"]*)";'
    for key, unit in re.findall(pattern, text, re.MULTILINE):
        if key in labels:
            return unit
        if not key:
            general = unit
    return general
