# Territories

`territories.csv`: the State anchor row (`es`), the 19 communities (Ceuta and Melilla
included) and the 52 INE provinces (50 provinces plus Ceuta, 51, and Melilla, 52, which
INE codes as provinces for statistics).

- Source: INE, "Relación de comunidades y ciudades autónomas con sus provincias",
  https://www.ine.es/daco/daco42/codmun/cod_ccaa_provincia.htm (read 2026-10-13).
- Codes are copied as published. Names are INE's with the article moved to the front
  ("Rioja, La" → "La Rioja", "Madrid, Comunidad de" → "Comunidad de Madrid").
- Columns: `id` (`es`, `ccaa-NN`, `prov-NN`), `ine_code` (empty for `es`), `name`,
  `level` (`state | ccaa | province`), `parent_id`.

Load with `uv run python -m datos.territories load`.
