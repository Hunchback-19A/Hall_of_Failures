"""
Small stdlib HTTP helper for optional network modules.

Uses only free public URLs. No API keys. Prefer ``certifi`` for CA bundles
when it is installed (helps on some Windows/Python setups).
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any, Optional
from urllib.parse import urlparse


DEFAULT_TIMEOUT_SECONDS = 20
_USER_AGENT = "megadatetime/0.2 (+https://github.com/; hobby educational package)"


class NetworkError(RuntimeError):
    """Raised when a free public data source cannot be reached or read."""


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def fetch_text(url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> str:
    """
    Download a URL and return the response body as text.

    Raises:
        NetworkError: on offline / HTTP / SSL / timeout failures.
    """
    host = urlparse(url).netloc or url
    request = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "*/*"},
    )
    try:
        with urllib.request.urlopen(
            request, timeout=timeout, context=_ssl_context()
        ) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        raise NetworkError(
            f"HTTP {exc.code} while contacting {host}. "
            "The free data source may be temporarily unavailable."
        ) from exc
    except urllib.error.URLError as exc:
        raise NetworkError(
            f"Could not reach {host} ({exc.reason}). "
            "Check your network connection; this package will not invent a fallback time."
        ) from exc
    except TimeoutError as exc:
        raise NetworkError(
            f"Timed out after {timeout}s while contacting {host}."
        ) from exc
    except OSError as exc:
        raise NetworkError(
            f"Network error while contacting {host}: {exc}"
        ) from exc


def fetch_json(url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Any:
    """Download a URL and parse JSON. Raises NetworkError on failure."""
    text = fetch_text(url, timeout=timeout)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        host = urlparse(url).netloc or url
        raise NetworkError(
            f"Received invalid JSON from {host}: {exc}"
        ) from exc
