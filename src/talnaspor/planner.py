"""Answer questions from catalog tables by selecting dimension values with explicit rules.

For a table found in the catalog, every dimension must be settled before any data is
requested:

- the time dimension takes the year asked about, or the latest period, which must be
  recent;
- a dimension with one value takes that value;
- a dimension whose category is named in the question takes that category, preferring
  the question's own words over related terms;
- any other dimension takes its total ("Alls", "Samtals", ...), if it has one.

A table is skipped rather than guessed at when a dimension cannot be settled, when a
word in the question is not accounted for by the table's titles or categories (it may
be a restriction the answer would ignore), or when the title restricts the table to a
group the question does not mention ("Námsmenn - ...").
"""

import re
import time
from dataclasses import dataclass
from datetime import date

import requests

from talnaspor.answer import SOURCE, WORDS, Answer, Lang, format_period, format_value
from talnaspor.catalog import (
    TOKEN,
    TableHit,
    _match,
    is_current,
    question_words,
    related_phrases,
)
from talnaspor.interpret import MONTH_WORDS, Clarification, month_periods, normalize
from talnaspor.jsonstat import decode_jsonstat
from talnaspor.pxweb import PXMetadata, PXVariable, get_data, get_metadata, get_units
from talnaspor.query import build_query

TIME_VALUE = re.compile(r"\d{4}([MÁQK]\d{1,2})?")
TIME_CODES = frozenset({"ár", "mánuður", "ársfjórðungur", "year", "month", "quarter"})
MAX_OPTIONS = 8
TOTALS = frozenset(
    {
        "alls",
        "samtals",
        "allt landid",
        "landid allt",
        "karlar og konur",
        "heild",
        "total",
        "males and females",
        "both sexes",
        "whole country",
    }
)
YEAR = re.compile(r"\b([12]\d{3})\b")

# Words too common to find tables by, but which name categories such as "Fjöldi".
CATEGORY_WORDS = frozenset({"fjoldi"})

# Without a year in the question, the latest period must be at most this many years old.
RECENT_YEARS = 2

# Table metadata changes at most daily; a short cache keeps trying several tables fast.
METADATA_SECONDS = 600
_metadata: dict[str, tuple[float, PXMetadata]] = {}


def _english(url: str) -> PXMetadata | None:
    """The English version of a table's metadata, if Statistics Iceland publishes one."""
    try:
        return _get_metadata(url.replace("/pxis/api/v1/is/", "/pxen/api/v1/en/"))
    except (requests.RequestException, ValueError):
        return None


def _aligned(metadata: PXMetadata, english: PXMetadata | None) -> dict[str, PXVariable]:
    """English variables by Icelandic code, where both versions list the same value codes."""
    if english is None or len(english.variables) != len(metadata.variables):
        return {}
    return {
        icelandic.code: translated
        for icelandic, translated in zip(metadata.variables, english.variables, strict=True)
        if icelandic.values == translated.values and translated.valueTexts
    }


def _get_metadata(url: str) -> PXMetadata:
    cached = _metadata.get(url)
    if cached and time.monotonic() - cached[0] < METADATA_SECONDS:
        return cached[1]
    metadata = get_metadata(url)
    _metadata[url] = (time.monotonic(), metadata)
    return metadata


@dataclass(frozen=True)
class Choice:
    """The one dimension the user must choose before a table can answer the question."""

    table_title: str
    dimension: str
    options: list[str]
    table: TableHit | None = None

    def message(self, lang: str = "is") -> str:
        options = ", ".join(self.options)
        if lang == "en":
            return (
                f"To answer from the table “{self.table_title}”, please choose "
                f"{self.dimension.lower()}: {options}. Ask again and name your choice."
            )
        return (
            f"Til að svara úr töflunni „{self.table_title}“ þarf að velja "
            f"{self.dimension.lower()}: {options}. Spyrðu aftur og nefndu valið."
        )


def plan_answer(
    question: str,
    hits: list[TableHit],
    attempts: int = 8,
    today: date | None = None,
    lang: Lang = "is",
) -> Answer | Choice | None:
    """Answer from the first suitable current table among the hits, tried in order.

    When no table can answer, return the single choice that would let the best table
    answer, if there is one, or None.
    """
    choice: Choice | None = None
    text = normalize(question)
    years = sorted(set(YEAR.findall(text)))
    # Only a question that names a month needs a monthly period; a year alone is fine.
    names_month = any(re.search(rf"\b{word}\b", text) for word in MONTH_WORDS)
    months = month_periods(text) if names_month else []
    if len(years) > 1 or isinstance(months, Clarification) or len(months) > 1:
        return None
    # A named month ("september 2025") must be matched exactly, by a monthly table.
    period = months[0] if months else None
    year = years[0] if years else None
    oldest = None if year else str((today or date.today()).year - RECENT_YEARS)

    words = question_words(question, keep=CATEGORY_WORDS) - MONTH_WORDS
    # Numbers other than the year can name categories such as "16-74 ára".
    numbers = set(re.findall(r"\d+", normalize(question))) - set(years)
    phrases = related_phrases(question)
    weights = {word: 1.0 for word in words | numbers}
    for phrase, related in phrases:
        # A matched phrase of several words is stronger evidence than a single word.
        for term in related:
            weights[term] = max(weights.get(term, 0.0), 1.5 if " " in phrase else 0.5)

    candidates = [hit for hit in hits if is_current(hit.updated)]
    for hit in candidates[:attempts]:
        try:
            metadata = _get_metadata(hit.api_url)
            time_variable = _time_variable(metadata)
            if time_variable is None:
                continue
            english = _english(hit.api_url) if lang == "en" else None
            translated = _aligned(metadata, english)
            if not _accounts_for(words, phrases, metadata, hit, translated):
                continue
            # A series that has stopped cannot answer a question about the present.
            if oldest and max(_texts(time_variable))[:4] < oldest:
                continue
            selections, unsettled = select(metadata, weights, year, translated, period)
            if selections is None:
                if choice is None and unsettled and len(unsettled) == 1:
                    choice = _choice(metadata, unsettled[0], hit, english, translated)
                continue
            time_code = time_variable.code
            query = build_query(metadata, selections)
            data = decode_jsonstat(get_data(hit.api_url, query), query)
            if len(data.observations) != 1:
                continue
            observation = data.observations[0]
            labels = _labels(observation.codes, observation.labels, metadata, translated)
            unit = get_units(hit.api_url, query, list(labels.values()), lang)
        except (requests.RequestException, ValueError):
            continue

        in_english = lang == "en" and english is not None
        title = english.title if in_english and english else metadata.title
        dimension_labels = {
            code: translated[code].text if code in translated else label
            for code, label in data.dimension_labels.items()
        }

        # Codes may be indexes; the label is the period ("2025", "2026Á2").
        period = observation.labels[time_code]
        varying = [v.code for v in metadata.variables if v.code != time_code and len(v.values) > 1]
        # Totals are defaults rather than what was asked; they are listed with the selections.
        described = (
            ", ".join(
                labels[code] for code in varying if normalize(labels[code]).strip() not in TOTALS
            )
            or title
        )
        number = format_value(observation.value, data.decimals, "", lang)
        shown = f"{number} ({unit})" if unit else number
        wording = WORDS[lang]
        source = (data.source or SOURCE) if lang == "is" else wording["agency"]
        text = (
            f"{described} ({format_period(period, lang)}): {shown}. "
            f"{wording['source']}: {source}, {title}."
        )
        if lang == "en" and not in_english:
            text += " (Labels are in Icelandic: this table has no English version.)"

        return Answer(
            kind="catalog",
            text=text,
            value=observation.value,
            value_text=shown,
            unit=unit or "",
            period=period,
            period_label=format_period(period, lang),
            table_title=title,
            source=source,
            page_url=hit.page_url_en if in_english else hit.page_url,
            api_url=hit.api_url,
            selections=observation.codes,
            labels=labels,
            status=observation.status,
            dimension_labels=dimension_labels,
        )
    return choice


def select(
    metadata: PXMetadata,
    weights: dict[str, float],
    year: str | None,
    translated: dict[str, PXVariable] | None = None,
    period: str | None = None,
) -> tuple[dict[str, str] | None, list[PXVariable] | None]:
    """Settle every dimension of a table for a question.

    Return the selections, or None with the dimensions that could not be settled (None
    when the time cannot be settled, since no choice of category would help).
    """
    time_variable = _time_variable(metadata)
    if time_variable is None:
        return None, None

    periods = [
        (text, code)
        for code, text in zip(time_variable.values, _texts(time_variable), strict=True)
        if (text == period if period else (year is None or text.startswith(year)))
    ]
    if not periods:
        return None, None
    selections = {time_variable.code: max(periods)[1]}

    unsettled = []
    for variable in metadata.variables:
        if variable is time_variable:
            continue
        value = _settle(variable, weights, (translated or {}).get(variable.code))
        if value is None:
            unsettled.append(variable)
        else:
            selections[variable.code] = value
    return (None, unsettled) if unsettled else (selections, None)


def _settle(
    variable: PXVariable, weights: dict[str, float], english: PXVariable | None = None
) -> str | None:
    if len(variable.values) == 1:
        return variable.values[0]

    texts = _texts(variable)
    texts_en = english.valueTexts if english else [""] * len(texts)
    # A category can be named in either language ("Konur", "Females"); each question
    # term counts once, whichever label it matches.
    named = {
        index: _naming_weight(f"{text} {text_en}", weights)
        for index, (text, text_en) in enumerate(zip(texts, texts_en, strict=True))
    }
    named = {index: weight for index, weight in named.items() if weight}
    totals = [
        index
        for index, (text, text_en) in enumerate(zip(texts, texts_en, strict=True))
        if normalize(text).strip() in TOTALS or normalize(text_en).strip() in TOTALS
    ]

    if named:
        best = max(named.values())
        candidates = [index for index, weight in named.items() if weight == best]
        if len(candidates) > 1:
            # "kvenna" names both "Konur" and "Karlar og konur"; the specific one is meant.
            candidates = [index for index in candidates if index not in totals]
        return variable.values[candidates[0]] if len(candidates) == 1 else None
    return variable.values[totals[0]] if len(totals) == 1 else None


def _naming_weight(text: str, weights: dict[str, float]) -> float:
    """How strongly the question names a category label, exactly or by inflection."""
    words = TOKEN.findall(normalize(text))
    return sum(
        weight
        for term, weight in weights.items()
        if (term in words if term.isdigit() else any(_match(term, word) == 1.0 for word in words))
    )


def _accounts_for(
    words: set[str],
    phrases: list[tuple[str, tuple[str, ...]]],
    metadata: PXMetadata,
    hit: TableHit,
    translated: dict[str, PXVariable] | None = None,
) -> bool:
    """Whether the table's titles and categories account for every word in the question."""
    texts = [metadata.title, hit.title_en or "", *hit.folders, *hit.folders_en]
    for variable in [*metadata.variables, *(translated or {}).values()]:
        texts.extend([variable.text, *variable.valueTexts])
    vocabulary = {word for text in texts for word in TOKEN.findall(normalize(text))}

    def present(term: str) -> bool:
        return any(_match(term, word) for word in vocabulary)

    for word in words:
        if present(word):
            continue
        related = [
            term
            for phrase, terms in phrases
            if any(word.startswith(part) or part.startswith(word) for part in phrase.split())
            for term in terms
        ]
        if not any(present(term) for term in related):
            return False

    # A title such as "Námsmenn - Atvinnuþátttaka ..." covers only that group.
    qualifier, _, rest = metadata.title.partition(" - ")
    if rest and len(qualifier.split()) <= 2:
        qualifier_words = TOKEN.findall(normalize(qualifier))
        if not any(_match(word, term) for word in qualifier_words for term in words):
            return False
    return True


def _time_variable(metadata: PXMetadata) -> PXVariable | None:
    for variable in metadata.variables:
        if (variable.model_extra or {}).get("time"):
            return variable
    for variable in metadata.variables:
        # Codes may be indexes ("0", "1", ...) with the periods only in the labels.
        if variable.code.lower() in TIME_CODES and all(
            TIME_VALUE.fullmatch(text) for text in _texts(variable)
        ):
            return variable
    return None


def _texts(variable: PXVariable) -> list[str]:
    return variable.valueTexts or variable.values


def _text(variable: PXVariable, code: str) -> str:
    return _texts(variable)[variable.values.index(code)]


def _choice(
    metadata: PXMetadata,
    variable: PXVariable,
    hit: TableHit,
    english: PXMetadata | None = None,
    translated: dict[str, PXVariable] | None = None,
) -> Choice | None:
    shown = (translated or {}).get(variable.code, variable)
    options = _texts(shown)
    if len(options) > MAX_OPTIONS:
        return None
    title = english.title if english and variable.code in (translated or {}) else metadata.title
    return Choice(title, shown.text, options, hit)


def _labels(
    codes: dict[str, str],
    labels: dict[str, str],
    metadata: PXMetadata,
    translated: dict[str, PXVariable],
) -> dict[str, str]:
    """Category labels, in English where the table's English version lists them."""
    result = dict(labels)
    for code, value in codes.items():
        if code in translated:
            result[code] = _text(translated[code], value)
    return result
