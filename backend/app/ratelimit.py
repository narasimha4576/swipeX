import os
import threading
import time

from fastapi import HTTPException

ALL_LIMITERS = []


def client_ip(request) -> str:
    """The caller's IP. Only trusts X-Forwarded-For when TRUST_PROXY=true (behind your own proxy)."""
    if os.getenv("TRUST_PROXY", "").lower() == "true":
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Allows `limit` events per `window_seconds` for each key. Kept in memory."""

    def __init__(self, limit, window_seconds, message):
        self.limit = limit
        self.window = window_seconds
        self.message = message
        self._events = {}
        self._lock = threading.Lock()
        ALL_LIMITERS.append(self)

    def _recent(self, key, now):
        cutoff = now - self.window
        events = [t for t in self._events.get(key, []) if t > cutoff]
        if events:
            self._events[key] = events
        else:
            self._events.pop(key, None)
        return events

    def retry_after(self, key):
        """Seconds to wait, or 0 if this key is not blocked."""
        with self._lock:
            now = time.time()
            events = self._recent(key, now)
            if len(events) < self.limit:
                return 0
            return max(1, int(events[-self.limit] + self.window - now) + 1)

    def check(self, key):
        wait = self.retry_after(key)
        if wait:
            raise HTTPException(status_code=429, detail=self.message, headers={"Retry-After": str(wait)})

    def add(self, key):
        with self._lock:
            now = time.time()
            self._recent(key, now)
            self._events.setdefault(key, []).append(now)
            if len(self._events) > 20000:
                for stale in list(self._events):
                    self._recent(stale, now)

    def hit(self, key):
        self.check(key)
        self.add(key)

    def clear(self, key):
        with self._lock:
            self._events.pop(key, None)

    def reset(self):
        with self._lock:
            self._events.clear()


def reset_all_limiters():
    for limiter in ALL_LIMITERS:
        limiter.reset()


login_by_account = RateLimiter(
    5, 15 * 60, "Too many failed sign-in attempts for this account. Please wait a few minutes and try again."
)
login_by_ip = RateLimiter(
    30, 15 * 60, "Too many failed sign-in attempts from this network. Please wait a few minutes and try again."
)
register_by_ip = RateLimiter(10, 60 * 60, "Too many accounts were created from this network. Please try again later.")