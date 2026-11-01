# Talnaspor: a five-minute guide for judges

## Start it

```sh
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app
```

Open <http://127.0.0.1:8000>. Talnaspor needs network access to px.hagstofa.is. Ask
questions about 30 seconds apart: Statistics Iceland limits requests per network address.

## Four questions to try

Values as of 31 October 2026. A figure changes only when Statistics Iceland publishes new
data, and the card always shows the period.

| # | Language | Question | Expected | Table | Shows |
|---|---|---|---|---|---|
| 1 | ÍS | Hver var verðbólgan í september 2026? | **5,9%** | `VIS01000` (Mánuður `2026M09`, Vísitala `CPI`, Liður `change_A`) | A curated answer |
| 2 | EN | How many people live in Iceland? | **394,324 people** (1 January 2026) | `MAN00000` | English, Statistics Iceland's own labels |
| 3 | EN | What is the population of Reykjavík in 2026? | **139,804** | `MAN03270` | An answer from any of the 2,102 tables, marked as selected automatically |
| 4 | EN | What is the population of Iceland in 2026? then **What about women?** | **191,927** | `MAN00101` (Kyn `2`) | A follow-up, with "Understood as a follow-up …" |

## A clarification

*Hver var verðbólgan árið 2024?* → "Tilgreindu mánuð, til dæmis „verðbólga í september
2026“." Inflation is published by month, so Talnaspor asks which month instead of choosing
one.

## A known limitation

*Hver var verðbólgan í síðasta mánuði?* gets a clarification instead of an answer. "Last
month" could mean the calendar month or the latest published month, and Talnaspor does not
guess. More generally, many questions outside inflation and population get suggestions of
tables rather than a figure, and a catalog unit can be general, such as "Fjöldi/hlutfall".

## Checking an answer at the source

- **Source** under each figure links to the Statistics Iceland table it came from.
- **About the data** (Nánar um gögnin) lists every dimension of that table, with its label
  and code, and the exact query sent to the API. Pick the same values on the table's page
  at px.hagstofa.is to see the same figure.
- Catalog answers also list the selected values in a yellow note above the source.

## How it maps to the judging criteria

*Provisional:* these criteria are the team's reading of the Gagnaþon brief, not an official
rubric.

| Criterion | What to show |
|---|---|
| Functionality | Verified values, and the refusals |
| Presentation | The answer card |
| Usability | Example questions, clarifications, two languages |
| Clarity | Unit, period, source link, selections |
| Deployment | `pip install -r requirements.txt` and `uvicorn app:app` from a fresh clone |
| User value | One figure from 2,102 tables, with its source |

**The honest weak spot.** Talnaspor uses no language model at runtime. It interprets
questions with deterministic rules and retrieves every figure directly from the PX-Web API.
The rules only choose codes; they do not generate numbers. The cost is coverage: phrasing
the rules do not recognise gets a clarification or suggestions. A language model could be a
later step, proposing codes that pass through the same validation (steps 5 and 7 of [how-it-works.md](how-it-works.md#2-one-question-step-by-step)).

## What the evidence shows

See [the evaluation summary](how-it-works.md#7-evaluation). In brief: no wrong figures
in the latest recorded runs of the development, understanding and external question sets,
but limited numerical coverage of broader phrasing; most other questions get a safe
non-answer. All three sets were used during development, so none is an unseen test.

## Beyond the hackathon

The current build is deliberately narrow: two curated tables, cautious catalog answers and
no runtime language model. [roadmap.md](roadmap.md) sets out planned work, none of it
implemented yet. Its primary direction is a hybrid architecture in which a locally hosted
open-weight language model proposes a structured reading of the question, and an
independent verification stage checks it against the question and Statistics Iceland's
metadata before any figure is retrieved. The current rules remain the baseline and the
fallback. The roadmap also covers near-term engineering, such as a live-versus-recorded
indicator and reproducible evaluation reports, and an independently controlled benchmark.
