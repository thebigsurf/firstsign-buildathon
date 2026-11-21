"""Per-client sliding-window rate limit for the endpoints that can spend Gemini money.

In-memory and per process: enough to stop one client (or a script) from draining the quota on a single Cloud Run
instance. At scale this moves to Cloud Armor or an API gateway (see docs/GEMINI_ENGINEERING.md).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from .errors import AppError

WINDOW_S = 60.0
MAX_CLIENTS = 5000  # bound memory: forget the oldest clients beyond this


class RateLimited(AppError):
    def __init__(self, retry_after_s: int) -> None:
        super().__init__(429, "rate_limited",
                         f"Too many requests from this device. Please wait {retry_after_s} second{'' if retry_after_s == 1 else 's'} and try again.")
        self.retry_after_s = retry_after_s


def client_ip(request: Request) -> str:
    """Cloud Run appends the real client IP as the LAST X-Forwarded-For entry; earlier entries can be spoofed."""
    forwarded = request.headers.get("x-forwarded-for", "")
    parts = [p.strip() for p in forwarded.split(",") if p.strip()]
    if parts:
        return parts[-1]
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def __init__(self, per_minute: int, clock=time.monotonic) -> None:  # noqa: ANN001
        self.per_minute = per_minute
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Count one request for `key`; raise RateLimited when it is over the limit. per_minute <= 0 disables."""
        if self.per_minute <= 0:
            return
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= WINDOW_S:
                hits.popleft()
            if len(hits) >= self.per_minute:
                raise RateLimited(max(1, int(WINDOW_S - (now - hits[0])) + 1))
            hits.append(now)
            if len(self._hits) > MAX_CLIENTS:
                for stale in [k for k, v in self._hits.items() if not v or now - v[-1] >= WINDOW_S][:1000]:
                    self._hits.pop(stale, None)
