# Geometry

`ccaa.geojson`: the 19 autonomous communities, simplified for the web map. GeoJSON
FeatureCollection in WGS84-compatible ETRS89 longitude/latitude, one feature per
community with `id` = territory id (`ccaa-NN`, as in `data/territories/`).

## Source

- **Product:** Base de Datos de Límites Jurisdiccionales de España, Instituto Geográfico
  Nacional (IGN). INSPIRE `AdministrativeUnit`, 2nd order (autonomous communities).
- **Download:** IGN ATOM service, `https://www.ign.es/atom/dataset_feeds/lin_lim_mun.es.xml`
  → `https://centrodedescargas.cnig.es/CentroDescargas/documentos/atom/au/lineas_limite_gml.zip`,
  member `au_AdministrativeUnit_2ndOrder0.gml` (file timestamp 2026-08-10).
- **Downloaded:** 2026-10-13, SHA-256
  `5bd73c530af995c05da8d9ff4e3d293f62d0dc91c5e48ee773fe881716c108a6`. Kept in
  `data/raw/ign/` (not in git).
- **Licence:** CC BY 4.0 under Orden FOM/2807/2015 (IGN licence document,
  `https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf`). The
  attribution must be visible at the foot of the map. As a derived work:

  > Obra derivada de Base de Datos de Límites Jurisdiccionales de España 2026 CC-BY 4.0 ign.es

  The official short identifier of the product comes from the selector at
  `scne.es/productos.html` (interactive only; not checked yet). Until then the full
  product name is used.

## How it is built

```bash
uv run python -m datos.territories build-geometry   # needs the `geo` group (shapely)
```

1. The 19 communities are read from the GML; unit 20 ("territories outside any
   community") is skipped.
2. They are simplified together as a coverage (tolerance 0.005°, about 450 m), so shared
   borders stay shared.
3. Islets under about 1 km² that touch no other community are dropped; a community's
   largest part and enclaves (Castilla-La Mancha inside Madrid) are kept.
4. Coordinates are snapped to a 0.001° grid; holes that no community occupies are filled,
   holes holding an enclave (Treviño and Villaverde de Trucíos inside the País Vasco) stay.

Result on 2026-10-13: 223 KB, no overlaps, no gaps between communities. The Canary Islands
inset and the markers for Ceuta and Melilla are layout, drawn by the web app.
