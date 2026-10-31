import os
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from talnaspor.app import app
from talnaspor.pxweb import get_metadata
from talnaspor.runtime import RuntimePolicyError, check_environment, check_px_url

PX = "https://px.hagstofa.is/pxis/api/v1/is/Efnahagur/visitolur/1_vnv/1_vnv/VIS01000.px"


@pytest.mark.parametrize(
    "url", [PX, "https://px.hagstofa.is/pxen/api/v1/en/Ibuar/mannfjoldi/MAN00101.px"]
)
def test_allows_statistics_icelands_api(url: str) -> None:
    check_px_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://px.hagstofa.is/pxis/api/v1/is/VIS01000.px",  # Not HTTPS.
        "https://api.openai.com/v1/chat/completions",
        "https://api.anthropic.com/v1/messages",
        "https://px.hagstofa.is.example.com/pxis/api/v1/is/VIS01000.px",
        "https://px.hagstofa.is@example.com/pxis/api/v1/is/VIS01000.px",
        "https://user@px.hagstofa.is/pxis/api/v1/is/VIS01000.px",
        "https://px.hagstofa.is:8443/pxis/api/v1/is/VIS01000.px",
        "https://px.hagstofa.is/pxis/pxweb/is/Efnahagur/VIS01000.px",  # A web page.
    ],
)
def test_refuses_any_other_address(url: str) -> None:
    with pytest.raises(RuntimePolicyError):
        check_px_url(url)


def test_refuses_before_sending_anything() -> None:
    with (
        patch("talnaspor.pxweb.requests.get") as get,
        pytest.raises(RuntimePolicyError),
    ):
        get_metadata("https://example.com/table.px")

    get.assert_not_called()


def test_refuses_a_redirect() -> None:
    redirect = Mock(status_code=302, headers={"Location": "https://example.com/"})
    with (
        patch("talnaspor.pxweb.requests.get", return_value=redirect),
        pytest.raises(RuntimePolicyError, match="Redirect refused"),
    ):
        get_metadata(PX)


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"OLLAMA_URL": "http://127.0.0.1:11434", "TALNASPOR_LLM_MODEL": "qwen3:8b"},
        {"OLLAMA_URL": "http://localhost:11434"},
        {"OLLAMA_URL": "http://[::1]:11434"},
    ],
)
def test_accepts_no_model_or_a_local_one(env: dict[str, str]) -> None:
    check_environment(env)


@pytest.mark.parametrize(
    "env",
    [
        {"OLLAMA_URL": "https://api.openai.com/v1"},
        {"OLLAMA_URL": "http://10.0.0.5:11434"},
        {"OLLAMA_URL": "http://ollama.example.com:11434"},
        {"TALNASPOR_LLM_MODEL": "gpt-oss:120b-cloud"},
        {"TALNASPOR_LLM_MODEL": "openai/gpt-4o"},
    ],
)
def test_refuses_a_remote_or_hosted_model(env: dict[str, str]) -> None:
    with pytest.raises(RuntimePolicyError):
        check_environment(env)


def test_server_does_not_start_with_a_remote_model_endpoint() -> None:
    env = {**os.environ, "OLLAMA_URL": "https://api.openai.com/v1"}
    result = subprocess.run(
        [sys.executable, "-c", "import talnaspor.app"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "RuntimePolicyError" in result.stderr


def test_answers_without_any_model_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("OLLAMA_URL", "TALNASPOR_LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)

    body = TestClient(app).post("/ask", json={"question": "Hvernig er veðrið?"}).json()

    assert body["status"] == "clarification"


def test_a_refused_request_fails_closed() -> None:
    # A redirect away from Statistics Iceland is an error, never an answer.
    redirect = Mock(status_code=302, headers={"Location": "https://example.com/"})
    with patch("talnaspor.pxweb.requests.get", return_value=redirect):
        response = TestClient(app).post(
            "/ask", json={"question": "Hver var verðbólgan í september 2026?"}
        )

    assert response.status_code == 500
    assert response.json()["reason"] == "unexpected"
    assert response.json()["answer"] is None
