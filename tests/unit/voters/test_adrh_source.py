"""The ADRH reader on a trimmed real answer of the INE (operation 353, 2023, filtered to every
municipality's mean net income per person)."""

import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from datos.http import build_client
from datos.voters.infrastructure.adrh_source import AdrhSource, InvalidAdrhResponseError

ANSWER = Path("tests/fixtures/ine/adrh/metadataoperacion_353_municipal_income_2023.json")


def _source(body: bytes, seen: list[str] | None = None) -> AdrhSource:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(str(request.url))
        return httpx.Response(200, content=body)

    return AdrhSource(build_client(httpx.MockTransport(handler)))


def test_asks_for_every_municipality_s_income_per_person_of_the_year_in_one_request() -> None:
    seen: list[str] = []

    download = _source(ANSWER.read_bytes(), seen).incomes(2023)

    assert len(seen) == 1
    assert "DATOS_METADATAOPERACION/353?p=12&g1=19:&g2=482:284048&date=20230101" in seen[0]
    assert download.url == seen[0]
    assert len(download.sha256) == 64


def test_reads_each_municipality_with_its_ine_code_and_series() -> None:
    incomes = _source(ANSWER.read_bytes()).incomes(2023).incomes

    by_code = {i.municipality_code: i for i in incomes}
    assert set(by_code) == {"02003", "35016", "38038"}
    assert by_code["02003"].euros_per_person == Decimal("14611.0")
    assert by_code["02003"].series_code == "ADRH103921"
    assert all(i.year == 2023 for i in incomes)


def test_a_value_hidden_by_statistical_secrecy_gives_no_income() -> None:
    incomes = _source(ANSWER.read_bytes()).incomes(2023).incomes

    assert len(incomes) == 3  # the fixture's fourth series has no value for 2023


def test_a_refusal_of_the_api_is_an_error_that_shows_its_message() -> None:
    refusal = b'{"status" : "No puede mostrarse por restricciones de volumen"}'

    with pytest.raises(InvalidAdrhResponseError, match="restricciones de volumen"):
        _source(refusal).incomes(2023)


def test_a_series_that_is_not_a_municipal_income_per_person_is_an_error() -> None:
    other = ANSWER.read_text(encoding="utf-8").replace(
        "Renta neta media por persona", "Renta neta media por hogar"
    )

    with pytest.raises(InvalidAdrhResponseError, match="not a municipal income per person"):
        _source(other.encode()).incomes(2023)


def test_a_value_of_another_year_is_not_taken_for_the_year_asked() -> None:
    series = json.loads(ANSWER.read_text(encoding="utf-8"))
    albacete = next(s for s in series if s["COD"] == "ADRH103921")
    albacete["Data"][0]["Anyo"] = 2022

    incomes = _source(json.dumps(series).encode()).incomes(2023).incomes

    assert "02003" not in {i.municipality_code for i in incomes}
