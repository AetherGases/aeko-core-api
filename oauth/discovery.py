"""OAuth discovery URLs and metadata documents."""

from oauth.constants import (
    AUTHORIZE_PATH,
    MCP_PROTECTED_RESOURCE_WELL_KNOWN_PATH,
    OAUTH_AUDIENCE,
    OAUTH_ISSUER,
    PROTECTED_RESOURCE_WELL_KNOWN_PATH,
    TOKEN_PATH,
)


def public_url(path: str) -> str:
    """Join the configured public issuer base URL with an application path."""
    return f"{OAUTH_ISSUER.rstrip('/')}{path}"


def mcp_protected_resource_metadata_url() -> str:
    """Return the protected-resource metadata URL for the MCP resource (RFC 9728)."""
    return f"{OAUTH_AUDIENCE.rstrip('/')}/.well-known/oauth-protected-resource"


def authorization_server_metadata_document() -> dict:
    """Build OAuth 2.1 authorization-server metadata for ChatGPT discovery."""
    return {
        "issuer": OAUTH_ISSUER,
        "authorization_endpoint": public_url(AUTHORIZE_PATH),
        "token_endpoint": public_url(TOKEN_PATH),
        "code_challenge_methods_supported": ["S256"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["none"],
        "client_id_metadata_document_supported": True,
        "authorization_response_iss_parameter_supported": True,
    }


def protected_resource_metadata_document() -> dict:
    """Build OAuth protected-resource metadata for the MCP resource."""
    return {
        "resource": OAUTH_AUDIENCE,
        "authorization_servers": [OAUTH_ISSUER],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["mcp"],
    }
