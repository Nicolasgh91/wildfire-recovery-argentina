from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    """Serialize payload into a stable JSON string for hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def sha256_with_secret(payload: Any, secret: str) -> str:
    """Compute SHA-256 hash from payload + server secret."""
    canonical = canonical_json(payload)
    message = f"{canonical}|{secret}".encode("utf-8")
    return hashlib.sha256(message).hexdigest()
