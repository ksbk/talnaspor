"""FastAPI application exposing Talnaspor's chat page and question endpoint."""

import logging
import os
import re
import time
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from talnaspor.answer import Answer, Comparison, Lang, answer, compare, format_period
from talnaspor.catalog import TableHit, question_words, search, table, topic_word
from talnaspor.interpret import (
    CHANGE,
    COMPARE_YEARS,
    INVALID_SPAN,
    INVALID_YEAR,
    NOT_FOUND,
    POPULATION_WORDS,
    RELATIVE_MESSAGE,
    SERIES,
    SERIES_UNSUPPORTED,
    YEAR,
    Clarification,
    Interpretation,
    curated_terms_cover,
    follow_up,
    interpret,
    invalid_duration,
    invalid_year,
    narrow,
    normalize,
    relative_period,
    without_periods,
)
from talnaspor.jsonstat import MissingValue
from talnaspor.planner import (
    GENERAL_KNOWLEDGE,
    Choice,
    comparison_span,
    plan_answer,
    plan_comparison,
)
from talnaspor.pxweb import RateLimited
from talnaspor.runtime import check_environment
from talnaspor.validation import UnavailableValue

# Settings that would send data to another host stop the server here, before it starts.
check_environment(os.environ)
# No telemetry export, whatever OTEL_* environment variables say.
app = FastAPI(title="Talnaspor", telemetry={"auto_configure": False})
logger = logging.getLogger(__name__)

INDEX = Path(__file__).parent / "static" / "index.html"

MESSAGES: dict[str, dict[str, str]] = {
    "is": {
        "suggestions": (
            "Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands "
            "fjalla líklega um efnið:"
        ),
        "error": "Ekki náðist samband við Hagstofu Íslands. Reyndu aftur síðar.",
        "unexpected": "Óvænt villa kom upp í Talnaspor. Reyndu aftur.",
        "rate_limited": (
            "Hagstofa Íslands takmarkar fjölda fyrirspurna í augnablikinu. "
            "Reyndu aftur eftir um það bil mínútu."
        ),
        "refusal": "Ekki tókst að svara spurningunni með staðfestum gögnum frá Hagstofu Íslands.",
        "unavailable": (
            "Engin tala er til fyrir {requested} í töflu Hagstofu Íslands. "
            "Taflan nær frá {first} til {last}."
        ),
        "unpublished": "Hagstofa Íslands hefur ekki birt þessa tölu (merkt „..“ í töflunni).",
        "missing": "Þessi tala er ekki tiltæk í töflu Hagstofu Íslands.",
        "one_at_a_time": (
            "Spyrðu einnar spurningar í einu, til dæmis fyrst um annað og svo um hitt."
        ),
        "no_context": (
            "Ég veit ekki við hvaða spurningu þetta á. Spyrðu allrar spurningarinnar, til "
            "dæmis „Hvert var atvinnuleysi kvenna árið 2025?“"
        ),
    },
    "en": {
        "suggestions": (
            "I cannot answer this directly yet, but these Statistics Iceland tables "
            "probably cover it:"
        ),
        "error": "Statistics Iceland could not be reached. Please try again later.",
        "unexpected": "Talnaspor ran into an unexpected error. Please try again.",
        "rate_limited": (
            "Statistics Iceland is limiting requests right now. Please try again in about a minute."
        ),
        "refusal": "I could not answer this question with verified data from Statistics Iceland.",
        "unavailable": (
            "Statistics Iceland's table has no figure for {requested}. It covers {first} to {last}."
        ),
        "unpublished": (
            "Statistics Iceland has not published this figure (marked “..” in the table)."
        ),
        "missing": "This figure is not available in Statistics Iceland's table.",
        "one_at_a_time": "Please ask one question at a time: the first, then the second.",
        "no_context": (
            "I don't know which question this follows. Please ask the whole question, for "
            "example “What was the unemployment rate for women in 2025?”"
        ),
    },
}


Question = Annotated[str, Field(min_length=1, max_length=500)]

# "Last year" as a calendar year; "the past year" is an interval, which the planner cannot
# answer with one year's figure.
CALENDAR_LAST_YEAR = re.compile(r"\b(last year|previous year|i fyrra|sidasta ar)\b")

# A named change measure ("annual change", "árleg breyting") is one period's figure, not a
# comparison between periods. Icelandic compounds ("ársbreyting") never match CHANGE.
NAMED_CHANGE = re.compile(
    r"\b(annual|monthly|yearly|quarterly|year on year|month on month|arleg\w*|manadarleg\w*)\b"
)

# Two questions in one: "…, and how many…", "… og hve margir…".
SEVERAL_QUESTIONS = re.compile(
    r"\b(and|og)\s+(how|what|which|when|hve|hversu|hvad|hver|hvert|hverjir|hverjar|hvenaer)\b"
)

# Questions are answered one after another, which keeps a batch within PX-Web's rate limit.
MAX_BATCH = 10


class AskRequest(BaseModel):
    question: Question
    lang: Lang = "is"
    # The question before this one, as understood, for follow-ups such as "What about women?".
    previous: Question | None = None


class AskBatchRequest(BaseModel):
    questions: list[Question] = Field(min_length=1, max_length=MAX_BATCH)
    lang: Lang = "is"


class AskResponse(BaseModel):
    status: Literal["answer", "suggestions", "clarification", "refusal", "error"]
    question: str
    message: str
    table: str | None = None
    selections: dict[str, str] | None = None
    compare_from: str | None = None
    answer: Answer | None = None
    comparison: Comparison | None = None
    tables: list[TableHit] | None = None
    # Why a refusal happened: the period or category is outside the table, the figure
    # is not published, or the data could not be verified for another reason.
    reason: (
        Literal["unavailable", "unpublished", "unverified", "rate_limited", "unexpected"] | None
    ) = None
    detail: str | None = None
    # A follow-up is answered as the previous question narrowed by it; this is that question.
    understood_as: str | None = None
    elapsed_ms: int


class AskBatchResponse(BaseModel):
    answers: list[AskResponse]
    elapsed_ms: int


# Statistics Iceland's primary table for a core topic is tried first for a question about
# it, so that a table counting something narrower or broader cannot answer instead (the
# population by registered religious affiliation, children in preschools for births). It
# still answers only if the planner can settle every word of the question from it.
POPULATION_TABLE = "Ibuar/mannfjoldi/1_yfirlit/Yfirlit_mannfjolda/MAN00101.px"
IMMIGRANT_TABLE = "Ibuar/mannfjoldi/3_bakgrunnur/Uppruni/MAN43000.px"
BIRTH_TABLE = "Ibuar/Faeddirdanir/Faeddir/faedingar/MAN05101.px"
PRIMARY_TABLES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("innflytj", "immigrant"), IMMIGRANT_TABLE),
    (("faeddust", "faeddir", "faeding", "born", "birth"), BIRTH_TABLE),
    (POPULATION_WORDS, POPULATION_TABLE),
)

# Tables whose figures mean more than their titles say. "Innflytjendur eftir kyni og
# sveitarfélagi" counts the second generation of immigrants too (85,577 on 1 January 2026,
# against 77,226 immigrants), so it never answers a question about immigrants.
EXCLUDED_TABLES = frozenset({"Ibuar/mannfjoldi/3_bakgrunnur/Uppruni/MAN43005.px"})


def candidates(question: str, tables: list[TableHit]) -> list[TableHit]:
    """Tables to try answering from: the best for the whole question, then for its topic.

    Words naming a category ("hlutfall") can outrank the topic in a search of the whole
    question, so the best tables for its most distinctive word are tried as well.
    """
    topic = topic_word(question)
    # Many tables can tie on a topic word, so look past the first few.
    by_topic = search(topic, limit=10) if topic else []

    def ranked(hits: list[TableHit]) -> list[TableHit]:
        # On equal scores, a shorter title is usually the more general table.
        return sorted(hits, key=lambda hit: (-hit.score, len(hit.title)))

    text = normalize(question)
    primary = [table(path) for words, path in PRIMARY_TABLES if any(w in text for w in words)]
    ordered = [hit for hit in primary if hit]
    ordered += ranked(tables[:5]) + ranked(by_topic) + ranked(tables[5:])
    ordered = [hit for hit in ordered if not hit.api_url.endswith(tuple(EXCLUDED_TABLES))]
    unique = {hit.api_url: hit for hit in reversed(ordered)}
    return sorted(unique.values(), key=ordered.index)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the browser chat page."""
    return FileResponse(INDEX)


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse | JSONResponse:
    """Answer a statistical question from verified PX-Web data, or explain why not."""
    response = safely_respond_to(request.question, request.lang, request.previous)
    if response.status == "error":
        status_code = {"rate_limited": 503, "unexpected": 500}.get(response.reason or "", 502)
        return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))
    return response


@app.post("/ask/batch", response_model=AskBatchResponse)
def ask_batch(request: AskBatchRequest) -> AskBatchResponse:
    """Answer several questions in one call, each exactly as /ask would, in order.

    Each answer carries its own status, so one question that cannot be answered, or a
    failure to reach Statistics Iceland, does not fail the others.
    """
    started = time.perf_counter()
    answers = [safely_respond_to(question, request.lang) for question in request.questions]
    return AskBatchResponse(
        answers=answers, elapsed_ms=round((time.perf_counter() - started) * 1000)
    )


def safely_respond_to(question: str, lang: Lang = "is", previous: str | None = None) -> AskResponse:
    """Answer one question; an unexpected failure becomes a JSON error, never plain text.

    Without this, FastAPI answers an unhandled exception with a plain-text 500, which
    the page cannot read and reports as "could not reach the server".

    A follow-up ("What about women?") is answered as the previous question narrowed by
    it, and the reply says so; without a previous question, it is never guessed at.
    """
    started = time.perf_counter()
    try:
        restriction = follow_up(question)
        if restriction is None:
            return respond_to(question, lang)
        if not previous:
            return AskResponse(
                status="clarification",
                question=question,
                message=MESSAGES[lang]["no_context"],
                elapsed_ms=round((time.perf_counter() - started) * 1000),
            )
        understood = narrow(previous, restriction)
        response = respond_to(understood, lang)
        return response.model_copy(update={"question": question, "understood_as": understood})
    except Exception as error:
        logger.exception("Unexpected error answering %r", question)
        return AskResponse(
            status="error",
            reason="unexpected",
            question=question,
            message=MESSAGES[lang]["unexpected"],
            detail=type(error).__name__,
            elapsed_ms=round((time.perf_counter() - started) * 1000),
        )


def respond_to(question: str, lang: Lang = "is") -> AskResponse:
    """Answer one question in the given language, reporting failures in the status."""
    started = time.perf_counter()

    def respond(**fields: object) -> AskResponse:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return AskResponse.model_validate(
            {"question": question, "elapsed_ms": elapsed_ms, **fields}
        )

    messages = MESSAGES[lang]
    if SEVERAL_QUESTIONS.search(normalize(question)):
        # Answering one part, or reading two parts as a comparison, would answer a question
        # that was not asked.
        return respond(status="clarification", message=messages["one_at_a_time"])
    if SERIES.search(normalize(question)):
        # A series or chart is asked for; two endpoints would answer another question.
        return respond(status="clarification", message=SERIES_UNSUPPORTED.text(lang))
    if invalid_year(normalize(question)):
        return respond(status="clarification", message=INVALID_YEAR.text(lang))
    interpretation = interpret(question)
    if isinstance(interpretation, Interpretation) and not curated_terms_cover(
        question_words(without_periods(question))
    ):
        # The question names something the national headline figures do not answer, such
        # as a municipality or a sub-index, so it is treated as any other topic: the
        # catalog planner answers only if a table settles every word, or says why not.
        interpretation = Clarification(NOT_FOUND["is"], NOT_FOUND["en"], recognized=False)
    if isinstance(interpretation, Clarification):
        # General-knowledge questions ("capital of Iceland") are not statistical, so they
        # get the plain "not found" reply rather than loosely related tables.
        searchable = not interpretation.recognized and not GENERAL_KNOWLEDGE.search(
            normalize(question)
        )
        tables = search(question, limit=10) if searchable else []
        if not tables:
            return respond(status="clarification", message=interpretation.text(lang))
        text = normalize(question)
        span = comparison_span(question)
        if invalid_duration(text):
            return respond(status="clarification", message=INVALID_SPAN.text(lang))
        asked = question
        last_year = span is None and CALENDAR_LAST_YEAR.search(text)
        if last_year and not re.search(YEAR, text) and not CHANGE.search(text):
            # "Í fyrra" (last year) is the previous calendar year, asked for by number; the
            # answer shows the year.
            asked = f"{question} {date.today().year - 1}"
            text = CALENDAR_LAST_YEAR.sub(" ", text)
        if span is None and relative_period(text):
            # The planner reads named years and months only; a relative period it cannot
            # use is refused rather than dropped (which answered with the latest figure).
            return respond(status="clarification", message=RELATIVE_MESSAGE.text(lang))
        if (
            span is None
            and CHANGE.search(text)
            and not NAMED_CHANGE.search(text)
            and not re.search(YEAR, text)
        ):
            # A change with no periods to compare is asked again, not answered with the
            # latest single figure (a different question) or a span the user did not state.
            return respond(status="clarification", message=COMPARE_YEARS.text(lang))
        hits = candidates(asked, tables)
        try:
            planned: Answer | Comparison | Choice | None = (
                plan_comparison(question, hits, span, attempts=12, lang=lang)
                if span
                else plan_answer(asked, hits, attempts=12, lang=lang)
            )
        except RateLimited as error:
            return respond(
                status="error",
                reason="rate_limited",
                message=messages["rate_limited"],
                detail=str(error),
            )
        if isinstance(planned, Answer):
            others = [t for t in tables if t.api_url != planned.api_url][:4]
            return respond(status="answer", message=planned.text, answer=planned, tables=others)
        if isinstance(planned, Comparison):
            others = [t for t in tables if t.api_url != planned.api_url][:4]
            return respond(status="answer", message=planned.text, comparison=planned, tables=others)
        message = messages["suggestions"]
        if isinstance(planned, Choice):
            message = f"{planned.message(lang)} {message}"
            if planned.table:
                # The table the choice refers to comes first.
                others = [t for t in tables if t.api_url != planned.table.api_url]
                tables = [planned.table, *others]
        return respond(status="suggestions", message=message, tables=tables[:5])

    context = {
        "table": interpretation.table,
        "selections": interpretation.selections,
        "compare_from": interpretation.compare_from,
    }
    try:
        if interpretation.compare_from is not None:
            comparison = compare(
                interpretation.table,
                interpretation.selections,
                interpretation.compare_from,
                lang,
            )
            return respond(
                status="answer", message=comparison.text, comparison=comparison, **context
            )
        result = answer(interpretation.table, interpretation.selections, lang)
    except RateLimited as error:
        return respond(
            status="error",
            reason="rate_limited",
            message=messages["rate_limited"],
            detail=str(error),
            **context,
        )
    except requests.RequestException as error:
        return respond(
            status="error",
            message=messages["error"],
            detail=str(error),
            **context,
        )
    except UnavailableValue as error:
        message = messages["unavailable"].format(
            requested=format_period(error.requested, lang),
            first=format_period(error.first, lang),
            last=format_period(error.last, lang),
        )
        return respond(
            status="refusal", reason="unavailable", message=message, detail=str(error), **context
        )
    except MissingValue as error:
        message = messages["unpublished" if error.status == ".." else "missing"]
        return respond(
            status="refusal", reason="unpublished", message=message, detail=str(error), **context
        )
    except ValueError as error:
        return respond(
            status="refusal",
            reason="unverified",
            message=messages["refusal"],
            detail=str(error),
            **context,
        )

    return respond(status="answer", message=result.text, answer=result, **context)
