"""Interpret Icelandic and English questions as table selections, using explicit rules."""

import re
import unicodedata
from dataclasses import dataclass

from talnaspor.answer import LATEST, before_latest


@dataclass(frozen=True)
class Interpretation:
    """A supported table and the dimension selections a question asks for.

    When compare_from is set, the question asks how the measure changed from that
    period to the selected one.
    """

    table: str
    selections: dict[str, str]
    compare_from: str | None = None


@dataclass(frozen=True)
class Clarification:
    """Why a question cannot be answered as asked, and what the user can ask instead."""

    message: str


SUPPORTED = (
    "Ég get svarað spurningum um verðbólgu og vísitölu neysluverðs eftir mánuðum "
    "og um mannfjölda á Íslandi eftir árum."
)

MONTHS = {
    "januar": 1,
    "january": 1,
    "februar": 2,
    "february": 2,
    "mars": 3,
    "march": 3,
    "april": 4,
    "mai": 5,
    # English "may" is also a verb, so it only counts as a month before a year.
    r"may(?=,?\s+(?:of\s+)?\d{4})": 5,
    "juni": 6,
    "june": 6,
    "juli": 7,
    "july": 7,
    "agust": 8,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "october": 10,
    "november": 11,
    "desember": 12,
    "december": 12,
}

CPI_WORDS = ("verdbolg", "inflation", "neysluverd", "consumer price", "cpi")
POPULATION_WORDS = (
    "mannfjold",
    "ibua",
    "population",
    "inhabitants",
    "people live",
    "bua a islandi",
    "bua margir",
    "margir bua",
    "adfluttir umfram",
    "net migration",
    "faeddir umfram",
    "natural increase",
)


# Word starts only, so that "arsbreyting" (annual change) is not a change-over-time question.
CHANGE = re.compile(
    r"\b(breyst|breyttist|breyting|thro(un|a)|aukist|haekkad|laekkad|vaxid|samanburd"
    r"|change|trend|compare|comparison|grown|since"
    r"|(fra|sidan)\s+(\w+\s+)?(1[7-9]|20)\d{2})"
)


def normalize(text: str) -> str:
    """Lowercase and strip diacritics, mapping þ, æ and ð explicitly."""
    text = text.lower().replace("þ", "th").replace("æ", "ae").replace("ð", "d")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def interpret(question: str) -> Interpretation | Clarification:
    """Map a question to one table and complete selections, or ask for clarification."""
    text = normalize(question)
    is_cpi = _has_any(text, CPI_WORDS)
    is_population = _has_any(text, POPULATION_WORDS)

    if is_cpi and is_population:
        return Clarification(f"Spyrðu um eitt efni í einu. {SUPPORTED}")
    if is_cpi:
        return _interpret_cpi(text)
    if is_population:
        return _interpret_population(text)
    return Clarification(f"Ég skildi ekki spurninguna. {SUPPORTED}")


def _interpret_cpi(text: str) -> Interpretation | Clarification:
    periods = _months(text)
    if isinstance(periods, Clarification):
        return periods

    if _has_any(text, ("manadarbreyting", "milli manada", "monthly", "month on month")):
        measure = "change_M"
    elif _has_any(text, ("verdbolg", "inflation", "arsbreyting", "annual", "12 manada")):
        measure = "change_A"
    else:
        measure = "index"

    housing = _has_any(text, ("an husnaedis", "excluding housing", "without housing"))
    selections = {"Vísitala": "CPILH" if housing else "CPI", "Liður": measure}
    return _with_periods("cpi", "Mánuður", selections, periods, bool(CHANGE.search(text)), 12)


def _interpret_population(text: str) -> Interpretation | Clarification:
    years = _years(text)
    if len(years) > 2:
        return Clarification("Ég get borið saman tvö ár í einu.")

    compares = bool(CHANGE.search(text)) or len(years) == 2

    if _has_any(text, ("adflutt", "brottflutt", "migration")):
        measure = "3"
    elif _has_any(text, ("faeddir umfram", "natural increase")):
        measure = "4"
    elif _has_any(text, ("fjolgun", "growth", "increase", "grew")) and not compares:
        measure = "1" if _has_any(text, ("%", "hlutfall", "prosent", "percent", "rate")) else "2"
    else:
        # Growth over a span of years is the change in the population itself.
        measure = "0"

    return _with_periods("population", "Ár", {"Eining": measure}, years, compares, 10)


def _with_periods(
    table: str,
    time_code: str,
    selections: dict[str, str],
    periods: list[str],
    compares: bool,
    default_span: int,
) -> Interpretation:
    """Complete selections with one period, or a comparison between two.

    A comparison without periods spans default_span steps up to the latest period;
    one with a single period runs from it to the latest.
    """
    if len(periods) == 2:
        return Interpretation(table, {time_code: periods[1], **selections}, periods[0])
    if compares:
        start = periods[0] if periods else before_latest(default_span)
        return Interpretation(table, {time_code: LATEST, **selections}, start)
    return Interpretation(table, {time_code: periods[0] if periods else LATEST, **selections})


def _months(text: str) -> list[str] | Clarification:
    """Find month periods, pairing each month with the year that follows it."""
    months = sorted(
        (match.start(), number)
        for word, number in MONTHS.items()
        for match in re.finditer(rf"\b{word}\b", text)
    )
    years = [(match.start(), match[1]) for match in re.finditer(r"\b(1[7-9]\d{2}|20\d{2})\b", text)]

    if not months and not years:
        return []
    if not years:
        return Clarification("Tilgreindu ár, til dæmis „verðbólga í september 2026“.")
    if not months:
        return Clarification("Tilgreindu mánuð, til dæmis „verðbólga í september 2026“.")

    if len(months) == 1 and len(years) == 2:
        periods = {f"{year}M{months[0][1]:02d}" for _, year in years}
    elif len(years) <= len(months):
        periods = set()
        for position, number in months:
            following = [year for start, year in years if start > position]
            year = following[0] if following else years[-1][1]
            periods.add(f"{year}M{number:02d}")
    else:
        return Clarification("Tilgreindu mánuð fyrir hvert ár, til dæmis „janúar 2025“.")

    if len(periods) > 2:
        return Clarification("Ég get borið saman tvo mánuði í einu.")
    return sorted(periods)


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _years(text: str) -> list[str]:
    return sorted(set(re.findall(r"\b(1[7-9]\d{2}|20\d{2})\b", text)))
