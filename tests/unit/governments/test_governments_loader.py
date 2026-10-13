from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pytest

from datos.governments.application.load_governments import (
    InvalidGovernmentsDatasetError,
    dataset_problems,
    load_governments,
)
from datos.governments.domain.competence import Competence, Sector
from datos.governments.domain.government_term import GovernmentTerm, PartyRole, TermParty
from datos.governments.domain.party import Party
from datos.governments.infrastructure.csv_source import (
    InvalidGovernmentsFileError,
    read_parties,
    read_terms,
)

SINCE = date(2020, 1, 1)
TODAY = date(2026, 10, 13)
DATA = Path("data/governments")
SOURCE = "https://example.org/source"
PARTY_A = Party("party-a", "Party A", "PA", "#112233")
PARTY_B = Party("party-b", "Party B", "PB", "#445566")


def _term(
    valid_from: date = SINCE,
    valid_to: date | None = None,
    *,
    territory_id: str = "ccaa-01",
    party_ids: tuple[str, ...] = ("party-a",),
) -> GovernmentTerm:
    return GovernmentTerm(
        territory_id=territory_id,
        president_name="President",
        valid_from=valid_from,
        valid_to=valid_to,
        parties=tuple(TermParty(p, PartyRole.GOVERNING, SOURCE) for p in party_ids),
        is_caretaker=False,
        source_url=SOURCE,
    )


class FakeRepository:
    def __init__(self, territory_ids: set[str]) -> None:
        self._territory_ids = territory_ids
        self.replaced: tuple[list[Party], list[GovernmentTerm]] | None = None

    def government_territory_ids(self) -> set[str]:
        return self._territory_ids

    def replace_all(self, parties: Sequence[Party], terms: Sequence[GovernmentTerm]) -> None:
        self.replaced = (list(parties), list(terms))

    def replace_competences(
        self, sectors: Sequence[Sector], competences: Sequence[Competence]
    ) -> None:
        self.competences = (list(sectors), list(competences))


# --- the versioned dataset itself ------------------------------------------------------


def test_the_versioned_dataset_passes_every_rule() -> None:
    parties = read_parties(DATA / "parties.csv")
    terms = read_terms(DATA / "government_terms.csv", DATA / "government_term_parties.csv")
    territory_ids = {"es"} | {f"ccaa-{n:02d}" for n in range(1, 20)}

    assert dataset_problems(parties, terms, territory_ids, since=SINCE, today=TODAY) == []


# --- validation ------------------------------------------------------------------------


def test_a_valid_dataset_has_no_problems() -> None:
    assert dataset_problems([PARTY_A], [_term()], {"ccaa-01"}, since=SINCE, today=TODAY) == []


def test_reports_every_problem_at_once() -> None:
    terms = [
        _term(date(2021, 1, 1), territory_id="ccaa-01", party_ids=("party-x",)),
        _term(territory_id="ccaa-99"),
    ]

    problems = dataset_problems([PARTY_A, PARTY_B], terms, {"ccaa-01"}, since=SINCE, today=TODAY)

    assert any("ccaa-01 from 2021-01-01: unknown party party-x" in p for p in problems)
    assert any("ccaa-01: no government from 2020-01-01 to 2021-01-01" in p for p in problems)
    assert any("ccaa-99 from 2020-01-01: territory has no government" in p for p in problems)
    assert any("party party-b is not used by any term" in p for p in problems)


def test_reports_a_term_without_a_governing_party() -> None:
    term = GovernmentTerm("ccaa-01", "P", SINCE, None, (), False, SOURCE)

    problems = dataset_problems([PARTY_A], [term], {"ccaa-01"}, since=SINCE, today=TODAY)

    assert "ccaa-01 from 2020-01-01: no governing party" in problems


def test_nothing_is_written_when_the_dataset_is_invalid() -> None:
    repository = FakeRepository({"ccaa-01"})

    with pytest.raises(InvalidGovernmentsDatasetError):
        load_governments(repository, [PARTY_A], [], since=SINCE, today=TODAY)

    assert repository.replaced is None


def test_writes_the_dataset_when_it_is_valid() -> None:
    repository = FakeRepository({"ccaa-01"})

    load_governments(repository, [PARTY_A], [_term()], since=SINCE, today=TODAY)

    assert repository.replaced is not None


# --- reading the CSVs ------------------------------------------------------------------

TERMS_HEADER = "territory_id,valid_from,valid_to,president_name,is_caretaker,source_url,notes\n"
PARTIES_HEADER = "territory_id,valid_from,party_id,role,source_url\n"


def _files(tmp_path: Path, terms: str, term_parties: str) -> tuple[Path, Path]:
    terms_path, term_parties_path = tmp_path / "terms.csv", tmp_path / "term_parties.csv"
    terms_path.write_text(TERMS_HEADER + terms, encoding="utf-8")
    term_parties_path.write_text(PARTIES_HEADER + term_parties, encoding="utf-8")
    return terms_path, term_parties_path


def test_reads_a_term_with_its_parties_and_an_open_end(tmp_path: Path) -> None:
    terms, parties = _files(
        tmp_path,
        f"ccaa-01,2020-01-01,,President,false,{SOURCE},a note\n",
        f"ccaa-01,2020-01-01,party-a,governing,{SOURCE}\n",
    )

    [term] = read_terms(terms, parties)

    assert term.valid_to is None
    assert term.parties == (TermParty("party-a", PartyRole.GOVERNING, SOURCE),)


def test_rejects_a_party_row_without_a_term(tmp_path: Path) -> None:
    terms, parties = _files(
        tmp_path,
        f"ccaa-01,2020-01-01,,President,false,{SOURCE},\n",
        f"ccaa-02,2020-01-01,party-a,governing,{SOURCE}\n",
    )

    with pytest.raises(InvalidGovernmentsFileError, match="ccaa-02 from 2020-01-01"):
        read_terms(terms, parties)


def test_rejects_an_unknown_role_with_the_line_number(tmp_path: Path) -> None:
    terms, parties = _files(
        tmp_path,
        f"ccaa-01,2020-01-01,,President,false,{SOURCE},\n",
        f"ccaa-01,2020-01-01,party-a,opposition,{SOURCE}\n",
    )

    with pytest.raises(InvalidGovernmentsFileError, match=r"term_parties\.csv line 2"):
        read_terms(terms, parties)


def test_rejects_a_duplicate_party_id(tmp_path: Path) -> None:
    path = tmp_path / "parties.csv"
    path.write_text("id,name,short_name,colour_hex\na,A,A,#000000\na,B,B,#111111\n", "utf-8")

    with pytest.raises(InvalidGovernmentsFileError, match="duplicate party id a"):
        read_parties(path)
