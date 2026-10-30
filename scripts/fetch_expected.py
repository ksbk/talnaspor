"""Fetch expected values for the question set, independently of Talnaspor's own code.

This script deliberately shares nothing with the talnaspor package: table URLs are
written out here, queries are built by hand, and responses use PX-Web's legacy json
format instead of JSON-stat2. Run with --write to record the values in the file.

    uv run python scripts/fetch_expected.py [--write]
"""

import json
import sys
from pathlib import Path

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
    url = "https://px.hagstofa.is/pxis/api/v1/is/" + path
    variables = requests.get(url, timeout=20).json()["variables"]
    query = []
    for variable in variables:
        texts = variable.get("valueTexts") or variable["values"]
        codes = dict(zip(texts, variable["values"], strict=True))
        label = labels.get(variable["code"], period if period in codes else None)
        query.append(
            {"code": variable["code"], "selection": {"filter": "item", "values": [codes[label]]}}
        )

    response = requests.post(url, json={"query": query, "response": {"format": "json"}}, timeout=20)
    response.raise_for_status()
    return [parse(response.json()["data"][0]["values"][0])]


def parse(text: str) -> int | float | None:
    if text.strip() in {"", ".", "..", "..."}:
        return None
    return float(text) if "." in text else int(text)


def main() -> None:
    document = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    mismatches = 0

    for item in document["questions"]:
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
        QUESTIONS.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {QUESTIONS}")
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
