"""Crawl Statistics Iceland's PX-Web table tree into src/talnaspor/data/catalog.json.

The API's search function is not enabled on px.hagstofa.is, so the catalog is built by
walking every database and folder once, in Icelandic and in English. Requests are
throttled to stay well within the API's rate limit.

    uv run python scripts/build_catalog.py
"""

import json
import time
from datetime import date
from pathlib import Path
from typing import Any

import requests

CATALOG = Path("src/talnaspor/data/catalog.json")
BASES = {
    "is": "https://px.hagstofa.is/pxis/api/v1/is/",
    "en": "https://px.hagstofa.is/pxen/api/v1/en/",
}
DATABASE_NAMES = {
    "Atvinnuvegir": "Atvinnuvegir",
    "Efnahagur": "Efnahagur",
    "Ibuar": "Íbúar",
    "Samfelag": "Samfélag",
    "Sogulegar": "Sögulegar hagtölur",
    "Umhverfi": "Umhverfi",
}
PAUSE_SECONDS = 0.35

session = requests.Session()


def get(url: str) -> Any:
    for attempt in range(5):
        time.sleep(PAUSE_SECONDS)
        response = session.get(url, timeout=30)
        if response.status_code == 429:
            time.sleep(10 * (attempt + 1))
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError(f"Rate limited repeatedly: {url}")


def crawl(base: str) -> dict[str, dict[str, Any]]:
    """Return every table under base, keyed by its path."""
    tables: dict[str, dict[str, Any]] = {}
    pending: list[tuple[str, list[str]]] = [
        (database["dbid"], [DATABASE_NAMES.get(database["dbid"], database["text"])])
        for database in get(base)
    ]

    while pending:
        path, folders = pending.pop()
        for entry in get(base + path):
            child = f"{path}/{entry['id']}"
            if entry["type"] == "l":
                pending.append((child, [*folders, entry["text"]]))
            elif entry["type"] == "t":
                tables[child] = {
                    "title": entry["text"],
                    "folders": folders,
                    "updated": entry.get("updated"),
                }
        print(f"{len(tables):5} tables, {len(pending):4} folders pending", end="\r")
    print()
    return tables


def main() -> None:
    icelandic = crawl(BASES["is"])
    english = crawl(BASES["en"])

    tables = [
        {
            "path": path,
            "title": table["title"],
            "folders": table["folders"],
            "title_en": english.get(path, {}).get("title"),
            "folders_en": english.get(path, {}).get("folders", []),
            "updated": table["updated"],
        }
        for path, table in sorted(icelandic.items())
    ]

    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(
        json.dumps(
            {"crawled": date.today().isoformat(), "tables": tables},
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    with_english = sum(1 for table in tables if table["title_en"])
    print(f"Wrote {len(tables)} tables ({with_english} with English titles) to {CATALOG}")


if __name__ == "__main__":
    main()
