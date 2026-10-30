import pytest

from talnaspor.catalog import _match, search


@pytest.mark.parametrize(
    ("question", "title"),
    [
        ("Hversu margir eru atvinnulausir á Íslandi?", "Atvinnulausir"),
        ("What is the unemployment rate?", "atvinnuleysi"),
        ("Hver er munurinn á launum karla og kvenna?", "Óleiðréttur launamunur kynjanna"),
        ("Hver er landsframleiðslan?", "Landsframleiðsla"),
        ("Hvað eru margir bílar á Íslandi?", "ökutæki"),
    ],
)
def test_finds_relevant_tables(question: str, title: str) -> None:
    hits = search(question)

    assert any(title in hit.title for hit in hits[:3])


@pytest.mark.parametrize("question", ["Hvernig er veðrið?", "Hvað kostar bensín?", "blah blah"])
def test_finds_nothing_for_unrelated_questions(question: str) -> None:
    assert search(question) == []


def test_links_to_table_pages() -> None:
    hits = search("Vísitala neysluverðs og breytingar grunnur 1988")
    cpi = next(hit for hit in hits if hit.api_url.endswith("/VIS01000.px"))

    assert cpi.page_url == (
        "https://px.hagstofa.is/pxis/pxweb/is/Efnahagur/"
        "Efnahagur__visitolur__1_vnv__1_vnv/VIS01000.px"
    )
    assert cpi.api_url == (
        "https://px.hagstofa.is/pxis/api/v1/is/Efnahagur/visitolur/1_vnv/1_vnv/VIS01000.px"
    )


def test_prefers_current_tables_over_discontinued_ones() -> None:
    hits = search("Hversu margir eru atvinnulausir á Íslandi?")

    assert (hits[0].updated or "") >= "2022"


@pytest.mark.parametrize(
    ("term", "word", "quality"),
    [
        ("laun", "launa", 1.0),
        ("ferdamenn", "ferdamanna", 0.6),
        ("kosning", "kosningathatttaka", 0.6),
        ("atvinnulausir", "atvinnuvegir", 0.0),
        ("bil", "bilar", 0.0),
    ],
)
def test_matches_inflected_word_forms(term: str, word: str, quality: float) -> None:
    assert _match(term, word) == quality


def test_does_not_match_life_expectancy_for_where_people_live() -> None:
    hits = search("How many women live in Iceland?")

    assert not any("expectancy" in (hit.title_en or "").lower() for hit in hits)
