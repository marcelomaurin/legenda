"""Autenticação de salas por token HMAC assinado."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


@dataclass(slots=True)
class RoomClaims:
    room: str
    role: str
    exp: int

    def expired(self) -> bool:
        return self.exp < int(time.time())


class RoomTokenManager:
    def __init__(self, secret: str) -> None:
        if len(secret) < 16:
            raise ValueError("room_auth_secret deve ter pelo menos 16 caracteres.")
        self.secret = secret.encode("utf-8")

    def create(self, room: str, role: str = "viewer", ttl_seconds: int = 3600) -> str:
        payload = {
            "room": room,
            "role": role,
            "exp": int(time.time()) + int(ttl_seconds),
        }
        payload_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_b64 = _b64encode(payload_raw)
        signature = hmac.new(self.secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
        return payload_b64 + "." + _b64encode(signature)

    def verify(self, token: str, expected_room: str | None = None) -> RoomClaims:
        try:
            payload_b64, signature_b64 = token.split(".", 1)
            supplied = _b64decode(signature_b64)
            expected = hmac.new(
                self.secret,
                payload_b64.encode("ascii"),
                hashlib.sha256,
            ).digest()

            if not hmac.compare_digest(supplied, expected):
                raise ValueError("assinatura inválida")

            payload: dict[str, Any] = json.loads(_b64decode(payload_b64))
            claims = RoomClaims(
                room=str(payload["room"]),
                role=str(payload.get("role", "viewer")),
                exp=int(payload["exp"]),
            )
        except Exception as exc:
            raise ValueError("token inválido") from exc

        if claims.expired():
            raise ValueError("token expirado")

        if expected_room is not None and claims.room != expected_room:
            raise ValueError("token não pertence à sala solicitada")

        return claims
