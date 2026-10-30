"""FastAPI application exposing Talnaspor's chat page and question endpoint."""

import time
from pathlib import Path
from typing import Literal

import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from talnaspor.answer import Answer, Comparison, answer, compare
from talnaspor.catalog import TableHit, search, topic_word
from talnaspor.interpret import Clarification, interpret
from talnaspor.planner import Choice, plan_answer

app = FastAPI(title="Talnaspor")

INDEX = Path(__file__).parent / "static" / "index.html"

SUGGESTIONS = (
    "Ég get ekki svarað þessu beint ennþá, en þessar töflur Hagstofu Íslands "
    "fjalla líklega um efnið:"
)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


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
    detail: str | None = None
    elapsed_ms: int


def candidates(question: str, tables: list[TableHit]) -> list[TableHit]:
    """Tables to try answering from: the best for the whole question, then for its topic.

    Words naming a category ("hlutfall") can outrank the topic in a search of the whole
    question, so the best tables for its most distinctive word are tried as well.
    """
    topic = topic_word(question)
    by_topic = search(topic, limit=5) if topic else []

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
    started = time.perf_counter()

    def respond(**fields: object) -> AskResponse:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return AskResponse.model_validate(
            {"question": request.question, "elapsed_ms": elapsed_ms, **fields}
        )

    interpretation = interpret(request.question)
    if isinstance(interpretation, Clarification):
        tables = [] if interpretation.recognized else search(request.question, limit=10)
        if not tables:
            return respond(status="clarification", message=interpretation.message)
        planned = plan_answer(request.question, candidates(request.question, tables))
        if isinstance(planned, Answer):
            others = [t for t in tables if t.api_url != planned.api_url][:4]
            return respond(status="answer", message=planned.text, answer=planned, tables=others)
        message = SUGGESTIONS
        if isinstance(planned, Choice):
            message = f"{planned.message()} {SUGGESTIONS}"
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
                interpretation.table, interpretation.selections, interpretation.compare_from
            )
            return respond(
                status="answer", message=comparison.text, comparison=comparison, **context
            )
        result = answer(interpretation.table, interpretation.selections)
    except requests.RequestException as error:
        body = respond(
            status="error",
            message="Ekki náðist samband við Hagstofu Íslands. Reyndu aftur síðar.",
            detail=str(error),
            **context,
        )
        return JSONResponse(status_code=502, content=body.model_dump(mode="json"))
    except ValueError as error:
        return respond(
            status="refusal",
            message="Ekki tókst að svara spurningunni með staðfestum gögnum frá Hagstofu Íslands.",
            detail=str(error),
            **context,
        )

    return respond(status="answer", message=result.text, answer=result, **context)
