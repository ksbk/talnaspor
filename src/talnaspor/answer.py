"""Answer statistical questions from verified PX-Web observations."""

import re
from collections.abc import Mapping
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from talnaspor.jsonstat import Observation, StatData, decode_jsonstat
from talnaspor.pxweb import get_data, get_metadata
from talnaspor.query import build_query
from talnaspor.tables import TABLES, Measure, Table

LATEST = "latest"
SOURCE = "Hagstofa Íslands"

Lang = Literal["is", "en"]

WORDS: dict[str, dict[str, str]] = {
    "is": {
        "agency": "Hagstofa Íslands",
        "source": "Heimild",
        "note": "Athugasemd Hagstofu",
        "change": "Breyting",
        "points": "prósentustig",
    },
    "en": {
        "agency": "Statistics Iceland",
        "source": "Source",
        "note": "Note from Statistics Iceland",
        "change": "Change",
        "points": "percentage points",
    },
}

MONTHS_EN = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

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
    """A source-backed answer and the evidence needed to verify it.

    A "curated" answer comes from a configured table with known units and wording. A
    "catalog" answer comes from a table found in the catalog, with dimension values
    selected by rules from the question; its unit is not known beyond the labels.
    """

    kind: Literal["curated", "catalog"] = "curated"
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
    dimension_labels: dict[str, str] = {}


class Point(BaseModel):
    """One verified observation in a comparison."""

    period: str
    period_label: str
    value: int | float
    value_text: str
    status: str | None


class Comparison(BaseModel):
    """A change between two verified observations of the same measure."""

    text: str
    unit: str
    start: Point
    end: Point
    difference: int | float
    difference_text: str
    relative_change_text: str | None
    table_title: str
    source: str
    page_url: str
    api_url: str
    selections: dict[str, list[str]]
    labels: dict[str, str]


def before_latest(steps: int) -> str:
    """Name the period a number of time steps before a table's most recent period."""
    return f"{LATEST}-{steps}"


def answer(table_key: str, selections: Mapping[str, str], lang: Lang = "is") -> Answer:
    """Retrieve, verify and present one observation from a supported table.

    The time selection may be LATEST or before_latest(n), which resolve against the
    table's most recent period.
    """
    table, measure, title, data = _retrieve(table_key, selections)

    if len(data.observations) != 1:
        raise ValueError(f"Expected one observation, received {len(data.observations)}")

    observation = data.observations[0]
    point, sentence = _point(observation, table, measure, data, lang)
    words = WORDS[lang]
    source = (data.source or SOURCE) if lang == "is" else words["agency"]
    title = title if lang == "is" else table.title_en
    text = f"{sentence}. {words['source']}: {source}, {title}."
    if observation.status:
        text += f" {words['note']}: {observation.status}."

    return Answer(
        text=text,
        value=observation.value,
        value_text=point.value_text,
        unit=measure.unit if lang == "is" else measure.unit_en,
        period=point.period,
        period_label=point.period_label,
        table_title=title,
        source=source,
        page_url=table.page_url if lang == "is" else table.page_url_en,
        api_url=table.api_url,
        selections=observation.codes,
        labels=_labels(observation, table, lang),
        status=observation.status,
    )


def compare(
    table_key: str, selections: Mapping[str, str], start: str, lang: Lang = "is"
) -> Comparison:
    """Compare one measure between a start period and the selected end period.

    Both periods may be LATEST or before_latest(n). Percentages are compared in
    percentage points; other measures also report the relative change.
    """
    table = TABLES[table_key]
    periods = [start, selections[table.time_code]]
    table, measure, title, data = _retrieve(table_key, {**selections, table.time_code: periods})

    if len(data.observations) != 2:
        raise ValueError(f"Expected two observations, received {len(data.observations)}")

    first, last = sorted(data.observations, key=lambda o: o.codes[table.time_code])
    start_point, start_sentence = _point(first, table, measure, data, lang)
    end_point, end_sentence = _point(last, table, measure, data, lang)
    words = WORDS[lang]
    unit = measure.unit if lang == "is" else measure.unit_en

    difference_exact = Decimal(repr(last.value)) - Decimal(repr(first.value))
    difference: int | float = (
        int(difference_exact)
        if isinstance(first.value, int) and isinstance(last.value, int)
        else float(difference_exact)
    )
    difference_unit = words["points"] if unit == "%" else unit
    difference_text = _signed(
        format_value(difference, data.decimals, difference_unit, lang), difference
    )

    relative_change_text = None
    if measure.unit != "%" and first.value != 0:
        relative = round(float(difference_exact / abs(Decimal(repr(first.value))) * 100), 1)
        relative_change_text = _signed(format_value(relative, 1, "%", lang), relative)

    change = difference_text + (f" ({relative_change_text})" if relative_change_text else "")
    source = (data.source or SOURCE) if lang == "is" else words["agency"]
    title = title if lang == "is" else table.title_en
    text = (
        f"{start_sentence}. {end_sentence}. {words['change']}: {change}. "
        f"{words['source']}: {source}, {title}."
    )
    statuses = sorted({o.status for o in (first, last) if o.status})
    if statuses:
        text += f" {words['note']}: {', '.join(statuses)}."

    return Comparison(
        text=text,
        unit=unit,
        start=start_point,
        end=end_point,
        difference=difference,
        difference_text=difference_text,
        relative_change_text=relative_change_text,
        table_title=title,
        source=source,
        page_url=table.page_url if lang == "is" else table.page_url_en,
        api_url=table.api_url,
        selections={
            code: [first.codes[code], last.codes[code]]
            if code == table.time_code
            else [first.codes[code]]
            for code in first.codes
        },
        labels={
            code: label
            for code, label in _labels(first, table, lang).items()
            if code != table.time_code
        },
    )


def _retrieve(
    table_key: str, selections: Mapping[str, str | list[str]]
) -> tuple[Table, Measure, str, StatData]:
    table = TABLES[table_key]
    measure_code = selections.get(table.measure_code)
    measure = table.measures.get(measure_code) if isinstance(measure_code, str) else None
    if measure is None:
        raise ValueError(f"Unsupported measure for {table_key}: {measure_code}")

    metadata = get_metadata(table.api_url)
    time_variable = next((v for v in metadata.variables if v.code == table.time_code), None)
    if time_variable is None:
        raise ValueError(f"Table {table_key} has no time dimension {table.time_code}")

    latest = max(time_variable.values)
    resolved = dict(selections)
    time_selection = resolved.get(table.time_code)
    if isinstance(time_selection, str):
        resolved[table.time_code] = _resolve_period(time_selection, latest)
    elif time_selection is not None:
        resolved[table.time_code] = [_resolve_period(p, latest) for p in time_selection]

    query = build_query(metadata, resolved)
    data = decode_jsonstat(get_data(table.api_url, query), query)
    return table, measure, metadata.title, data


def _point(
    observation: Observation, table: Table, measure: Measure, data: StatData, lang: Lang
) -> tuple[Point, str]:
    period = observation.codes[table.time_code]
    period_label = format_period(period, lang)
    unit = measure.unit if lang == "is" else measure.unit_en
    value_text = format_value(observation.value, data.decimals, unit, lang)
    template = measure.template if lang == "is" else measure.template_en
    sentence = template.format_map(
        {**_labels(observation, table, lang), "period": period_label, "value": value_text}
    )
    point = Point(
        period=period,
        period_label=period_label,
        value=observation.value,
        value_text=value_text,
        status=observation.status,
    )
    return point, sentence


def _labels(observation: Observation, table: Table, lang: Lang) -> dict[str, str]:
    """Category labels in the answer's language, from Statistics Iceland's English labels."""
    if lang == "is":
        return dict(observation.labels)
    return {
        code: table.labels_en.get(code, {}).get(value, observation.labels[code])
        for code, value in observation.codes.items()
    }


def _resolve_period(token: str, latest: str) -> str:
    if token == LATEST:
        return latest
    offset = re.fullmatch(rf"{LATEST}-(\d+)", token)
    if offset:
        return shift_period(latest, -int(offset[1]))
    return token


def shift_period(code: str, steps: int) -> str:
    """Move a year (2026) or month (2026M09) code by a number of its own steps."""
    if re.fullmatch(r"\d{4}", code):
        return str(int(code) + steps)
    month = re.fullmatch(r"(\d{4})M(0[1-9]|1[0-2])", code)
    if month:
        year, index = divmod(int(month[1]) * 12 + int(month[2]) - 1 + steps, 12)
        return f"{year}M{index + 1:02d}"
    raise ValueError(f"Cannot shift period {code}")


def _signed(text: str, value: float) -> str:
    return f"+{text}" if value > 0 else text


def format_period(code: str, lang: Lang = "is") -> str:
    """Render a PX-Web time code such as 2026M09 or 2026Á2 in Icelandic or English."""
    month = re.fullmatch(r"(\d{4})M(0[1-9]|1[0-2])", code)
    if month:
        names = MONTHS if lang == "is" else MONTHS_EN
        return f"{names[int(month[2]) - 1]} {month[1]}"
    quarter = re.fullmatch(r"(\d{4})[ÁQK]([1-4])", code)
    if quarter:
        if lang == "en":
            return f"Q{quarter[2]} {quarter[1]}"
        return f"{quarter[2]}. ársfjórðungur {quarter[1]}"
    return code


def format_value(value: float, decimals: int | None, unit: str, lang: Lang = "is") -> str:
    """Format a value without dropping any reported digits.

    Icelandic style uses a decimal comma and dot separators (1.234,5); English style the
    reverse (1,234.5).

    Table-level decimals can understate a measure's precision, so the value's own
    digits are never rounded away.
    """
    exponent = Decimal(repr(value)).as_tuple().exponent
    own_decimals = -exponent if isinstance(exponent, int) and exponent < 0 else 0
    places = max(decimals or 0, own_decimals)
    number = f"{value:,.{places}f}"
    if lang == "is":
        number = number.replace(",", "_").replace(".", ",").replace("_", ".")
    if not unit:
        return number
    return f"{number}%" if unit == "%" else f"{number} {unit}"
