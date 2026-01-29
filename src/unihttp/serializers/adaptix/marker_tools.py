from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Annotated, Any, get_args, get_origin, override

from unihttp.markers import Marker

from adaptix import Mediator, P, TypeHint, create_loc_stack_checker
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
from adaptix._internal.provider.essential import DirectMediator
from adaptix._internal.provider.loc_stack_filtering import (
    LocStack,
    LocStackChecker,
    Pred,
)
from adaptix._internal.provider.loc_stack_tools import find_owner_with_field
from adaptix._internal.provider.location import FieldLoc, OutputFieldLoc

__all__ = (
    "DefaultMarkerFieldPathMaker",
    "ForMarkerLocStackChecker",
    "KeyPath",
    "MarkerFieldPathMaker",
    "for_marker",
)


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
            key_path: KeyPath | None,
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
        # if marker is Path, then ("user_id",) -> ("path", "user_id")
        # if marker is Body, then ("username",) -> ("body", "username")
        return marker.name, *key_path


class ForMarkerLocStackChecker(LocStackChecker):
    def __init__(
            self,
            loc_stack_checker: LocStackChecker,
            marker: type[Marker],
            subclass: bool = False,
    ) -> None:
        self.marker = marker
        self.subclass = subclass
        self.loc_stack_checker = loc_stack_checker

    @override
    def check_loc_stack(
            self,
            mediator: DirectMediator,
            loc_stack: LocStack[OutputFieldLoc],
    ) -> bool:
        try:
            _, field_loc = find_owner_with_field(loc_stack)
        except ValueError:
            return False

        return self._check_field_loc(
            field_loc
        ) and self.loc_stack_checker.check_loc_stack(mediator, loc_stack)

    def _check_field_loc(self, loc: FieldLoc) -> bool:
        try:
            marker = get_marker(loc.type)
        except ValueError:
            return False

        if marker is None:
            return False

        if self.subclass:
            return issubclass(type(marker), self.marker)
        return type(marker) is self.marker


def for_marker(
        marker: type[Marker],
        predicate: Pred | None = None,
        subclass: bool = False,
) -> LocStackChecker:
    """
    for_marker predicate for adaptix recipe.

    Usage:
        # Dump all `Query` values `None` to `"null"`
        dumper(
            for_marker(Query, P[None]),
            lambda _: "null",
        )

        # Dump all `Query` values `bool` to int
        dumper(
             for_marker(Query, P[bool]),
             lambda x: int(x),
        )

        # Load all `Body` values `datetime` from int-timestamp to datetime
        loader(
            for_marker(Body, P[datetime]),
            lambda x: datetime.fromtimestamp(x / 1000),
        ).
    """
    loc_stack_checker: LocStackChecker
    if predicate is None:
        loc_stack_checker = P.ANY
    else:
        loc_stack_checker = create_loc_stack_checker(predicate)

    return ForMarkerLocStackChecker(
        marker=marker,
        subclass=subclass,
        loc_stack_checker=loc_stack_checker,
    )
