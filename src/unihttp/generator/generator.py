from __future__ import annotations

import re
import shutil
import subprocess  # noqa: S404
import tempfile
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined

from .configs import GenerationConfig
from .parser import OpenAPIParser
from .renderer import TemplateRenderer

_CLIENT_SPECS: dict[str, tuple[str, str | None, str]] = {
    "httpx": ("HTTPXSyncClient", "HTTPXAsyncClient", "unihttp.clients.httpx"),
    "aiohttp": ("AIOHttpSyncClient", "AIOhttpAsyncClient", "unihttp.clients.aiohttp"),
    "requests": ("RequestsSyncClient", None, "unihttp.clients.requests"),
    "niquests": ("NiquestsSyncClient", "NiquestsAsyncClient", "unihttp.clients.niquests"),
    "zapros": ("ZaprosSyncClient", None, "unihttp.clients.zapros"),
}

_SERIALIZER_IMPORTS: dict[str, str] = {
    "adaptix": "from unihttp.serializers.adaptix import DEFAULT_RETORT",
    "pydantic": "from unihttp.serializers.pydantic import DEFAULT_RETORT",
    "msgspec": "from unihttp.serializers.msgspec import DEFAULT_RETORT",
}


def _split_words(value: str) -> list[str]:
    return [part for part in re.split(r"[\s_\-./]+", str(value)) if part]


def _to_pascal(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in _split_words(name))


def _safe_identifier(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))
    name = re.sub(r"_+", "_", name).strip("_")
    if name and name[0].isdigit():
        name = "_" + name
    return name or "default"


def _namespace_class_name(path: tuple[str, ...]) -> str:
    return f"{''.join(_to_pascal(part) for part in path)}Namespace"


def _method_binding_name(namespace_path: tuple[str, ...], short_name: str) -> str:
    parts = [_safe_identifier(part) for part in namespace_path] + [
        _safe_identifier(short_name)
    ]
    return "_" + "_".join(parts)


def _client_spec(client_type: str) -> tuple[str, str | None, str]:
    return _CLIENT_SPECS.get(client_type, _CLIENT_SPECS["httpx"])


def _client_import_line(client_type: str) -> str:
    sync_class, async_class, module_path = _client_spec(client_type)
    if async_class:
        return f"from {module_path} import {sync_class}, {async_class}"
    return f"from {module_path} import {sync_class}"


def _serializer_import_line(serializer_type: str) -> str:
    return _SERIALIZER_IMPORTS.get(serializer_type, "")


def _supports_async(client_type: str) -> bool:
    return _client_spec(client_type)[1] is not None


def _sync_base_class(client_type: str) -> str:
    return _client_spec(client_type)[0]


def _async_base_class(client_type: str) -> str | None:
    return _client_spec(client_type)[1]


def _method_view(method: Any) -> dict[str, Any]:
    return {
        "class_name": method.class_name,
        "namespace_path": method.namespace_path,
        "short_name": method.short_name,
        "binding_name": _method_binding_name(method.namespace_path, method.short_name),
        "url": method.url,
        "http_method": method.http_method,
        "summary": method.summary,
        "params": method.params,
        "return_type": method.return_type,
        "operation_id": getattr(method, "operation_id", None),
    }


def _namespace_view(namespace: Any, path: tuple[str, ...] = ()) -> dict[str, Any]:
    current_path = (*path, namespace.name)
    return {
        "name": namespace.name,
        "path": current_path,
        "class_name": _namespace_class_name(current_path),
        "methods": [_method_view(method) for method in namespace.methods],
        "namespaces": [
            _namespace_view(child, current_path) for child in namespace.namespaces
        ],
    }


class SDKGenerator:
    """Generate SDK code from OpenAPI specification."""

    def __init__(
        self,
        parser: OpenAPIParser,
        config: GenerationConfig,
        template: str | None = None,
    ):
        self.parser = parser
        self.config = config
        self.template = template

    def _load_template_source(self) -> str:
        if self.template:
            return self.template

        local_template = Path(__file__).with_name("template.j2")
        if local_template.exists():
            return local_template.read_text(encoding="utf-8")

        return TemplateRenderer.load_template()

    def postprocess(self, code: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "generated.py"

            file.write_text(code)

            ruff_path = shutil.which("ruff")

            if ruff_path:
                result = subprocess.run(  # noqa: S603
                    [ruff_path, "check", "-s", "--fix", str(file)],
                    check=False,
                    capture_output=True,
                )

                if result.returncode not in {0, 1}:
                    raise RuntimeError(result.stderr)

                subprocess.run(  # noqa: S603
                    [ruff_path, "format", "-s", str(file)],
                    check=True,
                )

            else:
                raise FileNotFoundError("`ruff` not found.")

            return file.read_text()

    def generate(self) -> str:
        """Generate SDK code as a string."""
        env = Environment(  # noqa: S701
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        template = env.from_string(self._load_template_source())

        client_type = (
            self.config.client_type.value
            if hasattr(self.config.client_type, "value")
            else self.config.client_type
        )
        serializer_type = (
            self.config.serializer_type.value
            if hasattr(self.config.serializer_type, "value")
            else self.config.serializer_type
        )

        client_type = str(client_type)
        serializer_type = str(serializer_type)

        namespaces = [_namespace_view(namespace) for namespace in self.parser.namespaces]
        methods = [_method_view(method) for method in self.parser.methods]

        rendered = template.render(
            info=self.parser.spec.get("info", {}),
            models=self.parser.models,
            methods=methods,
            namespaces=namespaces,
            client_name=self.parser.client_name,
            client_type=client_type,
            serializer_type=serializer_type,
            client_import_line=_client_import_line(client_type),
            serializer_import_line=_serializer_import_line(serializer_type),
            sync_base_class=_sync_base_class(client_type),
            async_base_class=_async_base_class(client_type),
            supports_async=_supports_async(client_type),
            output_package_name=self.config.output_package_name,
            base_url=self.config.base_url,
        )

        return self.postprocess(rendered)

    @classmethod
    def from_file(
        cls,
        spec_path: str,
        config: GenerationConfig | None = None,
        custom_template: str | None = None,
    ) -> SDKGenerator:
        """Create a generator from an OpenAPI spec file."""
        parser = OpenAPIParser.from_file(spec_path)
        if config is None:
            config = GenerationConfig()
        return cls(parser, config, custom_template)

    def generate_with_config(self, config: GenerationConfig) -> str:
        """Generate SDK with a specific configuration."""
        self.config = config
        return self.generate()
