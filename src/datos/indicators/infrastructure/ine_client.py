"""Client of the INE Tempus API (`servicios.ine.es/wstempus/js/ES/`).

Two calls: the series of a table with their metadata (`SERIES_TABLA/{table}?tip=M`), and
the data of one series (`DATOS_SERIE/{code}?nult=N`). Responses are untrusted input,
validated with Pydantic at this edge; the SHA-256 of each body is kept so a stored value
can be traced to exactly what was received (ADR-0012).
"""

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

import httpx
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from datos.http import download

DEFAULT_BASE_URL = "https://servicios.ine.es/wstempus/js/ES/"
# The series listing of the population table (56940) is 3.6 MB on its own.
MAX_RESPONSE_BYTES = 20_000_000
# The INE asks for moderate use; one request at a time with a short pause.
REQUEST_DELAY_S = 0.3
COMMUNITY_VARIABLE_ID = 70  # "Comunidades y Ciudades Autónomas", value code = INE code


class InvalidIneResponseError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class VariableValue:
    variable_id: int
    name: str
    code: str


@dataclass(frozen=True, slots=True)
class IneSeries:
    code: str
    name: str
    unit_id: int
    scale_id: int
    periodicity_id: int
    values: tuple[VariableValue, ...]

    def value_of(self, variable_id: int) -> VariableValue | None:
        return next((v for v in self.values if v.variable_id == variable_id), None)

    @property
    def community_code(self) -> str | None:
        """Two-digit INE code of the community; None for national or other breakdowns."""
        value = self.value_of(COMMUNITY_VARIABLE_ID)
        return value.code if value and value.code else None


@dataclass(frozen=True, slots=True)
class IneDatum:
    year: int
    period_code: int
    # Decimal, not float: "has the value changed?" must compare exactly what was published.
    value: Decimal | None  # None when the INE publishes no value or marks it secret


@dataclass(frozen=True, slots=True)
class Download:
    url: str
    sha256: str


@dataclass(frozen=True, slots=True)
class IneSeriesData:
    series_code: str
    unit_id: int
    scale_id: int
    data: tuple[IneDatum, ...]
    download: Download


class IneClient:
    def __init__(
        self,
        client: httpx.Client,
        base_url: str = DEFAULT_BASE_URL,
        *,
        delay_s: float = REQUEST_DELAY_S,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._base_url = base_url
        self._delay_s = delay_s
        self._sleep = sleep

    def series_of_table(self, table_id: str) -> list[IneSeries]:
        body, _ = self._get(f"{self._base_url}SERIES_TABLA/{table_id}?tip=M")
        raw = _parse(_SERIES_LIST, body)
        return [_series(r) for r in raw]

    def series_data(self, series_code: str, *, last: int) -> IneSeriesData:
        url = f"{self._base_url}DATOS_SERIE/{series_code}?nult={last}"
        body, sha256 = self._get(url)
        raw = _parse(_SERIES_DATA, body)
        received = raw.COD
        if received != series_code:
            raise InvalidIneResponseError(f"asked for {series_code}, got {received}")
        return IneSeriesData(
            series_code=raw.COD,
            unit_id=raw.FK_Unidad,
            scale_id=raw.FK_Escala,
            data=tuple(
                IneDatum(d.Anyo, d.FK_Periodo, None if d.Secreto else d.Valor) for d in raw.Data
            ),
            download=Download(url, sha256),
        )

    def _get(self, url: str) -> tuple[bytes, str]:
        self._sleep(self._delay_s)
        body = download(self._client, url, accept="application/json", max_bytes=MAX_RESPONSE_BYTES)
        return body, hashlib.sha256(body).hexdigest()


# --- the INE's JSON, as received (field names are the INE's) ---------------------------


class _RawValue(BaseModel):
    FK_Variable: int
    Nombre: str
    Codigo: str = ""


class _RawSeries(BaseModel):
    COD: str
    Nombre: str
    FK_Unidad: int
    FK_Escala: int
    FK_Periodicidad: int
    MetaData: list[_RawValue] = Field(default_factory=list)


class _RawDatum(BaseModel):
    Anyo: int
    FK_Periodo: int
    Valor: Decimal | None = None
    Secreto: bool = False


class _RawSeriesData(BaseModel):
    COD: str
    FK_Unidad: int
    FK_Escala: int
    Data: list[_RawDatum]


_SERIES_LIST = TypeAdapter(list[_RawSeries])
_SERIES_DATA = TypeAdapter(_RawSeriesData)


def _parse[T](adapter: TypeAdapter[T], body: bytes) -> T:
    try:
        return adapter.validate_json(body)
    except ValidationError as error:
        raise InvalidIneResponseError(
            f"unexpected INE response: {error.error_count()} errors"
        ) from error


def _series(raw: _RawSeries) -> IneSeries:
    return IneSeries(
        code=raw.COD,
        name=raw.Nombre.strip(),
        unit_id=raw.FK_Unidad,
        scale_id=raw.FK_Escala,
        periodicity_id=raw.FK_Periodicidad,
        values=tuple(VariableValue(v.FK_Variable, v.Nombre, v.Codigo) for v in raw.MetaData),
    )
