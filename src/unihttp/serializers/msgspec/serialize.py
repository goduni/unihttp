from typing import Any, TypeVar, get_args, get_origin, get_type_hints

from unihttp.http import UploadFile
from unihttp.markers import Marker
from unihttp.omitted import Omitted
from unihttp.serialize import RequestDumper, ResponseLoader

import msgspec

T = TypeVar("T")


class MsgspecDumper(RequestDumper):
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
        if isinstance(field_value, Omitted):
            return

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
                serialized_value = msgspec.to_builtins(field_value)

            target_dict = data.get(marker.name)
            if target_dict is not None and isinstance(target_dict, dict):
                target_dict[field_name] = serialized_value


class MsgspecLoader(ResponseLoader):
    def load(self, data: Any, tp: type[T]) -> T:
        return msgspec.convert(data, type=tp)
