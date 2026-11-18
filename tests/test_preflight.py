from scripts.preflight import check_env, main, parse_env_file

GOOD = {
    "GEMINI_API_KEY": "k",
    "API_KEY": "k",
    "AUTH_SECRET": "x" * 40,
    "DASHBOARD_PASSWORD": "p",
    "DATABASE_URL": "sqlite:///a.db",
    "EMAIL_PASSWORD": "e",
    "TRUST_PROXY_HEADERS": "true",
    "DEBUG": "false",
}


def test_good_env_has_no_problems():
    assert check_env(GOOD) == []


def test_missing_keys_fail():
    env = dict(GOOD)
    del env["API_KEY"]
    assert ("FAIL", "API_KEY set nahi hai") in check_env(env)


def test_short_secret_fails():
    env = dict(GOOD, AUTH_SECRET="short")
    assert any(level == "FAIL" and "AUTH_SECRET" in msg for level, msg in check_env(env))


def test_debug_and_proxy_only_warn():
    env = dict(GOOD, DEBUG="true", TRUST_PROXY_HEADERS="false")
    levels = {level for level, _ in check_env(env)}
    assert levels == {"WARN"}


def test_parse_env_file(tmp_path):
    f = tmp_path / ".env"
    f.write_text('# c\nA=1\nB="two"\n\nbad line\n', encoding="utf-8")
    assert parse_env_file(f) == {"A": "1", "B": "two"}
    assert parse_env_file(tmp_path / "missing") == {}


def test_main_never_prints_values(tmp_path, capsys, monkeypatch):
    for key in list(GOOD) + ["RESEND_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    f = tmp_path / ".env"
    f.write_text("AUTH_SECRET=supersecretvalue\n", encoding="utf-8")
    code = main(["--env-file", str(f)])
    out = capsys.readouterr().out
    assert code == 1
    assert "supersecretvalue" not in out
