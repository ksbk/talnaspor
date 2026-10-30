"""Capture Icelandic metadata and data responses for offline answer tests."""

from pathlib import Path

import requests

from talnaspor.pxweb import get_data, get_metadata
from talnaspor.query import build_query
from talnaspor.tables import TABLES

FIXTURES = Path("tests/fixtures/is")

CAPTURES: list[tuple[str, dict[str, str | list[str]]]] = [
    ("cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"}),
    ("cpi", {"Mánuður": ["2025M09", "2026M09"], "Vísitala": "CPI", "Liður": "change_A"}),
    ("population", {"Ár": "2026", "Eining": "0"}),
    ("population", {"Ár": ["2016", "2026"], "Eining": "0"}),
]

FIXTURES.mkdir(parents=True, exist_ok=True)

for key, selections in CAPTURES:
    table = TABLES[key]

    metadata_response = requests.get(table.api_url, timeout=15)
    metadata_response.raise_for_status()
    (FIXTURES / f"{key}_metadata.json").write_text(metadata_response.text, encoding="utf-8")

    query = build_query(get_metadata(table.api_url), selections)
    periods = selections[table.time_code]
    period = "_".join([periods] if isinstance(periods, str) else periods).lower()
    data_path = FIXTURES / f"{key}_{period}.json"
    data_path.write_text(get_data(table.api_url, query), encoding="utf-8")

    print(f"Saved {key} metadata and {data_path}")
