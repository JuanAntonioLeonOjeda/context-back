"""What other modules may use from `governments` (.claude/rules/architecture.md): the read port,
the value types and the pure rules over them. Anything not listed here is internal."""

from datos.governments.application.read_governments import GovernmentsReader, government_on
from datos.governments.domain.competence import (
    Competence,
    CompetenceFunction,
    CompetenceLevel,
    applicable_competences,
)
from datos.governments.domain.government_term import GovernmentTerm, in_force_on

__all__ = [
    "Competence",
    "CompetenceFunction",
    "CompetenceLevel",
    "GovernmentTerm",
    "GovernmentsReader",
    "applicable_competences",
    "government_on",
    "in_force_on",
]
