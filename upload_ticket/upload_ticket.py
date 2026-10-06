"""Define upload ticket service contracts."""

from abc import ABC, abstractmethod

from upload_ticket.entity import UploadTicket


class IService(ABC):
    @abstractmethod
    def create(
        self,
        id_external_user: int,
        name: str,
        file_name: str,
        file_type: str,
    ) -> UploadTicket:
        """Create a new upload ticket for an inventory file."""
        pass

    @abstractmethod
    def signature_for(self, id_external_user: int, ticket: str) -> dict:
        """Return the Cloudinary upload signature for a ticket."""
        pass

    @abstractmethod
    def confirm_path(
        self,
        id_external_user: int,
        ticket: str,
        path: str,
    ) -> UploadTicket:
        """Record the uploaded file path and mark the ticket as uploaded."""
        pass

    @abstractmethod
    def get(self, id_external_user: int, ticket: str) -> UploadTicket:
        """Return an upload ticket owned by the given user."""
        pass

    @abstractmethod
    def mark_consumed(
        self,
        id_external_user: int,
        ticket: str,
        inventory_id: int,
    ) -> UploadTicket:
        """Mark an uploaded ticket as consumed after inventory creation."""
        pass

    @abstractmethod
    def created_inventory_ids(self, id_external_user: int) -> list[int]:
        """Return inventory identifiers created from upload tickets for a user."""
        pass
