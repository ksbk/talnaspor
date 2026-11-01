"""Every example question on the start page gives its documented, evidence-backed reply.

The page's examples are read from index.html and answered offline from the PX-Web responses
recorded in evaluation/recordings (an unrecorded request fails). Expected figures match the
evaluation set (questions.json) or the understanding set's development split, as noted.
"""

import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import requests
from fastapi.testclient import TestClient

from talnaspor.app import app

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import evaluate_understanding as recordings  # type: ignore[import-not-found]

PAGE = (ROOT / "src" / "talnaspor" / "static" / "index.html").read_text(encoding="utf-8")

# (status, table, periods, shown figure) for each example, with its evidence.
EXPECTED: dict[str, dict[str, tuple[str, str | None, list[str] | None, str | None]]] = {
    "is": {
        # cpi-09
        "Hver er verðbólgan núna?": ("answer", "VIS01000.px", ["2026M10"], "5,9%"),
        # pop-01
        "Hvað búa margir á Íslandi?": ("answer", "MAN00000.px", ["2026"], "394.324 íbúar"),
        # pop-10
        "Hvernig hefur mannfjöldinn breyst frá 2015 til 2025?": (
            "comparison",
            "MAN00000.px",
            ["2015", "2025"],
            "+66.420 íbúar",
        ),
        # cpi-11
        "Verðbólga í september 2025 og 2026": (
            "comparison",
            "VIS01000.px",
            ["2025M09", "2026M09"],
            "+1,8 prósentustig",
        ),
        # pop-04
        "Hver var fjölgun íbúa árið 2024?": ("answer", "MAN00000.px", ["2024"], "5.718 manns"),
        # The Icelandic form of understanding d10 (dev): the same table and cells.
        "Hvernig breyttist atvinnuleysi frá 2020 til 2025?": (
            "comparison",
            "VIN00911.px",
            ["2020", "2025"],
            "-2,0 prósentustig",
        ),
        # cat-04
        "Hver er munurinn á launum karla og kvenna?": (
            "answer",
            "VIN02010.px",
            ["2024"],
            "10,4 (%)",
        ),
        # clar-01
        "Verðbólga árið 2024": ("clarification", None, None, None),
    },
    "en": {
        # en-01
        "What is inflation now?": ("answer", "VIS01000.px", ["2026M10"], "5.9%"),
        # pop-01, in English
        "How many people live in Iceland?": ("answer", "MAN00000.px", ["2026"], "394,324 people"),
        # pop-11 (Icelandic wording): the same cells
        "How has the population changed since 2000?": (
            "comparison",
            "MAN00000.px",
            ["2000", "2026"],
            "+115,275 people",
        ),
        # cpi-11, in English
        "Inflation in September 2025 and 2026": (
            "comparison",
            "VIS01000.px",
            ["2025M09", "2026M09"],
            "+1.8 percentage points",
        ),
        # en-04
        "What was the population increase in 2024?": (
            "answer",
            "MAN00000.px",
            ["2024"],
            "5,718 people",
        ),
        # understanding d10 (dev), naming the rate: the same table and cells
        "How did the unemployment rate change between 2020 and 2025?": (
            "comparison",
            "VIN00911.px",
            ["2020", "2025"],
            "-2.0 percentage points",
        ),
        # en-08
        "What is the gender pay gap?": ("answer", "VIN02010.px", ["2024"], "10.4 (%)"),
        # en-09
        "What was inflation in 2024?": ("clarification", None, None, None),
    },
}


def page_examples(lang: str) -> list[str]:
    """The example questions the page shows for a language."""
    block = re.search(rf"\n    {lang}: \{{.*?examples: \[(.*?)\]", PAGE, re.DOTALL)
    assert block
    return re.findall(r'"([^"]+)"', block[1])


@pytest.fixture
def recorded() -> Iterator[None]:
    """Answer every PX-Web request from evaluation/recordings, offline."""
    with (
        patch.object(recordings, "RECORDINGS", ROOT / "evaluation" / "recordings"),
        patch.object(requests, "get", recordings.recorded(requests.get, "GET", offline=True)),
        patch.object(requests, "post", recordings.recorded(requests.post, "POST", offline=True)),
    ):
        yield


@pytest.mark.parametrize("lang", ["is", "en"])
def test_page_shows_exactly_the_checked_examples(lang: str) -> None:
    assert page_examples(lang) == list(EXPECTED[lang])


@pytest.mark.parametrize(
    ("lang", "question"),
    [(lang, question) for lang, examples in EXPECTED.items() for question in examples],
)
@pytest.mark.usefixtures("recorded")
def test_example_gives_its_documented_reply(lang: str, question: str) -> None:
    status, table, periods, shown = EXPECTED[lang][question]

    body: dict[str, Any] = (
        TestClient(app).post("/ask", json={"question": question, "lang": lang}).json()
    )

    if status == "clarification":
        assert body["status"] == "clarification"
        return
    assert body["status"] == "answer"
    result = body["comparison"] if status == "comparison" else body["answer"]
    assert result is not None
    assert result["api_url"].endswith("/" + str(table))
    if status == "comparison":
        assert [result["start"]["period"], result["end"]["period"]] == periods
        assert result["difference_text"] == shown
    else:
        assert [result["period"]] == periods
        assert result["value_text"] == shown
