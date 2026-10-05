"""Build Redis key names for upload tickets and created inventory indexes."""


def upload_key(ticket: str) -> str:
    """Return the Redis key that stores an upload ticket."""
    return f"aeko:inventory-upload:{ticket}"


def created_ids_key(id_external_user: int) -> str:
    """Return the Redis key that stores created inventory ids for a user."""
    return f"aeko:inventory-created:{id_external_user}"
