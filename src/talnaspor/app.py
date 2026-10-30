"""FastAPI application exposing Talnaspor's chat page and question endpoint."""

import time
from pathlib import Path
from typing import Literal

import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from talnaspor.answer import Answer, Comparison, answer, compare
from talnaspor.interpret import Clarification, interpret

app = FastAPI(title="Talnaspor")

INDEX = Path(__file__).parent / "static" / "index.html"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AskResponse(BaseModel):
    status: Literal["answer", "clarification", "refusal", "error"]
    question: str
    message: str
    table: str | None = None
    selections: dict[str, str] | None = None
    compare_from: str | None = None
    answer: Answer | None = None
    comparison: Comparison | None = None
    detail: str | None = None
    elapsed_ms: int


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
        return respond(status="clarification", message=interpretation.message)

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
