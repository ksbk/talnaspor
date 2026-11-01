"""Unsupported temporal requests must not become a different statistical answer.

The cases come from an independent repair by Codex (branch codex/repair-semantic-substitutions,
119b7ac). They check outcomes, not wording: each gets a clarification, with no answer, no
request to Statistics Iceland and no catalog planning.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from talnaspor.answer import before_latest
from talnaspor.app import app
from talnaspor.interpret import Interpretation, interpret, invalid_duration
from talnaspor.planner import Span


@pytest.mark.parametrize(
    ("question", "lang"),
    [
        ("Population over the last 00 years", "en"),
        ("Mannfjöldi síðustu 00 ár", "is"),
        ("Population over the last 000 years", "en"),
        ("Verðbólga síðustu 000 mánuði", "is"),
        ("Unemployment over the last 00 years", "en"),
        ("Atvinnuleysi síðustu 00 ár", "is"),
        ("Population in 2025 over the last 5 years", "en"),
        ("Mannfjöldi árið 2025 síðustu fimm ár", "is"),
        ("Population in 2025 over the last decade", "en"),
        ("Mannfjöldi árið 2025 síðasta áratug", "is"),
        ("Unemployment in 2025 over the last 5 years", "en"),
        ("Atvinnuleysi árið 2025 síðustu fimm ár", "is"),
        ("Population in year 0", "en"),
        ("Mannfjöldi árið 0", "is"),
        ("Population in year 0000", "en"),
        ("Mannfjöldi á árinu 0", "is"),
        ("Unemployment in year 0", "en"),
        ("Atvinnuleysi árið 0", "is"),
        ("Show the population trend over the last 5 years", "en"),
        ("Sýndu þróun mannfjölda síðustu fimm ár", "is"),
        ("Show a population time series for 2020 and 2025", "en"),
        ("Sýndu tímaröð mannfjölda frá 2020", "is"),
        ("Show the unemployment trend over the last 5 years", "en"),
        ("Sýndu þróun atvinnuleysis síðustu fimm ár", "is"),
    ],
)
def test_clarifies_without_retrieval_or_planner(question: str, lang: str) -> None:
    # Through /ask, so that catalog topics cannot bypass the guard.
    with (
        patch("talnaspor.pxweb._send") as send,
        patch("talnaspor.app.plan_answer") as plan,
        patch("talnaspor.app.plan_comparison") as compare,
    ):
        body = TestClient(app).post("/ask", json={"question": question, "lang": lang}).json()

    assert body["status"] == "clarification"
    assert body["answer"] is None and body["comparison"] is None
    send.assert_not_called()
    plan.assert_not_called()
    compare.assert_not_called()


@pytest.mark.parametrize("count", ["0", "00", "000"])
def test_zero_duration_is_numeric(count: str) -> None:
    assert invalid_duration(f"last {count} years")
    assert invalid_duration(f"sidustu {count} manudi")


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Population", Interpretation("population", {"Ár": "latest", "Eining": "0"})),
        ("Mannfjöldi árið 2025", Interpretation("population", {"Ár": "2025", "Eining": "0"})),
        ("Population in year 1000", Interpretation("population", {"Ár": "1000", "Eining": "0"})),
        ("Population in year 2999", Interpretation("population", {"Ár": "2999", "Eining": "0"})),
        *[
            (
                question,
                Interpretation("population", {"Ár": "latest", "Eining": "0"}, before_latest(5)),
            )
            for question in (
                "Population over the last 5 years",
                "Population over the last 05 years",
                "Mannfjöldi síðustu fimm ár",
                "Hvernig breyttist mannfjöldinn síðustu 5 ár?",
            )
        ],
        *[
            (question, Interpretation("population", {"Ár": "2025", "Eining": "0"}, "2020"))
            for question in (
                "Compare the population in 2020 and 2025",
                "Berðu saman mannfjölda 2020 og 2025",
            )
        ],
    ],
)
def test_preserves_supported_stocks_and_endpoint_comparisons(
    question: str, expected: Interpretation
) -> None:
    assert interpret(question) == expected


# A change with no stated period: a comparison span is never assumed, on either route.
UNSTATED_CHANGES = [
    ("How has Iceland's population changed?", "en"),
    ("How has the population changed?", "en"),
    ("Has the population grown?", "en"),
    ("Hvernig hefur mannfjöldinn breyst?", "is"),
    ("How has inflation changed?", "en"),
    ("Hvernig hefur verðbólgan þróast?", "is"),
    ("Hvernig hefur vísitala neysluverðs breyst?", "is"),
    # Catalog topics, which answered with the latest single figure.
    ("How has unemployment changed?", "en"),
    ("Hvernig hefur atvinnuleysi breyst?", "is"),
    ("How has the population of Reykjavík changed?", "en"),
    ("Hvernig hefur mannfjöldi í Reykjavík breyst?", "is"),
    ("How has the population of Reykjavík grown?", "en"),
]


@pytest.mark.parametrize(("question", "lang"), UNSTATED_CHANGES)
def test_asks_for_the_periods_of_an_unstated_change(question: str, lang: str) -> None:
    with (
        patch("talnaspor.pxweb._send") as send,
        patch("talnaspor.app.plan_answer") as plan,
        patch("talnaspor.app.plan_comparison") as compare,
    ):
        body = TestClient(app).post("/ask", json={"question": question, "lang": lang}).json()

    assert body["status"] == "clarification"
    assert body["answer"] is None and body["comparison"] is None
    expected = {"is": "Tilgreindu tímabilið sem á að bera saman", "en": "Please name the periods"}
    assert expected[lang] in body["message"]
    send.assert_not_called()
    plan.assert_not_called()
    compare.assert_not_called()


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        *[
            (
                question,
                Interpretation("population", {"Ár": "latest", "Eining": "0"}, before_latest(10)),
            )
            for question in (
                "How has Iceland's population changed over the last decade?",
                "Hvernig hefur mannfjöldinn breyst síðasta áratug?",
                "Hvernig hefur mannfjöldinn breyst síðustu tíu ár?",
            )
        ],
        *[
            (question, Interpretation("population", {"Ár": "2025", "Eining": "0"}, "2015"))
            for question in (
                "Hvernig hefur mannfjöldinn breyst frá 2015 til 2025?",
                "How did the population change from 2015 to 2025?",
            )
        ],
        *[
            (question, Interpretation("population", {"Ár": "latest", "Eining": "0"}, "2000"))
            for question in (
                "How has the population changed since 2000?",
                "Hvernig hefur mannfjöldinn breyst frá 2000?",
            )
        ],
        (
            "How has inflation changed over the last decade?",
            Interpretation(
                "cpi",
                {"Mánuður": "latest", "Vísitala": "CPI", "Liður": "change_A"},
                before_latest(120),
            ),
        ),
        (
            "Verðbólga í september 2025 og 2026",
            Interpretation(
                "cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"}, "2025M09"
            ),
        ),
        # A single latest value is still answered, with no comparison.
        (
            "Hvað búa margir á Íslandi?",
            Interpretation("population", {"Ár": "latest", "Eining": "0"}),
        ),
        (
            "What is inflation now?",
            Interpretation("cpi", {"Mánuður": "latest", "Vísitala": "CPI", "Liður": "change_A"}),
        ),
    ],
)
def test_keeps_stated_comparison_periods_and_latest_values(
    question: str, expected: Interpretation
) -> None:
    assert interpret(question) == expected


@pytest.mark.parametrize(
    ("question", "lang", "span"),
    [
        ("How did the unemployment rate change between 2020 and 2025?", "en", Span("2020", "2025")),
        ("Hvernig breyttist atvinnuleysi frá 2020 til 2025?", "is", Span("2020", "2025")),
        ("How has unemployment changed over the last five years?", "en", Span(None, None, 5)),
    ],
)
def test_catalog_compares_stated_periods(question: str, lang: str, span: Span) -> None:
    with (
        patch("talnaspor.pxweb._send") as send,
        patch("talnaspor.app.plan_answer") as plan,
        patch("talnaspor.app.plan_comparison", return_value=None) as compare,
    ):
        TestClient(app).post("/ask", json={"question": question, "lang": lang})

    assert compare.call_args.args[2] == span
    plan.assert_not_called()
    send.assert_not_called()


@pytest.mark.parametrize(
    ("question", "lang"),
    [("What is the unemployment rate?", "en"), ("Hver er kosningaþátttaka?", "is")],
)
def test_catalog_still_answers_a_single_latest_value(question: str, lang: str) -> None:
    with (
        patch("talnaspor.pxweb._send"),
        patch("talnaspor.app.plan_answer", return_value=None) as plan,
        patch("talnaspor.app.plan_comparison") as compare,
    ):
        TestClient(app).post("/ask", json={"question": question, "lang": lang})

    plan.assert_called_once()
    compare.assert_not_called()


@pytest.mark.parametrize(
    ("question", "lang"),
    [
        # A named change measure is one period's figure, not a comparison.
        ("What is the annual change in the wage index?", "en"),
        ("Monthly change in the wage index", "en"),
        ("Árleg breyting launavísitölu", "is"),
        # A change in one named period.
        ("What was the change in the wage index in August 2026?", "en"),
        ("Breyting launavísitölu í ágúst 2026", "is"),
    ],
)
def test_catalog_guard_leaves_single_period_changes(question: str, lang: str) -> None:
    with (
        patch("talnaspor.pxweb._send"),
        patch("talnaspor.app.plan_answer", return_value=None) as plan,
        patch("talnaspor.app.plan_comparison") as compare,
    ):
        body = TestClient(app).post("/ask", json={"question": question, "lang": lang}).json()

    assert "Please name the periods" not in body["message"]
    assert "Tilgreindu tímabilið sem á að bera saman" not in body["message"]
    plan.assert_called_once()
    compare.assert_not_called()


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Population growth in 2024", Interpretation("population", {"Ár": "2024", "Eining": "2"})),
        (
            "Hver var fjölgun íbúa árið 2024?",
            Interpretation("population", {"Ár": "2024", "Eining": "2"}),
        ),
        (
            "Population growth rate in 2024",
            Interpretation("population", {"Ár": "2024", "Eining": "1"}),
        ),
        (
            "Hve margir aðfluttir umfram brottflutta 2023?",
            Interpretation("population", {"Ár": "2023", "Eining": "3"}),
        ),
        (
            "Ársbreyting vísitölu neysluverðs í september 2026",
            Interpretation("cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"}),
        ),
        (
            "What was the monthly change in the CPI in September 2026?",
            Interpretation("cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_M"}),
        ),
    ],
)
def test_named_single_period_measures_are_unchanged(
    question: str, expected: Interpretation
) -> None:
    assert interpret(question) == expected


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known limitation: a change word with one named year on a catalog topic goes to the "
        "single-period planner. In the recorded responses it gets suggestions (no figure); it "
        "should compare that year with the one before, or ask for the periods."
    ),
)
@pytest.mark.parametrize(
    ("question", "lang"),
    [("unemployment change in 2024", "en"), ("breyting atvinnuleysis 2024", "is")],
)
def test_known_limitation_catalog_change_in_one_year(question: str, lang: str) -> None:
    with (
        patch("talnaspor.pxweb._send"),
        patch("talnaspor.app.plan_answer", return_value=None) as plan,
        patch("talnaspor.app.plan_comparison", return_value=None),
    ):
        TestClient(app).post("/ask", json={"question": question, "lang": lang})

    plan.assert_not_called()
