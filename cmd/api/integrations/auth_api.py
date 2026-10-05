"""Frozen HTTP client for the auth microservice login endpoint."""

import os
from typing import Any

import requests

AUTH_MS_LOGIN_PATH = "/api/auth/login"


class AuthError(RuntimeError):
    """Raised when a call to the auth microservice cannot be completed."""


def _base_url() -> str:
    """Resolve the auth microservice base URL from the environment."""

    base_url = os.environ.get("AUTH_MS_BASE_URL", "")

    if base_url == "":
        raise RuntimeError(
            "AUTH_MS_BASE_URL is not set. Please set it in the environment."
        )

    return base_url


def _timeout() -> float:
    """Resolve the shared microservice HTTP timeout from the environment."""

    value = os.environ.get("MS_HTTP_TIMEOUT", "")

    if value == "":
        raise RuntimeError(
            "MS_HTTP_TIMEOUT is not set. Please set it in the environment."
        )

    return float(value)


def _error_detail(response: Any) -> str:
    """Extract an API error message, falling back to the raw response text."""

    try:
        body = response.json()
    except ValueError:
        return response.text.strip()

    if not isinstance(body, dict):
        return response.text.strip()

    return " - ".join(
        str(body[field]) for field in ("error_code", "message") if field in body
    ) or response.text.strip()


def _request(method: str, url: str, **kwargs: Any) -> Any:
    """Send an auth microservice HTTP request and translate transport and status errors."""

    try:
        response = requests.request(
            method, url, headers={}, timeout=_timeout(), **kwargs
        )
    except requests.RequestException as exc:
        raise AuthError(
            f"Could not reach the auth microservice at {url}: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise AuthError(
            f"The auth microservice answered {response.status_code} for {url}: "
            f"{_error_detail(response)}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise AuthError(
            f"The auth microservice answered {response.status_code} for {url} with "
            f"something that is not JSON: {response.text.strip()!r}"
        ) from exc


def login(email: str, password: str) -> dict:
    """Authenticate with email and password and return the microservice payload as-is."""

    url = f"{_base_url()}{AUTH_MS_LOGIN_PATH}"
    return _request("POST", url, json={"email": email, "password": password})
