"""Reading the organisation files: what a good file gives and where a bad row is reported."""

from datetime import date
from pathlib import Path

import pytest

from datos.organization.domain.body import BodyKind, BodyLevel
from datos.organization.infrastructure.csv_source import (
    InvalidOrganizationFileError,
    read_bodies,
    read_competences,
    read_holders,
)

BODY_HEADER = "id,kind,level,territory_id,name,parent_id,dir3_id,source_url"
HOLDER_HEADER = "body_id,post_title,holder_name,valid_from,valid_to,source_url"
COMPETENCE_HEADER = "body_id,summary,legal_basis,sector_ids,source_url"
URL = "https://example.org/source"


def _file(tmp_path: Path, header: str, *rows: str, bom: bool = False) -> Path:
    path = tmp_path / "file.csv"
    path.write_text(("﻿" if bom else "") + "\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


# --- what a good file gives ----------------------------------------------------------


def test_reads_bodies_with_their_optional_cells_empty(tmp_path: Path) -> None:
    path = _file(
        tmp_path,
        BODY_HEADER,
        f"ccaa-13-gobierno,executive_head,ccaa,ccaa-13,Presidencia,,,{URL}",
        f"ccaa-13-sanidad,department,ccaa,ccaa-13,Sanidad,ccaa-13-gobierno,A13002915,{URL}",
        f"local-ayuntamiento,local,local,,Ayuntamiento,,,{URL}",
    )

    head, department, local = read_bodies(path)

    assert (head.kind, head.level, head.parent_id, head.dir3_id) == (
        BodyKind.EXECUTIVE_HEAD,
        BodyLevel.CCAA,
        None,
        None,
    )
    assert (department.parent_id, department.dir3_id) == ("ccaa-13-gobierno", "A13002915")
    assert (local.territory_id, local.level) == (None, BodyLevel.LOCAL)


def test_reads_holders_and_a_period_without_an_end(tmp_path: Path) -> None:
    path = _file(
        tmp_path,
        HOLDER_HEADER,
        f"ccaa-13-sanidad,Consejera de Sanidad,A Person,2023-06-17,2026-03-01,{URL}",
        f"ccaa-13-sanidad,Consejero de Sanidad,Another,2026-03-01,,{URL}",
    )

    first, second = read_holders(path)

    assert (first.valid_from, first.valid_to) == (date(2023, 6, 17), date(2026, 3, 1))
    assert (second.holder_name, second.valid_to) == ("Another", None)


def test_reads_competences_with_their_sectors(tmp_path: Path) -> None:
    path = _file(
        tmp_path,
        COMPETENCE_HEADER,
        f"ccaa-13-sanidad,Runs the health service,EA art. 27,health|housing,{URL}",
        f"ccaa-13-sanidad,Another one,EA art. 28,health,{URL}",
        f"ccaa-13-sanidad,With no sector yet,EA art. 29,,{URL}",
    )

    both, one, none = read_competences(path)

    assert both.sector_ids == ("health", "housing")
    assert one.sector_ids == ("health",)
    assert none.sector_ids == ()


def test_the_spaces_around_a_cell_are_dropped_and_a_spreadsheets_byte_order_mark_is_ignored(
    tmp_path: Path,
) -> None:
    path = _file(
        tmp_path,
        BODY_HEADER,
        f"  ccaa-13-gobierno ,executive_head,ccaa,ccaa-13,  Presidencia  ,,,{URL}",
        bom=True,
    )

    [body] = read_bodies(path)

    assert (body.id, body.name) == ("ccaa-13-gobierno", "Presidencia")


def test_a_file_with_only_its_header_has_no_rows(tmp_path: Path) -> None:
    assert read_bodies(_file(tmp_path, BODY_HEADER)) == []


# --- where a bad row is reported -----------------------------------------------------


@pytest.mark.parametrize(
    ("row", "field"),
    [
        (f"x,executive_chief,ccaa,ccaa-13,Name,,,{URL}", "kind"),
        (f"x,executive_head,regional,ccaa-13,Name,,,{URL}", "level"),
        (f"x,executive_head,ccaa,ccaa-13,   ,,,{URL}", "name"),
        (",executive_head,ccaa,ccaa-13,Name,,,{url}".replace("{url}", URL), "id"),
        ("x,executive_head,ccaa,ccaa-13,Name,,,www.example.org", "source_url"),
        ("x,executive_head,ccaa,ccaa-13,Name,,,", "source_url"),
    ],
)
def test_a_bad_body_row_is_reported_with_its_line_and_its_column(
    tmp_path: Path, row: str, field: str
) -> None:
    path = _file(tmp_path, BODY_HEADER, f"ok,executive_head,ccaa,ccaa-13,Name,,,{URL}", row)

    with pytest.raises(InvalidOrganizationFileError, match=rf"file\.csv:3: .*{field}"):
        read_bodies(path)


@pytest.mark.parametrize(
    ("row", "field"),
    [
        (f"x,Post,A Person,17/06/2023,,{URL}", "valid_from"),
        (f"x,Post,A Person,2023-06-17,someday,{URL}", "valid_to"),
        (f"x,Post,,2023-06-17,,{URL}", "holder_name"),
        ("x,Post,A Person,2023-06-17,,source", "source_url"),
    ],
)
def test_a_bad_holder_row_is_reported_with_its_line_and_its_column(
    tmp_path: Path, row: str, field: str
) -> None:
    path = _file(tmp_path, HOLDER_HEADER, row)

    with pytest.raises(InvalidOrganizationFileError, match=rf"file\.csv:2: .*{field}"):
        read_holders(path)


@pytest.mark.parametrize(
    ("row", "field"),
    [
        (f"x,,EA art. 1,health,{URL}", "summary"),
        (f"x,Does things,,health,{URL}", "legal_basis"),
        (f"x,Does things,EA art. 1,health||housing,{URL}", "sector_ids"),
        (f"x,Does things,EA art. 1,health|,{URL}", "sector_ids"),
    ],
)
def test_a_bad_competence_row_is_reported_with_its_line_and_its_column(
    tmp_path: Path, row: str, field: str
) -> None:
    path = _file(tmp_path, COMPETENCE_HEADER, row)

    with pytest.raises(InvalidOrganizationFileError, match=rf"file\.csv:2: .*{field}"):
        read_competences(path)


def test_a_row_with_a_cell_missing_or_one_too_many_is_reported(tmp_path: Path) -> None:
    short = _file(tmp_path, BODY_HEADER, f"x,executive_head,ccaa,ccaa-13,Name,,{URL}")
    long = _file(tmp_path, BODY_HEADER, f"x,executive_head,ccaa,ccaa-13,Name,,,{URL},extra")

    with pytest.raises(InvalidOrganizationFileError, match=r"file\.csv:2: "):
        read_bodies(short)
    with pytest.raises(InvalidOrganizationFileError, match=r"file\.csv:2: "):
        read_bodies(long)


@pytest.mark.parametrize(
    "header",
    [
        "id,kind,level,territory_id,name,parent_id,source_url",  # a column missing
        BODY_HEADER + ",notes",  # a column too many
        "kind,id,level,territory_id,name,parent_id,dir3_id,source_url",  # another order
    ],
)
def test_a_header_that_is_not_the_expected_one_is_reported_with_the_columns(
    tmp_path: Path, header: str
) -> None:
    with pytest.raises(InvalidOrganizationFileError, match=r"file\.csv:1: the columns are"):
        read_bodies(_file(tmp_path, header))


def test_a_missing_file_is_reported_as_such(tmp_path: Path) -> None:
    with pytest.raises(InvalidOrganizationFileError, match=r"nowhere\.csv: not found"):
        read_holders(tmp_path / "nowhere.csv")
