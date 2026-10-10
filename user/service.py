"""Coordinate domain operations for users and memories."""

from user.entity import User, UserMemory
from user.user import IService


def _strip_required(value: str, field: str) -> str:
    """Return a trimmed non-empty profile field value."""
    stripped = (value or "").strip()
    if not stripped:
        raise ValueError(f"{field} is required.")
    return stripped


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

    def get_mongo_user_or_create(self, id_external_user: int, role: str, usecase: str) -> User:
        """Return the stored user or create one with the supplied profile fields."""
        try:
            return self.get_mongo_user(id_external_user)
        except ValueError:
            try:
                return self.repository.create_user(id_external_user, role, usecase)
            except Exception as e:
                raise RuntimeError(f"Error creating user: {e}")

    def apply_sign_in_profile(self, id_external_user: int, role: str, usecase: str) -> User:
        """Create the user or refresh role and usecase after each OAuth Sign in."""
        role = _strip_required(role, "role")
        usecase = _strip_required(usecase, "usecase")
        try:
            self.repository.update_role_and_usecase(id_external_user, role, usecase)
            return self.get_mongo_user(id_external_user)
        except ValueError:
            return self.get_mongo_user_or_create(id_external_user, role, usecase)

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
