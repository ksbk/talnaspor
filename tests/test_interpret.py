import pytest

from talnaspor.answer import LATEST, before_latest
from talnaspor.interpret import Clarification, Interpretation, interpret, normalize


def test_normalizes_icelandic_letters() -> None:
    assert normalize("Þjóðin ÆTTI að vita verðbólguna") == "thjodin aetti ad vita verdbolguna"


@pytest.mark.parametrize(
    ("question", "selections"),
    [
        (
            "Hver var verðbólgan í september 2026?",
            {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"},
        ),
        ("Hver er verðbólgan núna?", {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"}),
        (
            "Hver er vísitala neysluverðs?",
            {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "index"},
        ),
        (
            "Mánaðarbreyting vísitölu neysluverðs í janúar 2025",
            {"Mánuður": "2025M01", "Vísitala": "CPI", "Liður": "change_M"},
        ),
        (
            "Verðbólga án húsnæðis í mars 2026",
            {"Mánuður": "2026M03", "Vísitala": "CPILH", "Liður": "change_A"},
        ),
        (
            "What was inflation in May 2025?",
            {"Mánuður": "2025M05", "Vísitala": "CPI", "Liður": "change_A"},
        ),
        (
            "May I ask what inflation is now?",
            {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"},
        ),
    ],
)
def test_interprets_cpi_questions(question: str, selections: dict[str, str]) -> None:
    assert interpret(question) == Interpretation("cpi", selections)


@pytest.mark.parametrize(
    ("question", "selections"),
    [
        ("Hver var mannfjöldinn árið 2020?", {"Ár": "2020", "Eining": "0"}),
        ("Hvað búa margir á Íslandi?", {"Ár": LATEST, "Eining": "0"}),
        ("What is the population of Iceland?", {"Ár": LATEST, "Eining": "0"}),
        ("Hver var fjölgun íbúa árið 2024?", {"Ár": "2024", "Eining": "2"}),
        ("Population growth rate in 2024", {"Ár": "2024", "Eining": "1"}),
        ("Hve margir aðfluttir umfram brottflutta 2023?", {"Ár": "2023", "Eining": "3"}),
        ("Fæddir umfram dána á Íslandi 2023, hve margir íbúar?", {"Ár": "2023", "Eining": "4"}),
    ],
)
def test_interprets_population_questions(question: str, selections: dict[str, str]) -> None:
    assert interpret(question) == Interpretation("population", selections)


@pytest.mark.parametrize(
    ("question", "message"),
    [
        ("Hvernig er veðrið?", "fann ekki svar"),
        ("Verðbólga og mannfjöldi árið 2024", "eitt efni"),
        ("Verðbólga árið 2024", "Tilgreindu mánuð"),
        ("Verðbólga í september", "Tilgreindu ár"),
        ("Verðbólga í janúar, febrúar og mars 2026", "tvo mánuði"),
        ("Mannfjöldi 2005, 2015 og 2025", "tvö ár"),
        ("Verðbólga í janúar 2024, 2025 og 2026", "hvert ár"),
    ],
)
def test_asks_for_clarification(question: str, message: str) -> None:
    result = interpret(question)

    assert isinstance(result, Clarification)
    assert message in result.message


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "How has Iceland's population changed?",
            Interpretation("population", {"Ár": LATEST, "Eining": "0"}, before_latest(10)),
        ),
        (
            "Hvernig hefur mannfjöldinn breyst frá 2015 til 2025?",
            Interpretation("population", {"Ár": "2025", "Eining": "0"}, "2015"),
        ),
        (
            "Mannfjöldi 2015 og 2025",
            Interpretation("population", {"Ár": "2025", "Eining": "0"}, "2015"),
        ),
        (
            "Population growth since 2000",
            Interpretation("population", {"Ár": LATEST, "Eining": "0"}, "2000"),
        ),
        (
            "Hvernig hefur verðbólgan þróast?",
            Interpretation(
                "cpi",
                {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"},
                before_latest(12),
            ),
        ),
        (
            "Breyting vísitölu neysluverðs frá janúar 2025 til september 2026",
            Interpretation(
                "cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "index"}, "2025M01"
            ),
        ),
        (
            "Verðbólga í janúar og febrúar 2026",
            Interpretation(
                "cpi", {"Mánuður": "2026M02", "Vísitala": "CPI", "Liður": "change_A"}, "2026M01"
            ),
        ),
        (
            "Verðbólga í september 2025 og 2026",
            Interpretation(
                "cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"}, "2025M09"
            ),
        ),
    ],
)
def test_interprets_change_over_time(question: str, expected: Interpretation) -> None:
    assert interpret(question) == expected


def test_annual_change_is_not_a_comparison() -> None:
    result = interpret("Ársbreyting vísitölu neysluverðs í september 2026")

    assert isinstance(result, Interpretation)
    assert result.compare_from is None


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "What was the monthly change in the CPI in September 2026?",
            Interpretation("cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_M"}),
        ),
        (
            "What was the annual change in CPI in September 2026?",
            Interpretation("cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"}),
        ),
        (
            "Population change in 2024",
            Interpretation("population", {"Ár": "2024", "Eining": "2"}),
        ),
        (
            "Verðbólga frá janúar 2025",
            Interpretation(
                "cpi", {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"}, "2025M01"
            ),
        ),
    ],
)
def test_change_within_one_period_is_not_a_comparison(
    question: str, expected: Interpretation
) -> None:
    assert interpret(question) == expected


def test_asks_which_change_for_cpi_in_one_month() -> None:
    result = interpret("Hver var breytingin á vísitölu neysluverðs í september 2026?")

    assert isinstance(result, Clarification)
    assert "mánaðarbreytingu eða ársbreytingu" in result.message


@pytest.mark.parametrize(
    ("question", "selections"),
    [
        ("Hvað fjölgaði íbúum mikið árið 2024?", {"Ár": "2024", "Eining": "2"}),
        ("Hver var fjöldi íbúa á Íslandi 2020?", {"Ár": "2020", "Eining": "0"}),
    ],
)
def test_recognizes_inflected_population_words(question: str, selections: dict[str, str]) -> None:
    assert interpret(question) == Interpretation("population", selections)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "Hver var mannfjöldinn í fyrra?",
            Interpretation("population", {"Ár": before_latest(1), "Eining": "0"}),
        ),
        (
            "Hvernig breyttist mannfjöldinn í fyrra?",
            Interpretation("population", {"Ár": before_latest(1), "Eining": "2"}),
        ),
        (
            "Inflation over the last 12 months",
            Interpretation("cpi", {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"}),
        ),
        (
            "Hvað er verðlag að hækka mikið?",
            Interpretation("cpi", {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"}),
        ),
        (
            "Hve margir bjuggu á Íslandi árið 1990?",
            Interpretation("population", {"Ár": "1990", "Eining": "0"}),
        ),
    ],
)
def test_interprets_last_year_and_wording(question: str, expected: Interpretation) -> None:
    assert interpret(question) == expected


@pytest.mark.parametrize(
    ("question", "message"),
    [
        ("What was inflation last year?", "Tilgreindu mánuð"),
        ("Hver var mannfjöldinn fyrir tíu árum?", "afstæð tímabil"),
        ("What was the population 10 years ago?", "afstæð tímabil"),
        ("Hver var verðbólgan í síðasta mánuði?", "afstæð tímabil"),
    ],
)
def test_never_ignores_relative_periods(question: str, message: str) -> None:
    result = interpret(question)

    assert isinstance(result, Clarification)
    assert message in result.message


@pytest.mark.parametrize(
    "question",
    [
        "Hvernig er veðrið?",
        "Verðbólga og mannfjöldi árið 2024",
        "Verðbólga árið 2024",
        "Verðbólga í september",
        "Verðbólga í janúar, febrúar og mars 2026",
        "Mannfjöldi 2005, 2015 og 2025",
        "Verðbólga í janúar 2024, 2025 og 2026",
        "Hver var breytingin á vísitölu neysluverðs í september 2026?",
        "What was inflation last year?",
        "Hver var mannfjöldinn fyrir tíu árum?",
        "Population over the last 3 months",
    ],
)
def test_every_clarification_has_english_wording(question: str) -> None:
    result = interpret(question)

    assert isinstance(result, Clarification)
    assert result.text("is") == result.message
    assert result.text("en") == result.message_en
    assert result.message_en and result.message_en != result.message
    assert not set("áðéíóúýþæö") & set(result.message_en.lower())


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "Hvernig hefur verðbólgan þróast síðustu tíu árin?",
            Interpretation(
                "cpi",
                {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"},
                before_latest(120),
            ),
        ),
        (
            "Inflation over the past 6 months",
            Interpretation(
                "cpi",
                {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"},
                before_latest(6),
            ),
        ),
        (
            "How has the population changed over the last five years?",
            Interpretation("population", {"Ár": LATEST, "Eining": "0"}, before_latest(5)),
        ),
        (
            "Mannfjöldi síðustu 20 ár",
            Interpretation("population", {"Ár": LATEST, "Eining": "0"}, before_latest(20)),
        ),
    ],
)
def test_compares_over_relative_spans(question: str, expected: Interpretation) -> None:
    assert interpret(question) == expected


def test_keeps_years_outside_the_usual_range() -> None:
    # Ignoring such a year would answer for the latest period instead.
    assert interpret("What was the population in 1650?") == Interpretation(
        "population", {"Ár": "1650", "Eining": "0"}
    )
