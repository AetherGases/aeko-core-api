"""Coordinate domain operations for users and memories."""

from user.entity import User, UserMemory
from user.user import IService

class Service(IService):
    def __init__(self, repository):
        self.repository = repository

    def get_mongo_user(self, id_external_user) -> User:
        """Retrieve the stored user matching an external identifier."""
        try:
            return self.repository.get_user(id_external_user)
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise RuntimeError(f"Error retrieving user: {e}")

    def get_user_memories(self, id_user: str) -> list[UserMemory]:
        """Retrieve the memories stored for a user."""
        try:
            return self.repository.get_user_memories(id_user)
        except Exception as e:
            raise RuntimeError(f"Error retrieving user memories: {e}")

    def create_user_memory(self, user_memory: UserMemory):
        """Persist a memory associated with a user."""
        try:
            self.repository.create_user_memory(user_memory)
        except Exception as e:
            raise RuntimeError(f"Error creating user memory: {e}")

    def set_id_external_company(self, id_user: str, id_external_company: int) -> None:
        """Persist the company identifier on the user."""
        try:
            self.repository.set_id_external_company(id_user, id_external_company)
        except Exception as e:
            raise RuntimeError(f"Error updating user company: {e}")
