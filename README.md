# Talnaspor

**Explore Icelandic statistics using everyday language.**

Talnaspor is an open-source web application developed by a solo developer for Gagnaþon
2026. Ask questions in Icelandic or English and retrieve figures from Statistics Iceland
(Hagstofa Íslands), with references to the original data.

## Why Talnaspor?

Statistics Iceland publishes thousands of tables. Finding a particular figure means
locating the right table and selecting its period, categories and measure. Talnaspor
helps with these steps and shows its selections so you can check the result at the source.

## Features

- Questions and answers in Icelandic and English
- Search across a catalog of approximately 2,100 statistical tables
- Inflation and population answers, with catalog answers where dimension selection is supported
- Validated PX-Web retrieval, source links, periods and selected categories
- Numerical units where available, and comparisons between two periods where supported
- Clarifications, table suggestions and refusals when a direct answer cannot be verified
- Supported short follow-ups, with the interpreted question shown

## Quick start

Requires Python 3.10 or later and network access to px.hagstofa.is.

```sh
git clone https://github.com/ksbk/talnaspor.git
cd talnaspor
python3 -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate
pip install -r requirements.txt    # Exact versions, exported from uv.lock
uvicorn app:app
```

Open <http://127.0.0.1:8000> in your browser. Talnaspor runs locally.
With uv installed, `make sync` followed by `make run` starts the same application.
See [example questions and recorded answers](docs/examples.md) to get started.

## How it works

Deterministic rules interpret a question and search the table catalog. Talnaspor selects
categories, validates them against table metadata, and retrieves observations through
Statistics Iceland's PX-Web API. It checks the returned structure and presents the
figure, or a supported two-period calculation, with its source and selections.

No language model runs at runtime. Structural validation cannot guarantee that a question
was interpreted correctly; the selected table and categories remain available to inspect.
See [How it works](docs/how-it-works.md) for the architecture, API and runtime safeguards.

## Evaluation and limitations

Supported questions have been tested against recorded expectations from Statistics
Iceland. The available evaluations informed development; they are not independent unseen
tests. Detailed results and methodology are in the
[evaluation documentation](docs/how-it-works.md#7-evaluation).

Broader natural-language coverage remains limited. Many questions receive a clarification
or table suggestions rather than a figure. Catalog units may be general, and time series,
ratios and compound questions are not supported. Live retrieval depends on API availability
and request limits. See the [known limitations](docs/how-it-works.md#8-known-limitations).

## Documentation

- [Technical documentation and development commands](docs/how-it-works.md)
- [Source guide: what every file does](docs/source-guide.md)
- [Examples with recorded figures and source selections](docs/examples.md)
- [Potential future enhancements](docs/roadmap.md)

## Development and licence

Talnaspor was developed by one individual using AI-assisted coding tools, including
Claude Code and Codex. It runs on Python, FastAPI, Uvicorn, Requests, Pydantic and pandas.
Released under the [MIT licence](LICENSE).
