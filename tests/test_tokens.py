from app.core.tokens import create_token, verify_token

SECRET = "s" * 32


def test_roundtrip():
    token = create_token(7, SECRET, 60, now=1000)
    assert verify_token(token, SECRET, now=1010) == 7


def test_expired():
    token = create_token(7, SECRET, 60, now=1000)
    assert verify_token(token, SECRET, now=1061) is None


def test_wrong_secret_and_tampering():
    token = create_token(7, SECRET, 60, now=1000)
    assert verify_token(token, "x" * 32, now=1010) is None
    payload, sig = token.split(".")
    assert verify_token(payload + "A." + sig, SECRET, now=1010) is None


def test_garbage_and_empty_secret():
    assert verify_token("garbage", SECRET) is None
    assert verify_token("", SECRET) is None
    assert verify_token("a.b", "") is None