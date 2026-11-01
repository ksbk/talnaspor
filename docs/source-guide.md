# Source guide: what every file does

A file-by-file reference to the code, for answering questions about the architecture.
[How it works](how-it-works.md) explains the ideas. This guide says where each one is
implemented, and what each file does and does not do.

Checked against `main` at `1461067`, 1 November 2026.

## Contents

1. [The whole system on one page](#1-the-whole-system-on-one-page)
2. [The life of one request](#2-the-life-of-one-request)
3. [The application package: src/talnaspor](#3-the-application-package-srctalnaspor)
4. [Scripts](#4-scripts)
5. [Tests](#5-tests)
6. [Evaluation files](#6-evaluation-files)
7. [Configuration and project files](#7-configuration-and-project-files)
8. [Where to look when asked](#8-where-to-look-when-asked)

---

## 1. The whole system on one page

```text
browser (static/index.html)
   │  POST /ask {question, lang, previous}
   ▼
app.py ── follow-ups, pre-checks, routing, every reply's status
   │
   ├─ curated route ─ interpret.py  (CPI and population rules → table + selections)
   │                    └ answer.py  (retrieve, check, word the answer)
   │                         uses tables.py (hand-configured tables, units, templates)
   │
   └─ catalog route ─ catalog.py   (search catalog.json for candidate tables)
                        └ planner.py (accept or reject each candidate; settle every
                                      dimension; retrieve; word the answer)
   both routes, for every number:
        pxweb.py    get metadata / post query (only to px.hagstofa.is; cache; retry)
          └ runtime.py   (which addresses and settings are allowed)
        query.py    build the query: every dimension, only allowed codes
          └ validation.py (refuse a code the table does not have)
        jsonstat.py check the JSON-stat2 response against the query; read the cells
```

**Module imports** (who uses whom; there are no cycles):

| Module | Imports from |
|---|---|
| `app.py` | `answer`, `catalog`, `interpret`, `jsonstat`, `planner`, `pxweb`, `runtime`, `validation` |
| `planner.py` | `answer`, `catalog`, `interpret`, `jsonstat`, `pxweb`, `query` |
| `answer.py` | `jsonstat`, `pxweb`, `query`, `tables` |
| `catalog.py` | `interpret` (only `normalize`) |
| `interpret.py` | `answer` (only `LATEST`, `before_latest`) |
| `query.py` | `pxweb` (`PXMetadata`), `validation` |
| `pxweb.py` | `runtime` |
| `jsonstat.py`, `tables.py`, `validation.py`, `runtime.py` | nothing in the package |

**What is deterministic:** everything. No language model, no randomness, no learned
weights. The same question and the same Statistics Iceland data give the same reply.

---

## 2. The life of one request

Example: *"Hvernig breyttist atvinnuleysi frá 2020 til 2025?"* (catalog route).

| Step | File and function | What happens |
|---|---|---|
| 1 | `static/index.html` `ask()` | The page posts `{question, lang}`, plus `previous` (the last answered question), to `/ask`. |
| 2 | `app.py` `ask()` → `safely_respond_to()` | Catches any unexpected exception, so the reply is always JSON. Checks whether this is a follow-up (`interpret.follow_up`). It is not. |
| 3 | `app.py` `respond_to()` | Pre-checks: two questions in one (`SEVERAL_QUESTIONS`), a series or chart (`interpret.SERIES`), an impossible year (`interpret.invalid_year`). None apply. |
| 4 | `interpret.interpret()` | Looks for CPI or population words. None are found, so it returns a `Clarification` with `recognized=False`. |
| 5 | `app.py` | Not recognized and not general knowledge, so it searches the catalog: `catalog.search(question, limit=10)`. |
| 6 | `planner.comparison_span()` | Finds two years: `Span("2020", "2025")`. Then come the guards: a zero or negative duration, "last year", other relative periods, and a change word with no period. None apply. |
| 7 | `app.candidates()` | Orders the candidates: hand-pinned primary tables first, then the top five (shorter title first on equal scores), then the best tables for the rarest word. Removes the excluded table. |
| 8 | `planner.plan_comparison()` | Tries up to 12 current candidates. **VIN01002** passes the word and title checks and every dimension is settled, but `measure_kind()` returns `None` (mixed unit, no "%" in the label), so it is skipped. **VIN00911** passes. |
| 9 | `query.build_query()` → `pxweb.get_data()` → `jsonstat.decode_jsonstat()` | Builds one query with both years. Every code must be in the metadata. The response must match the query exactly. |
| 10 | `pxweb.get_units()` | Requests the same query in PX format to read its `UNITS`: "Fjöldi/hlutfall". |
| 11 | `planner.plan_comparison()` | Computes the difference with exact decimals, −2.0. Uses percentage points because the selected label contains "%". Builds the text, the `Comparison` and its selections. |
| 12 | `app.respond_to()` | Returns `status="answer"` with the comparison and up to four other tables. |
| 13 | `static/index.html` `renderComparison()` | Shows both values, the change, the source link and "About the data" (every dimension, its label and code, and the exact query). |

A curated question, such as *"Hver var verðbólgan í september 2026?"*, takes a different
path from step 4: `interpret()` returns an `Interpretation` (`VIS01000`, month `2026M09`,
CPI, annual change). `curated_terms_cover()` confirms that every word is understood.
`answer.answer()` then retrieves, checks and words it.

---

## 3. The application package: src/talnaspor

### `app.py`: the web application and the router

**Role:** the FastAPI application. It receives questions, decides which route answers
them, turns every outcome (including failures) into a typed JSON reply, and serves the
page.

**Endpoints:**

| Endpoint | Function | Purpose |
|---|---|---|
| `GET /` | `index()` | Serves `static/index.html`. |
| `POST /ask` | `ask()` | One question. Returns HTTP 200, except errors: 503 rate limited, 500 unexpected, 502 Statistics Iceland unreachable. |
| `POST /ask/batch` | `ask_batch()` | Up to 10 questions (`MAX_BATCH`), answered one after another, each with its own status. |
| `GET /docs` | FastAPI | Interactive API documentation. |

**Request and reply models:**
- `AskRequest`: `question` (1–500 characters), `lang` (`is` or `en`), `previous`.
- `AskResponse`:
  - `status`: answer, suggestions, clarification, refusal or error;
  - `message`, `answer` or `comparison`, `tables`;
  - `reason`: unavailable, unpublished, unverified, rate_limited or unexpected;
  - `understood_as`, `elapsed_ms`.

**Key functions:**
- `safely_respond_to()`: the outer guard.
  - Handles follow-ups: `follow_up()`, then `narrow()`, then answering the narrowed question, which sets `understood_as`.
  - A follow-up with no previous question gets a clarification.
  - Turns any unexpected exception into `status="error"`, `reason="unexpected"`.
- `respond_to()`: the router. In order:
  1. Pre-checks: `SEVERAL_QUESTIONS`, `SERIES`, `invalid_year`.
  2. `interpret()`.
  3. The **curated gate**. If `interpret()` succeeded but `curated_terms_cover()` finds a word the curated rules do not know (e.g. "Reykjavík"), the question goes to the catalog instead.
  4. On the catalog route, in order:
     - `GENERAL_KNOWLEDGE` (e.g. "capital of Iceland") gets "not found";
     - `search()`;
     - `invalid_duration`;
     - "last year" is rewritten to the previous calendar year;
     - an unsupported relative period gets `RELATIVE_MESSAGE`;
     - a change with no periods and no named change measure (`NAMED_CHANGE`) gets `COMPARE_YEARS`;
     - `candidates()`;
     - `plan_comparison()` if there is a span, otherwise `plan_answer()`, with `attempts=12`.
  5. On the curated route: `compare()` or `answer()`, with each exception mapped to a reply:

     | Exception | Reply |
     |---|---|
     | `RateLimited` | error, `rate_limited` |
     | `RequestException` | error |
     | `UnavailableValue` | refusal, `unavailable` (states the range the table covers) |
     | `MissingValue` | refusal, `unpublished` |
     | other `ValueError` | refusal, `unverified` |

- `candidates()`: builds the order in which catalog tables are tried (see step 7 above).

**Hand-curated constants (be ready to explain):**
- `PRIMARY_TABLES`: questions about immigrants, births or the population try their primary table (`MAN43000`, `MAN05101`, `MAN00101`) first. It still has to pass every planner check.
- `EXCLUDED_TABLES`: `MAN43005`, titled "Innflytjendur…", also counts the second generation (85,577 against 77,226 immigrants), so it never answers.
- `NAMED_CHANGE`: "annual change", "árleg…" and similar name one period's figure, not a comparison.
- `CALENDAR_LAST_YEAR`: "last year" or "í fyrra" means the previous calendar year.

**Startup safeguards:** `check_environment(os.environ)` runs at import and stops the
server on unsafe model settings. `FastAPI(..., telemetry={"auto_configure": False})`
turns telemetry export off.

**Does not:** compute statistics, build queries or contact Statistics Iceland itself.

---

### `interpret.py`: the curated rules and the shared language helpers

**Role:** two jobs.
1. **Curated interpretation:** maps a CPI or population question to the configured table and a complete set of selections, or a `Clarification`.
2. **Shared helpers used by the catalog route:**
   - `normalize` (lower-case; þ→th, æ→ae, ð→d; strip accents);
   - period patterns;
   - follow-up handling.

**Data types:**
- `Interpretation(table, selections, compare_from)`: `compare_from` set means a comparison.
- `Clarification(message, message_en, recognized)`: `recognized=False` means "not a curated topic", which sends the question to the catalog.

**Main flow, `interpret(question)`:**
1. Finds topic words (`CPI_WORDS`, `POPULATION_WORDS`).
   - Both topics: "one topic at a time".
   - Neither: not recognized.
2. Refuses invalid periods: `invalid_duration` (zero or negative) and `invalid_year` (not four digits from 1000 to 2999).
3. Reads periods:
   - spans ("síðustu fimm ár", "the last decade");
   - "years ago";
   - "last year";
   - named years and months (`_months` pairs each month with the year that follows it).
4. Refuses conflicts rather than dropping one part:
   - a year plus a span: `ONE_PERIOD`;
   - an unsupported relative period: `RELATIVE_MESSAGE`;
   - a month for the population: `POPULATION_MONTH`;
   - a period the question states but the rules did not use: `RELATIVE_MESSAGE`.
5. `_interpret_cpi()`:
   - measure: monthly change `change_M`, annual change `change_A` (inflation), or `index`;
   - CPI or CPI excluding housing (`CPILH`);
   - "change" with only the index named: asks monthly or annual.
6. `_interpret_population()`: measure `0`–`4` (population, % growth, growth, net immigration, natural increase).
7. `_with_periods()` completes the selections:
   - one period, or two (a comparison);
   - a span back from the latest period;
   - **a change with no periods returns `COMPARE_YEARS` / `COMPARE_MONTHS`**, and is never given a span the user did not state.

**Other public helpers:**

| Helper | Used by | Purpose |
|---|---|---|
| `curated_terms_cover(words)` | `app.py` | The curated gate: every content word must start with a known stem (`CURATED_STEMS`). |
| `follow_up(question)` | `app.py` | "What about women?", "En í Reykjavík?" give the restriction; anything else gives `None`. |
| `narrow(previous, restriction)` | `app.py` | Replaces or adds a sex, year, age group or place in the previous question. |
| `relative_period`, `invalid_duration`, `invalid_year`, `without_periods`, `name_spans`, `month_periods` | `app.py`, `planner.py` | Period checks shared with the catalog route. |
| `CHANGE`, `SINCE`, `SPAN`, `SERIES`, `START_OF_YEAR`, `MONTH_WORDS`, `NUMBERS` | `app.py`, `planner.py` | Shared patterns. |

**Does not:** contact Statistics Iceland or know anything about catalog tables.

---

### `catalog.py`: table discovery

**Role:** loads `data/catalog.json` and ranks tables for a question by weighted word
matching. **It proposes candidates; it never decides an answer.**

**How `search(question, limit=5, minimum_score=3.0)` ranks:**
1. **Terms.** `question_words()` normalizes the text and drops `STOPWORDS` (question words, "Iceland", "change", …), digits and words of two letters or fewer. `related_phrases()` adds title words from the 29 `RELATED_TERMS` rules (e.g. "unemploy" → "atvinnuleysi").
2. **Index** (`_index()`, cached). Each table becomes a bag of words from its Icelandic and English titles (weight 1.0) and folder names (0.5). Each word gets an IDF weight, log(tables ÷ tables containing the word), so rarer words count more.
3. **Matching** (`_match()`). Two word forms match fully if they are equal, or if one is a prefix of the other covering at least 60% of the longer word. They match partly (0.6) if they share at least 4 leading letters covering 60% of the shorter word. This is **prefix matching, not stemming or lemmatization**.
4. **Score.** For each term, a table adds its best matching word: idf × field weight × match quality.
5. **Rank.** The score is multiplied by 0.85 if the table was not updated since 2022 (`CURRENT_SINCE`). Scores below 3.0 are dropped. Ties are broken by update date. The top `limit` are returned (the app asks for 10).

**Other functions:**
- `topic_word()`: the question word matching the fewest tables, used for a second search in `app.candidates()`. It ignores sex words (`CATEGORY_TERMS`).
- `table(path)`: looks up one catalog entry (used for the primary tables).
- `is_current()`: updated since 2022.
- `TableHit`: what a search returns, with page and API links.

**Does not:** contact Statistics Iceland, read table dimensions or check anything. The
catalog contains descriptions, not data.

---

### `planner.py`: catalog planning, retrieval and answers

**Role:** the core of the catalog route. For each candidate table it decides **accept or
reject**, settles every dimension by explicit rules, retrieves the cells, and words the
answer or comparison.

**Entry points:**
- `plan_answer(question, hits, attempts, lang)`: one value. Returns an `Answer`, a `Choice` or `None`.
- `plan_comparison(question, hits, span, attempts, lang)`: two periods. Returns a `Comparison`, a `Choice` or `None`.
- `comparison_span(question)`: returns a `Span` for two months, two years, "since YEAR" with a change word, or a span of years ("síðustu fimm ár"). Otherwise `None`.

**Checks for each candidate (failing one skips the table):**

| Check | Function | Rule |
|---|---|---|
| Current | `is_current`; `RECENT_YEARS` | Updated since 2022. Without a stated year, the latest period is at most 2 years old. |
| Has a time dimension | `_time_variable` | Marked as time in the metadata, or a known time code with period-shaped values. |
| Every word accounted for | `_accounts_for` | Every question word must appear, directly or through a related term, in the titles, folders, dimension names or category labels (Icelandic and English). |
| Title restriction | `_accounts_for` | A title "X - …" whose X is two words or fewer (e.g. "Námsmenn - …") needs the question to name X. |
| Topic in the title | `_names_topic` | At least one question word fully matches a title word. |
| No hidden sum | `_counts_together` | A title joining "A og B" (or "A and B"), with no dimension separating them, is skipped if the question names only one of them. |
| Every dimension settled | `select`, `_settle` | See below. If a dimension is unsettled, the table is skipped. |
| One cell or two | after `decode_jsonstat` | Exactly 1 observation, or 2 for a comparison. |
| No accounting codes | `CODED_LABEL` | Labels like "00-00-00 …" are rejected. |
| Clear measure (comparisons only) | `measure_kind` | The measure must be a percent, an index or a level, read from the label ("%", "Vísitala") or the unit. A mixed unit ("Fjöldi/hlutfall") with no "%" in the label means unclear, so the table is skipped. |

**How `_settle()` chooses a dimension's value, in order:**
1. The dimension has only one value: take it.
2. A category is named by question words, in either language. The strongest match wins, the question's own words outweigh related terms, and among ties the total is dropped. "First born" categories need the word (`QUALIFIED`).
3. The single total: `TOTALS` ("Alls", "Samtals", "Total", …).
4. If there is no total: the labour force survey's 16–74 age group (`SURVEY_TOTALS`).
5. If there is still none: the index level (`LEVELS`, "Vísitala").
6. Otherwise unsettled.

Time is settled by `select()`: the requested month, or the latest period in the requested
year, or the latest period.

**Choice:** if no candidate answers, and a candidate had exactly one unsettled dimension
with at most 8 options (`MAX_OPTIONS`), the user is offered that choice (`Choice.message`).

**English:** `_english()` fetches the table's English metadata. `_aligned()` uses its
labels only where the value codes match the Icelandic ones exactly. A table with no
English version answers in Icelandic labels and says so.

**Comparisons:**
- Both periods come from **one query**, so every non-time selection is identical.
- The difference uses exact decimals.
- Percentages are reported in percentage points; indexes in index points and percent; levels as a difference and percent.

**Caches:** metadata for 1 hour (`METADATA_SECONDS`). Network errors and `ValueError` on
one table skip that table. `RateLimited` stops the search, because further requests would
also be refused.

**Does not:** detect when two passing tables would disagree (the first to pass answers),
or judge whether a total is statistically appropriate.

---

### `query.py`: query construction

**Role:** `build_query(metadata, selections)` turns selections into a PX-Web query.
- The selections must cover **exactly** the table's dimensions (no missing, no extra).
- Each dimension has one value or a list of distinct values.
- Every value is checked with `validation.validate_value`.
- The response format is `json-stat2`.

**Raises:** `ValueError` (incomplete or repeated selections), or `UnavailableValue` (a
code the table does not have).

### `validation.py`: allowed values

**Role:** `validate_value()` returns the code if the table allows it. Otherwise it raises
**`UnavailableValue`**, which carries the requested value and the first and last allowed
labels. That lets the app reply "the table covers 1703 to 2026".

### `pxweb.py`: the only door to Statistics Iceland

**Role:** every HTTP request goes through `_send()`.

**Models:** `PXVariable` and `PXMetadata`. `PXMetadata` validates on load:
- at least one dimension;
- unique dimension codes;
- every dimension has values, none duplicated;
- labels and values have equal length.

**`_send()`:**
1. `runtime.check_px_url()` refuses any address but the PX-Web API over HTTPS.
2. Redirects are not followed, and a redirect raises `RuntimePolicyError`.
3. Identical requests are cached for an hour (`CACHE_SECONDS`).
4. An HTTP 429 is retried once after `Retry-After`, capped at 3 seconds. A second 429 raises **`RateLimited`**.

**Functions:**
- `get_metadata()`: GET, 15 s timeout.
- `get_data()`: POST the query, 20 s timeout.
- `get_units()`: POSTs the same query in PX format to read `UNITS` / `UNITS[en]`, because JSON-stat2 carries no units. A category-specific unit takes precedence.
- `clear_cache()`.

### `jsonstat.py`: response verification

**Role:** `decode_jsonstat(text, query)` reads a JSON-stat2 response **and checks that it
answers exactly the query**:
- dimension ids, and their order, equal the query's;
- sizes and dimension metadata are consistent;
- each dimension's categories are exactly the requested codes, with consistent positions and labels;
- the number of values equals the product of the dimension sizes.

A blank value raises **`MissingValue`** with the status marker (".." means not
published). Non-finite values are rejected. It returns a `StatData` holding
`Observation`s (value, codes, labels, status), the dataset source, dimension labels and
the table's decimals.

**Does not:** know whether the requested cells were the right ones.

### `answer.py`: curated answers, models and formatting

**Role:**
1. The reply models shared by both routes: `Answer`, `Comparison`, `Point`.
2. Curated retrieval:
   - `answer()` returns one value;
   - `compare()` returns two periods;
   - `_retrieve()` resolves `latest` / `latest-N` against the table's newest period (`shift_period`), builds the query, fetches it and checks the response.
3. Formatting:
   - `format_value()`: Icelandic 1.234,5 / English 1,234.5. It never drops reported digits.
   - `format_period()`: 2026M09 becomes "september 2026" / "September 2026", and quarters are handled too.
   - The `WORDS` vocabulary.

Curated answers fill the templates in `tables.py` and add Statistics Iceland's status note
when there is one.

### `tables.py`: the hand-configured tables

**Role:** the two curated tables, as data.
- **`cpi`:** `VIS01000`, time "Mánuður", measures `index` (stig), `change_M` and `change_A` (%).
- **`population`:** `MAN00000`, time "Ár", measures `0` population, `1` growth %, `2` growth, `3` net immigration, `4` natural increase.

For each table: the API and page links in both languages, the English title, the unit and
sentence template for each measure in both languages, and Statistics Iceland's English
labels (`labels_en`).

### `runtime.py`: network and model policy

**Role:**
- `check_px_url()`: only `https://px.hagstofa.is` on the paths `/pxis/api/v1/is/` or `/pxen/api/v1/en/`. No other port and no credentials.
- `check_environment()`: if set, `OLLAMA_URL` must be a loopback address, and `TALNASPOR_LLM_MODEL` must not be a "cloud" model or a provider-prefixed model. These settings only matter for a possible later local model; **the released application runs no model.**

**Not covered:** a proxy set with `HTTPS_PROXY`, or a library opening its own
connections (see [how-it-works.md §9](how-it-works.md#9-runtime-independence-and-ai-use)).

### `data/catalog.json`

A dated snapshot (crawled 2026-10-30) of **2,102 tables**, 1,777 with an English title.
Each record holds `path`, `title`, `folders`, `title_en`, `folders_en` and `updated`.
**No observations.** It is built by `scripts/build_catalog.py`.

### `static/index.html`

The whole browser interface in one file: HTML, CSS and JavaScript, with no external
scripts or fonts.
- **Language switch** (ÍS/EN), remembered in `localStorage` (`talnaspor-lang`).
- **`ask()`:** posts to `/ask` with `previous` = the last question that got an answer or suggestions (`understood_as` when it was a follow-up). Clarifications and errors are never context.
- **Rendering:** `renderAnswer()`, `renderComparison()`, `renderSuggestions()`, plus clarification, refusal and error messages, a retry button on errors, and a response-time footer.
- **"About the data"** (`aboutData()`): the table link, every dimension with its label and code, and the exact query sent.
- **Example questions:** eight per language, folded away until "Explore example questions" is clicked. They are checked by `tests/test_startup_examples.py` and `tests/test_page_examples.py`.

### `__init__.py`

Empty. It marks the package.

---

## 4. Scripts

| Script | What it does | Network |
|---|---|---|
| `build_catalog.py` | Walks the Icelandic and English PX-Web trees depth-first (0.35 s pause; backs off and retries on 429), joins them on table path, and writes `data/catalog.json` with its crawl date. Its docstring records that the API's search function is not enabled on px.hagstofa.is. | Live |
| `evaluate.py` | Asks every question in `evaluation/questions.json` through `/ask` and compares with the stored expected values. Writes `evaluation/results.md` (PASS / FAIL / STALE). `make evaluate`. | Live |
| `fetch_expected.py` | Fetches the expected values **independently of Talnaspor**: hand-written URLs and queries, and PX-Web's legacy `json` format instead of JSON-stat2. `--write` stores them. | Live |
| `evaluate_understanding.py` | Scores `evaluation/understanding.json` (CORRECT / SAFE / WRONG / ERROR) and writes `understanding-results.md`. Reports only the totals for the holdout split. Its `recorded()` wrapper saves and replays every PX-Web response in `evaluation/recordings/`. `make understanding` (offline). | Recorded |
| `serve_recorded.py` | Serves the app on port 8001 from the recordings: the demo backup. `--record` records new questions live. | Recorded |
| `capture_fixtures.py` | Saves CPI and population metadata and data into `tests/fixtures/is/`. | Live |
| `capture_cpi.py` | Saves one English CPI response (`tests/fixtures/cpi_2026m09.json`) used in developing the decoder. | Live |

---

## 5. Tests

`make check` runs lock and requirements checks, Ruff (lint and format), strict mypy, and
pytest. Latest offline run, 1 November 2026: **648 passed, 2 xfailed**. The two xfails
are strict and record known limitations.

| File | Tests | What it proves |
|---|---|---|
| `conftest.py` | — | Empties the PX-Web cache around every test. |
| `test_answer.py` | 20 | Curated answers and comparisons, number and period formatting, `latest` resolution, units and templates. |
| `test_app.py` | 46 | The router end to end: statuses, HTTP codes, follow-ups, the curated gate, refusals, batch, rate limiting, unexpected errors. |
| `test_catalog.py` | 6 | Search finds the expected tables, nothing for unrelated questions, page links, current tables preferred, inflection matching. |
| `test_interpret.py` | 27 | The curated rules: topics, measures, periods, spans, clarifications. |
| `test_jsonstat.py` | 5 | Response verification: decodes a real CPI response, maps values by category position, rejects a corrupted response, a response for a different query, and non-JSON. |
| `test_page_examples.py` | 5 | Runs the page's own script in Node (`page_harness.js`): examples folded, toggle, language switch, a click asks the question. Skipped without Node. |
| `test_planner.py` | 34 | Dimension settling, totals and fallbacks, the word and title checks, choices, comparisons, measure kinds. |
| `test_pxweb.py` | 9 | Metadata validated on load (inconsistent metadata rejected), queries submitted, HTTP errors propagated, the 429 retry and `RateLimited`, the cache. |
| `test_query.py` | 9 | Every dimension required, distinct values, unavailable codes. |
| `test_questions.py` | 3 | Every question in `questions.json` is interpreted as recorded (expanded once per question). |
| `test_runtime.py` | 9 | Only Statistics Iceland's API is allowed, refused before anything is sent; redirects refused; a refused request fails closed; local-only model settings; the server will not start with a remote model endpoint. |
| `test_semantic_safety.py` | 10 | Unsupported time requests and undated changes get a clarification with no request and no planning. Stated periods are kept. Includes the strict xfail ("unemployment change in 2024"). |
| `test_startup_examples.py` | 2 | Each of the 16 example questions gives its documented figure from the recordings (expanded once per example). |
| `test_validation.py` | 3 | `validate_value` and `UnavailableValue`. |
| `fixtures/` | — | Saved PX-Web responses for offline tests. |

The "Tests" column counts test functions; parametrized tests expand into many cases.

---

## 6. Evaluation files

| File | Contents |
|---|---|
| `evaluation/questions.json` | 65 curated development questions with expected results. Changed expectations carry `changed` and `previous` fields. |
| `evaluation/results.md` | The last checked-in live run (30 Oct 2026): 62 of 65 questions, 61 pass, 1 known limitation. |
| `evaluation/understanding.json` | 30 broader questions, split into development and holdout halves. |
| `evaluation/understanding-results.md` | The 31 Oct 2026 scores (holdout reported as totals only). |
| `evaluation/heldout.json` | 16 adversarial questions. **Protected**: not opened during this work. |
| `evaluation/external-question-evaluation.md` | The 60 Gagnaþon Track 3 starter questions: first run and after fixes. |
| `evaluation/recordings/` | Saved PX-Web responses, one file per request, named by a SHA-256 hash of method, URL and body. Used by offline tests, the understanding evaluation and the demo backup. |

---

## 7. Configuration and project files

| File | Purpose |
|---|---|
| `app.py` (repository root) | Makes `uvicorn app:app` work from the root after `pip install -r requirements.txt`, as in the organizers' setup. It only imports `talnaspor.app`. |
| `pyproject.toml` | Package metadata, dependencies, and Ruff (line length 100), strict mypy and pytest settings. Python ≥ 3.10. |
| `uv.lock` | Exact dependency versions. |
| `requirements.txt` | Pinned runtime dependencies for pip, generated from `uv.lock` (`make requirements`). |
| `Makefile` | `sync`, `run`, `check`, `test`, `lint`, `typecheck`, `evaluate`, `understanding`, `requirements`, `clean`, … (`make help`). |
| `docs/adr/001-separate-retrieval.md` | The founding decision: keep discovery, planning, retrieval, interpretation and presentation separate, and take numbers only from source data. |
| `README.md`, `docs/how-it-works.md`, `docs/examples.md`, `docs/judges-guide.md`, `docs/roadmap.md` | The user, technical, judge and future-work documentation. |

**Runtime dependencies:** FastAPI, Uvicorn, Requests and Pydantic. `pandas` is also listed
in `pyproject.toml` and the documentation, but no code in `src`, `scripts` or `tests`
imports it.

---

## 8. Where to look when asked

| Question | Answer in |
|---|---|
| How is a question routed? | `app.respond_to()` |
| Why did a question go to the catalog, not the curated answers? | `interpret.curated_terms_cover()` (the curated gate) |
| How are candidate tables found and ranked? | `catalog.search()`, `_match()`, `_index()` |
| In what order are candidates tried? | `app.candidates()` |
| Why was a table rejected? | `planner._accounts_for()`, `_names_topic()`, `_counts_together()`, `select()`, `measure_kind()` |
| How is each dimension's value chosen? | `planner._settle()` |
| How is "unemployment rate" picked as the measure? | `planner._settle()`: the category label matches the question's words |
| How are periods read? | `interpret.interpret()` (curated); `planner.comparison_span()` and `select()` (catalog) |
| Why does an undated change get a clarification? | `interpret._with_periods()` (curated); the `COMPARE_YEARS` guard in `app.respond_to()` (catalog) |
| How is the query checked? | `query.build_query()`, `validation.validate_value()` |
| How is the response checked? | `jsonstat.decode_jsonstat()` |
| Where do units come from? | `tables.py` (curated); `pxweb.get_units()` (catalog) |
| Why percentage points? | `answer.compare()` (unit "%"); `planner.measure_kind()` (catalog) |
| What if the figure is unpublished or the year is out of range? | `jsonstat.MissingValue`, `validation.UnavailableValue`, mapped in `app.respond_to()` |
| What stops requests to other servers? | `runtime.check_px_url()`, called by `pxweb._send()` |
| How are rate limits handled? | `pxweb._send()` (cache, one retry, `RateLimited`) |
| How do follow-ups work? | `interpret.follow_up()`, `narrow()`; `app.safely_respond_to()`; the page's `lastQuestion` |
| Is there a language model? | No. `runtime.check_environment()` only guards settings for a possible future local model |
| How is the catalog built, and how fresh is it? | `scripts/build_catalog.py`; the `crawled` field in `catalog.json` (2026-10-30) |
| How are the evaluations run? | `scripts/evaluate.py`, `evaluate_understanding.py`, `fetch_expected.py`; [how-it-works.md §7](how-it-works.md#7-evaluation) |
