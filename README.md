# Talnaspor

A chatbot that answers everyday questions about Icelandic statistics with official
figures from Statistics Iceland (Hagstofa Íslands), and shows exactly where every
number came from.

Built for Track 2 (direct PX-Web API) of Statistics Iceland's Gagnaþon 2026.

> **Hver er verðbólgan núna?**
> Vísitala neysluverðs, ársbreyting í október 2026: 5,9%. Heimild: Hagstofa Íslands,
> Vísitala neysluverðs og breytingar, grunnur 1988=100.

For other topics, Talnaspor searches all 2,102 tables Statistics Iceland publishes. It
answers from the best-matching table when the question settles every one of that
table's dimensions, and otherwise points to the tables that hold the answer.

Every figure is retrieved live from [px.hagstofa.is](https://px.hagstofa.is) and checked
against the exact query that was sent. Talnaspor uses **no language model at runtime**:
questions are interpreted by explicit rules, and answers are filled into fixed templates,
so a number can never be invented.

The interface and answers are in Icelandic or English, switched with **ÍS / EN** in the
page. English answers use Statistics Iceland's own English labels and table titles.

## Quick start

Requires Python 3.10 or later and network access to px.hagstofa.is.

```sh
git clone https://github.com/ksbk/talnaspor.git
cd talnaspor
```

**With pip** (the organizers' Track 2 setup):

```sh
python3 -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate
pip install -r requirements.txt    # Exact versions, exported from uv.lock
uvicorn app:app
```

**With [uv](https://docs.astral.sh/uv/)** and make:

```sh
make sync    # Install exact dependency versions from uv.lock
make run     # Start the server
```

Then open <http://127.0.0.1:8000> and ask a question, or click one of the examples.

## What you can ask

Questions can be in Icelandic or English, whichever language the page is set to. Answers,
clarifications and the interface follow the **ÍS / EN** switch.

| Topic | Examples | Source table |
|---|---|---|
| Inflation and the consumer price index | *Hver er verðbólgan núna?* · *Verðbólga án húsnæðis í mars 2026* · *Hver var mánaðarbreyting vísitölu neysluverðs í ágúst 2026?* · *What was the consumer price index in June 2025?* | [VIS01000](https://px.hagstofa.is/pxis/pxweb/is/Efnahagur/Efnahagur__visitolur__1_vnv__1_vnv/VIS01000.px), by month |
| Population | *Hvað búa margir á Íslandi?* · *Hver var mannfjöldinn í fyrra?* · *Hver var fjölgun íbúa árið 2024?* · *Hve margir aðfluttir umfram brottflutta 2023?* | [MAN00000](https://px.hagstofa.is/pxis/pxweb/is/Ibuar/Ibuar__mannfjoldi__1_yfirlit__Yfirlit_mannfjolda/MAN00000.px), by year |
| Change over time | *How has Iceland's population changed?* · *Verðbólga í september 2025 og 2026* · *Hvernig hefur mannfjöldinn breyst frá 2000?* | Either table |
| Other topics, answered | *Hversu margir eru atvinnulausir á Íslandi?* · *Hver er munurinn á launum karla og kvenna?* · *What is the unemployment rate?* · *Hver er kosningaþátttaka?* · *Hver er landsframleiðslan?* | The best-matching of all 2,102 tables |
| Other topics, found | *How many tourists visit Iceland?* · *Hvað eru margir bílar á Íslandi?* | The 5 best-matching tables, with links |

- **CPI measures:** the index level, monthly change and annual change (inflation), with
  or without housing.
- **Population measures:** population on 1 January, growth (number and %), net
  migration and natural increase.
- **Periods:** a named month or year, the latest published period when none is given,
  "last year" for population, two periods to compare, or a span back from the latest
  period ("síðustu tíu árin", "the last 6 months").
- **Comparisons:** a change in a percentage is reported in percentage points. Levels such
  as population also get the relative change. Catalog tables compare two periods too, but
  only when the unit or the selected category says whether the measure is a percentage,
  an index or a count.
- **Follow-ups:** a short follow-up such as *What about women?*, *En hjá körlum?*, *And in
  2020?* or *En í Reykjavík?* narrows the previous question, and the answer shows how it
  was understood. Without a previous question, Talnaspor asks for the whole question.

For other topics, answers from a catalog table are marked as selected automatically and
list every value chosen, so they can be checked. When one choice is missing, such as a
count or a percentage, Talnaspor names the options and asks again. Otherwise it suggests
the best-matching official tables, with links and the date each was last updated. When a question is ambiguous, Talnaspor asks for
clarification instead of guessing. When a figure has not been published (Statistics Iceland marks it `..`), it
says so instead of substituting another period.

## How it works

```
question ─▶ interpret ─▶ table metadata ─▶ validated query ─▶ PX-Web API
                                                                    │
answer card ◀─ ÍS/EN template ◀─ verified observation ◀─ JSON-stat2 decoder
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

The planner ([planner.py](src/talnaspor/planner.py)) then tries the best tables in turn.
It answers only when every dimension is settled by explicit rules: the year asked about
or the latest period (which must be recent); a category the question names; otherwise
the dimension's total ("Alls", "Samtals"). It skips a table instead of guessing when a
dimension remains open, when a word in the question is not accounted for by the table
(so a restriction such as "kvenna" is never ignored), or when the title limits the table
to a group the question does not mention. The unit comes from the table itself.

The browser page ([index.html](src/talnaspor/static/index.html)) is a single file with no
external scripts or fonts. Each answer card shows the figure, the source sentence, a link
to the table, the response time, and the exact query sent to Statistics Iceland, so
anyone can check the answer at the source.

### API

`POST /ask` takes `{"question": "...", "lang": "is"}` (`lang` is `is` or `en`, default
`is`) and returns one of five statuses:

| `status` | Meaning | HTTP |
|---|---|---|
| `answer` | A verified figure in `answer` (`kind` is `curated` or `catalog`), or a change between two periods in `comparison` | 200 |
| `suggestions` | No direct answer; the best-matching official tables are in `tables`, and `message` names any choice needed | 200 |
| `clarification` | The question needs more detail; `message` says what | 200 |
| `refusal` | No verified figure: `reason` is `unavailable` (outside the table's range, which `message` states), `unpublished` (marked `..`) or `unverified`; technical detail is in `detail` | 200 |
| `error` | Statistics Iceland could not be reached | 502 |

```sh
curl -X POST http://127.0.0.1:8000/ask -H 'Content-Type: application/json' \
     -d '{"question": "Hver er verðbólgan núna?"}'
```

`POST /ask/batch` takes up to 10 questions, `{"questions": ["...", "..."], "lang": "is"}`,
and returns
`{"answers": [...]}`: one `/ask` response per question, in order. Each has its own
status, so a question that fails does not fail the others, and the call returns 200.

```sh
curl -X POST http://127.0.0.1:8000/ask/batch -H 'Content-Type: application/json' \
     -d '{"questions": ["Hver er verðbólgan núna?", "Hvað búa margir á Íslandi?"]}'
```

Interactive API documentation is at <http://127.0.0.1:8000/docs>.

## Evaluation

[evaluation/questions.json](evaluation/questions.json) holds 65 realistic questions, 13 of
them answered in English. Each
expected figure was fetched by
[scripts/fetch_expected.py](scripts/fetch_expected.py), which shares no code with
Talnaspor's table configuration, query builder or decoder, and uses a different response
format.

```sh
make evaluate    # Ask every question live and write evaluation/results.md (slow)
```

Latest full run, on 31 October 2026: **64 of 65 pass, 1 documented limitation, 0
failures**. This includes 14 answers
from catalog tables, each checked for the table, period and figure (and, in Icelandic,
every selected value), 4 refusals, and 3 questions where the expected table must be
among those suggested. See
[evaluation/results.md](evaluation/results.md). The script pauses between questions, but
Statistics Iceland's request limit can still interrupt it; run it well before a demo.
[evaluation/heldout.json](evaluation/heldout.json) holds 16 further questions, never used to
tune the rules, for comparing interpreters. Every question's interpretation is also
checked offline by `make check`.

[evaluation/understanding.json](evaluation/understanding.json) holds 30 questions written
before the changes they measure (paraphrases, restrictions, comparisons, follow-ups and
questions that must be refused), half of them held out from development. Every response
is recorded, so `make understanding` replays it offline. Latest: no wrong answers; 6 of 13
answerable development questions and 4 of 13 held-out ones answered (2 of 13 each before),
and all 4 that must be refused refused. See
[evaluation/understanding-results.md](evaluation/understanding-results.md). One expected
value was wrong until 31 October: an immigrants table that also counts the second
generation was accepted for “How many immigrants live in Iceland?”. The external check
below found it; Talnaspor's answer was then wrong too, and is now fixed.

**External check.** The Gagnaþon Track 3 starter's 60 bilingual, source-backed questions:
16 correct, 44 safe (clarification, suggestions or refusal) and 0 wrong, from 9 correct and
4 wrong before the fixes it prompted. Questions that ask two things or need a ratio are
refused. See [evaluation/track3-results.md](evaluation/track3-results.md).

## Known limitations

- **Curated answers from two tables.** The consumer price index and key population figures
  have tailored wording, units and comparisons. Adding one means adding its configuration
  to [tables.py](src/talnaspor/tables.py) and keywords to
  [interpret.py](src/talnaspor/interpret.py).
- **Catalog answers are cautious.** They give one figure, or a comparison of two periods
  when the measure's kind is clear, with the unit Statistics Iceland states for the table,
  which can be general ("Fjöldi/hlutfall"). Many questions get a choice or suggestions
  instead of an answer.
- **Suggestions use word matching.** They can miss a table described with different
  words, and they reflect the catalog as of its last crawl, which
  `scripts/build_catalog.py` refreshes.
- **Keyword rules.** Unusual phrasing gets a clarification rather than an answer. A local
  language model (Qwen3 8B) that reworded missed questions was tested on the held-out
  questions; it added one answer, below the agreed bar, so it is not included.
- **Follow-ups in a few fixed forms.** A sex, an age group, a year or a place; anything
  else is treated as a new question.
- **Relative periods.** "Last year" (population) and spans such as "síðustu fimm ár"
  work. "Last month" and "ten years ago" get a clarification instead of an answer.
- **Two periods at most.** There are no time series or charts.
- **English depends on Statistics Iceland's English tables.** Catalog answers from a table
  without an English version keep its Icelandic labels and say so. In English table
  suggestions, the top-level folder name stays in Icelandic.
- **The latest year is incomplete for population.** Only the 1 January figure is
  published for the current year, so other measures for that year are refused.
- **Live data only.** Talnaspor needs network access to px.hagstofa.is, which limits
  requests per network address (HTTP 429), sometimes for minutes after heavy use.
  Identical requests are cached for an hour and a refused request is retried once;
  beyond that, Talnaspor says Statistics Iceland is limiting requests.
- **Curated answers are national headline figures.** A question naming anything they do
  not cover, such as a town, a sub-index or another country, is passed to the table
  search instead, which answers only if a table settles every word.

## Runtime and data

- **Software:** Python with FastAPI, Uvicorn, Requests, Pydantic and pandas, all free
  and open-source. No paid or hosted services and no language models are used at
  runtime. The only external service contacted is Statistics Iceland's public API.
- **Data:** Statistics Iceland (Hagstofa Íslands), retrieved live from
  [px.hagstofa.is](https://px.hagstofa.is).
- **Step-by-step guide:** [docs/how-it-works.md](docs/how-it-works.md) traces a question
  through the data, interpretation, query and verification.
- **Design decision:** [docs/adr/001-separate-retrieval.md](docs/adr/001-separate-retrieval.md).
- **Licence:** [MIT](LICENSE). Talnaspor is free to use, modify and share.

## Development and runtime independence

- **Development:** Talnaspor was developed with the help of AI coding assistants, Claude
  Code and Codex, which assisted in writing, testing and reviewing the code. The team
  directed and reviewed the work.
- **Runtime:** the competition build interprets questions, plans queries, validates them,
  calculates changes and formats answers with deterministic code in this repository. It
  performs no language-model inference. It runs on open-source software (Python,
  FastAPI, Uvicorn, Requests, Pydantic).
- **Data:** every statistical observation comes from Statistics Iceland's PX-Web API.
- **Optional local model:** local inference with the open-weight Qwen3 8B through Ollama
  was evaluated experimentally; it added one held-out answer, below the agreed bar, and
  is not part of the competition build.

Enforced in code ([runtime.py](src/talnaspor/runtime.py)):

- Every request goes through one function, which refuses any address other than
  `https://px.hagstofa.is/pxis/api/v1/is/…` or `…/pxen/api/v1/en/…`, and any redirect.
  A refused request is a logged error, never an answer.
- The server does not start if `OLLAMA_URL` points anywhere but this machine, or if
  `TALNASPOR_LLM_MODEL` names a hosted ("cloud") model or another provider's model.
- Telemetry export is switched off, whatever `OTEL_*` environment variables say.

Not enforced in code: a library opening its own connections, or a proxy set with
`HTTPS_PROXY`. Those need network-level controls, such as a firewall that allows only
px.hagstofa.is.

**Before enabling a local model (after the competition):** call the model only through
an endpoint taken from `runtime.py`, so the startup checks apply; pin the model by digest
and check with `ollama show` that it runs locally; refuse redirects from Ollama as from
PX-Web; deploy with an egress firewall that allows only px.hagstofa.is and loopback; and
merge only after it passes the held-out evaluation criteria.

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
