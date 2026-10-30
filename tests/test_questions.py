"""Check that every question in the evaluation set is interpreted as recorded."""

import json
from pathlib import Path
from typing import Any

import pytest

from talnaspor.app import candidates
from talnaspor.catalog import search
from talnaspor.interpret import Clarification, Interpretation, interpret

QUESTIONS: list[dict[str, Any]] = json.loads(
    (Path(__file__).parent.parent / "evaluation" / "questions.json").read_text(encoding="utf-8")
)["questions"]


@pytest.mark.parametrize("item", QUESTIONS, ids=[item["id"] for item in QUESTIONS])
def test_question_is_interpreted_as_recorded(item: dict[str, Any]) -> None:
    result = interpret(item["question"])

    if item["expect"] == "clarification":
        assert isinstance(result, Clarification)
        assert item["message"] in result.text(item.get("lang", "is"))
        return
    if item["expect"] in ("suggestions", "catalog"):
        # Not a curated topic: the expected table must be among those the planner tries.
        assert isinstance(result, Clarification)
        assert not result.recognized
        table = item.get("table") or item["table_path"]
        hits = candidates(item["question"], search(item["question"], limit=10))
        assert any(hit.api_url.endswith("/" + table) for hit in hits)
        return

    expected = item["interpretation"]
    assert result == Interpretation(
        expected["table"], expected["selections"], expected.get("compare_from")
    )


@pytest.mark.parametrize(
    "item",
    [item for item in QUESTIONS if item["expect"] in ("answer", "comparison", "catalog")],
    ids=lambda item: item["id"],
)
def test_question_has_verified_values(item: dict[str, Any]) -> None:
    periods = {"answer": 1, "comparison": 2, "catalog": 1}[item["expect"]]

    assert len(item["periods"]) == periods
    assert len(item["values"]) == periods
    assert all(isinstance(value, int | float) for value in item["values"])


def test_question_ids_are_unique() -> None:
    ids = [item["id"] for item in QUESTIONS]

    assert len(ids) == len(set(ids))
