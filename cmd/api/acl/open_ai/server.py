"""Build the FastMCP server that serves the ChatGPT tool catalog over HTTP."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from cmd.api.acl.mcp_server import run_in_worker_thread
from cmd.api.acl.open_ai.catalog import get_chatgpt_tools
from cmd.api.acl.open_ai.mcp_meta import INVENTORY_WIDGET_URI, tool_meta

SERVER_NAME = "aeko-chatgpt"
INVENTORY_WIDGET_MIME = "text/html;profile=mcp-app"
INVENTORY_WIDGET_PATH = (
    Path(__file__).resolve().parent / "widgets" / "analyze_inventory.html"
)


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
            meta=tool_meta(tool.name),
        )

    @server.resource(INVENTORY_WIDGET_URI, mime_type=INVENTORY_WIDGET_MIME)
    def analyze_inventory_widget() -> str:
        """Return the in-chat inventory upload form."""

        return INVENTORY_WIDGET_PATH.read_text(encoding="utf-8")

    return server


mcp = build_mcp_server()
