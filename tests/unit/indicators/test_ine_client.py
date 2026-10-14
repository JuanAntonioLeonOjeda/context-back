import hashlib
import json
from pathlib import Path

import httpx
import pytest

from datos.http import USER_AGENT, build_client
from datos.indicators.infrastructure.ine_client import IneClient, InvalidIneResponseError

FIXTURES = Path("tests/fixtures/ine")
BASE = "https://servicios.ine.es/wstempus/js/ES/"


def _client(routes: dict[str, bytes], seen: list[httpx.Request] | None = None) -> IneClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        for fragment, body in routes.items():
            if fragment in str(request.url):
                return httpx.Response(200, content=body)
        return httpx.Response(404)

    return IneClient(
        build_client(httpx.MockTransport(handler)), BASE, delay_s=0, sleep=lambda _: None
    )


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_series_of_a_table_carry_their_community_code_or_none_for_national() -> None:
    client = _client({"SERIES_TABLA/14506": _fixture("series_14506.json")})

    series = {s.code: s for s in client.series_of_table("14506")}

    assert series["EPA452576"].community_code == "18"  # Ceuta
    assert series["EPA452440"].community_code == "01"  # Andalucía
    assert series["EPA452434"].community_code is None  # Total Nacional
    assert series["EPA452576"].value_of(18).name == "Ambos sexos"  # type: ignore[union-attr]


def test_quarterly_data_keep_the_ine_period_codes() -> None:
    client = _client({"DATOS_SERIE/EPA452576": _fixture("data_EPA452576.json")})

    data = client.series_data("EPA452576", last=4)

    assert data.unit_id == 135 and data.scale_id == 1
    assert {d.period_code for d in data.data} <= {19, 20, 21, 22}
    assert all(d.value is not None for d in data.data)


def test_a_value_the_ine_does_not_publish_is_none_not_zero() -> None:
    # Ceuta, doctorate (old table 66104): the INE publishes no value for 2011 and 2012.
    client = _client({"DATOS_SERIE/EPA686811": _fixture("data_EPA686811.json")})

    data = client.series_data("EPA686811", last=8)

    missing = [d.year for d in data.data if d.value is None]
    assert missing == [2011, 2012]


def test_a_secret_value_is_none() -> None:
    body = json.loads(_fixture("data_ECV6221.json"))
    body["Data"][0]["Secreto"] = True
    client = _client({"DATOS_SERIE/ECV6221": json.dumps(body).encode()})

    data = client.series_data("ECV6221", last=3)

    assert data.data[0].value is None and data.data[1].value is not None


def test_a_series_in_thousands_reports_its_scale() -> None:
    client = _client({"DATOS_SERIE/EPA432730": _fixture("data_EPA432730.json")})

    data = client.series_data("EPA432730", last=3)

    assert data.scale_id == 4  # "Miles"


def test_the_download_records_the_url_and_the_sha256_of_the_body() -> None:
    body = _fixture("data_ECV6221.json")
    client = _client({"DATOS_SERIE/ECV6221": body})

    data = client.series_data("ECV6221", last=3)

    assert data.download.url == f"{BASE}DATOS_SERIE/ECV6221?nult=3"
    assert data.download.sha256 == hashlib.sha256(body).hexdigest()


def test_requests_identify_the_project_and_wait_between_calls() -> None:
    seen: list[httpx.Request] = []
    waits: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=_fixture("data_ECV6221.json"))

    client = IneClient(
        build_client(httpx.MockTransport(handler)), BASE, delay_s=0.3, sleep=waits.append
    )

    client.series_data("ECV6221", last=3)
    client.series_data("ECV6221", last=3)

    assert [r.headers["user-agent"] for r in seen] == [USER_AGENT, USER_AGENT]
    assert waits == [0.3, 0.3]


def test_a_response_for_another_series_is_refused() -> None:
    client = _client({"DATOS_SERIE/EPA452576": _fixture("data_ECV6221.json")})

    with pytest.raises(InvalidIneResponseError, match="asked for EPA452576"):
        client.series_data("EPA452576", last=3)


def test_an_unexpected_body_is_refused() -> None:
    client = _client({"DATOS_SERIE/X": b'{"error": "not a series"}'})

    with pytest.raises(InvalidIneResponseError):
        client.series_data("X", last=1)
