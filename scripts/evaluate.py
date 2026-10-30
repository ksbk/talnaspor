"""Ask every evaluation question through /ask, live, and compare with verified values.

Writes evaluation/results.md as a table suitable for the presentation.

    uv run --group dev python scripts/evaluate.py
"""

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from talnaspor.app import app

QUESTIONS = Path("evaluation/questions.json")
RESULTS = Path("evaluation/results.md")


def check(item: dict[str, Any], body: dict[str, Any]) -> str:
    """Return PASS, FAIL or STALE (a newer period was published since the values were recorded)."""
    if body["status"] != {"comparison": "answer"}.get(item["expect"], item["expect"]):
        return "FAIL"

    if item["expect"] == "clarification":
        return "PASS" if item["message"] in body["message"] else "FAIL"
    if item["expect"] == "suggestions":
        suggested = [table["api_url"] for table in body["tables"]]
        return "PASS" if any(url.endswith("/" + item["table"]) for url in suggested) else "FAIL"
    if item["expect"] == "refusal":
        return "PASS" if item["detail"] in (body["detail"] or "") else "FAIL"

    if item["expect"] == "answer":
        result = body["answer"]
        periods, values = [result["period"]], [result["value"]]
    else:
        result = body["comparison"]
        periods = [result["start"]["period"], result["end"]["period"]]
        values = [result["start"]["value"], result["end"]["value"]]

    if periods != item["periods"]:
        uses_latest = "latest" in json.dumps(item["interpretation"])
        return "STALE" if uses_latest else "FAIL"
    return "PASS" if values == item["values"] else "FAIL"


def shown(body: dict[str, Any]) -> str:
    if body.get("comparison"):
        comparison = body["comparison"]
        return f"{comparison['start']['value_text']} → {comparison['end']['value_text']}"
    if body.get("answer"):
        return str(body["answer"]["value_text"])
    if body.get("tables"):
        return f"{len(body['tables'])} töflur, t.d. {body['tables'][0]['title']}"
    return str(body["message"])


def main() -> None:
    document = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    client = TestClient(app)
    rows: list[str] = []
    outcomes: dict[str, int] = {}
    limitations: list[str] = []

    for item in document["questions"]:
        body = client.post("/ask", json={"question": item["question"]}).json()
        outcome = check(item, body)
        if outcome == "PASS" and "limitation" in item:
            # Behaves as documented, but the documented behaviour is not a good answer.
            outcome = "KNOWN LIMITATION"
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        expected = item["expect"] + (" (known limitation)" if "limitation" in item else "")
        if "limitation" in item:
            limitations.append(f"- `{item['id']}`: {item['limitation']}")
        cells = [item["id"], item["question"], expected, outcome, shown(body), body["elapsed_ms"]]
        rows.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |")
        print(f"{outcome:16} {item['id']:8} {body['elapsed_ms']:5} ms  {item['question']}")

    total = len(document["questions"])
    summary = ", ".join(f"{count} {outcome}" for outcome, count in sorted(outcomes.items()))
    RESULTS.write_text(
        "\n".join(
            [
                "# Evaluation results",
                "",
                (
                    f"Run on {date.today().isoformat()} against the live PX-Web API. "
                    f"Expected values recorded {document['as_of']}."
                ),
                "",
                f"**{total} questions: {summary}.**",
                "",
                (
                    "Expected values were fetched independently of Talnaspor's query and decoding "
                    "code (`scripts/fetch_expected.py`). KNOWN LIMITATION marks a question that "
                    "behaves as documented below but is not answered well. STALE means Statistics "
                    "Iceland has published a newer period since the values were recorded."
                ),
                "",
                "| ID | Question | Expected | Result | Shown | ms |",
                "|---|---|---|---|---|---:|",
                *rows,
                "",
                "## Known limitations",
                "",
                *limitations,
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\n{total} questions: {summary}. Wrote {RESULTS}")
    sys.exit(1 if outcomes.get("FAIL") else 0)


if __name__ == "__main__":
    main()
