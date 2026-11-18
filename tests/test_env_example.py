from pydantic import BaseModel

from scripts import sync_env_example as sync


class Demo(BaseModel):
    api_key: str = ""
    new_flag: bool = True
    name: str = "x y"
    auth_token_hours: int = 72


def test_missing_lines_lists_only_absent_settings():
    lines = sync.missing_lines("API_KEY=abc\n", Demo)
    assert lines == ["NEW_FLAG=true", "NAME=x y", "AUTH_TOKEN_HOURS=72"]


def test_secrets_are_added_blank():
    assert "API_KEY=" in sync.missing_lines("", Demo)


def test_comments_do_not_count_as_present():
    assert "API_KEY=" in sync.missing_lines("# API_KEY=old\n", Demo)


def test_real_env_example_covers_every_setting():
    assert sync.missing_lines() == []