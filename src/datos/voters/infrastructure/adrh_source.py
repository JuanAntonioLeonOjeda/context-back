"""Reader of the INE's Atlas de Distribución de Renta de los Hogares (ADRH, operation 353): the
mean net income per person of every municipality for a year, in one request.

Checked on 2026-11-06 (specs/context-voters/plan.md): the provincial tables of the ADRH are too
big for the API ("No puede mostrarse por restricciones de volumen", e.g. table 30824), even
filtered by concept, because they carry every census section. `DATOS_METADATAOPERACION` filters
the whole operation by variables instead: variable 19 ("Municipios", every value) and
482:284048 ("Renta neta media por persona"). For 2023 it answered 8,139 series in 4.6 MB, each a
municipality with its 5-digit INE code in the metadata, after about six minutes: hence the long
read timeout of this one request.
"""

import hashlib
from decimal import ROUND_HALF_UP, Decimal

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from datos.http import download
from datos.voters.application.load_income import IncomeDownload
from datos.voters.domain.income import MunicipalIncome

BASE_URL = "https://servicios.ine.es/wstempus/js/ES/"
MAX_RESPONSE_BYTES = 20_000_000
# The INE took about 6 minutes to build the 2023 answer: 15 minutes leaves room without hanging
# forever. Connecting is still quick or fails.
SLOW_READ = httpx.Timeout(20.0, read=900.0)
_FILTERS = "p=12&g1=19:&g2=482:284048"  # annual; every municipality; income per person


class InvalidAdrhResponseError(Exception):
    """The INE answered something this reader does not understand."""


class _Meta(BaseModel):
    T3_Variable: str | None = None
    Nombre: str
    Codigo: str | None = None


class _Datum(BaseModel):
    Anyo: int
    Valor: float | None = None


class _Series(BaseModel):
    COD: str
    MetaData: list[_Meta]
    Data: list[_Datum]


_SERIES = TypeAdapter(list[_Series])


class AdrhSource:
    def __init__(self, client: httpx.Client, *, base_url: str = BASE_URL) -> None:
        self._client = client
        self._base_url = base_url

    def incomes(self, year: int) -> IncomeDownload:
        url = f"{self._base_url}DATOS_METADATAOPERACION/353?{_FILTERS}&date={year}0101&tip=AM"
        body = download(
            self._client,
            url,
            accept="application/json",
            max_bytes=MAX_RESPONSE_BYTES,
            timeout=SLOW_READ,
        )
        series = _parse(body)
        incomes = tuple(income for s in series if (income := _municipal_income(s, year)))
        return IncomeDownload(url, hashlib.sha256(body).hexdigest(), incomes)


_CENT = Decimal("0.01")


def _municipal_income(series: _Series, year: int) -> MunicipalIncome | None:
    """The series' value for `year`, or None when the INE hides it (statistical secrecy)."""
    by_variable = {m.T3_Variable: m for m in series.MetaData if m.T3_Variable}
    municipality = by_variable.get("Municipios")
    concept = by_variable.get("SALDOS CONTABLES")
    # The filters ask for these exactly; anything else means the API changed under us.
    if (
        municipality is None
        or concept is None
        or concept.Nombre.strip() != ("Renta neta media por persona")
    ):
        raise InvalidAdrhResponseError(f"series {series.COD}: not a municipal income per person")
    code = municipality.Codigo or ""
    if len(code) != 5 or not code.isdigit():
        raise InvalidAdrhResponseError(f"series {series.COD}: municipality code {code!r}")
    value = next((d.Valor for d in series.Data if d.Anyo == year), None)
    if value is None:
        return None
    # The INE writes whole euros as floats (14611.0); str() keeps them exact for Decimal. Cents,
    # as the column stores them (numeric(10, 2), which rounds halves up too): a value with more
    # decimals would otherwise never equal its stored self and be stored again on every load.
    euros = Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)
    return MunicipalIncome(code, year, euros, series.COD)


def _parse(body: bytes) -> list[_Series]:
    try:
        return _SERIES.validate_json(body)
    except ValidationError as error:
        # The API answers {"status": "..."} instead of a list when it refuses a request.
        raise InvalidAdrhResponseError(f"unexpected INE response: {body[:200]!r}") from error
