import pytest

from talnaspor.answer import LATEST
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
        ("Verðbólga í janúar og febrúar 2026", "einn mánuð"),
        ("Mannfjöldi 2015 og 2025", "eitt ár"),
    ],
)
def test_asks_for_clarification(question: str, message: str) -> None:
    result = interpret(question)

    assert isinstance(result, Clarification)
    assert message in result.message
