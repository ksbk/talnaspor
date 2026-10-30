"""Capture a CPI response for developing the JSON-stat2 decoder."""

from pathlib import Path

from talnaspor.pxweb import get_data, get_metadata
from talnaspor.query import build_query

URL = "https://px.hagstofa.is/pxen/api/v1/en/Efnahagur/visitolur/1_vnv/1_vnv/VIS01000.px"

metadata = get_metadata(URL)

query = build_query(
    metadata,
    {
        "Month": "2026M09",
        "Index": "CPI",
        "Item": "change_A",
    },
)

response_text = get_data(URL, query)

fixture_path = Path("tests/fixtures/cpi_2026m09.json")
fixture_path.write_text(response_text, encoding="utf-8")

print(f"Saved response to {fixture_path}")
print(f"Table: {metadata.title}")
print(f"Dimensions: {[variable.code for variable in metadata.variables]}")
