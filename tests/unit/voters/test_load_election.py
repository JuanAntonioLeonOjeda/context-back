"""The checks before an election is stored, and when the use case loads, skips or refuses."""

from dataclasses import replace
from datetime import date

import pytest

from datos.voters.application.load_election import (
    ElectionAlreadyLoadedError,
    InvalidElectionError,
    LoadOutcome,
    load_election,
)
from datos.voters.domain.election import (
    Candidature,
    CandidatureVotes,
    Election,
    ElectionFile,
    ElectionKind,
    MunicipalResult,
    file_problems,
)

PROVINCES = {"prov-35", "prov-38"}
SHA = "a" * 64

PSOE = Candidature("000002", "PSOE", "Partido Socialista Obrero Español", "000002")
PSC = Candidature("000047", "PSC", "Partit dels Socialistes de Catalunya", "000002")


def _file(**overrides: object) -> ElectionFile:
    file = ElectionFile(
        source_file="02202307_MUNI.zip",
        sha256=SHA,
        election=Election(ElectionKind.CONGRESO, date(2023, 7, 23)),
        candidatures=(PSOE, PSC),
        results=(MunicipalResult("35016", "Las Palmas de Gran Canaria", 100, 2, 1, 70),),
        votes=(CandidatureVotes("35016", "000002", 50), CandidatureVotes("35016", "000047", 20)),
    )
    return replace(file, **overrides)  # type: ignore[arg-type]


class _Repository:
    def __init__(self, stored: str | None = None) -> None:
        self.stored = stored
        self.added: list[ElectionFile] = []

    def province_ids(self) -> set[str]:
        return set(PROVINCES)

    def stored_sha256(self, election_id: str) -> str | None:
        return self.stored

    def add(self, file: ElectionFile) -> None:
        self.added.append(file)


def test_a_sound_file_has_no_problems() -> None:
    assert file_problems(_file(), PROVINCES) == []


def test_reports_votes_that_do_not_add_up_to_the_municipal_total() -> None:
    votes = (CandidatureVotes("35016", "000002", 50), CandidatureVotes("35016", "000047", 19))

    assert file_problems(_file(votes=votes), PROVINCES) == [
        "municipality 35016: its candidatures add up to 69, its total says 70"
    ]


def test_reports_a_municipality_of_an_unknown_province() -> None:
    results = (MunicipalResult("99001", "Nowhere", 10, 0, 0, 0),)

    problems = file_problems(_file(results=results, votes=()), PROVINCES)

    assert "municipality 99001: province prov-99 is unknown" in problems


def test_reports_votes_of_an_unknown_candidature_and_without_a_municipal_total() -> None:
    votes = (*_file().votes, CandidatureVotes("38038", "000099", 5))

    problems = file_problems(_file(votes=votes), PROVINCES)

    assert "votes of 38038: unknown candidature 000099" in problems
    assert "votes of 38038: no municipal total" in problems


def test_reports_a_national_head_that_is_not_in_the_file() -> None:
    problems = file_problems(_file(candidatures=(PSC,), votes=()), PROVINCES)

    assert "candidature 000047: national head 000002 is not in the file" in problems


def test_reports_a_repeated_municipality_and_repeated_votes() -> None:
    result = _file().results[0]
    vote = CandidatureVotes("35016", "000002", 70)

    problems = file_problems(_file(results=(result, result), votes=(vote, vote)), PROVINCES)

    assert "municipality 35016 is repeated" in problems
    assert "votes of 35016/000002 is repeated" in problems


def test_loads_a_new_election() -> None:
    repository = _Repository()

    assert load_election(repository, _file()) is LoadOutcome.LOADED
    assert repository.added == [_file()]


def test_the_same_file_again_writes_nothing() -> None:
    repository = _Repository(stored=SHA)

    assert load_election(repository, _file()) is LoadOutcome.ALREADY_LOADED
    assert repository.added == []


def test_another_file_for_a_stored_election_is_refused() -> None:
    repository = _Repository(stored="b" * 64)

    with pytest.raises(ElectionAlreadyLoadedError, match="congreso-2023-07"):
        load_election(repository, _file())
    assert repository.added == []


def test_an_unsound_file_writes_nothing() -> None:
    repository = _Repository()
    votes = (CandidatureVotes("35016", "000002", 1),)

    with pytest.raises(InvalidElectionError, match="add up to 1"):
        load_election(repository, _file(votes=votes))
    assert repository.added == []
