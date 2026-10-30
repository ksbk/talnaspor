"""Supported Statistics Iceland tables, with units and answer templates."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Measure:
    """How to present one value of a table's measure dimension.

    The template may use {period}, {value} and any dimension code, which is
    replaced by that dimension's selected category label.
    """

    unit: str
    template: str


@dataclass(frozen=True)
class Table:
    """A PX-Web table that Talnaspor can answer questions from."""

    api_url: str
    page_url: str
    time_code: str
    measure_code: str
    measures: dict[str, Measure]


TABLES: dict[str, Table] = {
    "cpi": Table(
        api_url=(
            "https://px.hagstofa.is/pxis/api/v1/is/Efnahagur/visitolur/1_vnv/1_vnv/VIS01000.px"
        ),
        page_url=(
            "https://px.hagstofa.is/pxis/pxweb/is/Efnahagur/"
            "Efnahagur__visitolur__1_vnv__1_vnv/VIS01000.px"
        ),
        time_code="Mánuður",
        measure_code="Liður",
        measures={
            "index": Measure("stig", "{Vísitala} í {period}: {value}"),
            "change_M": Measure("%", "{Vísitala}, mánaðarbreyting í {period}: {value}"),
            "change_A": Measure("%", "{Vísitala}, ársbreyting í {period}: {value}"),
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
        time_code="Ár",
        measure_code="Eining",
        measures={
            "0": Measure("íbúar", "Mannfjöldi 1. janúar {period}: {value}"),
            "1": Measure("%", "Árleg fjölgun íbúa árið {period}: {value}"),
            "2": Measure("manns", "Fjölgun íbúa árið {period}: {value}"),
            "3": Measure("manns", "Aðfluttir umfram brottflutta árið {period}: {value}"),
            "4": Measure("manns", "Fæddir umfram dána árið {period}: {value}"),
        },
    ),
}
