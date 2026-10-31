"""Where Talnaspor may connect at runtime, checked rather than assumed.

Statistical observations come only from Statistics Iceland's PX-Web API: every request
goes through pxweb._send, which refuses any other address and any redirect. The
competition build runs no language model. A later, optional local model would be
allowed only through an Ollama server on this machine, with a model it runs itself;
settings that point anywhere else stop the server at startup instead of being used.
"""

import ipaddress
from collections.abc import Mapping
from urllib.parse import urlsplit

PX_HOST = "px.hagstofa.is"
PX_API_PATHS = ("/pxis/api/v1/is/", "/pxen/api/v1/en/")
LOOPBACK_NAMES = frozenset({"localhost"})


class RuntimePolicyError(RuntimeError):
    """A request or setting that would send data somewhere Talnaspor must not."""


def check_px_url(url: str) -> None:
    """Refuse any URL that is not Statistics Iceland's PX-Web API over HTTPS."""
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname != PX_HOST
        or parts.port not in (None, 443)
        or parts.username
        or not parts.path.startswith(PX_API_PATHS)
    ):
        raise RuntimePolicyError(f"Not Statistics Iceland's PX-Web API: {url}")


def check_environment(env: Mapping[str, str]) -> None:
    """Refuse settings that would send questions or prompts to a model on another host.

    OLLAMA_URL, if set, must be an Ollama server on this machine (a loopback address).
    TALNASPOR_LLM_MODEL, if set, must name a model Ollama runs locally: not a hosted
    ("cloud") model and not another provider's ("openai/...").
    """
    url = env.get("OLLAMA_URL")
    if url:
        parts = urlsplit(url)
        if parts.scheme != "http" or not _is_loopback(parts.hostname or ""):
            raise RuntimePolicyError(f"OLLAMA_URL must be a local Ollama server: {url}")
    model = env.get("TALNASPOR_LLM_MODEL")
    if model and ("cloud" in model.lower() or "/" in model):
        raise RuntimePolicyError(f"TALNASPOR_LLM_MODEL must be a local model: {model}")


def _is_loopback(host: str) -> bool:
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
