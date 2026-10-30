"""Interpret Icelandic and English questions as table selections, using explicit rules."""

import re
import unicodedata
from dataclasses import dataclass

from talnaspor.answer import LATEST


@dataclass(frozen=True)
class Interpretation:
    """A supported table and the dimension selections a question asks for."""

    table: str
    selections: dict[str, str]


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
    years = _years(text)
    months = [number for word, number in MONTHS.items() if re.search(rf"\b{word}\b", text)]

    if len(years) > 1 or len(set(months)) > 1:
        return Clarification("Ég get enn aðeins svarað fyrir einn mánuð í einu.")
    if months and not years:
        return Clarification("Tilgreindu ár, til dæmis „verðbólga í september 2026“.")
    if years and not months:
        return Clarification("Tilgreindu mánuð, til dæmis „verðbólga í september 2026“.")

    period = f"{years[0]}M{months[0]:02d}" if years else LATEST

    if _has_any(text, ("manadarbreyting", "milli manada", "monthly", "month on month")):
        measure = "change_M"
    elif _has_any(text, ("verdbolg", "inflation", "arsbreyting", "annual", "12 manada")):
        measure = "change_A"
    else:
        measure = "index"

    housing = _has_any(text, ("an husnaedis", "excluding housing", "without housing"))

    return Interpretation(
        "cpi",
        {"Mánuður": period, "Vísitala": "CPILH" if housing else "CPI", "Liður": measure},
    )


def _interpret_population(text: str) -> Interpretation | Clarification:
    years = _years(text)
    if len(years) > 1:
        return Clarification("Ég get enn aðeins svarað fyrir eitt ár í einu.")

    if _has_any(text, ("adflutt", "brottflutt", "migration")):
        measure = "3"
    elif _has_any(text, ("faeddir umfram", "natural increase")):
        measure = "4"
    elif _has_any(text, ("fjolgun", "growth", "increase", "grew")):
        measure = "1" if _has_any(text, ("%", "hlutfall", "prosent", "percent", "rate")) else "2"
    else:
        measure = "0"

    return Interpretation("population", {"Ár": years[0] if years else LATEST, "Eining": measure})


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _years(text: str) -> list[str]:
    return sorted(set(re.findall(r"\b(1[7-9]\d{2}|20\d{2})\b", text)))
