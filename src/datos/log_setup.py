"""Structured logging configuration (structlog), applied once at startup."""

import logging

import structlog

from datos.config import LogLevel


def configure_logging(level: LogLevel, *, as_json: bool) -> None:
    """Configure structlog: JSON lines in deployments, readable output in development."""
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer() if as_json else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.value)),
        cache_logger_on_first_use=True,
    )
