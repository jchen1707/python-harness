"""Application error types (architecture §6).

Services raise these domain errors; the api layer maps them to HTTP responses.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for domain errors raised by the service layer."""


class NotFoundError(AppError):
    """A requested entity does not exist."""
