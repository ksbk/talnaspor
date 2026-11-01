"""The start page's example questions are folded away until asked for.

The page's own script is run in Node against a minimal DOM (tests/page_harness.js), which
clicks through the page as a user would and reports what is shown. Skipped without Node.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent
PAGE = ROOT / "src" / "talnaspor" / "static" / "index.html"
LABELS = {
    "is": ("Skoða dæmi um spurningar", "Fela dæmi um spurningar"),
    "en": ("Explore example questions", "Hide example questions"),
}

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js")


def page_examples(lang: str) -> list[str]:
    """The example questions the page lists for a language."""
    block = re.search(
        rf"\n    {lang}: \{{.*?examples: \[(.*?)\]", PAGE.read_text(encoding="utf-8"), re.DOTALL
    )
    assert block
    return re.findall(r'"([^"]+)"', block[1])


@pytest.fixture(scope="module")
def steps() -> dict[str, Any]:
    node = shutil.which("node")
    assert node
    result = subprocess.run(
        [node, str(Path(__file__).parent / "page_harness.js"), str(PAGE)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return dict(json.loads(result.stdout))


def test_examples_are_folded_away_at_first(steps: dict[str, Any]) -> None:
    initial = steps["initial"]

    assert initial["hidden"] is True
    assert initial["expanded"] == "false"
    assert initial["controls"] == "examples"
    assert initial["label"] == LABELS["is"][0]


def test_toggle_unfolds_and_folds_the_examples(steps: dict[str, Any]) -> None:
    assert steps["expanded"]["hidden"] is False
    assert steps["expanded"]["expanded"] == "true"
    assert steps["expanded"]["label"] == LABELS["is"][1]
    assert steps["collapsed"]["hidden"] is True
    assert steps["collapsed"]["expanded"] == "false"
    assert steps["collapsed"]["label"] == LABELS["is"][0]


@pytest.mark.parametrize(
    ("step", "lang"),
    [("initial", "is"), ("englishCollapsed", "en"), ("icelandicStillExpanded", "is")],
)
def test_all_eight_examples_are_kept_in_each_language(
    steps: dict[str, Any], step: str, lang: str
) -> None:
    assert len(page_examples(lang)) == 8
    assert steps[step]["examples"] == page_examples(lang)


def test_changing_language_updates_the_toggle_and_keeps_its_state(steps: dict[str, Any]) -> None:
    english = steps["englishCollapsed"]
    assert english["lang"] == "en"
    assert english["hidden"] is True and english["expanded"] == "false"
    assert english["label"] == LABELS["en"][0]

    icelandic = steps["icelandicStillExpanded"]
    assert icelandic["hidden"] is False and icelandic["expanded"] == "true"
    assert icelandic["label"] == LABELS["is"][1]

    # Changing language never unfolds the examples.
    again = steps["englishStillCollapsed"]
    assert again["hidden"] is True and again["expanded"] == "false"
    assert again["label"] == LABELS["en"][0]


def test_choosing_an_example_asks_it(steps: dict[str, Any]) -> None:
    selected = steps["selected"]

    assert selected["question"] == page_examples("en")[2]
    assert selected["requests"] == [
        {"url": "/ask", "body": {"question": selected["question"], "lang": "en"}}
    ]
    assert selected["exchanges"] == 1
