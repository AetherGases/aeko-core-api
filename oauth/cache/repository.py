"""Persist and retrieve OAuth authorization codes through Redis."""

import json

from oauth.cache.key import code_key


class Repository:
    def __init__(self, redis_client):
        self.redis = redis_client

    def save(self, code, document, ttl) -> None:
        """Persist an authorization code document with the supplied TTL."""
        self.redis.set(code_key(code), json.dumps(document), ex=ttl)

    def pop(self, code):
        """Remove and return the stored authorization code document, if present."""
        payload = self.redis.getdel(code_key(code))
        if payload is None:
            return None

        decoded = payload.decode() if isinstance(payload, bytes) else payload
        return json.loads(decoded)
