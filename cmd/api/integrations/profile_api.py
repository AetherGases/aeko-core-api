"""Frozen HTTP client for the ms-auth profile endpoint (GET /api/profile)."""

from typing import Any

from cmd.api.integrations.ms_auth_http import base_url, request_json

PROFILE_MS_PATH = "/api/profile"


class ProfileError(RuntimeError):
    """Raised when a call to the auth microservice profile route cannot be completed."""


def get_profile(access_token: str) -> dict:
    """Fetch the logged-in user's profile from ms-auth and return the payload as-is."""
    url = f"{base_url()}{PROFILE_MS_PATH}"
    return request_json(
        "GET",
        url,
        error_type=ProfileError,
        headers={"Authorization": f"Bearer {access_token}"},
        json={},
    )


def profile_id(payload: dict) -> int:
    """Return the profile id as a positive integer for use as id_external_user."""
    return _positive_int(payload.get("id"), "id")


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
