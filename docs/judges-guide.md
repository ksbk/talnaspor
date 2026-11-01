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

## What the evidence shows

See [the README's evaluation section](../README.md#evaluation). In brief: no wrong figures
in the latest recorded runs of the development, understanding and external question sets,
but limited numerical coverage of broader phrasing; most other questions get a safe
non-answer. All three sets were used during development, so none is an unseen test.
