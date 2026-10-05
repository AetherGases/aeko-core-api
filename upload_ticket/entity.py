"""Define upload ticket domain entities."""

from dataclasses import dataclass

STATE_WAITING_FOR_UPLOAD = "waiting_for_upload"
STATE_UPLOADED = "uploaded"
STATE_CONSUMED = "consumed"

VALID_FILE_TYPES = frozenset({"IMAGE", "XLSX"})


@dataclass(frozen=True)
class UploadTicket:
    ticket: str
    id_external_user: int
    name: str
    file_name: str
    file_type: str
    path: str | None
    state: str
    inventory_id: int | None
