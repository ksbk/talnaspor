"""FastAPI application exposing Talnaspor's chat page and question endpoint."""

import time
from pathlib import Path
from typing import Annotated, Literal

import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from talnaspor.answer import Answer, Comparison, Lang, answer, compare, format_period
from talnaspor.catalog import TableHit, search, topic_word
from talnaspor.interpret import Clarification, interpret, normalize
from talnaspor.jsonstat import MissingValue
from talnaspor.planner import GENERAL_KNOWLEDGE, Choice, plan_answer
from talnaspor.validation import UnavailableValue

app = FastAPI(title="Talnaspor")

INDEX = Path(__file__).parent / "static" / "index.html"

MESSAGES: dict[str, dict[str, str]] = {
    "is": {
        "suggestions": (
            "Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands "
            "fjalla líklega um efnið:"
        ),
        "error": "Ekki náðist samband við Hagstofu Íslands. Reyndu aftur síðar.",
        "refusal": "Ekki tókst að svara spurningunni með staðfestum gögnum frá Hagstofu Íslands.",
        "unavailable": (
            "Engin tala er til fyrir {requested} í töflu Hagstofu Íslands. "
            "Taflan nær frá {first} til {last}."
        ),
        "unpublished": "Hagstofa Íslands hefur ekki birt þessa tölu (merkt „..“ í töflunni).",
        "missing": "Þessi tala er ekki tiltæk í töflu Hagstofu Íslands.",
    },
    "en": {
        "suggestions": (
            "I cannot answer this directly yet, but these Statistics Iceland tables "
            "probably cover it:"
        ),
        "error": "Statistics Iceland could not be reached. Please try again later.",
        "refusal": "I could not answer this question with verified data from Statistics Iceland.",
        "unavailable": (
            "Statistics Iceland's table has no figure for {requested}. It covers {first} to {last}."
        ),
        "unpublished": (
            "Statistics Iceland has not published this figure (marked “..” in the table)."
        ),
        "missing": "This figure is not available in Statistics Iceland's table.",
    },
}


Question = Annotated[str, Field(min_length=1, max_length=500)]

# Questions are answered one after another, which keeps a batch within PX-Web's rate limit.
MAX_BATCH = 10


class AskRequest(BaseModel):
    question: Question
    lang: Lang = "is"


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
    reason: Literal["unavailable", "unpublished", "unverified"] | None = None
    detail: str | None = None
    elapsed_ms: int


class AskBatchResponse(BaseModel):
    answers: list[AskResponse]
    elapsed_ms: int


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

    ordered = ranked(tables[:5]) + ranked(by_topic) + ranked(tables[5:])
    unique = {hit.api_url: hit for hit in reversed(ordered)}
    return sorted(unique.values(), key=ordered.index)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the browser chat page."""
    return FileResponse(INDEX)


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse | JSONResponse:
    """Answer a statistical question from verified PX-Web data, or explain why not."""
    response = respond_to(request.question, request.lang)
    if response.status == "error":
        return JSONResponse(status_code=502, content=response.model_dump(mode="json"))
    return response


@app.post("/ask/batch", response_model=AskBatchResponse)
def ask_batch(request: AskBatchRequest) -> AskBatchResponse:
    """Answer several questions in one call, each exactly as /ask would, in order.

    Each answer carries its own status, so one question that cannot be answered, or a
    failure to reach Statistics Iceland, does not fail the others.
    """
    started = time.perf_counter()
    answers = [respond_to(question, request.lang) for question in request.questions]
    return AskBatchResponse(
        answers=answers, elapsed_ms=round((time.perf_counter() - started) * 1000)
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
    interpretation = interpret(question)
    if isinstance(interpretation, Clarification):
        # General-knowledge questions ("capital of Iceland") are not statistical, so they
        # get the plain "not found" reply rather than loosely related tables.
        searchable = not interpretation.recognized and not GENERAL_KNOWLEDGE.search(
            normalize(question)
        )
        tables = search(question, limit=10) if searchable else []
        if not tables:
            return respond(status="clarification", message=interpretation.text(lang))
        planned = plan_answer(question, candidates(question, tables), attempts=12, lang=lang)
        if isinstance(planned, Answer):
            others = [t for t in tables if t.api_url != planned.api_url][:4]
            return respond(status="answer", message=planned.text, answer=planned, tables=others)
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
