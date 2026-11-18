from types import SimpleNamespace

from app.core import ratelimit
from app.core.ratelimit import RateLimiter, client_ip


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_blocks_after_limit_and_recovers():
    clock = Clock()
    limiter = RateLimiter(2, 10, clock)
    assert limiter.hit("a") == 0
    assert limiter.hit("a") == 0
    wait = limiter.hit("a")
    assert 0 < wait <= 10
    clock.now = 11
    assert limiter.hit("a") == 0


def test_keys_are_independent():
    limiter = RateLimiter(1, 10, Clock())
    assert limiter.hit("a") == 0
    assert limiter.hit("b") == 0
    assert limiter.hit("a") > 0


def test_blocked_attempts_do_not_extend_the_block():
    clock = Clock()
    limiter = RateLimiter(1, 10, clock)
    limiter.hit("a")
    clock.now = 5
    limiter.hit("a")
    clock.now = 10.5
    assert limiter.hit("a") == 0


def test_shared_limiter_disabled_and_reset():
    assert all(ratelimit.hit("k", 0, 60) == 0 for _ in range(20))
    assert ratelimit.hit("k", 1, 60) == 0
    assert ratelimit.hit("k", 1, 60) > 0
    ratelimit.reset_all()
    assert ratelimit.hit("k", 1, 60) == 0


def test_client_ip_trusts_proxy_header_only_when_enabled():
    request = SimpleNamespace(
        headers={"x-forwarded-for": "9.9.9.9, 10.0.0.1"}, client=SimpleNamespace(host="1.2.3.4")
    )
    assert client_ip(request, trust_proxy=False) == "1.2.3.4"
    assert client_ip(request, trust_proxy=True) == "9.9.9.9"
    assert client_ip(SimpleNamespace(headers={}, client=None)) == "unknown"