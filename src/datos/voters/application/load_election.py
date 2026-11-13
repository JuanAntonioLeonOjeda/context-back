"""Load an election's results: check the file, then store it once (spec AC1)."""

from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol

from datos.voters.domain.election import ElectionFile, file_problems


class ElectionRepository(Protocol):
    def province_ids(self) -> set[str]:
        """The provinces in `territories`: a municipality must belong to one."""
        ...

    def stored_sha256(self, election_id: str) -> str | None:
        """The hash of the file the election was loaded from, or None if it is not stored."""
        ...

    def add(self, file: ElectionFile) -> None:
        """Store the election, its candidatures, results and votes (the caller's transaction)."""
        ...


class LoadOutcome(StrEnum):
    LOADED = "loaded"
    ALREADY_LOADED = "already_loaded"  # the same file again: nothing is written


class InvalidElectionError(Exception):
    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__(f"{len(problems)} problem(s):\n- " + "\n- ".join(problems))
        self.problems = list(problems)


class ElectionAlreadyLoadedError(Exception):
    """Another file for an election that is stored: official results are final (spec AC1)."""


def load_election(repository: ElectionRepository, file: ElectionFile) -> LoadOutcome:
    stored = repository.stored_sha256(file.election.id)
    if stored == file.sha256:
        return LoadOutcome.ALREADY_LOADED
    if stored is not None:
        raise ElectionAlreadyLoadedError(
            f"{file.election.id} was loaded from another file (sha256 {stored[:12]}…);"
            f" {file.source_file} is {file.sha256[:12]}…"
        )
    problems = file_problems(file, repository.province_ids())
    if problems:
        raise InvalidElectionError(problems)
    repository.add(file)
    return LoadOutcome.LOADED
