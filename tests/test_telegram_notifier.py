from app.core.telegram_notifier import TelegramNotifier, format_alert


def test_disabled_without_credentials():
    n = TelegramNotifier(None, None, post=lambda u, p: 200)
    assert n.enabled is False
    assert n.send("hello") is False


def test_send_success_builds_correct_request():
    calls = []

    def fake_post(url, payload):
        calls.append((url, payload))
        return 200

    n = TelegramNotifier("TOKEN", "42", post=fake_post)
    assert n.send("hi") is True
    url, payload = calls[0]
    assert "botTOKEN/sendMessage" in url
    assert payload["chat_id"] == "42"
    assert payload["text"] == "hi"


def test_send_never_raises_on_network_error():
    def boom(url, payload):
        raise RuntimeError("network down")

    n = TelegramNotifier("T", "1", post=boom)
    assert n.send("hi") is False


def test_non_2xx_status_is_failure():
    n = TelegramNotifier("T", "1", post=lambda u, p: 500)
    assert n.send("hi") is False


def test_long_text_is_truncated():
    sent = {}

    def fake_post(url, payload):
        sent.update(payload)
        return 200

    TelegramNotifier("T", "1", post=fake_post).send("x" * 5000)
    assert len(sent["text"]) == 4096


def test_empty_text_not_sent():
    n = TelegramNotifier("T", "1", post=lambda u, p: 200)
    assert n.send("") is False


def test_format_alert_confirmed_and_single():
    multi = format_alert("Title", "Summary", sources=3, url="http://x")
    assert "Confirmed by 3 sources" in multi and "http://x" in multi
    assert "Single source" in format_alert("T", "S", sources=1)