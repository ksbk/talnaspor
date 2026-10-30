"""Supported Statistics Iceland tables, with units and answer templates."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Measure:
    """How to present one value of a table's measure dimension, in Icelandic and English.

    A template may use {period}, {value} and any dimension code, which is replaced by
    that dimension's selected category label in the template's language.
    """

    unit: str
    template: str
    unit_en: str
    template_en: str


@dataclass(frozen=True)
class Table:
    """A PX-Web table that Talnaspor can answer questions from.

    labels_en holds Statistics Iceland's own English labels for categories, by dimension
    code and value code, as published in the English version of the table.
    """

    api_url: str
    page_url: str
    title_en: str
    page_url_en: str
    time_code: str
    measure_code: str
    measures: dict[str, Measure]
    labels_en: dict[str, dict[str, str]] = field(default_factory=dict)


TABLES: dict[str, Table] = {
    "cpi": Table(
        api_url=(
            "https://px.hagstofa.is/pxis/api/v1/is/Efnahagur/visitolur/1_vnv/1_vnv/VIS01000.px"
        ),
        page_url=(
            "https://px.hagstofa.is/pxis/pxweb/is/Efnahagur/"
            "Efnahagur__visitolur__1_vnv__1_vnv/VIS01000.px"
        ),
        title_en="Consumer price index and changes, base 1988=100",
        page_url_en=(
            "https://px.hagstofa.is/pxen/pxweb/en/Efnahagur/"
            "Efnahagur__visitolur__1_vnv__1_vnv/VIS01000.px"
        ),
        time_code="Mánuður",
        measure_code="Liður",
        measures={
            "index": Measure(
                "stig", "{Vísitala} í {period}: {value}", "points", "{Vísitala}, {period}: {value}"
            ),
            "change_M": Measure(
                "%",
                "{Vísitala}, mánaðarbreyting í {period}: {value}",
                "%",
                "{Vísitala}, monthly change in {period}: {value}",
            ),
            "change_A": Measure(
                "%",
                "{Vísitala}, ársbreyting í {period}: {value}",
                "%",
                "{Vísitala}, annual change in {period}: {value}",
            ),
        },
        labels_en={
            "Vísitala": {
                "CPI": "Consumer price index",
                "CPILH": "Consumer price index less housing cost",
            },
            "Liður": {
                "index": "Index",
                "change_M": "Monthly change, %",
                "change_A": "Annual change, %",
            },
        },
    ),
    "population": Table(
        api_url=(
            "https://px.hagstofa.is/pxis/api/v1/is/Ibuar/mannfjoldi/1_yfirlit/"
            "Yfirlit_mannfjolda/MAN00000.px"
        ),
        page_url=(
            "https://px.hagstofa.is/pxis/pxweb/is/Ibuar/"
            "Ibuar__mannfjoldi__1_yfirlit__Yfirlit_mannfjolda/MAN00000.px"
        ),
        title_en="Population - key figures 1703-2026",
        page_url_en=(
            "https://px.hagstofa.is/pxen/pxweb/en/Ibuar/"
            "Ibuar__mannfjoldi__1_yfirlit__Yfirlit_mannfjolda/MAN00000.px"
        ),
        time_code="Ár",
        measure_code="Eining",
        measures={
            "0": Measure(
                "íbúar",
                "Mannfjöldi 1. janúar {period}: {value}",
                "people",
                "Population 1 January {period}: {value}",
            ),
            "1": Measure(
                "%",
                "Árleg fjölgun íbúa árið {period}: {value}",
                "%",
                "Population increase in {period}: {value}",
            ),
            "2": Measure(
                "manns",
                "Fjölgun íbúa árið {period}: {value}",
                "people",
                "Population increase in {period}: {value}",
            ),
            "3": Measure(
                "manns",
                "Aðfluttir umfram brottflutta árið {period}: {value}",
                "people",
                "Net immigration in {period}: {value}",
            ),
            "4": Measure(
                "manns",
                "Fæddir umfram dána árið {period}: {value}",
                "people",
                "Natural increase in {period}: {value}",
            ),
        },
        labels_en={
            "Eining": {
                "0": "Population 1 January",
                "1": "Population increase, %",
                "2": "Population increase",
                "3": "Net immigration",
                "4": "Natural increase",
            },
        },
    ),
}
