"""Frozen HTTP client for the profile microservice profile endpoint."""

import os
from typing import Any

import requests

PROFILE_MS_PATH = "/api/profile"


class ProfileError(RuntimeError):
    """Raised when a call to the profile microservice cannot be completed."""


def _base_url() -> str:
    """Resolve the profile microservice base URL from the environment."""

    base_url = os.environ.get("PROFILE_MS_BASE_URL", "")

    if base_url == "":
        raise RuntimeError(
            "PROFILE_MS_BASE_URL is not set. Please set it in the environment."
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


def _positive_int(value: Any, field_name: str) -> int:
    """Accept a positive integer or numeric string and reject bools or other values."""

    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field_name} must be a positive integer.")

    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped == "" or not stripped.isdigit():
            raise ValueError(f"{field_name} must be a positive integer.")
        parsed = int(stripped)
    else:
        raise ValueError(f"{field_name} must be a positive integer.")

    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")

    return parsed


def _request(method: str, url: str, access_token: str, **kwargs: Any) -> Any:
    """Send a profile microservice HTTP request and translate transport and status errors."""

    headers = {"Authentication": f"Bearer {access_token}"}

    try:
        response = requests.request(
            method, url, headers=headers, json={}, timeout=_timeout(), **kwargs
        )
    except requests.RequestException as exc:
        raise ProfileError(
            f"Could not reach the profile microservice at {url}: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise ProfileError(
            f"The profile microservice answered {response.status_code} for {url}: "
            f"{_error_detail(response)}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise ProfileError(
            f"The profile microservice answered {response.status_code} for {url} with "
            f"something that is not JSON: {response.text.strip()!r}"
        ) from exc


def get_profile(access_token: str) -> dict:
    """Fetch the authenticated user's profile and return the microservice payload as-is."""

    url = f"{_base_url()}{PROFILE_MS_PATH}"
    return _request("GET", url, access_token)


def profile_id(payload: dict) -> int:
    """Return the profile id as a positive integer for use as id_external_user."""

    return _positive_int(payload.get("id"), "id")
