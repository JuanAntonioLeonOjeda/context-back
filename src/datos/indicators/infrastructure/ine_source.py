"""Adapts the INE client to the `IndicatorSource` port of the use case."""

from datos.indicators.application.load_indicators import PublishedValue, SeriesValues
from datos.indicators.domain.indicator import SeriesInfo
from datos.indicators.infrastructure.ine_client import IneClient


class IneIndicatorSource:
    def __init__(self, client: IneClient) -> None:
        self._client = client

    def series_of_table(self, table_id: str) -> list[SeriesInfo]:
        return [
            SeriesInfo(
                code=s.code,
                community_code=s.community_code,
                values={v.variable_id: v.name for v in s.values},
            )
            for s in self._client.series_of_table(table_id)
        ]

    def series_values(self, series_code: str, *, last: int) -> SeriesValues:
        data = self._client.series_data(series_code, last=last)
        return SeriesValues(
            unit_id=data.unit_id,
            scale_id=data.scale_id,
            values=[PublishedValue(d.year, d.period_code, d.value) for d in data.data],
            url=data.download.url,
            sha256=data.download.sha256,
        )
