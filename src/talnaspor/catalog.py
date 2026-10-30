"""Find Statistics Iceland tables that match a question, using the crawled table catalog."""

import math
import re
from collections import Counter, defaultdict
from functools import cache
from pathlib import Path

from pydantic import BaseModel

from talnaspor.interpret import normalize

CATALOG = Path(__file__).parent / "data" / "catalog.json"
PAGE_BASE = "https://px.hagstofa.is/pxis/pxweb/is/"
API_BASE = "https://px.hagstofa.is/pxis/api/v1/is/"

# Question words and other terms that say nothing about which table is meant.
STOPWORDS = frozenset(
    [
        "hver",
        "hvert",
        "hvar",
        "hvad",
        "hvada",
        "hvernig",
        "hve",
        "hversu",
        "hvort",
        "hvenaer",
        "er",
        "var",
        "eru",
        "voru",
        "vera",
        "verid",
        "hefur",
        "hafa",
        "hafdi",
        "a",
        "i",
        "og",
        "um",
        "fra",
        "til",
        "ad",
        "af",
        "med",
        "vid",
        "sem",
        "thad",
        "thetta",
        "thessi",
        "eda",
        "en",
        "ekki",
        "margir",
        "margar",
        "morg",
        "mikid",
        "mikill",
        "mikil",
        "island",
        "islandi",
        "islands",
        "islenskur",
        "nu",
        "nuna",
        "arid",
        "ari",
        "ar",
        "arin",
        "manudi",
        "manudur",
        "sidan",
        "breyst",
        "breyttist",
        "thro",
        "throast",
        "throun",
        "what",
        "which",
        "how",
        "many",
        "much",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "has",
        "have",
        "had",
        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "from",
        "by",
        "and",
        "or",
        "with",
        "this",
        "that",
        "there",
        "iceland",
        "icelandic",
        "changed",
        "change",
        "number",
        "do",
        "does",
        "did",
        "over",
        "since",
        "per",
        "between",
        "fyrra",
        "fyrri",
        "sidasta",
        "sidustu",
        "last",
        "year",
        "years",
        "fjoldi",
        "kostar",
        "kosta",
        "kostadi",
        "cost",
        "costs",
        "price",
    ]
)

TOKEN = re.compile(r"[a-z0-9]+")


class CatalogTable(BaseModel):
    """One table in the crawled catalog."""

    path: str
    title: str
    folders: list[str]
    title_en: str | None = None
    folders_en: list[str] = []
    updated: str | None = None


class Catalog(BaseModel):
    crawled: str
    tables: list[CatalogTable]


class TableHit(BaseModel):
    """A catalog table that may hold the answer to a question."""

    title: str
    title_en: str | None
    folders: list[str]
    updated: str | None
    page_url: str
    api_url: str
    score: float


# Question wording that cannot be matched to table titles by spelling alone, mapped to
# the words Statistics Iceland uses in its titles.
RELATED_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("atvinnulaus", ("atvinnuleysi",)),
    ("unemploy", ("atvinnuleysi",)),
    ("karla og kvenna", ("launamunur", "kynjanna")),
    ("kynjanna", ("launamunur",)),
    ("gender pay", ("launamunur", "kynjanna")),
    ("medallaun", ("laun", "regluleg")),
    ("average wage", ("laun", "regluleg")),
    ("bilar", ("okutaeki", "bifreidar")),
    ("bila", ("okutaeki", "bifreidar")),
    ("cars", ("okutaeki", "bifreidar")),
    ("gdp", ("landsframleidsla",)),
    ("fiskafl", ("afli",)),
    ("fish catch", ("afli",)),
)

# A table not updated since this year is probably a discontinued series.
CURRENT_SINCE = "2022"


def search(question: str, limit: int = 5, minimum_score: float = 3.0) -> list[TableHit]:
    """Rank catalog tables by how well their titles and folders match the question."""
    tables, documents, idf = _index()
    text = normalize(question)
    terms = {t for t in TOKEN.findall(text) if t not in STOPWORDS and len(t) > 2}
    for phrase, related in RELATED_TERMS:
        if phrase in text:
            terms.update(related)
    if not terms:
        return []

    scores: defaultdict[int, float] = defaultdict(float)
    for term in terms:
        matches = {word: quality for word in idf if (quality := _match(term, word))}
        if not matches:
            continue
        for index, words in enumerate(documents):
            best = max(
                (
                    idf[word] * weight * matches[word]
                    for word, weight in words.items()
                    if word in matches
                ),
                default=0.0,
            )
            if best:
                scores[index] += best

    for index in scores:
        if (tables[index].updated or "") < CURRENT_SINCE:
            scores[index] *= 0.85

    ranked = sorted(
        (index for index, score in scores.items() if score >= minimum_score),
        key=lambda index: (scores[index], tables[index].updated or ""),
        reverse=True,
    )
    return [_hit(tables[index], scores[index]) for index in ranked[:limit]]


def _match(term: str, word: str) -> float:
    """Score how well two word forms match, allowing for Icelandic inflection.

    Forms of one word ("laun", "launa") are a full match. A shared stem ("ferdamenn",
    "ferdamanna") or the start of a compound ("kosning", "kosningathatttaka") is a weaker
    one; anything else does not match.
    """
    shorter = min(len(term), len(word))
    common = 0
    for left, right in zip(term, word, strict=False):
        if left != right:
            break
        common += 1
    if common < 4:
        return 0.0
    if common == shorter and shorter >= 0.6 * max(len(term), len(word)):
        return 1.0
    return 0.6 if common >= 0.6 * shorter else 0.0


@cache
def _index() -> tuple[list[CatalogTable], list[dict[str, float]], dict[str, float]]:
    tables = Catalog.model_validate_json(CATALOG.read_text(encoding="utf-8")).tables

    documents: list[dict[str, float]] = []
    for table in tables:
        words: dict[str, float] = {}
        # Titles say more about a table than the folders it is filed under.
        for text, weight in (
            (table.title, 1.0),
            (table.title_en or "", 1.0),
            (" ".join(table.folders), 0.5),
            (" ".join(table.folders_en), 0.5),
        ):
            for word in TOKEN.findall(normalize(text)):
                if word not in STOPWORDS and len(word) > 2:
                    words[word] = max(words.get(word, 0.0), weight)
        documents.append(words)

    frequency = Counter(word for words in documents for word in words)
    idf = {word: math.log(len(documents) / count) for word, count in frequency.items()}
    return tables, documents, idf


def _hit(table: CatalogTable, score: float) -> TableHit:
    *folders, file = table.path.split("/")
    return TableHit(
        title=table.title,
        title_en=table.title_en,
        folders=table.folders,
        updated=table.updated,
        page_url=f"{PAGE_BASE}{folders[0]}/{'__'.join(folders)}/{file}",
        api_url=API_BASE + table.path,
        score=round(score, 2),
    )
