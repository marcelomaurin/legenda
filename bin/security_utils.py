"""Utilitários de segurança para serviços administrativos locais."""

from __future__ import annotations

import hmac
import ipaddress


def bearer_matches(authorization: str, expected_token: str) -> bool:
    if not expected_token:
        return True
    supplied = authorization or ""
    expected = f"Bearer {expected_token}"
    return hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))


def is_loopback_host(host: str) -> bool:
    normalized = (host or "").strip().lower()
    if normalized in {"localhost", "ip6-localhost"}:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def require_token_for_remote_bind(host: str, token: str, service_name: str) -> None:
    if is_loopback_host(host):
        return
    if not token:
        raise ValueError(
            f"{service_name}: bind remoto em {host!r} exige token de autenticação."
        )
