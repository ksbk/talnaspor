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

    The message is in Icelandic and message_en in English. recognized is False when the
    question is not about a supported topic at all.
    """

    message: str
    message_en: str
    recognized: bool = True

    def text(self, lang: str) -> str:
        return self.message_en if lang == "en" else self.message


SUPPORTED = (
    "Spyrðu til dæmis um verðbólgu, mannfjölda, atvinnuleysi eða laun, og nefndu "
    "tímabil ef þú vilt."
)
SUPPORTED_EN = (
    "Try asking about inflation, population, unemployment or wages, for example, and "
    "name a period if you like."
)

NOT_FOUND = {
    "is": f"Ég fann ekki svar við þessari spurningu í gögnum Hagstofu Íslands. {SUPPORTED}",
    "en": f"I could not find an answer to this question in Statistics Iceland's data. "
    f"{SUPPORTED_EN}",
}

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
    r"|change|trend|compare|comparison|grown|evolv)"
)

# The start of a span, as in "frá 2015" or "since 2000", which runs to the latest period.
SINCE = re.compile(r"\b(since|(fra|sidan)\s+(\w+\s+)?[12]\d{3})")

# Any four-digit year from 1000 to 2999, so that a year outside a table's range is
# reported as unavailable rather than silently ignored.
YEAR = r"\b([12]\d{3})\b"

NUMBERS = {
    "eitt": 1, "einn": 1, "eins": 1, "tvo": 2, "tveggja": 2, "thrju": 3, "thriggja": 3,
    "fjogur": 4, "fjogurra": 4, "fimm": 5, "sex": 6, "sjo": 7, "atta": 8, "niu": 9,
    "tiu": 10, "tuttugu": 20, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twenty": 20,
    "einu": 1, "tveimur": 2, "thremur": 3, "fjorum": 4, "hundrad": 100, "hundred": 100,
}  # fmt: skip

# A span back from the latest period, as in "síðustu tíu árin" or "the last 5 years".
SPAN = re.compile(
    rf"\b(?:sidustu|last|past)\s+(\d{{1,3}}|{'|'.join(NUMBERS)})\s+"
    r"(ar|arin|arum|years?|manudi|manudina|manuda|months?)\b"
)

# "The last 12 months" describes annual change, not a relative period.
TWELVE_MONTHS = re.compile(r"\b(sidustu|last|past) 12 (manada|manudi|months)\b")
# A whole word: "síðasta ár" (last year) must not match "síðasta áratuginn" (the last decade).
LAST_YEAR = re.compile(
    r"\b(last year|past year|previous year|i fyrra|sidasta ar|sidasta arid|sidastlidid ar)\b"
)

# "The last decade" is the last ten years.
DECADE = re.compile(r"\b((the )?(last|past) decade|sidasta aratug\w*)")
# "The last century" is the last hundred years.
CENTURY = re.compile(r"\b((the )?(last|past) century|sidustu old\w*|sidustu aldar)\b")

# A point in time back from the latest period: "ten years ago", "a decade ago",
# "fyrir tíu árum", "fyrir áratug".
AGO = re.compile(
    rf"\b(?:(\d{{1,3}}|{'|'.join(NUMBERS)}|a|an) (years?|decades?) ago"
    rf"|fyrir (?:(\d{{1,3}}|{'|'.join(NUMBERS)}) )?(ari|arum|aratug|aratugum))\b"
)

# Other relative periods are not supported, and must never be silently ignored.
RELATIVE = re.compile(r"\b(last|past|previous|sidustu|sidasta|sidastlid|ago|fyrir \w+ arum)\b")

# "1. janúar 2026" dates a count, such as the population, to the start of a year: it asks
# about the year, not the month, and its "1" is not a category such as "1 árs".
START_OF_YEAR = re.compile(r"\b(1\.? januar|1(st)? (of )?january|january 1(st)?),? (?=[12]\d{3}\b)")

RELATIVE_MESSAGE = Clarification(
    "Ég get ekki enn svarað um afstæð tímabil eins og þetta. Tilgreindu ár eða mánuð, "
    "til dæmis „2016“ eða „september 2026“.",
    "I cannot yet answer about relative periods like this one. Please name a year or a "
    "month, for example “2016” or “September 2026”.",
)
ONE_PERIOD = Clarification(
    "Tilgreindu eitt tímabil, til dæmis „2016“.", "Please name one period, for example “2016”."
)
# A minus before a number ("-5 years", "mínus 5 ár"); "16-24" and "2020-2025" are ranges.
NEGATIVE = re.compile(r"(?<!\w)(?:-|minus\s+)\d")

INVALID_YEAR = Clarification(
    "Tilgreindu ár með fjórum tölustöfum, til dæmis „2016“.",
    "Please name a year with four digits, for example “2016”.",
)
SERIES_UNSUPPORTED = Clarification(
    "Ég get enn ekki sýnt tímaröð eða graf, aðeins breytingu milli tveggja tímabila. Spyrðu "
    "til dæmis „Hvernig hefur mannfjöldinn breyst síðustu fimm ár?“",
    "I cannot yet show a series or chart, only the change between two periods. Ask, for "
    "example, “How has the population changed over the last five years?”",
)
INVALID_SPAN = Clarification(
    "Tímabilið þarf að vera minnst eitt ár eða einn mánuður, til dæmis „síðustu fimm ár“.",
    "The period must be at least one year or one month, for example “the last five years”.",
)
POPULATION_MONTH = Clarification(
    "Mannfjöldi er talinn 1. janúar ár hvert. Tilgreindu ár, til dæmis „2025“.",
    "Population is counted on 1 January each year. Please name a year, for example “2025”.",
)
# A change asked for without the periods to compare: a span is never assumed.
COMPARE_YEARS = Clarification(
    "Tilgreindu tímabilið sem á að bera saman, til dæmis „frá 2015 til 2025“, „frá 2000“ "
    "eða „síðustu tíu ár“.",
    "Please name the periods to compare, for example “from 2015 to 2025”, “since 2000” or "
    "“over the last ten years”.",
)
COMPARE_MONTHS = Clarification(
    "Tilgreindu tímabilið sem á að bera saman, til dæmis „september 2025 og 2026“ eða "
    "„síðustu tíu árin“.",
    "Please name the periods to compare, for example “September 2025 and 2026” or “over "
    "the last ten years”.",
)
MONTHLY_SPAN = Clarification(
    "Mánaðarbreyting er breyting eins mánaðar. Tilgreindu mánuð, til dæmis „september "
    "2026“, eða spyrðu um verðbólgu síðustu 12 mánuði.",
    "The monthly change is one month's change. Please name a month, for example "
    "“September 2026”, or ask about inflation over the last 12 months.",
)


def states_period(text: str) -> bool:
    """Whether normalized text states a period: a year, a month or a relative period.

    "Now", "latest" and "today" are not stated periods: they mean the latest, as when none
    is given.
    """
    patterns = (SPAN, TWELVE_MONTHS, DECADE, CENTURY, AGO, LAST_YEAR, SINCE, RELATIVE)
    return (
        bool(re.search(YEAR, text))
        or _names_month(text)
        or any(pattern.search(text) for pattern in patterns)
    )


def _names_month(text: str) -> bool:
    return any(re.search(rf"\b{word}\b", text) for word in MONTHS)


def invalid_duration(text: str) -> bool:
    """Whether normalized text states a span or offset of zero or below ("the last 0 years",
    "fyrir 0 árum", "-5 years ago"). Such a period is refused: it is not a missing one, which
    takes the default, and must never fall back to it."""
    if NEGATIVE.search(text):
        return True
    span = SPAN.search(name_spans(text))
    if span and (int(span[1]) if span[1].isdigit() else NUMBERS[span[1]]) == 0:
        return True
    return _years_ago(text)[0] == 0


def invalid_year(text: str) -> bool:
    """Whether normalized text names a year Talnaspor cannot read as a period ("the year 0",
    "árið 500", "á árinu 0", "year 0000", "year +2025"): only four-digit years from 1000 to
    2999 are, and any other would be silently dropped."""
    named = re.findall(r"\b(?:year|ar|arid|ari|arinu)\s+([+-]?\d+)\b", text)
    return any(re.fullmatch(YEAR, year) is None for year in named)


# A request for a whole series or chart, which Talnaspor does not yet draw: two endpoints
# would answer a different question.
SERIES = re.compile(
    r"\b(trends?|time\s+series|series|year by year|each year|every year|ar fra ari"
    r"|throun\w*|timaro\w*|charts?|graphs?|linurit\w*|graf\w*)\b"
)


def relative_period(text: str) -> bool:
    """Whether normalized text states a period relative to the latest ("the last 3 years",
    "í fyrra", "a decade ago", "since 2019"), rather than only named years and months."""
    patterns = (SPAN, TWELVE_MONTHS, DECADE, CENTURY, AGO, LAST_YEAR, SINCE, RELATIVE)
    return any(pattern.search(text) for pattern in patterns)


def name_spans(text: str) -> str:
    """Spell named spans as years: "the last decade" is "last 10 years"."""
    return DECADE.sub("last 10 years", CENTURY.sub("last 100 years", text))


def without_periods(question: str) -> str:
    """The question without the relative periods the rules read ("síðustu öld", "fyrir
    áratug"), so that their words are not mistaken for a topic or restriction."""
    return AGO.sub(" ", CENTURY.sub(" ", normalize(question)))


def _years_ago(text: str) -> tuple[int | None, str]:
    """How many years back a point in time is ("a decade ago": 10), and the rest of the text."""
    match = AGO.search(text)
    if match is None:
        return None, text
    count, unit = match[1] or match[3], match[2] or match[4]
    number = 1 if count in (None, "a", "an") else int(count) if count.isdigit() else NUMBERS[count]
    years = number * (10 if unit.startswith(("decade", "aratug")) else 1)
    return years, text[: match.start()] + text[match.end() :]


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
        return Clarification(
            f"Spyrðu um eitt efni í einu. {SUPPORTED}",
            f"Please ask about one topic at a time. {SUPPORTED_EN}",
        )
    if not is_cpi and not is_population:
        return Clarification(NOT_FOUND["is"], NOT_FOUND["en"], recognized=False)

    if invalid_duration(text):
        return INVALID_SPAN
    if invalid_year(text):
        return INVALID_YEAR
    stated = states_period(text)
    text = name_spans(text)
    if is_cpi:
        # For inflation, "the last 12 months" is the annual change, not a span.
        text = TWELVE_MONTHS.sub("12 manada", text)
    years_ago, text = _years_ago(text)
    last_year = bool(LAST_YEAR.search(text))
    span = SPAN.search(text)
    months_back = None
    if span:
        count = int(span[1]) if span[1].isdigit() else NUMBERS[span[1]]
        in_months = span[2].startswith(("man", "month"))
        months_back = count if in_months else 12 * count
        text = text[: span.start()] + text[span.end() :]
        if re.search(YEAR, text) or _names_month(text):
            # "2025 over the last 5 years" names two periods; one would be dropped.
            return ONE_PERIOD
    if RELATIVE.search(LAST_YEAR.sub("", text)):
        return RELATIVE_MESSAGE
    if is_population and _names_month(START_OF_YEAR.sub("", text)):
        # The population is counted once a year; a month would be silently dropped.
        return POPULATION_MONTH
    used = (
        span is not None
        or years_ago is not None
        or last_year
        or bool(re.search(YEAR, text))
        or _names_month(text)
        or "12 manada" in text
    )
    if stated and not used:
        # A period the question states is used or refused, never replaced by a default.
        return RELATIVE_MESSAGE

    if is_cpi:
        if last_year:
            return Clarification(
                "Verðbólga er birt eftir mánuðum. Tilgreindu mánuð, "
                "til dæmis „verðbólga í desember 2025“.",
                "Inflation is published by month. Please name a month, "
                "for example “inflation in December 2025”.",
            )
        point = None if years_ago is None else before_latest(12 * years_ago)
        return _interpret_cpi(text, months_back, point)
    if months_back is not None and months_back % 12:
        return Clarification(
            "Mannfjöldi er birtur eftir árum. Tilgreindu fjölda ára, til dæmis „síðustu fimm ár“.",
            "Population is published by year. Please give a number of years, for example "
            "“the last five years”.",
        )
    return _interpret_population(
        text,
        last_year,
        None if months_back is None else months_back // 12,
        None if years_ago is None else before_latest(years_ago),
    )


def _interpret_cpi(
    text: str, months_back: int | None = None, point: str | None = None
) -> Interpretation | Clarification:
    periods = _months(text)
    if isinstance(periods, Clarification):
        return periods
    if point:
        if periods:
            return ONE_PERIOD
        periods = [point]

    if _has_any(text, ("manadarbreyting", "milli manada", "monthly", "month on month")):
        if "12 manada" in text:
            return MONTHLY_SPAN
        measure = "change_M"
    elif _has_any(
        text, ("verdbolg", "inflation", "arsbreyting", "annual", "12 manada", "verdlag", "haekk")
    ):
        measure = "change_A"
    else:
        measure = "index"

    spans = _spans(text, periods) or (months_back is not None and not periods)
    if CHANGE.search(text) and not spans and measure == "index":
        return Clarification(
            "Viltu mánaðarbreytingu eða ársbreytingu? Til dæmis "
            "„mánaðarbreyting vísitölu neysluverðs í september 2026“.",
            "Do you mean the monthly or the annual change? For example "
            "“monthly change in the CPI in September 2026”.",
        )

    housing = _has_any(text, ("an husnaedis", "excluding housing", "without housing"))
    selections = {"Vísitala": "CPILH" if housing else "CPI", "Liður": measure}
    return _with_periods("cpi", "Mánuður", selections, periods, spans, months_back, COMPARE_MONTHS)


def _interpret_population(
    text: str, last_year: bool, years_back: int | None = None, point: str | None = None
) -> Interpretation | Clarification:
    years = _years(text)
    grows = _has_any(text, ("fjolg", "growth", "increase", "grew")) or bool(CHANGE.search(text))
    components = _has_any(text, ("adflutt", "brottflutt", "migration", "faeddir umfram", "natural"))
    if point:
        if years:
            return ONE_PERIOD
        years = [point]
    elif last_year and not years:
        if grows and not components:
            # Change over the last year is between the two latest 1 January figures, shown
            # as both figures and the change, as for longer spans.
            years_back = 1
        else:
            # The latest population figure is for 1 January of the current year.
            years = [before_latest(1)]
    if len(years) > 2:
        return Clarification(
            "Ég get borið saman tvö ár í einu.", "I can compare two years at a time."
        )

    spans = _spans(text, years) or (years_back is not None and not years)

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

    return _with_periods(
        "population",
        "Ár",
        {"Eining": measure},
        years,
        spans,
        years_back,
        COMPARE_YEARS,
    )


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
    span: int | None,
    unstated: Clarification,
) -> Interpretation | Clarification:
    """Complete selections with one period, or a comparison between two.

    A comparison without periods spans the stated number of steps up to the latest period;
    one with a single period runs from it to the latest. A comparison with neither is not
    given a span: the question is asked again (unstated).
    """
    if len(periods) == 2:
        return Interpretation(table, {time_code: periods[1], **selections}, periods[0])
    if spans:
        if periods:
            start = periods[0]
        elif span is not None:
            start = before_latest(span)
        else:
            return unstated
        return Interpretation(table, {time_code: LATEST, **selections}, start)
    return Interpretation(table, {time_code: periods[0] if periods else LATEST, **selections})


# Month names as plain words; the English "may" pattern needs a following year.
MONTH_WORDS = frozenset(word for word in MONTHS if word.isalpha())


def month_periods(text: str) -> list[str] | Clarification:
    """Month periods (2026M09) named in normalized text, or what is missing to name one."""
    return _months(text)


def _months(text: str) -> list[str] | Clarification:
    """Find month periods, pairing each month with the year that follows it."""
    months = sorted(
        (match.start(), number)
        for word, number in MONTHS.items()
        for match in re.finditer(rf"\b{word}\b", text)
    )
    years = [(match.start(), match[1]) for match in re.finditer(YEAR, text)]

    if not months and not years:
        return []
    if not years:
        return Clarification(
            "Tilgreindu ár, til dæmis „verðbólga í september 2026“.",
            "Please name a year, for example “inflation in September 2026”.",
        )
    if not months:
        return Clarification(
            "Tilgreindu mánuð, til dæmis „verðbólga í september 2026“.",
            "Please name a month, for example “inflation in September 2026”.",
        )

    if len(months) == 1 and len(years) == 2:
        periods = {f"{year}M{months[0][1]:02d}" for _, year in years}
    elif len(years) <= len(months):
        periods = set()
        for position, number in months:
            following = [year for start, year in years if start > position]
            year = following[0] if following else years[-1][1]
            periods.add(f"{year}M{number:02d}")
    else:
        return Clarification(
            "Tilgreindu mánuð fyrir hvert ár, til dæmis „janúar 2025“.",
            "Please name a month for each year, for example “January 2025”.",
        )

    if len(periods) > 2:
        return Clarification(
            "Ég get borið saman tvo mánuði í einu.", "I can compare two months at a time."
        )
    return sorted(periods)


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _years(text: str) -> list[str]:
    return sorted(set(re.findall(YEAR, text)))


# Word stems the curated CPI and population answers account for: their topics, measures,
# periods and comparisons. A question with any other content word, such as a place
# ("Reykjavík"), a sub-index ("matvörum"), a country ("Norway") or another measure
# ("meðalaldur"), asks about something those national headline figures do not answer.
CURATED_STEMS = (
    # Consumer price index and its measures.
    "verdbolg", "inflation", "neysluverd", "consumer", "price", "cpi", "verdlag", "visital",
    "visitol", "index", "manadarbreyt", "arsbreyt", "monthly", "month", "annual", "haekk",
    "laekk", "husnaed", "housing", "exclud", "without", "milli",
    # Population and its measures.
    "mannfjold", "ibua", "ibui", "ibuum", "populat", "inhabit", "people", "bua", "bjugg",
    "bjo", "fjolg", "fjold", "growth", "increas", "grew", "hlutfall", "prosent", "percent",
    "rate", "adflutt", "brottflutt", "migrat", "immigrat", "net", "faedd", "umfram", "dana",
    "natural", "landsins", "landinu", "thjodin", "thjodar", "number", "size", "big", "stor",
    # Periods, spans and comparisons.
    "breyst", "breytt", "breyting", "throun", "throa", "thrad", "aukist", "vaxid", "samanburd",
    "chang", "trend", "compar", "grown", "since", "fra", "til", "sidan", "nuna", "now",
    "current", "today", "dag", "latest", "nyjust", "arin", "arid", "arum", "year", "manud",
    "manad", "sidust", "sidast", "last", "past", "previous", "fyrra", "ago", "between", "and",
    "than", "faster", "slower", "rise", "rose", "fell", "fall", "hvenaer", "decade", "aratug",
    "centur", "evolv",
)  # fmt: skip


def curated_terms_cover(words: set[str]) -> bool:
    """Whether every content word of a question is one the curated answers account for."""
    known = (*CURATED_STEMS, *MONTH_WORDS, *NUMBERS)
    # "ár" and "ára" (year, years) are too short to be prefixes; "may" is a month.
    return all(word in {"ar", "ara", "may"} or word.startswith(known) for word in words)


# Follow-ups that narrow the previous question, in a few fixed forms: a sex, an age group
# or a year ("What about women?", "En hjá körlum?", "And in 2020?"), or a place
# ("En í Reykjavík?", "And in Akureyri?"). Anything else is a question of its own.
FOLLOW_UP = re.compile(
    r"^(?:what about|how about|and for|and|hvad med|hvad um|en hja|en|og hja|og) (?P<rest>.+)$"
)
PLACE_FOLLOW_UP = re.compile(
    r"^(?:what about|how about|and|hvad med|en|og) (?P<rest>(?:in|i|a) (?![12]\d{3}\b)\w+(?: \w+)?)$"
)
SEX_WORDS = frozenset(
    {
        "women", "woman", "female", "females", "girls", "men", "man", "male", "males", "boys",
        "konur", "kvenna", "konum", "stulkur", "karlar", "karla", "korlum", "karlmenn",
        "karlmanna", "drengir",
    }
)  # fmt: skip
AGE_RANGE = re.compile(r"^\d{1,3}-\d{1,3}$")
# Words that may accompany a restriction: "ages 16-24", "16-24 ára", "in 2020", "árið 2020".
FILLER_WORDS = frozenset({"aged", "ages", "age", "ara", "years", "old", "in", "i", "arid", "year"})


def _words(text: str) -> list[str]:
    return re.sub(r"[^\w\s-]", " ", text).split()


def _kind(word: str) -> str | None:
    """Which restriction a normalized word states: a sex, a year or an age group."""
    if word in SEX_WORDS:
        return "sex"
    if re.fullmatch(YEAR, word):
        return "year"
    if AGE_RANGE.match(word):
        return "age"
    return None


def follow_up(question: str) -> str | None:
    """The restriction a follow-up question adds, in the user's own words, or None.

    "What about women?" gives "women"; "En í Reykjavík?" gives "í Reykjavík".
    """
    original = _words(question)
    text = " ".join(_words(normalize(question)))
    place = PLACE_FOLLOW_UP.match(text)
    match = place or FOLLOW_UP.match(text)
    if match is None:
        return None
    rest = match["rest"].split()
    if not place:
        kinds = [_kind(word) for word in rest]
        if not any(kinds) or any(
            kind is None and word not in FILLER_WORDS
            for kind, word in zip(kinds, rest, strict=True)
        ):
            return None
    return " ".join(original[-len(rest) :])


def narrow(previous: str, restriction: str) -> str:
    """The previous question with a follow-up's restriction.

    A sex, year or age group the previous question already states is replaced ("women"
    becomes "men"); a restriction it does not state is added after it.
    """
    words = previous.strip().rstrip("?").split()
    kinds = [_kind(normalize(new)) for new in restriction.split()]
    added = False
    for new, kind in zip(restriction.split(), kinds, strict=True):
        if kind is None:
            continue
        stated = [
            index
            for index, word in enumerate(words)
            if _kind(" ".join(_words(normalize(word)))) == kind
        ]
        if len(stated) == 1:
            words[stated[0]] = new
        else:
            added = True
    if any(kinds) and not added:
        return " ".join(words) + "?"
    return f"{' '.join(words)}, {restriction}?"
