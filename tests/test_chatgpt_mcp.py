"""Verify the ChatGPT MCP tool catalog and FastMCP server definition."""

from cmd.api.acl.catalog import chatgpt_tool_names, get_chatgpt_tools
from cmd.api.acl.mcp_server import mcp

EXPECTED = {
    "get_improvement_plan_by_inventory",
    "get_improvement_plan_problem",
    "get_improvement_plan_method",
    "get_improvement_plan_reasoning",
    "list_latest_improvement_plans",
    "query_improvement_plan_problems",
    "get_user_profile_by_external_id",
    "list_user_memory_fields",
    "get_user_memory_by_field",
    "list_user_memories",
    "list_user_session_names",
    "get_session_messages_by_name",
    "get_latest_session_messages",
    "count_user_sessions",
    "query_gases_info",
    "tavily_search",
    "tavily_research",
    "tavily_map",
    "climatiq_search",
    "climatiq_estimate",
    "calculator",
    "calculate_roi",
    "calculate_payback",
    "ask_aeko",
    "analyze_inventory",
    "get_inventory_analysis",
}


def test_chatgpt_catalog_is_the_union_plus_three_new_tools():
    """Verify that the catalog is the agent tool union plus the three ChatGPT tools."""
    assert {tool.name for tool in get_chatgpt_tools()} == EXPECTED


def test_chatgpt_catalog_has_no_duplicate_tool_names():
    """Verify that every tool name appears once in the catalog."""
    names = [tool.name for tool in get_chatgpt_tools()]

    assert len(names) == len(set(names)) == 26


def test_chatgpt_catalog_omits_metrics_and_chroma_upsert():
    """Verify that metrics and chroma upsert tools are never exposed."""
    names = {tool.name for tool in get_chatgpt_tools()}

    assert names.isdisjoint({"upsert_improvement_plan_problem"})
    assert "hub_metrics" not in names
    assert "aeko_metrics" not in names


def test_chatgpt_tool_names_match_the_expected_set():
    """Verify that the name helper returns the expected catalog names."""
    assert chatgpt_tool_names() == EXPECTED


def test_fastmcp_server_is_named_aeko_chatgpt():
    """Verify that the FastMCP server carries the ChatGPT server name."""
    assert mcp.name == "aeko-chatgpt"


def test_fastmcp_server_registers_every_catalog_tool():
    """Verify that the FastMCP server registers exactly the catalog tools."""
    registered = {tool.name for tool in mcp._tool_manager.list_tools()}

    assert registered == EXPECTED


def test_fastmcp_tool_arguments_never_start_with_an_underscore():
    """Verify that private parameter names are exposed without their underscore."""
    for registered in mcp._tool_manager.list_tools():
        assert not any(name.startswith("_") for name in registered.parameters["properties"])


def test_fastmcp_tavily_map_still_runs_with_its_renamed_argument(monkeypatch):
    """Verify that the renamed argument still reaches the wrapped function."""
    from cmd.api.acl.mcp_server import expose_function

    received = []

    def private(_input: str = "") -> str:
        """Echo the private argument."""
        received.append(_input)
        return _input

    wrapped = expose_function(private)

    assert wrapped(input="x") == "x"
    assert wrapped() == ""
    assert received == ["x", ""]


def test_fastmcp_runs_a_slow_sync_tool_without_blocking_the_event_loop(monkeypatch):
    """Verify that a slow sync tool does not stall a concurrent HTTP request."""
    import asyncio
    import threading

    import httpx
    from fastapi import FastAPI
    from langchain_core.tools import Tool

    from cmd.api.acl import mcp_server

    release = threading.Event()

    def slow(value: str = "") -> str:
        """Wait until another request releases the tool."""
        release.wait(timeout=5)
        return value

    stub = Tool(name="slow_tool", description="Slow stub.", func=slow)
    monkeypatch.setattr(mcp_server, "get_chatgpt_tools", lambda: [stub])
    server = mcp_server.build_mcp_server()

    app = FastAPI()

    @app.get("/health")
    async def health() -> dict:
        """Report liveness and release the slow tool."""
        release.set()
        return {"ok": True}

    async def scenario() -> list[str]:
        """Run the slow tool and a health request together and record finish order."""
        finished: list[str] = []

        async def run_tool() -> None:
            """Call the registered slow tool."""
            await server.call_tool("slow_tool", {"value": "done"})
            finished.append("tool")

        async def run_health() -> None:
            """Call the health route after the tool has started."""
            await asyncio.sleep(0.2)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")
            assert response.status_code == 200
            finished.append("health")

        await asyncio.gather(run_tool(), run_health())
        return finished

    assert asyncio.run(scenario()) == ["health", "tool"]


def test_fastmcp_async_wrapper_keeps_the_published_signature():
    """Verify that offloaded tools still publish their stripped parameter names."""
    properties = {
        tool.name: tool.parameters["properties"] for tool in mcp._tool_manager.list_tools()
    }

    assert "input" in properties["tavily_map"]
    assert "_input" not in properties["tavily_map"]
    assert set(properties["analyze_inventory"]) == {
        "id_external_user",
        "name",
        "fileName",
        "fileType",
        "ticket",
    }


def test_chatgpt_inventory_and_ask_descriptions_drive_the_partial_answer():
    """Verify that tool descriptions tell the model how to run the two-step upload flow."""
    descriptions = {tool.name: tool.description for tool in get_chatgpt_tools()}
    registered = {tool.name: tool.description for tool in mcp._tool_manager.list_tools()}
    analyze = descriptions["analyze_inventory"]

    for text in (analyze, registered["analyze_inventory"]):
        assert "Aether app" in text
        assert "get_inventory_analysis" in text
        assert "IMAGE" in text and "XLSX" in text
        assert "ticket" in text and "id_external_user" in text
    assert "PROCESSING" in descriptions["get_inventory_analysis"]
    assert "analyze_inventory" in descriptions["get_inventory_analysis"]
    assert "id_external_user" in descriptions["ask_aeko"]
    assert "session_name" in descriptions["ask_aeko"]
    assert registered["ask_aeko"] == descriptions["ask_aeko"]


def test_fastmcp_tools_keep_the_catalog_descriptions():
    """Verify that registered tools carry the LangChain tool descriptions."""
    descriptions = {tool.name: tool.description for tool in get_chatgpt_tools()}

    for registered in mcp._tool_manager.list_tools():
        assert registered.description == descriptions[registered.name]
