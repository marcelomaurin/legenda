"""Tradução plugável para clientes WebSocket do Legenda."""

from __future__ import annotations

import json
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any
from urllib.request import Request, urlopen


class Translator(ABC):
    @abstractmethod
    def translate(self, text: str, source: str, target: str) -> str:
        raise NotImplementedError


class PassthroughTranslator(Translator):
    def translate(self, text: str, source: str, target: str) -> str:
        return text


class LibreTranslateTranslator(Translator):
    def __init__(self, config: dict[str, Any]) -> None:
        self.endpoint = str(config.get("translation_endpoint", "")).rstrip("/")
        self.api_key = str(config.get("translation_api_key", "")).strip()
        self.timeout = float(config.get("translation_timeout_seconds", 8))

        if not self.endpoint:
            raise ValueError("translation_endpoint não configurado.")

    def translate(self, text: str, source: str, target: str) -> str:
        payload: dict[str, Any] = {
            "q": text,
            "source": normalize_language(source),
            "target": normalize_language(target),
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key

        request = Request(
            self.endpoint + "/translate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data["translatedText"]).strip()


class CachedTranslator(Translator):
    def __init__(self, inner: Translator, max_entries: int = 2048) -> None:
        self.inner = inner
        self.max_entries = max_entries
        self.cache: dict[tuple[str, str, str], str] = {}
        self.lock = threading.Lock()

    def translate(self, text: str, source: str, target: str) -> str:
        source_n = normalize_language(source)
        target_n = normalize_language(target)
        if source_n == target_n:
            return text

        key = (text, source_n, target_n)
        with self.lock:
            cached = self.cache.get(key)
        if cached is not None:
            return cached

        translated = self.inner.translate(text, source_n, target_n)

        with self.lock:
            if len(self.cache) >= self.max_entries:
                self.cache.pop(next(iter(self.cache)), None)
            self.cache[key] = translated

        return translated


def normalize_language(language: str) -> str:
    value = language.strip().lower()
    return value.split("-", 1)[0] if "-" in value else value


def create_translator(config: dict[str, Any]) -> Translator:
    provider = str(config.get("translation_provider", "none")).strip().lower()

    if provider in {"none", "off", "disabled"}:
        return CachedTranslator(PassthroughTranslator())

    if provider in {"libretranslate", "libre"}:
        return CachedTranslator(LibreTranslateTranslator(config))

    logging.warning("Provedor de tradução desconhecido '%s'; tradução desativada.", provider)
    return CachedTranslator(PassthroughTranslator())
