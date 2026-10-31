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
