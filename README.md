# Talnaspor

A chatbot that answers everyday questions about Icelandic statistics with official
figures from Statistics Iceland (Hagstofa Íslands), and shows exactly where every
number came from.

Built for Track 2 (direct PX-Web API) of Statistics Iceland's Gagnaþon 2026.

> **Hver er verðbólgan núna?**
> Vísitala neysluverðs, ársbreyting í október 2026: 5,9%. Heimild: Hagstofa Íslands,
> Vísitala neysluverðs og breytingar, grunnur 1988=100.

For any other topic, Talnaspor points to the official tables that hold the answer,
found among all 2,102 tables Statistics Iceland publishes.

Every figure is retrieved live from [px.hagstofa.is](https://px.hagstofa.is) and checked
against the exact query that was sent. Talnaspor uses **no language model at runtime**:
questions are interpreted by explicit rules, and answers are filled into fixed Icelandic
templates, so a number can never be invented.

## Quick start

Requires Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

```sh
make sync    # Install exact dependency versions from uv.lock
make run     # Start the server
```

Open <http://127.0.0.1:8000> and ask a question, or click one of the examples.

Without `make`, run `uv sync --locked` and then
`uv run --locked uvicorn talnaspor.app:app`.

## What you can ask

Questions can be in Icelandic or English. Answers are in Icelandic.

| Topic | Examples | Source table |
|---|---|---|
| Inflation and the consumer price index | *Hver er verðbólgan núna?* · *Verðbólga án húsnæðis í mars 2026* · *Hver var mánaðarbreyting vísitölu neysluverðs í ágúst 2026?* · *What was the consumer price index in June 2025?* | [VIS01000](https://px.hagstofa.is/pxis/pxweb/is/Efnahagur/Efnahagur__visitolur__1_vnv__1_vnv/VIS01000.px), by month |
| Population | *Hvað búa margir á Íslandi?* · *Hver var mannfjöldinn í fyrra?* · *Hver var fjölgun íbúa árið 2024?* · *Hve margir aðfluttir umfram brottflutta 2023?* | [MAN00000](https://px.hagstofa.is/pxis/pxweb/is/Ibuar/Ibuar__mannfjoldi__1_yfirlit__Yfirlit_mannfjolda/MAN00000.px), by year |
| Change over time | *How has Iceland's population changed?* · *Verðbólga í september 2025 og 2026* · *Hvernig hefur mannfjöldinn breyst frá 2000?* | Either table |
| Anything else | *Hversu margir eru atvinnulausir á Íslandi?* · *Hver er munurinn á launum karla og kvenna?* · *How many tourists visit Iceland?* | The 5 best-matching of all 2,102 tables, with links |

- **CPI measures:** the index level, monthly change and annual change (inflation), with
  or without housing.
- **Population measures:** population on 1 January, growth (number and %), net
  migration and natural increase.
- **Periods:** a named month or year, the latest published period when none is given,
  "last year" for population, or two periods to compare.
- **Comparisons:** a change in a percentage is reported in percentage points. Levels such
  as population also get the relative change.

For topics without a direct answer, Talnaspor suggests the best-matching official tables,
with links and the date each was last updated. It does not read figures from those
tables, so it cannot misread them. When a question is ambiguous, Talnaspor asks for
clarification instead of guessing. When a figure has not been published (Statistics Iceland marks it `..`), it
says so instead of substituting another period.

## How it works

```
question ─▶ interpret ─▶ table metadata ─▶ validated query ─▶ PX-Web API
                                                                    │
answer card ◀─ Icelandic template ◀─ verified observation ◀─ JSON-stat2 decoder
```

1. **Interpret** ([interpret.py](src/talnaspor/interpret.py)): normalizes the text (case,
   accents, þ, æ, ð), then uses keyword rules to choose a table, a measure and the
   periods. Nothing is guessed: missing or ambiguous details lead to a clarification.
2. **Validate** ([query.py](src/talnaspor/query.py), [pxweb.py](src/talnaspor/pxweb.py)):
   fetches the table's metadata and accepts only dimension codes and values that the
   table actually defines.
3. **Retrieve** ([pxweb.py](src/talnaspor/pxweb.py)): posts the query to PX-Web and
   requests JSON-stat2.
4. **Verify** ([jsonstat.py](src/talnaspor/jsonstat.py)): rejects any response that
   does not answer exactly the query sent: wrong dimensions, substituted categories,
   wrong shape, missing or non-numeric values.
5. **Present** ([answer.py](src/talnaspor/answer.py), [tables.py](src/talnaspor/tables.py)):
   formats numbers in Icelandic style without rounding away any digit Statistics Iceland
   reported, and attaches the unit, period, source, table title and a link to the table.

Questions on other topics are matched against a catalog of every table
([catalog.py](src/talnaspor/catalog.py)). Statistics Iceland's API search is not
enabled, so [scripts/build_catalog.py](scripts/build_catalog.py) crawls the full table
tree, in Icelandic and English, into
[src/talnaspor/data/catalog.json](src/talnaspor/data/catalog.json). Matching tolerates
Icelandic inflection, weights rare words higher and prefers tables that are still updated.

The browser page ([index.html](src/talnaspor/static/index.html)) is a single file with no
external scripts or fonts. Each answer card shows the figure, the source sentence, a link
to the table, the response time, and the exact query sent to Statistics Iceland, so
anyone can check the answer at the source.

### API

`POST /ask` takes `{"question": "..."}` and returns one of four statuses:

| `status` | Meaning | HTTP |
|---|---|---|
| `answer` | A verified figure in `answer`, or a change between two periods in `comparison` | 200 |
| `suggestions` | No direct answer; the best-matching official tables are in `tables` | 200 |
| `clarification` | The question needs more detail; `message` says what | 200 |
| `refusal` | The figure could not be verified, such as unpublished data; the reason is in `detail` | 200 |
| `error` | Statistics Iceland could not be reached | 502 |

```sh
curl -X POST http://127.0.0.1:8000/ask -H 'Content-Type: application/json' \
     -d '{"question": "Hver er verðbólgan núna?"}'
```

Interactive API documentation is at <http://127.0.0.1:8000/docs>.

## Evaluation

[evaluation/questions.json](evaluation/questions.json) holds 43 realistic questions. Each
expected figure was fetched by
[scripts/fetch_expected.py](scripts/fetch_expected.py), which shares no code with
Talnaspor's table configuration, query builder or decoder, and uses a different response
format.

```sh
make evaluate    # Ask every question live and write evaluation/results.md
```

Latest run: **41 pass, 2 documented limitations, 0 failures**, including 7 questions
where the expected table must be among those suggested. See
[evaluation/results.md](evaluation/results.md). Every question's interpretation is also
checked offline by `make check`.

## Known limitations

- **Direct answers from two tables.** Only the consumer price index and key population
  figures are answered with a figure. Other topics get table suggestions. Adding a
  table means adding its configuration to [tables.py](src/talnaspor/tables.py) and
  keywords to [interpret.py](src/talnaspor/interpret.py).
- **Suggestions use word matching.** They can miss a table described with different
  words, and they reflect the catalog as of its last crawl, which
  `scripts/build_catalog.py` refreshes.
- **Keyword rules.** Unusual phrasing gets a clarification rather than an answer.
- **Relative periods.** "Last year" works for population. Others, such as
  "síðustu fimm ár" or "last month", get a clarification instead of an answer.
- **Two periods at most.** There are no time series or charts.
- **Icelandic answers only,** including for questions asked in English.
- **The latest year is incomplete for population.** Only the 1 January figure is
  published for the current year, so other measures for that year are refused.
- **Live data only.** Talnaspor needs network access to px.hagstofa.is.

## Runtime and data

- **Software:** Python with FastAPI, Uvicorn, Requests, Pydantic and pandas, all free
  and open-source. No paid or hosted services and no language models are used at
  runtime. The only external service contacted is Statistics Iceland's public API.
- **Data:** Statistics Iceland (Hagstofa Íslands), retrieved live from
  [px.hagstofa.is](https://px.hagstofa.is).
- **Design decision:** [docs/adr/001-separate-retrieval.md](docs/adr/001-separate-retrieval.md).
- **Licence:** [MIT](LICENSE). Talnaspor is free to use, modify and share.

## Development

```sh
make sync          # Install the project and development tools from uv.lock
make run           # Start the server at http://127.0.0.1:8000 (API docs at /docs)
make evaluate      # Ask the evaluation questions live; write evaluation/results.md
make check         # Check the lockfile, lint, formatting, types, and tests
make format        # Format Python code
make typecheck     # Type-check source and tests with mypy
make test          # Run tests
make build         # Create source and wheel distributions in dist/
make clean         # Remove generated artifacts and caches; preserve .venv
make distclean     # Also remove .venv; run make sync to start again
```

Run `make help` for every target. Pass pytest options with, for example,
`make test PYTEST_ARGS='-q -k query'`. The tests run offline, using real Statistics
Iceland responses saved in [tests/fixtures](tests/fixtures).
`scripts/capture_fixtures.py` refreshes them, and `scripts/build_catalog.py` refreshes
the table catalog (takes several minutes).
