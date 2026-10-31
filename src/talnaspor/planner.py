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
from decimal import Decimal
from typing import Literal

import requests

from talnaspor.answer import (
    SOURCE,
    WORDS,
    Answer,
    Comparison,
    Lang,
    Point,
    _signed,
    format_period,
    format_value,
)
from talnaspor.catalog import (
    TOKEN,
    TableHit,
    _match,
    is_current,
    question_words,
    related_phrases,
)
from talnaspor.interpret import (
    CHANGE,
    MONTH_WORDS,
    NUMBERS,
    SINCE,
    SPAN,
    START_OF_YEAR,
    Clarification,
    month_periods,
    name_spans,
    normalize,
)
from talnaspor.jsonstat import decode_jsonstat
from talnaspor.pxweb import (
    PXMetadata,
    PXVariable,
    RateLimited,
    get_data,
    get_metadata,
    get_units,
)
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

# The labour force survey covers ages 16-74: in its tables that age group is the total,
# used only when a dimension has no other total ("Alls").
SURVEY_TOTALS = frozenset({"16-74 ara", "16-74 years", "16-74"})

# An index table's level ("Vísitölugildi", "Vísitala"), the default for its measure when
# a question names none and the dimension has no total: "Hver var launavísitalan?" asks
# for the index, not its monthly or annual change.
LEVELS = frozenset({"visitolugildi", "visitala", "index", "index value"})

# General-knowledge questions that share words with statistical tables ("capital of
# Iceland" is not about capital transfers); they get suggestions, never a figure.
GENERAL_KNOWLEDGE = re.compile(r"\b(capital of|capital city|hofudborg)")

# Category labels led by an accounting code ("00-00-00 Number") are line items that a
# plain question is unlikely to mean, and that a reader cannot interpret.
CODED_LABEL = re.compile(r"^\d{2}-\d{2}-\d{2}\b")

# Words too common to find tables by, but which name categories such as "Fjöldi".
CATEGORY_WORDS = frozenset({"fjoldi"})

# Without a year in the question, the latest period must be at most this many years old.
RECENT_YEARS = 2

# Table metadata changes at most daily; a cache keeps trying several tables fast.
METADATA_SECONDS = 3600
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
    text = START_OF_YEAR.sub("", normalize(question))
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

    if GENERAL_KNOWLEDGE.search(text):
        return None
    words = question_words(question, keep=CATEGORY_WORDS) - MONTH_WORDS
    # Numbers other than the year can name categories such as "16-74 ára".
    numbers = set(re.findall(r"\d+", text)) - set(years)
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
            title_en = english.title if english else None
            if not _accounts_for(words, phrases, metadata, hit, translated, title_en):
                continue
            if not _names_topic(words, phrases, metadata, hit, english):
                continue
            if _counts_together(words, phrases, metadata, hit, english, translated):
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
            if any(
                CODED_LABEL.match(label)
                for label in [*observation.labels.values(), *labels.values()]
            ):
                continue
            unit = get_units(hit.api_url, query, list(labels.values()), lang)
        except RateLimited:
            # Not a problem with this table: every further request would be refused too.
            raise
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
                labels[code]
                for code in varying
                if normalize(labels[code]).strip() not in TOTALS | SURVEY_TOTALS
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
    named = {
        index: weight
        for index, weight in named.items()
        if weight and _eligible(f"{texts[index]} {texts_en[index]}", weights)
    }
    totals = (
        [
            index
            for index, (text, text_en) in enumerate(zip(texts, texts_en, strict=True))
            if normalize(text).strip() in TOTALS or normalize(text_en).strip() in TOTALS
        ]
        or [
            index
            for index, (text, text_en) in enumerate(zip(texts, texts_en, strict=True))
            if normalize(text).strip() in SURVEY_TOTALS
            or normalize(text_en).strip() in SURVEY_TOTALS
        ]
        or [
            index
            for index, (text, text_en) in enumerate(zip(texts, texts_en, strict=True))
            if normalize(text).strip() in LEVELS or normalize(text_en).strip() in LEVELS
        ]
    )

    if named:
        best = max(named.values())
        candidates = [index for index, weight in named.items() if weight == best]
        if len(candidates) > 1:
            # "kvenna" names both "Konur" and "Karlar og konur"; the specific one is meant.
            candidates = [index for index in candidates if index not in totals]
        return variable.values[candidates[0]] if len(candidates) == 1 else None
    return variable.values[totals[0]] if len(totals) == 1 else None


# Categories chosen only when the question uses one of these words: "How many children
# were born" names both "All children" and "First born children", but asks about all.
QUALIFIED = {"frumburd": ("frumburd", "first"), "first born": ("frumburd", "first")}


def _eligible(label: str, weights: dict[str, float]) -> bool:
    text = normalize(label)
    return all(
        any(term.startswith(required) for term in weights for required in words)
        for qualifier, words in QUALIFIED.items()
        if qualifier in text
    )


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
    title_en: str | None = None,
) -> bool:
    """Whether the table's titles and categories account for every word in the question.

    The English title comes from the table's English metadata when the catalog lacks it.
    """
    texts = [metadata.title, hit.title_en or title_en or "", *hit.folders, *hit.folders_en]
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


def _names_topic(
    words: set[str],
    phrases: list[tuple[str, tuple[str, ...]]],
    metadata: PXMetadata,
    hit: TableHit,
    english: PXMetadata | None,
) -> bool:
    """Whether a question word (or a term related to one) fully names a word in the title.

    Fragments are not enough: "laun" (wages) only partly matches "launuðu" (paid), and
    the table of staff on paid leave does not answer a question about wages.
    """
    titles = [metadata.title, hit.title_en or "", english.title if english else ""]
    title_words = {word for title in titles for word in TOKEN.findall(normalize(title))}
    terms = set(words) - CATEGORY_WORDS
    for _, related in phrases:
        terms.update(related)
    return any(_match(term, word) == 1.0 for term in terms for word in title_words)


# Two words joined in a title: "hótelum og gistiheimilum", "hotels and guesthouses".
JOINED = re.compile(r"\b([a-z]{3,}) (?:og|and) ([a-z]{3,})\b")


def _counts_together(
    words: set[str],
    phrases: list[tuple[str, tuple[str, ...]]],
    metadata: PXMetadata,
    hit: TableHit,
    english: PXMetadata | None,
    translated: dict[str, PXVariable] | None = None,
) -> bool:
    """Whether the table counts together two things the question tells apart.

    A title that joins two things ("Gistinætur á hótelum og gistiheimilum") which no
    dimension of the table separates reports their sum, so it does not answer a question
    that names only one of them ("hotel overnight stays"). Joined things that a dimension
    does separate ("Gistinætur og gestakomur", with a dimension listing both) are fine.
    """
    separated = {
        word
        for variable in [*metadata.variables, *(translated or {}).values()]
        for text in [variable.text, *variable.valueTexts]
        for word in TOKEN.findall(normalize(text))
    }
    terms = set(words)
    for _, related in phrases:
        terms.update(related)

    def named(word: str) -> bool:
        # As loosely as the word check accepts a word, so that a misspelling ("hotelli")
        # cannot pass that check and still slip past this one.
        return any(_match(term, word) for term in terms)

    titles = [metadata.title, hit.title_en or "", english.title if english else ""]
    for title in titles:
        for first, second in JOINED.findall(normalize(title)):
            if any(_match(word, known) == 1.0 for word in (first, second) for known in separated):
                continue
            if named(first) != named(second):
                return True
    return False


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


# Words that ask for a change over time. They name no table or category, so a comparison
# does not require a table to account for them.
CHANGE_STEMS = (
    "chang", "breyt", "fjolg", "faekk", "aukn", "aukist", "haekk", "laekk", "between", "milli",
    "fra", "til", "since", "sidan", "compar", "samanburd", "thro", "trend", "increas",
    "decreas", "rise", "rose", "fell", "grow", "grew", "mikid", "much", "last", "past",
    "sidust", "years", "arin", "decade", "aratug",
)  # fmt: skip

Kind = Literal["percent", "index", "level"]

# Units that state a count or an amount, whose change is a difference and a percent.
LEVEL_UNITS = frozenset(
    {"fjoldi", "number", "einstaklingar", "persons", "ibuar", "inhabitants", "people"}
)


@dataclass(frozen=True)
class Span:
    """The two periods a comparison asks about.

    start and end are period labels ("2020", "2025M09"); end None is the table's latest
    period, and start None with years_back is that many years before the end.
    """

    start: str | None
    end: str | None
    years_back: int | None = None


def comparison_span(question: str) -> Span | None:
    """The periods a question asks to compare, or None if it asks about one period.

    Two years or two months ("between 2020 and 2025"), a change since a year ("how has it
    changed since 2019"), or a number of years to the latest ("the last five years").
    """
    text = START_OF_YEAR.sub("", normalize(question))
    names_month = any(re.search(rf"\b{word}\b", text) for word in MONTH_WORDS)
    months = month_periods(text) if names_month else []
    if isinstance(months, Clarification):
        return None
    years = sorted(set(YEAR.findall(text)))
    if months:
        return Span(months[0], months[1]) if len(months) == 2 else None
    if len(years) == 2:
        return Span(years[0], years[1])
    # A span of years ("síðustu fimm ár") is a comparison even without a word for change,
    # as in the curated answers.
    text = name_spans(text)
    span = SPAN.search(text)
    if span and not years and not span[2].startswith(("man", "month")):
        count = int(span[1]) if span[1].isdigit() else NUMBERS[span[1]]
        return Span(None, None, count)
    if len(years) == 1 and SINCE.search(text) and CHANGE.search(text):
        return Span(years[0], None)
    return None


def measure_kind(unit: str | None, labels: list[str]) -> Kind | None:
    """Whether a measure is a percent, an index or a level (a count), or None if unclear.

    A selected category that says so ("Atvinnuleysi, % (af vinnuafli)", "Vísitala") decides;
    otherwise the unit does. A missing or mixed unit ("Fjöldi/hlutfall") is unclear, and a
    change is never computed for an unclear measure.
    """
    for label in labels:
        text = normalize(label).strip()
        if "%" in text:
            return "percent"
        if text.startswith(("visitala", "index")):
            return "index"
    text = normalize(unit or "").strip()
    if not text or "/" in text:
        return None
    if "%" in text or text in {"hlutfall", "prosent", "percent", "percentage"}:
        return "percent"
    if text.startswith(("visitala", "index")):
        return "index"
    return "level" if text in LEVEL_UNITS else None


def _shift_years(label: str, years: int) -> str:
    """The same period a number of years earlier: 2026 → 2021, 2026M09 → 2021M09."""
    return f"{int(label[:4]) - years}{label[4:]}"


def plan_comparison(
    question: str,
    hits: list[TableHit],
    span: Span,
    attempts: int = 8,
    today: date | None = None,
    lang: Lang = "is",
) -> Comparison | Choice | None:
    """Compare one measure between two periods from the first suitable current table.

    Every dimension but time is settled as for a single answer, and both periods come from
    one verified query, so the two values differ only in time. The change is stated in
    percentage points for a percent, as a percent for an index, and as a difference and a
    percent for a level; a table whose measure is unclear is skipped.
    """
    choice: Choice | None = None
    text = START_OF_YEAR.sub("", normalize(question))
    years = set(YEAR.findall(text))
    words = {
        word
        for word in question_words(question, keep=CATEGORY_WORDS) - MONTH_WORDS
        if not word.startswith(CHANGE_STEMS) and word not in NUMBERS
    }
    numbers = set(re.findall(r"\d+", text)) - years - {str(span.years_back)}
    phrases = related_phrases(question)
    weights = {word: 1.0 for word in words | numbers}
    for phrase, related in phrases:
        for term in related:
            weights[term] = max(weights.get(term, 0.0), 1.5 if " " in phrase else 0.5)
    oldest = str((today or date.today()).year - RECENT_YEARS)

    for hit in [hit for hit in hits if is_current(hit.updated)][:attempts]:
        try:
            metadata = _get_metadata(hit.api_url)
            time_variable = _time_variable(metadata)
            if time_variable is None:
                continue
            english = _english(hit.api_url) if lang == "en" else None
            translated = _aligned(metadata, english)
            title_en = english.title if english else None
            if not _accounts_for(words, phrases, metadata, hit, translated, title_en):
                continue
            if not _names_topic(words, phrases, metadata, hit, english):
                continue
            if _counts_together(words, phrases, metadata, hit, english, translated):
                continue
            codes = dict(zip(_texts(time_variable), time_variable.values, strict=True))
            end = span.end or max(codes)
            if span.end is None and end[:4] < oldest:
                continue
            start = span.start or _shift_years(end, span.years_back or 0)
            if start not in codes or end not in codes or start >= end:
                continue
            selections, unsettled = select(metadata, weights, None, translated, end)
            if selections is None:
                if choice is None and unsettled and len(unsettled) == 1:
                    choice = _choice(metadata, unsettled[0], hit, english, translated)
                continue
            time_code = time_variable.code
            query = build_query(metadata, {**selections, time_code: [codes[start], codes[end]]})
            data = decode_jsonstat(get_data(hit.api_url, query), query)
            if len(data.observations) != 2:
                continue
            first, last = sorted(
                data.observations, key=lambda o: _texts(time_variable).index(o.labels[time_code])
            )
            labels = _labels(first.codes, first.labels, metadata, translated)
            if any(
                CODED_LABEL.match(label) for label in [*first.labels.values(), *labels.values()]
            ):
                continue
            unit = get_units(hit.api_url, query, list(labels.values()), lang)
            kind = measure_kind(unit, [labels[c] for c in labels if c != time_code])
            if kind is None:
                continue
        except RateLimited:
            raise
        except (requests.RequestException, ValueError):
            continue

        in_english = lang == "en" and english is not None
        title = english.title if in_english and english else metadata.title
        wording = WORDS[lang]
        varying = [v.code for v in metadata.variables if v.code != time_code and len(v.values) > 1]
        described = (
            ", ".join(
                labels[code]
                for code in varying
                if normalize(labels[code]).strip() not in TOTALS | SURVEY_TOTALS
            )
            or title
        )

        start_point, end_point = (
            Point(
                period=observation.labels[time_code],
                period_label=format_period(observation.labels[time_code], lang),
                value=observation.value,
                value_text=(
                    f"{format_value(observation.value, data.decimals, '', lang)} ({unit})"
                    if unit
                    else format_value(observation.value, data.decimals, "", lang)
                ),
                status=observation.status,
            )
            for observation in (first, last)
        )
        exact = Decimal(repr(last.value)) - Decimal(repr(first.value))
        difference: int | float = (
            int(exact)
            if isinstance(first.value, int) and isinstance(last.value, int)
            else float(exact)
        )
        unit_word = {"percent": wording["points"], "index": wording["index_points"]}.get(kind, "")
        difference_text = _signed(format_value(difference, data.decimals, "", lang), difference)
        difference_text += f" {unit_word}" if unit_word else (f" ({unit})" if unit else "")
        relative_text = None
        if kind != "percent" and first.value != 0:
            relative = round(float(exact / abs(Decimal(repr(first.value))) * 100), 1)
            relative_text = _signed(format_value(relative, 1, "%", lang), relative)
        change = difference_text + (f" ({relative_text})" if relative_text else "")
        source = (data.source or SOURCE) if lang == "is" else wording["agency"]
        text = (
            f"{described}: {start_point.period_label} {start_point.value_text}, "
            f"{end_point.period_label} {end_point.value_text}. {wording['change']}: {change}. "
            f"{wording['source']}: {source}, {title}."
        )
        if lang == "en" and not in_english:
            text += " (Labels are in Icelandic: this table has no English version.)"
        return Comparison(
            text=text,
            unit=unit or "",
            start=start_point,
            end=end_point,
            difference=difference,
            difference_text=difference_text,
            relative_change_text=relative_text,
            table_title=title,
            source=source,
            page_url=hit.page_url_en if in_english else hit.page_url,
            api_url=hit.api_url,
            selections={
                code: [first.codes[code], last.codes[code]] if code == time_code else [value]
                for code, value in first.codes.items()
            },
            labels={code: label for code, label in labels.items() if code != time_code},
        )
    return choice
