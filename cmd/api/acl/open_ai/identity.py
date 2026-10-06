"""Bind the ChatGPT user identifier on the current task with a ContextVar."""

from contextvars import ContextVar

_id_external_user: ContextVar[int | None] = ContextVar("chatgpt_id_external_user", default=None)
_SCOPE_STATE_KEY = "chatgpt_id_external_user"


def bind_id_external_user(id_external_user: int):
    """Bind the ChatGPT user identifier for the current task."""
    return _id_external_user.set(id_external_user)


def reset_id_external_user(token) -> None:
    """Clear the ChatGPT user identifier bound by bind_id_external_user."""
    _id_external_user.reset(token)


def attach_id_external_user(scope, id_external_user: int) -> None:
    """Store the ChatGPT user identifier on the ASGI scope for the MCP session."""
    state = scope.get("state")
    if isinstance(state, dict):
        state[_SCOPE_STATE_KEY] = id_external_user
        return
    if state is None:
        scope["state"] = {_SCOPE_STATE_KEY: id_external_user}
        return
    setattr(state, _SCOPE_STATE_KEY, id_external_user)


def current_id_external_user() -> int:
    """Return the bound ChatGPT user identifier."""
    value = _id_external_user.get()
    if value is not None:
        return value
    attached = _id_external_user_from_mcp_request()
    if attached is not None:
        return attached
    raise RuntimeError("ChatGPT identity is not bound.")


def _id_external_user_from_mcp_request() -> int | None:
    try:
        from mcp.server.lowlevel.server import request_ctx

        request = request_ctx.get().request
    except LookupError:
        return None
    state = getattr(request, "state", None)
    value = getattr(state, _SCOPE_STATE_KEY, None)
    return value if isinstance(value, int) else None
