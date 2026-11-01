# How Talnaspor works

A study guide: the data, how a question is interpreted, how the query is built and
checked, and why the answers can be trusted.

**The mental model in one sentence:** a question becomes a filled-in form for one Statistics
Iceland table, with exactly one value chosen for every column, and only Statistics Iceland
supplies the number. Everything else in the system exists to fill that form correctly, or
to refuse when it cannot.

## 1. The data: what a Statistics Iceland table is

PX-Web holds about **2,102 tables** in a folder tree, organised into six databases
(Atvinnuvegir, Efnahagur, Íbúar, Samfélag, Sögulegar hagtölur, Umhverfi).

Each table is a **cube**: a few *dimensions* (variables), and one number for every
combination of their values. The consumer price index table `VIS01000`:

| Dimension | Values (code → label) |
|---|---|
| `Mánuður` (month) | 462 values: `1988M05` … `2026M10` |
| `Vísitala` (which index) | `CPI` → Vísitala neysluverðs, `CPILH` → Vísitala neysluverðs án húsnæðis |
| `Liður` (which measure) | `index` → Vísitala, `change_M` → Mánaðarbreyting, %, `change_A` → Ársbreyting, % … |

That is 462 × 2 × 6 ≈ 5,500 cells. “Inflation in September 2026” is exactly one cell:
(`2026M09`, `CPI`, `change_A`).

Two API calls do all the work:

- **GET** the table URL returns its **metadata**: the dimensions and their allowed codes,
  the menu.
- **POST** a query, one selection per dimension, returns the matching cells.

The response format, **JSON-stat2**: `id` lists the dimensions in order, `size` how many
values each has, and `value` is a flat list of numbers. Talnaspor asks for one value per
dimension, so `size` is `[1, 1, 1]` and `value` is `[5.9]`.

Three quirks shape the design:

- **No unit in the JSON formats.** The unit is read from the same query in PX format,
  whose `UNITS` keyword says, for example, `Milljónir króna`.
- **Unpublished cells are `null`, marked `..`**, such as population growth for the
  current year.
- **Rate limiting.** Statistics Iceland answers HTTP 429 after a few quick requests from one
  address, sometimes for minutes.

## 2. One question, step by step

Produced from the saved responses in [tests/fixtures/is](../tests/fixtures/is):

| Step | What happens | Code |
|---|---|---|
| 1. Question | “Hver var verðbólgan í september 2026?” | |
| 2. Normalize | Lower case, accents stripped, þ→th, æ→ae, ð→d: `hver var verdbolgan i september 2026?` | [interpret.py](../src/talnaspor/interpret.py) `normalize` |
| 3. Interpret | Rules: *verdbolg* → topic CPI and measure annual change; *september 2026* → `2026M09`. Result: `{Mánuður: 2026M09, Vísitala: CPI, Liður: change_A}` | [interpret.py](../src/talnaspor/interpret.py) |
| 4. Metadata | The table's menu, fetched from Statistics Iceland | [pxweb.py](../src/talnaspor/pxweb.py) `get_metadata` |
| 5. Validate and build | Every selection must be a code in the menu, or no query is sent | [query.py](../src/talnaspor/query.py) `build_query` |
| 6. Retrieve | `POST {"query": [{"code": "Mánuður", "selection": {"filter": "item", "values": ["2026M09"]}}, …], "response": {"format": "json-stat2"}}` | [pxweb.py](../src/talnaspor/pxweb.py) `get_data` |
| 7. Decode and verify | The response must answer exactly the query: same dimensions in order, the same codes, the right shape, a real number (not `null`, not text) | [jsonstat.py](../src/talnaspor/jsonstat.py) |
| 8. Present | A template and Icelandic formatting: “Vísitala neysluverðs, ársbreyting í september 2026: 5,9%. Heimild: …”, with the table link, the selections and the response time | [answer.py](../src/talnaspor/answer.py), [tables.py](../src/talnaspor/tables.py) |

**The key principle:** the language side (step 3) only *chooses codes*. The number comes
only from step 6, and step 7 proves it is the right cell.

## 3. Two routes: curated and catalog

**Curated: CPI and population.** Two tables configured by hand in
[tables.py](../src/talnaspor/tables.py), with known units (íbúar, stig, %), Icelandic and
English sentence templates, Statistics Iceland's official English labels, and comparisons
such as “frá 2015 til 2025” or “síðustu tíu árin”. A change in a percentage is reported in
**percentage points**; a change in a level, such as population, also as a percent.

**Catalog: any other table.**

1. **Find.** Search a saved catalog of every table's title and folders
   ([catalog.py](../src/talnaspor/catalog.py), data in
   [catalog.json](../src/talnaspor/data/catalog.json), built by
   [build_catalog.py](../scripts/build_catalog.py) because the API's own search is not
   enabled). Matching tolerates Icelandic inflection, weights rare words higher and prefers
   tables that are still updated.
2. **Plan.** For the best candidate tables, settle **every** dimension by explicit rules
   ([planner.py](../src/talnaspor/planner.py)):
   - time: the year or month asked about, or the latest period, which must be recent;
   - a dimension with one value: that value;
   - a category the question names: that category (Konur, 16-74 ára);
   - anything else: its total (Alls, Samtals, Allt landið).
3. **Refuse rather than guess.** Skip a table when a dimension cannot be settled, when a
   word in the question is not accounted for by the table, when no question word fully
   matches its title, when the title restricts it to another group (“Námsmenn - …”), or
   when a selected category is an accounting code.

**The gate between the routes.** A curated answer is allowed only if every content word of
the question is one the curated answers understand. “Íbúar í Reykjavík” contains an
unknown word, so it goes to the catalog route, which finds the Reykjavík population table
and answers 139.804, instead of the national 394.324.

## 4. Every possible outcome

| Situation | Reply | Example |
|---|---|---|
| Every column settled | **Answer** with its evidence | “5,9%” |
| Essential information missing | **Clarification** | “Verðbólga árið 2024” → “Tilgreindu mánuð …” |
| One column needs the user's choice | **Choice**, with the table's own options | “… þarf að velja eining: Fjöldi, Hlutfall, %” |
| The topic exists, but no table can be settled | **Suggestions**: up to five tables with links | “How many tourists visit Iceland?” |
| A period outside the table | **Refusal** with the range it covers | “It covers May 1988 to October 2026.” |
| A figure not published (`..`) | **Refusal** saying so | “Hagstofa Íslands hefur ekki birt þessa tölu” |
| Not a statistical question | **Not found** | “What is the capital of Iceland?” |
| Statistics Iceland limiting requests | **An honest error** | “Hagstofa Íslands takmarkar fjölda fyrirspurna …” |

## 5. Language

The ÍS/EN switch decides the reply language; the question can be in either language,
independently of the switch. English answers use Statistics Iceland's own English labels
and table titles, never our own translations of official terms.

## 6. Reliability

Identical requests to Statistics Iceland are cached for an hour, and a refused request
(HTTP 429) is retried once after a short pause. Warming up before a demo therefore means the
demo itself makes no new requests. See [demo-checklist.md](demo-checklist.md).

## 7. Why the numbers can be trusted

- **Offline tests** run against real saved Statistics Iceland responses (`make check`).
- **The evaluation set** ([questions.json](../evaluation/questions.json)) compares answers
  with values fetched by [fetch_expected.py](../scripts/fetch_expected.py), which shares no
  code with Talnaspor and uses a different response format.
- **Further and adversarial questions** ([heldout.json](../evaluation/heldout.json)) found
  real defects, such as the Reykjavík and “capital” cases, which were fixed. Because they
  shaped those fixes, they are not an untouched test; nor are the understanding set's
  holdout half or the [external question evaluation](../evaluation/external-question-evaluation.md),
  which also guided fixes. A test on questions never
  seen during development is still to be done.
- **What this does not prove.** The number shown always comes from Statistics Iceland, but
  the interpretation can still pick the wrong table or category. That is why every answer
  lists its selections, and why many questions get a clarification or suggestions instead.

## 8. How it maps to the judging criteria

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
later step, proposing codes that pass through the same validation (steps 5 and 7).

## 9. Check yourself

1. Why does “Íbúar í Reykjavík” not get the national total?
2. Where does a catalog answer's unit come from?
3. What happens if Statistics Iceland returns `null` for the cell?
4. Why is a change in inflation reported in percentage points, not percent?
5. What stops an answer from the wrong table when a word is ambiguous (“capital”)?
6. Which step would a language model replace, and which would it never replace?

<details>
<summary>Answers</summary>

1. The gate between routes: “Reykjavík” is not a word the curated answers understand, so
   the catalog route answers from the Reykjavík table.
2. From the PX format's `UNITS` keyword, requested with the same query.
3. A refusal saying the figure has not been published.
4. Because inflation is itself a percentage; the difference between two percentages is in
   percentage points.
5. Every question word must be accounted for, a question word must fully match the table's
   title, and general-knowledge questions get “not found”.
6. Only step 3 (interpretation). Never steps 5–7: validation, retrieval and verification.

</details>
