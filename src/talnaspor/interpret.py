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
    """Why a question cannot be answered as asked, and what the user can ask instead.

    recognized is False when the question is not about a supported topic at all.
    """

    message: str
    recognized: bool = True


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

CPI_WORDS = (
    "verdbolg",
    "inflation",
    "neysluverd",
    "consumer price",
    "cpi",
    "verdlag",
    "price level",
)
POPULATION_WORDS = (
    "mannfjold",
    "ibua",
    "population",
    "inhabitants",
    "people live",
    "bua a islandi",
    "bua margir",
    "margir bua",
    "bjuggu",
    "bjo a islandi",
    "ibuum",
    "ibui",
    "adfluttir umfram",
    "net migration",
    "faeddir umfram",
    "natural increase",
)


# Word starts only, so that "arsbreyting" (annual change) is not a change-over-time question.
CHANGE = re.compile(
    r"\b(breyst|breyttist|breyting|thro(un|a)|aukist|haekkad|laekkad|vaxid|samanburd"
    r"|change|trend|compare|comparison|grown)"
)

# The start of a span, as in "frá 2015" or "since 2000", which runs to the latest period.
SINCE = re.compile(r"\b(since|(fra|sidan)\s+(\w+\s+)?(1[7-9]|20)\d{2})")

# "The last 12 months" describes annual change, not a relative period.
TWELVE_MONTHS = re.compile(r"\b(sidustu|last|past) 12 (manada|manudi|months)\b")
LAST_YEAR = re.compile(r"\b(last year|previous year|i fyrra|sidasta ar|sidastlidid ar)")

# Other relative periods are not supported, and must never be silently ignored.
RELATIVE = re.compile(r"\b(last|past|previous|sidustu|sidasta|sidastlid|ago|fyrir \w+ arum)\b")


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
    if not is_cpi and not is_population:
        return Clarification(f"Ég skildi ekki spurninguna. {SUPPORTED}", recognized=False)

    text = TWELVE_MONTHS.sub("12 manada", text)
    last_year = bool(LAST_YEAR.search(text))
    if RELATIVE.search(LAST_YEAR.sub("", text)):
        return Clarification(
            "Ég get ekki enn svarað um afstæð tímabil eins og „síðustu fimm ár“. "
            "Tilgreindu tímabil, til dæmis „september 2026“ eða „2020 og 2025“."
        )

    if is_cpi:
        if last_year:
            return Clarification(
                "Verðbólga er birt eftir mánuðum. Tilgreindu mánuð, "
                "til dæmis „verðbólga í desember 2025“."
            )
        return _interpret_cpi(text)
    return _interpret_population(text, last_year)


def _interpret_cpi(text: str) -> Interpretation | Clarification:
    periods = _months(text)
    if isinstance(periods, Clarification):
        return periods

    if _has_any(text, ("manadarbreyting", "milli manada", "monthly", "month on month")):
        measure = "change_M"
    elif _has_any(
        text, ("verdbolg", "inflation", "arsbreyting", "annual", "12 manada", "verdlag", "haekk")
    ):
        measure = "change_A"
    else:
        measure = "index"

    spans = _spans(text, periods)
    if CHANGE.search(text) and not spans and measure == "index":
        return Clarification(
            "Viltu mánaðarbreytingu eða ársbreytingu? Til dæmis "
            "„mánaðarbreyting vísitölu neysluverðs í september 2026“."
        )

    housing = _has_any(text, ("an husnaedis", "excluding housing", "without housing"))
    selections = {"Vísitala": "CPILH" if housing else "CPI", "Liður": measure}
    return _with_periods("cpi", "Mánuður", selections, periods, spans, 12)


def _interpret_population(text: str, last_year: bool) -> Interpretation | Clarification:
    years = _years(text)
    if last_year and not years:
        # The latest population figure is for 1 January of the current year.
        years = [before_latest(1)]
    if len(years) > 2:
        return Clarification("Ég get borið saman tvö ár í einu.")

    spans = _spans(text, years)
    grows = _has_any(text, ("fjolg", "growth", "increase", "grew")) or bool(CHANGE.search(text))

    if _has_any(text, ("adflutt", "brottflutt", "migration")):
        measure = "3"
    elif _has_any(text, ("faeddir umfram", "natural increase")):
        measure = "4"
    elif grows and not spans:
        # Growth or change within one year is that year's increase.
        measure = "1" if _has_any(text, ("%", "hlutfall", "prosent", "percent", "rate")) else "2"
    else:
        # Growth over a span of years is the change in the population itself.
        measure = "0"

    return _with_periods("population", "Ár", {"Eining": measure}, years, spans, 10)


def _spans(text: str, periods: list[str]) -> bool:
    """Whether a question asks about change across a span rather than within one period.

    Two periods, "since"/"frá" a period, or a change word with no period all span time;
    a change word with one period ("the change in September 2026") does not.
    """
    if len(periods) == 2 or SINCE.search(text):
        return True
    return bool(CHANGE.search(text)) and not periods


def _with_periods(
    table: str,
    time_code: str,
    selections: dict[str, str],
    periods: list[str],
    spans: bool,
    default_span: int,
) -> Interpretation:
    """Complete selections with one period, or a comparison between two.

    A comparison without periods spans default_span steps up to the latest period;
    one with a single period runs from it to the latest.
    """
    if len(periods) == 2:
        return Interpretation(table, {time_code: periods[1], **selections}, periods[0])
    if spans:
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
