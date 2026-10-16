from pathlib import Path

import pytest

from datos.classification.domain.tag_stoplist import (
    ArticleTag,
    MatchKind,
    Reason,
    StoplistEntry,
    is_listed,
    readable_labels,
    tag_key,
)
from datos.classification.infrastructure.tag_stoplist_file import (
    DEFAULT_STOPLIST,
    InvalidTagStoplistError,
    read_tag_stoplist,
    tag_stoplist_version,
)

STOPLIST = [
    StoplistEntry("okd", MatchKind.EXACT, Reason.OUTLET_MARKER),
    StoplistEntry("portada", MatchKind.PREFIX, Reason.OUTLET_MARKER),
]


def _tag(label: str) -> ArticleTag:
    return ArticleTag(tag_key(label), label)


def test_an_exact_entry_matches_the_whole_tag_only() -> None:
    assert is_listed("okd", STOPLIST)
    assert not is_listed("okd noticias", STOPLIST)
    assert not is_listed("ok", STOPLIST)


def test_a_prefix_entry_matches_the_tag_and_what_follows_it_by_whole_words() -> None:
    assert is_listed("portada", STOPLIST)
    assert is_listed("portada apertura 4", STOPLIST)
    assert not is_listed("portadas", STOPLIST)
    assert not is_listed("la portada", STOPLIST)


def test_the_labels_the_model_reads_keep_their_case_and_order() -> None:
    tags = [_tag("Ceuta"), _tag("OKD"), _tag("Crisis migratoria"), _tag("Portada Local")]

    assert readable_labels(tags, STOPLIST) == ("Ceuta", "Crisis migratoria")


def test_the_key_of_a_label_follows_the_rule_of_the_database() -> None:
    assert tag_key("  Elecciones   Generales ") == "elecciones generales"


def test_the_real_list_removes_what_gives_away_an_outlet_or_an_author() -> None:
    stoplist = read_tag_stoplist(DEFAULT_STOPLIST)
    labels = [
        "Home La Razón",
        "NLPremium",
        "A fondo",
        "Artículos Manuel Marraco",
        "Portada Destacadas",
    ]

    assert readable_labels([_tag(label) for label in labels], stoplist) == ()
    assert readable_labels([_tag("Sanidad"), _tag("Artículo de opinión")], stoplist) == (
        "Sanidad",
        "Artículo de opinión",
    )


def test_the_version_changes_with_the_file(tmp_path: Path) -> None:
    path = tmp_path / "list.csv"
    path.write_text("tag,match,reason\nokd,exact,outlet_marker\n", encoding="utf-8")
    first = tag_stoplist_version(path)
    path.write_text("tag,match,reason\nokd,exact,outlet_marker\ncool,exact,outlet_marker\n")

    assert tag_stoplist_version(path) != first


@pytest.mark.parametrize(
    ("body", "line"),
    [
        ("tag,match,reason\nOKD,exact,outlet_marker\n", 2),  # not in key form
        ("tag,match,reason\nokd,exact,outlet_marker\nx,fuzzy,byline\n", 3),  # unknown match
        ("tag,match,reason\nokd,exact,because\n", 2),  # unknown reason
        ("tag,match,reason\n  ,exact,byline\n", 2),  # empty tag
    ],
)
def test_a_row_that_does_not_validate_is_named_with_its_line(
    tmp_path: Path, body: str, line: int
) -> None:
    path = tmp_path / "list.csv"
    path.write_text(body, encoding="utf-8")

    with pytest.raises(InvalidTagStoplistError, match=f"list.csv:{line}"):
        read_tag_stoplist(path)


def test_a_missing_or_empty_file_is_an_error(tmp_path: Path) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_text("tag,match,reason\n", encoding="utf-8")

    with pytest.raises(InvalidTagStoplistError, match="no entries"):
        read_tag_stoplist(empty)
    with pytest.raises(InvalidTagStoplistError, match="not found"):
        read_tag_stoplist(tmp_path / "missing.csv")
