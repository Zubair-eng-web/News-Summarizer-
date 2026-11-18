"""In-memory sliding-window rate limiter (ek process ke liye)."""
import threading
import time
from collections import deque

MAX_KEYS = 10_000


class RateLimiter:
    def __init__(self, limit: int, window: float, clock=time.monotonic):
        self.limit = limit
        self.window = window
        self._clock = clock
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> float:
        """Koshish note karta hai. 0 = allowed, warna kitne seconds baad dobara try karein."""
        now = self._clock()
        with self._lock:
            queue = self._hits.setdefault(key, deque())
            cutoff = now - self.window
            while queue and queue[0] <= cutoff:
                queue.popleft()
            if len(queue) >= self.limit:
                return max(queue[0] + self.window - now, 0.001)
            queue.append(now)
            if len(self._hits) > MAX_KEYS:
                self._prune(cutoff)
            return 0.0

    def _prune(self, cutoff: float) -> None:
        for key in [k for k, q in self._hits.items() if not q or q[-1] <= cutoff]:
            del self._hits[key]


_limiters: dict[tuple, RateLimiter] = {}


def hit(key: str, limit: int, window: float) -> float:
    """Shared limiter. limit <= 0 ho to rate limiting band hai."""
    if limit <= 0:
        return 0.0
    limiter = _limiters.setdefault((limit, window), RateLimiter(limit, window))
    return limiter.hit(key)


def reset_all() -> None:
    _limiters.clear()


def client_ip(request, trust_proxy: bool = False) -> str:
    """Proxy ke peeche hone par hi X-Forwarded-For par bharosa karein."""
    if trust_proxy:
        first = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if first:
            return first[:64]
    return request.client.host if request.client else "unknown"