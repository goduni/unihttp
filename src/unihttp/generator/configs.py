from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClientType(Enum):
    """Available client types for SDK generation."""

    HTTPX = "httpx"
    AIOHTTP = "aiohttp"
    REQUESTS = "requests"
    NIQUESTS = "niquests"
    ZAPROS = "zapros"


class SerializerType(Enum):
    """Available serializer types for SDK generation."""

    ADAPTIX = "adaptix"
    PYDANTIC = "pydantic"
    MSGSPEC = "msgspec"


@dataclass
class GenerationConfig:
    """Configuration for SDK generation."""

    client_type: ClientType = ClientType.HTTPX
    serializer_type: SerializerType = SerializerType.ADAPTIX
    custom_template_path: str | None = None
    output_package_name: str | None = None
    base_url: str | None = None
