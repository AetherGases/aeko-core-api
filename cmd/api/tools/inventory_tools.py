"""Expose typed inventory upload and analysis tools backed by domain services."""

import logging
from typing import Any, Callable

from langchain_core.tools import Tool, create_schema_from_function

from cmd.api.integrations.inventory_api import InventoryError
from cmd.api.tools.constants import (
    ANALYZE_INVENTORY_DESCRIPTION,
    GET_INVENTORY_ANALYSIS_DESCRIPTION,
)
from cmd.api.tools.mongo_tools import _positive_int, _required_text
from upload_ticket.entity import STATE_UPLOADED


logger = logging.getLogger(__name__)

_tickets_service = None
_create_inventory = None
_plans_service = None
_inventory_response_keys = ("id", "name", "type", "status", "createdAt")


def configure(*, tickets=None, create_inventory=None, plans=None) -> None:
    """Bind upload tickets, inventory creation, and improvement plans."""

    global _tickets_service, _create_inventory, _plans_service
    _tickets_service = tickets
    _create_inventory = create_inventory
    _plans_service = plans


def _tickets():
    """Return the configured upload-ticket service."""

    if _tickets_service is None:
        raise RuntimeError("Upload ticket service is not configured.")
    return _tickets_service


def _inventory_creator() -> Callable[[str, str, str], dict]:
    """Return the configured inventory creation function."""

    if _create_inventory is None:
        raise RuntimeError("Inventory create function is not configured.")
    return _create_inventory


def _plans():
    """Return the configured improvement-plan service."""

    if _plans_service is None:
        raise RuntimeError("Improvement plan service is not configured.")
    return _plans_service


def _analyze_inventory(
    id_external_user: int,
    name: str | None = None,
    fileName: str | None = None,
    fileType: str | None = None,
    ticket: str | None = None,
) -> dict[str, Any]:
    """Create an upload ticket or submit its uploaded file for analysis."""

    identifier = _positive_int(id_external_user, "id_external_user")
    if ticket is None or (isinstance(ticket, str) and ticket.strip() == ""):
        inventory_name = _required_text(name, "name")
        file_name = _required_text(fileName, "fileName")
        file_type = _required_text(fileType, "fileType")
        if file_type not in {"IMAGE", "XLSX"}:
            raise ValueError("fileType must be exactly IMAGE or XLSX.")
        created = _tickets().create(
            identifier,
            inventory_name,
            file_name,
            file_type,
        )
        return {"ticket": created.ticket, "state": "waiting_for_upload"}

    ticket_value = _required_text(ticket, "ticket")
    uploaded = _tickets().get(identifier, ticket_value)
    if (
        uploaded.state != STATE_UPLOADED
        or not isinstance(uploaded.path, str)
        or uploaded.path.strip() == ""
    ):
        raise ValueError("Ticket upload is not complete.")

    try:
        inventory = _inventory_creator()(
            uploaded.name,
            uploaded.file_name,
            uploaded.path,
        )
    except InventoryError as exc:
        logger.warning("Inventory submission failed: %s", exc)
        raise RuntimeError("Inventory submission failed. Try again later.") from None
    _tickets().mark_consumed(identifier, ticket_value, inventory["id"])
    return {
        key: inventory[key]
        for key in _inventory_response_keys
        if key in inventory
    }


def _get_inventory_analysis(
    id_external_user: int,
    id: int,
) -> dict[str, Any]:
    """Return a created inventory's analysis or its processing state."""

    identifier = _positive_int(id_external_user, "id_external_user")
    inventory_id = _positive_int(id, "id")
    if inventory_id not in _tickets().created_inventory_ids(identifier):
        raise ValueError("inventory was not created through this user's upload tickets.")

    try:
        plan = _plans().get_by_id_external_inventory(inventory_id)
    except ValueError:
        return {"status": "PROCESSING"}

    return {
        "defined_problem": plan.defined_problem,
        "solving_method": plan.method,
        "reasoning": plan.reasoning,
    }


def _typed_tool(name: str, description: str, func: Any) -> Tool:
    """Build a Tool whose schema uses the function's named arguments."""

    return Tool(
        name=name,
        description=description,
        func=func,
        args_schema=create_schema_from_function(name, func),
    )


def get_inventory_ingest_tools() -> list[Tool]:
    """Return typed tools for inventory ingest and analysis polling."""

    return [
        _typed_tool(
            "analyze_inventory",
            ANALYZE_INVENTORY_DESCRIPTION,
            _analyze_inventory,
        ),
        _typed_tool(
            "get_inventory_analysis",
            GET_INVENTORY_ANALYSIS_DESCRIPTION,
            _get_inventory_analysis,
        ),
    ]
