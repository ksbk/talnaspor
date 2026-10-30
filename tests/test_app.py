from unittest.mock import patch

import requests
from fastapi.testclient import TestClient

from talnaspor.answer import LATEST, Answer
from talnaspor.app import app

client = TestClient(app)

POPULATION = Answer(
    text="Mannfjöldi 1. janúar 2026: 394.324 íbúar. Heimild: Hagstofa Íslands.",
    value=394324,
    value_text="394.324 íbúar",
    unit="íbúar",
    period="2026",
    period_label="2026",
    table_title="Lykiltölur mannfjöldans 1703-2026",
    source="Hagstofa Íslands, Hagskinna",
    page_url="https://px.hagstofa.is/pxis/pxweb/is/example",
    api_url="https://px.hagstofa.is/pxis/api/v1/is/example",
    selections={"Ár": "2026", "Eining": "0"},
    labels={"Ár": "2026", "Eining": "Mannfjöldi 1. janúar"},
    status=None,
)


def test_answers_supported_question() -> None:
    with patch("talnaspor.app.answer", return_value=POPULATION) as answer:
        response = client.post("/ask", json={"question": "Hvað búa margir á Íslandi?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answer"
    assert body["message"] == POPULATION.text
    assert body["table"] == "population"
    assert body["selections"] == {"Ár": LATEST, "Eining": "0"}
    assert body["answer"]["value"] == 394324
    assert body["answer"]["page_url"] == POPULATION.page_url
    assert isinstance(body["elapsed_ms"], int)
    answer.assert_called_once_with("population", {"Ár": LATEST, "Eining": "0"})


def test_asks_for_clarification_without_retrieval() -> None:
    with patch("talnaspor.app.answer") as answer:
        response = client.post("/ask", json={"question": "Verðbólga árið 2024"})

    assert response.status_code == 200
    assert response.json()["status"] == "clarification"
    assert response.json()["answer"] is None
    answer.assert_not_called()


def test_refuses_when_data_cannot_be_verified() -> None:
    error = ValueError("Missing value for {'Ár': '2026', 'Eining': '2'} (status '..')")
    with patch("talnaspor.app.answer", side_effect=error):
        response = client.post("/ask", json={"question": "Fjölgun íbúa árið 2026"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "refusal"
    assert body["answer"] is None
    assert "status '..'" in body["detail"]


def test_reports_upstream_failure() -> None:
    with patch("talnaspor.app.answer", side_effect=requests.ConnectionError("timed out")):
        response = client.post("/ask", json={"question": "Hver er verðbólgan?"})

    assert response.status_code == 502
    assert response.json()["status"] == "error"
    assert response.json()["answer"] is None


def test_rejects_empty_question() -> None:
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_serves_chat_page() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>Talnaspor</title>" in response.text
    assert 'fetch("/ask"' in response.text
