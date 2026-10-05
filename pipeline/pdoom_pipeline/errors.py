"""Collector failure classes from the source policy.

Collection failure is never evidence that a person made no statement.
"""

from __future__ import annotations

NOT_FOUND = "not_found"
TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
RATE_LIMITED = "rate_limited"
UNAUTHORIZED = "unauthorized"
BLOCKED_BY_POLICY = "blocked_by_policy"
PARSER_UNSUPPORTED = "parser_unsupported"
CONTENT_TOO_LARGE = "content_too_large"
INVALID_CONTENT = "invalid_content"
COLLECTOR_BUG = "collector_bug"
UNSAFE_URL = "unsafe_url"

RETRYABLE = {
    TEMPORARILY_UNAVAILABLE,
    RATE_LIMITED,
}


class CollectorFailure(Exception):
    def __init__(
        self,
        error_class: str,
        message: str,
        *,
        retryable: bool | None = None,
        retry_after: float | None = None,
    ):
        super().__init__(message)
        self.error_class = error_class
        self.retryable = error_class in RETRYABLE if retryable is None else retryable
        self.retry_after = retry_after


def classify_http_status(status: int) -> str:
    if status == 404:
        return NOT_FOUND
    if status == 429:
        return RATE_LIMITED
    if status in {401, 403}:
        return UNAUTHORIZED
    if status in {408, 425, 500, 502, 503, 504}:
        return TEMPORARILY_UNAVAILABLE
    if 400 <= status < 500:
        return INVALID_CONTENT
    if status >= 500:
        return TEMPORARILY_UNAVAILABLE
    return COLLECTOR_BUG
