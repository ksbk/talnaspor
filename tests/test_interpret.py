import pytest

from talnaspor.answer import LATEST, before_latest
from talnaspor.catalog import question_words
from talnaspor.interpret import (
    Clarification,
    Interpretation,
    curated_terms_cover,
    follow_up,
    interpret,
    narrow,
    normalize,
    without_periods,
)


def test_normalizes_icelandic_letters() -> None:
    assert normalize("Þjóðin ÆTTI að vita verðbólguna") == "thjodin aetti ad vita verdbolguna"


@pytest.mark.parametrize(
    ("question", "selections"),
    [
        (
            "Hver var verðbólgan í september 2026?",
            {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"},
        ),
        ("Hver er verðbólgan núna?", {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"}),
        (
            "Hver er vísitala neysluverðs?",
            {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "index"},
        ),
        (
            "Mánaðarbreyting vísitölu neysluverðs í janúar 2025",
            {"Mánuður": "2025M01", "Vísitala": "CPI", "Liður": "change_M"},
        ),
        (
            "Verðbólga án húsnæðis í mars 2026",
            {"Mánuður": "2026M03", "Vísitala": "CPILH", "Liður": "change_A"},
        ),
        (
            "What was inflation in May 2025?",
            {"Mánuður": "2025M05", "Vísitala": "CPI", "Liður": "change_A"},
        ),
        (
            "May I ask what inflation is now?",
            {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"},
        ),
    ],
)
def test_interprets_cpi_questions(question: str, selections: dict[str, str]) -> None:
    assert interpret(question) == Interpretation("cpi", selections)


@pytest.mark.parametrize(
    ("question", "selections"),
    [
        ("Hver var mannfjöldinn árið 2020?", {"Ár": "2020", "Eining": "0"}),
        ("Hvað búa margir á Íslandi?", {"Ár": LATEST, "Eining": "0"}),
        ("What is the population of Iceland?", {"Ár": LATEST, "Eining": "0"}),
        ("Hver var fjölgun íbúa árið 2024?", {"Ár": "2024", "Eining": "2"}),
        ("Population growth rate in 2024", {"Ár": "2024", "Eining": "1"}),
        ("Hve margir aðfluttir umfram brottflutta 2023?", {"Ár": "2023", "Eining": "3"}),
        ("Fæddir umfram dána á Íslandi 2023, hve margir íbúar?", {"Ár": "2023", "Eining": "4"}),
    ],
)
def test_interprets_population_questions(question: str, selections: dict[str, str]) -> None:
    assert interpret(question) == Interpretation("population", selections)


@pytest.mark.parametrize(
    ("question", "message"),
    [
        ("Hvernig er veðrið?", "fann ekki svar"),
        ("Verðbólga og mannfjöldi árið 2024", "eitt efni"),
        ("Verðbólga árið 2024", "Tilgreindu mánuð"),
        ("Verðbólga í september", "Tilgreindu ár"),
        ("Verðbólga í janúar, febrúar og mars 2026", "tvo mánuði"),
        ("Mannfjöldi 2005, 2015 og 2025", "tvö ár"),
        ("Verðbólga í janúar 2024, 2025 og 2026", "hvert ár"),
    ],
)
def test_asks_for_clarification(question: str, message: str) -> None:
    result = interpret(question)

    assert isinstance(result, Clarification)
    assert message in result.message


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "How has Iceland's population changed?",
            Interpretation("population", {"Ár": LATEST, "Eining": "0"}, before_latest(10)),
        ),
        (
            "Hvernig hefur mannfjöldinn breyst frá 2015 til 2025?",
            Interpretation("population", {"Ár": "2025", "Eining": "0"}, "2015"),
        ),
        (
            "Mannfjöldi 2015 og 2025",
            Interpretation("population", {"Ár": "2025", "Eining": "0"}, "2015"),
        ),
        (
            "Population growth since 2000",
            Interpretation("population", {"Ár": LATEST, "Eining": "0"}, "2000"),
        ),
        (
            "Hvernig hefur verðbólgan þróast?",
            Interpretation(
                "cpi",
                {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"},
                before_latest(12),
            ),
        ),
        (
            "Breyting vísitölu neysluverðs frá janúar 2025 til september 2026",
            Interpretation(
                "cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "index"}, "2025M01"
            ),
        ),
        (
            "Verðbólga í janúar og febrúar 2026",
            Interpretation(
                "cpi", {"Mánuður": "2026M02", "Vísitala": "CPI", "Liður": "change_A"}, "2026M01"
            ),
        ),
        (
            "Verðbólga í september 2025 og 2026",
            Interpretation(
                "cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"}, "2025M09"
            ),
        ),
    ],
)
def test_interprets_change_over_time(question: str, expected: Interpretation) -> None:
    assert interpret(question) == expected


def test_annual_change_is_not_a_comparison() -> None:
    result = interpret("Ársbreyting vísitölu neysluverðs í september 2026")

    assert isinstance(result, Interpretation)
    assert result.compare_from is None


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "What was the monthly change in the CPI in September 2026?",
            Interpretation("cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_M"}),
        ),
        (
            "What was the annual change in CPI in September 2026?",
            Interpretation("cpi", {"Mánuður": "2026M09", "Vísitala": "CPI", "Liður": "change_A"}),
        ),
        (
            "Population change in 2024",
            Interpretation("population", {"Ár": "2024", "Eining": "2"}),
        ),
        (
            "Verðbólga frá janúar 2025",
            Interpretation(
                "cpi", {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"}, "2025M01"
            ),
        ),
    ],
)
def test_change_within_one_period_is_not_a_comparison(
    question: str, expected: Interpretation
) -> None:
    assert interpret(question) == expected


def test_asks_which_change_for_cpi_in_one_month() -> None:
    result = interpret("Hver var breytingin á vísitölu neysluverðs í september 2026?")

    assert isinstance(result, Clarification)
    assert "mánaðarbreytingu eða ársbreytingu" in result.message


@pytest.mark.parametrize(
    ("question", "selections"),
    [
        ("Hvað fjölgaði íbúum mikið árið 2024?", {"Ár": "2024", "Eining": "2"}),
        ("Hver var fjöldi íbúa á Íslandi 2020?", {"Ár": "2020", "Eining": "0"}),
    ],
)
def test_recognizes_inflected_population_words(question: str, selections: dict[str, str]) -> None:
    assert interpret(question) == Interpretation("population", selections)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "Hver var mannfjöldinn í fyrra?",
            Interpretation("population", {"Ár": before_latest(1), "Eining": "0"}),
        ),
        (
            # Change over the last year shows both 1 January figures, as longer spans do.
            "Hvernig breyttist mannfjöldinn í fyrra?",
            Interpretation("population", {"Ár": LATEST, "Eining": "0"}, before_latest(1)),
        ),
        (
            "Inflation over the last 12 months",
            Interpretation("cpi", {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"}),
        ),
        (
            "Hvað er verðlag að hækka mikið?",
            Interpretation("cpi", {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"}),
        ),
        (
            "Hve margir bjuggu á Íslandi árið 1990?",
            Interpretation("population", {"Ár": "1990", "Eining": "0"}),
        ),
    ],
)
def test_interprets_last_year_and_wording(question: str, expected: Interpretation) -> None:
    assert interpret(question) == expected


@pytest.mark.parametrize(
    ("question", "message"),
    [
        ("What was inflation last year?", "Tilgreindu mánuð"),
        ("What was inflation two months ago?", "afstæð tímabil"),
        ("Hver var verðbólgan í síðasta mánuði?", "afstæð tímabil"),
    ],
)
def test_never_ignores_relative_periods(question: str, message: str) -> None:
    result = interpret(question)

    assert isinstance(result, Clarification)
    assert message in result.message


@pytest.mark.parametrize(
    "question",
    [
        "Hvernig er veðrið?",
        "Verðbólga og mannfjöldi árið 2024",
        "Verðbólga árið 2024",
        "Verðbólga í september",
        "Verðbólga í janúar, febrúar og mars 2026",
        "Mannfjöldi 2005, 2015 og 2025",
        "Verðbólga í janúar 2024, 2025 og 2026",
        "Hver var breytingin á vísitölu neysluverðs í september 2026?",
        "What was inflation last year?",
        "What was inflation two months ago?",
        "Population over the last 3 months",
    ],
)
def test_every_clarification_has_english_wording(question: str) -> None:
    result = interpret(question)

    assert isinstance(result, Clarification)
    assert result.text("is") == result.message
    assert result.text("en") == result.message_en
    assert result.message_en and result.message_en != result.message
    assert not set("áðéíóúýþæö") & set(result.message_en.lower())


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "Hvernig hefur verðbólgan þróast síðustu tíu árin?",
            Interpretation(
                "cpi",
                {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"},
                before_latest(120),
            ),
        ),
        (
            "Inflation over the past 6 months",
            Interpretation(
                "cpi",
                {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"},
                before_latest(6),
            ),
        ),
        (
            "How has the population changed over the last five years?",
            Interpretation("population", {"Ár": LATEST, "Eining": "0"}, before_latest(5)),
        ),
        (
            "Mannfjöldi síðustu 20 ár",
            Interpretation("population", {"Ár": LATEST, "Eining": "0"}, before_latest(20)),
        ),
        (
            "How has the population of Iceland changed over the last decade?",
            Interpretation("population", {"Ár": LATEST, "Eining": "0"}, before_latest(10)),
        ),
        (
            # "Síðasta ár" (last year) is a prefix of this, and must not match it.
            "Hvernig hefur mannfjöldinn breyst síðasta áratuginn?",
            Interpretation("population", {"Ár": LATEST, "Eining": "0"}, before_latest(10)),
        ),
        (
            "Inflation over the past decade",
            Interpretation(
                "cpi",
                {"Mánuður": LATEST, "Vísitala": "CPI", "Liður": "change_A"},
                before_latest(120),
            ),
        ),
    ],
)
def test_compares_over_relative_spans(question: str, expected: Interpretation) -> None:
    assert interpret(question) == expected


def test_keeps_years_outside_the_usual_range() -> None:
    # Ignoring such a year would answer for the latest period instead.
    assert interpret("What was the population in 1650?") == Interpretation(
        "population", {"Ár": "1650", "Eining": "0"}
    )


@pytest.mark.parametrize(
    ("question", "covered"),
    [
        ("Hve mikið hækkaði verðlag á milli ára í júlí 2026?", True),
        ("What was inflation in May 2025?", True),
        ("How big is Iceland's population today?", True),
        ("Íbúafjöldi landsins 2010", True),
        ("Hvað eru margir íbúar í Reykjavík?", False),
        ("Hver var verðbólgan á matvörum?", False),
        ("What is the inflation rate in Norway?", False),
        ("Hver er meðalaldur íbúa á Íslandi?", False),
        ("How has the population of Iceland changed over the last decade?", True),
        ("How many people lived in Iceland on 1 January 2026?", True),
        ("Hvernig hefur mannfjöldinn breyst síðasta áratuginn?", True),
    ],
)
def test_knows_which_words_the_curated_answers_cover(question: str, covered: bool) -> None:
    assert curated_terms_cover(question_words(question)) is covered


@pytest.mark.parametrize(
    ("question", "previous", "understood"),
    [
        (
            "What about women?",
            "What is the population of Iceland in 2026?",
            "What is the population of Iceland in 2026, women?",
        ),
        (
            # A restriction the previous question states is replaced, not added.
            "What about men?",
            "What was the unemployment rate for women in 2025?",
            "What was the unemployment rate for men in 2025?",
        ),
        (
            "And in 2020?",
            "What was the unemployment rate for women in 2025?",
            "What was the unemployment rate for women in 2020?",
        ),
        (
            "En hjá körlum?",
            "Hvert var atvinnuleysi árið 2025?",
            "Hvert var atvinnuleysi árið 2025, körlum?",
        ),
        (
            "Og árið 2024?",
            "Hvert var atvinnuleysi kvenna árið 2025?",
            "Hvert var atvinnuleysi kvenna árið 2024?",
        ),
        (
            "En í Reykjavík?",
            "Hvað búa margir á Íslandi?",
            "Hvað búa margir á Íslandi, í Reykjavík?",
        ),
        (
            "And for ages 16-24?",
            "What was the unemployment rate in 2024?",
            "What was the unemployment rate in 2024, ages 16-24?",
        ),
    ],
)
def test_narrows_the_previous_question_by_a_follow_up(
    question: str, previous: str, understood: str
) -> None:
    restriction = follow_up(question)

    assert restriction is not None
    assert narrow(previous, restriction) == understood


@pytest.mark.parametrize(
    "question",
    [
        # A new topic is a question of its own, not a restriction of the previous one.
        "What about unemployment?",
        "Hver er verðbólgan?",
        "And how many people live in Iceland?",
        "Mannfjöldi kvenna 2026",
    ],
)
def test_recognizes_only_the_defined_follow_up_forms(question: str) -> None:
    assert follow_up(question) is None


POPULATION_NOW = {"Ár": LATEST, "Eining": "0"}


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        # A comparison interval: both endpoints, the change and the percent change.
        (
            "How has the population of Iceland changed over the last century?",
            Interpretation("population", POPULATION_NOW, before_latest(100)),
        ),
        (
            "How has Iceland's population evolved over the past century?",
            Interpretation("population", POPULATION_NOW, before_latest(100)),
        ),
        (
            "Hvernig hefur mannfjöldinn breyst síðustu öld?",
            Interpretation("population", POPULATION_NOW, before_latest(100)),
        ),
        (
            "Hvernig hefur mannfjöldinn breyst síðustu hundrað árin?",
            Interpretation("population", POPULATION_NOW, before_latest(100)),
        ),
        (
            "How has the population of Iceland changed over the last year?",
            Interpretation("population", POPULATION_NOW, before_latest(1)),
        ),
        (
            "Hvernig hefur mannfjöldinn breyst síðasta árið?",
            Interpretation("population", POPULATION_NOW, before_latest(1)),
        ),
        # A point in time: one figure, that many years before the latest.
        (
            "What was the population of Iceland a decade ago?",
            Interpretation("population", {"Ár": before_latest(10), "Eining": "0"}),
        ),
        (
            "What was the population 10 years ago?",
            Interpretation("population", {"Ár": before_latest(10), "Eining": "0"}),
        ),
        (
            "Hver var mannfjöldinn fyrir áratug?",
            Interpretation("population", {"Ár": before_latest(10), "Eining": "0"}),
        ),
        (
            "Hver var mannfjöldinn fyrir tíu árum?",
            Interpretation("population", {"Ár": before_latest(10), "Eining": "0"}),
        ),
        (
            "What was inflation ten years ago?",
            Interpretation(
                "cpi", {"Mánuður": before_latest(120), "Vísitala": "CPI", "Liður": "change_A"}
            ),
        ),
        # Since a point in time: a comparison from it to the latest.
        (
            "How has the population changed since a decade ago?",
            Interpretation("population", POPULATION_NOW, before_latest(10)),
        ),
    ],
)
def test_tells_points_in_time_from_intervals(question: str, expected: Interpretation) -> None:
    assert interpret(question) == expected


def test_asks_for_one_period_when_two_are_named() -> None:
    result = interpret("What was the population in 2020, ten years ago?")

    assert isinstance(result, Clarification)
    assert "one period" in result.message_en


def test_explains_an_unsupported_relative_period_without_a_misleading_example() -> None:
    result = interpret("What was inflation two months ago?")

    assert isinstance(result, Clarification)
    assert "last month" not in result.message_en
    assert "afstæð tímabil" in result.message


@pytest.mark.parametrize(
    ("question", "covered"),
    [
        ("Hvernig hefur mannfjöldinn breyst síðustu öld?", True),
        ("Hver var mannfjöldinn fyrir áratug?", True),
        ("What was the population of Iceland a decade ago?", True),
        # "Old" outside "síðustu öld" is not a period: average age is another measure.
        ("How old is Iceland's population?", False),
    ],
)
def test_reads_relative_periods_as_periods_not_topics(question: str, covered: bool) -> None:
    assert curated_terms_cover(question_words(without_periods(question))) is covered


def comparison(table: str, back: int | str) -> Interpretation:
    start = back if isinstance(back, str) else before_latest(back)
    if table == "cpi":
        return Interpretation("cpi", {"Mánuður": LATEST, **ANNUAL}, start)
    return Interpretation("population", POPULATION_NOW, start)


ANNUAL = {"Vísitala": "CPI", "Liður": "change_A"}
CLARIFY = None


# Every topic with every kind of time expression, in both languages: a period the question
# states is used (a comparison or a point) or refused (a clarification), never replaced by
# a default. A default applies only when no period is stated.
@pytest.mark.parametrize(
    ("question", "expected"),
    [
        # Population: last 12 months (was 2016-2026, or the latest year alone).
        ("How has the population changed over the last 12 months?", comparison("pop", 1)),
        ("Hvernig hefur mannfjöldinn breyst síðustu 12 mánuði?", comparison("pop", 1)),
        ("Population over the last 12 months", comparison("pop", 1)),
        # Population: last year, decade, century, since.
        ("How has the population changed over the last year?", comparison("pop", 1)),
        ("Hvernig breyttist mannfjöldinn í fyrra?", comparison("pop", 1)),
        ("How has the population changed over the last decade?", comparison("pop", 10)),
        ("Hvernig hefur mannfjöldinn breyst síðasta áratuginn?", comparison("pop", 10)),
        ("How has the population changed over the last century?", comparison("pop", 100)),
        ("Hvernig hefur mannfjöldinn breyst síðustu öld?", comparison("pop", 100)),
        ("How has the population changed since 2016?", comparison("pop", "2016")),
        ("Hvernig hefur mannfjöldinn breyst frá 2016?", comparison("pop", "2016")),
        # Population: a point in time.
        (
            "What was the population a decade ago?",
            Interpretation("population", {"Ár": before_latest(10), "Eining": "0"}),
        ),
        (
            "Hver var mannfjöldinn fyrir áratug?",
            Interpretation("population", {"Ár": before_latest(10), "Eining": "0"}),
        ),
        (
            "Hve margir bjuggu á Íslandi 1. janúar 2026?",
            Interpretation("population", {"Ár": "2026", "Eining": "0"}),
        ),
        (
            "How many people lived in Iceland on 1 January 2026?",
            Interpretation("population", {"Ár": "2026", "Eining": "0"}),
        ),
        # Population: a named month is refused (was silently 1 January of that year).
        ("What was the population of Iceland on 1 December 2025?", CLARIFY),
        ("Hver var mannfjöldinn í september 2025?", CLARIFY),
        ("How did the population change between January and June 2025?", CLARIFY),
        # Population: no period stated, so the stated default applies.
        ("How has the population changed?", comparison("pop", 10)),
        ("Hvernig hefur mannfjöldinn breyst?", comparison("pop", 10)),
        # Inflation: last 12 months is the annual change.
        (
            "Inflation over the last 12 months",
            Interpretation("cpi", {"Mánuður": LATEST, **ANNUAL}),
        ),
        (
            "Verðbólga síðustu 12 mánuði",
            Interpretation("cpi", {"Mánuður": LATEST, **ANNUAL}),
        ),
        ("What was the monthly inflation in the last 12 months?", CLARIFY),
        # Inflation: decade, century, a point in time, a named month.
        ("How has inflation changed over the last decade?", comparison("cpi", 120)),
        ("Hvernig hefur verðbólgan breyst síðasta áratuginn?", comparison("cpi", 120)),
        ("How has inflation changed over the last century?", comparison("cpi", 1200)),
        (
            "What was inflation a decade ago?",
            Interpretation("cpi", {"Mánuður": before_latest(120), **ANNUAL}),
        ),
        (
            "Hver var verðbólgan fyrir áratug?",
            Interpretation("cpi", {"Mánuður": before_latest(120), **ANNUAL}),
        ),
        (
            "Hver var verðbólgan í september 2026?",
            Interpretation("cpi", {"Mánuður": "2026M09", **ANNUAL}),
        ),
        # Inflation: a year alone, last year, or since a year needs a month.
        ("What was inflation last year?", CLARIFY),
        ("Verðbólga árið 2024", CLARIFY),
        ("How has inflation changed since 2016?", CLARIFY),
        # A zero-length span is no period: refused, not the default (was ten years).
        ("How much did the population of Iceland grow in the last 0 years?", CLARIFY),
        ("Hvernig breyttist mannfjöldinn síðustu 0 ár?", CLARIFY),
        ("Inflation over the last 0 months", CLARIFY),
        ("Verðbólga síðustu 0 mánuði", CLARIFY),
        # Inflation: no period stated, so the latest.
        ("Hver er verðbólgan?", Interpretation("cpi", {"Mánuður": LATEST, **ANNUAL})),
        ("What is inflation now?", Interpretation("cpi", {"Mánuður": LATEST, **ANNUAL})),
    ],
)
def test_uses_or_refuses_every_stated_period(
    question: str, expected: Interpretation | None
) -> None:
    result = interpret(question)

    if expected is CLARIFY:
        assert isinstance(result, Clarification)
    else:
        assert result == expected
