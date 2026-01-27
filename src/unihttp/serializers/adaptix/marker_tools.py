from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Annotated, Any, get_args, get_origin

from unihttp.markers import Marker

from adaptix import Mediator, TypeHint
from adaptix._internal.model_tools.definitions import BaseField
from adaptix._internal.morphing.model.crown_definitions import (
    BaseNameLayoutRequest,
    InpExtraMove,
    OutExtraMove,
)
from adaptix._internal.morphing.name_layout.base import KeyPath
from adaptix._internal.morphing.name_layout.component import (
    BuiltinStructureMaker,
    FieldAndPath,
    StructureSchema,
)

__all__ = ("DefaultMarkerFieldPathMaker", "KeyPath", "MarkerFieldPathMaker")


def get_marker(tp: TypeHint) -> Marker | None:
    origin = get_origin(tp)

    if origin == Annotated:  # type: ignore[comparison-overlap]
        args = get_args(tp)
        for arg in args[1:]:
            if isinstance(arg, Marker):
                return arg

    return None


class MarkerFieldPathMaker(BuiltinStructureMaker, ABC):
    @abstractmethod
    def make(
            self,
            marker: Marker,
            key_path: KeyPath,
    ) -> KeyPath:
        raise NotImplementedError

    def _map_fields(
            self,
            mediator: Mediator[BaseNameLayoutRequest[Any]],
            request: BaseNameLayoutRequest[Any],
            schema: StructureSchema,
            extra_move: InpExtraMove[Any] | OutExtraMove[Any],
    ) -> Iterable[FieldAndPath[Any]]:
        for field, path in super()._map_fields(
                mediator=mediator,
                request=request,
                schema=schema,
                extra_move=extra_move,
        ):
            yield self._make_with_marker(field, path)

    def _make_with_marker(
            self,
            field: BaseField,
            key_path: KeyPath | None
    ) -> FieldAndPath[Any]:
        if key_path is None:
            return field, key_path

        marker = get_marker(field.type)
        if marker is None:
            return field, key_path

        return field, self.make(marker, key_path)


class DefaultMarkerFieldPathMaker(MarkerFieldPathMaker):
    def make(
            self,
            marker: Marker,
            key_path: KeyPath,
    ) -> KeyPath:
        # ("user_id",) -> ("path", "user_id")
        return marker.name, *key_path
