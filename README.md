# Talnaspor

Ask a question about Icelandic statistics, in Icelandic or English, and get the official
figure from Statistics Iceland (Hagstofa Íslands), together with exactly where it came from.

Built for Track 2 (direct PX-Web API) of Statistics Iceland's Gagnaþon 2026.

> **Hver er verðbólgan núna?**
> Vísitala neysluverðs, ársbreyting í október 2026: 5,9%. Heimild: Hagstofa Íslands,
> Vísitala neysluverðs og breytingar, grunnur 1988=100.

## What problem does it solve?

Statistics Iceland publishes about 2,100 tables. Finding one number means knowing which
table holds it and then choosing a value for every one of its dimensions (period, sex, age,
region, unit and so on). Talnaspor does that from a plain question. It shows the figure, its
unit and period, the source table and every value it selected, so anyone can check the
answer against the official source.

When Talnaspor cannot settle a question, it does not guess. It asks for the missing
detail, points to the tables that probably hold the answer, or says that the figure is not
available.

## What can it do?

- **Curated answers** for inflation and the consumer price index (table `VIS01000`) and
  for key population figures (`MAN00000`), with tailored wording and units. It handles
  named months and years, the latest period, comparisons of two periods and spans such as
  "síðustu tíu árin".
- **Catalog answers** from any of the 2,102 tables, but only when the question settles
  every dimension of the table. Each such answer is labelled as selected automatically and
  lists the values chosen.
- **Suggestions** of the best-matching tables, with links, when no table can be settled.
- **Clarifications** when a question is ambiguous or incomplete, and **refusals** when a
  period lies outside the table or a figure is unpublished (marked `..`).
- **Short follow-ups** such as *What about women?* or *En í Reykjavík?*. The answer shows
  how the follow-up was understood.
- **Two languages.** The **ÍS / EN** switch sets the language of the interface and answers.
  English answers use Statistics Iceland's own English labels and table titles.

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

**With [uv](https://docs.astral.sh/uv/)**:

```sh
make sync    # Install exact dependency versions from uv.lock
make run     # Start the server (auto-reloads on file changes)
```

Then open <http://127.0.0.1:8000>. Interactive API documentation is at
<http://127.0.0.1:8000/docs>. Talnaspor runs locally; there is no hosted version.

## Example questions

| Question | Answer (as of 31 October 2026) | Table |
|---|---|---|
| *Hver var verðbólgan í september 2026?* | 5,9% | `VIS01000` |
| *How many people live in Iceland?* | 394,324 people (1 January 2026) | `MAN00000` |
| *What is the population of Reykjavík in 2026?* | 139,804 | `MAN03270` (catalog) |
| *Hvernig breyttist atvinnuleysi frá 2020 til 2025?* | -2,0 prósentustig (6,3 → 4,3) | `VIN00911` (catalog) |
| *Inflation in September 2025 and 2026* | +1.8 percentage points (4.1% → 5.9%) | `VIS01000` |
| *Hver var verðbólgan árið 2024?* | Asks which month | |
| *Hver var mannfjöldinn árið 1650?* | Refuses: the table covers 1703 to 2026 | `MAN00000` |
| *How many tourists visit Iceland?* | Suggests five tables, with links | |

Figures change when Statistics Iceland publishes new data. The answer card always shows the
period. [docs/judges-guide.md](docs/judges-guide.md) is a short guided demonstration.

## How it works

```text
question ─▶ interpret ─▶ table metadata ─▶ validated query ─▶ PX-Web API
                                                                    │
answer card ◀─ ÍS/EN template ◀─ verified observation ◀─ JSON-stat2 decoder
```

1. **Interpret.** Explicit rules normalize the text and choose a table, a value for every
   dimension and the periods. For other topics, a saved catalog of every table is searched,
   and a planner settles each dimension by rule: the period asked for, a category the
   question names, otherwise the table's total. If a dimension stays open, or a word in the
   question is not accounted for, Talnaspor clarifies or suggests tables instead.
2. **Validate.** Every selected code must exist in the table's metadata, fetched from
   Statistics Iceland, or no query is sent.
3. **Retrieve.** The query is posted to the PX-Web API, which returns JSON-stat2.
4. **Verify.** A response is rejected unless it answers exactly the query sent: the same
   dimensions and codes, the expected shape, and a real number.
5. **Present.** Fixed Icelandic and English templates give the figure without rounding away
   reported digits, with its unit, period, source table and link.

**No language model at runtime.** Interpretation and query planning are deterministic code
in this repository. Every figure shown is a value returned by Statistics Iceland for the
validated query. The remaining risk is interpretation, that is, choosing the wrong table
or category. For that reason every answer shows its selections and is evaluated below.

For a step-by-step walk-through, see [docs/how-it-works.md](docs/how-it-works.md). The
design decision is recorded in
[docs/adr/001-separate-retrieval.md](docs/adr/001-separate-retrieval.md).

## Data sources and traceability

- **All figures** come live from Statistics Iceland's public PX-Web API at
  [px.hagstofa.is](https://px.hagstofa.is). No other data source is used.
- **Every answer card** shows the source table with a link to it, the period, the unit
  Statistics Iceland states, and the response time. **About the data** lists every
  dimension, with its label and code, and the exact query sent.
- **Catalog answers** are marked "selected automatically" and list each chosen value.
- **The table catalog** ([src/talnaspor/data/catalog.json](src/talnaspor/data/catalog.json))
  holds the titles and folders of all 2,102 tables in Icelandic and English. It was built
  by [scripts/build_catalog.py](scripts/build_catalog.py) because the API's own search is
  not enabled. It is a snapshot of the table list, not of the data.

## Evaluation

The evaluations below measure different things. None of them is an unseen, independent
test: each was used during development.

| Evaluation | What it measures | Latest result | Status |
|---|---|---|---|
| [Curated development set](evaluation/results.md) | Correctness on 65 realistic questions written during development, with expected values fetched independently ([scripts/fetch_expected.py](scripts/fetch_expected.py)) | Last checked-in run, 30 October 2026, covering 62 of the 65 questions: **61 pass, 1 known limitation, 0 failures**. All 48 numerical answers (curated, comparison and catalog) matched. | Development set. The run predates the current code and 3 later questions. |
| [Understanding set](evaluation/understanding-results.md) | Broader phrasing: paraphrases, restrictions, comparisons, follow-ups and questions that must not be answered (30 questions) | 31 October 2026: **0 wrong answers**. Correct answers to 6 of 13 answerable development questions and 4 of 13 answerable holdout questions; the other 16 answerable questions got safe non-answers. All 4 questions that must not be answered got no figure. | The holdout half was scored at checkpoints during development, and one holdout case influenced a fix. |
| [External question evaluation](evaluation/external-question-evaluation.md) | 60 bilingual, source-backed example questions published in the Gagnaþon 2026 Track 3 starter repository | First run: 9 correct, 47 safe non-answers, 4 wrong. After the fixes, on the same questions: **16 correct answers, 44 safe non-answers (clarification, suggestions or refusal), 0 wrong answers**. Both 31 October 2026. | The first run shaped the fixes and the same questions were reused, so no longer unseen. |

Three quantities matter, and they differ. **Wrong answers** (a figure that does not match
the source) were 0 in the latest recorded run of every set. **Numerical answer coverage** is
limited beyond the curated set: correct figures for 10 of 26 answerable understanding
questions and 16 of 60 external questions. **Safe non-answers** (a clarification,
suggestions or a refusal) make up the rest. They give no figure, so they are not counted as
correct, but they are not wrong. Coverage, not correctness, is the main weakness. The
results do not show that arbitrary questions are answered correctly. A fresh evaluation on
questions never seen during development has not yet been run.

[evaluation/heldout.json](evaluation/heldout.json) holds 16 further questions, used to
compare interpreters. Defects it revealed in the catalog planner were fixed when it was
added, so it is not an untouched test either.

Offline, `make check` runs 587 tests against real saved Statistics Iceland responses,
including a check of every curated question's interpretation. `make evaluate` re-runs the
curated set live. It is slow and can trigger Statistics Iceland's request limit, so do not
run it shortly before a demonstration.

## Known limitations

- **Coverage.** Outside inflation and population, many questions get a clarification or
  suggestions instead of an answer. Unusual phrasing gets a clarification.
- **Catalog units can be general.** A catalog answer uses the unit the table states, which
  can be general, such as "Fjöldi/hlutfall" (number/percent). Check the selected values to
  see which one is shown.
- **One figure or two periods.** No time series, charts, ratios or calculations across
  tables. A question that asks two things is told to ask one at a time.
- **Relative periods.** "Last year" (population) and spans such as "síðustu fimm ár" work.
  "Last month" and "ten years ago" get a clarification.
- **Follow-ups in a few fixed forms**: a sex, an age group, a year or a place.
- **Table search uses word matching.** It can miss a table described in other words, and
  it reflects the catalog as of its last crawl.
- **English depends on Statistics Iceland's English tables.** A table without an English
  version keeps its Icelandic labels, and says so.
- **Current-year population.** Only the 1 January figure is published for the current
  year, so other measures for that year are refused.
- **Live data only.** Talnaspor needs px.hagstofa.is, which limits requests per network
  address (HTTP 429). Identical requests are cached for an hour and a refused request is
  retried once. Beyond that, Talnaspor reports that Statistics Iceland is limiting requests.

## API

`POST /ask` takes `{"question": "...", "lang": "is"}` (`lang` is `is` or `en`) and returns:

| `status` | Meaning | HTTP |
|---|---|---|
| `answer` | A verified figure in `answer` (`kind` is `curated` or `catalog`), or a change between two periods in `comparison` | 200 |
| `suggestions` | No direct answer. The best-matching tables are in `tables`. | 200 |
| `clarification` | The question needs more detail. `message` says what. | 200 |
| `refusal` | No verified figure. `reason` is `unavailable`, `unpublished` or `unverified`. | 200 |
| `error` | Statistics Iceland could not be reached (502) or is limiting requests (503), or an unexpected failure occurred (500) | 502 / 503 / 500 |

```sh
curl -X POST http://127.0.0.1:8000/ask -H 'Content-Type: application/json' \
     -d '{"question": "Hver er verðbólgan núna?"}'
```

`POST /ask/batch` takes up to 10 questions, `{"questions": [...], "lang": "is"}`. It returns
one `/ask` response per question, each with its own status.

## Development

```sh
make sync          # Install the project and development tools from uv.lock
make check         # Lockfile, lint, formatting, types and tests (offline)
make test          # Tests only; pass options with PYTEST_ARGS='-q -k query'
make evaluate      # Re-run the curated set live; writes evaluation/results.md (slow)
make help          # Every target
```

`scripts/capture_fixtures.py` refreshes the saved test responses, and
`scripts/build_catalog.py` refreshes the table catalog (several minutes).

## Technology, AI use and licence

- **Software:** Python, FastAPI, Uvicorn, Requests, Pydantic and pandas, all free and
  open-source. The browser page is one HTML file with no external scripts or fonts.
- **Runtime independence:** the only external service contacted is Statistics Iceland's
  API. [runtime.py](src/talnaspor/runtime.py) refuses any other address and any redirect,
  and switches off telemetry export. It cannot stop a library from opening its own
  connections or a proxy set with `HTTPS_PROXY`; that needs network-level controls.
- **Language model:** none at runtime. A local open-weight model (Qwen3 8B through Ollama)
  was tested for rewording missed questions. It added one answer on the held-out
  questions, below the agreed bar, so it is not part of this build.
- **Development:** Talnaspor was written with the help of AI coding assistants (Claude Code
  and Codex). The team directed and reviewed the work.
- **Licence:** [MIT](LICENSE).
