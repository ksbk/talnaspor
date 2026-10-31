"""Score Talnaspor on evaluation/understanding.json: questions it was not written for.

Every PX-Web response is recorded in evaluation/recordings/, so a later run answers from
the recordings and makes live requests only for queries it has not seen. With --offline
it makes none: an unrecorded query fails, and the question is scored as an error.

Only the totals of the holdout split are reported, so that it cannot guide development.

    uv run --group dev python scripts/evaluate_understanding.py [--offline]
"""

import base64
import hashlib
import json
import statistics
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import requests
from fastapi.testclient import TestClient

from talnaspor.app import app

QUESTIONS = Path("evaluation/understanding.json")
RESULTS = Path("evaluation/understanding-results.md")
RECORDINGS = Path("evaluation/recordings")
# Statistics Iceland limits requests from one address; live requests are paced.
PAUSE_SECONDS = 0.4
OUTCOMES = ("CORRECT", "SAFE", "WRONG", "ERROR")

live_requests = 0


def recorded(send: Any, method: str, offline: bool) -> Any:
    """Wrap requests.get or requests.post to answer from, and add to, the recordings."""

    def wrapper(url: str, **kwargs: Any) -> requests.Response:
        global live_requests
        key = json.dumps([method, url, kwargs.get("json")], sort_keys=True, ensure_ascii=False)
        path = RECORDINGS / f"{hashlib.sha256(key.encode()).hexdigest()[:24]}.json"
        if path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
        elif offline:
            raise requests.ConnectionError(f"Not recorded: {method} {url}")
        else:
            time.sleep(PAUSE_SECONDS)
            live_requests += 1
            response = send(url, **kwargs)
            saved = {
                "key": key,
                "status": response.status_code,
                # Only the content type is needed; other headers include cookies.
                "headers": {"Content-Type": response.headers.get("Content-Type", "")},
                "content": base64.b64encode(response.content).decode(),
            }
            if response.status_code == 200:
                path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        response = requests.Response()
        response.status_code = saved["status"]
        response.headers.update(saved["headers"])
        response._content = base64.b64decode(saved["content"])
        response.url = url
        return response

    return wrapper


def score(item: dict[str, Any], body: dict[str, Any]) -> str:
    """CORRECT, SAFE (no answer where one was expected), WRONG or ERROR."""
    status = body.get("status")
    if status == "error" or status is None:
        return "ERROR"
    answered = status == "answer"
    if item["expect"] == "no_answer":
        return "WRONG" if answered else "CORRECT"
    if not answered:
        return "SAFE"

    if item["expect"] == "comparison":
        comparison = body.get("comparison")
        if not comparison:
            return "WRONG"
        got = [
            (comparison["start"]["period"], comparison["start"]["value"]),
            (comparison["end"]["period"], comparison["end"]["value"]),
        ]
        for entry in item["accept"]:
            if got == list(zip(entry["periods"], entry["values"], strict=True)):
                return "CORRECT"
        return "WRONG"

    result = body.get("answer")
    if not result or body.get("comparison"):
        return "WRONG"
    for entry in item["accept"]:
        if result["value"] == entry["values"][0] and str(result["period"]).startswith(
            entry["periods"][0]
        ):
            return "CORRECT"
    return "WRONG"


def shown(body: dict[str, Any]) -> str:
    if body.get("comparison"):
        comparison = body["comparison"]
        return f"{comparison['start']['value_text']} → {comparison['end']['value_text']}"
    if body.get("answer"):
        answer = body["answer"]
        return f"{answer['value_text']} ({answer['period']}, {answer['table_title'][:50]})"
    return f"{body.get('status')}: {str(body.get('message'))[:90]}"


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {outcome: sum(row["outcome"] == outcome for row in rows) for outcome in OUTCOMES}
    answerable = [row for row in rows if row["expect"] != "no_answer"]
    times = [row["ms"] for row in rows]
    return {
        **counts,
        "total": len(rows),
        "coverage": (f"{sum(row['outcome'] == 'CORRECT' for row in answerable)}/{len(answerable)}"),
        "median_ms": round(statistics.median(times)) if times else 0,
        "max_ms": max(times, default=0),
    }


def main() -> None:
    offline = "--offline" in sys.argv
    RECORDINGS.mkdir(parents=True, exist_ok=True)
    requests.get = recorded(requests.get, "GET", offline)  # type: ignore[assignment]
    requests.post = recorded(requests.post, "POST", offline)  # type: ignore[assignment]

    document = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    client = TestClient(app, raise_server_exceptions=False)
    rows = []
    for item in document["questions"]:
        payload = {"question": item["question"], "lang": item["lang"]}
        if "previous" in item:
            payload["previous"] = item["previous"]
        body = client.post("/ask", json=payload).json()
        row = {
            "id": item["id"],
            "split": item["split"],
            "category": item["category"],
            "expect": item["expect"],
            "outcome": score(item, body),
            "ms": body.get("elapsed_ms", 0),
            "shown": shown(body),
            "item": item,
        }
        rows.append(row)
        if item["split"] == "dev":
            print(f"{row['outcome']:8} {item['id']} {row['ms']:5} ms  {item['question']}")

    splits = {split: [row for row in rows if row["split"] == split] for split in ("dev", "holdout")}
    totals = {split: summary(split_rows) for split, split_rows in splits.items()}
    categories = sorted({row["category"] for row in rows})
    latency = (
        "replayed from recordings, so not comparable with a live run"
        if live_requests == 0
        else f"live ({live_requests} new PX-Web requests)"
    )

    def counts_row(name: str, total: dict[str, Any]) -> str:
        cells = [name, *(total[o] for o in OUTCOMES), total["coverage"]]
        cells += [total["median_ms"], total["max_ms"]]
        return "| " + " | ".join(str(cell) for cell in cells) + " |"

    lines = [
        "# Understanding evaluation",
        "",
        (
            f"Run on {date.today().isoformat()}; expected values recorded {document['as_of']}. "
            f"Latency: {latency}."
        ),
        "",
        (
            "CORRECT: the right figure, or a refusal where none should be given. SAFE: no "
            "answer where one exists (a clarification, suggestions or a refusal). WRONG: a "
            "figure that does not match an accepted cell, or a figure where none should be "
            "given. Coverage: correct answers among the answerable questions."
        ),
        "",
        "| Split | Correct | Safe | Wrong | Error | Coverage | Median ms | Max ms |",
        "|---|---:|---:|---:|---:|---|---:|---:|",
        counts_row("dev", totals["dev"]),
        counts_row("holdout", totals["holdout"]),
        "",
        "## By category (both splits)",
        "",
        "| Category | Correct | Safe | Wrong | Error | Coverage | Median ms | Max ms |",
        "|---|---:|---:|---:|---:|---|---:|---:|",
        *(
            counts_row(category, summary([r for r in rows if r["category"] == category]))
            for category in categories
        ),
        "",
        "## Dev questions",
        "",
        "| ID | Lang | Category | Question | Result | Shown | ms |",
        "|---|---|---|---|---|---|---:|",
    ]
    for row in splits["dev"]:
        item = row["item"]
        question = item["question"]
        if "previous" in item:
            question = f"({item['previous']}) → {question}"
        cells = [row["id"], item["lang"].upper(), row["category"], question, row["outcome"]]
        cells += [row["shown"], row["ms"]]
        lines.append("| " + " | ".join(str(c).replace("|", "\\|") for c in cells) + " |")
    RESULTS.write_text("\n".join([*lines, ""]), encoding="utf-8")

    for split, total in totals.items():
        print(
            f"{split:8} "
            + ", ".join(f"{total[o]} {o}" for o in OUTCOMES)
            + f"; coverage {total['coverage']}; median {total['median_ms']} ms"
        )
    print(f"{live_requests} live PX-Web requests. Wrote {RESULTS}")


if __name__ == "__main__":
    main()
