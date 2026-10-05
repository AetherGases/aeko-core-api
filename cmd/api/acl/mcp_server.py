"""Build the FastMCP server that serves the ChatGPT tool catalog over HTTP."""

import functools
import inspect
from typing import Any, Callable

import anyio.to_thread
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from cmd.api.acl.catalog import get_chatgpt_tools

SERVER_NAME = "aeko-chatgpt"


def expose_function(func: Callable[..., Any]) -> Callable[..., Any]:
    """Return a callable whose parameter names never start with an underscore.

    FastMCP rejects private parameter names. Functions without them are
    returned unchanged; otherwise a wrapper publishes the stripped names and
    forwards each call to the original parameters.
    """

    signature = inspect.signature(func)
    renamed = {
        name: name.lstrip("_")
        for name in signature.parameters
        if name.startswith("_")
    }
    if not renamed:
        return func

    original_by_public = {public: name for name, public in renamed.items()}
    public_signature = signature.replace(
        parameters=[
            parameter.replace(name=renamed.get(name, name))
            for name, parameter in signature.parameters.items()
        ]
    )

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Forward public argument names to the wrapped function."""

        return func(
            *args,
            **{original_by_public.get(key, key): value for key, value in kwargs.items()},
        )

    wrapper.__signature__ = public_signature
    return wrapper


def run_in_worker_thread(func: Callable[..., Any]) -> Callable[..., Any]:
    """Return an async callable that runs a sync tool on a worker thread.

    FastMCP calls sync functions inline on the event loop, so a slow tool would
    stall every other request. The wrapper keeps the published signature.
    """

    exposed = expose_function(func)

    @functools.wraps(exposed)
    async def call(**kwargs: Any) -> Any:
        """Run the wrapped tool off the event loop."""

        return await anyio.to_thread.run_sync(functools.partial(exposed, **kwargs))

    call.__signature__ = inspect.signature(exposed)
    return call


def build_mcp_server() -> FastMCP:
    """Create a FastMCP server with every ChatGPT tool registered.

    The streamable HTTP endpoint is served at the root path so a host
    application can choose the mount prefix.
    """

    server = FastMCP(
        SERVER_NAME,
        streamable_http_path="/",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    for tool in get_chatgpt_tools():
        server.add_tool(
            run_in_worker_thread(tool.func),
            name=tool.name,
            description=tool.description,
        )
    return server


mcp = build_mcp_server()
