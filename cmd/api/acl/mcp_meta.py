"""Build FastMCP tool metadata ChatGPT uses for Sign in."""

INVENTORY_WIDGET_URI = "ui://widget/analyze-inventory.html"


def tool_meta(name: str) -> dict:
    """Return FastMCP tool metadata ChatGPT uses for Sign in and widgets."""
    from cmd.api.acl.catalog import AUTHENTICATED_CHATGPT_TOOL_NAMES

    if name in AUTHENTICATED_CHATGPT_TOOL_NAMES:
        schemes = [{"type": "oauth2", "scopes": ["mcp"]}]
    else:
        schemes = [{"type": "noauth"}]
    meta = {"securitySchemes": schemes}
    if name == "analyze_inventory":
        meta["ui"] = {"resourceUri": INVENTORY_WIDGET_URI}
        meta["openai/outputTemplate"] = INVENTORY_WIDGET_URI
        meta["openai/fileParams"] = ["file"]
    return meta
