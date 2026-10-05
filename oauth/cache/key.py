"""Build Redis key names for OAuth authorization codes."""


def code_key(code: str) -> str:
    """Return the Redis key that stores an authorization code."""
    return f"oauth:code:{code}"
