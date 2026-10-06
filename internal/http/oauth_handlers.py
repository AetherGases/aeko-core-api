"""Expose OAuth 2.1 discovery, ChatGPT Sign in, and token endpoints."""

from html import escape

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from oauth.constants import OAUTH_AUDIENCE, OAUTH_ISSUER
from oauth.oauth import IService
from oauth.service import validate_authorize_parameters

router = APIRouter()

AUTHORIZE_PATH = "/aether-api/v1/oauth/authorize"
TOKEN_PATH = "/aether-api/v1/oauth/token"


def get_oauth_service(request: Request) -> IService:
    """Return the bound OAuth service, or raise HTTP 503."""
    service = getattr(request.app.state, "oauth", None)
    if service is None:
        raise HTTPException(status_code=503, detail="OAuth is not initialized")
    return service


def _hidden(name: str, value: str) -> str:
    return f'<input type="hidden" name="{escape(name)}" value="{escape(value)}">'


def render_sign_in(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    resource: str | None = None,
    error: str | None = None,
) -> str:
    """Return the ChatGPT Sign in webview HTML for the supplied OAuth parameters."""
    hidden = [
        _hidden("client_id", client_id),
        _hidden("redirect_uri", redirect_uri),
        _hidden("state", state),
        _hidden("code_challenge", code_challenge),
        _hidden("code_challenge_method", code_challenge_method),
    ]
    if resource:
        hidden.append(_hidden("resource", resource))
    message = f"<p>{escape(error)}</p>" if error else ""
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<title>Aether Sign in</title></head><body>"
        "<h1>Aether Sign in</h1>"
        f"{message}"
        f"<form method=\"post\" action=\"{AUTHORIZE_PATH}\">"
        "<label>Email <input type=\"email\" name=\"email\" required></label>"
        "<label>Password <input type=\"password\" name=\"password\" required></label>"
        f"{''.join(hidden)}"
        "<button type=\"submit\">Sign in</button>"
        "</form></body></html>"
    )


@router.get("/.well-known/oauth-authorization-server", include_in_schema=False)
def authorization_server_metadata():
    """Return OAuth 2.1 authorization-server metadata for ChatGPT discovery."""
    return {
        "issuer": OAUTH_ISSUER,
        "authorization_endpoint": f"{OAUTH_ISSUER}{AUTHORIZE_PATH}",
        "token_endpoint": f"{OAUTH_ISSUER}{TOKEN_PATH}",
        "code_challenge_methods_supported": ["S256"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["none"],
        "client_id_metadata_document_supported": True,
        "authorization_response_iss_parameter_supported": True,
    }


@router.get("/.well-known/oauth-protected-resource", include_in_schema=False)
def protected_resource_metadata():
    """Return OAuth protected-resource metadata for the MCP resource."""
    return {
        "resource": OAUTH_AUDIENCE,
        "authorization_servers": [OAUTH_ISSUER],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["mcp"],
    }


@router.get(AUTHORIZE_PATH, tags=["OAuth"])
def authorize_get(
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    response_type: str = "code",
    resource: str | None = None,
):
    """Render the ChatGPT Sign in webview after validating the authorize query."""
    if response_type != "code":
        raise HTTPException(status_code=400, detail="response_type must be code.")
    try:
        validate_authorize_parameters(
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge_method=code_challenge_method,
            resource=resource,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(
        render_sign_in(
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            resource=resource,
        )
    )


@router.post(AUTHORIZE_PATH, tags=["OAuth"])
def authorize_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    state: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(...),
    resource: str | None = Form(None),
):
    """Authenticate through the OAuth service and redirect to the client, or stay on Sign in."""
    try:
        location = get_oauth_service(request).authorize(
            email,
            password,
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            resource=resource,
        )
    except ValueError:
        return HTMLResponse(
            render_sign_in(
                client_id=client_id,
                redirect_uri=redirect_uri,
                state=state,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                resource=resource,
                error="Sign in failed.",
            ),
            status_code=401,
        )
    return RedirectResponse(url=location, status_code=302)


@router.post(TOKEN_PATH, tags=["OAuth"])
def token_post(
    request: Request,
    grant_type: str = Form(...),
    code: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    code_verifier: str = Form(...),
    resource: str | None = Form(None),
):
    """Exchange an authorization code for this API's Bearer access token."""
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="grant_type must be authorization_code.")
    try:
        return get_oauth_service(request).exchange(
            code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier,
            resource=resource,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
