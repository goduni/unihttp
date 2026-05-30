from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import yaml


@dataclass
class SchemaField:
    """Represents a field in a generated dataclass model."""

    name: str
    type: str
    default: Any | None = None


@dataclass
class SchemaModel:
    """Represents an OpenAPI schema model."""

    name: str
    fields: list[SchemaField]


@dataclass
class MethodParam:
    """Represents a method parameter."""

    name: str
    annotated_type: str
    proxy_type: str
    default: Any | None = None


@dataclass
class MethodDefinition:
    """Represents one generated API method."""

    class_name: str
    namespace_path: tuple[str, ...]
    short_name: str
    url: str
    http_method: str
    summary: str
    params: list[MethodParam]
    return_type: str
    operation_id: str | None = None


@dataclass
class NamespaceDefinition:
    """Represents a namespace with nested namespaces and methods."""

    name: str
    methods: list[MethodDefinition] = field(default_factory=list)
    namespaces: list[NamespaceDefinition] = field(default_factory=list)


@dataclass
class _NamespaceNode:
    """Internal tree node used to assemble NamespaceDefinition objects."""

    name: str
    children: dict[str, _NamespaceNode] = field(default_factory=dict)
    methods: list[MethodDefinition] = field(default_factory=list)


class OpenAPIParser:
    """Parse OpenAPI 3.1 specs and extract models and namespace-structured methods."""

    _OPENAPI_PRIMITIVE_MAP: ClassVar[dict[str, str]] = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }

    _FORMAT_MAP: ClassVar[dict[str, str]] = {
        "int32": "int",
        "int64": "int",
        "float": "float",
        "double": "float",
        "byte": "bytes",
        "binary": "bytes",
        "date": "str",
        "date-time": "str",
        "uuid": "str",
        "uri": "str",
        "email": "str",
    }

    _HTTP_METHODS: ClassVar[list[str]] = [
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
    ]

    _MARKER_FOR_IN: ClassVar[dict[str, str]] = {
        "path": "Path",
        "query": "Query",
        "header": "Header",
        "cookie": "Query",
    }

    _SPECIAL_SINGLETON_GET_NAMES: ClassVar[dict[str, str]] = {
        "health": "check",
        "readiness": "readiness",
        "liveness": "live",
        "live": "live",
        "status": "status",
        "metrics": "metrics",
    }

    _SPECIAL_SINGLETON_POST_NAMES: ClassVar[dict[str, str]] = {
        "login": "login",
        "logout": "logout",
        "refresh": "refresh",
    }

    _ACTION_SEGMENTS: ClassVar[set[str]] = {
        "activate",
        "archive",
        "assign",
        "approve",
        "cancel",
        "check",
        "confirm",
        "disable",
        "enable",
        "export",
        "import",
        "invite",
        "link",
        "lock",
        "pause",
        "publish",
        "reject",
        "remove",
        "reset",
        "restore",
        "resume",
        "revoke",
        "run",
        "search",
        "send",
        "start",
        "stop",
        "submit",
        "sync",
        "toggle",
        "unarchive",
        "unlock",
        "unpublish",
        "update",
        "verify",
    }

    def __init__(self, spec: dict[str, Any]):
        self.spec = spec

    @classmethod
    def from_file(cls, path: str | Path) -> OpenAPIParser:
        """Load a spec from YAML or JSON."""
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        if p.suffix.lower() in {".yaml", ".yml"}:
            spec = yaml.safe_load(text)
        else:
            spec = json.loads(text)
        if not isinstance(spec, dict):
            raise TypeError("OpenAPI spec must decode to a mapping")
        return cls(spec)

    @property
    def client_name(self) -> str:
        """Generate a client class name from info.title."""
        info = self.spec.get("info", {})
        title = info.get("title", "API")
        return f"{self._to_pascal(title)}Client"

    @property
    def models(self) -> list[SchemaModel]:
        """Extract dataclass-like schema models from components/schemas."""
        schemas = self.spec.get("components", {}).get("schemas", {})
        models: list[SchemaModel] = []

        for schema_name, schema in schemas.items():
            if not isinstance(schema, dict):
                continue
            if schema.get("type") != "object" and "properties" not in schema:
                continue

            props = schema.get("properties", {})
            if not isinstance(props, dict):
                continue

            required_set = set(schema.get("required", []))
            fields: list[SchemaField] = []

            for prop_name, prop_schema in props.items():
                if not isinstance(prop_schema, dict):
                    prop_schema = {}  # noqa: PLW2901
                is_required = prop_name in required_set
                fields.append(
                    SchemaField(
                        name=self._safe_identifier(self._to_snake(prop_name)),
                        type=self._schema_to_python_type(
                            prop_schema, required=is_required
                        ),
                        default=self._field_default(prop_schema, is_required),
                    )
                )

            fields.sort(key=lambda f: f.default is not None)
            models.append(SchemaModel(name=schema_name, fields=fields))

        return models

    @property
    def namespaces(self) -> list[NamespaceDefinition]:
        """Extract a tree of namespaces with methods attached to leaf namespaces."""
        methods = self.methods
        root = _NamespaceNode(name="")
        for method in methods:
            self._insert_method(root, method)
        return [self._node_to_namespace(node) for node in root.children.values()]

    @property
    def methods(self) -> list[MethodDefinition]:
        """Extract method definitions from the OpenAPI paths."""
        methods: list[MethodDefinition] = []
        paths = self.spec.get("paths", {})
        if not isinstance(paths, dict):
            return methods

        for path, path_item in paths.items():
            if isinstance(path_item, str):
                path_item = self._resolve_ref(path_item)  # noqa: PLW2901
            elif isinstance(path_item, dict) and "$ref" in path_item:
                path_item = self._resolve_ref(path_item["$ref"])  # noqa: PLW2901

            if not isinstance(path_item, dict):
                continue

            for http_method in self._HTTP_METHODS:
                operation = path_item.get(http_method)
                if not isinstance(operation, dict):
                    continue

                namespace_path = self._derive_namespace_path(path, operation)
                short_name = self._derive_short_name(
                    path=path,
                    http_method=http_method,
                    operation=operation,
                    namespace_path=namespace_path,
                )
                op_id = operation.get("operationId")
                class_name = self._derive_class_name(
                    namespace_path=namespace_path,
                    short_name=short_name,
                    http_method=http_method,
                )
                summary = operation.get("summary") or operation.get("description") or ""

                params = self._extract_params(path_item, operation)
                params.extend(self._body_params(operation))
                params.sort(key=lambda p: p.default is not None)

                methods.append(
                    MethodDefinition(
                        class_name=class_name,
                        namespace_path=namespace_path,
                        short_name=short_name,
                        url=path,
                        http_method=http_method.upper(),
                        summary=str(summary).replace('"', "'"),
                        params=params,
                        return_type=self._response_type(operation),
                        operation_id=op_id if isinstance(op_id, str) else None,
                    )
                )

        return methods

    def _insert_method(self, root: _NamespaceNode, method: MethodDefinition) -> None:
        node = root
        path = method.namespace_path or ("default",)
        for segment in path:
            if segment not in node.children:
                node.children[segment] = _NamespaceNode(name=segment)
            node = node.children[segment]
        node.methods.append(method)

    def _node_to_namespace(self, node: _NamespaceNode) -> NamespaceDefinition:
        return NamespaceDefinition(
            name=node.name,
            methods=node.methods,
            namespaces=[
                self._node_to_namespace(child) for child in node.children.values()
            ],
        )

    def _derive_namespace_path(
        self, path: str, operation: dict[str, Any]
    ) -> tuple[str, ...]:
        tags = operation.get("tags")
        if isinstance(tags, list) and tags:
            tag = tags[0]
            if isinstance(tag, str) and tag.strip():
                segments = [
                    self._safe_identifier(self._to_snake(part))
                    for part in re.split(r"[./\\s_-]+", tag)
                    if part
                ]
                if segments:
                    return tuple(segments)

        raw_segments = [segment for segment in path.split("/") if segment]
        static_segments = [
            self._safe_identifier(self._to_snake(segment))
            for segment in raw_segments
            if not self._is_path_parameter(segment)
        ]
        if not static_segments:
            return ("default",)

        # Prefer nested namespaces for hierarchical URLs, but drop obvious action tails.
        if len(static_segments) > 1 and self._looks_like_action(static_segments[-1]):
            return tuple(static_segments[:-1]) or (static_segments[-1],)

        return tuple(static_segments)

    def _derive_short_name(  # noqa: C901
        self,
        *,
        path: str,
        http_method: str,
        operation: dict[str, Any],
        namespace_path: tuple[str, ...],
    ) -> str:
        raw_segments = [segment for segment in path.split("/") if segment]
        path_params = [
            self._safe_identifier(self._to_snake(segment[1:-1]))
            for segment in raw_segments
            if self._is_path_parameter(segment)
        ]
        has_any_param = bool(path_params)
        has_terminal_param = bool(raw_segments) and self._is_path_parameter(
            raw_segments[-1]
        )
        tail = namespace_path[-1] if namespace_path else "default"

        # Action endpoints like /users/{id}/activate -> namespace users, method activate.
        if len([s for s in raw_segments if not self._is_path_parameter(s)]) > 1:
            last_static_raw = next(
                (
                    seg
                    for seg in reversed(raw_segments)
                    if not self._is_path_parameter(seg)
                ),
                None,
            )
            if last_static_raw is not None:
                last_static = self._safe_identifier(self._to_snake(last_static_raw))
                if self._looks_like_action(last_static_raw) and last_static != tail:
                    return self._safe_identifier(last_static)

        if not has_any_param:
            if len(namespace_path) == 1:
                seg = namespace_path[0]
                if http_method == "get":
                    return self._SPECIAL_SINGLETON_GET_NAMES.get(
                        seg, "list" if seg.endswith("s") else seg
                    )
                if http_method == "post":
                    return self._SPECIAL_SINGLETON_POST_NAMES.get(
                        seg, "create" if seg.endswith("s") else seg
                    )
                if http_method == "put":
                    return "replace" if seg.endswith("s") else seg
                if http_method == "patch":
                    return "update" if seg.endswith("s") else seg
                if http_method == "delete":
                    return "delete" if seg.endswith("s") else seg
            return self._fallback_operation_name(operation, http_method, path)

        if has_terminal_param:
            param_name = path_params[-1] if path_params else "id"
            if http_method == "get":
                return f"get_by_{param_name}"
            if http_method == "post":
                return self._fallback_operation_name(operation, http_method, path)
            if http_method == "put":
                return "replace"
            if http_method == "patch":
                return "update"
            if http_method == "delete":
                return "delete"
            if http_method == "head":
                return "head"
            if http_method == "options":
                return "options"

        if http_method == "get":
            return "list"
        if http_method == "post":
            return "create"
        if http_method == "put":
            return "replace"
        if http_method == "patch":
            return "update"
        if http_method == "delete":
            return "delete"
        if http_method == "head":
            return "head"
        if http_method == "options":
            return "options"

        return self._fallback_operation_name(operation, http_method, path)

    def _derive_class_name(
        self,
        *,
        namespace_path: tuple[str, ...],
        short_name: str,
        http_method: str,
    ) -> str:
        candidate = f"{'_'.join(namespace_path)}_{short_name}_{http_method}"
        return self._to_pascal(candidate)

    def _fallback_operation_name(
        self, operation: dict[str, Any], http_method: str, path: str
    ) -> str:
        op_id = operation.get("operationId")
        if isinstance(op_id, str) and op_id.strip():
            return self._safe_identifier(self._to_snake(op_id))

        candidate = f"{http_method}_{path}"
        candidate = self._to_snake(candidate)
        candidate = re.sub(r"_+", "_", candidate).strip("_")
        return self._safe_identifier(candidate)

    def _extract_params(
        self, path_item: dict[str, Any], operation: dict[str, Any]
    ) -> list[MethodParam]:
        params: list[MethodParam] = []
        seen_params: set[tuple[str, str]] = set()

        path_params_raw = path_item.get("parameters", [])
        op_params_raw = operation.get("parameters", [])
        path_params = list(path_params_raw) if isinstance(path_params_raw, list) else []
        op_params = list(op_params_raw) if isinstance(op_params_raw, list) else []

        for param in path_params + op_params:
            if not isinstance(param, dict):
                continue
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"])  # noqa: PLW2901
            if not isinstance(param, dict):
                continue

            p_in = param.get("in", "query")
            p_name = self._safe_identifier(
                self._to_snake(str(param.get("name", "param")))
            )
            key = (p_name, p_in)
            if key in seen_params:
                continue
            seen_params.add(key)

            p_schema = param.get("schema", {})
            if not isinstance(p_schema, dict):
                p_schema = {}
            is_required = param.get("required", p_in == "path")
            py_type = self._schema_to_python_type(
                p_schema,
                required=is_required,
            )

            marker = self._MARKER_FOR_IN.get(
                p_in,
                "Query",
            )

            params.append(
                MethodParam(
                    name=p_name,
                    annotated_type=f"{marker}[{py_type}]",
                    proxy_type=py_type,
                    default=self._field_default(
                        p_schema,
                        is_required,
                    ),
                )
            )

        return params

    def _resolve_ref(self, ref: str) -> dict[str, Any]:
        """Resolve a local JSON pointer like '#/components/schemas/User'."""
        parts = ref.lstrip("#/").split("/")
        node: Any = self.spec
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                raise KeyError(f"Unresolvable $ref: {ref}")
            node = node[part]
        if not isinstance(node, dict):
            raise TypeError(f"Resolved $ref is not an object: {ref}")
        return node

    def _schema_to_python_type(
        self, schema: dict[str, Any], required: bool = True
    ) -> str:
        """Convert an OpenAPI schema to a Python type string."""
        if "$ref" in schema:
            t = self._ref_to_name(schema["$ref"])
            return t if required else f"{t} | None"

        if "anyOf" in schema or "oneOf" in schema:
            variants = schema.get("anyOf") or schema.get("oneOf", [])
            if not isinstance(variants, list):
                variants = []
            non_null = [
                v for v in variants if isinstance(v, dict) and v.get("type") != "null"
            ]
            has_null = len(non_null) < len(variants)
            if len(non_null) == 1:
                inner = self._schema_to_python_type(non_null[0])
                return f"{inner} | None" if has_null else inner
            return "Any"

        oa_type = schema.get("type", "Any")
        fmt = schema.get("format", "")

        if fmt and fmt in self._FORMAT_MAP:
            base = self._FORMAT_MAP[fmt]
        elif isinstance(oa_type, list):
            non_null = [t for t in oa_type if t != "null"]
            has_null = len(non_null) < len(oa_type)
            base = (
                self._OPENAPI_PRIMITIVE_MAP.get(non_null[0], "Any") if non_null else "Any"
            )
            return f"{base} | None" if has_null else base
        elif oa_type == "array":
            items = schema.get("items", {})
            if not isinstance(items, dict):
                items = {}
            inner = self._schema_to_python_type(items)
            base = f"list[{inner}]"
        elif oa_type == "object":
            base = "dict"
        else:
            base = self._OPENAPI_PRIMITIVE_MAP.get(str(oa_type), "Any")

        return base if required else f"{base} | None"

    def _response_type(self, operation: dict[str, Any]) -> str:  # noqa: C901
        """Derive the Python return type from the first successful response."""
        responses = operation.get("responses", {})
        if not isinstance(responses, dict):
            return "dict"

        for code in ("200", "201", "202", "204", "2XX"):
            resp = responses.get(code)
            if not resp:
                continue
            if isinstance(resp, dict) and "$ref" in resp:
                resp = self._resolve_ref(resp["$ref"])
            if not isinstance(resp, dict):
                continue

            content = resp.get("content", {})
            if not isinstance(content, dict):
                continue

            for media_type in ("application/json", "text/plain", "*/*"):
                if media_type not in content:
                    continue
                payload = content[media_type]
                if not isinstance(payload, dict):
                    continue
                resp_schema = payload.get("schema", {})
                if not isinstance(resp_schema, dict):
                    resp_schema = {}

                if "$ref" in resp_schema:
                    return self._ref_to_name(resp_schema["$ref"])
                if resp_schema.get("type") == "array":
                    items = resp_schema.get("items", {})
                    if not isinstance(items, dict):
                        items = {}
                    inner = (
                        self._ref_to_name(items["$ref"])
                        if "$ref" in items
                        else self._schema_to_python_type(items)
                    )
                    return f"list[{inner}]"
                return self._schema_to_python_type(resp_schema)

        return "dict"

    def _body_params(self, operation: dict[str, Any]) -> list[MethodParam]:  # noqa: C901
        """
        Extract requestBody fields as
        a single body/form/file parameter or flattened params.
        """
        rb = operation.get("requestBody")
        if not rb:
            return []
        if isinstance(rb, dict) and "$ref" in rb:
            rb = self._resolve_ref(rb["$ref"])

        if not isinstance(rb, dict):
            return []

        content = rb.get("content", {})
        if not isinstance(content, dict):
            return []

        is_required = rb.get("required", False)

        for media_type, marker in (
            ("application/json", "Body"),
            ("application/x-www-form-urlencoded", "Form"),
            ("multipart/form-data", "File"),
        ):
            if media_type not in content:
                continue

            media_obj = content[media_type]
            if not isinstance(media_obj, dict):
                continue

            schema = media_obj.get("schema", {})
            if not isinstance(schema, dict):
                schema = {}

            if "$ref" in schema:
                model_name = self._ref_to_name(schema["$ref"])
                return [
                    MethodParam(
                        name=self._to_snake(model_name),
                        annotated_type=f"{marker}[{model_name}]",
                        proxy_type=model_name,
                        default=None if is_required else "None",
                    )
                ]

            if schema is None:
                return []

            props = schema.get("properties", {})
            if not isinstance(props, dict):
                return []

            required_set = set(schema.get("required", []))
            params: list[MethodParam] = []

            for prop_name, prop_schema in props.items():
                if not isinstance(prop_schema, dict):
                    prop_schema = {}  # noqa: PLW2901
                is_req = prop_name in required_set
                py_type = self._schema_to_python_type(prop_schema, required=is_req)
                params.append(
                    MethodParam(
                        name=self._safe_identifier(self._to_snake(prop_name)),
                        annotated_type=f"{marker}[{py_type}]",
                        proxy_type=prop_name,
                        default=self._field_default(prop_schema, is_req),
                    )
                )

            params.sort(key=lambda p: p.default is not None)
            return params

        return []

    def _field_default(self, schema: dict[str, Any], required: bool) -> Any:
        """Return a Python literal string for defaults, or 'None' for optional fields."""
        if "default" in schema:
            d = schema["default"]
            if isinstance(d, bool):
                return str(d)
            if isinstance(d, str):
                return repr(d)
            if d is None:
                return "None"
            return str(d)
        if not required:
            return "None"
        return None

    def _ref_to_name(self, ref: str) -> str:
        """'#/components/schemas/User' -> 'User'."""
        return ref.rsplit("/", maxsplit=1)[-1]

    def _is_path_parameter(self, segment: str) -> bool:
        return segment.startswith("{") and segment.endswith("}")

    def _looks_like_action(self, segment: str) -> bool:
        segment = self._safe_identifier(self._to_snake(segment))
        return segment in self._ACTION_SEGMENTS

    def _to_pascal(self, name: str) -> str:
        """Convert snake_case / kebab-case / path text to PascalCase."""
        name = re.sub(r"[{}/]", " ", name)
        return "".join(word.capitalize() for word in re.split(r"[\s_\-]+", name) if word)

    def _to_snake(self, name: str) -> str:
        """Convert PascalCase / camelCase / kebab-case / path text to snake_case."""
        name = re.sub(r"[{}/\-]", "_", name)
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
        return name.lower().strip("_")

    def _safe_identifier(self, name: str) -> str:
        """Ensure a string is a valid Python identifier."""
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        name = re.sub(r"_+", "_", name).strip("_")
        if name and name[0].isdigit():
            name = "_" + name
        return name or "default"


__all__ = [
    "MethodDefinition",
    "MethodParam",
    "NamespaceDefinition",
    "OpenAPIParser",
    "SchemaField",
    "SchemaModel",
]
