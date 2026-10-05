"""Define OAuth authorization-code entities."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationCode:
    id_external_user: int
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str
