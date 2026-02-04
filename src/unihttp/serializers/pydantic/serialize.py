from typing import Any, TypeVar, get_args, get_origin, get_type_hints

from pydantic import TypeAdapter

from unihttp.http import UploadFile
from unihttp.markers import Marker
from unihttp.serialize import RequestDumper, ResponseLoader

T = TypeVar("T")


class PydanticDumper(RequestDumper):
    def __init__(self, type_adapter_config: dict[str, Any] | None = None):
        self.type_adapter_config = type_adapter_config or {}

    def dump(self, obj: Any) -> Any:
        data: dict[str, Any] = {
            "path": {},
            "query": {},
            "header": {},
            "body": {},
            "file": {},
            "form": {},
        }

        cls = type(obj)

        try:
            type_hints = get_type_hints(cls, include_extras=True)
        except Exception:
            type_hints = cls.__annotations__  # Fallback

        for field_name, field_value in vars(obj).items():
            if field_name.startswith("__"):
                continue

            hint = type_hints.get(field_name)
            if hint is None:
                continue

            self._process_field(data, field_name, field_value, hint)

        return data

    def _process_field(
            self,
            data: dict[str, Any],
            field_name: str,
            field_value: Any,
            hint: Any,
    ) -> None:
        marker = None
        if get_origin(hint) is not None:
            for arg in get_args(hint):
                if isinstance(arg, Marker):
                    marker = arg
                    break

        if marker:
            if isinstance(field_value, UploadFile):
                serialized_value = field_value.to_tuple()
            else:
                serialized_value = TypeAdapter(type(field_value)).dump_python(
                    field_value, mode="json"
                )

            target_dict = data.get(marker.name)
            if target_dict is not None and isinstance(target_dict, dict):
                target_dict[field_name] = serialized_value


class PydanticLoader(ResponseLoader):
    def load(self, data: Any, tp: type[T]) -> T:
        adapter = TypeAdapter(tp)
        return adapter.validate_python(data)
