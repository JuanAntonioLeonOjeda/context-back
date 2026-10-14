# Indicators

The statistics shown on a community's card (`GET /communities/{id}/indicators`). Decided with the
author on 2026-10-13 (`specs/map-governments/plan.md`, ADR-0012); definitions in
`src/datos/indicators/domain/definitions.py`. Loaded from the INE Tempus API
(`https://servicios.ine.es/wstempus/js/ES/`) by `python -m datos.indicators load`.

| Indicator (`id`) | INE table | Unit | Frequency |
|---|---|---|---|
| `population` | [56940](https://www.ine.es/jaxiT3/Tabla.htm?t=56940), Estadística Continua de Población, all ages, both sexes | persons | quarterly |
| `poverty_or_exclusion_rate` | [60264](https://www.ine.es/jaxiT3/Tabla.htm?t=60264), Encuesta de Condiciones de Vida, AROPE, base 2013 | % of the population | annual |
| `higher_education_share_16plus` | [65289](https://www.ine.es/jaxiT3/Tabla.htm?t=65289), Encuesta de Población Activa, highest level "Educación superior", both sexes, aged 16 and over | % of people aged 16 and over | quarterly |
| `unemployment_rate` | [14506](https://www.ine.es/jaxiT3/Tabla.htm?t=14506), Encuesta de Población Activa, both sexes, all ages | % of the active population | quarterly |
| `housing_price_index` | [80270](https://www.ine.es/jaxiT3/Tabla.htm?t=80270), Índice de Precios de Vivienda, general (new and second-hand) | index, 2025 = 100 | quarterly |

## How a value is chosen and stored

- **One series per community**, chosen by the metadata the INE publishes for each series (which
  variable has which value), never by its name. The load stops with an error if a community has
  no series or more than one, or if the INE changes the unit or the scale a definition expects.
- **Stored as the INE published it**, with its series code, the INE period (year and period code:
  28 is the year, 19 to 22 the quarters) and the download that produced it (URL, date and SHA-256
  of the response). Observations are append-only: a revised value is a new row, and the current
  value is the one of the latest download (view `current_observations`).
- **No value is no row.** The API answers `null` for an indicator without data, never 0.
- **Scale** (the INE sometimes publishes in thousands) is stored with the indicator and applied
  when reading.

## Verified on 2026-10-13

- The five tables return a series for each of the 19 communities, Ceuta and Melilla included.
- The education table first chosen (66104) breaks the population down by level of education only
  until 2013; table 65289 publishes the share directly, in the current classification.
- The housing price index is base **2025 = 100** (the four quarters of 2025 average exactly
  100.0), not the base 2015 of the INE methodology pages.

## Out of scope for now

Household income (ADRH) is published by province; aggregating it to a community needs a method of
its own, decided in `context-voters`. Deflators and the treatment of series breaks arrive in the
same phase.
