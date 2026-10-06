"""Expose a typed tool for sending ChatGPT questions to Aeko."""

from langchain_core.tools import Tool, create_schema_from_function

from cmd.api.integrations.a2a.entity import (
    A2AMessage,
    A2A_RECIPIENT_AEKO,
    A2A_SENDER_CHATGPT,
)
from cmd.api.tools.constants import ASK_AEKO_DESCRIPTION
from cmd.api.tools.mongo_tools import _positive_int, _required_text


_a2a = None
_aeko_messenger_factory = None
_aeko_session_factory = None


def configure(
    *,
    a2a=None,
    aeko_messenger_factory=None,
    aeko_session_factory=None,
) -> None:
    """Bind the A2A service and Aeko factories used by the tool."""

    global _a2a, _aeko_messenger_factory, _aeko_session_factory
    _a2a = a2a
    _aeko_messenger_factory = aeko_messenger_factory
    _aeko_session_factory = aeko_session_factory


def ask_aeko(
    id_external_user: int,
    input: str,
    session_name: str | None = None,
) -> str:
    """Send a user question to Aeko and return the approved reply."""

    identifier = _positive_int(id_external_user, "id_external_user")
    message_input = _required_text(input, "input")
    effective_session_name = (
        None
        if session_name is None or session_name.strip() == ""
        else session_name
    )
    if (
        _a2a is None
        or _aeko_messenger_factory is None
        or _aeko_session_factory is None
    ):
        raise RuntimeError("A2A service and Aeko factories are not configured.")
    message = A2AMessage(
        A2A_SENDER_CHATGPT,
        A2A_RECIPIENT_AEKO,
        message_input,
        identifier,
        effective_session_name,
    )
    return _a2a.send(
        message,
        _aeko_messenger_factory,
        _aeko_session_factory,
    )


def get_ask_aeko_tools() -> list[Tool]:
    """Return the typed tool for sending questions to Aeko."""

    return [
        Tool(
            name="ask_aeko",
            description=ASK_AEKO_DESCRIPTION,
            func=ask_aeko,
            args_schema=create_schema_from_function("ask_aeko", ask_aeko),
        )
    ]
