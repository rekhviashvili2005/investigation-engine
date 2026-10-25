import pytest
from google.genai import errors

from app.llm.client import LLMError, with_retry


def make_api_error(code: int):
    return errors.APIError(code, {"error": {"message": "x", "status": "X"}})


def test_retry_succeeds_after_rate_limit():
    calls = {"n": 0}
    delays = []

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise make_api_error(429)
        return "ok"

    assert with_retry(flaky, sleep=delays.append) == "ok"
    assert calls["n"] == 3 and delays == [2.0, 4.0]


def test_no_retry_on_auth_error():
    calls = {"n": 0}

    def bad():
        calls["n"] += 1
        raise make_api_error(403)

    with pytest.raises(LLMError):
        with_retry(bad, sleep=lambda s: None)
    assert calls["n"] == 1


def test_gives_up_after_max_attempts():
    def always():
        raise make_api_error(503)

    with pytest.raises(LLMError):
        with_retry(always, max_attempts=3, sleep=lambda s: None)