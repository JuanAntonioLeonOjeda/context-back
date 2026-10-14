"""What other modules may use from `attribution` (.claude/rules/architecture.md)."""

from datos.attribution.domain.attribution import AttributionEntry, Confidence, Reason, attribute

__all__ = ["AttributionEntry", "Confidence", "Reason", "attribute"]
