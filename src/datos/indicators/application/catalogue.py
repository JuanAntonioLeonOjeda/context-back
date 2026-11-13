"""The ids of the indicators this project defines, for other modules that refer to one."""

from datos.indicators.domain.definitions import INDICATORS

INDICATOR_IDS: frozenset[str] = frozenset(definition.id for definition in INDICATORS)
