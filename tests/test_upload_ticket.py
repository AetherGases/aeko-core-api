"""Verify upload ticket lifecycle and Redis persistence."""

import pytest

from tests.conftest import FakeRedis
from upload_ticket.cache.key import upload_key
from upload_ticket.cache.repository import Repository
from upload_ticket.constants import INVENTORY_UPLOAD_TICKET_TTL_SECONDS
from upload_ticket.service import Service


@pytest.fixture
def redis():
    """Provide an isolated in-memory Redis double."""
    return FakeRedis()


@pytest.fixture
def repository(redis):
    """Provide an upload ticket repository backed by FakeRedis."""
    return Repository(redis)


@pytest.fixture
def service(repository, monkeypatch):
    """Provide an upload ticket service with Cloudinary stubbed out."""
    monkeypatch.setattr(
        "upload_ticket.service.get_upload_signature",
        lambda file_type: {"signature": file_type},
    )
    return Service(repository)


def test_create_returns_opaque_ticket_with_waiting_state(service, redis):
    """Persist a new ticket with waiting state and TTL."""
    ticket = service.create(42, "inventory", "file.xlsx", "XLSX")

    assert ticket.ticket
    assert ticket.state == "waiting_for_upload"
    assert ticket.path is None
    assert ticket.inventory_id is None
    assert ticket.id_external_user == 42
    assert ticket.name == "inventory"
    assert ticket.file_name == "file.xlsx"
    assert ticket.file_type == "XLSX"

    key = upload_key(ticket.ticket)
    assert key in redis.values
    assert redis.expirations[key] == INVENTORY_UPLOAD_TICKET_TTL_SECONDS


def test_signature_for_calls_get_upload_signature_with_file_type(service, monkeypatch):
    """Return Cloudinary signature JSON for the ticket file type."""
    created = service.create(42, "inventory", "file.xlsx", "XLSX")
    calls = []

    monkeypatch.setattr(
        "upload_ticket.service.get_upload_signature",
        lambda file_type: calls.append(file_type) or {"sig": 1},
    )

    result = service.signature_for(42, created.ticket)

    assert calls == ["XLSX"]
    assert result == {"sig": 1}


def test_confirm_path_once(service):
    """Store the upload path and move the ticket to uploaded state."""
    created = service.create(42, "inventory", "file.xlsx", "XLSX")

    updated = service.confirm_path(42, created.ticket, "/cloud/path")

    assert updated.path == "/cloud/path"
    assert updated.state == "uploaded"


def test_confirm_path_rejects_second_path(service):
    """Reject overwriting a path that was already confirmed."""
    created = service.create(42, "inventory", "file.xlsx", "XLSX")
    service.confirm_path(42, created.ticket, "/first")

    with pytest.raises(ValueError, match="path"):
        service.confirm_path(42, created.ticket, "/second")


def test_operations_reject_other_user(service):
    """Hide ticket existence from users who do not own it."""
    created = service.create(42, "inventory", "file.xlsx", "XLSX")

    with pytest.raises(ValueError, match="not found"):
        service.get(99, created.ticket)
    with pytest.raises(ValueError, match="not found"):
        service.signature_for(99, created.ticket)
    with pytest.raises(ValueError, match="not found"):
        service.confirm_path(99, created.ticket, "/path")


def test_mark_consumed_and_created_inventory_ids(service):
    """Append inventory ids after a successful consume."""
    created = service.create(42, "inventory", "file.xlsx", "XLSX")
    service.confirm_path(42, created.ticket, "/path")

    consumed = service.mark_consumed(42, created.ticket, 501)

    assert consumed.state == "consumed"
    assert consumed.inventory_id == 501
    assert service.created_inventory_ids(42) == [501]

    created2 = service.create(42, "inventory-two", "file2.xlsx", "IMAGE")
    service.confirm_path(42, created2.ticket, "/path-two")
    service.mark_consumed(42, created2.ticket, 502)

    assert service.created_inventory_ids(42) == [501, 502]


def test_mark_consumed_rejects_waiting_state(service):
    """Reject consume while the ticket is still waiting for upload."""
    created = service.create(42, "inventory", "file.xlsx", "XLSX")

    with pytest.raises(ValueError):
        service.mark_consumed(42, created.ticket, 501)


def test_record_created_inventory_appends_id(service):
    """Append inventory ids created through ChatGPT ingest without a ticket."""
    service.record_created_inventory(42, 501)

    assert service.created_inventory_ids(42) == [501]

    service.record_created_inventory(42, 502)

    assert service.created_inventory_ids(42) == [501, 502]
