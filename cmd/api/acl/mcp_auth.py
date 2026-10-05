"""Challenge unsigned ChatGPT tool calls with HTTP 401 and WWW-Authenticate."""

import json

from cmd.api.acl.catalog import AUTHENTICATED_CHATGPT_TOOL_NAMES
from cmd.api.acl.identity import (
    attach_id_external_user,
    bind_id_external_user,
    reset_id_external_user,
)
from oauth.constants import OAUTH_ISSUER
from oauth.token import decode_access_token

ERROR_DESCRIPTION = "You need to login to continue"


def www_authenticate_value() -> str:
    """Return the WWW-Authenticate challenge ChatGPT uses to open Sign in."""
    return (
        f'Bearer resource_metadata="{OAUTH_ISSUER}/.well-known/oauth-protected-resource", '
        f'scope="mcp", error="insufficient_scope", '
        f'error_description="{ERROR_DESCRIPTION}"'
    )


def wrap_mcp_auth(app):
    """Return an ASGI app that authenticates FR-005 ChatGPT tool calls."""
    return _McpAuthApp(app)


class _McpAuthApp:
    def __init__(self, app):
        self.app = app

    @property
    def routes(self):
        """Expose the wrapped Starlette routes for host-app mount checks."""
        return self.app.routes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return

        body = await _read_body(receive)
        payload = _json_object(body)
        replay = _replay_body(body, receive)

        if not _requires_chatgpt_identity(payload):
            await self.app(scope, replay, send)
            return

        token = _bearer_token(scope)
        try:
            if token is None:
                raise ValueError("Missing access token.")
            id_external_user = decode_access_token(token)
        except ValueError:
            await _send_unauthorized(send, None if payload is None else payload.get("id"))
            return

        attach_id_external_user(scope, id_external_user)
        identity = bind_id_external_user(id_external_user)
        try:
            await self.app(scope, replay, send)
        finally:
            reset_id_external_user(identity)


def _requires_chatgpt_identity(payload) -> bool:
    if not isinstance(payload, dict) or payload.get("method") != "tools/call":
        return False
    params = payload.get("params")
    if not isinstance(params, dict):
        return False
    return params.get("name") in AUTHENTICATED_CHATGPT_TOOL_NAMES


def _bearer_token(scope) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() != b"authorization":
            continue
        scheme, _, rest = value.decode("latin-1").partition(" ")
        if scheme.lower() != "bearer":
            return None
        token = rest.strip()
        return token or None
    return None


async def _read_body(receive) -> bytes:
    chunks: list[bytes] = []
    more = True
    while more:
        message = await receive()
        if message["type"] == "http.request":
            chunks.append(message.get("body", b""))
            more = bool(message.get("more_body", False))
        else:
            more = False
    return b"".join(chunks)


def _replay_body(body: bytes, receive):
    sent = False

    async def replay():
        """Replay the buffered body, then wait for the original disconnect."""
        nonlocal sent
        if sent:
            return await receive()
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return replay


def _json_object(body: bytes):
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


async def _send_unauthorized(send, request_id) -> None:
    challenge = www_authenticate_value()
    meta = {"mcp/www_authenticate": [challenge]}
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32001,
            "message": ERROR_DESCRIPTION,
            "_meta": meta,
        },
        "_meta": meta,
    }
    raw = json.dumps(payload).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(raw)).encode("ascii")),
                (b"www-authenticate", challenge.encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": raw})
