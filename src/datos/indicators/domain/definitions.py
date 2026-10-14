"""The five indicators of `map-governments` (plan.md, confirmed by the author 2026-10-13).

Selectors and INE ids verified against the Tempus API metadata on 2026-10-13. Variable
ids: 3 measure, 18 sex, 137 level of education, 260 concept, 345 housing type,
356 / 357 age group, 429 methodological base.
"""

from datos.indicators.domain.indicator import IndicatorDefinition, Periodicity

INDICATORS: tuple[IndicatorDefinition, ...] = (
    IndicatorDefinition(
        id="population",
        name="Población",
        unit="persons",
        periodicity=Periodicity.QUARTERLY,
        source_table_id="56940",
        description="Estadística Continua de Población, all ages, both sexes.",
        selector={18: "Total", 356: "Todas las edades", 260: "Población", 3: "Número"},
        unit_id=3,
        scale_id=1,
    ),
    IndicatorDefinition(
        id="poverty_or_exclusion_rate",
        name="Tasa de riesgo de pobreza o exclusión social (AROPE)",
        unit="%",
        periodicity=Periodicity.ANNUAL,
        source_table_id="60264",
        description="Encuesta de Condiciones de Vida, AROPE indicator, base 2013.",
        selector={
            356: "Total",
            260: "Tasa de riesgo de pobreza o exclusión social (indicador AROPE)",
            429: "Base 2013",
        },
        unit_id=101,
        scale_id=1,
    ),
    IndicatorDefinition(
        id="higher_education_share_16plus",
        name="Población de 16 y más años con educación superior",
        unit="%",
        periodicity=Periodicity.QUARTERLY,
        source_table_id="65289",
        description="Encuesta de Población Activa, share of people aged 16 and over whose"
        " highest level is higher education, both sexes.",
        selector={357: "Total", 18: "Ambos sexos", 137: "Educación superior", 3: "Porcentaje"},
        unit_id=101,
        scale_id=1,
    ),
    IndicatorDefinition(
        id="unemployment_rate",
        name="Tasa de paro",
        unit="%",
        periodicity=Periodicity.QUARTERLY,
        source_table_id="14506",
        description="Encuesta de Población Activa, unemployment rate, both sexes, all ages.",
        selector={3: "Tasa de paro de la población", 18: "Ambos sexos", 356: "Total"},
        unit_id=135,
        scale_id=1,
    ),
    IndicatorDefinition(
        id="housing_price_index",
        name="Índice de Precios de Vivienda",
        # Base verified on 2026-10-13: the four quarters of 2025 average exactly 100.
        unit="index (2025 = 100)",
        periodicity=Periodicity.QUARTERLY,
        source_table_id="80270",
        description="Índice de Precios de Vivienda, general (new and second-hand), base 2025.",
        selector={345: "General", 3: "Índice"},
        unit_id=133,
        scale_id=1,
    ),
)
