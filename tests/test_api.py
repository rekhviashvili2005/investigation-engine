from fastapi.testclient import TestClient

from app.api import main
from app.llm.agent import AgentAnswer

client = TestClient(main.app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_ask_validation():
    assert client.post("/ask", json={"question": "x"}).status_code == 422
    assert client.post("/ask", json={"question": "valid question", "mode": "bad"}).status_code == 422


def test_ask_ok(monkeypatch):
    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(main, "get_connection", lambda: FakeConn())
    monkeypatch.setattr(main, "run_agent", lambda *a, **k: AgentAnswer("answered", "Yes [1]", [1]))
    r = client.post("/ask", json={"question": "Is this a test?"})
    assert r.status_code == 200 and r.json()["status"] == "answered"


def test_ask_llm_error_is_503(monkeypatch):
    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(main, "get_connection", lambda: FakeConn())
    monkeypatch.setattr(main, "run_agent", lambda *a, **k: AgentAnswer("error", "", missing="LLM unavailable"))
    assert client.post("/ask", json={"question": "Is this a test?"}).status_code == 503


def test_upload_rejects_unknown_format():
    r = client.post("/documents", files={"file": ("a.xyz", b"data")})
    assert r.status_code == 415