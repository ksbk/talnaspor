from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
from fastapi.testclient import TestClient

from talnaspor.answer import LATEST, Answer, Comparison, Point
from talnaspor.app import (
    BIRTH_TABLE,
    EXCLUDED_TABLES,
    IMMIGRANT_TABLE,
    POPULATION_TABLE,
    AskResponse,
    app,
    candidates,
)
from talnaspor.catalog import search
from talnaspor.jsonstat import MissingValue
from talnaspor.planner import Choice
from talnaspor.pxweb import PXMetadata, RateLimited
from talnaspor.validation import UnavailableValue

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
    answer.assert_called_once_with("population", {"Ár": LATEST, "Eining": "0"}, "is")


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


def test_suggests_tables_for_unsupported_topics() -> None:
    with patch("talnaspor.app.plan_answer", return_value=None):
        response = client.post("/ask", json={"question": "Hversu margir eru atvinnulausir?"})

    body = response.json()
    assert body["status"] == "suggestions"
    assert "töflur Hagstofu" in body["message"]
    assert any("Atvinnulausir" in table["title"] for table in body["tables"])
    assert body["answer"] is None


def test_answers_from_a_catalog_table() -> None:
    planned = POPULATION.model_copy(
        update={
            "kind": "catalog",
            "api_url": "https://px.hagstofa.is/pxis/api/v1/is/Samfelag/x/VIN00001.px",
        }
    )
    with patch("talnaspor.app.plan_answer", return_value=planned) as plan_answer:
        response = client.post("/ask", json={"question": "Hversu margir eru atvinnulausir?"})

    body = response.json()
    assert body["status"] == "answer"
    assert body["answer"]["kind"] == "catalog"
    assert body["message"] == planned.text
    assert all(table["api_url"] != planned.api_url for table in body["tables"])
    plan_answer.assert_called_once()


def test_names_the_choice_a_table_needs() -> None:
    choice = Choice("Kosningaþátttaka 2016-2024", "Eining", ["Fjöldi", "Hlutfall, %"])
    with patch("talnaspor.app.plan_answer", return_value=choice):
        response = client.post("/ask", json={"question": "Hver var kosningaþátttaka árið 2024?"})

    body = response.json()
    assert body["status"] == "suggestions"
    assert body["message"].startswith(choice.message())
    assert body["tables"]


def test_keeps_clarification_when_no_table_matches() -> None:
    response = client.post("/ask", json={"question": "Hvernig er veðrið?"})

    assert response.json()["status"] == "clarification"
    assert response.json()["tables"] is None


def test_does_not_search_for_recognized_topics() -> None:
    with patch("talnaspor.app.search") as search:
        response = client.post("/ask", json={"question": "Verðbólga árið 2024"})

    assert response.json()["status"] == "clarification"
    search.assert_not_called()


def test_rejects_empty_question() -> None:
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_serves_chat_page() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>Talnaspor</title>" in response.text
    assert 'fetch("/ask"' in response.text


def test_answers_change_over_time_end_to_end() -> None:
    fixtures = Path(__file__).parent / "fixtures" / "is"
    metadata = PXMetadata.model_validate_json(
        (fixtures / "population_metadata.json").read_text(encoding="utf-8")
    )
    data = (fixtures / "population_2016_2026.json").read_text(encoding="utf-8")

    with (
        patch("talnaspor.answer.get_metadata", return_value=metadata),
        patch("talnaspor.answer.get_data", return_value=data),
    ):
        response = client.post(
            "/ask", json={"question": "How has Iceland's population changed over the last decade?"}
        )

    body = response.json()
    assert body["status"] == "answer"
    assert body["answer"] is None
    assert body["compare_from"] == "latest-10"
    assert body["comparison"]["difference_text"] == "+68.288 íbúar"
    assert body["comparison"]["relative_change_text"] == "+20,9%"
    assert body["message"].startswith("Mannfjöldi 1. janúar 2016: 326.036 íbúar.")


def test_answers_several_questions_in_order() -> None:
    questions = ["Hvað búa margir á Íslandi?", "Verðbólga árið 2024", "Hvernig er veðrið?"]
    with patch("talnaspor.app.answer", return_value=POPULATION):
        response = client.post("/ask/batch", json={"questions": questions})

    assert response.status_code == 200
    body = response.json()
    assert [item["question"] for item in body["answers"]] == questions
    assert [item["status"] for item in body["answers"]] == [
        "answer",
        "clarification",
        "clarification",
    ]
    assert body["answers"][0]["answer"]["value"] == 394324
    assert isinstance(body["elapsed_ms"], int)


def test_reports_failures_per_question_in_a_batch() -> None:
    with patch("talnaspor.app.answer", side_effect=requests.ConnectionError("timed out")):
        response = client.post(
            "/ask/batch", json={"questions": ["Hver er verðbólgan?", "Verðbólga árið 2024"]}
        )

    assert response.status_code == 200
    assert [item["status"] for item in response.json()["answers"]] == ["error", "clarification"]


@pytest.mark.parametrize(
    "questions", [[], ["Hver er verðbólgan?"] * 11, ["Hver er verðbólgan?", ""]]
)
def test_rejects_empty_oversized_or_blank_batches(questions: list[str]) -> None:
    assert client.post("/ask/batch", json={"questions": questions}).status_code == 422


def test_replies_in_english() -> None:
    clarification = client.post("/ask", json={"question": "Verðbólga árið 2024", "lang": "en"})
    assert clarification.json()["message"].startswith("Please name a month")

    with patch("talnaspor.app.answer", side_effect=ValueError("Missing value")):
        refusal = client.post("/ask", json={"question": "Hver er verðbólgan?", "lang": "en"})
    assert refusal.json()["message"].startswith("I could not answer")

    with patch("talnaspor.app.answer", side_effect=requests.ConnectionError("down")):
        error = client.post("/ask", json={"question": "Hver er verðbólgan?", "lang": "en"})
    assert error.status_code == 502
    assert error.json()["message"].startswith("Statistics Iceland could not be reached")


def test_passes_the_language_to_answers() -> None:
    with patch("talnaspor.app.answer", return_value=POPULATION) as answer:
        client.post("/ask", json={"question": "How many people live in Iceland?", "lang": "en"})
        client.post("/ask/batch", json={"questions": ["Hvað búa margir á Íslandi?"], "lang": "en"})

    assert [call.args[2] for call in answer.call_args_list] == ["en", "en"]


def test_rejects_unsupported_languages() -> None:
    response = client.post("/ask", json={"question": "Hver er verðbólgan?", "lang": "de"})

    assert response.status_code == 422


def test_serves_both_languages_in_the_page() -> None:
    page = client.get("/").text

    assert 'data-lang="is"' in page and 'data-lang="en"' in page
    assert "{ question, lang }" in page


def test_explains_a_period_outside_the_table() -> None:
    error = UnavailableValue("2030M01", "Mánuður", "1988M05", "2026M10")
    with patch("talnaspor.app.answer", side_effect=error):
        icelandic = client.post("/ask", json={"question": "Verðbólga í janúar 2030"}).json()
        english = client.post(
            "/ask", json={"question": "Verðbólga í janúar 2030", "lang": "en"}
        ).json()

    assert icelandic["reason"] == "unavailable"
    assert icelandic["message"] == (
        "Engin tala er til fyrir janúar 2030 í töflu Hagstofu Íslands. "
        "Taflan nær frá maí 1988 til október 2026."
    )
    assert english["message"] == (
        "Statistics Iceland's table has no figure for January 2030. "
        "It covers May 1988 to October 2026."
    )


def test_explains_an_unpublished_figure() -> None:
    error = MissingValue({"Ár": "2026", "Eining": "2"}, "..")
    with patch("talnaspor.app.answer", side_effect=error):
        body = client.post("/ask", json={"question": "Hver var fjölgun íbúa árið 2026?"}).json()

    assert body["status"] == "refusal"
    assert body["reason"] == "unpublished"
    assert body["message"].startswith("Hagstofa Íslands hefur ekki birt þessa tölu")


@pytest.mark.parametrize(
    ("question", "lang"),
    [("What is the capital of Iceland?", "en"), ("Hver er höfuðborg Íslands?", "is")],
)
def test_answers_general_knowledge_questions_with_not_found(question: str, lang: str) -> None:
    with patch("talnaspor.app.search") as search:
        body = client.post("/ask", json={"question": question, "lang": lang}).json()

    assert body["status"] == "clarification"
    assert body["tables"] is None
    search.assert_not_called()


def test_says_when_statistics_iceland_is_limiting_requests() -> None:
    with patch("talnaspor.app.answer", side_effect=RateLimited("429")):
        response = client.post("/ask", json={"question": "Hver er verðbólgan núna?"})

    assert response.status_code == 503
    assert response.json()["reason"] == "rate_limited"
    assert response.json()["message"].startswith("Hagstofa Íslands takmarkar")


def test_reports_a_rate_limit_met_while_planning() -> None:
    with patch("talnaspor.app.plan_answer", side_effect=RateLimited("429")):
        response = client.post(
            "/ask", json={"question": "Hversu margir eru atvinnulausir?", "lang": "en"}
        )

    assert response.status_code == 503
    assert response.json()["message"].startswith("Statistics Iceland is limiting requests")


@pytest.mark.parametrize(
    ("question", "lang"),
    [
        ("Hvað eru margir íbúar í Reykjavík?", "is"),
        ("What was the population of Reykjavik in 2020?", "en"),
        ("Hver var verðbólgan á matvörum í september 2026?", "is"),
        ("What is the inflation rate in Norway?", "en"),
        ("Hver er meðalaldur íbúa á Íslandi?", "is"),
        ("Hverjar eru meðaltekjur íbúa?", "is"),
    ],
)
def test_never_answers_qualified_questions_with_national_headline_figures(
    question: str, lang: str
) -> None:
    with (
        patch("talnaspor.app.answer") as answer,
        patch("talnaspor.app.compare") as compare,
        patch("talnaspor.app.plan_answer", return_value=None),
    ):
        body = client.post("/ask", json={"question": question, "lang": lang}).json()

    answer.assert_not_called()
    compare.assert_not_called()
    assert body["status"] in ("suggestions", "clarification")


def test_reports_an_unexpected_error_as_json_not_plain_text() -> None:
    # A plain-text 500 is unreadable to the page, which then wrongly reports that it
    # could not reach the server.
    with patch("talnaspor.app.answer", side_effect=RuntimeError("boom")):
        response = TestClient(app, raise_server_exceptions=False).post(
            "/ask", json={"question": "What is the population of Iceland in 2026?", "lang": "en"}
        )

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["status"] == "error" and body["reason"] == "unexpected"
    assert body["message"].startswith("Talnaspor ran into an unexpected error")
    assert body["detail"] == "RuntimeError"


def test_keeps_a_batch_going_after_an_unexpected_error() -> None:
    with patch("talnaspor.app.answer", side_effect=[RuntimeError("boom"), POPULATION]):
        response = client.post(
            "/ask/batch",
            json={"questions": ["Hver er verðbólgan núna?", "Hvað búa margir á Íslandi?"]},
        )

    assert response.status_code == 200
    assert [item["status"] for item in response.json()["answers"]] == ["error", "answer"]


def test_page_tells_server_errors_apart_from_lost_connections() -> None:
    page = client.get("/").text

    assert "badResponse" in page and "offline" in page


def test_answers_a_follow_up_as_the_previous_question_narrowed() -> None:
    def fake(question: str, lang: str = "is") -> AskResponse:
        return AskResponse(status="clarification", question=question, message="", elapsed_ms=0)

    with patch("talnaspor.app.respond_to", side_effect=fake) as respond_to:
        body = client.post(
            "/ask",
            json={
                "question": "What about men?",
                "previous": "What was the unemployment rate for women in 2025?",
                "lang": "en",
            },
        ).json()

    respond_to.assert_called_once_with("What was the unemployment rate for men in 2025?", "en")
    assert body["question"] == "What about men?"
    assert body["understood_as"] == "What was the unemployment rate for men in 2025?"


@pytest.mark.parametrize("lang", ["is", "en"])
def test_never_guesses_what_a_follow_up_without_context_refers_to(lang: str) -> None:
    with patch("talnaspor.app.respond_to") as respond_to:
        body = client.post("/ask", json={"question": "En konur?", "lang": lang}).json()

    assert body["status"] == "clarification"
    assert body["understood_as"] is None
    respond_to.assert_not_called()


def test_treats_a_question_of_its_own_as_new_despite_a_previous_one() -> None:
    def fake(question: str, lang: str = "is") -> AskResponse:
        return AskResponse(status="clarification", question=question, message="", elapsed_ms=0)

    with patch("talnaspor.app.respond_to", side_effect=fake) as respond_to:
        client.post(
            "/ask",
            json={"question": "Hver er verðbólgan?", "previous": "Hve margir búa á Íslandi?"},
        )

    respond_to.assert_called_once_with("Hver er verðbólgan?", "is")


def test_page_sends_the_previous_question_and_shows_the_follow_up() -> None:
    page = client.get("/").text

    assert "previous" in page and "understood_as" in page and "understoodAs" in page


@pytest.mark.parametrize(
    "question", ["Population of women in 2026", "Hve margar konur bjuggu á Íslandi 2026?"]
)
def test_tries_the_primary_population_table_first_for_population_questions(question: str) -> None:
    # Otherwise the table of registered religious affiliation, whose total differs from
    # the population, answers first.
    tried = candidates(question, [])

    assert tried[0].api_url.endswith("/" + POPULATION_TABLE)


def test_does_not_try_the_population_table_for_other_topics() -> None:
    tried = candidates("Atvinnuleysi kvenna 2025", [])

    assert all(not hit.api_url.endswith("/" + POPULATION_TABLE) for hit in tried)


def test_answers_a_comparison_from_a_catalog_table() -> None:
    comparison = Comparison(
        text="Konur: 2024 3,5 (%), 2025 4,3 (%). Breyting: +0,8 prósentustig.",
        unit="%",
        start=Point(
            period="2024", period_label="2024", value=3.5, value_text="3,5 (%)", status=None
        ),
        end=Point(period="2025", period_label="2025", value=4.3, value_text="4,3 (%)", status=None),
        difference=0.8,
        difference_text="+0,8 prósentustig",
        relative_change_text=None,
        table_title="Atvinnuþátttaka, atvinnuleysi 1991-2025",
        source="Hagstofa Íslands",
        page_url="https://px.hagstofa.is/pxis/pxweb/is/x",
        api_url="https://px.hagstofa.is/pxis/api/v1/is/x",
        selections={"Ár": ["0", "1"], "Kyn": ["2"]},
        labels={"Kyn": "Konur"},
    )
    with (
        patch("talnaspor.app.plan_comparison", return_value=comparison) as plan,
        patch("talnaspor.app.plan_answer") as single,
    ):
        body = client.post("/ask", json={"question": "Atvinnuleysi kvenna 2024 og 2025"}).json()

    assert body["status"] == "answer"
    assert body["comparison"]["difference_text"] == "+0,8 prósentustig"
    plan.assert_called_once()
    single.assert_not_called()


@pytest.mark.parametrize(
    ("question", "first"),
    [
        ("How many immigrants lived in Iceland on 1 January 2026?", IMMIGRANT_TABLE),
        ("Hve margir innflytjendur bjuggu á Íslandi?", IMMIGRANT_TABLE),
        ("How many children were born in Iceland in 2024?", BIRTH_TABLE),
        ("Hve mörg börn fæddust á Íslandi árið 2024?", BIRTH_TABLE),
    ],
)
def test_tries_the_primary_table_of_a_core_topic_first(question: str, first: str) -> None:
    # Births were answered from children in preschools; immigrants from a table that also
    # counts the second generation.
    assert candidates(question, [])[0].api_url.endswith("/" + first)


def test_never_answers_from_a_table_broader_than_its_title() -> None:
    question = "Hve margir innflytjendur bjuggu á Íslandi?"
    tried = candidates(question, search(question, limit=10))

    assert not any(hit.api_url.endswith(tuple(EXCLUDED_TABLES)) for hit in tried)


@pytest.mark.parametrize(
    ("question", "lang"),
    [
        (
            (
                "How many children were born in Iceland in 2025, and how many immigrants "
                "lived in Iceland on 1 January 2026?"
            ),
            "en",
        ),
        ("Hver var launavísitalan og hver var vísitala neysluverðs í ágúst 2026?", "is"),
    ],
)
def test_asks_for_one_question_at_a_time(question: str, lang: str) -> None:
    # Two years in two questions were read as a comparison between them.
    with patch("talnaspor.app.plan_comparison") as compare, patch("talnaspor.app.plan_answer"):
        body = client.post("/ask", json={"question": question, "lang": lang}).json()

    assert body["status"] == "clarification"
    compare.assert_not_called()


def test_page_shows_only_measured_response_times() -> None:
    page = client.get("/").text

    # Replies the page makes itself carry no time; a sub-millisecond one reads "< 1 ms".
    assert "elapsed_ms: 0" not in page
    assert 'typeof body.elapsed_ms !== "number"' in page and '"< 1"' in page


def test_page_takes_follow_up_context_only_from_answered_questions() -> None:
    page = client.get("/").text

    assert 'if (body.status === "answer" || body.status === "suggestions")' in page


@pytest.mark.parametrize(
    ("question", "lang"),
    [
        ("How has unemployment changed over the last 0 years?", "en"),
        ("Hvernig hefur atvinnuleysi breyst síðustu 0 ár?", "is"),
        ("Unemployment over the last -2 years", "en"),
        ("Atvinnuleysi síðustu 0 mánuði", "is"),
    ],
)
def test_refuses_an_invalid_duration_before_any_request(question: str, lang: str) -> None:
    # It answered with the latest figure, dropping the period.
    with (
        patch("talnaspor.pxweb.requests.get") as get,
        patch("talnaspor.pxweb.requests.post") as post,
    ):
        body = client.post("/ask", json={"question": question, "lang": lang}).json()

    assert body["status"] == "clarification"
    get.assert_not_called()
    post.assert_not_called()


@pytest.mark.parametrize(
    "question",
    [
        "Unemployment over the last 3 months",
        "Unemployment since 2019",
        # An interval, which one year's figure would replace.
        "How has unemployment changed over the past year?",
        "Hvernig breyttist atvinnuleysi í fyrra?",
    ],
)
def test_never_drops_a_relative_period_the_planner_cannot_use(question: str) -> None:
    with patch("talnaspor.app.plan_answer") as single:
        body = client.post("/ask", json={"question": question, "lang": "en"}).json()

    assert body["status"] == "clarification"
    single.assert_not_called()


@pytest.mark.parametrize(
    ("question", "start"),
    [
        ("How has the population changed over the last 1 year?", "latest-1"),
        ("How has the population changed over the last 10 years?", "latest-10"),
        ("How has the population changed over the last 12 months?", "latest-1"),
    ],
)
def test_plans_exactly_the_period_asked_for(question: str, start: str) -> None:
    with patch("talnaspor.app.compare", side_effect=ValueError("stop")) as plan:
        client.post("/ask", json={"question": question, "lang": "en"})

    table, selections, compare_from, _ = plan.call_args.args
    assert (table, selections["Ár"], compare_from) == ("population", "latest", start)


@pytest.mark.parametrize(
    "question", ["How many deaths were there last year?", "Atvinnuleysi í fyrra"]
)
def test_asks_the_planner_for_last_year_by_number(question: str) -> None:
    with patch("talnaspor.app.plan_answer", return_value=None) as single:
        client.post("/ask", json={"question": question, "lang": "en"})

    asked = single.call_args.args[0]
    assert asked.endswith(str(date.today().year - 1))


@pytest.mark.parametrize(
    ("question", "lang"),
    [
        ("Show the population trend over the last 5 years", "en"),
        ("Sýndu tímaröð mannfjöldans síðustu fimm ár", "is"),
        ("Show a chart of unemployment since 2019", "en"),
        ("Population year by year since 2016", "en"),
    ],
)
def test_asks_rather_than_answering_a_series_with_two_endpoints(question: str, lang: str) -> None:
    with (
        patch("talnaspor.app.compare") as curated,
        patch("talnaspor.app.plan_comparison") as catalog,
    ):
        body = client.post("/ask", json={"question": question, "lang": lang}).json()

    assert body["status"] == "clarification"
    curated.assert_not_called()
    catalog.assert_not_called()


@pytest.mark.parametrize("question", ["Unemployment in the year 0", "Atvinnuleysi árið 500"])
def test_refuses_an_invalid_year_on_the_catalog_route(question: str) -> None:
    with patch("talnaspor.app.plan_answer") as single:
        body = client.post("/ask", json={"question": question}).json()

    assert body["status"] == "clarification"
    single.assert_not_called()
