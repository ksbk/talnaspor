"""Answer statistical questions from a single verified PX-Web observation."""

import re
from collections.abc import Mapping
from decimal import Decimal

from pydantic import BaseModel

from talnaspor.jsonstat import decode_jsonstat
from talnaspor.pxweb import get_data, get_metadata
from talnaspor.query import build_query
from talnaspor.tables import TABLES

LATEST = "latest"
SOURCE = "Hagstofa Íslands"

MONTHS = (
    "janúar",
    "febrúar",
    "mars",
    "apríl",
    "maí",
    "júní",
    "júlí",
    "ágúst",
    "september",
    "október",
    "nóvember",
    "desember",
)


class Answer(BaseModel):
    """A source-backed answer and the evidence needed to verify it."""

    text: str
    value: int | float
    value_text: str
    unit: str
    period: str
    period_label: str
    table_title: str
    source: str
    page_url: str
    api_url: str
    selections: dict[str, str]
    labels: dict[str, str]
    status: str | None


def answer(table_key: str, selections: Mapping[str, str]) -> Answer:
    """Retrieve, verify and present one observation from a supported table.

    The time selection may be LATEST, which resolves to the table's most recent period.
    """
    table = TABLES[table_key]
    measure = table.measures.get(selections.get(table.measure_code, ""))
    if measure is None:
        raise ValueError(
            f"Unsupported measure for {table_key}: {selections.get(table.measure_code)}"
        )

    metadata = get_metadata(table.api_url)
    resolved = dict(selections)
    if resolved.get(table.time_code) == LATEST:
        time_variable = next((v for v in metadata.variables if v.code == table.time_code), None)
        if time_variable is None:
            raise ValueError(f"Table {table_key} has no time dimension {table.time_code}")
        resolved[table.time_code] = max(time_variable.values)

    query = build_query(metadata, resolved)
    data = decode_jsonstat(get_data(table.api_url, query), query)

    if len(data.observations) != 1:
        raise ValueError(f"Expected one observation, received {len(data.observations)}")

    observation = data.observations[0]
    period = observation.codes[table.time_code]
    period_label = format_period(period)
    value_text = format_value(observation.value, data.decimals, measure.unit)
    sentence = measure.template.format_map(
        {**observation.labels, "period": period_label, "value": value_text}
    )
    source = data.source or SOURCE
    text = f"{sentence}. Heimild: {source}, {metadata.title}."
    if observation.status:
        text += f" Athugasemd Hagstofu: {observation.status}."

    return Answer(
        text=text,
        value=observation.value,
        value_text=value_text,
        unit=measure.unit,
        period=period,
        period_label=period_label,
        table_title=metadata.title,
        source=source,
        page_url=table.page_url,
        api_url=table.api_url,
        selections=observation.codes,
        labels=observation.labels,
        status=observation.status,
    )


def format_period(code: str) -> str:
    """Render a PX-Web time code such as 2026M09 in Icelandic."""
    month = re.fullmatch(r"(\d{4})M(0[1-9]|1[0-2])", code)
    if month:
        return f"{MONTHS[int(month[2]) - 1]} {month[1]}"
    return code


def format_value(value: float, decimals: int | None, unit: str) -> str:
    """Format a value in Icelandic style without dropping any reported digits.

    Table-level decimals can understate a measure's precision, so the value's own
    digits are never rounded away.
    """
    exponent = Decimal(repr(value)).as_tuple().exponent
    own_decimals = -exponent if isinstance(exponent, int) and exponent < 0 else 0
    places = max(decimals or 0, own_decimals)
    number = f"{value:,.{places}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{number}%" if unit == "%" else f"{number} {unit}"
