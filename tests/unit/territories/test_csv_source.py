from pathlib import Path

import pytest

from datos.territories.csv_source import InvalidTerritoriesFileError, read_territories
from datos.territories.territory import Level, Territory, parents_first

HEADER = "id,ine_code,name,level,parent_id\n"
REAL_CSV = Path("data/territories/territories.csv")


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "territories.csv"
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def test_reads_empty_cells_as_missing(tmp_path: Path) -> None:
    path = _write(tmp_path, "es,,España,state,\nccaa-13,13,Comunidad de Madrid,ccaa,es\n")

    assert read_territories(path) == [
        Territory("es", None, "España", Level.STATE, None),
        Territory("ccaa-13", "13", "Comunidad de Madrid", Level.CCAA, "es"),
    ]


def test_rejects_the_whole_file_when_one_level_is_unknown(tmp_path: Path) -> None:
    path = _write(tmp_path, "es,,España,state,\nccaa-13,13,Madrid,region,es\n")

    with pytest.raises(InvalidTerritoriesFileError, match="line 3"):
        read_territories(path)


def test_rejects_a_duplicate_id(tmp_path: Path) -> None:
    path = _write(tmp_path, "ccaa-13,13,A,ccaa,es\nccaa-13,13,B,ccaa,es\n")

    with pytest.raises(InvalidTerritoriesFileError, match="duplicate id ccaa-13"):
        read_territories(path)


def test_orders_parents_before_children() -> None:
    province = Territory("prov-28", "28", "Madrid", Level.PROVINCE, "ccaa-13")
    community = Territory("ccaa-13", "13", "Comunidad de Madrid", Level.CCAA, "es")
    state = Territory("es", None, "España", Level.STATE, None)

    assert parents_first([province, community, state]) == [state, community, province]


def test_the_versioned_file_has_the_state_19_communities_and_52_provinces() -> None:
    territories = read_territories(REAL_CSV)
    by_level = {level: [t for t in territories if t.level is level] for level in Level}

    assert len(by_level[Level.STATE]) == 1
    assert len(by_level[Level.CCAA]) == 19
    assert len(by_level[Level.PROVINCE]) == 52
    ids = {t.id for t in territories}
    assert all(t.parent_id in ids for t in territories if t.parent_id is not None)
