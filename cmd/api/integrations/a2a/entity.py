"""Define the domain entities for agent-to-agent messaging."""

from dataclasses import dataclass

A2A_SENDER_CHATGPT = "chatgpt"
A2A_RECIPIENT_AEKO = "aeko"


@dataclass(frozen=True)
class A2AMessage:
    sender: str
    recipient: str
    text: str
    id_external_user: int
    session_name: str | None = None
