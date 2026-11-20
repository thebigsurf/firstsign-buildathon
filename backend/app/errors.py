"""Application errors that map to the consistent JSON error body."""

from __future__ import annotations


class AppError(Exception):
    """An expected failure with an HTTP status and a plain-English message."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class NotFound(AppError):
    def __init__(self, what: str, key: str) -> None:
        super().__init__(404, "not_found", f"{what} '{key}' was not found.")


class BadRequest(AppError):
    def __init__(self, message: str, code: str = "bad_request") -> None:
        super().__init__(400, code, message)


class Conflict(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(409, "conflict", message)


class UpstreamError(AppError):
    """Gemini or another upstream service failed after retries and fallbacks."""

    def __init__(self, message: str) -> None:
        super().__init__(502, "upstream_error", message)
