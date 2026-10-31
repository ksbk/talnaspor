"""Fetch expected values for the question set, independently of Talnaspor's own code.

This script deliberately shares nothing with the talnaspor package: table URLs are
written out here, queries are built by hand, and responses use PX-Web's legacy json
format instead of JSON-stat2. Run with --write to record the values in the file.

    uv run python scripts/fetch_expected.py [questions.json] [--write]

For a question set with 'accept' entries (evaluation/understanding.json), each entry's
cells are fetched by their labels, all its periods in one request.
"""

import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

QUESTIONS = Path("evaluation/questions.json")

TABLES = {
    "cpi": (
        "https://px.hagstofa.is/pxis/api/v1/is/Efnahagur/visitolur/1_vnv/1_vnv/VIS01000.px",
        "Mánuður",
    ),
    "population": (
        (
            "https://px.hagstofa.is/pxis/api/v1/is/Ibuar/mannfjoldi/1_yfirlit/"
            "Yfirlit_mannfjolda/MAN00000.px"
        ),
        "Ár",
    ),
}


def fetch(table: str, selections: dict[str, str], periods: list[str]) -> list[int | float | None]:
    url, time_code = TABLES[table]
    query = [
        {"code": code, "selection": {"filter": "item", "values": [value]}}
        for code, value in selections.items()
        if code != time_code
    ]
    query.append({"code": time_code, "selection": {"filter": "item", "values": periods}})

    response = requests.post(url, json={"query": query, "response": {"format": "json"}}, timeout=20)
    response.raise_for_status()
    body = response.json()

    time_column = [column["code"] for column in body["columns"]].index(time_code)
    by_period = {row["key"][time_column]: row["values"][0] for row in body["data"]}
    return [parse(by_period[period]) for period in periods]


def fetch_catalog(path: str, period: str, labels: dict[str, str]) -> list[int | float | None]:
    """Fetch one value from any table, selecting categories by their labels."""
    return fetch_cells(path, [period], labels)


_variables: dict[str, list[dict[str, Any]]] = {}


def fetch_cells(path: str, periods: list[str], labels: dict[str, str]) -> list[int | float | None]:
    """Fetch one value per period from any table, selecting categories by their labels.

    The dimension that is not labelled is the time dimension; its labels are the periods.
    """
    url = "https://px.hagstofa.is/pxis/api/v1/is/" + path
    if url not in _variables:
        _variables[url] = requests.get(url, timeout=20).json()["variables"]
    query = []
    time_code = None
    for variable in _variables[url]:
        texts = variable.get("valueTexts") or variable["values"]
        codes = dict(zip(texts, variable["values"], strict=True))
        if variable["code"] in labels:
            values = [codes[labels[variable["code"]]]]
        else:
            time_code = variable["code"]
            values = [codes[period] for period in periods]
        query.append({"code": variable["code"], "selection": {"filter": "item", "values": values}})

    response = requests.post(url, json={"query": query, "response": {"format": "json"}}, timeout=20)
    response.raise_for_status()
    body = response.json()
    time_column = [column["code"] for column in body["columns"]].index(time_code)
    by_code = {row["key"][time_column]: row["values"][0] for row in body["data"]}
    time_variable = next(v for v in _variables[url] if v["code"] == time_code)
    texts = time_variable.get("valueTexts") or time_variable["values"]
    code_of = dict(zip(texts, time_variable["values"], strict=True))
    return [parse(by_code[code_of[period]]) for period in periods]


def parse(text: str) -> int | float | None:
    if text.strip() in {"", ".", "..", "..."}:
        return None
    return float(text) if "." in text else int(text)


def main() -> None:
    files = [Path(arg) for arg in sys.argv[1:] if not arg.startswith("--")]
    questions = files[0] if files else QUESTIONS
    document = json.loads(questions.read_text(encoding="utf-8"))
    mismatches = 0

    for item in document["questions"]:
        if "accept" in item:
            for number, entry in enumerate(item["accept"]):
                values = fetch_cells(entry["table_path"], entry["periods"], entry["labels"])
                recorded = entry.get("values")
                status = "new" if recorded is None else ("ok" if recorded == values else "MISMATCH")
                mismatches += status == "MISMATCH"
                print(f"{item['id']}.{number:<5} {status:8} {entry['periods']} -> {values}")
                entry["values"] = values
                # Statistics Iceland limits requests from one address.
                time.sleep(1)
            continue
        if item["expect"] == "catalog":
            values = fetch_catalog(item["table_path"], item["period"], item["labels"])
            item["periods"] = [item["period"]]
        elif "periods" in item:
            interpretation = item["interpretation"]
            values = fetch(interpretation["table"], interpretation["selections"], item["periods"])
        else:
            continue
        recorded = item.get("values")
        status = "new" if recorded is None else ("ok" if recorded == values else "MISMATCH")
        mismatches += status == "MISMATCH"
        print(f"{item['id']:8} {status:8} {item['periods']} -> {values}")
        item["values"] = values

    if "--write" in sys.argv:
        questions.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {questions}")
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
