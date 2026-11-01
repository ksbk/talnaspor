# Talnaspor

Ask a question about Icelandic statistics, in Icelandic or English, and get the official
figure from Statistics Iceland (Hagstofa Íslands), together with exactly where it came from.

Built for Track 2 (direct PX-Web API) of Statistics Iceland's Gagnaþon 2026.

> **Hver er verðbólgan núna?**
> Vísitala neysluverðs, ársbreyting í október 2026: 5,9%. Heimild: Hagstofa Íslands,
> Vísitala neysluverðs og breytingar, grunnur 1988=100.

## Why

Statistics Iceland publishes about 2,100 tables. Finding one number means knowing which
table holds it and choosing a value for every one of its dimensions (period, sex, age,
region, unit and so on). Talnaspor does that from a plain question. It shows the figure,
its unit and period, the source table and every value it selected, so anyone can check the
answer at the source.

When Talnaspor cannot settle a question, it does not guess. It asks for the missing
detail, points to the tables that probably hold the answer, or says that the figure is not
available.

## What it can do

- **Curated answers** for inflation and the consumer price index (`VIS01000`) and key
  population figures (`MAN00000`): named or latest periods, two-period comparisons and
  spans such as "síðustu tíu árin".
- **Catalog answers** from any of the 2,102 tables, only when the question settles every
  dimension of the table. These are marked as selected automatically and list each value.
- **Suggestions, clarifications and refusals** when no table can be settled, a question is
  incomplete, or a figure is outside the table or unpublished.
- **Short follow-ups** such as *What about women?*, shown as understood.
- **Icelandic and English**, switched with **ÍS / EN**, using Statistics Iceland's own
  English labels.

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

Then open <http://127.0.0.1:8000>. With [uv](https://docs.astral.sh/uv/), `make sync`
and `make run` do the same. Talnaspor runs locally; there is no hosted version.

## Example questions

| Question | Answer (as of 31 October 2026) | Table |
|---|---|---|
| *Hver var verðbólgan í september 2026?* | 5,9% | `VIS01000` |
| *What is the population of Reykjavík in 2026?* | 139,804 | `MAN03270` (catalog) |
| *Hvernig breyttist atvinnuleysi frá 2020 til 2025?* | -2,0 prósentustig (6,3 → 4,3) | `VIN00911` (catalog) |
| *Hver var verðbólgan árið 2024?* | Asks which month | |

Figures change when Statistics Iceland publishes new data; the answer card always shows the
period. For a guided demonstration, see [docs/judges-guide.md](docs/judges-guide.md).

## How it works

```text
question ─▶ interpret ─▶ table metadata ─▶ validated query ─▶ PX-Web API
                                                                    │
answer card ◀─ ÍS/EN template ◀─ verified observation ◀─ JSON-stat2 decoder
```

Explicit rules turn the question into one value for every dimension of one table. Each
value must exist in the table's metadata, or no query is sent. The response is accepted
only if it answers exactly that query, and the figure is shown with its unit, period,
source link and the selections made.

**No language model runs at runtime.** Interpretation and planning are deterministic code,
and every figure is a value returned by Statistics Iceland. The remaining risk is choosing
the wrong table or category, which is why every answer shows its selections.

## Evaluation and limitations

Talnaspor gave **no wrong figures** in the latest recorded run of each evaluation set:

- 65 curated development questions: the last checked-in run covers 62 of them and predates
  the current code.
- 30 understanding questions.
- 60 external example questions from the Gagnaþon 2026 Track 3 starter repository: 16
  correct and 44 safe non-answers, after fixes prompted by an earlier run on the same
  questions (9 correct, 4 wrong).

**Coverage is the main weakness.** Beyond inflation and population, many questions get a
clarification or suggestions instead of a figure. Catalog units can be general, such as
"Fjöldi/hlutfall". Talnaspor gives one figure or two periods, with no time series or
ratios. Every set above was used during development, so none is an unseen test, and the
results do not show that arbitrary questions are answered correctly. See the
[evaluation summary](docs/how-it-works.md#7-evaluation) and the
[full list of limitations](docs/how-it-works.md#8-known-limitations).

## Future development

The primary planned direction, not part of this submission, is a hybrid architecture: a
local open-weight language model proposes how to read the question, and independent
verification and Statistics Iceland's data decide what is answered, with today's rules as
baseline and fallback. Details and other planned work are in [docs/roadmap.md](docs/roadmap.md).

## Documentation

- [How it works](docs/how-it-works.md): architecture, evaluation, limitations, runtime
  safeguards, API and development
- [Judges' guide](docs/judges-guide.md): a five-minute guided demonstration
- [Roadmap](docs/roadmap.md): planned work

## Technology and licence

Python, FastAPI, Uvicorn, Requests, Pydantic and pandas, all open-source. The only external
service contacted is Statistics Iceland's API. Talnaspor was written with the help of AI
coding assistants (Claude Code and Codex); the team directed and reviewed the work.
Licensed under [MIT](LICENSE).
