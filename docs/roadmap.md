# Talnaspor roadmap

**Everything in this document is planned work. None of it is implemented in the current
build.** What Talnaspor does today is described in [how-it-works.md](how-it-works.md). What
has been measured, and how, is in [its evaluation section](how-it-works.md#7-evaluation).
Success criteria below are proposed acceptance tests for future work, not results.

**Primary direction.** The main planned direction for future research and development is a
hybrid architecture: a locally hosted, open-weight language model that understands the
question and proposes a structured interpretation, with independent verification and
Statistics Iceland's data deciding what is answered. It is described in
[Target architecture](#target-architecture-local-language-model-with-independent-verification)
and in the [research programme L1–L7](#primary-research-programme-local-language-model).
It is not part of the current build or the Gagnaþon 2026 submission.

## Starting point

The current build answers from two curated tables, inflation and population, and from
catalog tables only when explicit rules settle every dimension. It gave no wrong figures in
the latest recorded run of each development-informed evaluation set. Its main weakness is
coverage: most broader questions get a clarification or suggestions. It cannot calculate
ratios or answer compound questions. No evaluation on questions unseen during development
has been run. No language model runs at runtime; in an earlier experiment, a local
open-weight model (Qwen3 8B) that reworded missed questions added one answer, below the bar
agreed in advance, and was not adopted.

## Principles that future work keeps

1. **Numbers come only from Statistics Iceland.** No component, including a language model,
   may supply a value. Every dimension code is checked against the table's metadata.
2. **A safe non-answer is better than a wrong answer.** A change that adds answers but also
   adds wrong ones is not accepted without an explicit, documented decision.
3. **Coverage and correctness are reported separately**, together with safe non-answers,
   for every evaluation set.
4. **Every evaluation set is labelled** as development-informed or unseen, and a set loses
   "unseen" status the moment its results influence a change.
5. **Language models are local and propose; verification decides.** Any model is an
   open-weight model running on the same machine. Its output is a proposal that must pass
   independent verification against the question and Statistics Iceland's metadata.
6. **Deterministic rules remain.** The current rules stay as the baseline that every new
   method is measured against, and as a fallback path when no model is available or its
   proposal fails verification.

## Target architecture: local language model with independent verification

*Planned. Nothing in this section is implemented.*

```text
user question + dialogue context
        │
        ▼
local multilingual LLM ── intent understanding, structured proposal ◀──┐
        │                                                            │ revise
        ▼                                                            │
catalog and semantic retrieval ── candidate tables ──────────────────┤
        │                                                            │
        ▼                                                            │
statistical dimension resolution ── one value per dimension ─────────┘
        │
════════╪══════════ independent verification boundary ══════════════
        ▼
semantic and numerical verification ── constraints kept? units, time, operation valid?
        │                                  └─ fails ─▶ clarification, suggestions or refusal
        ▼
PX-Web retrieval and verified computations ── figures only from Statistics Iceland
        │
        ▼
evidence-grounded explanation ── every number checked against the verified evidence
```

| Stage | Responsibility | Must not |
|---|---|---|
| Local LLM proposal | Read the question and dialogue context in Icelandic or English; propose a structured interpretation (measure, population, place, time reference, operation) in a fixed schema, with any ambiguity stated | Supply figures or dimension codes that have not been checked against metadata |
| Catalog and semantic retrieval | Find candidate tables from official metadata (see R3) | Treat generated annotations as official metadata |
| Dimension resolution | Map the proposal to one value per dimension of a candidate table | Fill an unresolved constraint with a default without saying so |
| Verification boundary | Check, independently of the model, that every stated constraint is represented, codes exist, and units, time references and operations are compatible (see R4, R5) | Be bypassed: nothing reaches retrieval without passing it |
| Retrieval and computation | Query PX-Web; compute changes, ratios or shares only by verified, displayed formulas | Use any data source other than Statistics Iceland |
| Explanation | Phrase the verified result conversationally in the user's language | Introduce a number, unit, period or claim that is not in the verified evidence |

**Iteration.** The proposal, retrieval and resolution stages may loop: retrieval results
and table metadata can be given back to the model to revise its proposal, for example to
choose between candidate tables or to ask which category was meant. The loop is bounded,
and it ends on the model side of the verification boundary. Verification itself never
asks the model whether a plan is correct.

**Fallback.** When no model is available, when the model times out, or when its proposal
fails verification, the current deterministic rules answer, clarify or refuse exactly as
they do today. The explanation stage falls back to the current fixed templates.

**Schema-valid is not statistically correct.** Constrained decoding can guarantee that a
model's output parses and fits the schema. It cannot guarantee that the proposal means what
the user asked: a well-formed interpretation can name the wrong population, drop a
restriction such as "kvenna", confuse a level with a change, or pick the wrong reference
period. That is why verification is a separate, deterministic stage, and why evaluation
measures semantic correctness, not schema validity.

## Primary research programme: local language model

The research milestones that would build and test the target architecture above. They run
in order where stated, and each ends in a published measurement. The model is adopted for
any stage only if it improves on the deterministic baseline under the reporting standard
below, without raising unsupported-answer risk.

### L1. A test suite for interpretation (D: evaluation)

- **Problem:** existing sets measure final answers, not whether a question was understood.
- **Proposal:** a labelled suite in Icelandic and English, with the expected structured
  interpretation and expected outcome for each question, covering:
  - the same question in both languages (see R2) and several paraphrases of each;
  - follow-up questions, with the dialogue context they depend on;
  - the correct table, or a set of acceptable tables;
  - every dimension's expected value, including stated restrictions that must not be
    dropped;
  - units and measure types (level, change, rate, index);
  - statistical operations: comparisons, percentage changes, ratios and shares;
  - questions that must be clarified or refused, including unsupported operations.
- **Success criterion:** the suite exists with a written labelling guide, double-checked
  labels, and a declared split into development and sealed test questions.
- **Dependencies and risks:** labels need fluent Icelandic and statistical expertise.
  Labels drafted with a model must be reviewed by people before use.

### L2. Choosing candidate models (A, D)

- **Problem:** models differ widely in Icelandic ability, structured output and size.
- **Proposal:** benchmark several multilingual open-weight models on the L1 development
  split, including Qwen-family models at more than one size and models from other
  families, chosen for licence, Icelandic support and local hardware fit. Qwen3 8B, the
  model of the earlier rewording experiment, is one baseline; no model is preferred before
  the results.
- **Success criterion:** a published comparison of interpretation accuracy per field,
  semantic correctness, latency and memory use, per model and size, on stated hardware.
- **Dependencies and risks:** depends on L1. Results on a small set may not generalise;
  model licences must permit the intended use.

### L3. Choosing a local inference runtime (C: deployment)

- **Problem:** the architecture needs reproducible, schema-constrained output from a model
  running on the same machine.
- **Proposal:** evaluate Ollama and at least one alternative local runtime for: structured
  output constrained to a JSON schema or grammar, determinism with fixed settings, model
  pinning by digest, loopback-only serving, and latency. Capabilities are checked by
  experiment, not taken from documentation.
- **Success criterion:** for the chosen runtime, repeated runs on the same input and pinned
  model give identical output, every output parses against the schema, and the existing
  runtime safeguards (loopback-only `OLLAMA_URL`, no hosted models) apply unchanged.
- **Dependencies and risks:** runtimes change quickly; versions must be pinned. Constrained
  decoding can lower answer quality, which L4 measures.

### L4. Structured proposals behind the verification boundary (A, B)

- **Problem:** a proposal is only useful if it can be checked and, when wrong, rejected.
- **Proposal:** define the proposal schema (independent of PX-Web codes), map proposals to
  table dimensions, and run them through the R4 and R5 checks before any query. Compare
  rules only, model only, and model with rule fallback on identical inputs.
- **Success criterion:** on the sealed L1 split, reported separately: numerical answer
  coverage, semantic correctness, unsupported-answer risk and latency. Adoption requires
  higher coverage than the rules with no increase in wrong answers.
- **Dependencies and risks:** depends on L1–L3 and on R4 and R5. Risk that verification is
  too strict to let any gain through, or too loose to catch plausible errors; both are
  measured.

### L5. Iterating between retrieval and proposal (A)

- **Problem:** the right table often depends on what tables exist, which the model does not
  know in advance.
- **Proposal:** give the model the top candidate tables and their dimensions, and let it
  revise its proposal or ask a clarifying question, within a fixed number of rounds.
- **Success criterion:** compared with a single proposal, table and dimension accuracy and
  coverage rise on the sealed split, with latency reported for each number of rounds.
- **Dependencies and risks:** depends on L4 and R3. Each round adds latency and another
  chance of error.

### L6. Follow-ups and dialogue context (A)

- **Problem:** the current build handles follow-ups in a few fixed forms only.
- **Proposal:** pass the previous verified question and answer as context, so the model can
  propose a narrowed or changed interpretation, and show the user how it was understood, as
  the current build does.
- **Success criterion:** on the L1 follow-up questions, correct resolution of what was
  carried over and what changed, reported separately from single questions.
- **Dependencies and risks:** depends on L4. Context can carry over a restriction the user
  meant to drop, so each follow-up states its interpretation.

### L7. Evidence-grounded explanation (C, B)

- **Problem:** fixed templates are reliable but stiff; free text can introduce errors.
- **Proposal:** let the model phrase the answer from a verified evidence record (figures,
  units, periods, selections and source), then check automatically that every number,
  unit and period in the text appears in that record. Text that fails the check is
  replaced by the current template.
- **Success criterion:** on all answered L1 questions, no explanation that passes the check
  contains a figure, unit or period not in the evidence, and the rate of fallback to
  templates is reported.
- **Dependencies and risks:** depends on L4. The check covers numbers and labels, not every
  shade of meaning, so the source and selections stay visible next to the text.

## Near-term engineering

Engineering work that needs no new research. Each item is independent of the others.

### N1. Show whether data is live or recorded (C: user experience)

- **Problem:** in the recorded-response backup mode, the page looks exactly like a live
  session, so the presenter must say so out loud.
- **Proposal:** the server reports its data mode, and the page shows a visible label such
  as "Recorded responses from 31 October 2026" in recorded mode.
- **Success criterion:** a test serves the page in each mode and checks the label; the
  label is visible without scrolling and announced to screen readers.
- **Dependencies and risks:** small change to the recorded-response script and the page.
  Risk: none to answers; the label must never appear in live mode.

### N2. A reproducible evaluation report for each release (B: verification)

- **Problem:** the last checked-in curated report predates the current code and covers 62
  of 65 questions.
- **Proposal:** each release regenerates every evaluation report from recorded responses,
  stamped with the commit, the recording date and the question-set version, and the
  release check fails if a report is older than the code it describes.
- **Success criterion:** from a fresh clone, one offline command reproduces every report
  byte for byte for a tagged release.
- **Dependencies and risks:** recordings must be refreshed live, slowly, because of
  Statistics Iceland's request limit. Recorded data ages; reports must state its date.

### N3. Clearer units and measures in catalog answers (B: verification)

- **Problem:** a catalog table's unit can be general ("Fjöldi/hlutfall"), so a reader must
  check the selections to see whether a figure is a count or a percentage.
- **Proposal:** derive the shown unit from the selected measure category where the table
  makes it explicit, and keep the table's own unit where it does not. Show a true minus
  sign for negative changes.
- **Success criterion:** for every catalog answer in the evaluation sets, the shown unit
  is either unchanged or follows from a named category, checked by tests; no figure
  changes.
- **Dependencies and risks:** depends on consistent category naming across tables. Risk:
  a wrong inference of the unit is itself a wrong answer, so ambiguous cases keep the
  table's unit.

### N4. Clarifications that name the unresolved part (A: coverage)

- **Problem:** when a question cannot be settled, the reply does not always say which part
  of the question was not understood or which dimension stayed open.
- **Proposal:** when the planner skips a table, record the reason (an open dimension, an
  unexplained word, a restricting title) and use the most specific reason in the reply.
- **Success criterion:** on the understanding set, every clarification and suggestion
  names a word or a dimension, and no answer changes.
- **Dependencies and risks:** depends on the planner keeping skip reasons. Risk: replies
  that expose internal codes; they must use Statistics Iceland's labels.

### N5. Accessibility and small screens (C: user experience)

- **Problem:** the page has basic accessible markup but has not been audited.
- **Proposal:** an audit against WCAG 2.2 AA: keyboard use, focus order, contrast in both
  colour schemes, screen-reader announcements of new answers, and layout at 320 px.
- **Success criterion:** an automated accessibility check reports no violations, and a
  documented manual keyboard and screen-reader pass covers each reply type.
- **Dependencies and risks:** none beyond time. Risk of scope growth into a redesign.

### N6. Statistical definitions next to answers (C: user experience)

- **Problem:** terms such as "ársbreyting" or "mannfjöldi 1. janúar" are precise, but not
  every user knows what they include.
- **Proposal:** link each curated measure to Statistics Iceland's own definition or
  methodology page, and show a catalog table's notes where the table provides them.
- **Success criterion:** every curated answer type carries a working link to an official
  definition; a link check runs in the release check.
- **Dependencies and risks:** official pages move; links need checking. Talnaspor must
  not write its own definitions of official terms.

### N7. Reproducible deployment and reliability (C: deployment)

- **Problem:** Talnaspor runs locally only, and depends on Statistics Iceland's request
  limit.
- **Proposal:** a documented container build from the lockfile, with an egress rule that
  allows only px.hagstofa.is; a persistent response cache; health and rate-limit metrics.
- **Success criterion:** the container starts from a fresh clone with one command, passes
  `make check`, and a deliberately blocked outside address is refused at the network
  level as well as in code.
- **Dependencies and risks:** hosting is a separate decision for the owners and, for any
  public service, for Statistics Iceland's usage terms. A shared cache must not serve data
  older than its stated date.

### N8. Feedback and error reporting (C: user experience)

- **Problem:** there is no way for a user to report a wrong or unhelpful answer.
- **Proposal:** an optional "this was wrong or unhelpful" control that stores the question,
  the reply and the selections locally, with no personal data.
- **Success criterion:** a report contains everything needed to reproduce the reply
  offline, and is written only when the user asks.
- **Dependencies and risks:** privacy and storage policy must be decided first. Reports
  are development data and must not be mixed into unseen test sets.

## Longer-term supporting research

Research that the local-model programme depends on, and that is useful without it. Each
item starts with a measurement, so that a method is adopted only if it beats the current
baseline on the reporting standard below.

### R1. An independently controlled benchmark (D: evaluation)

- **Problem:** every current evaluation set was used during development, so none measures
  performance on unseen questions.
- **Proposal:** a benchmark of questions written and answered by people outside the
  development work, with expected values taken from Statistics Iceland's tables, kept
  sealed and run only at declared checkpoints. Questions are stratified by topic,
  difficulty, language and question type, including ones that must not be answered.
- **Success criterion:** the benchmark exists with a written protocol, its expected values
  are independently checked, and results are published with the commit they measure,
  whatever they show.
- **Dependencies and risks:** needs volunteers or partners who are independent of
  development; none is arranged. Each use leaks information, so use must be logged.

### R2. Icelandic and English equivalence (D: evaluation)

- **Problem:** the same question in Icelandic and English can be interpreted differently.
- **Proposal:** a paired test set in which each question has an Icelandic and an English
  version, checked for the same table, selections and figure.
- **Success criterion:** the paired agreement rate is reported for each release, with
  every disagreement listed.
- **Dependencies and risks:** translations must be equivalent in meaning, which needs a
  fluent reviewer for each pair.

### R3. Finding the right table (A: coverage)

- **Problem:** table search uses word matching, and misses tables described with other
  words or synonyms.
- **Proposal:** first measure table-retrieval recall on labelled questions for the current
  search. Then compare, on the same questions: synonym and inflection lists, multilingual
  embedding search over official titles and notes, and search over reviewed annotations.
  Official metadata and any generated annotations are kept separate, and annotations count
  as unverified until reviewed.
- **Success criterion:** recall of the correct table among the top 5 and top 10 is
  reported for each method, with confidence intervals, on a set not used to tune it.
- **Dependencies and risks:** needs labelled questions (R1 or a separate development set).
  Embedding models add dependencies that must run locally.

### R4. Planning every dimension, and checking the plan independently (A, B)

- **Problem:** the current build can return a correct official figure for a different
  question than the one asked, for example by defaulting a dimension to its total when the
  question meant something narrower.
- **Proposal:** measure planner coverage when given the correct table and intent
  ("oracle" input), to separate retrieval errors from planning errors. Then add an
  independent check that compares each selection with the question's stated constraints,
  so that no stated restriction is silently dropped.
- **Success criterion:** on a labelled set, every answer whose selections ignore a stated
  constraint is detected, and the planning and retrieval error rates are reported
  separately.
- **Dependencies and risks:** needs a written specification of constraints, which is
  itself research. Risk of rejecting good answers; measured as lost coverage.

### R5. Measures, units, time and derived figures (B: verification)

- **Problem:** Talnaspor cannot calculate ratios, shares or changes across tables, and
  time references such as "last month" are ambiguous.
- **Proposal:** a small typed description of a statistical question (measure, unit,
  population, time reference and operation) that is checked before any calculation: for
  example that two operands share a unit and a time reference, or that a share has a
  matching total. Derived figures show their operands and formula.
- **Success criterion:** each derived figure in the test sets is reproduced exactly from
  its displayed operands, and each incompatible combination in a negative test set is
  refused.
- **Dependencies and risks:** depends on metadata that states units and reference periods
  consistently. A derived figure is not an official statistic and must be labelled as such.

### R6. A baseline comparison study (D: evaluation)

- **Problem:** without shared baselines, gains from any one method cannot be attributed.
- **Proposal:** run four configurations on the same inputs: rules only, rules with catalog
  search (the current build), semantic retrieval (R3), and the local-model architecture
  (L1–L7), each with and without the deterministic fallback.
- **Success criterion:** one report gives, for each configuration, the reporting-standard
  figures below, with uncertainty and the commit and data date used.
- **Dependencies and risks:** depends on R1 and R3. Risk of tuning to the comparison set,
  so the set's status must be declared.

### R7. Learning from a separately developed project (B: verification)

- **Problem:** stricter verification (R4, R5) need not be designed from scratch.
- **Proposal:** Statspjall is a separately developed, experimental project for the same
  data source, at an early stage: its interfaces and their tests are defined, but its
  components are not yet implemented. Investigate whether its design for recording each
  question's constraints and verifying a plan before and after retrieval could be reused.
- **Success criterion:** a written assessment of which parts, if any, fit Talnaspor, and
  at what cost. No integration is assumed.
- **Dependencies and risks:** depends on that project's progress and licence
  compatibility. The two are separate projects, and no combined product exists.

## Reporting standard for every evaluation

Every evaluation report states, for each set and each configuration:

- **Numerical answer accuracy:** correct figures among the figures given.
- **Semantic correctness:** whether the interpretation (table, dimensions, measure, time
  reference and operation) matches the question, judged separately from the figure.
- **Answer coverage:** correct figures among the answerable questions.
- **Safe non-answers:** clarifications, suggestions and refusals, by type.
- **Wrong answers and unsupported-answer risk:** each figure given where it was wrong, or
  where no figure should have been given, listed with the question, the figure, the
  expected outcome and the cause, as the main measure of risk.
- **Latency:** median and 95th-percentile response time on stated hardware, with and
  without a model.
- **Refusal correctness:** among questions that must not be answered, how many got no
  figure.
- **Uncertainty:** confidence intervals for rates, and the number of questions behind them.
- **Provenance:** commit, question-set version and status (development-informed or unseen),
  data and recording dates, and the command that reproduces the report.
- **Limitations:** what the set does not cover.
