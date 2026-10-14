"""Time as a dependency, so "today" is testable (rules: atomic-functions-solid, D)."""

from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

# Governments change on Spanish calendar dates (the BOE), so "today" is today in Spain.
SPAIN = ZoneInfo("Europe/Madrid")


class Clock(Protocol):
    def today(self) -> date: ...


class SystemClock:
    def today(self) -> date:
        return datetime.now(SPAIN).date()
