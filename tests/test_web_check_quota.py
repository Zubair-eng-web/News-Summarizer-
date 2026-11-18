import pytest
from google.genai import errors

from app.agents import web_check as wc
from app.agents.research import ResearchError


class QuotaError(errors.APIError):
    def __init__(self):
        Exception.__init__(self, "429 RESOURCE_EXHAUSTED")
        self.code = 429


class OtherError(errors.APIError):
    def __init__(self):
        Exception.__init__(self, "500 INTERNAL")
        self.code = 500


class FailingClient:
    def __init__(self, error):
        self.models = self
        self.error = error

    def generate_content(self, **kwargs):
        raise self.error


def test_quota_error_gives_clear_message():
    with pytest.raises(ResearchError) as info:
        wc.web_check("claim", FailingClient(QuotaError()))
    assert str(info.value) == wc.QUOTA_MSG


def test_other_errors_keep_original_message():
    with pytest.raises(ResearchError) as info:
        wc.web_check("claim", FailingClient(OtherError()))
    assert "500" in str(info.value)