import json
from datetime import date
from unittest.mock import patch

import pytest
import requests

from talnaspor.answer import Answer
from talnaspor.catalog import TableHit
from talnaspor.planner import (
    Choice,
    _accounts_for,
    _counts_together,
    _time_variable,
    plan_answer,
    select,
)
from talnaspor.pxweb import PXMetadata

URL = "https://px.hagstofa.is/pxis/api/v1/is/Samfelag/vinnumarkadur/VIN01002.px"


def metadata(title: str = "Atvinnuþátttaka, atvinnuleysi 1991-2025") -> PXMetadata:
    return PXMetadata.model_validate(
        {
            "title": title,
            "variables": [
                # Index codes, with the years only in the labels.
                {"code": "Ár", "text": "Ár", "values": ["0", "1"], "valueTexts": ["2024", "2025"]},
                {
                    "code": "Kyn",
                    "text": "Kyn",
                    "values": ["0", "1", "2"],
                    "valueTexts": ["Karlar og konur", "Karlar", "Konur"],
                },
                {
                    "code": "Aldur",
                    "text": "Aldur",
                    "values": ["0", "1", "2"],
                    "valueTexts": ["Alls", "16-24 ára", "16-74 ára"],
                },
                {
                    "code": "Eining",
                    "text": "Eining",
                    "values": ["0", "1"],
                    "valueTexts": ["Atvinnuleysi", "Vinnuafl"],
                },
            ],
        }
    )


def hit(title: str = "Atvinnuþátttaka, atvinnuleysi 1991-2025") -> TableHit:
    return TableHit(
        title=title,
        title_en="Activity rate, unemployment 1991-2025",
        folders=["Samfélag", "Vinnumarkaður"],
        updated="2026-02-19T09:00:00",
        page_url="https://px.hagstofa.is/pxis/pxweb/is/Samfelag/Samfelag__vinnumarkadur/VIN01002.px",
        page_url_en="https://px.hagstofa.is/pxen/pxweb/en/Samfelag/Samfelag__vinnumarkadur/VIN01002.px",
        api_url=URL,
        score=10.0,
    )


def response(labels: dict[str, tuple[str, str]], value: float) -> str:
    """A JSON-stat2 response for one cell; labels map a dimension to (code, label)."""
    return json.dumps(
        {
            "class": "dataset",
            "label": "Atvinnuþátttaka",
            "source": "Hagstofa Íslands",
            "id": list(labels),
            "size": [1] * len(labels),
            "dimension": {
                code: {
                    "label": code,
                    "category": {"index": {value_code: 0}, "label": {value_code: label}},
                }
                for code, (value_code, label) in labels.items()
            },
            "value": [value],
        }
    )


def test_finds_time_dimension_from_labels_when_codes_are_indexes() -> None:
    time_variable = _time_variable(metadata())

    assert time_variable is not None
    assert time_variable.code == "Ár"


@pytest.mark.parametrize(
    ("weights", "year", "expected"),
    [
        # Unnamed dimensions take their totals; the latest period is the latest label.
        ({"atvinnuleysi": 1.0}, None, {"Ár": "1", "Kyn": "0", "Aldur": "0", "Eining": "0"}),
        # A year selects that period by its label.
        ({"atvinnuleysi": 1.0}, "2024", {"Ár": "0", "Kyn": "0", "Aldur": "0", "Eining": "0"}),
        # "konur" names both "Konur" and "Karlar og konur"; the specific one is meant.
        (
            {"atvinnuleysi": 1.0, "konur": 0.5},
            None,
            {"Ár": "1", "Kyn": "2", "Aldur": "0", "Eining": "0"},
        ),
        # Numbers name categories exactly.
        (
            {"atvinnuleysi": 1.0, "ara": 1.0, "16": 1.0, "74": 1.0},
            None,
            {"Ár": "1", "Kyn": "0", "Aldur": "2", "Eining": "0"},
        ),
    ],
)
def test_settles_every_dimension(
    weights: dict[str, float], year: str | None, expected: dict[str, str]
) -> None:
    assert select(metadata(), weights, year) == (expected, None)


def test_reports_dimensions_it_cannot_settle() -> None:
    selections, unsettled = select(metadata(), {"vinnumarkadur": 1.0}, None)

    assert selections is None
    assert [variable.code for variable in unsettled or []] == ["Eining"]


def test_rejects_a_year_the_table_does_not_cover() -> None:
    assert select(metadata(), {"atvinnuleysi": 1.0}, "2030") == (None, None)


def test_requires_the_table_to_account_for_every_question_word() -> None:
    assert _accounts_for({"atvinnuleysi", "konur"}, [], metadata(), hit())
    assert not _accounts_for({"atvinnuleysi", "reykjavik"}, [], metadata(), hit())


def test_accounts_for_words_in_the_english_title_from_metadata() -> None:
    # The catalog lacks some English titles; the table's English metadata has them.
    untitled = hit().model_copy(update={"title_en": None})

    assert not _accounts_for({"activity"}, [], metadata(), untitled)
    assert _accounts_for({"activity"}, [], metadata(), untitled, None, "Activity rate 1991-2025")


def stays(title: str, units: list[str] | None = None) -> PXMetadata:
    variables = [{"code": "Mánuður", "text": "Mánuður", "values": ["2025M08"]}]
    if units:
        variables.append(
            {"code": "Eining", "text": "Eining", "values": ["0", "1"], "valueTexts": units}
        )
    return PXMetadata.model_validate({"title": title, "variables": variables})


def test_skips_a_table_that_sums_what_the_question_names_one_of() -> None:
    # Hotels and guesthouses together do not answer a question about hotels.
    joined = stays("Gistinætur á hótelum og gistiheimilum 2017-")
    untitled = hit().model_copy(update={"title_en": None})

    assert _counts_together({"hotel", "gistinaetur"}, [], joined, untitled, None)
    assert not _counts_together({"hotelum", "gistiheimilum"}, [], joined, untitled, None)
    assert not _counts_together({"gistinaetur"}, [], joined, untitled, None)


def test_keeps_a_table_whose_dimension_separates_the_joined_things() -> None:
    separate = stays("Gistinætur og gestakomur á hótelum", ["Gestakomur", "Gistinætur"])
    untitled = hit().model_copy(update={"title_en": None})

    assert not _counts_together({"gistinaetur", "hotelum"}, [], separate, untitled, None)


def test_skips_tables_restricted_to_a_group_the_question_does_not_name() -> None:
    title = "Námsmenn - Atvinnuþátttaka, atvinnuleysi 2003-2025"

    assert not _accounts_for({"atvinnuleysi"}, [], metadata(title), hit(title))
    assert _accounts_for({"atvinnuleysi", "namsmenn"}, [], metadata(title), hit(title))


def run(
    question: str, data: str, today: date = date(2026, 10, 30)
) -> tuple[Answer | Choice | None, int]:
    """Plan an answer offline; also return how many data requests were made."""
    with (
        patch("talnaspor.planner._get_metadata", return_value=metadata()),
        patch("talnaspor.planner.get_data", return_value=data) as get_data,
        patch("talnaspor.planner.get_units", return_value="Fjöldi/hlutfall"),
    ):
        result = plan_answer(question, [hit()], today=today)
    return result, get_data.call_count


def test_answers_with_labels_unit_and_source() -> None:
    data = response(
        {
            "Ár": ("1", "2025"),
            "Kyn": ("2", "Konur"),
            "Aldur": ("0", "Alls"),
            "Eining": ("0", "Atvinnuleysi"),
        },
        4.3,
    )

    result, _ = run("Atvinnuleysi kvenna", data)

    assert isinstance(result, Answer)
    assert result.kind == "catalog"
    assert result.text == (
        "Konur, Atvinnuleysi (2025): 4,3 (Fjöldi/hlutfall). "
        "Heimild: Hagstofa Íslands, Atvinnuþátttaka, atvinnuleysi 1991-2025."
    )
    assert result.period == "2025"
    assert result.labels["Aldur"] == "Alls"
    assert result.page_url == hit().page_url


@pytest.mark.parametrize(
    "question", ["Atvinnuleysi kvenna 1. janúar 2025", "Unemployment of women on 1 January 2025"]
)
def test_reads_the_first_of_january_as_the_year(question: str) -> None:
    # Not the month 2025M01, which an annual table lacks, and "1" names no category.
    data = response(
        {
            "Ár": ("1", "2025"),
            "Kyn": ("2", "Konur"),
            "Aldur": ("0", "Alls"),
            "Eining": ("0", "Atvinnuleysi"),
        },
        4.3,
    )

    result, _ = run(question, data)

    assert isinstance(result, Answer)
    assert result.period == "2025"
    assert result.selections == {"Ár": "1", "Kyn": "2", "Aldur": "0", "Eining": "0"}


def test_skips_series_that_have_stopped() -> None:
    assert run("Atvinnuleysi", "{}", today=date(2030, 1, 1)) == (None, 0)


def test_offers_the_one_choice_that_would_settle_a_table() -> None:
    result, calls = run("Atvinnuþátttaka á vinnumarkaði", "{}")

    assert isinstance(result, Choice)
    assert result.dimension == "Eining"
    assert result.options == ["Atvinnuleysi", "Vinnuafl"]
    assert "Atvinnuleysi, Vinnuafl" in result.message()
    assert calls == 0


def test_does_not_answer_questions_about_several_years() -> None:
    assert run("Atvinnuleysi 2024 og 2025", "{}") == (None, 0)


def test_rejects_a_response_for_different_selections() -> None:
    wrong = response(
        {
            "Ár": ("1", "2025"),
            "Kyn": ("1", "Karlar"),
            "Aldur": ("0", "Alls"),
            "Eining": ("0", "Atvinnuleysi"),
        },
        4.4,
    )

    assert run("Atvinnuleysi kvenna", wrong)[0] is None


def test_answer_payload_is_serializable() -> None:
    data = response(
        {
            "Ár": ("1", "2025"),
            "Kyn": ("0", "Karlar og konur"),
            "Aldur": ("0", "Alls"),
            "Eining": ("0", "Atvinnuleysi"),
        },
        4.3,
    )
    result, _ = run("Atvinnuleysi", data)

    assert isinstance(result, Answer)
    assert json.loads(result.model_dump_json())["value_text"] == "4,3 (Fjöldi/hlutfall)"


def english_metadata() -> PXMetadata:
    return PXMetadata.model_validate(
        {
            "title": "Activity rate, unemployment 1991-2025",
            "variables": [
                {
                    "code": "Year",
                    "text": "Year",
                    "values": ["0", "1"],
                    "valueTexts": ["2024", "2025"],
                },
                {
                    "code": "Sex",
                    "text": "Sex",
                    "values": ["0", "1", "2"],
                    "valueTexts": ["Males and females", "Males", "Females"],
                },
                {
                    "code": "Age",
                    "text": "Age",
                    "values": ["0", "1", "2"],
                    "valueTexts": ["Total", "16-24 years", "16-74 years"],
                },
                {
                    "code": "Unit",
                    "text": "Unit",
                    "values": ["0", "1"],
                    "valueTexts": ["Unemployment", "Labour force"],
                },
            ],
        }
    )


def run_english(question: str, data: str, english: PXMetadata | None) -> Answer | Choice | None:
    def by_language(url: str) -> PXMetadata:
        if "/pxen/" not in url:
            return metadata()
        if english is None:
            raise requests.HTTPError("404 Not Found")
        return english

    with (
        patch("talnaspor.planner._get_metadata", side_effect=by_language),
        patch("talnaspor.planner.get_data", return_value=data),
        patch("talnaspor.planner.get_units", return_value="Number/percent") as get_units,
    ):
        result = plan_answer(question, [hit()], today=date(2026, 10, 30), lang="en")
    if isinstance(result, Answer):
        assert get_units.call_args.args[3] == "en"
    return result


WOMEN_2025 = {
    "Ár": ("1", "2025"),
    "Kyn": ("2", "Konur"),
    "Aldur": ("0", "Alls"),
    "Eining": ("0", "Atvinnuleysi"),
}


def test_answers_in_english_with_the_tables_english_labels() -> None:
    result = run_english("Unemployment females", response(WOMEN_2025, 4.3), english_metadata())

    assert isinstance(result, Answer)
    assert result.text == (
        "Females, Unemployment (2025): 4.3 (Number/percent). "
        "Source: Statistics Iceland, Activity rate, unemployment 1991-2025."
    )
    assert result.labels["Kyn"] == "Females"
    assert result.dimension_labels["Kyn"] == "Sex"
    assert result.page_url == hit().page_url_en


def test_answers_with_icelandic_labels_when_a_table_has_no_english_version() -> None:
    result = run_english("Atvinnuleysi kvenna", response(WOMEN_2025, 4.3), None)

    assert isinstance(result, Answer)
    assert result.labels["Kyn"] == "Konur"
    assert result.text.endswith("(Labels are in Icelandic: this table has no English version.)")
    assert result.page_url == hit().page_url


def monthly_metadata() -> PXMetadata:
    return PXMetadata.model_validate(
        {
            "title": "Atvinnulausir 2003-2026",
            "variables": [
                {
                    "code": "Mánuður",
                    "text": "Mánuður",
                    "values": ["2025M08", "2025M09", "2025M10"],
                    "time": True,
                },
                {"code": "Eining", "text": "Eining", "values": ["0"], "valueTexts": ["Fjöldi"]},
            ],
        }
    )


def test_selects_exactly_the_month_asked_for() -> None:
    selections, _ = select(monthly_metadata(), {}, None, None, "2025M09")

    assert selections == {"Mánuður": "2025M09", "Eining": "0"}


def test_does_not_answer_a_month_from_a_table_without_it() -> None:
    assert select(monthly_metadata(), {}, None, None, "2025M12") == (None, None)
    # An annual table cannot answer for a month either.
    assert select(metadata(), {"atvinnuleysi": 1.0}, None, None, "2025M03") == (None, None)


def test_skips_annual_tables_for_a_question_about_a_month() -> None:
    assert run("Atvinnuleysi í mars 2025", "{}") == (None, 0)


@pytest.mark.parametrize(
    "question",
    [
        # Only a fragment of the title matches: "laun" (wages) and "launuðu" (paid).
        "Atvinnulaun",
        # A general-knowledge question that shares a word with statistical tables.
        "What is the capital of Iceland?",
    ],
)
def test_does_not_answer_without_a_full_title_match(question: str) -> None:
    assert run(question, "{}") == (None, 0)


def test_skips_categories_labelled_with_accounting_codes() -> None:
    coded = response(
        {
            "Ár": ("1", "2025"),
            "Kyn": ("0", "Karlar og konur"),
            "Aldur": ("0", "Alls"),
            "Eining": ("0", "00-00-00 Atvinnuleysi"),
        },
        4.3,
    )

    assert run("Atvinnuleysi", coded)[0] is None
