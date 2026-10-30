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
        ("Hvernig er veðrið?", "skildi ekki"),
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
